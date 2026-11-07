"""All five checks and every row must remain exportable, without new ETABS calls."""
from __future__ import annotations

from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import unittest

from tbdy_next.web import make_handler
from tbdy_next.reporting import build_complete_report, build_printable_html, ReportUnavailable
from test_quick_suite import fake_live_suite


class ReportExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls: list[str] = []
        def capture(case: str):
            self.calls.append(case)
            return deepcopy(fake_live_suite(case))
        self.server = ThreadingHTTPServer(('127.0.0.1', 0),
                                          make_handler(self.root, live_capture=capture))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.tmp.cleanup()

    def _create(self):
        req = Request(self.base + '/api/live-suite?case=Modal', data=b'', method='POST')
        with urlopen(req, timeout=8) as res:
            self.assertEqual(res.status, 200)
            return json.loads(res.read())['run_id']

    def _get(self, path):
        with urlopen(self.base + path, timeout=8) as res:
            return res.read(), dict(res.headers)

    def test_json_includes_all_five_checks_member_rows_and_source_rows(self):
        run_id = self._create()
        blob, headers = self._get('/api/export-checks?run_id=' + run_id)
        report = json.loads(blob)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(report['schema'], 'tbdy.next.complete.engineering.report.v1')
        self.assertEqual(report['run_id'], run_id)
        self.assertEqual(report['model'], 'kompakt_b.EDB')
        self.assertEqual(report['engineering_release'], 'NOT_READY')
        self.assertEqual(report['formal_compliance'], 'NOT_PROVEN')
        self.assertEqual([r['check_id'] for r in report['checks']], [
            'modal_mass_95', 'column_rect_min', 'beam_width_min',
            'beam_depth_min', 'beam_depth_width'])
        self.assertEqual(report['modal_source_table']['row_count'], 3)
        self.assertEqual(len(report['modal_source_table']['rows']), 3)
        self.assertEqual(len(report['source_snapshot']['geometry_capture']['tables']), 6)
        self.assertEqual(report['geometry_source_summary']['material_types']['source_api'],
                         'PropMaterial.GetTypeOAPI')
        self.assertEqual(report['evaluation_counts']['geometry_item_evaluations'], 11)
        self.assertEqual(sum(len(r['items']) for r in report['checks'][1:]), 11)
        self.assertEqual(self.calls, ['Modal'], 'GET export must not call ETABS')

    def test_repeated_exports_are_identical(self):
        run_id = self._create()
        url = '/api/export-checks?run_id=' + run_id
        first, _ = self._get(url)
        second, _ = self._get(url)
        self.assertEqual(first, second)

    def test_printable_report_contains_all_item_rows_and_modal_rows(self):
        run_id = self._create()
        body, headers = self._get('/report/print?run_id=' + run_id)
        content = body.decode('utf-8')
        self.assertIn('text/html', headers['Content-Type'])
        self.assertIn('FORMAL COMPLIANCE = NOT_PROVEN', content)
        self.assertIn('ENGINEERING RELEASE = NOT_READY', content)
        self.assertIn('Modal kaynak tablosu', content)
        self.assertIn('Kiriş gövde genişliği', content)
        self.assertIn('Kolon kısa kenar', content)
        self.assertIn('C35/45', content)
        # Independent verification: each of the 4 geometry check sections
        # contains every member row, and the 3 original modal rows are kept.
        self.assertEqual(content.count('<section class="percheck">'), 5)
        self.assertGreater(content.count('<tr>'), 18)
        self.assertIn('frame-ancestors', headers['Content-Security-Policy'])
        self.assertEqual(self.calls, ['Modal'])

    def test_rejects_invalid_and_missing_run_id(self):
        for path, expected in [
            ('/api/export-checks', 400),
            ('/api/export-checks?run_id=../x', 400),
            ('/report/print?run_id=RUN-' + '0'*32, 404),
        ]:
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(self.base + path, timeout=8)
                self.assertEqual(raised.exception.code, expected)

    def test_rejects_tampered_geometry_receipt(self):
        run_id = self._create()
        receipt = next((self.root / run_id).glob('*-quick-geometry.json'))
        receipt.write_text(receipt.read_text().replace('SCREENING_PARTIAL', 'FAKE_PASS'))
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + '/api/export-checks?run_id=' + run_id, timeout=8)
        self.assertEqual(raised.exception.code, 404)

    def test_rejects_tampered_input_source(self):
        run_id = self._create()
        source = self.root / run_id / 'input.source'
        content = source.read_text(encoding='utf-8')
        source.write_text(content.replace('C35/45','C22/28',1), encoding='utf-8')
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + '/report/print?run_id=' + run_id, timeout=8)
        self.assertEqual(raised.exception.code, 404)

    def test_not_exportable_if_only_modal_exists(self):
        from tbdy_next.cli import main
        path = Path(__file__).parent / 'fixtures/modal_meets.json'
        self.assertEqual(main(['check-modal', '--input', str(path), '--case','Modal', '--out', str(self.root)]),0)
        run_id = next(self.root.glob('RUN-*')).name
        with self.assertRaises(ReportUnavailable):
            build_complete_report(self.root, run_id)

    def test_report_escapes_injected_markup(self):
        run_id = self._create()
        report = build_complete_report(self.root, run_id)
        report['model'] = '<script>alert(1)</script>'
        text = build_printable_html(report)
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('<script>alert(1)</script>', text)

    def test_ui_includes_report_actions_and_run_selector(self):
        src, _ = self._get('/quick.js')
        js = src.decode('utf-8')
        self.assertIn('Tam JSON dışa aktar', js)
        self.assertIn('Mühendislik raporu / PDF', js)
        self.assertIn('/api/export-checks?run_id=', js)
        self.assertIn('/report/print?run_id=', js)
        self.assertIn('chooseRun.addEventListener', js)


if __name__ == '__main__':
    unittest.main()
