"""Actual R08 calculation plus explicit R03/R14 consumer contract fixtures.

This module does not claim a native whole-pipeline run. The separate vertical
slice test exercises acquisition-shaped sources through EnginePipelineRunner.
"""
from copy import deepcopy
from argparse import Namespace
from contextlib import redirect_stdout
import io
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from test_adopted_analysis_basis import source_and_basis
from test_adopted_second_order_basis import adopted_fixture
from test_audit_hardening import CLOSED, closure_fixture
from tbdy_next.engineering.analysis_setup import ADOPTED_ANALYSIS_PENDING, normalize_analysis_basis
from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
from tbdy_next.engineering.column_r14_closure import _adopted_calculation_context, _evaluate_single_r14_column
from tbdy_next.engineering.cli_adapter import run_cli
from tbdy_next.engineering.pipeline_snapshot import read_snapshot
from tbdy_next.engineering.design_scenario import _digest, _source_data
from tbdy_next.engineering.second_order_basis import AXIAL_IDEALIZATION_APPLIED, AXIAL_IDEALIZATION_GATE


def r14_adopted_consumer_fixture(*, computed_k=False):
    owner = adopted_fixture(k=.8 if computed_k else 1., rm=0., nd=1200.)
    if computed_k:
        ends = {side: {"basis": "FRAME_SECTION_REFERENCE", "joint_id": side,
                       "alpha_web": 1., "alpha_flange_comparison": .5} for side in ("I", "J")}
        for axis in ("M2", "M3"):
            owner["source"]["second_order_basis"]["members"]["127"]["axes"][axis]["k_source"] = {
                "method": "FRAME_END_RATIOS", "section": "alpha_web"}
        # The end-ratio source is an explicit contract fixture; K, Euler loads
        # and final PMM capacities are computed by the existing actual owners.
        with patch("tbdy_next.engineering.column_r08_local_live.reference_end_ratios",
                   return_value={"127": {a: ends for a in ("M2", "M3")}}):
            local = project_column_r08_local_live(**owner)
    else:
        local = project_column_r08_local_live(**owner)
    args = closure_fixture()
    args.update(uid="127", pmm_col=owner["pmm"], r08_local_col=local, r08_global=owner["global_pdelta"])
    args["axial"] = owner["axial"]
    args["axial_col"]["combination_checks"] = [{"combination": "G_STATIC", "nd_kn": 1200.}]
    args["axial_col"]["story"] = owner["pmm"]["story"]
    for row in args["story_alpha"]["stories"]:
        row["story"] = owner["pmm"]["story"]
    _, analysis = source_and_basis()
    analysis["source_data_sha256"] = _digest(_source_data(owner["source"]))
    analysis["design_groups"] = {"gravity": ["G_STATIC"]}
    analysis = normalize_analysis_basis(analysis, source_data_sha256=analysis["source_data_sha256"])
    args["analysis_setup_reconciliation"].update(
        calculation_basis_status="ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN",
        calculation_basis=analysis, calculation_basis_sha256=_digest(analysis),
        engineering_approval="NOT_GRANTED", analysis_generation_independently_verified=False,
        reconciled_blocker_codes=[ADOPTED_ANALYSIS_PENDING])
    candidate = owner["selected_cages"]["127"].candidate_sha256
    args["dependency_evidence"] = {"source_payload_sha256": _digest(owner["source"]),
        "columns": {"127": {"open_gates": [], "candidate_revision_sha256": candidate}},
        "artifacts": {"r08:127": {"payload_sha256": _digest(local)}}}
    args["r10_det"]["engineer_column_selection"]["selected"]["label"] = "32Phi16"
    return args


class R14AdoptedBasisTests(unittest.TestCase):
    def test_idealization_acceptance_label_cannot_bypass_computed_application(self):
        for pretend_application in (False, True):
            with self.subTest(pretend_application=pretend_application):
                args = r14_adopted_consumer_fixture()
                local = args["r08_local_col"]
                local["open_gates"].append(AXIAL_IDEALIZATION_GATE)
                if pretend_application:
                    local["axial_idealization_application"] = {
                        "status": AXIAL_IDEALIZATION_APPLIED, "qualified": True,
                    }
                args["dependency_evidence"]["artifacts"]["r08:127"]["payload_sha256"] = _digest(local)
                result = _evaluate_single_r14_column(**args)
                self.assertNotEqual(result["status"], CLOSED)
                self.assertIn("R08_LOCAL:" + AXIAL_IDEALIZATION_GATE, result["open_gates"])
                self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_actual_applied_r08_can_numerically_close_with_visible_acceptance_gates(self):
        args = r14_adopted_consumer_fixture()
        result = _evaluate_single_r14_column(**args)
        self.assertEqual(result["status"], CLOSED, result["open_gates"])
        self.assertIn("R08_LOCAL:ACTUAL_ANALYSIS_ORDER_UNVERIFIED", result["open_gates"])
        self.assertIn("R03:" + ADOPTED_ANALYSIS_PENDING, result["open_gates"])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["engineering_release"], "NOT_READY")
        pillar = result["pillars"]["second_order_selected_pmm"]
        self.assertFalse(pillar["adopted_calculation_context"]["analysis_generation_independently_verified"])
        self.assertEqual(pillar["adopted_calculation_context"]["engineering_approval"], "NOT_GRANTED")

    def test_stale_source_cage_method_or_axis_values_cannot_convert_gates_to_acceptance(self):
        good = r14_adopted_consumer_fixture()
        for defect in ("payload", "native", "candidate", "artifact", "member", "axis", "row", "analysis_hash", "analysis_order"):
            with self.subTest(defect=defect):
                args = deepcopy(good)
                local, evidence = args["r08_local_col"], args["dependency_evidence"]
                reconciliation = args["analysis_setup_reconciliation"]
                if defect == "payload": evidence["source_payload_sha256"] = "another-source"
                elif defect == "native": reconciliation["calculation_basis"]["source_data_sha256"] = "f" * 64
                elif defect == "candidate": evidence["columns"]["127"]["candidate_revision_sha256"] = "another-cage"
                elif defect == "artifact": evidence["artifacts"]["r08:127"]["payload_sha256"] = "stale"
                elif defect == "member": local["adopted_second_order_basis"]["member"]["combinations"] = ["G_STATIC", "E_MISSING"]
                elif defect == "axis": local["stiffness_and_euler"]["M2"]["effective_length_factor_k"] = 2.
                elif defect == "row": local["magnified_selected_pmm"]["rows"][0]["second_order_basis_sha256"] = "another-method"
                elif defect == "analysis_hash": reconciliation["calculation_basis_sha256"] = "stale"
                else: reconciliation["calculation_basis"]["generation"]["source_analysis_order"] = "SECOND_ORDER"
                if defect in ("member", "axis", "row"):
                    evidence["artifacts"]["r08:127"]["payload_sha256"] = _digest(local)
                result = _evaluate_single_r14_column(**args)
                self.assertNotEqual(result["status"], CLOSED)
                self.assertIn("ADOPTED_CALCULATION_BASIS_BINDING_UNVERIFIED", result["open_gates"])

    def test_computed_k_uses_machine_budget_without_accepting_an_engineering_difference(self):
        good = r14_adopted_consumer_fixture(computed_k=True)
        self.assertEqual(_evaluate_single_r14_column(**good)["status"], CLOSED)
        for steps, expected in ((8, CLOSED), (9, "R14_PARTIAL_OR_UNBOUND")):
            with self.subTest(steps=steps):
                args = deepcopy(good)
                local = args["r08_local_col"]
                used = .8
                for _ in range(steps):
                    used = math.nextafter(used, math.inf)
                local["stiffness_and_euler"]["M2"]["effective_length_factor_k"] = used
                local["stiffness_and_euler"]["M2"]["k_source_resolution"]["computed_k"] = used
                args["dependency_evidence"]["artifacts"]["r08:127"]["payload_sha256"] = _digest(local)
                self.assertEqual(_evaluate_single_r14_column(**args)["status"], expected)
        manual = r14_adopted_consumer_fixture()
        manual["r08_local_col"]["stiffness_and_euler"]["M2"]["effective_length_factor_k"] = math.nextafter(1., math.inf)
        manual["dependency_evidence"]["artifacts"]["r08:127"]["payload_sha256"] = _digest(manual["r08_local_col"])
        self.assertNotEqual(_evaluate_single_r14_column(**manual)["status"], CLOSED)

    def test_missing_calculation_coupled_member_or_unrelated_native_failure_remains_open(self):
        good = r14_adopted_consumer_fixture()
        for defect in ("missing_calculation", "coupled", "native_failure"):
            with self.subTest(defect=defect):
                args = deepcopy(good)
                local = args["r08_local_col"]
                if defect == "missing_calculation": local.pop("magnified_selected_pmm")
                elif defect == "coupled":
                    local.update(execution_status="NOT_RUN", second_order_basis_status="WALL_COUPLED_ADOPTED_BASIS_WITHHELD")
                    local["open_gates"].append("WALL_FRAME_EFFECTIVE_LENGTH_REQUIRES_COUPLED_MODEL")
                else: args["analysis_setup_reconciliation"]["reconciled_blocker_codes"].append("NATIVE_FORCE_GENERATION_MISMATCH")
                args["dependency_evidence"]["artifacts"]["r08:127"]["payload_sha256"] = _digest(local)
                result = _evaluate_single_r14_column(**args)
                self.assertNotEqual(result["status"], CLOSED)
                self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_gate_removal_or_status_label_alone_cannot_simulate_an_adopted_calculation(self):
        args = closure_fixture()
        args["r08_local_col"].update(adopted_second_order_basis={},
            second_order_basis_status="ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN", open_gates=[])
        result = _evaluate_single_r14_column(**args)
        self.assertNotEqual(result["status"], CLOSED)
        self.assertIn("ADOPTED_CALCULATION_BASIS_BINDING_UNVERIFIED", result["open_gates"])

    def test_source_qualified_no_alpha_does_not_require_a_number_in_inapplicable_legacy_rows(self):
        args = r14_adopted_consumer_fixture()
        args["dependency_evidence"]["columns"]["127"]["alpha_feedback_not_required"] = True
        for row in args["story_alpha"]["stories"]:
            row.update(governing_alpha_i=None, demand_feedback_action="UNRESOLVED")
        result = _evaluate_single_r14_column(**args)
        self.assertEqual(result["status"], CLOSED, result["open_gates"])
        args["dependency_evidence"]["columns"]["127"]["alpha_feedback_not_required"] = False
        unbound = _evaluate_single_r14_column(**args)
        self.assertNotEqual(unbound["status"], CLOSED)
        self.assertIn("STORY_ALPHA_VALUE_MISSING_OR_INVALID", unbound["open_gates"])


class R14AxialIdealizationConsumptionTests(unittest.TestCase):
    """Negative consumer tests begin with an actual normal-pipeline calculation."""

    @classmethod
    def setUpClass(cls):
        from variable_axial_slice_fixture import source_and_request

        raw, request = source_and_request()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, request_path = root / "native.source", root / "scenario.json"
            source_path.write_bytes(raw)
            request_path.write_text(json.dumps(request), encoding="utf-8")
            stream = io.StringIO()
            with redirect_stdout(stream):
                status = run_cli(Namespace(action="run-pipeline", source=source_path, design_scenario=request_path,
                    out=root, case="Modal", compare_run=None, beam_selection=None, column_selection=None))
            if status != 0:
                raise AssertionError(stream.getvalue())
            summary = json.loads(stream.getvalue())
            cls.results = read_snapshot(Path(summary["run_dir"]), input_sha=summary["input_sha256"])["results"]

    def context(self, local, evidence):
        return _adopted_calculation_context("C1", self.results["column_axial"]["combination_plan"], local,
            self.results["analysis_setup_reconciliation"], evidence)

    def test_actual_bound_idealization_is_consumed_but_corrupted_inputs_and_arithmetic_are_not(self):
        original = self.results["r08_local_slenderness"]["per_member"]["C1"]
        recorded_evidence = self.results["report_evidence"]["design_revisions"]
        context = self.context(original, recorded_evidence)
        self.assertEqual(context["axial_idealization"]["status"], AXIAL_IDEALIZATION_APPLIED)
        self.assertFalse(context["axial_idealization"]["conservative_bound_proven"])
        self.assertFalse(context["axial_idealization"]["original_constant_axial_clause_satisfied"])
        self.assertEqual(context["axial_idealization"]["engineering_approval"], "NOT_GRANTED")
        for defect in ("nmax", "cut_missing", "local_nd", "factor_nd", "moment_product", "scope", "conservative_claim"):
            with self.subTest(defect=defect):
                local, evidence = deepcopy(original), deepcopy(recorded_evidence)
                premises = local["axial_idealization_evidence"]
                application = local["axial_idealization_application"]
                case = sorted(premises["combinations"])[0]
                row = next(r for r in local["magnified_selected_pmm"]["rows"] if r["combination"] == case)
                if defect == "nmax":
                    premises["combinations"][case]["nmax_kn"] -= 1
                elif defect == "cut_missing":
                    premises["combinations"][case]["cuts"].pop()
                elif defect == "local_nd":
                    row["nd_kn"] = premises["combinations"][case]["nmin_kn"]
                elif defect == "factor_nd":
                    row["adopted_axis_factors"]["M2"]["coefficient_nd_kn"] -= 1
                elif defect == "moment_product":
                    row["magnified_m2_design_knm"] *= .5
                elif defect == "scope":
                    application["combinations"].pop(case)
                else:
                    application["conservative_bound_proven"] = True
                # Rehash the altered records: numerical/source consistency must
                # fail independently of a stale outer digest or approval label.
                premises["evidence_sha256"] = _digest({k: v for k, v in premises.items() if k != "evidence_sha256"})
                application["eligibility_sha256"] = premises["evidence_sha256"]
                for item in local["magnified_selected_pmm"]["rows"]:
                    if "axial_idealization_evidence_sha256" in item:
                        item["axial_idealization_evidence_sha256"] = premises["evidence_sha256"]
                application["application_sha256"] = _digest({k: v for k, v in application.items() if k != "application_sha256"})
                evidence["artifacts"]["r08:C1"]["payload_sha256"] = _digest(local)
                self.assertIsNone(self.context(local, evidence))


if __name__ == "__main__":
    unittest.main()
