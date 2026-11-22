"""Project signed ETABS shell joint forces onto the upper side of a horizontal cut."""
from __future__ import annotations

from collections import defaultdict
from math import fsum, isclose, isfinite

from .gravity_story_basis import WALL_FORCE, _CUT_TOL_M, _physical_population


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _real(value):
    return type(value) in (int, float) and isfinite(value)


def _vector(values, size):
    return isinstance(values, (list, tuple)) and len(values) == size and all(_real(v) for v in values)


def _global_force(local_force, matrix):
    _check(_vector(local_force, 3), "WALL_CUT_NONFINITE_FORCE")
    _check(_vector(matrix, 9), "WALL_JOINT_TRANSFORMATION_UNAVAILABLE")
    rows = [matrix[i:i + 3] for i in (0, 3, 6)]
    for i, row in enumerate(rows):
        for j in range(i + 1):
            dot = fsum(a * b for a, b in zip(row, rows[j]))
            _check(isclose(dot, float(i == j), abs_tol=1e-9, rel_tol=0),
                   "WALL_JOINT_TRANSFORMATION_NOT_ORTHONORMAL")
    a, b, c = rows
    determinant = (a[0] * (b[1]*c[2] - b[2]*c[1]) - a[1] * (b[0]*c[2] - b[2]*c[0])
                   + a[2] * (b[0]*c[1] - b[1]*c[0]))
    _check(isclose(determinant, 1., abs_tol=1e-9, rel_tol=0), "WALL_JOINT_TRANSFORMATION_NOT_RIGHT_HANDED")
    return [fsum(a * b for a, b in zip(axis, local_force)) for axis in rows]


def project_upper_wall_forces(source, level, cut_z_m, case_names, *, model_sha256, analysis_generation,
                              area_mesh, joint_xyz, shell_forces, joint_transformations):
    """Return one global resultant per physical wall and explicit first-order case.

    The native rows are [object, element, point, case, step type, step number,
    F1, F2, F3, M1, M2, M3]. Point-element matrices map local forces to global.
    An element may participate only on a complete bottom edge of the upper body.
    A wall crossed within a shell needs a different section-integration method.
    """
    _check(model_sha256 == level["model_sha256"] and analysis_generation == level["analysis_generation"],
           "WALL_CUT_MODEL_GENERATION_MISMATCH")
    _check(_real(cut_z_m) and case_names and len(set(case_names)) == len(case_names), "WALL_CUT_CASE_OR_PLANE_INVALID")
    cases = set(case_names)
    population, *_ = _physical_population(source, cut_z_m)
    walls = {uid for kind, uid in population if kind == "WALL"}
    edges = defaultdict(set)
    mesh_ids = set()
    for row in area_mesh:
        uid, element = row["ObjName"], row["ElmName"]
        if row["ObjType"] != "Wall" or uid not in walls:
            continue
        _check(element not in mesh_ids, "WALL_CUT_DUPLICATE_SHELL_ELEMENT")
        mesh_ids.add(element)
        points = [row.get(k) for k in ("ElmJt1", "ElmJt2", "ElmJt3", "ElmJt4")]
        points = [p for p in points if p not in (None, "", "None")]
        _check(len(points) in (3, 4) and len(set(points)) == len(points)
               and all(_vector(joint_xyz.get(p), 3) for p in points), "WALL_CUT_GEOMETRY_UNAVAILABLE")
        elevations = [joint_xyz[p][2] for p in points]
        if max(elevations) <= cut_z_m + _CUT_TOL_M:
            continue
        _check(min(elevations) >= cut_z_m - _CUT_TOL_M, "WALL_CUT_INSIDE_SHELL_NOT_SUPPORTED")
        on_plane = {p for p, z in zip(points, elevations) if abs(z - cut_z_m) <= _CUT_TOL_M}
        if not on_plane:
            continue
        _check(len(on_plane) == 2 and any({a, b} == on_plane for a, b in zip(points, points[1:] + points[:1])),
               "WALL_CUT_PARTIAL_EDGE_NOT_SUPPORTED")
        edges[uid].update((element, point) for point in on_plane)
    _check(set(edges) == walls, "WALL_CUT_PHYSICAL_BOUNDARY_INCOMPLETE")

    rows = []
    for uid in sorted(walls):
        indexed = {}
        for raw in shell_forces[uid]:
            _check(len(raw) == 12 and raw[0] == uid, "WALL_CUT_NATIVE_FORCE_SHAPE_OR_OBJECT_INVALID")
            _, element, point, case, step, number, *components = raw
            if (element, point) not in edges[uid]:
                continue
            _check(case in cases and step == "Step" and _real(number) and number == 1,
                   "WALL_CUT_CASE_OR_STEP_MISMATCH")
            _check(_vector(components, 6), "WALL_CUT_NONFINITE_FORCE")
            key = case, element, point
            _check(key not in indexed, "WALL_CUT_DUPLICATE_FORCE")
            indexed[key] = _global_force(components[:3], joint_transformations.get(point))
        for case in sorted(cases):
            edge_keys = [(case, e, p) for e, p in sorted(edges[uid])]
            _check(all(k in indexed for k in edge_keys), "WALL_CUT_NATIVE_FORCE_MISSING")
            vector = [fsum(indexed[k][i] for k in edge_keys) for i in range(3)]
            rows.append({"kind": "WALL", "object_id": uid, "element_id": "upper edges " +
                         ",".join(sorted({e for e, _ in edges[uid]})), "case": case, "step_type": "Step",
                         "step_number": 1, "z_m": cut_z_m, "representation": WALL_FORCE, "vector_kn": vector})
    return rows
