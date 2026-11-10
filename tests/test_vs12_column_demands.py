"""Independent six-component oracle and failure cases for the offline demand chain."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from column_bank_fixture import SyntheticBank, subset, encoded, zipped
from column_demand_fixture import DesignBank, TABLE
from tbdy_next.cli import main
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.native_archive import NativeArchive, BankError
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.store import save_column_bank, read_column_bank


def assess(fixture):
    raw = fixture.build()
    bank = recover_column_bank(raw)
    with closing(NativeArchive(raw)) as archive:
        return build_demand_chain(bank, archive)


class DemandChainTests(unittest.TestCase):
    def test_independent_signed_six_component_hand_oracle(self):
        chain = assess(DesignBank())
        state = next(r for r in chain['candidates'] if r['native_key']['Obj'] == 'C_SYNTHETIC_1' and r['native_key']['ObjSta'] == 0)
        self.assertEqual(state['native_values'], dict(zip(('P','V2','V3','T','M2','M3'), (-180,10.8,-18.4,2.6,48,-57.2))))
        for key, expected in {'N_compression_kN':180,'V2_kN':10.8,'V3_kN':-18.4,'T_kNcm':260,
                              'M2_kNcm':4800,'M3_kNcm':-5720}.items():
            self.assertAlmostEqual(state['domain_values'][key], expected)
        self.assertEqual(len(state['native_key']), 7)
        self.assertEqual(state['constituent_factors'], [1.4, 1.6])
        self.assertEqual(len(state['constituent_row_ids']), 2)
        self.assertEqual(chain['static_candidate_count'], 8)

    def test_tension_is_negative_compression_and_j_station_is_not_flipped(self):
        fixture = DesignBank()
        for rows in fixture.forces.values():
            for row in rows:
                if row[4] in ('G','Q','SUM'): row[7] = -row[7]
        chain = assess(fixture)
        rows = [r for r in chain['candidates'] if r['native_key']['Obj']=='C_SYNTHETIC_1']
        self.assertEqual([r['domain_values']['N_compression_kN'] for r in rows], [-180,-360,-540,-720])
        self.assertEqual(rows[-1]['native_key']['ObjSta'], 3.3)
        self.assertEqual(rows[-1]['location_role'], 'RECORDED_STATION')
        self.assertEqual(rows[-1]['analysis_order'], 'NOT_PROVEN')

    def test_mesh_interface_keeps_two_distinct_full_states(self):
        rows = [r for r in assess(DesignBank())['candidates'] if r['native_key']['Obj']=='C_SYNTHETIC_1'
                and r['native_key']['ObjSta']==2]
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['native_key']['ElmSta'] for r in rows}, {0,2})
        self.assertEqual(len({r['state_id'] for r in rows}), 2)

    def test_changed_shear_or_torsion_prevents_candidate(self):
        for component in (9,10):  # Native V3, T; PMM components are unchanged.
            fixture = DesignBank()
            next(r for r in fixture.forces[fixture.members[0]] if r[4]=='SUM')[component] += .01
            self.assertEqual(assess(fixture)['static_candidate_count'], 7)

    def test_step_mismatch_never_borrows_another_case_step(self):
        fixture = DesignBank()
        next(r for r in fixture.forces[fixture.members[0]] if r[4]=='Q')[6] = 2
        self.assertEqual(assess(fixture)['static_candidate_count'], 7)

    def test_spectrum_envelope_and_nested_routes_cannot_promote(self):
        chain = assess(DesignBank())
        routes = {r['combination']:r for r in chain['combinations']}
        self.assertEqual(routes['SUM']['classification'], 'STATIC_LINEAR_ADD')
        self.assertEqual(routes['RS_SUM']['classification'], 'RESPONSE_SPECTRUM_LINEAR_ADD')
        self.assertEqual(routes['ENV']['classification'], 'ENVELOPE')
        self.assertEqual(routes['NESTED']['classification'], 'STATIC_NESTED_UNVERIFIED')
        self.assertEqual({r['native_key']['LoadCase'] for r in chain['candidates']}, {'SUM'})
        self.assertTrue(all(not r['final_design_eligible'] for r in chain['candidates']))

    def test_renaming_does_not_change_the_engineering_route(self):
        fixture = DesignBank()
        fixture.combos['MISLEADING_EARTHQUAKE'] = fixture.combos.pop('SUM')
        fixture.combos['NESTED'] = (0, [(1,'MISLEADING_EARTHQUAKE',1)])
        for rows in fixture.forces.values():
            for row in rows:
                if row[4]=='SUM': row[4]='MISLEADING_EARTHQUAKE'
        chain = assess(fixture)
        self.assertEqual(chain['static_candidate_count'], 8)
        self.assertEqual({r['native_key']['LoadCase'] for r in chain['candidates']}, {'MISLEADING_EARTHQUAKE'})

    def test_unknown_and_cyclic_references_remain_visible(self):
        for terms in ([(1,'LOST',1)], [(1,'NESTED',1)]):
            fixture = DesignBank(); fixture.combos['NESTED'] = (0,terms)
            chain = assess(fixture)
            row = next(r for r in chain['combinations'] if r['combination']=='NESTED')
            self.assertEqual(row['classification'], 'DEFINITION_UNRESOLVED')
            self.assertTrue(row['reason'])
            self.assertEqual(chain['combination_count'], 4)

    def test_missing_case_type_or_unstable_capture_yields_no_static_candidates(self):
        for issue in ('type','capture'):
            fixture = DesignBank()
            if issue=='type': fixture.omitted.add(('LoadCases.GetTypeOAPI_1','case','Q'))
            else: fixture.context['identity_unchanged'] = False
            self.assertEqual(assess(fixture)['static_candidate_count'], 0)

    def test_design_reference_is_not_a_design_selection_or_pmm_pass(self):
        chain = assess(DesignBank()); summary = chain['design_summary']
        self.assertEqual((summary['row_count'],summary['reference_count'],summary['known_combination_references']), (8,24,24))
        self.assertEqual(summary['null_pmm_ratio_rows'], 8)
        self.assertIsNone(summary['rows'][0]['native_design_row']['PMMRatio'])
        self.assertFalse(summary['full_design_selection_proven'])
        self.assertEqual(chain['design_demand_authority'], 'DENIED')
        self.assertTrue(all(not ref['shear_axis_mapping_proven'] and not ref['final_design_eligible']
                            for row in summary['rows'] for ref in row['references']))

    def test_duplicate_design_station_never_selects_first_native_element(self):
        rows = [r for r in assess(DesignBank())['design_summary']['rows'] if r['station_text']=='2']
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row['design_station_occurrences'], 2)
            self.assertTrue(all(r['status']=='AMBIGUOUS_DESIGN_STATION' and r['source_state_count']==2 for r in row['references']))

    def test_rounded_station_does_not_use_nearest_force(self):
        fixture = DesignBank()
        for row in fixture.forces[fixture.members[0]]:
            if row[1]==3.3: row[1]=.8583333589
        fixture.design_rows[3]['Station'] = '.85833'
        row = assess(fixture)['design_summary']['rows'][3]
        self.assertTrue(all(r['status']=='EXACT_NATIVE_STATION_NOT_FOUND' and not r['source_row_ids'] for r in row['references']))

    def test_wrong_story_label_section_or_unselected_member_blocks_binding(self):
        for field in ('Story','Label','DesignSect','UniqueName'):
            fixture = DesignBank(); fixture.design_rows[0][field] = 'OTHER'
            row = assess(fixture)['design_summary']['rows'][0]
            self.assertFalse(row['identity_matches_source_member'])
            self.assertTrue(all(r['status']=='DESIGN_MEMBER_CONTEXT_UNRESOLVED' for r in row['references']))

    def test_unknown_design_combination_is_not_inferred_from_similar_name(self):
        fixture = DesignBank(); fixture.design_rows[0]['PMMCombo'] = 'SUM_'
        ref = assess(fixture)['design_summary']['rows'][0]['references'][0]
        self.assertEqual(ref['status'], 'COMBINATION_NOT_DEFINED')
        self.assertEqual(ref['source_row_ids'], [])

    def test_absent_design_table_retains_static_evidence(self):
        chain = assess(SyntheticBank())
        self.assertEqual(chain['static_candidate_count'], 8)
        self.assertEqual(chain['design_summary']['status'], 'NOT_OBSERVED')
        self.assertEqual(len(chain['design_summary']['missing_selected_members']), 2)

    def test_units_missing_schema_bad_cells_or_missing_fields_reject_design_only(self):
        for issue in ('units','schema','shape','fields'):
            fixture = DesignBank()
            if issue=='units': fixture.units['Station']='cm'
            elif issue=='schema': fixture.omitted.add(('DatabaseTables.GetAllFieldsInTable','table',TABLE))
            elif issue=='shape': fixture.truncate=True
            else: fixture.table_fields.remove('Station')
            chain = assess(fixture)
            self.assertEqual(chain['static_candidate_count'], 8)
            self.assertEqual(chain['design_summary']['status'], 'NOT_PROVEN')
            self.assertEqual(chain['design_summary']['unique_static_links'], 0)

    def test_subset_cannot_inherit_parent_static_authority(self):
        raw = subset(DesignBank().build()); bank = recover_column_bank(raw)
        with closing(NativeArchive(raw)) as archive:
            chain = build_demand_chain(bank,archive)
        self.assertEqual(chain['static_candidate_count'], 0)
        self.assertEqual(chain['design_demand_authority'], 'DENIED')

    def test_damaged_optional_table_gzip_retains_valid_force_chain(self):
        for damage in ('truncated','invalid_deflate'):
            with self.subTest(damage=damage):
                files=DesignBank().files()
                index=[json.loads(line) for line in files['shard-index.jsonl'].splitlines()]
                entry=next(r for r in index if r['api']=='DatabaseTables.GetTableForDisplayArray')
                original=files[entry['path']]
                files[entry['path']]=original[:-7] if damage=='truncated' else original[:10]+b'\x07'+original[-8:]
                entry['sha256']=sha256(files[entry['path']]).hexdigest()
                files['shard-index.jsonl']=b'\n'.join(map(encoded,index))
                files['archive-manifest.json']=encoded({'schema':'tbdy.full-bank.archive-manifest.v1',
                    'files':{name:{'sha256':sha256(value).hexdigest(),'bytes':len(value)} for name,value in files.items()
                             if name!='archive-manifest.json'}})
                raw=zipped(files); bank=recover_column_bank(raw)
                with closing(NativeArchive(raw)) as archive:
                    chain=build_demand_chain(bank,archive)
                self.assertEqual(chain['static_candidate_count'],8)
                self.assertEqual(chain['design_summary']['status'],'NOT_PROVEN')

    def test_cross_archive_binding_and_changed_constituent_rejected(self):
        fixture = DesignBank(); raw = fixture.build(); bank = recover_column_bank(raw)
        other = DesignBank(); other.units['Station']='cm'
        with closing(NativeArchive(other.build())) as archive, self.assertRaisesRegex(BankError,'ARCHIVE_BINDING'):
            build_demand_chain(bank,archive)
        bad = deepcopy(bank)
        bad['static_replay']['items'][0]['constituent_row_ids'][0] = bad['static_replay']['items'][1]['constituent_row_ids'][0]
        with closing(NativeArchive(raw)) as archive:
            chain = build_demand_chain(bad,archive)
        self.assertEqual(chain['static_candidate_count'], 7)
        self.assertIn('CONSTITUENT_BINDING',chain['rejected_candidates'][0]['reason'])


class DemandStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); source=self.root/'source.zip'; source.write_bytes(DesignBank().build())
        self.receipts=self.root/'receipts'; self.saved=save_column_bank(source,self.receipts)
        self.run=self.saved['run_id']

    def snapshot(self):
        return {str(p.relative_to(self.root)):sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}

    def test_existing_receipt_and_database_are_unchanged_by_every_view_and_cli(self):
        before=self.snapshot()
        for view in ('native','static','design'):
            read_column_bank(self.receipts,self.run,view=view)
        with patch('sys.stdout',new_callable=StringIO) as stream:
            code=main(['inspect-column-demands','--out',str(self.receipts),'--run-id',self.run])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(stream.getvalue())['static_candidate_count'],8)
        self.assertEqual(self.snapshot(),before)

    def test_filtered_pagination_and_full_export_share_calculation_hash(self):
        full=read_column_bank(self.receipts,self.run,full=True)
        page=read_column_bank(self.receipts,self.run,member_id='C_SYNTHETIC_1',output_case='SUM',view='static',offset=1,limit=2)
        self.assertEqual(page['demand_page']['total'],4)
        self.assertEqual(len(page['demand_page']['rows']),2)
        self.assertEqual(page['demand_chain']['result_sha256'],full['demand_chain']['result_sha256'])
        self.assertEqual(len(full['demand_chain']['candidates']),8)
        self.assertEqual(len(full['demand_chain']['design_summary']['rows']),8)
        page=read_column_bank(self.receipts,self.run,member_id='C_SYNTHETIC_1',output_case='RS_SUM',view='design')
        self.assertEqual(page['demand_page']['total'],4)
        self.assertEqual(read_column_bank(self.receipts,self.run,output_case='RS_SUM',view='static')['demand_page']['total'],0)

    def test_cache_hit_rechecks_source_and_database_integrity(self):
        for name in ('column-bank.sqlite','input.source'):
            read_column_bank(self.receipts,self.run)
            p=self.receipts/self.run/name; original=p.read_bytes()
            p.write_bytes(original+b'TAMPER')
            with self.assertRaisesRegex(BankError,'CHANGED'): read_column_bank(self.receipts,self.run)
            p.write_bytes(original)

    def test_returned_views_cannot_mutate_cached_source(self):
        page=read_column_bank(self.receipts,self.run,view='static')
        page['demand_page']['rows'][0]['domain_values']['N_compression_kN']=99999
        page['demand_chain']['combinations'].clear()
        second=read_column_bank(self.receipts,self.run,view='static')
        self.assertEqual(second['demand_page']['rows'][0]['domain_values']['N_compression_kN'],180)
        self.assertEqual(len(second['demand_chain']['combinations']),4)

    def test_invalid_view_does_not_fall_back_to_another_population(self):
        with self.assertRaisesRegex(BankError,'PAGE_INVALID'):
            read_column_bank(self.receipts,self.run,view='capacity')


if __name__=='__main__':
    unittest.main()
