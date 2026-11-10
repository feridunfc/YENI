"""Reuse report banks and Column B7 separately; no new report goldens invented."""
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tbdy_next.cli import main
from tbdy_next.column_engine import section_capacity as capacity
from tbdy_next.column_engine.section_reference import ReferenceSection, _axial_root
from tbdy_next.verification import golden_gate as gate
from tbdy_next.verification import report_oracles


class GoldenReportGateTests(unittest.TestCase):
    def test_original_23_comparisons_and_seven_tests_are_preserved_and_execute(self):
        manifest, first, _, _ = gate.load_bank()
        self.assertEqual(len(first['arithmetic_cases']),23)
        self.assertEqual({r['id'] for r in manifest['reports']},{'GOLDEN-01','GOLDEN-02','GOLDEN-03','GOLDEN-04'})
        for name,relative,count in (('golden01','test_golden.py',3),('golden02','COLUMN_GOLDEN_02/test_golden02_arithmetic.py',7)):
            with self.subTest(name=name),TemporaryDirectory() as folder:
                root=Path(folder)
                with ZipFile(gate.ROOT/'data'/f'{name}.zip') as z:
                    for item in z.infolist():
                        if item.is_dir():continue
                        p=root/item.filename
                        self.assertTrue(p.resolve().is_relative_to(root.resolve()))
                        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(item))
                result=subprocess.run([sys.executable,str(root/relative)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn(f'Ran {count} tests',result.stderr)

    def test_golden01_oracle_function_is_reused_verbatim(self):
        with ZipFile(gate.ROOT/'data/golden01.zip') as z:
            source=z.read('test_golden.py').decode()
        original=source[source.index('def calculate(c):'):source.index('\nclass ReportArithmetics')]
        self.assertIn(original,Path(report_oracles.__file__).read_text(encoding='utf8'))

    def test_three_classifications_and_missing_coverage_stay_visible(self):
        r=gate.build_golden_gate()
        self.assertEqual(r['record_count'],44)
        self.assertEqual(r['classification_counts'],{'NUMERICAL_MATCH':13,'ENGINEERING_INTERPRETATION_DIFFERENCE':4,'INSUFFICIENT_SOURCE':27})
        self.assertEqual(len(r['legacy_reference_bank']['golden02_replayed_test_groups']),7)
        self.assertFalse(r['acceptance_eligible']);self.assertEqual(r['engineering_release'],'NOT_READY')
        self.assertEqual({d['domain'] for d in r['required_domains']},set(gate.REQUIRED_DOMAINS))
        self.assertTrue(all(not d['report_golden_complete'] for d in r['required_domains']))
        self.assertFalse(r['independent_numerical_bank']['is_golden_report_01_02'])
        self.assertTrue(r['real_model_bank']['not_substituted_for_report_gate'])

    def test_actual_yeni_beta_matches_independent_report_values(self):
        r=gate.build_golden_gate();rows={v['id']:v for v in r['comparisons']}
        beta=rows['G02_BETA_SZ01_ground']
        self.assertAlmostEqual(beta['yeni'],1.549351615,places=8)
        self.assertLessEqual(beta['yeni_oracle_difference'],1e-12)
        used=rows['G02_USED_FACTOR_SZ01_ground']
        self.assertIsNone(used['yeni']);self.assertEqual(used['report'],1.85)
        self.assertEqual(used['classification'],'ENGINEERING_INTERPRETATION_DIFFERENCE')
        self.assertFalse(used['normative_disagreement_resolved'])
        self.assertFalse(used['printed_symbol_probe']['product_branch_from_printed_symbol'])
        self.assertEqual(rows['G02_EQ729_SZ01_ground']['classification'],'INSUFFICIENT_SOURCE')

    def test_required_as_cannot_replace_provided_area(self):
        rows={v['id']:v for v in gate.build_golden_gate()['comparisons']}
        area=rows['G01_PROVIDED_AS']
        self.assertAlmostEqual(area['yeni'],18.472564803107986)
        self.assertNotEqual(area['yeni'],16.)
        self.assertEqual(area['pdf_pages_1_based'],[183,196])
        self.assertEqual(rows['PMM_REPORT_GATE']['classification'],'INSUFFICIENT_SOURCE')

    def test_scwb_existing_kernel_is_compared_with_printed_capacities(self):
        rows={v['id']:v for v in gate.build_golden_gate()['comparisons']}
        self.assertAlmostEqual(rows['G01_SCWB_COLUMN_SUM']['yeni'],347.34)
        self.assertAlmostEqual(rows['G01_SCWB_BEAM_1P2_SUM']['yeni'],185.8788)
        self.assertIs(rows['G01_SCWB_NUMERIC_INEQUALITY']['yeni'],True)
        self.assertEqual(rows['G01_SCWB_NUMERIC_INEQUALITY']['classification'],'NUMERICAL_MATCH')

    def test_alpha_negative_golden_is_not_hidden_by_different_bank(self):
        r=gate.build_golden_gate();row=next(v for v in r['comparisons'] if v['id']=='G02_ALPHA_ground')
        self.assertAlmostEqual(row['independent'],34.8720/55.6859)
        self.assertTrue(row['below_070_reference'])
        self.assertFalse(row['one_column_repair_proven'])
        self.assertFalse(row['automatic_inverse_alpha_magnification_authorized'])
        self.assertIsNone(row['yeni']);self.assertEqual(row['classification'],'INSUFFICIENT_SOURCE')
        self.assertEqual(r['negative_system_reference']['golden01'],'BLOCKED_A15_SYSTEM_MISMATCH')

    def test_unexplained_discrepancy_is_a_hard_regression_failure(self):
        for args in ((2,1,1,.01),(1,1,2,.01),(True,1,1,0),(None,math.nan,0,0),(None,1,1,-1)):
            with self.subTest(args=args),self.assertRaises(gate.GoldenRegressionError):gate.compare_values(*args)
        with patch.object(gate.ts500_column,'moment_magnification_factors',return_value={'beta':1,'beta_story':1,'final_factor':None,'status':'EQ729_DECISION_NOT_PROVEN'}):
            with self.assertRaisesRegex(gate.GoldenRegressionError,'YENI_ORACLE_MISMATCH'):gate.build_golden_gate()

    def test_source_manifest_and_member_tampering_fail_closed(self):
        with TemporaryDirectory() as folder:
            copy=Path(folder)/'bank';shutil.copytree(gate.ROOT,copy,ignore=shutil.ignore_patterns('__pycache__'))
            p=copy/'data/golden02.zip';p.write_bytes(p.read_bytes()+b'changed')
            with self.assertRaisesRegex(gate.GoldenRegressionError,'SOURCE_CHANGED'):gate.load_bank(root=copy)
            p=copy/'data/SOURCE_MANIFEST.json';p.write_bytes(p.read_bytes()+b' ')
            with self.assertRaisesRegex(gate.GoldenRegressionError,'MANIFEST_CHANGED'):gate.load_bank(root=copy)
        with TemporaryDirectory() as folder,self.assertRaises(FileNotFoundError):gate.build_golden_gate(source_dir=folder)

    def test_unknown_reports_and_full_pdf_presence_are_not_claimed(self):
        r=gate.build_golden_gate()
        self.assertEqual(r['source_verification'],'PINNED_REVIEWED_EXCERPTS_AND_AUDIT_BYTES')
        self.assertFalse(r['source_pdf_bytes_bundled'])
        for name in ('GOLDEN03_REPORT_GATE','GOLDEN04_REPORT_GATE','CAPACITY_SHEAR_REPORT_GATE'):
            row=next(v for v in r['comparisons'] if v['id']==name)
            self.assertIsNone(row['yeni']);self.assertIsNone(row['independent'])
            self.assertEqual(row['classification'],'INSUFFICIENT_SOURCE')

    def test_cli_export_and_enforced_acceptance_exit_code(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);out=io.StringIO()
            with redirect_stdout(out):self.assertEqual(main(['inspect-golden-regression']),0)
            expected=json.loads(out.getvalue());p=root/'gate.json';h=root/'gate.html'
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(['inspect-golden-regression','--json',str(p)]),0)
                self.assertEqual(main(['inspect-golden-regression','--html',str(h)]),0)
                self.assertEqual(main(['inspect-golden-regression','--require-complete']),3)
                self.assertEqual(main(['inspect-golden-regression','--json',str(p)]),2)
            self.assertEqual(json.loads(p.read_text(encoding='utf8')),expected)
            self.assertEqual(h.read_text(encoding='utf8'),gate.build_golden_html(expected))

    def test_html_escapes_evidence_and_summary_rejects_stale_identity(self):
        r=gate.build_golden_gate();bad=deepcopy(r);bad['acceptance_eligible']=True
        with self.assertRaisesRegex(gate.GoldenRegressionError,'DERIVATION_CHANGED'):gate.golden_gate_summary(bad)
        r['comparisons'][0]['explanation']='<script>attack</script>'
        r['result_sha256']=gate.digest({k:v for k,v in r.items() if k!='result_sha256'})
        html=gate.build_golden_html(r);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)


class ReusedColumnB7Tests(unittest.TestCase):
    def test_existing_two_cages_three_angles_with_explicit_model_differences(self):
        gate.load_bank()  # Pins the untouched Column oracle and original fixture.
        spec=importlib.util.spec_from_file_location('vs26_column_b7_oracle',gate.ROOT/'references/column_oracle.py')
        oracle=importlib.util.module_from_spec(spec);sys.modules[spec.name]=oracle;spec.loader.exec_module(oracle)
        classified=[]
        for layout in ('A','B'):
            coords=[(-150.,-250.),(150.,-250.),(-150.,250.),(150.,250.)]
            if layout=='B':coords.extend([(-150.,0.),(150.,0.)])
            bars=tuple(capacity.Bar(x,y,math.pi*20**2/4) for x,y in coords)
            section=capacity.Section(400,600,bars,capacity.Material(35,35/1.5,420/1.15))
            oldbars=tuple(oracle.OracleBar(i,x,y,20,math.pi*20**2/4) for i,(x,y) in enumerate(coords))
            mat=oracle.OracleMaterial(35,35/1.5,420/1.15,.79)
            ref=ReferenceSection(400,600,tuple((b.x2,b.x3,b.area) for b in bars),.85*(35/1.5),.79,420/1.15)
            for angle in (0,45,90):
                with self.subTest(layout=layout,angle=angle):
                    curve=capacity._Curve(section,angle);current,reason=curve.solve(500000)
                    self.assertIsNone(reason)
                    old=oracle.solve_fixed_p_state(width_mm=400,depth_mm=600,bars=oldbars,material=mat,
                        theta_deg=angle,target_n=500000,axial_tolerance_n=1,scan_count=700)
                    self.assertIsNotNone(old)
                    clearance=min(abs(.79*current['c_mm']-d)-r for d,r in zip(curve.depths,curve.radii))
                    if clearance>0:
                        # Original B7 budgets; M3 sign is converted explicitly.
                        self.assertAlmostEqual(current['m2_nmm'],old.m2_nmm,delta=15000)
                        self.assertAlmostEqual(current['m3_nmm'],-old.m3_nmm,delta=15000)
                        self.assertAlmostEqual(current['c_mm'],old.c_mm,delta=.1)
                        classified.append('NUMERICAL_MATCH')
                    else:
                        # This is the old point-bar subtraction versus VS25's
                        # continuous disk subtraction. Do not loosen c or M
                        # tolerance and call the two constitutive models equal.
                        self.assertEqual(angle,0)
                        self.assertGreater(abs(current['c_mm']-old.c_mm),.05)
                        independent=_axial_root(ref,angle,500000,32)
                        self.assertIsNotNone(independent)
                        self.assertAlmostEqual(current['m3_nmm'],independent['m3_nmm'],delta=1000)
                        classified.append('ENGINEERING_INTERPRETATION_DIFFERENCE')
        self.assertEqual(classified.count('NUMERICAL_MATCH'),4)
        self.assertEqual(classified.count('ENGINEERING_INTERPRETATION_DIFFERENCE'),2)


if __name__=='__main__':unittest.main()
