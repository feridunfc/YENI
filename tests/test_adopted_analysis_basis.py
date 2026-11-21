"""Explicit calculation assumptions are consumed without granting engineering approval."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.engineering.analysis_setup import (
    ADOPTED_ANALYSIS_PENDING, ADOPTED_ANALYSIS_SCHEMA, STATIC_CASES, SUMMARY,
    audit_model_analysis_setup, project_analysis_setup_reconciliation,
)
from tbdy_next.engineering.design_assignments import _PROFILE
from tbdy_next.engineering.design_scenario import (
    SCHEMA, _digest, _source_data, create_design_scenario, prepare_pipeline_source,
    validate_design_scenario, verify_parent,
)
from test_r03_analysis_setup import basis_probe


def source_and_basis():
    groups = {g["id"]: ["service-in-its-name"] for g in _PROFILE["groups"] if g.get("checks")}
    source = {"source_mode": "LIVE_ETABS", "vs04_basis_probe": basis_probe(),
              "column_axial": {"request": {"pmm_member": "ALL", "combination_source": "ASSIGNED_DESIGN",
                                           "design_assignment": {"groups": groups}}}}
    source["vs04_basis_probe"]["table_reads"][STATIC_CASES]["rows"][0]["StiffType"] = "Unstressed"
    basis = {
        "schema": ADOPTED_ANALYSIS_SCHEMA, "basis_id": "synthetic-analysis-calculation",
        "basis_role": "ADOPTED_CALCULATION_ASSUMPTIONS", "engineering_approval": "NOT_GRANTED",
        "source_data_sha256": _digest(_source_data(source)),
        "decision_reference": "Public synthetic calculation fixture; no original model approval",
        "model_profile": {"profile_id": "synthetic-frame", "structural_system": "FRAME",
                          "ductility_level": "HIGH", "decision_reference": "Synthetic fixture definition"},
        "case_roles": {"gravity": "GRAVITY", "spectrum-any-name": "RESPONSE_SPECTRUM"},
        "design_groups": groups,
        "generation": {"analysis_run_id": "SYNTHETIC-NOT-ETABS", "source_analysis_order": "FIRST_ORDER",
                       "completed_case_names": ["gravity", "spectrum-any-name"],
                       "decision_reference": "Explicit first-order assumption, not a solver-log proof"},
    }
    return source, basis


def prepare(source, basis):
    raw = json.dumps(source, sort_keys=True).encode()
    request = {"schema": SCHEMA, "scenario_id": "adopted-analysis", "parent_input_sha256": sha256(raw).hexdigest(),
               "beam_selection": "default", "column_selection": "default", "analysis_basis": basis}
    return raw, prepare_pipeline_source(raw, request=request)


class AdoptedAnalysisBasisTests(unittest.TestCase):
    def test_complete_explicit_assumptions_resolve_calculation_admission_not_engineering_acceptance(self):
        source, basis = source_and_basis()
        raw, prepared = prepare(source, basis)
        native = audit_model_analysis_setup(source["vs04_basis_probe"])
        result = project_analysis_setup_reconciliation(native, prepared.payload)
        self.assertEqual(result["reconciled_blocker_codes"], [ADOPTED_ANALYSIS_PENDING])
        self.assertFalse(result["analysis_generation_independently_verified"])
        self.assertFalse(native["analysis_generation_proven"])
        self.assertEqual(result["engineering_approval"], "NOT_GRANTED")
        self.assertEqual(result["calculation_basis_sha256"], _digest(result["calculation_basis"]))
        verify_parent(prepared.payload, raw)
        self.assertEqual(prepared.parent_raw, raw)

    def test_legacy_source_keeps_existing_unresolved_gates(self):
        source, _ = source_and_basis()
        result = project_analysis_setup_reconciliation(audit_model_analysis_setup(source["vs04_basis_probe"]), source)
        self.assertIn("APPROVED_MODEL_PROFILE_MISSING", result["reconciled_blocker_codes"])
        self.assertIn("ANALYSIS_GENERATION_NOT_PROVEN", result["reconciled_blocker_codes"])
        self.assertNotIn("calculation_basis_status", result)

    def test_wrong_source_or_authority_cannot_form_a_scenario(self):
        source, basis = source_and_basis()
        for key, value in (("source_data_sha256", "f" * 64), ("engineering_approval", "APPROVED"),
                           ("basis_role", "PROVEN")):
            changed = deepcopy(basis)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare(source, changed)

    def test_case_group_and_generation_scope_must_match_native_population(self):
        source, basis = source_and_basis()
        for kind in ("role", "missing_case", "generation", "groups"):
            changed = deepcopy(basis)
            if kind == "role": changed["case_roles"]["spectrum-any-name"] = "GRAVITY"
            if kind == "missing_case": changed["case_roles"].pop("gravity")
            if kind == "generation": changed["generation"]["completed_case_names"] = ["gravity"]
            if kind == "groups": changed["design_groups"].pop(next(iter(changed["design_groups"])))
            _, prepared = prepare(source, changed)
            result = project_analysis_setup_reconciliation(audit_model_analysis_setup(source["vs04_basis_probe"]), prepared.payload)
            with self.subTest(kind=kind):
                self.assertNotIn("calculation_basis_status", result)
                self.assertTrue(any(c.startswith("ADOPTED_ANALYSIS_BASIS_INVALID:") for c in result["reconciled_blocker_codes"]))

    def test_named_nonlinear_stiffness_predecessor_rejects_first_order_assumption(self):
        source, basis = source_and_basis()
        rows = source["vs04_basis_probe"]["table_reads"][STATIC_CASES]["rows"]
        for row in rows: row["NonlinCase"] = "PDELTA-STATE"
        basis["source_data_sha256"] = _digest(_source_data(source))
        _, prepared = prepare(source, basis)
        result = project_analysis_setup_reconciliation(audit_model_analysis_setup(source["vs04_basis_probe"]), prepared.payload)
        self.assertTrue(any("CONFLICTS_WITH_NATIVE_PREDECESSOR" in c for c in result["reconciled_blocker_codes"]))

    def test_explicit_pdelta_or_unknown_stiffness_cannot_be_adopted_as_first_order(self):
        for setting in ("P-Delta", "Unknown stiffness"):
            source, basis = source_and_basis()
            source["vs04_basis_probe"]["table_reads"][STATIC_CASES]["rows"][0]["StiffType"] = setting
            basis["source_data_sha256"] = _digest(_source_data(source))
            _, prepared = prepare(source, basis)
            result = project_analysis_setup_reconciliation(audit_model_analysis_setup(source["vs04_basis_probe"]), prepared.payload)
            with self.subTest(setting=setting):
                self.assertNotIn("calculation_basis_status", result)
                self.assertTrue(any("STIFFNESS_SETTING_CONFLICT_OR_UNSUPPORTED" in c for c in result["reconciled_blocker_codes"]))

    def test_native_ritz_and_eigen_names_bind_to_modal_role(self):
        for kind in ("Modal", "Modal - Ritz", "Modal - Eigen"):
            source, basis = source_and_basis()
            table = source["vs04_basis_probe"]["table_reads"][SUMMARY]
            table["rows"].append({"Name": "Modal", "Type": kind, "GUID": "modal-guid"})
            table["row_count"] = len(table["rows"])
            basis["case_roles"]["Modal"] = "MODAL"
            basis["generation"]["completed_case_names"].append("Modal")
            basis["source_data_sha256"] = _digest(_source_data(source))
            _, prepared = prepare(source, basis)
            result = project_analysis_setup_reconciliation(audit_model_analysis_setup(source["vs04_basis_probe"]), prepared.payload)
            with self.subTest(kind=kind):
                self.assertEqual(result["reconciled_blocker_codes"], [ADOPTED_ANALYSIS_PENDING])
                self.assertFalse(result["analysis_generation_independently_verified"])

    def test_empty_nonlinear_predecessor_remains_an_assumption_not_source_proof(self):
        source, basis = source_and_basis()
        source["vs04_basis_probe"]["table_reads"][STATIC_CASES]["rows"][0]["StiffType"] = "Nonlinear Case"
        basis["source_data_sha256"] = _digest(_source_data(source))
        _, prepared = prepare(source, basis)
        result = project_analysis_setup_reconciliation(audit_model_analysis_setup(source["vs04_basis_probe"]), prepared.payload)
        self.assertEqual(result["reconciled_blocker_codes"], [ADOPTED_ANALYSIS_PENDING])
        self.assertFalse(result["analysis_generation_independently_verified"])

    def test_native_failures_survive_valid_basis(self):
        source, basis = source_and_basis()
        _, prepared = prepare(source, basis)
        native = audit_model_analysis_setup(source["vs04_basis_probe"])
        native["blocker_codes"].append("NATIVE_FORCE_GENERATION_MISMATCH")
        result = project_analysis_setup_reconciliation(native, prepared.payload)
        self.assertIn("NATIVE_FORCE_GENERATION_MISMATCH", result["reconciled_blocker_codes"])
        self.assertIn(ADOPTED_ANALYSIS_PENDING, result["reconciled_blocker_codes"])

    def test_changed_basis_changes_scenario_identity_and_cannot_be_silently_mutated(self):
        source, basis = source_and_basis()
        _, original = prepare(source, basis)
        changed = deepcopy(basis)
        changed["generation"]["analysis_run_id"] += "-revised"
        _, revised = prepare(source, changed)
        self.assertNotEqual(original.payload["design_scenario"]["scenario_sha256"],
                            revised.payload["design_scenario"]["scenario_sha256"])
        self.assertEqual(original.payload["design_scenario"]["source_data_sha256"],
                         revised.payload["design_scenario"]["source_data_sha256"])
        tampered = deepcopy(original.payload)
        tampered["analysis_basis"]["generation"]["analysis_run_id"] += "-changed"
        with self.assertRaises(ValueError): validate_design_scenario(tampered)

    def test_rebar_policy_revision_inherits_adopted_basis_and_original_parent(self):
        source, basis = source_and_basis()
        raw, original = prepare(source, basis)
        with TemporaryDirectory() as directory:
            path = Path(directory)
            original.archive_parent(path)
            revised = prepare_pipeline_source(original.raw, source_directory=path,
                                               selection_overrides={"column_selection": {"min_rho": .02}})
        self.assertEqual(revised.payload["analysis_basis"], original.payload["analysis_basis"])
        self.assertEqual(revised.parent_raw, raw)

    def test_unbound_native_basis_cannot_bypass_scenario_preparation(self):
        source, basis = source_and_basis()
        source["analysis_basis"] = basis
        with self.assertRaisesRegex(ValueError, "REQUIRES_PREPARED_SCENARIO"):
            prepare_pipeline_source(json.dumps(source).encode())


if __name__ == "__main__":
    unittest.main()
