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
        profile["incident_walls"].append({**leg,"member":"B","direction":(0.,-1.)})
        double = wall_return_anchor(profile,panel,"J",8,125.,40.,92.,material,20.)
        self.assertEqual(double["available_by_face_mm"],[360.,360.])
        self.assertTrue(double["fits_column"])

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
