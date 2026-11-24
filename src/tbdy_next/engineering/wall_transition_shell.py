"""Native element joint resultants on one side of a horizontal cut and at panel boundaries."""

from collections import defaultdict
from math import dist, fsum

from ..etabs_source_gateway_windows import verify
from .basement_pier_geometry import _column_footprints, _context, panel_profile, required
from .gravity_wall_cut import joint_action_at_origin
from .wall_transition import GLOBAL_COMPONENTS, TOL, changes, mesh_geometry, section_plan, weighted_vectors

SCHEMA = "tbdy.next.original-transition-shell-actions.v1"


def native_plan(source, label_rows, *, with_fields=False):
    context = _context(source)
    groups = defaultdict(set)
    for row in label_rows:
        groups[row["PierName"], row["Story"]].add(row["UniqueName"])
    coords, mesh = mesh_geometry(source)
    wanted = defaultdict(set)
    fields = defaultdict(set)
    for (_, story), ids in groups.items():
        # Full-height groups need no supplemental native read.
        xyz, walls = context[:2]
        heights = {(xyz[walls[u]["UniquePt1"]][2], xyz[walls[u]["UniquePt4"]][2]) for u in ids}
        if len(heights) < 2:
            continue
        footprints, _ = _column_footprints(context, story)
        profile = panel_profile(context, footprints, sorted(ids))
        lengths = {p["member"]: p["length_m"] for p in profile["panels"]}
        for lower, upper, changed in changes(profile):
            for uid in changed:
                wanted[uid].update((elm, p) for elm, nodes in mesh[uid].items() for p in nodes)
            for side, band in (("Below", lower), ("Above", upper)):
                plan = section_plan(band, upper["bottom_m"], side, lengths, mesh, coords)
                for uid, pairs in plan["corners"].items():
                    wanted[uid].update(pairs)
                if with_fields:
                    levels = {upper["bottom_m"], plan.get("z_m", upper["bottom_m"])}
                    for uid in band["members"]:
                        for elm, nodes in mesh[uid].items():
                            heights = [coords[p][2] for p in nodes]
                            if any(min(heights) - TOL <= z <= max(heights) + TOL for z in levels):
                                fields[uid].update((elm, p) for p in nodes)
    return (wanted, coords, fields) if with_fields else (wanted, coords)


def _zone(position, panel, xyz):
    a, b, _, _ = [xyz[p] for p in panel["point_ids"]]
    ends = "I" if dist(position[:2], a[:2]) <= TOL else "J" if dist(position[:2], b[:2]) <= TOL else ""
    level = (
        "Bottom"
        if abs(position[2] - panel["bottom_m"]) <= TOL
        else "Top"
        if abs(position[2] - panel["top_m"]) <= TOL
        else ""
    )
    return " ".join(p for p in (ends, level) if p) or "Interior"


def _actions(read, uid, cases, pairs, origin, coords):
    item = read["members"][uid]
    corners = [tuple(k) for k in item["corners"]]
    index = {key: i for i, key in enumerate(corners)}
    required(
        len(index) == len(corners) and set(pairs) <= index.keys(), "NATIVE_SHELL_CORNER_POPULATION_MISMATCH"
    )
    out = {}
    for case in cases:
        raw = item["cases"][case]
        required(len(raw) == len(index), "NATIVE_SHELL_ACTION_COUNT_MISMATCH")
        out[case] = {}
        for key in pairs:
            _, point = key
            pos, axes = read["point_bases"][point]
            required(dist(pos, coords[point]) <= TOL, "NATIVE_TRANSITION_JOINT_LOCATION_DIFFERS")
            out[case][key] = joint_action_at_origin(raw[index[key]], axes, pos, origin)
    return out


def project_transition_shells(source, bound, scope, change, panels, plans, coords, mesh, xyz, panel_actions):
    changed = change["started"] + change["ended"]
    end_points = {
        p for uid in changed for p in panels[uid]["point_ids"] if abs(xyz[p][2] - change["z_m"]) <= TOL
    }
    origin = [fsum(xyz[p][i] for p in end_points) / len(end_points) for i in range(2)] + [change["z_m"]]
    from .mixed_demands import linear_coefficients, native_graph
    from .wall_shell_section import IDENTITY, recover_section, uniform_edge_load

    combos = dict(scope["native_static"])
    external = {
        p["member"]: {c["combination"]: c for c in p.get("combinations", ())} for p in change["panel_loads"]
    }
    extra = {
        name
        for rows in external.values()
        for name, c in rows.items()
        if c["role"] == "ADDITIONAL_STATIC_PRESSURE"
    }
    if extra:
        _, types, graph = native_graph(source)
        combos.update({name: linear_coefficients(name, graph, types) for name in sorted(extra)})
    out = {
        "origin_m": origin,
        "component_order": GLOBAL_COMPONENTS,
        "sections": [],
        "panel_zones": [],
        "recovered": [],
        "expected_section_combinations": 2 * len(combos),
        "expected_panel_combinations": len(changed) * len(combos),
    }
    read = ((source.get("pier_section_forces") or {}).get("read") or {}).get("transition_shells")
    if not read:
        return {**out, "status": "NATIVE_TRANSITION_SHELL_READ_REQUIRED"}
    try:
        verify(read)
        required(
            read["schema"] == SCHEMA
            and read["model_sha256"] == bound["model_sha256"]
            and read["units"] == 6
            and read["selection_restored"] is True,
            "TRANSITION_MODEL_OR_SELECTION_MISMATCH",
        )
        leaves = {c for terms in combos.values() for c in terms}
        solution = read.get("solution")
        if solution:
            controls = solution["pier_controls"]
            required(
                solution["method"] == "INPUT_IDENTICAL_PRIVATE_REANALYSIS"
                and solution["input_sha256"] == bound["model_sha256"]
                and solution["frame_control_matched"] is True
                and controls["rows"] > 0
                and controls["outside_tolerance"] == 0,
                "PRIVATE_WALL_CONTROL_BINDING_REQUIRED",
            )
            out["solution"] = solution
        out["basis"] = solution["method"] if solution else "SOLVED_ORIGINAL"
        for side, plan in plans.items():
            if not plan["corners"]:
                continue
            sign = 1 if plan["element_face"] == "Bottom" else -1
            terms = defaultdict(list)
            for uid, pairs in plan["corners"].items():
                series = _actions(read, uid, leaves, pairs, origin, coords)
                for case, values in series.items():
                    terms[case].extend((sign, v) for v in values.values())
            primitive = {case: weighted_vectors(v) for case, v in terms.items()}
            for name, coeff in combos.items():
                vector = weighted_vectors([(float(f), primitive[c]) for c, f in coeff.items()])
                out["sections"].append(
                    {
                        "side": side,
                        "z_m": plan["z_m"],
                        "at_transition": plan["at_transition"],
                        "combination": name,
                        "global_kn_knm": vector,
                    }
                )
            try:
                controls = recover_section(
                    read,
                    plan,
                    panels,
                    mesh,
                    coords,
                    xyz,
                    plan["z_m"],
                    plan["element_face"] == "Bottom",
                    combos,
                    origin,
                )
                exact_z = recover_section(
                    read, plan, panels, mesh, coords, xyz, change["z_m"], side == "Above", combos, origin
                )
                physical = next(s for s in change["sections"] if s["side"] == side)
                for sec in (s for s in out["sections"] if s["side"] == side):
                    name = sec["combination"]
                    delta = [a - b for a, b in zip(controls[name], sec["global_kn_knm"])]
                    result = {
                        "side": side,
                        "z_m": change["z_m"],
                        "combination": name,
                        "global_kn_knm": exact_z[name],
                        "control_z_m": plan["z_m"],
                        "control_delta_kn_knm": delta,
                        "status": "RECOVERED_CORNER_FIELD_REFERENCE",
                    }
                    if physical.get("axial_limit_kn"):
                        result["reference_axial_ratio"] = (
                            max(0.0, exact_z[name][2]) / physical["axial_limit_kn"]
                        )
                    try:
                        direct = uniform_edge_load(
                            plan, mesh, coords, panels, xyz, panel_actions, name, origin
                        )
                        result["control_uniform_load_kn_knm"] = direct
                        result["control_delta_after_uniform_load_kn_knm"] = [
                            d - f for d, f in zip(delta, direct)
                        ]
                    except (KeyError, ValueError, TypeError) as exc:
                        result["control_load_reason"] = str(exc)
                    out["recovered"].append(result)
            except (KeyError, TypeError, ValueError) as exc:
                out.setdefault("field_reasons", {})[side] = str(exc)
        for uid in changed:
            pairs = [(e, p) for e, nodes in mesh[uid].items() for p in nodes]
            data = _actions(read, uid, leaves, pairs, origin, coords)
            zones = defaultdict(list)
            for e, p in pairs:
                zones[_zone(coords[p], panels[uid], xyz)].append((e, p))
            opening_face = "Bottom" if uid in change["started"] else "Top"
            edge_zones = [zone for zone in zones if zone.split()[-1] == opening_face]
            required(edge_zones, "OPENING_PANEL_END_JOINTS_MISSING")
            for name, coeff in combos.items():
                vectors = {
                    zone: weighted_vectors(
                        [(float(f), data[c][key]) for key in keys for c, f in coeff.items()]
                    )
                    for zone, keys in zones.items()
                }
                total = weighted_vectors([(1, v) for v in vectors.values()])
                rec = {
                    "member": uid,
                    "combination": name,
                    "zones": vectors,
                    "total_kn_knm": total,
                    "opening_face": opening_face,
                    "opening_edge_kn_knm": weighted_vectors([(1, vectors[k]) for k in edge_zones]),
                }
                out["panel_zones"].append(rec)
                applied = external.get(uid, {}).get(name)
                if applied:
                    from .coupled_wall_transition import BALANCE_ABS, BALANCE_REL

                    points = [xyz[p] for p in panels[uid]["point_ids"]]
                    a, b = points[:2]
                    length = dist(a[:2], b[:2])
                    q = applied["normal_force_kn"]
                    force = [
                        q * (b[1] - a[1]) / length,
                        -q * (b[0] - a[0]) / length,
                        -applied["self_weight_kn"],
                        0.0,
                        0.0,
                        0.0,
                    ]
                    center = [fsum(p[i] for p in points) / 4 for i in range(3)]
                    body = joint_action_at_origin(force, IDENTITY, center, origin)
                    residual = [v + b for v, b in zip(total, body)]
                    limits = [
                        max(BALANCE_ABS, BALANCE_REL * max(abs(v[i]) for v in [body, *vectors.values()]))
                        for i in range(6)
                    ]
                    rec.update(
                        body_kn_knm=body,
                        residual_kn_knm=residual,
                        limits_kn_knm=limits,
                        balanced=all(abs(v) <= t for v, t in zip(residual, limits)),
                    )
        out["status"] = (
            "SIGNED_SHELL_SECTIONS_AND_PANEL_BOUNDARIES"
            if len(out["sections"]) == out["expected_section_combinations"]
            else "COMMON_MESH_SECTION_REQUIRED"
        )
        if any(p.get("balanced") is False for p in out["panel_zones"]):
            out["status"] = "PANEL_EQUILIBRIUM_MISMATCH"
    except (KeyError, TypeError, IndexError, ValueError, RuntimeError) as exc:
        out.update(status="TRANSITION_SHELL_SOURCE_INCOMPLETE", reason=str(exc))
    return out
