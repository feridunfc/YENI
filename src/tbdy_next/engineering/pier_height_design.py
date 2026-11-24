"""TBDY 7.6 wall checks on both physical faces of the original ETABS pier stacks."""
from math import ceil, floor, isclose

from ..column_engine.section_interval import SectionInterval
from .confinement_regions import _hook
from .pier_seismic_shear import DISPLAY_KN, envelope


def section_dimensions(length, thick, height):
    # Ordinary isolated rectangular wall. Use the full wall length as its
    # laterally unsupported length, without claiming a perpendicular return.
    minimum = max(250., height/16, length/30)
    return {"panel_height_mm": height, "provided_thickness_mm": thick, "required_thickness_mm": minimum,
            "length_over_thickness": length/thick, "status": "DIMENSIONS_SATISFIED"
            if thick >= minimum and length >= 6*thick else "DIMENSIONS_REQUIRE_REVIEW"}


def web_ties(detail, height_mm):
    # One crosstie joins the two curtains at each vertical station and horizontal
    # layer. The top/bottom half pitches leave no uncovered strip between panels.
    width, pitch = detail["web_width_mm"], detail["web_vertical_pitch_mm"]
    layers = ceil(height_mm / detail["web_horizontal_pitch_mm"])
    if min(width, height_mm, pitch, layers) <= 0:
        raise ValueError("POSITIVE_WEB_LAYOUT_REQUIRED")
    dz = height_mm/layers
    nx = detail["web_stations_per_face"]
    density = nx*layers*1e6/(width*height_mm)
    # Minimum in a sliding 1 m by 1 m square fully contained in this grid.
    per_square = floor(1000/pitch + 1e-12)*floor(1000/dz + 1e-12)
    dia = detail["web_bar_diameter_mm"]
    return {"diameter_mm": dia, "count": nx*layers, "stations_per_layer": nx, "layers": layers,
            "horizontal_pitch_mm": pitch, "first_layer_above_bottom_mm": dz/2, "vertical_pitch_mm": dz,
            "ties_per_m2": density, "minimum_ties_in_full_m2": per_square, "critical_required_per_m2": 10,
            "ordinary_required_per_m2": 4, "hook": _hook(dia),
            "status": "WEB_CROSSTIES_CALCULATED" if min(per_square, density) >= 10 else "WEB_CROSSTIES_INSUFFICIENT"}


def joint_friction(detail, ve, tension):
    # Proposal for roughened (>= 5 mm) concrete with anchored perpendicular
    # vertical bars. Reserve separate steel for net direct tension. No credit
    # for permanent compression. kN, mm² and MPa.
    area, fc, fyd = detail["ach_mm2"], detail["fck_mpa"], detail["fyd_mpa"]
    if detail["fyk_mpa"] > 500 or min(area, fc, fyd) <= 0 or min(ve, tension) < 0:
        raise ValueError("JOINT_MATERIAL_OR_DEMAND_OUTSIDE_SCOPE")
    as_required = tension*1000/fyd
    available = detail["steel_area_mm2"] - as_required
    resistance = {"roughened_concrete_and_steel_kn": area*detail["fctd_mpa"]/1000 + max(0., available)*fyd/1000,
                  "tbdy_7_19_concrete_cap_kn": area*min(.2*fc, 3.3+.08*fc)/1000,
                  "ts500_8_1_7_concrete_cap_kn": .2*min(detail["fcd_mpa"], 25.)*area/1000}
    vr = min(resistance.values())
    return {**resistance, "ve_in_plane_upper_kn": ve, "tension_upper_kn": tension, "reserved_steel_mm2": as_required,
            "available_friction_steel_mm2": max(0., available), "mu": 1., "resistance_kn": vr,
            "upper_utilization": ve/vr, "status": "ROUGH_JOINT_BOUND_SATISFIED" if available >= 0 and ve <= vr
            else "JOINT_BOUND_INCONCLUSIVE"}


def _ordinate(rows, z, field):
    """Same panel for interpolation. Include both sides of a storey jump at z."""
    by_member = {}
    for r in rows:
        by_member.setdefault(r["member"], {})[r["face"]] = r
    candidates = []
    for faces in by_member.values():
        a, b = faces["Bottom"], faces["Top"]
        za, zb = a["z_m"], b["z_m"]
        if za >= zb:
            raise ValueError("POSITIVE_PHYSICAL_PANEL_HEIGHT_REQUIRED")
        if za-1e-8 <= z <= zb+1e-8:
            f = min(1., max(0., (z-za)/(zb-za)))
            candidates.append((1-f)*a[field] + f*b[field])
    if not candidates:
        raise ValueError("REFERENCE_ELEVATION_OUTSIDE_PIER")
    return max(candidates)


def _branch(rows, site, branch, ztop, *, shear_available=True):
    base, z = branch["reference_z_m"], site["z_m"]
    h = ztop-base
    if h <= 0 or not isclose(h*1000, branch["wall_height_mm"], abs_tol=1e-5):
        raise ValueError("INCONSISTENT_PIER_HEIGHT")
    hcr = branch["minimum_hcr_mm"]/1000
    fraction = max(0., z-base-hcr)/h
    demands = {}
    for component in ("m2", "m3"):
        bottom = _ordinate(rows, base, component)
        roof = _ordinate(rows, ztop, component)
        # Spectral signs need not coincide. Positive interpolation weights
        # bound the shifted signed line for every admissible pair.
        demands[component+"_design_knm"] = max(site[component], (1-fraction)*bottom + fraction*roof)
    third = base + h/3
    f = min(1., max(0., (z-third)/(ztop-third)))
    for kind in ("solid", "coupled") if shear_available else ():
        def upper_envelope(level):
            # Both physical faces at a storey jump and every larger demand above the cut.
            native = _ordinate(rows, level, kind)
            return max([native] + [r[kind] for r in rows if r["z_m"] >= level - 1e-8])

        bottom = upper_envelope(base)
        knee = upper_envelope(third)
        upper = upper_envelope(max(base, z))
        if z >= third:
            upper = max(upper, (1-f)*knee + f*max(.5*bottom, _ordinate(rows, ztop, kind)))
        demands[kind] = {"ve_upper_kn": max(upper, site[kind]), "base_upper_kn": bottom,
                         "third_height_upper_kn": knee, "third_height_native_kn": _ordinate(rows, third, kind),
                         "method": "NONREDUCING_HEIGHT_ENVELOPE_OF_ALTERNATIVE_SHEAR_LIMIT"}
    return {**demands, "reference_z_m": base, "hcr_m": hcr, "third_height_z_m": third,
            "above_plateau_slope_fraction": fraction}


def pier_design_checks(pier, objects, section, detail, bound, combinations, shear, clear):
    expected = [{"member": uid, "story": objects[uid]["story"], "face": face}
                for uid in pier["member_ids"] for face in ("Bottom", "Top")]
    rows, panels, joints = [], [], []
    properties = bound.get("properties", {})
    for uid in pier["member_ids"]:
        story = objects[uid]["story"]
        native = properties.get((pier["pier"], story), [])
        panel = {"member": uid, "story": story, "status": "HOLD"}
        panels.append(panel)
        if uid in clear and detail and len(native) == 1:
            bottom, top = (float(native[0][k]) for k in ("CGBotZ", "CGTopZ"))
            panel.update(bottom_z_m=bottom, top_z_m=top,
                         dimensions=section_dimensions(pier["length_mm"], pier["thickness_mm"], 1000*(top-bottom)),
                         web_crossties=web_ties(detail, 1000*(top-bottom)), status="PANEL_CALCULATED")
    local_shear = {(r["member"], r["face"], r["combination"]): r for r in shear}
    capacity = SectionInterval(section) if section else None
    for combo in sorted(combinations):
        cuts = []
        for site in expected:
            r = {**site, "combination": combo, "status": "HOLD"}
            rows.append(r)
            uid, face, story = site["member"], site["face"], site["story"]
            try:
                if uid not in clear or not detail:
                    raise ValueError("VERIFIED_PIER_GEOMETRY_AND_PROPOSED_CAGE_REQUIRED")
                native = envelope(bound["groups"][pier["pier"], story, face, combo])
                r["z_m"] = float(properties[pier["pier"], story][0]["CGBotZ" if face == "Bottom" else "CGTopZ"])
                r["nd_interval_kn"] = [-native["Max"]["P"]-DISPLAY_KN, -native["Min"]["P"]+DISPLAY_KN]
                r["axial_limit_kn"] = .35 * detail["ach_mm2"] * detail["fck_mpa"]/1000
                r["axial_ratio"] = max(0., r["nd_interval_kn"][1])/r["axial_limit_kn"]
                for moment in ("M2", "M3"):
                    r[moment.lower()] = max(abs(native[s][moment]) for s in ("Min", "Max")) + .001
                cuts.append(r)
                local = local_shear[uid, face, combo]
                for kind in ("solid", "coupled"):
                    r[kind] = local["branches"][kind]["ve_upper_kn"]
            except (ValueError, KeyError, TypeError) as exc:
                r["reason"] = str(exc)
        if len(cuts) == len(expected):
            shear_available = all("solid" in r and "coupled" in r for r in cuts)
            for r in cuts:
                try:
                    branches = {k: _branch(cuts, r, b, pier["top_z_m"], shear_available=shear_available)
                                for k, b in pier["height_branches"].items()}
                    r["height_branches"] = branches
                    for axis in ("m2", "m3"):
                        r[axis+"_design_knm"] = max(b[axis+"_design_knm"] for b in branches.values())
                    if shear_available:
                        r["ve_upper_kn"] = max(b[k]["ve_upper_kn"] for b in branches.values() for k in ("solid","coupled"))
                        r["shear_upper_ratio"] = max(b[k]["ve_upper_kn"]/min(detail["vr_kn"], detail[k+"_strut_limit_kn"])
                            for b in branches.values() for k in ("solid", "coupled"))
                    else:
                        r["reason"] = "COMPLETE_STACK_SHEAR_CONTROLS_REQUIRED"
                    r["pmm"] = capacity.assess(r["nd_interval_kn"], r["m2_design_knm"], r["m3_design_knm"])
                    r["status"] = "SECTION_BOUND_SATISFIED" if (r["pmm"]["status"] == "PMM_BOX_SATISFIED"
                        and r.get("shear_upper_ratio", 2) <= 1 and r["axial_ratio"] <= 1) else "SECTION_BOUND_INCONCLUSIVE"
                except (ValueError, KeyError, TypeError) as exc:
                    r["reason"] = str(exc)
        else:
            for r in cuts:
                r["reason"] = "COMPLETE_STACK_END_RESULTS_REQUIRED_FOR_HEIGHT_DIAGRAM"
        # One construction plane at each panel bottom. Include the adjacent lower
        # panel's top demand at internal floors, without counting that plane twice.
        combo_rows = { (r["member"], r["face"]): r for r in rows if r["combination"] == combo}
        for panel in panels:
            joint = {"upper_member": panel["member"], "story": panel["story"], "combination": combo, "status": "HOLD"}
            joints.append(joint)
            if "bottom_z_m" not in panel or len(cuts) != len(expected):
                continue
            z = panel["bottom_z_m"]
            sides = [r for r in combo_rows.values() if "z_m" in r and abs(r["z_m"]-z) < 1e-8]
            if not sides or any("ve_upper_kn" not in r for r in sides):
                continue
            joint.update(z_m=z, faces=[[r["member"], r["face"]] for r in sides])
            try:
                joint.update(joint_friction(detail, max(r["ve_upper_kn"] for r in sides),
                                           max(0., *(-r["nd_interval_kn"][0] for r in sides))))
            except ValueError as exc:
                joint["reason"] = str(exc)
    return rows, panels, joints
