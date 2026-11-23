"""One building-wide wall calculation organised by physical pier, storey and face."""
from collections import defaultdict
from math import hypot, isclose, isfinite, pi, sqrt

from .basement_pier_design import _material
from .basement_pier_geometry import _column_footprints, _context, cut_web_area, pier_membership
from .pier_force_source import ORIGINAL, signed_vector
from .pier_height_design import joint_friction
from .pier_seismic_shear import envelope
from .column_r10_live import _materials_fck
from .wall_boundary import _catalog_proposal
from .wall_overturning import directional_model, pier_moments, storey_reference


def _source_cut(bound, key, static):
    rows = bound["groups"][key]
    if static:
        vec = signed_vector(rows, ORIGINAL)
        low, high = vec, vec
    else:
        bounds = envelope(rows)
        low, high = bounds["Min"], bounds["Max"]
    return {"compression_kn": max(0., -low["P"]), "tension_kn": max(0., high["P"]),
            "abs_v2_kn": max(abs(low["V2"]), abs(high["V2"])),
            "abs_v3_kn": max(abs(low["V3"]), abs(high["V3"])),
            "axial_interval_kn": [-high["P"], -low["P"]],
            "force_basis": "SIGNED_STATIC" if static else "COMPONENT_ENVELOPE"}


def _reference_friction(cut, area, material):
    # Explicit reference proposal for a roughened horizontal plane and 0.75%
    # anchored bars. Selected-cage design uses its own actual bars and design Ve.
    mat, fyk = material
    ac = area["net_m2"]*1e6
    detail = {"ach_mm2": ac, "fck_mpa": mat.fck, "fcd_mpa": mat.fcd, "fctd_mpa": .35*sqrt(mat.fck)*mat.fcd/mat.fck,
              "fyk_mpa": fyk, "fyd_mpa": mat.fyd, "steel_area_mm2": .0075*ac}
    shear = hypot(cut["abs_v2_kn"], cut["abs_v3_kn"])
    fr = joint_friction(detail, shear, cut["tension_kn"])
    return {"reference_plane_shear_kn": shear, "reference_friction": fr}


def _reference_web(cut, area, material, angle):
    """In-plane resultant check on parallel web concrete with two proposed Ø12/200 curtains."""
    if not isfinite(angle) or not isclose(angle/90, round(angle/90), abs_tol=1e-7, rel_tol=0):
        raise ValueError("DIRECTIONAL_SHEAR_WEB_REQUIRES_ALIGNED_PIER")
    axis = "X" if round(angle/90) % 2 == 0 else "Y"
    web = area["directional_webs"][axis]
    mat, _ = material
    ac = web["net_m2"]*1e6
    rho = 2*(pi*12**2/4)/(200*web["maximum_thickness_m"]*1000)
    vr = ac*(.65*.35*sqrt(mat.fck)*mat.fcd/mat.fck + rho*mat.fyd)/1000
    solid, coupled = (.85*ac*sqrt(mat.fck)/1000, .65*ac*sqrt(mat.fck)/1000)
    return {"axis": axis, "web_area_m2": web["net_m2"], "rho_h": rho, "vr_kn": vr,
            "solid_limit_kn": solid, "coupled_limit_kn": coupled,
            "source_v2_ratio": cut["abs_v2_kn"]/min(vr, solid, coupled)}


def _governing(rows, field, nested=None):
    values = []
    for row in rows:
        value = (row.get(nested) or {}).get(field) if nested else row.get(field)
        if isinstance(value, (int,float)) and isfinite(value):
            values.append((value, row))
    if not values:
        return None
    maximum, row = max(values, key=lambda item: item[0])
    return {"ratio": maximum, "combination": row.get("combination"), "face": row.get("face"), "evaluated": len(values)}


def _design_summary(row, sections, basement):
    pier, story = row["pier"], row["story"]
    rect = next((r for r in sections["piers"] if r["pier"] == pier), {})
    cuts = [r for r in rect.get("seismic_sections", []) if r["story"] == story]
    joints = [r for r in rect.get("construction_joints", []) if r["story"] == story]
    connections = [r for r in rect.get("strong_wall_connections", []) if r["story"] == story]
    panels = [r for r in rect.get("panel_details", []) if r["story"] == story]
    out = {"axial": _governing(cuts, "axial_ratio"), "shear": _governing(cuts, "shear_upper_ratio"),
           "horizontal_joint": _governing(joints, "upper_utilization"), "pmm": _governing(cuts, "upper_utilization", "pmm"),
           "wall_beam": _governing(connections, "upper_utilization"), "scheduled_panels": sum(
               p.get("web_crossties",{}).get("status") == "WEB_CROSSTIES_CALCULATED" and
               p.get("dimensions",{}).get("status") == "DIMENSIONS_SATISFIED" for p in panels),
           "conditional_faces": sum(r.get("chain_status") == "CONDITIONAL_SECTION_DESIGN" for r in cuts),
           "expected_faces": len(cuts), "panel_count": len(row["members"])}
    if basement:
        webs = basement.get("geometry", {}).get("panels", [])
        out.update(pmm=_governing([r for r in basement["cuts"] if r["role"] == "WALL_STRENGTH"], "pmm_upper"),
                   scheduled_panels=sum("vertical" in p and "horizontal" in p for p in webs),
                   pressure_ends_checked=sum(len(p.get("pressure_connections",{}).get("ends",{})) for p in webs),
                   pressure_ends_satisfied=sum(e["status"] == "CONDITIONAL_PRESSURE_END_DESIGN" for p in webs
                       for e in p.get("pressure_connections",{}).get("ends",{}).values()))
        out["reason"] = basement.get("reason") or "MULTIPANEL_IN_PLANE_SHEAR_DISTRIBUTION_AND_HORIZONTAL_JOINT_DETAIL_REQUIRED"
    elif not cuts:
        out["reason"] = row.get("reason") or "PIER_SECTION_AND_CAGE_REQUIRED"
    elif out["conditional_faces"] < len(cuts):
        out["reason"] = next((r.get("reason") or ", ".join(r.get("open_section_checks",[]))
                              for r in cuts if r.get("chain_status") != "CONDITIONAL_SECTION_DESIGN"), None) or "SECTION_CHAIN_INCOMPLETE"
    return out


def _cut_rows(row, face, combos, bound, area, fck, material, angle):
    rows = []
    for name, role in combos.items():
        rec = {"face": face, "combination": name, "role": role}
        rows.append(rec)
        try:
            rec.update(_source_cut(bound, (row["pier"], row["story"], face, name), role == "ASSIGNED_STATIC"))
            if area and fck and isfinite(fck) and fck > 0:
                limit = .35 * area["net_m2"] * fck * 1000
                rec.update(axial_limit_kn=limit, axial_ratio=rec["compression_kn"]/limit)
            if area and material:
                rec.update(_reference_friction(rec, area, material))
                rec["reference_web"] = _reference_web(rec, area, material, angle)
        except (KeyError, TypeError, ValueError) as exc:
            rec["reason"] = str(exc)
    return rows


def wall_batch(source, stages, boundaries, sections, bound, scope):
    """Preserve the physical population even when inputs for individual checks are missing."""
    physical = defaultdict(list)
    for wall in boundaries["walls"]:
        physical[wall.get("pier"), wall["story"], None if wall.get("pier") else wall["member_id"]].append(wall)
    combos = {k: "ASSIGNED_STATIC" for k in scope["native_static"]}
    combos.update({k: "ASSIGNED_SEISMIC" for k in scope["native_seismic"]})
    combos.update({k: "ASSIGNED_OTHER" for k in scope["other"] if k not in combos})
    for c in scope["controls"].values():
        if c.get("combination"):
            combos.setdefault(c["combination"], "AMPLIFIED_CONTROL")
    groups = {(p["pier"], p["story"]): p for p in sections["basement_piers"]}
    try:
        context = _context(source)
    except (KeyError, ValueError, TypeError):
        context = None
    try:
        model = directional_model(source, scope)
        model_reason = None
    except (KeyError, ValueError, TypeError) as exc:
        model, model_reason = None, str(exc)
    strengths = _materials_fck(stages.get("extra"))
    rows = []
    for (pier, story, _), walls in sorted(physical.items(), key=lambda kv: tuple(str(v or "~") for v in kv[0])):
        ids = sorted(w["member_id"] for w in walls)
        row = {"pier": pier, "story": story, "members": ids, "wall_labels": [w.get("label") for w in walls],
               "faces": {}, "cuts": [], "overturning": {}}
        rows.append(row)
        try:
            if not pier:
                raise ValueError("PIER_ASSIGNMENT_REQUIRED")
            if bound.get("kind") != ORIGINAL:
                raise ValueError(sections.get("source_reason") or "ORIGINAL_PIER_TABLES_REQUIRED")
            native = pier_membership(bound, pier, story, ids)
        except (KeyError, TypeError, ValueError) as exc:
            row["reason"] = str(exc)
            row["design"] = _design_summary(row, sections, groups.get((pier,story)))
            continue
        try:
            if context is None:
                raise ValueError("PHYSICAL_WALL_FOOTPRINT_SOURCE_REQUIRED")
            columns, _ = _column_footprints(context, story)
            for face in ("Bottom","Top"):
                row["faces"][face] = cut_web_area(context, columns, native, ids, face)
        except (KeyError, TypeError, ValueError) as exc:
            row["area_reason"] = str(exc)
        try:
            mat, _ = _material(source, stages, native["Material"])
            material = mat, _catalog_proposal(source)["fywk_mpa"]
        except (KeyError, TypeError, ValueError) as exc:
            material = None
            row["material_reason"] = str(exc)
        for face in ("Bottom", "Top"):
            row["cuts"].extend(_cut_rows(row, face, combos, bound, row["faces"].get(face), strengths.get(native["Material"]),
                                       material, float(native["AxisAngle"])))
        try:
            if not model:
                raise ValueError(model_reason)
            row["overturning"] = pier_moments(model, bound["groups"], pier, story, native)
        except (KeyError, TypeError, ValueError) as exc:
            row["overturning_reason"] = str(exc)
        row["native_bottom_z_m"] = float(native["CGBotZ"])
        row["design"] = _design_summary(row, sections, groups.get((pier,story)))
        assigned_rows = [c for c in row["cuts"] if c["role"].startswith("ASSIGNED_")]
        row["assigned"] = {"axial": _governing(assigned_rows, "axial_ratio"),
                           "web": _governing(assigned_rows, "source_v2_ratio", "reference_web"),
                           "friction": _governing(assigned_rows, "upper_utilization", "reference_friction")}
    references = []
    for story in sorted({r["story"] for r in rows}):
        at_level = [r for r in rows if r["story"] == story]
        for direction in ("X","Y"):
            moments = [r["overturning"][direction] for r in at_level if direction in r["overturning"]]
            ref = {"story": story, "direction": direction, "expected_groups": len(at_level), "evaluated_groups": len(moments)}
            references.append(ref)
            if not moments:
                ref["reason"] = model_reason or "DIRECTIONAL_PIER_MOMENTS_REQUIRED"
                continue
            ref["case"] = moments[0]["case"]
            try:
                ref["storey_moment_knm"] = storey_reference(source, story, direction, ref["case"])
            except (KeyError, TypeError, ValueError) as exc:
                ref["reason"] = str(exc)
            ref["project_status"] = "HOLD"
            ref["project_reason"] = "PROJECT_BASE_WALL_POPULATION_COUPLING_AND_MODAL_WALL_TOTAL_REQUIRED"
    named = [r for r in rows if r["pier"]]
    assigned = [c for r in named for c in r["cuts"] if c["role"].startswith("ASSIGNED_")]
    design = [r["design"] for r in named]
    counts = {"physical_walls": len(boundaries["walls"]), "pier_storeys": len(named), "unassigned_walls": len(rows)-len(named),
              "assigned_combinations": sum(role.startswith("ASSIGNED_") for role in combos.values()),
              "assigned_face_checks_expected": len(named)*2*sum(role.startswith("ASSIGNED_") for role in combos.values()),
              "native_assigned_faces": sum("compression_kn" in c for c in assigned),
              "net_area_axial_faces": sum("axial_ratio" in c for c in assigned),
              "net_area_axial_exceedances": sum(c.get("axial_ratio", 0) > 1 for c in assigned),
              "reference_friction_faces": sum("reference_friction" in c for c in assigned),
              "reference_friction_inconclusive": sum(c["reference_friction"]["status"] != "ROUGH_JOINT_BOUND_SATISFIED"
                                                     for c in assigned if "reference_friction" in c),
              "reference_web_shear_faces": sum("reference_web" in c for c in assigned),
              "reference_web_shear_over_limit": sum(c["reference_web"]["source_v2_ratio"] > 1
                                                    for c in assigned if "reference_web" in c),
              "directional_moments": sum(len(r["overturning"]) for r in named),
              "design_axial_storeys": sum(d["axial"] is not None for d in design),
              "design_shear_storeys": sum(d["shear"] is not None for d in design),
              "design_friction_storeys": sum(d["horizontal_joint"] is not None for d in design),
              "design_pmm_storeys": sum(d["pmm"] is not None for d in design),
              "scheduled_panels": sum(d["scheduled_panels"] for d in design),
              "complete_rectangular_stacks": sections["conditional_piers"]}
    return {"schema": "tbdy.next.wall-batch.v1", "counts": counts, "rows": rows, "overturning_storeys": references,
            "combinations": combos, "reference_web": {"curtains": 2, "horizontal_diameter_mm": 12, "pitch_mm": 200},
            "reference_joint": {"vertical_steel_ratio": .0075, "mu": 1.,
             "assumptions": "Anchored perpendicular bars, roughness at least 5 mm, zero compression credit, net direct tension reserved."},
            "source_model_sha256": bound.get("model_sha256"), "solution_reference": bound.get("solution_reference")}
