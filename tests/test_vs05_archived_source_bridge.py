"""VS05 ARCH-D3 source-bound candidate compilation and FCR tests.

The synthetic fixture mimics exact real ETABS table field identities and
units, but never constitutes an approved model or normative oracle.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from tbdy_next.archived_source_bridge import (
    compile_archived_source_candidate, RESULT_SCHEMA,
)
from tbdy_next.compiled_dag import (
    CompilationRejected, RegulatoryCompiler, read_candidate_catalog,
)
from tools.audit_vs05_archived_run import audit_archived_run

CATALOG=Path(__file__).resolve().parents[1]/"config"/"dag"/"tbdy_r1c_94_candidate.json"


def t(key,rows,units=None):
    fields=list(rows[0])
    return {
        "table_key":key, "status":"CAPTURED",
        "fields":fields, "rows":rows,"row_count":len(rows),
        "field_metadata":{
            "status":"OK","field_keys":fields,
            "units_by_field":{x:(units or {}).get(x,"") for x in fields}
        },
    }


def source_report():
    basis={
        "schema":"tbdy.next.vs04e.basis-source-probe.v1",
        "read_only_invariant_proven":True,
        "units_before":6,"units_after":6,
        "table_reads":{
            "Story Definitions":t("Story Definitions",[
                {"Tower":"T1","Story":"+4.50","Height":"4.5","GUID":"g-top"},
                {"Tower":"T1","Story":"+0.00","Height":"5.15","GUID":"g-bottom"},
            ],{"Height":"m"}),
            "Tower and Base Story Definitions":t(
                "Tower and Base Story Definitions",
                [{"Tower":"T1","BSName":"Base","BSElev":"-5.15","GUID":"g-base"}],
                {"BSElev":"m"}),
            "Load Case Definitions - Summary":t(
                "Load Case Definitions - Summary",
                [{"Name":"Modal","Type":"Modal - Ritz","GUID":"g-modal"},
                 {"Name":"RSX","Type":"Response Spectrum","GUID":"g-x"},
                 {"Name":"RSY","Type":"Response Spectrum","GUID":"g-y"}]),
            "Load Case Definitions - Response Spectrum":t(
                "Load Case Definitions - Response Spectrum",
                [{"Name":"RSX","ModalCase":"Modal","LoadName":"U1","Function":"RESP_YATAY"},
                 {"Name":"RSY","ModalCase":"Modal","LoadName":"U2","Function":"RESP_YATAY"}]),
            "Load Combination Definitions":t(
                "Load Combination Definitions",
                [{"Name":"E1","Type":"Linear Add","LoadName":"RSX","SF":"1"}])
        }
    }
    geometry={
        "schema":"tbdy.next.geometry.capture.v2",
        "present_units":6,"present_units_after":6,
        "unit_state_unchanged":True,
        "tables":{
            "FRAME_ASSIGNMENTS":t("Frame Assignments - Summary",[
                {"Story":"+0.00","UniqueName":"72","Type":"Column"},
                {"Story":"+4.50","UniqueName":"100","Type":"Beam"},
                {"Story":"+4.50","UniqueName":"900","Type":"Null"},
            ]),
            "COLUMN_CONNECTIVITY":t("Column Object Connectivity",[
                {"Story":"+0.00","UniqueName":"72","UniquePtI":"P1","UniquePtJ":"P2"}]),
            "BEAM_CONNECTIVITY":t("Beam Object Connectivity",[
                {"Story":"+4.50","UniqueName":"100","UniquePtI":"P3","UniquePtJ":"P4"}]),
        }
    }
    return {
        "schema":"tbdy.next.complete.engineering.report.v1",
        "model":"kompakt_b.EDB","run_id":"RUN-"+"a"*32,
        "source_mode":"LIVE_ETABS",
        "formal_compliance":"NOT_PROVEN",
        "engineering_release":"NOT_READY",
        "source_provenance":{"input_sha256":"b"*64},
        "source_snapshot":{
            "source_mode":"LIVE_ETABS",
            "analysis_sources":{"analysis_generation_proven":False},
            "geometry_capture":geometry,"vs04_basis_probe":basis,
        }
    }


class Vs05RealSourceCandidateD3(unittest.TestCase):
    def setUp(self):
        self.compiler=RegulatoryCompiler(read_candidate_catalog(CATALOG))
        self.data=source_report()

    def test_source_to_typed_facts_to_frozen_plan_to_fcr(self):
        x=compile_archived_source_candidate(self.data,self.compiler)
        self.assertEqual(x["schema"],RESULT_SCHEMA)
        self.assertEqual(x["run_id"],self.data["run_id"])
        self.assertEqual(x["status"],"LIVE_ARCHIVE_DERIVED_CANDIDATE_ONLY")
        self.assertEqual(x["candidate_physical_summary"]["candidate_column_frame_count"],1)
        self.assertEqual(x["candidate_physical_summary"]["candidate_beam_frame_count"],1)
        self.assertEqual(x["candidate_physical_summary"]["candidate_structural_frame_count"],2)
        self.assertEqual(x["candidate_physical_summary"]["non_column_beam_type_counts"],
                         {"Null":1})
        self.assertEqual(x["candidate_physical_summary"]["missing_frame_connection_count"],0)
        self.assertEqual(x["candidate_combo_summary"]["raw_combo_definition_row_count"],1)
        self.assertEqual(x["candidate_combo_summary"]["typed_combo_definitions_executed"],0)
        self.assertEqual(x["profile_review"]["candidate_upper_story_ids"],["+0.00","+4.50"])
        self.assertEqual(x["profile_review"]["upper_story_without_captured_vertical_members"],
                         ["+4.50"])
        self.assertFalse(x["profile_review"]["full_model_census_proven"])
        self.assertEqual(x["candidate_plan"]["expected_check_instance_count"],6)
        self.assertEqual(x["fcr"]["expected_count"],6)
        self.assertEqual(x["fcr"]["reconciled_count"],6)
        self.assertEqual(x["fcr"]["not_proven_count"],6)
        self.assertEqual(x["fcr"]["pass_count"],0)
        self.assertFalse(x["model_analysis_generation_proven"])
        self.assertEqual(x["formal_compliance"],"NOT_PROVEN")

    def test_missing_story_definitions_hard_reject(self):
        a=deepcopy(self.data)
        del a["source_snapshot"]["vs04_basis_probe"]["table_reads"]["Story Definitions"]
        with self.assertRaisesRegex(CompilationRejected,"SOURCE_TABLE_NOT_CAPTURED"):
            compile_archived_source_candidate(a,self.compiler)

    def test_duplicate_connection_and_wrong_story_rejected(self):
        for mode in ("duplicate","unknown"):
            a=deepcopy(self.data)
            rows=a["source_snapshot"]["geometry_capture"]["tables"]["COLUMN_CONNECTIVITY"]["rows"]
            if mode=="duplicate":
                rows.append(deepcopy(rows[0]))
                a["source_snapshot"]["geometry_capture"]["tables"]["COLUMN_CONNECTIVITY"]["row_count"]=2
            else:
                rows[0]["Story"]="NOT_A_STORY"
            with self.subTest(mode=mode),self.assertRaises(CompilationRejected):
                compile_archived_source_candidate(a,self.compiler)

    def test_geometry_type_mismatch_rejected(self):
        a=deepcopy(self.data)
        a["source_snapshot"]["geometry_capture"]["tables"]["FRAME_ASSIGNMENTS"]["rows"][0]["Type"]="Beam"
        with self.assertRaisesRegex(CompilationRejected,"CONNECTIVITY_DISAGREEMENT"):
            compile_archived_source_candidate(a,self.compiler)

    def test_bad_units_or_wrong_generation_fail_closed(self):
        a=deepcopy(self.data)
        a["source_snapshot"]["vs04_basis_probe"]["table_reads"]["Story Definitions"]["field_metadata"]["units_by_field"]["Height"]="ft"
        with self.assertRaisesRegex(CompilationRejected,"SOURCE_UNIT"):
            compile_archived_source_candidate(a,self.compiler)
        a=deepcopy(self.data)
        a["source_snapshot"]["analysis_sources"]["analysis_generation_proven"]=True
        with self.assertRaisesRegex(CompilationRejected,"GENERATION_STATE"):
            compile_archived_source_candidate(a,self.compiler)

    def test_case_direction_and_duplicate_case_rejected(self):
        a=deepcopy(self.data)
        rows=a["source_snapshot"]["vs04_basis_probe"]["table_reads"]["Load Case Definitions - Response Spectrum"]["rows"]
        rows[1]["LoadName"]="U1"
        with self.assertRaisesRegex(CompilationRejected,"CASE_OR_DIRECTION"):
            compile_archived_source_candidate(a,self.compiler)
        a=deepcopy(self.data)
        rows=a["source_snapshot"]["vs04_basis_probe"]["table_reads"]["Load Case Definitions - Summary"]["rows"]
        rows[2]["Name"]="RSX"
        with self.assertRaisesRegex(CompilationRejected,"DUPLICATE_SOURCE"):
            compile_archived_source_candidate(a,self.compiler)

    def test_zero_or_missing_combo_raw_data_does_not_fabricate_roles(self):
        a=deepcopy(self.data)
        a["source_snapshot"]["vs04_basis_probe"]["table_reads"]["Load Combination Definitions"]["status"]="CAPTURE_ERROR"
        with self.assertRaisesRegex(CompilationRejected,"SOURCE_TABLE_NOT_CAPTURED"):
            compile_archived_source_candidate(a,self.compiler)

    def test_run_id_and_original_receipt_provenance_not_changed(self):
        x=compile_archived_source_candidate(self.data,self.compiler)
        self.assertEqual(x["original_input_receipt_sha256_claim"],"b"*64)
        self.assertEqual(len(x["source_snapshot_sha256_canonical"]),64)
        self.assertNotEqual(x["source_snapshot_sha256_canonical"],"b"*64)
        self.assertIn("ORIGINAL",x.get("note","").upper()) # sidecar does not claim new live run

    def test_cli_verifies_archive_boundary_and_never_overwrites(self):
        with TemporaryDirectory() as root:
            target=Path(root)/"D3_ARCHIVE_SIDE_CAR.json"
            with patch("tools.audit_vs05_archived_run.build_complete_report",
                       return_value=deepcopy(self.data)) as verified:
                first=audit_archived_run(
                    receipts_root=Path(root),
                    run_id=self.data["run_id"],
                    catalog_file=CATALOG,output_file=target)
                self.assertEqual(verified.call_count,1)
                self.assertEqual(first["run_id"],self.data["run_id"])
                self.assertEqual(first["candidate_source_result"]["fcr"]["expected_count"],6)
                self.assertEqual(first["candidate_source_result"]["fcr"]["pass_count"],0)
                self.assertEqual(json.loads(target.read_text(encoding="utf-8")),first)
                with self.assertRaises(CompilationRejected):
                    audit_archived_run(
                        receipts_root=Path(root),run_id=self.data["run_id"],
                        catalog_file=CATALOG,output_file=target)

    def test_direct_unverified_file_is_never_accepted_by_cli(self):
        with TemporaryDirectory() as root:
            with self.assertRaises(Exception):
                audit_archived_run(
                    receipts_root=Path(root),run_id=self.data["run_id"],
                    catalog_file=CATALOG,
                    output_file=Path(root)/"NEW.json")


if __name__=="__main__":
    unittest.main()
