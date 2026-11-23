"""Physical coverage and calculation boundaries for column-supported basement webs."""
import math
import unittest

from tbdy_next.column_engine.section_capacity import Material
from tbdy_next.engineering.basement_pier_design import _allocate, _section_terms, basement_coverage, basement_piers
from tbdy_next.engineering.basement_pier_geometry import _bounds, _union
from tbdy_next.engineering.basement_wall_pressure import panel_pressure_design, vertical_section
from tbdy_next.reporting import _basement_pier_tables


class BasementWebTests(unittest.TestCase):
    def test_fold_overlap_and_clear_section_are_different(self):
        web = _bounds((0, 0), (3, 0), .4)
        corner = _bounds((3, 0), (3, 8), .4)
        self.assertAlmostEqual(_union([web, corner]), (3 + 8)*.4 - .04)
        with self.assertRaisesRegex(ValueError, "ORTHOGONAL"):
            _bounds((0, 0), (3, 1), .4)

    def test_stress_first_moments_at_native_origin_and_when_translated(self):
        # Two rectangles of equal area at right angles. The imposed axial stress
        # is 360 + 5x - 7y (kN/m²) in the reference coordinate system.
        panels = [dict(member="a", width_direction=[1, 0], clear_centroid_xy_m=[1, 0]),
                  dict(member="b", width_direction=[0, 1], clear_centroid_xy_m=[2, 1])]
        for panel in panels:
            panel.update(clear_length_m=2., thickness_m=.4)
        area = .8
        axial = [area*365, area*(360+10-7)]
        strong = [area*4/12*5, area*4/12*(-7)]
        weak = [area*.16/12*(-7), area*.16/12*(-5)]
        total = sum(axial)
        qx = axial[0] + 2*axial[1] + strong[0] - weak[1]
        qy = axial[1] + weak[0] + strong[1]
        geom = dict(native_axes_2_xy=[1,0], net_centroid_xy_m=[1.5,.5],
                    panels=panels, clear_web_area_m2=1.6)
        for x, y in ((0., 0.), (102., 11.)):
            terms, inertia = _section_terms(geom, [x,y,0.])
            result, error = _allocate(terms, inertia, total, qx-total*x, qy-total*y)
            self.assertLess(max(map(abs, error)), 1e-8)
            for i, uid in enumerate(("a", "b")):
                for expected, observed in zip((axial[i], weak[i], strong[i]), result[uid]):
                    self.assertAlmostEqual(expected, observed, places=8)

    def test_eight_metre_web_pressure_strip_and_detail(self):
        panel = {"member":"460", "span_m":8., "clear_length_m":7.2, "thickness_m":.4}
        combos = {"NoPressure": {"pressure_kn_m2":{"460":0.}},
                  "Soil": {"pressure_kn_m2":{"460":-55.56}}}
        mat = Material(35., 35./1.5, 500./1.15)
        h = panel_pressure_design(panel, combos, 40., mat, 5.15)
        self.assertEqual((h["governing"], h["diameter_mm"], h["maximum_pitch_mm"]), ("Soil",22,100))
        self.assertAlmostEqual(h["cuts"][1]["moment_bound_knm_m"], 444.48)
        self.assertAlmostEqual(h["cuts"][1]["reaction_bound_kn_m"], 277.8)
        self.assertAlmostEqual(h["diagonal_cracking_kn_m"], .65*.35*math.sqrt(35)/1.5*(400-40-33))
        self.assertLess(max(h["cuts"][1][k] for k in ("moment_ratio","cracking_shear_ratio")), 1.)
        sec, v = vertical_section(panel,h,40.,mat,12,200)
        self.assertEqual((len(sec.bars), v["stations_per_face"], v["crossties"]), (72,36,1872))
        self.assertGreaterEqual(v["min_crossties_full_m2"], 4)

    def test_missing_capture_preserves_physical_and_unclassified_load_scope(self):
        walls = [{"member_id":uid, "pier":"yP1","story":"+0.00"} for uid in ("443","460","461","463","473")]
        scope = {"native_static":{"Grav_Ult":{}}, "native_seismic":{}, "other":["Unresolved"]}
        groups = basement_piers({}, {}, {"walls":walls}, {}, scope)
        count = basement_coverage(groups)
        self.assertEqual((count["assigned_cuts_evaluated"], count["assigned_cuts_expected"]), (0,4))
        self.assertEqual((count["scheduled_panels"], count["physical_panels"]), (0,5))
        self.assertEqual(count["assigned_pressure_panel_combinations_expected"], 10)
        self.assertIn("ORIGINAL_PIER_SECTION_AND_FORCE_SOURCE_REQUIRED", _basement_pier_tables({"basement_piers":groups}))
        self.assertEqual(_basement_pier_tables({}), "")
