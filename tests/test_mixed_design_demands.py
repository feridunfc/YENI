"""Mixed static demand algebra and spectral evidence, with independent arithmetic.

Synthetic source fixtures prove source/algorithm contracts, not an approved
complete building model. The existing spectral bank owner remains authoritative.
"""
from copy import deepcopy
from fractions import Fraction
import json
import unittest
from unittest.mock import patch

from test_alpha_design_iteration import two_columns
from test_r10_live import _rowset
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.column_engine.spectral_envelope import observed_component_interval
from tbdy_next.engineering.alpha_iteration import qualify_story_alpha, build_demand_revision, revised_force_rows
from tbdy_next.engineering.mixed_demands import (
    native_graph, linear_coefficients, represent_linear_effect, earthquake_partition,
    earthquake_row, spectral_component_evidence, _number,
)


def table(key, rows):
    fields = list(rows[0])
    return {"table_key": key, "status": "CAPTURED", "rows": rows, "row_count": len(rows), "fields": fields,
            "field_metadata": {"status": "OK", "field_keys": fields, "units_by_field": dict.fromkeys(fields, "")}}


def mixed_fixture():
    source, axial, scope, dep, r10 = two_columns()
    content = {
        "Load Case Definitions - Summary": [
            {"Name": "BASE_A", "Type": "Linear Static", "GUID": "a"},
            {"Name": "ACTION_B", "Type": "Linear Static", "GUID": "b"}],
        "Load Combination Definitions": [
            {"Name": "G", "Type": "Linear Add", "LoadName": "BASE_A", "SF": "1", "GUID": "g"},
            {"Name": "Q", "Type": "Linear Add", "LoadName": "G", "SF": "1.2", "GUID": "q"},
            {"Name": "Q", "Type": "Linear Add", "LoadName": "ACTION_B", "SF": "1", "GUID": "q"}],
        "Load Case Definitions - Linear Static": [
            {"Name": "BASE_A", "LoadType": "Load", "LoadName": "p1", "LoadSF": "1"},
            {"Name": "ACTION_B", "LoadType": "Load", "LoadName": "p2", "LoadSF": "1"}],
        "Load Pattern Definitions": [
            {"LoadPat": "p1", "DesignType": "Dead", "SelfWtMult": "1"},
            {"LoadPat": "p2", "DesignType": "Quake", "SelfWtMult": "0"}],
    }
    source["vs04_basis_probe"] = {"table_reads": {k: table(k, v) for k, v in content.items()}}
    for combo in axial["combination_plan"]["combinations"]:
        combo["case_names"] = ["BASE_A"] if combo["name"] == "G" else ["BASE_A", "ACTION_B"]
    for uid, shear in (("C1", 100.), ("C2", -30.)):
        rows = list(native_frame_force_rows(source["column_axial"]["force_source"]["rowsets"][uid], uid))
        gravity = (-200., shear, shear, 7., 11., -13.)
        source["column_axial"]["force_source"]["rowsets"][uid] = _rowset([
            (*r[:7], *(gravity if r[4] == "G" else tuple(float(Fraction(str(g))*Fraction(6, 5)+Fraction(str(e)))
                                                        for g, e in zip(gravity, r[7:])))) for r in rows])
    return source, axial, scope, dep, r10


def spectral_fixture():
    source, axial, scope, dep, r10 = mixed_fixture()
    tables = source["vs04_basis_probe"]["table_reads"]
    k = "Load Case Definitions - Summary"
    tables[k] = table(k, tables[k]["rows"] + [{"Name": "RS", "Type": "Response Spectrum", "GUID": "rs"}])
    k = "Load Combination Definitions"
    tables[k] = table(k, tables[k]["rows"] + [
        {"Name": "S", "Type": "Linear Add", "LoadName": "BASE_A", "SF": ".9", "GUID": "s"},
        {"Name": "S", "Type": "Linear Add", "LoadName": "RS", "SF": ".3", "GUID": "s"}])
    axial["combination_plan"]["combinations"].append({"name": "S", "force_semantics": "SCALAR_COMPONENT_ENVELOPE"})
    scope["instances"] = []
    source["column_axial"]["force_source"].update(
        schema="tbdy.next.etabs-frame-force-source.v1", api="Results.FrameForce", units_code=6)
    for uid, rowset in source["column_axial"]["force_source"]["rowsets"].items():
        rows = list(native_frame_force_rows(rowset, uid))
        center, radius = (-90., 3., -4., 5., 6., -7.), (2., 4., 6., 8., 10., 12.)
        for sta in (0., 1.5, 3.):
            for step, sign in (("Max", 1), ("Min", -1)):
                rows.append((uid, sta, uid+"-1", sta, "S", step, 0., *[c+sign*r for c, r in zip(center, radius)]))
        source["column_axial"]["force_source"]["rowsets"][uid] = _rowset(rows)
        scope["instances"].append({"element_id": uid, "combination": "S", "analysis_element_coverage": {}, "configured_cut_coverage": {}})
    return source, axial, scope


class CoefficientAlgebraContracts(unittest.TestCase):
    def test_exact_rational_representation_no_least_squares(self):
        self.assertEqual(represent_linear_effect({"E": 1}, {"M": {"G": "1.2", "E": 1}, "G0": {"G": 1}}),
                         {"G0": "-6/5", "M": "1"})

    def test_two_gravity_loads_need_independent_information(self):
        with self.assertRaisesRegex(ValueError, "NOT_IDENTIFIABLE"):
            represent_linear_effect({"E": 1}, {"M": {"G": 1, "Q": 1, "E": 1}, "U": {"G": "1.4", "Q": "1.6"}})

    def test_redundant_rows_are_deterministic(self):
        observations = {"B": {"G": 2}, "A": {"G": 1}, "M": {"G": 1, "E": 1}}
        self.assertEqual(represent_linear_effect({"E": 1}, observations),
                         represent_linear_effect({"E": 1}, dict(reversed(list(observations.items())))))

    def test_no_observations_is_not_zero_quake(self):
        with self.assertRaisesRegex(ValueError, "NOT_IDENTIFIABLE"):
            represent_linear_effect({"E": 1}, {})

    def test_cycle_and_non_linear_rejected(self):
        for graph in ({"A": {"operator_etabs": "Linear Add", "rows": [{"ref_type": "COMBO", "ref": "A", "factor": 1}]}},
                      {"A": {"operator_etabs": "SRSS", "rows": [{"ref_type": "CASE", "ref": "E", "factor": 1}]}}):
            with self.assertRaises(ValueError): linear_coefficients("A", graph, {"E": {}})

    def test_nested_static_repeated_coefficients_cancel(self):
        graph = {"A": {"operator_etabs": "Linear Add", "rows": [
            {"ref_type": "CASE", "ref": "G", "factor": 2}, {"ref_type": "CASE", "ref": "G", "factor": -2},
            {"ref_type": "CASE", "ref": "E", "factor": ".3"}]}}
        self.assertEqual(linear_coefficients("A", graph, {"E": {}, "G": {}}), {"E": Fraction(3, 10)})

    def test_malformed_nonfinite_or_boolean_factor_rejected(self):
        for x in (True, "nan", "inf", "1e999", "1e-999999999", "0/0", "oops"):
            with self.subTest(value=x), self.assertRaises(ValueError): _number(x)


class MixedStaticContracts(unittest.TestCase):
    def test_real_loadsf_schema_and_native_roles(self):
        s, a, *_ = mixed_fixture()
        result = earthquake_partition(s, ["Q"], a["combination_plan"])
        self.assertEqual(result["recipes"]["Q"]["observation_weights"], {"G": "-6/5", "Q": "1"})
        self.assertTrue(result["recipes"]["Q"]["mixed"])

    def test_alpha_uses_earthquake_not_combined_shear(self):
        args = mixed_fixture(); before = deepcopy(args[0]); result = qualify_story_alpha(*args)
        self.assertEqual(result["status"], "QUALIFIED_REFERENCE")
        for case in result["cases"]:
            self.assertEqual((case["vis_kn"], case["vik_kn"], case["alpha"], case["factor"]), (80., 100., .8, 1.25))
            self.assertEqual([t["shear_kn"] for t in case["terms"]], [80., 20.])
            self.assertEqual(len(case["terms"][0]["earthquake_component_rows"]), 2)
        self.assertEqual(args[0], before)

    def test_revised_combined_m_v_not_compounded_n_and_t_unchanged(self):
        args = mixed_fixture(); s = args[0]; q = qualify_story_alpha(*args)
        revision = build_demand_revision(s, q["cases"], input_sha="test-source")
        rows = s["column_axial"]["force_source"]["rowsets"]["C1"]
        original = list(native_frame_force_rows(rows, "C1")); revised = revised_force_rows(rows, "C1", revision)
        for old, new in zip(original, revised):
            self.assertEqual(old[:7], new[:7]); self.assertEqual(old[7], new[7]); self.assertEqual(old[10], new[10])
            for index in (8, 9, 11, 12):
                self.assertEqual(new[index], old[index]*1.25 if old[4] == "Q" else old[index])
        self.assertEqual(revised, revised_force_rows(rows, "C1", revision))

    def test_missing_support_cut_preserves_blocked_whole_story(self):
        args = mixed_fixture(); rs = args[0]["column_axial"]["force_source"]["rowsets"]
        rows = list(native_frame_force_rows(rs["C2"], "C2"))
        rs["C2"] = _rowset([r for r in rows if not (r[4] == "G" and r[1] == 0)])
        q = qualify_story_alpha(*args)
        self.assertEqual(q["status"], "BLOCKED_INPUTS")
        self.assertTrue(any("CUT_MISSING_OR_AMBIGUOUS:G" in c for c in q["reason_codes"]))
        self.assertTrue(all(c["expected_member_ids"] == ["C1", "C2"] for c in q["cases"]))

    def test_other_element_side_cannot_supply_missing_support(self):
        args = mixed_fixture(); rs = args[0]["column_axial"]["force_source"]["rowsets"]["C1"]
        rs["Elm"][0] = "C1-other"
        self.assertEqual(qualify_story_alpha(*args)["status"], "BLOCKED_INPUTS")

    def test_native_roles_missing_not_inferred_from_names(self):
        args = mixed_fixture(); args[0]["vs04_basis_probe"]["table_reads"].pop("Load Pattern Definitions")
        self.assertEqual(qualify_story_alpha(*args)["status"], "BLOCKED_INPUTS")

    def test_other_pattern_role_is_unknown_not_gravity(self):
        args = mixed_fixture(); args[0]["vs04_basis_probe"]["table_reads"]["Load Pattern Definitions"]["rows"][0]["DesignType"] = "Other"
        self.assertEqual(qualify_story_alpha(*args)["status"], "BLOCKED_INPUTS")

    def test_inconsistent_sf_and_loadsf_rejected(self):
        args = mixed_fixture(); k = "Load Case Definitions - Linear Static"
        tables = args[0]["vs04_basis_probe"]["table_reads"]
        tables[k] = table(k, [{**r, "SF": "2"} for r in tables[k]["rows"]])
        self.assertTrue(any("FIELDS_CONFLICT" in c for c in qualify_story_alpha(*args)["reason_codes"]))

    def test_no_static_rank_cannot_use_spectral_max(self):
        args = mixed_fixture(); rs = args[0]["column_axial"]["force_source"]["rowsets"]
        for uid, rowset in rs.items():
            rs[uid] = _rowset([r for r in native_frame_force_rows(rowset, uid) if r[4] == "Q"])
        self.assertTrue(any("NOT_IDENTIFIABLE" in c for c in qualify_story_alpha(*args)["reason_codes"]))

    def test_observed_step_does_not_become_static_by_its_name(self):
        args = mixed_fixture(); rs = args[0]["column_axial"]["force_source"]["rowsets"]["C1"]
        rs["StepNum"][0] = 1.
        self.assertEqual(qualify_story_alpha(*args)["status"], "BLOCKED_INPUTS")


class SpectralIntervalContracts(unittest.TestCase):
    def test_independent_center_radius_and_compression_sign(self):
        x = observed_component_interval([-99, -19, -40, -39, -49, -79], [-76, 27, 29, 53, 66, 59])
        self.assertEqual(list(x["center_native"].values()), [-87.5, 4., -5.5, 7., 8.5, -10.])
        self.assertEqual(list(x["radius_native"].values()), [11.5, 23., 34.5, 46., 57.5, 69.])
        self.assertEqual(x["nd_bounds_kn"], [76., 99.]); self.assertFalse(x["physical_concurrency_proven"])

    def test_wrong_order_nonfinite_and_shape_are_not_zero_utilization(self):
        for lower, upper in (([0]*5, [1]*6), ([2]*6, [1]*6), ([float("nan")]*6, [1]*6)):
            with self.assertRaises(ValueError): observed_component_interval(lower, upper)

    def test_expected_member_pair_population_and_no_rescaling(self):
        args = spectral_fixture(); result = spectral_component_evidence(*args, input_sha="source")
        self.assertEqual(result["expected_pair_count"], 2)
        self.assertEqual(result["status_counts"], {"OBSERVED_INTERVALS_DECOMPOSED": 2})
        self.assertEqual(len(result["rows"][0]["cuts"]), 3)
        self.assertEqual(result["rows"][0]["spectral_case_coefficients"], {"RS": "3/10"})
        self.assertEqual(result["rows"][0]["cuts"][0]["radius_native"]["M3"], 12.)
        self.assertFalse(result["signed_alpha_input_eligible"])
        self.assertFalse(result["additional_directional_or_scale_factor_applied"])
        json.dumps(result, allow_nan=False)

    def test_configured_ulp_difference_does_not_invent_another_cut(self):
        args = spectral_fixture(); args[2]["configured_output_cuts"]["C1"]["cuts"][1]["object_station_m"] += 2e-16
        result = spectral_component_evidence(*args, input_sha="source")
        self.assertEqual(result["rows"][0]["expected_cut_count"], 3)
        self.assertEqual(result["status_counts"], {"OBSERVED_INTERVALS_DECOMPOSED": 2})

    def test_missing_min_step_stays_in_pair_and_cut_denominators(self):
        args = spectral_fixture(); rs = args[0]["column_axial"]["force_source"]["rowsets"]
        rs["C1"] = _rowset([r for r in native_frame_force_rows(rs["C1"], "C1") if not (r[4] == "S" and r[5] == "Min" and r[1] == 1.5)])
        result = spectral_component_evidence(*args, input_sha="source")
        self.assertEqual(result["expected_pair_count"], 2)
        self.assertEqual(result["rows"][0]["expected_cut_count"], 3)
        self.assertEqual(result["rows"][0]["status"], "NOT_PROVEN")
        self.assertEqual(result["rows"][1]["status"], "OBSERVED_INTERVALS_DECOMPOSED")

    def test_member_without_forces_is_not_removed(self):
        args = spectral_fixture(); args[0]["column_axial"]["force_source"]["rowsets"].pop("C2")
        result = spectral_component_evidence(*args, input_sha="source")
        self.assertEqual(result["expected_pair_count"], 2); self.assertEqual(result["rows"][1]["status"], "NOT_PROVEN")
        self.assertEqual(result["rows"][1]["required_cut_count"], 3)

    def test_unmapped_element_still_blocks_interval_authority(self):
        args = spectral_fixture(); args[2]["instances"][0]["analysis_element_coverage"] = {"reason": "UNMAPPED"}
        result = spectral_component_evidence(*args, input_sha="source")
        self.assertEqual(result["rows"][0]["status"], "NOT_PROVEN")

    def test_wrong_native_row_shape_becomes_visible_gap_not_exception(self):
        args = spectral_fixture(); args[0]["column_axial"]["force_source"]["rowsets"]["C1"]["P"].pop()
        result = spectral_component_evidence(*args, input_sha="source")
        self.assertEqual(result["rows"][0]["status"], "NOT_PROVEN")

    def test_envelope_operator_not_accepted_as_linear_sum(self):
        args = spectral_fixture()
        for row in args[0]["vs04_basis_probe"]["table_reads"]["Load Combination Definitions"]["rows"]:
            if row["Name"] == "S": row["Type"] = "Envelope"
        result = spectral_component_evidence(*args, input_sha="source")
        self.assertTrue(all(r["status"] == "NOT_PROVEN" for r in result["rows"]))

    def test_no_spectral_request_has_no_extra_artifact(self):
        args = mixed_fixture()
        self.assertIsNone(spectral_component_evidence(*args[:3], input_sha="source"))

    def test_registry_reuses_single_spectral_owner_without_node_promotion(self):
        from tbdy_next.engineering.pipeline import STAGES, _validate_dependency_contracts
        _validate_dependency_contracts()
        stages = [s for s in STAGES if s.key == "mixed-demand-components"]
        self.assertEqual(len(stages), 1)
        self.assertEqual([c.key for c in stages[0].consumes], ["column_axial", "pmm_scope"])
        self.assertEqual(stages[0].dag_nodes, ())


class ProjectionAndScopeContracts(unittest.TestCase):
    def test_wrong_units_do_not_produce_qualified_intervals(self):
        args = spectral_fixture(); args[0]["column_axial"]["force_source"]["units_code"] = 5
        r = spectral_component_evidence(*args, input_sha="s")
        self.assertEqual(r["status_counts"], {"NOT_PROVEN": 2})
        self.assertIn("NATIVE_FORCE_SCHEMA_OR_UNITS_UNQUALIFIED", r["reason_codes"])

    def test_duplicate_expected_instance_does_not_hide_scope_problem(self):
        args = spectral_fixture(); args[2]["instances"].append(deepcopy(args[2]["instances"][0]))
        r = spectral_component_evidence(*args, input_sha="s")
        self.assertIn("DUPLICATE_EXPECTED_MEMBER_COMBINATION", r["reason_codes"])
        self.assertEqual(r["status_counts"], {"NOT_PROVEN": 2})

    def test_blocked_upstream_pair_cannot_be_upgraded_by_complete_scalars(self):
        args = spectral_fixture(); args[2]["instances"][0].update(execution_status="BLOCKED", reason="BAD_SOURCE")
        r = spectral_component_evidence(*args, input_sha="s")
        self.assertEqual(r["rows"][0]["status"], "NOT_PROVEN")
        self.assertEqual(r["rows"][1]["status"], "OBSERVED_INTERVALS_DECOMPOSED")

    def test_html_is_projection_and_escapes_source_text(self):
        from tbdy_next.reporting import _mixed_components_html
        r = spectral_component_evidence(*spectral_fixture(), input_sha="s")
        r["rows"][0]["reason_codes"] = ["<script>bad</script>"]
        with patch("tbdy_next.engineering.mixed_demands.spectral_component_evidence", side_effect=AssertionError("solver")) as fn:
            html = _mixed_components_html(r)
        fn.assert_not_called(); self.assertNotIn("<script>", html); self.assertIn("&lt;script&gt;", html)
        self.assertIn("NOT concurrent", html)
