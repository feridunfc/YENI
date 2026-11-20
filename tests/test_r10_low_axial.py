import unittest

from tbdy_next.column_engine.source_bank import FIELDS
from tbdy_next.engineering.column_r10_live import _assigned_seismic_combinations, _evaluate_scwb_at_joint_ends
from tbdy_next.engineering.column_r14_closure import _evaluate_single_r14_column
from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.mixed_demands import SCHEMA, SPECTRAL_METHOD
from tbdy_next.engineering.scwb_axial import joint_low_axial_decisions
from tbdy_next.reporting import _column_r10_html
from test_mixed_design_demands import mixed_fixture, table


class JointLowAxialTests(unittest.TestCase):
    def setUp(self):
        self.frames = {uid: {"frame_id": uid, "point_i": other, "point_j": "N"}
                       for uid, other in (("U", "TOP"), ("L", "BASE"))}
        self.frames["B"] = {"frame_id": "B", "axes_global": [[1, 0, 0], [0, 0, 1], [0, -1, 0]]}
        self.points = {"TOP": [0, 0, 8], "N": [0, 0, 4], "BASE": [0, 0, 0]}
        self.adjacency = {"N": [{"frame_id": uid, "end": "J", "type": "Column"} for uid in ("U", "L")]
                               + [{"frame_id": "B", "end": "I", "type": "Beam"}]}
        self.groups = {"ductile": ["E"], "gravity": ["G"]}
        self.axial = {"columns": [{"element_id": "U", "gross_area_mm2": 90000, "fck_mpa": 30},
                                  {"element_id": "L", "gross_area_mm2": 100000, "fck_mpa": 40}],
                      "combination_plan": {"source": "ASSIGNED_DESIGN", "design_assignment": {"groups": self.groups},
                                           "combinations": [{"name": "E", "force_semantics": "SCALAR_COMPONENT_ENVELOPE"},
                                                            {"name": "G", "force_semantics": "STATIC_SIGNED_VECTOR"}]}}
        self.scope = {"input_sha256": "input", "analysis_mesh": {"members": {}}, "configured_output_cuts": {}}
        self.force = {"api": "Results.FrameForce", "units_code": 6, "schema": "tbdy.next.etabs-frame-force-source.v1",
                      "rowsets": {}}
        basis = mixed_fixture()[0]["vs04_basis_probe"]
        self.tables = basis["table_reads"]
        cases = "Load Case Definitions - Summary"
        combos = "Load Combination Definitions"
        self.tables[cases] = table(cases, self.tables[cases]["rows"] + [{"Name": "RS", "Type": "Response Spectrum", "GUID": "rs"}])
        self.tables[combos] = table(combos, self.tables[combos]["rows"] + [
            {"Name": "E", "Type": "Linear Add", "LoadName": "BASE_A", "SF": "1.2", "GUID": "e"},
            {"Name": "E", "Type": "Linear Add", "LoadName": "RS", "SF": "1", "GUID": "e"}])
        self.source = {"column_axial": {"force_source": self.force}, "vs04_basis_probe": basis}
        self.mixed = {"schema": SCHEMA, "method": SPECTRAL_METHOD, "input_sha256": "input", "rows": []}
        self.plan = {"topology_blockers": [], "joints": {"N": {"column_ids": ["U", "L"]}}}
        for uid, high in (("U", 270.), ("L", 400.)):
            elm = uid + "-element"
            joints = [self.frames[uid]["point_i"], "N"]
            self.scope["analysis_mesh"]["members"][uid] = {"roster_bound": True,
                "expected_analysis_element_ids": [elm], "analysis_element_end_joints": {elm: joints}}
            self.scope["configured_output_cuts"][uid] = {"status": "REQUIRED_SUBSET_BOUND", "length_m": 4.,
                "offset_i_m": 0., "offset_j_m": .2, "cuts": [
                    {"object_station_m": x, "analysis_element_id": elm, "element_station_m": x} for x in (0., 1.9, 3.8)]}
            self.set_forces(uid, high)
        self.bind_source()

    def set_forces(self, uid, high, gravity=100.):
        elm = uid + "-element"
        rows = [(uid, 3.8, elm, 3.8, name, step, 0., -nd, 0., 0., 0., 0., 0.)
                for name, step, nd in (("E", "Max", high - 10.), ("E", "Min", high), ("G", "Single Value", gravity))]
        self.force["rowsets"][uid] = {**dict(zip(FIELDS, map(list, zip(*rows)))), "NumberResults": 3, "pRetVal": 0}
        bounds = [high - 10., high]
        self.mixed["rows"] = [x for x in self.mixed["rows"] if x["member_id"] != uid]
        self.mixed["rows"].append({"member_id": uid, "combination": "E", "status": "SAME_SOURCE_COMPONENT_REPLAY_MATCH",
            "cuts": [{"native_cut": list(rows[0][:4]), "configured_required_cut": True, "nd_bounds_kn": bounds,
                      "primitive_replay": {"status": "NUMERICAL_MATCH", "nd_bounds_kn": list(bounds)}}]})

    def bind_source(self):
        self.plan["source_payload_sha256"] = self.mixed["source_payload_sha256"] = _digest(self.source)
        self.mixed["sha256"] = _digest({k: v for k, v in self.mixed.items() if k != "sha256"})

    def decision(self):
        return joint_low_axial_decisions(self.source, self.axial, self.scope, self.mixed, self.plan,
                                         self.frames, self.points, self.adjacency,
                                         _assigned_seismic_combinations(self.axial), input_sha="input")["N"]

    def test_boundary_uses_each_column_and_physical_side_even_with_both_native_j_ends(self):
        result = self.decision()
        self.assertIs(result["exempt"], True)
        self.assertEqual([(e["physical_side"], e["end"], e["max_nd_kn"], e["limit_kn"]) for e in result["column_ends"]],
                         [("UPPER", "J", 270., 270.), ("LOWER", "J", 400., 400.)])

    def test_only_factored_gravity_plus_earthquake_nd_controls_the_exception(self):
        for seismic, gravity in ((270.000001, 100.), (230., 271.)):
            with self.subTest(seismic=seismic):
                self.set_forces("U", seismic, gravity)
                self.bind_source()
                result = self.decision()
                self.assertEqual(result["exempt"], seismic <= 270.)
                end = result["column_ends"][0]
                self.assertEqual(end["governing_combination"], "E" if seismic > gravity else "G")
                self.assertEqual(end["max_seismic_nd_kn"], seismic)

    def test_tension_keeps_its_sign(self):
        self.set_forces("L", -450., -500.)
        self.bind_source()
        end = self.decision()["column_ends"][1]
        self.assertEqual(end["max_nd_kn"], -450.)
        self.assertIs(self.decision()["exempt"], True)

    def test_native_i_of_meshed_column_uses_the_oriented_end_element(self):
        self.frames["U"].update(point_i="N", point_j="TOP")
        self.adjacency["N"][0]["end"] = "I"
        self.scope["analysis_mesh"]["members"]["U"] = {"roster_bound": True,
            "expected_analysis_element_ids": ["a", "b"], "analysis_element_end_joints": {"a": ["N", "mid"], "b": ["mid", "TOP"]}}
        self.scope["configured_output_cuts"]["U"]["cuts"] = [
            {"object_station_m": obj, "element_station_m": sta, "analysis_element_id": elm}
            for obj, sta, elm in ((0., 0., "a"), (1.9, 1.9, "a"), (2., 2., "a"), (2., 0., "b"), (3.8, 1.8, "b"))]
        raw = self.force["rowsets"]["U"]
        raw.update(ObjSta=[0.] * 3, Elm=["a"] * 3, ElmSta=[0.] * 3)
        self.mixed["rows"][0]["cuts"][0]["native_cut"] = ["U", 0., "a", 0.]
        self.bind_source()
        result = self.decision()
        self.assertIs(result["exempt"], True)
        self.assertEqual(result["column_ends"][0]["configured_cut"], ["U", 0., "a", 0.])

    def test_assigned_signed_seismic_cases_use_the_single_native_axial_value(self):
        self.axial["combination_plan"]["combinations"][0]["force_semantics"] = "STATIC_SIGNED_VECTOR"
        self.tables["Load Combination Definitions"]["rows"][-1]["LoadName"] = "ACTION_B"
        for raw in self.force["rowsets"].values():
            for field in FIELDS:
                raw[field].pop(0)
            raw["NumberResults"] = 2
            raw["StepType"][0] = "Single Value"
        self.bind_source()
        self.mixed = None
        result = self.decision()
        self.assertIs(result["exempt"], True)
        self.assertEqual(result["column_ends"][1]["max_seismic_nd_kn"], 400.)

    def test_incomplete_cycle_wrong_units_or_cross_source_cannot_waive(self):
        for defect in ("assigned case", "mesh orientation", "native element side", "missing extreme", "step",
                       "unverified replay", "other source", "straddling limit", "units", "cut",
                       "gravity only", "earthquake only"):
            with self.subTest(defect=defect):
                self.setUp()
                raw = self.force["rowsets"]["U"]
                if defect == "assigned case":
                    self.groups["capacity"] = ["missing"]
                elif defect == "mesh orientation":
                    self.scope["analysis_mesh"]["members"]["U"]["analysis_element_end_joints"]["U-element"].reverse()
                elif defect == "native element side":
                    raw["Elm"][0] = "other"
                elif defect == "missing extreme":
                    raw["StepType"][0] = "Single Value"
                elif defect == "step":
                    raw["StepNum"][0] = 1
                elif defect == "gravity only":
                    self.tables["Load Combination Definitions"]["rows"][-1]["SF"] = "0"
                elif defect == "earthquake only":
                    self.tables["Load Combination Definitions"]["rows"][-2]["SF"] = "0"
                elif defect == "unverified replay":
                    self.mixed["rows"][0]["cuts"][0]["primitive_replay"]["status"] = "NUMERICAL_MISMATCH"
                elif defect == "straddling limit":
                    self.mixed["rows"][0]["cuts"][0]["primitive_replay"]["nd_bounds_kn"][1] += 1e-11
                elif defect == "units":
                    self.force["units_code"] = 12
                elif defect == "cut":
                    self.scope["configured_output_cuts"]["U"]["cuts"].pop()
                self.bind_source()
                if defect == "other source":
                    self.mixed["input_sha256"] = "another-input"
                result = self.decision()
                self.assertIsNone(result["exempt"])
                self.assertTrue(result["reasons"])

    def test_missing_gravity_only_result_does_not_mask_complete_seismic_nd(self):
        self.force["rowsets"]["U"]["ObjSta"][2] = 1.9
        self.bind_source()
        result = self.decision()
        self.assertTrue(result["exempt"])
        upper = result["column_ends"][0]
        self.assertIsNone(upper["max_nd_kn"])
        self.assertIn("G", upper["other_unresolved_combinations"])

    def test_two_members_on_same_side_or_no_continuing_column_do_not_waive(self):
        self.points["BASE"][2] = 9
        self.assertIn("SCWB_OPPOSITE_COLUMN_SIDES_REQUIRED", self.decision()["reasons"])
        self.adjacency["N"].pop(1)
        self.assertEqual(self.decision()["status"], "NOT_A_TWO_COLUMN_JOINT")

    def test_r10_and_report_use_decision_for_spectral_only_joint_without_granting_moment_pass(self):
        self.groups.pop("gravity")
        self.axial["combination_plan"]["combinations"].pop()
        decision = self.decision()
        joints = _evaluate_scwb_at_joint_ends("U", self.frames, self.points, self.adjacency, self.source,
                                              self.axial, {}, {"checks": []}, low_axial_by_joint={"N": decision})
        self.assertEqual(len(joints), 1)
        self.assertEqual(joints[0]["status"], "SCWB_EQ_7_3_EXEMPT_LOW_AXIAL")
        self.assertIsNone(joints[0]["scenario_reference_satisfied"])
        self.assertIsNone(joints[0]["scwb_ratio"])
        html = _column_r10_html({"scwb_joints": joints})
        self.assertIn("Max seismic Nd (kN)", html)
        self.assertIn("EXEMPT_LOW_AXIAL", html)
        self.assertIn("UPPER", html)
        # A sampled gravity-case failure cannot require the waived equation or grant alpha.
        joints[0]["scenario_reference_satisfied"] = False
        closure = _evaluate_single_r14_column(uid="U", axial=self.axial, axial_col={}, pmm_col=None,
            r08_global=None, r08_local_col=None, beam_by_id={}, r10_det={"scwb_joints": joints}, story_alpha=None)
        pillar = closure["pillars"]["scwb_and_story_alpha"]
        self.assertEqual(pillar["low_axial_exempt_joint_ids"], ["N"])
        self.assertIsNone(pillar["scwb_satisfied"])
        self.assertEqual(pillar["story_alpha_rows"], [])
        self.assertNotIn("SCWB_JOINT_RATIO_REQUIRES_7_3_6_BRANCH_REVIEW", closure["open_gates"])
