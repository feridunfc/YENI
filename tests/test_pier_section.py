"""Regression at the original P3 roof-storey bottom cut, using its proposed two-curtain cage."""
from math import pi
import unittest

from tbdy_next.column_engine.section_capacity import Bar, Material, Section, perimeter, solver
from tbdy_next.column_engine.section_reference import ReferenceSection, reference_radial_capacity
from tbdy_next.engineering.pier_force_source import ORIGINAL, METHOD, signed_vector


class PierCutRegression(unittest.TestCase):
    # Native Grav_Ult, wall 414 at the bottom of +9.00 m, kN and kN-m.
    original = {"CaseType": "Combination", "StepType": "None", "P": -567.0264, "V2": 1.2839,
                "V3": 3.2668, "T": -3.6855, "M2": 11.7128, "M3": 12.2791}

    def test_static_none_is_one_state_and_unequal_envelopes_never_form_a_vector(self):
        exact = signed_vector([self.original], ORIGINAL)
        self.assertEqual(exact["M2"], self.original["M2"])
        self.assertEqual(exact["P"], self.original["P"])
        for kind, case_type in ((ORIGINAL, "Combination"), (METHOD, "NonStatic")):
            low = {**self.original, "CaseType": case_type, "StepType": "Min"}
            high = {**low, "StepType": "Max", "V3": low["V3"] + 0.0001}
            with self.assertRaisesRegex(ValueError, "SIGNED_CONCURRENT"):
                signed_vector([low, high], kind)

    def test_fixed_axial_capacity_matches_independent_strip_integral_after_local_refinement(self):
        end, _, _ = perimeter(800, 400, 40, 10, 14, n2=7, n3=3)
        bars = [Bar(sign*(1000+b.x2), b.x3, b.area) for sign in (-1, 1) for b in end]
        bars.extend(Bar(x, y, 36*pi) for x in (-500, -300, -100, 100, 300, 500) for y in (-142, 142))
        mat = Material(35, 35/1.5, 500/1.15)
        section = Section(2800, 400, tuple(bars), mat)
        reference = ReferenceSection(2800, 400, tuple((b.x2, b.x3, b.area) for b in bars),
                                     .85*mat.fcd, .79, mat.fyd)
        n = -1000*self.original["P"]
        m2, m3 = self.original["M2"]*1e6, self.original["M3"]*1e6
        result = solver(section).assess(n, m2, m3, refine_crossing=True)
        independent = reference_radial_capacity(reference, n, m2, m3)
        self.assertEqual(independent["status"], "REFERENCE_OBSERVED_STABLE")
        self.assertAlmostEqual(result["radial_capacity_kNm"], independent["capacity_knm"], delta=.002)
        trace = result["refinement"]
        self.assertEqual(trace["status"], "TWO_LOCAL_REFINEMENTS_STABLE_AFTER_GLOBAL_BRACKETING")
        self.assertLessEqual(trace["max_axial_residual_n"], 1)
        local = trace["local_crossing"]
        self.assertTrue(all(d <= b for d, b in zip(local["differences_knm"][-2:], local["budgets_knm"][-2:])))
        self.assertFalse(trace["continuous_error_bound_proven"])
