from contextlib import closing
from copy import deepcopy
import math
import unittest

from column_kinematics_fixture import KinematicsBank, DISPLACEMENTS, STATIC
from tbdy_next.column_engine.native_archive import NativeArchive, BankError
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.column_prechecks import build_column_prechecks
from tbdy_next.column_engine.column_pmm import build_column_cages
from tbdy_next.column_engine.column_transverse import build_column_transverse
from tbdy_next.column_engine.column_joints import build_column_joints
from tbdy_next.column_engine.column_kinematics import build_column_kinematics, kinematic_summaries
from tbdy_next.column_engine.kinematics_kernel import joint_chord_kinematics


def inputs(raw, archive):
    bank = recover_column_bank(raw)
    chain = build_demand_chain(bank, archive)
    pre = build_column_prechecks(bank, chain)
    cages = build_column_cages(bank, chain, pre, archive)
    ties = build_column_transverse(chain, cages, archive)
    return bank, chain, build_column_joints(bank, chain, cages, ties, archive)


def package(fixture=None):
    raw = (fixture or KinematicsBank()).build()
    with closing(NativeArchive(raw)) as archive:
        bank, chain, joints = inputs(raw, archive)
        return build_column_kinematics(bank, chain, joints, archive)


class ChordKernelTests(unittest.TestCase):
    def compute(self, **changes):
        args = dict(axes_global=[[0, 0, 1], [1, 0, 0], [0, 1, 0]], length_m=4,
            u_i=[0, 0, 0], u_j=[.008, -.006, 0], r_i=[.0015, .002, 0], r_j=[.0015, .002, 0])
        return joint_chord_kinematics(**(args | changes))

    def test_independent_rigid_rotation_oracle_and_cross_product_signs(self):
        r = self.compute()
        self.assertEqual(r["delta_local_m"], [0, .008, -.006])
        self.assertEqual(r["chord_alpha2_rad"], .0015)
        self.assertEqual(r["chord_alpha3_rad"], .002)
        for end in ("i", "j"):
            for axis in (2, 3):
                self.assertEqual(r[f"joint_{end}_relative_r{axis}_rad"], 0)

    def test_global_rigid_rotation_and_translation_do_not_change_local_answer(self):
        # Rotate all geometry and vectors 90 degrees about Global Z.
        r = self.compute(axes_global=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
            u_i=[.1, -.2, .003], u_j=[.106, -.192, .003], r_i=[-.002, .0015, 0], r_j=[-.002, .0015, 0])
        self.assertAlmostEqual(r["chord_alpha2_rad"], .0015)
        self.assertAlmostEqual(r["chord_alpha3_rad"], .002)
        self.assertAlmostEqual(r["joint_i_relative_r2_rad"], 0)
        self.assertAlmostEqual(r["joint_j_relative_r3_rad"], 0)

    def test_reversed_ij_with_right_handed_basis_preserves_zero_relative_rotations(self):
        r = self.compute(axes_global=[[0, 0, -1], [1, 0, 0], [0, -1, 0]],
            u_i=[.008, -.006, 0], u_j=[0, 0, 0])
        self.assertEqual(r["chord_alpha2_rad"], .0015)
        self.assertEqual(r["chord_alpha3_rad"], -.002)
        self.assertEqual(r["joint_i_relative_r2_rad"], 0)
        self.assertEqual(r["joint_j_relative_r3_rad"], 0)

    def test_nodal_rotation_difference_is_not_discarded_or_absed(self):
        r = self.compute(r_i=[-.001, .003, 0], r_j=[.002, -.001, 0])
        self.assertAlmostEqual(r["joint_i_relative_r2_rad"], -.0025)
        self.assertAlmostEqual(r["joint_i_relative_r3_rad"], .001)
        self.assertAlmostEqual(r["joint_j_relative_r2_rad"], .0005)
        self.assertAlmostEqual(r["joint_j_relative_r3_rad"], -.003)

    def test_invalid_length_vectors_reflections_and_overflow_are_rejected(self):
        for change in ({"length_m": 0}, {"length_m": -1}, {"u_i": [0, 0]}, {"r_j": [math.nan, 0, 0]},
            {"u_i": [True, 0, 0]}, {"axes_global": [[0, 0, 1], [2, 0, 0], [0, 1, 0]]},
            {"axes_global": [[0, 0, 1], [1, 0, 0], [0, -1, 0]]},
            {"u_i": [-1e308, 0, 0], "u_j": [1e308, 0, 0]}):
            with self.subTest(change=change), self.assertRaises(BankError):
                self.compute(**change)


class ColumnKinematicsTests(unittest.TestCase):
    def test_complete_pair_keeps_signed_six_vectors_and_distinct_node_cut_lengths(self):
        r = package()
        self.assertEqual(r["expected_member_case_count"], 2)
        self.assertEqual(r["linked_member_case_count"], 2)
        p = r["rows"][0]["force_pair"]
        self.assertEqual(p["i"]["native_values"], dict(P=-180, V2=10.8, V3=-18.4, T=2.6, M2=48, M3=-57.2))
        self.assertEqual(p["j"]["native_values"], dict(P=-720, V2=43.2, V3=-73.6, T=10.4, M2=192, M3=-228.8))
        self.assertEqual(p["i"]["native_key"]["Elm"], "C_SYNTHETIC_1A")
        self.assertEqual(p["j"]["native_key"]["Elm"], "C_SYNTHETIC_1B")
        self.assertEqual(p["object_i_j_length_m"], 4)
        self.assertEqual(p["output_cut_span_m"], 3.3)
        self.assertFalse(p["j_cut_at_joint_coordinate"])
        self.assertFalse(p["output_cuts_are_physical_support_faces"])
        self.assertTrue(p["interior_states_retained_in_demand_chain"])

    def test_table_point_identity_raw_precision_and_source_indices_are_preserved(self):
        r = package(); row = r["rows"][0]; j = row["joint_j"]
        self.assertEqual(j["point_id"], "P1")
        self.assertEqual(j["raw"]["Label"], "UNRELATED_LABEL")
        self.assertEqual(j["raw"]["Ux"], ".108000")
        self.assertEqual(j["source_row_index"], 1)
        self.assertEqual(len(j["source_row_id"]), 64)
        self.assertEqual(row["point_i"], "P0")
        self.assertAlmostEqual(row["calculation"]["chord_alpha2_rad"], .0015)
        self.assertAlmostEqual(row["calculation"]["chord_alpha3_rad"], .002)
        self.assertAlmostEqual(row["calculation"]["joint_i_relative_r3_rad"], 0)
        self.assertFalse(r["displacement_table_source"]["zero_value_proves_zero_motion"])

    def test_pdelta_and_literal_none_never_issue_first_order_or_magnification(self):
        r = package(); cases = {c["case_name"]: c for c in r["analysis_basis"]["cases"]}
        self.assertEqual(cases["G"]["nonlinear_case_raw"], "None")
        self.assertEqual(cases["G"]["status"], "RECORDED_NONLINEAR_CASE_UNRESOLVED")
        self.assertEqual(cases["Q"]["status"], "RECORDED_PDELTA_STIFFNESS")
        self.assertEqual(len(cases["Q"]["recorded_rows"]), 2)
        for key in ("cm", "beta", "magnified_design_moments", "ts500_sway_phi", "effective_length_factor", "selected_design"):
            self.assertIsNone(r[key])
        self.assertEqual(r["analysis_order"], "NOT_PROVEN")
        self.assertFalse(r["actual_second_order_applied"])
        self.assertEqual(r["design_demand_authority"], "DENIED")
        self.assertEqual(r["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(r["engineering_release"], "NOT_READY")

    def test_conflicting_stiffness_definitions_are_not_resolved_by_first_row(self):
        f = KinematicsBank(); f.static_rows.append(dict(Name="G", StiffType="P-Delta", NonlinCase="None"))
        r = package(f); g = next(c for c in r["analysis_basis"]["cases"] if c["case_name"] == "G")
        self.assertEqual(g["reason"], "STATIC_STIFFNESS_METADATA_CONFLICT")
        self.assertIsNone(g["stiffness_type"])
        self.assertEqual(r["linked_member_case_count"], 2)

    def test_missing_stiffness_metadata_does_not_invent_analysis_order(self):
        f = KinematicsBank(); f.omitted.add(("DatabaseTables.GetTableForDisplayArray", "table", STATIC))
        r = package(f)
        self.assertEqual(r["analysis_basis"]["reason"], "STATIC_STIFFNESS_TABLE_NOT_OBSERVED")
        self.assertEqual(r["linked_member_case_count"], 2)
        self.assertEqual(r["analysis_order"], "NOT_PROVEN")

    def test_missing_one_point_preserves_expected_denominator_and_other_column(self):
        f = KinematicsBank(); f.displacement_rows = f.displacement_rows[1:]
        r = package(f)
        self.assertEqual(r["expected_member_case_count"], 2)
        self.assertEqual(r["bound_force_pair_count"], 2)
        self.assertEqual(r["linked_member_case_count"], 1)
        self.assertEqual(r["rows"][0]["kinematics_reason"], "JOINT_DISPLACEMENT_MISSING")
        self.assertIsNone(r["rows"][0]["joint_i"])

    def test_duplicate_point_case_is_ambiguous_even_when_cells_are_identical(self):
        f = KinematicsBank(); f.displacement_rows.append(deepcopy(f.displacement_rows[1]))
        r = package(f)
        self.assertEqual(r["linked_member_case_count"], 0)
        self.assertEqual(r["reason_counts"], {"JOINT_DISPLACEMENT_AMBIGUOUS": 2})

    def test_rs_envelope_and_numbered_steps_never_join_static_single_value(self):
        for field, value in (("CaseType", "LinRespSpec"), ("StepType", "Max"), ("StepNumber", "0"), ("StepLabel", "Stage1")):
            f = KinematicsBank(); f.displacement_rows[1][field] = value
            with self.subTest(field=field):
                r = package(f)
                self.assertEqual(r["linked_member_case_count"], 0)
                self.assertEqual(r["reason_counts"], {"JOINT_DISPLACEMENT_NOT_SINGLE_STATIC_COMBINATION": 2})

    def test_missing_table_and_wrong_units_block_only_kinematics(self):
        for mode in ("missing", "units"):
            f = KinematicsBank()
            if mode == "missing": f.omitted.add(("DatabaseTables.GetTableForDisplayArray", "table", DISPLACEMENTS))
            else: f.displacement_units["Ux"] = "mm"
            with self.subTest(mode=mode):
                r = package(f)
                self.assertEqual(r["bound_force_pair_count"], 2)
                self.assertEqual(r["calculated_kinematics_count"], 0)
                self.assertEqual(r["status_counts"], {"PARTIAL_SOURCE_LINK": 2})

    def test_non_numeric_and_nonfinite_cells_do_not_turn_into_zero(self):
        for value in (None, "", "NaN", "Infinity", "1E9999"):
            f = KinematicsBank(); f.displacement_rows[1]["Ux"] = value
            with self.subTest(value=value):
                r = package(f)
                self.assertEqual(r["calculated_kinematics_count"], 0)
                self.assertEqual(r["bound_force_pair_count"], 2)

    def test_missing_force_end_does_not_select_an_interior_maximum(self):
        f = KinematicsBank(); f.forces[f.members[0]] = [r for r in f.forces[f.members[0]] if r[1] != 3.3]
        r = package(f)
        self.assertEqual(r["bound_force_pair_count"], 1)
        self.assertEqual(r["calculated_kinematics_count"], 2)
        self.assertEqual(r["rows"][0]["force_reason"], "COLUMN_FORCE_END_NOT_RECORDED")

    def test_duplicate_end_elements_are_not_silently_selected(self):
        f = KinematicsBank(); rows = f.forces[f.members[0]]
        extra = deepcopy([r for r in rows if r[1] == 3.3])
        for row in extra: row[2] += "DUPLICATE_ELEMENT"
        rows.extend(extra)
        r = package(f)
        self.assertEqual(r["bound_force_pair_count"], 1)
        self.assertEqual(r["rows"][0]["force_reason"], "COLUMN_FORCE_END_AMBIGUOUS")

    def test_near_coincident_end_cuts_cannot_reuse_one_state_for_both_ends(self):
        # Independent review counterexample: both matching windows contain
        # the recorded station zero even though the nominal cuts differ.
        f = KinematicsBank()
        f.calls[("FrameObj.GetEndLengthOffset", "frame", f.members[0])]["raw_response"][2] = 4-5e-8
        r = package(f)
        self.assertEqual(r["bound_force_pair_count"], 1)
        self.assertEqual(r["calculated_kinematics_count"], 2)
        self.assertIsNone(r["rows"][0]["force_pair"])
        self.assertEqual(r["rows"][0]["force_reason"], "COLUMN_FORCE_END_MATCH_WINDOWS_OVERLAP")

    def test_global_transform_arguments_and_ij_orientation_must_be_bound(self):
        for mode in ("arguments", "direction"):
            f = KinematicsBank(); call = f.calls[("FrameObj.GetTransformationMatrix", "frame", f.members[0])]
            if mode == "arguments": call["args"][-1] = False
            else: call["raw_response"][0] = [0, 1, 0, 0, 0, -1, -1, 0, 0]
            with self.subTest(mode=mode):
                r = package(f)
                self.assertEqual(r["linked_member_case_count"], 1)
                self.assertEqual(r["rows"][0]["status"], "BLOCKED_INPUTS")

    def test_dependency_hash_and_run_mismatches_reject_the_entire_derivation(self):
        raw = KinematicsBank().build()
        with closing(NativeArchive(raw)) as a:
            b, c, j = inputs(raw, a)
            first = build_column_kinematics(b, c, j, a)
            self.assertEqual(first, build_column_kinematics(b, c, j, a))
            for key, value in (("source_run_id", "WRONG"), ("source_demand_result_sha256", "WRONG"),
                               ("source_archive_sha256", "WRONG"), ("axis_convention", "OLD")):
                bad = deepcopy(j); bad[key] = value
                with self.subTest(key=key), self.assertRaises(BankError): build_column_kinematics(b, c, bad, a)

    def test_summary_preserves_cut_and_node_identity_without_changing_numbers(self):
        r = package(); flat = kinematic_summaries(r)[0]
        self.assertEqual(flat["i_P"], -180)
        self.assertEqual(flat["j_M3"], -228.8)
        self.assertEqual(flat["point_j"], "P1")
        self.assertEqual(flat["j_station_m"], 3.3)
        self.assertAlmostEqual(flat["chord_alpha3_rad"], .002)

    def test_expanded_record_budget_is_explicit_bounded_and_only_for_regular_joints(self):
        f = KinematicsBank(); f.displacement_rows = [f.displacement_rows[0]]*20001
        with closing(NativeArchive(f.build())) as a:
            with self.assertRaises(BankError): a.table(DISPLACEMENTS, ["Ux"])
            self.assertEqual(len(a.table(DISPLACEMENTS, ["Ux"], max_records=50000)[0]), 20001)
            for key, budget in ((DISPLACEMENTS, 50001), (DISPLACEMENTS, True), (STATIC, 50000),
                                ("Joint Displacements (Including Internal Mesh Joints)", 50000)):
                with self.subTest(key=key, budget=budget), self.assertRaises(BankError):
                    a.table(key, [], max_records=budget)


if __name__ == "__main__": unittest.main()
