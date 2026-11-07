"""VS05 bounded normative formula tests. All evidence sources are synthetic.

Even all proof flags=True are *self-assertions* in this fixture and MUST
NEVER create full regulatory compliance or production release.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest

from tbdy_next.normative_checks import (
    BASE_PROOFS, DRIFT_PROOFS,
    directional_base_shear_check, directional_effective_drift_check,
)


def approved_shape(proofs):
    return {
        **{k: True for k in proofs},
        "source_refs": {
            "model_generation":"synthetic-model-generation-1",
            "analysis_case":"RSX",
            "source_receipt":"synthetic-source-hash",
            "independent_oracle":"synthetic-hand-oracle",
        },
    }


def base_facts():
    return {
        "direction":"X","case":"RSX",
        "model_generation_id":"synthetic-model-generation-1",
        "qualified_tp_s":"0.5",
        "seismic_mass_kg":"100000",
        "sar_dd2_at_tp_m_s2":"2.0",
        "importance_I":"1.5",
        "sds_dd2":"1.0",
        "vtx_pre_beta_kn":"400",
        "a1_b2_b3":{"A1":"PRESENT","B2":"ABSENT","B3":"ABSENT"},
        "applied_beta":"1.324",
    }


def drift_facts():
    return {
        "direction":"X","case":"RSX","story":"+4.50",
        "model_generation_id":"synthetic-model-generation-1",
        "qualified_tp_s":"0.5",
        "story_height_m":"4.5","R":"7","importance_I":"1.5",
        "sae_dd3_at_same_tp_m_s2":"0.5",
        "sae_dd2_at_same_tp_m_s2":"1.0",
        "material":"RC","wall_connection":"ADHERED_BRITTLE",
        "flexible_wall_capacity_documented":False,
        "members":[
            {"member_id":"C1","u_upper_m":"0.020","u_lower_m":"0.005"},
            {"member_id":"C2","u_upper_m":"0.008","u_lower_m":"0.006"},
        ],
    }


class Vs05SourceGatedNormativeTests(unittest.TestCase):
    def test_complete_base_shear_arithmetic_including_minimum_and_beta(self):
        r=directional_base_shear_check(base_facts(),approved_shape(BASE_PROOFS))
        self.assertEqual(r["status"],"MEETS_NUMERICAL_CRITERION")
        self.assertEqual(r["execution"],"EXECUTED_NUMERIC_FORMULA")
        self.assertEqual(Decimal(r["calculation"]["minimum_base_shear_kn"]),Decimal("588.399"))
        self.assertEqual(Decimal(r["calculation"]["spectral_base_shear_kn"]),Decimal("200"))
        self.assertEqual(Decimal(r["calculation"]["equivalent_base_shear_kn"]),Decimal("588.399"))
        self.assertEqual(Decimal(r["calculation"]["gamma_E"]),Decimal("0.90"))
        self.assertEqual(Decimal(r["calculation"]["required_scale_factor"]),
                         Decimal("1.32389775"))
        self.assertEqual(Decimal(r["calculation"]["applied_beta"]),Decimal("1.324"))
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(r["engineering_release"],"NOT_READY")

    def test_underapplied_beta_is_real_negative_numeric_condition(self):
        data=base_facts()
        data["applied_beta"]="1.3"
        r=directional_base_shear_check(data,approved_shape(BASE_PROOFS))
        self.assertEqual(r["status"],"DOES_NOT_MEET_NUMERICAL_CRITERION")
        self.assertEqual(r["numerical_condition"],"APPLIED_SCALE_BELOW_REQUIRED")
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")

    def test_gamma_08_only_when_all_irregularities_explicitly_absent(self):
        data=base_facts()
        data["a1_b2_b3"]={k:"ABSENT" for k in ("A1","B2","B3")}
        r=directional_base_shear_check(data,approved_shape(BASE_PROOFS))
        self.assertEqual(Decimal(r["calculation"]["gamma_E"]),Decimal("0.80"))

    def test_unknown_irregularity_must_block_beta(self):
        data=base_facts()
        data["a1_b2_b3"]["B2"]="UNKNOWN"
        r=directional_base_shear_check(data,approved_shape(BASE_PROOFS))
        self.assertEqual(r["status"],"NOT_PROVEN")
        self.assertIsNone(r["calculation"])
        self.assertIn("FULL_A1_B2_B3_CLASSIFICATION_REQUIRED",r["missing_evidence"])

    def test_missing_model_analysis_generation_blocks_numeric_promotion(self):
        evidence=approved_shape(BASE_PROOFS)
        evidence["same_model_analysis_generation"]=False
        r=directional_base_shear_check(base_facts(),evidence)
        self.assertEqual(r["status"],"NOT_PROVEN")
        self.assertIn("same_model_analysis_generation",r["missing_evidence"])
        self.assertEqual(r["execution"],"BLOCKED_BY_EVIDENCE")

    def test_response_spectrum_base_shear_must_be_truly_pre_beta(self):
        e=approved_shape(BASE_PROOFS)
        e["pre_beta_modal_base_shear_not_scaled"]=False
        r=directional_base_shear_check(base_facts(),e)
        self.assertEqual(r["status"],"NOT_PROVEN")

    def test_same_model_and_case_reference_cannot_be_spoofed(self):
        e=approved_shape(BASE_PROOFS)
        e["source_refs"]["analysis_case"]="RSY"
        self.assertEqual(directional_base_shear_check(
            base_facts(),e)["status"],"NOT_PROVEN")
        e=approved_shape(DRIFT_PROOFS)
        e["source_refs"]["model_generation"]="some-other-generation"
        r=directional_effective_drift_check(drift_facts(),e)
        self.assertIn("MODEL_ANALYSIS_GENERATION_REFERENCE_MISMATCH",
                      r["missing_evidence"])
        self.assertIsNone(r["calculation"])

    def test_source_ids_cannot_be_blank(self):
        e=approved_shape(BASE_PROOFS)
        e["source_refs"]["analysis_case"]=""
        r=directional_base_shear_check(base_facts(),e)
        self.assertIn("exact_source_refs_and_independent_oracle",r["missing_evidence"])

    def test_mismatched_case_and_nonfinite_mass_denied(self):
        x=base_facts()
        x["case"]="RSY"
        self.assertEqual(directional_base_shear_check(x,approved_shape(BASE_PROOFS))["status"],
                         "NOT_PROVEN")
        x=base_facts()
        x["seismic_mass_kg"]="NaN"
        self.assertEqual(directional_base_shear_check(x,approved_shape(BASE_PROOFS))["status"],
                         "NOT_PROVEN")

    def test_true_physical_member_end_drift_formula_and_limit(self):
        r=directional_effective_drift_check(drift_facts(),approved_shape(DRIFT_PROOFS))
        self.assertEqual(r["status"],"MEETS_NUMERICAL_CRITERION")
        self.assertEqual(r["execution"],"EXECUTED_NUMERIC_FORMULA")
        self.assertEqual(r["calculation"]["critical_member_id"],"C1")
        self.assertEqual(Decimal(r["calculation"]["maximum_reduced_relative_displacement_m"]),
                         Decimal("0.015"))
        self.assertEqual(Decimal(r["calculation"]["effective_relative_displacement_m"]),
                         Decimal("0.07"))
        self.assertEqual(Decimal(r["calculation"]["limit"]),Decimal("0.008"))
        ratio=Decimal(r["calculation"]["lambda_effective_drift_over_height"])
        self.assertLess(abs(ratio - Decimal(7)/Decimal(900)),Decimal("1e-24"))
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")

    def test_unacceptable_brittle_wall_drift_detected(self):
        x=drift_facts()
        x["members"][0]["u_upper_m"]="0.025"
        r=directional_effective_drift_check(x,approved_shape(DRIFT_PROOFS))
        self.assertEqual(r["status"],"DOES_NOT_MEET_NUMERICAL_CRITERION")
        self.assertGreater(Decimal(r["calculation"]["lambda_effective_drift_over_height"]),
                           Decimal("0.008"))

    def test_flexible_wall_requires_tested_capacity_evidence(self):
        x=drift_facts()
        x["members"][0]["u_upper_m"]="0.025"
        x["wall_connection"]="DOCUMENTED_FLEXIBLE"
        x["flexible_wall_capacity_documented"]=False
        fail=directional_effective_drift_check(x,approved_shape(DRIFT_PROOFS))
        self.assertEqual(fail["status"],"NOT_PROVEN")
        x["flexible_wall_capacity_documented"]=True
        pass_result=directional_effective_drift_check(x,approved_shape(DRIFT_PROOFS))
        self.assertEqual(pass_result["status"],"MEETS_NUMERICAL_CRITERION")
        self.assertEqual(Decimal(pass_result["calculation"]["limit"]),Decimal("0.016"))

    def test_signed_member_displacements_have_valid_absolute_delta(self):
        x=drift_facts()
        x["members"][0]["u_upper_m"]="-0.020"
        x["members"][0]["u_lower_m"]="-0.005"
        r=directional_effective_drift_check(x,approved_shape(DRIFT_PROOFS))
        self.assertEqual(r["status"],"MEETS_NUMERICAL_CRITERION")
        self.assertEqual(Decimal(r["calculation"]["maximum_reduced_relative_displacement_m"]),
                         Decimal("0.015"))

    def test_zero_member_drift_is_valid(self):
        x=drift_facts()
        for m in x["members"]:
            m["u_upper_m"]="0.005"
            m["u_lower_m"]="0.005"
        r=directional_effective_drift_check(x,approved_shape(DRIFT_PROOFS))
        self.assertEqual(r["status"],"MEETS_NUMERICAL_CRITERION")
        self.assertEqual(Decimal(r["calculation"]["lambda_effective_drift_over_height"]),Decimal(0))

    def test_duplicate_physical_member_grain_fail_closed(self):
        x=drift_facts()
        x["members"][1]["member_id"]="C1"
        self.assertEqual(
            directional_effective_drift_check(x,approved_shape(DRIFT_PROOFS))["status"],
            "NOT_PROVEN")

    def test_no_physical_node_or_same_tp_source_proof_no_calculation(self):
        x=drift_facts()
        e=approved_shape(DRIFT_PROOFS)
        e["physical_story_and_end_node_identity"]=False
        e["matched_dd2_dd3_at_same_directional_tp"]=False
        r=directional_effective_drift_check(x,e)
        self.assertEqual(r["status"],"NOT_PROVEN")
        self.assertEqual(r["execution"],"BLOCKED_BY_EVIDENCE")
        self.assertIn("physical_story_and_end_node_identity",r["missing_evidence"])
        self.assertIn("matched_dd2_dd3_at_same_directional_tp",r["missing_evidence"])

    def test_no_real_building_pass_from_synthetic_proofs(self):
        for result in (
            directional_base_shear_check(base_facts(),approved_shape(BASE_PROOFS)),
            directional_effective_drift_check(drift_facts(),approved_shape(DRIFT_PROOFS)),
        ):
            self.assertEqual(result["formal_compliance"],"NOT_PROVEN")
            self.assertEqual(result["engineering_release"],"NOT_READY")
            self.assertEqual(result["source_only"],True)


if __name__=="__main__":
    unittest.main()
