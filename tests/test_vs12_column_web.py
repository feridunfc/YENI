"""HTTP and report acceptance for derived demands on an existing sealed bank."""
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


class DemandWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(); cls.root=Path(cls.temp.name)
        source=cls.root/'source.zip'; source.write_bytes(DesignBank().build())
        cls.saved=save_column_bank(source,cls.root/'receipts')
        def forbidden(*args,**kwargs): raise AssertionError('CE-02 is offline')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.root/'receipts',live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.query=urlencode({'run_id':cls.saved['run_id']})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def get(self,path): return urlopen(self.base+path,timeout=10)

    def test_static_and_design_views_filter_the_same_source(self):
        with self.get('/api/column-bank?'+self.query+'&view=static&member=C_SYNTHETIC_1&case=SUM') as response:
            static=json.load(response)
        with self.get('/api/column-bank?'+self.query+'&view=design&member=C_SYNTHETIC_1') as response:
            design=json.load(response)
        self.assertEqual(static['demand_page']['total'],4)
        self.assertEqual(static['demand_page']['rows'][0]['domain_values']['M2_kNcm'],4800)
        self.assertEqual(design['demand_page']['total'],4)
        self.assertIsNone(design['demand_page']['rows'][0]['native_design_row']['PMMRatio'])
        self.assertEqual(static['demand_chain']['result_sha256'],design['demand_chain']['result_sha256'])
        self.assertEqual(static['demand_chain']['source_run_id'],self.saved['run_id'])

    def test_html_and_json_explain_units_and_keep_unresolved_native_identity(self):
        with self.get('/api/export-column-bank?'+self.query) as response: data=json.load(response)
        with self.get('/report/column-bank?'+self.query) as response: html=response.read().decode()
        chain=data['demand_chain']
        self.assertEqual(len(chain['candidates']),8)
        self.assertEqual(len(chain['design_summary']['rows']),8)
        for value in ('CE-02','8 doğrulanmış statik kaynak adayı','24 PMM/VMaj/VMin','kN·cm',
                      'PMMRatio','NOT_PROVEN','çift istasyon','yuvarlanmaz',chain['result_sha256']):
            self.assertIn(value,html)
        self.assertNotIn('<script',html)

    def test_invalid_view_and_duplicate_parameter_are_rejected(self):
        for tail in ('&view=capacity','&view=static&view=design'):
            with self.assertRaises(HTTPError) as caught:
                self.get('/api/column-bank?'+self.query+tail)
            self.assertEqual(caught.exception.code,400)


if __name__=='__main__': unittest.main()
