"""Coordinate the proposed straight bars entering each basement column."""
from collections import defaultdict
from itertools import chain, combinations, product
from math import ceil, floor, hypot

from .wall_bar_paths import bent_path, point_distance, segment_distance

from .basement_pier_geometry import support_id
from .basement_wall_pressure import DEFAULT_AGGREGATE_MM, clear_limit, finite_grid


def layout_policy(geometry, panel, cover, aggregate=DEFAULT_AGGREGATE_MM):
    """Use a shared elevation lattice; give the shorter collinear web the inner curtain."""
    direction = panel["width_direction"]
    joints = {panel["joint_i"], panel["joint_j"]}
    shorter = any(joints & {p["joint_i"], p["joint_j"]} and p["span_m"] > panel["span_m"]+1e-8
                  and abs(sum(a*b for a,b in zip(direction,p["width_direction"]))) > 1-1e-9
                  for p in geometry["panels"])
    pier_height = (geometry["top_m"]-geometry["bottom_m"])*1000
    height = (panel.get("top_m",geometry["top_m"])-panel.get("bottom_m",geometry["bottom_m"]))*1000
    base_offset = max(0., (panel.get("bottom_m",geometry["bottom_m"])-geometry["bottom_m"])*1000)
    # Keep all panels on one elevation lattice. Choose its densest feasible catalogue spacing.
    pitch = 40 if finite_grid(pier_height,14,40,cover)["clear_spacing_mm"] >= clear_limit(aggregate,14) else 50
    fine = finite_grid(pier_height,14,pitch,cover)
    out = {"aggregate_mm":aggregate, "height":height, "module":fine["pitch_mm"], "start":fine["first_and_last_offset_mm"],
           "phase":.5 if abs(direction[0]) > .5 else 0., "inner":shorter}
    if base_offset > 1e-7:
        out["base_offset_mm"] = base_offset
    return out


def level_grid(policy, diameter, nominal, cover, *, dowel=False, minimum_per_m=None):
    module, height = policy["module"], policy["height"]
    base = policy.get("base_offset_mm", 0.)
    edge = cover+diameter/2
    required_count = 1000//nominal if minimum_per_m is None else minimum_per_m
    for stride in range(min(4,floor(nominal/module+1e-9)),0,-1):
        spacing = stride*module
        if spacing-diameter < clear_limit(policy.get("aggregate_mm", DEFAULT_AGGREGATE_MM),diameter):
            continue
        offset = (policy.get("dowel_phase",policy["phase"]+(stride//2 if policy["inner"] else 0.))
                  if dowel else policy["phase"])
        seed = policy["start"] + offset*module - base
        first = seed + ceil((edge-seed)/spacing-1e-10)*spacing
        count = 1+floor((height-edge-first)/spacing+1e-10)
        last = height-first-(count-1)*spacing
        minimum = min(floor(1000/spacing+1e-10), 1+floor((1000-max(first,last))/spacing+1e-10), count)
        if minimum >= required_count and min(first,last) >= edge-1e-7:
            grid = {"layers":count,"pitch_mm":spacing,"first_station_mm":first,"last_cover_to_center_mm":last,
                    "clear_spacing_mm":spacing-diameter,"minimum_in_any_full_metre":minimum,
                    "guaranteed_bars_per_m":required_count}
            if base > 1e-7:
                grid["base_offset_mm"] = base
            return grid
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
            corner = end if role=="web" else dowels.get("anchor",{})
            shape = corner.get("return_shape")
            levels = grid.get("opposite_face_levels",grid) if face==1 else grid
            base = levels.get("base_offset_mm", grid.get("base_offset_mm", 0.))
            heights = [base+levels["first_station_mm"]+i*levels["pitch_mm"] for i in range(levels["layers"])]
            hook = end.get("hook") if role=="web" else dowels.get("hook")
            path = next((p for p in corner.get("bar_paths",()) if p["face"]==face),None)
            if hook and hook.get("local_paths"):
                local = next(p for p in hook["local_paths"] if p["face"]==face)
                path = {**local,"points_mm":[(u*dx-v*dy,u*dy+v*dx) for u,v in local["points_mm"]]}
            elif hook:
                turn = hook["lateral_turn"]*face
                path = bent_path(face,(x,y),(ex,ey),(-turn*dy,turn*dx),hook["straight_to_tangent_mm"],
                                 hook["centreline_radius_mm"],hook["straight_tail_mm"])
            if path:
                pts = list(path["points_mm"])
                errors = list(path["chord_error_mm"])
                if end.get("joint"):
                    arm = panel["clear_length_m"]*1000 if role=="web" else grid["wall_embedment_mm"]
                    pts.insert(0,[pts[0][0]-ex*arm,pts[0][1]-ey*arm])
                    errors.insert(0,0.)
                xs,ys = zip(*pts)
                err = max(errors)
                yield {"member":panel["member"],"role":role,"face":face,"horizontal":abs(ex)>.5,
                       "bounds":(min(xs)-err,max(xs)+err,min(ys)-err,max(ys)+err),"diameter":grid["diameter_mm"],
                       "heights":heights,"segments":list(zip(pts,pts[1:],errors))}
                continue
            if shape == "RETURN_U_HAIRPIN" and face==1:
                # One closure connects both straight legs. The envelope of the bend
                # includes its complete arc and both faces in the receiving web.
                sx, sy = -2*dy*offset, 2*dx*offset
                start = length-offset-grid["diameter_mm"]/2
                xs=[x+start*ex,x2,x2-sx,x+start*ex-sx]
                ys=[y+start*ey,y2,y2-sy,y+start*ey-sy]
                yield {"member":panel["member"],"role":role+" bend","face":0,"horizontal":abs(ex)>.5,
                       "bounds":(min(xs),max(xs),min(ys),max(ys)), "diameter":grid["diameter_mm"], "heights":heights}
            hook = end.get("hook") if role == "web" else None
            if hook:
                # The bounding rectangle contains the complete arc and tail. A passing
                # distance is a conservative lower bound for the curved bar.
                shift = hook["centreline_radius_mm"] + hook["straight_tail_mm"]
                x3, y3 = x2 - hook["lateral_turn"]*face*dy*shift, y2 + hook["lateral_turn"]*face*dx*shift
            elif shape=="RETURN_PAIRED_90":
                shift = corner["centreline_radius_mm"]+corner["hook_90_tail_mm"]
                x3,y3 = x2+face*dy*shift,y2-face*dx*shift
            else:
                x3, y3 = x2, y2
            yield {"member":panel["member"], "role":role, "face":face, "horizontal":abs(ex)>.5,
                   "bounds":(min(x,x2,x3),max(x,x2,x3),min(y,y2,y3),max(y,y2,y3)), "diameter":grid["diameter_mm"],
                   "heights":heights}


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


def _segments(f):
    if "segments" in f:
        return f["segments"]
    x0,x1,y0,y1=f["bounds"]
    return [((x0,y0),(x1,y1),0.)]


def _separation(a,b, aggregate=DEFAULT_AGGREGATE_MM):
    a0,a1,a2,a3 = a["bounds"]; b0,b1,b2,b3 = b["bounds"]
    dx = max(0.,a0-b1,b0-a1)
    dy = max(0.,a2-b3,b2-a3)
    dz, za, zb = _closest_levels(a["heights"],b["heights"])
    clear = hypot(dx,dy,dz)-(a["diameter"]+b["diameter"])/2
    parallel = a["horizontal"]==b["horizontal"]
    limit = clear_limit(aggregate,a["diameter"],b["diameter"]) if parallel else 0.
    if "segments" in a or "segments" in b:
        minimum = clear_limit(aggregate,a["diameter"],b["diameter"])
        if clear <= minimum:
            worst = None
            for p,q,ea in _segments(a):
                for u,v,eb in _segments(b):
                    px,py=q[0]-p[0],q[1]-p[1]
                    ux,uy=v[0]-u[0],v[1]-u[1]
                    # Each chord spans 11.25 degrees. Allow both tangent uncertainties when testing parallel bars.
                    aligned = abs(px*ux+py*uy) >= .98078528040*hypot(px,py)*hypot(ux,uy)
                    req = minimum if aligned else 0.
                    dist = max(0.,segment_distance(p,q,u,v)-ea-eb)
                    space = hypot(dist,dz)-(a["diameter"]+b["diameter"])/2
                    entry = (space-req,space,req,aligned)
                    if worst is None or entry<worst:
                        worst=entry
            _,clear,limit,parallel=worst
    return {"members":[a["member"],b["member"]],"roles":[a["role"],b["role"]],"faces":[a["face"],b["face"]],
            "levels_above_base_mm":[za,zb],"parallel":parallel,"clear_mm":clear,"required_mm":limit,
            "margin_mm":clear-limit, "fits": clear >= limit-1e-8 if parallel else clear > 0.}


def main_bar_collision(first, second, aggregate):
    webs = [[f for f in _families(panel,side,end) if f["role"]=="web"] for panel,side,end in (first,second)]
    return any(not _separation(a,b,aggregate)["fits"] for a in webs[0] for b in webs[1])


def _through_families(families, proof, role="web"):
    """Replace two specified collinear continuations by the two actual through-bars per level."""
    straight = [f for f in families if f["role"]==role]
    rest = [f for f in families if f["role"]!=role]
    tracks = defaultdict(list)
    for f in straight:
        lo,hi = (2,3) if f["horizontal"] else (0,1)
        coords = f["bounds"]
        if abs(coords[lo]-coords[hi])>1e-6:
            return families
        tracks[(f["horizontal"],round(coords[lo],6),f["diameter"])].append(f)
    if len(tracks)!=2 or any(len(bars)!=2 for bars in tracks.values()):
        return families
    for a,b in tracks.values():
        if sorted((a["member"],b["member"]))!=sorted(proof["members"]) or len(a["heights"])!=len(b["heights"]) or any(
                abs(h-k)>1e-6 for h,k in zip(a["heights"],b["heights"])):
            return families
        aa,bb=a["bounds"],b["bounds"]
        rest.append({**a,"member":" + ".join(proof["members"]),"role":"continuous "+role,
                     "bounds":(min(aa[0],bb[0]),max(aa[1],bb[1]),min(aa[2],bb[2]),max(aa[3],bb[3]))})
    return rest


def stagger_column_entries(geometry, designs, through, cover, aggregate):
    """Translate actual bar elevations. Keep both face arms, diameters, pitch and guaranteed steel."""
    panels = {p["member"]:p for p in geometry["panels"]}
    joints = defaultdict(list)
    for uid,p in panels.items():
        for side in ("I","J"):
            joints[support_id(p,side)].append((uid,side))

    def layout_at(key, current):
        copies = []
        for uid,_ in joints[key]:
            detail = current.get(uid) or {}
            ends = {s:dict(e) for s,e in detail.get("ends",{}).items()}
            copies.append({**panels[uid],"horizontal":detail.get("horizontal"),"vertical":detail.get("vertical"),
                           "pressure_connections":{"ends":ends}})
        return check_joint_layout({"panels":copies},aggregate,through,target=key)[0]["status"]

    def options(uid):
        detail = designs[uid]
        yield detail
        p = panels[uid]
        if detail["horizontal"].get("opposite_face_levels") or any(support_id(p,s) in through for s in ("I","J")):
            return
        policy = layout_policy(geometry,p,cover,aggregate)
        phase = policy["phase"]+int(policy["inner"])
        horizontal = detail["horizontal"]
        # Independent wall and dowel grids may be staggered on the same construction module.
        shifts = (0., .5, 1., 1.5, 2., 2.5, 3., 3.5)
        seen = set()
        for h_step, d_step in product(shifts, repeat=2):
            h = level_grid({**policy,"phase":phase+h_step},horizontal["diameter_mm"],horizontal["maximum_pitch_mm"],cover)
            if not h or h["pitch_mm"]!=horizontal["pitch_mm"] or h["minimum_in_any_full_metre"]<horizontal["guaranteed_bars_per_m"]:
                continue
            ends = {}
            for side,e in detail["ends"].items():
                bars = e["transfer"]
                if e["status"]!="CONDITIONAL_PRESSURE_END_DESIGN":
                    ends[side]=e
                    continue
                nominal = bars.get("maximum_pitch_mm")
                if not nominal:
                    break
                g = level_grid({**policy,"dowel_phase":phase+d_step},bars["diameter_mm"],nominal,
                               max(cover,e["end_cover_mm"]),dowel=True)
                if not g or g["pitch_mm"]!=bars["pitch_mm"] or g["minimum_in_any_full_metre"]<bars["guaranteed_bars_per_m"]:
                    break
                ends[side]={**e,"transfer":{**bars,**g}}
            if set(ends)!=set(detail["ends"]):
                continue
            identity = (h["first_station_mm"], *(e["transfer"].get("first_station_mm") for e in ends.values()))
            if identity in seen:
                continue
            seen.add(identity)
            v = detail["vertical"]
            yield {**detail,"horizontal":{**horizontal,**h,"guaranteed_bars_per_m":horizontal["guaranteed_bars_per_m"]},
                   "vertical":{**v,"crossties":v["stations_per_face"]*h["layers"]},"ends":ends}

    ok = "PROPOSED_PRESSURE_BARS_FIT"
    for key, incident in joints.items():
        if len(incident) == 1 and key not in through:
            uid, side = incident[0]
            detail = designs.get(uid) or {}
            end = detail.get("ends", {}).get(side, {})
            bars = end.get("transfer", {})
            if (end.get("hook") and bars.get("basis") == "SAME_CORNER_NATIVE_EDGE"
                    and layout_at(key, designs) == "PROPOSED_PRESSURE_BARS_CLASH"):
                policy = layout_policy(geometry, panels[uid], cover, aggregate)
                cap = bars["concrete_limit_kn_m"]
                for shift in (.5, .25, .75):
                    grid = level_grid({**policy, "dowel_phase": policy["phase"] + shift},
                                      bars["diameter_mm"], bars["maximum_pitch_mm"], max(cover, end["end_cover_mm"]),
                                      dowel=True, minimum_per_m=1)
                    if not grid or abs(grid["pitch_mm"] - bars["pitch_mm"]) > 1e-8:
                        continue
                    count = grid["minimum_in_any_full_metre"]
                    factor = count / bars["guaranteed_bars_per_m"]
                    steel = factor * bars["steel_resistance_kn_m"]
                    ratio = bars["peak_reaction_kn_m"] / steel
                    peak_shear = max(r["max_native_shear_kn_m"] for r in bars["combinations"])
                    if ratio > bars["steel_selection_limit"] or peak_shear > cap:
                        continue
                    cuts = [{**r, "upper_ratio": max(r["reaction_kn_m"] / steel, r["max_native_shear_kn_m"] / cap)}
                            for r in bars["combinations"]]
                    shifted = {**bars, **grid, "guaranteed_bars_per_m": count, "as_mm2_m": factor * bars["as_mm2_m"],
                               "steel_resistance_kn_m": steel, "resistance_kn_m": min(steel, cap), "steel_ratio": ratio,
                               "peak_ratio": max(r["upper_ratio"] for r in cuts), "combinations": cuts,
                               "force_margin_kn_m": min(steel - bars["peak_reaction_kn_m"], cap - peak_shear)}
                    trial = {**detail, "ends": {**detail["ends"], side: {**end, "transfer": shifted}}}
                    if layout_at(key, {**designs, uid: trial}) == ok:
                        designs[uid] = trial
                        break
        if key in through or len(incident)<2 or layout_at(key,designs)!="PROPOSED_PRESSURE_BARS_CLASH":
            continue
        uids = [uid for uid,_ in incident]
        neighbours = {support_id(panels[uid],s) for uid in uids for s in ("I","J")}-{key}
        protected = [k for k in neighbours if layout_at(k,designs)==ok]
        # Try changing one entry first. Only explore pairs if neither single move resolves the clash.
        choices = {u:list(options(u)) for u in uids}
        singles = (((u,), (v,)) for u in uids for v in choices[u][1:])
        pairs = ((pair, vals) for pair in combinations(uids,2) for vals in product(*(choices[u][1:] for u in pair)))
        for ids, vals in chain(singles,pairs):
            trial = dict(designs)
            trial.update(zip(ids, vals))
            if layout_at(key,trial)==ok and all(layout_at(k,trial)==ok for k in protected):
                designs.update(zip(ids,vals))
                break


def check_joint_layout(geometry, aggregate=DEFAULT_AGGREGATE_MM, through=None, *, target=None):
    by_column = defaultdict(list)
    for panel in geometry["panels"]:
        for side in ("I","J"):
            end = panel.get("pressure_connections",{}).get("ends",{}).get(side)
            by_column[support_id(panel,side)].append((panel,side,end))
    result = []
    for uid,incident in sorted(by_column.items()):
        if target is not None and uid != target:
            continue
        row = {"column":uid, "members":[p["member"] for p,_,_ in incident], "status":"HOLD"}
        result.append(row)
        if not all(end and end["status"] in ("CONDITIONAL_PRESSURE_END_DESIGN", "HOLD_INCIDENT_PRESSURE_END_DETAILS_REQUIRED")
                   for _,_,end in incident):
            row["reason"] = "ALL_INCIDENT_PRESSURE_END_DETAILS_REQUIRED"
            for _, _, end in incident:
                if end:
                    end["layout_status"] = row["reason"]
                    if end["status"] == "CONDITIONAL_PRESSURE_END_DESIGN":
                        end["status"] = "HOLD_INCIDENT_PRESSURE_END_DETAILS_REQUIRED"
            continue
        corners = [(p,s,e) for p,s,e in incident if e.get("joint")]
        actual = {p["member"] for p,_,_ in incident}
        if any(set(e["incident_walls"])-actual for _,_,e in corners):
            bridge=geometry.get("bridge_checks",{}).get(uid)
            if bridge:
                row["transfer_connection"]=bridge
            if not bridge or bridge["status"]!="TRANSFER_CAGE_LAYOUT_VERIFIED":
                row["reason"] = (bridge or {}).get("reason","RECEIVING_WALL_CURTAIN_LAYOUT_UNBOUND")
                for _,_,end in incident:
                    end["layout_status"] = row["reason"]
                continue
            trial = bridge.get("coordinated_trial") or {}
            if trial.get("status") == "COMPLETE_LAYOUT":
                row.update(status="PROPOSED_PRESSURE_BARS_FIT", governing=trial["mutual_clearance"], coordinated_layout=True)
                for _,_,end in incident:
                    end["layout_status"] = "PROPOSED_PRESSURE_BARS_FIT"
                continue
        families = [bar for panel,side,end in incident for bar in _families(panel,side,end)]
        proof = (through or {}).get(uid)
        if proof:
            merged = _through_families(families,proof)
            if len(merged)==len(families)-2:
                families = merged
                if proof.get("through_dowels"):
                    dowels = _through_families(families,proof,"dowel")
                    if len(dowels)==len(families)-2:
                        families=dowels
                        row["continuous_dowels"]=proof["through_dowels"]
                row["continuous_web"] = proof
                for _,_,end in incident:
                    end["bar_path"] = "UNSPLICED_THROUGH_COLUMN"
                    end["through_bar_length_mm"] = proof["one_piece_length_mm"]
        checks = [_separation(a,b,aggregate) for a,b in combinations(families,2)
                  if not (a["member"]==b["member"] and a["role"] != b["role"] and
                          a["role"].removesuffix(" bend")==b["role"].removesuffix(" bend"))]
        for panel,side,end in corners:
            v = panel.get("vertical") or {}
            if not v.get("stations_per_face"):
                row["reason"] = "RECEIVING_WALL_VERTICAL_GRID_REQUIRED"
                break
            dx,dy = panel["width_direction"]
            sense = 1 if side=="I" else -1
            h = panel["horizontal"]
            track = panel["thickness_m"]*500-h["cover_mm"]-h["curtain_inset_mm"]-2*h["diameter_mm"]-v["diameter_mm"]/2
            for i in range(v["stations_per_face"]):
                along = sense*(end["column_depth_mm"]/2+(i+.5)*v["pitch_mm"])
                for f in (-1,1):
                    x,y = along*dx-f*track*dy,along*dy+f*track*dx
                    for bar in families:
                        if bar["member"]==panel["member"] and bar["role"]=="web":
                            continue  # Intended contact of the two perpendicular curtain grids.
                        x0,x1,y0,y1 = bar["bounds"]
                        space = hypot(max(0,x0-x,x-x1),max(0,y0-y,y-y1))-(v["diameter_mm"]+bar["diameter"])/2
                        minimum = clear_limit(aggregate,v["diameter_mm"],bar["diameter"])
                        if "segments" in bar and space<=minimum:
                            space=min(point_distance((x,y),p,q)-err for p,q,err in _segments(bar))-(v["diameter_mm"]+bar["diameter"])/2
                        checks.append({"members":[panel["member"],bar["member"]],"roles":["vertical",bar["role"]],
                            "parallel":False,"clear_mm":space,"required_mm":minimum,"margin_mm":space-minimum,
                            "fits":space>=minimum})
        from .wall_return_layout import vertical_margin
        for panel,side,end in corners:
            if not panel.get("vertical"):
                continue
            for family in families:
                margin=vertical_margin(family,panel,side,end,aggregate)
                if margin!=float("inf"):
                    checks.append({"members":[panel["member"],family["member"]],"roles":["verticals and crossties",family["role"]],
                                   "parallel":False,"clear_mm":margin,"required_mm":0.,"margin_mm":margin,"fits":margin>=-1e-8})
        if row.get("reason"):
            continue
        row.update(family_pairs=len(checks), minimum_parallel_clear_mm=min(q["clear_mm"] for q in checks if q["parallel"]),
                   governing=min(checks,key=lambda q:q["margin_mm"]),
                   status="PROPOSED_PRESSURE_BARS_FIT" if all(q["fits"] for q in checks) else "PROPOSED_PRESSURE_BARS_CLASH")
        for _,_,end in incident:
            end["layout_status"] = row["status"]
            if row["status"] == "PROPOSED_PRESSURE_BARS_CLASH":
                end["status"] = row["status"]
    return result
