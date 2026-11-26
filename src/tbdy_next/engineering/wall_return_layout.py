"""Coordinate developed horizontal bars inside two monolithic return curtains."""
from itertools import product
from math import hypot

from .basement_joint_layout import _families, _segments, _closest_levels, layout_policy, level_grid
from .basement_wall_connection import wall_return_anchor
from .basement_wall_pressure import clear_limit
from .wall_bar_paths import point_distance, segment_distance


def vertical_margin(bar,panel,side,end,aggregate):
    """Shortest distance to an actual receiving vertical bar anywhere along the return."""
    if bar["member"]==panel["member"] and (bar["role"]=="web" or panel.get("shared_web_tracks")):
        return float("inf")
    h,v = panel["horizontal"],panel["vertical"]
    dx,dy = panel["width_direction"]
    step = 1 if side=="I" else -1
    track = panel["thickness_m"]*500-h["cover_mm"]-h["curtain_inset_mm"]-2*h["diameter_mm"]-v["diameter_mm"]/2
    track = v.get("track_mm",track)
    minimum = clear_limit(aggregate,v["diameter_mm"],bar["diameter"])
    radius = (bar["diameter"]+v["diameter_mm"])/2
    bounds=bar["bounds"]
    margin=float("inf")
    tie_dia=v.get("crosstie_diameter_mm",h["diameter_mm"])
    z=[h["first_station_mm"]+j*h["pitch_mm"] for j in range(h["layers"])]
    dz=_closest_levels(bar["heights"],z)[0]
    tie_radii=(bar["diameter"]+tie_dia)/2
    for i in range(v["stations_per_face"]):
        along=step*(end["column_depth_mm"]/2+(i+.5)*v["pitch_mm"])
        if dz<=tie_radii and not panel.get("dimensioned_corner_crossties"):
            # Reserve the whole plan envelope of both 135-degree hooks at this level.
            # Their inward tails and mandrels fit inside this rectangle.
            reach=3.5*tie_dia+max(10*tie_dia,80.)
            tl=track+(tie_dia+v["diameter_mm"])/2
            xy=[((along+d)*dx-f*dy,(along+d)*dy+f*dx) for d in (-reach,reach) for f in (-tl,tl)]
            xs,ys=zip(*xy)
            sep=hypot(max(0.,bounds[0]-max(xs),min(xs)-bounds[1]),max(0.,bounds[2]-max(ys),min(ys)-bounds[3]),dz)
            margin=min(margin,sep-tie_radii)
        for face in (-1,1):
            x,y=along*dx-face*track*dy,along*dy+face*track*dx
            bound=hypot(max(0.,bounds[0]-x,x-bounds[1]),max(0.,bounds[2]-y,y-bounds[3]))-radius-minimum
            if bound>0:
                continue
            margin=min(margin,min(point_distance((x,y),p,q)-err for p,q,err in _segments(bar))-radius-minimum)
    return margin


def _fits(a,b,aggregate):
    # Broad-phase each chord before computing its geometric distance.
    dz=float("inf") if not a["heights"] or not b["heights"] else _closest_levels(a["heights"],b["heights"])[0]
    radii=(a["diameter"]+b["diameter"])/2
    limit=clear_limit(aggregate,a["diameter"],b["diameter"])
    if dz>=radii+limit:
        return True
    for f in (a,b):
        if "_lines" not in f:
            f["_lines"]=[(p,q,err,min(p[0],q[0]),max(p[0],q[0]),min(p[1],q[1]),max(p[1],q[1]),
                         q[0]-p[0],q[1]-p[1],hypot(q[0]-p[0],q[1]-p[1])) for p,q,err in _segments(f)]
    for p,q,ea,l,r,s,t,x,y,length in a["_lines"]:
        for u,v,eb,i,j,k,h,dx,dy,long in b["_lines"]:
            parallel=abs(x*dx+y*dy)>=.98078528040*length*long
            target=radii+(limit if parallel else 0.)
            if dz>target or hypot(max(0,l-j,i-r),max(0,s-h,k-t),dz)>target+ea+eb:
                continue
            gap=hypot(max(0.,segment_distance(p,q,u,v)-ea-eb),dz)
            if (parallel and gap<target-1e-8) or (not parallel and gap<=target):
                return False
    return True


def coordinate_return_tracks(geometry,designs,mat,aggregate):
    from collections import defaultdict
    by_joint=defaultdict(list)
    for panel in geometry["panels"]:
        design=designs.get(panel["member"],{})
        for side,end in design.get("ends",{}).items():
            if end.get("joint"):
                by_joint[end["joint"]].append(({**panel,"horizontal":design["horizontal"],"vertical":design["vertical"]},side,end))
    for incident in by_joint.values():
        present={p["member"] for p,_,_ in incident}
        if len(incident)!=2 or any(e["status"]!="CONDITIONAL_PRESSURE_END_DESIGN" or set(e["incident_walls"])!=present-{p["member"]}
                                  for p,_,e in incident):
            continue
        original=[end["transfer"] for _,_,end in incident]
        choices=[]
        for (p,_,end),bars in zip(incident,original):
            policy=layout_policy(geometry,p,p["horizontal"]["cover_mm"],aggregate)
            eligible={}
            for phase in (0.,.5,1.,1.5,.25,.75,1.25,1.75):
                grid=level_grid({**policy,"dowel_phase":phase},bars["diameter_mm"],bars["maximum_pitch_mm"],end["end_cover_mm"],dowel=True)
                if grid and grid["minimum_in_any_full_metre"]>=bars["guaranteed_bars_per_m"] and grid["clear_spacing_mm"]>=1.5*bars["diameter_mm"]:
                    candidate={**bars,**grid,"guaranteed_bars_per_m":bars["guaranteed_bars_per_m"]}
                    eligible[grid["pitch_mm"],round(grid["first_station_mm"],6)]=candidate
            choices.append(sorted(eligible.values(),key=lambda d:-d["pitch_mm"]))
        # Try wider valid dowel spacings first. Each grid retains the designed steel in every full metre.
        trials=list(product(*choices))
        def separation(trial):
            return (sum(t["pitch_mm"] for t in trial),abs(trial[0]["first_station_mm"]-trial[1]["first_station_mm"]))
        trials.sort(key=separation,reverse=True)
        for grid_pair in [original,*trials]:
            for (_,_,end),bars in zip(incident,grid_pair):
                end["transfer"]={**bars,"anchor":dict(bars["anchor"])}
            if _coordinate_corner(incident,mat,aggregate):
                break
        else:
            for (_,_,end),bars in zip(incident,original):
                end["transfer"]=bars


def _coordinate_corner(incident,mat,aggregate, *, census=None, bend_factors=(3.5,)):
    options={}
    for index,(p,side,end) in enumerate(incident):
        for role in ("web","dowel"):
            h=p["horizontal"]
            dowel=end["transfer"]
            d=h if role=="web" else dowel
            anchor=end if role=="web" else dowel.get("anchor",{})
            if anchor.get("return_shape")!="CONTINUOUS_90_FULL_DEVELOPMENT_IN_RETURN":
                return
            offset=(500*p["thickness_m"]-h["cover_mm"]-h["curtain_inset_mm"]-1.5*d["diameter_mm"]
                    if role=="web" else dowel["offset_each_side_mm"])
            profile=p["support_sections"][side]
            # Explicit transverse coordinates at 5-mm increments. No cover or bar area changes.
            for face in (-1,1):
                key=(index,role,face)
                options[key]=[]
                minimum=(clear_limit(aggregate,d["diameter_mm"])+d["diameter_mm"])/2
                entries=[offset]
                if role=="dowel" and not p.get("shared_web_tracks"):
                    entries.extend(v for v in (60.,minimum+1.) if minimum<=v<offset-1e-6)
                for entry in entries:
                    lanes=sorted(range(-145,146,5),key=lambda t:abs(t-(60 if face>0 else -60)))
                    for factor,lane in product(bend_factors,lanes):
                        updated=wall_return_anchor(profile,p,side,d["diameter_mm"],entry,h["cover_mm"],
                                 d.get("neighbour_clear_mm",d["pitch_mm"]-d["diameter_mm"]),mat,aggregate,
                                 face_lanes={face:lane,-face:-lane},continuous_leg=bool(p.get("shared_web_tracks")),
                                 bend_factor=factor,selected_face=face if census is not None else None)
                        if not updated["fits_column"]:
                            continue
                        trial={**end,**updated} if role=="web" else {**end,"transfer":{**dowel,"offset_each_side_mm":entry,"anchor":updated}}
                        bar=next(f for f in _families(p,side,trial) if f["role"]==role and f["face"]==face)
                        if all(vertical_margin(bar,other,s,e,aggregate)>=-1e-8 for other,s,e in incident):
                            options[key].append(((entry,lane,factor),bar,next(row for row in updated["bar_paths"] if row["face"]==face)))
                if census is not None:
                    census[f"{p['member']}:{role}:{face}"] = len(options[key])
                if not options[key]:
                    return
    # Forward checking rejects an offset as soon as a remaining bar has no feasible route.
    cache={}
    def compatible(k,a,l,b):
        if k[:2]==l[:2] and a[0][0]!=b[0][0]:
            return False
        key=(k,a[0],l,b[0])
        if key not in cache:
            cache[key]=_fits(a[1],b[1],aggregate)
        return cache[key]
    def search(domains,assigned):
        if not domains:
            return assigned
        key=min(domains,key=lambda k:len(domains[k]))
        for choice in domains[key]:
            remaining={l:[b for b in opts if compatible(key,choice,l,b)] for l,opts in domains.items() if l!=key}
            if all(remaining.values()):
                answer=search(remaining,{**assigned,key:choice})
                if answer:
                    return answer
        return None
    solution=search(options,{})
    if solution:
        for i,(_,_,end) in enumerate(incident):
            for role,anchor in (("web",end),("dowel",end["transfer"]["anchor"])):
                chosen=[solution[i,role,f] for f in (-1,1)]
                anchor["bar_paths"]=[row[2] for row in chosen]
                if census is not None:
                    anchor["inside_diameters_by_face_mm"]=[(2*row[0][2]-1)*row[1]["diameter"] for row in chosen]
                anchor["receiving_track_coordinates_mm"]=[row[0][1] for row in chosen]
                diameter=chosen[0][1]["diameter"]
                projection=anchor["column_depth_mm"]/2+max(row[0][1] for row in chosen)+diameter/2
                anchor.update(specified_embedment_mm=projection,margin_mm=anchor["column_available_mm"]-projection)
                if role=="dowel":
                    end["transfer"].update(column_embedment_mm=projection,offset_each_side_mm=chosen[0][0][0])
        return True
    return False
