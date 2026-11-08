"""D4 negative oracle and source/combination graph audit, with no ETABS.

Run: PYTHONPATH=src python -m unittest discover -s tests -p 'test_vs05_d4*.py' -v
"""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from tbdy_next.vs05_d4_source_authority import (
    SourceContractError, audit_d4_source_authority, _canonical, _digest,
)


def table(key, rows):
    fields = list(rows[0])
    return {
        "status": "CAPTURED", "table_key": key,
        "row_count": len(rows), "fields": fields, "rows": rows,
        "field_metadata": {
            "status": "OK", "field_keys": fields,
            "units_by_field": {k: "" for k in fields},
        },
    }


def payload():
    cases = [
        {"Name": "Modal", "Type": "Modal - Ritz", "GUID": "guid-modal"},
        {"Name": "RSX", "Type": "Response Spectrum", "GUID": "guid-rsx"},
        {"Name": "RSY", "Type": "Response Spectrum", "GUID": "guid-rsy"},
        {"Name": "DL", "Type": "Linear Static", "GUID": "guid-dl"},
    ]
    spectra = [
        {"Name": "RSX", "LoadName": "U1", "ModalCase": "Modal",
         "Function": "RESP_YATAY"},
        {"Name": "RSY", "LoadName": "U2", "ModalCase": "Modal",
         "Function": "RESP_YATAY"},
    ]
    combos = [
        {"Name": "SUM_X", "Type": "Linear Add", "LoadName": "DL",
         "SF": "1.0", "GUID": "combo-sum-x"},
        {"Name": "SUM_X", "Type": "None", "LoadName": "RSX",
         "SF": "2.5", "GUID": "None"},
        {"Name": "ENV", "Type": "Envelope", "LoadName": "SUM_X",
         "SF": "1", "GUID": "combo-env"},
        {"Name": "SRSS_COMBO", "Type": "SRSS", "LoadName": "RSY",
         "SF": "1", "GUID": "combo-srss"},
    ]
    source = {
        "source_mode": "LIVE_ETABS",
        "vs04_basis_probe": {
            "schema": "tbdy.next.vs04e.basis-source-probe.v1",
            "read_only_invariant_proven": True,
            "units_before": 6, "units_after": 6,
            "table_reads": {
                "Load Case Definitions - Summary": table("c", cases),
                "Load Case Definitions - Response Spectrum": table("s", spectra),
                "Load Combination Definitions": table("b", combos),
            },
        },
        "analysis_sources": {"analysis_generation_proven": False},
    }
    return {
        "schema": "tbdy.next.complete.engineering.report.v1",
        "run_id": "RUN-" + "a" * 32,
        "source_mode": "LIVE_ETABS",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "capture_metadata": {
            "vs04_same_session_capture": True,
            "display_selection_restored": True,
            "analysis_generation_proven": False,
        },
        "source_snapshot": source,
        "vs04_pipeline": {
            "stages": {
                "vs04_f": {
                    "components": [{
                        "component": "SEISMIC_MASS_RECONCILIATION",
                        "status": "SOURCE_CONTRACT_OBSERVED_UNAPPROVED",
                        "source_facts": {
                            "mass_source": "MsSrc1",
                            "comparisons": {
                                "joint_to_group_UX": True,
                                "joint_to_group_UY": True,
                                "story_to_group_UX": True,
                                "story_to_group_UY": True,
                            },
                            "group_sums": {"UX_ton": "4380.4916",
                                           "UY_ton": "4380.4916"},
                        },
                    }],
                },
            },
        },
    }


def d3_for(src):
    return {
        "run_id": src["run_id"],
        "source_snapshot_sha256_canonical": _digest(src["source_snapshot"]),
        "model_analysis_generation_proven": False,
        "formal_compliance": "NOT_PROVEN",
        "fcr": {"expected_count": 10, "reconciled_count": 10,
                "not_proven_count": 10, "pass_count": 0},
    }


class D4SourceEvidenceContractTest(unittest.TestCase):
    def test_source_roles_and_nested_operator_shapes_stay_unapproved(self):
        r = payload()
        x = audit_d4_source_authority(r, d3_for(r))
        self.assertEqual(x["source_case_catalog"]["case_count"], 4)
        self.assertTrue(x["source_case_catalog"]["x_y_case_shape_consistent"])
        self.assertEqual(x["source_combination_graph"]["raw_row_count"], 4)
        self.assertEqual(x["source_combination_graph"]["parsed_combination_count"], 3)
        self.assertEqual(x["source_combination_graph"]["operator_counts"],
                         {"Envelope": 1, "Linear Add": 1, "SRSS": 1})
        self.assertEqual(x["source_combination_graph"]["unknown_reference_count"], 0)
        self.assertFalse(x["source_combination_graph"]["design_demand_vector_authorized"])
        self.assertEqual(x["source_mass_reconciliation"]["candidate_mass_ton"],
                         "4380.4916")
        self.assertFalse(x["source_mass_reconciliation"]["seismic_mass_scope_approved"])
        self.assertFalse(x["source_capture"]["analysis_generation_proven"])
        self.assertEqual(x["d3_fcr"]["not_proven"], 10)
        self.assertEqual(x["normative_check_instances_promoted"], 0)
        self.assertEqual(x["formal_compliance"], "NOT_PROVEN")

    def test_mutating_d3_hash_or_denominator_causes_rejection(self):
        src = payload()
        d3 = d3_for(src)
        d3["source_snapshot_sha256_canonical"] = "b" * 64
        with self.assertRaisesRegex(SourceContractError, "HASH_MISMATCH"):
            audit_d4_source_authority(src, d3)
        d3 = d3_for(src)
        d3["fcr"]["reconciled_count"] = 9
        with self.assertRaisesRegex(SourceContractError, "FCR_DENOMINATOR"):
            audit_d4_source_authority(src, d3)

    def test_extra_unknown_combo_source_does_not_become_a_design_vector(self):
        src = payload()
        t = src["source_snapshot"]["vs04_basis_probe"]["table_reads"][
            "Load Combination Definitions"]
        t["rows"][1]["LoadName"] = "NOT_A_CASE"
        result = audit_d4_source_authority(src)
        self.assertEqual(result["source_combination_graph"]["unknown_reference_count"], 1)
        self.assertFalse(result["source_combination_graph"][
            "candidate_operator_reference_shape_observed"])
        self.assertEqual(result["normative_check_instances_promoted"], 0)

    def test_srss_and_envelope_are_risky_even_inside_nested_sum(self):
        result = audit_d4_source_authority(payload())
        names = [x["combo"] for x in result["source_combination_graph"][
            "nonconcurrent_vector_risks"]]
        self.assertEqual(names, ["ENV", "SRSS_COMBO", "SUM_X"])

    def test_cycle_cannot_authorize_combinations(self):
        src = payload()
        rows = src["source_snapshot"]["vs04_basis_probe"]["table_reads"][
            "Load Combination Definitions"]["rows"]
        rows[0]["LoadName"] = "ENV"  # ENV already refers to SUM_X
        result = audit_d4_source_authority(src)
        self.assertTrue(result["source_combination_graph"]["cycle_candidates"])
        self.assertFalse(result["source_combination_graph"][
            "candidate_operator_reference_shape_observed"])

    def test_case_direction_mismatch_is_rejected_as_source_inconsistent(self):
        src = payload()
        selected = src["source_snapshot"]["vs04_basis_probe"]["table_reads"][
            "Load Case Definitions - Response Spectrum"]
        selected["rows"][1]["LoadName"] = "U1"
        out = audit_d4_source_authority(src)
        self.assertFalse(out["source_case_catalog"]["x_y_case_shape_consistent"])
        self.assertFalse(out["gamma_e_authorized"])

    def test_corrupt_rows_or_units_metadata_cannot_be_skipped(self):
        for problem in ("row_count", "duplicate_field", "metadata"):
            src = payload()
            table = src["source_snapshot"]["vs04_basis_probe"]["table_reads"][
                "Load Case Definitions - Summary"]
            if problem == "row_count":
                table["row_count"] = 500
            elif problem == "duplicate_field":
                table["fields"].append("Name")
            else:
                table["field_metadata"]["status"] = "ERROR"
            with self.subTest(problem=problem), self.assertRaises(SourceContractError):
                audit_d4_source_authority(src)

    def test_candidate_mass_comparison_missing_never_grants_mass_mt(self):
        src = payload()
        facts = src["vs04_pipeline"]["stages"]["vs04_f"]["components"][0]["source_facts"]
        facts["comparisons"]["joint_to_group_UY"] = False
        result = audit_d4_source_authority(src)
        self.assertFalse(result["source_mass_reconciliation"][
            "mass_reconciliation_source_observed"])
        self.assertIsNone(result["source_mass_reconciliation"]["candidate_mass_ton"])
        self.assertFalse(result["source_mass_reconciliation"]["seismic_mass_scope_approved"])

    def test_zero_nonfinite_or_invalid_factor_is_blocked(self):
        for bad in ("NaN", "Infinity", "not-number"):
            src = payload()
            src["source_snapshot"]["vs04_basis_probe"]["table_reads"][
                "Load Combination Definitions"]["rows"][0]["SF"] = bad
            with self.subTest(factor=bad), self.assertRaises(SourceContractError):
                audit_d4_source_authority(src)

    def test_stray_report_claims_cannot_promote_regulatory_pass(self):
        src = payload()
        src["approved_combo_book"] = True
        src["source_snapshot"]["approved_model_profile"] = True
        result = audit_d4_source_authority(src)
        self.assertFalse(result["approved_combo_book"])
        self.assertFalse(result["approved_model_profile"])
        self.assertFalse(result["a1_b2_b3_full_inventory_proven"])
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_nested_sum_inheriting_envelope_is_nonconcurrent(self):
        src = payload()
        combo = src["source_snapshot"]["vs04_basis_probe"]["table_reads"][
            "Load Combination Definitions"]
        combo["rows"].append({"Name": "OUTER_SUM", "Type": "Linear Add",
                              "LoadName": "ENV", "SF": "1", "GUID": "combo-outer"})
        combo["row_count"] += 1
        result = audit_d4_source_authority(src)
        risk = {x["combo"]: x for x in result["source_combination_graph"][
            "nonconcurrent_vector_risks"]}
        self.assertIn("OUTER_SUM", risk)
        self.assertIn("NON_SUM_OPERATOR_OR_UNKNOWN_OPERATOR",
                      risk["OUTER_SUM"]["reason_codes"])

    def test_same_session_disconnected_or_unrestored_is_partial(self):
        for field in ("vs04_same_session_capture", "display_selection_restored"):
            src = payload()
            src["capture_metadata"][field] = False
            result = audit_d4_source_authority(src)
            self.assertEqual(result["status"],
                             "SOURCE_GATES_PARTIAL_NOT_REGULATORY_APPROVED")
            self.assertTrue(result["source_blocker_codes"])
            self.assertFalse(result["source_capture"]["analysis_generation_proven"])

    def test_untrusted_claimed_analysis_epoch_must_not_promote(self):
        for level in ("analysis_sources", "capture_metadata"):
            src = payload()
            if level == "analysis_sources":
                src["source_snapshot"]["analysis_sources"]["analysis_generation_proven"] = True
            else:
                src["capture_metadata"]["analysis_generation_proven"] = True
            with self.subTest(level=level), self.assertRaises(SourceContractError):
                audit_d4_source_authority(src)

    def test_mass_observed_still_needs_basement_mt_scope(self):
        result = audit_d4_source_authority(payload())
        mass = result["source_mass_reconciliation"]
        self.assertTrue(mass["mass_reconciliation_source_observed"])
        self.assertIn("MASS_MT_UPPER_BUILDING_BASEMENT_SCOPE_UNAPPROVED",
                      mass["reason_codes"])
        self.assertIn("upper_building_mass_scope",
                      result["normative_base_shear_missing_evidence"])
        self.assertEqual(result["normative_check_instances_promoted"], 0)

    def test_report_must_be_exact_live_schema(self):
        src = payload()
        src["source_mode"] = "OFFLINE_ARCHIVE"
        with self.assertRaisesRegex(SourceContractError, "REPORT_SCOPE"):
            audit_d4_source_authority(src)

    def test_read_only_unit_gate(self):
        src = payload()
        src["source_snapshot"]["vs04_basis_probe"]["units_after"] = 9
        with self.assertRaisesRegex(SourceContractError, "READ_ONLY_BASIS"):
            audit_d4_source_authority(src)


if __name__ == "__main__":
    unittest.main()
