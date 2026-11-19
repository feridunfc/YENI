"""Tests for engineer-selectable beam & column rebar, stirrup and crosstie policies."""
from __future__ import annotations

import contextlib
from hashlib import sha256
import io
import json
from math import pi
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.cli import main as cli_main
from tbdy_next.column_engine.beam_capacity import build_selected_beam_cage
from tbdy_next.engineering.rebar_selection import (
    DEFAULT_BEAM_SELECTION_POLICY,
    DEFAULT_COLUMN_SELECTION_POLICY,
    evaluate_beam_stirrups,
    normalize_beam_selection_policy,
    normalize_column_selection_policy,
    select_beam_station_rebar,
    select_column_rebar,
)
import test_beam_r10_live
from rebar_selection_fixture import attach_configured_selection_scope, configure_three_cut_forces

_C30 = {"fck_mpa": 30.0, "fcd_mpa": 20.0, "fctd_mpa": 1.28, "gamma_c": 1.5}
_B420 = {"fyk_mpa": 420.0, "fyd_mpa": 420.0 / 1.15, "gamma_s": 1.15}
_BEAM_RHO_BOUNDS = {"rho_min": 0.8 * _C30["fctd_mpa"] / _B420["fyd_mpa"], "rho_max": 0.02}


def _beam_profile(*, b_mm: float = 300.0, h_mm: float = 500.0, cover_mm: float = 52.0) -> dict:
    return {
        "local2_height_mm": h_mm,
        "local3_width_mm": b_mm,
        "cover_top_centroid_mm": cover_mm,
        "cover_bottom_centroid_mm": cover_mm,
        "material": {
            "fck": _C30["fck_mpa"],
            "fcd": _C30["fcd_mpa"],
            "fyd": _B420["fyd_mpa"],
            "es": 200_000.0,
        },
        "fcd_mpa": _C30["fcd_mpa"],
        "fyd_mpa": _B420["fyd_mpa"],
        "es_mpa": 200_000.0,
    }


class RebarSelectionUnitTests(unittest.TestCase):
    def test_beam_defaults_include_montage_2phi12_2phi14_and_12_to_25_selectable(self):
        policy = normalize_beam_selection_policy("default")
        self.assertEqual(policy["top_continuous"], {"count": 2, "diameter_mm": 12})
        self.assertEqual(policy["bottom_continuous"], {"count": 2, "diameter_mm": 14})
        self.assertEqual(policy["allowed_additional_diameters_mm"], [16, 20, 22, 24, 25])
        self.assertEqual(policy["stirrup_confinement"], {"diameter_mm": 8, "spacing_mm": 100.0, "legs": 2})
        self.assertEqual(policy["stirrup_span"], {"diameter_mm": 8, "spacing_mm": 150.0, "legs": 2})

        all_diams = normalize_beam_selection_policy({
            "allowed_additional_diameters_mm": [12, 14, 16, 20, 22, 24, 25],
        })
        self.assertEqual(all_diams["allowed_additional_diameters_mm"], [12, 14, 16, 20, 22, 24, 25])

    def test_beam_cage_and_station_selection_strictly_exceed_required_and_compute_m3(self):
        profile = _beam_profile(b_mm=300.0, h_mm=500.0)
        bounds = _BEAM_RHO_BOUNDS
        policy = normalize_beam_selection_policy("default")

        selected = select_beam_station_rebar(
            profile=profile,
            top_req_mm2=1450.0,
            bot_req_mm2=650.0,
            rho_bounds=bounds,
            policy=policy,
            is_support=True,
        )
        self.assertEqual(selected["selection_status"], "ENGINEER_REBAR_SELECTED_NOT_PROVEN")
        self.assertEqual(selected["status"], "BEAM_SELECTED_CALCULATED")
        self.assertTrue(selected["strictly_exceeds_targets"])
        self.assertGreater(selected["area_top_mm2"], 1450.0)
        self.assertGreater(selected["area_bottom_mm2"], 0.5 * selected["area_top_mm2"])
        self.assertTrue(selected["support_compression_half_tension_met"])
        self.assertTrue(selected["rho_bounds_met"])
        self.assertIn("2Φ12", selected["top_label"])
        self.assertIn("2Φ14", selected["bottom_label"])
        self.assertGreater(selected["capacity"]["positive_m3_knm"], 0.0)
        self.assertLess(selected["capacity"]["negative_m3_knm"], 0.0)

        # Equal area fails strict_exceeds_required when strictly_exceeds_required=True
        exact_top = 2 * 113.0973355 + 2 * 314.1592654
        strict_cage = build_selected_beam_cage(
            profile,
            top_continuous_count=2,
            top_continuous_diameter_mm=12,
            top_additional_count=2,
            top_additional_diameter_mm=20,
            bottom_continuous_count=2,
            bottom_continuous_diameter_mm=14,
            bottom_additional_count=0,
            bottom_additional_diameter_mm=16,
            target_top_mm2=exact_top,
            target_bottom_mm2=250.0,
        )
        self.assertFalse(strict_cage["strictly_exceeds_targets"])

    def test_beam_stirrups_evaluate_phi8_10_and_15_and_flag_8_d_min_for_phi12(self):
        c30 = _C30
        b420 = _B420
        policy = normalize_beam_selection_policy("default")

        res_phi12 = evaluate_beam_stirrups(
            b_mm=300.0,
            h_mm=500.0,
            d_eff_mm=460.0,
            min_long_diameter_mm=12,
            fctd_mpa=c30["fctd_mpa"],
            fcd_mpa=c30["fcd_mpa"],
            fywk_mpa=b420["fyk_mpa"],
            gamma_s=1.15,
            ve_eq_kn=120.0,
            ve_total_kn=160.0,
            policy=policy,
        )
        self.assertEqual(res_phi12["confinement"]["label"], "Φ8/100")
        self.assertEqual(res_phi12["span"]["label"], "Φ8/150")
        self.assertFalse(res_phi12["confinement"]["spacing_ok"])
        self.assertTrue(any("TBDY_7_4_4_4_SPACING_EXCEEDS_8_D_MIN" in a for a in res_phi12["alerts"]))

        res_phi14 = evaluate_beam_stirrups(
            b_mm=300.0,
            h_mm=500.0,
            d_eff_mm=460.0,
            min_long_diameter_mm=14,
            fctd_mpa=c30["fctd_mpa"],
            fcd_mpa=c30["fcd_mpa"],
            fywk_mpa=b420["fyk_mpa"],
            gamma_s=1.15,
            ve_eq_kn=120.0,
            ve_total_kn=160.0,
            policy=policy,
        )
        self.assertTrue(res_phi14["confinement"]["spacing_ok"])
        self.assertEqual(res_phi14["alerts"], [])

    def test_column_selection_accepts_exact_one_percent_and_rejects_a_deficit(self):
        four_bar_area = pi * 20**2
        width = 342.0
        exact_depth = four_bar_area / (0.01 * width)
        policy = normalize_column_selection_policy({
            "allowed_longitudinal_diameters_mm": [20],
            "stirrup_confinement_spacing_mm": 50.0,
            "stirrup_span_spacing_mm": 80.0,
        })
        for depth, expected_count in ((exact_depth, 4), (exact_depth + 1e-7, 6)):
            with self.subTest(depth=depth):
                result = select_column_rebar(
                    t2_mm=width, t3_mm=depth, cover_mm=40.0,
                    fck_mpa=30.0, fcd_mpa=20.0, fyd_mpa=420.0 / 1.15, es_mpa=200_000.0,
                    fywk_mpa=420.0, gamma_c=1.5, gamma_s=1.15, local_axis_angle_deg=0.0,
                    demand_vectors=[{"nd_kn": 0.01, "m2_knm": 0.0, "m3_knm": 0.0}],
                    shear_demands=[{"nd_kn": 0.01, "v2_kn": 0.0, "v3_kn": 0.0}], policy=policy,
                )
                minimum = result["tbdy_minimum_longitudinal_area_mm2"]
                if expected_count == 4:
                    self.assertEqual(minimum, four_bar_area)
                self.assertEqual(result["selected"]["bar_count"], expected_count)
                self.assertGreaterEqual(result["selected"]["area_mm2"], minimum)

    def test_column_selection_computes_counts_from_pmm_steps_up_phi8_to_phi10_and_adds_crossties(self):
        c30 = _C30
        b420 = _B420
        policy = normalize_column_selection_policy(DEFAULT_COLUMN_SELECTION_POLICY)

        # Wide 800x400 column triggers crossties along 800 mm face (a <= 25*phi_tie)
        demands = [{"nd_kn": 1800.0, "m2_knm": 180.0, "m3_knm": 320.0}]
        shears = [{"nd_kn": 1800.0, "v2_kn": 140.0, "v3_kn": 90.0}]
        res = select_column_rebar(
            t2_mm=800.0,
            t3_mm=400.0,
            cover_mm=40.0,
            fck_mpa=c30["fck_mpa"],
            fcd_mpa=c30["fcd_mpa"],
            fyd_mpa=b420["fyd_mpa"],
            es_mpa=200_000.0,
            fywk_mpa=b420["fyk_mpa"],
            gamma_c=c30["gamma_c"],
            gamma_s=b420["gamma_s"],
            local_axis_angle_deg=0.0,
            demand_vectors=demands,
            shear_demands=shears,
            policy=policy,
        )
        self.assertEqual(res["status"], "ENGINEER_COLUMN_SELECTED_NOT_PROVEN")
        self.assertEqual(res["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(res["engineering_release"], "NOT_READY")
        sel = res["selected"]
        self.assertIsNotNone(sel)
        self.assertTrue(sel["pmm_satisfied"])
        self.assertLess(sel["pmm_max_utilization"], 1.0)
        self.assertGreater(sel["rho"], 0.01)
        self.assertLessEqual(sel["rho"], 0.04)

        # Φ25 bars require tie >= 25/3 = 8.33 mm -> skips Φ8 and steps up to Φ10/Φ12
        cand25 = res["candidates_by_diameter"]["25"]
        self.assertGreaterEqual(cand25["selected_transverse"]["tie_diameter_mm"], 10)
        tried_8 = next(t for t in cand25["transverse_candidates_tried"] if t["tie_diameter_mm"] == 8)
        self.assertFalse(tried_8["tie_size_ok"])
        self.assertIn(cand25["selected_transverse"]["confinement_label"], ("Φ10/100", "Φ12/100"))
        self.assertIn(cand25["selected_transverse"]["midspan_label"], ("Φ10/150", "Φ12/150"))

        # Compact 450x450 column: Φ25 longitudinal forces skipping Φ8 -> picks Φ10/Φ12 to satisfy Ash & d/3
        compact_res = select_column_rebar(
            t2_mm=450.0, t3_mm=450.0, cover_mm=40.0,
            fck_mpa=c30["fck_mpa"], fcd_mpa=c30["fcd_mpa"], fyd_mpa=b420["fyd_mpa"],
            es_mpa=200_000.0, fywk_mpa=b420["fyk_mpa"],
            gamma_c=c30["gamma_c"], gamma_s=b420["gamma_s"],
            local_axis_angle_deg=0.0,
            demand_vectors=[{"nd_kn": 600.0, "m2_knm": 80.0, "m3_knm": 120.0}],
            shear_demands=[{"nd_kn": 600.0, "v2_kn": 50.0, "v3_kn": 40.0}],
            policy=policy,
        )
        c25_tr = compact_res["candidates_by_diameter"]["25"]["selected_transverse"]
        self.assertGreaterEqual(c25_tr["tie_diameter_mm"], 10)
        self.assertTrue(c25_tr["tie_size_ok"])
        self.assertTrue(c25_tr["ash_satisfied"])

        # Wide face forces extra crosstie legs so a <= 25*phi_w
        cand16 = res["candidates_by_diameter"]["16"]
        self.assertTrue(cand16["selected_transverse"]["crosstie_a_ok"])
        self.assertGreater(max(cand16["selected_transverse"]["legs_v2"], cand16["selected_transverse"]["legs_v3"]), 2)
        self.assertTrue(any("TBDY_7_3_4_1_CONFINEMENT_SPACING" in a for a in cand16["selected_transverse"]["alerts"]))


class RebarSelectionWebCliTests(test_beam_r10_live.BeamR10WebAndReportIntegration):
    def setUp(self):
        self.complete_selection_scope = True
        super().setUp()
        configure_three_cut_forces(self.outputs)

    def capture(self, case, *, column_axial_request=None):
        data = super().capture(case, column_axial_request=column_axial_request)
        if not self.complete_selection_scope or not (column_axial_request or {}).get("pmm_member"):
            return data
        return attach_configured_selection_scope(data)

    def _post_json(self, path: str, body: dict) -> dict:
        req = Request(
            self.url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _run_cli_selection(self, run_id, **policies):
        with TemporaryDirectory() as temp:
            args = ["run-pipeline", "--source", str(self.root / run_id / "input.source"),
                    "--case", "Modal", "--out", str(self.root)]
            for key, value in policies.items():
                if value == "default":
                    argument = value
                else:
                    path = Path(temp) / (key + ".json")
                    path.write_text(json.dumps(value), encoding="utf-8")
                    argument = str(path)
                args.extend(("--" + key.replace("_", "-"), argument))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(args), 0)
            return json.loads(output.getvalue())

    def _sealed_results(self, run_id):
        path = next((self.root / run_id).glob("*-engine-results.json"))
        return json.loads(path.read_bytes())["payload"]["results"]

    def _assert_adapter_parity(self, web_run_id, cli_summary):
        cli_run_id = Path(cli_summary["run_dir"]).name
        self.assertEqual((self.root / web_run_id / "input.source").read_bytes(),
                         (self.root / cli_run_id / "input.source").read_bytes())
        self.assertEqual(self._sealed_results(web_run_id), self._sealed_results(cli_run_id))
        return self._sealed_results(web_run_id)

    def test_web_cli_selection_and_sibling_reapplication_share_full_engineering_results(self):
        base = self.post(self.pmm_query())["run_id"]
        native = (self.root / base / "input.source").read_bytes()
        policies = {"beam_selection": "default", "column_selection": "default"}
        selected = self._post_json("/api/apply-rebar-selection", {"base_run_id": base, **policies})["run_id"]
        cli = self._run_cli_selection(base, **policies)
        results = self._assert_adapter_parity(selected, cli)
        evidence = results["report_evidence"]
        self.assertTrue(evidence["design_dependencies"]["candidate_execution_allowed"])
        self.assertEqual(evidence["design_dependencies"]["selected_candidates"]["rows"][0]["status"],
                         "SAME_RUN_CANDIDATE_BOUND")
        self.assertIsNotNone(evidence["alpha_iteration"])
        selected_raw = (self.root / selected / "input.source").read_bytes()
        self.assertEqual((self.root / selected / "parent.source").read_bytes(), native)
        cli_selected = Path(cli["run_dir"]).name
        unchanged = self._post_json("/api/apply-rebar-selection", {"base_run_id": cli_selected, **policies})["run_id"]
        self._assert_adapter_parity(unchanged, self._run_cli_selection(cli_selected, **policies))
        self.assertEqual((self.root / unchanged / "input.source").read_bytes(), selected_raw)

        changed_policy = {"min_rho": .02, "allowed_longitudinal_diameters_mm": [16, 20]}
        changed = self._post_json("/api/apply-rebar-selection", {
            "base_run_id": cli_selected, "column_selection": changed_policy})["run_id"]
        changed_results = self._assert_adapter_parity(changed,
            self._run_cli_selection(cli_selected, column_selection=changed_policy))
        changed_source = json.loads((self.root / changed / "input.source").read_bytes())
        original_source = json.loads(selected_raw)
        self.assertEqual(changed_source["beam_selection"], original_source["beam_selection"])
        self.assertNotEqual(changed_source["column_selection"], original_source["column_selection"])
        self.assertNotEqual(changed_results["report_evidence"]["design_scenario"]["scenario_sha256"],
                            evidence["design_scenario"]["scenario_sha256"])
        self.assertEqual(changed_source["design_scenario"]["parent_input_sha256"], sha256(native).hexdigest())
        self.assertEqual((self.root / changed / "parent.source").read_bytes(), native)
        self.assertEqual((self.root / selected / "input.source").read_bytes(), selected_raw)
        self.assertEqual((self.root / cli_selected / "input.source").read_bytes(), selected_raw)
        self.assertEqual((self.root / base / "input.source").read_bytes(), native)

    def test_missing_scope_blocks_identically_through_web_and_cli(self):
        self.complete_selection_scope = False
        base = self.post(self.pmm_query())["run_id"]
        policies = {"beam_selection": "default", "column_selection": "default"}
        web = self._post_json("/api/apply-rebar-selection", {"base_run_id": base, **policies})
        results = self._assert_adapter_parity(web["run_id"], self._run_cli_selection(base, **policies))
        evidence = results["report_evidence"]
        self.assertFalse(evidence["design_dependencies"]["candidate_execution_allowed"])
        self.assertEqual(evidence["alpha_iteration"]["status"], "BLOCKED_INPUTS")
        self.assertIsNone(results["r10_live"])
        self.assertEqual(evidence["design_dependencies"]["selected_candidates"]["rows"][0]["status"],
                         "BLOCKED_DEPENDENCY")

    def test_live_selection_also_archives_native_parent_and_uses_scenario_dependencies(self):
        query = self.pmm_query()
        query.update(beam_selection="default", column_selection="default")
        run_id = self.post(query)["run_id"]
        parent = (self.root / run_id / "parent.source").read_bytes()
        self.assertNotIn("beam_selection", json.loads(parent))
        self.assertNotIn("column_selection", json.loads(parent))
        self.assertNotIn("design_scenario", json.loads(parent))
        results = self._sealed_results(run_id)
        self.assertEqual(results["report_evidence"]["design_scenario"]["parent_input_sha256"], sha256(parent).hexdigest())
        self.assertIsNotNone(results["report_evidence"]["design_dependencies"])
        self.assertIsNotNone(results["report_evidence"]["alpha_iteration"])
        self._assert_adapter_parity(run_id, self._run_cli_selection(run_id))

    def test_reapplication_rejects_corrupt_parent_and_unknown_policy_without_new_run(self):
        base = self.post(self.pmm_query())["run_id"]
        with self.assertRaises(HTTPError) as error:
            self._post_json("/api/apply-rebar-selection", {
                "base_run_id": base, "column_selection": {"min_rhoo": .02}})
        self.assertEqual(error.exception.code, 422)
        selected = self._post_json("/api/apply-rebar-selection", {
            "base_run_id": base, "column_selection": "default"})["run_id"]
        before = set(self.root.glob("RUN-*"))
        (self.root / selected / "parent.source").write_bytes(b"{}")
        with self.assertRaises(HTTPError) as error:
            self._post_json("/api/apply-rebar-selection", {
                "base_run_id": selected, "column_selection": "default"})
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(set(self.root.glob("RUN-*")), before)

    def test_live_vs04_apply_endpoint_html_report_cli_and_workspace_ui(self):
        # 1. Live capture with engineer default beam & column policies
        q = self.pmm_query()
        q["beam_selection"] = "default"
        q["column_selection"] = "default"
        ack = self.post(q)
        self.assertTrue(ack["beam_r10"]["engineer_selection_active"])
        self.assertEqual(ack["r10_live"]["engineer_column_selection_status"], "ENGINEER_COLUMN_SELECTED_NOT_PROVEN")

        report = json.loads(self.get("/api/export-checks?run_id=" + ack["run_id"]))
        beam_b1 = next(b for b in report["beam_r10"]["beams"] if b["member_id"] == "B1")
        self.assertEqual(beam_b1["ends"]["I"]["engineer_selection"]["selection_status"], "ENGINEER_REBAR_SELECTED_NOT_PROVEN")
        self.assertEqual(beam_b1["engineer_stirrups"]["confinement"]["label"], "Φ8/100")
        self.assertEqual(beam_b1["engineer_stirrups"]["span"]["label"], "Φ8/150")
        self.assertIn("engineer_selected_scwb", report["r10_live"]["scwb_joints"][0])
        self.assertEqual(
            report["r10_live"]["scwb_joints"][0]["engineer_selected_scwb"]["beam_capacity_role"],
            "ENGINEER_SELECTED_BEAM_REBAR",
        )
        self.assertEqual(report["r10_live"]["engineer_column_selection"]["formal_compliance"], "NOT_PROVEN")

        html = self.get("/report/print?run_id=" + ack["run_id"]).decode("utf-8")
        self.assertIn("Top (cont + ilave)", html)
        self.assertIn("Eng. SCWB ratio", html)
        self.assertIn("Legs V2/V3", html)

        # 2. Apply custom policy via /api/apply-rebar-selection onto baseline run
        custom_beam = {
            **DEFAULT_BEAM_SELECTION_POLICY,
            "allowed_additional_diameters_mm": [12, 14, 16, 20, 22, 24, 25],
        }
        custom_col = {
            **DEFAULT_COLUMN_SELECTION_POLICY,
            "allowed_longitudinal_diameters_mm": [16, 20],
        }
        reapplied = self._post_json("/api/apply-rebar-selection", {
            "base_run_id": ack["run_id"],
            "beam_selection": custom_beam,
            "column_selection": custom_col,
        })
        self.assertNotEqual(reapplied["run_id"], ack["run_id"])
        self.assertTrue(reapplied["beam_r10"]["engineer_selection_active"])
        re_report = json.loads(self.get("/api/export-checks?run_id=" + reapplied["run_id"]))
        self.assertEqual(
            sorted(re_report["r10_live"]["engineer_column_selection"]["candidates_by_diameter"].keys()),
            ["16", "20"],
        )

        # 3. CLI run-pipeline --beam-selection / --column-selection
        with TemporaryDirectory() as out_dir:
            src_file = self.root / ack["run_id"] / "input.source"
            beam_cfg = Path(out_dir) / "beam.json"
            col_cfg = Path(out_dir) / "col.json"
            beam_cfg.write_text(json.dumps(custom_beam), encoding="utf-8")
            col_cfg.write_text(json.dumps(custom_col), encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli_main([
                    "run-pipeline",
                    "--source", str(src_file),
                    "--case", "Modal",
                    "--out", out_dir,
                    "--beam-selection", str(beam_cfg),
                    "--column-selection", str(col_cfg),
                ])
            self.assertEqual(code, 0)
            cli_out = json.loads(buf.getvalue())
            self.assertEqual(cli_out["engineering_release"], "NOT_READY")

        # 4. Workspace UI exposes Rebar & stirrup selection controls
        ws_html = self.get("/").decode("utf-8")
        ws_js = self.get("/workspace.js").decode("utf-8")
        ws_src_js = self.get("/workspace-source.js").decode("utf-8")
        for token in ("settingsRebarTab", "deskRebarSettings", "deskBeamAllowedDiams", "deskColLongDiams", "deskColTieDiams", "deskApplyRebar"):
            self.assertIn(token, ws_html)
        self.assertIn("tbdy:apply-rebar-selection", ws_js)
        self.assertIn("/api/apply-rebar-selection", ws_src_js)


for _name in [n for n in dir(test_beam_r10_live.BeamR10WebAndReportIntegration) if n.startswith("test_")]:
    setattr(RebarSelectionWebCliTests, _name, None)


if __name__ == "__main__":
    unittest.main()
