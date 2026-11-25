"""Directional plate checks at every ETABS element corner in a pressure-loaded basement panel."""
from math import floor, fsum, isclose, isfinite, pi

from ..etabs_source_gateway_windows import verify
from .basement_pier_geometry import required
from ..column_engine.section_interval import SectionInterval
from .basement_joint_layout import layout_policy
from .basement_wall_connection import _transfer, developed_entry_grids, support_profiles
from .basement_wall_pressure import CAGES, layer_resistance, vertical_section
from .wall_shell_section import _basis


LEGACY_SCHEMA = "tbdy.next.wall-pressure-shell-fields.v1"
SCHEMA = "tbdy.next.wall-pressure-shell-fields.v2"
PLATE_COMPONENTS = ("M11", "M22", "M12", "V13", "V23")
COMPONENTS = ("F11", "F22", "F12", *PLATE_COMPONENTS)


def checked_fields(source, bound):
    from .wall_transition import mesh_geometry
    read = source.get("pier_section_forces", {}).get("read", {})
    fields = read.get("pressure_shells")
    required(isinstance(fields,dict), "NATIVE_TWO_WAY_SHELL_FIELDS_REQUIRED")
    verify(fields)
    required(fields["schema"] in (LEGACY_SCHEMA, SCHEMA) and fields["units"] == 6 and fields["selection_restored"] is True
             and fields["model_sha256"] == bound["model_sha256"] == read["model_sha256"]
             and fields["parent_input_sha256"] == read["parent_input_sha256"]
             and fields["components"] == list(COMPONENTS if fields["schema"] == SCHEMA else PLATE_COMPONENTS), "TWO_WAY_SHELL_SOLVED_SOURCE_MISMATCH")
    solved = (read.get("transition_shells") or {}).get("solution") or {}
    expected_sha = (read["model_sha256"] if fields.get("solution_role") == "SOLVED_ORIGINAL" else
                    solved.get("solved_sha256") if fields.get("solution_role") == "INPUT_IDENTICAL_PRIVATE_REANALYSIS" else None)
    required(expected_sha and fields["solved_sha256"] == expected_sha and fields["pier_controls"]["outside_tolerance"] == 0
             and fields["pier_controls"]["components"] > 0, "TWO_WAY_SHELL_FORCE_CONTROLS_DIFFER")
    return fields["members"], mesh_geometry(source)[1]


def _interval(coefficients, lo, hi):
    return (fsum(min(c*l,c*u) for c,l,u in zip(coefficients,lo,hi)),
            fsum(max(c*l,c*u) for c,l,u in zip(coefficients,lo,hi)))


def directional_actions(axes, direction, lo, hi):
    """Transform component intervals without assigning simultaneity to spectral extrema."""
    required(len(lo) == len(hi) == 5 and all(isfinite(l) and isfinite(u) and l <= u for l,u in zip(lo,hi)),
             "PRESSURE_SHELL_COMPONENT_BOUNDS_INVALID")
    a,b,_ = axes
    dx,dy = direction
    h1,h2 = dx*a[0]+dy*a[1], dx*b[0]+dy*b[1]
    z1,z2 = a[2],b[2]
    coeffs = ((h1*h1,h2*h2,2*h1*h2), (z1*z1,z2*z2,2*z1*z2),
              (h1*z1,h2*z2,h1*z2+h2*z1), (0,0,0,h1,h2), (0,0,0,z1,z2))
    return [_interval(c,lo,hi) for c in coeffs]


def panel_shell_checks(panel, combos, item, mesh, material):
    direction = panel["width_direction"]
    required(panel.get("shell_model") in {"Shell-Thick","Shell-Thin"}, "SHELL_PROPERTY_WITH_PLATE_BENDING_REQUIRED")
    expected = {(elm,pt) for elm,pts in mesh.items() for pt in pts}
    corners = [tuple(q) for q in item["corners"]]
    required(expected and len(corners) == len(expected) and set(corners) == expected
             and set(item["axes"]) == set(mesh) and set(combos) <= set(item["cases"]),
             "TWO_WAY_SHELL_POPULATION_MISMATCH")
    axes = {elm:_basis(matrix,(direction[1],-direction[0],0.)) for elm,matrix in item["axes"].items()}
    h,v = panel.get("horizontal",{}),panel.get("vertical",{})
    capacities = {}
    if h:
        capacities["Horizontal"] = (h["design_moment_resistance_knm_m"],h["diagonal_cracking_kn_m"])
    if h and v:
        thickness = panel["thickness_m"]*1000
        depth = thickness/2-h["cover_mm"]-h["curtain_inset_mm"]-2*h["diameter_mm"]-v["diameter_mm"]/2
        capacities["Vertical"] = layer_resistance(thickness,depth,v["diameter_mm"],floor(1000/v["pitch_mm"]+1e-9),material)
    checks = []
    for name, spec in combos.items():
        steps = item["cases"][name]
        if set(steps) == {"Min","Max"}:
            lows, highs = steps["Min"], steps["Max"]
        else:
            required(len(steps)==1 and next(iter(steps)) in ("","Static","Single Value") and not spec["spectral"],
                     "EXPECTED_NATIVE_PRESSURE_ENVELOPE_OR_SIGNED_STATIC")
            lows = highs = next(iter(steps.values()))
        required(len(lows) == len(highs) == len(corners), "TWO_WAY_SHELL_RESULT_COUNT_MISMATCH")
        governing = {}
        for (elm,pt),lo,hi in zip(corners,lows,highs):
            if not spec["spectral"]:
                required(all(isclose(l,u,rel_tol=1e-10,abs_tol=1e-9) for l,u in zip(lo,hi)),
                         "STATIC_SHELL_COMPONENTS_DO_NOT_DEFINE_ONE_STATE")
            mh,mv,tw,vh,vv = directional_actions(axes[elm],direction,lo[-5:],hi[-5:])
            twist = max(map(abs,tw))
            for axis,m,q in (("Horizontal",mh,vh),("Vertical",mv,vv)):
                # The symmetric two-face bending bound follows |m| + |m_hv| in each steel direction.
                for action,demand,capacity_index,unit in (("Bending",max(map(abs,m))+twist,0,"kN·m/m"),
                                                         ("Transverse shear",max(map(abs,q)),1,"kN/m")):
                    key = (axis,action)
                    if key not in governing or demand > governing[key]["demand"]:
                        capacity = capacities.get(axis,(None,None))[capacity_index]
                        governing[key] = {"combination":name, "role":spec["role"], "axis":axis,"action":action,
                            "element":elm,"point":pt,"native_steps":sorted(steps),"native_low":lo,"native_high":hi,
                            "basis":"NATIVE_SCALAR_ENVELOPE_BOUND" if spec["spectral"] else "SIGNED_STATIC",
                            "direct_interval":list(m if action=="Bending" else q),
                            "twisting_interval_knm_m":list(tw),"demand":demand,"resistance":capacity,"unit":unit,
                            "ratio":demand/capacity if capacity else None,
                            "status":"LAYER_CAPACITY_REQUIRED" if capacity is None else
                                     "ABOVE_SECTION_REFERENCE" if demand>capacity else "WITHIN_SECTION_REFERENCE"}
        checks.extend(governing.values())
    return {"status":"TWO_WAY_SHELL_CORNER_ACTIONS_EVALUATED", "elements":len(mesh), "corners":len(corners),
            "combinations":len(combos), "expected_checks":4*len(combos),"checks":checks,
            "capacity_scope":"SYMMETRIC_STRIP_ZERO_MEMBRANE_FORCE",
            "support_scope":"COMBINED_INTERFACE_ACTIONS_AND_DETAIL_REQUIRED"}


def propose_shell_detail(source, stages, geometry, panel, material, cover, aggregate, cuts, *, states=None, edges=None, main_pair=None, field_cache=None):
    """Select both curtains together. Every resistance uses the chosen bar coordinates."""
    from .wall_membrane_design import SELECTION_LIMIT, check_curtains

    rows = panel["two_way_shell"]["checks"]
    demands = {(axis, action): max(r["demand"] for r in rows if (r["axis"], r["action"]) == (axis, action))
               for axis in ("Horizontal", "Vertical") for action in ("Bending", "Transverse shear")}
    web_cuts = [(c["face"],c["combination"],d) for c in cuts for d in c.get("web_demands",[])
                if d["member"] == panel["member"]]
    cases = {r["combination"] for r in rows}
    required(len(web_cuts) == 2*len(cases) and {(f,n) for f,n,_ in web_cuts}
             == {(f,n) for f in ("Top","Bottom") for n in cases}, "SHELL_DETAIL_PIER_CUT_POPULATION_MISMATCH")
    combined = states is not None
    required(not combined or (set(states)==cases and edges is not None), "NATIVE_EDGE_AND_MEMBRANE_INPUT_REQUIRED")
    profiles = support_profiles(source, stages, panel)
    policy = layout_policy(geometry, panel, cover, aggregate)
    if policy["inner"]:
        policy = {**policy, "phase":policy["phase"]+1}
    if combined:
        # Collinear neighbours use opposite elevation phases for their independent
        # dowels as well as their main bars. Different wall directions are offset half a module.
        policy = {**policy, "dowel_phase":policy["phase"]}
    t = panel["thickness_m"]*1000
    limit = SELECTION_LIMIT if combined else 1.
    best = best_rank = None
    if field_cache is None:
        field_cache = {}
    grids = developed_entry_grids(profiles,geometry,panel,cover,material,policy,include_unanchored=combined)
    for h, ends, lane in grids:
        if main_pair and ((h["diameter_mm"],h["maximum_pitch_mm"]) != main_pair
                          or not all(e["fits_column"] for e in ends.values())):
            continue
        hcap = layer_resistance(t,lane,h["diameter_mm"],h["guaranteed_bars_per_m"],material)
        if demands["Horizontal","Bending"] > limit*hcap[0] or demands["Horizontal","Transverse shear"] > hcap[1]:
            continue
        strip = h if combined else {**h, "cuts":panel["horizontal"]["cuts"]}
        for dia, pitch in CAGES:
            if 2*pi*dia**2/4 < .0025*pitch*t:
                continue
            try:
                section, v = vertical_section(panel,h,cover,material,dia,pitch,aggregate=aggregate)
            except ValueError as exc:
                if str(exc) == "VERTICAL_WEB_GRID_DOES_NOT_FIT":
                    continue
                raise
            depth = lane-(h["diameter_mm"]+dia)/2
            vcap = layer_resistance(t,depth,dia,floor(1000/v["pitch_mm"]+1e-9),material)
            if demands["Vertical","Bending"] > limit*vcap[0] or demands["Vertical","Transverse shear"] > vcap[1]:
                continue
            trial = {"maximum_aggregate_mm":aggregate,"horizontal":h,"vertical":v,
                     "resistances":{"Horizontal":hcap,"Vertical":vcap},"cut_pmm":[],"ends":{}}
            conditions = []
            if combined:
                check = check_curtains(states,field_cache,t,h,v,material,lane)
                trial["membrane_and_plate"] = check
                if not check["satisfied"]:
                    rank = (3,max(check["governing"]["utilization"], check["steel_max"]/limit))
                    if best_rank is None or rank < best_rank:
                        best_rank, best = rank, {**trial,"status":"UNQUALIFIED_CURTAIN_TRIAL",
                                                 "reason":"COMBINED_CURTAIN_RESISTANCE_OR_RESERVE_EXCEEDED"}
                    continue
            for side, end in ends.items():
                transfer = _transfer(panel, profiles[side], strip, material, policy, vertical_diameter=dia,
                                     native_edge=edges[side] if combined else None)
                end_ok = transfer["status"] != "HOLD" and end["fits_column"]
                status = "CONDITIONAL_PRESSURE_END_DESIGN" if end_ok else "DOWEL_OR_ANCHORAGE_LAYOUT_REQUIRED"
                if not end_ok:
                    conditions.append(status)
                trial["ends"][side] = {**end, "transfer":transfer,"status":status}
            rank = (1,len(conditions)) if conditions else (0,0)
            if (main_pair and conditions) or (best_rank is not None and rank >= best_rank):
                continue
            interval = SectionInterval(section)
            for face, name, demand in web_cuts:
                pmm = interval.assess(demand["nd_kn"],demand["m2_upper_knm"],demand["m3_upper_knm"])
                if pmm["status"] != "PMM_BOX_SATISFIED":
                    break
                trial["cut_pmm"].append({"face":face,"combination":name,"upper_utilization":pmm["upper_utilization"]})
            if len(trial["cut_pmm"]) != len(web_cuts):
                if combined and (best_rank is None or best_rank[0]>2):
                    best_rank, best = (2,-len(trial["cut_pmm"])), {**trial,"status":"UNQUALIFIED_CURTAIN_TRIAL",
                                                               "reason":"SAME_CURTAIN_PIER_PMM_NOT_ESTABLISHED"}
                continue
            if combined:
                edge_ok = all(e["status"]=="NATIVE_EDGE_CONTROL_SATISFIED" for e in edges.values())
                if not edge_ok:
                    conditions.append("NATIVE_EDGE_EQUILIBRIUM_UNRESOLVED")
                trial.update(status="UNQUALIFIED_CURTAIN_TRIAL" if conditions else "PROPOSED_COMBINED_CURTAINS",
                             support_scope="NATIVE_EDGE_FRICTION_AND_ANCHORED_TENSION",open_input=", ".join(dict.fromkeys(conditions)))
            else:
                trial.update(status="PROPOSED_TWO_WAY_CURTAINS",support_scope="DEVELOPMENT_AND_ONE_WAY_DOWEL_REFERENCE",
                             open_input="COMBINED_SHELL_MEMBRANE_AND_BENDING_AND_NATIVE_INTERFACE_TRANSFER")
            if rank[0]==0:
                return trial
            best_rank, best = rank, trial
    return best or {"status":"HOLD","reason":"NO_CURTAIN_AT_PROJECT_COVER_MEETS_BOTH_DIRECTIONS_AND_SUPPORTS"}
