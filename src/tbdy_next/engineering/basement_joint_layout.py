"""Coordinate the proposed straight bars entering each basement column."""
from collections import defaultdict
from itertools import combinations
from math import ceil, floor, hypot

from .basement_wall_pressure import DEFAULT_AGGREGATE_MM, clear_limit, finite_grid


def layout_policy(geometry, panel, cover, aggregate=DEFAULT_AGGREGATE_MM):
    """Use a shared elevation lattice; give the shorter collinear web the inner curtain."""
    direction = panel["width_direction"]
    joints = {panel["joint_i"], panel["joint_j"]}
    shorter = any(joints & {p["joint_i"], p["joint_j"]} and p["span_m"] > panel["span_m"]+1e-8
                  and abs(sum(a*b for a,b in zip(direction,p["width_direction"]))) > 1-1e-9
                  for p in geometry["panels"])
    height = (geometry["top_m"]-geometry["bottom_m"])*1000
    # Keep all panels on one elevation lattice. Choose its densest feasible catalogue spacing.
    pitch = 40 if finite_grid(height,14,40,cover)["clear_spacing_mm"] >= clear_limit(aggregate,14) else 50
    fine = finite_grid(height,14,pitch,cover)
    return {"aggregate_mm":aggregate, "height":height, "module":fine["pitch_mm"], "start":fine["first_and_last_offset_mm"],
            "phase":.5 if abs(direction[0]) > .5 else 0., "inner":shorter}


def level_grid(policy, diameter, nominal, cover, *, dowel=False):
    module, height = policy["module"], policy["height"]
    edge = cover+diameter/2
    required_count = 1000//nominal
    for stride in range(min(4,floor(nominal/module+1e-9)),0,-1):
        spacing = stride*module
        if spacing-diameter < clear_limit(policy.get("aggregate_mm", DEFAULT_AGGREGATE_MM),diameter):
            continue
        offset = policy["phase"] + (stride//2 if dowel and policy["inner"] else 0.)
        seed = policy["start"] + offset*module
        first = seed + ceil((edge-seed)/spacing-1e-10)*spacing
        count = 1+floor((height-edge-first)/spacing+1e-10)
        last = height-first-(count-1)*spacing
        minimum = min(floor(1000/spacing+1e-10), 1+floor((1000-max(first,last))/spacing+1e-10), count)
        if minimum >= required_count and min(first,last) >= edge-1e-7:
            return {"layers":count,"pitch_mm":spacing,"first_station_mm":first,"last_cover_to_center_mm":last,
                    "clear_spacing_mm":spacing-diameter,"minimum_in_any_full_metre":minimum,
                    "guaranteed_bars_per_m":required_count}
    return {}


def _families(panel, side, end):
    main = panel["horizontal"]
    dowels = end["transfer"]
    dx, dy = panel["width_direction"]
    sign = -1 if side=="I" else 1
    ex, ey = sign*dx, sign*dy
    depth = end["column_depth_mm"]
    main_offset = 500*panel["thickness_m"]-main["cover_mm"]-main["curtain_inset_mm"]-1.5*main["diameter_mm"]
    for role, grid, offset, length in (("web",main,main_offset,end["specified_embedment_mm"]),
            ("dowel",dowels,dowels["offset_each_side_mm"],dowels["column_embedment_mm"])):
        for face in (-1,1):
            x, y = -ex*depth/2-face*dy*offset, -ey*depth/2+face*dx*offset
            x2, y2 = x+length*ex, y+length*ey
            yield {"member":panel["member"], "role":role, "face":face, "horizontal":abs(ex)>.5,
                   "bounds":(min(x,x2),max(x,x2),min(y,y2),max(y,y2)), "diameter":grid["diameter_mm"],
                   "heights":[grid["first_station_mm"]+i*grid["pitch_mm"] for i in range(grid["layers"])]}


def _closest_levels(left, right):
    i = j = 0
    best = (float("inf"),0.,0.)
    while i<len(left) and j<len(right):
        x, y = left[i], right[j]
        best = min(best,(abs(x-y),x,y))
        if x<y:
            i += 1
        else:
            j += 1
    return best


def _separation(a,b, aggregate=DEFAULT_AGGREGATE_MM):
    a0,a1,a2,a3 = a["bounds"]; b0,b1,b2,b3 = b["bounds"]
    dx = max(0.,a0-b1,b0-a1)
    dy = max(0.,a2-b3,b2-a3)
    dz, za, zb = _closest_levels(a["heights"],b["heights"])
    clear = hypot(dx,dy,dz)-(a["diameter"]+b["diameter"])/2
    parallel = a["horizontal"]==b["horizontal"]
    limit = clear_limit(aggregate,a["diameter"],b["diameter"]) if parallel else 0.
    return {"members":[a["member"],b["member"]],"roles":[a["role"],b["role"]],"faces":[a["face"],b["face"]],
            "levels_above_base_mm":[za,zb],"parallel":parallel,"clear_mm":clear,"required_mm":limit,
            "margin_mm":clear-limit, "fits": clear >= limit-1e-8 if parallel else clear > 0.}


def check_joint_layout(geometry, aggregate=DEFAULT_AGGREGATE_MM):
    by_column = defaultdict(list)
    for panel in geometry["panels"]:
        for side in ("I","J"):
            end = panel.get("pressure_connections",{}).get("ends",{}).get(side)
            by_column[panel["column_"+side.lower()]].append((panel,side,end))
    result = []
    for uid,incident in sorted(by_column.items()):
        row = {"column":uid, "members":[p["member"] for p,_,_ in incident], "status":"HOLD"}
        result.append(row)
        if not all(end and end["status"]=="CONDITIONAL_PRESSURE_END_DESIGN" for _,_,end in incident):
            row["reason"] = "ALL_INCIDENT_PRESSURE_END_DETAILS_REQUIRED"
            for _, _, end in incident:
                if end:
                    end["layout_status"] = row["reason"]
                    if end["status"] == "CONDITIONAL_PRESSURE_END_DESIGN":
                        end["status"] = "HOLD_INCIDENT_PRESSURE_END_DETAILS_REQUIRED"
            continue
        families = [bar for panel,side,end in incident for bar in _families(panel,side,end)]
        checks = [_separation(a,b,aggregate) for a,b in combinations(families,2)]
        row.update(family_pairs=len(checks), minimum_parallel_clear_mm=min(q["clear_mm"] for q in checks if q["parallel"]),
                   governing=min(checks,key=lambda q:q["margin_mm"]),
                   status="PROPOSED_PRESSURE_BARS_FIT" if all(q["fits"] for q in checks) else "PROPOSED_PRESSURE_BARS_CLASH")
        for _,_,end in incident:
            end["layout_status"] = row["status"]
            if row["status"] == "PROPOSED_PRESSURE_BARS_CLASH":
                end["status"] = row["status"]
    return result
