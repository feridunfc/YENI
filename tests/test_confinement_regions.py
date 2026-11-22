import unittest
from math import pi

from tbdy_next.engineering.confinement_regions import tie_schedule
from tbdy_next.engineering.rebar_selection import evaluate_beam_stirrups, normalize_beam_selection_policy
from tbdy_next.engineering.wall_boundary import _boundary_cage, _section_minima


class ConfinementArithmeticTests(unittest.TestCase):
    def test_overlap_uses_end_pitch_and_counts_each_tie_once(self):
        schedule = tie_schedule(1200, 1400, 90, 150)
        self.assertEqual(schedule["confined_union_mm"], 1200)
        self.assertEqual(schedule["overlap_mm"], 1200)
        self.assertEqual(schedule["first_tie_mm"], 45)
        self.assertEqual(schedule["tie_count"], 14)
        self.assertLessEqual(schedule["runs"][0]["pitch_mm"], 90)

    def test_distinct_zones_share_transition_ties(self):
        schedule = tie_schedule(4450, 1200, 90, 150, minimum_pitch=50)
        self.assertEqual([x["intervals"] for x in schedule["runs"]], [13, 14, 13])
        self.assertEqual(schedule["tie_count"], 41)
        i, span, j = schedule["runs"]
        self.assertEqual((i["to_mm"], span["to_mm"]), (span["from_mm"], j["from_mm"]))
        self.assertEqual(j["to_mm"], 4405)

    def test_tiny_middle_zone_cannot_place_two_column_ties_10_mm_apart(self):
        schedule = tie_schedule(2410, 1200, 90, 150, minimum_pitch=50)
        run, = schedule["runs"]
        self.assertEqual(run["region"], "FULL_LENGTH_TIGHTER_PITCH")
        self.assertTrue(50 <= run["pitch_mm"] <= 90)

    def test_effective_depth_governs_pitch_even_if_gross_height_passes(self):
        result = evaluate_beam_stirrups(
            b_mm=300, h_mm=450, d_eff_mm=380, min_long_diameter_mm=16,
            fctd_mpa=1.5, fcd_mpa=20, fywk_mpa=420, gamma_s=1.15,
            ve_eq_kn=10, ve_total_kn=20, policy=normalize_beam_selection_policy("default"))
        self.assertEqual(result["confinement"]["tbdy_spacing_limit_mm"], 95)
        self.assertIs(result["confinement"]["spacing_ok"], False)
        self.assertEqual(result["confinement"]["zone_length_mm"], 900)

    def test_wall_longitudinal_minimum_is_per_end_and_per_gross_wall_area(self):
        section = _section_minima(4400, 400)
        critical = section["critical"]
        self.assertEqual((critical["end_width_mm"], critical["minimum_as_per_end_mm2"]), (880, 3520))
        self.assertEqual(critical["bars_per_end"], 24)
        self.assertAlmostEqual(critical["provided_as_per_end_mm2"], 24 * pi * 14**2 / 4)
        self.assertEqual(section["above_critical"]["minimum_as_per_end_mm2"], 1760)
        self.assertEqual(critical["pitch_limit_mm"], 84)

    def test_wall_ties_consume_eq71_second_term_in_both_axes(self):
        section = {"adopted_constant_detail": _section_minima(4400, 400)["critical"], "thickness_mm": 400}
        cage = _boundary_cage(section, 35, {"cover_mm": 40, "fywk_mpa": 500})
        self.assertEqual(cage["spacing_mm"], 80)
        for name, bk in (("along_wall", 310), ("across_wall", 790)):
            d = cage["directions"][name]
            self.assertAlmostEqual(d["required_ash_mm2"], 0.05 * 80 * bk * 35 / 500)
            self.assertGreaterEqual(d["provided_ash_mm2"], d["required_ash_mm2"])
            self.assertLessEqual(d["largest_leg_gap_mm"], 250)
            self.assertEqual(len(set(d["bar_indices"])), d["legs"])
