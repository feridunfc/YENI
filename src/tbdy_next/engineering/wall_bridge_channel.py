"""Finite common tracks for the short link and the adjoining rectangular end cage."""
from itertools import combinations
from math import ceil, floor, pi, sqrt

from .basement_joint_layout import _families, _separation
from .basement_wall_connection import tension_development, wall_return_anchor
from .basement_wall_pressure import clear_limit
from .wall_bridge_coordinated import _receiving_clearance, window_grid
from .wall_bridge_layout import _translated, series_interface_checks
from .wall_bridge_routes import route_search
from .wall_bridge_trial import corridors, cut_section_checks
from .wall_membrane_design import SELECTION_LIMIT, check_curtains


def channel_trial(straight, turn, link, ns, fs, section, pier, states, material, aggregate, cover, height, cuts, *, neighbours=None, designs=None, remote_profile=None, coordinates=None):
    cage = pier["transverse_cage"]
    tie = cage["tie_diameter_mm"]
    length, width = link["span_m"]*1000, link["thickness_m"]*1000
    if abs(width-length)>1.e-5 or abs(section.t3-width)>1.e-5:
        raise ValueError("CHANNEL_SQUARE_LINK_AND_MATCHED_RECEIVER_REQUIRED")
    count = ceil(height/cage["spacing_mm"])
    pitch = height/count
    # Locate the two rods separately. The third clear gap is between the rods.
    diameters = (18,16)
    clearance = (pitch-tie-sum(diameters))/3
    if clearance < max(clear_limit(aggregate,d,tie) for d in diameters):
        raise ValueError("CHANNEL_HOOP_WINDOW_TOO_SMALL")
    interbar = max(clearance,1.5*max(diameters)+.3)
    outer_gap = (pitch-tie-sum(diameters)-interbar)/2
    if outer_gap < max(clear_limit(aggregate,d,tie) for d in diameters):
        raise ValueError("CHANNEL_ROD_SPACING_AND_HOOP_CLEARANCE_INCOMPATIBLE")
    phases = (-pitch/2+tie/2+outer_gap+diameters[0]/2,
               pitch/2-tie/2-outer_gap-diameters[1]/2)
    grids = [window_grid(height,pitch,[z],d,cover,aggregate) for d,z in zip(diameters,phases)]
    arm, = [a for side in link["support_sections"].values() for a in side["incident_walls"]
            if a["member"] in pier["member_ids"]]
    d = arm["direction"]
    n = (-d[1],d[0])
    end = pier["adopted_constant_detail"]["end_width_mm"]
    bars = [(section.t2/2+b.x2,b.x3,sqrt(4*b.area/pi)) for b in section.bars]
    xyz = [((x*d[0]+y*n[0],x*d[1]+y*n[1]),dia) for x,y,dia in bars]
    boundary = [(x,y,dia) for x,y,dia in bars if x<=end]
    def lanes(axis,dia):
        rows = [(v[axis],v[2]) for v in boundary]
        return corridors(rows,0.,width/2-cover-dia/2,dia,aggregate)
    tracks = lanes(1,max(diameters))
    if not tracks or tracks[0][0] > 0:
        raise ValueError("CENTRE_CHANNEL_OCCUPIED")
    offset = floor(tracks[0][1]-.01)
    areas = [g["guaranteed_bars_per_m"]*pi*d*d/4 for g,d in zip(grids,diameters)]
    equiv = {"guaranteed_bars_per_m":1,"diameter_mm":sqrt(4*sum(areas)/pi)}
    h = dict(web=grids[0],dowel=grids[1],web_track_mm=offset,dowel_track_mm=offset)
    web, edge = 24,22
    xw, xe = lanes(0,web),lanes(0,edge)
    if not xw or not xe:
        raise ValueError("TURNING_WALL_ENTRY_LANES_REQUIRED")
    turn_layout = dict(web=window_grid(height,pitch,[0.],web,cover,aggregate),
                       dowel=window_grid(height,pitch,[0.],edge,cover,aggregate),
                       web_track_mm=min(floor(xw[-1][1]-.01),width/2-cover-25/2-12),
                       dowel_track_mm=floor(xe[0][1]-.1))
    if not any(low<=turn_layout["web_track_mm"]<=high for low,high in xw):
        raise ValueError("TURNING_CURTAIN_AND_OUTSIDE_VERTICAL_LANE_REQUIRED")
    # Both entering grids cross I and J on continuous tracks and develop at the far ends.
    # Their finite-window steel area is shared by sandwich and friction demands.
    supports = straight["support_sections"][ns]
    anchors = [wall_return_anchor(supports,straight,ns,dia,offset,cover,interbar,material,aggregate,
                                  continuous_leg=True) for dia in diameters]
    if not all(a["fits_column"] and a["return_shape"]=="STRAIGHT_THROUGH_RECEIVING_WEB"
               and a["specified_embedment_mm"]-length>=a["position_i_mm"]-1.e-7 for a in anchors):
        raise ValueError("UNINTERRUPTED_THROUGH_TRACKS_REQUIRE_REAL_TERMINAL_DEVELOPMENT")
    detail = {**anchors[0],"transfer":{**grids[1],"anchor":anchors[1],"offset_each_side_mm":offset,
              "wall_embedment_mm":anchors[1]["position_i_mm"],"column_embedment_mm":anchors[1]["specified_embedment_mm"]}}
    main = {**grids[0],"cover_mm":cover,"curtain_inset_mm":width/2-cover-1.5*diameters[0]-offset}
    continuous = [_translated({**f,"heights":h[f["role"]]["levels_mm"]},-length*d[0],-length*d[1])
                  for f in _families({**straight,"horizontal":main},ns,detail)]
    vt = offset+(max(diameters)+20)/2
    link_pitch = length/3
    verts = [(tuple((-length+(i+.5)*link_pitch)*d[k]+sign*vt*n[k] for k in (0,1)),20)
             for i in range(3) for sign in (-1,1)]
    # Route the selected 24 mm web inside a 25 mm bending/clearance template.
    # The retained centreline, elevations and straight development are unchanged.
    template={**turn_layout,"web":window_grid(height,pitch,[0.],25,cover,aggregate)}
    routes = route_search(turn,fs,continuous,xyz,template,material,cover,aggregate,height,pitch,tie,verts,d,end)
    for family in routes["selected_families"]:
        if family["role"]=="web":
            family["diameter"]=web
            if family["face"]==-1:
                from .wall_channel_lap import _min_count
                cropped=family["heights"][1:-1]
                # The first/last short bays overlap the terminal donor groups.
                # Keep the physical end distance within 200 mm and verify every
                # full-metre window before changing either end of the finite grid.
                if (cropped and max(cropped[0],height-cropped[-1])<=200.
                        and _min_count(cropped,height)>=turn_layout["web"]["guaranteed_bars_per_m"]):
                    family["heights"]=cropped
                    routes["selection"]["web_minus"].update(installed_levels_mm=cropped,
                                                             edge_starters_terminate_straight=True)
    routes["web_bending_template_diameter_mm"]=25
    curtains, sections = {}, {}
    for obj,grid,track,vdiam,vpitch,vtrack in (
        (straight,equiv,offset,14,150.,offset-(max(diameters)+14)/2),(link,equiv,offset,20,link_pitch,vt),
        (turn,turn_layout["web"],turn_layout["web_track_mm"],22,200,turn_layout["web_track_mm"]-(web+22)/2)):
        uid = obj["member"]
        field=check_curtains(states[uid],{},width,grid,{"diameter_mm":vdiam,"pitch_mm":vpitch},
                             material,track,vertical_offset_mm=vtrack)
        curtains[uid] = field
        sections[uid] = cut_section_checks(obj,link["member"],cuts,states[uid],material,vdiam,vpitch,vtrack,aggregate)
    steel = sum(areas)*material.fyd/1000
    lengths = [tension_development(dia,material.fyd,material.fck,material.fcd,cover,interbar)["position_i_mm"]
               for dia in diameters]
    # Split both actions by actual steel area. Each diameter develops its own increase
    # in tensile stress over the available length. Use the longer development requirement.
    series=series_interface_checks(link["native_support_edges"],1.2*steel,max(lengths),length,SELECTION_LIMIT)
    shared=[]
    for obj, sides in ((straight,("I","J")),(link,("I","J"))):
        for side in sides:
            for c in obj["native_support_edges"][side]["cuts"]:
                name=c["combination"]
                check=next(x for x in curtains[obj["member"]]["checks"]
                           if x["action"]=="Horizontal steel" and x["combination"]==name)
                shell=check["demand_kn_m"]
                friction=c["equivalent_friction_demand_kn_m"]/1.2
                shared.append({"member":obj["member"],"side":side,"combination":name,
                               "shell_tie_kn_m":shell,"friction_tie_kn_m":friction,
                               "per_face_resistance_kn_m":steel,"utilization":(shell+friction)/steel})
    chosen=continuous+routes["selected_families"]
    mutual = min((_separation(a,b,aggregate) for a,b in combinations(chosen,2)),key=lambda r:r["margin_mm"])
    result = {"basis":"FINITE_CENTRE_CHANNEL_WITH_SHARED_FACE_STEEL","status":"HOLD","pitch_mm":pitch,
              "height_mm":height,"cover_mm":cover,"tie_mm":tie,"hoop_count":count,"clear_window_mm":outer_gap,"interbar_clear_mm":interbar,
              "straight_tracks_mm":[-offset,offset],"diameters_mm":list(diameters),"phases_mm":list(phases),
              "guaranteed_bars_per_face_per_m":[g["guaranteed_bars_per_m"] for g in grids],
              "shared_steel":shared,"series_interface_checks":series,"return_routes":routes,
              "mutual_clearance":mutual,"curtains":{k:{"governing":v["governing"],"lever_arm_mm":v["lever_arm_mm"]}
              for k,v in curtains.items()},"sections":sections,"turn_layout":turn_layout,
              "receiving_vertical":min((_receiving_clearance(f,xyz,aggregate) for f in chosen),key=lambda r:r["margin_mm"])}
    result["checks"]={"shell_and_shared_friction":max(row["utilization"] for row in shared)<=SELECTION_LIMIT
                      and all(q["governing"]["utilization"]<=SELECTION_LIMIT for q in curtains.values()),
                      "pmm":all(q.get("satisfied") for q in sections.values()),
                      "friction_differential_bond":series["bond_satisfied"],"eight_routes":len(chosen)==8,
                      "incoming_turn_friction":max(row["equivalent_friction_demand_kn_m"] for row in turn["native_support_edges"][fs]["cuts"])
                      <=SELECTION_LIMIT*1.2*turn_layout["dowel"]["guaranteed_bars_per_m"]*pi*edge**2/4*material.fyd/1000}
    from .wall_channel_ties import link_ties
    ties = link_ties(chosen,continuous,verts,d,n,length,width,height,vt,20,cover,aggregate) if len(chosen)==8 else {"satisfied":False}
    result["link_crossties"] = ties
    result["checks"]["link_crossties"] = ties["satisfied"]
    from .wall_channel_bond import combined_bond
    bond = combined_bond(states[link["member"]],link["native_support_edges"],curtains[link["member"]]["lever_arm_mm"],
                         width,material,steel,length,max(lengths))
    result["combined_bond"] = bond
    result["checks"]["combined_bond"] = bond["satisfied"]
    result["checks"]["receiving_clearance"] = result["receiving_vertical"]["margin_mm"]>=0
    result["checks"]["mutual_clearance"] = all(_separation(a,b,aggregate)["fits"] for a,b in combinations(chosen,2))
    result["checks"]["serial_friction"] = series["friction_satisfied"]
    edge_checks=[]
    for panel in (straight,turn,link):
        for side in ("I","J"):
            edge_row=panel["native_support_edges"][side]
            limit=.2*min(material.fcd,25.)*panel["thickness_m"]*1000
            if side in panel.get("two_way_shell",{}).get("proposed_detail",{}).get("ends",{}):
                transfer=panel["two_way_shell"]["proposed_detail"]["ends"][side]["transfer"]
                limit=min(limit,transfer["concrete_limit_kn_m"])
            edge_checks.append({"member":panel["member"],"side":side,"status":edge_row["status"],
                "static_checks":edge_row["checked_static_interior"],"balanced":edge_row["balanced_static_interior"],
                "concrete_limit_kn_m":limit,"peak_concrete_ratio":max(
                    r["max_native_shear_kn_m"]/limit for r in edge_row["cuts"])})
    result["native_edge_checks"]=edge_checks
    result["checks"]["concrete_interface_and_equilibrium"]=all(row["status"]=="NATIVE_EDGE_CONTROL_SATISFIED" and
        row["static_checks"]==row["balanced"]>0 and row["peak_concrete_ratio"]<=1. for row in edge_checks)
    from .wall_channel_ends import column_end,corner_end
    remote={}
    if neighbours and designs:
        i="I" if ns=="J" else "J"
        j="I" if fs=="J" else "J"
        vcount=sections[straight["member"]]["stations_per_face"]
        vgrid={"track_mm":sections[straight["member"]]["vertical_offset_mm"],"diameter_mm":14,
               "stations_per_face":vcount,"pitch_mm":1000*straight["clear_length_m"]/vcount,"crosstie_diameter_mm":12}
        distance=1000*straight["span_m"]+length
        crossing=[_translated(f,distance*d[0],distance*d[1]) for f in routes["selected_families"]]
        remote["corner"],at_corner=corner_end(straight,i,neighbours,designs,h,vgrid,material,cover,aggregate,interbar,
                                               crossing=crossing)
        remote["column"]=column_end(turn,j,turn_layout,routes["selection"],material,cover,aggregate,states[turn["member"]])
        if coordinates and routes["all_four_paths_fit"]:
            from .wall_channel_lap import zoned_column_lap
            from .wall_channel_ties import tie_families
            installed=chosen+list(tie_families("link_crosstie",ties))
            lap=zoned_column_lap(turn,j,turn_layout,routes["selection"],states[turn["member"]],coordinates,
                                 material,cover,aggregate,near_families=installed)
            vg=lap["vertical"]
            regional_section=cut_section_checks(turn,link["member"],cuts,states[turn["member"]],material,
                vg["diameter_mm"],vg["pitch_mm"],vg["minimum_track_mm"],aggregate,offsets=vg["offsets_by_station_mm"])
            lap["section"]=regional_section
            remote["column"]["uniform_end_trial_unresolved"]=remote["column"]["unresolved"]
            remote["column"]["zoned_transition"]=lap
            checks={"SOURCE_REGISTERED_COLUMN_PASSAGE":lap["registered_column_passage"],
                    "FULL_YIELD_LAPS_AND_DONOR_CLEARANCE":all(all(f["checks"].values()) for f in lap["faces"].values()),
                    "VERTICAL_CLEARANCE":vg["governing_clearance_margin_mm"]>=0,
                    "REGIONAL_NATIVE_SHELL":lap["regional_shell"]["satisfied"],
                    "REGIONAL_SECTION_PMM":regional_section["satisfied"],
                    "LAP_CONFINEMENT_LAYOUT":all(r["satisfied"] for r in lap["lap_confinement"].values()),
                    "STRAIGHT_LAP_INSIDE_VERTICAL_CURTAIN_TBDY_7_6_4":all(
                        r["satisfied"] for r in lap["straight_lap_enclosure"].values()),
                    "CRANK_TRANSVERSE_FORCE_EQUILIBRIUM":lap["crank_tie_equilibrium"]["directionally_admissible"],
                    "CRANK_HOOK_PAIRS_AT_RETAINED_LEVELS":not lap["crank_tie_equilibrium"]["unbraced"],
                    "SIMULTANEOUS_CRANK_HOOK_GEOMETRY":lap["crank_tie_equilibrium"]["common_plane_assembly"]["satisfied"]}
            remote["column"]["zoned_transition_checks"]=checks
            open_items=[name for name,ok in checks.items() if not ok]
            # Directional admissibility alone cannot qualify undimensioned hooks.
            remote["column"]["unresolved"]=open_items or ["COMPLETE_REGIONAL_CAGE_INTERSECTION_AUDIT_REQUIRED"]
            result["sections"][turn["member"]]=regional_section
            result["checks"]["pmm"]=all(item["satisfied"] for item in result["sections"].values())
            result["checks"]["shell_and_shared_friction"]=(lap["regional_shell"]["satisfied"] and
                all(curtains[p["member"]]["governing"]["utilization"]<=SELECTION_LIMIT for p in (straight,link)) and
                all(r["utilization"]<=SELECTION_LIMIT for r in shared))
        # Test the exact two remote through-column grids on the near side. A
        # single bar height and a repeated path for a whole face are distinct trials.
        original=turn["two_way_shell"]["proposed_detail"]["horizontal"]
        levels={}
        for face in (-1,1):
            g=original.get("opposite_face_levels",original) if face==1 else original
            levels[face]=[g["first_station_mm"]+k*g["pitch_mm"] for k in range(g["layers"])]
        lane=width/2-original["cover_mm"]-original["curtain_inset_mm"]-1.5*original["diameter_mm"]
        fixed={**turn_layout,"web":{**original,"fixed_levels_by_face":levels},"web_track_mm":lane}
        inventory=route_search(turn,fs,continuous,xyz,fixed,material,cover,aggregate,height,pitch,tie,verts,d,end,
                               fixed_web_census=True)
        remote["column"]["registered_grid_trial"]={"track_mm":lane,"diameter_mm":original["diameter_mm"],
            "levels_by_face":{str(face):len(z) for face,z in levels.items()},
            "cases":inventory,"scope":"Fixed registered levels and one repeated bend per face into either receiving arm"}
        if remote_profile:
            from .wall_channel_ends import column_hook_options
            remote["column"]["hook_catalogue"]=column_hook_options(remote_profile,turn,j,material,cover,aggregate)
        if at_corner:
            adjacent=[_translated(f,-distance*d[0],-distance*d[1]) for f in at_corner if f["member"]!=straight["member"]]
            check=[_separation(a,b,aggregate) for a in adjacent for b in routes["selected_families"]]
            remote["overlap"]=min(check,key=lambda x:x["margin_mm"]) if check else None
    result["remote_endpoint_comparisons"]=remote
    result["checks"]["remote_corner_and_overlap"]=bool(remote.get("corner",{}).get("complete_corner")
                                                and (remote.get("overlap") or {}).get("fits"))
    result["checks"]["remote_column"]=remote.get("column",{}).get("status")=="VERIFIED_DEVELOPMENT_AND_LAYOUT"
    result["unresolved"]=[k for k,ok in result["checks"].items() if not ok]
    if "remote_column" in result["unresolved"]:
        result["unresolved"]+=remote.get("column",{}).get("unresolved",[])
    result["status"]="HOLD" if result["unresolved"] else "COMPLETE_LAYOUT"
    return result
