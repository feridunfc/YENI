"""Scoped Supervisor authority, expected populations, and short-link equilibrium."""
import unittest
from types import SimpleNamespace

from tbdy_next.engineering.g3_contract import ACCEPTED_G3, supervisor_decision
from tbdy_next.engineering.g4_accounting import check_accounting
from tbdy_next.engineering.g4_population import FAMILIES, _coupling_roles, freeze_population, identities
from tbdy_next.engineering.wall_channel_bond import combined_bond


class G4Tests(unittest.TestCase):
    def test_section_acceptance_rejects_a_copied_digest(self):
        with self.assertRaisesRegex(ValueError, "G3_REVIEWED_SECTION_VERIFICATION"):
            supervisor_decision({"contract_sha256":ACCEPTED_G3,"input_sha256":"other"})
        unrelated={"contract_sha256":"other","decision":"SUPERVISOR_REVIEW"}
        self.assertEqual(supervisor_decision(unrelated), unrelated)

    def test_an_incomplete_source_cannot_borrow_completed_rows(self):
        frozen=freeze_population({}, "input")
        self.assertTrue(frozen["unresolved"])
        with self.assertRaisesRegex(ValueError, "EXPECTED_POPULATION_UNAVAILABLE"):
            check_accounting(frozen, {}, {}, {"checks":[]})
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_EMPTY"):
            identities([{"id":"1"},{"id":"1"}],"id")
        self.assertEqual(len(dict(FAMILIES)),57)

    def test_coupling_classification_uses_two_distinct_physical_wall_supports(self):
        def wall(uid, start):
            return {"UniqueName":uid,**{"UniquePt"+str(i):str(start+i) for i in range(1,5)}}
        points={"1":(0,0,0),"2":(2,0,0),"3":(2,0,3),"4":(0,0,3),
                "5":(4,0,0),"6":(6,0,0),"7":(6,0,3),"8":(4,0,3),
                "9":(1,0,3),"10":(5,0,3),"11":(5,0,2)}
        beam=lambda uid,end:{"UniqueName":uid,"UniquePtI":"9","UniquePtJ":end}
        records=_coupling_roles([beam("A","10"),beam("B","11"),beam("C","3")],
                                [wall("X",0),wall("Y",4)],points)
        self.assertEqual(records["A"]["ends"],[["X"],["Y"]])
        self.assertEqual(records["A"]["status"],"WALL_TO_WALL_ROLE_REVIEW")
        self.assertEqual(records["B"]["status"],"NO_TWO_DIRECT_WALL_SUPPORTS")
        self.assertEqual(records["C"]["status"],"NO_TWO_DIRECT_WALL_SUPPORTS")

    def test_a_through_column_lap_checks_the_entire_finite_grid(self):
        from tbdy_next.engineering.wall_channel_ends import _maximum_translation_gap
        levels=[20.+j*50. for j in range(90)]
        self.assertAlmostEqual(_maximum_translation_gap(100.,levels),25.)
        self.assertAlmostEqual(_maximum_translation_gap(125.,levels),12.5)
        with self.assertRaisesRegex(ValueError,"NO_FULL_INTERIOR"):
            _maximum_translation_gap(125.,levels[:2])

    def test_corner_tie_chords_retain_the_clearance_error_and_physical_levels(self):
        from tbdy_next.engineering.wall_channel_ties import tie_families
        row={"points_mm":[(i,0.) for i in range(28)],"diameter_mm":14,"levels_mm":[80.,210.]}
        family,=tie_families("W31",{"crossties":[row]})
        self.assertEqual(len(family["segments"]),27)
        self.assertEqual(family["heights"],row["levels_mm"])
        self.assertGreater(family["segments"][1][2],0)
        self.assertEqual(family["segments"][-1][2],0)

    def test_a_bonded_tension_increment_requires_room_for_balancing_concrete(self):
        mat=SimpleNamespace(fck=30.,fcd=20.)
        zero=(0.,0.)
        def corner(uid, h):
            return ("E",uid,[(h,h),zero,zero],[zero]*5)
        def side(uid):
            return {"cuts":[{"combination":"G","tension_intervals":[
                {"node":uid,"z_m":0.,"element_intervals":{"native|E":[0.,0.]}}]}]}
        edges={"I":side("i"),"J":side("j")}
        def check(force):
            return combined_bond({"G":[corner("i",0.),corner("j",force)]}, edges,180.,400.,mat,100.,400.,1000.)
        self.assertTrue(check(40.)["satisfied"])
        self.assertFalse(check(4000.)["satisfied"])
        edges["J"]["cuts"][0]["tension_intervals"][0]["z_m"]=1.
        with self.assertRaisesRegex(ValueError,"PHYSICAL_SLICES"):
            check(40.)
