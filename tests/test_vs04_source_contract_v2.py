"""VS04 pipeline v2: prove the one-table display dependency, not a false PASS.

This file tests the diagnostic arbiter with a small constructed stage summary.
No fake table values are treated as an independent numerical ETABS oracle.
Existing v1 receipt interpretation stays strictly byte-for-byte compatible.
"""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from tbdy_next.live_source_pipeline import (
    _v2_modal_display_resolution,
    evaluate_single_run_source_pipeline,
    _legacy_single_run_source_pipeline,
    _DIAGNOSTIC_STATUS,
)
from test_vs04_full_single_run import live_payload


def diagnostic_candidate():
    payload=live_payload("Modal")
    payload["analysis_sources"]["pipeline_contract_version"]="v2"
    payload.setdefault("capture_metadata",{})["vs04_same_session_capture"]=True
    # This stage is a diagnostic test double: values are not a numerical oracle.
    e=payload["vs04_basis_probe"]
    e.setdefault("table_reads",{})["Response Spectrum Modal Info"]={
        "status":"CAPTURE_ERROR","table_key":"Response Spectrum Modal Info",
        "error":"seven_list: ETABS ret_code=1",
        "fields":[],"rows":[],"row_count":0,
    }
    e["display_cases_before"]=[]
    g=payload["vs04_diaphragm_probe"]
    g["original_display_cases"]=[]
    g["temporary_display_cases"]=["RSX","RSY"]
    g["display_selection_restored"]=True
    g["spectrum_modal_original_selection"]={
        "status":"CAPTURE_ERROR","table_key":"Response Spectrum Modal Info",
        "error":"seven_list: ETABS ret_code=1",
        "fields":[],"rows":[],"row_count":0,
    }
    g["spectrum_modal_selected_cases"]["status"]="CAPTURED"
    g["spectrum_modal_selected_cases"]["row_count"]=200

    stage={
        "vs04_e":{
            "status":"SOURCE_CANDIDATES_OBSERVED_PENDING_REVIEW",
            "candidate_count":15,"observed_candidate_count":14,
            "candidates":[
                {"table_key":"OBSERVED_"+str(i),"status":"OBSERVED_UNAPPROVED",
                 "reason_codes":[]} for i in range(14)
            ]+[{"table_key":"Response Spectrum Modal Info","status":"NOT_PROVEN",
                "reason_codes":["ROWS_OR_FIELD_METADATA_NOT_CAPTURED"]}],
        },
        "vs04_f":{
            "status":"BASIS_SOURCE_PARTIAL_PENDING_ENGINEERING_REVIEW",
            "expected_component_count":4,"observed_component_count":3,
            "components":[
                {"component":name,"status":"SOURCE_CONTRACT_OBSERVED_UNAPPROVED",
                 "reason_codes":[]} for name in
                ("SEISMIC_MASS_RECONCILIATION","RESPONSE_SPECTRUM_CASE_BINDINGS",
                 "PHYSICAL_STORY_GEOMETRY")
            ] + [{"component":"SPECTRUM_MODAL_OUTPUT","status":"NOT_PROVEN",
                  "reason_codes":["ETABS_RESPONSE_SPECTRUM_MODAL_INFO_RET_CODE_NOT_ZERO"]}],
        },
        "vs04_g":{
            "status":"SOURCE_CAPTURES_PARTIAL",
            "source_expected_count":5,"source_success_count":4,
            "tables":[
                {"table_key":name,"source_status":"OBSERVED_UNAPPROVED",
                 "reason_codes":[]} for name in
                ("Diaphragm Definitions","Area Assignments - Diaphragms",
                 "Joint Assignments - Diaphragms")
            ]+[
                {"table_key":"Response Spectrum Modal Info",
                 "capture_phase":"original_selection",
                 "source_status":"NOT_PROVEN",
                 "reason_codes":["ETABS_TABLE_NOT_CAPTURED"]},
                {"table_key":"Response Spectrum Modal Info",
                 "capture_phase":"selected_RSX_RSY",
                 "source_status":"OBSERVED_UNAPPROVED",
                 "rows":200,"reason_codes":[]},
            ],
        },
        "vs04_h":{
            "status":"SOURCE_LINKAGE_OBSERVED_PENDING_ENGINEERING_REVIEW",
            "observed_source_component_count":4,
            "source_component_count":4,
            "mandatory_holds":["MODEL_GENERATION_NOT_PROVEN"],
        },
        "vs04_i":{
            "status":"SOURCE_NUMERICAL_RECONSTRUCTED_PENDING_ENGINEERING_REVIEW",
            "analytical_knot_consistency_count":26,
            "modal_source_rows":200,
            "reconstructed_modal_rows":200,
            "unexplained_modal_rows":0,
            "mandatory_holds":["MODEL_GENERATION_NOT_PROVEN"],
        },
        "vs04_j":{
            "status":"CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING",
            "conditional_eq_4_19_minimum_term_kn":"1355.185792361929752",
            "missing_authorities":["Vtx_PRE_BETA_NOT_PROVEN"],
            "normative_checks_executed":0,
        },
    }
    names=[
        ("vs04_e","BASIS_PROBE"),("vs04_f","BASIS_LINKAGE"),
        ("vs04_g","DIAPHRAGM_PROBE"),("vs04_h","DIAPHRAGM_LINKAGE"),
        ("vs04_i","SPECTRUM_RECONSTRUCTION"),("vs04_j","BASE_SHEAR_SCREENING")]
    summary=[{
        "check_id":check_id,"stage_key":key,"title":check_id,
        "status":("NOT_PROVEN" if key in ("vs04_e","vs04_f","vs04_g") else
                  "CONDITIONAL_ONLY_NOT_CODE_APPROVED" if key=="vs04_j" else
                  "SOURCE_OBSERVED_UNAPPROVED"),
        "source_status":stage[key]["status"],
        "applicability":"NOT_REVIEWED","formal_compliance":"NOT_PROVEN",
        "reason_codes":[],"source":"SAME_RUN_ARCHIVED_ETABS_CAPTURE"
    } for key,check_id in names]
    legacy={
        "stage":"VS04_E_TO_J_SAME_RUN_SOURCE_PIPELINE",
        "engineering_release":"NOT_READY","formal_compliance":"NOT_PROVEN",
        "regulatory_checks_executed":0,"same_analysis_generation_proven":False,
        "full_equivalent_base_shear_proven":False,
        "effective_drift_proven":False,
        "source_only":True,
        "status":"SOURCE_PIPELINE_EVALUATED_PENDING_ENGINEERING_REVIEW",
        "source_component_count":6,"source_observed_count":2,
        "conditional_component_count":1,
        "checks":summary,"stages":stage,
    }
    return payload,legacy


class Vs04SourceV2Contract(unittest.TestCase):
    def test_selected_output_reconciles_only_original_display_dependency(self):
        payload,legacy=diagnostic_candidate()
        r=_v2_modal_display_resolution(payload,legacy)
        self.assertEqual(r["status"],"SOURCE_DISPLAY_SELECTION_DEPENDENCY_RECONCILED")
        self.assertTrue(r["original_read_still_failed"])
        self.assertTrue(r["selected_case_read_observed"])
        self.assertEqual(r["selected_case_row_count"],200)
        self.assertFalse(r["analysis_generation_proven"])
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")

    def test_v2_e_f_g_counts_remain_partial_and_provenance_is_explained(self):
        payload,legacy=diagnostic_candidate()
        with patch("tbdy_next.live_source_pipeline._legacy_single_run_source_pipeline",
                   return_value=deepcopy(legacy)):
            result=evaluate_single_run_source_pipeline(payload)
        self.assertEqual(result["pipeline_contract_version"],"v2")
        self.assertEqual(result["source_observed_count"],2)
        self.assertEqual(result["source_diagnostic_resolved_count"],3)
        self.assertEqual(result["source_unresolved_count"],0)
        self.assertEqual(result["conditional_component_count"],1)
        for check, count in zip(result["checks"][:3],[(15,14),(4,3),(5,4)]):
            self.assertEqual(check["status"],_DIAGNOSTIC_STATUS)
            self.assertEqual(check["coverage"]["expected"],count[0])
            self.assertEqual(check["coverage"]["observed_in_original_stage"],count[1])
            self.assertEqual(check["coverage"]["unobserved_in_original_stage"],1)
            self.assertEqual(check["coverage"]["independent_selected_case_reconciliation_count"],1)
            self.assertIn("INITIAL_UNSELECTED_MODAL_INFO_RET_CODE_1",check["reason_codes"])
            self.assertTrue(check["missing_evidence"])
            self.assertEqual(check["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(result["checks"][-1]["status"],
                         "CONDITIONAL_ONLY_NOT_CODE_APPROVED")
        self.assertEqual(result["regulatory_checks_executed"],0)

    def test_other_missing_source_must_not_be_recovered_by_200_rows(self):
        payload,legacy=diagnostic_candidate()
        legacy["stages"]["vs04_e"]["candidates"][0]["status"]="NOT_PROVEN"
        r=_v2_modal_display_resolution(payload,legacy)
        self.assertEqual(r["status"],"NOT_PROVEN")
        self.assertIn("UNSELECTED_MODAL_ERROR_NOT_THE_ONLY_OPEN_SOURCE_DEPENDENCY",
                      r["reason_codes"])

    def test_missing_com_selection_provenance_blocks_recovery(self):
        payload,legacy=diagnostic_candidate()
        payload["capture_metadata"]["vs04_same_session_capture"]=False
        self.assertEqual(_v2_modal_display_resolution(payload,legacy)["status"],"NOT_PROVEN")

    def test_wrong_selected_mode_count_blocks_recovery(self):
        payload,legacy=diagnostic_candidate()
        payload["vs04_diaphragm_probe"]["spectrum_modal_selected_cases"]["row_count"]=199
        self.assertEqual(_v2_modal_display_resolution(payload,legacy)["status"],"NOT_PROVEN")

    def test_failed_spectral_independent_check_blocks_recovery(self):
        payload,legacy=diagnostic_candidate()
        legacy["stages"]["vs04_i"]["reconstructed_modal_rows"]=199
        self.assertEqual(_v2_modal_display_resolution(payload,legacy)["status"],"NOT_PROVEN")

    def test_swapped_unselected_error_not_silent_data(self):
        payload,legacy=diagnostic_candidate()
        payload["vs04_basis_probe"]["table_reads"]["Response Spectrum Modal Info"]["error"]="unknown"
        self.assertEqual(_v2_modal_display_resolution(payload,legacy)["status"],"NOT_PROVEN")

    def test_legacy_v1_synthetic_report_is_byte_compatible(self):
        payload=live_payload("Modal")
        payload["analysis_sources"].pop("pipeline_contract_version",None)
        expected=_legacy_single_run_source_pipeline(payload)
        actual=evaluate_single_run_source_pipeline(payload)
        self.assertEqual(actual,expected)
        self.assertNotIn("pipeline_contract_version",actual)
        self.assertEqual(actual["source_component_count"],6)
        self.assertEqual(actual["regulatory_checks_executed"],0)

    def test_unresolved_status_must_carry_nested_reason(self):
        payload,legacy=diagnostic_candidate()
        payload["vs04_basis_probe"]["table_reads"]["Response Spectrum Modal Info"]["error"]="unrecognized"
        with patch("tbdy_next.live_source_pipeline._legacy_single_run_source_pipeline",
                   return_value=deepcopy(legacy)):
            result=evaluate_single_run_source_pipeline(payload)
        self.assertEqual(result["source_diagnostic_resolved_count"],0)
        self.assertEqual(result["source_unresolved_count"],3)
        for check in result["checks"][:3]:
            self.assertEqual(check["status"],"NOT_PROVEN")
            self.assertTrue(check["reason_codes"])
            self.assertTrue(check["missing_evidence"])
        self.assertEqual(result["engineering_release"],"NOT_READY")


if __name__=="__main__":
    unittest.main()
