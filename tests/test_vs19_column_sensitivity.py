from contextlib import closing
from copy import deepcopy
import math
import unittest

from column_kinematics_fixture import KinematicsBank
from column_stability_fixture import StiffnessBank
from tbdy_next.column_engine.native_archive import NativeArchive, BankError, digest
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.column_prechecks import build_column_prechecks
from tbdy_next.column_engine.column_stability import build_column_stability
from tbdy_next.column_engine.column_pmm import build_column_cages
from tbdy_next.column_engine.column_transverse import build_column_transverse
from tbdy_next.column_engine.column_joints import build_column_joints
from tbdy_next.column_engine.column_kinematics import build_column_kinematics
from tbdy_next.column_engine.column_sensitivity import build_column_sensitivity, sensitivity_summaries
from tbdy_next.column_engine.sensitivity_kernel import (stiffness_family, zero_denominator_length_mm,
    source_denominator, source_length_scenarios)


def inputs(fixture):
    raw = fixture.build(); bank = recover_column_bank(raw)
    with closing(NativeArchive(raw)) as archive:
        chain = build_demand_chain(bank, archive); pre = build_column_prechecks(bank, chain)
        stability = build_column_stability(bank, chain, pre, archive)
        cages = build_column_cages(bank, chain, pre, archive)
        transverse = build_column_transverse(chain, cages, archive)
        joints = build_column_joints(bank, chain, cages, transverse, archive)
        kinematics = build_column_kinematics(bank, chain, joints, archive)
    return chain, stability, kinematics


def package(fixture=None):
    return build_column_sensitivity(*inputs(fixture or KinematicsBank()))


class LengthSensitivityKernelTests(unittest.TestCase):
    def test_independent_asymmetric_400x600_e30gpa_and_n1000_oracle(self):
        # Native T2=400, T3=600: I22=3.2e9, I33=7.2e9 mm4.
        family = stiffness_family(ec_mpa=30000, ic_mm4=3.2e9, radius_mm=120)
        self.assertEqual([r["effective_ei_nmm2_scenario"] for r in family], [3.84e13, 2.56e13, 1.92e13])
        self.assertEqual([r["effective_length_lk_mm_scenario"] for r in family[0]["length_references"]], [2640, 4800, 12000])
        values = source_length_scenarios(source_n_compression_kn=1000, family=family, radius_mm=120)
        for row, expected in zip(values, [17074.335419, 13941.136491, 12073.378359]):
            self.assertAlmostEqual(row["zero_denominator_length_mm"], expected, places=6)
            self.assertTrue(row["zero_length_exceeds_100i_reference"])

    def test_second_axis_obeys_inertia_and_length_ratios_without_swapping_dimensions(self):
        a = stiffness_family(ec_mpa=30000, ic_mm4=3.2e9, radius_mm=120)
        b = stiffness_family(ec_mpa=30000, ic_mm4=7.2e9, radius_mm=180)
        for x, y in zip(a, b):
            self.assertEqual(y["effective_ei_nmm2_scenario"]/x["effective_ei_nmm2_scenario"], 2.25)
            la = zero_denominator_length_mm(effective_ei_nmm2=x["effective_ei_nmm2_scenario"], source_n_compression_kn=1000)
            lb = zero_denominator_length_mm(effective_ei_nmm2=y["effective_ei_nmm2_scenario"], source_n_compression_kn=1000)
            self.assertAlmostEqual(lb/la, 1.5)

    def test_independent_four_metre_euler_and_denominator_oracle(self):
        from tbdy_next.column_engine.ts500_column import euler_load_kn
        nk = euler_load_kn(effective_ei_nmm2=2.56e13, effective_length_lk_mm=4000)
        self.assertAlmostEqual(nk, 15791.367041743, places=9)
        r = source_denominator(source_n_compression_kn=1000, nk_kn=nk)
        self.assertAlmostEqual(r["source_denominator"], .917676538290601, places=14)
        self.assertEqual(r["status"], "POSITIVE_SOURCE_DENOMINATOR")
        self.assertIsNone(r["beta"]); self.assertFalse(r["design_stability_proven"])

    def test_length_scaling_identity_and_zero_neighborhood_never_grant_positive_acceptance(self):
        from tbdy_next.column_engine.ts500_column import euler_load_kn
        l0 = zero_denominator_length_mm(effective_ei_nmm2=2.56e13, source_n_compression_kn=1000)
        for multiplier, expected, status in ((.8, .36, "POSITIVE_SOURCE_DENOMINATOR"),
            (1, 0, "NUMERICALLY_NEAR_ZERO"), (1.2, -.44, "NONPOSITIVE_SOURCE_DENOMINATOR")):
            nk = euler_load_kn(effective_ei_nmm2=2.56e13, effective_length_lk_mm=multiplier*l0)
            r = source_denominator(source_n_compression_kn=1000, nk_kn=nk)
            self.assertAlmostEqual(r["source_denominator"], expected, places=14)
            self.assertEqual(r["status"], status); self.assertIsNone(r["beta"])
        for length in (math.nextafter(l0, 0), math.nextafter(l0, math.inf)):
            nk = euler_load_kn(effective_ei_nmm2=2.56e13, effective_length_lk_mm=length)
            self.assertEqual(source_denominator(source_n_compression_kn=1000, nk_kn=nk)["status"], "NUMERICALLY_NEAR_ZERO")

    def test_zero_length_is_not_euler_nk_equals_n_length(self):
        l0 = zero_denominator_length_mm(effective_ei_nmm2=2.56e13, source_n_compression_kn=1000)
        euler_equal_n = math.pi*math.sqrt(2.56e13/1e6)
        self.assertAlmostEqual(euler_equal_n/l0, math.sqrt(1.3))
        self.assertNotAlmostEqual(euler_equal_n, l0)

    def test_tension_and_zero_are_kept_without_absolute_value_or_fictitious_length(self):
        family = stiffness_family(ec_mpa=30000, ic_mm4=3.2e9, radius_mm=120)
        for n in (0, -1, -1000):
            rows = source_length_scenarios(source_n_compression_kn=n, family=family, radius_mm=120)
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(r["status"] == "NONCOMPRESSION_NOT_APPLICABLE" for r in rows))
            self.assertTrue(all(r["zero_denominator_length_mm"] is None and not r["at_reference_lengths"] for r in rows))

    def test_invalid_numeric_inputs_are_rejected(self):
        for n in (0, -1, math.inf, math.nan, True):
            with self.subTest(n=n), self.assertRaises(BankError):
                zero_denominator_length_mm(effective_ei_nmm2=1e13, source_n_compression_kn=n)
        for change in ({"ec_mpa":0}, {"ic_mm4":-1}, {"radius_mm":math.inf}, {"radius_mm":True}):
            with self.subTest(change=change), self.assertRaises(BankError):
                stiffness_family(**(dict(ec_mpa=30000, ic_mm4=3.2e9, radius_mm=120) | change))


class ColumnSensitivityTests(unittest.TestCase):
    def test_all_static_stations_and_both_axes_are_evaluated(self):
        r = package()
        self.assertEqual(r["static_state_count"], 8); self.assertEqual(r["state_axis_count"], 16)
        self.assertEqual(r["calculated_axis_count"], 4)
        self.assertEqual(r["stiffness_scenario_count"], 12)
        self.assertEqual(r["euler_reference_count"], 36)
        self.assertEqual(r["zero_length_reference_count"], 48)
        self.assertEqual(r["source_denominator_count"], 144)
        self.assertFalse(r["source_population_reduced"])
        middle = [x for x in r["rows"] if x["member_id"] == "C_SYNTHETIC_1" and x["native_key"]["ObjSta"] == 2]
        self.assertEqual(len(middle), 4)
        self.assertEqual({x["native_key"]["Elm"] for x in middle}, {"C_SYNTHETIC_1A", "C_SYNTHETIC_1B"})

    def test_native_axis_contract_and_exact_vs_approximate_radii_are_distinct(self):
        f = StiffnessBank(); f.unequal_rectangle()
        r = package(f); a, b = r["axes"][:2]
        self.assertEqual(a["gross_inertia_mm4"], 14.4e9)
        self.assertAlmostEqual(b["gross_inertia_mm4"], 25.6e9)
        self.assertEqual(a["radius_reference_mm"], 180)
        self.assertAlmostEqual(a["radius_exact_mm"], 173.20508075688772)
        self.assertEqual(a["length_100i_mm"], 18000)
        self.assertEqual(b["length_100i_mm"], 24000)
        self.assertEqual(r["policy"]["radius_basis"], "TS500_RECTANGLE_0_30_BENDING_DIMENSION")

    def test_missing_point_graph_does_not_erase_independent_section_and_force_references(self):
        r = package(StiffnessBank())
        self.assertEqual(r["zero_length_reference_count"], 48)
        self.assertTrue(all(p["n_i_kn"] is None for p in r["axial_profiles"]))

    def test_missing_elastic_source_preserves_population_and_reports_blockers(self):
        f = KinematicsBank(); f.omitted.add(("PropMaterial.GetMPIsotropic", "material", "CONCRETE_SYNTHETIC"))
        r = package(f)
        self.assertEqual(r["state_axis_count"], 16)
        self.assertEqual(r["calculated_axis_count"], 0)
        self.assertEqual(r["zero_length_reference_count"], 0)
        self.assertEqual(r["status_counts"], {"BLOCKED_INPUTS":16})
        self.assertTrue(all(row["reason"] for row in r["rows"]))

    def test_contradictory_native_properties_are_not_overridden_by_rectangle_formula(self):
        f = KinematicsBank()
        f.calls[("PropFrame.GetSectProps", "frame_section", "RECT_SYNTHETIC")]["raw_response"][4] *= 2
        r = package(f)
        self.assertEqual(r["calculated_axis_count"], 0)
        self.assertEqual(r["state_axis_count"], 16)

    def test_source_axial_signs_and_zero_do_not_disappear(self):
        for p in (1000, 0):
            f = KinematicsBank(); f.set_static_vector([p, 0, 0, 0, 20, 40])
            r = package(f)
            self.assertEqual(r["status_counts"], {"NONCOMPRESSION_NOT_APPLICABLE":16})
            self.assertEqual(r["zero_length_reference_count"], 0)
            self.assertTrue(all(float(row["n_source_compression_kn"]) == -p for row in r["rows"]))

    def test_source_axial_variation_and_signed_end_difference_do_not_become_constant_n_proof(self):
        r = package(); p = r["axial_profiles"][0]
        self.assertEqual((p["n_i_kn"], p["n_j_kn"], p["end_n_j_minus_i_kn"]), ("180", "720", "540"))
        self.assertEqual(p["recorded_range_kn"], "540")
        self.assertEqual(p["recorded_values_status"], "RECORDED_AXIAL_VALUES_DIFFER")
        self.assertFalse(p["constant_axial_force_along_height_proven"])
        f = KinematicsBank(); f.set_static_vector([-1000, 0, 0, 0, 20, 40])
        same = package(f)
        self.assertTrue(all(p["recorded_values_status"] == "RECORDED_AXIAL_VALUES_EQUAL" for p in same["axial_profiles"]))
        self.assertTrue(all(not p["constant_axial_force_along_height_proven"] for p in same["axial_profiles"]))

    def test_every_exact_critical_tie_is_kept_without_reducing_full_population(self):
        f = KinematicsBank(); f.set_static_vector([-1000, 0, 0, 0, 20, 40])
        r = package(f); summary = sensitivity_summaries(r)
        self.assertEqual(len(summary), 4)
        self.assertTrue(all(len(s["critical_source_states"]) == 4 for s in summary))
        self.assertEqual(len(r["rows"]), 16)
        self.assertTrue(all(not s["actual_design_critical_state_selected"] for s in summary))

    def test_dependencies_are_immutable_and_derivation_is_deterministic(self):
        args = inputs(KinematicsBank()); before = digest(args)
        a, b = build_column_sensitivity(*args), build_column_sensitivity(*args)
        self.assertEqual(a, b); self.assertEqual(digest(args), before)
        a["policy"]["creep_ratio_scenarios"][0] = 999
        self.assertEqual(build_column_sensitivity(*args)["policy"]["creep_ratio_scenarios"], [0, .5, 1])

    def test_stale_sources_and_axes_are_rejected(self):
        args = inputs(KinematicsBank())
        for item, key, value in ((1, "source_demand_result_sha256", "WRONG"), (1, "source_run_id", "WRONG"),
            (2, "source_archive_sha256", "WRONG"), (2, "source_bank_result_sha256", "WRONG"), (1, "axis_convention", "OLD")):
            bad = deepcopy(args); bad[item][key] = value
            with self.subTest(key=key), self.assertRaises(BankError): build_column_sensitivity(*bad)

    def test_duplicate_and_nonstatic_states_are_rejected(self):
        args = inputs(KinematicsBank())
        bad = deepcopy(args); bad[0]["candidates"].append(deepcopy(bad[0]["candidates"][0]))
        with self.assertRaises(BankError): build_column_sensitivity(*bad)
        for key, value in (("StepType", "Max"), ("StepNum", 1), ("LoadCase", "RS_SUM")):
            bad = deepcopy(args); bad[0]["candidates"][0]["native_key"][key] = value
            with self.subTest(key=key), self.assertRaises(BankError): build_column_sensitivity(*bad)

    def test_no_parameter_family_grants_real_lengths_creep_or_design_authority(self):
        r = package()
        for key in ("actual_creep_ratio", "actual_effective_length_lk_mm", "actual_sway_classification", "actual_cm", "actual_beta", "magnified_design_moments"):
            self.assertIsNone(r[key])
        self.assertFalse(r["actual_second_order_applied"])
        self.assertFalse(r["approximate_method_applicability_proven"])
        self.assertEqual(r["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(r["engineering_release"], "NOT_READY")
        self.assertEqual(r["design_demand_authority"], "DENIED")
        self.assertFalse(r["policy"]["actual_ei_interval_proven"])
        self.assertFalse(r["policy"]["source_axial_force_is_design_nd"])


if __name__ == "__main__": unittest.main()
