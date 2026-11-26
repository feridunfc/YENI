"""Closed-scope G2 decisions, physical serial cuts and scoped G3 references."""
import unittest
from copy import deepcopy

from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.g2_contract import ACCEPTED_G2, supervisor_decision
from tbdy_next.engineering.g3_capacity import compare_reference
from tbdy_next.engineering.wall_bridge_coordinated import window_grid
from tbdy_next.engineering.wall_bridge_layout import series_interface_checks
from tbdy_next.engineering.wall_bridge_routes import hoop_plan_gap


class CoordinatedBridgeTests(unittest.TestCase):
    def test_node_and_element_tractions_are_matched_before_taking_a_maximum(self):
        def edge(a,b):
            bands = {"CORNER|471-1":a,"NODE|471":b}
            upper = max(a[1],b[1])
            return {"cuts":[{"combination":"RS","equivalent_friction_demand_kn_m":upper,
                "tension_intervals":[{"z_m":z,"node":str(z),"lower_kn_m":min(a[0],b[0]),
                    "upper_kn_m":upper,"element_intervals":bands.copy()} for z in (0.,1.)]}]}
        left,right = edge([5.,8.],[85.,90.]),edge([6.,9.],[84.,90.])
        result = series_interface_checks({"I":left,"J":right},150.,1000.,400.,.85)
        self.assertEqual(result["combinations"][0]["tension_difference_upper_equivalent_kn_m"],6.)
        self.assertTrue(result["bond_satisfied"])
        changed = deepcopy(right)
        del changed["cuts"][0]["tension_intervals"][0]["element_intervals"]["NODE|471"]
        with self.assertRaises(ValueError):
            series_interface_checks({"I":left,"J":changed},150.,1000.,400.,.85)

    def test_physical_window_crops_cover_and_checks_minimum_full_metre(self):
        grid = window_grid(5150.,128.75,[-20.54,20.54],14.,40.,20.)
        self.assertEqual(grid["guaranteed_bars_per_m"],14)
        self.assertGreaterEqual(min(grid["levels_mm"]),47.)
        self.assertLessEqual(max(grid["levels_mm"]),5150.-47.)
        with self.assertRaisesRegex(ValueError,"CLEARANCE"):
            window_grid(5150.,128.75,[-16.,16.],14.,40.,20.)

    def test_external_return_can_clear_the_receiver_hoop_in_plan(self):
        self.assertAlmostEqual(hoop_plan_gap([(-120.,0.),(-10.,0.)],[0.],(1.,0.),800.,400.,40.),50.)
        self.assertEqual(hoop_plan_gap([(0.,20.),(120.,20.)],[0.],(1.,0.),800.,400.,40.),0.)


class ScopedContracts(unittest.TestCase):
    def test_supervisor_decision_cannot_be_transferred_to_another_packet(self):
        other = {"contract_sha256":"0"*64,"decision":"SUPERVISOR_REVIEW"}
        self.assertEqual(supervisor_decision(other),other)
        with self.assertRaisesRegex(ValueError,"REVIEWED_VERIFICATION"):
            supervisor_decision({"contract_sha256":ACCEPTED_G2,"input_sha256":"changed","evidence":{},"gaps":{}})

    def test_independent_comparison_checks_residual_and_equilibrium(self):
        basis = {"columns":{"A":{"cuts":{"static":{"radial_capacity_knm":20.}},
                                 "ts500_limit_kn":100., "tbdy_limit_kn":120.}},"beams":{}}
        reference = {"schema":"tbdy.next.g3-section-reference.v1","input_basis_sha256":_digest(basis),
                     "columns":{"A":{"static":{"capacity_knm":20.0001,"axial_residual_n":.00001,
                                               "perpendicular_residual_nmm":0.},
                                      "ts500_limit_kn":100., "tbdy_limit_kn":120.}},
                     "beams":{},"independent_methods_sha256":"reference"}
        basis["columns"]["A"]["cuts"]["spectral_box"] = {"radial_capacity_knm":20.}
        reference["input_basis_sha256"] = _digest(basis)
        reference["columns"]["A"]["spectral_box"] = deepcopy(reference["columns"]["A"]["static"])
        self.assertLess(compare_reference(basis,reference)["maximum_residuals"]["column_capacity_knm"],.001)
        reference["columns"]["A"]["static"]["capacity_knm"] += .02
        with self.assertRaisesRegex(ValueError,"RESIDUAL"):
            compare_reference(basis,reference)
        reference["input_basis_sha256"] = "stale"
        with self.assertRaisesRegex(ValueError,"INPUTS_CHANGED"):
            compare_reference(basis,reference)
