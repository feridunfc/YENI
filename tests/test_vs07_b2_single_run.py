"""B2 same-run JSON/HTML delivery and preservation of accepted receipts."""
from __future__ import annotations

from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs07_soft_story_b2 import BASE, b2_source, reseal


class B2SingleRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls = []
        self.delta = b2_source(numeric_names=True)

        def capture(case):
            self.calls.append(case)
            payload = deepcopy(fake_live_suite(case))
            if self.delta is not None:
                payload["vs05_delta_source"] = deepcopy(self.delta)
            return payload

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.root, live_capture=capture))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.tmp.cleanup()

    def create(self):
        request = Request(self.base + "/api/live-suite?case=Modal", data=b"", method="POST")
        with urlopen(request, timeout=10) as response:
            return json.load(response)["run_id"]

    def get(self, path):
        with urlopen(self.base + path, timeout=10) as response:
            return response.read()

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_source_to_same_run_json_html_inventory_and_receipts_unchanged(self):
        points = self.delta["table_reads"]["Point Object Connectivity"]
        points["rows"].append({"UniqueName": "INTERIOR", "Story": "+3.00",
                               "X": "0", "Y": "0", "Z": "2.7"})
        points["row_count"] = len(points["rows"])
        self.delta = reseal(self.delta)
        run_id = self.create()
        before = self.snapshot()
        report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
        b2 = report["soft_story_b2"]
        self.assertEqual(b2["comparison_coverage"]["resolved"], 8)
        self.assertEqual(b2["story_order"]["intermediate_point_count"], 1)
        self.assertEqual(b2["threshold_exceeded_comparisons"], 1)
        entries = [e for e in report["check_inventory"]["entries"] if e["check_id"] == "SOFT_STORY_B2"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["evaluation"], "CONDITIONAL_SOURCE_NUMERICAL")
        self.assertEqual(entries[0]["evaluated_count"], 6)
        self.assertEqual(b2["source_payload_sha256"], report["source_snapshot"]["vs05_delta_source"]["payload_sha256"])
        self.assertEqual(report["story_drift"]["execution_status"], "EXECUTED_SOURCE_NUMERICAL")
        html = self.get("/report/print?run_id=" + run_id).decode()
        self.assertIn("B2 yumuşak kat", html)
        self.assertIn(b2["result_sha256"], html)
        self.assertIn("THRESHOLD_EXCEEDED", html)
        self.assertIn("Avg Drift", html)
        self.assertIn("Kat kotu ve ara nokta eşleştirmesi", html)
        self.assertIn("NOT_PROVEN", html)
        self.assertEqual(report["engineering_release"], "NOT_READY")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.calls, ["Modal"])
        self.assertEqual(json.loads(self.get("/api/export-checks?run_id=" + run_id)), report)
        from tools.verify_vs07_b2_archived import verify
        replay = verify(self.root, run_id)
        self.assertEqual(replay["result_sha256"], b2["result_sha256"])
        self.assertEqual(self.snapshot(), before)

    def test_b2_missing_base_does_not_erase_previous_story_drift_or_geometry(self):
        del self.delta["table_reads"][BASE]
        self.delta = reseal(self.delta)
        run_id = self.create()
        report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
        self.assertEqual(report["soft_story_b2"]["status"], "BLOCKED_SOURCE")
        self.assertEqual(report["story_drift"]["execution_status"], "EXECUTED_SOURCE_NUMERICAL")
        self.assertEqual(len(report["checks"]), 5)
        b2 = next(e for e in report["check_inventory"]["entries"] if e["check_id"] == "SOFT_STORY_B2")
        self.assertEqual(b2["evaluation"], "BLOCKED_SOURCE")
        self.assertIn("B2_SOURCE_TABLE_MISSING", self.get("/report/print?run_id=" + run_id).decode())

    def test_pre_delta_historical_run_stays_five_checks_with_new_registry(self):
        self.delta = None
        run_id = self.create()
        report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
        self.assertNotIn("soft_story_b2", report)
        self.assertEqual(report["check_inventory"]["count"], 5)
        registry = json.loads(self.get("/api/check-registry"))
        b2 = [r for r in registry["checks"] if r["check_id"] == "SOFT_STORY_B2"]
        self.assertEqual(len(b2), 1)
        self.assertEqual(b2[0]["tab_id"], 9)


if __name__ == "__main__":
    unittest.main()
