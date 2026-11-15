"""Mandatory closure tests for YENI_MASTER_HANDOFF_ENGINEERING_RECIPE_2026-11-14.md (F01-F13 & P0-A/B/C)."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from http.server import ThreadingHTTPServer
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from column_stability_fixture import StiffnessBank
from test_engine_r07_r08_chain import sample_receipts, seal
from test_vs15_column_pmm import inputs as pmm_inputs
from tbdy_next.b1_source_bridge import evaluate_b1_sources
from tbdy_next.basis_linkage import LoadRoleBook, review_basis_linkage
from tbdy_next.column_engine.beam_capacity import (
    BLOCKED_UNSUPPORTED_LAYOUT,
    propose_beam_cage_chk132,
    proposed_beam_cage,
)
from tbdy_next.column_engine.column_pmm import build_column_pmm
from tbdy_next.column_engine.column_pmm_quality import build_column_pmm_quality
from tbdy_next.column_engine.csi_geometry import (
    LocalSectionDims,
    NativeSectionDims,
    local_dimensions,
    to_local_dimensions,
)
from tbdy_next.column_engine.section_capacity import Bar, Material, Section, k1_factor, solver
from tbdy_next.column_engine.ts500_column import apply_minimum_eccentricity
from tbdy_next.engineering.column_gates import (
    NAMESPACE_RECONCILIATION,
    audit_model_analysis_setup,
    evaluate_axial_caps,
    evaluate_column_p0_gates,
    evaluate_reinforcement_state,
    evaluate_transverse_leg_topology,
    match_station_with_tolerance,
    parse_canonical_rule_id,
    resolve_legacy73_catalog_entry,
    verify_single_owner_contract,
)
from tbdy_next.engineering.live_column import load_and_evaluate_127_from_receipts
from tbdy_next.etabs_source_gateway_windows import (
    capture_receipt_sha,
    dual_hashes,
    seal as seal_gateway,
    semantic_source_sha,
    verify as verify_gateway,
)
from tbdy_next.web import make_handler


class P0HandoffClosureTests(unittest.TestCase):
    """Covers F01-F13 and P0-A, P0-B, P0-C closure tests from handoff-r1."""

    def test_p0a_namespace_and_catalog_reconciliation(self):
        # 73 Recipe != 94 DAG != 242 Atomic != Rxx != VSxx
        self.assertEqual(NAMESPACE_RECONCILIATION["Rxx"]["count"], 21)
        self.assertEqual(NAMESPACE_RECONCILIATION["VSxx"]["count"], 27)
        self.assertEqual(NAMESPACE_RECONCILIATION["LEGACY73"]["count"], 73)
        self.assertEqual(NAMESPACE_RECONCILIATION["LEGACY242"]["count"], 242)
        self.assertEqual(NAMESPACE_RECONCILIATION["DAG94"]["count"], 94)
        self.assertEqual(sum(NAMESPACE_RECONCILIATION["DAG94"]["breakdown"].values()), 94)

        parsed = parse_canonical_rule_id("TS500:7.7:AXIAL_COMPRESSION_MAX:COLUMN:2000R2018")
        self.assertEqual(parsed["standard"], "TS500")
        self.assertEqual(parsed["clause"], "7.7")
        with self.assertRaises(ValueError):
            parse_canonical_rule_id("INVALID_ID")

        # Catalog fixes: CHK-108 -> PLAN_PROTRUSIONS_A3, CHK-111 -> VERTICAL_DISCONTINUITY_B3, CHK-008 -> None
        chk108 = resolve_legacy73_catalog_entry("LEGACY73:CHK-108")
        self.assertEqual(chk108["canonical_name"], "PLAN_PROTRUSIONS_A3")
        with self.assertRaises(ValueError):
            resolve_legacy73_catalog_entry("LEGACY73:CHK-108", proposed_label="Storey Discontinuity")

        chk111 = resolve_legacy73_catalog_entry("LEGACY73:CHK-111")
        self.assertEqual(chk111["canonical_name"], "VERTICAL_DISCONTINUITY_B3")
        with self.assertRaises(ValueError):
            resolve_legacy73_catalog_entry("LEGACY73:CHK-111", proposed_label="Mass Irregularity")

        self.assertIsNone(resolve_legacy73_catalog_entry("CHK-008"))
        self.assertIsNone(resolve_legacy73_catalog_entry("LEGACY73:CHK-008"))

    def test_p0a_and_f12_single_owner_contract_and_packaging(self):
        report = verify_single_owner_contract()
        self.assertEqual(report["status"], "VERIFIED")
        self.assertEqual(report["tools_imports_in_src_tbdy_next"], [])
        self.assertTrue(report["presentation_has_no_formula_owner"])

    def test_f01_axial_compression_caps_independent_of_pmm_ratio(self):
        # 800x800 mm, C35/45 (fck=35, fcd=35/1.5=23.3333 MPa), B420C (fyd=365.217 MPa), 16Phi24
        ac = 800.0 * 800.0
        ast = 16 * math.pi * 24.0**2 / 4.0
        fcd = 35.0 / 1.5
        fyd = 420.0 / 1.15

        # Nd exceeds the TS500 7.7 limit and stays within the steel-plus-net-concrete capacity.
        res = evaluate_axial_caps(
            nd_kn=14000.0,
            fck_mpa=35.0,
            fcd_mpa=fcd,
            fyd_mpa=fyd,
            ac_mm2=ac,
            ast_mm2=ast,
            is_seismic_combo=False,
            pmm_utilization=0.89,
        )
        self.assertAlmostEqual(res["raw_plastic_n0_kn"], 15193.3024, places=4)
        self.assertAlmostEqual(res["checks"]["CHK-005"]["limit_kn"], 13440.0, places=3)
        self.assertAlmostEqual(res["checks"]["CHK-004"]["limit_kn"], 8960.0, places=3)
        self.assertFalse(res["080_n0_is_ts500_7_7"])
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(res["formal_compliance"], "FAIL")
        self.assertTrue(res["overrides_pmm_pass"])
        self.assertIn("CHK005_TS500_7_7_AXIAL_LIMIT_EXCEEDED", res["reason_codes"])

        # Seismic combo with Ndm = 9,500 kN (> 8,960 kN TBDY 7.3.1.2 limit)
        seis = evaluate_axial_caps(
            nd_kn=9500.0,
            fck_mpa=35.0,
            fcd_mpa=fcd,
            fyd_mpa=fyd,
            ac_mm2=ac,
            ast_mm2=ast,
            is_seismic_combo=True,
            pmm_utilization=0.61,
        )
        self.assertEqual(seis["status"], "FAIL")
        self.assertEqual(seis["checks"]["CHK-004"]["status"], "FAIL")
        self.assertIn("CHK004_TBDY_7_3_1_2_AXIAL_LIMIT_EXCEEDED", seis["reason_codes"])

    def test_f02_f08_f09_minimum_eccentricity_and_single_axis_conversion(self):
        # F08 & F09: 300x800 mm non-square section (native T2=300, T3=800)
        native = NativeSectionDims(native_t2_mm=300.0, native_t3_mm=800.0)
        local = to_local_dimensions(native)
        self.assertEqual(local.local2_extent_mm, 800.0)
        self.assertEqual(local.local3_extent_mm, 300.0)
        self.assertEqual(local.bending_depth_m2_mm, 300.0)
        self.assertEqual(local.bending_depth_m3_mm, 800.0)

        # F09: Double axis conversion (swap-back) is denied by type system
        with self.assertRaises(TypeError):
            to_local_dimensions(local)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            local_dimensions(local, 800.0)

        # F02 & F08: Small moment + high Nd on 300x800 mm for Angle=0 and Angle=90
        emin_0 = apply_minimum_eccentricity(
            nd_kn=1000.0, m2_knm=5.0, m3_knm=-10.0, dims=native, local_axis_angle_deg=0.0
        )
        self.assertAlmostEqual(emin_0["e_min_m2_mm"], 24.0)
        self.assertAlmostEqual(emin_0["e_min_m3_mm"], 39.0)
        self.assertAlmostEqual(emin_0["m2_design_knm"], 24.0)
        self.assertAlmostEqual(emin_0["m3_design_knm"], -39.0)
        self.assertTrue(emin_0["m2_floor_governed"])
        self.assertTrue(emin_0["m3_floor_governed"])

        emin_90 = apply_minimum_eccentricity(
            nd_kn=1000.0, m2_knm=5.0, m3_knm=-10.0, dims=local, local_axis_angle_deg=90.0
        )
        self.assertAlmostEqual(emin_90["mx_global_design_knm"], 39.0, places=6)
        self.assertAlmostEqual(emin_90["my_global_design_knm"], 24.0, places=6)

        # Asymmetric PMM verification on 300x800 mm section
        bars = (
            Bar(-340.0, -90.0, 452.389),
            Bar(340.0, -90.0, 452.389),
            Bar(-340.0, 90.0, 452.389),
            Bar(340.0, 90.0, 452.389),
        )
        sec = Section(local.local2_extent_mm, local.local3_extent_mm, bars, Material(35.0, 35.0 / 1.5, 420.0 / 1.15))
        pmm = solver(sec)
        raw_res = pmm.assess(1000.0 * 1000.0, 5.0 * 1e6, -10.0 * 1e6)
        emin_res = pmm.assess(1000.0 * 1000.0, emin_0["m2_design_knm"] * 1e6, emin_0["m3_design_knm"] * 1e6)
        self.assertGreater(emin_res["utilization"], raw_res["utilization"])

    def test_f03_template_vs_proposed_vs_selected_reinforcement(self):
        ac = 800.0 * 800.0
        # 1. TEMPLATE (12Phi20, IsDesigned=Yes, rho=0.589%)
        tpl = evaluate_reinforcement_state(
            role="TEMPLATE", ac_mm2=ac, bar_count=12, bar_diameter_mm=20.0, is_designed_flag=True
        )
        self.assertEqual(tpl["status"], "TEMPLATE_ONLY_NOT_SELECTED_CAGE")
        self.assertEqual(tpl["formal_compliance"], "NOT_PROVEN")
        self.assertTrue(tpl["would_fail_if_selected"])
        self.assertLess(tpl["rho"], 0.01)

        # 2. PROPOSED (16Phi24, rho=1.131%)
        prop = evaluate_reinforcement_state(
            role="PROPOSED", ac_mm2=ac, bar_count=16, bar_diameter_mm=24.0
        )
        self.assertEqual(prop["status"], "PROPOSED_SCENARIO_ONLY")
        self.assertEqual(prop["formal_compliance"], "NOT_PROVEN")
        self.assertFalse(prop["selection_approved"])
        self.assertTrue(0.01 <= prop["rho"] <= 0.04)

        # 3. SELECTED with 12Phi20 (rho < 1.0%) -> explicit FAIL
        sel_fail = evaluate_reinforcement_state(
            role="SELECTED", ac_mm2=ac, bar_count=12, bar_diameter_mm=20.0, selection_approved=True
        )
        self.assertEqual(sel_fail["status"], "FAIL")
        self.assertEqual(sel_fail["formal_compliance"], "FAIL")
        self.assertIn("RHO_BELOW_TBDY_MIN_001", sel_fail["reason_codes"])

    def test_f04_missing_design_selection_does_not_claim_list_contents(self):
        gateway = sample_receipts()["live"]["gateway_capture"]
        absent = audit_model_analysis_setup(gateway)
        self.assertIn("CONCRETE_DESIGN_COMBINATIONS_NOT_OBSERVED", absent["blocker_codes"])
        self.assertIsNone(absent["design_selection_count"])
        self.assertIsNone(absent["strength_design_combinations"])
        self.assertEqual(absent["verdict"], "NOT_PROVEN")
        self.assertIn("ANALYSIS_GENERATION_NOT_PROVEN", absent["blocker_codes"])
        self.assertFalse(absent["nonlin_case_none_alone_proves_first_order"])

    def test_f05_dual_hash_and_tolerant_station_matching(self):
        rec1 = {
            "schema": "tbdy.next.etabs.generic-source-capture.v1",
            "captured_at_utc": "2026-11-14T10:00:00Z",
            "model": r"C:\tmp\kompakt_b.EDB",
            "model_units_code": 6,
            "table_reads": {"Story Definitions": {"status": "CAPTURED", "row_count": 1, "rows": [{"Story": "+3.00"}]}},
        }
        rec2 = deepcopy(rec1)
        rec2["captured_at_utc"] = "2026-11-14T12:34:56Z"
        rec1["semantic_source_sha"] = semantic_source_sha(rec1)
        rec2["semantic_source_sha"] = semantic_source_sha(rec2)
        sealed1 = seal_gateway(rec1)
        sealed2 = seal_gateway(rec2)
        verify_gateway(sealed1)
        verify_gateway(sealed2)

        self.assertEqual(semantic_source_sha(sealed1), semantic_source_sha(sealed2))
        self.assertNotEqual(capture_receipt_sha(sealed1), capture_receipt_sha(sealed2))
        self.assertEqual(dual_hashes(sealed1)["semantic_source_sha"], dual_hashes(sealed2)["semantic_source_sha"])

        prior = {(1.9, 1.9, "Single Value", 0.0): {"station": 1.9}}
        key, val = match_station_with_tolerance(prior, 1.9000004, 1.9000004, "Single Value", 0.0, tol_m=1e-6)
        self.assertEqual(key[0], 1.9)
        self.assertEqual(val["station"], 1.9)
        with self.assertRaises(ValueError):
            match_station_with_tolerance(prior, 1.91, 1.91, "Single Value", 0.0, tol_m=1e-6)

    def test_f07_transverse_leg_topology_chk123(self):
        # 16Phi24 on 800x800: 5 bars per face at [-336, -168, 0, 168, 336], bar spacing = 168 mm.
        # With Phi12 stirrup + crossties on all 5 bars (a_i = 168 mm <= 25*12 = 300 mm) and s = 100 mm <= 6*24 = 144 mm:
        coords = [-336.0, -168.0, 0.0, 168.0, 336.0]
        ok_top = evaluate_transverse_leg_topology(
            b_min_mm=800.0,
            longitudinal_bar_diameter_mm=24.0,
            transverse_bar_diameter_mm=12.0,
            vertical_spacing_s_mm=100.0,
            face_bar_coords_mm=coords,
            tied_bar_indices=[0, 1, 2, 3, 4],
        )
        self.assertEqual(ok_top["status"], "WITHIN_TOPOLOGY_LIMITS")
        self.assertTrue(ok_top["ai_met"])
        self.assertTrue(ok_top["s_met"])
        self.assertAlmostEqual(ok_top["max_ai_mm"], 168.0)
        self.assertAlmostEqual(ok_top["ai_limit_25_phi_e_mm"], 300.0)

        missing_legs = evaluate_transverse_leg_topology(
            b_min_mm=800.0,
            longitudinal_bar_diameter_mm=24.0,
            transverse_bar_diameter_mm=12.0,
            vertical_spacing_s_mm=100.0,
            face_bar_coords_mm=coords,
        )
        self.assertEqual(missing_legs["status"], "NOT_PROVEN")
        self.assertIsNone(missing_legs["ai_met"])

        # Without internal crossties (only corners 0 and 4 tied -> a_i = 672 mm > 300 mm): FAIL
        no_ties = evaluate_transverse_leg_topology(
            b_min_mm=800.0,
            longitudinal_bar_diameter_mm=24.0,
            transverse_bar_diameter_mm=12.0,
            vertical_spacing_s_mm=100.0,
            face_bar_coords_mm=coords,
            tied_bar_indices=[0, 4],
        )
        self.assertEqual(no_ties["status"], "FAIL")
        self.assertIn("AI_EXCEEDS_25_PHI_TRANSVERSE", no_ties["reason_codes"])

        # s = 150 mm with Phi20 longitudinal bars (6 * 20 = 120 mm < 150 mm): FAIL
        bad_s = evaluate_transverse_leg_topology(
            b_min_mm=800.0,
            longitudinal_bar_diameter_mm=20.0,
            transverse_bar_diameter_mm=10.0,
            vertical_spacing_s_mm=150.0,
            face_bar_coords_mm=[-341.0, -113.67, 113.67, 341.0],
            tied_bar_indices=[0, 1, 2, 3],
        )
        self.assertEqual(bad_s["status"], "FAIL")
        self.assertIn("S_EXCEEDS_6_PHI_LONGITUDINAL", bad_s["reason_codes"])

    def test_f10_continuous_k1_across_intermediate_fck_values(self):
        expected = {
            22: 0.85,
            25: 0.85,
            28: 0.832,
            30: 0.82,
            32: 0.808,
            35: 0.79,
            50: 0.70,
        }
        for fck, k1_exp in expected.items():
            with self.subTest(fck=fck):
                self.assertAlmostEqual(k1_factor(fck), k1_exp, places=9)
                mat = Material(float(fck), float(fck) / 1.5, 420.0 / 1.15)
                self.assertAlmostEqual(mat.k1, k1_exp, places=9)
                fixture = StiffnessBank()
                fixture.calls[("PropMaterial.GetOConcrete", "material", "CONCRETE_SYNTHETIC")]["raw_response"][0] = fck * 1000
                fixture.set_static_vector((-500.0, 0, 0, 0, 40.0, 60.0))
                _, chain, _, stability, cages = pmm_inputs(fixture)
                result = build_column_pmm(chain, cages, stability)
                quality = build_column_pmm_quality(
                    chain, cages, result, member_id="C_SYNTHETIC_1", output_case="SUM"
                )
                self.assertGreater(quality["comparison_count"], 0)
                self.assertEqual(quality["status_counts"], {
                    "NUMERICAL_COMPARISON_MATCH": quality["comparison_count"]
                })
                for model in quality["reference_models"]:
                    self.assertAlmostEqual(model["parameters"]["block_depth_factor"], k1_exp, places=9)

    def test_f11_non_numeric_story_names_and_load_role_book(self):
        # Test basis_linkage with "Zemin", "1. Kat", "2. Kat" and custom case names
        def tbl(key, fields, rows, units=None):
            return {
                "table_key": key,
                "status": "CAPTURED",
                "fields": list(fields),
                "row_count": len(rows),
                "rows": [dict(zip(fields, r)) for r in rows],
                "field_metadata": {
                    "status": "OK",
                    "field_count": len(fields),
                    "field_keys": list(fields),
                    "units_by_field": units or {f: "" for f in fields},
                },
            }

        reads = {
            "Story Definitions": tbl(
                "Story Definitions",
                ["Tower", "Story", "Height"],
                [["T1", "2. Kat", "3.0"], ["T1", "1. Kat", "3.0"], ["T1", "Zemin", "4.0"]],
                {"Height": "m"},
            ),
            "Tower and Base Story Definitions": tbl(
                "Tower and Base Story Definitions",
                ["Tower", "BSName", "BSElev"],
                [["T1", "Temel", "0.0"]],
                {"BSElev": "m"},
            ),
            "Mass Summary by Story": tbl(
                "Mass Summary by Story",
                ["Story", "UX", "UY", "UZ"],
                [["Zemin", "100", "100", "0"], ["1. Kat", "100", "100", "0"], ["2. Kat", "100", "100", "0"]],
                {"UX": "ton", "UY": "ton", "UZ": "ton"},
            ),
            "Mass Summary by Group": tbl(
                "Mass Summary by Group",
                ["Group", "MassX", "MassY", "MassZ"],
                [["All", "300", "300", "0"]],
                {"MassX": "ton", "MassY": "ton", "MassZ": "ton"},
            ),
            "Mass Source Definition": tbl(
                "Mass Source Definition",
                ["Name", "IsDefault", "SourceSelf", "SourceLoads", "LoadPattern", "Multiplier"],
                [["Kutle_Ana", "Yes", "Yes", "Yes", "G_SABIT", "1.0"]],
            ),
            "Assembled Joint Masses": tbl(
                "Assembled Joint Masses",
                ["PointElm", "Story", "UX", "UY", "UZ"],
                [["J1", "Zemin", "100", "100", "0"], ["J2", "1. Kat", "100", "100", "0"], ["J3", "2. Kat", "100", "100", "0"]],
                {"UX": "ton", "UY": "ton", "UZ": "ton"},
            ),
            "Mass Summary by Diaphragm": tbl(
                "Mass Summary by Diaphragm",
                ["Story", "Diaphragm", "MassX", "MassY"],
                [["Zemin", "D1", "100", "100"], ["1. Kat", "D1", "100", "100"], ["2. Kat", "D1", "100", "100"]],
                {"MassX": "ton", "MassY": "ton"},
            ),
            "Functions - Response Spectrum - TSC-2018": tbl(
                "Functions - Response Spectrum - TSC-2018",
                ["Name", "Period", "Value", "Ss", "S1", "R", "D", "I", "SDS", "SD1", "Fs", "F1"],
                [
                    ["AFAD_DD2", "0.0", "0.4", "1.0", "0.3", "7", "2.5", "1.0", "1.2", "0.45", "1.2", "1.5"],
                    ["AFAD_DD2", "0.2", "1.2", "1.0", "0.3", "7", "2.5", "1.0", "1.2", "0.45", "1.2", "1.5"],
                ],
                {"Period": "sec", "I": "sec"},
            ),
            "Load Case Definitions - Response Spectrum": tbl(
                "Load Case Definitions - Response Spectrum",
                ["Name", "MassSource", "LoadName", "Function", "TransAccSF", "CoordSys", "Angle", "ModalCase", "ModalCombo", "DirCombo", "EccenRatio"],
                [
                    ["EX_SPEK", "Previous  (Kutle_Ana)", "U1", "AFAD_DD2", "9.81", "Global", "0", "MOD_RITZ", "CQC", "SRSS", "0.05"],
                    ["EY_SPEK", "Previous  (Kutle_Ana)", "U2", "AFAD_DD2", "9.81", "Global", "0", "MOD_RITZ", "CQC", "SRSS", "0.05"],
                ],
                {"TransAccSF": "m/sec2", "Angle": "deg"},
            ),
            "Load Case Definitions - Summary": tbl(
                "Load Case Definitions - Summary",
                ["Name", "Type"],
                [["MOD_RITZ", "Modal - Ritz"], ["EX_SPEK", "Response Spectrum"], ["EY_SPEK", "Response Spectrum"]],
            ),
            "Modal Case Definitions - Ritz": tbl(
                "Modal Case Definitions - Ritz",
                ["Name", "MassSource", "LoadType", "LoadName", "MaxModes", "TargetRatio"],
                [
                    ["MOD_RITZ", "Kutle_Ana", "Accel", "Accel UX", "12", "99"],
                    ["MOD_RITZ", "Kutle_Ana", "Accel", "Accel UY", "12", "99"],
                ],
                {"TargetRatio": "%"},
            ),
            "Load Case Definitions - Damping - Modal": tbl(
                "Load Case Definitions - Damping - Modal",
                ["Name", "DampType", "ConstDamp"],
                [["EX_SPEK", "Constant", "0.05"], ["EY_SPEK", "Constant", "0.05"]],
            ),
            "Response Spectrum Modal Info": tbl(
                "Response Spectrum Modal Info",
                ["Case", "Mode"],
                [["EX_SPEK", "1"]],
            ),
        }
        probe = {
            "schema": "tbdy.next.vs04e.basis-source-probe.v1",
            "source_mode": "LIVE_ETABS",
            "read_only_invariant_proven": True,
            "units_before": 6,
            "units_after": 6,
            "display_cases_before": ["MOD_RITZ"],
            "display_cases_after": ["MOD_RITZ"],
            "available_table_count": len(reads),
            "candidate_tables": [
                {"table_key": k, "table_name": k, "import_type": 1, "candidate_roles_not_approved": ["seismic_mass"]}
                for k in reads
            ],
            "table_reads": reads,
            "schema_roles_approved": False,
            "analysis_generation_proven": False,
        }
        rb = LoadRoleBook(
            mass_source="Kutle_Ana",
            modal_case="MOD_RITZ",
            x_spectrum_case="EX_SPEK",
            y_spectrum_case="EY_SPEK",
            wall_load_pattern="DUVAR_YUKU",
        )
        res = review_basis_linkage(probe, role_book=rb)
        self.assertEqual(res["observed_component_count"], 4)
        geom_comp = next(c for c in res["components"] if c["component"] == "PHYSICAL_STORY_GEOMETRY")
        self.assertEqual(geom_comp["status"], "SOURCE_CONTRACT_OBSERVED_UNAPPROVED")
        levels = geom_comp["source_facts"]["levels_bottom_up"]
        self.assertEqual([lv["story"] for lv in levels], ["Zemin", "1. Kat", "2. Kat"])
        self.assertEqual([Decimal(lv["elevation_m"]) for lv in levels], [Decimal("4.0"), Decimal("7.0"), Decimal("10.0")])

        # Also verify B1 source bridge with non-numeric stories ("Zemin", "1. Kat", "2. Kat") and custom wall load pattern
        from test_vs06_b1_source_bridge import sources as b1_sources
        from test_vs05_story_drift_binding import seal as seal_b1
        g_b1, l_b1 = b1_sources()
        g_b1.pop("payload_sha256", None)
        l_b1.pop("payload_sha256", None)
        story_map = {"+3.00": "Zemin", "+6.00": "1. Kat", "+9.00": "2. Kat"}
        for tname in ("Story Definitions", "Frame Assignments - Section Properties", "Column Object Connectivity", "Area Assignments - Section Properties", "Wall Object Connectivity"):
            for r in g_b1["table_reads"][tname]["rows"]:
                r["Story"] = story_map[r["Story"]]
        for r in l_b1["table_reads"]["Beam Object Connectivity"]["rows"]:
            r["Story"] = story_map[r["Story"]]
        for r in l_b1["frame_load_object_probe"]["rows"]:
            r["LoadPattern"] = "DUVAR_YUKU"
        b1_res = evaluate_b1_sources(seal_b1(g_b1), seal_b1(l_b1), role_book=rb)
        self.assertEqual([s["story"] for s in b1_res["story_direction_areas"]], ["Zemin", "1. Kat", "2. Kat"])
        self.assertEqual(b1_res["source_candidate_wall_beams"], 2)

    def test_f13_beam_single_row_blocked_and_multi_row_chk132(self):
        profile = {
            "local2_height_mm": 600.0,
            "local3_width_mm": 250.0,
            "cover_top_centroid_mm": 55.0,
            "cover_bottom_centroid_mm": 55.0,
            "material": {"fck": 35.0, "fcd": 35.0 / 1.5, "fyd": 420.0 / 1.15},
        }
        target = 5.5 * math.pi * 24**2 / 4
        legacy = proposed_beam_cage(profile, target, target, 24)
        self.assertEqual(legacy["reason"], "BEAM_SINGLE_ROW_SPACING_BELOW_REFERENCE")

        blocked = propose_beam_cage_chk132(profile, target, target, 24, allow_multi_row=False)
        self.assertEqual(blocked["status"], BLOCKED_UNSUPPORTED_LAYOUT)
        self.assertFalse(blocked["final_design_eligible"])

        multi = propose_beam_cage_chk132(
            profile, target, target, 24, allow_multi_row=True, max_rows_per_face=2
        )
        self.assertEqual(multi["status"], "BEAM_PROPOSAL_CALCULATED")
        self.assertEqual(multi["layout_mode"], "TWO_ROW")
        self.assertEqual(multi["top_row_counts"], [4, 2])
        self.assertAlmostEqual(multi["effective_top_centroid_mm"], 55.0 + 49.0 / 3)
        self.assertFalse(multi["final_design_eligible"])

    def test_p0_gate_report_is_projected_as_json_and_html(self):
        files = sample_receipts()
        live, lc_run, prior = (files[key] for key in ("live", "lc_run", "pmm_run"))
        gateway = live["gateway_capture"]
        reinforcement = gateway["table_reads"]["Frame Section Property Definitions - Concrete Column Reinforcing"]["rows"][0]
        reinforcement.update(
            ReinfConfig="Rectangular", NumBars2Dir="5", NumBars3Dir="3",
            BarSizeLong="20", BarSizeCorn="20", BarSizeConf="10", SpacingConf="0.15", IsDesigned="Yes",
        )
        del gateway["payload_sha256"]
        seal(gateway)
        live["selected_identity"].update(Elm="101", ObjSta=0.0, ElmSta=0.0, StepNum=0.0)
        live["native_force_row"] = {**live["selected_identity"], "P": -100.0, "M2": 10.0, "M3": 3.0}
        del live["payload_sha256"]
        seal(live)

        r07, _, r09 = lc_run["check_instances"]
        r07["numeric_detail"]["owner_pmm_result"] = {"utilization": 0.05}
        r09["numeric_detail"].update(bar_diameter_mm=24.0, tie_diameter_mm=12.0)
        for check in (r07, r09):
            del check["instance_sha256"]
            seal(check, "instance_sha256")
        lc_run["source"]["source_sha256"] = live["payload_sha256"]
        del lc_run["run_result_sha256"]
        seal(lc_run, "run_result_sha256")
        prior["reference_lc_dl_run_sha256"] = lc_run["run_result_sha256"]
        del prior["run_result_sha256"]
        seal(prior, "run_result_sha256")

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipts = root / "column_127_receipts"
            run_path = receipts / "r07_r09_results" / "fixture" / "run_result.json"
            run_path.parent.mkdir(parents=True)
            for filename, payload in (
                ("r07_r09_live.json", live),
                ("r07_127_gravult_capture.json", files["combo"]),
                ("r07_127_gravult_numeric_result.json", prior),
                ("r08_127_live_offsets_axes_points.json", files["geometry"]),
                (run_path.relative_to(receipts), lc_run),
            ):
                (receipts / filename).write_text(json.dumps(payload), encoding="utf-8")

            with patch("tbdy_next.engineering.live_column.solver") as solver_factory:
                solver_factory.return_value.assess.return_value = {
                    "status": "WITHIN_SCENARIO_SURFACE", "utilization": 0.05,
                }
                self._assert_gate_projections(root, receipts)

    def _assert_gate_projections(self, root, receipts):
        bundle = load_and_evaluate_127_from_receipts(receipts)
        p0 = bundle["p0_gate_report"]
        self.assertEqual(p0["member"], "101")
        self.assertEqual(p0["label"], "C1")
        self.assertEqual(p0["story"], "+4.50")
        self.assertEqual(bundle["reconciled"]["r08"]["geometry"]["observed_output_span_m"], 3.8)
        self.assertEqual(p0["verdict_summary"]["template_12phi20_if_selected"], "FAIL")
        self.assertEqual(p0["verdict_summary"]["template_tie_phi10_s150"], "FAIL")
        self.assertEqual(p0["verdict_summary"]["analysis_setup_status"], "BLOCKED")
        self.assertEqual(p0["verdict_summary"]["analysis_setup_verdict"], "NOT_PROVEN")
        self.assertEqual(p0["verdict_summary"]["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(p0["verdict_summary"]["engineering_release"], "NOT_READY")
        self.assertEqual(p0["verdict_summary"]["production_ready"], "NO")
        trans = p0["p0b_gates"]["f07_transverse_topology"]
        self.assertEqual(trans["proposed_16phi24"]["status"], "NOT_PROVEN")
        self.assertIsNone(trans["etabs_template_12phi20_phi10_s150"]["max_ai_mm"])

        with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root)) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base + "/api/column-127-gates", timeout=5) as resp:
                    api_json = json.load(resp)
                self.assertEqual(api_json, json.loads(json.dumps(p0)))
                with urlopen(base + "/report/column-127", timeout=5) as resp:
                    html = resp.read().decode("utf-8")
                self.assertIn("Column 101 (C1)", html)
                self.assertIn(p0["result_sha256"], html)
            finally:
                server.shutdown()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
