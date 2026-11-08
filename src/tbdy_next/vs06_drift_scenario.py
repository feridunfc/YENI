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
    """Observed exact load pattern; beam loaded spans, not blind full lengths.

    Consume the failed DatabaseTables attempt and, when available, the
    read-only FrameObj.GetLoadDistributed probe from the SAME generic gateway.
    Never treat an API failure as proof of an unloaded beam or absent wall.
    """
    base = {
        "load_pattern": opts["wall_load_pattern"],
        "source_status": "NO_AUTO_WALL_CENSUS",
        "source_method": None, "original_distributed_table_status": None,
        "candidate_beam_count": 0, "candidate_total_length_m": None,
        "assumed_net_face_area_m2": None, "assumed_wall_volume_m3": None,
        "candidate_beams": [], "candidate_spans": [],
        "source_census_complete": False, "source_load_rows_considered": 0,
        "source_load_rows_matched": 0, "unresolved_beam_count": None,
        "interpretation": "Wall gravity loading is not physical masonry proof.",
    }
    manual_length = _positive(opts["manual_wall_length_m"], "MANUAL_LENGTH", zero=True)
    height = _positive(opts["wall_height_m"], "WALL_HEIGHT")
    coverage = _positive(opts["coverage_pct"], "COVERAGE", zero=True) / 100
    openings = _positive(opts["opening_pct"], "OPENING", zero=True) / 100
    thickness = _positive(opts["thickness_m"], "THICKNESS")
    def geometry(out: dict, length: Decimal) -> dict:
        area = length * height * coverage * (1-openings)
        return {**out, "candidate_total_length_m": str(length),
                "assumed_net_face_area_m2": str(area),
                "assumed_wall_volume_m3": str(area*thickness)}
    def manual(reason: str) -> dict:
        if manual_length == 0:
            return {**base, "source_status": reason}
        return geometry({
            **base, "source_status": "USER_MANUAL_LENGTH_ASSUMPTION",
            "interpretation": "Explicit user dimensions, not ETABS wall assignment proof.",
        }, manual_length)
    if opts["wall_mode"] != "LOAD_PATTERN_BEAM_CANDIDATE":
        return manual("USER_MANUAL_WALL_LENGTH_NOT_GIVEN")
    snapshot = report.get("source_snapshot") or {}
    capture = snapshot.get("vs06_wall_load_source")
    if not isinstance(capture, Mapping):
        return manual("LOAD_PATTERN_SOURCE_NOT_CAPTURED")
    try:
        _verify_generic_capture(capture)
    except (ValueError, TypeError) as exc:
        raise DriftScenarioError("LOAD_PATTERN_CAPTURE_INTEGRITY_FAILURE") from exc
    reads = capture.get("table_reads") or {}
    beam_table = reads.get("Beam Object Connectivity")
    if (not isinstance(beam_table, Mapping)
            or beam_table.get("status") != "CAPTURED"
            or not {"UniqueName", "Story", "Length"}.issubset(beam_table.get("fields") or [])
            or ((beam_table.get("field_metadata") or {}).get("units_by_field") or {}).get("Length") != "m"
            or not isinstance(beam_table.get("rows"), list)
            or beam_table.get("row_count") != len(beam_table["rows"])):
        return manual("BEAM_CONNECTIVITY_TYPED_GEOMETRY_MISSING")
    beams = {}
    for row in beam_table["rows"]:
        name = row.get("UniqueName")
        if not isinstance(name, str) or not name or name in beams:
            raise DriftScenarioError("DUPLICATE_OR_EMPTY_BEAM_ID")
        beams[name] = {
            "length": _positive(str(row.get("Length")), "BEAM_LENGTH"),
            "story": row.get("Story"),
        }

    distributed = reads.get("Frame Loads Assignments - Distributed")
    db_status = (distributed.get("status") if isinstance(distributed, Mapping)
                 else "NOT_REQUESTED")
    probe = capture.get("frame_load_object_probe")
    if isinstance(distributed, Mapping) and db_status == "CAPTURED":
        metadata = distributed.get("field_metadata") or {}
        keys = {"UniqueName", "LoadPattern", "RelDistA", "RelDistB", "LoadType"}
        if (not keys.issubset(distributed.get("fields") or [])
                or not keys.issubset(metadata.get("field_keys") or [])
                or metadata.get("status") != "OK"
                or not isinstance(distributed.get("rows"), list)
                or distributed.get("row_count") != len(distributed["rows"])):
            return manual("ETABS_DISTRIBUTED_LOAD_FIELDS_NOT_RECONCILED")
        rows = distributed["rows"]
        method, complete, unresolved = ("DatabaseTables.GetTableForDisplayArray", True, 0)
    elif isinstance(probe, Mapping):
        if (probe.get("schema") != "tbdy.next.etabs.frame-object-distributed-load-probe.v1"
                or probe.get("source_method") != "SapModel.FrameObj.GetLoadDistributed"
                or probe.get("model_units_code") != 6
                or probe.get("status") not in ("CAPTURED", "SOURCE_PARTIAL")
                or probe.get("beam_count") != len(beams)
                or not isinstance(probe.get("rows"), list)
                or probe.get("load_row_count") != len(probe["rows"])
                or probe.get("successful_beam_count", -1)
                   + probe.get("unresolved_beam_count", -1) != len(beams)):
            raise DriftScenarioError("OBJECT_DISTRIBUTED_LOAD_PROBE_CONTRACT_INVALID")
        rows = probe["rows"]
        method = probe["source_method"]
        complete = probe["status"] == "CAPTURED"
        unresolved = probe["unresolved_beam_count"]
    else:
        return manual("LOAD_PATTERN_DB_FAILED_OBJECT_PROBE_NOT_CAPTURED"
                      if db_status == "CAPTURE_ERROR"
                      else "LOAD_PATTERN_LOAD_TABLE_MISSING")

    spans: dict[str, list[tuple[Decimal, Decimal]]] = {}
    matched = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise DriftScenarioError("DISTRIBUTED_LOAD_ROW_NOT_OBJECT")
        if row.get("LoadPattern") != opts["wall_load_pattern"]:
            continue
        kind = row.get("LoadType", row.get("MyType"))
        if kind not in ("Force", "1", 1):
            continue
        name = row.get("UniqueName")
        if name not in beams:
            continue
        try:
            a, b = Decimal(str(row.get("RelDistA"))), Decimal(str(row.get("RelDistB")))
        except (InvalidOperation, TypeError, ValueError):
            raise DriftScenarioError("DISTRIBUTED_LOAD_SPAN_MISSING") from None
        if not a.is_finite() or not b.is_finite() or a < 0 or b > 1 or a > b:
            raise DriftScenarioError("DISTRIBUTED_LOAD_SPAN_INVALID")
        if a < b:
            spans.setdefault(name, []).append((a, b))
            matched += 1

    items = []
    total = Decimal(0)
    for name in sorted(spans):
        combined: list[list[Decimal]] = []
        for a, b in sorted(spans[name]):
            if combined and a <= combined[-1][1]:
                combined[-1][1] = max(b, combined[-1][1])
            else:
                combined.append([a, b])
        fraction = sum((end-start for start, end in combined), Decimal(0))
        length = beams[name]["length"] * fraction
        total += length
        items.append({
            "beam_id": name, "story": beams[name]["story"],
            "beam_length_m": str(beams[name]["length"]),
            "loaded_fraction": str(fraction), "candidate_loaded_length_m": str(length),
            "interval_count": len(combined),
        })
    result = {
        **base,
        "source_status": (
            "LOAD_PATTERN_OBSERVED_SOURCE_COMPLETE" if complete and items
            else "LOAD_PATTERN_NOT_FOUND_IN_COMPLETE_CENSUS" if complete
            else "LOAD_PATTERN_OBSERVED_PARTIAL_OBJECT_PROBE" if items
            else "LOAD_PATTERN_OBJECT_PROBE_PARTIAL_NO_OBSERVATIONS"),
        "source_method": method, "original_distributed_table_status": db_status,
        "candidate_beam_count": len(items), "candidate_beams": [r["beam_id"] for r in items],
        "candidate_spans": items, "source_census_complete": complete,
        "source_load_rows_considered": len(rows), "source_load_rows_matched": matched,
        "unresolved_beam_count": unresolved,
        "interpretation": (
            "Only actually loaded beam intervals are used, with overlapping "
            "line loads unioned once. Wall height and masonry applicability "
            "remain user engineering assumptions."),
    }
    return geometry(result, total) if items else result

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
