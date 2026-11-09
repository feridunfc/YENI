from copy import deepcopy
import math
import unittest
from unittest.mock import patch

from test_vs15_column_pmm import inputs
from tbdy_next.column_engine.column_pmm import build_column_pmm
from tbdy_next.column_engine.column_pmm_quality import build_column_pmm_quality
from tbdy_next.column_engine.native_archive import BankError


class CriticalPMMReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,chain,_,stability,cages=inputs()
        cls.baseline=(chain,cages,build_column_pmm(chain,cages,stability))
    def setUp(self):self.chain,self.cages,self.pmm=deepcopy(self.baseline)
    def result(self,**filters):return build_column_pmm_quality(self.chain,self.cages,self.pmm,**filters)
    def member_rows(self):return [r for r in self.pmm['rows'] if r['member_id']=='C_SYNTHETIC_1' and r['candidate_label']=='16Φ24']
    def replace_capacity(self,row,capacity):
        row['radial_capacity_kNm']=capacity
        row['utilization']=math.hypot(row['native_values']['M2'],row['native_values']['M3'])/capacity
        row['refinement']['capacity_kNm']=[capacity]*3

    def test_critical_subset_matches_without_modifying_primary_or_claiming_full_coverage(self):
        before=deepcopy((self.chain,self.cages,self.pmm));r=self.result()
        self.assertEqual((r['comparison_count'],r['member_scenario_count']),(6,6))
        self.assertEqual(r['status_counts'],{'NUMERICAL_COMPARISON_MATCH':6})
        self.assertEqual((self.chain,self.cages,self.pmm),before)
        for flag in ('full_primary_population_independently_checked','critical_selection_independently_verified',
                     'independent_material_model_validation','actual_second_order_applied','primary_results_changed'):
            self.assertFalse(r[flag])
        self.assertEqual((r['design_demand_authority'],r['formal_compliance'],r['engineering_release']),('DENIED','NOT_PROVEN','NOT_READY'))

    def test_every_equal_primary_maximum_keeps_state_and_source_binding(self):
        primary=self.member_rows()
        # Equal original source vectors occur at different elements/stations in this fixture.
        for row in primary[:2]:self.replace_capacity(row,math.hypot(row['native_values']['M2'],row['native_values']['M3'])/.5)
        r=self.result(member_id='C_SYNTHETIC_1')
        group=next(g for g in r['members'] if g['candidate_label']=='16Φ24')
        expected={row['state_id'] for row in primary[:2]}
        self.assertEqual(set(group['target_state_ids']),expected)
        compared=[row for row in r['rows'] if row['candidate_label']=='16Φ24']
        self.assertEqual({row['state_id'] for row in compared},expected)
        self.assertEqual(group['comparison_count'],2)
        for row in compared:
            source=next(p for p in primary if p['state_id']==row['state_id'])
            for key in ('candidate_id','native_key','native_values','source_row_id'):self.assertEqual(row[key],source[key])

    def test_small_primary_capacity_corruption_is_detected_with_fixed_budget(self):
        for row in self.member_rows():self.replace_capacity(row,row['radial_capacity_kNm']*.99)
        r=self.result(member_id='C_SYNTHETIC_1')
        changed=next(x for x in r['rows'] if x['candidate_label']=='16Φ24')
        self.assertEqual(changed['status'],'NUMERICAL_COMPARISON_MISMATCH')
        self.assertGreater(changed['absolute_difference_knm'],changed['comparison_budget_knm'])
        self.assertFalse(r['numerical_policy']['primary_level_spread_added_to_budget'])
        self.assertEqual(r['numerical_policy']['comparison_relative_tolerance'],.002)

    def test_reference_failure_is_retained_in_target_population(self):
        with patch('tbdy_next.column_engine.column_pmm_quality.reference_radial_capacity',side_effect=ValueError('NO_ROOT')):
            r=self.result()
        self.assertEqual(r['comparison_count'],r['critical_target_count'])
        self.assertEqual(r['status_counts'],{'REFERENCE_UNRESOLVED':6})
        self.assertTrue(all(x['reference_capacity_knm'] is None and x['reason']=='NO_ROOT' for x in r['rows']))
        self.assertTrue(all(not g['critical_comparisons_all_match'] for g in r['members']))

    def test_axial_only_outside_and_unresolved_groups_remain_visible_unchecked(self):
        for row in self.member_rows():row.update(status='NUMERIC_UNRESOLVED',utilization=None)
        for row,status in zip(self.member_rows(),('AXIAL_ONLY_SCENARIO','OUTSIDE_SCENARIO_AXIAL_RANGE')):
            row.update(status=status,axial_utilization=.2)
        r=self.result();g=next(g for g in r['members'] if g['member_id']=='C_SYNTHETIC_1' and g['candidate_label']=='16Φ24')
        self.assertEqual(g['status'],'NO_PRIMARY_RADIAL_RESULT')
        self.assertEqual((g['target_count'],g['comparison_count']),(0,0))
        self.assertIn('OUTSIDE_SCENARIO_AXIAL_RANGE',g['primary_status_counts'])
        self.assertFalse(g['critical_comparisons_all_match'])
        self.assertEqual(r['member_scenario_count'],6)

    def test_spectral_filter_does_not_borrow_static_comparison(self):
        r=self.result(member_id='C_SYNTHETIC_1',output_case='RS_SUM')
        self.assertEqual((r['filtered_primary_assessment_count'],r['comparison_count']),(0,0))
        self.assertEqual(r['member_scenario_count'],3)
        self.assertTrue(all(g['status']=='NO_STATIC_STATES' for g in r['members']))

    def test_source_order_does_not_change_derived_hash(self):
        expected=self.result()['result_sha256']
        self.pmm['rows'].reverse();self.chain['candidates'].reverse();self.cages['members'].reverse()
        self.assertEqual(self.result()['result_sha256'],expected)

    def test_source_identity_policy_and_authority_reject_tampering(self):
        for kind in ('archive','demand','cage','state','candidate','axis','authority','policy','scope'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='archive':self.pmm['source_archive_sha256']='OTHER'
                elif kind=='demand':self.pmm['source_demand_result_sha256']='OTHER'
                elif kind=='cage':self.pmm['source_cages_result_sha256']='OTHER'
                elif kind=='state':self.pmm['rows'][0]['native_values']['M2']+=1
                elif kind=='candidate':self.pmm['rows'][0]['candidate_id']='OTHER'
                elif kind=='axis':self.pmm['axis_convention']='SWAPPED'
                elif kind=='authority':self.pmm['formal_compliance']='PROVEN'
                elif kind=='policy':self.pmm['numerical_policy']['moment_relative_tolerance']=.02
                else:self.pmm['pmm_population_reduced']=True
                with self.assertRaises(BankError):self.result()

    def test_population_and_numeric_malformations_are_rejected(self):
        for kind in ('missing','duplicate','nan','ratio','refinement','status'):
            with self.subTest(kind=kind):
                self.setUp();row=self.pmm['rows'][0]
                if kind=='missing':self.pmm['rows'].pop()
                elif kind=='duplicate':self.pmm['rows'].append(deepcopy(row))
                elif kind=='nan':row['radial_capacity_kNm']=float('nan')
                elif kind=='ratio':row['utilization']*=2
                elif kind=='refinement':row['refinement']['capacity_kNm'][0]*=.5
                else:row['status']='PASS'
                with self.assertRaises(BankError):self.result()
