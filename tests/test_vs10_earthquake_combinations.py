"""Independent coefficient/context oracles; no production model data committed."""
from copy import deepcopy
from fractions import Fraction as F
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from tbdy_next.earthquake_combinations import (
    COMBOS, SUMMARY, SPECTRUM, MET, UNMET, UNKNOWN, NA,
    bind_earthquake_combinations, coefficient_subcondition,
)
from tbdy_next.vs05_d4_source_authority import _case_source, _combo_source
from tbdy_next.source_control_bundle import bind_source_controls
from tbdy_next.web import make_handler
from test_vs05_story_delta import table
from test_vs09_source_controls import snapshot as base_snapshot


def definitions():
    return [
        ("N1", "Linear Add", [("G", "1"), ("RSX", "1"), ("RSY", ".3")]),
        ("N2", "Linear Add", [("G", "1"), ("RSX", ".3"), ("RSY", "1")]),
        ("K1", "Linear Add", [("G", "1"), ("RSX", "2.5"), ("RSY", ".75")]),
        ("K2", "Linear Add", [("G", "1"), ("RSX", ".75"), ("RSY", "2.5")]),
        ("OTHER_PAIR", "Linear Add", [("G", "1"), ("LC_EQ_OTHER", "1")]),
        ("ENV", "Envelope", [("N1", "1"), ("N2", "1")]),
    ]


def set_combos(src, specs):
    rows = []
    for name, operator, terms in specs:
        for i, (ref, factor) in enumerate(terms):
            rows.append({"Name": name, "Type": operator if i == 0 else "None",
                "LoadName": ref, "SF": factor, "GUID": "SYNTHETIC-" + name if i == 0 else "None"})
    src["vs04_basis_probe"]["table_reads"][COMBOS] = table(COMBOS, list(rows[0]), rows, {"SF": ""})
    return src


def snapshot(specs=None):
    src = base_snapshot()
    cases = [{"Name": n, "Type": t, "GUID": "SYNTHETIC-" + n} for n, t in (
        ("Modal", "Modal - Ritz"), ("RSX", "Response Spectrum"), ("RSY", "Response Spectrum"),
        ("G", "Linear Static"), ("LC_EQ_OTHER", "Linear Static"))]
    tables = src["vs04_basis_probe"]["table_reads"]
    tables[SUMMARY] = table(SUMMARY, list(cases[0]), cases, {})
    for row in tables[SPECTRUM]["rows"]: row["Function"] = "SYNTHETIC_SPECTRUM"
    tables[SPECTRUM]["fields"].append("Function")
    tables[SPECTRUM]["field_metadata"]["field_keys"] = tables[SPECTRUM]["fields"][:]
    return set_combos(src, specs or definitions())


def result(src):
    report = bind_earthquake_combinations(src)
    return report, report["checks"][0], report["checks"][1]


class ArithmeticTests(unittest.TestCase):
    def test_exact_normalized_ratio_with_independent_fraction_oracle(self):
        for x, y in (("1", ".3"), ("2.5", ".75"), ("-.3", "1"),
                     ("-2.5", "-.75"), ("1", ".3000000000001"), ("1", ".2999999999999")):
            row = coefficient_subcondition(x, y)
            a, b = abs(F(x)), abs(F(y))
            oracle = min(a, b) / max(a, b)
            self.assertEqual(row["status"] == MET, oracle == F(3, 10))
            self.assertEqual(F(row["common_factor"]), max(a, b))

    def test_pure_direction_tied_axes_and_zero_are_not_hidden(self):
        for x, y in (("1", "0"), ("0", "1"), ("1", "1")):
            self.assertEqual(coefficient_subcondition(x, y)["status"], UNMET)
        with self.assertRaises(ValueError): coefficient_subcondition("0", "0")

    def test_invalid_numbers_never_compute(self):
        for value in (True, None, "NaN", "Infinity", "", "not-a-factor"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                coefficient_subcondition(value, ".3")


class SourceAndContextTests(unittest.TestCase):
    def test_two_controls_without_source_mutation_or_authority(self):
        src = snapshot(); before = deepcopy(src)
        full, ratios, pairs = result(src)
        self.assertEqual((full["observed_combination_count"], full["parsed_combination_count"]), (6, 6))
        self.assertEqual((ratios["expected_count"], ratios["evaluated_count"], ratios["met_count"], ratios["not_applicable_count"]), (6, 4, 4, 2))
        self.assertEqual((pairs["expected_count"], pairs["met_count"]), (2, 2))
        self.assertEqual({x["common_factor"] for x in pairs["items"]}, {"1", "2.5"})
        self.assertTrue(all(x["full_sign_envelope"] == UNKNOWN for x in pairs["items"]))
        self.assertEqual(full, bind_earthquake_combinations(src))
        self.assertEqual(src, before)
        self.assertEqual(full["formal_compliance"], UNKNOWN)
        self.assertEqual(full["engineering_release"], "NOT_READY")

    def test_accepted_d4_default_summary_and_hash_are_unchanged(self):
        tables = snapshot()["vs04_basis_probe"]["table_reads"]
        cases = _case_source(tables)["cases"]
        previous = _combo_source(tables, cases)
        exposed = _combo_source(tables, cases, include_graph=True)
        self.assertEqual({k: v for k, v in exposed.items() if k != "typed_graph"}, previous)
        self.assertEqual(len(exposed["typed_graph"]), 6)

    def test_missing_or_zero_secondary_axis_is_ratio_failure(self):
        for terms in ([('G','1'), ('RSX','1')], [('G','1'), ('RSX','1'), ('RSY','0')]):
            specs = definitions(); specs[0] = ('N1', 'Linear Add', terms)
            _, ratios, _ = result(snapshot(specs))
            item = next(r for r in ratios['items'] if r['combination'] == 'N1')
            self.assertEqual(item['status'], UNMET)
            self.assertEqual(item['minor_major_ratio'], '0')
            self.assertEqual(ratios['expected_count'], 6)

    def test_both_zero_coefficients_stay_unresolved_not_scope_excluded(self):
        specs = definitions(); specs[0] = ('N1', 'Linear Add', [('G','1'), ('RSX','0'), ('RSY','0')])
        _, ratios, pairs = result(snapshot(specs))
        item = next(r for r in ratios['items'] if r['combination'] == 'N1')
        self.assertEqual(item['status'], UNKNOWN)
        self.assertTrue(any(r.get('unresolved_combination') == 'N1' for r in pairs['items']))

    def test_other_actions_and_common_factor_cannot_cross_complete_contexts(self):
        for factor in ('1', '-1', '.9'):
            specs = [
                ('A', 'Linear Add', [('G','1'), ('RSX','1'), ('RSY','.3')]),
                ('B', 'Linear Add', [('G',factor), ('RSX','.75'), ('RSY','2.5')]),
            ]
            _, ratios, pairs = result(snapshot(specs))
            self.assertEqual(ratios['met_count'], 2)
            self.assertEqual((pairs['expected_count'], pairs['unmet_count']), (2, 2))
        specs[1] = ('B', 'Linear Add', [('G','-.9'), ('RSX','.3'), ('RSY','1')])
        self.assertEqual(result(snapshot(specs))[2]['unmet_count'], 2)

    def test_names_and_order_do_not_determine_the_context(self):
        src = snapshot(); original = result(src)[2]
        rename = {name: 'OPAQUE_' + str(i) for i, (name, _, _) in enumerate(definitions())}
        specs = [(rename[n], op, [(rename.get(ref, ref), f) for ref, f in terms])
                 for n, op, terms in reversed(definitions())]
        changed = result(snapshot(specs))[2]
        self.assertEqual({r['context_sha256'] for r in original['items']},
                         {r['context_sha256'] for r in changed['items']})
        self.assertEqual(changed['met_count'], 2)

    def test_negative_horizontal_coefficients_do_not_prove_full_sign_envelope(self):
        specs = [
            ('A', 'Linear Add', [('G','1'), ('RSX','-1'), ('RSY','.3')]),
            ('B', 'Linear Add', [('G','1'), ('RSX','.3'), ('RSY','-1')]),
        ]
        _, ratios, pairs = result(snapshot(specs))
        self.assertEqual(ratios['met_count'], 2)
        self.assertEqual(pairs['met_count'], 1)
        self.assertEqual(pairs['items'][0]['full_sign_envelope'], UNKNOWN)
        self.assertEqual(set(pairs['items'][0]['observed_sign_patterns']), {'-+', '+-'})

    def test_nested_sum_factors_are_exact_and_envelope_is_not_summed(self):
        specs = definitions() + [
            ('NESTED', 'Linear Add', [('N1', '.1'), ('K1', '.2')]),
            ('BAD_NESTED', 'Linear Add', [('ENV', '1'), ('G', '1')]),
        ]
        _, ratios, _ = result(snapshot(specs))
        by_name = {r['combination']: r for r in ratios['items']}
        nested = by_name['NESTED']
        # Independent fractions: .1*1+.2*2.5=.6; .1*.3+.2*.75=.18.
        self.assertEqual(F(nested['coefficient_x']), F(3, 5))
        self.assertEqual(F(nested['coefficient_y']), F(9, 50))
        self.assertEqual(nested['status'], MET)
        self.assertEqual(by_name['BAD_NESTED']['status'], UNKNOWN)
        self.assertEqual(by_name['ENV']['status'], NA)
        self.assertEqual({r['ref'] for r in by_name['ENV']['envelope_alternatives']}, {'N1', 'N2'})
        self.assertNotIn('case_coefficients', by_name['ENV'])

    def test_cancellation_is_not_silently_classified_outside_scope(self):
        specs = definitions() + [('CANCEL', 'Linear Add', [('N1','1'), ('N2','-1')])]
        row = next(r for r in result(snapshot(specs))[1]['items'] if r['combination']=='CANCEL')
        self.assertEqual((row['coefficient_x'], row['coefficient_y'], row['minor_major_ratio']), ('0.7', '-0.7', '1'))
        self.assertEqual(row['status'], UNMET)

    def test_outside_pair_is_not_labeled_nonseismic(self):
        _, ratios, _ = result(snapshot())
        row = next(r for r in ratios['items'] if r['combination']=='OTHER_PAIR')
        self.assertEqual(row['status'], NA)
        self.assertEqual(row['reason'], 'OUTSIDE_SELECTED_RS_PAIR_SCOPE')
        self.assertIn('LC_EQ_OTHER', row['case_coefficients'])

    def test_unknown_reference_keeps_parent_and_envelope_unknown(self):
        specs=definitions(); specs[0][2].append(('UNSEEN_CASE','0'))
        _, ratios, pairs=result(snapshot(specs))
        by_name={r['combination']:r for r in ratios['items']}
        self.assertEqual(ratios['expected_count'],6)
        self.assertEqual(by_name['N1']['status'],UNKNOWN)
        self.assertEqual(by_name['ENV']['status'],UNKNOWN)
        self.assertTrue(any(r.get('unresolved_combination')=='N1' for r in pairs['items']))
        # A missing companion may be inside the unresolved source definition.
        group=next(r for r in pairs['items'] if r.get('common_factor')=='1')
        self.assertEqual(group['status'],UNKNOWN)

    def test_cycles_and_unsupported_operators_do_not_poison_independent_groups(self):
        for extra in ([('CYCLE','Linear Add',[('CYCLE','1')])],
                      [('CYCLE','Linear Add',[('OTHER_CYCLE','1')]), ('OTHER_CYCLE','Linear Add',[('CYCLE','1')])],
                      [('ABS','Absolute Add',[('N1','1'),('N2','1')])]):
            full,ratios,pairs=result(snapshot(definitions()+extra))
            self.assertEqual(ratios['expected_count'],6+len(extra))
            self.assertEqual(ratios['not_proven_count'],len(extra))
            self.assertEqual(ratios['met_count'],4)
            self.assertEqual(full['resolved_context_count'],2)
            self.assertEqual(pairs['met_count'],2)

    def test_repeated_reference_is_explicit_adapter_limit(self):
        specs=definitions(); specs[0][2].append(('RSX','-1'))
        row=next(r for r in result(snapshot(specs))[1]['items'] if r['combination']=='N1')
        self.assertEqual(row['status'],UNKNOWN)
        self.assertEqual(row['reason'],'REPEATED_REFERENCE_UNSUPPORTED_BY_SCALAR_ADAPTER')

    def test_case_identity_axis_units_and_missing_source_preserve_named_population(self):
        for defect in ('case_guid','type','axis','angle','units','context','missing_table','factor'):
            src=snapshot();tables=src['vs04_basis_probe']['table_reads']
            if defect=='case_guid':tables[SUMMARY]['rows'][1]['GUID']=tables[SUMMARY]['rows'][0]['GUID']
            elif defect=='type':tables[SUMMARY]['rows'][1]['Type']='Linear Static'
            elif defect=='axis':tables[SPECTRUM]['rows'][0]['LoadName']='U2'
            elif defect=='angle':tables[SPECTRUM]['rows'][0]['Angle']='90'
            elif defect=='units':tables[COMBOS]['field_metadata']['units_by_field']['SF']='kN'
            elif defect=='context':src['vs04_basis_probe']['read_only_invariant_proven']=False
            elif defect=='missing_table':del tables[SUMMARY]
            else:tables[COMBOS]['rows'][0]['SF']='NaN'
            full, ratios, pairs=result(src)
            self.assertEqual((ratios['expected_count'],ratios['not_proven_count']),(6,6),defect)
            self.assertEqual(pairs['not_proven_count'],6)
            self.assertEqual({r['combination'] for r in ratios['items']},{s[0] for s in definitions()})
            self.assertFalse(full['coverage_known'])

    def test_header_and_continuation_conflict_cannot_select_last_operator(self):
        for defect in ('missing_first','contradiction','row_count'):
            src=snapshot();tab=src['vs04_basis_probe']['table_reads'][COMBOS]
            if defect=='missing_first':tab['rows'][0]['Type']='None'
            elif defect=='contradiction':tab['rows'][1]['Type']='Envelope'
            else:tab['row_count']-=1
            _, ratios, _=result(src)
            self.assertEqual(ratios['expected_count'],6)
            self.assertEqual(next(r for r in ratios['items'] if r['combination']=='N1')['status'],UNKNOWN)

    def test_modal_reference_must_have_native_modal_type_and_function_identity(self):
        for defect in ('static_reference', 'spectrum_reference', 'wrong_type', 'unknown_type', 'blank_function'):
            src = snapshot(); tables = src['vs04_basis_probe']['table_reads']
            if defect == 'static_reference': tables[SPECTRUM]['rows'][0]['ModalCase'] = 'G'
            elif defect == 'spectrum_reference': tables[SPECTRUM]['rows'][0]['ModalCase'] = 'RSY'
            elif defect == 'wrong_type': tables[SUMMARY]['rows'][0]['Type'] = 'Linear Static'
            elif defect == 'unknown_type': tables[SUMMARY]['rows'][0]['Type'] = 'Unknown'
            else: tables[SPECTRUM]['rows'][0]['Function'] = ' '
            full, ratios, pairs = result(src)
            self.assertFalse(full['coverage_known'], defect)
            self.assertEqual((ratios['expected_count'], ratios['not_proven_count']), (6, 6), defect)
            self.assertEqual(pairs['not_proven_count'], 6)
        src = snapshot(); src['vs04_basis_probe']['table_reads'][SUMMARY]['rows'][0]['Type'] = 'Modal - Eigen'
        self.assertEqual(result(src)[1]['met_count'], 4)

    def test_no_selected_pair_and_missing_probe_stay_honest_about_scope(self):
        full, ratios, pairs=result(snapshot([definitions()[4]]))
        self.assertEqual((ratios['status'],ratios['evaluated_count'],ratios['not_applicable_count']),(NA,0,1))
        self.assertEqual(pairs['status'],NA)
        full, ratios, pairs=result({})
        self.assertEqual(full['observed_combination_count'],0)
        self.assertFalse(full['coverage_known'])
        self.assertEqual(ratios['status'],UNKNOWN)

    def test_unrelated_flags_and_case_name_conventions_do_not_authorize(self):
        src=snapshot(); expected=bind_earthquake_combinations(src)
        src.update(formal_compliance='PASS', combination_roles_approved=True, D='2.5', full_sign_envelope=True)
        self.assertEqual(bind_earthquake_combinations(src),expected)


class DeliveryTests(unittest.TestCase):
    def test_single_capture_report_ui_catalog_and_immutable_receipts(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); calls=[]
            def capture(case):calls.append(case);return snapshot()
            server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(root,live_capture=capture))
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            def get(route):
                with urlopen(base+route,timeout=10) as response:return response.read()
            try:
                with urlopen(Request(base+'/api/live-suite?case=Modal',data=b'',method='POST'),timeout=10) as response:
                    run_id=json.load(response)['run_id']
                before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
                report=json.loads(get('/api/export-checks?run_id='+run_id))
                package=report['earthquake_combinations']
                self.assertEqual([c['met_count'] for c in package['checks']],[4,2])
                self.assertEqual(report['source_controls'],bind_source_controls(snapshot()))
                ids=[r['check_id'] for r in report['check_inventory']['entries']]
                for check in package['checks']:self.assertEqual(ids.count(check['check_id']),1)
                html=get('/report/print?run_id='+run_id).decode()
                for check in package['checks']:
                    self.assertIn(check['result_sha256'],html)
                    self.assertIn(check['check_id'],html)
                self.assertIn('Zarf seçenekleri',html)
                self.assertIn('FULL_PLUS_MINUS_SIGN_ENVELOPE_NOT_PROVEN',html)
                registry=json.loads(get('/api/check-registry'))
                self.assertEqual(registry['implemented_check_count'],16)
                for row in registry['checks']:
                    if row['check_id'].startswith('earthquake_'):self.assertEqual(row['tab_id'],5)
                self.assertEqual(json.loads(get('/api/export-checks?run_id='+run_id)),report)
                self.assertEqual(before,{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})
                self.assertEqual(calls,['Modal'])
            finally:server.shutdown();server.server_close();thread.join(3)


if __name__=='__main__':unittest.main()
