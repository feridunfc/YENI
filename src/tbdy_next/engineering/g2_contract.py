"""Replayable G2 evidence for signed frame feedback and scoped report comparisons."""
from hashlib import sha256
from importlib.resources import files
import json
from math import hypot, isclose, isfinite

from .design_scenario import _digest
from .g1_contract import ACCEPTED_CONTRACT
from ..verification.golden_gate import build_golden_gate, golden_gate_summary


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _reference(name):
    raw = files("tbdy_next.verification").joinpath("data",name).read_bytes()
    value=json.loads(raw)
    return value,_digest(value)


def _c29(model_sha):
    data, digest = _reference("g2_c29_reference.json")
    require(digest=="9ad3e6faa6cc6facb3aa5a6cc757e9e35b1b0704375ba2b806cb3e340a2c8bb1","C29_VERIFIED_REFERENCE_IDENTITY")
    require(data["model_sha256"]==model_sha and data["independent_receipt_sha256"]==
            "3e5cd9361b889400502be143931eecb8fe56d1bef50e4c9be27aca8ad9280e3a","C29_ARCHIVE_IDENTITY")
    cases = {"Grav_Ult","Grav_TempNeg","Grav_TempPos"}
    rows=data["faces"]
    keys=set()
    for row in rows:
        k=row["identity"]
        key=(k["member"],k["combination"],k["physical_cut"],k["element"],k["side"])
        require(key not in keys,"C29_DUPLICATE_SECTION")
        keys.add(key)
        difference=abs(row["reference_capacity_knm"]-row["independent_capacity_knm"])
        require(isclose(difference,row["metrics"]["capacity_difference_knm"],abs_tol=1e-9)
                and set(row["metrics"])==set(data["tolerances"])
                and all(0<=v<=data["tolerances"][name] for name,v in row["metrics"].items())
                and row["n_kn"]>0 and isclose(hypot(*row["design_moments_knm"])/row["independent_capacity_knm"],
                                              row["independent_utilization"],abs_tol=1e-10),"C29_REFERENCE_RESIDUAL")
    groups={(a,b,c) for a,b,c,_,_ in keys}
    require(len(keys)==24 and len(groups)==18 and {x[0] for x in groups}=={"142","225"}
            and all(sum(k[:2]==(uid,name) for k in keys)==4 for uid in ("142","225") for name in cases),
            "C29_EXPECTED_PHYSICAL_FACES")
    return {"reference_sha256":digest,"independent_receipt_sha256":data["independent_receipt_sha256"],
            "faces":len(keys),"physical_combination_cuts":len(groups),"model_sha256":model_sha,
            "maximum_difference_knm":max(r["metrics"]["capacity_difference_knm"] for r in rows),
            "tolerance_knm":data["tolerances"]["capacity_difference_knm"]}


def _golden():
    report=build_golden_gate()
    golden_gate_summary(report)
    rows=report["comparisons"]
    require(len(rows)==len({r["id"] for r in rows})==44 and report["classification_counts"]==
            {"NUMERICAL_MATCH":36,"ENGINEERING_INTERPRETATION_DIFFERENCE":4,"INSUFFICIENT_SOURCE":4},
            "GOLDEN_EXPECTED_RECORDS")
    branches, outside = [], []
    for row in rows:
        if row["classification"]=="ENGINEERING_INTERPRETATION_DIFFERENCE":
            beta=row["yeni_beta"]
            beta_s=row["yeni_beta_story"]
            reading=row["printed_symbol_probe"]
            product=beta*beta_s
            printed=product if reading["lk_over_i"]>reading["threshold"] else max(beta,beta_s)
            require(not reading["product_branch_from_printed_symbol"] and printed==max(beta,beta_s)
                    and abs(row["report"]-product)<=row["report_rounding_tolerance"]
                    and abs(row["report"]-printed)>row["report_rounding_tolerance"],"EQ729_SOURCE_BRANCH_MISMATCH")
            branches.append({"id":row["id"],"reported":row["report"],"product":product,"printed_symbol":printed,
                             "lk_over_i":reading["lk_over_i"],"threshold":reading["threshold"],
                             "tolerance":row["report_rounding_tolerance"]})
        elif row["classification"]=="INSUFFICIENT_SOURCE":
            require(row["yeni"] is None and bool(row["explanation"]),"GOLDEN_SCOPE_UNSUPPORTED")
            outside.append({"id":row["id"],"reason":row["explanation"]})
    require(len(branches)==len(outside)==4 and len(rows)-len(branches)-len(outside)==36,"GOLDEN_CLASSES")
    return {"records":len(rows),"counts":report["classification_counts"],"row_table_sha256":_digest(rows),
            "source_manifest_sha256":report["source_manifest_sha256"],"eq729_readings":branches,
            "source_limited":outside,"scope":"FROZEN_44_REPORT_RECORDS"}


def frame_implementation_sha256():
    base=files("tbdy_next")
    paths=("engineering/alpha_iteration.py","engineering/column_r10_live.py","engineering/column_r14_closure.py",
           "engineering/column_r08_local_live.py","engineering/design_dependencies.py","engineering/pipeline.py",
           "engineering/scwb_axial.py","engineering/beam_r10_live.py","engineering/rebar_selection.py",
           "engineering/column_pmm_section.py","engineering/column_clear_length.py","column_engine/ts500_column.py",
           "column_engine/story_alpha.py","column_engine/section_capacity.py",
           "column_engine/joint_kernel.py","column_engine/transverse_kernel.py")
    return _digest({path:sha256(base.joinpath(*path.split("/")).read_text(encoding="utf-8").encode()).hexdigest()
                    for path in paths})


def verify_frame_evidence(doc):
    """Recalculate denominators, factors, load revisions and actual terminal outcomes."""
    require(doc["schema"] == "tbdy.next.g2-frame-examples.v1", "FRAME_REFERENCE_SCHEMA")
    current = frame_implementation_sha256()
    if doc["implementation_sha256"] != current:
        # A frozen example may be consumed by another producer only after its
        # independent end-to-end replay reproduces every field except producer identity.
        require(_digest(doc) == FRAME_REFERENCE_SHA256
                and _digest({**doc, "implementation_sha256": current}) == FRAME_REPLAY_SHA256,
                "FRAME_IMPLEMENTATION_CHANGED")
    report = doc["positive"]
    require(report["feedback_consumed"] is True and report["terminal"]=="FIXED_POINT_REFERENCE" and report["feasibility"]=="FEASIBLE_REFERENCE"
            and report["iteration_count"]>=1 and report["columns_closed"]==8 and report["beams"]==8,
            "FRAME_POSITIVE_TERMINAL_REQUIRED")
    require(report["expected_cuts"]==report["observed_cuts"]==120 and len(report["cases"])==16,
            "FRAME_COMPLETE_PHYSICAL_CENSUS")
    ids={(s,d,c) for s in ("S1","S2") for d in "XY" for c in ("G+EX","G-EX","G+EY","G-EY")}
    require({(r["story"],r["direction"],r["combination"]) for r in report["cases"]}==ids,
            "FRAME_ASSIGNED_CASE_CENSUS")
    require(report["checked_beam_faces"]==16 and 0.<report["maximum_signed_beam_ratio"]<=1.,
            "FRAME_SIGNED_BEAM_CAPACITY")
    require(set(report["independent_sections"])=={"C"+str(s)+str(n) for s in (1,2) for n in range(4)},
            "FRAME_GOVERNING_SECTION_CENSUS")
    for row in report["independent_sections"].values():
        require(isclose(abs(row["production_knm"]-row["capacity_knm"]),row["difference_knm"],abs_tol=1e-9)
                and 0<=row["difference_knm"]<=.01 and 0<=row["axial_residual_n"]<=.001
                and 0<=row["perpendicular_residual_nmm"]<=.001 and 0<row["utilization"]<=1.,
                "FRAME_INDEPENDENT_FIXED_AXIAL_SECTION")
    require({r["axis"] for r in report["equilibrium"]}==set("XY"),"FRAME_PLANE_CENSUS")
    for plane in report["equilibrium"]:
        require(set(plane["non_sway_indices"])=={"S1","S2"} and
                all(0<=v<=.05 for v in plane["non_sway_indices"].values()) and
                max(plane["storey_shear_residuals_kn"]+[plane["maximum_rotation_equilibrium_residual_knm"],
                    plane["maximum_floor_balance_residual_kn"],plane["condensation_displacement_error_m"]])<1e-7,
                "FRAME_STATIC_EQUILIBRIUM")
    subunit=False
    for case in report["cases"]:
        terms=case["members"]
        require({r["id"] for r in terms}=={"C"+case["story"][-1]+str(i) for i in range(4)} and len(terms)==4,
                "FRAME_STOREY_POPULATION")
        vik=sum(abs(r["reference_earthquake_shear_kn"]) for r in terms)
        vis=sum(abs(r["reference_earthquake_shear_kn"]) for r in terms if r["credited"])
        require(all(r["credited"]==(r["minimum_joint_ratio"]>=1.) for r in terms) and vis>0 and vik>0,
                "FRAME_SIGNED_CREDIT_OR_DENOMINATOR")
        alpha=vis/vik
        require(.7<=alpha<=1.+1e-12 and abs(alpha-case["alpha"])<1e-10
                and abs(case["factor"]-1/alpha)<1e-10,"FRAME_INDEPENDENT_ALPHA")
        subunit |= alpha<1.-1.e-8
        for r in terms:
            require(abs(r["native_earthquake_shear_kn"]-r["reference_earthquake_shear_kn"])<1e-7,
                    "FRAME_FORCE_REFERENCE")
    require(subunit and bool(report["cage_changes"]),"FRAME_RESELECTION_REQUIRED")
    for row in report["cage_changes"]:
        require(row["original_cage"]!=row["revised_cage"] and row["factor"]>1.
                and abs(row["original_moment_knm"]*row["factor"]-row["revised_moment_knm"])<1e-7
                and 0<row["maximum_pmm_ratio"]<=1. and 0<=row["maximum_ve_ratio"]<=1.
                and 0<=row["maximum_joint_ratio"]<=1. and row["joint_ties_satisfied"] is True
                and row["r14"]=="R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES","FRAME_DEPENDENCY_CHAIN")
    boundary=doc["negative"]
    require(boundary["terminal"] in ("NO_FEASIBLE_CANDIDATE","NO_CONVERGENCE","NO_CONVERGENCE_CYCLE")
            and boundary["feedback_consumed"] is False and boundary["unresolved_count"]>0
            and boundary.get("maximum_factor_applied",0)>1. and boundary["iteration_count"]>=1
            and boundary["source_sha256"]==report["source_sha256"] and boundary["policy_sha256"]!=report["policy_sha256"],
            "FRAME_NEGATIVE_TERMINAL_REQUIRED")
    return {"positive":report,"negative":boundary,"example_sha256":_digest(doc)}


def _calibrated_c29(source, local):
    # The independently integrated eight-element example and the original
    # building have different meshes and EDB identities. Bind each to its own seal.
    evidence=_c29("685f5f45e7448c8c471a2c041c65c681447cc02175846bbf82ae172139a8c283")
    require(source["analysis_archive"]["observed_edb_sha256"]=="0ce0e970988def9776f9d4804b8897f6e08d6ac3e4937aa72ebec941314cfb15"
            and _digest(source["gravity_order_pair"])=="c71ec940b1cb367a2aa799a556f5d1c9807de41e8474cf2f25044da2d3d5efeb",
            "ORIGINAL_C29_CALIBRATION_ARCHIVE")
    keys=("stiffness_and_euler","magnified_selected_pmm","spectral_envelope_pmm_scenario","combination_scenarios")
    expected={"142":"97c070f420c0c76ec23e4b3c844da89953a94acd3a1178201941b65fd0d7311f",
              "225":"c0d01a5b8e0f6c2bf77ec1a3f90697e5fa0600365f8cc42d989b68af4782b7c3"}
    observed={uid:_digest({k:local["per_member"][uid][k] for k in keys}) for uid in expected}
    require(observed==expected,"ORIGINAL_C29_CALIBRATED_RESULTS_CHANGED")
    return {**evidence,"scope":"Independent eight-element C29 section study and separate original-building calibration",
            "original_edb_sha256":source["analysis_archive"]["observed_edb_sha256"],
            "original_reference_results_sha256":"998c1098a8fdaab11a4789c30564dc8ab31dac949a59294377769b1d317d5565",
            "original_calibration_sha256":observed}


def _frame():
    reference,digest=_reference("g2_frame_examples.json")
    require(digest==FRAME_REFERENCE_SHA256,"FRAME_SIGNED_REFERENCE_IDENTITY")
    return verify_frame_evidence(reference)


FRAME_REFERENCE_SHA256="80a75a9d6b1dd6a9d9efdbf4ba7aedd4c98442c5a3518ae60757e3f8efa3d1a3"
# The independent complete replay includes the producer fingerprint in its checksummed data.
# The later producer treats missing legacy story terms as ineligible for SCWB credit.
FRAME_REPLAY_SHA256="5b4c97c6ca9c5d059f7495a3e0537d0a22e27d0fee11d5a284d9b50bd08567ce"


def g2_contract(g1,source,local):
    packet={"schema":"tbdy.next.g2-contract.v1","input_sha256":g1.get("input_sha256"),"g1_contract_sha256":g1.get("contract_sha256"),
            "g1_reviewed_sha256":(g1.get("supervisor_acceptance") or {}).get("reviewed_contract_sha256"),
            "decision":"SUPERVISOR_REVIEW","engineering_release":"NOT_READY","evidence":{}}
    evidence=packet["evidence"]
    errors={}
    for name,compute in (("golden",_golden),("c29",lambda:_calibrated_c29(source, local)),
                         ("frame",_frame)):
        try:
            evidence[name]=compute()
        except (OSError,ValueError,TypeError,KeyError,IndexError,ArithmeticError) as exc:
            errors[name]=str(exc) if not isinstance(exc,OSError) else "FRAME_REFERENCE_FILE_UNAVAILABLE"
    accepted=(packet["g1_reviewed_sha256"]==ACCEPTED_CONTRACT and g1.get("decision")=="SUPERVISOR_ACCEPTED"
              and g1.get("contract_sha256")==_digest({k:v for k,v in g1.items() if k!="contract_sha256"})
              =="070ac74e3b57f7f3b77f8327d0e218aa3b5f09af7766a9f23939ec64868468f2")
    packet["gaps"]={k:{"status":"PARTIAL","closure_ready":accepted and all(n in evidence for n in names),
                        "supervisor_approval":"PENDING"} for k,names in (("GAP-013",("frame",)),("GAP-016",("golden","c29","frame")))}
    packet["unresolved"]=errors
    return {**packet,"contract_sha256":_digest(packet)}


def verification_record(directory, building, input_sha):
    """Compare the persisted packets with the authoritative recorded building stage."""
    digests = {}
    for name in ("g1","g2"):
        path=directory/(name+"-contract.json")
        data=path.read_bytes()
        packet=json.loads(data)
        require(packet==building[name+"_contract"] and packet["input_sha256"]==input_sha
                and packet["contract_sha256"]==_digest({k:v for k,v in packet.items() if k!="contract_sha256"}),
                "PERSISTED_"+name.upper()+"_CONTRACT_MISMATCH")
        digests[path.name]=sha256(data).hexdigest()
    g2=building["g2_contract"]
    require(g2["g1_contract_sha256"]==building["g1_contract"]["contract_sha256"],"G2_G1_CROSS_LINK")
    record={"schema":"tbdy.next.g2-verification.v1","input_sha256":input_sha,"files_sha256":digests,
            "contract_sha256":g2["contract_sha256"],"gaps":g2["gaps"],
            "evidence_sha256":{k:_digest(v) for k,v in g2["evidence"].items()}}
    return {**record,"verification_sha256":_digest(record)}
