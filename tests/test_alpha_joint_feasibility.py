"""Final alpha consumes recorded joint scope/results, not just column PMM/Ve.

The panel/tie outcomes below come from the existing R13 adapter. PMM/Ve inputs
are explicit consumer fixtures, not an independent whole-building calculation.
"""
from copy import deepcopy
import unittest
from unittest.mock import Mock

from tbdy_next.column_engine.joint_kernel import joint_transverse_reference
from tbdy_next.engineering.alpha_iteration import _feasibility, run_bounded_feedback
from tbdy_next.reporting import _alpha_feedback_html
import test_r13_joint_adapters as joint_adapter


def attach_reference_joint_results(dependencies, r10, combinations):
    """Explicit upward/orthogonal recorded-result fixture for driver-only tests."""
    for uid, member in dependencies["members"].items():
        ends = []
        for end_name, point in zip(("I", "J"), member["joint_ids"]):
            joint = dependencies["joints"][point]
            faces = dict.fromkeys(("2+", "2-", "3+", "3-"))
            for face, beam in zip(faces, joint["beam_ends"]):
                faces[face] = {"frame_id": beam["member_id"], "native_end": beam["end"]}
            end = {"member_id": uid, "end": end_name, "point_id": point, "faces": faces, "axes": [],
                   "status": "NO_RECORDED_BEAM_AT_NODE"}
            if joint["beam_ends"]:
                end["status"] = "JOINT_GEOMETRIC_REFERENCES_CALCULATED"
                lower = [c for c in joint["column_ids"] if dependencies["members"][c]["joint_ids"][1] == point]
                upper = [c for c in joint["column_ids"] if dependencies["members"][c]["joint_ids"][0] == point]
                for axis, direction in (("V2", [1., 0., 0.]), ("V3", [0., 1., 0.])):
                    entry = {"axis": axis, "calculation": None}
                    if faces[axis[-1] + "+"] or faces[axis[-1] + "-"]:
                        entry["calculation"] = {"geometric_limit_kn": 1000.}
                        entry["joint_shear_ve"] = {
                            "status": "JOINT_SHEAR_VE_CALCULATED_NOT_PROVEN", "target_axis": axis,
                            "global_direction": direction, "upper_column_ids": upper, "lower_column_ids": lower,
                            "column_topology_issues": [], "expected_seismic_combinations": list(combinations),
                            "column_shear_cases": [{"combination": c, "status": "BOUND" if upper else "ROOF_ZERO_BOUNDARY",
                                "deduction_kn": 0., "missing_column_ids": []} for c in combinations],
                            "column_shear_scope_complete": True, "missing_column_shear_combinations": [],
                            "v_kol_basis": "MIN_UPPER_LOWER_COLUMN_SHEAR" if upper else "ROOF_JOINT_NO_UPPER_COLUMN_VKOL_ZERO",
                            "v_kol_applicability": "CONDITIONAL_NONNEGATIVE_DEDUCTION_FOR_QUALIFIED_SWAY_MECHANISM",
                            "v_kol_used_kn": 0., "sway_a_ve_kn": 100., "sway_b_ve_kn": 100.,
                            "governing_ve_kn": 100., "geometric_limit_kn": 1000.,
                            "utilization": .1, "within_geometric_limit": True}
                        entry["joint_transverse_7_5_2_3"] = {
                            "status": "JOINT_TRANSVERSE_REFERENCES_CALCULATED_NOT_PROVEN",
                            "target_axis": axis, "global_direction": direction, "lower_column_id": lower[0],
                            "lower_axis": axis, "axis_mapping_status": "PHYSICAL_AXIS_BOUND",
                            "column_topology_issues": [], "lower_column_has_confinement_calc": True,
                            **joint_transverse_reference(lower_required_ash_mm2=100., lower_spacing_mm=100.,
                                proposed_ash_mm2=200., joint_spacing_mm=100., tie_diameter_mm=10., enclosure="UNENCLOSED")}
                    end["axes"].append(entry)
            ends.append(end)
        r10["per_member"][uid]["member_joint_ends"] = ends


def state_with_actual_joint(fixture=None, **calculate):
    fixture = fixture or joint_adapter.JointAdapterInvariantTests()
    if not hasattr(fixture, "frames"):
        fixture.setUp()
    axis = fixture.calculate(**calculate)
    members = {uid: {"joint_ids": [f["point_i"], f["point_j"]]} for uid, f in fixture.frames.items()}
    points = sorted({p for row in members.values() for p in row["joint_ids"]})
    joints = {p: {"joint_id": p, "column_ids": [u for u, m in members.items() if p in m["joint_ids"]],
                  "execution_allowed": True, "beam_ends": [{"member_id": b, "end": "I"}
                    for b in ("B+", "B-")] if p == "J" else []} for p in points}
    state = {"dependencies": {"members": members, "joints": joints}, "revision": None,
             "required_signed_combinations": ["E1", "E2"], "required_seismic_combinations": ["E1", "E2"],
             "r10": {"per_member": {}}, "r08": {"per_member": {}}}
    for uid in members:
        state["r10"]["per_member"][uid] = {"engineer_column_selection": {"selected": {"label": "fixture"}},
            "column_transverse_and_shear": {"engineer_capacity_shear_ve": {"axes": {
                a: {"max_utilization_ts500": .5, "cases": [{"combination": c, "ve_scwb_scenario_kn": 50.,
                    "vr_ts500_min_kn": 100., "utilization_ts500": .5} for c in ("E1", "E2")]} for a in ("V2", "V3")}}}}
        state["r08"]["per_member"][uid] = {"magnified_selected_pmm": {
            "status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN", "global_beta_ii_factor": 1.,
            "expected_row_count": 1, "evaluated_row_count": 1, "resolved_row_count": 1, "max_utilization": .5}}
    attach_reference_joint_results(state["dependencies"], state["r10"], ["E1", "E2"])
    for detail in state["r10"]["per_member"].values():
        for end in detail["member_joint_ends"]:
            if end["point_id"] == "J":
                end["axes"][0] = deepcopy(axis)
    return state


def framed_axis(state, uid="U"):
    return next(e for e in state["r10"]["per_member"][uid]["member_joint_ends"] if e["point_id"] == "J")["axes"][0]


class JointFinalFeasibilityContracts(unittest.TestCase):
    def test_no_candidate_preserves_other_joint_failures_and_missing_dependencies_in_either_order(self):
        state = state_with_actual_joint(shear_e2=0.)
        members = state["dependencies"]["members"]
        members["MISSING"] = {}
        state["r10"]["per_member"]["U"]["engineer_column_selection"] = {
            "status": "ENGINEER_COLUMN_SELECTION_NO_PASSING_CAGE", "selected": None}
        for order in (list(members), list(reversed(members))):
            with self.subTest(order=order):
                state["dependencies"]["members"] = {uid: members[uid] for uid in order}
                result = _feasibility(state)
                self.assertEqual(result["status"], "JOINT_DESIGN_FAILURE")
                self.assertEqual(result["no_feasible_candidate_member_ids"], ["U"])
                self.assertEqual(result["reselect_member_ids"], [])
                self.assertIn("U:NO_FEASIBLE_CANDIDATE", result["failure_codes"])
                self.assertIn("L:J:V2:JOINT_SHEAR_LIMIT_EXCEEDED", result["failure_codes"])
                self.assertIn("MISSING:SELECTED_CAGE_UNAVAILABLE", result["reason_codes"])
                html = _alpha_feedback_html({"status": result["status"], "final_feasibility": result})
                for reason in result["failure_codes"] + result["reason_codes"]:
                    self.assertIn(reason, html)

    def test_each_exhausted_candidate_family_remains_in_the_terminal_outcome(self):
        state = state_with_actual_joint()
        for member in state["r10"]["per_member"].values():
            member["engineer_column_selection"] = {"status": "ENGINEER_COLUMN_SELECTION_NO_PASSING_CAGE"}
        result = _feasibility(state)
        expected = sorted(state["dependencies"]["members"])
        self.assertEqual(result["status"], "NO_FEASIBLE_CANDIDATE")
        self.assertEqual(result["member_id"], expected[0])
        self.assertEqual(result["no_feasible_candidate_member_ids"], expected)
        self.assertEqual(result["failure_codes"], [uid + ":NO_FEASIBLE_CANDIDATE" for uid in expected])

    def test_actual_joint_and_tie_success_can_complete_reference_feasibility(self):
        state = state_with_actual_joint()
        before = deepcopy(state)
        result = _feasibility(state)
        self.assertEqual(result["status"], "FEASIBLE_REFERENCE")
        self.assertEqual(result["reselect_member_ids"], [])
        self.assertEqual(state, before)

    def test_missing_or_changed_physical_scope_cannot_become_an_exemption(self):
        for kind in ("missing_end", "duplicate_end", "wrong_point", "missing_joint", "missing_face", "no_beam_claim", "dropped_beam", "missing_axis", "duplicate_axis"):
            state = state_with_actual_joint()
            ends = state["r10"]["per_member"]["U"]["member_joint_ends"]
            if kind == "missing_end": ends.pop()
            elif kind == "duplicate_end": ends[1] = deepcopy(ends[0])
            elif kind == "wrong_point": ends[0]["point_id"] = "OTHER"
            elif kind == "missing_joint": state["dependencies"]["joints"].pop("J")
            elif kind == "missing_face": ends[0]["faces"].pop("3-")
            elif kind == "no_beam_claim": ends[0].update(status="NO_RECORDED_BEAM_AT_NODE", axes=[])
            elif kind == "dropped_beam": ends[0]["faces"]["2+"] = None
            elif kind == "missing_axis": ends[0]["axes"].pop(0)
            else: ends[0]["axes"].append(deepcopy(ends[0]["axes"][0]))
            with self.subTest(kind=kind):
                self.assertEqual(_feasibility(state)["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")

    def test_missing_unbound_or_nonfinite_panel_and_tie_results_block(self):
        for key in ("joint_shear_ve", "joint_transverse_7_5_2_3"):
            for value in (None, {}, {"status": "UNBOUND"}, "not-a-record"):
                state = state_with_actual_joint(); framed_axis(state)[key] = value
                with self.subTest(key=key, value=value):
                    self.assertEqual(_feasibility(state)["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")
        for key, field in (("joint_shear_ve", "utilization"), ("joint_shear_ve", "governing_ve_kn"),
                           ("joint_transverse_7_5_2_3", "proposed_ash_mm2")):
            state = state_with_actual_joint(); framed_axis(state)[key][field] = float("nan")
            with self.subTest(field=field):
                self.assertEqual(_feasibility(state)["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")

    def test_expected_seismic_scope_is_not_inferred_from_successful_results(self):
        for kind in ("missing_expected_input", "shortened_expected", "missing_case", "duplicate_case"):
            state = state_with_actual_joint(); shear = framed_axis(state)["joint_shear_ve"]
            if kind == "missing_expected_input": state.pop("required_seismic_combinations")
            elif kind == "shortened_expected": shear["expected_seismic_combinations"] = ["E1"]
            elif kind == "missing_case": shear["column_shear_cases"].pop()
            else: shear["column_shear_cases"][1] = deepcopy(shear["column_shear_cases"][0])
            with self.subTest(kind=kind):
                self.assertEqual(_feasibility(state)["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")

    def test_proven_panel_failure_terminates_without_automatic_cage_reselection(self):
        state = state_with_actual_joint(shear_e2=0.)
        result = _feasibility(state)
        self.assertEqual(result["status"], "JOINT_DESIGN_FAILURE")
        self.assertEqual(result["reselect_member_ids"], [])
        self.assertTrue(any("JOINT_SHEAR_LIMIT_EXCEEDED" in code for code in result["failure_codes"]))
        qualify = Mock(side_effect=AssertionError("known joint failure must terminate before alpha"))
        rebuild = Mock(side_effect=AssertionError("joint failure must not reselect the column"))
        _, record = run_bounded_feedback(initial=state, qualify=qualify, demand=None,
            rebuild=rebuild, signature=None, feasible=_feasibility)
        self.assertEqual(record["status"], "JOINT_DESIGN_FAILURE")
        self.assertFalse(record["feedback_consumed"])
        self.assertEqual(record["iteration_count"], 0)
        qualify.assert_not_called(); rebuild.assert_not_called()
        # A simultaneous unresolved dependency must not hide the proved joint
        # failure in the sealed-result report.
        mixed = deepcopy(state)
        mixed["r08"]["per_member"]["U"]["magnified_selected_pmm"].pop("global_beta_ii_factor")
        mixed_result = _feasibility(mixed)
        self.assertEqual(mixed_result["status"], "JOINT_DESIGN_FAILURE")
        self.assertTrue(mixed_result["reason_codes"])
        html = _alpha_feedback_html({**record, "final_feasibility": mixed_result})
        for reason in (*mixed_result["failure_codes"], *mixed_result["reason_codes"]):
            self.assertIn(reason, html)

    def test_proven_tie_failure_is_not_a_fixed_point(self):
        fixture = joint_adapter.JointAdapterInvariantTests(); fixture.setUp()
        fixture.selections["L"]["selected"]["selected_transverse"]["confinement_v2"]["ash_mm2"] = 100.
        result = _feasibility(state_with_actual_joint(fixture))
        self.assertEqual(result["status"], "JOINT_DESIGN_FAILURE")
        self.assertEqual(result["reselect_member_ids"], [])
        self.assertTrue(any("JOINT_TRANSVERSE_REFERENCE_FAILED" in code for code in result["failure_codes"]))

    def test_passing_qualified_zero_bound_does_not_need_a_favorable_deduction(self):
        fixture = joint_adapter.JointAdapterInvariantTests(); fixture.setUp()
        for beam in fixture.beams.values():
            beam["ends"]["I"]["engineer_selection"].update(area_top_mm2=500., area_bottom_mm2=500.)
        self.assertEqual(_feasibility(state_with_actual_joint(fixture, force_rows={}))["status"], "FEASIBLE_REFERENCE")

    def test_exceeded_unresolved_zero_bound_requires_refinement_not_proven_failure(self):
        result = _feasibility(state_with_actual_joint(force_rows={}))
        self.assertEqual(result["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")
        self.assertEqual(result["failure_codes"], [])
        self.assertTrue(any("JOINT_SHEAR_BOUND_REFINEMENT_REQUIRED" in code for code in result["reason_codes"]))

    def test_unknown_lower_physical_side_is_not_a_passing_bound(self):
        fixture = joint_adapter.JointAdapterInvariantTests(); fixture.setUp()
        del fixture.points["P0"]
        result = _feasibility(state_with_actual_joint(fixture))
        self.assertEqual(result["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")
        self.assertEqual(result["failure_codes"], [])

    def test_defined_roof_zero_exceedance_remains_a_failure(self):
        fixture = joint_adapter.JointAdapterInvariantTests(); fixture.setUp()
        del fixture.frames["U"]
        fixture.adjacency["J"] = [fixture.adjacency["J"][0]]
        fixture.end_row.update(member_id="L", end="J")
        self.assertEqual(_feasibility(state_with_actual_joint(fixture, force_rows={}))["status"], "JOINT_DESIGN_FAILURE")


if __name__ == "__main__":
    unittest.main()
