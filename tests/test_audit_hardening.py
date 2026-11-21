"""Independent negative-contract regressions from the 2026-11-16 audit.

Synthetic rows below test completeness/persistence, not real ETABS acceptance.
Capacity solver doubles deliberately isolate gates from numerical kernel tests.
"""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tbdy_next.engineering.analysis_setup import _audit_cracked_section_modifiers
from tbdy_next.engineering.column_r14_closure import _evaluate_single_r14_column, project_column_r14_and_r15_closure
from tbdy_next.engineering.column_r08_local_live import _evaluate_spectral_bounding_corners, _project_single_r08_local
from tbdy_next.engineering.column_r10_live import _compute_capacity_shear_axes, _evaluate_story_alpha_summary
from tbdy_next.engineering.rebar_selection import normalize_column_selection_policy, select_column_rebar
from tbdy_next.engineering.pipeline_snapshot import SCHEMA, REQUIRED_KEYS, compare_runs, read_snapshot, record_snapshot
from tbdy_next.column_engine.csi_geometry import LocalSectionDims
from tbdy_next.receipts import ReceiptRun
from test_r10_live import _rowset

CLOSED = "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES"

def closure_fixture():
    return dict(uid="C1", axial={"combination_plan":{
        "source":"ASSIGNED_DESIGN", "blockers":[],
        "combinations":[{"name":n,"force_semantics":"STATIC_SIGNED_VECTOR"} for n in ("G","EX","EY")],
        "design_assignment":{"groups":{"gravity":["G"],"ductile":["EX","EY"]}}}},
        axial_col={"story":"S1","section":"C60","ts500_limit_kn":5000.,
            "tbdy_seismic_reference_limit_kn":3500.,
            "combination_checks":[{"combination":n,"nd_kn":900.} for n in ("G","EX","EY")]},
        pmm_col={"member_id":"C1","status":"NUMERICAL_COMPLETE",
                 "expected_station_count":3,"evaluated_station_count":3},
        r08_global={"status":"NUMERIC_PRECHECK_UNAPPROVED","expected_story_direction_count":2,
                    "evaluated_story_direction_count":2,"missing_story_direction":[],
                    "direction_results":{d:{"within_reference_limit_candidate":True} for d in ("X","Y")}},
        r08_local_col={"open_gates":[], "magnified_selected_pmm":{
            "status":"MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN","max_utilization":.4,
            "expected_row_count":3,"evaluated_row_count":3,"resolved_row_count":3}},
        beam_by_id={}, r10_det={
            "engineer_column_selection":{"status":"ENGINEER_COLUMN_SELECTED_NOT_PROVEN",
                "selected":{"label":"16Phi24","rho":.02,"selected_transverse":{"all_tbdy_checks_met":True}}},
            "column_transverse_and_shear":{"engineer_capacity_shear_ve":{"axes":{
                v:{"max_utilization_ts500":.5,"max_utilization_zero_concrete":.8} for v in ("V2","V3")}}},
            "member_joint_ends":[{"end":e,"faces":{},"status":"NO_RECORDED_BEAM_AT_NODE"} for e in ("I","J")],
            "scwb_joints":[]},
        story_alpha={"stories":[{"story":"S1","direction":d,"governing_alpha_i":1.,
            "denominator_status":"FULL_STORY_COLUMN_DENOMINATOR","demand_feedback_action":"NONE"} for d in ("X","Y")]},
        analysis_setup_reconciliation={"cracked_section_stiffness_audit":{
            "all_columns_match_0_70":True,"all_beams_match_0_35":True},"reconciled_blocker_codes":[]})

class ClosureNegativeContracts(unittest.TestCase):
    def test_complete_synthetic_numeric_baseline_stays_not_proven(self):
        result=_evaluate_single_r14_column(**closure_fixture())
        self.assertEqual(result["status"],CLOSED)
        self.assertEqual(result["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(result["engineering_release"],"NOT_READY")

    def assert_not_closed(self, edit, gate=None):
        b=closure_fixture(); edit(b); r=_evaluate_single_r14_column(**b)
        self.assertNotEqual(r["status"],CLOSED, r)
        if gate: self.assertIn(gate,r["open_gates"])
        return r

    def test_blocked_nonempty_pmm_cannot_close(self):
        self.assert_not_closed(lambda b:b["r08_local_col"].update(magnified_selected_pmm={"status":"BLOCKED","max_utilization":None}))
    def test_missing_global_result_cannot_close(self):
        self.assert_not_closed(lambda b:b.update(r08_global=None))
    def test_unknown_global_result_cannot_close(self):
        self.assert_not_closed(lambda b:b.update(r08_global={"all_observed_below_numeric_limit":None}))
    def test_blocked_global_result_with_affirmative_flags_cannot_close(self):
        self.assert_not_closed(lambda b: b["r08_global"].update(status="BLOCKED_SOURCE_UNAVAILABLE"),
                               "GLOBAL_PDELTA_UNKNOWN_OR_NOT_ACCEPTED")
    def test_missing_global_story_direction_count_cannot_close(self):
        self.assert_not_closed(lambda b: b["r08_global"].update(evaluated_story_direction_count=1),
                               "GLOBAL_PDELTA_UNKNOWN_OR_NOT_ACCEPTED")
    def test_partial_pmm_result_cannot_close(self):
        self.assert_not_closed(lambda b: b["pmm_col"].update(status="NUMERICAL_PARTIAL"),
                               "COLUMN_PMM_RESULT_MISSING_OR_INCOMPLETE")
    def test_partial_magnified_station_population_cannot_close(self):
        self.assert_not_closed(lambda b: b["r08_local_col"]["magnified_selected_pmm"].update(resolved_row_count=2),
                               "SECOND_ORDER_PMM_NOT_NUMERICALLY_RESOLVED")
    def test_missing_shear_ratio_cannot_close(self):
        self.assert_not_closed(lambda b:b["r10_det"]["column_transverse_and_shear"]["engineer_capacity_shear_ve"]["axes"]["V2"].update(max_utilization_ts500=None))
    def test_nan_pmm_ratio_cannot_close(self):
        self.assert_not_closed(lambda b:b["r08_local_col"]["magnified_selected_pmm"].update(max_utilization=float("nan")))
    def test_upstream_r03_blocker_propagates(self):
        self.assert_not_closed(lambda b:b["analysis_setup_reconciliation"].update(reconciled_blocker_codes=["ANALYSIS_GENERATION_NOT_PROVEN"]),"R03:ANALYSIS_GENERATION_NOT_PROVEN")
    def test_local_open_gate_propagates(self):
        self.assert_not_closed(lambda b:b["r08_local_col"].update(open_gates=["MISSING_EI"]),"R08_LOCAL:MISSING_EI")
    def test_missing_selected_transverse_cannot_close(self):
        self.assert_not_closed(lambda b:b["r10_det"]["engineer_column_selection"]["selected"].pop("selected_transverse"))
    def test_missing_axial_limits_cannot_close(self):
        self.assert_not_closed(lambda b:b["axial_col"].pop("ts500_limit_kn"))
    def test_missing_expected_axial_combo_cannot_close(self):
        self.assert_not_closed(lambda b:b["axial_col"]["combination_checks"].pop())
    def test_invalid_or_infinite_axial_force_blocks_instead_of_failing_the_member(self):
        for value in ("bad", float("inf")):
            with self.subTest(value=value):
                result = self.assert_not_closed(lambda b: b["axial_col"]["combination_checks"][0].update(nd_kn=value),
                                                "AXIAL_DEMAND_MISSING_OR_INVALID")
                self.assertEqual(result["normative_failures"], [])
    def test_missing_required_spectral_result_cannot_close(self):
        def edit(b): b["axial"]["combination_plan"]["combinations"][-1]["force_semantics"]="SCALAR_COMPONENT_ENVELOPE"
        self.assert_not_closed(edit,"SPECTRAL_PMM_REQUIRED_POPULATION_NOT_PROVEN")
    def test_missing_one_story_direction_cannot_close(self):
        self.assert_not_closed(lambda b:b["story_alpha"]["stories"].pop())
    def test_unobserved_joint_cannot_be_assumed_beamless(self):
        self.assert_not_closed(lambda b:b["r10_det"].update(member_joint_ends=[]))
    def test_missing_joint_end_cannot_be_assumed_beamless(self):
        self.assert_not_closed(lambda b: b["r10_det"]["member_joint_ends"].pop(),
                               "PHYSICAL_JOINT_TOPOLOGY_NOT_OBSERVED")
    def test_recorded_beam_axis_requires_joint_calculation(self):
        def edit(b):
            b["r10_det"]["member_joint_ends"][0].update(
                status="JOINT_GEOMETRIC_REFERENCES_CALCULATED", faces={"2+": {"frame_id": "B1"}}, axes=[])
            b["r10_det"]["scwb_joints"] = [{"beam_ids": ["B1"], "scenario_reference_satisfied": True}]
            b["beam_by_id"]["B1"] = {"member_id": "B1", "engineer_shear_ve": {"gravity_shear_vdy_kn": 20},
                                      "engineer_stirrups": {"confinement": {"spacing_ok": True, "utilization_conservative": .5}}}
        self.assert_not_closed(edit, "JOINT_APPLICABLE_AXIS_COVERAGE_INCOMPLETE:I")
    def test_missing_incident_beam_is_not_dropped(self):
        def edit(b):
            b["r10_det"]["scwb_joints"]=[{"beam_ids":["B1","B2"],"scenario_reference_satisfied":True,"sampled_minimum_normalized_ratio":1.4}]
            b["beam_by_id"]={"B1":{"member_id":"B1","engineer_shear_ve":{"gravity_shear_vdy_kn":20.},"engineer_stirrups":{"confinement":{"spacing_ok":True,"utilization_conservative":.5}}}}
        self.assert_not_closed(edit,"CONNECTED_BEAM_RESULT_MISSING:B2")
    def test_zero_concrete_exceedance_is_review_not_invented_physical_fail(self):
        r=self.assert_not_closed(lambda b:b["r10_det"]["column_transverse_and_shear"]["engineer_capacity_shear_ve"]["axes"]["V2"].update(max_utilization_zero_concrete=1.7))
        self.assertEqual(r["normative_failures"],[])
    def test_explicit_pmm_failure_not_masked_by_missing_other_data(self):
        def edit(b):
            b["r08_local_col"]["magnified_selected_pmm"]={"status":"MAGNIFIED_PMM_EXCEEDS_CAPACITY","max_utilization":1.2}
            b["r08_global"]=None
        r=self.assert_not_closed(edit)
        self.assertEqual(r["status"],"R14_FAILED_NORMATIVE_CHECK")
        self.assertIn("SECOND_ORDER_MAGNIFIED_SELECTED_PMM_EXCEEDED",r["normative_failures"])
    def test_missing_expected_member_kept_in_population_ledger(self):
        b=closure_fixture()
        r=project_column_r14_and_r15_closure(
            geometry={"checks":[{"check_id":"column_rect_min","items":[{"element_id":"C1"},{"element_id":"C2"}]}]},
            axial={**b["axial"],"columns":[{"element_id":"C1",**b["axial_col"]}]},
            pmm={"scope":"ALL_COLUMNS","member_id":"ALL","members":[b["pmm_col"]]},
            r08_second_order=b["r08_global"],r08_local={"per_member":{"C1":b["r08_local_col"]}},
            beam_r10=None,r10_live={"per_member":{"C1":b["r10_det"]},"story_alpha":b["story_alpha"]},
            analysis_setup_reconciliation=b["analysis_setup_reconciliation"])
        self.assertEqual(r["expected_column_count"],2)
        self.assertEqual(r["ledger_column_count"],2)
        self.assertEqual(r["missing_column_ids"],["C2"])
        self.assertNotEqual(r["status"],"R15_ALL_COLUMNS_CLOSED_NOT_PROVEN")

class MagnifiedPmmContracts(unittest.TestCase):
    def test_unresolved_solver_rows_cannot_return_a_within_capacity_scenario(self):
        from test_r08_local_live import _r08_local_fixture

        source, geometry, axial, pmm = _r08_local_fixture()
        pmm["expected_station_count"] = 2
        section = SimpleNamespace(t2=800.0, t3=800.0, bars=[])
        unresolved = SimpleNamespace(assess=lambda *args: {"status": "NUMERIC_UNRESOLVED", "utilization": None})
        with patch("tbdy_next.engineering.column_r08_local_live.solver", return_value=unresolved):
            result = _project_single_r08_local(source, geometry, axial, pmm, eng_col_section=section)
        magnified = result["magnified_selected_pmm"]
        self.assertEqual(magnified["status"], "MAGNIFIED_PMM_COVERAGE_OR_NUMERIC_UNRESOLVED")
        self.assertEqual(magnified["resolved_row_count"], 0)
        self.assertIsNone(magnified["max_utilization"])


class PmmAnalysisMeshContracts(unittest.TestCase):
    def _two_element_column(self):
        from tbdy_next.engineering.column_r10_live import (
            ANALYSIS_FRAME_ELEMENTS, ANALYSIS_JOINT_COORDINATE_SCHEMA, ANALYSIS_JOINT_ELEMENTS, END_OFFSETS,
            FRAME_OUTPUT_STATIONS,
        )
        from test_r03_analysis_setup import capture_table
        from test_r08_local_live import _r08_local_fixture

        source, geometry, axial, _ = _r08_local_fixture()
        source["geometry_capture"]["schema"] = "tbdy.next.geometry.capture.v2"
        source["geometry_capture"]["tables"]["COLUMN_CONNECTIVITY"]["field_metadata"]["table_version"] = 1

        def source_table(key, fields, rows, **units):
            table = capture_table(key, fields, rows)
            table["field_metadata"]["table_version"] = 1
            table["field_metadata"]["units_by_field"].update(units)
            return table

        tables = {
            ANALYSIS_FRAME_ELEMENTS: source_table(
                ANALYSIS_FRAME_ELEMENTS, ["Story", "ObjType", "ObjName", "ElmName", "ElmJtI", "ElmJtJ"],
                [("+4.50", "Frame", "127", "E2", "B", "412"),
                 ("+4.50", "Frame", "127", "E1", "1044", "B")],
            ),
            ANALYSIS_JOINT_ELEMENTS: source_table(
                ANALYSIS_JOINT_ELEMENTS,
                ["Story", "ElmName", "ObjType", "ObjLabel", "ObjName", "GlobalX", "GlobalY", "GlobalZ"],
                [("+4.50", "1044", "Point", "1044", "1044", "7", "11", "4.5"),
                 ("+4.50", "B", "Frame", "C88", "127", "7", "11", "6.39999"),
                 ("+4.50", "412", "Point", "412", "412", "7", "11", "9.0")],
                GlobalX="m", GlobalY="m", GlobalZ="m",
            ),
            END_OFFSETS: source_table(
                END_OFFSETS, ["UniqueName", "Story", "OffsetI", "OffsetJ"],
                [("127", "+4.50", "0", "0.7")], OffsetI="m", OffsetJ="m",
            ),
            FRAME_OUTPUT_STATIONS: source_table(
                FRAME_OUTPUT_STATIONS, ["Story", "UniqueName", "StationOpt", "MaxSpacing", "MinStations"],
                [("+4.50", "127", "Min Stations", "None", "3")], MaxSpacing="m",
            ),
        }
        source["column_axial"]["r10_source"] = {
            "schema": "tbdy.next.r10-live-source.v1", "units_before": 6, "units_after": 6,
            "model_locked_before": True, "model_locked_after": True, "table_reads": tables,
            "analysis_joint_coordinates": {
                "schema": ANALYSIS_JOINT_COORDINATE_SCHEMA, "coordinate_system": "Global", "units": "m",
                "coordinates": {"1044": [7.0, 11.0, 4.5], "B": [7.0, 11.0, 6.4], "412": [7.0, 11.0, 9.0]},
                "errors": {},
            },
        }
        axial["combination_plan"] = {
            "blockers": [], "combinations": [{"name": "G", "force_semantics": "STATIC_SIGNED_VECTOR"}],
        }
        axial["columns"][0]["combination_checks"] = [{"combination": "G", "status": "WITHIN_LIMIT"}]
        return source, geometry, axial

    def test_configured_cut_subset_requires_both_sides_of_a_mesh_node(self):
        from tbdy_next.engineering.column_pmm import (
            bind_configured_output_cuts, bind_pmm_mesh_source, evaluate_column_pmm,
        )

        source, geometry, axial = self._two_element_column()
        mesh = bind_pmm_mesh_source(source, {"127": "+4.50"})["members"]
        configured = bind_configured_output_cuts(source, mesh)
        self.assertEqual(configured["127"]["status"], "REQUIRED_SUBSET_BOUND")
        required = [(0.0, "E1", 0.0), (1.9, "E1", 1.9), (1.9, "E2", 0.0), (3.8, "E2", 1.9)]
        derived = [(round(cut["object_station_m"], 9), cut["analysis_element_id"], round(cut["element_station_m"], 9))
                   for cut in configured["127"]["cuts"]]
        self.assertCountEqual(derived, required)

        def evaluate(cuts):
            rows = [("127", station, element, local, "G", "Single Value", 0.0,
                     -100.0, 0.0, 0.0, 0.0, 1.0, 1.0) for station, element, local in cuts]
            source["column_axial"]["force_source"]["rowsets"]["127"] = _rowset(rows)
            return evaluate_column_pmm(source, geometry, axial, station_minimums={"127": 3},
                                       mesh_members=mesh, configured_cuts=configured)

        with patch("tbdy_next.engineering.column_pmm._station_result",
                   return_value={"status": "WITHIN_SCENARIO_SURFACE"}) as assess:
            resolved = evaluate(required)
            self.assertEqual(resolved["status"], "NUMERICAL_COMPLETE")
            self.assertEqual(resolved["evaluated_station_count"], 4)
            self.assertEqual(resolved["formal_compliance"], "NOT_PROVEN")
            self.assertEqual(assess.call_count, 4)

            # Keep the same row count and both element IDs while omitting the E2 side at 1.9 m.
            assess.reset_mock()
            blocked = evaluate([required[0], required[1], (2.2, "E2", 0.3), required[3]])
            assess.assert_not_called()
            self.assertEqual(blocked["status"], "BLOCKED")
            combination = blocked["combinations"][0]
            self.assertEqual(combination["reason"], "ETABS_CONFIGURED_CUT_COVERAGE_UNRESOLVED")
            self.assertEqual(combination["analysis_element_coverage"]["missing_analysis_element_ids"], [])
            coverage = combination["configured_cut_coverage"]
            self.assertEqual((coverage["required_count"], coverage["matched_count"]), (4, 3))
            self.assertEqual(len(coverage["missing_cuts"]), 1)
            missing = coverage["missing_cuts"][0]
            self.assertEqual(missing["analysis_element_id"], "E2")
            self.assertAlmostEqual(missing["object_station_m"], 1.9)
            self.assertAlmostEqual(missing["element_station_m"], 0.0)

    def test_missing_or_failed_native_coordinates_cannot_use_rounded_display_values(self):
        from tbdy_next.engineering.column_pmm import bind_configured_output_cuts, bind_pmm_mesh_source

        for issue in ("missing_joint", "failed_joint", "uncaptured_native_coordinates"):
            with self.subTest(issue=issue):
                source, _, _ = self._two_element_column()
                r10 = source["column_axial"]["r10_source"]
                joints = r10["analysis_joint_coordinates"]
                if issue == "uncaptured_native_coordinates":
                    del r10["analysis_joint_coordinates"]
                elif issue == "missing_joint":
                    del joints["coordinates"]["B"]
                else:
                    joints["errors"]["B"] = "FAILED"
                mesh = bind_pmm_mesh_source(source, {"127": "+4.50"})["members"]
                self.assertTrue(mesh["127"]["roster_bound"])
                configured = bind_configured_output_cuts(source, mesh)["127"]
                self.assertEqual(configured["status"], "NOT_PROVEN")
                self.assertEqual(configured["cuts"], [])
                expected_reason = ("ANALYSIS_JOINT_COORDINATE_SOURCE_UNAVAILABLE" if issue == "uncaptured_native_coordinates"
                                   else "ANALYSIS_JOINT_COORDINATES_MISSING_OR_AMBIGUOUS")
                self.assertEqual(configured["reason"], expected_reason)

    def test_mesh_midpoint_uses_the_containing_element_local_origin(self):
        from math import nextafter

        from tbdy_next.engineering.column_pmm import bind_configured_output_cuts, bind_pmm_mesh_source
        from tbdy_next.engineering.column_r10_live import ANALYSIS_FRAME_ELEMENTS

        source, _, _ = self._two_element_column()
        r10 = source["column_axial"]["r10_source"]
        tables = r10["table_reads"]
        points = r10["analysis_joint_coordinates"]["coordinates"]
        points["B"] = [7.0, nextafter(11.0, 0.0), 5.7]
        mesh = bind_pmm_mesh_source(source, {"127": "+4.50"})["members"]
        configured = bind_configured_output_cuts(source, mesh)["127"]
        self.assertEqual(configured["status"], "REQUIRED_SUBSET_BOUND")
        self.assertEqual(len(configured["cuts"]), 5)
        midpoint = configured["cuts"][3]
        self.assertAlmostEqual(midpoint["object_station_m"], 1.9)
        self.assertEqual(midpoint["analysis_element_id"], "E2")
        self.assertAlmostEqual(midpoint["element_station_m"], 0.7)

        original_y = points["B"][1]
        points["B"][1] = 11.000001
        unbound = bind_configured_output_cuts(source, mesh)["127"]
        self.assertEqual(unbound["reason"], "VERTICAL_ANALYSIS_MESH_GEOMETRY_UNVERIFIED")
        points["B"][1] = original_y

        frame = next(row for row in tables[ANALYSIS_FRAME_ELEMENTS]["rows"] if row["ElmName"] == "E2")
        frame["ElmJtI"], frame["ElmJtJ"] = frame["ElmJtJ"], frame["ElmJtI"]
        reversed_mesh = bind_pmm_mesh_source(source, {"127": "+4.50"})["members"]
        unbound = bind_configured_output_cuts(source, reversed_mesh)["127"]
        self.assertEqual(unbound["reason"], "ORIENTED_ANALYSIS_ELEMENT_CHAIN_UNVERIFIED")

    def test_configured_cut_subset_detects_shifted_midpoint_with_same_row_count(self):
        from tbdy_next.engineering.column_pmm import bind_configured_output_cuts, _required_cut_coverage
        from tbdy_next.engineering.column_r10_live import END_OFFSETS
        from test_r03_analysis_setup import capture_table
        from test_r08_local_live import _r08_local_fixture

        source, _, _, _ = _r08_local_fixture()
        geometry = source["geometry_capture"]
        geometry["schema"] = "tbdy.next.geometry.capture.v2"
        geometry["tables"]["COLUMN_CONNECTIVITY"]["field_metadata"]["table_version"] = 1
        offsets = capture_table(END_OFFSETS, ["UniqueName", "Story", "OffsetI", "OffsetJ"],
                                [("127", "+4.50", "0", "0.7")])
        offsets["field_metadata"].update(table_version=1)
        offsets["field_metadata"]["units_by_field"].update(OffsetI="m", OffsetJ="m")
        source["column_axial"]["r10_source"] = {
            "schema": "tbdy.next.r10-live-source.v1", "units_before": 6, "units_after": 6,
            "model_locked_before": True, "model_locked_after": True, "table_reads": {END_OFFSETS: offsets},
        }
        qualified_mesh = {"127": {"expected_analysis_element_ids": ["127"], "single_element_end_joints": ["1044", "412"],
                                 "station_assignment": {"Story": "+4.50", "StationOpt": "Min Stations",
                                                        "MinStations": "3", "MaxSpacing": "None"}}}
        grid = bind_configured_output_cuts(source, qualified_mesh)["127"]
        self.assertEqual([cut["object_station_m"] for cut in grid["cuts"]], [0.0, 1.9, 3.8])
        original = [("127", x, "127", x) for x in (0.0, 1.9, 3.8, 2.2)]
        shifted = [("127", x, "127", x) for x in (0.0, 2.0, 3.8, 2.2)]
        extra = _required_cut_coverage(original, grid)
        self.assertEqual(extra["matched_count"], 3)
        self.assertEqual(extra["unmatched_native_cut_count"], 1)
        self.assertFalse(extra["exact_cut_census"])
        self.assertTrue(_required_cut_coverage(original[:3], grid)["exact_cut_census"])
        missing = _required_cut_coverage(shifted, grid)["missing_cuts"]
        self.assertEqual([cut["object_station_m"] for cut in missing], [1.9])

    def test_a_missing_element_blocks_the_signed_check_even_at_the_station_minimum(self):
        from tbdy_next.engineering.column_pmm import bind_pmm_mesh_source, evaluate_column_pmm
        from tbdy_next.engineering.column_r10_live import ANALYSIS_FRAME_ELEMENTS
        from test_r03_analysis_setup import capture_table
        from test_r08_local_live import _r08_local_fixture

        source, geometry, axial, _ = _r08_local_fixture()
        table = capture_table(ANALYSIS_FRAME_ELEMENTS, ["Story", "ObjType", "ObjName", "ElmName", "ElmJtI", "ElmJtJ"],
                              [("+4.50", "Frame", "127", "127-1", "A", "B"), ("+4.50", "Frame", "127", "127-2", "B", "C"),
                               ("Other story", "Shell", "127", "127-1", "X", "Y")])
        table["field_metadata"]["table_version"] = 1
        source["column_axial"]["r10_source"] = {
            "schema": "tbdy.next.r10-live-source.v1", "model_locked_before": True, "model_locked_after": True,
            "units_before": 6, "units_after": 6, "table_reads": {ANALYSIS_FRAME_ELEMENTS: table},
        }
        mesh = bind_pmm_mesh_source(source, {"127": "+4.50"})
        self.assertEqual(mesh["members"]["127"]["expected_analysis_element_ids"], ["127-1", "127-2"])
        axial["combination_plan"] = {"blockers": [], "combinations": [{"name": "G", "force_semantics": "STATIC_SIGNED_VECTOR"}]}
        axial["columns"][0]["combination_checks"] = [{"combination": "G", "status": "WITHIN_LIMIT"}]
        rows = [("127", station, "127-1", station, "G", "Single Value", 0.0, -100.0, 0.0, 0.0, 0.0, 1.0, 1.0)
                for station in (0.0, 1.0, 2.0)]
        force_source = source["column_axial"]["force_source"]
        force_source["rowsets"]["127"] = _rowset(rows)
        with patch("tbdy_next.engineering.column_pmm._station_result", return_value={"status": "WITHIN_SCENARIO_SURFACE"}) as assess:
            blocked = evaluate_column_pmm(source, geometry, axial, station_minimums={"127": 3},
                                          mesh_members=mesh["members"])
            assess.assert_not_called()
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertEqual(blocked["combinations"][0]["analysis_element_coverage"]["missing_analysis_element_ids"], ["127-2"])

            # The shared coordinate has two native cuts, one on either side of the mesh boundary.
            rows.append(("127", 2.0, "127-2", 0.0, "G", "Single Value", 0.0, -100.0, 0.0, 0.0, 0.0, 1.0, 1.0))
            force_source["rowsets"]["127"] = _rowset(rows)
            resolved = evaluate_column_pmm(source, geometry, axial, station_minimums={"127": 3},
                                           mesh_members=mesh["members"])
            self.assertEqual(resolved["evaluated_station_count"], 4)
            self.assertEqual(assess.call_count, 4)
            self.assertEqual(resolved["formal_compliance"], "NOT_PROVEN")

        conflict = bind_pmm_mesh_source(source, {"127": "Wrong story"})
        self.assertFalse(conflict["members"]["127"]["roster_bound"])
        self.assertEqual(conflict["members"]["127"]["reason"], "ANALYSIS_FRAME_OBJECT_MAPPING_CONFLICT")

    def test_etabs_output_assignment_supplies_the_minimum_without_a_summary_value(self):
        from tbdy_next.engineering.column_pmm import bind_pmm_mesh_source, configured_output_station_minimums
        from tbdy_next.engineering.column_r10_live import FRAME_OUTPUT_STATIONS
        from test_r03_analysis_setup import capture_table
        from test_r08_local_live import _r08_local_fixture

        source, geometry, _, _ = _r08_local_fixture()
        table = capture_table(FRAME_OUTPUT_STATIONS, ["Story", "UniqueName", "StationOpt", "MaxSpacing", "MinStations"],
                              [("+4.50", "127", "Min Stations", "None", "4")])
        table["field_metadata"]["table_version"] = 1
        table["field_metadata"]["units_by_field"]["MaxSpacing"] = "m"
        source["column_axial"]["r10_source"] = {
            "schema": "tbdy.next.r10-live-source.v1", "model_locked_before": True, "model_locked_after": True,
            "units_before": 6, "units_after": 6, "table_reads": {FRAME_OUTPUT_STATIONS: table},
        }
        mesh = bind_pmm_mesh_source(source, {"127": "+4.50"})
        self.assertEqual(configured_output_station_minimums(source, geometry, mesh_members=mesh["members"]), {"127": 4})


class SpectrumPopulationContracts(unittest.TestCase):
    class Solver:
        def __init__(self,result=None): self.calls=0; self.result=result or {"status":"WITHIN_SCENARIO_SURFACE","utilization":.2}
        def assess(self,*args): self.calls+=1; return self.result
    def fixture(self):
        rows=[]
        for name in ("EX","EY"):
            for sta in (0.,3.):
                for step,n,m in (("Max",-100.,20.),("Min",-200.,-20.)):
                    rows.append(("C1",sta,"C1-1",sta,name,step,0.,n,0.,0.,0.,m,m))
        return dict(uid="C1",source={"column_axial":{"force_source":{"rowsets":{"C1":_rowset(rows)}}}},
            axial={"combination_plan":{"combinations":[{"name":n,"force_semantics":"SCALAR_COMPONENT_ENVELOPE"} for n in ("EX","EY")]}},
            dims_local=LocalSectionDims(600,600),cap_solver=self.Solver(),
            stiffness_map={a:{"selected_nk_ts500_7_20_kn":5000.} for a in ("M2","M3")},global_beta_ii=1.)
    def filter_rows(self,k,keep):
        from tbdy_next.engineering.column_pmm import native_frame_force_rows
        rows=[r for r in native_frame_force_rows(k["source"]["column_axial"]["force_source"]["rowsets"]["C1"],"C1") if keep(r)]
        k["source"]["column_axial"]["force_source"]["rowsets"]["C1"]=_rowset(rows)
    def test_complete_synthetic_case_cut_box_is_reference_only(self):
        r=_evaluate_spectral_bounding_corners(**self.fixture())
        self.assertEqual(r["status"],"BOUNDED_CORNER_ENVELOPE_WITHIN_CAPACITY_NOT_PROVEN")
        self.assertEqual(r["expected_case_cut_count"],4)
        self.assertEqual(r["evaluated_corner_count"],32)
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")
    def test_missing_y_stops_before_solver(self):
        k=self.fixture(); self.filter_rows(k,lambda r:r[4]!="EY")
        r=_evaluate_spectral_bounding_corners(**k)
        self.assertFalse(r["coverage_complete"]); self.assertEqual(k["cap_solver"].calls,0)
    def test_mesh_conflict_stops_spectral_reference_before_solver(self):
        k = self.fixture()
        r = _evaluate_spectral_bounding_corners(**k, mesh_blocked_combinations=("EY",))
        self.assertIn("SPECTRAL_ANALYSIS_ELEMENT_COVERAGE_UNRESOLVED:EY", r["reason_codes"])
        self.assertEqual(k["cap_solver"].calls, 0)
    def test_missing_one_case_cut_stops_before_solver(self):
        k=self.fixture(); self.filter_rows(k,lambda r:not(r[4]=="EY" and r[1]==3.))
        r=_evaluate_spectral_bounding_corners(**k)
        self.assertFalse(r["coverage_complete"]); self.assertEqual(len(r["missing_case_cuts"]),1)
    def test_missing_min_step_stops_before_solver(self):
        k=self.fixture(); self.filter_rows(k,lambda r:not(r[4]=="EY" and r[1]==3. and r[5]=="Min"))
        r=_evaluate_spectral_bounding_corners(**k)
        self.assertFalse(r["coverage_complete"]); self.assertEqual(k["cap_solver"].calls,0)
    def test_missing_selected_euler_load_is_not_template_fallback(self):
        k=self.fixture(); k["stiffness_map"]["M2"]={"preferred_nk_kn":10000.}
        r=_evaluate_spectral_bounding_corners(**k)
        self.assertFalse(r["coverage_complete"])
    def test_unknown_global_factor_blocks(self):
        k=self.fixture(); k["global_beta_ii"]=None
        self.assertFalse(_evaluate_spectral_bounding_corners(**k)["coverage_complete"])
    def test_nan_solver_utilization_is_unresolved(self):
        k=self.fixture(); k["cap_solver"]=self.Solver({"status":"WITHIN_SCENARIO_SURFACE","utilization":math.nan})
        r=_evaluate_spectral_bounding_corners(**k)
        self.assertEqual(r["status"],"SPECTRAL_BOUNDING_NUMERIC_UNRESOLVED"); self.assertIsNone(r["max_bounding_utilization"])
    def test_unknown_solver_status_cannot_be_counted_as_zero_utilization(self):
        k=self.fixture(); k["cap_solver"]=self.Solver({"status":"BLOCKED","utilization":0.})
        self.assertEqual(_evaluate_spectral_bounding_corners(**k)["status"],"SPECTRAL_BOUNDING_NUMERIC_UNRESOLVED")
    def test_overlarge_box_is_not_physical_member_failure(self):
        k=self.fixture(); k["cap_solver"]=self.Solver({"status":"EXCEEDS_SCENARIO_SURFACE","utilization":1.2})
        r=_evaluate_spectral_bounding_corners(**k)
        self.assertEqual(r["status"],"CONSERVATIVE_CORNER_EXCEEDS_1_0_CONCURRENT_VECTOR_REQUIRED")
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")

class SourceAndNormativeRepairContracts(unittest.TestCase):
    def test_all_fallback_sections_are_inspected_but_assignment_stays_unproven(self):
        rows=[{"Name":n,"DesignType":t,"I2Mod":v,"I3Mod":v} for n,t,v in (("C_OK","Column",.7),("C_BAD","Column",1.),("B_OK","Beam",.35),("B_BAD","Beam",1.))]
        r=_audit_cracked_section_modifiers({"geometry_capture":{"tables":{"RECTANGULAR_SECTIONS":{"rows":rows}}}})
        self.assertEqual(len(r["column_sections"]),2); self.assertEqual(len(r["beam_sections"]),2)
        self.assertFalse(r["assignment_coverage_proven"])
        self.assertEqual(r["status"],"MODIFIERS_INCOMPLETE_OR_MISMATCHED")
    def test_policy_may_tighten_but_not_relax_supported_bounds(self):
        self.assertEqual(normalize_column_selection_policy({"min_rho":.02})["min_rho"],.02)
        for values in ({"min_rho":.005},{"max_rho":.05}):
            with self.subTest(values=values), self.assertRaises(ValueError): normalize_column_selection_policy(values)
    def test_local_section_extents_are_not_swapped_twice(self):
        class StopAfterDimensions(Exception): pass
        captured=[]
        def observe(*args): captured.append(args); raise StopAfterDimensions()
        with patch("tbdy_next.engineering.rebar_selection.LocalSectionDims",side_effect=observe):
            with self.assertRaises(StopAfterDimensions):
                select_column_rebar(t2_mm=800.,t3_mm=300.,cover_mm=40.,fck_mpa=35.,fcd_mpa=35/1.5,
                    fyd_mpa=420/1.15,es_mpa=200000.,fywk_mpa=420.,gamma_c=1.5,gamma_s=1.15,
                    local_axis_angle_deg=0.,demand_vectors=[],shear_demands=[],policy={})
        self.assertEqual(captured,[(800.,300.)])
        from tbdy_next.column_engine.ts500_column import apply_minimum_eccentricity
        r=apply_minimum_eccentricity(nd_kn=1000.,m2_knm=0.,m3_knm=0.,dims=LocalSectionDims(*captured[0]))
        self.assertEqual(abs(r["m2_design_knm"]),24.); self.assertEqual(abs(r["m3_design_knm"]),39.)
    def test_unsafe_capacity_ratio_reduction_replaced_by_unreduced_reference(self):
        joints=[{"target_end":e,"direction":"X","cases":[{"output_case":"G","target_column_capacity_knm":500.,
            "sum_mrc_reference_knm":2000.,"sum_mrb_reference_knm":800.,"reference_satisfied":True}]} for e in ("I","J")]
        # Explicit synthetic Vd lies below the unreduced capacity reference.
        forces=_rowset([("C1",s,"C1-1",s,"G","Single Value",0.,-300.,50.,0.,0.,0.,0.)
                        for s in (0.,3.)])
        r=_compute_capacity_shear_axes(uid="C1",col_frame={"axes_global":[[0,0,1],[1,0,0],[0,1,0]]},ln_m=3.,
            scwb_joints=joints,stations=[],static_combos=["G"],rowset=forces,section=None,use_engineer=False,vr_lookup=lambda *x:(1000.,1000.))
        self.assertAlmostEqual(r["V2"]["max_ve_scwb_scenario_kn"],2*1.4*500/3)
        self.assertEqual(r["V2"]["cases"][0]["vd_floor_kn"],50.)
        self.assertEqual(r["V2"]["cases"][0]["mp_i_basis"],"UNREDUCED_7_3_7_3_NO_ANALYSIS_MOMENT_SHARE")
    def test_spectral_only_seismic_group_does_not_use_gravity_for_alpha(self):
        frames={c:{"frame_id":c,"story":"S1","axes_global":[[0,0,1],[1,0,0],[0,1,0]]} for c in ("C1","C2")}
        ax={"combination_plan":{"source":"ASSIGNED_DESIGN","design_assignment":{"groups":{"gravity":["G"],"ductile":["EX","EY"]}},
            "combinations":[{"name":"G","force_semantics":"STATIC_SIGNED_VECTOR"}]+[{"name":n,"force_semantics":"SCALAR_COMPONENT_ENVELOPE"} for n in ("EX","EY")]}}
        r=_evaluate_story_alpha_summary(frames=frames,all_target_cols=list(frames.values()),evaluated_uids=list(frames),scwb_joints=[],force_rowsets={},axial=ax,use_engineer_selection=False)
        self.assertIsNone(r)

class SnapshotContracts(unittest.TestCase):
    def setUp(self): self.temp=TemporaryDirectory(); self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def make_run(self,raw=b'{}',selected=.01,sealed=True):
        from hashlib import sha256
        run=ReceiptRun(self.root); h=sha256(raw).hexdigest(); run.archive_input(raw,expected_sha256=h)
        if sealed:
            run.record("schema-discovery", {}, input_sha256=h, receipt_schema=SCHEMA)
        run.record("modal",{"value":1},input_sha256=h)
        if sealed:
            result = dict.fromkeys(REQUIRED_KEYS)
            result.update(r10_live={"selected_min_rho": selected}, report_evidence={})
            link = record_snapshot(run, input_sha=h, results=result, registry=[])
            run.record("live-capture", {"engine_snapshot": link}, input_sha256=h)
        return run,h
    def test_identical_complete_recorded_stage_sets_compare_identical(self):
        a,_=self.make_run(); b,_=self.make_run()
        self.assertEqual(compare_runs(a.root,b.root)["status"],"IDENTICAL")
    def test_changed_selected_cage_result_cannot_compare_identical(self):
        a,_=self.make_run(selected=.01); b,_=self.make_run(selected=.02)
        r=compare_runs(a.root,b.root)
        self.assertEqual(r["status"],"DIFFERENT"); self.assertIn("engine-results",r["mismatched_stages"])
    def test_source_change_visible_even_if_old_stage_payloads_equal(self):
        a,_=self.make_run(raw=b'{}'); b,_=self.make_run(raw=b'{"different":true}')
        self.assertEqual(compare_runs(a.root,b.root)["status"],"DIFFERENT")
    def test_method_change_visible_with_identical_numbers(self):
        a,_=self.make_run()
        with patch("tbdy_next.engineering.pipeline_snapshot.method_fingerprint",return_value={"package_sha256":"changed"}): b,_=self.make_run()
        self.assertEqual(compare_runs(a.root,b.root)["status"],"DIFFERENT")
    def test_legacy_comparison_never_claims_complete_identity(self):
        a,_=self.make_run(sealed=False); b,_=self.make_run(sealed=False)
        self.assertEqual(compare_runs(a.root,b.root)["status"],"LEGACY_PARTIAL_COMPARISON")
    def test_extra_receipt_invalidates_the_sealed_inventory(self):
        a,_=self.make_run(); b,h=self.make_run(); b.record("extra",{"v":1},input_sha256=h)
        with self.assertRaises(ValueError):
            compare_runs(a.root, b.root)
    def test_snapshot_tamper_fails_instead_of_falling_back(self):
        a,h=self.make_run(); p=next(a.root.glob("*-engine-results.json")); value=json.loads(p.read_text()); value["payload"]["results"]["r10_live"]={"changed":True};p.write_text(json.dumps(value))
        with self.assertRaises(ValueError): read_snapshot(a.root,input_sha=h)
    def test_nonfinite_results_cannot_be_sealed(self):
        run,h=self.make_run(sealed=False); r={k:None for k in REQUIRED_KEYS};r["result"]={"value":math.nan}
        r["report_evidence"] = {}
        with self.assertRaises(ValueError): record_snapshot(run,input_sha=h,results=r,registry=[])

if __name__=="__main__": unittest.main()
