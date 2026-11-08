"""VS06-A: read-only census of source-numeric STORY_DRIFT instances.

Derived only from a sealed generic ETABS snapshot and its VS05 result.
A complete *accounting* ledger is not a complete displacement source,
physical applicability proof, normative drift check, or design release.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from .story_delta import story_heights
from .story_drift_binding import _verify_generic_capture

SCHEMA = "tbdy.next.vs06.story-slot-ledger.v1"
CASES = ("RSX", "RSY")
DIRECTIONS = ("X", "Y")


class StorySlotLedgerError(ValueError):
    """Contradictory or untrusted source/coverage evidence."""


def _slot(row: Mapping[str, Any]) -> tuple[str, str, str]:
    if not isinstance(row, Mapping):
        raise StorySlotLedgerError("SLOT_ROW_NOT_OBJECT")
    story, case, direction = row.get("story"), row.get("case"), row.get("direction")
    if not isinstance(story, str) or not story or case not in CASES or direction not in DIRECTIONS:
        raise StorySlotLedgerError("INVALID_STORY_CASE_DIRECTION")
    return story, case, direction


def build_story_slot_ledger(source: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any]:
    """Reconcile all expected source slots without inventing applicability.

    The VS05 record is historical and MUST NOT be rewritten: prior receipts
    are verified against its original exact payload during JSON/HTML export.
    """
    if not isinstance(source, Mapping) or not isinstance(record, Mapping):
        raise StorySlotLedgerError("SOURCE_OR_RECORD_NOT_OBJECT")
    _verify_generic_capture(source)
    if (record.get("check_id") != "STORY_DRIFT" or
            record.get("execution_status") != "EXECUTED_SOURCE_NUMERICAL" or
            record.get("formal_compliance") != "NOT_PROVEN" or
            record.get("engineering_release") != "NOT_READY" or
            record.get("dag_execution_authority") != "DENIED" or
            record.get("numerical_pass_issued") is not False):
        raise StorySlotLedgerError("UNTRUSTED_NORMATIVE_PROMOTION")
    if record.get("source_payload_sha256") != source.get("payload_sha256"):
        raise StorySlotLedgerError("SOURCE_RECORD_HASH_MISMATCH")

    heights = story_heights(source)
    expected = {(story, case, direction)
                for story in heights for case in CASES for direction in DIRECTIONS}
    rows = record.get("items")
    missing_rows = record.get("missing_story_case_direction")
    if not isinstance(rows, list) or not isinstance(missing_rows, list):
        raise StorySlotLedgerError("INVALID_SOURCE_SLOT_LISTS")
    observed: set[tuple[str, str, str]] = set()
    observed_values: dict[tuple[str, str, str], str] = {}
    for row in rows:
        key = _slot(row)
        if key not in expected:
            raise StorySlotLedgerError("OBSERVED_OUTSIDE_EXPECTED_DENOMINATOR")
        if key in observed:
            raise StorySlotLedgerError("DUPLICATE_OBSERVED_SLOT")
        if (row.get("regulatory_status") != "NOT_PROVEN" or
                row.get("calculation_type") != "ETABS_STORY_DRIFT_RATIO_TIMES_STORY_HEIGHT" or
                row.get("primary_direction") is not (key[1][-1] == key[2])):
            raise StorySlotLedgerError("OBSERVED_ROW_CONTRACT_INVALID")
        value = row.get("etabs_derived_delta_mm")
        if not isinstance(value, str) or not value:
            raise StorySlotLedgerError("OBSERVED_DELTA_MISSING")
        observed.add(key)
        observed_values[key] = value

    missing: set[tuple[str, str, str]] = set()
    for row in missing_rows:
        key = _slot(row)
        if key not in expected or key in observed:
            raise StorySlotLedgerError("INVALID_MISSING_SLOT")
        if key in missing:
            raise StorySlotLedgerError("DUPLICATE_MISSING_SLOT")
        missing.add(key)
    if missing != expected - observed:
        raise StorySlotLedgerError("MISSING_SLOT_CENSUS_MISMATCH")
    if (record.get("expected_story_case_direction_count") != len(expected) or
            record.get("evaluated_story_case_direction_count") != len(observed) or
            record.get("all_stories_covered") is not (not missing) or
            record.get("status") != ("NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE"
                                     if missing else "NUMERIC_SOURCE_OBSERVED")):
        raise StorySlotLedgerError("RECORD_COVERAGE_CONFLICT")

    slots = []
    for story, case, direction in sorted(expected):
        key = (story, case, direction)
        seen = key in observed
        slots.append({
            "story": story, "case": case, "direction": direction,
            "source_status": "OBSERVED_SOURCE_NUMERIC" if seen else "SOURCE_MISSING",
            "source_delta_mm": observed_values.get(key),
            "physical_applicability": "NOT_PROVEN",
            "normative_status": "NOT_PROVEN",
            "reason_code": ("NORMATIVE_BASIS_UNAPPROVED" if seen
                            else "MISSING_SOURCE_AND_APPLICABILITY_EVIDENCE"),
        })
    ledger = {
        "schema": SCHEMA,
        "check_id": "STORY_DRIFT",
        "dag_node_id": "STORY_DRIFT",
        "dag_execution_authority": "DENIED",
        "source_payload_sha256": source["payload_sha256"],
        "expected_slot_count": len(expected),
        "accounted_slot_count": len(slots),
        "source_numeric_count": len(observed),
        "source_missing_count": len(missing),
        "accounting_complete": len(slots) == len(expected),
        "source_coverage_complete": not missing,
        "physical_applicability_verified": False,
        "normative_checks_issued": 0,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "slots": slots,
    }
    payload = json.dumps(ledger, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    ledger["ledger_sha256"] = sha256(payload).hexdigest()
    return ledger
