"""Development and vertical-interface shear for a basement wall under transverse pressure."""
from math import ceil, cos, isfinite, pi, radians, sin, sqrt

from ..column_engine.section_capacity import perimeter
from .basement_joint_layout import layout_policy, level_grid
from .basement_pier_geometry import required
from .basement_wall_pressure import CAGES, panel_pressure_design
from .column_pmm_section import COLUMN_REINFORCING, _named_row, _rows


def tension_development(diameter, fyd, fck, fcd, cover, clear_spacing):
    """TS 500 9.1.2(a), full-yield deformed straight bars. All lengths in mm."""
    required(all(isfinite(v) and v > 0 for v in (diameter, fyd, fck, fcd, cover, clear_spacing))
             and diameter <= 32, "STRAIGHT_DEFORMED_BAR_INPUT_OUTSIDE_SCOPE")
    fctd = .35*sqrt(fck)*fcd/fck
    basic = max(20*diameter, .12*diameter*fyd/fctd)
    splitting = 1.2 if cover < diameter or clear_spacing < 1.5*diameter else 1.
    return {"position_ii_mm": basic*splitting, "position_i_mm": 1.4*basic*splitting,
            "cover_spacing_factor": splitting, "fctd_mpa": fctd}


def support_profiles(source, stages, panel):
    capture = source["column_axial"]["pmm_section_source"]
    required(capture.get("model_locked_before") is True and capture.get("model_locked_after") is True
             and capture.get("units_before") == capture.get("units_after") == 6, "COLUMN_DETAIL_SOURCE_REQUIRED")
    rows = _rows(capture["table_reads"], COLUMN_REINFORCING, {"Name","NumBars2Dir","NumBars3Dir"}, {})
    profiles = {}
    for side, support in panel["support_sections"].items():
        name, uid = support["section"], support["column"]
        members = [r for r in stages["column_pmm"]["members"] if r.get("member_id") == uid]
        required(len(members) == 1 and members[0].get("section") == name, "COLUMN_SECTION_IDENTITY_REQUIRED")
        detail = members[0].get("section_evidence") or {}
        axial = [r for r in stages["column_axial"]["columns"] if r.get("element_id") == uid]
        required(len(axial) == 1 and axial[0].get("section") == name
                 and axial[0].get("material_name") == support["material"]
                 and axial[0].get("fck_mpa") == detail.get("fck_mpa") and axial[0].get("fcd_mpa") == detail.get("fcd_mpa"),
                 "COLUMN_MATERIAL_AND_SECTION_MISMATCH")
        counts = _named_row(rows, "Name", name, COLUMN_REINFORCING)
        bars, _, _ = perimeter(detail["t2_mm"], detail["t3_mm"], detail["cover_to_tie_mm"], detail["tie_diameter_mm"],
                               detail["longitudinal_bar_diameter_mm"], int(counts["NumBars2Dir"]), int(counts["NumBars3Dir"]))
        required(len(bars) == detail["bar_count"], "COLUMN_LONGITUDINAL_GRID_MISMATCH")
        # At zero rotation the native column local-2 axis is global X.
        angle = radians(support["axis_angle_deg"])
        dx, dy = panel["width_direction"]
        along_2, along_3 = dx*cos(angle)+dy*sin(angle), -dx*sin(angle)+dy*cos(angle)
        across_2, across_3 = -along_3, along_2
        depth = abs(along_2)*detail["t2_mm"] + abs(along_3)*detail["t3_mm"]
        required(abs(depth-support["depth_mm"]) < 1e-5, "COLUMN_DEPTH_AND_LAYOUT_AXES_DIFFER")
        profiles[side] = {**support, "role": detail["reinforcement_role"], "fck": detail["fck_mpa"],
            "fcd": detail["fcd_mpa"], "cover": detail["cover_to_tie_mm"], "tie": detail["tie_diameter_mm"],
            "bar_diameter": detail["longitudinal_bar_diameter_mm"],
            "bar_offsets": [b.x2*across_2 + b.x3*across_3 for b in bars]}
    return profiles


def _bar_clearance(profile, offset, diameter):
    centre_distance = min(abs(sign*offset-x) for sign in (-1,1) for x in profile["bar_offsets"])
    return centre_distance - (diameter + profile["bar_diameter"])/2


def _adjacent_web(geometry, panel, side, offset, diameter, cover):
    joint = panel["joint_"+side.lower()]
    for other in geometry["panels"]:
        if other["member"] == panel["member"] or joint not in (other["joint_i"],other["joint_j"]):
            continue
        dx, dy = panel["width_direction"]
        ex, ey = other["width_direction"]
        same_line = abs(dx*ex+dy*ey) > 1-1e-9
        fits = offset+diameter/2+cover <= other["thickness_m"]*500+1e-7
        return {"member": other["member"], "wall": other["wall"], "collinear": same_line,
                "clear_extension_mm": other["clear_length_m"]*1000-cover if same_line and fits else 0.}
    return {}


def _development(profiles, geometry, panel, grid, mat):
    dia, cover = grid["diameter_mm"], grid["cover_mm"]
    spacing = grid["pitch_mm"]-dia
    wall = tension_development(dia, mat.fyd, mat.fck, mat.fcd, cover, spacing)
    offset = 500*panel["thickness_m"]-cover-grid.get("curtain_inset_mm",0.)-1.5*dia
    ends = {}
    for side, prof in profiles.items():
        end_cover = max(cover, prof["cover"])
        # Stop before the inside of the far hoop. This also keeps its outer cover clear.
        available = prof["depth_mm"]-end_cover-prof["tie"]
        bond = tension_development(dia, mat.fyd, prof["fck"], prof["fcd"], end_cover, spacing)
        needed = bond["position_i_mm"]
        specified = 5*ceil(needed/5)
        clearance = _bar_clearance(prof, offset, dia)
        adjacent = _adjacent_web(geometry, panel, side, offset, dia, cover)
        corridor = prof["depth_mm"]+adjacent["clear_extension_mm"] if adjacent.get("clear_extension_mm",0)>0 else available
        ends[side] = {**bond, "column": prof["column"], "column_section": prof["section"], "column_role": prof["role"],
            "column_depth_mm": prof["depth_mm"], "end_cover_mm": end_cover, "far_hoop_mm": prof["tie"],
            "column_available_mm": available, "specified_embedment_mm": specified, "margin_mm": available-needed,
            "wall_side_available_mm": 500*panel["clear_length_m"], "wall_side_required_mm": wall["position_i_mm"],
            "template_longitudinal_clearance_mm": clearance, "adjacent_web": adjacent,
            "geometric_corridor_mm": corridor, "fits_column": specified <= available and clearance > 0
            and wall["position_i_mm"] <= 500*panel["clear_length_m"]}
    return ends


def _transfer(panel, profile, h, mat, policy):
    thickness = panel["thickness_m"]*1000
    peak = max(row["reaction_bound_kn_m"] for row in h["cuts"])
    # Two dedicated deformed bars per level, perpendicular to the joint and symmetric
    # about the web mid-plane. No pressure-flexural steel is counted as a dowel.
    choices = sorted(((d,p) for d in (10,12,14,16) for p in (200,125,100)), key=lambda pair: pair[0]**2/pair[1])
    cover = max(h["cover_mm"],profile["cover"])
    column_limit = profile["depth_mm"]-cover-profile["tie"]
    wall_limit = panel["clear_length_m"]*500
    cap = .2*min(mat.fcd,profile["fcd"],25.)*thickness
    offset = thickness/8
    for dia,pitch in choices:
        grid = level_grid(policy,dia,pitch,cover,dowel=True)
        if not grid:
            continue
        wall = tension_development(dia,mat.fyd,mat.fck,mat.fcd,cover,grid["clear_spacing_mm"])
        column = tension_development(dia,mat.fyd,profile["fck"],profile["fcd"],cover,grid["clear_spacing_mm"])
        steel = 2*grid["guaranteed_bars_per_m"]*pi*dia**2/4
        resistance = min(.6*steel*mat.fyd/1000, cap)
        wall_embed, col_embed = (5*ceil(dev["position_i_mm"]/5) for dev in (wall,column))
        # Keep the dowels between the two pressure curtains, clear of the column's modelled vertical bars.
        curtain_offset = thickness/2-h["cover_mm"]-h.get("curtain_inset_mm",0.)-1.5*h["diameter_mm"]
        clear = _bar_clearance(profile,offset,dia)
        if (peak <= resistance and wall_embed <= wall_limit and col_embed <= column_limit and clear > 0
                and curtain_offset-offset > (dia+h["diameter_mm"])/2 and grid["clear_spacing_mm"] >= max(25.,dia)):
            break
    else:
        return {"status":"HOLD", "reason":"NO_SEPARATE_FULLY_DEVELOPED_DOWEL_LAYOUT_IN_CATALOGUE",
                "peak_reaction_kn_m":peak, "concrete_limit_kn_m":cap}
    cuts = []
    for row in h["cuts"]:
        total = abs(row["pressure_kn_m2"])*panel["span_m"]
        reaction = row["reaction_bound_kn_m"]
        cuts.append({"combination":row["combination"], "reaction_kn_m":reaction,
                     "other_end_at_this_bound_kn_m":total-reaction, "total_applied_kn_m":total,
                     "upper_ratio":reaction/resistance})
    return {"status":"CONDITIONAL_PRESSURE_SHEAR_TRANSFER", "diameter_mm":dia, **grid, "bars_per_layer":2,
            "offset_each_side_mm":offset, "maximum_pitch_mm":pitch, "as_mm2_m":steel,
            "mu":.6, "steel_resistance_kn_m":.6*steel*mat.fyd/1000,
            "concrete_limit_kn_m":cap, "resistance_kn_m":resistance, "peak_reaction_kn_m":peak,
            "peak_ratio":peak/resistance, "force_margin_kn_m":resistance-peak,
            "wall_required_mm":wall["position_i_mm"], "wall_embedment_mm":wall_embed, "wall_available_mm":wall_limit,
            "column_required_mm":column["position_i_mm"], "column_embedment_mm":col_embed, "column_available_mm":column_limit,
            "template_longitudinal_clearance_mm":clear, "pressure_only_normal_force_kn_m":0., "combinations":cuts}


def pressure_connections(source, stages, geometry, panel, initial, combos, cover, mat, height):
    profiles = support_profiles(source, stages, panel)
    initial_ends = _development(profiles, geometry, panel, initial, mat)
    policy = layout_policy(geometry,panel,cover)
    inset = 50. if policy["inner"] else 0.
    initial_pair = (initial["diameter_mm"], initial["maximum_pitch_mm"])
    options = set(CAGES) | {(d,p) for d in (12,14,16,18,20,22,25) for p in (50,40)}
    candidates = [initial_pair] + sorted(options-{initial_pair}, key=lambda pair: (pair[0]**2/pair[1],pair[0]))
    h, ends = initial, initial_ends
    for candidate in candidates:
        try:
            grid = panel_pressure_design(panel, combos, cover, mat, height, candidates=[candidate], inset=inset,
                                        grid_for=lambda dia,pitch: level_grid(policy,dia,pitch,cover))
        except ValueError as exc:
            if str(exc) != "NO_PROPOSED_HORIZONTAL_CAGE_MEETS_PRESSURE_BENDING_AND_CRACKING_SHEAR":
                raise
            continue
        assessment = _development(profiles, geometry, panel, grid, mat)
        if all(row["fits_column"] for row in assessment.values()):
            h, ends = grid, assessment
            break
    selected = "first_station_mm" in h
    for side, end in ends.items():
        end["initial"] = dict(initial_ends[side])
        end["transfer"] = _transfer(panel, profiles[side], h, mat, policy)
        end["status"] = ("CONDITIONAL_PRESSURE_END_DESIGN" if selected and end["transfer"]["status"] != "HOLD"
                         else "COLUMN_ONLY_ANCHORAGE_EXCEEDANCE" if not end["fits_column"] else "HOLD")
    return h, {"initial_diameter_mm":initial_pair[0], "initial_maximum_pitch_mm":initial_pair[1],
               "initial_pitch_mm":initial["pitch_mm"], "initial_mr_knm_m":initial["design_moment_resistance_knm_m"],
               "max_aggregate_from_horizontal_spacing_mm":.75*(h["pitch_mm"]-h["diameter_mm"]),
               "detail":"STRAIGHT_COLUMN_EMBEDMENT_AND_SEPARATE_PERPENDICULAR_DOWELS", "ends":ends}
