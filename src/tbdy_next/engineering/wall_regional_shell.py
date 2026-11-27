"""Static lower-bound membrane/plate fields at the actual curtain planes of a wall strip."""
from math import hypot, sqrt


def _clip(points, a, b, limit):
    """Intersect a convex polygon of admissible face tensions with a half-plane."""
    result = []
    previous = points[-1]
    previous_value = a*previous[0] + b*previous[1] - limit
    for current in points:
        value = a*current[0] + b*current[1] - limit
        if (value > 0) != (previous_value > 0):
            fraction = previous_value/(previous_value-value)
            result.append(tuple(x+fraction*(y-x) for x,y in zip(previous,current)))
        if value <= 0:
            result.append(current)
        previous,previous_value = current,value
    return result


def _admissible(force, moment, planes, thickness, skin, cracked, core_shear, limit):
    arm = thickness-skin
    if hypot(*(max(map(abs,v)) for v in moment[3:])) > limit*core_shear*(thickness-2*skin):
        return False
    shear = [max(abs(n/2-sign*m*1000/arm) for n in force[2] for m in moment[2]) for sign in (1,-1)]
    for axis, (xp,xn,capacity_p,capacity_n) in enumerate(planes):
        for normal in set(force[axis]):
            for bending in set(moment[axis]):
                p,n = limit*capacity_p,limit*capacity_n
                polygon = [(0.,0.),(p,0.),(p,n),(0.,n)]
                for sign,tau in zip((1,-1),shear):
                    # The two independent steel ties are at +xp and -xn.
                    # N = T+ + T- - C+ - C-. Positive CSI M compresses the +3 skin.
                    a,b = .5+sign*xp/arm,.5-sign*xn/arm
                    base = normal/2-sign*1000*bending/arm
                    # Diagonal dominance of both C and limit*fcd*skin*I-C
                    # encloses both principal compressions including in-plane shear.
                    polygon = _clip(polygon,-a,-b,-(base+tau))
                    if polygon:
                        polygon = _clip(polygon,a,b,base+limit*skin*cracked-tau)
                    if not polygon:
                        return False
    return True


def regional_shell(states, coordinates, station, curtains, thickness, material, limit, *, edge_steel=None):
    """A common skin depth must work for every endpoint of a native component box."""
    cracked = .6*(1-material.fck/250)*material.fcd
    core_shear = .65*.35*sqrt(material.fck)*material.fcd/material.fck
    trials = tuple(range(5,int(thickness/2),5))
    probes = {}
    for name, rows in states.items():
        for element, point, membrane, plate in rows:
            s = station(coordinates[point])
            sections = curtains(s)
            key = (name,element,point)
            if key in probes:
                raise ValueError("DUPLICATE_NATIVE_REGIONAL_CORNER")
            # Enclose both local-3 orientations for an asymmetric splice. One
            # compression depth equilibrates every sign/interval for this physical corner.
            planes = {tuple(axes) for axes in sections}
            planes.update(tuple((xn,xp,n,p) for xp,xn,p,n in axes) for axes in sections)
            adopted=None
            for fraction,track,stock in ((0.,0.,0.),*(edge_steel(name,s) if edge_steel else ())):
                def allocated(axes):
                    (xp,xn,p,n),vertical=axes
                    extra=fraction*stock
                    return (((xp*p+track*extra)/(p+extra),(xn*n+track*extra)/(n+extra),p+extra,n+extra),vertical)
                depth=next((v for v in trials if all(_admissible(membrane,plate,allocated(axes),thickness,v,cracked,core_shear,limit)
                                                    for axes in planes)),None)
                if depth is not None:
                    adopted=(depth,fraction)
                    break
            probes[key] = (round(s,6),adopted)
    groups = {}
    failed = []
    for (name,element,point),(s,adopted) in probes.items():
        row = groups.setdefault(s,{"station_mm":s,"expected":0,"satisfied":0,"skin_range_mm":[],"max_residual_dowel_fraction":0.})
        row["expected"]+=1
        if adopted is None:
            failed.append({"combination":name,"element":element,"point":point,"station_mm":s})
        else:
            depth,fraction=adopted
            row["max_residual_dowel_fraction"]=max(row["max_residual_dowel_fraction"],fraction)
            row["satisfied"]+=1
            row["skin_range_mm"] = [min([depth,*row["skin_range_mm"]]), max([depth,*row["skin_range_mm"]])]
    from .design_scenario import _digest
    return {"method":"EQUILIBRATED_DISTINCT_STEEL_AND_CONCRETE_PLANES","selection_limit":limit,
            "corner_count":len(probes),"satisfied":bool(probes) and not failed,"failures":failed,
            "stations":[groups[s] for s in sorted(groups)],"corner_proof_sha256":_digest(
                [[*key,s,t] for key,(s,t) in sorted(probes.items())])}
