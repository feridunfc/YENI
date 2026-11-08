"""VS06-D1: B1 auto-derived from SAME live ETABS run in archival reports.

No real COM call during tests, no source mutation or new fabricated PASS.
"""
from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs06_b1_source_bridge import sources


class B1SingleRunReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.live_calls=[]
        def simulated_live(case):
            self.live_calls.append(case)
            payload=fake_live_suite(case)
            g,l=sources()
            payload["vs06_b1_geometry_source"]=g
            payload["vs06_wall_load_source"]=l
            return payload
        self.s=ThreadingHTTPServer(("127.0.0.1",0),
                                   make_handler(self.root,live_capture=simulated_live))
        self.worker=Thread(target=self.s.serve_forever,daemon=True)
        self.worker.start()
        self.base=f"http://127.0.0.1:{self.s.server_port}"

    def tearDown(self):
        self.s.shutdown();self.s.server_close()
        self.worker.join(3)
        self.tmp.cleanup()

    def live(self):
        req=Request(self.base+"/api/live-suite?case=Modal",data=b"",method="POST")
        with urlopen(req,timeout=10) as response:
            return json.load(response)["run_id"]

    def test_single_run_B1_geometry_plus_LC_WDL_to_JSON_HTML(self):
        run_id=self.live()
        with urlopen(self.base+"/api/export-checks?run_id="+run_id) as response:
            report=json.load(response)
        b1=report["vs06_b1_result"]
        self.assertEqual(report["vs06_b1_source_status"],"SOURCE_BOUND_NUMERICAL")
        self.assertEqual(b1["source_wall_load_rows"],2)
        self.assertEqual(b1["source_candidate_wall_beams"],2)
        self.assertEqual(b1["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(b1["parameters"]["wall_type"],"BRITTLE")
        self.assertEqual(report["check_inventory"]["count"], 6)
        entry = next(x for x in report["check_inventory"]["entries"]
                     if x["check_id"] == "WEAK_STORY_B1")
        self.assertEqual(entry["evaluation"], "CONDITIONAL_SOURCE_NUMERICAL")
        self.assertEqual(entry["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(entry["evaluated_count"], 2)
        self.assertEqual(entry["status"], b1["b1_numerical"]["numeric_condition"])
        with urlopen(self.base+"/report/print?run_id="+run_id) as response:
            html=response.read().decode("utf-8")
        self.assertIn("VS06-D1",html)
        self.assertIn("Hesap varsayımları",html)
        self.assertIn("NOT_PROVEN",html)
        self.assertEqual(self.live_calls,["Modal"],
                         "Read-only report must not make second ETABS capture")

    def test_b1_corrupt_optional_capture_does_not_reopen_earlier_checks(self):
        def broken_live(case):
            payload=fake_live_suite(case)
            g,l=sources()
            l["frame_load_object_probe"]["rows"][0]["LoadPattern"]="TAMPERED"
            payload["vs06_b1_geometry_source"]=g
            payload["vs06_wall_load_source"]=l
            return payload
        self.s.RequestHandlerClass=make_handler(self.root,live_capture=broken_live)
        run_id=self.live()
        with urlopen(self.base+"/api/export-checks?run_id="+run_id) as response:
            report=json.load(response)
        self.assertNotIn("vs06_b1_result",report)
        self.assertIn("BLOCKED_SOURCE_BINDING",report["vs06_b1_source_status"])
        self.assertEqual(report["engineering_release"],"NOT_READY")
        self.assertEqual(report["check_inventory"]["count"],6)
        b1 = next(x for x in report["check_inventory"]["entries"]
                  if x["check_id"] == "WEAK_STORY_B1")
        self.assertEqual(b1["status"], "BLOCKED_SOURCE_BINDING")
        self.assertEqual(b1["evaluation"], "BLOCKED_SOURCE")
        self.assertEqual(b1["evaluated_count"], 0)
        self.assertEqual(b1["formal_compliance"], "NOT_PROVEN")


if __name__=="__main__":
    unittest.main()
