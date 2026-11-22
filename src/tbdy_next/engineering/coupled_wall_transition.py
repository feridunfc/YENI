"""First-order cut resultants for a vertical frame at a stepped pair of coplanar walls."""
from __future__ import annotations

from collections import Counter, defaultdict
from math import fsum
import re

from .design_scenario import _digest
from .gravity_wall_cut import _check, _real, _vector, joint_action_at_origin

SCHEMA = "tbdy.next.coupled-wall-transition.v1"
DESIGN_SCHEMA = "tbdy.next.coupled-wall-transition.v2"
COMPONENTS = ("N", "V2", "V3", "T", "M2", "M3")
SIGNED_CASES = ("LC_DL", "LC_EQX", "LC_EQY", "LC_H", "LC_HE", "LC_T")
# Common axes are +Z, +X, +Y. All moments follow the right-hand rule.
INDEX = (2, 0, 1, 5, 3, 4)
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
EPS = 1e-7
MESH_ABS, MESH_REL = .05, .01
BALANCE_ABS, BALANCE_REL = .01, 1e-6


def normalize_transition(raw, *, source_data_sha256):
    _check(isinstance(raw, dict) and raw.get("schema") in (SCHEMA, DESIGN_SCHEMA)
           and raw.get("source_data_sha256") == source_data_sha256, "TRANSITION_SOURCE_MISMATCH")
    _check(isinstance(raw.get("member_id"), str) and raw["member_id"]
           and _vector(raw.get("origin_m"), 3) and _vector(raw.get("bracket_m"), 2)
           and raw["bracket_m"][0] < raw["origin_m"][2] < raw["bracket_m"][1], "TRANSITION_PLANES_INVALID")
    if raw["schema"] == DESIGN_SCHEMA:
        from .transition_design_trace import checked_trace
        checked_trace(raw)
    else:
        _check("design_trace" not in raw, "TRANSITION_UNVERSIONED_DESIGN_TRACE")
    cases = raw.get("cases")
    _check(isinstance(cases, dict) and set(cases) == set(SIGNED_CASES) and all(
        isinstance(s, dict) and s.get("type") == "Linear Static"
        and s.get("step") == ["Single Value", 0] and s.get("initial_condition") == "NONE"
        and s.get("scale") == 1 and _real(s.get("weight_multiplier"))
        and s.get("auto_lateral") is (c in ("LC_EQX","LC_EQY")) for c, s in cases.items()),
        "TRANSITION_CASE_BASIS_INVALID")
    _check(all(isinstance(raw.get(k), str) and re.fullmatch(r"[0-9a-f]{64}",raw[k])
               for k in ("axis_and_load_export_sha256","original_edb_sha256"))
           and isinstance(raw.get("point_axes_source"), str) and raw["point_axes_source"],
           "TRANSITION_MODEL_REFERENCE_MISSING")
    _check(len(raw.get("walls", {})) == 2 and _real(raw.get("frame_weight_kn_per_m"))
           and raw["frame_weight_kn_per_m"] > 0, "TRANSITION_BODY_PROPERTIES_INVALID")
    previous = None
    seams = set()
    x0, _, z0 = raw["origin_m"]
    for uid, wall in sorted(raw["walls"].items(), key=lambda item: item[1]["x_m"][0]):
        xs, zs = wall["x_m"], wall["z_m"]
        _check(isinstance(uid, str) and _vector(xs, 2) and _vector(zs, 2) and xs[0] < xs[1]
               and (previous is None or previous == xs[0] == x0)
               and zs[0] <= z0 < raw["bracket_m"][1] < zs[1]
               and (zs[0] == z0 or zs[0] < raw["bracket_m"][0])
               and _real(wall["weight_kn_per_m2"]) and wall["weight_kn_per_m2"] > 0
               and set(wall["pressure_kn_per_m2"]) == cases.keys()
               and all(_real(v) for v in wall["pressure_kn_per_m2"].values()),
               "TRANSITION_WALL_LAYOUT_OR_LOAD_INVALID")
        previous = xs[1]
        seams.add(zs[0] == z0)
    _check(seams == {False, True}, "TRANSITION_PHYSICAL_GEOMETRY_INVALID")
    levels = raw["levels"]
    _check(len(levels) == 2 and [lv["pitch_m"] for lv in levels] == [.05, .025]
           and len({lv["model_sha256"] for lv in levels}) == 2, "TRANSITION_MESH_PAIR_INVALID")
    for lv in levels:
        check_transition_level(lv,cases)
    return raw


def check_transition_level(lv, cases):
    _check(set(lv["archives"]) == {"analysis_mesh","frame_forces","static_shell_forces","case_statuses"}
           and all(re.fullmatch(r"[0-9a-f]{64}", h) for h in [lv["model_sha256"], *lv["archives"].values()])
           and lv["generation_sha256"] == _digest([lv["model_sha256"], lv["archives"]])
           and lv["units_code"] == 6 and lv["case_statuses"] == dict.fromkeys(cases, 4),
           "TRANSITION_GENERATION_INVALID")
    _check(lv.get("slice_sha256") == _digest({k:v for k,v in lv.items() if k != "slice_sha256"}),
           "TRANSITION_SOURCE_SLICE_CHANGED")
    # R maps local frame 1,2,3 to global. The supported frame runs I→J upward.
    m = lv["frame_matrix"]
    _check(_vector(m, 9) and [m[i] for i in (0,3,6)] == [0,0,1], "TRANSITION_FRAME_AXES_INVALID")


def _six(rows):
    return tuple(fsum(col) for col in zip(*rows, strict=True)) if rows else (0.,)*6


def _public(v):
    return dict(zip(COMPONENTS, (v[i] for i in INDEX), strict=True))


def _near(a, b):
    return abs(a-b) <= EPS


def _seismic_load_scope(definition, lo, hi):
    """CSI distributes automatic static seismic forces at story elevations."""
    application = definition.get("story_application") or {}
    levels = application.get("levels_m") or {}
    if (application.get("code") != "TSC-2018" or application.get("towers") != 1
            or application.get("additional_object_loads") != 0 or len(levels) < 2
            or not all(_real(z) for z in levels.values())
            or application.get("bottom_story") not in levels or application.get("top_story") not in levels):
        return False
    bottom, top = levels[application["bottom_story"]], levels[application["top_story"]]
    return bottom < lo < hi < top and not any(lo-EPS <= z <= hi+EPS for z in levels.values())


def _rectangles(raw, level):
    """Independently inventory every required shell and shared joint by its physical grid."""
    origin, (lo, hi) = raw["origin_m"], raw["bracket_m"]
    coords, pitch = level["coordinates"], level["pitch_m"]
    _check(all(_vector(p, 3) and _near(p[1], origin[1]) for p in coords.values())
           and set(coords) == set(level["point_matrices"]), "TRANSITION_JOINT_AXES_OR_COORDINATES_MISSING")
    cells, rings, lines = {}, {}, defaultdict(list)
    edge_use = Counter()
    positions = {}
    for uid, element, ring in level["shells"]:
        _check(uid in raw["walls"] and len(ring) == len(set(ring)) == 4
               and element not in cells, "TRANSITION_SHELL_IDENTITY_INVALID")
        points = [coords[n] for n in ring]
        xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
        zmin, zmax = min(p[2] for p in points), max(p[2] for p in points)
        wall = raw["walls"][uid]
        _check(zmin >= max(lo, wall["z_m"][0])-EPS and zmax <= hi+EPS
               and _near(zmax-zmin, pitch) and xmin < xmax
               and _near(zmin-lo, round((zmin-lo)/pitch)*pitch)
               and len({(p[0], p[2]) for p in points}) == 4
               and all(p[0] in (xmin,xmax) and p[2] in (zmin,zmax) for p in points),
               "TRANSITION_RECTANGULAR_MESH_REQUIRED")
        for n, b in zip(ring, ring[1:]+ring[:1]):
            p, q = coords[n], coords[b]
            _check((p[0] == q[0]) != (p[2] == q[2])
                   and positions.setdefault(tuple(p), n) == n, "TRANSITION_DISCONNECTED_SHELL_EDGE")
            edge_use[tuple(sorted((n,b)))] += 1
        # Positive local 3 follows the native shell corner winding.
        a, b, c = points[:3]
        cy = (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])
        cells[element] = (uid, xmin, xmax, zmin, zmax, 1 if cy > 0 else -1)
        rings[element] = ring
        lines[uid, round((zmin-lo)/pitch)].append((xmin, xmax))
    for uid, wall in raw["walls"].items():
        for j in range(round((max(lo,wall["z_m"][0])-lo)/pitch), round((hi-lo)/pitch)):
            intervals = sorted(lines[uid,j])
            _check(intervals and _near(intervals[0][0], wall["x_m"][0])
                   and _near(intervals[-1][1], wall["x_m"][1])
                   and all(_near(a[1],b[0]) for a,b in zip(intervals, intervals[1:])),
                   "TRANSITION_WALL_CROSS_SECTION_INCOMPLETE")
    _check(all(n in (1,2) for n in edge_use.values()), "TRANSITION_OVERLAPPING_EDGES")
    rim = {n for edge,count in edge_use.items() if count == 1 for n in edge}
    _check(len(coords) == len(positions) and all(
        _near(coords[n][2],lo) or _near(coords[n][2],hi) or
        (_near(coords[n][0],origin[0]) and coords[n][2] <= origin[2]+EPS) or
        any(_near(coords[n][0],x) and wall["z_m"][0]-EPS <= coords[n][2] for wall in raw["walls"].values()
            for x in wall["x_m"] if not _near(x,origin[0])) or
        any(_near(coords[n][2],wall["z_m"][0]) and wall["x_m"][0]-EPS <= coords[n][0] <= wall["x_m"][1]+EPS
            for wall in raw["walls"].values()) for n in rim), "TRANSITION_UNMATCHED_MESH_EDGE")
    return cells, rings, rim


def _mesh_actions(raw, level, wall_normals):
    origin = raw["origin_m"]
    lo, hi = raw["bracket_m"]
    cases, coords = raw["cases"], level["coordinates"]
    cells, rings, rim = _rectangles(raw, level)
    cut_rows = defaultdict(list)
    rim_rows, interior_rows, loads = defaultdict(list), defaultdict(list), defaultdict(list)
    mid = origin[2]

    def assign(case, uid, n, zmin, zmax, action):
        z = coords[n][2]
        if _near(z, lo):
            cut_rows[case, "lower", uid].append(tuple(-v for v in action))
        elif _near(z, hi):
            cut_rows[case, "upper", uid].append(action)
        elif n in rim:
            rim_rows[case, n].append(action)
        else:
            interior_rows[case, n].append(action)
        if _near(z, mid):
            if _near(zmax, mid):
                cut_rows[case, "below_transition", uid].append(action)
            elif _near(zmin, mid):
                cut_rows[case, "above_transition", uid].append(tuple(-v for v in action))

    seen = set()
    for uid, element, n, case, step, num, *values in level["shell_rows"]:
        owner, _, _, a, b, _ = cells[element]
        key = (element, n, case)
        _check(owner == uid and n in rings[element] and case in cases and _real(num)
               and [step,num] == cases[case]["step"] and key not in seen, "TRANSITION_SHELL_ROW_MISMATCH")
        seen.add(key)
        assign(case, uid, n, a, b, joint_action_at_origin(values, level["point_matrices"][n], coords[n], origin))
    _check(len(seen) == 4*len(cells)*len(cases), "TRANSITION_SHELL_FORCE_MISSING")

    segments = {e:(i,j) for e,i,j in level["frame_segments"]}
    ordered = sorted(segments.values(), key=lambda ij: coords[ij[0]][2])
    _check(len(segments) == len(level["frame_segments"]) == round((hi-lo)/level["pitch_m"])
           and all(_near(coords[i][0],origin[0]) and _near(coords[j][0],origin[0])
                   and _near(coords[j][2]-coords[i][2],level["pitch_m"]) for i,j in ordered)
           and _near(coords[ordered[0][0]][2],lo) and _near(coords[ordered[-1][1]][2],hi)
           and all(a[1]==b[0] for a,b in zip(ordered,ordered[1:])), "TRANSITION_FRAME_CONNECTIVITY_INVALID")
    seen = set()
    for uid, element, end, case, step, num, *components in level["frame_rows"]:
        key = (element,end,case)
        _check(uid == raw["member_id"] and case in cases and _real(num) and [step,num] == cases[case]["step"]
               and end in ("I","J") and key not in seen and _vector(components,6), "TRANSITION_FRAME_ROW_MISMATCH")
        seen.add(key)
        i, j = segments[element]
        n = i if end == "I" else j
        p,v2,v3,t,m2,m3 = components
        vector = joint_action_at_origin((p,v2,v3,t,-m2,m3), level["frame_matrix"], coords[n], origin)
        assign(case, uid, n, coords[i][2], coords[j][2], tuple(-v for v in vector) if end=="I" else vector)
    _check(len(seen) == 2*len(segments)*len(cases), "TRANSITION_FRAME_FORCE_MISSING")

    for case, definition in cases.items():
        for uid, x1, x2, z1, z2, normal in cells.values():
            wall = raw["walls"][uid]
            _check(normal == wall_normals[uid], "TRANSITION_MESH_AND_OBJECT_NORMAL_DISAGREE")
            area = (x2-x1)*(z2-z1)
            pressure = normal*wall["pressure_kn_per_m2"][case]*area
            weight = -wall["weight_kn_per_m2"]*definition["weight_multiplier"]*area
            loads[case].append(joint_action_at_origin([0,pressure,weight,0,0,0], IDENTITY,
                                    [(x1+x2)/2,origin[1],(z1+z2)/2], origin))
        gravity = -raw["frame_weight_kn_per_m"]*(hi-lo)*definition["weight_multiplier"]
        loads[case].append(joint_action_at_origin([0,0,gravity,0,0,0], IDENTITY,
                                                  [*origin[:2],(hi+lo)/2], origin))

    output = {}
    for case in cases:
        cuts, roster, counts = {}, {}, {}
        for name in ("lower","upper","below_transition","above_transition"):
            # The wall starting at the transition contributes only above it.
            members = [raw["member_id"], *(u for u,w in raw["walls"].items()
                       if w["z_m"][0] < mid or name in ("upper","above_transition"))]
            groups = {u:cut_rows[case,name,u] for u in members}
            _check(all(groups.values()), "TRANSITION_CUT_CONTRIBUTOR_MISSING")
            roster[name] = {u:_public(_six(v)) for u,v in groups.items()}
            counts[name] = {u:len(v) for u,v in groups.items()}
            cuts[name] = _six([v for group in groups.values() for v in group])
        side = _six([_six(v) for (c,n), v in rim_rows.items() if c == case])
        external = _six(loads[case])
        terms = [tuple(-v for v in cuts["lower"]),cuts["upper"],side,external]
        residual = _six(terms)
        interior = [_six(v) for (c,n),v in interior_rows.items() if c == case]
        peak = [max((abs(v[i]) for v in interior), default=0.) for i in range(6)]
        limits = [max(BALANCE_ABS, BALANCE_REL*max(abs(v[i]) for v in terms)) for i in range(6)]
        qualified = all(abs(v)<=b and p<=b for v,p,b in zip(residual,peak,limits))
        load_complete = not cases[case]["auto_lateral"] or _seismic_load_scope(cases[case], lo, hi)
        status = "BALANCED" if qualified else "EQUILIBRIUM_TOLERANCE_EXCEEDED"
        if not load_complete:
            status = "AUTO_SEISMIC_JOINT_LOAD_INVENTORY_REQUIRED"
        output[case] = {"cuts":{name:_public(v) for name,v in cuts.items()},
                        "actions_by_object":roster,"cut_contribution_counts":counts,
                        "lateral_and_soffit_transfer":_public(side),"applied_body_load":_public(external),
                        "signed_residual":_public(residual),"balance_tolerance":_public(limits),
                        "maximum_interior_joint_residual":_public(peak), "balance_status":status,
                        "load_inventory_complete":load_complete,"numeric_balance_within_tolerance":qualified}
    return {"model_sha256":level["model_sha256"], "generation_sha256":level["generation_sha256"],
            "pitch_m":level["pitch_m"],"shell_count":len(cells),"frame_count":len(segments),
            "lateral_joint_ids":sorted(n for n in rim if lo+EPS < coords[n][2] < hi-EPS), "cases":output}


def _parent_geometry(raw, source):
    """Bind the private remesh to the original physical objects and seismic story roster."""
    tables = source["vs06_b1_geometry_source"]["table_reads"]
    points = {r["UniqueName"]:r for r in tables["Point Object Connectivity"]["rows"]}
    columns = [c for c in tables["Column Object Connectivity"]["rows"] if c["UniqueName"] == raw["member_id"]]
    _check(len(columns) == 1, "TRANSITION_PARENT_COLUMN_MISSING")
    i, j = (points[columns[0][k]] for k in ("UniquePtI","UniquePtJ"))
    _check(all(_near(float(p[k]), v) for p in (i,j) for k,v in zip(("X","Y"),raw["origin_m"]))
           and float(i["Z"]) < raw["bracket_m"][0] < raw["bracket_m"][1] < float(j["Z"]),
           "TRANSITION_PARENT_COLUMN_AXIS_MISMATCH")
    walls = {r["UniqueName"]:r for r in tables["Wall Object Connectivity"]["rows"]}
    normals = {}
    for uid, plan in raw["walls"].items():
        w = walls[uid]
        corners = [points[w["UniquePt"+str(n)]] for n in range(1,5)]
        x, y, z = ([float(p[k]) for p in corners] for k in ("X","Y","Z"))
        _check(w["WallBay"] == plan["label"] and w["Story"] == columns[0]["Story"]
               and [min(x),max(x)] == plan["x_m"] and [min(z),max(z)] == plan["z_m"]
               and all(_near(v,raw["origin_m"][1]) for v in y), "TRANSITION_PARENT_WALL_COORDINATES_MISMATCH")
        normal_y = (z[1]-z[0])*(x[2]-x[0])-(x[1]-x[0])*(z[2]-z[0])
        _check(normal_y != 0, "TRANSITION_DEGENERATE_WALL")
        normals[uid] = 1 if normal_y > 0 else -1
    for case in raw["cases"].values():
        applied = case.get("story_application")
        if not applied:
            continue
        stories = tables["Story Definitions"]["rows"]
        base = applied["bottom_story"]
        _check(i["Story"] == base and len({r["Tower"] for r in stories}) == 1,
               "TRANSITION_PARENT_STORY_SCOPE_MISMATCH")
        elevations = {base:float(i["Z"])}
        current = elevations[base]
        for row in reversed(stories):
            current += float(row["Height"])
            elevations[row["Story"]] = current
        _check(elevations == applied["levels_m"] and current == elevations[applied["top_story"]],
               "TRANSITION_PARENT_STORY_SCOPE_MISMATCH")
    return normals


def project_transition(raw, physical_length, source):
    walls = (physical_length.get("wall_mesh") or {}).get("walls", ())
    _check(physical_length.get("member_id") == raw["member_id"] and
           {w["wall_id"]:(w["base_z_m"],w["top_z_m"]) for w in walls}
           == {uid:tuple(w["z_m"]) for uid,w in raw["walls"].items()}, "TRANSITION_PARENT_POPULATION_MISMATCH")
    normals = _parent_geometry(raw, source)
    coarse, fine = [_mesh_actions(raw, lv, normals) for lv in raw["levels"]]
    comparison = []
    for case in raw["cases"]:
        for face in coarse["cases"][case]["cuts"]:
            left, right = (lv["cases"][case]["cuts"][face] for lv in (coarse,fine))
            for name in COMPONENTS:
                a, b = left[name], right[name]
                limit = max(MESH_ABS, MESH_REL*max(abs(a),abs(b)))
                comparison.append({"case":case,"face":face,"component":name,"coarse":a,"fine":b,
                                   "delta":b-a,"tolerance":limit,"within_tolerance":abs(b-a)<=limit})
    design = {}
    if raw["schema"] == DESIGN_SCHEMA:
        from .transition_design_trace import project_design_trace
        design["design_trace"] = project_design_trace(raw, source, (coarse,fine))
    return {**design,"member_id":raw["member_id"],"scope":"SIGNED_LINEAR_STATIC_COUPLED_SECTION",
            "origin_global_m":raw["origin_m"],"bracketing_cuts_m":raw["bracket_m"],
            "axes":"N along +Z, V2 along +X, V3 along +Y. T, M2 and M3 use right-hand moments about those axes. Positive face upward.",
            "units":["kN","kN","kN","kN m","kN m","kN m"],
            "case_steps":{c:v["step"] for c,v in raw["cases"].items()},
            "geometry":{"walls":{u:{"label":w["label"],"x_m":w["x_m"],"z_m":w["z_m"]}
                                  for u,w in raw["walls"].items()}},
            "budget":{"mesh_absolute":MESH_ABS,"mesh_relative":MESH_REL,
                      "balance_absolute":BALANCE_ABS,"balance_relative":BALANCE_REL},
            "point_axes_source":raw["point_axes_source"], "source_data_sha256":raw["source_data_sha256"],
            "source_archive_sha256":_digest(raw),"models":[coarse,fine],"convergence":comparison,
            "evaluated_components":len(comparison),
            "converged_components":sum(x["within_tolerance"] for x in comparison),
            "second_order_status":"COUPLED_SECOND_ORDER_DEMAND_UNQUALIFIED",
            "reinforcement_status":"CONSTRUCTION_CONTINUITY_UNVERIFIED"}
