from contextlib import redirect_stdout
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

from column_joint_fixture import JointBank
from tbdy_next.cli import main
from tbdy_next.column_engine.store import save_column_bank
from tbdy_next.web import make_handler


class ColumnJointWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name)
        source=cls.root/'bank.zip';source.write_bytes(JointBank().build())
        saved=save_column_bank(source,cls.root/'receipts');cls.run_id=saved['run_id']
        def forbidden(*args,**kwargs):raise AssertionError('Offline joint references must not call ETABS')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.root/'receipts',live_capture=forbidden))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.query=urlencode({'run_id':cls.run_id})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temp.cleanup()

    def get(self,path):return urlopen(self.base+path,timeout=15)

    def test_joint_views_are_filtered_without_load_case_or_pmm_authority(self):
        with patch('tbdy_next.column_engine.demand_view._pmm',side_effect=AssertionError('Unexpected PMM')):
            with self.get('/api/column-bank?'+self.query+'&view=joints&member=C_SYNTHETIC_2') as response:r=json.load(response)
            self.assertEqual(r['demand_page']['total'],2)
            self.assertEqual(r['column_joints']['graph']['status'],'NATIVE_ENDPOINT_GRAPH_BOUND')
            self.assertNotIn('column_pmm',r);self.assertNotIn('column_shear',r)
            with self.get('/api/column-bank?'+self.query+'&view=joint-ties&member=C_SYNTHETIC_2') as response:r=json.load(response)
            self.assertEqual(r['demand_page']['total'],7)
        for view in ('joints','joint-ties'):
            with self.assertRaises(HTTPError) as caught:self.get('/api/column-bank?'+self.query+'&view='+view+'&case=SUM')
            self.assertEqual(caught.exception.code,400)

    def test_full_export_preserves_graph_proofs_and_original_sqlite_bytes(self):
        db=self.root/'receipts'/self.run_id/'column-bank.sqlite';before=sha256(db.read_bytes()).hexdigest()
        with self.get('/api/export-column-bank?'+self.query) as response:full=json.load(response)
        joints=full['column_joints']
        self.assertEqual(len(joints['graph']['frames']),6);self.assertEqual(len(joints['graph']['points']),7)
        self.assertEqual(len(joints['rows']),4)
        for field,source in [('source_bank_result_sha256',full),('source_cages_result_sha256',full['column_cages']),
                             ('source_transverse_result_sha256',full['column_transverse'])]:
            self.assertEqual(joints[field],source['result_sha256'])
        self.assertFalse(joints['physical_geometry_proven']);self.assertEqual(joints['ve_status'],'NOT_PROVEN')
        self.assertEqual(before,sha256(db.read_bytes()).hexdigest())

    def test_html_and_ui_distinguish_joint_geometry_from_actual_design(self):
        with self.get('/report/column-bank?'+self.query) as response:html=response.read().decode()
        for value in ('VS17','Kolon–kiriş birleşim referansları','Denk. 7.1 tabanı','≥ ilgili kolon eninin %75',
                      'Ve ve SCWB: NOT_PROVEN','BX+','Ash yüksek N (mm²)'):
            self.assertIn(value,html)
        self.assertNotIn('<script',html)
        with self.get('/') as response:ui=response.read().decode()
        self.assertIn('label="Kolon–kiriş birleşimleri"',ui)
        self.assertIn('value="joints"',ui);self.assertIn('value="joint-ties"',ui)
        with self.get('/api/check-registry') as response:r=json.load(response)
        self.assertEqual(r['implemented_check_count'],16)

    def test_cli_joint_summary_runs_on_existing_receipt_without_pmm_or_import(self):
        output=io.StringIO()
        with patch('tbdy_next.column_engine.demand_view._pmm',side_effect=AssertionError('Unexpected PMM')), redirect_stdout(output):
            status=main(['inspect-column-demands','--out',str(self.root/'receipts'),'--run-id',self.run_id,'--joints'])
        self.assertEqual(status,0);r=json.loads(output.getvalue())
        self.assertEqual(r['column_joints']['column_end_count'],4)
        self.assertEqual(r['column_joints']['geometric_limit_count'],4)
        self.assertEqual(r['column_joints']['scwb_status'],'NOT_PROVEN')
        self.assertNotIn('column_pmm',r)


if __name__=='__main__':unittest.main()
