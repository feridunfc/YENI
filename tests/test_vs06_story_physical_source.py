"""VS06-B: partial physical connectivity never becomes regulatory approval."""
from __future__ import annotations

import copy
import unittest

from tbdy_next.story_drift_binding import bind_story_drift
from tbdy_next.story_slot_ledger import build_story_slot_ledger
from tbdy_next.story_physical_source import PhysicalSourceError, review_story_physical_source
from test_vs05_story_drift_binding import seal
from test_vs05_story_delta import fixture
from test_vs06_story_slot_ledger import source_record, synthetic_12_of_16


def check(source, record):
    ledger = build_story_slot_ledger(source, record)
    return review_story_physical_source(source, record, ledger)


def reseal(changed):
    changed.pop("payload_sha256", None)
    source = seal(changed)
    record = bind_story_drift(source)
    return source, record


class Vs06PhysicalEvidenceTests(unittest.TestCase):
    def test_existing_source_column_observed_but_no_applicability_pass(self):
        source, record = source_record()
        report = check(source, record)
        self.assertEqual(report["observed_column_count"], 1)
        self.assertEqual(report["endpoint_linked_column_count"], 1)
        self.assertEqual(report["response_spectrum_independent_max_rows"], 2)
        self.assertEqual(report["ritz_modal_shape_rows"], 2)
        self.assertEqual(report["signed_concurrent_spectrum_design_pairs_proven"], 0)
        self.assertEqual(report["formal_compliance"], "NOT_PROVEN")
        self.assertFalse(report["analysis_generation_independently_proven"])
        self.assertEqual(len(report["slots"]), 8)
        self.assertEqual(report["observed_stories"][1]["member_presence_evidence"],
                         "COLUMN_CONNECTIVITY_OBSERVED")
        self.assertTrue(all(s["physical_applicability"] == "NOT_PROVEN"
                            for s in report["slots"]))

    def test_12_of_16_missing_topology_remains_not_proven(self):
        source, record = synthetic_12_of_16()
        report = check(source, record)
        self.assertEqual(len(report["slots"]), 16)
        upper = [x for x in report["slots"] if x["story"] == "+14.50"]
        self.assertEqual(len(upper), 4)
        self.assertTrue(all(x["source_status"] == "SOURCE_MISSING" for x in upper))
        self.assertTrue(all(x["member_presence_evidence"] ==
                            "NO_COLUMN_CONNECTIVITY_OBSERVED" for x in upper))
        self.assertTrue(all(x["physical_applicability"] == "NOT_PROVEN" for x in upper))
        self.assertFalse(report["full_physical_story_census_proven"])

    def test_column_at_missing_story_does_not_fabricate_spectrum_data(self):
        source, record = synthetic_12_of_16()
        data = copy.deepcopy(source)
        pt = data["table_reads"]["Point Object Connectivity"]
        pt["rows"].append({"UniqueName": "777", "Story": "+14.50",
                           "X": "10", "Y": "10", "Z": "14.5"})
        pt["row_count"] += 1
        col = data["table_reads"]["Column Object Connectivity"]
        col["rows"].append({"UniqueName": "888", "Story": "+14.50",
                            "UniquePtI": "292", "UniquePtJ": "777", "Length": "5.5"})
        col["row_count"] += 1
        source, record = reseal(data)
        report = check(source, record)
        top = [r for r in report["slots"] if r["story"] == "+14.50"]
        self.assertEqual(len(top), 4)
        self.assertTrue(all(r["member_presence_evidence"] ==
                            "COLUMN_CONNECTIVITY_OBSERVED" for r in top))
        self.assertTrue(all(r["source_status"] == "SOURCE_MISSING" for r in top))
        self.assertEqual(report["signed_concurrent_spectrum_design_pairs_proven"], 0)

    def test_tampered_slot_ledger_rejected(self):
        source, record = source_record()
        ledger = build_story_slot_ledger(source, record)
        ledger["slots"].pop()
        with self.assertRaisesRegex(PhysicalSourceError,
                                    "STORY_SLOT_LEDGER_REPLAY_MISMATCH"):
            review_story_physical_source(source, record, ledger)

    def test_falsified_spectrum_projection_is_rejected(self):
        source, record = source_record()
        data = copy.deepcopy(source)
        rs = [r for r in data["table_reads"]["Joint Displacements"]["rows"]
              if r["OutputCase"] == "RSX"][0]
        rs["StepType"] = "Step"
        source, record = reseal(data)
        self.assertEqual(record["execution_status"], "EXECUTED_SOURCE_NUMERICAL")
        with self.assertRaisesRegex(PhysicalSourceError,
                                    "SPECTRUM_DISPLACEMENT_PROJECTION_UNEXPECTED"):
            check(source, record)

    def test_unknown_column_story_cannot_disappear(self):
        source, record = source_record()
        data = copy.deepcopy(source)
        data["table_reads"]["Column Object Connectivity"]["rows"][0]["Story"] = "UNKNOWN"
        source, record = reseal(data)
        self.assertEqual(record["execution_status"], "EXECUTED_SOURCE_NUMERICAL")
        with self.assertRaisesRegex(PhysicalSourceError,
                                    "COLUMN_STORY_OUTSIDE_OBSERVED_STORIES"):
            check(source, record)

    def test_nonfinite_point_coordinate_is_not_accepted(self):
        source, record = source_record()
        data = copy.deepcopy(source)
        data["table_reads"]["Point Object Connectivity"]["rows"][0]["X"] = "NaN"
        source, record = reseal(data)
        self.assertEqual(record["execution_status"], "EXECUTED_SOURCE_NUMERICAL")
        with self.assertRaises(ValueError):
            check(source, record)

    def test_result_mesh_points_do_not_establish_physical_object_census(self):
        source, record = source_record()
        data = copy.deepcopy(source)
        table = data["table_reads"]["Joint Displacements"]
        table["rows"].append({
            "UniqueName": "mesh-only", "Story": "+9.00", "OutputCase": "RSX",
            "CaseType": "LinRespSpec", "StepType": "Max", "StepNumber": "None",
            "Ux": "0.01", "Uy": "0.01",
        })
        table["row_count"] += 1
        source, record = reseal(data)
        report = check(source, record)
        self.assertEqual(report["joint_result_point_not_in_point_objects_count"], 1)
        self.assertFalse(report["full_physical_story_census_proven"])

    def test_immutable_source_and_deterministic_review_hash(self):
        source, record = source_record()
        before_source, before_record = copy.deepcopy(source), copy.deepcopy(record)
        a, b = check(source, record), check(source, record)
        self.assertEqual(a, b)
        self.assertEqual(len(a["review_sha256"]), 64)
        self.assertEqual(source, before_source)
        self.assertEqual(record, before_record)
        self.assertEqual(a["engineering_release"], "NOT_READY")
        self.assertEqual(a["dag_execution_authority"], "DENIED")


if __name__ == "__main__":
    unittest.main()
