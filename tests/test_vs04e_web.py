"""VS04-E web/receipt integration: expected norm instances never silently PASS."""
from __future__ import annotations

from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs03 import source as vs03_source, geo as vs03_geo
from test_vs04_numerics import numeric_source


class Vs04ENormativeReadinessWeb(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.calls=0
        def live(case):
            self.calls+=1
            payload=fake_live_suite(case)
            payload["next_capture"]=vs03_source()
            payload["geometry_capture"]=vs03_geo()
            basis=numeric_source()
            basis["readiness_stage_required"]=True
            payload["analysis_sources"]=basis
            return payload
        self.server=ThreadingHTTPServer(
            ("127.0.0.1",0),make_handler(self.root,live_capture=live))
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.tmp.cleanup()

    def _run(self):
        request=Request(self.url+"/api/live-vs04?case=Modal",data=b"",method="POST")
        with urlopen(request,timeout=7) as r:
            return json.loads(r.read())

    def test_old_eight_checks_and_five_missing_normative_gates_in_one_run(self):
        out=self._run()
        self.assertEqual(out["vs04_numerics"]["observed_component_count"],5)
        self.assertEqual(out["vs04_readiness"]["expected_check_count"],5)
        self.assertEqual(out["vs04_readiness"]["proven_check_count"],0)
        self.assertEqual(out["vs04_readiness"]["regulatory_checks_executed"],0)
        self.assertEqual(out["engineering_release"],"NOT_READY")
        rid=out["run_id"]
        with urlopen(self.url+"/api/export-checks?run_id="+rid,timeout=7) as r:
            report=json.loads(r.read())
        self.assertEqual(len(report["checks"]),8)
        self.assertEqual(report["vs04_readiness"]["regulatory_checks_executed"],0)
        self.assertEqual(report["source_snapshot"]["analysis_sources"]["readiness_stage_required"],True)
        self.assertIsNotNone(report["source_provenance"]["vs04_readiness_receipt_sha256"])
        with urlopen(self.url+"/report/print?run_id="+rid,timeout=7) as r:
            html=r.read().decode("utf-8")
        self.assertIn("VS04-E · TBDY normatif kanıt kapıları",html)
        self.assertIn("effective_drift_Y",html)
        self.assertEqual(self.calls,1)

    def test_missing_or_corrupted_required_receipt_denies_export(self):
        for tamper in ("missing","corrupt"):
            with self.subTest(tamper=tamper):
                rid=self._run()["run_id"]
                path=next((self.root/rid).glob("*-vs04-readiness.json"))
                if tamper=="missing":
                    path.unlink()
                else:
                    path.write_text(path.read_text(encoding="utf-8").replace(
                        "NOT_PROVEN","FALSE_PASS"),encoding="utf-8")
                with self.assertRaises(HTTPError) as err:
                    urlopen(self.url+"/api/export-checks?run_id="+rid,timeout=7)
                self.assertEqual(err.exception.code,404)

    def test_history_revalidates_readiness_and_sealed_source(self):
        rid=self._run()["run_id"]
        with urlopen(self.url+"/api/quick-history",timeout=7) as r:
            data=json.loads(r.read())
        self.assertEqual(data["runs"][0]["run_id"],rid)
        self.assertEqual(data["runs"][0]["vs04_readiness"]["expected_check_count"],5)
        path=next((self.root/rid).glob("*-vs04-readiness.json"))
        path.unlink()
        with urlopen(self.url+"/api/quick-history",timeout=7) as r:
            data=json.loads(r.read())
        self.assertFalse(any(x["run_id"]==rid for x in data["runs"]))


if __name__=="__main__":
    unittest.main()
