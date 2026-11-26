"""Section force equilibrium and proposed web design for column-supported basement piers."""
from collections import defaultdict
from itertools import product
from math import fsum, isfinite, pi

from ..column_engine.section_capacity import Material
from ..column_engine.section_interval import SectionInterval
from .basement_joint_layout import check_joint_layout
from .basement_pier_geometry import folded_section, required, support_id
from .basement_wall_connection import pressure_connections
from .basement_wall_pressure import CAGES, DEFAULT_AGGREGATE_MM, panel_pressure_design, pressure_cases, vertical_section
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


def _mark_collinear_runs(panels):
    columns=defaultdict(list)
    for p in panels:
        for side in ("I","J"):
            if p.get("column_"+side.lower()):
                columns[p["column_"+side.lower()]].append(p)
    for p in panels:
        peers=[]
        for side in ("I","J"):
            peers.extend(q for q in columns.get(p.get("column_"+side.lower()),[]) if q is not p and
                         abs(sum(a*b for a,b in zip(q["width_direction"],p["width_direction"])))>1-1e-9)
        if len(peers)==2:
            for q in [p,*peers]:
                q["collinear_run"]=True


def _through_bar_proof(incident, designs, states, mat, *, run=False):
    """One unspliced main bar per track. Dowels remain separately developed at each wall face."""
    from .wall_support_edge import edge_bar_forces, edge_tie_upper
    (a,side_a),(b,side_b) = incident
    steel, lengths, ends, actions, outer = [], [], [], [], []
    for (panel,side),detail in zip(incident,designs):
        if detail.get("status") != "PROPOSED_COMBINED_CURTAINS":
            return None
        end = detail["ends"][side]
        far_side = "J" if side=="I" else "I"
        far = detail["ends"][far_side]
        if not end["fits_column"] or not far["fits_column"] or (not run and any(e["anchorage_type"]!="STRAIGHT" for e in (end,far))):
            return None
        h=detail["horizontal"]
        steel.append(h["guaranteed_bars_per_m"]*pi*h["diameter_mm"]**2/4*mat.fyd/1000)
        lengths.append(end["position_i_mm"])
        ends.append(end)
        outer.append(panel["span_m"]*1000-far["column_depth_mm"]/2+far["specified_embedment_mm"])
        edge=panel["native_support_edges"][side]
        field = edge_tie_upper if run else edge_bar_forces
        if run and not detail["membrane_and_plate"]["satisfied"]:
            return None
        actions.append(field(states[panel["member"]],edge["nodes"],detail["membrane_and_plate"]["lever_arm_mm"]))
    ha,hb=(d["horizontal"] for d in designs)
    if any(abs(ha[k]-hb[k])>1e-6 for k in ("diameter_mm","first_station_mm","pitch_mm","layers","curtain_inset_mm","cover_mm")):
        return None
    if abs(a["thickness_m"]-b["thickness_m"])>1e-8 or not actions[0] or actions[0].keys()!=actions[1].keys():
        return None
    # Bound complete sign reversal using absolute design forces on both sides at the
    # same level and case. Each outer end still develops the full yield force.
    available=min(e["column_available_mm"] for e in ends)
    checks=[]
    for key in sorted(actions[0]):
        demand=[values[key] for values in actions]
        # In the checked sandwich model horizontal steel is tensile and concrete carries compression.
        # For T1,T2 >= 0 the worst jump across one unspliced rod is max(T1_max,T2_max).
        combine=max if run else fsum
        required_mm=combine(force*lb/resistance for force,lb,resistance in zip(demand,lengths,steel))
        checks.append({"combination":key[0],"point":key[1],"absolute_main_forces_kn_m":demand,
                       "required_bond_mm":required_mm,"available_bond_mm":available,"ratio":required_mm/available})
    governing=max(checks,key=lambda r:r["ratio"])
    if governing["ratio"]>1 or any(e["wall_side_available_mm"]<e["wall_side_required_mm"] for e in ends):
        return None
    return {"detail":"SINGLE_CONTINUOUS_STRAIGHT_BAR_NO_SPLICE_IN_EITHER_PANEL_OR_SUPPORT",
            "members":[a["member"],b["member"]],"column":ends[0]["column"],
            "diameter_mm":ha["diameter_mm"],"pitch_mm":ha["pitch_mm"],"layers":ha["layers"],
            "one_piece_length_mm":fsum(outer),"full_yield_development_mm":lengths,
            "per_face_steel_resistance_kn_m":steel,"reversal_checks":checks,"governing":governing,
            "bond_basis":"TENSILE_TIE_DIFFERENCE_INTERVAL" if run else "ABSOLUTE_REVERSAL"}


def _coordinate_main_bars(geometry, states, designs, aggregate, material, redesign, *, source=None,stages=None):
    from .wall_collinear_run import coordinate_run
    from .basement_joint_layout import main_bar_collision
    joints = defaultdict(list)
    for p in geometry["panels"]:
        for s in ("I","J"):
            joints[support_id(p,s)].append((p,s))
    proofs=coordinate_run(geometry,states,designs,material,aggregate,redesign,source,stages) if source and states else {}
    for col, incident in joints.items():
        if col in proofs:
            continue
        if len(incident)!=2:
            continue
        (a,sa),(b,sb)=incident
        # At a through joint the two centre-lines leave the identical physical point in opposite directions.
        sign = 1 if sa==sb else -1
        dot=fsum(x*y for x,y in zip(a["width_direction"],b["width_direction"]))
        if a["joint_"+sa.lower()]!=b["joint_"+sb.lower()] or sign*dot > -1+1e-9:
            continue
        current=[designs.get(p["member"]) or {} for p,_ in incident]
        if any(d.get("status")!="PROPOSED_COMBINED_CURTAINS" for d in current):
            continue
        def descriptors(trials):
            return [({**p,"horizontal":d["horizontal"]},s,d["ends"][s]) for (p,s),d in zip(incident,trials)]
        if not main_bar_collision(*descriptors(current),aggregate):
            continue
        # A continuous length can terminate with full development at the next column
        # even when another panel starts there. Keep its grid when checking that joint.
        locked = {m for proof in proofs.values() for m in proof["members"]}
        pair=(current[0]["horizontal"]["diameter_mm"],current[0]["horizontal"]["maximum_pitch_mm"])
        # Start with both selected cages, then trial real catalogue bars on the shared elevation lattice.
        candidates=[None]+sorted({pair,*((dia,pitch) for dia in (12,14,16,18) for pitch in (100,60,50))},
                                  key=lambda v:(v[0]**2/v[1],v))
        for match in candidates:
            if match is not None and any(p["member"] in locked for p,_ in incident):
                continue
            trials = current if match is None else [redesign(p,match) for p,_ in incident]
            proof = _through_bar_proof(incident,trials,states,material)
            if not proof or locked.intersection(proof["members"]):
                continue  # Independent terminal development at this end was already specified.
            # Check all independent dowels against the continuous rods before committing this choice.
            local = [{"member":p["member"],"column_i":p["column_i"],"column_j":p["column_j"],
                      "thickness_m":p["thickness_m"],"width_direction":p["width_direction"],"support_sections":p.get("support_sections",{}),"horizontal":d["horizontal"],
                      "pressure_connections":{"ends":{k:dict(v) for k,v in d["ends"].items()}}}
                     for (p,_),d in zip(incident,trials)]
            check=next(r for r in check_joint_layout({"panels":local},aggregate,{col:proof}) if r["column"]==col)
            if check["status"]=="PROPOSED_PRESSURE_BARS_FIT" and check.get("continuous_web"):
                proofs[col]=proof
                for (p,_),d in zip(incident,trials):
                    designs[p["member"]]=d
                break
    return proofs


def _design(result, source, stages, bound, scope, *, boundaries=None):
    name, story = result["pier"], result["story"]
    geom = folded_section(source, bound, name, story, result["members"])
    result["geometry"] = geom
    combos, patterns = pressure_cases(source, bound, scope, name, story, geom["panels"],
        allow_unloaded=bool(source["pier_section_forces"]["read"].get("pressure_shells", {}).get("edge_actions")))
    result.update(expected_cut_combinations=2*len(combos), additional_static=[k for k,s in combos.items()
        if s["role"] == "ADDITIONAL_STATIC_PRESSURE"], uniform_normal_pressures_kn_m2=patterns)
    for face, (combo,spec) in product(("Bottom","Top"),combos.items()):
        try:
            row = _cut(geom,bound,name,story,face,combo,spec)
        except (KeyError,TypeError,ValueError) as exc:
            row = {"face":face,"combination":combo,"role":spec["role"],"status":"HOLD","reason":str(exc)}
        result["cuts"].append(row)
    _mark_collinear_runs(geom["panels"])
    mat, cover = _material(source,stages,geom["material"])
    aggregate = (source.get("building_design") or {}).get("maximum_aggregate_mm", DEFAULT_AGGREGATE_MM)
    result["maximum_aggregate_mm"] = aggregate
    from .wall_pressure_shell import SCHEMA, checked_fields, panel_shell_checks, propose_shell_detail
    read = source["pier_section_forces"]["read"].get("pressure_shells") or {}
    combined = read.get("schema") == SCHEMA
    height = geom["top_m"]-geom["bottom_m"]
    for panel in ([] if combined else geom["panels"]):
        uid = panel["member"]
        try:
            horizontal = panel_pressure_design(panel,combos,cover,mat,height,aggregate=aggregate)
            try:
                horizontal, panel["pressure_connections"] = pressure_connections(
                    source, stages, geom, panel, horizontal, combos, cover, mat, height, aggregate=aggregate)
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
                try:
                    section, layout = vertical_section(panel,horizontal,cover,mat,dia,pitch,aggregate=aggregate)
                except ValueError as exc:
                    if str(exc) == "VERTICAL_WEB_GRID_DOES_NOT_FIT":
                        continue
                    raise
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
    try:
        fields, mesh = checked_fields(source, bound)
        field_reason = None
    except (KeyError, TypeError, ValueError) as exc:
        fields, mesh, field_reason = {}, {}, str(exc)
    for panel in geom["panels"]:
        try:
            required(not field_reason, field_reason)
            uid = panel["member"]
            required(uid in fields and uid in mesh, "NATIVE_TWO_WAY_SHELL_PANEL_MISSING")
            panel["two_way_shell"] = panel_shell_checks(panel,combos,fields[uid],mesh[uid],mat)
        except (KeyError, TypeError, ValueError) as exc:
            panel["two_way_shell"] = {"status":"HOLD","reason":str(exc),"expected_checks":4*len(combos),"checks":[]}
    link_states={}
    if combined:
        from .wall_membrane_design import corner_states
        from .wall_support_edge import support_edge_actions
        for link in geom.get("transfer_panels", []):
            try:
                field = fields[link["member"]]
                required(set(map(tuple,field["corners"])) == {(elm,p) for elm,pts in mesh[link["member"]].items()
                         for p in pts}, "LINK_SHELL_CUT_POPULATION_DIFFERS")
                states = link_states[link["member"]] = corner_states(link,field,combos)
                link["native_support_edges"] = support_edge_actions(link,geom,read["edge_actions"],states,combos, record_transfer_intervals=True)
                link["edge_balance_verified"] = all(e["status"]=="NATIVE_EDGE_CONTROL_SATISFIED"
                                                     for e in link["native_support_edges"].values())
            except (KeyError,TypeError,ValueError) as exc:
                link.update(edge_balance_verified=False, reason=str(exc))
    designs, corner_fields, caches = {}, {}, {}

    def design_candidate(panel, pair=None):
        uid=panel["member"]
        return propose_shell_detail(source,stages,geom,panel,mat,cover,aggregate,result["cuts"],
                                    states=corner_fields.get(uid),edges=panel.get("native_support_edges"),
                                    main_pair=pair,field_cache=caches.setdefault(uid,{}))

    for panel in geom["panels"]:
        shell = panel["two_way_shell"]
        if not shell["checks"]:
            continue
        try:
            states = edges = None
            if combined:
                from .wall_membrane_design import corner_states
                from .wall_support_edge import support_edge_actions
                states = corner_states(panel,fields[panel["member"]],combos)
                edges = support_edge_actions(panel,geom,read["edge_actions"],states,combos)
                corner_fields[panel["member"]] = states
                panel["native_support_edges"] = edges
                shell["capacity_scope"] = "SAME_CORNER_MEMBRANE_AND_PLATE"
                shell["support_scope"] = "NATIVE_VERTICAL_EDGE_ACTIONS"
            detail = design_candidate(panel)
        except (KeyError, TypeError, ValueError) as exc:
            detail = {"status":"HOLD","reason":str(exc)}
        designs[panel["member"]] = detail
    from .wall_return_layout import coordinate_return_tracks
    through = _coordinate_main_bars(geom,corner_fields,designs,aggregate,mat,design_candidate,source=source,stages=stages)
    coordinate_return_tracks(geom,designs,mat,aggregate) if combined else {}
    if combined:
        from .basement_joint_layout import stagger_column_entries
        stagger_column_entries(geom, designs, through, cover, aggregate)
    shell_panels=[]
    for panel in geom["panels"]:
        shadow = {**panel,"pressure_connections":{}}
        shell_panels.append(shadow)
        shell=panel["two_way_shell"]
        detail = designs.get(panel["member"])
        if detail is None:
            continue
        shell["proposed_detail"] = detail
        if detail["status"] == "HOLD":
            continue
        shadow.update(horizontal=detail["horizontal"],vertical=detail["vertical"], pressure_connections={"ends":detail["ends"]})
        if combined and len(detail["cut_pmm"]) == result["expected_cut_combinations"]:
            pmm = {(r["face"],r["combination"]):r["upper_utilization"] for r in detail["cut_pmm"]}
            for cut in result["cuts"]:
                for item in cut.get("web_demands",[]):
                    if item["member"] == panel["member"]:
                        item.update(pmm_upper=pmm[cut["face"],cut["combination"]],basis="SAME_CURTAIN_PER_CUT_INTERVAL")
        for check in shell["checks"]:
            capacities = detail["resistances"][check["axis"]]
            capacity = capacities[0 if check["action"] == "Bending" else 1]
            check.update(proposed_resistance=capacity, proposed_ratio=check["demand"]/capacity)
    from .wall_bridge_layout import bridge_checks
    bridge=bridge_checks(geom,designs,boundaries,source,mat,aggregate,{**corner_fields,**link_states},result["cuts"],stages=stages) if combined else {}
    result["two_way_support_layouts"] = check_joint_layout({"panels":shell_panels,"bridge_checks":bridge},aggregate,through)
    result["pressure_joint_layouts"] = [] if combined else check_joint_layout(geom,aggregate)
    if combined:
        by_support = {r["column"]:r for r in result["two_way_support_layouts"]}
        for panel in geom["panels"]:
            shell = panel["two_way_shell"]
            detail = shell.get("proposed_detail") or {}
            supports = [by_support[support_id(panel,side)] for side in ("I","J")]
            qualified = detail.get("status") == "PROPOSED_COMBINED_CURTAINS" and all(
                r["status"] == "PROPOSED_PRESSURE_BARS_FIT" for r in supports)
            panel["schedule_status"] = "PRESSURE_PANEL_SCHEDULE_QUALIFIED" if qualified else "PRESSURE_PANEL_DETAIL_OPEN"
            if qualified and any(panel["member"] in {item["member"] for prof in link["support_sections"].values()
                    for item in prof["incident_walls"]} and not link.get("edge_balance_verified")
                    for link in geom.get("transfer_panels",[])):
                panel.update(schedule_status="PRESSURE_PANEL_DETAIL_OPEN",reason="TRANSFER_PANEL_EDGE_BALANCE_UNVERIFIED")
            if not qualified:
                panel["reason"] = (detail.get("open_input") or detail.get("reason") or shell.get("reason")
                                   or next((r.get("reason") or r["status"] for r in supports
                                            if r["status"] != "PROPOSED_PRESSURE_BARS_FIT"), "COMBINED_DESIGN_INCOMPLETE"))
        from .wall_collinear_run import qualify_run_terminals
        qualify_run_terminals(geom["panels"], through)
    for row in result["cuts"]:
        checks = row.get("web_demands",[])
        if checks and all("pmm_upper" in d for d in checks):
            row["status"] = "CONDITIONAL_NET_WEB_PMM_BOUND"
            row["pmm_upper"] = max(d["pmm_upper"] for d in checks)
        else:
            row["status"] = "HOLD"
    result["evaluated_cut_combinations"] = sum(r["status"] == "CONDITIONAL_NET_WEB_PMM_BOUND" for r in result["cuts"])
    if result["evaluated_cut_combinations"] == result["expected_cut_combinations"]:
        result["status"] = ("CONDITIONAL_SAME_CURTAIN_NET_WEB_PMM" if combined else
                            "CONDITIONAL_NET_WEB_PMM_WITH_PRESSURE_STRIP_REFERENCES")
    else:
        result["status"] = "HOLD"


def _body_references(source, stages, row, bound, scope):
    """Check physical webs at their own heights when a common folded pier section is undefined."""
    from math import dist
    from .basement_pier_geometry import _context
    from .basement_wall_pressure import layer_resistance
    from .wall_membrane_design import check_curtains, corner_states
    from .wall_pressure_shell import SCHEMA, checked_fields, panel_shell_checks

    if (source.get("pier_section_forces", {}).get("read", {}).get("pressure_shells") or {}).get("schema") != SCHEMA:
        return
    xyz, walls, assigns, props = _context(source)[:4]
    fields, mesh = checked_fields(source, bound)
    row["body_references"] = {}
    for uid in row["members"]:
        try:
            raw = walls[uid]
            a,b,c,d = [xyz[raw["UniquePt"+str(i)]] for i in (1,2,3,4)]
            length = dist(a[:2],b[:2])
            required(length>0 and a[:2]==d[:2] and b[:2]==c[:2] and a[2]==b[2] and c[2]==d[2]>a[2],
                     "RECTANGULAR_VERTICAL_SHELL_BODY_REQUIRED")
            prop = props[assigns[uid]["SectProp"]]
            panel = {"wall":raw["WallBay"],"member":uid,"width_direction":[(b[k]-a[k])/length for k in (0,1)],
                     "thickness_m":float(prop["Thickness"]),"shell_model":prop["ModelType"]}
            combos = {n:{"role":"WALL_STRENGTH","spectral":n in scope["native_seismic"]} for n in row["wall_strength"]}
            material, cover = _material(source, stages, prop["Material"])
            thickness = 1000*panel["thickness_m"]
            lane = thickness/2-cover-1.5*12
            plate = panel_shell_checks(panel,combos,fields[uid],mesh[uid],material)
            # A 1 m strip on a uniform 200 mm grid has at least five rods per curtain.
            combined = check_curtains(corner_states(panel,fields[uid],combos),{},thickness,
                {"diameter_mm":12,"guaranteed_bars_per_m":5},{"diameter_mm":12,"pitch_mm":200},material,lane)
            capacities = {axis:layer_resistance(thickness,off,12,5,material)
                          for axis,off in (("Vertical",lane-12),("Horizontal",lane))}
            for item in plate["checks"]:
                item["proposed_ratio"] = item["demand"]/capacities[item["axis"]][0 if item["action"]=="Bending" else 1]
            row["body_references"][uid] = {"status":"BODY_REFERENCE_EVALUATED","cover_mm":cover,
                "diameter_mm":12,"pitch_mm":200,"schedule_qualified":False,
                "checks":plate["checks"],"membrane_and_plate":combined}
        except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
            row["body_references"][uid] = {"status":"HOLD","reason":str(exc)}


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
            _design(row,source,stages,bound,scope,boundaries=bounds)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            row["reason"] = str(exc)
            if str(exc)=="WALL_BASE_OR_TOP_CHANGES_WITHIN_PIER" and bound.get("kind")==ORIGINAL:
                try:
                    _body_references(source, stages, row, bound, scope)
                except (ValueError, TypeError, KeyError) as missing:
                    row["body_reference_hold"] = str(missing)
    return results


def pressure_ends(panel):
    if "native_support_edges" in panel:
        return ((panel.get("two_way_shell") or {}).get("proposed_detail") or {}).get("ends", {})
    return panel.get("pressure_connections", {}).get("ends", {})


def basement_coverage(piers):
    assigned_expected = assigned_evaluated = other_evaluated = pressure_expected = pressure_evaluated = 0
    physical = scheduled = ends_checked = ends_satisfied = initial_short = transferred = extra_transferred = 0
    def evaluated_combinations(plate, membrane, names):
        return {name for name in names if
                {(q["axis"],q["action"]) for q in plate if q["combination"]==name and q.get("proposed_ratio") is not None}
                == {(axis,action) for axis in ("Horizontal","Vertical") for action in ("Bending","Transverse shear")}
                and {q["action"] for q in membrane if q["combination"]==name and q.get("utilization") is not None}
                == {"Horizontal steel","Vertical steel","Face concrete compression","Core transverse shear"}}

    reference_cases = 0
    combined_checks = plate_checks = same_cage_cuts = edge_cases = balanced_nodes = checked_nodes = 0
    for pier in piers:
        names = pier["wall_strength"]
        physical += len(pier["members"])
        assigned_expected += 2*len(names)
        pressure_expected += len(names)*len(pier["members"])
        for ref in pier.get("body_references", {}).values():
            if ref["status"]=="BODY_REFERENCE_EVALUATED":
                mem = ref["membrane_and_plate"]["checks"]
                num = len(evaluated_combinations(ref["checks"],mem,names))
                pressure_evaluated += num
                reference_cases += num
                combined_checks += len(mem)
                plate_checks += len(ref["checks"])
        for row in pier["cuts"]:
            if row["status"] == "CONDITIONAL_NET_WEB_PMM_BOUND":
                if row["role"] == "WALL_STRENGTH":
                    assigned_evaluated += 1
                else:
                    other_evaluated += 1
        for panel in (pier.get("geometry") or {}).get("panels", []):
            scheduled += panel.get("schedule_status") == "PRESSURE_PANEL_SCHEDULE_QUALIFIED"
            membrane = ((panel.get("two_way_shell") or {}).get("proposed_detail") or {}).get("membrane_and_plate")
            shell = panel.get("two_way_shell") or {}
            if membrane:
                combined_checks += len(membrane["checks"])
                plate_checks += sum("proposed_ratio" in c for c in shell["checks"])
                same_cage_cuts += len(shell["proposed_detail"]["cut_pmm"])
            for edge in panel.get("native_support_edges",{}).values():
                edge_cases += len(edge["cuts"])
                balanced_nodes += edge["balanced_static_interior"]
                checked_nodes += edge["checked_static_interior"]
            if membrane:
                pressure_evaluated += len(evaluated_combinations(shell["checks"], membrane["checks"], names))
            elif shell.get("capacity_scope") != "SAME_CORNER_MEMBRANE_AND_PLATE":
                pressure_evaluated += len({c["combination"] for c in panel.get("horizontal",{}).get("cuts",[])
                                           if c["combination"] in names})
            for end in pressure_ends(panel).values():
                ends_checked += 1
                initial_short += (end.get("initial") or {}).get("margin_mm",0) < 0
                ends_satisfied += (end["status"] == "CONDITIONAL_PRESSURE_END_DESIGN" and
                                   (not membrane or end.get("layout_status") == "PROPOSED_PRESSURE_BARS_FIT"))
                for cut in end["transfer"].get("combinations", []):
                    if cut["combination"] in names:
                        transferred += 1
                    else:
                        extra_transferred += 1
    return {"physical_panels":physical,"scheduled_panels":scheduled,"assigned_cuts_expected":assigned_expected,
            "independent_shell_body_reference_combinations":reference_cases,"combined_membrane_checks":combined_checks,"same_cage_plate_checks":plate_checks,
            "same_cage_pmm_cuts":same_cage_cuts,"native_edge_combinations":edge_cases,
            "balanced_interior_nodal_states":balanced_nodes,"checked_interior_nodal_states":checked_nodes,
            "assigned_cuts_evaluated":assigned_evaluated,"additional_static_cuts_evaluated":other_evaluated,
            "assigned_pressure_panel_combinations_expected":pressure_expected,
            "assigned_pressure_panel_combinations_evaluated":pressure_evaluated,
            "physical_pressure_ends_expected":2*physical,"physical_pressure_ends_checked":ends_checked,
            "physical_pressure_ends_satisfied":ends_satisfied,"initial_column_only_shortfalls":initial_short,
            "assigned_pressure_end_combinations_expected":2*pressure_expected,
            "assigned_pressure_end_combinations_evaluated":transferred,
            "additional_static_pressure_end_combinations":extra_transferred}
