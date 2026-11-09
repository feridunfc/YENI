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
from tbdy_next.scwb_report import scwb_html
from tbdy_next.web import make_handler


class ScwbPage(HTMLParser):
    def __init__(self):super().__init__();self.open_details=0;self.scripts=0
    def handle_starttag(self,tag,attrs):
        if tag=='details' and 'open' in dict(attrs):self.open_details+=1
        if tag=='script':self.scripts+=1


class ColumnScwbWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name);cls.receipts=cls.root/'receipts'
        source=cls.root/'bank.zip';source.write_bytes(KinematicsBank().build())
        cls.run_id=save_column_bank(source,cls.receipts)['run_id']
        cls.paths=[cls.receipts/cls.run_id/f for f in ('input.source','column-bank.sqlite')]
        cls.hashes=[sha256(p.read_bytes()).hexdigest() for p in cls.paths]
        def forbidden(*args,**kwargs):raise AssertionError('SCWB adaptation must stay offline')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.receipts,live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1]);cls.query='run_id='+cls.run_id
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()
    def get(self,path):return urlopen(self.base+path,timeout=20)

    def test_http_has_complete_joint_scope_and_paginates_summaries(self):
        with self.get('/api/column-bank?'+self.query+'&view=scwb') as response:r=json.load(response)
        s=r['column_scwb'];self.assertEqual((s['joint_node_count'],s['joint_case_count'],r['demand_page']['total']),(3,36,36))
        self.assertEqual(s['source_joints_result_sha256'],r['column_joints']['result_sha256'])
        self.assertEqual(s['source_kinematics_result_sha256'],r['column_kinematics']['result_sha256'])
        self.assertNotIn('column_references',s)
        page=read_column_bank(self.receipts,self.run_id,view='scwb',limit=2,offset=2)['demand_page']
        self.assertEqual(page['rows'],s['summaries'][2:4])

    def test_member_filter_preserves_other_column_and_beams(self):
        with self.get('/api/column-bank?'+self.query+'&view=scwb&member=C_SYNTHETIC_1') as response:r=json.load(response)
        s=r['column_scwb'];self.assertEqual((s['filtered_joint_node_count'],s['filtered_joint_case_count']),(2,24))
        self.assertTrue(s['neighbouring_participants_retained'])
        self.assertEqual({c['member_id'] for c in s['column_references']},{'C_SYNTHETIC_1','C_SYNTHETIC_2'})
        self.assertEqual({b['member_id'] for b in s['beam_sources']},{'BX+','BX-','BY+','BY-'})

    def test_spectral_case_does_not_reuse_unfiltered_minimum_or_claim_pass(self):
        with self.get('/api/column-bank?'+self.query+'&view=scwb&member=C_SYNTHETIC_1&case=RS_SUM') as response:r=json.load(response)
        s=r['column_scwb'];self.assertEqual(s['column_references'],[])
        self.assertEqual(s['filtered_joint_case_count'],0)
        self.assertTrue(all(row['sampled_minimum_column_sum_knm'] is None and row['scwb_ratio'] is None and
            row['status']=='NO_STATIC_SOURCE_CASES' for row in r['demand_page']['rows']))

    def test_ordinary_views_do_not_invoke_scwb_solver(self):
        with patch('tbdy_next.column_engine.demand_view._scwb',side_effect=AssertionError('Unexpected SCWB solve')):
            for view in ('native','pmm','overview','shear'):
                self.assertNotIn('column_scwb',read_column_bank(self.receipts,self.run_id,view=view))

    def test_export_keeps_precision_and_no_database_growth_or_cache_mutation(self):
        with self.get('/api/export-column-bank?'+self.query) as response:r=json.load(response)
        s=r['column_scwb'];self.assertEqual(len(s['rows']),s['expected_joint_case_count'])
        self.assertEqual(len(s['column_references']),24)
        self.assertTrue(all(row['scwb_ratio'] is None for row in s['rows']))
        value=s['column_references'][0]['capacity_knm'];self.assertNotEqual(value,round(value,2))
        s['column_references'][0]['capacity_knm']=1
        fresh=read_column_bank(self.receipts,self.run_id,view='scwb',member_id='C_SYNTHETIC_1')['column_scwb']
        self.assertEqual(fresh['column_references'][0]['capacity_knm'],value)
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in self.paths])

    def test_report_shows_column_reference_and_beam_gap_with_closed_details(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        self.assertLess(html.index('Kolon mühendislik özeti · VS20'),html.index('Güçlü kolon–zayıf kiriş · VS22'))
        for phrase in ('Kiriş uç donatısı bekleniyor','En küçük ΣMrc kaynak (kN·m)','deprem yönüyle uyumlu Nd minimumu değildir',
                       'Sıfır override sıfır donatı sayılmaz','Çatı veya düşük eksenel kuvvet istisnası uygulanmadı'):
            self.assertIn(phrase,html)
        section=html[html.index('<section class="column-scwb">'):]
        first=section[section.index('<table>'):section.index('</table>')]
        self.assertEqual(first.count('<tr>'),13)
        self.assertNotIn('source_state',first);self.assertNotIn('reference_id',first)
        page=ScwbPage();page.feed(html);self.assertEqual((page.open_details,page.scripts),(0,0))

    def test_html_escapes_labels_and_retains_missing_topology(self):
        s=read_column_bank(self.receipts,self.run_id,view='scwb',member_id='C_SYNTHETIC_1')['column_scwb']
        s['summaries'][0].update(joint_id='<script>alert(1)</script>',status='TOPOLOGY_UNRESOLVED',sampled_minimum_column_sum_knm=None)
        html=scwb_html(s);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)
        self.assertIn('Bağlantı geometrisi belirsiz',html)

    def test_ui_location_and_cli_are_offline_and_conditional(self):
        with self.get('/') as response:html=response.read().decode()
        start=html.index('<optgroup label="Kolon–kiriş birleşimleri">');end=html.index('</optgroup>',start)
        self.assertIn('value="scwb"',html[start:end])
        before=sorted(p.name for p in self.receipts.iterdir());out=io.StringIO()
        with redirect_stdout(out):code=main(['inspect-column-demands','--out',str(self.receipts),'--run-id',self.run_id,'--scwb'])
        self.assertEqual(code,0);s=json.loads(out.getvalue())['column_scwb']
        self.assertEqual(s['design_demand_authority'],'DENIED');self.assertFalse(s['required_beam_steel_used_as_capacity'])
        self.assertEqual(before,sorted(p.name for p in self.receipts.iterdir()))

    def test_blocked_graph_retains_expected_population_in_http_and_html(self):
        fixture=KinematicsBank();fixture.calls.pop(('PointObj.GetCoordCartesian','point','PX+'))
        source=self.root/'blocked.zip';source.write_bytes(fixture.build())
        run_id=save_column_bank(source,self.receipts)['run_id']
        with self.get('/api/column-bank?view=scwb&run_id='+run_id) as response:r=json.load(response)
        s=r['column_scwb'];self.assertEqual((s['selected_column_count'],s['expected_column_end_count']),(2,4))
        self.assertIsNone(s['filtered_joint_node_count']);self.assertIsNone(s['expected_joint_case_count'])
        html=scwb_html(s);self.assertIn('Birleşim sayısı bilinmiyor',html)
        self.assertIn('2 bilinen kolon / 4 beklenen uç / 24 beklenen kapasite kaydı',html)
        self.assertIn('C_SYNTHETIC_1',html);self.assertIn('C_SYNTHETIC_2',html)
