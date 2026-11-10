"""Independent selection/coverage examples; engineering kernels are not reimplemented."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from column_kinematics_fixture import KinematicsBank
from tbdy_next.column_engine.column_overview import build_column_overview, station_coverage, _shear_summary
from tbdy_next.column_engine.transverse_kernel import shear_reference
from tbdy_next.column_engine.native_archive import BankError
from tbdy_next.column_engine.store import save_column_bank, read_column_bank
from tbdy_next.column_overview_report import number, pmm_text


def inputs(fixture=None):
    with TemporaryDirectory() as directory:
        root = Path(directory); source = root/'bank.zip'; source.write_bytes((fixture or KinematicsBank()).build())
        saved = save_column_bank(source, root/'receipts')
        result = read_column_bank(root/'receipts', saved['run_id'], full=True)
    return tuple(result[k] for k in ('demand_chain', 'column_cages', 'column_pmm', 'column_shear', 'column_sensitivity'))


class ColumnOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = inputs()

    def setUp(self):
        self.args = deepcopy(self.base)
        self.chain, self.cages, self.pmm, self.shear, self.sensitivity = self.args
        self.member = 'C_SYNTHETIC_1'

    def result(self, **filters):
        return build_column_overview(*self.args, **filters)

    def scenario(self, result=None, label='16Φ24'):
        row = next(r for r in (result or self.result())['rows'] if r['member_id'] == self.member)
        return next(s for s in row['scenarios'] if s['candidate_label'] == label)

    def pmm_rows(self):
        rows = [r for r in self.pmm['rows'] if r['member_id'] == self.member and r['candidate_label'] == '16Φ24']
        for r in rows:
            r.update(status='WITHIN_SCENARIO_SURFACE', utilization=.1, reason=None)
        return rows

    def test_all_members_and_all_three_display_scenarios_survive(self):
        result = self.result()
        self.assertEqual((result['member_count'], result['static_state_count']), (2, 8))
        self.assertEqual(result['candidate_labels'], ['16Φ24','16Φ28','16Φ32'])
        self.assertEqual(result['default_display_candidate'], '16Φ24')
        for row in result['rows']:
            self.assertEqual(len(row['scenarios']), 3)
            for s in row['scenarios']:
                self.assertFalse(s['selected_design'])
                self.assertEqual(s['design_values'], {'Nd_kn':None,'M2d_knm':None,'M3d_knm':None,'status':'NOT_PROVEN'})
        self.assertFalse(result['automatic_design_selection'])
        self.assertFalse(result['spectral_design_vectors_formed'])

    def test_summary_uses_one_concurrent_source_vector_not_component_extrema(self):
        rows = self.pmm_rows(); rows[0]['utilization'] = .9
        pm = self.scenario()['pmm']; source = pm['representative']
        self.assertEqual(source['state_id'], rows[0]['state_id'])
        self.assertEqual(source['native_values'], rows[0]['native_values'])
        self.assertEqual(source['source_values']['n_compression_kn'], -rows[0]['native_values']['P'])
        self.assertNotEqual(source['source_values']['n_compression_kn'], max(-r['native_values']['P'] for r in rows))
        self.assertEqual(source['source_values']['m2_knm'], rows[0]['native_values']['M2'])
        self.assertEqual(source['source_values']['m3_knm'], rows[0]['native_values']['M3'])

    def test_exact_ties_and_analysis_element_identity_are_retained(self):
        rows = self.pmm_rows(); rows[1]['utilization'] = rows[2]['utilization'] = .8
        pm = self.scenario()['pmm']
        self.assertEqual(pm['critical_state_count'], 2)
        self.assertEqual({s['state_id'] for s in pm['critical_states']}, {rows[1]['state_id'],rows[2]['state_id']})
        self.assertEqual({s['native_key']['ObjSta'] for s in pm['critical_states']}, {2})
        self.assertEqual(len({s['native_key']['Elm'] for s in pm['critical_states']}), 2)

    def test_selection_uses_unrounded_ratio(self):
        rows = self.pmm_rows();rows[0]['utilization'] = .40952601;rows[1]['utilization'] = .40952610
        self.assertEqual(number(rows[0]['utilization'],4), number(rows[1]['utilization'],4))
        pm = self.scenario()['pmm']
        self.assertEqual(pm['critical_state_count'], 1)
        self.assertEqual(pm['representative']['state_id'], rows[1]['state_id'])

    def test_reordering_inputs_does_not_change_projection_or_tie_representative(self):
        expected = self.result()
        self.chain['candidates'].reverse();self.chain['members'].reverse()
        self.cages['candidates'].reverse();self.cages['members'].reverse()
        for r in (self.pmm,self.shear,self.sensitivity):r['rows'].reverse()
        self.chain['design_summary']['rows'].reverse()
        self.assertEqual(expected, self.result())

    def test_axial_range_exceedance_is_not_hidden_by_low_resolved_pmm(self):
        rows = self.pmm_rows();rows[-1].update(status='OUTSIDE_SCENARIO_AXIAL_RANGE',utilization=None,reason='SECTION_MODEL_AXIAL_LIMIT')
        pm = self.scenario()['pmm']
        self.assertEqual(pm['maximum_resolved_utilization'], .1)
        self.assertEqual(pm['status'], 'AXIAL_RANGE_EXCEEDED')
        self.assertEqual(pm['representative']['state_id'], rows[-1]['state_id'])
        self.assertIn('Eksenel sınır aşılıyor', pmm_text(pm))
        self.assertNotIn('0,1000', pmm_text(pm))

    def test_unresolved_trial_ratio_never_competes_with_resolved_pmm(self):
        rows = self.pmm_rows();rows[0].update(status='NUMERIC_UNRESOLVED',utilization=None,trial_utilization=90,reason='ANGULAR_REFINEMENT_NOT_STABLE')
        pm = self.scenario()['pmm']
        self.assertEqual(pm['status'], 'PARTIAL_NUMERICAL_COVERAGE')
        self.assertEqual(pm['maximum_resolved_utilization'], .1)
        self.assertEqual(pm['unresolved_count'], 1)
        self.assertFalse(pm['trial_ratios_used'])
        self.assertIn('1 belirsiz', pmm_text(pm))

    def test_axial_only_ratio_is_a_separate_metric(self):
        rows = self.pmm_rows();rows[0].update(status='AXIAL_ONLY_SCENARIO',utilization=None,axial_utilization=.8)
        pm = self.scenario()['pmm']
        self.assertEqual(pm['maximum_resolved_utilization'], .1)
        self.assertEqual(pm['maximum_axial_utilization'], .8)
        self.assertEqual(pm['axial_only_count'], 1)
        self.assertNotEqual(pm['representative']['state_id'], rows[0]['state_id'])
        self.assertIn('ayrıca 1 yalnız N', pmm_text(pm))
        for row in rows:row.update(status='AXIAL_ONLY_SCENARIO',utilization=None,axial_utilization=.3)
        pm = self.scenario()['pmm']
        self.assertIsNone(pm['maximum_resolved_utilization'])
        self.assertEqual(pm['status'], 'AXIAL_ONLY_REFERENCES')
        self.assertIn('Yalnız N:', pmm_text(pm))

    def test_no_silent_switch_from_blocked_display_cage_to_another_cage(self):
        rows = self.pmm_rows()
        for row in rows:row.update(status='BLOCKED_INPUTS',utilization=None,reason='TEST_MISSING_INPUT')
        result = self.result();pm = self.scenario(result)['pmm']
        self.assertEqual(result['default_display_candidate'], '16Φ24')
        self.assertEqual(pm['status'], 'NUMERICAL_RESULTS_UNAVAILABLE')
        self.assertEqual(pm['blocked_count'], 4)
        self.assertIsNotNone(self.scenario(result,'16Φ28')['pmm']['maximum_resolved_utilization'])

    def test_shear_maximum_keeps_own_state_and_branches(self):
        pm_rows = self.pmm_rows();pm_rows[0]['utilization'] = .7
        sh_rows = [r for r in self.shear['rows'] if r['member_id']==self.member and r['candidate_label']=='16Φ24']
        for row in sh_rows:
            row['calculation']['branches']['ts500']['source_utilization'] = .1
            row['calculation']['branches']['zero_concrete']['source_utilization'] = .2
        target = next(r for r in sh_rows if r['state_id']==pm_rows[-1]['state_id'] and r['shear_axis']=='V2')
        target['calculation']['branches']['zero_concrete']['source_utilization'] = 1.2
        scenario = self.scenario();sh = scenario['shear']
        self.assertEqual(sh['status'], 'SOURCE_REFERENCE_EXCEEDED')
        self.assertEqual({s['state_id'] for s in sh['at_pmm_representative']}, {pm_rows[0]['state_id']})
        governing = next(b for b in sh['branches'] if b['axis']=='V2' and b['branch']=='zero_concrete')
        self.assertEqual(governing['critical_source_states'][0]['state_id'], pm_rows[-1]['state_id'])
        self.assertIsNone(sh['selected_concrete_branch']);self.assertEqual(sh['ve_status'],'NOT_PROVEN')

    def test_wrong_candidate_identity_with_same_display_label_is_rejected(self):
        self.shear['rows'][0]['candidate_id'] = 'OTHER_CAGE'
        with self.assertRaisesRegex(BankError,'CANDIDATE_BINDING'):self.result()

    def test_other_shear_limits_remain_visible_when_both_resistance_ratios_are_below_one(self):
        import math
        calc=shear_reference(n_compression_kn=1000,shear_kn=1700,area_mm2=320000,bw_mm=400,d_mm=736,
            fck_mpa=35,fywk_mpa=500,asw_mm2=180*math.pi,spacing_mm=100,gamma_c=1.5,gamma_s=1.15)
        self.assertLess(calc['branches']['ts500']['source_utilization'],1)
        self.assertLess(calc['branches']['zero_concrete']['source_utilization'],1)
        self.assertAlmostEqual(calc['ts500_web_reference_kn'],1511.253333333,places=6)
        self.assertAlmostEqual(calc['tbdy_brittle_reference_kn'],1609.173700997,places=6)
        row=deepcopy(self.shear['rows'][0]);row['calculation']=calc;row['native_values']['V2']=1700
        summary=_shear_summary([row],None)
        self.assertEqual(summary['status'],'SOURCE_REFERENCE_EXCEEDED')
        self.assertEqual((summary['branch_source_exceedance_count'],summary['other_limit_exceedance_count']),(0,2))
        self.assertEqual({f['reference'] for f in summary['other_limit_findings']},{'ts500_web','tbdy_brittle'})
        self.assertTrue(all(not f['design_demand_qualified'] for f in summary['other_limit_findings']))

    def test_foreign_vector_and_missing_or_duplicate_assessment_are_rejected(self):
        for change in ('foreign','missing','duplicate'):
            with self.subTest(change=change):
                self.setUp()
                if change=='foreign':
                    self.sensitivity['rows'][0]['native_values'] = {**self.sensitivity['rows'][0]['native_values'], 'M2':9999}
                elif change=='missing':self.shear['rows'].pop()
                else:self.pmm['rows'].append(deepcopy(self.pmm['rows'][0]))
                with self.assertRaises(BankError):self.result()

    def test_invalid_ratio_or_authority_promotion_is_rejected(self):
        for change in ('nan','wrong_status','source','design','second_order'):
            with self.subTest(change=change):
                self.setUp()
                if change=='nan':self.pmm['rows'][0]['utilization'] = float('nan')
                elif change=='wrong_status':self.pmm['rows'][0]['status'] = 'NUMERIC_UNRESOLVED'
                elif change=='source':self.shear['source_archive_sha256'] = 'OTHER'
                elif change=='design':self.cages['selected_design'] = '16Φ32'
                else:self.pmm['actual_second_order_applied'] = True
                with self.assertRaises(BankError):self.result()

    def test_spectral_filter_preserves_member_population_with_empty_calculation(self):
        result = self.result(output_case='RS_SUM')
        self.assertEqual((result['member_count'], result['members_without_static_states']), (2,2))
        self.assertEqual(result['static_state_count'], 0)
        for row in result['rows']:
            for scenario in row['scenarios']:
                self.assertIsNone(scenario['pmm']['representative'])
                self.assertEqual(scenario['pmm']['status'],'NO_STATIC_STATES')
        self.assertFalse(result['spectral_design_vectors_formed'])

    def test_reference_findings_count_comparisons_not_failed_columns(self):
        rows = [r for r in self.sensitivity['rows'] if r['member_id']==self.member][:2]
        for row in rows:
            ref=row['scenarios'][-1]['at_reference_lengths'][-1]
            ref.update(status='NONPOSITIVE_SOURCE_DENOMINATOR',source_denominator=-.059)
        result = self.result()
        self.assertEqual(result['nonpositive_reference_count'], 2)
        self.assertEqual(result['members_with_nonpositive_references'], 1)
        for row in result['rows']:
            self.assertEqual(row['second_order']['status'],'NOT_PROVEN')
            self.assertFalse(row['second_order']['actual_stability_failure_proven'])

    def test_projection_does_not_mutate_any_accepted_input(self):
        before = deepcopy(self.args);self.result();self.result(member_id=self.member,output_case='SUM')
        self.assertEqual(before,self.args)

    def test_missing_section_keeps_members_and_explicit_blocked_scenarios(self):
        fixture=KinematicsBank();fixture.omitted.add(('PropFrame.GetRebarColumn','column_section','RECT_SYNTHETIC'))
        result=build_column_overview(*inputs(fixture))
        self.assertEqual(result['member_count'],2)
        for row in result['rows']:
            self.assertTrue(all(s['pmm']['status']=='NUMERICAL_RESULTS_UNAVAILABLE' for s in row['scenarios']))

    def test_independent_reference_set_overlap_uses_row_and_role(self):
        rows=[]
        for i in range(3):
            refs=[{'role':role,'combination':'SUM','status':'AMBIGUOUS_DESIGN_STATION' if i<2 else 'EXACT_NATIVE_STATION_NOT_FOUND',
                   'exact_station_found':not (role=='PMM' and i!=1),'design_station_ambiguous':i<2,'source_state_count':0}
                  for role in ('PMM','MAJOR_SHEAR','MINOR_SHEAR')]
            rows.append({'table_row_id':str(i),'member_id':'C','station_text':str(i),'references':refs})
        c=station_coverage(rows)
        self.assertEqual((c['reference_count'],c['missing_exact_reference_count'],c['ambiguous_reference_count']), (9,2,6))
        self.assertEqual((c['overlap_reference_count'],c['union_reference_count']), (1,7))
        self.assertEqual((c['ambiguous_row_count'],c['missing_exact_row_count'],c['overlap_row_count']), (2,2,1))
        rows[0]['references'].append(deepcopy(rows[0]['references'][0]))
        with self.assertRaisesRegex(BankError,'DUPLICATE_DESIGN_ROLE'):station_coverage(rows)


if __name__=='__main__':unittest.main()
