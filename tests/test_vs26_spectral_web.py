from contextlib import redirect_stdout
from hashlib import sha256
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from column_spectral_fixture import SpectralBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank, read_column_bank
from tbdy_next.spectral_report import build_spectral_html
from tbdy_next.web import make_handler


class ParsedPage(HTMLParser):
    def __init__(self):
        super().__init__(); self.open_details = 0; self.scripts = 0
    def handle_starttag(self, tag, attrs):
        self.open_details += tag == 'details' and 'open' in dict(attrs)
        self.scripts += tag == 'script'


class SpectralWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(); cls.root = Path(cls.temp.name); cls.receipts = cls.root/'receipts'
        source = cls.root/'bank.zip'; source.write_bytes(SpectralBank().build())
        cls.run_id = save_column_bank(source, cls.receipts)['run_id']
        cls.paths = [cls.receipts/cls.run_id/f for f in ('input.source', 'column-bank.sqlite')]
        cls.hashes = [sha256(p.read_bytes()).hexdigest() for p in cls.paths]
        def forbidden(*args, **kwargs): raise AssertionError('Spectral envelope view must remain offline')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(cls.receipts, live_capture=forbidden))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_address[1])
        cls.query = 'run_id=' + cls.run_id + '&view=spectral-envelopes'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def get(self, path): return urlopen(self.base + path, timeout=30)

    def test_http_scope_filters_first_without_loading_capacity(self):
        with patch('tbdy_next.column_engine.demand_view._derive', side_effect=AssertionError('No capacity or static-chain derivation')):
            with self.get('/api/column-bank?' + self.query + '&member=C_SYNTHETIC_1&case=RS_SUM&offset=1') as response:
                report = json.load(response)
        page = report['demand_page']
        self.assertEqual((page['total'], page['offset'], len(page['rows'])), (4, 1, 3))
        self.assertTrue(all(r['member_id'] == 'C_SYNTHETIC_1' and r['output_case'] == 'RS_SUM' for r in page['rows']))
        for key in ('force_page', 'force_states', 'column_pmm', 'column_pmm_quality', 'scwb_scenarios', 'demand_chain'):
            self.assertNotIn(key, report)

    def test_explicit_page_json_export_matches_view_not_full_bank(self):
        query = self.query + '&member=C_SYNTHETIC_1&case=RS_SUM&offset=2'
        with self.get('/api/column-bank?' + query) as response: shown = json.load(response)
        with self.get('/api/export-column-bank?' + query) as response:
            self.assertIn('spectral_page_2.json', response.headers['Content-Disposition'])
            exported = json.load(response)
        self.assertEqual(shown, exported)
        self.assertEqual(len(exported['demand_page']['rows']), 2)
        self.assertNotIn('rows', exported['column_spectral_envelopes'])
        self.assertNotIn('force_states', exported)

    def test_report_is_filtered_compact_escaped_and_details_closed(self):
        query = self.query + '&member=C_SYNTHETIC_1&case=RS_SUM&offset=2'
        with self.get('/report/column-bank?' + query) as response:
            html = response.read().decode(); self.assertIn("default-src 'none'", response.headers['Content-Security-Policy'])
        self.assertIn('seçili sayfadır: 3–4 / 4', html)
        first_table = html[html.index('<table>'):html.index('</table>')]
        self.assertEqual(first_table.count('<tr>'), 3)
        self.assertNotIn('source_row_id', first_table)
        self.assertIn('V2, V3 ve T sınırları', html)
        self.assertIn('N alt=−P üst', html)
        self.assertIn('NOT_PROVEN / NOT_READY', html)
        parsed = ParsedPage(); parsed.feed(html)
        self.assertEqual((parsed.open_details, parsed.scripts), (0, 0))
        report = read_column_bank(self.receipts, self.run_id, view='spectral-envelopes', limit=1)
        report['demand_page']['rows'][0]['story'] = '<script>alert(1)</script>'
        escaped = build_spectral_html(report)
        self.assertIn('&lt;script&gt;', escaped); self.assertNotIn('<script>', escaped)

    def test_export_query_cannot_silently_ignore_filters_or_export_sqlite(self):
        for path, query in (
            ('/api/export-column-bank?', self.query + '&format=sqlite'),
            ('/api/export-column-bank?', 'run_id=' + self.run_id + '&member=C_SYNTHETIC_1'),
            ('/report/column-bank?', 'run_id=' + self.run_id + '&view=pmm'),
            ('/api/column-bank?', self.query + '&offset=-1'),
            ('/api/column-bank?', self.query + '&view=native'),
            ('/api/column-bank?', self.query + '&column_cage=16x24')):
            with self.subTest(query=query), self.assertRaises(HTTPError) as error: self.get(path + query)
            self.assertEqual(error.exception.code, 400); error.exception.close()
        with self.assertRaisesRegex(ValueError, 'PAGE_SCOPE'):
            read_column_bank(self.receipts, self.run_id, view='spectral-envelopes', full=True)

    def test_empty_filter_retains_global_counts_and_reports_no_local_rows(self):
        report = read_column_bank(self.receipts, self.run_id, view='spectral-envelopes', output_case='SUM')
        self.assertEqual(report['demand_page']['total'], 0)
        self.assertEqual(report['column_spectral_envelopes']['matched_rows'], 32)
        self.assertIn('0–0 / 0', build_spectral_html(report))

    def test_source_and_database_tampering_fail_even_after_cache_warmed(self):
        for filename in ('input.source', 'column-bank.sqlite'):
            with self.subTest(file=filename), TemporaryDirectory() as folder:
                root = Path(folder); source = root/'source.zip'; source.write_bytes(SpectralBank().build())
                run = save_column_bank(source, root/'receipts')['run_id']
                read_column_bank(root/'receipts', run, view='spectral-envelopes')
                changed = root/'receipts'/run/filename; original = changed.read_bytes()
                changed.write_bytes(original + b'TAMPER')
                with self.assertRaisesRegex(ValueError, 'ARCHIVE_OR_DATABASE_CHANGED'):
                    read_column_bank(root/'receipts', run, view='spectral-envelopes')

    def test_static_candidate_population_and_result_hash_are_unchanged(self):
        before = read_column_bank(self.receipts, self.run_id, view='static')['demand_chain']
        report = read_column_bank(self.receipts, self.run_id, view='spectral-envelopes')
        report['demand_page']['rows'][0]['bounds']['N']['upper'] = 999999
        after = read_column_bank(self.receipts, self.run_id, view='static')['demand_chain']
        self.assertEqual(before, after)
        self.assertEqual(after['static_candidate_count'], 8)
        fresh = read_column_bank(self.receipts, self.run_id, view='spectral-envelopes')
        self.assertNotEqual(fresh['demand_page']['rows'][0]['bounds']['N']['upper'], 999999)
        self.assertEqual(self.hashes, [sha256(p.read_bytes()).hexdigest() for p in self.paths])

    def test_normal_views_do_not_compute_spectral_envelopes(self):
        with patch('tbdy_next.column_engine.demand_view._spectral', side_effect=AssertionError('Unexpected spectral replay')):
            for view in ('native', 'static', 'overview', 'pmm'):
                self.assertNotIn('column_spectral_envelopes', read_column_bank(self.receipts, self.run_id, view=view))

    def test_cli_summary_and_correct_ui_group(self):
        out = io.StringIO()
        with redirect_stdout(out), patch('tbdy_next.column_engine.demand_view._derive', side_effect=AssertionError('No capacity solve')):
            code = main(['inspect-column-demands', '--run-id', self.run_id, '--out', str(self.receipts), '--spectral'])
        self.assertEqual(code, 0)
        result = json.loads(out.getvalue()); self.assertEqual(result['matched_rows'], 32)
        self.assertNotIn('rows', result); self.assertNotIn('spectral_cases', result)
        with self.get('/') as response: html = response.read().decode()
        group = html[html.index('<optgroup label="Kuvvetler ve birleşimler">'):]
        self.assertIn('value="spectral-envelopes"', group[:group.index('</optgroup>')])

    def test_html_does_not_accept_a_foreign_or_approved_result(self):
        for key, value in (('source_archive_sha256', 'OTHER'), ('code_rule_qualified', True), ('physical_concurrency_proven', True)):
            report = read_column_bank(self.receipts, self.run_id, view='spectral-envelopes')
            report['column_spectral_envelopes'][key] = value
            with self.assertRaisesRegex(ValueError, 'CONTRACT_INVALID'): build_spectral_html(report)
