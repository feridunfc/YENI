"""Primitive/modal capture, same-cut coverage and sealed report contracts."""
from copy import deepcopy
import unittest
from unittest.mock import patch, Mock

from test_column_axial_live import OutputFixture
from test_mixed_design_demands import spectral_fixture, table
from test_r10_live import _rowset
from test_vs04e_basis import ProbeSap
from tbdy_next.basis_probe import capture_basis_probe
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.frame_force_capture import capture_frame_forces, ForceSelectionRestoreError
from tbdy_next.etabs_source_gateway_windows import DisplaySelectionRestoreError
from tbdy_next.engineering.demand_sources import (
    SUPPORT_SCHEMA, demand_capture_plan, component_force_rows, native_demand_source_evidence,
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


if __name__ == '__main__':
    unittest.main()
