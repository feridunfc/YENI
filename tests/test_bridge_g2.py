"""Serial interfaces, receiving-cage clearance and Supervisor candidate evidence."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.design_dependencies import _uncredited_directions
from tbdy_next.engineering.g2_contract import _c29, _golden, _reference, verify_frame_evidence, verification_record
from tbdy_next.engineering.wall_bridge_layout import series_interface_checks
from tbdy_next.engineering.wall_bridge_trial import corridors


class SerialPlanes(unittest.TestCase):
    def setUp(self):
        def side(name,values):
            return {"cuts":[{"combination":"G+E","equivalent_friction_demand_kn_m":max(h for l,h in values),
                             "tension_intervals":[{"z_m":i,"node":name+str(i),"lower_kn_m":l,"upper_kn_m":h}
                                                  for i,(l,h) in enumerate(values)]}]}
        self.edges={"I":side("i",[(260,300),(5,10)]),"J":side("j",[(250,280),(295,301)])}

    def test_equal_face_peaks_do_not_bound_same_height_jump(self):
        result=series_interface_checks(self.edges,400,600,400,.85)
        row,=result["combinations"]
        self.assertEqual(row["series_demand_kn_m"],301)
        self.assertEqual(row["face_envelope_difference_kn_m"],1)
        self.assertEqual(row["tension_difference_upper_equivalent_kn_m"],296)
        self.assertTrue(result["friction_satisfied"])
        self.assertFalse(result["bond_satisfied"])
        self.assertEqual(row["governing_height"]["node_i"],"i1")

    def test_missing_or_duplicate_cases_and_different_levels_are_rejected(self):
        raw=self.edges["J"]["cuts"]
        for changed in ([],raw*2,[{**raw[0],"combination":"Different"}]):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                series_interface_checks({**self.edges,"J":{"cuts":changed}},400,600,400,.85)
        self.edges["J"]["cuts"][0]["tension_intervals"][0]["z_m"]=-1
        with self.assertRaises(ValueError):
            series_interface_checks(self.edges,400,600,400,.85)

    def test_registered_boundary_leaves_no_intermediate_14mm_corridor(self):
        stations=[(57.,14.),(133.2222222222,14.)]
        fourteen=corridors(stations,0.,153.,14.,20.)
        eight=corridors(stations,0.,156.,8.,20.)
        self.assertEqual(len(fourteen),1)
        self.assertAlmostEqual(fourteen[0][1],16.3333333333)
        self.assertTrue(any(lo<95<hi for lo,hi in eight))


class ClosureEvidence(unittest.TestCase):
    def test_golden_and_c29_source_census(self):
        self.assertEqual(_golden()["records"],44)
        source,_=_reference("g2_c29_reference.json")
        self.assertEqual(_c29(source["model_sha256"])["faces"],24)
        with self.assertRaises(ValueError):
            _c29("0"*64)

    def test_feedback_requires_complete_signed_roster(self):
        p={"story_columns":{"S":["A","B"]}}
        no={"member_id":"B","numerator_eligible":False,"amplification_eligible":False}
        yes={"member_id":"A","numerator_eligible":True,"amplification_eligible":True}
        r={"story":"S","direction":"X","combination":"EX","status":"QUALIFIED_REFERENCE",
           "alpha":.8,"terms":[yes,no]}
        record={"required_seismic_combinations":["EX"],"final_qualification":{"cases":[r]}}
        self.assertEqual(_uncredited_directions(record,p,"B","S"),["X"])
        r["terms"]=[no,no]
        self.assertEqual(_uncredited_directions(record,p,"B","S"),[])

    def test_packet_files_match_sealed_stage(self):
        def packet(doc):
            return {**doc,"contract_sha256":_digest(doc)}
        a=packet({"input_sha256":"test"})
        b=packet({"input_sha256":"test","g1_contract_sha256":a["contract_sha256"],"gaps":{},"evidence":{}})
        values={"g1_contract":a,"g2_contract":b}
        with TemporaryDirectory() as root:
            folder=Path(root)
            for k,v in values.items():
                (folder/(k.replace("_","-")+".json")).write_text(json.dumps(v),encoding="utf-8")
            self.assertEqual(verification_record(folder,values,"test")["contract_sha256"],b["contract_sha256"])
            (folder/"g2-contract.json").write_text("{}",encoding="utf-8")
            with self.assertRaises(ValueError):
                verification_record(folder,values,"test")

    def test_physical_example_and_exhaustion(self):
        doc,_=_reference("g2_frame_examples.json")
        self.assertTrue(verify_frame_evidence(doc)["positive"]["cage_changes"])
        altered=deepcopy(doc)
        altered["positive"]["cases"][0]["factor"]=.5
        with self.assertRaises(ValueError):
            verify_frame_evidence(altered)
