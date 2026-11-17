"""Bounded same-run alpha feedback; consumes existing owners, never native writes.

Supported reference branch: full physical story population, upward vertical
orthogonal frames, qualified configured bottom cuts, assigned signed seismic
combinations and selected two-sign SCWB evidence at both ends. No spectral
vector reconstruction, implied support exemption or low-N numerator credit.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import math
from typing import Any, Mapping

from ..column_engine.beam_references import station_budget
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.story_alpha import evaluate_story_alpha_reference, alpha_feedback_factor
from .design_scenario import _digest

SCHEMA = "tbdy.next.alpha-design-iteration.v1"
DEMAND_SCHEMA = "tbdy.next.alpha-demand-revision.v1"
METHOD = "alpha-feedback.mixed-signed-same-cut.v2"
MAX_ITERATIONS = 8


def _sealed(value):
    return {**value, "sha256": _digest(value)}


def validate_record(value, schema):
    if (not isinstance(value, Mapping) or value.get("schema") != schema
            or value.get("sha256") != _digest({k: v for k, v in value.items() if k != "sha256"})):
        raise ValueError("ALPHA_REVISION_INTEGRITY_INVALID")


def _axis_indices(frame, direction):
    axes = frame.get("axes_global")
    if not axes or abs(axes[0][2] - 1.0) > 1e-10:
        raise ValueError("ALPHA_UPWARD_VERTICAL_AXES_REQUIRED")
    axis = 0 if direction == "X" else 1
    matches = [j for j in (1, 2) if abs(abs(axes[j][axis]) - 1.0) <= 1e-10]
    if len(matches) != 1:
        raise ValueError("ALPHA_ORTHOGONAL_AXES_REQUIRED")
    return (8, 12) if matches[0] == 1 else (9, 11)


def _earthquake_shear_provenance(source, names, plan):
    from .mixed_demands import earthquake_partition
    return earthquake_partition(source, names, plan)


def qualify_story_alpha(source, axial, scope, dependencies, r10):
    """Compute alpha using original forces at one physically common bottom cut.

The strict subset deliberately blocks unproven end exemptions. Numerical
SCWB is still a selected-candidate reference, not engineering approval.
"""
    from .column_r10_live import _build_frame_catalog
    from .design_dependencies import story_blockers
    from .mixed_demands import earthquake_row

    plan = (axial or {}).get("combination_plan") or {}
    groups = (plan.get("design_assignment") or {}).get("groups") or {}
    names = sorted(set(groups.get("ductile", ())) | set(groups.get("capacity", ())))
    semantics = {r["name"]: r.get("force_semantics") for r in plan.get("combinations", ())}
    reasons = []
    if plan.get("source") != "ASSIGNED_DESIGN" or plan.get("blockers") or not names:
        reasons.append("ALPHA_ASSIGNED_SEISMIC_COMBINATIONS_UNAVAILABLE")
    for name in names:
        if semantics.get(name) != "STATIC_SIGNED_VECTOR":
            reasons.append("ALPHA_SIGNED_SEISMIC_DEMAND_REQUIRED:" + name)
    if not dependencies or dependencies.get("global_blockers") or dependencies.get("topology_blockers"):
        reasons.append("ALPHA_PHYSICAL_DEPENDENCIES_UNAVAILABLE")
    if reasons:
        return {"status": "BLOCKED_INPUTS", "reason_codes": sorted(set(reasons)), "cases": []}
    try:
        seismic_basis = _earthquake_shear_provenance(source, names, plan)
    except (KeyError, ValueError, TypeError, ArithmeticError, RecursionError) as exc:
        return {"status": "BLOCKED_INPUTS", "cases": [],
                "reason_codes": ["ALPHA_SEISMIC_SHEAR_PROVENANCE_UNVERIFIED:" + str(exc)]}
    frames, points, _ = _build_frame_catalog(source)
    rowsets = ((source.get("column_axial") or {}).get("force_source") or {}).get("rowsets") or {}
    cuts = (scope or {}).get("configured_output_cuts") or {}
    details = (r10 or {}).get("per_member") or {}
    results = []
    for story, uids in dependencies["story_columns"].items():
        st_reasons = story_blockers(dependencies, story)
        for combo in names:
            for direction in ("X", "Y"):
                codes = list(st_reasons)
                terms, elevations = [], []
                for uid in uids:
                    frame, grid = frames.get(uid) or {}, cuts.get(uid) or {}
                    try:
                        v_index, _ = _axis_indices(frame, direction)
                        if grid.get("status") != "REQUIRED_SUBSET_BOUND" or grid.get("offset_i_m") != 0.0:
                            raise ValueError("ALPHA_CONFIGURED_BOTTOM_CUT_UNVERIFIED")
                        bottom = [c for c in grid["cuts"] if c["object_station_m"] == 0.0]
                        if len(bottom) != 1:
                            raise ValueError("ALPHA_BOTTOM_CUT_AMBIGUOUS")
                        cut = bottom[0]
                        matching = [r for r in native_frame_force_rows(rowsets[uid], uid)
                            if r[4] == combo and r[5] == "Single Value" and r[6] == 0
                            and r[2] == cut["analysis_element_id"]
                            and abs(r[1] - cut["object_station_m"]) <= station_budget(r[1], cut["object_station_m"], grid["length_m"])
                            and abs(r[3] - cut["element_station_m"]) <= station_budget(r[3], cut["element_station_m"], grid["length_m"])]
                        if len(matching) != 1:
                            raise ValueError("ALPHA_SAME_CUT_FORCE_MISSING_OR_AMBIGUOUS")
                        target = matching[0]
                        row, component_rows = earthquake_row(
                            list(native_frame_force_rows(rowsets[uid], uid)), target,
                            seismic_basis["recipes"][combo], length=grid["length_m"])
                        k = 0 if direction == "X" else 1
                        shear = row[8]*frame["axes_global"][1][k] + row[9]*frame["axes_global"][2][k]
                        if not math.isfinite(shear):
                            raise ValueError("ALPHA_NONFINITE_SHEAR")
                        elevations.append(points[frame["point_i"]][2])
                        checks = []
                        for end in ("I", "J"):
                            js = [j for j in details.get(uid, {}).get("scwb_joints", ())
                                  if j.get("target_end") == end and j.get("direction") == direction]
                            if len(js) != 1:
                                raise ValueError("ALPHA_TWO_END_SCWB_OR_EXEMPTION_UNVERIFIED")
                            cr = [r for r in (js[0].get("engineer_selected_scwb") or {}).get("cases", ())
                                  if r.get("output_case") == combo]
                            signs = [r.get("rotation_sign") for r in cr]
                            if sorted(signs) != [-1, 1] or any(type(r.get("reference_satisfied")) is not bool for r in cr):
                                raise ValueError("ALPHA_SELECTED_TWO_SIGN_SCWB_UNRESOLVED")
                            checks.extend(r["reference_satisfied"] for r in cr)
                        terms.append({"member_id": uid, "source_cut": cut, "shear_kn": shear,
                                      "two_end_scwb_satisfied": all(checks), "source_row_key": list(row[:7]),
                                      "source_force_sha256": _digest(target), "earthquake_component_sha256": _digest(row),
                                      "earthquake_component_rows": component_rows})
                    except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
                        codes.append(uid + ":" + str(exc))
                if len(terms) != len(uids):
                    codes.append("ALPHA_FULL_STORY_POPULATION_INCOMPLETE")
                if elevations and max(elevations) - min(elevations) > 1e-9:
                    codes.append("ALPHA_COMMON_PHYSICAL_CUT_ELEVATION_UNVERIFIED")
                positive = any(t["shear_kn"] > 0 for t in terms)
                negative = any(t["shear_kn"] < 0 for t in terms)
                if positive and negative:
                    codes.append("ALPHA_COUNTERACTING_SHEARS_OUTSIDE_SUPPORTED_BRANCH")
                vik = math.fsum(abs(t["shear_kn"]) for t in terms)
                vis = math.fsum(abs(t["shear_kn"]) for t in terms if t["two_end_scwb_satisfied"])
                if vik <= 0:
                    codes.append("ALPHA_ZERO_DIRECTIONAL_SHEAR")
                record = {"story": story, "direction": direction, "combination": combo,
                          "expected_member_ids": list(uids), "terms": terms,
                          "eligible_member_ids": [t["member_id"] for t in terms if t["two_end_scwb_satisfied"]],
                          "reason_codes": sorted(set(codes)), "vis_kn": vis, "vik_kn": vik,
                          "low_axial_optional_credit_used": False}
                if not codes:
                    reference = evaluate_story_alpha_reference(vis_kn=vis, vik_kn=vik)
                    record.update(alpha=float(reference["alpha"]), factor=alpha_feedback_factor(reference),
                                  status="REANALYSIS_REQUIRED" if reference["classification_review_required"] else "QUALIFIED_REFERENCE")
                else:
                    record.update(alpha=None, factor=None, status="BLOCKED_INPUTS")
                results.append(record)
    status = ("BLOCKED_INPUTS" if not results or any(r["status"] == "BLOCKED_INPUTS" for r in results) else
              "REANALYSIS_REQUIRED" if any(r["status"] == "REANALYSIS_REQUIRED" for r in results) else "QUALIFIED_REFERENCE")
    return {"status": status, "reason_codes": sorted({c for r in results for c in r["reason_codes"]}),
            "cases": results, "seismic_shear_provenance": seismic_basis,
            "basis": "ORIGINAL_SIGNED_EARTHQUAKE_COMPONENT_COMMON_BOTTOM_CUT_NO_LOW_N_CREDIT"}


def build_demand_revision(source, cases, *, input_sha):
    """Absolute factors relative to captured vectors, never factors on prior results."""
    from .column_r10_live import _build_frame_catalog
    frames, _, _ = _build_frame_catalog(source)
    rows = ((source.get("column_axial") or {}).get("force_source") or {}).get("rowsets") or {}
    factors = {}
    seen = set()
    for case in cases:
        key = (case["story"], case["direction"], case["combination"])
        if key in seen or case.get("status") != "QUALIFIED_REFERENCE":
            raise ValueError("ALPHA_CASE_DUPLICATE_OR_UNQUALIFIED")
        seen.add(key)
        factor = case.get("factor")
        if type(factor) not in (int, float) or not math.isfinite(factor) or not 1 <= factor <= 1/0.70:
            raise ValueError("ALPHA_FACTOR_INVALID")
        if factor == 1:
            continue
        for uid in case["eligible_member_ids"]:
            v, m = _axis_indices(frames[uid], case["direction"])
            entry = factors.setdefault(uid, {}).setdefault(case["combination"], [1.0]*4)
            for index in (v, m):
                entry[(8,9,11,12).index(index)] = factor
    return _sealed({"schema": DEMAND_SCHEMA, "method": METHOD, "input_sha256": input_sha,
                    "source_payload_sha256": _digest(source), "factors": factors,
                    "base_rowset_sha256": {u: _digest(rows[u]) for u in factors},
                    "basis": "ABSOLUTE_ON_ORIGINAL_COMBINED_SIGNED_M_V_ONLY_N_AND_T_UNCHANGED"})


def revised_force_rows(rowset, uid, revision=None):
    rows = list(native_frame_force_rows(rowset, uid))
    if revision is None:
        return rows
    validate_record(revision, DEMAND_SCHEMA)
    factors = revision["factors"].get(uid, {})
    if factors and revision["base_rowset_sha256"].get(uid) != _digest(rowset):
        raise ValueError("ALPHA_DEMAND_BASE_ROWSET_CHANGED")
    out = []
    for row in rows:
        row = list(row)
        if row[4] in factors:
            if row[5] != "Single Value" or row[6] != 0:
                raise ValueError("ALPHA_UNSIGNED_OR_STEPPED_VECTOR_REJECTED")
            for i, factor in zip((8,9,11,12), factors[row[4]]):
                row[i] *= factor
                if not math.isfinite(row[i]):
                    raise ValueError("ALPHA_REVISED_DEMAND_NONFINITE")
        out.append(tuple(row))
    return out


def revised_pmm_member(member, source, revision):
    """R08 consumes revised raw moments and retains all seven-field native keys."""
    if not revision or member["member_id"] not in revision["factors"]:
        return member
    result = deepcopy(member)
    uid = member["member_id"]
    rowset = source["column_axial"]["force_source"]["rowsets"][uid]
    revised = {r[:7]: r for r in revised_force_rows(rowset, uid, revision)}
    for row in result.get("rows", ()):
        key = (uid, row["object_station_m"], row["analysis_element_id"], row["element_station_m"],
               row["combination"], row["step_type"], row["step_number"])
        native = revised[key]
        row["m2_knm"], row["m3_knm"] = native[11], native[12]
        # Baseline capacity numbers are not revised PMM evidence.
        row.pop("capacity", None); row.pop("utilization", None)
        row["status"] = "ALPHA_REVISED_INPUT_REQUIRES_SELECTED_PMM"
    result["design_demand_revision_sha256"] = revision["sha256"]
    return result


def run_bounded_feedback(*, initial, qualify, demand, rebuild, signature, feasible, max_iterations=MAX_ITERATIONS):
    """Bounded owner-driven iteration, explicit terminal states; no truthy success."""
    if type(max_iterations) is not int or not 1 <= max_iterations <= 32:
        raise ValueError("ALPHA_ITERATION_LIMIT_INVALID")
    state = initial
    current_factors = {}
    seen = set()
    trace = []
    affected = set()
    status = "NO_CONVERGENCE"
    qualification = None
    for index in range(max_iterations + 1):
        check = feasible(state)
        if check["status"] == "NO_FEASIBLE_CANDIDATE":
            status = check["status"]; break
        qualification = qualify(state)
        if qualification["status"] != "QUALIFIED_REFERENCE":
            status = qualification["status"]
            break
        revision = demand(qualification["cases"])
        target = revision["factors"]
        changed = sorted(u for u in set(target) | set(current_factors) if target.get(u) != current_factors.get(u))
        if check["status"] != "FEASIBLE_REFERENCE":
            status = check["status"]; break
        recheck = check.get("reselect_member_ids", [])
        changed = sorted(set(changed) | set(recheck))
        if not changed:
            status = "FIXED_POINT_REFERENCE" if check["status"] == "FEASIBLE_REFERENCE" else check["status"]
            break
        if index == max_iterations:
            status = "NO_CONVERGENCE"; break
        mark = _digest({"factors": target, "cages": signature(state), "reselect": recheck})
        if mark in seen:
            status = "NO_CONVERGENCE_CYCLE"; break
        seen.add(mark)
        state, actions = rebuild(state, revision, changed)
        affected.update(changed)
        trace.append({"iteration": index + 1, "demand_revision_sha256": revision["sha256"],
                      "changed_member_ids": changed, "actions": actions,
                      "case_evidence": qualification["cases"], "candidate_signature": signature(state)})
        current_factors = deepcopy(target)
    record = _sealed({"schema": SCHEMA, "method": METHOD, "status": status,
                      "iteration_count": len(trace), "max_iterations": max_iterations,
                      "affected_member_ids": sorted(affected), "trace": trace,
                      "final_qualification": qualification,
                      "final_demand_revision": state.get("revision"),
                      "feedback_consumed": status == "FIXED_POINT_REFERENCE",
                      "engineering_release": "NOT_READY", "formal_compliance": "NOT_PROVEN"})
    return state, record


def _candidate_signature(state):
    return {u: _digest({"section": asdict(c.section), "selected": c.selection.get("selected")})
            for u, c in sorted(state["cages"].items())}


def _feasibility(state):
    """Numerical reference feasibility, never engineering approval or source repair."""
    r10, r08 = state.get("r10") or {}, state.get("r08") or {}
    details, locals_ = r10.get("per_member") or {}, r08.get("per_member") or {}
    reselect = []
    blocked = []
    for uid in state["dependencies"]["members"]:
        selected = (details.get(uid) or {}).get("engineer_column_selection") or {}
        if selected.get("status") == "ENGINEER_COLUMN_SELECTION_NO_PASSING_CAGE":
            return {"status": "NO_FEASIBLE_CANDIDATE", "member_id": uid,
                    "scope": "SUPPORTED_CANDIDATE_FAMILY_AND_CURRENT_DEMAND_CONSTRAINTS"}
        if not selected.get("selected"):
            blocked.append(uid + ":SELECTED_CAGE_UNAVAILABLE"); continue
        pmm = (locals_.get(uid) or {}).get("magnified_selected_pmm") or {}
        if (pmm.get("status") not in ("MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN", "MAGNIFIED_PMM_EXCEEDS_CAPACITY")
                or type(pmm.get("global_beta_ii_factor")) not in (int, float)
                or not math.isfinite(pmm["global_beta_ii_factor"]) or pmm["global_beta_ii_factor"] < 1
                or pmm.get("evaluated_row_count") != pmm.get("expected_row_count")
                or pmm.get("resolved_row_count") != pmm.get("expected_row_count")
                or type(pmm.get("expected_row_count")) is not int or pmm["expected_row_count"] <= 0):
            blocked.append(uid + ":SELECTED_SECOND_ORDER_REFERENCE_UNRESOLVED"); continue
        if pmm["status"] == "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN":
            util = pmm.get("max_utilization")
            if type(util) not in (int, float) or not math.isfinite(util) or not 0 <= util <= 1 + 1e-6:
                blocked.append(uid + ":SELECTED_PMM_UTILIZATION_UNQUALIFIED"); continue
        if pmm["status"] == "MAGNIFIED_PMM_EXCEEDS_CAPACITY":
            reselect.append(uid)
        ve = ((details[uid].get("column_transverse_and_shear") or {}).get("engineer_capacity_shear_ve") or {})
        axes = ve.get("axes") or {}
        if set(axes) != {"V2", "V3"}:
            blocked.append(uid + ":SELECTED_CAPACITY_SHEAR_UNRESOLVED"); continue
        for axis_name, axis in axes.items():
            cases = axis.get("cases") or []
            expected = state.get("required_signed_combinations") or []
            observed = [c.get("combination") for c in cases]
            if (not cases or len(set(observed)) != len(observed)
                    or (expected and set(observed) != set(expected))):
                blocked.append(uid + ":CAPACITY_SHEAR_COMBINATION_COVERAGE_UNRESOLVED")
                continue
            for case in cases:
                nums = [case.get(k) for k in ("ve_scwb_scenario_kn", "vr_ts500_min_kn", "utilization_ts500")]
                if (any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in nums)
                        or not nums[1]):
                    blocked.append(uid + ":CAPACITY_SHEAR_CASE_UNRESOLVED"); continue
                stations = ((details[uid].get("column_transverse_and_shear") or {}).get("shear_stations") or [])
                vd = [abs(st["v2_kn" if axis_name == "V2" else "v3_kn"])
                      for st in stations if st["combination"] == case["combination"]]
                if vd and nums[0] < max(vd) - 1e-9:
                    reselect.append(uid)
            value = axis.get("max_utilization_ts500")
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                blocked.append(uid + ":SELECTED_SHEAR_NONFINITE")
            elif value > 1.0 + 1e-6:
                reselect.append(uid)
    return {"status": "NUMERIC_OR_DEPENDENCY_UNRESOLVED" if blocked else "FEASIBLE_REFERENCE",
            "reselect_member_ids": sorted(set(reselect)), "reason_codes": sorted(set(blocked))}


def _selection_constraints(state, pmm, changed):
    """Retain each native state's reference second-order moment vector, never maxima joins."""
    pmembers = {m["member_id"]: m for m in (pmm or {}).get("members", ())}
    extra_m, extra_v = {}, {}
    for uid in changed:
        local = ((state.get("r08") or {}).get("per_member") or {}).get(uid) or {}
        mag = local.get("magnified_selected_pmm") or {}
        # Previous iteration is a design constraint, not a multiplier on capture.
        if mag.get("status") == "MAGNIFIED_PMM_EXCEEDS_CAPACITY":
            base = {(r["combination"], r["object_station_m"], r["analysis_element_id"], r["element_station_m"]): r
                    for r in pmembers.get(uid, {}).get("rows", ())}
            for row in mag.get("rows", ()):
                key = (row.get("combination"), row.get("object_station_m"), row.get("analysis_element_id"), row.get("element_station_m"))
                original = base.get(key)
                if original is None or row.get("nd_kn") != original["nd_kn"]:
                    raise ValueError("ALPHA_SECOND_ORDER_CONSTRAINT_IDENTITY_UNRESOLVED")
                values = [row.get("magnified_m2_design_knm"), row.get("magnified_m3_design_knm")]
                if not all(type(v) in (float, int) and math.isfinite(v) for v in values):
                    raise ValueError("ALPHA_SECOND_ORDER_CONSTRAINT_UNRESOLVED")
                extra_m.setdefault(uid, []).append({"combination": key[0], "station_m": key[1],
                    "analysis_element_id": key[2], "element_station_m": key[3], "nd_kn": original["nd_kn"],
                    "m2_knm": values[0], "m3_knm": values[1]})
        det = ((state.get("r10") or {}).get("per_member") or {}).get(uid) or {}
        trans = det.get("column_transverse_and_shear") or {}
        axes = (trans.get("engineer_capacity_shear_ve") or {}).get("axes") or {}
        for axis, result in axes.items():
            if (result.get("max_utilization_ts500") or 0) <= 1 + 1e-6:
                continue
            for case in result.get("cases", ()):
                for st in trans.get("shear_stations", ()):
                    if st["combination"] == case["combination"]:
                        extra_v.setdefault(uid, []).append({"nd_kn": st["nd_kn"],
                            "v2_kn": case["ve_scwb_scenario_kn"] if axis == "V2" else 0.0,
                            "v3_kn": case["ve_scwb_scenario_kn"] if axis == "V3" else 0.0})
    return extra_m, extra_v



def _story_summary(qualification):
    """Project the qualified same-cut calculation; do not recompute a second alpha."""
    grouped = {}
    for case in qualification["cases"]:
        grouped.setdefault((case["story"], case["direction"]), []).append(case)
    stories = []
    for (story, direction), cases in sorted(grouped.items()):
        complete = all(c["alpha"] is not None for c in cases)
        worst = min(cases, key=lambda c: c["alpha"]) if complete else None
        alpha = worst["alpha"] if worst else None
        action = ("PARTIAL_STORY_SCOPE_UNKNOWN_OTHER_COLUMNS" if alpha is None else
                  "STORY_SCWB_BELOW_0_70_SYSTEM_R_AND_DUCTILITY_REVIEW_REQUIRED" if alpha < .7 else
                  "AMPLIFY_COLUMN_DEMANDS_BY_1_OVER_ALPHA" if alpha < 1 else "NONE")
        stories.append({"story": story, "direction": direction,
            "story_column_count": len(cases[0]["expected_member_ids"]),
            "evaluated_column_count": len(cases[0]["expected_member_ids"]) if complete else None,
            "denominator_status": "FULL_STORY_COLUMN_DENOMINATOR",
            "governing_combination": worst["combination"] if worst else None,
            "governing_alpha_i": alpha, "governing_band": "AT_OR_ABOVE_0P70" if alpha is not None and alpha >= .7 else "UNRESOLVED_OR_BELOW",
            "moment_magnification_factor_7_3_6_2": worst["factor"] if worst else None,
            "demand_feedback_action": action, "cases": [dict(c,alpha_i=c["alpha"]) for c in cases]})
    values = [c["alpha"] for c in qualification["cases"] if c["alpha"] is not None]
    factors = [c["factor"] for c in qualification["cases"] if c["factor"] is not None]
    return {"schema": "tbdy.next.story-alpha-7-3-6.v1", "method": METHOD,
            "selection_basis": "ALGORITHM_SELECTED_CANDIDATE_SCWB",
            "denominator_scope": "FULL_STORY_COLUMN_DENOMINATOR", "stories": stories,
            "minimum_resolved_alpha_i": min(values, default=None),
            "max_column_demand_magnification_1_over_alpha": max(factors, default=None),
            "any_story_below_0_70": any(v < .7 for v in values), "formal_compliance": "NOT_PROVEN"}


def run_alpha_design_iteration(*, source, geometry, axial, pmm, extra, scope, dependencies,
                               r10, r08, cages, beam, global_pdelta, input_sha):
    """Existing pipeline's bounded substage; rebuild only dirty member/joint owners."""
    from .column_r10_live import project_column_r10_live
    from .column_r08_local_live import project_column_r08_local_live
    from .design_scenario import selected_candidate_ledger

    initial = {"r10": r10, "r08": r08, "cages": cages, "dependencies": dependencies,
               "revision": None, "additional_demands": {}, "additional_shears": {},
               "required_signed_combinations": [c["name"] for c in (axial or {}).get("combination_plan", {}).get("combinations", ())
                                                if c.get("force_semantics") == "STATIC_SIGNED_VECTOR"]}

    def qualify(state):
        return qualify_story_alpha(source, axial, scope, state["dependencies"], state["r10"])

    def rebuild(state, revision, changed):
        plan = deepcopy(state["dependencies"])
        for uid in changed:
            plan["members"][uid]["demand_revision_sha256"] = _digest({
                "base": dependencies["members"][uid]["demand_revision_sha256"],
                "absolute_factors": revision["factors"].get(uid, {})})
        extra_m, extra_v = _selection_constraints(state, pmm, changed)
        # Monotone reference constraints avoid forgetting a prior failed local check.
        more_m, more_v = deepcopy(state["additional_demands"]), deepcopy(state["additional_shears"])
        for uid in changed:
            more_m[uid] = list({_digest(v): v for v in more_m.get(uid, []) + extra_m.get(uid, [])}.values())
            more_v[uid] = list({_digest(v): v for v in more_v.get(uid, []) + extra_v.get(uid, [])}.values())
        new_cages = {}
        next_r10 = project_column_r10_live(
            source, geometry, axial, pmm, extra, beam_live=beam, dependency_plan=plan,
            selected_cages_out=new_cages, demand_revision=revision,
            previous_result=state["r10"], previous_cages=state["cages"], reselect_member_ids=changed,
            additional_demands=more_m, additional_shears=more_v)
        plan = next_r10["member_dependencies"]
        next_r08 = project_column_r08_local_live(
            source, geometry, axial, pmm, global_pdelta, r10_live=next_r10, selected_cages=new_cages,
            dependency_plan=plan, demand_revision=revision, previous_result=state["r08"], recompute_member_ids=changed)
        actions = {**next_r10.get("alpha_recalculation", {}), "r08_member_ids": changed,
                   "beam_owner_reexecuted": False,
                   "second_order_constraint_count": sum(map(len, more_m.values())),
                   "capacity_shear_constraint_count": sum(map(len, more_v.values()))}
        return {"r10": next_r10, "r08": next_r08, "cages": new_cages, "dependencies": plan,
                "revision": revision, "additional_demands": more_m, "additional_shears": more_v,
                "required_signed_combinations": state["required_signed_combinations"]}, actions

    state, record = run_bounded_feedback(
        initial=initial, qualify=qualify,
        demand=lambda cases: build_demand_revision(source, cases, input_sha=input_sha),
        rebuild=rebuild, signature=_candidate_signature, feasible=_feasibility)
    final_candidates = selected_candidate_ledger(scope, state["cages"], state["r10"], input_sha=input_sha)
    record = _sealed({**{k: v for k, v in record.items() if k != "sha256"},
        "input_sha256": input_sha, "source_payload_sha256": _digest(source),
        "expected_member_ids": sorted(dependencies["members"]),
        "final_candidate_signature": _candidate_signature(state),
        "final_candidate_ledger_sha256": _digest(final_candidates),
        "final_feasibility": _feasibility(state),
        "selection_constraints_policy": "MONOTONE_SAME_RUN_REFERENCE_CONSTRAINTS_NOT_GLOBAL_OPTIMALITY",
        "formula_owner": "column_engine.story_alpha", "engineering_authority": "DENIED"})
    if state["r10"] is not None:
        if (record.get("final_qualification") or {}).get("cases"):
            state["r10"]["story_alpha"] = _story_summary(record["final_qualification"])
        state["r10"]["alpha_iteration"] = record
    return state, final_candidates, record
