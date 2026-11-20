"""Independent numeric regressions for TS 500 7.26 and TBDY 7.3.7.5.

Synthetic native-row contracts exercise existing YENI owners. They do not
qualify an ETABS model, a spectral design vector, or engineering acceptance.
"""
from copy import deepcopy
import math
import unittest
from unittest.mock import Mock

from tbdy_next.column_engine.csi_geometry import LocalSectionDims
from tbdy_next.column_engine.section_capacity import Material, Section, perimeter, solver
from tbdy_next.engineering.alpha_iteration import _feasibility, build_demand_revision
from tbdy_next.engineering.column_pmm import evaluate_column_pmm
from tbdy_next.engineering.column_r08_local_live import (
    _evaluate_spectral_bounding_corners, _magnified_moment_demand, project_column_r08_local_live,
)
from tbdy_next.engineering.column_r10_live import SelectedColumnCage, _compute_capacity_shear_axes
from tbdy_next.engineering.column_r14_closure import _evaluate_single_r14_column
from test_alpha_design_iteration import two_columns
from test_r08_local_live import _r08_local_fixture
from test_r10_live import _rowset


def _selected_section():
    bars, _, _ = perimeter(800, 800, 40, 10, 25, n2=4, n3=4)
    return Section(800, 800, bars, Material(35, 35 / 1.5, 420 / 1.15))


def _independent_euler_and_beta():
    # Twelve 25 mm bars: eight at |y|=337.5 and four at |y|=112.5 mm.
    # This oracle does not call YENI stiffness or magnification arithmetic.
    steel_i = math.pi * 25**2 / 4 * (8 * 337.5**2 + 4 * 112.5**2)
    ei = .2 * (3250 * math.sqrt(35) + 14000) * 800**4 / 12 + 200000 * steel_i
    nk = math.pi**2 * ei / 3800**2 / 1000
    return nk, 1 / (1 - 1.3 * 5000 / nk)


class MinimumEccentricityOrderTests(unittest.TestCase):
    def test_native_pmm_to_selected_r08_floors_before_magnification(self):
        source, geometry, axial, _ = _r08_local_fixture()
        combo = "G_STATIC"
        rows = [("127", x, "127-1", x, combo, "Single Value", 0.,
                 -5000., 0., 0., 0., -1., 1.) for x in (0., 3.8)]
        source["column_axial"]["force_source"]["rowsets"]["127"] = _rowset(rows)
        axial["combination_plan"] = {"blockers": [], "combinations": [
            {"name": combo, "force_semantics": "STATIC_SIGNED_VECTOR"}]}
        axial["columns"][0]["combination_checks"] = [{"combination": combo, "status": "WITHIN_LIMIT"}]
        pmm = evaluate_column_pmm(source, geometry, axial)
        self.assertEqual(pmm["status"], "NUMERICAL_COMPLETE")
        self.assertEqual((pmm["rows"][0]["m2_knm"], pmm["rows"][0]["m2_design_knm"]), (-1., -195.))
        selection = {"member_id": "127", "selected": {"label": "12Phi25"}}
        source["column_selection"] = {}
        original = deepcopy(source)
        result = project_column_r08_local_live(
            source, geometry, axial, pmm,
            {"direction_results": {axis: {"beta_ii_candidate": 1.} for axis in ("X", "Y")}},
            r10_live={"member_id": "127", "engineer_column_selection": selection},
            selected_cages={"127": SelectedColumnCage(selection, _selected_section())},
        )
        _, beta = _independent_euler_and_beta()
        # Independent hand result: 195 * 1.030504912300101 = 200.9484578985197 kNm.
        expected = 195 * beta
        self.assertAlmostEqual(expected, 200.9484578985197, places=10)
        station = result["magnified_selected_pmm"]["rows"][0]
        self.assertEqual(station["first_order_m2_knm"], -1.)
        self.assertEqual(station["first_order_m2_design_knm"], -195.)
        self.assertAlmostEqual(station["magnified_m2_design_knm"], -expected, places=9)
        self.assertAlmostEqual(station["magnified_m3_design_knm"], expected, places=9)
        self.assertEqual((station["analysis_element_id"], station["element_station_m"],
                          station["step_type"], station["step_number"]), ("127-1", 0., "Single Value", 0.))
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertEqual(source, original)

    def test_floor_boundary_sign_and_moments_above_minimum(self):
        for raw, floored, final, governed in (
            (0., 195., 429., True), (-1., -195., -429., True),
            (195., 195., 429., False), (-195., -195., -429., False),
            (300., 300., 660., False), (-400., -400., -880., False),
        ):
            with self.subTest(raw=raw):
                result = _magnified_moment_demand(
                    nd_kn=5000, m2_knm=raw, m3_knm=-raw, dims=LocalSectionDims(800, 800),
                    beta_m2=2., beta_m3=2., global_factor=1.1)
                self.assertEqual(result["first_order_m2_knm"], raw)
                self.assertEqual(result["first_order_m2_design_knm"], floored)
                self.assertAlmostEqual(result["magnified_m2_design_knm"], final, places=10)
                self.assertEqual(result["m2_floor_governed"], governed)

    def test_zero_axial_and_tension_do_not_create_eccentricity_moments(self):
        for nd in (0., -100.):
            with self.subTest(nd=nd):
                result = _magnified_moment_demand(
                    nd_kn=nd, m2_knm=-1., m3_knm=0., dims=LocalSectionDims(800, 800),
                    beta_m2=1., beta_m3=1., global_factor=1.)
                self.assertEqual((result["minimum_m2_knm"], result["minimum_m3_knm"]), (0., 0.))
                self.assertEqual((result["magnified_m2_design_knm"], result["magnified_m3_design_knm"]), (-1., 0.))

    def test_rectangular_local_dimensions_remain_on_the_correct_axis(self):
        result = _magnified_moment_demand(
            nd_kn=1000, m2_knm=-1., m3_knm=1., dims=LocalSectionDims(400, 600),
            beta_m2=2., beta_m3=3., global_factor=1.)
        self.assertEqual((result["minimum_m2_knm"], result["minimum_m3_knm"]), (33., 27.))
        self.assertEqual((result["magnified_m2_design_knm"], result["magnified_m3_design_knm"]), (-66., 81.))

    def test_invalid_magnification_is_never_a_reducing_or_nan_factor(self):
        for value in (None, True, .99, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _magnified_moment_demand(
                    nd_kn=5000, m2_knm=1., m3_knm=1., dims=LocalSectionDims(800, 800),
                    beta_m2=value, beta_m3=1., global_factor=1.)

    @staticmethod
    def _spectral_args():
        nk, _ = _independent_euler_and_beta()
        return dict(uid="127", source={"column_axial": {"force_source": {"rowsets": {"127": _rowset([
            ("127", 1.9, "127-2", 0., "E_SPEC", step, 0., p, 0., 0., 0., m, m)
            for step, p, m in (("Max", -4900., 1.), ("Min", -5000., -1.))
        ])}}}}, axial={"combination_plan": {"combinations": [
            {"name": "E_SPEC", "force_semantics": "SCALAR_COMPONENT_ENVELOPE"}]}},
            dims_local=LocalSectionDims(800, 800),
            stiffness_map={axis: {"selected_nk_ts500_7_20_kn": nk} for axis in ("M2", "M3")},
            global_beta_ii=1.)

    def test_spectral_all_four_signs_use_the_same_floor_before_beta_order(self):
        # Recorder wraps the production section solver; it supplies no capacity arithmetic.
        owner = solver(_selected_section())
        recorder = Mock(wraps=owner)
        result = _evaluate_spectral_bounding_corners(**self._spectral_args(), cap_solver=recorder)
        self.assertEqual(result["evaluated_corner_count"], 8)
        calls = [c.args for c in recorder.assess.call_args_list if c.args[0] == 5000e3]
        self.assertEqual(len(calls), 4)
        expected = 200.9484578985197
        for _, m2, m3 in calls:
            self.assertAlmostEqual(abs(m2) / 1e6, expected, places=9)
            self.assertAlmostEqual(abs(m3) / 1e6, expected, places=9)
        self.assertEqual({(math.copysign(1, c[1]), math.copysign(1, c[2])) for c in calls},
                         {(1., 1.), (1., -1.), (-1., 1.), (-1., -1.)})
        witness = result["governing_corner"]
        self.assertEqual((witness["analysis_element_id"], witness["element_station_m"]), ("127-2", 0.))
        self.assertEqual(abs(witness["first_order_m2_knm"]), 1.)
        self.assertEqual(abs(witness["first_order_m2_design_knm"]), 195.)
        self.assertIn("NONCONCURRENT", witness["basis"])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")

    def test_missing_spectral_step_keeps_scope_blocked_without_assessing_corners(self):
        args = self._spectral_args()
        rows = args["source"]["column_axial"]["force_source"]["rowsets"]["127"]
        for value in rows.values():
            if isinstance(value, list):
                value.pop()
        rows["NumberResults"] = 1
        owner = Mock()
        result = _evaluate_spectral_bounding_corners(**args, cap_solver=owner)
        owner.assess.assert_not_called()
        self.assertEqual(result["status"], "SPECTRAL_BOUNDING_INPUT_OR_COVERAGE_BLOCKED")
        self.assertIsNone(result["governing_corner"])


def _force(uid="C", sta=0., combo="Q", v2=500., v3=50., *, elm=None, elm_sta=None, step="Single Value"):
    return (uid, sta, elm or uid + "-1", sta if elm_sta is None else elm_sta, combo,
            step, 0., -100., v2, v3, 0., -20., 40.)


def _ve_args(rows=None, *, uid="C", combos=("Q",)):
    def joint(end, direction):
        return {"target_end": end, "direction": direction, "engineer_selected_scwb": {
            "cases": [{"output_case": combo, "target_column_capacity_knm": 300.} for combo in combos]}}
    return dict(uid=uid, col_frame={"axes_global": [[0, 0, 1], [1, 0, 0], [0, 1, 0]]}, ln_m=3.,
                scwb_joints=[joint(e, d) for e in ("I", "J") for d in ("X", "Y")],
                stations=[], static_combos=list(combos), rowset=_rowset(rows if rows is not None else [_force(uid)]),
                section=None, use_engineer=True, vr_lookup=lambda *args: (600., 300.))


class CapacityShearDemandFloorTests(unittest.TestCase):
    def test_initial_ve_is_floored_by_vd_with_native_governing_cut(self):
        axes = _compute_capacity_shear_axes(**_ve_args([
            _force(sta=0., v2=100.), _force(sta=1.5, v2=-500., elm="C-2", elm_sta=0.)]))
        case = axes["V2"]["cases"][0]
        self.assertEqual(case["ve_unreduced_kn"], 280.)  # (1.4*300 + 1.4*300)/3
        self.assertEqual((case["vd_floor_kn"], case["ve_scwb_scenario_kn"]), (500., 500.))
        self.assertAlmostEqual(case["utilization_ts500"], 5 / 6)
        self.assertEqual(case["vd_governing_cut"], {"member_id": "C", "combination": "Q",
            "object_station_m": 1.5, "analysis_element_id": "C-2", "element_station_m": 0.,
            "step_type": "Single Value", "step_number": 0., "shear_axis": "V2", "signed_shear_kn": -500.})
        self.assertEqual(axes["V3"]["max_ve_scwb_scenario_kn"], 280.)
        self.assertNotIn("revised_vd_floor_kn", case)

    def test_floor_threshold_negative_shear_and_observed_zero(self):
        for vd, expected in ((0., 280.), (279.999, 280.), (280., 280.), (-280., 280.), (-500., 500.)):
            with self.subTest(vd=vd):
                case = _compute_capacity_shear_axes(**_ve_args([_force(v2=vd)]))["V2"]["cases"][0]
                self.assertEqual(case["ve_scwb_scenario_kn"], expected)
                self.assertEqual(case["vd_floor_kn"], abs(vd))
                self.assertEqual(case["status"], "CAPACITY_SHEAR_CASE_CALCULATED_NOT_PROVEN")

    def test_revised_native_demands_change_vd_without_scaling_end_capacity(self):
        source, _, _, _, _ = two_columns()
        rows = [_force("C1", sta=x, v2=400., v3=40.) for x in (0., 1.5, 3.)]
        source["column_axial"]["force_source"]["rowsets"]["C1"] = _rowset(rows)
        original = deepcopy(source)
        revision = build_demand_revision(source, [{"story": "Zemin", "direction": "X", "combination": "Q",
            "status": "QUALIFIED_REFERENCE", "factor": 1.25, "eligible_member_ids": ["C1"]}], input_sha="fixture")
        args = _ve_args(rows, uid="C1")
        initial = _compute_capacity_shear_axes(**args)["V2"]["cases"][0]
        revised = _compute_capacity_shear_axes(**args, demand_revision=revision)["V2"]["cases"][0]
        self.assertEqual((initial["ve_unreduced_kn"], revised["ve_unreduced_kn"]), (280., 280.))
        self.assertEqual((initial["vd_floor_kn"], revised["vd_floor_kn"]), (400., 500.))
        self.assertEqual(revised["ve_scwb_scenario_kn"], 500.)
        self.assertEqual(revised["revised_vd_floor_kn"], 500.)
        self.assertEqual(revised["alpha_demand_revision_sha256"], revision["sha256"])
        self.assertEqual(source, original)

    def test_missing_required_combination_is_retained_and_nulls_complete_axis(self):
        axes = _compute_capacity_shear_axes(**_ve_args(combos=("Q", "Q_MISSING")))
        for axis in axes.values():
            self.assertEqual([c["combination"] for c in axis["cases"]], ["Q", "Q_MISSING"])
            missing = axis["cases"][1]
            self.assertIn("VD_REQUIRED_COMBINATION_MISSING", missing["reason_codes"])
            self.assertIsNone(missing["ve_scwb_scenario_kn"])
            self.assertIsNone(axis["max_utilization_ts500"])
            self.assertIsNone(axis["max_ve_scwb_scenario_kn"])
            self.assertEqual(axis["unresolved_combinations"], ["Q_MISSING"])

    def test_missing_one_element_side_cut_is_not_replaced_by_same_object_station(self):
        rows = [_force(sta=1.5, combo=c, elm="C-1", elm_sta=1.5) for c in ("Q", "E")]
        rows.append(_force(sta=1.5, combo="E", elm="C-2", elm_sta=0.))
        axes = _compute_capacity_shear_axes(**_ve_args(rows, combos=("Q", "E")))
        case = axes["V2"]["cases"][0]
        self.assertIn("VD_REQUIRED_NATIVE_CUT_MISSING", case["reason_codes"])
        self.assertEqual(case["vd_missing_cuts"], [{"object_station_m": 1.5,
            "analysis_element_id": "C-2", "element_station_m": 0.}])
        self.assertIsNone(axes["V2"]["max_utilization_ts500"])

    def test_unsigned_step_cannot_supply_a_static_vd_floor(self):
        axes = _compute_capacity_shear_axes(**_ve_args([_force(step="Max")]))
        self.assertIn("VD_STATIC_SIGNED_STEP_REQUIRED", axes["V2"]["reason_codes"])
        self.assertIsNone(axes["V2"]["cases"][0]["vd_floor_kn"])

    def test_invalid_native_shear_does_not_fall_back_to_favorable_station(self):
        args = _ve_args([_force(v2=float("nan"))])
        args["stations"] = [{"combination": "Q", "v2_kn": 0., "v3_kn": 0.}]
        axes = _compute_capacity_shear_axes(**args)
        self.assertIsNone(axes["V2"]["max_utilization_ts500"])
        self.assertTrue(any(r.startswith("VD_FORCE_SOURCE_UNRESOLVED:") for r in axes["V2"]["reason_codes"]))

    def test_missing_or_nonfinite_projected_vd_stays_unresolved(self):
        for value in (None, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                args = _ve_args()
                args["rowset"] = None
                args["stations"] = [{"combination": "Q", "v2_kn": value, "v3_kn": 50.}]
                result = _compute_capacity_shear_axes(**args)["V2"]
                self.assertIn("VD_SHEAR_VALUE_MISSING_OR_INVALID", result["reason_codes"])
                self.assertIsNone(result["max_utilization_ts500"])

    def test_missing_end_moment_is_retained_instead_of_dropping_the_case(self):
        args = _ve_args()
        args["scwb_joints"][0]["engineer_selected_scwb"]["cases"] = []
        result = _compute_capacity_shear_axes(**args)["V2"]
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("CAPACITY_SHEAR_END_MOMENT_UNRESOLVED", result["reason_codes"])
        self.assertIsNone(result["max_utilization_ts500"])

    def test_partial_ve_cannot_satisfy_alpha_or_r14_consumers(self):
        axes = _compute_capacity_shear_axes(**_ve_args(combos=("Q", "Q_MISSING")))
        detail = {"engineer_column_selection": {"selected": {"label": "fixture"}},
                  "column_transverse_and_shear": {"engineer_capacity_shear_ve": {"axes": axes}}}
        local = {"magnified_selected_pmm": {"status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN",
                 "global_beta_ii_factor": 1., "evaluated_row_count": 1, "expected_row_count": 1,
                 "resolved_row_count": 1, "max_utilization": .1}}
        feasibility = _feasibility({"dependencies": {"members": {"C": {}}},
            "r10": {"per_member": {"C": detail}}, "r08": {"per_member": {"C": local}},
            "required_signed_combinations": ["Q", "Q_MISSING"]})
        self.assertEqual(feasibility["status"], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")
        closure = _evaluate_single_r14_column(uid="C", axial={}, axial_col={}, pmm_col=None,
            r08_global=None, r08_local_col=local, beam_by_id={}, r10_det=detail, story_alpha=None)
        self.assertIn("COLUMN_SHEAR_UTILIZATION_MISSING_OR_INVALID:V2", closure["open_gates"])
        self.assertIn("COLUMN_SHEAR_UTILIZATION_MISSING_OR_INVALID:V3", closure["open_gates"])


if __name__ == "__main__":
    unittest.main()
