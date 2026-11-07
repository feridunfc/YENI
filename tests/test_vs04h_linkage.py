"""VS04-H deterministic source binding negative and positive oracles.

Synthetic fixtures have no independent ETABS/model-generation authority.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.diaphragm_linkage import review_vs04h_source
from tbdy_next.quick_checks import check_registry
from tools.review_vs04h_diaphragm import review_files


def _table(name, rows, units=None):
    fields=list(rows[0]) if rows else []
    units=units or {}
    return {"status":"CAPTURED","table_key":name,"rows":rows,"fields":fields,
            "row_count":len(rows),"field_metadata":{
                "status":"OK","field_keys":fields,
                "field_count":len(fields),
                "units_by_field":{x:units.get(x,"") for x in fields},
            }}


def _fixture():
    def area(story, label, unique, d):
        return {"Story":story,"Label":label,"UniqueName":unique,"Diaphragm":d}
    definitions=[{"Name":f"D{i}","Rigidity":"Semi-Rigid","GUID":f"GUID-{i}"}
                 for i in range(1,6)]
    a=[area("+9.00","F1","100","D3"),
       area("+4.50","F2","101","D2"),
       area("+0.00","F3","102","D1"),
       area("Base","F4","103","None")]
    j=[area("+9.00","131","200","D3"),
       area("+4.50","17","201","D2"),
       area("+0.00","128","202","D1"),
       area("+0.00","45","203","From Shell Object")]
    table={}
    for key,rows in (("Diaphragm Definitions",definitions),
                     ("Area Assignments - Diaphragms",a),
                     ("Joint Assignments - Diaphragms",j)):
        table[key]=_table(key,rows)
    modes=[]
    for case in ("RSX","RSY"):
        for mode in range(1,101):
            period=str(Decimal("0.5") / Decimal(mode))
            row={"SpecCase":case,"ModalCase":"Modal","Mode":str(mode),
                 "Period":period,"DampRatio":"0.05",
                 "U1Acc":"1.18" if case=="RSX" else "0",
                 "U2Acc":"1.18" if case=="RSY" else "0",
                 "U3Acc":"0",
                 "U1Amp":"-0.003" if case=="RSX" else "0",
                 "U2Amp":"-0.002" if case=="RSY" else "0",
                 "U3Amp":"0"}
            modes.append(row)
    modal_units={"Period":"sec",
                 "U1Acc":"m/sec2","U2Acc":"m/sec2","U3Acc":"m/sec2",
                 "U1Amp":"m","U2Amp":"m","U3Amp":"m"}
    capture={"schema":"tbdy.next.vs04g.diaphragm-modal-probe.v1",
             "source_mode":"LIVE_ETABS","units_before":6,"units_after":6,
             "original_display_cases":[],"temporary_display_cases":["RSX","RSY"],
             "display_selection_restored":True,
             "analysis_generation_proven":False,
             "eccentricity_applied_proven":False,
             "diaphragm_constraints_applied_proven":False,
             "diaphragm_tables":table,
             "spectrum_modal_original_selection":{
                 "status":"CAPTURE_ERROR","table_key":"Response Spectrum Modal Info",
                 "fields":[],"rows":[],"row_count":0,
                 "field_metadata":{"status":"OK",
                                   "field_keys":["SpecCase"]},
                 "error":"ETABS ret_code=1"},
             "spectrum_modal_selected_cases":_table(
                 "Response Spectrum Modal Info",modes,modal_units)}
    return {"schema":"tbdy.next.vs04g.diaphragm-source-receipt.v1",
            "source":capture,"review":{"source_success_count":4}}


def _prior(fixture):
    rows=fixture["source"]["spectrum_modal_selected_cases"]["rows"]
    return {"schema":"tbdy.next.vs04.offline-source-replay.v1",
            "input_sha256":"synthetic-never-real",
            "numeric_source_review":{"results":[{
                "component":"MODAL_PERIOD_FREQUENCY_IDENTITY",
                "status":"SOURCE_ARITHMETIC_OBSERVED",
                "items":[{"mode":r["Mode"],"period_sec":r["Period"]}
                         for r in rows if r["SpecCase"]=="RSX"]
            }]}}


from decimal import Decimal


class Vs04HLinks(unittest.TestCase):
    def setUp(self):
        self.data=_fixture()

    def test_all_four_source_links_do_not_grant_normative_authority(self):
        result=review_vs04h_source(self.data,prior_modal_replay=_prior(self.data))
        self.assertEqual(result["observed_source_component_count"],4)
        self.assertEqual(result["original_source_reads_observed"],4)
        self.assertEqual(result["original_source_reads_expected"],5)
        self.assertEqual(result["defined_but_unassigned_diaphragms"],["D4","D5"])
        self.assertEqual(result["components"][3]["source_facts"]["compared_to_vs04d_modal_modes"],100)
        self.assertEqual(result["components"][3]["source_facts"]["comparison_rows"],100)
        self.assertEqual(result["components"][1]["source_facts"]["explicit_none_count"],1)
        self.assertEqual(result["components"][2]["source_facts"]["from_shell_object_count"],1)
        self.assertEqual(result["regulatory_checks_executed"],0)
        self.assertFalse(result["accidental_eccentricity_applied_proven"])
        self.assertFalse(result["diaphragm_mass_explained"])
        self.assertEqual(result["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(result["engineering_release"],"NOT_READY")
        self.assertEqual(len(check_registry()),8)

    def test_no_modal_prior_still_reviews_source_only(self):
        result=review_vs04h_source(self.data)
        self.assertEqual(result["observed_source_component_count"],4)
        self.assertNotIn("compared_to_vs04d_modal_modes",
                         result["components"][3]["source_facts"])

    def test_invalid_source_scope_rejected(self):
        for prop,value in (("display_selection_restored",False),
                           ("units_after",7),
                           ("analysis_generation_proven",True),
                           ("eccentricity_applied_proven",True),
                           ("temporary_display_cases",["Modal"])):
            with self.subTest(prop=prop):
                inp=deepcopy(self.data)
                inp["source"][prop]=value
                self.assertEqual(review_vs04h_source(inp)["status"],"SOURCE_REJECTED")

    def test_duplicate_or_unknown_diaphragm_rejected(self):
        for prop, val in (("Name","D2"),("Rigidity","Unrecognized"),
                          ("GUID","GUID-2")):
            with self.subTest(prop=prop):
                inp=deepcopy(self.data)
                inp["source"]["diaphragm_tables"]["Diaphragm Definitions"]["rows"][0][prop]=val
                self.assertEqual(review_vs04h_source(inp)["components"][0]["status"],"NOT_PROVEN")

    def test_unknown_assignment_does_not_auto_register(self):
        inp=deepcopy(self.data)
        inp["source"]["diaphragm_tables"]["Area Assignments - Diaphragms"]["rows"][0]["Diaphragm"]="D99"
        self.assertEqual(review_vs04h_source(inp)["components"][1]["status"],"NOT_PROVEN")
        self.assertEqual(review_vs04h_source(inp)["components"][2]["status"],
                         "SOURCE_CONTRACT_OBSERVED_UNAPPROVED")

    def test_duplicate_point_identity_not_silently_counted(self):
        inp=deepcopy(self.data)
        inp["source"]["diaphragm_tables"]["Joint Assignments - Diaphragms"]["rows"][0]["UniqueName"]="201"
        self.assertEqual(review_vs04h_source(inp)["components"][2]["status"],"NOT_PROVEN")

    def test_per_case_modal_deduplication(self):
        inp=deepcopy(self.data)
        rows=inp["source"]["spectrum_modal_selected_cases"]["rows"]
        rows[1]["Mode"]="1"
        self.assertEqual(review_vs04h_source(inp)["components"][3]["status"],"NOT_PROVEN")

    def test_one_missing_spectrum_mode_blocks_source_fact(self):
        inp=deepcopy(self.data)
        t=inp["source"]["spectrum_modal_selected_cases"]
        t["rows"].pop()
        t["row_count"]-=1
        self.assertEqual(review_vs04h_source(inp)["components"][3]["status"],"NOT_PROVEN")

    def test_cross_direction_nonzero_rejected(self):
        inp=deepcopy(self.data)
        inp["source"]["spectrum_modal_selected_cases"]["rows"][0]["U2Acc"]="1.5"
        self.assertEqual(review_vs04h_source(inp)["components"][3]["status"],"NOT_PROVEN")

    def test_mismatched_rs_y_active_spectrum_acceleration_rejected(self):
        inp=deepcopy(self.data)
        inp["source"]["spectrum_modal_selected_cases"]["rows"][100]["U2Acc"]="1.19"
        self.assertIn("RSX_RSY_EQUAL_FUNCTION_MODAL_SOURCE_MISMATCH",
                      review_vs04h_source(inp)["components"][3]["reason_codes"])

    def test_mismatched_prior_vs04d_modal_period_rejected(self):
        prior=_prior(self.data)
        prior["numeric_source_review"]["results"][0]["items"][99]["period_sec"]="9.9"
        self.assertEqual(review_vs04h_source(
            self.data,prior_modal_replay=prior)["components"][3]["status"],"NOT_PROVEN")

    def test_wrong_period_or_acceleration_units_rejected(self):
        inp=deepcopy(self.data)
        inp["source"]["spectrum_modal_selected_cases"]["field_metadata"]["units_by_field"]["U1Acc"]="g"
        self.assertEqual(review_vs04h_source(inp)["components"][3]["status"],"NOT_PROVEN")

    def test_damping_or_nonfinite_modal_numbers_rejected(self):
        for field,value in (("DampRatio","0.2"),("Period","NaN"),("U1Acc","Infinity")):
            with self.subTest(field=field):
                inp=deepcopy(self.data)
                inp["source"]["spectrum_modal_selected_cases"]["rows"][0][field]=value
                self.assertEqual(review_vs04h_source(inp)["components"][3]["status"],"NOT_PROVEN")

    def test_offline_replay_immutable_input_and_fail_closed_output(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            inp=root/"source.json"
            prior=root/"prior.json"
            out=root/"review.json"
            inp.write_text(json.dumps(self.data,sort_keys=True),encoding="utf-8")
            prior.write_text(json.dumps(_prior(self.data),sort_keys=True),encoding="utf-8")
            original=inp.read_bytes()
            report=review_files(inp,out,prior)
            self.assertEqual(report["linkage"]["observed_source_component_count"],4)
            self.assertIsNotNone(report["prior_modal_replay_sha256"])
            self.assertFalse(report["source_raw_included"])
            self.assertEqual(original,inp.read_bytes())
            with self.assertRaises(ValueError):
                review_files(inp,out)
            with self.assertRaises(ValueError):
                review_files(inp,inp)

    def test_no_source_is_not_proven(self):
        self.assertEqual(review_vs04h_source(None)["status"],"SOURCE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
