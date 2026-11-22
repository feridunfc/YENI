"""Regression checks for physical cut identity and scale ownership in the C104 study."""
import unittest

from tbdy_next.engineering.transition_design_trace import _base_rows, _comparison, mesh_effects, scale_sensitivity


class DesignTraceTests(unittest.TestCase):
    def test_effective_total_scale_depends_on_the_observed_case_scale(self):
        # The required increase is relative to the already-scaled response.
        first = scale_sensitivity(4000.,3200.,10.)
        doubled = scale_sensitivity(4000.,6400.,20.)
        self.assertEqual(first[0]["additional_factor_on_observed"],1.)
        self.assertAlmostEqual(first[1]["additional_factor_on_observed"],1.125)
        self.assertEqual(first[1]["case_scale_for_target_m_s2"],11.25)
        self.assertEqual(doubled[1]["additional_factor_on_observed"],1.)

    def test_ineligible_static_and_spectral_steps_cannot_share_a_base_reaction(self):
        raw = [2,["LC_EQX","RSX"],["Single Value","Max"],[0,0],
               [-4000,3200],[0,0],[0,0],[0,0],[0,0],[0,0],0,0,0]
        xyz,rows = _base_rows(raw,("LC_EQX","RSX"))
        self.assertEqual(xyz,[0,0,0])
        self.assertEqual(rows["LC_EQX"]["FX"],-4000)
        raw[2][1] = "Min"
        with self.assertRaisesRegex(ValueError,"STEP"):
            _base_rows(raw,("LC_EQX","RSX"))

    def test_missing_or_duplicate_native_cases_remain_errors(self):
        raw = [2,["LC_EQX","LC_EQX"],["Single Value"]*2,[0,0],*([[0,0]]*6),0,0,0]
        with self.assertRaisesRegex(ValueError,"STEP"):
            _base_rows(raw,("LC_EQX",))
        with self.assertRaisesRegex(ValueError,"POPULATION"):
            _base_rows(raw,("LC_EQY",))

    def test_crossed_contrasts_retain_interaction(self):
        row = mesh_effects(1.,3.,6.,12.)
        self.assertEqual(row["b_minus_a_vertical"],2.)
        self.assertEqual(row["d_minus_c_vertical"],6.)
        self.assertEqual(row["c_minus_a_horizontal"],5.)
        self.assertEqual(row["d_minus_b_horizontal"],9.)
        self.assertEqual(row["interaction"],4.)
        self.assertEqual(row["a_d_difference"],2.+5.+4.)

    def test_fixed_mesh_tolerance_uses_absolute_floor_near_zero(self):
        self.assertTrue(_comparison(-.012,.020)["within_budget"])
        self.assertFalse(_comparison(-.031,.031)["within_budget"])
        self.assertAlmostEqual(_comparison(-200.,-203.)["limit"],2.03)
