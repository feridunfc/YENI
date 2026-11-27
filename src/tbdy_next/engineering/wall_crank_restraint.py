"""Necessary signed equilibrium for transverse ties anchored on the other registered curtain."""
from math import cos, hypot, pi, sin

from .wall_bar_paths import point_distance, segment_distance


def hook_path(a,b,da,db,tie,sign,bend):
    """Two 135 degree ends tangent to the *outside* of the actual retained rods."""
    span=hypot(b[0]-a[0],b[1]-a[1])
    u=((b[0]-a[0])/span,(b[1]-a[1])/span)
    v=(-sign*u[1],sign*u[0])
    radius=bend*tie
    tail=max(80.,10*tie)
    def head(p,bar,side):
        touch=(bar+tie)/2
        center=[p[k]-side*(radius-touch)*u[k] for k in (0,1)]
        points=[]
        for i in range(19):
            t=i*pi/24
            points.append(tuple(center[k]+radius*(v[k]*cos(t)+side*u[k]*sin(t)) for k in (0,1)))
        points.append(tuple(points[-1][k]+tail*(-v[k]*sin(t)+side*u[k]*cos(t)) for k in (0,1)))
        return points
    return head(a,da,-1)[::-1]+head(b,db,1),radius*(1-cos(pi/48))


def brace_options(target, anchor_grid, bars, diameter, fyd, height, width, cover):
    x,z=target
    options=[]
    for ax,az,ad in anchor_grid:
        if abs(az-z)>300:
            continue
        other=[(bx,bz,bd) for bx,bz,bd in bars if min(z,az)-150<=bz<=max(z,az)+150 and
               (bx,bz)!=(x,z) and (bx,bz)!=(ax,az)]
        for tie in (8,10,12,14,16):
            found=False
            for bend in (3.5,4.5,6.):
                for sign in (-1,1):
                    path,error=hook_path(target,(ax,az),diameter,ad,tie,sign,bend)
                    if any(abs(s)+tie/2+error>width/2-cover or min(t,height-t)<cover+tie/2+error for s,t in path):
                        continue
                    if any(point_distance((bx,bz),p,q)<(tie+bd)/2+error for p,q in zip(path,path[1:])
                           for bx,bz,bd in other if min(p[1],q[1])-24<=bz<=max(p[1],q[1])+24
                           and min(p[0],q[0])-24<=bx<=max(p[0],q[0])+24):
                        continue
                    slope=(az-z)/abs(ax-x)
                    options.append({"anchor":[ax,az,ad],"diameter_mm":tie,"bend_radius_mm":tie*bend,
                                    "bend_sign":sign,"slope":slope,"horizontal_kn":pi*tie**2*fyd/4000/hypot(1.,slope)})
                    found=True
                    break
                if found:
                    break
    return options


def bracket(options,reaction,slope):
    """Solve two signed equilibrium equations with nonnegative tensile reactions."""
    horizontal=reaction/hypot(1.,slope)
    for a in options:
        if abs(a["slope"]-slope)<1.e-8 and a["horizontal_kn"]>=horizontal:
            return [{"tie":a,"horizontal_used_kn":horizontal}]
        for b in options:
            if not a["slope"]<slope<b["slope"]:
                continue
            ha=horizontal*(b["slope"]-slope)/(b["slope"]-a["slope"])
            if ha<=a["horizontal_kn"] and horizontal-ha<=b["horizontal_kn"]:
                return [{"tie":a,"horizontal_used_kn":ha},{"tie":b,"horizontal_used_kn":horizontal-ha}]
    return []


def simultaneous_hook_clearance(rows, faces, old_d, new_d):
    """Test the selected hook pairs together at each outward crank tangent."""
    planes={}
    possible=0
    conflicts=0
    first=None
    for cell in rows:
        face=faces[cell["face"]]
        new=cell["bar"]=="new"
        x=face["new_lap_track_mm"] if new else face["old_lap_track_mm"]
        target=(cell["face"]*x,cell["z_mm"])
        local=planes.setdefault(cell["station_mm"],[])
        for entry in cell["balanced_hook_pair"]:
            tie=entry["tie"]
            ax,az,ad=tie["anchor"]
            diameter=tie["diameter_mm"]
            path,error=hook_path(target,(ax,az),new_d if new else old_d,ad,diameter,
                                 tie["bend_sign"],tie["bend_radius_mm"]/diameter)
            box=(min(p[0] for p in path),max(p[0] for p in path),min(p[1] for p in path),max(p[1] for p in path))
            for old_box,old_path,other_d,other_error,old_z in local:
                required=(other_d+diameter)/2+other_error+error
                if (box[0]>old_box[1]+required or old_box[0]>box[1]+required
                        or box[2]>old_box[3]+required or old_box[2]>box[3]+required):
                    continue
                possible+=1
                overlaps=any(segment_distance(p,q,r,s)<required for p,q in zip(path,path[1:])
                             for r,s in zip(old_path,old_path[1:]) if
                             max(min(p[0],q[0])-max(r[0],s[0]),min(r[0],s[0])-max(p[0],q[0]),
                                 min(p[1],q[1])-max(r[1],s[1]),min(r[1],s[1])-max(p[1],q[1]))<=required)
                if overlaps:
                    conflicts+=1
                    if first is None:
                        first={"station_mm":cell["station_mm"],"levels_mm":[old_z,cell["z_mm"]],
                               "diameters_mm":[other_d,diameter]}
            local.append((box,path,diameter,error,cell["z_mm"]))
    return {"layout":"COMMON_TANGENT_PLANE_AT_EACH_OUTWARD_BEND","candidate_pairs_tested":possible,
            "interfering_pairs":conflicts,"first_interference":first,
            "satisfied":bool(rows) and all(r["balanced_hook_pair"] for r in rows) and conflicts==0}


def crank_tie_envelope(faces, old_track, bridge_track, *, dims=None):
    """Positive combinations of tie forces lie inside their extreme directional slopes.

    Check the bend that pushes the moving rod toward the exposed face. Its
    required reaction points into the wall. This is an optimistic screen: all
    opposing anchor levels, unlimited steel and free hook rotation are allowed.
    """
    rows=[]
    for sign,face in faces.items():
        peer=faces[-sign]
        if face["cranked_bar"]=="new":
            new=True
            station=face["crank_start_mm"]
            target_track=face["new_lap_track_mm"]
            dx=bridge_track-target_track
            targets=[(z,0.) for z in face["new_levels_mm"]]
        else:
            new=False
            station=face["crank_start_mm"]+face["crank_run_mm"]
            target_track=face["old_lap_track_mm"]
            dx=old_track-target_track
            targets=[(z,(z-z0)/dx) for z0,z in zip(face["old_levels_mm"],face["old_lap_levels_mm"],strict=True)]
        anchors=[]
        if station<=peer["lap_end_mm"]:
            if peer["cranked_bar"]=="old" and station>peer["crank_start_mm"]:
                raise ValueError("OPPOSING_CRANK_MUST_BE_RESOLVED_AT_SUPPORT")
            anchors.extend((old_track,z) for z in peer["old_levels_mm"])
            if peer.get("straight_edge_starters_mm") and station<=peer["straight_edge_termination_station_mm"]:
                anchors.extend((old_track,z) for z in peer["straight_edge_starters_mm"])
        if station>=peer["lap_start_mm"]:
            if peer["cranked_bar"]=="new" and station<peer["crank_start_mm"]+peer["crank_run_mm"]-1.e-7:
                raise ValueError("OPPOSING_CRANK_MUST_BE_RESOLVED_AT_SUPPORT")
            anchors.extend((bridge_track,z) for z in peer["new_levels_mm"])
        if not anchors or dx<=0:
            raise ValueError("CRANK_REACTION_ANCHOR_OR_DIRECTION_MISSING")
        for z,required_slope in targets:
            directions=[((pz-z)/(x+target_track),pz) for x,pz in anchors]
            lower,upper=min(directions),max(directions)
            ratio=max(lower[0]-required_slope,required_slope-upper[0],0.)
            # For a fanned curtain the tabulated per-bar reaction is the
            # maximum over all levels. Use each rod's actual tangent slope.
            max_z=face["fan_out_mm"]
            tangent=hypot(dx,required_slope*dx)/hypot(dx,max_z)/6
            force=face["crank_reaction_per_bar_kn"]*tangent/hypot(1,tangent)*hypot(1,1/6)*6
            horizontal=force/hypot(1,required_slope)
            braces=[]
            if dims and ratio<1.e-8:
                old_d,new_d,fyd,height,width,cover=dims
                peer_d=old_d if new else new_d
                rod_d=new_d if new else old_d
                other=[(-sign*x,pz,peer_d) for x,pz in anchors]
                same=[(sign*target_track,tz,rod_d) for tz,_ in targets]
                # Both original and incoming parallel grids coexist at the lap endpoint.
                if new:
                    same.extend((sign*old_track,tz,old_d) for tz in face["old_levels_mm"])
                else:
                    same.extend((sign*bridge_track,tz,new_d) for tz in face["new_levels_mm"])
                options=brace_options((sign*target_track,z),other,same+other,rod_d,fyd,height,width,cover)
                braces=bracket(options,force,required_slope)
            rows.append({"face":sign,"bar":"new" if new else "old","station_mm":station,"z_mm":z,
                         "required_slope":required_slope,"anchor_slope_range":[lower[0],upper[0]],
                         "extreme_anchor_levels_mm":[lower[1],upper[1]],"transverse_reaction_kn":force,
                         "residual_z_kn_at_horizontal_equilibrium":ratio*horizontal,
                         "admissible":ratio<1.e-8,"balanced_hook_pair":braces})
    bad=[r for r in rows if not r["admissible"]]
    missing=[r for r in rows if not r["balanced_hook_pair"]]
    assembly=simultaneous_hook_clearance(rows,faces,*dims[:2]) if dims else None
    return {"scope":"DIRECT_TENSION_CROSSTIES_TO_ALL_REGISTERED_OPPOSING_WEB_BARS",
            "common_plane_assembly":assembly,
            "bar_count":len(rows),"outside_tie_cone_count":len(bad),"governing":max(rows,key=lambda r:r["residual_z_kn_at_horizontal_equilibrium"]),
            "outside_tie_cone":bad,"directionally_admissible":not bad,
            "balanced_hook_pairs":len(rows)-len(missing),"unbraced":[[v["face"],v["z_mm"]] for v in missing],
            "bar_checks":rows}
