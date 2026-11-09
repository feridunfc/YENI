"""Independent section oracles and source-population/authority regressions."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from column_stability_fixture import StiffnessBank
from tbdy_next.column_engine.native_archive import NativeArchive,BankError
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.column_prechecks import build_column_prechecks
from tbdy_next.column_engine.column_stability import build_column_stability
from tbdy_next.column_engine.column_pmm import build_column_cages,build_column_pmm,cage_rows
from tbdy_next.column_engine.section_capacity import (Bar,Material,Section,perimeter,evaluate_state,
    solver,_Curve,FORCE_TOL_N)
from tbdy_next.column_engine.store import save_column_bank,read_column_bank


def inputs(fixture=None):
    raw=(fixture or StiffnessBank()).build();bank=recover_column_bank(raw)
    with closing(NativeArchive(raw)) as archive:
        chain=build_demand_chain(bank,archive);prechecks=build_column_prechecks(bank,chain)
        stability=build_column_stability(bank,chain,prechecks,archive)
        cages=build_column_cages(bank,chain,prechecks,archive)
    return bank,chain,prechecks,stability,cages


class SectionCapacityOracles(unittest.TestCase):
    def setUp(self):
        self.material=Material(30,20,400)
        self.section=Section(400,400,tuple(Bar(x,y,1000) for x in (-150,150) for y in (-150,150)),self.material)

    def test_full_compression_counts_only_net_concrete(self):
        state=evaluate_state(self.section,0,1e7)
        self.assertEqual(state['n_n'],4252000)
        self.assertEqual((state['m2_nmm'],state['m3_nmm']),(0,0))

    def test_half_block_hand_oracle_and_csi_positive_faces(self):
        for angle,axis in ((0,'m3_nmm'),(90,'m2_nmm')):
            state=evaluate_state(self.section,angle,200/.82)
            self.assertAlmostEqual(state['n_n'],1604000,places=6)
            self.assertAlmostEqual(state[axis],329200000,places=4)
            opposite='m2_nmm' if axis=='m3_nmm' else 'm3_nmm'
            self.assertAlmostEqual(state[opposite],0,places=5)

    def test_asymmetric_steel_exposes_csi_m3_sign(self):
        section=Section(400,400,(Bar(50,0,1000),),self.material)
        state=evaluate_state(section,0,1e7)
        self.assertEqual(state['m3_nmm'],(400-17)*1000*50)
        self.assertEqual(state['m2_nmm'],0)
        with self.assertRaisesRegex(ValueError,'SYMMETRY'): solver(section)

    def test_rotated_half_disk_first_moments_have_independent_triangle_oracle(self):
        # .6*x2+.8*x3 >= 180 cuts a triangle from the 400mm square.
        # Bar center(100,150) lies on that boundary: A_half=50pi,Q=2000/3.
        area=100*math.pi;bar=Bar(100,150,area)
        section=Section(400,400,(bar,),self.material)
        state=evaluate_state(section,math.degrees(math.atan2(.8,.6)),100/.82)
        triangle=125*(500/3)/2;centroid2=1300/9;centroid3=475/3
        steel=108*area;half=50*math.pi;first=2000/3
        self.assertAlmostEqual(state['n_n'],17*(triangle-half)+steel,places=6)
        self.assertAlmostEqual(state['m2_nmm'],17*triangle*centroid3+steel*150-17*(half*150+first*.8),places=5)
        self.assertAlmostEqual(state['m3_nmm'],17*triangle*centroid2+steel*100-17*(half*100+first*.6),places=5)

    def test_old_whole_bar_entry_jump_is_now_continuous_and_monotone(self):
        states=[evaluate_state(self.section,0,(50+d)/.82) for d in (-1e-7,0,1e-7)]
        self.assertLess(states[-1]['n_n']-states[0]['n_n'],1)
        self.assertLessEqual(states[0]['n_n'],states[1]['n_n'])
        self.assertLessEqual(states[1]['n_n'],states[2]['n_n'])
        state,reason=_Curve(self.section,0).solve(-260000)
        self.assertIsNone(reason)
        self.assertLessEqual(abs(state['n_n']+260000),FORCE_TOL_N)

    def test_disk_geometry_rejects_overlap_and_crossing_section_edge(self):
        for bars in ((Bar(195,0,1000),),(Bar(0,0,1000),Bar(10,0,1000))):
            with self.assertRaises(ValueError): Section(400,400,bars,self.material)

    def test_pure_axial_endpoints_and_zero_vector_never_emit_infinity(self):
        calc=solver(self.section)
        for n in (-1600000,4252000,0):
            r=calc.assess(n,0,0)
            self.assertEqual(r['status'],'AXIAL_ONLY_SCENARIO')
            self.assertIsNone(r['utilization']);self.assertIsNone(r['radial_capacity_kNm'])
            json.dumps(r,allow_nan=False)
        self.assertEqual(calc.assess(-1600001,0,0)['status'],'OUTSIDE_SCENARIO_AXIAL_RANGE')
        self.assertEqual(calc.assess(-1600000,1e6,0)['status'],'NUMERIC_UNRESOLVED')

    def test_radial_capacity_matches_hand_half_block_and_preserves_signed_symmetry(self):
        calc=solver(self.section)
        a=calc.assess(1604000,0,329.2e6);b=calc.assess(1604000,0,-329.2e6)
        self.assertAlmostEqual(a['radial_capacity_kNm'],329.2,delta=.001)
        self.assertEqual(a['status'],'NUMERIC_UNRESOLVED')
        self.assertEqual(a['reason'],'NEAR_NUMERICAL_SURFACE_BOUNDARY')
        self.assertEqual(a['utilization'],b['utilization'])
        self.assertLessEqual(a['refinement']['max_axial_residual_n'],1)
        self.assertFalse(a['refinement']['continuous_error_bound_proven'])

    def test_near_surface_on_both_sides_stays_undecided_but_distant_states_resolve(self):
        calc=solver(self.section)
        for scale in (.9999,1.0001):
            r=calc.assess(1604000,0,scale*329.2e6)
            self.assertEqual(r['reason'],'NEAR_NUMERICAL_SURFACE_BOUNDARY')
            self.assertIsNone(r['utilization'])
            self.assertIsNotNone(r['trial_utilization'])
        self.assertEqual(calc.assess(1604000,0,.98*329.2e6)['status'],'WITHIN_SCENARIO_SURFACE')
        self.assertEqual(calc.assess(1604000,0,1.02*329.2e6)['status'],'EXCEEDS_SCENARIO_SURFACE')

    def test_exceedance_is_distinct_from_numerical_failure(self):
        result=solver(self.section).assess(1604000,0,2*329.2e6)
        self.assertEqual(result['status'],'EXCEEDS_SCENARIO_SURFACE')
        with patch('tbdy_next.column_engine.section_capacity.MAX_ANGLE_COUNT',288),patch(
                'tbdy_next.column_engine.section_capacity.MOMENT_REL_TOL',0),patch(
                'tbdy_next.column_engine.section_capacity.MOMENT_ABS_TOL_NMM',0):
            unresolved=solver(self.section).assess(1604000,123e6,234e6)
        self.assertEqual(unresolved['status'],'NUMERIC_UNRESOLVED')
        self.assertIsNone(unresolved['utilization'])

    def test_unequal_section_rotation_swaps_moment_axes(self):
        bars,_,_=perimeter(600,800,40,10,24)
        a=Section(600,800,bars,self.material)
        b=Section(800,600,tuple(Bar(v.x3,v.x2,v.area) for v in bars),self.material)
        ra=solver(a).assess(1000000,100e6,-200e6);rb=solver(b).assess(1000000,-200e6,100e6)
        self.assertAlmostEqual(ra['radial_capacity_kNm'],rb['radial_capacity_kNm'],delta=.003)

    def test_adaptive_refinement_keeps_failed_history_and_original_tolerances(self):
        with patch('tbdy_next.column_engine.section_capacity.ANGLE_COUNTS',(8,16,32)):
            result=solver(self.section).assess(1604000,123e6,234e6)
        trace=result['refinement']
        self.assertGreater(len(trace['history']),1)
        self.assertEqual(trace['history'][0]['status'],'OBSERVED_NOT_STABLE')
        self.assertEqual(trace['status'],'OBSERVED_STABLE_AT_BOTH_STEPS')
        self.assertLessEqual(trace['max_axial_residual_n'],1)
        for step in trace['history']:
            for delta,budget in zip(step['differences_kNm'],step['budgets_kNm']):
                self.assertGreaterEqual(budget,.001)

    def test_kernel_rejects_bool_nonfinite_and_unsupported_concrete(self):
        for value in (True,float('nan'),float('inf')):
            with self.assertRaises(ValueError): solver(self.section).assess(value,0,0)
        with self.assertRaises(ValueError): Material(37,24,400)
        with self.assertRaises(ValueError): perimeter(800,800,40,10,24,n2=True)


class ProposedCageAndSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank,cls.chain,cls.prechecks,cls.stability,cls.cages=inputs()
        cls.pmm=build_column_pmm(cls.chain,cls.cages,cls.stability)

    def test_cover_geometry_areas_and_unknown_aggregate_remain_explicit(self):
        self.assertEqual(self.cages['bound_member_count'],2)
        for cage,diameter,center,spacing in zip(self.cages['candidates'],(24,28,32),(64,66,68),(144,139,134)):
            self.assertEqual(cage['bar_count'],16)
            self.assertEqual(len(cage['bars']),16)
            self.assertEqual(cage['center_offset_mm'],center)
            self.assertEqual(cage['minimum_clear_spacing_mm'],spacing)
            self.assertAlmostEqual(cage['as_cm2'],16*math.pi*(diameter/2)**2/100)
            self.assertEqual(cage['spacing_status'],'AGGREGATE_NOT_BOUND')
            self.assertGreaterEqual(cage['tie_diameter_mm'],diameter/3)
            self.assertTrue(cage['tie_diameter_reference_met'])
        self.assertEqual(self.cages['proposal_policy']['gamma_concrete'],1.5)
        self.assertFalse(self.cages['proposal_policy']['project_applicability_approved'])

    def test_all_static_vectors_x_all_three_cages_without_extrema_reduction(self):
        self.assertEqual((self.pmm['static_state_count'],self.pmm['assessment_count']),(8,24))
        by_id={r['state_id']:r for r in self.chain['candidates']}
        for state in self.pmm['rows']:
            source=by_id[state['state_id']]
            self.assertEqual(state['native_values'],source['native_values'])
            self.assertEqual(state['native_key'],source['native_key'])
            self.assertEqual(state['source_row_id'],source['source_row_id'])
            self.assertFalse(state['final_design_eligible'])
        self.assertFalse(self.pmm['pmm_population_reduced'])
        self.assertIsNone(self.pmm['selected_design'])
        self.assertFalse(self.pmm['actual_second_order_applied'])
        self.assertFalse(self.pmm['minimum_eccentricity_applied'])
        self.assertEqual(self.pmm['formal_compliance'],'NOT_PROVEN')

    def test_each_summary_identifies_exact_critical_station_without_calling_it_selected(self):
        for summary in self.pmm['members']:
            matched=[r for r in self.pmm['rows'] if r['member_id']==summary['member_id'] and r['candidate_label']==summary['candidate_label']]
            numeric=[r for r in matched if r['utilization'] is not None]
            self.assertEqual(summary['static_state_count'],4)
            self.assertEqual(summary['maximum_resolved_utilization'],max(r['utilization'] for r in numeric))
            self.assertFalse(summary['selected_design'])
            for critical in summary['critical_resolved_states']:
                self.assertIn(critical['state_id'],[r['state_id'] for r in matched])

    def test_model_bar_labels_are_not_interpreted_as_diameters(self):
        fixture=StiffnessBank();data=fixture.calls[('PropFrame.GetRebarColumn','column_section','RECT_SYNTHETIC')]
        data['raw_response'][8:10]=['not-a-number','arbitrary-tie-name']
        *_,cages=inputs(fixture)
        self.assertEqual(cages['bound_member_count'],2)
        self.assertFalse(cages['profiles'][0]['bar_labels_used_as_dimensions'])
        self.assertEqual([r['center_offset_mm'] for r in cages['candidates']],[64,66,68])

    def test_missing_native_rebar_and_lightweight_sources_are_blocked_not_defaulted(self):
        for mode in ('missing','lightweight'):
            fixture=StiffnessBank()
            if mode=='missing':fixture.omitted.add(('PropFrame.GetRebarColumn','column_section','RECT_SYNTHETIC'))
            else:fixture.calls[('PropMaterial.GetOConcrete','material','CONCRETE_SYNTHETIC')]['raw_response'][1]=True
            _,chain,_,stability,cages=inputs(fixture)
            self.assertEqual(cages['bound_member_count'],0)
            pmm=build_column_pmm(chain,cages,stability)
            self.assertEqual(pmm['status_counts'],{'BLOCKED_INPUTS':24})
            self.assertEqual(len(cage_rows(cages)),6)

    def test_source_binding_failure_and_duplicate_state_are_rejected(self):
        cages=deepcopy(self.cages);cages['source_archive_sha256']='OTHER'
        with self.assertRaises(BankError):build_column_pmm(self.chain,cages,self.stability)
        chain=deepcopy(self.chain);chain['candidates'].append(deepcopy(chain['candidates'][0]))
        with self.assertRaises(BankError):build_column_pmm(chain,self.cages,self.stability)
        chain=deepcopy(self.chain);chain['candidates'].pop()
        with self.assertRaises(BankError):build_column_pmm(chain,self.cages,self.stability)

    def test_building_pmm_never_mutates_accepted_source_results(self):
        before=deepcopy((self.chain,self.cages,self.stability))
        result=build_column_pmm(self.chain,self.cages,self.stability)
        self.assertEqual((self.chain,self.cages,self.stability),before)
        self.assertEqual(result['result_sha256'],self.pmm['result_sha256'])
        json.dumps(result,allow_nan=False)

    def test_archive_pages_full_export_and_cached_reads_keep_sqlite_unchanged(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.zip';source.write_bytes(StiffnessBank().build())
            saved=save_column_bank(source,root/'receipts');run=saved['run_id'];db=root/'receipts'/run/'column-bank.sqlite'
            old=sha256(db.read_bytes()).hexdigest()
            native=read_column_bank(root/'receipts',run)
            self.assertNotIn('column_pmm',native)
            report=read_column_bank(root/'receipts',run,view='cages',member_id='C_SYNTHETIC_1')
            self.assertEqual(report['demand_page']['total'],3)
            with self.assertRaises(BankError):read_column_bank(root/'receipts',run,view='cages',output_case='SUM')
            filtered=read_column_bank(root/'receipts',run,view='pmm',member_id='C_SYNTHETIC_2',output_case='SUM',offset=2,limit=3)
            self.assertEqual(filtered['demand_page']['total'],12)
            self.assertEqual(len(filtered['demand_page']['rows']),3)
            self.assertNotIn('rows',filtered['column_pmm'])
            full=read_column_bank(root/'receipts',run,full=True)
            self.assertEqual(len(full['column_pmm']['rows']),24)
            self.assertEqual(sha256(db.read_bytes()).hexdigest(),old)
            archive=root/'receipts'/run/'input.source';archive.write_bytes(archive.read_bytes()+b'changed')
            with self.assertRaises(BankError):read_column_bank(root/'receipts',run,view='pmm')


if __name__=='__main__':unittest.main()
