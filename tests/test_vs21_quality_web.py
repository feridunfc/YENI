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
from urllib.request import urlopen

from column_kinematics_fixture import KinematicsBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
from tbdy_next.column_quality_report import quality_html
from tbdy_next.web import make_handler


class QualityPage(HTMLParser):
    def __init__(self):super().__init__();self.open_details=0;self.scripts=0
    def handle_starttag(self,tag,attrs):
        if tag=='details' and 'open' in dict(attrs):self.open_details+=1
        if tag=='script':self.scripts+=1


class ColumnQualityWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name);cls.receipts=cls.root/'receipts'
        source=cls.root/'bank.zip';source.write_bytes(KinematicsBank().build())
        cls.run_id=save_column_bank(source,cls.receipts)['run_id']
        cls.paths=[cls.receipts/cls.run_id/f for f in ('input.source','column-bank.sqlite')]
        cls.hashes=[sha256(p.read_bytes()).hexdigest() for p in cls.paths]
        def forbidden(*args,**kwargs):raise AssertionError('Numerical reference must stay offline')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.receipts,live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1]);cls.query='run_id='+cls.run_id
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()
    def get(self,path):return urlopen(self.base+path,timeout=20)

    def test_http_quality_has_full_scope_and_paginated_comparisons(self):
        with self.get('/api/column-bank?'+self.query+'&view=pmm-quality') as response:r=json.load(response)
        q=r['column_pmm_quality']
        self.assertEqual((q['comparison_count'],r['demand_page']['total']),(6,6))
        self.assertEqual(q['source_pmm_result_sha256'],r['column_pmm']['result_sha256'])
        self.assertEqual(q['source_cages_result_sha256'],r['column_cages']['result_sha256'])
        self.assertEqual(len(q['reference_models']),3)
        page=read_column_bank(self.receipts,self.run_id,view='pmm-quality',limit=2,offset=2)['demand_page']
        self.assertEqual(page['rows'],q['rows'][2:4])

    def test_member_and_spectral_filters_remain_bound_and_empty_is_not_pass(self):
        with self.get('/api/column-bank?'+self.query+'&view=pmm-quality&member=C_SYNTHETIC_1&case=RS_SUM') as response:r=json.load(response)
        q=r['column_pmm_quality']
        self.assertEqual((q['comparison_count'],len(q['members'])),(0,3))
        self.assertEqual((q['member_id_filter'],q['output_case_filter']),('C_SYNTHETIC_1','RS_SUM'))
        self.assertTrue(all(not g['critical_comparisons_all_match'] for g in q['members']))
        self.assertEqual(r['demand_page']['rows'],[])

    def test_ordinary_views_do_not_invoke_reference_solver(self):
        with patch('tbdy_next.column_engine.demand_view._pmm_quality',side_effect=AssertionError('Unexpected reference solve')):
            for view in ('native','pmm','overview','shear'):
                result=read_column_bank(self.receipts,self.run_id,view=view)
                self.assertNotIn('column_pmm_quality',result)

    def test_full_export_preserves_precision_no_database_growth_and_cache_isolation(self):
        with self.get('/api/export-column-bank?'+self.query) as response:r=json.load(response)
        q=r['column_pmm_quality'];self.assertEqual(len(q['rows']),q['critical_target_count'])
        value=q['rows'][0]['reference_capacity_knm'];self.assertNotEqual(value,round(value,2))
        q['rows'][0]['reference_capacity_knm']=1
        fresh=read_column_bank(self.receipts,self.run_id,view='pmm-quality')['column_pmm_quality']
        self.assertEqual(fresh['rows'][0]['reference_capacity_knm'],value)
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in self.paths])

    def test_report_preserves_summary_and_discloses_numerical_scope_with_closed_details(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        self.assertLess(html.index('Kolon mühendislik özeti · VS20'),html.index('PMM bağımsız sayısal kıyas · VS21'))
        for phrase in ('Tolerans içinde','Bağımsız kapasite (kN·m)','PMM nüfusunun tamamı bağımsız doğrulanmış değildir',
                       'aynı malzeme modelini','Ana hesabın üç düzeydeki kapasite yayılımı bütçeye eklenmez'):
            self.assertIn(phrase,html)
        page=QualityPage();page.feed(html);self.assertEqual((page.open_details,page.scripts),(0,0))

    def test_html_escapes_source_labels_and_retains_mismatch_and_failure(self):
        q=read_column_bank(self.receipts,self.run_id,view='pmm-quality')['column_pmm_quality']
        q['rows'][0]['story']='<script>alert(1)</script>'
        q['rows'][0]['status']='NUMERICAL_COMPARISON_MISMATCH'
        q['rows'][1].update(status='REFERENCE_UNRESOLVED',reference_capacity_knm=None,reference_utilization=None)
        html=quality_html(q)
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)
        self.assertIn('Tolerans dışında',html);self.assertIn('Referans çözülemedi',html)

    def test_ui_location_and_cli_have_explicit_comparison_scope(self):
        with self.get('/') as response:html=response.read().decode()
        start=html.index('<optgroup label="Donatı ve kapasite">');end=html.index('</optgroup>',start)
        self.assertIn('value="pmm-quality"',html[start:end])
        before=sorted(p.name for p in self.receipts.iterdir());out=io.StringIO()
        with redirect_stdout(out):code=main(['inspect-column-demands','--out',str(self.receipts),'--run-id',self.run_id,'--quality'])
        self.assertEqual(code,0);q=json.loads(out.getvalue())['column_pmm_quality']
        self.assertTrue(q['critical_subset_only']);self.assertFalse(q['full_primary_population_independently_checked'])
        self.assertEqual(before,sorted(p.name for p in self.receipts.iterdir()))

    def test_vs25_full_json_exposes_resolved_planes_and_unchanged_source_vectors(self):
        with self.get('/api/export-column-bank?'+self.query) as response:r=json.load(response)
        p=r['column_pmm'];q=r['column_pmm_quality']
        self.assertEqual(p['schema'],'tbdy.next.column-pmm-scenarios.v3')
        self.assertEqual(q['schema'],'tbdy.next.column-pmm-numerical-reference.v2')
        self.assertEqual(q['source_pmm_result_sha256'],p['result_sha256'])
        for row in p['rows']:
            if row['utilization'] is None:continue
            root=row['refinement']['direction_root']
            self.assertAlmostEqual(root['target_n_n'],-row['native_values']['P']*1000,delta=1e-6)
            self.assertEqual(root['capacity_nmm']/1e6,row['radial_capacity_kNm'])
            self.assertLessEqual(root['direction_residual_nmm'],1000)
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in self.paths])

    def test_vs25_report_places_root_evidence_in_closed_details(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        self.assertIn('<details><summary>Kritik kayıtların denge noktaları ve yaklaşım farkları</summary>',html)
        self.assertIn('Basınç normali θ (°)',html)
        self.assertIn('M2·u3−M3·u2=0',html)
        self.assertNotIn('üç çözünürlükte bulunan en küçük radyal kapasiteye oranıdır',html)
        page=QualityPage();page.feed(html);self.assertEqual((page.open_details,page.scripts),(0,0))
