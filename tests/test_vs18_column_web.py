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
from urllib.parse import urlencode
from urllib.request import urlopen

from column_kinematics_fixture import KinematicsBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank
from tbdy_next.web import make_handler


class ColumnKinematicsWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(); cls.root = Path(cls.temp.name)
        source = cls.root/"bank.zip"; source.write_bytes(KinematicsBank().build())
        saved = save_column_bank(source, cls.root/"receipts"); cls.run_id = saved["run_id"]
        cls.database = cls.root/"receipts"/cls.run_id/"column-bank.sqlite"
        cls.source = cls.database.parent/"input.source"
        cls.hashes = [sha256(p.read_bytes()).hexdigest() for p in (cls.database, cls.source)]
        def forbidden(*args, **kwargs): raise AssertionError("Offline kinematics must not call ETABS")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.root/"receipts", live_capture=forbidden))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.base = "http://127.0.0.1:"+str(cls.server.server_address[1])
        cls.query = urlencode({"run_id": cls.run_id})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def get(self, path): return urlopen(self.base+path, timeout=15)

    def test_both_views_filter_member_and_combination_without_pmm(self):
        with patch("tbdy_next.column_engine.demand_view._pmm", side_effect=AssertionError("Unexpected PMM")):
            for view in ("end-forces", "kinematics"):
                with self.get("/api/column-bank?"+self.query+"&view="+view+"&member=C_SYNTHETIC_2&case=SUM") as response:
                    r = json.load(response)
                self.assertEqual(r["demand_page"]["total"], 1)
                self.assertEqual(r["demand_page"]["rows"][0]["point_i"], "P1")
                self.assertEqual(r["column_kinematics"]["linked_member_case_count"], 2)
                self.assertNotIn("rows", r["column_kinematics"])
                self.assertNotIn("column_pmm", r)
                with self.get("/api/column-bank?"+self.query+"&view="+view+"&case=RS_SUM") as response:
                    self.assertEqual(json.load(response)["demand_page"]["total"], 0)

    def test_full_json_preserves_raw_cells_force_keys_and_source_hashes(self):
        with self.get("/api/export-column-bank?"+self.query) as response: r = json.load(response)
        k = r["column_kinematics"]
        self.assertEqual(len(k["rows"]), 2)
        self.assertEqual(k["source_joints_result_sha256"], r["column_joints"]["result_sha256"])
        self.assertEqual(k["source_demand_result_sha256"], r["demand_chain"]["result_sha256"])
        self.assertEqual(k["rows"][0]["joint_j"]["raw"]["Ux"], ".108000")
        self.assertEqual(k["rows"][0]["force_pair"]["j"]["native_key"]["ElmSta"], 1.3)
        self.assertFalse(k["actual_second_order_applied"])
        self.assertEqual(self.hashes, [sha256(p.read_bytes()).hexdigest() for p in (self.database, self.source)])

    def test_html_and_ui_keep_kinematics_separate_from_design_acceptance(self):
        with self.get("/report/column-bank?"+self.query) as response: html = response.read().decode()
        for value in ("VS18", "2/2 kolon–birleşim", "α2=−Δu3/L", "P-Delta", "Nonlinear Case", "NOT_PROVEN", "P1"):
            self.assertIn(value, html)
        self.assertNotIn("<script", html)
        with self.get("/") as response: ui = response.read().decode()
        for value in ('label="İkinci mertebe girdileri"', 'value="end-forces"', 'value="kinematics"'):
            self.assertIn(value, ui)
        with self.get("/api/check-registry") as response: self.assertEqual(json.load(response)["implemented_check_count"], 16)

    def test_cli_uses_existing_bank_without_pmm_or_new_database(self):
        output = io.StringIO()
        with patch("tbdy_next.column_engine.demand_view._pmm", side_effect=AssertionError("Unexpected PMM")), redirect_stdout(output):
            code = main(["inspect-column-demands", "--out", str(self.root/"receipts"), "--run-id", self.run_id, "--kinematics"])
        self.assertEqual(code, 0); r = json.loads(output.getvalue())["column_kinematics"]
        self.assertEqual(r["linked_member_case_count"], 2)
        self.assertEqual(r["analysis_order"], "NOT_PROVEN")
        self.assertEqual(self.hashes, [sha256(p.read_bytes()).hexdigest() for p in (self.database, self.source)])


if __name__ == "__main__": unittest.main()
