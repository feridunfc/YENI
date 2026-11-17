"""Same-capture component replay; Decimal fixtures are independent of the owner."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
import unittest
from unittest.mock import patch

from test_native_demand_sources import support_fixture
from test_r10_live import _rowset
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.engineering.mixed_demands import spectral_component_evidence


def replay_fixture(static_factor='.9', spectral_factor='.3'):
    args = support_fixture(); source = args[0]
    for row in source['vs04_basis_probe']['table_reads']['Load Combination Definitions']['rows']:
        if row['Name'] == 'S':
            row['SF'] = static_factor if row['LoadName'] == 'BASE_A' else spectral_factor
    support = source['column_axial']['demand_support']['force_source']['rowsets']
    target = source['column_axial']['force_source']['rowsets']
    for uid, rs in support.items():
        rows = list(native_frame_force_rows(rs, uid))
        rows = [(*r[:7], 10., 20., 30., 40., 50., 60.) if r[4] == 'RS' else r for r in rows]
        support[uid] = _rowset(rows)
        rebuilt = []
        for target_row in native_frame_force_rows(target[uid], uid):
            if target_row[4] != 'S':
                rebuilt.append(target_row); continue
            static = next(r for r in rows if r[:4] == target_row[:4] and r[4] == 'BASE_A')
            spectral = next(r for r in rows if r[:4] == target_row[:4] and r[4] == 'RS')
            with localcontext() as ctx:
                ctx.prec = 80
                sign = Decimal(1 if target_row[5] == 'Max' else -1)
                values = [float(Decimal(static_factor)*Decimal(str(g)) + sign*abs(Decimal(spectral_factor))*Decimal(str(e)))
                          for g, e in zip(static[7:], spectral[7:])]
            rebuilt.append((*target_row[:7], *values))
        target[uid] = _rowset(rebuilt)
    return args


def mutate_support(args, change):
    force = args[0]['column_axial']['demand_support']['force_source']
    rows = list(native_frame_force_rows(force['rowsets']['C1'], 'C1'))
    force['rowsets']['C1'] = _rowset(change(rows))


class SameSourceSpectralReplay(unittest.TestCase):
    def evaluate(self, args):
        return spectral_component_evidence(*args, input_sha='one-capture')

    def test_all_six_components_match_independent_decimal_fixture(self):
        args = replay_fixture(); original = deepcopy(args)
        result = self.evaluate(args); replay = result['primitive_replay']
        self.assertEqual(result['status_counts'], {'SAME_SOURCE_COMPONENT_REPLAY_MATCH': 2})
        self.assertEqual((replay['expected_cut_count'], replay['matched_cut_count'], replay['scalar_comparisons']), (6, 6, 72))
        self.assertEqual(replay['over_tolerance_components'], 0)
        self.assertEqual(args, original)
        cut = result['rows'][0]['cuts'][0]['primitive_replay']
        self.assertEqual(cut['nd_bounds_kn'], [177., 183.])
        self.assertEqual(cut['center_native']['V2'], 90.)
        self.assertEqual(cut['radius_native']['M3'], 18.)
        self.assertEqual([t['case_guid'] for t in cut['source_terms']], ['a', 'rs'])
        self.assertFalse(result['signed_alpha_input_eligible']); self.assertFalse(result['physical_concurrency_proven'])
        json.dumps(result, allow_nan=False)

    def test_negative_and_amplified_coefficients_are_used_once(self):
        for factors in [('-0.9', '-0.3'), ('1.2', '2.5'), ('0.9', '0.75')]:
            with self.subTest(factors=factors):
                result = self.evaluate(replay_fixture(*factors))
                self.assertEqual(result['primitive_replay']['status'], 'NUMERICAL_MATCH')
                self.assertFalse(result['additional_directional_or_scale_factor_applied'])

    def test_changed_primitive_force_is_a_visible_arithmetic_mismatch(self):
        args = replay_fixture()
        mutate_support(args, lambda rows: [(*r[:11], r[11]+.001, r[12]) if r[4]=='RS' and r[1]==0 else r for r in rows])
        result = self.evaluate(args); replay = result['primitive_replay']
        self.assertEqual(replay['status'], 'NUMERICAL_MISMATCH')
        self.assertEqual((replay['matched_cut_count'], replay['mismatched_cut_count'], replay['over_tolerance_components']), (5, 1, 2))
        self.assertEqual(result['rows'][0]['status'], 'NOT_PROVEN')
        self.assertEqual(len(result['rows'][0]['cuts'][0]['primitive_replay']['failed_comparisons']), 2)

    def test_missing_leaf_keeps_the_full_expected_denominator(self):
        args = replay_fixture()
        mutate_support(args, lambda rows: [r for r in rows if not (r[4]=='RS' and r[1]==1.5)])
        replay = self.evaluate(args)['primitive_replay']
        self.assertEqual((replay['expected_cut_count'], replay['matched_cut_count'], replay['unresolved_cut_count']), (6, 5, 1))
        self.assertEqual(replay['status'], 'SOURCE_UNRESOLVED')

    def test_opposite_analysis_element_side_is_not_interpolated(self):
        args = replay_fixture()
        mutate_support(args, lambda rows: [(*r[:2], 'opposite-side', *r[3:]) if r[4]=='RS' and r[1]==1.5 else r for r in rows])
        self.assertEqual(self.evaluate(args)['primitive_replay']['unresolved_cut_count'], 1)

    def test_unique_ulp_match_is_allowed_but_ambiguous_match_is_rejected(self):
        args = replay_fixture()
        mutate_support(args, lambda rows: [(*r[:1], r[1]+2e-16, *r[2:]) if r[4]=='RS' and r[1]==1.5 else r for r in rows])
        self.assertEqual(self.evaluate(args)['primitive_replay']['matched_cut_count'], 6)
        mutate_support(args, lambda rows: rows+[(*r[:1], 1.5, *r[2:]) for r in rows if r[4]=='RS' and r[1]>1 and r[1]<2])
        self.assertEqual(self.evaluate(args)['primitive_replay']['unresolved_cut_count'], 1)

    def test_negative_spectral_amplitude_and_wrong_step_cannot_be_hidden(self):
        for defect in ('negative', 'step'):
            args = replay_fixture()
            mutate_support(args, lambda rows: [((*r[:7], -1., *r[8:]) if defect=='negative' else (*r[:5], 'Min', *r[6:]))
                                              if r[4]=='RS' and r[1]==0 else r for r in rows])
            self.assertEqual(self.evaluate(args)['primitive_replay']['unresolved_cut_count'], 1)

    def test_foreign_plan_or_unrestored_selection_blocks_all_leaf_replay(self):
        for defect in ('plan', 'restore', 'units'):
            args = replay_fixture(); support = args[0]['column_axial']['demand_support']
            if defect=='plan': support['plan']['case_definitions']['RS']['guid'] = 'foreign'
            elif defect=='restore': support['force_source']['output_selection_after']['cases']['RS'] = True
            else: support['force_source']['units_code'] = 12
            result = self.evaluate(args)
            self.assertEqual(result['primitive_replay']['unresolved_cut_count'], 6)
            self.assertEqual(result['status_counts'], {'NOT_PROVEN': 2})

    def test_missing_member_is_not_replaced_by_another_archive(self):
        args = replay_fixture(); force = args[0]['column_axial']['demand_support']['force_source']
        force['rowsets'].pop('C1'); force['errors']['C1']='capture failed'
        result = self.evaluate(args)
        self.assertEqual(result['primitive_replay']['unresolved_cut_count'], 3)
        self.assertEqual(result['expected_pair_count'], 2)

    def test_upstream_blocker_keeps_matched_arithmetic_unqualified(self):
        args = replay_fixture(); args[2]['dependency_blockers']=['UNBOUND_ANALYSIS_MESH']
        result = self.evaluate(args)
        self.assertEqual(result['primitive_replay']['matched_cut_count'], 6)
        self.assertEqual(result['primitive_replay']['qualified_pair_count'], 0)
        self.assertEqual(result['status_counts'], {'NOT_PROVEN': 2})

    def test_older_source_is_explicitly_observed_only(self):
        args = replay_fixture(); args[0]['column_axial'].pop('demand_support')
        result = self.evaluate(args)
        self.assertEqual(result['primitive_replay']['status'], 'NOT_CAPTURED')
        self.assertEqual(result['status_counts'], {'OBSERVED_INTERVALS_DECOMPOSED': 2})

    def test_html_projects_replay_counts_without_invoking_owner(self):
        from tbdy_next.reporting import _mixed_components_html
        result = self.evaluate(replay_fixture())
        with patch('tbdy_next.column_engine.spectral_envelope.replay_component_envelope', side_effect=AssertionError('recalculation')) as calc:
            html = _mixed_components_html(result)
        calc.assert_not_called(); self.assertIn('Same-capture primitive-case replay', html)
        self.assertIn('NOT concurrent', html); self.assertIn('Matched cuts', html)

    def test_live_and_bank_adapters_share_the_same_arithmetic_owner(self):
        from test_vs26_spectral_envelopes import evaluate
        from tbdy_next.column_engine.spectral_envelope import replay_component_envelope
        with patch('tbdy_next.column_engine.spectral_envelope.replay_component_envelope', wraps=replay_component_envelope) as owner:
            self.evaluate(replay_fixture())
            live_calls = owner.call_count
            evaluate()
        self.assertEqual(live_calls, 6); self.assertGreater(owner.call_count, live_calls)


if __name__ == '__main__':
    unittest.main()
