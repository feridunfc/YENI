from contextlib import redirect_stdout
from hashlib import sha256
from http.server import ThreadingHTTPServer
from html.parser import HTMLParser
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import urlopen

from column_kinematics_fixture import KinematicsBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank, read_column_bank
from tbdy_next.web import make_handler


class FirstTable(HTMLParser):
    def __init__(self):
        super().__init__();self.table_count=0;self.row_count=0;self.text=[];self.open_details=0
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.table_count+=1
        if tag=='tr' and self.table_count==1:self.row_count+=1
        if tag=='details' and 'open' in dict(attrs):self.open_details+=1
    def handle_data(self,data):
        if self.table_count==1:self.text.append(data)


class ColumnOverviewWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name);cls.receipts=cls.root/'receipts'
        source=cls.root/'bank.zip';source.write_bytes(KinematicsBank().build())
        cls.run_id=save_column_bank(source,cls.receipts)['run_id']
        cls.source=cls.receipts/cls.run_id/'input.source';cls.db=cls.receipts/cls.run_id/'column-bank.sqlite'
        cls.hashes=[sha256(p.read_bytes()).hexdigest() for p in (cls.source,cls.db)]
        def forbidden(*args,**kwargs):raise AssertionError('Overview must stay offline')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.receipts,live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1]);cls.query=urlencode({'run_id':cls.run_id})
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()
    def get(self,path):return urlopen(self.base+path,timeout=20)

    def test_overview_pages_members_with_all_three_explicit_scenarios(self):
        with self.get('/api/column-bank?'+self.query+'&view=overview') as response:r=json.load(response)
        self.assertEqual(r['demand_page']['total'],2)
        self.assertEqual(r['column_overview']['member_count'],2)
        self.assertNotIn('rows',r['column_overview'])
        self.assertEqual(len(r['demand_page']['rows'][0]['scenarios']),3)
        one=read_column_bank(self.receipts,self.run_id,view='overview',offset=1,limit=1)
        self.assertEqual((one['demand_page']['total'],len(one['demand_page']['rows'])),(2,1))
        self.assertEqual(one['demand_page']['rows'][0]['member_id'],'C_SYNTHETIC_2')

    def test_member_and_spectral_filters_do_not_reuse_global_critical_values(self):
        with self.get('/api/column-bank?'+self.query+'&view=overview&member=C_SYNTHETIC_1&case=RS_SUM') as response:r=json.load(response)
        self.assertEqual(r['demand_page']['total'],1)
        self.assertEqual(r['column_overview']['output_case_filter'],'RS_SUM')
        self.assertEqual(r['column_overview']['static_state_count'],0)
        self.assertIsNone(r['demand_page']['rows'][0]['scenarios'][0]['pmm']['representative'])
        self.assertFalse(r['column_overview']['spectral_design_vectors_formed'])

    def test_html_starts_with_readable_summary_and_details_are_closed(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        self.assertLess(html.index('Kolon mühendislik özeti · VS20'),html.index('Kolon kuvvet bankası ve statik birleşim doğrulaması'))
        parsed=FirstTable();parsed.feed(html)
        self.assertEqual(parsed.row_count,3)  # header + one row per member
        self.assertEqual(parsed.open_details,0)
        main_text=' '.join(parsed.text)
        for text in ('N kaynak (kN)','M2 kaynak (kN·m)','Koşullu PMM','Ve bekleniyor','Girdiler bekleniyor'):
            self.assertIn(text,main_text)
        self.assertNotIn('source_row_id',main_text)
        self.assertIn('Tam hassasiyet, kaynak kimlikleri',html)
        self.assertNotIn('<script',html)

    def test_full_json_retains_original_calculations_without_database_growth(self):
        with self.get('/api/export-column-bank?'+self.query) as response:r=json.load(response)
        self.assertEqual((len(r['column_overview']['rows']),len(r['column_pmm']['rows']),len(r['column_shear']['rows'])),(2,24,48))
        self.assertEqual(r['column_overview']['source_pmm_result_sha256'],r['column_pmm']['result_sha256'])
        self.assertEqual(r['column_overview']['source_sensitivity_result_sha256'],r['column_sensitivity']['result_sha256'])
        self.assertFalse(r['column_overview']['automatic_design_selection'])
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in (self.source,self.db)])

    def test_native_navigation_stays_lazy_and_ui_summary_is_default(self):
        with patch('tbdy_next.column_engine.demand_view._pmm',side_effect=AssertionError('Unexpected PMM')):
            with self.get('/api/column-bank?'+self.query) as response:r=json.load(response)
            self.assertNotIn('column_overview',r)
        with self.get('/') as response:html=response.read().decode()
        self.assertIn('value="overview" selected',html)
        self.assertIn('id="columnProposal"',html)
        self.assertIn('id="columnOverviewDetails"',html)
        with self.get('/api/check-registry') as response:self.assertEqual(json.load(response)['implemented_check_count'],16)

    def test_cli_returns_overview_scope_without_new_receipt(self):
        before=sorted(p.name for p in self.receipts.iterdir());out=io.StringIO()
        with redirect_stdout(out):code=main(['inspect-column-demands','--out',str(self.receipts),'--run-id',self.run_id,'--overview'])
        self.assertEqual(code,0);r=json.loads(out.getvalue())['column_overview']
        self.assertEqual(r['member_count'],2);self.assertEqual(r['engineering_release'],'NOT_READY')
        self.assertEqual(before,sorted(p.name for p in self.receipts.iterdir()))
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in (self.source,self.db)])


if __name__=='__main__':unittest.main()
