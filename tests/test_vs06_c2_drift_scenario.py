"""VS06-C2: observed source math + explicit wall assumptions, no fake code PASS."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
import unittest

from tbdy_next.story_physical_source import review_story_physical_source
from tbdy_next.story_slot_ledger import build_story_slot_ledger
from tbdy_next.effective_drift_readiness import review_effective_drift_readiness
from tbdy_next.vs06_drift_scenario import DriftScenarioError, evaluate_drift_scenario, options
from tbdy_next.web import make_handler
from test_vs06_story_slot_ledger import source_record, synthetic_12_of_16
from test_vs05_story_drift_binding import seal
from test_quick_suite import fake_live_suite


CATALOG = json.loads(
    (Path(__file__).resolve().parents[1] / "config/dag/tbdy_r1c_94_candidate.json")
    .read_text(encoding="utf-8"))


def scenario_report(pair=None):
    source, record = pair or source_record()
    ledger = build_story_slot_ledger(source, record)
    physical = review_story_physical_source(source, record, ledger)
    ready = review_effective_drift_readiness(source, record, ledger, physical, CATALOG)
    return {
        "run_id": "RUN-" + "a" * 32,
        "story_drift": record,
        "vs06_effective_drift_readiness": ready,
        "source_snapshot": {"vs05_delta_source": source},
        "source_provenance": {"input_sha256": "f" * 64},
    }


class Vs06C2Numerics(unittest.TestCase):
    def test_default_is_brittle_and_numeric_is_computed(self):
        data = evaluate_drift_scenario(scenario_report())
        self.assertEqual(data["scenario_input"]["wall_type"], "BRITTLE")
        self.assertEqual(data["scenario_input"]["wall_load_pattern"], "LC_WDL")
        self.assertEqual(data["scenario_input"]["wall_mode"], "LOAD_PATTERN_BEAM_CANDIDATE")
        self.assertEqual(data["limit"], "0.008")
        self.assertEqual(data["source_numeric_count"], 1)
        self.assertEqual(data["expected_story_direction_count"], 4)
        self.assertEqual(data["missing_source_count"], 3)
        row = next(x for x in data["rows"] if x["source_delta_mm"])
        self.assertEqual(Decimal(row["effective_delta_mm"]), Decimal("3.4920000") * Decimal(7) / Decimal("1.5"))
        self.assertLess(
            abs(Decimal(row["lambda_effective_ratio"]) -
                Decimal("0.0034920") * Decimal(7) / Decimal("1.5") * Decimal("0.5") / Decimal("4.5")),
            Decimal("1e-25"))
        self.assertEqual(row["conditional_numeric_condition"], "CONDITIONAL_WITHIN_LIMIT")
        self.assertEqual(data["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(data["result_kind"], "CONDITIONAL_SENSITIVITY_SCENARIO")

    def test_brittle_vs_flexible_limit_but_no_experimental_approval(self):
        r = scenario_report()
        b = evaluate_drift_scenario(r, {"wall_type": "BRITTLE"})
        f = evaluate_drift_scenario(r, {"wall_type": "FLEXIBLE"})
        self.assertEqual(Decimal(f["limit"]), Decimal(b["limit"]) * 2)
        self.assertEqual(f["flexible_capacity_warning"], "FLEXIBLE_CONNECTION_TEST_PROOF_REQUIRED")
        self.assertFalse(f["flexible_branch_capacity_accepted"])
        xb = next(x for x in b["rows"] if x["utilization_ratio"])
        xf = next(x for x in f["rows"] if x["utilization_ratio"])
        self.assertLess(
            abs(Decimal(xb["utilization_ratio"]) - Decimal(xf["utilization_ratio"]) * 2),
            Decimal("1e-25"))
        self.assertEqual(f["formal_compliance"], "NOT_PROVEN")

    def test_coverage_does_not_interpolate_normative_limit(self):
        a = evaluate_drift_scenario(scenario_report(), {"coverage_pct": "100"})
        b = evaluate_drift_scenario(scenario_report(), {"coverage_pct": "20"})
        self.assertEqual(a["limit"], b["limit"])
        self.assertEqual(a["rows"], b["rows"])
        self.assertNotEqual(a["scenario_sha256"], b["scenario_sha256"])

    def test_12_of_16_stays_six_of_eight_conditional_primary(self):
        r = evaluate_drift_scenario(scenario_report(synthetic_12_of_16()))
        self.assertEqual((r["source_numeric_count"],r["missing_source_count"]), (6,2))
        self.assertEqual(len(r["rows"]), 8)
        top = [x for x in r["rows"] if x["story"] == "+14.50"]
        self.assertEqual(len(top), 2)
        self.assertTrue(all(x["conditional_numeric_condition"] == "SOURCE_DRIFT_MISSING" for x in top))

    def test_reject_nonfinite_lambda_and_unknown_source_inputs(self):
        for values in ({"lambda": "NaN"}, {"r": "0"}, {"wall_type": "MAGIC"},
                       {"coverage_pct": "110"}, {"unexpected": "1"},
                       {"opening_pct": "-2"}, {"wall_load_pattern": ""},
                       {"wall_load_pattern": " LC_WDL"}, {"wall_load_pattern": "LC_WDL\n"}):
            with self.subTest(values=values), self.assertRaises(DriftScenarioError):
                options(values)

    def test_source_not_captured_preserves_numeric_scenario(self):
        r = evaluate_drift_scenario(scenario_report())
        self.assertEqual(r["wall_candidate_inventory"]["source_status"],
                         "LOAD_PATTERN_SOURCE_NOT_CAPTURED")
        self.assertIsNone(r["wall_candidate_inventory"]["assumed_net_face_area_m2"])
        self.assertEqual(r["source_numeric_count"], 1)

    def test_manual_wall_length_assumption_computes_face_area(self):
        report = scenario_report()
        result = evaluate_drift_scenario(
            report,
            {"wall_mode": "MANUAL", "manual_wall_length_m": "15",
             "wall_height_m": "3", "coverage_pct": "60",
             "opening_pct": "20", "thickness_m": "0.20"})
        wall = result["wall_candidate_inventory"]
        self.assertEqual(wall["source_status"], "USER_MANUAL_LENGTH_ASSUMPTION")
        self.assertEqual(Decimal(wall["assumed_net_face_area_m2"]), Decimal("21.6"))
        self.assertEqual(Decimal(wall["assumed_wall_volume_m3"]), Decimal("4.32"))
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["source_numeric_count"], 1)

    def test_lc_wdl_source_candidates_and_assumed_area(self):
        report = scenario_report()
        geometry = {"tables": {"FRAME_ASSIGNMENTS": {
            "rows": [
                {"UniqueName": "B1", "Type": "Beam"},
                {"UniqueName": "B2", "Type": "Beam"},
                {"UniqueName": "C1", "Type": "Column"}]}}}
        wall = {
            "schema": "tbdy.next.etabs.generic-source-capture.v1",
            "status": "CAPTURED",
            "table_reads": {
                "Frame Loads Assignments - Distributed": {
                    "table_key": "Frame Loads Assignments - Distributed", "status": "CAPTURED",
                    "fields": ["UniqueName", "LoadPattern", "RelDistA", "RelDistB", "LoadType"],
                    "field_metadata": {"status": "OK", "field_keys":
                                       ["UniqueName", "LoadPattern", "RelDistA", "RelDistB", "LoadType"]},
                    "row_count": 4,
                    "rows": [
                        {"UniqueName": "B1", "LoadPattern": "LC_WDL",
                         "RelDistA": "0", "RelDistB": "0.7", "LoadType": "Force"},
                        {"UniqueName": "B1", "LoadPattern": "LC_WDL",
                         "RelDistA": "0.3", "RelDistB": "1", "LoadType": "Force"},
                        {"UniqueName": "B2", "LoadPattern": "LC_WALL",
                         "RelDistA": "0", "RelDistB": "1", "LoadType": "Force"},
                        {"UniqueName": "C1", "LoadPattern": "LC_WDL",
                         "RelDistA": "0", "RelDistB": "1", "LoadType": "Force"},
                    ]},
                "Beam Object Connectivity": {
                    "table_key": "Beam Object Connectivity", "status": "CAPTURED",
                    "fields": ["UniqueName", "Length"],
                    "field_metadata": {"status": "OK", "field_keys": ["UniqueName", "Length"],
                                       "units_by_field": {"Length": "m"}},
                    "row_count": 2,
                    "rows": [{"UniqueName": "B1", "Length": "5"},
                             {"UniqueName": "B2", "Length": "4"}],
                },
            },
        }
        report["source_snapshot"]["geometry_capture"] = geometry
        report["source_snapshot"]["vs06_wall_load_source"] = seal(wall)
        r = evaluate_drift_scenario(report, {"wall_height_m": "3", "coverage_pct": "80",
                                             "opening_pct": "25", "thickness_m": "0.2"})
        c = r["wall_candidate_inventory"]
        self.assertEqual(c["load_pattern"], "LC_WDL")
        self.assertEqual(c["candidate_beam_count"], 1)
        self.assertEqual(c["candidate_beams"], ["B1"])
        self.assertEqual(Decimal(c["candidate_total_length_m"]), Decimal("5"))
        self.assertEqual(Decimal(c["assumed_net_face_area_m2"]), Decimal("9"))
        self.assertEqual(Decimal(c["assumed_wall_volume_m3"]), Decimal("1.8"))
        self.assertEqual(r["formal_compliance"], "NOT_PROVEN")
        # A different exact ETABS pattern resolves only the other beam.
        alt = evaluate_drift_scenario(report, {"wall_load_pattern": "LC_WALL"})
        candidate = alt["wall_candidate_inventory"]
        self.assertEqual(candidate["load_pattern"], "LC_WALL")
        self.assertEqual(candidate["candidate_beams"], ["B2"])
        self.assertEqual(Decimal(candidate["candidate_total_length_m"]), Decimal("4"))
        self.assertEqual(alt["formal_compliance"], "NOT_PROVEN")

    def test_legacy_mode_name_defaults_to_real_lc_wdl_pattern(self):
        legacy = options({"wall_mode": "LC_WALL_BEAM_CANDIDATE"})
        self.assertEqual(legacy["wall_mode"], "LOAD_PATTERN_BEAM_CANDIDATE")
        self.assertEqual(legacy["wall_load_pattern"], "LC_WDL")

    def test_scenario_determinism_does_not_mutate_archived_inputs(self):
        report = scenario_report()
        original = deepcopy(report)
        one = evaluate_drift_scenario(report)
        two = evaluate_drift_scenario(report)
        self.assertEqual(one, two)
        self.assertEqual(report, original)
        self.assertEqual(len(one["scenario_sha256"]), 64)


class Vs06C2HttpIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls = []
        def capture(case):
            self.calls.append(case)
            source = fake_live_suite(case)
            generic, _ = source_record()
            source["vs05_delta_source"] = generic
            return source
        self.server = ThreadingHTTPServer(("127.0.0.1", 0),
                                          make_handler(self.root, live_capture=capture))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.tmp.cleanup()

    def test_live_once_then_scenario_and_json_html_no_com(self):
        req = Request(self.base + "/api/live-suite?case=Modal", data=b"", method="POST")
        with urlopen(req, timeout=10) as response:
            run = json.load(response)["run_id"]
        opts = urlencode({"r": "7", "i": "1.5", "lambda": "0.5",
                          "wall_type": "FLEXIBLE", "material": "RC"})
        with urlopen(self.base + "/api/vs06-drift-scenario?run_id="+run+"&"+opts) as response:
            result = json.load(response)
        self.assertEqual(result["source_numeric_count"], 1)
        self.assertEqual(result["limit"], "0.016")
        with urlopen(self.base + "/api/export-checks?run_id="+run+"&"+opts) as response:
            report = json.load(response)
        self.assertEqual(report["vs06_drift_scenario"], result)
        with urlopen(self.base + "/report/print?run_id="+run+"&"+opts) as response:
            html = response.read().decode("utf-8")
        self.assertIn("VS06-C2", html)
        self.assertIn("0.016", html)
        self.assertIn("FORMAL COMPLIANCE: NOT_PROVEN", html)
        self.assertEqual(self.calls, ["Modal"], "Report and scenario must not reconnect to ETABS")

    def test_invalid_scenario_never_triggers_new_capture(self):
        req = Request(self.base + "/api/live-suite?case=Modal", data=b"", method="POST")
        with urlopen(req, timeout=10) as response:
            run = json.load(response)["run_id"]
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/api/vs06-drift-scenario?run_id="+run+"&r=NaN")
        self.assertEqual(error.exception.code, 422)
        self.assertEqual(self.calls, ["Modal"])

    def test_ui_brittle_default_and_one_primary_live_button(self):
        with urlopen(self.base + "/") as response:
            html = response.read().decode("utf-8")
        with urlopen(self.base + "/quick.js") as response:
            js = response.read().decode("utf-8")
        self.assertEqual(html.count('id="runAllBtn"'), 1)
        self.assertIn('value="BRITTLE" selected', html)
        self.assertIn('value="LOAD_PATTERN_BEAM_CANDIDATE" selected', html)
        self.assertIn('id="c2WallLoadPattern"', html)
        self.assertIn('value="LC_WDL"', html)
        self.assertIn("wall_load_pattern: 'c2WallLoadPattern'", js)
        self.assertIn('id="c2Calculate"', html)
        self.assertIn("vs06-drift-scenario?run_id=", js)
        self.assertIn("activeScenarioQuery", js)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
