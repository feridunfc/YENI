"""VS04: exact analysis-table source evidence and fail-closed report integration."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.analysis_sources import (
    TABLES, capture_analysis_sources, review_analysis_sources,
)
from tbdy_next.etabs_modal import ModalCaptureError
from tbdy_next.quick_checks import check_registry
from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs03 import source as vs03_source, geo as vs03_geo


def sample_tables():
    """Synthetic table values ONLY; never accepted ETABS field contracts."""
    specs = (
        ("OutputCase", "StepType", "StepNum", "Period", "Frequency"),
        ("OutputCase", "CaseType", "StepType", "FX", "FY", "FZ"),
        ("Story", "OutputCase", "CaseType", "StepType", "Direction", "Drift"),
    )
    values = (
        ("Modal", "Mode", "1", "0.5", "2"),
        ("RSX", "LinRespSpec", "Max", "1200", "55", "0"),
        ("+3", "RSY", "LinRespSpec", "Max", "Y", "0.001"),
    )
    units = (
        ("", "", "", "sec", "1/sec"),
        ("", "", "", "kN", "kN", "kN"),
        ("", "", "", "", "", "m"),
    )
    return {
        key: {"fields": list(fields), "rows": [dict(zip(fields, data))],
              "units": dict(zip(fields, unit_list))}
        for key, fields, data, unit_list in zip(TABLES, specs, values, units)
    }


class FakeDB:
    def __init__(self, *, restore_fails=False, failing_table=None):
        self.selected = ("LC_DL",)
        self.writes = []
        self.restore_fails = restore_fails
        self.failing_table = failing_table
        self.data = sample_tables()

    def GetLoadCasesSelectedForDisplay(self):
        return len(self.selected), list(self.selected), 0

    def SetLoadCasesSelectedForDisplay(self, cases):
        target = tuple(c for c in cases if c)
        self.writes.append(target)
        if not (self.restore_fails and target == ("LC_DL",)):
            self.selected = target
        return 0

    def GetAllFieldsInTable(self, key):
        table = self.data[key]
        fields = table["fields"]
        units = table["units"]
        return (1, len(fields), fields, fields, [""] * len(fields),
                [units[k] for k in fields], [False] * len(fields), 0)

    def GetTableForDisplayArray(self, key, *args):
        if key == self.failing_table:
            raise ValueError("table unavailable")
        table = self.data[key]
        fields = table["fields"]
        flat = [row[k] for row in table["rows"] for k in fields]
        return None, 1, fields, len(table["rows"]), flat, 0


class FakeSap:
    def __init__(self, **kwargs):
        self.DatabaseTables = FakeDB(**kwargs)
    def GetPresentUnits(self):
        return 6


class Vs04SchemaTests(unittest.TestCase):
    def setUp(self):
        self.sap = FakeSap()
        self.capture = capture_analysis_sources(self.sap, modal_case="Modal")

    def test_complete_capture_preserves_units_and_case_selection(self):
        self.assertEqual(self.sap.DatabaseTables.selected, ("LC_DL",))
        self.assertEqual(self.sap.DatabaseTables.writes,
                         [("Modal", "RSX", "RSY"), ("LC_DL",)])
        self.assertEqual(list(self.capture["tables"]), list(TABLES))
        for key in TABLES:
            table = self.capture["tables"][key]
            self.assertEqual(table["row_count"], 1)
            self.assertEqual(table["field_metadata"]["status"], "OK")
            self.assertEqual(len(table["rows"]), 1)
        self.assertFalse(self.capture["analysis_generation_proven"])

    def test_schema_only_does_not_issue_compliance_or_numerical_checks(self):
        result = review_analysis_sources(self.capture)
        self.assertEqual(result["status"], "SOURCE_SCHEMA_CAPTURED_PENDING_REVIEW")
        self.assertEqual(result["captured_table_count"], 3)
        self.assertEqual(result["numeric_checks_executed"], 0)
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertEqual(len(check_registry()), 12)
        self.assertTrue(all(row["status"] == "OBSERVED_UNAPPROVED"
                            for row in result["tables"]))

    def test_source_hashes_are_deterministic_and_sensitive_to_rows(self):
        first = review_analysis_sources(self.capture)["tables"][0]["source_sha256"]
        second = review_analysis_sources(deepcopy(self.capture))["tables"][0]["source_sha256"]
        self.assertEqual(first, second)
        altered = deepcopy(self.capture)
        altered["tables"][TABLES[0]]["rows"][0]["Period"] = "1.5"
        changed = review_analysis_sources(altered)["tables"][0]["source_sha256"]
        self.assertNotEqual(first, changed)

    def test_missing_or_mismatched_table_fails_closed(self):
        for broken in ("missing", "key", "empty", "count", "field"):
            with self.subTest(broken=broken):
                item = deepcopy(self.capture)
                table = item["tables"][TABLES[0]]
                if broken == "missing":
                    del item["tables"][TABLES[0]]
                elif broken == "key":
                    table["table_key"] = "WRONG"
                elif broken == "empty":
                    table["row_count"], table["rows"] = 0, []
                elif broken == "count":
                    table["row_count"] = 2
                elif broken == "field":
                    table["rows"][0].pop("Frequency")
                result = review_analysis_sources(item)
                self.assertEqual(result["status"], "SOURCE_SCHEMA_INCOMPLETE")
                self.assertEqual(result["tables"][0]["status"], "NOT_PROVEN")

    def test_unknown_or_ambiguous_metadata_fails_closed(self):
        for broken in ("status", "count", "units", "keys"):
            with self.subTest(broken=broken):
                item = deepcopy(self.capture)
                meta = item["tables"][TABLES[0]]["field_metadata"]
                if broken == "status":
                    meta["status"] = "METADATA_ERROR"
                elif broken == "count":
                    meta["field_count"] = 99
                elif broken == "units":
                    meta["units_by_field"]["Period"] = None
                elif broken == "keys":
                    meta["field_keys"].remove("Period")
                result = review_analysis_sources(item)
                self.assertEqual(result["tables"][0]["status"], "NOT_PROVEN")

    def test_mixed_or_unstable_units_fails_closed(self):
        item = deepcopy(self.capture)
        item["units_after"] = 7
        result = review_analysis_sources(item)
        self.assertEqual(result["captured_table_count"], 0)
        self.assertEqual(result["status"], "SOURCE_SCHEMA_INCOMPLETE")

    def test_mismatched_case_selection_or_lineage_never_passes(self):
        for name, value in (("display_selection_restored", False),
                            ("analysis_generation_proven", True),
                            ("combination_roles_approved", True)):
            with self.subTest(name=name):
                item = deepcopy(self.capture)
                item[name] = value
                self.assertEqual(review_analysis_sources(item)["captured_table_count"], 0)

    def test_unavailable_source_is_not_proven(self):
        self.assertEqual(review_analysis_sources(None)["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(review_analysis_sources({})["formal_compliance"], "NOT_PROVEN")

    def test_invalid_case_roles_rejected_before_selection(self):
        with self.assertRaises(ModalCaptureError):
            capture_analysis_sources(FakeSap(), modal_case="RSX")
        with self.assertRaises(ModalCaptureError):
            capture_analysis_sources(FakeSap(), modal_case=" Modal ")

    def test_capture_error_retained_and_selection_restored(self):
        sap = FakeSap(failing_table=TABLES[1])
        cap = capture_analysis_sources(sap, modal_case="Modal")
        self.assertEqual(sap.DatabaseTables.selected, ("LC_DL",))
        result = review_analysis_sources(cap)
        self.assertEqual(result["tables"][1]["status"], "NOT_PROVEN")
        self.assertIn("TABLE_NOT_CAPTURED", result["tables"][1]["reason_codes"])

    def test_failed_display_restore_blocks_whole_capture(self):
        sap = FakeSap(restore_fails=True)
        with self.assertRaisesRegex(ModalCaptureError, "RESTORE_FAILED"):
            capture_analysis_sources(sap, modal_case="Modal")

    def test_duplicate_display_field_does_not_create_pass(self):
        item = deepcopy(self.capture)
        item["tables"][TABLES[2]]["fields"].append("Drift")
        self.assertEqual(review_analysis_sources(item)["tables"][2]["status"], "NOT_PROVEN")


class Vs04WebIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls = []
        def live(case):
            self.calls.append(case)
            payload = fake_live_suite(case)
            payload["next_capture"] = vs03_source()
            payload["geometry_capture"] = vs03_geo()
            payload["analysis_sources"] = capture_analysis_sources(FakeSap(), modal_case=case)
            return payload
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.root, live_capture=live))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.tmp.cleanup()

    def _run(self):
        request = Request(self.base + "/api/live-vs04?case=Modal", data=b"", method="POST")
        with urlopen(request, timeout=6) as response:
            return json.loads(response.read())

    def test_existing_eight_and_new_three_source_tables_in_same_run(self):
        out = self._run()
        self.assertEqual(out["vs04_schema"]["captured_table_count"], 3)
        self.assertEqual(out["extra_checks"]["status"], "NUMERICAL_CLASSIFIED")
        run_id = out["run_id"]
        with urlopen(self.base + "/api/export-checks?run_id=" + run_id, timeout=6) as response:
            report = json.loads(response.read())
        self.assertEqual(len(report["checks"]), 8)
        self.assertEqual(report["vs04"]["numeric_checks_executed"], 0)
        self.assertEqual(len(report["source_snapshot"]["analysis_sources"]["tables"]), 3)
        self.assertEqual(report["engineering_release"], "NOT_READY")
        self.assertIn("vs04_schema_receipt_sha256", report["source_provenance"])
        with urlopen(self.base + "/report/print?run_id=" + run_id, timeout=6) as response:
            html = response.read().decode("utf-8")
        self.assertIn("VS04 · Analiz kaynak şeması", html)
        self.assertIn("Modal Periods And Frequencies", html)
        self.assertIn("Story Drifts", html)
        self.assertEqual(self.calls, ["Modal"], "GET must never attach to ETABS")

    def test_v04_receipt_tamper_denies_export(self):
        run_id = self._run()["run_id"]
        file = next((self.root / run_id).glob("*-vs04-schema.json"))
        file.write_text(file.read_text(encoding="utf-8").replace(
            "OBSERVED_UNAPPROVED", "FORGED_PASS"), encoding="utf-8")
        with self.assertRaises(HTTPError) as ctx:
            urlopen(self.base + "/api/export-checks?run_id=" + run_id, timeout=6)
        self.assertEqual(ctx.exception.code, 404)

    def test_untrusted_origin_rejected_before_live_capture(self):
        request = Request(self.base + "/api/live-vs04?case=Modal",
                          data=b"", method="POST",
                          headers={"Origin": "https://other.example"})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(request, timeout=6)
        self.assertEqual(ctx.exception.code, 403)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
