"""Strong-axis storey connection of a rectangular pier to the selected frame beams (TBDY 7.6.6.2)."""
from math import hypot, isclose, isfinite

from ..column_engine.scwb_kernel import column_axis_interval_bound
from ..etabs_geometry import FRAME_INSERTION
from .column_clear_length import _FRAME_TRANSLATION, _index, _no_translation, _records, _translation_fields


def _beam_ends(source, stages, panel, thickness):
    geometry = source["vs06_b1_geometry_source"]["table_reads"]
    walls = _index(_records(geometry, "Wall Object Connectivity", "UniqueName UniquePt3 UniquePt4 Story"), "UniqueName")
    points = _index(_records(geometry, "Point Object Connectivity", "UniqueName X Y Z", ("X","Y","Z")), "UniqueName")
    def xyz(uid):
        return tuple(float(points[uid][k]) for k in "XYZ")
    wall = walls[panel["member"]]
    left, right = wall["UniquePt3"], wall["UniquePt4"]
    a, b = xyz(left), xyz(right)
    if a[2] != b[2] or not isclose(a[2], panel["top_z_m"], abs_tol=1e-6):
        raise ValueError("WALL_CONNECTION_ELEVATION_DIFFERS")
    length = hypot(b[0]-a[0], b[1]-a[1])
    u, v = (b[0]-a[0])/length, (b[1]-a[1])/length
    tables = source["column_axial"]["r10_source"]["table_reads"]
    inserts = _index(_records(tables, FRAME_INSERTION, "UniqueName CardinalPt Story"), "UniqueName")
    fields = _translation_fields(tables[FRAME_INSERTION], 1, _FRAME_TRANSLATION, ("OffsetCSys",))
    beams = _index(_records(source["geometry_capture"]["tables"], "BEAM_CONNECTIVITY",
                           "UniqueName Story UniquePtI UniquePtJ"), "UniqueName")
    designed = {r["member_id"]: r for r in (stages.get("beam_r10") or {}).get("beams", [])}
    selected = []
    for uid, beam in beams.items():
        if beam["Story"] != panel["story"]:
            continue
        entry = designed.get(uid, {})
        row = inserts[uid]
        # A displaced beam anywhere on this storey can change the inferred incidence.
        if (row["CardinalPt"] not in {"8 (Top Center)", "10 (Centroid)", "5 (Middle Center)"}
                or not _no_translation(row, fields) or not entry.get("horizontal_local2_up")):
            raise ValueError("BEAM_PLACEMENT_OR_HORIZONTAL_AXIS_UNBOUND")
        ids = [beam["UniquePtI"], beam["UniquePtJ"]]
        ends = [xyz(q) for q in ids]
        if any(abs(q[2]-a[2]) > 1e-6 for q in ends):
            raise ValueError("BEAM_STOREY_DATUM_DIFFERS")
        x = [(q[0]-a[0])*u + (q[1]-a[1])*v for q in ends]
        y = [-(q[0]-a[0])*v + (q[1]-a[1])*u for q in ends]
        width = float(entry["width_mm"])/2000 + thickness/2000
        if max(x) < -1e-6 or min(x) > length+1e-6 or min(y) > width or max(y) < -width:
            continue
        if abs(x[1]-x[0]) < 1e-6:  # Perpendicular beam flexural axis has zero strong-axis projection.
            continue
        if abs(y[1]-y[0]) > 1e-6:
            raise ValueError("OBLIQUE_BEAM_WALL_TRANSFER_REQUIRES_AXIS_RECONCILIATION")
        common = [i for i, q in enumerate(ids) if q in (left, right)]
        if len(common) != 1:
            raise ValueError("EMBEDDED_OR_UNRESOLVED_BEAM_WALL_INTERSECTION")
        idx, = common
        face = "I" if idx == 0 else "J"
        opposite = x[1-idx]
        if (ids[idx] == left and opposite >= 0) or (ids[idx] == right and opposite <= length):
            raise ValueError("BEAM_OVERLAPS_PIER_END_ZONE")
        if entry.get("selected_design", {}).get("status") != "CONDITIONAL_DESIGN_CALCULATED":
            raise ValueError("SELECTED_BEAM_DESIGN_INCOMPLETE_OR_EXCEEDED")
        end = entry["ends"][face]
        station = 0. if face == "I" else float(entry["length_mm"])/1000
        if (entry["point_"+face.lower()] != ids[idx] or end.get("released_for_bending") is not False
                or abs(float(entry["end_offsets_mm"][face])) > 1e-4
                or abs(float(end["target_station_m"])-station) > 1e-5):
            raise ValueError("ACTUAL_WALL_FACE_BEAM_DESIGN_STATION_REQUIRED")
        design = end.get("engineer_selection") or {}
        cap = design.get("capacity") or {}
        if (design.get("status") != "BEAM_SELECTED_CALCULATED" or cap.get("status") != "BEAM_CAPACITY_REFERENCE"
                or cap.get("axial_force_scenario_n") != 0):
            raise ValueError("SELECTED_ZERO_AXIAL_BEAM_END_CAPACITY_REQUIRED")
        magnitudes = {}
        for sign, label in ((1,"positive_m3_knm"),(-1,"negative_m3_knm")):
            point, = [p for p in cap["points"] if p["rotation_sign"] == sign]
            strength = sign*float(cap[label])
            guard = float(point["tolerance_knm"])
            if not (isfinite(strength) and isfinite(guard) and strength > 0 and guard >= 0):
                raise ValueError("BEAM_END_SIGNED_CAPACITY_UNRESOLVED")
            magnitudes[label] = strength + guard
        selected.append({"beam": uid, "label": entry["label"], "face": face, "point": ids[idx],
                         "upper_mr_knm": max(magnitudes.values()), **magnitudes})
    if not selected:
        raise ValueError("NO_STRONG_AXIS_BEAM_END_BOUND_TO_PIER")
    return selected


def strong_wall_checks(source, stages, pier, section, panels, designs, combos):
    rows = []
    cuts = {(x["member"], x["face"], x["combination"]): x for x in designs}
    for panel in panels:
        reason = None
        try:
            if panel["status"] != "PANEL_CALCULATED" or not section:
                raise ValueError("PIER_GEOMETRY_AND_SECTION_REQUIRED")
            beams = _beam_ends(source, stages, panel, pier["thickness_mm"])
            z = panel["top_z_m"]
            at_level = [(panel["member"], "Top")]
            if z < pier["top_z_m"]-1e-6:
                upper, = [p for p in panels if abs(p["bottom_z_m"]-z) < 1e-6]
                at_level.append((upper["member"], "Bottom"))
        except (KeyError, ValueError, TypeError) as exc:
            reason = str(exc)
        for combo in sorted(combos):
            r = {"lower_member": panel["member"], "story": panel["story"], "combination": combo, "status": "HOLD"}
            rows.append(r)
            if reason:
                r["reason"] = reason
                continue
            try:
                terms = []
                for uid, face in at_level:
                    nd = cuts[uid, face, combo]["nd_interval_kn"]
                    capacity = column_axis_interval_bound(section, "M3", *nd)
                    terms.append({"member": uid, "face": face, "nd_interval_kn": nd,
                                  "mr_lower_knm": capacity["mr_lower_bound_knm"]})
                wall = sum(t["mr_lower_knm"] for t in terms)
                required = 1.2*sum(b["upper_mr_knm"] for b in beams)
                if wall <= 0:
                    raise ValueError("POSITIVE_STRONG_AXIS_WALL_LOWER_BOUND_REQUIRED")
                r.update(z_m=z, wall_terms=terms, selected_beam_ends=beams, mr_wall_lower_knm=wall,
                         required_mr_knm=required, upper_utilization=required/wall,
                         status="STRONG_WALL_BOUND_SATISFIED" if wall >= required else "STRONG_WALL_BOUND_INCONCLUSIVE")
            except (KeyError, ValueError, TypeError) as exc:
                r["reason"] = str(exc)
    return rows
