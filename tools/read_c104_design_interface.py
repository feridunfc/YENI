"""Read the solved C104 mesh. An explicit flag also reproduces the prior A mesh in a new private EDB."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from math import isclose
from pathlib import Path
import re
from shutil import copyfile
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, socket

from prepare_c29_story_balance import checksum as digest, require
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.engineering.coupled_wall_transition import SIGNED_CASES as REFERENCE
from tbdy_next.engineering.gravity_wall_cut import joint_action_at_origin
from tbdy_next.etabs_source_gateway_windows import available_tables, model_file, read_table, return_code, selected_cases, set_cases
from tbdy_next.frame_force_capture import _catalog_names, capture_frame_forces, get_results_setup_state, restore_results_setup_state
from tbdy_next.live_etabs import _with_etabs

MESH="Area Assignments - Wall Auto Mesh Options"

def native(raw,method):
    require(return_code(raw,method)==0,method+" failed")
    return list(raw[:-1]) if isinstance(raw,(tuple,list)) else []

def states(raw,method):
    size,names,values=native(raw,method)
    require(size==len(names)==len(set(names))==len(values),"Invalid "+method)
    return dict(zip(names,values))

def save(path, value):
    with path.open("x",encoding="utf8") as out:
        json.dump(value,out,ensure_ascii=False,allow_nan=False)

def guard_model(sap,model,original):
    active=Path(model_file(sap))
    require(model.is_file() and not model.samefile(original) and model.stat().st_nlink==1
            and not any(p.is_symlink() or p.is_junction() for p in (model,*model.parents))
            and active in (model,model.with_suffix(".$et")),"Open the exact private C104 model")

def text_shape(path):
    lines=[line.strip() for line in path.read_text(encoding="mbcs").splitlines()[1:] if line.strip()]
    normalized=[]
    for i,line in enumerate(lines):
        if " File saved as " in line:
            continue
        if line=="$ SECTION DESIGNER SECTIONS" and i+1<len(lines) and lines[i+1]=="$ SLAB PROPERTIES":
            continue
        if line.startswith(('AREAASSIGN  "W21"  "+0.00"','AREAASSIGN  "W22"  "+0.00"')):
            line=re.sub(r"  MESHVERT \d+ MESHHORIZ \d+ ", "  ", line)
            line=re.sub(r'  LINECONSTRAINT  "No"', "", line)
        normalized.append(line)
    return Counter(normalized)



def editing_rows(db):
    version,fields,count,flat=native(db.GetTableForEditingArray(MESH,"",0,[],0,[]),"Read editable wall mesh")
    require(version==2 and len(fields)==len(set(fields)) and len(flat)==count*len(fields),
            "Unexpected editable wall mesh table")
    wanted=("UniqueName","MeshOption","Nv","Nh","Restraints")
    require(set(fields)<=set(("Story","Label",*wanted)) and set(wanted)<=set(fields)|{"Nv","Nh"},
            f"Unexpected editable wall mesh fields: {fields}")
    n=len(fields)
    return version,fields,[dict(zip(fields,flat[i:i+n])) for i in range(0,len(flat),n)]



CASES = (*REFERENCE, "RSX", "RSY")
WALLS = ("436", "437", "438")
POINTS = ("ElmJt1","ElmJt2","ElmJt3","ElmJt4")


def interface_geometry(areas,joints,frames):
    xyz={r["ElmName"]:[float(r["Global"+d]) for d in "XYZ"] for r in joints}
    edge={n for n,(x,y,z) in xyz.items() if abs(x-77.4)<1e-6 and abs(y-.4)<1e-6 and -1.500001<=z<=.000001}
    incident={(r["ObjType"],r["ObjName"]) for r in areas if edge.intersection(r.get(k) for k in POINTS)}
    require(edge and {("Wall","437"),("Wall","438")}<=incident,"W22/W23 physical edge missing")
    meshrows=[r for r in areas if (r["ObjType"]=="Wall" and r["ObjName"] in WALLS) or (r["ObjType"],r["ObjName"]) in incident]
    edges_frames=[r for r in frames if r.get("ObjType")=="Frame" and edge.intersection((r.get("ElmJtI"),r.get("ElmJtJ")))]
    wanted={r.get(k) for r in meshrows for k in POINTS}-{None,"","None"}
    require(wanted<=xyz.keys(),"Missing analysis joint coordinates")
    return {"edge_points":sorted(edge),"area_cells":meshrows,"incident_frames":edges_frames,
            "coordinates":{n:xyz[n] for n in sorted(wanted|edge)}},incident


def read(sap, out, model, guard, archive_root, reference_export):
    guard(sap)
    fingerprint = digest(model)
    require(text_shape(model.with_suffix(".$et")) == text_shape(reference_export), "Input deck differs outside authorized mesh fields")
    settings = read_table(sap.DatabaseTables,MESH)
    require(settings["status"]=="CAPTURED","Wall mesh table unavailable")
    actual={r["UniqueName"]:r for r in settings["rows"] if r["UniqueName"] in ("436","437")}
    candidates=[lv for lv in ("mesh-1","mesh-2") if actual==json.loads((archive_root/lv/"mesh_assignments.json").read_bytes())]
    require(len(candidates)==1 and all(native(sap.AreaObj.GetEdgeConstraint(u,False),"GetEdgeConstraint")==[False] for u in actual),
            "Physical wall mesh or edge policy differs from both archived models")
    level,=candidates
    require(sap.GetPresentUnits() == 6, "Set ETABS display units to kN, m, C")
    statuses = states(sap.Analyze.GetCaseStatus(0,[],[]), "GetCaseStatus")
    save(out/"state.json", {"level":level, "edb_sha256":fingerprint, "units_code":6,
                          "locked":sap.GetModelIsLocked(), "statuses":statuses})
    if not sap.GetModelIsLocked() or any(statuses.get(k) != 4 for k in CASES):
        print("The saved mesh has no available locked solution for the requested cases. State saved. No analysis was run.", flush=True)
        return
    archive = archive_root/level
    last = json.loads((archive/"finished.json").read_bytes())
    require(digest(archive/"frame_forces.json") == last["frame_sha"], "Archived witness hash differs")
    all_cases = tuple(k for k,v in statuses.items() if not k.startswith("~") and v==4)
    controls = capture_frame_forces(sap, members=("211",), cases=REFERENCE)
    def witnesses(raw):
        return {tuple(row[:7]):row[7:] for row in native_frame_force_rows(raw["rowsets"]["211"],"211")
                if row[4] in REFERENCE}
    a = witnesses(json.loads((archive/"frame_forces.json").read_bytes()))
    b = witnesses(controls)
    common=a.keys() & b.keys()
    bad=sum(not isclose(x,y,abs_tol=1e-6,rel_tol=1e-8) for key in common for x,y in zip(a[key],b[key],strict=True))
    matched=not controls["errors"] and bool(common) and a.keys()==b.keys() and bad==0
    save(out/"archived-controls.json",{"matched":matched,"archived_rows":len(a),"observed_rows":len(b),"common_rows":len(common),
                                      "scalar_differences":bad,"actual_file_sha256":fingerprint,"solved_physical_cases":all_cases})
    print(level,"archived scalar controls:",6*len(common)-bad,"/",6*len(a),flush=True)
    # Keep the actual new generation even if one archived control differs.
    combo_names=json.loads((archive/"frame_forces.json").read_bytes())["output_selection_during"]["combos"]
    assigned=tuple(n for n,selected in combo_names.items() if selected)
    save(out/"design-frame-forces.json",capture_frame_forces(sap,members=("211",),cases=REFERENCE,combinations=assigned))
    db = sap.DatabaseTables
    names = _catalog_names(sap.LoadCases.GetNameList(0,[],0))
    combos = _catalog_names(sap.RespCombo.GetNameList(0,[]))
    setup = sap.Results.Setup
    before = get_results_setup_state(setup,cases=names,combos=combos)
    display = selected_cases(db)
    try:
        ordered = tuple(n for n in names if n in CASES)
        set_cases(db,ordered)
        save(out/"display-cases.json",{"requested":ordered,"observed":selected_cases(db)})
        catalogue = {t["table_key"] for t in available_tables(db)}
        keys = {"Story Forces","Mass Summary by Story","Centers Of Mass And Rigidity","Load Case Definitions - Response Spectrum",
                "Load Pattern Definitions - Auto Seismic - TSC 2018","Mass Source Definition","Story Max Over Avg Drifts",
                "Diaphragm Center Of Mass Displacements","Joint Assignments - Restraints"}
        keys.update(k for k in catalogue if "constraint" in k.lower() or "seismic loads to diaphragms" in k.lower()
                    or "centers of mass" in k.lower())
        for key in sorted(keys & catalogue):
            save(out/(key+".json"), read_table(db,key))
        native(setup.DeselectAllCasesAndCombosForOutput(),"Clear temporary output selection")
        for case in CASES:
            native(setup.SetCaseSelectedForOutput(case,True),"Select "+case)
        require(get_results_setup_state(setup,cases=names,combos=combos) ==
                {"cases":{n:n in CASES for n in names},"combos":dict.fromkeys(combos,False)}, "Native output selection differs")
        base = native(sap.Results.BaseReact(0,*([] for _ in range(9)),0.,0.,0.),"BaseReact")
        require(set(base[1]) == set(CASES), "Native base-reaction case population differs")
        save(out/"base-reactions.json",base)
        area = read_table(db,"Objects and Elements - Areas")
        joint = read_table(db,"Objects and Elements - Joints")
        frames = read_table(db,"Objects and Elements - Frames")
        require(all(t["status"] == "CAPTURED" for t in (area,joint,frames)), "Mesh tables unavailable")
        mesh,incident = interface_geometry(area["rows"],joint["rows"],frames["rows"])
        xyz,edge,meshrows,edges_frames=mesh["coordinates"],set(mesh["edge_points"]),mesh["area_cells"],mesh["incident_frames"]
        nds=set(xyz)
        save(out/"interface-mesh.json",mesh)
        edges={u:native(sap.AreaObj.GetEdgeConstraint(u,False),"GetEdgeConstraint "+u) for u in WALLS}
        save(out/"wall-policies.json",edges)
        owners=sorted({uid for kind,uid in incident}|set(WALLS))
        for uid in owners:
            raw=native(sap.Results.AreaJointForceShell(uid,0,0,*([] for _ in range(12))),"AreaJointForceShell "+uid)
            save(out/("area-"+uid+".json"),raw)
        if edges_frames:
            resolved = tuple(sorted({r["ObjName"] for r in edges_frames}))
            save(out/"incident-frame-forces.json",capture_frame_forces(sap,members=resolved,cases=REFERENCE))
        reactions = {}
        for n in sorted(edge):
            try:
                raw = native(sap.Results.JointReact(n,1,0,*([] for _ in range(11))),"JointReact "+n)
                reactions[n] = {"raw":raw}
            except Exception as exc:
                reactions[n] = {"error":str(exc)}
        save(out/"edge-joint-reactions.json",reactions)
        matrices={}
        body_nodes={r[k] for r in meshrows if r["ObjType"]=="Wall" and r["ObjName"] in ("437","438")
                    for k in POINTS if r.get(k) in xyz}
        needed=edge|body_nodes|{n for n in nds if abs(xyz[n][2]+1.5)<.051}
        for n in sorted(needed):
            try:
                mat,=native(sap.PointElm.GetTransformationMatrix(n,[]),"GetTransformationMatrix "+n)
            except Exception:
                angles=native(sap.PointElm.GetLocalAxes(n,0.,0.,0.),"GetLocalAxes "+n)
                require(angles==[0.,0.,0.], "Unresolved point axes at "+n)
                mat=[1.,0.,0.,0.,1.,0.,0.,0.,1.]
            joint_action_at_origin([0.]*6,mat,xyz[n],[74,.4,-1.5])
            matrices[n]=mat
        save(out/"point-matrices.json",matrices)
    finally:
        try:
            set_cases(db,display)
        finally:
            restore_results_setup_state(setup,before)
        require(selected_cases(db)==display and get_results_setup_state(setup,cases=names,combos=combos)==before,
                "Original selection could not be verified")
    guard(sap)
    require(sap.GetModelIsLocked() and digest(model)==fingerprint,"Source lock or EDB changed")
    save(out/"complete.json",{"level":level,"file_sha256":fingerprint,"archive_frame_sha256":last["frame_sha"],
                              "witness_rows":len(a),"archived_controls_match":matched,"selected_cases":CASES,"restored":True,"file_hashes":{
                                  p.name:digest(p) for p in sorted(out.glob("*.json"))}})
    print("Read complete:",out,flush=True)


def study(sap, root, model, archive_root, reference_export, original, reproduce_coarse):
    def exact_copy(active):
        guard_model(active,model,original)
    exact_copy(sap)
    fine_sha=digest(model)
    fine=root/"fine"
    fine.mkdir()
    read(sap,fine,model,exact_copy,archive_root,reference_export)
    if not reproduce_coarse:
        return
    require((fine/"complete.json").is_file(),"No solved fine result. Coarse copy not started.")
    coarse=root/"coarse"
    coarse.mkdir()
    clone=coarse/"C104_INTERFACE_A.EDB"
    target_original=digest(original)
    def guard(active):
        path=Path(model_file(active))
        require(path in (clone,clone.with_suffix(".$et")) and clone.is_file() and clone.stat().st_nlink==1
                and not any(p.is_symlink() or p.is_junction() for p in (clone,*clone.parents))
                and not clone.samefile(model) and not clone.samefile(original), "Not the dedicated coarse experiment")
    # The new directory was created exclusively. Never overwrite a saved study.
    require(not clone.exists(), "Private destination already exists")
    copyfile(model,clone)
    require(digest(clone)==fine_sha, "Private copy differs")
    opened=False
    try:
        native(sap.File.OpenFile(str(clone)), "Open the new private coarse clone")
        opened=True
        guard(sap)
        if sap.GetModelIsLocked():
            native(sap.SetModelIsLocked(False),"Unlock only the new private clone")
        db=sap.DatabaseTables
        previous=read_table(db,MESH)
        require(previous["status"]=="CAPTURED","No mesh input table")
        before={r["UniqueName"]:r for r in previous["rows"]}
        fine_expected=json.loads((archive_root/"mesh-2/mesh_assignments.json").read_bytes())
        target=json.loads((archive_root/"mesh-1/mesh_assignments.json").read_bytes())
        require(all(before[u]==v for u,v in fine_expected.items()),"Starting clone is not mesh D")
        try:
            version,columns,content=editing_rows(db)
            require(len(content)==30 and {"UniqueName","Nv","Nh"}<=set(columns),"Wall mesh edit fields differ")
            for row in content:
                if row["UniqueName"] in target:
                    row.update({k:target[row["UniqueName"]][k] for k in ("Nv","Nh")})
            flat=[str(r[k]) if r.get(k) not in ("",None,"None") else "" for r in content for k in columns]
            guard(sap)
            native(db.SetTableForEditingArray(MESH,version,columns,len(content),flat),"Change only the two archived mesh divisions")
            applied=native(db.ApplyEditedTables(True,0,0,0,0,""),"Apply the two mesh divisions")
            require(applied[:2]==[0,0],"Import rejected: "+str(applied))
        finally:
            db.CancelTableEditing()
        after=read_table(db,MESH)
        require(after["status"]=="CAPTURED" and {r["UniqueName"]:r for r in after["rows"]}=={**before,**target},
                "Mesh readback differs outside the two exact input rows")
        guard(sap)
        physical=[n for n,s in json.loads((archive_root/"mesh-1/case_statuses.json").read_bytes())["statuses"].items() if not n.startswith("~") and s==4]
        require(len(physical)==15 and sap.GetPresentUnits()==6,"Unexpected public case roster or units")
        for n in physical:
            native(sap.Analyze.SetRunCaseFlag(n,True,False),"Arm archived case "+n)
        native(sap.File.Save(str(clone)),"Save the generated coarse deck under its private name")
        guard(sap)
        require(text_shape(clone.with_suffix(".$et"))==text_shape(reference_export),"Coarse model input differs outside the two meshes")
        print("Solving the previously studied coarse mesh in the new copy, 15 original cases.",flush=True)
        native(sap.Analyze.RunAnalysis(),"Run the coarse copy")
        guard(sap)
        read(sap,coarse,clone,guard,archive_root,reference_export)
        require((coarse/"complete.json").is_file(),"Coarse capture incomplete")
    finally:
        if opened:
            native(sap.File.OpenFile(str(model)),"Return to the fine model")
            exact_copy(sap)
        require(digest(model)==fine_sha and digest(original)==target_original,"Protected EDB changed")
    save(root/"both-complete.json",{"fine_capture":digest(fine/"complete.json"),"coarse_capture":digest(coarse/"complete.json"),
                                    "fine_edb_sha256":fine_sha,"original_edb_sha256":target_original})
    print("Both meshes read:",root,flush=True)



def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pid",type=int,required=True)
    for arg in ("model","original","original-export","mesh-run","out"):
        p.add_argument("--"+arg,type=Path,required=True)
    p.add_argument("--reproduce-coarse",action="store_true",help="Solve the original 15 cases in a new A-mesh copy.")
    a=p.parse_args()
    root=a.out.resolve()/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    model,original=a.model.resolve(strict=True),a.original.resolve(strict=True)
    archive=a.mesh_run.resolve(strict=True)
    reference=a.original_export.resolve(strict=True)
    require(digest(original)==json.loads((archive/"finished.json").read_bytes())["original_sha"],"Original EDB hash differs")
    require(model!=original and not model.samefile(original),"The active model must be the private D-mesh copy")
    with socket(AF_INET,SOCK_STREAM) as slot:
        slot.setsockopt(SOL_SOCKET,SO_EXCLUSIVEADDRUSE,1)
        slot.bind(("127.0.0.1",8876))
        root.mkdir(parents=True,exist_ok=False)
        print("C104 interface capture:",root,flush=True)
        _with_etabs(a.pid,lambda sap:study(sap,root,model,archive,reference,original,a.reproduce_coarse))

if __name__=="__main__":
    main()
