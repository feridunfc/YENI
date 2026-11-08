from __future__ import annotations

import copy
import hashlib
import json
import unittest

from tbdy_next.story_drift_binding import bind_story_drift
from test_vs05_story_delta import fixture


def seal(source):
    source = copy.deepcopy(source)
    serial = (json.dumps(source, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    source["payload_sha256"] = hashlib.sha256(serial).hexdigest()
    return source


class StoryDriftBindingTests(unittest.TestCase):
    def test_partial_source_produces_actual_story_drift_record(self):
        record = bind_story_drift(seal(fixture()))
        self.assertEqual(record["check_id"], "STORY_DRIFT")
        self.assertEqual(record["dag_node_id"], "STORY_DRIFT")
        self.assertEqual(record["status"], "NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE")
        self.assertEqual(record["execution_status"], "EXECUTED_SOURCE_NUMERICAL")
        self.assertEqual(record["formal_compliance"], "NOT_PROVEN")
        self.assertFalse(record["numerical_pass_issued"])
        self.assertEqual(record["evaluated_story_case_direction_count"], 1)
        self.assertEqual(record["expected_story_case_direction_count"], 8)
        self.assertEqual(record["items"][0]["etabs_derived_delta_mm"], "3.4920000")
        self.assertEqual(record["modal_shape_column_mode_pairs"], 1)
        self.assertEqual(record["spectrum_max_point_rows_not_subtracted"], 2)

    def test_invalid_digest_is_blocked(self):
        data = seal(fixture())
        data["table_reads"]["Story Drifts"]["rows"][0]["Drift"] = "0.99"
        record = bind_story_drift(data)
        self.assertEqual(record["status"], "BLOCKED_SOURCE_INVALID")
        self.assertEqual(record["reason_codes"], ["GENERIC_SOURCE_SEAL_MISMATCH"])
        self.assertEqual(record["items"], [])

    def test_capture_failure_is_a_visible_blocked_check(self):
        record = bind_story_drift(None, capture_error="COM_TABLE_NOT_AVAILABLE")
        self.assertEqual(record["status"], "BLOCKED_SOURCE_UNAVAILABLE")
        self.assertEqual(record["reason_codes"], ["LIVE_ETABS_STORY_DRIFT_CAPTURE_FAILED"])
        self.assertEqual(record["source_capture_error"], "COM_TABLE_NOT_AVAILABLE")

    def test_absent_capture_is_not_proven(self):
        record = bind_story_drift(None)
        self.assertEqual(record["status"], "BLOCKED_SOURCE_UNAVAILABLE")
        self.assertEqual(record["formal_compliance"], "NOT_PROVEN")

    def test_invalid_numeric_data_is_blocked(self):
        data = fixture()
        data["table_reads"]["Story Drifts"]["rows"][0]["Drift"] = "NaN"
        record = bind_story_drift(seal(data))
        self.assertEqual(record["status"], "BLOCKED_SOURCE_INVALID")
        self.assertEqual(record["items"], [])

    def test_no_mutation_of_capture(self):
        data = seal(fixture())
        before = copy.deepcopy(data)
        bind_story_drift(data)
        self.assertEqual(data, before)

    def test_no_bypass_for_missing_spectrum_point_concurrence(self):
        record = bind_story_drift(seal(fixture()))
        self.assertEqual(record["spectrum_max_point_rows_not_subtracted"], 2)
        self.assertEqual(record["items"][0]["calculation_type"],
                         "ETABS_STORY_DRIFT_RATIO_TIMES_STORY_HEIGHT")
        self.assertFalse(record["numerical_pass_issued"])

    def test_malformed_source_is_blocked(self):
        record = bind_story_drift({"status": "CAPTURED", "schema": "unexpected"})
        self.assertEqual(record["status"], "BLOCKED_SOURCE_INVALID")


if __name__ == "__main__":
    unittest.main()
