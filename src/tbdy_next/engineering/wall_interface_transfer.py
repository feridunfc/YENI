"""Native point actions along the shared physical W22/W23 edge of the C104 study."""
from collections import defaultdict
from math import fsum, isclose

from .coupled_wall_transition import BALANCE_ABS, BALANCE_REL, IDENTITY, SIGNED_CASES
from .gravity_wall_cut import _check, _vector, joint_action_at_origin

GLOBAL = ("FX","FY","FZ","MX","MY","MZ")
PAIR = ("437","438")


def physical_interface(source):
    geometry = source["vs06_b1_geometry_source"]["table_reads"]
    points = {r["UniqueName"]:[float(r[d]) for d in "XYZ"] for r in geometry["Point Object Connectivity"]["rows"]}
    walls = {r["UniqueName"]:r for r in geometry["Wall Object Connectivity"]["rows"]}
    w22,w23 = (walls[u] for u in PAIR)
    _check([w22["WallBay"],w23["WallBay"]] == ["W22","W23"] and w22["Story"] == w23["Story"],
           "DESIGN_WALL_INTERFACE_IDENTITY")
    corners = {r["WallBay"]:{r["UniquePt"+str(i)]:points[r["UniquePt"+str(i)]] for i in range(1,5)}
               for r in (w22,w23)}
    edge_x = max(p[0] for p in corners["W22"].values())
    edge_y = {p[1] for wall in corners.values() for p in wall.values()}
    _check(len(edge_y)==1 and edge_x==min(p[0] for p in corners["W23"].values()), "DESIGN_WALL_INTERFACE_PLANES")
    edge_y, = edge_y
    zlo = max(min(p[2] for p in wall.values()) for wall in corners.values())
    zhi = min(max(p[2] for p in wall.values()) for wall in corners.values())
    _check(zlo<zhi,"DESIGN_WALL_INTERFACE_OVERLAP")
    tables = source["column_axial"]["r10_source"]["table_reads"]
    native_points = {r["ElmName"]:[float(r["Global"+d]) for d in "XYZ"]
                     for r in tables["Objects and Elements - Joints"]["rows"]}
    native_edge = {n for n,(x,y,z) in native_points.items() if abs(x-edge_x)<1e-7 and
                   abs(y-edge_y)<1e-7 and zlo-1e-7<=z<=zhi+1e-7}
    nodes = {uid:sorted({cell[k] for cell in tables["Objects and Elements - Areas"]["rows"]
                         if cell["ObjType"]=="Wall" and cell["ObjName"]==uid
                         for k in ("ElmJt1","ElmJt2","ElmJt3","ElmJt4") if cell.get(k) in native_edge}) for uid in PAIR}
    return {"physical_walls":corners,"edge_xy_m":[edge_x,edge_y],"z_range_m":[zlo,zhi],
            "physical_shared_corner_ids":sorted(corners["W22"].keys() & corners["W23"].keys()),
            "original_analysis_edge_nodes":nodes,"original_shared_analysis_nodes":sorted(set(nodes[PAIR[0]]) & set(nodes[PAIR[1]]))}


def _polygon(points):
    # Signed shoelace area on x-z gives the opposite sign to the global y normal.
    x0,y0,z0=points[0]
    _check(len(points)>=3 and all(abs(p[1]-y0)<1e-6 for p in points),"INTERFACE_BODY_OUT_OF_PLANE")
    xz=[(p[0]-x0,p[2]-z0) for p in points]
    edges=list(zip(xz,xz[1:]+xz[:1]))
    w=[a[0]*b[1]-b[0]*a[1] for a,b in edges]
    signed=fsum(w)
    _check(abs(signed)>1e-12,"INTERFACE_BODY_DEGENERATE_POLYGON")
    cx=fsum((a[0]+b[0])*v for (a,b),v in zip(edges,w))/(3*signed)
    cz=fsum((a[1]+b[1])*v for (a,b),v in zip(edges,w))/(3*signed)
    return abs(signed)/2,[cx+x0,y0,cz+z0],(-1 if signed>0 else 1)


def _whole_wall_balance(raw, body, edge, geometry, deck, owners=PAIR):
    if body is None:
        return {"status":"WHOLE_WALL_POINT_AXES_UNAVAILABLE","cases":[]}
    inputs=deck["wall_inputs"]
    _check(inputs["W22"]==inputs["W23"],"INTERFACE_BODY_PROPERTIES_DIFFER")
    coords=body["coords"]
    walls=geometry["physical_walls"]
    mesh_corners, areas = set(),defaultdict(list)
    for uid,elm,nodes in body["cells"]:
        _check(uid in owners and 3<=len(nodes)==len(set(nodes))<=4,"INTERFACE_BODY_CELL_INVALID")
        area,centroid,_=_polygon([coords[n] for n in nodes])
        for n in nodes:
            _check((uid,elm,n) not in mesh_corners,"INTERFACE_BODY_DUPLICATE_CORNER")
            mesh_corners.add((uid,elm,n))
        areas[uid].append((area,centroid))
    objects={}
    for uid in owners:
        label={"437":"W22","438":"W23"}[uid]
        # Use the original physical corner order, as read from the CSI object.
        area,center,normal=_polygon(list(walls[label].values()))
        _check(isclose(fsum(v for v,_ in areas[uid]),area,abs_tol=1e-6,rel_tol=1e-6) and all(
               isclose(fsum(v*xyz[j] for v,xyz in areas[uid])/area,center[j],abs_tol=2e-6) for j in (0,1,2)),
               "INTERFACE_BODY_MESH_AND_OBJECT_GEOMETRY_DIFFER")
        objects[uid]=(area,center,normal)
    groups,seen=defaultdict(list),set()
    for uid,elm,n,case,step,num,*v in body["rows"]:
        key=(uid,elm,n,case)
        _check((uid,elm,n) in mesh_corners and key not in seen and case in SIGNED_CASES and
               step=="Single Value" and num==0,"INTERFACE_BODY_NATIVE_STEP_OR_CORNER")
        seen.add(key)
        groups[case,uid,n in edge].append(joint_action_at_origin(v,body["axes"][n],coords[n],raw["origin_m"]))
    _check(len(seen)==len(mesh_corners)*len(SIGNED_CASES),"INTERFACE_BODY_MISSING_NATIVE_ACTION")
    rows=[]
    for case in SIGNED_CASES:
        pairs=[]
        for uid,(area,center,normal) in objects.items():
            wall=raw["walls"][PAIR[0]]
            weight=-area*wall["weight_kn_per_m2"]*raw["cases"][case]["weight_multiplier"]
            pressure=area*normal*wall["pressure_kn_per_m2"][case]
            loads=joint_action_at_origin([0.,pressure,weight,0.,0.,0.],IDENTITY,center,raw["origin_m"])
            boundaries=[[fsum(col) for col in zip(*groups[case,uid,on])] for on in (True,False)]
            _check(all(len(v)==6 for v in boundaries),"INTERFACE_BODY_BOUNDARY_POPULATION")
            pairs.append([*boundaries,list(loads)])
        terms_by_owner=list(zip(owners,pairs,strict=True))
        if len(owners)==2:
            combined=[[fsum((x,y)) for x,y in zip(a,b,strict=True)] for a,b in zip(*pairs,strict=True)]
            terms_by_owner.append(("W22+W23",combined))
        for owner,terms in terms_by_owner:
            residual=[fsum(column) for column in zip(*terms,strict=True)]
            limits=[max(BALANCE_ABS,BALANCE_REL*max(abs(v) for v in col)) for col in zip(*terms,strict=True)]
            rows.append({"case":case,"owner":owner,"native_interface":terms[0],"other_native_joint_actions":terms[1],
                         "independent_applied_body_load":terms[2],"residual":residual,"limits":limits,
                         "balanced":all(abs(v)<=l for v,l in zip(residual,limits))})
    return {"status":"WHOLE_WALL_EQUILIBRIUM_EVALUATED","control_volume":"Complete physical areas "+", ".join(owners),
            "actions":"All point-on-element actions, including both interface sides. The remainder includes the other corners and load paths.",
            "areas_m2":{u:v[0] for u,v in objects.items()},"native_corners":len(mesh_corners),"cases":rows}


def retained_interface_side(raw, body, geometry, deck):
    x,y=geometry["edge_xy_m"]
    lo,hi=geometry["z_range_m"]
    edge={n for n,(px,py,pz) in body["coords"].items() if abs(x-px)<1e-7 and abs(y-py)<1e-7 and lo-1e-7<=pz<=hi+1e-7}
    _check(edge,"RETAINED_W22_EDGE_MISSING")
    balance=_whole_wall_balance(raw,body,edge,geometry,deck,owners=("437",))
    groups=defaultdict(list)
    for uid,elm,n,case,step,num,*v in body["rows"]:
        if n not in edge:
            continue
        point=body["coords"][n]
        action=joint_action_at_origin(v,body["axes"][n],point,point)
        groups[case,point[2]].append((action[2],(point[0]-raw["origin_m"][0])*action[2],action[4],
                                      (point[2]-raw["origin_m"][2])*action[0]))
    curves={}
    for case in SIGNED_CASES:
        totals=[0.]*4
        curve=[]
        for key in sorted(k for k in groups if k[0]==case):
            totals=[fsum((a,fsum(col))) for a,col in zip(totals,zip(*groups[key],strict=True),strict=True)]
            curve.append({"z_m":key[1],"cumulative_fz_kn":totals[0],"cumulative_x_fz_knm":totals[1],
                          "cumulative_point_my_knm":totals[2],"cumulative_z_fx_knm":totals[3]})
        curves[case]=curve
    return {"edge_node_count":len(edge),"whole_wall_balance":balance,"vertical_edge_distributions":curves,
            "axes_source":raw["point_axes_source"],"measured_owner":"437"}


def project_interface(raw, data, geometry, deck):
    from .transition_design_trace import _base_rows
    corners = [tuple(r) for r in data["incident_corners"]]
    ids = set(corners)
    _check(ids and len(corners)==len(ids) and set(PAIR) <= {u for k,u,_,_ in ids if k=="Wall"},
           "NATIVE_INTERFACE_CORNER_INVENTORY")
    coords,matrices = data["coordinates"],data["matrices"]
    _check(set(coords)==set(matrices) and all(_vector(p,3) for p in coords.values()),"NATIVE_INTERFACE_POINTS")
    edge = {u:{n for _,owner,_,n in ids if owner==u} for u in PAIR}
    origin = raw["origin_m"]
    xwall = raw["walls"][PAIR[0]]["x_m"][1]
    _check(all(abs(p[0]-xwall)<1e-6 and abs(p[1]-origin[1])<1e-6 for p in coords.values()),
           "NATIVE_INTERFACE_COORDINATES")
    grouped, seen = defaultdict(list),set()
    for kind,uid,elm,node,case,step,num,*values in data["edge_rows"]:
        corner = (kind,uid,elm,node)
        identity = (*corner,case)
        _check(corner in ids and identity not in seen and case in SIGNED_CASES and step=="Single Value" and num==0,
               "NATIVE_INTERFACE_CASE_OR_DUPLICATE")
        seen.add(identity)
        xyz=coords[node]
        at_node = joint_action_at_origin(values,matrices[node],xyz,xyz)
        at_o = joint_action_at_origin(values,matrices[node],xyz,origin)
        first = (xyz[0]-origin[0])*at_node[2]
        z_fx = (xyz[2]-origin[2])*at_node[0]
        grouped[case,uid,xyz[2]].append((*at_o,first,at_node[4],z_fx))
    _check(len(seen)==len(ids)*len(SIGNED_CASES),"NATIVE_INTERFACE_FORCE_POPULATION")
    results = {}
    for case in SIGNED_CASES:
        actions = {}
        for uid in sorted({uid for _,uid,_,_ in ids}):
            sums = [0.]*9
            curve=[]
            for key in sorted(k for k in grouped if k[:2]==(case,uid)):
                values=[fsum(v) for v in zip(*grouped[key],strict=True)]
                sums=[fsum((a,b)) for a,b in zip(sums,values,strict=True)]
                curve.append({"z_m":key[2],"fz_kn":values[2],"cumulative_fz_kn":sums[2],
                              "cumulative_x_fz_knm":sums[6]})
            actions[uid]={"global_at_origin":dict(zip(GLOBAL,sums[:6],strict=True)),
                          "x_fz_knm":sums[6],"direct_my_knm":sums[7],"z_fx_knm":sums[8],"distribution":curve}
        results[case]=actions
    at,base=_base_rows(data["base_reactions"],(*SIGNED_CASES,"RSX","RSY"))
    return {"capture_sha256":data["capture_sha256"],"file_sha256":data["file_sha256"],
            "archived_controls":data["controls"],"model_generation":"NEW_LOCKED_NATIVE_READ",
            "base_reference_m":at,"base_reactions":base,"tables":data["tables"],
            "w23_mesh":data["w23_mesh"],"edge_node_counts":{u:len(v) for u,v in edge.items()},"shared_edge_node_ids":sorted(edge[PAIR[0]]&edge[PAIR[1]]),
            "coincident_distinct_ids":[sorted(ns) for p in sorted(set(tuple(v) for v in coords.values()))
                                       if len(ns:=[n for n in coords if tuple(coords[n])==p])>1],
            "auto_edge":data["walls"],"incident_area_owners":sorted({u for _,u,_,_ in ids}),
            "incident_frame_objects":sorted({row["ObjName"] for row in data["incident_frames"]}),
            "native_corner_count":len(corners),"edge_cases":results,
            "sign_convention":"Native point actions on each area, rotated to global and transported to the same origin.",
            "whole_wall_balance":_whole_wall_balance(raw,data.get("whole_walls"),set(coords),geometry,deck),
            "constraint_force_partition":"Separate generated-constraint forces require independent native ownership."}
