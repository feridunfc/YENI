"""D2 member/joint dependency evidence for the existing offline design pipeline.

No formula, force reconstruction, second scheduler, or approval authority lives
here. Independent member candidates may run; consumers of incomplete joints or
stories cannot. Revisions describe actual upstream artifacts, not cache hits.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from math import isfinite
from typing import Any, Mapping

from .design_scenario import _digest, design_dependency_ledger

SCHEMA = "tbdy.next.member-design-dependencies.v1"
REVISION_SCHEMA = "tbdy.next.design-artifact-revisions.v1"
METHOD = "offline-member-dependencies.d2.v1"


def _identity(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _topology(source: Mapping[str, Any]) -> tuple[dict, dict, list[str]]:
    """Qualify the captured frame census before reusing its existing owner.

Connectivity is never filtered to successful force rows. Assignment census is
an independent captured table, not a claim of physical face/anchorage approval.
"""
    from .column_r10_live import _build_frame_catalog

    geometry = source.get("geometry_capture") or {}
    tables = geometry.get("tables") or {}
    issues = []
    rows_by_kind = {}
    for key, kind, native in (("COLUMN_CONNECTIVITY", "Column", "Column Object Connectivity"),
                              ("BEAM_CONNECTIVITY", "Beam", "Beam Object Connectivity")):
        table = tables.get(key) or {}
        rows = table.get("rows")
        if (table.get("table_key") != native or table.get("status") not in ("CAPTURED", "EMPTY_TABLE")
                or not isinstance(rows, list) or type(table.get("row_count")) is not int
                or table["row_count"] != len(rows)
                or any(not isinstance(r, Mapping) or not all(_identity(r.get(k)) for k in
                       ("UniqueName", "Story", "UniquePtI", "UniquePtJ"))
                       or r["UniquePtI"] == r["UniquePtJ"] for r in rows)):
            issues.append("DESIGN_CONNECTIVITY_CENSUS_UNVERIFIED:" + kind)
            continue
        ids = [r["UniqueName"] for r in rows]
        if len(set(ids)) != len(ids):
            issues.append("DESIGN_CONNECTIVITY_DUPLICATE:" + kind)
        rows_by_kind[kind] = rows
    assignments = tables.get("FRAME_ASSIGNMENTS") or {}
    ar = assignments.get("rows")
    if (assignments.get("status") != "CAPTURED" or not isinstance(ar, list)
            or type(assignments.get("row_count")) is not int or assignments["row_count"] != len(ar)
            or any(not isinstance(r, Mapping) for r in ar)):
        issues.append("DESIGN_FRAME_ASSIGNMENT_CENSUS_UNVERIFIED")
    else:
        for kind, rows in rows_by_kind.items():
            roster = [r.get("UniqueName") for r in ar if r.get("Type") == kind]
            if (any(not _identity(uid) for uid in roster) or len(set(roster)) != len(roster)
                    or set(roster) != {r["UniqueName"] for r in rows}):
                issues.append("DESIGN_FRAME_CONNECTIVITY_CENSUS_MISMATCH:" + kind)
    all_ids = [r["UniqueName"] for rows in rows_by_kind.values() for r in rows]
    if len(all_ids) != len(set(all_ids)):
        issues.append("DESIGN_FRAME_NAMESPACE_COLLISION")
    if issues:
        return {}, {}, sorted(set(issues))
    frames, _, graph = _build_frame_catalog(source)
    if set(frames) != set(all_ids):
        return {}, {}, ["DESIGN_FRAME_CATALOG_CENSUS_MISMATCH"]
    return frames, dict(graph["adjacency"]), []


def build_member_dependency_plan(source: Mapping[str, Any], scope: Mapping[str, Any] | None,
                                 *, input_sha: str) -> dict[str, Any]:
    """Freeze member and physical-joint populations before candidate evaluation."""
    scope = scope or {}
    aggregate = design_dependency_ledger(scope, input_sha=input_sha)
    global_codes = [b for b in aggregate["blockers"]
                    if b != "DESIGN_COHORT_HAS_UNRESOLVED_REQUIRED_PAIRS"]
    if any("DESIGN_DUPLICATE_OR_INVALID_EXPECTED_PAIR" in b["reason_codes"]
           for b in aggregate["blocked_pairs"]):
        global_codes.append("DESIGN_DUPLICATE_OR_INVALID_EXPECTED_PAIR")
    instances = scope.get("instances") or []
    expected = sorted({r["element_id"] for r in instances if _identity(r.get("element_id"))})
    by_member = defaultdict(list)
    for row in aggregate["blocked_pairs"]:
        by_member[row["element_id"]].append(row)
    frames, adjacency, topology_codes = _topology(source)
    feature = source.get("column_axial") or {}
    forces = (feature.get("force_source") or {}).get("rowsets") or {}
    members = {}
    for uid in expected:
        frame = frames.get(uid) or {}
        reasons = list(global_codes)
        if by_member[uid]:
            reasons.append("DESIGN_MEMBER_REQUIRED_PAIRS_UNRESOLVED")
        if not frame or frame.get("type") != "Column":
            reasons.extend(topology_codes or ["DESIGN_PHYSICAL_COLUMN_UNBOUND"])
        pair_rows = [r for r in instances if r.get("element_id") == uid]
        members[uid] = {
            "member_id": uid, "story": frame.get("story"),
            "joint_ids": [frame["point_i"], frame["point_j"]] if frame else [],
            "source_execution_allowed": not reasons, "reason_codes": sorted(set(reasons)),
            "expected_pair_count": len(pair_rows), "blocked_pairs": by_member[uid],
            "demand_revision_sha256": _digest({"forces": forces.get(uid), "pairs": pair_rows,
                                               "request": feature.get("request"),
                                               "basis": feature.get("design_preferences")}),
        }
    joints = {}
    for jid, incident in sorted(adjacency.items()):
        cols = sorted(r["frame_id"] for r in incident if r["type"] == "Column")
        if not set(cols) & set(expected):
            continue
        beams = sorted((r["frame_id"], r["end"]) for r in incident if r["type"] == "Beam")
        blockers = list(topology_codes)
        for uid in cols:
            if uid not in members or not members[uid]["source_execution_allowed"]:
                blockers.append("JOINT_COLUMN_SOURCE_UNAVAILABLE:" + uid)
        joints[jid] = {"joint_id": jid, "column_ids": cols,
                       "beam_ends": [{"member_id": uid, "end": end} for uid, end in beams],
                       "topology_sha256": _digest({"joint": jid, "incident": sorted(
                           incident, key=lambda x: (x["type"], x["frame_id"], x["end"]))}),
                       "source_blockers": sorted(set(blockers)), "blockers": sorted(set(blockers)),
                       "execution_allowed": not blockers}
    stories = {}
    for frame in frames.values():
        if frame["type"] == "Column":
            stories.setdefault(frame["story"], []).append(frame["frame_id"])
    r10_source = feature.get("r10_source") or {}
    beam_forces = (r10_source.get("beam_force_source") or {}).get("rowsets") or {}
    from .column_r10_live import BEAM_DESIGN_SUMMARY
    design_rows = ((r10_source.get("table_reads") or {}).get(BEAM_DESIGN_SUMMARY) or {}).get("rows") or []
    beam_members = {uid: {"member_id": uid, "story": f["story"], "joint_ids": [f["point_i"], f["point_j"]],
                         "demand_revision_sha256": _digest({"forces": beam_forces.get(uid),
                             "design_rows": [r for r in design_rows if r.get("UniqueName") == uid],
                             "section": f["section_name"]})}
                    for uid, f in frames.items() if f["type"] == "Beam"}
    ready = sorted(uid for uid, row in members.items() if row["source_execution_allowed"])
    return {"schema": SCHEMA, "method_revision": METHOD, "input_sha256": input_sha,
            "scope": "MEMBER_JOINT_STORY_WITH_FULL_PHYSICAL_DENOMINATORS",
            "expected_member_combination_count": aggregate["expected_member_combination_count"],
            "expected_column_count": len(expected), "blocked_pair_count": aggregate["blocked_pair_count"],
            "blocked_pairs": aggregate["blocked_pairs"], "global_blockers": sorted(set(global_codes)),
            "blockers": sorted(set(global_codes)), "topology_blockers": topology_codes,
            "members": members, "beam_members": beam_members, "source_payload_sha256": _digest(source),
            "joints": joints, "story_columns": {s: sorted(v) for s, v in sorted(stories.items())},
            "ready_member_ids": ready, "blocked_member_ids": sorted(set(expected) - set(ready)),
            "candidate_execution_allowed": bool(ready), "all_member_inputs_bound": len(ready) == len(expected) and bool(expected),
            "status": "PARTIAL_DEPENDENCY" if ready and len(ready) < len(expected) else
                      "REFERENCE_CANDIDATE_INPUTS_BOUND" if ready else "BLOCKED_DEPENDENCY",
            "independent_cut_census_proven": False, "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY"}


def bind_joint_candidates(plan: Mapping[str, Any], sections: Mapping[str, Any],
                          selections: Mapping[str, Any], beam_live: Mapping[str, Any] | None) -> dict[str, Any]:
    """Freeze each joint's actual selected inputs before SCWB/Ve/R13 owners run."""
    from ..column_engine.section_capacity import Section

    result = deepcopy(plan)
    beam_by_id = {b["member_id"]: b for b in (beam_live or {}).get("beams", ())}
    candidate_revisions = {}
    for uid, member in result["members"].items():
        selection, section = selections.get(uid), sections.get(uid)
        valid = (member["source_execution_allowed"] and isinstance(section, Section)
                 and isinstance(selection, Mapping) and selection.get("member_id") == uid
                 and bool(selection.get("selected")))
        member["selected_candidate_bound"] = valid
        member["candidate_revision_sha256"] = (_digest({"selection": selection, "section": asdict(section)})
                                                if valid else None)
        candidate_revisions[uid] = member["candidate_revision_sha256"]
    for jid, joint in result["joints"].items():
        blockers = list(joint["source_blockers"])
        dependencies = {}
        for uid in joint["column_ids"]:
            member = result["members"].get(uid) or {}
            if not member.get("selected_candidate_bound"):
                blockers.append("JOINT_SELECTED_COLUMN_UNAVAILABLE:" + uid)
            dependencies["column:" + uid] = {"candidate": candidate_revisions.get(uid),
                                             "demand": member.get("demand_revision_sha256")}
        for item in joint["beam_ends"]:
            bid, end = item["member_id"], item["end"]
            beam = beam_by_id.get(bid) or {}
            end_data = (beam.get("ends") or {}).get(end) or {}
            selection = end_data.get("engineer_selection") or {}
            capacity = selection.get("capacity") or {}
            values = (capacity.get("positive_m3_knm"), capacity.get("negative_m3_knm"))
            valid = (capacity.get("status") == "BEAM_CAPACITY_REFERENCE" and not end_data.get("released_for_bending")
                     and all(type(v) in (int, float) and isfinite(v) for v in values)
                     and values[0] > 0 and values[1] < 0)
            if not valid:
                blockers.append("JOINT_SELECTED_BEAM_END_UNAVAILABLE:" + bid + ":" + end)
            dependencies["beam:" + bid + ":" + end] = _digest({"selection": selection,
                "demand": (result["beam_members"].get(bid) or {}).get("demand_revision_sha256"),
                "released": end_data.get("released_for_bending"), "point_i": beam.get("point_i"),
                "point_j": beam.get("point_j")})
        joint.update(blockers=sorted(set(blockers)), execution_allowed=not blockers,
                     upstream_candidate_revisions=dependencies,
                     input_revision_sha256=_digest({"topology": joint["topology_sha256"], "inputs": dependencies}))
    return result


def verify_dependency_source(plan: Mapping[str, Any], source: Mapping[str, Any]) -> None:
    if plan.get("schema") != SCHEMA or plan.get("source_payload_sha256") != _digest(source):
        raise ValueError("DESIGN_DEPENDENCY_SOURCE_MISMATCH")


def joint_blockers(plan: Mapping[str, Any] | None, joint_id: str) -> list[str]:
    if plan is None:
        return []
    joint = plan["joints"].get(joint_id)
    return list(joint["blockers"]) if joint else ["DESIGN_EXPECTED_JOINT_NOT_BOUND:" + joint_id]


def member_joint_blockers(plan: Mapping[str, Any], uid: str) -> list[str]:
    member = plan["members"].get(uid) or {}
    codes = list(member.get("reason_codes", ()))
    for jid in member.get("joint_ids", ()):
        codes.extend("JOINT:" + jid + ":" + code for code in joint_blockers(plan, jid))
    return sorted(set(codes))


def story_blockers(plan: Mapping[str, Any] | None, story: str) -> list[str]:
    if plan is None:
        return []
    columns = plan["story_columns"].get(story, ())
    reasons = list(plan["topology_blockers"])
    if not columns:
        reasons.append("DESIGN_STORY_COLUMN_CENSUS_UNAVAILABLE")
    for uid in columns:
        if uid not in plan["members"]:
            reasons.append("STORY_COLUMN_OUTSIDE_EVALUATED_SCOPE:" + uid)
        else:
            reasons.extend("COLUMN:" + uid + ":" + c for c in member_joint_blockers(plan, uid))
    return sorted(set(reasons))


def blocked_member_result(uid: str, codes: list[str], *, schema: str) -> dict[str, Any]:
    return {"schema": schema, "member_id": uid, "status": "BLOCKED_DEPENDENCY",
            "execution_status": "NOT_RUN", "open_gates": sorted(set(codes)),
            "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}


def build_revision_evidence(plan: Mapping[str, Any], candidate_ledger: Mapping[str, Any] | None,
                            r10: Mapping[str, Any] | None, r08: Mapping[str, Any] | None,
                            *, input_sha: str) -> dict[str, Any]:
    """Record a dependency DAG of artifact revisions and gate R14, without recomputing.

All eligible owners are rerun each invocation (there is no design cache). The
ledger exposes invalidations between runs and makes unconsumed alpha feedback
an explicit open dependency rather than pretending the original Ve is revised.
"""
    if (plan.get("schema") != SCHEMA or plan.get("input_sha256") != input_sha
            or (candidate_ledger is not None and candidate_ledger.get("input_sha256") != input_sha)):
        raise ValueError("DESIGN_REVISION_SOURCE_MISMATCH")
    artifacts: dict[str, dict[str, Any]] = {}
    def add(key: str, payload: Any, depends: list[str]) -> str:
        if key in artifacts or any(d not in artifacts for d in depends):
            raise ValueError("DESIGN_REVISION_PRODUCER_OR_DEPENDENCY_INVALID:" + key)
        upstream = {d: artifacts[d]["revision_sha256"] for d in sorted(depends)}
        digest = _digest({"artifact_id": key, "method": METHOD, "payload_sha256": _digest(payload), "dependencies": upstream})
        artifacts[key] = {"artifact_id": key, "payload_sha256": _digest(payload),
                          "dependencies": upstream, "revision_sha256": digest}
        return key

    r10 = r10 or {}; r08 = r08 or {}
    details = r10.get("per_member") if r10.get("per_member") is not None else {r10.get("member_id"): r10}
    locals_ = r08.get("per_member") if r08.get("per_member") is not None else {r08.get("member_id"): r08}
    candidate_rows = {r["member_id"]: r for r in (candidate_ledger or {}).get("rows", ())}
    feedback = r10.get("alpha_iteration")
    feedback_consumed = False
    if feedback is not None:
        from .alpha_iteration import validate_record, SCHEMA as ALPHA_SCHEMA
        validate_record(feedback, ALPHA_SCHEMA)
        if (feedback.get("input_sha256") != input_sha
                or feedback.get("expected_member_ids") != sorted(plan["members"])
                or feedback.get("final_candidate_ledger_sha256") != _digest(candidate_ledger)):
            raise ValueError("ALPHA_FINAL_CANDIDATE_OR_SCOPE_MISMATCH")
        feedback_consumed = (feedback.get("status") == "FIXED_POINT_REFERENCE"
                             and feedback.get("feedback_consumed") is True)
    columns = {}
    for uid, member in plan["members"].items():
        demand = add("demand:" + uid, member["demand_revision_sha256"], [])
        candidate = add("candidate:" + uid, candidate_rows.get(uid), [demand])
        add("r08:" + uid, locals_.get(uid), [candidate, demand])
    for jid, joint in plan["joints"].items():
        beam_keys = []
        for item in joint["beam_ends"]:
            bid, end = item["member_id"], item["end"]
            key = "beam-end:" + bid + ":" + end
            if key not in artifacts:
                add(key, (joint.get("upstream_candidate_revisions") or {}).get("beam:" + bid + ":" + end), [])
            beam_keys.append(key)
        inputs = ["candidate:" + uid for uid in joint["column_ids"] if uid in plan["members"]]
        scwb = [j for row in details.values() if row for j in row.get("scwb_joints", ()) if j["joint_id"] == jid]
        add("scwb:" + jid, {"input_revision": joint.get("input_revision_sha256"),
                             "blockers": joint["blockers"], "result": scwb}, inputs + beam_keys)
    alpha_by_story = defaultdict(list)
    for row in (r10.get("story_alpha") or {}).get("stories", ()):
        alpha_by_story[str(row["story"])].append(row)
    for story, members in plan["story_columns"].items():
        joints = sorted({j for uid in members for j in (plan["members"].get(uid) or {}).get("joint_ids", ())})
        add("alpha:" + story, {"expected_columns": members, "result": alpha_by_story[story]},
            ["scwb:" + jid for jid in joints if jid in plan["joints"]])
    if feedback is not None:
        add("alpha-iteration", feedback, ["alpha:" + str(st) for st in plan["story_columns"]]
            + ["candidate:" + u for u in plan["members"]] + ["r08:" + u for u in plan["members"]])
    for uid, member in plan["members"].items():
        reasons = member_joint_blockers(plan, uid)
        selected = candidate_rows.get(uid) or {}
        if selected.get("status") != "SAME_RUN_CANDIDATE_BOUND":
            reasons.append("SAME_RUN_SELECTED_COLUMN_CAGE_UNAVAILABLE")
        elif member.get("candidate_revision_sha256") != selected.get("candidate_sha256"):
            reasons.append("SELECTED_CAGE_REVISION_CHANGED_AFTER_R10")
        story = member.get("story")
        alpha = alpha_by_story.get(story, [])
        if not feedback_consumed and (len(alpha) != 2 or {r.get("direction") for r in alpha} != {"X", "Y"}
                or any(r.get("demand_feedback_action") != "NONE" for r in alpha)):
            reasons.append("DESIGN_ALPHA_FEEDBACK_NOT_RESOLVED_OR_NOT_CONSUMED")
        if feedback is not None and not feedback_consumed:
            reasons.append("ALPHA_ITERATION:" + feedback["status"])
        reasons.extend("STORY:" + c for c in story_blockers(plan, story))
        deps = ["candidate:" + uid, "demand:" + uid]
        deps += ["scwb:" + jid for jid in member["joint_ids"] if jid in plan["joints"]]
        alpha_key = "alpha:" + str(story)
        if alpha_key in artifacts:
            deps.append(alpha_key)
        if feedback is not None:
            deps.append("alpha-iteration")
        det = details.get(uid) or {}
        ve = add("ve-review:" + uid, {"reference": det.get("column_transverse_and_shear"),
                 "feedback_consumed": not reasons, "open_dependencies": sorted(set(reasons))}, deps)
        closure_key = add("r14-input:" + uid, {"blockers": sorted(set(reasons))}, [ve, "r08:" + uid])
        columns[uid] = {"member_id": uid, "open_gates": sorted(set(reasons)),
                        "artifact_id": closure_key, "input_revision_sha256": artifacts[closure_key]["revision_sha256"],
                        "reference_ve_is_revised_design_demand": False,
                        "alpha_feedback_consumed": feedback_consumed}
    result = {"schema": REVISION_SCHEMA, "method_revision": METHOD, "input_sha256": input_sha,
              "artifacts": artifacts, "columns": columns, "cache_reuse_performed": False,
              "alpha_demand_iteration_implemented": feedback is not None,
              "alpha_iteration_status": feedback.get("status") if feedback else None,
              "engineering_release": "NOT_READY"}
    result["ledger_sha256"] = _digest(result)
    return result


def validate_revision_evidence(ledger: Mapping[str, Any]) -> None:
    if (ledger.get("schema") != REVISION_SCHEMA or ledger.get("method_revision") != METHOD
            or ledger.get("ledger_sha256") != _digest({k: v for k, v in ledger.items() if k != "ledger_sha256"})):
        raise ValueError("DESIGN_REVISION_LEDGER_INTEGRITY_INVALID")
    artifacts = ledger["artifacts"]
    for key, record in artifacts.items():
        dependencies = record["dependencies"]
        if (record.get("artifact_id") != key or any(d not in artifacts or artifacts[d]["revision_sha256"] != rev
                                                   for d, rev in dependencies.items())
                or record["revision_sha256"] != _digest({"artifact_id": key, "method": METHOD,
                    "payload_sha256": record["payload_sha256"], "dependencies": dependencies})):
            raise ValueError("DESIGN_REVISION_UPSTREAM_MISMATCH:" + key)
    pending, resolved = set(artifacts), set()
    while pending:
        ready = {k for k in pending if set(artifacts[k]["dependencies"]) <= resolved}
        if not ready:
            raise ValueError("DESIGN_REVISION_CYCLE")
        pending -= ready
        resolved |= ready
    for row in ledger["columns"].values():
        if row["artifact_id"] not in artifacts or row["input_revision_sha256"] != artifacts[row["artifact_id"]]["revision_sha256"]:
            raise ValueError("DESIGN_CLOSURE_REVISION_MISMATCH")


def compare_revision_evidence(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    """Return changed inputs and all dependent revisions; never reuse stale outputs."""
    for ledger in (previous, current):
        validate_revision_evidence(ledger)
    before, after = previous["artifacts"], current["artifacts"]
    changed = sorted(k for k in before.keys() & after.keys()
                     if before[k]["revision_sha256"] != after[k]["revision_sha256"])
    return {"status": "UNCHANGED" if before == after else "CHANGED",
            "changed_artifact_ids": changed, "added_artifact_ids": sorted(after.keys() - before.keys()),
            "removed_artifact_ids": sorted(before.keys() - after.keys()),
            "stale_results_reused": False}
