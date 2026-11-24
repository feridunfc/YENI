"""Bind the TBDY 7.3.5.3(a) decision to native column ends for R10."""
from collections import defaultdict
from math import isclose, isfinite

from ..column_engine.beam_references import station_budget
from ..column_engine.csi_geometry import physical_column_side_at_joint
from ..column_engine.native_archive import BankError
from ..column_engine.scwb_kernel import low_axial_limit_kn
from ..column_engine.source_bank import native_frame_force_rows
from .column_pmm import _oriented_element_chain
from .design_dependencies import _topology
from .design_scenario import _digest
from .mixed_demands import SCHEMA as MIXED_SCHEMA, SPECTRAL_METHOD, verify_combined_seismic_axial_cases


def qualified_interval_ratio(joint):
    """Verify all recorded family/sway outcomes before projecting the minimum."""
    decision = joint.get("low_axial_exception") or {}
    interval = joint.get("seismic_axial_interval_check") or {}
    names = decision.get("seismic_combinations") or []
    cases = interval.get("cases") or []
    if (decision.get("status") != "LOW_AXIAL_LIMIT_EXCEEDED" or decision.get("exempt") is not False
            or not decision.get("input_sha256") or interval.get("input_sha256") != decision["input_sha256"]
            or interval.get("status") != "SCWB_EQ_7_3_INTERVAL_SUFFICIENT" or interval.get("sufficient") is not True
            or not names or len(set(names)) != len(names) or len(cases) != len(names)
            or {c.get("combination") for c in cases} != set(names)
            or interval.get("evaluated_checks") != 2*len(names) or interval.get("expected_checks") != 2*len(names)):
        return None
    ratios = []
    for case in cases:
        sways = case.get("sways") or []
        if len(sways) != 2 or {w.get("rotation_sign") for w in sways} != {-1, 1}:
            return None
        for sway in sways:
            ratio = sway.get("ratio_lower")
            if sway.get("sufficient") is not True or type(ratio) not in (float, int) or not isfinite(ratio) or ratio <= 1:
                return None
            ratios.append(ratio)
    minimum = min(ratios)
    return minimum if minimum == interval.get("minimum_ratio_lower") else None


def _assigned_end_disposition(frame, end, direction, frames, points, plan, summaries, names):
    """Classify one expected frame end from its frozen connectivity and R10 results."""
    from .column_r10_live import _parallel
    uid = frame["frame_id"]
    jid = frame["point_i" if end == "I" else "point_j"]
    other_end = frame["point_j" if end == "I" else "point_i"]
    physical_column_side_at_joint(points.get(jid), points.get(other_end))
    joint = plan["joints"][jid]
    if (not joint.get("execution_allowed") or uid not in joint["column_ids"]
            or plan["members"][uid]["joint_ids"] != [frame["point_i"], frame["point_j"]]):
        raise ValueError("STORY_JOINT_DEPENDENCIES_UNRESOLVED")
    beams = joint["beam_ends"]
    x, y = [1., 0., 0.], [0., 1., 0.]
    vec = x if direction == "X" else y
    aligned = []
    for beam in beams:
        b = frames[beam["member_id"]]
        if (b["type"] != "Beam" or not b.get("axes_global")
                or b["point_i" if beam["end"] == "I" else "point_j"] != jid
                or not any(_parallel(b["axes_global"][0], v) for v in (x, y))):
            raise ValueError("STORY_BEAM_AXIS_OR_END_UNVERIFIED")
        if _parallel(b["axes_global"][0], vec):
            aligned.append(b["frame_id"])
    if not aligned:
        return "NO_FRAME_BEAM_AT_NODE" if not beams else "NO_FRAME_BEAM_IN_DIRECTION"
    columns = set(joint["column_ids"])
    sides = []
    for cid in columns:
        col = frames[cid]
        if col["type"] != "Column" or jid not in (col["point_i"], col["point_j"]):
            raise ValueError("STORY_COLUMN_END_NOT_BOUND")
        other = col["point_j"] if col["point_i"] == jid else col["point_i"]
        sides.append(physical_column_side_at_joint(points[jid], points[other]))
    if sides == ["LOWER"]:
        return "COLUMN_DOES_NOT_CONTINUE_ABOVE_7_3_5_3_B"
    matches = [j for j in summaries if j.get("target_member_id") == uid and j.get("joint_id") == jid
               and j.get("target_end") == end and j.get("direction") == direction]
    if sorted(sides) != ["LOWER", "UPPER"] or len(matches) != 1:
        raise ValueError("ASSIGNED_DIRECTIONAL_JOINT_RESULT_UNBOUND")
    j = matches[0]
    decision = j.get("low_axial_exception") or {}
    if (decision.get("input_sha256") != plan["input_sha256"] or decision.get("seismic_combinations") != names
            or decision.get("reasons") or set(j.get("column_ids", ())) != columns
            or set(j.get("beam_ids", ())) != set(aligned)
            or {e.get("member_id") for e in decision.get("column_ends", ())} != columns):
        raise ValueError("ASSIGNED_DIRECTIONAL_JOINT_SOURCE_CONFLICT")
    if decision.get("status") == "EXEMPT_LOW_AXIAL" and decision.get("exempt") is True:
        for item in decision["column_ends"]:
            limit = low_axial_limit_kn(item["gross_area_mm2"], item["fck_mpa"])
            nd = item["seismic_nd_intervals_kn"]
            if (set(nd) != set(names) or item["limit_kn"] != limit or
                    any(len(pair) != 2 or not all(isfinite(v) for v in pair)
                        or not pair[0] <= pair[1] <= limit for pair in nd.values())):
                raise ValueError("STORY_LOW_AXIAL_BOUND_CONFLICT")
        return "EXEMPT_LOW_AXIAL"
    if qualified_interval_ratio(j) is not None:
        return "EQ_7_3_INTERVAL_SUFFICIENT"
    raise ValueError("ASSIGNED_EQ_7_3_REQUIRES_FURTHER_EVALUATION")


def assigned_story_applicability(source, scope, plan, r10, names):
    """Check whether a story needs the 7.3.6 alternative before requesting signed shears."""
    from .frame_geometry import build_frame_catalog
    from .design_dependencies import story_blockers
    request = (source.get("column_axial") or {}).get("request") or {}
    if (request.get("pmm_member") != "ALL" or not plan or not r10 or not scope or not names or not scope.get("input_sha256")
            or scope["input_sha256"] != plan.get("input_sha256") or plan.get("source_payload_sha256") != _digest(source)
            or plan.get("global_blockers") or plan.get("topology_blockers") or not plan.get("all_member_inputs_bound")
            or r10.get("member_dependencies") != plan):
        return []
    frames, points, graph = build_frame_catalog(source)
    expected = defaultdict(list)
    for uid, frame in frames.items():
        if frame["type"] == "Column":
            expected[frame["story"]].append(uid)
    roster = {story: sorted(ids) for story, ids in expected.items()}
    if (not roster or roster != plan.get("story_columns") or set(plan["members"]) != {u for ids in roster.values() for u in ids}
            or any(m.get("selected_candidate_bound") is not True for m in plan["members"].values())):
        return []
    for jid, incident in graph["adjacency"].items():
        columns = sorted(r["frame_id"] for r in incident if r["type"] == "Column")
        if columns:
            joint = plan["joints"].get(jid) or {}
            beams = sorted((r["frame_id"], r["end"]) for r in incident if r["type"] == "Beam")
            if (joint.get("column_ids") != columns or
                    [(b["member_id"], b["end"]) for b in joint.get("beam_ends", ())] != beams):
                return []
    rows = []
    for story, ids in sorted(roster.items()):
        for direction in ("X", "Y"):
            reasons = list(story_blockers(plan, story))
            ends = []
            for uid in ids:
                frame = frames[uid]
                for end, jid in (("I", frame["point_i"]), ("J", frame["point_j"])):
                    try:
                        summaries = r10["per_member"][uid]["scwb_joints"]
                        status = _assigned_end_disposition(frame, end, direction, frames, points, plan, summaries, names)
                    except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
                        status = "UNRESOLVED"
                        reasons.append(f"{uid}:{end}:{exc}")
                    ends.append({"member_id": uid, "end": end, "joint_id": jid, "disposition": status})
            rows.append({"story": story, "direction": direction, "expected_member_ids": ids, "ends": ends,
                         "input_sha256": plan["input_sha256"], "assigned_seismic_combinations": names,
                         "status": "UNRESOLVED" if reasons else "ALTERNATIVE_NOT_REQUIRED",
                         "reason_codes": sorted(set(reasons)), "alpha": None, "vis_kn": None, "vik_kn": None,
                         "applied_demand_factor": None if reasons else 1.0})
    return rows


def _configured_end(scope, frame, end):
    uid = frame["frame_id"]
    mesh = scope["analysis_mesh"]["members"].get(uid, {})
    grid = scope["configured_output_cuts"].get(uid, {})
    if not mesh.get("roster_bound") or grid.get("status") != "REQUIRED_SUBSET_BOUND":
        raise BankError("SCWB_CONFIGURED_COLUMN_END_UNBOUND")
    chain = _oriented_element_chain(mesh["expected_analysis_element_ids"], mesh["analysis_element_end_joints"],
                                    frame["point_i"], frame["point_j"])
    if not chain:
        raise BankError("SCWB_COLUMN_ANALYSIS_ENDS_UNBOUND")
    length = grid["length_m"]
    obj = grid["offset_i_m"] if end == "I" else length - grid["offset_j_m"]
    elm = chain[0][0 if end == "I" else -1]
    cuts = [cut for cut in grid["cuts"] if cut["analysis_element_id"] == elm and
            abs(cut["object_station_m"] - obj) <= station_budget(cut["object_station_m"], obj, length)]
    if len(cuts) != 1:
        raise BankError("SCWB_CONFIGURED_COLUMN_END_MISSING_OR_AMBIGUOUS")
    cut = cuts[0]
    return (uid, cut["object_station_m"], elm, cut["element_station_m"]), length


def _spectral_bounds(rows, pairs, limit):
    if len(rows) != 2 or {r[5] for r in rows} != {"Max", "Min"} or rows[0][:4] != rows[1][:4]:
        raise BankError("SCWB_TWO_SPECTRAL_EXTREMA_REQUIRED")
    if len(pairs) != 1 or pairs[0]["status"] != "SAME_SOURCE_COMPONENT_REPLAY_MATCH":
        raise BankError("SCWB_SAME_SOURCE_AXIAL_REPLAY_REQUIRED")
    cuts = [c for c in pairs[0]["cuts"] if tuple(c["native_cut"]) == rows[0][:4] and c["configured_required_cut"]]
    if len(cuts) != 1 or cuts[0]["primitive_replay"]["status"] != "NUMERICAL_MATCH":
        raise BankError("SCWB_COLUMN_END_AXIAL_REPLAY_UNRESOLVED")
    by_step = {row[5]: -row[7] for row in rows}  # ETABS P is negative in compression.
    nd = [by_step["Max"], by_step["Min"]]
    if nd[0] > nd[1]:
        raise BankError("SCWB_AXIAL_BOUNDS_REVERSED")
    for bounds in (cuts[0]["nd_bounds_kn"], cuts[0]["primitive_replay"]["nd_bounds_kn"]):
        if len(bounds) != 2 or not all(isclose(a, b, abs_tol=1e-9, rel_tol=1e-12) for a, b in zip(nd, bounds)):
            raise BankError("SCWB_COLUMN_END_AXIAL_BOUNDS_CONFLICT")
        if (bounds[1] <= limit) != (nd[1] <= limit):
            raise BankError("SCWB_AXIAL_THRESHOLD_STRADDLED_BY_REPLAY")
    return nd


def _column_end_axial(joint, frame, end, points, scope, section, rowset, semantics, seismic, pairs):
    uid = frame["frame_id"]
    first, last = frame["point_i"], frame["point_j"]
    if end not in ("I", "J") or joint != (first if end == "I" else last):
        raise BankError("SCWB_PHYSICAL_END_IDENTITY_CONFLICT")
    side = physical_column_side_at_joint(points.get(joint), points.get(last if end == "I" else first))
    key, length = _configured_end(scope, frame, end)
    limit = low_axial_limit_kn(section.get("gross_area_mm2"), section.get("fck_mpa"))
    grouped = defaultdict(list)
    for row in native_frame_force_rows(rowset, uid):
        if (row[2] == key[2] and abs(row[1] - key[1]) <= station_budget(row[1], key[1], length)
                and abs(row[3] - key[3]) <= station_budget(row[3], key[3], length)):
            grouped[row[4]].append(row)
    intervals = {}
    other_unresolved = {}
    for name, role in semantics.items():
        sample = grouped[name]
        try:
            if not sample or any(r[6] != 0 for r in sample):
                raise BankError("SCWB_ASSIGNED_ZERO_STEP_END_MISSING")
            if role == "SCALAR_COMPONENT_ENVELOPE":
                intervals[name] = _spectral_bounds(sample, pairs[uid, name], limit)
            elif role == "STATIC_SIGNED_VECTOR" and len(sample) == 1 and sample[0][5] in ("", "Single Value"):
                intervals[name] = [-sample[0][7], -sample[0][7]]
            else:
                raise BankError("SCWB_ASSIGNED_END_FORCE_UNSUPPORTED_OR_AMBIGUOUS")
        except BankError as exc:
            if name in seismic:
                raise BankError(f"{exc}:{name}") from exc
            other_unresolved[name] = str(exc)
    maxima = {name: bounds[1] for name, bounds in intervals.items()}
    governing = None if other_unresolved else max(maxima, key=maxima.get)
    governing_seismic = max(seismic, key=maxima.get)
    return {"member_id": uid, "physical_side": side, "end": end, "configured_cut": list(key),
            "gross_area_mm2": section["gross_area_mm2"], "fck_mpa": section["fck_mpa"], "limit_kn": limit,
            "nd_max_by_combination_kn": maxima, "seismic_nd_intervals_kn": {n: intervals[n] for n in sorted(seismic)},
            "other_unresolved_combinations": other_unresolved,
            "governing_combination": governing, "max_nd_kn": maxima.get(governing),
            "governing_seismic_combination": governing_seismic, "max_seismic_nd_kn": maxima[governing_seismic]}


def joint_low_axial_decisions(source, axial, scope, mixed, dependency_plan, frames, points, adjacency,
                              seismic, *, input_sha):
    """Use assigned combinations at the two physical ends. Axial bounds need no concurrent moment or shear."""
    plan = axial.get("combination_plan") or {}
    if scope is None or plan.get("source") != "ASSIGNED_DESIGN":
        return {}
    assigned = (plan.get("design_assignment") or {}).get("groups") or {}
    expected = {name for group in assigned.values() for name in group}
    combos = plan.get("combinations") or []
    semantics = {row["name"]: row.get("force_semantics") for row in combos}
    force = (source.get("column_axial") or {}).get("force_source") or {}
    error = None
    if not input_sha or scope.get("input_sha256") != input_sha or scope.get("dependency_blockers"):
        error = "SCWB_INPUT_SCOPE_UNVERIFIED"
    elif plan.get("blockers") or not seismic or expected != semantics.keys() or len(combos) != len(semantics):
        error = "SCWB_ASSIGNED_COMBINATIONS_UNBOUND"
    elif (force.get("schema") != "tbdy.next.etabs-frame-force-source.v1" or force.get("api") != "Results.FrameForce"
          or force.get("units_code") != 6):
        error = "SCWB_NATIVE_FORCE_SOURCE_OR_UNITS_UNVERIFIED"
    else:
        try:
            verify_combined_seismic_axial_cases(source, seismic, semantics)
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            error = str(exc)
    pairs = defaultdict(list)
    if not error and "SCALAR_COMPONENT_ENVELOPE" in semantics.values():
        source_hash = dependency_plan["source_payload_sha256"] if dependency_plan else _digest(source)
        if (not mixed or mixed.get("schema") != MIXED_SCHEMA or mixed.get("method") != SPECTRAL_METHOD
                or mixed.get("input_sha256") != input_sha or mixed.get("source_payload_sha256") != source_hash
                or mixed.get("sha256") != _digest({k: v for k, v in mixed.items() if k != "sha256"})):
            if any(semantics[name] == "SCALAR_COMPONENT_ENVELOPE" for name in seismic):
                error = "SCWB_SAME_SOURCE_AXIAL_REPLAY_REQUIRED"
        else:
            for row in mixed["rows"]:
                pairs[row["member_id"], row["combination"]].append(row)
    topology_errors = dependency_plan["topology_blockers"] if dependency_plan else _topology(source)[2]
    sections = {c["element_id"]: c for c in axial.get("columns", ())}
    results = {}
    for joint, incident in adjacency.items():
        if not any(item["type"] == "Beam" for item in incident):
            continue
        cols = [item for item in incident if item["type"] == "Column"]
        if not cols:
            continue
        decision = {"clause": "TBDY 7.3.5.3(a)", "input_sha256": input_sha, "status": "UNRESOLVED",
                    "basis": "MAX_ASSIGNED_COMBINED_SEISMIC_ND_AT_CONFIGURED_COLUMN_ENDS",
                    "exempt": None, "assigned_combinations": sorted(expected), "seismic_combinations": sorted(seismic),
                    "column_ends": [], "reasons": []}
        results[joint] = decision
        if topology_errors:
            decision["reasons"] = list(topology_errors)
            continue
        if len(cols) != 2 or len({item["frame_id"] for item in cols}) != 2:
            decision["status"] = "NOT_A_TWO_COLUMN_JOINT"
            continue
        if dependency_plan is not None:
            expected_joint = dependency_plan["joints"].get(joint) or {}
            if set(expected_joint.get("column_ids", ())) != {item["frame_id"] for item in cols}:
                decision["reasons"].append("SCWB_EXPECTED_COLUMN_PAIR_UNBOUND")
                continue
            if expected_joint.get("source_blockers"):
                decision["reasons"].extend(expected_joint["source_blockers"])
                continue
        if error:
            decision["reasons"].append(error)
            continue
        for item in cols:
            uid = item["frame_id"]
            try:
                result = _column_end_axial(joint, frames[uid], item["end"], points, scope, sections.get(uid, {}),
                                           force["rowsets"].get(uid, {}), semantics, seismic, pairs)
                decision["column_ends"].append(result)
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                decision["reasons"].append(f"{uid}:{exc}")
        ends = decision["column_ends"]
        if decision["reasons"]:
            continue
        if {end["physical_side"] for end in ends} != {"UPPER", "LOWER"}:
            decision["reasons"].append("SCWB_OPPOSITE_COLUMN_SIDES_REQUIRED")
            continue
        exempt = all(end["max_seismic_nd_kn"] <= end["limit_kn"] for end in ends)
        decision.update(exempt=exempt, status="EXEMPT_LOW_AXIAL" if exempt else "LOW_AXIAL_LIMIT_EXCEEDED")
    return results


def alpha_low_axial_credit(source, axial, scope, dependency_plan, frame, end_joints, seismic,
                           *, source_payload_sha256):
    """Consume existing axial/end results for optional TBDY 7.3.6.1 credit.

This is a per-column decision, not the two-column joint exception. A neighbor
may exceed its limit while the target column qualifies. Credit never asserts
that Eq. 7.3 is satisfied and therefore does not itself authorize 1/alpha demand
amplification. No force or section-capacity calculation is repeated here.
"""
    from .design_dependencies import SCHEMA as DEPENDENCY_SCHEMA

    result = {"clause": "TBDY 7.3.6.1", "eligible": False, "status": "UNVERIFIED",
              "column_ends": [], "reason_codes": []}
    try:
        # The caller hashes this immutable source once per qualification, not
        # once per member/direction/combination. No source force is mutated.
        if (dependency_plan.get("schema") != DEPENDENCY_SCHEMA
                or dependency_plan.get("source_payload_sha256") != source_payload_sha256):
            raise ValueError("ALPHA_LOW_N_DEPENDENCY_SOURCE_MISMATCH")
        identity = scope.get("input_sha256")
        if not identity or dependency_plan.get("input_sha256") != identity:
            raise ValueError("ALPHA_LOW_N_SOURCE_IDENTITY_UNBOUND")
        uid = frame["frame_id"]
        plan = axial["combination_plan"]
        semantics = {c["name"]: c.get("force_semantics") for c in plan["combinations"]}
        verify_combined_seismic_axial_cases(source, seismic, semantics)
        columns = [c for c in axial.get("columns", ()) if c.get("element_id") == uid]
        if len(columns) != 1:
            raise ValueError("ALPHA_LOW_N_COLUMN_RESULT_UNBOUND")
        column = columns[0]
        limit = low_axial_limit_kn(column.get("gross_area_mm2"), column.get("fck_mpa"))
        maxima = {}
        for name in seismic:
            checks = [r for r in column.get("combination_checks", ()) if r.get("combination") == name]
            if (len(checks) != 1 or checks[0].get("status") not in ("WITHIN_LIMIT", "OUTSIDE_LIMIT")
                    or type(checks[0].get("nd_kn")) not in (int, float)
                    or not isfinite(checks[0]["nd_kn"]) or checks[0]["nd_kn"] < 0):
                raise ValueError("ALPHA_LOW_N_MEMBER_MAXIMUM_UNBOUND:" + name)
            maxima[name] = checks[0]["nd_kn"]
        for end in ("I", "J"):
            joint = end_joints[end]
            decision = joint.get("low_axial_exception") or {}
            if (decision.get("input_sha256") != identity or decision.get("reasons")
                    or decision.get("status") not in ("EXEMPT_LOW_AXIAL", "LOW_AXIAL_LIMIT_EXCEEDED")
                    or set(decision.get("seismic_combinations", ())) != set(seismic)):
                raise ValueError("ALPHA_LOW_N_END_EVIDENCE_UNBOUND:" + end)
            ends = [r for r in decision.get("column_ends", ())
                    if r.get("member_id") == uid and r.get("end") == end]
            if len(ends) != 1:
                raise ValueError("ALPHA_LOW_N_END_IDENTITY_UNBOUND:" + end)
            evidence = ends[0]
            cut, length = _configured_end(scope, frame, end)
            observed = evidence.get("configured_cut") or ()
            if (len(observed) != 4 or observed[0] != cut[0] or observed[2] != cut[2]
                    or any(type(observed[k]) not in (int, float) or not isfinite(observed[k]) for k in (1, 3))
                    or abs(observed[1] - cut[1]) > station_budget(observed[1], cut[1], length)
                    or abs(observed[3] - cut[3]) > station_budget(observed[3], cut[3], length)
                    or evidence.get("gross_area_mm2") != column["gross_area_mm2"]
                    or evidence.get("fck_mpa") != column["fck_mpa"] or evidence.get("limit_kn") != limit):
                raise ValueError("ALPHA_LOW_N_END_CUT_OR_SECTION_CONFLICT:" + end)
            values = evidence.get("nd_max_by_combination_kn") or {}
            for name in seismic:
                value = values.get(name)
                if type(value) not in (int, float) or not isfinite(value):
                    raise ValueError("ALPHA_LOW_N_END_VALUE_UNBOUND:" + end)
                if value > maxima[name]:
                    raise ValueError("ALPHA_LOW_N_END_MEMBER_MAXIMUM_CONFLICT:" + end)
            result["column_ends"].append(evidence)
        eligible = all(n <= limit for n in maxima.values())
        result.update(status="QUALIFIED_LOW_AXIAL_CREDIT" if eligible else "LOW_AXIAL_LIMIT_EXCEEDED",
                      eligible=eligible, input_sha256=identity, limit_kn=limit,
                      member_max_compression_by_combination_kn=maxima)
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        result["reason_codes"] = [str(exc)]
    return result
