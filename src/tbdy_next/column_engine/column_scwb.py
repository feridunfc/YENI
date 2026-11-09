"""VS22: source-bound adaptation of TBDY joint/direction SCWB orchestration.

Each native joint occurs once. Every expected column/beam end is retained.
Available column references use N at verified source cuts and proposed cages;
required beam steel and ETABS override cells never become provided capacity.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from dataclasses import asdict
import math

from .column_joints import GEOMETRY_TOL, _vertical, _parallel
from .column_kinematics import _force_pair
from .column_pmm import cage_rows, _section, DIAMETERS
from .column_prechecks import _number
from .column_stability import OPTIONAL_ERRORS
from .csi_geometry import AXIS_CONVENTION
from .native_archive import BankError, digest, finite, identity
from .scwb_kernel import JointCase, MemberMomentCapacity, compute_scwb_joint_result, column_axis_capacity, SOURCE

SCHEMA="tbdy.next.scwb-source-references.v1"
POLICY="COMPLETE_JOINT_ROSTER_SAME_STATIC_CASE_COLUMN_AXIS_REFERENCE_V1"
LABELS=tuple(f"16Φ{d}" for d in DIAMETERS)
REBAR_FIELDS="MatPropLong MatPropConfine CoverTop CoverBot TopLeftArea TopRightArea BotLeftArea BotRightArea pRetVal".split()
OPEN_BASIS=["ACTUAL_OR_SELECTED_BEAM_END_REINFORCEMENT_NOT_BOUND","BEAM_END_SIGNED_CAPACITIES_NOT_BOUND",
    "PROPOSED_COLUMN_CAGES_NOT_SELECTED_OR_AS_BUILT","EARTHQUAKE_COMPATIBLE_MINIMUM_CAPACITY_ND_NOT_BOUND",
    "PHYSICAL_JOINT_FACES_AND_SLAB_PARTICIPATION_NOT_BOUND","SCWB_EXCEPTION_APPLICABILITY_NOT_PROVEN",
    "SECOND_ORDER_AND_FINAL_DESIGN_STATE_NOT_BOUND"]


def _validate(chain,cages,joints,kinematics,archive):
    for result in (chain,cages,joints,kinematics):
        if (result["source_archive_sha256"]!=archive.sha256 or result["source_run_id"]!=chain["source_run_id"]
                or result["design_demand_authority"]!="DENIED" or result["formal_compliance"]!="NOT_PROVEN"
                or result["engineering_release"]!="NOT_READY"):
            raise BankError("SCWB_SOURCE_OR_AUTHORITY_MISMATCH")
    for result in (cages,joints,kinematics):
        if result["axis_convention"]!=AXIS_CONVENTION or result["source_demand_result_sha256"]!=chain["result_sha256"]:
            raise BankError("SCWB_DERIVATION_MISMATCH")
    if (joints["source_cages_result_sha256"]!=cages["result_sha256"]
            or kinematics["source_joints_result_sha256"]!=joints["result_sha256"]
            or any(r["selected_design"] is not None for r in (cages,joints,kinematics))
            or kinematics["actual_second_order_applied"] is not False or joints["scwb_status"]!="NOT_PROVEN"):
        raise BankError("SCWB_SCOPE_MISMATCH")
    members={m["member_id"] for m in cages["members"]}
    cases={c["combination"] for c in chain["combinations"] if c["classification"]=="STATIC_LINEAR_ADD"}
    states={s["state_id"]:s for s in chain["candidates"]}
    force_index=defaultdict(list)
    for state in states.values():force_index[(state['native_key']['Obj'],state['native_key']['LoadCase'])].append(state)
    frames={f['frame_id']:f for f in joints['graph']['frames']}
    expected_pairs={(m,c) for m in members for c in cases}
    if len(states)!=chain["static_candidate_count"] or len(members)!=len(cages["members"]):
        raise BankError("SCWB_SOURCE_POPULATION_MISMATCH")
    seen=set()
    for row in kinematics["rows"]:
        key=(row["member_id"],row["output_case"])
        if key in seen or key not in expected_pairs:
            raise BankError("SCWB_FORCE_PAIR_POPULATION_MISMATCH")
        seen.add(key);pair=row["force_pair"]
        if pair:
            if (row["force_status"]!="SAME_CASE_FORCE_CUT_PAIR_BOUND" or pair["output_cuts_are_physical_support_faces"] is not False
                    or pair["end_pair_is_design_envelope"] is not False):raise BankError("SCWB_FORCE_PAIR_SCOPE_MISMATCH")
            for end in ("i","j"):
                state=pair[end];native=state["native_key"]
                if (state!=states.get(state["state_id"]) or native["Obj"]!=key[0] or native["LoadCase"]!=key[1]
                        or native["StepType"]!="Single Value" or native["StepNum"]!=0
                        or state["vector_status"]!="SIGNED_STATIC_SOURCE_VECTOR"):
                    raise BankError("SCWB_FORCE_STATE_BINDING_MISMATCH")
            # Rebind I/J to native offsets and unique source stations. Same
            # member/case alone would accept a swapped or interior end state.
            observed=archive.native('FrameObj.GetEndLengthOffset','frame',key[0],
                ('AutoOffset','Length1','Length2','RZ','pRetVal'))
            if observed is None or key[0] not in frames:raise BankError('SCWB_NATIVE_END_CUTS_NOT_BOUND')
            values,proof=observed
            member={'station_geometry':{'native_facts':{'offsets':{'values':values,'source':proof}}}}
            if pair!=_force_pair(member,frames[key[0]],force_index[key]):
                raise BankError('SCWB_NATIVE_END_CUT_BINDING_MISMATCH')
    if seen!=expected_pairs:raise BankError("SCWB_FORCE_PAIR_POPULATION_MISMATCH")
    return sorted(cases)


def _beam_sources(archive,frames):
    table_keys=sorted(name for api,kind,name in archive.index if api=="DatabaseTables.GetTableForDisplayArray"
        and kind=="table" and isinstance(name,str) and name.startswith("Concrete Beam Design Summary - "))
    summary={"status":"NOT_RECORDED","source":None,"row_count":0,"member_count":0,"reason":None,
        "required_area_is_provided_rebar":False,"required_area_used_as_capacity":False}
    counts=Counter()
    try:
        if len(table_keys)>1:raise BankError("SCWB_BEAM_SUMMARY_AMBIGUOUS")
        if table_keys:
            observed=archive.table(table_keys[0],("UniqueName","Station","AsTop","AsBot"))
            if observed is None:raise BankError("SCWB_BEAM_SUMMARY_NOT_OBSERVED")
            rows,proof=observed
            counts=Counter(identity(row["UniqueName"],"beam_unique_name") for row in rows)
            summary.update(status="REQUIRED_AREA_SOURCE_ONLY",source=proof,row_count=len(rows),member_count=len(counts))
    except OPTIONAL_ERRORS as exc:summary.update(status="BLOCKED_SOURCE",reason=str(exc))
    result=[]
    for name,frame in sorted(frames.items()):
        if frame["design_orientation"]!=2:continue
        row={"member_id":name,"point_i":frame["point_i"],"point_j":frame["point_j"],"section_name":None,
            "source_calls":{},"cover_top_mm":None,"cover_bottom_mm":None,"override_area_mm2":None,
            "required_area_row_count":counts[name],"actual_or_selected_cage_bound":False,
            "moment_capacity_knm":None,"status":"BEAM_CAPACITY_NOT_BOUND","reason":"ACTUAL_BEAM_END_REINFORCEMENT_NOT_BOUND"}
        try:
            observed=archive.native("FrameObj.GetSection","frame",name,("PropName","SAuto","pRetVal"))
            if observed is None:raise BankError("SCWB_BEAM_SECTION_NOT_RECORDED")
            values,proof=observed;section=identity(values["PropName"],"beam_section")
            row["section_name"]=section;row["source_calls"]["assignment"]=proof
            observed=archive.native("PropFrame.GetRebarBeam","beam_section",section,REBAR_FIELDS)
            if observed is None:raise BankError("SCWB_BEAM_REBAR_SETTING_NOT_RECORDED")
            values,proof=observed;row["source_calls"]["rebar_setting"]=proof
            row["cover_top_mm"]=float(_number(values["CoverTop"],"beam_top_cover")*1000)
            row["cover_bottom_mm"]=float(_number(values["CoverBot"],"beam_bottom_cover")*1000)
            row["override_area_mm2"]={k:float(_number(values[k],k)*1000000) for k in ("TopLeftArea","TopRightArea","BotLeftArea","BotRightArea")}
            row["reason"]="ZERO_OVERRIDES_ARE_NOT_PROVIDED_REBAR" if all(v==0 for v in row["override_area_mm2"].values()) else "MODEL_OVERRIDES_ARE_NOT_QUALIFIED_END_CAGES"
        except OPTIONAL_ERRORS as exc:row["reason"]=str(exc)
        result.append(row)
    summary["unknown_native_member_ids"]=sorted(set(counts)-set(frames))
    return result,summary


def _joint_roster(node,direction,frames,points):
    """Strict global orthogonal scenario; oblique/unknown beams are retained."""
    vector=[1,0,0] if direction=="X" else [0,1,0]
    other=[0,1,0] if direction=="X" else [1,0,0]
    columns,beams,excluded,unknown,reasons=[],[],[],[],[]
    if node["coincident_other_point_ids"]:reasons.append("COINCIDENT_DISTINCT_POINT_IDS")
    if node["possible_interior_frame_connections"]:reasons.append("INTERIOR_FRAME_CONNECTION_NOT_BOUND")
    for item in node["incident_frames"]:
        frame=frames[item["frame_id"]];end=item["end"]
        if end not in ("I","J") or frame["point_"+end.lower()]!=node["point_id"] or frame["design_orientation"]!=item["design_orientation"]:
            raise BankError("SCWB_NATIVE_JOINT_MEMBERSHIP_MISMATCH")
        opposite=frame["point_j"] if end=="I" else frame["point_i"]
        delta=[a-b for a,b in zip(points[opposite]["xyz_m"],node["xyz_m"])];length=math.sqrt(sum(v*v for v in delta))
        if length<=GEOMETRY_TOL:raise BankError("SCWB_ZERO_LENGTH_FRAME")
        ray=[v/length for v in delta]
        if item["design_orientation"]==1:
            columns.append({"member_id":item["frame_id"],"end":end,"position":"BELOW" if delta[2]<-GEOMETRY_TOL else "ABOVE" if delta[2]>GEOMETRY_TOL else "UNRESOLVED"})
        elif item["design_orientation"]==2:
            beam={"member_id":item["frame_id"],"end":end,"side":None}
            if _parallel(ray,vector):
                beam["side"]="+" if sum(a*b for a,b in zip(ray,vector))>0 else "-";beams.append(beam)
            elif _parallel(ray,other):excluded.append(beam)
            else:
                beams.append(beam);unknown.append(beam);reasons.append("NONORTHOGONAL_BEAM_DIRECTION_NOT_BOUND")
        else:reasons.append("OTHER_INCIDENT_FRAME_NOT_CLASSIFIED")
    if len(columns)!=len({r["member_id"] for r in columns}) or len(beams)!=len({r["member_id"] for r in beams}):
        raise BankError("SCWB_DUPLICATE_JOINT_PARTICIPANT")
    return {"columns":sorted(columns,key=lambda r:r["member_id"]),"beams":sorted(beams,key=lambda r:r["member_id"]),
        "other_direction_beams":excluded,"unclassified_beams":unknown,"reasons":sorted(set(reasons)),
        "recorded_above_column_count":sum(c["position"]=="ABOVE" for c in columns),
        "recorded_below_column_count":sum(c["position"]=="BELOW" for c in columns),
        "normative_exception_applied":False}


def _column_reference(name,end,case,label,direction,frames,pairs,proposals,profiles,chain):
    row={"member_id":name,"end":end,"output_case":case,"candidate_label":label,"candidate_id":None,
        "axis":None,"n_source_kn":None,"capacity_knm":None,"tolerance_knm":None,"calculation":None,
        "source_state":None,"source_force_pair_id":None,"status":"COLUMN_CAPACITY_UNRESOLVED","reason":None,
        "source_cut_is_physical_joint_face":False,"earthquake_compatible_nd_selected":False,"final_design_eligible":False}
    try:
        frame=frames[name];axes=_vertical(frame);vector=[1,0,0] if direction=="X" else [0,1,0]
        aligned=[i for i in (1,2) if _parallel(axes[i],vector)]
        if len(aligned)!=1:raise BankError("SCWB_COLUMN_GLOBAL_AXIS_NOT_PRINCIPAL")
        axis="M3" if aligned[0]==1 else "M2";row["axis"]=axis
        cage=proposals.get((name,label));pair=pairs.get((name,case))
        if (not cage or cage["geometry_status"]!="PROPOSED_GEOMETRY_CALCULATED"
                or cage["area_ratio_status"]!="WITHIN_1_TO_4_PERCENT_REFERENCE"
                or cage["spacing_status"]=="BELOW_SPACING_REFERENCE" or not cage["tie_diameter_reference_met"]):
            raise BankError("SCWB_COLUMN_PROPOSAL_NOT_BOUND")
        row["candidate_id"]=cage["candidate_id"]
        profile=profiles[cage["profile_id"]];geometry=frame["geometry"]["section"]
        section=_section(profile,cage)
        if (profile["section_name"]!=geometry["section_name"]
                or (section.t2,section.t3)!=(geometry["local2_extent_mm"],geometry["local3_extent_mm"])):
            raise BankError("SCWB_COLUMN_SECTION_AXIS_MISMATCH")
        if not pair or pair["force_pair"] is None:raise BankError((pair or {}).get("force_reason") or "SCWB_FORCE_PAIR_NOT_BOUND")
        if pair["point_"+end.lower()]!=frame["point_"+end.lower()]:raise BankError("SCWB_FORCE_PAIR_POINT_MISMATCH")
        state=pair["force_pair"][end.lower()]
        n=-float(_number(state["native_values"]["P"],"P")*1000)
        row.update(source_state={k:deepcopy(state[k]) for k in ("state_id","source_row_id","native_key","native_values")},
            source_force_pair_id=pair["link_id"],n_source_kn=n/1000)
        calc=column_axis_capacity(section,n,axis)
        row.update(calculation=calc,capacity_knm=calc["capacity_knm"],tolerance_knm=calc["tolerance_knm"],status=calc["status"],reason=calc["reason"])
    except OPTIONAL_ERRORS as exc:row["reason"]=str(exc)
    row["reference_id"]="SCWB-COL-"+digest({"archive":chain["source_archive_sha256"],"member":name,"end":end,"case":case,
        "label":label,"direction":direction,"axis":row["axis"]})[:24]
    return row


def _summaries(nodes,rows,cases):
    groups=defaultdict(list)
    for row in rows:groups[(row["joint_id"],row["direction"],row["candidate_label"],row["rotation_sign"])].append(row)
    results=[]
    for node in nodes:
        for direction in ("X","Y"):
            for label in LABELS:
                for sign in (-1,1):
                    source=groups[(node["point_id"],direction,label,sign)]
                    if len(source)!=len(cases) or {r["output_case"] for r in source}!=set(cases):raise BankError("SCWB_SUMMARY_CASE_POPULATION_MISMATCH")
                    complete=bool(source) and all(r["sum_mrc_reference_knm"] is not None and not r["topology_reasons"] for r in source)
                    minimum=min((r["sum_mrc_reference_knm"] for r in source),default=None) if complete else None
                    roster=node["rosters"][direction]
                    results.append({"joint_id":node["point_id"],"elevation_m":node["xyz_m"][2],"direction":direction,"rotation_sign":sign,
                        "candidate_label":label,"column_ids":[c["member_id"] for c in roster["columns"]],
                        "beam_ids":[b["member_id"] for b in roster["beams"]],"expected_case_count":len(cases),
                        "calculated_column_sum_count":sum(r["sum_mrc_reference_knm"] is not None and not r["topology_reasons"] for r in source),
                        "sampled_minimum_column_sum_knm":minimum,"sampled_minimum_case_ids":[r["output_case"] for r in source if minimum is not None and r["sum_mrc_reference_knm"]==minimum],
                        "minimum_over_declared_static_cases_only":True,"normative_nd_minimum_proven":False,
                        "sum_mrb_knm":None,"scwb_ratio":None,"normalized_reference_ratio":None,
                        "status":"NO_STATIC_SOURCE_CASES" if not source else "TOPOLOGY_UNRESOLVED" if roster["reasons"] else
                            "NO_RECORDED_BEAM_IN_DIRECTION" if not roster["beams"] else
                            "BEAM_CAPACITY_NOT_BOUND" if complete else "COLUMN_AND_BEAM_INPUTS_INCOMPLETE",
                        "topology_reasons":roster["reasons"],"case_result_ids":[r["result_id"] for r in source],
                        "normative_exception_applied":False,"formal_compliance":"NOT_PROVEN","final_design_eligible":False})
    return results


def build_column_scwb(chain,cages,joints,kinematics,archive):
    cases=_validate(chain,cages,joints,kinematics,archive)
    graph=joints["graph"];frames={f["frame_id"]:f for f in graph["frames"]};points={p["point_id"]:p for p in graph["points"]}
    selected={m['member_id'] for m in cages['members']}
    graph_bound=graph['status']=='NATIVE_ENDPOINT_GRAPH_BOUND'
    if graph['status'] not in ('NATIVE_ENDPOINT_GRAPH_BOUND','BLOCKED_INPUTS'):raise BankError('SCWB_UNKNOWN_GRAPH_STATUS')
    if not graph_bound and (frames or points or graph['nodes']):raise BankError('SCWB_PARTIAL_GRAPH_NOT_QUALIFIED')
    if (len(frames)!=len(graph["frames"]) or len(points)!=len(graph["points"])
            or len({n["point_id"] for n in graph["nodes"]})!=len(graph["nodes"])):raise BankError("SCWB_DUPLICATE_GRAPH_IDENTITY")
    if graph["status"]=="NATIVE_ENDPOINT_GRAPH_BOUND":
        expected_nodes={frames[m][key] for m in selected for key in ("point_i","point_j")}
        if expected_nodes!={n["point_id"] for n in graph["nodes"]}:raise BankError("SCWB_JOINT_POPULATION_MISMATCH")
        for node in graph["nodes"]:
            expected={(f["frame_id"],end) for f in frames.values() for end,key in (("I","point_i"),("J","point_j")) if f[key]==node["point_id"]}
            actual=[(r["frame_id"],r["end"]) for r in node["incident_frames"]]
            if set(actual)!=expected or len(actual)!=len(expected):raise BankError("SCWB_INCOMPLETE_NATIVE_JOINT_ROSTER")
    beams,beam_summary=_beam_sources(archive,frames)
    beam_index={r["member_id"]:r for r in beams}
    proposals={(r["member_id"],r["label"]):r for r in cage_rows(cages)};profiles={p["profile_id"]:p for p in cages["profiles"]}
    pairs={(r["member_id"],r["output_case"]):r for r in kinematics["rows"]}
    references={};rows=[];nodes=[]
    for node in sorted(graph["nodes"],key=lambda n:n["point_id"]):
        item={"point_id":node["point_id"],"xyz_m":deepcopy(node["xyz_m"]),"rosters":{}}
        for direction in ("X","Y"):
            roster=_joint_roster(node,direction,frames,points);item["rosters"][direction]=roster
            for case in cases:
                for label in LABELS:
                    colrefs=[]
                    for col in roster["columns"]:
                        key=(col["member_id"],col["end"],case,label,direction)
                        if key not in references:references[key]=_column_reference(*key,frames,pairs,proposals,profiles,chain)
                        colrefs.append(references[key])
                    for sign in (-1,1):
                        context=JointCase(chain["source_run_id"],archive.sha256,node["point_id"],direction,sign,case,label)
                        capacities=[MemberMomentCapacity(context,r["member_id"],r["end"],"COLUMN",r["capacity_knm"],r["reference_id"],
                            r["tolerance_knm"] or 0,r["reason"]) for r in colrefs]
                        capacities += [MemberMomentCapacity(context,b["member_id"],b["end"],"BEAM",None,None,reason=beam_index[b["member_id"]]["reason"])
                            for b in roster["beams"]]
                        result=compute_scwb_joint_result(context,[(c["member_id"],c["end"]) for c in roster["columns"]],
                            [(b["member_id"],b["end"]) for b in roster["beams"]],capacities)
                        row={"joint_id":node["point_id"],"direction":direction,"rotation_sign":sign,"output_case":case,"candidate_label":label,
                            "context":asdict(context),"column_reference_ids":[r["reference_id"] for r in colrefs],
                            "beam_ids":[b["member_id"] for b in roster["beams"]],"topology_reasons":roster["reasons"],
                            "earthquake_direction_qualified":False,"source_cuts_are_physical_joint_faces":False,**result}
                        if roster["reasons"]:
                            row.update(status="TOPOLOGY_UNRESOLVED",sum_mrc_reference_knm=None,normalized_reference_ratio=None,reference_satisfied=None)
                        row["result_id"]="SCWB-CASE-"+digest(asdict(context))[:24];rows.append(row)
        nodes.append(item)
    summaries=_summaries(nodes,rows,cases)
    result={"schema":SCHEMA,"policy":POLICY,"axis_convention":AXIS_CONVENTION,"source_run_id":chain["source_run_id"],
        "source_archive_sha256":archive.sha256,"source_demand_result_sha256":chain["result_sha256"],
        "source_cages_result_sha256":cages["result_sha256"],"source_joints_result_sha256":joints["result_sha256"],
        "source_kinematics_result_sha256":kinematics["result_sha256"],"graph_status":graph["status"],"graph_reason":graph["reason"],
        "joint_node_count":len(nodes) if graph_bound else None,"column_end_count":sum(len(n["rosters"]["X"]["columns"]) for n in nodes),
        "selected_member_ids":sorted(selected),"selected_column_count":len(selected),"expected_column_end_count":2*len(selected),
        "source_population_status":"NATIVE_JOINT_GRAPH_BOUND" if graph_bound else "BLOCKED_NATIVE_JOINT_GRAPH",
        "unresolved_member_ends":[] if graph_bound else [{"member_id":name,"end":end,"reason":graph['reason']}
            for name in sorted(selected) for end in ('I','J')],
        "native_beam_count":len(beams) if graph_bound else None,"static_cases":cases,"scenario_labels":list(LABELS),"rows":rows,"nodes":nodes,
        "column_references":list(references.values()),"beam_sources":beams,"beam_summary_source":beam_summary,"summaries":summaries,
        "joint_case_count":len(rows),"expected_joint_case_count":len(nodes)*len(cases)*len(LABELS)*4 if graph_bound else None,
        "expected_column_reference_count":2*len(selected)*len(cases)*len(LABELS)*2,
        "column_reference_count":len(references),"calculated_column_reference_count":sum(r["capacity_knm"] is not None for r in references.values()),
        "calculated_column_sum_count":sum(r["sum_mrc_reference_knm"] is not None for r in rows),
        "status_counts":dict(sorted(Counter(r["status"] for r in summaries).items())),
        "column_reason_counts":dict(sorted(Counter(r["reason"] for r in references.values() if r["reason"]).items())),
        "scwb_ratio_count":0,"source_population_reduced":False,"selected_design":None,"actual_second_order_applied":False,
        "physical_joint_population_proven":False,"normative_exception_applied":False,"earthquake_compatible_minimum_proven":False,
        "required_beam_steel_used_as_capacity":False,"approximate_as_half_fallback_used":False,"open_basis":OPEN_BASIS.copy(),
        "adapted_sources":[SOURCE,SOURCE.replace("core/capacity_design.py","joints/scwb.py"),SOURCE.replace("core/capacity_design.py","joints/scwb_projection.py")],
        "code_reference":"https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf",
        "member_id_filter":None,"output_case_filter":None,"formal_compliance":"NOT_PROVEN","design_demand_authority":"DENIED","engineering_release":"NOT_READY"}
    result["result_sha256"]=digest(result)
    return result


def scwb_projection(result,member_id=None,output_case=None):
    """Filter joints by a column; never remove its neighbouring participants."""
    nodes=[n for n in result["nodes"] if member_id is None or any(c["member_id"]==member_id for c in n["rosters"]["X"]["columns"])]
    ids={n["point_id"] for n in nodes};cases=[c for c in result["static_cases"] if output_case is None or c==output_case]
    rows=[r for r in result["rows"] if r["joint_id"] in ids and r["output_case"] in cases]
    ref_ids={key for r in rows for key in r["column_reference_ids"]};beam_ids={b["member_id"] for n in nodes for roster in n["rosters"].values() for b in roster["beams"]}
    projected={**result,"member_id_filter":member_id,"output_case_filter":output_case,"nodes":nodes,"rows":rows,"static_cases":cases,
        "column_references":[r for r in result["column_references"] if r["reference_id"] in ref_ids],
        "beam_sources":[r for r in result["beam_sources"] if r["member_id"] in beam_ids],"summaries":_summaries(nodes,rows,cases),
        "filtered_joint_node_count":len(nodes) if result['joint_node_count'] is not None else None,
        "filtered_joint_case_count":len(rows),"neighbouring_participants_retained":True,
        "unresolved_member_ends":[r for r in result['unresolved_member_ends'] if member_id is None or r['member_id']==member_id]}
    projected["filtered_status_counts"]=dict(sorted(Counter(r["status"] for r in projected["summaries"]).items()))
    return deepcopy(projected)
