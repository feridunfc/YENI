"""Check a hoop-synchronous, straight two-curtain bridge with the native W6 cage."""
from math import ceil, floor, hypot, pi, sqrt

from .basement_joint_layout import _closest_levels, _families, _segments, _separation, level_grid
from .basement_wall_connection import tension_development, wall_return_anchor
from .basement_wall_pressure import clear_limit
from .wall_bar_paths import point_distance, segment_distance
from .wall_membrane_design import SELECTION_LIMIT, check_curtains


def corridors(centres, low, high, diameter, aggregate):
    """Intervals available to a rod crossing a row of vertical bars, including cover."""
    intervals = [(low,high)] if low <= high else []
    for station, bar in sorted(centres):
        exclusion = (diameter+bar)/2 + clear_limit(aggregate,diameter,bar)
        new = []
        for a,b in intervals:
            if station+exclusion <= a or station-exclusion >= b:
                new.append((a,b))
            else:
                if a <= station-exclusion:
                    new.append((a,station-exclusion))
                if station+exclusion <= b:
                    new.append((station+exclusion,b))
        intervals = new
    return intervals


def link_clearances(families, straight_id, length, vertical_pitch, horizontal_track,
                    vertical_track, diameter, direction, normal, hoop_levels, tie_diameter, aggregate):
    """Conservative clearances to physical closed hoops, link verticals and crossties."""
    hoop_checks=[]
    minimum_vertical=None
    minimum_tie=None
    count=round(length/vertical_pitch)
    web_levels=next((f["heights"] for f in families if f["role"]=="web" and f["member"]==straight_id),[])
    if not web_levels:
        return {"complete":False}
    for family in families:
        bar=family["diameter"]
        dz=_closest_levels(family["heights"],hoop_levels)[0]
        clear=dz-(bar+tie_diameter)/2
        hoop_checks.append({"member":family["member"],"role":family["role"],"face":family["face"],
                            "clear_lower_mm":clear,"required_mm":clear_limit(aggregate,bar,tie_diameter)})
        if family["role"]=="web" and family["member"]==straight_id:
            continue  # Deliberate intersections attaching the link verticals to the continuous web.
        for i in range(count):
            along=-length+(i+.5)*vertical_pitch
            def at(offset):
                return tuple(along*direction[j]+offset*normal[j] for j in (0,1))
            for sign in (-1,1):
                point=at(sign*vertical_track)
                space=min(point_distance(point,a,b)-err for a,b,err in _segments(family))-(bar+diameter)/2
                item={"member":family["member"],"role":family["role"],"face":family["face"],"station_mm":along,
                      "clear_mm":space,"margin_mm":space-clear_limit(aggregate,bar,diameter)}
                if minimum_vertical is None or item["margin_mm"]<minimum_vertical["margin_mm"]:
                    minimum_vertical=item
            ends=(at(-horizontal_track),at(horizontal_track))
            # Reserve the complete crosstie hook sweep within one rod diameter of the line.
            plan=max(0.,min(segment_distance(a,b,*ends)-err for a,b,err in _segments(family))-diameter)
            dz=_closest_levels(family["heights"],web_levels)[0]
            margin=hypot(plan,dz)-(bar+diameter)/2
            if minimum_tie is None or margin<minimum_tie["surface_separation_mm"]:
                minimum_tie={"member":family["member"],"role":family["role"],"face":family["face"],
                             "station_mm":along,"surface_separation_mm":margin}
    return {"complete":len(families)==8,"boundary_hoop_checks":hoop_checks,
            "link_vertical_governing":minimum_vertical,"link_crosstie_governing":minimum_tie}


def cut_section_checks(panel, link_id, cuts, states, mat, diameter, nominal_pitch, offset, aggregate, *, offsets=None):
    """Check the actual vertical steel against assigned pier cuts or native shell-field bounds."""
    from ..column_engine.section_capacity import Bar, Section
    from ..column_engine.section_interval import SectionInterval
    length=panel.get("clear_length_m",panel["span_m"])
    thickness=panel["thickness_m"]*1000
    count=max(2,ceil(1000*length/nominal_pitch-1e-10))
    spacing=1000*length/count
    if min(2*offset-diameter,spacing-diameter)<clear_limit(aggregate,diameter):
        return {"satisfied":False,"reason":"VERTICAL_REINFORCEMENT_CLEARANCE","offset_mm":offset}
    area=pi*diameter**2/4
    offsets=[offset]*count if offsets is None else offsets
    if (len(offsets)!=count or list(offsets)!=list(reversed(offsets)) or min(offsets)!=offset
            or max(offsets)+diameter/2>thickness/2):
        raise ValueError("WALL_SECTION_REQUIRES_REAL_MIRRORED_VERTICALS")
    bars=tuple(Bar((2*i-count+1)*spacing/2,sign*x,area) for i,x in enumerate(offsets) for sign in (-1,1))
    owner=SectionInterval(Section(1000*length,thickness,bars,mat))
    demands=[]
    if panel["member"]==link_id:
        # A source-bound section envelope over the complete native corner population.
        # The constant part of the axial line load has zero first moment. The
        # remaining range times integral(abs(x)) bounds strong-axis bending.
        for name,field in states.items():
            low=min(membrane[1][0] for _,_,membrane,_ in field)
            high=max(membrane[1][1] for _,_,membrane,_ in field)
            weak=length*max(abs(m) for _,_,_,plate in field for m in plate[1])
            demands.append((name,"NATIVE_SHELL_FIELD",[-high*length,-low*length],weak,(high-low)*length**2/8))
    else:
        for row in cuts:
            for d in row.get("web_demands",()):
                if d["member"]==panel["member"]:
                    demands.append((row["combination"],row["face"],d["nd_kn"],d["m2_upper_knm"],d["m3_upper_knm"]))
    rows=[]
    for name,face,axial,weak,strong in demands:
        r=owner.assess(axial,weak,strong)
        rows.append({"combination":name,"face":face,"nd_kn":axial,"m2_upper_knm":weak,"m3_upper_knm":strong,
                     "status":r["status"],"upper_utilization":r.get("upper_utilization")})
    expected=len(states) if panel["member"]==link_id else len(cuts)
    return {"satisfied":bool(expected) and len(rows)==expected and all(r["status"]=="PMM_BOX_SATISFIED" for r in rows),
            "stations_per_face":count,"vertical_offset_mm":offset,"checks":rows}


def synchronous_trial(straight,turn,link,straight_side,turn_side,section,pier,fields,material,aggregate,cover,height,cuts=()):
    from .wall_bridge_layout import _translated, series_interface_checks
    cage = pier["transverse_cage"]
    thick = link["thickness_m"]*1000
    length = link["span_m"]*1000
    count = ceil(height/cage["spacing_mm"])
    pitch = height/count
    hoops = [(i+.5)*pitch for i in range(count)]
    tie = cage["tie_diameter_mm"]
    # These rods traverse the actual closed hoop in plan. Even/odd subsets can only
    # reduce the steel per metre available from one track. Retain the densest case.
    standard = (8,10,12,14,16,18,20,22,25)
    valid = [d for d in standard if pitch/2-(d+tie)/2 >= clear_limit(aggregate,d,tie)]
    if not valid:
        raise ValueError("NO_DIAMETER_CROSSES_W6_HOOP_AT_REQUIRED_CLEARANCE")
    dia = max(valid)
    grid = level_grid({"module":pitch,"height":height,"start":0.,"phase":0.,"inner":False,
                       "aggregate_mm":aggregate},dia,ceil(pitch),cover,minimum_per_m=floor(1000/pitch))
    if not grid:
        raise ValueError("NO_HOOP_SYNCHRONOUS_LEVELS_AT_PHYSICAL_COVER")
    h = {**grid,"diameter_mm":dia,"cover_mm":cover,"physical_height_mm":height}
    levels = [h["first_station_mm"]+j*pitch for j in range(h["layers"])]
    v = {"diameter_mm":dia,"pitch_mm":length/ceil(length/pitch)}
    steel = .6*2*h["guaranteed_bars_per_m"]*pi*dia**2/4*material.fyd/1000
    bond = tension_development(dia,material.fyd,material.fck,material.fcd,cover,pitch-dia)
    series = series_interface_checks(link["native_support_edges"],steel,bond["position_i_mm"],length,SELECTION_LIMIT)
    bars = [(section.t2/2+b.x2,b.x3,sqrt(4*b.area/pi)) for b in section.bars]
    extent = pier["adopted_constant_detail"]["end_width_mm"]
    boundary = [b for b in bars if 0 <= b[0] <= extent]
    if not boundary:
        raise ValueError("W6_BOUNDARY_BAR_CENTRES_MISSING")
    legal = min(thick/2,section.t3/2)-cover-dia/2
    tracks = corridors([(y,d) for x,y,d in boundary],0.,legal,dia,aggregate)
    if not tracks:
        raise ValueError("NO_STRAIGHT_BRIDGE_TRACK_IN_BOUNDARY")
    lane = floor(max(b for a,b in tracks))  # specify an integer-mm centreline inside the tolerance
    vertical_offset = lane-dia
    reserve = clear_limit(aggregate,dia,dia)+dia
    # Dedicated dowels must also pass the link's verticals and the symmetric
    # web rods. Move them to the widest admissible inner track.
    inner = [(a,min(b,vertical_offset-reserve)) for a,b in tracks if a<=vertical_offset-reserve]
    if not inner:
        raise ValueError("NO_INDEPENDENT_DOWEL_TRACK_BETWEEN_WEB_AND_BOUNDARY_BARS")
    dowel_lane = max(b for _,b in inner)
    xtracks = corridors([(x,d) for x,y,d in boundary],-legal,legal,dia,aggregate)
    positive = [(max(0.,a),b) for a,b in xtracks if b>0.]
    symmetric = max((b for a,b in positive if any(lo<=-b<=hi for lo,hi in xtracks)),default=0.)
    fields_receipt = {}
    field_caches = {p["member"]:{} for p in (straight,link,turn)}
    for panel, normal, member_states in ((straight,lane,fields[straight["member"]]),
            (link,lane,fields[link["member"]]),(turn,legal,fields[turn["member"]])):
        check=check_curtains(member_states,field_caches[panel["member"]],thick,h,v,material,normal)
        fields_receipt[panel["member"]]={"normal_mm":normal,"lever_arm_mm":check["lever_arm_mm"],
            "position_scope":"OPTIMISTIC_OUTER_FACE_BEFORE_PLAN_CLEARANCE" if panel is turn else "SYNCHRONIZED_TRACK",
            "steel_max":check["steel_max"],"governing":check["governing"],"satisfied":check["satisfied"]}
    turn_peak = max(r["equivalent_friction_demand_kn_m"] for r in turn["native_support_edges"][turn_side]["cuts"])
    far = next(s for s,vv in link["support_sections"].items() if vv["joint"]==turn["joint_"+turn_side.lower()])
    foreign = next(w for w in link["support_sections"][far]["incident_walls"] if w["member"] in pier["member_ids"])
    direction = foreign["direction"]
    normal = (-direction[1],direction[0])
    near = (-length*direction[0],-length*direction[1])
    paths=[]
    if symmetric>0.:
        # Try the outermost symmetric X-stations inside the crossing corridors.
        # Each bend and its full developed tail remain in the path tested below.
        for panel,side,offset,dowel,start in ((straight,straight_side,lane,dowel_lane,near),
                                             (turn,turn_side,symmetric,symmetric/2,(0.,0.))):
            dedicated = {**h,"offset_each_side_mm":dowel}
            support = panel["support_sections"][side]
            web = wall_return_anchor(support,panel,side,dia,offset,cover,pitch-dia,material,aggregate,
                                     tail_track=legal-10 if panel is turn else None)
            anch = wall_return_anchor(support,panel,side,dia,dowel,cover,pitch-dia,material,aggregate,
                                      tail_track=32. if panel is turn else None)
            detail = {**web,"transfer":{**dedicated,"column_embedment_mm":anch["specified_embedment_mm"],
                      "wall_embedment_mm":anch["position_i_mm"],"anchor":anch}}
            if web["fits_column"] and anch["fits_column"]:
                panel_h = {**h,"curtain_inset_mm":thick/2-cover-1.5*dia-offset}
                paths.extend(_translated(f,*start) for f in _families({**panel,"horizontal":panel_h},side,detail))
    from itertools import combinations
    pairs = [_separation(a,b,aggregate) for a,b in combinations(paths,2)]
    minimum = None
    for f in paths:
        for x,y,d in bars:
            point = tuple(x*direction[i]+y*normal[i] for i in (0,1))
            gap = min(point_distance(point,a,b)-err for a,b,err in _segments(f))-(dia+d)/2
            item = {"member":f["member"],"role":f["role"],"face":f["face"],"station_xy_mm":[x,y],
                    "margin_mm":gap-clear_limit(aggregate,dia,d),"clear_mm":gap}
            if minimum is None or item["margin_mm"] < minimum["margin_mm"]:
                minimum=item
    phase_trials=[]
    # Every other hoop midpoint separates crossing runs but also halves guaranteed
    # reinforcement. Recheck capacity on the actual finite grid in both assignments.
    for straight_phase,turn_phase in ((None,None),(0,1),(1,0)):
        staged=[]
        grids={}
        for panel,phase in ((straight,straight_phase),(turn,turn_phase)):
            stride=1 if phase is None else 2
            grid=level_grid({"module":pitch,"height":height,"start":0.,"phase":phase or 0.,
                             "inner":False,"aggregate_mm":aggregate},dia,ceil(stride*pitch),cover,
                            minimum_per_m=floor(1000/(stride*pitch)))
            if not grid: break
            grids[panel["member"]]=grid
            for fam in paths:
                if fam["member"]==panel["member"]:
                    staged.append({**fam,"heights":[grid["first_station_mm"]+i*grid["pitch_mm"] for i in range(grid["layers"])]})
        if len(grids)!=2:
            continue
        checks=[_separation(a,b,aggregate) for a,b in combinations(staged,2)]
        straight_grid=grids[straight["member"]]
        turn_grid=grids[turn["member"]]
        turn_resistance=steel*turn_grid["guaranteed_bars_per_m"]/h["guaranteed_bars_per_m"]
        per_panel={}
        for panel,offset,grid in ((straight,lane,straight_grid),(link,lane,straight_grid),(turn,symmetric,turn_grid)):
            if 2*offset <= 2*dia:
                per_panel[panel["member"]]={"satisfied":False,"reason":"INSUFFICIENT_INTERNAL_LEVER_ARM"}
                continue
            evaluated=check_curtains(fields[panel["member"]],field_caches[panel["member"]],thick,
                                     {**h,**grid},v,material,offset)
            per_panel[panel["member"]]={k:evaluated[k] for k in ("lever_arm_mm","satisfied","steel_max","governing")}
        phase_trials.append({"straight_phase":straight_phase,"turn_phase":turn_phase,"grids":grids,
            "curtain_checks":per_panel,"checked_bar_paths":len(staged),"W55_dowel_ratio":turn_peak/turn_resistance,
            "mutual_governing":min(checks,key=lambda x:x["margin_mm"]) if checks else None,
            **link_clearances(staged,straight["member"],length,v["pitch_mm"],lane,vertical_offset,dia,
                              direction,normal,hoops,tie,aggregate)})
    # Count the positive-face corridors using the smallest catalogue bar. If
    # a corridor cannot contain two centre-lines even at independently staggered
    # elevations, its largest feasible diameter bounds its steel throughput.
    positive_by_d = {d:corridors([(x,b) for x,y,b in boundary],0.,thick/2-cover-d/2,d,aggregate) for d in valid}
    cells = []
    smallest = min(valid)
    dzmax = pitch-(smallest+tie)-2*clear_limit(aggregate,smallest,tie)
    for lo,hi in positive_by_d[smallest]:
        largest = max(d for d,rows in positive_by_d.items() if any(max(lo,a)<=min(hi,b) for a,b in rows))
        single = hypot(hi-lo,dzmax)<smallest+clear_limit(aggregate,smallest)
        cells.append({"from_mm":lo,"to_mm":hi,"largest_diameter_mm":largest,"at_most_one_per_hoop":single})
    optimistic = None
    if cells and all(c["at_most_one_per_hoop"] for c in cells):
        max_area = ceil(1000/pitch)*sum(pi*c["largest_diameter_mm"]**2/4 for c in cells)
        upper = max_area*material.fyd/1000
        from .wall_membrane_design import required_face_forces
        # Give both faces the largest possible lever, even ignoring vertical bars.
        # The maximum over both signs is convex and even in inverse lever arm,
        # so this supplies a lower demand for any symmetric smaller arm.
        optimistic_arm=thick-2*cover-smallest
        demand=max(required_face_forces(membrane,plate[:3],sign,optimistic_arm/1000)[0]
                   for states in fields[turn["member"]].values() for _,_,membrane,plate in states for sign in (-1,1))
        optimistic = {"positive_face_corridors":cells,"area_upper_mm2_per_m":max_area,
                      "resistance_upper_kn_m":upper,"optimistic_arm_mm":optimistic_arm,"horizontal_demand_at_outer_tracks_kn_m":demand,
                      "symmetric_curtain_ratio_at_outer_tracks":demand/upper,
                      "includes_all_positive_tracks_no_steel_reserved_for_dowels":True}
    return {"scope":"ONE_CONTINUOUS_ROD_PER_FACE_ROLE_PER_HOOP_INTERVAL",
        "symmetric_multiple_track_bound":optimistic,"phase_trials":phase_trials,
        "section_checks":{panel["member"]:cut_section_checks(panel,link["member"],cuts,fields[panel["member"]],
                         material,dia,v["pitch_mm"],offset-dia,aggregate)
                         for panel,offset in ((straight,lane),(link,lane),(turn,symmetric))},
        "selection_limit":SELECTION_LIMIT,"height_mm":height,"hoop_count":count,"hoop_pitch_mm":pitch,
        "first_hoop_mm":hoops[0],"last_hoop_mm":hoops[-1],"first_bar_mm":levels[0],"last_bar_mm":levels[-1],
        "bar_levels":len(levels),"diameter_mm":dia,"maximum_diameter_by_hoop_mm":max(valid),
        "hoop_clear_mm":_closest_levels(levels,hoops)[0]-(dia+tie)/2,"required_clear_mm":clear_limit(aggregate,dia,tie),
        "W31_track_mm":lane,"W31_dowel_track_mm":dowel_lane,"W32_vertical_track_mm":vertical_offset,
        "W32_vertical_pitch_mm":v["pitch_mm"],"symmetric_W55_track_mm":symmetric,"W55_x_corridors_mm":xtracks,
        "W55_dowel_demand_kn_m":turn_peak,"dowel_resistance_kn_m":steel,"W55_dowel_ratio":turn_peak/steel,
        "curtain_checks":fields_receipt,"series_interface_checks":series,
        "checked_bar_paths":len(paths),"mutual_governing":min(pairs,key=lambda x:x["margin_mm"]) if pairs else None,
        "receiving_vertical_governing":minimum}
