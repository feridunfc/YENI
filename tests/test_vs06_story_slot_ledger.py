"""VS06-A: original VS05 receipts remain untouched; all source slots accounted."""
from __future__ import annotations

import copy
from decimal import Decimal
import unittest

from tbdy_next.story_drift_binding import bind_story_drift
from tbdy_next.story_slot_ledger import StorySlotLedgerError, build_story_slot_ledger
from test_vs05_story_delta import fixture
from test_vs05_story_drift_binding import seal


def source_record():
    source = seal(fixture())
    return source, bind_story_drift(source)


def synthetic_12_of_16():
    """Four story labels, with all +14.50 RSX/RSY rows intentionally missing."""
    source = fixture()
    story = source["table_reads"]["Story Definitions"]
    story["rows"] += [
        {"Story": "+14.50", "Tower": "T1", "Height": "5.5"},
        {"Story": "+19.00", "Tower": "T1", "Height": "4.5"},
    ]
    story["row_count"] = len(story["rows"])
    drifts = source["table_reads"]["Story Drifts"]
    maxima = source["table_reads"]["Story Max Over Avg Drifts"]
    drifts["rows"] = []
    maxima["rows"] = []
    for s in story["rows"]:
        if s["Story"] == "+14.50":
            continue
        for case in ("RSX", "RSY"):
            for direction in ("X", "Y"):
                drifts["rows"].append({
                    "Story": s["Story"], "OutputCase": case,
                    "CaseType": "LinRespSpec", "StepType": "Max",
                    "Direction": direction, "Drift": "0.000776", "Label": "131",
                })
                value = str(Decimal("0.000776") * Decimal(s["Height"]))
                maxima["rows"].append({
                    "Story": s["Story"], "OutputCase": case,
                    "CaseType": "LinRespSpec", "StepType": "Max",
                    "Direction": direction, "Max Drift": value,
                    "Avg Drift": value, "Ratio": "1.0",
                })
    drifts["row_count"] = len(drifts["rows"])
    maxima["row_count"] = len(maxima["rows"])
    source = seal(source)
    return source, bind_story_drift(source)


class StorySlotLedgerTests(unittest.TestCase):
    def test_existing_partial_fixture_all_slots_reconciled(self):
        source, record = source_record()
        original = copy.deepcopy(record)
        ledger = build_story_slot_ledger(source, record)
        self.assertEqual((ledger["expected_slot_count"], ledger["accounted_slot_count"]), (8, 8))
        self.assertEqual((ledger["source_numeric_count"], ledger["source_missing_count"]), (1, 7))
        self.assertFalse(ledger["source_coverage_complete"])
        self.assertEqual(ledger["normative_checks_issued"], 0)
        self.assertTrue(all(x["physical_applicability"] == "NOT_PROVEN" for x in ledger["slots"]))
        self.assertEqual(record, original)
        self.assertEqual(len(ledger["ledger_sha256"]), 64)

    def test_12_of_16_missing_upper_story_is_not_assumed_inapplicable(self):
        source, record = synthetic_12_of_16()
        self.assertEqual(record["status"], "NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE")
        ledger = build_story_slot_ledger(source, record)
        self.assertEqual((ledger["expected_slot_count"], ledger["accounted_slot_count"]), (16, 16))
        self.assertEqual((ledger["source_numeric_count"], ledger["source_missing_count"]), (12, 4))
        absent = [r for r in ledger["slots"] if r["source_status"] == "SOURCE_MISSING"]
        self.assertEqual({r["story"] for r in absent}, {"+14.50"})
        self.assertEqual({(r["case"],r["direction"]) for r in absent},
                         {("RSX", "X"), ("RSX", "Y"), ("RSY", "X"), ("RSY", "Y")})
        self.assertTrue(all(r["normative_status"] == "NOT_PROVEN" for r in ledger["slots"]))
        self.assertFalse(ledger["physical_applicability_verified"])

    def test_cannot_promote_to_formal_compliance(self):
        source, record = source_record()
        record["numerical_pass_issued"] = True
        with self.assertRaisesRegex(StorySlotLedgerError, "UNTRUSTED_NORMATIVE_PROMOTION"):
            build_story_slot_ledger(source, record)

    def test_capture_hash_tamper_rejected(self):
        source, record = source_record()
        source["table_reads"]["Story Definitions"]["rows"][0]["Height"] = "8.5"
        with self.assertRaises(ValueError):
            build_story_slot_ledger(source, record)

    def test_duplicate_observed_row_rejected(self):
        source, record = source_record()
        record["items"].append(copy.deepcopy(record["items"][0]))
        with self.assertRaisesRegex(StorySlotLedgerError, "DUPLICATE_OBSERVED_SLOT"):
            build_story_slot_ledger(source, record)

    def test_missing_slot_cannot_disappear(self):
        source, record = source_record()
        record["missing_story_case_direction"].pop()
        with self.assertRaisesRegex(StorySlotLedgerError, "MISSING_SLOT_CENSUS_MISMATCH"):
            build_story_slot_ledger(source, record)

    def test_unexpected_story_rejected(self):
        source, record = source_record()
        record["items"][0]["story"] = "UNSEEN_STORY"
        with self.assertRaisesRegex(StorySlotLedgerError, "OBSERVED_OUTSIDE_EXPECTED_DENOMINATOR"):
            build_story_slot_ledger(source, record)

    def test_hash_and_record_binding_are_stable(self):
        source, record = source_record()
        a = build_story_slot_ledger(source, record)
        b = build_story_slot_ledger(source, record)
        self.assertEqual(a, b)
        record["source_payload_sha256"] = "f" * 64
        with self.assertRaisesRegex(StorySlotLedgerError, "SOURCE_RECORD_HASH_MISMATCH"):
            build_story_slot_ledger(source, record)


if __name__ == "__main__":
    unittest.main()
