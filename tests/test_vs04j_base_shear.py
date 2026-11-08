"""VS04-J source-only conditional base-shear screen and negative gates.

All test fixtures are synthetic. The conditional minimum term is NOT a
design VtE nor an approved gamma/beta/analysis scale factor.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.base_shear_screening import review_base_shear_screening
from tbdy_next.analysis_numerics import evaluate_analysis_numerics
from tbdy_next.quick_checks import check_registry
from test_vs04f_bindings import fixture as basis_fixture
from test_vs04i_spectrum import fixture as spectrum_fixture
from test_vs04_numerics import numeric_source
from tools.review_vs04j_base_shear import replay_screening


def fixture():
    basis = basis_fixture()
    spectra, selected, modal = spectrum_fixture()
    new_table = spectra["source"]["table_reads"][
        "Functions - Response Spectrum - TSC-2018"]
    rows = new_table["rows"]
    metadata = (("Ss", "0.345"), ("S1", "0.111"),
                ("Fs", "1.524"), ("F1", "2.378"))
    for idx, row in enumerate(rows):
        for field, number in metadata:
            row[field] = number if idx == 0 else "None"
    new_table["fields"] += [field for field, _ in metadata]
    new_table["field_metadata"]["field_keys"] = list(new_table["fields"])
    new_table["field_metadata"]["field_count"] = len(new_table["fields"])
    for field, _ in metadata:
        new_table["field_metadata"]["units_by_field"][field] = ""
    new_table["field_metadata"]["units_by_field"]["I"] = "sec"
    basis["source"]["table_reads"]["Functions - Response Spectrum - TSC-2018"] = new_table
    # VS04-F's historical fixture calls the function SYNTHETIC, while
    # VS04-I uses the observed RESP_YATAY identity. They are unrelated
    # independent synthetic fixtures: reconcile the *test inputs* only.
    for case in basis["source"]["table_reads"]["Load Case Definitions - Response Spectrum"]["rows"]:
        case["Function"] = "RESP_YATAY"
    modal["numeric_source_review"]["numeric_regulatory_checks_executed"] = 0
    all_results = evaluate_analysis_numerics(numeric_source())["results"]
    modal["numeric_source_review"]["results"] += [all_results[1], all_results[2]]
    return basis, selected, modal


class Vs04JTests(unittest.TestCase):
    def setUp(self):
        self.basis, self.selected, self.modal = fixture()

    def test_conditional_eq_4_19_floor_from_independent_synthetic_sources(self):
        result = review_base_shear_screening(self.basis,self.selected,self.modal)
        self.assertEqual(result["status"], "CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING")
        self.assertEqual(Decimal(result["source_mass_candidate_ton"]), Decimal(30))
        self.assertEqual(Decimal(result["source_mass_candidate_kg"]), Decimal(30000))
        expected = Decimal("0.04")*Decimal(30000)*Decimal("1.5")*Decimal("0.52578")*Decimal("9.80665")/1000
        self.assertEqual(Decimal(result["conditional_eq_4_19_minimum_term_kn"]), expected)
        self.assertEqual(result["source_case_base_reaction_components_kn"],
                         {"RSX_FX":"120","RSY_FY":"140"})
        self.assertEqual(result["spectrum_modal_rows_verified"],200)
        self.assertEqual(result["spectrum_function_samples_verified"],26)
        self.assertEqual(result["normative_checks_executed"],0)
        self.assertEqual(result["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(result["engineering_release"],"NOT_READY")
        self.assertFalse(result["governing_periods_XY_authorized"])
        self.assertIsNone(result["full_equivalent_base_shear_kn"])
        self.assertIsNone(result["beta_tE_X"])
        self.assertIsNone(result["beta_tE_Y"])
        self.assertEqual(len(check_registry()),12)

    def test_mutated_mass_group_denied_not_silently_used(self):
        x=deepcopy(self.basis)
        rows=x["source"]["table_reads"]["Mass Summary by Group"]["rows"]
        rows[0]["MassX"]="55"
        outcome=review_base_shear_screening(x,self.selected,self.modal)
        self.assertEqual(outcome["status"],"NOT_PROVEN")
        self.assertIsNone(outcome["conditional_eq_4_19_minimum_term_kn"])

    def test_unknown_or_unqualified_case_source_denied(self):
        x=deepcopy(self.basis)
        x["source"]["table_reads"]["Load Case Definitions - Response Spectrum"]["rows"][0]["Function"]="WRONG"
        result=review_base_shear_screening(x,self.selected,self.modal)
        self.assertEqual(result["status"],"NOT_PROVEN")

    def test_corrupted_modal_spectrum_denies_conditional_floor(self):
        x=deepcopy(self.selected)
        x["source"]["spectrum_modal_selected_cases"]["rows"][0]["U1Acc"]="6.0"
        result=review_base_shear_screening(self.basis,x,self.modal)
        self.assertEqual(result["status"],"NOT_PROVEN")

    def test_modal_case_and_prior_replay_binding_denied(self):
        x=deepcopy(self.modal)
        x["numeric_source_review"]["results"][0]["items"][0]["circular_frequency_rad_sec"]="100"
        result=review_base_shear_screening(self.basis,self.selected,x)
        self.assertEqual(result["status"],"NOT_PROVEN")

    def test_base_reaction_display_cannot_be_relabelled_pre_beta_vtx(self):
        x=deepcopy(self.modal)
        x["numeric_source_review"]["results"][1]["items"][0]["source_semantics"]="PRE_BETA_APPROVED"
        result=review_base_shear_screening(self.basis,self.selected,x)
        self.assertEqual(result["status"],"NOT_PROVEN")
        self.assertFalse(result["pre_beta_modal_base_shear_authorized"])

    def test_wrong_direction_or_abs_mismatch_denied(self):
        for field,value in (("output_case","RSY"),("absolute_reaction_kn","121")):
            with self.subTest(field=field):
                x=deepcopy(self.modal)
                x["numeric_source_review"]["results"][1]["items"][0][field]=value
                result=review_base_shear_screening(self.basis,self.selected,x)
                self.assertEqual(result["status"],"NOT_PROVEN")

    def test_nonfinite_header_importance_factor_denied(self):
        x=deepcopy(self.basis)
        x["source"]["table_reads"]["Functions - Response Spectrum - TSC-2018"]["rows"][0]["I"]="NaN"
        result=review_base_shear_screening(x,self.selected,self.modal)
        self.assertEqual(result["status"],"NOT_PROVEN")

    def test_synthetic_source_never_creates_ninth_normative_check(self):
        output=review_base_shear_screening(self.basis,self.selected,self.modal)
        self.assertIsNone(output["full_equivalent_base_shear_kn"])
        self.assertEqual(output["normative_checks_executed"],0)
        self.assertFalse(output["model_analysis_generation_proven"])
        self.assertFalse(output["irregularity_A1_B2_B3_inventory_authorized"])
        self.assertFalse(output["basement_boundary_authorized"])

    def test_missing_source_rejected(self):
        outcome=review_base_shear_screening(None,self.selected,self.modal)
        self.assertEqual(outcome["status"],"NOT_PROVEN")
        self.assertIn("EXACT_THREE_SOURCE_RECEIPTS_REQUIRED",outcome["reason_codes"])

    def test_source_replay_deterministic_and_immutable(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            files=[]
            for n, data in enumerate((self.basis,self.selected,self.modal)):
                file=root/f"src_{n}.json"
                file.write_text(json.dumps(data,sort_keys=True),encoding="utf8")
                files.append(file)
            originals=[f.read_bytes() for f in files]
            out=root/"screen.json"
            value=replay_screening(*files,out)
            self.assertEqual(value["screening"]["status"],"CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING")
            self.assertEqual(json.loads(out.read_text(encoding="utf8")),value)
            self.assertTrue(all(a.read_bytes()==b for a,b in zip(files,originals)))
            with self.assertRaises(ValueError):
                replay_screening(*files,out)
            with self.assertRaises(ValueError):
                replay_screening(*files,files[0])


if __name__ == "__main__":
    unittest.main()
