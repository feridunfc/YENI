"""Offline column report/API contract; no live ETABS dependency."""
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from column_bank_fixture import SyntheticBank
from test_vs07_navigation import PageStructure
from tbdy_next.column_engine.store import save_column_bank
from tbdy_next.web import make_handler


class ColumnWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(); cls.root = Path(cls.temp.name)
        source = cls.root/'synthetic.zip'; source.write_bytes(SyntheticBank().build())
        cls.saved = save_column_bank(source, cls.root/'receipts')
        def forbidden_capture(*args, **kwargs):
            raise AssertionError('Offline inspection must never call ETABS')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(cls.root/'receipts', live_capture=forbidden_capture))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_address[1])
        cls.query = urlencode({'run_id': cls.saved['run_id']})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def get(self, path):
        return urlopen(self.base + path, timeout=10)

    def test_history_and_native_page_share_exact_run(self):
        with self.get('/api/column-history') as response: history = json.load(response)
        self.assertEqual([r['run_id'] for r in history['runs']], [self.saved['run_id']])
        with self.get('/api/column-bank?' + self.query + '&member=C_SYNTHETIC_1&case=G') as response:
            page = json.load(response)
        self.assertEqual(page['result_sha256'], self.saved['result_sha256'])
        self.assertEqual(page['force_page']['total'], 4)
        self.assertEqual(page['force_page']['rows'][0]['P'], -100)
        self.assertEqual(page['design_demand_authority'], 'DENIED')

    def test_json_and_sqlite_exports_preserve_all_vectors_and_traces(self):
        with self.get('/api/export-column-bank?' + self.query) as response:
            report = json.load(response)
            self.assertIn('attachment', response.headers['Content-Disposition'])
        self.assertEqual(len(report['force_states']), 64)
        self.assertEqual(len(report['static_replay']['items']), 8)
        self.assertEqual(report['database_sha256'], self.saved['database_sha256'])
        with self.get('/api/export-column-bank?' + self.query + '&format=sqlite') as response:
            raw = response.read()
            self.assertEqual(response.headers['Content-Type'], 'application/vnd.sqlite3')
        self.assertEqual(sha256(raw).hexdigest(), report['database_sha256'])
        self.assertEqual(raw[:16], b'SQLite format 3\x00')

    def test_html_print_report_contains_scope_counts_and_end_geometry(self):
        with self.get('/report/column-bank?' + self.query) as response:
            html = response.read().decode()
            self.assertIn("default-src 'none'", response.headers['Content-Security-Policy'])
        for value in ('2/2', '64 kuvvet satırı', '48 skaler', '3.3', 'NOT_PROVEN / NOT_READY',
                      'MISSING', 'SUM', self.saved['source_archive_sha256'], self.saved['result_sha256']):
            self.assertIn(value, html)
        self.assertNotIn('<script', html)

    def test_bad_query_or_absent_run_cannot_select_another_archive(self):
        for path, code in (
            ('/api/column-bank?run_id=../bank', 400),
            ('/api/column-bank?' + self.query + '&run_id=other', 400),
            ('/api/column-bank?' + self.query + '&offset=-1', 400),
            ('/api/export-column-bank?' + self.query + '&format=exe', 400),
            ('/report/column-bank?' + self.query + '&path=elsewhere', 400),
            ('/api/column-bank?run_id=RUN-' + '0'*32, 404)):
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught: self.get(path)
            self.assertEqual(caught.exception.code, code)

    def test_ui_panel_is_under_columns_and_script_is_served(self):
        with self.get('/') as response: html = response.read().decode()
        page = PageStructure(html)
        self.assertEqual(page.ids['columnBankPanel'], 1)
        self.assertIn('columncontent', [p[1] for p in page.ancestors['columnBankPanel']])
        self.assertIn("getElementById('columncontent').classList.toggle('hidden',i!==12)", html)
        self.assertIn('<script src="/column.js">', html)
        with self.get('/column.js') as response:
            script = response.read().decode()
            self.assertIn('text/javascript', response.headers['Content-Type'])
        self.assertIn('window.openColumnBank', script)
        with self.get('/api/check-registry') as response: registry = json.load(response)
        self.assertEqual(registry['implemented_check_count'], 16, 'A source bank is not an extra normative CHECK')


if __name__ == '__main__':
    unittest.main()
