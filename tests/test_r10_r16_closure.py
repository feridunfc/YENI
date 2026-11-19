"""R10-R16 end-to-end closure and independent norm oracle tests (R16).

Covers:
- R10/R12: Live beam static gravity shear Vdy capture + full Ve = Vdy + (Mpi+Mpj)/ln,
           and engineer-selected column Ve / Vr (CHK-126).
- R11:     TBDY 7.3.6.1 story alpha_i = sum(Vis)/sum(Vik) & 7.3.6.2 (1/alpha_i) feedback.
- R13:     TBDY 7.5.2.1 joint shear Vj = 1.25*fyk*(As1+As2) - Vkol (V2 vs V3 no double counting)
           & TBDY 7.5.2.3 joint transverse reinforcement.
- R14:     End-to-end single-column closure (Axial + Approved Combos + 2nd-Order P-Delta + P-delta
           magnified selected-cage PMM + Ve/Vr + SCWB/alpha_i + Vj/7.5.2.3).
- R15:     87-column population scaling via `pmm_member="ALL"` (Engine + Web HTTP + HTML report).
- R16:     Independent hand/oracle verification without importing primary solver equations.
"""
from __future__ import annotations

import copy
import json
import math
import unittest

from tbdy_next.column_engine.source_bank import FIELDS
from tbdy_next.engineering.beam_r10_live import project_beam_r10_live
from tbdy_next.engineering.column_axial import PREFERENCES, evaluate_column_axial
from tbdy_next.engineering.column_pmm import evaluate_column_pmm
from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
from tbdy_next.engineering.column_r10_live import (
    BEAM_DESIGN_SUMMARY,
    BEAM_REINFORCING,
    END_OFFSETS,
    RELEASES,
    _evaluate_story_alpha_summary,
    project_column_r10_live,
)
from tbdy_next.engineering.column_r14_closure import project_column_r14_and_r15_closure
from tbdy_next.quick_checks import evaluate_geometry_capture
from test_beam_r10_live import _attach_r10_beam_sources, _beam_table
from test_column_axial_live import SPECTRAL, STATIC
from test_r03_analysis_setup import capture_table
from test_r10_live import R10WebAndReportIntegration, _add_field, _base_live_payload, _pmm_sec_source, _rowset


def _make_87_column_live_fixtures():
    """Build a valid 3-story x 29-column (87 rectangular columns) LIVE_ETABS fixture."""
    payload, _, extra, axial_base, _ = _base_live_payload(enclosed_j=False)
    col_rows = []
    geom_col_items = []
    axial_cols = []
    beam_rows = []
    fa_rows = []
    pts = []
    rowsets = {}
    stories = [("S1", 0.0, 3.0), ("S2", 3.0, 6.0), ("S3", 6.0, 9.0)]
    seen_pts = set()

    def add_pt(pid: str, x: float, y: float, z: float) -> None:
        if pid not in seen_pts:
            seen_pts.add(pid)
            pts.append({"UniqueName": pid, "X": f"{x}", "Y": f"{y}", "Z": f"{z}"})

    c_idx = 0
    for s_idx, (sname, z0, z1) in enumerate(stories):
        for bay in range(29):
            c_idx += 1
            cid = f"C{c_idx:03d}"
            pi = f"P_{s_idx}_{bay}"
            pj = f"P_{s_idx + 1}_{bay}"
            x = float(bay * 5.0)
            add_pt(pi, x, 0.0, z0)
            add_pt(pj, x, 0.0, z1)
            col_rows.append({
                "UniqueName": cid, "ColumnBay": f"CL{bay+1}", "Story": sname,
                "UniquePtI": pi, "UniquePtJ": pj, "Length": "3.0",
            })
            fa_rows.append({"UniqueName": cid, "Label": cid, "Story": sname, "AnalysisSect": "C60", "AxisAngle": "0"})
            geom_col_items.append({
                "element_id": cid, "label": cid, "story": sname,
                "section": "C60", "analysis_section": "C60",
                "section_design_difference": False,
                "material_classification": "RESOLVED_CONCRETE_USAGE",
                "material_name": "C35/45", "width_mm": 600.0, "depth_mm": 600.0,
                "t2_mm": 600.0, "t3_mm": 600.0, "frame_length_m": 3.0,
                "i_joint_id": pi, "j_joint_id": pj, "status": "WITHIN_LIMIT",
            })
            axial_cols.append({
                "element_id": cid, "story": sname, "section": "C60", "material_name": "C35/45", "status": "WITHIN_LIMIT",
                "fck_mpa": 35.0, "fcd_mpa": 35.0 / 1.5, "n_max_kn": 1400.0,
                "ts500_limit_kn": 0.90 * 360_000.0 * (35.0 / 1.5) / 1000.0,
                "tbdy_seismic_reference_limit_kn": 0.40 * 360_000.0 * 35.0 / 1000.0,
                "combination_checks": [
                    {"combination": STATIC, "status": "WITHIN_LIMIT", "nd_kn": 1400.0},
                    {"combination": "Duct_SeisX", "status": "WITHIN_LIMIT", "nd_kn": 1100.0},
                    {"combination": "Duct_SeisY", "status": "WITHIN_LIMIT", "nd_kn": 1100.0},
                ],
            })
            rowsets[cid] = _rowset([
                (cid, 0.0, f"{cid}-1", 0.0, STATIC, "Single Value", 0.0, -1400.0, 35.0, 12.0, 0.0, -30.0, -80.0),
                (cid, 3.0, f"{cid}-1", 3.0, STATIC, "Single Value", 0.0, -1380.0, 35.0, 12.0, 0.0, 35.0, 90.0),
                (cid, 0.0, f"{cid}-1", 0.0, "Duct_SeisX", "Single Value", 0.0, -1100.0, 95.0, 18.0, 0.0, -45.0, -180.0),
                (cid, 3.0, f"{cid}-1", 3.0, "Duct_SeisX", "Single Value", 0.0, -1080.0, 95.0, 18.0, 0.0, 50.0, 195.0),
                (cid, 0.0, f"{cid}-1", 0.0, "Duct_SeisY", "Single Value", 0.0, -1100.0, 20.0, 88.0, 0.0, -150.0, -40.0),
                (cid, 3.0, f"{cid}-1", 3.0, "Duct_SeisY", "Single Value", 0.0, -1080.0, 20.0, 88.0, 0.0, 160.0, 42.0),
            ])
        for bay in range(28):
            bid = f"B_{sname}_{bay+1:02d}"
            pi = f"P_{s_idx + 1}_{bay}"
            pj = f"P_{s_idx + 1}_{bay + 1}"
            beam_rows.append({"UniqueName": bid, "BeamBay": bid, "Story": sname, "UniquePtI": pi, "UniquePtJ": pj, "Length": "5.0"})
            fa_rows.append({"UniqueName": bid, "Label": bid, "Story": sname, "AnalysisSect": "B30", "AxisAngle": "0"})

    payload["geometry_capture"]["present_units"] = 6
    payload["geometry_capture"]["present_units_after"] = 6
    payload["geometry_capture"]["unit_state_unchanged"] = True
    payload["geometry_capture"]["tables"] = {
        "FRAME_ASSIGNMENTS": {"fields": ["UniqueName", "Label", "Story", "AnalysisSect", "AxisAngle"], "rows": fa_rows},
        "COLUMN_CONNECTIVITY": {
            "fields": ["UniqueName", "ColumnBay", "Story", "UniquePtI", "UniquePtJ", "Length"],
            "rows": col_rows,
            "field_metadata": {"units_by_field": {"Length": "m"}},
        },
        "BEAM_CONNECTIVITY": {
            "fields": ["UniqueName", "BeamBay", "Story", "UniquePtI", "UniquePtJ", "Length"],
            "rows": beam_rows,
            "field_metadata": {"units_by_field": {"Length": "m"}},
        },
        "RECTANGULAR_SECTIONS": {
            "fields": ["Name", "Material", "t2", "t3"],
            "rows": [
                {"Name": "C60", "Material": "C35/45", "t2": "0.60", "t3": "0.60"},
                {"Name": "B30", "Material": "C35/45", "t2": "0.35", "t3": "0.60"},
            ],
        },
    }
    payload["vs05_delta_source"]["table_reads"]["Point Object Connectivity"] = {
        "fields": ["UniqueName", "X", "Y", "Z"], "rows": pts,
    }
    sec_src = _pmm_sec_source(name="C60", designed="No", bars2="4", bars3="4", spacing="0.10")
    reinf_b = _beam_table(
        BEAM_REINFORCING,
        ["Name", "RebarMatL", "RebarMatC", "CoverTop", "CoverBot", "TopLeftArea", "TopRightArea", "BotLeftArea", "BotRightArea"],
        [("B30", "B420C", "B420C", "0.05", "0.05", "0.0008", "0.0008", "0.0006", "0.0006")],
        {"CoverTop": "m", "CoverBot": "m", "TopLeftArea": "m2", "TopRightArea": "m2", "BotLeftArea": "m2", "BotRightArea": "m2"},
    )
    off_rows = [(c["UniqueName"], "0.0", "0.30") for c in col_rows] + [(b["UniqueName"], "0.30", "0.30") for b in beam_rows]
    offsets = _beam_table(END_OFFSETS, ["UniqueName", "LengthI", "LengthJ"], off_rows, {"LengthI": "m", "LengthJ": "m"})
    releases = _beam_table(RELEASES, ["UniqueName", "M2I", "M3I", "M2J", "M3J"], [(b["UniqueName"], "No", "No", "No", "No") for b in beam_rows])
    ds_rows = []
    beam_rowsets = {}
    for b in beam_rows:
        bid = b["UniqueName"]
        sname = b["Story"]
        ds_rows.extend([
            (sname, bid, bid, "B30", "0.30", "No Message", STATIC, "450", "900", STATIC, "450", "650", STATIC, "0.0", "900", "650", "No Message", "No Message"),
            (sname, bid, bid, "B30", "2.50", "No Message", STATIC, "450", "500", STATIC, "450", "750", STATIC, "0.0", "500", "750", "No Message", "No Message"),
            (sname, bid, bid, "B30", "4.70", "No Message", STATIC, "450", "900", STATIC, "450", "650", STATIC, "0.0", "900", "650", "No Message", "No Message"),
        ])
        beam_rowsets[bid] = _rowset([
            (bid, 0.30, f"{bid}-1", 0.30, STATIC, "Single Value", 0.0, 0.0, 92.0, 0.0, 0.0, 0.0, -70.0),
            (bid, 4.70, f"{bid}-1", 4.70, STATIC, "Single Value", 0.0, 0.0, -88.0, 0.0, 0.0, 0.0, -68.0),
        ])
    design_sum = _beam_table(
        BEAM_DESIGN_SUMMARY,
        ["Story", "Label", "UniqueName", "DesignSect", "Station", "Status",
         "AsTopCombo", "AsMinTop", "AsTop", "AsBotCombo", "AsMinBot", "AsBot",
         "TLngCombo", "TLngRebar", "totTopRebar", "totBotRebar", "WarnMsg", "ErrMsg"],
        ds_rows,
        {"Station": "m", "AsTop": "mm2", "AsBot": "mm2", "totTopRebar": "mm2", "totBotRebar": "mm2", "AsMinTop": "mm2", "AsMinBot": "mm2", "TLngRebar": "mm2"},
    )
    payload["column_axial"] = {
        "request": {
            "check": "column-pmm", "member": "ALL", "pmm_member": "ALL",
            "base_run_id": "RUN-87TEST", "base_input_sha256": "sha-87test",
            "combination_source": "ASSIGNED_DESIGN",
            "design_assignment": {"groups": {"gravity": [STATIC], "ductile": ["Duct_SeisX", "Duct_SeisY"]}},
        },
        "force_source": {"units_code": 6, "combinations": [STATIC, "Duct_SeisX", "Duct_SeisY"], "rowsets": rowsets},
        "pmm_section_source": sec_src,
        "r10_source": {
            "schema": "tbdy.next.r10-live-source.v1",
            "table_reads": {
                BEAM_REINFORCING: reinf_b,
                END_OFFSETS: offsets,
                RELEASES: releases,
                BEAM_DESIGN_SUMMARY: design_sum,
            },
            "table_errors": {},
            "beam_force_source": {"rowsets": beam_rowsets},
        },
        "design_preferences": capture_table(PREFERENCES, ["GammaC", "GammaS"], [("1.5", "1.15")]),
    }
    payload["beam_selection"] = {"enabled": True}
    payload["column_selection"] = {"enabled": True}

    geometry = {"checks": [{"check_id": "column_rect_min", "status": "EVALUATED", "items": geom_col_items}]}
    axial = {
        "status": "NUMERICAL_COMPLETE",
        "combination_plan": {
            "source": "ASSIGNED_DESIGN",
            "blockers": [],
            "design_assignment": {"groups": {"gravity": [STATIC], "ductile": ["Duct_SeisX", "Duct_SeisY"]}},
            "combinations": [
                {"name": STATIC, "force_semantics": "STATIC_SIGNED_VECTOR"},
                {"name": "Duct_SeisX", "force_semantics": "STATIC_SIGNED_VECTOR"},
                {"name": "Duct_SeisY", "force_semantics": "STATIC_SIGNED_VECTOR"},
            ],
        },
        "columns": axial_cols,
    }
    return payload, geometry, extra, axial


class R10ToR16OracleUnitTests(unittest.TestCase):
    def test_r13_joint_shear_vj_no_double_counting_and_7_5_2_3_oracle(self):
        payload, geometry, extra, axial, pmm = _base_live_payload(enclosed_j=True)
        tables = payload["geometry_capture"]["tables"]
        tables["BEAM_CONNECTIVITY"]["field_metadata"] = {"units_by_field": {"Length": "m"}}
        for r in tables["BEAM_CONNECTIVITY"]["rows"]:
            r["Length"] = "6.0" if r["UniqueName"] in ("511", "517") else "5.0"
        tables["COLUMN_CONNECTIVITY"]["field_metadata"] = {"units_by_field": {"Length": "m"}}
        for r in tables["COLUMN_CONNECTIVITY"]["rows"]:
            r["Length"] = "4.5"

        r10_src = payload["column_axial"].setdefault(
            "r10_source",
            {"schema": "tbdy.next.r10-live-source.v1", "table_reads": {}, "table_errors": {}},
        )["table_reads"]
        r10_src[BEAM_REINFORCING] = _beam_table(
            BEAM_REINFORCING,
            ["Name", "RebarMatL", "RebarMatC", "CoverTop", "CoverBot", "TopLeftArea", "TopRightArea", "BotLeftArea", "BotRightArea"],
            [("B60x70", "B420C", "B420C", "0.05", "0.05", "0.0", "0.0", "0.0", "0.0")],
            {"CoverTop": "m", "CoverBot": "m", "TopLeftArea": "m2", "TopRightArea": "m2", "BotLeftArea": "m2", "BotRightArea": "m2"},
        )
        r10_src[END_OFFSETS] = _beam_table(
            END_OFFSETS,
            ["UniqueName", "LengthI", "LengthJ"],
            [("127", "0.0", "0.35"), ("511", "0.4", "0.4"), ("517", "0.4", "0.4"), ("516", "0.4", "0.4"), ("518", "0.4", "0.4")],
            {"LengthI": "m", "LengthJ": "m"},
        )
        r10_src[RELEASES] = _beam_table(
            RELEASES,
            ["UniqueName", "M2I", "M3I", "M2J", "M3J"],
            [(b["UniqueName"], "No", "No", "No", "No") for b in tables["BEAM_CONNECTIVITY"]["rows"]],
        )
        ds_rows = []
        for b in tables["BEAM_CONNECTIVITY"]["rows"]:
            bid = b["UniqueName"]
            # Deliberately make X beams (511, 517) much heavier than Y beams (516, 518)
            atop, abot = ("1800", "1100") if bid in ("511", "517") else ("950", "600")
            for sta in ("0.40", "2.50", "5.60"):
                ds_rows.append((b["Story"], b["BeamBay"], bid, "B60x70", sta, "No Message", STATIC, "500", atop, STATIC, "500", abot, STATIC, "0.0", atop, abot, "No Message", "No Message"))
        r10_src[BEAM_DESIGN_SUMMARY] = _beam_table(
            BEAM_DESIGN_SUMMARY,
            ["Story", "Label", "UniqueName", "DesignSect", "Station", "Status",
             "AsTopCombo", "AsMinTop", "AsTop", "AsBotCombo", "AsMinBot", "AsBot",
             "TLngCombo", "TLngRebar", "totTopRebar", "totBotRebar", "WarnMsg", "ErrMsg"],
            ds_rows,
            {"Station": "m", "AsTop": "mm2", "AsBot": "mm2", "totTopRebar": "mm2", "totBotRebar": "mm2", "AsMinTop": "mm2", "AsMinBot": "mm2", "TLngRebar": "mm2"},
        )
        payload["beam_selection"] = {"enabled": True}
        payload["column_selection"] = {"enabled": True}

        beam_live = project_beam_r10_live(payload, geometry, axial, pmm, extra)
        r10 = project_column_r10_live(payload, geometry, axial, pmm, extra, beam_live=beam_live)

        end_j = next(e for e in r10["member_joint_ends"] if e["end"] == "J")
        ax_by_name = {a["axis"]: a for a in end_j["axes"]}
        v2_jve = ax_by_name["V2"]["joint_shear_ve"]
        v3_jve = ax_by_name["V3"]["joint_shear_ve"]
        self.assertEqual(v2_jve["v_kol_basis"], "ROOF_JOINT_NO_UPPER_COLUMN_VKOL_ZERO")
        self.assertEqual(v2_jve["code_ref"], "TBDY 7.5.2.1 / Eq. 7.11")
        self.assertAlmostEqual(v2_jve["v_kol_used_kn"], 0.0, places=6)

        # Independent oracle on orthogonal axes (axis_angle="90": local2 aligns with Global Y beams 516/518; local3 aligns with Global X beams 511/517)
        b_511_i = next(b for b in beam_live["beams"] if b["member_id"] == "511")["ends"]["I"]["engineer_selection"]
        b_517_i = next(b for b in beam_live["beams"] if b["member_id"] == "517")["ends"]["I"]["engineer_selection"]
        b_516_i = next(b for b in beam_live["beams"] if b["member_id"] == "516")["ends"]["I"]["engineer_selection"]
        b_518_i = next(b for b in beam_live["beams"] if b["member_id"] == "518")["ends"]["I"]["engineer_selection"]
        oracle_v3 = 1.25 * 420.0 * max(
            b_511_i["area_top_mm2"] + b_517_i["area_bottom_mm2"],
            b_511_i["area_bottom_mm2"] + b_517_i["area_top_mm2"],
        ) / 1000.0
        oracle_v2 = 1.25 * 420.0 * max(
            b_516_i["area_top_mm2"] + b_518_i["area_bottom_mm2"],
            b_516_i["area_bottom_mm2"] + b_518_i["area_top_mm2"],
        ) / 1000.0
        self.assertAlmostEqual(v3_jve["governing_ve_kn"], oracle_v3, places=5)
        self.assertAlmostEqual(v2_jve["governing_ve_kn"], oracle_v2, places=5)
        self.assertGreater(v3_jve["governing_ve_kn"] - v2_jve["governing_ve_kn"], 200.0)
        # Verify TBDY 7.5.2.3 enclosed parameters
        jt_v3 = ax_by_name["V3"]["joint_transverse_7_5_2_3"]
        self.assertEqual(jt_v3["fraction_of_lower_required_density"], 0.4)
        self.assertEqual(jt_v3["spacing_limit_mm"], 150)
        lower = next(c for c in axial["columns"] if c["element_id"] == jt_v3["lower_column_id"])
        # A missing demand takes the conservative amount without asserting an observed high axial load.
        lower.pop("n_max_kn", None)
        conservative = project_column_r10_live(payload, geometry, axial, pmm, extra, beam_live=beam_live)
        j_end = next(end for end in conservative["member_joint_ends"] if end["end"] == "J")
        tie = next(a for a in j_end["axes"] if a["axis"] == "V3")["joint_transverse_7_5_2_3"]
        self.assertEqual(tie["axial_branch"], "CONSERVATIVE_HIGH_AXIAL_REFERENCE_INPUTS_UNBOUND")
        self.assertGreaterEqual(tie["lower_required_ash_mm2"], jt_v3["lower_required_ash_mm2"])

    def test_r11_alpha_i_and_r15_87_columns_population_and_pdelta_oracle(self):
        payload, geometry, extra, axial = _make_87_column_live_fixtures()
        pmm = evaluate_column_pmm(payload, geometry, axial)
        beam_r10 = project_beam_r10_live(payload, geometry, axial, pmm, extra)
        r10 = project_column_r10_live(payload, geometry, axial, pmm, extra, beam_live=beam_r10)
        r08_local = project_column_r08_local_live(payload, geometry, axial, pmm, None, r10_live=r10)
        r14_r15 = project_column_r14_and_r15_closure(
            geometry=geometry, axial=axial, pmm=pmm,
            r08_second_order=None, r08_local=r08_local,
            beam_r10=beam_r10, r10_live=r10,
        )

        # R11 full-story denominator across 87 columns
        sa = r10["story_alpha"]
        self.assertEqual(sa["denominator_scope"], "FULL_STORY_COLUMN_DENOMINATOR")
        self.assertEqual(len(sa["stories"]), 6)  # 3 stories x 2 directions
        for st in sa["stories"]:
            self.assertEqual(st["story_column_count"], 29)
            self.assertEqual(st["evaluated_column_count"], 29)
            self.assertNotEqual(st["demand_feedback_action"], "PARTIAL_STORY_SCOPE_UNKNOWN_OTHER_COLUMNS")
            a_i = st["governing_alpha_i"]
            if a_i < 0.70:
                self.assertEqual(st["demand_feedback_action"], "STORY_SCWB_BELOW_0_70_SYSTEM_R_AND_DUCTILITY_REVIEW_REQUIRED")
            elif a_i < 1.0:
                self.assertEqual(st["demand_feedback_action"], "AMPLIFY_COLUMN_DEMANDS_BY_1_OVER_ALPHA")
                self.assertAlmostEqual(st["moment_magnification_factor_7_3_6_2"], 1.0 / a_i, places=6)
            else:
                self.assertEqual(st["demand_feedback_action"], "NONE")
                self.assertAlmostEqual(st["moment_magnification_factor_7_3_6_2"], 1.0, places=6)

        # R14 / R15 87-column denominator invariance
        self.assertEqual(pmm["scope"], "ALL_COLUMNS")
        self.assertEqual(pmm["expected_column_count"], 87)
        self.assertEqual(pmm["evaluated_column_count"], 87)
        self.assertEqual(r14_r15["scope"], "ALL_COLUMNS")
        self.assertEqual(r14_r15["expected_column_count"], 87)
        self.assertEqual(r14_r15["evaluated_column_count"], 87)
        self.assertEqual(r14_r15["missing_column_ids"], [])
        self.assertEqual(
            r14_r15["normative_fail_count"] + r14_r15["numerically_closed_count"] + r14_r15["partial_or_unbound_count"],
            87,
        )

        # Independent TS 500 Eq. 7.20 + Nk P-delta oracle for column C001
        c1_local = r08_local["per_member"]["C001"]
        mag = c1_local["magnified_selected_pmm"]
        self.assertIn("max_utilization", mag)
        stiff_m3 = c1_local["stiffness_and_euler"]["M3"]
        ec_oracle = 3250.0 * math.sqrt(35.0) + 14000.0
        ic_oracle = (600.0 ** 4) / 12.0
        is_oracle = stiff_m3["selected_is_mm4"]
        ei_oracle = 0.2 * ec_oracle * ic_oracle + 200000.0 * is_oracle
        nk_oracle = (math.pi ** 2) * ei_oracle / (3000.0 ** 2) / 1000.0
        self.assertAlmostEqual(stiff_m3["selected_nk_ts500_7_20_kn"], nk_oracle, places=3)

    def test_r11_alpha_i_demand_feedback_bands_oracle(self):
        axes_g = [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        cols = [{"frame_id": f"C{i}", "story": "S1", "axes_global": axes_g} for i in range(5)]
        rowsets = {
            f"C{i}": _rowset([(f"C{i}", 0.0, f"C{i}-1", 0.0, "SeisX", "Single Value", 0.0, -500.0, 100.0, 0.0, 0.0, 0.0, 50.0)])
            for i in range(5)
        }
        axial_min = {
            "combination_plan": {
                "source": "ASSIGNED_DESIGN",
                "design_assignment": {"groups": {"gravity": ["G"], "ductile": ["SeisX"]}},
                "combinations": [{"name": "SeisX", "force_semantics": "STATIC_SIGNED_VECTOR"}],
            }
        }

        def _make_joints(pass_count: int):
            return [
                {
                    "target_member_id": f"C{i}",
                    "direction": "X",
                    "engineer_selected_scwb": {"cases": [{"output_case": "SeisX", "reference_satisfied": i < pass_count}]},
                }
                for i in range(5)
            ]

        res_080 = _evaluate_story_alpha_summary(
            evaluated_uids=[f"C{i}" for i in range(5)],
            all_target_cols=cols,
            frames={},
            scwb_joints=_make_joints(4),
            force_rowsets=rowsets,
            axial=axial_min,
            use_engineer_selection=True,
        )
        st_x_80 = next(s for s in res_080["stories"] if s["direction"] == "X")
        self.assertAlmostEqual(st_x_80["governing_alpha_i"], 0.80, places=6)
        self.assertEqual(st_x_80["demand_feedback_action"], "AMPLIFY_COLUMN_DEMANDS_BY_1_OVER_ALPHA")
        self.assertAlmostEqual(st_x_80["moment_magnification_factor_7_3_6_2"], 1.0 / 0.80, places=6)

        res_060 = _evaluate_story_alpha_summary(
            evaluated_uids=[f"C{i}" for i in range(5)],
            all_target_cols=cols,
            frames={},
            scwb_joints=_make_joints(3),
            force_rowsets=rowsets,
            axial=axial_min,
            use_engineer_selection=True,
        )
        st_x_60 = next(s for s in res_060["stories"] if s["direction"] == "X")
        self.assertAlmostEqual(st_x_60["governing_alpha_i"], 0.60, places=6)
        self.assertEqual(st_x_60["demand_feedback_action"], "STORY_SCWB_BELOW_0_70_SYSTEM_R_AND_DUCTILITY_REVIEW_REQUIRED")
        self.assertIsNone(st_x_60["moment_magnification_factor_7_3_6_2"])

        res_100 = _evaluate_story_alpha_summary(
            evaluated_uids=[f"C{i}" for i in range(5)],
            all_target_cols=cols,
            frames={},
            scwb_joints=_make_joints(5),
            force_rowsets=rowsets,
            axial=axial_min,
            use_engineer_selection=True,
        )
        st_x_100 = next(s for s in res_100["stories"] if s["direction"] == "X")
        self.assertAlmostEqual(st_x_100["governing_alpha_i"], 1.0, places=6)
        self.assertEqual(st_x_100["demand_feedback_action"], "NONE")
        self.assertAlmostEqual(st_x_100["moment_magnification_factor_7_3_6_2"], 1.0, places=6)


class R10ToR15WebAndOracleIntegration(R10WebAndReportIntegration):
    def capture(self, case, *, column_axial_request=None):
        data = super().capture(case, column_axial_request=column_axial_request)
        if column_axial_request and column_axial_request.get("pmm_member"):
            _attach_r10_beam_sources(data)
            # Inject beam static gravity shear Vdy inside r10_source["beam_force_source"]
            data["column_axial"]["r10_source"]["beam_force_source"] = {
                "rowsets": {
                    "B1": _rowset([
                        ("B1", 0.20, "B1-1", 0.20, STATIC, "Single Value", 0.0, 0.0, 105.5, 0.0, 0.0, 0.0, -80.0),
                        ("B1", 4.80, "B1-1", 4.80, STATIC, "Single Value", 0.0, 0.0, -98.0, 0.0, 0.0, 0.0, -75.0),
                    ]),
                    "B2": _rowset([
                        ("B2", 0.20, "B2-1", 0.20, STATIC, "Single Value", 0.0, 0.0, 64.0, 0.0, 0.0, 0.0, -50.0),
                        ("B2", 4.80, "B2-1", 4.80, STATIC, "Single Value", 0.0, 0.0, -61.0, 0.0, 0.0, 0.0, -45.0),
                    ]),
                }
            }
        return data

    def test_r12_beam_vdy_and_selected_column_ve_and_all_columns_web_report(self):
        # 1) Single-column end-to-end R10-R14 over real Web HTTP + HTML report with Vdy + selected steel
        q1 = self.pmm_query()
        q1["beam_selection"] = json.dumps({"enabled": True})
        q1["column_selection"] = json.dumps({"enabled": True})
        ack1 = self.post(q1)
        self.assertEqual(ack1["r14_closure"]["scope"], "SINGLE_COLUMN")
        self.assertEqual(ack1["r14_closure"]["member_id"], "C1")

        exp1 = json.loads(self.get("/api/export-checks?run_id=" + ack1["run_id"]))
        b1 = next(b for b in exp1["beam_r10"]["beams"] if b["member_id"] == "B1")
        ve_b1 = b1["engineer_shear_ve"]
        self.assertEqual(ve_b1["status"], "SCENARIO_VE_CALCULATED_NOT_PROVEN")
        self.assertAlmostEqual(ve_b1["gravity_shear_vdy_kn"], 105.5, places=6)

        # Independent norm oracle for B1 Ve = Vdy + (Mpi + Mpj)/ln
        cap_i = b1["ends"]["I"]["engineer_selection"]["capacity"]
        cap_j = b1["ends"]["J"]["engineer_selection"]["capacity"]
        mpi_pos = 1.4 * abs(float(cap_i["positive_m3_knm"]))
        mpi_neg = 1.4 * abs(float(cap_i["negative_m3_knm"]))
        mpj_pos = 1.4 * abs(float(cap_j["positive_m3_knm"]))
        mpj_neg = 1.4 * abs(float(cap_j["negative_m3_knm"]))
        oracle_ve = 105.5 + max(mpi_pos + mpj_neg, mpi_neg + mpj_pos) / 4.6
        self.assertAlmostEqual(ve_b1["scenario_ve_kn"], oracle_ve, places=6)

        # Engineer-selected column Ve / Vr (R12)
        eng_col_ve = exp1["r10_live"]["column_transverse_and_shear"]["engineer_capacity_shear_ve"]
        self.assertEqual(eng_col_ve["selection_basis"], "ENGINEER_SELECTED_BEAM_AND_COLUMN")
        self.assertTrue(any(v is not None for v in (eng_col_ve["axes"]["V2"]["max_utilization_ts500"],)))

        # Single-column HTML includes R14 section
        html1 = self.get("/report/print?run_id=" + ack1["run_id"]).decode("utf-8")
        self.assertIn("R14 · Single-column end-to-end closure", html1)

        # 2) All-columns (member=ALL) Web HTTP POST + HTML report + story_alpha full denominator
        q_all = copy.deepcopy(q1)
        q_all["member"] = "ALL"
        ack_all = self.post(q_all)
        self.assertEqual(ack_all["column_pmm"]["member_id"], "ALL")
        self.assertEqual(ack_all["r14_closure"]["scope"], "ALL_COLUMNS")
        self.assertEqual(
            ack_all["r14_closure"]["expected_column_count"],
            ack_all["r14_closure"]["evaluated_column_count"],
        )
        exp_all = json.loads(self.get("/api/export-checks?run_id=" + ack_all["run_id"]))
        self.assertEqual(exp_all["r14_closure"]["scope"], "ALL_COLUMNS")
        html_all = self.get("/report/print?run_id=" + ack_all["run_id"]).decode("utf-8")
        self.assertIn("R14 / R15", html_all)
        self.assertIn("Column PMM (all columns population)", html_all)


class LiveEtabs23SchemaRegressionTests(unittest.TestCase):
    def test_etabs23_beam_reinforcing_columns_and_live_r14_schema_keys(self):
        from tbdy_next.engineering.beam_r10_live import (
            BEAM_REINFORCING,
            _beam_reinforcing_by_section,
        )
        from tbdy_next.engineering.column_r14_closure import project_column_r14_and_r15_closure

        r10_src = {
            "table_reads": {
                BEAM_REINFORCING: {
                    "table_key": BEAM_REINFORCING,
                    "fields": [
                        "Name", "MatPropLong", "MatPropConfine",
                        "TopCover", "BotCover",
                        "TopIEndArea", "TopJEndArea", "BotIEndArea", "BotJEndArea",
                    ],
                    "field_metadata": {
                        "units_by_field": {
                            "TopCover": "m",
                            "BotCover": "m",
                            "TopIEndArea": "m2",
                            "TopJEndArea": "m2",
                            "BotIEndArea": "m2",
                            "BotJEndArea": "m2",
                        }
                    },
                    "rows": [
                        {
                            "Name": "B60x70",
                            "MatPropLong": "B500C",
                            "MatPropConfine": "B500C",
                            "TopCover": "0.06",
                            "BotCover": "0.06",
                            "TopIEndArea": "0.0012",
                            "TopJEndArea": "0.0015",
                            "BotIEndArea": "0.0008",
                            "BotJEndArea": "0.0009",
                        }
                    ],
                },
            }
        }
        sec_map = _beam_reinforcing_by_section(r10_src)
        self.assertIn("B60x70", sec_map)
        b_sec = sec_map["B60x70"]
        self.assertEqual(b_sec["rebar_material_long"], "B500C")
        self.assertEqual(b_sec["rebar_material_conf"], "B500C")
        self.assertAlmostEqual(b_sec["cover_top_mm"], 60.0)
        self.assertAlmostEqual(b_sec["cover_bottom_mm"], 60.0)
        self.assertAlmostEqual(b_sec["override_areas_mm2"]["TopLeftArea"], 1200.0)
        self.assertAlmostEqual(b_sec["override_areas_mm2"]["TopRightArea"], 1500.0)
        self.assertAlmostEqual(b_sec["override_areas_mm2"]["BotLeftArea"], 800.0)
        self.assertAlmostEqual(b_sec["override_areas_mm2"]["BotRightArea"], 900.0)

        geometry = {
            "columns": [{"element_id": "127", "label": "C1", "story": "+0.00", "section_name": "Column_80x80"}]
        }
        axial = {
            "combination_plan": {
                "source": "ASSIGNED_DESIGN",
                "blockers": [],
                "design_assignment": {"groups": {"ductile": ["Duct_SeisX"], "gravity": ["Grav_Ult"]}},
            },
            "columns": [
                {
                    "element_id": "127",
                    "story": "+0.00",
                    "section": "Column_80x80",
                    "ts500_limit_kn": 13440.0,
                    "tbdy_seismic_reference_limit_kn": 8960.0,
                    "governing": {"nd_kn": 342.34, "combination": "Grav_Ult"},
                    "combination_checks": [{"combination": "Grav_Ult", "nd_kn": 342.34}],
                }
            ],
        }
        pmm = {"member_id": "127", "observed_exceedance_count": 0}
        r08_global = {"all_observed_below_numeric_limit": True}
        r08_local = {
            "member_id": "127",
            "max_reference_beta_sway_prevented": 1.0,
            "magnified_selected_pmm": {
                "status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN",
                "max_utilization": 0.25,
                "governing_combination": "Grav_Ult",
            },
        }
        beam_r10 = {
            "beams": [
                {
                    "member_id": "511",
                    "engineer_shear_ve": {"status": "BEAM_SHEAR_VE_CALCULATED_NOT_PROVEN", "gravity_shear_vdy_kn": 64.44},
                    "engineer_stirrups": {
                        "confinement": {
                            "spacing_ok": False,
                            "alerts": ["TBDY_7_4_4_4_SPACING_EXCEEDS_8_D_MIN:100mm>96mm"],
                            "utilization_conservative": 0.45,
                        },
                        "span": {"spacing_ok": True, "alerts": [], "utilization_conservative": 0.30},
                    },
                }
            ]
        }
        r10_live = {
            "member_id": "127",
            "story_alpha": {
                "stories": [
                    {
                        "story": "+0.00",
                        "direction": "X",
                        "governing_alpha_i": 0.98,
                        "denominator_status": "FULL_STORY_COLUMN_DENOMINATOR",
                        "demand_feedback_action": "PARTIAL_STORY_SCOPE_UNKNOWN_OTHER_COLUMNS",
                    }
                ]
            },
            "engineer_column_selection": {
                "status": "ENGINEER_COLUMN_SELECTED_NOT_PROVEN",
                "selected": {
                    "label": "32Φ16",
                    "selected_transverse": {"confinement_label": "Φ8/100", "all_tbdy_checks_met": True},
                },
            },
            "column_transverse_and_shear": {
                "engineer_capacity_shear_ve": {
                    "status": "SCENARIO_VE_CALCULATED_NOT_PROVEN",
                    "axes": {"V2": {"max_utilization_ts500": 0.25, "max_utilization_zero_concrete": 0.35}},
                }
            },
            "member_joint_ends": [
                {
                    "end": "J",
                    "status": "JOINT_GEOMETRIC_REFERENCES_CALCULATED",
                    "faces": {"right": {"frame_id": "511"}},
                    "axes": [
                        {
                            "axis": "V2",
                            "calculation": {"beam_ids": ["511"]},
                            "joint_shear_ve": {"utilization": 0.20, "within_geometric_limit": True},
                            "joint_transverse_7_5_2_3": {"all_references_met": True},
                        }
                    ],
                }
            ],
            "scwb_joints": [
                {
                    "beam_ids": ["511"],
                    "engineer_selected_scwb": {
                        "reference_satisfied": True,
                        "sampled_minimum_normalized_ratio": 2.50,
                    },
                }
            ],
        }
        r14 = project_column_r14_and_r15_closure(
            geometry=geometry,
            axial=axial,
            pmm=pmm,
            r08_second_order=r08_global,
            r08_local=r08_local,
            beam_r10=beam_r10,
            r10_live=r10_live,
        )
        self.assertIsNotNone(r14)
        self.assertEqual(r14["scope"], "SINGLE_COLUMN")
        self.assertNotIn("COLUMN_ENGINEER_CAGE_NOT_SELECTED_OR_BLOCKED", r14["open_gates"])
        self.assertAlmostEqual(r14["pillars"]["axial_caps"]["n_max_kn"], 342.34)
        self.assertNotIn("STORY_ALPHA_I_BELOW_0_70", r14["normative_failures"])
        self.assertIn("CONNECTED_BEAM_STIRRUP_OR_VE_FAIL:511", r14["normative_failures"])

        # True < 0.70 feedback action must still raise STORY_ALPHA_I_BELOW_0_70
        r10_live["story_alpha"]["stories"][0]["demand_feedback_action"] = (
            "STORY_SCWB_BELOW_0_70_SYSTEM_R_AND_DUCTILITY_REVIEW_REQUIRED"
        )
        r14_low = project_column_r14_and_r15_closure(
            geometry=geometry,
            axial=axial,
            pmm=pmm,
            r08_second_order=r08_global,
            r08_local=r08_local,
            beam_r10=beam_r10,
            r10_live=r10_live,
        )
        self.assertIn("STORY_ALPHA_I_BELOW_0_70", r14_low["normative_failures"])

    def test_r03_reconciliation_and_table_4_2_stiffness_gate(self):
        from tbdy_next.engineering.analysis_setup import project_analysis_setup_reconciliation
        from tbdy_next.engineering.column_r14_closure import project_column_r14_and_r15_closure

        setup = {
            "status": "BLOCKED",
            "blocker_codes": [
                "APPROVED_MODEL_PROFILE_MISSING",
                "APPROVED_LOAD_ROLES_AND_DESIGN_FAMILIES_MISSING",
                "ANALYSIS_GENERATION_NOT_PROVEN",
            ],
        }
        snapshot = {
            "column_axial": {
                "request": {
                    "combination_source": "ASSIGNED_DESIGN",
                    "design_assignment": {
                        "profile": "YENI_DESIGN_GROUPS_V1",
                        "scope": "upper",
                        "groups": {
                            "gravity": ["Grav_Ult"],
                            "ductile": ["Duct_SeisX"],
                        },
                    },
                }
            },
            "geometry_capture": {
                "tables": {
                    "COLUMN_CONNECTIVITY": {"rows": [{"UniqueName": "127"}]},
                    "BEAM_CONNECTIVITY": {"rows": [{"UniqueName": "511"}]},
                    "SECTION_ASSIGNMENTS": {
                        "rows": [
                            {"UniqueName": "127", "SectProp": "Column_80x80"},
                            {"UniqueName": "511", "SectProp": "B60x70"},
                        ]
                    },
                    "RECTANGULAR_SECTIONS": {
                        "rows": [
                            {"Name": "Column_80x80", "DesignType": "Column", "I2Mod": "0.7", "I3Mod": "0.7", "AMod": "1", "JMod": "1"},
                            {"Name": "B60x70", "DesignType": "Beam", "I2Mod": "0.35", "I3Mod": "0.35", "AMod": "1", "JMod": "1"},
                        ]
                    },
                    "SECTION_SUMMARY": {
                        "rows": [
                            {"Name": "Column_80x80", "I2Mod": "0.7", "I3Mod": "0.7", "AMod": "1", "JMod": "1"},
                            {"Name": "B60x70", "I2Mod": "0.35", "I3Mod": "0.35", "AMod": "1", "JMod": "1"},
                        ]
                    },
                }
            },
        }
        rec = project_analysis_setup_reconciliation(setup, snapshot)
        self.assertIsNotNone(rec)
        self.assertTrue(rec["design_families_assigned"])
        self.assertEqual(rec["assigned_design_families"]["bound_families"], ["ductile", "gravity"])
        self.assertEqual(
            rec["reconciled_blocker_codes"],
            [
                "APPROVED_MODEL_PROFILE_MISSING",
                "LOAD_CASE_ROLES_AND_REMAINING_DESIGN_FAMILIES_UNAPPROVED",
                "ANALYSIS_GENERATION_NOT_PROVEN",
            ],
        )
        self.assertEqual(rec["cracked_section_stiffness_audit"]["status"], "ETABS_TABLE_4_2_MODIFIERS_VERIFIED")
        self.assertTrue(rec["cracked_section_stiffness_audit"]["all_columns_match_0_70"])
        self.assertTrue(rec["cracked_section_stiffness_audit"]["all_beams_match_0_35"])

        # Verify column_r14_closure swaps cracked+creep gate to TS500_CREEP_RATIO_RM_NOT_APPROVED
        geometry = {"columns": [{"element_id": "127", "label": "C1", "story": "+0.00", "section_name": "Column_80x80"}]}
        axial = {
            "combination_plan": {"source": "ASSIGNED_DESIGN", "blockers": [], "design_assignment": {"groups": {"ductile": [], "gravity": ["Grav_Ult"]}}},
            "columns": [{"element_id": "127", "story": "+0.00", "section": "Column_80x80", "ts500_limit_kn": 13440.0, "tbdy_seismic_reference_limit_kn": 8960.0, "governing": {"nd_kn": 300.0}, "combination_checks": []}],
        }
        r14 = project_column_r14_and_r15_closure(
            geometry=geometry,
            axial=axial,
            pmm={"member_id": "127", "observed_exceedance_count": 0},
            r08_second_order={"all_observed_below_numeric_limit": True},
            r08_local={"member_id": "127", "magnified_selected_pmm": {"status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN", "max_utilization": 0.2}},
            beam_r10={"beams": []},
            r10_live={"member_id": "127", "engineer_column_selection": {"status": "ENGINEER_COLUMN_SELECTED_NOT_PROVEN", "selected": {"label": "32Φ16", "selected_transverse": {"all_tbdy_checks_met": True}}}, "column_transverse_and_shear": {"engineer_capacity_shear_ve": {"axes": {"V2": {"max_utilization_ts500": 0.2, "max_utilization_zero_concrete": 0.3}}}}, "story_alpha": {"stories": [{"story": "+0.00", "direction": "X", "denominator_status": "FULL_STORY_COLUMN_DENOMINATOR", "demand_feedback_action": "NONE"}]}},
            analysis_setup_reconciliation=rec,
        )
        # Audit correction: this fixture has no axial-case population, no Y
        # shear/alpha result and unresolved R03 source gates. It MUST NOT close.
        self.assertEqual(r14["status"], "R14_PARTIAL_OR_UNBOUND")
        self.assertIn("R03:ANALYSIS_GENERATION_NOT_PROVEN", r14["open_gates"])
        self.assertIn("TS500_CREEP_RATIO_RM_NOT_APPROVED", r14["open_gates"])
        self.assertNotIn("CREEP_RATIO_RM_AND_CRACKED_SECTION_STIFFNESS_NOT_APPROVED", r14["open_gates"])
        self.assertTrue(r14["pillars"]["second_order_selected_pmm"]["cracked_stiffness_tbdy_4_2_verified"])

    def test_step3_same_station_envelope_beamless_ve_and_spectral_pmm(self):
        from tbdy_next.column_engine.section_capacity import Bar, Material, Section, solver
        from tbdy_next.column_engine.ts500_column import LocalSectionDims
        from tbdy_next.engineering.beam_r10_live import _evaluate_beam_end
        from tbdy_next.engineering.column_r08_local_live import _evaluate_spectral_bounding_corners
        from tbdy_next.engineering.column_r10_live import _compute_capacity_shear_axes
        from tbdy_next.engineering.column_r14_closure import project_column_r14_and_r15_closure

        # 1) Beam end: exact same station -> conservative envelope; distinct stations -> AMBIGUOUS
        profile = {
            "local2_height_mm": 700.0,
            "local3_width_mm": 600.0,
            "cover_top_centroid_mm": 60.0,
            "cover_bottom_centroid_mm": 60.0,
            "cover_to_tie_mm": 42.0,
            "tie_diameter_mm": 8,
            "material": {"fck": 35.0, "fcd": 35.0 / 1.5, "fyd": 500.0 / 1.15, "es": 200000.0},
        }
        mat = Material(fck=35.0, fcd=35.0 / 1.5, fyd=500.0 / 1.15, es=200000.0)
        rho_bounds = {"rho_min": 0.0025, "rho_max": 0.02}
        base_row = {
            "unique_name": "361",
            "design_sect": "B60x70",
            "station_m": 6.6,
            "status": "No Message",
            "warn_msg": "No Message",
            "err_msg": "No Message",
            "as_top_combo": "Grav_Ult",
            "as_bot_combo": "Grav_Ult",
            "t_lng_combo": "Crack_SeisY_Soil",
            "areas_mm2": {"AsTop": 1256.0, "AsMinTop": 975.0, "totTopRebar": 1653.0, "AsBot": 423.0, "AsMinBot": 423.0, "totBotRebar": 714.0, "TLngRebar": 793.0},
        }
        row2 = {
            **base_row,
            "as_top_combo": "Duct_SeisX",
            "areas_mm2": {"AsTop": 1307.0, "AsMinTop": 975.0, "totTopRebar": 1705.0, "AsBot": 854.0, "AsMinBot": 854.0, "totBotRebar": 1038.0, "TLngRebar": 795.0},
        }
        res_same = _evaluate_beam_end(
            end="J", target_sta_m=6.6, length_m=7.0, section_name="B60x70",
            profile=profile, material=mat, design_rows=[base_row, row2],
            override_top_mm2=0.0, override_bot_mm2=0.0, rho_bounds=rho_bounds, released=False,
        )
        self.assertEqual(res_same["status"], "BEAM_CANDIDATE_CALCULATED_NOT_PROVEN")
        self.assertTrue(res_same["station_discontinuity_envelope"])
        self.assertAlmostEqual(res_same["targets_mm2"]["top_mm2"], 1705.0)
        self.assertAlmostEqual(res_same["targets_mm2"]["bottom_mm2"], 1038.0)

        import math
        row_distinct = {**row2, "station_m": 6.6 + math.ulp(6.6)}
        res_diff = _evaluate_beam_end(
            end="J", target_sta_m=6.6, length_m=7.0, section_name="B60x70",
            profile=profile, material=mat, design_rows=[base_row, row_distinct],
            override_top_mm2=0.0, override_bot_mm2=0.0, rho_bounds=rho_bounds, released=False,
        )
        self.assertEqual(res_diff["reason"], "BEAM_DESIGN_STATION_AMBIGUOUS")

        # 2) Beamless column Ve = 1.4*(Mri+Mrj)/ln
        bars = [
            Bar(x2=340.0, x3=340.0, area=314.16), Bar(x2=-340.0, x3=340.0, area=314.16),
            Bar(x2=340.0, x3=-340.0, area=314.16), Bar(x2=-340.0, x3=-340.0, area=314.16),
            Bar(x2=340.0, x3=0.0, area=314.16), Bar(x2=-340.0, x3=0.0, area=314.16),
            Bar(x2=0.0, x3=340.0, area=314.16), Bar(x2=0.0, x3=-340.0, area=314.16),
        ]
        col_sec = Section(t2=800.0, t3=800.0, bars=tuple(bars), material=mat)
        rowset = _rowset([
            ("210", 0.0, "210-1", 0.0, "Grav_Ult", "Single Value", 0.0, -300.0, 10.0, 10.0, 0.0, 50.0, 40.0),
            ("210", 5.15, "210-3", 0.85, "Grav_Ult", "Single Value", 0.0, -200.0, 10.0, 10.0, 0.0, -30.0, -25.0),
        ])
        col_frame = {"axes_global": [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]}
        axes_ve = _compute_capacity_shear_axes(
            uid="210", col_frame=col_frame, ln_m=4.5, scwb_joints=[],
            stations=[{"combination": "Grav_Ult", "nd_kn": 300.0}],
            static_combos=["Grav_Ult"], rowset=rowset, section=col_sec, use_engineer=True,
            vr_lookup=lambda c, a, v: (900.0, 700.0),
        )
        self.assertIn("V2", axes_ve)
        self.assertEqual(axes_ve["V2"]["ve_basis"], "NO_FRAMING_BEAMS_BOTH_ENDS_1_4_MR")
        self.assertEqual(axes_ve["V2"]["cases"][0]["mp_i_basis"], "SUPPORT_UNREDUCED_1_4_MR")
        self.assertEqual(axes_ve["V2"]["cases"][0]["mp_j_basis"], "SUPPORT_UNREDUCED_1_4_MR")

        # 3) Spectral bounding 8-corner box PMM (within capacity & exceeding capacity)
        cap = solver(col_sec)
        dims = LocalSectionDims(800.0, 800.0)
        axial_mock = {"combination_plan": {"combinations": [{"name": "Duct_SeisX", "force_semantics": "SCALAR_COMPONENT_ENVELOPE"}]}}
        src_ok = {
            "column_axial": {
                "force_source": {
                    "rowsets": {
                        "127": _rowset([
                            ("127", 0.0, "127", 0.0, "Duct_SeisX", "Max", 0.0, -50.0, 0.0, 0.0, 0.0, 80.0, 90.0),
                            ("127", 0.0, "127", 0.0, "Duct_SeisX", "Min", 0.0, -250.0, 0.0, 0.0, 0.0, -70.0, -85.0),
                        ])
                    }
                }
            }
        }
        sp_ok = _evaluate_spectral_bounding_corners(
            uid="127", source=src_ok, axial=axial_mock, dims_local=dims, cap_solver=cap,
            stiffness_map={"M2": {"selected_nk_ts500_7_20_kn": 50000.0}, "M3": {"selected_nk_ts500_7_20_kn": 50000.0}},
            global_beta_ii=1.0,
        )
        self.assertEqual(sp_ok["status"], "BOUNDED_CORNER_ENVELOPE_WITHIN_CAPACITY_NOT_PROVEN")
        self.assertEqual(sp_ok["evaluated_corner_count"], 8)
        self.assertLessEqual(sp_ok["max_bounding_utilization"], 1.0)

        src_hi = {
            "column_axial": {
                "force_source": {
                    "rowsets": {
                        "127": _rowset([
                            ("127", 0.0, "127", 0.0, "Duct_SeisX", "Max", 0.0, -50.0, 0.0, 0.0, 0.0, 2500.0, 2500.0),
                            ("127", 0.0, "127", 0.0, "Duct_SeisX", "Min", 0.0, -250.0, 0.0, 0.0, 0.0, -2500.0, -2500.0),
                        ])
                    }
                }
            }
        }
        sp_hi = _evaluate_spectral_bounding_corners(
            uid="127", source=src_hi, axial=axial_mock, dims_local=dims, cap_solver=cap,
            stiffness_map={"M2": {"selected_nk_ts500_7_20_kn": 50000.0}, "M3": {"selected_nk_ts500_7_20_kn": 50000.0}},
            global_beta_ii=1.0,
        )
        self.assertEqual(sp_hi["status"], "CONSERVATIVE_CORNER_EXCEEDS_1_0_CONCURRENT_VECTOR_REQUIRED")
        r14_spec_gate = project_column_r14_and_r15_closure(
            geometry={"columns": [{"element_id": "127", "label": "C1", "story": "+0.00", "section_name": "Column_80x80"}]},
            axial={"combination_plan": {"source": "ASSIGNED_DESIGN", "blockers": [], "design_assignment": {"groups": {"ductile": ["Duct_SeisX"], "gravity": []}}}, "columns": [{"element_id": "127", "story": "+0.00", "section": "Column_80x80", "ts500_limit_kn": 13440.0, "tbdy_seismic_reference_limit_kn": 8960.0, "governing": {"nd_kn": 250.0}, "combination_checks": []}]},
            pmm={"member_id": "127", "observed_exceedance_count": 0},
            r08_second_order={"all_observed_below_numeric_limit": True},
            r08_local={"member_id": "127", "magnified_selected_pmm": {"status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN", "max_utilization": 0.2}, "spectral_envelope_pmm_scenario": sp_hi},
            beam_r10={"beams": []},
            r10_live={"member_id": "127", "engineer_column_selection": {"status": "ENGINEER_COLUMN_SELECTED_NOT_PROVEN", "selected": {"label": "32Φ16", "selected_transverse": {"all_tbdy_checks_met": True}}}, "column_transverse_and_shear": {"engineer_capacity_shear_ve": {"axes": axes_ve}}, "story_alpha": {"stories": [{"story": "+0.00", "direction": "X", "denominator_status": "FULL_STORY_COLUMN_DENOMINATOR", "demand_feedback_action": "NONE"}]}},
        )
        self.assertIn("SPECTRAL_PMM_CONSERVATIVE_BOX_EXCEEDS_1_0_CONCURRENT_VECTORS_NEEDED", r14_spec_gate["open_gates"])
