"""VS04-F source-only linkages. Synthetic data, not an ETABS live oracle."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.basis_linkage import review_basis_linkage
from tbdy_next.quick_checks import check_registry
from tools.review_vs04f_basis import replay_basis


def table(key, rows, units=None):
    fields=list(rows[0]) if rows else []
    units=units or {}
    return {"table_key":key,"status":"CAPTURED",
      "fields":fields,"row_count":len(rows),"rows":rows,
      "field_metadata":{"status":"OK","field_count":len(fields),
        "field_keys":fields,"units_by_field":{x:units.get(x,"") for x in fields}}}


def fixture():
    d={}
    d["Mass Summary by Story"]=table("Mass Summary by Story",[
      {"Story":"+3.00","UX":"20","UY":"20","UZ":"20"},
      {"Story":"+0.00","UX":"10","UY":"10","UZ":"10"}],
      {"UX":"ton","UY":"ton","UZ":"ton"})
    d["Mass Summary by Group"]=table("Mass Summary by Group",[
      {"Group":"All","MassX":"30","MassY":"30","MassZ":"30"}],
      {"MassX":"ton","MassY":"ton","MassZ":"ton"})
    d["Assembled Joint Masses"]=table("Assembled Joint Masses",[
      {"PointElm":"A","Story":"+3.00","UX":"20","UY":"20","UZ":"20"},
      {"PointElm":"B","Story":"+0.00","UX":"10","UY":"10","UZ":"10"}],
      {"UX":"ton","UY":"ton","UZ":"ton"})
    d["Mass Source Definition"]=table("Mass Source Definition",[
      {"Name":"MsSrc1","IsDefault":"Yes","SourceSelf":"Yes","SourceLoads":"Yes",
       "LoadPattern":"LC_LL","Multiplier":"0.3"},
      {"Name":"MsSrc1","IsDefault":"None","SourceSelf":"None","SourceLoads":"None",
       "LoadPattern":"LC_SDL","Multiplier":"1"}])
    d["Mass Summary by Diaphragm"]=table("Mass Summary by Diaphragm",[
      {"Story":"+3.00","Diaphragm":"D2","MassX":"0","MassY":"0"},
      {"Story":"+0.00","Diaphragm":"D1","MassX":"0","MassY":"0"}],
      {"MassX":"ton","MassY":"ton"})
    d["Load Case Definitions - Summary"]=table("Load Case Definitions - Summary",[
      {"Name":"Modal","Type":"Modal - Ritz"},
      {"Name":"RSX","Type":"Response Spectrum"},
      {"Name":"RSY","Type":"Response Spectrum"}])
    d["Modal Case Definitions - Ritz"]=table("Modal Case Definitions - Ritz",[
      {"Name":"Modal","MassSource":"MsSrc1","LoadType":"Accel","LoadName":"Accel UX",
       "MaxModes":"100","TargetRatio":"95"},
      {"Name":"Modal","MassSource":"None","LoadType":"Accel","LoadName":"Accel UY",
       "MaxModes":"None","TargetRatio":"95"}],
       {"TargetRatio":"%"})
    d["Load Case Definitions - Response Spectrum"]=table("Load Case Definitions - Response Spectrum",[
      {"Name":"RSX","MassSource":"Previous  (MsSrc1)","LoadName":"U1",
       "Function":"SYNTHETIC","TransAccSF":"10","CoordSys":"Global",
       "Angle":"0","ModalCase":"Modal","ModalCombo":"CQC",
       "DirCombo":"SRSS","EccenRatio":"0.05"},
      {"Name":"RSY","MassSource":"Previous  (MsSrc1)","LoadName":"U2",
       "Function":"SYNTHETIC","TransAccSF":"10","CoordSys":"Global",
       "Angle":"0","ModalCase":"Modal","ModalCombo":"CQC",
       "DirCombo":"SRSS","EccenRatio":"0.05"}],
       {"TransAccSF":"m/sec2","Angle":"deg"})
    d["Functions - Response Spectrum - TSC-2018"]=table("Functions - Response Spectrum - TSC-2018",[
      {"Name":"SYNTHETIC","Period":"0","Value":"0.08",
       "R":"7","D":"2.5","I":"1.5","Ss":"0.345","S1":"0.111",
       "Fs":"1.524","F1":"2.378","SDS":"0.52578","SD1":"0.263958"},
      {"Name":"SYNTHETIC","Period":"0.5","Value":"0.11",
       "R":"None","D":"None","I":"None","Ss":"None","S1":"None",
       "Fs":"None","F1":"None","SDS":"None","SD1":"None"}],
       {"Period":"sec","I":"sec"})
    d["Load Case Definitions - Damping - Modal"]=table("Load Case Definitions - Damping - Modal",[
      {"Name":"RSX","DampType":"Constant","ConstDamp":"0.05"},
      {"Name":"RSY","DampType":"Constant","ConstDamp":"0.05"}])
    d["Story Definitions"]=table("Story Definitions",[
      {"Tower":"T1","Story":"+3.00","Height":"3.00"},
      {"Tower":"T1","Story":"+0.00","Height":"3.00"}],
      {"Height":"m"})
    d["Tower and Base Story Definitions"]=table("Tower and Base Story Definitions",[
      {"Tower":"T1","BSName":"Base","BSElev":"-3.00"}],
      {"BSElev":"m"})
    d["Response Spectrum Modal Info"]={
      "table_key":"Response Spectrum Modal Info","status":"CAPTURE_ERROR",
      "error":"ETABS ret_code=1","fields":[],"rows":[],"row_count":0}
    probes=[{"table_key":k,"candidate_roles_not_approved":["UNAPPROVED"]} for k in d]
    src={"schema":"tbdy.next.vs04e.basis-source-probe.v1",
         "source_mode":"LIVE_ETABS","read_only_invariant_proven":True,
         "units_before":6,"units_after":6,
         "display_cases_before":[],"display_cases_after":[],
         "analysis_generation_proven":False,"schema_roles_approved":False,
         "table_reads":d,"candidate_tables":probes,"available_table_count":175}
    return {"schema":"tbdy.next.vs04e.basis-probe-receipt.v1",
            "source":src,"review":{"status":"SOURCE_CANDIDATES_OBSERVED_PENDING_REVIEW"}}


class SourceBindingsTest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture()

    def test_three_typed_source_groups_never_promote_code(self):
        r=review_basis_linkage(self.fixture)
        self.assertEqual(r["observed_component_count"],3)
        self.assertEqual(r["expected_component_count"],4)
        self.assertEqual(r["normative_checks_executed"],0)
        self.assertEqual(r["seismic_mass_final_kg"],None)
        self.assertEqual(r["beta_tE_X"],None)
        self.assertEqual(len(check_registry()),11)
        self.assertEqual(r["engineering_release"],"NOT_READY")
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")
        self.assertTrue(all(x["formal_compliance"]=="NOT_PROVEN" for x in r["components"]))
        self.assertEqual(r["components"][3]["status"],"NOT_PROVEN")

    def test_group_story_joint_masses_reconcile_without_diaph_approval(self):
        r=review_basis_linkage(self.fixture)
        x=r["components"][0]
        self.assertEqual(x["source_facts"]["story_sums"]["UX_ton"],"30")
        self.assertEqual(x["source_facts"]["joint_sums"]["UX_ton"],"30")
        self.assertEqual(x["source_facts"]["group_sums"]["UY_ton"],"30")
        self.assertTrue(all(x["source_facts"]["comparisons"].values()))
        self.assertIn("ZERO_DIAPHRAGM_MASS_REQUIRES_ASSIGNMENT_PROOF",x["caution_codes"])

    def test_exact_case_and_spectrum_source_link(self):
        r=review_basis_linkage(self.fixture)
        x=r["components"][1]
        self.assertEqual(x["source_facts"]["modal_combination"],"CQC")
        self.assertEqual(x["source_facts"]["function"],"SYNTHETIC")
        self.assertEqual(x["source_facts"]["case_factors"]["RSX"]["direction"],"U1")
        self.assertEqual(x["source_facts"]["case_factors"]["RSY"]["scale_m_s2"],"10")
        self.assertEqual(x["source_facts"]["function_parameters"]["I"],"1.5")
        self.assertIn("I_FIELD_UNITS_METADATA_IS_SEC_BUT_PARAMETER_IS_DIMENSIONLESS",
                      x["caution_codes"])

    def test_geometry_and_base_elevation_closed_only_source_shape(self):
        r=review_basis_linkage(self.fixture)["components"][2]
        self.assertEqual(r["source_facts"]["story_count"],2)
        self.assertEqual(r["source_facts"]["base_elevation_m"],"-3.00")
        self.assertEqual([x["height_m"] for x in r["source_facts"]["levels_bottom_up"]],
                         ["3.00","3.00"])

    def test_inconsistent_joint_mass_detected(self):
        f=deepcopy(self.fixture)
        f["source"]["table_reads"]["Assembled Joint Masses"]["rows"][0]["UX"]="30"
        r=review_basis_linkage(f)["components"][0]
        self.assertEqual(r["status"],"NOT_PROVEN")
        self.assertEqual(r["reason_codes"],["MASS_JOINT_STORY_GROUP_DISAGREEMENT"])

    def test_duplicate_joint_rejected(self):
        f=deepcopy(self.fixture)
        f["source"]["table_reads"]["Assembled Joint Masses"]["rows"][0]["PointElm"]="B"
        self.assertIn("ASSEMBLED_JOINT_IDENTITY_NOT_UNIQUE",
                      review_basis_linkage(f)["components"][0]["reason_codes"])

    def test_wrong_mass_unit_blocks_binding(self):
        f=deepcopy(self.fixture)
        f["source"]["table_reads"]["Mass Summary by Story"]["field_metadata"]["units_by_field"]["UX"]="kN"
        self.assertEqual(review_basis_linkage(f)["components"][0]["status"],"NOT_PROVEN")

    def test_zero_mass_mesh_nodes_cannot_hide_missing_mass(self):
        f=deepcopy(self.fixture)
        joints=f["source"]["table_reads"]["Assembled Joint Masses"]
        for i in range(120):
            joints["rows"].append({"PointElm":"Z"+str(i),"Story":"+3.00",
                                  "UX":"0","UY":"0","UZ":"0"})
        joints["row_count"]=len(joints["rows"])
        joints["rows"][0]["UX"]="20.5"
        result=review_basis_linkage(f)["components"][0]
        self.assertEqual(result["status"],"NOT_PROVEN")
        self.assertIn("MASS_JOINT_STORY_GROUP_DISAGREEMENT",result["reason_codes"])

    def test_bogus_spectrum_case_direction_blocks(self):
        f=deepcopy(self.fixture)
        f["source"]["table_reads"]["Load Case Definitions - Response Spectrum"]["rows"][0]["LoadName"]="U2"
        self.assertEqual(review_basis_linkage(f)["components"][1]["status"],"NOT_PROVEN")

    def test_spectrum_source_mul_validation(self):
        f=deepcopy(self.fixture)
        f["source"]["table_reads"]["Functions - Response Spectrum - TSC-2018"]["rows"][0]["SDS"]="0.8"
        self.assertIn("SDS_SD1_SOURCE_MULTIPLICATION_CONFLICT",
                      review_basis_linkage(f)["components"][1]["reason_codes"])

    def test_bad_story_height_fails_closed(self):
        f=deepcopy(self.fixture)
        f["source"]["table_reads"]["Story Definitions"]["rows"][1]["Height"]="5"
        self.assertEqual(review_basis_linkage(f)["components"][2]["status"],"NOT_PROVEN")

    def test_capture_source_changed_is_rejected(self):
        f=deepcopy(self.fixture)
        f["source"]["analysis_generation_proven"]=True
        self.assertEqual(review_basis_linkage(f)["status"],"SOURCE_REJECTED")

    def test_damping_unknown_blocks_spectrum_case(self):
        f=deepcopy(self.fixture)
        f["source"]["table_reads"]["Load Case Definitions - Damping - Modal"]["rows"][0]["ConstDamp"]="None"
        self.assertEqual(review_basis_linkage(f)["components"][1]["status"],"NOT_PROVEN")

    def test_no_raw_returns_unavailable(self):
        self.assertEqual(review_basis_linkage(None)["status"],"SOURCE_UNAVAILABLE")

    def test_offline_receipt_is_deterministic_and_protects_original(self):
        with TemporaryDirectory() as d:
            src=Path(d)/"raw.json"
            out=Path(d)/"review.json"
            src.write_text(json.dumps(self.fixture,sort_keys=True),encoding="utf-8")
            prev=src.read_bytes()
            result=replay_basis(src,out)
            self.assertEqual(src.read_bytes(),prev)
            self.assertEqual(result["engineering_release"],"NOT_READY")
            self.assertEqual(result["basis_linkage"]["observed_component_count"],3)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")),result)
            with self.assertRaises(ValueError):
                replay_basis(src,out)
            with self.assertRaises(ValueError):
                replay_basis(src,src)


if __name__=="__main__":
    unittest.main()
