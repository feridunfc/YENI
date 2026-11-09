from contextlib import redirect_stdout
from hashlib import sha256
from http.server import ThreadingHTTPServer
from html.parser import HTMLParser
import io,json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

from scwb_scenario_fixture import ScenarioBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
from tbdy_next.scenario_report import scenario_html
from tbdy_next.web import make_handler


class ScenarioPage(HTMLParser):
    def __init__(self):super().__init__();self.open_details=0;self.scripts=0
    def handle_starttag(self,tag,attrs):
        if tag=='details' and 'open' in dict(attrs):self.open_details+=1
        if tag=='script':self.scripts+=1


class ScenarioWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name);cls.receipts=cls.root/'receipts'
        source=cls.root/'bank.zip';source.write_bytes(ScenarioBank().build())
        cls.run_id=save_column_bank(source,cls.receipts)['run_id']
        cls.paths=[cls.receipts/cls.run_id/f for f in ('input.source','column-bank.sqlite')]
        cls.hashes=[sha256(p.read_bytes()).hexdigest() for p in cls.paths]
        def forbidden(*args,**kwargs):raise AssertionError('SCWB proposal comparison must stay offline')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.receipts,live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1]);cls.query='run_id='+cls.run_id
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()
    def get(self,path):return urlopen(self.base+path,timeout=30)

    def test_http_default_proposal_filters_before_pagination(self):
        with self.get('/api/column-bank?'+self.query+'&view=scwb-scenarios&offset=2') as response:r=json.load(response)
        s=r['scwb_scenarios'];self.assertEqual((s['display_column_label'],s['display_beam_diameter_mm']),('16Φ24',20))
        self.assertEqual((s['expected_case_count'],s['filtered_case_count'],s['filtered_summary_count']),(108,12,6))
        self.assertEqual(r['demand_page']['rows'],s['summaries'][2:]);self.assertNotIn('rows',s)
        small=read_column_bank(self.receipts,self.run_id,view='scwb-scenarios',limit=2,offset=2)['demand_page']
        self.assertEqual(small['rows'],s['summaries'][2:4])

    def test_explicit_scenario_and_column_filter_keep_neighbours(self):
        query='&view=scwb-scenarios&member=C_SYNTHETIC_1&column_cage='+quote('16Φ28')+'&beam_diameter=24'
        with self.get('/api/column-bank?'+self.query+query) as response:r=json.load(response)
        s=r['scwb_scenarios'];self.assertEqual((s['filtered_joint_node_count'],s['filtered_summary_count']),(2,4))
        self.assertTrue(all(x['column_label']=='16Φ28' and x['beam_diameter_mm']==24 for x in s['summaries']))
        self.assertTrue(all('C_SYNTHETIC_2' in x['column_ids'] for x in s['summaries'] if x['joint_id']=='P1'))
        self.assertEqual({b['member_id'] for b in s['beam_references']},{'BX+','BX-','BY+','BY-'})

    def test_spectral_filter_never_reuses_static_minimum(self):
        with self.get('/api/column-bank?'+self.query+'&view=scwb-scenarios&case=RS_SUM') as response:r=json.load(response)
        s=r['scwb_scenarios'];self.assertEqual(s['filtered_case_count'],0)
        self.assertTrue(all(row['status']=='NO_STATIC_SOURCE_CASES' and row['minimum_normalized_scenario_ratio'] is None for row in r['demand_page']['rows']))

    def test_unknown_or_misapplied_scenario_filters_are_rejected(self):
        for query in ('&view=scwb-scenarios&column_cage=FAKE','&view=scwb-scenarios&beam_diameter=32',
                      '&view=scwb-scenarios&beam_diameter=20.0','&view=scwb&beam_diameter=20','&view=beam-cages&column_cage=16x24'):
            with self.subTest(query=query),self.assertRaises(HTTPError) as caught:self.get('/api/column-bank?'+self.query+query)
            self.assertEqual(caught.exception.code,400);caught.exception.close()
        with self.assertRaises(ValueError):read_column_bank(self.receipts,self.run_id,view='scwb-scenarios',beam_diameter=True)

    def test_ordinary_views_do_not_compute_joint_scenarios(self):
        with patch('tbdy_next.column_engine.demand_view._scwb_scenarios',side_effect=AssertionError('Unexpected scenario calculation')):
            for view in ('native','overview','pmm','shear','scwb','beam-cages'):
                self.assertNotIn('scwb_scenarios',read_column_bank(self.receipts,self.run_id,view=view))

    def test_json_full_nine_scenarios_precision_source_hashes_and_cache_isolation(self):
        prior=read_column_bank(self.receipts,self.run_id,view='scwb')['column_scwb']['result_sha256']
        beam=read_column_bank(self.receipts,self.run_id,view='beam-cages')['beam_end_references']['result_sha256']
        with self.get('/api/export-column-bank?'+self.query) as response:r=json.load(response)
        s=r['scwb_scenarios'];self.assertEqual((len(s['rows']),len(s['summaries'])),(108,54))
        self.assertEqual((s['source_scwb_result_sha256'],s['source_beam_result_sha256']),(prior,beam))
        row=next(x for x in s['rows'] if x['normalized_scenario_ratio'] is not None);value=row['normalized_scenario_ratio']
        self.assertNotEqual(value,round(value,3));row['normalized_scenario_ratio']=0
        fresh=read_column_bank(self.receipts,self.run_id,full=True)['scwb_scenarios']
        self.assertEqual(next(x for x in fresh['rows'] if x['result_id']==row['result_id'])['normalized_scenario_ratio'],value)
        self.assertTrue(all(x['scwb_ratio'] is None for x in fresh['rows']))
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in self.paths])

    def test_html_has_all_nine_options_compact_first_table_and_closed_details(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        self.assertLess(html.index('Kolon mühendislik özeti · VS20'),html.index('SCWB öneri senaryoları · VS24'))
        for phrase in ('kolon kaynak N','kiriş N=0','senaryo referansı ≥1','minimum verilmez','nihai SCWB oranı üretilmez'):
            self.assertIn(phrase,html)
        section=html[html.index('<section class="scwb-scenarios">'):]
        first=section[section.index('<table>'):section.index('</table>')];self.assertEqual(first.count('<tr>'),7)
        self.assertNotIn('source_row_id',first);self.assertNotIn('result_id',first)
        self.assertIn('Kolon 16Φ24 / kiriş Φ20',html);self.assertIn('Kolon 16Φ32 / kiriş Φ24',html)
        page=ScenarioPage();page.feed(html);self.assertEqual((page.open_details,page.scripts),(0,0))

    def test_html_escapes_labels_and_keeps_blocked_population(self):
        s=read_column_bank(self.receipts,self.run_id,view='pmm-quality')['scwb_scenarios']
        s['summaries'][0]['joint_id']='<script>alert(1)</script>';html=scenario_html(s)
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)
        f=ScenarioBank();f.calls.pop(('PointObj.GetCoordCartesian','point','PX+'))
        source=self.root/'blocked.zip';source.write_bytes(f.build());run=save_column_bank(source,self.receipts)['run_id']
        with self.get('/api/column-bank?view=scwb-scenarios&run_id='+run) as response:r=json.load(response)
        s=r['scwb_scenarios'];self.assertIsNone(s['expected_case_count']);self.assertEqual(s['expected_column_end_count'],4)
        self.assertIn('2 bilinen kolon / 4 beklenen kolon ucu',scenario_html(s))

    def test_ui_group_cli_display_choices_and_combined_beam_export(self):
        with self.get('/') as response:html=response.read().decode()
        start=html.index('<optgroup label="Kolon–kiriş birleşimleri">');end=html.index('</optgroup>',start)
        self.assertIn('value="scwb-scenarios"',html[start:end]);before=sorted(p.name for p in self.receipts.iterdir())
        for flags in ([],['--beams'],['--column-cage','16Φ28','--beam-diameter','24']):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['inspect-column-demands','--out',str(self.receipts),'--run-id',self.run_id,'--scwb-scenarios',*flags])
            self.assertEqual(code,0);r=json.loads(out.getvalue());s=r['scwb_scenarios']
            expected=('16Φ28',24) if '--column-cage' in flags else ('16Φ24',20)
            self.assertEqual((s['display_column_label'],s['display_beam_diameter_mm']),expected)
            self.assertEqual(s['filtered_summary_count'],6);self.assertEqual(s['formal_compliance'],'NOT_PROVEN')
            if '--beams' in flags:self.assertEqual(len(r['beam_end_references']['rows']),8)
        self.assertEqual(before,sorted(p.name for p in self.receipts.iterdir()))
