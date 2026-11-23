"""Regression checks for source population, spectrum separation and pressure-end detailing."""
from math import pi
import unittest

from tbdy_next.column_engine.section_capacity import Material
from tbdy_next.engineering.basement_pier_geometry import _bounds, _overlap_area, _union
from tbdy_next.engineering.basement_wall_connection import tension_development
from tbdy_next.engineering.wall_batch import _reference_friction, _reference_web, wall_batch
from tbdy_next.engineering.wall_overturning import recover_amplitudes


class WallBatchTest(unittest.TestCase):
    def test_directional_radii_need_an_independent_control(self):
        equations = {"cx": (1, .3), "cy": (.3, 1), "dx": (2.5, .75), "dy": (.75, 2.5)}
        radii = {name: x*1267.867 + y*547.36 for name, (x,y) in equations.items()}
        values = recover_amplitudes(equations, radii)
        self.assertAlmostEqual(values["X"], 1267.867)
        self.assertAlmostEqual(values["Y"], 547.36)
        self.assertLess(values["uncertainty_knm"]["X"], .0001)
        radii["cx"] += .001
        with self.assertRaisesRegex(ValueError, "CONTROLS_DIFFER"):
            recover_amplitudes(equations, radii)
        with self.assertRaisesRegex(ValueError, "NOT_IDENTIFIABLE"):
            recover_amplitudes({"a": (1,.3), "b": (2,.6), "c": (3,.9)}, {"a":10, "b":20, "c":30})

    def test_missing_source_retains_unassigned_and_grouped_wall_rows(self):
        walls = [{"member_id":"w1","pier":"P","story":"B"}, {"member_id":"w2","pier":"P","story":"B"},
                 {"member_id":"w3","pier":None,"story":"B"}]
        out = wall_batch({}, {}, {"walls":walls}, {"piers":[],"basement_piers":[],"conditional_piers":0}, {},
                         {"native_static":{"G":{}}, "native_seismic":{},"other":[],"controls":{}})
        self.assertEqual(out["counts"]["physical_walls"], 3)
        self.assertEqual(out["counts"]["assigned_face_checks_expected"], 2)
        self.assertEqual(out["counts"]["native_assigned_faces"], 0)
        self.assertEqual(len(out["rows"]), 2)
        self.assertIn("PIER_ASSIGNMENT_REQUIRED", [r["reason"] for r in out["rows"]])

    def test_overlapping_column_and_perpendicular_web_are_reserved_only_once(self):
        web = _bounds((0,0),(4,0),.4)
        crossing = _bounds((2,0),(2,2),.4)
        column = (1.6,2.4,-.4,.4)
        self.assertAlmostEqual(_union([web])-_overlap_area([web],[crossing,column]), 1.6-.8*.4)

    def test_friction_reserves_tension_and_uses_both_in_plane_components_of_the_joint(self):
        material = Material(35, 35/1.5, 500/1.15), 500
        area = {"net_m2": 1.6, "directional_webs":{"X":{"net_m2":1.2,"maximum_thickness_m":.4}}}
        cut = {"abs_v2_kn":300, "abs_v3_kn":400,"tension_kn":700}
        out = _reference_friction(cut, area, material)
        self.assertEqual(out["reference_plane_shear_kn"],500)
        f = out["reference_friction"]
        self.assertAlmostEqual(f["reserved_steel_mm2"],700000/(500/1.15))
        self.assertAlmostEqual(f["ts500_8_1_7_concrete_cap_kn"],.2*35/1.5*1600)
        exceed = _reference_friction({**cut,"tension_kn":6000}, area, material)
        self.assertEqual(exceed["reference_friction"]["status"],"JOINT_BOUND_INCONCLUSIVE")
        web = _reference_web(cut,area,material,180)
        self.assertAlmostEqual(web["web_area_m2"],1.2)
        self.assertAlmostEqual(web["rho_h"],2*36*pi/(400*200))
        with self.assertRaisesRegex(ValueError,"ALIGNED_PIER"):
            _reference_web(cut,area,material,45)

    def test_bond_position_and_splitting_change_required_length(self):
        def bond(d, pitch):
            return tension_development(d,500/1.15,35,35/1.5,40,pitch-d)
        self.assertGreater(bond(22,100)["position_i_mm"],750)
        self.assertLess(bond(14,39.5)["position_i_mm"],750)
        self.assertAlmostEqual(bond(14,30)["position_i_mm"],1.2*bond(14,39.5)["position_i_mm"])
