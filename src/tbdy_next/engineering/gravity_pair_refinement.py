"""Bind refined ETABS element cuts to the original physical C29 member."""

from collections import defaultdict
from collections.abc import Mapping
from math import hypot, isclose
import re

from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.ts500_column import STORY_LOAD_RATIO_LIMIT, _magnification_denominator, euler_load_kn
from .column_clear_length import proven_clear_length_m
from .column_r08_local_live import _adopted_axis_factor, _magnified_moment_demand
from .gravity_order_pair import (
    FORCE_FIELDS, QUALIFIED_SCHEMA, SCHEMA, _finite, _native_ei, _station_pmm, _summarize_pmm, _utilization,
    normalize_gravity_order_pair,
)

DIVISIONS = (2, 4, 8)
POSITION_TOL_M = 1e-6
REL_TOL = 0.01
FORCE_TOL = 0.1
BOW_TOL_MM = 0.01
PMM_TOL = 0.001


def _position_close(a, b):
    return isclose(a, b, rel_tol=0, abs_tol=POSITION_TOL_M)


def normalize_levels(levels, base):
    if (not isinstance(levels, list) or not levels or len(levels) > len(DIVISIONS)
            or any(not isinstance(level, Mapping) for level in levels)
            or tuple(level.get("divisions") for level in levels) != DIVISIONS[:len(levels)]):
        raise ValueError("GRAVITY_REFINEMENT_LEVELS_INVALID")
    members = base["force_source"]["rowsets"].keys()
    revisions = set()
    required = {"divisions", "model_sha256", "mesh", "frame_object_modifiers", "force_source",
                "joint_displacements", "story_inputs"}
    qualified = base["schema"] == QUALIFIED_SCHEMA
    if qualified:
        required.add("analysis_generation")
    optional = {"kinematics", "story_basis_source"} if qualified else set()
    for level in levels:
        if (set(level) - optional != required
                or not isinstance(level["model_sha256"], str)
                or re.fullmatch(r"[a-f0-9]{64}", level["model_sha256"]) is None
                or level["model_sha256"] in revisions
                or not isinstance(level["mesh"], Mapping) or level["mesh"].keys() != members
                or not isinstance(level["joint_displacements"], Mapping)
                or not level["joint_displacements"].keys() <= members
                or not isinstance(level["story_inputs"], Mapping) or not level["story_inputs"].keys() <= members):
            raise ValueError("GRAVITY_REFINEMENT_SOURCE_OR_MESH_SCOPE_INVALID")
        revisions.add(level["model_sha256"])
        if qualified:
            generation = level["analysis_generation"]
            force = level["force_source"]
            if (not isinstance(generation, str) or re.fullmatch(r"[a-f0-9]{64}", generation) is None
                    or not isinstance(force, Mapping) or force.get("analysis_generation") != generation
                    or force.get("model_sha256") != level["model_sha256"] or level["story_inputs"]
                    or any(not isinstance(level[key], Mapping) for key in optional & level.keys())):
                raise ValueError("GRAVITY_REFINEMENT_GENERATION_OR_PRODUCER_SCOPE_INVALID")
        for mesh in level["mesh"].values():
            if not isinstance(mesh, list) or len(mesh) != level["divisions"]:
                raise ValueError("GRAVITY_REFINEMENT_ELEMENT_COUNT_MISMATCH")
            for element in mesh:
                if (not isinstance(element, Mapping)
                        or set(element) != {"element", "i_joint", "j_joint", "i_xyz", "j_xyz"}
                        or not all(isinstance(element[k], str) and element[k] for k in ("element", "i_joint", "j_joint"))
                        or any(not isinstance(element[key], list) or len(element[key]) != 3
                               or not all(_finite(x) for x in element[key]) for key in ("i_xyz", "j_xyz"))):
                    raise ValueError("GRAVITY_REFINEMENT_ELEMENT_GEOMETRY_INVALID")
        normalize_gravity_order_pair({
            **base, "schema": SCHEMA, "mesh": {uid: [row["element"] for row in mesh] for uid, mesh in level["mesh"].items()},
            "frame_object_modifiers": level["frame_object_modifiers"], "force_source": level["force_source"],
        }, source_data_sha256=base["source_data_sha256"])
    return levels


def _member_mesh(source, uid, physical, level):
    length = proven_clear_length_m(physical, uid)
    if length is None:
        raise ValueError("GRAVITY_REFINEMENT_PHYSICAL_FACES_UNVERIFIED")
    faces = physical["faces"]
    i_joint, j_joint = (faces[end]["joint_id"] for end in ("I", "J"))
    records = source["vs06_b1_geometry_source"]["table_reads"]["Point Object Connectivity"]["rows"]
    coordinates = {row["UniqueName"]: [float(row[axis]) for axis in "XYZ"]
                   for row in records if row["UniqueName"] in (i_joint, j_joint)}
    original_i, original_j = coordinates[i_joint], coordinates[j_joint]
    clear_i, clear_j = faces["I"]["top_z_m"], faces["J"]["soffit_z_m"]
    elements = sorted(level["mesh"][uid], key=lambda row: row["i_xyz"][2])
    if (elements[0]["i_joint"] != i_joint or elements[-1]["j_joint"] != j_joint
            or not all(_position_close(a, b) for a, b in zip(elements[0]["i_xyz"], original_i))
            or not all(_position_close(a, b) for a, b in zip(elements[-1]["j_xyz"], original_j))):
        raise ValueError("GRAVITY_REFINEMENT_ORIGINAL_ENDPOINTS_CHANGED")
    for i, element in enumerate(elements):
        a, b = element["i_xyz"], element["j_xyz"]
        if (a[2] >= b[2] or not all(_position_close(x, y) for x, y in zip(a[:2], original_i[:2]))
                or not all(_position_close(x, y) for x, y in zip(b[:2], original_i[:2]))):
            raise ValueError("GRAVITY_REFINEMENT_LOCAL_AXIS_CHANGED")
        if i and (elements[i - 1]["j_joint"] != element["i_joint"]
                  or not _position_close(elements[i - 1]["j_xyz"][2], a[2])
                  or not _position_close(a[2], clear_i + length * i / level["divisions"])):
            raise ValueError("GRAVITY_REFINEMENT_SEGMENT_JUNCTION_MISMATCH")
    return elements, original_i[2], clear_i, clear_j


def _paired_cuts(uid, level, cases, elements, original_z, low, high):
    mesh = {row["element"]: row for row in elements}
    mapping = {pair[order]: (name, order) for name, pair in cases.items() for order in ("first", "second")}
    cuts = defaultdict(dict)
    for row in native_frame_force_rows(level["force_source"]["rowsets"][uid], uid):
        _, obj_station, element, elm_station, label, step, number, *vector = row
        element_row = mesh[element]
        a, b = element_row["i_xyz"][2], element_row["j_xyz"][2]
        z = a + elm_station
        if ((step, number) != ("Step", 1.0) or not _position_close(z, original_z + obj_station)
                or z < max(a, low) - POSITION_TOL_M or z > min(b, high) + POSITION_TOL_M):
            raise ValueError("GRAVITY_REFINEMENT_PHYSICAL_STATION_MISMATCH")
        name, order = mapping[label]
        key = (name, element, obj_station, elm_station)
        if order in cuts[key]:
            raise ValueError("GRAVITY_REFINEMENT_CUT_DUPLICATE")
        side = "UPPER" if _position_close(z, a) else "LOWER" if _position_close(z, b) else "INTERIOR"
        cuts[key].update({order: vector, "physical_station_m": round(z - low, 6), "side": side})
    for name in cases:
        for element, row in mesh.items():
            values = [low + v["physical_station_m"] for k, v in cuts.items() if k[:2] == (name, element)]
            start, end = max(row["i_xyz"][2], low), min(row["j_xyz"][2], high)
            if (not any(_position_close(v, start) for v in values) or not any(_position_close(v, end) for v in values)
                    or not any(start + POSITION_TOL_M < v < end - POSITION_TOL_M for v in values)):
                raise ValueError("GRAVITY_REFINEMENT_ELEMENT_CUT_COVERAGE_INCOMPLETE")
    if not all("first" in v and "second" in v for v in cuts.values()):
        raise ValueError("GRAVITY_REFINEMENT_PAIRED_CUTS_MISMATCH")
    if len({(key[0], row["physical_station_m"], row["side"]) for key, row in cuts.items()}) != len(cuts):
        raise ValueError("GRAVITY_REFINEMENT_PHYSICAL_CUT_AMBIGUOUS")
    return cuts


def _refined_ts500(local, dims, capacity, cuts, story, cases, *, story_scope=None):
    # The revised first-order vectors and level-specific story inputs drive the
    # same factor owner. The original selected demand stays on its own branch.
    basis = local["adopted_second_order_basis"]
    if basis["global_factor_policy"] != "TS500_SWAY_WITH_TBDY_UNITY":
        return {}, "REVISED_TS500_FACTOR_POLICY_UNSUPPORTED", []
    if not isinstance(story, Mapping) or not story.keys() <= {"M2", "M3"}:
        raise ValueError("GRAVITY_REFINEMENT_AXIS_BASIS_INVALID")
    for item in story.values():
        if (not isinstance(item, Mapping) or set(item) != {"k", "story_aggregates"}
                or not _finite(item["k"]) or item["k"] <= 0 or not isinstance(item["story_aggregates"], Mapping)
                or not item["story_aggregates"].keys() <= cases.keys()):
            raise ValueError("GRAVITY_REFINEMENT_AXIS_BASIS_INVALID")
    factors = {}
    diagnostics = []
    peaks = {name: max(-value["first"][0] for key, value in cuts.items() if key[0] == name)
             for name in cases}
    for name in cases:
        for axis, stiffness in local["stiffness_and_euler"].items():
            revised_axis = story.get(axis, {})
            totals = revised_axis.get("story_aggregates", {}).get(name)
            trace = {"combination": name, "axis": axis, "ei_nmm2": stiffness["selected_ei_nmm2"],
                     "ln_mm": stiffness["free_length_ln_mm"], "coefficient_nd_kn": peaks[name],
                     "status": "REVISED_TS500_STORY_BASIS_UNAVAILABLE"}
            if story_scope is not None:
                trace["story_scope"] = story_scope
            diagnostics.append(trace)
            if revised_axis:
                k = revised_axis["k"]
                lk = k * trace["ln_mm"]
                nk = euler_load_kn(effective_ei_nmm2=trace["ei_nmm2"], effective_length_lk_mm=lk)
                trace.update(k=k, lk_mm=lk, nk_kn=nk,
                             member_denominator=float(_magnification_denominator(peaks[name], nk)))
            if totals is None:
                continue
            if (not isinstance(totals, Mapping) or set(totals) != {"nd_kn", "nk_kn"}
                    or not all(_finite(v) and v > 0 for v in totals.values())):
                raise ValueError("GRAVITY_REFINEMENT_STORY_TOTALS_INVALID")
            revised = {**basis, "member": {**basis["member"], "axes": {
                **basis["member"]["axes"], axis: {**basis["member"]["axes"][axis],
                                                "story_aggregates": {name: totals}},
            }}}
            revised_stiffness = {**stiffness, "effective_length_factor_k": k}
            result = _adopted_axis_factor(revised, axis, name, peaks[name], nk, revised_stiffness, end_ratio=None)
            trace.update(story_nd_kn=totals["nd_kn"], story_nk_kn=totals["nk_kn"],
                         story_denominator=float(_magnification_denominator(totals["nd_kn"], totals["nk_kn"])),
                         story_load_ratio_limit=float(STORY_LOAD_RATIO_LIMIT), **result)
            if result.get("final_factor") is not None:
                factors[name, axis] = result["final_factor"]
    results = {}
    for key, cut in cuts.items():
        name = key[0]
        if any((name, axis) not in factors for axis in ("M2", "M3")):
            continue
        nd, m2, m3 = -cut["first"][0], cut["first"][4], cut["first"][5]
        demand = _magnified_moment_demand(nd_kn=nd, m2_knm=m2, m3_knm=m3, dims=dims,
            beta_m2=factors[name, "M2"], beta_m3=factors[name, "M3"], global_factor=1.0)
        m2, m3 = demand["magnified_m2_design_knm"], demand["magnified_m3_design_knm"]
        results[key] = {
            "ts500_m2_knm": m2, "ts500_m3_knm": m3, "ts500_coefficient_nd_kn": peaks[name],
            "ts500_beta_m2": factors[name, "M2"], "ts500_beta_m3": factors[name, "M3"],
            "ts500_pmm": capacity.assess(nd * 1000.0, m2 * 1e6, m3 * 1e6),
        }
    if any(trace["status"] == "BLOCKED" for trace in diagnostics):
        status = "REVISED_TS500_STABILITY_FAILURE"
    elif len(results) == len(cuts):
        status = ("REVISED_TS500_CONDITIONAL_FRAME_ONLY_CALCULATED" if story_scope is not None
                  else "REVISED_FIRST_ORDER_VECTORS_AND_STORY_INPUTS_CONSUMED")
    else:
        status = "REVISED_TS500_STORY_BASIS_UNAVAILABLE"
    return results, status, diagnostics


def _node_chord_profiles(elements, record, cases, low):
    joints = [(row["i_joint"], row["i_xyz"][2]) for row in elements]
    joints.append((elements[-1]["j_joint"], elements[-1]["j_xyz"][2]))
    result = {}
    for name, case in cases.items():
        vectors = record.get(case["second"], {})
        if (not isinstance(vectors, Mapping) or set(vectors) != {joint for joint, _ in joints}
                or any(not isinstance(v, list) or len(v) != 3 or not all(_finite(x) for x in v) for v in vectors.values())):
            return {}
        start, end = joints[0][1], joints[-1][1]
        a, b = (vectors[joints[i][0]] for i in (0, -1))
        samples = []
        for joint, z in joints:
            t = (z - start) / (end - start)
            u = vectors[joint]
            offset = [(u[i] - a[i] - t * (b[i] - a[i])) * 1000 for i in (0, 1)]
            samples.append({"station_m": round(z - low, 6), "joint_id": joint,
                            "dx_mm": offset[0], "dy_mm": offset[1], "norm_mm": hypot(*offset)})
        result[name] = samples
    return result


def compare_level(source, pmm, local, base, level, dims, capacity, *, story_geometry=None):
    uid, cases = pmm["member_id"], base["cases"]
    out = {"divisions": level["divisions"], "model_sha256": level["model_sha256"], "rows": [],
           "status": "GRAVITY_REFINEMENT_UNBOUND",
           "cut_counts": {"expected": None, "evaluated": 0, "failed": 0, "unresolved": None}}
    try:
        elements, z, low, high = _member_mesh(source, uid, local["physical_clear_length"], level)
        stiffness = _native_ei(source, pmm["section"], uid,
                              {**base, "frame_object_modifiers": level["frame_object_modifiers"]}, local["stiffness_and_euler"])
        out["stiffness_comparison"] = stiffness
        if not all(row["ts500_ei_nmm2"] and isclose(row["etabs_ei_nmm2"], row["ts500_ei_nmm2"], rel_tol=1e-6)
                   for row in stiffness.values()):
            raise ValueError("GRAVITY_REFINEMENT_EFFECTIVE_EI_MISMATCH")
        cuts = _paired_cuts(uid, level, cases, elements, z, low, high)
        out["cut_counts"].update(expected=len(cuts), unresolved=len(cuts))
        out["first_order_nmax_kn"] = {name: max(-value["first"][0] for key, value in cuts.items() if key[0] == name)
                                     for name in cases}
        revised = {}
        try:
            story = level["story_inputs"].get(uid, {})
            story_scope = None
            if base["schema"] == QUALIFIED_SCHEMA:
                out["analysis_generation"] = level["analysis_generation"]
                from .gravity_story_basis import produce_story_basis

                story_basis = produce_story_basis(source, local, level, uid, cases, story_geometry=story_geometry)
                out["revised_story_basis"] = story_basis
                story = story_basis["story_inputs"]
                conditional = story_basis.get("conditional_frame_basis") or {}
                if story_basis["status"] != "REVISED_STORY_BASIS_CALCULATED" and conditional.get("story_inputs"):
                    story = conditional["story_inputs"]
                    story_scope = out["ts500_story_scope"] = conditional["scope"]
            revised, out["ts500_status"], out["revised_axis_factors"] = _refined_ts500(
                local, dims, capacity, cuts, story, cases, story_scope=story_scope)
        except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
            out.update(ts500_status="REVISED_TS500_BASIS_INVALID", ts500_reason=str(exc))
        original_z = local["physical_clear_length"]["end_cuts"]["I"][1]
        original_stations = {(row["combination"], round(row["object_station_m"] - original_z, 6))
                             for row in pmm["rows"] if row["combination"] in cases}
        matched_stations = {(name, cut["physical_station_m"]) for (name, *rest), cut in cuts.items()}
        out["common_original_physical_cuts"] = len(original_stations & matched_stations)
        out["additional_physical_cuts"] = len(matched_stations - original_stations)
        for key, cut in sorted(cuts.items()):
            name, element, station, elm_station = key
            row = {"combination": name, "analysis_element_id": element, "object_station_m": station,
                   "element_station_m": elm_station, "physical_station_m": cut["physical_station_m"], "side": cut["side"],
                   "control": dict(zip(FORCE_FIELDS, cut["first"])), "second": dict(zip(FORCE_FIELDS, cut["second"])),
                   **_station_pmm(cut["second"], dims, capacity)}
            if key in revised:
                assessment = revised[key]["ts500_pmm"]
                row.update({field: value for field, value in revised[key].items() if field != "ts500_pmm"})
                row.update(ts500_utilization=_utilization(assessment),
                           ts500_pmm_status=assessment["status"], ts500_pmm_reason=assessment.get("reason"))
                if story_scope is not None:
                    row["ts500_story_scope"] = story_scope
            out["rows"].append(row)
        _summarize_pmm(out, len(cuts), controls_matched=True)
        # The two controls agree in case and mesh identity. Each refined run
        # carries its own first-order forces.
        out["control_status"] = "REVISED_MODEL_FIRST_ORDER_PAIRED"
        profiles = _node_chord_profiles(elements, level["joint_displacements"].get(uid, {}), cases, low)
        peaks = {name: max(samples, key=lambda row: row["norm_mm"]) for name, samples in profiles.items()}
        out["second_order_node_chord_samples"] = profiles
        out["sampled_chord_peaks"] = peaks
        out["second_order_node_chord_bow_mm"] = {name: row["norm_mm"] for name, row in peaks.items()}
        out["clear_length_m"] = round(high - low, 6)
        out["full_span_peak_status"] = "UNVERIFIED_BETWEEN_NATIVE_JOINTS"
        if base["schema"] == QUALIFIED_SCHEMA:
            from .gravity_deformation import recover_level

            span = recover_level(level, uid, elements, cases, low, high, stiffness)
            out["full_span_deformation"] = span
            out["full_span_peak_status"] = span["status"]
    except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
        out.update(reason=str(exc))
    return out


def _common_node_deformation(before, after, names):
    profiles = [level["second_order_node_chord_samples"] for level in (before, after)]
    cases = {}
    for name in sorted(names):
        a, b = ({r["station_m"]: r for r in profile.get(name, ())} for profile in profiles)
        stations = sorted(s for s in a.keys() & b.keys() if 0 <= s <= after["clear_length_m"])
        # Matching only two support nodes gives no information on local bow.
        if not any(0 < s < after["clear_length_m"] for s in stations):
            continue
        rows = []
        for station in stations:
            first = [a[station][axis] for axis in ("dx_mm", "dy_mm")]
            second = [b[station][axis] for axis in ("dx_mm", "dy_mm")]
            difference = [y - x for x, y in zip(first, second)]
            rows.append({"station_m": station, "before_joint_id": a[station]["joint_id"],
                         "after_joint_id": b[station]["joint_id"], "before_xy_mm": first, "after_xy_mm": second,
                         "difference_xy_mm": difference, "difference_mm": hypot(*difference)})
        cases[name] = {"samples": rows, "max_difference_mm": max(row["difference_mm"] for row in rows)}
    within = (all(case["max_difference_mm"] <= BOW_TOL_MM for case in cases.values())
              if names and cases.keys() == names else None)
    return {"method": "MATCHED_NATIVE_JOINTS_RELATIVE_TO_ORIGINAL_NODE_CHORD", "tolerance_mm": BOW_TOL_MM,
            "status": {None: "UNVERIFIED", True: "WITHIN_TOLERANCE", False: "OUTSIDE_TOLERANCE"}[within],
            "cases": cases}


def _mesh_change(before, after):
    fields = ("p_kn", "m2_knm", "m3_knm")
    index = lambda rows: {(r["combination"], r["physical_station_m"], r["side"]): r for r in rows}
    a, b = (index(level["rows"]) for level in (before, after))
    shared = a.keys() & b.keys()
    bow_a, bow_b = (level["second_order_node_chord_bow_mm"] for level in (before, after))
    forces_match = bool(shared) and all(isclose(a[key]["second"][field], b[key]["second"][field],
        rel_tol=REL_TOL, abs_tol=FORCE_TOL) for key in shared for field in fields)
    names = {r["combination"] for r in before["rows"]}
    covers_common = all(len({k[1] for k in shared if k[0] == name}) >= 3 for name in names)
    peaks_match = all(isclose(max(abs(r["second"][f]) for r in a.values() if r["combination"] == name),
        max(abs(r["second"][f]) for r in b.values() if r["combination"] == name), rel_tol=REL_TOL, abs_tol=FORCE_TOL)
        for f in fields for name in names)
    pmms_match = all(isclose(max(r["second_pmm_utilization"] for r in a.values() if r["combination"] == name),
        max(r["second_pmm_utilization"] for r in b.values() if r["combination"] == name), rel_tol=REL_TOL, abs_tol=PMM_TOL)
        for name in names)
    bow_available = bow_a.keys() == bow_b.keys() == names
    bow_matches = (all(isclose(bow_a[name], bow_b[name], rel_tol=REL_TOL, abs_tol=BOW_TOL_MM)
                       for name in names) if bow_available else None)
    force_deltas = {f: max((abs(a[key]["second"][f] - b[key]["second"][f]) for key in shared), default=None)
                    for f in fields}
    span = {}
    bow_for_mesh = bow_matches
    if "analysis_generation" in before and "analysis_generation" in after:
        from .gravity_deformation import compare_recovered

        span = compare_recovered(before.get("full_span_deformation"), after.get("full_span_deformation"), BOW_TOL_MM)
        bow_for_mesh = span["within_tolerance"]
    return {"before": before["divisions"], "after": after["divisions"], "shared_signed_cuts": len(shared),
            "max_common_absolute_difference": force_deltas,
            "sufficient_common_locations": covers_common,
            "common_node_deformation": _common_node_deformation(before, after, names),
            "full_span_peak_status": span.get("status", "UNVERIFIED_BETWEEN_NATIVE_JOINTS"),
            **({"full_span_deformation_comparison": span} if span else {}),
            "forces_within_tolerance": forces_match and covers_common, "full_mesh_extrema_within_tolerance": peaks_match,
            "full_mesh_pmm_within_tolerance": pmms_match, "node_chord_bow_within_tolerance": bow_matches,
            "within_tolerance": (forces_match and peaks_match and pmms_match and bow_for_mesh
                                 if covers_common and bow_for_mesh is not None else None)}


def _method_comparison(original, finest, local):
    """Keep both native sides when a reference cut falls at a refined junction."""
    start = local["physical_clear_length"]["end_cuts"]["I"][1]
    cuts = defaultdict(list)
    for row in finest["rows"]:
        cuts[row["combination"], row["physical_station_m"]].append(row)
    original_coefficients = {row["combination"]: row["coefficient_nd_kn"]
                             for row in local["magnified_selected_pmm"]["rows"] if "coefficient_nd_kn" in row}

    def moments(vector):
        return [vector["m2_knm"], vector["m3_knm"]]

    def delta(a, b):
        return [x - y for x, y in zip(a, b)] if a is not None and b is not None else None

    rows = []
    for row in original:
        name = row["combination"]
        station = round(row["object_station_m"] - start, 6)
        design = [row["ts500_m2_knm"], row["ts500_m3_knm"]]
        choices = []
        for cut in cuts[name, station]:
            direct = [cut.get("second_design_m2_knm"), cut.get("second_design_m3_knm")]
            ts = [cut["ts500_m2_knm"], cut["ts500_m3_knm"]] if "ts500_m2_knm" in cut else None
            ratios = [("ORIGINAL_TS500", row["ts500_utilization"]), ("DIRECT_P_DELTA", cut["second_pmm_utilization"]),
                      ("REVISED_TS500", cut.get("ts500_utilization"))]
            complete = all(_finite(value) for _, value in ratios)
            first_moments, second_moments = moments(cut["control"]), moments(cut["second"])
            choices.append({"element": cut["analysis_element_id"], "side": cut["side"],
                            "first_nd_kn": -cut["control"]["p_kn"], "second_nd_kn": -cut["second"]["p_kn"],
                            "first_m2_m3_knm": first_moments, "second_m2_m3_knm": second_moments,
                            "second_minus_first_signed_knm": delta(second_moments, first_moments),
                            "second_minus_first_abs_knm": delta([abs(v) for v in second_moments],
                                                                [abs(v) for v in first_moments]),
                            "direct_design_m2_m3_knm": direct, "direct_pmm": cut["second_pmm_utilization"],
                            "revised_nmax_kn": finest["first_order_nmax_kn"][name],
                            "revised_ts500_coefficient_nd_kn": cut.get("ts500_coefficient_nd_kn"),
                            "revised_ts500_beta": [cut["ts500_beta_m2"], cut["ts500_beta_m3"]] if ts else None,
                            "revised_ts500_m2_m3_knm": ts, "revised_ts500_pmm": cut.get("ts500_utilization"),
                            "revised_ts500_pmm_status": cut.get("ts500_pmm_status"),
                            **({"revised_ts500_story_scope": cut["ts500_story_scope"]} if "ts500_story_scope" in cut else {}),
                            "revised_ts500_minus_direct_design_knm": delta(ts, direct),
                            "direct_minus_original_design_knm": (delta(direct, design)
                                                                 if all(_finite(v) for v in (*direct, *design)) else None),
                            "governing_comparison": max(ratios, key=lambda item: item[1])[0] if complete else None})
        rows.append({"combination": name, "physical_station_m": station, "original_element": row["analysis_element_id"],
                     "original_nd_kn": -row["original"]["p_kn"], "original_coefficient_nd_kn": original_coefficients.get(name),
                     "original_first_m2_m3_knm": moments(row["original"]), "original_ts500_design_m2_m3_knm": design,
                     "original_ts500_pmm": row["ts500_utilization"], "refined_cuts": choices})
    return {"divisions": finest["divisions"], "model_sha256": finest["model_sha256"],
            "expected_physical_cuts": len(rows), "matched_physical_cuts": sum(bool(row["refined_cuts"]) for row in rows),
            "revised_ts500_status": finest.get("ts500_status"),
            **({"revised_ts500_story_scope": finest["ts500_story_scope"]} if "ts500_story_scope" in finest else {}),
            "rows": rows}


def compare_levels(source, pmm, local, base, dims, capacity, original, *, story_geometry=None):
    levels = [compare_level(source, pmm, local, base, level, dims, capacity, story_geometry=story_geometry)
              for level in base["refined_levels"]]
    changes = [_mesh_change(a, b) for a, b in zip(levels, levels[1:])
               if a["status"] == b["status"] == "GRAVITY_PAIR_COMPARED"]
    full_series = len(levels) == len(DIVISIONS) and len(changes) == len(DIVISIONS) - 1
    final_comparison = changes[-1]["within_tolerance"] if full_series else None
    status = {True: "WITHIN_NUMERICAL_TOLERANCE", False: "OUTSIDE_NUMERICAL_TOLERANCE", None: "UNVERIFIED"}[final_comparison]
    comparison = _method_comparison(original, levels[-1], local) if levels[-1]["rows"] else None
    return {"levels": levels, "changes": changes, "status": status, "method_comparison": comparison,
            "tolerances": {"relative": REL_TOL, "force_kn": FORCE_TOL, "moment_knm": FORCE_TOL,
                           "node_chord_bow_mm": BOW_TOL_MM, "pmm": PMM_TOL}}
