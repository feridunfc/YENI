"""Independent extrema oracle, normative area arithmetic and source failure cases."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from column_demand_fixture import DesignBank
from tbdy_next.column_engine.column_prechecks import critical_selection, build_column_prechecks
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.native_archive import NativeArchive, BankError
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.store import save_column_bank, read_column_bank


def hand_chain():
    # A–C contain all scalar extrema; D must still remain a full PMM candidate.
    values={'A':(300,20,-4,5,-2,1), 'B':(200,-20,30,-5,6,-3),
            'C':(-100,10,-30,1,-6,3), 'D':(290,19,29,4,5,2)}
    states=[]
    for i,(identity,(n,m2,m3,v2,v3,t)) in enumerate(values.items()):
        states.append({'state_id':identity,'source_row_id':'ROW_'+identity,'source_archive_sha256':'SYNTHETIC',
            'vector_status':'SIGNED_STATIC_SOURCE_VECTOR','native_key':{'Obj':'C1','ObjSta':i,'Elm':'E1','ElmSta':i,
                'LoadCase':'SUM','StepType':'Single Value','StepNum':0},
            'native_values':{'P':-n,'V2':v2,'V3':v3,'T':t/100,'M2':m2/100,'M3':m3/100},
            'domain_values':{'N_compression_kN':n,'V2_kN':v2,'V3_kN':v3,'T_kNcm':t,'M2_kNcm':m2,'M3_kNcm':m3}})
    return {'candidates':states,'source_archive_sha256':'SYNTHETIC','result_sha256':'CHAIN_SYNTHETIC',
        'combinations':[{'combination':'SUM','classification':'STATIC_LINEAR_ADD'}]}


def assess(fixture):
    raw=fixture.build(); bank=recover_column_bank(raw)
    with closing(NativeArchive(raw)) as archive:
        chain=build_demand_chain(bank,archive)
    return build_column_prechecks(bank,chain)


class CriticalSelectionTests(unittest.TestCase):
    population=[{'member_id':'C1','observed_station_count':4}]

    def test_independent_multiaxial_oracle_and_pmm_population_preserved(self):
        chain=hand_chain(); original=deepcopy(chain)
        result=critical_selection(chain,self.population)
        actual={r['criterion']:set(r['state_ids']) for r in result['members'][0]['criteria']}
        self.assertEqual(actual,{'N_COMPRESSION_MAX':{'A'},'N_TENSION_MAX':{'C'},'M2_ABS_MAX':{'A','B'},
            'M3_ABS_MAX':{'B','C'},'V2_ABS_MAX':{'A','B'},'V3_ABS_MAX':{'B','C'},'T_ABS_MAX':{'B','C'}})
        self.assertEqual({r['state_id'] for r in result['rows']},{'A','B','C'})
        self.assertEqual(chain,original)
        self.assertEqual(result['candidate_count'],4)
        self.assertFalse(result['pmm_population_reduced'])

    def test_each_critical_vector_is_an_original_complete_vector(self):
        chain=hand_chain(); original={r['state_id']:r for r in chain['candidates']}
        for row in critical_selection(chain,self.population)['rows']:
            for field in ('source_row_id','native_key','native_values','domain_values'):
                self.assertEqual(row[field],original[row['state_id']][field])
            self.assertFalse(row['final_design_eligible'])

    def test_case_filter_recomputes_extrema_instead_of_filtering_global_winners(self):
        chain=hand_chain(); chain['candidates'][0]['native_key']['LoadCase']='OTHER'
        chain['combinations'].append({'combination':'OTHER','classification':'STATIC_LINEAR_ADD'})
        full=critical_selection(chain,self.population)
        filtered=critical_selection(chain,self.population,output_case='SUM')
        def compression(result): return result['members'][0]['criteria'][0]['state_ids']
        self.assertEqual(compression(full),['A'])
        self.assertEqual(compression(filtered),['D'])
        self.assertEqual(filtered['candidate_count'],3)
        self.assertEqual(filtered['output_case'],'SUM')
        self.assertNotEqual(filtered['result_sha256'],full['result_sha256'])

    def test_rounding_does_not_create_a_tie(self):
        chain=hand_chain(); chain['candidates'][1]['native_values']['M2']=-.19999999999999996
        chain['candidates'][1]['domain_values']['M2_kNcm']=-19.999999999999996
        result=critical_selection(chain,self.population)
        self.assertEqual(result['members'][0]['criteria'][2]['state_ids'],['A'])

    def test_native_moments_remain_distinct_when_float_unit_conversion_collapses_them(self):
        for component,index in (('T',10),('M2',11),('M3',12)):
            for sign in (-1,1):
                fixture=DesignBank(); fixture.combos['SUM']=(0,[(0,'G',1)])
                for rows in fixture.forces.values():
                    for row in rows:
                        if row[4] in ('G','SUM'):
                            row[7:]=[0]*6
                            row[index]=sign*({0:.2000000000000001,3.3:.20000000000000012}.get(row[1],0))
                raw=fixture.build(); bank=recover_column_bank(raw)
                with closing(NativeArchive(raw)) as archive:
                    chain=build_demand_chain(bank,archive)
                member_states=[r for r in chain['candidates'] if r['native_key']['Obj']=='C_SYNTHETIC_1'
                    and r['native_key']['ObjSta'] in (0,3.3)]
                self.assertEqual(len(member_states),2)
                self.assertEqual(len({r['domain_values'][component+'_kNcm'] for r in member_states}),1)
                result=build_column_prechecks(bank,chain)['critical_selection']
                criterion=next(c for c in result['members'][0]['criteria'] if c['criterion']==component+'_ABS_MAX')
                self.assertEqual(criterion['state_ids'],[r['state_id'] for r in member_states if r['native_key']['ObjSta']==3.3])
                self.assertEqual(criterion['magnitude'],'20.000000000000012')

    def test_no_compression_or_tension_is_distinct_from_zero_and_missing(self):
        chain=hand_chain()
        for row in chain['candidates']:
            row['domain_values']={k:0 for k in row['domain_values']}
            row['native_values']={k:0 for k in row['native_values']}
        result=critical_selection(chain,self.population)
        criteria=result['members'][0]['criteria']
        self.assertEqual([r['status'] for r in criteria[:2]],['NO_OBSERVED_COMPRESSION','NO_OBSERVED_TENSION'])
        self.assertTrue(all(r['magnitude'] is None for r in criteria[:2]))
        self.assertTrue(all(r['status']=='ALL_ZERO' and len(r['state_ids'])==4 for r in criteria[2:]))
        self.assertEqual(result['critical_state_count'],4)

    def test_missing_member_stays_in_source_population(self):
        population=self.population+[{'member_id':'MISSING','observed_station_count':0}]
        result=critical_selection(hand_chain(),population)
        missing=result['members'][1]
        self.assertEqual(missing['source_subset_coverage'],'UNRESOLVED')
        self.assertIsNone(missing['expected_static_states'])
        self.assertTrue(all(r['status']=='NO_CANDIDATES' for r in missing['criteria']))

    def test_partial_station_coverage_cannot_become_complete(self):
        chain=hand_chain(); chain['candidates'].pop()
        result=critical_selection(chain,self.population)
        self.assertEqual(result['members'][0]['source_subset_coverage'],'PARTIAL')
        self.assertEqual(result['members'][0]['expected_static_states'],4)

    def test_unknown_or_spectral_filter_never_uses_other_static_cases(self):
        chain=hand_chain(); chain['combinations'].append({'combination':'RS','classification':'RESPONSE_SPECTRUM_LINEAR_ADD'})
        for output in ('UNKNOWN','RS'):
            result=critical_selection(chain,self.population,output_case=output)
            self.assertEqual(result['rows'],[])
            self.assertEqual(result['candidate_count'],0)
            self.assertEqual(result['members'][0]['source_subset_coverage'],'UNRESOLVED')

    def test_duplicate_and_cross_source_state_cannot_be_selected(self):
        for defect in ('duplicate','source','route'):
            chain=hand_chain()
            if defect=='duplicate': chain['candidates'].append(deepcopy(chain['candidates'][0]))
            elif defect=='source': chain['candidates'][0]['source_archive_sha256']='OTHER'
            else: chain['candidates'][0]['vector_status']='SPECTRAL_EXTREMA'
            with self.assertRaises(BankError): critical_selection(chain,self.population)


class ReinforcementBoundsTests(unittest.TestCase):
    def test_eighty_square_hand_calculation_and_exact_source_area_conversion(self):
        result=assess(DesignBank()); bounds=result['reinforcement_bounds']
        self.assertEqual(bounds['calculated_member_count'],2)
        for row in bounds['rows']:
            self.assertEqual((row['gross_area_cm2'],row['minimum_as_cm2'],row['maximum_as_cm2']),('6400','64','256'))
            self.assertIsNone(row['provided_as_cm2'])
            self.assertFalse(row['physical_cage_proven'])
        self.assertEqual(bounds['source_comparison_counts'],{'NUMERICAL_MATCH':8})
        self.assertTrue(all(r['source_asmin_cm2']=='64' for r in bounds['source_comparisons']))

    def test_unequal_rectangle_uses_both_native_dimensions(self):
        fixture=DesignBank()
        fixture.calls[('PropFrame.GetRectangle','frame_section','RECT_SYNTHETIC')]['raw_response'][2:4]=[.5,.3]
        for row in fixture.design_rows: row['AsMin']='.0015'
        bounds=assess(fixture)['reinforcement_bounds']
        for row in bounds['rows']:
            self.assertEqual((row['gross_area_cm2'],row['minimum_as_cm2'],row['maximum_as_cm2']),('1500','15','60'))
        self.assertEqual(bounds['source_comparison_counts'],{'NUMERICAL_MATCH':8})

    def test_above_and_below_source_values_are_comparisons_not_compliance_verdicts(self):
        fixture=DesignBank(); fixture.design_rows[0]['AsMin']='.0065'; fixture.design_rows[1]['AsMin']='.0063'
        result=assess(fixture); rows=result['reinforcement_bounds']['source_comparisons']
        self.assertEqual((rows[0]['status'],rows[0]['difference_cm2']),('SOURCE_ABOVE_REFERENCE','1'))
        self.assertEqual((rows[1]['status'],rows[1]['difference_cm2']),('SOURCE_BELOW_REFERENCE','-1'))
        self.assertEqual(result['formal_compliance'],'NOT_PROVEN')
        self.assertEqual(result['design_demand_authority'],'DENIED')

    def test_missing_units_or_asmin_remain_unresolved_without_erasing_area_bounds(self):
        for defect in ('unit','field','null','nan','negative','huge'):
            fixture=DesignBank()
            if defect=='unit': fixture.units['AsMin']='cm2'
            elif defect=='field': fixture.table_fields.remove('AsMin')
            else: fixture.design_rows[0]['AsMin']={'null':None,'nan':'NaN','negative':'-1','huge':'1e999999'}[defect]
            bounds=assess(fixture)['reinforcement_bounds']
            self.assertEqual(bounds['calculated_member_count'],2)
            self.assertEqual(bounds['source_comparisons'][0]['status'],'NOT_PROVEN')
            self.assertIsNone(bounds['source_comparisons'][0]['source_asmin_cm2'])

    def test_missing_section_keeps_members_and_critical_vectors(self):
        fixture=DesignBank(); fixture.omitted.add(('PropFrame.GetRectangle','frame_section','RECT_SYNTHETIC'))
        result=assess(fixture)
        self.assertEqual(result['reinforcement_bounds']['selected_member_count'],2)
        self.assertEqual(result['reinforcement_bounds']['calculated_member_count'],0)
        self.assertEqual(result['critical_selection']['candidate_count'],8)
        self.assertTrue(all(r['minimum_as_cm2'] is None for r in result['reinforcement_bounds']['rows']))

    def test_different_design_section_does_not_borrow_model_section_for_comparison(self):
        fixture=DesignBank(); fixture.design_rows[0]['DesignSect']='OTHER'
        row=assess(fixture)['reinforcement_bounds']['source_comparisons'][0]
        self.assertEqual(row['status'],'NOT_PROVEN')
        self.assertEqual(row['reason'],'DESIGN_SECTION_IDENTITY_NOT_BOUND')

    def test_model_rebar_setting_does_not_establish_provided_area_or_splice_allowance(self):
        fixture=DesignBank()
        rebar=fixture.calls[('PropFrame.GetRebarColumn','column_section','RECT_SYNTHETIC')]['raw_response']
        rebar[8]='BAR_DIAMETER_NOT_OBSERVED'; rebar[-2]=False
        bounds=assess(fixture)['reinforcement_bounds']
        self.assertFalse(bounds['provided_reinforcement_checked'])
        self.assertFalse(bounds['splice_checked'])
        self.assertFalse(bounds['bar_diameter_and_count_checked'])
        self.assertFalse(bounds['applicability_proven'])
        self.assertTrue(bounds['boundary_inclusive'])
        self.assertTrue(all(r['maximum_as_cm2']=='256' and r['provided_as_cm2'] is None for r in bounds['rows']))


class PrecheckStoreTests(unittest.TestCase):
    def test_new_views_preserve_files_and_export_complete_demands_and_traces(self):
        with TemporaryDirectory() as directory:
            root=Path(directory); source=root/'bank.zip'; source.write_bytes(DesignBank().build())
            saved=save_column_bank(source,root/'receipts'); run=saved['run_id']
            def files(): return {str(p):sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
            before=files()
            full=read_column_bank(root/'receipts',run,full=True)
            critical=read_column_bank(root/'receipts',run,view='critical',member_id='C_SYNTHETIC_1',output_case='SUM',limit=1)
            bounds=read_column_bank(root/'receipts',run,view='reinforcement',member_id='C_SYNTHETIC_2')
            self.assertEqual(critical['critical_scope']['candidate_count'],4)
            self.assertEqual(len(critical['demand_page']['rows']),1)
            self.assertEqual(bounds['demand_page']['total'],1)
            self.assertEqual(bounds['demand_page']['rows'][0]['minimum_as_cm2'],'64')
            self.assertEqual(len(full['demand_chain']['candidates']),8)
            self.assertEqual(len(full['column_prechecks']['reinforcement_bounds']['source_comparisons']),8)
            self.assertEqual(critical['column_prechecks']['result_sha256'],full['column_prechecks']['result_sha256'])
            self.assertEqual(critical['column_prechecks']['source_demand_result_sha256'],full['demand_chain']['result_sha256'])
            with self.assertRaisesRegex(BankError,'CASE_FILTER_NOT_APPLICABLE'):
                read_column_bank(root/'receipts',run,view='reinforcement',output_case='SUM')
            critical['demand_page']['rows'][0]['domain_values']['N_compression_kN']=999999
            again=read_column_bank(root/'receipts',run,view='critical')
            self.assertTrue(all(r['domain_values']['N_compression_kN']!=999999 for r in again['demand_page']['rows']))
            self.assertEqual(files(),before)


if __name__=='__main__': unittest.main()
