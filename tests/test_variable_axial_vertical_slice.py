"""Actual production pipeline over explicit variable-N source fixtures.

No calculated stage, resistance, selected cage or closure output is replaced.
The source is generated offline; none of these tests claims original C29 or
live ETABS verification, TS500 applicability or engineering acceptance.
"""
from argparse import Namespace
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from hashlib import sha256
from http.server import ThreadingHTTPServer
import io
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from tbdy_next.engineering.cli_adapter import run_cli
from tbdy_next.column_engine.column_kinematics import COMPONENTS, COORDINATE_CONTRACT
from tbdy_next.engineering.column_pmm_section import MECHANICAL
from tbdy_next.engineering.design_scenario import _digest, _source_data
from tbdy_next.engineering.gravity_order_pair import QUALIFIED_SCHEMA, normalize_gravity_order_pair
from tbdy_next.engineering.gravity_story_basis import FRAME_FORCE
from tbdy_next.engineering.second_order_basis import SWAY_POLICY
from tbdy_next.engineering.pipeline_snapshot import compare_runs, read_snapshot
from tbdy_next.reporting import build_complete_report, build_printable_html
from tbdy_next.web import make_handler
from vertical_slice_fixture import digest, table
from variable_axial_slice_fixture import (
    COMBINATIONS, CUTS, TOP_COMPRESSION_KN, bind_source, source_and_request,
)
from test_r10_live import _rowset


APPLIED = "ADOPTED_AXIAL_IDEALIZATION_APPLIED_NOT_PROVEN"
PENDING = "ADOPTED_AXIAL_IDEALIZATION_ENGINEERING_ACCEPTANCE_PENDING"
CONTRIBUTOR_MODIFIER_SCHEMA = "tbdy.next.gravity-story-contributor-modifiers.v1"


def completion_fixture(*, spring_scale=1.):
    """Build signed demands, source geometry, and an analytical parabolic bow."""
    from test_gravity_story_basis import add_bound_story_basis

    raw, request = source_and_request()
    source = json.loads(raw)
    source["column_axial"]["pmm_section_source"]["table_reads"][MECHANICAL] = table(
        MECHANICAL, "Material E1 UnitWeight", [("B420C", "200000000", "78.5"), ("C35/45", "34000000", "25")],
        {"E1": "kN/m2", "UnitWeight": "kN/m3"})
    uid, name, length = "C1", "G", 2.5
    first, second = "SYN_GRAV_F", "SYN_GRAV_P"
    cases = {name: {"first": first, "second": second, "patterns": {"LC_DL": 1.}}}
    before = {"cases": {first: False, second: False}, "combos": {name: True}}
    force = {"schema": "tbdy.next.etabs-frame-force-source.v1", "api": "Results.FrameForce",
             "item_type": "ObjectElm", "units_code": 6, "errors": {}, "output_selection_before": before,
             "output_selection_after": before, "output_selection_during": {
                 "cases": {first: True, second: True}, "combos": {name: False}}}
    sec_mods = [1., 1., 1., 1., .7, .7, 1., 1.]
    inertia = 800. ** 4 / 12.
    steel = math.pi * 16. ** 2 / 4 * (18 * 340. ** 2 + 2 * sum((-340. + j * 85.) ** 2 for j in range(1, 8)))
    ei = .2 * (3250. * math.sqrt(35.) + 14000.) * inertia + 200000. * steel
    modifier = ei / (34000. * inertia * .7)
    levels = []
    for divisions in (2, 4, 8):
        positions = [*(length * j / divisions for j in range(divisions)), 3.]
        joints = ["P0", *(f"M{divisions}_{i}" for i in range(1, divisions)), "P1"]
        elements, rows = [], []
        for index, (a, b) in enumerate(zip(positions, positions[1:])):
            element = f"M{divisions}_E{index}"
            elements.append({"element": element, "i_joint": joints[index], "j_joint": joints[index + 1],
                             "i_xyz": [0., 0., a], "j_xyz": [0., 0., b]})
            face = min(b, length)
            for cut in (a, (a + face) / 2, face):
                rows.extend((uid, cut, element, cut - a, case, "Step", 1., p, 0., 0., 0., m2, m3)
                            for case, p, m2, m3 in ((first, -2780. + 16. * cut, -150., 170.), (second, -2810. + 16. * cut, -153., 174.)))
        model = sha256(f"manufactured model {divisions} spring {spring_scale}".encode()).hexdigest()
        generation = sha256(f"manufactured solve {divisions} spring {spring_scale}".encode()).hexdigest()
        scaling = .0004
        motion = {node: dict(zip(COMPONENTS, (scaling * z * (3. - z), 0., 0., 0., scaling * (3. - 2. * z), 0.)))
                  for node, z in zip(joints, positions)}
        sections = {r["element"]: {"axes_global": [[0., 0., 1.], [1., 0., 0.], [0., 1., 0.]],
                     "offsets_m": [0., .5 if i == divisions - 1 else 0.], "rigid_end_factor": 0.,
                     "kinematics_basis": "PRISMATIC_CENTROIDAL_UNRELEASED_GLOBAL_JOINTS",
                     "ei_knm2": [ei / 1e9, ei / 1e9], "ga_kn": [100000., 100000.]}
                    for i, r in enumerate(elements)}
        level = {"divisions": divisions, "model_sha256": model, "analysis_generation": generation,
                 "mesh": {uid: elements}, "frame_object_modifiers": {uid: [1., 1., 1., 1., modifier, modifier, 1., 1.]},
                 "force_source": {**force, "rowsets": {uid: _rowset(rows)},
                                  "model_sha256": model, "analysis_generation": generation},
                 "joint_displacements": {uid: {second: {node: [item[k] for k in COMPONENTS[:3]]
                                                       for node, item in motion.items()}}},
                 "story_inputs": {}, "kinematics": {
                     "schema": "tbdy.next.gravity-frame-kinematics.v1", "model_sha256": model,
                     "analysis_generation": generation, "case_step": ["Step", 1.],
                     "coordinate_contract": COORDINATE_CONTRACT,
                     "units": {"translational": "m", "rotational": "rad", "stiffness": "kN,m"},
                     "translation_error_m": 0., "rotation_error_rad": 0.,
                     "members": {uid: {"joints": {second: motion}, "elements": sections}}}}
        story = add_bound_story_basis(source, level, uid, cases, ln_mm=2500., ei_nmm2=ei, story_id="S1")
        for axis in story["columns"][uid]["axes"].values():
            for side in ("i", "j"):
                axis["restraint"][side]["k_knm_per_rad"] *= spring_scale
        levels.append(level)
    geom = source["vs06_b1_geometry_source"]
    geom["payload_sha256"] = digest({key: value for key, value in geom.items() if key != "payload_sha256"})
    basis = request["second_order_basis"]
    basis["global_factor_policy"] = SWAY_POLICY
    basis["global_factor_reference"] = "Manufactured source with non-overlapping global policy"
    for axis in (axis for member in basis["members"].values() for axis in member["axes"].values()):
        axis.update(sway="SWAY_PERMITTED", eq729_length_reading="EFFECTIVE_LENGTH",
                    story_aggregates={combo: {"nd_kn": 500., "nk_kn": 100000., "reference": "Analytical fixture"}
                                      for combo in COMBINATIONS})
    raw, request = bind_source(source, request)
    base_rows = [(uid, z, "C1-elm", z, case, "Step", 1., -(TOP_COMPRESSION_KN[uid] + 16. * (length - z)), 0., 0., 0., m2, m3)
                 for z in CUTS for case, m2, m3 in ((first, 30., 30.), (second, 33., 33.))]
    request["scenario_id"] = "qualified-refined-gravity-contract"
    request["gravity_order_pair"] = {
        "schema": QUALIFIED_SCHEMA, "source_data_sha256": _digest(_source_data(source)), "section_name": "C80",
        "cases": cases, "force_source": {**force, "rowsets": {uid: _rowset(base_rows)}},
        "frame_section_modifiers": sec_mods, "frame_object_modifiers": {uid: [1.] * 8},
        "mesh": {uid: ["C1-elm"]}, "refined_levels": levels}
    return raw, request


def completion_with_story_contributor(*, modifier_scale=.5):
    """Add a native-shaped parallel column outside the paired C1 mesh scope."""
    raw, request = completion_fixture()
    source = json.loads(raw)
    renames = {"C1": "C3", "C1-elm": "C3-elm", "P0": "CP0", "P1": "CP1"}

    def copy_rows(record, field, wanted):
        for row in deepcopy(record["rows"]):
            if row[field] in wanted:
                record["rows"].append({key: renames.get(value, value) for key, value in row.items()})
        record["row_count"] = len(record["rows"])

    geometry = source["geometry_capture"]["tables"]
    for name in ("FRAME_ASSIGNMENTS", "SECTION_ASSIGNMENTS", "COLUMN_CONNECTIVITY"):
        copy_rows(geometry[name], "UniqueName", {"C1"})
    for branch in ("vs05_delta_source", "vs06_b1_geometry_source"):
        table = source[branch]["table_reads"]["Point Object Connectivity"]
        copy_rows(table, "UniqueName", {"P0", "P1"})
        for row in table["rows"]:
            if row["UniqueName"] in ("CP0", "CP1"):
                row["X"] = "10"
    axial = source["column_axial"]
    native = axial["r10_source"]["table_reads"]
    for name, field in (
        ("Objects and Elements - Frames", "ObjName"),
        ("Frame Assignments - Output Stations", "UniqueName"),
        ("Frame Assignments - End Length Offsets", "UniqueName"),
        ("Frame Assignments - Insertion Point", "UniqueName"),
    ):
        copy_rows(native[name], field, {"C1"})
    joints = native["Objects and Elements - Joints"]
    copy_rows(joints, "ElmName", {"P0", "P1"})
    for row in joints["rows"]:
        if row["ElmName"] in ("CP0", "CP1"):
            row["GlobalX"] = "10"
    for force in (axial["force_source"], axial["demand_support"]["force_source"]):
        rowset = force["rowsets"]["C3"] = deepcopy(force["rowsets"]["C1"])
        rowset["Obj"] = ["C3"] * rowset["NumberResults"]
        rowset["Elm"] = ["C3-elm"] * rowset["NumberResults"]
    request["second_order_basis"]["members"]["C3"] = deepcopy(request["second_order_basis"]["members"]["C1"])

    pair = request["gravity_order_pair"]
    for level in pair["refined_levels"]:
        model = sha256((level["model_sha256"] + f"|C3|{modifier_scale}").encode()).hexdigest()
        generation = sha256((model + "|manufactured solve").encode()).hexdigest()
        for record in (level, level["force_source"], level["kinematics"], level["story_basis_source"]):
            record.update(model_sha256=model, analysis_generation=generation)
        block = level["story_basis_source"]
        target = level["frame_object_modifiers"]["C1"]
        contributor = list(target)
        contributor[4] *= modifier_scale
        contributor[5] *= modifier_scale
        block["contributor_modifiers"] = {
            "schema": CONTRIBUTOR_MODIFIER_SCHEMA, "model_sha256": model, "analysis_generation": generation,
            "modifiers": {"C1": list(target), "C3": contributor},
        }
        column = block["columns"]["C3"] = deepcopy(block["columns"]["C1"])
        for axis, index in (("M2", 4), ("M3", 5)):
            info = column["axes"][axis]
            info.update(section_modifier=.7, object_modifier=contributor[index])
            ei = info["ec_mpa"] * info["i_mm4"] * .7 * contributor[index]
            spring = math.pi / 2 * (ei / 1e9) / (column["ln_mm"] / 1000)
            for side, joint in (("i", "CP0"), ("j", "CP1")):
                info["restraint"][side].update(joint_id=joint, k_knm_per_rad=spring)
        section = block["story_cuts"]["S1"]
        first = pair["cases"]["G"]["first"]
        section["forces"].append({"kind": "COLUMN", "object_id": "C3", "element_id": "C3-elm",
            "case": first, "step_type": "Step", "step_number": 1., "z_m": section["z_m"],
            "representation": FRAME_FORCE, "vector_kn": [-5000., 0., 0.]})
        section["equilibrium"][first]["upper_external_applied_kn"] += 5000.
    for branch in ("vs05_delta_source", "vs06_b1_geometry_source"):
        record = source[branch]
        record["payload_sha256"] = digest({key: value for key, value in record.items() if key != "payload_sha256"})
    raw, request = bind_source(source, request)
    request["gravity_order_pair"]["source_data_sha256"] = _digest(_source_data(source))
    return raw, request


class VariableAxialVerticalSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.raw, cls.request = source_and_request()
        cls.summary, cls.snapshot = cls.calculate(cls.raw, cls.request, "self-weight-adopted")
        cls.directory = Path(cls.summary["run_dir"])
        cls.stages = cls.snapshot["results"]
        cls.default_raw, cls.default_request = source_and_request(adopt_axial_idealization=False)
        cls.default_summary, cls.default_snapshot = cls.calculate(
            cls.default_raw, cls.default_request, "self-weight-default")

    @classmethod
    def calculate(cls, raw, request, name):
        source_path, request_path = cls.root / (name + ".source"), cls.root / (name + ".json")
        source_path.write_bytes(raw)
        request_path.write_text(json.dumps(request), encoding="utf-8")
        args = Namespace(action="run-pipeline", source=source_path, design_scenario=request_path,
                         out=cls.root, case="Modal", compare_run=None,
                         beam_selection=None, column_selection=None)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = run_cli(args)
        if code != 0:
            raise AssertionError(stream.getvalue())
        summary = json.loads(stream.getvalue())
        return summary, read_snapshot(Path(summary["run_dir"]), input_sha=summary["input_sha256"])

    def test_same_variable_source_default_blocks_and_explicit_input_method_is_consumed(self):
        self.assertEqual(self.raw, self.default_raw)
        source = json.loads(self.raw)
        self.assertEqual(source["example_context"]["classification"], "CONTRACT_FIXTURE")
        self.assertEqual(source["example_context"]["origin"], "GENERATED_OFFLINE_NOT_ETABS")
        default = self.default_snapshot["results"]
        self.assertEqual(default["r14_closure"]["numerically_closed_count"], 0)
        self.assertEqual(self.stages["r14_closure"]["numerically_closed_count"], 2)
        self.assertEqual(self.stages["r14_closure"]["expected_column_count"], 2)
        scope = self.stages["report_evidence"]["column_pmm_expected_instances"]
        self.assertEqual(scope["expected_member_combination_count"], 10)
        self.assertEqual(scope["numerically_complete_signed_pair_count"], 10)
        self.assertTrue(scope["independent_cut_census_proven"])
        self.assertEqual(sum(r["configured_cut_coverage"]["matched_count"] for r in scope["instances"]), 30)
        for uid, top in TOP_COMPRESSION_KN.items():
            old = default["r08_local_slenderness"]["per_member"][uid]
            self.assertIn("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED", old["open_gates"])
            self.assertEqual(old["gravity_axial_balance"]["combinations"]["G"]["status"],
                             "SELF_WEIGHT_BALANCED_AT_SIGNED_CUTS")
            local = self.stages["r08_local_slenderness"]["per_member"][uid]
            evidence, applied = local["axial_idealization_evidence"], local["axial_idealization_application"]
            self.assertEqual(evidence["status"], "SELF_WEIGHT_NMAX_INPUTS_ELIGIBLE")
            self.assertEqual(applied["status"], APPLIED)
            self.assertEqual(set(applied["combinations"]), set(COMBINATIONS))
            self.assertIn(PENDING, local["open_gates"])
            self.assertNotIn("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED", local["open_gates"])
            for record in (evidence, applied):
                self.assertFalse(record["original_constant_axial_clause_satisfied"])
                self.assertFalse(record["conservative_bound_proven"])
                self.assertEqual(record["engineering_approval"], "NOT_GRANTED")
            for name, case in evidence["combinations"].items():
                self.assertEqual((case["expected_cut_count"], case["evaluated_cut_count"]), (3, 3))
                self.assertEqual((case["nmin_kn"], case["nmax_kn"]), (top, top + 40.))
                self.assertEqual([cut["object_station_m"] for cut in case["cuts"]], list(CUTS))
                self.assertEqual([cut["nd_kn"] for cut in case["cuts"]], [top + 40., top + 20., top])
                self.assertTrue(all(cut["native_p_kn"] == -cut["nd_kn"] for cut in case["cuts"]))
                self.assertTrue(all(cut["superposition_residual_kn"] == 0. for cut in case["cuts"]))
            # Independent dimensions: .8*.8*25*1 =16 kN/m, at1.25m intervals.
            for interval in local["gravity_axial_balance"]["combinations"]["G"]["intervals"]:
                self.assertEqual(interval["predicted_self_weight_change_kn"], 20.)
                self.assertEqual(interval["native_axial_change_kn"], 20.)
                self.assertEqual(interval["superposition_residual_kn"], 0.)
        for stage in (default, self.stages):
            self.assertEqual(stage["r14_closure"]["engineering_release"], "NOT_READY")
        self.assertNotEqual(compare_runs(Path(self.default_summary["run_dir"]), self.directory)["status"], "IDENTICAL")

    def test_qualified_revised_model_consumes_story_and_six_dof_in_sealed_pipeline(self):
        raw, request = completion_fixture()
        summary, snapshot = self.calculate(raw, request, "qualified-refined")
        run = Path(summary["run_dir"])
        r08 = snapshot["results"]["r08_local_slenderness"]["per_member"]["C1"]["gravity_order_pair"]["refinement"]
        r14 = next(row for row in snapshot["results"]["r14_closure"]["columns"] if row["member_id"] == "C1")
        closure = r14["pillars"]["second_order_selected_pmm"]["gravity_refinement"]
        finest = r08["levels"][-1]
        self.assertEqual(finest["ts500_status"], "REVISED_FIRST_ORDER_VECTORS_AND_STORY_INPUTS_CONSUMED", finest)
        self.assertEqual(len(finest["revised_axis_factors"]), 2)
        self.assertTrue(all(factor["final_factor"] > 1 for factor in finest["revised_axis_factors"]))
        self.assertEqual(closure["method_comparison"]["matched_physical_cuts"], 3)
        choices = [c for row in r08["method_comparison"]["rows"] for c in row["refined_cuts"]]
        self.assertEqual(len(choices), 4)
        self.assertTrue(all(c["revised_ts500_pmm"] is not None for c in choices))
        span = r08["changes"][-1]["full_span_deformation_comparison"]
        self.assertTrue(span["within_tolerance"], span)
        self.assertAlmostEqual(span["cases"]["G"]["after_peak"]["value_mm"], .9, delta=.001)
        self.assertAlmostEqual(span["cases"]["G"]["after_peak"]["station_m"], 1.5, delta=.025)
        self.assertEqual(snapshot["results"]["r14_closure"]["engineering_release"], "NOT_READY")
        with patch("tbdy_next.engineering.gravity_deformation.recover_level", side_effect=AssertionError("recompute")), \
             patch("tbdy_next.engineering.gravity_pair_refinement._refined_ts500", side_effect=AssertionError("recompute")):
            report = build_complete_report(self.root, run.name)
            html = build_printable_html(report)
            self.assertEqual(report["run_id"], run.name)
            self.assertIn("Revised TS 500 coefficients", html)
            self.assertIn("Full-span deformation", html)

    def test_revised_restraint_changes_design_and_a_real_limit_failure_is_retained(self):
        finest_levels = {}
        for scale in (1., 2., .01):
            raw, request = completion_fixture(spring_scale=scale)
            _, snapshot = self.calculate(raw, request, f"revised-springs-{scale}")
            local = snapshot["results"]["r08_local_slenderness"]["per_member"]["C1"]
            finest_levels[scale] = local["gravity_order_pair"]["refinement"]["levels"][-1]
        original, stiffer, failed = (finest_levels[scale] for scale in (1., 2., .01))
        self.assertLess(stiffer["revised_axis_factors"][0]["k"], original["revised_axis_factors"][0]["k"])
        self.assertLess(stiffer["revised_axis_factors"][0]["final_factor"],
                        original["revised_axis_factors"][0]["final_factor"])
        self.assertLess(abs(stiffer["rows"][0]["ts500_m2_knm"]), abs(original["rows"][0]["ts500_m2_knm"]))
        self.assertEqual(stiffer["rows"][0]["second"], original["rows"][0]["second"])
        self.assertEqual(failed["ts500_status"], "REVISED_TS500_STABILITY_FAILURE")
        self.assertEqual(len(failed["rows"]), len(original["rows"]))
        for axis in failed["revised_axis_factors"]:
            self.assertEqual(axis["reason"], "TS500_APPROXIMATE_METHOD_SLENDERNESS_LIMIT_EXCEEDED")
            self.assertLess(axis["member_denominator"], 0.)
            self.assertIsNone(axis["final_factor"])
        self.assertTrue(all("ts500_m2_knm" not in row for row in failed["rows"]))

    def test_nonpaired_story_column_modifiers_are_consumed_without_expanding_paired_mesh(self):
        results = {}
        for scale in (.5, 1.):
            raw, request = completion_with_story_contributor(modifier_scale=scale)
            pair = request["gravity_order_pair"]
            self.assertEqual(set(pair["force_source"]["rowsets"]), {"C1"})
            for level in pair["refined_levels"]:
                self.assertEqual(set(level["mesh"]), {"C1"})
                self.assertEqual(set(level["frame_object_modifiers"]), {"C1"})
            _, snapshot = self.calculate(raw, request, f"separate-story-modifiers-{scale}")
            self.assertEqual(snapshot["results"]["r14_closure"]["expected_column_count"], 3)
            local = snapshot["results"]["r08_local_slenderness"]["per_member"]["C1"]
            finest = local["gravity_order_pair"]["refinement"]["levels"][-1]
            results[scale] = finest
            self.assertEqual(finest["ts500_status"], "REVISED_FIRST_ORDER_VECTORS_AND_STORY_INPUTS_CONSUMED")
            basis = finest["revised_story_basis"]
            self.assertEqual(basis["status"], "REVISED_STORY_BASIS_CALCULATED")
            self.assertEqual(basis["contributor_modifier_source"]["expected_column_ids"], ["C1", "C3"])
            self.assertEqual(basis["cases"]["G"]["supported_compression_kn"], 7780.)
            for factor in finest["revised_axis_factors"]:
                axis = factor["axis"]
                columns = {row["member_id"]: row for row in basis["axes"][axis]["contributors"]}
                self.assertEqual(set(columns), {"C1", "C3"})
                info = pair["refined_levels"][-1]["story_basis_source"]["columns"]["C3"]["axes"][axis]
                expected_ei = info["ec_mpa"] * (800.**4 / 12) * .7 * info["object_modifier"]
                # Independent symmetric-spring fixture gives K=2 and ln=2500 mm.
                expected_nk = math.pi**2 * expected_ei / 5000.**2 / 1000
                self.assertAlmostEqual(columns["C3"]["effective_ei_nmm2"] / expected_ei, 1., places=12)
                self.assertAlmostEqual(columns["C3"]["member_nk_kn"], expected_nk, places=8)
                story_nk = columns["C1"]["member_nk_kn"] + expected_nk
                expected_beta = 1. / (1. - 1.3 * 7780. / story_nk)
                self.assertAlmostEqual(factor["story_nk_kn"], story_nk, places=8)
                self.assertAlmostEqual(factor["final_factor"], expected_beta, places=12)
                field = "ts500_" + axis.lower() + "_knm"
                self.assertAlmostEqual(finest["rows"][0][field], (-150. if axis == "M2" else 170.) * expected_beta)
            self.assertTrue(all(row.get("ts500_utilization") is not None for row in finest["rows"]))
        self.assertLess(results[1.]["revised_axis_factors"][0]["final_factor"],
                        results[.5]["revised_axis_factors"][0]["final_factor"])
        self.assertLess(abs(results[1.]["rows"][0]["ts500_m2_knm"]),
                        abs(results[.5]["rows"][0]["ts500_m2_knm"]))
        invalid = deepcopy(pair)
        invalid["refined_levels"][-1]["frame_object_modifiers"]["C3"] = [1.] * 8
        with self.assertRaisesRegex(ValueError, "GRAVITY_PAIR_MEMBER_OR_STIFFNESS_SCOPE_UNVERIFIED"):
            normalize_gravity_order_pair(invalid, source_data_sha256=invalid["source_data_sha256"])

    def test_missing_or_stale_nonpaired_modifier_source_cannot_produce_story_factor(self):
        for defect, reason in (
            ("missing", "STORY_CONTRIBUTOR_MODIFIER_SCOPE_INCOMPLETE:C3"),
            ("stale", "STORY_CONTRIBUTOR_MODIFIER_MODEL_GENERATION_MISMATCH"),
        ):
            with self.subTest(defect=defect):
                raw, request = completion_with_story_contributor()
                capture = request["gravity_order_pair"]["refined_levels"][-1]["story_basis_source"]["contributor_modifiers"]
                if defect == "missing":
                    capture["modifiers"].pop("C3")
                else:
                    capture["analysis_generation"] = "f" * 64
                _, snapshot = self.calculate(raw, request, "invalid-story-modifiers-" + defect)
                local = snapshot["results"]["r08_local_slenderness"]["per_member"]["C1"]
                finest = local["gravity_order_pair"]["refinement"]["levels"][-1]
                basis = finest["revised_story_basis"]
                self.assertIn(reason, basis["reasons"])
                self.assertEqual(basis["story_inputs"], {})
                self.assertEqual(basis["cases"]["G"]["expected_count"], 2)
                self.assertEqual(len(finest["rows"]), 24)
                self.assertTrue(all(factor.get("final_factor") is None for factor in finest["revised_axis_factors"]))
                self.assertTrue(all("ts500_m2_knm" not in row for row in finest["rows"]))
                self.assertEqual(snapshot["results"]["r14_closure"]["engineering_release"], "NOT_READY")

    def test_independent_stiffness_beta_and_cut_local_demand_are_numerically_consumed(self):
        # Independent 9-by9 perimeter cage:32Phi16, cover40/tie12/bar radius8.
        # No production stiffness, magnification or eccentricity function is an oracle.
        bar_area = math.pi * 16. ** 2 / 4
        steel_inertia = bar_area * (18 * 340. ** 2 + 2 * sum((-340. + j * 85.) ** 2 for j in range(1, 8)))
        concrete_inertia = 800. ** 4 / 12
        ec = 3250. * math.sqrt(35.) + 14000.
        ei = .2 * ec * concrete_inertia + 200000. * steel_inertia
        nk = math.pi ** 2 * ei / 2500. ** 2 / 1000.
        eccentricity_m = (15. + .03 * 800.) / 1000.
        for uid, top in TOP_COMPRESSION_KN.items():
            selected = self.stages["r10_live"]["per_member"][uid]["engineer_column_selection"]["selected"]
            self.assertEqual((selected["bar_count"], selected["diameter_mm"],
                              selected["num_bars_2_dir"], selected["num_bars_3_dir"]), (32, 16, 9, 9))
            local = self.stages["r08_local_slenderness"]["per_member"][uid]
            coefficient_n = top + 40.
            beta = 1. / (1. - 1.3 * coefficient_n / nk)
            for axis in ("M2", "M3"):
                actual = local["stiffness_and_euler"][axis]
                self.assertAlmostEqual(actual["selected_is_mm4"] / steel_inertia, 1., places=12)
                self.assertAlmostEqual(actual["selected_ei_nmm2"] / ei, 1., places=12)
                self.assertAlmostEqual(actual["selected_nk_kn"] / nk, 1., places=12)
            mag = local["magnified_selected_pmm"]
            self.assertEqual((mag["expected_row_count"], mag["resolved_row_count"]), (15, 15))
            for row in mag["rows"]:
                actual_nd = top + 16. * (2.5 - row["object_station_m"])
                self.assertEqual(row["nd_kn"], actual_nd)
                self.assertEqual(row["coefficient_nd_kn"], coefficient_n)
                self.assertEqual(row["analysis_element_id"], uid + "-elm")
                self.assertEqual(row["global_beta_ii_applied"], 1.)
                for suffix in ("m2", "m3"):
                    first_order = abs(row["first_order_" + suffix + "_knm"])
                    expected_floor = max(first_order, actual_nd * eccentricity_m)
                    self.assertAlmostEqual(row["beta_" + suffix], beta, places=12)
                    self.assertAlmostEqual(abs(row["first_order_" + suffix + "_design_knm"]), expected_floor, places=10)
                    self.assertAlmostEqual(abs(row["magnified_" + suffix + "_design_knm"]), expected_floor * beta, places=10)
                self.assertGreater(row["moment_reserve_knm"], 0.)
                self.assertLess(row["utilization"], 1.)
            self.assertGreater(len({row["nd_kn"] for row in mag["rows"]}), 1)

    def test_actual_interior_scwb_capacity_shear_and_cages_complete_the_slice(self):
        self.assertEqual(self.stages["beam_r10"]["calculated_beam_count"], 4)
        r10 = self.stages["r10_live"]["per_member"]
        joints = [joint for joint in r10["C1"]["scwb_joints"] if joint["joint_id"] == "P1"]
        self.assertEqual({joint["direction"] for joint in joints}, {"X", "Y"})
        for joint in joints:
            result = joint["seismic_axial_interval_check"]
            self.assertEqual(result["status"], "SCWB_EQ_7_3_INTERVAL_SUFFICIENT")
            self.assertEqual((result["expected_checks"], result["evaluated_checks"]), (8, 8))
            for case in result["cases"]:
                for sway in case["sways"]:
                    self.assertGreater(sway["ratio_lower"], 1.)
                    self.assertAlmostEqual(sway["ratio_lower"], sway["column_sum_lower_knm"] / sway["required_sum_upper_knm"])
        for member in r10.values():
            shear = member["column_transverse_and_shear"]["engineer_capacity_shear_ve"]
            for axis in ("V2", "V3"):
                self.assertLess(shear["axes"][axis]["max_utilization_ts500"], 1.)
                self.assertLess(shear["axes"][axis]["max_utilization_zero_concrete"], 1.)
            self.assertTrue(member["engineer_column_selection"]["selected"]["selected_transverse"]["all_tbdy_checks_met"])
        iteration = self.stages["report_evidence"]["alpha_iteration"]
        self.assertEqual(iteration["status"], "ALTERNATIVE_NOT_REQUIRED")
        self.assertFalse(iteration["feedback_consumed"])

    def test_source_weight_revision_changes_nmax_beta_and_actual_design_moments(self):
        raw, request = source_and_request(unit_weight_kn_m3=30.)
        self.assertNotEqual(raw, self.raw)
        summary, snapshot = self.calculate(raw, request, "heavier-self-weight")
        self.assertEqual(snapshot["results"]["r14_closure"]["numerically_closed_count"], 2)
        for uid, top in TOP_COMPRESSION_KN.items():
            old = self.stages["r08_local_slenderness"]["per_member"][uid]
            new = snapshot["results"]["r08_local_slenderness"]["per_member"][uid]
            self.assertEqual(new["axial_idealization_application"]["combinations"]["G"]["nmax_kn"], top + 48.)
            # The cage revision also binds source identity; compare its actual
            # reinforcement geometry rather than assuming equal source hashes.
            old_cage = self.stages["r10_live"]["per_member"][uid]["engineer_column_selection"]["selected"]
            new_cage = snapshot["results"]["r10_live"]["per_member"][uid]["engineer_column_selection"]["selected"]
            for key in ("bar_count", "diameter_mm", "num_bars_2_dir", "num_bars_3_dir", "area_mm2"):
                self.assertEqual(new_cage[key], old_cage[key])
            self.assertNotEqual(new["second_order_basis_application"]["selected_cage_sha256"],
                                old["second_order_basis_application"]["selected_cage_sha256"])
            self.assertNotEqual(new["axial_idealization_application"]["eligibility_sha256"],
                                old["axial_idealization_application"]["eligibility_sha256"])
            self.assertEqual(new["stiffness_and_euler"]["M2"]["selected_nk_kn"],
                             old["stiffness_and_euler"]["M2"]["selected_nk_kn"])
            old_rows, new_rows = old["magnified_selected_pmm"]["rows"], new["magnified_selected_pmm"]["rows"]
            self.assertGreater(new_rows[0]["beta_m2"], old_rows[0]["beta_m2"])
            self.assertGreater(abs(new_rows[0]["magnified_m2_design_knm"]), abs(old_rows[0]["magnified_m2_design_knm"]))
            for interval in new["gravity_axial_balance"]["combinations"]["G"]["intervals"]:
                self.assertAlmostEqual(interval["predicted_self_weight_change_kn"], 24.)
        self.assertNotEqual(compare_runs(self.directory, Path(summary["run_dir"]))["status"], "IDENTICAL")

    def test_missing_primitive_cut_does_not_shrink_design_population_or_grant_method(self):
        source = json.loads(self.raw)
        rowset = source["column_axial"]["demand_support"]["force_source"]["rowsets"]["C1"]
        index = next(i for i in range(rowset["NumberResults"])
                     if rowset["LoadCase"][i] == "LC_DL" and rowset["ObjSta"][i] == 1.25)
        for value in rowset.values():
            if isinstance(value, list):
                value.pop(index)
        rowset["NumberResults"] -= 1
        raw, request = bind_source(source, self.request)
        _, snapshot = self.calculate(raw, request, "missing-primitive-cut")
        stages = snapshot["results"]
        scope = stages["report_evidence"]["column_pmm_expected_instances"]
        self.assertEqual(scope["expected_member_combination_count"], 10)
        self.assertEqual(sum(r["configured_cut_coverage"]["matched_count"] for r in scope["instances"]), 30)
        local = stages["r08_local_slenderness"]["per_member"]["C1"]
        self.assertEqual(local["axial_idealization_evidence"]["status"], "SELF_WEIGHT_NMAX_INPUTS_REJECTED")
        self.assertIn("AXIAL_IDEALIZATION_INPUTS_UNRESOLVED", local["open_gates"])
        self.assertIn("VARIABLE_AXIAL_SECOND_ORDER_METHOD_UNQUALIFIED", local["open_gates"])
        closed = {row["member_id"]: row for row in stages["r14_closure"]["columns"]}
        self.assertNotEqual(closed["C1"]["status"], "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES")
        self.assertEqual(stages["r14_closure"]["engineering_release"], "NOT_READY")

    def test_configured_cut_matching_accepts_one_ulp_but_rejects_shift_and_duplicates(self):
        for name, midpoint, duplicate, eligible in (
            ("one-ulp-cut", math.nextafter(1.25, math.inf), False, True),
            ("shifted-cut", 1.2501, False, False),
            ("duplicate-cut", 1.25, True, False),
            ("ambiguous-cut", math.nextafter(1.25, math.inf), True, False),
        ):
            with self.subTest(name=name):
                source = json.loads(self.raw)
                axial = source["column_axial"]
                for force in (axial["force_source"], axial["demand_support"]["force_source"]):
                    rowset = force["rowsets"]["C1"]
                    indices = [i for i, station in enumerate(rowset["ObjSta"]) if station == 1.25]
                    for index in indices:
                        if duplicate:
                            for field, values in rowset.items():
                                if isinstance(values, list):
                                    values.append(midpoint if field in ("ObjSta", "ElmSta") else values[index])
                        else:
                            rowset["ObjSta"][index] = rowset["ElmSta"][index] = midpoint
                    if duplicate:
                        rowset["NumberResults"] += len(indices)
                raw, request = bind_source(source, self.request)
                summary, snapshot = self.calculate(raw, request, name)
                stages = snapshot["results"]
                closure = stages["r14_closure"]
                self.assertEqual(summary["engineering_release"], "NOT_READY")
                if name == "duplicate-cut":
                    # The native force owner rejects exact full-key duplicates
                    # before selection or R14; no downstream closure is created.
                    self.assertIsNone(closure)
                    dependencies = summary["design_dependencies"]
                    self.assertEqual(dependencies["expected_column_count"], 2)
                    self.assertFalse(dependencies["members"]["C1"]["source_execution_allowed"])
                    self.assertIn("COLUMN_AXIAL_SOURCE_INVALID:FORCE_STATION_NEGATIVE_OR_FULL_KEY_DUPLICATE",
                                  dependencies["members"]["C1"]["reason_codes"])
                    continue
                self.assertEqual(closure["expected_column_count"], 2)
                self.assertEqual(closure["engineering_release"], "NOT_READY")
                members = {row["member_id"]: row for row in closure["columns"]}
                if eligible:
                    self.assertEqual(closure["numerically_closed_count"], 2)
                    local = stages["r08_local_slenderness"]["per_member"]["C1"]
                    evidence = local["axial_idealization_evidence"]
                    self.assertEqual(local["axial_idealization_application"]["status"], APPLIED)
                    self.assertEqual(evidence["physical_scope"]["configured_grid"]["cuts"][1]["object_station_m"], 1.25)
                    for case in evidence["combinations"].values():
                        self.assertEqual(case["cuts"][1]["object_station_m"], midpoint)
                        self.assertEqual(case["cuts"][1]["element_station_m"], midpoint)
                    native_cuts = {(row["combination"], row["object_station_m"], row["analysis_element_id"],
                                    row["element_station_m"])
                                   for case in evidence["combinations"].values() for row in case["cuts"]}
                    consumed_cuts = {(row["combination"], row["object_station_m"], row["analysis_element_id"],
                                      row["element_station_m"]) for row in local["magnified_selected_pmm"]["rows"]}
                    self.assertEqual(native_cuts, consumed_cuts)
                else:
                    self.assertNotEqual(members["C1"]["status"], "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES")

    def test_eligible_axial_method_does_not_hide_real_transverse_capacity_exceedance(self):
        request = deepcopy(self.request)
        request["column_selection"].update(tie_diameter_preference_mm=[10],
            stirrup_confinement_spacing_mm=90, stirrup_span_spacing_mm=90)
        _, snapshot = self.calculate(self.raw, request, "insufficient-transverse-design")
        stages = snapshot["results"]
        self.assertEqual(stages["r14_closure"]["numerically_closed_count"], 0)
        for uid in TOP_COMPRESSION_KN:
            self.assertEqual(stages["r08_local_slenderness"]["per_member"][uid]["axial_idealization_application"]["status"], APPLIED)
            shear = stages["r10_live"]["per_member"][uid]["column_transverse_and_shear"]["engineer_capacity_shear_ve"]
            self.assertGreater(shear["axes"]["V2"]["max_utilization_zero_concrete"], 1.)
        self.assertTrue(all("COLUMN_ZERO_CONCRETE_BRANCH_REVIEW_REQUIRED:V2" in row["open_gates"]
                            for row in stages["r14_closure"]["columns"]))
        # Exceeded conservative branch requires refinement; it is not relabelled
        # as a proven normative failure by this fixture.
        self.assertEqual(stages["r14_closure"]["engineering_release"], "NOT_READY")

    def test_normal_web_replay_and_report_use_same_recorded_idealization_without_owner_calls(self):
        def no_capture(*args, **kwargs):
            raise AssertionError("Offline example must not acquire ETABS")
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.root, live_capture=no_capture))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = "http://127.0.0.1:" + str(server.server_port)
            body = json.dumps({"base_run_id": self.directory.name, "design_scenario": self.request}).encode()
            with urlopen(Request(url + "/api/apply-rebar-selection", data=body,
                                 headers={"Content-Type": "application/json"}), timeout=30) as response:
                acknowledgement = json.load(response)
            directory = self.root / acknowledgement["run_id"]
            self.assertEqual(compare_runs(self.directory, directory)["status"], "IDENTICAL")
            owners = (
                "tbdy_next.engineering.pipeline.EnginePipelineRunner.run",
                "tbdy_next.engineering.column_r08_local_live.project_column_r08_local_live",
                "tbdy_next.engineering.column_r10_live.project_column_r10_live",
                "tbdy_next.engineering.column_axial_balance.project_self_weight_nmax_idealization",
                "tbdy_next.engineering.column_r14_closure.project_column_r14_and_r15_closure",
                "tbdy_next.engineering.rebar_selection.select_column_rebar",
            )
            with ExitStack() as stack:
                spies = [stack.enter_context(patch(owner, side_effect=AssertionError("Report-time calculation"))) for owner in owners]
                report = build_complete_report(self.root, directory.name)
                html = build_printable_html(report)
                self.assertEqual(report["example_context"]["classification"], "CONTRACT_FIXTURE")
                self.assertIn("SYNTHETIC CONTRACT FIXTURE — NO LIVE ETABS ANALYSIS", html)
                with urlopen(url + "/api/export-checks?run_id=" + directory.name, timeout=8) as response:
                    web_report = json.load(response)
                with urlopen(url + "/report/print?run_id=" + directory.name, timeout=8) as response:
                    web_html = response.read().decode()
            self.assertTrue(all(spy.call_count == 0 for spy in spies))
            self.assertEqual(report, web_report)
            self.assertEqual(html, web_html)
            heading = "Adopted self-weight axial idealization"
            self.assertTrue(heading in html, "Recorded axial idealization was not displayed")
            idealization_html = html.split(heading, 1)[1].split("<h3>", 1)[0]
            for text in ("SELF_WEIGHT_NMAX", "NOT_GRANTED", "2540", "1540",
                         "N used for coefficient", "Local N for section",
                         "conservatism and engineering acceptance are not established"):
                self.assertTrue(text in idealization_html, "Missing recorded idealization field: " + text)
            for uid in TOP_COMPRESSION_KN:
                self.assertEqual(report["r08_local_slenderness"]["per_member"][uid]["axial_idealization_application"],
                                 self.stages["r08_local_slenderness"]["per_member"][uid]["axial_idealization_application"])
            archived = json.loads((directory / "input.source").read_bytes())
            self.assertEqual(archived["column_axial"]["force_source"], json.loads(self.raw)["column_axial"]["force_source"])
            self.assertEqual((directory / "parent.source").read_bytes(), self.raw)
        finally:
            server.shutdown()
            thread.join(3)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
