"""TBDY 7.6.2/7.6.5 boundary minima for continuous, rectangular ETABS pier stacks."""
from collections import defaultdict
from hashlib import sha256
from math import ceil, floor, pi
import re

from ..column_engine.section_capacity import perimeter
from ..column_engine.transverse_kernel import bar_area_mm2, confinement_reference
from .analysis_archive import _archive_bytes
from .beam_r10_live import _steel_grade_mpa
from .column_clear_length import _index, _records
from .column_r10_live import _materials_fck
from .confinement_regions import _hook
from .rebar_selection import _min_crosstie_legs_for_face


def _section_minima(length, thickness):
    area = length * thickness
    bar_area = pi * 14 ** 2 / 4
    result = {}
    for zone, width, ratio in (("critical", max(0.2 * length, 2 * thickness), 0.002),
                               ("above_critical", max(0.1 * length, thickness), 0.001)):
        required = max(4 * bar_area, ratio * area)
        # Symmetric two-face proposal, using the clause's reference bar size.
        bars = 2 * ceil(required / (2 * bar_area))
        result[zone] = {"end_width_mm": width, "minimum_as_per_end_mm2": required,
                        "bars_per_end": bars, "diameter_mm": 14, "provided_as_per_end_mm2": bars * bar_area,
                        "maximum_unspliced_as_per_end_mm2": 0.03 * width * thickness,
                        "pitch_limit_mm": min(150, 6 * 14, thickness / 3) if zone == "critical"
                        else min(thickness, 200)}
    return result


def _catalog_proposal(source):
    """Use the unique grade and cover of the active column sections as an explicit wall proposal."""
    geometry = (source.get("vs06_b1_geometry_source") or {}).get("table_reads", {})
    steel = ((source.get("column_axial") or {}).get("pmm_section_source") or {})
    try:
        sections = _index(_records(geometry, "Frame Assignments - Section Properties",
                                   "UniqueName SectProp"), "UniqueName")
        columns = _records(geometry, "Column Object Connectivity", "UniqueName")
        props = _index(_records(steel["table_reads"], "Frame Section Property Definitions - Concrete Column Reinforcing",
                                "Name Cover RebarMatC", ("Cover",)), "Name")
        used = {sections[c["UniqueName"]]["SectProp"] for c in columns}
        (grade, cover), = {(props[name]["RebarMatC"], float(props[name]["Cover"]) * 1000) for name in used}
        fy, _ = _steel_grade_mpa(steel, grade)
        if cover > 0 and fy and fy > 0:
            return {"grade": grade, "fywk_mpa": fy, "cover_mm": cover,
                    "proposal_basis": "ADOPTED_FROM_ACTIVE_COLUMN_SECTIONS", "source_column_sections": sorted(used)}
    except (KeyError, TypeError, ValueError):
        pass
    return None


def _boundary_cage(section, fck, material):
    detail = section["adopted_constant_detail"]
    u, v = detail["end_width_mm"], section["thickness_mm"]
    cover, tie, long_d = material["cover_mm"], 10, detail["diameter_mm"]
    spacing = 10 * floor(detail["pitch_limit_mm"] / 10)
    if spacing < 50 or min(u, v) <= 2 * (cover + tie + long_d / 2):
        raise ValueError("BOUNDARY_HOOP_OR_LONGITUDINAL_CAGE_DOES_NOT_FIT")
    # One closed hoop and interior crossties. Every tie line engages a perimeter bar.
    n_v = max(2, 1 + ceil((v - 2 * cover) / (25 * tie)))
    n_u = max(2, detail["bars_per_end"] // 2 - n_v + 2)
    bars, _, clear = perimeter(u, v, cover, tie, long_d, n2=n_u, n3=n_v)
    if len(bars) != detail["bars_per_end"] or clear < max(40, 1.5 * long_d):
        raise ValueError("BOUNDARY_LONGITUDINAL_GRID_REQUIRES_RESELECTION")
    directions = {}
    for direction, across, stations in (("along_wall", v, n_v), ("across_wall", u, n_u)):
        geometric_legs, _ = _min_crosstie_legs_for_face(face_extent_mm=across, cover_mm=cover,
                                                        tie_mm=tie, n_bars=stations)
        bk = across - 2 * cover - tie
        area = bar_area_mm2(tie)
        reference = confinement_reference(area_mm2=u*v, core_area_mm2=(u-2*cover)*(v-2*cover),
                                          bk_mm=bk, spacing_mm=spacing, fck_mpa=fck,
                                          fywk_mpa=material["fywk_mpa"], ash_mm2=geometric_legs * area)
        required = (2 / 3) * reference["eq71_b_mm2"]
        legs = max(geometric_legs, ceil(required / area))
        if legs > stations:
            raise ValueError("BOUNDARY_TIE_LINES_NEED_MORE_LONGITUDINAL_BARS")
        indices = [round(i * (stations-1) / (legs-1)) for i in range(legs)]
        # The perimeter-bar pitch and the outer-hoop centreline pitch differ at the corners.
        pitch = (across - 2 * (cover + tie + long_d / 2)) / (stations-1)
        lines = [cover + tie + long_d/2 + i * pitch for i in indices]
        lines[0], lines[-1] = cover + tie/2, across - cover - tie/2
        max_gap = max(b-a for a, b in zip(lines, lines[1:]))
        if max_gap > 25 * tie:
            raise ValueError("BOUNDARY_TIE_LINE_SPACING_EXCEEDS_25_DIAMETERS")
        directions[direction] = {"legs": legs, "core_bk_mm": bk, "required_ash_mm2": required,
                                 "provided_ash_mm2": legs * area, "utilization": required / (legs * area),
                                 "bar_indices": indices, "tie_line_distances_mm": lines,
                                 "largest_leg_gap_mm": max_gap}
    return {**material, "fck_mpa": fck, "tie_diameter_mm": tie, "spacing_mm": spacing,
            "longitudinal_grid_u_v": [n_u, n_v], "minimum_longitudinal_clear_spacing_mm": clear,
            "directions": directions, "hook": _hook(tie), "status": "CONDITIONAL_TRANSVERSE_CAGE_CALCULATED"}


def _stack(panels):
    # A shared native edge tests continuity independently of a repeated pier label.
    panels = sorted(panels, key=lambda p: p["bottom_z_m"])
    example = panels[0]
    if len(panels) < 2:
        raise ValueError("CONTINUOUS_PIER_HEIGHT_AND_BASE_REQUIRED")
    for lower, upper in zip(panels, panels[1:]):
        if lower["top_z_m"] > upper["bottom_z_m"]:
            raise ValueError("MULTIPLE_WALL_PANELS_AT_SAME_ELEVATION")
        if lower["top_z_m"] < upper["bottom_z_m"]:
            raise ValueError("VERTICAL_GAP_BETWEEN_WALL_PANELS")
        if lower["thickness_mm"] != upper["thickness_mm"]:
            raise ValueError("STACKED_WALL_PANEL_THICKNESS_CHANGES")
        if lower["outline"] != upper["outline"]:
            raise ValueError("STACKED_WALL_PANEL_PLAN_OUTLINE_CHANGES")
        if lower["upper_edge"] != upper["lower_edge"]:
            raise ValueError("STACKED_WALL_PANEL_EDGE_IDS_DIFFER")
    length, thickness = example["length_mm"], example["thickness_mm"]
    bottom, top = example["bottom_z_m"], panels[-1]["top_z_m"]
    branches = {}
    # The alternatives explicitly identify the modelling assumption about the basement.
    for name, base in (("LOWEST_MODELLED_WALL_BASE", bottom),
                       ("RIGID_FIRST_BASEMENT_SCENARIO", example["top_z_m"])):
        height = (top - base) * 1000
        slender = height > 2 * length
        branch = {"reference_z_m": base, "wall_height_mm": height, "hw_over_lw": height / length,
                  "ends_required": slender}
        if slender:
            hcr = max(length, height / 6)
            if hcr > 2 * length:
                raise ValueError("CRITICAL_HEIGHT_LOWER_AND_UPPER_LIMITS_REQUIRE_REVIEW")
            branch.update(minimum_hcr_mm=hcr, critical_interval_z_m=[bottom, min(top, base + hcr / 1000)])
        branches[name] = branch
    if not any(b["ends_required"] for b in branches.values()):
        raise ValueError("NO_SLENDER_BRANCH_IN_MODELLED_BASE_SCENARIOS")
    minima = _section_minima(length, thickness)
    adopted = minima["critical"]
    if 2 * adopted["end_width_mm"] > length or adopted["pitch_limit_mm"] < 50:
        raise ValueError("DISTINCT_BOUNDARY_ZONES_OR_MINIMUM_TIE_PITCH_INFEASIBLE")
    if adopted["provided_as_per_end_mm2"] > adopted["maximum_unspliced_as_per_end_mm2"]:
        raise ValueError("PROPOSED_BOUNDARY_STEEL_EXCEEDS_MAXIMUM")
    return {"bottom_z_m": bottom, "top_z_m": top, "length_mm": length, "thickness_mm": thickness,
            "height_branches": branches, "section_minima": minima, "adopted_constant_detail": adopted,
            "foundation_tie_continuation_min_mm": max(300, thickness)}


_ASSIGN = re.compile(r'^\s*AREAASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+(.*)$')


def wall_boundaries(source, stages, evidence, wall_inventory):
    rows = {uid: {"member_id": uid, "label": obj["Label"], "story": obj["Story"], "status": "HOLD",
                  "reason": "PIER_ASSIGNMENT_AND_RECONCILED_RECTANGULAR_PANEL_REQUIRED"}
            for uid, obj in (wall_inventory or {}).items()}
    result = {"walls": list(rows.values()), "piers": [],
              "scope": "Rectangular in-web end zones, high ductility. The proposal retains the critical width, "
                       "longitudinal bars and transverse steel over the entire stack. Cover and tie steel are a design proposal. "
                       "Signed section demands are evaluated in the pier section results. Anchorage and construction fit require detailing."}
    record = source.get("analysis_archive") or {}
    matched = (stages.get("analysis_setup_reconciliation") or {}).get("archived_analysis_order") or {}
    if matched.get("status") != "ARCHIVED_SOLVER_FIRST_ORDER_MATCHED" or not rows:
        return result
    try:
        data = _archive_bytes(record.get("model_export_base64"), 2_000_000)
    except ValueError:
        return result
    if sha256(data).hexdigest() != matched.get("model_export_sha256"):
        return result
    assign = defaultdict(list)
    for line in data.decode("latin-1").splitlines():
        match = _ASSIGN.match(line)
        if match:
            label, story, fields = match.groups()
            assign[story, label].append(fields)
    geometry = (source.get("vs06_b1_geometry_source") or {}).get("table_reads", {})
    coords = {r["UniqueName"]: r for r in (geometry.get("Point Object Connectivity") or {}).get("rows", [])}
    verified = {r["element_id"]: r for r in (evidence.get("wall_geometry") or {}).get("items", [])}
    groups = defaultdict(list)
    for uid, row in rows.items():
        fields = assign[row["story"], row["label"]]
        if len(fields) != 1:
            # An unlocated or ambiguous assignment can hide another member of any stack.
            return result
        names = re.findall(r'\bPIER\s+"([^"]+)"', fields[0])
        if len(names) > 1:
            return result
        if not names:
            continue
        row["pier"] = names[0]
        groups[names[0]].append(uid)
        if re.findall(r'\bSECTION\s+"([^"]+)"', fields[0]) != [wall_inventory[uid].get("SectProp")]:
            return result
    material = _catalog_proposal(source)
    strengths = _materials_fck(stages.get("extra"))
    for name, ids in sorted(groups.items()):
        panels = []
        try:
            for uid in ids:
                wall = verified.get(uid) or {}
                if wall.get("status") != "SOURCE_NUMERICAL" or wall.get("section") != wall_inventory[uid]["SectProp"]:
                    raise ValueError("RECONCILED_RECTANGULAR_PANEL_REQUIRED")
                corners = sorted(((float(coords[q]["Z"]), float(coords[q]["X"]), float(coords[q]["Y"]), q)
                                  for q in wall["point_ids"]))
                panels.append({"bottom_z_m": corners[0][0], "top_z_m": corners[-1][0],
                               "lower_edge": sorted(q[3] for q in corners[:2]),
                               "upper_edge": sorted(q[3] for q in corners[2:]),
                               "outline": [q[1:3] for q in corners[:2]],
                               "length_mm": float(wall["panel_length_m"]) * 1000,
                               "thickness_mm": float(wall["thickness_mm"])})
            section = _stack(panels)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            for uid in ids:
                rows[uid]["reason"] = str(exc)
            continue
        concretes = {verified[uid].get("material_name") for uid in ids}
        concrete = next(iter(concretes)) if len(concretes) == 1 else None
        cage = {"status": "HOLD", "reason": "UNIQUE_SOURCE_CONCRETE_AND_CATALOG_PROPOSAL_REQUIRED"}
        if material and strengths.get(concrete):
            try:
                cage = {**_boundary_cage(section, strengths[concrete], material), "concrete": concrete}
            except ValueError as exc:
                cage = {"status": "HOLD", "reason": str(exc)}
        result["piers"].append({"pier": name, "member_ids": ids, **section, "transverse_cage": cage})
        for uid in ids:
            rows[uid].update(status="BOUNDARY_MINIMA_CALCULATED", reason=None, cage_status=cage["status"])
    return result
