"""One combined run owns the selected combinations, native forces and axial result."""
from __future__ import annotations

from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tbdy_next.column_engine.source_bank import FORCE_SIGNATURE
from tbdy_next.engineering.column_axial import PREFERENCES, STAGE, column_strength_plan
from tbdy_next.engineering.column_pmm_section import BAR_SIZES, COLUMN_REINFORCING, MECHANICAL, REBAR_DATA, SCHEMA
from tbdy_next.frame_force_capture import ForceSelectionRestoreError, capture_frame_forces
from tbdy_next.receipts import canonical_bytes
from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_r03_analysis_setup import basis_probe, capture_table
from test_vs03 import source as material_source
from test_vs04_numerics import numeric_source


STATIC = "Duct_Seis_not_a_role"
SPECTRAL = "service-in-its-name"
ENVELOPE = "envelope-any-name"


class OutputFixture:
    def __init__(self, *, omit_min=False, fail_restore=False):
        self.sap = Mock()
        self.sap.GetModelIsLocked.return_value = True
        self.sap.GetPresentUnits.return_value = 6
        self.setup = self.sap.Results.Setup
        self.cases = {"gravity": True, "spectrum-any-name": False}
        self.combos = {STATIC: True, SPECTRAL: False, ENVELOPE: False}
        self.original = {"cases": self.cases.copy(), "combos": self.combos.copy()}
        self.sap.LoadCases.GetNameList.return_value = (2, list(self.cases), 0)
        self.sap.RespCombo.GetNameList.return_value = (3, list(self.combos), 0)
        self.setup.GetCaseSelectedForOutput.side_effect = lambda name: (self.cases[name], 0)
        self.setup.GetComboSelectedForOutput.side_effect = lambda name: (self.combos[name], 0)
        self.setup.SetCaseSelectedForOutput.side_effect = (
            lambda name, flag: 1 if fail_restore else (self.cases.__setitem__(name, flag), 0)[1]
        )
        self.setup.SetComboSelectedForOutput.side_effect = lambda name, flag: (self.combos.__setitem__(name, flag), 0)[1]
        self.setup.DeselectAllCasesAndCombosForOutput.side_effect = self.clear
        self.omit_min = omit_min
        self.sap.Results.FrameForce.side_effect = self.frame_force

    def clear(self):
        self.cases.update(dict.fromkeys(self.cases, False))
        self.combos.update(dict.fromkeys(self.combos, False))
        return 0

    def frame_force(self, member, item_type, count, *arrays):
        assert item_type == 0 and count == 0 and len(arrays) == 13
        states = {
            STATIC: [("Single Value", -1100.0)],
            SPECTRAL: [("Max", 300.0), ("Min", -900.0)],
            ENVELOPE: [("Max", -50.0), ("Min", -2250.0)],
        }
        if self.omit_min and member == "C1":
            states[ENVELOPE].pop()
        rows = [(member, station, member + "-elm", station, name, step, 0.0, axial, 2.0, 3.0, 4.0, 5.0, 6.0)
                for name, selected in self.combos.items() if selected
                for step, axial in states[name] for station in (0.0, 2.0)]
        raw = [len(rows), *map(list, zip(*rows)), 0]
        assert len(raw) == len(FORCE_SIGNATURE)
        return raw

    def capture(self, *, combinations):
        return capture_frame_forces(self.sap, members=("C1", "C2"), combinations=tuple(combinations))


class ColumnAxialIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.outputs = OutputFixture()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.root, live_capture=self.capture))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)
        self.base_run = self.post({"case": "Modal"})["run_id"]

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(3)
        self.server.server_close()
        self.temp.cleanup()

    def post(self, query):
        req = Request(self.url + "/api/live-vs04?" + urlencode(query, doseq=True), data=b"", method="POST")
        with urlopen(req, timeout=8) as response:
            return json.load(response)

    def get(self, path):
        with urlopen(self.url + path, timeout=8) as response:
            return response.read()

    def query(self, source, names=()):
        return {"case": "Modal", "check": "column-axial", "base_run_id": self.base_run,
                "combination_source": source, "combination": names}

    def capture(self, case, *, column_axial_request=None):
        data = fake_live_suite(case)
        data["analysis_sources"] = numeric_source()
        data["next_capture"] = material_source()
        data["vs04_basis_probe"] = basis_probe()
        data["capture_metadata"]["vs04_same_session_capture"] = True
        if column_axial_request:
            plan = column_strength_plan(data, column_axial_request)
            self.assertEqual(plan["blockers"], [])
            data["column_axial"] = {
                "request": column_axial_request,
                "design_preferences": capture_table(PREFERENCES, ["GammaC", "GammaS"], [("1.5", "1.15")]),
                "force_source": self.outputs.capture(combinations=[c["name"] for c in plan["combinations"]]),
            }
            if column_axial_request.get("pmm_member"):
                section = capture_table(COLUMN_REINFORCING, ["Name", "RebarMatL", "RebarMatC", "ReinfConfig", "IsDesigned",
                    "Cover", "NumBars2Dir", "NumBars3Dir", "BarSizeLong", "BarSizeCorn", "BarSizeConf",
                    "SpacingConf", "NumCBars2", "NumCBars3"],
                    [("C40", "B420C", "B420C", "Rectangular", "Yes", "0.04", "4", "4", "20", "20", "10", "0.15", "3", "2")])
                sizes = capture_table(BAR_SIZES, ["Name", "Diameter", "Area"], [
                    ("20", "0.02", "0.000314"), ("10", "0.01", "0.0000785")])
                steel = capture_table(REBAR_DATA, ["Material", "Fy"], [("B420C", "420000")])
                elastic = capture_table(MECHANICAL, ["Material", "E1"], [("B420C", "200000000")])
                for table, units in ((section, {"Cover": "m", "SpacingConf": "m"}), (sizes, {"Diameter": "m", "Area": "m2"}),
                                     (steel, {"Fy": "kN/m2"}), (elastic, {"E1": "kN/m2"})):
                    table["field_metadata"]["units_by_field"].update(units)
                data["column_axial"]["pmm_section_source"] = {
                    "schema": SCHEMA, "model_locked_before": True, "model_locked_after": True,
                    "units_before": 6, "units_after": 6,
                    "table_reads": {t["table_key"]: t for t in (section, sizes, steel, elastic)},
                }
        return data

    def test_etabs_strength_selection_guard_calculation_receipt_and_html(self):
        ack = self.post(self.query("ETABS_STRENGTH"))
        rid = ack["run_id"]
        result = json.loads(self.get("/api/export-checks?run_id=" + rid))
        axial = result["column_axial"]
        self.assertEqual(axial["status"], "NUMERICAL_COMPLETE")
        self.assertEqual(axial["evaluated_member_combination_count"], 4)
        self.assertEqual(axial["observed_exceedance_count"], 1)
        self.assertEqual(axial["columns"][0]["governing"]["step_type"], "Min")
        self.assertEqual(axial["columns"][1]["governing"]["nd_kn"], 2250)
        self.assertEqual(axial["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(self.outputs.cases, self.outputs.original["cases"])
        self.assertEqual(self.outputs.combos, self.outputs.original["combos"])
        self.assertIn(b"Column axial compression", self.get("/report/print?run_id=" + rid))
        receipt = next((self.root / rid).glob(f"*-{STAGE}.json"))
        record = json.loads(receipt.read_bytes())
        self.assertEqual(record["payload"], axial)
        record.pop("receipt_sha256")
        record["payload"]["columns"][0]["governing"]["nd_kn"] = 1.0
        record["receipt_sha256"] = sha256(canonical_bytes(record)).hexdigest()
        receipt.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(HTTPError) as error:
            self.get("/api/export-checks?run_id=" + rid)
        self.assertEqual(error.exception.code, 404)

    def test_saved_set_uses_exact_names_and_missing_envelope_stays_partial(self):
        self.outputs.omit_min = True
        rid = self.post(self.query("SAVED_DEFAULTS", [STATIC, ENVELOPE]))["run_id"]
        result = json.loads(self.get("/api/export-checks?run_id=" + rid))["column_axial"]
        self.assertEqual(result["status"], "NUMERICAL_PARTIAL")
        self.assertEqual(result["evaluated_member_combination_count"], 3)
        partial = result["columns"][0]
        self.assertEqual(partial["status"], "PARTIAL")
        self.assertEqual(partial["governing"]["combination"], STATIC)
        self.assertEqual(partial["combination_checks"][1]["reason"], "SCALAR_AXIAL_MIN_MAX_PAIR_UNVERIFIED")
        calls = self.outputs.sap.Results.FrameForce.call_count
        with self.assertRaises(HTTPError) as error:
            self.post(self.query("SAVED_DEFAULTS", ["Not a current model combination"]))
        self.assertEqual(error.exception.code, 422)
        self.assertEqual(self.outputs.sap.Results.FrameForce.call_count, calls)

    def test_assigned_design_groups_are_bound_to_the_same_capture(self):
        query = self.query("ASSIGNED_DESIGN")
        assigned = {"gravity": [STATIC], "ductile": [SPECTRAL]}
        query["assignments"] = json.dumps(assigned)
        rid = self.post(query)["run_id"]
        result = json.loads(self.get("/api/export-checks?run_id=" + rid))
        axial = result["column_axial"]
        self.assertEqual(axial["status"], "NUMERICAL_COMPLETE")
        self.assertEqual(axial["combination_plan"]["source"], "ASSIGNED_DESIGN")
        self.assertEqual(axial["combination_plan"]["design_assignment"]["groups"], assigned)
        self.assertEqual(axial["evaluated_member_combination_count"], 4)
        self.assertEqual(result["design_assignments"]["check_groups"]["4.3"], ["gravity", "ductile"])
        forces = result["source_snapshot"]["column_axial"]["force_source"]
        self.assertEqual(set(forces["rowsets"]["C1"]["LoadCase"]), {STATIC, SPECTRAL})
        self.assertEqual(forces["output_selection_before"], forces["output_selection_after"])
        self.assertIn(b"Assigned design combinations", self.get("/report/print?run_id=" + rid))

        calls = self.outputs.sap.Results.FrameForce.call_count
        query["assignments"] = json.dumps({"gravity": [STATIC], "weight": [SPECTRAL]})
        with self.assertRaises(HTTPError) as error:
            self.post(query)
        self.assertEqual(error.exception.code, 422)
        self.assertEqual(self.outputs.sap.Results.FrameForce.call_count, calls)

    def test_force_failure_can_restore_and_restore_failure_rejects_source(self):
        fixture = OutputFixture()
        fixture.sap.Results.FrameForce.side_effect = ValueError("frame results unavailable")
        evidence = fixture.capture(combinations=[SPECTRAL])
        self.assertEqual(set(evidence["errors"]), {"C1", "C2"})
        self.assertEqual(evidence["output_selection_after"], fixture.original)
        with self.assertRaises(ForceSelectionRestoreError):
            OutputFixture(fail_restore=True).capture(combinations=[SPECTRAL])

    def test_pmm_uses_only_verified_signed_stations_and_seals_the_template_scenario(self):
        query = self.query("ASSIGNED_DESIGN")
        query.update(check="column-pmm", member="C1", assignments=json.dumps({"gravity": [STATIC], "ductile": [SPECTRAL]}))
        acknowledgement = self.post(query)
        rid = acknowledgement["run_id"]
        self.assertEqual(acknowledgement["column_pmm"]["member_id"], "C1")
        result = json.loads(self.get("/api/export-checks?run_id=" + rid))
        pmm = result["column_pmm"]
        self.assertEqual(pmm["status"], "NUMERICAL_COMPLETE")
        self.assertEqual((pmm["expected_station_count"], pmm["evaluated_station_count"]), (2, 2))
        self.assertEqual(pmm["section_evidence"]["reinforcement_role"], "ETABS_DESIGN_TEMPLATE")
        reinforcement = result["column_pmm_reinforcement"]
        self.assertEqual(len(reinforcement["bar_positions_mm"]), 12)
        self.assertEqual(reinforcement["tie_spacing_mm"], 150)
        self.assertEqual((reinforcement["tie_bars_parallel_2"], reinforcement["tie_bars_parallel_3"]), (3, 2))
        self.assertNotIn("bar_positions_mm", pmm["section_evidence"])
        self.assertEqual({row["combination"] for row in pmm["rows"]}, {STATIC})
        self.assertEqual({row["analysis_element_id"] for row in pmm["rows"]}, {"C1-elm"})
        self.assertEqual(next(row["status"] for row in pmm["combinations"] if row["name"] == SPECTRAL), "OUT_OF_SCOPE")
        self.assertAlmostEqual(pmm["rows"][0]["m2_design_knm"], 1100 * (15 + .03 * 400) / 1000)
        self.assertEqual(pmm["formal_compliance"], "NOT_PROVEN")
        html = self.get("/report/print?run_id=" + rid)
        self.assertIn(b"Column PMM and minimum eccentricity", html)
        self.assertIn(b"Tie spacing (mm)", html)
        self.assertEqual(result["native_demand_sources"]["status"], "BLOCKED_SOURCE")
        self.assertIn(b"Native load-case and modal force coverage", html)
        snapshot = json.loads(next((self.root / rid).glob("*-engine-results.json")).read_bytes())["payload"]
        self.assertEqual(snapshot["results"]["report_evidence"]["native_demand_sources"], result["native_demand_sources"])
        receipt = next((self.root / rid).glob("*-column-pmm.json"))
        record = json.loads(receipt.read_bytes())
        self.assertEqual(record["receipt_sha256"], result["source_provenance"]["column_pmm_receipt_sha256"])
        record.pop("receipt_sha256")
        record["payload"]["rows"][0]["m2_design_knm"] = 0
        record["receipt_sha256"] = sha256(canonical_bytes(record)).hexdigest()
        receipt.write_bytes(canonical_bytes(record))
        with self.assertRaises(HTTPError) as error:
            self.get("/api/export-checks?run_id=" + rid)
        self.assertEqual(error.exception.code, 404)

        calls = self.outputs.sap.Results.FrameForce.call_count
        with self.assertRaises(HTTPError) as error:
            self.post({**query, "member": "C1-elm"})
        self.assertEqual(error.exception.code, 422)
        self.assertEqual(self.outputs.sap.Results.FrameForce.call_count, calls)
