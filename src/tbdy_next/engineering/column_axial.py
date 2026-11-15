"""Bind selected combinations, native frame forces and section limits to one run."""
from __future__ import annotations

from collections import Counter, defaultdict
from math import isfinite
from ntpath import normcase

from ..column_engine.demand_chain import classify_combinations
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.ts500_column import section_axial_limits_kn
from ..etabs_source_gateway_windows import field_schema, read_table
from ..frame_force_capture import (
    MAX_RESPONSE_COMBINATIONS, ForceSelectionRestoreError, capture_frame_forces,
)
from ..quick_checks import evaluate_geometry_capture
from ..vs05_d4_source_authority import _case_summary, _combo_source, _source_table
from .analysis_setup import bind_analysis_setup
from .design_assignments import ASSIGNED_DESIGN

CHECK = "COLUMN_AXIAL_COMPRESSION"
STAGE = "column-axial"
PREFERENCES = "Concrete Frame Design Preferences - TS 500-2000(R2018)"
STATIC_ROUTES = {"STATIC_LINEAR_ADD", "STATIC_NESTED_UNVERIFIED"}
ENVELOPE_ROUTES = {"RESPONSE_SPECTRUM_LINEAR_ADD", "ENVELOPE"}
CASE_TYPES = {"Linear Static": 1, "Response Spectrum": 4}
OPERATORS = {"Linear Add": 0, "Envelope": 1, "Absolute Add": 2, "SRSS": 3, "Range Add": 4}


def column_strength_plan(snapshot: dict, request: dict) -> dict:
    """Resolve names against the captured catalog, without granting load-role approval."""
    setup = bind_analysis_setup(snapshot)
    mode = request["combination_source"]
    names = (setup["strength_design_combinations"] or []
             if mode == "ETABS_STRENGTH" else request["combinations"])
    plan = {"source": mode, "base_run_id": request["base_run_id"],
            "base_input_sha256": request["base_input_sha256"],
            "combination_graph_sha256": setup["typed_graph_source_sha256"],
            "combinations": [{"name": name} for name in names], "blockers": []}
    if mode == ASSIGNED_DESIGN:
        assignment = request["design_assignment"]
        if sorted({name for group in assignment["groups"].values() for name in group}) != names:
            raise ValueError("COLUMN_AXIAL_ASSIGNMENTS_UNBOUND")
        plan["design_assignment"] = assignment
    filename = snapshot["capture_metadata"]["model_filename"]
    if normcase(filename) != normcase(request["model_filename"]):
        plan["blockers"].append("ACTIVE_MODEL_DIFFERS_FROM_SELECTED_RUN")
    if not setup["definition_coverage_known"]:
        plan["blockers"].append("COMBINATION_DEFINITIONS_UNVERIFIED")
    if (mode in {"SAVED_DEFAULTS", ASSIGNED_DESIGN}
            and setup["typed_graph_source_sha256"] != request["combination_graph_sha256"]):
        plan["blockers"].append("COMBINATION_DEFINITIONS_CHANGED_REFRESH_LIVE_RUN")
    if not names:
        plan["blockers"].append("NO_COLUMN_STRENGTH_COMBINATIONS")
    if len(names) > MAX_RESPONSE_COMBINATIONS:
        plan["blockers"].append("COLUMN_STRENGTH_SET_EXCEEDS_CAPTURE_LIMIT")
    missing = sorted(set(names) - set(setup["defined_combination_names"]))
    if missing:
        plan["blockers"].append("COMBINATION_NAMES_UNRESOLVED: " + ", ".join(missing))
    if plan["blockers"]:
        return plan

    tables = snapshot["vs04_basis_probe"]["table_reads"]
    cases = _case_summary(tables, require_key=True)
    graph = _combo_source(tables, cases, include_graph=True, require_key=True)["typed_graph"]
    case_defs = {name: {"status": "OBSERVED", "case_type": CASE_TYPES.get(case["type"], 99)}
                 for name, case in cases.items()}
    combo_defs = {
        name: {
            "status": "OBSERVED", "operator": OPERATORS[group["operator_etabs"]],
            "terms": [{"type": int(row["ref_type"] == "COMBO"), "name": row["ref"],
                       "factor": float(row["factor"])} for row in group["rows"]],
        } for name, group in graph.items()
    }
    routes = classify_combinations(case_defs, combo_defs)
    for record in plan["combinations"]:
        name = record["name"]
        route = routes[name]
        kind = route["classification"]
        semantics = "UNSUPPORTED_FORCE_STATE"
        if kind in STATIC_ROUTES:
            semantics = "STATIC_SIGNED_VECTOR"
        elif kind in ENVELOPE_ROUTES and set(route["case_types"]) <= {1, 4}:
            semantics = "SCALAR_COMPONENT_ENVELOPE"
        record.update(operator=graph[name]["operator_etabs"], classification=kind,
                      force_semantics=semantics, case_names=route["case_names"])
    return plan


def _columns(geometry: dict) -> list[dict]:
    return next((check["items"] for check in geometry["checks"]
                 if check["check_id"] == "column_rect_min"), [])


def capture_column_axial(sap, snapshot: dict, request: dict) -> dict:
    """Add an optional source branch to the combined ETABS capture."""
    plan = column_strength_plan(snapshot, request)
    captured = {"request": request}
    if plan["blockers"]:
        return captured
    geometry = evaluate_geometry_capture(snapshot["geometry_capture"])
    targets = tuple(row["element_id"] for row in _columns(geometry) if row["status"] != "NOT_APPLICABLE")
    try:
        db = sap.DatabaseTables
        preferences = read_table(db, PREFERENCES, max_rows=4)
        preferences["field_metadata"] = field_schema(db, PREFERENCES)
        captured["design_preferences"] = preferences
    except Exception as exc:
        captured["design_preferences_error"] = f"{type(exc).__name__}: {exc}"[:400]
    if not targets:
        return captured
    try:
        captured["force_source"] = capture_frame_forces(
            sap, members=targets, combinations=tuple(row["name"] for row in plan["combinations"]),
        )
    except ForceSelectionRestoreError:
        raise
    except Exception as exc:
        captured["force_source_error"] = f"{type(exc).__name__}: {exc}"[:400]
    return captured


def _gamma_c(source: dict) -> float:
    original = source.get("design_preferences")
    rows = _source_table({PREFERENCES: original}, PREFERENCES, {"GammaC"}, require_key=True)
    if len(rows) != 1 or original["field_metadata"]["units_by_field"].get("GammaC") != "":
        raise ValueError("TS500_CONCRETE_FACTOR_UNVERIFIED")
    gamma_c = float(rows[0]["GammaC"])
    if not isfinite(gamma_c) or gamma_c <= 0:
        raise ValueError("TS500_CONCRETE_FACTOR_INVALID")
    return gamma_c


def _verified_rowsets(feature: dict, names: set[str], members: set[str]) -> dict:
    source = feature.get("force_source")
    if source is None:
        return {}
    during = source["output_selection_during"]
    if (source.get("schema") != "tbdy.next.etabs-frame-force-source.v1"
            or source.get("api") != "Results.FrameForce" or source.get("item_type") != "ObjectElm"
            or source.get("units_code") != 6
            or source["output_selection_before"] != source["output_selection_after"]
            or any(during["cases"].values())
            or {key for key, selected in during["combos"].items() if selected} != names
            or set(source["rowsets"]) & set(source["errors"])
            or set(source["rowsets"]) | set(source["errors"]) != members):
        raise ValueError("FRAME_FORCE_SOURCE_CONTRACT_UNVERIFIED")
    return source["rowsets"]


def _critical_native_row(rows: list, expected_cuts: set, semantics: str) -> tuple:
    if semantics not in {"STATIC_SIGNED_VECTOR", "SCALAR_COMPONENT_ENVELOPE"}:
        raise ValueError("COMBINATION_FORCE_SEMANTICS_UNSUPPORTED")
    if not rows:
        raise ValueError("NO_NATIVE_FRAME_FORCE_ROWS_FOR_COMBINATION")
    per_cut = defaultdict(dict)
    for row in rows:
        cut, step = row[:4], row[5]
        if row[6] != 0 or step in per_cut[cut]:
            raise ValueError("UNSUPPORTED_OR_DUPLICATE_FRAME_FORCE_STEP")
        per_cut[cut][step] = row
    if set(per_cut) != expected_cuts:
        raise ValueError("NATIVE_CUT_COVERAGE_INCOMPLETE_FOR_COMBINATION")
    if semantics == "STATIC_SIGNED_VECTOR":
        if any(set(steps) not in ({"Single Value"}, {""}) for steps in per_cut.values()):
            raise ValueError("STATIC_SINGLE_VALUE_STEP_UNVERIFIED")
        return min(rows, key=lambda row: (row[7], row[:4]))
    if any(set(steps) != {"Min", "Max"} or steps["Min"][7] > steps["Max"][7]
           for steps in per_cut.values()):
        raise ValueError("SCALAR_AXIAL_MIN_MAX_PAIR_UNVERIFIED")
    return min((steps["Min"] for steps in per_cut.values()), key=lambda row: (row[7], row[:4]))


def _member_result(member: dict, plan: dict, rowset: dict | None, *,
                   fck: float | None, gamma_c: float | None, source_error: str | None) -> dict:
    identity = {key: member.get(key) for key in ("story", "element_id", "section", "material_name")}
    if member["status"] == "NOT_APPLICABLE":
        return {**identity, "status": "NOT_APPLICABLE", "reason": member.get("reason")}
    result = {**identity, "status": "BLOCKED", "governing": None,
              "evaluated_combinations": 0, "combination_checks": []}
    if plan["blockers"]:
        return {**result, "reason": plan["blockers"][0]}
    if (member.get("material_classification") != "RESOLVED_CONCRETE_USAGE"
            or member.get("section_design_difference") or member.get("analysis_section") != member["section"]):
        return {**result, "reason": member.get("reason") or "RECTANGULAR_ANALYSIS_AND_DESIGN_SECTION_UNVERIFIED"}
    if fck is None or gamma_c is None:
        return {**result, "reason": "CONCRETE_STRENGTH_OR_TS500_FACTOR_UNVERIFIED"}
    area = float(member["width_mm"]) * float(member["depth_mm"])
    limits = section_axial_limits_kn(fck_mpa=fck, fcd_mpa=fck / gamma_c, ac_mm2=area)
    result.update(fck_mpa=fck, fcd_mpa=fck / gamma_c, gross_area_mm2=area,
                  ts500_limit_kn=limits["ts500_eq_7_7_max_nd_kn"],
                  tbdy_seismic_reference_limit_kn=limits["tbdy_7_3_1_2_max_ndm_kn"])
    if rowset is None:
        return {**result, "reason": source_error or "NATIVE_FRAME_FORCE_UNAVAILABLE"}
    names = {row["name"] for row in plan["combinations"]}
    by_combo = defaultdict(list)
    for row in native_frame_force_rows(rowset, member["element_id"]):
        if row[4] not in names:
            raise ValueError("FRAME_FORCE_COMBINATION_OUTSIDE_REQUEST")
        by_combo[row[4]].append(row)
    cuts = {row[:4] for rows in by_combo.values() for row in rows}
    complete = []
    for combo in plan["combinations"]:
        name, semantics = combo["name"], combo["force_semantics"]
        check = {"combination": name, "force_semantics": semantics,
                 "force_row_count": len(by_combo[name])}
        try:
            row = _critical_native_row(by_combo[name], cuts, semantics)
            nd = max(0.0, -row[7])
            limit = result["ts500_limit_kn"]
            check.update(status="OUTSIDE_LIMIT" if nd > limit else "WITHIN_LIMIT",
                         object_station_m=row[1], analysis_element=row[2], element_station_m=row[3],
                         step_type=row[5], axial_force_kn=row[7], nd_kn=nd, ratio=nd / limit)
            complete.append(check)
        except ValueError as exc:
            check.update(status="BLOCKED", reason=str(exc))
        result["combination_checks"].append(check)
    result["evaluated_combinations"] = len(complete)
    if not complete:
        return {**result, "reason": "NO_EVALUABLE_SELECTED_COMBINATIONS"}
    governing = max(complete, key=lambda check: check["ratio"])
    partial = len(complete) != len(names)
    result.update(governing=governing, observed_exceedance=governing["status"] == "OUTSIDE_LIMIT",
                  status="PARTIAL" if partial else governing["status"])
    return result


def evaluate_column_axial(snapshot: dict, geometry: dict, extra: dict | None) -> dict:
    """Rebuild the bounded TS 500 axial check from the exact source behind its receipt."""
    feature = snapshot["column_axial"]
    plan = column_strength_plan(snapshot, feature["request"])
    members = _columns(geometry)
    targets = [row["element_id"] for row in members if row["status"] != "NOT_APPLICABLE"]
    rowsets = _verified_rowsets(feature, {c["name"] for c in plan["combinations"]}, set(targets))
    try:
        gamma_c = _gamma_c(feature)
    except ValueError:
        gamma_c = None
    material_items = next((check["items"] for check in (extra or {}).get("checks", [])
                           if check["check_id"] == "concrete_fck_25"), [])
    materials = {row["material_name"]: float(row["fck_mpa"]) for row in material_items
                 if row.get("fck_mpa") is not None}
    failures = (feature.get("force_source") or {}).get("errors", {})
    results = [_member_result(member, plan, rowsets.get(member["element_id"]),
                              fck=materials.get(member["material_name"]), gamma_c=gamma_c,
                              source_error=failures.get(member["element_id"], feature.get("force_source_error")))
               for member in members]
    completed = sum(row["status"] in {"WITHIN_LIMIT", "OUTSIDE_LIMIT"} for row in results)
    evaluated = sum(row.get("evaluated_combinations", 0) for row in results)
    status = ("NUMERICAL_COMPLETE" if completed and completed == len(targets)
              else "NUMERICAL_PARTIAL" if evaluated else "BLOCKED")
    return {
        "schema": "tbdy.next.column-axial-check.v1", "check_id": CHECK,
        "numerical_rule": "TS500:7.7:AXIAL_COMPRESSION_MAX:COLUMN:2000R2018",
        "status": status, "combination_plan": plan, "gamma_c": gamma_c,
        "expected_column_count": len(targets), "completed_column_count": completed,
        "expected_member_combination_count": len(targets) * len(plan["combinations"]),
        "evaluated_member_combination_count": evaluated,
        "native_force_row_count": sum(record["NumberResults"] for record in rowsets.values()),
        "column_status_counts": dict(sorted(Counter(row["status"] for row in results).items())),
        "observed_exceedance_count": sum(row.get("observed_exceedance", False) for row in results),
        "columns": results, "tbdy_seismic_axial_check": "DESIGN_COMBINATION_BASIS_UNVERIFIED",
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
    }
