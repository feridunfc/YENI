"""Independent calculation/contract tests for explicitly adopted second-order inputs.

These public synthetic fixtures exercise the existing PMM and TS 500 owners.
They are not an original-building replay or engineering approval.
"""
from copy import deepcopy
from dataclasses import asdict
import math
import unittest
from unittest.mock import patch

from tbdy_next.column_engine.section_capacity import Material, Section, perimeter, solver
from tbdy_next.column_engine.native_archive import BankError
from tbdy_next.column_engine.ts500_column import (
    adopted_magnification_factors, member_magnification_coefficient, moment_magnification_factors,
)
from tbdy_next.engineering.column_clear_length import FACE_BASIS, WALL_COUPLED
from tbdy_next.engineering.column_effective_length import reference_end_ratios, resolve_adopted_frame_k
from tbdy_next.engineering.column_pmm import evaluate_column_pmm
from tbdy_next.engineering.column_pmm_section import MECHANICAL
from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
from tbdy_next.engineering.column_r10_live import SelectedColumnCage
from tbdy_next.engineering.design_scenario import _digest, _source_data
from tbdy_next.engineering.gravity_order_pair import SCHEMA as PAIR_SCHEMA, normalize_gravity_order_pair
from tbdy_next.vs05_d4_source_authority import COMBOS, SUMMARY
from test_r03_analysis_setup import capture_table
from tbdy_next.engineering.second_order_basis import (
    ACCEPTANCE_GATE, NONSWAY_POLICY, ROLE, SCHEMA, SWAY_POLICY, normalize_second_order_basis,
)
from test_r08_local_live import _r08_local_fixture
from test_r10_live import _rowset


def adopted_fixture(*, spectral=False, sway=False, k=2.0, rm=1.0, ei_method="TS500_7_20", nd=5000.):
    source, geometry, axial, _ = _r08_local_fixture()
    names = ["G_STATIC"] + (["E_SPECTRAL"] if spectral else [])
    rows = [("127", x, "127-1", x, names[0], "Single Value", 0., -nd, 0., 0., 0., -20., 30.) for x in (0., 3.8)]
    if spectral:
        rows += [("127", x, "127-1", x, names[1], step, 0., n, 0., 0., 0., m2, m3)
                 for x in (0., 3.8) for step, n, m2, m3 in (("Min", -nd-500, -10., -20.), ("Max", -nd+500, 10., 20.))]
    source["column_axial"]["force_source"]["rowsets"]["127"] = _rowset(rows)
    axial["combination_plan"] = {"source": "ASSIGNED_DESIGN", "blockers": [], "combinations": [
        {"name": n, "force_semantics": "STATIC_SIGNED_VECTOR" if n == names[0] else "SCALAR_COMPONENT_ENVELOPE"}
        for n in names], "design_assignment": {"groups": {"gravity": [names[0]], "ductile": names[1:]}}}
    axial["columns"][0]["combination_checks"] = [{"combination": n, "status": "WITHIN_LIMIT"} for n in names]
    pmm = evaluate_column_pmm(source, geometry, axial)
    bars, _, _ = perimeter(800, 800, 40, 10, 16, n2=9, n3=9)
    section = Section(800, 800, bars, Material(35, 35/1.5, 420/1.15))
    selection = {"member_id": "127", "selected": {"label": "32Phi16"}}
    source["column_selection"] = {}
    candidate_sha = _digest({"selection": selection, "section": asdict(section)})
    cage = SelectedColumnCage(selection, section, candidate_sha256=candidate_sha)
    r10 = {"member_id": "127", "engineer_column_selection": selection,
           "physical_clear_lengths": {"per_member": {"127": {"member_id": "127", "status": FACE_BASIS, "physical_length_m": 3.8}}}}
    basis = {"schema": SCHEMA, "basis_id": "SYNTHETIC-ADOPTED-SECOND-ORDER", "basis_role": ROLE,
        "engineering_approval": "NOT_GRANTED", "source_data_sha256": _digest(_source_data(source)),
        "source_analysis_order": "FIRST_ORDER", "source_order_reference": "Synthetic first-order fixture; no solver-log approval",
        "global_factor_policy": SWAY_POLICY if sway else NONSWAY_POLICY,
        "global_factor_reference": "Synthetic separate local/global policy; no engineering approval",
        "members": {"127": {"combinations": names, "applicability": "TS500_7_6_2_CONSTANT_SECTION_AND_AXIAL_FORCE",
            "decision_reference": "Synthetic constant rectangle and compression scenario",
            "axes": {axis: {"k": k, "creep_ratio_rm": rm, "ei_method": ei_method,
                "sway": "SWAY_PERMITTED" if sway else "SWAY_PREVENTED", "cm_policy": "UNITY",
                "eq729_length_reading": "EFFECTIVE_LENGTH" if sway else "NOT_APPLICABLE",
                "decision_reference": "Synthetic independently checked end restraint/stiffness scenario",
                "story_aggregates": {n: {"nd_kn": 20000., "nk_kn": 100000.,
                                         "reference": "Synthetic complete story aggregates"} for n in names} if sway else {}}
                for axis in ("M2", "M3")}}}}
    source["second_order_basis"] = basis
    global_record = {"status": "NUMERIC_PRECHECK_UNAPPROVED", "expected_story_direction_count": 2,
        "evaluated_story_direction_count": 2, "missing_story_direction": [],
        "direction_results": {d: {"within_reference_limit_candidate": True, "beta_ii_candidate": 1.} for d in ("X", "Y")}}
    return dict(source=source, geometry=geometry, axial=axial, pmm=pmm, global_pdelta=global_record,
                r10_live=r10, selected_cages={"127": cage})


def independent_euler(*, k, rm, method="TS500_7_20"):
    """Hand geometry: 32Phi16, bar centrelines at +/-342mm, 85.5mm steps."""
    area_bar = math.pi * 16**2 / 4
    steel_i = area_bar * (18 * 342**2 + 2 * sum((-342 + j*85.5)**2 for j in range(1, 8)))
    ec, concrete_i = 3250*math.sqrt(35)+14000, 800**4/12
    ei = ((.2*ec*concrete_i + 200000*steel_i) if method == "TS500_7_20" else .4*ec*concrete_i) / (1+rm)
    return math.pi**2 * ei / (k*3800)**2 / 1000


class AdoptedSecondOrderCalculationTests(unittest.TestCase):
    def test_variable_axial_gate_uses_signed_pmm_even_without_order_log_or_weight_data(self):
        args = adopted_fixture()
        source = args["source"]
        source["column_axial"]["force_source"]["rowsets"]["127"]["P"][1] += 200.0
        source["second_order_basis"]["source_data_sha256"] = _digest(_source_data(source))
        args["pmm"] = evaluate_column_pmm(source, args["geometry"], args["axial"])
        result = project_column_r08_local_live(**args)
        self.assertEqual(result["status"], "ADOPTED_SECOND_ORDER_CALCULATED_NOT_PROVEN")
        self.assertEqual(result["gravity_axial_balance"]["status"], "GRAVITY_AXIAL_BALANCE_UNBOUND")
        self.assertNotIn("archived_solver_log_sha256", result)
        self.assertIn("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED", result["open_gates"])

    def test_matched_gravity_pair_uses_same_section_at_unmagnified_second_order_vector(self):
        args, raw = self._gravity_pair_fixture()
        source = args["source"]
        result = project_column_r08_local_live(**args)
        compared = result["gravity_order_pair"]
        self.assertEqual(compared["status"], "GRAVITY_PAIR_COMPARED")
        self.assertEqual(compared["cut_counts"], {"expected": 2, "evaluated": 2, "failed": 0, "unresolved": 0})
        self.assertFalse(compared["elastic_stiffness_matches_ts500"])
        self.assertEqual(compared["local_p_delta_mesh_convergence"], "UNVERIFIED")
        expected = solver(args["selected_cages"]["127"].section).assess(5000e3, -300e6, 350e6)["utilization"]
        self.assertAlmostEqual(compared["governing"]["utilization"], expected)
        self.assertEqual(result["magnified_selected_pmm"], project_column_r08_local_live(
            **{**args, "source": {key: value for key, value in source.items() if key != "gravity_order_pair"}}
        )["magnified_selected_pmm"])

        raw["force_source"]["rowsets"]["127"]["M2"][0] += 1.0
        mismatch = project_column_r08_local_live(**args)["gravity_order_pair"]
        self.assertEqual(mismatch["status"], "GRAVITY_PAIR_CONTROL_MISMATCH")
        self.assertNotIn("second_order_pmm", mismatch["rows"][0])

    def test_gravity_pair_axial_failure_remains_visible_alongside_healthy_cut(self):
        args, raw = self._gravity_pair_fixture()
        rowset = raw["force_source"]["rowsets"]["127"]
        rowset["P"][1] = -1e6  # The first P–Delta cut exceeds the section axial domain.
        compared = project_column_r08_local_live(**args)["gravity_order_pair"]
        self.assertEqual(compared["control_status"], "MATCHED")
        self.assertEqual(compared["status"], "GRAVITY_PAIR_PMM_FAILURE")
        self.assertEqual(compared["cut_counts"], {"expected": 2, "evaluated": 2, "failed": 1, "unresolved": 0})
        self.assertEqual(compared["rows"][0]["second_pmm_status"], "OUTSIDE_SCENARIO_AXIAL_RANGE")
        self.assertEqual(compared["rows"][0]["second_pmm_reason"], "SECTION_MODEL_AXIAL_LIMIT")
        self.assertIsNotNone(compared["rows"][1]["second_pmm_utilization"])
        self.assertNotIn("governing", compared)

    @staticmethod
    def _gravity_pair_fixture(*, sway=False):
        args = adopted_fixture(sway=sway)
        source = args["source"]
        patterns, static = "Load Pattern Definitions", "Load Case Definitions - Linear Static"
        source["vs04_basis_probe"] = {"table_reads": {
            SUMMARY: capture_table(SUMMARY, ["Name", "Type", "GUID"], [("DEAD", "Linear Static", "g")]),
            COMBOS: capture_table(COMBOS, ["Name", "Type", "LoadName", "SF", "GUID"], [
                ("G_STATIC", "Linear Add", "DEAD", "1.4", "combo-guid"),
            ]),
            static: capture_table(static, ["Name", "LoadType", "LoadName", "SF"], [("DEAD", "Load", "DT", "1")]),
            patterns: capture_table(patterns, ["Name", "Type", "SelfWtMult"], [("DT", "Dead", "1")]),
        }}
        section_summary = "Frame Section Property Definitions - Summary"
        source["geometry_capture"]["tables"]["SECTION_SUMMARY"] = capture_table(
            section_summary, ["Name", "Material"], [("Column_80x80", "C35/45")])
        mechanical = source["column_axial"]["pmm_section_source"]["table_reads"][MECHANICAL]
        mechanical["rows"].append({"Material": "C35/45", "E1": "34000000"})
        mechanical["row_count"] += 1
        native_sha = _digest(_source_data(source))
        source["second_order_basis"]["source_data_sha256"] = native_sha

        before = {"cases": {"F": False, "P": False}, "combos": {"G_STATIC": True}}
        pair_rows = [("127", x, "127-1", x, name, "Step", 1., -5000., 0., 0., 0., m2, m3)
                     for x in (0., 3.8) for name, m2, m3 in (("F", -20., 30.), ("P", -300., 350.))]
        raw = {
            "schema": PAIR_SCHEMA, "source_data_sha256": native_sha, "section_name": "Column_80x80",
            "cases": {"G_STATIC": {"first": "F", "second": "P", "patterns": {"DT": 1.4}}},
            "force_source": {"schema": "tbdy.next.etabs-frame-force-source.v1", "units_code": 6, "errors": {},
                "api": "Results.FrameForce", "item_type": "ObjectElm", "rowsets": {"127": _rowset(pair_rows)},
                "output_selection_before": before, "output_selection_after": before,
                "output_selection_during": {"cases": {"F": True, "P": True}, "combos": {"G_STATIC": False}}},
            "frame_section_modifiers": [1., 1., 1., 1., .7, .7, 1., 1.],
            "frame_object_modifiers": {"127": [1.] * 8}, "mesh": {"127": ["127-1"]},
        }
        source["gravity_order_pair"] = normalize_gravity_order_pair(raw, source_data_sha256=native_sha)
        return args, raw

    def test_refined_mesh_preserves_new_identities_and_uses_its_first_order_vectors(self):
        args, raw = self._gravity_pair_fixture(sway=True)
        uid, name = "127", "G_STATIC"
        source = args["source"]
        physical = args["r10_live"]["physical_clear_lengths"]["per_member"][uid]
        physical.update(faces={"I": {"joint_id": "1044", "top_z_m": 0.0},
                               "J": {"joint_id": "412", "soffit_z_m": 3.8}},
                        end_cuts={"I": [uid, 0., "127-1", 0.], "J": [uid, 3.8, "127-1", 3.8]})
        source["vs06_b1_geometry_source"] = {"table_reads": {"Point Object Connectivity": {"rows": [
            {"UniqueName": "1044", "X": 0, "Y": 0, "Z": 0}, {"UniqueName": "412", "X": 0, "Y": 0, "Z": 4.5},
        ]}}}
        native_sha = _digest(_source_data(source))
        source["second_order_basis"]["source_data_sha256"] = raw["source_data_sha256"] = native_sha
        target_ei = independent_euler(k=2., rm=1.) * 1000 * (7600 ** 2) / math.pi ** 2
        factor = target_ei / (34000 * (800 ** 4 / 12) * .7)
        levels = []
        for divisions in (2, 4, 8):
            nodes = ["1044", *(f"J{divisions}-{j}" for j in range(1, divisions)), "412"]
            z = [*(3.8 * j / divisions for j in range(divisions)), 4.5]
            mesh, forces = [], []
            for i in range(divisions):
                element, a, b = f"E{divisions}-{i}", z[i], z[i + 1]
                mesh.append({"element": element, "i_joint": nodes[i], "j_joint": nodes[i + 1],
                             "i_xyz": [0., 0., a], "j_xyz": [0., 0., b]})
                last = min(b, 3.8)
                for station in (a, (a + last) / 2, last):
                    for case, n, m2 in (("F", -950., -140.), ("P", -1100., -160.)):
                        forces.append((uid, station, element, station - a, case, "Step", 1., n, 0., 0., 0., m2, 100.))
            levels.append({"divisions": divisions, "model_sha256": str(divisions) * 64, "mesh": {uid: mesh},
                "frame_object_modifiers": {uid: [1., 1., 1., 1., factor, factor, 1., 1.]},
                "force_source": {**raw["force_source"], "rowsets": {uid: _rowset(forces)}},
                "joint_displacements": {uid: {"P": {node: [0., 0., 0.] for node in nodes}}},
                "story_inputs": {uid: {axis: {"k": 2., "story_aggregates": {name: {"nd_kn": 20000., "nk_kn": 100000.}}}
                                       for axis in ("M2", "M3")}},
            })
        raw["refined_levels"] = levels
        source["gravity_order_pair"] = normalize_gravity_order_pair(raw, source_data_sha256=native_sha)
        compared = project_column_r08_local_live(**args)["gravity_order_pair"]
        self.assertEqual(compared["status"], "GRAVITY_PAIR_COMPARED")
        refined = compared["refinement"]
        self.assertEqual(refined["status"], "WITHIN_NUMERICAL_TOLERANCE")
        last = refined["levels"][-1]
        self.assertEqual(last["ts500_status"], "REVISED_FIRST_ORDER_VECTORS_AND_STORY_INPUTS_CONSUMED")
        self.assertEqual(last["cut_counts"]["evaluated"], 24)
        self.assertGreater(last["additional_physical_cuts"], 0)
        self.assertEqual({row["analysis_element_id"] for row in last["rows"]}, {f"E8-{i}" for i in range(8)})
        self.assertEqual(last["rows"][0]["control"]["p_kn"], -950.)
        self.assertNotEqual(last["rows"][0]["ts500_m2_knm"], compared["rows"][0]["ts500_m2_knm"])
        levels[-1]["force_source"]["rowsets"][uid]["ElmSta"][0] = 0.1
        failed = project_column_r08_local_live(**args)["gravity_order_pair"]["refinement"]
        self.assertEqual(failed["status"], "UNVERIFIED")
        self.assertEqual(failed["levels"][-1]["reason"], "GRAVITY_REFINEMENT_PHYSICAL_STATION_MISMATCH")

    def test_selected_static_demand_consumes_k_and_rm_before_euler_and_floor_before_beta(self):
        args = adopted_fixture()
        before = deepcopy(args["source"])
        result = project_column_r08_local_live(**args)
        nk = independent_euler(k=2., rm=1.)
        beta = 1/(1-1.3*5000/nk)
        for axis in ("M2", "M3"):
            self.assertAlmostEqual(result["stiffness_and_euler"][axis]["selected_nk_kn"], nk, places=9)
        row = result["magnified_selected_pmm"]["rows"][0]
        self.assertEqual((row["first_order_m2_knm"], row["first_order_m2_design_knm"]), (-20., -195.))
        self.assertAlmostEqual(row["magnified_m2_design_knm"], -195*beta, places=9)
        self.assertAlmostEqual(row["magnified_m3_design_knm"], 195*beta, places=9)
        self.assertEqual(row["adopted_axis_factors"]["M2"]["cm"], 1.)
        self.assertEqual(result["second_order_basis_status"], "ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN")
        self.assertEqual(result["second_order_basis_application"]["selected_cage_sha256"], args["selected_cages"]["127"].candidate_sha256)
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertIn(ACCEPTANCE_GATE, result["open_gates"])
        self.assertIn("ACTUAL_ANALYSIS_ORDER_UNVERIFIED", result["open_gates"])
        self.assertEqual(args["source"], before)

    def test_tbdY_global_factor_is_applied_once_only_on_nonsway_route(self):
        args = adopted_fixture()
        for direction, beta in (("X", 1.2), ("Y", 1.1)):
            args["global_pdelta"]["direction_results"][direction]["beta_ii_candidate"] = beta
        result = project_column_r08_local_live(**args)
        expected = -195/(1-1.3*5000/independent_euler(k=2, rm=1))*1.2
        row = result["magnified_selected_pmm"]["rows"][0]
        self.assertAlmostEqual(row["magnified_m2_design_knm"], expected, places=9)
        self.assertEqual(row["global_beta_ii_applied"], 1.2)

    def test_missing_or_nonunit_tbdY_blocks_sway_without_implicit_global_factor_one(self):
        for defect in ("missing_factor", "missing_direction_count", "nonunit", "outside_limit"):
            with self.subTest(defect=defect):
                args = adopted_fixture(sway=True)
                if defect == "missing_factor":
                    args["global_pdelta"]["direction_results"]["Y"].pop("beta_ii_candidate")
                elif defect == "missing_direction_count":
                    args["global_pdelta"].pop("evaluated_story_direction_count")
                elif defect == "outside_limit":
                    args["global_pdelta"]["direction_results"]["X"]["within_reference_limit_candidate"] = False
                else:
                    args["global_pdelta"]["direction_results"]["X"]["beta_ii_candidate"] = 1.01
                result = project_column_r08_local_live(**args)
                self.assertEqual(result["execution_status"], "NOT_RUN")
                self.assertNotIn("magnified_selected_pmm", result)
                self.assertTrue(any("TBDY" in gate for gate in result["open_gates"]))

    def test_wall_coupling_and_missing_physical_length_cannot_adopt_native_offset_span(self):
        for kind in ("missing", "coupled"):
            with self.subTest(kind=kind):
                args = adopted_fixture()
                proof = args["r10_live"]["physical_clear_lengths"]["per_member"]["127"]
                if kind == "missing":
                    proof["status"] = "MODEL_CLEAR_LENGTH_UNRESOLVED"
                else:
                    proof["status"] = WALL_COUPLED
                result = project_column_r08_local_live(**args)
                self.assertEqual(result["execution_status"], "NOT_RUN")
                self.assertIsNone(result["stiffness_and_euler"])
                self.assertNotIn("magnified_selected_pmm", result)
                self.assertNotEqual(result["second_order_basis_status"], "ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN")

    def test_declared_720_never_falls_back_to_721_when_steel_stiffness_input_missing(self):
        args = adopted_fixture()
        args["pmm"]["section_evidence"].pop("es_mpa")
        result = project_column_r08_local_live(**args)
        self.assertIsNone(result["stiffness_and_euler"]["M2"]["selected_nk_kn"])
        self.assertEqual(result["magnified_selected_pmm"]["status"], "SECOND_ORDER_BUCKLING_OR_BLOCKED")
        self.assertEqual(result["second_order_basis_status"], "ADOPTED_CALCULATION_BASIS_DEMAND_INCOMPLETE")

    def test_missing_combination_or_spectral_cm_context_remains_explicitly_incomplete(self):
        args = adopted_fixture(spectral=True)
        args["source"]["second_order_basis"]["members"]["127"]["combinations"].remove("E_SPECTRAL")
        missing = project_column_r08_local_live(**args)
        self.assertEqual(missing["execution_status"], "NOT_RUN")
        self.assertIn("SECOND_ORDER_BASIS_REQUIRED_COMBINATION_SCOPE_MISMATCH:127", missing["open_gates"])
        args = adopted_fixture(spectral=True)
        args["source"]["second_order_basis"]["members"]["127"]["axes"]["M2"]["cm_policy"] = "SIGNED_END_RATIO"
        unresolved = project_column_r08_local_live(**args)
        self.assertIn("ADOPTED_SPECTRAL_CM_REQUIRES_UNITY:M2", unresolved["spectral_envelope_pmm_scenario"]["reason_codes"])
        self.assertEqual(unresolved["second_order_basis_status"], "ADOPTED_CALCULATION_BASIS_DEMAND_INCOMPLETE")

    def test_known_second_order_metadata_cannot_be_magnified_again(self):
        args = adopted_fixture()
        args["pmm"]["actual_second_order_applied"] = True
        result = project_column_r08_local_live(**args)
        self.assertEqual(result["execution_status"], "NOT_RUN")
        self.assertIn("ADOPTED_SECOND_ORDER_SOURCE_ORDER_CONFLICT_NO_DOUBLE_APPLICATION", result["open_gates"])

    def test_current_frame_reference_k_is_recomputed_before_euler_and_stale_selection_blocks(self):
        # alpha_i=alpha_j=1 -> no-sway k=.8, independently from Eq7.14.
        args = adopted_fixture(k=.8)
        ends = {side: {"basis": "FRAME_SECTION_REFERENCE", "joint_id": side,
                       "alpha_web": 1., "alpha_flange_comparison": .5} for side in ("I", "J")}
        for axis in ("M2", "M3"):
            args["source"]["second_order_basis"]["members"]["127"]["axes"][axis]["k_source"] = {
                "method": "FRAME_END_RATIOS", "section": "alpha_web"}
        with patch("tbdy_next.engineering.column_r08_local_live.reference_end_ratios", return_value={"127": {a: ends for a in ("M2", "M3")}}):
            actual = project_column_r08_local_live(**args)
            self.assertAlmostEqual(actual["stiffness_and_euler"]["M2"]["selected_nk_kn"], independent_euler(k=.8, rm=1), places=8)
            self.assertAlmostEqual(actual["stiffness_and_euler"]["M2"]["k_source_resolution"]["computed_k"], .8, places=15)
            args["source"]["second_order_basis"]["members"]["127"]["axes"]["M2"]["k"] = 1.2
            stale = project_column_r08_local_live(**args)
        self.assertEqual(stale["execution_status"], "NOT_RUN")
        self.assertIn("ADOPTED_K_VALUE_CONFLICTS_WITH_CURRENT_FRAME_REFERENCE", stale["open_gates"])

    def test_frame_k_selection_does_not_invent_mat_rotation_or_missing_end(self):
        cfg = {"k": .8, "sway": "SWAY_PREVENTED", "k_source": {"method": "FRAME_END_RATIOS", "section": "alpha_web"}}
        for ends in ({}, {"I": {"basis": "MAT_ROTATIONAL_STIFFNESS_UNBOUND"},
                         "J": {"basis": "FRAME_SECTION_REFERENCE", "alpha_web": 1.}}):
            with self.subTest(ends=ends), self.assertRaisesRegex(ValueError, "TWO_BOUND_FRAME_END_RATIOS"):
                resolve_adopted_frame_k(cfg, ends)

    def test_native_two_beam_end_geometry_drives_existing_k_owner(self):
        from tbdy_next.column_engine.native_archive import digest
        from tbdy_next.etabs_geometry import FRAME_INSERTION, SLAB_PROPERTIES
        from test_column_clear_length import fixture, project

        source, tables, scope = fixture()
        geometry = source["geometry_capture"]["tables"]
        sections = geometry["RECTANGULAR_SECTIONS"]
        sections["fields"].append("Material")
        sections["field_metadata"]["field_keys"].append("Material")
        sections["rows"][0]["Material"] = "C35"
        fa = geometry["FRAME_ASSIGNMENTS"]
        fa["fields"].append("Length")
        fa["field_metadata"]["field_keys"].append("Length")
        fa["field_metadata"]["units_by_field"]["Length"] = "m"
        fa["rows"][0]["Length"], fa["rows"][1]["Length"] = "4.5", "3"
        fa["rows"].append(dict(zip(fa["fields"], ("B0", "Base", "B0", "Beam", "Rect", "None", "3"))))
        fa["row_count"] = len(fa["rows"])
        bc = geometry["BEAM_CONNECTIVITY"]
        bc["rows"].append(dict(zip(bc["fields"], ("B0", "Base", "P0", "P3"))))
        bc["row_count"] = len(bc["rows"])
        b1 = source["vs06_b1_geometry_source"]
        points = b1["table_reads"]["Point Object Connectivity"]
        points["rows"].append(dict(zip(points["fields"], ("P3", "Base", "3", "0", "-4.5"))))
        points["row_count"] = len(points["rows"])
        joints = tables["Objects and Elements - Joints"]
        joints["rows"].append(dict(zip(joints["fields"], ("P3", "P3", "Joint", "Base", "3", "0", "-4.5"))))
        joints["row_count"] = len(joints["rows"])
        ins = tables[FRAME_INSERTION]
        ins["rows"].append(dict(zip(ins["fields"], ("B0", "Base", "B0", "8 (Top Center)", "No", "No"))))
        ins["row_count"] = len(ins["rows"])
        tables[SLAB_PROPERTIES]["rows"][0].update(PropType="Slab", Thickness=".2")
        b1["payload_sha256"] = digest({k: v for k, v in b1.items() if k != "payload_sha256"})
        physical = project(source, scope)["per_member"]
        self.assertEqual(physical["C"]["status"], FACE_BASIS)
        axes = reference_end_ratios(source, physical)
        # Same rectangular section, column length4.5m, beam length3m with0.5Ig:
        # alpha = (Ig/4.5)/(0.5Ig/3) = 4/3, k = .7 + .05*(8/3).
        expected_k = .7 + .05*(8/3)
        cfg = {"k": expected_k, "sway": "SWAY_PREVENTED",
               "k_source": {"method": "FRAME_END_RATIOS", "section": "alpha_web"}}
        k, witness = resolve_adopted_frame_k(cfg, axes["C"]["M3"])
        self.assertAlmostEqual(witness["alpha_i"], 4/3, places=12)
        self.assertAlmostEqual(witness["alpha_j"], 4/3, places=12)
        self.assertAlmostEqual(k, expected_k, places=14)
        sections["rows"][0].pop("Material")
        self.assertEqual(reference_end_ratios(source, physical), {})


class AdoptedCoefficientOwnerTests(unittest.TestCase):
    def case(self, **updates):
        inputs = dict(nd_kn=5000., nk_kn=100000., free_length_ln_mm=4000., k=2., radius_mm=100.,
            fck_mpa=35., area_mm2=640000., sway="SWAY_PERMITTED", cm_policy="UNITY",
            eq729_length_reading="EFFECTIVE_LENGTH", story_nd_kn=20000., story_nk_kn=100000.)
        inputs.update(updates)
        return adopted_magnification_factors(**inputs)

    def test_selected_reading_changes_maximum_vs_product_without_approving_ambiguity(self):
        product = self.case()
        maximum = self.case(eq729_length_reading="FREE_LENGTH")
        local, story = 1/(1-1.3*.05), 1/(1-1.3*.2)
        self.assertAlmostEqual(product["final_factor"], local*story, places=12)
        self.assertAlmostEqual(maximum["final_factor"], max(local, story), places=12)
        self.assertEqual(product["eq729_selected_branch"], "PRODUCT")
        self.assertEqual(maximum["eq729_selected_branch"], "MAXIMUM")
        self.assertFalse(product["eq729_comparison"]["product_authorized"])
        self.assertEqual(product["engineering_approval"], "NOT_GRANTED")

    def test_eq729_strict_boundary_and_approximate_method_limit(self):
        boundary = self.case(nd_kn=5600., free_length_ln_mm=7000., k=1., eq729_length_reading="FREE_LENGTH")
        above = self.case(nd_kn=5600., free_length_ln_mm=math.nextafter(7000., math.inf), k=1., eq729_length_reading="FREE_LENGTH")
        self.assertEqual(boundary["eq729_selected_branch"], "MAXIMUM")
        self.assertEqual(above["eq729_selected_branch"], "PRODUCT")
        unsupported = self.case(k=3.)
        self.assertEqual(unsupported["status"], "BLOCKED")
        self.assertEqual(unsupported["reason"], "TS500_APPROXIMATE_METHOD_SLENDERNESS_LIMIT_EXCEEDED")
        self.assertIsNone(unsupported["final_factor"])

    def test_story_7_28_boundary_and_noncompression_are_not_local_buckling_defaults(self):
        boundary = self.case(story_nd_kn=45000.)
        self.assertAlmostEqual(boundary["beta_story"], 1/(1-1.3*.45), places=12)
        above = self.case(story_nd_kn=45000.001)
        self.assertEqual(above["reason"], "TS500_7_28_STORY_LIMIT_EXCEEDED")
        self.assertIsNone(above["final_factor"])
        tension = self.case(nd_kn=-100.)
        self.assertEqual(tension["beta"], 1.)
        self.assertAlmostEqual(tension["final_factor"], 1/(1-1.3*.2), places=12)


class MemberMagnificationScalarTests(unittest.TestCase):
    def test_printed_cm_clamp_and_independent_positive_coefficient(self):
        self.assertEqual(member_magnification_coefficient(nd_kn=85.13, nk_kn=26790.32, cm=.41), 1.)
        # 0.7/(1 - 1.3*0.6) = 35/11, independently reduced as a rational number.
        self.assertAlmostEqual(member_magnification_coefficient(nd_kn=600., nk_kn=1000., cm=.7), 35/11, places=14)
        self.assertEqual(member_magnification_coefficient(nd_kn=-100., nk_kn=1000., cm=1., allow_noncompression=True), 1.)

    def test_nonpositive_denominator_and_original_wrapper_guards(self):
        for nd in (1000., 1000.001):
            with self.subTest(nd=nd):
                self.assertIsNone(member_magnification_coefficient(nd_kn=nd, nk_kn=1300., cm=1.))
                result = moment_magnification_factors(nd_kn=nd, nk_kn=1300., sway="SWAY_PREVENTED",
                    horizontal_load_between_ends=True)
                self.assertEqual(result["reason"], "TS500_7_24_NONPOSITIVE_DENOMINATOR")
                self.assertIsNone(result["beta"])
        self.assertEqual(member_magnification_coefficient(nd_kn=90., nk_kn=130., cm=.4), 4.)
        for update in ({"nd_kn": 0}, {"nd_kn": -1}, {"nk_kn": 0}, {"cm": .399}, {"cm": 1.001}, {"cm": math.nan}):
            with self.subTest(update=update), self.assertRaises(BankError):
                member_magnification_coefficient(**({"nd_kn": 600., "nk_kn": 1000., "cm": .7} | update))
        with self.assertRaisesRegex(BankError, "TRANSVERSE_LOAD_BASIS_REQUIRED"):
            moment_magnification_factors(nd_kn=600., nk_kn=1000., sway="SWAY_PREVENTED")
        with self.assertRaisesRegex(BankError, "STORY_AGGREGATES_CONFLICT"):
            moment_magnification_factors(nd_kn=600., nk_kn=1000., sway="SWAY_PREVENTED", story_nd_kn=1.)

    def test_existing_production_wrapper_calls_scalar_owner(self):
        with patch("tbdy_next.column_engine.ts500_column.member_magnification_coefficient",
                   wraps=member_magnification_coefficient) as owner:
            result = moment_magnification_factors(nd_kn=600., nk_kn=1000., sway="SWAY_PREVENTED",
                horizontal_load_between_ends=True)
        owner.assert_called_once_with(nd_kn=600., nk_kn=1000., cm=1, allow_noncompression=False)
        # 1/(1 - 1.3*0.6) = 50/11; status and final-factor branch are unchanged.
        self.assertAlmostEqual(result["beta"], 50/11, places=14)
        self.assertEqual(result["final_factor"], result["beta"])
        self.assertEqual(result["status"], "COEFFICIENTS_ONLY")


class AdoptedBasisContractTests(unittest.TestCase):
    def test_invalid_inputs_and_unsupported_decisions_are_rejected(self):
        mutations = (
            lambda d: d.update(source_analysis_order="SECOND_ORDER"),
            lambda d: d.update(engineering_approval="APPROVED"),
            lambda d: d.update(global_factor_policy=[]),
            lambda d: d["members"]["127"]["axes"]["M2"].update(k=True),
            lambda d: d["members"]["127"]["axes"]["M2"].update(k=0),
            lambda d: d["members"]["127"]["axes"]["M2"].update(creep_ratio_rm=float("nan")),
            lambda d: d["members"]["127"]["axes"]["M2"].update(creep_ratio_rm=1.01),
            lambda d: d["members"]["127"]["axes"]["M2"].update(ei_method=[]),
            lambda d: d["members"]["127"]["axes"]["M2"].update(decision_reference=""),
            lambda d: d["members"]["127"]["axes"].pop("M3"),
            lambda d: d["members"]["127"]["axes"]["M2"].update(eq729_length_reading="EFFECTIVE_LENGTH"),
            lambda d: d["members"]["127"]["axes"]["M2"].update(sway="SWAY_PERMITTED"),
        )
        for mutation in mutations:
            args = adopted_fixture()
            doc = args["source"]["second_order_basis"]
            mutation(doc)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                normalize_second_order_basis(doc, source_data_sha256=_digest(_source_data(args["source"])))

    def test_source_change_and_unknown_member_reject_basis_but_policy_change_has_own_revision(self):
        args = adopted_fixture()
        args["source"]["capture_metadata"] = {"model_filename": "different-model.edb"}
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"):
            project_column_r08_local_live(**args)
        args = adopted_fixture()
        doc = args["source"]["second_order_basis"]
        doc["members"]["UNKNOWN"] = doc["members"].pop("127")
        with self.assertRaisesRegex(ValueError, "OUTSIDE_PHYSICAL_ROSTER"):
            project_column_r08_local_live(**args)

    def test_observed_rows_do_not_replace_expected_combination_scope(self):
        args = adopted_fixture()
        args["axial"].pop("combination_plan")
        result = project_column_r08_local_live(**args)
        self.assertEqual(result["execution_status"], "NOT_RUN")
        self.assertIn("ADOPTED_SECOND_ORDER_EXPECTED_COMBINATION_PLAN_MISSING", result["open_gates"])


class AdoptedBasisDemandRevisionTests(unittest.TestCase):
    def test_axis_specific_k_rm_and_method_change_governing_demands_and_basis_revision(self):
        args = adopted_fixture()
        first = project_column_r08_local_live(**args)
        cfg = args["source"]["second_order_basis"]["members"]["127"]["axes"]["M3"]
        cfg.update(k=1.5, creep_ratio_rm=.5, ei_method="TS500_7_21")
        second = project_column_r08_local_live(**args)
        nk3 = independent_euler(k=1.5, rm=.5, method="TS500_7_21")
        self.assertAlmostEqual(second["stiffness_and_euler"]["M3"]["selected_nk_kn"], nk3, places=9)
        a, b = first["magnified_selected_pmm"]["rows"][0], second["magnified_selected_pmm"]["rows"][0]
        self.assertEqual(a["magnified_m2_design_knm"], b["magnified_m2_design_knm"])
        self.assertLess(b["magnified_m3_design_knm"], a["magnified_m3_design_knm"])
        self.assertAlmostEqual(b["magnified_m3_design_knm"], 195/(1-1.3*5000/nk3), places=9)
        self.assertNotEqual(first["second_order_basis_sha256"], second["second_order_basis_sha256"])

    def test_spectral_corners_use_same_selected_k_rm_and_adopted_sway_story_factor(self):
        args = adopted_fixture(spectral=True, sway=True)
        result = project_column_r08_local_live(**args)
        box = result["spectral_envelope_pmm_scenario"]
        corner = box["governing_corner"]
        self.assertTrue(box["coverage_complete"])
        self.assertEqual(box["evaluated_corner_count"], 16)
        factor = max(1/(1-1.3*corner["nd_kn"]/independent_euler(k=2., rm=1.)), 1/(1-1.3*.2))
        self.assertAlmostEqual(abs(corner["magnified_m2_design_knm"]), corner["nd_kn"]*.039*factor, places=9)
        self.assertEqual(corner["adopted_axis_factors"]["M2"]["eq729_selected_branch"], "MAXIMUM")
        self.assertEqual(corner["global_beta_ii_applied"], 1.)
        self.assertEqual(result["second_order_basis_status"], "ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN")


if __name__ == "__main__":
    unittest.main()
