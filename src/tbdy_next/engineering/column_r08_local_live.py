"""R08-Local live bridge: TS 500 slenderness (7.17-7.18), EI (7.20/7.21), Nk and beta (7.24/7.29).

Deterministic report/pipeline-time projection over the SAME replayed live
receipts (`geometry_capture`, `column_axial`, `column_pmm`, `r08-second-order`).
Reuses `live_column.project_column_slenderness_evidence` and `ts500_column`
with zero formula duplication and writes no new receipt files.

Never guesses support clear length ln, effective length factor k, creep ratio
Rm, sway class, or Eq. 7.29 resolution: reference scenarios stay NOT_PROVEN.
"""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Mapping

from ..column_engine.section_capacity import Section, solver
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.ts500_column import (
    SWAY_PERMITTED,
    SWAY_PREVENTED,
    LocalSectionDims,
    adopted_magnification_factors,
    apply_minimum_eccentricity,
    effective_stiffness_nmm2,
    eq729_length_comparison,
    euler_load_kn,
    evaluate_slenderness,
    moment_magnification_factors,
    rectangle_properties,
)
from .column_clear_length import FACE_BASIS, WALL_COUPLED, proven_clear_length_m
from .column_effective_length import effective_length_reference, reference_end_ratios, resolve_adopted_frame_k
from .column_mat_support import project_mat_horizontal_supports
from .column_r10_live import SelectedColumnCage
from .live_column import project_column_slenderness_evidence
from .second_order_basis import ACCEPTANCE_GATE, NONSWAY_POLICY, SWAY_POLICY

SCHEMA = "tbdy.next.column-r08-local-live.v1"

PHYSICAL_CLEAR_LENGTH_GATE = "PHYSICAL_SUPPORT_FACES_AND_CLEAR_LENGTH_NOT_PROVEN"
WALL_COUPLED_LENGTH_GATE = "WALL_FRAME_EFFECTIVE_LENGTH_REQUIRES_COUPLED_MODEL"
OPEN_GATES = (
    PHYSICAL_CLEAR_LENGTH_GATE,
    "END_RESTRAINTS_K_AND_SWAY_CLASSIFICATION_NOT_APPROVED",
    "CREEP_RATIO_RM_AND_SECTION_CRACKING_NOT_APPROVED",
    "ACTUAL_ANALYSIS_ORDER_UNVERIFIED",
    "EQ729_LENGTH_AMBIGUITY_NOT_RESOLVED",
)
_UTILIZATION_STATUSES = frozenset({"WITHIN_SCENARIO_SURFACE", "EXCEEDS_SCENARIO_SURFACE", "AXIAL_ONLY_SCENARIO"})
_SELECTED_CAGE_UNAVAILABLE = "SAME_RUN_SELECTED_COLUMN_CAGE_UNAVAILABLE"


def _reference_ec_mpa(fck_mpa: float) -> float:
    return 3250.0 * math.sqrt(fck_mpa) + 14000.0


def _assessed_utilization(assessment: Mapping[str, Any]) -> float | None:
    status = assessment.get("status")
    if status not in _UTILIZATION_STATUSES:
        return None
    value = assessment.get("axial_utilization" if status == "AXIAL_ONLY_SCENARIO" else "utilization")
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _magnified_moment_demand(
    *, nd_kn: float, m2_knm: float, m3_knm: float, dims: LocalSectionDims,
    beta_m2: float, beta_m3: float, global_factor: float,
) -> dict[str, Any]:
    """Compose the existing minimum-eccentricity owner before magnification.

    TS 500 7.26 applies beta to M2 subject to the 6.16 minimum, not to a raw
    moment that is floored afterwards. The current local/global factor policy
    is unchanged; its engineering acceptance remains a separate requirement.
    """
    factors = (beta_m2, beta_m3, global_factor)
    try:
        valid = all(not isinstance(v, bool) and math.isfinite(float(v)) and float(v) >= 1.0 for v in factors)
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not valid:
        raise ValueError("MOMENT_MAGNIFICATION_FACTOR_INVALID")
    beta_m2, beta_m3, global_factor = map(float, factors)
    first_order = apply_minimum_eccentricity(
        nd_kn=nd_kn, m2_knm=m2_knm, m3_knm=m3_knm, dims=dims,
    )
    m2_final = first_order["m2_design_knm"] * beta_m2 * global_factor
    m3_final = first_order["m3_design_knm"] * beta_m3 * global_factor
    if not all(math.isfinite(v) for v in (m2_final, m3_final)):
        raise ValueError("MAGNIFIED_MOMENT_NONFINITE")
    return {
        "first_order_m2_knm": first_order["m2_raw_knm"],
        "first_order_m3_knm": first_order["m3_raw_knm"],
        "first_order_m2_design_knm": first_order["m2_design_knm"],
        "first_order_m3_design_knm": first_order["m3_design_knm"],
        "minimum_m2_knm": first_order["m2_min_knm"],
        "minimum_m3_knm": first_order["m3_min_knm"],
        "minimum_eccentricity_m2_mm": first_order["e_min_m2_mm"],
        "minimum_eccentricity_m3_mm": first_order["e_min_m3_mm"],
        "m2_floor_governed": first_order["m2_floor_governed"],
        "m3_floor_governed": first_order["m3_floor_governed"],
        "beta_m2": beta_m2,
        "beta_m3": beta_m3,
        "global_beta_ii_applied": global_factor,
        "magnified_m2_design_knm": m2_final,
        "magnified_m3_design_knm": m3_final,
        "moment_operation_order": "MINIMUM_ECCENTRICITY_THEN_LOCAL_AND_GLOBAL_MAGNIFICATION",
    }


def global_pdelta_precheck_within_limit(record: Mapping[str, Any] | None) -> bool | None:
    """Read the canonical story precheck only when its direction coverage is complete."""
    if not record or record.get("status") != "NUMERIC_PRECHECK_UNAPPROVED":
        return None
    expected = record.get("expected_story_direction_count")
    evaluated = record.get("evaluated_story_direction_count")
    if type(expected) is not int or type(evaluated) is not int or expected <= 0 or evaluated != expected:
        return None
    if record.get("missing_story_direction") != []:
        return None
    directions = record.get("direction_results") or {}
    flags = [(directions.get(axis) or {}).get("within_reference_limit_candidate") for axis in ("X", "Y")]
    return all(flags) if all(type(flag) is bool for flag in flags) else None


def _end_moment_ratio(m_a: float, m_b: float) -> float:
    """TS 500 §7.6.2 end-moment ratio M1/M2 in [-1, 1] (|M1| <= |M2|; positive = single curvature)."""
    if abs(m_a) == 0.0 and abs(m_b) == 0.0:
        return 0.0
    m1, m2 = (m_a, m_b) if abs(m_a) <= abs(m_b) else (m_b, m_a)
    if m2 == 0.0:
        return 0.0
    return max(-1.0, min(1.0, m1 / m2))


def _adopted_global_factor(basis: Mapping[str, Any], global_pdelta: Mapping[str, Any] | None) -> float:
    """Consume a complete existing TBDY factor once; never invent overlap policy."""
    if global_pdelta_precheck_within_limit(global_pdelta) is not True:
        raise ValueError("ADOPTED_SECOND_ORDER_TBDY_PRECHECK_UNRESOLVED_OR_OUTSIDE_LIMIT")
    factors = []
    for axis in ("X", "Y"):
        value = ((global_pdelta or {}).get("direction_results", {}).get(axis) or {}).get("beta_ii_candidate")
        if isinstance(value, bool):
            raise ValueError("ADOPTED_SECOND_ORDER_TBDY_FACTOR_MISSING_OR_INVALID:" + axis)
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("ADOPTED_SECOND_ORDER_TBDY_FACTOR_MISSING_OR_INVALID:" + axis) from exc
        if not math.isfinite(value) or value < 1:
            raise ValueError("ADOPTED_SECOND_ORDER_TBDY_FACTOR_MISSING_OR_INVALID:" + axis)
        factors.append(value)
    if basis["global_factor_policy"] == SWAY_POLICY:
        if any(abs(value - 1.0) > 8 * math.ulp(1.0) for value in factors):
            raise ValueError("ADOPTED_TS500_SWAY_AND_NONUNIT_TBDY_OVERLAP_UNSUPPORTED")
        return 1.0
    if basis["global_factor_policy"] != NONSWAY_POLICY:
        raise ValueError("ADOPTED_SECOND_ORDER_GLOBAL_FACTOR_POLICY_UNSUPPORTED")
    return max(factors)


def _adopted_axis_factor(basis, axis, combination, nd_kn, nk_kn, stiffness, *, end_ratio=None, spectral=False):
    """Pass bound inputs to the single TS 500 coefficient owner."""
    cfg = basis["member"]["axes"][axis]
    if spectral and cfg["cm_policy"] != "UNITY":
        raise ValueError("ADOPTED_SPECTRAL_CM_REQUIRES_UNITY:" + axis)
    story = cfg["story_aggregates"].get(combination, {})
    return adopted_magnification_factors(nd_kn=nd_kn, nk_kn=nk_kn,
        free_length_ln_mm=stiffness["free_length_ln_mm"], k=stiffness["effective_length_factor_k"], radius_mm=stiffness["radius_mm"],
        fck_mpa=stiffness["fck_mpa"], area_mm2=stiffness["area_mm2"], sway=cfg["sway"],
        cm_policy=cfg["cm_policy"], eq729_length_reading=cfg["eq729_length_reading"],
        signed_end_moment_ratio=end_ratio, story_nd_kn=story.get("nd_kn"), story_nk_kn=story.get("nk_kn"))


def _project_single_r08_local(
    source: Mapping[str, Any],
    geometry: Mapping[str, Any] | None,
    axial: Mapping[str, Any] | None,
    pmm: Mapping[str, Any],
    global_pdelta: Mapping[str, Any] | None = None,
    eng_col_res: Mapping[str, Any] | None = None,
    eng_col_section: Any = None,
    physical_length: Mapping[str, Any] | None = None,
    adopted_basis: Mapping[str, Any] | None = None,
    adopted_basis_error: str | None = None,
    restraint_axes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project TS 500 local slenderness, magnification and selected-cage 2nd-order PMM for one column."""
    evidence = project_column_slenderness_evidence(source, pmm, global_pdelta)
    uid = pmm.get("member_id")
    section_ev = pmm.get("section_evidence") or {}
    t2_mm = section_ev.get("native_t2_mm")
    t3_mm = section_ev.get("native_t3_mm")
    fck_mpa = section_ev.get("fck_mpa")
    es_mpa = section_ev.get("es_mpa")
    frame_length_m = evidence.get("frame_length_m")
    stations = [float(s) for s in evidence.get("observed_object_stations_m") or ()]
    observed_reduced_span_mm = (
        (max(stations) - min(stations)) * 1000.0
        if len(stations) >= 2 and max(stations) > min(stations)
        else None
    )
    frame_length_mm = frame_length_m * 1000.0 if frame_length_m is not None else None
    candidate_span_mm = observed_reduced_span_mm or frame_length_mm
    span_basis = (
        "OBSERVED_REDUCED_OUTPUT_SPAN_NOT_PHYSICAL_LN"
        if observed_reduced_span_mm is not None
        else "JOINT_TO_JOINT_FRAME_LENGTH_NOT_PHYSICAL_LN"
        if frame_length_mm is not None
        else "SPAN_UNAVAILABLE"
    )
    ln = proven_clear_length_m(physical_length, uid)
    wall_coupled = (physical_length is not None and physical_length.get("member_id") == uid
                    and physical_length.get("status") == WALL_COUPLED)
    open_gates = list(OPEN_GATES)
    if ln is not None:
        candidate_span_mm = ln * 1000.0
        span_basis = FACE_BASIS
        open_gates.remove(PHYSICAL_CLEAR_LENGTH_GATE)
        evidence["unverified_inputs"].remove("Physical support faces and clear length")
    elif wall_coupled:
        # A native cut span cannot represent the isolated buckling length of a
        # column exchanging forces with a wall inside that span.
        candidate_span_mm = None
        span_basis = WALL_COUPLED
        open_gates[open_gates.index(PHYSICAL_CLEAR_LENGTH_GATE)] = WALL_COUPLED_LENGTH_GATE

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "member_id": uid,
        "story": pmm.get("story"),
        "section": pmm.get("section"),
        "evidence": evidence,
        "frame_length_mm": frame_length_mm,
        "observed_reduced_span_mm": observed_reduced_span_mm,
        "candidate_span_mm": candidate_span_mm,
        "span_basis": span_basis,
        **({"physical_clear_length": physical_length} if physical_length is not None else {}),
        "ec_reference_mpa": None,
        "ec_basis": "NOT_AVAILABLE",
        "stiffness_and_euler": None,
        "combination_scenarios": [],
        "max_reference_beta_sway_prevented": None,
        "open_gates": open_gates,
        "status": "OBSERVED_EVIDENCE_ONLY",
        **({"execution_status": "NOT_RUN"} if wall_coupled else {}),
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
    if pmm.get("analysis_order") == "FIRST_ORDER" and pmm.get("archived_solver_log_sha256"):
        out["source_analysis_order"] = pmm["analysis_order"]
        out["archived_solver_log_sha256"] = pmm["archived_solver_log_sha256"]
        open_gates.remove("ACTUAL_ANALYSIS_ORDER_UNVERIFIED")
        evidence["unverified_inputs"].remove("Actual analysis order and global P–Δ treatment")
        evidence["unverified_inputs"].append("Global P–Δ treatment for design")
    if adopted_basis is not None and ln is not None and frame_length_m is not None:
        from .column_axial_balance import project_gravity_axial_balance

        balance = project_gravity_axial_balance(source, pmm, physical_length, frame_length_m)
        if balance is not None:
            out["gravity_axial_balance"] = balance
            if out.get("archived_solver_log_sha256") and any(
                abs(interval["native_axial_change_kn"]) > 1e-8
                for combo in (balance.get("combinations") or {}).values() for interval in combo["intervals"]
            ):
                open_gates.append("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED")
    resolved_k = {}
    if adopted_basis is not None:
        out.update(adopted_second_order_basis=adopted_basis,
                   second_order_basis_sha256=adopted_basis["basis_sha256"],
                   second_order_basis_status="ADOPTED_CALCULATION_BASIS_NOT_APPLIED")
        open_gates.append(ACCEPTANCE_GATE)
        if wall_coupled:
            out["second_order_basis_status"] = "WALL_COUPLED_ADOPTED_BASIS_WITHHELD"
        elif ln is None:
            adopted_basis_error = "ADOPTED_SECOND_ORDER_PHYSICAL_CLEAR_LENGTH_REQUIRED"
        elif (pmm.get("actual_second_order_applied") is True
              or pmm.get("analysis_order") not in (None, "UNVERIFIED", "NOT_PROVEN", "FIRST_ORDER")):
            adopted_basis_error = "ADOPTED_SECOND_ORDER_SOURCE_ORDER_CONFLICT_NO_DOUBLE_APPLICATION"
        if not wall_coupled and adopted_basis_error is None:
            try:
                adopted_global_factor = _adopted_global_factor(adopted_basis, global_pdelta)
                resolved_k = {axis: resolve_adopted_frame_k(cfg, (restraint_axes or {}).get(axis))
                              for axis, cfg in adopted_basis["member"]["axes"].items()}
            except ValueError as exc:
                adopted_basis_error = str(exc)
    if adopted_basis_error is not None:
        out.update(status="ADOPTED_SECOND_ORDER_BASIS_UNRESOLVED", execution_status="NOT_RUN",
                   second_order_basis_status="ADOPTED_CALCULATION_BASIS_NOT_APPLIED")
        open_gates.append(adopted_basis_error)
        return out
    if not candidate_span_mm or not t2_mm or not t3_mm or not fck_mpa:
        return out

    props = rectangle_properties(t2_mm, t3_mm)
    ec_mpa = _reference_ec_mpa(float(fck_mpa))
    out["ec_reference_mpa"] = ec_mpa
    out["ec_basis"] = "TS500_EQ_3_1_3250_SQRT_FCK_PLUS_14000_REFERENCE"

    is2 = is3 = None
    feature = source.get("column_axial") or {}
    if geometry is not None and feature.get("pmm_section_source") and feature.get("design_preferences"):
        from .column_axial import _columns
        from .column_pmm_section import build_pmm_section

        member = next((r for r in _columns(geometry) if r["element_id"] == uid), None)
        axial_member = next((r for r in axial.get("columns", ()) if r["element_id"] == uid), None)
        if member is not None and axial_member is not None:
            try:
                sec, _ = build_pmm_section(
                    feature["pmm_section_source"], member, axial_member,
                    feature["design_preferences"], include_layout=True,
                )
                is2 = math.fsum(b.area * (b.x3 ** 2) for b in sec.bars)
                is3 = math.fsum(b.area * (b.x2 ** 2) for b in sec.bars)
            except (ValueError, KeyError, TypeError, ArithmeticError):
                pass

    eng_is2 = math.fsum(b.area * (b.x3 ** 2) for b in eng_col_section.bars) if eng_col_section is not None else None
    eng_is3 = math.fsum(b.area * (b.x2 ** 2) for b in eng_col_section.bars) if eng_col_section is not None else None

    axis_specs = (
        ("M2", props["i22_mm4"], props["r22_exact_mm"], is2, eng_is2, 2, 3),
        ("M3", props["i33_mm4"], props["r33_exact_mm"], is3, eng_is3, 3, 2),
    )
    stiffness_map: dict[str, dict[str, Any]] = {}
    for axis_name, ic_mm4, r_mm, is_mm4, eng_is_mm4, _, _ in axis_specs:
        axis_basis = adopted_basis["member"]["axes"][axis_name] if adopted_basis else None
        rm = axis_basis["creep_ratio_rm"] if axis_basis else 0.0
        k = resolved_k[axis_name][0] if axis_basis else 1.0
        lk_mm = k * candidate_span_mm
        ei_uncracked_ref = effective_stiffness_nmm2(
            ec_mpa=ec_mpa, ic_mm4=ic_mm4, creep_ratio=rm, method="TS500_7_21",
        )
        nk_721 = euler_load_kn(effective_ei_nmm2=ei_uncracked_ref, effective_length_lk_mm=lk_mm)
        ei_720 = (
            effective_stiffness_nmm2(
                ec_mpa=ec_mpa, ic_mm4=ic_mm4, creep_ratio=rm, method="TS500_7_20",
                es_mpa=float(es_mpa), is_mm4=float(is_mm4),
            )
            if es_mpa and is_mm4 is not None
            else None
        )
        nk_720 = (
            euler_load_kn(effective_ei_nmm2=ei_720, effective_length_lk_mm=lk_mm)
            if ei_720 is not None
            else None
        )
        eng_ei_720 = (
            effective_stiffness_nmm2(
                ec_mpa=ec_mpa, ic_mm4=ic_mm4, creep_ratio=rm, method="TS500_7_20",
                es_mpa=float(es_mpa), is_mm4=float(eng_is_mm4),
            )
            if es_mpa and eng_is_mm4 is not None
            else None
        )
        eng_nk_720 = (
            euler_load_kn(effective_ei_nmm2=eng_ei_720, effective_length_lk_mm=lk_mm)
            if eng_ei_720 is not None
            else None
        )
        stiffness_map[axis_name] = {
            "ic_mm4": ic_mm4,
            "is_mm4": is_mm4,
            "radius_mm": r_mm,
            "reference_creep_ratio_rm": rm,
            "ei_ts500_7_21_nmm2": ei_uncracked_ref,
            "nk_ts500_7_21_kn": nk_721,
            "ei_ts500_7_20_nmm2": ei_720,
            "nk_ts500_7_20_kn": nk_720,
            "preferred_nk_kn": nk_720 if nk_720 is not None else nk_721,
            **({"selected_is_mm4": eng_is_mm4, "selected_ei_ts500_7_20_nmm2": eng_ei_720, "selected_nk_ts500_7_20_kn": eng_nk_720} if eng_nk_720 is not None else {}),
            "ei_method_basis": "TS500_7_20_WITH_RM_0_REFERENCE" if nk_720 is not None else "TS500_7_21_WITH_RM_0_REFERENCE",
        }
        if axis_basis:
            use_rebar = axis_basis["ei_method"] == "TS500_7_20"
            stiffness_map[axis_name].update(
                free_length_ln_mm=candidate_span_mm, effective_length_lk_mm=lk_mm, effective_length_factor_k=k,
                fck_mpa=float(fck_mpa), area_mm2=props["area_mm2"],
                ei_method_basis=axis_basis["ei_method"] + "_ADOPTED_CALCULATION_ASSUMPTIONS",
                preferred_nk_kn=nk_720 if use_rebar else nk_721,
                selected_nk_kn=(eng_nk_720 if use_rebar else nk_721) if eng_col_section is not None else None,
                selected_ei_nmm2=(eng_ei_720 if use_rebar else ei_uncracked_ref) if eng_col_section is not None else None,
                adopted_axis_basis=axis_basis)
            if resolved_k[axis_name][1] is not None:
                stiffness_map[axis_name]["k_source_resolution"] = resolved_k[axis_name][1]
            if stiffness_map[axis_name]["selected_nk_kn"] is None:
                open_gates.append("ADOPTED_SECOND_ORDER_SELECTED_EI_INPUTS_MISSING:" + axis_name)
    out["stiffness_and_euler"] = stiffness_map

    rows_by_combo: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in pmm.get("rows") or ():
        if row.get("nd_kn") is not None and row.get("object_station_m") is not None:
            rows_by_combo[row["combination"]].append(row)

    betas: list[float] = []
    scenarios: list[dict[str, Any]] = []
    combo_betas_selected: dict[str, dict[str, Any]] = {}
    adopted_combo_factors: dict[str, dict[str, Any]] = {}
    for combo_name in sorted(rows_by_combo):
        combo_rows = sorted(rows_by_combo[combo_name], key=lambda item: float(item["object_station_m"]))
        if len(combo_rows) < 2 or float(combo_rows[0]["object_station_m"]) == float(combo_rows[-1]["object_station_m"]):
            continue
        r_start, r_end = combo_rows[0], combo_rows[-1]
        nd_max = (max(float(row["nd_kn"]) for row in combo_rows) if adopted_basis
                  else max(float(r_start["nd_kn"]), float(r_end["nd_kn"])))
        axes_out: dict[str, Any] = {}
        combo_sel_axes: dict[str, float | None] = {}
        adopted_selected_axes = {}
        for axis_name, _, r_mm, _, _, _, _ in axis_specs:
            m_key = "m2_knm" if axis_name == "M2" else "m3_knm"
            m_a = float(r_start[m_key])
            m_b = float(r_end[m_key])
            end_ratio = _end_moment_ratio(m_a, m_b)
            if adopted_basis:
                stiff = stiffness_map[axis_name]
                selected = None
                if stiff.get("selected_nk_kn") is not None:
                    selected = _adopted_axis_factor(adopted_basis, axis_name, combo_name, nd_max,
                                                    stiff["selected_nk_kn"], stiff, end_ratio=end_ratio)
                combo_sel_axes[axis_name] = selected.get("final_factor") if selected else None
                adopted_selected_axes[axis_name] = selected
                axes_out[axis_name] = {
                    "end_moments_knm": [m_a, m_b], "signed_end_moment_ratio": end_ratio,
                    "slenderness_sway_prevented_k1": None, "slenderness_sway_permitted_k1": None,
                    "magnification_sway_prevented_k1": None,
                    "eq729_reference": (selected or {}).get("eq729_comparison"),
                    "adopted_magnification": selected,
                }
                if selected and selected.get("status") == "BLOCKED":
                    open_gates.append("ADOPTED_SECOND_ORDER:" + str(selected["reason"]) + ":" + combo_name + ":" + axis_name)
                continue
            slenderness_no_sway = evaluate_slenderness(
                free_length_ln_mm=candidate_span_mm, k=1.0, radius_mm=r_mm,
                sway=SWAY_PREVENTED, signed_end_moment_ratio=end_ratio,
            )
            slenderness_sway = evaluate_slenderness(
                free_length_ln_mm=candidate_span_mm, k=1.0, radius_mm=r_mm,
                sway=SWAY_PERMITTED,
            )
            nk_kn = stiffness_map[axis_name]["preferred_nk_kn"]
            mag_no_sway = None
            eq729_ref = None
            sel_nk = stiffness_map[axis_name].get("selected_nk_ts500_7_20_kn")
            if nd_max > 0:
                mag_no_sway = moment_magnification_factors(
                    nd_kn=nd_max, nk_kn=nk_kn, sway=SWAY_PREVENTED,
                    signed_end_moment_ratio=end_ratio, horizontal_load_between_ends=False,
                )
                if isinstance(mag_no_sway.get("beta"), (int, float)):
                    betas.append(float(mag_no_sway["beta"]))
                if sel_nk is not None:
                    mag_sel = moment_magnification_factors(
                        nd_kn=nd_max, nk_kn=sel_nk, sway=SWAY_PREVENTED,
                        signed_end_moment_ratio=end_ratio, horizontal_load_between_ends=False,
                    )
                    combo_sel_axes[axis_name] = (
                        float(mag_sel["beta"])
                        if isinstance(mag_sel.get("beta"), (int, float))
                        else None
                    )
                eq729_ref = eq729_length_comparison(
                    free_length_ln_mm=candidate_span_mm, effective_length_lk_mm=candidate_span_mm,
                    radius_mm=r_mm, nd_kn=nd_max, fck_mpa=float(fck_mpa), area_mm2=props["area_mm2"],
                )
            else:
                combo_sel_axes[axis_name] = 1.0
            axes_out[axis_name] = {
                "end_moments_knm": [m_a, m_b],
                "signed_end_moment_ratio": end_ratio,
                "slenderness_sway_prevented_k1": slenderness_no_sway,
                "slenderness_sway_permitted_k1": slenderness_sway,
                "magnification_sway_prevented_k1": mag_no_sway,
                "eq729_reference": eq729_ref,
            }
        combo_betas_selected[combo_name] = combo_sel_axes
        if adopted_basis:
            adopted_combo_factors[combo_name] = adopted_selected_axes
        scenarios.append({
            "combination": combo_name,
            "end_stations_m": [float(r_start["object_station_m"]), float(r_end["object_station_m"])],
            "governing_nd_kn": nd_max,
            "axes": axes_out,
            "formal_compliance": "NOT_PROVEN",
        })

    out["combination_scenarios"] = scenarios
    out["max_reference_beta_sway_prevented"] = max(betas) if betas else None
    if scenarios:
        out["status"] = "REFERENCE_SLENDERNESS_CALCULATED"

    if eng_col_section is not None and (scenarios or adopted_basis):
        dims_local = LocalSectionDims(eng_col_section.t2, eng_col_section.t3)
        cap_solver = solver(eng_col_section)
        dir_res = (global_pdelta or {}).get("direction_results") or {}
        global_beta_vals = []
        for ax in ("X", "Y"):
            b_str = (dir_res.get(ax) or {}).get("beta_ii_candidate")
            if b_str is not None:
                try:
                    factor = float(b_str)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(factor) and factor >= 1.0 and not isinstance(b_str, bool):
                    global_beta_vals.append(factor)
        global_beta_ii = max(global_beta_vals) if len(global_beta_vals) == 2 else None
        if adopted_basis:
            global_beta_ii = adopted_global_factor
        mag_rows: list[dict[str, Any]] = []
        blocked_buckling = False
        max_util = None
        gov_combo = None
        governing_station = None
        exceeds = False
        expected_stations = pmm.get("expected_station_count")
        resolved_station_count = 0
        for row in pmm.get("rows") or ():
            cname = row.get("combination")
            if cname not in combo_betas_selected or row.get("nd_kn") is None:
                continue
            b_m2 = combo_betas_selected[cname].get("M2")
            b_m3 = combo_betas_selected[cname].get("M3")
            if b_m2 is None or b_m3 is None:
                blocked_buckling = True
                mag_rows.append({
                    "combination": cname,
                    "object_station_m": row.get("object_station_m"),
                    "status": "SECOND_ORDER_BUCKLING_OR_BLOCKED",
                    "utilization": None,
                })
                continue
            g_fac = global_beta_ii if (global_beta_ii is not None and global_beta_ii > 1.0) else 1.0
            demand = {}
            try:
                demand = _magnified_moment_demand(
                    nd_kn=float(row["nd_kn"]), m2_knm=float(row["m2_knm"]),
                    m3_knm=float(row["m3_knm"]), dims=dims_local,
                    beta_m2=b_m2, beta_m3=b_m3, global_factor=g_fac,
                )
                assess = cap_solver.assess(
                    float(row["nd_kn"]) * 1000.0,
                    demand["magnified_m2_design_knm"] * 1e6,
                    demand["magnified_m3_design_knm"] * 1e6,
                )
            except (ValueError, ArithmeticError):
                assess = {"status": "NUMERIC_UNRESOLVED"}
            util = _assessed_utilization(assess)
            if assess.get("status") == "OUTSIDE_SCENARIO_AXIAL_RANGE" or util is not None:
                resolved_station_count += 1
            if assess.get("status") == "OUTSIDE_SCENARIO_AXIAL_RANGE" or (util is not None and util > 1.0 + 1e-6):
                exceeds = True
            station = {
                "combination": cname,
                "object_station_m": row.get("object_station_m"),
                "analysis_element_id": row.get("analysis_element_id"),
                "element_station_m": row.get("element_station_m"),
                "step_type": row.get("step_type"),
                "step_number": row.get("step_number"),
                "nd_kn": row.get("nd_kn"),
                "first_order_m2_knm": row["m2_knm"],
                "first_order_m3_knm": row["m3_knm"],
                "beta_m2": b_m2,
                "beta_m3": b_m3,
                "global_beta_ii_applied": g_fac,
                "first_order_m2_design_knm": None,
                "first_order_m3_design_knm": None,
                "magnified_m2_design_knm": None,
                "magnified_m3_design_knm": None,
                **demand,
                **({"adopted_axis_factors": adopted_combo_factors[cname],
                    "second_order_basis_sha256": adopted_basis["basis_sha256"]} if adopted_basis else {}),
                "moment_demand_knm": None,
                "radial_capacity_knm": None,
                "moment_reserve_knm": None,
                "utilization": util,
                "status": assess["status"],
            }
            if util is not None and assess["status"] in ("WITHIN_SCENARIO_SURFACE", "EXCEEDS_SCENARIO_SURFACE"):
                capacity = assess.get("radial_capacity_kNm")
                if type(capacity) in (float, int) and math.isfinite(capacity) and capacity > 0:
                    moment = math.hypot(demand["magnified_m2_design_knm"], demand["magnified_m3_design_knm"])
                    station.update(moment_demand_knm=moment, radial_capacity_knm=capacity,
                                   moment_reserve_knm=capacity - moment)
            mag_rows.append(station)
            if util is not None and (max_util is None or util >= max_util):
                max_util = util
                gov_combo = cname
                governing_station = station
        complete = (type(expected_stations) is int and expected_stations > 0
                    and resolved_station_count == expected_stations == len(mag_rows))
        if exceeds:
            mag_status = "MAGNIFIED_PMM_EXCEEDS_CAPACITY"
        elif blocked_buckling:
            mag_status = "SECOND_ORDER_BUCKLING_OR_BLOCKED"
        elif complete:
            mag_status = "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN"
        else:
            mag_status = "MAGNIFIED_PMM_COVERAGE_OR_NUMERIC_UNRESOLVED"
        out["magnified_selected_pmm"] = {
            "status": mag_status,
            "governing_combination": gov_combo,
            "governing_station": governing_station if complete and all(r["utilization"] is not None for r in mag_rows) else None,
            "max_utilization": max_util if complete or exceeds else None,
            "global_beta_ii_factor": global_beta_ii,
            "global_beta_ii_basis": (adopted_basis["global_factor_policy"] if adopted_basis else
                                     "STORY_PRECHECK_REFERENCE" if global_beta_ii is not None else "UNIT_FACTOR_REFERENCE_ASSUMPTION"),
            "global_pdelta_within_limit": global_pdelta_precheck_within_limit(global_pdelta),
            "evaluated_row_count": len(mag_rows),
            "expected_row_count": expected_stations,
            "resolved_row_count": resolved_station_count,
            "rows": mag_rows,
            "formal_compliance": "NOT_PROVEN",
        }
        spectral_bound = _evaluate_spectral_bounding_corners(
            uid=uid,
            source=source,
            axial=axial,
            dims_local=dims_local,
            cap_solver=cap_solver,
            stiffness_map=stiffness_map,
            global_beta_ii=global_beta_ii,
            adopted_basis=adopted_basis,
            use_engineer=True,
            mesh_blocked_combinations=tuple(combo["name"] for combo in pmm.get("combinations", ())
                                            if combo.get("status") == "BLOCKED"
                                            and (combo.get("analysis_element_coverage") or {}).get("reason")
                                            not in (None, "ANALYSIS_FRAME_ELEMENT_SOURCE_UNAVAILABLE")),
            cut_blocked_combinations=tuple(combo["name"] for combo in pmm.get("combinations", ())
                                           if combo.get("reason") == "ETABS_CONFIGURED_CUT_COVERAGE_UNRESOLVED"),
        )
        if spectral_bound is not None:
            out["spectral_envelope_pmm_scenario"] = spectral_bound
        if adopted_basis:
            static_done = complete and mag_status in {"MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN", "MAGNIFIED_PMM_EXCEEDS_CAPACITY"}
            spectral_done = spectral_bound is None or (spectral_bound.get("coverage_complete") is True
                and spectral_bound.get("status") in {"BOUNDED_CORNER_ENVELOPE_WITHIN_CAPACITY_NOT_PROVEN",
                                                    "CONSERVATIVE_CORNER_EXCEEDS_1_0_CONCURRENT_VECTOR_REQUIRED"})
            out["second_order_basis_status"] = ("ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN" if static_done and spectral_done
                                                 else "ADOPTED_CALCULATION_BASIS_DEMAND_INCOMPLETE")
            out["status"] = "ADOPTED_SECOND_ORDER_CALCULATED_NOT_PROVEN" if static_done and spectral_done else "ADOPTED_SECOND_ORDER_BASIS_UNRESOLVED"
    return out


def _evaluate_spectral_bounding_corners(
    *,
    uid: str | None,
    source: Mapping[str, Any],
    axial: Mapping[str, Any] | None,
    dims_local: LocalSectionDims,
    cap_solver: Any,
    stiffness_map: Mapping[str, Mapping[str, Any]],
    global_beta_ii: float | None,
    use_engineer: bool = True,
    mesh_blocked_combinations: tuple[str, ...] = (),
    cut_blocked_combinations: tuple[str, ...] = (),
    adopted_basis: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Sample eight bounding corners with explicit case/cut/step completeness.

    This is a reference box, NOT an approved concurrent spectral demand and NOT
    a proof that nonlinear magnification preserves convexity between corners.
    Expected cuts are the source-wide native cut census, not just received
    spectral cuts. The independent physical cut census remains a release gate.
    """
    if not uid or axial is None:
        return None
    names = {str(c["name"]) for c in (axial.get("combination_plan") or {}).get("combinations", ())
             if c.get("force_semantics") == "SCALAR_COMPONENT_ENVELOPE"}
    if not names:
        return None
    errors: list[str] = []
    errors.extend("SPECTRAL_ANALYSIS_ELEMENT_COVERAGE_UNRESOLVED:" + name
                  for name in sorted(names.intersection(mesh_blocked_combinations)))
    errors.extend("SPECTRAL_CONFIGURED_CUT_COVERAGE_UNRESOLVED:" + name
                  for name in sorted(names.intersection(cut_blocked_combinations)))
    rowset = ((source.get("column_axial") or {}).get("force_source") or {}).get("rowsets", {}).get(uid)
    rows = list(native_frame_force_rows(rowset, uid)) if rowset is not None else []
    # ObjSta AND ElmSta are retained; two cuts at one object coordinate are not merged.
    def cut(row):
        return (float(row[1]), str(row[2]), float(row[3]))
    cuts = {cut(r) for r in rows}
    grouped: dict[tuple, list] = defaultdict(list)
    for row in rows:
        if str(row[4]) in names:
            grouped[(str(row[4]), *cut(row))].append(row)
    expected = {(name, *c) for name in names for c in cuts}
    missing = sorted(expected - grouped.keys())
    if not cuts:
        errors.append("NATIVE_CUT_CENSUS_MISSING")
    if missing:
        errors.append("SPECTRAL_CASE_CUT_COVERAGE_INCOMPLETE")
    if names - {key[0] for key in grouped}:
        errors.append("SPECTRAL_REQUIRED_COMBINATION_MISSING")
    for key, grp in grouped.items():
        steps = [str(r[5]).strip().lower() for r in grp]
        if sorted(steps) != ["max", "min"]:
            errors.append("SPECTRAL_MIN_MAX_STEP_PAIR_MISSING_OR_AMBIGUOUS:" + str(key))
        if any(not math.isfinite(float(r[i])) for r in grp for i in (1, 3, 7, 11, 12)):
            errors.append("SPECTRAL_NONFINITE_SOURCE_VALUE:" + str(key))

    def positive(value):
        try:
            return not isinstance(value, bool) and math.isfinite(float(value)) and float(value) > 0
        except (TypeError, ValueError, OverflowError):
            return False
    nk = {}
    for axis in ("M2", "M3"):
        stiff = stiffness_map.get(axis) or {}
        value = (stiff.get("selected_nk_kn") if adopted_basis else stiff.get("selected_nk_ts500_7_20_kn")) if use_engineer else (
            stiff.get("preferred_nk_kn") or stiff.get("nk_ts500_7_21_kn"))
        if not positive(value):
            errors.append("SPECTRAL_EULER_LOAD_MISSING_OR_INVALID:" + axis)
        else:
            nk[axis] = float(value)
    if not positive(global_beta_ii) or float(global_beta_ii) < 1.0:
        errors.append("SPECTRAL_GLOBAL_SECOND_ORDER_FACTOR_UNPROVEN")
    if adopted_basis:
        for axis in ("M2", "M3"):
            if adopted_basis["member"]["axes"][axis]["cm_policy"] != "UNITY":
                errors.append("ADOPTED_SPECTRAL_CM_REQUIRES_UNITY:" + axis)
    result = {
        "schema": "tbdy.next.spectral-bounding-pmm.v2",
        "basis": "NONCONCURRENT_ENVELOPE_8_CORNER_REFERENCE_NOT_FULL_DOMAIN_PROOF",
        "status": "SPECTRAL_BOUNDING_INPUT_OR_COVERAGE_BLOCKED",
        "combinations_expected": sorted(names),
        "combinations_evaluated": [],
        "combinations_observed": sorted({key[0] for key in grouped}),
        "expected_case_cut_count": len(expected),
        "observed_case_cut_count": len(grouped),
        "missing_case_cuts": [list(k) for k in missing],
        "coverage_complete": not errors,
        "coverage_basis": "SOURCE_WIDE_NATIVE_CUT_CENSUS_NOT_PHYSICAL_CUT_ACCEPTANCE",
        "evaluated_corner_count": 0,
        "governing_combination": None,
        "governing_station_m": None,
        "governing_corner": None,
        "max_bounding_utilization": None,
        "reason_codes": sorted(set(errors)),
        "formal_compliance": "NOT_PROVEN",
        **({"second_order_basis_sha256": adopted_basis["basis_sha256"],
            "global_factor_policy": adopted_basis["global_factor_policy"]} if adopted_basis else {}),
    }
    if errors:
        return result
    max_util, corner_count = 0.0, 0
    gov_combo = gov_sta = None
    governing_corner = None
    numeric_block = False
    outside = False
    for (name, sta, elm, elmsta), grp in sorted(grouped.items()):
        nds = [-float(r[7]) for r in grp]
        m2_abs, m3_abs = (max(abs(float(r[idx])) for r in grp) for idx in (11, 12))
        for nd in sorted({min(nds), max(nds)}):
            adopted_factors = {}
            if adopted_basis:
                adopted_factors = {axis: _adopted_axis_factor(adopted_basis, axis, name, nd, nk[axis],
                                                            stiffness_map[axis], spectral=True) for axis in ("M2", "M3")}
                factors = {axis: ref.get("final_factor") for axis, ref in adopted_factors.items()}
                errors.extend("ADOPTED_SECOND_ORDER:" + ref["reason"] + ":" + name + ":" + axis
                              for axis, ref in adopted_factors.items() if ref.get("status") == "BLOCKED")
            else:
                factors = {axis: (moment_magnification_factors(
                    nd_kn=nd, nk_kn=nk[axis], sway=SWAY_PREVENTED,
                    horizontal_load_between_ends=True).get("beta") if nd > 0 else 1.0)
                    for axis in ("M2", "M3")}
            if any(not positive(v) for v in factors.values()):
                numeric_block = True
                continue
            for sign2 in (1.0, -1.0):
                for sign3 in (1.0, -1.0):
                    demand = _magnified_moment_demand(
                        nd_kn=nd, m2_knm=sign2*m2_abs, m3_knm=sign3*m3_abs, dims=dims_local,
                        beta_m2=factors["M2"], beta_m3=factors["M3"], global_factor=float(global_beta_ii))
                    assessment = cap_solver.assess(nd*1000.0, demand["magnified_m2_design_knm"]*1e6,
                                                   demand["magnified_m3_design_knm"]*1e6)
                    corner_count += 1
                    witness = {
                        "combination": name, "object_station_m": sta,
                        "analysis_element_id": elm, "element_station_m": elmsta,
                        "nd_kn": nd, **demand,
                        "status": assessment.get("status"),
                        "utilization": _assessed_utilization(assessment),
                        "basis": "NONCONCURRENT_COMPONENT_BOX_CORNER_NOT_NATIVE_FORCE_VECTOR",
                        **({"adopted_axis_factors": adopted_factors,
                            "second_order_basis_sha256": adopted_basis["basis_sha256"]} if adopted_basis else {}),
                    }
                    if assessment.get("status") == "OUTSIDE_SCENARIO_AXIAL_RANGE":
                        outside = True
                        gov_combo, gov_sta = name, sta
                        governing_corner = witness
                        continue
                    util = _assessed_utilization(assessment)
                    if util is None:
                        numeric_block = True
                    elif not outside and util >= max_util:
                        max_util, gov_combo, gov_sta = util, name, sta
                        governing_corner = witness
    result.update(evaluated_corner_count=corner_count,
                  combinations_evaluated=sorted(names), governing_combination=gov_combo,
                  governing_station_m=gov_sta,
                  governing_corner=governing_corner if not numeric_block else None,
                  max_bounding_utilization=max_util if not (numeric_block or outside) else None)
    if numeric_block:
        result["status"] = "SPECTRAL_BOUNDING_NUMERIC_UNRESOLVED"
        result["reason_codes"] = sorted(set(["SPECTRAL_CORNER_SOLVER_OR_MAGNIFICATION_UNRESOLVED", *errors]))
    elif outside or max_util > 1.0 + 1e-6:
        result["status"] = "CONSERVATIVE_CORNER_EXCEEDS_1_0_CONCURRENT_VECTOR_REQUIRED"
        if outside:
            result["reason_codes"] = ["SPECTRAL_CORNER_OUTSIDE_REFERENCE_AXIAL_RANGE"]
    else:
        result["status"] = "BOUNDED_CORNER_ENVELOPE_WITHIN_CAPACITY_NOT_PROVEN"
    return result


def project_column_r08_local_live(
    source: Mapping[str, Any],
    geometry: Mapping[str, Any] | None,
    axial: Mapping[str, Any] | None,
    pmm: Mapping[str, Any] | None,
    global_pdelta: Mapping[str, Any] | None = None,
    *,
    r10_live: Mapping[str, Any] | None = None,
    selected_cages: Mapping[str, SelectedColumnCage] | None = None,
    dependency_plan: Mapping[str, Any] | None = None,
    demand_revision: Mapping[str, Any] | None = None,
    previous_result: Mapping[str, Any] | None = None,
    recompute_member_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    """Project R08 reference scenarios using the same candidate section as R10 when supplied."""
    if pmm is None or axial is None or "column_axial" not in source:
        return None
    if dependency_plan is not None:
        from .design_dependencies import verify_dependency_source
        verify_dependency_source(dependency_plan, source)
    col_selection_enabled = source.get("column_selection") is not None
    if demand_revision is not None:
        from .alpha_iteration import validate_record, DEMAND_SCHEMA
        from .design_scenario import _digest
        validate_record(demand_revision, DEMAND_SCHEMA)
        if (dependency_plan is None or demand_revision["input_sha256"] != dependency_plan["input_sha256"]
                or demand_revision["source_payload_sha256"] != _digest(source)):
            raise ValueError("ALPHA_DEMAND_SOURCE_MISMATCH")
    if previous_result is not None and recompute_member_ids is None:
        raise ValueError("ALPHA_R08_REUSE_SCOPE_REQUIRED")
    basis_document = None
    basis_source_payload_sha256 = None
    if source.get("second_order_basis") is not None:
        from .design_scenario import _digest, _source_data
        from .second_order_basis import normalize_second_order_basis

        basis_document = normalize_second_order_basis(source["second_order_basis"],
                                                      source_data_sha256=_digest(_source_data(source)))
        from .column_axial import _columns

        known_members = {str(member["element_id"]) for member in _columns(geometry or {})}
        if set(basis_document["members"]) - known_members:
            raise ValueError("SECOND_ORDER_BASIS_MEMBER_OUTSIDE_PHYSICAL_ROSTER")
        basis_source_payload_sha256 = _digest(source)
    physical_lengths = ((r10_live or {}).get("physical_clear_lengths") or {}).get("per_member", {})
    end_ratios = reference_end_ratios(source, physical_lengths)
    mat_supports = project_mat_horizontal_supports(source, physical_lengths)

    def _reported_selection(uid: str) -> Mapping[str, Any] | None:
        if not r10_live:
            return None
        per_member = r10_live.get("per_member")
        if per_member is not None:
            return (per_member.get(uid) or {}).get("engineer_column_selection")
        if r10_live.get("member_id") == uid:
            return r10_live.get("engineer_column_selection")
        return None

    def _eng_section_for(uid: str) -> tuple[Mapping[str, Any] | None, Any]:
        if not col_selection_enabled:
            return None, None
        reported = _reported_selection(uid)
        if selected_cages is not None:
            cage = selected_cages.get(uid)
            if (not isinstance(cage, SelectedColumnCage) or cage.selection.get("member_id") != uid
                    or not cage.selection.get("selected") or not isinstance(cage.section, Section)
                    or (r10_live is not None and reported is not cage.selection)):
                return None, None
            if dependency_plan is not None:
                from .design_scenario import _digest
                from dataclasses import asdict
                if (cage.input_sha256 != dependency_plan["input_sha256"]
                        or cage.candidate_sha256 != _digest({"selection": cage.selection, "section": asdict(cage.section)})):
                    return None, None
            return cage.selection, cage.section

        # Legacy callers may only have archived JSON; retain their original reference path.
        from .column_r10_live import _evaluate_engineer_column_selection, member_local_axis_angle_deg

        ang = member_local_axis_angle_deg(source, uid)
        calc_res, calc_sec = _evaluate_engineer_column_selection(
            uid=uid, source=source, geometry=geometry, axial=axial, angle_deg=ang,
        )
        return reported or calc_res, calc_sec

    def _project_member(member: Mapping[str, Any]) -> dict[str, Any]:
        uid = member.get("member_id")
        physical_length = physical_lengths.get(uid)
        boundary = {"mat_horizontal_support": mat_supports[uid]} if uid in mat_supports else {}
        adopted_basis = None
        basis_error = None
        if basis_document is not None:
            from .second_order_basis import member_second_order_basis

            expected_combinations = {str(c["name"]) for c in (axial.get("combination_plan") or {}).get("combinations", ()) if c.get("name")}
            observed_combinations = {str(row["combination"]) for row in member.get("rows", ()) if row.get("combination")}
            try:
                if uid in basis_document["members"] and not expected_combinations:
                    raise ValueError("ADOPTED_SECOND_ORDER_EXPECTED_COMBINATION_PLAN_MISSING")
                adopted_basis = member_second_order_basis(basis_document, uid, expected_combinations | observed_combinations)
            except ValueError as exc:
                basis_error = str(exc)
        if dependency_plan is not None:
            from .design_dependencies import blocked_member_result
            dep = dependency_plan["members"].get(uid) or {}
            if not dep.get("source_execution_allowed"):
                return {**blocked_member_result(
                    uid, list(dep.get("reason_codes") or ["DESIGN_MEMBER_INPUT_UNAVAILABLE"]), schema=SCHEMA),
                    **boundary}
        e_res, e_sec = _eng_section_for(uid) if uid else (None, None)
        if dependency_plan is not None and col_selection_enabled and e_sec is None:
            return {**blocked_member_result(uid, [_SELECTED_CAGE_UNAVAILABLE], schema=SCHEMA), **boundary}
        binding = None
        if dependency_plan is not None:
            from .design_scenario import _digest
            binding = _digest({"input_sha256": dependency_plan["input_sha256"],
                "pmm_member": member, "candidate": selected_cages[uid].candidate_sha256
                    if selected_cages and uid in selected_cages else None,
                "global_second_order": global_pdelta,
                **({"physical_clear_length": physical_length} if physical_length is not None else {}),
                **({"adopted_second_order_basis": adopted_basis, "adopted_second_order_error": basis_error}
                   if basis_document is not None else {}),
                "absolute_alpha_factors": (demand_revision or {}).get("factors", {}).get(uid, {})})
        if previous_result is not None and uid not in recompute_member_ids:
            prior = (previous_result.get("per_member") or {}).get(uid)
            if prior is None:
                raise ValueError("ALPHA_PREVIOUS_R08_MEMBER_MISSING:" + str(uid))
            if binding is None or prior.get("input_binding_sha256") != binding:
                raise ValueError("ALPHA_PREVIOUS_R08_INPUT_REVISION_CHANGED:" + str(uid))
            return prior
        from .alpha_iteration import revised_pmm_member
        revised_member = revised_pmm_member(member, source, demand_revision)
        result = _project_single_r08_local(
            source, geometry, axial, revised_member, global_pdelta,
            eng_col_res=e_res, eng_col_section=e_sec, physical_length=physical_length,
            adopted_basis=adopted_basis, adopted_basis_error=basis_error,
            restraint_axes=end_ratios.get(uid),
        )
        if adopted_basis is not None:
            cage = (selected_cages or {}).get(uid)
            result["second_order_basis_application"] = {
                "status": result["second_order_basis_status"], "member_id": uid,
                "source_data_sha256": adopted_basis["source_data_sha256"],
                "input_payload_sha256": basis_source_payload_sha256,
                "basis_sha256": adopted_basis["basis_sha256"],
                "member_basis_sha256": adopted_basis["member_basis_sha256"],
                "selected_cage_sha256": cage.candidate_sha256 if isinstance(cage, SelectedColumnCage) else None,
                "engineering_approval": "NOT_GRANTED",
            }
        if not adopted_basis and uid in end_ratios and result.get("stiffness_and_euler"):
            result["effective_length_reference"] = effective_length_reference(
                end_ratios[uid], result, revised_member["section_evidence"],
            )
        result.update(boundary)
        if binding is not None:
            result["input_binding_sha256"] = binding
        if demand_revision is not None:
            result["alpha_demand_revision_sha256"] = demand_revision["sha256"]
        if selected_cages is not None and col_selection_enabled and e_sec is None:
            result["open_gates"].append(_SELECTED_CAGE_UNAVAILABLE)
        return result

    if pmm.get("scope") == "ALL_COLUMNS" or pmm.get("member_id") == "ALL":
        per_member: dict[str, dict[str, Any]] = {}
        for m_pmm in pmm.get("members") or ():
            muid = m_pmm.get("member_id")
            if not muid:
                continue
            per_member[muid] = _project_member(m_pmm)
        open_gates = list(OPEN_GATES)
        span_issues = [r for r in per_member.values() if r.get("span_basis") != FACE_BASIS]
        if per_member and all(WALL_COUPLED_LENGTH_GATE in r.get("open_gates", ()) for r in span_issues):
            open_gates.remove(PHYSICAL_CLEAR_LENGTH_GATE)
        if any(WALL_COUPLED_LENGTH_GATE in r.get("open_gates", ()) for r in span_issues):
            open_gates.append(WALL_COUPLED_LENGTH_GATE)
        if any(_SELECTED_CAGE_UNAVAILABLE in member["open_gates"] for member in per_member.values()):
            open_gates.append(_SELECTED_CAGE_UNAVAILABLE)
        return {
            "schema": SCHEMA,
            "scope": "ALL_COLUMNS",
            "member_id": "ALL",
            "evaluated_column_count": sum(r.get("execution_status") != "NOT_RUN" for r in per_member.values()),
            **({"expected_column_count": len(per_member),
                "blocked_column_count": sum(r.get("execution_status") == "NOT_RUN" for r in per_member.values())}
               if dependency_plan is not None else {}),
            "per_member": per_member,
            "open_gates": open_gates,
            "status": "REFERENCE_SLENDERNESS_CALCULATED" if per_member else "OBSERVED_EVIDENCE_ONLY",
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
        }

    return _project_member(pmm)
