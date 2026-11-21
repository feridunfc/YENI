"""Existing production scalar owners versus pinned report and independent values.

Synthetic wrapper examples below verify routing and boundaries, not live ETABS
or physical engineering acceptance. No production arithmetic is the oracle.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import math
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tbdy_next import spectrum_reconstruction
from tbdy_next.column_engine import joint_kernel, transverse_kernel
from tbdy_next.column_engine.native_archive import BankError
from tbdy_next.engineering import column_r10_live, rebar_selection
from tbdy_next.verification import golden_gate as gate
import test_r13_joint_adapters as joint_fixture


class GoldenScalarAdapterTests(unittest.TestCase):
    def test_new_rows_call_the_same_scalar_owners_with_declared_units(self):
        owners = (
            (gate.basis_linkage, "spectral_design_coefficients"),
            (gate.spectrum_reconstruction, "spectral_corner_periods"),
            (gate.transverse_kernel, "provided_transverse_steel"),
            (gate.transverse_kernel, "confinement_axial_threshold"),
            (gate.joint_kernel, "beam_steel_tension_kn"),
            (gate.joint_kernel, "joint_shear_equilibrium_kn"),
            (gate.ts500_column, "eq729_single_reading"),
            (gate.ts500_column, "member_magnification_coefficient"),
        )
        from contextlib import ExitStack
        with ExitStack() as stack:
            spies = [stack.enter_context(patch.object(module, name, wraps=getattr(module, name))) for module, name in owners]
            result = gate.build_golden_gate()
        self.assertEqual([p.call_count for p in spies], [1, 2, 1, 1, 3, 2, 4, 7])
        spies[-1].assert_any_call(nd_kn=85.13, nk_kn=26790.32, cm=.41)
        spies[2].assert_called_once_with(leg_count=4, diameter_mm=8, spacing_mm=80)
        spies[3].assert_called_once_with(area_mm2=160000, fck_mpa=30)
        self.assertEqual(result["classification_counts"], {
            "NUMERICAL_MATCH": 36, "INSUFFICIENT_SOURCE": 4, "ENGINEERING_INTERPRETATION_DIFFERENCE": 4,
        })
        rows = {r["id"]: r for r in result["comparisons"]}
        expected = {"G01_SDS": .6592, "G01_SD1": .1912,
                    "G01_TA": float(Decimal('.2') * Decimal('.1912') / Decimal('.6592')),
                    "G01_TB": float(Decimal('.1912') / Decimal('.6592')),
                    "G01_CONFINEMENT_ASW_OVER_S": math.pi * 8 * 8 / 80 * 10,
                    "G01_CONFINEMENT_AXIAL_BRANCH_THRESHOLD": 960.,
                    "G01_JOINT_VE_ONE_BEAM_APPROX": 198.605,
                    "G01_JOINT_VE_TWO_BEAM_APPROX": 389.015,
                    "G01_LOCAL_BETA_NON_DIAGNOSTIC": 1.}
        for key, value in expected.items():
            with self.subTest(case=key):
                self.assertAlmostEqual(rows[key]["yeni"], value, places=10)
                self.assertEqual(rows[key]["classification"], "NUMERICAL_MATCH")
        self.assertEqual(rows["G01_CONFINEMENT_ASW_OVER_S"]["quantity_unit"], "cm2/m")
        self.assertIn("does not discriminate", rows["G01_LOCAL_BETA_NON_DIAGNOSTIC"]["explanation"])
        for key in ("G01_SWAY_PHI_GROUND", "G01_SWAY_PHI_UPPER"):
            self.assertTrue(rows[key]["source_inputs_available"])
            self.assertEqual(rows[key]["classification"], "NUMERICAL_MATCH")
            self.assertFalse(rows[key]["source_population_qualified"])
        self.assertFalse(result["acceptance_eligible"])

    def test_original_fixture_ids_expected_values_tolerances_and_source_identity_are_preserved(self):
        manifest, first, _, _ = gate.load_bank()
        rows = {r["id"]: r for r in gate.build_golden_gate()["comparisons"]}
        for case in first["arithmetic_cases"]:
            row = rows["G01_" + case["id"]]
            self.assertEqual(row["inputs"], case["inputs"])
            self.assertEqual(row["report"], case["expected"])
            self.assertEqual(row["report_rounding_tolerance"], case["absolute_tolerance"])
        self.assertEqual(gate.MANIFEST_SHA256, "59dedec19a7e6c3d5f496e8d616b8c708af3c99701e271bd872644e39361bec7")
        material = gate._material_binding(manifest)
        self.assertEqual(material["source_pdf_sha256"], next(r["sha256"] for r in manifest["reports"] if r["id"] == "GOLDEN-02"))
        self.assertEqual((material["pdf_page_1_based"], material["printed_page"], material["fck_mpa"]), (7, 5, 30))

    def test_real_sway_rows_recompute_the_source_scalars_before_the_branch_comparison(self):
        with patch.object(gate.ts500_column, "sway_phi_reference", wraps=gate.ts500_column.sway_phi_reference) as owner:
            result = gate.build_golden_gate()
        self.assertEqual(owner.call_count, 4)
        owner.assert_any_call(drift_m=1.574 / 1000, sum_nd_over_length_kn_per_m=732.22, story_shear_kn=169.25)
        owner.assert_any_call(drift_m=1.670 / 1000, sum_nd_over_length_kn_per_m=424.47, story_shear_kn=117.23)
        owner.assert_any_call(drift_m=5.347 / 1000, sum_nd_over_length_kn_per_m=652.08, story_shear_kn=55.69)
        rows = {row["id"]: row for row in result["comparisons"]}
        # Decimal report arithmetic is independent of the production owner.
        for case_id, drift, total, shear in (
            ("G01_SWAY_PHI_GROUND", "1.574", "732.22", "169.25"),
            ("G01_SWAY_PHI_UPPER", "1.670", "424.47", "117.23"),
        ):
            row = rows[case_id]
            expected = Decimal('1.5') * Decimal(drift) * Decimal(total) / (Decimal('1000') * Decimal(shear))
            self.assertAlmostEqual(row["yeni"], float(expected), places=15)
            self.assertEqual(row["source_binding"]["pdf_page_1_based"], 186)
            self.assertEqual(row["source_directions"], ["X", "Y"])
            self.assertFalse(row["automatic_sway_assignment_authorized"])
        changed = rows["G02_SWAY_BRANCH_CHANGED"]
        self.assertIs(changed["yeni"], True)
        old, new = (changed["intermediate_comparisons"][key] for key in ("reference", "revised"))
        self.assertEqual(new["inputs"], {"delta_mm": 5.347, "sum_N_over_L_kN_per_m": 652.08, "story_shear_kN": 55.69})
        self.assertEqual((old["source_binding"]["report_id"], new["source_binding"]["report_id"]), ("GOLDEN-01", "GOLDEN-02"))
        self.assertEqual(new["source_binding"]["pdf_page_1_based"], 185)
        expected = Decimal('1.5') * Decimal('5.347') * Decimal('652.08') / (Decimal('1000') * Decimal('55.69'))
        self.assertAlmostEqual(new["yeni"], float(expected), places=15)
        self.assertFalse(changed["source_population_qualified"])
        self.assertFalse(changed["engineering_acceptance"])
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_sway_unit_errors_cannot_pass_on_the_same_threshold_boolean(self):
        actual = gate.ts500_column.sway_phi_reference
        def wrong_units(**values):
            values["drift_m"] *= 1000
            return actual(**values)
        with patch.object(gate.ts500_column, "sway_phi_reference", side_effect=wrong_units):
            with self.assertRaisesRegex(gate.GoldenRegressionError, "YENI_ORACLE_MISMATCH"):
                gate.build_golden_gate()

    def test_sway_source_rows_require_both_directions_and_original_fixture_values(self):
        _, first, second, excerpts = gate.load_bank()
        changed = deepcopy(excerpts)
        page = next(row for row in changed if row["report_id"] == "GOLDEN-02" and row["pdf_page_1_based"] == 185)
        page["text"] = page["text"].split("Y Yönü")[0]
        with self.assertRaisesRegex(gate.GoldenRegressionError, "SWAY_SOURCE_ROWS_INCOMPLETE"):
            gate._bound_sway_reports(first, second, changed)
        changed = deepcopy(excerpts)
        page = next(row for row in changed if row["report_id"] == "GOLDEN-01" and row["pdf_page_1_based"] == 186)
        page["text"] = page["text"].replace("732.22", "732.23")
        with self.assertRaisesRegex(gate.GoldenRegressionError, "SWAY_FIXTURE_EXCERPT_CONFLICT"):
            gate._bound_sway_reports(first, second, changed)

    def test_sway_scalar_domains_and_threshold_sensitivity_use_the_real_ground_inputs(self):
        _, first, _, _ = gate.load_bank()
        source = next(row["inputs"] for row in first["arithmetic_cases"] if row["id"] == "SWAY_PHI_GROUND")
        original = dict(drift_m=source["delta_mm"] / 1000,
                        sum_nd_over_length_kn_per_m=source["sum_N_over_L_kN_per_m"],
                        story_shear_kn=source["story_shear_kN"])
        owner = gate.ts500_column.sway_phi_reference
        # A scalar boundary perturbation of the same report row, not a new building.
        limit_drift = .05 * original["story_shear_kn"] / (1.5 * original["sum_nd_over_length_kn_per_m"])
        self.assertAlmostEqual(owner(**{**original, "drift_m": limit_drift}), .05, places=15)
        self.assertLess(owner(**{**original, "drift_m": limit_drift * (1 - 1e-8)}), .05)
        self.assertGreater(owner(**{**original, "drift_m": limit_drift * (1 + 1e-8)}), .05)
        self.assertEqual(owner(**{**original, "drift_m": 0.}), 0.)
        for key, values in (
            ("drift_m", (-1., math.nan, math.inf, True)),
            ("sum_nd_over_length_kn_per_m", (-1., math.nan, math.inf, True)),
            ("story_shear_kn", (0., -1., math.nan, math.inf, True)),
        ):
            for value in values:
                with self.subTest(field=key, value=value), self.assertRaises(BankError):
                    owner(**{**original, key: value})

    def test_wrong_unit_or_owner_arithmetic_fails_independent_comparison(self):
        mutations = (
            (gate.basis_linkage, "spectral_design_coefficients", {"sds": Decimal('.65'), "sd1": Decimal('.1912')}),
            (gate.transverse_kernel, "provided_transverse_steel", {"provided_ash_mm2": 201.0619, "ash_per_s_mm2_per_mm": 25.1327}),
            (gate.transverse_kernel, "confinement_axial_threshold", {"axial_limit_n": 960000., "axial_limit_kn": 960000.}),
            (gate.joint_kernel, "joint_shear_equilibrium_kn", 200.),
            (gate.ts500_column, "member_magnification_coefficient", 1.1),
        )
        for module, name, value in mutations:
            with self.subTest(owner=name), patch.object(module, name, return_value=value):
                with self.assertRaisesRegex(gate.GoldenRegressionError, "YENI_ORACLE_MISMATCH"):
                    gate.build_golden_gate()

    def test_printed_length_compares_intermediates_without_authorizing_a_factor(self):
        result = gate.build_golden_gate()
        rows = [r for r in result["comparisons"] if r["id"].startswith("G02_EQ729_")]
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertIs(row["yeni"], False)
            self.assertEqual(row["report_rounding_tolerance"], 0)
            self.assertNotIn("free_length_ln_mm", row["inputs"])
            for comparison in row["intermediate_comparisons"].values():
                self.assertLessEqual(comparison["yeni_oracle_difference"], comparison["yeni_oracle_tolerance"])
                self.assertEqual(comparison["target_provenance"], "INDEPENDENT_DERIVED_NOT_PRINTED")
        interpreted = [r for r in result["comparisons"] if r["id"].startswith("G02_USED_FACTOR_")]
        self.assertTrue(all(r["classification"] == "ENGINEERING_INTERPRETATION_DIFFERENCE" for r in interpreted))
        owner = gate.ts500_column.eq729_single_reading
        def wrong_threshold(**kwargs):
            return {**owner(**kwargs), "threshold": 99999.}
        with patch.object(gate.ts500_column, "eq729_single_reading", side_effect=wrong_threshold):
            with self.assertRaisesRegex(gate.GoldenRegressionError, "YENI_ORACLE_MISMATCH"):
                gate.build_golden_gate()

    def test_material_binding_is_pinned_independently_of_original_archives(self):
        with TemporaryDirectory() as directory:
            copied = Path(directory) / 'bank'
            shutil.copytree(gate.ROOT, copied, ignore=shutil.ignore_patterns('__pycache__'))
            binding = copied / gate.MATERIAL_BINDING_FILE
            binding.write_text(binding.read_text().replace('"fck_mpa": 30', '"fck_mpa": 35'))
            with self.assertRaisesRegex(gate.GoldenRegressionError, "ADAPTER_MATERIAL_BINDING_CHANGED"):
                gate.load_bank(root=copied)

    def test_live_joint_adapter_uses_shared_equilibrium_and_retains_missing_case_bound(self):
        fixture = joint_fixture.JointAdapterInvariantTests()
        fixture.setUp()
        with patch.object(column_r10_live, "beam_steel_tension_kn", wraps=joint_kernel.beam_steel_tension_kn) as tension, \
             patch.object(column_r10_live, "joint_shear_equilibrium_kn", wraps=joint_kernel.joint_shear_equilibrium_kn) as equilibrium:
            full = fixture.calculate()["joint_shear_ve"]
            missing = fixture.calculate(force_rows={"L": fixture.force_rows("L")})["joint_shear_ve"]
        self.assertEqual(full["governing_ve_kn"], 850.)
        self.assertEqual(missing["governing_ve_kn"], 1050.)
        self.assertFalse(missing["column_shear_scope_complete"])
        self.assertEqual(tension.call_count, 8)
        self.assertEqual(equilibrium.call_count, 4)

    def test_selected_transverse_geometry_uses_shared_area_and_threshold(self):
        with patch.object(rebar_selection, "provided_transverse_steel", wraps=transverse_kernel.provided_transverse_steel) as steel, \
             patch.object(rebar_selection, "confinement_axial_threshold", wraps=transverse_kernel.confinement_axial_threshold) as threshold:
            result = rebar_selection._evaluate_column_transverse_choice(
                tie_d=8, s_conf_mm=80., s_span_mm=150., long_d=16, n2=4, n3=4,
                t2_mm=400., t3_mm=400., cover_mm=35., fck_mpa=30., fywk_mpa=420.,
                gamma_c=1.5, gamma_s=1.15, shear_demands=[],
            )
        self.assertEqual(steel.call_count, 2)
        threshold.assert_called_once_with(area_mm2=160000., fck_mpa=30.)
        self.assertAlmostEqual(result["confinement_v2"]["ash_mm2"], math.pi * 8 * 8)
        self.assertAlmostEqual(result["confinement_v3"]["ash_mm2"], math.pi * 8 * 8)

    def test_full_spectrum_operation_reuses_corner_periods(self):
        D = Decimal
        with patch.object(spectrum_reconstruction, "spectral_corner_periods", wraps=spectrum_reconstruction.spectral_corner_periods) as periods:
            actual = spectrum_reconstruction._spectrum(D('.1'), sds=D('.6592'), sd1=D('.1912'), R=D(8), D=D(3), I=D(1), TL=D(6))
        expected = D('.6592') / (D(3) + D(5) * D('.1') * D('.6592') / D('.1912'))
        self.assertEqual(actual, expected)
        periods.assert_called_once_with(sds=D('.6592'), sd1=D('.1912'))

    def test_scalar_input_domains_and_nonnegative_equilibrium_boundary(self):
        self.assertEqual(joint_kernel.joint_shear_equilibrium_kn(beam_tension_kn=10., column_shear_deduction_kn=10.), 0.)
        self.assertEqual(joint_kernel.joint_shear_equilibrium_kn(beam_tension_kn=10., column_shear_deduction_kn=11.), 0.)
        self.assertEqual(joint_kernel.beam_steel_tension_kn(fyk_mpa=420., area_mm2=0.), 0.)
        for invalid in (-1., math.nan, math.inf):
            with self.subTest(value=invalid), self.assertRaises(BankError):
                joint_kernel.joint_shear_equilibrium_kn(beam_tension_kn=10., column_shear_deduction_kn=invalid)
        for invalid in (0, -1, True, 2.5):
            with self.subTest(legs=invalid), self.assertRaises(BankError):
                transverse_kernel.provided_transverse_steel(leg_count=invalid, diameter_mm=8., spacing_mm=80.)
        for invalid in (Decimal(0), Decimal('-1'), Decimal('NaN'), Decimal('Infinity')):
            with self.subTest(coefficient=invalid), self.assertRaises(ValueError):
                spectrum_reconstruction.spectral_corner_periods(sds=invalid, sd1=Decimal('.2'))

    def test_reference_coverage_denominator_is_frozen_before_success(self):
        manifest, first, second, _ = gate.load_bank()
        expected = gate._required_comparison_ids(first, second)
        result = gate.build_golden_gate()
        coverage = result["reference_comparison_coverage"]
        self.assertEqual((coverage["expected_count"], coverage["observed_count"], coverage["matched_count"]), (44, 44, 36))
        self.assertEqual(len(coverage["unresolved_ids"]), 8)
        self.assertFalse(result["reference_comparisons_complete"])
        self.assertFalse(coverage["engineering_acceptance_granted"])
        removed = result["comparisons"][1:]
        partial = gate.reference_comparison_coverage(removed, expected)
        self.assertEqual(partial["expected_count"], 44)
        self.assertEqual(partial["missing_ids"], [result["comparisons"][0]["id"]])
        for bad in (result["comparisons"] + [result["comparisons"][0]],
                    result["comparisons"] + [{"id": "UNREGISTERED"}]):
            with self.assertRaisesRegex(gate.GoldenRegressionError, "POPULATION_CONFLICT"):
                gate.reference_comparison_coverage(bad, expected)

    def test_coverage_can_finish_its_explicit_contract_without_engineering_authority(self):
        # Only a predicate contract fixture, not production golden results.
        rows = [{"id": key, "classification": "NUMERICAL_MATCH", "yeni": value,
                 "independent": value, "report": value, "report_rounding_tolerance": 0}
                for key, value in (("CONTRACT_A", 1.), ("CONTRACT_B", False))]
        coverage = gate.reference_comparison_coverage(rows, ("CONTRACT_A", "CONTRACT_B"))
        self.assertTrue(coverage["complete"])
        self.assertFalse(coverage["engineering_acceptance_granted"])
        rows[0]["yeni"] = None
        with self.assertRaisesRegex(gate.GoldenRegressionError, "MATCH_WITHOUT_COMPARISON_VALUES"):
            gate.reference_comparison_coverage(rows, ("CONTRACT_A", "CONTRACT_B"))

    def test_progress_report_projects_saved_result_without_new_owner_calls(self):
        result = gate.build_golden_gate()
        with patch.object(gate, "build_golden_gate", side_effect=AssertionError('report-time calculation')):
            html = gate.build_golden_html(result)
        self.assertIn('36 / 44 matched', html)
        self.assertIn('Unresolved records: 8', html)
        legacy = deepcopy(result)
        for key in ('reference_comparison_coverage', 'reference_comparisons_complete', 'adapter_source_bindings'):
            legacy.pop(key)
        legacy['result_sha256'] = gate.digest({k: v for k, v in legacy.items() if k != 'result_sha256'})
        self.assertIn('not recorded in this legacy result', gate.build_golden_html(legacy))


if __name__ == '__main__':
    unittest.main()
