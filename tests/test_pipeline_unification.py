"""One pipeline owner: registry, column gates on the live path, Web/CLI equivalence."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tbdy_next.engineering.cli_adapter import _run_pipeline_replay
from tbdy_next.engineering.column_live_gates import project_column_gates
from tbdy_next.engineering.pipeline import STAGES, dag_coverage, stage_registry
import test_column_axial_live as live
from test_column_axial_live import SPECTRAL, STATIC


class RegistryContract(unittest.TestCase):
    def test_every_bound_node_exists_and_authority_stays_denied(self):
        coverage = dag_coverage()
        self.assertEqual(coverage["unknown_node_ids"], [])
        self.assertEqual(coverage["catalog_node_count"], 94)
        self.assertGreaterEqual(coverage["bound_node_count"], 20)
        self.assertEqual(coverage["bound_node_count"] + coverage["unbound_node_count"], 94)
        self.assertEqual(coverage["dag_execution_authority"], "DENIED")

    def test_stage_keys_and_receipt_names_are_single_owned(self):
        keys = [stage.key for stage in STAGES]
        self.assertEqual(len(keys), len(set(keys)))
        receipts = [name for stage in STAGES for name in stage.receipts]
        self.assertEqual(len(receipts), len(set(receipts)))
        self.assertEqual({row["mode"] for row in stage_registry()},
                         {"LIVE_SOURCE_RUN", "ARCHIVED_RECEIPT_SCENARIO", "OFFLINE_COLUMN_BANK"})

    def test_registered_receipt_names_match_the_stage_constants(self):
        from tbdy_next.engineering.analysis_setup import STAGE as SETUP
        from tbdy_next.engineering.column_axial import STAGE as AXIAL
        from tbdy_next.engineering.column_pmm import STAGE as PMM
        names = {name for stage in STAGES for name in stage.receipts}
        self.assertLessEqual({SETUP, AXIAL, PMM}, names)


def _axial(source: str, ductile: list[str], nd: float, tbdy_limit: float = 1000.0, ts500: float = 2000.0):
    plan = {"source": source, "blockers": [], "combinations": []}
    if source == "ASSIGNED_DESIGN":
        plan["design_assignment"] = {"groups": {"gravity": ["G"], "ductile": ductile}}
    check = lambda name: {"combination": name, "status": "OUTSIDE_LIMIT" if nd > ts500 else "WITHIN_LIMIT", "nd_kn": nd}
    return {"status": "NUMERICAL_COMPLETE", "combination_plan": plan, "columns": [{
        "element_id": "U1", "ts500_limit_kn": ts500, "tbdy_seismic_reference_limit_kn": tbdy_limit,
        "combination_checks": [check("G"), check("D")]}]}


def _pmm(role: str, bar_count=12, area=314.0, diameter=20.0):
    return {"member_id": "U1", "status": "NUMERICAL_COMPLETE", "analysis_order": "UNVERIFIED", "rows": [],
            "section_evidence": {"reinforcement_role": role, "bar_count": bar_count, "t2_mm": 800.0,
                                 "t3_mm": 800.0, "longitudinal_bar_area_mm2": area,
                                 "longitudinal_bar_diameter_mm": diameter, "fck_mpa": 35.0,
                                 "fcd_mpa": 35 / 1.5, "fyd_mpa": 365.2}}


class GateProjection(unittest.TestCase):
    source = {"column_axial": {}}

    def test_no_column_source_means_no_projection(self):
        self.assertIsNone(project_column_gates({}, _axial("ETABS_STRENGTH", [], 10)))
        self.assertIsNone(project_column_gates(self.source, None))

    def test_chk004_is_a_proven_fail_only_for_the_assigned_ductile_group(self):
        gates = project_column_gates(self.source, _axial("ASSIGNED_DESIGN", ["D"], 1500.0))
        self.assertEqual(gates["axial_gates"]["chk004_proven_exceedance_count"], 1)
        self.assertEqual(gates["axial_gates"]["chk004_proven_exceedances"][0]["combination"], "D")
        self.assertEqual(gates["formal_compliance"], "FAIL")
        self.assertEqual(gates["status"], "LOCAL_FAIL_PRESENT")

    def test_unassigned_role_never_claims_chk004_fail_or_pass(self):
        gates = project_column_gates(self.source, _axial("ETABS_STRENGTH", [], 1500.0))
        counts = gates["axial_gates"]
        self.assertEqual(counts["chk004_proven_exceedance_count"], 0)
        self.assertEqual(counts["chk004_exceeds_reference_but_role_unassigned_count"], 2)
        self.assertEqual(gates["formal_compliance"], "NOT_PROVEN")
        self.assertIn("SEISMIC_COMBINATION_ROLE_UNASSIGNED", {g["code"] for g in gates["open_gates"]})

    def test_chk005_exceedance_is_a_proven_fail_regardless_of_role(self):
        gates = project_column_gates(self.source, _axial("ETABS_STRENGTH", [], 2500.0))
        self.assertEqual(gates["axial_gates"]["chk005_exceedance_count"], 2)
        self.assertEqual(gates["formal_compliance"], "FAIL")

    def test_template_cage_is_missing_cage_not_a_pass_and_not_a_fail(self):
        gates = project_column_gates(self.source, _axial("ASSIGNED_DESIGN", ["D"], 10.0), _pmm("ETABS_DESIGN_TEMPLATE"))
        self.assertEqual(gates["reinforcement_gate"]["role"], "TEMPLATE")
        self.assertTrue(gates["reinforcement_gate"]["would_fail_if_selected"])
        codes = {g["code"] for g in gates["open_gates"]}
        self.assertLessEqual({"SELECTED_CAGE_MISSING", "ANALYSIS_ORDER_UNVERIFIED", "CONFINEMENT_DETAIL_NOT_PROVEN"}, codes)
        self.assertFalse(gates["canonical_design_pass_allowed"])
        self.assertEqual(gates["formal_compliance"], "NOT_PROVEN")

    def test_etabs_check_reinforcement_below_minimum_is_a_proven_fail(self):
        gates = project_column_gates(self.source, _axial("ASSIGNED_DESIGN", ["D"], 10.0), _pmm("ETABS_CHECK_REINFORCEMENT"))
        self.assertEqual(gates["reinforcement_gate"]["formal_compliance"], "FAIL")
        self.assertIn("CHK117_TBDY_7_3_2_1_LONGITUDINAL_LIMITS", {f["code"] for f in gates["local_findings"]})
        self.assertEqual(gates["formal_compliance"], "FAIL")

    def test_compliant_selected_cage_still_waits_for_approval(self):
        gates = project_column_gates(self.source, _axial("ASSIGNED_DESIGN", ["D"], 10.0),
                                     _pmm("ETABS_CHECK_REINFORCEMENT", bar_count=16, area=452.4, diameter=24.0))
        self.assertEqual(gates["formal_compliance"], "NOT_PROVEN")
        self.assertIn("SELECTED_CAGE_APPROVAL", {g["code"] for g in gates["open_gates"]})
        self.assertFalse(gates["canonical_design_pass_allowed"])


class LiveGatesAndCli(live.ColumnAxialIntegration):
    """Reuse the live-run fixture; the inherited tests are not collected twice."""

    def pmm_run(self) -> str:
        query = self.query("ASSIGNED_DESIGN")
        query.update(check="column-pmm", member="C1",
                     assignments=json.dumps({"gravity": [STATIC], "ductile": [SPECTRAL]}))
        return self.post(query)["run_id"]

    def test_acknowledgement_report_and_html_share_one_gate_projection(self):
        run_id = self.pmm_run()
        report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
        gates = report["column_gates"]
        self.assertEqual(gates["reinforcement_gate"]["role"], "TEMPLATE")
        self.assertFalse(gates["canonical_design_pass_allowed"])
        self.assertEqual(gates["axial_gates"]["seismic_applicability_basis"], "ASSIGNED_DESIGN_GROUP")
        html = self.get("/report/print?run_id=" + run_id)
        self.assertIn(b"Recorded ETABS reinforcement gates", html)
        self.assertIn(b"CHK-004 / CHK-005 / CHK-117", html)
        # The receipt payloads stay untouched, so historical runs keep replaying.
        self.assertNotIn("column_gates", report["column_pmm"])

    def test_new_report_reads_sealed_design_results_without_running_design_solvers(self):
        run_id = self.pmm_run()
        targets = [
            "tbdy_next.history.evaluate_modal_mass",
            "tbdy_next.reporting.evaluate_geometry_capture",
            "tbdy_next.engineering.pipeline.derive_report_evidence",
            "tbdy_next.engineering.column_axial.evaluate_column_axial",
            "tbdy_next.engineering.column_pmm.evaluate_column_pmm",
            "tbdy_next.engineering.beam_r10_live.project_beam_r10_live",
            "tbdy_next.engineering.column_r10_live.project_column_r10_live",
            "tbdy_next.engineering.column_live_gates.project_column_gates",
            "tbdy_next.engineering.column_r08_local_live.project_column_r08_local_live",
            "tbdy_next.engineering.column_r14_closure.project_column_r14_and_r15_closure",
        ]
        from contextlib import ExitStack
        with ExitStack() as stack:
            for target in targets:
                stack.enter_context(patch(target, side_effect=AssertionError("REPORT_MUST_NOT_RECALCULATE_DESIGN_STAGE")))
            report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
            markup = self.get("/report/print?run_id=" + run_id)
        self.assertEqual(report["design_stage_provenance"]["status"], "SEALED_PIPELINE_STAGE_RESULTS")
        self.assertTrue(report["design_stage_provenance"]["full_report_projection_only"])
        self.assertIn(report["design_stage_provenance"]["snapshot_results_sha256"].encode(), markup)

    def test_pipeline_endpoint_publishes_registry_and_dag_coverage(self):
        body = json.loads(self.get("/api/pipeline"))
        self.assertEqual(body["dag_coverage"]["unknown_node_ids"], [])
        self.assertIn("column-gates", {row["key"] for row in body["stages"]})

    def test_cli_replay_of_a_sealed_run_reproduces_every_stage_payload(self):
        run_id = self.pmm_run()
        run_dir = self.root / run_id
        with TemporaryDirectory() as out:
            args = SimpleNamespace(source=run_dir / "input.source", case="Modal",
                                   out=Path(out), compare_run=run_dir)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = _run_pipeline_replay(args)
            summary = json.loads(buffer.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(summary["compare"]["status"], "IDENTICAL")
        self.assertEqual(summary["compare"]["mismatched_stages"], [])
        self.assertEqual(summary["engineering_release"], "NOT_READY")


# Inherited fixture tests belong to test_column_axial_live; do not run them twice.
for _name in [n for n in dir(live.ColumnAxialIntegration) if n.startswith("test_")]:
    setattr(LiveGatesAndCli, _name, None)


if __name__ == "__main__":
    unittest.main()
