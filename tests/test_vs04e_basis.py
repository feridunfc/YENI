"""VS04-E: verify source-only readiness and TBDY chapter 4 formula isolation."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest

from tbdy_next.normative_basis import (
    GATES, UnqualifiedEngineeringInput,
    eq_4_19_equivalent_base_shear_kn,
    eq_4_31_base_scale,
    eq_4_34_effective_drift,
    eq_4_9_lambda,
    review_normative_readiness,
)
from tbdy_next.basis_probe import capture_basis_probe, review_basis_probe, parse_available_tables
from tbdy_next.etabs_modal import ModalCaptureError
from tbdy_next.quick_checks import check_registry
from test_vs04_numerics import numeric_source


class NormativeFormulaKernels(unittest.TestCase):
    def test_4_19_mass_times_sar_and_minimum(self):
        result=eq_4_19_equivalent_base_shear_kn(
            seismic_mass_kg="1000000",
            reduced_spectral_acceleration_m_s2="2",
            importance_factor="1.5",sds_dd2="0.8")
        self.assertEqual(result["spectral_base_shear_kn"],"2000")
        self.assertEqual(Decimal(result["minimum_base_shear_kn"]),Decimal("470.7192"))
        self.assertEqual(Decimal(result["equivalent_base_shear_kn"]),Decimal(2000))
        self.assertEqual(result["source_status"],"FORMULA_ONLY_UNQUALIFIED")

    def test_4_19_floor_can_govern(self):
        x=eq_4_19_equivalent_base_shear_kn(
            seismic_mass_kg="1000000",reduced_spectral_acceleration_m_s2="0.1",
            importance_factor="1.5",sds_dd2="0.8")
        self.assertEqual(Decimal(x["equivalent_base_shear_kn"]),Decimal("470.7192"))

    def test_4_31_gamma_and_ratio(self):
        for irregularity, expected in ((True,"1.80"),(False,"1.60")):
            with self.subTest(irregularity=irregularity):
                x=eq_4_31_base_scale(
                    equivalent_base_shear_kn="2000",modal_base_shear_kn="1000",
                    irregularity_A1_B2_B3_any=irregularity,
                    irregularity_inventory_complete=True,
                    basement_boundary_qualified=True)
                self.assertEqual(Decimal(x["required_scale_factor"]),Decimal(expected))
                self.assertEqual(x["source_status"],"FORMULA_ONLY_UNQUALIFIED")

    def test_4_31_no_scaling_when_modal_sufficient(self):
        x=eq_4_31_base_scale(
            equivalent_base_shear_kn="1000",modal_base_shear_kn="1100",
            irregularity_A1_B2_B3_any=False,irregularity_inventory_complete=True,
            basement_boundary_qualified=True)
        self.assertEqual(Decimal(x["required_scale_factor"]),Decimal(1))
        self.assertEqual(x["scaling_required"],"false")

    def test_4_31_refuses_unknown_irregularity_or_basement(self):
        for kwargs in (
            dict(irregularity_A1_B2_B3_any=None,irregularity_inventory_complete=True,
                 basement_boundary_qualified=True),
            dict(irregularity_A1_B2_B3_any=False,irregularity_inventory_complete=False,
                 basement_boundary_qualified=True),
            dict(irregularity_A1_B2_B3_any=False,irregularity_inventory_complete=True,
                 basement_boundary_qualified=False),
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(UnqualifiedEngineeringInput):
                    eq_4_31_base_scale(
                        equivalent_base_shear_kn=2000,modal_base_shear_kn=1000,**kwargs)

    def test_4_34_adhered_brick_case_and_flexible_exception(self):
        example=dict(reduced_relative_displacement_m="0.012",story_height_m="3",
                     R="8",importance_factor="1.5",lambda_dd3_dd2="0.35",
                     material="RC")
        a=eq_4_34_effective_drift(**example,wall_connection="ADHERED_BRITTLE")
        self.assertEqual(a["condition_satisfied_if_all_input_proofs_accepted"],"true")
        self.assertEqual(Decimal(a["limit"]),Decimal("0.008"))
        with self.assertRaises(UnqualifiedEngineeringInput):
            eq_4_34_effective_drift(**example,wall_connection="DOCUMENTED_FLEXIBLE")
        b=eq_4_34_effective_drift(**example,wall_connection="DOCUMENTED_FLEXIBLE",
                                  flexible_wall_capacity_documented=True)
        self.assertEqual(Decimal(b["limit"]),Decimal("0.016"))

    def test_4_34_limit_and_kappa_steel(self):
        a=eq_4_34_effective_drift(
            reduced_relative_displacement_m="0.020",story_height_m="3",
            R="8",importance_factor="1",lambda_dd3_dd2="0.5",
            material="STEEL",wall_connection="ADHERED_BRITTLE")
        self.assertEqual(Decimal(a["limit"]),Decimal("0.004"))
        self.assertEqual(a["condition_satisfied_if_all_input_proofs_accepted"],"false")

    def test_4_9_lambda_and_invalid_inputs(self):
        self.assertEqual(Decimal(eq_4_9_lambda(sae_dd3_m_s2="0.9",sae_dd2_m_s2="3")),
                         Decimal("0.3"))
        for fn,kwargs in (
            (eq_4_9_lambda,dict(sae_dd3_m_s2=0,sae_dd2_m_s2=3)),
            (eq_4_19_equivalent_base_shear_kn,
             dict(seismic_mass_kg=1000,reduced_spectral_acceleration_m_s2=float("nan"),
                  importance_factor=1,sds_dd2=0.4)),
        ):
            with self.subTest(fn=fn):
                with self.assertRaises(UnqualifiedEngineeringInput):
                    fn(**kwargs)

    def test_4_34_no_raw_drift_shortcut_and_unknown_material(self):
        with self.assertRaises(TypeError):
            eq_4_34_effective_drift(
                Drift="0.001",story_height_m=3,R=8,importance_factor=1,
                lambda_dd3_dd2=0.3,material="RC",wall_connection="ADHERED_BRITTLE")
        with self.assertRaises(UnqualifiedEngineeringInput):
            eq_4_34_effective_drift(
                reduced_relative_displacement_m=0.001,story_height_m=3,
                R=8,importance_factor=1,lambda_dd3_dd2=0.3,
                material="UNKNOWN",wall_connection="ADHERED_BRITTLE")

    def test_regulatory_inventory_fails_closed_with_real_shaped_data(self):
        out=review_normative_readiness(numeric_source())
        self.assertEqual(len(GATES),5)
        self.assertEqual(out["expected_check_count"],5)
        self.assertEqual(out["proven_check_count"],0)
        self.assertEqual(out["regulatory_checks_executed"],0)
        self.assertEqual(len(check_registry()),12)
        self.assertEqual(out["engineering_release"],"NOT_READY")
        self.assertTrue(all(x["status"]=="NOT_PROVEN" for x in out["checks"]))
        self.assertIn("gammaE_from_A1_B2_B3",
                      out["checks"][1]["missing_evidence"])
        self.assertIn("drift_ratio_semantics_X",
                      out["checks"][3]["missing_evidence"])
        self.assertIn("BASE_REACTION_X_DISPLAY_COMPONENT_ONLY",
                      out["checks"][1]["source_only_hints"])

    def test_missing_raw_still_precompiles_five_expected_checks(self):
        out=review_normative_readiness(None)
        self.assertEqual(out["expected_check_count"],5)
        self.assertEqual(out["proven_check_count"],0)
        self.assertEqual(out["checks"][0]["source_only_hints"],[])


class ProbeDb:
    def __init__(self):
        self.selected=("LC_DL",)
        self.keys=[
            "Story Definitions",
            "Load Case Definitions - Response Spectrum",
            "Mass Summary by Story",
            "Frame Assignments - Summary",
        ]
        self.readkeys=[]
    def GetAvailableTables(self):
        return 4,self.keys,self.keys,[0]*4,0
    def GetLoadCasesSelectedForDisplay(self):
        return len(self.selected),list(self.selected),0
    def GetAllFieldsInTable(self,key):
        return 1,2,["Name","Value"],["Name","Value"],["",""],["",""],[False,False],0
    def GetTableForDisplayArray(self,key,*args):
        self.readkeys.append(key)
        return None,1,["Name","Value"],1,[key,"1"],0


class ProbeSap:
    def __init__(self,locked=True):
        self.DatabaseTables=ProbeDb()
        self.locked=locked
    def GetModelIsLocked(self):
        return self.locked
    def GetPresentUnits(self):
        return 6


class BasisSourceProbeTests(unittest.TestCase):
    def test_discover_and_read_candidates_without_selection_mutations(self):
        sap=ProbeSap()
        result=capture_basis_probe(sap,max_tables=2)
        self.assertEqual(result["available_table_count"],4)
        self.assertEqual(result["candidate_table_count"],3)
        self.assertEqual(len(result["read_table_keys"]),2)
        self.assertEqual(len(result["not_read_table_keys"]),1)
        self.assertEqual(sap.DatabaseTables.selected,("LC_DL",))
        self.assertEqual(len(sap.DatabaseTables.readkeys),2)
        review=review_basis_probe(result)
        self.assertEqual(review["candidate_count"],3)
        self.assertEqual(review["observed_candidate_count"],2)
        self.assertEqual(review["engineering_release"],"NOT_READY")

    def test_invalid_available_table_abi_and_duplicate_keys_rejected(self):
        for obj in ((1,["A"],["A"],[0],1), (1,["A","A"],["A","A"],[0,0],0)):
            with self.subTest(obj=obj):
                with self.assertRaises(ModalCaptureError):
                    parse_available_tables(obj)

    def test_unlocked_model_and_changed_case_selection_rejected(self):
        with self.assertRaises(ModalCaptureError):
            capture_basis_probe(ProbeSap(locked=False))
        x=capture_basis_probe(ProbeSap())
        x["display_cases_after"]=["TAMPERED"]
        self.assertEqual(review_basis_probe(x)["status"],"SOURCE_REJECTED")

    def test_unsupported_capture_schema_never_passes(self):
        self.assertEqual(review_basis_probe({})["status"],"SOURCE_REJECTED")


if __name__=="__main__":
    unittest.main()
