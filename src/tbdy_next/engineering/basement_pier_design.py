"""Section force equilibrium and proposed web design for column-supported basement piers."""
from collections import defaultdict
from itertools import product
from math import fsum, isfinite, pi

from ..column_engine.section_capacity import Material
from ..column_engine.section_interval import SectionInterval
from .basement_joint_layout import check_joint_layout
from .basement_pier_geometry import folded_section, required
from .basement_wall_connection import pressure_connections
from .basement_wall_pressure import CAGES, panel_pressure_design, pressure_cases, vertical_section
from .beam_r10_live import _design_factors, _steel_grade_mpa
from .column_r10_live import _materials_fck
from .pier_force_source import ORIGINAL, signed_vector
from .pier_seismic_shear import DISPLAY_KN, envelope
from .wall_boundary import _catalog_proposal


def _section_terms(geometry, origin):
    # Relative coordinates of each net rectangle in the native pier 2–3 plane.
    ux, uy = geometry["native_axes_2_xy"]
    cx,cy = geometry["net_centroid_xy_m"]
    u0,v0 = (cx-origin[0])*ux + (cy-origin[1])*uy, -(cx-origin[0])*uy + (cy-origin[1])*ux
    terms = {}
    for panel in geometry["panels"]:
        x,y = panel["clear_centroid_xy_m"]
        u,v = (x-cx)*ux + (y-cy)*uy, -(x-cx)*uy + (y-cy)*ux
        dx,dy = panel["width_direction"]
        c,s = dx*ux+dy*uy, -dx*uy+dy*ux
        length, t = panel["clear_length_m"], panel["thickness_m"]
        area = length*t
        terms[panel["member"]] = (area,u,v,c,s,area*length**2/12,area*t**2/12)
    j_uu = fsum(a*u*u + jl*c*c + jt*s*s for a,u,v,c,s,jl,jt in terms.values())
    j_vv = fsum(a*v*v + jl*s*s + jt*c*c for a,u,v,c,s,jl,jt in terms.values())
    j_uv = fsum(a*u*v + (jl-jt)*c*s for a,u,v,c,s,jl,jt in terms.values())
    det = j_uu*j_vv-j_uv*j_uv
    required(isfinite(det) and det > 1e-12*j_uu*j_vv, "DEGENERATE_NET_PIER_SECTION")
    return terms, (geometry["clear_web_area_m2"],u0,v0,j_uu,j_vv,j_uv,det)


def _allocate(terms, inertia, n, qu, qv):
    """An affine vertical force density in compression-positive kN/m². Moments are first moments in kN·m."""
    area,u0,v0,ju,jv,juv,det = inertia
    gu = ((qu-n*u0)*jv-(qv-n*v0)*juv)/det
    gv = ((qv-n*v0)*ju-(qu-n*u0)*juv)/det
    forces, ru, rv = {}, [], []
    for uid,(a,u,v,c,s,jl,jt) in terms.items():
        axial = a*(n/area+gu*u+gv*v)
        strong, weak = jl*(gu*c+gv*s), jt*(-gu*s+gv*c)
        forces[uid] = (axial, weak, strong)
        ru.append(axial*(u0+u)+strong*c-weak*s)
        rv.append(axial*(v0+v)+strong*s+weak*c)
    residual = [fsum(f[0] for f in forces.values())-n, fsum(ru)-qu, fsum(rv)-qv]
    required(all(abs(r) < 1e-7 for r in residual), "PIER_SECTION_FORCE_EQUILIBRIUM_FAILED")
    return forces, residual


def _cut(geometry, bound, name, story, face, combo, spec):
    rows = bound["groups"][name, story, face, combo]
    if spec["spectral"]:
        bounds = envelope(rows)
        mode = "NATIVE_SCALAR_ENVELOPE"
    else:
        vector = signed_vector(rows, ORIGINAL)
        bounds = {"Min":vector,"Max":vector}
        mode = "SIGNED_STATIC"
    origin = geometry["native_face_origins_m"][face]
    terms, inertia = _section_terms(geometry, origin)
    lo = -bounds["Max"]["P"] - DISPLAY_KN
    hi = -bounds["Min"]["P"] + DISPLAY_KN
    # Source centroid is rounded per global coordinate. Both moment signs are enclosed,
    # also for signed gravity, so no accidental change of pier or panel bending convention is needed.
    origin_error = max(abs(lo),abs(hi))*.00051*sum(abs(x) for x in geometry["native_axes_2_xy"])
    def moment_limit(component):
        return max(abs(bounds[k][component]) for k in ("Min","Max")) + DISPLAY_KN + origin_error
    mu,mv = moment_limit("M3"), moment_limit("M2")
    loads = defaultdict(list)
    residual = [0.,0.,0.]
    for n,qu,qv in product((lo,hi),(-mu,mu),(-mv,mv)):
        solution, error = _allocate(terms, inertia, n, qu, qv)
        residual = [max(x,abs(y)) for x,y in zip(residual,error)]
        for uid, f in solution.items():
            loads[uid].append(f)
    allocated = []
    for uid, values in loads.items():
        ns, m2, m3 = zip(*values)
        allocated.append({"member":uid, "nd_kn":[min(ns),max(ns)], "m2_upper_knm":max(map(abs,m2)),
                          "m3_upper_knm":max(map(abs,m3))})
    return {"face":face, "combination":combo, "role":spec["role"], "basis":mode, "native_origin_m":origin,
            "native_kn_knm":bounds, "nd_kn":[lo,hi], "moment_origin_allowance_knm":origin_error,
            "equilibrium_error_kn_knm":residual, "web_demands":allocated}


def _material(source, stages, concrete):
    bars = _catalog_proposal(source)
    required(bars is not None, "WALL_COVER_AND_STEEL_GRADE_PROPOSAL_REQUIRED")
    axial = source["column_axial"]
    gc, gs = _design_factors(axial.get("design_preferences"))
    fy, es = _steel_grade_mpa(axial.get("pmm_section_source"),bars["grade"])
    fc = _materials_fck(stages.get("extra")).get(concrete)
    required(all(v is not None and isfinite(v) and v > 0 for v in (fc,fy,es,gc,gs)) and fy == bars["fywk_mpa"],
             "PIER_MATERIAL_OR_DESIGN_FACTOR_MISSING")
    return Material(fc,fc/gc,fy/gs,es), bars["cover_mm"]


def _design(result, source, stages, bound, scope):
    name, story = result["pier"], result["story"]
    geom = folded_section(source, bound, name, story, result["members"])
    result["geometry"] = geom
    combos, patterns = pressure_cases(source, bound, scope, name, story, geom["panels"])
    result.update(expected_cut_combinations=2*len(combos), additional_static=[k for k,s in combos.items()
        if s["role"] == "ADDITIONAL_STATIC_PRESSURE"], uniform_normal_pressures_kn_m2=patterns)
    for face, (combo,spec) in product(("Bottom","Top"),combos.items()):
        try:
            row = _cut(geom,bound,name,story,face,combo,spec)
        except (KeyError,TypeError,ValueError) as exc:
            row = {"face":face,"combination":combo,"role":spec["role"],"status":"HOLD","reason":str(exc)}
        result["cuts"].append(row)
    mat, cover = _material(source,stages,geom["material"])
    height = geom["top_m"]-geom["bottom_m"]
    for panel in geom["panels"]:
        uid = panel["member"]
        try:
            horizontal = panel_pressure_design(panel,combos,cover,mat,height)
            try:
                horizontal, panel["pressure_connections"] = pressure_connections(
                    source, stages, geom, panel, horizontal, combos, cover, mat, height)
            except (KeyError, TypeError, ValueError) as exc:
                panel["pressure_connections"] = {"status":"HOLD", "reason": str(exc), "ends":{}}
            panel["horizontal"] = horizontal
            panel["pressure_design_scope"] = {"calculated": "ONE_WAY_HORIZONTAL_UNIFORM_STRIP",
                "status": "SHELL_BENDING_AND_INTERFACE_NORMAL_ACTION_REQUIRED",
                "span_m": panel["span_m"], "height_m": height,
                "construction_status": "AGGREGATE_HOOK_AND_CAGE_CLEARANCE_REQUIRED"}
            panel["schedule_status"] = "PRESSURE_STRIP_CANDIDATE_ONLY"
            demands = [(r["face"],r["combination"],d) for r in result["cuts"] for d in r.get("web_demands",[]) if d["member"]==uid]
            required(len(demands) == result["expected_cut_combinations"], "COMPLETE_NATIVE_CUT_POPULATION_REQUIRED_FOR_VERTICAL_SELECTION")
            whole_n = [min(d["nd_kn"][0] for _,_,d in demands), max(d["nd_kn"][1] for _,_,d in demands)]
            m2 = max(d["m2_upper_knm"] for _,_,d in demands)
            m3 = max(d["m3_upper_knm"] for _,_,d in demands)
            for dia,pitch in CAGES:
                if 2*(pi*dia**2/4)/(pitch*panel["thickness_m"]*1000) < .0025:
                    continue
                section, layout = vertical_section(panel,horizontal,cover,mat,dia,pitch)
                interval = SectionInterval(section)
                ratios = []
                try:
                    for _,_,d in demands:
                        value = interval.assess(d["nd_kn"], d["m2_upper_knm"], d["m3_upper_knm"])
                        if value["status"] != "PMM_BOX_SATISFIED":
                            break
                        ratios.append(value)
                except ValueError:
                    pass
                if len(ratios) != len(demands):
                    continue
                for (_,_,d),ratio in zip(demands,ratios):
                    d.update(pmm_upper=ratio["upper_utilization"], basis="PER_CUT_INTERVAL")
                index = max(range(len(ratios)), key=lambda i: ratios[i]["upper_utilization"])
                panel["vertical"] = {**layout,"bound_scope":"PER_CUT_INTERVAL", "all_cuts_nd_kn":whole_n,
                    "all_cuts_m2_upper_knm":m2,"all_cuts_m3_upper_knm":m3,
                    "governing_face":demands[index][0], "governing_combination":demands[index][1],
                    "pmm_upper":ratios[index]["upper_utilization"]}
                break
            required("vertical" in panel,"PROPOSED_VERTICAL_CAGES_DID_NOT_ESTABLISH_PMM_BOUND")
        except (KeyError,TypeError,ValueError) as exc:
            panel["reason"] = str(exc)
    result["pressure_joint_layouts"] = check_joint_layout(geom)
    for row in result["cuts"]:
        checks = row.get("web_demands",[])
        if checks and all("pmm_upper" in d for d in checks):
            row["status"] = "CONDITIONAL_NET_WEB_PMM_BOUND"
            row["pmm_upper"] = max(d["pmm_upper"] for d in checks)
        else:
            row["status"] = "HOLD"
    result["evaluated_cut_combinations"] = sum(r["status"] == "CONDITIONAL_NET_WEB_PMM_BOUND" for r in result["cuts"])
    result["status"] = "CONDITIONAL_NET_WEB_PMM_WITH_PRESSURE_STRIP_REFERENCES" if result["evaluated_cut_combinations"] == result["expected_cut_combinations"] else "HOLD"


def basement_piers(source, stages, bounds, bound, scope):
    groups = defaultdict(list)
    for row in bounds["walls"]:
        if row.get("pier"):
            groups[row["pier"],row["story"]].append(row["member_id"])
    results = []
    for (name,story), ids in sorted(groups.items()):
        if len(ids) < 2:
            continue
        assigned = sorted(set(scope["native_static"]) | set(scope["native_seismic"]) | set(scope["other"]))
        row = {"pier":name,"story":story,"members":sorted(ids),"wall_strength":assigned,
               "expected_cut_combinations":2*len(assigned), "evaluated_cut_combinations":0, "cuts":[], "status":"HOLD"}
        results.append(row)
        try:
            required(bound.get("kind") == ORIGINAL, "ORIGINAL_PIER_SECTION_AND_FORCE_SOURCE_REQUIRED")
            _design(row,source,stages,bound,scope)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            row["reason"] = str(exc)
    return results


def basement_coverage(piers):
    assigned_expected = assigned_evaluated = other_evaluated = pressure_expected = pressure_evaluated = 0
    physical = scheduled = ends_checked = ends_satisfied = initial_short = transferred = extra_transferred = 0
    for pier in piers:
        names = pier["wall_strength"]
        physical += len(pier["members"])
        assigned_expected += 2*len(names)
        pressure_expected += len(names)*len(pier["members"])
        for row in pier["cuts"]:
            if row["status"] == "CONDITIONAL_NET_WEB_PMM_BOUND":
                if row["role"] == "WALL_STRENGTH":
                    assigned_evaluated += 1
                else:
                    other_evaluated += 1
        for panel in (pier.get("geometry") or {}).get("panels", []):
            scheduled += panel.get("schedule_status") == "PRESSURE_PANEL_SCHEDULE_QUALIFIED"
            pressure_evaluated += sum(c["combination"] in names for c in panel.get("horizontal", {}).get("cuts", []))
            for end in panel.get("pressure_connections", {}).get("ends", {}).values():
                ends_checked += 1
                initial_short += end["initial"]["margin_mm"] < 0
                ends_satisfied += end["status"] == "CONDITIONAL_PRESSURE_END_DESIGN"
                for cut in end["transfer"].get("combinations", []):
                    if cut["combination"] in names:
                        transferred += 1
                    else:
                        extra_transferred += 1
    return {"physical_panels":physical,"scheduled_panels":scheduled,"assigned_cuts_expected":assigned_expected,
            "assigned_cuts_evaluated":assigned_evaluated,"additional_static_cuts_evaluated":other_evaluated,
            "assigned_pressure_panel_combinations_expected":pressure_expected,
            "assigned_pressure_panel_combinations_evaluated":pressure_evaluated,
            "physical_pressure_ends_expected":2*physical,"physical_pressure_ends_checked":ends_checked,
            "physical_pressure_ends_satisfied":ends_satisfied,"initial_column_only_shortfalls":initial_short,
            "assigned_pressure_end_combinations_expected":2*pressure_expected,
            "assigned_pressure_end_combinations_evaluated":transferred,
            "additional_static_pressure_end_combinations":extra_transferred}
