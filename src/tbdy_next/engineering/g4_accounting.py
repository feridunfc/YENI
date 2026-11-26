"""Join recorded check outcomes to the independent source-side physical census."""
from collections import Counter, defaultdict

from .basement_pier_design import pressure_ends
from .design_scenario import _digest
from .g1_contract import require
from .g4_population import FAMILIES


def check_accounting(frozen, source, stages, building):
    require(not frozen.get("unresolved") and frozen["population_sha256"]==_digest(
        {k:v for k,v in frozen.items() if k!="population_sha256"}),"G4_EXPECTED_POPULATION_UNAVAILABLE")
    names=[name for name,_ in FAMILIES]
    summary={r["name"]:r for r in building["checks"]}
    require(len(summary)==len(building["checks"])==len(names) and summary.keys()==set(names),"G4_SUMMARY_FAMILY_DRIFT")
    observed=defaultdict(dict)
    def record(family,identity,disposition,reason):
        key=(identity,) if isinstance(identity,str) else tuple(identity)
        require(key not in observed[family],"G4_DUPLICATE_RESULT:"+names[family]+repr(key))
        observed[family][key]=[disposition,str(reason)]
    def condition(family,key,satisfied,reason):
        record(family,key,"EVALUATED" if satisfied else "BLOCKED",reason)
    def rows(family,items,key):
        for r in items:
            status=r["status"]
            disposition=("NOT_APPLICABLE" if status=="NOT_APPLICABLE" else "BLOCKED" if status in ("NOT_PROVEN","BLOCKED","HOLD")
                else "FAILED" if status in ("NUMERICAL_EXCEEDANCE","SUBCONDITION_NOT_MET","DOES_NOT_MEET_SUBCONDITION") else "EVALUATED")
            record(family,r[key],disposition,status)
    for axis in ("X","Y"):
        condition(0,axis,stages["result"].get("sum_u"+axis.lower()) is not None,stages["result"]["status"])
    for s in ("geometry","extra"):
        for check in stages[s]["checks"]:
            f=names.index(check["check_id"])
            rows(f,check["items"],"element_id" if s=="geometry" else "material_name" if f==5 else "story")
    vs=stages["vs04_pipeline"]["stages"]
    for i,component,field,ident in ((8,"vs04_e","candidates","table_key"),(9,"vs04_f","components","component"),
                                     (10,"vs04_g","tables","table_key"),(11,"vs04_h","components","component")):
        for r in vs[component][field]:
            key=(r[ident],r.get("capture_phase","default")) if i==10 else r[ident]
            status=r.get("source_status",r.get("status"))
            condition(i,key,"OBSERVED" in status,status)
    # Successful reconstruction requires every unique selected case/mode. A count alone
    # cannot distinguish a duplicated native mode from a missing one.
    spectrum=vs["vs04_i"]
    selected=source["vs04_diaphragm_probe"]["spectrum_modal_selected_cases"]["rows"]
    for r in selected:
        condition(12,(r["SpecCase"],r["Mode"]),spectrum["reconstructed_modal_rows"]==len(selected)
                  and spectrum["unexplained_modal_rows"]==0,spectrum["status"])
    condition(13,"Eq4.19",vs["vs04_j"]["conditional_eq_4_19_minimum_term_kn"] is not None,vs["vs04_j"]["status"])
    ev=stages["report_evidence"]
    for j,identity in enumerate(("combination","context_sha256")):
        rows(14+j,ev["earthquake_combinations"]["checks"][j]["items"],identity)
    for r in ev["story_drift"]["items"]:
        condition(16,(r["story"],r["case"],r["direction"]),r["etabs_derived_delta_m"] is not None,r["regulatory_status"])
    for r in ev["r08_second_order"]["results"]:
        condition(17,(r["story"],r["direction"]),r["theta_ii_candidate"] is not None,r["source_numeric_status"])
    for r in ev["vs06_b1_result"]["b1_numerical"]["paired_results"]:
        condition(18,(r["lower_story"],r["upper_story"],r["direction"]),r["eta_ci"] is not None,r["numeric_condition"])
    for r in ev["soft_story_b2"]["story_results"]:
        record(19,(r["story"],r["direction"]),"BLOCKED" if not r["numeric_complete"] else
               "FAILED" if r["observed_threshold_exceeded"] else "EVALUATED",r["status"])
    for r in ev["wall_geometry"]["items"]:
        statuses=[q.get("status") for q in r["subconditions"]] if isinstance(r["subconditions"],list) else []
        outcome = {"NOT_APPLICABLE":"NOT_APPLICABLE","NOT_PROVEN":"BLOCKED"}.get(r["status"],"EVALUATED")
        if "DOES_NOT_MEET_SUBCONDITION" in statuses:
            outcome = "FAILED"
        record(20,r["element_id"],outcome,r["status"])
    for r in stages["column_axial"]["columns"]:
        for cut in r["combination_checks"]:
            record(21,(r["element_id"],cut["combination"]),"FAILED" if cut["ratio"]>1 else "EVALUATED",cut["status"])
    for r in stages["beam_r10"]["beams"]:
        status=r["selected_design"]["status"]
        record(22,r["member_id"],{"CONDITIONAL_DESIGN_CALCULATED":"EVALUATED","NUMERICAL_EXCEEDANCE":"FAILED"}.get(status,"BLOCKED"),status)
    for r in building["columns"]:
        record(23,r["member_id"],{"conditional":"EVALUATED","failed":"FAILED","hold":"BLOCKED"}[r["status"]],
               r.get("reason") or r["status"])
    walls=building["wall_sections"]
    for w in walls["batch"]["rows"]:
        if not w["pier"]:
            continue
        for cut in w["cuts"]:
            if cut["role"].startswith("ASSIGNED_"):
                key=(w["pier"],w["story"],cut["face"],cut["combination"])
                for i,field in ((24,"abs_v2_kn"),(25,"axial_ratio"),(26,"reference_web"),(27,"reference_friction")):
                    condition(i,key,cut.get(field) is not None,cut["force_basis"])
        for axis,over in w["overturning"].items():
            condition(28,(w["pier"],w["story"],axis),over.get("magnitude_knm") is not None,"NATIVE_DIRECTIONAL_CUT")
    for r in building["wall_boundaries"]["walls"]:
        condition(33,r["member_id"],r["status"]=="BOUNDARY_MINIMA_CALCULATED",r["status"])
        condition(34,r["member_id"],r.get("cage_status")=="CONDITIONAL_TRANSVERSE_CAGE_CALCULATED",r.get("cage_status",r["status"]))
    for family,group in ((30,"columns"),(31,"beams")):
        for r in building["frame_confinement"][group]:
            status=r["status"]
            record(family,r["member_id"],{"SCHEDULE_CALCULATED":"EVALUATED","NUMERICAL_EXCEEDANCE":"FAILED"}.get(status,"BLOCKED"),status)
            if group=="beams":
                for face,f in r.get("faces",{}).items():
                    condition(32,(r["member_id"],face),"schedule" in r and f["basis"]=="COLUMN_JOINT_AND_NATIVE_FACE_CUT",f["basis"])
    for pier in walls["piers"]:
        for r in pier["panel_details"]:
            condition(42,r["member"],r["status"]=="PANEL_CALCULATED",r["status"])
        for f,group in ((35,"gravity_rows"),(36,"seismic_shear")):
            for cut in pier[group]:
                record(f,(cut["member"],cut["face"],cut["combination"]),
                       "FAILED" if "EXCEED" in cut["status"] else "EVALUATED",cut["status"])
        for cut in pier["seismic_sections"]:
            key=(cut["member"],cut["face"],cut["combination"])
            for f,field in ((37,"axial_ratio"),(38,"height_branches"),(39,"shear_upper_ratio"),(40,"pmm"),(44,"chain_status")):
                condition(f,key,cut.get(field) is not None and (f!=44 or cut[field]=="CONDITIONAL_SECTION_DESIGN"),cut["status"])
        for f,group,field in ((41,"construction_joints","upper_member"),(43,"strong_wall_connections","lower_member")):
            for cut in pier[group]:
                record(f,(cut[field],cut["combination"]),"FAILED" if "EXCEED" in cut["status"] else "EVALUATED",cut["status"])
        for uid in pier["members"]:
            condition(29,uid,pier["conditional_section_count"]>0,"RECTANGULAR_STACK_CONDITIONAL_SCHEDULE")
    def body(uid,design,plate,assigned):
        for name in assigned:
            m=[q for q in design.get("checks",[]) if q["combination"]==name and q.get("utilization") is not None]
            p=[q for q in plate if q["combination"]==name and q.get("proposed_ratio") is not None]
            valid={q["action"] for q in m}=={"Horizontal steel","Vertical steel","Face concrete compression","Core transverse shear"} and \
                {(q["action"],q["axis"]) for q in p}=={(a,b) for a in ("Bending","Transverse shear") for b in ("Horizontal","Vertical")}
            condition(47,(uid,name),valid,"SAME_CORNER_AND_PROPOSED_PLATE_CURTAIN" if valid else "INCOMPLETE_SHELL_ACTIONS")
    for pier in walls["basement_piers"]:
        assigned=pier["wall_strength"]
        for cut in pier["cuts"]:
            if cut["role"]=="WALL_STRENGTH":
                condition(46,(pier["pier"],pier["story"],cut["face"],cut["combination"]),
                          cut["status"]=="CONDITIONAL_NET_WEB_PMM_BOUND",cut["status"])
        for uid,r in pier.get("body_references",{}).items():
            body(uid,r.get("membrane_and_plate",{}),r.get("checks",[]),assigned)
        for panel in (pier.get("geometry") or {}).get("panels",[]):
            uid=panel["member"]
            ok=panel.get("schedule_status")=="PRESSURE_PANEL_SCHEDULE_QUALIFIED"
            for f in (29,48):
                condition(f,uid,ok,panel.get("reason") or panel.get("schedule_status"))
            shell=panel.get("two_way_shell",{})
            if "membrane_and_plate" in shell.get("proposed_detail",{}):
                body(uid,shell["proposed_detail"]["membrane_and_plate"],shell.get("checks",[]),assigned)
            for side,end in pressure_ends(panel).items():
                ok=end.get("status")=="CONDITIONAL_PRESSURE_END_DESIGN" and end.get("layout_status")=="PROPOSED_PRESSURE_BARS_FIT"
                record(49,(uid,side),"EVALUATED" if ok else "CHECKED_OPEN",end.get("layout_status") or end["status"])
                for cut in end["transfer"].get("combinations",[]):
                    if cut["combination"] in assigned:
                        condition(50,(uid,side,cut["combination"]),True,"NATIVE_EDGE_TRANSFER")
        for panel in (pier.get("geometry") or {}).get("transfer_panels",[]):
            if panel.get("schedule_status")=="PRESSURE_PANEL_SCHEDULE_QUALIFIED":
                condition(29,panel["member"],True,panel["schedule_status"])
    # These owners explicitly report zero design evaluations. Materialise each open
    # item so a slab, mat, diaphragm or unapproved wall schedule cannot disappear in totals.
    for index in (45,51,52,53,54,55):
        name,grain=FAMILIES[index]
        require(summary[name]["evaluated"]==0,"G4_UNSUPPORTED_OWNER_HAS_RESULTS:"+name)
        for identity in frozen["grains"][grain]:
            record(index,identity,"BLOCKED",summary[name]["outcome"])
    for uid,r in frozen["coupling_beam_applicability"].items():
        record(56,uid,"BLOCKED" if r["status"]=="WALL_TO_WALL_ROLE_REVIEW" else "NOT_APPLICABLE",r["status"])
    ledger={}
    for i,(name,grain) in enumerate(FAMILIES):
        expected=frozen["grains"][grain]
        original=summary[name]
        require(original["expected"] in (None,len(expected)),"G4_DENOMINATOR_CHANGED:"+name)
        keys={tuple(key) for key in expected}
        require(not (observed[i].keys()-keys),"G4_UNEXPECTED_RESULTS:"+name)
        entries=[]
        for key in expected:
            result=observed[i].get(tuple(key),["BLOCKED",original["outcome"]])
            entries.append(result)
        counts=Counter(r[0] for r in entries)
        calculated=sum(counts[k] for k in ("EVALUATED","FAILED","CHECKED_OPEN"))
        require(original["evaluated"] is None or original["evaluated"]==calculated,"G4_EVALUATED_COUNT_MISMATCH:"+name)
        if 8<=i<=13:
            require(calculated==stages["vs04_pipeline"]["checks"][i-8]["coverage"]["observed_in_original_stage"],
                    "G4_SOURCE_COVERAGE_MISMATCH:"+name)
        ledger[name]={"grain":grain,"expected":len(expected),"dispositions":dict(counts),"ordered_outcomes":entries}
    return {"expected_population_sha256":frozen["population_sha256"],"families":ledger,"family_count":len(ledger),
            "expected_instances":sum(v["expected"] for v in ledger.values()),
            "coupling_roles":dict(Counter(v["status"] for v in frozen["coupling_beam_applicability"].values())),
            "open_transition_members":[r["member_id"] for r in building["columns"] if r["member_id"] in frozen["coupled_transition_columns"]
                                       and r["status"]=="hold"],"engineering_release":"NOT_READY"}
