"""Tests for live beam capacity (CHK-131..136, multi-row CHK-132), SCWB sum Mrb and column Ve (CHK-126)."""
from __future__ import annotations

import json
import math
import unittest

from tbdy_next.engineering.beam_r10_live import project_beam_r10_live
from tbdy_next.engineering.column_r10_live import (
    BEAM_DESIGN_SUMMARY,
    BEAM_REINFORCING,
    END_OFFSETS,
    RELEASES,
    project_column_r10_live,
)
from tbdy_next.engineering.pipeline import EnginePipelineRunner, STAGES
import test_column_axial_live as live
from test_r03_analysis_setup import capture_table
from test_r10_live import R10WebAndReportIntegration, _add_field


def _beam_table(key: str, cols: list[str], rows: list[tuple], units: dict[str, str] | None = None) -> dict:
    tbl = capture_table(key, cols, rows)
    if units:
        tbl["field_metadata"]["units_by_field"].update(units)
    return tbl


def _attach_r10_beam_sources(data: dict) -> dict:
    """Attach unit-verified R10 beam reinforcing, end offsets, releases and design summary to live fixture."""
    tables = data["geometry_capture"]["tables"]
    _add_field(tables["BEAM_CONNECTIVITY"], "Length")
    for row in tables["BEAM_CONNECTIVITY"]["rows"]:
        row["Length"] = "5.0"
    tables["BEAM_CONNECTIVITY"]["field_metadata"]["units_by_field"]["Length"] = "m"
    _add_field(tables["COLUMN_CONNECTIVITY"], "Length")
    for row in tables["COLUMN_CONNECTIVITY"]["rows"]:
        row["Length"] = "3.0"
    tables["COLUMN_CONNECTIVITY"]["field_metadata"]["units_by_field"]["Length"] = "m"

    reinf = _beam_table(
        BEAM_REINFORCING,
        ["Name", "RebarMatL", "RebarMatC", "CoverTop", "CoverBot", "TopLeftArea", "TopRightArea", "BotLeftArea", "BotRightArea"],
        [
            ("B30", "B420C", "B420C", "0.05", "0.05", "0.0010", "0.0010", "0.0007", "0.0007"),
            ("B24", "B420C", "B420C", "0.05", "0.05", "0.0", "0.0", "0.0", "0.0"),
        ],
        {
            "CoverTop": "m", "CoverBot": "m",
            "TopLeftArea": "m2", "TopRightArea": "m2", "BotLeftArea": "m2", "BotRightArea": "m2",
        },
    )
    offsets = _beam_table(
        END_OFFSETS,
        ["UniqueName", "LengthI", "LengthJ"],
        [("C1", "0.0", "0.25"), ("B1", "0.20", "0.20"), ("B2", "0.20", "0.20")],
        {"LengthI": "m", "LengthJ": "m"},
    )
    releases = _beam_table(
        RELEASES,
        ["UniqueName", "M2I", "M3I", "M2J", "M3J"],
        [("B1", "No", "No", "No", "No"), ("B2", "No", "No", "No", "No")],
    )
    # B1 (b=300 mm, h=500 mm) at I=0.20 m needs 1800 mm2 top -> 6Φ20 -> forces TWO_ROW (CHK-132)!
    # B2 (b=240 mm, h=900 mm) needs 900 mm2 top -> 3Φ20 -> TWO_ROW (max 2 per row in b=240!)
    summary = _beam_table(
        BEAM_DESIGN_SUMMARY,
        ["Story", "Label", "UniqueName", "DesignSect", "Station", "Status",
         "AsTopCombo", "AsMinTop", "AsTop", "AsBotCombo", "AsMinBot", "AsBot",
         "TLngCombo", "TLngRebar", "totTopRebar", "totBotRebar", "WarnMsg", "ErrMsg"],
        [
            ("S1", "B1", "B1", "B30", "0.20", "No Message", "C1", "0.0005", "0.0018", "C1", "0.0004", "0.0009", "C1", "0.0", "0.0018", "0.0009", "No Message", "No Message"),
            ("S1", "B1", "B1", "B30", "4.80", "No Message", "C1", "0.0005", "0.0015", "C1", "0.0004", "0.0009", "C1", "0.0", "0.0015", "0.0009", "No Message", "No Message"),
            ("S1", "B2", "B2", "B24", "0.20", "No Message", "C1", "0.0006", "0.0009", "C1", "0.0004", "0.0006", "C1", "0.0", "0.0009", "0.0006", "No Message", "No Message"),
            ("S1", "B2", "B2", "B24", "4.80", "No Message", "C1", "0.0006", "0.0009", "C1", "0.0004", "0.0006", "C1", "0.0", "0.0009", "0.0006", "No Message", "No Message"),
        ],
        {
            "Station": "m",
            "AsMinTop": "m2", "AsTop": "m2", "AsMinBot": "m2", "AsBot": "m2",
            "TLngRebar": "m2", "totTopRebar": "m2", "totBotRebar": "m2",
        },
    )
    data["column_axial"]["r10_source"] = {
        "schema": "tbdy.next.r10-live-source.v1",
        "model_locked_before": True,
        "model_locked_after": True,
        "units_before": 6,
        "units_after": 6,
        "table_reads": {
            BEAM_REINFORCING: reinf,
            END_OFFSETS: offsets,
            RELEASES: releases,
            BEAM_DESIGN_SUMMARY: summary,
        },
        "table_errors": {},
    }
    return data


class BeamR10UnitTests(unittest.TestCase):
    def test_beam_stage_is_bound_to_all_four_beam_dag_nodes(self):
        runner = EnginePipelineRunner()
        cov = runner.coverage()
        self.assertEqual(cov["unknown_node_ids"], [])
        self.assertIn("beam-r10-live", {s.key for s in STAGES})
        for node in ("BEAM_DEMAND", "BEAM_FLEXURE", "BEAM_REBAR", "BEAM_SHEAR"):
            self.assertIn("beam-r10-live", cov["bindings"][node])


class BeamR10WebAndReportIntegration(R10WebAndReportIntegration):
    def capture(self, case, *, column_axial_request=None):
        data = super().capture(case, column_axial_request=column_axial_request)
        if column_axial_request and column_axial_request.get("pmm_member"):
            _attach_r10_beam_sources(data)
        return data

    def test_beam_unit_validation_and_multi_row_chk132_capacity_and_ve(self):
        ack = self.post(self.pmm_query())
        report = json.loads(self.get("/api/export-checks?run_id=" + ack["run_id"]))
        beam_r10 = report["beam_r10"]
        self.assertEqual(beam_r10["status"], "BEAM_CANDIDATE_SCENARIOS_CALCULATED_NOT_PROVEN")
        self.assertEqual(beam_r10["beam_count"], 2)
        self.assertEqual(beam_r10["calculated_beam_count"], 2)
        b1 = next(b for b in beam_r10["beams"] if b["member_id"] == "B1")
        cand_i_20 = b1["ends"]["I"]["candidates"]["20"]
        self.assertEqual(cand_i_20["check_id"], "CHK-132")
        self.assertEqual(cand_i_20["layout_mode"], "TWO_ROW")
        self.assertGreater(sum(cand_i_20["top_row_counts"]), 4)
        self.assertTrue(cand_i_20["chk133_bounds_reference_met"])
        self.assertGreater(cand_i_20["capacity"]["positive_m3_knm"], 0.0)
        self.assertLess(cand_i_20["capacity"]["negative_m3_knm"], 0.0)
        # Override areas on B30 evaluated only as OVERRIDE_SCENARIO_ONLY, never selected design
        ov_i = b1["ends"]["I"]["override_scenario"]
        self.assertIsNotNone(ov_i)
        self.assertFalse(ov_i["selected_design"])
        self.assertEqual(ov_i["origin"], "ETABS_SECTION_OVERRIDE_SCENARIO_ONLY")
        # Beam Ve moment-pair term (no beam static V_dy in force_source)
        self.assertEqual(b1["clear_span_mm"], 4600.0)
        self.assertGreater(b1["shear_ve"]["earthquake_capacity_shear_term_kn"], 0.0)
        self.assertGreater(b1["shear_ve"]["ts500_max_shear_vr_max_kn"], 0.0)
        self.assertEqual(b1["shear_ve"]["status"], "MOMENT_PAIR_SHEAR_TERM_ONLY_VDY_NOT_CAPTURED")
        self.assertEqual(beam_r10["formal_compliance"], "NOT_PROVEN")

    def test_live_vs04_pipeline_export_and_html_report_include_beam_scwb_and_col_ve(self):
        ack = self.post(self.pmm_query())
        run_id = ack["run_id"]
        self.assertEqual(ack["beam_r10"]["calculated_beam_count"], 2)
        self.assertEqual(ack["beam_r10"]["formal_compliance"], "NOT_PROVEN")

        report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
        r10 = report["r10_live"]
        scwb = r10["scwb_joints"]
        self.assertEqual(len(scwb), 2)
        for j in scwb:
            self.assertEqual(j["status"], "SCENARIO_SCWB_EVALUATED_NOT_PROVEN")
            self.assertEqual(j["beam_capacity_role"], "CANDIDATE_SCENARIO_PHI20_N0")
            self.assertGreater(j["sampled_minimum_beam_sum_knm"], 0.0)
            self.assertGreater(j["sampled_minimum_normalized_ratio"], 0.0)
            self.assertEqual(sorted(j["diameter_scenarios"]), ["16", "20", "24"])
            self.assertEqual({c["rotation_sign"] for c in j["cases"]}, {-1, 1})
            self.assertIsNone(j["scwb_ratio"])
            self.assertEqual(j["formal_compliance"], "NOT_PROVEN")

        ve = r10["column_transverse_and_shear"]["capacity_shear_ve"]
        self.assertIsNotNone(ve)
        self.assertEqual(ve["check_id"], "CHK-126")
        self.assertAlmostEqual(ve["clear_length_m"], 2.75, places=6)
        self.assertEqual(ve["clear_length_basis"], "END_OFFSETS_SUBTRACTED")
        self.assertGreater(ve["axes"]["V2"]["max_ve_scwb_scenario_kn"], 0.0)
        self.assertGreater(ve["axes"]["V3"]["max_ve_scwb_scenario_kn"], 0.0)
        self.assertEqual(r10["column_transverse_and_shear"]["ve_status"], "SCENARIO_VE_CALCULATED_NOT_PROVEN")

        html = self.get("/report/print?run_id=" + run_id).decode("utf-8")
        self.assertIn("Beam R10", html)
        self.assertIn("TWO_ROW", html)
        self.assertIn("Min sum Mrb (kN·m)", html)
        self.assertIn("Min SCWB ratio", html)


for _name in [n for n in dir(live.ColumnAxialIntegration) if n.startswith("test_")]:
    setattr(BeamR10WebAndReportIntegration, _name, None)
setattr(BeamR10WebAndReportIntegration, "test_live_vs04_pipeline_export_and_html_report_include_r10", None)


if __name__ == "__main__":
    unittest.main()
