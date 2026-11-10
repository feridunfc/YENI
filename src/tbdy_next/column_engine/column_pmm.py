"""CE-05A: explicit proposed cages x every concurrent static source vector.

The finite three-cage scenario is not an exhaustive or automatic design
selection. Observed model properties and proposed parameters stay separate.
No actual cage, analysis-order, seismic-demand or detailing authority is added.
"""
from collections import Counter, defaultdict
from dataclasses import asdict

from .column_prechecks import _number
from .column_stability import OPTIONAL_ERRORS
from .csi_geometry import AXIS_CONVENTION, REFERENCE as CSI_REFERENCE, local_dimensions
from .native_archive import BankError, digest
from .observed_context import EXPECTED_FIELDS
from .section_capacity import (ANGLE_COUNTS, MAX_ANGLE_COUNT, FORCE_TOL_N, MOMENT_ABS_TOL_NMM, MOMENT_REL_TOL,
    DIRECTION_TOL_NMM, DIRECTION_MAX_ITERATIONS, RADIAL_BASIS, Bar, Material, Section, perimeter, solver)

DIAMETERS = (24, 28, 32)
POLICY = {"id": "CE05A_RECT16_24_28_32_T12_GC1P5_GS1P15_CSI_AXES_V2",
    "axis_convention": AXIS_CONVENTION,
    "bar_diameters_mm": list(DIAMETERS), "bars_per_local2_face": 5, "bars_per_local3_face": 5,
    "tie_diameter_mm": 12, "gamma_concrete": 1.5, "gamma_steel": 1.15,
    "tie_diameter_basis": "PROPOSAL_AT_LEAST_LONGITUDINAL_DIAMETER_OVER_3_TS500_7_4_1",
    "origin": "EXPLICIT_PROPOSAL_NOT_ETABS_BAR_LABELS", "project_applicability_approved": False,
    "aggregate_max_mm": None, "bar_availability_proven": False,
    "candidate_population_exhaustive": False, "automatic_design_selection": False}
REFERENCES = {
    "native_dimensions": CSI_REFERENCE,
    "capacity_kernel": "https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/design/columns/section_capacity.py",
    "geometry_kernel": "https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/design/columns/rebar_layout.py",
    "cover": "https://docs.csiamerica.com/help-files/etabs-api-2016/html/cef22cbd-9054-36ac-88e2-9e0ed51f3295.htm",
    "signs": "https://docs.csiamerica.com/help-files/sap/Output/Frame_Element_Internal_Forces_Output_Conventions.htm",
    "ts500": "https://staff.emu.edu.tr/cemalgenes/Documents/courses/INSA471_2019_20_Bahar/TS500.pdf"}
OPEN_BASIS = ["PROPOSED_CAGE_NOT_SELECTED_OR_AS_BUILT", "PROJECT_MATERIAL_FACTORS_NOT_APPROVED",
    "AGGREGATE_AND_CONFINEMENT_DETAILING_NOT_BOUND", "MINIMUM_ECCENTRICITY_NOT_APPLIED",
    "SECOND_ORDER_NOT_APPLIED", "FULL_DESIGN_COMBINATION_POPULATION_NOT_PROVEN",
    "STEEL_STRAIN_SAMPLED_AT_BAR_CENTROID", "CONTINUOUS_PMM_ERROR_BOUND_NOT_PROVEN"]


def _native(archive, api, kind, name):
    observed = archive.native(api, kind, name, EXPECTED_FIELDS[api])
    if observed is None: raise BankError("PMM_SOURCE_NOT_OBSERVED:"+api)
    return observed


def _profile(member, bound, archive):
    name = member["frame_name"]
    if not bound or bound["status"] != "REQUIRED_AREA_BOUNDS_CALCULATED":
        raise BankError("PMM_RECTANGULAR_SECTION_NOT_BOUND")
    assigned, assignment = _native(archive,"FrameObj.GetSection","frame",name)
    if assigned["PropName"] != bound["section_name"]: raise BankError("PMM_ASSIGNED_SECTION_MISMATCH")
    section_name = assigned["PropName"]
    rect, rect_source = _native(archive,"PropFrame.GetRectangle","frame_section",section_name)
    rebar, rebar_source = _native(archive,"PropFrame.GetRebarColumn","column_section",section_name)
    concrete, concrete_source = _native(archive,"PropMaterial.GetOConcrete","material",rect["MatProp"])
    steel, steel_source = _native(archive,"PropMaterial.GetORebar_1","material",rebar["MatPropLong"])
    if type(rebar["Pattern"]) is not int or rebar["Pattern"] != 1:
        raise BankError("PMM_MODEL_REBAR_PATTERN_NOT_RECTANGULAR")
    if concrete["IsLightweight"] is not False: raise BankError("PMM_NORMALWEIGHT_CONCRETE_NOT_BOUND")
    t2,t3,cover = (float(_number(v,k)*1000) for v,k in ((rect["T2"],"T2"),(rect["T3"],"T3"),(rebar["Cover"],"Cover")))
    fc,fy = (float(_number(v,k)/1000) for v,k in ((concrete["Fc"],"Fc"),(steel["FY"],"FY")))
    material = Material(fc,fc/POLICY["gamma_concrete"],fy/POLICY["gamma_steel"])
    if (t2 != float(_number(bound["b2_cm"],"b2_cm")*10)
            or t3 != float(_number(bound["b3_cm"],"b3_cm")*10)):
        raise BankError("PMM_GEOMETRY_BINDING_MISMATCH")
    profile = {"section_name": section_name, "t2_mm": t2, "t3_mm": t3,
        "model_clear_cover_to_tie_mm": cover, "material": asdict(material),
        "concrete_material": rect["MatProp"], "steel_material": rebar["MatPropLong"],
        "model_to_be_designed": rebar["ToBeDesigned"], "model_bar_label": rebar["RebarSize"],
        "model_tie_label": rebar["TieSize"], "bar_labels_used_as_dimensions": False,
        "cover_basis": "CSI_CLEAR_TO_CONFINEMENT_STEEL", "source_calls": {
            "rectangle":rect_source,"rebar_setting":rebar_source,"concrete":concrete_source,"steel":steel_source},
        "proposal_policy_id": POLICY["id"], "physical_cage_proven": False}
    profile["profile_id"] = "PROFILE-"+digest(profile)[:24]
    return profile, assignment


def _candidate(profile, diameter):
    row = {"profile_id":profile["profile_id"], "label":f"16Φ{diameter}", "bar_diameter_mm":diameter,
        "bar_count":16, "bars_per_local2_face":5,"bars_per_local3_face":5,
        "tie_diameter_mm":POLICY["tie_diameter_mm"], "t2_mm":profile["t2_mm"], "t3_mm":profile["t3_mm"],
        "clear_cover_to_tie_mm":profile["model_clear_cover_to_tie_mm"], "bars":[],
        "as_cm2":None,"rho_percent":None,"center_offset_mm":None,"minimum_clear_spacing_mm":None,
        "geometry_status":"BLOCKED_INPUTS","reason":None,"area_ratio_status":"NOT_PROVEN",
        "spacing_status":"AGGREGATE_NOT_BOUND","selected_design":False,"physical_cage_proven":False}
    try:
        d2,d3 = local_dimensions(profile["t2_mm"],profile["t3_mm"])
        bars,center,spacing = perimeter(d2,d3,profile["model_clear_cover_to_tie_mm"],POLICY["tie_diameter_mm"],diameter)
        area = sum(b.area for b in bars)
        rho = area/(profile["t2_mm"]*profile["t3_mm"])
        row.update(bars=[{"x2_mm":b.x2,"x3_mm":b.x3,"area_mm2":b.area,"diameter_mm":diameter} for b in bars],
            as_cm2=area/100,rho_percent=100*rho,center_offset_mm=center,minimum_clear_spacing_mm=spacing,
            geometry_status="PROPOSED_GEOMETRY_CALCULATED",area_ratio_status="WITHIN_1_TO_4_PERCENT_REFERENCE"
                if .01<=rho<=.04 else "OUTSIDE_1_TO_4_PERCENT_REFERENCE",minimum_spacing_without_aggregate_mm=max(1.5*diameter,40),
            spacing_status="AGGREGATE_NOT_BOUND" if spacing>=max(1.5*diameter,40) else "BELOW_SPACING_REFERENCE",
            minimum_tie_diameter_reference_mm=diameter/3,
            tie_diameter_reference_met=POLICY["tie_diameter_mm"]>=diameter/3)
    except (ValueError,OverflowError) as exc:
        row["reason"] = str(exc)
    row["candidate_id"] = "CAGE-"+digest(row)[:24]
    return row


def build_column_cages(bank,chain,prechecks,archive):
    if (bank["source_archive_sha256"] != archive.sha256 or chain["source_archive_sha256"] != archive.sha256
            or prechecks["source_archive_sha256"] != archive.sha256
            or chain["source_bank_result_sha256"] != bank["result_sha256"]
            or prechecks["source_demand_result_sha256"] != chain["result_sha256"]):
        raise BankError("CAGE_SOURCE_BINDING_MISMATCH")
    bounds = {r["member_id"]:r for r in prechecks["reinforcement_bounds"]["rows"]}
    profiles, members = {}, []
    for member in bank["members"]:
        frame = (member.get("context") or {}).get("frame") or {}
        item = {"member_id":member["frame_name"],"story":frame.get("story_label"),"column_label":frame.get("column_label"),
            "profile_id":None,"status":"BLOCKED_INPUTS","reason":None,"assignment_source":None}
        try:
            profile,assignment = _profile(member,bounds.get(member["frame_name"]),archive)
            profiles[profile["profile_id"]] = profile
            item.update(profile_id=profile["profile_id"],status="PROPOSAL_INPUTS_BOUND",assignment_source=assignment)
        except OPTIONAL_ERRORS as exc:
            item["reason"] = str(exc)
        members.append(item)
    candidates = [_candidate(profile,d) for profile in profiles.values() for d in DIAMETERS]
    result = {"schema":"tbdy.next.column-cages.v2","axis_convention":AXIS_CONVENTION,
        "source_run_id":bank.get("run_id"),"source_archive_sha256":archive.sha256,
        "source_demand_result_sha256":chain["result_sha256"],"source_prechecks_result_sha256":prechecks["result_sha256"],
        "proposal_policy":POLICY.copy(),"references":REFERENCES.copy(),"profiles":list(profiles.values()),"members":members,
        "candidates":candidates,"bound_member_count":sum(m["profile_id"] is not None for m in members),
        "distinct_profile_count":len(profiles),"candidate_geometry_count":len(candidates),
        "member_proposal_count":len(members)*len(DIAMETERS),"selected_design":None,"formal_compliance":"NOT_PROVEN",
        "design_demand_authority":"DENIED","engineering_release":"NOT_READY"}
    result["result_sha256"] = digest(result)
    return result


def cage_rows(cages,member_id=None):
    candidates = defaultdict(list)
    for candidate in cages["candidates"]: candidates[candidate["profile_id"]].append(candidate)
    result = []
    for member in cages["members"]:
        if member_id is not None and member["member_id"] != member_id: continue
        for candidate in candidates[member["profile_id"]] or [
                {"candidate_id":None,"label":f"16Φ{d}","bar_diameter_mm":d,"bars":[],
                 "geometry_status":"BLOCKED_INPUTS","reason":member["reason"]} for d in DIAMETERS]:
            result.append({**member,**candidate})
    return result


def _section(profile,candidate):
    d2,d3 = local_dimensions(profile["t2_mm"],profile["t3_mm"])
    return Section(d2,d3,tuple(Bar(b["x2_mm"],b["x3_mm"],b["area_mm2"])
        for b in candidate["bars"]),Material(**profile["material"]))


def build_column_pmm(chain,cages,stability):
    if (cages.get("axis_convention") != AXIS_CONVENTION or stability.get("axis_convention") != AXIS_CONVENTION
            or cages["source_demand_result_sha256"] != chain["result_sha256"]
            or cages["source_run_id"] != chain["source_run_id"] or stability["source_run_id"] != chain["source_run_id"]
            or stability["source_demand_result_sha256"] != chain["result_sha256"]
            or cages["source_archive_sha256"] != chain["source_archive_sha256"]
            or stability["source_archive_sha256"] != chain["source_archive_sha256"]
            or stability["source_prechecks_result_sha256"] != cages["source_prechecks_result_sha256"]):
        raise BankError("PMM_SOURCE_BINDING_MISMATCH")
    profiles = {p["profile_id"]:p for p in cages["profiles"]}
    members = {m["member_id"]:m for m in cages["members"]}
    if len(members)!=len(cages["members"]) or len(chain["candidates"])!=chain["static_candidate_count"]:
        raise BankError("PMM_POPULATION_BINDING_MISMATCH")
    proposals = defaultdict(list)
    for row in cage_rows(cages): proposals[row["member_id"]].append(row)
    rows = []
    seen = set()
    for state in chain["candidates"]:
        key,name = state["native_key"],state["native_key"]["Obj"]
        if (name not in members or state["state_id"] in seen or state["source_archive_sha256"] != chain["source_archive_sha256"]
                or state["vector_status"] != "SIGNED_STATIC_SOURCE_VECTOR" or state["coordinate_basis"] != "CSI_FRAME_LOCAL_1_2_3"):
            raise BankError("PMM_STATIC_STATE_BINDING_MISMATCH")
        seen.add(state["state_id"])
        for cage in proposals[name]:
            result = {"status":"BLOCKED_INPUTS","reason":cage.get("reason"),"utilization":None,
                "radial_capacity_kNm":None,"refinement":None,"final_design_eligible":False}
            if cage["geometry_status"] == "PROPOSED_GEOMETRY_CALCULATED":
                if cage["area_ratio_status"] != "WITHIN_1_TO_4_PERCENT_REFERENCE":
                    result["reason"] = "PROPOSED_AREA_OUTSIDE_REFERENCE"
                elif cage["spacing_status"] == "BELOW_SPACING_REFERENCE":
                    result["reason"] = "PROPOSED_SPACING_BELOW_REFERENCE"
                elif not cage["tie_diameter_reference_met"]:
                    result["reason"] = "PROPOSED_TIE_DIAMETER_BELOW_REFERENCE"
                else:
                    native = state["native_values"]
                    n,m2,m3 = (-float(_number(native["P"],"P")*1000),float(_number(native["M2"],"M2")*1000000),
                        float(_number(native["M3"],"M3")*1000000))
                    try:
                        result = solver(_section(profiles[cage["profile_id"]],cage)).assess(n,m2,m3)
                    except (ValueError,OverflowError) as exc:
                        result.update(status="NUMERIC_UNRESOLVED",reason=str(exc))
            rows.append({"state_id":state["state_id"],"source_row_id":state["source_row_id"],"member_id":name,
                "candidate_id":cage["candidate_id"],"candidate_label":cage["label"],"native_key":key,
                "native_values":state["native_values"],"domain_values":state["domain_values"],
                "scope":"UNMODIFIED_STATIC_SOURCE_VECTOR_PROPOSED_CAGE",**result})
    grouped = defaultdict(list)
    for row in rows: grouped[(row["member_id"],row["candidate_label"])].append(row)
    summaries = []
    for cage in cage_rows(cages):
        values = grouped[(cage["member_id"],cage["label"])]
        numeric = [r for r in values if r["utilization"] is not None]
        maximum = max((r["utilization"] for r in numeric),default=None)
        counts = Counter(r["status"] for r in values)
        summaries.append({"member_id":cage["member_id"],"story":cage["story"],"candidate_id":cage["candidate_id"],
            "candidate_label":cage["label"],"as_cm2":cage.get("as_cm2"),"static_state_count":len(values),
            "status_counts":dict(counts),"maximum_resolved_utilization":maximum,
            "critical_resolved_states":[{"state_id":r["state_id"],"native_key":r["native_key"],"utilization":maximum}
                for r in numeric if r["utilization"]==maximum],
            "numeric_population_complete":bool(values) and not (counts["NUMERIC_UNRESOLVED"] or counts["BLOCKED_INPUTS"]),
            "selected_design":False})
    result = {"schema":"tbdy.next.column-pmm-scenarios.v3","axis_convention":AXIS_CONVENTION,
        "source_run_id":chain["source_run_id"],
        "source_archive_sha256":chain["source_archive_sha256"],"source_demand_result_sha256":chain["result_sha256"],
        "source_cages_result_sha256":cages["result_sha256"],"source_stability_result_sha256":stability["result_sha256"],
        "static_state_count":len(seen),"assessment_count":len(rows),"expected_assessment_count":len(seen)*len(DIAMETERS),
        "pmm_population_reduced":False,"candidate_population_exhaustive":False,"members":summaries,"rows":rows,
        "status_counts":dict(Counter(r["status"] for r in rows)),"reason_counts":dict(Counter(r["reason"] for r in rows if r["reason"])),
        "numerical_policy":{"initial_angle_counts":list(ANGLE_COUNTS),"maximum_angle_count":MAX_ANGLE_COUNT,
            "axial_tolerance_n":FORCE_TOL_N,
            "moment_absolute_tolerance_nmm":MOMENT_ABS_TOL_NMM,"moment_relative_tolerance":MOMENT_REL_TOL,
            "boundary_guard":"MOMENT_ABS_PLUS_RELATIVE_PLUS_FORCE_TOL_TIMES_SECTION_RADIUS",
            "basis":RADIAL_BASIS,"solver_revision":"VS25_DIRECTION_ROOT",
            "direction_absolute_tolerance_nmm":DIRECTION_TOL_NMM,
            "direction_maximum_iterations":DIRECTION_MAX_ITERATIONS,"final_capacity_from_strain_compatible_point":True,
            "global_root_uniqueness_proven":False,
            "concrete_replacement":"EXACT_CIRCULAR_DISK_HALFPLANE_AREA_AND_FIRST_MOMENTS",
            "moment_signs":"CSI_M2_PLUS3_COMPRESSION_M3_PLUS2_COMPRESSION"},
        "open_basis":list(OPEN_BASIS),"selected_design":None,"actual_second_order_applied":False,
        "minimum_eccentricity_applied":False,"design_demand_authority":"DENIED",
        "formal_compliance":"NOT_PROVEN","engineering_release":"NOT_READY"}
    result["result_sha256"] = digest(result)
    return result
