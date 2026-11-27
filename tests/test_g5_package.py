"""Counterexamples for the sealed pipeline and the W55 regional splice."""
from copy import deepcopy
from math import hypot
import unittest

from tbdy_next.engineering.building_stage_graph import BuildingStageGraph
from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.g2_contract import _reference
from tbdy_next.engineering.g4_contract import ACCEPTED_G4, ACCEPTED_VERIFICATION, supervisor_decision
from tbdy_next.engineering.g5_contract import (
    ACCEPTED_G5, ACCEPTED_G5_VERIFICATION, supervisor_decision as g5_supervisor_decision,
)
from tbdy_next.engineering.pipeline import stage_registry
from tbdy_next.engineering.wall_channel_lap import _donors, _min_count
from tbdy_next.engineering.wall_crank_restraint import bracket
from tbdy_next.engineering.wall_knuckle_restraint import audit_regional_cage_3d, solve_continuous_rod_on_ties
from tbdy_next.engineering.wall_lap_hoops import straight_lap_enclosure
from tbdy_next.engineering.wall_regional_shell import _admissible


class G5EvidenceTests(unittest.TestCase):
    def test_historical_certificate_and_changed_candidate(self):
        record, _ = _reference("g4_reviewed_verification.json")
        self.assertEqual(ACCEPTED_G4, record["contract_sha256"])
        self.assertEqual(ACCEPTED_VERIFICATION, _digest({k:v for k,v in record.items() if k!="verification_sha256"}))
        other = {"input_sha256":"other","evidence":{}}
        candidate = {**other,"contract_sha256":_digest(other)}
        self.assertEqual(supervisor_decision(candidate), candidate)
        with self.assertRaisesRegex(ValueError, "G4_CANDIDATE_SEAL_CHANGED"):
            supervisor_decision({**candidate,"input_sha256":"forged"})

    def test_g5_certificate_and_changed_candidate(self):
        record, _ = _reference("g5_reviewed_verification.json")
        self.assertEqual(ACCEPTED_G5, record["contract_sha256"])
        self.assertEqual(ACCEPTED_G5_VERIFICATION, _digest({k: v for k, v in record.items() if k != "verification_sha256"}))
        other = {"input_sha256": "other", "evidence": {}}
        candidate = {**other, "contract_sha256": _digest(other)}
        self.assertEqual(g5_supervisor_decision(candidate), candidate)
        with self.assertRaisesRegex(ValueError, "G5_CANDIDATE_SEAL_CHANGED"):
            g5_supervisor_decision({**candidate, "input_sha256": "forged"})

    def test_dag_rejects_fault_before_dependent_owner(self):
        graph = BuildingStageGraph(stage_registry(), "source")
        value = {"stage":"MODAL_SCHEMA_DISCOVERY","observed_fields":["case"],"count":1}
        for message, obj, source in (("WRONG_OUTPUT",{**value,"stage":"other"},"source"),
                                     ("INVALID_CONTENT",{**value,"observed_fields":[]},"source"),
                                     ("SOURCE_CHANGED",value,"other")):
            with self.assertRaisesRegex(ValueError, message):
                graph.validate("schema-discovery",obj,source)
            with self.assertRaisesRegex(ValueError, "BLOCKED"):
                graph.before("schema")
        graph.before("quick-geometry")
        graph.validate("schema-discovery",value,"source")
        graph.accepted("schema-discovery",value)
        graph.before("schema")
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            graph.before("schema-discovery")

    def test_donor_area_cannot_be_counted_twice_and_cutoffs_change_window_count(self):
        used, deficit = _donors([20.],[15.,25.],200.,150.,50.,20.,100.)
        self.assertEqual(sum(x["area_mm2"] for x in used),200.)
        self.assertEqual(deficit,{"level_mm":25.,"missing_area_mm2":100.})
        self.assertEqual(_min_count([50+i*100 for i in range(21)],2100),10)
        self.assertEqual(_min_count([150+i*100 for i in range(19)],2100),9)

    def test_local_force_equilibrium_needs_two_sided_tension(self):
        options=[{"slope":s,"horizontal_kn":40.} for s in (-.5,.5)]
        self.assertEqual(bracket(options,30.,.51),[])
        solution=bracket(options,30.,.25)
        h=sum(r["horizontal_used_kn"] for r in solution)
        v=sum(r["horizontal_used_kn"]*r["tie"]["slope"] for r in solution)
        self.assertAlmostEqual(v/h,.25)
        self.assertAlmostEqual(hypot(h,v),30.)

    def test_sufficient_steel_area_does_not_waive_lap_enclosure(self):
        faces={-1:{"lap_start_mm":0.,"lap_end_mm":1000.,"old_lap_track_mm":79.,"new_lap_track_mm":135.5}}
        group={"shape":[-155.5,-53.,50.,450.,False,False],"diameter_mm":8.}
        loops={"-1":{"groups":[group,deepcopy(group)],"stations":[
            {"stations_mm":list(range(25,1000,100))},{"stations_mm":list(range(75,1000,100))}],
            "hook_plane_separation_mm":10.}}
        layout={"diameter_mm":16.,"pitch_mm":100.,"offsets_by_station_mm":[100.]*10}
        result=straight_lap_enclosure(faces,loops,layout,400.,40.,16.,24.,20.)["-1"]
        self.assertFalse(result["satisfied"])
        self.assertEqual(result["installed_outside_verticals"],0)
        trial=next(r for r in result["supplementary_vertical_trials"] if r["diameter_mm"]==16.)
        self.assertEqual(trial["outside_centre_min_mm"]-trial["covered_centre_max_mm"],3.5)
        trial=next(r for r in result["supplementary_vertical_trials"] if r["diameter_mm"]==12.)
        self.assertLess(trial["interior_surface_clear_upper_mm"],trial["required_parallel_clear_mm"])

    def test_membrane_tension_and_core_shear_have_independent_limits(self):
        axes=((100.,100.,200.,200.),)*2
        zeros=((0.,0.),)*5
        self.assertTrue(_admissible(((50.,50.),(0.,0.),(0.,0.)),zeros,axes,400.,40.,15.,1.,.85))
        self.assertFalse(_admissible(((400.,400.),(0.,0.),(0.,0.)),zeros,axes,400.,40.,15.,1.,.85))
        self.assertFalse(_admissible(((0.,0.),)*3,(*zeros[:3],(0.,400.),(0.,0.)),axes,400.,40.,15.,1.,.85))

    def test_continuous_rod_tension_only_springs_and_equilibrium(self):
        reactions, max_m, max_v, res_v, res_m = solve_continuous_rod_on_ties(
            [100., 200., 800.], [(120., 30.)], 25., 14., 250.
        )
        self.assertEqual(reactions[2], 0.0)
        self.assertTrue(all(r >= 0.0 for r in reactions))
        self.assertAlmostEqual(sum(reactions), 30.0, places=6)
        self.assertLess(res_v, 1.0e-8)
        self.assertLess(res_m, 1.0e-8)
        self.assertGreater(max_m, 0.0)
        self.assertGreater(max_v, 0.0)

    def test_regional_cage_3d_audit_detects_cover_and_bar_collision(self):
        clear_segs = [
            ((100., -100., 80.), (500., -100., 80.), 12., "bar_a"),
            ((300., -70., 60.), (300., -70., 400.), 7., "bar_b"),
        ]
        ok = audit_regional_cage_3d(clear_segs, 400., 500., 40.)
        self.assertTrue(ok["satisfied"])
        self.assertEqual(ok["interfering_pairs"], 0)
        clash_segs = [
            ((100., -100., 80.), (500., -100., 80.), 12., "bar_a"),
            ((300., -118., 60.), (300., -118., 400.), 7., "bar_b"),
        ]
        bad = audit_regional_cage_3d(clash_segs, 400., 500., 40.)
        self.assertFalse(bad["satisfied"])
        self.assertEqual(bad["interfering_pairs"], 1)
        uncovered = [((100., -155., 80.), (500., -155., 80.), 8., "bar_c")]
        cov = audit_regional_cage_3d(uncovered, 400., 500., 40.)
        self.assertFalse(cov["satisfied"])
        self.assertEqual(cov["cover_violations"], 1)
