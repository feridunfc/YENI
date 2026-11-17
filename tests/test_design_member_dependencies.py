"""D2 orchestration contracts: no COM, no second formula oracle."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from tbdy_next.column_engine.section_capacity import Bar, Material, Section
from tbdy_next.engineering.column_r10_live import SelectedColumnCage
from tbdy_next.engineering.design_scenario import selected_candidate_ledger
from tbdy_next.engineering.design_dependencies import (
    _digest, build_member_dependency_plan, bind_joint_candidates, build_revision_evidence,
    compare_revision_evidence, joint_blockers, member_joint_blockers, story_blockers,
    verify_dependency_source,
)
from test_offline_design_scenario import scope_fixture


def fixture():
    def table(key, rows):
        return {"table_key": key, "status": "CAPTURED" if rows else "EMPTY_TABLE",
                "rows": rows, "row_count": len(rows)}
    columns = [dict(UniqueName=u, Story=s, UniquePtI=i, UniquePtJ=j)
               for u, s, i, j in (("C1", "S1", "A", "B"), ("C2", "S2", "B", "C"), ("C3", "S3", "D", "E"))]
    beams = [dict(UniqueName=u, Story=s, UniquePtI=i, UniquePtJ=j)
             for u, s, i, j in (("B1", "S1", "B", "F"), ("B3", "S3", "E", "G"))]
    assignments = [dict(UniqueName=r["UniqueName"], Type=kind, Story=r["Story"])
                   for kind, rows in (("Column", columns), ("Beam", beams)) for r in rows]
    source = {"geometry_capture": {"tables": {
        "COLUMN_CONNECTIVITY": table("Column Object Connectivity", columns),
        "BEAM_CONNECTIVITY": table("Beam Object Connectivity", beams),
        "FRAME_ASSIGNMENTS": table("Frame Assignments - Summary", assignments),
    }}, "column_axial": {"force_source": {"rowsets": {u: {"P": [-1]} for u in ("C1", "C2", "C3")}}},
              "column_selection": {}}
    scope = scope_fixture()
    scope["instances"] = [dict(deepcopy(scope["instances"][0]), element_id=u) for u in ("C1", "C2", "C3")]
    scope["expected_member_combination_count"] = 3
    return source, scope


def selected_inputs(plan):
    selections = {u: {"member_id": u, "selected": {"label": "fixture"}} for u in plan["members"]}
    sections = {u: Section(300, 400, (Bar(-50, -50, 314), Bar(50, 50, 314)), Material(30, 20, 365))
                for u in selections}
    beams = {"beams": [{"member_id": u, "point_i": i, "point_j": j, "ends": {
        e: {"engineer_selection": {"capacity": {"status": "BEAM_CAPACITY_REFERENCE",
              "positive_m3_knm": 50, "negative_m3_knm": -60}}, "released_for_bending": False}
        for e in ("I", "J")}} for u, i, j in (("B1", "B", "F"), ("B3", "E", "G"))]}
    return sections, selections, beams


def artifacts(source, scope):
    plan = build_member_dependency_plan(source, scope, input_sha="input-hash")
    sections, selections, beams = selected_inputs(plan)
    plan = bind_joint_candidates(plan, sections, selections, beams)
    r10 = {"per_member": {u: {"engineer_column_selection": selections[u], "scwb_joints": [],
                              "column_transverse_and_shear": {"fixture": True}} for u in selections},
           "story_alpha": {"stories": [{"story": s, "direction": d, "demand_feedback_action": "NONE"}
                          for s in ("S1", "S2", "S3") for d in ("X", "Y")]}}
    cages = {u: SelectedColumnCage(selections[u], sections[u], "input-hash",
                                  plan["members"][u]["candidate_revision_sha256"]) for u in selections}
    ledger = selected_candidate_ledger(scope, cages, r10, input_sha="input-hash")
    r08 = {"per_member": {u: {"status": "fixture"} for u in selections}}
    return plan, sections, selections, beams, r10, cages, ledger, r08


class MemberDependencyContracts(unittest.TestCase):
    def test_one_bad_pair_stops_only_its_member_candidates(self):
        source, scope = fixture(); scope["instances"][0]["execution_status"] = "BLOCKED"
        p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        self.assertEqual(p["ready_member_ids"], ["C2", "C3"])
        self.assertEqual(p["blocked_member_ids"], ["C1"])
        self.assertEqual(p["expected_member_combination_count"], 3)
        self.assertTrue(p["candidate_execution_allowed"])
        self.assertFalse(p["all_member_inputs_bound"])
        self.assertTrue(joint_blockers(p, "B")); self.assertFalse(joint_blockers(p, "E"))
        self.assertTrue(story_blockers(p, "S1")); self.assertTrue(story_blockers(p, "S2"))
        self.assertFalse(story_blockers(p, "S3"))

    def test_global_source_mismatch_stops_every_member(self):
        source, scope = fixture()
        p = build_member_dependency_plan(source, scope, input_sha="other")
        self.assertFalse(p["candidate_execution_allowed"])
        self.assertEqual(len(p["members"]), 3)

    def test_scope_duplicate_is_not_localized_as_if_valid_population(self):
        source, scope = fixture(); scope["instances"].append(deepcopy(scope["instances"][0]))
        scope["expected_member_combination_count"] = 4
        p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        self.assertFalse(p["candidate_execution_allowed"])
        self.assertIn("DESIGN_DUPLICATE_OR_INVALID_EXPECTED_PAIR", p["global_blockers"])

    def test_absent_connectivity_is_not_a_beamless_exception(self):
        source, scope = fixture(); t = source["geometry_capture"]["tables"]["BEAM_CONNECTIVITY"]
        t["rows"] = []; t["row_count"] = 0; t["status"] = "EMPTY_TABLE"
        p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        self.assertFalse(p["candidate_execution_allowed"])
        self.assertIn("DESIGN_FRAME_CONNECTIVITY_CENSUS_MISMATCH:Beam", p["topology_blockers"])

    def test_duplicate_topology_is_rejected_before_dictionary_overwrite(self):
        source, scope = fixture(); t = source["geometry_capture"]["tables"]["COLUMN_CONNECTIVITY"]
        t["rows"].append(deepcopy(t["rows"][0])); t["row_count"] += 1
        p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        self.assertFalse(p["candidate_execution_allowed"])

    def test_single_column_scope_does_not_erase_unevaluated_joint_neighbor(self):
        source, scope = fixture(); scope["instances"] = scope["instances"][:1]; scope["expected_member_combination_count"] = 1
        p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        self.assertEqual(p["ready_member_ids"], ["C1"])
        self.assertIn("JOINT_COLUMN_SOURCE_UNAVAILABLE:C2", joint_blockers(p, "B"))
        self.assertEqual(p["story_columns"]["S2"], ["C2"])

    def test_foreign_plan_cannot_be_consumed_by_current_source(self):
        source, scope = fixture(); p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        verify_dependency_source(p, source)
        source["column_axial"]["force_source"]["rowsets"]["C1"]["P"] = [-2]
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"): verify_dependency_source(p, source)

    def test_missing_selected_neighbor_blocks_joint_not_independent_member(self):
        source, scope = fixture(); p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        sections, selections, beams = selected_inputs(p); sections.pop("C1")
        bound = bind_joint_candidates(p, sections, selections, beams)
        self.assertIn("JOINT_SELECTED_COLUMN_UNAVAILABLE:C1", joint_blockers(bound, "B"))
        self.assertTrue(bound["members"]["C2"]["selected_candidate_bound"])
        self.assertFalse(joint_blockers(bound, "E"))

    def test_missing_beam_end_blocks_its_joint_not_other_beam_end(self):
        source, scope = fixture(); p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        sections, selections, beams = selected_inputs(p); beams["beams"][0]["ends"].pop("I")
        bound = bind_joint_candidates(p, sections, selections, beams)
        self.assertIn("JOINT_SELECTED_BEAM_END_UNAVAILABLE:B1:I", joint_blockers(bound, "B"))
        self.assertFalse(joint_blockers(bound, "E"))

    def test_missing_released_or_wrong_sign_beam_does_not_supply_a_selected_capacity(self):
        source, scope = fixture(); p = build_member_dependency_plan(source, scope, input_sha="input-hash")
        for mutation in ("missing", "released", "wrong_sign"):
            sections, selections, beams = selected_inputs(p); end = beams["beams"][0]["ends"]["I"]
            if mutation == "missing": end["engineer_selection"]["capacity"].pop("positive_m3_knm")
            elif mutation == "released": end["released_for_bending"] = True
            else: end["engineer_selection"]["capacity"]["negative_m3_knm"] = 60
            self.assertTrue(joint_blockers(bind_joint_candidates(p, sections, selections, beams), "B"))


class RevisionContracts(unittest.TestCase):
    def test_deterministic_and_each_upstream_revision_exists(self):
        source, scope = fixture(); p, _, _, _, r10, _, candidates, r08 = artifacts(source, scope)
        a = build_revision_evidence(p, candidates, r10, r08, input_sha="input-hash")
        b = build_revision_evidence(p, candidates, r10, r08, input_sha="input-hash")
        self.assertEqual(compare_revision_evidence(a,b)["status"], "UNCHANGED")
        for record in a["artifacts"].values():
            for key, revision in record["dependencies"].items():
                self.assertEqual(revision, a["artifacts"][key]["revision_sha256"])
        self.assertFalse(a["alpha_demand_iteration_implemented"])

    def test_cage_revision_invalidates_joint_story_ve_and_closure_not_disconnected_component(self):
        source, scope = fixture(); p, sections, selections, beams, r10, cages, cand, r08 = artifacts(source, scope)
        a = build_revision_evidence(p, cand, r10, r08, input_sha="input-hash")
        sections["C1"] = replace(sections["C1"], t2=310)
        cages["C1"] = SelectedColumnCage(selections["C1"], sections["C1"])
        changed = bind_joint_candidates(p, sections, selections, beams)
        cand = selected_candidate_ledger(scope, cages, r10, input_sha="input-hash")
        b = build_revision_evidence(changed, cand, r10, r08, input_sha="input-hash")
        ids = compare_revision_evidence(a,b)["changed_artifact_ids"]
        for key in ("candidate:C1", "scwb:B", "alpha:S1", "alpha:S2", "ve-review:C2", "r14-input:C2"):
            self.assertIn(key, ids)
        for key in ("candidate:C3", "scwb:E", "alpha:S3", "r14-input:C3"):
            self.assertNotIn(key, ids)

    def test_stale_candidate_from_another_r10_revision_blocks_closure(self):
        source, scope = fixture(); p, _, _, _, r10, _, cand, r08 = artifacts(source, scope)
        cand["rows"][0]["candidate_sha256"] = "old"
        out = build_revision_evidence(p, cand, r10, r08, input_sha="input-hash")
        self.assertIn("SELECTED_CAGE_REVISION_CHANGED_AFTER_R10", out["columns"]["C1"]["open_gates"])

    def test_alpha_feedback_request_is_not_reported_as_consumed(self):
        source, scope = fixture(); p, _, _, _, r10, _, cand, r08 = artifacts(source, scope)
        for r in r10["story_alpha"]["stories"]:
            if r["story"] == "S1": r["demand_feedback_action"] = "AMPLIFY_COLUMN_DEMANDS_BY_1_OVER_ALPHA"
        out = build_revision_evidence(p, cand, r10, r08, input_sha="input-hash")
        self.assertIn("DESIGN_ALPHA_FEEDBACK_NOT_RESOLVED_OR_NOT_CONSUMED", out["columns"]["C1"]["open_gates"])
        self.assertNotIn("DESIGN_ALPHA_FEEDBACK_NOT_RESOLVED_OR_NOT_CONSUMED", out["columns"]["C3"]["open_gates"])

    def test_beam_revision_flows_to_incident_joint(self):
        source, scope = fixture(); p, sections, selections, beams, r10, _, cand, r08 = artifacts(source, scope)
        a = build_revision_evidence(p,cand,r10,r08,input_sha="input-hash")
        beams["beams"][0]["ends"]["I"]["engineer_selection"]["capacity"]["positive_m3_knm"] = 51
        p = bind_joint_candidates(p,sections,selections,beams)
        b = build_revision_evidence(p,cand,r10,r08,input_sha="input-hash")
        ids = compare_revision_evidence(a,b)["changed_artifact_ids"]
        self.assertIn("beam-end:B1:I", ids); self.assertIn("scwb:B",ids); self.assertNotIn("scwb:E",ids)

    def test_wrong_source_and_tampered_ledger_are_rejected(self):
        source, scope = fixture(); p, _, _, _, r10, _, cand, r08 = artifacts(source, scope)
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"):
            build_revision_evidence(p,cand,r10,r08,input_sha="other")
        a = build_revision_evidence(p,cand,r10,r08,input_sha="input-hash"); b=deepcopy(a)
        b["artifacts"]["candidate:C1"]["revision_sha256"]="bad"
        with self.assertRaisesRegex(ValueError, "INTEGRITY_INVALID"): compare_revision_evidence(a,b)


class ExecutionContracts(unittest.TestCase):
    def test_r08_skips_only_blocked_member_and_keeps_expected_population(self):
        from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
        source, scope = fixture(); scope["instances"][0]["execution_status"]="BLOCKED"
        p, _, selections, _, r10, cages, _, _ = artifacts(source,scope)
        pmm={"scope":"ALL_COLUMNS","member_id":"ALL", "members":[{"member_id":u} for u in p["members"]]}
        with patch("tbdy_next.engineering.column_r08_local_live._project_single_r08_local",
                   side_effect=lambda source,geo,ax,member,*a,**kw:{"member_id":member["member_id"],"open_gates":[]}) as solver:
            out=project_column_r08_local_live(source,{}, {},pmm,r10_live=r10,selected_cages=cages,dependency_plan=p)
        self.assertEqual(solver.call_count,2)
        self.assertEqual(out["expected_column_count"],3);self.assertEqual(out["evaluated_column_count"],2)
        self.assertEqual(out["per_member"]["C1"]["status"],"BLOCKED_DEPENDENCY")

    def test_r08_rejects_cage_from_other_source_before_solver(self):
        from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
        source, scope = fixture(); p, _, _, _, r10, cages, _, _ = artifacts(source, scope)
        cages["C1"] = replace(cages["C1"], input_sha256="another-run-source")
        pmm = {"member_id": "C1"}
        with patch("tbdy_next.engineering.column_r08_local_live._project_single_r08_local") as solver:
            out = project_column_r08_local_live(source, {}, {}, pmm, r10_live=r10, selected_cages=cages, dependency_plan=p)
        solver.assert_not_called()
        self.assertEqual(out["status"], "BLOCKED_DEPENDENCY")

    def test_scwb_does_not_call_capacity_owner_on_a_blocked_joint(self):
        from tbdy_next.engineering.column_r10_live import _evaluate_scwb_at_joint_ends, _build_frame_catalog
        source, scope = fixture(); source["column_axial"]["pmm_section_source"] = {"fixture": True}
        scope["instances"][0]["execution_status"] = "BLOCKED"
        p, _, _, beams, _, _, _, _ = artifacts(source, scope)
        frames, _, meta = _build_frame_catalog(source)
        axial = {"combination_plan": {"combinations": [{"name": "G", "force_semantics": "STATIC_SIGNED_VECTOR"}]}}
        with patch("tbdy_next.engineering.column_r10_live.column_axis_capacity", side_effect=AssertionError("blocked")) as owner:
            out = _evaluate_scwb_at_joint_ends("C2", frames, {"B": [0,0,0], "C": [0,0,3]}, meta["adjacency"],
                                              source, axial, {}, {"checks": []}, beam_live=beams, dependency_plan=p)
        owner.assert_not_called()
        self.assertEqual(len(out), 2)
        self.assertTrue(all(r["status"] == "BLOCKED_DEPENDENCY" and r["joint_id"] == "B" for r in out))

    def test_ve_cannot_fall_back_to_unreduced_capacity_when_dependency_missing(self):
        from tbdy_next.engineering.column_r10_live import _evaluate_single_member_r10_details, _build_frame_catalog
        source, scope = fixture(); scope["instances"][0]["execution_status"] = "BLOCKED"
        p, sections, selections, beams, _, _, _, _ = artifacts(source,scope)
        frames,points,meta = _build_frame_catalog(source)
        with patch("tbdy_next.engineering.column_r10_live._evaluate_scwb_at_joint_ends", return_value=[]), patch(
                "tbdy_next.engineering.column_r10_live._evaluate_column_shear_and_confinement_for_id", return_value={"fixture": True}), patch(
                "tbdy_next.engineering.column_r10_live._column_capacity_shear_ve", side_effect=AssertionError("blocked")) as owner:
            out = _evaluate_single_member_r10_details(uid="C2", frames=frames, points=points, adjacency=meta["adjacency"],
                source=source, geometry={}, axial={}, end_rows=[], beam_live=beams, eng_col_res=selections["C2"],
                eng_col_sections=sections, col_sections_cache={}, beam_sel_active=True, pmm_single=None, dependency_plan=p)
        owner.assert_not_called()
        self.assertEqual(out["column_transverse_and_shear"]["capacity_shear_dependency"]["status"], "BLOCKED_DEPENDENCY")

    def test_blocked_story_keeps_full_population_and_never_calls_alpha_formula(self):
        from tbdy_next.engineering.column_r10_live import _evaluate_story_alpha_summary, _build_frame_catalog
        source,scope = fixture();scope["instances"][0]["execution_status"]="BLOCKED"
        p, _, _, _, _, _, _, _ = artifacts(source,scope)
        frames, _, _ = _build_frame_catalog(source)
        axial={"combination_plan": {"source":"ASSIGNED_DESIGN", "design_assignment":{"groups":{"ductile":["G"]}},
                                   "combinations":[{"name":"G","force_semantics":"STATIC_SIGNED_VECTOR"}]}}
        with patch("tbdy_next.engineering.column_r10_live.evaluate_story_alpha_reference", side_effect=AssertionError("blocked")) as owner:
            out=_evaluate_story_alpha_summary(evaluated_uids=["C1", "C2"], all_target_cols=[frames["C1"],frames["C2"]],
                frames=frames, scwb_joints=[{"target_member_id":"C2","direction":"X"}], force_rowsets={},axial=axial,
                use_engineer_selection=True,dependency_plan=p)
        owner.assert_not_called()
        self.assertEqual(len(out["stories"]),4)
        self.assertTrue(all(r["denominator_status"]=="FULL_STORY_COLUMN_DENOMINATOR" for r in out["stories"]))
        self.assertTrue(all(r["governing_alpha_i"] is None for r in out["stories"]))

    def test_r10_skips_bad_own_candidate_but_selects_other_members(self):
        from tbdy_next.engineering.column_r10_live import project_column_r10_live
        source, scope=fixture();scope["instances"][0]["execution_status"]="BLOCKED"
        p=build_member_dependency_plan(source,scope,input_sha="input-hash")
        sections,selections,beams=selected_inputs(p)
        def select(**kw): u=kw["uid"];return selections[u],sections[u]
        def details(**kw):
            return {"member_id":kw["uid"], "scwb_joints":[], "column_transverse_and_shear":None,
                    "member_joint_ends":[], "engineer_column_selection":kw["eng_col_res"], "global_moment_projections":[]}
        axial={"columns":[{"element_id":u} for u in p["members"]]}
        pmm={"scope":"ALL_COLUMNS","member_id":"ALL","members":[{"member_id":u} for u in p["members"]]}
        with patch("tbdy_next.engineering.column_r10_live._evaluate_engineer_column_selection",side_effect=select) as sel, patch(
                "tbdy_next.engineering.column_r10_live._evaluate_single_member_r10_details",side_effect=details) as det, patch(
                "tbdy_next.engineering.column_r10_live._evaluate_joint_end",side_effect=lambda col,end,*a:{
                    "member_id":col["frame_id"],"end":end,"point_id":col["point_i" if end=="I" else "point_j"],
                    "status":"fixture","narrow_faces":[],"enclosure_scenario":None}), patch(
                "tbdy_next.engineering.column_r10_live._attach_r13_joint_shear_and_transverse"):
            cages={};out=project_column_r10_live(source,{},axial,pmm,beam_live=beams,dependency_plan=p,selected_cages_out=cages)
        self.assertEqual([c.kwargs["uid"] for c in sel.call_args_list],["C2","C3"])
        self.assertEqual(det.call_count,2);self.assertEqual(set(out["per_member"]),{"C1","C2","C3"})
        self.assertEqual(set(cages),{"C2","C3"})
        self.assertTrue(joint_blockers(out["member_dependencies"],"B"))

if __name__ == "__main__": unittest.main()
