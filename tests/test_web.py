"""VS01 local web contract: no COM, no live ETABS side effects."""
from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.web import make_handler

FIXTURES = Path(__file__).parent / "fixtures"


class TestLocalWeb(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Path(self.tmp.name)))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, path, payload=None):
        headers = {}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=payload, headers=headers)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, response.read(), dict(response.headers)
        except HTTPError as exc:
            return exc.code, exc.read(), dict(exc.headers)

    def test_local_ui_serves_english_workspace_and_source_views(self):
        status, data, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"text/html", headers["Content-Type"].encode())
        self.assertIn(b'<html lang="en">', data)
        self.assertIn(b'id="deskCheckTree"', data)
        self.assertIn(b'id="deskRun"', data)
        self.assertIn(b'/workspace-source.js', data)
        self.assertNotIn(b'tbdyPreviewData', data)
        status, data, _ = self.request("/source")
        self.assertEqual(status, 200)
        self.assertIn(b'id="nav"', data)
        self.assertIn(b'/quick.js', data)

    def test_print_bytes_follow_verified_archive_and_reject_modified_html(self):
        from hashlib import sha256
        from unittest.mock import patch
        from tbdy_next.history_catalog import recorded_print_hash, verification_key
        directory = Path(self.tmp.name) / ("RUN-"+"1"*32)
        directory.mkdir()
        source = directory / "input.source"
        source.write_bytes(b"original")
        page = b"<html>verified</html>"
        (directory / "report.html").write_bytes(page)
        recorded_print_hash(directory, verification_key(directory), sha256(page).hexdigest())
        url = self.base + "/report/print?run_id=" + directory.name
        with patch("tbdy_next.web.build_complete_report", side_effect=AssertionError("unexpected rebuild")):
            with urlopen(url) as response:
                self.assertEqual(response.read(), page)
        source.write_bytes(b"altered input")
        (directory / "report.html").write_bytes(b"<html>unverified</html>")
        with patch("tbdy_next.web.build_complete_report", return_value={}) as rebuild, \
             patch("tbdy_next.web.build_printable_html", return_value="<html>new verified</html>"):
            with urlopen(url) as response:
                self.assertEqual(response.read(), b"<html>new verified</html>")
            rebuild.assert_called_once()

    def test_persisted_print_key_tracks_compressed_blob_and_falls_back_without_identity(self):
        from hashlib import sha256
        from unittest.mock import patch
        from tbdy_next.archive_blobs import store_archive
        from tbdy_next.history_catalog import print_verification_key, recorded_print_hash, verification_key

        directory = Path(self.tmp.name) / ("RUN-" + "2"*32)
        directory.mkdir()
        payload = b"sealed source"
        with patch("tbdy_next.archive_blobs.PACK_THRESHOLD", 1):
            store_archive(directory / "input.source", payload)
        key = verification_key(directory)
        recorded_print_hash(directory, key, sha256(b"verified html").hexdigest())
        self.assertEqual(print_verification_key(directory), key)
        with patch("tbdy_next.history_catalog._print_state", return_value=None):
            with patch("tbdy_next.history_catalog.verification_key", wraps=verification_key) as full_check:
                self.assertEqual(print_verification_key(directory), key)
                full_check.assert_called_once_with(directory)
        blob = directory.parent / ".archive-blobs" / (sha256(payload).hexdigest() + ".gz")
        blob.write_bytes(blob.read_bytes() + b"changed")
        self.assertNotEqual(print_verification_key(directory), key)
        with self.assertRaisesRegex(ValueError, "ARCHIVE_CHANGED_DURING_PRINT_REGISTRATION"):
            recorded_print_hash(directory, key, sha256(b"old html").hexdigest())

    def test_health_explicitly_not_ready(self):
        status, data, _ = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["engineering_release"], "NOT_READY")

    def test_modal_api_writes_schema_and_numerical_receipts(self):
        raw = (FIXTURES / "modal_meets.json").read_bytes()
        status, data, _ = self.request("/api/modal?case=Modal", raw)
        self.assertEqual(status, 200)
        body = json.loads(data)
        self.assertEqual(body["result"]["status"], "MEETS_NUMERICAL_CRITERION")
        self.assertEqual(body["result"]["engineering_release"], "NOT_READY")
        receipts = list((Path(self.tmp.name) / body["run_id"]).glob("[0-9][0-9]-*.json"))
        self.assertEqual(len(receipts), 3)
        self.assertEqual(len(list((Path(self.tmp.name) / body["run_id"]).glob("input.source"))), 1)

    def test_actual_discovery_endpoint_not_schema_verified(self):
        raw = (FIXTURES / "preflight_synthetic.json").read_bytes()
        status, data, _ = self.request("/api/discovery", raw)
        self.assertEqual(status, 200)
        result = json.loads(data)["result"]
        self.assertTrue(result["modal_table_listed"])
        self.assertFalse(result["modal_schema_verified"])

    def test_invalid_modal_case_rejected_and_recorded(self):
        raw = (FIXTURES / "modal_meets.json").read_bytes()
        status, data, _ = self.request("/api/modal?case=DoesNotExist", raw)
        self.assertEqual(status, 422)
        body = json.loads(data)
        self.assertEqual(body["result"]["status"], "REJECTED")
        self.assertEqual(len(list((Path(self.tmp.name) / body["run_id"]).glob("*rejected.json"))), 1)

    def test_modal_schema_endpoint_reports_fields_only(self):
        raw = (FIXTURES / "modal_meets.json").read_bytes()
        status, data, _ = self.request("/api/modal-schema", raw)
        self.assertEqual(status, 200)
        result = json.loads(data)["result"]
        self.assertEqual(result["status"], "SCHEMA_FIELDS_PRESENT")
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_history_and_unknown_route(self):
        status, data, _ = self.request("/api/runs")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["runs"], [])
        status, data, _ = self.request("/unsupported")
        self.assertEqual(status, 404)

    def test_missing_length_does_not_process(self):
        req = Request(self.base + "/api/modal?case=Modal", method="POST")
        try:
            urlopen(req, timeout=3)
            self.fail("Expected error")
        except HTTPError as exc:
            self.assertIn(exc.code, (411, 413))


if __name__ == "__main__":
    unittest.main()
