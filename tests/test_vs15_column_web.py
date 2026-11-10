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


class ColumnPmmWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name)
        source=cls.root/'bank.zip';source.write_bytes(StiffnessBank().build())
        saved=save_column_bank(source,cls.root/'receipts')
        def forbidden(*args,**kwargs):raise AssertionError('Offline PMM must not call ETABS')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.root/'receipts',live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.query=urlencode({'run_id':saved['run_id']})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()

    def get(self,path):return urlopen(self.base+path,timeout=15)

    def test_cages_reject_case_filter_and_preserve_proposed_cover_geometry(self):
        with self.get('/api/column-bank?'+self.query+'&view=cages&member=C_SYNTHETIC_1') as response:report=json.load(response)
        self.assertEqual(report['demand_page']['total'],3)
        self.assertEqual(report['demand_page']['rows'][0]['center_offset_mm'],64)
        self.assertIsNone(report['column_cages']['selected_design'])
        with self.assertRaises(HTTPError) as caught:self.get('/api/column-bank?'+self.query+'&view=cages&case=SUM')
        self.assertEqual(caught.exception.code,400)

    def test_pmm_filter_and_full_export_preserve_all_source_states_and_authority(self):
        with self.get('/api/column-bank?'+self.query+'&view=pmm&member=C_SYNTHETIC_2&case=SUM') as response:report=json.load(response)
        self.assertEqual(report['demand_page']['total'],12)
        self.assertNotIn('rows',report['column_pmm'])
        self.assertTrue(all(r['member_id']=='C_SYNTHETIC_2' for r in report['demand_page']['rows']))
        with self.get('/api/export-column-bank?'+self.query) as response:full=json.load(response)
        self.assertEqual(len(full['column_pmm']['rows']),24)
        self.assertEqual(full['column_pmm']['source_cages_result_sha256'],full['column_cages']['result_sha256'])
        self.assertEqual(full['column_pmm']['design_demand_authority'],'DENIED')

    def test_report_includes_cage_drawings_and_conditioned_ratios_without_new_completed_check(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        for value in ('VS15','16Φ24','<svg','Koşullu PMM','72/144/288','1152','γc=1,5',
                      'Minimum dışmerkezlik ve ikinci mertebe uygulanmadı','NOT_READY'):
            self.assertIn(value,html)
        self.assertEqual(html.count('<circle '),48)
        self.assertNotIn('<script',html)
        with self.get('/') as response:ui=response.read().decode()
        for value in ('value="cages"','value="pmm"','Donatı ve kapasite'):self.assertIn(value,ui)
        with self.get('/api/check-registry') as response:registry=json.load(response)
        self.assertEqual(registry['implemented_check_count'],16)


if __name__=='__main__':unittest.main()
