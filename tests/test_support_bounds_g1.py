"""Regressions for conditional lower restraints, joint projections and frozen combination inputs."""
import unittest

from tbdy_next.column_engine.section_capacity import Material
from tbdy_next.engineering.basement_wall_connection import wall_return_anchor
from tbdy_next.engineering.column_effective_length import lower_support_factors, resolve_adopted_frame_k, SUPPORT_ENVELOPE
from tbdy_next.engineering.column_mat_support import BOUND
from tbdy_next.engineering.g1_contract import export_catalog, g1_contract


class SupportBoundsAndContract(unittest.TestCase):
    def test_each_lower_support_needs_its_native_identity(self):
        upper = {"basis":"FRAME_SECTION_REFERENCE","alpha_web":2.3}
        lower = {"basis":"MAT_ROTATIONAL_STIFFNESS_UNBOUND","horizontal_support":BOUND}
        ends = {"I":lower,"J":upper}
        branches = lower_support_factors(ends)
        self.assertEqual([r["alpha_i"] for r in branches], [1.,10.,None])
        k = max(r["k"] for r in branches)
        basis = {"sway":"SWAY_PERMITTED","k":k,"k_source":{"method":SUPPORT_ENVELOPE,"section":"alpha_web"}}
        self.assertEqual(resolve_adopted_frame_k(basis,ends)[1]["branches"], branches)
        with self.assertRaises(ValueError):
            resolve_adopted_frame_k({**basis,"k":branches[0]["k"]},ends)
        with self.assertRaises(ValueError):
            lower_support_factors({"I":{"basis":lower["basis"]},"J":upper})
        with self.assertRaises(ValueError):
            lower_support_factors({"I":{"basis":"WALL_BELOW_ROTATIONAL_STIFFNESS_UNBOUND","walls_below":[]},"J":upper})

    def test_one_sided_return_preserves_both_face_covers(self):
        material = Material(35.,35./1.5,500./1.15,200000.)
        panel = {"width_direction":(1.,0.),"clear_length_m":3.}
        leg = {"member":"A","across":True,"direction":(0.,1.),"thickness_mm":400.,"span_mm":3000.}
        profile = {"joint":"J","depth_mm":400.,"incident_walls":[leg]}
        single = wall_return_anchor(profile,panel,"J",8,125.,40.,92.,material,20.)
        self.assertEqual(single["available_by_face_mm"],[160.,360.])
        self.assertFalse(single["fits_column"])
        profile["full_corner_square"] = True
        double = wall_return_anchor(profile,panel,"J",8,125.,40.,92.,material,20.)
        self.assertEqual(double["available_by_face_mm"],[360.,360.])
        self.assertTrue(double["fits_column"])
        self.assertEqual(double["return_shape"],"CONTINUOUS_90_FULL_DEVELOPMENT_IN_RETURN")
        for path in double["bar_paths"]:
            a,b=path["points_mm"][-2:]
            self.assertAlmostEqual(a[0],b[0])
            self.assertGreaterEqual(b[1]-a[1],double["position_i_mm"])
        leg["span_mm"]=180.
        self.assertFalse(wall_return_anchor(profile,panel,"J",8,125.,40.,92.,material,20.)["fits_column"])

    def test_unit_couple_fields_and_strip_bound(self):
        from tbdy_next.engineering.mat_rotational_stiffness import strip_rotational_stiffness
        # Independent Simpson integration of equilibrium and complementary work.
        length,b,h,e,g,m,v,ks=2.4,.8,.9,34e6,14.16e6,.25,1.,14500.
        n=400
        def integral(fn):
            return length/(3*n)*sum((1 if i in (0,n) else 4 if i%2 else 2)*fn(i*length/n) for i in range(n+1))
        def q(x):return 12*(x-length/2)/length**3
        def moment(x):return 1-3*(x/length)**2+2*(x/length)**3
        def shear(x):return 6*x*(length-x)/length**3
        self.assertAlmostEqual(integral(q),0.)
        self.assertAlmostEqual(integral(lambda x:x*q(x)),1.)
        work=integral(lambda x:moment(x)**2/(e*m*b*h**3/12)+shear(x)**2/(5*g*b*h/6)+q(x)**2/(ks*b))
        k=strip_rotational_stiffness(length,b,h,e,g,m,v,ks)
        self.assertAlmostEqual(work*k,1.,places=8)
        self.assertLess(strip_rotational_stiffness(length,b,h,e,g,m,v,ks,footprint_half=.4),k)
        with self.assertRaises(ValueError):
            strip_rotational_stiffness(length,b,h,e,g,m,v,0.)

    def test_pin_credit_is_retained_in_storey_sum(self):
        from tbdy_next.engineering.column_effective_length import lower_support_factors
        mat = {"method":"MONOLITHIC_FOOTPRINT_FREE_STRIPS_LINEAR_WINKLER", "joint":"1",
               "k_theta_min_knm_rad":20., "alpha_i_upper":12., "column_ei_over_l_knm":60.,
               "leg_stiffness_knm_rad":[10.,10.]}
        ends = {"I":{"basis":"MAT_ROTATIONAL_STIFFNESS_UNBOUND", "joint_id":"1",
                     "horizontal_support":BOUND, "mat_rotation_bound":mat},
                "J":{"basis":"FRAME_SECTION_REFERENCE", "alpha_web":2.}}
        self.assertEqual([r["alpha_i"] for r in lower_support_factors(ends)], [1.,12.])
        self.assertIsNone(lower_support_factors(ends,storey_hinge=True)[-1]["alpha_i"])
        mat["joint"] = "stale"
        self.assertIsNone(lower_support_factors(ends)[-1]["alpha_i"])

    def test_elevation_bound_checks_all_phases_of_the_closed_hoops(self):
        from tbdy_next.engineering.wall_bridge_layout import best_hoop_phase_gap
        self.assertEqual(best_hoop_phase_gap([100.,120.,140.,160.,180.],80.,300.),10.)
        self.assertEqual(best_hoop_phase_gap([120.,200.],80.,300.),40.)

    def test_only_reviewed_contract_can_close(self):
        from unittest.mock import patch
        from tbdy_next.engineering import g1_contract as owner
        from tbdy_next.engineering.design_scenario import _digest
        packet={"scope":"isolated fixture","decision":"AWAITING_SUPERVISOR","gaps":{g:{"closure_ready":True} for g in owner.GAPS}}
        with patch.object(owner,"ACCEPTED_CONTRACT",_digest(packet)):
            accepted=owner.supervisor_decision(packet)
            self.assertTrue(all(r["status"]=="CLOSED" for r in accepted["gaps"].values()))
            self.assertEqual(owner.supervisor_decision({**packet,"scope":"other"})["decision"],"AWAITING_SUPERVISOR")
        self.assertEqual(packet["decision"],"AWAITING_SUPERVISOR")

    def test_deck_detects_a_changed_factor_or_operator(self):
        deck = 'COMBO "D" TYPE "Linear Add"\nCOMBO "D" LOADCASE "A" SF -0.25'
        row = {"ref_type":"CASE","ref":"A","factor":"-1/4"}
        graph = {"D":{"operator_etabs":"Linear Add","rows":[row]}}
        self.assertEqual(export_catalog(deck,graph,{"A":{}})[0]["D"]["terms"],[["CASE","A","-1/4"]])
        with self.assertRaises(ValueError):
            export_catalog(deck.replace("SF -","SF "),graph,{"A":{}})
        with self.assertRaises(ValueError):
            export_catalog(deck.replace("Linear Add","Envelope"),graph,{"A":{}})
        incomplete = g1_contract({},None,None,None,"x")
        self.assertFalse(any(r["closure_ready"] for r in incomplete["gaps"].values()))
