"""CE-06A: proposed transverse layouts and full static-source shear scenarios.

No new archive or database. Native confinement steel is read independently
from longitudinal steel. Every result remains a proposal/reference, never an
authorized seismic Ve, actual confinement detail or chosen reinforcement.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import math

from .column_pmm import DIAMETERS, POLICY as CAGE_POLICY, REFERENCES as CAGE_REFERENCES, _native
from .column_prechecks import _number
from .column_stability import OPTIONAL_ERRORS
from .csi_geometry import AXIS_CONVENTION, local_dimensions
from .native_archive import BankError, digest
from .section_capacity import perimeter
from .transverse_kernel import confinement_reference, shear_reference, zero_concrete_gate
from .ts500_column import positive

POLICY = {"id":"CE06A_T12_S100_OUTER_PLUS_3_CROSSTIES_EACH_AXIS",
    "spacing_mm":100,"closed_outer_hoop_count":1,"crossties_per_axis":3,
    "gamma_concrete":CAGE_POLICY["gamma_concrete"],"gamma_steel":CAGE_POLICY["gamma_steel"],
    "ductility_scenario":"HIGH_DUCTILITY_REFERENCE_ONLY",
    "origin":"EXPLICIT_PROPOSAL_NOT_NATIVE_TIE_LABELS_OR_COUNTS",
    "project_applicability_approved":False,"physical_arrangement_proven":False,
    "automatic_design_selection":False}
REFERENCES = {"tbdy":"https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf",
    "ts500":CAGE_REFERENCES["ts500"],"cover":CAGE_REFERENCES["cover"],
    "shear_kernel":"https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/regulatory/column_shear_p7.py",
    "confinement_kernel":"https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/regulatory/column_transverse_confinement.py"}
OPEN_BASIS = ["PROPOSED_LAYOUT_NOT_SELECTED_OR_AS_BUILT", "HOOK_ANCHORAGE_AND_3D_CONGESTION_NOT_PROVEN",
    "PROJECT_DUCTILITY_AND_MATERIAL_FACTORS_NOT_APPROVED", "STEEL_GRADE_COMPLIANCE_NOT_PROVEN",
    "DESIGN_CUT_AND_FREE_HEIGHT_NOT_BOUND", "CAPACITY_END_MOMENTS_AND_SEISMIC_D_NOT_BOUND",
    "EARTHQUAKE_SHARE_AND_CONFINEMENT_LOCATION_NOT_BOUND", "FULL_DESIGN_AXIAL_POPULATION_NOT_PROVEN",
    "TORSION_SHEAR_INTERACTION_NOT_ASSESSED", "SECOND_ORDER_NOT_APPLIED"]


def _steel(profile,archive):
    rebar,source = _native(archive,"PropFrame.GetRebarColumn","column_section",profile["section_name"])
    if source != profile["source_calls"]["rebar_setting"]:
        raise BankError("TRANSVERSE_REBAR_SOURCE_MISMATCH")
    if type(rebar["Pattern"]) is not int or rebar["Pattern"]!=1:
        raise BankError("TRANSVERSE_RECTANGULAR_PATTERN_NOT_BOUND")
    # CSI ConfineType is applicable only to Pattern=2. A real Pattern=1
    # capture can return 0 here; it must not block a rectangular proposal.
    steel,steel_source = _native(archive,"PropMaterial.GetORebar_1","material",rebar["MatPropConfine"])
    fy = positive(float(_number(steel["FY"],"confinement_FY")/1000),"fywk")
    return {"profile_id":profile["profile_id"],"section_name":profile["section_name"],
        "confinement_material":rebar["MatPropConfine"],"observed_fywk_mpa":fy,
        "scenario_fywd_mpa":fy/POLICY["gamma_steel"],"fck_mpa":profile["material"]["fck"],
        "source_calls":{"rebar_setting":source,"confinement_steel":steel_source},
        "model_pattern":rebar["Pattern"],"model_confine_type_unused":rebar["ConfineType"],
        "material_from":"GetRebarColumn.MatPropConfine","steel_grade_compliance":"NOT_PROVEN"}


def proposed_layout(cage):
    """One closed hoop plus three orthogonal crossties each way, per 100 mm.

Straight axes are projection geometry only; hooks, bends and vertical stacking
are deliberately unresolved. Ack is OUTSIDE to OUTSIDE, bk AXIS to AXIS.
Asw sums legs parallel to shear; Ash sums projections perpendicular to bk.
Their equality follows from this explicit orthogonal layout, not a general
substitution between the two quantities.
"""
    if cage["geometry_status"]!="PROPOSED_GEOMETRY_CALCULATED":
        raise BankError("TRANSVERSE_LONGITUDINAL_GEOMETRY_NOT_BOUND")
    w,h = local_dimensions(cage["t2_mm"],cage["t3_mm"])
    c,t,p = (positive(cage[key],key) for key in
        ("clear_cover_to_tie_mm","tie_diameter_mm","bar_diameter_mm"))
    bars,center,_ = perimeter(w,h,c,t,p)
    if cage["bars"] != [{"x2_mm":b.x2,"x3_mm":b.x3,"area_mm2":b.area,"diameter_mm":p} for b in bars]:
        raise BankError("TRANSVERSE_BAR_COORDINATES_MISMATCH")
    k2,k3 = w-2*c-t,h-2*c-t
    area = math.pi*t*t/4
    # Each straight leg is counted once. Hook returns are not extra shear legs.
    legs = []
    for axis,span,other_span,bar_other in ((2,k2,k3,h-2*center),(3,k3,k2,w-2*center)):
        positions = [-other_span/2,-bar_other/4,0,bar_other/4,other_span/2]
        for index,position in enumerate(positions):
            ends = [[-span/2,position],[span/2,position]] if axis==2 else [[position,-span/2],[position,span/2]]
            legs.append({"leg_id":f"L{axis}-{index}","parallel_axis":axis,"diameter_mm":t,
                "area_mm2":area,"endpoints_mm":ends,"position_mm":position,
                "kind":"OUTER_HOOP_LEG" if index in (0,4) else "CROSSTIE"})
    axes = {}
    for axis,bw,depth,bk in ((2,h,w,k3),(3,w,h,k2)):
        active = [leg for leg in legs if leg["parallel_axis"]==axis]
        positions = [leg["position_mm"] for leg in active]
        asw = sum(leg["area_mm2"] for leg in active)
        # Projection is exactly one for these perpendicular orthogonal legs.
        ash = sum(leg["area_mm2"]*1 for leg in legs if leg["parallel_axis"]!=5-axis)
        axes[f"V{axis}"] = {"shear_axis":f"V{axis}","bw_mm":bw,"d_mm":depth-center,
            "effective_depth_basis":"OPPOSITE_OUTERMOST_LONGITUDINAL_LAYER_CENTROID_REFERENCE",
            "bk_axis":5-axis,"bk_mm":bk,"asw_mm2":asw,"ash_mm2":ash,
            "asw_leg_ids":[leg["leg_id"] for leg in active],
            "ash_leg_ids":[leg["leg_id"] for leg in legs if leg["parallel_axis"]!=5-axis],
            "maximum_lateral_leg_spacing_mm":max(b-a for a,b in zip(positions,positions[1:]))}
    return {"gross_area_mm2":w*h,"core_area_mm2":(w-2*c)*(h-2*c),
        "core_outside_dimensions_mm":[w-2*c,h-2*c],"core_axis_dimensions_mm":[k2,k3],
        "core_area_basis":"OUTSIDE_OF_OUTERMOST_HOOP_TBDY_7_0_ACK",
        "bk_basis":"AXES_OF_OUTERMOST_HOOP_TBDY_7_0_BK",
        "tie_diameter_mm":t,"spacing_mm":POLICY["spacing_mm"],"legs":legs,"axes":axes,
        "straight_projection_only":True,"physical_arrangement_proven":False}


def _proposal(cage,material):
    row = {"candidate_id":cage["candidate_id"],"candidate_label":cage["label"],"profile_id":cage["profile_id"],
        "status":"BLOCKED_INPUTS","reason":cage.get("reason"),"layout":None,"axes":{},
        "selected_design":False,"physical_arrangement_proven":False}
    try:
        if cage["area_ratio_status"]!="WITHIN_1_TO_4_PERCENT_REFERENCE" or cage["spacing_status"]=="BELOW_SPACING_REFERENCE":
            raise BankError("TRANSVERSE_CAGE_OUTSIDE_REFERENCE_GEOMETRY")
        layout = proposed_layout(cage)
        t,s,fc,fy = layout["tie_diameter_mm"],layout["spacing_mm"],material["fck_mpa"],material["observed_fywk_mpa"]
        bmin,bmax = min(cage["t2_mm"],cage["t3_mm"]),max(cage["t2_mm"],cage["t3_mm"])
        high_spacing = min(bmin/3,6*cage["bar_diameter_mm"],150)
        middle_spacing = min(bmin/2,200)
        general_spacing = min(12*cage["bar_diameter_mm"],200)
        for key,axis in layout["axes"].items():
            ref = confinement_reference(area_mm2=layout["gross_area_mm2"],core_area_mm2=layout["core_area_mm2"],
                bk_mm=axis["bk_mm"],spacing_mm=s,fck_mpa=fc,fywk_mpa=fy,ash_mm2=axis["ash_mm2"])
            row["axes"][key] = {**axis,"confinement":ref,
                "lateral_spacing_reference_met":axis["maximum_lateral_leg_spacing_mm"]<=25*t}
        row.update(status="PROPOSED_TRANSVERSE_REFERENCES_CALCULATED",reason=None,layout=layout,
            confinement_spacing_min_mm=50,confinement_spacing_max_mm=high_spacing,
            confinement_spacing_reference_met=50<=s<=high_spacing,
            middle_spacing_max_mm=middle_spacing,middle_spacing_reference_met=s<=middle_spacing,
            ts500_general_spacing_max_mm=general_spacing,ts500_general_spacing_reference_met=s<=general_spacing,
            minimum_tie_diameter_mm=max(8,cage["bar_diameter_mm"]/3),
            tie_diameter_reference_met=t>=max(8,cage["bar_diameter_mm"]/3),
            required_region_length_mm=None,region_length_status="FREE_HEIGHT_AND_CANTILEVER_BASIS_NOT_PROVEN",
            noncantilever_length_lower_bound_without_ln_mm=max(1.5*bmax,500),
            cantilever_length_reference_mm=2*bmax,
            low_axial_threshold_kn=.20*layout["gross_area_mm2"]*fc/1000,
            axial_branch_selected=None,
            hook_requirements={"proposed_end_angles_degrees":[135,135],"minimum_inner_bend_diameter_mm":5*t,
                "minimum_straight_tail_mm":max(6*t,80),"anchorage_and_3d_fit":"NOT_PROVEN"})
    except OPTIONAL_ERRORS as exc:
        row["reason"] = str(exc)
    row["transverse_id"] = "TIE-"+digest(row)[:24]
    return row


def build_column_transverse(chain,cages,archive):
    if (cages.get("axis_convention")!=AXIS_CONVENTION
            or cages["source_archive_sha256"]!=archive.sha256 or chain["source_archive_sha256"]!=archive.sha256
            or cages["source_demand_result_sha256"]!=chain["result_sha256"] or cages["source_run_id"]!=chain["source_run_id"]):
        raise BankError("TRANSVERSE_SOURCE_BINDING_MISMATCH")
    profiles,errors,proposals = {},{},[]
    for profile in cages["profiles"]:
        try: profiles[profile["profile_id"]] = _steel(profile,archive)
        except OPTIONAL_ERRORS as exc: errors[profile["profile_id"]] = str(exc)
    members = [{**m,"reason":errors.get(m["profile_id"],m["reason"]),
        "status":"TRANSVERSE_MATERIAL_BOUND" if m["profile_id"] in profiles else "BLOCKED_INPUTS"} for m in cages["members"]]
    for cage in cages["candidates"]:
        if cage["profile_id"] in profiles: proposals.append(_proposal(cage,profiles[cage["profile_id"]]))
    result = {"schema":"tbdy.next.column-transverse-proposals.v2","axis_convention":AXIS_CONVENTION,
        "source_run_id":chain["source_run_id"],
        "source_archive_sha256":archive.sha256,"source_demand_result_sha256":chain["result_sha256"],
        "source_cages_result_sha256":cages["result_sha256"],"proposal_policy":deepcopy(POLICY),
        "references":REFERENCES.copy(),"profiles":list(profiles.values()),"members":members,"proposals":proposals,
        "bound_member_count":sum(m["status"]=="TRANSVERSE_MATERIAL_BOUND" for m in members),
        "member_proposal_count":len(members)*len(DIAMETERS),"open_basis":list(OPEN_BASIS),
        "selected_design":None,"design_demand_authority":"DENIED","formal_compliance":"NOT_PROVEN",
        "engineering_release":"NOT_READY"}
    result["result_sha256"] = digest(result)
    return result


def transverse_rows(transverse,member_id=None):
    proposals = defaultdict(list)
    for row in transverse["proposals"]: proposals[row["profile_id"]].append(row)
    result = []
    for member in transverse["members"]:
        if member_id is not None and member["member_id"]!=member_id: continue
        for proposal in proposals[member["profile_id"]] or [{"candidate_id":None,"transverse_id":None,
                "candidate_label":f"16Φ{diameter}","status":"BLOCKED_INPUTS","reason":member["reason"],
                "layout":None,"axes":{}} for diameter in DIAMETERS]:
            for axis in ("V2","V3"):
                result.append({**member,**{k:v for k,v in proposal.items() if k!="axes"},
                    "shear_axis":axis,"direction":proposal["axes"].get(axis)})
    return result


def build_column_shear(chain,cages,transverse):
    if (cages.get("axis_convention")!=AXIS_CONVENTION or transverse.get("axis_convention")!=AXIS_CONVENTION
            or transverse["source_run_id"]!=chain["source_run_id"] or cages["source_run_id"]!=chain["source_run_id"]
            or transverse["source_archive_sha256"]!=chain["source_archive_sha256"]
            or cages["source_archive_sha256"]!=chain["source_archive_sha256"]
            or transverse["source_demand_result_sha256"]!=chain["result_sha256"]
            or cages["source_demand_result_sha256"]!=chain["result_sha256"]
            or transverse["source_cages_result_sha256"]!=cages["result_sha256"]):
        raise BankError("SHEAR_SOURCE_BINDING_MISMATCH")
    profiles = {p["profile_id"]:p for p in transverse["profiles"]}
    members = {m["member_id"] for m in transverse["members"]}
    if (len(members)!=len(transverse["members"]) or members!={m["member_id"] for m in cages["members"]}
            or len(chain["candidates"])!=chain["static_candidate_count"]):
        raise BankError("SHEAR_POPULATION_BINDING_MISMATCH")
    proposals = defaultdict(list)
    for row in transverse_rows(transverse): proposals[row["member_id"]].append(row)
    expected = {(f"16Φ{d}",axis) for d in DIAMETERS for axis in ("V2","V3")}
    for name in members:
        if len(proposals[name])!=6 or {(r["candidate_label"],r["shear_axis"]) for r in proposals[name]}!=expected:
            raise BankError("SHEAR_PROPOSAL_POPULATION_MISMATCH")
    rows,seen = [],set()
    for state in chain["candidates"]:
        name = state["native_key"]["Obj"]
        if (name not in members or state["state_id"] in seen or state["source_archive_sha256"]!=chain["source_archive_sha256"]
                or state["vector_status"]!="SIGNED_STATIC_SOURCE_VECTOR" or state["coordinate_basis"]!="CSI_FRAME_LOCAL_1_2_3"):
            raise BankError("SHEAR_STATIC_STATE_BINDING_MISMATCH")
        seen.add(state["state_id"])
        for proposal in proposals[name]:
            axis = proposal["shear_axis"]
            row = {"state_id":state["state_id"],"source_row_id":state["source_row_id"],"member_id":name,
                "native_key":state["native_key"],"native_values":state["native_values"],
                "candidate_id":proposal["candidate_id"],"candidate_label":proposal["candidate_label"],
                "transverse_id":proposal["transverse_id"],"shear_axis":axis,
                "scope":"UNMODIFIED_STATIC_SOURCE_COMPONENT_PROPOSED_TIES",
                "status":"BLOCKED_INPUTS","reason":proposal.get("reason"),"calculation":None,
                "final_design_eligible":False}
            if proposal["status"]=="PROPOSED_TRANSVERSE_REFERENCES_CALCULATED":
                try:
                    material,layout,direction = profiles[proposal["profile_id"]],proposal["layout"],proposal["direction"]
                    row["calculation"] = shear_reference(
                        n_compression_kn=-float(_number(state["native_values"]["P"],"P")),
                        shear_kn=float(_number(state["native_values"][axis],axis)),area_mm2=layout["gross_area_mm2"],
                        bw_mm=direction["bw_mm"],d_mm=direction["d_mm"],fck_mpa=material["fck_mpa"],
                        fywk_mpa=material["observed_fywk_mpa"],asw_mm2=direction["asw_mm2"],spacing_mm=layout["spacing_mm"],
                        gamma_c=POLICY["gamma_concrete"],gamma_s=POLICY["gamma_steel"])
                    row.update(status="SHEAR_REFERENCES_CALCULATED",reason=None)
                    if row["calculation"]["vcr_kn"] is None:
                        row.update(status="SHEAR_REFERENCE_PARTIAL",reason="OUTSIDE_CRACKING_FORMULA_DOMAIN")
                except OPTIONAL_ERRORS as exc: row["reason"] = str(exc)
            rows.append(row)
    grouped = defaultdict(list)
    for row in rows: grouped[(row["member_id"],row["candidate_label"],row["shear_axis"])].append(row)
    summaries = []
    for proposal in transverse_rows(transverse):
        matched = grouped[(proposal["member_id"],proposal["candidate_label"],proposal["shear_axis"])]
        summary = {k:proposal[k] for k in ("member_id","story","candidate_label","shear_axis","transverse_id")}
        summary.update(static_state_count=len(matched),status_counts=dict(Counter(r["status"] for r in matched)),branches={})
        for branch in ("ts500","zero_concrete"):
            numeric = [r for r in matched if r["calculation"] and r["calculation"]["branches"][branch]["source_utilization"] is not None]
            maximum = max((r["calculation"]["branches"][branch]["source_utilization"] for r in numeric),default=None)
            summary["branches"][branch] = {"maximum_source_utilization":maximum,
                "numeric_count":len(numeric),"status_counts":dict(Counter(r["calculation"]["branches"][branch]["status"] for r in numeric)),
                "critical_source_states":[{"state_id":r["state_id"],"source_row_id":r["source_row_id"],"native_key":r["native_key"]}
                    for r in numeric if r["calculation"]["branches"][branch]["source_utilization"]==maximum]}
        summaries.append(summary)
    result = {"schema":"tbdy.next.column-shear-scenarios.v2","axis_convention":AXIS_CONVENTION,
        "source_run_id":chain["source_run_id"],
        "source_archive_sha256":chain["source_archive_sha256"],"source_demand_result_sha256":chain["result_sha256"],
        "source_cages_result_sha256":cages["result_sha256"],"source_transverse_result_sha256":transverse["result_sha256"],
        "static_state_count":len(seen),"assessment_count":len(rows),"expected_assessment_count":len(seen)*len(DIAMETERS)*2,
        "source_population_reduced":False,"rows":rows,"members":summaries,
        "status_counts":dict(Counter(r["status"] for r in rows)),
        "reason_counts":dict(Counter(r["reason"] for r in rows if r["reason"])),
        "vc_zero_gate":zero_concrete_gate(in_confinement=None,earthquake_only_kn=None,seismic_total_kn=None,
            n_compression_kn=None,area_mm2=None,fck_mpa=None),
        "ve_status":"NOT_PROVEN","actual_second_order_applied":False,"selected_design":None,
        "references":REFERENCES.copy(),"open_basis":list(OPEN_BASIS),"design_demand_authority":"DENIED",
        "formal_compliance":"NOT_PROVEN","engineering_release":"NOT_READY"}
    result["result_sha256"] = digest(result)
    return result
