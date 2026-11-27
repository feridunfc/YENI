"""Check a staggered, full-tension transition from registered through-bars into the bridge curtain."""
from functools import lru_cache
from itertools import product
from math import atan, ceil, cos, floor, hypot, pi, sin, sqrt, tan

from .basement_wall_connection import tension_development
from .basement_wall_pressure import clear_limit
from .wall_regional_shell import regional_shell


def _levels(grid):
    return [grid["first_station_mm"] + i * grid["pitch_mm"] for i in range(grid["layers"])]


def _donors(original, incoming, original_area, incoming_area, lane_gap, radius, maximum):
    """Allocate finite donor area once. Admissible neighbours are ordered intervals in z."""
    remaining = [original_area for _ in original]
    coupled = []
    for z in incoming:
        needed = incoming_area
        for i, old in enumerate(original):
            if hypot(lane_gap, z - old) - radius > maximum + 1.0e-8:
                continue
            used = min(remaining[i], needed)
            if used > 1.0e-8:
                coupled.append({"new_z_mm": z, "old_z_mm": old, "area_mm2": used})
                remaining[i] -= used
                needed -= used
            if needed <= 1.0e-7:
                break
        if needed > 1.0e-7:
            return coupled, {"level_mm": z, "missing_area_mm2": needed}
    return coupled, None


def _grid_clear(left, right, offset, radius):
    return min(hypot(offset, a - b) - radius for a in left for b in right)


def _ramp_projection(move, diameter, inv_slope=6.0):
    """Two tangent circular bends with a 1:inv_slope straight, measured longitudinally."""
    angle = atan(1.0 / inv_slope)
    radius = 7.0 * diameter
    straight = (move - 2.0 * radius * (1.0 - cos(angle))) / sin(angle)
    if straight < 0.0:
        raise ValueError("OFFSET_TOO_SMALL_FOR_FULL_TANGENT_BENDS")
    return 2.0 * radius * sin(angle) + straight * cos(angle)


def _crank_fraction(s, run, move, diameter, inv_slope=6.0):
    if s <= 0.0:
        return 0.0
    if s >= run:
        return 1.0
    radius = 7.0 * diameter
    angle = atan(1.0 / inv_slope)
    arc = radius * sin(angle)
    if s < arc:
        return (radius - sqrt(radius**2 - s**2)) / move
    if s > run - arc:
        return 1.0 - (radius - sqrt(radius**2 - (run - s) ** 2)) / move
    return (radius * (1.0 - cos(angle)) + (s - arc) * tan(angle)) / move


def _min_count(levels, height):
    starts = [0.0, height - 1000.0] + [v + 1.0e-7 for v in levels if v < height - 1000.0]
    return min(sum(start <= v <= start + 1000.0 for v in levels) for start in starts)


def zoned_column_lap(panel, side, layout, selection, states, coordinates, material, cover, aggregate, *, near_families=()):
    from .wall_membrane_design import SELECTION_LIMIT

    detail = panel["two_way_shell"]["proposed_detail"]
    end = detail["ends"][side]
    old = detail["horizontal"]
    old_d = old["diameter_mm"]
    new_d = layout["web"]["diameter_mm"]
    height = old["physical_height_mm"]
    width = 1000.0 * panel["thickness_m"]
    length = 1000.0 * panel["clear_length_m"]
    old_track = width / 2.0 - cover - old["curtain_inset_mm"] - 1.5 * old_d
    outer = layout["web_track_mm"]
    radius = (old_d + new_d) / 2.0
    spacing = max(1.5 * new_d, clear_limit(aggregate, old_d, new_d)) + 0.5
    lane_gap = radius + spacing
    lb = tension_development(new_d, material.fyd, material.fck, material.fcd, cover, spacing)
    lap = 5 * ceil(1.8 * lb["position_i_mm"] / 5.0)

    # Size exterior longitudinal web bars (TBDY 7.6.4) and inner straight-lap tracks so
    # closed normal-plane lap hoops fit inside the exterior vertical curtain with 40 mm cover.
    vdiam = 14
    stations = ceil(length / 100.0 - 1.0e-9)
    vpitch = length / stations
    hoop_d = max(8.0, ceil(new_d / 3.0))
    half_offset = (hoop_d + 2.0) / 2.0
    half_space = vpitch / 4.0 - half_offset
    hoop_side = sqrt(max(0.0, ((hoop_d + vdiam) / 2.0 + clear_limit(aggregate, hoop_d, vdiam)) ** 2 - half_space**2)) + 3.5 * hoop_d * (1.0 - cos(pi / 12.0))
    outer_v_track = floor(width / 2.0 - cover - vdiam / 2.0)
    mid_track = float(floor(outer_v_track - hoop_side - (hoop_d + new_d) / 2.0 - 3.0))
    in_track = mid_track - lane_gap
    if in_track <= 0.0 or old_track <= mid_track or outer <= mid_track:
        raise ValueError("NO_COVERED_STAGGERED_LAP_FITS")

    r1 = _ramp_projection(old_track - mid_track, old_d, 6.0)
    r2 = _ramp_projection(mid_track - in_track, old_d, 9.0)
    r3 = _ramp_projection(mid_track - in_track, new_d, 9.0)
    r4 = _ramp_projection(outer - mid_track, new_d, 6.0)

    far = end["transfer"]
    dowels = _levels(far)
    near_dowel_start = length - selection["dowel_plus"]["full_straight_tail_mm"]
    lap1_start = float(5 * ceil((far["wall_embedment_mm"] + 20.0) / 5.0))
    lap1_end = lap1_start + lap
    lap2_end = float(5 * floor((near_dowel_start - 15.0) / 5.0))
    lap2_start = lap2_end - lap
    k1_s = lap1_start - 80.0
    k2l_s = lap1_end - 20.0
    k3r_s = lap2_start + 35.0
    k4_s = near_dowel_start + 80.0
    stagger = lap2_start - lap1_start
    if k1_s - r1 < 0.0 or lap1_end > lap2_start or k3r_s + r3 > k4_s or k4_s + r4 > length:
        raise ValueError("NO_COVERED_STAGGERED_LAP_FITS")

    root = coordinates[panel["joint_" + side.lower()]]
    sense = 1 if side == "I" else -1
    direction = [sense * v for v in panel["width_direction"]]

    def station(pt):
        return 1000.0 * sum((pt[i] - root[i]) * direction[i] for i in (0, 1)) - end["column_depth_mm"] / 2.0

    def x_old(face, s):
        if s <= k1_s - r1:
            return old_track
        if s <= k1_s:
            return old_track + (mid_track - old_track) * _crank_fraction(s - (k1_s - r1), r1, old_track - mid_track, old_d, 6.0)
        if face == 1 or s <= k2l_s - r2:
            return mid_track
        if s <= k2l_s:
            return mid_track + (in_track - mid_track) * _crank_fraction(s - (k2l_s - r2), r2, mid_track - in_track, old_d, 9.0)
        return in_track

    def x_new(face, s):
        if s >= k4_s + r4:
            return outer
        if s >= k4_s:
            return mid_track + (outer - mid_track) * _crank_fraction(s - k4_s, r4, outer - mid_track, new_d, 6.0)
        if face == -1 or s >= k3r_s + r3:
            return mid_track
        if s >= k3r_s:
            return in_track + (mid_track - in_track) * _crank_fraction(s - k3r_s, r3, mid_track - in_track, new_d, 9.0)
        return in_track

    area_old = pi * old_d**2 / 4.0
    area_new = pi * new_d**2 / 4.0
    max_gap = min(lap / 6.0, 100.0)
    faces = {}
    reg_by_face = {}
    for face, suffix, l_start, l_end in ((1, "plus", lap1_start, lap1_end), (-1, "minus", lap2_start, lap2_end)):
        registered = _levels(old.get("opposite_face_levels", old) if face == 1 else old)
        reg_by_face[face] = registered
        route = selection["web_" + suffix]
        zold = registered[1:-1] if route.get("edge_starters_terminate_straight") else registered
        phase = route["phase_mm"]
        pitch = layout["web"]["pitch_mm"]
        new_levels = route.get("installed_levels_mm") or [
            k * pitch + phase
            for k in range(-1, ceil(height / pitch) + 2)
            if cover + new_d / 2.0 <= k * pitch + phase <= height - cover - new_d / 2.0
        ]
        pairs, deficit = _donors(zold, new_levels, area_old, area_new, lane_gap, radius, max_gap)
        min_old_x_at_dowel = min(x_old(face, 0.0), x_old(face, far["wall_embedment_mm"]))
        far_gap = _grid_clear(registered, dowels, min_old_x_at_dowel - far["offset_each_side_mm"], (old_d + far["diameter_mm"]) / 2.0)
        straight_after_k1 = (l_end - k1_s) if face == 1 else ((k2l_s - r2) - k1_s)
        req_dev = max(end["wall_side_required_mm"], end["position_i_mm"])
        checks = {
            "donor_full_yield": deficit is None,
            "far_dowel_clearance": far_gap >= clear_limit(aggregate, old_d, far["diameter_mm"]),
            "registered_starter_developed": straight_after_k1 >= req_dev,
        }
        moving_d = new_d if face == 1 else old_d
        inv_s = 9.0
        faces[face] = {
            "face": face,
            "lap_start_mm": l_start,
            "lap_end_mm": l_end,
            "crank_start_mm": k3r_s if face == 1 else k2l_s - r2,
            "old_lap_track_mm": mid_track if face == 1 else in_track,
            "new_lap_track_mm": in_track if face == 1 else mid_track,
            "cranked_bar": "both",
            "entry_crank_knuckle_station_mm": k1_s,
            "exit_crank_knuckle_station_mm": k4_s,
            "straight_from_column_face_mm": straight_after_k1,
            "fan_out_mm": 0,
            "crank_run_mm": r3 if face == 1 else r2,
            "maximum_slope": 1.0 / 6.0,
            "inner_transition_slope": 1.0 / inv_s,
            "minimum_bend_inside_diameter_mm": 13 * moving_d,
            "old_levels_mm": zold,
            "old_lap_levels_mm": zold,
            "new_levels_mm": new_levels,
            "donor_allocations": pairs,
            "deficit": deficit,
            "far_dowel_clear_lower_mm": far_gap,
            "checks": checks,
            "crank_reaction_per_bar_kn": 1.5 * pi * moving_d**2 / 4.0 * material.fyd * sin(atan(1.0 / inv_s)) / 1000.0,
            "straight_edge_starters_mm": [z for z in registered if z not in zold],
            "straight_edge_termination_station_mm": (k2l_s - r2) if registered != zold else None,
        }

    from .wall_bar_paths import point_distance

    near_joint = coordinates[panel["joint_" + ("j" if side == "I" else "i")]]
    normal = (-panel["width_direction"][1], panel["width_direction"][0])

    def near_clear(s, x):
        near_s = station(near_joint)
        margin = float("inf")
        if near_s - s > 1700.0:
            return margin
        for sgn in (-1, 1):
            p = tuple((s - near_s) * u + sgn * x * v for u, v in zip(direction, normal))
            for family in near_families:
                segments = family["segments"]
                if family["member"] == panel["member"] and family["role"] == "web":
                    segments = segments[1:]
                if not segments:
                    continue
                distance = min(point_distance(p, a, b) - e for a, b, e in segments)
                margin = min(margin, distance - (vdiam + family["diameter"]) / 2.0 - clear_limit(aggregate, vdiam, family["diameter"]))
        return margin

    @lru_cache(maxsize=None)
    def available(s, x):
        values = []
        for face_sgn, row in faces.items():
            if s <= row["lap_end_mm"]:
                values.append(abs(x - x_old(face_sgn, s)) * cos(atan(1.0 / 6.0)) - (vdiam + old_d) / 2.0)
            if s >= row["lap_start_mm"]:
                values.append(abs(x - x_new(face_sgn, s)) * cos(atan(1.0 / 6.0)) - (vdiam + new_d) / 2.0)
        for dx, dia, ds in (
            (far["offset_each_side_mm"], far["diameter_mm"], max(s - far["wall_embedment_mm"], 0.0)),
            (layout["dowel_track_mm"], layout["dowel"]["diameter_mm"], max(near_dowel_start - s, 0.0)),
        ):
            values.append(hypot(x - dx, ds) - (vdiam + dia) / 2.0 - clear_limit(aggregate, vdiam, dia))
        return min(*values, near_clear(s, x))

    inner_v_max = floor(mid_track + (hoop_d + new_d) / 2.0 + 3.0 - hoop_side)
    x_candidates = [outer_v_track] + list(range(inner_v_max, 44, -1))
    offsets = []
    gaps = []
    for i in range(stations):
        s = min(i + 0.5, stations - i - 0.5) * vpitch
        options = []
        for x in x_candidates:
            gap = min(available(s, x), available(length - s, x))
            options.append((x, gap))
            if gap >= 0.0:
                break
        x, gap = max(options, key=lambda item: (item[1] >= 0.0, item[0] if item[1] >= 0.0 else item[1]))
        offsets.append(x)
        gaps.append(gap)
    vtrack = min(offsets)

    @lru_cache(maxsize=None)
    def planes(s):
        choices = []
        for face_sgn in (1, -1):
            row = faces[face_sgn]
            face_options = []
            if s <= row["lap_end_mm"]:
                xo = x_old(face_sgn, s)
                cos_f = (
                    cos(atan(1.0 / 6.0))
                    if k1_s - r1 < s < k1_s
                    else (cos(atan(1.0 / 9.0)) if face_sgn == -1 and k2l_s - r2 < s < k2l_s else 1.0)
                )
                face_options.append((xo, _min_count(row["old_levels_mm"], height) * area_old * cos_f * material.fyd / 1000.0))
            if s >= row["lap_start_mm"]:
                xn = x_new(face_sgn, s)
                cos_f = (
                    cos(atan(1.0 / 6.0))
                    if k4_s < s < k4_s + r4
                    else (cos(atan(1.0 / 9.0)) if face_sgn == 1 and k3r_s < s < k3r_s + r3 else 1.0)
                )
                face_options.append((xn, _min_count(row["new_levels_mm"], height) * area_new * cos_f * material.fyd / 1000.0))
            choices.append(face_options)
        vertical = floor(1000.0 / vpitch + 1.0e-9) * pi * vdiam**2 / 4.0 * material.fyd / 1000.0
        at = max(0.0, min(length, s))
        local_v = min(x for i, x in enumerate(offsets) if abs((i + 0.5) * vpitch - at) <= 1000.0 + 1.0e-7)
        return [[(p[0], n[0], p[1], n[1]), (local_v, local_v, vertical, vertical)] for p, n in product(*choices)]

    near_side = "J" if side == "I" else "I"
    frictions = {r["combination"]: r["equivalent_friction_demand_kn_m"] for r in panel["native_support_edges"][near_side]["cuts"]}
    dowel_grid = layout["dowel"]
    dowel_d = dowel_grid["diameter_mm"]
    ld = tension_development(dowel_d, material.fyd, material.fck, material.fcd, cover, dowel_grid["clear_spacing_mm"])["position_i_mm"]
    by_face = []
    for suffix in ("plus", "minus"):
        route = selection["dowel_" + suffix]
        zz = [k * dowel_grid["pitch_mm"] + route["phase_mm"] for k in range(-1, ceil(height / dowel_grid["pitch_mm"]) + 2)]
        zz = [z for z in zz if cover + dowel_d / 2.0 <= z <= height - cover - dowel_d / 2.0]
        by_face.append((_min_count(zz, height) * pi * dowel_d**2 / 4.0 * material.fyd / 1000.0, route["full_straight_tail_mm"]))

    def residual(name, s):
        if s < length - 1.0e-7 or name not in frictions:
            return ()
        steel = min(total * min(1.0, tail / ld) for total, tail in by_face)
        res = max(0.0, steel - frictions[name] / (1.2 * SELECTION_LIMIT))
        return [(f, layout["dowel_track_mm"], res) for f in (0.25, 0.5, 0.75, 1.0)]

    field = regional_shell(states, coordinates, station, planes, width, material, SELECTION_LIMIT, edge_steel=residual)
    field["terminal_dowel_allocation"] = {
        name: {"friction_tie_kn_m_per_face": v / 1.2, "residual_kn_m_per_face_at_limit": SELECTION_LIMIT * residual(name, length)[-1][2]}
        for name, v in frictions.items()
    }
    vertical_detail = {
        "diameter_mm": vdiam,
        "pitch_mm": vpitch,
        "minimum_track_mm": vtrack,
        "offsets_by_station_mm": offsets,
        "governing_clearance_margin_mm": min(gaps),
    }
    from .wall_knuckle_restraint import knuckle_restraint_and_cage_audit
    from .wall_lap_hoops import place_lap_hoops, straight_lap_enclosure

    loops = place_lap_hoops(faces, vertical_detail, layout, selection, height, width, cover, aggregate, old_d, new_d)
    enclosure = straight_lap_enclosure(faces, loops, vertical_detail, width, cover, old_d, new_d, aggregate)
    reaction, cage_audit = knuckle_restraint_and_cage_audit(
        faces=faces,
        loops=loops,
        vertical_detail=vertical_detail,
        layout=layout,
        selection=selection,
        far=far,
        dowels=dowels,
        reg_minus=reg_by_face[-1],
        x_old_fn=x_old,
        x_new_fn=x_new,
        stations_spec=(k1_s, r1, k2l_s, r2, k3r_s, r3, k4_s, r4, mid_track, in_track),
        dims=(old_d, new_d, material.fyd, height, width, cover),
        aggregate=aggregate,
        length=length,
    )
    return {
        "basis": "STAGGERED_UNSPLICED_COLUMN_BARS_TO_STRAIGHT_BRIDGE_STARTERS",
        "clear_length_mm": length,
        "old_track_mm": old_track,
        "new_track_mm": outer,
        "mid_lap_track_mm": mid_track,
        "inner_lap_track_mm": in_track,
        "lap_separation_mm": spacing,
        "development": lb,
        "full_tension_lap_mm": lap,
        "centre_stagger_mm": stagger,
        "vertical": vertical_detail,
        "lap_confinement": loops,
        "straight_lap_enclosure": enclosure,
        "crank_tie_equilibrium": reaction,
        "regional_cage_audit": cage_audit,
        "cover_mm": cover,
        "registered_column_passage": end.get("anchorage_type") == "UNSPLICED_THROUGH_COLUMN"
        and end.get("layout_status") == "PROPOSED_PRESSURE_BARS_FIT",
        "faces": {str(k): v for k, v in faces.items()},
        "regional_shell": field,
    }
