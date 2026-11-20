"""Directional end coverage, native supplementary statics, and R14 ratio regressions."""
from copy import deepcopy
from unittest import TestCase

from test_alpha_design_iteration import two_columns
from test_mixed_design_demands import table
from test_native_demand_sources import support_fixture
from test_r10_live import _rowset
from tbdy_next.engineering.alpha_iteration import run_bounded_feedback
from tbdy_next.engineering.column_r14_closure import _evaluate_single_r14_column
from tbdy_next.engineering.demand_sources import demand_capture_plan, component_force_rows
from tbdy_next.engineering.design_dependencies import _stories_without_alpha
from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.scwb_axial import assigned_story_applicability, qualified_interval_ratio
from tbdy_next.engineering.story_static_reference import _member_witness, _signed_rows, _story_reference


def population():
    source, _, scope, dep, r10 = two_columns()
    tables = source["geometry_capture"]["tables"]
    tables["FRAME_ASSIGNMENTS"]["rows"].append({"UniqueName":"B", "Type":"Beam", "AxisAngle":"0"})
    tables["BEAM_CONNECTIVITY"]["rows"].append({"UniqueName":"B","UniquePtI":"C1J","UniquePtJ":"C2J","Story":"Zemin"})
    source["column_axial"]["request"] = {"pmm_member":"ALL"}
    scope["input_sha256"] = "test"
    dep.update(input_sha256="test", source_payload_sha256=_digest(source), all_member_inputs_bound=True)
    for uid, member in dep["members"].items():
        member["selected_candidate_bound"] = True
        for end, jid in zip(("I","J"), member["joint_ids"]):
            beams = [] if end == "I" else [{"member_id":"B", "end":"I" if uid == "C1" else "J"}]
            dep["joints"][jid].update(column_ids=[uid], beam_ends=beams, execution_allowed=True)
    r10["member_dependencies"] = dep
    return source, scope, dep, r10


class StoryApplicability(TestCase):
    def test_roof_and_beamless_ends_with_no_implicit_alpha(self):
        args = population()
        rows = assigned_story_applicability(*args, ["E"])
        self.assertEqual([r["status"] for r in rows], ["ALTERNATIVE_NOT_REQUIRED"] * 2)
        x, y = rows
        self.assertEqual([r["disposition"] for r in x["ends"]],
                         ["NO_FRAME_BEAM_AT_NODE", "COLUMN_DOES_NOT_CONTINUE_ABOVE_7_3_5_3_B"] * 2)
        self.assertEqual(y["ends"][1]["disposition"], "NO_FRAME_BEAM_IN_DIRECTION")
        self.assertIsNone(x["alpha"])
        status = {"status":"ALTERNATIVE_NOT_REQUIRED", "cases":[], "reason_codes":[], "story_applicability":rows}
        dep = args[2]
        feedback = {"status":status["status"],"final_qualification":status, "source_payload_sha256":dep["source_payload_sha256"],
                    "final_feasibility":{"status":"FEASIBLE_REFERENCE","reselect_member_ids":[]}}
        self.assertEqual(_stories_without_alpha(feedback, dep), {"Zemin"})
        y["ends"].pop()
        self.assertEqual(_stories_without_alpha(feedback, dep), set())

    def test_deleted_roster_beam_or_cross_source_disallows_waiver(self):
        for defect in ("beam", "roster", "source", "cage", "coordinates"):
            with self.subTest(defect=defect):
                source, scope, dep, r10 = population()
                if defect == "beam":
                    dep["joints"]["C1J"]["beam_ends"] = []
                elif defect == "roster":
                    dep["story_columns"]["Zemin"].pop()
                elif defect == "source":
                    scope["input_sha256"] = "other"
                elif defect == "cage":
                    dep["members"]["C2"]["selected_candidate_bound"] = False
                else:
                    source["vs05_delta_source"]["table_reads"]["Point Object Connectivity"]["rows"].pop()
                    dep["source_payload_sha256"] = _digest(source)
                rows = assigned_story_applicability(source, scope, dep, r10, ["E"])
                self.assertFalse(rows and all(r["status"] == "ALTERNATIVE_NOT_REQUIRED" for r in rows))

    def test_inapplicable_alternative_cannot_hide_candidate_reselection_or_numerical_error(self):
        for feasibility, members, expected in (("FEASIBLE_REFERENCE", [], "ALTERNATIVE_NOT_REQUIRED"),
             ("FEASIBLE_REFERENCE", ["C"], "RESELECTION_REQUIRED"), ("NUMERIC_OR_DEPENDENCY_UNRESOLVED", [], "NUMERIC_OR_DEPENDENCY_UNRESOLVED")):
            with self.subTest(expected=expected):
                _, record = run_bounded_feedback(initial={}, qualify=lambda s: {"status":"ALTERNATIVE_NOT_REQUIRED","cases":[]},
                    demand=None, rebuild=None, signature=None, feasible=lambda s: {"status":feasibility,"reselect_member_ids":members})
                self.assertEqual((record["status"], record["iteration_count"], record["feedback_consumed"]), (expected, 0, False))

    def test_r14_projects_already_normalized_bound_and_rejects_missing_sway(self):
        interval = {"input_sha256":"src", "status":"SCWB_EQ_7_3_INTERVAL_SUFFICIENT","sufficient":True,
                    "evaluated_checks":2,"expected_checks":2,"minimum_ratio_lower":2.75,
                    "cases":[{"combination":"E","sways":[{"rotation_sign":s,"sufficient":True,"ratio_lower":v}
                              for s, v in ((1, 3.), (-1, 2.75))]}]}
        joint = {"joint_id":"J","direction":"X","low_axial_exception":{"status":"LOW_AXIAL_LIMIT_EXCEEDED",
                 "exempt":False,"input_sha256":"src","seismic_combinations":["E"]},"seismic_axial_interval_check":interval}
        def pillar(joints):
            return _evaluate_single_r14_column(uid="C", axial={}, axial_col={}, pmm_col=None, r08_global=None,
                r08_local_col=None, beam_by_id={}, r10_det={"scwb_joints":joints}, story_alpha=None)["pillars"]["scwb_and_story_alpha"]
        self.assertEqual(qualified_interval_ratio(joint), 2.75)
        self.assertEqual(pillar([joint])["min_scwb_ratio"], 2.75)
        p = pillar([joint, {"joint_id":"K","low_axial_exception":{"exempt":True}}])
        self.assertEqual(p["min_scwb_ratio"], 2.75)
        self.assertIsNone(p["scwb_satisfied"])
        interval["cases"][0]["sways"].pop()
        self.assertIsNone(qualified_interval_ratio(joint))
        self.assertIsNone(pillar([joint])["min_scwb_ratio"])


class SupplementarySignedCases(TestCase):
    def test_opt_in_is_disjoint_from_assigned_primitives(self):
        s, axial, _ = support_fixture()
        plan = axial["combination_plan"]
        self.assertEqual(demand_capture_plan(s, plan), s["column_axial"]["demand_support"]["plan"])
        for names in (["RS"], ["BASE_A"], ["M"], ["missing"]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                demand_capture_plan(s, {**plan,"reference_static_cases":names})
        tables = s["vs04_basis_probe"]["table_reads"]
        for key, row in (("Load Case Definitions - Summary", {"Name":"EX","Type":"Linear Static","GUID":"ex"}),
            ("Load Case Definitions - Linear Static", {"Name":"EX","LoadType":"Load","LoadName":"p2","LoadSF":"1"})):
            tables[key] = table(key, [*tables[key]["rows"], row])
        plan["reference_static_cases"] = ["EX"]
        extended = demand_capture_plan(s, plan)
        self.assertIn("EX", extended["cases"])
        self.assertNotIn("EX", extended["primitive_cases"])
        support = s["column_axial"]["demand_support"]
        support["plan"] = extended
        force = support["force_source"]
        for k in ("before","during","after"):
            force["output_selection_" + k]["cases"]["EX"] = k == "during"
        from tbdy_next.column_engine.source_bank import native_frame_force_rows
        orig = list(native_frame_force_rows(force["rowsets"]["C1"], "C1"))
        new = [(*r[:4], "EX", *r[5:]) for r in orig if r[4] == "BASE_A"]
        force["rowsets"]["C1"] = _rowset(orig + new)
        self.assertNotIn("EX", {r[4] for r in component_force_rows(s, "C1", plan)})

    def setUp(self):
        self.uid = "C"
        self.frame = {"frame_id":"C","point_i":"I","point_j":"J","axes_global":[[0,0,1],[0,1,0],[-1,0,0]]}
        self.points = {"I":[0, 0, 1], "J":[0, 0, 4]}
        cuts = [{"analysis_element_id":"e","object_station_m":s,"element_station_m":s} for s in (0.,1.5,3.)]
        self.scope = {"analysis_mesh":{"members":{"C":{"roster_bound":True,"expected_analysis_element_ids":["e"],
            "analysis_element_end_joints":{"e":["I","J"]}}}}, "configured_output_cuts":{"C":{
            "status":"REQUIRED_SUBSET_BOUND","length_m":3.,"offset_i_m":0.,"offset_j_m":0.,"cuts":cuts}}}
        self.section = {"gross_area_mm2":100000.,"fck_mpa":30.}
        rows = [("C",s,"e",s,n,"Single Value",0.,p,20.,-7.,0.,0.,0.)
                for s in (0.,1.5,3.) for n,p in (("G",-200.),("L",-200.),("EX",35. if s else -20.))]
        self.native = _rowset(rows)
        self.supp = _signed_rows(self.native, "C", {"L", "EX"})
        self.grav = _signed_rows(self.native, "C", {"G"})

    def witness(self):
        return _member_witness("C", "EX", {"G":{"L":1}}, self.supp, self.grav, self.scope, self.frame, self.section)

    def story(self, term):
        return _story_reference("story", "X", "EX", ["C"], {"C":self.frame}, self.points, {"C":term}, {})

    def test_projection_interior_governing_sign_and_identity(self):
        term = self.witness()
        self.assertEqual((term["governing_axial"]["max_nd_kn"],term["governing_axial"]["earthquake_factor"]), (235., -1))
        result = self.story(term)
        self.assertEqual((result["vis_kn"], result["vik_kn"], result["alpha"], result["factor"]), (7.,7.,1.,1.))
        self.assertTrue(result["identity_factor_check"]["fixed"])
        self.assertEqual(result["terms"][0]["local_projection"], [0,-1])

    def test_high_axial_cannot_be_counted_on_roof_or_from_another_case(self):
        self.section["gross_area_mm2"] = 70000.
        r = self.story(self.witness())
        self.assertEqual(r["signed_total_kn"],7.)
        self.assertIsNone(r["vis_kn"])
        self.assertIsNone(r["alpha"])

    def test_missing_duplicate_nonzero_step_or_incompatible_gravity_blocks(self):
        for defect in ("cut","gravity","step","duplicate","configured"):
            with self.subTest(defect=defect):
                self.setUp()
                key = next(iter(self.supp["EX"]))
                if defect == "cut":
                    self.supp["EX"].pop(key)
                elif defect == "gravity":
                    row = self.supp["L"][key]
                    self.supp["L"][key] = (*row[:7], 10., *row[8:])
                elif defect == "configured":
                    self.scope["configured_output_cuts"]["C"]["cuts"][1]["element_station_m"] += .1
                else:
                    raw = deepcopy(self.native)
                    if defect == "step":
                        raw["StepNum"][2] = 1.
                    else:
                        for k,v in raw.items():
                            if isinstance(v,list):
                                v.append(v[2])
                        raw["NumberResults"] += 1
                    with self.assertRaises(ValueError):
                        _signed_rows(raw, "C", {"EX"})
                    continue
                with self.assertRaises(ValueError):
                    self.witness()
