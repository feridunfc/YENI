"""Source-bound root evidence, independent plane replay and failure population."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch

from test_vs15_column_pmm import inputs
from tbdy_next.column_engine.column_pmm import build_column_pmm
from tbdy_next.column_engine.column_pmm_quality import build_column_pmm_quality
from tbdy_next.column_engine.native_archive import BankError
from tbdy_next.column_engine.section_reference import reference_radial_capacity


class RootEvidenceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,chain,_,stability,cages=inputs()
        cls.baseline=(chain,cages,stability,build_column_pmm(chain,cages,stability))
    def setUp(self):self.chain,self.cages,self.stability,self.pmm=deepcopy(self.baseline)
    def result(self):return build_column_pmm_quality(self.chain,self.cages,self.pmm)

    def test_solver_revision_and_unchanged_budgets_are_explicit(self):
        q=self.result();policy=self.pmm['numerical_policy']
        self.assertEqual(self.pmm['schema'],'tbdy.next.column-pmm-scenarios.v3')
        self.assertEqual(q['primary_solver_revision'],'VS25_DIRECTION_ROOT')
        self.assertEqual(policy['basis'],q['primary_capacity_basis'])
        self.assertEqual((policy['axial_tolerance_n'],policy['moment_absolute_tolerance_nmm'],policy['moment_relative_tolerance']),(1,1000,.002))
        self.assertEqual(policy['direction_absolute_tolerance_nmm'],1000)
        self.assertTrue(policy['final_capacity_from_strain_compatible_point'])
        self.assertEqual(q['numerical_policy']['comparison_relative_tolerance'],.002)
        self.assertFalse(q['numerical_policy']['primary_level_spread_added_to_budget'])
        self.assertEqual(q['primary_fixed_plane_validation']['recorded_point_check_count'],72)
        self.assertFalse(q['primary_fixed_plane_validation']['independent_root_search'])
        self.assertFalse(q['full_primary_population_independently_checked'])

    def test_false_plane_bracket_and_root_scope_are_rejected(self):
        for kind in ('c','theta','strain','endpoint_n','endpoint_m','empty_history','target_n','direction','iterations','scope','policy'):
            with self.subTest(kind=kind):
                self.setUp();r=self.pmm['rows'][0];e=r['refinement'];root=e['direction_root']
                if kind=='c':root['point']['c_mm']=1
                elif kind=='theta':
                    root['point']['theta_deg']=root['initial_bracket_theta_deg'][0]
                    root['final_bracket_theta_deg']=root['initial_bracket_theta_deg'][:]
                elif kind=='strain':root['point']['maximum_tensile_strain']=.09
                elif kind=='endpoint_n':e['finest_ray']['left']['n_n']=-1e20
                elif kind=='endpoint_m':e['finest_ray']['right']['m2_nmm']+=1e6
                elif kind=='empty_history':e['history']=[]
                elif kind=='target_n':root['target_n_n']+=1
                elif kind=='direction':root['direction_residual_nmm']=1001
                elif kind=='iterations':root['iterations']=True
                elif kind=='scope':root['interpolated_strain_plane_used']=True
                else:self.pmm['numerical_policy']['direction_absolute_tolerance_nmm']=1001
                with self.assertRaises(BankError):self.result()

    def test_coherently_scaled_moment_evidence_fails_independent_plane_replay(self):
        r=self.pmm['rows'][0];e=r['refinement'];root=e['direction_root'];point=root['point']
        for key in ('m2_nmm','m3_nmm'):point[key]*=.99
        u2,u3=root['folded_unit_direction'];capacity=point['m2_nmm']*u2+point['m3_nmm']*u3
        root['capacity_nmm']=capacity;root['direction_residual_nmm']=abs(point['m2_nmm']*u3-point['m3_nmm']*u2)
        r['radial_capacity_kNm']=capacity/1e6
        r['utilization']=math.hypot(r['native_values']['M2'],r['native_values']['M3'])/r['radial_capacity_kNm']
        e['selected_capacity_kNm']=capacity/1e6
        e['root_minus_coarse_minimum_kNm']=capacity/1e6-min(e['capacity_kNm'])
        e['root_minus_finest_polygon_kNm']=capacity/1e6-e['capacity_kNm'][-1]
        with self.assertRaisesRegex(BankError,'FIXED_PLANE_REPLAY_MISMATCH'):self.result()

    def test_wrong_material_cannot_reuse_root_resultants(self):
        self.cages['profiles'][0]['material']['fcd']*=1.1
        with self.assertRaisesRegex(BankError,'FIXED_PLANE_REPLAY_MISMATCH'):self.result()

    def test_point_replay_and_reference_search_call_no_production_solver(self):
        before=deepcopy(self.pmm)
        with (patch('tbdy_next.column_engine.section_capacity._Curve.evaluate',side_effect=AssertionError('production integration called')),
              patch('tbdy_next.column_engine.section_capacity.solver',side_effect=AssertionError('production solver called'))):
            q=self.result()
        self.assertEqual(q['status_counts'],{'NUMERICAL_COMPARISON_MATCH':6})
        self.assertEqual(self.pmm,before)
        self.assertFalse(q['primary_results_changed'])
        for r in q['rows']:
            self.assertIn('point',r['primary_direction_root'])
            self.assertFalse(r['reference']['production_capacity_solver_called'])

    def test_reference_disagreement_stays_visible_with_the_same_capacity_budget(self):
        def disagree(*args):
            r=reference_radial_capacity(*args);r['capacity_knm']*=1.01;r['utilization']/=1.01;return r
        with patch('tbdy_next.column_engine.column_pmm_quality.reference_radial_capacity',side_effect=disagree):q=self.result()
        self.assertEqual(q['status_counts'],{'NUMERICAL_COMPARISON_MISMATCH':6})
        self.assertTrue(all(r['absolute_difference_knm']>r['comparison_budget_knm'] for r in q['rows']))
        self.assertEqual(q['numerical_policy']['comparison_relative_tolerance'],.002)

    def test_root_failures_retain_full_population_and_cannot_become_empty_success(self):
        with patch('tbdy_next.column_engine.section_capacity.DIRECTION_MAX_ITERATIONS',0):
            self.pmm=build_column_pmm(self.chain,self.cages,self.stability)
        q=self.result()
        self.assertEqual(self.pmm['status_counts'],{'NUMERIC_UNRESOLVED':24})
        self.assertEqual((q['primary_total_assessment_count'],q['comparison_count']),(24,0))
        self.assertEqual(q['groups_without_radial_targets'],6)
        self.assertTrue(all(not g['critical_comparisons_all_match'] for g in q['members']))
        self.assertEqual(q['formal_compliance'],'NOT_PROVEN')


if __name__=='__main__':unittest.main()
