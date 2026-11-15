"""VS01 live click -> owned capture -> existing parser -> receipts -> UI history.

No Windows or COM required; only bounded fake ETABS capture, same as previous
VS01 acceptance tests. The separate real Windows run remains operator-owned.
"""
from __future__ import annotations

from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.history import modal_history
from tbdy_next.etabs_modal import ModalCaptureError
from tbdy_next.live_etabs import (
    EtabsUnitsError, _attach_etabs, _session_info, read_quick_suite_from_running_etabs,
    select_etabs_capture_units,
)
from tbdy_next.web import make_handler

FIXTURE = Path(__file__).parent / 'fixtures/modal_meets.json'


def live_fixture(_: str) -> dict:
    payload = deepcopy(json.loads(FIXTURE.read_text(encoding='utf-8')))
    payload['source_mode'] = 'LIVE_ETABS'
    payload['capture_metadata'] = {
        'model_filename': r'C:\tmp\kompakt_b.EDB', 'case_row_count': 2,
        'display_selection_restored': True, 'analysis_generation_proven': False,
    }
    return payload


class TestLiveModalFromUI(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.calls: list[str] = []
        self.reader = lambda case: (self.calls.append(case), live_fixture(case))[1]
        self.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), make_handler(Path(self.temp.name), live_capture=self.reader)
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def send(self, *, path='/api/live-modal?case=Modal', body=b'', origin=None):
        headers={}
        if origin is not None:
            headers['Origin']=origin
        req=Request(self.base+path, data=body, headers=headers, method='POST')
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_one_click_gets_live_etabs_result_and_receipt(self):
        status, body=self.send()
        self.assertEqual(status,200)
        self.assertEqual(self.calls,['Modal'])
        self.assertEqual(body['model_name'],'kompakt_b.EDB')
        self.assertEqual(body['source_rows'],3)
        self.assertEqual(body['case_row_count'],2)
        self.assertEqual(body['result']['sum_ux'],'0.96')
        self.assertEqual(body['result']['status'],'MEETS_NUMERICAL_CRITERION')
        self.assertEqual(body['engineering_release'],'NOT_READY')
        path=Path(self.temp.name)/body['run_id']
        self.assertEqual(len(list(path.glob('*.json'))),4)
        self.assertTrue((path/'input.source').is_file())
        hist=modal_history(Path(self.temp.name))
        self.assertEqual(len(hist),1)
        self.assertEqual(hist[0]['source_mode'],'LIVE_ETABS')
        self.assertEqual(hist[0]['case_row_count'],2)

    def test_history_endpoint_exposes_previous_real_results(self):
        self.send()
        with urlopen(self.base+'/api/modal-history', timeout=5) as response:
            hist=json.loads(response.read())['runs']
        self.assertEqual(hist[0]['model_name'],'kompakt_b.EDB')
        self.assertEqual(hist[0]['result']['sum_uy'],'0.96')
        self.assertEqual(hist[0]['engineering_release'],'NOT_READY')

    def test_missing_case_does_not_touch_etabs(self):
        code, payload=self.send(path='/api/live-modal')
        self.assertEqual(code,400)
        self.assertEqual(payload['reason'],'EXACT_MODAL_CASE_REQUIRED')
        self.assertEqual(self.calls,[])

    def test_cross_origin_cannot_trigger_live_etabs(self):
        code, payload=self.send(origin='https://untrusted.example')
        self.assertEqual(code,403)
        self.assertEqual(payload['reason'],'CROSS_ORIGIN_DENIED')
        self.assertEqual(self.calls,[])

    def test_body_upload_is_not_allowed_for_live_endpoint(self):
        code, payload=self.send(body=b'{}')
        self.assertEqual(code,400)
        self.assertEqual(payload['reason'],'LIVE_REQUEST_MUST_HAVE_NO_BODY')
        self.assertEqual(self.calls,[])

    def test_unavailable_etabs_never_yields_fake_result(self):
        def broken(_case):
            raise RuntimeError('ACTIVE_ETABS_NOT_FOUND')
        self.server.RequestHandlerClass=make_handler(Path(self.temp.name), live_capture=broken)
        code,payload=self.send()
        self.assertEqual(code,503)
        self.assertEqual(payload['status'],'CAPTURE_REJECTED')
        self.assertNotIn('result',payload)
        self.assertEqual(list(Path(self.temp.name).glob('RUN-*')),[])

    def test_units_diagnostic_and_scan_rejection_retain_attached_model(self):
        sap = Mock()
        sap.GetModelFilename.return_value = r'C:\tmp\kompakt_b.EDB'
        sap.GetPresentUnits.return_value = 12
        sap.GetPresentUnits_2.return_value = (6, 6, 2, 0)
        session = _session_info(sap, 2056, True)
        self.assertEqual(session, {
            'model_name': 'kompakt_b.EDB', 'model_locked': True, 'process_id': 2056,
            'attachment': 'PROCESS_ID', 'units_code': 12, 'units_label': 'tonf·m·°C',
            'units_api_agree': True,
        })
        self.server.RequestHandlerClass = make_handler(Path(self.temp.name), etabs_pid=2056)
        connected = {**session, 'units_code': 6, 'units_label': 'kN·m·°C'}
        with patch('tbdy_next.live_etabs.select_etabs_capture_units',
                   return_value={'before': session, 'after': connected}) as connect:
            status, diagnostic = self.send(path='/api/etabs-session')
            self.assertEqual(status, 200)
            self.assertEqual(diagnostic['etabs_session'], connected)
            self.assertEqual(diagnostic['required_units_code'], 6)
            self.assertEqual(self.send(path='/api/etabs-session?pid=9')[0], 400)
            self.assertEqual(self.send(path='/api/etabs-session', origin='https://external.example')[0], 403)
            connect.assert_called_once_with(2056)
        with patch('tbdy_next.live_etabs.read_quick_suite_from_running_etabs',
                   side_effect=EtabsUnitsError(session)) as read_suite:
            status, rejection = self.send(path='/api/live-vs04?case=Modal')
            self.assertEqual(status, 503)
            self.assertEqual(rejection['etabs_session'], session)
            self.assertIn('expected=6;observed=12', rejection['reason'])
            read_suite.assert_called_once_with('Modal', with_vs04=True, process_id=2056)
        self.assertEqual(list(Path(self.temp.name).glob('RUN-*')), [])

    def test_explicit_pid_never_falls_back_to_another_analysed_model(self):
        client = Mock()
        helper = client.CreateObject.return_value
        helper.GetObjectProcess.return_value = None
        with self.assertRaisesRegex(ModalCaptureError, 'PID 2056 is unavailable'):
            _attach_etabs(client, 2056)
        helper.GetObjectProcess.assert_called_once_with('CSI.ETABS.API.ETABSObject', 2056)
        client.GetActiveObject.assert_not_called()

    def test_unit_setters_must_verify_matching_getters_before_numeric_capture(self):
        sap = Mock()
        sap.GetModelFilename.return_value = r'C:\tmp\kompakt_b.EDB'
        sap.GetModelIsLocked.return_value = True
        sap.GetPresentUnits.return_value = 6
        sap.GetPresentUnits_2.return_value = (6, 6, 2, 0)
        sap.SetPresentUnits.return_value = 0
        sap.SetPresentUnits_2.return_value = 0
        with patch('tbdy_next.live_etabs.sys.platform', 'win32'), \
                patch('tbdy_next.live_etabs._with_etabs', side_effect=lambda _, action: action(sap)), \
                patch('tbdy_next.live_etabs.capture_modal') as capture:
            with self.assertRaises(EtabsUnitsError) as error:
                read_quick_suite_from_running_etabs('Modal', with_vs04=True)
            self.assertIs(error.exception.session['units_api_agree'], False)
            sap.SetPresentUnits.assert_called_once_with(6)
            sap.SetPresentUnits_2.assert_called_once_with(4, 6, 2)
            capture.assert_not_called()

    def test_pid_bound_unit_setup_can_use_both_csi_setters(self):
        sap = Mock()
        sap.GetModelFilename.return_value = r'C:\tmp\kompakt_b.EDB'
        sap.GetModelIsLocked.return_value = True
        sap.GetPresentUnits.side_effect = (12, 12, 6)
        sap.GetPresentUnits_2.side_effect = ((6, 6, 2, 0), (6, 6, 2, 0), (4, 6, 2, 0))
        sap.SetPresentUnits.return_value = 0
        sap.SetPresentUnits_2.return_value = 0
        with patch('tbdy_next.live_etabs._with_etabs', side_effect=lambda _, action: action(sap)) as attach:
            result = select_etabs_capture_units(2056)
        self.assertEqual(attach.call_args.args[0], 2056)
        self.assertEqual(result['before']['units_code'], 12)
        self.assertEqual(result['after']['units_code'], 6)
        sap.SetPresentUnits.assert_called_once_with(6)
        sap.SetPresentUnits_2.assert_called_once_with(4, 6, 2)

    def test_scan_selects_units_and_leaves_them_selected(self):
        events = []
        sap = Mock()
        sap.GetModelFilename.return_value = r'C:\tmp\kompakt_b.EDB'
        sap.GetModelIsLocked.return_value = True
        def set_units(code):
            sap.GetPresentUnits.return_value = code
            sap.GetPresentUnits_2.return_value = ((4 if code == 6 else 6), 6, 2, 0)
            events.append(code)
            return 0
        sap.SetPresentUnits.side_effect = set_units
        set_units(12)
        def capture(_, case):
            events.append(f'capture {case}')
            self.assertEqual(sap.GetPresentUnits(), 6)
            return live_fixture(case)
        with patch('tbdy_next.live_etabs.sys.platform', 'win32'), \
                patch('tbdy_next.live_etabs._with_etabs', side_effect=lambda _, action: action(sap)), \
                patch('tbdy_next.live_etabs.capture_modal', side_effect=capture) as modal, \
                patch('tbdy_next.etabs_geometry.capture_geometry', return_value={}), \
                patch('tbdy_next.next_capture.capture_next_facts', return_value={}):
            payload = read_quick_suite_from_running_etabs('Modal', process_id=2056)
            self.assertEqual(events, [12, 6, 'capture Modal'])
            meta = payload['capture_metadata']
            self.assertEqual(meta['etabs_session']['units_code'], 6)
            self.assertEqual(meta['etabs_session_before_scan']['units_code'], 12)
            self.assertEqual(meta['etabs_session_after_scan']['units_code'], 6)
            modal.side_effect = ModalCaptureError('source unavailable')
            with self.assertRaisesRegex(ModalCaptureError, 'source unavailable'):
                read_quick_suite_from_running_etabs('Modal', process_id=2056)
            self.assertEqual(events, [12, 6, 'capture Modal'])
            self.assertEqual(sap.GetPresentUnits(), 6)

    def test_live_source_invalid_schema_is_rejected_and_archived(self):
        def invalid(case):
            payload=live_fixture(case)
            payload['table']['row_count']=10
            return payload
        self.server.RequestHandlerClass=make_handler(Path(self.temp.name), live_capture=invalid)
        code,payload=self.send()
        self.assertEqual(code,422)
        self.assertEqual(payload['result']['status'],'REJECTED')
        path=Path(self.temp.name)/payload['run_id']
        self.assertTrue((path/'input.source').is_file())
        self.assertEqual(modal_history(Path(self.temp.name)),[])


    def test_full_table_endpoint_returns_all_fields_and_rows(self):
        status, body = self.send()
        self.assertEqual(status, 200)
        run_id = body['run_id']
        with urlopen(self.base + '/api/modal-table?run_id=' + run_id, timeout=5) as response:
            table = json.loads(response.read())['table']
        self.assertEqual(table['run_id'], run_id)
        self.assertEqual(table['table_key'], 'Modal Participating Mass Ratios')
        self.assertEqual(table['fields'], ['Case', 'Mode', 'UX', 'UY', 'SumUX', 'SumUY'])
        self.assertEqual(table['row_count'], 3)
        self.assertEqual(len(table['rows']), 3)
        self.assertEqual(table['case_row_count'], 2)
        self.assertEqual(table['rows'][2]['Case'], 'Other')
        self.assertEqual(table['engineering_release'], 'NOT_READY')

    def test_full_table_endpoint_rejects_unknown_and_invalid_runs(self):
        for path, expected in [
            ('/api/modal-table', 400),
            ('/api/modal-table?run_id=../../x', 400),
            ('/api/modal-table?run_id=RUN-' + '0'*32, 404),
        ]:
            with self.subTest(path=path):
                try:
                    urlopen(self.base + path, timeout=5)
                    self.fail('Expected HTTP error')
                except HTTPError as error:
                    self.assertEqual(error.code, expected)

    def test_full_table_endpoint_rejects_modified_source(self):
        status, body = self.send()
        self.assertEqual(status, 200)
        run_id = body['run_id']
        source = Path(self.temp.name) / run_id / 'input.source'
        text = source.read_text(encoding='utf-8')
        source.write_text(text.replace('0.96', '0.99', 1), encoding='utf-8')
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + '/api/modal-table?run_id=' + run_id, timeout=5)
        self.assertEqual(raised.exception.code, 404)

    def test_full_table_ui_is_below_numerical_note(self):
        with urlopen(self.base + '/source', timeout=5) as response:
            html = response.read().decode('utf-8')
        self.assertIn('modal-table-divider', html)
        self.assertIn('window.showModalFullTable(data.run_id)', html)
        with urlopen(self.base + '/history.js', timeout=5) as response:
            script = response.read().decode('utf-8')
        self.assertIn("node('hr', undefined, 'modal-table-divider')", script)
        self.assertIn('showModalFullTable(entry.run_id)', script)
        self.assertIn('for (const row of record.rows)', script)

    def test_ui_has_direct_connection_no_mandatory_file_selection(self):
        with urlopen(self.base+'/source',timeout=5) as response:
            html=response.read().decode('utf-8')
        self.assertIn('id="runAllBtn"',html)
        self.assertNotIn('id="liveModalBtn"',html)
        self.assertIn('Developer tools and offline source import',html)
        self.assertIn('/history.js',html)
        with urlopen(self.base+'/quick.js',timeout=5) as response:
            js=response.read().decode('utf-8')
        self.assertIn("/api/live-vs04?case=",js)
        self.assertNotIn("/api/live-modal?case=",js)

if __name__=='__main__':
    unittest.main()
