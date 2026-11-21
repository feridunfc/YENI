"""Actual selected spectral shear owners; R14/dependency records are consumer fixtures."""
from copy import deepcopy
import unittest

from test_audit_hardening import closure_fixture
from test_column_spectral_shear import fixture
from test_design_member_dependencies import artifacts, fixture as dependency_fixture
from test_r10_live import _rowset
from test_scwb_axial_interval import section
from tbdy_next.engineering.column_r14_closure import _evaluate_single_r14_column
from tbdy_next.engineering.column_spectral_shear import (
    NATIVE_BRITTLE_FAILURE, selected_spectral_shear, spectral_native_brittle_violations,
)
from tbdy_next.engineering.design_dependencies import build_revision_evidence
from tbdy_next.engineering.design_scenario import _digest


def actual_spectral_result(center=3000., radius=12., length=4., missing_case=False):
    cuts, native = fixture(center=center, radius=radius)
    remapped_cuts, rows = {}, []
    for key, cut in cuts.items():
        station = key[1] * length / 4.
        new_key = ("C", station, "C", station)
        cut["native_cut"] = list(new_key)
        cut["primitive_replay"]["center_native"]["V3"] = 8.
        cut["primitive_replay"]["radius_native"]["V3"] = 4.
        remapped_cuts[new_key] = cut
        for step, row in native["E", key].items():
            rows.append((*new_key, *row[4:9], 4. if step == "Min" else 12., *row[10:]))
    names = ["E", "E2"] if missing_case else ["E"]
    scope = {"analysis_mesh": {"members": {"C": {"roster_bound": True,
        "expected_analysis_element_ids": ["C"], "analysis_element_end_joints": {"C": ["I", "J"]}}}},
        "configured_output_cuts": {"C": {"status": "REQUIRED_SUBSET_BOUND", "length_m": length,
            "offset_i_m": 0., "offset_j_m": 0., "cuts": [{"analysis_element_id": "C",
                "object_station_m": key[1], "element_station_m": key[3]} for key in remapped_cuts]}}}
    context = {"names": names, "input_sha256": "input", "scope": scope, "error": None, "controls": {},
               "pairs": {"C": {"E": {"status": "SAME_SOURCE_COMPONENT_REPLAY_MATCH",
                   "expected_cut_count": 3, "cuts": list(remapped_cuts.values())}}}}
    selection = {"diameter_mm": 20., "selected_transverse": {"tie_diameter_mm": 10.,
        "confinement_spacing_mm": 90., "midspan_spacing_mm": 90., "legs_v2": 4, "legs_v3": 4}}
    return selected_spectral_shear(context, {"frame_id": "C", "point_i": "I", "point_j": "J"},
        _rowset(rows), section(), selection, {"cover_to_tie_mm": 40., "fck_mpa": 35., "fcd_mpa": 35./1.5,
            "gamma_s": 1.15}, 420., length, "END_OFFSETS_SUBTRACTED",
        {"V2": {"bending_axis": "M3", "direction": "X"}, "V3": {"bending_axis": "M2", "direction": "Y"}},
        "candidate", None)


def violations(result, **changes):
    args = dict(result=result, names=set(result["assigned_combinations"]), uid="C", input_sha="input", revision=_digest(result))
    return spectral_native_brittle_violations(**{**args, **changes})


class NativeSpectralFailureTests(unittest.TestCase):
    def test_native_vd_failure_is_definite_without_optional_model_d_control(self):
        result = actual_spectral_result()
        self.assertEqual(result["status"], NATIVE_BRITTLE_FAILURE, result)
        failed = violations(result)
        self.assertEqual([(r["combination"], r["axis"]) for r in failed], [("E", "V2")])
        self.assertEqual(failed[0]["vd_floor_kn"], 3012.)
        self.assertGreater(failed[0]["native_brittle_utilization"], 1.)
        case = result["axes"]["V2"]["cases"][0]
        self.assertEqual(case["cap_control"]["status"], "MODEL_D_COMBINATION_UNRESOLVED")
        self.assertEqual(result["calculated_axis_case_count"], 2)

    def test_conservative_upper_bound_exceedance_is_still_review(self):
        result = actual_spectral_result(center=8., length=.4)
        self.assertEqual(result["status"], "CONSERVATIVE_BOUND_EXCEEDS_LIMIT_REVIEW_REQUIRED", result)
        self.assertEqual(violations(result), [])
        self.assertLess(result["max_native_brittle_utilization"], 1.)

    def test_equality_and_adjacent_native_limit_values(self):
        limit = actual_spectral_result()["axes"]["V2"]["cases"][0]["tbdy_eq7_7_limit_kn"]
        for delta, expected in ((-1e-8, False), (0., False), (1e-8, True)):
            with self.subTest(delta=delta):
                result = actual_spectral_result(center=limit+delta, radius=0.)
                self.assertEqual(bool(violations(result)), expected)

    def test_known_failure_survives_missing_other_case_without_removing_scope(self):
        result = actual_spectral_result(missing_case=True)
        self.assertEqual(result["status"], NATIVE_BRITTLE_FAILURE)
        self.assertEqual(result["expected_axis_case_count"], 4)
        self.assertEqual(result["calculated_axis_case_count"], 2)
        self.assertEqual(len(violations(result)), 1)
        self.assertEqual(result["axes"]["V2"]["cases"][1]["status"], "SPECTRAL_SHEAR_UNRESOLVED")

    def test_source_hash_cage_witness_or_scope_tampering_cannot_prove_failure(self):
        result = actual_spectral_result()
        self.assertFalse(violations(result, revision="stale"))
        self.assertFalse(violations(result, input_sha="other"))
        self.assertFalse(violations(result, names={"E", "E2"}))
        for field in ("candidate", "witness", "count", "station", "status", "ratio"):
            with self.subTest(field=field):
                altered = deepcopy(result)
                case = altered["axes"]["V2"]["cases"][0]
                if field == "candidate": altered["candidate_revision_sha256"] = None
                elif field == "witness": case["vd_governing"]["signed_kn"] -= 1.
                elif field == "count": altered["calculated_axis_case_count"] = 1
                elif field == "station": case["vd_governing"]["cut"][0] = "OTHER"
                elif field == "status": case["native_brittle_limit_exceeded"] = False
                else: case["native_brittle_utilization"] = "NaN"
                self.assertFalse(violations(altered))

    def test_r14_does_not_hide_native_failure_behind_alpha_or_missing_pmm(self):
        result = actual_spectral_result(missing_case=True)
        args = closure_fixture()
        args["uid"] = "C"
        args["axial"]["combination_plan"] = {"source": "ASSIGNED_DESIGN", "blockers": [],
            "design_assignment": {"groups": {"ductile": ["E", "E2"]}}, "combinations": [
                {"name": n, "force_semantics": "SCALAR_COMPONENT_ENVELOPE"} for n in ("E", "E2")]}
        args["dependency_evidence"] = {"input_sha256": "input", "columns": {"C": {"open_gates": ["OTHER_MEMBER_UNRESOLVED"],
            "alpha_feedback_not_required": False, "spectral_shear_sha256": _digest(result)}}}
        args["r10_det"]["column_transverse_and_shear"]["engineer_capacity_shear_ve"]["assigned_spectral"] = result
        args["r08_local_col"] = None
        outcome = _evaluate_single_r14_column(**args)
        self.assertEqual(outcome["status"], "R14_FAILED_NORMATIVE_CHECK")
        self.assertIn("COLUMN_NATIVE_SPECTRAL_SHEAR_EXCEEDS_TBDY_EQ_7_7:E:V2", outcome["normative_failures"])
        self.assertIn("SECOND_ORDER_MAGNIFIED_SELECTED_PMM_NOT_COMPUTED", outcome["open_gates"])
        self.assertEqual(outcome["engineering_release"], "NOT_READY")

    def test_dependency_hash_is_retained_for_qualified_failure_beside_open_gates(self):
        source, scope = dependency_fixture()
        plan, _, _, _, r10, _, ledger, r08 = artifacts(source, scope)
        # This source/cage consumer fixture deliberately has an unrelated open
        # dependency. The actual shear result above is not a whole-model oracle.
        plan["members"]["C1"]["reason_codes"].append("OTHER_NUMERICAL_OWNER_UNRESOLVED")
        result = actual_spectral_result()
        result.update(member_id="C1", input_sha256="input-hash",
                      candidate_revision_sha256=plan["members"]["C1"]["candidate_revision_sha256"])
        r10["per_member"]["C1"]["column_transverse_and_shear"] = {"engineer_capacity_shear_ve": {"assigned_spectral": result}}
        evidence = build_revision_evidence(plan, ledger, r10, r08, input_sha="input-hash")
        self.assertTrue(evidence["columns"]["C1"]["open_gates"])
        self.assertEqual(evidence["columns"]["C1"]["spectral_shear_sha256"], _digest(result))
        result["candidate_revision_sha256"] = "another-cage"
        evidence = build_revision_evidence(plan, ledger, r10, r08, input_sha="input-hash")
        self.assertNotIn("spectral_shear_sha256", evidence["columns"]["C1"])


if __name__ == "__main__":
    unittest.main()
