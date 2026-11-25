"""Development and vertical-interface shear for a basement wall under transverse pressure."""
from math import ceil, cos, hypot, isfinite, pi, radians, sin, sqrt

from ..column_engine.section_capacity import perimeter
from .basement_joint_layout import layout_policy, level_grid
from .basement_pier_geometry import required
from .basement_wall_pressure import CAGES, DEFAULT_AGGREGATE_MM, clear_limit, panel_pressure_design
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
        selection = ((stages.get("r10_live") or {}).get("per_member", {}).get(uid, {})
                     .get("engineer_column_selection") or {})
        selected = selection.get("selected")
        if selected is not None:
            required(selection.get("member_id") == uid and selection.get("status") == "ENGINEER_COLUMN_SELECTED_NOT_PROVEN"
                     and selection.get("section_sides_mm") == [detail["t2_mm"], detail["t3_mm"]]
                     and selected.get("eligible") is True, "SELECTED_SUPPORT_CAGE_IDENTITY_REQUIRED")
            n2, n3 = selected["num_bars_2_dir"], selected["num_bars_3_dir"]
            dia, count = selected["diameter_mm"], selected["bar_count"]
            tie = selected["selected_transverse"]["tie_diameter_mm"]
            role = "ENGINEER_SELECTED_COLUMN_REBAR"
        else:
            counts = _named_row(rows, "Name", name, COLUMN_REINFORCING)
            n2, n3 = int(counts["NumBars2Dir"]), int(counts["NumBars3Dir"])
            dia, count = detail["longitudinal_bar_diameter_mm"], detail["bar_count"]
            tie, role = detail["tie_diameter_mm"], detail["reinforcement_role"]
        bars, _, _ = perimeter(detail["t2_mm"], detail["t3_mm"], detail["cover_to_tie_mm"], tie, dia, n2, n3)
        required(len(bars) == count, "COLUMN_LONGITUDINAL_GRID_MISMATCH")
        # At zero rotation the native column local-2 axis is global X.
        angle = radians(support["axis_angle_deg"])
        dx, dy = panel["width_direction"]
        along_2, along_3 = dx*cos(angle)+dy*sin(angle), -dx*sin(angle)+dy*cos(angle)
        across_2, across_3 = -along_3, along_2
        depth = abs(along_2)*detail["t2_mm"] + abs(along_3)*detail["t3_mm"]
        required(abs(depth-support["depth_mm"]) < 1e-5, "COLUMN_DEPTH_AND_LAYOUT_AXES_DIFFER")
        profiles[side] = {**support, "role": role, "bar_count": count, "fck": detail["fck_mpa"],
            "fcd": detail["fcd_mpa"], "cover": detail["cover_to_tie_mm"], "tie": tie,
            "bar_diameter": dia,
            "bar_offsets": [b.x2*across_2 + b.x3*across_3 for b in bars],
            "bar_coordinates": [(b.x2*along_2+b.x3*along_3, b.x2*across_2+b.x3*across_3) for b in bars],
            "width_mm": abs(across_2)*detail["t2_mm"]+abs(across_3)*detail["t3_mm"]}
    return profiles


def _bar_clearance(profile, offset, diameter):
    centre_distance = min(abs(sign*offset-x) for sign in (-1,1) for x in profile["bar_offsets"])
    return centre_distance - (diameter + profile["bar_diameter"])/2


def _entry_lanes(profiles, preferred):
    # Midpoints of neighbouring vertical bars maximise clearance inside each available lane.
    occupied = sorted({abs(x) for profile in profiles for x in profile["bar_offsets"]})
    mids = [(lo+hi)/2 for lo,hi in zip(occupied, occupied[1:]) if 0 < (lo+hi)/2 < preferred]
    return [preferred, *sorted(mids, reverse=True)]


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


def _hook_90(profile, side, offset, dia, required_mm, available, clear):
    """TS 500 Figure 9.1(b). Two quarter bends in plan with separate, inward-facing tails."""
    if not profile.get("bar_coordinates"):
        return None
    radius = 3.5*dia  # 6 phi inside mandrel diameter plus half a bar.
    tail = 12*dia
    projection = 5*ceil(.75*required_mm/5)
    tangent = projection-radius-dia/2
    if tangent < 0 or available < projection:
        return None
    sense = -1 if side == "I" else 1
    for turn in (1,-1):
        # Outward bends can use the wider column core. Inward bends must leave room
        # between the opposing hooks. Both paths stay within the far hoop.
        tip = offset+turn*(radius+tail)
        if (max(offset,tip)+dia/2+profile["cover"]+profile["tie"] > profile["width_mm"]/2
                or 2*min(offset,tip)-dia < clear):
            continue
        clearance = float("inf")
        for along, across in profile["bar_coordinates"]:
            x = profile["depth_mm"]/2+sense*along
            for face in (-1,1):
                y = turn*(face*across-offset)
                line = hypot(x-min(max(x,0.),tangent), y)
                tail_distance = hypot(x-(tangent+radius), y-min(max(y,radius),radius+tail))
                ax, ay = x-tangent, radius-y
                bend = (abs(hypot(ax,ay)-radius) if ax>=0 and ay>=0 else
                        min(hypot(ax,ay-radius),hypot(ax-radius,ay)))
                clearance = min(clearance, min(line,bend,tail_distance)-(profile["bar_diameter"]+dia)/2)
        if clearance >= clear:
            return {"type":"STANDARD_90_DEGREE_HOOK", "required_projection_mm":.75*required_mm,
                    "projection_mm":projection, "straight_to_tangent_mm":tangent, "inside_diameter_mm":6*dia,
                    "centreline_radius_mm":radius, "straight_tail_mm":tail, "clearance_mm":clearance,
                    "lateral_turn":turn}
    return None


def _development(profiles, geometry, panel, grid, mat, aggregate=DEFAULT_AGGREGATE_MM):
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
        limit = clear_limit(aggregate, dia, prof["bar_diameter"])
        adjacent = _adjacent_web(geometry, panel, side, offset, dia, cover)
        corridor = prof["depth_mm"]+adjacent["clear_extension_mm"] if adjacent.get("clear_extension_mm",0)>0 else available
        hook = None
        if specified > available or clearance < limit:
            hook = _hook_90(prof, side, offset, dia, needed, available, limit)
            if hook:
                clearance, specified, needed = hook["clearance_mm"], hook["projection_mm"], hook["required_projection_mm"]
        ends[side] = {**bond, "anchorage_type":"STANDARD_90_DEGREE_HOOK" if hook else "STRAIGHT", "hook":hook, "column": prof["column"], "column_section": prof["section"], "column_role": prof["role"],
            "column_bars": prof["bar_count"], "column_bar_diameter_mm": prof["bar_diameter"],
            "column_depth_mm": prof["depth_mm"], "end_cover_mm": end_cover, "far_hoop_mm": prof["tie"],
            "column_available_mm": available, "specified_embedment_mm": specified, "margin_mm": available-needed,
            "wall_side_available_mm": 500*panel["clear_length_m"], "wall_side_required_mm": wall["position_i_mm"],
            "template_longitudinal_clearance_mm": clearance, "adjacent_web": adjacent,
            "geometric_corridor_mm": corridor, "maximum_aggregate_mm": aggregate, "entry_required_mm": limit,
            "entry_margin_mm": clearance-limit, "horizontal_clear_mm": spacing,
            "horizontal_required_mm": clear_limit(aggregate, dia),
            "fits_column": specified <= available and clearance >= limit and spacing >= clear_limit(aggregate, dia)
            and wall["position_i_mm"] <= 500*panel["clear_length_m"]}
    return ends


def _transfer(panel, profile, h, mat, policy, *, vertical_diameter=None, native_edge=None):
    thickness = panel["thickness_m"]*1000
    native = native_edge.get("cuts") if native_edge is not None else None
    if native is None:
        peak = shear_peak = max(row["reaction_bound_kn_m"] for row in h["cuts"])
    else:
        required(bool(native), "NATIVE_SUPPORT_EDGE_COMBINATIONS_REQUIRED")
        peak = max(r["equivalent_friction_demand_kn_m"] for r in native)
        shear_peak = max(r["max_native_shear_kn_m"] for r in native)
    # Two dedicated deformed bars per level, perpendicular to the joint and symmetric
    # about the web mid-plane. No pressure-flexural steel is counted as a dowel.
    choices = sorted(((d,p) for d in (10,12,14,16,18,20,22,25) for p in (200,125,100,50)), key=lambda pair: pair[0]**2/pair[1])
    cover = max(h["cover_mm"],profile["cover"])
    column_limit = profile["depth_mm"]-cover-profile["tie"]
    wall_limit = panel["clear_length_m"]*500
    cap = .2*min(mat.fcd,profile["fcd"],25.)*thickness
    aggregate = policy["aggregate_mm"]
    for dia,pitch in choices:
        grid = level_grid(policy,dia,pitch,cover,dowel=True)
        if not grid:
            continue
        wall = tension_development(dia,mat.fyd,mat.fck,mat.fcd,cover,grid["clear_spacing_mm"])
        column = tension_development(dia,mat.fyd,profile["fck"],profile["fcd"],cover,grid["clear_spacing_mm"])
        steel = 2*grid["guaranteed_bars_per_m"]*pi*dia**2/4
        resistance = min(.6*steel*mat.fyd/1000, cap)
        wall_embed, col_embed = (5*ceil(dev["position_i_mm"]/5) for dev in (wall,column))
        # Each symmetric dowel pair must clear the supporting column's vertical bars.
        curtain_offset = thickness/2-h["cover_mm"]-h.get("curtain_inset_mm",0.)-1.5*h["diameter_mm"]
        limit = clear_limit(aggregate, dia, profile["bar_diameter"])
        lanes = _entry_lanes([profile], thickness/8)
        if vertical_diameter is not None:
            # Keep dedicated dowels between the actual face curtains.
            lanes = _entry_lanes([profile], curtain_offset)
            vertical_axis = curtain_offset-(h["diameter_mm"]+vertical_diameter)/2
            lanes = [off for off in lanes if off <= curtain_offset and abs(off-vertical_axis)-(dia+vertical_diameter)/2
                     >= clear_limit(aggregate,dia,vertical_diameter)]
        offset = next((off for off in lanes
                       if _bar_clearance(profile,off,dia) >= limit
                       and 2*off-dia >= clear_limit(aggregate,dia)
                       and abs(curtain_offset-off)-(dia+h["diameter_mm"])/2 >= clear_limit(aggregate,dia,h["diameter_mm"])), None)
        steel_limit = .6*steel*mat.fyd/1000
        if (peak <= steel_limit and shear_peak <= cap and wall_embed <= wall_limit and col_embed <= column_limit and offset is not None
                and grid["clear_spacing_mm"] >= clear_limit(aggregate,dia)):
            clear = _bar_clearance(profile,offset,dia)
            break
    else:
        return {"status":"HOLD", "reason":"NO_SEPARATE_FULLY_DEVELOPED_DOWEL_LAYOUT_IN_CATALOGUE",
                "peak_reaction_kn_m":peak, "native_peak_shear_kn_m":shear_peak, "concrete_limit_kn_m":cap}
    cuts = [{**r, "reaction_kn_m":r["equivalent_friction_demand_kn_m"],
             "upper_ratio":max(r["equivalent_friction_demand_kn_m"]/steel_limit, r["max_native_shear_kn_m"]/cap)}
            for r in (native or [])]
    for row in (h["cuts"] if native is None else []):
        total = abs(row["pressure_kn_m2"])*panel["span_m"]
        reaction = row["reaction_bound_kn_m"]
        cuts.append({"combination":row["combination"], "reaction_kn_m":reaction,
                     "other_end_at_this_bound_kn_m":total-reaction, "total_applied_kn_m":total,
                     "upper_ratio":reaction/resistance})
    return {"status":"CONDITIONAL_PRESSURE_SHEAR_TRANSFER", "diameter_mm":dia, **grid, "bars_per_layer":2,
            "offset_each_side_mm":offset, "maximum_pitch_mm":pitch, "as_mm2_m":steel,
            "mu":.6, "steel_resistance_kn_m":.6*steel*mat.fyd/1000,
            "concrete_limit_kn_m":cap, "resistance_kn_m":resistance, "peak_reaction_kn_m":peak,
            "peak_ratio":max(r["upper_ratio"] for r in cuts), "force_margin_kn_m":min(steel_limit-peak,cap-shear_peak),
            "wall_required_mm":wall["position_i_mm"], "wall_embedment_mm":wall_embed, "wall_available_mm":wall_limit,
            "column_required_mm":column["position_i_mm"], "column_embedment_mm":col_embed, "column_available_mm":column_limit,
            "template_longitudinal_clearance_mm":clear, "entry_required_mm":limit, "basis":"SAME_CORNER_NATIVE_EDGE" if native is not None else "ONE_WAY_PRESSURE_REFERENCE",
            "pressure_only_normal_force_kn_m":None if native is not None else 0., "combinations":cuts}


def developed_entry_grids(profiles, geometry, panel, cover, mat, policy, preferred_pair=None, *, include_unanchored=False):
    """Trial straight-bar grids at the actual levels and lanes inside both supporting cages."""
    options = set(CAGES) | {(d,p) for d in (12,14,16,18,20,22,25) for p in (40,50,60,75,80)}
    thickness = 1000*panel["thickness_m"]
    inset = 0.
    aggregate = policy["aggregate_mm"]
    options = sorted(options, key=lambda pair: (pair != preferred_pair, pair[0]**2/pair[1], pair[0], pair[1]))
    for dia, pitch in options:
        levels = level_grid(policy,dia,pitch,cover)
        if not levels or 2*levels["guaranteed_bars_per_m"]*pi*dia**2/4 < .0025*1000*thickness:
            continue
        preferred = thickness/2-cover-1.5*dia-inset
        lowest = preferred-min(dia,20.)
        lanes = [preferred, *_entry_lanes(profiles.values(), preferred)[1:], lowest]
        # A short straight embedment or a bend can clear a column bar before its
        # projected centreline. Include the exact straight-bar clearance boundaries.
        for profile in profiles.values():
            clearance = clear_limit(aggregate, dia, profile["bar_diameter"])+(dia+profile["bar_diameter"])/2
            for centre in profile["bar_offsets"]:
                lanes.extend((abs(centre)-clearance, abs(centre)+clearance))
        for lane in sorted({round(v,8) for v in lanes if lowest-1e-7 <= v <= preferred+1e-7}, reverse=True):
            if preferred-lane > min(dia,20.)+1e-8 or 2*lane-dia < clear_limit(aggregate,dia):
                continue
            grid = {**levels,"diameter_mm":dia,"maximum_pitch_mm":pitch,"cover_mm":cover,
                    "curtain_inset_mm":inset+preferred-lane,"physical_height_mm":policy["height"]}
            if include_unanchored:
                grid["guaranteed_bars_per_m"] = levels["minimum_in_any_full_metre"]
            ends = _development(profiles,geometry,panel,grid,mat,aggregate)
            if include_unanchored or all(end["fits_column"] for end in ends.values()):
                yield grid, ends, lane


def pressure_connections(source, stages, geometry, panel, initial, combos, cover, mat, height, *, aggregate=DEFAULT_AGGREGATE_MM):
    profiles = support_profiles(source, stages, panel)
    initial_ends = _development(profiles, geometry, panel, initial, mat, aggregate)
    policy = layout_policy(geometry,panel,cover,aggregate)
    initial_pair = (initial["diameter_mm"], initial["maximum_pitch_mm"])
    h, ends = initial, initial_ends
    selected = False
    for grid, assessment, _ in developed_entry_grids(profiles,geometry,panel,cover,mat,policy,initial_pair):
        pair = (grid["diameter_mm"], grid["maximum_pitch_mm"])
        try:
            h = panel_pressure_design(panel,combos,cover,mat,height,candidates=[pair],
                                      inset=grid["curtain_inset_mm"],aggregate=aggregate,grid_for=lambda d,p: grid)
        except ValueError as exc:
            if str(exc) != "NO_PROPOSED_HORIZONTAL_CAGE_MEETS_PRESSURE_BENDING_AND_CRACKING_SHEAR":
                raise
            continue
        ends, selected = assessment, True
        break
    for side, end in ends.items():
        end["initial"] = dict(initial_ends[side])
        end["transfer"] = _transfer(panel, profiles[side], h, mat, policy)
        end["status"] = ("CONDITIONAL_PRESSURE_END_DESIGN" if selected and end["fits_column"] and end["transfer"]["status"] != "HOLD"
                         else "SUPPORT_ENTRY_SPACING_UNSATISFIED" if end["entry_margin_mm"] < 0
                         else "COLUMN_ONLY_ANCHORAGE_EXCEEDANCE" if end["margin_mm"] < 0 else "HOLD")
    return h, {"initial_diameter_mm":initial_pair[0], "initial_maximum_pitch_mm":initial_pair[1],
               "initial_pitch_mm":initial["pitch_mm"], "initial_mr_knm_m":initial["design_moment_resistance_knm_m"],
               "max_aggregate_from_horizontal_spacing_mm":.75*(h["pitch_mm"]-h["diameter_mm"]),
               "detail":"STRAIGHT_COLUMN_EMBEDMENT_AND_SEPARATE_PERPENDICULAR_DOWELS", "ends":ends}
