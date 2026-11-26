"""Physical vertical wall edge actions, shared frame nodes and signed interior nodal equilibrium."""
from collections import defaultdict
from math import fsum, hypot, isfinite

from .basement_pier_geometry import required
from .gravity_wall_cut import _global_force
from .wall_transition import TOL


def _node_incidence(edge, selected, combinations):
    """Sum signed forces and moments at the same native point in common global axes."""
    terms = defaultdict(lambda: defaultdict(list))
    for role in ("areas", "frames"):
        for uid, item in edge[role].items():
            indices = [(i, p) for i, (_, p) in enumerate(item["corners"]) if p in selected]
            if not indices:
                continue
            for name, spec in combinations.items():
                if spec["spectral"]:
                    continue
                steps = item["cases"][name]
                signed = next(iter(steps.values()))
                required(all(len(v)==len(item["corners"]) for v in steps.values()),
                         "NODAL_EDGE_STEP_POPULATION_DIFFERS")
                for i,p in indices:
                    local = signed[i]
                    required(len(local)==6 and all(isfinite(x) for x in local) and all(
                             all(abs(a-b)<=1e-8+1e-10*max(abs(a),abs(b)) for a,b in zip(local,other[i]))
                             for other in steps.values()), "EDGE_STATIC_JOINT_FORCE_IS_NOT_SIGNED")
                    matrix = edge["point_bases"][p][1]
                    forces = (*_global_force(local[:3],matrix), *_global_force(local[3:],matrix))
                    terms[p][name].append((role,uid,forces))
    return terms


def _absolute_lower(interval):
    return max(0., interval[0], -interval[1])


def _nodal_tractions(raw, uid, nodes, coords, direction, combinations):
    """Independent per-metre bound at interior nodes from wall-side native nodal actions."""
    item = raw["areas"][uid]
    index = defaultdict(list)
    for i,(elm,p) in enumerate(item["corners"]):
        index[p].append((i,elm))
    dx,dy = direction
    ranges = defaultdict(list)
    for before,p,after in zip(nodes,nodes[1:],nodes[2:]):
        length = (coords[after][2]-coords[before][2])/2
        required(length>0 and index[p], "NODAL_EDGE_TRIBUTARY_LENGTH_REQUIRED")
        basis = raw["point_bases"][p][1]
        unit = [_global_force(tuple(float(i==j) for i in range(3)),basis) for j in range(3)]
        projections = [[x*dx+y*dy for x,y,z in unit],[z for x,y,z in unit],[-x*dy+y*dx for x,y,z in unit]]
        for name,spec in combinations.items():
            steps=item["cases"][name]
            low=steps.get("Min",next(iter(steps.values())))
            high=steps.get("Max",low)
            components=[]
            for coeff in projections:
                lower, upper = [], []
                for i,_ in index[p]:
                    required(len(low[i])==len(high[i])==6 and all(isfinite(a) and isfinite(b) and a<=b+1e-8
                             for a,b in zip(low[i],high[i])), "NODAL_SUPPORT_COMPONENT_INTERVAL_INVALID")
                    lower.extend(min(c*a,c*b) for c,a,b in zip(coeff,low[i],high[i]))
                    upper.extend(max(c*a,c*b) for c,a,b in zip(coeff,low[i],high[i]))
                components.append([fsum(lower)/length,fsum(upper)/length])
            n,v,w = (max(map(abs,r)) for r in components)
            shear = hypot(v,w)
            ranges[name].append({"point":p,"element":" + ".join(e for _,e in index[p]),
                "normal_tension_kn_m":n,"native_shear_kn_m":shear,"equivalent_friction_demand_kn_m":shear+.6*n,
                "traction_source":"WALL_SIDE_NODAL_TRIBUTARY_ABSOLUTE_NORMAL","tributary_height_m":length,
                # The nodal normal has no oriented tensile sign. It increases the upper
                # bound but supplies no guaranteed positive tension for a bond difference.
                "equivalent_friction_lower_kn_m":hypot(*map(_absolute_lower,components[1:])),
                "normal_vertical_transverse_kn_m":components})
    return ranges


def edge_tie_upper(states, nodes, arm_mm):
    """Either physical face, using the same tensile-tie/concrete field as the selected web."""
    from .wall_membrane_design import required_face_forces
    selected=set(nodes)
    upper={}
    for name,corners in states.items():
        for _,pt,membrane,plate in corners:
            if pt in selected:
                key=(name,pt)
                upper[key]=max(upper.get(key,0.),*(required_face_forces(membrane,plate[:3],f,arm_mm/1000)[0]
                                                  for f in (-1,1)))
    return upper


def edge_bar_forces(states, nodes, arm_mm):
    """Horizontal resultant bound on either face, including twisting of the tie field."""
    selected = set(nodes)
    forces = {}
    arm = arm_mm/1000
    for case, corners in states.items():
        for _, pt, membrane, plate in corners:
            if pt not in selected:
                continue
            for face in (-1,1):
                def face_max(component):
                    n, m = membrane[component], plate[component]
                    return max(abs(v/2-face*w/arm) for v in n for w in m)
                key = (case,pt)
                forces[key] = max(forces.get(key,0.),face_max(0)+face_max(2))
    return forces


def support_edge_actions(panel, geometry, raw, states, combinations, *, record_transfer_intervals=False):
    """Use line tractions for design. Endpoint nodal forces also contain floor or mat actions."""
    uid = panel["member"]
    edges = raw["boundaries"][uid]
    xy = panel["width_direction"]
    coords = {p:raw["point_bases"][p][0] for pair in edges for p in pair}
    along = {p:fsum(a*b for a,b in zip(xy,xyz)) for p,xyz in coords.items()}
    results = {}
    for side, extreme in (("I",min),("J",max)):
        x = extreme(along.values())
        segments = [e for e in edges if all(abs(along[p]-x)<=TOL for p in e)]
        nodes = sorted({p for e in segments for p in e},key=lambda p:coords[p][2])
        required(len(nodes)>1 and {tuple(sorted(e)) for e in segments} ==
                 {tuple(sorted(e)) for e in zip(nodes,nodes[1:])} and
                 abs(coords[nodes[0]][2]-geometry["bottom_m"])<=TOL and
                 abs(coords[nodes[-1]][2]-geometry["top_m"])<=TOL, "CONTINUOUS_VERTICAL_EDGE_REQUIRED")
        column = panel["column_"+side.lower()]
        support = panel.get("support_sections", {}).get(side, {})
        counterparts = ([("frames",column)] if column else
                        [("areas",r["member"]) for r in support.get("incident_walls",[])])
        required(counterparts and all(set(nodes) <= {p for _,p in raw[role].get(obj,{}).get("corners",[])}
                 for role,obj in counterparts), "EXACT_SHARED_FRAME_EDGE_NODES_REQUIRED" if column else
                 "EXACT_SHARED_WALL_EDGE_NODES_REQUIRED")
        nodeset=set(nodes)
        incident=_node_incidence(raw,nodeset,combinations)
        controls=[]
        for node in nodes:
            for name,spec in combinations.items():
                if spec["spectral"]:
                    continue
                actions=incident[node][name]
                own=[f for role,obj,f in actions if role=="areas" and obj==uid]
                opposite=[f for role,obj,f in actions if (role,obj) in counterparts]
                required(own and opposite,"BOTH_NATIVE_SUPPORT_SIDES_REQUIRED")
                residual=[fsum(f[i] for _,_,f in actions) for i in range(6)]
                internal=node not in (nodes[0],nodes[-1])
                limits=[max(.02,1e-6*fsum(abs(f[i]) for _,_,f in actions)) for i in range(6)]
                controls.append({"combination":name,"point":node,"interior":internal,
                    "wall_kn_knm":[fsum(f[i] for f in own) for i in range(6)],
                    ("column_kn_knm" if column else "adjacent_walls_kn_knm"):[fsum(f[i] for f in opposite) for i in range(6)],
                    "all_incident_residual_kn_knm":residual,"limits_kn_knm":limits,
                    "balanced":all(abs(v)<=lim for v,lim in zip(residual,limits)) if internal else None})
        # Each field is already in the wall h,z frame. Positive Fhh is tension on either cut.
        # Normal tension is allocated to additional anchored dowels along with friction steel.
        nodal = _nodal_tractions(raw,uid,nodes,coords,xy,combinations)
        cuts=[]
        for name,corners in states.items():
            candidates=[]
            for elm,pt,membrane,plate in corners:
                if pt not in nodeset:
                    continue
                normal=max(0.,membrane[0][1])
                shear=hypot(max(map(abs,membrane[2])),max(map(abs,plate[3])))
                candidates.append({"element":elm,"point":pt,"normal_tension_kn_m":normal,
                    "native_shear_kn_m":shear,"equivalent_friction_demand_kn_m":shear+.6*normal,
                    "traction_source":"UNAVERAGED_EDGE_CORNER_FIELD",
                    "equivalent_friction_lower_kn_m":hypot(_absolute_lower(membrane[2]),_absolute_lower(plate[3])) + .6*max(0.,membrane[0][0])})
            required(candidates and {r["point"] for r in candidates}==nodeset,"ALL_EDGE_FIELD_CORNERS_REQUIRED")
            field_governing=max(candidates,key=lambda r:r["equivalent_friction_demand_kn_m"])
            candidates.extend(nodal[name])
            governing=max(candidates,key=lambda r:r["equivalent_friction_demand_kn_m"])
            cuts.append({"combination":name,**governing,"field_bound_kn_m":field_governing["equivalent_friction_demand_kn_m"],
                         "nodal_bound_kn_m":max((v["equivalent_friction_demand_kn_m"] for v in nodal[name]),default=None),
                         "max_native_shear_kn_m":max(r["native_shear_kn_m"] for r in candidates),
                         "basis":"NATIVE_COMPONENT_INTERVAL_BOUND" if combinations[name]["spectral"] else "SIGNED_STATIC"})
            if record_transfer_intervals:
                vertical = []
                for node in nodes:
                    sample = [c for c in candidates if c["point"] == node]
                    vertical.append({"z_m":coords[node][2], "node":node,
                        "lower_kn_m":min(c["equivalent_friction_lower_kn_m"] for c in sample),
                        "upper_kn_m":max(c["equivalent_friction_demand_kn_m"] for c in sample),
                        "element_intervals":{c["traction_source"]+"|"+c["element"]:
                            [c["equivalent_friction_lower_kn_m"], c["equivalent_friction_demand_kn_m"]]
                            for c in sample}})
                cuts[-1]["tension_intervals"] = vertical
        middle=[r for r in controls if r["interior"]]
        results[side]={"column":column,"counterparts":counterparts,"nodes":nodes,"checked_static_interior":len(middle),
                       "balanced_static_interior":sum(r["balanced"] for r in middle),
                       "native_joint_controls":controls,"cuts":cuts,
                       "status":"NATIVE_EDGE_CONTROL_SATISFIED" if middle and all(r["balanced"] for r in middle)
                                else "NATIVE_EDGE_EQUILIBRIUM_UNRESOLVED",
                       "endpoint_scope":"BOTTOM_AND_TOP_INCLUDE_FLOOR_OR_MAT_ACTIONS; LINE_TRACTIONS_RETAINED"}
    return results
