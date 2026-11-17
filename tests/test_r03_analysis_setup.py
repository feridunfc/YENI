"""R03 source gate tests through the current combined ETABS request."""
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.basis_probe import capture_basis_probe
from tbdy_next.engineering.analysis_setup import (
    DESIGN_COMBOS, STATIC_CASES, STAGE, audit_model_analysis_setup, bind_analysis_setup,
)
from tbdy_next.receipts import canonical_bytes
from tbdy_next.vs05_d4_source_authority import COMBOS, SUMMARY
from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs04e_basis import ProbeSap
from test_vs04_numerics import numeric_source


def capture_table(key, columns, values):
    return {
        "status": "CAPTURED", "table_key": key, "fields": columns, "row_count": len(values),
        "rows": [dict(zip(columns, row)) for row in values],
        "field_metadata": {"status": "OK", "field_keys": columns,
                           "units_by_field": {field: "" for field in columns}},
    }


def basis_probe():
    records = (
        capture_table(SUMMARY, ["Name", "Type", "GUID"], [
            ("gravity", "Linear Static", "case-1"), ("spectrum-any-name", "Response Spectrum", "case-2")]),
        capture_table(COMBOS, ["Name", "Type", "LoadName", "SF", "GUID"], [
            ("service-in-its-name", "Linear Add", "spectrum-any-name", "1", "combo-1"),
            ("service-in-its-name", "None", "gravity", "1.2", "None"),
            ("envelope-any-name", "Envelope", "service-in-its-name", "1", "combo-2"),
            ("Duct_Seis_not_a_role", "Linear Add", "gravity", "1.4", "combo-3")]),
        capture_table(DESIGN_COMBOS, ["ComboName", "ComboType"], [
            ("service-in-its-name", "Strength"), ("envelope-any-name", "Strength"),
            ("Duct_Seis_not_a_role", "Service")]),
        capture_table(STATIC_CASES, ["Name", "StiffType", "NonlinCase"], [
            ("gravity", "P-Delta", "None"), ("gravity", "None", "None")]),
    )
    return {"schema": "tbdy.next.vs04e.basis-source-probe.v1",
            "source_mode": "LIVE_ETABS", "read_only_invariant_proven": True,
            "units_before": 6, "units_after": 6, "display_cases_before": [], "display_cases_after": [],
            "table_reads": {table["table_key"]: table for table in records}}


class AnalysisSetupTests(unittest.TestCase):
    def test_combination_names_do_not_supply_project_roles_or_order(self):
        result = audit_model_analysis_setup(basis_probe())
        self.assertTrue(result["definition_coverage_known"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["design_selection_type_counts"], {"Strength": 2, "Service": 1})
        self.assertFalse(result["design_demand_authorized"])
        self.assertFalse(result["analysis_order_proven"])
        self.assertEqual(result["linear_static_stiffness_counts"], {"P-Delta": 1})
        combos = {row["combination"]: row for row in result["combination_audit"]}
        self.assertEqual(combos["service-in-its-name"]["spectral_case_references"], ["spectrum-any-name"])
        self.assertTrue(combos["service-in-its-name"]["selected_for_strength"])
        self.assertEqual(combos["envelope-any-name"]["spectral_case_references"], ["spectrum-any-name"])
        self.assertIn("NON_SUM_OPERATOR_OR_UNKNOWN_OPERATOR",
                      combos["envelope-any-name"]["nonconcurrent_source_reasons"])
        self.assertEqual(combos["Duct_Seis_not_a_role"]["spectral_case_references"], [])
        self.assertFalse(combos["Duct_Seis_not_a_role"]["selected_for_strength"])

    def test_empty_unread_foreign_and_conflicting_sources_are_distinct(self):
        raw = basis_probe()
        raw["table_reads"][DESIGN_COMBOS] = capture_table(DESIGN_COMBOS, ["ComboName", "ComboType"], [])
        result = audit_model_analysis_setup(raw)
        self.assertEqual(result["design_selection_count"], 0)
        self.assertIn("STRENGTH_DESIGN_COMBINATION_SELECTION_EMPTY", result["blocker_codes"])
        raw["table_reads"][DESIGN_COMBOS] = capture_table(
            DESIGN_COMBOS, ["ComboName", "ComboType"], [("foreign", "Strength")])
        result = audit_model_analysis_setup(raw)
        self.assertEqual(result["diagnostics"]["unresolved_selections"], ["foreign"])
        raw["table_reads"][DESIGN_COMBOS]["table_key"] = COMBOS
        result = audit_model_analysis_setup(raw)
        self.assertIsNone(result["design_selection_count"])
        self.assertIn("TABLE_IDENTITY_CONFLICT", result["diagnostics"]["design_selection"])
        raw["table_reads"][COMBOS]["rows"][0]["LoadName"] = "missing"
        result = audit_model_analysis_setup(raw)
        self.assertFalse(result["definition_coverage_known"])
        self.assertIn("COMBINATION_GRAPH_UNRESOLVED", result["blocker_codes"])
        raw["units_after"] = 12
        result = bind_analysis_setup({"source_mode": "LIVE_ETABS", "vs04_basis_probe": raw,
                                     "capture_metadata": {"vs04_same_session_capture": True}})
        self.assertIsNone(result["design_selection_count"])
        self.assertIn("SAME_RUN_ANALYSIS_SETUP_CAPTURE_UNPROVEN", result["blocker_codes"])

    def test_read_only_capture_includes_design_selection_beyond_probe_limit(self):
        sap = ProbeSap()
        db = sap.DatabaseTables
        db.keys[-1] = DESIGN_COMBOS
        original = db.selected
        payload = capture_basis_probe(sap, max_tables=1)
        self.assertIn(DESIGN_COMBOS, db.readkeys)
        self.assertIn(DESIGN_COMBOS, payload["table_reads"])
        self.assertEqual(payload["candidate_table_count"], 3)
        self.assertEqual(db.selected, original)
        absent = capture_basis_probe(ProbeSap(), max_tables=1)
        self.assertEqual(absent["table_reads"][DESIGN_COMBOS]["status"], "NOT_LISTED")

    def test_combined_request_exports_the_same_sealed_gate_and_rejects_changed_receipt(self):
        calls = []

        def capture(case):
            calls.append(case)
            data = fake_live_suite(case)
            data["analysis_sources"] = numeric_source()
            data["vs04_basis_probe"] = basis_probe()
            data["capture_metadata"]["vs04_same_session_capture"] = True
            return data

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, live_capture=capture)) as server:
                worker = Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    base = f"http://127.0.0.1:{server.server_port}"
                    request = Request(base + "/api/live-vs04?case=Modal", data=b"", method="POST")
                    with urlopen(request, timeout=8) as response:
                        body = json.load(response)
                    run_id = body["run_id"]
                    url = base + "/api/export-checks?run_id=" + run_id
                    with urlopen(url, timeout=8) as response:
                        export = json.load(response)
                    with urlopen(base + "/report/print?run_id=" + run_id, timeout=8) as response:
                        html = response.read().decode("utf-8")
                    self.assertEqual(body["analysis_setup"], export["analysis_setup"])
                    self.assertEqual(body["analysis_setup"]["design_selection_count"], 3)
                    self.assertIn("R03", html)
                    self.assertIn("service-in-its-name", html)
                    self.assertEqual(calls, ["Modal"])
                    receipt_path = next((root / run_id).glob(f"*-{STAGE}.json"))
                    receipt = json.loads(receipt_path.read_bytes())
                    self.assertEqual(export["source_provenance"]["analysis_setup_receipt_sha256"],
                                     receipt.pop("receipt_sha256"))
                    receipt["payload"]["design_selection_count"] = 1
                    receipt["receipt_sha256"] = sha256(canonical_bytes(receipt)).hexdigest()
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    with self.assertRaises(HTTPError) as rejected:
                        urlopen(url, timeout=8)
                    self.assertEqual(rejected.exception.code, 404)
                    receipt_path.unlink()
                    with self.assertRaises(HTTPError) as missing:
                        urlopen(url, timeout=8)
                    self.assertEqual(missing.exception.code, 404)
                finally:
                    server.shutdown()
                    worker.join(timeout=3)
