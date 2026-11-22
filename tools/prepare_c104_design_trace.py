"""Bind C104 assigned design rows, signed base reactions, and optional new W22/W23 native reads."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import shlex

from prepare_c104_transition import FRAME, PARENT_SHA, native_slice, one
from prepare_c29_story_balance import arrays, checksum, field, read, require
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.engineering.coupled_wall_transition import DESIGN_SCHEMA, IDENTITY, SIGNED_CASES, normalize_transition
from tbdy_next.engineering.design_scenario import _digest, _source_data
from tbdy_next.engineering.mixed_demands import linear_coefficients
from tbdy_next.engineering.transition_design_trace import SCHEMA


def read_deck(path, assigned):
    rows = [shlex.split(line.strip()) for line in path.read_bytes().decode("latin-1").splitlines()
            if line.startswith("  ") and line.strip() and not line.strip().startswith("$")]
    graph, cases = {}, {}
    for row in rows:
        if row[0] == "LOADCASE":
            cases[row[1]] = True
        if row[0] == "COMBO":
            group = graph.setdefault(row[1], {"rows":[]})
            if row[2] == "TYPE":
                group["operator_etabs"] = row[3]
            if row[2] in ("LOADCASE","LOADCOMBO"):
                group["rows"].append({"ref_type":"CASE" if row[2]=="LOADCASE" else "COMBO",
                                      "ref":row[3],"factor":field(row,"SF")})
    combos = {name:{c:float(v) for c,v in linear_coefficients(name,graph,cases).items()} for name in assigned}
    # The wider free body uses whole physical W22/W23 objects with identical property and load assignments.
    wall_inputs = {}
    for label in ("W22","W23"):
        assign = one(r for r in rows if r[:3]==["AREAASSIGN",label,"+0.00"])
        require(field(assign,"CARDINALPOINT")=="MIDDLE" and
                not set(assign)&{"ANG","ANGLE","ADVANCEDAXES","OFFSET","WMOD","WEIGHTMOD"}, "Unsupported coupled wall assignment")
        loads = [r[3:] for r in rows if r[:3]==["AREALOAD",label,"+0.00"]]
        wall_inputs[label] = {"section":field(assign,"SECTION"),"loads":sorted(loads)}
    require(wall_inputs["W22"]==wall_inputs["W23"], "Whole-wall loads or properties differ; independent model basis required")
    definitions = {}
    for axis,accel in (("X","U1"),("Y","U2")):
        eq, rs = "LC_EQ"+axis, "RS"+axis
        eqrow = one(r for r in rows if r[:2]==["SEISMIC",eq])
        case = one(r for r in rows if r[:3] == ["LOADCASE",rs,"TYPE"])
        load = one(r for r in rows if r[:3] == ["LOADCASE",rs,"ACCEL"])
        function = one(r for r in rows if r[:3] == ["FUNCTION",field(load,"FUNC"),"FUNCTYPE"])
        require(eqrow[2]=="TSC-2018" and field(eqrow,"DIR")==axis and field(eqrow,"PERIODTYPE")=="USER"
                and case[3]=="Response Spectrum" and load[3]==accel and field(function,"SPECTYPE")=="TSC-2018",
                "Unsupported equivalent-static or response-spectrum direction")
        definitions[axis]={"spectrum_case":rs,"equivalent_case":eq,"function":function[1],"modal_case":field(case,"MODALCASE"),
                           "user_period_s":float(field(eqrow,"USERT")),"scale_m_s2":float(field(load,"SF")),
                           "load_name":accel,"top_story":field(eqrow,"TOPSTORY"), "bottom_story":field(eqrow,"BOTTOMSTORY"),
                           "reduced_function_parameters":{k:float(field(function,k)) for k in ("R","D","I","SS","S1","TL")}}
    mass = one(r for r in rows if r[0]=="MASSSOURCE" and field(r,"ISDEFAULT")=="Yes")
    return {"export_sha256":checksum(path),"combinations":combos,"directions":definitions,
            "wall_inputs":wall_inputs,"mass_source":mass,"mass_patterns":{r[2]:float(r[3]) for r in rows if r[:2]==["MASSSOURCELOAD",mass[1]]}}


def assigned_rows(capture, level, assigned):
    require(capture["units_code"]==6 and not capture["errors"] and
            {n for n,on in capture["output_selection_during"]["combos"].items() if on} == set(assigned),
            "Captured combo selection or units differ from the assignment")
    coords = level["coordinates"]
    segments = {name:(i,j) for name,i,j in level["frame_segments"]}
    result = []
    for uid,station,elm,es,case,step,num,*v in native_frame_force_rows(capture["rowsets"][FRAME],FRAME):
        if elm not in segments or case not in assigned:
            continue
        i,j = segments[elm]
        for end,node,s in (("I",i,0),("J",j,coords[j][2]-coords[i][2])):
            if abs(es-s)<2e-6:
                require(abs(station-coords[node][2]-5.15)<2e-6, "Frame station and physical cut differ")
                result.append([uid,elm,end,case,step,num,*v])
    return result


def retained_w22(directory, shells):
    mesh=read(directory/"analysis_mesh.json")
    cells=[[r["ObjName"],r["ElmName"],[r["ElmJt"+str(i)] for i in (1,2,3,4)]]
           for r in mesh["area_elements"] if r["ObjType"]=="Wall" and r["ObjName"]=="437"]
    nodes={n for _,_,ring in cells for n in ring}
    return {"cells":cells, "coords":{n:mesh["joint_coords"][n] for n in nodes},
            "axes":dict.fromkeys(nodes,IDENTITY), "rows":list(arrays(shells["437"],12))}


def w23_mesh(mesh):
    coords=mesh["coordinates"]
    rings=sorted(sorted(coords[n] for k in ("ElmJt1","ElmJt2","ElmJt3","ElmJt4") if (n:=r.get(k)) in coords)
                 for r in mesh["area_cells"] if r["ObjType"]=="Wall" and r["ObjName"]=="438")
    require(rings and all(len(ring)>=3 for ring in rings),"W23 has no complete native cells")
    return {"cell_count":len(rings),"coordinate_rings_sha256":_digest(rings)}


def cross_levels(folder, control, original_sha, assigned):
    seal=read(folder/"both-complete.json")
    require(seal["a_d_capture"]==checksum(control/"both-complete.json") and seal["original_sha"]==original_sha,
            "Crossed run has another original or A/D reference")
    levels={}
    for name,vertical,horizontal in (("B",2,1),("C",1,2)):
        path=folder/name
        completed=read(path/"finished.json")
        require(checksum(path/"finished.json")==seal["levels"][name] and completed["case_count"]==15
                and completed["inputs_match_reference"] is True and completed["vertical"]==vertical and completed["horizontal"]==horizontal
                and all(checksum(path/f)==completed[k] for f,k in (("interface-mesh.json","edge_mesh_sha256"),
                        ("wall-policies.json","wall_policy_sha256"),("mesh_assignments.json","mesh_assignment_sha256"))),
                "Crossed source controls changed")
        assignments=read(path/"mesh_assignments.json")
        require([(int(assignments[u]["Nv"]),int(assignments[u]["Nh"])) for u in ("436","437")]
                == [(103*vertical,7*horizontal),(30*vertical,4*horizontal)],"Unexpected crossed mesh divisions")
        level=native_slice(path,.05/vertical)
        levels[name]={"level":level,"assigned_frame_rows":assigned_rows(read(path/"frame_forces.json"),level,assigned),
                      "base_reactions":read(path/"static_shell_forces.json")["base_react"],
                      "w23_mesh":w23_mesh(read(path/"interface-mesh.json")),"policies":read(path/"wall-policies.json"),
                      "vertical":vertical,"horizontal":horizontal,"capture_sha256":seal["levels"][name],
                      "input_export_sha256":completed["input_export_sha256"]}
    return {"schema":"tbdy.next.c104-crossed-mesh.v1","pair_sha256":checksum(folder/"both-complete.json"),"models":levels}


def interface_slice(folder, name, level, assigned):
    seal = read(folder/"complete.json")
    require(seal["level"]==name and seal["restored"] is True and
            seal["archive_frame_sha256"]==level["archives"]["frame_forces"] and
            all(Path(f).name == f and checksum(folder/f) == sha for f,sha in seal["file_hashes"].items()),
            "Incomplete or changed native interface capture")
    mesh = read(folder/"interface-mesh.json")
    coords = mesh["coordinates"]
    edge = set(mesh["edge_points"])
    # Include every native corner incident on the interface. A coincident ID remains distinct.
    owners = defaultdict(set)
    for cell in mesh["area_cells"]:
        for k in ("ElmJt1","ElmJt2","ElmJt3","ElmJt4"):
            n = cell.get(k)
            if n in edge:
                owners[cell["ObjType"],cell["ObjName"]].add((cell["ElmName"],n))
    require(len({uid for _,uid in owners}) == len(owners), "Ambiguous area namespace")
    bodies = {cell["ElmName"]:[n for k in ("ElmJt1","ElmJt2","ElmJt3","ElmJt4") if (n:=cell.get(k)) in coords]
              for cell in mesh["area_cells"] if cell["ObjType"]=="Wall" and cell["ObjName"] in ("437","438")}
    body_rows = []
    rows = []
    for (kind,uid),corners in sorted(owners.items()):
        for obj,elm,n,case,step,num,*v in arrays(read(folder/("area-"+uid+".json")),12):
            if uid in ("437","438") and case in SIGNED_CASES:
                require(obj==uid and elm in bodies and n in bodies[elm],"Whole-wall result outside native mesh")
                body_rows.append([uid,elm,n,case,step,num,*v])
            if (elm,n) in corners and case in SIGNED_CASES:
                require(obj==uid, "Native area result belongs to another object")
                rows.append([kind,obj,elm,n,case,step,num,*v])
    matrices = read(folder/"point-matrices.json")
    body_nodes={n for ns in bodies.values() for n in ns}
    body = None
    if body_nodes <= matrices.keys():
        body = {"cells":[[c["ObjName"],c["ElmName"],bodies[c["ElmName"]]] for c in mesh["area_cells"]
                         if c["ObjType"]=="Wall" and c["ObjName"] in ("437","438")],
                "coords":{n:coords[n] for n in body_nodes},"axes":{n:matrices[n] for n in body_nodes},"rows":body_rows}
    keys=("Story Forces","Mass Summary by Story","Centers Of Mass And Rigidity","Story Max Over Avg Drifts")
    tables={k:read(folder/(k+".json")) for k in keys if k+".json" in seal["file_hashes"]}
    # Preserve the actual native element IDs and measure the re-solve separately from the old A/D solves.
    frame = assigned_rows(read(folder/"design-frame-forces.json"),level,assigned) if seal["archived_controls_match"] else []
    return {"capture_sha256":checksum(folder/"complete.json"),"file_sha256":seal["file_sha256"],
            "controls":read(folder/"archived-controls.json"),"base_reactions":read(folder/"base-reactions.json"),
            "tables":tables,"w23_mesh":w23_mesh(mesh), "walls":read(folder/"wall-policies.json"),"assigned_frame_rows":frame,
            "coordinates":{n:coords[n] for n in sorted(edge)}, "matrices":{n:matrices[n] for n in sorted(edge)},
            "incident_corners":[[kind,u,e,n] for (kind,u),es in sorted(owners.items()) for e,n in sorted(es)],
            "incident_frames":mesh["incident_frames"],"edge_rows":rows,"whole_walls":body}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("source","scenario","mesh-run","deck","out"):
        p.add_argument("--"+arg,type=Path,required=True)
    p.add_argument("--cross-run",type=Path,help="Optional crossed B/C meshes bound to the same A/D read.")
    p.add_argument("--interface-run",type=Path,help="Completed pair with both native capture seals.")
    p.add_argument("--interface-fine",type=Path,help="Independent completed D capture directory.")
    p.add_argument("--interface-coarse",type=Path,help="Independent completed A capture directory.")
    a=p.parse_args()
    require(not a.interface_run or not (a.interface_fine or a.interface_coarse), "Select a pair or individual captures")
    parent=read(a.source)
    scenario=read(a.scenario)
    raw=scenario["coupled_wall_transition"]
    require(checksum(a.source)==PARENT_SHA==scenario["parent_input_sha256"] and
            raw["source_data_sha256"] == _digest(_source_data(parent)), "Wrong original transition parent")
    normalize_transition(raw,source_data_sha256=raw["source_data_sha256"])
    assigned=parent["column_axial"]["request"]["combinations"]
    packet={"schema":SCHEMA,"deck":read_deck(a.deck,assigned),"levels":[]}
    for name,side,level in zip(("mesh-1","mesh-2"),("coarse","fine"),raw["levels"],strict=True):
        folder=a.mesh_run/name
        require(all(checksum(folder/(k+".json"))==v for k,v in level["archives"].items()), "Archived solve changed")
        status=read(folder/"case_statuses.json")
        require(status["return"] == 0 and all(v==4 for k,v in status["statuses"].items() if not k.startswith("~")),
                "Physical cases incomplete")
        shells=read(folder/"static_shell_forces.json")
        item={"generation_sha256":level["generation_sha256"],"assigned_frame_rows":assigned_rows(read(folder/"frame_forces.json"),level,assigned),
              "base_reactions":shells["base_react"],"retained_w22":retained_w22(folder,shells)}
        if a.interface_run:
            both=read(a.interface_run/"both-complete.json")
            require(checksum(a.interface_run/side/"complete.json")==both[side+"_capture"] and
                    both["original_edb_sha256"]==raw["original_edb_sha256"],"Paired reader seal differs")
            item["interface_read"]=interface_slice(a.interface_run/side,name,level,assigned)
        else:
            capture_dir=a.interface_coarse if side=="coarse" else a.interface_fine
            if capture_dir:
                item["interface_read"]=interface_slice(capture_dir,name,level,assigned)
        packet["levels"].append(item)
    if a.cross_run:
        require(a.interface_run is not None,"Crossed levels require the corresponding A/D pair")
        packet["crossed_meshes"]=cross_levels(a.cross_run,a.interface_run,raw["original_edb_sha256"],assigned)
    packet["sha256"]=_digest(packet)
    raw["schema"]=DESIGN_SCHEMA
    raw["design_trace"]=packet
    scenario["scenario_id"]="C104-assigned-design-and-interface"
    normalize_transition(raw,source_data_sha256=raw["source_data_sha256"])
    with a.out.open("x",encoding="utf-8") as f:
        json.dump(scenario,f,ensure_ascii=False,allow_nan=False)

if __name__=="__main__":
    main()
