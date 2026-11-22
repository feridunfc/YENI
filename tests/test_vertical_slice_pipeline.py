"""Normal CLI/Web source-to-report calculations using real production owners.

The public source is synthetic. This verifies an executable bounded reference
slice, not an ETABS solve, original87 replay, spectral design or project approval.
No stage result or engineering capacity is replaced in these integration tests.
"""
from argparse import Namespace
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from hashlib import sha256
from html import unescape
from http.server import ThreadingHTTPServer
import io
import json
import math
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from tbdy_next.engineering.cli_adapter import run_cli
from tbdy_next.engineering.design_scenario import _digest, _source_data
from tbdy_next.engineering.pipeline_snapshot import compare_runs, read_snapshot
from tbdy_next.reporting import build_complete_report, build_printable_html
from tbdy_next.web import make_handler
from vertical_slice_fixture import COMBINATIONS, CUTS, source_and_request


class VerticalSlicePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.raw, cls.request = source_and_request()
        cls.summary, cls.snapshot = cls.calculate(cls.raw, cls.request, "base")
        cls.directory = Path(cls.summary["run_dir"])
        cls.stages = cls.snapshot["results"]

    @classmethod
    def calculate(cls, raw, request, name, **run_options):
        source_path = cls.root / (name + ".source")
        request_path = cls.root / (name + ".json")
        source_path.write_bytes(raw)
        request_path.write_text(json.dumps(request), encoding="utf-8")
        args = Namespace(action="run-pipeline", source=source_path, design_scenario=request_path,
                         out=cls.root, case="Modal", compare_run=None,
                         beam_selection=None, column_selection=None, **run_options)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = run_cli(args)
        if code != 0:
            raise AssertionError(stream.getvalue())
        summary = json.loads(stream.getvalue())
        snapshot = read_snapshot(Path(summary["run_dir"]), input_sha=summary["input_sha256"])
        return summary, snapshot

    def test_actual_source_selection_pdelta_joint_and_r14_close_the_declared_numeric_slice(self):
        stages = self.stages
        scope = stages["report_evidence"]["column_pmm_expected_instances"]
        self.assertTrue(scope["independent_cut_census_proven"])
        self.assertEqual(scope["expected_member_combination_count"], 5)
        self.assertEqual(scope["numerically_complete_signed_pair_count"], 5)
        self.assertEqual({r["combination"] for r in scope["instances"]}, set(COMBINATIONS))
        self.assertEqual(sum(r["configured_cut_coverage"]["matched_count"] for r in scope["instances"]), 15)
        self.assertTrue(all(r["configured_cut_coverage"]["exact_cut_census"] for r in scope["instances"]))
        r10 = stages["r10_live"]["per_member"]["C1"]
        selected = r10["engineer_column_selection"]["selected"]
        self.assertEqual((selected["bar_count"], selected["diameter_mm"]), (32, 16))
        self.assertAlmostEqual(selected["area_mm2"], 32 * math.pi * 16 ** 2 / 4, places=8)
        self.assertGreaterEqual(selected["area_mm2"], .01 * 800 ** 2)
        self.assertEqual(selected["selected_transverse"]["confinement_spacing_mm"], 90)
        self.assertEqual(selected["selected_transverse"]["legs_v2"], 5)
        self.assertTrue(selected["selected_transverse"]["all_tbdy_checks_met"])
        self.assertEqual(stages["beam_r10"]["calculated_beam_count"], 2)
        self.assertEqual(stages["r10_live"]["physical_clear_lengths"]["per_member"]["C1"]["physical_length_m"], 2.5)

        global_result = stages["r08_second_order"]
        self.assertEqual(global_result["evaluated_story_direction_count"], 2)
        for direction, shear in (("X", 25.), ("Y", 20.)):
            self.assertAlmostEqual(float(global_result["direction_results"][direction]["theta_max_candidate"]),
                                   500. * .001 / (shear * 3.))
            self.assertEqual(float(global_result["direction_results"][direction]["beta_ii_candidate"]), 1.)
        local = stages["r08_local_slenderness"]["per_member"]["C1"]
        self.assertEqual(local["second_order_basis_application"]["status"], "ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN")
        mag = local["magnified_selected_pmm"]
        self.assertEqual((mag["expected_row_count"], mag["resolved_row_count"]), (15, 15))
        self.assertLess(mag["max_utilization"], 1.)
        self.assertTrue(all(row["moment_reserve_knm"] > 0 for row in mag["rows"]))
        self.assertEqual({row["object_station_m"] for row in mag["rows"]}, set(CUTS))
        self.assertEqual({row["analysis_element_id"] for row in mag["rows"]}, {"C1-elm"})
        ve = r10["column_transverse_and_shear"]["engineer_capacity_shear_ve"]
        for axis in ("V2", "V3"):
            self.assertLess(ve["axes"][axis]["max_utilization_ts500"], 1.)
            self.assertLess(ve["axes"][axis]["max_utilization_zero_concrete"], 1.)
        roof = next(end for end in r10["member_joint_ends"] if end["end"] == "J")
        for axis in roof["axes"]:
            if axis.get("calculation") is not None:
                self.assertTrue(axis["joint_shear_ve"]["within_geometric_limit"])
                self.assertTrue(axis["joint_transverse_7_5_2_3"]["all_references_met"])

        closure = stages["r14_closure"]
        self.assertEqual((closure["expected_column_count"], closure["numerically_closed_count"],
                          closure["normative_fail_count"], closure["partial_or_unbound_count"]), (1, 1, 0, 0))
        self.assertEqual(closure["columns"][0]["status"], "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES")
        self.assertEqual(closure["engineering_release"], "NOT_READY")
        self.assertTrue(closure["columns"][0]["open_gates"])
        iteration = stages["report_evidence"]["alpha_iteration"]
        self.assertEqual(iteration["status"], "ALTERNATIVE_NOT_REQUIRED")
        self.assertEqual(iteration["iteration_count"], 0)
        self.assertFalse(iteration["feedback_consumed"])
        # A roof exclusion is not an interior-joint SCWB numerical validation.
        applicability = iteration["final_qualification"]["story_applicability"]
        self.assertEqual({row["direction"] for row in applicability}, {"X", "Y"})

    def test_adopted_k_and_creep_revision_changes_actual_r08_and_sealed_results(self):
        raw, request = source_and_request(k=2., rm=1.)
        self.assertEqual(raw, self.raw)
        summary, snapshot = self.calculate(raw, request, "changed-basis")
        changed = snapshot["results"]
        before = self.stages["r08_local_slenderness"]["per_member"]["C1"]
        after = changed["r08_local_slenderness"]["per_member"]["C1"]
        self.assertEqual(before["second_order_basis_application"]["source_data_sha256"],
                         after["second_order_basis_application"]["source_data_sha256"])
        self.assertEqual(before["second_order_basis_application"]["selected_cage_sha256"],
                         after["second_order_basis_application"]["selected_cage_sha256"])
        self.assertNotEqual(before["second_order_basis_application"]["basis_sha256"],
                            after["second_order_basis_application"]["basis_sha256"])
        for axis in ("M2", "M3"):
            old = before["stiffness_and_euler"][axis]
            new = after["stiffness_and_euler"][axis]
            # Independent parameter scaling: doubling k divides Nk by4;
            # Rm0->1 halves adopted EI, so the combined Nk ratio is1/8.
            self.assertAlmostEqual(new["selected_nk_kn"] / old["selected_nk_kn"], 1 / 8)
        self.assertGreater(after["magnified_selected_pmm"]["max_utilization"], before["magnified_selected_pmm"]["max_utilization"])
        self.assertEqual(changed["r14_closure"]["numerically_closed_count"], 1)
        self.assertNotEqual(compare_runs(self.directory, Path(summary["run_dir"]))["status"], "IDENTICAL")
        self.assertEqual((Path(summary["run_dir"]) / "parent.source").read_bytes(), self.raw)

    def test_normal_web_scenario_matches_cli_and_report_opening_calls_no_calculation(self):
        def no_capture(*args, **kwargs):
            raise AssertionError("Offline design must not acquire an ETABS session")
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.root, live_capture=no_capture))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = "http://127.0.0.1:" + str(server.server_port)
            body = json.dumps({"base_run_id": self.directory.name, "design_scenario": self.request}).encode()
            with urlopen(Request(url + "/api/apply-rebar-selection", data=body,
                                 headers={"Content-Type": "application/json"}), timeout=30) as response:
                acknowledgement = json.load(response)
            web_directory = self.root / acknowledgement["run_id"]
            self.assertEqual(compare_runs(self.directory, web_directory)["status"], "IDENTICAL")
            owners = (
                "tbdy_next.engineering.pipeline.EnginePipelineRunner.run",
                "tbdy_next.engineering.column_r08_local_live.project_column_r08_local_live",
                "tbdy_next.engineering.column_r10_live.project_column_r10_live",
                "tbdy_next.engineering.beam_r10_live.project_beam_r10_live",
                "tbdy_next.engineering.column_r14_closure.project_column_r14_and_r15_closure",
                "tbdy_next.engineering.rebar_selection.select_column_rebar",
            )
            with ExitStack() as stack:
                spies = [stack.enter_context(patch(owner, side_effect=AssertionError("Report-time calculation"))) for owner in owners]
                report = build_complete_report(self.root, web_directory.name)
                html = build_printable_html(report)
                with urlopen(url + "/api/export-checks?run_id=" + web_directory.name, timeout=8) as response:
                    web_report = json.load(response)
                with urlopen(url + "/report/print?run_id=" + web_directory.name, timeout=8) as response:
                    web_html = response.read().decode()
            self.assertTrue(all(spy.call_count == 0 for spy in spies))
            self.assertEqual(report, web_report)
            self.assertEqual(html, web_html)
            self.assertIn("32Φ16", html)
            self.assertIn("R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES", html)
            self.assertIn("Second order · Adopted calculation basis", html)
            adopted = html.split("Second order · Adopted calculation basis", 1)[1].split("</section>", 1)[0]
            self.assertIn("K used", adopted)
            self.assertIn("Rm used", adopted)
            rows = [[unescape(re.sub(r"<[^>]+>", "", cell)).strip()
                     for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
                    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", adopted, re.S)]
            basis_rows = [row for row in rows if len(row) > 4 and row[0] == "C1" and row[1] in ("M2", "M3")]
            self.assertEqual({row[1] for row in basis_rows}, {"M2", "M3"})
            for row in basis_rows:
                actual = report["r08_local_slenderness"]["per_member"]["C1"]["stiffness_and_euler"][row[1]]
                self.assertEqual(float(row[3]), actual["effective_length_factor_k"])
                self.assertEqual(float(row[4]), actual["reference_creep_ratio_rm"])
                self.assertEqual((float(row[3]), float(row[4])), (1., 0.))
            self.assertEqual(report["r14_closure"], self.stages["r14_closure"])
        finally:
            server.shutdown()
            thread.join(3)
            server.server_close()

    def test_missing_native_cut_stays_in_scope_and_cannot_close(self):
        source = json.loads(self.raw)
        rowset = source["column_axial"]["force_source"]["rowsets"]["C1"]
        for value in rowset.values():
            if isinstance(value, list):
                value.pop()
        rowset["NumberResults"] -= 1
        raw = json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        request = deepcopy(self.request)
        request["parent_input_sha256"] = sha256(raw).hexdigest()
        for key in ("analysis_basis", "second_order_basis"):
            request[key]["source_data_sha256"] = _digest(_source_data(source))
        _, snapshot = self.calculate(raw, request, "missing-cut")
        stages = snapshot["results"]
        scope = stages["report_evidence"]["column_pmm_expected_instances"]
        self.assertEqual(scope["expected_member_combination_count"], 5)
        self.assertFalse(scope["independent_cut_census_proven"])
        self.assertEqual(scope["numerically_complete_signed_pair_count"], 4)
        self.assertEqual(stages["r14_closure"]["numerically_closed_count"], 0)
        self.assertEqual(stages["r14_closure"]["engineering_release"], "NOT_READY")

    def test_actual_two_story_joint_capacity_and_transverse_design_trial(self):
        raw, request = source_and_request(two_story=True, column_tie_diameter=10, column_tie_spacing=90)
        _, trial = self.calculate(raw, request, "two-story-phi10")
        self.assertEqual(trial["results"]["r14_closure"]["numerically_closed_count"], 0)
        self.assertTrue(all("COLUMN_ZERO_CONCRETE_BRANCH_REVIEW_REQUIRED:V2" in row["open_gates"]
                            for row in trial["results"]["r14_closure"]["columns"]))
        adopted_raw, adopted_request = source_and_request(two_story=True)
        self.assertEqual(adopted_raw, raw)
        _, adopted = self.calculate(adopted_raw, adopted_request, "two-story-phi12-70")
        stages = adopted["results"]
        self.assertEqual(stages["r14_closure"]["numerically_closed_count"], 2)
        self.assertEqual(stages["r14_closure"]["normative_fail_count"], 0)
        scope = stages["report_evidence"]["column_pmm_expected_instances"]
        self.assertEqual(scope["expected_member_combination_count"], 10)
        self.assertTrue(scope["independent_cut_census_proven"])
        self.assertEqual(sum(row["configured_cut_coverage"]["matched_count"] for row in scope["instances"]), 30)
        self.assertEqual(stages["beam_r10"]["calculated_beam_count"], 4)
        lower = stages["r10_live"]["per_member"]["C1"]
        joints = [joint for joint in lower["scwb_joints"] if joint["joint_id"] == "P1"]
        self.assertEqual({joint["direction"] for joint in joints}, {"X", "Y"})
        for joint in joints:
            result = joint["seismic_axial_interval_check"]
            self.assertEqual(result["status"], "SCWB_EQ_7_3_INTERVAL_SUFFICIENT")
            self.assertEqual((result["expected_checks"], result["evaluated_checks"]), (8, 8))
            self.assertGreater(result["minimum_ratio_lower"], 1.)
            for case in result["cases"]:
                self.assertEqual(set(case["columns"]), {"C1", "C2"})
                self.assertEqual(case["columns"]["C1"]["nd_interval_kn"], [2500., 2500.])
                self.assertEqual(case["columns"]["C2"]["nd_interval_kn"], [1500., 1500.])
                for sway in case["sways"]:
                    self.assertAlmostEqual(sway["ratio_lower"],
                                           sway["column_sum_lower_knm"] / sway["required_sum_upper_knm"])
        # Both real section owners have contributed at the interior joint;
        # the roof disposition does not supply this numerical inequality.
        iteration = stages["report_evidence"]["alpha_iteration"]
        self.assertEqual(iteration["status"], "ALTERNATIVE_NOT_REQUIRED")
        dispositions = [end["disposition"] for row in iteration["final_qualification"]["story_applicability"]
                        for end in row["ends"] if end["joint_id"] == "P1"]
        self.assertEqual(dispositions, ["EQ_7_3_INTERVAL_SUFFICIENT"] * 4)
        self.assertEqual(stages["r14_closure"]["engineering_release"], "NOT_READY")

    def test_building_run_keeps_beams_and_writes_report_when_column_basis_is_missing(self):
        request = deepcopy(self.request)
        request.pop("second_order_basis", None)
        request.pop("analysis_archive", None)
        summary, snapshot = self.calculate(self.raw, request, "building", whole_building=True)
        building = snapshot["results"]["report_evidence"]["building_design"]
        self.assertEqual(building["column_count"], 1)
        self.assertEqual(building["column_status_counts"], {"hold": 1})
        self.assertEqual(building["beam_count"], 2)
        beams = snapshot["results"]["beam_r10"]["beams"]
        self.assertEqual(len(beams), 2)
        self.assertTrue(all("selected_design" in b and b["engineer_shear_ve"]["scenario_ve_kn"] > 0 for b in beams))
        page = Path(summary["report_path"]).read_text(encoding="utf-8")
        self.assertIn("Whole-building calculation", page)
        self.assertIn(snapshot["results_sha256"], page)

    def test_selected_beam_checks_full_shear_and_preserves_exceedance_with_another_zone_missing(self):
        from tbdy_next.engineering.beam_r10_live import _selected_beam_design
        beam = deepcopy(self.stages["beam_r10"]["beams"][0])
        shear = beam["engineer_shear_ve"]
        shear["ts500_max_shear_vr_max_kn"] = (shear["scenario_ve_kn"] + shear["earthquake_capacity_shear_term_kn"]) / 2
        beam["engineer_stirrups"].pop("span")
        result = _selected_beam_design(beam)
        self.assertEqual(result["status"], "NUMERICAL_EXCEEDANCE")
        self.assertIn("CAPACITY_SHEAR_EXCEEDS:WEB", result["failures"])
        self.assertIn("RESISTANCE_UNAVAILABLE:SPAN", result["missing"])

    def test_real_magnified_demand_reselects_cage_without_alpha_or_native_force_change(self):
        # A declared numerical stress example, not a verified restraint model:
        # K=5/Rm=1 deliberately tests the adopted-input calculation consumer.
        raw, request = source_and_request(k=5., rm=1., column_tie_diameter=12, column_tie_spacing=70)
        source = json.loads(raw)
        native = source["column_axial"]["force_source"]
        native["rowsets"]["C1"]["M3"] = [value + 870. for value in native["rowsets"]["C1"]["M3"]]
        raw = json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        request["parent_input_sha256"] = sha256(raw).hexdigest()
        for key in ("analysis_basis", "second_order_basis"):
            request[key]["source_data_sha256"] = _digest(_source_data(source))
        first_order_request = deepcopy(request)
        for axis in first_order_request["second_order_basis"]["members"]["C1"]["axes"].values():
            axis.update(k=1., creep_ratio_rm=0.)
        initial_summary, initial = self.calculate(raw, first_order_request, "stress-initial")
        initial_r10 = initial["results"]["r10_live"]["per_member"]["C1"]
        self.assertEqual(initial_r10["engineer_column_selection"]["selected"]["label"], "32Φ16")
        self.assertEqual(initial["results"]["report_evidence"]["alpha_iteration"]["iteration_count"], 0)

        summary, rebuilt = self.calculate(raw, request, "stress-reselected")
        stages = rebuilt["results"]
        selected = stages["r10_live"]["per_member"]["C1"]["engineer_column_selection"]["selected"]
        self.assertEqual(selected["label"], "34Φ16")
        iteration = stages["report_evidence"]["alpha_iteration"]
        self.assertEqual(iteration["status"], "ALTERNATIVE_NOT_REQUIRED")
        self.assertEqual(iteration["iteration_count"], 1)
        self.assertFalse(iteration["feedback_consumed"])
        self.assertEqual(iteration["final_demand_revision"]["factors"], {})
        trace = iteration["trace"][0]
        self.assertEqual(trace["mode"], "NATIVE_DEMAND_DESIGN_RESELECTION")
        self.assertEqual(trace["changed_member_ids"], ["C1"])
        self.assertEqual(trace["actions"]["second_order_constraint_count"], 15)
        self.assertEqual(trace["actions"]["joint_consumer_member_ids"], ["C1"])
        self.assertFalse(trace["actions"]["beam_owner_reexecuted"])
        local = stages["r08_local_slenderness"]["per_member"]["C1"]
        self.assertLess(local["magnified_selected_pmm"]["max_utilization"], 1.)
        self.assertGreater(local["magnified_selected_pmm"]["max_utilization"], .98)
        self.assertEqual((local["magnified_selected_pmm"]["expected_row_count"],
                          local["magnified_selected_pmm"]["resolved_row_count"]), (15, 15))
        for run in (initial_summary, summary):
            directory = Path(run["run_dir"])
            self.assertEqual((directory / "parent.source").read_bytes(), raw)
            recorded = json.loads((directory / "input.source").read_bytes())
            self.assertEqual(recorded["column_axial"]["force_source"], native)
        self.assertEqual(stages["r14_closure"]["numerically_closed_count"], 1)
        self.assertEqual(stages["r14_closure"]["engineering_release"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
