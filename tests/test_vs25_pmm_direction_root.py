"""Fixed-plane hand oracles and the six archived PMM discrepancy cases."""
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from tbdy_next.column_engine.section_capacity import (
    Bar,Material,Section,RadialSolver,_Curve,_radial,_direction_root,perimeter)

FIXTURE=json.loads(Path(__file__).with_name('vs25_pmm_regression_cases.json').read_text(encoding='utf-8'))


def regression_section(row):
    model=next(m for m in FIXTURE['models'] if m['reference_model_id']==row['reference_model_id'])
    p=model['parameters']
    return Section(p['local2_mm'],p['local3_mm'],tuple(Bar(*b) for b in p['bars']),Material(**model['source_material']))


class DirectionRootOracles(unittest.TestCase):
    def setUp(self):
        self.section=Section(400,400,tuple(Bar(x,y,1000) for x in (-150,150) for y in (-150,150)),Material(30,20,400))
        # nx=.6, ny=.8, block boundary .6*x2+.8*x3=180. Only the
        # (+150,+150) bar is in the concrete triangle, entirely, at 255.6 MPa.
        # Other bars yield in tension. These are direct area/centroid sums.
        area=125*(500/3)/2
        self.n=17*(area-1000)+(255.6-3*400)*1000
        self.m2=17*area*(475/3)+(255.6+400-17)*1000*150
        self.m3=17*area*(1300/9)+(255.6+400-17)*1000*150
        self.capacity=math.hypot(self.m2,self.m3)/1e6

    def assess(self,scale=.5):return RadialSolver(self.section).assess(self.n,scale*self.m2,scale*self.m3)

    def test_off_grid_closed_form_plane_recovers_axial_and_biaxial_equilibrium(self):
        r=self.assess();root=r['refinement']['direction_root'];point=root['point']
        self.assertEqual(r['status'],'WITHIN_SCENARIO_SURFACE')
        self.assertAlmostEqual(r['radial_capacity_kNm'],173.3891114749959,delta=.0003)
        self.assertAlmostEqual(r['utilization'],.5,delta=1e-6)
        self.assertAlmostEqual(point['theta_deg'],math.degrees(math.atan2(.8,.6)),delta=.002)
        self.assertAlmostEqual(point['c_mm'],100/.82,delta=.002)
        self.assertLessEqual(abs(point['n_n']-self.n),1)
        self.assertLessEqual(root['direction_residual_nmm'],1000)
        self.assertFalse(root['interpolated_strain_plane_used'])
        self.assertFalse(root['global_root_uniqueness_proven'])

    def test_all_signed_quadrants_and_demand_scales_preserve_fixed_n_capacity(self):
        for sign2,sign3 in ((1,1),(1,-1),(-1,1),(-1,-1)):
            for scale in (.25,2):
                with self.subTest(signs=(sign2,sign3),scale=scale):
                    r=RadialSolver(self.section).assess(self.n,sign2*scale*self.m2,sign3*scale*self.m3)
                    self.assertAlmostEqual(r['radial_capacity_kNm'],self.capacity,delta=.0003)
                    self.assertAlmostEqual(r['utilization'],scale,delta=1e-5)
                    self.assertEqual(r['status'],'WITHIN_SCENARIO_SURFACE' if scale<1 else 'EXCEEDS_SCENARIO_SURFACE')

    def test_off_grid_boundary_band_remains_unresolved_on_both_sides(self):
        for scale in (.9999,1.0001):
            r=self.assess(scale)
            self.assertEqual(r['reason'],'NEAR_NUMERICAL_SURFACE_BOUNDARY')
            self.assertIsNone(r['utilization'])
            self.assertAlmostEqual(r['trial_utilization'],scale,delta=1e-5)
            self.assertEqual(r['refinement']['direction_root']['status'],'MOMENT_DIRECTION_ROOT_RESOLVED')

    def test_cardinal_root_reuses_physical_endpoint_without_angle_iteration(self):
        for m2,m3 in ((0,1e8),(-1e8,0)):
            r=RadialSolver(self.section).assess(1604000,m2,m3);root=r['refinement']['direction_root']
            self.assertAlmostEqual(r['radial_capacity_kNm'],329.2,delta=.001)
            self.assertEqual((root['iterations'],root['evaluated_point_count']),(0,2))
            self.assertIn(root['point']['theta_deg'],(0,90))

    def test_different_initial_angular_grids_resolve_the_same_physical_point(self):
        results=[]
        for counts in ((24,48,96),(72,144,288)):
            with patch('tbdy_next.column_engine.section_capacity.ANGLE_COUNTS',counts):results.append(self.assess())
        self.assertNotEqual(results[0]['refinement']['coarse_minimum_capacity_kNm'],results[1]['refinement']['coarse_minimum_capacity_kNm'])
        self.assertAlmostEqual(results[0]['radial_capacity_kNm'],results[1]['radial_capacity_kNm'],delta=.001)

    def test_unequal_rectangle_axis_exchange_preserves_direction_root_capacity(self):
        bars,_,_=perimeter(600,800,40,12,28)
        a=Section(600,800,bars,self.section.material)
        b=Section(800,600,tuple(Bar(p.x3,p.x2,p.area) for p in bars),self.section.material)
        ra=RadialSolver(a).assess(1e6,100e6,-200e6);rb=RadialSolver(b).assess(1e6,-200e6,100e6)
        self.assertAlmostEqual(ra['radial_capacity_kNm'],rb['radial_capacity_kNm'],delta=.001)
        self.assertAlmostEqual(ra['refinement']['direction_root']['point']['theta_deg']+
            rb['refinement']['direction_root']['point']['theta_deg'],90,delta=.001)

    def test_all_six_archived_mismatches_close_without_changing_comparison_budget(self):
        self.assertEqual(len(FIXTURE['cases']),6)
        for row in FIXTURE['cases']:
            with self.subTest(member=row['member_id'],cage=row['candidate_label']):
                v=row['native_values'];r=RadialSolver(regression_section(row)).assess(-v['P']*1000,v['M2']*1e6,v['M3']*1e6)
                self.assertGreater(abs(row['primary_capacity_knm']-row['reference_capacity_knm']),row['comparison_budget_knm'])
                self.assertAlmostEqual(r['radial_capacity_kNm'],row['reference_capacity_knm'],delta=.001)
                self.assertLessEqual(r['refinement']['max_axial_residual_n'],1)

    def test_stable_coarse_steps_are_retained_but_no_longer_used_as_capacity(self):
        row=next(r for r in FIXTURE['cases'] if r['member_id']=='72');v=row['native_values']
        r=RadialSolver(regression_section(row)).assess(-v['P']*1000,v['M2']*1e6,v['M3']*1e6);e=r['refinement']
        self.assertEqual(e['status'],'OBSERVED_STABLE_AT_BOTH_STEPS')
        self.assertTrue(all(d<=b for d,b in zip(e['differences_kNm'],e['budgets_kNm'])))
        self.assertGreater(e['root_minus_coarse_minimum_kNm'],row['comparison_budget_knm'])
        self.assertEqual(e['selected_capacity_kNm'],r['radial_capacity_kNm'])
        self.assertNotEqual(min(e['capacity_kNm']),r['radial_capacity_kNm'])
        self.assertFalse(e['continuous_error_bound_proven'])

    def test_distinct_sampled_intersections_at_equal_radius_are_ambiguous(self):
        points=[{'m2_nmm':x,'m3_nmm':y,'theta_deg':a} for x,y,a in ((1e6,0,0),(0,1e6,45),(1e6,0,90))]
        self.assertIsNone(_radial(points,math.sqrt(.5),math.sqrt(.5)))

    def test_adjacent_segments_touching_one_sampled_vertex_are_one_bracket(self):
        points=[{'m2_nmm':x,'m3_nmm':y,'theta_deg':a} for x,y,a in ((0,1e6,0),(1e6,1e6,45),(1e6,0,90))]
        result=_radial(points,math.sqrt(.5),math.sqrt(.5))
        self.assertIsNotNone(result);self.assertAlmostEqual(result[0],math.sqrt(2)*1e6)

    def test_missing_direction_sign_bracket_is_explicitly_unresolved(self):
        points=[_Curve(self.section,a).solve(1604000)[0] for a in (0,1.25)]
        r=_direction_root(self.section,1604000,math.sqrt(.5),math.sqrt(.5),{'left':points[0],'right':points[1]})
        self.assertEqual(r['reason'],'DIRECTION_ROOT_SIGN_BRACKET_MISSING');self.assertIsNone(r['point'])

    def test_iteration_exhaustion_never_falls_back_to_polygon_capacity(self):
        with patch('tbdy_next.column_engine.section_capacity.DIRECTION_MAX_ITERATIONS',0):r=self.assess()
        self.assertEqual(r['status'],'NUMERIC_UNRESOLVED');self.assertEqual(r['reason'],'DIRECTION_ROOT_ITERATION_LIMIT')
        self.assertIsNone(r['radial_capacity_kNm']);self.assertIsNone(r['utilization'])
        self.assertEqual(len(r['refinement']['capacity_kNm']),3)

    def test_failed_fresh_axial_solve_cannot_return_a_refined_capacity(self):
        r=self.assess();ray=r['refinement']['finest_ray'];magnitude=math.hypot(self.m2,self.m3)
        with patch('tbdy_next.column_engine.section_capacity._Curve.solve',return_value=(None,'AXIAL_ROOT_UNRESOLVED')):
            root=_direction_root(self.section,self.n,self.m2/magnitude,self.m3/magnitude,ray)
        self.assertEqual(root['reason'],'DIRECTION_ROOT_AXIAL_ROOT_UNRESOLVED')
        self.assertIsNone(root['capacity_nmm'])

    def test_invalid_endpoint_resultants_fail_closed(self):
        ray=self.assess()['refinement']['finest_ray'];magnitude=math.hypot(self.m2,self.m3)
        for key,value in (('n_n',float('nan')),('n_n',self.n+10),('c_mm',0),('maximum_tensile_strain',.11)):
            bad=deepcopy(ray);bad['left'][key]=value
            root=_direction_root(self.section,self.n,self.m2/magnitude,self.m3/magnitude,bad)
            self.assertEqual(root['status'],'MOMENT_DIRECTION_ROOT_UNRESOLVED');self.assertIsNone(root['capacity_nmm'])

    def test_finite_components_with_overflowing_magnitude_do_not_emit_nonfinite_json(self):
        r=RadialSolver(self.section).assess(self.n,1.7e308,1.7e308)
        self.assertEqual(r['reason'],'MOMENT_MAGNITUDE_NOT_FINITE');json.dumps(r,allow_nan=False)

    def test_axial_hint_is_only_a_bracket_and_extreme_wrong_seeds_converge(self):
        theta=math.degrees(math.atan2(.8,.6))
        expected=_Curve(self.section,theta).solve(self.n)[0]
        for seed in (1e-100,1,100/.82,1e100):
            with self.subTest(seed=seed):
                point,reason=_Curve(self.section,theta).solve(self.n,seed_c=seed)
                self.assertIsNone(reason);self.assertLessEqual(abs(point['n_n']-self.n),1)
                self.assertAlmostEqual(point['c_mm'],100/.82,delta=.001)
                # At fixed angle, monotone increments of concrete/steel force
                # act inside radius R: ||ΔM|| <= R*|ΔN|.
                dm=math.hypot(point['m2_nmm']-expected['m2_nmm'],point['m3_nmm']-expected['m3_nmm'])
                self.assertLessEqual(dm,math.hypot(400,400)/2*abs(point['n_n']-expected['n_n'])+1e-4)

    def test_invalid_axial_hint_is_rejected(self):
        for value in (True,0,-1,float('nan'),float('inf')):
            with self.subTest(seed=value),self.assertRaises(ValueError):_Curve(self.section,40).solve(self.n,seed_c=value)

    def test_seeded_outside_axial_range_and_excessive_strain_fail_closed(self):
        for target in (-2e6,5e6):
            point,reason=_Curve(self.section,0).solve(target,seed_c=100)
            self.assertIsNone(point);self.assertEqual(reason,'AXIAL_ROOT_UNRESOLVED')
        for seed in (None,100):
            point,reason=_Curve(self.section,0).solve(-1599990,seed_c=seed)
            self.assertIsNone(point);self.assertEqual(reason,'STEEL_STRAIN_LIMIT_UNRESOLVED')


if __name__=='__main__':unittest.main()
