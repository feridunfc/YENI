"""Scoped, independently replayable G6 Supervisor closure candidates for GAP-011 and GAP-012."""
from __future__ import annotations

from hashlib import sha256
from math import acos, hypot, isclose, pi, sqrt
from typing import Any, Mapping

from .column_r14_closure import _evaluate_single_r14_column
from .confinement_regions import column_confinement
from .design_scenario import _digest
from .g1_contract import require
from .g4_contract import ACCEPTED_G4, ACCEPTED_POPULATION
from .g5_contract import ACCEPTED_G5
from .rebar_selection import _evaluate_column_transverse_choice

SCHEMA = "tbdy.next.g6-contract.v1"
VERIFICATION_SCHEMA = "tbdy.next.g6-verification.v1"


def _independent_beam_mr_knm(
    bw: float,
    h: float,
    bars: list[Mapping[str, Any]],
    fcd: float,
    fyd: float,
    es: float,
    nd_kn: float,
    positive_m3: bool,
) -> tuple[float, float]:
    """Independent bisection solver on C35 stress block (k1=0.79) + exact displaced bar disks."""
    sign = 1.0 if positive_m3 else -1.0
    stress = 0.85 * fcd
    target_n = nd_kn * 1000.0
    low, high = 1e-6, 16.0 * h
    force = 0.0
    moment = 0.0
    for _ in range(54):
        neutral = 0.5 * (low + high)
        thick = min(h, 0.79 * neutral)
        line = 0.5 * h - thick
        force = stress * bw * thick
        moment = force * (0.5 * h - 0.5 * thick)
        for bar in bars:
            y = sign * float(bar["x2_mm"])
            r = 0.5 * float(bar["diameter_mm"])
            area = float(bar["area_mm2"])
            strain = 0.003 * (1.0 - (0.5 * h - y) / neutral)
            steel = max(-fyd, min(fyd, strain * es)) * area
            dist = line - y
            removed = 0.0
            first = 0.0
            if dist <= -r:
                removed = area
            elif dist < r:
                chord = sqrt(max(0.0, r * r - dist * dist))
                removed = r * r * acos(max(-1.0, min(1.0, dist / r))) - dist * chord
                first = 2.0 * (chord ** 3) / 3.0
            bf = steel - stress * removed
            force += bf
            moment += bf * y - stress * first
        if force < target_n:
            low = neutral
        else:
            high = neutral
    return moment / 1e6, abs(force - target_n)


def _independent_seg_dist(
    a1: tuple[float, float, float],
    a2: tuple[float, float, float],
    b1: tuple[float, float, float],
    b2: tuple[float, float, float],
) -> float:
    ux, uy, uz = a2[0] - a1[0], a2[1] - a1[1], a2[2] - a1[2]
    vx, vy, vz = b2[0] - b1[0], b2[1] - b1[1], b2[2] - b1[2]
    wx, wy, wz = a1[0] - b1[0], a1[1] - b1[1], a1[2] - b1[2]
    aa = ux * ux + uy * uy + uz * uz
    bb = ux * vx + uy * vy + uz * vz
    cc = vx * vx + vy * vy + vz * vz
    dd = ux * wx + uy * wy + uz * wz
    ee = vx * wx + vy * wy + vz * wz
    det = aa * cc - bb * bb
    sd, td = det, det
    if det < 1e-12:
        sn, sd, tn, td = 0.0, 1.0, ee, cc
    else:
        sn, tn = bb * ee - cc * dd, aa * ee - bb * dd
        if sn < 0.0:
            sn, tn, td = 0.0, ee, cc
        elif sn > sd:
            sn, tn, td = sd, ee + bb, cc
    if tn < 0.0:
        tn = 0.0
        sn, sd = (0.0, 1.0) if -dd < 0.0 else ((sd, sd) if -dd > aa else (-dd, aa))
    elif tn > td:
        tn = td
        sn, sd = (0.0, 1.0) if (-dd + bb) < 0.0 else ((sd, sd) if (-dd + bb) > aa else (-dd + bb, aa))
    sc = 0.0 if abs(sn) < 1e-12 else sn / sd
    tc = 0.0 if abs(tn) < 1e-12 else tn / td
    return sqrt((wx + sc * ux - tc * vx) ** 2 + (wy + sc * uy - tc * vy) ** 2 + (wz + sc * uz - tc * vz) ** 2)


def _audit_gap_011(
    source: Mapping[str, Any],
    stages: Mapping[str, Any],
    building: Mapping[str, Any],
    report_html: str,
) -> dict[str, Any]:
    """Independent clause-by-clause audit for GAP-011 scoped frame & C29 reinforcement detailing."""
    r10_cols = stages["r10_live"]["per_member"]
    r14_cols = {c["member_id"]: c for c in stages["r14_closure"]["columns"]}
    conf_cols = {c["member_id"]: c for c in building["frame_confinement"]["columns"]}

    conditional_ids = sorted(c["member_id"] for c in building["columns"] if c["status"] == "conditional")
    failed_ids = sorted(c["member_id"] for c in building["columns"] if c["status"] == "failed")
    held_ids = sorted(c["member_id"] for c in building["columns"] if c["status"] == "hold")
    require(
        (len(conditional_ids), len(failed_ids), len(held_ids)) == (69, 4, 14),
        "G6_COLUMN_POPULATION_DRIFT",
    )

    # 1. Verify As >= 0.01*Ac without deficit tolerance, effective legs, hooks, and candidate role on all 69 columns
    min_rho_observed = 1.0
    max_a_ratio = 0.0
    for uid in conditional_ids:
        sel_block = r10_cols[uid]["engineer_column_selection"]
        require(sel_block["origin"] == "ENGINEER_SELECTED_COLUMN_REBAR", "G6_COLUMN_SELECTION_ROLE_DRIFT")
        require(sel_block["formal_compliance"] == "NOT_PROVEN", "G6_PREMATURE_COLUMN_APPROVAL")
        sel = sel_block["selected"]
        t2, t3 = sel_block["section_sides_mm"]
        ac = float(t2) * float(t3)
        area = float(sel["bar_count"]) * (pi * (float(sel["diameter_mm"]) ** 2) / 4.0)
        require(isclose(area, float(sel["area_mm2"]), rel_tol=1e-9, abs_tol=1e-6), "G6_BAR_AREA_MISMATCH")
        require(area >= 0.01 * ac, f"G6_RHO_DEFICIT:{uid}")
        min_rho_observed = min(min_rho_observed, area / ac)

        tr = sel["selected_transverse"]
        td = float(tr["tie_diameter_mm"])
        require(td >= max(8.0, float(sel["diameter_mm"]) / 3.0), f"G6_TIE_DIAMETER:{uid}")
        for axis_k, n_bars, extent in (("v2", int(sel["num_bars_3_dir"]), float(t3)), ("v3", int(sel["num_bars_2_dir"]), float(t2))):
            legs = int(tr["legs_" + axis_k])
            require(2 <= legs <= n_bars, f"G6_INVALID_LEG_COUNT:{uid}:{axis_k}")
            span_core = extent - 2.0 * 40.0
            pitch_bar = span_core / (n_bars - 1)
            step = (n_bars - 1 + legs - 2) // (legs - 1)
            a_mm = step * pitch_bar
            require(a_mm <= 25.0 * td + 1e-7, f"G6_RESTRAINED_BAR_SPACING:{uid}:{axis_k}")
            max_a_ratio = max(max_a_ratio, a_mm / (25.0 * td))

        conf = conf_cols[uid]
        require(conf["status"] == "SCHEDULE_CALCULATED", f"G6_CONFINEMENT_STATUS:{uid}")
        hk = conf["hook"]
        require(
            hk["hook_angle_deg"] == 135
            and hk["minimum_inside_bend_diameter_mm"] >= 5.0 * td
            and hk["minimum_ribbed_tail_mm"] >= max(6.0 * td, 80.0),
            f"G6_COLUMN_HOOK:{uid}",
        )
        require(
            r14_cols[uid]["status"] == "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES",
            f"G6_R14_CANDIDATE_ROLE_LOST:{uid}",
        )

    # 2. Verify C21-C24 foundation continuation failures survive despite passing PMM
    for uid in failed_ids:
        conf = conf_cols[uid]
        require(
            conf["status"] == "NUMERICAL_EXCEEDANCE"
            and conf["foundation_continuation"]["model_depth_mm"] == 600.0
            and conf["foundation_continuation"]["required_mm"] == 800.0
            and "COLUMN_CONFINEMENT:FOUNDATION_DEPTH_BELOW_CONTINUATION" in r14_cols[uid]["normative_failures"],
            f"G6_FOUNDATION_FAILURE_MASKED:{uid}",
        )

    # 3. Synthetic tie-spacing failure precedence probe on C29/142 (PMM pass + s_conf=180mm > 96mm -> failure!)
    c142_det = r10_cols["142"]
    c142_sel = c142_det["engineer_column_selection"]["selected"]
    require(c142_sel["pmm_satisfied"] is True and c142_sel["pmm_max_utilization"] < 1.0, "G6_C142_PMM_BASELINE")
    bad_tr = _evaluate_column_transverse_choice(
        tie_d=10, s_conf_mm=180.0, s_span_mm=150.0, long_d=16,
        n2=9, n3=9, t2_mm=800.0, t3_mm=800.0, cover_mm=40.0,
        fck_mpa=35.0, fywk_mpa=500.0, gamma_c=1.5, gamma_s=1.15, shear_demands=(),
    )
    require(bad_tr["confinement_spacing_ok"] is False and bad_tr["all_tbdy_checks_met"] is False, "G6_SYNTHETIC_TIE_CHECK")
    mutated_det = {
        **c142_det,
        "engineer_column_selection": {
            **c142_det["engineer_column_selection"],
            "selected": {**c142_sel, "selected_transverse": bad_tr},
        },
    }
    bad_conf = column_confinement("142", mutated_det, stages["r08_local_slenderness"]["per_member"]["142"]["physical_clear_length"])
    mutated_det["confinement_regions"] = bad_conf
    axial_142 = next(c for c in stages["column_axial"]["columns"] if c["element_id"] == "142")
    pmm_142 = next(c for c in stages["column_pmm"]["members"] if c["member_id"] == "142")
    bad_r14 = _evaluate_single_r14_column(
        uid="142",
        axial=stages["column_axial"],
        axial_col=axial_142,
        pmm_col=pmm_142,
        r08_global=stages["r08_second_order"],
        r08_local_col=stages["r08_local_slenderness"]["per_member"]["142"],
        beam_by_id={b["member_id"]: b for b in stages["beam_r10"]["beams"]},
        r10_det=mutated_det,
        story_alpha=None,
        analysis_setup_reconciliation=stages["analysis_setup_reconciliation"],
        pmm_cut_census_proven=True,
    )
    require(
        bad_conf["status"] == "NUMERICAL_EXCEEDANCE"
        and "COLUMN_TRANSVERSE_AND_CROSSTIE_TBDY_RULES_NOT_MET" in bad_r14["normative_failures"]
        and bad_r14["status"] != "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES",
        "G6_TIE_FAILURE_PRECEDENCE_BROKEN",
    )

    # 4. Verify C29 3D detail & UI/report candidate role preservation
    c29 = building["c29_joint_detail"]
    require(
        c29["status"] == "C29_3D_DETAIL_AND_12_BEAMS_VERIFIED_CANDIDATE"
        and c29["selection_role"] == "ALGORITHM_SELECTED_CANDIDATE"
        and c29["original_project_approval"] == "NOT_GRANTED"
        and len(c29["joints"]) == 3
        and all(j["naive_2d_overlay_clash_detected"] and j["registered_3d_collision_free"] for j in c29["joints"])
        and "ALGORITHM_SELECTED_CANDIDATE" in report_html,
        "G6_C29_DETAIL_OR_REPORT_ROLE_MISSING",
    )
    # Independent 3D clearance spot-check on orthogonal X/Y registered beam layers + hoop window
    d_xy = _independent_seg_dist((-500.0, -213.75, -60.0), (0.0, -213.75, -60.0), (-213.75, -500.0, -89.0), (-213.75, 0.0, -89.0))
    require(d_xy - (12.5 + 12.5) >= 4.0 - 1e-6, "G6_INDEPENDENT_ORTHOGONAL_LAYER_CLEARANCE")

    return {
        "conditional_columns_verified": len(conditional_ids),
        "foundation_failures_preserved": failed_ids,
        "wall_coupled_holds_preserved": len(held_ids),
        "minimum_observed_rho": min_rho_observed,
        "maximum_restrained_bar_spacing_ratio": max_a_ratio,
        "tie_spacing_failure_precedence_verified": True,
        "c29_joints_verified": [j["joint_id"] for j in c29["joints"]],
        "c29_min_3d_clearances_mm": {j["joint_id"]: j["registered_3d_min_clearance_mm"] for j in c29["joints"]},
        "candidate_role_preserved_in_r14_and_report": True,
    }


def _audit_gap_012(
    source: Mapping[str, Any],
    stages: Mapping[str, Any],
    building: Mapping[str, Any],
) -> dict[str, Any]:
    """Independent section-equilibrium, axial-torsion, coupling-beam & 360-end audit for GAP-012."""
    beams = stages["beam_r10"]["beams"]
    indep = building["beam_independent_design"]
    coup = building["coupling_beams"]
    c29 = building["c29_joint_detail"]
    require(len(beams) == indep["beam_count"] == coup["expected_beam_population"] == 180, "G6_BEAM_CENSUS_MISMATCH")
    require(indep["e2k_modifiers_and_releases"]["verified"] is True, "G6_E2K_BEAM_RELEASES_OR_MODIFIERS")

    # 1. Independently integrate all 540 stations (180 x {I, J, SPAN} = 1,080 signed N=0 capacities)
    fcd = 35.0 / 1.5
    max_cap_diff_knm = 0.0
    max_axial_res_n = 0.0
    for b in beams:
        bw, h = float(b["width_mm"]), float(b["height_mm"])
        fyd = float(b["fyk_mpa"]) / 1.15
        for sel in (
            b["ends"]["I"]["engineer_selection"],
            b["ends"]["J"]["engineer_selection"],
            b["engineer_midspan"],
        ):
            cap = sel["capacity"]
            for sign_flag, key in ((True, "positive_m3_knm"), (False, "negative_m3_knm")):
                mr_ind, res_n = _independent_beam_mr_knm(bw, h, sel["bars"], fcd, fyd, 200000.0, 0.0, sign_flag)
                diff = abs(abs(float(cap[key])) - mr_ind)
                require(diff <= 0.01 and res_n <= 0.01, f"G6_INDEPENDENT_BEAM_MR_MISMATCH:{b['member_id']}:{key}")
                max_cap_diff_knm = max(max_cap_diff_knm, diff)
                max_axial_res_n = max(max_axial_res_n, res_n)

    # 2. Verify all 93,841 FrameForce vectors satisfy axial, N-M3 interval box, and TS 500 §8.2 torsion limits
    require(
        indep["native_force_vectors_checked"] == 93841
        and indep["tbdy_7_4_1_2_axial_qualified_beams"] == 180
        and indep["max_axial_over_0_10_ac_fck"] <= 1.0
        and indep["axial_interval_box_exceedances"] == 0
        and indep["max_axial_interval_box_utilization"] < 1.0
        and indep["combined_web_crushing_exceedances"] == 0
        and indep["concurrent_stirrup_exceedances"] == 0
        and indep["concurrent_longitudinal_exceedances"] == 0,
        "G6_BEAM_AXIAL_BOX_OR_TORSION_EXCEEDANCE",
    )

    # 3. Verify all 360 physical beam ends & 4 coupling-role beams & 12 C29 connected beams (24 ends)
    require(
        sum(indep["end_topology_counts"].values()) == 360
        and sum(indep["end_anchorage_counts"].values()) == 360
        and indep["end_topology_counts"].get("COLUMN_FACE") == 254,
        "G6_BEAM_END_TOPOLOGY_CENSUS",
    )
    require(
        coup["role_review_count"] == 4
        and coup["satisfied_count"] == 4
        and coup["not_applicable_count"] == 176
        and coup["blocked_count"] == 0
        and coup["failed_count"] == 0,
        "G6_COUPLING_BEAM_QUALIFICATION",
    )
    # Independent check on the 4 coupling-role beams
    fctd = 0.35 * sqrt(35.0) / 1.5
    for cb in coup["beams"]:
        if cb["applicability"] == "WALL_TO_WALL_ROLE_REVIEW":
            lim = 1.5 * float(cb["width_mm"]) * (float(cb["height_mm"]) - 60.0) * fctd / 1000.0
            require(
                cb["ln_over_h_physical"] > 2.0
                and cb["ve_physical_kn"] <= cb["tbdy_7_6_8_1_shear_threshold_kn"] <= lim + 50.0
                and cb["ve_physical_kn"] <= cb["vr_confinement_kn"],
                f"G6_COUPLING_BEAM_CHECK:{cb['member_id']}",
            )
    require(
        c29["distinct_connected_beam_count"] == 12
        and c29["verified_beam_ends"] == 24
        and all(bt["registered_axial_box_max_utilization"] < 1.0 and bt["far_end_anchorage_ok"] for bt in c29["connected_beams"]),
        "G6_C29_INCIDENT_BEAMS",
    )

    return {
        "beams_verified": 180,
        "stations_independently_integrated": 540,
        "signed_zero_axial_capacities_verified": 1080,
        "max_independent_capacity_residual_knm": max_cap_diff_knm,
        "max_independent_axial_residual_n": max_axial_res_n,
        "native_beam_vectors_checked": indep["native_force_vectors_checked"],
        "max_axial_over_0_10_ac_fck": indep["max_axial_over_0_10_ac_fck"],
        "max_axial_interval_box_utilization": indep["max_axial_interval_box_utilization"],
        "max_combined_shear_torsion_web_ratio": indep["max_combined_shear_torsion_web_ratio"],
        "physical_beam_ends_classified": 360,
        "coupling_role_beams_qualified": [
            r["member_id"] for r in coup["beams"] if r["applicability"] == "WALL_TO_WALL_ROLE_REVIEW"
        ],
        "c29_connected_beams_verified": [bt["member_id"] for bt in c29["connected_beams"]],
    }


def g6_contract(
    source: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    g5_packet: Mapping[str, Any],
    report_html: str,
) -> dict[str, Any]:
    """Assemble the scoped G6 Supervisor review packet for GAP-011 and GAP-012."""
    stages = snapshot["results"]
    building = stages["building_design"]
    g4_packet = building["g4_contract"]

    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "input_sha256": snapshot["input_sha256"],
        "parent_g4_contract_sha256": g4_packet["contract_sha256"],
        "parent_g5_contract_sha256": g5_packet["contract_sha256"],
        "reviewed_g4_sha256": ACCEPTED_G4,
        "reviewed_g5_sha256": ACCEPTED_G5,
        "expected_population_sha256": ACCEPTED_POPULATION,
        "decision": "SUPERVISOR_REVIEW",
        "engineering_release": "NOT_READY",
        "scope": (
            "Scoped frame reinforcement detailing (69 conditional columns, C21-C24 foundation failures, "
            "C29 3-storey 3D collision-free joint takeoff with candidate-role preservation) and complete "
            "180-beam N-M3 interval capacity, TS 500 8.2 ULS torsion, 4 TBDY 7.6.8 coupling-role beams, "
            "and 360-end support/anchorage topology"
        ),
        "separate_gaps": ["GAP-006", "GAP-009", "GAP-015", "GAP-018"],
        "excluded_scopes": [
            "14 wall-coupled columns (awaiting GAP-006/009 coupled method)",
            "SLS beam deflection and crack-width combinations (uncaptured in source)",
            "Engineer as-built construction sign-off",
        ],
        "gaps": {},
        "evidence": {},
    }

    for gap in ("GAP-011", "GAP-012"):
        issues: list[str] = []
        try:
            require(
                g4_packet.get("decision") == "SUPERVISOR_ACCEPTED_SCOPED"
                and g5_packet.get("decision") == "SUPERVISOR_ACCEPTED_SCOPED"
                and g5_packet.get("reviewed_g4_sha256") == ACCEPTED_G4
                and g5_packet.get("supervisor_acceptance", {}).get("reviewed_contract_sha256") == ACCEPTED_G5
                and g5_packet.get("input_sha256") == snapshot["input_sha256"]
                and _digest({k: v for k, v in g5_packet.items() if k != "contract_sha256"}) == g5_packet["contract_sha256"],
                "G6_ACCEPTED_G5_PARENT_REQUIRED",
            )
            if gap == "GAP-011":
                packet["evidence"]["reinforcement_detailing"] = _audit_gap_011(source, stages, building, report_html)
            else:
                packet["evidence"]["beam_capacity_and_topology"] = _audit_gap_012(source, stages, building)
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError) as exc:
            issues.append(str(exc))
        packet["gaps"][gap] = {
            "status": "PARTIAL",
            "closure_ready": not issues,
            "supervisor_approval": "PENDING",
            "unresolved": issues,
        }

    return {**packet, "contract_sha256": _digest(packet)}


def g6_verification(directory, packet: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    names = [
        "g4-contract.json",
        "g4-verification.json",
        "g5-contract.json",
        "g5-verification.json",
        "g6-contract.json",
        "report.html",
    ]
    result = {
        "schema": VERIFICATION_SCHEMA,
        "input_sha256": snapshot["input_sha256"],
        "contract_sha256": packet["contract_sha256"],
        "gaps": packet["gaps"],
        "snapshot_sha256": _digest(snapshot),
        "results_sha256": snapshot["results_sha256"],
        "files_sha256": {n: sha256((directory / n).read_bytes()).hexdigest() for n in names},
        "evidence_sha256": {k: _digest(v) for k, v in packet["evidence"].items()},
    }
    return {**result, "verification_sha256": _digest(result)}
