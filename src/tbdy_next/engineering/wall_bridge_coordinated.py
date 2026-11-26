"""Finite hoop-window reinforcement trial for a rectangular boundary with a short return."""
from itertools import combinations
from math import ceil, floor, hypot, pi, sqrt

from .basement_joint_layout import _closest_levels, _families, _segments, _separation
from .basement_wall_connection import tension_development, wall_return_anchor
from .basement_wall_pressure import clear_limit
from .wall_bar_paths import point_distance
from .wall_bridge_trial import corridors, cut_section_checks
from .wall_membrane_design import SELECTION_LIMIT, check_curtains


def window_grid(height, pitch, offsets, diameter, cover, aggregate):
    """Count bars in every physical metre, including the cropped first and last hoop bays."""
    centre = cover+diameter/2
    levels = sorted(k*pitch+z for k in range(-1,ceil(height/pitch)+2) for z in offsets
                    if centre <= k*pitch+z <= height-centre)
    if len(levels)<2 or height<1000:
        raise ValueError("SHORT_HOOP_GRID")
    clear = min(b-a for a,b in zip(levels,levels[1:]))-diameter
    if clear+1.e-8 < clear_limit(aggregate,diameter):
        raise ValueError("COORDINATED_BAR_LEVEL_CLEARANCE")
    # A closed interval reaches its smallest count just after a bar exits at the left end.
    events = [0.,height-1000]+[v+1.e-7 for v in levels if v+1.e-7 <= height-1000]
    guaranteed = min(sum(a<=v<=a+1000 for v in levels) for a in events)
    return {"levels_mm":levels,"guaranteed_bars_per_m":guaranteed,"diameter_mm":diameter,
            "clear_spacing_mm":clear,"pitch_mm":pitch,"layers":len(levels),"first_station_mm":levels[0]}


def _receiving_clearance(family,bars,aggregate):
    dia = family["diameter"]
    samples = []
    for point,d in bars:
        gap = min(point_distance(point,a,b)-err for a,b,err in _segments(family))-(d+dia)/2
        samples.append((gap-clear_limit(aggregate,d,dia),gap,point))
    margin,clear,station = min(samples)
    return {"margin_mm":margin,"clear_mm":clear,"station_mm":station,"member":family["member"],"role":family["role"]}


def endpoint_match(panel,side,proposed,vertical):
    """Compare the through-web grid with the one actually detailed and verified at the remote end."""
    existing = panel.get("two_way_shell",{}).get("proposed_detail",{})
    main = existing.get("horizontal",{})
    peer = "I" if side=="J" else "J"
    old_vertical = existing.get("vertical",{})
    out = {"joint":panel["joint_"+peer.lower()],"proposed_diameter_mm":proposed["web"]["diameter_mm"],
           "existing_diameter_mm":main.get("diameter_mm"),"existing_pitch_mm":main.get("pitch_mm"),
           "same_web":False,"same_verticals":False}
    if not main or not old_vertical or not existing.get("ends",{}).get(peer):
        return out
    offset = panel["thickness_m"]*500-main["cover_mm"]-main["curtain_inset_mm"]-1.5*main["diameter_mm"]
    levels = proposed["web"]["levels_mm"]
    out["same_web"] = (main["diameter_mm"]==proposed["web"]["diameter_mm"]
        and abs(offset-proposed["web_track_mm"])<1.e-6
        and all(grid["layers"]==len(levels) and all(abs(z-grid["first_station_mm"]-i*grid["pitch_mm"])<1.e-6
                for i,z in enumerate(levels)) for grid in (main,main.get("opposite_face_levels",main))))
    out["same_verticals"] = (old_vertical["diameter_mm"]==vertical["vertical_diameter_mm"]
        and abs(old_vertical["pitch_mm"]-vertical["vertical_pitch_mm"])<1.e-6
        and abs(offset-(main["diameter_mm"]+old_vertical["diameter_mm"])/2-vertical["vertical_offset_mm"])<1.e-6)
    return out


def coordinated_trial(straight,turn,link,ns,fs,section,pier,states,material,aggregate,cover,height,cuts):
    from .wall_bridge_layout import series_interface_checks, _translated
    cage = pier["transverse_cage"]
    width,length = 1000*link["thickness_m"],1000*link["span_m"]
    if abs(width-400)>1.e-5 or abs(length-width)>1.e-5:
        raise ValueError("COORDINATED_SHORT_SQUARE_LINK_REQUIRED")
    count = ceil(height/cage["spacing_mm"])
    pitch = height/count
    hoops = [(k+.5)*pitch for k in range(count)]
    small,web,edge = 14,25,22
    distance = (small+clear_limit(aggregate,small))/2+.2
    small_grid = window_grid(height,pitch,[-distance,distance],small,cover,aggregate)
    tie = cage["tie_diameter_mm"]
    shift = pitch/2-clear_limit(aggregate,edge,tie)-(edge+tie)/2-.15
    web_shift = pitch/2-clear_limit(aggregate,web,tie)-(web+tie)/2-.15
    if min(shift,web_shift) <= 0:
        raise ValueError("NO_W55_HOOP_WINDOW")
    turn_grid = window_grid(height,pitch,[-web_shift],web,cover,aggregate)
    edge_grid = window_grid(height,pitch,[shift],edge,cover,aggregate)
    foreign, = [v for r in link["support_sections"].values() for v in r["incident_walls"] if v["member"] in pier["member_ids"]]
    d = foreign["direction"]
    n = (-d[1],d[0])
    bars = [(section.t2/2+b.x2,b.x3,sqrt(4*b.area/pi)) for b in section.bars]
    xyz = [((x*d[0]+y*n[0],x*d[1]+y*n[1]),dia) for x,y,dia in bars]
    boundary = [(x,y,dia) for x,y,dia in bars if x<=pier["adopted_constant_detail"]["end_width_mm"]]
    def legal_tracks(use_x,dia):
        return corridors([(x if use_x else y,bar) for x,y,bar in boundary],0.,width/2-cover-dia/2,dia,aggregate)
    ys = legal_tracks(False,small)
    xs = legal_tracks(True,web)
    dx = legal_tracks(True,edge)
    if not ys or not xs or not dx:
        raise ValueError("NO_RECEIVING_PLAN_CORRIDOR")
    main_y = floor(ys[-1][1]-.01)
    dowel_y = ceil(ys[-1][0]+.01)
    main_x = floor(xs[-1][1]-.01)
    dowel_x = ceil(dx[-1][0]+3.)
    profiles = [(straight,ns,small_grid,small_grid,main_y,dowel_y,(-length*d[0],-length*d[1])),
                (turn,fs,turn_grid,edge_grid,main_x,dowel_x,(0.,0.))]
    curtain_checks,section_checks,dowels,anchors = {},{},{},{}
    link_diameter,link_pitch=20,length/3
    for panel,grid,offset in ((straight,small_grid,main_y),(link,small_grid,main_y),(turn,turn_grid,main_x)):
        uid = panel["member"]
        vdia,vertical_pitch = (22,200.) if panel is turn else (link_diameter,link_pitch)
        vert = {"diameter_mm":vdia,"pitch_mm":vertical_pitch}
        vertical_offset = offset+(vdia+grid["diameter_mm"])/2 if panel is not turn else offset-(vdia+grid["diameter_mm"])/2
        field = check_curtains(states[uid],{},width,grid,vert,material,offset,vertical_offset_mm=vertical_offset)
        curtain_checks[uid] = {k:field[k] for k in ("lever_arm_mm","governing","steel_max")}
        curtain_checks[uid].update(satisfied=field["satisfied"] and field["governing"]["utilization"]<=SELECTION_LIMIT,
                                   vertical_diameter_mm=vdia,vertical_pitch_mm=vertical_pitch,
                                   vertical_offset_mm=vertical_offset)
        if vertical_offset+vdia/2+cover>width/2:
            raise ValueError("WEB_VERTICAL_OUTSIDE_REAL_COVER")
        # The sandwich reference uses the smaller inscribed lever arm. PMM uses the actual bars.
        section_checks[uid] = cut_section_checks(panel,link["member"],cuts,states[uid],material,vdia,
                                                vertical_pitch,vertical_offset,aggregate)
    families=[]
    for panel,side,h,q,offset,qo,start in profiles:
        uid = panel["member"]
        built=[]
        ends=[]
        for role,grid,lane in (("web",h,offset),("dowel",q,qo)):
            dia=grid["diameter_mm"]
            support=panel["support_sections"][side]
            dest = None if panel is straight else ({-1:-70.,1:70.} if role=="web" else {-1:25.,1:-25.})
            anchor = wall_return_anchor(support,panel,side,dia,lane,cover,grid["clear_spacing_mm"],material,
                                        aggregate,face_lanes=dest)
            ends.append(anchor)
            anchors[uid+"_"+role] = {k:anchor.get(k) for k in ("fits_column","receiving_members","return_shape",
                                     "specified_embedment_mm","wall_side_available_mm","position_i_mm")}
        if all(a["fits_column"] for a in ends):
            detail = {**ends[0],"transfer":{**q,"offset_each_side_mm":qo,"anchor":ends[1],
                      "column_embedment_mm":ends[1]["specified_embedment_mm"],"wall_embedment_mm":ends[1]["position_i_mm"]}}
            horizontal = {**h,"cover_mm":cover,"curtain_inset_mm":width/2-cover-1.5*h["diameter_mm"]-offset}
            for f in _families({**panel,"horizontal":horizontal},side,detail):
                actual = h if f["role"]=="web" else q
                built.append(_translated({**f,"heights":actual["levels_mm"]},*start))
        families.extend(built)
        cap = .6*2*q["guaranteed_bars_per_m"]*pi*q["diameter_mm"]**2/4*material.fyd/1000
        demand = max(c["equivalent_friction_demand_kn_m"] for c in panel["native_support_edges"][side]["cuts"])
        dowels[uid] = {"resistance_kn_m":cap,"demand_kn_m":demand,"ratio":demand/cap,"satisfied":demand/cap<=SELECTION_LIMIT}
    cap = dowels[straight["member"]]["resistance_kn_m"]
    lb = tension_development(small,material.fyd,material.fck,material.fcd,cover,small_grid["clear_spacing_mm"])
    series = series_interface_checks(link["native_support_edges"],cap,lb["position_i_mm"],length,SELECTION_LIMIT)
    pairs = [_separation(a,b,aggregate) for a,b in combinations(families,2)]
    rebar = [_receiving_clearance(f,xyz,aggregate) for f in families]
    hoop = [{"member":f["member"],"role":f["role"],"clear_mm":_closest_levels(f["heights"],hoops)[0]-(f["diameter"]+tie)/2,
             "required_mm":clear_limit(aggregate,f["diameter"],tie)} for f in families]
    actual = {p["member"]:{"web_track_mm":y,"dowel_track_mm":a,"web":g,"dowel":q}
              for p,_,g,q,y,a,_ in profiles}
    from .wall_bridge_routes import route_search
    nvert=round(length/link_pitch)
    pts=[(tuple((-length+(j+.5)*link_pitch)*d[k]+sign*(main_y+(small+link_diameter)/2)*n[k] for k in (0,1)),link_diameter)
         for j in range(nvert) for sign in (-1,1)]
    straight_families = [f for f in families if f["member"]==straight["member"]]
    routes=route_search(turn,fs,straight_families,
                        xyz,actual[turn["member"]],material,cover,aggregate,height,pitch,tie,pts,d,pier["adopted_constant_detail"]["end_width_mm"])
    from .wall_bridge_trial import link_clearances
    chosen = straight_families + routes["selected_families"]
    remote = {p["member"]:endpoint_match(p,side,actual[p["member"]],curtain_checks[p["member"]])
              for p,side in ((straight,ns),(turn,fs))}
    ties = link_clearances(chosen,straight["member"],length,link_pitch,main_y,main_y+(small+link_diameter)/2,
                           link_diameter,d,n,hoops,tie,aggregate) if len(chosen)==8 else {"complete":False}
    constraints = {
        "shell_reserve":all(v["satisfied"] for v in curtain_checks.values()),
        "all_pmm_sections":all(v.get("satisfied",False) for v in section_checks.values()),
        "independent_dowels":all(v["satisfied"] for v in dowels.values()),
        "serial_friction":series["friction_satisfied"],"differential_bond":series["bond_satisfied"],
        "developed_through_bars":all(ends["return_shape"]=="STRAIGHT_THROUGH_RECEIVING_WEB"
            and ends["specified_embedment_mm"]-length>=ends["position_i_mm"]-1.e-7
            for key,ends in anchors.items() if key.startswith(straight["member"]+"_")),
        "continuous_web_and_dowel_routes":routes["all_four_paths_fit"],
        "remote_web_and_vertical_details":all(v["same_web"] and v["same_verticals"] for v in remote.values()),
        "link_verticals_and_ties":(ties["complete"] and ties["link_vertical_governing"]["margin_mm"]>=0
                                   and ties["link_crosstie_governing"]["surface_separation_mm"]>0),
        "straight_bar_clearances":len(straight_families)==4
            and all(_separation(a,b,aggregate)["fits"] for a,b in combinations(straight_families,2))
            and all(_receiving_clearance(f,xyz,aggregate)["margin_mm"]>=0 for f in straight_families)
            and all(h["clear_mm"]>=h["required_mm"] for h in hoop if h["member"]==straight["member"]),
    }
    return {"basis":"COORDINATED_FINITE_HOOP_WINDOWS_AND_PHYSICAL_ELEMENT_INTERVALS","return_routes":routes,
            "checks":constraints,"unresolved":[k for k,v in constraints.items() if not v],
            "status":"COMPLETE_LAYOUT" if all(constraints.values()) else "HOLD",
            "link_crosstie_checks":ties,"remote_endpoint_comparisons":remote,
            "height_mm":height,"cover_mm":cover,"hoop_count":count,"pitch_mm":pitch,"families":actual,
            "steel_selection_limit":SELECTION_LIMIT,"curtains":curtain_checks,"sections":section_checks,
            "dowels":dowels,"series_interface_checks":series,"anchors":anchors,"checked_entry_paths":len(families),
            "receiving_vertical":min(rebar,key=lambda x:x["margin_mm"]) if rebar else None,
            "mutual_clearance":min(pairs,key=lambda x:x["margin_mm"]) if pairs else None,"hoop_clearance":hoop,
            "remote_interfaces":[straight["joint_i" if ns=="J" else "joint_j"],turn["joint_i" if fs=="J" else "joint_j"]]}
