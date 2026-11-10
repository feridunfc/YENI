from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from column_bank_fixture import encoded,zipped
from column_stability_fixture import StiffnessBank
from tbdy_next.column_engine.native_archive import NativeArchive,BankError
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.column_prechecks import build_column_prechecks
from tbdy_next.column_engine.column_stability import build_column_stability
from tbdy_next.column_engine.store import read_column_bank,save_column_bank
from tbdy_next.column_engine.ts500_column import (rectangle_properties,minimum_eccentricity_mm,
    evaluate_slenderness,effective_stiffness_nmm2,euler_load_kn,moment_magnification_factors,
    eq729_length_comparison,SWAY_PREVENTED,SWAY_PERMITTED)


def assess(raw):
    bank=recover_column_bank(raw)
    with closing(NativeArchive(raw)) as archive:
        chain=build_demand_chain(bank,archive); prechecks=build_column_prechecks(bank,chain)
        before=deepcopy((bank,chain,prechecks))
        result=build_column_stability(bank,chain,prechecks,archive)
    assert (bank,chain,prechecks)==before
    return result,chain


class SectionAndEccentricityTests(unittest.TestCase):
    def test_source_geometry_stiffness_and_exact_vs_approximate_radius(self):
        result,_=assess(StiffnessBank().build())
        self.assertEqual((result['selected_member_count'],result['distinct_section_count'],result['native_property_match_count']),(2,1,10))
        row=result['sections'][0]; sec=row['section']; e=row['elastic']
        self.assertEqual(sec['area_mm2'],640000)
        self.assertAlmostEqual(sec['i22_mm4']/1e9,34.13333333333333)
        self.assertAlmostEqual(sec['r22_exact_mm'],230.9401076758503)
        self.assertEqual(sec['r22_ts500_approx_mm'],240)
        self.assertEqual(e['observed_E_MPa'],34000)
        self.assertAlmostEqual(e['gross_EI22_kNcm2']/1e9,11.60533333333333)
        self.assertFalse(e['effective_stiffness_proven'])

    def test_unequal_rectangle_axis_mapping_and_reference_units(self):
        fixture=StiffnessBank(); fixture.unequal_rectangle(); fixture.set_static_vector([-1000,0,0,0,20,40])
        result,_=assess(fixture.build()); sec=result['sections'][0]['section']
        self.assertAlmostEqual(sec['i22_mm4']/1e9,14.4)
        self.assertAlmostEqual(sec['i33_mm4']/1e9,25.6)
        axes=result['eccentricity']['rows'][0]['axes']
        self.assertEqual([a['e_min_mm'] for a in axes],['33','39'])
        self.assertEqual([a['reference_minimum_moment_kNcm'] for a in axes],['3300','3900'])
        self.assertEqual([a['status'] for a in axes],['BELOW_REFERENCE','AT_OR_ABOVE_REFERENCE'])
        self.assertEqual([a['source_eccentricity_mm'] for a in axes],['20','40'])

    def test_equality_is_inclusive_and_nearby_smaller_native_value_is_below(self):
        for sign in (-1,1):
            fixture=StiffnessBank(); fixture.set_static_vector([-1000,0,0,0,sign*39,sign*38.99999999999999])
            result,_=assess(fixture.build()); axes=result['eccentricity']['rows'][0]['axes']
            self.assertEqual([a['status'] for a in axes],['AT_OR_ABOVE_REFERENCE','BELOW_REFERENCE'])

    def test_zero_and_tensile_axial_values_are_not_compression_checks(self):
        for p in (0,100):
            fixture=StiffnessBank(); fixture.set_static_vector([p,0,0,0,0,0])
            result,_=assess(fixture.build())
            self.assertEqual(result['eccentricity']['status_counts'],{'NONCOMPRESSION_NOT_APPLICABLE':16})
            self.assertTrue(all(a['source_eccentricity_mm'] is None for r in result['eccentricity']['rows'] for a in r['axes']))

    def test_noninteger_dimension_unit_conversion_does_not_turn_equality_into_failure(self):
        for t2,moment in ((.3017,24.051),(.8034,39.102)):
            fixture=StiffnessBank(); fixture.set_static_vector([-1000,0,0,0,moment,40])
            fixture.calls[('PropFrame.GetRectangle','frame_section','RECT_SYNTHETIC')]['raw_response'][3]=t2
            fixture.omitted.add(('PropFrame.GetSectProps','frame_section','RECT_SYNTHETIC'))
            result,_=assess(fixture.build())
            row=result['eccentricity']['rows'][0]['axes'][0]
            self.assertEqual(row['status'],'AT_OR_ABOVE_REFERENCE')
            self.assertEqual(row['e_min_mm'],str(moment))

    def test_every_station_is_retained_without_adjusting_a_source_vector(self):
        result,chain=assess(StiffnessBank().build())
        original={r['state_id']:r for r in chain['candidates']}
        self.assertEqual(len(result['eccentricity']['rows']),8)
        for row in result['eccentricity']['rows']:
            for key in ('native_key','native_values','domain_values','source_row_id'):
                self.assertEqual(row[key],original[row['state_id']][key])
            self.assertFalse(row['design_end_binding_proven'])
            self.assertFalse(row['final_design_eligible'])
            self.assertIsNone(row['adjusted_demand_vector'])

    def test_offsets_do_not_supply_regulatory_length_k_or_magnification(self):
        result,_=assess(StiffnessBank().build())
        row=result['sections'][0]
        self.assertEqual((row['lengths']['object_i_j_m'],row['lengths']['output_face_span_m']),(4,3.3))
        for key in ('ts500_free_length_ln_mm','effective_length_factor_k','effective_length_lk_mm'):
            self.assertIsNone(row['lengths'][key])
        self.assertIsNone(row['second_order']['magnification_factor'])
        self.assertFalse(result['actual_second_order_applied'])

    def test_missing_geometry_keeps_population_and_unresolved_reference_rows(self):
        fixture=StiffnessBank(); fixture.omitted.add(('PropFrame.GetRectangle','frame_section','RECT_SYNTHETIC'))
        result,_=assess(fixture.build())
        self.assertEqual(len(result['sections']),2)
        self.assertEqual(result['calculated_section_count'],0)
        self.assertEqual(result['eccentricity']['status_counts'],{'NOT_PROVEN':16})

    def test_property_mismatch_is_visible_and_not_an_effective_stiffness_approval(self):
        fixture=StiffnessBank()
        fixture.calls[('PropFrame.GetSectProps','frame_section','RECT_SYNTHETIC')]['raw_response'][4]=.04
        result,_=assess(fixture.build()); row=result['sections'][0]
        self.assertEqual(row['property_comparison_status'],'NUMERICAL_MISMATCH')
        self.assertEqual(row['property_comparisons'][1]['status'],'NUMERICAL_MISMATCH')
        self.assertIsNone(row['second_order']['effective_ei_nmm2'])

    def test_missing_invalid_and_wrong_unit_elastic_data_do_not_erase_other_calculations(self):
        for defect in ('missing','zero','units'):
            fixture=StiffnessBank(); key=('PropMaterial.GetMPIsotropic','material','CONCRETE_SYNTHETIC')
            if defect=='missing': fixture.omitted.add(key)
            elif defect=='zero': fixture.calls[key]['raw_response'][0]=0
            else: fixture.calls[key]['units_code']=5
            result,_=assess(fixture.build())
            self.assertEqual(result['elastic_member_count'],0)
            self.assertEqual(result['native_property_match_count'],10)
            self.assertEqual(result['eccentricity']['state_count'],8)

    def test_corrupt_optional_property_payload_is_isolated(self):
        fixture=StiffnessBank(); files=fixture.files()
        index=[json.loads(x) for x in files['shard-index.jsonl'].splitlines()]
        item=next(x for x in index if x['api']=='PropFrame.GetSectProps')
        path=item['path']; files[path]=b'not a gzip stream'; item['sha256']=sha256(files[path]).hexdigest()
        files['shard-index.jsonl']=b'\n'.join(map(encoded,index))
        manifest=json.loads(files['archive-manifest.json'])
        for name in (path,'shard-index.jsonl'):
            manifest['files'][name]={'sha256':sha256(files[name]).hexdigest(),'bytes':len(files[name])}
        files['archive-manifest.json']=encoded(manifest)
        result,_=assess(zipped(files))
        self.assertEqual(result['native_property_match_count'],0)
        self.assertEqual(result['elastic_member_count'],2)
        self.assertEqual(result['eccentricity']['state_count'],8)

    def test_cross_source_precheck_binding_is_rejected(self):
        raw=StiffnessBank().build(); bank=recover_column_bank(raw)
        with closing(NativeArchive(raw)) as archive:
            chain=build_demand_chain(bank,archive); pre=build_column_prechecks(bank,chain)
            pre['source_demand_result_sha256']='ANOTHER_RESULT'
            with self.assertRaisesRegex(BankError,'BINDING'):
                build_column_stability(bank,chain,pre,archive)


class Ts500ArithmeticTests(unittest.TestCase):
    def test_slenderness_negligibility_limits_and_general_analysis_boundary(self):
        for value,status in ((22,'NEGLECT_LIMIT_MET_NUMERICALLY'),(22.0001,'MOMENT_MAGNIFICATION_REQUIRED'),
                             (100,'MOMENT_MAGNIFICATION_REQUIRED'),(100.0001,'GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED')):
            result=evaluate_slenderness(free_length_ln_mm=value*100,k=1,radius_mm=100,sway=SWAY_PERMITTED)
            self.assertEqual(result['status'],status)
        r=evaluate_slenderness(free_length_ln_mm=2000,k=1.5,radius_mm=100,sway=SWAY_PREVENTED,signed_end_moment_ratio=0)
        self.assertEqual((r['lk_mm'],r['neglect_limit']),(3000,34))

    def test_missing_end_ratio_is_not_invented(self):
        result=evaluate_slenderness(free_length_ln_mm=3000,k=1,radius_mm=100,sway=SWAY_PREVENTED)
        self.assertEqual(result['status'],'SIGNED_END_MOMENT_RATIO_REQUIRED')
        self.assertIsNone(result['neglect_limit'])

    def test_effective_ei_and_euler_independent_hand_values(self):
        ei=effective_stiffness_nmm2(ec_mpa=30000,ic_mm4=100000000,creep_ratio=.5,method='TS500_7_21')
        self.assertEqual(ei,800000000000)
        self.assertAlmostEqual(euler_load_kn(effective_ei_nmm2=ei,effective_length_lk_mm=3000),877.2981689857207)
        ei20=effective_stiffness_nmm2(ec_mpa=30000,ic_mm4=100000000,creep_ratio=.5,method='TS500_7_20',es_mpa=200000,is_mm4=2000000)
        self.assertAlmostEqual(ei20/1e11,6.666666666666667)

    def test_beta_oracle_places_one_point_three_in_numerator_of_load_ratio(self):
        r=moment_magnification_factors(nd_kn=500,nk_kn=1000,sway=SWAY_PREVENTED,horizontal_load_between_ends=True)
        self.assertAlmostEqual(r['beta'],20/7)
        self.assertNotAlmostEqual(r['beta'],1.625)
        self.assertEqual(r['final_factor'],r['beta'])
        self.assertEqual(r['formal_compliance'],'NOT_PROVEN')

    def test_nonpositive_denominator_blocks_without_finite_factor(self):
        for nd in (1000,1001):
            r=moment_magnification_factors(nd_kn=nd,nk_kn=1300,sway=SWAY_PREVENTED,horizontal_load_between_ends=True)
            self.assertEqual(r['status'],'BLOCKED')
            self.assertIsNone(r['final_factor']); self.assertIsNone(r['beta'])

    def test_cm_lower_bound_and_transverse_load_basis(self):
        r=moment_magnification_factors(nd_kn=500,nk_kn=1000,sway=SWAY_PREVENTED,
            horizontal_load_between_ends=False,signed_end_moment_ratio=-1)
        self.assertEqual(r['cm'],.4); self.assertAlmostEqual(r['beta'],8/7)
        with self.assertRaisesRegex(BankError,'TRANSVERSE_LOAD_BASIS'):
            moment_magnification_factors(nd_kn=500,nk_kn=1000,sway=SWAY_PREVENTED,signed_end_moment_ratio=1)

    def test_story_limit_is_inclusive_and_eq729_is_not_silently_resolved(self):
        args=dict(nd_kn=500,nk_kn=2000,sway=SWAY_PERMITTED,story_nk_kn=1000)
        r=moment_magnification_factors(**args,story_nd_kn=450)
        self.assertAlmostEqual(r['beta_story'],200/83)
        self.assertEqual(r['status'],'EQ729_DECISION_NOT_PROVEN'); self.assertIsNone(r['final_factor'])
        self.assertEqual(moment_magnification_factors(**args,story_nd_kn=450.0000000001)['status'],'BLOCKED')

    def test_eq729_separates_free_and_effective_length_without_choosing_a_policy(self):
        r=eq729_length_comparison(free_length_ln_mm=600,effective_length_lk_mm=1200,radius_mm=10,
            nd_kn=1000,fck_mpa=40,area_mm2=100000)
        self.assertEqual(r['threshold'],70)
        self.assertFalse(r['free_length_reading_requires_product'])
        self.assertTrue(r['printed_symbol_reading_requires_product'])
        self.assertFalse(r['product_authorized'])

    def test_invalid_units_inputs_and_missing_policy_fail_closed(self):
        for value in (True,0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): rectangle_properties(value,800)
        with self.assertRaises(ValueError): minimum_eccentricity_mm(0)
        with self.assertRaises(ValueError): evaluate_slenderness(free_length_ln_mm=3000,k=1,radius_mm=100,sway='UNKNOWN')
        for rm in (-.1,1.0001,None):
            with self.assertRaises(ValueError): effective_stiffness_nmm2(ec_mpa=30000,ic_mm4=1e8,creep_ratio=rm,method='TS500_7_21')


class StabilityStoreTests(unittest.TestCase):
    def test_filters_readonly_files_and_cache_copy_boundaries(self):
        with TemporaryDirectory() as temp:
            root=Path(temp); source=root/'source.zip'; source.write_bytes(StiffnessBank().build())
            saved=save_column_bank(source,root/'receipts'); run=saved['run_id']
            def hashes(): return {str(p):sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
            before=hashes()
            report=read_column_bank(root/'receipts',run,view='stiffness',member_id='C_SYNTHETIC_1')
            self.assertEqual(report['demand_page']['total'],1)
            self.assertNotIn('rows',report['column_stability']['eccentricity'])
            with self.assertRaisesRegex(BankError,'CASE_FILTER_NOT_APPLICABLE'):
                read_column_bank(root/'receipts',run,view='stiffness',output_case='SUM')
            rows=read_column_bank(root/'receipts',run,view='eccentricity',member_id='C_SYNTHETIC_2',output_case='SUM',offset=1,limit=2)
            self.assertEqual((rows['demand_page']['total'],len(rows['demand_page']['rows'])),(4,2))
            rows['demand_page']['rows'][0]['axes'][0]['e_min_mm']='999'
            full=read_column_bank(root/'receipts',run,full=True)
            self.assertEqual(len(full['column_stability']['eccentricity']['rows']),8)
            self.assertEqual(full['column_stability']['eccentricity']['rows'][1]['axes'][0]['e_min_mm'],'39')
            self.assertEqual(read_column_bank(root/'receipts',run,view='eccentricity',output_case='RS_SUM')['demand_page']['total'],0)
            self.assertEqual(hashes(),before)


if __name__=='__main__': unittest.main()
