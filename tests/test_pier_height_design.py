"""Original P2 dimensions, material and cage. Perturbations exercise the decision boundaries."""
from math import hypot, pi, radians, sqrt
import unittest
from unittest.mock import patch

from tbdy_next.column_engine.section_capacity import Bar, Material, Section, _Curve, perimeter
from tbdy_next.column_engine.section_interval import SectionInterval
from tbdy_next.column_engine.section_reference import ReferenceSection, reference_radial_capacity
from tbdy_next.engineering.pier_height_design import _branch, _ordinate, joint_friction, section_dimensions, web_ties
from tbdy_next.engineering.pier_joint_strength import strong_wall_checks


class PierHeightDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ends, _, _ = perimeter(800, 400, 40, 10, 14, 10, 3)
        bars = [Bar(s*(1600+b.x2), b.x3, b.area) for s in (-1, 1) for b in ends]
        bars.extend(Bar(x, y, 36*pi) for x in range(-1100, 1101, 200) for y in (-142, 142))
        cls.s = Section(4000, 400, tuple(bars), Material(35, 35/1.5, 500/1.15))
        cls.kernel = SectionInterval(cls.s)
        cls.detail = {"ach_mm2": 1600000, "fyk_mpa": 500, "fck_mpa": 35, "fyd_mpa": 500/1.15,
                      "fcd_mpa": 35/1.5, "fctd_mpa": .35*sqrt(35)/1.5,
                      "steel_area_mm2": sum(b.area for b in bars)}

    def test_interval_component_floors_against_equilibrated_interior_strain_planes(self):
        # Both cardinals and the steep part of this very elongated section.
        for a, b in ((0, 2), (43, 47), (86, 90)):
            lower = self.kernel._patch(750000, 875000, radians(a), radians(b))
            for t in (a, (a+b)/2, b):
                for n in (750000, 801950, 875000):
                    pt, reason = _Curve(self.s, t).solve(n, seed_c=290)
                    self.assertIsNone(reason)
                    self.assertLessEqual(lower[0], pt["m2_nmm"]/1e6)
                    self.assertLessEqual(lower[1], pt["m3_nmm"]/1e6)

    def test_box_contains_independent_response_at_interior_n_and_accepts_both_axes(self):
        ref = ReferenceSection(4000, 400, tuple((b.x2,b.x3,b.area) for b in self.s.bars),
                               .85*self.s.material.fcd, .79, self.s.material.fyd)
        m2, m3 = 96.0078, 3322.2547
        result = self.kernel.assess([779.0436,2095.6304], m2, m3)
        independent = reference_radial_capacity(ref, 1340e3, m2*1e6, m3*1e6)
        self.assertEqual(independent["status"], "REFERENCE_OBSERVED_STABLE")
        self.assertLess(hypot(m2,m3)/independent["capacity_knm"], result["upper_utilization"])
        self.assertEqual(result["status"], "PMM_BOX_SATISFIED")
        with self.assertRaisesRegex(ValueError, "AXIAL_INTERVAL"):
            self.kernel.assess([-1e6, 1900], m2, m3)
        self.assertEqual(self.kernel.assess([803, 812], 5000, 30000)["status"], "PMM_BOX_INCONCLUSIVE")

    def test_real_elevations_storey_jump_and_figure_7_12_roof(self):
        # Known bottom M3 values from Crack_SeisX_Soil. Scale the illustrative
        # shear ordinates independently to exercise the third-height intersection.
        levels = [('472', -5.15, 0, 2906.3205, 2000, 1000, 700),
                  ('428', 0, 4.5, 3322.2547, 800, 800, 400), ('417', 4.5, 9, 1024.4224, 500, 300, 50)]
        rows = []
        for uid, zb, zt, mb, mt, vb, vt in levels:
            for side, z, m, v in (("Bottom",zb,mb,vb),("Top",zt,mt,vt)):
                rows.append(dict(member=uid,face=side,z_m=z,m2=0,m3=m,solid=v,coupled=v))
        branch = {"reference_z_m": 0., "minimum_hcr_mm": 4000, "wall_height_mm": 9000}
        roof = _branch(rows, rows[-1], branch, 9.)
        self.assertEqual(_ordinate(rows, 0., "m3"), 3322.2547)
        self.assertAlmostEqual(roof["solid"]["third_height_upper_kn"], 800+(400-800)*3/4.5)
        self.assertEqual(roof["solid"]["ve_upper_kn"], 400.)
        self.assertAlmostEqual(roof["m3_design_knm"], 3322.2547+(500-3322.2547)*5/9)
        self.assertEqual(_branch(rows, rows[0], branch, 9.)["m3_design_knm"], 3322.2547)
        moment_only = _branch(rows, rows[-1], branch, 9., shear_available=False)
        self.assertEqual(moment_only["m3_design_knm"], roof["m3_design_knm"])
        self.assertNotIn("coupled", moment_only)
        with self.assertRaisesRegex(ValueError, "ELEVATION"):
            _ordinate(rows, 12, "solid")

    def test_friction_reserves_steel_for_direct_tension_and_enforces_both_caps(self):
        r = joint_friction(self.detail, 1975.2499, 0.)
        self.assertEqual(r["status"], "ROUGH_JOINT_BOUND_SATISFIED")
        self.assertAlmostEqual(r["resistance_kn"], 1.6e6*self.detail["fctd_mpa"]/1000+
                               self.detail["steel_area_mm2"]*500/1.15/1000)
        tension = joint_friction(self.detail, 1975.2499, 400.)
        self.assertAlmostEqual(tension["resistance_kn"], r["resistance_kn"]-400)
        capped = joint_friction({**self.detail, "steel_area_mm2": 50000}, 8000, 0)
        self.assertAlmostEqual(capped["resistance_kn"], .2*35/1.5*1600)
        self.assertEqual(capped["status"], "JOINT_BOUND_INCONCLUSIVE")

    def test_actual_panel_web_density_and_thickness(self):
        s = web_ties({"web_width_mm":2400,"web_vertical_pitch_mm":200,"web_horizontal_pitch_mm":200,
                      "web_stations_per_face":12,"web_bar_diameter_mm":12},5150)
        self.assertEqual((s["layers"],s["count"],s["minimum_ties_in_full_m2"]),(26,312,25))
        self.assertEqual(section_dimensions(4000,400,5150)["required_thickness_mm"],321.875)

    def test_roof_wall_strength_uses_one_wall_and_a_missing_internal_side_stays_open(self):
        combo = "Crack_SeisX_Soil"
        panels = [dict(member="428", story="+4.50", bottom_z_m=0., top_z_m=4.5, status="PANEL_CALCULATED"),
                  dict(member="417", story="+9.00", bottom_z_m=4.5, top_z_m=9., status="PANEL_CALCULATED")]
        cuts = [dict(member=p["member"], face="Top", combination=combo, nd_interval_kn=[200.,400.]) for p in panels]
        beams = [{"beam":"566","face":"I","upper_mr_knm":319.4834667555042}]
        with patch("tbdy_next.engineering.pier_joint_strength._beam_ends", return_value=beams):
            inside, roof = strong_wall_checks({}, {}, {"top_z_m":9., "thickness_mm":400.}, self.s, panels, cuts, [combo])
        self.assertEqual(inside["status"], "HOLD")
        self.assertEqual(roof["status"], "STRONG_WALL_BOUND_SATISFIED")
        self.assertEqual(len(roof["wall_terms"]), 1)
        self.assertAlmostEqual(roof["required_mr_knm"], 1.2*beams[0]["upper_mr_knm"])
