"""VS02: one bounded ETABS capture with five numerical subchecks, no legacy runtime."""
from __future__ import annotations

from copy import deepcopy
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.etabs_geometry import TABLES, capture_geometry
from tbdy_next.quick_checks import CHECKS, check_registry, evaluate_geometry_capture
from tbdy_next.history import quick_history
from tbdy_next.web import make_handler

FIXTURE = Path(__file__).parent / "fixtures/modal_meets.json"


def tab(role, fields, values, units=None):
    key = TABLES[role]
    return {"table_key": key, "status": "CAPTURED", "fields": fields,
            "row_count": len(values), "rows": [dict(zip(fields, row)) for row in values],
            "field_metadata": {"status": "OK", "table_version": 1,
                               "field_keys": fields[:], "units_by_field": units or {k: "" for k in fields}}}


def geometry():
    f = ["Story", "UniqueName", "Type", "AnalysisSect", "DesignSect"]
    summary = [
        ["S1", "C1", "Column", "C40", "C40"],
        ["S1", "C2", "Column", "C25", "C25"],
        ["S1", "B1", "Beam", "B30", "B30"],
        ["S1", "B2", "Beam", "B24", "B24"],
        ["S1", "B3", "Beam", "B99", "B99"],
    ]
    assignments = [[r[0], r[1], r[3]] for r in summary]
    sections = [
        ["C40", "0.40", "0.40"], ["C25", "0.25", "0.40"],
        ["B30", "0.30", "0.50"], ["B24", "0.24", "0.90"],
    ]
    cols = [["S1", "C1"], ["S1", "C2"]]
    beams = [["S1", "B1"], ["S1", "B2"], ["S1", "B3"]]
    return {"schema": "tbdy.next.geometry.capture.v2", "present_units": 6,
            "present_units_after": 6, "unit_state_unchanged": True,
            "material_types": {"status": "CAPTURED", "source_api": "PropMaterial.GetTypeOAPI",
                               "facts": {"C35/45": {"status": "TYPE_RESOLVED", "material_type_code": 2}}},
            "tables": {
                "FRAME_ASSIGNMENTS": tab("FRAME_ASSIGNMENTS", f, summary),
                "SECTION_ASSIGNMENTS": tab("SECTION_ASSIGNMENTS", ["Story", "UniqueName", "SectProp"], assignments),
                "RECTANGULAR_SECTIONS": tab("RECTANGULAR_SECTIONS", ["Name", "t2", "t3", "Material"],
                                          [r + ["C35/45"] for r in sections],
                                          {"Name": "", "t2": "m", "t3": "m", "Material": ""}),
                "COLUMN_CONNECTIVITY": tab("COLUMN_CONNECTIVITY", ["Story", "UniqueName"], cols),
                "BEAM_CONNECTIVITY": tab("BEAM_CONNECTIVITY", ["Story", "UniqueName"], beams),
                "SECTION_SUMMARY": tab("SECTION_SUMMARY", ["Name", "Area", "Shape", "Material"],
                                       [[x[0], "0.12", "Concrete Rectangular", "C35/45"] for x in sections]),
            }}


class GeometryChecks(unittest.TestCase):
    def test_registry_exact_five_no_fictitious_10(self):
        self.assertEqual(len(CHECKS), 5)
        self.assertEqual({tab: sum(c.tab_id == tab for c in CHECKS) for tab in (7, 11, 12)},
                         {7: 1, 11: 3, 12: 1})
        self.assertEqual(len({r['check_id'] for r in check_registry()}), 16)

    def test_full_assignment_join_all_elements_and_thresholds(self):
        out = evaluate_geometry_capture(geometry())
        self.assertEqual(out['status'], 'SCREENING_PARTIAL')
        checks = {r['check_id']: r for r in out['checks']}
        self.assertEqual(out['source_row_count'], 5)
        self.assertEqual(out['column_connectivity_count'], 2)
        self.assertEqual(out['beam_connectivity_count'], 3)
        self.assertEqual(checks['column_rect_min']['expected_count'], 2)
        self.assertEqual(checks['column_rect_min']['unmet_count'], 1)
        self.assertEqual(checks['beam_width_min']['evaluated_count'], 2)
        self.assertEqual(checks['beam_width_min']['not_proven_count'], 1)
        self.assertEqual(checks['beam_width_min']['unmet_count'], 1)
        self.assertEqual(checks['beam_depth_min']['unmet_count'], 0)
        self.assertEqual(checks['beam_depth_width']['unmet_count'], 1)
        self.assertEqual(checks['column_rect_min']['items'][0]['width_mm'], '400.00')
        self.assertEqual(checks['beam_width_min']['items'][-1]['reason'],
                         'ASSIGNED_SECTION_DEFINITION_MISSING')
        self.assertTrue(all(c['formal_compliance'] == 'NOT_PROVEN' for c in checks.values()))
        self.assertEqual(out['engineering_release'], 'NOT_READY')

    def test_strict_sectprop_source_not_designsect_label(self):
        src = geometry()
        src['tables']['FRAME_ASSIGNMENTS']['rows'][2]['DesignSect'] = 'FAKE_DESIGN_SECTION'
        out = evaluate_geometry_capture(src)
        b1 = next(c for c in out['checks'] if c['check_id'] == 'beam_width_min')['items'][0]
        self.assertEqual(b1['section'], 'B30')
        self.assertEqual(b1['value'], '300.00')
        self.assertTrue(b1['section_design_difference'])

    def test_analysis_section_conflict_blocks_not_pass(self):
        src = geometry()
        src['tables']['FRAME_ASSIGNMENTS']['rows'][2]['AnalysisSect'] = 'DIFFERENT'
        out = evaluate_geometry_capture(src)
        item = next(c for c in out['checks'] if c['check_id'] == 'beam_width_min')['items'][0]
        self.assertEqual(item['status'], 'NOT_PROVEN')
        self.assertEqual(item['reason'], 'ANALYSIS_SECTION_SECTPROP_MISMATCH')

    def test_section_assignment_missing_cannot_fall_back_to_designsect(self):
        src = geometry()
        src['tables']['SECTION_ASSIGNMENTS']['rows'][0]['SectProp'] = ''
        item = next(c for c in evaluate_geometry_capture(src)['checks'] if c['check_id'] == 'column_rect_min')['items'][0]
        self.assertEqual(item['status'], 'NOT_PROVEN')
        self.assertEqual(item['reason'], 'SECTPROP_MISSING_FOR_MEMBER')

    def test_live_unit_metadata_wrong_blocks_all(self):
        src = geometry()
        src['tables']['RECTANGULAR_SECTIONS']['field_metadata']['units_by_field']['t2'] = 'mm'
        out = evaluate_geometry_capture(src)
        self.assertEqual(out['status'], 'SOURCE_SCHEMA_REVIEW_REQUIRED')
        self.assertTrue(all(c['evaluated_count'] == 0 for c in out['checks']))

    def test_display_metadata_field_mismatch_blocks_all(self):
        src = geometry()
        src['tables']['SECTION_ASSIGNMENTS']['field_metadata']['field_keys'].remove('SectProp')
        out = evaluate_geometry_capture(src)
        self.assertIn('display/metadata', out['reason'])

    def test_wrong_present_units_or_changed_during_capture(self):
        for mode in ('wrong', 'changed'):
            with self.subTest(mode=mode):
                src = geometry()
                if mode == 'wrong':
                    src['present_units'] = 9
                else:
                    src['present_units_after'] = 9
                self.assertEqual(evaluate_geometry_capture(src)['status'], 'SOURCE_SCHEMA_REVIEW_REQUIRED')

    def test_duplicate_frame_id_rejected(self):
        src = geometry()
        src['tables']['FRAME_ASSIGNMENTS']['rows'][1]['UniqueName'] = 'C1'
        self.assertIn('DUPLICATE', evaluate_geometry_capture(src)['reason'])

    def test_unmatched_connectivity_cannot_disappear_from_denominator(self):
        src = geometry()
        src['tables']['BEAM_CONNECTIVITY']['rows'].append({'Story': 'S1', 'UniqueName': 'B4'})
        src['tables']['BEAM_CONNECTIVITY']['row_count'] += 1
        out = evaluate_geometry_capture(src)
        beam = next(c for c in out['checks'] if c['check_id'] == 'beam_width_min')
        self.assertEqual(beam['expected_count'], 4)
        self.assertEqual(beam['not_proven_count'], 2)
        self.assertTrue(any(x['reason'] == 'CONNECTIVITY_SUMMARY_IDENTITY_MISMATCH' for x in beam['items']
                            if x['status'] == 'NOT_PROVEN'))

    def test_proven_non_concrete_beam_is_excluded_not_failed(self):
        src = geometry()
        src['tables']['FRAME_ASSIGNMENTS']['rows'][4]['AnalysisSect'] = 'STEEL_I'
        src['tables']['FRAME_ASSIGNMENTS']['rows'][4]['DesignSect'] = 'STEEL_I'
        src['tables']['SECTION_ASSIGNMENTS']['rows'][4]['SectProp'] = 'STEEL_I'
        src['tables']['SECTION_SUMMARY']['rows'].append({
            'Name': 'STEEL_I', 'Area': '0.01', 'Shape': 'Steel I', 'Material': 'S355'})
        src['tables']['SECTION_SUMMARY']['row_count'] += 1
        src['material_types']['facts']['S355'] = {'status': 'TYPE_RESOLVED', 'material_type_code': 1}
        out = evaluate_geometry_capture(src)
        b = next(c for c in out['checks'] if c['check_id'] == 'beam_width_min')
        self.assertEqual(b['expected_count'], 3)
        self.assertEqual(b['evaluated_count'], 2)
        self.assertEqual(b['not_proven_count'], 0)
        self.assertEqual(b['not_applicable_count'], 1)
        self.assertEqual(b['proven_non_concrete_count'], 1)
        self.assertEqual(b['items'][-1]['status'], 'NOT_APPLICABLE')
        self.assertEqual(b['items'][-1]['reason'], 'PROVEN_NON_CONCRETE_MATERIAL')
        self.assertEqual(b['unmet_count'], 1)

    def test_missing_material_type_cannot_infer_concrete_from_section_name(self):
        src = geometry()
        src['material_types']['facts']['C35/45'] = {'status':'TYPE_UNRESOLVED', 'material_type_code': None}
        out = evaluate_geometry_capture(src)
        for check in out['checks']:
            self.assertEqual(check['evaluated_count'], 0)
            self.assertTrue(all(r['status'] == 'NOT_PROVEN' for r in check['items']))
        self.assertEqual(out['status'], 'NO_DATA')

    def test_material_name_or_shape_not_pretended_type_proof(self):
        src = geometry()
        src['tables']['SECTION_SUMMARY']['rows'][0]['Material'] = 'S355'
        # Despite a rectangular section key, the exact material type is unknown.
        result = evaluate_geometry_capture(src)
        item = next(c for c in result['checks'] if c['check_id'] == 'column_rect_min')['items'][0]
        self.assertEqual(item['status'], 'NOT_PROVEN')
        self.assertEqual(item['reason'], 'MATERIAL_TYPE_UNRESOLVED')

    def test_material_api_nonzero_code_is_unresolved(self):
        sap = FakeSap()
        sap.PropMaterial.GetTypeOAPI = lambda name: (2, 0, 1)
        captured = capture_geometry(sap)
        self.assertEqual(captured['material_types']['facts']['C35/45']['status'], 'TYPE_UNRESOLVED')
        out = evaluate_geometry_capture(captured)
        self.assertEqual(out['status'], 'NO_DATA')

    def test_same_section_summary_duplicate_is_rejected(self):
        src = geometry()
        src['tables']['SECTION_SUMMARY']['rows'].append(dict(src['tables']['SECTION_SUMMARY']['rows'][0]))
        src['tables']['SECTION_SUMMARY']['row_count'] += 1
        out = evaluate_geometry_capture(src)
        self.assertEqual(out['status'], 'SOURCE_SCHEMA_REVIEW_REQUIRED')
        self.assertIn('DUPLICATE_OR_EMPTY_SECTION', out['reason'])

    def test_invalid_dimensions_mark_only_referenced_member_unproven(self):
        src = geometry()
        src['tables']['RECTANGULAR_SECTIONS']['rows'][0]['t2'] = 'NaN'
        out = evaluate_geometry_capture(src)
        col = next(c for c in out['checks'] if c['check_id'] == 'column_rect_min')
        self.assertEqual(col['not_proven_count'], 1)
        self.assertEqual(col['evaluated_count'], 1)


class FakeDatabase:
    def __init__(self):
        self.calls = []
        self.meta_calls = []
        self.tables = geometry()['tables']

    def GetTableForDisplayArray(self, *args):
        self.calls.append(args[0])
        for tab in self.tables.values():
            if tab['table_key'] == args[0]:
                cells = []
                for row in tab['rows']:
                    cells.extend(str(row[k]) for k in tab['fields'])
                return (0, 0, tab['fields'], tab['row_count'], cells, 0)
        return (0, 0, [], 0, [], 1)

    def GetAllFieldsInTable(self, key):
        self.meta_calls.append(key)
        for tab in self.tables.values():
            if tab['table_key'] == key:
                fields = tab['fields']
                unit_map = tab['field_metadata']['units_by_field']
                return (1, len(fields), fields, fields, ['']*len(fields),
                        [unit_map.get(f, '') for f in fields], [False]*len(fields), 0)
        return (0, 0, [], [], [], [], [], 1)


class FakeMaterialApi:
    def __init__(self):
        self.queries = []

    def GetTypeOAPI(self, name):
        self.queries.append(name)
        return (2, 0, 0) if name == "C35/45" else (0, 0, 1)


class FakeSap:
    def __init__(self, unit=6):
        self.DatabaseTables = FakeDatabase()
        self.PropMaterial = FakeMaterialApi()
        self.unit = unit
        self.reads = 0

    def GetPresentUnits(self):
        self.reads += 1
        return self.unit


class GeometryCapture(unittest.TestCase):
    def test_exact_six_geometry_tables_metadata_without_mutation(self):
        sap = FakeSap()
        captured = capture_geometry(sap)
        self.assertEqual(captured['present_units'], 6)
        self.assertTrue(captured['unit_state_unchanged'])
        self.assertEqual(set(captured['tables']), set(TABLES))
        self.assertEqual(sap.DatabaseTables.calls, list(TABLES.values()))
        self.assertEqual(sap.DatabaseTables.meta_calls, list(TABLES.values()))
        self.assertEqual(sap.reads, 2)
        self.assertEqual(sap.PropMaterial.queries, ["C35/45"])
        self.assertEqual(evaluate_geometry_capture(captured)['status'], 'SCREENING_PARTIAL')

    def test_bad_field_metadata_not_qualified(self):
        sap = FakeSap()
        def bad_meta(*args):
            return (0,)
        sap.DatabaseTables.GetAllFieldsInTable = bad_meta
        self.assertEqual(evaluate_geometry_capture(capture_geometry(sap))['status'],
                         'SOURCE_SCHEMA_REVIEW_REQUIRED')


def fake_live_suite(case):
    payload = json.loads(FIXTURE.read_text(encoding='utf-8'))
    payload['source_mode'] = 'LIVE_ETABS'
    payload['capture_metadata'] = {'model_filename':r'C:\tmp\kompakt_b.EDB',
                                   'case_row_count': 2, 'display_selection_restored':True}
    payload['geometry_capture'] = geometry()
    return payload


class LiveQuickSuiteWeb(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.calls = []
        self.handler = make_handler(Path(self.tmp.name), live_capture=lambda case: (self.calls.append(case), fake_live_suite(case))[1])
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), self.handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def test_tree_api_counts_come_from_implemented_check_registry(self):
        with urlopen(self.base + '/api/check-registry', timeout=4) as response:
            info = json.loads(response.read())
        self.assertEqual(info['implemented_check_count'], 16)
        self.assertEqual(sum(x['tab_id'] == 11 for x in info['checks']), 3)
        self.assertEqual(sum(x['tab_id'] == 12 for x in info['checks']), 1)

    def test_one_live_request_both_domains_and_local_receipt(self):
        req = Request(self.base + '/api/live-suite?case=Modal', data=b'', method='POST')
        with urlopen(req, timeout=4) as response:
            body = json.loads(response.read())
        self.assertEqual(body['result']['sum_ux'], '0.96')
        self.assertEqual(len(body['geometry']['checks']), 4)
        self.assertEqual(self.calls, ['Modal'])
        path = Path(self.tmp.name) / body['run_id']
        self.assertTrue((path / 'input.source').exists())
        self.assertEqual(len(list(path.glob('*quick-geometry.json'))), 1)
        history = quick_history(Path(self.tmp.name))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['geometry']['checks'][0]['unmet_count'], 1)

    def test_rejects_tampered_geometry_receipt(self):
        req = Request(self.base + '/api/live-suite?case=Modal', data=b'', method='POST')
        with urlopen(req, timeout=4) as response:
            body = json.loads(response.read())
        receipt = next((Path(self.tmp.name) / body['run_id']).glob('*quick-geometry.json'))
        receipt.write_text(receipt.read_text().replace('SCREENING_PARTIAL', 'FAKE_PASS'))
        self.assertEqual(quick_history(Path(self.tmp.name)), [])

    def test_cross_origin_cannot_start_live_suite(self):
        req = Request(self.base + '/api/live-suite?case=Modal', data=b'',
                      headers={'Origin':'https://unauthorized.invalid'}, method='POST')
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req, timeout=4)
        self.assertEqual(ctx.exception.code, 403)
        self.assertEqual(self.calls, [])

    def test_ui_contains_combined_button_and_registry_tree(self):
        with urlopen(self.base + '/', timeout=4) as response:
            html = response.read().decode('utf-8')
        self.assertIn('id="runAllBtn"', html)
        self.assertNotIn('id="quickSuiteBtn"', html)
        self.assertIn('id="geometrycontent"', html)
        self.assertIn('/quick.js', html)
        with urlopen(self.base + '/quick.js', timeout=4) as response:
            js = response.read().decode('utf-8')
        self.assertIn('definitions.filter(d => d.tab_id === index)', js)
        self.assertIn('Beton dışı:', js)
        self.assertIn('item.material_classification', js)
        self.assertNotIn('10 CHECK', js)


if __name__ == '__main__':
    unittest.main()
