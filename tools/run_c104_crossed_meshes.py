"""Run the B/C crossed C104 response study in separate private copies using the original 15 cases."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from shutil import copyfile
from socket import AF_INET,SOCK_STREAM,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,socket

from read_c104_design_interface import (MESH, REFERENCE, digest, editing_rows, guard_model, interface_geometry,
                                        native, require, save, states, text_shape)
from tbdy_next.etabs_source_gateway_windows import model_file, read_table
from tbdy_next.frame_force_capture import capture_frame_forces, get_results_setup_state, restore_results_setup_state
from tbdy_next.live_etabs import _with_etabs

BASE_DIVISIONS={"436":(103,7),"437":(30,4)}
CORE=("211",)
WALLS=("436","437")

def selected_shell_data(sap):
    setup=sap.Results.Setup
    _,names=native(sap.LoadCases.GetNameList(0,[],0),"Cases GetNameList")
    _,combos=native(sap.RespCombo.GetNameList(0,[]),"Combinations GetNameList")
    before=get_results_setup_state(setup,cases=names,combos=combos)
    during={"cases":{n:n in REFERENCE for n in names},"combos":dict.fromkeys(combos,False)}
    try:
        native(setup.DeselectAllCasesAndCombosForOutput(),"Reset ETABS output selection")
        for n in REFERENCE:
            native(setup.SetCaseSelectedForOutput(n,True),"Select "+n)
        require(get_results_setup_state(setup,cases=names,combos=combos)==during,"Wrong private output selection")
        a={u:native(sap.Results.AreaJointForceShell(u,0,0,*([] for _ in range(12))),"Read wall shell forces "+u)
           for u in WALLS}
        a["base_react"]=native(sap.Results.BaseReact(0,*([] for _ in range(9)),0.,0.,0.),"BaseReact")
    finally:
        restore_results_setup_state(setup,before)
        require(get_results_setup_state(setup,cases=names,combos=combos)==before,"Output state restoration failed")
    return a


def collect_mesh(sap):
    db=sap.DatabaseTables
    af=read_table(db,"Objects and Elements - Areas")
    ff=read_table(db,"Objects and Elements - Frames")
    pt=read_table(db,"Objects and Elements - Joints")
    require(all(x["status"]=="CAPTURED" for x in (af,ff,pt)),"Missing native analysis mesh")
    walls=[r for r in af["rows"] if r["ObjType"]=="Wall" and r["ObjName"] in WALLS]
    elements=[r for r in ff["rows"] if r["ObjType"]=="Frame" and r["ObjName"] in CORE]
    wanted={r[k] for r in walls for k in ("ElmJt1","ElmJt2","ElmJt3","ElmJt4") if r.get(k) not in (None,"None","")}
    wanted|={r[k] for r in elements for k in ("ElmJtI","ElmJtJ")}
    coords={r["ElmName"]:[float(r["Global"+d]) for d in "XYZ"] for r in pt["rows"] if r["ElmName"] in wanted}
    require(wanted==set(coords),"Missing mesh joints")
    edges={u:set() for u in WALLS}
    for r in walls:
        ns=[r[k] for k in ("ElmJt1","ElmJt2","ElmJt3","ElmJt4") if r.get(k) not in (None,"None","")]
        for a,b in zip(ns,ns[1:]+ns[:1]):
            edges[r["ObjName"]].add(frozenset((a,b)))
    parts=[]
    for r in elements:
        if r["ObjName"]=="211":
            ns=(r["ElmJtI"],r["ElmJtJ"])
            parts.append({"element_id":r["ElmName"],"nodes":ns,
                          "z_m":[coords[h][2] for h in ns],
                          "exact_common_edge_walls":[u for u in WALLS if frozenset(ns) in edges[u]]})
    require(parts,"Empty C104 frame mesh")
    return {"area_elements":walls,"frame_elements":elements,"joint_coords":coords,"C104_segments":parts}



def load(p):
    return json.loads(p.read_bytes())

def cross_inputs(rows,vscale,hscale):
    out={r["UniqueName"]:dict(r) for r in rows}
    for uid,(nv,nh) in BASE_DIVISIONS.items():
        out[uid].update(Nv=str(nv*vscale),Nh=str(nh*hscale))
    return out

def solve(sap,root,model,original,reference_export,archive_root,pair):
    def exact_copy(active):
        guard_model(active,model,original)
    exact_copy(sap)
    base=load(pair/"both-complete.json")
    fine=load(pair/"fine/complete.json")
    require(digest(model)==base["fine_edb_sha256"] and digest(original)==base["original_edb_sha256"]
            and digest(pair/"fine/complete.json")==base["fine_capture"] and fine["archived_controls_match"],
            "Original or approved D generation changed")
    combos=load(pair/"fine/design-frame-forces.json")["output_selection_during"]["combos"]
    combos=tuple(n for n,on in combos.items() if on)
    require(len(combos)==11,"Unexpected assigned design population")
    expected=load(archive_root/"mesh-2/mesh_assignments.json")
    physical=[n for n,s in load(archive_root/"mesh-2/case_statuses.json")["statuses"].items() if not n.startswith("~") and s==4]
    require(len(physical)==15,"Unexpected existing load population")
    switched=False
    try:
        for name,vscale,hscale in (("B",2,1),("C",1,2)):
            directory=root/name
            directory.mkdir(exist_ok=False)
            clone=directory/("C104_"+name+".EDB")
            copyfile(model,clone)
            require(digest(clone)==base["fine_edb_sha256"],"Clone fingerprint differs")
            def guard():
                require(Path(model_file(sap)) in (clone,clone.with_suffix(".$et")) and not clone.samefile(model)
                        and not clone.samefile(original) and clone.stat().st_nlink==1
                        and not any(p.is_junction() or p.is_symlink() for p in (clone,*clone.parents)),
                        "Operation outside the new private clone")
            native(sap.File.OpenFile(str(clone)),"Open "+name)
            switched=True
            guard()
            if sap.GetModelIsLocked():native(sap.SetModelIsLocked(False),"Unlock only "+name)
            db=sap.DatabaseTables
            before=read_table(db,MESH)
            require(before["status"]=="CAPTURED" and {r["UniqueName"]:r for r in before["rows"] if r["UniqueName"] in expected}==expected,
                    "Initial mesh differs from D")
            target=cross_inputs(before["rows"],vscale,hscale)
            try:
                ver,cols,rows=editing_rows(db)
                require({"UniqueName","Nv","Nh"}<=set(cols),"Missing mesh division fields")
                edited=cross_inputs(rows,vscale,hscale)
                flat=[str(r[k]) if r.get(k) not in (None,"None","") else "" for r in edited.values() for k in cols]
                guard()
                native(db.SetTableForEditingArray(MESH,ver,cols,len(rows),flat),"Edit mesh divisions")
                errors=native(db.ApplyEditedTables(True,0,0,0,0,""),"Apply mesh divisions")
                require(errors[:2]==[0,0],"Native import failed")
            finally:
                db.CancelTableEditing()
            actual=read_table(db,MESH)
            require(actual["status"]=="CAPTURED" and {r["UniqueName"]:r for r in actual["rows"]}==target,"Mesh readback differs")
            policies={u:native(sap.AreaObj.GetEdgeConstraint(u,False),"Read "+u) for u in ("436","437","438")}
            require(policies==load(pair/"fine/wall-policies.json"),"W23 or adjoining edge policy differs")
            guard()
            for case in physical:native(sap.Analyze.SetRunCaseFlag(case,True,False),"Arm "+case)
            native(sap.File.Save(str(clone)),"Save "+name+" private input")
            guard()
            require(text_shape(clone.with_suffix(".$et"))==text_shape(reference_export) and sap.GetPresentUnits()==6,
                    "Physical inputs or units differ")
            print("Solving",name, "vertical subdivision multiplier",vscale,"horizontal",hscale,flush=True)
            native(sap.Analyze.RunAnalysis(),"RunAnalysis "+name)
            guard()
            status=states(sap.Analyze.GetCaseStatus(0,[],[]),"Solved status")
            require(sap.GetModelIsLocked() and all(status[n]==4 for n in physical),"Incomplete crossed solve")
            save(directory/"case_statuses.json",{"return":0,"statuses":status})
            save(directory/"mesh_assignments.json",{u:target[u] for u in expected})
            mesh=collect_mesh(sap)
            parts=mesh["C104_segments"]
            require(len(parts)==103*vscale and all(c["exact_common_edge_walls"] for c in parts),"Disconnected C104 mesh")
            save(directory/"analysis_mesh.json",mesh)
            fs=capture_frame_forces(sap,members=("211",),cases=REFERENCE,combinations=combos)
            require(not fs["errors"] and fs["units_code"]==6,"Frame forces incomplete")
            save(directory/"frame_forces.json",fs)
            save(directory/"static_shell_forces.json",selected_shell_data(sap))
            dims=[read_table(db,"Objects and Elements - "+k) for k in ("Areas","Joints","Frames")]
            require(all(t["status"]=="CAPTURED" for t in dims),"Missing W23 analysis geometry")
            physical_mesh,owners=interface_geometry(*(t["rows"] for t in dims))
            save(directory/"interface-mesh.json",physical_mesh)
            save(directory/"wall-policies.json",policies)
            save(directory/"finished.json",{"case_count":len(physical),"model_sha_before_final_save":digest(clone),
                 "column_segments":len(parts),"wall_common_segments":len(parts),
                 "frame_sha":digest(directory/"frame_forces.json"),"shear_shell_sha":digest(directory/"static_shell_forces.json"),
                 "inputs_match_reference":True,"vertical":vscale,"horizontal":hscale,
                 "edge_mesh_sha256":digest(directory/"interface-mesh.json"),"wall_policy_sha256":digest(directory/"wall-policies.json"),
                 "mesh_assignment_sha256":digest(directory/"mesh_assignments.json"),"input_export_sha256":digest(clone.with_suffix(".$et"))})
            print("Recorded",name,len(parts),"connected C104 segments.",flush=True)
    finally:
        if switched:
            native(sap.File.OpenFile(str(model)),"Return to D")
            exact_copy(sap)
        require(digest(model)==base["fine_edb_sha256"] and digest(original)==base["original_edb_sha256"],"Protected EDB changed")
    save(root/"both-complete.json",{"a_d_capture":digest(pair/"both-complete.json"),"original_sha":base["original_edb_sha256"],
         "levels":{n:digest(root/n/"finished.json") for n in ("B","C")}})
    print("Crossed meshes complete:",root,flush=True)



def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pid",type=int,required=True)
    for arg in ("model","original","original-export","mesh-run","ad-run","out"):
        p.add_argument("--"+arg,type=Path,required=True)
    a=p.parse_args()
    model,original=a.model.resolve(strict=True),a.original.resolve(strict=True)
    require(not model.samefile(original),"Open the private D model")
    root=a.out.resolve()/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with socket(AF_INET,SOCK_STREAM) as slot:
        slot.setsockopt(SOL_SOCKET,SO_EXCLUSIVEADDRUSE,1)
        slot.bind(("127.0.0.1",8876))
        root.mkdir(parents=True,exist_ok=False)
        print("Crossed C104 study:",root,flush=True)
        _with_etabs(a.pid,lambda sap:solve(sap,root,model,original,a.original_export.resolve(strict=True),
                                           a.mesh_run.resolve(strict=True),a.ad_run.resolve(strict=True)))
if __name__=="__main__":
    main()
