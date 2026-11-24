"""Directional plate checks at every ETABS element corner in a pressure-loaded basement panel."""
from math import floor, fsum, isclose, isfinite, pi

from ..etabs_source_gateway_windows import verify
from .basement_pier_geometry import required
from ..column_engine.section_interval import SectionInterval
from .basement_joint_layout import layout_policy
from .basement_wall_connection import _transfer, developed_entry_grids, support_profiles
from .basement_wall_pressure import CAGES, layer_resistance, vertical_section
from .wall_shell_section import _basis


SCHEMA = "tbdy.next.wall-pressure-shell-fields.v1"
COMPONENTS = ("M11", "M22", "M12", "V13", "V23")


def checked_fields(source, bound):
    from .wall_transition import mesh_geometry
    read = source.get("pier_section_forces", {}).get("read", {})
    fields = read.get("pressure_shells")
    required(isinstance(fields,dict), "NATIVE_TWO_WAY_SHELL_FIELDS_REQUIRED")
    verify(fields)
    required(fields["schema"] == SCHEMA and fields["units"] == 6 and fields["selection_restored"] is True
             and fields["model_sha256"] == bound["model_sha256"] == read["model_sha256"]
             and fields["parent_input_sha256"] == read["parent_input_sha256"]
             and fields["components"] == list(COMPONENTS), "TWO_WAY_SHELL_SOLVED_SOURCE_MISMATCH")
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
             and set(item["axes"]) == set(mesh) and set(item["cases"]) == set(combos),
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
            mh,mv,tw,vh,vv = directional_actions(axes[elm],direction,lo,hi)
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


def propose_shell_detail(source, stages, geometry, panel, material, cover, aggregate, cuts):
    """Size a common pair of curtains against plate actions and the allocated native pier cuts."""
    rows = panel["two_way_shell"]["checks"]
    demands = {(axis, action): max(r["demand"] for r in rows if (r["axis"], r["action"]) == (axis, action))
               for axis in ("Horizontal", "Vertical") for action in ("Bending", "Transverse shear")}
    web_cuts = [(c["face"],c["combination"],d) for c in cuts for d in c.get("web_demands",[])
                if d["member"] == panel["member"]]
    cases = {r["combination"] for r in rows}
    required(len(web_cuts) == 2*len(cases) and {(f,n) for f,n,_ in web_cuts}
             == {(f,n) for f in ("Top","Bottom") for n in cases}, "SHELL_DETAIL_PIER_CUT_POPULATION_MISMATCH")
    profiles = support_profiles(source, stages, panel)
    policy = layout_policy(geometry, panel, cover, aggregate)
    if policy["inner"]:
        # Give adjacent collinear inner curtains their own elevations on the shared lattice.
        policy = {**policy, "phase":policy["phase"]+1}
    t = panel["thickness_m"]*1000
    first = None
    for h, ends, lane in developed_entry_grids(profiles,geometry,panel,cover,material,policy):
        hcap = layer_resistance(t,lane,h["diameter_mm"],h["guaranteed_bars_per_m"],material)
        if demands["Horizontal","Bending"] > hcap[0] or demands["Horizontal","Transverse shear"] > hcap[1]:
            continue
        # This separate dowel reference uses the documented one-way support reaction.
        # Plate transverse shear at a corner alone cannot establish the force across the joint.
        strip = {**h,"cuts":panel["horizontal"]["cuts"]}
        for dia, pitch in CAGES:
            if 2*pi*dia**2/4 < .0025*pitch*t:
                continue
            try:
                section, v = vertical_section(panel,h,cover,material,dia,pitch,aggregate=aggregate)
            except ValueError as exc:
                if str(exc) == "VERTICAL_WEB_GRID_DOES_NOT_FIT":
                    continue
                raise
            depth = lane-h["diameter_mm"]/2-dia/2
            vcap = layer_resistance(t,depth,dia,floor(1000/v["pitch_mm"]+1e-9),material)
            if demands["Vertical","Bending"] > vcap[0] or demands["Vertical","Transverse shear"] > vcap[1]:
                continue
            detailed_ends = {}
            for side, end in ends.items():
                transfer = _transfer(panel, profiles[side], strip, material, policy, vertical_diameter=dia)
                detailed_ends[side] = {**end, "transfer":transfer,
                    "status":"CONDITIONAL_PRESSURE_END_DESIGN" if transfer["status"] != "HOLD" else "DOWEL_LAYOUT_REQUIRED"}
            dowels_fit = all(end["transfer"]["status"] != "HOLD" for end in detailed_ends.values())
            if first and not dowels_fit:
                continue
            pmm = []
            interval = SectionInterval(section)
            for face, name, demand in web_cuts:
                check = interval.assess(demand["nd_kn"],demand["m2_upper_knm"],demand["m3_upper_knm"])
                if check["status"] != "PMM_BOX_SATISFIED":
                    break
                pmm.append({"face":face,"combination":name,"upper_utilization":check["upper_utilization"]})
            if len(pmm) != len(web_cuts):
                continue
            trial = {"status":"PROPOSED_TWO_WAY_CURTAINS", "maximum_aggregate_mm":aggregate,
                     "horizontal":h, "vertical":v, "ends":detailed_ends, "cut_pmm":pmm,
                     "resistances":{"Horizontal":hcap,"Vertical":vcap},
                     "support_scope":"STRAIGHT_DEVELOPMENT_AND_SEPARATE_ONE_WAY_DOWEL_REFERENCE",
                     "open_input":"COMBINED_SHELL_MEMBRANE_AND_BENDING_AND_NATIVE_INTERFACE_TRANSFER"}
            if dowels_fit:
                return trial
            first = trial
            break
    return first or {"status":"HOLD","reason":"NO_STRAIGHT_TWO_WAY_CURTAIN_FITS_DEMAND_AND_BOTH_SUPPORT_CAGES"}
