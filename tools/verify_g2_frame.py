"""Run two signed physical examples through run-pipeline and audit their sealed results."""
import argparse
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from math import fsum, isclose
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tests"))
from g2_frame_fixture import frame_source
from g2_section_oracle import independent_capacity
from tbdy_next.engineering.cli_adapter import run_cli
from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.design_scenario import _digest, _policy
from tbdy_next.engineering.g2_contract import frame_implementation_sha256, verify_frame_evidence
from tbdy_next.engineering.pipeline_snapshot import read_snapshot


def solve(root, exhaust):
    raw,request=frame_source(exhaust=exhaust)
    root.mkdir(parents=True,exist_ok=True)
    source=root/"frame.source"
    scenario=root/"scenario.json"
    source.write_bytes(raw)
    scenario.write_text(json.dumps(request,ensure_ascii=False),encoding="utf-8")
    args=argparse.Namespace(action="run-pipeline", source=source,design_scenario=scenario,out=root,case="Modal",
                            compare_run=None,beam_selection=None,column_selection=None)
    buffer=StringIO()
    with redirect_stdout(buffer):
        code=run_cli(args)
    if code:
        raise ArithmeticError(buffer.getvalue())
    summary=json.loads(buffer.getvalue())
    snapshot=read_snapshot(Path(summary["run_dir"]),input_sha=summary["input_sha256"])
    return raw,request,snapshot["results"]


def check(actual,expected,tolerance=1e-7):
    if not isclose(actual,expected,rel_tol=1.e-10,abs_tol=tolerance):
        raise ArithmeticError(f"Independent reference {expected} differs from {actual}")


def example(raw,request,st,negative):
    source=json.loads(raw)
    feature=source["column_axial"]
    forces=feature["force_source"]["rowsets"]
    expected_columns={f"C{f}{n}" for f in (1,2) for n in range(4)}
    if not (set(forces)==expected_columns):
        raise ValueError("Incomplete two-storey physical column population")
    it=st["report_evidence"]["alpha_iteration"]
    closure=st["r14_closure"]
    base={"source_sha256":sha256(raw).hexdigest(),"policy_sha256":_digest(_policy(request["column_selection"],"column_selection")),
          "terminal":it["status"],"iteration_count":it["iteration_count"],
          "feasibility":it["final_feasibility"]["status"],"feedback_consumed":it["feedback_consumed"]}
    if negative:
        return {**base,"unresolved_count":8-closure["numerically_closed_count"],"failures":it["final_feasibility"],
                "maximum_factor_applied":max((c["factor"] for step in it["trace"]
                    for c in step.get("case_evidence",[]) if c.get("factor")),default=1.)}
    if it["status"]!="FIXED_POINT_REFERENCE":
        raise ArithmeticError(str(it["final_feasibility"]))
    details=st["r10_live"]["per_member"]
    by_id={r["member_id"]:r for r in closure["columns"]}
    rev=it["final_demand_revision"]
    beam_max=0.
    for beam in st["beam_r10"]["beams"]:
        native=feature["r10_source"]["beam_force_source"]["rowsets"][beam["member_id"]]
        for end,z in zip(("I","J"),sorted(set(native["ObjSta"])),strict=True):
            cap=beam["ends"][end]["engineer_selection"]["capacity"]
            signed=[m for station,m in zip(native["ObjSta"],native["M3"]) if station==z]
            beam_max=max(beam_max,max(max(signed)/cap["positive_m3_knm"],min(signed)/cap["negative_m3_knm"]))
    if beam_max>1.:
        raise ArithmeticError(f"Physical signed beam face demand/capacity {beam_max:.6f}")
    capacities={}
    for uid,rr in details.items():
        native=next(r["section_evidence"] for r in st["column_pmm"]["members"] if r["member_id"]==uid)
        chosen=rr["engineer_column_selection"]["selected"]
        cuts=st["r08_local_slenderness"]["per_member"][uid]["magnified_selected_pmm"]["rows"]
        worst=max(cuts,key=lambda c:c["utilization"])
        capacities[uid]={**independent_capacity(native,chosen,worst),"combination":worst["combination"],
                         "station_m":worst["object_station_m"]}
    cases=[]
    constraints=source["example_context"]["equilibrium"]
    for c in constraints:
        if not (max(c["storey_shear_residuals_kn"]+[c["maximum_rotation_equilibrium_residual_knm"],
                 c["maximum_floor_balance_residual_kn"],c["condensation_displacement_error_m"]])<1e-7):
            raise ValueError("Independent static equilibrium residual exceeds the tolerance")
    for case in it["final_qualification"]["cases"]:
        story,direction,combo=(case[k] for k in ("story","direction","combination"))
        members=[]
        for t in case["terms"]:
            uid=t["member_id"]
            native=forces[uid]
            def bottom(name):
                index,=[i for i in range(native["NumberResults"]) if native["ObjSta"][i]==0.
                        and native["LoadCase"][i]==name]
                return native["V2" if direction=="X" else "V3"][index]
            reference=bottom(combo)-bottom("G")
            check(t["shear_kn"],reference)
            ratios=[]
            for end in ("I","J"):
                joint=[j for j in details[uid]["scwb_joints"] if j["target_end"]==end and j["direction"]==direction]
                if end=="I" and story=="S1":
                    if not (not joint and source["column_axial"]["r10_source"]["point_restraints"]["observations"]["F0"+uid[-1]]["local_dof"]==[True]*6):
                        raise ValueError("Fixed footing releases or joint connectivity differ")
                    continue
                j,=joint
                signs=[r for r in j["engineer_selected_scwb"]["cases"] if r["output_case"]==combo]
                if not (sorted(r["rotation_sign"] for r in signs)==[-1,1]):
                    raise ValueError("Both joint rotation senses are required")
                for row in signs:
                    ref=row["sum_mrc_reference_knm"]/(1.2*row["sum_mrb_reference_knm"])
                    check(ref,row["normalized_reference_ratio"])
                    ratios.append(ref)
            credit=all(r>=1. for r in ratios)
            if not (t["numerator_eligible"]==credit and t["amplification_eligible"]==credit and not t["low_axial_credit_used"]):
                raise ValueError("Story shear credit disagrees with the two signed end checks")
            members.append({"id":uid,"credited":credit,"minimum_joint_ratio":min(ratios),
                            "reference_earthquake_shear_kn":reference,"native_earthquake_shear_kn":t["shear_kn"]})
        vik=fsum(abs(r["reference_earthquake_shear_kn"]) for r in members)
        vis=fsum(abs(r["reference_earthquake_shear_kn"]) for r in members if r["credited"])
        check(vis/vik,case["alpha"])
        check(vik/vis,case["factor"])
        cases.append({"story":story,"direction":direction,"combination":combo,"members":members,
                      "alpha":case["alpha"],"factor":case["factor"]})
    changes={}
    for step in it["trace"]:
        for uid,row in step["actions"]["selected_layout_changes"].items():
            if uid not in changes: changes[uid]=dict(row)
            else: changes[uid]["after"]=row["after"]
    changed=[]
    for uid,row in changes.items():
        if row["before"]==row["after"]:
            continue
        rr=details[uid]
        mag=st["r08_local_slenderness"]["per_member"][uid]["magnified_selected_pmm"]
        if not (mag["expected_row_count"]==mag["resolved_row_count"]==15):
            raise ValueError("Missing selected-cage second-order PMM cut")
        candidates=[]
        for cut in mag["rows"]:
            name=cut["combination"]
            native=forces[uid]
            j,=[i for i in range(native["NumberResults"]) if native["ObjSta"][i]==cut["object_station_m"]
                and native["LoadCase"][i]==name and native["Elm"][i]==cut["analysis_element_id"]]
            for axis,index in (("M2",2),("M3",3)):
                factor=rev["factors"].get(uid,{}).get(name,[1]*4)[index]
                if factor<=1.: continue
                original=native[axis][j]
                revised=cut["first_order_"+axis.lower()+"_knm"]
                check(revised,factor*original)
                candidates.append((abs(revised),name,axis,cut["object_station_m"],factor,original,revised))
        _,name,axis,z,factor,original,revised=max(candidates)
        ve=rr["column_transverse_and_shear"]["engineer_capacity_shear_ve"]["axes"]
        vre=[]
        for v_axis,detail in ve.items():
            if not (detail["expected_combination_count"]==detail["evaluated_combination_count"]==5):
                raise ValueError("Incomplete capacity-shear combination census")
            for v in detail["cases"]:
                combo=v["combination"]
                ends={}
                for joint in rr["scwb_joints"]:
                    if joint["direction"]==detail["direction"]:
                        ends[joint["target_end"]]=max(case["target_column_capacity_knm"]
                            for case in joint["engineer_selected_scwb"]["cases"] if case["output_case"]==combo)
                native=forces[uid]
                indices=[i for i,c in enumerate(native["LoadCase"]) if c==combo]
                axial=[native["P"][i] for i in indices]
                if max(axial)-min(axial)>1e-8:
                    raise ValueError("Reference requires constant section compression over this physical member")
                # At the prismatic fixed foot the same cage and signed compression give
                # the same principal Mr as the physical upper end in this example.
                mi=ends.get("I",ends["J"])
                ln=rr["column_transverse_and_shear"]["engineer_capacity_shear_ve"]["clear_length_m"]
                shear=(1.4*mi+1.4*ends["J"])/ln
                check(v["ve_unreduced_kn"],shear)
                factor_v=rev["factors"].get(uid,{}).get(combo,[1]*4)[0 if v_axis=="V2" else 1]
                floor=max(abs(native[v_axis][i])*factor_v for i in indices)
                check(v["vd_floor_kn"],floor)
                effective=max(shear,floor)
                check(v["ve_scwb_scenario_kn"],effective)
                check(v["utilization_ts500"],effective/v["vr_ts500_min_kn"])
                check(v["utilization_zero_concrete"],effective/v["vr_zero_concrete_min_kn"])
                if not (effective+1e-7>=v["vd_floor_kn"]):
                    raise ValueError("Capacity shear falls below the signed demand")
                vre.extend((v["utilization_ts500"],v["utilization_zero_concrete"]))
        joints=[]
        for end in rr["member_joint_ends"]:
            for a in end["axes"]:
                if not a.get("calculation"):continue
                s=a["joint_shear_ve"]
                if not (s["v_kol_used_kn"]==0 and s["within_geometric_limit"]):
                    raise ValueError("Joint equilibrium exceeds the geometric limit or uses an unverified deduction")
                # Swapping the sway sense swaps tension faces. An absent beam
                # contributes zero steel at a physical exterior joint.
                faces=list(s["faces"].values())
                ta,tb=([1.25*f["fyk_mpa"]*f["as_"+side+"_mm2"]/1000 if f["present"] else 0. for f in faces]
                       for side in ("top","bot"))
                check(max(ta[0]+tb[1],tb[0]+ta[1]),s["governing_ve_kn"])
                check(s["governing_ve_kn"]/a["calculation"]["geometric_limit_kn"],s["utilization"])
                t=a["joint_transverse_7_5_2_3"]
                if not (t["all_references_met"] and t["proposed_ash_mm2"]>=t["required_ash_at_joint_spacing_mm2"]-1e-7):
                    raise ValueError("Joint transverse reinforcement is insufficient")
                joints.append(s["utilization"])
        changed.append({"id":uid,"original_cage":row["before"],"revised_cage":row["after"],
            "factor":factor,"combination":name,"axis":axis,"station_m":z,"original_moment_knm":original,
            "revised_moment_knm":revised,"maximum_pmm_ratio":mag["max_utilization"],"maximum_ve_ratio":max(vre),
            "maximum_joint_ratio":max(joints),"joint_ties_satisfied":True,"r14":by_id[uid]["status"]})
    scope=st["report_evidence"]["column_pmm_expected_instances"]
    return {**base,"equilibrium":constraints,"checked_beam_faces":16,"maximum_signed_beam_ratio":beam_max,
            "independent_sections":capacities,"expected_cuts":120,"observed_cuts":sum(
            r["configured_cut_coverage"]["matched_count"] for r in scope["instances"]),
            "cases":cases,"cage_changes":changed,"columns_closed":closure["numerically_closed_count"],
            "beams":st["beam_r10"]["calculated_beam_count"]}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output",type=Path,required=True)
    cli.add_argument("--work",type=Path)
    cli.add_argument("--verify-receipts",action="store_true",help="Reopen the two sealed example runs from --work")
    args=cli.parse_args()
    if args.verify_receipts and not args.work:
        cli.error("--verify-receipts requires --work")
    with TemporaryDirectory() as tmp:
        root=args.work or Path(tmp)
        methods={p:sha256((ROOT/p).read_text(encoding="utf-8").encode()).hexdigest() for p in
                 ("tests/g2_frame_fixture.py","tests/g2_section_oracle.py","tests/vertical_slice_fixture.py","tools/verify_g2_frame.py")}
        packet={"schema":"tbdy.next.g2-frame-examples.v1","implementation_sha256":frame_implementation_sha256(),
                "independent_methods_sha256":methods}
        for name in ("positive","negative"):
            if args.verify_receipts:
                folder=root/name
                directory,=folder.glob("RUN-*")
                raw=(folder/"frame.source").read_bytes()
                request=json.loads((folder/"scenario.json").read_bytes())
                if archive_bytes(directory/"parent.source")!=raw or sha256(raw).hexdigest()!=request["parent_input_sha256"]:
                    raise ValueError("Example parent source does not match the archived physical model")
                final_sha=sha256(archive_bytes(directory/"input.source")).hexdigest()
                st=read_snapshot(directory,input_sha=final_sha)["results"]
                lineage=st["report_evidence"]["design_scenario"]
                if (lineage["policies"]["column_selection"]!=_policy(request["column_selection"],"column_selection")
                        or lineage["parent_input_sha256"]!=request["parent_input_sha256"]
                        or lineage["scenario_id"]!=request["scenario_id"]):
                    raise ValueError("Example policy does not match the sealed run")
            else:
                raw,request,st=solve(root/name,name=="negative")
            packet[name]=example(raw,request,st,name=="negative")
        verify_frame_evidence(packet)
        args.output.write_text(json.dumps(packet,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("G2 independent frame checks passed")


if __name__=="__main__":
    main()
