"""Independent VS09 oracles and source/receipt boundaries; synthetic fixtures only."""
from copy import deepcopy
from decimal import Decimal as D
from fractions import Fraction as F
from http.server import ThreadingHTTPServer
from itertools import combinations, permutations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from tbdy_next.source_control_bundle import (
    CHECKS, MET, UNMET, UNKNOWN, PERIODS, SPECTRUM_CASE, SPECTRUM_MODAL_TABLE,
    bind_source_controls, concrete_upper_subcondition, modal_spacing,
)
from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs03 import source as material_source
from test_vs05_story_delta import table
from test_vs07_soft_story_b2 import reseal


def snapshot(periods=("1", ".79"), method="CQC"):
    src = deepcopy(fake_live_suite("Modal"))
    src["next_capture"] = material_source()
    definitions = [{"Name": name, "ModalCase": "Modal", "ModalCombo": method,
        "DirCombo": "SRSS", "LoadName": axis, "CoordSys": "Global", "Angle": "0"}
        for name, axis in (("RSX", "U1"), ("RSY", "U2"))]
    src["vs04_basis_probe"] = {
        "schema": "tbdy.next.vs04e.basis-source-probe.v1", "read_only_invariant_proven": True,
        "units_before": 6, "units_after": 6, "display_cases_before": [], "display_cases_after": [],
        "table_reads": {SPECTRUM_CASE: table(SPECTRUM_CASE, list(definitions[0]), definitions, {"Angle": "deg"})}}
    modal_rows = [{"SpecCase": name, "ModalCase": "Modal", "Mode": str(i),
                   "Period": period, "DampRatio": ".07"}
                  for name in ("RSX", "RSY") for i, period in enumerate(periods, 1)]
    src["vs04_diaphragm_probe"] = {
        "schema": "tbdy.next.vs04g.diaphragm-modal-probe.v1", "units_before": 6, "units_after": 6,
        "display_selection_restored": True,
        "spectrum_modal_selected_cases": table(SPECTRUM_MODAL_TABLE, list(modal_rows[0]), modal_rows, {"Period": "sec"})}
    rows = [{"Case": "Modal", "Mode": str(i), "Period": value} for i, value in enumerate(periods, 1)]
    src["vs05_delta_source"] = reseal({
        "schema": "tbdy.next.etabs.generic-source-capture.v1", "status": "CAPTURED",
        "model": src["capture_metadata"]["model_filename"], "model_locked": True,
        "model_units_code": 6, "model_units_unchanged": True, "selection_restored": True,
        "table_reads": {PERIODS: table(PERIODS, list(rows[0]), rows, {"Period": "sec"})}})
    return src


def checks(src):
    return {c["check_id"]: c for c in bind_source_controls(src)["checks"]}


class IndependentArithmeticTests(unittest.TestCase):
    def test_upper_strength_boundary_and_scope_exceedance(self):
        for value, expected in (("79.999", MET), ("80", MET), ("80.001", UNMET), ("24", MET)):
            result = concrete_upper_subcondition(value)
            self.assertEqual(result["status"], expected)
        self.assertEqual(concrete_upper_subcondition("80.001")["strength_scope_observation"],
                         "ABOVE_TBDY_STRENGTH_SCOPE")
        # The new upper predicate does not silently reimplement/replace C25.
        self.assertEqual(concrete_upper_subcondition("24")["limit"], "80")

    def test_invalid_scalar_values_never_compute(self):
        for raw in (None, True, "NaN", "Infinity", "0", "-1", ""):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                concrete_upper_subcondition(raw)
            with self.subTest(period=raw), self.assertRaises(ValueError):
                modal_spacing({1: "1", 2: raw})

    def test_strict_srss_boundary_uses_unrounded_comparison(self):
        self.assertEqual(modal_spacing({1: "1", 2: ".7999999999"})["spacing_status"], MET)
        self.assertEqual(modal_spacing({1: "1", 2: ".8"})["spacing_status"], UNMET)
        self.assertEqual(modal_spacing({1: "1", 2: ".8000000001"})["spacing_status"], UNMET)
        three = modal_spacing({1: "1", 2: ".79", 3: ".63"})
        self.assertEqual(three["spacing_status"], MET)
        self.assertAlmostEqual(D(three["maximum_period_ratio"]), D(63) / 79, places=27)
        self.assertEqual(modal_spacing({1: "1", 2: ".79", 3: ".632"})["spacing_status"], UNMET)

    def test_adjacent_algorithm_against_independent_all_pairs_fraction_oracle(self):
        for values in (("1", ".79", ".63"), ("1", ".79", ".632"),
                       ("1", "1", ".5", ".2"), (".005", ".006", ".45", ".47")):
            oracle = [min(F(a), F(b)) / max(F(a), F(b)) for a, b in combinations(values, 2)]
            for permutation in permutations(enumerate(values, 1)):
                result = modal_spacing(dict(permutation))
                self.assertEqual(result["spacing_status"] == MET, all(q < F(4, 5) for q in oracle))
                self.assertEqual(result["all_distinct_pair_count"], len(oracle))
                self.assertAlmostEqual(D(result["maximum_period_ratio"]),
                                      D(max(oracle).numerator) / D(max(oracle).denominator), places=27)

    def test_single_mode_equal_periods_and_nonsequential_identities(self):
        one = modal_spacing({1: ".25"})
        self.assertEqual((one["mode_count"], one["all_distinct_pair_count"], one["spacing_status"]), (1, 0, MET))
        same = modal_spacing({2: ".5", 17: ".5"})
        self.assertEqual((same["maximum_period_ratio"], same["spacing_status"]), ("1", UNMET))
        for raw in ({}, {True: "1"}, {0: "1"}, {"1": "1"}):
            with self.assertRaises(ValueError): modal_spacing(raw)


class SourceContractTests(unittest.TestCase):
    def test_two_checks_same_source_and_no_authority_or_mutation(self):
        src = snapshot(); before = deepcopy(src)
        result = bind_source_controls(src)
        self.assertEqual(len(result["checks"]), 2)
        for c in result["checks"]:
            self.assertEqual(c["status"], MET, c["reason_codes"])
            self.assertEqual((c["formal_compliance"], c["engineering_release"], c["dag_execution_authority"]),
                             (UNKNOWN, "NOT_READY", "DENIED"))
        self.assertEqual(result, bind_source_controls(src))
        self.assertEqual(src, before)

    def test_material_units_and_name_do_not_change_numeric_strength(self):
        for unit, literal in (("kN/m2", "35000"), ("MPa", "35"), ("N/mm2", "35")):
            src = snapshot(); table = src["next_capture"]["material_table"]
            table["field_metadata"]["units_by_field"]["Fc"] = unit
            table["rows"][0]["Fc"] = literal
            # Numeric values govern, not class-looking material names.
            table["rows"][0]["Material"] = "C100/115"
            fact = src["geometry_capture"]["material_types"]["facts"].pop("C35/45")
            src["geometry_capture"]["material_types"]["facts"]["C100/115"] = fact
            result = checks(src)["concrete_fck_80"]
            self.assertEqual(result["status"], MET)
            self.assertEqual(D(result["items"][0]["fck_mpa"]), D(35))

    def test_missing_duplicate_wrong_table_or_unknown_units_keep_material_unproven(self):
        for defect in ("missing", "duplicate", "units", "table"):
            src = snapshot(); tab = src["next_capture"]["material_table"]
            if defect == "missing": tab["rows"].clear(); tab["row_count"] = 0
            elif defect == "duplicate": tab["rows"] *= 2; tab["row_count"] = 2
            elif defect == "units": tab["field_metadata"]["units_by_field"]["Fc"] = "psi"
            else: tab["table_key"] = "NOT_CONCRETE_STRENGTH"
            result = checks(src)
            self.assertEqual(result["concrete_fck_80"]["not_proven_count"], 1)
            self.assertEqual(result["modal_combination_spacing"]["evaluated_count"], 2)

    def test_unknown_material_fact_is_retained_alongside_valid_material(self):
        for invalid in (None, {"status": "TYPE_RESOLVED", "material_type_code": True},
                        {"status": "TYPE_RESOLVED", "material_type_code": 99}):
            src = snapshot()
            src["geometry_capture"]["material_types"]["facts"]["UNKNOWN"] = invalid
            result = checks(src)["concrete_fck_80"]
            self.assertEqual((result["expected_count"], result["evaluated_count"], result["not_proven_count"]), (2, 1, 1))

    def test_material_context_failure_does_not_block_modal_check(self):
        src = snapshot(); src["geometry_capture"]["unit_state_unchanged"] = False
        result = checks(src)
        self.assertEqual(result["concrete_fck_80"]["status"], UNKNOWN)
        self.assertEqual(result["modal_combination_spacing"]["status"], MET)

    def test_failed_material_context_preserves_all_observed_material_identities(self):
        for defect in ("table", "units", "type_source"):
            src = snapshot()
            types = src["geometry_capture"]["material_types"]
            types["facts"]["C40"] = deepcopy(types["facts"]["C35/45"])
            tab = src["next_capture"]["material_table"]
            tab["rows"].append({"Material": "C40", "Fc": "40000"}); tab["row_count"] += 1
            self.assertEqual(checks(src)["concrete_fck_80"]["evaluated_count"], 2)
            if defect == "table": tab["table_key"] = "WRONG_STRENGTH_TABLE"
            elif defect == "units": src["geometry_capture"]["unit_state_unchanged"] = False
            else: types["source_api"] = "UNREVIEWED_TYPE_SOURCE"
            result = checks(src)["concrete_fck_80"]
            self.assertEqual((result["expected_count"], result["not_proven_count"]), (2, 2))
            self.assertEqual({r["material_name"] for r in result["items"]}, {"C35/45", "C40"})

    def test_modal_and_directional_srss_are_distinct(self):
        src = snapshot(("1", ".95"))
        result = checks(src)["modal_combination_spacing"]
        self.assertEqual(result["met_count"], 2)
        for row in result["items"]:
            self.assertEqual(row["spacing_status"], UNMET)
            self.assertEqual(row["method_condition"], "CQC_SELECTED_SOURCE_ONLY")
            self.assertEqual(row["directional_combination"], "SRSS")
        for row in src["vs04_basis_probe"]["table_reads"][SPECTRUM_CASE]["rows"]:
            row["ModalCombo"] = "SRSS"; row["DirCombo"] = "CQC"
        self.assertEqual(checks(src)["modal_combination_spacing"]["unmet_count"], 2)

    def test_srss_at_exact_point_eight_is_not_permitted_by_spacing_rule(self):
        result = checks(snapshot(("1", ".8"), "SRSS"))["modal_combination_spacing"]
        self.assertEqual((result["evaluated_count"], result["unmet_count"]), (2, 2))
        self.assertEqual(result["items"][0]["method_condition"], "SRSS_SPACING_CONDITION_NOT_MET")

    def test_missing_duplicate_or_foreign_selected_mode_keeps_both_cases(self):
        for defect in ("missing", "duplicate", "foreign", "period"):
            src = snapshot(); tab = src["vs04_diaphragm_probe"]["spectrum_modal_selected_cases"]
            if defect == "missing": tab["rows"].pop(0)
            elif defect == "duplicate": tab["rows"].append(deepcopy(tab["rows"][0]))
            elif defect == "foreign": tab["rows"][0]["ModalCase"] = "FOREIGN"
            else: tab["rows"][0]["Period"] = "1.1"
            tab["row_count"] = len(tab["rows"])
            result = checks(src)["modal_combination_spacing"]
            self.assertEqual((result["expected_count"], result["evaluated_count"], result["not_proven_count"]), (2, 1, 1))
            self.assertEqual(result["items"][0]["status"], UNKNOWN)

    def test_bad_seal_units_model_or_missing_period_population_blocks_only_modal(self):
        for defect in ("seal", "units", "model", "missing_mode", "duplicate_mode"):
            src = snapshot(); delta = src["vs05_delta_source"]; tab = delta["table_reads"][PERIODS]
            if defect == "seal": delta["payload_sha256"] = "0" * 64
            elif defect == "units": tab["field_metadata"]["units_by_field"]["Period"] = "ms"
            elif defect == "model": delta["model"] = "FOREIGN.EDB"
            elif defect == "missing_mode": tab["rows"].pop()
            else: tab["rows"].append(deepcopy(tab["rows"][0]))
            tab["row_count"] = len(tab["rows"])
            if defect != "seal": src["vs05_delta_source"] = reseal(delta)
            result = checks(src)
            self.assertEqual(result["modal_combination_spacing"]["not_proven_count"], 2)
            self.assertEqual(result["concrete_fck_80"]["evaluated_count"], 1)

    def test_unsupported_or_multiple_case_definitions_do_not_pick_a_row(self):
        for defect in ("method", "duplicate", "missing", "angle"):
            src = snapshot(); tab = src["vs04_basis_probe"]["table_reads"][SPECTRUM_CASE]
            if defect == "method": tab["rows"][0]["ModalCombo"] = "UNKNOWN"
            elif defect == "duplicate": tab["rows"].append(deepcopy(tab["rows"][0]))
            elif defect == "missing": tab["rows"].pop(0)
            else: tab["rows"][0]["Angle"] = "90"
            tab["row_count"] = len(tab["rows"])
            result = checks(src)["modal_combination_spacing"]
            self.assertEqual((result["evaluated_count"], result["not_proven_count"]), (1, 1))

    def test_readonly_context_and_direction_bindings_required(self):
        for defect in ("selection", "units", "same_case", "blank_case", "failed_period_capture"):
            src = snapshot()
            if defect == "selection": src["vs04_basis_probe"]["display_cases_after"] = ["CHANGED"]
            elif defect == "units": src["vs04_diaphragm_probe"]["units_after"] = 9
            elif defect == "same_case": src["next_capture"]["y_case"] = "RSX"
            elif defect == "blank_case": src["next_capture"]["x_case"] = None
            else:
                src["vs05_delta_source"]["status"] = "ERROR"
                src["vs05_delta_source"] = reseal(src["vs05_delta_source"])
            self.assertEqual(checks(src)["modal_combination_spacing"]["not_proven_count"], 2)

    def test_spacing_does_not_add_five_percent_damping_restriction(self):
        src = snapshot(method="SRSS")
        result = checks(src)["modal_combination_spacing"]
        self.assertEqual(result["met_count"], 2)  # Synthetic DampRatio=.07 deliberately.
        self.assertIn("CQC_CORRELATION_DAMPING_AND_COMBINED_FORCES_NOT_EVALUATED", result["unevaluated_requirements"])

    def test_missing_sources_or_user_authority_flags_do_not_authorize_results(self):
        self.assertEqual(bind_source_controls({})["checks"], [])
        src = snapshot(); baseline = bind_source_controls(src)
        src.update(formal_compliance="PASS", srss_approved=True, concrete_verified=True)
        self.assertEqual(bind_source_controls(src), baseline)
        src["vs04_diaphragm_probe"] = None
        result = checks(src)
        self.assertEqual(result["modal_combination_spacing"]["status"], UNKNOWN)
        self.assertEqual(result["concrete_fck_80"]["status"], MET)


class DeliveryTests(unittest.TestCase):
    def test_same_capture_json_html_registry_and_historical_receipts(self):
        with TemporaryDirectory() as folder:
            root = Path(folder); calls = []
            def capture(case):
                calls.append(case)
                return snapshot(("1", ".95"))
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, live_capture=capture))
            thread = Thread(target=server.serve_forever, daemon=True); thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            def get(route):
                with urlopen(base + route, timeout=10) as response: return response.read()
            try:
                with urlopen(Request(base + "/api/live-suite?case=Modal", data=b"", method="POST"), timeout=10) as response:
                    run_id = json.load(response)["run_id"]
                before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                report = json.loads(get("/api/export-checks?run_id=" + run_id))
                result = report["source_controls"]
                self.assertEqual([c["evaluated_count"] for c in result["checks"]], [1, 2])
                ids = [r["check_id"] for r in report["check_inventory"]["entries"]]
                for spec in CHECKS: self.assertEqual(ids.count(spec.check_id), 1)
                html = get("/report/print?run_id=" + run_id).decode()
                for check in result["checks"]:
                    self.assertIn(check["check_id"], html)
                    self.assertIn(check["result_sha256"], html)
                for text in ("CQC_SELECTED_SOURCE_ONLY", "Mod birleştirme", "NOT_PROVEN"):
                    self.assertIn(text, html)
                registry = json.loads(get("/api/check-registry"))
                self.assertEqual(registry["implemented_check_count"], 16)
                self.assertEqual(json.loads(get("/api/export-checks?run_id=" + run_id)), report)
                self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()})
                self.assertEqual(calls, ["Modal"])
            finally:
                server.shutdown(); server.server_close(); thread.join(3)


if __name__ == "__main__":
    unittest.main()
