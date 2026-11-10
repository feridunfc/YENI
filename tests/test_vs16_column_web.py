from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from column_stability_fixture import StiffnessBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank
from tbdy_next.web import make_handler


class ColumnTransverseWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name)
        source=cls.root/'bank.zip';source.write_bytes(StiffnessBank().build())
        saved=save_column_bank(source,cls.root/'receipts');cls.run_id=saved['run_id']
        def forbidden(*args,**kwargs):raise AssertionError('Offline shear must not call ETABS')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.root/'receipts',live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.query=urlencode({'run_id':cls.run_id})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()

    def get(self,path):return urlopen(self.base+path,timeout=15)

    def test_transverse_view_preserves_distinct_confinement_material_and_rejects_case_filter(self):
        with self.get('/api/column-bank?'+self.query+'&view=transverse&member=C_SYNTHETIC_1') as response:report=json.load(response)
        self.assertEqual(report['demand_page']['total'],6)
        self.assertEqual(report['column_transverse']['profiles'][0]['observed_fywk_mpa'],420)
        self.assertIsNone(report['column_transverse']['selected_design'])
        self.assertNotIn('column_pmm',report);self.assertNotIn('column_shear',report)
        with self.assertRaises(HTTPError) as caught:self.get('/api/column-bank?'+self.query+'&view=transverse&case=SUM')
        self.assertEqual(caught.exception.code,400)

    def test_shear_filter_and_full_export_bind_same_source_and_keep_ve_unknown(self):
        with self.get('/api/column-bank?'+self.query+'&view=shear&member=C_SYNTHETIC_2&case=SUM') as response:report=json.load(response)
        self.assertEqual(report['demand_page']['total'],24)
        self.assertNotIn('rows',report['column_shear']);self.assertNotIn('column_pmm',report)
        self.assertTrue(all(r['member_id']=='C_SYNTHETIC_2' for r in report['demand_page']['rows']))
        with self.get('/api/export-column-bank?'+self.query) as response:full=json.load(response)
        self.assertEqual(len(full['column_shear']['rows']),48)
        self.assertEqual(len(full['column_pmm']['rows']),24)
        self.assertEqual(full['column_shear']['source_cages_result_sha256'],full['column_cages']['result_sha256'])
        self.assertEqual(full['column_shear']['source_transverse_result_sha256'],full['column_transverse']['result_sha256'])
        self.assertEqual(full['column_shear']['ve_status'],'NOT_PROVEN')
        self.assertIsNone(full['column_shear']['vc_zero_gate']['required'])

    def test_report_draws_only_proposed_axes_and_keeps_check_count_and_scope(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        for value in ('VS16','Φ12/100','Koşullu kesme','Ack dıştan dışa','Vc=0','Ve=NOT_PROVEN',
                      'TIE_STEEL_SYNTHETIC','kanca ve düşey yerleşim doğrulanmadı','NOT_READY'):
            self.assertIn(value,html)
        self.assertEqual(html.count('<circle '),48)
        self.assertEqual(html.count('<line '),30)
        self.assertNotIn('<script',html)
        with self.get('/') as response:ui=response.read().decode()
        for value in ('value="transverse"','value="shear"','Kesme ve sargı'):self.assertIn(value,ui)
        with self.get('/api/check-registry') as response:registry=json.load(response)
        self.assertEqual(registry['implemented_check_count'],16)

    def test_cli_shear_switch_does_not_require_pmm_or_new_import(self):
        output=io.StringIO()
        with redirect_stdout(output):status=main(['inspect-column-demands','--out',str(self.root/'receipts'),'--run-id',self.run_id,'--shear'])
        self.assertEqual(status,0);result=json.loads(output.getvalue())
        self.assertEqual(result['column_shear']['assessment_count'],48)
        self.assertEqual(result['column_shear']['ve_status'],'NOT_PROVEN')
        self.assertNotIn('column_pmm',result)
        self.assertIsNone(result['column_transverse']['selected_design'])


if __name__=='__main__':unittest.main()
