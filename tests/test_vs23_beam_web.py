from contextlib import redirect_stdout
from copy import deepcopy
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
from urllib.error import HTTPError
from urllib.request import urlopen

from beam_reference_fixture import BeamBank
from tbdy_next.beam_report import beam_html
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
from tbdy_next.web import make_handler


class BeamPage(HTMLParser):
    def __init__(self):super().__init__();self.open_details=0;self.scripts=0
    def handle_starttag(self,tag,attrs):
        if tag=='details' and 'open' in dict(attrs):self.open_details+=1
        if tag=='script':self.scripts+=1


class BeamWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name);cls.receipts=cls.root/'receipts'
        source=cls.root/'bank.zip';source.write_bytes(BeamBank().build())
        cls.run_id=save_column_bank(source,cls.receipts)['run_id']
        cls.paths=[cls.receipts/cls.run_id/f for f in ('input.source','column-bank.sqlite')]
        cls.hashes=[sha256(p.read_bytes()).hexdigest() for p in cls.paths]
        def forbidden(*args,**kwargs):raise AssertionError('Beam references must stay offline')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.receipts,live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1]);cls.query='run_id='+cls.run_id
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()
    def get(self,path):return urlopen(self.base+path,timeout=30)

    def test_http_retains_both_ends_and_paginates_without_losing_population(self):
        with self.get('/api/column-bank?'+self.query+'&view=beam-cages&offset=2') as response:r=json.load(response)
        b=r['beam_end_references'];page=r['demand_page']
        self.assertEqual((b['target_beam_count'],b['expected_end_count'],b['expected_incident_end_count']),(4,8,4))
        self.assertEqual((b['filtered_end_count'],b['calculated_candidate_count'],page['total']),(8,24,8))
        self.assertEqual(page['rows'],b['rows'][2:])
        limited=read_column_bank(self.receipts,self.run_id,view='beam-cages',limit=2,offset=2)['demand_page']
        self.assertEqual(limited['rows'],b['rows'][2:4])
        self.assertEqual(b['source_joints_result_sha256'],r['column_joints']['result_sha256'])

    def test_column_filter_retains_incident_beams_and_both_column_identities(self):
        with self.get('/api/column-bank?'+self.query+'&view=beam-cages&member=C_SYNTHETIC_1') as response:r=json.load(response)
        b=r['beam_end_references'];self.assertEqual((b['expected_end_count'],b['filtered_end_count']),(8,4))
        self.assertEqual({row['member_id'] for row in b['rows']},{'BX+','BX-','BY+','BY-'})
        self.assertTrue(all(row['incident_to_column_joint'] and 'C_SYNTHETIC_2' in row['adjacent_column_ids'] for row in b['rows']))

    def test_case_filter_cannot_misrepresent_independent_area_envelopes(self):
        with self.assertRaises(HTTPError) as caught:
            self.get('/api/column-bank?'+self.query+'&view=beam-cages&case=SUM')
        self.assertEqual(caught.exception.code,400)
        caught.exception.close()
        with self.assertRaises(ValueError):read_column_bank(self.receipts,self.run_id,view='beam-cages',output_case='SUM')

    def test_ordinary_views_do_not_invoke_beam_capacity_solver(self):
        with patch('tbdy_next.column_engine.demand_view._beam_references',side_effect=AssertionError('Unexpected beam solve')):
            for view in ('native','pmm','overview','shear','scwb'):
                self.assertNotIn('beam_end_references',read_column_bank(self.receipts,self.run_id,view=view))

    def test_export_precision_cache_isolation_scwb_identity_and_unchanged_source_files(self):
        prior=read_column_bank(self.receipts,self.run_id,view='scwb')['column_scwb']['result_sha256']
        with self.get('/api/export-column-bank?'+self.query) as response:r=json.load(response)
        b=r['beam_end_references'];self.assertEqual(len(b['rows']),8)
        self.assertEqual(sum(len(row['candidates']) for row in b['rows']),24)
        c=b['rows'][0]['candidates'][0];value=c['capacity']['negative_m3_knm']
        self.assertLess(value,0);self.assertNotEqual(value,round(value,2))
        self.assertIsNone(b['scwb_ratio']);self.assertFalse(b['actual_or_selected_beam_capacity_bound'])
        c['capacity']['negative_m3_knm']=1
        fresh=read_column_bank(self.receipts,self.run_id,view='beam-cages')['beam_end_references']
        self.assertEqual(fresh['rows'][0]['candidates'][0]['capacity']['negative_m3_knm'],value)
        self.assertEqual(prior,r['column_scwb']['result_sha256'])
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in self.paths])

    def test_report_has_complete_compact_end_table_and_closed_source_details(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        self.assertLess(html.index('Kolon mühendislik özeti · VS20'),html.index('Kiriş uç donatısı ve kapasitesi · VS23'))
        for phrase in ('8/8 kaynak ucu','24/24 donatı/kapasite senaryosu','N=0 saf eğilme',
                       'Gerekli As, uygulanmış donatı değildir','ağırlık merkezine kadardır','SCWB oranı üretilmez'):
            self.assertIn(phrase,html)
        section=html[html.index('<section class="beam-references">'):]
        first=section[section.index('<table>'):section.index('</table>')]
        self.assertEqual(first.count('<tr>'),9);self.assertIn('Φ20',first)
        self.assertNotIn('source_row_id',first);self.assertNotIn('native_cut_keys',first)
        page=BeamPage();page.feed(html);self.assertEqual((page.open_details,page.scripts),(0,0))

    def test_html_escapes_source_labels_and_retains_ambiguous_end(self):
        f=BeamBank();duplicate=deepcopy(f.beam_rows[0]);duplicate['totTopRebar']='.1';f.beam_rows.append(duplicate)
        source=self.root/'ambiguous.zip';source.write_bytes(f.build());run=save_column_bank(source,self.receipts)['run_id']
        with self.get('/api/column-bank?view=beam-cages&run_id='+run) as response:r=json.load(response)
        b=r['beam_end_references'];self.assertEqual((b['source_bound_end_count'],b['calculated_candidate_count']),(7,21))
        blocked=next(row for row in b['rows'] if row['reason'])
        self.assertEqual(blocked['source']['design_match_count'],2)
        self.assertTrue(all(c['capacity'] is None for c in blocked['candidates']))
        blocked['member_id']='<script>alert(1)</script>';html=beam_html(b)
        self.assertIn('BEAM_DESIGN_STATION_AMBIGUOUS',html)
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)

    def test_ui_group_and_cli_beams_alone_or_with_scwb_keep_authority_denied(self):
        with self.get('/') as response:html=response.read().decode()
        start=html.index('<optgroup label="Kolon–kiriş birleşimleri">');end=html.index('</optgroup>',start)
        self.assertIn('value="beam-cages"',html[start:end]);self.assertIn('id="columnBeamProposal"',html)
        before=sorted(p.name for p in self.receipts.iterdir())
        for flags in (['--beams'],['--beams','--scwb']):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['inspect-column-demands','--out',str(self.receipts),'--run-id',self.run_id,*flags])
            self.assertEqual(code,0);r=json.loads(out.getvalue());b=r['beam_end_references']
            self.assertEqual(b['design_demand_authority'],'DENIED');self.assertEqual(b['formal_compliance'],'NOT_PROVEN')
            self.assertEqual(len(b['rows']),8);self.assertIsNone(b['selected_design'])
            self.assertEqual('column_scwb' in r,'--scwb' in flags)
        self.assertEqual(before,sorted(p.name for p in self.receipts.iterdir()))

    def test_missing_graph_keeps_known_columns_and_unknown_beam_population(self):
        f=BeamBank();f.calls.pop(('PointObj.GetCoordCartesian','point','PX+'))
        source=self.root/'blocked.zip';source.write_bytes(f.build());run=save_column_bank(source,self.receipts)['run_id']
        with self.get('/api/column-bank?view=beam-cages&run_id='+run) as response:r=json.load(response)
        b=r['beam_end_references'];self.assertEqual(b['known_column_count'],2)
        self.assertIsNone(b['target_beam_count']);self.assertIsNone(b['expected_end_count'])
        self.assertEqual(r['demand_page']['rows'],[])
        html=beam_html(b);self.assertIn('2 bilinen kolon korunur',html);self.assertIn('kiriş/uç sayısı bilinmiyor',html)
