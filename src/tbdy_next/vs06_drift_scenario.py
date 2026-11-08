"""VS06-C2: actionable TBDY 4.9 source-numeric scenario, NOT a code release.

Reuses eq_4_34_effective_drift for observed ETABS Story Drifts*h.
A user-selected R/I/lambda, brittle/flexible class and wall coverage are
explicit WHAT-IF assumptions; source-numeric candidates are not qualified
same-step design earthquake member-end differences.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

from .normative_basis import eq_4_34_effective_drift
from .story_drift_binding import _verify_generic_capture

SCHEMA = "tbdy.next.vs06.c2.drift-scenario.v1"
DEFAULTS = {
    "r": "7", "i": "1.5", "lambda": "0.5", "material": "RC",
    "wall_type": "BRITTLE", "flexible_proven": "false",
    "wall_mode": "LOAD_PATTERN_BEAM_CANDIDATE",
    "wall_load_pattern": "LC_WDL",
    "coverage_pct": "100", "wall_height_m": "2.8",
    "opening_pct": "0", "thickness_m": "0.19",
    "manual_wall_length_m": "0",
}
ALLOWED = frozenset(DEFAULTS)
CASES = {"X": "RSX", "Y": "RSY"}


class DriftScenarioError(ValueError):
    pass


def _positive(v: Any, name: str, *, zero: bool = False, maximum: str | None = None) -> Decimal:
    if type(v) is not str or len(v) > 40:
        raise DriftScenarioError(name + "_INVALID_TYPE")
    try:
        x = Decimal(v)
    except (InvalidOperation, ValueError):
        raise DriftScenarioError(name + "_NOT_DECIMAL") from None
    if not x.is_finite() or (x < 0 if zero else x <= 0):
        raise DriftScenarioError(name + "_NOT_POSITIVE_FINITE")
    if maximum is not None and x > Decimal(maximum):
        raise DriftScenarioError(name + "_EXCEEDS_MAX")
    return x


def options(raw: Mapping[str, Any] | None) -> dict[str, str]:
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping) or set(raw) - ALLOWED:
        raise DriftScenarioError("UNKNOWN_SCENARIO_FIELDS")
    merged = {**DEFAULTS, **raw}
    if any(type(v) is not str for v in merged.values()):
        raise DriftScenarioError("SCENARIO_VALUES_MUST_BE_STRINGS")
    if merged["material"] not in ("RC", "STEEL"):
        raise DriftScenarioError("MATERIAL_NOT_SUPPORTED")
    if merged["wall_type"] not in ("BRITTLE", "FLEXIBLE"):
        raise DriftScenarioError("WALL_TYPE_NOT_SUPPORTED")
    if merged["flexible_proven"] not in ("true", "false"):
        raise DriftScenarioError("FLEXIBLE_CAPACITY_FLAG_INVALID")
    if merged["wall_mode"] == "LC_WALL_BEAM_CANDIDATE":
        # Preserve early C2 scenario clients; this old mode ID never
        # chooses LC_WALL as an actual ETABS load pattern.
        merged["wall_mode"] = "LOAD_PATTERN_BEAM_CANDIDATE"
    if merged["wall_mode"] not in ("MANUAL", "LOAD_PATTERN_BEAM_CANDIDATE"):
        raise DriftScenarioError("WALL_MODE_INVALID")
    pattern = merged["wall_load_pattern"]
    if (not pattern or len(pattern) > 120 or pattern.strip() != pattern
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in pattern)):
        raise DriftScenarioError("WALL_LOAD_PATTERN_INVALID")
    _positive(merged["r"], "R", maximum="20")
    _positive(merged["i"], "I", maximum="5")
    _positive(merged["lambda"], "LAMBDA", maximum="10")
    _positive(merged["coverage_pct"], "COVERAGE", zero=True, maximum="100")
    _positive(merged["opening_pct"], "OPENING", zero=True, maximum="100")
    _positive(merged["wall_height_m"], "HEIGHT", maximum="30")
    _positive(merged["thickness_m"], "THICKNESS", maximum="2")
    _positive(merged["manual_wall_length_m"], "MANUAL_WALL_LENGTH", zero=True, maximum="100000")
    return merged


def _wall_candidates(report: Mapping[str, Any], opts: Mapping[str, str]) -> dict[str, Any]:
    """Optional exact source, never infer masonry solely from applied gravity load.

    The only used link is an exact load-pattern match on observed beam IDs.
    With unknown ETABS field names/units, candidacy remains unavailable.
    """
    base = {
        "load_pattern": opts["wall_load_pattern"], "source_status": "NO_AUTO_WALL_CENSUS",
        "candidate_beam_count": 0, "candidate_total_length_m": None,
        "assumed_net_face_area_m2": None,
        "assumed_wall_volume_m3": None, "candidate_beams": [],
        "interpretation": "Gravity load does not certify physical infill existence or type.",
    }
    manual_length = _positive(opts["manual_wall_length_m"],
                              "MANUAL_WALL_LENGTH", zero=True)
    def manual_inventory(reason: str) -> dict[str, Any]:
        if manual_length == 0:
            return {**base, "source_status": reason}
        area = (manual_length * _positive(opts["wall_height_m"], "HEIGHT")
                * _positive(opts["coverage_pct"], "COVERAGE", zero=True) / 100
                * (Decimal(1)-_positive(opts["opening_pct"], "OPENING", zero=True)/100))
        return {**base, "source_status": "USER_MANUAL_LENGTH_ASSUMPTION",
                "candidate_total_length_m": str(manual_length),
                "assumed_net_face_area_m2": str(area),
                "assumed_wall_volume_m3": str(area * _positive(opts["thickness_m"], "THICKNESS")),
                "interpretation": "Manual wall length, height, coverage and openings are scenario inputs, not ETABS-confirmed physical walls."}
    if opts["wall_mode"] != "LOAD_PATTERN_BEAM_CANDIDATE":
        return manual_inventory("USER_MANUAL_WALL_LENGTH_NOT_GIVEN")
    source = report.get("source_snapshot") or {}
    capture = source.get("vs06_wall_load_source")
    if not isinstance(capture, Mapping):
        return manual_inventory("LOAD_PATTERN_SOURCE_NOT_CAPTURED")
    try:
        _verify_generic_capture(capture)
    except (ValueError, TypeError) as exc:
        raise DriftScenarioError("LOAD_PATTERN_CAPTURE_INTEGRITY_FAILURE") from exc
    table = (capture.get("table_reads") or {}).get("Frame Loads - Distributed")
    if not isinstance(table, Mapping) or table.get("status") != "CAPTURED":
        return manual_inventory("LOAD_PATTERN_LOAD_TABLE_MISSING")
    fields = table.get("fields")
    meta = table.get("field_metadata") or {}
    if (not isinstance(fields, list) or meta.get("status") != "OK" or
            not {"UniqueName", "LoadPat"}.issubset(fields) or
            not {"UniqueName", "LoadPat"}.issubset(meta.get("field_keys") or [])):
        return manual_inventory("LOAD_PATTERN_FIELD_BINDING_UNREVIEWED")
    rows = table.get("rows")
    if not isinstance(rows, list) or table.get("row_count") != len(rows):
        raise DriftScenarioError("LOAD_PATTERN_ROW_CENSUS_CORRUPT")
    geometry = (source.get("geometry_capture") or {}).get("tables") or {}
    frames = ((geometry.get("FRAME_ASSIGNMENTS") or {}).get("rows")) or []
    beam_ids = {r.get("UniqueName") for r in frames if
                isinstance(r, Mapping) and str(r.get("Type", "")).casefold() == "beam"}
    ids = sorted({r.get("UniqueName") for r in rows
                  if isinstance(r, Mapping) and r.get("LoadPat") == opts["wall_load_pattern"]
                  and r.get("UniqueName") in beam_ids})
    # Full beam lengths require separately observed, typed geometric Length
    # metadata; load magnitude/distance alone never establishes wall height.
    lengths = (capture.get("table_reads") or {}).get("Beam Object Connectivity")
    length_by_id: dict[str, Decimal] = {}
    if isinstance(lengths, Mapping) and lengths.get("status") == "CAPTURED":
        lm = lengths.get("field_metadata") or {}
        if ({"UniqueName", "Length"}.issubset(lengths.get("fields") or []) and
                {"UniqueName", "Length"}.issubset(lm.get("field_keys") or []) and
                (lm.get("units_by_field") or {}).get("Length") == "m"):
            lr = lengths.get("rows")
            if isinstance(lr, list) and lengths.get("row_count") == len(lr):
                for item in lr:
                    if not isinstance(item, Mapping):
                        raise DriftScenarioError("BEAM_CONNECTIVITY_ROW_INVALID")
                    name = item.get("UniqueName")
                    if name in length_by_id:
                        raise DriftScenarioError("DUPLICATE_BEAM_LENGTH")
                    length_by_id[name] = _positive(str(item.get("Length")), "BEAM_LENGTH")
    complete = bool(ids) and all(x in length_by_id for x in ids)
    total = sum((length_by_id[x] for x in ids), Decimal(0)) if complete else None
    area = (total * _positive(opts["wall_height_m"], "HEIGHT")
            * _positive(opts["coverage_pct"], "COVERAGE", zero=True) / 100
            * (Decimal(1)-_positive(opts["opening_pct"], "OPENING", zero=True)/100)
            if total is not None else None)
    thickness = _positive(opts["thickness_m"], "THICKNESS")
    return {**base, "source_status": (
                 "LOAD_PATTERN_BEAM_CANDIDATE_GEOMETRY" if complete
                 else "LOAD_PATTERN_NO_MATCHING_BEAMS" if not ids
                 else "LOAD_PATTERN_BEAMS_OBSERVED_LENGTH_UNQUALIFIED"),
            "candidate_beam_count": len(ids),
            "candidate_total_length_m": str(total) if total is not None else None,
            "assumed_net_face_area_m2": str(area) if area is not None else None,
            "assumed_wall_volume_m3": str(area * thickness) if area is not None else None,
            "candidate_beams": ids,
            "interpretation": ("Assumed face area = complete candidate beam length × user wall height × coverage × (1-openings). "
                               "No proof of masonry location, infill continuity or B1 effective shear area.")}


def evaluate_drift_scenario(report: Mapping[str, Any], inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    opt = options(inputs)
    drift = report.get("story_drift")
    ready = report.get("vs06_effective_drift_readiness")
    if not isinstance(drift, Mapping) or not isinstance(ready, Mapping):
        raise DriftScenarioError("VERIFIED_VS06_C1_REPORT_REQUIRED")
    source_rows = drift.get("items")
    instances = ready.get("check_instances")
    if not isinstance(source_rows, list) or not isinstance(instances, list):
        raise DriftScenarioError("DRIFT_SOURCE_OR_INSTANCES_INVALID")
    index = {}
    for row in source_rows:
        key = (row.get("story"), row.get("case"), row.get("direction"))
        if key in index:
            raise DriftScenarioError("DUPLICATE_SOURCE_DRIFT_SLOT")
        index[key] = row
    lam = _positive(opt["lambda"], "LAMBDA")
    R, I = _positive(opt["r"], "R"), _positive(opt["i"], "I")
    kappa = Decimal(1) if opt["material"] == "RC" else Decimal("0.5")
    coef = Decimal("0.008") if opt["wall_type"] == "BRITTLE" else Decimal("0.016")
    limit = coef * kappa
    rows = []
    for instance in instances:
        story, case, direction = (instance["story"], instance["case"], instance["direction"])
        if CASES[direction] != case:
            raise DriftScenarioError("NOT_PRIMARY_DIRECTION")
        raw = index.get((story, case, direction))
        base = {"story": story, "case": case, "direction": direction,
                "check_instance_id": instance["check_instance_id"],
                "source_delta_mm": raw.get("etabs_derived_delta_mm") if raw else None,
                "story_height_m": raw.get("height_m") if raw else None,
                "effective_delta_mm": None, "lambda_effective_ratio": None,
                "limit": str(limit), "utilization_ratio": None,
                "conditional_numeric_condition": "SOURCE_DRIFT_MISSING" if not raw else "NOT_EVALUATED",
                "formal_compliance": "NOT_PROVEN"}
        if raw:
            h = _positive(raw["height_m"], "STORY_HEIGHT")
            delta = _positive(raw["etabs_derived_delta_m"], "ETABS_DELTA", zero=True)
            if delta:
                # The existing pure TBDY 4.34 kernel owns R/I and lambda math.
                # Use its conservative brittle branch for common arithmetic,
                # and select wall-type limit separately; flexible documentation
                # is never fabricated as a caller-supplied proof flag.
                k = eq_4_34_effective_drift(
                    reduced_relative_displacement_m=delta,
                    story_height_m=h, R=R, importance_factor=I,
                    lambda_dd3_dd2=lam, material=opt["material"],
                    wall_connection="ADHERED_BRITTLE")
                effective = Decimal(k["effective_relative_displacement_m"])
                value = Decimal(k["lambda_effective_drift_over_height"])
            else:
                effective = value = Decimal(0)
            utilization = value / limit
            base.update(
                effective_delta_mm=str(effective * 1000),
                lambda_effective_ratio=str(value),
                utilization_ratio=str(utilization),
                conditional_numeric_condition=(
                    "CONDITIONAL_WITHIN_LIMIT" if utilization <= 1 else "CONDITIONAL_EXCEEDS_LIMIT"))
        rows.append(base)
    if len(rows) != ready["expected_story_direction_instances"]:
        raise DriftScenarioError("DAG_STORY_DIRECTION_DENOMINATOR_CHANGED")
    if ready["dag_execution_authority"] != "DENIED" or ready["formal_compliance"] != "NOT_PROVEN":
        raise DriftScenarioError("DAG_AUTHORITY_VIOLATION")
    wall = _wall_candidates(report, opt)
    evaluated = sum(r["utilization_ratio"] is not None for r in rows)
    result = {
        "schema": SCHEMA,
        "run_id": report["run_id"],
        "input_sha256": report["source_provenance"]["input_sha256"],
        "check_id": "STORY_DRIFT",
        "code_refs": ["TBDY 2018 4.9.1.1 (4.32)", "4.9.1.2 (4.33)",
                      "4.9.1.3 (4.34a/b)", "4.9.1.4 lambda"],
        "scenario_input": opt,
        "scenario_assumptions": ["R", "I", "lambda", "wall_type", "material", "wall_coverage"],
        "source_numeric_count": evaluated,
        "expected_story_direction_count": len(rows),
        "missing_source_count": len(rows)-evaluated,
        "conditional_within_count": sum(x["conditional_numeric_condition"] == "CONDITIONAL_WITHIN_LIMIT" for x in rows),
        "conditional_exceeds_count": sum(x["conditional_numeric_condition"] == "CONDITIONAL_EXCEEDS_LIMIT" for x in rows),
        "limit": str(limit),
        "flexible_branch_capacity_accepted": (opt["wall_type"] == "FLEXIBLE" and opt["flexible_proven"] == "true"),
        "flexible_capacity_warning": ("FLEXIBLE_CONNECTION_TEST_PROOF_REQUIRED" if opt["wall_type"] == "FLEXIBLE" and opt["flexible_proven"] != "true" else None),
        "wall_candidate_inventory": wall,
        "rows": rows,
        "source_basis": "ETABS_STORY_DRIFTS_TIMES_HEIGHT_NOT_INDEPENDENT_EQ_4_32_MEMBER_DELTA",
        "result_kind": "CONDITIONAL_SENSITIVITY_SCENARIO",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "note": ("Conditional numeric calculation executed using the established Eq 4.34 kernel. "
                 "Results are not an authorized TBDY Pass/Fail; no independent spectrum/analysis generation and "
                 "physical member-end design displacements are proven."),
    }
    result["scenario_sha256"] = sha256((json.dumps(result, sort_keys=True,
            ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n").encode("utf-8")).hexdigest()
    return result
