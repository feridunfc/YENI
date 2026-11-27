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


def _column_footprints(context, story):
    xyz, _, _, _, shape, frames, angles, columns, offsets, insert, _, _ = context
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
    return footprints, supports


def pier_membership(bound, name, story, member_ids):
    required(sorted(bound["assignments"].get((name, story), [])) == sorted(member_ids), "NATIVE_AND_ARCHIVED_PIER_MEMBERSHIP_DIFFER")
    properties = bound["properties"].get((name, story), [])
    required(len(properties) == 1, "ONE_NATIVE_PIER_PROPERTY_AT_THE_STOREY_REQUIRED")
    native = properties[0]
    required(int(native["NumLineObj"]) == 0 and int(native["NumAreaObj"]) == len(member_ids)
             and not any(re.search(r'\bPIER\s+"' + re.escape(name) + r'"', line)
                         for line in bound["deck"].splitlines() if line.lstrip().startswith("LINEASSIGN ")),
             "SEPARATE_SHELL_AND_FRAME_RESULTANTS_REQUIRED")
    return native


def _overlap_area(strips, obstacles):
    return _union([(max(s[0],r[0]), min(s[1],r[1]), max(s[2],r[2]), min(s[3],r[3]))
                   for s in strips for r in obstacles if _intersection(s,r) > 0])


def cut_web_area(context, columns, native, member_ids, face):
    """One-sided horizontal shell footprint with overlapping columns reserved once."""
    z = float(native["CGBotZ" if face == "Bottom" else "CGTopZ"])
    return web_area_at(context, columns, member_ids, z, face, native["Material"])


def web_area_at(context, columns, member_ids, z, face, material):
    xyz, walls, assignments, props, _, _, _, _, _, _, fields, inserts = context
    oriented, thicknesses = defaultdict(list), defaultdict(list)
    strips, contributing = [], []
    for uid in member_ids:
        row = walls[uid]
        a, b, high_b, high_a = [xyz[row["UniquePt"+str(i)]] for i in (1,2,3,4)]
        prop = props[assignments[uid]["SectProp"]]
        required(a[:2] == high_a[:2] and b[:2] == high_b[:2] and a[2] == b[2] < high_a[2] == high_b[2],
                 "VERTICAL_RECTANGULAR_WALL_REQUIRED")
        if not (a[2]-1e-7 <= z < high_a[2]-1e-7 if face == "Bottom" else a[2]+1e-7 < z <= high_a[2]+1e-7):
            continue
        thick = float(prop["Thickness"])
        required(isfinite(thick) and thick > 0 and prop["Material"] == material and inserts[uid]
                 and all(r["CardinalPt"] == "Middle" and _no_translation(r, fields) for r in inserts[uid]),
                 "WALL_MATERIAL_THICKNESS_OR_INSERTION_UNQUALIFIED")
        strips.append(_bounds(a[:2], b[:2], thick))
        axis = "X" if close(a[1], b[1]) else "Y"
        oriented[axis].append(strips[-1])
        thicknesses[axis].append(thick)
        contributing.append(uid)
    reserved = []
    for uid, rect in columns.items():
        col = next(r for r in context[7] if r["UniqueName"] == uid)
        low, high = (xyz[col[k]][2] for k in ("UniquePtI","UniquePtJ"))
        if not (low-1e-7 <= z < high-1e-7 if face == "Bottom" else low+1e-7 < z <= high+1e-7):
            continue
        reserved.append(rect)
    gross, overlap = _union(strips), _overlap_area(strips, reserved)
    required(gross > overlap, "POSITIVE_NET_WALL_CUT_AREA_REQUIRED")
    webs = {}
    for axis, other in (("X","Y"),("Y","X")):
        if oriented[axis]:
            net = _union(oriented[axis]) - _overlap_area(oriented[axis], reserved+oriented[other])
            if net > 0:
                webs[axis] = {"net_m2": net, "maximum_thickness_m": max(thicknesses[axis])}
    return {"z_m": z, "members": contributing, "shell_union_m2": gross, "column_overlap_m2": overlap,
            "net_m2": gross-overlap, "directional_webs": webs}


def panel_profile(context, columns, member_ids):
    """Separate the assigned shell property from the panels present at each elevation."""
    xyz, walls, assignments, props = context[:4]
    ends = defaultdict(set)
    for uid, r in walls.items():
        for a,b in ((1,4),(2,3)):
            ends[frozenset((r["UniquePt"+str(a)],r["UniquePt"+str(b)]))].add(uid)
    panels = []
    for uid in member_ids:
        r = walls[uid]
        i,j,k,l = [r["UniquePt"+str(n)] for n in range(1,5)]
        section = assignments[uid]["SectProp"]
        panels.append({"member":uid, "label":r["WallBay"], "section":section, "material":props[section]["Material"],
                       "thickness_m":float(props[section]["Thickness"]), "bottom_m":xyz[i][2], "top_m":xyz[l][2],
                       "length_m":dist(xyz[i],xyz[j]), "point_ids":[i,j,k,l],
                       "i_edge_wall_ids":sorted(ends[frozenset((i,l))]-{uid}),
                       "j_edge_wall_ids":sorted(ends[frozenset((j,k))]-{uid})})
    levels = sorted({z for p in panels for z in (p["bottom_m"],p["top_m"])})
    materials = {p["material"] for p in panels}
    required(len(materials)==1,"SINGLE_WEB_MATERIAL_REQUIRED")
    bands = []
    for lo,hi in pairwise(levels):
        cut = web_area_at(context,columns,member_ids,lo,"Bottom",next(iter(materials)))
        bands.append({"bottom_m":lo,"top_m":hi,"members":cut["members"],"net_area_m2":cut["net_m2"],
                      "shell_area_m2":cut["shell_union_m2"]})
    return {"panels":panels,"bands":bands}


def support_id(panel, side):
    return panel.get("support_sections", {}).get(side, {}).get("support_id") or panel["column_"+side.lower()]


def _wall_edge(context, uid, joint, opposite, direction, material):
    xyz, walls, assignments, props = context[:4]
    fields, inserts = context[-2:]
    incident = []
    for other, row in walls.items():
        if other == uid:
            continue
        points = [row["UniquePt"+str(n)] for n in (1,2,3,4)]
        for low, high, remote in ((points[0],points[3],points[1]),(points[1],points[2],points[0])):
            if (low, high) != (joint, opposite):
                continue
            a, b = xyz[joint], xyz[remote]
            length = dist(a[:2],b[:2])
            prop = props[assignments[other]["SectProp"]]
            thick = float(prop["Thickness"])
            required(length>0 and close(a[2],b[2]) and thick>0 and prop["Material"] == material
                     and inserts[other] and all(r["CardinalPt"]=="Middle" and _no_translation(r, fields)
                     for r in inserts[other]), "WALL_RETURN_GEOMETRY_UNBOUND")
            unit = [(b[k]-a[k])/length for k in (0,1)]
            alignment = abs(sum(x*y for x,y in zip(direction,unit)))
            required(close(alignment,0) or close(alignment,1), "ORTHOGONAL_RETURN_REQUIRED")
            incident.append({"member":other,"wall":row["WallBay"],"across":close(alignment,0),
                             "thickness_mm":thick*1000,"span_mm":length*1000,"direction":unit,"remote_joint":remote})
    required(incident, "NATIVE_SHARED_VERTICAL_SUPPORT_REQUIRED")
    depth = max((v["thickness_mm"] for v in incident if v["across"]), default=0.)
    return {"kind":"WALL_JUNCTION","support_id":"joint "+joint,"column":None,"joint":joint,"upper_joint":opposite,
            "material":material,"depth_mm":depth,"incident_walls":incident}


def _link_panel(context, uid):
    xyz, walls, assignments, props = context[:4]
    row = walls[uid]
    i,j,jt,it = [row["UniquePt"+str(k)] for k in (1,2,3,4)]
    a,b = xyz[i],xyz[j]
    length = dist(a[:2],b[:2])
    direction = tuple((b[k]-a[k])/length for k in (0,1))
    prop = props[assignments[uid]["SectProp"]]
    return {"member":uid,"wall":row["WallBay"],"width_direction":direction,"joint_i":i,"joint_j":j,
            "column_i":None,"column_j":None,"span_m":length,"thickness_m":float(prop["Thickness"]),"support_sections":{
            side:_wall_edge(context,uid,pt,high,direction,prop["Material"]) for side,pt,high in (("I",i,it),("J",j,jt))}}


def _stepped_wall_seam(context, uid, joint, opposite, direction, material, member_ids):
    xyz, walls, assignments, props = context[:4]
    fields, inserts = context[-2:]
    z0, z1 = sorted((xyz[joint][2], xyz[opposite][2]))
    xy = xyz[joint][:2]
    incident = []
    for other in member_ids:
        if other == uid:
            continue
        row = walls[other]
        points = [row["UniquePt"+str(n)] for n in (1,2,3,4)]
        for low, high, remote in ((points[0],points[3],points[1]),(points[1],points[2],points[0])):
            if dist(xyz[low][:2], xy) > 1e-7 or dist(xyz[high][:2], xy) > 1e-7:
                continue
            oz0, oz1 = sorted((xyz[low][2], xyz[high][2]))
            if min(z1, oz1) - max(z0, oz0) <= 1e-7 or not ({joint, opposite} & {low, high}):
                continue
            a, b = xyz[low], xyz[remote]
            length = dist(a[:2], b[:2])
            prop = props[assignments[other]["SectProp"]]
            thick = float(prop["Thickness"])
            required(length > 0 and close(a[2], b[2]) and thick > 0 and prop["Material"] == material
                     and inserts[other] and all(r["CardinalPt"] == "Middle" and _no_translation(r, fields)
                     for r in inserts[other]), "WALL_RETURN_GEOMETRY_UNBOUND")
            unit = [(b[k]-a[k])/length for k in (0, 1)]
            alignment = abs(sum(x*y for x, y in zip(direction, unit)))
            required(close(alignment, 0) or close(alignment, 1), "ORTHOGONAL_RETURN_REQUIRED")
            incident.append({"member":other, "wall":row["WallBay"], "across":close(alignment, 0),
                             "thickness_mm":thick*1000, "span_mm":length*1000, "direction":unit, "remote_joint":remote,
                             "overlap_z_m":[max(z0, oz0), min(z1, oz1)]})
    required(incident, "NATIVE_SHARED_VERTICAL_SUPPORT_REQUIRED")
    return {"kind":"STEPPED_WALL_SEAM", "support_id":"seam "+joint, "column":None, "joint":joint,
            "upper_joint":opposite, "material":material, "depth_mm":0., "incident_walls":incident}


def folded_section(source, bound, name, story, member_ids):
    context = _context(source)
    xyz, walls, assignments, props, shape, frames, angles, _, _, _, sf, shell_insert = context
    native = pier_membership(bound, name, story, member_ids)
    required(bool(re.search(r'^\s*UNITS\s+"KN"\s+"M"\s+"C"\s*$', bound["deck"], re.M)), "ARCHIVED_DECK_UNITS_REQUIRED")
    footprints, supports = _column_footprints(context, story)
    levels = {(xyz[walls[uid]["UniquePt1"]][2], xyz[walls[uid]["UniquePt4"]][2]) for uid in member_ids}
    stepped = len(levels) > 1
    bottom = min(lo for lo, _ in levels)
    top = max(hi for _, hi in levels)
    required(bottom < 0 and close(top, 0.)
             and all(bottom-1e-7 <= lo < hi <= top+1e-7 for lo, hi in levels),
             "SINGLE_BASEMENT_ENDING_AT_PROJECT_ZERO_REQUIRED")
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
        ends.update((i, j))
        length = dist(a[:2], b[:2])
        dx, dy = (b[0]-a[0])/length, (b[1]-a[1])/length
        support_sections = {}
        for side, pt, high in (("I",i,it),("J",j,jt)):
            candidates = supports[xyz[pt][:2]]
            if not candidates:
                try:
                    support_sections[side] = _wall_edge(context, uid, pt, high, (dx,dy), prop["Material"])
                except ValueError as exc:
                    if not stepped or str(exc) != "NATIVE_SHARED_VERTICAL_SUPPORT_REQUIRED":
                        raise
                    support_sections[side] = _stepped_wall_seam(context, uid, pt, high, (dx,dy), prop["Material"], member_ids)
                continue
            shared_full = len(candidates) == 1 and candidates[0][1:] == (pt, high)
            shared_stepped = (stepped and len(candidates) == 1
                              and xyz[candidates[0][1]][2]-1e-7 <= a[2] < upper_a[2] <= xyz[candidates[0][2]][2]+1e-7
                              and (pt == candidates[0][1] or high == candidates[0][2]))
            required(shared_full or shared_stepped, "WALL_COLUMN_SHARED_END_JOINTS_REQUIRED")
            col = candidates[0][0]
            x0, x1, y0, y1 = footprints[col]
            required(abs(dy)*(x1-x0) + abs(dx)*(y1-y0) >= thick-1e-9, "COLUMN_MUST_COVER_WEB_THICKNESS")
            section_name = frames[col]["SectProp"]
            angle = angles[col]["AxisAngle"]
            support_sections[side] = {"column":col, "section":section_name, "material":shape[section_name]["Material"],
                "depth_mm":1000*(abs(dx)*(x1-x0)+abs(dy)*(y1-y0)),
                "axis_angle_deg":float(angle) if angle not in ("None",None,"") else 0.}
        l, r = (support_sections[s]["depth_mm"]/2000 for s in ("I","J"))
        left, right = (support_sections[s]["column"] for s in ("I","J"))
        clear_a, clear_b = (a[0]+dx*l, a[1]+dy*l), (b[0]-dx*r, b[1]-dy*r)
        required(length-l-r > 0, "NO_CLEAR_WALL_BETWEEN_COLUMN_FACES")
        clear_rect = _bounds(clear_a, clear_b, thick)
        required(all(_intersection(clear_rect, footprint) < 1e-9 for footprint in footprints.values()),
                 "ANOTHER_COLUMN_INTERSECTS_CLEAR_WEB")
        panels.append({"member": uid, "wall": row["WallBay"], "joint_i": i, "joint_j": j,
            "upper_joint_i": it, "upper_joint_j": jt, "bottom_m": a[2], "top_m": upper_a[2],
            "column_i": left, "column_j": right,
            "support_sections": support_sections,
            "section_name": prop["Name"], "shell_model": prop.get("ModelType"), "span_m": length, "thickness_m": thick, "clear_length_m": length-l-r, "width_direction": [dx, dy],
            "clear_centroid_xy_m": [(u+v)/2 for u,v in zip(clear_a, clear_b)], "clear_bounds_xy_m": list(clear_rect)})
        strips.append(rect)
        strips_clear.append(clear_rect)
    # Two end points, no branch, and only one connected graph.
    assigned = {uid for uids in bound["assignments"].values() for uid in uids}
    links = {}
    for p in panels:
        for s in p["support_sections"].values():
            for adj in s.get("incident_walls", []):
                if adj["member"] not in assigned and adj["remote_joint"] in ends:
                    links[adj["member"]] = tuple(sorted((s["joint"],adj["remote_joint"])))
    canon = {}
    for node in ends:
        key = (round(xyz[node][0], 6), round(xyz[node][1], 6)) if stepped else node
        canon[node] = canon.setdefault(key, node)
    plan_ends = Counter()
    for p in panels:
        plan_ends.update((canon[p["joint_i"]], canon[p["joint_j"]]))
    graph = [(canon[p["joint_i"]], canon[p["joint_j"]]) for p in panels] + [(canon[u], canon[v]) for u, v in links.values()]
    for u, v in links.values():
        plan_ends.update((canon[u], canon[v]))
    reached = {canon[panels[0]["joint_i"]]}
    for _ in panels:
        for pair in graph:
            edge = set(pair)
            if edge & reached:
                reached.update(edge)
    required(len(reached) == len(plan_ends) and sorted(plan_ends.values()) == [1,1]+[2]*(len(plan_ends)-2),
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
    face_origins, face_sections = {}, {}
    for face, key, z in (("Bottom","Bot",bottom),("Top","Top",top)):
        active = [p for p in panels if (p["bottom_m"]-1e-7 <= z < p["top_m"]-1e-7 if face == "Bottom"
                                        else p["bottom_m"]+1e-7 < z <= p["top_m"]+1e-7)]
        required(bool(active), "POSITIVE_NET_WALL_CUT_AREA_REQUIRED")
        active_pos = [xyz[node] for p in active for node in (p["joint_i"], p["joint_j"])]
        active_width = max(x*axes[0]+y*axes[1] for x,y,_ in active_pos) - min(x*axes[0]+y*axes[1] for x,y,_ in active_pos)
        active_nom = fsum(p["span_m"]*p["thickness_m"] for p in active)
        active_cg = [fsum(p["span_m"]*p["thickness_m"]*(xyz[p["joint_i"]][k]+xyz[p["joint_j"]][k])/2
                          for p in active)/active_nom for k in (0,1)]
        active_net = fsum(p["clear_length_m"]*p["thickness_m"] for p in active)
        cx, cy, cz = (float(native["CG"+key+k]) for k in "XYZ")
        # The source table rounds these fields to the displayed millimetre or better.
        required(close(cx, active_cg[0], .00051) and close(cy, active_cg[1], .00051) and close(cz, z, .00051)
                 and close(float(native["Width"+key]), active_width, .00051)
                 and close(float(native["Thick"+key]), active_nom/active_width, .000051), "NATIVE_PIER_FACE_PROPERTIES_DIFFER")
        face_origins[face] = [cx,cy,cz]
        face_sections[face] = {"members": [p["member"] for p in active], "nominal_area_m2": active_nom,
            "clear_web_area_m2": active_net,
            "net_centroid_xy_m": [fsum(p["clear_length_m"]*p["thickness_m"]*p["clear_centroid_xy_m"][k]
                                       for p in active)/active_net for k in (0,1)]}
    for panel in panels:
        panel["folded_pier_length_m"] = width
    transfer = {uid:_link_panel(context,uid) for uid in links}
    reviewed = (source.get("analysis_archive") or {}).get("observed_edb_sha256") == "0ce0e970988def9776f9d4804b8897f6e08d6ac3e4937aa72ebec941314cfb15"
    for panel in panels:
        for end in panel["support_sections"].values():
            if end.get("kind") != "WALL_JUNCTION":
                continue
            end["full_corner_square"] = reviewed and end["joint"] in {"947","953","949"} and close(end["depth_mm"],400.) and close(panel["thickness_m"],.4)
            for leg in end["incident_walls"]:
                link = transfer.get(leg["member"])
                if link:
                    remote = next(e for e in link["support_sections"].values() if e["joint"]==leg["remote_joint"])
                    leg["continuations"] = remote["incident_walls"]
    return {"panels": panels, "bottom_m":bottom, "top_m":top, "stepped": stepped, "face_sections": face_sections,
            "native_axes_2_xy":axes, "native_face_origins_m":face_origins,
            "nominal_area_m2": nominal, "shell_footprint_union_m2": _union(strips), "clear_web_area_m2":net_area,
            "net_centroid_xy_m":[fsum(p["clear_length_m"]*p["thickness_m"]*p["clear_centroid_xy_m"][k]
                                     for p in panels)/net_area for k in (0,1)],
            "connectivity_links":links, "transfer_panels":list(transfer.values()),
            "reserved_column_ids":sorted({p[key] for p in panels for key in ("column_i","column_j") if p[key]}),
            "material":native["Material"], "projected_length_m":width, "height_over_length":(top-bottom)/width}
