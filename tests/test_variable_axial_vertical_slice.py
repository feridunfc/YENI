"""Actual production pipeline over explicit variable-N source fixtures.

No calculated stage, resistance, selected cage or closure output is replaced.
The source is generated offline; none of these tests claims original C29 or
live ETABS verification, TS500 applicability or engineering acceptance.
"""
from argparse import Namespace
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from http.server import ThreadingHTTPServer
import io
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from tbdy_next.engineering.cli_adapter import run_cli
from tbdy_next.engineering.pipeline_snapshot import compare_runs, read_snapshot
from tbdy_next.reporting import build_complete_report, build_printable_html
from tbdy_next.web import make_handler
from variable_axial_slice_fixture import (
    COMBINATIONS, CUTS, TOP_COMPRESSION_KN, bind_source, source_and_request,
)


APPLIED = "ADOPTED_AXIAL_IDEALIZATION_APPLIED_NOT_PROVEN"
PENDING = "ADOPTED_AXIAL_IDEALIZATION_ENGINEERING_ACCEPTANCE_PENDING"


class VariableAxialVerticalSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.raw, cls.request = source_and_request()
        cls.summary, cls.snapshot = cls.calculate(cls.raw, cls.request, "self-weight-adopted")
        cls.directory = Path(cls.summary["run_dir"])
        cls.stages = cls.snapshot["results"]
        cls.default_raw, cls.default_request = source_and_request(adopt_axial_idealization=False)
        cls.default_summary, cls.default_snapshot = cls.calculate(
            cls.default_raw, cls.default_request, "self-weight-default")

    @classmethod
    def calculate(cls, raw, request, name):
        source_path, request_path = cls.root / (name + ".source"), cls.root / (name + ".json")
        source_path.write_bytes(raw)
        request_path.write_text(json.dumps(request), encoding="utf-8")
        args = Namespace(action="run-pipeline", source=source_path, design_scenario=request_path,
                         out=cls.root, case="Modal", compare_run=None,
                         beam_selection=None, column_selection=None)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = run_cli(args)
        if code != 0:
            raise AssertionError(stream.getvalue())
        summary = json.loads(stream.getvalue())
        return summary, read_snapshot(Path(summary["run_dir"]), input_sha=summary["input_sha256"])

    def test_same_variable_source_default_blocks_and_explicit_input_method_is_consumed(self):
        self.assertEqual(self.raw, self.default_raw)
        source = json.loads(self.raw)
        self.assertEqual(source["example_context"]["classification"], "CONTRACT_FIXTURE")
        self.assertEqual(source["example_context"]["origin"], "GENERATED_OFFLINE_NOT_ETABS")
        default = self.default_snapshot["results"]
        self.assertEqual(default["r14_closure"]["numerically_closed_count"], 0)
        self.assertEqual(self.stages["r14_closure"]["numerically_closed_count"], 2)
        self.assertEqual(self.stages["r14_closure"]["expected_column_count"], 2)
        scope = self.stages["report_evidence"]["column_pmm_expected_instances"]
        self.assertEqual(scope["expected_member_combination_count"], 10)
        self.assertEqual(scope["numerically_complete_signed_pair_count"], 10)
        self.assertTrue(scope["independent_cut_census_proven"])
        self.assertEqual(sum(r["configured_cut_coverage"]["matched_count"] for r in scope["instances"]), 30)
        for uid, top in TOP_COMPRESSION_KN.items():
            old = default["r08_local_slenderness"]["per_member"][uid]
            self.assertIn("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED", old["open_gates"])
            self.assertEqual(old["gravity_axial_balance"]["combinations"]["G"]["status"],
                             "SELF_WEIGHT_BALANCED_AT_SIGNED_CUTS")
            local = self.stages["r08_local_slenderness"]["per_member"][uid]
            evidence, applied = local["axial_idealization_evidence"], local["axial_idealization_application"]
            self.assertEqual(evidence["status"], "SELF_WEIGHT_NMAX_INPUTS_ELIGIBLE")
            self.assertEqual(applied["status"], APPLIED)
            self.assertEqual(set(applied["combinations"]), set(COMBINATIONS))
            self.assertIn(PENDING, local["open_gates"])
            self.assertNotIn("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED", local["open_gates"])
            for record in (evidence, applied):
                self.assertFalse(record["original_constant_axial_clause_satisfied"])
                self.assertFalse(record["conservative_bound_proven"])
                self.assertEqual(record["engineering_approval"], "NOT_GRANTED")
            for name, case in evidence["combinations"].items():
                self.assertEqual((case["expected_cut_count"], case["evaluated_cut_count"]), (3, 3))
                self.assertEqual((case["nmin_kn"], case["nmax_kn"]), (top, top + 40.))
                self.assertEqual([cut["object_station_m"] for cut in case["cuts"]], list(CUTS))
                self.assertEqual([cut["nd_kn"] for cut in case["cuts"]], [top + 40., top + 20., top])
                self.assertTrue(all(cut["native_p_kn"] == -cut["nd_kn"] for cut in case["cuts"]))
                self.assertTrue(all(cut["superposition_residual_kn"] == 0. for cut in case["cuts"]))
            # Independent dimensions: .8*.8*25*1 =16 kN/m, at1.25m intervals.
            for interval in local["gravity_axial_balance"]["combinations"]["G"]["intervals"]:
                self.assertEqual(interval["predicted_self_weight_change_kn"], 20.)
                self.assertEqual(interval["native_axial_change_kn"], 20.)
                self.assertEqual(interval["superposition_residual_kn"], 0.)
        for stage in (default, self.stages):
            self.assertEqual(stage["r14_closure"]["engineering_release"], "NOT_READY")
        self.assertNotEqual(compare_runs(Path(self.default_summary["run_dir"]), self.directory)["status"], "IDENTICAL")

    def test_independent_stiffness_beta_and_cut_local_demand_are_numerically_consumed(self):
        # Independent 9-by9 perimeter cage:32Phi16, cover40/tie12/bar radius8.
        # No production stiffness, magnification or eccentricity function is an oracle.
        bar_area = math.pi * 16. ** 2 / 4
        steel_inertia = bar_area * (18 * 340. ** 2 + 2 * sum((-340. + j * 85.) ** 2 for j in range(1, 8)))
        concrete_inertia = 800. ** 4 / 12
        ec = 3250. * math.sqrt(35.) + 14000.
        ei = .2 * ec * concrete_inertia + 200000. * steel_inertia
        nk = math.pi ** 2 * ei / 2500. ** 2 / 1000.
        eccentricity_m = (15. + .03 * 800.) / 1000.
        for uid, top in TOP_COMPRESSION_KN.items():
            selected = self.stages["r10_live"]["per_member"][uid]["engineer_column_selection"]["selected"]
            self.assertEqual((selected["bar_count"], selected["diameter_mm"],
                              selected["num_bars_2_dir"], selected["num_bars_3_dir"]), (32, 16, 9, 9))
            local = self.stages["r08_local_slenderness"]["per_member"][uid]
            coefficient_n = top + 40.
            beta = 1. / (1. - 1.3 * coefficient_n / nk)
            for axis in ("M2", "M3"):
                actual = local["stiffness_and_euler"][axis]
                self.assertAlmostEqual(actual["selected_is_mm4"] / steel_inertia, 1., places=12)
                self.assertAlmostEqual(actual["selected_ei_nmm2"] / ei, 1., places=12)
                self.assertAlmostEqual(actual["selected_nk_kn"] / nk, 1., places=12)
            mag = local["magnified_selected_pmm"]
            self.assertEqual((mag["expected_row_count"], mag["resolved_row_count"]), (15, 15))
            for row in mag["rows"]:
                actual_nd = top + 16. * (2.5 - row["object_station_m"])
                self.assertEqual(row["nd_kn"], actual_nd)
                self.assertEqual(row["coefficient_nd_kn"], coefficient_n)
                self.assertEqual(row["analysis_element_id"], uid + "-elm")
                self.assertEqual(row["global_beta_ii_applied"], 1.)
                for suffix in ("m2", "m3"):
                    first_order = abs(row["first_order_" + suffix + "_knm"])
                    expected_floor = max(first_order, actual_nd * eccentricity_m)
                    self.assertAlmostEqual(row["beta_" + suffix], beta, places=12)
                    self.assertAlmostEqual(abs(row["first_order_" + suffix + "_design_knm"]), expected_floor, places=10)
                    self.assertAlmostEqual(abs(row["magnified_" + suffix + "_design_knm"]), expected_floor * beta, places=10)
                self.assertGreater(row["moment_reserve_knm"], 0.)
                self.assertLess(row["utilization"], 1.)
            self.assertGreater(len({row["nd_kn"] for row in mag["rows"]}), 1)

    def test_actual_interior_scwb_capacity_shear_and_cages_complete_the_slice(self):
        self.assertEqual(self.stages["beam_r10"]["calculated_beam_count"], 4)
        r10 = self.stages["r10_live"]["per_member"]
        joints = [joint for joint in r10["C1"]["scwb_joints"] if joint["joint_id"] == "P1"]
        self.assertEqual({joint["direction"] for joint in joints}, {"X", "Y"})
        for joint in joints:
            result = joint["seismic_axial_interval_check"]
            self.assertEqual(result["status"], "SCWB_EQ_7_3_INTERVAL_SUFFICIENT")
            self.assertEqual((result["expected_checks"], result["evaluated_checks"]), (8, 8))
            for case in result["cases"]:
                for sway in case["sways"]:
                    self.assertGreater(sway["ratio_lower"], 1.)
                    self.assertAlmostEqual(sway["ratio_lower"], sway["column_sum_lower_knm"] / sway["required_sum_upper_knm"])
        for member in r10.values():
            shear = member["column_transverse_and_shear"]["engineer_capacity_shear_ve"]
            for axis in ("V2", "V3"):
                self.assertLess(shear["axes"][axis]["max_utilization_ts500"], 1.)
                self.assertLess(shear["axes"][axis]["max_utilization_zero_concrete"], 1.)
            self.assertTrue(member["engineer_column_selection"]["selected"]["selected_transverse"]["all_tbdy_checks_met"])
        iteration = self.stages["report_evidence"]["alpha_iteration"]
        self.assertEqual(iteration["status"], "ALTERNATIVE_NOT_REQUIRED")
        self.assertFalse(iteration["feedback_consumed"])

    def test_source_weight_revision_changes_nmax_beta_and_actual_design_moments(self):
        raw, request = source_and_request(unit_weight_kn_m3=30.)
        self.assertNotEqual(raw, self.raw)
        summary, snapshot = self.calculate(raw, request, "heavier-self-weight")
        self.assertEqual(snapshot["results"]["r14_closure"]["numerically_closed_count"], 2)
        for uid, top in TOP_COMPRESSION_KN.items():
            old = self.stages["r08_local_slenderness"]["per_member"][uid]
            new = snapshot["results"]["r08_local_slenderness"]["per_member"][uid]
            self.assertEqual(new["axial_idealization_application"]["combinations"]["G"]["nmax_kn"], top + 48.)
            # The cage revision also binds source identity; compare its actual
            # reinforcement geometry rather than assuming equal source hashes.
            old_cage = self.stages["r10_live"]["per_member"][uid]["engineer_column_selection"]["selected"]
            new_cage = snapshot["results"]["r10_live"]["per_member"][uid]["engineer_column_selection"]["selected"]
            for key in ("bar_count", "diameter_mm", "num_bars_2_dir", "num_bars_3_dir", "area_mm2"):
                self.assertEqual(new_cage[key], old_cage[key])
            self.assertNotEqual(new["second_order_basis_application"]["selected_cage_sha256"],
                                old["second_order_basis_application"]["selected_cage_sha256"])
            self.assertNotEqual(new["axial_idealization_application"]["eligibility_sha256"],
                                old["axial_idealization_application"]["eligibility_sha256"])
            self.assertEqual(new["stiffness_and_euler"]["M2"]["selected_nk_kn"],
                             old["stiffness_and_euler"]["M2"]["selected_nk_kn"])
            old_rows, new_rows = old["magnified_selected_pmm"]["rows"], new["magnified_selected_pmm"]["rows"]
            self.assertGreater(new_rows[0]["beta_m2"], old_rows[0]["beta_m2"])
            self.assertGreater(abs(new_rows[0]["magnified_m2_design_knm"]), abs(old_rows[0]["magnified_m2_design_knm"]))
            for interval in new["gravity_axial_balance"]["combinations"]["G"]["intervals"]:
                self.assertAlmostEqual(interval["predicted_self_weight_change_kn"], 24.)
        self.assertNotEqual(compare_runs(self.directory, Path(summary["run_dir"]))["status"], "IDENTICAL")

    def test_missing_primitive_cut_does_not_shrink_design_population_or_grant_method(self):
        source = json.loads(self.raw)
        rowset = source["column_axial"]["demand_support"]["force_source"]["rowsets"]["C1"]
        index = next(i for i in range(rowset["NumberResults"])
                     if rowset["LoadCase"][i] == "LC_DL" and rowset["ObjSta"][i] == 1.25)
        for value in rowset.values():
            if isinstance(value, list):
                value.pop(index)
        rowset["NumberResults"] -= 1
        raw, request = bind_source(source, self.request)
        _, snapshot = self.calculate(raw, request, "missing-primitive-cut")
        stages = snapshot["results"]
        scope = stages["report_evidence"]["column_pmm_expected_instances"]
        self.assertEqual(scope["expected_member_combination_count"], 10)
        self.assertEqual(sum(r["configured_cut_coverage"]["matched_count"] for r in scope["instances"]), 30)
        local = stages["r08_local_slenderness"]["per_member"]["C1"]
        self.assertEqual(local["axial_idealization_evidence"]["status"], "SELF_WEIGHT_NMAX_INPUTS_REJECTED")
        self.assertIn("AXIAL_IDEALIZATION_INPUTS_UNRESOLVED", local["open_gates"])
        self.assertIn("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED", local["open_gates"])
        closed = {row["member_id"]: row for row in stages["r14_closure"]["columns"]}
        self.assertNotEqual(closed["C1"]["status"], "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES")
        self.assertEqual(stages["r14_closure"]["engineering_release"], "NOT_READY")

    def test_configured_cut_matching_accepts_one_ulp_but_rejects_shift_and_duplicates(self):
        for name, midpoint, duplicate, eligible in (
            ("one-ulp-cut", math.nextafter(1.25, math.inf), False, True),
            ("shifted-cut", 1.2501, False, False),
            ("duplicate-cut", 1.25, True, False),
            ("ambiguous-cut", math.nextafter(1.25, math.inf), True, False),
        ):
            with self.subTest(name=name):
                source = json.loads(self.raw)
                axial = source["column_axial"]
                for force in (axial["force_source"], axial["demand_support"]["force_source"]):
                    rowset = force["rowsets"]["C1"]
                    indices = [i for i, station in enumerate(rowset["ObjSta"]) if station == 1.25]
                    for index in indices:
                        if duplicate:
                            for field, values in rowset.items():
                                if isinstance(values, list):
                                    values.append(midpoint if field in ("ObjSta", "ElmSta") else values[index])
                        else:
                            rowset["ObjSta"][index] = rowset["ElmSta"][index] = midpoint
                    if duplicate:
                        rowset["NumberResults"] += len(indices)
                raw, request = bind_source(source, self.request)
                summary, snapshot = self.calculate(raw, request, name)
                stages = snapshot["results"]
                closure = stages["r14_closure"]
                self.assertEqual(summary["engineering_release"], "NOT_READY")
                if name == "duplicate-cut":
                    # The native force owner rejects exact full-key duplicates
                    # before selection or R14; no downstream closure is created.
                    self.assertIsNone(closure)
                    dependencies = summary["design_dependencies"]
                    self.assertEqual(dependencies["expected_column_count"], 2)
                    self.assertFalse(dependencies["members"]["C1"]["source_execution_allowed"])
                    self.assertIn("COLUMN_AXIAL_SOURCE_INVALID:FORCE_STATION_NEGATIVE_OR_FULL_KEY_DUPLICATE",
                                  dependencies["members"]["C1"]["reason_codes"])
                    continue
                self.assertEqual(closure["expected_column_count"], 2)
                self.assertEqual(closure["engineering_release"], "NOT_READY")
                members = {row["member_id"]: row for row in closure["columns"]}
                if eligible:
                    self.assertEqual(closure["numerically_closed_count"], 2)
                    local = stages["r08_local_slenderness"]["per_member"]["C1"]
                    evidence = local["axial_idealization_evidence"]
                    self.assertEqual(local["axial_idealization_application"]["status"], APPLIED)
                    self.assertEqual(evidence["physical_scope"]["configured_grid"]["cuts"][1]["object_station_m"], 1.25)
                    for case in evidence["combinations"].values():
                        self.assertEqual(case["cuts"][1]["object_station_m"], midpoint)
                        self.assertEqual(case["cuts"][1]["element_station_m"], midpoint)
                    native_cuts = {(row["combination"], row["object_station_m"], row["analysis_element_id"],
                                    row["element_station_m"])
                                   for case in evidence["combinations"].values() for row in case["cuts"]}
                    consumed_cuts = {(row["combination"], row["object_station_m"], row["analysis_element_id"],
                                      row["element_station_m"]) for row in local["magnified_selected_pmm"]["rows"]}
                    self.assertEqual(native_cuts, consumed_cuts)
                else:
                    self.assertNotEqual(members["C1"]["status"], "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES")

    def test_eligible_axial_method_does_not_hide_real_transverse_capacity_exceedance(self):
        request = deepcopy(self.request)
        request["column_selection"].update(tie_diameter_preference_mm=[10],
            stirrup_confinement_spacing_mm=90, stirrup_span_spacing_mm=90)
        _, snapshot = self.calculate(self.raw, request, "insufficient-transverse-design")
        stages = snapshot["results"]
        self.assertEqual(stages["r14_closure"]["numerically_closed_count"], 0)
        for uid in TOP_COMPRESSION_KN:
            self.assertEqual(stages["r08_local_slenderness"]["per_member"][uid]["axial_idealization_application"]["status"], APPLIED)
            shear = stages["r10_live"]["per_member"][uid]["column_transverse_and_shear"]["engineer_capacity_shear_ve"]
            self.assertGreater(shear["axes"]["V2"]["max_utilization_zero_concrete"], 1.)
        self.assertTrue(all("COLUMN_ZERO_CONCRETE_BRANCH_REVIEW_REQUIRED:V2" in row["open_gates"]
                            for row in stages["r14_closure"]["columns"]))
        # Exceeded conservative branch requires refinement; it is not relabelled
        # as a proven normative failure by this fixture.
        self.assertEqual(stages["r14_closure"]["engineering_release"], "NOT_READY")

    def test_normal_web_replay_and_report_use_same_recorded_idealization_without_owner_calls(self):
        def no_capture(*args, **kwargs):
            raise AssertionError("Offline example must not acquire ETABS")
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.root, live_capture=no_capture))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = "http://127.0.0.1:" + str(server.server_port)
            body = json.dumps({"base_run_id": self.directory.name, "design_scenario": self.request}).encode()
            with urlopen(Request(url + "/api/apply-rebar-selection", data=body,
                                 headers={"Content-Type": "application/json"}), timeout=30) as response:
                acknowledgement = json.load(response)
            directory = self.root / acknowledgement["run_id"]
            self.assertEqual(compare_runs(self.directory, directory)["status"], "IDENTICAL")
            owners = (
                "tbdy_next.engineering.pipeline.EnginePipelineRunner.run",
                "tbdy_next.engineering.column_r08_local_live.project_column_r08_local_live",
                "tbdy_next.engineering.column_r10_live.project_column_r10_live",
                "tbdy_next.engineering.column_axial_balance.project_self_weight_nmax_idealization",
                "tbdy_next.engineering.column_r14_closure.project_column_r14_and_r15_closure",
                "tbdy_next.engineering.rebar_selection.select_column_rebar",
            )
            with ExitStack() as stack:
                spies = [stack.enter_context(patch(owner, side_effect=AssertionError("Report-time calculation"))) for owner in owners]
                report = build_complete_report(self.root, directory.name)
                html = build_printable_html(report)
                self.assertEqual(report["example_context"]["classification"], "CONTRACT_FIXTURE")
                self.assertIn("SYNTHETIC CONTRACT FIXTURE — NO LIVE ETABS ANALYSIS", html)
                with urlopen(url + "/api/export-checks?run_id=" + directory.name, timeout=8) as response:
                    web_report = json.load(response)
                with urlopen(url + "/report/print?run_id=" + directory.name, timeout=8) as response:
                    web_html = response.read().decode()
            self.assertTrue(all(spy.call_count == 0 for spy in spies))
            self.assertEqual(report, web_report)
            self.assertEqual(html, web_html)
            heading = "Adopted self-weight axial idealization"
            self.assertTrue(heading in html, "Recorded axial idealization was not displayed")
            idealization_html = html.split(heading, 1)[1].split("<h3>", 1)[0]
            for text in ("SELF_WEIGHT_NMAX", "NOT_GRANTED", "2540", "1540",
                         "N used for coefficient", "Local N for section",
                         "conservatism and engineering acceptance are not established"):
                self.assertTrue(text in idealization_html, "Missing recorded idealization field: " + text)
            for uid in TOP_COMPRESSION_KN:
                self.assertEqual(report["r08_local_slenderness"]["per_member"][uid]["axial_idealization_application"],
                                 self.stages["r08_local_slenderness"]["per_member"][uid]["axial_idealization_application"])
            archived = json.loads((directory / "input.source").read_bytes())
            self.assertEqual(archived["column_axial"]["force_source"], json.loads(self.raw)["column_axial"]["force_source"])
            self.assertEqual((directory / "parent.source").read_bytes(), self.raw)
        finally:
            server.shutdown()
            thread.join(3)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
