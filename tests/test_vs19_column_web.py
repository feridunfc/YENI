from contextlib import redirect_stdout
from hashlib import sha256
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from column_kinematics_fixture import KinematicsBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank
from tbdy_next.web import make_handler


class ColumnSensitivityWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(); cls.root = Path(cls.temp.name)
        source = cls.root/"bank.zip"; source.write_bytes(KinematicsBank().build())
        saved = save_column_bank(source, cls.root/"receipts"); cls.run_id = saved["run_id"]
        cls.database = cls.root/"receipts"/cls.run_id/"column-bank.sqlite"
        cls.source = cls.database.parent/"input.source"
        cls.hashes = [sha256(p.read_bytes()).hexdigest() for p in (cls.database, cls.source)]
        def forbidden(*args, **kwargs): raise AssertionError("Sensitivity must stay offline")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.root/"receipts", live_capture=forbidden))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.base = "http://127.0.0.1:"+str(cls.server.server_address[1])
        cls.query = urlencode({"run_id": cls.run_id})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def get(self, path): return urlopen(self.base+path, timeout=15)

    def test_two_views_keep_section_and_case_scope_distinct_without_pmm(self):
        with patch("tbdy_next.column_engine.demand_view._pmm", side_effect=AssertionError("Unexpected PMM")):
            with self.get("/api/column-bank?"+self.query+"&view=stiffness-scenarios&member=C_SYNTHETIC_2") as response:
                r = json.load(response)
            self.assertEqual(r["demand_page"]["total"], 2)
            self.assertEqual(r["column_sensitivity"]["calculated_axis_count"], 4)
            self.assertNotIn("rows", r["column_sensitivity"]); self.assertNotIn("axes", r["column_sensitivity"])
            self.assertNotIn("column_pmm", r)
            with self.get("/api/column-bank?"+self.query+"&view=length-sensitivity&member=C_SYNTHETIC_2&case=SUM") as response:
                r = json.load(response)
            self.assertEqual(r["demand_page"]["total"], 8)
            self.assertEqual(len(r["column_sensitivity"]["axial_profiles"]), 1)
            with self.get("/api/column-bank?"+self.query+"&view=length-sensitivity&case=RS_SUM") as response:
                r = json.load(response)
            self.assertEqual(r["demand_page"]["total"], 0)
            self.assertEqual(r["column_sensitivity"]["axial_profiles"], [])
        with self.assertRaises(HTTPError) as caught:
            self.get("/api/column-bank?"+self.query+"&view=stiffness-scenarios&case=SUM")
        self.assertEqual(caught.exception.code, 400)

    def test_full_json_keeps_all_states_and_original_source_bytes(self):
        with self.get("/api/export-column-bank?"+self.query) as response: r = json.load(response)
        s = r["column_sensitivity"]
        self.assertEqual(len(s["rows"]), 16); self.assertEqual(len(s["axes"]), 4)
        self.assertEqual(s["source_kinematics_result_sha256"], r["column_kinematics"]["result_sha256"])
        self.assertEqual(s["source_stability_result_sha256"], r["column_stability"]["result_sha256"])
        self.assertEqual(s["zero_length_reference_count"], 48)
        self.assertEqual(s["source_denominator_count"], 144)
        self.assertFalse(s["source_population_reduced"])
        self.assertEqual(self.hashes, [sha256(p.read_bytes()).hexdigest() for p in (self.database, self.source)])

    def test_html_ui_and_registry_expose_references_without_design_acceptance(self):
        with self.get("/report/column-bank?"+self.query) as response: html = response.read().decode()
        for value in ("VS19", "Etkin boy ve rijitlik duyarlılığı", "Rm=0/0,5/1", "i=0,30h", "Nk=N Euler boyu değildir",
                      "40i önlenmiş sınıfın yalnız üst sınırı", "NOT_PROVEN", "RECORDED_AXIAL_VALUES_DIFFER"):
            self.assertIn(value, html)
        self.assertNotIn("<script", html)
        with self.get("/") as response: ui = response.read().decode()
        self.assertIn('value="stiffness-scenarios"', ui); self.assertIn('value="length-sensitivity"', ui)
        with self.get("/api/check-registry") as response: self.assertEqual(json.load(response)["implemented_check_count"], 16)

    def test_cli_summary_reads_existing_receipt_without_new_bank(self):
        output = io.StringIO()
        with patch("tbdy_next.column_engine.demand_view._pmm", side_effect=AssertionError("Unexpected PMM")), redirect_stdout(output):
            code = main(["inspect-column-demands", "--out", str(self.root/"receipts"), "--run-id", self.run_id, "--sensitivity"])
        self.assertEqual(code, 0); s = json.loads(output.getvalue())["column_sensitivity"]
        self.assertEqual(s["state_axis_count"], 16)
        self.assertEqual(s["euler_reference_count"], 36)
        self.assertEqual(s["formal_compliance"], "NOT_PROVEN")
        self.assertFalse(s["actual_second_order_applied"])
        self.assertEqual(self.hashes, [sha256(p.read_bytes()).hexdigest() for p in (self.database, self.source)])


if __name__ == "__main__": unittest.main()
