import math
import unittest

from tbdy_next.column_engine.ts500_column import (
    SWAY_PERMITTED, SWAY_PREVENTED, effective_length_factor, elastic_sway_length_factor,
)
from tbdy_next.engineering.column_effective_length import effective_length_reference


class ColumnEffectiveLengthTests(unittest.TestCase):
    def test_nonsway_uses_smaller_end_limit_and_is_order_independent(self):
        for a, b in ((0, 5), (5, 0)):
            self.assertEqual(effective_length_factor(alpha_i=a, alpha_j=b, sway=SWAY_PREVENTED), .85)
        self.assertEqual(effective_length_factor(alpha_i=.5, alpha_j=.5, sway=SWAY_PREVENTED), .75)

    def test_sway_branches_and_pinned_end(self):
        self.assertAlmostEqual(effective_length_factor(alpha_i=1, alpha_j=1, sway=SWAY_PERMITTED), .95*math.sqrt(2))
        self.assertAlmostEqual(effective_length_factor(alpha_i=1, alpha_j=3, sway=SWAY_PERMITTED), .9*math.sqrt(3))
        self.assertAlmostEqual(effective_length_factor(alpha_i=None, alpha_j=5, sway=SWAY_PERMITTED), 3.5)
        with self.assertRaises(ValueError):
            effective_length_factor(alpha_i=None, alpha_j=None, sway=SWAY_PERMITTED)

    def test_elastic_sway_springs_have_known_roots_and_fixed_limits(self):
        def k(a, b):
            return elastic_sway_length_factor(clear_length_m=4, ei_knm2=2000,
                                             k_i_knm_per_rad=a*500, k_j_knm_per_rad=b*500)

        self.assertAlmostEqual(k(0, math.pi/4), 4)
        self.assertAlmostEqual(k(math.pi/4, 0), 4)
        self.assertAlmostEqual(k(math.pi/2, math.pi/2), 2)
        self.assertAlmostEqual(k(0, 1e10), 2)
        self.assertAlmostEqual(k(1e10, 1e10), 1)
        self.assertLess(k(2, 1), k(1, 1))
        with self.assertRaises(ValueError):
            k(0, 0)
        with self.assertRaises(ValueError):
            k(-1, 2)

    def test_reference_emits_both_support_limiting_scenarios_and_length_readings(self):
        end = {"alpha_web": 5, "alpha_flange_comparison": 3}
        local = {"stiffness_and_euler": {"M2": {"radius_mm": 230, "ei_ts500_7_21_nmm2": 1e14}},
                 "candidate_span_mm": 4450, "combination_scenarios": [{"combination": "G", "governing_nd_kn": 1600}]}
        sec = {"fck_mpa": 35, "native_t2_mm": 800, "native_t3_mm": 800}
        cases = effective_length_reference({"M2": {"I": {}, "J": end}}, local, sec)["axes"]["M2"]["cases"]
        self.assertEqual(len(cases), 8)
        self.assertEqual({row["support"] for row in cases}, {"MAT_FIXED", "MAT_HINGED"})
        self.assertTrue(all(row["eq729_reference"] for row in cases if row["sway"] == SWAY_PERMITTED))
        self.assertTrue(all(not x["product_authorized"] for row in cases for x in row["eq729_reference"]))
