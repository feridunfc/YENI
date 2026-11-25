"""Recover horizontal section actions from native, unaveraged rectangular shell corner fields."""

from math import dist, isfinite

from .basement_pier_geometry import required
from .gravity_wall_cut import _global_force, joint_action_at_origin
from .wall_transition import TOL, weighted_vectors

IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def _basis(matrix, normal):
    # Identify the local basis by its signed shell-face normal. Some CSI interfaces
    # describe direction cosines by global rows, others by local rows.
    _global_force((0.0, 0.0, 1.0), matrix)  # orthonormal and right handed
    rows = [tuple(matrix[i : i + 3]) for i in (0, 3, 6)]
    choices = [tuple(v) for v in (rows, list(zip(*rows))) if dist(v[2], normal) < 1e-7]
    required(choices and all(max(dist(a,b) for a,b in zip(choices[0],other)) < 1e-10
                             for other in choices[1:]), "SHELL_LOCAL_BASIS_OR_FACE_ORIENTATION_UNRESOLVED")
    return choices[0]


def _traction(values, axes):
    # ETABS shell moments are minus the first stress moment across positive local 3.
    # Use the lower face of an upper free body consistently for all planes.
    a, b, n = axes
    f11, f22, f12, m11, m22, m12, v13, v23 = values
    required(all(isfinite(v) for v in values), "NONFINITE_SHELL_CORNER_RESULTANT")
    u, v = a[2], b[2]
    f1, f2, f3 = f11 * u + f12 * v, f12 * u + f22 * v, v13 * u + v23 * v
    m1, m2 = m11 * u + m12 * v, m12 * u + m22 * v
    return tuple(-(f1 * a[i] + f2 * b[i] + f3 * n[i]) for i in range(3)) + tuple(
        m1 * b[i] - m2 * a[i] for i in range(3)
    )


def _line_element(ends, values, axes, origin):
    """Consistent line weights integrate a linear force and its quadratic moment arm."""
    a, b = ends
    length = dist(a, b)
    left, right = [_traction(v, axes) for v in values]
    result = []
    for pos, near, far in ((a, left, right), (b, right, left)):
        w = [length * (2 * near[i] + far[i]) / 6 for i in range(3)] + [
            length * near[i] / 2 for i in range(3, 6)
        ]
        result.append(joint_action_at_origin(w, IDENTITY, pos, origin))
    return weighted_vectors([(1, v) for v in result])


def recover_panel(fields, mesh, coords, panel, xyz, z, retain_above, cases, origin):
    a, b = [xyz[p] for p in panel["point_ids"][:2]]
    length = dist(a[:2], b[:2])
    dx, dy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    idx = {tuple(k): i for i, k in enumerate(fields["corners"])}
    required(len(idx) == len(fields["corners"]), "DUPLICATE_SHELL_FIELD_CORNER")
    totals = {c: [] for c in cases}
    intervals = []
    for elm, nodes in mesh.items():
        heights = [coords[p][2] for p in nodes]
        lo, hi = min(heights), max(heights)
        active = lo - TOL <= z < hi - TOL if retain_above else lo + TOL < z <= hi + TOL
        if not active:
            continue
        required(len(nodes) == 4 and hi - lo > TOL, "RECTANGULAR_SHELL_FIELD_REQUIRED")

        def station(p):
            return (coords[p][0] - a[0]) * dx + (coords[p][1] - a[1]) * dy

        bottom, top = (
            sorted((p for p in nodes if abs(coords[p][2] - h) <= TOL), key=station) for h in (lo, hi)
        )
        required(
            len(bottom) == len(top) == 2
            and all(dist(coords[i][:2], coords[j][:2]) <= TOL for i, j in zip(bottom, top))
            and all(abs((coords[p][0] - a[0]) * dy - (coords[p][1] - a[1]) * dx) <= TOL for p in nodes),
            "RECTANGULAR_SHELL_FIELD_REQUIRED",
        )
        normal = (dy, -dx, 0.0)
        axes = _basis(fields["axes"][elm], normal)
        fraction = min(1.0, max(0.0, (z - lo) / (hi - lo)))
        ends = [(*coords[p][:2], z) for p in bottom]
        intervals.append(tuple(station(p) for p in bottom))
        for case in cases:
            raw = fields["cases"][case]
            required(len(raw) == len(idx), "SHELL_FIELD_CASE_POPULATION_DIFFERS")
            values = [
                [
                    (1 - fraction) * x + fraction * y
                    for x, y in zip(raw[idx[elm, i]], raw[idx[elm, j]], strict=True)
                ]
                for i, j in zip(bottom, top)
            ]
            totals[case].append(_line_element(ends, values, axes, origin))
    intervals.sort()
    required(
        intervals
        and abs(intervals[0][0]) <= TOL
        and abs(intervals[-1][1] - length) <= TOL
        and all(abs(x[1] - y[0]) <= TOL for x, y in zip(intervals, intervals[1:])),
        "FULL_PHYSICAL_PANEL_SECTION_REQUIRED",
    )
    return {c: weighted_vectors([(1, v) for v in values]) for c, values in totals.items()}


def recover_section(read, plan, panels, mesh, coords, xyz, z, retain_above, combos, origin):
    leaves = {c for terms in combos.values() for c in terms}
    actions = []
    for uid in plan["members"]:
        member = read["members"][uid]
        required("fields" in member, member.get("field_reason", "NATIVE_CORNER_FIELDS_REQUIRED:" + uid))
        actions.append(
            recover_panel(
                member["fields"], mesh[uid], coords, panels[uid], xyz, z, retain_above, leaves, origin
            )
        )
    return {
        name: weighted_vectors([(float(f), a[c]) for a in actions for c, f in terms.items()])
        for name, terms in combos.items()
    }


def uniform_edge_load(plan, mesh, coords, panels, xyz, panel_actions, combination, origin):
    """Project uniform self-weight and normal pressure onto the selected rectangular element edge.

    The bilinear translational shape function of each corner integrates to A/4.
    Normalize to the same lower-face sign as the section and transport each force
    from its own corner. Rotational loads and temperature initial strains are outside this term.
    """
    vectors = []
    sign = 1 if plan["element_face"] == "Bottom" else -1
    for uid, pairs in plan["corners"].items():
        panel = panels[uid]
        actions = panel_actions[uid]
        load = next((r for r in actions["combinations"] if r["combination"] == combination), None)
        required(load is not None and actions["surface_m2"] > 0, "UNIFORM_EDGE_LOAD_SOURCE_REQUIRED")
        a, b = [xyz[p] for p in panel["point_ids"][:2]]
        length = dist(a[:2], b[:2])
        q = load["pressure_kn_m2"]
        density = [
            q * (b[1] - a[1]) / length,
            -q * (b[0] - a[0]) / length,
            -load["self_weight_kn"] / actions["surface_m2"],
        ]
        for element, point in pairs:
            positions = [coords[p] for p in mesh[uid][element]]
            bottom_z, top_z = min(p[2] for p in positions), max(p[2] for p in positions)
            bottom = [p for p in positions if abs(p[2] - bottom_z) <= TOL]
            top = [p for p in positions if abs(p[2] - top_z) <= TOL]
            required(
                len(positions) == 4
                and len(top) == len(bottom) == 2
                and all(any(dist(i[:2], j[:2]) <= TOL for j in top) for i in bottom),
                "RECTANGULAR_SHELL_FIELD_REQUIRED",
            )
            share = dist(bottom[0][:2], bottom[1][:2]) * (top_z - bottom_z) / 4
            force = [share * f for f in density] + [0.0, 0.0, 0.0]
            vectors.append((sign, joint_action_at_origin(force, IDENTITY, coords[point], origin)))
    return weighted_vectors(vectors)
