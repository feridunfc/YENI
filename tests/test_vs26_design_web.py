from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from zipfile import ZipFile

from column_spectral_fixture import SpectralBank
from tbdy_next.cli import main
from tbdy_next.column_engine.demand_view import verified_spectral_design
from tbdy_next.column_engine.native_archive import digest
from tbdy_next.column_engine.spectral_projection import write_spectral_forensic
from tbdy_next.column_engine.store import save_column_bank, read_column_bank
from tbdy_next.spectral_design_report import build_spectral_design_html
from tbdy_next.web import make_handler


class SpectralDesignWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name);cls.receipts=cls.root/'receipts'
        source=cls.root/'source.zip';source.write_bytes(SpectralBank().build())
        cls.run_id=save_column_bank(source,cls.receipts)['run_id']
        cls.paths=[cls.receipts/cls.run_id/f for f in ('input.source','column-bank.sqlite')]
        cls.hashes=[sha256(p.read_bytes()).hexdigest() for p in cls.paths]
        def forbidden(*args,**kwargs):raise AssertionError('VS26 may not invoke live ETABS')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.receipts,live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()

    def query(self,**kwargs):return urlencode({'run_id':self.run_id,'view':'spectral-design',**kwargs})
    def get(self,path):return urlopen(self.base+path,timeout=40)

    def test_initial_summary_is_bounded_and_does_not_load_raw_or_unrelated_engines(self):
        with patch('tbdy_next.column_engine.demand_view._derive',side_effect=AssertionError('No SCWB/stability pipeline')):
            with self.get('/api/column-bank?'+self.query()) as response:raw=response.read();report=json.loads(raw)
        self.assertLess(len(raw),100_000)
        self.assertEqual(len(report['demand_page']['rows']),2)
        self.assertEqual(report['column_spectral_design']['candidate_count'],128)
        self.assertEqual(report['spectral_pmm']['assessment_count'],384)
        self.assertEqual(report['spectral_replay']['scalar_comparisons'],192)
        self.assertEqual({r['comparisons'] for r in report['spectral_replay']['component_differences']},{32})
        for key in ('force_states','force_page','column_pmm','scwb_scenarios','demand_chain','static_replay'):
            self.assertNotIn(key,report)
        for key in ('candidates','envelopes','static_load_definition_facts'):
            self.assertNotIn(key,report['column_spectral_design'])
        self.assertNotIn('rows',report['spectral_pmm'])

    def test_selected_cage_case_and_member_governing_are_from_filtered_population(self):
        r=read_column_bank(self.receipts,self.run_id,view='spectral-design',member_id='C_SYNTHETIC_1',
            output_case='RS_SUM',column_label='16Φ28')
        page=r['demand_page'];self.assertEqual(len(page['rows']),1)
        row=page['rows'][0];self.assertEqual(row['assessment_count'],32)
        self.assertEqual(row['reinforcement'],'16Φ28')
        self.assertEqual(row['governing_resolved']['combination'],'RS_SUM')
        self.assertEqual(r['column_spectral_design']['filtered_assessment_count'],32)
        self.assertFalse(row['continuous_axial_envelope_complete'])

    def test_candidate_page_has_exact_source_and_numeric_trace_without_full_population(self):
        r=read_column_bank(self.receipts,self.run_id,view='spectral-candidates',member_id='C_SYNTHETIC_1',
            output_case='RS_SUM',offset=2,limit=3)
        page=r['demand_page'];self.assertEqual((page['total'],len(page['rows'])),(32,3))
        for row in page['rows']:
            state=row['design_candidate'];trace=row['numerical_evidence']
            self.assertEqual(state['candidate_id'],row['candidate_id'])
            self.assertEqual(trace['N_N'],row['forces']['N_kN']*1000)
            self.assertEqual(trace['M2_Nmm'],row['forces']['M2_kNm']*1e6)
            self.assertEqual(digest(trace),row['numerical_evidence_id'])
            self.assertEqual(state['source_archive_sha256'],self.hashes[0])
            self.assertEqual(set(state['native_max_min_row_ids']),{'Max','Min'})
        original=page['rows'][0]['forces']['N_kN'];page['rows'][0]['forces']['N_kN']=99999
        fresh=read_column_bank(self.receipts,self.run_id,view='spectral-candidates',member_id='C_SYNTHETIC_1',output_case='RS_SUM',offset=2,limit=3)
        self.assertEqual(fresh['demand_page']['rows'][0]['forces']['N_kN'],original)

    def test_json_and_html_use_same_selected_page_and_no_scripts(self):
        query=self.query(view='spectral-candidates',member='C_SYNTHETIC_1',case='RS_SUM',offset=30,column_cage='16Φ32')
        with self.get('/api/column-bank?'+query) as response:shown=json.load(response)
        with self.get('/api/export-column-bank?'+query) as response:
            self.assertIn('spectral-candidates_page_30.json',response.headers['Content-Disposition'])
            exported=json.load(response)
        self.assertEqual(shown,exported);self.assertEqual(len(shown['demand_page']['rows']),2)
        with self.get('/report/column-bank?'+query) as response:
            html=response.read().decode();self.assertIn("default-src 'none'",response.headers['Content-Security-Policy'])
        self.assertEqual(html,build_spectral_design_html(shown))
        self.assertIn('Seçili sayfa: 31–32 / 32',html)
        self.assertIn('NOT_PROVEN / NOT_READY',html)
        self.assertNotIn('<script',html);self.assertNotIn('<details open',html)
        table=html[html.index('<table>'):html.index('</table>')]
        self.assertNotIn('source_row_id',table);self.assertEqual(table.count('<tr>'),3)

    def test_full_forensic_is_separate_deterministic_complete_and_hash_joined(self):
        with self.get('/api/export-spectral-design?'+urlencode({'run_id':self.run_id})) as response:
            raw=response.read();self.assertEqual(response.headers['Content-Type'],'application/zip')
        _,result=verified_spectral_design(self.receipts,self.run_id);repeat=io.BytesIO();write_spectral_forensic(result,repeat)
        self.assertEqual(raw,repeat.getvalue())
        with ZipFile(io.BytesIO(raw)) as archive:
            manifest=json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['scope'],'FULL_RECORDED_VS26_POPULATION_NO_FILTERS')
            self.assertEqual(manifest['source_archive_sha256'],self.hashes[0])
            self.assertEqual(manifest['files']['design-candidates.ndjson']['record_count'],128)
            self.assertEqual(manifest['files']['pmm-evaluations.ndjson']['record_count'],384)
            self.assertEqual(manifest['files']['physical-static-states.ndjson']['record_count'],8)
            for name,record in manifest['files'].items():
                data=archive.read(name);self.assertEqual(sha256(data).hexdigest(),record['sha256']);self.assertEqual(len(data),record['bytes'])
            candidates={r['candidate_id']:r for r in map(json.loads,archive.read('design-candidates.ndjson').splitlines())}
            evidence={r['evidence_id']:r for r in map(json.loads,archive.read('numerical-evidence.ndjson').splitlines())}
            for row in map(json.loads,archive.read('pmm-evaluations.ndjson').splitlines()):
                self.assertEqual(row['forces'],candidates[row['candidate_id']]['forces'])
                self.assertIn(row['numerical_evidence_id'],evidence)
        self.assertEqual(self.hashes,[sha256(p.read_bytes()).hexdigest() for p in self.paths])

    def test_forensic_does_not_silently_ignore_filters_and_sqlite_is_not_design_export(self):
        for path in ('/api/export-spectral-design?'+self.query(),
            '/api/export-spectral-design?'+urlencode({'run_id':self.run_id,'member':'C_SYNTHETIC_1'}),
            '/api/export-column-bank?'+self.query(format='sqlite'),
            '/api/column-bank?'+self.query(beam_diameter=20),
            '/report/column-bank?'+self.query(column_cage='16x24')):
            with self.subTest(path=path),self.assertRaises(HTTPError) as error:self.get(path)
            self.assertEqual(error.exception.code,400);error.exception.close()
        with self.assertRaisesRegex(ValueError,'PAGE_SCOPE'):
            read_column_bank(self.receipts,self.run_id,view='spectral-design',full=True)

    def test_cli_filtered_json_html_and_forensic_paths_preserve_existing_files(self):
        base=['inspect-spectral-design','--run-id',self.run_id,'--out',str(self.receipts)]
        params=['--member','C_SYNTHETIC_1','--case','RS_SUM','--cage','16Φ28','--candidates','--offset','31','--limit','1']
        out=io.StringIO()
        with redirect_stdout(out):self.assertEqual(main(base+params),0)
        shown=json.loads(out.getvalue());self.assertEqual(len(shown['demand_page']['rows']),1)
        target=self.root/'view.json';html=self.root/'view.html'
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(base+params+['--json',str(target)]),0)
            self.assertEqual(main(base+params+['--html',str(html)]),0)
            self.assertEqual(main(base+params+['--json',str(target)]),2)
        self.assertEqual(json.loads(target.read_text(encoding='utf-8')),shown)
        self.assertEqual(html.read_text(encoding='utf-8'),build_spectral_design_html(shown))
        target=self.root/'full.zip'
        with redirect_stdout(io.StringIO()):self.assertEqual(main(base+['--forensic',str(target)]),0)
        with ZipFile(target) as z:self.assertEqual(json.loads(z.read('manifest.json'))['source_archive_sha256'],self.hashes[0])

    def test_source_tampering_is_rejected_even_with_design_cache_warmed(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/'s.zip';source.write_bytes(SpectralBank().build())
            run=save_column_bank(source,root/'r')['run_id'];read_column_bank(root/'r',run,view='spectral-design')
            path=root/'r'/run/'input.source';path.write_bytes(path.read_bytes()+b'CHANGED')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_OR_DATABASE_CHANGED'):
                verified_spectral_design(root/'r',run)

    def test_unrelated_views_do_not_trigger_design_solve(self):
        with patch('tbdy_next.column_engine.demand_view._spectral_design',side_effect=AssertionError('unexpected design solve')):
            for view in ('native','static','spectral-envelopes'):
                self.assertNotIn('spectral_pmm',read_column_bank(self.receipts,self.run_id,view=view))

    def test_empty_scope_is_explicit_and_html_rejects_foreign_authority(self):
        r=read_column_bank(self.receipts,self.run_id,view='spectral-design',output_case='SUM')
        self.assertEqual(r['column_spectral_design']['filtered_assessment_count'],0)
        self.assertTrue(all(x['governing_resolved'] is None and not x['numerical_selection_complete'] for x in r['demand_page']['rows']))
        for key,value in (('physical_concurrency_proven',True),('source_archive_sha256','OTHER'),('continuous_axial_envelope_complete',True)):
            changed=deepcopy(r);changed['column_spectral_design'][key]=value
            with self.assertRaisesRegex(ValueError,'CONTRACT_INVALID'):build_spectral_design_html(changed)
        for key,value in (('source_manifest_sha256','0'*64),('normative_qualification','PROVEN'),('acceptance_eligible',True)):
            changed=deepcopy(r);changed['golden_regression_gate'][key]=value
            with self.assertRaisesRegex(ValueError,'CONTRACT_INVALID'):build_spectral_design_html(changed)
        r['demand_page']['rows'][0]['story']='<script>alert(1)</script>'
        html=build_spectral_design_html(r);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)


if __name__=='__main__':unittest.main()
