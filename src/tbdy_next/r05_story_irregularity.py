"""R05 — archived single-run story, A1/B1/B2 and source-drift reconciliation.

No COM. Reuse the existing independently testable VS03, VS05–VS07
calculators. Account for missing source slots without inventing an absent
physical story, normative PASS, displacement concurrence, or generation joins.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

from .story_drift_binding import bind_story_drift
from .story_slot_ledger import build_story_slot_ledger
from .story_physical_source import review_story_physical_source
from .physical_story_scope import review_physical_story_scope
from .effective_drift_readiness import review_effective_drift_readiness
from .next_checks import evaluate_next_capture
from .soft_story_b2 import bind_soft_story_b2
from .b1_source_bridge import evaluate_b1_sources
from .story_delta import story_heights

SCHEMA = "tbdy.next.r05-offline-story-irregularity-ledger.v1"
REPORT_SCHEMA = "tbdy.next.complete.engineering.report.v1"
CASE_DIRECTION = {"RSX": "X", "RSY": "Y"}
RULES = {"STORY_DRIFT", "A1_X", "A1_Y", "WEAK_STORY_B1", "SOFT_STORY_B2"}


class R05EvidenceError(ValueError):
    """Contradictory source, legacy arithmetic or unapproved promotion."""


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise R05EvidenceError(code)


def _equal_numeric(a: Any, b: Any, code: str) -> None:
    try:
        x, y = Decimal(str(a)), Decimal(str(b))
        _require(x.is_finite() and y.is_finite() and x == y, code)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise R05EvidenceError(code) from exc


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _blocked(reason: str, source_sha: str, run_id: str | None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA, "status": "BLOCKED_REPLAY",
        "run_id": run_id, "source_file_sha256": source_sha,
        "reason_codes": [reason], "rule_scope": sorted(RULES),
        "normative_checks_executed": 0, "design_demand_authority": "DENIED",
        "analysis_generation_proven": False,
        "full_building_applicability_proven": False,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
    out["result_sha256"] = _digest(out)
    return out


def _reconcile_a1(recomputed: Mapping[str, Any], stored: Mapping[str, Any],
                  declared: set[str]) -> dict[str, Any]:
    _require(recomputed.get("status") == "NUMERICAL_CLASSIFIED"
             and recomputed.get("formal_compliance") == "NOT_PROVEN",
             "A1_CORE_SOURCE_NOT_CLASSIFIED")
    old = {c["check_id"]: c for c in stored.get("checks", [])
           if c.get("check_id") in ("a1_torsion_x", "a1_torsion_y")}
    new = {c["check_id"]: c for c in recomputed.get("checks", [])
           if c.get("check_id") in ("a1_torsion_x", "a1_torsion_y")}
    _require(set(old) == set(new) == {"a1_torsion_x", "a1_torsion_y"},
             "A1_CHECK_SOURCE_MISSING")
    entries: list[dict[str, Any]] = []
    observed: set[tuple[str, str]] = set()
    for direction in ("X", "Y"):
        check_id = "a1_torsion_x" if direction == "X" else "a1_torsion_y"
        current, historical = new[check_id], old[check_id]
        _require(current.get("status") == historical.get("status") == "A1_CLASSIFIED",
                 "A1_RECORDED_STATUS_CONFLICT")
        now_rows = current.get("items", [])
        old_rows = historical.get("items", [])
        _require(isinstance(now_rows, list) and isinstance(old_rows, list),
                 "A1_ROW_SHAPE_INVALID")
        def indexed(rows: list[dict]) -> dict[str, dict]:
            data = {}
            for row in rows:
                story = row.get("story")
                _require(isinstance(story, str) and story in declared
                         and row.get("direction") == direction and story not in data,
                         "A1_DUPLICATE_OR_FOREIGN_STORY")
                data[story] = row
            return data
        nr, hr = indexed(now_rows), indexed(old_rows)
        _require(set(nr) == set(hr), "A1_SOURCE_POPULATION_MISMATCH")
        for story, row in nr.items():
            old_row = hr[story]
            for k in ("status", "source_case", "direction"):
                _require(row.get(k) == old_row.get(k),
                         "A1_SOURCE_RESULT_CONFLICT:" + k)
            _require(row.get("status") in ("A1_OBSERVED", "A1_NOT_OBSERVED"),
                     "A1_UNSUPPORTED_SOURCE_STATUS")
            _equal_numeric(row.get("eta_bi"), old_row.get("eta_bi"),
                           "A1_NUMERICAL_REPLAY_CONFLICT")
            observed.add((story, direction))
            entries.append({
                "story": story, "direction": direction, "case": "RSX" if direction == "X" else "RSY",
                "source_status": row["status"], "eta_bi": row["eta_bi"],
                "interpretation": "SOURCE_NUMERICAL_A1_ONLY",
                "normative_status": "NOT_PROVEN",
                "physical_applicability": "UNKNOWN",
            })
    expected = {(story, d) for story in declared for d in ("X", "Y")}
    _require(observed <= expected, "A1_OBSERVED_OUTSIDE_DECLARED_STORIES")
    for story, direction in sorted(expected - observed):
        entries.append({
            "story": story, "direction": direction,
            "case": "RSX" if direction == "X" else "RSY",
            "source_status": "SOURCE_MISSING",
            "eta_bi": None, "interpretation": "NO_A1_SOURCE_ROW_FOR_DECLARED_STORY",
            "normative_status": "NOT_PROVEN",
            "physical_applicability": "UNKNOWN",
        })
    return {
        "expected_story_direction_instances": len(expected),
        "observed_source_instances": len(observed),
        "source_missing_instances": len(expected - observed),
        "rows": sorted(entries, key=lambda x: (x["story"], x["direction"])),
        "normative_classification": "NOT_PROVEN",
    }


def _reconcile_b2(new: Mapping[str, Any], old: Mapping[str, Any],
                  source_sha: str, declared: set[str]) -> dict[str, Any]:
    _require(new.get("source_payload_sha256") == old.get("source_payload_sha256")
             == source_sha, "B2_SOURCE_PAYLOAD_CONFLICT")
    _require(new.get("formal_compliance") == old.get("formal_compliance") == "NOT_PROVEN"
             and new.get("engineering_release") == old.get("engineering_release") == "NOT_READY",
             "B2_UNAUTHORIZED_FORMAL_PROMOTION")
    for key in ("expected_count", "evaluated_count", "threshold_exceeded_comparisons"):
        _require(new.get(key) == old.get(key), "B2_RECORDED_COUNT_MISMATCH:" + key)
    for key in ("expected", "resolved", "missing", "invalid"):
        _require(new.get("source_coverage", {}).get(key) ==
                 old.get("source_coverage", {}).get(key),
                 "B2_SOURCE_COVERAGE_MISMATCH:" + key)
    for key in ("expected", "resolved", "unresolved", "complete"):
        _require(new.get("comparison_coverage", {}).get(key) ==
                 old.get("comparison_coverage", {}).get(key),
                 "B2_COMPARISON_COVERAGE_MISMATCH:" + key)
    _require(new.get("normative_b2_classification") == "NOT_PROVEN"
             and new.get("numerical_pass_issued") is False,
             "B2_NORMATIVE_VERDICT_UNAUTHORIZED")
    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for row in new.get("source_rows", []):
        story, direction = row.get("story"), row.get("direction")
        _require(story in declared and direction in ("X", "Y")
                 and (story, direction) not in seen,
                 "B2_DUPLICATE_OR_FOREIGN_STORY_DIRECTION")
        seen.add((story, direction))
        rows.append({"story": story, "direction": direction,
                     "case": "RSX" if direction == "X" else "RSY",
                     "source_status": row.get("status"),
                     "average_drift_m": row.get("average_drift_m"),
                     "normative_status": "NOT_PROVEN"})
    expected = {(s, d) for s in declared for d in ("X", "Y")}
    _require(seen == expected, "B2_DECLARED_STORY_CENSUS_MISMATCH")
    return {
        "source_coverage": dict(new["source_coverage"]),
        "comparison_coverage": dict(new["comparison_coverage"]),
        "threshold_exceeded_comparisons": new["threshold_exceeded_comparisons"],
        "conditional_scenario_only": True,
        "rows": sorted(rows, key=lambda x: (x["story"], x["direction"])),
        "normative_classification": "NOT_PROVEN",
    }


def _reconcile_b1(new: Mapping[str, Any], old: Mapping[str, Any],
                  geometry: Mapping[str, Any], loads: Mapping[str, Any],
                  declared: set[str]) -> dict[str, Any]:
    _require(new.get("formal_compliance") == old.get("formal_compliance") == "NOT_PROVEN",
             "B1_UNAUTHORIZED_COMPLIANCE")
    for key, source in (("geometry_capture_sha256", geometry),
                        ("wall_load_capture_sha256", loads)):
        _require(new.get("provenance", {}).get(key) ==
                 old.get("provenance", {}).get(key) == source.get("payload_sha256"),
                 "B1_SOURCE_PROVENANCE_MISMATCH:" + key)
    a, b = new.get("b1_numerical", {}), old.get("b1_numerical", {})
    for key in ("input_stories", "active_physical_stories",
                "expected_story_direction_pairs", "computed_story_direction_pairs"):
        _require(a.get(key) == b.get(key), "B1_NUMERIC_COUNT_MISMATCH:" + key)
    _equal_numeric(a.get("eta_ci_min"), b.get("eta_ci_min"),
                   "B1_ETA_MIN_REPLAY_MISMATCH")
    _require(set(a.get("inactive_stories", [])) <= declared
             and set(b.get("inactive_stories", [])) == set(a.get("inactive_stories", [])),
             "B1_CONDITIONAL_STORY_SCOPE_CHANGED")
    _require(a.get("formal_compliance") == "NOT_PROVEN"
             and a.get("physical_census_approved") is False,
             "B1_PHYSICAL_STORY_APPROVAL_NOT_PROVEN")
    return {
        "input_stories": a["input_stories"],
        "conditional_active_stories": a["active_physical_stories"],
        "candidate_inactive_stories": list(a["inactive_stories"]),
        "conditional_pair_count": a["computed_story_direction_pairs"],
        "conditional_eta_ci_min": a["eta_ci_min"],
        "conditional_inactive_is_not_code_not_applicable": True,
        "infill_weight_thickness_opening_and_wall_type_are_assumptions": True,
        "formal_compliance": "NOT_PROVEN",
    }


def review_r05_story_irregularities(
    report: Mapping[str, Any], source_file_sha256: str,
    *, catalog: Mapping[str, Any], r04_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = report.get("run_id") if isinstance(report, Mapping) else None
    try:
        _require(isinstance(report, Mapping) and
                 report.get("schema") == REPORT_SCHEMA and
                 report.get("formal_compliance") == "NOT_PROVEN" and
                 report.get("engineering_release") == "NOT_READY",
                 "HISTORICAL_REPORT_SCOPE_INVALID")
        _require(isinstance(run_id, str) and run_id.startswith("RUN-"),
                 "RUN_ID_INVALID")
        source = report.get("source_snapshot")
        _require(isinstance(source, Mapping), "ORIGINAL_SOURCE_SNAPSHOT_MISSING")
        generic = source.get("vs05_delta_source")
        _require(isinstance(generic, Mapping) and
                 source.get("source_mode") == "LIVE_ETABS" and
                 generic.get("analysis_generation_proven") is False,
                 "GENERIC_SOURCE_MODE_OR_GENERATION_INVALID")
        # Only one exact sealed snapshot is used for drift / B2 / physical
        # source review. Other captured tables must be from this full report,
        # but same model path is NOT proof of one analysis generation.
        drift = bind_story_drift(generic)
        _require(drift.get("execution_status") == "EXECUTED_SOURCE_NUMERICAL"
                 and drift.get("formal_compliance") == "NOT_PROVEN"
                 and drift.get("engineering_release") == "NOT_READY",
                 "STORY_DRIFT_SOURCE_REPLAY_BLOCKED")
        stored_drift = report.get("story_drift")
        _require(isinstance(stored_drift, Mapping) and
                 dict(stored_drift) == drift, "STORY_DRIFT_ARCHIVE_REPLAY_MISMATCH")
        ledger = build_story_slot_ledger(generic, drift)
        _require(report.get("vs06_story_slot_ledger") == ledger,
                 "STORY_SLOT_LEDGER_ARCHIVE_MISMATCH")
        physical = review_story_physical_source(generic, drift, ledger)
        _require(report.get("vs06_physical_source_review") == physical,
                 "PHYSICAL_PARTIAL_SOURCE_REPLAY_MISMATCH")
        scope = review_physical_story_scope(generic)
        # Observed columns are a *partial* census of vertical elements,
        # NOT a complete frame/area/null/mesh-object census.
        _require(physical.get("full_physical_story_census_proven") is False
                 and physical.get("signed_concurrent_spectrum_design_pairs_proven") == 0,
                 "PHYSICAL_OR_CONCURRENCE_FALSE_PROMOTION")
        effective = review_effective_drift_readiness(generic, drift, ledger,
                                                      physical, catalog)
        _require(report.get("vs06_effective_drift_readiness") == effective,
                 "EFFECTIVE_DRIFT_READINESS_REPLAY_MISMATCH")
        _require(effective.get("formula_executed_count") == 0
                 and effective.get("candidate_fcr_pass") == 0,
                 "EFFECTIVE_DRIFT_FALSE_CODE_PASS")
        defined = set(story_heights(generic))
        _require(len(defined) * 4 == ledger["expected_slot_count"],
                 "DECLARED_STORY_SLOT_DENOMINATOR_CHANGED")
        _require(len(defined) * 2 == effective["expected_story_direction_instances"],
                 "EFFECTIVE_DRIFT_PRIMARY_DENOMINATOR_CHANGED")
        # Recalculate A1 using the existing VS03 checker and its raw
        # geometry, then add the declared-but-missing story/direction rows.
        a1 = _reconcile_a1(
            evaluate_next_capture(source.get("next_capture"),
                                  source.get("geometry_capture")),
            report.get("vs03", {}), defined)
        b2_new = bind_soft_story_b2(generic, physical_scope=scope)
        b2 = _reconcile_b2(b2_new, report.get("soft_story_b2", {}),
                           generic["payload_sha256"], defined)
        geo, load = (source.get("vs06_b1_geometry_source"),
                     source.get("vs06_wall_load_source"))
        _require(isinstance(geo, Mapping) and isinstance(load, Mapping),
                 "B1_SAME_REPORT_CAPTURE_MISSING")
        b1_new = evaluate_b1_sources(geo, load, physical_scope=scope,
                                     physical_scope_source=generic)
        b1 = _reconcile_b1(b1_new, report.get("vs06_b1_result", {}),
                            geo, load, defined)

        if r04_receipt is not None:
            _require(isinstance(r04_receipt, Mapping)
                     and r04_receipt.get("schema") ==
                         "tbdy.next.r04-historical-modal-spectral-replay.v1"
                     and r04_receipt.get("run_id") == run_id
                     and r04_receipt.get("source_file_sha256") == source_file_sha256
                     and r04_receipt.get("engineering_release") == "NOT_READY"
                     and r04_receipt.get("status") ==
                         "HISTORICAL_SOURCE_NUMERIC_REPLAY_RECONCILED",
                     "R04_RECEIPT_CANNOT_BE_JOINED")
        missing = [dict(slot) for slot in ledger["slots"]
                   if slot["source_status"] == "SOURCE_MISSING"]
        unknown_stories = [r["story"] for r in scope.get("stories", [])
                           if r["applicability"] == "UNKNOWN"]
        # Even if a full inventory later exists, re-evaluate the exact
        # derived source before allowing NOT_APPLICABLE to affect a check.
        status = "SOURCE_SCENARIOS_REPLAYED_PARTIAL_PHYSICAL_AUTHORITY"
        result = {
            "schema": SCHEMA, "status": status,
            "run_id": run_id, "source_file_sha256": source_file_sha256,
            "generic_source_sha256": generic["payload_sha256"],
            "drift_slot_ledger_sha256": ledger["ledger_sha256"],
            "physical_review_sha256": physical["review_sha256"],
            "effective_drift_readiness_sha256": effective["readiness_sha256"],
            "declared_stories": sorted(defined), "declared_story_count": len(defined),
            "physical_inventory_status": scope.get("status"),
            "complete_physical_census_proven": scope.get("source_inventory_complete") is True,
            "unknown_physical_story_applicability": sorted(unknown_stories),
            "source_drift": {
                "expected_slot_count": ledger["expected_slot_count"],
                "accounted_slot_count": ledger["accounted_slot_count"],
                "observed_numeric_slots": ledger["source_numeric_count"],
                "missing_source_slots": ledger["source_missing_count"],
                "slots": ledger["slots"],
                "primary_direction_check_instances": effective["candidate_fcr_expected"],
                "primary_direction_not_proven": effective["candidate_fcr_not_proven"],
                "normative_formula_execution_count": 0,
            },
            "partial_physical_observations": {
                "observed_columns": physical["observed_column_count"],
                "linked_column_endpoints": physical["endpoint_linked_column_count"],
                "point_objects_observed": physical["observed_point_object_count"],
                "complete_all_object_inventory_proven": False,
                "independent_spectrum_extrema_not_concurrent": True,
            },
            "a1_source_only": a1, "b1_conditional": b1,
            "b2_conditional": b2,
            "missing_source_slot_details": missing,
            "r04_historical_report_relation": (
                "SAME_PINNED_REPORT_REPLAY_ONLY" if r04_receipt is not None
                else "R04_EXECUTION_NOT_SUPPLIED"),
            "missing_authorities": [
                "COMPLETE_FRAME_AREA_JOINT_NULL_MESH_CENSUS",
                "APPROVED_BASEMENT_AND_EMPTY_STORY_APPLICABILITY",
                "ANALYSIS_GENERATION_AND_ECCENTRICITY_FIVE_PERCENT",
                "EFFECTIVE_DRIFT_R_I_DD2_DD3_LAMBDA_WALL_BASIS",
                "A1_DUAL_ECCENTRICITY_RESPONSE_APPLICABILITY",
                "B1_ACTUAL_INFILL_PANEL_STIFFNESS_AND_OPENINGS",
                "B2_ETABS_AVG_DRIFT_CODE_EQUIVALENCE",
                "SIGNED_CONCURRENT_SPECTRAL_DESIGN_DISPLACEMENTS",
            ],
            "normative_checks_executed": 0,
            "design_demand_authority": "DENIED",
            "analysis_generation_proven": False,
            "full_building_applicability_proven": False,
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
        }
        _require(len(ledger["slots"]) == ledger["accounted_slot_count"]
                 and ledger["source_missing_count"] + ledger["source_numeric_count"]
                 == ledger["expected_slot_count"],
                 "STORY_SLOT_SUM_NOT_RECONCILED")
        result["result_sha256"] = _digest(result)
        return result
    except (R05EvidenceError, KeyError, ValueError, TypeError,
            ArithmeticError, AttributeError) as exc:
        return _blocked(str(exc), source_file_sha256, run_id)
