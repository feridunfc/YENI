"""R14 single-column end-to-end closure and R15 building-wide column population ledger.

Deterministic report/pipeline-time projection unifying:
- Axial caps (CHK-004 / CHK-005) & approved combination plan (`ASSIGNED_DESIGN`),
- Engineer-selected column longitudinal + stirrup/crosstie cage,
- Second-order P-Delta (R08 global) & P-delta (R08-Local TS 500 7.6.2) magnified PMM,
- Connected beam capacity & Ve = Vdy + (Mpi + Mpj)/ln (R10/R12),
- Capacity shear Ve vs selected Vr (CHK-126 / R12),
- SCWB (TBDY 7.3.6) & story alpha_i demand feedback (R11),
- Beam-column joint shear Vj = 1.25*fyk*(As1+As2) - Vkol & TBDY 7.5.2.3 transverse (R13).

Results are persisted by the pipeline owner; this function itself has no I/O.
Missing/blocked dependencies cannot produce numerical closure.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from .column_r08_local_live import global_pdelta_precheck_within_limit
from .scwb_axial import qualified_interval_ratio


SCHEMA = "tbdy.next.column-r14-r15-closure.v2"

_STANDARD_R14_OPEN_GATES = (
    "EFFECTIVE_LENGTH_K_AND_SWAY_CLASSIFICATION_NOT_APPROVED",
    "CREEP_RATIO_RM_AND_CRACKED_SECTION_STIFFNESS_NOT_APPROVED",
    "PHYSICAL_JOINT_FACES_OFFSETS_AND_ANCHORAGE_NOT_PROVEN",
)
_ALLOWED_STANDARD_OPEN_GATES = frozenset(
    (*_STANDARD_R14_OPEN_GATES, "TS500_CREEP_RATIO_RM_NOT_APPROVED")
)


def _cracked_stiffness_tbdy_4_2_verified(analysis_setup_reconciliation: Mapping[str, Any] | None) -> bool:
    audit = (analysis_setup_reconciliation or {}).get("cracked_section_stiffness_audit") or {}
    return bool(audit.get("all_columns_match_0_70")) and bool(audit.get("all_beams_match_0_35"))


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _beam_ids_connected_to_member(
    det: Mapping[str, Any],
) -> list[str]:
    beam_ids: set[str] = set()
    for end_row in det.get("member_joint_ends") or ():
        for f_info in (end_row.get("faces") or {}).values():
            if f_info and f_info.get("frame_id"):
                beam_ids.add(f_info["frame_id"])
    for sc in det.get("scwb_joints") or ():
        for bid in sc.get("beam_ids") or ():
            beam_ids.add(bid)
    return sorted(beam_ids)


def _adopted_calculation_context(uid, plan, local, reconciliation, evidence):
    """Qualify conditional numerical completion, never engineering acceptance.

    A gate label alone is insufficient. The exact R08 result, selected cage,
    source payload, native parent and both normalized adopted documents must
    agree with the existing dependency ledger and the calculated axis inputs.
    """
    from .analysis_setup import normalize_analysis_basis, ADOPTED_ANALYSIS_PENDING
    from .design_scenario import _digest
    from .second_order_basis import normalize_second_order_basis, ACCEPTANCE_GATE

    applied = "ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN"
    try:
        local, reconciliation, evidence = local or {}, reconciliation or {}, evidence or {}
        basis = local.get("adopted_second_order_basis") or {}
        application = local.get("second_order_basis_application") or {}
        analysis = reconciliation.get("calculation_basis") or {}
        row = (evidence.get("columns") or {}).get(uid) or {}
        native_sha = basis.get("source_data_sha256")
        if (local.get("second_order_basis_status") != applied or application.get("status") != applied
                or local.get("status") != "ADOPTED_SECOND_ORDER_CALCULATED_NOT_PROVEN"
                or local.get("execution_status") == "NOT_RUN"
                or reconciliation.get("calculation_basis_status") != applied
                or reconciliation.get("engineering_approval") != "NOT_GRANTED"
                or reconciliation.get("analysis_generation_independently_verified") is not False
                or application.get("engineering_approval") != "NOT_GRANTED"
                or basis.get("member_id") != uid or application.get("member_id") != uid
                or application.get("source_data_sha256") != native_sha or analysis.get("source_data_sha256") != native_sha
                or not evidence.get("source_payload_sha256")
                or application.get("input_payload_sha256") != evidence["source_payload_sha256"]
                or not row.get("candidate_revision_sha256")
                or application.get("selected_cage_sha256") != row["candidate_revision_sha256"]
                or ACCEPTANCE_GATE not in local.get("open_gates", ())
                or ADOPTED_ANALYSIS_PENDING not in reconciliation.get("reconciled_blocker_codes", ())):
            return None
        artifact = (evidence.get("artifacts") or {}).get("r08:" + uid) or {}
        if artifact.get("payload_sha256") != _digest(local):
            return None
        resolved_keys = {"member_id", "member", "basis_sha256", "member_basis_sha256"}
        single_document = {**{k: v for k, v in basis.items() if k not in resolved_keys},
                           "members": {uid: basis["member"]}}
        normalized = normalize_second_order_basis(single_document, source_data_sha256=native_sha)
        if normalized != single_document or normalize_analysis_basis(analysis, source_data_sha256=native_sha) != analysis:
            return None
        if (reconciliation.get("calculation_basis_sha256") != _digest(analysis)
                or not basis.get("basis_sha256")
                or local.get("second_order_basis_sha256") != basis["basis_sha256"]
                or application.get("basis_sha256") != basis["basis_sha256"]
                or basis.get("member_basis_sha256") != _digest(basis["member"])
                or application.get("member_basis_sha256") != basis["member_basis_sha256"]
                or analysis["generation"]["source_analysis_order"] != basis["source_analysis_order"]):
            return None
        names = {c["name"] for c in plan.get("combinations", ())}
        groups = {k: sorted(v) for k, v in ((plan.get("design_assignment") or {}).get("groups") or {}).items() if v}
        force_groups = reconciliation.get("calculation_force_groups", analysis["design_groups"])
        if (not names or set(basis["member"]["combinations"]) != names or force_groups != groups
                or any(analysis["design_groups"].get(key) != value for key, value in groups.items())):
            return None
        archive_order = reconciliation.get("archived_analysis_order")
        if archive_order and (local.get("source_analysis_order") != archive_order["source_analysis_order"]
                              or local.get("archived_solver_log_sha256") != archive_order["solver_log_sha256"]):
            return None
        stiffness = local.get("stiffness_and_euler") or {}
        if set(stiffness) != {"M2", "M3"}:
            return None
        for axis, values in stiffness.items():
            adopted = basis["member"]["axes"][axis]
            used_k = _finite_number(values.get("effective_length_factor_k"))
            selection, resolution = adopted.get("k_source"), values.get("k_source_resolution")
            k_matches = used_k == adopted["k"]
            if selection is not None:
                resolution = resolution or {}
                ends = resolution.get("ends") or {}
                k_matches = (used_k is not None
                    and abs(used_k - adopted["k"]) <= 8 * max(math.ulp(used_k), math.ulp(adopted["k"]))
                    and resolution.get("status") == "CURRENT_FRAME_REFERENCE_CONSUMED"
                    and resolution.get("engineering_approval") == "NOT_GRANTED"
                    and resolution.get("method") == selection["method"] and resolution.get("section") == selection["section"]
                    and resolution.get("sway") == adopted["sway"] and resolution.get("computed_k") == used_k
                    and set(ends) == {"I", "J"}
                    and all(ends[e].get("basis") == "FRAME_SECTION_REFERENCE" for e in ("I", "J"))
                    and all(_finite_number(resolution.get(a)) is not None and resolution[a] >= 0
                            and resolution[a] == ends[e].get(selection["section"])
                            for a, e in (("alpha_i", "I"), ("alpha_j", "J"))))
            elif resolution is not None:
                k_matches = False
            if (values.get("adopted_axis_basis") != adopted
                    or not k_matches
                    or values.get("reference_creep_ratio_rm") != adopted["creep_ratio_rm"]
                    or values.get("ei_method_basis") != adopted["ei_method"] + "_ADOPTED_CALCULATION_ASSUMPTIONS"
                    or any((_finite_number(values.get(key)) or 0) <= 0
                           for key in ("free_length_ln_mm", "effective_length_lk_mm", "selected_nk_kn", "selected_ei_nmm2"))):
                return None
        magnified = local.get("magnified_selected_pmm") or {}
        if (not magnified.get("rows") or any(r.get("second_order_basis_sha256") != basis["basis_sha256"]
                for r in magnified["rows"])):
            return None
        spectral = local.get("spectral_envelope_pmm_scenario")
        if spectral is not None and spectral.get("second_order_basis_sha256") != basis["basis_sha256"]:
            return None
        return {"status": applied, "second_order_basis_sha256": basis["basis_sha256"],
                "analysis_basis_sha256": reconciliation["calculation_basis_sha256"],
                "source_data_sha256": native_sha, "selected_cage_sha256": row["candidate_revision_sha256"],
                "engineering_approval": "NOT_GRANTED", "analysis_generation_independently_verified": False}
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return None


def _evaluate_single_r14_column(
    *,
    uid: str,
    axial: Mapping[str, Any],
    axial_col: Mapping[str, Any],
    pmm_col: Mapping[str, Any] | None,
    r08_global: Mapping[str, Any] | None,
    r08_local_col: Mapping[str, Any] | None,
    beam_by_id: Mapping[str, Mapping[str, Any]],
    r10_det: Mapping[str, Any] | None,
    story_alpha: Mapping[str, Any] | None,
    analysis_setup_reconciliation: Mapping[str, Any] | None = None,
    pmm_cut_census_proven: bool | None = None,
    dependency_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    plan = axial.get("combination_plan") or {}
    normative_failures: list[str] = []
    cracked_verified = _cracked_stiffness_tbdy_4_2_verified(analysis_setup_reconciliation)
    open_gates: list[str] = [
        ("TS500_CREEP_RATIO_RM_NOT_APPROVED" if (cracked_verified and g == "CREEP_RATIO_RM_AND_CRACKED_SECTION_STIFFNESS_NOT_APPROVED") else g)
        for g in _STANDARD_R14_OPEN_GATES
    ]

    dependency_row = (dependency_evidence.get("columns", {}).get(uid) if dependency_evidence is not None else None)
    if dependency_evidence is not None:
        if dependency_row is None:
            open_gates.append("DESIGN_MEMBER_REVISION_EVIDENCE_MISSING")
        else:
            open_gates.extend("D2:" + code for code in dependency_row["open_gates"])

    if (r10_det or {}).get("alpha_joint_recheck_open_gate"):
        open_gates.append(r10_det["alpha_joint_recheck_open_gate"])
    alpha_consumed = bool(dependency_row and dependency_row.get("alpha_feedback_consumed") is True)
    alpha_not_required = bool(dependency_row and dependency_row.get("alpha_feedback_not_required") is True)
    # 1. Combination approval gate
    combo_approved_source = plan.get("source") == "ASSIGNED_DESIGN" and not plan.get("blockers")
    if not combo_approved_source:
        open_gates.append("COMBINATION_ROLE_ASSIGNMENT_UNAPPROVED")

    # 2. Axial cap (CHK-004 / CHK-005)
    ts500_lim = _finite_number(axial_col.get("ts500_limit_kn"))
    tbdy_lim = _finite_number(axial_col.get("tbdy_seismic_reference_limit_kn"))
    seismic_names = (
        set(((plan.get("design_assignment") or {}).get("groups") or {}).get("ductile", ()))
        if plan.get("source") == "ASSIGNED_DESIGN"
        else set()
    )
    axial_checks = axial_col.get("combination_checks") or []
    axial_demands = [(c.get("combination"), _finite_number(c.get("nd_kn"))) for c in axial_checks]
    chk005_fail = ts500_lim is not None and ts500_lim > 0 and any(
        nd is not None and nd > ts500_lim for _, nd in axial_demands)
    chk004_fail = tbdy_lim is not None and tbdy_lim > 0 and any(
        name in seismic_names and nd is not None and nd > tbdy_lim for name, nd in axial_demands)
    if chk005_fail:
        normative_failures.append("CHK005_TS500_AXIAL_CAP_EXCEEDED")
    if chk004_fail:
        normative_failures.append("CHK004_TBDY_SEISMIC_AXIAL_CAP_EXCEEDED")

    # 3. Engineer cage + Second-order magnified PMM
    det = r10_det or {}
    eng_col = det.get("engineer_column_selection") or {}
    sel_cage = eng_col.get("selected") or {}
    eng_sel_status = eng_col.get("status") or eng_col.get("selection_status")
    sel_ok = eng_sel_status in ("ENGINEER_COLUMN_SELECTED_NOT_PROVEN", "ENGINEER_COLUMN_REBAR_SELECTED_NOT_PROVEN") and bool(sel_cage)
    if not sel_ok:
        open_gates.append("COLUMN_ENGINEER_CAGE_NOT_SELECTED_OR_BLOCKED")

    mag_pmm = (r08_local_col or {}).get("magnified_selected_pmm") or {}
    mag_status = mag_pmm.get("status")
    if mag_status == "MAGNIFIED_PMM_EXCEEDS_CAPACITY":
        normative_failures.append("SECOND_ORDER_MAGNIFIED_SELECTED_PMM_EXCEEDED")
    elif mag_status == "SECOND_ORDER_BUCKLING_OR_BLOCKED":
        # This mixed upstream status does not prove a physical buckling failure.
        open_gates.append("SECOND_ORDER_BUCKLING_OR_SOURCE_BLOCK_UNRESOLVED")
    elif not mag_pmm:
        open_gates.append("SECOND_ORDER_MAGNIFIED_SELECTED_PMM_NOT_COMPUTED")

    spec_pmm = (r08_local_col or {}).get("spectral_envelope_pmm_scenario") or {}
    if spec_pmm.get("status") == "CONSERVATIVE_CORNER_EXCEEDS_1_0_CONCURRENT_VECTOR_REQUIRED":
        open_gates.append("SPECTRAL_PMM_CONSERVATIVE_BOX_EXCEEDS_1_0_CONCURRENT_VECTORS_NEEDED")

    global_pdelta_ok = global_pdelta_precheck_within_limit(r08_global)
    if r08_global is None:
        open_gates.append("GLOBAL_PDELTA_NOT_BOUND")
    elif global_pdelta_ok is False:
        open_gates.append("GLOBAL_PDELTA_EXCEEDS_REFERENCE_LIMIT_REQUIRES_STIFFENING")

    # 4. Column capacity shear Ve / Vr & confinement/crossties
    sel_tr = sel_cage.get("selected_transverse") or {}
    if sel_tr.get("all_tbdy_checks_met") is False:
        normative_failures.append("COLUMN_TRANSVERSE_AND_CROSSTIE_TBDY_RULES_NOT_MET")
    ts_block = det.get("column_transverse_and_shear") or {}
    ve_block = ts_block.get("engineer_capacity_shear_ve")
    spectral_shear = (ve_block or {}).get("assigned_spectral") or {}
    spectral_native_failures: list[dict[str, Any]] = []
    max_ve_ts500_util = None
    max_ve_zero_util = None
    if ve_block and ve_block.get("axes"):
        ts_utils = [n for a in ve_block["axes"].values()
                    if (n := _finite_number(a.get("max_utilization_ts500"))) is not None and n >= 0]
        z_utils = [n for a in ve_block["axes"].values()
                   if (n := _finite_number(a.get("max_utilization_zero_concrete"))) is not None and n >= 0]
        max_ve_ts500_util = max(ts_utils) if ts_utils else None
        max_ve_zero_util = max(z_utils) if z_utils else None
        if max_ve_ts500_util is not None and max_ve_ts500_util > 1.0 + 1e-6:
            normative_failures.append("COLUMN_CAPACITY_SHEAR_VE_EXCEEDS_TS500_VR")
    else:
        open_gates.append("COLUMN_CAPACITY_SHEAR_VE_UNBOUND")

    # 5. Connected beams: rebar, Vdy + Ve, stirrups
    conn_beam_ids = _beam_ids_connected_to_member(det)
    conn_beams = [beam_by_id[b] for b in conn_beam_ids if b in beam_by_id]
    beam_vdy_bound_all = bool(conn_beams) and all(
        ((b.get("engineer_shear_ve") or b.get("shear_ve") or {}).get("gravity_shear_vdy_kn")) is not None
        for b in conn_beams
    )
    if conn_beams and not beam_vdy_bound_all:
        open_gates.append("CONNECTED_BEAM_GRAVITY_SHEAR_VDY_NOT_CAPTURED")
    elif not conn_beams and det.get("member_joint_ends"):
        # Footing/free-cantilever columns have 0 beams; only flag if joints report beams that are missing from beam_r10
        if any(any(f is not None for f in (e.get("faces") or {}).values()) for e in det.get("member_joint_ends") or ()):
            open_gates.append("CONNECTED_BEAMS_NOT_EVALUATED")
    for b in conn_beams:
        st_b = b.get("engineer_stirrups") or {}
        if st_b:
            conf_b = st_b.get("confinement") or st_b.get("confinement_2h") or {}
            if conf_b.get("spacing_ok") is False or (conf_b.get("utilization_conservative") or 0.0) > 1.0 + 1e-6:
                normative_failures.append(f"CONNECTED_BEAM_STIRRUP_OR_VE_FAIL:{b['member_id']}")

    # 6. SCWB & story alpha_i feedback
    scwb_joints = det.get("scwb_joints") or []
    scwb_ratios: list[float] = []
    scwb_unsat = False
    scwb_unbound = not scwb_joints
    low_axial_joints = set()
    interval_directions = {}
    unresolved_seismic_nd = False
    for j in scwb_joints:
        exception = j.get("low_axial_exception") or {}
        if exception.get("exempt") is True:
            low_axial_joints.add(j["joint_id"])
            continue
        ratio = qualified_interval_ratio(j)
        if ratio is not None:
            interval_directions[j["joint_id"], j["direction"]] = ratio
            scwb_ratios.append(ratio)
            continue
        elif exception.get("status") in ("LOW_AXIAL_LIMIT_EXCEEDED", "UNRESOLVED"):
            unresolved_seismic_nd = True
        blk = j.get("engineer_selected_scwb") or j
        sat = blk.get("reference_satisfied" if "engineer_selected_scwb" in j else "scenario_reference_satisfied")
        rat = blk.get("sampled_minimum_normalized_ratio")
        if rat is not None:
            scwb_ratios.append(float(rat))
        if sat is False:
            scwb_unsat = True
        elif sat is None:
            scwb_unbound = True
    if scwb_unsat:
        # 7.3.6 permits an explicitly qualified alternative; low joint ratio
        # alone is not proof that the complete code branch has failed.
        open_gates.append("SCWB_JOINT_RATIO_REQUIRES_7_3_6_BRANCH_REVIEW")
    if unresolved_seismic_nd:
        open_gates.append("SCWB_SEISMIC_GOVERNING_ND_UNQUALIFIED")
    scwb_satisfied = (not scwb_unsat and not scwb_unbound) if scwb_joints else None
    if (low_axial_joints or unresolved_seismic_nd) and not scwb_unsat:
        scwb_satisfied = None
    if scwb_unbound and any(any(f is not None for f in (e.get("faces") or {}).values()) for e in det.get("member_joint_ends") or ()):
        open_gates.append("SCWB_JOINT_CAPACITIES_UNBOUND")

    col_story = str(axial_col.get("story") or (pmm_col or {}).get("story") or "")
    story_alpha_rows = [
        s for s in (story_alpha or {}).get("stories", ())
        if str(s.get("story")) == col_story
    ]
    if not story_alpha_rows and not alpha_not_required:
        open_gates.append("STORY_ALPHA_I_NOT_EVALUATED")
    elif not alpha_not_required:
        if any(s.get("denominator_status") != "FULL_STORY_COLUMN_DENOMINATOR" for s in story_alpha_rows):
            open_gates.append("STORY_ALPHA_I_PARTIAL_COLUMN_DENOMINATOR")
        if any(s.get("demand_feedback_action") == "STORY_SCWB_BELOW_0_70_SYSTEM_R_AND_DUCTILITY_REVIEW_REQUIRED" for s in story_alpha_rows):
            normative_failures.append("STORY_ALPHA_I_BELOW_0_70")
        elif not alpha_consumed and any(s.get("demand_feedback_action") == "AMPLIFY_COLUMN_DEMANDS_BY_1_OVER_ALPHA" for s in story_alpha_rows):
            open_gates.append("STORY_ALPHA_I_BETWEEN_0_70_AND_1_00_AMPLIFY_1_OVER_ALPHA_REQUIRED")

    # 7. Beam-column joint Vj & 7.5.2.3
    joint_ends_with_beams = [
        e for e in det.get("member_joint_ends") or ()
        if e.get("status") == "JOINT_GEOMETRIC_REFERENCES_CALCULATED"
    ]
    if not joint_ends_with_beams and any(any(f is not None for f in (e.get("faces") or {}).values()) for e in det.get("member_joint_ends") or ()):
        open_gates.append("JOINT_SHEAR_GEOMETRY_INCOMPLETE")
    vj_utils: list[float] = []
    joint_bound_exceedances: list[dict[str, Any]] = []
    for e in joint_ends_with_beams:
        for ax in e.get("axes") or ():
            if ax.get("calculation") is None:
                continue
            jve = ax.get("joint_shear_ve") or {}
            if jve.get("within_geometric_limit") is False:
                if str(jve.get("v_kol_basis", "")).startswith("CONSERVATIVE_ZERO_VKOL_"):
                    # An exceeded upper bound with an unbound deduction is not
                    # proof that the actual joint demand exceeds its limit.
                    open_gates.append(f"JOINT_SHEAR_CONSERVATIVE_BOUND_EXCEEDS_LIMIT_REFINEMENT_REQUIRED:{e['end']}:{ax['axis']}")
                    joint_bound_exceedances.append({
                        "end": e["end"], "axis": ax["axis"],
                        "v_kol_basis": jve.get("v_kol_basis"),
                        "governing_ve_kn": jve.get("governing_ve_kn"),
                        "geometric_limit_kn": jve.get("geometric_limit_kn"),
                        "utilization": jve.get("utilization"),
                        "missing_column_shear_combinations": jve.get("missing_column_shear_combinations", []),
                        "column_topology_issues": jve.get("column_topology_issues", []),
                    })
                else:
                    normative_failures.append(f"JOINT_SHEAR_VJ_EXCEEDS_7_5_2_2_LIMIT:{e['end']}:{ax['axis']}")
            elif jve.get("within_geometric_limit") is True and (util := _finite_number(jve.get("utilization"))) is not None and util >= 0:
                vj_utils.append(util)
            else:
                open_gates.append(f"JOINT_SHEAR_VE_UNBOUND:{e['end']}:{ax['axis']}")
            jt = ax.get("joint_transverse_7_5_2_3")
            if jt is None:
                open_gates.append(f"JOINT_TRANSVERSE_7_5_2_3_UNBOUND:{e['end']}:{ax['axis']}")
            elif jt.get("all_references_met") is False:
                normative_failures.append(f"JOINT_TRANSVERSE_7_5_2_3_NOT_MET:{e['end']}:{ax['axis']}")
            elif jt.get("all_references_met") is not True:
                open_gates.append(f"JOINT_TRANSVERSE_7_5_2_3_UNBOUND:{e['end']}:{ax['axis']}")

    # A nonempty dict is not a successful calculation. Positive completeness
    # proofs are required before assigning any numerical-closure status.
    def finite_number(value: Any, *, nonnegative: bool = False) -> bool:
        number = _finite_number(value)
        return number is not None and (not nonnegative or number >= 0.0)

    if analysis_setup_reconciliation is None:
        open_gates.append("R03_ANALYSIS_SETUP_RECONCILIATION_MISSING")
    else:
        open_gates.extend("R03:" + str(code) for code in
                          analysis_setup_reconciliation.get("reconciled_blocker_codes", ()))
    open_gates.extend("R08_LOCAL:" + str(code) for code in (r08_local_col or {}).get("open_gates", ()))
    adopted_context = _adopted_calculation_context(uid, plan, r08_local_col, analysis_setup_reconciliation, dependency_evidence)
    if (adopted_context is None and ((r08_local_col or {}).get("adopted_second_order_basis") is not None
                                   or (analysis_setup_reconciliation or {}).get("calculation_basis") is not None)):
        open_gates.append("ADOPTED_CALCULATION_BASIS_BINDING_UNVERIFIED")
    if pmm_cut_census_proven is False:
        open_gates.append("INDEPENDENT_ANALYSIS_CUT_CENSUS_NOT_PROVEN")
    pmm_result = pmm_col or {}
    expected_stations = pmm_result.get("expected_station_count")
    evaluated_stations = pmm_result.get("evaluated_station_count")
    if (pmm_result.get("status") != "NUMERICAL_COMPLETE"
            or type(expected_stations) is not int or expected_stations <= 0
            or type(evaluated_stations) is not int or evaluated_stations != expected_stations):
        open_gates.append("COLUMN_PMM_RESULT_MISSING_OR_INCOMPLETE")

    expected_combos = {str(c["name"]) for c in plan.get("combinations", ()) if c.get("name")}
    if not expected_combos:
        groups = (plan.get("design_assignment") or {}).get("groups") or {}
        expected_combos = {str(n) for names in groups.values() for n in names}
    observed_combos = {str(name) for name, nd in axial_demands if nd is not None}
    if not expected_combos or not expected_combos <= observed_combos:
        open_gates.append("AXIAL_REQUIRED_COMBINATION_COVERAGE_INCOMPLETE")
    if ts500_lim is None or ts500_lim <= 0:
        open_gates.append("TS500_AXIAL_LIMIT_MISSING_OR_INVALID")
    if seismic_names and (tbdy_lim is None or tbdy_lim <= 0):
        open_gates.append("TBDY_AXIAL_LIMIT_MISSING_OR_INVALID")
    if not axial_demands or any(nd is None for _, nd in axial_demands):
        open_gates.append("AXIAL_DEMAND_MISSING_OR_INVALID")

    mag_numeric_ok = (mag_status == "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN"
                      and type(expected_stations) is int and expected_stations > 0
                      and all(type(mag_pmm.get(key)) is int and mag_pmm[key] == expected_stations
                              for key in ("expected_row_count", "evaluated_row_count", "resolved_row_count"))
                      and finite_number(mag_pmm.get("max_utilization"), nonnegative=True)
                      and float(mag_pmm["max_utilization"]) <= 1.0 + 1e-6)
    if not mag_numeric_ok and mag_status != "MAGNIFIED_PMM_EXCEEDS_CAPACITY":
        open_gates.append("SECOND_ORDER_PMM_NOT_NUMERICALLY_RESOLVED")
    if global_pdelta_ok is not True:
        open_gates.append("GLOBAL_PDELTA_UNKNOWN_OR_NOT_ACCEPTED")
    if not sel_tr or sel_tr.get("all_tbdy_checks_met") is not True:
        open_gates.append("SELECTED_TRANSVERSE_RESULT_MISSING_OR_UNRESOLVED")
    if not finite_number(sel_cage.get("rho"), nonnegative=True):
        open_gates.append("SELECTED_LONGITUDINAL_RATIO_MISSING_OR_INVALID")
    elif not 0.01 <= float(sel_cage["rho"]) <= 0.04:
        open_gates.append("SELECTED_REBAR_OUTSIDE_SUPPORTED_TBDY_RANGE_REVIEW_REQUIRED")

    spectral_required = {str(c["name"]) for c in plan.get("combinations", ())
                         if c.get("force_semantics") == "SCALAR_COMPONENT_ENVELOPE"}
    if spectral_required:
        if not (spec_pmm.get("status") == "BOUNDED_CORNER_ENVELOPE_WITHIN_CAPACITY_NOT_PROVEN"
                and spec_pmm.get("coverage_complete") is True
                and spectral_required <= set(spec_pmm.get("combinations_evaluated", ()))
                and finite_number(spec_pmm.get("max_bounding_utilization"), nonnegative=True)):
            open_gates.append("SPECTRAL_PMM_REQUIRED_POPULATION_NOT_PROVEN")
        from .column_spectral_shear import complete_spectral_shear, spectral_native_brittle_violations
        spectral_native_failures = spectral_native_brittle_violations(
            spectral_shear, seismic_names & spectral_required, uid,
            (dependency_evidence or {}).get("input_sha256"),
            (dependency_row or {}).get("spectral_shear_sha256"))
        normative_failures.extend("COLUMN_NATIVE_SPECTRAL_SHEAR_EXCEEDS_TBDY_EQ_7_7:"
                                  + case["combination"] + ":" + case["axis"]
                                  for case in spectral_native_failures)
        if seismic_names & spectral_required and not (alpha_not_required and complete_spectral_shear(
                spectral_shear, seismic_names & spectral_required, uid, dependency_evidence.get("input_sha256"),
                dependency_row.get("spectral_shear_sha256"))):
            open_gates.append("SCWB_AND_CAPACITY_SHEAR_SPECTRAL_DEMAND_POLICY_NOT_PROVEN")

    ve_axes = (ve_block or {}).get("axes") or {}
    if not {"V2", "V3"} <= set(ve_axes):
        open_gates.append("COLUMN_CAPACITY_SHEAR_BOTH_AXES_REQUIRED")
    for axis in ("V2", "V3"):
        ve_a = ve_axes.get(axis) or {}
        if not finite_number(ve_a.get("max_utilization_ts500"), nonnegative=True):
            open_gates.append("COLUMN_SHEAR_UTILIZATION_MISSING_OR_INVALID:" + axis)
        zero_u = ve_a.get("max_utilization_zero_concrete")
        if not finite_number(zero_u, nonnegative=True):
            open_gates.append("COLUMN_ZERO_CONCRETE_REFERENCE_MISSING:" + axis)
        elif float(zero_u) > 1.0 + 1e-6:
            # Vc=0 has two simultaneous code conditions. Without applicability
            # evidence this is a review gate, not an invented physical FAIL.
            open_gates.append("COLUMN_ZERO_CONCRETE_BRANCH_REVIEW_REQUIRED:" + axis)

    missing_beams = sorted(set(conn_beam_ids) - set(beam_by_id))
    open_gates.extend("CONNECTED_BEAM_RESULT_MISSING:" + bid for bid in missing_beams)
    for b in conn_beams:
        conf = (b.get("engineer_stirrups") or {}).get("confinement") or (b.get("engineer_stirrups") or {}).get("confinement_2h") or {}
        if conf.get("spacing_ok") is None or not finite_number(conf.get("utilization_conservative"), nonnegative=True):
            open_gates.append("CONNECTED_BEAM_STIRRUP_RESULT_UNRESOLVED:" + str(b.get("member_id")))
    if not alpha_not_required and {str(r.get("direction")) for r in story_alpha_rows} != {"X", "Y"}:
        open_gates.append("STORY_ALPHA_BOTH_DIRECTIONS_REQUIRED")
    for row in (() if alpha_not_required else story_alpha_rows):
        if not finite_number(row.get("governing_alpha_i"), nonnegative=True):
            open_gates.append("STORY_ALPHA_VALUE_MISSING_OR_INVALID")
        if row.get("demand_feedback_action") not in ("NONE", "AMPLIFY_COLUMN_DEMANDS_BY_1_OVER_ALPHA",
                "STORY_SCWB_BELOW_0_70_SYSTEM_R_AND_DUCTILITY_REVIEW_REQUIRED"):
            open_gates.append("STORY_ALPHA_FEEDBACK_UNRESOLVED")
    # Geometry omission cannot be interpreted as a beamless/exceptional joint.
    joint_ends = det.get("member_joint_ends") or ()
    if len(joint_ends) != 2 or {end.get("end") for end in joint_ends} != {"I", "J"}:
        open_gates.append("PHYSICAL_JOINT_TOPOLOGY_NOT_OBSERVED")
    for end in joint_ends:
        if end.get("status") not in ("NO_RECORDED_BEAM_AT_NODE", "JOINT_GEOMETRIC_REFERENCES_CALCULATED"):
            open_gates.append("PHYSICAL_JOINT_END_UNRESOLVED:" + str(end.get("end")))
    for end in joint_ends_with_beams:
        faces = end.get("faces") or {}
        expected_axes = {f"V{axis}" for axis in (2, 3) if faces.get(f"{axis}+") or faces.get(f"{axis}-")}
        calculated_axes = [axis.get("axis") for axis in (end.get("axes") or ()) if axis.get("calculation") is not None]
        if not expected_axes or len(calculated_axes) != len(expected_axes) or set(calculated_axes) != expected_axes:
            open_gates.append("JOINT_APPLICABLE_AXIS_COVERAGE_INCOMPLETE:" + str(end.get("end")))

    dedup_failures = sorted(set(normative_failures))
    dedup_open = sorted(set(open_gates))
    conditional_acceptance_gates = set()
    if adopted_context is not None:
        conditional_acceptance_gates = {
            "R03:ADOPTED_ANALYSIS_BASIS_ENGINEERING_ACCEPTANCE_PENDING",
            "R08_LOCAL:ADOPTED_SECOND_ORDER_BASIS_ENGINEERING_ACCEPTANCE_PENDING",
            "R08_LOCAL:END_RESTRAINTS_K_AND_SWAY_CLASSIFICATION_NOT_APPROVED",
            "R08_LOCAL:CREEP_RATIO_RM_AND_SECTION_CRACKING_NOT_APPROVED",
            "R08_LOCAL:ACTUAL_ANALYSIS_ORDER_UNVERIFIED",
            "R08_LOCAL:EQ729_LENGTH_AMBIGUITY_NOT_RESOLVED",
        }
    binding_gaps = [g for g in dedup_open if g not in _ALLOWED_STANDARD_OPEN_GATES | conditional_acceptance_gates]

    if dedup_failures:
        closure_status = "R14_FAILED_NORMATIVE_CHECK"
    elif combo_approved_source and sel_ok and mag_pmm and not binding_gaps:
        closure_status = "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES"
    else:
        closure_status = "R14_PARTIAL_OR_UNBOUND"

    return {
        "member_id": uid,
        "story": col_story or None,
        "section": axial_col.get("section") or (pmm_col or {}).get("section"),
        "status": closure_status,
        "pillars": {
            "combination_approval": {
                "source": plan.get("source"),
                "approved_design_groups": combo_approved_source,
            },
            "axial_caps": {
                "n_max_kn": (
                    axial_col.get("n_max_kn")
                    if axial_col.get("n_max_kn") is not None
                    else (axial_col.get("governing") or {}).get("nd_kn")
                ),
                "ts500_limit_kn": ts500_lim,
                "tbdy_limit_kn": tbdy_lim,
                "chk005_failed": chk005_fail,
                "chk004_failed": chk004_fail,
            },
            "second_order_selected_pmm": {
                "selection_status": eng_sel_status,
                "longitudinal_label": sel_cage.get("label"),
                "transverse_label": sel_tr.get("confinement_label"),
                "magnified_pmm_status": mag_status,
                "max_magnified_utilization": mag_pmm.get("max_utilization"),
                "governing_combination": mag_pmm.get("governing_combination"),
                "governing_static_station": mag_pmm.get("governing_station"),
                "max_reference_beta_sway_prevented": (r08_local_col or {}).get("max_reference_beta_sway_prevented"),
                "global_pdelta_within_limit": global_pdelta_ok,
                **({"mat_horizontal_support_status": r08_local_col["mat_horizontal_support"]["status"]}
                   if r08_local_col and "mat_horizontal_support" in r08_local_col else {}),
                "cracked_stiffness_tbdy_4_2_verified": cracked_verified,
                "spectral_envelope_pmm_status": spec_pmm.get("status"),
                "spectral_envelope_max_utilization": spec_pmm.get("max_bounding_utilization"),
                **({"adopted_calculation_context": adopted_context} if adopted_context is not None else {}),
                **({"gravity_order_comparison": {
                    key: value for key, value in r08_local_col["gravity_order_pair"].items() if key != "rows"
                }} if r08_local_col and "gravity_order_pair" in r08_local_col else {}),
            },
            "column_shear_ve": {
                **({"assigned_spectral_status": spectral_shear.get("status"),
                    "spectral_case_axis_count": spectral_shear.get("calculated_axis_case_count", 0),
                    "max_spectral_resistance_utilization": spectral_shear.get("max_resistance_utilization"),
                    "max_spectral_brittle_utilization": spectral_shear.get("max_brittle_utilization"),
                    "max_native_spectral_brittle_utilization": spectral_shear.get("max_native_brittle_utilization"),
                    "qualified_native_brittle_failures": spectral_native_failures}
                   if spectral_shear else {}),
                "max_ve_ts500_utilization": max_ve_ts500_util,
                "max_ve_zero_concrete_utilization": max_ve_zero_util,
                "all_tbdy_transverse_checks_met": sel_tr.get("all_tbdy_checks_met") if sel_tr else None,
            },
            "connected_beams": {
                "beam_ids": conn_beam_ids,
                "all_vdy_bound": beam_vdy_bound_all if conn_beams else None,
            },
            "scwb_and_story_alpha": {
                "min_scwb_ratio": min(scwb_ratios) if scwb_ratios else None,
                "min_seismic_interval_ratio_lower": min(interval_directions.values(), default=None),
                "alternative_not_required_for_selected_scenario": alpha_not_required,
                "scwb_satisfied": scwb_satisfied,
                "low_axial_exempt_joint_ids": sorted(low_axial_joints),
                "seismic_interval_qualified_joint_directions": [
                    {"joint": point, "direction": direction, "minimum_ratio_lower": value}
                    for (point, direction), value in sorted(interval_directions.items())],
                "story_alpha_rows": [
                    {
                        "direction": s.get("direction"),
                        "governing_alpha_i": s.get("governing_alpha_i"),
                        "denominator_status": s.get("denominator_status"),
                        "demand_feedback_action": s.get("demand_feedback_action"),
                    }
                    for s in story_alpha_rows
                ],
            },
            "joint_shear_and_transverse": {
                "max_vj_utilization": max(vj_utils) if vj_utils else None,
                "conservative_bound_exceedances": joint_bound_exceedances,
            },
        },
        **({"design_dependency_revision": dependency_row} if dependency_evidence is not None else {}),
        "normative_failures": dedup_failures,
        "open_gates": dedup_open,
        "formal_compliance": "FAIL" if dedup_failures else "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }


def project_column_r14_and_r15_closure(
    *,
    geometry: Mapping[str, Any] | None,
    axial: Mapping[str, Any] | None,
    pmm: Mapping[str, Any] | None,
    r08_second_order: Mapping[str, Any] | None,
    r08_local: Mapping[str, Any] | None,
    beam_r10: Mapping[str, Any] | None,
    r10_live: Mapping[str, Any] | None,
    analysis_setup_reconciliation: Mapping[str, Any] | None = None,
    pmm_cut_census_proven: bool | None = None,
    dependency_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Project R14 end-to-end single-column closure or R15 full-population ledger."""
    if axial is None or pmm is None or geometry is None:
        return None
    if dependency_evidence is not None:
        from .design_dependencies import validate_revision_evidence
        validate_revision_evidence(dependency_evidence)
    beam_by_id = {b["member_id"]: b for b in (beam_r10 or {}).get("beams") or ()}
    axial_by_id = {c["element_id"]: c for c in axial.get("columns", ())}
    story_alpha = (r10_live or {}).get("story_alpha")

    is_all = bool(pmm.get("scope") == "ALL_COLUMNS" or pmm.get("member_id") == "ALL")
    if not is_all:
        uid = pmm.get("member_id")
        if not uid or uid not in axial_by_id:
            return None
        col_closure = _evaluate_single_r14_column(
            uid=uid,
            axial=axial,
            axial_col=axial_by_id[uid],
            pmm_col=pmm,
            r08_global=r08_second_order,
            r08_local_col=r08_local,
            beam_by_id=beam_by_id,
            r10_det=r10_live,
            story_alpha=story_alpha,
            analysis_setup_reconciliation=analysis_setup_reconciliation,
            pmm_cut_census_proven=pmm_cut_census_proven, dependency_evidence=dependency_evidence,
        )
        return {
            "schema": SCHEMA,
            "scope": "SINGLE_COLUMN",
            "member_id": uid,
            **col_closure,
        }

    expected_ids = [
        row["element_id"]
        for row in next((c["items"] for c in geometry.get("checks", ()) if c.get("check_id") == "column_rect_min"), ())
        if row.get("status") != "NOT_APPLICABLE"
    ]
    pmm_by_id = {m["member_id"]: m for m in pmm.get("members") or () if m.get("member_id")}
    local_by_id = (r08_local or {}).get("per_member") or {}
    r10_by_id = (r10_live or {}).get("per_member") or {}

    columns_out: list[dict[str, Any]] = []
    missing_ids: list[str] = []
    for uid in expected_ids:
        if uid not in axial_by_id or uid not in pmm_by_id:
            missing_ids.append(uid)
            columns_out.append({
                "member_id": uid, "status": "R14_PARTIAL_OR_UNBOUND",
                "normative_failures": [], "open_gates": ["EXPECTED_COLUMN_INPUT_MISSING"],
                "pillars": {}, "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
            })
            continue
        columns_out.append(_evaluate_single_r14_column(
            uid=uid,
            axial=axial,
            axial_col=axial_by_id[uid],
            pmm_col=pmm_by_id.get(uid),
            r08_global=r08_second_order,
            r08_local_col=local_by_id.get(uid),
            beam_by_id=beam_by_id,
            r10_det=r10_by_id.get(uid),
            story_alpha=story_alpha,
            analysis_setup_reconciliation=analysis_setup_reconciliation,
            pmm_cut_census_proven=pmm_cut_census_proven, dependency_evidence=dependency_evidence,
        ))

    closed_n = sum(c["status"] == "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES" for c in columns_out)
    fail_n = sum(c["status"] == "R14_FAILED_NORMATIVE_CHECK" for c in columns_out)
    partial_n = sum(c["status"] == "R14_PARTIAL_OR_UNBOUND" for c in columns_out)
    full_denom = not missing_ids and len(columns_out) == len(expected_ids) and len(expected_ids) > 0
    if not full_denom:
        building_status = "R15_PARTIAL_COLUMN_POPULATION"
    elif fail_n > 0:
        building_status = "R15_ALL_COLUMNS_EVALUATED_WITH_FAILURES"
    elif closed_n == len(columns_out):
        building_status = "R15_ALL_COLUMNS_CLOSED_NOT_PROVEN"
    else:
        building_status = "R15_ALL_COLUMNS_EVALUATED_PARTIAL_GATES"

    return {
        "schema": SCHEMA,
        "scope": "ALL_COLUMNS",
        "member_id": "ALL",
        "expected_column_count": len(expected_ids),
        "evaluated_column_count": len(columns_out) - len(missing_ids),
        "ledger_column_count": len(columns_out),
        "missing_column_ids": missing_ids,
        "numerically_closed_count": closed_n,
        "normative_fail_count": fail_n,
        "partial_or_unbound_count": partial_n,
        "story_alpha": story_alpha,
        "columns": columns_out,
        "status": building_status,
        "formal_compliance": "FAIL" if fail_n > 0 else "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
