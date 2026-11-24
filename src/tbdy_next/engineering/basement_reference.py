"""TBDY 3.3.1 basement candidate geometry and mass scope on the original building."""
from collections import defaultdict, deque
from itertools import pairwise
from math import fsum, isclose, isfinite

from ..story_geometry import read_story_levels
from .basement_pier_geometry import close, required
from .column_clear_length import _floor_at_joint, _group, _index, _records
from .pier_force_source import _table


def _ground_plan(source, story, top):
    geometry = source["vs06_b1_geometry_source"]["table_reads"]
    native = source["column_axial"]["r10_source"]["table_reads"]
    points = _index(_records(geometry, "Point Object Connectivity", "UniqueName X Y Z", ("X", "Y", "Z")), "UniqueName")
    floors = _group(_records(native, "Floor Object Connectivity", "UniqueName Story UniquePt1 UniquePt2 UniquePt3"), "UniqueName")
    assignments = _index(_records(geometry, "Area Assignments - Section Properties", "UniqueName SectProp"), "UniqueName")
    slabs = _index(_records(native, "Slab Property Definitions", "Name PropType"), "Name")
    polygons = []
    for uid, pieces in floors.items():
        if not any(row["Story"] == story for row in pieces):
            continue
        first = next(row for row in pieces if row["Story"] == story)
        prop = slabs[assignments[uid]["SectProp"]]
        required(prop["PropType"] == "Slab", "GROUND_FLOOR_SHELL_TYPE_REQUIRES_REVIEW:" + uid)
        origin = tuple(float(points[first["UniquePt1"]][k]) for k in "XYZ")
        corners = _floor_at_joint(pieces, origin, points)
        xyz = [tuple(float(points[p][k]) for k in "XYZ") for p in corners]
        required(all(close(z, top) for _, _, z in xyz), "GROUND_FLOOR_SHELL_ELEVATION_DIFFERS")
        polygon = [(x, y) for x, y, _ in xyz]
        edges = list(zip(polygon, polygon[1:] + polygon[:1]))
        required(all((a[0] == b[0]) != (a[1] == b[1]) for a, b in edges), "ORTHOGONAL_FLOOR_PLAN_REQUIRED")
        area = fsum((a[0] - origin[0]) * (b[1] - origin[1]) - (b[0] - origin[0]) * (a[1] - origin[1])
                    for a, b in edges) / 2
        required(isclose(area, float(first["Area"]), abs_tol=.0050001, rel_tol=0), "GROUND_FLOOR_AREA_DIFFERS:" + uid)
        polygons.append(polygon)
    required(polygons, "GROUND_FLOOR_FOOTPRINT_REQUIRED")
    return points, polygons


def _facades(polygons, panels, axis):
    """At each projected strip use the first and last ground-floor boundaries."""
    sweep, normal = axis, 1 - axis
    edges = [(a, b) for poly in polygons for a, b in zip(poly, poly[1:] + poly[:1])
             if a[normal] == b[normal]]
    walls = [w for w in panels if w["a"][normal] == w["b"][normal]]
    breaks = sorted({p[sweep] for a, b in edges for p in (a, b)}
                    | {w[key][sweep] for w in walls for key in ("a", "b")})
    segments = [[], []]
    for lo, hi in pairwise(breaks):
        mid = (lo + hi) / 2
        hits = [a[normal] for a, b in edges if min(a[sweep], b[sweep]) < mid < max(a[sweep], b[sweep])]
        if not hits:
            continue
        for side, edge in enumerate((min(hits), max(hits))):
            ids = sorted(w["id"] for w in walls if close(w["a"][normal], edge)
                         and min(w["a"][sweep], w["b"][sweep]) < mid < max(w["a"][sweep], w["b"][sweep]))
            records = segments[side]
            if records and records[-1]["at_m"] == edge and records[-1]["to_m"] == lo and records[-1]["walls"] == ids:
                records[-1]["to_m"] = hi
            else:
                records.append({"from_m": lo, "to_m": hi, "at_m": edge, "walls": ids})
    return segments


def _wall_path(polygons, panels, side):
    """Trace connected wall centrelines between the extreme ends of an open facade."""
    normal = 0 if side.startswith("X") else 1
    sweep = 1 - normal
    corners = [p for poly in polygons for p in poly]
    limit = (max if side.endswith("+") else min)(p[normal] for p in corners)
    ends = sorted({p for p in corners if p[normal] == limit}, key=lambda p: p[sweep])
    start, finish = ends[0], ends[-1]
    nodes = {p[k] for p in panels for k in ("a","b")} | {start, finish}
    adjacency = defaultdict(list)
    for p in panels:
        a, b = p["a"], p["b"]
        dim = 0 if a[0] != b[0] else 1
        subset = sorted((v for v in nodes if v[1-dim] == a[1-dim]
                         and min(a[dim], b[dim]) <= v[dim] <= max(a[dim], b[dim])), key=lambda v: v[dim])
        for i, j in pairwise(subset):
            adjacency[i].append((j, p["id"]))
            adjacency[j].append((i, p["id"]))
    queue, parent = deque([start]), {start: None}
    while queue and finish not in parent:
        current = queue.popleft()
        for joint, uid in adjacency[current]:
            if joint not in parent:
                parent[joint] = (current, uid)
                queue.append(joint)
    connected = finish != start and finish in parent
    walls = []
    if connected:
        joint = finish
        while joint != start:
            joint, uid = parent[joint]
            if not walls or walls[-1] != uid:
                walls.append(uid)
    return {"side": side, "endpoints_m": [start, finish], "connected": connected, "wall_ids": walls[::-1]}


def _perimeter(source, story, base, top, basement_storeys):
    points, polygons = _ground_plan(source, story, top)
    tables = source["vs06_b1_geometry_source"]["table_reads"]
    walls = _records(tables, "Wall Object Connectivity", "UniqueName Story WallBay UniquePt1 UniquePt2 UniquePt3 UniquePt4")
    panels = []
    for w in walls:
        if w["Story"] not in basement_storeys:
            continue
        a, b, c, d = [tuple(float(points[w["UniquePt" + str(i)]][k]) for k in "XYZ") for i in range(1, 5)]
        required(a[:2] == d[:2] and b[:2] == c[:2] and a[2] == b[2] < c[2] == d[2]
                 and base <= a[2] and c[2] <= top and ((a[0] == b[0]) != (a[1] == b[1])),
                 "ORTHOGONAL_BASEMENT_WALL_REQUIRED:" + w["UniqueName"])
        panels.append({"id": w["UniqueName"], "label": w["WallBay"], "a": a[:2], "b": b[:2], "lo": a[2], "hi": c[2]})
    required(len({w["id"] for w in panels}) == len(panels) and panels, "BASEMENT_WALL_POPULATION_REQUIRED")
    breaks = sorted({base, top} | {w[k] for w in panels for k in ("lo", "hi")})
    bands = []
    for lo, hi in pairwise(breaks):
        present = [w for w in panels if w["lo"] <= lo and hi <= w["hi"]]
        sides = []
        for axis, names in enumerate((("Y−", "Y+"), ("X−", "X+"))):
            for name, intervals in zip(names, _facades(polygons, present, axis)):
                projected = fsum(r["to_m"] - r["from_m"] for r in intervals)
                covered = fsum(r["to_m"] - r["from_m"] for r in intervals if r["walls"])
                sides.append({"side": name, "span_m": projected, "on_outline_m": covered,
                              "gap_m": projected - covered, "intervals": intervals})
        counted = {uid for side in sides for r in side["intervals"] for uid in r["walls"]}
        bands.append({"bottom_m": lo, "top_m": hi, "sides": sides,
                      "open_side_paths": [_wall_path(polygons, present, s["side"]) for s in sides if s["on_outline_m"] == 0],
                      "other_wall_ids": sorted({w["id"] for w in present} - counted)})
    return {"floor_shells": len(polygons), "wall_count": len(panels), "bands": bands,
            "wall_labels": {w["id"]: w["label"] for w in panels},
            "interpretation": "Projected ground-floor outline and coincident wall centrelines. "
                              "Returns, offset walls, openings and structural continuity require project interpretation."}


def _masses(source, top):
    tables = source["vs04_basis_probe"]["table_reads"]
    name = "Assembled Joint Masses"
    units = tables[name]["field_metadata"]["units_by_field"]
    fields = ("UX", "UY", "UZ", "RX", "RY", "RZ")
    required(units["Z"] == "m" and all(units[k] == ("ton" if k[0] == "U" else "ton-m2") for k in fields),
             "BASEMENT_MASS_UNITS_REQUIRED")
    rows = _table(tables, name)
    seen = set()
    by_plane = defaultdict(list)
    for row in rows:
        joint = row["PointElm"]
        z = float(row["Z"])
        values = tuple(float(row[k]) for k in fields)
        required(joint and joint not in seen and isfinite(z) and all(isfinite(v) and v >= 0 for v in values),
                 "UNIQUE_FINITE_ASSEMBLED_JOINT_MASSES_REQUIRED")
        seen.add(joint)
        by_plane[z].append(values)
    planes = [{"z_m": z, "joint_count": len(vals), "omitted": z <= top,
               **dict(zip(fields, map(fsum, zip(*vals))))} for z, vals in sorted(by_plane.items())]
    summary = _table(tables, "Mass Summary by Story")
    for k in fields[:3]:
        required(tables["Mass Summary by Story"]["field_metadata"]["units_by_field"][k] == "ton"
                 and abs(fsum(float(r[k]) for r in summary) - fsum(r[k] for r in planes))
                 <= .000051 * (len(rows) + len(summary)), "JOINT_AND_STOREY_MASSES_DIFFER:" + k)
    return {"joints": len(seen), "planes": planes, "components": list(fields),
            "removed": {k: fsum(r[k] for r in planes if r["omitted"]) for k in fields},
            "retained": {k: fsum(r[k] for r in planes if not r["omitted"]) for k in fields}}


def _full_periods(source, modal):
    bank = source["column_axial"]["demand_support"]["force_source"]
    periods = bank["native_modal_results"]["methods"]["ModalPeriod"]["data"]
    table = source["table"]
    rows = [r for r in table["rows"] if r["Case"] == modal]
    modes = bank["expected_modal_modes"][modal]
    required(table["row_count"] == len(table["rows"]) and periods["ret"] == 0
             and periods["NumberResults"] == len(modes) == len(rows)
             and all(periods["LoadCase"][i] == modal and periods["StepType"][i] == "Mode"
                     and periods["StepNum"][i] == m == int(rows[i]["Mode"])
                     and isfinite(periods["Period"][i]) and periods["Period"][i] > 0
                     and abs(periods["Period"][i] - float(rows[i]["Period"])) <= .00051
                     for i, m in enumerate(modes)), "BASEMENT_FULL_MODE_IDENTITY_DIFFERS")
    out = []
    for axis in ("X", "Y"):
        ratios = [float(r["U" + axis]) for r in rows]
        required(all(isfinite(r) and 0 <= r <= 1 for r in ratios), "INVALID_DIRECTIONAL_MASS_RATIO")
        ranked = sorted(range(len(rows)), key=ratios.__getitem__, reverse=True)
        first = ranked[0]
        required(ratios[first] > 0 and (len(ranked) == 1 or ratios[first] - ratios[ranked[1]] > .0001),
                 "DIRECTIONAL_DOMINANT_MODE_AMBIGUOUS:" + axis)
        period = periods["Period"][first]
        out.append({"direction": axis, "full_mode": modes[first], "full_period_s": period,
                    "full_participating_ratio": ratios[first], "upper_period_at_1_1_s": period / 1.1})
    return out


def _dominant(modes, direction):
    required(len(modes) >= 2 and all(isfinite(r[direction]) and 0 <= r[direction] <= 1 and r["period_s"] > 0 for r in modes)
             and fsum(r[direction] for r in modes) <= 1 + len(modes)*1e-9, "INVALID_MODAL_MASS_FRACTIONS")
    ordered = sorted(modes, key=lambda r: r[direction], reverse=True)
    remainder = max(0., 1 - fsum(r[direction] for r in modes))
    first = ordered[0]
    required(first[direction] > max(remainder, ordered[1][direction]) + 1e-6,
             "DIRECTIONAL_DOMINANT_MODE_NOT_SEPARATED:" + direction)
    return first, remainder


def _period_decision(native_periods, solution):
    rows = []
    for native in native_periods:
        axis = native["direction"]
        full, full_left = _dominant(solution["full"], axis)
        upper, upper_left = _dominant(solution["upper"], axis)
        period_difference = abs(full["period_s"] / native["full_period_s"] - 1)
        mass_difference = abs(full[axis] - native["full_participating_ratio"])
        required(period_difference <= .001 and mass_difference <= .001,
                 "PRIVATE_MATRIX_FULL_MODE_DIFFERS_FROM_NATIVE_RITZ:" + axis)
        ratio = full["period_s"] / upper["period_s"]
        # Retain the uncertainty from rounding the recorded periods; the two
        # readings in the clause also differ exactly at equality.
        delta = max(1e-8, ratio * period_difference,
                    ratio * (full.get("relative_residual", 0.) + upper.get("relative_residual", 0.)))
        state = ("SATISFIED" if ratio + delta < 1.1 else "EXCEEDED" if ratio - delta > 1.1
                 else "LIMIT_REQUIRES_REVIEW")
        rows.append({**native, "matrix_full_mode": full["mode"], "matrix_full_period_s": full["period_s"],
                     "matrix_full_mass_ratio": full[axis], "upper_mode": upper["mode"], "upper_period_s": upper["period_s"],
                     "upper_mass_ratio": upper[axis], "full_uncomputed_mass_bound": full_left,
                     "upper_uncomputed_mass_bound": upper_left, "period_ratio": ratio, "limit": 1.1,
                     "comparison_band": delta, "native_relative_period_difference": period_difference,
                     "native_mass_ratio_difference": mass_difference, "status": state})
    return rows


def basement_reference(source, modal, storeys):
    result = {"schema": "tbdy.next.basement-reference.v1", "status": "BASEMENT_REFERENCE_PENDING",
              "periods": [], "expected_directions": 2}
    try:
        levels, base = read_story_levels(source["vs04_basis_probe"])
        default = min(levels, key=lambda r: r.elevation_m)
        ground_story = (source.get("basement_modal_matrices") or {}).get("ground_story", default.story)
        selected = [level for level in levels if level.story == ground_story]
        required(len(selected) == 1, "CANDIDATE_GROUND_STOREY_ID_DIFFERS")
        bottom, top = float(base["base_elevation_m"]), float(selected[0].elevation_m)
        basement_storeys = {level.story for level in levels if bottom < level.elevation_m <= top}
        required(bottom < top and all(any(close(s["cut_z_m"], z) for s in storeys) for z in (bottom,top)),
                 "CANDIDATE_GROUND_AND_FOUNDATION_CUTS_REQUIRED")
        result.update(ground_story=ground_story, foundation_m=bottom, candidate_m=top,
                      source_model_sha256=source["analysis_archive"]["observed_edb_sha256"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return {**result, "reason": str(exc)}
    for key, calc, args in (("perimeter", _perimeter, (source, ground_story, bottom, top, basement_storeys)),
                            ("mass_scope", _masses, (source, top)), ("periods", _full_periods, (source, modal))):
        try:
            result[key] = calc(*args)
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError) as exc:
            result[key + "_reason"] = str(exc)
    if result.get("perimeter"):
        result["enclosure_status"] = "PROJECT_RIGID_ENCLOSURE_INTERPRETATION_REQUIRED"
    if not source.get("basement_modal_matrices"):
        result["period_reason"] = "SAME_STIFFNESS_UPPER_MASS_MODEL_REQUIRED"
        return result
    if len(result["periods"]) != 2 or not result.get("mass_scope"):
        return result
    try:
        from .basement_matrices import solve_period_pair
        solution = solve_period_pair(source, modal, top)
        result["matrix_solution"] = solution
        rows = _period_decision(result["periods"], solution)
        result.update(periods=rows, evaluated_directions=len(rows))
        states = {r["status"] for r in rows}
        if "EXCEEDED" in states:
            result.update(status="FOUNDATION_TOP_BY_3_3_1_2", design_base_m=bottom, period_status="EXCEEDED")
        elif states == {"SATISFIED"}:
            result.update(status="PERIOD_CONDITION_SATISFIED_ENCLOSURE_DECISION_REQUIRED", period_status="SATISFIED")
        else:
            result.update(status="PERIOD_LIMIT_REQUIRES_REVIEW", period_status="LIMIT_REQUIRES_REVIEW")
        result["reference_cuts"] = [
            {"condition": label, "cut_z_m": st["cut_z_m"], "direction": row["direction"],
             **{k: row[k] for k in ("wall_to_storey_shear", "horizontal_floor_mo_cqc_knm",
                                    "separate_piers_native_to_floor_mo") if k in row}}
            for z, label in ((top,"RIGID_ENCLOSURE_AND_PERIOD_CONDITIONS_MET"), (bottom,"FOUNDATION_TOP"))
            for st in storeys if close(st["cut_z_m"], z) and st.get("status") == "SIGNED_CUT_BALANCED"
            for row in st.get("directions", ())]
    except (KeyError, IndexError, TypeError, ValueError, ArithmeticError, RuntimeError) as exc:
        result["period_reason"] = str(exc)
    return result
