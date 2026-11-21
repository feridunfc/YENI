"""Scoped applicability consumers; explicit PMM/Ve fixtures are not a design oracle."""
from copy import deepcopy
import unittest

from test_alpha_joint_feasibility import attach_reference_joint_results
from test_alpha_design_iteration import two_columns
from test_story_alpha_applicability import population
from tbdy_next.engineering.alpha_iteration import _feasibility, qualify_story_alpha, run_bounded_feedback
from tbdy_next.engineering.design_dependencies import _stories_without_alpha
from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.scwb_axial import assigned_story_applicability


def reference_state():
    source, scope, plan, r10 = population()
    state = {"dependencies": plan, "r10": r10, "r08": {"per_member": {}}, "revision": None,
             "required_signed_combinations": ["G"], "required_seismic_combinations": ["E"]}
    for jid, joint in plan["joints"].items():
        joint["joint_id"] = jid
    for uid in plan["members"]:
        r10["per_member"][uid].update(engineer_column_selection={"selected": {"label": "consumer-fixture"}},
            column_transverse_and_shear={"engineer_capacity_shear_ve": {"axes": {
                a: {"max_utilization_ts500": .5, "cases": [{"combination": "G", "ve_scwb_scenario_kn": 50.,
                     "vr_ts500_min_kn": 100., "utilization_ts500": .5}]} for a in ("V2", "V3")}}})
        state["r08"]["per_member"][uid] = {"magnified_selected_pmm": {
            "status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN", "global_beta_ii_factor": 1.,
            "expected_row_count": 1, "evaluated_row_count": 1, "resolved_row_count": 1, "max_utilization": .5}}
    attach_reference_joint_results(plan, r10, ["E"])
    return source, scope, state


def applicability_record(source, scope, state):
    plan = state["dependencies"]
    def qualify(current):
        rows = assigned_story_applicability(source, scope, plan, current["r10"], ["E"])
        return {"status": "ALTERNATIVE_NOT_REQUIRED", "reason_codes": [], "cases": [], "story_applicability": rows}
    _, record = run_bounded_feedback(initial=state, qualify=qualify, demand=None,
        rebuild=None, signature=None, feasible=_feasibility)
    record.update(source_payload_sha256=plan["source_payload_sha256"], final_feasibility=_feasibility(state),
                  required_seismic_combinations=["E"])
    return record


class ScopedAlphaApplicabilityTests(unittest.TestCase):
    def test_signed_roof_and_beamless_source_uses_actual_physical_applicability_owner(self):
        source, scope, plan, r10 = population()
        axial = two_columns()[1]
        qualification = qualify_story_alpha(source, axial, scope, plan, r10)
        self.assertEqual(qualification["status"], "ALTERNATIVE_NOT_REQUIRED")
        self.assertEqual(qualification["cases"], [])
        self.assertEqual(len(qualification["story_applicability"]), 2)
        self.assertTrue(all(row["expected_member_ids"] == ["C1", "C2"] for row in qualification["story_applicability"]))

    def test_required_interior_end_without_capacity_is_not_a_roof_default(self):
        source, scope, plan, r10 = population()
        tables = source["geometry_capture"]["tables"]
        tables["FRAME_ASSIGNMENTS"]["rows"].append(dict(UniqueName="C3", Type="Column", AnalysisSect="Rect", AxisAngle="0", Story="Upper"))
        tables["COLUMN_CONNECTIVITY"]["rows"].append(dict(UniqueName="C3", Story="Upper", UniquePtI="C1J", UniquePtJ="C3J", Length="3"))
        source["vs05_delta_source"]["table_reads"]["Point Object Connectivity"]["rows"].append(
            dict(UniqueName="C3J", X="0", Y="0", Z="6"))
        source["column_axial"]["force_source"]["rowsets"]["C3"] = rows = deepcopy(source["column_axial"]["force_source"]["rowsets"]["C1"])
        rows["Obj"] = ["C3"] * rows["NumberResults"]
        rows["Elm"] = ["C3-1"] * rows["NumberResults"]
        scope["configured_output_cuts"]["C3"] = deepcopy(scope["configured_output_cuts"]["C1"])
        for cut in scope["configured_output_cuts"]["C3"]["cuts"]:
            cut["analysis_element_id"] = "C3-1"
        plan["members"]["C3"] = {"story": "Upper", "joint_ids": ["C1J", "C3J"], "reason_codes": [],
                                    "source_execution_allowed": True, "selected_candidate_bound": True}
        plan["story_columns"]["Upper"] = ["C3"]
        plan["joints"]["C1J"]["column_ids"] = ["C1", "C3"]
        plan["joints"]["C3J"] = {"column_ids": ["C3"], "beam_ends": [], "blockers": [], "execution_allowed": True}
        r10["per_member"]["C3"] = {"scwb_joints": []}
        plan["source_payload_sha256"] = _digest(source)
        rows = assigned_story_applicability(source, scope, plan, r10, ["Q"])
        self.assertTrue(any(e["member_id"] == "C3" and e["end"] == "I" and e["disposition"] == "UNRESOLVED"
                            for row in rows for e in row["ends"]))
        qualification = qualify_story_alpha(source, two_columns()[1], scope, plan, r10)
        self.assertEqual(qualification["status"], "BLOCKED_INPUTS")
        self.assertTrue(any("TWO_END_SCWB" in reason for reason in qualification["reason_codes"]))

    def test_missing_coupled_member_pmm_preserves_applicability_and_blocks_global_feasibility(self):
        source, scope, state = reference_state()
        before = applicability_record(source, scope, state)
        self.assertEqual(before["status"], "ALTERNATIVE_NOT_REQUIRED")
        self.assertEqual(_stories_without_alpha(before, state["dependencies"]), {"Zemin"})
        state["r08"]["per_member"]["C2"] = {"status": "WALL_FRAME_EFFECTIVE_LENGTH_REQUIRES_COUPLED_MODEL"}
        after = applicability_record(source, scope, state)
        self.assertEqual(after["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")
        self.assertFalse(after["feedback_consumed"])
        self.assertTrue(any(s.startswith("C2:") for s in after["final_feasibility"]["reason_codes"]))
        self.assertEqual(_stories_without_alpha(after, state["dependencies"]), {"Zemin"})
        self.assertEqual(sorted(state["dependencies"]["members"]), ["C1", "C2"])
        self.assertEqual(state["dependencies"]["story_columns"]["Zemin"], ["C1", "C2"])

    def test_reselection_does_not_reclassify_applicability(self):
        source, scope, state = reference_state()
        state["r08"]["per_member"]["C2"]["magnified_selected_pmm"].update(
            status="MAGNIFIED_PMM_EXCEEDS_CAPACITY", max_utilization=1.2)
        record = applicability_record(source, scope, state)
        self.assertEqual(record["status"], "RESELECTION_REQUIRED")
        self.assertEqual(record["final_feasibility"]["reselect_member_ids"], ["C2"])
        self.assertEqual(_stories_without_alpha(record, state["dependencies"]), {"Zemin"})

    def test_missing_case_end_direction_or_cross_source_cannot_waive_alpha(self):
        source, scope, state = reference_state()
        good = applicability_record(source, scope, state)
        for defect in ("source", "case", "end", "direction", "cage", "demand", "unknown_story"):
            with self.subTest(defect=defect):
                record, plan = deepcopy(good), deepcopy(state["dependencies"])
                rows = record["final_qualification"]["story_applicability"]
                if defect == "source": record["source_payload_sha256"] = "another-source"
                elif defect == "case": record["required_seismic_combinations"].append("E2")
                elif defect == "end": rows[0]["ends"].pop()
                elif defect == "direction": rows.pop()
                elif defect == "cage": plan["members"]["C2"]["selected_candidate_bound"] = False
                elif defect == "demand": rows[0]["applied_demand_factor"] = 1.2
                else: rows[0]["story"] = "unknown"
                self.assertEqual(_stories_without_alpha(record, plan), set())

    def test_other_story_incomplete_applicability_does_not_remove_complete_story(self):
        source, scope, state = reference_state()
        record = applicability_record(source, scope, state)
        plan = state["dependencies"]
        plan["story_columns"]["Other"] = ["C3"]
        plan["members"]["C3"] = {"joint_ids": ["C3I", "C3J"], "source_execution_allowed": True,
                                   "selected_candidate_bound": True}
        record["assigned_story_applicability"] = record["final_qualification"]["story_applicability"] + [
            {"story": "Other", "direction": "X", "status": "UNRESOLVED", "ends": []}]
        self.assertEqual(_stories_without_alpha(record, plan), {"Zemin"})

    def test_no_alpha_reselection_uses_same_bounded_driver_without_scaling(self):
        calls = []
        def rebuild(state, revision, changed):
            calls.append((revision["factors"], changed))
            return {"revision": revision, "candidate": 2}, {"selected_member_ids": changed}
        _, record = run_bounded_feedback(initial={"candidate": 1},
            qualify=lambda s: {"status": "ALTERNATIVE_NOT_REQUIRED", "cases": [], "reason_codes": []},
            demand=lambda cases: {"factors": {}, "sha256": "identity"}, rebuild=rebuild,
            signature=lambda s: {"C1": s["candidate"]},
            feasible=lambda s: {"status": "FEASIBLE_REFERENCE", "reselect_member_ids": ["C1"] if s["candidate"] == 1 else []})
        self.assertEqual(calls, [({}, ["C1"])])
        self.assertEqual(record["status"], "ALTERNATIVE_NOT_REQUIRED")
        self.assertEqual(record["iteration_count"], 1)
        self.assertEqual(record["trace"][0]["mode"], "NATIVE_DEMAND_DESIGN_RESELECTION")
        self.assertFalse(record["feedback_consumed"])

    def test_no_alpha_reselection_cannot_loop_or_hide_unresolved_dependencies(self):
        for blocked, expected in ((False, "NO_CONVERGENCE_CYCLE"), (True, "NUMERIC_OR_DEPENDENCY_UNRESOLVED")):
            with self.subTest(blocked=blocked):
                _, record = run_bounded_feedback(initial={},
                    qualify=lambda s: {"status": "ALTERNATIVE_NOT_REQUIRED", "cases": []},
                    demand=lambda cases: {"factors": {}, "sha256": "identity"},
                    rebuild=lambda s, r, c: ({"revision": r}, {}), signature=lambda s: {"C": "same-cage"},
                    feasible=lambda s: {"status": "NUMERIC_OR_DEPENDENCY_UNRESOLVED" if blocked else "FEASIBLE_REFERENCE",
                                        "reselect_member_ids": ["C"]})
                self.assertEqual(record["status"], expected)
                self.assertFalse(record["feedback_consumed"])


if __name__ == "__main__":
    unittest.main()
