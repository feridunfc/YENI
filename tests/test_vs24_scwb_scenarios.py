from contextlib import closing
from copy import deepcopy
import unittest

from scwb_scenario_fixture import ScenarioBank
from test_vs22_column_scwb import inputs
from tbdy_next.column_engine.native_archive import NativeArchive,BankError,digest
from tbdy_next.column_engine.column_scwb import build_column_scwb
from tbdy_next.column_engine.beam_references import build_beam_references
from tbdy_next.column_engine.scwb_scenarios import build_scwb_scenarios,scenario_projection,scenario_summaries


def parents(fixture=None):
    raw,chain,cages,joints,kin=inputs(fixture or ScenarioBank())
    with closing(NativeArchive(raw)) as archive:
        scwb=build_column_scwb(chain,cages,joints,kin,archive);beams=build_beam_references(chain,joints,archive)
    return raw,chain,joints,scwb,beams


def package(fixture=None):
    raw,*args=parents(fixture)
    with closing(NativeArchive(raw)) as archive:return build_scwb_scenarios(*args,archive)


def resign(result):result['result_sha256']=digest({k:v for k,v in result.items() if k!='result_sha256'})


class ScenarioBindingTests(unittest.TestCase):
    def test_complete_three_by_three_population_and_case_counts(self):
        r=package()
        self.assertEqual((r['joint_node_count'],r['expected_case_count'],r['case_count'],r['calculated_case_count']),(3,108,108,36))
        self.assertEqual((r['expected_summary_count'],r['summary_count']),(54,54))
        self.assertEqual(len(r['beam_references']),24);self.assertEqual(r['scwb_ratio_count'],0)
        self.assertTrue(all(row['scwb_ratio'] is None for row in r['rows']))
        self.assertTrue(all(not row['normative_nd_minimum_proven'] for row in r['summaries']))

    def test_asymmetric_beams_use_exact_signed_branch_and_same_column_case(self):
        r=package();beam={b['reference_id']:b for b in r['beam_references']}
        row=next(x for x in r['rows'] if x['joint_id']=='P1' and x['direction']=='X' and x['rotation_sign']==1)
        refs=[beam[key] for key in row['beam_reference_ids']];by_name={x['member_id']:x for x in refs}
        self.assertEqual((by_name['BX+']['local_internal_moment_sign'],by_name['BX-']['local_internal_moment_sign']),(1,-1))
        self.assertEqual((by_name['BX+']['tension_face'],by_name['BX-']['tension_face']),('BOTTOM','TOP'))
        self.assertAlmostEqual(row['sum_mrb_scenario_knm'],sum(b['capacity_knm'] for b in refs))
        self.assertAlmostEqual(row['normalized_scenario_ratio'],row['sum_mrc_scenario_knm']/(1.2*row['sum_mrb_scenario_knm']))
        self.assertFalse(row['concurrent_column_and_beam_force_state_proven'])
        self.assertTrue(all(not x['column_case_is_beam_area_control_case'] for x in refs))

    def test_native_ij_reversal_preserves_joint_sign_branch_and_summary(self):
        original=package();f=ScenarioBank();f.reverse('BX+');reversed=package(f)
        def summaries(r):return [(s['direction'],s['column_label'],s['beam_diameter_mm'],s['minimum_normalized_scenario_ratio']) for s in r['summaries'] if s['joint_id']=='P1']
        self.assertEqual(summaries(original),summaries(reversed))
        self.assertTrue(all(b['end']=='J' for b in reversed['beam_references'] if b['member_id']=='BX+'))

    def test_quarter_turn_preserves_corresponding_global_plane_ratio(self):
        original=package();f=ScenarioBank();f.rotate_global(90);rotated=package(f)
        def summaries(r,d):return [s['minimum_normalized_scenario_ratio'] for s in r['summaries'] if s['joint_id']=='P1' and s['direction']==d]
        for a,b in zip(summaries(original,'X'),summaries(rotated,'Y')):self.assertAlmostEqual(a,b)

    def test_released_or_partial_beam_end_stays_in_denominator_and_nulls_ratio(self):
        for spring in (0,10000):
            with self.subTest(spring=spring):
                f=ScenarioBank();raw=f.calls[('FrameObj.GetReleases','frame','BX+')]['raw_response'];raw[0][5]=True;raw[2][5]=spring
                r=package(f);rows=[x for x in r['rows'] if x['joint_id']=='P1' and x['direction']=='X']
                self.assertTrue(all(x['expected_beam_count']==2 and x['sum_mrb_scenario_knm'] is None and x['normalized_scenario_ratio'] is None for x in rows))
                self.assertTrue(all(any(m['member_id']=='BX+' for m in row['missing_capacities']) for row in rows))
                self.assertIn('SCENARIO_LOCAL_ROTATION_RELEASED_OR_PARTIAL',r['mapping_reason_counts'])

    def test_missing_release_evidence_does_not_assume_fixed_joint(self):
        f=ScenarioBank();f.omitted.add(('FrameObj.GetReleases','frame','BX+'));r=package(f)
        self.assertIn('SCENARIO_NATIVE_RELEASE_NOT_OBSERVED',r['mapping_reason_counts'])
        self.assertTrue(all(s['minimum_normalized_scenario_ratio'] is None for s in r['summaries'] if s['joint_id']=='P1' and s['direction']=='X'))

    def test_m2_column_release_blocks_correct_global_direction_only(self):
        f=ScenarioBank();f.calls[('FrameObj.GetReleases','frame','C_SYNTHETIC_1')]['raw_response'][1][4]=True;r=package(f)
        rows=[s for s in r['summaries'] if s['joint_id']=='P1']
        self.assertTrue(all(s['minimum_normalized_scenario_ratio'] is None for s in rows if s['direction']=='Y'))
        self.assertTrue(all(s['minimum_normalized_scenario_ratio'] is not None for s in rows if s['direction']=='X'))

    def test_ambiguous_beam_source_retains_both_beams_and_all_scenarios(self):
        f=ScenarioBank();f.beam_rows.append(deepcopy(f.beam_rows[0]));r=package(f)
        self.assertEqual(r['case_count'],108)
        summaries=[s for s in r['summaries'] if s['joint_id']=='P1' and s['direction']=='X']
        self.assertTrue(all(s['beam_ids']==['BX+','BX-'] and s['status']=='SCENARIO_INPUTS_INCOMPLETE' and s['minimum_normalized_scenario_ratio'] is None for s in summaries))

    def test_complete_case_and_both_rotation_minimum_keep_exact_governing_pairs(self):
        r=package();rows={x['result_id']:x for x in r['rows']}
        for s in r['summaries']:
            source=[rows[key] for key in s['case_result_ids']]
            if s['minimum_normalized_scenario_ratio'] is None:continue
            self.assertEqual(s['minimum_normalized_scenario_ratio'],min(x['normalized_scenario_ratio'] for x in source))
            expected=[x['result_id'] for x in source if x['normalized_scenario_ratio']==s['minimum_normalized_scenario_ratio']]
            self.assertEqual(set(s['governing_result_ids']),set(expected))
            self.assertTrue(any(x['sum_mrc_scenario_knm']==s['governing_sum_mrc_knm'] and x['sum_mrb_scenario_knm']==s['governing_sum_mrb_knm'] for x in source))

    def test_one_missing_case_or_rotation_nulls_summary_instead_of_minimum_fallback(self):
        r=package();node=next(n for n in r['nodes'] if n['point_id']=='P1');rows=[deepcopy(x) for x in r['rows'] if x['joint_id']=='P1']
        for row in rows:
            if row['rotation_sign']==1:row.update(normalized_scenario_ratio=None,status='CAPACITY_INPUTS_INCOMPLETE',scenario_reference_satisfied=None)
        s=scenario_summaries([node],rows,r['static_cases'],r['column_labels'],r['beam_diameters_mm'])
        self.assertTrue(all(x['minimum_normalized_scenario_ratio'] is None and x['calculated_case_rotation_count']==1 for x in s))
        with self.assertRaises(BankError):scenario_summaries([node],rows[:-1],r['static_cases'],r['column_labels'],r['beam_diameters_mm'])

    def test_topology_uncertainty_nulls_all_totals_without_dropping_participants(self):
        f=ScenarioBank();f.point('OTHER',(3,0,6));f.frame('BRACE','P1','OTHER',3,'RECT_SYNTHETIC',[1,0,0,0,1,0,0,0,1]);r=package(f)
        for row in r['rows']:
            if row['joint_id']=='P1':
                self.assertEqual(row['status'],'TOPOLOGY_UNRESOLVED');self.assertEqual(row['expected_beam_count'],2)
                for key in ('normalized_scenario_ratio','sum_mrc_scenario_knm','sum_mrb_scenario_knm','required_mrc_scenario_knm'):self.assertIsNone(row[key])

    def test_member_and_proposal_filters_keep_all_adjacent_participants(self):
        r=scenario_projection(package(),'C_SYNTHETIC_1',column_label='16Φ28',beam_diameter=20)
        self.assertEqual((r['filtered_joint_node_count'],r['filtered_case_count'],r['filtered_summary_count']),(2,8,4))
        self.assertTrue(r['neighbouring_participants_retained'])
        self.assertTrue(all(s['column_ids']==['C_SYNTHETIC_1','C_SYNTHETIC_2'] for s in r['summaries'] if s['joint_id']=='P1'))
        self.assertEqual({b['member_id'] for b in r['beam_references']},{'BX+','BX-','BY+','BY-'})
        self.assertTrue(all(s['column_label']=='16Φ28' and s['beam_diameter_mm']==20 for s in r['summaries']))

    def test_spectral_filter_and_no_beam_direction_never_claim_a_satisfied_ratio(self):
        r=scenario_projection(package(),output_case='RS_SUM',column_label='16Φ24',beam_diameter=20)
        self.assertEqual(r['filtered_case_count'],0)
        self.assertTrue(all(s['status']=='NO_STATIC_SOURCE_CASES' and s['minimum_normalized_scenario_ratio'] is None for s in r['summaries']))
        base=[s for s in package()['summaries'] if s['joint_id']=='P0']
        self.assertTrue(all(s['status']=='NO_RECORDED_BEAM_IN_DIRECTION' and s['scenario_reference_satisfied'] is None for s in base))

    def test_parent_hash_and_rehashed_scope_population_tampering_rejected(self):
        for kind in ('hash','beam_end','case','authority','selected','sign_capacity'):
            with self.subTest(kind=kind):
                raw,chain,joints,scwb,beams=parents()
                if kind=='hash':beams['rows'][0]['source']['targets']['top_mm2']=1
                elif kind=='beam_end':beams['rows'].pop();resign(beams)
                elif kind=='case':scwb['rows'].pop();resign(scwb)
                elif kind=='authority':beams['formal_compliance']='PROVEN';resign(beams)
                elif kind=='selected':beams['selected_design']='Φ20';resign(beams)
                else:scwb['rows'][0]['column_reference_ids']=['missing'];resign(scwb)
                with closing(NativeArchive(raw)) as a,self.assertRaises((BankError,KeyError)):build_scwb_scenarios(chain,joints,scwb,beams,a)

    def test_unknown_graph_preserves_known_column_ends_and_unknown_joint_denominator(self):
        f=ScenarioBank();f.calls.pop(('PointObj.GetCoordCartesian','point','PX+'));r=package(f)
        self.assertEqual((r['known_column_count'],r['expected_column_end_count']),(2,4))
        self.assertIsNone(r['joint_node_count']);self.assertIsNone(r['expected_case_count']);self.assertIsNone(r['expected_summary_count'])
        self.assertEqual(len(r['unresolved_member_ends']),4)

    def test_beam_candidates_cannot_be_moved_to_another_native_member_end(self):
        raw,chain,joints,scwb,beams=parents()
        first=next(r for r in beams['rows'] if r['member_id']=='BX+' and r['end']=='I')
        other=next(r for r in beams['rows'] if r['member_id']=='BX-' and r['end']=='I')
        first['candidates'],other['candidates']=other['candidates'],first['candidates'];resign(beams)
        with closing(NativeArchive(raw)) as a,self.assertRaisesRegex(BankError,'CANDIDATE_SOURCE_BINDING'):
            build_scwb_scenarios(chain,joints,scwb,beams,a)

    def test_beam_end_identity_is_independently_bound_to_archive_member_and_end(self):
        raw,chain,joints,scwb,beams=parents();beams['rows'][0]['end_id']=beams['rows'][1]['end_id'];resign(beams)
        with closing(NativeArchive(raw)) as a,self.assertRaisesRegex(BankError,'BEAM_END_ID_MISMATCH'):
            build_scwb_scenarios(chain,joints,scwb,beams,a)

    def test_column_source_state_must_match_native_end_case_components_and_n(self):
        for kind in ('wrong_end','n','components','step','pair_id'):
            with self.subTest(kind=kind):
                raw,chain,joints,scwb,beams=parents()
                refs=[r for r in scwb['column_references'] if r['member_id']=='C_SYNTHETIC_1' and r['axis']=='M3' and r['candidate_label']=='16Φ24']
                i=next(r for r in refs if r['end']=='I');j=next(r for r in refs if r['end']=='J')
                if kind=='wrong_end':j['source_state']=deepcopy(i['source_state'])
                elif kind=='n':j['n_source_kn']=1;j['calculation']['n_source_kn']=1
                elif kind=='components':j['source_state']['native_values']['M3']+=1
                elif kind=='step':j['source_state']['native_key']['StepType']='Max'
                else:j['source_force_pair_id']=i['reference_id']
                resign(scwb)
                with closing(NativeArchive(raw)) as a,self.assertRaisesRegex(BankError,'COLUMN_NATIVE_END_STATE'):
                    build_scwb_scenarios(chain,joints,scwb,beams,a)

    def test_existing_parent_hashes_and_objects_are_unchanged_by_scenario_projection(self):
        raw,chain,joints,scwb,beams=parents();original=deepcopy((chain,joints,scwb,beams))
        with closing(NativeArchive(raw)) as a:r=build_scwb_scenarios(chain,joints,scwb,beams,a)
        self.assertEqual((chain,joints,scwb,beams),original)
        projected=scenario_projection(r);projected['rows'][0]['missing_capacities'].append({'fake':True})
        self.assertFalse(any('fake' in v for v in r['rows'][0]['missing_capacities']))
