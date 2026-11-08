"""B1 normative numerical golden oracles; never grants approved compliance.

TBDY 2018 Table 3.6 and 3.6.2.3, weak-story total effective shear area.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest

from tbdy_next.weak_story_b1 import B1InputError, evaluate_b1


def floor(label, z, aw, ag, ak, *, active=True):
    def areas(wall):
        return {"Aw_m2": str(aw), "Ag_m2": str(ag), "Ak_m2": str(wall)}
    return {
        "story": label, "elevation_m": str(z), "active": active,
        "X": areas(ak), "Y": areas(ak),
    }


class B1WeakStoryGolden(unittest.TestCase):
    def test_exact_080_is_not_a_b1_trigger(self):
        r = evaluate_b1([floor("LOW", 0, 8, 0, 0),
                         floor("UP", 3, 10, 0, 0)], R_base="7")
        self.assertEqual(r["eta_ci_min"], "0.8")
        self.assertEqual(r["numeric_condition"], "NO_B1_NUMERIC_TRIGGER")
        self.assertIsNone(r["R_multiplier_both_directions"])
        self.assertEqual(r["computed_story_direction_pairs"], 2)
        self.assertEqual(r["formal_compliance"], "NOT_PROVEN")

    def test_b1_between_060_and_080_adjusts_R_both_directions(self):
        r = evaluate_b1([floor("LOW", 0, 7, 0, 0),
                         floor("UP", 3, 10, 0, 0)], R_base="7")
        self.assertEqual(r["eta_ci_min"], "0.7")
        self.assertEqual(r["numeric_condition"], "B1_R_REDUCTION_REQUIRED")
        self.assertEqual(Decimal(r["R_multiplier_both_directions"]),
                         Decimal("0.875"))
        self.assertEqual(Decimal(r["R_adjusted_both_directions"]),
                         Decimal("6.125"))
        self.assertTrue(all(x["numeric_condition"] == "B1_R_REDUCTION_REQUIRED"
                            for x in r["paired_results"]))

    def test_exact_060_is_R_reduction_not_forbidden(self):
        r = evaluate_b1([floor("LOW", 0, 6, 0, 0),
                         floor("UP", 3, 10, 0, 0)], R_base="8")
        self.assertEqual(r["eta_ci_min"], "0.6")
        self.assertEqual(r["numeric_condition"], "B1_R_REDUCTION_REQUIRED")
        self.assertEqual(Decimal(r["R_adjusted_both_directions"]), Decimal(6))

    def test_below_060_requires_redesign_and_reanalysis(self):
        r = evaluate_b1([floor("LOW", 0, 5, 0, 0),
                         floor("UP", 3, 10, 0, 0)], R_base="8")
        self.assertEqual(r["numeric_condition"], "REDESIGN_AND_REANALYZE")
        self.assertIsNone(r["R_adjusted_both_directions"])
        self.assertEqual(r["formal_compliance"], "NOT_PROVEN")

    def test_lower_infill_gt_upper_with_preliminary_B1_ignores_both(self):
        # Raw: (4 + 0.15*1) / (6 + 0.15*0) < 0.8, lower Ak higher.
        r = evaluate_b1([floor("LOW", 0, 4, 0, 1),
                         floor("UP", 3, 6, 0, 0)])
        for row in r["paired_results"]:
            self.assertTrue(row["infill_omitted_because_lower_more_than_upper"])
            self.assertEqual(Decimal(row["eta_ci"]), Decimal(4)/Decimal(6))
            self.assertEqual(row["Ae_lower_m2"], "4")
            self.assertEqual(row["Ae_upper_m2"], "6")

    def test_lower_more_infill_without_B1_does_not_trigger_exception(self):
        r = evaluate_b1([floor("LOW", 0, 10, 0, 10),
                         floor("UP", 3, 10, 0, 1)])
        self.assertFalse(r["paired_results"][0]["infill_omitted_because_lower_more_than_upper"])
        self.assertEqual(r["numeric_condition"], "NO_B1_NUMERIC_TRIGGER")

    def test_flexible_connection_takes_Ak_zero_without_authorizing_code(self):
        a = [floor("LOW", 0, 7, 0, 40), floor("UP", 3, 10, 0, 20)]
        r = evaluate_b1(a, wall_type="FLEXIBLE", flex_connection_verified=True,
                        physical_census_proven=True, source_directional_area_proven=True)
        self.assertEqual(Decimal(r["eta_ci_min"]), Decimal("0.7"))
        self.assertTrue(all(x["flexible_infill_omitted_by_4_9_1_3_b"] for x in r["paired_results"]))
        self.assertEqual(r["formal_compliance"], "NOT_PROVEN")

    def test_inactive_top_story_not_added_to_denominator(self):
        a = [floor("LOW", 0, 7, 0, 0), floor("UP", 3, 10, 0, 0),
             floor("EMPTY", 8, 0, 0, 0, active=False)]
        r = evaluate_b1(a)
        self.assertEqual(r["input_stories"], 3)
        self.assertEqual(r["active_physical_stories"], 2)
        self.assertEqual(r["expected_story_direction_pairs"], 2)
        self.assertEqual(r["inactive_stories"], ["EMPTY"])

    def test_basement_negative_elevation_is_valid(self):
        a = [floor("BASEMENT", -4.5, 7, 0, 0),
             floor("GROUND", 0, 10, 0, 0)]
        r = evaluate_b1(a)
        self.assertEqual(r["paired_results"][0]["lower_story"], "BASEMENT")

    def test_input_invalidity_does_not_turn_missing_into_zero(self):
        for values in (
            [floor("LOW", 0, 7, 0, 0), floor("LOW", 3, 10, 0, 0)],
            [floor("LOW", 0, 7, 0, 0), floor("UP", 0, 10, 0, 0)],
            [floor("LOW", 0, 7, 0, 0), floor("UP", 3, 0, 0, 0)],
            [floor("LOW", 0, 7, 0, 0), floor("UP", 3, 10, 0, -1)],
            [floor("LOW", 0, 7, 0, 0), floor("UP", 3, 10, 0, 0, active=False)],
        ):
            with self.subTest(values=values), self.assertRaises(B1InputError):
                evaluate_b1(values)

    def test_determinism_and_no_mutation(self):
        src = [floor("LOW", 0, 10, 2, 1), floor("UP", 3, 9, 3, 0)]
        old = deepcopy(src)
        a,b = evaluate_b1(src),evaluate_b1(src)
        self.assertEqual(src, old)
        self.assertEqual(a,b)
        self.assertEqual(len(a["result_sha256"]),64)
        self.assertEqual(a["formal_compliance"],"NOT_PROVEN")


if __name__ == "__main__":
    unittest.main()
