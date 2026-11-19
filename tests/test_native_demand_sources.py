"""Primitive/modal capture, same-cut coverage and sealed report contracts."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch, Mock

from test_column_axial_live import OutputFixture
from test_mixed_design_demands import spectral_fixture, table
from test_r10_live import _rowset
from test_vs04e_basis import ProbeSap
from tbdy_next.basis_probe import capture_basis_probe
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.frame_force_capture import capture_frame_forces, ForceSelectionRestoreError, native_modal_rows
from tbdy_next.frame_force_capture import MODAL_RESULT_FIELDS, MODAL_RESULTS_SCHEMA, ECCENTRICITY_SCHEMA
from tbdy_next.etabs_source_gateway_windows import DisplaySelectionRestoreError
from tbdy_next.engineering.demand_sources import (
    SUPPORT_SCHEMA, demand_capture_plan, component_force_rows, native_demand_source_evidence,
    spectral_modal_parameters,
)
from tbdy_next.engineering.mixed_demands import earthquake_partition, earthquake_row, native_load_patterns


def support_fixture():
    source, axial, scope = spectral_fixture()
    tables = source['vs04_basis_probe']['table_reads']
    key = 'Load Case Definitions - Summary'
    tables[key] = table(key, tables[key]['rows'] + [{'Name': 'M', 'Type': 'Modal - Ritz', 'GUID': 'm'}])
    key = 'Load Case Definitions - Response Spectrum'
    tables[key] = table(key, [{'Name': 'RS', 'ModalCase': 'M'}])
    key = 'Modal Periods And Frequencies'
    source['analysis_sources'] = {'tables': {key: table(key, [{'Case': 'M', 'Mode': str(i)} for i in (1, 2, 3)])}}
    axial['combination_plan']['combinations'][-1]['case_names'] = ['BASE_A', 'RS']
    plan = demand_capture_plan(source, axial['combination_plan'])
    rowsets = {}
    for uid, rowset in source['column_axial']['force_source']['rowsets'].items():
        base = list(native_frame_force_rows(rowset, uid))
        rows = []
        for gravity in (r for r in base if r[4] == 'G'):
            mixed = next(r for r in base if r[:4] == gravity[:4] and r[4] == 'Q')
            rows.append((*gravity[:4], 'BASE_A', *gravity[5:]))
            rows.append((*gravity[:4], 'ACTION_B', 'Single Value', 0.,
                         *[e - 1.2*g for e, g in zip(mixed[7:], gravity[7:])]))
            for mode in (1, 2, 3):
                rows.append((*gravity[:4], 'M', 'Mode', float(mode), *([float(mode)]*6)))
            rows.append((*gravity[:4], 'RS', 'Max', 0., *([1.]*6)))
        rowsets[uid] = _rowset(rows)
    before = {'cases': dict.fromkeys(plan['cases'], False), 'combos': {'G': True, 'Q': False, 'S': False}}
    source['column_axial']['demand_support'] = {
        'schema': SUPPORT_SCHEMA, 'plan': plan, 'force_source': {
            'schema': 'tbdy.next.etabs-frame-force-source.v1', 'api': 'Results.FrameForce',
            'item_type': 'ObjectElm', 'units_code': 6,
            'output_selection_before': before, 'output_selection_after': deepcopy(before),
            'output_selection_during': {'cases': dict.fromkeys(plan['cases'], True), 'combos': dict.fromkeys(before['combos'], False)},
            'mode_shape_option': {'before': [1, 1, False], 'during': [1, 3, True], 'after': [1, 1, False]},
            'expected_modal_modes': plan['modal_modes'], 'rowsets': rowsets, 'errors': {},
        }}
    return source, axial, scope


def modal_fixture():
    fixture = OutputFixture()
    fixture.cases['M'] = False
    fixture.sap.LoadCases.GetNameList.return_value = (3, list(fixture.cases), 0)
    fixture.mode_option = (1, 1, False)
    fixture.setup.GetOptionModeShape.side_effect = lambda *args: (*fixture.mode_option, 0)
    def set_modes(start, end, all_modes):
        fixture.mode_option = (start, end, all_modes)
        return 0
    fixture.setup.SetOptionModeShape.side_effect = set_modes
    def force(member, *args):
        rows = [(member, station, member+'-elm', station, 'M', 'Mode', float(mode), *([float(mode)]*6))
                for mode in ((1, 2, 3) if fixture.mode_option[2] else (1,)) for station in (0., 2.)]
        return [len(rows), *map(list, zip(*rows)), 0]
    fixture.sap.Results.FrameForce.side_effect = force
    return fixture


def pattern_fixture(initial=()):
    sap = ProbeSap()
    sap.DatabaseTables.keys[-1] = 'Load Pattern Definitions'
    sap.LoadPatterns = Mock()
    sap.LoadPatterns.GetNameList.return_value = (2, ['p1', 'p2'], 0)
    db = sap.DatabaseTables
    db.patterns = tuple(initial)
    db.GetLoadPatternsSelectedForDisplay = Mock(side_effect=lambda *args:
        (len(db.patterns), list(db.patterns), 0) if db.patterns else (0, [''], 1))
    def setter(values):
        db.patterns = tuple(v for v in values if v)
        return values, 0
    db.SetLoadPatternsSelectedForDisplay = Mock(side_effect=setter)
    original = db.GetTableForDisplayArray
    def read(key, *args):
        if key == 'Load Pattern Definitions':
            if db.patterns != ('p1', 'p2'):
                return None, 0, [], 0, [], 1
            return None, 2, ['Name', 'Type', 'SelfWtMult'], 2, ['p1', 'Dead', '1', 'p2', 'Seismic', '0'], 0
        return original(key, *args)
    db.GetTableForDisplayArray = Mock(side_effect=read)
    original_metadata = db.GetAllFieldsInTable
    db.GetAllFieldsInTable = lambda key: ((2, 3, ['Name', 'Type', 'SelfWtMult'],
        ['Name', 'Type', 'Self weight multiplier'], ['', '', ''], ['', '', ''], [True]*3, 0)
        if key == 'Load Pattern Definitions' else original_metadata(key))
    return sap


class NativeCaptureContracts(unittest.TestCase):
    def test_column_capture_reuses_same_model_and_adapter_for_support(self):
        from tbdy_next.engineering.column_axial import capture_column_axial
        source, axial, _ = support_fixture()
        plan = {**axial['combination_plan'], 'blockers': []}
        sap = Mock()
        geometry = {'checks': [{'check_id': 'column_rect_min', 'items': [
            {'element_id': uid, 'status': 'MEETS_SUBCONDITION'} for uid in ('C1', 'C2')]}]}
        with patch('tbdy_next.engineering.column_axial.column_strength_plan', return_value=plan), \
             patch('tbdy_next.engineering.column_axial.evaluate_geometry_capture', return_value=geometry), \
             patch('tbdy_next.engineering.column_axial.read_table', return_value={}), \
             patch('tbdy_next.engineering.column_axial.field_schema', return_value={}), \
             patch('tbdy_next.engineering.column_pmm_section.capture_pmm_section', return_value={}), \
             patch('tbdy_next.engineering.column_r10_live.capture_r10_sources', return_value={}), \
             patch('tbdy_next.engineering.column_axial.capture_frame_forces', side_effect=[{'base': True}, {'support': True}]) as capture:
            result = capture_column_axial(sap, source, {'pmm_member': 'ALL'})
        self.assertEqual(capture.call_count, 2)
        self.assertTrue(all(call.args == (sap,) for call in capture.call_args_list))
        self.assertNotIn('cases', capture.call_args_list[0].kwargs)
        self.assertNotIn('combinations', capture.call_args_list[1].kwargs)
        self.assertEqual(capture.call_args_list[1].kwargs['modal_modes'], {'M': [1, 2, 3]})
        self.assertEqual(capture.call_args_list[1].kwargs['spectrum_cases'], ('RS',))
        self.assertEqual(result['force_source'], {'base': True})
        self.assertEqual(result['demand_support']['force_source'], {'support': True})

    def test_all_modes_requested_and_both_output_options_restored(self):
        f = modal_fixture(); before = deepcopy(f.cases)
        capture = capture_frame_forces(f.sap, members=('C1',), cases=('M',), modal_modes={'M': [1, 2, 3]})
        self.assertEqual(set(capture['rowsets']['C1']['StepNum']), {1., 2., 3.})
        self.assertEqual(capture['output_selection_before'], capture['output_selection_after'])
        self.assertEqual(f.cases, before); self.assertEqual(f.mode_option, (1, 1, False))
        self.assertTrue(capture['mode_shape_option']['during'][2])

    def test_frame_failure_retains_member_error_and_restores(self):
        f = modal_fixture(); f.sap.Results.FrameForce.side_effect = RuntimeError('native failure')
        result = capture_frame_forces(f.sap, members=('C1',), cases=('M',), modal_modes={'M': [1, 2, 3]})
        self.assertEqual(list(result['errors']), ['C1'])
        self.assertEqual(f.mode_option, (1, 1, False))
        self.assertEqual(result['output_selection_before'], result['output_selection_after'])

    def test_case_restore_failure_does_not_skip_mode_restore(self):
        f = modal_fixture(); original = f.setup.SetCaseSelectedForOutput.side_effect
        f.setup.SetCaseSelectedForOutput.side_effect = lambda name, flag: 1 if name == 'gravity' and flag else original(name, flag)
        with self.assertRaises(ForceSelectionRestoreError):
            capture_frame_forces(f.sap, members=('C1',), cases=('M',), modal_modes={'M': [1, 2, 3]})
        self.assertEqual(f.mode_option, (1, 1, False))

    def test_mode_setter_mutation_then_error_still_restores(self):
        f = modal_fixture(); original = f.setup.SetOptionModeShape.side_effect
        def setter(start, end, all_modes):
            original(start, end, all_modes)
            return 1 if all_modes else 0
        f.setup.SetOptionModeShape.side_effect = setter
        with self.assertRaisesRegex(ValueError, 'MODE_SELECTION_REJECTED'):
            capture_frame_forces(f.sap, members=('C1',), cases=('M',), modal_modes={'M': [1, 2, 3]})
        self.assertEqual(f.mode_option, (1, 1, False)); self.assertTrue(f.cases['gravity'])

    def test_mode_restore_failure_is_hard_error(self):
        f = modal_fixture(); original = f.setup.SetOptionModeShape.side_effect
        f.setup.SetOptionModeShape.side_effect = lambda start, end, all_modes: original(start, end, all_modes) if all_modes else 1
        with self.assertRaises(ForceSelectionRestoreError):
            capture_frame_forces(f.sap, members=('C1',), cases=('M',), modal_modes={'M': [1, 2, 3]})
        self.assertTrue(f.cases['gravity'])

    def test_unknown_case_rejected_before_selection(self):
        f = modal_fixture()
        with self.assertRaisesRegex(ValueError, 'CASE_MISSING'):
            capture_frame_forces(f.sap, members=('C1',), cases=('unknown',))
        f.setup.DeselectAllCasesAndCombosForOutput.assert_not_called()

    def test_load_patterns_captured_beyond_discovery_budget(self):
        sap = pattern_fixture()
        result = capture_basis_probe(sap, max_tables=1)
        self.assertEqual(result['table_reads']['Load Pattern Definitions']['status'], 'CAPTURED')
        self.assertNotIn('Load Pattern Definitions', result['not_read_table_keys'])
        self.assertEqual(sap.DatabaseTables.patterns, ())
        self.assertEqual(result['table_reads']['Load Pattern Definitions']['display_pattern_selection'],
                         {'before': [], 'during': ['p1', 'p2'], 'after': []})
        self.assertEqual(set(native_load_patterns(result['table_reads'])), {'p1', 'p2'})

    def test_load_pattern_read_failure_preserves_selection(self):
        sap = pattern_fixture(('p1',))
        sap.DatabaseTables.GetTableForDisplayArray.side_effect = RuntimeError('table failed')
        result = capture_basis_probe(sap)
        self.assertEqual(result['table_reads']['Load Pattern Definitions']['status'], 'CAPTURE_ERROR')
        self.assertEqual(sap.DatabaseTables.patterns, ('p1',))

    def test_load_pattern_setter_mutates_then_fails_still_restores(self):
        sap = pattern_fixture(('p1',)); db = sap.DatabaseTables
        original = db.SetLoadPatternsSelectedForDisplay.side_effect
        def setter(values):
            original(values)
            return 1 if len(values) == 2 else 0
        db.SetLoadPatternsSelectedForDisplay.side_effect = setter
        result = capture_basis_probe(sap)
        self.assertEqual(result['table_reads']['Load Pattern Definitions']['status'], 'CAPTURE_ERROR')
        self.assertEqual(db.patterns, ('p1',))

    def test_load_pattern_restore_failure_aborts_combined_capture(self):
        sap = pattern_fixture(('p1',)); db = sap.DatabaseTables
        original = db.SetLoadPatternsSelectedForDisplay.side_effect
        db.SetLoadPatternsSelectedForDisplay.side_effect = lambda values: original(values) if len(values) == 2 else 1
        with self.assertRaises(DisplaySelectionRestoreError):
            capture_basis_probe(sap)

    def test_invalid_load_pattern_selection_prevents_mutation(self):
        sap = pattern_fixture(); db = sap.DatabaseTables
        db.GetLoadPatternsSelectedForDisplay.side_effect = lambda *args: (0, ['p1'], 1)
        result = capture_basis_probe(sap)
        self.assertEqual(result['table_reads']['Load Pattern Definitions']['status'], 'CAPTURE_ERROR')
        db.SetLoadPatternsSelectedForDisplay.assert_not_called()


class DemandCoverageContracts(unittest.TestCase):
    def test_every_mode_and_required_cut_are_accounted_for(self):
        args = support_fixture(); result = native_demand_source_evidence(*args, input_sha='same-source')
        self.assertEqual(result['status'], 'REQUIRED_SOURCE_COVERAGE_COMPLETE')
        self.assertEqual(result['expected_member_case_count'], 8)
        self.assertEqual(result['completed_member_case_count'], 8)
        modal = [r for r in result['rows'] if r['case'] == 'M']
        self.assertEqual([r['matched_cut_slices'] for r in modal], [9, 9])
        self.assertFalse(result['spectral_alpha_authorized'])
        self.assertFalse(result['physical_concurrency_proven'])

    def test_mode_one_alone_does_not_prove_three_mode_coverage(self):
        args = support_fixture(); force = args[0]['column_axial']['demand_support']['force_source']
        force['rowsets']['C1'] = _rowset([r for r in native_frame_force_rows(force['rowsets']['C1'], 'C1') if r[4] != 'M' or r[6] == 1])
        result = native_demand_source_evidence(*args, input_sha='s')
        row = next(r for r in result['rows'] if r['member_id']=='C1' and r['case']=='M')
        self.assertEqual(row['expected_mode_count'], 3)
        self.assertEqual(row['expected_cut_slices'], 9); self.assertEqual(row['matched_cut_slices'], 3)
        self.assertEqual(result['status'], 'SOURCE_PARTIAL')

    def test_one_missing_cut_in_one_mode_is_not_hidden_by_mode_union(self):
        args = support_fixture(); force = args[0]['column_axial']['demand_support']['force_source']
        force['rowsets']['C1'] = _rowset([r for r in native_frame_force_rows(force['rowsets']['C1'], 'C1') if not (r[4]=='M' and r[6]==2 and r[1]==1.5)])
        result = native_demand_source_evidence(*args, input_sha='s')
        row = next(r for r in result['rows'] if r['member_id']=='C1' and r['case']=='M')
        self.assertEqual(row['observed_mode_ids'], [1., 2., 3.])
        self.assertEqual(row['matched_cut_slices'], 8); self.assertEqual(row['status'], 'SOURCE_PARTIAL')

    def test_other_element_side_at_same_object_station_does_not_match(self):
        args = support_fixture(); force = args[0]['column_axial']['demand_support']['force_source']
        rows = list(native_frame_force_rows(force['rowsets']['C1'], 'C1'))
        force['rowsets']['C1'] = _rowset([(*r[:2], 'opposite-side', *r[3:]) if r[4]=='M' and r[6]==2 and r[1]==1.5 else r for r in rows])
        result = native_demand_source_evidence(*args, input_sha='s')
        self.assertEqual(next(r for r in result['rows'] if r['member_id']=='C1' and r['case']=='M')['matched_cut_slices'], 8)

    def test_member_error_preserves_denominators(self):
        args = support_fixture(); force = args[0]['column_axial']['demand_support']['force_source']
        force['rowsets'].pop('C1'); force['errors']['C1'] = 'read failed'
        result = native_demand_source_evidence(*args, input_sha='s')
        self.assertEqual(result['expected_member_case_count'], 8)
        self.assertEqual(result['completed_member_case_count'], 4)
        self.assertEqual(next(r for r in result['rows'] if r['member_id']=='C1' and r['case']=='M')['expected_cut_slices'], 9)

    def test_no_period_inventory_cannot_use_force_rows_as_denominator(self):
        args = support_fixture(); args[0]['analysis_sources']['tables'].clear()
        result = native_demand_source_evidence(*args, input_sha='s')
        self.assertEqual(result['status'], 'BLOCKED_SOURCE')

    def test_noncontiguous_period_inventory_is_rejected(self):
        args = support_fixture(); t=args[0]['analysis_sources']['tables']['Modal Periods And Frequencies']
        t['rows'].pop(1); t['row_count']-=1
        with self.assertRaisesRegex(ValueError, 'INVENTORY_INCOMPLETE'):
            demand_capture_plan(args[0], args[1]['combination_plan'])

    def test_plan_or_units_or_selection_tampering_blocks_support(self):
        for mutation in ('plan','units','selection','mode'):
            args=support_fixture(); support=args[0]['column_axial']['demand_support']; force=support['force_source']
            if mutation=='plan': support['plan']['case_definitions']['M']['guid']='other-model'
            elif mutation=='units': force['units_code']=12
            elif mutation=='selection': force['output_selection_after']['cases']['M']=True
            else: force['mode_shape_option']['after']=[1, 3, True]
            with self.subTest(mutation=mutation):
                self.assertEqual(native_demand_source_evidence(*args, input_sha='s')['status'], 'BLOCKED_SOURCE')

    def test_missing_load_patterns_remains_a_source_gap(self):
        args=support_fixture(); args[0]['vs04_basis_probe']['table_reads'].pop('Load Pattern Definitions')
        result=native_demand_source_evidence(*args,input_sha='s')
        self.assertEqual(result['status'],'SOURCE_PARTIAL')
        self.assertFalse(result['load_pattern_definitions_captured'])

    def test_live_pattern_fields_reuse_the_existing_static_algebra(self):
        args = support_fixture(); tables = args[0]['vs04_basis_probe']['table_reads']
        key = 'Load Pattern Definitions'
        tables[key] = table(key, [{'Name': r['LoadPat'], 'Type': r['DesignType'], 'SelfWtMult': r['SelfWtMult']}
                                  for r in tables[key]['rows']])
        self.assertEqual(native_demand_source_evidence(*args, input_sha='s')['status'], 'REQUIRED_SOURCE_COVERAGE_COMPLETE')
        self.assertEqual(earthquake_partition(args[0], ['Q'], args[1]['combination_plan'])['case_roles']['ACTION_B'], 'EARTHQUAKE')

    def test_conflicting_pattern_fields_or_incomplete_catalog_are_rejected(self):
        for defect in ('aliases', 'catalog', 'restore', 'weight'):
            args = support_fixture(); tables = args[0]['vs04_basis_probe']['table_reads']; key = 'Load Pattern Definitions'
            if defect == 'aliases':
                tables[key] = table(key, [{**r, 'Name': r['LoadPat'], 'Type': 'Other'} for r in tables[key]['rows']])
            elif defect == 'weight':
                tables[key]['rows'][0]['SelfWtMult'] = 'NaN'
            else:
                tables[key]['native_pattern_names'] = ['p1', 'p2'] + (['p3'] if defect == 'catalog' else [])
                tables[key]['display_pattern_selection'] = {'before': [], 'during': tables[key]['native_pattern_names'], 'after': ['p1'] if defect == 'restore' else []}
            with self.subTest(defect=defect):
                self.assertEqual(native_demand_source_evidence(*args, input_sha='s')['status'], 'SOURCE_PARTIAL')
                with self.assertRaises(ValueError):
                    earthquake_partition(args[0], ['Q'], args[1]['combination_plan'])

    def test_primitive_spectrum_is_one_scalar_maximum_not_a_signed_vector(self):
        args = support_fixture(); result = native_demand_source_evidence(*args, input_sha='s')
        spectral = [r for r in result['rows'] if r['case'] == 'RS']
        self.assertEqual([r['matched_cut_slices'] for r in spectral], [3, 3])
        self.assertTrue(all(r['force_semantics'] == 'NATIVE_RESPONSE_SPECTRUM_SCALAR_MAXIMUM' for r in spectral))
        self.assertFalse(result['physical_concurrency_proven']); self.assertFalse(result['spectral_alpha_authorized'])
        static_rows = component_force_rows(args[0], 'C1', args[1]['combination_plan'])
        self.assertFalse(any(r[4] == 'RS' for r in static_rows))

    def test_primitive_spectrum_minimum_or_signed_step_does_not_replace_maximum(self):
        for step in ('Min', 'Single Value'):
            args = support_fixture(); force = args[0]['column_axial']['demand_support']['force_source']
            rows = native_frame_force_rows(force['rowsets']['C1'], 'C1')
            force['rowsets']['C1'] = _rowset([(*r[:5], step, *r[6:]) if r[4] == 'RS' else r for r in rows])
            result = native_demand_source_evidence(*args, input_sha='s')
            self.assertEqual(next(r for r in result['rows'] if r['member_id'] == 'C1' and r['case'] == 'RS')['status'], 'SOURCE_PARTIAL')

    def test_primitive_rows_feed_existing_mixed_algebra_without_combining_archives(self):
        source,axial,scope=support_fixture(); plan=axial['combination_plan']
        for uid,rs in source['column_axial']['force_source']['rowsets'].items():
            source['column_axial']['force_source']['rowsets'][uid]=_rowset([r for r in native_frame_force_rows(rs,uid) if r[4]!='G'])
        recipe=earthquake_partition(source,['Q'],plan)['recipes']['Q']
        self.assertEqual(recipe['observation_weights'],{'ACTION_B':'1'})
        for uid,expected in [('C1',80.),('C2',20.)]:
            rows=component_force_rows(source,uid,plan)
            target=next(r for r in rows if r[4]=='Q' and r[1]==0.)
            effect,_=earthquake_row(rows,target,recipe,length=3.)
            self.assertAlmostEqual(effect[8],expected)

    def test_recorded_html_has_no_calculator_call_and_escapes_values(self):
        from tbdy_next.reporting import _native_demand_sources_html
        result=native_demand_source_evidence(*support_fixture(),input_sha='s')
        result['rows'][0]['case']='<script>bad</script>'
        with patch('tbdy_next.engineering.demand_sources.native_demand_source_evidence',side_effect=AssertionError('recalculation')) as calc:
            html=_native_demand_sources_html(result)
        calc.assert_not_called(); self.assertNotIn('<script>',html); self.assertIn('&lt;script&gt;',html)


def modal_parameter_fixture():
    """Three independent modes and a renamed U2 case; no fixed 100/RSX assumptions."""
    source, axial, scope = support_fixture()
    def native_table(key, rows, units):
        result = table(key, rows)
        result['field_metadata'].update(field_count=len(result['fields']))
        result['field_metadata']['units_by_field'].update(units)
        return result
    source['capture_metadata'] = {'vs04_same_session_capture': True}
    source['vs04_basis_probe'].update(schema='tbdy.next.vs04e.basis-source-probe.v1',
        read_only_invariant_proven=True, units_before=6, units_after=6,
        display_cases_before=[], display_cases_after=[])
    key = 'Load Case Definitions - Response Spectrum'
    source['vs04_basis_probe']['table_reads'][key] = native_table(key, [{
        'Name': 'RS', 'ModalCase': 'M', 'GUID': 'rs', 'LoadName': 'U2', 'CoordSys': 'Global',
        'Angle': '0', 'Function': 'FUNC', 'TransAccSF': '10', 'ModalCombo': 'CQC',
        'DirCombo': 'SRSS', 'RigidResp': 'No', 'EccenRatio': '0.05'}],
        {'Angle': 'deg', 'TransAccSF': 'm/sec2'})
    key = 'Modal Periods And Frequencies'
    periods = ['1', '0.5', '0.25']
    source['analysis_sources'].update(schema='tbdy.next.vs04.analysis-sources.v1',
        display_selection_restored=True, units_before=6, units_after=6)
    source['analysis_sources']['tables'][key] = native_table(key,
        [{'Case': 'M', 'Mode': str(i+1), 'Period': p} for i,p in enumerate(periods)], {'Period':'sec'})
    key = 'Response Spectrum Modal Info'
    rows = [{'SpecCase': 'RS', 'ModalCase': 'M', 'Mode': str(i+1), 'Period': p,
        'DampRatio': ['0.025', '0.05', '0.06'][i], 'U1Acc': '0', 'U2Acc': '1.2', 'U3Acc': '0',
        'U1Amp': '0', 'U2Amp': ['0.123456', '-0.234567', '0'][i], 'U3Amp': '0'} for i,p in enumerate(periods)]
    units = {'Period':'sec', **{a+'Acc':'m/sec2' for a in ('U1','U2','U3')},
             **{a+'Amp':'m' for a in ('U1','U2','U3')}}
    source['vs04_diaphragm_probe'] = {'schema':'tbdy.next.vs04g.diaphragm-modal-probe.v1',
        'display_selection_restored':True, 'units_before':6, 'units_after':6,
        'original_display_cases':[], 'temporary_display_cases':['RS'],
        'spectrum_modal_original_selection': {'table_key': key, 'status':'CAPTURE_ERROR'},
        'spectrum_modal_selected_cases':native_table(key, rows, units)}
    return source, axial, scope


class SpectralModalParameterTests(unittest.TestCase):
    def bind(self, args):
        return native_demand_source_evidence(*args, input_sha='source')['spectral_modal_parameters']

    def test_existing_selected_capture_reconciles_unselected_failure_without_rewriting_source(self):
        args=modal_parameter_fixture(); before=deepcopy(args[0]); result=self.bind(args)
        self.assertEqual(result['status'],'NATIVE_MODAL_PARAMETERS_BOUND')
        self.assertEqual((result['expected_mode_rows'],result['bound_mode_rows']),(3,3))
        self.assertEqual(result['initial_unselected_read_status'],'CAPTURE_ERROR')
        self.assertEqual(args[0],before)
        self.assertEqual(result['cases'][0]['case_guid'],'rs')
        self.assertEqual(result['cases'][0]['modal_case_guid'],'m')

    def test_variable_native_damping_signed_amplitude_and_display_precision_are_preserved(self):
        result=self.bind(modal_parameter_fixture()); case=result['cases'][0]
        self.assertEqual((case['active_damping_min'],case['active_damping_max']),('0.025','0.06'))
        self.assertEqual([r['native_values']['U2Amp'] for r in case['mode_rows']],['0.123456','-0.234567','0'])
        self.assertEqual(case['active_axis'],'U2')
        self.assertEqual(case['acceleration_scale_m_s2'],'10')
        self.assertFalse(result['native_full_precision_proven'])

    def test_modal_parameters_do_not_grant_torsion_or_alpha_or_concurrency_authority(self):
        result=self.bind(modal_parameter_fixture())
        self.assertEqual(result['cases'][0]['accidental_torsion_status'],'DEFINED_NONZERO_CONTRIBUTIONS_UNBOUND')
        self.assertTrue(all(result[k] is False for k in ('spectral_alpha_authorized','physical_concurrency_proven','modal_superposition_qualified')))
        self.assertEqual(result['engineering_release'],'NOT_READY')

    def test_zero_eccentricity_definition_alone_does_not_prove_applied_torsion_absent(self):
        args=modal_parameter_fixture()
        args[0]['vs04_basis_probe']['table_reads']['Load Case Definitions - Response Spectrum']['rows'][0]['EccenRatio']='0'
        self.assertEqual(self.bind(args)['cases'][0]['accidental_torsion_status'],'DEFINED_ZERO_APPLIED_EFFECT_UNPROVEN')

    def test_missing_selected_table_does_not_fall_back_to_initial_read_or_lose_denominator(self):
        args=modal_parameter_fixture(); probe=args[0]['vs04_diaphragm_probe']
        probe['spectrum_modal_original_selection']=probe.pop('spectrum_modal_selected_cases')
        result=self.bind(args)
        self.assertEqual(result['status'],'BLOCKED_SOURCE')
        self.assertEqual((result['expected_mode_rows'],result['bound_mode_rows']),(3,0))

    def test_missing_modal_row_stays_in_expected_population(self):
        args=modal_parameter_fixture(); t=args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']
        t['rows'].pop(1);t['row_count']-=1
        result=self.bind(args)
        self.assertEqual((result['expected_mode_rows'],result['bound_mode_rows']),(3,2))
        self.assertEqual(result['cases'][0]['missing_modes'],[2])
        self.assertEqual(result['status'],'SOURCE_PARTIAL')

    def test_duplicate_mode_is_not_silently_overwritten(self):
        args=modal_parameter_fixture(); t=args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']
        t['rows'].append(deepcopy(t['rows'][0]));t['row_count']+=1
        result=self.bind(args)
        self.assertEqual(result['cases'][0]['duplicate_modes'],[1])
        self.assertEqual(result['bound_mode_rows'],2)
        self.assertEqual(result['status'],'SOURCE_PARTIAL')

    def test_unexpected_mode_never_expands_the_denominator(self):
        args=modal_parameter_fixture(); t=args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']
        t['rows'].append({**t['rows'][0],'Mode':'4'});t['row_count']+=1
        result=self.bind(args)
        self.assertEqual(result['expected_mode_rows'],3)
        self.assertEqual(result['cases'][0]['unexpected_modes'],[4])
        self.assertEqual(result['status'],'SOURCE_PARTIAL')

    def test_modal_period_and_case_must_match_independent_inventory(self):
        for field,value in [('Period','0.9'),('ModalCase','OTHER')]:
            args=modal_parameter_fixture()
            args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']['rows'][0][field]=value
            result=self.bind(args)
            with self.subTest(field=field):
                self.assertEqual(result['bound_mode_rows'],2)
                self.assertEqual(result['status'],'SOURCE_PARTIAL')

    def test_case_guid_and_multicomponent_definition_are_not_guessed(self):
        for defect in ('guid','multi','axis'):
            args=modal_parameter_fixture(); t=args[0]['vs04_basis_probe']['table_reads']['Load Case Definitions - Response Spectrum']
            if defect=='guid': t['rows'][0]['GUID']='another-capture'
            elif defect=='axis': t['rows'][0]['LoadName']='X'
            else: t['rows'].append(deepcopy(t['rows'][0]));t['row_count']+=1
            with self.subTest(defect=defect): self.assertEqual(self.bind(args)['bound_mode_rows'],0)

    def test_wrong_units_metadata_or_row_count_block_source(self):
        for defect in ('amplitude','damping','count','metadata'):
            args=modal_parameter_fixture(); t=args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']
            if defect=='amplitude': t['field_metadata']['units_by_field']['U2Amp']='mm'
            elif defect=='damping': t['field_metadata']['units_by_field']['DampRatio']='percent'
            elif defect=='count': t['row_count']+=1
            else: t['field_metadata']['status']='METADATA_ERROR'
            with self.subTest(defect=defect): self.assertEqual(self.bind(args)['status'],'BLOCKED_SOURCE')

    def test_nonfinite_numeric_fields_do_not_bind(self):
        for field in ('Period','DampRatio','U1Acc','U2Acc','U3Acc','U1Amp','U2Amp','U3Amp'):
            args=modal_parameter_fixture()
            args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']['rows'][0][field]='NaN'
            with self.subTest(field=field): self.assertEqual(self.bind(args)['bound_mode_rows'],2)

    def test_out_of_range_active_damping_is_rejected(self):
        for value in ('-0.01','1.01'):
            args=modal_parameter_fixture()
            args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']['rows'][0]['DampRatio']=value
            with self.subTest(value=value): self.assertEqual(self.bind(args)['bound_mode_rows'],2)

    def test_unexpected_inactive_direction_is_not_folded_into_active_axis(self):
        for field in ('U1Acc','U3Amp'):
            args=modal_parameter_fixture()
            args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']['rows'][0][field]='0.2'
            with self.subTest(field=field): self.assertEqual(self.bind(args)['bound_mode_rows'],2)

    def test_selection_restoration_same_session_and_capture_units_are_required(self):
        for defect in ('selection','restore','session','units','period_units','basis_restore'):
            args=modal_parameter_fixture(); s=args[0]; p=s['vs04_diaphragm_probe']
            if defect=='selection': p['temporary_display_cases']=[]
            elif defect=='restore': p['display_selection_restored']=False
            elif defect=='session': s['capture_metadata']['vs04_same_session_capture']=False
            elif defect=='units': p['units_before']=12
            elif defect=='period_units': s['analysis_sources']['units_after']=12
            else: s['vs04_basis_probe']['display_cases_after']=['CHANGED']
            with self.subTest(defect=defect): self.assertEqual(self.bind(args)['status'],'BLOCKED_SOURCE')

    def test_case_outside_selected_names_is_rejected(self):
        args=modal_parameter_fixture(); args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']['rows'][0]['SpecCase']='OTHER'
        self.assertEqual(self.bind(args)['status'],'BLOCKED_SOURCE')

    def test_one_bad_case_does_not_hide_the_other_case_or_change_population(self):
        args=modal_parameter_fixture(); source=args[0]
        plan=demand_capture_plan(source,args[1]['combination_plan'])
        plan['spectrum_modal_bindings']['OTHER_RS']='M'
        plan['case_definitions']['OTHER_RS']={'guid':'other','type':'Response Spectrum'}
        definitions=source['vs04_basis_probe']['table_reads']['Load Case Definitions - Response Spectrum']
        definitions['rows'].append({**definitions['rows'][0],'Name':'OTHER_RS','GUID':'other'})
        definitions['row_count']+=1
        probe=source['vs04_diaphragm_probe'];probe['temporary_display_cases'].append('OTHER_RS')
        t=probe['spectrum_modal_selected_cases']
        t['rows'] += [{**r,'SpecCase':'OTHER_RS'} for r in list(t['rows'])]
        t['row_count']=len(t['rows'])
        t['rows'][0]['Period']='999'
        result=spectral_modal_parameters(source,plan)
        self.assertEqual((result['expected_case_count'],result['bound_case_count']),(2,1))
        self.assertEqual((result['expected_mode_rows'],result['bound_mode_rows']),(6,5))
        self.assertEqual(next(c for c in result['cases'] if c['case']=='OTHER_RS')['status'],'NATIVE_MODAL_PARAMETERS_BOUND')

    def test_row_order_does_not_change_mode_identity_or_counts(self):
        args=modal_parameter_fixture(); t=args[0]['vs04_diaphragm_probe']['spectrum_modal_selected_cases']
        t['rows'].reverse()
        result=self.bind(args)
        self.assertEqual([r['mode'] for r in result['cases'][0]['mode_rows']],[1,2,3])
        self.assertEqual(result['bound_mode_rows'],3)

    def test_no_spectral_leaves_is_proven_by_the_plan_not_by_empty_returned_rows(self):
        args=modal_parameter_fixture(); plan=demand_capture_plan(args[0],args[1]['combination_plan'])
        plan['spectrum_modal_bindings']={};plan['modal_modes']={}
        result=spectral_modal_parameters({},plan)
        self.assertEqual(result['status'],'NOT_REQUIRED_NO_SPECTRAL_LEAVES')
        self.assertEqual(result['expected_mode_rows'],0)

    def test_binding_repeats_identically_and_keeps_a_record_hash(self):
        args=modal_parameter_fixture()
        a,b=self.bind(args),self.bind(args)
        self.assertEqual(a,b);self.assertEqual(len(a['sha256']),64)
        self.assertTrue(all(len(r['source_row_sha256'])==64 for r in a['cases'][0]['mode_rows']))

    def test_report_projects_parameters_without_calling_the_binder(self):
        from tbdy_next.reporting import _native_demand_sources_html
        result=native_demand_source_evidence(*modal_parameter_fixture(),input_sha='s')
        result['spectral_modal_parameters']['cases'][0]['case']='<script>bad</script>'
        with patch('tbdy_next.engineering.demand_sources.spectral_modal_parameters',side_effect=AssertionError('recalculation')) as calc:
            html=_native_demand_sources_html(result)
        calc.assert_not_called()
        self.assertIn('Native response-spectrum modal parameters',html)
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)


def numeric_modal_records():
    """Synthetic native ABI values; not evidence from a live ETABS model."""
    periods = (0.470003213456789, 0.31337123456789, 0.202020202020202)
    period_rows, factor_rows = [], []
    for mode, period in enumerate(periods, 1):
        frequency = 1. / period
        omega = 2. * math.pi * frequency
        eigenvalue = omega * omega
        period_rows.append(('M', 'Mode', float(mode), period, frequency, omega, eigenvalue))
        factor_rows.append(('M', 'Mode', float(mode), period,
            -0.123456789012345 * mode, 0., 0.2, 0., -0.3, 0.4, 2., 2. * eigenvalue))
    return {method: {'NumberResults': len(rows), **dict(zip(MODAL_RESULT_FIELDS[method], map(list, zip(*rows)))), 'ret': 0}
            for method, rows in (('ModalPeriod', period_rows), ('ModalParticipationFactors', factor_rows))}


def numeric_parameter_fixture():
    args = modal_parameter_fixture(); source = args[0]
    records = numeric_modal_records()
    force = source['column_axial']['demand_support']['force_source']
    force['native_modal_results'] = {'schema': MODAL_RESULTS_SCHEMA, 'units_code': 6, 'methods': {
        name: {'api': 'Results.' + name, 'status': 'CAPTURED', 'data': data} for name, data in records.items()}}
    force['native_spectrum_eccentricity'] = {'schema': ECCENTRICITY_SCHEMA, 'units_code': 6, 'cases': {
        'RS': {'api': ['LoadCases.ResponseSpectrum.GetEccentricity',
                       'LoadCases.ResponseSpectrum.GetDiaphragmEccentricityOverride'],
               'status': 'CAPTURED', 'data': {'default_ratio': 0.05, 'override_lengths_m': {}}}}}
    key = 'Modal Periods And Frequencies'
    rows = [{'Case': 'M', 'Mode': str(i+1), **{
        display: format(records['ModalPeriod'][native][i], '.6g')
        for display, native in (('Period','Period'), ('Frequency','Frequency'),
                                ('CircFreq','CircFreq'), ('Eigenvalue','EigenValue'))}}
        for i in range(3)]
    period_table = table(key, rows)
    period_table['field_metadata'].update(field_count=len(period_table['fields']))
    period_table['field_metadata']['units_by_field'].update(
        Period='sec', Frequency='cyc/sec', CircFreq='rad/sec', Eigenvalue='rad2/sec2')
    source['analysis_sources']['tables'][key] = period_table
    for i, row in enumerate(source['vs04_diaphragm_probe']['spectrum_modal_selected_cases']['rows']):
        row['Period'] = rows[i]['Period']
    return args


def native_numeric_capture_fixture():
    fixture = modal_fixture()
    fixture.cases['RS'] = False
    fixture.sap.LoadCases.GetNameList.return_value = (len(fixture.cases), list(fixture.cases), 0)
    records = numeric_modal_records()
    for method, data in records.items():
        getattr(fixture.sap.Results, method).return_value = (
            data['NumberResults'], *(data[key] for key in MODAL_RESULT_FIELDS[method]), data['ret'])
    api = fixture.sap.LoadCases.ResponseSpectrum
    api.GetEccentricity.return_value = (0.05, 0)
    api.GetDiaphragmEccentricityOverride.return_value = (0, [], [], 0)
    return fixture


def omit_participation_identity(data):
    """Observed null/zero ABI shape; the numbers remain synthetic test values."""
    data['StepType'] = [None] * data['NumberResults']
    data['StepNum'] = [0.] * data['NumberResults']
    return data


class NativeNumericCaptureTests(unittest.TestCase):
    def capture(self, fixture):
        return capture_frame_forces(fixture.sap, members=('C1',), cases=('M', 'RS'),
                                    modal_modes={'M': [1, 2, 3]}, spectrum_cases=('RS',))

    def test_native_methods_share_selected_session_and_preserve_double_values(self):
        fixture = native_numeric_capture_fixture(); before = deepcopy(fixture.cases)
        raw = fixture.sap.Results.ModalPeriod.return_value
        def read(*args):
            self.assertTrue(fixture.cases['M'] and fixture.cases['RS'])
            self.assertTrue(fixture.mode_option[2])
            return raw
        fixture.sap.Results.ModalPeriod.side_effect = read
        result = self.capture(fixture)
        methods = result['native_modal_results']['methods']
        self.assertEqual(methods['ModalPeriod']['data'], numeric_modal_records()['ModalPeriod'])
        self.assertEqual(methods['ModalParticipationFactors']['data'], numeric_modal_records()['ModalParticipationFactors'])
        self.assertEqual(result['native_spectrum_eccentricity']['cases']['RS']['data']['default_ratio'], 0.05)
        self.assertEqual(fixture.cases, before); self.assertEqual(fixture.mode_option, (1, 1, False))
        fixture.sap.LoadCases.ResponseSpectrum.GetEccentricity.assert_called_once_with('RS', 0.)
        fixture.sap.LoadCases.ResponseSpectrum.GetDiaphragmEccentricityOverride.assert_called_once_with('RS', 0, [], [])

    def test_optional_getter_error_retains_forces_and_other_method_and_restores(self):
        for method in MODAL_RESULT_FIELDS:
            fixture = native_numeric_capture_fixture()
            getattr(fixture.sap.Results, method).side_effect = RuntimeError('native getter unavailable')
            result = self.capture(fixture)
            with self.subTest(method=method):
                self.assertEqual(result['native_modal_results']['methods'][method]['status'], 'CAPTURE_ERROR')
                self.assertEqual(len(result['rowsets']), 1)
                self.assertEqual(result['output_selection_before'], result['output_selection_after'])
                self.assertEqual(fixture.mode_option, (1, 1, False))

    def test_null_zero_participation_identity_uses_companion_without_rewriting_raw_values(self):
        fixture = native_numeric_capture_fixture()
        method = 'ModalParticipationFactors'
        data = omit_participation_identity(numeric_modal_records()[method])
        for field in MODAL_RESULT_FIELDS[method]: data[field].reverse()
        getattr(fixture.sap.Results, method).return_value = (
            data['NumberResults'], *(data[key] for key in MODAL_RESULT_FIELDS[method]), data['ret'])
        result = self.capture(fixture)
        record = result['native_modal_results']['methods'][method]
        self.assertEqual(record['status'], 'CAPTURED')
        self.assertEqual(record['data'], data)
        self.assertEqual(record['data']['StepType'], [None] * 3)
        self.assertEqual(record['data']['StepNum'], [0.] * 3)
        self.assertEqual(result['output_selection_before'], result['output_selection_after'])
        self.assertEqual(fixture.mode_option, (1, 1, False))

    def test_failed_period_getter_cannot_supply_null_zero_identity(self):
        fixture = native_numeric_capture_fixture()
        method = 'ModalParticipationFactors'
        data = omit_participation_identity(numeric_modal_records()[method])
        getattr(fixture.sap.Results, method).return_value = (
            data['NumberResults'], *(data[key] for key in MODAL_RESULT_FIELDS[method]), data['ret'])
        fixture.sap.Results.ModalPeriod.side_effect = RuntimeError('unavailable')
        result = self.capture(fixture)
        self.assertEqual(result['native_modal_results']['methods'][method]['status'], 'CAPTURE_ERROR')
        self.assertEqual(result['native_modal_results']['methods'][method]['data'], data)
        self.assertEqual(result['output_selection_before'], result['output_selection_after'])

    def test_rejected_native_identity_retains_exact_data_without_qualifying_it(self):
        fixture = native_numeric_capture_fixture()
        method = 'ModalParticipationFactors'
        data = numeric_modal_records()[method]
        data['StepType'][1] = 'unexpected native step'
        getattr(fixture.sap.Results, method).return_value = (
            data['NumberResults'], *(data[key] for key in MODAL_RESULT_FIELDS[method]), data['ret'])
        result = self.capture(fixture)
        record = result['native_modal_results']['methods'][method]
        self.assertEqual(record['status'], 'CAPTURE_ERROR')
        self.assertEqual(record['data'], data)
        self.assertIn('IDENTITY_OR_NUMBER_INVALID', record['error'])
        self.assertEqual(result['output_selection_before'], result['output_selection_after'])
        self.assertEqual(fixture.mode_option, (1, 1, False))

    def test_nonfinite_native_diagnostic_does_not_poison_other_source_json(self):
        import json
        fixture = native_numeric_capture_fixture()
        method = 'ModalParticipationFactors'
        data = numeric_modal_records()[method]
        data['UX'][1] = float('nan')
        getattr(fixture.sap.Results, method).return_value = (
            data['NumberResults'], *(data[key] for key in MODAL_RESULT_FIELDS[method]), data['ret'])
        result = self.capture(fixture)
        record = result['native_modal_results']['methods'][method]
        self.assertEqual(record['status'], 'CAPTURE_ERROR')
        self.assertNotIn('data', record)
        self.assertEqual(record['unserializable_native_values'], [
            {'field': 'UX', 'index': 1, 'type': 'float', 'representation': 'nan'}])
        json.dumps(result, allow_nan=False)
        self.assertEqual(result['output_selection_before'], result['output_selection_after'])

    def test_native_return_abi_and_codes_are_verified(self):
        for raw in ((0,), (3, *([[]]*7), 1), (True, *([[]]*7), 0), (0, *([[]]*7), False)):
            fixture = native_numeric_capture_fixture(); fixture.sap.Results.ModalPeriod.return_value = raw
            with self.subTest(raw=raw):
                self.assertEqual(self.capture(fixture)['native_modal_results']['methods']['ModalPeriod']['status'], 'CAPTURE_ERROR')
                self.assertEqual(fixture.mode_option, (1, 1, False))

    def test_eccentricity_error_is_not_rewritten_as_zero_overrides(self):
        for method in ('GetEccentricity', 'GetDiaphragmEccentricityOverride'):
            fixture = native_numeric_capture_fixture()
            getattr(fixture.sap.LoadCases.ResponseSpectrum, method).side_effect = RuntimeError('unavailable')
            record = self.capture(fixture)['native_spectrum_eccentricity']['cases']['RS']
            with self.subTest(method=method):
                self.assertEqual(record['status'], 'CAPTURE_ERROR'); self.assertNotIn('data', record)
                self.assertEqual(fixture.mode_option, (1, 1, False))

    def test_zero_override_null_arrays_are_explicit_native_empty_result(self):
        fixture = native_numeric_capture_fixture()
        fixture.sap.LoadCases.ResponseSpectrum.GetDiaphragmEccentricityOverride.return_value = (0, None, None, 0)
        record = self.capture(fixture)['native_spectrum_eccentricity']['cases']['RS']
        self.assertEqual(record['status'], 'CAPTURED'); self.assertEqual(record['data']['override_lengths_m'], {})

    def test_override_lengths_and_native_identifiers_are_not_converted_to_ratios(self):
        fixture = native_numeric_capture_fixture()
        fixture.sap.LoadCases.ResponseSpectrum.GetDiaphragmEccentricityOverride.return_value = (1, ['D1@Story-A'], [1.23456789012345], 0)
        record = self.capture(fixture)['native_spectrum_eccentricity']['cases']['RS']
        self.assertEqual(record['data']['override_lengths_m'], {'D1@Story-A': 1.23456789012345})

    def test_invalid_override_count_duplicate_or_return_is_rejected(self):
        for raw in ((2, ['D1'], [1.], 0), (2, ['D1', 'D1'], [1., 2.], 0),
                    (1, ['D1'], [-1.], 0), (1, ['D1'], [float('inf')], 0),
                    (0, [], [], 1), (False, [], [], 0)):
            fixture = native_numeric_capture_fixture()
            fixture.sap.LoadCases.ResponseSpectrum.GetDiaphragmEccentricityOverride.return_value = raw
            with self.subTest(raw=raw):
                self.assertEqual(self.capture(fixture)['native_spectrum_eccentricity']['cases']['RS']['status'], 'CAPTURE_ERROR')

    def test_spectrum_case_outside_requested_inventory_is_rejected_before_mutation(self):
        fixture = native_numeric_capture_fixture()
        with self.assertRaisesRegex(ValueError, 'SPECTRUM_CASE_INVENTORY_INVALID'):
            capture_frame_forces(fixture.sap, members=('C1',), cases=('M',), spectrum_cases=('RS',))
        fixture.setup.DeselectAllCasesAndCombosForOutput.assert_not_called()

    def test_new_getters_cannot_hide_failed_selection_restoration(self):
        fixture = native_numeric_capture_fixture()
        original = fixture.setup.SetOptionModeShape.side_effect
        fixture.setup.SetOptionModeShape.side_effect = lambda a,b,c: original(a,b,c) if c else 1
        with self.assertRaises(ForceSelectionRestoreError): self.capture(fixture)
        self.assertTrue(fixture.cases['gravity'])


class NativeNumericEvidenceTests(unittest.TestCase):
    def bind(self, args):
        return native_demand_source_evidence(*args, input_sha='synthetic-source')['spectral_modal_parameters']

    def test_unrounded_native_numbers_bind_without_changing_source_or_granting_force_authority(self):
        args = numeric_parameter_fixture(); before = deepcopy(args[0]); modal = self.bind(args)
        result = modal['native_numeric_precision']
        self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 3))
        self.assertTrue(result['native_periods_qualified'])
        self.assertEqual(result['rows'][0]['period_api_values']['Period'], 0.470003213456789)
        self.assertEqual(result['rows'][0]['participation_api_values']['UX'], -0.123456789012345)
        self.assertEqual(args[0], before)
        self.assertTrue(all(result[key] is False for key in ('amplitudes_full_precision_proven',
            'active_damping_full_precision_proven', 'modal_force_reconstruction_qualified')))
        self.assertFalse(modal['spectral_alpha_authorized']); self.assertFalse(modal['native_full_precision_proven'])

    def omitted_fixture(self):
        args = numeric_parameter_fixture()
        methods = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods']
        omit_participation_identity(methods['ModalParticipationFactors']['data'])
        return args, methods

    def test_null_zero_identity_is_bound_by_exact_case_period_independent_of_row_order(self):
        args, methods = self.omitted_fixture()
        for field in MODAL_RESULT_FIELDS['ModalParticipationFactors']:
            methods['ModalParticipationFactors']['data'][field].reverse()
        before = deepcopy(args)
        modal = self.bind(args); result = modal['native_numeric_precision']
        self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 3))
        for row in result['rows']:
            self.assertEqual(row['participation_identity_basis'], 'UNIQUE_EXACT_SAME_CASE_PERIOD')
            self.assertIsNone(row['participation_api_values']['StepType'])
            self.assertEqual(row['participation_api_values']['StepNum'], 0.)
            self.assertEqual(row['participation_api_values']['mode_identity']['mode'], row['mode'])
            self.assertEqual(row['participation_api_values']['UX'], -0.123456789012345 * row['mode'])
        self.assertEqual(args, before)
        self.assertFalse(modal['spectral_alpha_authorized'])
        self.assertFalse(result['modal_force_reconstruction_qualified'])

    def test_null_zero_identity_rejects_degenerate_same_case_periods(self):
        args, methods = self.omitted_fixture()
        periods = methods['ModalPeriod']['data']
        periods['Period'][1] = periods['Period'][0]
        result = self.bind(args)['native_numeric_precision']
        self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 0))
        self.assertIn('NATIVE_MODAL_IDENTITY_PERIOD_MATCH_NOT_UNIQUE', result['reason_codes'])

    def test_null_zero_identity_does_not_use_nearest_period_or_row_position(self):
        args, methods = self.omitted_fixture()
        factors = methods['ModalParticipationFactors']['data']
        factors['Period'][0] = math.nextafter(factors['Period'][0], math.inf)
        result = self.bind(args)['native_numeric_precision']
        self.assertEqual(result['status'], 'BLOCKED_SOURCE')
        self.assertIn('NATIVE_MODAL_IDENTITY_PERIOD_MATCH_NOT_UNIQUE', result['reason_codes'])

    def test_null_zero_identity_requires_complete_independent_period_inventory(self):
        args, methods = self.omitted_fixture()
        periods = methods['ModalPeriod']['data']
        for field in MODAL_RESULT_FIELDS['ModalPeriod']: periods[field].pop()
        periods['NumberResults'] -= 1
        result = self.bind(args)['native_numeric_precision']
        self.assertEqual(result['expected_mode_count'], 3)
        self.assertIn('NATIVE_MODAL_IDENTITY_PERIOD_INVENTORY_INCOMPLETE', result['reason_codes'])

    def test_null_zero_participation_missing_mode_remains_in_denominator(self):
        args, methods = self.omitted_fixture()
        factors = methods['ModalParticipationFactors']['data']
        for field in MODAL_RESULT_FIELDS['ModalParticipationFactors']: factors[field].pop(1)
        factors['NumberResults'] -= 1
        result = self.bind(args)['native_numeric_precision']
        self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 2))
        self.assertEqual(result['status'], 'SOURCE_PARTIAL')
        self.assertIn('NATIVE_MODAL_NUMERIC_MODE_MISSING', result['rows'][1]['reason_codes'])

    def test_only_observed_null_zero_shape_may_use_period_identity(self):
        for step_type, step_num in ((None, 1.), ('', 0.), ('Mode', 0.), ('Step', 0.), (None, False)):
            args, methods = self.omitted_fixture()
            factors = methods['ModalParticipationFactors']['data']
            factors['StepType'][0], factors['StepNum'][0] = step_type, step_num
            with self.subTest(step_type=step_type, step_num=step_num):
                result = self.bind(args)['native_numeric_precision']
                self.assertEqual(result['status'], 'BLOCKED_SOURCE')
                self.assertIn('NATIVE_MODAL_RESULT_IDENTITY_OR_NUMBER_INVALID', result['reason_codes'])

    def test_duplicate_period_bound_participation_cannot_claim_another_mode(self):
        args, methods = self.omitted_fixture()
        factors = methods['ModalParticipationFactors']['data']
        for field in MODAL_RESULT_FIELDS['ModalParticipationFactors']: factors[field][1] = factors[field][0]
        result = self.bind(args)['native_numeric_precision']
        self.assertIn('NATIVE_MODAL_RESULT_DUPLICATE_MODE', result['reason_codes'])

    def test_equal_periods_in_different_cases_are_bound_with_case_identity(self):
        records = numeric_modal_records()
        for method, data in records.items():
            for field in MODAL_RESULT_FIELDS[method]:
                data[field] += ['OTHER'] * 3 if field == 'LoadCase' else data[field][:]
            data['NumberResults'] = 6
        factors = omit_participation_identity(records['ModalParticipationFactors'])
        rows = native_modal_rows(factors, 'ModalParticipationFactors', {'M': [1, 2, 3], 'OTHER': [1, 2, 3]},
                                 period_record=records['ModalPeriod'])
        self.assertEqual([(r['LoadCase'], r['mode_identity']['mode']) for r in rows],
                         [(case, mode) for case in ('M', 'OTHER') for mode in (1, 2, 3)])

    def test_modal_period_getter_cannot_omit_its_own_mode_identity(self):
        args, methods = self.omitted_fixture()
        omit_participation_identity(methods['ModalPeriod']['data'])
        result = self.bind(args)['native_numeric_precision']
        self.assertEqual(result['status'], 'BLOCKED_SOURCE')

    def test_old_capture_keeps_expected_counts_and_missing_evidence(self):
        modal = self.bind(modal_parameter_fixture()); result = modal['native_numeric_precision']
        self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 0))
        self.assertEqual(result['status'], 'NOT_CAPTURED')
        self.assertFalse(result['native_periods_qualified'])
        self.assertEqual(modal['native_torsion_definitions']['status'], 'NOT_CAPTURED')

    def test_error_record_with_retained_data_cannot_qualify_numeric_inputs(self):
        args = numeric_parameter_fixture()
        methods = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods']
        methods['ModalParticipationFactors']['status'] = 'CAPTURE_ERROR'
        methods['ModalParticipationFactors']['error'] = 'Native result identity rejected'
        result = self.bind(args)['native_numeric_precision']
        self.assertEqual(result['status'], 'BLOCKED_SOURCE')
        self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 0))
        self.assertFalse(result['native_periods_qualified'])

    def test_missing_mode_in_either_api_stays_in_denominator(self):
        for method in MODAL_RESULT_FIELDS:
            args = numeric_parameter_fixture()
            data = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods'][method]['data']
            for field in MODAL_RESULT_FIELDS[method]: data[field].pop(1)
            data['NumberResults'] -= 1
            result = self.bind(args)['native_numeric_precision']
            with self.subTest(method=method):
                self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 2))
                self.assertIn('NATIVE_MODAL_NUMERIC_MODE_MISSING', result['rows'][1]['reason_codes'])
                self.assertEqual(result['status'], 'SOURCE_PARTIAL')

    def test_duplicate_unexpected_wrong_case_and_nonnumeric_api_values_are_rejected(self):
        for field, value in (('StepNum', 2.), ('StepNum', 4.), ('LoadCase', 'OTHER'), ('StepType', 'Step'),
                             ('Period', '0.470003'),
                             ('Period', 0.), ('Period', True), ('StepNum', 1.5)):
            args = numeric_parameter_fixture()
            data = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods']['ModalPeriod']['data']
            data[field][0] = value
            with self.subTest(field=field, value=value):
                result = self.bind(args)['native_numeric_precision']
                self.assertEqual(result['status'], 'BLOCKED_SOURCE'); self.assertEqual(result['expected_mode_count'], 3)

    def test_nonfinite_source_is_rejected_before_hashing_any_evidence(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            args = numeric_parameter_fixture()
            data = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods']['ModalPeriod']['data']
            data['Period'][0] = value
            with self.subTest(value=value):
                result = native_demand_source_evidence(*args, input_sha='s')
                self.assertEqual(result['status'], 'BLOCKED_SOURCE')
                self.assertNotIn('spectral_modal_parameters', result)

    def test_native_method_error_schema_or_units_blocks_only_precision_evidence(self):
        for defect in ('method', 'units', 'schema', 'fields', 'array', 'api', 'empty'):
            args = numeric_parameter_fixture()
            capture = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']
            rec = capture['methods']['ModalPeriod']
            if defect == 'method': capture['methods'].pop('ModalParticipationFactors')
            elif defect == 'units': capture['units_code'] = 12
            elif defect == 'schema': capture['schema'] = 'unknown'
            elif defect == 'fields': rec['data']['extra'] = []
            elif defect == 'array': rec['data']['Period'].pop()
            elif defect == 'api': rec['api'] = 'otherAPI'
            else: rec['status'] = 'CAPTURE_ERROR'
            modal = self.bind(args)
            with self.subTest(defect=defect):
                self.assertEqual(modal['native_numeric_precision']['status'], 'BLOCKED_SOURCE')
                self.assertEqual(modal['bound_mode_rows'], 3)
                self.assertFalse(modal['native_full_precision_proven'])

    def test_cross_api_period_frequency_eigenvalue_and_mass_stiffness_conflicts_are_localized(self):
        for method, field in (('ModalPeriod','Frequency'), ('ModalPeriod','CircFreq'),
                              ('ModalPeriod','EigenValue'), ('ModalParticipationFactors','Period'),
                              ('ModalParticipationFactors','ModalStiff')):
            args = numeric_parameter_fixture()
            data = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods'][method]['data']
            data[field][1] *= 1.000001
            result = self.bind(args)['native_numeric_precision']
            with self.subTest(method=method, field=field):
                self.assertEqual(result['bound_mode_count'], 2)
                self.assertIn('NATIVE_MODAL_NUMERIC_IDENTITIES_CONFLICT', result['rows'][1]['reason_codes'])

    def test_display_conflict_and_frequency_units_are_not_ignored(self):
        for defect in ('value', 'unit', 'field'):
            args = numeric_parameter_fixture()
            table = args[0]['analysis_sources']['tables']['Modal Periods And Frequencies']
            if defect == 'value': table['rows'][1]['Frequency'] = '999'
            elif defect == 'unit': table['field_metadata']['units_by_field']['Frequency'] = 'rpm'
            else:
                for row in table['rows']: row.pop('Eigenvalue')
            with self.subTest(defect=defect):
                if defect == 'field':
                    # The enclosing source-table contract rejects a malformed row first.
                    self.assertEqual(native_demand_source_evidence(*args, input_sha='s')['status'], 'BLOCKED_SOURCE')
                    continue
                result = self.bind(args)['native_numeric_precision']
                self.assertFalse(result['native_periods_qualified'])
                self.assertEqual(result['bound_mode_count'], 2 if defect == 'value' else 0)

    def test_declared_binary_consistency_budget_has_an_explicit_boundary(self):
        for ulps, bound in ((32, 3), (33, 2)):
            args = numeric_parameter_fixture()
            data = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods']['ModalParticipationFactors']['data']
            for _ in range(ulps): data['Period'][0] = math.nextafter(data['Period'][0], math.inf)
            with self.subTest(ulps=ulps):
                self.assertEqual(self.bind(args)['native_numeric_precision']['bound_mode_count'], bound)

    def test_empty_native_arrays_are_missing_modes_not_complete(self):
        args = numeric_parameter_fixture()
        methods = args[0]['column_axial']['demand_support']['force_source']['native_modal_results']['methods']
        for method, rec in methods.items():
            rec['data'] = {'NumberResults': 0, 'ret': 0, **dict.fromkeys(MODAL_RESULT_FIELDS[method], [])}
        result = self.bind(args)['native_numeric_precision']
        self.assertEqual((result['expected_mode_count'], result['bound_mode_count']), (3, 0))
        self.assertEqual(result['status'], 'SOURCE_PARTIAL')

    def test_restoration_or_same_session_failure_prevents_new_evidence_binding(self):
        for defect in ('restore', 'session', 'mode'):
            args = numeric_parameter_fixture()
            force = args[0]['column_axial']['demand_support']['force_source']
            if defect == 'restore': force['output_selection_after']['cases']['M'] = True
            elif defect == 'mode': force['mode_shape_option']['after'] = [1, 3, True]
            else: args[0]['capture_metadata']['vs04_same_session_capture'] = False
            result = native_demand_source_evidence(*args, input_sha='s')
            with self.subTest(defect=defect):
                self.assertNotIn('native_numeric_precision', result.get('spectral_modal_parameters', {}))

    def test_torsion_definition_never_proves_applied_force_or_decomposition(self):
        result = self.bind(numeric_parameter_fixture())['native_torsion_definitions']
        self.assertEqual(result['bound_case_count'], 1)
        self.assertEqual(result['status'], 'NATIVE_DEFINITIONS_BOUND_CONTRIBUTIONS_UNAVAILABLE')
        self.assertFalse(result['applied_contributions_bound']); self.assertFalse(result['force_decomposition_qualified'])

    def test_nonzero_overrides_preserve_lengths_but_block_story_identity(self):
        args = numeric_parameter_fixture()
        capture = args[0]['column_axial']['demand_support']['force_source']['native_spectrum_eccentricity']
        capture['cases']['RS']['data']['override_lengths_m'] = {'D1@Story-A': 1.25}
        result = self.bind(args)['native_torsion_definitions']; row = result['cases'][0]
        self.assertEqual(row['override_lengths_m'], {'D1@Story-A': 1.25}); self.assertEqual(row['override_unit'], 'm')
        self.assertFalse(row['override_story_identity_bound']); self.assertEqual(result['bound_case_count'], 0)
        self.assertEqual(result['status'], 'SOURCE_PARTIAL')

    def test_torsion_case_units_and_definition_conflicts_keep_expected_case(self):
        for defect in ('units', 'case', 'guid', 'ratio', 'ratio_zero', 'capture_error', 'invalid_length'):
            args = numeric_parameter_fixture()
            capture = args[0]['column_axial']['demand_support']['force_source']['native_spectrum_eccentricity']
            rec = capture['cases']['RS']
            definition = args[0]['vs04_basis_probe']['table_reads']['Load Case Definitions - Response Spectrum']['rows'][0]
            if defect == 'units': capture['units_code'] = 12
            elif defect == 'case': capture['cases']['OTHER'] = capture['cases'].pop('RS')
            elif defect == 'guid': definition['GUID'] = 'other'
            elif defect == 'ratio': rec['data']['default_ratio'] = 0.15
            elif defect == 'ratio_zero': definition['EccenRatio'] = '0'
            elif defect == 'capture_error': rec['status'] = 'CAPTURE_ERROR'
            else: rec['data']['override_lengths_m'] = {'D1': -1.}
            result = self.bind(args)['native_torsion_definitions']
            with self.subTest(defect=defect):
                self.assertEqual((result['expected_case_count'], result['bound_case_count']), (1, 0))
                self.assertFalse(result['applied_contributions_bound'])

    def test_zero_default_is_not_evidence_of_absent_applied_torsion(self):
        args = numeric_parameter_fixture()
        args[0]['column_axial']['demand_support']['force_source']['native_spectrum_eccentricity']['cases']['RS']['data']['default_ratio'] = 0.
        args[0]['vs04_basis_probe']['table_reads']['Load Case Definitions - Response Spectrum']['rows'][0]['EccenRatio'] = '0'
        result = self.bind(args)['native_torsion_definitions']
        self.assertEqual(result['bound_case_count'], 1); self.assertFalse(result['applied_contributions_bound'])

    def test_native_evidence_repeat_hash_and_report_are_sealed_projection(self):
        from tbdy_next.reporting import _native_demand_sources_html
        args = numeric_parameter_fixture()
        first = native_demand_source_evidence(*args, input_sha='synthetic')
        self.assertEqual(first, native_demand_source_evidence(*args, input_sha='synthetic'))
        first['spectral_modal_parameters']['native_torsion_definitions']['cases'][0]['case'] = '<script>bad</script>'
        with patch('tbdy_next.engineering.demand_sources.native_modal_precision', side_effect=AssertionError('recalculation')) as numeric, \
             patch('tbdy_next.engineering.demand_sources.native_torsion_definitions', side_effect=AssertionError('recalculation')) as torsion:
            html = _native_demand_sources_html(first)
        numeric.assert_not_called(); torsion.assert_not_called()
        self.assertIn('Native modal numeric precision', html); self.assertIn('Accidental-torsion source limits', html)
        self.assertIn('&lt;script&gt;', html); self.assertNotIn('<script>', html)


class SpectrumResponseEvidenceTests(unittest.TestCase):
    def capture_inputs(self):
        fixture = native_numeric_capture_fixture()
        api = fixture.sap.LoadCases.ResponseSpectrum
        api.GetModalCase.return_value = ("M", 0)
        api.GetLoads.return_value = (1, ["U2"], ["FUNC"], [10.], ["Global"], [0.], 0)
        api.GetDampType.return_value = (1, 0)
        api.GetDampConstant.return_value = (0.025, 0)
        api.GetDampOverrides.return_value = (1, [2], [0.037500000000000006], 0)
        fixture.sap.Func.GetValues.return_value = (2, [0., 1.], [1., 3.], 0)
        return fixture

    def inputs(self, fixture):
        return capture_frame_forces(fixture.sap, members=("C1",), cases=("M", "RS"),
            modal_modes={"M": [1, 2, 3]}, spectrum_cases=("RS",))["native_spectrum_inputs"]

    def source(self):
        from fractions import Fraction
        args = numeric_parameter_fixture()
        force = args[0]["column_axial"]["demand_support"]["force_source"]
        force["native_spectrum_inputs"] = self.inputs(self.capture_inputs())
        native = force["native_modal_results"]["methods"]
        native["ModalParticipationFactors"]["data"]["UY"] = [1.25, -2.5, 0.]
        selected = args[0]["vs04_diaphragm_probe"]["spectrum_modal_selected_cases"]
        for i, row in enumerate(selected["rows"]):
            period = native["ModalPeriod"]["data"]["Period"][i]
            eigenvalue = native["ModalPeriod"]["data"]["EigenValue"][i]
            participation = native["ModalParticipationFactors"]["data"]["UY"][i]
            acceleration = 10 * (1 + 2 * Fraction(period))
            amp = Fraction(participation) * acceleration / Fraction(eigenvalue)
            row.update(U2Acc=format(float(acceleration), ".6f"), U2Amp=format(float(amp), ".12f"),
                       DampRatio="0.0375" if i == 1 else "0.025")
        key = "Load Case Definitions - Damping - Modal"
        damping = table(key, [{"Name": "RS", "DampType": "Constant", "ConstDamp": "0.025",
                               "OverMode": "2", "OverDamp": "0.0375"}])
        damping["field_metadata"]["field_count"] = len(damping["fields"])
        args[0]["vs04_basis_probe"]["table_reads"][key] = damping
        return args

    def evidence(self, args):
        return native_demand_source_evidence(*args, input_sha="fixture")["spectral_modal_parameters"]["spectrum_response_evidence"]

    def test_gateway_retains_the_raw_case_function_and_override_returns(self):
        fixture = self.capture_inputs()
        captured = self.inputs(fixture)
        raw = captured["cases"]["RS"]["GetDampOverrides"]
        self.assertEqual(raw["raw"], (1, [2], [0.037500000000000006], 0))
        self.assertEqual(raw["name"], "RS")
        self.assertEqual(captured["functions"]["FUNC"]["raw"], (2, [0., 1.], [1., 3.], 0))
        fixture.sap.Func.GetValues.assert_called_once_with("FUNC", 0, [], [])
        self.assertEqual(fixture.mode_option, (1, 1, False))

    def test_bad_native_return_preserves_diagnostics_and_other_methods(self):
        fixture = self.capture_inputs()
        fixture.sap.LoadCases.ResponseSpectrum.GetDampConstant.return_value = (0.05, 7)
        fixture.sap.Func.GetValues.return_value = (2, [0., 1.], [math.nan, 1.], 0)
        captured = self.inputs(fixture)
        bad = captured["cases"]["RS"]["GetDampConstant"]
        self.assertEqual((bad["status"], bad["raw"]), ("CAPTURE_ERROR", (0.05, 7)))
        self.assertEqual(captured["functions"]["FUNC"]["invalid_native_values"][0]["representation"], "nan")
        self.assertEqual(captured["cases"]["RS"]["GetLoads"]["status"], "CAPTURED")

    def test_native_knots_signed_amplitude_and_damping_override_bind_same_mode(self):
        from fractions import Fraction
        args = self.source()
        result = self.evidence(args)
        self.assertEqual(result["curve_reference_count"], 3)
        self.assertEqual(result["display_status_counts"], {"DISPLAY_INTERVALS_OVERLAP": 2, "ZERO_DISPLAY_PRECISION_UNRESOLVED": 1})
        case = result["cases"][0]
        self.assertEqual(case["case_damping"]["overrides"], {"2": 0.037500000000000006})
        self.assertTrue(all(r["curve_display_compatible"] and r["damping_display_compatible"] for r in case["rows"]))
        self.assertEqual(case["rows"][1]["case_damping_ratio"], 0.037500000000000006)
        native = args[0]["column_axial"]["demand_support"]["force_source"]["native_modal_results"]["methods"]["ModalPeriod"]["data"]
        for i, participant in enumerate((1.25, -2.5, 0.)):
            expected = 10 * (1 + 2 * Fraction(native["Period"][i])) * Fraction(participant) / Fraction(native["EigenValue"][i])
            self.assertLess(abs(expected - Fraction(case["rows"][i]["unadjusted_curve_amplitude_m"])), Fraction(1, 10**57))
        self.assertFalse(result["applied_amplitudes_full_precision_proven"])
        self.assertFalse(result["active_damping_full_precision_proven"])
        self.assertFalse(result["force_reconstruction_qualified"])

    def test_effective_display_disagreement_and_curve_mismatch_remain_visible(self):
        args = self.source()
        rows = args[0]["vs04_diaphragm_probe"]["spectrum_modal_selected_cases"]["rows"]
        rows[0].update(U2Amp="-9.000000", DampRatio="0.075")
        row = self.evidence(args)["cases"][0]["rows"][0]
        self.assertEqual(row["status"], "DISPLAY_CONFLICT")
        self.assertFalse(row["curve_display_compatible"])
        self.assertFalse(row["damping_display_compatible"])

    def test_padded_native_function_requires_the_complete_matching_definition(self):
        from tbdy_next.spectrum_reconstruction import FUNCTION
        args = self.source()
        inputs = args[0]["column_axial"]["demand_support"]["force_source"]["native_spectrum_inputs"]
        inputs["functions"]["FUNC"]["raw"] = (2, [0., 0., 1.], [0., 1., 3.], 0)
        points = table(FUNCTION, [{"Name": "FUNC", "Period": "1.0", "Value": "3.000"},
                                  {"Name": "FUNC", "Period": "0", "Value": "1.000"}])
        points["field_metadata"]["field_count"] = 3
        points["field_metadata"]["units_by_field"]["Period"] = "sec"
        args[0]["vs04_basis_probe"]["table_reads"][FUNCTION] = points
        before = deepcopy(inputs)
        evidence = self.evidence(args)
        self.assertEqual(evidence["curve_reference_count"], 3)
        self.assertEqual(evidence["cases"][0]["native_array_offset"], 1)
        self.assertTrue(all(r["curve_display_compatible"] for r in evidence["cases"][0]["rows"]))
        self.assertEqual(inputs, before)
        for problem in ("foreign", "count", "clock_units", "duplicate", "mismatch", "prefix", "first_period"):
            with self.subTest(problem=problem):
                broken = deepcopy(args)
                tab = broken[0]["vs04_basis_probe"]["table_reads"][FUNCTION]
                raw = broken[0]["column_axial"]["demand_support"]["force_source"]["native_spectrum_inputs"]["functions"]["FUNC"]["raw"]
                if problem == "foreign": tab["rows"][1]["Name"] = "OTHER"
                elif problem == "count": tab["row_count"] += 1
                elif problem == "clock_units": tab["field_metadata"]["units_by_field"]["Period"] = "ms"
                elif problem == "duplicate": tab["rows"][0]["Period"] = "0.00"
                elif problem == "mismatch": tab["rows"][0]["Value"] = "3.001"
                elif problem == "prefix": raw[2][0] = 0.02
                else: raw[1][1] = 0.001
                result = self.evidence(broken)
                self.assertEqual(result["curve_reference_count"], 0)
                self.assertEqual(result["expected_case_mode_count"], 3)
                self.assertFalse(result["applied_amplitudes_full_precision_proven"])

    def test_legacy_and_missing_mode_keep_the_expected_case_mode_and_cut_grid(self):
        args = self.source()
        del args[0]["column_axial"]["demand_support"]["force_source"]["native_spectrum_inputs"]
        selected = args[0]["vs04_diaphragm_probe"]["spectrum_modal_selected_cases"]
        selected["rows"].pop(1)
        selected["row_count"] -= 1
        result = native_demand_source_evidence(*args, input_sha="fixture")
        scope = result["torsion_cut_scope"]
        self.assertEqual((scope["expected_case_cut_count"], scope["isolated_contribution_count"]), (6, 0))
        evidence = result["spectral_modal_parameters"]["spectrum_response_evidence"]
        self.assertEqual(evidence["expected_case_mode_count"], 3)
        self.assertEqual(evidence["cases"][0]["rows"][1]["status"], "BLOCKED_SOURCE")
        self.assertEqual(evidence["curve_reference_count"], 0)
        self.assertEqual(evidence["cases"][0]["case_damping"]["status"], "NOT_CAPTURED")

    def test_foreign_case_function_angle_scale_and_rejected_returns_block_curve(self):
        for defect in ("case", "function", "direction", "angle", "scale", "getter", "ret", "status", "units", "duplicated_knots"):
            with self.subTest(defect=defect):
                args = self.source()
                raw = args[0]["column_axial"]["demand_support"]["force_source"]["native_spectrum_inputs"]
                methods = raw["cases"]["RS"]
                if defect == "case": methods["GetModalCase"]["raw"] = ("Other", 0)
                elif defect == "function": methods["GetLoads"]["raw"][2][0] = "Other"
                elif defect == "direction": methods["GetLoads"]["raw"][1][0] = "U1"
                elif defect == "angle": methods["GetLoads"]["raw"][5][0] = 0.001
                elif defect == "scale": methods["GetLoads"]["raw"][3][0] = 100.
                elif defect == "getter": raw["functions"]["FUNC"]["name"] = "Other"
                elif defect == "ret": raw["functions"]["FUNC"]["raw"] = (2, [0., 1.], [1., 3.], False)
                elif defect == "status": methods["GetLoads"]["status"] = "CAPTURE_ERROR"
                elif defect == "duplicated_knots": raw["functions"]["FUNC"]["raw"][1][1] = 0.
                else: raw["units_code"] = 12
                evidence = self.evidence(args)
                self.assertEqual(evidence["curve_reference_count"], 0)
                self.assertEqual(evidence["expected_case_mode_count"], 3)

    def test_damping_table_and_native_override_cannot_disagree(self):
        args = self.source()
        key = "Load Case Definitions - Damping - Modal"
        args[0]["vs04_basis_probe"]["table_reads"][key]["rows"][0]["OverMode"] = "1"
        evidence = self.evidence(args)
        self.assertEqual(evidence["cases"][0]["case_damping"]["status"], "BLOCKED_SOURCE")
        self.assertEqual(evidence["curve_reference_count"], 3)

    def test_display_percent_or_zero_cannot_bind_to_a_positive_native_ratio(self):
        for field in ("units", "constant", "override"):
            with self.subTest(field=field):
                args = self.source()
                damping = args[0]["vs04_basis_probe"]["table_reads"]["Load Case Definitions - Damping - Modal"]
                if field == "units":
                    damping["field_metadata"]["units_by_field"]["OverDamp"] = "%"
                else:
                    damping["rows"][0]["ConstDamp" if field == "constant" else "OverDamp"] = "0"
                self.assertEqual(self.evidence(args)["cases"][0]["case_damping"]["status"], "BLOCKED_SOURCE")

    def test_printed_boundary_signed_factor_and_curve_endpoints(self):
        from decimal import Decimal
        from tbdy_next.spectrum_reconstruction import modal_amplitude_comparison, native_curve_amplitude
        self.assertEqual(modal_amplitude_comparison("1.0", "-1.1", -1., 1.)["status"], "DISPLAY_INTERVALS_OVERLAP")
        self.assertEqual(modal_amplitude_comparison("1.0", "-1.11", -1., 1.)["status"], "DISPLAY_CONFLICT")
        periods = [Decimal(0), Decimal(1)]
        knots = [(p, p+1, Decimal(0)) for p in periods]
        for t, a in ((0., -2.), (1., -4.)):
            self.assertEqual(native_curve_amplitude(periods, knots, t, 2., -1., 1.)[1], a)
        with self.assertRaisesRegex(ValueError, "OUTSIDE_AVAILABLE_FUNCTION_RANGE"):
            native_curve_amplitude(periods, knots, math.nextafter(1., 2.), 2., 1., 1.)

    def test_total_diaphragm_loads_preserve_case_scope_without_isolating_torsion(self):
        from tbdy_next.diaphragm_probe import DIAPHRAGM_FORCE_TABLE
        args = self.source()
        force = table(DIAPHRAGM_FORCE_TABLE, [{"Story": "Roof", "UniqueName": "7", "OutputCase": "RS",
            "StepType": "Max", "FXA": "2.5", "FYA": "3.5"}])
        force["field_metadata"].update(field_count=len(force["fields"]))
        force["field_metadata"]["units_by_field"].update(FXA="kN", FYA="kN")
        args[0]["vs04_diaphragm_probe"]["diaphragm_forces_selected_cases"] = force
        context = self.evidence(args)["diaphragm_force_context"]
        self.assertEqual(context["rows_by_case"], {"RS": 1})
        self.assertFalse(context["isolated_accidental_contributions_bound"])
        force["rows"][0]["OutputCase"] = "Other"
        self.assertEqual(self.evidence(args)["diaphragm_force_context"]["status"], "BLOCKED_SOURCE")


if __name__ == '__main__':
    unittest.main()
