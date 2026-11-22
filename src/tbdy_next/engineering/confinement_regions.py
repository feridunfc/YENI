"""Detailing schedules on the final selected frame cages, measured from the clear I face."""
from math import ceil, isclose, isfinite

from ..etabs_geometry import FRAME_INSERTION
from .column_clear_length import (_FRAME_TRANSLATION, _index, _no_translation, _records,
                                  _translation_fields, proven_clear_length_m)


def tie_schedule(length, zone, end_spacing, middle_spacing, *, minimum_pitch=0.0):
    """Two symmetric end zones. Runs share their endpoint tie at each transition."""
    if not all(isfinite(x) and x > 0 for x in (length, zone, end_spacing, middle_spacing)):
        raise ValueError("POSITIVE_CLEAR_LENGTH_ZONE_AND_SPACING_REQUIRED")
    face_gap = min(50.0, end_spacing / 2, length / 2)
    last = length - face_gap
    confined = min(zone, length)
    result = {"clear_length_mm": length, "required_end_length_mm": zone,
              "end_intervals_mm": {"I": [0.0, confined], "J": [length - confined, length]},
              "confined_union_mm": min(length, 2 * zone), "first_tie_mm": face_gap,
              "last_tie_mm": last, "overlap_mm": max(0.0, 2 * confined - length)}
    if face_gap == last:
        return {**result, "runs": [], "tie_count": 1}
    boundaries = ([(face_gap, last, end_spacing, "BOTH_ENDS")] if length <= 2 * zone
                  else [(face_gap, zone, end_spacing, "I"), (zone, length - zone, middle_spacing, "MIDDLE"),
                        (length - zone, last, end_spacing, "J")])
    # Very short transition pieces can violate the column's 50 mm minimum pitch.
    # Use end detailing throughout with the smaller specified pitch in that case.
    if any(b <= a or (b - a) / ceil((b - a) / pitch) < minimum_pitch
           for a, b, pitch, _ in boundaries):
        boundaries = [(face_gap, last, min(end_spacing, middle_spacing), "FULL_LENGTH_TIGHTER_PITCH")]
    runs, count = [], 1
    for start, stop, limit, region in boundaries:
        intervals = ceil((stop - start) / limit)
        actual = (stop - start) / intervals
        if actual < minimum_pitch - 1e-8:
            raise ValueError("INSUFFICIENT_ROOM_FOR_MINIMUM_TIE_PITCH")
        runs.append({"region": region, "from_mm": start, "to_mm": stop, "intervals": intervals,
                     "pitch_mm": actual})
        count += intervals
    return {**result, "runs": runs, "tie_count": count}


def _hook(diameter):
    return {"hook_angle_deg": 135, "minimum_inside_bend_diameter_mm": 5 * diameter,
            "minimum_ribbed_tail_mm": max(6 * diameter, 80)}


def column_confinement(uid, member, clear):
    length = proven_clear_length_m(clear, uid)
    if not length:
        return {"status": "HOLD", "reason": (clear or {}).get("status", "COLUMN_SUPPORT_FACES_UNAVAILABLE")}
    cage = member.get("engineer_column_selection") or {}
    selected = cage.get("selected") or {}
    ties = selected.get("selected_transverse")
    if not ties or not cage.get("section_sides_mm"):
        return {"status": "HOLD", "reason": "FINAL_SELECTED_COLUMN_CAGE_UNAVAILABLE"}
    faces = clear["faces"]
    if not faces["J"].get("beams"):
        return {"status": "HOLD", "reason": "UPPER_FRAMING_BEAM_OR_CANTILEVER_CLASSIFICATION_REQUIRED"}
    length *= 1000
    sides = cage["section_sides_mm"]
    zone = max(length / 6, 1.5 * max(sides), 500.0)
    row = {"longitudinal": selected["label"], "end_ties": ties["confinement_label"],
           "middle_ties": ties["midspan_label"], "legs_v2_v3": [ties["legs_v2"], ties["legs_v3"]],
           "crossties_v2_v3_per_station": [ties["crossties_parallel_v2"], ties["crossties_parallel_v3"]],
           "face_z_m": [faces["I"]["top_z_m"], faces["J"]["soffit_z_m"]],
           "face_joints": [faces[end]["joint_id"] for end in ("I", "J")],
           "lateral_leg_spacing_mm": ties["crosstie_max_spacing_a_mm"],
           "lateral_leg_limit_mm": ties["crosstie_limit_25_phi_mm"], "hook": _hook(ties["tie_diameter_mm"])}
    if not ties["all_tbdy_checks_met"]:
        return {**row, "status": "NUMERICAL_EXCEEDANCE", "reason": "SELECTED_COLUMN_TRANSVERSE_CHECK_FAILED"}
    try:
        schedule = tie_schedule(length, zone, ties["confinement_spacing_mm"], ties["midspan_spacing_mm"],
                                minimum_pitch=50.0)
    except ValueError as exc:
        return {**row, "status": "HOLD", "reason": str(exc)}
    mat = [slab for slab in faces["I"]["slabs"] if slab["type"] == "Mat"]
    if mat:
        thickness = min(slab["thickness_m"] for slab in mat) * 1000
        row["foundation_continuation"] = {"required_mm": min(sides), "model_depth_mm": thickness,
                                          "gross_depth_sufficient": thickness >= min(sides)}
    fail = mat and not row["foundation_continuation"]["gross_depth_sufficient"]
    return {**row, "status": "NUMERICAL_EXCEEDANCE" if fail else "SCHEDULE_CALCULATED",
            "reason": "FOUNDATION_DEPTH_BELOW_CONTINUATION" if fail else None, "schedule": schedule}


def _face_geometry(source):
    tables = ((source.get("column_axial") or {}).get("r10_source") or {}).get("table_reads", {})
    geometry = (source.get("vs06_b1_geometry_source") or {}).get("table_reads", {})
    try:
        points = _index(_records(geometry, "Point Object Connectivity", "UniqueName X Y Z", ("X", "Y", "Z")),
                        "UniqueName")
        frames = _index(_records(tables, FRAME_INSERTION, "UniqueName CardinalPt"), "UniqueName")
        translations = _translation_fields(tables[FRAME_INSERTION], 1, _FRAME_TRANSLATION, ("OffsetCSys",))
        xyz = {uid: tuple(float(r[k]) for k in "XYZ") for uid, r in points.items()}
        centered = {uid: r["CardinalPt"] for uid, r in frames.items() if _no_translation(r, translations)}
        return xyz, centered
    except (ValueError, KeyError, TypeError):
        return {}, {}


def _beam(beam, column_joints, square_half_sides, xyz, centered):
    ties = beam.get("engineer_stirrups") or {}
    offsets = beam.get("end_offsets_mm") or {}
    clear = beam.get("clear_span_mm")
    if not ties or len(offsets) != 2 or clear is None or clear <= 0:
        return {"status": "HOLD", "reason": "SELECTED_TIES_AND_NATIVE_CLEAR_SPAN_REQUIRED"}
    end, mid = ties["confinement"], ties["span"]
    p, q = (xyz.get(beam["point_" + side]) for side in ("i", "j"))
    aligned = (p and q and isclose(p[2], q[2], abs_tol=1e-8)
               and ((abs(p[0] - q[0]) < 1e-8) != (abs(p[1] - q[1]) < 1e-8))
               and beam.get("horizontal_local2_up") and centered.get(beam["member_id"]) in
               {"5 (Middle Center)", "8 (Top Center)", "10 (Centroid)"})
    faces = {}
    for side in ("I", "J"):
        joint = beam["point_" + side.lower()]
        station = beam["ends"].get(side, {}).get("target_station_m")
        expected = offsets[side] if side == "I" else beam["length_mm"] - offsets[side]
        supports = sorted(column_joints.get(joint, ()))
        widths = [square_half_sides.get(uid) for uid in supports]
        bound = (aligned and widths and all(w is not None and isclose(w, offsets[side], abs_tol=0.1) for w in widths)
                 and station is not None
                 and isclose(station * 1000, expected, abs_tol=0.1))
        faces[side] = {"joint_id": joint, "object_station_mm": expected,
                       "column_ids": supports, "column_half_widths_mm": widths,
                       "basis": "COLUMN_JOINT_AND_NATIVE_FACE_CUT" if bound else "MODEL_CUT_ONLY"}
    # An equal-spaced leg layout across the entire gross width bounds the pitch
    # across the narrower actual hoop. Bar engagement and hook fit need a drawing.
    spacing = {name: beam["width_mm"] / (zone["legs"] - 1)
               for name, zone in (("end", end), ("middle", mid)) if zone["legs"] >= 2}
    row = {"faces": faces, "effective_depth_mm": ties["effective_depth_mm"],
           "end_ties": end["label"], "middle_ties": mid["label"], "end_legs": end["legs"],
           "middle_legs": mid["legs"], "equal_leg_spacing_upper_bound_mm": spacing,
           "end_pitch_limit_mm": end["tbdy_spacing_limit_mm"], "end_hook": _hook(end["diameter_mm"]),
           "middle_hook": _hook(mid["diameter_mm"])}
    selected = beam.get("selected_design") or {}
    if selected.get("status") != "CONDITIONAL_DESIGN_CALCULATED":
        return {**row, "status": selected.get("status", "HOLD"), "reason": "SELECTED_BEAM_DESIGN_UNRESOLVED"}
    if len(spacing) != 2 or max(spacing.values()) > 350:
        return {**row, "status": "HOLD", "reason": "TRANSVERSE_LEG_POSITIONS_REQUIRED_FOR_350_MM_CHECK"}
    if end["diameter_mm"] < 8:
        return {**row, "status": "NUMERICAL_EXCEEDANCE", "reason": "END_HOOP_BELOW_8_MM"}
    schedule = tie_schedule(clear, end["zone_length_mm"], end["spacing_mm"], mid["spacing_mm"])
    return {**row, "status": "SCHEDULE_CALCULATED", "schedule": schedule}


def frame_confinement(source, columns, beams, stages):
    r10 = stages.get("r10_live") or {}
    members = r10.get("per_member", {})
    beam_records = {b["member_id"]: b for b in (stages.get("beam_r10") or {}).get("beams", ())}
    column_joints, col_rows, beam_rows = {}, [], []
    xyz, centered = _face_geometry(source)
    half_sides = {}
    for uid, item in (columns or {}).items():
        member = members.get(uid, {})
        sides = (member.get("engineer_column_selection") or {}).get("section_sides_mm") or []
        angle = member.get("local_axis_angle_deg")
        i, j = (xyz.get(item.get("UniquePt" + end)) for end in ("I", "J"))
        if (i and j and i[:2] == j[:2] and i[2] < j[2] and len(sides) == 2 and sides[0] == sides[1]
                and isinstance(angle, (int, float)) and isclose(angle, round(angle / 90) * 90, abs_tol=1e-7)
                and centered.get(uid) in {"5 (Middle Center)", "10 (Centroid)"}):
            half_sides[uid] = sides[0] / 2
        for end in ("I", "J"):
            column_joints.setdefault(item.get("UniquePt" + end), set()).add(uid)
        col_rows.append({"member_id": uid, "label": item["ColumnBay"], "story": item["Story"],
                         **(member.get("confinement_regions") or
                            {"status": "HOLD", "reason": "COLUMN_R10_SCHEDULE_UNAVAILABLE"})})
    for uid, item in (beams or {}).items():
        beam_rows.append({"member_id": uid, "label": item["BeamBay"], "story": item["Story"],
                          **_beam(beam_records.get(uid, {}), column_joints, half_sides, xyz, centered)})
    return {"columns": col_rows, "beams": beam_rows,
            "scope": "High-ductility rectangular frame proposal. Column faces use floor top and upper support soffit. "
                     "The two-end beam layout extends to model cuts at other supports. Infill short-column effects, "
                     "joint interiors, anchorage, splice positions and installed hook fit require separate detailing."}
