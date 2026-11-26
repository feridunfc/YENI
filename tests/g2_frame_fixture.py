"""Independent two-storey frame statics and source tables for the ordinary pipeline.

The in-plane translations of each floor are rigid. Beams and columns are
axially inextensible for the first-order bending solution. Base rotations and
translations are restrained. Vertical equilibrium recovers column compression.
Coordinates are metres, forces kN, moments kN m and rotations radians.
"""
from copy import deepcopy
from hashlib import sha256
import json
from math import fsum

import numpy as np

import vertical_slice_fixture as v
from tbdy_next.engineering.design_scenario import _digest, _source_data

CORNERS = ((0,0),(5,0),(0,5),(5,5))
SPANS = ((0,1),(2,3),(0,2),(1,3))
STOREYS = (1,2)
EC = 33_000_000.


def frame_actions(widths, height, beam_depth, load, *, stiffness_factors=(.7,.35)):
    """Assemble floor translations and independent column-end rotations.

    The second solution eliminates rotations first, independently checking all
    floor translations. Each element also supplies its two end actions for the
    joint moment and storey shear equilibrium checks below.
    """
    directions = []
    checks = []
    for axis in (0,1):
        stiffness = np.zeros((10,10))
        elements = []
        def element(key, dofs, length, ei):
            l = length
            matrix = ei/l**3*np.array(((12,6*l,-12,6*l),(6*l,4*l*l,-6*l,2*l*l),
                                      (-12,-6*l,12,-6*l),(6*l,2*l*l,-6*l,4*l*l)))
            for i, row in enumerate(dofs):
                for j, col in enumerate(dofs):
                    if row is not None and col is not None:
                        stiffness[row,col] += matrix[i,j]
            elements.append((key,dofs,matrix))
        def rotation(floor, node):
            return 2+4*(floor-1)+node
        for floor in STOREYS:
            for node, width in enumerate(widths):
                element(("C",floor,node),
                        (floor-2 if floor>1 else None,rotation(floor-1,node) if floor>1 else None,
                         floor-1,rotation(floor,node)), height, stiffness_factors[0]*EC*width**4/12)
            for index in (2*axis,2*axis+1):
                i,j = SPANS[index]
                element(("B",floor,index),(None,rotation(floor,i),None,rotation(floor,j)),
                        5., stiffness_factors[1]*EC*.5*beam_depth**3/12)
        forces = np.array([.4*load,.6*load]+[0.]*8)
        solution = np.linalg.solve(stiffness,forces)
        rr = stiffness[2:,2:]
        condensed = stiffness[:2,:2]-stiffness[:2,2:]@np.linalg.solve(rr,stiffness[2:,:2])
        recovered = np.linalg.solve(condensed,forces[:2])
        residual = stiffness@solution-forces
        check = {"axis":"XY"[axis],"floor_loads_kn":forces[:2].tolist(),
                 "floor_displacements_m":solution[:2].tolist(),
                 "maximum_rotation_equilibrium_residual_knm":max(map(abs,residual[2:])),
                 "maximum_floor_balance_residual_kn":max(map(abs,residual[:2])),
                 "condensation_displacement_error_m":max(abs(recovered-solution[:2]))}
        states = {}
        for key,dofs,k in elements:
            states[key] = (k@np.array([solution[i] if i is not None else 0. for i in dofs])).tolist()
        check["storey_shear_residuals_kn"] = [abs(-fsum(states["C",f,n][0] for n in range(4))
                                                -sum(forces[f-1:2])) for f in STOREYS]
        if (np.linalg.norm(residual,np.inf)>1e-7 or max(check["storey_shear_residuals_kn"])>1e-7
                or check["condensation_displacement_error_m"]>1e-11):
            raise ArithmeticError("FRAME_REFERENCE_EQUILIBRIUM")
        directions.append(states)
        checks.append(check)
    return directions,checks


def frame_source(*, lateral=1550., weak=.55, beam_depth=1.25, weak_as=.00275, strong_as=.0014,
                 height=4.5, tie=12, tie_pitch=65, exhaust=False):
    raw, request = v.source_and_request(two_story=True)
    data = json.loads(raw)
    widths = (.8,.8,.8,weak)
    planes, checks = frame_actions(widths,height,beam_depth,lateral)
    geo = data["geometry_capture"]["tables"]
    feature = data["column_axial"]
    r10 = feature["r10_source"]["table_reads"]
    b1 = data["vs06_b1_geometry_source"]
    cols, beams, assignments, offsets, insertion, analysis, stations, releases, sums = ([] for i in range(9))
    col_rows, beam_rows = {}, {}
    corners = [("F"+str(f)+str(n),"Base" if not f else "S"+str(f),str(x),str(y),str(f*height))
               for f in (0,1,2) for n,(x,y) in enumerate(CORNERS)]

    point_table = v.table("Point Object Connectivity","UniqueName Story X Y Z",corners,dict.fromkeys("XYZ","m"))
    def put(record, values):
        record["rows"] = [dict(zip(record["fields"],row,strict=True)) for row in values]
        record["row_count"] = len(record["rows"])
    def add_frame(key, story, kind, section, start, end, off_i, off_j):
        assignments.append((story,key,kind,section,section,"0",key))
        offsets.append((story,key,str(off_i),str(off_j)))
        insertion.append((key,story,key,"10 (Centroid)" if kind=="Column" else "8 (Top Center)","No","No"))
    secname="Cweak"
    for table in (geo["RECTANGULAR_SECTIONS"],geo["SECTION_SUMMARY"]):
        for row in table["rows"]:
            if row["Name"]=="B60x50":
                if "Area" in row: row["Area"]=str(.5*beam_depth)
                else: row.update(t2=".5",t3=str(beam_depth))
        extra=deepcopy(next(row for row in table["rows"] if row["Name"]=="C80"))
        extra["Name"]=secname
        if "Area" in extra: extra["Area"]=str(weak**2)
        else: extra.update(t2=str(weak),t3=str(weak))
        table["rows"].append(extra)
        table["row_count"]=len(table["rows"])
    for record in feature["pmm_section_source"]["table_reads"].values():
        if record["rows"] and record["rows"][0].get("Name")=="C80":
            record["rows"].append(dict(record["rows"][0],Name=secname,NumBars2Dir="6",NumBars3Dir="6"))
            record["row_count"]+=1
    def active(combo):
        if combo=="G": return (0.,0.)
        sign = 1 if "+" in combo else -1
        return (sign,sign*.3) if combo.endswith("X") else (.3*sign,sign)
    for f in STOREYS:
        story="S"+str(f)
        for n,width in enumerate(widths):
            key="C"+str(f)+str(n)
            start,end="F"+str(f-1)+str(n),"F"+str(f)+str(n)
            add_frame(key,story,"Column",secname if n==3 else "C80",start,end,0.,beam_depth)
            cols.append((story,key,key,start,end,str(height)))
            analysis.append((story,"Frame",key,key+"-elm",start,end))
            stations.append((story,key,"Min Stations","None","3"))
            vectors=[]
            # Applied gravity is nodal. Beam end shears under sway also produce
            # compression or uplift, accumulated down from the roof.
            gravity_per_floor = 1650. if n!=3 else 1175.
            for combo in v.COMBINATIONS:
                sx,sy=active(combo)
                axial=(3-f)*gravity_per_floor
                for axis,factor in enumerate((sx,sy)):
                    for level in range(f,3):
                        for b in (axis*2,axis*2+1):
                            if n in SPANS[b]:
                                idx=SPANS[b].index(n)
                                # positive lateral rotation tilts a horizontal beam downward
                                axial -= factor*planes[axis]["B",level,b][idx*2]
                shear_x=-sx*planes[0]["C",f,n][0]
                shear_y=-sy*planes[1]["C",f,n][0]
                for z in (0.,(height-beam_depth)/2,height-beam_depth):
                    mx=sx*planes[0]["C",f,n][1]-z*planes[0]["C",f,n][0]*sx
                    my=sy*planes[1]["C",f,n][1]-z*planes[1]["C",f,n][0]*sy
                    vectors.append((key,z,key+"-elm",z,combo,"Single Value",0.,-axial,shear_x,shear_y,0.,-my,mx))
            col_rows[key]=v._rowset(vectors)
        for b,(n,m) in enumerate(SPANS):
            key="B"+str(f)+str(b)
            start,end="F"+str(f)+str(n),"F"+str(f)+str(m)
            add_frame(key,story,"Beam","B60x50",start,end,widths[n]/2,widths[m]/2)
            beams.append((story,key,key,start,end,"5"))
            releases.append((key,"No","No","No","No"))
            beam_vectors=[]
            for pos,nd in ((widths[n]/2,n),(5-widths[m]/2,m)):
                axis=b//2
                vr, mi = planes[axis]["B",f,b][:2]
                demand = abs(mi-pos*vr)
                # Both signs occur. Size the design-book steel from the physical face
                # moment using a deliberately short 0.85d lever. The audit then uses
                # actual bar centroids and compares both selected signed capacities.
                area=max(demand/(365000.*.85*(beam_depth-.08)),
                         weak_as if (f==1 and nd==3) else strong_as)
                sums.append((story,key,key,"B60x50",str(pos),"No Message","G+EX",".0005",str(area),
                             "G+EX",".0005",str(area),"G","0",str(area),str(area),"No Message","No Message"))
                for combo in v.COMBINATIONS:
                    axis=b//2
                    factor=active(combo)[axis]
                    vr,mi=planes[axis]["B",f,b][:2]
                    beam_vectors.append((key,pos,key+"-elm",pos,combo,"Single Value",0.,0.,factor*vr,0.,0.,0.,factor*(mi-pos*vr)))
            beam_rows[key]=v._rowset(beam_vectors)
    put(geo["FRAME_ASSIGNMENTS"],assignments)
    put(geo["SECTION_ASSIGNMENTS"],[(x[0],x[1],x[3]) for x in assignments])
    put(geo["COLUMN_CONNECTIVITY"],cols)
    put(geo["BEAM_CONNECTIVITY"],beams)
    for table,records in ((v.ANALYSIS_FRAME_ELEMENTS,analysis),(v.FRAME_OUTPUT_STATIONS,stations),
                          (v.END_OFFSETS,offsets),(v.FRAME_INSERTION,insertion),(v.RELEASES,releases),
                          (v.BEAM_DESIGN_SUMMARY,sums)):
        put(r10[table],records)
    b1["table_reads"]["Point Object Connectivity"]=deepcopy(point_table)
    b1["payload_sha256"]=v.digest({k:x for k,x in b1.items() if k!="payload_sha256"})
    put(r10["Objects and Elements - Joints"],[(u,u,"Joint",s,x,y,z) for u,s,x,y,z in corners])
    put(r10[v.FLOOR_CONNECTIVITY],[("MAT","Base","MAT","F00","F01","F03","F02")])
    put(r10[v.AREA_ELEMENTS],[("Base","M1","Floor","MAT","MAT","F00","F01","F03"),
                               ("Base","M2","Floor","MAT","MAT","F03","F02","F00")])
    dr=data["r08_second_order_source"]
    rs=dr["spectrum_source"]["table_reads"]
    for row in rs["Story Definitions"]["rows"]: row["Height"]=str(height)
    for row in rs["Story Forces"]["rows"]:
        sx,sy=(1.,.3) if row["OutputCase"]=="RSX" else (.3,1.)
        total=lateral*(.6 if row["Story"]=="S2" else 1.)
        row.update(VX=str(sx*total),VY=str(sy*total))
    for row in rs["Story Max Over Avg Drifts"]["rows"]:
        i=int(row["Story"][-1])-1
        disp=checks["XY".index(row["Direction"])]["floor_displacements_m"]
        scale=1. if row["OutputCase"]=="RS"+row["Direction"] else .3
        row["Avg Drift"]=str(scale*(disp[i]-(disp[i-1] if i else 0.))/height)
    wt=dr["weight_source"]["table_reads"]
    weight=3*1650+1175
    for row in wt["Story Forces"]["rows"]: row["P"]=str(weight*(3-int(row["Story"][-1])))
    wt["Base Reactions"]["rows"][0]["FZ"]=str(2*weight)
    dr["spectrum_source"]=v.generic(rs)
    dr["weight_source"]=v.generic(wt)
    data["vs05_delta_source"]=v.generic({**deepcopy(rs),"Point Object Connectivity":point_table})
    feature["r10_source"]["beam_force_source"]["rowsets"]=beam_rows
    feature["force_source"]["rowsets"]=col_rows
    from tbdy_next.etabs_geometry import POINT_RESTRAINT_SCHEMA
    base_nodes=["F0"+str(n) for n in range(4)]
    feature["r10_source"]["point_restraints"]={"schema":POINT_RESTRAINT_SCHEMA,"point_ids":base_nodes,
        "observations":{u:{"local_dof":[True]*6,"axes_angles_deg":[0.,0.,0.],"advanced_axes":False} for u in base_nodes},
        "errors":{}}
    data["example_context"]={"classification":"OFFLINE_ELASTIC_FRAME_EXAMPLE","origin":"INDEPENDENT_STIFFNESS_SOLUTION",
                             "equilibrium":checks,"corner_coordinates_m":CORNERS,"heights_m":[height,height]}
    basis=request["second_order_basis"]
    base=basis["members"]["C1"]
    basis["members"]={u:deepcopy(base) for u in sorted(col_rows)}
    _, gross = frame_actions(widths,height,beam_depth,lateral,stiffness_factors=(1.,1.))
    # TS 500 Eq. 7.13. Use all axial compression, gross-stiffness displacement
    # and actual interstorey motion for each loaded floor and direction.
    for f in STOREYS:
        for axis, statics in enumerate(checks):
            disp=gross[axis]["floor_displacements_m"]
            statics["gross_floor_displacements_m"]=disp
            delta=disp[f-1]-(disp[f-2] if f>1 else 0.)
            shear=sum(statics["floor_loads_kn"][f-1:])
            values=[]
            for combo in v.COMBINATIONS:
                component=abs(active(combo)[axis])
                if not component:
                    continue
                compression=0.
                for n in range(4):
                    rs=col_rows["C"+str(f)+str(n)]
                    j=next(i for i,(c,z) in enumerate(zip(rs["LoadCase"],rs["ObjSta"])) if c==combo and z==0.)
                    compression+=max(0.,-rs["P"][j])
                values.append(1.5*compression*abs(component*delta)/(height*component*shear))
            if not values or max(values)>.05:
                raise ValueError("FRAME_LATERAL_STABILITY_INDEX_EXCEEDED")
            statics.setdefault("non_sway_indices",{})["S"+str(f)]=max(values)
    for entry in basis["members"].values():
        for axis in entry["axes"].values():
            axis["decision_reference"]="Full physical frame displacement and complete compression, TS 500 stability index <= 0.05; conservative non-sway unit length factor."
    native=_digest(_source_data(data))
    request["analysis_basis"]["source_data_sha256"]=basis["source_data_sha256"]=native
    request["scenario_id"]="g2-frame-exhausted" if exhaust else "g2-frame"
    request["column_selection"].update(tie_diameter_preference_mm=[tie],stirrup_confinement_spacing_mm=tie_pitch,
                                       stirrup_span_spacing_mm=tie_pitch)
    if exhaust:
        request["column_selection"].update(max_rho=.011,allowed_longitudinal_diameters_mm=[16,20,22])
    data_bytes=json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
    request["parent_input_sha256"]=sha256(data_bytes).hexdigest()
    return data_bytes,request
