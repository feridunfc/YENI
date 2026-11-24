"""Directional shell bounds, project aggregate size and support-entry regressions."""
import unittest
from itertools import product
from math import sqrt

from tbdy_next.engineering.basement_joint_layout import level_grid
from tbdy_next.engineering.basement_wall_connection import _bar_clearance, _entry_lanes, _transfer
from tbdy_next.engineering.basement_wall_pressure import DEFAULT_AGGREGATE_MM, clear_limit
from tbdy_next.engineering.frame_geometry import _csi_frame_axes
from tbdy_next.engineering.frame_storey_design import BUILDING_SCHEMA, FRAME_METHOD, normalize_building_design
from tbdy_next.engineering.seismic_input_review import physical_height
from tbdy_next.engineering.wall_pressure_shell import directional_actions, panel_shell_checks


class TestWallPressureProject(unittest.TestCase):
    def test_actual_w28_entry_and_row_require_different_clearance_checks(self):
        # The Ø14 curtain axis is 139 mm from the centre. C221 and C227 use Ø16 bars.
        prof = {"bar_diameter":16,"bar_offsets":[-171.,-85.5,0.,85.5,171.]}
        self.assertEqual(_bar_clearance(prof,139.,14.),17.)
        self.assertAlmostEqual(clear_limit(DEFAULT_AGGREGATE_MM,14.,16.),26.6666666667)
        self.assertLess(39.5-14., clear_limit(20.,14.))
        lane = _entry_lanes([prof],139.)[1]
        self.assertAlmostEqual(_bar_clearance(prof,lane,14.),27.75)

    def test_inner_curtain_can_use_a_separate_outer_dowel_lane_with_cover_and_bond(self):
        from tbdy_next.column_engine.section_capacity import Material
        profile = {"depth_mm":800., "cover":40., "tie":10., "bar_diameter":16.,
                   "bar_offsets":[85.5*i for i in range(-4,5)], "fck":35., "fcd":35./1.5}
        panel = {"thickness_m":.4,"span_m":3.,"clear_length_m":2.2}
        h = {"cover_mm":40.,"diameter_mm":12,"curtain_inset_mm":99.25,
             "cuts":[{"combination":"soil","pressure_kn_m2":54.,"reaction_bound_kn_m":101.25}]}
        policy = {"aggregate_mm":20., "height":5150., "module":49.56862745098,"start":47.,"phase":1.,"inner":True}
        mat = Material(35.,35./1.5,500./1.15,200000.)
        result = _transfer(panel,profile,h,mat,policy,vertical_diameter=12)
        self.assertEqual(result["status"],"CONDITIONAL_PRESSURE_SHEAR_TRANSFER")
        offset = result["offset_each_side_mm"]
        dia = result["diameter_mm"]
        self.assertGreater(offset,42.75)
        self.assertLessEqual(offset+dia/2+40,200)
        self.assertGreaterEqual(offset-42.75-(dia+12)/2,4*20/3)
        self.assertGreaterEqual(offset-30.75-(dia+12)/2,4*20/3)
        self.assertGreaterEqual(result["template_longitudinal_clearance_mm"],4*20/3)
        self.assertLessEqual(result["column_embedment_mm"],result["column_available_mm"])

    def test_aggregate_override_propagates_to_the_actual_level_grid(self):
        p = {"height":3000., "module":40., "phase":0., "start":48., "inner":False}
        self.assertTrue(level_grid({**p,"aggregate_mm":16.},14,50,40))
        self.assertEqual(level_grid({**p,"aggregate_mm":20.},14,50,40),{})
        raw = {"schema":BUILDING_SCHEMA,"source_data_sha256":"a"*64,"frame_method":FRAME_METHOD,
               "wall_hinge_aggregate_storeys":[],"decision_reference":"Project assumptions"}
        for d in [False,0.,-1.,float("inf"),"20"]:
            with self.assertRaises(ValueError):
                normalize_building_design({**raw,"maximum_aggregate_mm":d},source_data_sha256="a"*64)
        self.assertEqual(normalize_building_design({**raw,"maximum_aggregate_mm":22.4},
                         source_data_sha256="a"*64)["maximum_aggregate_mm"],22.4)

    def test_rotated_component_box_bounds_every_signed_corner(self):
        c=sqrt(.5)
        axes=((c,0,c),(-c,0,c),(0,-1,0))
        lo=[-3.,1.,-2.,-6.,2.]; hi=[7.,2.,3.,1.,4.]
        intervals=directional_actions(axes,(1.,0.),lo,hi)
        samples=[[] for _ in range(5)]
        for a,b,t,q1,q2 in product(*zip(lo,hi)):
            for dst,x in zip(samples,((a+b)/2-t,(a+b)/2+t,(a-b)/2,c*(q1-q2),c*(q1+q2))):
                dst.append(x)
        for values,(lower,upper) in zip(samples,intervals):
            self.assertAlmostEqual(min(values),lower)
            self.assertAlmostEqual(max(values),upper)
        with self.assertRaises(ValueError):
            directional_actions(axes,(1.,0.),hi,lo)

    def test_shell_governing_twist_stays_at_same_corner_and_in_its_combination(self):
        mesh = {"E":("A","B","C")}
        item = {"corners":[["E",p] for p in mesh["E"]], "axes":{"E":[1,0,0,0,0,1,0,-1,0]},
                "cases":{"G":{"Single Value":[[10,0,0,1,0],[0,0,8,4,0],[0,2,0,3,0]]}}}
        panel = {"shell_model":"Shell-Thick","width_direction":[1,0]}
        cases = {"G":{"spectral":False,"role":"WALL_STRENGTH"}}
        result = panel_shell_checks(panel,cases,item,mesh,None)
        self.assertEqual(result["expected_checks"],4)
        values = {(r["axis"],r["action"]):(r["demand"],r["point"]) for r in result["checks"]}
        self.assertEqual(values["Horizontal","Bending"],(10.,"A"))
        self.assertEqual(values["Vertical","Bending"],(8.,"B"))
        self.assertEqual(values["Horizontal","Transverse shear"],(4.,"B"))
        with self.assertRaisesRegex(ValueError,"POPULATION_MISMATCH"):
            panel_shell_checks(panel,cases,{**item,"corners":item["corners"][:-1]},mesh,None)
        bounds = item["cases"]["G"]["Single Value"]
        item["cases"]["G"] = {"Min":bounds,"Max":[[12,0,0,1,0],*bounds[1:]]}
        with self.assertRaisesRegex(ValueError,"ONE_STATE"):
            panel_shell_checks(panel,cases,item,mesh,None)
        cases["G"]["spectral"] = True
        bounded = panel_shell_checks(panel,cases,item,mesh,None)
        self.assertEqual(bounded["checks"][0]["demand"],12.)
        self.assertEqual(bounded["checks"][0]["basis"],"NATIVE_SCALAR_ENVELOPE_BOUND")

    def test_physical_height_and_frame_axes_at_the_negative_base(self):
        stories=[{"story":"B","lower_elevation_m":-5.15,"upper_elevation_m":0.,"height_m":5.15},
                 {"story":"1","lower_elevation_m":0.,"upper_elevation_m":4.5,"height_m":4.5},
                 {"story":"2","lower_elevation_m":4.5,"upper_elevation_m":9.,"height_m":4.5}]
        self.assertEqual(physical_height(stories)["total_m"],14.15)
        self.assertIsNone(physical_height(stories[::2]))
        axes=_csi_frame_axes([74.,0.,-5.15],[74.,0.,0.],90.)
        self.assertEqual(axes[0],[0.,0.,1.])
        self.assertAlmostEqual(axes[1][1],1.)
        self.assertAlmostEqual(axes[2][0],-1.)
