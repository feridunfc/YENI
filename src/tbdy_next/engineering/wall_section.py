"""Signed gravity PMM and in-plane shear of a rectangular, singly assigned pier."""
from math import ceil, cos, floor, hypot, isclose, isfinite, radians, sin, sqrt
import re

from ..column_engine.section_capacity import Bar, Material, Section, perimeter, solver
from ..column_engine.transverse_kernel import bar_area_mm2
from ..etabs_geometry import AREA_INSERTION, FRAME_INSERTION
from .beam_r10_live import _design_factors, _steel_grade_mpa
from .column_clear_length import _FRAME_TRANSLATION, _SHELL_TRANSLATION, _index, _no_translation, _records, _translation_fields
from .pier_force_source import METHOD, ORIGINAL, bound_pier_forces, signed_vector
from .pier_height_design import pier_design_checks
from .pier_joint_strength import strong_wall_checks
from .pier_seismic_shear import envelope, upper_shear, vertical_component, wall_load_scope


def reinforced_section(pier, feature):
    cage, end = pier["transverse_cage"], pier["adopted_constant_detail"]
    if cage.get("status") != "CONDITIONAL_TRANSVERSE_CAGE_CALCULATED":
        raise ValueError("TWO_COMPLETE_BOUNDARY_CAGES_REQUIRED")
    if not all(b["ends_required"] for b in pier["height_branches"].values()):
        raise ValueError("WEB_DEFINITION_REQUIRES_BASE_OR_SQUAT_WALL_DECISION")
    length, thick, width = pier["length_mm"], pier["thickness_mm"], end["end_width_mm"]
    web = length - 2 * width
    gc, gs = _design_factors(feature.get("design_preferences"))
    fy, es = _steel_grade_mpa(feature.get("pmm_section_source"), cage["grade"])
    if not all((gc, gs, fy, es)) or fy != cage["fywk_mpa"] or web <= 0:
        raise ValueError("PIER_MATERIAL_FACTORS_OR_DISTINCT_WEB_REQUIRED")
    fc = cage["fck_mpa"]
    material = Material(fc, fc / gc, fy / gs, es)
    dia = 12
    area = bar_area_mm2(dia)
    # Two curtains. Limit both directions to 200 mm as a detailing proposal.
    pitch_limit = min(200, 2 * area / (0.0025 * thick))
    horizontal = 10 * floor(pitch_limit / 10)
    if horizontal <= dia or thick <= 2 * (cage["cover_mm"] + 1.5 * dia):
        raise ValueError("WEB_CURTAINS_DO_NOT_FIT")
    count = ceil(web / pitch_limit)
    pitch = web / count
    cover = cage["cover_mm"]
    at_face = thick / 2 - cover - 1.5 * dia  # Horizontal bars occupy the outer layer.
    perimeter_bars, _, _ = perimeter(width, thick, cover, cage["tie_diameter_mm"], end["diameter_mm"],
                                     *cage["longitudinal_grid_u_v"])
    offset = (length - width) / 2
    bars = [Bar(side * (offset + b.x2), b.x3, b.area) for side in (-1, 1) for b in perimeter_bars]
    bars.extend(Bar((2*i-count+1) * pitch / 2, side * at_face, area)
                for i in range(count) for side in (-1, 1))
    rho_v = 2 * count * area / (web * thick)
    rho_h = 2 * area / (horizontal * thick)
    interface_spacing = pitch/2 + cover + cage["tie_diameter_mm"] + end["diameter_mm"]/2
    if min(rho_v, rho_h) < 0.0025 - 1e-12 or max(pitch, horizontal, interface_spacing) > 250:
        raise ValueError("PIER_WEB_RATIO_OR_SPACING_EXCEEDS_LIMIT")
    section = Section(length, thick, tuple(bars), material)
    ach = length * thick
    fctd = 0.35 * sqrt(fc) / gc
    vr = ach * (0.65 * fctd + rho_h * material.fyd) / 1000
    return section, {"web_width_mm": web, "web_bar_diameter_mm": dia, "web_stations_per_face": count,
        "web_vertical_pitch_mm": pitch, "web_horizontal_pitch_mm": horizontal,
        "boundary_to_web_pitch_mm": interface_spacing, "rho_web_vertical": rho_v, "rho_web_horizontal": rho_h,
        "boundary_bars_per_end": len(perimeter_bars), "total_vertical_bars": len(bars),
        "steel_area_mm2": sum(b.area for b in bars), "fck_mpa": fc, "fctd_mpa": fctd, "fyd_mpa": material.fyd,
        "ach_mm2": ach, "vr_kn": vr, "solid_strut_limit_kn": 0.85 * ach * sqrt(fc) / 1000,
        "coupled_strut_limit_kn": 0.65 * ach * sqrt(fc) / 1000,
        "steel_grade": cage["grade"], "fyk_mpa": fy, "fcd_mpa": material.fcd, "clear_cover_mm": cover}


def _isolated_panel(member, story, source, bound, pier):
    tables = source["vs06_b1_geometry_source"]["table_reads"]
    panels = {r["UniqueName"]: r for r in tables["Wall Object Connectivity"]["rows"]}
    points = {r["UniqueName"]: tuple(float(r[k]) for k in ("X", "Y", "Z"))
              for r in tables["Point Object Connectivity"]["rows"]}
    columns = tables["Column Object Connectivity"]["rows"]
    shapes = {r["Name"]: r for r in tables["Frame Section Property Definitions - Concrete Rectangular"]["rows"]}
    frame_sections = {r["UniqueName"]: r["SectProp"] for r in tables["Frame Assignments - Section Properties"]["rows"]}
    placement = source["column_axial"]["r10_source"]["table_reads"]
    frames = _index(_records(placement, FRAME_INSERTION, "UniqueName CardinalPt Story"), "UniqueName")
    frame_fields = _translation_fields(placement[FRAME_INSERTION], 1, _FRAME_TRANSLATION, ("OffsetCSys",))
    wall_fields = _translation_fields(placement[AREA_INSERTION], 2, _SHELL_TRANSLATION,
                                      ("CoordSys", "PointLabel", "PointName", "PointNumber"))
    insertions = [r for r in _records(placement, AREA_INSERTION, "UniqueName CardinalPt Story") if r["UniqueName"] == member]
    if not insertions or any(r["CardinalPt"] != "Middle" or not _no_translation(r, wall_fields) for r in insertions):
        raise ValueError("SHIFTED_PIER_FOOTPRINT_REQUIRES_SECTION_GEOMETRY")
    panel = panels[member]
    p, q = (points[panel[k]] for k in ("UniquePt1", "UniquePt2"))
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = hypot(dx, dy)
    if abs(length * 1000 - pier["length_mm"]) > 0.1 or p[2] != q[2]:
        raise ValueError("PIER_BASE_EDGE_ORIENTATION_UNRESOLVED")
    name = re.escape(pier["pier"])
    if bound["kind"] == METHOD:
        if not re.search(r'^\s*PIERNAME\s+"' + name + r'"[ \t\r]*$', bound["deck"], re.MULTILINE):
            raise ValueError("EXPLICIT_PIER_AXES_REQUIRE_NATIVE_SECTION_PROPERTIES")
    else:
        native = bound["properties"].get((pier["pier"], story), [])
        if len(native) != 1:
            raise ValueError("UNIQUE_PIER_SECTION_PROPERTIES_REQUIRED")
        row = native[0]
        angle = radians(float(row["AxisAngle"]))
        if (int(row["NumAreaObj"]) != 1 or int(row["NumLineObj"]) != 0
                or row["Material"] != pier["transverse_cage"]["concrete"]
                or abs((dx*sin(angle) - dy*cos(angle))/length) > 1e-5):
            raise ValueError("NATIVE_PIER_MEMBERSHIP_MATERIAL_OR_STRONG_AXIS_DIFFERS")
        for face, edge in (("Bot", (p, q)), ("Top", (points[panel["UniquePt3"]], points[panel["UniquePt4"]]))):
            centroid = [(a+b)/2 for a, b in zip(*edge)]
            expected = {**{"CG"+face+k: v for k, v in zip("XYZ", centroid)},
                        "Width"+face: length, "Thick"+face: pier["thickness_mm"]/1000}
            if any(not isclose(float(row[k]), v, rel_tol=0, abs_tol=1e-4) for k, v in expected.items()):
                raise ValueError("NATIVE_PIER_CENTROID_OR_SECTION_DIFFERS")
    for line in bound["deck"].splitlines():
        if re.match(r"^\s*LINEASSIGN\s", line) and re.search(r'\bPIER\s+"' + re.escape(pier["pier"]) + '"', line):
            raise ValueError("PIER_INCLUDES_FRAME_OBJECT")
    clearances = []
    for col in columns:
        if col["Story"] != story:
            continue
        placement_row = frames[col["UniqueName"]]
        if placement_row["CardinalPt"] not in {"10 (Centroid)", "5 (Middle Center)"} or not _no_translation(placement_row, frame_fields):
            raise ValueError("SHIFTED_COLUMN_FOOTPRINT_REQUIRES_SECTION_GEOMETRY")
        a, b = (points[col[k]] for k in ("UniquePtI", "UniquePtJ"))
        if a[:2] != b[:2]:
            raise ValueError("INCLINED_COLUMN_OVERLAP_REQUIRES_PHYSICAL_SECTION")
        shape = shapes[frame_sections[col["UniqueName"]]]
        radius = hypot(float(shape["t2"]), float(shape["t3"])) / 2
        if not isfinite(radius) or radius <= 0:
            raise ValueError("PIER_COLUMN_FOOTPRINT_UNRESOLVED")
        vx, vy = a[0] - p[0], a[1] - p[1]
        t = max(0.0, min(1.0, (vx*dx + vy*dy) / length**2))
        clearances.append(hypot(vx - t*dx, vy - t*dy) - radius - pier["thickness_mm"]/2000)
    if clearances and min(clearances) <= 0:
        raise ValueError("PIER_COLUMN_FOOTPRINT_REQUIRES_COMPOSITE_SECTION")
    return min(clearances) if clearances else None


def _gravity_check(section, detail, forces):
    axial = -forces["P"]
    capacity = solver(section).assess(axial*1000, forces["M2"]*1e6, forces["M3"]*1e6, refine_crossing=True)
    ratio = capacity.get("utilization")
    if capacity["status"] == "AXIAL_ONLY_SCENARIO":
        ratio = capacity["axial_utilization"]
    vr = detail["vr_kn"]
    shear = abs(forces["V2"])
    failure = (shear > vr or shear > detail["solid_strut_limit_kn"]
               or capacity["status"] in {"EXCEEDS_SCENARIO_SURFACE", "OUTSIDE_SCENARIO_AXIAL_RANGE"})
    reason = capacity.get("reason")
    if not failure and shear > detail["coupled_strut_limit_kn"]:
        reason = "COUPLED_OR_SOLID_WALL_CLASSIFICATION_REQUIRED"
    refinement = capacity.get("refinement") or {}
    return {"status": "NUMERICAL_EXCEEDANCE" if failure else "HOLD" if reason or ratio is None else "GRAVITY_CUT_CALCULATED",
            "forces_kn_knm": forces, "compression_kn": axial, "pmm_status": capacity["status"],
            "capacity_refinement": refinement.get("status"), "local_refinement": refinement.get("local_crossing"),
            "reason": reason, "pmm_ratio": ratio, "radial_capacity_knm": capacity["radial_capacity_kNm"],
            "axial_range_kn": capacity["axial_range_kN"], "v2_over_vr": shear / vr,
            "v2_over_solid_strut": shear / detail["solid_strut_limit_kn"],
            "v2_over_coupled_strut": shear / detail["coupled_strut_limit_kn"]}


def wall_sections(source, stages, boundaries):
    plan = (stages.get("column_axial") or {}).get("combination_plan") or {}
    assigned = (plan.get("design_assignment") or {}).get("groups", {}).get("gravity", [])
    static = {x["name"] for x in plan.get("combinations", []) if x.get("classification") == "STATIC_LINEAR_ADD"}
    roles = (stages.get("analysis_setup_reconciliation") or {}).get("assigned_design_families") or {}
    seismic = (roles.get("project_role_catalog") or {}).get("available_groups", {}).get("wall", [])
    scope = {"native_static": {}, "native_seismic": {}, "controls": {}, "other": []}
    if boundaries["piers"]:
        try:
            scope = wall_load_scope(source)
        except (KeyError, TypeError, ValueError):
            pass
    if (source.get("pier_section_forces") or {}).get("kind") != METHOD:
        assigned = sorted(scope["native_static"])
        static = set(assigned)
    source_error = None
    try:
        bound = bound_pier_forces(source, assigned)
    except (KeyError, TypeError, ValueError) as exc:
        bound, source_error = {}, str(exc)
    result = {"basis": bound.get("kind"), "model_sha256": bound.get("model_sha256"),
              "solution_reference": bound.get("solution_reference"), "source_reason": source_error,
              "gravity_combinations": assigned, "wall_seismic_combinations": seismic, "piers": [],
              "native_wall_static": sorted(scope["native_static"]), "native_wall_seismic": sorted(scope["native_seismic"]),
              "other_wall_strength_assignments": scope["other"],
              "expected_gravity": 0, "evaluated_gravity": 0, "gravity_exceedances": 0,
              "expected_seismic": 0, "observed_seismic_envelopes": 0, "evaluated_seismic_design": 0,
              "expected_shear_bounds": 0, "evaluated_shear_bounds": 0, "satisfied_shear_bounds": 0,
              "expected_height_cuts": 0, "evaluated_height_cuts": 0, "evaluated_height_shear": 0, "satisfied_height_shear": 0,
              "evaluated_axial": 0, "evaluated_pmm_boxes": 0, "satisfied_pmm_boxes": 0, "satisfied_sections": 0,
              "expected_joints": 0, "evaluated_joints": 0, "satisfied_joints": 0,
              "expected_detail_panels": 0, "evaluated_detail_panels": 0,
              "satisfied_detail_panels": 0, "axial_limit_exceedances": 0,
              "conditional_seismic_sections": 0, "conditional_piers": 0,
              "expected_strong_wall": 0, "evaluated_strong_wall": 0, "satisfied_strong_wall": 0,
              "design_basis": {"reinforcement": "PROPOSED_CONSTANT_WEB_AND_BOUNDARY_CAGES",
                  "axial": "NATIVE_ASSIGNED_COMBINATIONS_WITH_MODEL_LIVE_LOAD",
                  "moment": "TBDY_7_6_6_1_TWO_BASE_SCENARIOS_AND_LOCAL_FACE_ENVELOPE",
                  "shear": "TBDY_FIG_7_12C_PIECEWISE_LINEAR_WITHIN_EACH_PANEL",
                  "joint_friction": "ROUGHENED_AT_LEAST_5_MM_ANCHORED_PERPENDICULAR_BARS_IN_PLANE",
                  "beam_strength": "SELECTED_RECTANGULAR_BEAM_ENDS_AT_ZERO_AXIAL_BOTH_SIGNS"},
              "seismic_design_reason": "PROJECT_BASE_LOAD_POLICY_AND_REINFORCEMENT_DEVELOPMENT_REQUIRED"}
    objects = {row["member_id"]: row for row in boundaries["walls"]}
    for pier in boundaries["piers"]:
        name, members = pier["pier"], pier["member_ids"]
        record = {"pier": name, "gravity_rows": [], "seismic_envelopes": [], "seismic_shear": [], "members": members}
        result["piers"].append(record)
        result["expected_gravity"] += 2 * len(members) * len(assigned)
        result["expected_seismic"] += 2 * len(members) * len(seismic)
        result["expected_shear_bounds"] += 2 * len(members) * len(scope["native_seismic"])
        try:
            section, record["reinforcement"] = reinforced_section(pier, source["column_axial"])
        except (KeyError, TypeError, ValueError) as exc:
            section = None
            record["cage_reason"] = str(exc)
        for member in members:
            story = objects[member]["story"]
            reason = source_error or record.get("cage_reason")
            if not reason:
                try:
                    if bound["assignments"].get((name, story)) != [member]:
                        raise ValueError("PIER_ASSIGNMENT_INCLUDES_OTHER_OBJECTS_OR_IS_MISSING")
                    clearance = _isolated_panel(member, story, source, bound, pier)
                    record.setdefault("column_footprint_clearance_lower_bound_m", {})[member] = clearance
                except (KeyError, TypeError, ValueError) as exc:
                    reason = str(exc)
            for face in ("Bottom", "Top"):
                for combo in assigned:
                    row = {"member": member, "story": story, "face": face, "combination": combo, "status": "HOLD"}
                    record["gravity_rows"].append(row)
                    if reason or combo not in static:
                        row["reason"] = reason or "SIGNED_STATIC_COMBINATION_REQUIRED"
                        continue
                    case = bound["cases"][combo]
                    row.update(output_case=case, step="Final Step 1" if bound["kind"] == METHOD else "Static")
                    try:
                        forces = signed_vector(bound["groups"][name, story, face, case], bound["kind"])
                        row.update(_gravity_check(section, record["reinforcement"], forces))
                    except (KeyError, TypeError, ValueError) as exc:
                        row["reason"] = str(exc)
                    result["evaluated_gravity"] += row["status"] != "HOLD"
                    result["gravity_exceedances"] += row["status"] == "NUMERICAL_EXCEEDANCE"
                if not reason and bound["kind"] == ORIGINAL:
                    key = (name, story, face)
                    for combo in seismic:
                        try:
                            bounds = envelope(bound["groups"][*key, combo])
                        except (KeyError, TypeError, ValueError):
                            continue
                        record["seismic_envelopes"].append({"member": member, "story": story, "face": face,
                            "combination": combo, "scalar_bounds_kn_knm": bounds})
                        result["observed_seismic_envelopes"] += 1
                    try:
                        edz = vertical_component(scope, bound["groups"], key)
                    except (KeyError, TypeError, ValueError) as exc:
                        edz, reason_z = None, str(exc)
                    for combo in scope["native_seismic"]:
                        row = {"member": member, "story": story, "face": face, "combination": combo, "status": "HOLD"}
                        record["seismic_shear"].append(row)
                        try:
                            if edz is None:
                                raise ValueError(reason_z)
                            row.update(upper_shear(scope, combo, bound["groups"], key, seismic, record["reinforcement"], edz))
                            result["evaluated_shear_bounds"] += 1
                            result["satisfied_shear_bounds"] += row["status"] == "SHEAR_BOUND_SATISFIED"
                        except (KeyError, TypeError, ValueError) as exc:
                            row["reason"] = str(exc)
        if (source.get("pier_section_forces") or {}).get("kind") != METHOD:
            combos = scope["native_seismic"]
            result["expected_height_cuts"] += 2*len(members)*len(combos)
            result["expected_joints"] += len(members)*len(combos)
            result["expected_detail_panels"] += len(members)
            designs, panels, joints = pier_design_checks(pier, objects, section, record.get("reinforcement"), bound,
                combos, record["seismic_shear"], record.get("column_footprint_clearance_lower_bound_m", {}))
            record.update(seismic_sections=designs, panel_details=panels, construction_joints=joints)
            connections = strong_wall_checks(source, stages, pier, section, panels, designs, combos)
            record["strong_wall_connections"] = connections
            panel_map = {p["member"]: p for p in panels}
            interfaces = {(j.get("z_m"), j["combination"]): j for j in joints}
            by_floor = {(c.get("z_m"), c["combination"]): c for c in connections}
            for r in designs:
                z, case = r.get("z_m"), r["combination"]
                panel = panel_map[r["member"]]
                required = {"section": r["status"] == "SECTION_BOUND_SATISFIED",
                            "dimensions": panel.get("dimensions", {}).get("status") == "DIMENSIONS_SATISFIED",
                            "web_ties": panel.get("web_crossties", {}).get("status") == "WEB_CROSSTIES_CALCULATED"}
                if z != pier["top_z_m"]:
                    required["horizontal_joint"] = interfaces.get((z, case), {}).get("status") == "ROUGH_JOINT_BOUND_SATISFIED"
                if z != pier["bottom_z_m"]:
                    required["strong_wall"] = by_floor.get((z, case), {}).get("status") == "STRONG_WALL_BOUND_SATISFIED"
                r["open_section_checks"] = [k for k, meets in required.items() if not meets]
                r["chain_status"] = "CONDITIONAL_SECTION_DESIGN" if all(required.values()) else "SECTION_DESIGN_OPEN"
            record["conditional_section_count"] = sum(r["chain_status"] == "CONDITIONAL_SECTION_DESIGN" for r in designs)
            result["conditional_seismic_sections"] += record["conditional_section_count"]
            result["conditional_piers"] += bool(designs) and record["conditional_section_count"] == 2*len(members)*len(combos)
            result["expected_strong_wall"] += len(members)*len(combos)
            result["evaluated_strong_wall"] += sum("upper_utilization" in r for r in connections)
            result["satisfied_strong_wall"] += sum(r["status"] == "STRONG_WALL_BOUND_SATISFIED" for r in connections)
            result["evaluated_axial"] += sum("axial_ratio" in r for r in designs)
            result["axial_limit_exceedances"] += sum(r.get("axial_ratio", 0) > 1 for r in designs)
            result["evaluated_height_cuts"] += sum("height_branches" in r for r in designs)
            result["evaluated_height_shear"] += sum("shear_upper_ratio" in r for r in designs)
            result["satisfied_height_shear"] += sum(r.get("shear_upper_ratio", 2) <= 1 for r in designs)
            result["evaluated_pmm_boxes"] += sum((r.get("pmm") or {}).get("upper_utilization") is not None for r in designs)
            result["satisfied_pmm_boxes"] += sum((r.get("pmm") or {}).get("status") == "PMM_BOX_SATISFIED" for r in designs)
            result["satisfied_sections"] += sum(r["status"] == "SECTION_BOUND_SATISFIED" for r in designs)
            result["evaluated_joints"] += sum("upper_utilization" in j for j in joints)
            result["satisfied_joints"] += sum(j["status"] == "ROUGH_JOINT_BOUND_SATISFIED" for j in joints)
            result["evaluated_detail_panels"] += sum(p["status"] == "PANEL_CALCULATED" for p in panels)
            result["satisfied_detail_panels"] += sum(p.get("dimensions", {}).get("status") == "DIMENSIONS_SATISFIED"
                and p.get("web_crossties", {}).get("status") == "WEB_CROSSTIES_CALCULATED" for p in panels)
        shear_rows = [r for r in record["seismic_shear"] if r.get("upper_utilization") is not None]
        record["governing_seismic_shear"] = max(shear_rows, key=lambda r: r["upper_utilization"]) if shear_rows else None
        for field in ("pmm_ratio", "v2_over_vr"):
            values = [row for row in record["gravity_rows"] if row.get(field) is not None]
            record["governing_" + field] = max(values, key=lambda row: row[field]) if values else None
    return result
