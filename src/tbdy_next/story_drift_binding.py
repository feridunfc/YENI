"""Bind a same-session ETABS generic source capture to the EXISTING STORY_DRIFT record.

This is a *source numerical* stage, not TBDY 2018 drift compliance.  In
particular: spectrum point displacement maxima are never subtracted, and a
Ritz-mode shape differential is never promoted to a design displacement.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .story_delta import DeltaSourceError, calculate

CHECK_ID = "STORY_DRIFT"
RECORD_SCHEMA = "tbdy.next.vs05.story-drift-check-record.v1"


def _verify_generic_capture(source: Mapping[str, Any]) -> None:
    """Check the SHA-256 emitted by the existing generic gateway's `seal`."""
    checksum = source.get("payload_sha256")
    if not isinstance(checksum, str) or len(checksum) != 64:
        raise DeltaSourceError("GENERIC_SOURCE_SEAL_MISSING")
    original = {k: v for k, v in source.items() if k != "payload_sha256"}
    serialized = (json.dumps(original, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    if hashlib.sha256(serialized).hexdigest() != checksum:
        raise DeltaSourceError("GENERIC_SOURCE_SEAL_MISMATCH")


def bind_story_drift(source: Mapping[str, Any] | None,
                     *, capture_error: str | None = None) -> dict[str, Any]:
    """Project exact ETABS drift rows into one catalog-owned check record.

    Missing/invalid capture yields a blocked check rather than silently
    deleting it or fabricating code compliance.  Old VS04 runs without any
    capture remain compatible at their original reporting call sites.
    """
    base: dict[str, Any] = {
        "schema": RECORD_SCHEMA,
        "check_id": CHECK_ID,
        "dag_node_id": CHECK_ID,
        "dag_node_type": "REGULATORY_CHECK",
        "dag_declared_dependencies": ["ANALYSIS_BASIS_GATE", "SEISMIC_DESIGN_BASIS"],
        "dag_execution_authority": "DENIED",
        "title": "TBDY 2018 STORY_DRIFT — ETABS reduced-drift source candidates",
        "code_ref": "TBDY 2018 4.9.1 / 4.32–4.34 (not yet authorized)",
        "status": "BLOCKED_SOURCE_UNAVAILABLE",
        "execution_status": "BLOCKED",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "numerical_pass_issued": False,
        "items": [],
        "missing_story_case_direction": [],
        "expected_story_case_direction_count": 0,
        "evaluated_story_case_direction_count": 0,
        "all_stories_covered": False,
        "model": None,
        "source_payload_sha256": None,
        "source_capture_error": capture_error,
        "modal_shape_column_mode_pairs": 0,
        "spectrum_max_point_rows_not_subtracted": 0,
        "note": "Numeric candidates only; scaling, R/I, lambda, method applicability, "
                "physical story completeness and independent verification are not yet qualified.",
    }
    if capture_error:
        return {**base, "reason_codes": ["LIVE_ETABS_STORY_DRIFT_CAPTURE_FAILED"]}
    if not isinstance(source, Mapping):
        return {**base, "reason_codes": ["STORY_DRIFT_CAPTURE_ABSENT"]}
    try:
        _verify_generic_capture(source)
        result = calculate(source)
        rows = result["story_deltas"]
        coverage = result["story_delta_coverage"]
        expected = coverage["available_story_count"] * 2 * 2
        if len(rows) != coverage["response_spectrum_rows"] or expected < len(rows):
            raise DeltaSourceError("SOURCE_COVERAGE_INTERNAL_CONFLICT")
        if bool(coverage["all_stories_covered"]) != (expected == len(rows)):
            raise DeltaSourceError("STORY_COVERAGE_COMPLETENESS_CONFLICT")
        partial = expected != len(rows)
        return {
            **base,
            "status": ("NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE" if partial
                       else "NUMERIC_SOURCE_OBSERVED"),
            "execution_status": "EXECUTED_SOURCE_NUMERICAL",
            "model": result["model"],
            "source_payload_sha256": source["payload_sha256"],
            "source_capture_error": None,
            "items": rows,
            "missing_story_case_direction": coverage["missing_story_case_direction"],
            "expected_story_case_direction_count": expected,
            "evaluated_story_case_direction_count": len(rows),
            "all_stories_covered": coverage["all_stories_covered"],
            "uncovered_stories": coverage["uncovered_stories"],
            "modal_shape_column_mode_pairs": result["modal_shape_coverage"]["column_mode_shape_difference_count"],
            "spectrum_max_point_rows_not_subtracted": result["modal_shape_coverage"]["spectrum_point_max_rows_not_subtracted"],
            "reason_codes": (["INCOMPLETE_STORY_DRIFT_CASE_COVERAGE"] if partial else []),
        }
    except (DeltaSourceError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
        return {**base, "status": "BLOCKED_SOURCE_INVALID",
                "reason_codes": [str(exc)]}
