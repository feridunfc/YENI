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

    def test_dowels_stay_inside_project_cover_and_develop_the_native_edge_tension(self):
        from tbdy_next.column_engine.section_capacity import Material
        profile = {"depth_mm":800., "cover":40., "tie":10., "bar_diameter":16.,
                   "bar_offsets":[85.5*i for i in range(-4,5)], "fck":35., "fcd":35./1.5}
        panel = {"thickness_m":.4,"span_m":3.,"clear_length_m":2.2}
        h = {"cover_mm":40.,"diameter_mm":12,"curtain_inset_mm":99.25,
             "cuts":[{"combination":"soil","pressure_kn_m2":54.,"reaction_bound_kn_m":101.25}]}
        policy = {"aggregate_mm":20., "height":5150., "module":49.56862745098,"start":47.,"phase":1.,"inner":True}
        mat = Material(35.,35./1.5,500./1.15,200000.)
        result = _transfer(panel,profile,h,mat,policy,vertical_diameter=12)
        self.assertEqual(result["status"], "HOLD")
        h["curtain_inset_mm"] = 12.
        cut = {"combination":"soil","max_native_shear_kn_m":100.,"native_shear_kn_m":100.,
               "normal_tension_kn_m":50.,"equivalent_friction_demand_kn_m":130.}
        result = _transfer(panel,profile,h,mat,policy,vertical_diameter=12,native_edge={"cuts":[cut]})
        self.assertEqual(result["status"],"CONDITIONAL_PRESSURE_SHEAR_TRANSFER")
        self.assertEqual(result["peak_reaction_kn_m"],130.)
        self.assertAlmostEqual(result["peak_ratio"],max(130/result["steel_resistance_kn_m"],100/result["concrete_limit_kn_m"]))
        offset, dia = result["offset_each_side_mm"], result["diameter_mm"]
        self.assertLess(offset, 130.)
        self.assertGreaterEqual(118.-offset-(dia+12)/2,4*20/3)
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

    def test_same_face_equilibrium_with_tension_twist_and_both_signs(self):
        from tbdy_next.engineering.wall_membrane_design import required_face_forces
        membrane = [(100.,100.),(0.,0.),(4.,4.)]
        moment = [(10.,10.),(0.,0.),(2.,2.)]
        # z=0.2 m, opposite face forces average to the membrane tensor and
        # their first moment recovers the CSI bending tensor with its signed face convention.
        self.assertEqual(required_face_forces(membrane,moment,-1,.2)[:2],(112.,12.))
        self.assertEqual(required_face_forces(membrane,moment,1,.2)[:2],(8.,8.))
        self.assertGreater(required_face_forces(membrane,moment,1,.2)[2],0.)

    def test_through_bar_requires_both_sides_and_full_stress_reversal_bond(self):
        from tbdy_next.column_engine.section_capacity import Material
        from tbdy_next.engineering.basement_pier_design import _through_bar_proof
        mat=Material(35.,35./1.5,500./1.15,200000.)
        end={"anchorage_type":"STRAIGHT","fits_column":True,"position_i_mm":635.,"column_depth_mm":800.,
             "specified_embedment_mm":635.,"column_available_mm":750.,"column":"C","wall_side_available_mm":900.,
             "wall_side_required_mm":635.}
        h={"diameter_mm":12.,"first_station_mm":46.,"pitch_mm":100.,"layers":10,"curtain_inset_mm":0.,
           "cover_mm":40.,"guaranteed_bars_per_m":10}
        design={"status":"PROPOSED_COMBINED_CURTAINS","ends":{"I":end,"J":end},"horizontal":h,
                "membrane_and_plate":{"lever_arm_mm":230.}}
        panels=[({"member":p,"span_m":3.,"thickness_m":.4,"native_support_edges":{side:{"nodes":["p"]}}},side)
                for p,side in (("L","J"),("R","I"))]
        def states(n):
            return {p:{"D":[("e","p",[(n,n),(0,0),(0,0)],[(0,0)]*5)]} for p in ("L","R")}
        passed=_through_bar_proof(panels,[design,design],states(200.),mat)
        self.assertEqual(passed["one_piece_length_mm"],6470.)
        self.assertLess(passed["governing"]["ratio"],1.)
        self.assertIsNone(_through_bar_proof(panels,[design,design],states(700.),mat))
        self.assertIsNone(_through_bar_proof(panels,[design,{**design,"horizontal":{**h,"first_station_mm":49.}}],states(200.),mat))

    def test_interior_nodal_transfer_uses_both_elements_and_the_native_tributary_height(self):
        from tbdy_next.engineering.wall_support_edge import _nodal_tractions
        rows=[[60.,0.,40.,0.,0.,0.],[-10.,0.,20.,0.,0.,0.]]
        coords={"i":[0.,0.,0.],"p":[0.,0.,1.],"j":[0.,0.,4.]}
        edge={"areas":{"w":{"corners":[["a","p"],["b","p"]],"cases":{"D":{"Single Value":rows}}}},
              "point_bases":{"p":[coords["p"],[1.,0.,0.,0.,1.,0.,0.,0.,1.]]}}
        row=_nodal_tractions(edge,"w",["i","p","j"],coords,[1.,0.],{"D":{"spectral":False}})["D"][0]
        self.assertEqual(row["tributary_height_m"],2.)
        self.assertEqual(row["equivalent_friction_demand_kn_m"],30.+.6*25.)

    def test_hook_has_mandrel_tail_cover_and_both_face_clearances(self):
        from tbdy_next.engineering.basement_wall_connection import _hook_90
        profile={"depth_mm":900.,"width_mm":1200.,"cover":40.,"tie":10.,
                 "bar_coordinates":[(-400.,0.),(400.,0.)],"bar_diameter":16.}
        h=_hook_90(profile,"I",140.,16.,800.,850.,26.7)
        self.assertEqual((h["inside_diameter_mm"],h["straight_tail_mm"],h["required_projection_mm"]),(96.,192.,600.))
        self.assertIsNone(_hook_90(profile,"I",140.,16.,800.,595.,26.7))

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
