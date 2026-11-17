"""Permanent source-bound R07 / R08 / R09 engine service.

Research scripts acquire receipts; this module owns the repeatable verification
and calculation path. It never connects to COM, alters an EDB, or upgrades a
scenario to engineering approval. Inputs are private receipt files, not Git data.
"""
from __future__ import annotations

import json
import math
import ntpath
from pathlib import Path
from typing import Any, Mapping

from tbdy_next.column_engine.csi_geometry import local_dimensions
from tbdy_next.column_engine.native_archive import digest
from tbdy_next.column_engine.section_capacity import Bar, Material, Section, solver
from tbdy_next.column_engine.ts500_column import minimum_eccentricity_mm, rectangle_properties
from tbdy_next.engineering.column_gates import evaluate_column_p0_gates, match_station_with_tolerance
from tbdy_next.quick_checks import _rows as geometry_rows

LIVE = "tbdy.next.r07-r09.live-readonly.v1"
COMBO = "tbdy.next.r07.gravult-combo-live-capture.v1"
COMBO_RUN = "tbdy.next.r07.gravult-combo-pmm-run-result.v1"
LC_RUN = "tbdy.next.r07-r09.one-column-run-result.v1"
GATEWAY = "tbdy.next.etabs.generic-source-capture.v1"
FORCES = ("P", "V2", "V3", "T", "M2", "M3")
IDENTITY = ("Obj", "Elm", "ObjSta", "ElmSta", "LoadCase", "StepType", "StepNum")
GRAV_ULT = (
    ("LC_DL", "1.4"), ("LC_SDL", "1.4"), ("LC_WDL", "1.4"),
    ("LC_LL", "1.6"), ("LC_DDL", "1.6"), ("LC_S", "1.6"),
)


class LiveEvidenceError(ValueError):
    """A mandatory provenance, numeric, or engineering basis is missing."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise LiveEvidenceError(reason)


def number(value, name: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value), "INVALID_NUMBER:" + name)
    return float(value)


def text_number(value, name: str) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise LiveEvidenceError("INVALID_SOURCE_NUMBER:" + name) from exc
    require(math.isfinite(val), "INVALID_SOURCE_NUMBER:" + name)
    return val


def sealed(obj: Mapping, sha_field: str) -> None:
    require(isinstance(obj, dict), "RECEIPT_NOT_OBJECT")
    body = dict(obj)
    claimed = body.pop(sha_field, None)
    require(isinstance(claimed, str) and len(claimed) == 64
            and digest(body) == claimed, "RECEIPT_SHA_MISMATCH:" + sha_field)


def table(gateway: Mapping, key: str) -> list:
    require(gateway.get("schema") == GATEWAY
            and gateway.get("status") == "CAPTURED", "GATEWAY_UNVERIFIED")
    t = gateway.get("table_reads", {}).get(key, {})
    require(t.get("status") == "CAPTURED"
            and t.get("field_metadata", {}).get("status") == "OK"
            and isinstance(t.get("rows"), list)
            and t.get("row_count") == len(t["rows"]), "TABLE_INCOMPLETE:" + key)
    return t["rows"]


def unique(rows: list, key: str, wanted: str) -> dict:
    matches = [r for r in rows if r.get(key) == wanted]
    require(len(matches) == 1, "ROW_AMBIGUOUS:" + key + ":" + wanted)
    return matches[0]


def _gateway_ready(g: Mapping, path: str) -> None:
    sealed(g, "payload_sha256")
    require(g.get("model") == path and g.get("source_only") is True
            and g.get("model_locked") is True and g.get("model_units_code") == 6
            and g.get("model_units_unchanged") is True
            and g.get("case_selection_before") == g.get("case_selection_after")
            and g.get("selection_restored") is True,
            "GATEWAY_MODEL_OR_SELECTION_INVALID")


def _profile(live: Mapping, member: str) -> tuple:
    g = live["gateway_capture"]
    col = unique(table(g, "Column Object Connectivity"), "UniqueName", member)
    assign = unique(table(g, "Frame Assignments - Section Properties"), "UniqueName", member)
    require(col.get("Story") == assign.get("Story")
            and assign.get("Shape") == "Concrete Rectangular",
            "COLUMN_PHYSICAL_ASSIGNMENT_INVALID")
    rect = unique(table(g, "Frame Section Property Definitions - Concrete Rectangular"),
                  "Name", assign["SectProp"])
    require(rect.get("DesignType") == "Column", "FRAME_SECTION_NOT_COLUMN")
    return col, assign, rect


def _geometry(live: Mapping, geom: Mapping, member: str, stations: list[float]) -> dict:
    _gateway_ready(geom, live["model_filename"])
    require(geom.get("analysis_generation_proven") is False,
            "UNPROVEN_GENERATION_MISREPRESENTED")
    col, assign, rect = _profile(live, member)
    offsets = unique(table(geom, "Frame Assignments - End Length Offsets"),
                     "UniqueName", member)
    axes = unique(table(geom, "Frame Assignments - Local Axes"),
                  "UniqueName", member)
    points = table(geom, "Point Object Connectivity")
    pi = unique(points, "UniqueName", col["UniquePtI"])
    pj = unique(points, "UniqueName", col["UniquePtJ"])
    xi = [text_number(pi[a], a) for a in ("X", "Y", "Z")]
    xj = [text_number(pj[a], a) for a in ("X", "Y", "Z")]
    length = math.dist(xi, xj)
    require(abs(length - text_number(col["Length"], "Length")) <= 1e-7,
            "POINT_LENGTH_MISMATCH")
    oi, oj = (text_number(offsets[k], k) for k in ("OffsetI", "OffsetJ"))
    require(oi >= 0 and oj >= 0 and oi + oj < length, "INVALID_END_OFFSETS")
    span = length - oi - oj
    require(stations and abs(min(stations)) <= 1e-7
            and abs(max(stations) - span) <= 1e-7,
            "OUTPUT_SPAN_OFFSET_MISMATCH")
    require(assign.get("SectProp") == rect.get("Name"), "SECTION_NAME_MISMATCH")
    t2 = text_number(rect["t2"], "t2") * 1000
    t3 = text_number(rect["t3"], "t3") * 1000
    props = rectangle_properties(t2, t3)
    return {
        "story": col["Story"], "label": assign["Label"], "member": member,
        "point_i": {"id": pi["UniqueName"], "xyz_m": xi},
        "point_j": {"id": pj["UniqueName"], "xyz_m": xj},
        "length_i_j_m": length, "offset_i_m": oi, "offset_j_m": oj,
        "offset_option": offsets["OffsetOpt"],
        "rigid_zone_factor": text_number(offsets["RigidFact"], "RigidFact"),
        "local_axis_rotation_deg": text_number(axes["Angle"], "Angle"),
        "observed_output_span_m": span,
        "observed_stations_m": sorted(stations),
        "section_name": assign["SectProp"],
        "native_t2_mm": t2, "native_t3_mm": t3,
        "section_references": props,
        "minimum_eccentricity_mm_reference_only": float(minimum_eccentricity_mm(t2)),
        "free_length_ln_mm": None, "effective_length_factor_k": None,
        "actual_p_delta_or_p_Delta_applied_proven": False,
        "effective_slenderness_calculated": False,
    }


def project_column_slenderness_evidence(
    source: Mapping, pmm: Mapping, global_pdelta: Mapping | None,
) -> dict:
    """Present the frame length and gross-section L/r after exact PMM receipt replay."""
    uid = pmm["member_id"]
    result = {
        "member_id": uid,
        "story": pmm["story"],
        "section": pmm["section"],
        "status": "NOT_PROVEN",
        "frame_length_m": None,
        "geometric_slenderness": None,
        "i_joint_id": None,
        "j_joint_id": None,
        "observed_object_stations_m": [],
        "analysis_order": pmm["analysis_order"],
        "global_pdelta_status": global_pdelta.get("status") if global_pdelta is not None else None,
        "unverified_inputs": [
            "Physical support faces and clear length",
            "End restraints, sway classification and effective length factors by axis",
            "Effective stiffness and creep assumptions",
            "Design axial force and signed moments at the physical end faces",
            "Actual analysis order and global P–Δ treatment",
        ],
    }
    if source.get("source_mode") != "LIVE_ETABS":
        return result
    force_source = source["column_axial"].get("force_source") or {}
    if force_source.get("units_code") == 6:
        # The PMM replay validated these native ObjectElm arrays for this UID.
        rowset = force_source["rowsets"].get(uid, {})
        result["observed_object_stations_m"] = sorted(set(rowset.get("ObjSta", [])))

    geometry = source.get("geometry_capture") or {}
    if (geometry.get("present_units") != 6 or geometry.get("present_units_after") != 6
            or geometry.get("unit_state_unchanged") is not True):
        return result
    try:
        columns = geometry_rows(geometry, "COLUMN_CONNECTIVITY", {"UniqueName", "Story"})
        column = unique(columns, "UniqueName", uid)
    except ValueError:
        return result
    if column["Story"] != pmm["story"]:
        return result
    for source_field, result_field in (("UniquePtI", "i_joint_id"), ("UniquePtJ", "j_joint_id")):
        value = column.get(source_field)
        if isinstance(value, str) and value.strip() and value not in {"None", "N.A."}:
            result[result_field] = value
    units = geometry["tables"]["COLUMN_CONNECTIVITY"]["field_metadata"].get("units_by_field") or {}
    raw_length = column.get("Length")
    if not isinstance(units, Mapping) or units.get("Length") != "m" or type(raw_length) not in (str, int, float):
        return result
    try:
        length = text_number(raw_length, "Length")
    except LiveEvidenceError:
        return result
    if length <= 0:
        return result
    result["frame_length_m"] = length

    section = pmm.get("section_evidence") or {}
    try:
        properties = rectangle_properties(section.get("native_t2_mm"), section.get("native_t3_mm"))
    except (ValueError, ArithmeticError):
        return result
    r2, r3 = properties["r22_exact_mm"], properties["r33_exact_mm"]
    length_mm = length * 1000
    ratio2, ratio3 = length_mm / r2, length_mm / r3
    if math.isfinite(ratio2) and math.isfinite(ratio3):
        result["geometric_slenderness"] = {
            "radius_local_2_mm": r2,
            "radius_local_3_mm": r3,
            "frame_length_over_radius_local_2": ratio2,
            "frame_length_over_radius_local_3": ratio3,
        }
    return result


def _material_and_cage(live: Mapping, lc_run: Mapping, member: str):
    stages = {r["stage"]: r for r in lc_run["check_instances"]}
    require(set(stages) == {"R07", "R08", "R09"}, "LC_RUN_STAGE_SET_INVALID")
    cage = stages["R09"]["numeric_detail"]
    require(cage.get("role") == "PROPOSED"
            and cage.get("constructible_scenario") is True
            and cage.get("cage_revision_sha256") == lc_run.get("cage_revision_sha256"),
            "UNAPPROVED_OR_TAMPERED_CAGE")
    owner_mat = stages["R07"]["numeric_detail"]["kernel_inputs"]["material_owner"]
    material = Material(**owner_mat)
    col, assign, rect = _profile(live, member)
    cg = live["gateway_capture"]
    concrete = unique(table(cg, "Material Properties - Concrete Data"),
                      "Material", rect["Material"])
    design = unique(table(cg, "Frame Section Property Definitions - Concrete Column Reinforcing"),
                    "Name", assign["SectProp"])
    steel = unique(table(cg, "Material Properties - Rebar Data"),
                   "Material", design["RebarMatL"])
    pref_rows = table(cg, "Concrete Frame Design Preferences - TS 500-2000(R2018)")
    require(len(pref_rows) == 1, "DESIGN_FACTORS_AMBIGUOUS")
    fck = text_number(concrete["Fc"], "Fc") / 1000
    fy = text_number(steel["Fy"], "Fy") / 1000
    gc = text_number(pref_rows[0]["GammaC"], "GammaC")
    gs = text_number(pref_rows[0]["GammaS"], "GammaS")
    require(abs(material.fck - fck) < 1e-9
            and abs(material.fcd - fck / gc) < 1e-9
            and abs(material.fyd - fy / gs) < 1e-9,
            "MATERIAL_OR_FACTORS_CHANGED")
    bars = tuple(Bar(**bar) for bar in cage["bar_area_geometry"])
    dim2, dim3 = local_dimensions(
        text_number(rect["t2"], "t2") * 1000,
        text_number(rect["t3"], "t3") * 1000)
    rho = sum(bar.area for bar in bars) / (dim2 * dim3)
    require(len(bars) == cage.get("bar_count")
            and .01 <= rho <= .04
            and abs(rho - number(cage.get("steel_ratio"), "steel_ratio")) <= 1e-12,
            "PROPOSED_REBAR_AREA_OR_RATIO_MISMATCH")
    require(cage.get("area_ratio_reference_met") is True
            and cage.get("spacing_reference_met") is True
            and cage.get("tie_diameter_reference_met") is True,
            "PROPOSED_CAGE_GEOMETRY_REFERENCE_GATE")
    return Section(dim2, dim3, bars, material), cage


def review_live_column(*, live: dict, lc_run: dict, combo: dict,
                       pmm_run: dict, geometry: dict) -> dict:
    """Reconcile an observed concurrent static combo and re-run the owned PMM.

    Returns numeric-only R07 with R08/R09 intentionally non-authorized.
    The recorded prior PMM is an independent consistency check, NOT an oracle.
    """
    for payload, field in ((live, "payload_sha256"), (lc_run, "run_result_sha256"),
                           (combo, "payload_sha256"), (pmm_run, "run_result_sha256"),
                           (geometry, "payload_sha256")):
        sealed(payload, field)
    require(live.get("schema") == LIVE and combo.get("schema") == COMBO
            and pmm_run.get("schema") == COMBO_RUN and lc_run.get("schema") == LC_RUN,
            "INCOMPATIBLE_RECEIPT_SCHEMA")
    _gateway_ready(live["gateway_capture"], live["model_filename"])
    require(live.get("analysis_generation_proven") is False
            and combo.get("analysis_generation_proven") is False
            and combo.get("same_cut_proven") is False
            and combo.get("source_only") is True,
            "UNPROVEN_SOURCE_AUTHORITY_MISREPRESENTED")
    require(live.get("model_units_before") == live.get("model_units_after") == 6
            and live.get("model_locked_before") is True
            and live.get("model_locked_after") is True
            and live.get("edb_sha256_before") == live.get("edb_sha256_after")
            and live.get("requested_member"), "LIVE_MODEL_UNVERIFIED")
    member = live["requested_member"]
    require(member == combo.get("member_id")
            and member == lc_run["source"]["physical_object_id"]
            and combo.get("model_filename") == live["model_filename"]
            and combo.get("model_edb_sha256") == live["edb_sha256_before"]
            and pmm_run.get("model_edb_sha256") == combo["model_edb_sha256"]
            and pmm_run.get("source_capture_sha256") == combo["payload_sha256"]
            and pmm_run.get("reference_lc_dl_run_sha256") == lc_run["run_result_sha256"]
            and pmm_run.get("original_cage_sha256") == lc_run["cage_revision_sha256"]
            and pmm_run.get("engineering_release") == lc_run.get("engineering_release") == "NOT_READY"
            and combo.get("results_combo_flag_before") == combo.get("results_combo_flag_after"),
            "CROSS_SOURCE_OR_CAPTURE_STATE_INVALID")
    require(lc_run["source"]["source_sha256"] == live["payload_sha256"]
            and lc_run["source"]["model_edb_sha256"] == combo["model_edb_sha256"],
            "BASELINE_SOURCE_CHANGED")
    require(lc_run["source"].get("output_case") == "LC_DL"
            and lc_run.get("design_demand_approved") is False,
            "LC_DL_BASELINE_NOT_A_SOURCE_ONLY_SCENARIO")
    identity = live.get("selected_identity")
    require(isinstance(identity, dict)
            and identity.get("Obj") == member
            and identity.get("LoadCase") == "LC_DL"
            and identity.get("StepType") == "Single Value",
            "LC_DL_SELECTED_IDENTITY_UNVERIFIED")
    for ci in lc_run["check_instances"]:
        sealed(ci, "instance_sha256")
    require(combo["combo"].get("name") == "Grav_Ult"
            and combo["combo"].get("operator") == "Linear Add"
            and combo["combo"].get("concrete_design_list") == "Strength"
            and tuple((t.get("case"), t.get("factor")) for t in combo["combo"]["terms"]) == GRAV_ULT
            and all(t.get("case_type") == "Linear Static" for t in combo["combo"]["terms"]),
            "COMBO_AST_NOT_SUPPORTED_STATIC_LINEAR_ADD")
    rows = combo.get("rows")
    require(isinstance(rows, list) and len(rows) == combo.get("combo_station_count")
            and len(rows) == pmm_run.get("observed_station_count")
            and len(rows) == pmm_run.get("numeric_pmm_station_count")
            and len(rows) > 0, "COMBO_ROW_COUNT_MISMATCH")
    section, cage = _material_and_cage(live, lc_run, member)
    owner = solver(section)
    prior = {}
    for ci in pmm_run["check_instances"]:
        sealed(ci, "instance_sha256")
        require(ci.get("physical_object_id") == member
                and ci.get("case") == "Grav_Ult"
                and ci.get("source_sha256") == combo["payload_sha256"],
                "PMM_PRIOR_IDENTITY_INVALID")
        key = (ci["obj_station_m"], ci["elm_station_m"], ci["step_type"], ci["step_number"])
        require(key not in prior, "PMM_PRIOR_DUPLICATE")
        prior[key] = ci
    resolved, seen = [], set()
    for row in rows:
        require(row.get("Obj") == member and row.get("LoadCase") == "Grav_Ult"
                and row.get("StepType") == "Single Value"
                and number(row.get("StepNum"), "StepNum") == 0.0,
                "NONCONCURRENT_COMBO_STATE")
        native = {field: number(row.get(field), field) for field in FORCES}
        ost, est = (number(row[k], k) for k in ("ObjSta", "ElmSta"))
        try:
            matched_key, check = match_station_with_tolerance(
                prior, ost, est, "Single Value", 0.0, tol_m=1e-6
            )
        except ValueError as exc:
            raise LiveEvidenceError("STATION_DUPLICATE_OR_MISSING") from exc
        require(matched_key not in seen, "STATION_DUPLICATE_OR_MISSING")
        seen.add(matched_key)
        require(check.get("analysis_element_id") == row.get("Elm"), "ELEMENT_ID_CHANGED")
        require(all(abs(native[f] - number(check["signed_source_six"][f], f)) <= 1e-9
                    for f in FORCES), "SIX_SIGNED_FORCE_MISMATCH")
        result = owner.assess(-native["P"] * 1000, native["M2"] * 1e6, native["M3"] * 1e6)
        expected = check["owner_pmm_result"]
        require(result.get("status") == expected.get("status")
                and result.get("utilization") is not None
                and expected.get("utilization") is not None
                and abs(result["utilization"] - expected["utilization"]) <= 1e-9,
                "OWNED_PMM_REPLAY_DIVERGED")
        resolved.append({
            "object_station_m": ost, "element_station_m": est, "element_id": row["Elm"],
            "case": "Grav_Ult", "step_type": "Single Value", "step_number": 0,
            "signed_P_kN": native["P"], "signed_M2_kNm": native["M2"],
            "signed_M3_kNm": native["M3"], "numeric_utilization": result["utilization"],
            "numeric_status": result["status"], "design_eligible": False,
        })
    require(len(resolved) == len(prior) == len(rows), "INCOMPLETE_STATION_COVERAGE")
    resolved.sort(key=lambda r: r["object_station_m"])
    georef = _geometry(live, geometry, member, [r["object_station_m"] for r in resolved])
    governing = max(resolved, key=lambda r: r["numeric_utilization"])
    output = {
        "schema": "tbdy.next.engine.live-column-reconciled.v1",
        "member": member, "case": "Grav_Ult",
        "source_model_sha256": combo["model_edb_sha256"],
        "receipt_sha256": {
            "live": live["payload_sha256"], "lc_dl_run": lc_run["run_result_sha256"],
            "combo_capture": combo["payload_sha256"], "combo_pmm": pmm_run["run_result_sha256"],
            "geometry_capture": geometry["payload_sha256"],
        },
        "source_consistency": "SIGNED_STATIC_COMBO_AND_PMM_OWNER_REPLAY_MATCHED",
        "r07": {"status": "NUMERIC_SECTION_SCENARIO", "stations": resolved,
                "governing_observed_station_m": governing["object_station_m"],
                "maximum_numeric_utilization": governing["numeric_utilization"],
                "formal_pmm_pass": False},
        "r08": {"status": "GEOMETRY_BOUND_SECOND_ORDER_NOT_EVALUATED",
                "geometry": georef,
                "global_p_delta": "STORY_WEIGHT_SHEAR_DRIFT_BASIS_NOT_BOUND",
                "local_p_delta": "K_LN_SWAY_EI_CREEP_NOT_BOUND",
                "actual_second_order_applied_proven": False},
        "r09": {"status": "PROPOSED_CAGE_NOT_APPROVED",
                "cage_revision_sha256": cage["cage_revision_sha256"],
                "bar_count": cage["bar_count"], "steel_ratio": cage["steel_ratio"],
                "selection_approved": False},
        "analysis_generation_proven": False, "same_cut_proven": False,
        "design_demand_approved": False, "engineering_verdict": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "remaining_gates": [
            "APPROVED_SEISMIC_COMBOBOOK", "SAME_GENERATION_AND_SAME_CUT",
            "STORY_SEISMIC_WEIGHT_SHEAR_DRIFT", "PDELTA_ANALYSIS_BASIS",
            "TS500_FREE_LENGTH_AND_K", "CREEP_AND_EFFECTIVE_EI",
            "MINIMUM_ECCENTRICITY", "SELECTED_CAGE_AND_INDEPENDENT_PMM_ORACLE",
        ],
    }
    output["result_sha256"] = digest(output)
    return output


def load_and_evaluate_127_from_receipts(receipt_dir: Path | str | None = None) -> dict[str, Any]:
    """Read the archived source and its digest-linked run, then replay the P0 gates."""
    directory = Path(receipt_dir) if receipt_dir is not None else (
        Path.cwd() / ".private_sources" / "from_R07_R09_GITHUB"
    )
    live = json.loads((directory / "r07_r09_live.json").read_text(encoding="utf-8"))
    combo = json.loads((directory / "r07_127_gravult_capture.json").read_text(encoding="utf-8"))
    pmm_run = json.loads((directory / "r07_127_gravult_numeric_result.json").read_text(encoding="utf-8"))
    geometry = json.loads((directory / "r08_127_live_offsets_axes_points.json").read_text(encoding="utf-8"))

    if live.get("schema") == LIVE:
        run_sha = pmm_run["reference_lc_dl_run_sha256"]
        matching_runs = []
        for path in (directory / "r07_r09_results").glob("*/run_result.json"):
            run = json.loads(path.read_text(encoding="utf-8"))
            if run.get("run_result_sha256") == run_sha:
                matching_runs.append(run)
        require(len(matching_runs) == 1, "LC_DL_RUN_RECEIPT_MISSING_OR_AMBIGUOUS")
        (lc_run,) = matching_runs
    else:
        lc_run = live["run_result"]
        live = live["live_capture"]

    setup_path = directory / "r07_live_combinations.json"
    setup_capture = json.loads(setup_path.read_text(encoding="utf-8")) if setup_path.is_file() else None
    receipts = dict(live=live, lc_run=lc_run, combo=combo, pmm_run=pmm_run, geometry=geometry)
    reconciled = review_live_column(**receipts)
    p0_report = evaluate_column_p0_gates(**receipts, setup_capture=setup_capture)
    _, _, rect = _profile(live, reconciled["member"])
    r07 = next(row for row in lc_run["check_instances"] if row["stage"] == "R07")
    return {
        "reconciled": reconciled,
        "p0_gate_report": p0_report,
        "source_context": {
            "model_name": ntpath.basename(live["model_filename"]),
            "concrete_material": rect["Material"],
            "material_owner": r07["numeric_detail"]["kernel_inputs"]["material_owner"],
        },
    }
