"""Verify continuations at the two ends remote from the short receiving link."""
from copy import deepcopy
from math import ceil, floor, hypot, sqrt

from .basement_joint_layout import _closest_levels, _families, _separation
from .basement_wall_connection import tension_development, wall_return_anchor
from .basement_wall_pressure import clear_limit
from .wall_return_layout import _coordinate_corner


def corner_end(straight, side, neighbours, designs, layout, vertical, mat, cover, aggregate, spacing, *, crossing=()):
    # No peer detail is changed unless an entire admissible alternative has been selected.
    end = straight["support_sections"][side]
    joint = end["joint"]
    other, = [p for p in neighbours.values() if p["member"]!=straight["member"] and joint in (p["joint_i"],p["joint_j"])]
    peer = designs[other["member"]]
    ps = "I" if other["joint_i"]==joint else "J"
    obj={**straight,"shared_web_tracks":True,"vertical":vertical,"dimensioned_corner_crossties":True}
    grids={k:{**layout[k],"neighbour_clear_mm":spacing} for k in ("web","dowel")}
    offset=layout["web_track_mm"]
    obj["horizontal"]={**grids["web"],"cover_mm":cover,
                       "curtain_inset_mm":straight["thickness_m"]*500-cover-1.5*grids["web"]["diameter_mm"]-offset}
    anchors={k:wall_return_anchor(end,straight,side,g["diameter_mm"],offset,cover,spacing,mat,aggregate,
                                  continuous_leg=True) for k,g in grids.items()}
    detail={**anchors["web"],"transfer":{**grids["dowel"],"column_embedment_mm":anchors["dowel"]["specified_embedment_mm"],
        "wall_embedment_mm":straight["clear_length_m"]*1000,"offset_each_side_mm":offset,"anchor":anchors["dowel"]}}
    pd=deepcopy(peer["ends"][ps])
    op={**other,"horizontal":peer["horizontal"],"vertical":peer["vertical"],"dimensioned_corner_crossties":True}
    incident=[(obj,side,detail),(op,ps,pd)]
    census={}
    complete=all(a["fits_column"] for a in anchors.values()) and bool(_coordinate_corner(incident,mat,aggregate,census=census,bend_factors=(3.5,5.,7.,9.)))
    receipt={"joint":joint,"peer":other["member"],"checked_end_tracks":census,"geometric_development":{
        role:{"required_mm":a["position_i_mm"],"available_mm":a["wall_side_available_mm"],
              "receiving_members":a["receiving_members"]} for role,a in anchors.items()},"complete_corner":complete}
    families=[]
    if complete:
        for p,s,e in incident:
            families.extend(_families(p,s,e))
        from .wall_bridge_layout import _translated
        from .wall_channel_ties import link_ties, tie_families
        far="J" if ps=="I" else "I"
        far_j=other["joint_"+far.lower()]
        step=1 if ps=="I" else -1
        dist=other["span_m"]*1000*step
        tx,ty=[dist*x for x in other["width_direction"]]
        extra=[]
        for p in neighbours.values():
            for si in ("I","J"):
                if p["joint_"+si.lower()]!=far_j or p["member"] not in designs:
                    continue
                dd=designs[p["member"]]
                if not dd.get("ends",{}).get(si):
                    continue
                bars=_families({**p,"horizontal":dd["horizontal"]},si,dd["ends"][si])
                extra.extend(_translated(f,tx,ty) for f in bars)
        all_bars=families+extra+list(crossing)
        ties={}
        for p,s,end_detail in incident:
            h,v=p["horizontal"],p["vertical"]
            dia=v["diameter_mm"]
            own=sorted((f for f in all_bars if f["member"]==p["member"]),key=lambda f:f["role"])
            direction=tuple(x*(1 if s=="J" else -1) for x in p["width_direction"])
            normal=(-direction[1],direction[0])
            track=v.get("track_mm",p["thickness_m"]*500-h["cover_mm"]-h["curtain_inset_mm"]-2*h["diameter_mm"]-dia/2)
            origin=tuple(-x*end_detail["column_depth_mm"]/2 for x in direction)
            length=p["clear_length_m"]*1000
            station_count=v["stations_per_face"]
            vertices=[(tuple(origin[k]+(-length+(i+.5)*length/station_count)*direction[k]+f*track*normal[k]
                             for k in (0,1)),dia) for i in range(station_count) for f in (-1,1)]
            trials={}
            roles=("web","dowel") if p.get("shared_web_tracks") else ("web",)
            for tie_diameter in ((12,14,16,18) if p.get("shared_web_tracks") else (12,)):
                for role in roles:
                    tie=link_ties(all_bars,own,vertices,direction,normal,length,1000*p["thickness_m"],
                                  peer["horizontal"]["physical_height_mm"],track,dia,cover,aggregate,
                                  grid_role=role,member=p["member"]+"_crossties",origin=origin,
                                  contact_diameter=max(h["diameter_mm"],dia),tie_diameter=tie_diameter)
                    trials[f"{role}_{tie_diameter}"]=tie
                    if tie["satisfied"]:
                        break
                if tie["satisfied"]:
                    break
            ties[p["member"]]={**tie,"attachment_grid":role,"trial_counts":{k:v.get("admissible_paths_by_station") for k,v in trials.items()}}
            installed=list(tie_families(p["member"]+"_crossties",tie))
            all_bars.extend(installed)
            families.extend(installed)
        receipt["crosstie_paths"]=ties
        receipt["complete_corner"]=all(q["satisfied"] for q in ties.values())
        receipt["selected_paths"]=[{"member":p["member"],"side":s,"web":e["bar_paths"],
                                    "dowel":e["transfer"]["anchor"]["bar_paths"]} for p,s,e in incident]
    return receipt, families


def _maximum_translation_gap(pitch, original):
    # Rows in the central strip stay inside the finite wall for an entire pitch of translation.
    low, high = original[0]+pitch, original[-1]-pitch
    residues=sorted({(k*pitch-original[0])%(original[1]-original[0]) for k in range(ceil(low/pitch),floor(high/pitch)+1)})
    if not residues:
        raise ValueError("LAP_HAS_NO_FULL_INTERIOR_GRID")
    spacing=original[1]-original[0]
    return max(b-a for a,b in zip(residues,residues[1:]+[residues[0]+spacing]))/2


def column_end(turn,side,layout,selection,material,cover,aggregate,states):
    existing=turn["two_way_shell"]["proposed_detail"]
    old=existing["horizontal"]
    end=existing["ends"][side]
    available=end["column_available_mm"]
    old_track=turn["thickness_m"]*500-old["cover_mm"]-old["curtain_inset_mm"]-1.5*old["diameter_mm"]
    data={}
    for role in ("web","dowel"):
        grid=layout[role]
        dia=grid["diameter_mm"]
        lb=tension_development(dia,material.fyd,material.fck,material.fcd,cover,grid["clear_spacing_mm"])["position_i_mm"]
        projection=5*ceil(.75*lb/5)
        row={"diameter_mm":dia,"required_hook_projection_mm":projection,"available_projection_mm":available,
             "projection_fits":projection<=available,"wall_development_mm":lb}
        if role=="web":
            # Alternative lap onto the existing, continuous column bars. Check closest full-height
            # pair on both faces. A geometrically intersecting pair cannot be used as a lap.
            faces=[]
            for face,suffix in ((-1,"minus"),(1,"plus")):
                chosen=selection.get("web_"+suffix)
                if not chosen:
                    continue
                original=old.get("opposite_face_levels",old) if face==1 else old
                zz=[original["first_station_mm"]+i*original["pitch_mm"] for i in range(original["layers"])]
                phase=chosen["phase_mm"]
                pitch=grid["pitch_mm"]
                height=old["physical_height_mm"]
                levels=grid.get("fixed_levels_by_face",{}).get(face)
                if levels is None:
                    levels=[k*pitch+phase for k in range(-1,ceil(height/pitch)+2)
                            if cover+dia/2<=k*pitch+phase<=height-cover-dia/2]
                dz,a,b=_closest_levels(zz,levels)
                dx=abs(layout["web_track_mm"]-old_track)
                faces.append({"face":face,"track_separation_mm":dx,"closest_levels_mm":[a,b],
                              "identical_levels":len(levels)==len(zz) and all(abs(s-t)<1.e-7 for s,t in zip(levels,zz)),
                              "surface_clear_mm":hypot(dx,dz)-(dia+old["diameter_mm"])/2})
            if faces:
                upper_z=_maximum_translation_gap(pitch,zz)
                clear=clear_limit(aggregate,dia,old["diameter_mm"])
                radius=(dia+old["diameter_mm"])/2
                needed=sqrt(max(0.,(clear+radius)**2-upper_z**2))
                inner=floor(old_track-needed)
                row["rephased_lap"]={"maximum_nearest_level_distance_mm":upper_z,
                    "best_possible_surface_clear_upper_mm":hypot(dx,upper_z)-radius,
                    "required_track_separation_mm":needed,"nearest_inner_track_mm":inner}
            required_clear=clear_limit(aggregate,dia,old["diameter_mm"])
            at_clear=tension_development(dia,material.fyd,material.fck,material.fcd,cover,required_clear)["position_i_mm"]
            row["lap"]={"existing_diameter_mm":old["diameter_mm"],"existing_track_mm":old_track,
                        "new_track_mm":layout["web_track_mm"],"full_tension_lap_at_clear_limit_mm":1.8*at_clear,
                        "full_tension_lap_at_unsplit_spacing_mm":1.8*lb,
                        "two_staggered_groups_extent_at_clear_limit_mm":2.5*1.8*at_clear,
                        "wall_clear_length_mm":turn["clear_length_m"]*1000,
                        "required_parallel_clear_mm":clear_limit(aggregate,dia,old["diameter_mm"]),
                        "faces":faces}
        data[role]=row
    unresolved=[]
    # Only an already registered matching cage can carry its remote physical layout approval.
    matches=(data["web"]["diameter_mm"]==old["diameter_mm"] and abs(layout["web_track_mm"]-old_track)<1.e-7
             and len(data["web"]["lap"]["faces"])==2
             and all(row["identical_levels"] for row in data["web"]["lap"]["faces"])
             and end.get("anchorage_type")=="UNSPLICED_THROUGH_COLUMN")
    if not matches and not data["web"]["projection_fits"]:
        unresolved.append("FULL_YIELD_STANDARD_HOOK_PROJECTION")
    if not matches and any(f["surface_clear_mm"]<data["web"]["lap"]["required_parallel_clear_mm"]
                           for f in data["web"]["lap"]["faces"]):
        unresolved.append("BRIDGE_STARTERS_AND_EXISTING_THROUGH_RODS_INTERFERE")
    if not (matches and end["status"]=="CONDITIONAL_PRESSURE_END_DESIGN"
            and end.get("layout_status")=="PROPOSED_PRESSURE_BARS_FIT"):
        unresolved.append("REMOTE_CAGE_CONTINUITY_REQUIRES_VERIFIED_PATH")
    return {"joint":turn["joint_"+side.lower()],"column":end["column"],"details":data,"unresolved":unresolved,
            "status":"HOLD" if unresolved else "VERIFIED_DEVELOPMENT_AND_LAYOUT"}


def column_hook_options(profile,panel,side,material,cover,aggregate):
    """Intersect the actual column entry lanes with cover. Evaluate quarter bends inside the far hoop."""
    from .basement_wall_connection import _hook_90
    from .wall_bridge_trial import corridors
    width=1000*panel["thickness_m"]
    available=profile["depth_mm"]-max(cover,profile["cover"])-profile["tie"]
    result=[]
    for diameter in (12,14,16,18,20,22,24,25):
        clearance=clear_limit(aggregate,diameter,profile["bar_diameter"])
        # This is the favourable unsplit length. A crowded lap requires a longer bar.
        bond=tension_development(diameter,material.fyd,material.fck,material.fcd,cover,2*diameter)["position_i_mm"]
        projection=5*ceil(.75*bond/5)
        intervals=corridors([(x,profile["bar_diameter"]) for x in profile["bar_offsets"]],0.,
                            width/2-cover-diameter/2,diameter,aggregate)
        choices=[]
        if projection<=available:
            for low,high in intervals:
                tracks=sorted({low,high,(low+high)/2,*range(ceil(low),floor(high)+1)})
                for offset in tracks:
                    path=_hook_90(profile,side,offset,diameter,bond,available,clearance)
                    if path:
                        choices.append({"track_mm":offset,"hook":path})
        result.append({"diameter_mm":diameter,"minimum_projection_mm":projection,"available_mm":available,
                       "entry_intervals_mm":intervals,"admissible_sampled_hooks":choices})
    return result
