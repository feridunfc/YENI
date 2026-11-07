"""VS05 candidate DAG and FCR invariants, using exact R1-C 94-node source.

No test or fixture claims an approved profile, combo-book, model generation,
or real-building regulatory PASS.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.compiled_dag import (
    CATALOG_SCHEMA, CompilationRejected, RegulatoryCompiler,
    assess_candidate_plan, canonical_json, read_candidate_catalog,
    validate_candidate_catalog,
)

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / "config" / "dag" / "tbdy_r1c_94_candidate.json"


def instances():
    return [
        {"check_instance_id":"BASE_SHEAR:X","node_id":"BASE_SHEAR",
         "subject_id":"X","grain":"GLOBAL_DIRECTION"},
        {"check_instance_id":"BASE_SHEAR:Y","node_id":"BASE_SHEAR",
         "subject_id":"Y","grain":"GLOBAL_DIRECTION"},
        {"check_instance_id":"STORY_DRIFT:X:+4.50","node_id":"STORY_DRIFT",
         "subject_id":"X:+4.50","grain":"STORY_DIRECTION"},
        {"check_instance_id":"STORY_DRIFT:Y:+4.50","node_id":"STORY_DRIFT",
         "subject_id":"Y:+4.50","grain":"STORY_DIRECTION"},
    ]


def profile():
    return {"schema":"tbdy.next.vs05.model_profile.candidate.v1",
            "profile_id":"SYNTHETIC_RESEARCH_ONLY",
            "version":"v0","source_model_sha256":"synthetic-source-sha",
            "approval_reference":"NOT_APPROVED"}


def book():
    return {"schema":"tbdy.next.vs05.combo_book.candidate.v1",
            "book_id":"SYNTHETIC_COMBOS",
            "version":"v0","combo_definition_sha256":"synthetic-combo",
            "approval_reference":"NOT_APPROVED"}


class Vs05CompiledDagTest(unittest.TestCase):
    def setUp(self):
        self.catalog=read_candidate_catalog(CATALOG)
        self.compiler=RegulatoryCompiler(self.catalog)

    def test_exact_94_node_140_edge_candidate_graph(self):
        result=validate_candidate_catalog(self.catalog)
        self.assertEqual(result["candidate_nodes"],94)
        self.assertEqual(result["candidate_dependency_edges"],140)
        self.assertEqual(result["source_gate_count"],16)
        self.assertEqual(result["derivation_count"],10)
        self.assertEqual(result["regulatory_candidate_count"],32)
        self.assertEqual(result["design_candidate_count"],36)
        self.assertEqual(result["candidate_check_node_count"],68)
        self.assertEqual(result["execution_authorized_nodes"],0)
        flat=[n for wave in result["topological_waves"] for n in wave]
        self.assertEqual(len(flat),94)
        self.assertEqual(len(flat),len(set(flat)))
        self.assertEqual(result["topological_waves"][0],["SOURCE_SHA_GATE"])
        self.assertEqual(result["formal_compliance"],"NOT_PROVEN")

    def test_catalog_original_identity_source_research_not_executable(self):
        self.assertEqual(self.catalog["schema"],CATALOG_SCHEMA)
        self.assertEqual(self.catalog["source_file"],"TBDY_DAG_94_Dugum(1).mmd")
        self.assertTrue(all(n["execution_authority"]=="DENIED"
                            for n in self.catalog["nodes"]))

    def test_candidate_plan_freezes_exact_explicit_check_instances(self):
        args=dict(model_profile=profile(),combo_book=book(),
                  expected_instances=instances())
        first=self.compiler.compile_candidate(**args)
        second=self.compiler.compile_candidate(**args)
        self.assertEqual(first,second)
        self.assertEqual(first["expected_check_instance_count"],4)
        self.assertEqual(first["catalog_candidate_check_node_count"],68)
        self.assertEqual(first["execution_authority"],"DENIED")
        self.assertEqual(first["status"],"CANDIDATE_PLAN_UNAUTHORIZED")
        self.assertFalse(first["model_profile_approval_proven"])
        self.assertFalse(first["combo_book_approval_proven"])
        self.assertFalse(first["analysis_generation_proven"])
        self.assertEqual([x["check_instance_id"] for x in first["expected_check_instances"]],
                         sorted(x["check_instance_id"] for x in first["expected_check_instances"]))
        self.assertEqual(len(first["plan_sha256"]),64)

    def test_report_filter_does_not_shrink_expected_instances(self):
        plan=self.compiler.compile_candidate(
            model_profile=profile(),combo_book=book(),
            expected_instances=instances())
        result=assess_candidate_plan(plan,[])
        self.assertEqual(result["expected_count"],4)
        self.assertEqual(result["submitted_count"],0)
        self.assertEqual(result["missing_count"],4)
        self.assertEqual(result["reconciled_count"],4)
        self.assertEqual(result["not_proven_count"],4)
        self.assertEqual(result["pass_count"],0)
        self.assertEqual(result["formal_compliance"],"NOT_PROVEN")

    def test_caller_supplied_pass_is_explicitly_blocked(self):
        plan=self.compiler.compile_candidate(
            model_profile=profile(),combo_book=book(),
            expected_instances=instances())
        recorded=[{"check_instance_id":"BASE_SHEAR:X","status":"PASS"}]
        result=assess_candidate_plan(plan,recorded)
        self.assertEqual(result["submitted_count"],1)
        self.assertEqual(result["missing_count"],3)
        self.assertEqual(result["not_proven_count"],4)
        entry=next(x for x in result["outcomes"] if x["check_instance_id"]=="BASE_SHEAR:X")
        self.assertEqual(entry["status"],"NOT_PROVEN")
        self.assertEqual(entry["source_outcome_status"],"PASS")
        self.assertEqual(entry["reason_codes"],["EXECUTION_AUTHORITY_DENIED_FOR_CANDIDATE_DAG"])
        self.assertEqual(entry["execution"],"BLOCKED")

    def test_duplicate_and_orphan_results_rejected(self):
        plan=self.compiler.compile_candidate(
            model_profile=None,combo_book=None,expected_instances=instances())
        for rows in (
            [{"check_instance_id":"BASE_SHEAR:X","status":"FAIL"}]*2,
            [{"check_instance_id":"NEW_BOGUS:99","status":"PASS"}],
            [{"check_instance_id":"BASE_SHEAR:X","status":"UNKNOWN"}],
        ):
            with self.subTest(rows=rows):
                with self.assertRaises(CompilationRejected):
                    assess_candidate_plan(plan,rows)

    def test_plan_hash_blocks_mutation_or_fake_execution(self):
        plan=self.compiler.compile_candidate(
            model_profile=profile(),combo_book=book(),expected_instances=instances())
        for mutate in ("expected", "authority", "profile"):
            with self.subTest(mutate=mutate):
                candidate=deepcopy(plan)
                if mutate=="expected":
                    candidate["expected_check_instances"].pop()
                elif mutate=="authority":
                    candidate["execution_authority"]="APPROVED"
                else:
                    candidate["model_profile_approval_proven"]=True
                with self.assertRaises(CompilationRejected):
                    assess_candidate_plan(candidate,[])

    def test_cycle_with_same_edge_count_rejected(self):
        data=deepcopy(self.catalog)
        byid={n["node_id"]:n for n in data["nodes"]}
        byid["SOURCE_SHA_GATE"]["depends_on"]=["FOUNDATION_TIE_BEAM"]
        byid["FOUNDATION_STRIP_SHEAR"]["depends_on"]=[]
        with self.assertRaisesRegex(CompilationRejected,"CYCLIC"):
            validate_candidate_catalog(data)

    def test_unknown_source_producer_and_changed_node_type_rejected(self):
        data=deepcopy(self.catalog)
        byid={n["node_id"]:n for n in data["nodes"]}
        byid["MODEL_PROFILE_GATE"]["depends_on"]=["NO_SUCH_SOURCE"]
        with self.assertRaisesRegex(CompilationRejected,"UNKNOWN_DEPENDENCY"):
            validate_candidate_catalog(data)
        data=deepcopy(self.catalog)
        data["nodes"][0]["execution_authority"]="GRANTED"
        with self.assertRaisesRegex(CompilationRejected,"DENIED"):
            validate_candidate_catalog(data)

    def test_duplicate_instance_and_ambiguous_grain_rejected(self):
        for records in (instances()+[instances()[0]],
                        [{**instances()[0],"grain":"UNKNOWN"}],
                        [{**instances()[0],"node_id":"SOURCE_SHA_GATE"}]):
            with self.subTest(records=records):
                with self.assertRaises(CompilationRejected):
                    self.compiler.compile_candidate(
                        model_profile=None,combo_book=None,
                        expected_instances=records)

    def test_missing_approvals_cannot_be_self_approved(self):
        proposal=profile()
        proposal["approval_reference"]="USER_SAYS_APPROVED"
        proposal["status"]="APPROVED"
        combo=book()
        combo["approval_reference"]="USER_SAYS_APPROVED"
        combo["status"]="APPROVED"
        plan=self.compiler.compile_candidate(
            model_profile=proposal,combo_book=combo,
            expected_instances=instances())
        self.assertFalse(plan["normative_execution_authorized"])
        self.assertFalse(plan["model_profile_approval_proven"])
        self.assertFalse(plan["combo_book_approval_proven"])

    def test_cli_uses_exact_fixture_and_immutable_output(self):
        from tools.audit_vs05_candidate_dag import audit
        manifest = REPO / "tests" / "fixtures" / "vs05_candidate_plan_input.json"
        with TemporaryDirectory() as folder:
            target = Path(folder) / "vs05_candidate_audit.json"
            report = audit(CATALOG, manifest, target)
            self.assertEqual(report["dag"]["candidate_nodes"], 94)
            self.assertEqual(report["dag"]["candidate_dependency_edges"], 140)
            self.assertEqual(report["fcr"]["expected_count"], 4)
            self.assertEqual(report["fcr"]["reconciled_count"], 4)
            self.assertEqual(report["fcr"]["not_proven_count"], 4)
            self.assertEqual(report["fcr"]["pass_count"], 0)
            self.assertEqual(report["engineering_release"], "NOT_READY")
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)
            with self.assertRaises(CompilationRejected):
                audit(CATALOG, manifest, target)

    def test_candidate_catalog_mutation_rejected(self):
        data=deepcopy(self.catalog)
        data["nodes"].pop()
        with self.assertRaisesRegex(CompilationRejected,"NODE_COUNT"):
            validate_candidate_catalog(data)


if __name__=="__main__":
    unittest.main()
