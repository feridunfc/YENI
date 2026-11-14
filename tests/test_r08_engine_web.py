"""R08 native product integration: one button, same receipt, exact report replay.

No stand-alone calculation script and no Windows COM in CI.  The fake adapter
is injected into the normal web application's already-existing live capture path.
"""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_r08_story_second_order import fixture


class R08ProductWebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls = []

        def capture(case):
            self.calls.append(case)
            data = fake_live_suite(case)
            data["r08_second_order_source"] = fixture()
            return data

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.root, live_capture=capture))
        self.worker = Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(3)
        self.tmp.cleanup()

    def get(self, path):
        with urlopen(self.origin + path, timeout=12) as res:
            return json.loads(res.read())

    def test_single_live_run_then_immutable_r08_report_replay(self):
        request = Request(self.origin + "/api/live-suite?case=Modal",
                          data=b"", method="POST")
        with urlopen(request, timeout=12) as res:
            body = json.load(res)
        self.assertEqual(self.calls, ["Modal"])
        self.assertEqual(body["r08_second_order"]["status"], "NUMERIC_PRECHECK_UNAPPROVED")
        self.assertEqual(body["engineering_release"], "NOT_READY")
        runid = body["run_id"]
        self.assertEqual(len(list((self.root / runid).glob("*r08-second-order.json"))), 1)
        report = self.get("/api/export-checks?run_id=" + runid)
        self.assertEqual(report["r08_second_order"], body["r08_second_order"])
        self.assertTrue(report["source_provenance"]["r08_second_order_receipt_sha256"])
        self.assertEqual(report["r08_second_order"]["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(report["engineering_release"], "NOT_READY")
        self.assertEqual(self.calls, ["Modal"], "Report must not requery ETABS")
        registry = self.get("/api/check-registry")
        self.assertEqual(registry["implemented_check_count"], 16,
                         "GLOBAL_SECOND_ORDER is an existing DAG node, not a duplicate check")

    def test_tampered_r08_receipt_denies_report(self):
        request = Request(self.origin + "/api/live-suite?case=Modal",
                          data=b"", method="POST")
        with urlopen(request, timeout=12) as res:
            body = json.load(res)
        runid = body["run_id"]
        receipt = next((self.root / runid).glob("*r08-second-order.json"))
        obj = json.loads(receipt.read_text("utf-8"))
        obj["payload"]["status"] = "FABRICATED_ACCEPTANCE"
        receipt.write_text(json.dumps(obj, ensure_ascii=False), "utf-8")
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as raised:
            self.get("/api/export-checks?run_id=" + runid)
        self.assertEqual(raised.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
