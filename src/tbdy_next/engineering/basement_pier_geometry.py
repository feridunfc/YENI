"""Physical web sections between the supporting columns of a folded basement pier."""
from collections import Counter, defaultdict
from itertools import pairwise
from math import cos, dist, fsum, hypot, isclose, isfinite, radians, sin
import re

from ..etabs_geometry import AREA_INSERTION, FRAME_INSERTION
from .column_clear_length import _FRAME_TRANSLATION, _SHELL_TRANSLATION, _index, _no_translation, _records, _translation_fields


def required(ok, reason):
    if not ok:
        raise ValueError(reason)


def close(a, b, tol=1e-7):
    return isclose(a, b, rel_tol=0, abs_tol=tol)


def _bounds(a, b, thickness):
    x, y = a
    u, v = b
    if close(x, u) and not close(y, v):
        return (x-thickness/2, x+thickness/2, min(y, v), max(y, v))
    if close(y, v) and not close(x, u):
        return (min(x, u), max(x, u), y-thickness/2, y+thickness/2)
    raise ValueError("ORTHOGONAL_FULL_HEIGHT_WEB_REQUIRED")


def _intersection(a, b):
    return max(0., min(a[1], b[1])-max(a[0], b[0])) * max(0., min(a[3], b[3])-max(a[2], b[2]))


def _union(rects):
    # Integrate the union once, including the inside corners of perpendicular webs.
    xs = sorted({v for r in rects for v in r[:2]})
    area = 0.
    for x0, x1 in pairwise(xs):
        ys = sorted((r[2], r[3]) for r in rects if r[0] < x1 and r[1] > x0)
        last = -float("inf")
        for low, high in ys:
            area += (x1-x0) * max(0., high-max(last, low))
            last = max(last, high)
    return area


def _context(source):
    geom = source["vs06_b1_geometry_source"]["table_reads"]
    native = source["column_axial"]["r10_source"]["table_reads"]
    fields = ("X", "Y", "Z")
    xyz = {q["UniqueName"]: tuple(float(q[k]) for k in fields)
           for q in _records(geom, "Point Object Connectivity", "UniqueName X Y Z", fields)}
    walls = _index(_records(geom, "Wall Object Connectivity", "UniqueName WallBay Story UniquePt1 UniquePt2 UniquePt3 UniquePt4"), "UniqueName")
    assignments = _index(_records(geom, "Area Assignments - Section Properties", "UniqueName SectProp"), "UniqueName")
    props = _index(_records(geom, "Wall Property Definitions - Specified", "Name Material Thickness", ("Thickness",)), "Name")
    shape = _index(_records(geom, "Frame Section Property Definitions - Concrete Rectangular", "Name t2 t3", ("t2", "t3")), "Name")
    frames = _index(_records(geom, "Frame Assignments - Section Properties", "UniqueName SectProp"), "UniqueName")
    angles = _index(_records(source["geometry_capture"]["tables"], "FRAME_ASSIGNMENTS", "UniqueName AxisAngle"), "UniqueName")
    columns = _records(geom, "Column Object Connectivity", "UniqueName Story UniquePtI UniquePtJ")
    offset = _translation_fields(native[FRAME_INSERTION], 1, _FRAME_TRANSLATION, ("OffsetCSys",))
    insert = _index(_records(native, FRAME_INSERTION, "UniqueName CardinalPt Story"), "UniqueName")
    shell_fields = _translation_fields(native[AREA_INSERTION], 2, _SHELL_TRANSLATION, ("CoordSys", "PointLabel", "PointName", "PointNumber"))
    wall_inserts = defaultdict(list)
    for row in _records(native, AREA_INSERTION, "UniqueName CardinalPt Story"):
        wall_inserts[row["UniqueName"]].append(row)
    return xyz, walls, assignments, props, shape, frames, angles, columns, offset, insert, shell_fields, wall_inserts


def folded_section(source, bound, name, story, member_ids):
    xyz, walls, assignments, props, shape, frames, angles, columns, offsets, insert, sf, shell_insert = _context(source)
    assigned = bound["assignments"].get((name, story), [])
    required(sorted(assigned) == sorted(member_ids), "NATIVE_AND_ARCHIVED_PIER_MEMBERSHIP_DIFFER")
    properties = bound["properties"].get((name, story), [])
    required(len(properties) == 1, "ONE_NATIVE_PIER_PROPERTY_AT_THE_STOREY_REQUIRED")
    native = properties[0]
    required(int(native["NumLineObj"]) == 0 and int(native["NumAreaObj"]) == len(member_ids)
             and not any(re.search(r'\bPIER\s+"' + re.escape(name) + r'"', line)
                         for line in bound["deck"].splitlines() if line.lstrip().startswith("LINEASSIGN ")),
             "SEPARATE_SHELL_AND_FRAME_RESULTANTS_REQUIRED")
    required(bool(re.search(r'^\s*UNITS\s+"KN"\s+"M"\s+"C"\s*$', bound["deck"], re.M)), "ARCHIVED_DECK_UNITS_REQUIRED")
    footprints, supports = {}, defaultdict(list)
    for col in columns:
        if col["Story"] != story:
            continue
        uid = col["UniqueName"]
        a, b = xyz[col["UniquePtI"]], xyz[col["UniquePtJ"]]
        placement = insert[uid]
        angle = angles[uid]["AxisAngle"]
        required(a[:2] == b[:2] and a[2] < b[2] and placement["CardinalPt"] in {"10 (Centroid)", "5 (Middle Center)"}
                 and _no_translation(placement, offsets), "VERTICAL_CENTRED_COLUMN_FOOTPRINT_REQUIRED")
        rotation = 0. if angle in ("None", None, "") else float(angle)
        required(isfinite(rotation) and close(rotation/90, round(rotation/90)), "ORTHOGONAL_COLUMN_FOOTPRINT_REQUIRED")
        sec = shape[frames[uid]["SectProp"]]
        # A vertical CSI frame at zero rotation has local 2 along global X; native t3 lies along local 2.
        wx, wy = float(sec["t3"]), float(sec["t2"])
        if round(rotation/90) % 2:
            wx, wy = wy, wx
        required(all(isfinite(n) and n > 0 for n in (wx, wy)), "POSITIVE_COLUMN_DIMENSIONS_REQUIRED")
        footprints[uid] = (a[0]-wx/2, a[0]+wx/2, a[1]-wy/2, a[1]+wy/2)
        supports[a[:2]].append((uid, col["UniquePtI"], col["UniquePtJ"]))
    levels = {(xyz[walls[uid]["UniquePt1"]][2], xyz[walls[uid]["UniquePt4"]][2]) for uid in member_ids}
    required(len(levels) == 1, "WALL_BASE_OR_TOP_CHANGES_WITHIN_PIER")
    bottom, top = levels.pop()
    required(bottom < 0 and close(top, 0.), "SINGLE_BASEMENT_ENDING_AT_PROJECT_ZERO_REQUIRED")
    panels, strips, strips_clear, ends = [], [], [], Counter()
    for uid in member_ids:
        row = walls[uid]
        prop = props[assignments[uid]["SectProp"]]
        thick = float(prop["Thickness"])
        required(prop["Material"] == native["Material"] and isfinite(thick) and thick > 0
                 and shell_insert[uid] and all(z["CardinalPt"] == "Middle" and _no_translation(z, sf) for z in shell_insert[uid]),
                 "WALL_MATERIAL_THICKNESS_OR_INSERTION_UNQUALIFIED")
        i, j, jt, it = [row["UniquePt"+str(n)] for n in (1, 2, 3, 4)]
        a, b, upper_b, upper_a = [xyz[k] for k in (i, j, jt, it)]
        required(a[:2] == upper_a[:2] and b[:2] == upper_b[:2] and a[2] == b[2] < upper_b[2] == upper_a[2],
                 "VERTICAL_RECTANGULAR_WALL_REQUIRED")
        rect = _bounds(a[:2], b[:2], thick)
        required(len(supports[a[:2]]) == len(supports[b[:2]]) == 1,
                 "EACH_PANEL_END_REQUIRES_ONE_REGISTERED_SUPPORT_COLUMN")
        left, li, lt = supports[a[:2]][0]
        right, ri, rt = supports[b[:2]][0]
        required((li, lt, ri, rt) == (i, it, j, jt), "WALL_COLUMN_SHARED_END_JOINTS_REQUIRED")
        ends.update((i, j))
        length = dist(a[:2], b[:2])
        dx, dy = (b[0]-a[0])/length, (b[1]-a[1])/length
        def reach(col):
            x0, x1, y0, y1 = footprints[col]
            required(abs(dy)*(x1-x0) + abs(dx)*(y1-y0) >= thick-1e-9, "COLUMN_MUST_COVER_WEB_THICKNESS")
            return (abs(dx)*(x1-x0) + abs(dy)*(y1-y0))/2
        l, r = reach(left), reach(right)
        clear_a, clear_b = (a[0]+dx*l, a[1]+dy*l), (b[0]-dx*r, b[1]-dy*r)
        required(length-l-r > 0, "NO_CLEAR_WALL_BETWEEN_COLUMN_FACES")
        clear_rect = _bounds(clear_a, clear_b, thick)
        required(all(_intersection(clear_rect, footprint) < 1e-9 for footprint in footprints.values()),
                 "ANOTHER_COLUMN_INTERSECTS_CLEAR_WEB")
        panels.append({"member": uid, "wall": row["WallBay"], "joint_i": i, "joint_j": j, "column_i": left, "column_j": right,
            "span_m": length, "thickness_m": thick, "clear_length_m": length-l-r, "width_direction": [dx, dy],
            "clear_centroid_xy_m": [(u+v)/2 for u,v in zip(clear_a, clear_b)], "clear_bounds_xy_m": list(clear_rect)})
        strips.append(rect)
        strips_clear.append(clear_rect)
    # Two end points, no branch, and only one connected graph.
    reached = {panels[0]["joint_i"]}
    for _ in panels:
        for p in panels:
            edge = {p["joint_i"], p["joint_j"]}
            if edge & reached:
                reached.update(edge)
    required(len(reached) == len(ends) and sorted(ends.values()) == [1,1]+[2]*(len(ends)-2),
             "CONTINUOUS_NONBRANCHING_WALL_PLAN_REQUIRED")
    nominal = sum(p["span_m"]*p["thickness_m"] for p in panels)
    net_area = sum(p["clear_length_m"]*p["thickness_m"] for p in panels)
    required(close(_union(strips_clear), net_area), "CLEAR_WALL_STRIPS_OVERLAP")
    for uid, row in walls.items():
        if uid in member_ids or row["Story"] != story:
            continue
        prop = props[assignments[uid]["SectProp"]]
        a, b, upper_b, upper_a = [xyz[row["UniquePt"+str(n)]][:2] for n in (1,2,3,4)]
        required(a == upper_a and b == upper_b and shell_insert[uid]
                 and all(z["CardinalPt"] == "Middle" and _no_translation(z, sf) for z in shell_insert[uid]),
                 "FOREIGN_WALL_FOOTPRINT_UNRESOLVED")
        other = _bounds(a,b,float(prop["Thickness"]))
        required(all(_intersection(other, clear_rect) < 1e-9 for clear_rect in strips_clear), "FOREIGN_WALL_INTERSECTS_CLEAR_WEB")
    angle = radians(float(native["AxisAngle"]))
    axes = [cos(angle), sin(angle)]
    required(all(isfinite(v) for v in axes), "NATIVE_PIER_AXIS_UNRESOLVED")
    positions = [xyz[node] for node in ends]
    width = max(x*axes[0]+y*axes[1] for x,y,z in positions) - min(x*axes[0]+y*axes[1] for x,y,z in positions)
    required(width > 0, "NATIVE_PIER_PROJECTED_LENGTH_UNRESOLVED")
    nominal_cg = [fsum(p["span_m"]*p["thickness_m"]*(xyz[p["joint_i"]][k]+xyz[p["joint_j"]][k])/2
                        for p in panels)/nominal for k in (0,1)]
    face_origins = {}
    for face, key, z in (("Bottom","Bot",bottom),("Top","Top",top)):
        cx, cy, cz = (float(native["CG"+key+k]) for k in "XYZ")
        # The source table rounds these fields to the displayed millimetre or better.
        required(close(cx, nominal_cg[0], .00051) and close(cy, nominal_cg[1], .00051) and close(cz, z, .00051)
                 and close(float(native["Width"+key]), width, .00051)
                 and close(float(native["Thick"+key]), nominal/width, .000051), "NATIVE_PIER_FACE_PROPERTIES_DIFFER")
        face_origins[face] = [cx,cy,cz]
    return {"panels": panels, "bottom_m":bottom, "top_m":top, "native_axes_2_xy":axes, "native_face_origins_m":face_origins,
            "nominal_area_m2": nominal, "shell_footprint_union_m2": _union(strips), "clear_web_area_m2":net_area,
            "net_centroid_xy_m":[fsum(p["clear_length_m"]*p["thickness_m"]*p["clear_centroid_xy_m"][k]
                                     for p in panels)/net_area for k in (0,1)],
            "reserved_column_ids":sorted({p[key] for p in panels for key in ("column_i","column_j")}),
            "material":native["Material"], "projected_length_m":width, "height_over_length":(top-bottom)/width}
