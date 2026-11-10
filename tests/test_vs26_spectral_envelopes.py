from contextlib import closing
from copy import deepcopy
import json
import unittest

from column_spectral_fixture import SpectralBank
from tbdy_next.column_engine.native_archive import BankError, NativeArchive, digest
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.spectral_envelope import build_spectral_envelopes, spectral_projection, COMPONENTS


def evaluate(fixture=None):
    raw = (fixture or SpectralBank()).build()
    bank = recover_column_bank(raw)
    bank["run_id"] = "RUN-SYNTHETIC"
    with closing(NativeArchive(raw)) as archive:
        return build_spectral_envelopes(bank, archive)


def first(result, case="RS_SUM"):
    return next(r for r in result["rows"] if r["output_case"] == case and r["member_id"] == "C_SYNTHETIC_1" and r["station_key"]["ObjSta"] == 0)


class SpectralEnvelopeTests(unittest.TestCase):
    def test_independent_signed_center_amplitude_and_all_six_native_bounds(self):
        result = evaluate(); row = first(result)
        self.assertEqual((result["eligible_combination_count"], result["expected_pair_count"], result["matched_rows"], result["scalar_comparisons"]), (2, 16, 32, 192))
        self.assertEqual(result["source_coverage_status"], "SOURCE_COVERAGE_COMPLETE")
        self.assertEqual(result["over_tolerance_components"], 0)
        self.assertEqual(row["center"], dict(zip(COMPONENTS, [-87.5, 4, -5.5, 7, 8.5, -10])))
        self.assertEqual(row["spectral_radius"], dict(zip(COMPONENTS, [11.5, 23, 34.5, 46, 57.5, 69])))
        self.assertEqual(row["native_bounds"]["P"], {"lower": -99, "upper": -76})
        self.assertEqual(row["bounds"]["N"], {"lower": 76, "upper": 99})
        self.assertEqual(row["bounds"]["T"], {"lower": -39, "upper": 53})
        for component in COMPONENTS:
            b = row["native_bounds"][component]
            self.assertEqual((b["lower"]+b["upper"])/2, row["center"][component])
            self.assertEqual((b["upper"]-b["lower"])/2, row["spectral_radius"][component])

    def test_signed_static_coefficients_are_not_absolute_amplitudes(self):
        row = first(evaluate())
        q = next(t for t in row["source_terms"] if t["native_key"]["LoadCase"] == "Q")
        self.assertEqual(q["factor"], -.5)
        self.assertEqual(row["center"]["P"], -87.5)
        self.assertEqual(row["center"]["M3"], -10)

    def test_negative_rs_coefficient_preserves_symmetric_bounds_and_original_factor(self):
        fixture = SpectralBank()
        fixture.combos["RS_SUM"][1][2] = (0, "RS", -1)
        row = first(evaluate(fixture))
        self.assertEqual(row["status"], "NUMERICAL_MATCH")
        self.assertEqual(row["bounds"]["M2"], {"lower": -49, "upper": 66})
        self.assertEqual(row["source_terms"][2]["factor"], -1)

    def test_captured_100_30_and_2p5_0p75_are_not_reapplied(self):
        result = evaluate()
        row = first(result, "CAPTURED_HIGH")
        self.assertEqual(row["bounds"]["N"], {"lower": 58.75, "upper": 116.25})
        self.assertEqual(row["bounds"]["M2"], {"lower": -135.25, "upper": 152.25})
        for case, factor in (("RS_SUM", 1), ("CAPTURED_HIGH", 2.5)):
            pattern = next(s for s in result["combinations"] if s["combination"] == case)["coefficient_context"]["captured_directional_pattern"]
            self.assertTrue(pattern["is_100_30_pattern"])
            self.assertEqual(pattern["primary_factor"], factor)
            self.assertEqual(pattern["secondary_to_primary"], .3)
        self.assertEqual(result["spectral_cases"][0]["loads"][0]["scale"], 10)
        self.assertFalse(result["spectrum_scale_reapplied"])
        self.assertFalse(result["strength_amplification_reapplied"])

    def test_case_name_does_not_establish_direction_or_code_acceptance(self):
        fixture = SpectralBank()
        fixture.calls[("LoadCases.ResponseSpectrum.GetLoads", "case", "RS")]["raw_response"][4] = ["Custom"]
        result = evaluate(fixture)
        self.assertIsNone(next(s for s in result["combinations"] if s["combination"] == "RS_SUM")["coefficient_context"]["captured_directional_pattern"])
        self.assertEqual(result["matched_rows"], 32)
        self.assertFalse(result["code_rule_qualified"])

    def test_equal_bounds_keep_both_native_steps(self):
        fixture = SpectralBank()
        for rows in fixture.forces.values():
            for r in rows:
                scale = (fixture.members.index(r[0])+1) * (1 if r[1] == 0 else 2 if r[2].endswith("A") else 3 if r[1] == 2 else 4)
                if r[4] in ("RS", "SECOND_SPECTRUM"):
                    r[7:] = [0]*6
                elif r[4] in ("RS_SUM", "CAPTURED_HIGH"):
                    r[7:] = [v*scale for v in [-87.5, 4, -5.5, 7, 8.5, -10]]
        row = first(evaluate(fixture))
        self.assertEqual(row["bounds"]["N"], {"lower": 87.5, "upper": 87.5})
        self.assertEqual({r["native_key"]["StepType"] for r in row["native_steps"]}, {"Max", "Min"})
        self.assertEqual(len({r["source_row_id"] for r in row["native_steps"]}), 2)

    def test_exact_element_and_element_station_are_never_collapsed(self):
        result = evaluate()
        rows = [r for r in result["rows"] if r["member_id"] == "C_SYNTHETIC_1" and r["output_case"] == "RS_SUM" and r["station_key"]["ObjSta"] == 2]
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["station_key"]["ElmSta"] for r in rows}, {0, 2})
        self.assertEqual({r["bounds"]["N"]["upper"] for r in rows}, {198, 297})
        for row in rows:
            for source in row["source_terms"] + row["native_steps"]:
                self.assertEqual({k: source["native_key"][k] for k in row["station_key"]}, row["station_key"])

    def test_missing_target_step_preserves_expected_pair_and_gap(self):
        f = SpectralBank(); f.forces[f.members[0]].remove(f.source_row("RS_SUM", "Min"))
        r = evaluate(f)
        self.assertEqual(r["expected_pair_count"], 16)
        self.assertEqual(r["unresolved_pair_count"], 1)
        self.assertEqual(r["source_coverage_status"], "PARTIAL")
        self.assertIsNone(first(r)["bounds"])

    def test_missing_leaf_is_not_zero_filled(self):
        f = SpectralBank(); f.forces[f.members[0]].remove(f.source_row("SECOND_SPECTRUM"))
        r = evaluate(f)
        self.assertEqual(r["unresolved_pair_count"], 2)
        self.assertIn("LEAF_ROW_MISSING", first(r)["reason"])

    def test_nonzero_and_unknown_steps_are_not_projected_to_zero(self):
        for target, field, value in (("RS_SUM", 6, 1), ("RS", 6, 1), ("RS", 5, "Min"), ("G", 5, "Step")):
            with self.subTest(target=target, field=field):
                f = SpectralBank(); f.source_row(target, "Single Value" if target == "G" else "Max")[field] = value
                row = first(evaluate(f))
                self.assertEqual(row["status"], "SOURCE_UNRESOLVED")
                self.assertIsNone(row["bounds"])

    def test_extra_native_step_and_extra_leaf_fail_explicitly(self):
        for case in ("RS_SUM", "RS"):
            with self.subTest(case=case):
                f = SpectralBank(); extra = deepcopy(f.source_row(case)); extra[6] = 1
                f.forces[f.members[0]].append(extra)
                self.assertEqual(first(evaluate(f))["status"], "SOURCE_UNRESOLVED")

    def test_negative_spectral_max_is_not_replaced_with_absolute_value(self):
        f = SpectralBank(); f.source_row("RS")[10] = -40
        row = first(evaluate(f))
        self.assertIn("NEGATIVE_SPECTRAL_MAX_AMPLITUDE:RS:T", row["reason"])
        self.assertEqual(row["scalar_comparisons"], 0)

    def test_source_mismatch_and_inverted_native_interval_are_distinct(self):
        f = SpectralBank(); f.source_row("RS_SUM")[11] += .001
        r = evaluate(f)
        self.assertEqual(r["replay_status"], "NUMERICAL_MISMATCH")
        self.assertEqual(r["source_coverage_status"], "SOURCE_COVERAGE_COMPLETE")
        self.assertEqual(r["over_tolerance_components"], 1)
        self.assertEqual(first(r)["bounds"]["M2"]["upper"], 66)
        f = SpectralBank(); f.source_row("RS_SUM", "Min")[11] = 100
        self.assertEqual(first(evaluate(f))["reason"], "NATIVE_ENVELOPE_ORDER_INVALID")

    def test_declared_source_tolerance_is_used_for_both_steps(self):
        f = SpectralBank(); f.source_row("RS_SUM")[11] += 5e-10
        r = evaluate(f)
        self.assertEqual(r["replay_status"], "NUMERICAL_MATCH")
        self.assertEqual(r["relative_tolerance"], "1e-12")
        self.assertGreater(r["maximum_absolute_difference_by_unit"]["kNm"], 0)

    def test_unsupported_definitions_are_listed_without_interval_recursion(self):
        f = SpectralBank()
        f.combos["NESTED_RS"] = (0, [(1, "RS_SUM", 1)])
        f.combos["DUP_RS"] = (0, [(0, "RS", 1), (0, "RS", .3)])
        f.combos["SRSS_RS"] = (2, [(0, "RS", 1)])
        f.combos["MIXED_MODAL"] = (0, [(0, "MODAL", 1), (0, "RS", 1)])
        r = evaluate(f); scopes = {s["combination"]: s for s in r["combinations"]}
        for name in ("ENV", "NESTED_RS", "DUP_RS", "SRSS_RS", "MIXED_MODAL"):
            self.assertEqual(scopes[name]["scope"], "OUTSIDE_RECIPE")
            self.assertTrue(scopes[name]["reason"])
            self.assertFalse(any(row["output_case"] == name for row in r["rows"]))

    def test_missing_member_station_population_cannot_be_complete(self):
        f = SpectralBank(); f.forces[f.members[1]] = []
        r = evaluate(f)
        self.assertEqual(r["members_without_station_population"], [f.members[1]])
        self.assertEqual(r["source_coverage_status"], "PARTIAL")
        self.assertEqual(r["selected_member_count"], 2)

    def test_bad_native_units_never_gain_a_matched_envelope(self):
        f = SpectralBank(); f.force_units = 5
        r = evaluate(f)
        self.assertEqual(r["matched_rows"], 0)
        self.assertNotEqual(r["source_coverage_status"], "SOURCE_COVERAGE_COMPLETE")

    def test_unstable_capture_has_no_complete_source_authority(self):
        f = SpectralBank(); f.context["identity_unchanged"] = False
        r = evaluate(f)
        self.assertEqual(r["matched_rows"], 32)
        self.assertEqual(r["replay_status"], "NOT_PROVEN")
        self.assertFalse(r["capture_context_observed"])

    def test_arithmetic_overflow_retains_gap_and_serializable_output(self):
        f = SpectralBank(); f.combos["RS_SUM"][1][2] = (0, "RS", 1e308)
        r = evaluate(f)
        self.assertEqual(first(r)["status"], "SOURCE_UNRESOLVED")
        self.assertIsNone(first(r)["bounds"])
        json.dumps(r, allow_nan=False)

    def test_archive_binding_and_duplicate_source_ids_are_rejected(self):
        raw = SpectralBank().build(); bank = recover_column_bank(raw)
        with closing(NativeArchive(raw)) as archive:
            bad = deepcopy(bank); bad["source_archive_sha256"] = "different"
            with self.assertRaisesRegex(BankError, "ARCHIVE_BINDING"): build_spectral_envelopes(bad, archive)
            bad = deepcopy(bank); bad["force_states"].append(deepcopy(bad["force_states"][0]))
            with self.assertRaisesRegex(BankError, "FORCE_BINDING"): build_spectral_envelopes(bad, archive)

    def test_coherently_altered_leaves_targets_and_rehashed_row_ids_are_rejected(self):
        raw = SpectralBank().build(); bank = recover_column_bank(raw)
        with closing(NativeArchive(raw)) as archive:
            for rehash in (False, True):
                with self.subTest(rehash=rehash):
                    bad = deepcopy(bank)
                    for row in bad["force_states"]:
                        if row["Obj"] == "C_SYNTHETIC_1" and row["ObjSta"] == 0 and row["LoadCase"] in ("G", "RS_SUM", "CAPTURED_HIGH"):
                            row["P"] += 1000
                            if rehash:
                                row["source_row_id"] = digest({"archive": archive.sha256, "call": row["call_id"],
                                    "index": row["source_row_index"], "values": [row[k] for k in ("Obj", "ObjSta", "Elm", "ElmSta", "LoadCase", "StepType", "StepNum", *COMPONENTS)]})
                    with self.assertRaisesRegex(BankError, "NATIVE_FORCE_BINDING"):
                        build_spectral_envelopes(bad, archive)

    def test_native_definition_population_and_story_bindings_are_checked(self):
        raw = SpectralBank().build(); bank = recover_column_bank(raw)
        with closing(NativeArchive(raw)) as archive:
            for kind in ("factor", "case_type", "story", "population"):
                bad = deepcopy(bank)
                if kind == "factor": bad["combination_definitions"][1]["terms"][0]["factor"] = 7
                if kind == "case_type": bad["case_definitions"][0]["case_type"] = 4
                if kind == "story": bad["members"][0]["context"]["frame"]["story_label"] = "OTHER"
                if kind == "population": bad["members"].pop()
                with self.subTest(kind=kind), self.assertRaisesRegex(BankError, "SPECTRAL_NATIVE_"):
                    build_spectral_envelopes(bad, archive)

    def test_result_definitions_never_alias_accepted_bank_input(self):
        raw = SpectralBank().build(); bank = recover_column_bank(raw); before = deepcopy(bank)
        with closing(NativeArchive(raw)) as archive:
            result = build_spectral_envelopes(bank, archive)
        result["combinations"][0]["definition"]["terms"][0]["factor"] = 999
        self.assertEqual(bank, before)

    def test_capture_context_cannot_be_promoted_in_memory(self):
        f = SpectralBank(); f.context["identity_unchanged"] = False
        raw = f.build(); bank = recover_column_bank(raw); bank["capture_context_observed"] = True
        with closing(NativeArchive(raw)) as archive, self.assertRaisesRegex(BankError, "CAPTURE_CONTEXT_MISMATCH"):
            build_spectral_envelopes(bank, archive)

    def test_no_envelope_becomes_design_vector_or_code_approved_result(self):
        r = evaluate()
        self.assertEqual((r["design_demand_authority"], r["formal_compliance"], r["engineering_release"]), ("DENIED", "NOT_PROVEN", "NOT_READY"))
        for key in ("physical_concurrency_proven", "code_rule_qualified", "analysis_generation_qualified", "static_candidate_population_changed", "final_design_eligible"):
            self.assertIs(r[key], False)
        self.assertTrue(all(row["concurrent_force_vector"] is None and not row["final_design_eligible"] for row in r["rows"]))

    def test_projection_filters_before_pagination_and_does_not_mutate_cached_rows(self):
        r = evaluate(); p = spectral_projection(r, member_id="C_SYNTHETIC_2", output_case="RS_SUM", offset=1, limit=2)
        self.assertEqual(p["demand_page"]["total"], 4)
        self.assertEqual(len(p["demand_page"]["rows"]), 2)
        self.assertNotIn("rows", p["column_spectral_envelopes"])
        p["demand_page"]["rows"][0]["bounds"]["N"]["upper"] = 0
        self.assertTrue(all(row["bounds"]["N"]["upper"] > 0 for row in r["rows"]))
