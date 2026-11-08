"""VS06-C1: actual 94-node candidate DAG/FCR, zero normative drift PASS."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from tbdy_next.compiled_dag import CompilationRejected
from tbdy_next.effective_drift_readiness import (
    EffectiveDriftReadinessError, review_effective_drift_readiness,
)
from tbdy_next.story_physical_source import review_story_physical_source
from tbdy_next.story_slot_ledger import build_story_slot_ledger
from test_vs06_story_slot_ledger import source_record, synthetic_12_of_16


CATALOG = Path(__file__).resolve().parents[1] / "config" / "dag" / "tbdy_r1c_94_candidate.json"


def inputs(source_record_pair=None):
    source, record = source_record_pair or source_record()
    ledger = build_story_slot_ledger(source, record)
    physical = review_story_physical_source(source, record, ledger)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return source, record, ledger, physical, catalog


def run(args):
    return review_effective_drift_readiness(*args)


class Vs06EffectiveDriftReadinessTests(unittest.TestCase):
    def test_two_stories_four_primary_candidates_and_no_pass(self):
        r = run(inputs())
        self.assertEqual(r["expected_story_direction_instances"], 4)
        self.assertEqual(r["source_numeric_primary_instances"], 1)
        self.assertEqual(r["source_missing_primary_instances"], 3)
        self.assertEqual(r["candidate_fcr_expected"], 4)
        self.assertEqual(r["candidate_fcr_reconciled"], 4)
        self.assertEqual(r["candidate_fcr_not_proven"], 4)
        self.assertEqual(r["candidate_fcr_pass"], 0)
        self.assertEqual(r["formula_executed_count"], 0)
        self.assertEqual(r["dag_dependency_ids"],
                         ["ANALYSIS_BASIS_GATE", "SEISMIC_DESIGN_BASIS"])
        self.assertTrue(all(x["regulatory_status"] == "NOT_PROVEN"
                            for x in r["check_instances"]))

    def test_real_shape_12_of_16_is_six_of_eight_primary_candidates(self):
        r = run(inputs(synthetic_12_of_16()))
        self.assertEqual((r["expected_story_direction_instances"],
                          r["source_numeric_primary_instances"],
                          r["source_missing_primary_instances"]), (8, 6, 2))
        top = [x for x in r["check_instances"] if x["story"] == "+14.50"]
        self.assertEqual(len(top), 2)
        self.assertTrue(all(x["source_numeric_status"] == "SOURCE_MISSING"
                            for x in top))
        self.assertTrue(all("COMPLETE_PHYSICAL_OBJECT_CENSUS_REQUIRED_BEFORE_NOT_APPLICABLE"
                            in x["required_source_evidence"] for x in top))

    def test_cross_directional_source_rows_do_not_create_extra_checks(self):
        r = run(inputs(synthetic_12_of_16()))
        self.assertEqual(len(r["check_instances"]), 8)
        self.assertTrue(all((x["case"],x["direction"]) in
                            (("RSX","X"),("RSY","Y"))
                            for x in r["check_instances"]))

    def test_etabs_numeric_candidate_not_elevated_to_eq_4_32(self):
        r = run(inputs())
        observed = [x for x in r["check_instances"]
                    if x["source_numeric_status"] == "OBSERVED_SOURCE_NUMERIC"]
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]["etabs_derived_delta_mm_candidate"],
                         "3.4920000")
        self.assertFalse(observed[0]["calculation_ready"])
        self.assertIn("QUALIFIED_PHYSICAL_SIGNED_REDUCED_DELTA_NOT_AVAILABLE",
                      observed[0]["required_source_evidence"])

    def test_falsified_physical_provenance_denied(self):
        args = list(inputs())
        forged = deepcopy(args[3])
        forged["full_physical_story_census_proven"] = True
        args[3] = forged
        with self.assertRaisesRegex(EffectiveDriftReadinessError,
                                    "PHYSICAL_SOURCE_REVIEW_NOT_VERIFIED"):
            run(args)

    def test_falsified_slot_ledger_denied(self):
        args = list(inputs())
        ledger = deepcopy(args[2])
        ledger["slots"].pop()
        args[2] = ledger
        with self.assertRaisesRegex(EffectiveDriftReadinessError,
                                    "SOURCE_SLOT_LEDGER_NOT_VERIFIED"):
            run(args)

    def test_changed_dag_dependency_refused(self):
        args = list(inputs())
        candidate = deepcopy(args[4])
        target = next(n for n in candidate["nodes"] if n["node_id"]=="STORY_DRIFT")
        target["depends_on"][0] = "MODEL_PROFILE_GATE"
        args[4] = candidate
        with self.assertRaises((CompilationRejected, EffectiveDriftReadinessError)):
            run(args)

    def test_caller_forged_executable_dag_denied(self):
        args = list(inputs())
        candidate = deepcopy(args[4])
        target = next(n for n in candidate["nodes"] if n["node_id"]=="STORY_DRIFT")
        target["execution_authority"] = "AUTHORIZED"
        args[4] = candidate
        with self.assertRaises(CompilationRejected):
            run(args)

    def test_deterministic_no_source_mutation(self):
        args = inputs(synthetic_12_of_16())
        originals = deepcopy(args)
        a, b = run(args), run(args)
        self.assertEqual(a, b)
        self.assertEqual(args, originals)
        self.assertEqual(len(a["readiness_sha256"]), 64)
        self.assertEqual(a["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(a["engineering_release"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
