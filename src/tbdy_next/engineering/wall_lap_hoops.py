"""Dimension the normal-plane confinement loops around a finite wall lap."""
from math import ceil, cos, floor, hypot, pi, sin, sqrt

from .wall_bar_paths import point_distance


def hoop_path(left, right, bottom, top, diameter, flip_x, flip_z):
    """A rectangular loop with two inward 135 degree tails at one corner.

    The hooks occupy adjoining longitudinal planes. The path returns to the
    second plane along the remote long leg. All dimensions are bar centrelines.
    """
    radius = 3.5 * diameter
    if min(right-left, top-bottom) < 2*radius:
        return []
    tail = max(80., 10*diameter)
    chords = []
    def arc(x, z, start, stop):
        count = ceil((stop-start)/7.5)
        for i in range(count+1):
            a = (start+(stop-start)*i/count)*pi/180
            chords.append((x+radius*cos(a),z+radius*sin(a)))
    arc(left+radius,bottom+radius,135,270)
    arc(right-radius,bottom+radius,270,360)
    arc(right-radius,top-radius,0,90)
    arc(left+radius,top-radius,90,180)
    arc(left+radius,bottom+radius,180,315)
    direction = 2**-.5
    x,z=chords[0]
    chords.insert(0,(x+tail*direction,z+tail*direction))
    x,z=chords[-1]
    chords.append((x+tail*direction,z+tail*direction))
    return [(left+right-x if flip_x else x, bottom+top-z if flip_z else z) for x,z in chords]


def group_loop(levels, donors, bars, old_lane, new_lane, width, height, cover, diameter, verticals=()):
    """Search covered rounded loops. Every allocated donor and incoming rod is enclosed."""
    xmin,xmax=sorted((old_lane,new_lane))
    zmin,zmax=min(*levels,*donors),max(*levels,*donors)
    targets=[(x,z,d) for x,z,d in bars if (x==old_lane and z in donors) or (x==new_lane and z in levels)]
    largest=max(d for _,_,d in targets)
    nearby=[(x,z,d) for x,z,d in bars if xmin-120<=x<=xmax+120 and zmin-150<=z<=zmax+150]
    error=3.5*diameter*(1-cos(pi/48))
    loops=0
    best=None
    for inner,outer in ((4,4),(12,4),(20,4),(36,4),(52,4),(60,4),(68,4),(76,4),
                        (4,3),(12,3),(20,3),(36,3),(52,3),(60,3),(68,3),(76,3)):
        left=xmin-(diameter+largest)/2-(inner if xmin>0 else outer)
        right=xmax+(diameter+largest)/2+(outer if xmin>0 else inner)
        if max(abs(left),abs(right))+diameter/2>width/2-cover:
            continue
        if verticals and any(min(abs(x-left),abs(x-right))<required for x,required in verticals):
            continue
        for lo in (0,2,4,6,8,10,12,14,16,18,20,22,24):
            for hi in (0,2,4,6,8,10,12,14,16,18,20,22,24):
                bottom=zmin-(diameter+largest)/2-2-lo
                top=zmax+(diameter+largest)/2+2+hi
                if bottom-diameter/2<cover or top+diameter/2>height-cover:
                    continue
                radius=3.5*diameter
                if any(hypot(max(left+radius-x,x-right+radius,0.),
                             max(bottom+radius-z,z-top+radius,0.))>radius-(d+diameter)/2+1.e-8
                       for x,z,d in targets):
                    continue
                for flip_x,flip_z in ((False,False),(True,False),(False,True),(True,True)):
                    shape=hoop_path(left,right,bottom,top,diameter,flip_x,flip_z)
                    if not shape:
                        continue
                    if any(abs(x)+diameter/2>width/2-cover or
                           not cover+diameter/2<=z<=height-cover-diameter/2 for x,z in shape):
                        continue
                    loops+=1
                    margin=float("inf")
                    for p,q in zip(shape,shape[1:]):
                        for x,z,d in nearby:
                            if not (min(p[1],q[1])-22<=z<=max(p[1],q[1])+22 and
                                    min(p[0],q[0])-22<=x<=max(p[0],q[0])+22):
                                continue
                            margin=min(margin,point_distance((x,z),p,q)-error-(d+diameter)/2)
                        if margin<0:
                            break
                    if best is None or margin>best:
                        best=margin
                    if margin>=0:
                        return {"shape":[left,right,bottom,top,flip_x,flip_z],"diameter_mm":diameter,
                                "nonintersection_lower_mm":min(margin,1.),"tested":loops}
    return {"shape":None,"tested":loops,"best_rejected_margin_mm":best}


def lap_hoop_census(row, other_bars, width, height, cover, old_d, new_d, *, verticals=()):
    sign=row["face"]
    old=sign*row["old_lap_track_mm"]
    new=sign*row["new_lap_track_mm"]
    levels=row["new_levels_mm"]
    bars=[(old,z,old_d) for z in row["old_lap_levels_mm"]]+[(new,z,new_d) for z in levels]+list(other_bars)
    donors={z:[] for z in levels}
    for pair in row["donor_allocations"]:
        donors[pair["new_z_mm"]].append(pair["old_z_mm"])
    # Group up to four neighbouring laps inside each closed stirrup. A path through
    # all actual levels must exist, including the first and last covered groups.
    reachable={0:[]}
    failed=[]
    diameter=max(8.,ceil(new_d/3))
    for start in range(len(levels)):
        if start not in reachable:
            continue
        for end in range(min(start+4,len(levels)),start,-1):
            if end in reachable:
                continue
            band=levels[start:end]
            group=sorted({v for z in band for v in donors[z]})
            if not group:
                continue
            trial=group_loop(band,group,bars,old,new,width,height,cover,diameter,verticals)
            summary={"first_new_z_mm":band[0],"last_new_z_mm":band[-1],**trial}
            if trial["shape"]:
                reachable[end]=[*reachable[start],summary]
                if end==len(levels):
                    return {"cross_sections_fit":True,"groups":reachable[end],"failures":failed}
            else:
                failed.append(summary)
    return {"cross_sections_fit":False,"retained_levels":max(reachable),"required_levels":len(levels),
            "failures":failed,"groups":reachable[max(reachable)]}


def place_lap_hoops(faces, vertical, layout, selection, height, width, cover, aggregate, old_d, new_d):
    from .basement_wall_pressure import clear_limit
    out={}
    for sign,row in faces.items():
        tie=max(8.,ceil(new_d/3))
        bay=vertical["pitch_mm"]
        spacing_limit=min(200.,width/4)
        # Adjacent height bands use stations one half-bay apart. The terminating
        # hook is one diameter plus 2 mm away from its overlapping closing leg.
        half_offset=(tie+2.)/2
        half_space=bay/4-half_offset
        radius=(tie+vertical["diameter_mm"])/2
        clear=clear_limit(aggregate,tie,vertical["diameter_mm"])
        side=sqrt(max(0.,(radius+clear)**2-half_space**2))+3.5*tie*(1-cos(pi/12))
        tracks={x for i,x in enumerate(vertical["offsets_by_station_mm"]) if
                row["lap_start_mm"]-bay<=(i+.5)*bay<=row["lap_end_mm"]+bay}
        other=[]
        peer=faces[-sign]
        if row["lap_start_mm"]<peer["lap_start_mm"]:
            other.extend(((-sign)*peer["old_lap_track_mm"] if peer["cranked_bar"]=="new" else
                          (-sign)*faces[1]["old_lap_track_mm"],z,old_d) for z in peer["old_levels_mm"])
        else:
            other.extend((-sign*layout["web_track_mm"],z,new_d) for z in peer["new_levels_mm"])
        for face,suffix in ((-1,"minus"),(1,"plus")):
            route=selection["dowel_"+suffix]
            phase=route["phase_mm"]
            pitch=layout["dowel"]["pitch_mm"]
            if row["lap_end_mm"]>=vertical["pitch_mm"]*len(vertical["offsets_by_station_mm"])-route["full_straight_tail_mm"]:
                other.extend((face*layout["dowel_track_mm"],k*pitch+phase,layout["dowel"]["diameter_mm"])
                             for k in range(-1,ceil(height/pitch)+2) if 0<=k*pitch+phase<=height)
        cage=lap_hoop_census(row,other,width,height,cover,old_d,new_d,
                            verticals=[(face*x,side) for x in tracks for face in (-1,1)])
        ok=cage["cross_sections_fit"] and half_space>=radius and bay<=spacing_limit+1.e-7
        layers=[]
        for i,g in enumerate(cage["groups"]):
            phase=(.25+.5*(i%2))*bay
            positions=[phase+k*bay for k in range(ceil((row["lap_start_mm"]+half_offset-phase)/bay),
                       floor((row["lap_end_mm"]-half_offset-phase)/bay)+1)]
            ok=ok and len(positions)>=6 and max(positions[0]-row["lap_start_mm"],
                                                  row["lap_end_mm"]-positions[-1])+half_offset<=spacing_limit+1.e-7
            layers.append({"band":i,"stations_mm":positions})
        # Disjoint station planes shield unlike phases. For equal phases use
        # the full occupied height interval (including curved corners and tails).
        for i,a in enumerate(cage["groups"]):
            for j,b in enumerate(cage["groups"][:i]):
                gap=(a["shape"][2]-b["shape"][3]) if (i-j)%2==0 else bay/2-2*half_offset
                ok=ok and gap-tie>=clear-1.e-8
        out[str(sign)]={**cage,"stations":layers,"pitch_mm":bay,"hook_plane_separation_mm":2*half_offset,
            "minimum_required_loop_count":6,"maximum_pitch_mm":spacing_limit,"satisfied":bool(ok)}
    return out


def straight_lap_enclosure(faces, loops, vertical, width, cover, old_d, new_d, aggregate):
    """TBDY 7.6.4, straight lap ends inside the longitudinal web reinforcement.

    Test the installed bars. For supplementary outside bars, report necessary
    cover and parallel-clearance bounds across the actual staggered loop planes.
    """
    from .basement_wall_pressure import clear_limit
    results={}
    for sign,row in faces.items():
        start,stop=row["lap_start_mm"],row["lap_end_mm"]
        outer=max(row["old_lap_track_mm"]+old_d/2,row["new_lap_track_mm"]+new_d/2)
        dia=vertical["diameter_mm"]
        installed=[(i+.5)*vertical["pitch_mm"] for i,x in enumerate(vertical["offsets_by_station_mm"])
                   if start<=(i+.5)*vertical["pitch_mm"]<=stop and x-dia/2>=outer-1.e-8]
        gaps=[b-a for a,b in zip([start,*installed],[*installed,stop])]
        cage=loops[str(sign)]
        rails=[]
        for group,bank in zip(cage["groups"],cage["stations"],strict=True):
            left,right,bottom,top,*_=group["shape"]
            tie=group["diameter_mm"]
            if top-bottom<=7*tie:
                continue
            track=max(abs(left),abs(right))
            rails.extend((s,track,tie) for s in bank["stations_mm"])
        banks=sorted(set(s for s,_,_ in rails))
        largest_gap=max((b-a for a,b in zip(banks,banks[1:])),default=None)
        half_plane=cage["hook_plane_separation_mm"]/2
        catalog=[]
        for d in (8,10,12,14,16,18,20,22,24,25):
            low=outer+d/2
            high=width/2-cover-d/2
            bound=None
            if low<=high and largest_gap is not None:
                worst_track=max(max(abs(high-x),abs(low-x)) for _,x,_ in rails)
                # Any full-height vertical between adjacent outer rails must pass
                # at least one of their upright segments at this distance or less.
                bound=hypot(largest_gap/2+half_plane,worst_track)-(d+min(t for _,_,t in rails))/2
            catalog.append({"diameter_mm":d,"outside_centre_min_mm":low,"covered_centre_max_mm":high,
                            "interior_surface_clear_upper_mm":bound,"required_parallel_clear_mm":
                            clear_limit(aggregate,d,cage["groups"][0]["diameter_mm"]) if rails else None})
        results[str(sign)]={"outer_horizontal_surface_mm":outer,"installed_outside_verticals":len(installed),
                        "largest_unenclosed_interval_mm":max(gaps),"minimum_count":6,"maximum_pitch_mm":200.,
                        "largest_interior_rail_gap_mm":largest_gap,"interior_interval_mm":[banks[0],banks[-1]] if banks else [],
                        "supplementary_vertical_trials":catalog,"satisfied":len(installed)>=6 and max(gaps)<=200.+1.e-7}
    return results
