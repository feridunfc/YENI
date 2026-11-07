"""VS04 product-entrypoint regression: one visible live calculation action.

The backend is tested using one injected synthetic capture. This proves
HTTP/run_id/report wiring, NOT an ETABS Windows GUI/E2E acceptance.
"""
from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import urlopen, Request

from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs03 import source as vs03_source, geo as vs03_geo
from test_vs04_numerics import numeric_source


class OneButtonProductPath(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.calls=[]
        def capture(case):
            self.calls.append(case)
            source=fake_live_suite(case)
            source["next_capture"]=vs03_source()
            source["geometry_capture"]=vs03_geo()
            analysis=numeric_source()
            analysis["readiness_stage_required"]=True
            source["analysis_sources"]=analysis
            return source
        self.server=ThreadingHTTPServer(
            ("127.0.0.1",0),make_handler(self.root,live_capture=capture))
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.tmp.cleanup()

    def get(self,path):
        with urlopen(self.url+path,timeout=8) as r:
            return r.read().decode("utf-8")

    def test_one_primary_etabs_calculation_button_and_exact_route(self):
        html=self.get("/")
        js=self.get("/quick.js")
        self.assertEqual(html.count('id="runAllBtn"'),1)
        for old in ('id="liveModalBtn"','id="quickSuiteBtn"','id="vs04SourceBtn"'):
            self.assertNotIn(old,html)
        self.assertIn('id="liveCase"',html)
        self.assertIn('ETABS’tan Oku ve Hesapla',html)
        self.assertIn("engineering",html.lower())
        self.assertIn("runAllBtn",js)
        self.assertIn("/api/live-vs04?case=",js)
        self.assertNotIn("/api/live-suite?case=",js)
        self.assertNotIn("quickSuiteBtn",js)
        self.assertNotIn("vs04SourceBtn",js)
        self.assertIn("NOT_PROVEN",js)
        self.assertIn("NOT_READY",js)

    def test_one_backend_call_builds_single_run_id_and_same_report(self):
        req=Request(self.url+"/api/live-vs04?case=Modal",
                    data=b"",method="POST")
        with urlopen(req,timeout=8) as response:
            data=json.loads(response.read())
        self.assertEqual(self.calls,["Modal"])
        self.assertTrue(data["run_id"].startswith("RUN-"))
        self.assertEqual(data["engineering_release"],"NOT_READY")
        self.assertEqual(data["vs04_schema"]["captured_table_count"],3)
        self.assertEqual(data["vs04_numerics"]["observed_component_count"],5)
        self.assertEqual(data["vs04_readiness"]["proven_check_count"],0)
        self.assertIsNotNone(data["geometry"])
        self.assertIsNotNone(data["extra_checks"])
        run_id=data["run_id"]
        with urlopen(self.url+"/api/export-checks?run_id="+run_id,timeout=8) as response:
            report=json.loads(response.read())
        self.assertEqual(report["run_id"],run_id)
        self.assertEqual(len(report["checks"]),8)
        self.assertEqual(report["vs04_readiness"]["regulatory_checks_executed"],0)
        self.assertEqual(report["formal_compliance"],"NOT_PROVEN")
        html=self.get("/report/print?run_id="+run_id)
        self.assertIn("VS04-E",html)
        self.assertEqual(self.calls,["Modal"],"Exports must never rerun ETABS")

    def test_no_live_action_on_initial_ui_get(self):
        self.get("/")
        self.get("/quick.js")
        self.assertEqual(self.calls,[])


if __name__=="__main__":
    unittest.main()
