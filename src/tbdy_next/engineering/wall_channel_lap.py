"""Check a staggered, full-tension transition from registered through-bars into the bridge curtain."""
from itertools import product
from functools import lru_cache
from math import atan, ceil, cos, floor, hypot, pi, sin, sqrt, tan

from .basement_wall_connection import tension_development
from .basement_wall_pressure import clear_limit
from .wall_regional_shell import regional_shell


def _levels(grid):
    return [grid["first_station_mm"]+i*grid["pitch_mm"] for i in range(grid["layers"])]


def _donors(original, incoming, original_area, incoming_area, lane_gap, radius, maximum):
    """Allocate finite donor area once. Admissible neighbours are ordered intervals in z."""
    remaining=[original_area for _ in original]
    coupled=[]
    for z in incoming:
        needed=incoming_area
        for i,old in enumerate(original):
            if hypot(lane_gap,z-old)-radius>maximum+1.e-8:
                continue
            used=min(remaining[i],needed)
            if used>1.e-8:
                coupled.append({"new_z_mm":z,"old_z_mm":old,"area_mm2":used})
                remaining[i]-=used
                needed-=used
            if needed<=1.e-7:
                break
        if needed>1.e-7:
            return coupled,{"level_mm":z,"missing_area_mm2":needed}
    return coupled,None


def _grid_clear(left,right,offset,radius):
    return min(hypot(offset,a-b)-radius for a in left for b in right)


def _ramp_projection(move,diameter):
    """Two tangent circular bends with a 1:6 straight, measured in the longitudinal direction."""
    angle=atan(1/6)
    radius=7*diameter
    straight=(move-2*radius*(1-cos(angle)))/sin(angle)
    if straight<0:
        raise ValueError("OFFSET_TOO_SMALL_FOR_FULL_TANGENT_BENDS")
    return 2*radius*sin(angle)+straight*cos(angle)


def _crank_fraction(s,run,move,diameter):
    if s<=0:
        return 0.
    if s>=run:
        return 1.
    radius=7*diameter
    angle=atan(1/6)
    arc=radius*sin(angle)
    if s<arc:
        return (radius-sqrt(radius**2-s**2))/move
    if s>run-arc:
        return 1-(radius-sqrt(radius**2-(run-s)**2))/move
    return (radius*(1-cos(angle))+(s-arc)*tan(angle))/move


def _min_count(levels,height):
    starts=[0.,height-1000]+[v+1.e-7 for v in levels if v<height-1000]
    return min(sum(start<=v<=start+1000 for v in levels) for start in starts)


def zoned_column_lap(panel,side,layout,selection,states,coordinates,material,cover,aggregate, *, near_families=()):
    from .wall_membrane_design import SELECTION_LIMIT
    detail=panel["two_way_shell"]["proposed_detail"]
    end=detail["ends"][side]
    old=detail["horizontal"]
    old_d=old["diameter_mm"]
    new_d=layout["web"]["diameter_mm"]
    height=old["physical_height_mm"]
    width=1000*panel["thickness_m"]
    length=1000*panel["clear_length_m"]
    old_track=width/2-cover-old["curtain_inset_mm"]-1.5*old_d
    outer=layout["web_track_mm"]
    radius=(old_d+new_d)/2
    # Clear spacing for full, unsplit development, plus half a millimetre of layout tolerance.
    spacing=max(1.5*new_d,clear_limit(aggregate,old_d,new_d))+.5
    lane_gap=radius+spacing
    lb=tension_development(new_d,material.fyd,material.fck,material.fcd,cover,spacing)
    lap=5*ceil(1.8*lb["position_i_mm"]/5)
    stagger=5*ceil(1.5*lap/5)
    root=coordinates[panel["joint_"+side.lower()]]
    sense=1 if side=="I" else -1
    direction=[sense*v for v in panel["width_direction"]]
    def station(pt):
        return 1000*sum((pt[i]-root[i])*direction[i] for i in (0,1))-end["column_depth_mm"]/2
    # The stiffer original curtain continues unspliced from the adjacent panel. Only one
    # face changes at a time. New bars stay on their selected bridge heights and tracks.
    area_old=pi*old_d**2/4
    area_new=pi*new_d**2/4
    far=end["transfer"]
    dowels=_levels(far)
    max_gap=min(lap/6,100.)
    faces={}
    first_start=5*ceil((far["wall_embedment_mm"]+clear_limit(aggregate,new_d,far["diameter_mm"])+
                       (new_d+far["diameter_mm"])/2)/5)
    for face,suffix,start in ((1,"plus",first_start),(-1,"minus",first_start+stagger)):
        registered=_levels(old.get("opposite_face_levels",old) if face==1 else old)
        route=selection["web_"+suffix]
        zold=registered[1:-1] if route.get("edge_starters_terminate_straight") else registered
        phase=route["phase_mm"]
        pitch=layout["web"]["pitch_mm"]
        new=route.get("installed_levels_mm") or [k*pitch+phase for k in range(-1,ceil(height/pitch)+2)
             if cover+new_d/2<=k*pitch+phase<=height-cover-new_d/2]
        # On the early face the old web stays straight. The new bar bends outward
        # after the lap. On the late face the donor bends inward before its lap.
        old_lane=old_track if face==1 else outer-lane_gap
        new_lane=old_track-lane_gap if face==1 else outer
        moving_d=new_d if face==1 else old_d
        trials=[]
        for shift in ((0,) if face==1 else range(0,33,2)):
            scale=shift/max(abs(z-height/2) for z in zold)
            zlap=[z+(z-height/2)*scale for z in zold]
            if min(zlap[0],height-zlap[-1])-old_d/2<cover:
                continue
            pairs,deficit=_donors(zlap,new,area_old,area_new,lane_gap,radius,max_gap)
            move=hypot(outer-new_lane if face==1 else old_track-old_lane,shift)
            ramp=_ramp_projection(move,moving_d)
            first=start+lap if face==1 else start-ramp
            if first<0 or max(start+lap,first+ramp)>length:
                continue
            # Lower bound throughout the crank. At the early face the elevations are fixed.
            # At the fanned face the far dowels must end before the crank starts.
            far_gap=_grid_clear(zold,dowels,old_track-far["offset_each_side_mm"],(old_d+far["diameter_mm"])/2)
            straight_length=start+lap if face==1 else first
            checks={"donor_full_yield":deficit is None,"far_dowel_clearance":far_gap>=clear_limit(aggregate,old_d,far["diameter_mm"]),
                    "registered_starter_developed":straight_length>=max(end["wall_side_required_mm"],end["position_i_mm"])}
            trials.append({"face":face,"lap_start_mm":start,"lap_end_mm":start+lap,"crank_start_mm":first,
                           "old_lap_track_mm":old_lane,"new_lap_track_mm":new_lane,"cranked_bar":"new" if face==1 else "old",
                           "straight_from_column_face_mm":straight_length,"fan_out_mm":shift,"crank_run_mm":ramp,
                           "maximum_slope":1/6,"minimum_bend_inside_diameter_mm":13*moving_d,
                           "old_levels_mm":zold,"old_lap_levels_mm":zlap,"new_levels_mm":new,
                           "donor_allocations":pairs,"deficit":deficit,"far_dowel_clear_lower_mm":far_gap,
                           "checks":checks,"crank_reaction_per_bar_kn":1.5*pi*moving_d**2/4*material.fyd*sin(atan(1/6))/1000})
            if all(checks.values()):
                break
        if not trials:
            raise ValueError("NO_COVERED_STAGGERED_LAP_FITS")
        faces[face]=trials[-1]
        faces[face]["straight_edge_starters_mm"]=[z for z in registered if z not in zold]
        faces[face]["straight_edge_termination_station_mm"]=faces[face]["crank_start_mm"] if registered!=zold else None
    vdiam,vpitch=16,100.
    from .wall_bar_paths import point_distance
    near_joint=coordinates[panel["joint_"+("j" if side=="I" else "i")]]
    normal=(-panel["width_direction"][1],panel["width_direction"][0])
    def near_clear(s,x):
        near_s=station(near_joint)
        margin=float("inf")
        if near_s-s>1700:
            return margin
        for sign in (-1,1):
            p=tuple((s-near_s)*u+sign*x*v for u,v in zip(direction,normal))
            for family in near_families:
                segments=family["segments"]
                if family["member"]==panel["member"] and family["role"]=="web":
                    segments=segments[1:]  # The straight incoming trace is checked by profile().
                if not segments:
                    continue
                distance=min(point_distance(p,a,b)-e for a,b,e in segments)
                margin=min(margin,distance-(vdiam+family["diameter"])/2-clear_limit(aggregate,vdiam,family["diameter"]))
        return margin
    def profile(row,s):
        on_new=row["cranked_bar"]=="new"
        move=hypot(outer-row["new_lap_track_mm"] if on_new else old_track-row["old_lap_track_mm"],row["fan_out_mm"])
        f=_crank_fraction(s-row["crank_start_mm"],row["crank_run_mm"],move,new_d if on_new else old_d)
        xold=old_track+(row["old_lap_track_mm"]-old_track)*f
        xnew=row["new_lap_track_mm"]+(outer-row["new_lap_track_mm"])*f
        return xold,xnew,f
    stations=ceil(length/vpitch-1.e-9)
    vpitch=length/stations
    @lru_cache(maxsize=None)
    def available(s,x):
        values=[]
        for row in faces.values():
            xo,xn,_=profile(row,s)
            if s<=row["lap_end_mm"]:
                values.append(abs(x-xo)*cos(atan(1/6))-(vdiam+old_d)/2)
            if s>=row["lap_start_mm"]:
                values.append(abs(x-xn)*cos(atan(1/6))-(vdiam+new_d)/2)
        for dx,dia,ds in ((far["offset_each_side_mm"],far["diameter_mm"],max(s-far["wall_embedment_mm"],0)),
                          (layout["dowel_track_mm"],layout["dowel"]["diameter_mm"],
                           max(length-selection["dowel_plus"]["full_straight_tail_mm"]-s,0))):
            values.append(hypot(x-dx,ds)-(vdiam+dia)/2-clear_limit(aggregate,vdiam,dia))
        return min(*values,near_clear(s,x))
    # Mirrored pairs keep the actual verified PMM section biaxially symmetric.
    offsets=[]
    gaps=[]
    for i in range(stations):
        s=min(i+.5,stations-i-.5)*vpitch
        options=[]
        for x in range(floor(width/2-cover-vdiam/2-10),44,-1):
            gap=min(available(s,x),available(length-s,x))
            options.append((x,gap))
            if gap>=0:
                break
        x,gap=max(options,key=lambda item:(item[1]>=0,item[0] if item[1]>=0 else item[1]))
        offsets.append(x)
        gaps.append(gap)
    vtrack=min(offsets)
    @lru_cache(maxsize=None)
    def planes(s):
        choices=[]
        for face in (1,-1):
            row=faces[face]
            face_options=[]
            if s<=row["lap_end_mm"]:
                x,_,f=profile(row,s)
                levels=[u+f*(v-u) for u,v in zip(row["old_levels_mm"],row["old_lap_levels_mm"])]
                area=area_old*(cos(atan(1/6)) if 0<f<1 and row["cranked_bar"]=="old" else 1)
                face_options.append((x,_min_count(levels,height)*area*material.fyd/1000))
            if s>=row["lap_start_mm"]:
                _,x,f=profile(row,s)
                area=area_new*(cos(atan(1/6)) if 0<f<1 and row["cranked_bar"]=="new" else 1)
                face_options.append((x,_min_count(row["new_levels_mm"],height)*area*material.fyd/1000))
            choices.append(face_options)
        vertical=floor(1000/vpitch+1.e-9)*pi*vdiam**2/4*material.fyd/1000
        # Bound every full one-metre vertical strip touching the native station.
        # The support-centre cut projects to the adjacent physical clear-face strip.
        at=max(0.,min(length,s))
        local_v=min(x for i,x in enumerate(offsets) if abs((i+.5)*vpitch-at)<=1000+1.e-7)
        # Each grid must carry the complete field independently throughout a lap.
        # Convex interpolation then includes every intermediate transfer fraction.
        return [[(p[0],n[0],p[1],n[1]),(local_v,local_v,vertical,vertical)] for p,n in product(*choices)]
    # Seal all native corners, including the two support-side half-widths.
    near_side="J" if side=="I" else "I"
    frictions={r["combination"]:r["equivalent_friction_demand_kn_m"] for r in panel["native_support_edges"][near_side]["cuts"]}
    dowel_grid=layout["dowel"]
    dowel_d=dowel_grid["diameter_mm"]
    ld=tension_development(dowel_d,material.fyd,material.fck,material.fcd,cover,dowel_grid["clear_spacing_mm"])["position_i_mm"]
    by_face=[]
    for suffix in ("plus","minus"):
        route=selection["dowel_"+suffix]
        zz=[k*dowel_grid["pitch_mm"]+route["phase_mm"] for k in range(-1,ceil(height/dowel_grid["pitch_mm"])+2)]
        zz=[z for z in zz if cover+dowel_d/2<=z<=height-cover-dowel_d/2]
        by_face.append((_min_count(zz,height)*pi*dowel_d**2/4*material.fyd/1000,route["full_straight_tail_mm"]))
    def residual(name,s):
        if s<length-1.e-7 or name not in frictions:
            return ()
        steel=min(total*min(1.,tail/ld) for total,tail in by_face)
        residual=max(0.,steel-frictions[name]/(1.2*SELECTION_LIMIT))
        return [(f,layout["dowel_track_mm"],residual) for f in (.25,.5,.75,1.)]
    field=regional_shell(states,coordinates,station,planes,width,material,SELECTION_LIMIT,edge_steel=residual)
    field["terminal_dowel_allocation"]={name:{"friction_tie_kn_m_per_face":v/1.2,
        "residual_kn_m_per_face_at_limit":SELECTION_LIMIT*residual(name,length)[-1][2]} for name,v in frictions.items()}
    vertical_detail={"diameter_mm":vdiam,"pitch_mm":vpitch,"minimum_track_mm":vtrack,
                     "offsets_by_station_mm":offsets,"governing_clearance_margin_mm":min(gaps)}
    from .wall_lap_hoops import place_lap_hoops, straight_lap_enclosure
    from .wall_crank_restraint import crank_tie_envelope
    loops=place_lap_hoops(faces,vertical_detail,layout,selection,height,width,cover,aggregate,old_d,new_d)
    enclosure=straight_lap_enclosure(faces,loops,vertical_detail,width,cover,old_d,new_d,aggregate)
    reaction=crank_tie_envelope(faces,old_track,outer,dims=(old_d,new_d,material.fyd,height,width,cover))
    return {"basis":"STAGGERED_UNSPLICED_COLUMN_BARS_TO_STRAIGHT_BRIDGE_STARTERS",
            "clear_length_mm":length,"old_track_mm":old_track,"new_track_mm":outer,
            "lap_separation_mm":spacing,"development":lb,"full_tension_lap_mm":lap,
            "centre_stagger_mm":stagger,"vertical":vertical_detail,"lap_confinement":loops,
            "straight_lap_enclosure":enclosure,"crank_tie_equilibrium":reaction,
            "cover_mm":cover,"registered_column_passage":end.get("anchorage_type")=="UNSPLICED_THROUGH_COLUMN"
                and end.get("layout_status")=="PROPOSED_PRESSURE_BARS_FIT",
            "faces":{str(k):v for k,v in faces.items()},"regional_shell":field}
