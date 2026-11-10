"""Analytic oracles independent of the production PMM implementation."""
from copy import deepcopy
from dataclasses import replace
import json
import math
import unittest
from unittest.mock import patch

from tbdy_next.column_engine.section_reference import (
    ReferenceSection, rectangle_resultants, disk_resultants, reference_state,
    reference_radial_capacity, _radial_level, FORCE_TOL_N, DIRECTION_ABS_TOL_NMM, DIRECTION_REL_TOL)


class IndependentReferenceOracles(unittest.TestCase):
    def setUp(self):
        self.section=ReferenceSection(400,400,tuple((x,y,1000) for x in (-150,150) for y in (-150,150)),17,.82,400)

    def test_rectangle_half_area_and_native_axes_have_closed_form(self):
        area,q2,q3=rectangle_resultants(400,600,1,0,0)
        self.assertEqual((20*area,20*q3,20*q2),(2400000,0,240000000))
        for sign in (-1,1):
            a,x,y=rectangle_resultants(400,600,0,sign,0)
            self.assertAlmostEqual(a,120000)
            self.assertAlmostEqual(x,0)
            self.assertAlmostEqual(y,sign*18000000)

    def test_rectangle_oblique_triangle_and_empty_full_have_closed_form(self):
        a,q2,q3=rectangle_resultants(400,400,.6,.8,180)
        triangle=125*(500/3)/2
        self.assertAlmostEqual(a,triangle)
        self.assertAlmostEqual(q2,triangle*1300/9)
        self.assertAlmostEqual(q3,triangle*475/3)
        self.assertEqual(rectangle_resultants(400,600,1,0,1000),(0,0,0))
        self.assertEqual(rectangle_resultants(400,600,1,0,-1000),(240000,0,0))

    def test_gaussian_disk_area_and_first_moment_match_half_disk_oracle(self):
        area=100*math.pi
        a,q=disk_resultants(area,0,32)
        self.assertAlmostEqual(20*a/1000,math.pi,delta=1e-10)
        self.assertAlmostEqual(20*a*80/1e6,.08*math.pi,delta=1e-10)
        self.assertAlmostEqual(20*q/1e6,20*(2000/3)/1e6,delta=1e-8)
        self.assertEqual(disk_resultants(area,10,8),(0,0))
        self.assertEqual(disk_resultants(area,-10,8),(area,0))

    def test_disk_refines_against_independent_integral(self):
        radius=12;cut=3;area=math.pi*radius**2
        expected=radius**2*math.acos(cut/radius)-cut*math.sqrt(radius**2-cut**2)
        first=2/3*(radius**2-cut**2)**1.5
        errors=[]
        for panels in (8,16,32):
            a,q=disk_resultants(area,cut,panels)
            errors.append(abs(q-first));self.assertAlmostEqual(a,expected,delta=.001)
        self.assertGreater(errors[0],errors[1]);self.assertGreater(errors[1],errors[2])
        self.assertLess(errors[-1],.001)

    def test_half_section_steel_and_net_concrete_oracle(self):
        for angle,axis in ((0,'m3_nmm'),(90,'m2_nmm')):
            r=reference_state(self.section,angle,200/.82)
            self.assertAlmostEqual(r['n_n'],1604000,delta=1e-6)
            self.assertAlmostEqual(r[axis],329200000,delta=.01)
            self.assertAlmostEqual(r['m2_nmm' if axis=='m3_nmm' else 'm3_nmm'],0,delta=.01)

    def test_oblique_partial_bar_and_distinct_block_neutral_axes(self):
        # Compression triangle .6*x2+.8*x3 >=180; bar center on BLOCK boundary.
        # c=100/.79; the bar strain is .003*(1-.79), not zero.
        area=100*math.pi
        s=ReferenceSection(400,400,((100,150,area),),20,.79,400)
        r=reference_state(s,math.degrees(math.atan2(.8,.6)),100/.79)
        triangle=125*(500/3)/2;half=area/2;first=2000/3;steel=126*area
        self.assertAlmostEqual(r['n_n'],20*(triangle-half)+steel,delta=.001)
        self.assertAlmostEqual(r['m2_nmm'],20*triangle*475/3+steel*150-20*(half*150+.8*first),delta=.1)
        self.assertAlmostEqual(r['m3_nmm'],20*triangle*1300/9+steel*100-20*(half*100+.6*first),delta=.1)

    def test_full_compression_and_tension_limits(self):
        full=reference_state(self.section,0,1e9)
        self.assertEqual((full['n_n'],full['m2_nmm'],full['m3_nmm']),(4252000,0,0))
        tension=reference_state(self.section,0,1e-9)
        self.assertAlmostEqual(tension['n_n'],-1600000,delta=.001)
        self.assertAlmostEqual(tension['m3_nmm'],0,delta=.01)

    def test_asymmetric_fixed_plane_sign_and_rectangle_axis_swap(self):
        section=ReferenceSection(400,600,((50,80,1000),),20,.79,400)
        full=reference_state(section,0,1e9)
        self.assertEqual((full['m2_nmm'],full['m3_nmm']),(380*1000*80,380*1000*50))
        reflected=replace(section,bars=((-50,80,1000),))
        self.assertEqual(reference_state(reflected,180,1e9)['m3_nmm'],-full['m3_nmm'])
        swapped=replace(section,local2_mm=600,local3_mm=400,bars=((80,50,1000),))
        a=reference_state(section,23,250);b=reference_state(swapped,67,250)
        self.assertAlmostEqual(a['n_n'],b['n_n'],delta=.001)
        self.assertAlmostEqual(a['m2_nmm'],b['m3_nmm'],delta=.1)
        self.assertAlmostEqual(a['m3_nmm'],b['m2_nmm'],delta=.1)

    def test_radial_root_recovers_hand_plane_without_production_solver(self):
        with patch('tbdy_next.column_engine.section_capacity.solver',side_effect=AssertionError('not independent')):
            r=reference_radial_capacity(self.section,1604000,0,-329200000)
        self.assertEqual(r['status'],'REFERENCE_OBSERVED_STABLE')
        self.assertAlmostEqual(r['capacity_knm'],329.2,delta=.0001)
        self.assertLessEqual(r['max_axial_residual_n'],FORCE_TOL_N)
        for h in r['history']:
            self.assertEqual(h['positive_root_count'],1)
            p=h['positive_roots'][0]
            self.assertLessEqual(p['direction_residual_nmm'],DIRECTION_ABS_TOL_NMM+DIRECTION_REL_TOL*p['capacity_nmm'])
            self.assertFalse(h['production_bracket_used'])
        self.assertFalse(r['continuous_error_bound_proven'])
        self.assertFalse(r['global_root_uniqueness_proven'])

    def test_zero_axial_force_is_pure_bending_not_zero_vector(self):
        r=reference_radial_capacity(self.section,0,20e6,10e6)
        self.assertEqual(r['status'],'REFERENCE_OBSERVED_STABLE')
        self.assertGreater(r['capacity_knm'],0)
        for args in ((0,0,0),(-1600000,1,0),(4252000,1,0),(float('nan'),1,1)):
            with self.subTest(args=args),self.assertRaises(ValueError):reference_radial_capacity(self.section,*args)

    def test_biaxial_reflection_and_cache_results_are_isolated(self):
        a=reference_radial_capacity(self.section,1e6,120e6,90e6)
        b=reference_radial_capacity(self.section,1e6,-120e6,-90e6)
        self.assertEqual(a,b)
        expected=deepcopy(a);a['history'][0]['positive_roots'].clear()
        self.assertEqual(reference_radial_capacity(self.section,1e6,120e6,90e6),expected)
        json.dumps(expected,allow_nan=False)

    def test_multiple_positive_roots_are_not_silently_selected(self):
        fake={'positive_root_count':2,'positive_roots':[{},{}]}
        with patch('tbdy_next.column_engine.section_reference._radial_level',return_value=fake):
            r=reference_radial_capacity(self.section,123456,12345,67890)
        self.assertEqual(r['status'],'REFERENCE_UNRESOLVED')
        self.assertIsNone(r['capacity_knm'])

    def test_direction_search_counts_all_observed_positive_roots_and_rejects_opposite_ray(self):
        def points(section,angle,n,panels):
            return {'m2_nmm':1e6*math.sin(math.radians(4*angle)),'m3_nmm':1e6,'axial_residual_n':0,'theta_deg':angle}
        with patch('tbdy_next.column_engine.section_reference._axial_root',side_effect=points):
            r=_radial_level(self.section,1e6,0,1,8,12)
        self.assertEqual(r['positive_root_count'],3)
        with patch('tbdy_next.column_engine.section_reference._axial_root',return_value={
                'm2_nmm':0,'m3_nmm':-1e6,'axial_residual_n':0}):
            r=_radial_level(self.section,1e6,0,1,8,12)
        self.assertEqual(r['positive_root_count'],0)

    def test_both_successive_refinements_must_pass_not_only_the_last(self):
        levels=[{'positive_root_count':1,'positive_roots':[{'capacity_nmm':c,'direction_residual_nmm':0}],
                 'max_axial_residual_n':0} for c in (1e6,1.1e6,1.1e6+1)]
        with patch('tbdy_next.column_engine.section_reference._radial_level',side_effect=levels):
            r=reference_radial_capacity(self.section,654321,98765,43210)
        self.assertEqual(r['status'],'REFERENCE_NOT_STABLE')
        self.assertGreater(r['differences_knm'][0],r['budgets_knm'][0])
        self.assertLess(r['differences_knm'][1],r['budgets_knm'][1])

    def test_invalid_geometry_or_missing_symmetry_cannot_authorize_radial_result(self):
        for bars in (((195,0,1000),),((0,0,1000),(10,0,1000))):
            with self.assertRaises(ValueError):replace(self.section,bars=bars)
        with self.assertRaisesRegex(ValueError,'SYMMETRY'):
            reference_radial_capacity(replace(self.section,bars=((50,0,1000),)),100,1,1)
