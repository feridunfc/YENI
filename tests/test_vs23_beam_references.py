from contextlib import closing
from copy import deepcopy
import math
import unittest
from beam_reference_fixture import BeamBank
from test_vs22_column_scwb import inputs
from tbdy_next.column_engine.native_archive import NativeArchive,BankError
from tbdy_next.column_engine.beam_references import build_beam_references,beam_projection,station_budget


def package(fixture=None):
    raw,chain,cages,joints,kin=inputs(fixture or BeamBank())
    with closing(NativeArchive(raw)) as archive:return build_beam_references(chain,joints,archive)


class BeamReferenceTests(unittest.TestCase):
    def test_complete_source_targets_and_three_conditional_candidates_per_end(self):
        r=package()
        self.assertEqual((r['native_beam_count'],r['target_beam_count'],r['expected_end_count'],r['expected_incident_end_count']),(4,4,8,4))
        self.assertEqual((r['source_bound_end_count'],r['incident_bound_end_count'],r['calculated_candidate_count']),(8,4,24))
        self.assertTrue(all(len(row['candidates'])==3 for row in r['rows']))
        self.assertIsNone(r['scwb_ratio']);self.assertIsNone(r['selected_design'])

    def test_units_total_area_and_different_control_cases_preserved(self):
        r=package();source=r['rows'][0]['source'];targets=source['targets']
        self.assertEqual((targets['top_mm2'],targets['bottom_mm2']),(1200,800))
        self.assertEqual(targets['source_areas_mm2']['AsTop'],900)
        self.assertEqual((targets['top_combination'],targets['bottom_combination']),('SUM','RS_SUM'))
        self.assertFalse(targets['same_force_vector_claimed']);self.assertFalse(targets['total_required_area_is_provided'])
        self.assertEqual(source['table_source']['field_units']['AsTop'],'m2')

    def test_ulp_arithmetic_drift_matches_but_display_rounding_does_not(self):
        f=BeamBank();f.beam_rows[0]['Station']=str(math.nextafter(.25,1));r=package(f)
        self.assertEqual(r['source_bound_end_count'],8)
        f=BeamBank();f.beam_rows[0]['Station']='0.25001';r=package(f)
        self.assertEqual(r['source_reason_counts'],{'BEAM_DESIGN_STATION_NOT_FOUND':1})
        self.assertLessEqual(station_budget(1e10,1e10,1e10),1e-9)

    def test_two_distinct_native_cuts_at_same_target_remain_ambiguous(self):
        f=BeamBank();other=deepcopy(f.forces['BX+'][0]);other[2]='SECOND_ELEMENT';f.forces['BX+'].append(other)
        r=package(f);row=next(row for row in r['rows'] if row['member_id']=='BX+' and row['end']=='I')
        self.assertEqual(row['reason'],'BEAM_NATIVE_CUT_AMBIGUOUS');self.assertEqual(row['source']['native_cut_count'],2)
        self.assertTrue(all(c['capacity'] is None for c in row['candidates']))

    def test_overlapping_end_match_windows_cannot_use_one_cut_twice(self):
        f=BeamBank();f.calls[('FrameObj.GetEndLengthOffset','frame','BX+')]['raw_response'][2]=math.nextafter(4.75,0)
        r=package(f);ends=[row for row in r['rows'] if row['member_id']=='BX+']
        self.assertEqual(len(ends),2);self.assertTrue(all(row['reason']=='BEAM_END_MATCH_WINDOWS_OVERLAP' for row in ends))
        self.assertTrue(all(c['capacity'] is None for row in ends for c in row['candidates']))

    def test_unknown_or_undefined_control_combination_cannot_seed_proposals(self):
        for key in ('AsTopCombo','AsBotCombo','TLngCombo'):
            with self.subTest(key=key):
                f=BeamBank();f.beam_rows[0][key]='NOT_IN_CAPTURED_MODEL';r=package(f)
                self.assertEqual(r['source_bound_end_count'],7)
                self.assertEqual(r['source_reason_counts'],{'BEAM_CONTROL_REFERENCE_NOT_BOUND':1})

    def test_duplicate_design_station_never_uses_maximum_or_last_row(self):
        f=BeamBank();duplicate=deepcopy(f.beam_rows[0]);duplicate['totTopRebar']='.1';f.beam_rows.append(duplicate)
        r=package(f);row=next(row for row in r['rows'] if row['member_id']=='BX+' and row['end']=='I')
        self.assertEqual(row['reason'],'BEAM_DESIGN_STATION_AMBIGUOUS');self.assertEqual(len(row['source']['design_matches']),2)
        self.assertTrue(all(c['capacity'] is None for c in row['candidates']))

    def test_interior_maximum_cannot_replace_the_endpoint(self):
        f=BeamBank();f.beam_rows[1]['totTopRebar']='.1';r=package(f)
        self.assertTrue(all(row['source']['targets']['top_mm2']==1200 for row in r['rows']))

    def test_wrong_units_and_missing_schema_block_source_instead_of_guessing(self):
        f=BeamBank();f.beam_units['AsTop']='cm2';r=package(f)
        self.assertEqual(r['source_bound_end_count'],0);self.assertEqual(r['table_status'],'BEAM_DESIGN_TABLE_BLOCKED')
        self.assertEqual(len(r['rows']),8)

    def test_missing_negative_warned_or_foreign_section_rows_block_only_their_end(self):
        for key,value in (('AsTop',None),('AsTop','-1'),('ErrMsg','Design failed'),('WarnMsg','Warning'),('DesignSect','OTHER')):
            with self.subTest(key=key,value=value):
                f=BeamBank();f.beam_rows[0][key]=value;r=package(f)
                self.assertEqual(r['source_bound_end_count'],7)
                self.assertTrue(all(c['capacity'] is None for c in r['rows'][0]['candidates']))

    def test_zero_overrides_do_not_qualify_actual_reinforcement_or_scwb(self):
        r=package();self.assertFalse(r['actual_or_selected_beam_capacity_bound'])
        self.assertTrue(all(not p['model_overrides_used_as_provided'] for p in r['profiles']))
        self.assertTrue(all(not c['selected_design'] and not c['physical_cage_proven'] for row in r['rows'] for c in row['candidates']))

    def test_column_filter_keeps_only_incident_ends_and_source_population_metadata(self):
        r=beam_projection(package(),'C_SYNTHETIC_1')
        self.assertEqual((r['expected_end_count'],r['filtered_end_count']),(8,4))
        self.assertTrue(all('C_SYNTHETIC_2' in row['adjacent_column_ids'] for row in r['rows']))
        self.assertTrue(all(row['incident_to_column_joint'] for row in r['rows']))

    def test_unrelated_beam_is_listed_as_outside_joint_scope(self):
        f=BeamBank();f.frame('UNRELATED','PX+','PY+',2,'BEAM_SYNTHETIC',[1,0,0,0,0,1,0,-1,0])
        r=package(f);self.assertEqual(r['native_beam_count'],5);self.assertEqual(r['target_beam_count'],4)
        self.assertEqual(r['outside_joint_scope_beams'][0]['member_id'],'UNRELATED')

    def test_missing_graph_keeps_known_columns_and_unknown_beam_denominator(self):
        f=BeamBank();f.calls.pop(('PointObj.GetCoordCartesian','point','PX+'));r=package(f)
        self.assertEqual(r['known_column_count'],2);self.assertIsNone(r['target_beam_count']);self.assertIsNone(r['expected_end_count'])
        self.assertEqual(r['source_population_status'],'BLOCKED_NATIVE_JOINT_GRAPH')

    def test_source_and_complete_joint_roster_guards(self):
        for kind in ('source','authority','roster','node'):
            with self.subTest(kind=kind):
                raw,chain,cages,joints,kin=inputs(BeamBank())
                if kind=='source':joints['source_demand_result_sha256']='OTHER'
                elif kind=='authority':joints['formal_compliance']='PROVEN'
                elif kind=='node':joints['graph']['nodes'].pop()
                else:joints['graph']['nodes'][1]['incident_frames'].pop()
                with closing(NativeArchive(raw)) as archive,self.assertRaises(BankError):build_beam_references(chain,joints,archive)

    def test_missing_native_offset_or_force_never_falls_back_to_table_extrema(self):
        for api in ('FrameObj.GetEndLengthOffset','Results.FrameForce'):
            with self.subTest(api=api):
                f=BeamBank();f.omitted.add((api,'frame','BX+'));r=package(f)
                rows=[row for row in r['rows'] if row['member_id']=='BX+']
                self.assertEqual(len(rows),2);self.assertTrue(all(row['status']=='BEAM_END_SOURCE_BLOCKED' for row in rows))
