"""Enumerate covered quarter-bends for each face of the transverse wall at a T junction."""
from math import ceil, hypot
from itertools import product

from .basement_joint_layout import _separation
from .basement_wall_connection import _forward_length
from .basement_wall_pressure import clear_limit
from .wall_bar_paths import bent_path, segment_distance


def hoop_plan_gap(points, errors, direction, end_width, wall_width, cover):
    """Lower centreline distance to the entire closed hoop and hook envelope in plan."""
    normal = (-direction[1], direction[0])
    def local(point):
        return tuple(sum(a*b for a,b in zip(point,axis)) for axis in (direction,normal))
    low, high = cover, end_width-cover
    depth = wall_width/2-cover
    corners = [(low,-depth),(high,-depth),(high,depth),(low,depth)]
    outline = list(zip(corners,corners[1:]+corners[:1]))
    result = float("inf")
    for a,b,error in zip(points,points[1:],errors):
        a,b = local(a),local(b)
        if any(low <= x <= high and -depth <= y <= depth for x,y in (a,b)):
            return 0.
        result = min(result,max(0.,min(segment_distance(a,b,c,d) for c,d in outline)-error))
    return result


def route_search(panel,side,straight_families,xyz,layout,material,cover,aggregate,height,pitch,tie,verticals,
                 direction_pier, end_width):
    from .wall_bridge_coordinated import _receiving_clearance, window_grid
    from .basement_wall_connection import tension_development
    support = panel["support_sections"][side]
    dx,dy = panel["width_direction"]
    sense = 1 if side=="J" else -1
    forward,normal=(sense*dx,sense*dy),(-dy,dx)
    width=1000*panel["thickness_m"]
    own=1000*panel["clear_length_m"]
    # The full T is the union of the transverse incoming web and the two receiving arms.
    # In local (normal,forward) coordinates its two reentrant corners are (+/-w/2,-w/2).
    # Outside the incoming strip the rod needs full cover to the horizontal free edge.
    def covered(points,errors,radius):
        for a,b,error in zip(points,points[1:],errors):
            def loc(p):
                return (sum(x*y for x,y in zip(p,normal)),sum(x*y for x,y in zip(p,forward)))
            a,b=loc(a),loc(b)
            if max(a[1],b[1])+radius+error>width/2:
                return False
            for sign in (-1,1):
                # The exposed horizontal and vertical edges of this corner are rays.
                corner = (sign*width/2,-width/2)
                rays = ((sign*100000.,-width/2),(sign*width/2,-100000.))
                if min(segment_distance(a,b,corner,q) for q in rays)<radius+error-1.e-8:
                    return False
        return True
    options={}
    census={}
    for role,face in product(("web","dowel"),(-1,1)):
        grid=layout[role]
        dia=grid["diameter_mm"]
        band=pitch/2-clear_limit(aggregate,dia,tie)-(dia+tie)/2
        bond=tension_development(dia,material.fyd,material.fck,material.fcd,cover,pitch-dia)["position_i_mm"]
        tail=ceil(bond/5)*5
        if own/2<bond:
            raise ValueError("INSUFFICIENT_INCOMING_DEVELOPMENT")
        offset=layout[role+"_track_mm"]
        limits={"geometric_paths":0,"receiving_vertical_clear":0,"link_vertical_clear":0,"continuous_field_clear":0}
        survivors=[]
        best=None
        for arm in support["incident_walls"]:
            if not arm["across"]:
                continue
            direction=arm["direction"]
            length,receiver=_forward_length(arm,direction)
            for factor,dest in product((3.5,5.,7.,9.,12.,15.),range(-145,146,5)):
                radius=factor*dia
                if abs(dest)+dia/2+cover>width/2:
                    continue
                outward=face*offset*sum(x*y for x,y in zip(normal,direction))
                if outward+radius+tail+dia/2+cover>length:
                    continue
                start=tuple(face*offset*normal[i]-(radius-dest)*forward[i] for i in (0,1))
                path=bent_path(face,start,forward,direction,0.,radius,tail)
                pts=path["points_mm"][1:]
                err=path["chord_error_mm"][1:]
                first=tuple(face*offset*normal[i]-(support["depth_mm"]/2+(own if role=="web" else bond))*forward[i]
                            for i in (0,1))
                if sum((p-q)*a for p,q,a in zip(pts[0],first,forward))<0:
                    continue
                pts.insert(0,first)
                err.insert(0,0.)
                if not covered(pts,err,cover+dia/2):
                    continue
                limits["geometric_paths"]+=1
                xs,ys=zip(*pts)
                extra=max(err)
                fam={"member":panel["member"],"role":role,"face":face,"diameter":dia,"horizontal":abs(dx)>.5,
                     "segments":list(zip(pts,pts[1:],err)),"bounds":(min(xs)-extra,max(xs)+extra,min(ys)-extra,max(ys)+extra)}
                rc=_receiving_clearance(fam,xyz,aggregate)
                if rc["margin_mm"]<0:
                    continue
                limits["receiving_vertical_clear"]+=1
                lc=_receiving_clearance(fam,verticals,aggregate)
                if lc["margin_mm"]<0:
                    continue
                limits["link_vertical_clear"]+=1
                plan_gap = hoop_plan_gap(pts,err,direction_pier,end_width,width,cover)
                for phase in (-pitch/2,-pitch/3,-band+.1,-band/2,0.,band/2,band-.1,pitch/3,pitch/2):
                    hoop_clear = hypot(plan_gap,pitch/2-abs(phase))-(dia+tie)/2
                    if hoop_clear < clear_limit(aggregate,dia,tie):
                        continue
                    alt=window_grid(height,pitch,[phase],dia,cover,aggregate)
                    if alt["guaranteed_bars_per_m"]<grid["guaranteed_bars_per_m"]:
                        continue
                    current={**fam,"heights":alt["levels_mm"]}
                    controls=[_separation(current,f,aggregate) for f in straight_families]
                    worst=min(controls,key=lambda c:c["margin_mm"])
                    descriptor={"receiving_members":receiver,"inside_bend_diameter_mm":2*radius-dia,
                                "tail_track_mm":dest,"phase_mm":phase,"full_straight_tail_mm":tail,
                                "receiving_vertical_margin_mm":rc["margin_mm"],"link_vertical_margin_mm":lc["margin_mm"],
                                "continuous_field_margin_mm":worst["margin_mm"],"governing_field":worst,
                                "boundary_hoop_clear_mm":hoop_clear,"boundary_hoop_plan_gap_mm":plan_gap}
                    if best is None or worst["margin_mm"]>best["continuous_field_margin_mm"]:
                        best=descriptor
                    if all(c["fits"] for c in controls):
                        limits["continuous_field_clear"]+=1
                        survivors.append((current,descriptor))
        key=role+("_minus" if face<0 else "_plus")
        census[key]={**limits,"best":best}
        options[key]=survivors
    def match(keys,chosen):
        if not keys:
            return chosen
        key,*rest=keys
        for f,description in options[key]:
            if all(_separation(f,old,aggregate)["fits"] for old,_ in chosen.values()):
                found=match(rest,{**chosen,key:(f,description)})
                if found is not None:
                    return found
        return None
    found=match(sorted(options,key=lambda k:len(options[k])),{})
    return {"cases":census,"all_four_paths_fit":found is not None,
            "selected_families":[v[0] for v in found.values()] if found else [],
            "selection":{k:v[1] for k,v in found.items()} if found else {},
            "scope":"Both physical receiving directions, six bend radii, 5 mm tail tracks and nine phases against the covered hoop footprint"}
