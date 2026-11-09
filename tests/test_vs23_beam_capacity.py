from copy import deepcopy
import math
import unittest
from tbdy_next.column_engine.beam_capacity import proposed_beam_cage,signed_beam_capacity
from tbdy_next.column_engine.section_capacity import Bar,Material,Section
from tbdy_next.column_engine.section_reference import ReferenceSection,_axial_root


def profile():
    return {'local2_height_mm':700,'local3_width_mm':600,'cover_top_centroid_mm':60,'cover_bottom_centroid_mm':60,
        'material':{'fck':35,'fcd':35/1.5,'fyd':500/1.15}}


class BeamCapacityTests(unittest.TestCase):
    def test_independent_analytic_elastic_compression_steel_oracle(self):
        # c=100,a=.82c=82; concrete=418200 N; net top steel=283000 N;
        # bottom steel=-701200 N. N=0 and moment=214123800 Nmm.
        section=Section(400,300,tuple(Bar(x,y,a) for x,a in ((150,500),(-150,876.5)) for y in (-100,100)),Material(30,20,400))
        result=signed_beam_capacity(section)
        self.assertAlmostEqual(result['positive_m3_knm'],214.1238,places=3)
        self.assertLess(abs(result['points'][0]['point']['n_n']),1)
        self.assertAlmostEqual(result['points'][0]['point']['c_mm'],100,places=3)
        self.assertNotAlmostEqual(result['positive_m3_knm'],-result['negative_m3_knm'],places=1)

    def test_vertical_mirror_swaps_signed_capacities_without_assuming_symmetry(self):
        bars=tuple(Bar(x,y,a) for x,a in ((150,500),(-150,876.5)) for y in (-100,100))
        material=Material(30,20,400);a=signed_beam_capacity(Section(400,300,bars,material))
        b=signed_beam_capacity(Section(400,300,tuple(Bar(-r.x2,r.x3,r.area) for r in bars),material))
        self.assertAlmostEqual(b['negative_m3_knm'],-214.1238,places=3)
        self.assertAlmostEqual(a['negative_m3_knm'],-b['positive_m3_knm'],places=6)

    def test_singly_reinforced_closed_form_without_clamping(self):
        # 2000 mm2 yielding in tension, d=540; compression block excludes steel.
        section=Section(600,300,tuple(Bar(-240,y,1000) for y in (-75,75)),Material(30,20,400))
        expected=800000*(540-(800000/(.85*20*300))/2)/1e6
        self.assertAlmostEqual(signed_beam_capacity(section)['positive_m3_knm'],expected,places=3)

    def test_source_cover_is_centroid_distance_not_column_cover(self):
        r=proposed_beam_cage(profile(),1200,800,20)
        self.assertEqual((r['top_count'],r['bottom_count']),(4,3))
        self.assertEqual({b['x2_mm'] for b in r['bars']},{290,-290})
        self.assertEqual(r['top_clear_cover_to_tie_mm'],40)
        self.assertFalse(r['selected_design']);self.assertFalse(r['physical_cage_proven'])

    def test_areas_ceil_exact_boundary_and_one_ulp_above(self):
        area=math.pi*20**2/4
        self.assertEqual(proposed_beam_cage(profile(),4*area,2*area,20)['top_count'],4)
        self.assertEqual(proposed_beam_cage(profile(),math.nextafter(4*area,math.inf),800,20)['top_count'],5)

    def test_narrow_section_does_not_compress_spacing_or_add_an_implicit_layer(self):
        p=profile();p['local3_width_mm']=180
        r=proposed_beam_cage(p,2000,2000,16)
        self.assertEqual(r['status'],'BEAM_PROPOSAL_BLOCKED');self.assertIsNone(r['capacity']);self.assertEqual(r['bars'],[])

    def test_opposite_faces_must_also_meet_clear_spacing_reference(self):
        p=profile();p['local2_height_mm']=150
        r=proposed_beam_cage(p,300,300,20)
        self.assertEqual(r['minimum_clear_spacing_mm'],10)
        self.assertEqual(r['status'],'BEAM_PROPOSAL_BLOCKED');self.assertIsNone(r['capacity'])

    def test_zero_required_area_has_no_division_or_zero_provided_assumption(self):
        r=proposed_beam_cage(profile(),0,0,16)
        self.assertEqual((r['top_count'],r['bottom_count']),(2,2))
        self.assertIsNone(r['top_source_area_ratio']);self.assertGreater(r['area_top_mm2'],0)

    def test_bad_area_diameter_cover_and_width_symmetry_rejected(self):
        for value in (None,True,float('nan'),-1):
            with self.subTest(value=value),self.assertRaises(ValueError):proposed_beam_cage(profile(),value,800,20)
        with self.assertRaises(ValueError):proposed_beam_cage(profile(),1200,800,18)
        p=profile();p['cover_top_centroid_mm']=10
        self.assertIsNone(proposed_beam_cage(p,1200,800,20)['capacity'])
        section=Section(400,300,(Bar(150,-80,500),Bar(-150,100,1000)),Material(30,20,400))
        with self.assertRaises(ValueError):signed_beam_capacity(section)

    def test_independent_strip_and_bisection_compare_both_signs_for_proposed_cage(self):
        p=profile();r=proposed_beam_cage(p,1700,1100,20);m=Material(**p['material'])
        reference=ReferenceSection(700,600,tuple((b['x2_mm'],b['x3_mm'],b['area_mm2']) for b in r['bars']),
            .85*m.fcd,m.k1,m.fyd)
        for angle,key in ((0,'positive_m3_knm'),(180,'negative_m3_knm')):
            point=_axial_root(reference,angle,0,32)
            self.assertLessEqual(abs(point['m3_nmm']/1e6-r['capacity'][key]),.002*abs(r['capacity'][key])+.002)

    def test_capacity_cache_result_is_not_mutable_by_consumer(self):
        section=Section(400,300,tuple(Bar(x,y,500) for x in (-150,150) for y in (-100,100)),Material(30,20,400))
        a=signed_beam_capacity(section);value=a['positive_m3_knm'];a['positive_m3_knm']=1
        self.assertEqual(signed_beam_capacity(section)['positive_m3_knm'],value)
