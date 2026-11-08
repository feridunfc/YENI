"""VS05 closure invariants: source arithmetic is never regulatory PASS."""
import unittest
from tbdy_next.reporting import _vs05_check_inventory, _vs05_summary_row


class Vs05ReportInventoryTests(unittest.TestCase):
    def test_old_report_remains_eight_checks(self):
        old = [{"check_id": 'check_'+str(i)} for i in range(8)]
        inv = _vs05_check_inventory(old, None)
        self.assertEqual(inv['count'], 8)
        self.assertEqual(len(inv['entries']), 8)

    def test_story_drift_append_only_and_numerical(self):
        old = [{"check_id": 'check_'+str(i)} for i in range(8)]
        item = {"check_id": "STORY_DRIFT", "status": "NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE"}
        inv = _vs05_check_inventory(old, item)
        self.assertEqual(inv['count'], 9)
        self.assertEqual(inv['entries'][-1]['formal_compliance'], 'NOT_PROVEN')
        self.assertEqual(inv['entries'][-1]['evaluation'], 'SOURCE_NUMERICAL')
        self.assertEqual([x['check_id'] for x in inv['entries'][:-1]], [x['check_id'] for x in old])

    def test_reject_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_REPORTED_CHECK_ID'):
            _vs05_check_inventory([{"check_id": "STORY_DRIFT"}],
                                   {"check_id": "STORY_DRIFT", "status": "NUMERIC_SOURCE_OBSERVED"})

    def test_reject_foreign_id(self):
        with self.assertRaisesRegex(ValueError, 'UNEXPECTED_STORY_DRIFT_CHECK_ID'):
            _vs05_check_inventory([], {"check_id": "FAKE", "status": "NUMERIC_SOURCE_OBSERVED"})

    def test_12_of_16_all_normative_not_proven(self):
        row = _vs05_summary_row({"status": "NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE",
                                 "expected_story_case_direction_count": 16,
                                 "evaluated_story_case_direction_count": 12})
        self.assertEqual((row['expected_count'],row['evaluated_count']), (16,12))
        self.assertEqual((row['met_count'], row['unmet_count'],row['not_proven_count']), (0,0,16))

    def test_bad_coverage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'STORY_DRIFT_INVALID_COVERAGE'):
            _vs05_summary_row({"status": "X", "expected_story_case_direction_count": 12,
                               "evaluated_story_case_direction_count": 16})

if __name__ == '__main__':
    unittest.main()
