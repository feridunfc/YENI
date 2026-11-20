"""Signed supplementary static story calculations from the existing capture and owners."""
from collections import defaultdict
from math import fsum, isclose

from ..column_engine.beam_references import station_budget
from ..column_engine.scwb_kernel import low_axial_limit_kn
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.story_alpha import alpha_feedback_factor, evaluate_story_alpha_reference
from .alpha_iteration import _axis_indices
from .column_pmm import _required_cut_coverage
from .column_r10_live import _build_frame_catalog
from .demand_sources import _verified_support
from .design_dependencies import _topology
from .design_scenario import _digest
from .mixed_demands import _static_roles, linear_coefficients, native_graph
from .scwb_axial import _configured_end


def _signed_rows(rowset, uid, names):
    rows = defaultdict(dict)
    for row in native_frame_force_rows(rowset, uid):
        if row[4] in names:
            if row[5] not in ("Single Value", "") or row[6] != 0 or row[:4] in rows[row[4]]:
                raise ValueError("STATIC_REFERENCE_STEP_OR_CUT_AMBIGUOUS")
            rows[row[4]][row[:4]] = row
    if rows.keys() != set(names):
        raise ValueError("STATIC_REFERENCE_CASE_ROWS_MISSING")
    return rows


def _member_witness(uid, case, gravity, supplemental, assigned, scope, frame, section):
    reference = supplemental[case]
    cuts = set(reference)
    observed = [*assigned.values(), *(supplemental[n] for terms in gravity.values() for n in terms)]
    if any(set(c) != cuts for c in observed):
        raise ValueError("STATIC_REFERENCE_SAME_NATIVE_CUTS_REQUIRED")
    grid = scope["configured_output_cuts"][uid]
    key, length = _configured_end(scope, frame, "I")
    coverage = _required_cut_coverage(reference.values(), grid)
    if (grid["offset_i_m"] != 0 or key[1] != 0 or not coverage["required_count"]
            or coverage["matched_count"] != coverage["required_count"]):
        raise ValueError("STATIC_REFERENCE_CONFIGURED_CUTS_INCOMPLETE")
    bottom = [cut for cut in cuts if cut[2] == key[2]
              and abs(cut[1]-key[1]) <= station_budget(cut[1], key[1], length)
              and abs(cut[3]-key[3]) <= station_budget(cut[3], key[3], length)]
    if len(bottom) != 1:
        raise ValueError("STATIC_REFERENCE_BOTTOM_NOT_UNIQUE")
    limit = low_axial_limit_kn(section["gross_area_mm2"], section["fck_mpa"])
    worst = None
    for name, terms in gravity.items():
        for cut, quake in reference.items():
            p_g = assigned[name][cut][7]
            replay = fsum(float(coef) * supplemental[leaf][cut][7] for leaf, coef in terms.items())
            p_e = quake[7]
            nd = -p_g + abs(p_e)
            if (not isclose(replay, p_g, rel_tol=1e-12, abs_tol=1e-9)
                    or (nd <= limit) != (-replay + abs(p_e) <= limit)):
                raise ValueError("STATIC_REFERENCE_GRAVITY_AXIAL_REPLAY_CONFLICT")
            if worst is None or nd > worst["max_nd_kn"]:
                worst = {"gravity": name, "earthquake_factor": -1 if p_e > 0 else 1,
                         "cut": list(cut), "gravity_p_kn": p_g, "earthquake_p_kn": p_e, "max_nd_kn": nd}
    row = reference[bottom[0]]
    return {"member_id": uid, "source_cut": list(bottom[0]), "step_type": row[5], "step_number": row[6],
            "v2_kn": row[8], "v3_kn": row[9], "cut_count": len(cuts), "limit_kn": limit,
            "numerator_eligible": worst["max_nd_kn"] <= limit, "governing_axial": worst}


def _story_reference(story, direction, case, ids, frames, points, witnesses, failures):
    reasons, terms, elevations = [], [], []
    index = 0 if direction == "X" else 1
    for uid in ids:
        try:
            if uid in failures:
                raise ValueError(failures[uid])
            frame, term = frames[uid], witnesses[uid]
            _axis_indices(frame, direction)
            e2, e3 = frame["axes_global"][1:]
            shear = fsum((term["v2_kn"] * e2[index], term["v3_kn"] * e3[index]))
            elevations.append(points[frame["point_i"]][2])
            terms.append({**term, "local_projection": [e2[index], e3[index]], "signed_shear_kn": shear})
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            reasons.append(uid + ":" + str(exc))
    complete = bool(ids) and len(terms) == len(ids)
    if not complete or max(elevations, default=0) - min(elevations, default=0) > 1e-9:
        reasons.append("STATIC_REFERENCE_COMMON_CUT_POPULATION_INCOMPLETE")
        complete = False
    signed = fsum(t["signed_shear_kn"] for t in terms) if complete else None
    if complete and (not signed or any(t["signed_shear_kn"] * signed < 0 for t in terms)):
        reasons.append("STATIC_REFERENCE_ZERO_OR_COUNTERACTING_SHEARS")
    if any(not t["numerator_eligible"] for t in terms):
        reasons.append("STATIC_REFERENCE_HIGH_N_REQUIRES_TWO_END_CAPACITY_CHECKS")
    eligible = [t for t in terms if t["numerator_eligible"]]
    result = {"story": story, "direction": direction, "case": case, "expected_member_ids": ids,
              "expected_count": len(ids), "bound_count": len(terms), "credited_count": len(eligible),
              "terms": terms, "signed_total_kn": signed, "reason_codes": sorted(set(reasons)),
              "vis_kn": None, "vik_kn": None, "alpha": None, "factor": None, "status": "BLOCKED_INPUTS"}
    if not reasons:
        vik = abs(signed)
        vis = abs(fsum(t["signed_shear_kn"] for t in eligible))
        check = evaluate_story_alpha_reference(vis_kn=vis, vik_kn=vik)
        factor = alpha_feedback_factor(check)
        result.update(vis_kn=vis, vik_kn=vik, alpha=float(check["alpha"]), factor=factor, status="SIGNED_STATIC_REFERENCE")
        if factor == 1.0:
            residual = max(abs(t["signed_shear_kn"] * factor - t["signed_shear_kn"]) for t in terms)
            result["identity_factor_check"] = {"initial_factor": 1.0, "calculated_factor": factor,
                                               "evaluations": 1, "maximum_shear_change_kn": residual,
                                               "fixed": residual == 0.0}
    return result


def supplementary_story_reference(source, axial, scope, dependencies):
    plan = (axial or {}).get("combination_plan") or {}
    names = plan.get("reference_static_cases")
    if not names:
        return None
    result = {"basis": "EACH_ASSIGNED_GRAVITY_PLUS_OR_MINUS_ONE_SUPPLEMENTARY_STATIC_CASE",
              "force_semantics": "STATIC_SIGNED_VECTOR", "earthquake_factors": [-1, 1],
              "credit_basis": "7.3.6.1_OPTIONAL_LOW_AXIAL_ALL_OBSERVED_AND_CONFIGURED_CUTS",
              "assigned_to_design": False, "cases": [], "reason_codes": []}
    try:
        support_plan, support = _verified_support(source, plan)
        tables, catalog, graph = native_graph(source)
        groups = plan["design_assignment"]["groups"]
        roles = {c["name"]: c["force_semantics"] for c in plan["combinations"]}
        gravity = {n: linear_coefficients(n, graph, catalog) for n in groups["gravity"]}
        primitives = {n for terms in gravity.values() for n in terms}
        kinds = _static_roles(tables, primitives | set(names), catalog)
        definitions = tables["Load Case Definitions - Linear Static"]["rows"]
        settings = {(row["StiffType"], row["NonlinCase"], row["MassSource"]) for row in definitions
                    if row["Name"] in kinds}
        if (not gravity or any(not terms or roles[n] != "STATIC_SIGNED_VECTOR" for n, terms in gravity.items())
                or names != support_plan["reference_static_cases"] or any(kinds[n] != "EARTHQUAKE" for n in names)
                or any(kinds[n] != "NON_EARTHQUAKE" for n in primitives) or len(settings) != 1
                or not all(next(iter(settings)))):
            raise ValueError("STATIC_REFERENCE_ACTION_OR_STIFFNESS_BASIS_UNQUALIFIED")
        result["gravity_combinations"] = {n: {k: str(v) for k, v in terms.items()} for n, terms in gravity.items()}
        result["common_static_settings"] = list(next(iter(settings)))
        frames, _, blockers = _topology(source)
        _, points, _ = _build_frame_catalog(source)
        roster = defaultdict(list)
        for uid, frame in frames.items():
            if frame["type"] == "Column":
                roster[frame["story"]].append(uid)
        stories = {s: sorted(v) for s, v in sorted(roster.items())}
        original = source["column_axial"]["force_source"]
        sections = {r["element_id"]: r for r in axial["columns"]}
        during = original.get("output_selection_during") or {}
        requested = {n for group in groups.values() for n in group}
        if (blockers or not stories or stories != dependencies["story_columns"]
                or not scope.get("input_sha256") or scope["input_sha256"] != dependencies.get("input_sha256")
                or dependencies.get("source_payload_sha256") != _digest(source)
                or scope.get("dependency_blockers") or original.get("units_code") != 6
                or original.get("api") != "Results.FrameForce" or original.get("item_type") != "ObjectElm"
                or not original.get("output_selection_before") or original["output_selection_before"] != original.get("output_selection_after")
                or any(during.get("cases", {}).values()) or {n for n,v in during.get("combos", {}).items() if v} != requested):
            raise ValueError("STATIC_REFERENCE_ORIGINAL_SOURCE_OR_POPULATION_UNBOUND")
        result["input_sha256"] = scope["input_sha256"]
        result["earthquake_partition"] = {n: {"quake_only_case": n, "coefficient": 1,
                                             "case_guid": catalog[n]["guid"]} for n in names}
        for case in names:
            witnesses, failures = {}, {}
            for ids in stories.values():
                for uid in ids:
                    try:
                        supplemental = _signed_rows(support["rowsets"][uid], uid, primitives | {case})
                        assigned = _signed_rows(original["rowsets"][uid], uid, gravity)
                        witnesses[uid] = _member_witness(uid, case, gravity, supplemental, assigned, scope,
                                                         frames[uid], sections[uid])
                    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                        failures[uid] = str(exc)
            for story, ids in stories.items():
                for direction in ("X", "Y"):
                    result["cases"].append(_story_reference(story, direction, case, ids, frames, points, witnesses, failures))
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        result["reason_codes"].append(str(exc))
    return result
