from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.cli import main
from tbdy_next.modal import evaluate_modal_mass
from tbdy_next.source import SourceError, parse_modal_capture, read_json, review_preflight

FIXTURES = Path(__file__).parent / "fixtures"


class TestDiscovery(unittest.TestCase):
    def test_accepts_inventory_not_schema(self):
        result = review_preflight(read_json(FIXTURES / "preflight_synthetic.json"))
        self.assertEqual(result["status"], "DISCOVERED")
        self.assertFalse(result["modal_schema_verified"])
        self.assertTrue(result["modal_table_listed"])
        self.assertEqual(result["available_table_count"], 2)

    def test_rejects_wrong_inventory_count(self):
        obj = deepcopy(read_json(FIXTURES / "preflight_synthetic.json"))
        obj["observations"]["available_tables"]["count"] = 999
        with self.assertRaises(SourceError):
            review_preflight(obj)

    def test_rejects_duplicate_case(self):
        obj = deepcopy(read_json(FIXTURES / "preflight_synthetic.json"))
        obj["observations"]["load_cases"].update(names=["Modal", "Modal"])
        with self.assertRaises(SourceError):
            review_preflight(obj)


class TestModalSchema(unittest.TestCase):
    def test_valid_full_table_and_case_isolation(self):
        table = parse_modal_capture(read_json(FIXTURES / "modal_meets.json"), case="Modal")
        self.assertEqual(len(table.rows), 2)
        self.assertEqual(table.all_rows_count, 3)
        self.assertEqual(table.rows[-1].mode, 2)

    def test_rejects_truncated_table(self):
        obj = deepcopy(read_json(FIXTURES / "modal_meets.json"))
        obj["table"]["row_count"] = 9
        with self.assertRaises(SourceError):
            parse_modal_capture(obj, case="Modal")

    def test_rejects_missing_mode(self):
        obj = deepcopy(read_json(FIXTURES / "modal_meets.json"))
        obj["table"]["rows"][1]["Mode"] = "3"
        with self.assertRaises(SourceError):
            parse_modal_capture(obj, case="Modal")

    def test_rejects_misleading_cumulative(self):
        obj = deepcopy(read_json(FIXTURES / "modal_meets.json"))
        obj["table"]["rows"][1]["SumUY"] = "1"
        with self.assertRaises(SourceError):
            parse_modal_capture(obj, case="Modal")

    def test_rejects_nan_and_infinity(self):
        for bad in ("NaN", "Infinity"):
            with self.subTest(bad=bad):
                obj = deepcopy(read_json(FIXTURES / "modal_meets.json"))
                obj["table"]["rows"][0]["UX"] = bad
                with self.assertRaises(SourceError):
                    parse_modal_capture(obj, case="Modal")

    def test_rejects_unknown_case(self):
        with self.assertRaises(SourceError):
            parse_modal_capture(read_json(FIXTURES / "modal_meets.json"), case="Nothing")

    def test_rejects_missing_feature(self):
        obj = deepcopy(read_json(FIXTURES / "modal_meets.json"))
        obj["table"]["fields"].remove("SumUX")
        with self.assertRaises(SourceError):
            parse_modal_capture(obj, case="Modal")


class TestNumericalCheck(unittest.TestCase):
    def test_meets_threshold(self):
        table = parse_modal_capture(read_json(FIXTURES / "modal_meets.json"), case="Modal")
        value = evaluate_modal_mass(table).as_dict()
        self.assertEqual(value["status"], "MEETS_NUMERICAL_CRITERION")
        self.assertEqual(value["required_ratio"], "0.95")
        self.assertEqual(value["governing_mode_count"], 2)
        self.assertEqual(value["engineering_release"], "NOT_READY")

    def test_below_95_is_not_meeting(self):
        table = parse_modal_capture(read_json(FIXTURES / "modal_below.json"), case="Modal")
        value = evaluate_modal_mass(table).as_dict()
        self.assertEqual(value["status"], "DOES_NOT_MEET_NUMERICAL_CRITERION")
        self.assertEqual(value["sum_ux"], "0.942")
        self.assertEqual(value["sum_uy"], "0.918")

    def test_exact_95_counts(self):
        obj = deepcopy(read_json(FIXTURES / "modal_below.json"))
        obj["table"]["rows"][1].update(UX="0.15", UY="0.17", SumUX="0.95", SumUY="0.95")
        table = parse_modal_capture(obj, case="Modal")
        self.assertEqual(evaluate_modal_mass(table).as_dict()["status"], "MEETS_NUMERICAL_CRITERION")


class TestReceipt(unittest.TestCase):
    def test_writes_two_distinct_receipts(self):
        with TemporaryDirectory() as temp:
            exit_code = main(["check-modal", "--input", str(FIXTURES / "modal_meets.json"), "--case", "Modal", "--out", temp])
            self.assertEqual(exit_code, 0)
            outputs = list(Path(temp).glob("RUN-*/*.json"))
            self.assertEqual(len(outputs), 2)
            statuses = [json.loads(p.read_text())["payload"]["status"] for p in outputs]
            self.assertCountEqual(statuses, ["SCHEMA_VALID", "MEETS_NUMERICAL_CRITERION"])

    def test_rejected_input_writes_rejected_receipt(self):
        with TemporaryDirectory() as temp:
            exit_code = main(["check-modal", "--input", str(FIXTURES / "modal_meets.json"), "--case", "Unknown", "--out", temp])
            self.assertEqual(exit_code, 2)
            outputs = list(Path(temp).glob("RUN-*/*.json"))
            self.assertEqual(len(outputs), 1)
            receipt = json.loads(outputs[0].read_text())
            self.assertEqual(receipt["payload"]["status"], "REJECTED")
            self.assertEqual(receipt["payload"]["engineering_release"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
