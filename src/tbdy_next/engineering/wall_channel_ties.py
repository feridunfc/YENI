"""Finite special crossties for the two curtains in the short transfer panel."""
from bisect import bisect_left, bisect_right
from itertools import product
from math import cos, hypot, pi, sin, sqrt

from .basement_wall_pressure import clear_limit

from .basement_joint_layout import _closest_levels, _segments, _separation
from .wall_bar_paths import point_distance, segment_distance


def _vertical_threshold(first,second,aggregate):
    """Required elevation separation of two finite planar bar paths in mm."""
    radius=(first["diameter"]+second["diameter"])/2
    clear=clear_limit(aggregate,first["diameter"],second["diameter"])
    worst=0.
    for a,b,ea in _segments(first):
        vx,vy=b[0]-a[0],b[1]-a[1]
        for c,d,eb in _segments(second):
            wx,wy=d[0]-c[0],d[1]-c[1]
            aligned=abs(vx*wx+vy*wy)>=.98078528040*hypot(vx,vy)*hypot(wx,wy)
            limit=radius+(clear if aligned else 1.e-7)
            planar=max(0.,segment_distance(a,b,c,d)-ea-eb)
            if planar<limit:
                worst=max(worst,sqrt(limit**2-planar**2))
    return worst


def _allows(z, heights, threshold):
    i=bisect_left(heights,z)
    return all(abs(z-q)>=threshold-1.e-9 for q in heights[max(0,i-1):i+1])


def link_ties(families,continuous,verts,d,n,length,width,height,track,vertical_diameter,cover,aggregate, *,
              grid_role="dowel", member="link_crosstie", origin=(0.,0.), contact_diameter=None, tie_diameter=12):
    diameter=tie_diameter
    radius=3.5*diameter
    touch=(vertical_diameter+diameter)/2
    tail=max(10*diameter,80)
    grid=next(f for f in continuous if f["role"]==grid_role)
    count=len(verts)//2
    spacing=length/count
    def xy(u,v):
        return (origin[0]+u*d[0]+v*n[0],origin[1]+u*d[1]+v*n[1])
    constraints=[]
    def options(index):
        u=-length+(index+.5)*spacing
        result=[]
        best=None
        for sign,side,parity,angle in product((-1,1),(-1,1),(None,0,1),(0.,pi/3,pi/2)):
            stem=u+sign*(radius-(radius-touch)*cos(angle))
            centre_y=track-(radius-touch)*sin(angle)
            def hook(face):
                angles=[i*3*pi/4/12 for i in range(13)]
                points=[(stem-sign*radius*(1-cos(t)),face*(centre_y+radius*sin(t))) for t in angles]
                x,y=points[-1]
                points.append((x-sign*tail*sin(angles[-1]),y+face*tail*cos(angles[-1])))
                return points
            path=hook(-1)[::-1]+hook(1)
            error=radius*(1-cos(3*pi/96))
            if any(x < -length+diameter/2+error or x > -diameter/2-error or abs(y)+diameter/2+error>width/2-cover for x,y in path):
                continue
            ends=list(map(lambda p:xy(*p),path))
            errors=[0.]+[error]*12+[0.]+[error]*12+[0.]
            seg=list(zip(ends,ends[1:],errors))
            # The two intended verticals are embraced at the tangent. Check every other vertical.
            if any(min(point_distance(pt,a,b)-eps for a,b,eps in seg)<(v+diameter)/2-1.e-8
                   for j,(pt,v) in enumerate(verts) if j//2!=index):
                continue
            shift=side*(diameter+grid["diameter"])/2
            base_levels=grid["heights"] if parity is None else grid["heights"][parity::2]
            levels=[z+shift for z in base_levels if cover+diameter/2<=z+shift<=height-cover-diameter/2]
            if not levels:
                continue
            xs,ys=zip(*ends)
            f={"member":member,"role":"crosstie","face":index,"diameter":diameter,"horizontal":False,
               "heights":levels,"segments":seg,"bounds":(min(xs)-error,max(xs)+error,min(ys)-error,max(ys)+error)}
            # The dowel layer is intentionally enclosed on both faces and touches at the scheduled elevation.
            checks=[]
            contacts=set()
            allowed=levels
            for other in families:
                check=_separation(f,other,aggregate)
                if other in continuous and other["role"]==grid_role:
                    # A special crosstie wraps its own horizontal and vertical bars. Its curved
                    # head approaches the retained rod tangentially. Dedicated returns and the
                    # two free tails still obey the ordinary clearance check.
                    straight=[]
                    turns=[]
                    for a,b,eps in _segments(other):
                        du,dv=b[0]-a[0],b[1]-a[1]
                        (straight if eps==0 and abs(du*n[0]+dv*n[1])<1.e-7 else turns).append((a,b,eps))
                    dz=_closest_levels(levels,other["heights"])[0]
                    touch_z=(diameter+other["diameter"])/2
                    crosses=any(segment_distance(a,b,p,q)<1.e-7 for a,b,_ in straight for p,q,_ in seg[1:-1])
                    if crosses and abs(dz-touch_z)<1.e-7:
                        contacts.add(other["face"])
                        tests=[_separation({**f,"segments":[seg[0],seg[-1]]},{**other,"segments":straight},aggregate)]
                        if turns:
                            tests.append(_separation(f,{**other,"segments":turns},aggregate))
                        check=min(tests,key=lambda q:q["margin_mm"])
                        if not check["parallel"] and check["clear_mm"]>=-1.e-8:
                            check={**check,"fits":True,"margin_mm":max(0.,check["clear_mm"])}
                if not check["fits"] and allowed:
                    if other in continuous and other["role"]==grid_role and crosses and abs(dz-touch_z)<1.e-7:
                        threshold=_vertical_threshold({**f,"segments":[seg[0],seg[-1]]},{**other,"segments":straight},aggregate)
                        if turns:
                            threshold=max(threshold,_vertical_threshold(f,{**other,"segments":turns},aggregate))
                    else:
                        threshold=_vertical_threshold(f,other,aggregate)
                    allowed=[z for z in allowed if _allows(z,other["heights"],threshold)]
                    if allowed:
                        check={**check,"fits":True,"margin_mm":0.,"selection":"CLEAR_AT_RETAINED_TIE_LEVELS"}
                checks.append(check)
            if contacts!={-1,1}:
                continue
            worst=min(checks,key=lambda c:c["margin_mm"])
            if best is None or worst["margin_mm"]>best["margin_mm"]:
                best=worst
            if not allowed or not all(c["fits"] for c in checks):
                continue
            levels=f["heights"]=allowed
            result.append((f,{"station_mm":u,"hook_angle_deg":135,"inside_diameter_mm":2*radius-diameter,
                "tail_mm":tail,"diameter_mm":diameter,"points_mm":ends,"levels_mm":levels,"grid_parity":parity,
                "minimum_unrelated_margin_mm":min(c["margin_mm"] for c in checks)}))
        constraints.append(best)
        return result
    choices=[options(i) for i in range(count)]
    # Adjacent hooks may overlap in plan. Check the actual finite heights of every pair.
    required=10*(max(diameter,contact_diameter or max(f["diameter"] for f in continuous))/diameter)**2
    def certify(proposed):
        width_m=min(1.,length/1000)
        starts=[0.,length-1000]+[(i+.5)*spacing+1.e-7 for i in range(count) if (i+.5)*spacing+1.e-7<=length-1000]
        density=float("inf")
        for start in starts if length>1000 else [0.]:
            levels=sorted(z for i,(f,_) in enumerate(proposed) if start<=(i+.5)*spacing<=start+1000*width_m
                          for z in f["heights"])
            events=[0.,height-1000]+[z+1.e-7 for z in levels if z+1.e-7<=height-1000]
            density=min(density,min(bisect_right(levels,t+1000)-bisect_left(levels,t) for t in events)/width_m)
        if density>=required:
            return {"satisfied":True,"density_per_m2":density,"required_per_m2":required,
                    "crossties":[row for _,row in proposed]}
    tested=0
    pair_cache={}
    def compatible(a,b):
        key=id(a),id(b)
        if key not in pair_cache:
            pair_cache[key]=_separation(a[0],b[0],aggregate)["fits"]
        return pair_cache[key]
    def search(i,chosen):
        nonlocal tested
        tested+=1
        if i==len(choices):
            return certify(chosen)
        for candidate in choices[i]:
            if tested>=2048:
                return None
            if all(compatible(candidate,other) for other in chosen):
                prefix=[*chosen,candidate]
                if certify(prefix+union[i+1:]) is None:
                    continue
                success=search(i+1,prefix)
                if success:
                    return success
    for opts in choices:
        opts.sort(key=lambda option:-len(option[0]["heights"]))
    union=[({"heights":sorted({z for fam,_ in opts for z in fam["heights"]})}, {}) for opts in choices]
    optimistic=certify(union) if all(choices) else None
    # Adjacent stations may interleave occupied tie levels. Crop only the
    # conflicting levels of a real hook and recheck the installed metre census.
    def interleave(phase=None):
        indices=list(range(count))
        for order in (indices,indices[::-1],indices[::2]+indices[1::2]):
            installed={}
            for index in order:
                best=None
                for f,row in choices[index]:
                    if phase is not None and row["grid_parity"] != (index+phase)%2:
                        continue
                    levels=f["heights"]
                    for other,_ in installed.values():
                        candidate={**f,"heights":levels}
                        if _separation(candidate,other,aggregate)["fits"]:
                            continue
                        threshold=_vertical_threshold(f,other,aggregate)
                        levels=[z for z in levels if _allows(z,other["heights"],threshold)]
                        if not levels:
                            break
                    if levels and (best is None or len(levels)>len(best[0]["heights"])):
                        best=({**f,"heights":levels},{**row,"levels_mm":levels})
                        if len(levels)==len(choices[index][0][0]["heights"]):
                            break
                if best is None:
                    break
                installed[index]=best
            if len(installed)==count:
                chosen=[installed[i] for i in indices]
                out=certify(chosen)
                if out and all(_separation(a[0],b[0],aggregate)["fits"] for i,a in enumerate(chosen) for b in chosen[:i]):
                    return {**out,"placement":"STATION_SPECIFIC_VERIFIED_TIE_LEVELS" if phase is None else
                            "ALTERNATING_STATION_GRID_PHASE","first_station_parity":phase}
    selected=None
    if optimistic:
        selected=interleave(0) or interleave(1) or interleave() or search(0,[])
    return selected or {"satisfied":False,"search_nodes":tested,
        "search_ceiling_reached":tested>=2048,
        "admissible_paths_by_station":[len(v) for v in choices],"best_clearance_by_station":constraints,"reason":"CROSSTIE_HOOK_OR_DENSITY"}


def tie_families(member, schedule):
    """Recover the exact plan chords and installed elevations for adjacent-cage checks."""
    for index, tie in enumerate(schedule.get("crossties", [])):
        points=tie["points_mm"]
        diameter=tie["diameter_mm"]
        error=3.5*diameter*(1-cos(3*pi/96))
        errors=[0.]+[error]*12+[0.]+[error]*12+[0.]
        xs,ys=zip(*points)
        yield {"member":member,"role":"crosstie","face":index,"diameter":diameter,"horizontal":False,
               "heights":tie["levels_mm"],"segments":list(zip(points,points[1:],errors)),
               "bounds":(min(xs)-error,max(xs)+error,min(ys)-error,max(ys)+error)}
