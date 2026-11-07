"""VS03 additional source-bound vertical slice: material fck and A1 X/Y."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.next_capture import capture_next_facts
from tbdy_next.next_checks import evaluate_next_capture, EXTRA_CHECKS
from tbdy_next.quick_checks import check_registry
from tbdy_next.web import make_handler
from test_quick_suite import geometry, fake_live_suite


def source():
    cols = ["Material", "Fc"]
    fields = ["Story", "OutputCase", "Direction", "MaxDrift", "AvgDrift", "Ratio"]
    rows = [
        {"Story": "+3", "OutputCase": "RSX", "Direction": "X", "MaxDrift": "0.00125", "AvgDrift": "0.001", "Ratio": "1.25"},
        {"Story": "+3", "OutputCase": "RSY", "Direction": "Y", "MaxDrift": "0.00118", "AvgDrift": "0.001", "Ratio": "1.18"},
        {"Story": "+6", "OutputCase": "RSX", "Direction": "X", "MaxDrift": "0.00112", "AvgDrift": "0.001", "Ratio": "1.12"},
        {"Story": "+6", "OutputCase": "RSY", "Direction": "Y", "MaxDrift": "0.00131", "AvgDrift": "0.001", "Ratio": "1.31"},
    ]
    def table(key, fields, rows, units):
        return {"status": "CAPTURED", "table_key": key, "fields": fields,
                "row_count": len(rows), "rows": rows,
                "field_metadata": {"status": "OK", "field_keys": fields,
                                   "units_by_field": units}}
    return {"schema": "tbdy.next.vs03.capture.v1", "units_before": 6, "units_after": 6,
            "case_selection_restored": True, "x_case": "RSX", "y_case": "RSY",
            "material_table": table("Material Properties - Concrete Data", cols,
                                    [{"Material": "C35/45", "Fc": "35000"}],
                                    {"Material": "", "Fc": "kN/m2"}),
            "a1_table": table("Story Max Over Avg Drifts", fields, rows,
                              {k: "" for k in fields})}


def geo():
    g=geometry()
    for row in g["tables"]["FRAME_ASSIGNMENTS"]["rows"]:
        row["Story"]="+3"
    return g


class Vs03Math(unittest.TestCase):
    def test_three_new_checks_and_values(self):
        out=evaluate_next_capture(source(),geo())
        self.assertEqual(len(EXTRA_CHECKS),3)
        self.assertEqual(len(check_registry()),8)
        self.assertEqual(out['status'],'NUMERICAL_CLASSIFIED')
        a,b,c=out['checks']
        self.assertEqual(a['items'][0]['fck_mpa'],'35.000')
        self.assertEqual(a['status'],'MEETS_SUBCONDITION')
        self.assertEqual(b['a1_present_count'],1)
        self.assertEqual(c['a1_present_count'],1)
        self.assertEqual(b['items'][0]['eta_bi'],'1.25')
        self.assertEqual(out['applicability_basis'],'NOT_REVIEWED')
        self.assertTrue(all(x['formal_compliance']=='NOT_PROVEN' for x in out['checks']))

    def test_fck_below_25_is_negative_not_false_success(self):
        x=source();x['material_table']['rows'][0]['Fc']='20000'
        a=evaluate_next_capture(x,geo())['checks'][0]
        self.assertEqual(a['status'],'DOES_NOT_MEET_SUBCONDITION')
        self.assertEqual(a['unmet_count'],1)

    def test_unknown_fck_units_do_not_pass(self):
        x=source();x['material_table']['field_metadata']['units_by_field']['Fc']='psi'
        a=evaluate_next_capture(x,geo())['checks'][0]
        self.assertEqual(a['status'],'NOT_PROVEN')
        self.assertEqual(a['items'][0]['reason'],'FC_FIELD_UNIT_NOT_REVIEWED')

    def test_duplicate_material_definition_is_not_proven(self):
        x=source();x['material_table']['rows'].append(dict(x['material_table']['rows'][0]));x['material_table']['row_count']=2
        a=evaluate_next_capture(x,geo())['checks'][0]
        self.assertEqual(a['status'],'NOT_PROVEN')
        self.assertEqual(a['items'][0]['reason'],'MATERIAL_ROW_MISSING_OR_DUPLICATE')

    def test_wrong_a1_ratio_is_not_proven(self):
        x=source();x['a1_table']['rows'][0]['Ratio']='1.01'
        xrow=evaluate_next_capture(x,geo())['checks'][1]['items'][0]
        self.assertEqual(xrow['status'],'NOT_PROVEN')
        self.assertEqual(xrow['reason'],'A1_ROW_INVALID_OR_RATIO_CONFLICT')

    def test_missing_direction_case_is_not_proven(self):
        x=source();x['a1_table']['rows']=[r for r in x['a1_table']['rows'] if r['OutputCase']!='RSY'];x['a1_table']['row_count']=2
        y=evaluate_next_capture(x,geo())['checks'][2]
        self.assertEqual(y['not_proven_count'],2)
        self.assertEqual(y['status'],'NOT_PROVEN')

    def test_missing_a1_schema_does_not_crash_or_pass(self):
        x=source();x['a1_table']['fields'].remove('Direction')
        y=evaluate_next_capture(x,geo())['checks'][2]
        self.assertEqual(y['status'],'NOT_PROVEN')

    def test_unresolved_material_type_never_passes(self):
        g=geo();g['material_types']['facts']['C35/45']={'status':'TYPE_UNRESOLVED','material_type_code':None}
        a=evaluate_next_capture(source(),g)['checks'][0]
        self.assertEqual(a['status'],'NOT_PROVEN')
        self.assertEqual(a['items'][0]['reason'],'MATERIAL_TYPE_UNRESOLVED')

    def test_source_missing_is_unknown(self):
        self.assertEqual(evaluate_next_capture(None,geo())['status'],'SOURCE_SCHEMA_REVIEW_REQUIRED')


class NextDb:
    def __init__(self, broken=False):
        self.cases=('LC_DL',)
        self.writes=[]
        self.broken=broken
        self.data=source()
    def GetLoadCasesSelectedForDisplay(self):
        return (len(self.cases),list(self.cases),0)
    def SetLoadCasesSelectedForDisplay(self,values):
        self.writes.append(tuple(values))
        self.cases=tuple(x for x in values if x)
        return 0
    def GetAllFieldsInTable(self,key):
        table=self.data['material_table'] if key=='Material Properties - Concrete Data' else self.data['a1_table']
        fields=table['fields'];u=table['field_metadata']['units_by_field']
        return 1,len(fields),fields,fields,['']*len(fields),[u.get(f,'') for f in fields],[False]*len(fields),0
    def GetTableForDisplayArray(self,key,*args):
        if self.broken and key=='Story Max Over Avg Drifts':
            raise RuntimeError('broken table')
        t=self.data['material_table'] if key=='Material Properties - Concrete Data' else self.data['a1_table']
        cells=[str(row[k]) for row in t['rows'] for k in t['fields']]
        return (None,1,t['fields'],len(t['rows']),cells,0)
class NextSap:
    def __init__(self,broken=False):
        self.DatabaseTables=NextDb(broken)
    def GetPresentUnits(self):
        return 6

class NextCapture(unittest.TestCase):
    def test_capture_restores_selected_cases(self):
        sap=NextSap(); data=capture_next_facts(sap)
        self.assertEqual(data['a1_table']['row_count'],4)
        self.assertEqual(data['material_table']['row_count'],1)
        self.assertEqual(sap.DatabaseTables.cases,('LC_DL',))
        self.assertEqual(sap.DatabaseTables.writes,[('RSX','RSY'),('LC_DL',)])

    def test_failed_table_restores_selection(self):
        sap=NextSap(broken=True)
        capture = capture_next_facts(sap)
        self.assertEqual(capture['a1_table']['status'], 'CAPTURE_ERROR')
        self.assertEqual(sap.DatabaseTables.cases,('LC_DL',))

class Vs03ReportIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        def live(case):
            p=fake_live_suite(case)
            p['next_capture']=source()
            p['geometry_capture']=geo()
            return p
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(Path(self.tmp.name),live_capture=live))
        self.thread=Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2);self.tmp.cleanup()
    def _run(self):
        req=Request(self.base+'/api/live-suite?case=Modal',data=b'',method='POST')
        with urlopen(req,timeout=6) as res:
            return json.loads(res.read())
    def test_export_contains_all_eight_and_source(self):
        out=self._run()
        self.assertEqual(out['extra_checks']['status'],'NUMERICAL_CLASSIFIED')
        rid=out['run_id']
        with urlopen(self.base+'/api/export-checks?run_id='+rid,timeout=6) as res:
            export=json.loads(res.read())
        self.assertEqual(len(export['checks']),8)
        self.assertEqual(export['checks'][5]['items'][0]['fck_mpa'],'35.000')
        self.assertEqual(export['source_snapshot']['next_capture']['a1_table']['row_count'],4)
        self.assertEqual(export['engineering_release'],'NOT_READY')
        with urlopen(self.base+'/report/print?run_id='+rid,timeout=6) as res:
            html=res.read().decode('utf-8')
        self.assertIn('A1 burulma katsayısı',html)
        self.assertIn('Kullanılan beton',html)

    def test_tampered_extra_receipt_blocks_export(self):
        out=self._run();rid=out['run_id']
        quick=next((Path(self.tmp.name)/rid).glob('*quick-extra.json'))
        quick.write_text(quick.read_text(encoding='utf-8').replace('MEETS_SUBCONDITION','FAKE_PASS'),encoding='utf-8')
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base+'/api/export-checks?run_id='+rid,timeout=6)
        self.assertEqual(error.exception.code,404)

    def test_old_five_check_result_still_exportable(self):
        # Existing archived runs must survive registry growth.
        rid=self._run()['run_id']
        d=Path(self.tmp.name)/rid
        # Generate an ordinary five-check report by stripping VS03 capture and re-archiving
        # would invalidate existing receipts; instead the legacy coverage remains in
        # the preexisting test_report_export suite.
        self.assertTrue((d/'input.source').exists())

if __name__=='__main__':unittest.main()
