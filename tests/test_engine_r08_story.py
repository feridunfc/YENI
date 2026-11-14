"""Unit tests for direction-matched R08 story numeric screening."""
import unittest

from tbdy_next.column_engine.native_archive import digest
from tbdy_next.engineering.story_pdelta import StorySourceError, review_story_pdelta


def example():
    return {
        "schema": "tbdy.next.r08.story-source.v1",
        "weight_basis": "G_PLUS_NQ",
        "weight_kind": "INDIVIDUAL_STORY_WEIGHT",
        "weight_units": "kN",
        "shear_units": "kN",
        "drift_units": "m",
        "height_units": "m",
        "combination_name": "WGHT_SYNTHETIC",
        "weight_operator": "Linear Add",
        "weight_terms": {
            "LC_DL": 1.0, "LC_SDL": 1.0, "LC_WDL": 1.0,
            "LC_DDL": 1.0, "LC_LL": 0.3,
        },
        "n_live": 0.3,
        "directions": {
            "X": {"shear_case": "RSX", "drift_case": "RSX",
                  "case_type": "LinRespSpec", "step_type": "Max"},
            "Y": {"shear_case": "RSY", "drift_case": "RSY",
                  "case_type": "LinRespSpec", "step_type": "Max"},
        },
        "design_parameters": {
            "R_X": 7.0, "R_Y": 7.0, "D_X": 2.5, "D_Y": 2.5, "Ch": 0.5
        },
        "stories": [
            {"story": "S2", "level_m": 9.0, "height_m": 4.5,
             "individual_w_kN": 1000.0,
             "shear_kN": {"X": 100.0, "Y": 90.0},
             "average_reduced_drift_m": {"X": .002, "Y": .0025}},
            {"story": "S1", "level_m": 4.5, "height_m": 4.5,
             "individual_w_kN": 2000.0,
             "shear_kN": {"X": 200.0, "Y": 180.0},
             "average_reduced_drift_m": {"X": .003, "Y": .004}},
        ],
    }


class StoryScreeningTests(unittest.TestCase):

    def test_cumulative_weight_and_two_axes(self):
        result = review_story_pdelta(example())
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertEqual(result["engineering_verdict"], "NOT_PROVEN")
        self.assertEqual(result["rows"][0]["cumulative_weight_kN"], 1000.)
        self.assertEqual(result["rows"][1]["cumulative_weight_kN"], 3000.)
        self.assertAlmostEqual(
            result["rows"][1]["axes"]["X"]["theta_II_reference"], .01)
        self.assertAlmostEqual(
            result["rows"][1]["axes"]["Y"]["theta_II_reference"],
            .004 * 3000 / (180 * 4.5))
        self.assertAlmostEqual(result["limit_reference"]["X"], .12 * 2.5 / (7 * .5))
        self.assertTrue(result["all_observed_below_numeric_limit"])
        self.assertEqual(result["rows"][1]["axes"]["X"]["beta_II_candidate"], 1.)
        body = dict(result)
        self.assertEqual(digest({k: v for k, v in body.items() if k != "result_sha256"}),
                         result["result_sha256"])

    def test_wrong_axis_is_rejected(self):
        source = example()
        source["directions"]["Y"]["shear_case"] = "RSX"
        with self.assertRaisesRegex(StorySourceError, "MIXED_CASE"):
            review_story_pdelta(source)

    def test_gravity_service_cannot_impersonate_seismic_weight(self):
        source = example()
        source["combination_name"] = "Grav_Service"
        with self.assertRaisesRegex(StorySourceError, "GRAVITY_COMBINATION"):
            review_story_pdelta(source)

    def test_wrong_live_load_mass_factor_is_rejected(self):
        source = example()
        source["weight_terms"]["LC_LL"] = 1.0
        with self.assertRaisesRegex(StorySourceError, "N_LIVE"):
            review_story_pdelta(source)

    def test_cumulative_weight_must_not_be_passed_as_individual(self):
        source = example()
        source["weight_kind"] = "CUMULATIVE_AT_CUT"
        with self.assertRaisesRegex(StorySourceError, "WEIGHT_OR_UNITS"):
            review_story_pdelta(source)

    def test_zero_shear_is_rejected(self):
        source = example()
        source["stories"][0]["shear_kN"]["Y"] = 0.
        with self.assertRaisesRegex(StorySourceError, "INVALID_STORY_VALUE"):
            review_story_pdelta(source)


if __name__ == "__main__":
    unittest.main()
