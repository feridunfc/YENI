"""VS13 filtered HTTP views and printed report on an unchanged offline bank."""
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from column_demand_fixture import DesignBank
from tbdy_next.column_engine.store import save_column_bank
from tbdy_next.web import make_handler


class PrecheckWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(); cls.root=Path(cls.temp.name)
        source=cls.root/'bank.zip'; source.write_bytes(DesignBank().build())
        cls.saved=save_column_bank(source,cls.root/'receipts')
        def forbidden(*args,**kwargs): raise AssertionError('Offline prechecks must not call ETABS')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.root/'receipts',live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.query=urlencode({'run_id':cls.saved['run_id']})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def get(self,path): return urlopen(self.base+path,timeout=10)

    def test_critical_view_keeps_entire_source_vector_and_full_export_population(self):
        with self.get('/api/column-bank?'+self.query+'&view=critical&member=C_SYNTHETIC_1&case=SUM') as response:
            data=json.load(response)
        self.assertEqual(data['critical_scope']['candidate_count'],4)
        self.assertFalse(data['critical_scope']['pmm_population_reduced'])
        self.assertEqual(data['demand_page']['total'],1)
        state=data['demand_page']['rows'][0]
        self.assertEqual((state['native_key']['ObjSta'],state['domain_values']['N_compression_kN']), (3.3,720))
        self.assertEqual(len(state['native_values']),6)
        with self.get('/api/export-column-bank?'+self.query) as response: full=json.load(response)
        self.assertEqual(len(full['demand_chain']['candidates']),8)
        self.assertEqual(len(full['column_prechecks']['critical_selection']['rows']),2)
        self.assertEqual(len(full['column_prechecks']['reinforcement_bounds']['source_comparisons']),8)

    def test_reinforcement_bound_is_member_specific_and_rejects_case_filter(self):
        with self.get('/api/column-bank?'+self.query+'&view=reinforcement&member=C_SYNTHETIC_2') as response:
            data=json.load(response)
        self.assertEqual(data['demand_page']['total'],1)
        row=data['demand_page']['rows'][0]
        self.assertEqual((row['minimum_as_cm2'],row['maximum_as_cm2']),('64','256'))
        self.assertIsNone(row['provided_as_cm2'])
        with self.assertRaises(HTTPError) as caught:
            self.get('/api/column-bank?'+self.query+'&view=reinforcement&case=SUM')
        self.assertEqual(caught.exception.code,400)

    def test_report_and_ui_present_area_scope_and_source_extrema_without_pmm_promotion(self):
        with self.get('/report/column-bank?'+self.query) as response: html=response.read().decode()
        for label in ('VS13','Kritik statik','7.3.2.1','6400','256','PMM için tam talep',
                      'bir kuvvet vektörü oluşturmaz','gerçek donatı kafesini','NOT_PROVEN','NUMERICAL_MATCH'):
            self.assertIn(label,html)
        self.assertNotIn('<script',html)
        with self.get('/') as response: page=response.read().decode()
        self.assertIn('value="critical"',page)
        self.assertIn('value="reinforcement"',page)
        with self.get('/api/check-registry') as response: registry=json.load(response)
        self.assertEqual(registry['implemented_check_count'],16,'Input bounds do not claim an extra complete normative CHECK')


if __name__=='__main__': unittest.main()
