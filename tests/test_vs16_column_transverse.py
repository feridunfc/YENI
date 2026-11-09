"""Independent hand oracles, source identity and conservative authority tests."""
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
from test_vs15_column_pmm import inputs
from tbdy_next.column_engine.native_archive import NativeArchive,BankError
from tbdy_next.column_engine.column_transverse import (build_column_transverse,build_column_shear,
    proposed_layout,transverse_rows)
from tbdy_next.column_engine.transverse_kernel import confinement_reference,shear_reference,zero_concrete_gate
from tbdy_next.column_engine.store import save_column_bank,read_column_bank


def package(fixture=None):
    fixture=fixture or StiffnessBank()
    bank,chain,prechecks,stability,cages=inputs(fixture)
    with closing(NativeArchive(fixture.build())) as archive:
        transverse=build_column_transverse(chain,cages,archive)
    shear=build_column_shear(chain,cages,transverse)
    return chain,cages,transverse,shear


class TransverseHandOracles(unittest.TestCase):
    def shear(self,**changes):
        args=dict(n_compression_kn=1000,shear_kn=-500,area_mm2=640000,bw_mm=800,d_mm=736,
            fck_mpa=35,fywk_mpa=500,asw_mm2=180*math.pi,spacing_mm=100,gamma_c=1.5,gamma_s=1.15)
        return shear_reference(**(args|changes))

    def test_compression_hand_calculation_kn_mm_mpa(self):
        result=self.shear();branch=result['branches']['ts500']
        self.assertEqual(result['axial_factor'],1.109375)
        self.assertAlmostEqual(result['fctd_mpa'],1.380418616056577)
        self.assertAlmostEqual(result['vcr_kn'],586.098136005,places=8)
        self.assertAlmostEqual(branch['vc_kn'],468.878508804,places=8)
        self.assertAlmostEqual(branch['vw_kn'],1809.557368468,places=8)
        self.assertAlmostEqual(branch['vr_kn'],2278.435877272,places=8)
        self.assertAlmostEqual(branch['balance_asw_per_s_mm2_per_mm'],.097254659987,places=10)
        self.assertAlmostEqual(result['ts500_web_reference_kn'],3022.506666667,places=8)
        self.assertAlmostEqual(result['tbdy_brittle_reference_kn'],3218.347402006,places=8)
        self.assertEqual(result['ts500_web_column_applicability'],'NOT_PROVEN')

    def test_tension_reduces_vcr_using_positive_magnitude_with_negative_gamma(self):
        result=self.shear(n_compression_kn=-1000);branch=result['branches']['ts500']
        self.assertEqual(result['axial_factor'],.53125)
        self.assertAlmostEqual(result['vcr_kn'],280.666713017,places=8)
        self.assertAlmostEqual(branch['vc_kn'],224.533370413,places=8)
        self.assertAlmostEqual(branch['vr_kn'],2034.090738881,places=8)
        self.assertAlmostEqual(branch['balance_asw_per_s_mm2_per_mm'],.860833217459,places=10)
        self.assertAlmostEqual(result['branches']['zero_concrete']['balance_asw_per_s_mm2_per_mm'],1.5625)
        self.assertFalse(result['tension_gamma_zero_exception_applied'])

    def test_small_tension_exception_is_not_assumed_and_zero_axial_has_unit_factor(self):
        self.assertEqual(self.shear(n_compression_kn=0)['axial_factor'],1)
        small=self.shear(n_compression_kn=-100)
        self.assertEqual(small['axial_factor'],.953125)
        self.assertFalse(small['tension_gamma_zero_exception_applied'])

    def test_negative_cracking_factor_is_unknown_not_clamped_but_zero_scenario_survives(self):
        result=self.shear(n_compression_kn=-3000)
        self.assertLess(result['axial_factor'],0);self.assertIsNone(result['vcr_kn'])
        self.assertIsNone(result['branches']['ts500']['vr_kn'])
        self.assertEqual(result['branches']['ts500']['status'],'OUTSIDE_CRACKING_FORMULA_DOMAIN')
        self.assertAlmostEqual(result['branches']['zero_concrete']['vw_kn'],1809.557368468,places=8)
        self.assertIsNone(result['vc_branch_selected']);self.assertIsNone(result['ve_kn'])
        json.dumps(result,allow_nan=False)

    def test_shear_sign_is_preserved_and_force_balance_never_returns_negative_area_or_infinity(self):
        negative=self.shear(shear_kn=-100);positive=self.shear(shear_kn=100)
        self.assertEqual(negative['source_signed_v_kn'],-100)
        self.assertEqual(negative['branches'],positive['branches'])
        self.assertEqual(positive['branches']['ts500']['balance_asw_per_s_mm2_per_mm'],0)
        self.assertIsNone(positive['branches']['ts500']['balance_spacing_bound_mm'])

    def test_reference_equality_is_inclusive_without_promoting_next_float(self):
        capacity=self.shear()['branches']['zero_concrete']['vr_kn']
        self.assertEqual(self.shear(shear_kn=capacity)['branches']['zero_concrete']['status'],'WITHIN_REFERENCE_RESISTANCE')
        self.assertEqual(self.shear(shear_kn=math.nextafter(capacity,math.inf))['branches']['zero_concrete']['status'],'EXCEEDS_REFERENCE_RESISTANCE')

    def test_confinement_hand_oracle_does_not_select_reduced_axial_branch(self):
        r=confinement_reference(area_mm2=640000,core_area_mm2=518400,bk_mm=708,spacing_mm=100,
            fck_mpa=35,fywk_mpa=500,ash_mm2=180*math.pi)
        self.assertAlmostEqual(r['eq71_a_mm2'],348.755555555556)
        self.assertAlmostEqual(r['eq71_b_mm2'],371.7)
        self.assertAlmostEqual(r['high_axial_required_ash_mm2'],371.7)
        self.assertAlmostEqual(r['low_axial_required_ash_mm2'],247.8)
        self.assertIsNone(r['axial_branch_selected'])

    def gate(self,**changes):
        args=dict(in_confinement=True,earthquake_only_kn=500,seismic_total_kn=1000,n_compression_kn=1120,
            area_mm2=640000,fck_mpa=35)
        return zero_concrete_gate(**(args|changes))

    def test_zero_concrete_gate_strict_share_and_inclusive_axial_threshold(self):
        self.assertFalse(self.gate()['required'])
        self.assertTrue(self.gate(earthquake_only_kn=500.000001)['required'])
        self.assertFalse(self.gate(earthquake_only_kn=500.000001,n_compression_kn=1120.000001)['required'])
        self.assertFalse(self.gate(earthquake_only_kn=900,in_confinement=False)['required'])
        self.assertTrue(self.gate(earthquake_only_kn=-900,n_compression_kn=-1000)['required'])

    def test_missing_seismic_or_location_information_never_selects_vc(self):
        for key in ('in_confinement','earthquake_only_kn','seismic_total_kn','n_compression_kn'):
            result=self.gate(**{key:None})
            self.assertEqual(result,{'status':'NOT_PROVEN','required':None})
        with self.assertRaises(BankError):self.gate(seismic_total_kn=0)

    def test_kernel_rejects_invalid_nonfinite_and_unphysical_dimensions(self):
        for key in ('n_compression_kn','shear_kn','area_mm2','bw_mm','d_mm','fywk_mpa','spacing_mm','gamma_s'):
            for value in (True,float('nan'),float('inf')):
                with self.subTest(key=key,value=value),self.assertRaises(BankError):self.shear(**{key:value})
        for changes in ({'d_mm':800},{'asw_mm2':0},{'spacing_mm':-1},{'fywk_mpa':0}):
            with self.assertRaises(BankError):self.shear(**changes)
        with self.assertRaises(BankError):
            confinement_reference(area_mm2=100,core_area_mm2=100,bk_mm=10,spacing_mm=100,fck_mpa=35,fywk_mpa=500,ash_mm2=100)


class TransverseSourceAndGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.chain,cls.cages,cls.transverse,cls.shear=package()

    def test_outer_core_area_and_axis_dimensions_are_distinct_with_five_real_proposed_legs(self):
        for proposal,gap in zip(self.transverse['proposals'],(186,187,188)):
            layout=proposal['layout']
            self.assertEqual(layout['core_area_mm2'],518400)
            self.assertEqual(layout['core_axis_dimensions_mm'],[708,708])
            self.assertEqual(len(layout['legs']),10)
            self.assertEqual(sum(leg['kind']=='CROSSTIE' for leg in layout['legs']),6)
            for name,axis in proposal['axes'].items():
                self.assertAlmostEqual(axis['asw_mm2'],180*math.pi)
                self.assertAlmostEqual(axis['ash_mm2'],180*math.pi)
                self.assertEqual(axis['maximum_lateral_leg_spacing_mm'],gap)
                self.assertEqual(len(axis['asw_leg_ids']),5)
                self.assertTrue(all(leg.startswith('L'+name[-1]+'-') for leg in axis['asw_leg_ids']))
            self.assertIsNone(proposal['required_region_length_mm'])
            self.assertEqual(proposal['noncantilever_length_lower_bound_without_ln_mm'],1200)
            self.assertEqual(proposal['cantilever_length_reference_mm'],1600)
            self.assertIsNone(proposal['axial_branch_selected'])

    def test_unequal_rectangle_maps_shear_depth_and_perpendicular_bk(self):
        fixture=StiffnessBank();fixture.unequal_rectangle()
        # Independent native confinement material of 500 MPa for this oracle.
        fixture.calls[('PropMaterial.GetORebar_1','material','TIE_STEEL_SYNTHETIC')]['raw_response'][0]=500000
        _,_,transverse,_=package(fixture);p=transverse['proposals'][0]
        self.assertEqual(p['layout']['core_area_mm2'],374400)
        v2,v3=p['axes']['V2'],p['axes']['V3']
        self.assertEqual((v2['bw_mm'],v2['d_mm'],v2['bk_axis'],v2['bk_mm']),(600,736,3,508))
        self.assertEqual((v3['bw_mm'],v3['d_mm'],v3['bk_axis'],v3['bk_mm']),(800,536,2,708))
        self.assertAlmostEqual(v2['confinement']['high_axial_required_ash_mm2'],300.892307692,places=8)
        self.assertAlmostEqual(v3['confinement']['high_axial_required_ash_mm2'],419.353846154,places=8)

    def test_confinement_material_is_separate_from_longitudinal_material(self):
        p=self.transverse['profiles'][0]
        self.assertEqual(p['confinement_material'],'TIE_STEEL_SYNTHETIC')
        self.assertEqual(p['observed_fywk_mpa'],420)
        self.assertAlmostEqual(p['scenario_fywd_mpa'],365.2173913043478)
        self.assertAlmostEqual(self.cages['profiles'][0]['material']['fyd'],434.7826086956522)
        self.assertAlmostEqual(self.transverse['proposals'][0]['axes']['V2']['confinement']['high_axial_required_ash_mm2'],442.5)
        self.assertEqual(p['steel_grade_compliance'],'NOT_PROVEN')

    def test_missing_confinement_material_blocks_new_results_without_discarding_cages(self):
        fixture=StiffnessBank();fixture.omitted.add(('PropMaterial.GetORebar_1','material','TIE_STEEL_SYNTHETIC'))
        _,cages,transverse,shear=package(fixture)
        self.assertEqual(cages['bound_member_count'],2)
        self.assertEqual(transverse['bound_member_count'],0)
        self.assertEqual(shear['status_counts'],{'BLOCKED_INPUTS':48})
        self.assertEqual(len(transverse_rows(transverse)),12)
        self.assertTrue(all(r['calculation'] is None for r in shear['rows']))

    def test_inapplicable_native_confine_type_zero_does_not_block_rectangular_source(self):
        for native in (0,2):
            fixture=StiffnessBank();fixture.calls[('PropFrame.GetRebarColumn','column_section','RECT_SYNTHETIC')]['raw_response'][3]=native
            _,_,transverse,shear=package(fixture)
            self.assertEqual(transverse['bound_member_count'],2)
            self.assertEqual(transverse['profiles'][0]['model_confine_type_unused'],native)
            self.assertEqual(shear['status_counts'],{'SHEAR_REFERENCES_CALCULATED':48})

    def test_circular_pattern_is_not_reinterpreted_as_rectangular_proposal(self):
        fixture=StiffnessBank();fixture.calls[('PropFrame.GetRebarColumn','column_section','RECT_SYNTHETIC')]['raw_response'][2]=2
        _,_,transverse,shear=package(fixture)
        self.assertEqual(transverse['bound_member_count'],0)
        self.assertEqual(shear['status_counts'],{'BLOCKED_INPUTS':48})

    def test_native_labels_and_tie_counts_do_not_override_explicit_proposal(self):
        fixture=StiffnessBank();call=fixture.calls[('PropFrame.GetRebarColumn','column_section','RECT_SYNTHETIC')]
        call['raw_response'][8:13]=['unknown-long-label','unknown-tie-label',.9,99,0]
        _,_,transverse,_=package(fixture)
        p=transverse['proposals'][0]
        self.assertEqual(p['layout']['spacing_mm'],100)
        self.assertEqual(p['layout']['tie_diameter_mm'],12)
        self.assertEqual(len(p['axes']['V2']['asw_leg_ids']),5)

    def test_all_static_vectors_three_cages_two_axes_keep_source_and_station(self):
        self.assertEqual((self.shear['static_state_count'],self.shear['assessment_count']),(8,48))
        states={r['state_id']:r for r in self.chain['candidates']}
        for row in self.shear['rows']:
            source=states[row['state_id']]
            self.assertEqual(row['native_key'],source['native_key'])
            self.assertEqual(row['native_values'],source['native_values'])
            self.assertEqual(row['source_row_id'],source['source_row_id'])
            self.assertEqual(row['calculation']['source_signed_v_kn'],source['native_values'][row['shear_axis']])
            self.assertEqual(row['calculation']['n_compression_kn'],-source['native_values']['P'])
            self.assertFalse(row['final_design_eligible'])
        for state in states:self.assertEqual(sum(r['state_id']==state for r in self.shear['rows']),6)
        self.assertFalse(self.shear['source_population_reduced']);self.assertIsNone(self.shear['selected_design'])
        self.assertEqual(self.shear['ve_status'],'NOT_PROVEN');self.assertIsNone(self.shear['vc_zero_gate']['required'])

    def test_summary_keeps_exact_critical_source_ties_in_each_branch(self):
        fixture=StiffnessBank();fixture.set_static_vector([-1000,500,-300,4,40,-50])
        _,_,_,shear=package(fixture)
        for member in shear['members']:
            self.assertEqual(member['static_state_count'],4)
            for branch in member['branches'].values():
                self.assertEqual(branch['numeric_count'],4)
                self.assertEqual(len(branch['critical_source_states']),4)
                self.assertEqual({r['native_key']['ObjSta'] for r in branch['critical_source_states']},{0,2,3.3})

    def test_source_mismatch_duplicate_state_or_missing_proposal_is_rejected(self):
        changed=deepcopy(self.transverse);changed['source_cages_result_sha256']='OTHER'
        with self.assertRaises(BankError):build_column_shear(self.chain,self.cages,changed)
        changed=deepcopy(self.chain);changed['candidates'][1]=deepcopy(changed['candidates'][0])
        with self.assertRaises(BankError):build_column_shear(changed,self.cages,self.transverse)
        changed=deepcopy(self.transverse);changed['proposals'].pop()
        with self.assertRaises(BankError):build_column_shear(self.chain,self.cages,changed)
        changed=deepcopy(self.cages['candidates'][0]);changed['bars'][0]['x2_mm']+=1
        with self.assertRaises(BankError):proposed_layout(changed)

    def test_result_build_is_deterministic_and_preserves_accepted_inputs(self):
        before=deepcopy((self.chain,self.cages,self.transverse))
        again=build_column_shear(self.chain,self.cages,self.transverse)
        self.assertEqual((self.chain,self.cages,self.transverse),before)
        self.assertEqual(again['result_sha256'],self.shear['result_sha256'])
        json.dumps(again,allow_nan=False)

    def test_shear_pages_are_lazy_filterable_and_never_grow_sqlite(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.zip';source.write_bytes(StiffnessBank().build())
            saved=save_column_bank(source,root/'receipts');run=saved['run_id']
            db=root/'receipts'/run/'column-bank.sqlite';before=sha256(db.read_bytes()).hexdigest()
            with patch('tbdy_next.column_engine.demand_view._pmm',side_effect=AssertionError('Shear must not invoke PMM')):
                native=read_column_bank(root/'receipts',run)
                self.assertNotIn('column_shear',native)
                page=read_column_bank(root/'receipts',run,view='shear',member_id='C_SYNTHETIC_2',output_case='SUM',offset=2,limit=3)
                self.assertEqual(page['demand_page']['total'],24)
                self.assertEqual(len(page['demand_page']['rows']),3)
                self.assertNotIn('rows',page['column_shear'])
                self.assertTrue(all(r['member_id']=='C_SYNTHETIC_2' for r in page['demand_page']['rows']))
            self.assertEqual(sha256(db.read_bytes()).hexdigest(),before)
            with self.assertRaises(BankError):read_column_bank(root/'receipts',run,view='transverse',output_case='SUM')
            archive=root/'receipts'/run/'input.source';archive.write_bytes(archive.read_bytes()+b'changed')
            with self.assertRaises(BankError):read_column_bank(root/'receipts',run,view='shear')


if __name__=='__main__':unittest.main()
