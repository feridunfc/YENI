"""VS05-ARCH-D2: typed candidate profile / nested combo / expected denominator.

All fixtures are deliberately synthetic; profile, combo book and check
enforcement authorities are DENIED pending real model census and approval.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import unittest

from tbdy_next.compiled_dag import (
    CompilationRejected, RegulatoryCompiler, assess_candidate_plan,
    read_candidate_catalog,
)
from tbdy_next.candidate_model_contracts import (
    review_model_profile_candidate,
    review_combo_book_candidate,
    compile_limited_source_candidates,
)

CATALOG=Path(__file__).resolve().parents[1]/"config"/"dag"/"tbdy_r1c_94_candidate.json"


def profile():
    return {
        "schema":"tbdy.next.vs05.typed-model-profile.candidate.v2",
        "project_id":"SYNTHETIC_PROJECT",
        "model_id":"SYNTHETIC_MODEL",
        "version":"candidate-1",
        "source_snapshot_sha256":"a"*64,
        "analysis_generation_id":None,
        "units":"kN_m_C",
        "stories":[
            {"story_id":"Base","role":"BASE_CANDIDATE",
             "elevation_m":"-5.15","height_m":None},
            {"story_id":"+0.00","role":"UPPER_CANDIDATE",
             "elevation_m":"0.00","height_m":"5.15"},
            {"story_id":"+4.50","role":"UPPER_CANDIDATE",
             "elevation_m":"4.50","height_m":"4.5"},
        ],
        "physical_elements":[
            {"element_id":"C1","story_id":"+0.00",
             "element_type":"COLUMN","point_i":"P1","point_j":"P2"},
            {"element_id":"W1","story_id":"+4.50",
             "element_type":"WALL","point_i":"P3","point_j":"P4"},
        ]
    }


def book():
    return {
        "schema":"tbdy.next.vs05.typed-combo-book.candidate.v2",
        "book_id":"SYNTHETIC_BOOK",
        "version":"candidate-1",
        "source_snapshot_sha256":"a"*64,
        "cases":[
            {"case_id":"D","source_case_guid":"source-D"},
            {"case_id":"L","source_case_guid":"source-L"},
            {"case_id":"RSX","source_case_guid":"source-RSX"},
            {"case_id":"RSY","source_case_guid":"source-RSY"},
        ],
        "combinations":[
            {"combo_id":"SUM_DL","operator":"SUM",
             "terms":[
                 {"ref_type":"CASE","ref_id":"D","factor":"1.2"},
                 {"ref_type":"CASE","ref_id":"L","factor":"1.6"},
             ]},
            {"combo_id":"SUM_X","operator":"SUM",
             "terms":[
                 {"ref_type":"COMBO","ref_id":"SUM_DL","factor":"1"},
                 {"ref_type":"CASE","ref_id":"RSX","factor":"1"},
             ]},
        ],
        "consumer_roles":[
            {"role_id":"COLUMN_DESIGN","source_ref_type":"COMBO",
             "source_ref_id":"SUM_X","requires_concurrent_vector":True},
            {"role_id":"RESPONSE_SPECTRUM_Y","source_ref_type":"CASE",
             "source_ref_id":"RSY","requires_concurrent_vector":False},
        ]
    }


class Vs05TypedCandidateContracts(unittest.TestCase):
    def test_profile_typed_story_member_inventory(self):
        x=review_model_profile_candidate(profile())
        self.assertEqual(x["candidate_upper_story_ids"],["+0.00","+4.50"])
        self.assertEqual(x["candidate_story_count"],3)
        self.assertEqual(x["candidate_element_count"],2)
        self.assertFalse(x["analysis_generation_proven"])
        self.assertFalse(x["full_model_census_proven"])
        self.assertFalse(x["profile_approval_proven"])
        self.assertEqual(x["formal_compliance"],"NOT_PROVEN")

    def test_combo_nested_sum_dag_and_roles_are_bounded(self):
        x=review_combo_book_candidate(book())
        self.assertEqual(x["case_count"],4)
        self.assertEqual(x["combination_count"],2)
        self.assertEqual(x["consumer_role_count"],2)
        self.assertTrue(x["nested_definition_acyclic"])
        self.assertFalse(x["complete_case_combo_population_proven"])
        self.assertFalse(x["combo_roles_approved"])

    def test_candidate_compiles_six_instances_and_reconciles_all(self):
        compiler=RegulatoryCompiler(read_candidate_catalog(CATALOG))
        out=compile_limited_source_candidates(compiler,profile(),book())
        self.assertEqual(out["expected_instance_count"],6)
        self.assertFalse(out["whole_building_expected_check_census_proven"])
        plan=out["plan"]
        self.assertEqual(plan["expected_check_instance_count"],6)
        self.assertFalse(plan["normative_execution_authorized"])
        result=assess_candidate_plan(plan,[])
        self.assertEqual(result["expected_count"],6)
        self.assertEqual(result["missing_count"],6)
        self.assertEqual(result["not_proven_count"],6)
        self.assertEqual(result["pass_count"],0)

    def test_unsafe_envelope_can_never_be_concurrent_design_vector(self):
        x=book()
        x["combinations"].append({
            "combo_id":"ENVELOPE_X","operator":"ENVELOPE_MAX",
            "terms":[{"ref_type":"COMBO","ref_id":"SUM_X","factor":"1"}],
        })
        x["consumer_roles"][0]["source_ref_id"]="ENVELOPE_X"
        with self.assertRaisesRegex(CompilationRejected,"NONCONCURRENT"):
            review_combo_book_candidate(x)

    def test_nested_nonconcurrent_operator_hidden_under_sum_rejected(self):
        x=book()
        x["combinations"].append({
            "combo_id":"ENV","operator":"SRSS",
            "terms":[{"ref_type":"CASE","ref_id":"RSX","factor":"1"}],
        })
        x["combinations"][1]["terms"][0]["ref_id"]="ENV"
        with self.assertRaisesRegex(CompilationRejected,"NONCONCURRENT"):
            review_combo_book_candidate(x)

    def test_nested_combo_cycle_and_unknown_source_rejected(self):
        x=book()
        x["combinations"][0]["terms"][0]={
            "ref_type":"COMBO","ref_id":"SUM_X","factor":"1"}
        with self.assertRaisesRegex(CompilationRejected,"CYCLIC_NESTED"):
            review_combo_book_candidate(x)
        x=book()
        x["combinations"][0]["terms"][0]["ref_id"]="UNDEFINED"
        with self.assertRaisesRegex(CompilationRejected,"UNKNOWN_CASE"):
            review_combo_book_candidate(x)

    def test_mismatched_source_snapshot_blocks_compiler(self):
        x=book()
        x["source_snapshot_sha256"]="b"*64
        compiler=RegulatoryCompiler(read_candidate_catalog(CATALOG))
        with self.assertRaisesRegex(CompilationRejected,"DIFFERENT_SOURCE"):
            compile_limited_source_candidates(compiler,profile(),x)

    def test_source_hash_must_be_exact_digest(self):
        x=profile()
        x["source_snapshot_sha256"]="wrong"
        with self.assertRaisesRegex(CompilationRejected,"SHA256_REQUIRED"):
            review_model_profile_candidate(x)

    def test_profile_generation_cannot_be_self_attested(self):
        x=profile()
        x["analysis_generation_id"]="trust-me"
        with self.assertRaisesRegex(CompilationRejected,"CANNOT_SELF_ATTEST"):
            review_model_profile_candidate(x)

    def test_duplicate_physical_element_and_story_rejected(self):
        x=profile()
        x["physical_elements"].append(deepcopy(x["physical_elements"][0]))
        with self.assertRaisesRegex(CompilationRejected,"DUPLICATE_ELEMENT"):
            review_model_profile_candidate(x)
        x=profile()
        x["stories"][1]["story_id"]="Base"
        with self.assertRaisesRegex(CompilationRejected,"DUPLICATE_OR_UNKNOWN_STORY_ROLE"):
            review_model_profile_candidate(x)

    def test_missing_member_is_explicit_not_silent_grain_elision(self):
        x=profile()
        x["physical_elements"]=[x["physical_elements"][0]]
        result=review_model_profile_candidate(x)
        self.assertEqual(result["upper_story_without_captured_vertical_members"],["+4.50"])
        compiler=RegulatoryCompiler(read_candidate_catalog(CATALOG))
        out=compile_limited_source_candidates(compiler,x,book())
        self.assertEqual(out["expected_instance_count"],6)

    def test_wrong_units_and_zero_height_rejected(self):
        x=profile()
        x["units"]="N_mm_MPa"
        with self.assertRaisesRegex(CompilationRejected,"SOURCE_UNITS"):
            review_model_profile_candidate(x)
        x=profile()
        x["stories"][1]["height_m"]="0"
        with self.assertRaisesRegex(CompilationRejected,"VALUE_INVALID"):
            review_model_profile_candidate(x)

    def test_ambiguous_duplicate_case_and_combo_names_rejected(self):
        x=book()
        x["cases"].append(deepcopy(x["cases"][0]))
        with self.assertRaisesRegex(CompilationRejected,"DUPLICATE_CASE"):
            review_combo_book_candidate(x)
        x=book()
        x["combinations"][0]["combo_id"]="RSX"
        with self.assertRaisesRegex(CompilationRejected,"DUPLICATE_COMBO"):
            review_combo_book_candidate(x)

    def test_none_of_the_declarations_promote_code_compliance(self):
        x=profile()
        y=book()
        x["approval_reference"]="I_APPROVE"
        y["approved"]=True
        compiler=RegulatoryCompiler(read_candidate_catalog(CATALOG))
        result=compile_limited_source_candidates(compiler,x,y)
        self.assertEqual(result["status"],"UNAPPROVED_CANDIDATE_PHYSICAL_SCOPE")
        self.assertEqual(result["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(result["engineering_release"],"NOT_READY")
        self.assertFalse(result["plan"]["normative_execution_authorized"])


if __name__=="__main__":
    unittest.main()
