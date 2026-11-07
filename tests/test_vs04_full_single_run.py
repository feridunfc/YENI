"""VS04 E–J single-run web integration and fail-closed receipts.

Synthetic ETABS-shaped tables test routing and data lineage only. They do
not constitute a Windows ETABS acceptance or a normative seismic PASS.
"""
from __future__ import annotations

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
from test_vs04j_base_shear import fixture as base_fixtures
from test_vs04h_linkage import _fixture as diaphragm_fixture


def live_payload(case: str) -> dict:
    payload=fake_live_suite(case)
    payload["geometry_capture"]=vs03_geo()
    payload["next_capture"]=vs03_source()
    analysis=numeric_source()
    analysis["numeric_stage_required"]=True
    analysis["readiness_stage_required"]=True
    analysis["pipeline_stage_required"]=True
    analysis["pipeline_contract_version"]="v2"
    payload["analysis_sources"]=analysis
    payload.setdefault("capture_metadata", {})["vs04_same_session_capture"]=True
    payload["vs04_basis_probe"]=base_fixtures()[0]["source"]
    payload["vs04_diaphragm_probe"]=diaphragm_fixture()["source"]
    return payload


class Vs04SingleRunIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.calls=[]
        def capture(case):
            self.calls.append(case)
            return live_payload(case)
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

    def _post(self):
        req=Request(self.url+"/api/live-vs04?case=Modal",data=b"",method="POST")
        with urlopen(req,timeout=15) as f:
            return json.loads(f.read())

    def _get(self,path):
        with urlopen(self.url+path,timeout=15) as f:
            return f.read().decode("utf8")

    def test_one_live_action_seals_e_to_j_under_one_run_and_exports(self):
        live=self._post()
        self.assertEqual(self.calls,["Modal"])
        self.assertEqual(live["engineering_release"],"NOT_READY")
        pipeline=live["vs04_pipeline"]
        self.assertEqual(pipeline["source_component_count"],6)
        self.assertEqual(pipeline["pipeline_contract_version"],"v2")
        self.assertIsNotNone(pipeline["modal_display_selection_reconciliation"])
        self.assertEqual(pipeline["regulatory_checks_executed"],0)
        self.assertTrue(all(c["reason_codes"] or
                            c["status"] != "NOT_PROVEN"
                            for c in pipeline["checks"]))
        self.assertEqual([r["check_id"] for r in pipeline["checks"]],
            ["BASIS_PROBE","BASIS_LINKAGE","DIAPHRAGM_PROBE",
             "DIAPHRAGM_LINKAGE","SPECTRUM_RECONSTRUCTION","BASE_SHEAR_SCREENING"])
        self.assertTrue(all(r["formal_compliance"]=="NOT_PROVEN"
                            for r in pipeline["checks"]))
        self.assertEqual(pipeline["regulatory_checks_executed"],0)
        self.assertFalse(pipeline["same_analysis_generation_proven"])
        self.assertEqual(live["vs04_readiness"]["proven_check_count"],0)
        rid=live["run_id"]
        files=list((self.root/rid).glob("*-vs04-pipeline.json"))
        self.assertEqual(len(files),1)
        report=json.loads(self._get("/api/export-checks?run_id="+rid))
        self.assertEqual(len(report["checks"]),8)
        self.assertEqual(report["vs04_pipeline"],pipeline)
        self.assertEqual(report["vs04_source_summary"]["pipeline_contract_version"],"v2")
        self.assertIn("VS04 E–J six source-only stages",report["scope"])
        self.assertIsNotNone(report["source_provenance"]["vs04_pipeline_receipt_sha256"])
        self.assertEqual(report["formal_compliance"],"NOT_PROVEN")
        html=self._get("/report/print?run_id="+rid)
        self.assertIn("VS04 E–J",html)
        self.assertIn("BASE_SHEAR_SCREENING",html)
        self.assertIn("NOT_PROVEN",html)
        self.assertIn("Özgün kapsama",html)
        self.assertIn("Seçim bağımlılığı",html)
        self.assertEqual(self.calls,["Modal"],"Export must never call ETABS twice")
        history=json.loads(self._get("/api/quick-history"))
        record=next(x for x in history["runs"] if x["run_id"]==rid)
        self.assertEqual(record["vs04_pipeline"],pipeline)

    def test_deleted_or_corrupt_pipeline_receipt_blocks_both_exports(self):
        for tamper in ("delete","corrupt"):
            with self.subTest(tamper=tamper):
                live=self._post()
                rid=live["run_id"]
                rec=next((self.root/rid).glob("*-vs04-pipeline.json"))
                if tamper=="delete":
                    rec.unlink()
                else:
                    text=rec.read_text(encoding="utf8")
                    rec.write_text(text.replace("NOT_PROVEN","UNTRUE_PASS"),
                                   encoding="utf8")
                for route in ("/api/export-checks?run_id=",
                              "/report/print?run_id="):
                    with self.assertRaises(HTTPError) as err:
                        self._get(route+rid)
                    self.assertEqual(err.exception.code,404)
                history=json.loads(self._get("/api/quick-history"))
                self.assertNotIn(rid,[r["run_id"] for r in history["runs"]])

    def test_required_source_triplet_missing_is_rejected_before_archive(self):
        # Direct source-pipeline evaluation: all mandatory facts must exist.
        from tbdy_next.live_source_pipeline import evaluate_single_run_source_pipeline
        partial=live_payload("Modal")
        partial.pop("vs04_basis_probe")
        out=evaluate_single_run_source_pipeline(partial)
        self.assertEqual(out["status"],"SOURCE_NOT_CAPTURED")
        self.assertEqual(out["regulatory_checks_executed"],0)

    def test_broken_spectrum_source_does_not_promote_normative(self):
        from tbdy_next.live_source_pipeline import evaluate_single_run_source_pipeline
        source=live_payload("Modal")
        source["vs04_basis_probe"]["table_reads"][
            "Functions - Response Spectrum - TSC-2018"]["rows"][0]["SDS"]="NaN"
        r=evaluate_single_run_source_pipeline(source)
        self.assertEqual(r["regulatory_checks_executed"],0)
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(r["engineering_release"],"NOT_READY")
        assert r["stages"]["vs04_i"]["status"]=="NOT_PROVEN"
        assert r["stages"]["vs04_j"]["status"]=="NOT_PROVEN"


if __name__=="__main__":
    unittest.main()
