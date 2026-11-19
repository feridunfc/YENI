"""Tests for R08-Local TS 500 live slenderness/magnification projection and EnginePipelineRunner."""
from __future__ import annotations

import json
import math
import unittest
from unittest.mock import patch

from tbdy_next.column_engine.section_capacity import Material, Section, perimeter, solver
from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
from tbdy_next.engineering.column_r10_live import SelectedColumnCage
from tbdy_next.engineering.pipeline import EnginePipelineRunner, STAGES
import test_column_axial_live as live
from test_column_axial_live import SPECTRAL, STATIC
from test_r03_analysis_setup import capture_table
from test_r10_live import _pmm_sec_source


def _r08_local_fixture():
    col_conn = capture_table(
        "Column Object Connectivity",
        ["UniqueName", "Story", "UniquePtI", "UniquePtJ", "Length"],
        [("127", "+4.50", "1044", "412", "4.5")],
    )
    col_conn["field_metadata"]["units_by_field"]["Length"] = "m"
    payload = {
        "source_mode": "LIVE_ETABS",
        "geometry_capture": {
            "present_units": 6,
            "present_units_after": 6,
            "unit_state_unchanged": True,
            "tables": {
                "FRAME_ASSIGNMENTS": capture_table(
                    "Frame Assignments - Summary",
                    ["UniqueName", "Label", "Story", "AnalysisSect"],
                    [("127", "C88", "+4.50", "Column_80x80")],
                ),
                "COLUMN_CONNECTIVITY": col_conn,
            },
        },
        "column_axial": {
            "request": {"check": "column-pmm", "member": "127", "pmm_member": "127"},
            "force_source": {
                "units_code": 6,
                "rowsets": {"127": {"ObjSta": [0.0, 1.9, 3.8]}},
            },
            "pmm_section_source": _pmm_sec_source(),
            "design_preferences": capture_table("Concrete Frame Design Preferences - TS 500-2000(R2018)",
                                                ["GammaC", "GammaS"], [("1.5", "1.15")]),
        },
    }
    geometry = {
        "checks": [{"check_id": "column_rect_min", "status": "EVALUATED", "items": [{
            "element_id": "127", "label": "C88", "story": "+4.50",
            "section": "Column_80x80", "analysis_section": "Column_80x80",
            "section_design_difference": False, "material_classification": "RESOLVED_CONCRETE_USAGE",
            "material_name": "C35/45", "width_mm": 800.0, "depth_mm": 800.0,
        }]}]
    }
    axial = {"status": "NUMERICAL_COMPLETE", "columns": [{
        "element_id": "127", "section": "Column_80x80", "material_name": "C35/45",
        "fck_mpa": 35.0, "fcd_mpa": 35.0 / 1.5,
    }]}
    pmm = {
        "member_id": "127", "story": "+4.50", "section": "Column_80x80", "analysis_order": "UNVERIFIED",
        "rows": [
            {"combination": STATIC, "object_station_m": 0.0, "nd_kn": 1200.0, "m2_knm": 40.0, "m3_knm": -60.0},
            {"combination": STATIC, "object_station_m": 3.8, "nd_kn": 1000.0, "m2_knm": -20.0, "m3_knm": 30.0},
        ],
        "section_evidence": {
            "native_t2_mm": 800.0, "native_t3_mm": 800.0, "fck_mpa": 35.0, "es_mpa": 200000.0,
        },
    }
    return payload, geometry, axial, pmm


class R08LocalUnitTests(unittest.TestCase):
    def test_runner_integrates_compiled_dag_and_r08_local_stage(self):
        runner = EnginePipelineRunner()
        cov = runner.coverage()
        self.assertEqual(cov["unknown_node_ids"], [])
        self.assertIn("column-r08-local", {s.key for s in STAGES})
        self.assertIn("column-r08-local", cov["bindings"]["COLUMN_SLENDERNESS"])

    def test_project_column_r08_local_live_computes_ts500_scenarios_without_pass(self):
        payload, geometry, axial, pmm = _r08_local_fixture()
        res = project_column_r08_local_live(payload, geometry, axial, pmm, {"status": "NUMERIC_PRECHECK_UNAPPROVED"})
        self.assertEqual(res["status"], "REFERENCE_SLENDERNESS_CALCULATED")
        self.assertEqual(res["observed_reduced_span_mm"], 3800.0)
        self.assertEqual(res["frame_length_mm"], 4500.0)
        self.assertEqual(res["span_basis"], "OBSERVED_REDUCED_OUTPUT_SPAN_NOT_PHYSICAL_LN")
        self.assertGreater(res["stiffness_and_euler"]["M2"]["preferred_nk_kn"], 0.0)
        self.assertEqual(res["stiffness_and_euler"]["M2"]["ei_method_basis"], "TS500_7_20_WITH_RM_0_REFERENCE")
        self.assertEqual(len(res["combination_scenarios"]), 1)
        m2 = res["combination_scenarios"][0]["axes"]["M2"]
        self.assertAlmostEqual(m2["signed_end_moment_ratio"], -0.5, places=6)
        self.assertGreaterEqual(m2["magnification_sway_prevented_k1"]["beta"], 1.0)
        self.assertEqual(res["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(res["engineering_release"], "NOT_READY")
        self.assertIn("PHYSICAL_SUPPORT_FACES_AND_CLEAR_LENGTH_NOT_PROVEN", res["open_gates"])

    def test_pipeline_r08_uses_the_r10_section_or_records_a_blocker(self):
        source, geometry, axial, pmm = _r08_local_fixture()
        source["column_selection"] = {}
        pmm["expected_station_count"] = 2
        bars, _, _ = perimeter(800, 800, 40, 10, 25, n2=4, n3=4)
        section = Section(800, 800, bars, Material(35, 35 / 1.5, 420 / 1.15))
        selection = {"member_id": "127", "selected": {"label": "12Ø25"}}
        r10 = {"member_id": "127", "engineer_column_selection": selection}
        cages = {"127": SelectedColumnCage(selection, section)}

        with patch("tbdy_next.engineering.column_r10_live._evaluate_engineer_column_selection",
                   side_effect=AssertionError("R08 must reuse the R10 section")), patch(
                       "tbdy_next.engineering.column_r08_local_live.solver", wraps=solver,
                   ) as assess:
            bound = project_column_r08_local_live(source, geometry, axial, pmm, r10_live=r10, selected_cages=cages)
            self.assertIs(assess.call_args.args[0], section)
            result = bound["magnified_selected_pmm"]
            self.assertEqual(result["resolved_row_count"], 2)
            station = result["governing_station"]
            self.assertEqual(station, max(result["rows"], key=lambda item: item["utilization"]))
            moment = math.hypot(station["magnified_m2_design_knm"], station["magnified_m3_design_knm"])
            self.assertAlmostEqual(moment, station["moment_demand_knm"])
            self.assertAlmostEqual(moment / station["radial_capacity_knm"], result["max_utilization"])
            self.assertAlmostEqual(station["moment_reserve_knm"], station["radial_capacity_knm"] - moment)
            assess.reset_mock()
            # A fresh run that failed to produce a candidate cannot use an old receipt or section.
            unbound = project_column_r08_local_live(source, geometry, axial, pmm, r10_live=r10, selected_cages={})
            assess.assert_not_called()
        self.assertIn("SAME_RUN_SELECTED_COLUMN_CAGE_UNAVAILABLE", unbound["open_gates"])
        self.assertNotIn("magnified_selected_pmm", unbound)

    def test_static_reserve_requires_resolved_bending_and_complete_governing_coverage(self):
        source, geometry, axial, pmm = _r08_local_fixture()
        source["column_selection"] = {}
        pmm["expected_station_count"] = 2
        bars, _, _ = perimeter(800, 800, 40, 10, 25, n2=4, n3=4)
        section = Section(800, 800, bars, Material(35, 35 / 1.5, 420 / 1.15))
        selection = {"member_id": "127", "selected": {"label": "12Ø25"}}
        valid = {"status": "EXCEEDS_SCENARIO_SURFACE", "utilization": 2.0, "radial_capacity_kNm": 10.0}
        for other in (
            {"status": "NUMERIC_UNRESOLVED", "trial_utilization": 1.0, "radial_capacity_kNm": 50.0},
            {"status": "OUTSIDE_SCENARIO_AXIAL_RANGE"},
            {"status": "AXIAL_ONLY_SCENARIO", "axial_utilization": 0.3},
        ):
            with self.subTest(status=other["status"]), patch("tbdy_next.engineering.column_r08_local_live.solver") as factory:
                factory.return_value.assess.side_effect = [valid, other]
                result = project_column_r08_local_live(
                    source, geometry, axial, pmm, r10_live={"member_id": "127", "engineer_column_selection": selection},
                    selected_cages={"127": SelectedColumnCage(selection, section)},
                )["magnified_selected_pmm"]
                first, second = result["rows"]
                self.assertLess(first["moment_reserve_knm"], 0)
                self.assertIsNone(second["radial_capacity_knm"])
                self.assertIsNone(second["moment_reserve_knm"])
                self.assertEqual(result["governing_station"], first if other["status"] == "AXIAL_ONLY_SCENARIO" else None)


class R08LocalWebIntegration(live.ColumnAxialIntegration):
    def capture(self, case, *, column_axial_request=None):
        data = super().capture(case, column_axial_request=column_axial_request)
        conn = data["geometry_capture"]["tables"]["COLUMN_CONNECTIVITY"]
        conn["fields"] += ["UniquePtI", "UniquePtJ", "Length"]
        conn["field_metadata"]["field_keys"] += ["UniquePtI", "UniquePtJ", "Length"]
        conn["field_metadata"]["units_by_field"].update({"UniquePtI": "", "UniquePtJ": "", "Length": "m"})
        for idx, row in enumerate(conn["rows"]):
            row["UniquePtI"], row["UniquePtJ"], row["Length"] = f"PI{idx}", f"PJ{idx}", "3.8"
        return data

    def test_r08_local_reaches_web_ack_export_and_html_report(self):
        query = self.query("ASSIGNED_DESIGN")
        query.update(check="column-pmm", member="C1",
                     assignments=json.dumps({"gravity": [STATIC], "ductile": [SPECTRAL]}))
        ack = self.post(query)
        run_id = ack["run_id"]
        self.assertEqual(ack["r08_local_slenderness"]["member_id"], "C1")
        self.assertEqual(ack["r08_local_slenderness"]["status"], "REFERENCE_SLENDERNESS_CALCULATED")
        self.assertEqual(ack["r08_local_slenderness"]["formal_compliance"], "NOT_PROVEN")

        report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
        self.assertEqual(report["r08_local_slenderness"]["status"], "REFERENCE_SLENDERNESS_CALCULATED")
        html = self.get("/report/print?run_id=" + run_id).decode("utf-8")
        self.assertIn("Beta ref (no-sway)", html)


for _name in [n for n in dir(live.ColumnAxialIntegration) if n.startswith("test_")]:
    setattr(R08LocalWebIntegration, _name, None)


if __name__ == "__main__":
    unittest.main()
