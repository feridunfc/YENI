"""VS04 observed ETABS fields: bounded source algebra and report integrity.

All numbers here are synthetic fixtures, never recorded real ETABS evidence.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.analysis_numerics import evaluate_analysis_numerics
from tbdy_next.analysis_sources import TABLES, capture_analysis_sources
from tbdy_next.quick_checks import check_registry
from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs03 import source as vs03_source, geo as vs03_geo
from test_vs04 import FakeSap


def _table(key, fields, data, units):
    return {
        "status": "CAPTURED", "table_key": key,
        "fields": fields, "rows": [dict(zip(fields, values)) for values in data],
        "row_count": len(data),
        "field_metadata": {
            "status": "OK", "table_version": 1, "field_keys": list(fields),
            "field_count": len(fields), "field_names": list(fields),
            "field_descriptions": [""] * len(fields),
            "units_by_field": {f: units.get(f, "") for f in fields},
            "importable_by_field": {f: False for f in fields},
        }
    }


def numeric_source():
    source = capture_analysis_sources(FakeSap(), modal_case="Modal")
    modal_fields = ["Case", "Mode", "Period", "Frequency", "CircFreq", "Eigenvalue"]
    modal_rows = [
        ["Modal", "1", "0.5", "2", "12.566370614359172", "157.91367041743"],
        ["Modal", "2", "0.25", "4", "25.132741228718345", "631.65468166972"],
    ]
    base_fields = ["OutputCase", "CaseType", "StepType", "StepNumber",
                   "FX", "FY", "FZ", "MX", "MY", "MZ", "X", "Y", "Z"]
    base_rows = [
        ["RSX", "LinRespSpec", "Max", "", "120", "5", "0", "1", "2", "3", "0", "0", "0"],
        ["RSY", "LinRespSpec", "Max", "", "3", "-140", "0", "5", "6", "7", "0", "0", "0"],
    ]
    drift_fields = ["Story", "OutputCase", "CaseType", "StepType", "StepNumber",
                    "Direction", "Drift", "Drift/", "Label", "X", "Y", "Z"]
    drift_rows = [
        ["+3", "RSX", "LinRespSpec", "Max", "", "X", "0.002", "500",
         "N11", "0", "0", "3"],
        ["+3", "RSY", "LinRespSpec", "Max", "", "Y", "0.004", "250",
         "N11", "0", "0", "3"],
    ]
    source["tables"] = {
        TABLES[0]: _table(TABLES[0], modal_fields, modal_rows,
                          {"Period": "sec", "Frequency": "cyc/sec",
                           "CircFreq": "rad/sec", "Eigenvalue": "rad2/sec2"}),
        TABLES[1]: _table(TABLES[1], base_fields, base_rows,
                          {**dict.fromkeys(("FX", "FY", "FZ"), "kN"),
                           **dict.fromkeys(("MX", "MY", "MZ"), "kN-m"),
                           **dict.fromkeys(("X", "Y", "Z"), "m")}),
        TABLES[2]: _table(TABLES[2], drift_fields, drift_rows,
                          {"Drift": "", "Drift/": "",
                           "X": "m", "Y": "m", "Z": "m"}),
    }
    source["numeric_stage_required"] = True
    return source


class NumericalSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = numeric_source()

    def test_five_source_components_observed_without_formal_compliance(self):
        result = evaluate_analysis_numerics(self.source)
        self.assertEqual(result["observed_component_count"], 5)
        self.assertEqual(result["status"],
                         "SOURCE_NUMERICAL_OBSERVED_PENDING_ENGINEERING_REVIEW")
        self.assertEqual(len(result["results"][0]["items"]), 2)
        self.assertEqual(result["results"][1]["items"][0]["absolute_reaction_kn"], "120")
        self.assertEqual(result["results"][2]["items"][0]["absolute_reaction_kn"], "140")
        self.assertEqual(result["results"][3]["items"][0]["observed_reciprocal_product"], "1.000")
        self.assertFalse(result["results"][3]["items"][0]["ratio_units_approved"])
        self.assertEqual(result["numeric_regulatory_checks_executed"], 0)
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertEqual(len(check_registry()), 8)

    def test_numerical_results_deterministic(self):
        self.assertEqual(evaluate_analysis_numerics(self.source),
                         evaluate_analysis_numerics(deepcopy(self.source)))

    def test_changed_modal_frequency_cannot_be_called_consistent(self):
        self.source["tables"][TABLES[0]]["rows"][0]["Frequency"] = "7"
        result = evaluate_analysis_numerics(self.source)
        self.assertEqual(result["results"][0]["status"], "NOT_PROVEN")
        self.assertEqual(result["observed_component_count"], 4)

    def test_duplicate_modal_mode_blocks_modal(self):
        self.source["tables"][TABLES[0]]["rows"][1]["Mode"] = "1"
        result = evaluate_analysis_numerics(self.source)
        self.assertEqual(result["results"][0]["status"], "NOT_PROVEN")

    def test_noncontiguous_modal_mode_blocks_modal(self):
        self.source["tables"][TABLES[0]]["rows"][1]["Mode"] = "3"
        result = evaluate_analysis_numerics(self.source)
        self.assertIn("MODE_POPULATION_NOT_CONTIGUOUS_FROM_ONE",
                      result["results"][0]["reason_codes"])

    def test_unknown_modal_units_are_not_accepted(self):
        self.source["tables"][TABLES[0]]["field_metadata"]["units_by_field"]["CircFreq"] = ""
        self.assertEqual(evaluate_analysis_numerics(self.source)["results"][0]["status"],
                         "NOT_PROVEN")

    def test_nonfinite_modal_numeric_rejected(self):
        self.source["tables"][TABLES[0]]["rows"][0]["Period"] = "NaN"
        self.assertEqual(evaluate_analysis_numerics(self.source)["results"][0]["status"],
                         "NOT_PROVEN")

    def test_base_case_kind_or_step_mismatch_blocks_source_component(self):
        for col, value in (("CaseType", "LinStatic"), ("StepType", "Min")):
            with self.subTest(col=col):
                payload = deepcopy(self.source)
                payload["tables"][TABLES[1]]["rows"][0][col] = value
                out = evaluate_analysis_numerics(payload)
                self.assertEqual(out["results"][1]["status"], "NOT_PROVEN")

    def test_duplicate_base_reaction_max_row_rejected(self):
        table = self.source["tables"][TABLES[1]]
        table["rows"].append(dict(table["rows"][0]))
        table["row_count"] += 1
        result = evaluate_analysis_numerics(self.source)
        self.assertIn("RESPONSE_SPECTRUM_MAX_ROW_MISSING_OR_AMBIGUOUS",
                      result["results"][1]["reason_codes"])

    def test_base_units_cannot_be_guessed(self):
        self.source["tables"][TABLES[1]]["field_metadata"]["units_by_field"]["FX"] = ""
        self.assertEqual(evaluate_analysis_numerics(self.source)["results"][1]["status"],
                         "NOT_PROVEN")

    def test_drift_ratio_reciprocal_mismatch_blocks_only_target(self):
        self.source["tables"][TABLES[2]]["rows"][0]["Drift/"] = "100"
        result = evaluate_analysis_numerics(self.source)
        self.assertEqual(result["results"][3]["status"], "NOT_PROVEN")
        self.assertEqual(result["results"][4]["status"], "SOURCE_ARITHMETIC_OBSERVED")
        self.assertEqual(result["numeric_regulatory_checks_executed"], 0)

    def test_missing_story_and_duplicate_drift_identity_rejected(self):
        payload = deepcopy(self.source)
        payload["tables"][TABLES[2]]["rows"][0]["Story"] = ""
        self.assertEqual(evaluate_analysis_numerics(payload)["results"][3]["status"],
                         "NOT_PROVEN")
        table = self.source["tables"][TABLES[2]]
        table["rows"].append(dict(table["rows"][0]))
        table["row_count"] += 1
        self.assertEqual(evaluate_analysis_numerics(self.source)["results"][3]["status"],
                         "NOT_PROVEN")

    def test_unknown_source_and_units_hold(self):
        self.assertEqual(evaluate_analysis_numerics(None)["status"], "SOURCE_UNAVAILABLE")
        self.source["units_after"] = 7
        self.assertEqual(evaluate_analysis_numerics(self.source)["observed_component_count"], 0)


class Vs04RealDisplayFormatTests(unittest.TestCase):
    """Live-observed rendering patterns; actual eigen rows remain unprovided."""

    def test_fourteen_live_short_period_formats_are_rounding_consistent(self):
        from decimal import Decimal
        observed = [
            ("83", "0.033", "30.628", "192.4411"),
            ("84", "0.032", "31.567", "198.3402"),
            ("85", "0.029", "34.916", "219.3814"),
            ("88", "0.025", "40.502", "254.4835"),
            ("89", "0.021", "46.533", "292.3781"),
            ("90", "0.021", "48.276", "303.3263"),
            ("91", "0.018", "54.533", "342.6434"),
            ("92", "0.017", "57.378", "360.5154"),
            ("93", "0.016", "64.505", "405.2968"),
            ("95", "0.012", "81.911", "514.6626"),
            ("96", "0.012", "86.01", "540.4196"),
            ("98", "0.008", "130.042", "817.0804"),
            ("99", "0.005", "221.99", "1394.8061"),
            ("100", "0.004", "228.588", "1436.2635"),
        ]
        for mode, t, f, w in observed:
            with self.subTest(mode=mode):
                payload = numeric_source()
                table = payload["tables"][TABLES[0]]
                row = table["rows"][0]
                row.update(Period=t, Frequency=f, CircFreq=w,
                           Eigenvalue=str((Decimal(w)**2).quantize(Decimal("0.01"))))
                table["rows"], table["row_count"] = [row], 1
                result = evaluate_analysis_numerics(payload)["results"][0]
                self.assertEqual(result["status"], "SOURCE_ARITHMETIC_OBSERVED")
                self.assertEqual(result["items"][0]["comparison_basis"],
                                 "EXACT_DISPLAY_PRECISION_INTERVAL")
        # The eigenvalue above was synthesized to test the interval algorithm,
        # NOT taken from ETABS. No live numerical acceptance follows from this.

    def test_six_live_drift_fraction_displays(self):
        observations = (
            ("X","0.000776","1/1289"),
            ("X","0.000797","1/1255"),
            ("X","0.000509","1/1963"),
            ("Y","0.001196","1/836"),
            ("Y","0.00118","1/848"),
            ("Y","0.000387","1/2587"),
        )
        for direction, drift, shown in observations:
            with self.subTest(direction=direction, shown=shown):
                payload = numeric_source()
                row = next(r for r in payload["tables"][TABLES[2]]["rows"]
                           if r["Direction"] == direction)
                row["Drift"],row["Drift/"] = drift,shown
                result = evaluate_analysis_numerics(payload)["results"][3 if direction=="X" else 4]
                self.assertEqual(result["status"], "SOURCE_ARITHMETIC_OBSERVED")
                self.assertEqual(result["items"][0]["reciprocal_display_encoding"],
                                 "UNITY_OVER_DENOMINATOR")
                self.assertFalse(result["items"][0]["ratio_units_approved"])

    def test_invalid_fraction_and_spurious_tolerance_are_rejected(self):
        for bad in ("2/1289","1/0","1/01289","1/100"," 1/1289 ",
                    "1/1289/2","1/inf"):
            with self.subTest(bad=bad):
                payload = numeric_source()
                payload["tables"][TABLES[2]]["rows"][0].update(
                    Drift="0.000776", **{"Drift/":bad})
                self.assertEqual(evaluate_analysis_numerics(payload)["results"][3]["status"],
                                 "NOT_PROVEN")
        payload = numeric_source()
        payload["tables"][TABLES[0]]["rows"][0].update(
            Period="0.005",Frequency="221.99",
            CircFreq="1436.2635",Eigenvalue="2062852.84")
        self.assertEqual(evaluate_analysis_numerics(payload)["results"][0]["status"],
                         "NOT_PROVEN")


class Vs04NumericalReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls = []
        def live(case):
            self.calls.append(case)
            payload = fake_live_suite(case)
            payload["next_capture"] = vs03_source()
            payload["geometry_capture"] = vs03_geo()
            payload["analysis_sources"] = numeric_source()
            return payload
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.root, live_capture=live))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.tmp.cleanup()

    def _run(self):
        request = Request(self.base + "/api/live-vs04?case=Modal",
                          data=b"", method="POST")
        with urlopen(request, timeout=7) as resp:
            return json.loads(resp.read())

    def test_one_run_contains_eight_legacy_checks_and_separate_numerics(self):
        reply = self._run()
        self.assertEqual(reply["vs04_numerics"]["observed_component_count"], 5)
        self.assertEqual(reply["vs04_numerics"]["numeric_regulatory_checks_executed"], 0)
        rid = reply["run_id"]
        with urlopen(self.base + "/api/export-checks?run_id=" + rid, timeout=7) as resp:
            report = json.loads(resp.read())
        self.assertEqual(len(report["checks"]), 8)
        self.assertEqual(report["vs04_numerics"]["observed_component_count"], 5)
        self.assertEqual(report["engineering_release"], "NOT_READY")
        self.assertEqual(len(self.calls), 1)
        with urlopen(self.base + "/report/print?run_id=" + rid, timeout=7) as resp:
            html = resp.read().decode("utf-8")
        self.assertIn("VS04 · Sayısal kaynak tutarlılığı", html)
        self.assertIn("BASE_REACTION_X", html)
        self.assertEqual(len(self.calls), 1, "Exports must not call ETABS")

    def test_missing_or_forged_numeric_receipt_blocks_export(self):
        for tamper in ("missing", "forged"):
            with self.subTest(tamper=tamper):
                rid = self._run()["run_id"]
                receipt = next((self.root / rid).glob("*-vs04-numerics.json"))
                if tamper == "missing":
                    receipt.unlink()
                else:
                    receipt.write_text(receipt.read_text(encoding="utf-8").replace(
                        "SOURCE_ARITHMETIC_OBSERVED", "FORGED_PASS"), encoding="utf-8")
                with self.assertRaises(HTTPError) as err:
                    urlopen(self.base + "/api/export-checks?run_id=" + rid, timeout=7)
                self.assertEqual(err.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
