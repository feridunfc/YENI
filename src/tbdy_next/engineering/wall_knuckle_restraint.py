"""Vertical knuckle bearing rods, 135-degree tension crossties, and 3D regional cage audit."""
from collections import defaultdict
from math import atan, ceil, cos, hypot, pi, sin, sqrt

from .basement_wall_pressure import clear_limit
from .wall_crank_restraint import hook_path
from .wall_lap_hoops import hoop_path
from .wall_membrane_design import SELECTION_LIMIT


def seg3d_distance(p1, p2, q1, q2):
    """Exact Euclidean distance between two 3D line segments [p1, p2] and [q1, q2]."""
    u = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    v = (q2[0] - q1[0], q2[1] - q1[1], q2[2] - q1[2])
    w = (p1[0] - q1[0], p1[1] - q1[1], p1[2] - q1[2])
    a = sum(x * x for x in u)
    b = sum(x * y for x, y in zip(u, v))
    c = sum(x * x for x in v)
    d = sum(x * y for x, y in zip(u, w))
    e = sum(x * y for x, y in zip(v, w))
    det = a * c - b * b
    s_den, t_den = det, det
    if det < 1.0e-12:
        s_num, s_den = 0.0, 1.0
        t_num, t_den = e, c
    else:
        s_num = b * e - c * d
        t_num = a * e - b * d
        if s_num < 0.0:
            s_num, t_num, t_den = 0.0, e, c
        elif s_num > s_den:
            s_num, t_num, t_den = s_den, e + b, c
    if t_num < 0.0:
        t_num = 0.0
        s_num, s_den = (0.0, 1.0) if -d < 0.0 else ((s_den, s_den) if -d > a else (-d, a))
    elif t_num > t_den:
        t_num = t_den
        s_num, s_den = (0.0, 1.0) if (-d + b) < 0.0 else ((s_den, s_den) if (-d + b) > a else (-d + b, a))
    sc = 0.0 if abs(s_num) < 1.0e-12 or s_den == 0.0 else s_num / s_den
    tc = 0.0 if abs(t_num) < 1.0e-12 or t_den == 0.0 else t_num / t_den
    dp = (w[0] + sc * u[0] - tc * v[0], w[1] + sc * u[1] - tc * v[1], w[2] + sc * u[2] - tc * v[2])
    return sqrt(sum(x * x for x in dp))


def solve_continuous_rod_on_ties(z_ties, loads, rod_d, tie_d, span_tie_mm, elastic_modulus_mpa=200000.0):
    """Solve a 1D Euler-Bernoulli bearing rod on tension-only elastic crosstie springs.

    After active-set convergence (all active crosstie reactions R_i >= 0), shear V(z)
    and bending moment M(z) are integrated independently from pure statics.
    """
    if not z_ties:
        total = sum(f for _, f in loads)
        return [], float("inf"), float("inf"), abs(total), float("inf")
    nodes = sorted(set(z_ties) | {zl for zl, _ in loads})
    idx_map = {z: i for i, z in enumerate(nodes)}
    n = len(nodes)
    ei = elastic_modulus_mpa * (pi * rod_d**4 / 64.0)
    k_spring = elastic_modulus_mpa * (pi * tie_d**2 / 4.0) / max(span_tie_mm, 50.0)
    load_vec = [0.0] * (2 * n)
    for zl, fl_kn in loads:
        load_vec[2 * idx_map[zl]] += fl_kn * 1000.0
    active = set(z_ties)
    u = [0.0] * (2 * n)
    for _ in range(25):
        if not active:
            return [0.0 for _ in z_ties], float("inf"), float("inf"), float("inf"), float("inf")
        stiff = [[0.0] * (2 * n) for _ in range(2 * n)]
        for elem in range(n - 1):
            span = nodes[elem + 1] - nodes[elem]
            c1, c2 = 12.0 * ei / span**3, 6.0 * ei / span**2
            c3, c4 = 4.0 * ei / span, 2.0 * ei / span
            dofs = (2 * elem, 2 * elem + 1, 2 * (elem + 1), 2 * (elem + 1) + 1)
            ke = ((c1, c2, -c1, c2), (c2, c3, -c2, c4), (-c1, -c2, c1, -c2), (c2, c4, -c2, c3))
            for r in range(4):
                for col in range(4):
                    stiff[dofs[r]][dofs[col]] += ke[r][col]
        for zt in active:
            ii = 2 * idx_map[zt]
            stiff[ii][ii] += k_spring
        m = 2 * n
        aug = [stiff[r][:] + [load_vec[r]] for r in range(m)]
        for col in range(m):
            piv = max(range(col, m), key=lambda r: abs(aug[r][col]))
            aug[col], aug[piv] = aug[piv], aug[col]
            pv = aug[col][col]
            if abs(pv) < 1.0e-12:
                return [0.0 for _ in z_ties], float("inf"), float("inf"), float("inf"), float("inf")
            for j in range(col, m + 1):
                aug[col][j] /= pv
            for r in range(col + 1, m):
                fac = aug[r][col]
                if fac != 0.0:
                    for j in range(col, m + 1):
                        aug[r][j] -= fac * aug[col][j]
        u = [0.0] * m
        for r in range(m - 1, -1, -1):
            u[r] = aug[r][m] - sum(aug[r][j] * u[j] for j in range(r + 1, m))
        neg = {zt for zt in active if u[2 * idx_map[zt]] < -1.0e-9}
        if not neg:
            break
        active -= neg
    reactions = [max(0.0, k_spring * u[2 * idx_map[zt]] / 1000.0) if zt in active else 0.0 for zt in z_ties]
    net_node_kn = {z: 0.0 for z in nodes}
    for zl, fl_kn in loads:
        net_node_kn[zl] += fl_kn
    for zt, r_kn in zip(z_ties, reactions):
        net_node_kn[zt] -= r_kn
    shear = moment = max_v = max_m = 0.0
    for i, z in enumerate(nodes):
        shear += net_node_kn[z]
        max_m = max(max_m, abs(moment))
        if i < n - 1:
            max_v = max(max_v, abs(shear))
            moment += shear * (nodes[i + 1] - z) / 1000.0
    max_m = max(max_m, abs(moment))
    return reactions, max_m, max_v, abs(shear), abs(moment)


def _intentional_bearing_contact(ta, tb):
    for a, b in ((ta, tb), (tb, ta)):
        if a.startswith("rod_K1") and b.startswith("old"):
            return True
        if a.startswith("rod_K23_L") and b.startswith("old-"):
            return True
        if a.startswith("rod_K23_R") and b.startswith("new+"):
            return True
        if a.startswith("rod_K4") and b.startswith("new"):
            return True
        if a.startswith("tie_K") and b.startswith("rod_" + a.split("@")[0][4:]):
            return True
    return False


def audit_regional_cage_3d(segments, width, height, cover):
    """Verify nominal cover and 3D solid non-intersection across all installed cage segments."""
    cover_violations = 0
    for p0, p1, rad, _ in segments:
        if (max(abs(p0[1]), abs(p1[1])) + rad > width / 2.0 - cover + 1.0e-6
                or min(p0[2], p1[2]) - rad < cover - 1.0e-6
                or max(p0[2], p1[2]) + rad > height - cover + 1.0e-6):
            cover_violations += 1
    grid = defaultdict(list)
    for idx, (p0, p1, rad, _) in enumerate(segments):
        for bs in range(int((min(p0[0], p1[0]) - rad) // 250), int((max(p0[0], p1[0]) + rad) // 250) + 1):
            for bz in range(int((min(p0[2], p1[2]) - rad) // 250), int((max(p0[2], p1[2]) + rad) // 250) + 1):
                grid[(bs, bz)].append(idx)
    seen = set()
    conflicts = 0
    first = None
    for cell in grid.values():
        count = len(cell)
        for i in range(count):
            ia = cell[i]
            a0, a1, ra, ta = segments[ia]
            ax0, ax1 = min(a0[1], a1[1]) - ra, max(a0[1], a1[1]) + ra
            as0, as1 = min(a0[0], a1[0]) - ra, max(a0[0], a1[0]) + ra
            az0, az1 = min(a0[2], a1[2]) - ra, max(a0[2], a1[2]) + ra
            for j in range(i + 1, count):
                ib = cell[j]
                b0, b1, rb, tb = segments[ib]
                if ta == tb:
                    continue
                if ax1 < min(b0[1], b1[1]) - rb or ax0 > max(b0[1], b1[1]) + rb:
                    continue
                if as1 < min(b0[0], b1[0]) - rb or as0 > max(b0[0], b1[0]) + rb:
                    continue
                if az1 < min(b0[2], b1[2]) - rb or az0 > max(b0[2], b1[2]) + rb:
                    continue
                pair = (ia, ib) if ia < ib else (ib, ia)
                if pair in seen:
                    continue
                seen.add(pair)
                req = (ra + rb - 0.5) if _intentional_bearing_contact(ta, tb) else (ra + rb - 1.0e-4)
                dist = seg3d_distance(a0, a1, b0, b1)
                if dist < req:
                    conflicts += 1
                    if first is None:
                        first = {"bars": [ta, tb], "surface_overlap_mm": round((ra + rb) - dist, 4)}
    return {
        "segment_count": len(segments),
        "candidate_pairs_tested": len(seen),
        "cover_violations": cover_violations,
        "interfering_pairs": conflicts,
        "first_interference": first,
        "satisfied": cover_violations == 0 and conflicts == 0,
    }


def knuckle_restraint_and_cage_audit(
    *,
    faces,
    loops,
    vertical_detail,
    layout,
    selection,
    far,
    dowels,
    reg_minus,
    x_old_fn,
    x_new_fn,
    stations_spec,
    dims,
    aggregate,
    length,
):
    """Place K1, K23, K4 vertical bearing rods + 135-deg crossties and audit the full 3D cage."""
    old_d, new_d, fyd, height, width, cover = dims
    k1_s, r1, k2l_s, r2, k3r_s, r3, k4_s, r4, mid_track, in_track = stations_spec
    vdiam = vertical_detail["diameter_mm"]
    vpitch = vertical_detail["pitch_mm"]
    offsets = vertical_detail["offsets_by_station_mm"]

    base_segs = []
    vr = vdiam / 2.0
    for i, xo in enumerate(offsets):
        sv = (i + 0.5) * vpitch
        for sgn in (-1, 1):
            base_segs.append(((sv, sgn * xo, cover + vr), (sv, sgn * xo, height - cover - vr), vr, f"vert_{sgn}_{i}"))

    for sgn_str in ("1", "-1"):
        cage = loops[sgn_str]
        half_off = cage["hook_plane_separation_mm"] / 2.0
        for gi, (grp, bank) in enumerate(zip(cage["groups"], cage["stations"])):
            d_h = grp["diameter_mm"]
            err_h = 3.5 * d_h * (1.0 - cos(pi / 48.0))
            pts = hoop_path(*grp["shape"][:4], d_h, *grp["shape"][4:])
            for st in bank["stations_mm"]:
                for s_plane in (st - half_off, st + half_off):
                    tag = f"hoop_{sgn_str}_{gi}@{s_plane:.1f}"
                    for p0, p1 in zip(pts, pts[1:]):
                        base_segs.append(((s_plane, p0[0], p0[1]), (s_plane, p1[0], p1[1]), d_h / 2.0 + err_h, tag))

    def crank_pts(face, s_start, s_end, fn, knots):
        ss = sorted(
            {s_start, s_end}
            | {k0 + (k1 - k0) * j / 8.0 for k0, k1 in knots for j in range(9) if s_start <= k0 + (k1 - k0) * j / 8.0 <= s_end}
        )
        return [(s, face * fn(face, s)) for s in ss]

    err_old = 7.0 * old_d * (1.0 - cos(atan(1.0 / 6.0) / 4.0))
    err_new = 7.0 * new_d * (1.0 - cos(atan(1.0 / 6.0) / 4.0))
    zold_p = faces[1]["old_levels_mm"]
    zold_m = faces[-1]["old_levels_mm"]
    znew_p = faces[1]["new_levels_mm"]
    znew_m = faces[-1]["new_levels_mm"]
    lap1_s, lap1_e = faces[1]["lap_start_mm"], faces[1]["lap_end_mm"]
    lap2_s, lap2_e = faces[-1]["lap_start_mm"], faces[-1]["lap_end_mm"]

    for z in zold_p:
        pts = crank_pts(+1, 0.0, lap1_e, x_old_fn, [(k1_s - r1, k1_s)])
        for (s0, x0), (s1, x1) in zip(pts, pts[1:]):
            base_segs.append(((s0, x0, z), (s1, x1, z), old_d / 2.0 + err_old, f"old+@{z:.1f}"))
    for z in reg_minus:
        end_s = lap2_e if z in zold_m else (k2l_s - r2)
        pts = crank_pts(-1, 0.0, end_s, x_old_fn, [(k1_s - r1, k1_s), (k2l_s - r2, k2l_s)])
        for (s0, x0), (s1, x1) in zip(pts, pts[1:]):
            base_segs.append(((s0, x0, z), (s1, x1, z), old_d / 2.0 + err_old, f"old-@{z:.1f}"))
    for z in znew_p:
        pts = crank_pts(+1, lap1_s, length, x_new_fn, [(k3r_s, k3r_s + r3), (k4_s, k4_s + r4)])
        for (s0, x0), (s1, x1) in zip(pts, pts[1:]):
            base_segs.append(((s0, x0, z), (s1, x1, z), new_d / 2.0 + err_new, f"new+@{z:.1f}"))
    for z in znew_m:
        pts = crank_pts(-1, lap2_s, length, x_new_fn, [(k4_s, k4_s + r4)])
        for (s0, x0), (s1, x1) in zip(pts, pts[1:]):
            base_segs.append(((s0, x0, z), (s1, x1, z), new_d / 2.0 + err_new, f"new-@{z:.1f}"))

    far_r = far["diameter_mm"] / 2.0
    for z in dowels:
        for sgn in (-1, 1):
            base_segs.append(
                ((0.0, sgn * far["offset_each_side_mm"], z), (far["wall_embedment_mm"], sgn * far["offset_each_side_mm"], z), far_r, f"fardowel_{sgn}@{z:.1f}")
            )
    dowel_d = layout["dowel"]["diameter_mm"]
    dowel_pitch = layout["dowel"]["pitch_mm"]
    for sgn, suffix in ((+1, "plus"), (-1, "minus")):
        route = selection["dowel_" + suffix]
        s_tail_start = length - route["full_straight_tail_mm"]
        zz = [
            k * dowel_pitch + route["phase_mm"]
            for k in range(-1, ceil(height / dowel_pitch) + 2)
            if cover + dowel_d / 2.0 <= k * dowel_pitch + route["phase_mm"] <= height - cover - dowel_d / 2.0
        ]
        for z in zz:
            base_segs.append(
                ((s_tail_start, sgn * layout["dowel_track_mm"], z), (length, sgn * layout["dowel_track_mm"], z), dowel_d / 2.0, f"neardowel_{sgn}@{z:.1f}")
            )

    f_old_6 = 1.5 * pi * old_d**2 / 4.0 * fyd * sin(atan(1.0 / 6.0)) / 1000.0
    f_old_9 = 1.5 * pi * old_d**2 / 4.0 * fyd * sin(atan(1.0 / 9.0)) / 1000.0
    f_new_6 = 1.5 * pi * new_d**2 / 4.0 * fyd * sin(atan(1.0 / 6.0)) / 1000.0
    f_new_9 = 1.5 * pi * new_d**2 / 4.0 * fyd * sin(atan(1.0 / 9.0)) / 1000.0

    clamps_spec = (
        ("K1", (-(mid_track + old_d / 2.0 + 11.0), k1_s), (+(mid_track + old_d / 2.0 + 11.0), k1_s), 22.0, 12.0, +1, 36,
         [(z, f_old_6) for z in zold_p], [(z, f_old_6) for z in reg_minus]),
        ("K23", (-(in_track + old_d / 2.0 + 14.0), k2l_s), (+(in_track + new_d / 2.0 + 14.0), k3r_s), 28.0, 14.0, -1, 56,
         [(z, f_new_9) for z in znew_p], [(z, f_old_9) for z in zold_m]),
        ("K4", (-(mid_track + new_d / 2.0 + 14.0), k4_s), (+(mid_track + new_d / 2.0 + 14.0), k4_s), 28.0, 14.0, -1, 36,
         [(z, f_new_6) for z in znew_p], [(z, f_new_6) for z in znew_m]),
    )

    rod_segs = []
    tie_segs = []
    clamp_rows = []
    total_knuckles = 0
    balanced_knuckles = 0
    unbraced = []

    for name, (x_l, s_l), (x_r, s_r), rod_d, tie_d, b_sgn, max_dz, loads_p, loads_m in clamps_spec:
        rod_segs.append(((s_l, x_l, cover + rod_d / 2.0), (s_l, x_l, height - cover - rod_d / 2.0), rod_d / 2.0, f"rod_{name}_L"))
        rod_segs.append(((s_r, x_r, cover + rod_d / 2.0), (s_r, x_r, height - cover - rod_d / 2.0), rod_d / 2.0, f"rod_{name}_R"))
        path_xs, err = hook_path((x_l, s_l), (x_r, s_r), rod_d, rod_d, tie_d, b_sgn, 3.5)
        xs, ss = [p[0] for p in path_xs], [p[1] for p in path_xs]
        s_lo, s_hi = min(ss) - tie_d / 2.0 - err, max(ss) + tie_d / 2.0 + err
        xmin_t, xmax_t = min(xs) - tie_d / 2.0 - err, max(xs) + tie_d / 2.0 + err
        local_obs = [
            seg for seg in base_segs
            if max(seg[0][0], seg[1][0]) + seg[2] >= s_lo and min(seg[0][0], seg[1][0]) - seg[2] <= s_hi
            and max(seg[0][1], seg[1][1]) + seg[2] >= xmin_t and min(seg[0][1], seg[1][1]) - seg[2] <= xmax_t
        ]
        req_dz = tie_d + clear_limit(aggregate, tie_d, tie_d) + 1.0
        z_min_lim = cover + tie_d / 2.0 + 2.0
        z_max_lim = height - cover - tie_d / 2.0 - 2.0
        dz_choices = tuple(v for step in range(0, max_dz + 1, 4) for v in ((0.0,) if step == 0 else (float(step), -float(step))))
        chosen = []
        z_cursor = z_min_lim
        while z_cursor <= z_max_lim:
            found = None
            for dz in dz_choices:
                z_l, z_r = z_cursor, z_cursor + dz
                slope_x = (z_r - z_l) / (x_r - x_l)
                z_xmin = z_l + slope_x * (xmin_t - x_l)
                z_xmax = z_l + slope_x * (xmax_t - x_l)
                if min(z_xmin, z_xmax) < z_min_lim or max(z_xmin, z_xmax) > z_max_lim:
                    continue
                if chosen:
                    p_l, p_r = chosen[-1]
                    prev_slope = (p_r - p_l) / (x_r - x_l)
                    p_xmin = p_l + prev_slope * (xmin_t - x_l)
                    p_xmax = p_l + prev_slope * (xmax_t - x_l)
                    slope_c = hypot(1.0, max(abs(slope_x), abs(prev_slope)))
                    if min(z_xmin - p_xmin, z_xmax - p_xmax) / slope_c < req_dz:
                        continue
                pts3d = [(p[1], p[0], z_l + slope_x * (p[0] - x_l)) for p in path_xs]
                t_segs = list(zip(pts3d, pts3d[1:]))
                z_lo_t = min(p[2] for p in pts3d) - tie_d / 2.0 - err - 15.0
                z_hi_t = max(p[2] for p in pts3d) + tie_d / 2.0 + err + 15.0
                if any(
                    max(q0[2], q1[2]) + rq >= z_lo_t
                    and min(q0[2], q1[2]) - rq <= z_hi_t
                    and any(seg3d_distance(a0, a1, q0, q1) < tie_d / 2.0 + err + rq + 0.4 for a0, a1 in t_segs)
                    for q0, q1, rq, _ in local_obs
                ):
                    continue
                found = (round(z_l, 2), round(z_r, 2))
                break
            if found:
                chosen.append(found)
                z_l, z_r = found
                slope_x = (z_r - z_l) / (x_r - x_l)
                pts3d = [(p[1], p[0], z_l + slope_x * (p[0] - x_l)) for p in path_xs]
                for a0, a1 in zip(pts3d, pts3d[1:]):
                    tie_segs.append((a0, a1, tie_d / 2.0 + err, f"tie_{name}@{z_l:.1f}"))
                z_cursor += req_dz + 1.0
            else:
                z_cursor += 1.0

        span_tie = hypot(x_r - x_l, s_r - s_l)
        cos_shank = (x_r - x_l) / span_tie
        tie_resistance_kn = pi * tie_d**2 / 4.0 * fyd / 1000.0 * cos_shank
        rod_mp_knm = (rod_d**3 / 6.0) * fyd / 1.0e6
        rod_vr_kn = 0.6 * (pi * rod_d**2 / 4.0) * fyd / 1000.0
        max_tie_kn = max_m_knm = max_v_kn = max_res_v = max_res_m = 0.0
        for side_loads, z_supports in ((loads_p, [zr for _, zr in chosen]), (loads_m, [zl for zl, _ in chosen])):
            reac, m_pk, v_pk, res_v, res_m = solve_continuous_rod_on_ties(z_supports, side_loads, rod_d, tie_d, span_tie)
            max_m_knm = max(max_m_knm, m_pk)
            max_v_kn = max(max_v_kn, v_pk)
            max_res_v = max(max_res_v, res_v)
            max_res_m = max(max_res_m, res_m)
            for idx, rval in enumerate(reac):
                zl_t, zr_t = chosen[idx]
                slope = (zr_t - zl_t) / span_tie
                max_tie_kn = max(max_tie_kn, rval * hypot(1.0, slope))
        tie_util = max_tie_kn / tie_resistance_kn if tie_resistance_kn > 0 else float("inf")
        m_util = max_m_knm / rod_mp_knm if rod_mp_knm > 0 else float("inf")
        v_util = max_v_kn / rod_vr_kn if rod_vr_kn > 0 else float("inf")
        clamp_ok = (
            bool(chosen)
            and max(abs(xmin_t), abs(xmax_t)) <= width / 2.0 - cover + 1.0e-6
            and max(tie_util, m_util, v_util) <= SELECTION_LIMIT
            and max_res_v <= 1.0e-6
            and max_res_m <= 1.0e-6
        )
        n_bars = len(loads_p) + len(loads_m)
        total_knuckles += n_bars
        if clamp_ok:
            balanced_knuckles += n_bars
        else:
            unbraced.extend([[1, z] for z, _ in loads_p] + [[-1, z] for z, _ in loads_m])
        clamp_rows.append({
            "clamp": name,
            "rod_stations_mm": [[x_l, s_l], [x_r, s_r]],
            "rod_diameter_mm": rod_d,
            "tie_diameter_mm": tie_d,
            "installed_tie_count": len(chosen),
            "tie_levels_mm": chosen,
            "max_tie_demand_kn": max_tie_kn,
            "tie_resistance_kn": tie_resistance_kn,
            "tie_utilization": tie_util,
            "max_rod_moment_knm": max_m_knm,
            "rod_plastic_moment_knm": rod_mp_knm,
            "rod_moment_utilization": m_util,
            "max_rod_shear_kn": max_v_kn,
            "rod_shear_resistance_kn": rod_vr_kn,
            "rod_shear_utilization": v_util,
            "selection_limit": SELECTION_LIMIT,
            "equilibrium_residual_v_kn": max_res_v,
            "equilibrium_residual_m_knm": max_res_m,
            "satisfied": clamp_ok,
        })

    cage_audit = audit_regional_cage_3d(base_segs + rod_segs + tie_segs, width, height, cover)
    all_clamps_ok = bool(clamp_rows) and all(c["satisfied"] for c in clamp_rows)
    reaction = {
        "scope": "VERTICAL_KNUCKLE_BEARING_RODS_WITH_135_DEG_TENSION_CROSSTIES",
        "selection_limit": SELECTION_LIMIT,
        "clamps": clamp_rows,
        "bar_count": total_knuckles,
        "outside_tie_cone_count": 0 if all_clamps_ok else len(unbraced),
        "directionally_admissible": all_clamps_ok,
        "balanced_hook_pairs": balanced_knuckles,
        "unbraced": unbraced,
        "common_plane_assembly": {
            "layout": "THREE_CLAMP_3D_KNUCKLE_BEARING_ASSEMBLY",
            "candidate_pairs_tested": cage_audit["candidate_pairs_tested"],
            "interfering_pairs": cage_audit["interfering_pairs"],
            "first_interference": cage_audit["first_interference"],
            "satisfied": all_clamps_ok and cage_audit["satisfied"],
        },
    }
    return reaction, cage_audit
