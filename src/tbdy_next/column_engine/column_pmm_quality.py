"""VS21: independent numerical comparisons of primary-critical PMM states.

Selection is intentionally made by the existing primary model. This does not
independently search all demand states or authorize its critical selection.
Every equal critical state remains in the comparison population, including
failed reference solves. No source file or engineering result is replaced.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from functools import lru_cache
import math

from .column_pmm import DIAMETERS, cage_rows
from .column_prechecks import _number
from .csi_geometry import AXIS_CONVENTION
from .native_archive import BankError, digest, finite
from .section_reference import (ReferenceSection, reference_radial_capacity, reference_state, LEVELS,
    FORCE_TOL_N, DIRECTION_ABS_TOL_NMM, DIRECTION_REL_TOL, INTEGRATION_ABS_TOL_NMM, INTEGRATION_REL_TOL)

SCHEMA="tbdy.next.column-pmm-numerical-reference.v2"
POLICY="CRITICAL_PMM_STRIP_GAUSS_BISECTION_WITH_PRIMARY_DIRECTION_ROOT_V2"
PRIMARY_BASIS="STRAIN_COMPATIBLE_POINT_AT_FIXED_N_AND_MOMENT_DIRECTION"
PRIMARY_DIRECTION_TOL_NMM=1000.0
K1={16:.85,18:.85,20:.85,25:.85,30:.82,35:.79,40:.76,45:.73,50:.70}
PRIMARY_FORCE_TOL_N=1.0
COMPARISON_ABS_NMM=1000.0
COMPARISON_REL=.002
TS500="https://staff.emu.edu.tr/cemalgenes/Documents/courses/INSA471_2019_20_Bahar/TS500.pdf"
RADIAL={"WITHIN_SCENARIO_SURFACE","EXCEEDS_SCENARIO_SURFACE"}
STATUSES=RADIAL|{"AXIAL_ONLY_SCENARIO","OUTSIDE_SCENARIO_AXIAL_RANGE","NUMERIC_UNRESOLVED","BLOCKED_INPUTS"}


def _key(row):
    k=row["native_key"]
    return (str(k["LoadCase"]),_number(k["ObjSta"],"station"),str(k["Elm"]),
        _number(k["ElmSta"],"element_station"),str(k["StepType"]),_number(k["StepNum"],"step"),row["state_id"])


@lru_cache(maxsize=4096)
def _fixed_plane(section,angle,c):
    return reference_state(section,angle,c,panels=32)


def _point_replay(section,point,target_n):
    values={k:finite(point[k],'primary_point_'+k) for k in ('n_n','m2_nmm','m3_nmm','c_mm','theta_deg','maximum_tensile_strain')}
    if (values['c_mm']<=0 or not 0<=values['theta_deg']<=90 or not 0<=values['maximum_tensile_strain']<=.1
            or abs(values['n_n']-target_n)>PRIMARY_FORCE_TOL_N):
        raise BankError('PMM_QUALITY_PRIMARY_PLANE_OUTSIDE_SCOPE')
    replay=_fixed_plane(section,values['theta_deg'],values['c_mm'])
    if (abs(replay['n_n']-values['n_n'])>FORCE_TOL_N
            or any(abs(replay[k]-values[k])>INTEGRATION_ABS_TOL_NMM for k in ('m2_nmm','m3_nmm'))
            or not math.isclose(replay['maximum_tensile_strain'],values['maximum_tensile_strain'],rel_tol=1e-10,abs_tol=1e-12)):
        raise BankError('PMM_QUALITY_PRIMARY_FIXED_PLANE_REPLAY_MISMATCH')


def _root_evidence(row,section):
    """Bind the recorded production point to its exact native N and M direction.

    No production solve is called here. Independent fixed-plane integration
    checks the recorded c/theta/resultants; it does not independently locate
    a radial root. The separate root search keeps its comparison budget.
    """
    try:
        evidence=row['refinement'];root=evidence['direction_root'];point=root['point']
        if (evidence['capacity_basis']!=PRIMARY_BASIS or root['status']!='MOMENT_DIRECTION_ROOT_RESOLVED'
                or root['reason'] is not None or root['method']!='BRACKETED_BISECTION_EXACT_AXIAL_EQUILIBRIUM'
                or root['angle_basis']!='COMPRESSION_NORMAL_LOCAL2_TO_LOCAL3_FIRST_QUADRANT_DEG'
                or root['direction_tolerance_nmm']!=PRIMARY_DIRECTION_TOL_NMM
                or root['interpolated_strain_plane_used'] is not False or root['global_root_uniqueness_proven'] is not False
                or evidence['continuous_error_bound_proven'] is not False):
            raise BankError('PMM_QUALITY_PRIMARY_ROOT_SCOPE_INVALID')
        values={k:finite(point[k],'primary_root_'+k) for k in ('n_n','m2_nmm','m3_nmm','c_mm','theta_deg','maximum_tensile_strain')}
        n=-float(_number(row['native_values']['P'],'P')*1000)
        m2,m3=(float(_number(row['native_values'][k],k)*1000000) for k in ('M2','M3'))
        magnitude=math.hypot(m2,m3);u2,u3=abs(m2)/magnitude,abs(m3)/magnitude
        axial=abs(values['n_n']-n);direction=abs(values['m2_nmm']*u3-values['m3_nmm']*u2)
        capacity=values['m2_nmm']*u2+values['m3_nmm']*u3
        initial=root['initial_bracket_theta_deg'];final=root['final_bracket_theta_deg']
        if (any(not isinstance(pair,list) or len(pair)!=2 for pair in (initial,final))
                or not 0<=finite(initial[0],'angle')<=finite(final[0],'angle')<=values['theta_deg']
                    <=finite(final[1],'angle')<=finite(initial[1],'angle')<=90
                or initial[0]>=initial[1] or values['c_mm']<=0 or not 0<=values['maximum_tensile_strain']<=.1
                or initial!=[evidence['finest_ray'][side]['theta_deg'] for side in ('left','right')]
                or finite(root['target_n_n'],'root_target_N')!=n or root['folded_unit_direction']!=[u2,u3]
                or axial>PRIMARY_FORCE_TOL_N or direction>PRIMARY_DIRECTION_TOL_NMM or capacity<=0
                or type(root['iterations']) is not int or not 0<=root['iterations']<=64
                or root['evaluated_point_count']!=root['iterations']+2
                or not axial<=finite(root['max_axial_residual_n'],'root_max_N')<=evidence['max_axial_residual_n']):
            raise BankError('PMM_QUALITY_PRIMARY_ROOT_STATE_NOT_BOUND')
        expected={'capacity_nmm':capacity,'axial_residual_n':axial,'direction_residual_nmm':direction}
        if any(not math.isclose(finite(root[k],k),v,rel_tol=1e-12,abs_tol=1e-7) for k,v in expected.items()):
            raise BankError('PMM_QUALITY_PRIMARY_ROOT_RESIDUAL_MISMATCH')
        cap=row['radial_capacity_kNm'];levels=evidence['capacity_kNm']
        if (not math.isclose(cap,capacity/1e6,rel_tol=1e-12,abs_tol=1e-12)
                or evidence['selected_capacity_kNm']!=cap or evidence['coarse_minimum_capacity_kNm']!=min(levels)
                or not math.isclose(evidence['root_minus_coarse_minimum_kNm'],cap-min(levels),abs_tol=1e-10)
                or not math.isclose(evidence['root_minus_finest_polygon_kNm'],cap-levels[-1],abs_tol=1e-10)):
            raise BankError('PMM_QUALITY_PRIMARY_ROOT_CAPACITY_MISMATCH')
        left,right=(evidence['finest_ray'][side] for side in ('left','right'))
        for p in (left,right,point):_point_replay(section,p,n)
        gl=left['m2_nmm']*u3-left['m3_nmm']*u2;gh=right['m2_nmm']*u3-right['m3_nmm']*u2
        if gl*gh>0 and min(abs(gl),abs(gh))>PRIMARY_DIRECTION_TOL_NMM:
            raise BankError('PMM_QUALITY_PRIMARY_ROOT_BRACKET_NOT_BOUND')
    except BankError:
        raise
    except (KeyError,TypeError,ZeroDivisionError,OverflowError,ValueError) as exc:
        raise BankError('PMM_QUALITY_PRIMARY_ROOT_EVIDENCE_INVALID') from exc


def _validate(chain,cages,pmm):
    for r in (chain,cages,pmm):
        if (r["source_run_id"]!=chain["source_run_id"] or r["source_archive_sha256"]!=chain["source_archive_sha256"]
                or r["design_demand_authority"]!="DENIED" or r["formal_compliance"]!="NOT_PROVEN" or r["engineering_release"]!="NOT_READY"):
            raise BankError("PMM_QUALITY_SOURCE_OR_AUTHORITY_MISMATCH")
    for r in (cages,pmm):
        if (r["axis_convention"]!=AXIS_CONVENTION or r["source_demand_result_sha256"]!=chain["result_sha256"]
                or r["selected_design"] is not None):
            raise BankError("PMM_QUALITY_DERIVATION_MISMATCH")
    if (pmm["source_cages_result_sha256"]!=cages["result_sha256"] or pmm["actual_second_order_applied"] is not False
            or pmm["minimum_eccentricity_applied"] is not False or pmm["pmm_population_reduced"] is not False):
        raise BankError("PMM_QUALITY_SCOPE_MISMATCH")
    numerical=pmm["numerical_policy"]
    if (pmm['schema']!='tbdy.next.column-pmm-scenarios.v3' or numerical['basis']!=PRIMARY_BASIS
            or numerical['solver_revision']!='VS25_DIRECTION_ROOT' or numerical['direction_absolute_tolerance_nmm']!=PRIMARY_DIRECTION_TOL_NMM
            or numerical['direction_maximum_iterations']!=64 or numerical['final_capacity_from_strain_compatible_point'] is not True
            or numerical["axial_tolerance_n"]!=PRIMARY_FORCE_TOL_N
            or numerical["moment_absolute_tolerance_nmm"]!=COMPARISON_ABS_NMM
            or numerical["moment_relative_tolerance"]!=COMPARISON_REL):
        raise BankError("PMM_QUALITY_PRIMARY_NUMERIC_POLICY_NOT_ACCEPTED")
    members={r["member_id"] for r in cages["members"]}
    proposals={(r["member_id"],r["label"]):r for r in cage_rows(cages)}
    profiles={p['profile_id']:p for p in cages['profiles']};models={}
    labels={f"16Φ{d}" for d in DIAMETERS}
    states={r["state_id"]:r for r in chain["candidates"]}
    if (len(members)!=len(cages["members"]) or members!={r["member_id"] for r in chain["members"]}
            or set(proposals)!={(m,label) for m in members for label in labels}
            or len(states)!=len(chain["candidates"]) or len(states)!=chain["static_candidate_count"]):
        raise BankError("PMM_QUALITY_SOURCE_POPULATION_MISMATCH")
    seen=set()
    for row in pmm["rows"]:
        key=(row["state_id"],row["candidate_label"]);source=states.get(row["state_id"])
        proposal=proposals.get((row["member_id"],row["candidate_label"]))
        if (key in seen or source is None or proposal is None or row["candidate_id"]!=proposal["candidate_id"]
                or row["member_id"]!=source["native_key"]["Obj"] or row["final_design_eligible"] is not False
                or any(row[k]!=source[k] for k in ("native_key","native_values","source_row_id"))):
            raise BankError("PMM_QUALITY_STATE_OR_CAGE_BINDING_MISMATCH")
        seen.add(key)
        if row["status"] not in STATUSES or (row["status"] in RADIAL)!=(row["utilization"] is not None):
            raise BankError("PMM_QUALITY_PRIMARY_STATUS_INVALID")
        if row["status"] in RADIAL:
            for k in ("utilization","radial_capacity_kNm"):
                v=row[k]
                if type(v) not in (int,float) or not math.isfinite(v) or v<=0:
                    raise BankError("PMM_QUALITY_PRIMARY_RADIAL_VALUE_INVALID")
            magnitude=math.hypot(row["native_values"]["M2"],row["native_values"]["M3"])
            if not math.isclose(row["utilization"],magnitude/row["radial_capacity_kNm"],rel_tol=1e-12,abs_tol=1e-12):
                raise BankError("PMM_QUALITY_PRIMARY_RATIO_INCONSISTENT")
            refinement=row.get("refinement")
            if not refinement or refinement.get("status")!="OBSERVED_STABLE_AT_BOTH_STEPS":
                raise BankError("PMM_QUALITY_PRIMARY_REFINEMENT_NOT_BOUND")
            capacities=refinement.get("capacity_kNm",[])
            history=refinement.get('history')
            if (not isinstance(capacities,list) or len(capacities)!=3
                    or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in capacities)
                    or not isinstance(history,list) or not history or not isinstance(history[-1],dict)
                    or capacities!=history[-1].get('capacity_kNm')
                    or not 0<=refinement.get("max_axial_residual_n",math.inf)<=PRIMARY_FORCE_TOL_N):
                raise BankError("PMM_QUALITY_PRIMARY_REFINEMENT_NOT_BOUND")
            model_key=(proposal['profile_id'],proposal['candidate_id'])
            if model_key not in models:models[model_key]=_model(profiles[proposal['profile_id']],proposal)[0]
            _root_evidence(row,models[model_key])
    if seen!={(state,label) for state in states for label in labels}:
        raise BankError("PMM_QUALITY_ASSESSMENT_POPULATION_MISMATCH")
    if len(seen)!=pmm["assessment_count"]:
        raise BankError("PMM_QUALITY_ASSESSMENT_POPULATION_MISMATCH")
    return proposals


def _model(profile,cage):
    material=profile["material"]
    values={"local2_mm":cage["t3_mm"],"local3_mm":cage["t2_mm"],
        "bars":tuple((b["x2_mm"],b["x3_mm"],b["area_mm2"]) for b in cage["bars"]),
        "block_stress_mpa":.85*material["fcd"],"block_depth_factor":K1[material["fck"]],
        "steel_yield_mpa":material["fyd"],"steel_modulus_mpa":material["es"],"concrete_ultimate_strain":material["ecu"]}
    section=ReferenceSection(**values)
    source={"profile_id":profile["profile_id"],"candidate_id":cage["candidate_id"],"candidate_label":cage["label"],
        "source_material":deepcopy(material),"parameters":values,"axis_convention":AXIS_CONVENTION,
        "same_declared_material_model":True,"constitutive_model_independently_validated":False}
    source["reference_model_id"]="REFMODEL-"+digest(source)[:24]
    return section,source


def _compare(row,section,model_id):
    result={k:deepcopy(row[k]) for k in ("state_id","source_row_id","member_id","candidate_id","candidate_label","native_key","native_values")}
    primary=row["radial_capacity_kNm"]
    result.update(reference_model_id=model_id,primary_capacity_knm=primary,primary_utilization=row["utilization"],
        primary_level_capacities_knm=deepcopy(row["refinement"]["capacity_kNm"]),
        primary_level_spread_knm=max(row["refinement"]["capacity_kNm"])-min(row["refinement"]["capacity_kNm"]),
        primary_direction_root=deepcopy(row['refinement']['direction_root']),
        primary_coarse_minimum_capacity_knm=row['refinement']['coarse_minimum_capacity_kNm'],
        primary_root_minus_coarse_minimum_knm=row['refinement']['root_minus_coarse_minimum_kNm'],
        reference=None,reference_capacity_knm=None,reference_utilization=None,
        signed_difference_knm=None,absolute_difference_knm=None,relative_difference=None,comparison_budget_knm=None,
        status="REFERENCE_UNRESOLVED",reason=None,final_design_eligible=False)
    try:
        n=-float(_number(row["native_values"]["P"],"P")*1000)
        m2=float(_number(row["native_values"]["M2"],"M2")*1000000)
        m3=float(_number(row["native_values"]["M3"],"M3")*1000000)
        reference=reference_radial_capacity(section,n,m2,m3)
        result["reference"]=reference
        if reference["status"]!="REFERENCE_OBSERVED_STABLE":
            result.update(status=reference["status"],reason=reference.get("reason"));return result
        capacity=reference["capacity_knm"]
        radius=math.hypot(section.local2_mm,section.local3_mm)/2
        # Fixed, declared before the comparison; observed level spread is NOT added.
        budget=(COMPARISON_ABS_NMM+COMPARISON_REL*max(primary,capacity)*1e6
                +(PRIMARY_FORCE_TOL_N+FORCE_TOL_N)*radius)/1e6
        difference=capacity-primary
        result.update(reference_capacity_knm=capacity,reference_utilization=reference["utilization"],
            signed_difference_knm=difference,absolute_difference_knm=abs(difference),
            relative_difference=abs(difference)/max(primary,capacity),comparison_budget_knm=budget,
            status="NUMERICAL_COMPARISON_MATCH" if abs(difference)<=budget else "NUMERICAL_COMPARISON_MISMATCH")
    except (ValueError,OverflowError) as exc:
        result["reason"]=str(exc)
    return result


def build_column_pmm_quality(chain,cages,pmm,*,member_id=None,output_case=None):
    proposals=_validate(chain,cages,pmm)
    profiles={p["profile_id"]:p for p in cages["profiles"]}
    grouped=defaultdict(list)
    for row in sorted(pmm["rows"],key=_key):
        if ((member_id is None or row["member_id"]==member_id)
                and (output_case is None or row["native_key"]["LoadCase"]==output_case)):
            grouped[(row["member_id"],row["candidate_label"])].append(row)
    rows,groups,models=[],[],{}
    for (name,label),cage in sorted(proposals.items()):
        if member_id is not None and name!=member_id:continue
        primary=grouped[(name,label)]
        radial=[r for r in primary if r["status"] in RADIAL]
        maximum=max((r["utilization"] for r in radial),default=None)
        critical=[r for r in radial if r["utilization"]==maximum]
        comparisons=[]
        if critical:
            section,model=_model(profiles[cage["profile_id"]],cage)
            models[model["reference_model_id"]]=model
            for row in critical:
                item=_compare(row,section,model["reference_model_id"])
                item["story"]=cage["story"];comparisons.append(item);rows.append(item)
        counts=Counter(r["status"] for r in primary)
        groups.append({"member_id":name,"story":cage["story"],"candidate_id":cage["candidate_id"],"candidate_label":label,
            "primary_state_count":len(primary),"primary_radial_state_count":len(radial),"primary_status_counts":dict(sorted(counts.items())),
            "primary_nonradial_state_count":len(primary)-len(radial),"primary_maximum_resolved_utilization":maximum,
            "target_state_ids":[r["state_id"] for r in critical],"target_count":len(critical),"comparison_count":len(comparisons),
            "comparison_status_counts":dict(sorted(Counter(r["status"] for r in comparisons).items())),
            "critical_comparisons_all_match":bool(critical) and all(r["status"]=="NUMERICAL_COMPARISON_MATCH" for r in comparisons),
            "status":"CRITICAL_RADIAL_COMPARISONS" if critical else "NO_PRIMARY_RADIAL_RESULT" if primary else "NO_STATIC_STATES",
            "all_primary_states_independently_checked":False,"selected_design":False})
    result={"schema":SCHEMA,"policy_id":POLICY,"axis_convention":AXIS_CONVENTION,
        "source_run_id":chain["source_run_id"],"source_archive_sha256":chain["source_archive_sha256"],
        "source_demand_result_sha256":chain["result_sha256"],"source_cages_result_sha256":cages["result_sha256"],
        "source_pmm_result_sha256":pmm["result_sha256"],"member_id_filter":member_id,"output_case_filter":output_case,
        "primary_total_assessment_count":pmm["assessment_count"],"filtered_primary_assessment_count":sum(g["primary_state_count"] for g in groups),
        "member_count":len({g["member_id"] for g in groups}),"member_scenario_count":len(groups),
        "critical_target_count":sum(g["target_count"] for g in groups),"comparison_count":len(rows),
        "groups_without_radial_targets":sum(not g["target_count"] for g in groups),
        "status_counts":dict(sorted(Counter(r["status"] for r in rows).items())),"rows":rows,"members":groups,
        "reference_models":[models[k] for k in sorted(models)],"selection_basis":"PRIMARY_MAXIMUM_RESOLVED_RADIAL_PMM_ALL_EXACT_TIES",
        "critical_subset_only":True,"critical_selection_independently_verified":False,
        "full_primary_population_independently_checked":False,"primary_results_changed":False,
        "primary_capacity_basis":PRIMARY_BASIS,"primary_solver_revision":"VS25_DIRECTION_ROOT",
        "primary_fixed_plane_validation":{"method":"INDEPENDENT_STRIP_GAUSS_AT_RECORDED_C_THETA","disk_panels":32,
            "recorded_point_check_count":3*sum(r['status'] in RADIAL for r in pmm['rows']),
            "force_difference_tolerance_n":FORCE_TOL_N,"moment_difference_tolerance_nmm":INTEGRATION_ABS_TOL_NMM,
            "independent_root_search":False,"changes_supplied_primary_results":False},
        "numerical_policy":{"levels":[{"disk_panels":p,"quadrant_intervals":a} for p,a in LEVELS],
            "force_tolerance_n":FORCE_TOL_N,"direction_absolute_tolerance_nmm":DIRECTION_ABS_TOL_NMM,
            "direction_relative_tolerance":DIRECTION_REL_TOL,"integration_absolute_tolerance_nmm":INTEGRATION_ABS_TOL_NMM,
            "integration_relative_tolerance":INTEGRATION_REL_TOL,"comparison_absolute_nmm":COMPARISON_ABS_NMM,
            "comparison_relative_tolerance":COMPARISON_REL,"primary_force_tolerance_n":PRIMARY_FORCE_TOL_N,
            "primary_direction_absolute_tolerance_nmm":PRIMARY_DIRECTION_TOL_NMM,
            "force_budget_uses_section_radius":True,"primary_level_spread_added_to_budget":False},
        "reference_url":TS500,"same_declared_material_model":True,"independent_material_model_validation":False,
        "continuous_error_bound_proven":False,"global_root_uniqueness_proven":False,
        "actual_second_order_applied":False,"selected_design":None,"design_demand_authority":"DENIED",
        "formal_compliance":"NOT_PROVEN","engineering_release":"NOT_READY"}
    result["result_sha256"]=digest(result)
    return result
