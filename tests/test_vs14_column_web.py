from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from column_stability_fixture import StiffnessBank
from tbdy_next.column_engine.store import save_column_bank
from tbdy_next.web import make_handler


class StabilityWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(); cls.root=Path(cls.temp.name)
        source=cls.root/'bank.zip'; source.write_bytes(StiffnessBank().build())
        saved=save_column_bank(source,cls.root/'receipts')
        def forbidden(*args,**kwargs): raise AssertionError('Offline stiffness must not call ETABS')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.root/'receipts',live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.query=urlencode({'run_id':saved['run_id']})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def get(self,path): return urlopen(self.base+path,timeout=10)

    def test_member_stiffness_is_linked_to_existing_demands_and_rejects_case_filter(self):
        with self.get('/api/column-bank?'+self.query+'&view=stiffness&member=C_SYNTHETIC_1') as response:
            report=json.load(response)
        self.assertEqual(report['demand_page']['total'],1)
        row=report['demand_page']['rows'][0]
        self.assertEqual(row['elastic']['observed_E_MPa'],34000)
        self.assertIsNone(row['second_order']['magnification_factor'])
        self.assertEqual(report['column_stability']['source_prechecks_result_sha256'],report['column_prechecks']['result_sha256'])
        with self.assertRaises(HTTPError) as caught:
            self.get('/api/column-bank?'+self.query+'&view=stiffness&case=SUM')
        self.assertEqual(caught.exception.code,400)

    def test_eccentricity_view_keeps_state_identity_and_json_has_all_reference_rows(self):
        with self.get('/api/column-bank?'+self.query+'&view=eccentricity&member=C_SYNTHETIC_2&case=SUM') as response:
            report=json.load(response)
        self.assertEqual(report['demand_page']['total'],4)
        self.assertEqual(report['demand_page']['rows'][0]['axes'][0]['e_min_mm'],'39')
        self.assertTrue(all(r['native_key']['Obj']=='C_SYNTHETIC_2' for r in report['demand_page']['rows']))
        with self.get('/api/export-column-bank?'+self.query) as response: full=json.load(response)
        self.assertEqual(len(full['demand_chain']['candidates']),8)
        self.assertEqual(len(full['column_stability']['eccentricity']['rows']),8)
        self.assertFalse(full['column_stability']['actual_second_order_applied'])

    def test_report_and_ui_expose_source_scope_and_keep_control_count(self):
        with self.get('/report/column-bank?'+self.query) as response: html=response.read().decode()
        for value in ('VS14','Kesit rijitliği','34000','Minimum dışmerkezlik','6.16','7.29',
                      'Çıktı aralığı serbest boy değildir','iç istasyon kıyasları','NOT_PROVEN'):
            self.assertIn(value,html)
        self.assertNotIn('<script',html)
        with self.get('/') as response: ui=response.read().decode()
        for value in ('value="stiffness"','value="eccentricity"','Kesit ve ön hesaplar'):
            self.assertIn(value,ui)
        with self.get('/api/check-registry') as response: registry=json.load(response)
        self.assertEqual(registry['implemented_check_count'],16)


if __name__=='__main__': unittest.main()
