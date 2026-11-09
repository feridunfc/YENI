from contextlib import closing
from copy import deepcopy
import unittest

from column_kinematics_fixture import KinematicsBank
from tbdy_next.column_engine.native_archive import NativeArchive,BankError
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.column_prechecks import build_column_prechecks
from tbdy_next.column_engine.column_pmm import build_column_cages
from tbdy_next.column_engine.column_transverse import build_column_transverse
from tbdy_next.column_engine.column_joints import build_column_joints
from tbdy_next.column_engine.column_kinematics import build_column_kinematics
from tbdy_next.column_engine.column_scwb import build_column_scwb,scwb_projection,_summaries


def inputs(fixture=None):
    raw=(fixture or KinematicsBank()).build();bank=recover_column_bank(raw);bank['run_id']='RUN-SCWB-TEST'
    with closing(NativeArchive(raw)) as a:
        chain=build_demand_chain(bank,a);pre=build_column_prechecks(bank,chain);cages=build_column_cages(bank,chain,pre,a)
        transverse=build_column_transverse(chain,cages,a);joints=build_column_joints(bank,chain,cages,transverse,a)
        kin=build_column_kinematics(bank,chain,joints,a)
    return raw,chain,cages,joints,kin


def package(fixture=None):
    raw,*args=inputs(fixture)
    with closing(NativeArchive(raw)) as a:return build_column_scwb(*args,a)


class SourceSCWBTests(unittest.TestCase):
    def test_each_joint_once_all_ends_cases_scenarios_and_signs_retained(self):
        r=package()
        self.assertEqual((r['joint_node_count'],r['column_end_count'],r['native_beam_count']),(3,4,4))
        self.assertEqual((r['joint_case_count'],r['expected_joint_case_count'],r['column_reference_count']),(36,36,24))
        self.assertEqual(r['calculated_column_reference_count'],24)
        self.assertEqual(len({x['result_id'] for x in r['rows']}),36)
        self.assertTrue(all(x['scwb_ratio'] is None and x['normalized_reference_ratio'] is None for x in r['rows']))
        self.assertEqual(r['scwb_ratio_count'],0)

    def test_columns_sum_same_case_source_n_with_correct_p_sign(self):
        r=package();refs={x['reference_id']:x for x in r['column_references']}
        for row in r['rows']:
            values=[refs[k] for k in row['column_reference_ids']]
            self.assertEqual(row['sum_mrc_reference_knm'],sum(x['capacity_knm'] for x in values))
            for x in values:
                self.assertEqual(x['n_source_kn'],-x['source_state']['native_values']['P'])
                self.assertEqual(x['source_state']['native_key']['LoadCase'],row['output_case'])
                self.assertFalse(x['source_cut_is_physical_joint_face'])

    def test_missing_beam_rebar_stays_missing_even_when_override_is_nonzero(self):
        fixture=KinematicsBank();call=fixture.calls[('PropFrame.GetRebarBeam','beam_section','BEAM_SYNTHETIC')]
        call['raw_response'][4:8]=[.001,.002,.001,.002]
        r=package(fixture)
        self.assertTrue(all(x['moment_capacity_knm'] is None for x in r['beam_sources']))
        self.assertTrue(all(x['reason']=='MODEL_OVERRIDES_ARE_NOT_QUALIFIED_END_CAGES' for x in r['beam_sources']))
        self.assertFalse(r['required_beam_steel_used_as_capacity']);self.assertFalse(r['approximate_as_half_fallback_used'])

    def test_zero_overrides_do_not_mean_zero_provided_rebar(self):
        r=package();self.assertTrue(all(x['reason']=='ZERO_OVERRIDES_ARE_NOT_PROVIDED_REBAR' for x in r['beam_sources']))
        self.assertTrue(all(not x['actual_or_selected_cage_bound'] for x in r['beam_sources']))

    def test_rotated_unequal_column_maps_global_direction_to_other_local_axis(self):
        fixture=KinematicsBank();fixture.unequal_rotated_lower();r=package(fixture)
        index={x['reference_id']:x for x in r['column_references']}
        row=next(x for x in r['rows'] if x['joint_id']=='P1' and x['direction']=='X' and x['candidate_label']=='16Φ24')
        cols={index[k]['member_id']:index[k] for k in row['column_reference_ids']}
        self.assertEqual(cols['C_SYNTHETIC_1']['axis'],'M2');self.assertEqual(cols['C_SYNTHETIC_2']['axis'],'M3')
        self.assertNotEqual(cols['C_SYNTHETIC_1']['capacity_knm'],cols['C_SYNTHETIC_2']['capacity_knm'])

    def test_oblique_beam_stays_in_roster_and_blocks_total_in_both_directions(self):
        fixture=KinematicsBank();fixture.point('PX+',(5,2,4));r=package(fixture)
        node=next(n for n in r['nodes'] if n['point_id']=='P1')
        for roster in node['rosters'].values():
            self.assertIn('BX+',[x['member_id'] for x in roster['beams']])
            self.assertIn('NONORTHOGONAL_BEAM_DIRECTION_NOT_BOUND',roster['reasons'])
        for row in r['rows']:
            if row['joint_id']=='P1':self.assertEqual(row['status'],'TOPOLOGY_UNRESOLVED');self.assertIsNone(row['sum_mrc_reference_knm'])

    def test_member_filter_keeps_neighbouring_column_and_beam_population(self):
        r=scwb_projection(package(),member_id='C_SYNTHETIC_1')
        self.assertEqual(r['filtered_joint_node_count'],2)
        middle=[s for s in r['summaries'] if s['joint_id']=='P1']
        self.assertTrue(all(s['column_ids']==['C_SYNTHETIC_1','C_SYNTHETIC_2'] for s in middle))
        self.assertTrue(all(len(s['beam_ids'])==2 for s in middle))
        self.assertTrue(r['neighbouring_participants_retained'])

    def test_spectral_filter_and_unrecorded_cases_do_not_reuse_static_minima(self):
        r=scwb_projection(package(),output_case='RS_SUM')
        self.assertEqual(r['filtered_joint_case_count'],0)
        self.assertTrue(all(s['sampled_minimum_column_sum_knm'] is None and s['status']=='NO_STATIC_SOURCE_CASES' for s in r['summaries']))

    def test_one_failed_required_case_nulls_sampled_minimum_instead_of_dropping_it(self):
        r=package();node=next(n for n in r['nodes'] if n['point_id']=='P1')
        rows=[deepcopy(x) for x in r['rows'] if x['joint_id']=='P1']
        second=deepcopy(rows)
        for row in second:row.update(output_case='OTHER',result_id=row['result_id']+'OTHER',sum_mrc_reference_knm=None)
        result=_summaries([node],rows+second,['SUM','OTHER'])
        self.assertTrue(all(s['sampled_minimum_column_sum_knm'] is None and s['calculated_column_sum_count']==1 and s['expected_case_count']==2 for s in result))

    def test_native_no_upper_column_is_not_automatic_code_exemption(self):
        r=package();roof=next(n for n in r['nodes'] if n['point_id']=='P2')
        self.assertEqual(roof['rosters']['X']['recorded_above_column_count'],0)
        self.assertFalse(roof['rosters']['X']['normative_exception_applied'])
        self.assertFalse(r['normative_exception_applied']);self.assertFalse(r['earthquake_compatible_minimum_proven'])

    def test_incomplete_joint_roster_and_mixed_force_state_rejected(self):
        for kind in ('roster','case','source','authority'):
            with self.subTest(kind=kind):
                raw,chain,cages,joints,kin=inputs()
                if kind=='roster':joints['graph']['nodes'][1]['incident_frames'].pop()
                elif kind=='case':kin['rows'][0]['force_pair']['i']=deepcopy(kin['rows'][0]['force_pair']['i']);kin['rows'][0]['force_pair']['i']['native_key']['LoadCase']='OTHER'
                elif kind=='source':kin['source_joints_result_sha256']='OTHER'
                else:joints['formal_compliance']='PROVEN'
                with closing(NativeArchive(raw)) as a,self.assertRaises(BankError):build_column_scwb(chain,cages,joints,kin,a)

    def test_missing_force_pair_blocks_every_affected_total_and_minimum(self):
        raw,chain,cages,joints,kin=inputs();kin['rows'][0].update(force_pair=None,force_status='BLOCKED_INPUTS',force_reason='END_MISSING')
        with closing(NativeArchive(raw)) as a:r=build_column_scwb(chain,cages,joints,kin,a)
        middle=[s for s in r['summaries'] if s['joint_id']=='P1']
        self.assertTrue(all(s['sampled_minimum_column_sum_knm'] is None for s in middle))
        self.assertEqual(r['column_reason_counts']['END_MISSING'],12)

    def test_swapped_duplicated_interior_or_changed_offset_force_ends_are_rejected(self):
        for kind in ('swap','duplicate','interior','offset'):
            with self.subTest(kind=kind):
                raw,chain,cages,joints,kin=inputs();pair=kin['rows'][0]['force_pair']
                if kind=='swap':pair['i'],pair['j']=pair['j'],pair['i']
                elif kind=='duplicate':pair['j']=pair['i']
                elif kind=='offset':pair['offset_j_m']=0
                else:
                    pair['i']=next(r for r in chain['candidates'] if r['native_key']['Obj']==kin['rows'][0]['member_id']
                        and r['native_key']['LoadCase']==kin['rows'][0]['output_case'] and 0<r['native_key']['ObjSta']<3.3)
                with closing(NativeArchive(raw)) as a,self.assertRaises(BankError):build_column_scwb(chain,cages,joints,kin,a)

    def test_missing_graph_preserves_known_column_end_case_denominators(self):
        fixture=KinematicsBank();fixture.calls.pop(('PointObj.GetCoordCartesian','point','PX+'))
        r=package(fixture)
        self.assertEqual(r['source_population_status'],'BLOCKED_NATIVE_JOINT_GRAPH')
        self.assertEqual((r['selected_column_count'],r['expected_column_end_count'],r['expected_column_reference_count']),(2,4,24))
        self.assertIsNone(r['joint_node_count']);self.assertIsNone(r['expected_joint_case_count'])
        self.assertEqual(r['column_reference_count'],0);self.assertEqual(len(r['unresolved_member_ends']),4)
        self.assertIsNone(scwb_projection(r)['filtered_joint_node_count'])
        self.assertEqual(len(scwb_projection(r,member_id='C_SYNTHETIC_1')['unresolved_member_ends']),2)
