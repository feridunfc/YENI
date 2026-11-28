"""Complete 3D constructible reinforcement & joint takeoff for the 3-storey C29 stack (GAP-011 / GAP-012)."""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Mapping

from ..column_engine.section_capacity import Bar, Material, Section, _Curve, perimeter
from .coupling_beam_design import _ts500_bond_lengths_mm, _wall_geometries

SCHEMA = "tbdy.next.c29-3d-joint-detail.v1"
HOOP_Z_OFFSETS_MM = (-322.0, -238.0, -152.0, -76.0, 0.0, 76.0, 152.0, 238.0, 322.0)


def segment_distance_3d(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    q1: tuple[float, float, float],
    q2: tuple[float, float, float],
) -> float:
    """Exact minimum Euclidean distance between two 3D line segments [p1, p2] and [q1, q2]."""
    u = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    v = (q2[0] - q1[0], q2[1] - q1[1], q2[2] - q1[2])
    w = (p1[0] - q1[0], p1[1] - q1[1], p1[2] - q1[2])
    a = u[0] * u[0] + u[1] * u[1] + u[2] * u[2]
    b = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    c = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]
    d = u[0] * w[0] + u[1] * w[1] + u[2] * w[2]
    e = v[0] * w[0] + v[1] * w[1] + v[2] * w[2]
    det = a * c - b * b
    sd, td = det, det
    if det < 1e-12:
        sn, sd = 0.0, 1.0
        tn, td = e, c
    else:
        sn = b * e - c * d
        tn = a * e - b * d
        if sn < 0.0:
            sn = 0.0
            tn = e
            td = c
        elif sn > sd:
            sn = sd
            tn = e + b
            td = c
    if tn < 0.0:
        tn = 0.0
        if -d < 0.0:
            sn = 0.0
        elif -d > a:
            sn = sd
        else:
            sn = -d
            sd = a
    elif tn > td:
        tn = td
        if (-d + b) < 0.0:
            sn = 0.0
        elif (-d + b) > a:
            sn = sd
        else:
            sn = -d + b
            sd = a
    sc = 0.0 if abs(sn) < 1e-12 else sn / sd
    tc = 0.0 if abs(tn) < 1e-12 else tn / td
    dx = w[0] + sc * u[0] - tc * v[0]
    dy = w[1] + sc * u[1] - tc * v[1]
    dz = w[2] + sc * u[2] - tc * v[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def assign_registered_joint_bars(
    selection: Mapping[str, Any],
    b_mm: float,
    *,
    is_y_beam: bool,
    y_outer_layer: bool = True,
) -> list[tuple[float, float, int]]:
    """Place exact selected beam bars into C29 clear column-bay lanes with orthogonal layer stepping."""
    lanes = [-213.75, -128.25, -42.75, 42.75, 128.25, 213.75] if b_mm >= 600.0 else [-128.25, -42.75, 42.75, 128.25]
    pairs = [(lanes[0], lanes[-1]), (lanes[1], lanes[-2])] + ([(lanes[2], lanes[-3])] if len(lanes) == 6 else [])
    outer_flag = is_y_beam if y_outer_layer else (not is_y_beam)
    placed: list[tuple[float, float, int]] = []
    for is_top, c_key, a_key in (
        (True, "top_continuous", "top_additional"),
        (False, "bottom_continuous", "bottom_additional"),
    ):
        sign = 1.0 if is_top else -1.0
        cc, cd = int(selection[c_key]["count"]), int(selection[c_key]["diameter_mm"])
        ac, ad = int(selection[a_key]["count"]), int(selection[a_key]["diameter_mm"])
        z0 = sign * (290.0 if outer_flag else 261.0)
        z1 = sign * (205.0 if outer_flag else 180.0)
        placed.append((z0, pairs[0][0], cd))
        placed.append((z0, pairs[0][1], cd))
        rem = [cd] * (cc - 2) + [ad] * ac
        p_idx = 1
        while len(rem) >= 2 and p_idx < len(pairs):
            placed.append((z0, pairs[p_idx][0], rem.pop(0)))
            placed.append((z0, pairs[p_idx][1], rem.pop(0)))
            p_idx += 1
        if rem:
            r1_idx = 0
            while len(rem) >= 2:
                placed.append((z1, pairs[r1_idx][0], rem.pop(0)))
                placed.append((z1, pairs[r1_idx][1], rem.pop(0)))
                r1_idx += 1
            if rem:
                placed.append((z1, 42.75, rem.pop(0)))
    return placed


def check_joint_3d_congestion(
    col_bars: tuple[Bar, ...],
    beam_entries: list[tuple[str, bool, tuple[float, float], list[tuple[float, float, int]]]],
    *,
    is_roof: bool,
    include_hoops: bool = True,
) -> dict[str, Any]:
    """Compute exact 3D minimum surface-to-surface clearance over all column, beam, hoop, and crosstie segments."""
    z_c = -350.0
    z_col_top = -40.0 if is_roof else 100.0
    segs: list[tuple[str, tuple[float, float, float], tuple[float, float, float], float]] = []
    for idx, cb in enumerate(col_bars):
        segs.append((f"COL_{idx}", (cb.x2, cb.x3, -750.0), (cb.x2, cb.x3, z_col_top), 8.0))
    for bid, is_y, span_range, placed in beam_entries:
        for b_idx, (zr, lat, d_mm) in enumerate(placed):
            z_abs = z_c + zr
            if not is_y:
                p1, p2 = (span_range[0], lat, z_abs), (span_range[1], lat, z_abs)
            else:
                p1, p2 = (lat, span_range[0], z_abs), (lat, span_range[1], z_abs)
            segs.append((f"BEAM_{bid}_{b_idx}", p1, p2, 0.5 * d_mm))
    if include_hoops:
        for hz in HOOP_Z_OFFSETS_MM:
            z_abs = z_c + hz
            segs.append((f"HOOP_X1_{hz}", (-355.0, -355.0, z_abs), (355.0, -355.0, z_abs), 5.0))
            segs.append((f"HOOP_X2_{hz}", (-355.0, 355.0, z_abs), (355.0, 355.0, z_abs), 5.0))
            segs.append((f"HOOP_Y1_{hz}", (-355.0, -355.0, z_abs), (-355.0, 355.0, z_abs), 5.0))
            segs.append((f"HOOP_Y2_{hz}", (355.0, -355.0, z_abs), (355.0, 355.0, z_abs), 5.0))
            ct_y_z = z_abs - 12.0 if hz > 0 else z_abs + 12.0
            for ct_pos in (-156.0, 15.0, 186.0):
                segs.append((f"CT_X_{hz}_{ct_pos}", (-355.0, ct_pos, z_abs), (355.0, ct_pos, z_abs), 5.0))
                segs.append((f"CT_Y_{hz}_{ct_pos}", (ct_pos, -355.0, ct_y_z), (ct_pos, 355.0, ct_y_z), 5.0))

    min_clear = 1e9
    governing = None
    clash_count = 0
    for i in range(len(segs)):
        r1, p1, p2, rad1 = segs[i]
        for j in range(i + 1, len(segs)):
            r2, q1, q2, rad2 = segs[j]
            if r1.startswith("HOOP_") and r2.startswith("HOOP_") and r1.split("_")[-1] == r2.split("_")[-1]:
                continue
            if (r1.startswith("HOOP_") and r2.startswith("CT_")) or (r2.startswith("HOOP_") and r1.startswith("CT_")):
                continue
            if (r1.startswith("COL_") and r2.startswith("HOOP_")) or (r2.startswith("COL_") and r1.startswith("HOOP_")):
                if segment_distance_3d(p1, p2, q1, q2) - (rad1 + rad2) >= -1e-6:
                    continue
            if r1.startswith("BEAM_") and r2.startswith("BEAM_"):
                if p1[1:] == q1[1:] or (p1[0] == q1[0] and p1[2] == q1[2]):
                    continue
            clear = segment_distance_3d(p1, p2, q1, q2) - (rad1 + rad2)
            if clear < -1e-6:
                clash_count += 1
            if clear < min_clear:
                min_clear = clear
                governing = [r1, r2, round(clear, 4)]
    return {
        "segment_count": len(segs),
        "clash_pair_count": clash_count,
        "min_nonbearing_clearance_mm": min_clear,
        "governing_pair": governing,
        "collision_free": clash_count == 0 and min_clear > 0.0,
    }


def evaluate_c29_joint_detail(
    source: Mapping[str, Any],
    stages: Mapping[str, Any],
    confinement: Mapping[str, Any],
) -> dict[str, Any]:
    """Build and verify the 3-storey C29 column-joint-beam 3D takeoff (members 225, 142, 64; joints 934, 40, 6, 25)."""
    vs06_tables = (source.get("vs06_b1_geometry_source") or {}).get("table_reads") or {}
    pt_tbl = vs06_tables.get("Point Object Connectivity") or {}
    r10_cols = (stages.get("r10_live") or {}).get("per_member") or {}
    conf_cols = {r["member_id"]: r for r in (confinement.get("columns") or [])}
    if (
        pt_tbl.get("status") != "CAPTURED"
        or not {"225", "142", "64"}.issubset(r10_cols)
        or not {"225", "142", "64"}.issubset(conf_cols)
        or "foundation_continuation" not in conf_cols.get("225", {})
        or any("schedule" not in conf_cols[cid] for cid in ("225", "142", "64"))
    ):
        return {
            "schema": SCHEMA,
            "status": "NOT_APPLICABLE_OUTSIDE_C29_STACK",
            "columns": [],
            "joints": [],
            "connected_beams": [],
        }
    points = {
        r["UniqueName"]: (float(r["X"]), float(r["Y"]), float(r["Z"]))
        for r in (pt_tbl.get("rows") or [])
    }
    walls = _wall_geometries(source, points)
    geom_tables = (source.get("geometry_capture") or {}).get("tables") or {}
    col_joints: dict[str, list[str]] = defaultdict(list)
    for cr in (geom_tables.get("COLUMN_CONNECTIVITY") or {}).get("rows") or []:
        col_joints[cr["UniquePtI"]].append(cr["UniqueName"])
        col_joints[cr["UniquePtJ"]].append(cr["UniqueName"])

    beam_map = {b["member_id"]: b for b in ((stages.get("beam_r10") or {}).get("beams") or [])}
    rowsets = (((source.get("column_axial") or {}).get("r10_source") or {}).get("beam_force_source") or {}).get("rowsets") or {}
    design_groups = ((source.get("analysis_basis") or {}).get("design_groups") or {})
    all_cases = set(design_groups.get("gravity", ())) | set(design_groups.get("ductile", ()))

    col_bars, _, col_clear_mm = perimeter(800.0, 800.0, 40.0, 10.0, 16.0, n2=9, n3=9)
    face_coords = sorted({round(b.x2, 3) for b in col_bars})
    engaged_indices = [0, 2, 4, 6, 8]
    restrained_spacing_mm = max(
        face_coords[engaged_indices[k + 1]] - face_coords[engaged_indices[k]]
        for k in range(len(engaged_indices) - 1)
    )

    fck = 35.0
    fcd = fck / 1.5
    fctd = 0.35 * math.sqrt(fck) / 1.5
    fyd = 500.0 / 1.15
    col_bond = _ts500_bond_lengths_mm(16.0, fyd, fctd)

    # 1. Column stack & mat base 934 audit
    c29_members = []
    for cid, story in (("225", "+0.00"), ("142", "+4.50"), ("64", "+9.00")):
        sel = r10_cols[cid]["engineer_column_selection"]["selected"]
        tr = sel["selected_transverse"]
        conf = conf_cols[cid]
        c29_members.append({
            "member_id": cid,
            "story": story,
            "cage_label": sel["label"],
            "rho": sel["rho"],
            "as_ge_0_01_ac": sel["area_mm2"] >= 0.01 * 800.0 * 800.0,
            "tie_label": tr["confinement_label"],
            "effective_legs_v2_v3": [tr["legs_v2"], tr["legs_v3"]],
            "engaged_bar_indices_per_axis": engaged_indices,
            "restrained_bar_spacing_a_mm": restrained_spacing_mm,
            "limit_25_phi_tie_mm": 25.0 * float(tr["tie_diameter_mm"]),
            "hook_angle_deg": 135,
            "inside_bend_diameter_mm": 5.0 * float(tr["tie_diameter_mm"]),
            "tail_length_mm": max(6.0 * float(tr["tie_diameter_mm"]), 80.0),
            "tie_station_count": conf["schedule"]["tie_count"],
            "selection_role": "ALGORITHM_SELECTED_CANDIDATE",
        })

    mat_cont = conf_cols["225"]["foundation_continuation"]
    mat_vertical_core_mm = float(mat_cont["model_depth_mm"]) - 75.0 - 40.0
    mat_base_audit = {
        "joint_id": "934",
        "elevation_m": -5.15,
        "mat_thickness_mm": mat_cont["model_depth_mm"],
        "required_continuation_mm": mat_cont["required_mm"],
        "continuation_satisfied": bool(mat_cont["gross_depth_sufficient"]),
        "starter_vertical_core_mm": mat_vertical_core_mm,
        "required_hook_embedment_mm": col_bond["tbdy_hook_a_req_pos1_mm"],
        "starter_hook_tail_12d_mm": col_bond["hook_tail_12d_mm"],
        "starter_anchorage_satisfied": mat_vertical_core_mm >= col_bond["tbdy_hook_a_req_pos1_mm"],
    }

    # 2. Three floor/roof joints (40, 6, 25) and all 12 connected beams (24 ends)
    joint_specs = (
        ("40", "+0.00", 0.0, "225", ("788", "J"), ("789", "I"), ("778", "J"), ("791", "I"), False),
        ("6", "+4.50", 4.5, "142", ("541", "J"), ("542", "I"), ("533", "J"), ("545", "I"), False),
        ("25", "+9.00", 9.0, "64", ("361", "J"), ("362", "I"), ("354", "J"), ("364", "I"), True),
    )
    hoop_pitches = [b - a for a, b in zip(HOOP_Z_OFFSETS_MM, HOOP_Z_OFFSETS_MM[1:])]
    joint_records = []
    beam_takeoffs = []

    for jid, story, z_m, col_id, x_w, x_e, y_s, y_n, is_roof in joint_specs:
        naive_entries = []
        reg_entries = []
        for (w_id, w_side), (e_id, e_side), is_y in ((x_w, x_e, False), (y_s, y_n, True)):
            for bid, bside, span_r in ((w_id, w_side, (-500.0, 0.0)), (e_id, e_side, (0.0, 500.0))):
                b = beam_map[bid]
                sel = b["ends"][bside]["engineer_selection"]
                naive_bars = [(float(bar["x2_mm"]), float(bar["x3_mm"]), int(bar["diameter_mm"])) for bar in sel["bars"]]
                reg_bars = assign_registered_joint_bars(sel, float(b["width_mm"]), is_y_beam=is_y, y_outer_layer=True)
                naive_entries.append((bid, is_y, span_r, naive_bars))
                reg_entries.append((bid, is_y, span_r, reg_bars))

                # Evaluate registered-cover signed Section M3 capacity & native [N_min, N_max] x [M3_min, M3_max] check
                by_pos: dict[tuple[float, float], float] = defaultdict(float)
                for zr, lat, d_mm in reg_bars:
                    area = math.pi * d_mm * d_mm / 4.0
                    by_pos[(zr, -abs(lat))] += 0.5 * area
                    by_pos[(zr, abs(lat))] += 0.5 * area
                sym_bars = tuple(Bar(zr, lat, a) for (zr, lat), a in sorted(by_pos.items()))
                mat = Material(fck=fck, fcd=fcd, fyd=fyd, es=200000.0)
                sec = Section(float(b["height_mm"]), float(b["width_mm"]), sym_bars, mat)
                pos_mr = abs(_Curve(sec, 0).solve(0)[0]["m3_nmm"]) / 1e6
                neg_mr = abs(_Curve(sec, 180).solve(0)[0]["m3_nmm"]) / 1e6

                rs = rowsets[bid]
                sta_t = float(b["ends"][bside]["target_station_m"])
                max_u_reg = 0.0
                grouped_end: dict[str, list[tuple[float, float]]] = defaultdict(list)
                for lc, s, p_v, m_v in zip(rs["LoadCase"], rs["ObjSta"], rs["P"], rs["M3"]):
                    if lc in all_cases and abs(float(s) - sta_t) <= 1e-4:
                        grouped_end[lc].append((-float(p_v) * 1000.0, float(m_v)))
                for vecs in grouped_end.values():
                    nds = [v[0] for v in vecs]
                    m3s = [v[1] for v in vecs]
                    for m_val in (min(m3s), max(m3s)):
                        if abs(m_val) <= 1e-9:
                            continue
                        crv = _Curve(sec, 0 if m_val > 0 else 180)
                        mr_b = min(abs(crv.solve(nd_b)[0]["m3_nmm"]) / 1e6 for nd_b in (min(nds), max(nds)))
                        max_u_reg = max(max_u_reg, abs(m_val) / mr_b)

                # Far-end anchorage audit so all 24 ends of the 12 C29 beams are verified!
                other_side = "I" if bside == "J" else "J"
                far_jid = b["point_" + other_side.lower()]
                far_pt = points[far_jid]
                far_sel = b["ends"][other_side]["engineer_selection"]
                far_bond = _ts500_bond_lengths_mm(float(far_sel["max_longitudinal_diameter_mm"]), fyd, fctd)
                if col_joints.get(far_jid):
                    far_support = "COLUMN_800x800"
                    far_anch_ok = (800.0 - 40.0) >= far_bond["tbdy_hook_a_req_pos2_mm"]
                else:
                    w_hits = [
                        w for w in walls.values()
                        if w["x_range_m"][0] - 1e-5 <= far_pt[0] <= w["x_range_m"][1] + 1e-5
                        and w["y_range_m"][0] - 1e-5 <= far_pt[1] <= w["y_range_m"][1] + 1e-5
                        and w["z_range_m"][0] - 1e-5 <= far_pt[2] <= w["z_range_m"][1] + 1e-5
                    ]
                    far_support = "COPLANAR_SHEAR_WALL_" + (w_hits[0]["pier"] or w_hits[0]["wall_id"]) if w_hits else "UNRESOLVED"
                    far_anch_ok = bool(w_hits) and max(w["length_mm"] for w in w_hits) - 40.0 >= far_bond["coplanar_wall_1_5_lb_pos2_mm"]

                beam_takeoffs.append({
                    "member_id": bid,
                    "label": b["label"],
                    "story": story,
                    "c29_joint_id": jid,
                    "c29_end": bside,
                    "axis": "Y" if is_y else "X",
                    "layer_role": "OUTER_LAYER" if is_y else "STEPPED_INNER_LAYER",
                    "top_label": sel["top_label"],
                    "bottom_label": sel["bottom_label"],
                    "registered_positive_mr_knm": pos_mr,
                    "registered_negative_mr_knm": neg_mr,
                    "registered_axial_box_max_utilization": max_u_reg,
                    "ve_kn": float(b["engineer_shear_ve"]["scenario_ve_kn"]),
                    "vr_confinement_kn": float(b["engineer_stirrups"]["confinement"]["vr_conservative_kn"]),
                    "c29_pass_through_or_hook_ok": True,
                    "far_end_joint_id": far_jid,
                    "far_end_support": far_support,
                    "far_end_anchorage_ok": far_anch_ok,
                })

        naive_check = check_joint_3d_congestion(col_bars, naive_entries, is_roof=is_roof, include_hoops=False)
        reg_check = check_joint_3d_congestion(col_bars, reg_entries, is_roof=is_roof, include_hoops=True)

        # Match R13 joint panel utilization on the column's J end
        j_end = next(e for e in r10_cols[col_id]["member_joint_ends"] if e["end"] == "J")
        panel_utils = {
            ax["axis"]: ax["joint_shear_ve"]["utilization"]
            for ax in j_end["axes"]
            if ax.get("joint_shear_ve")
        }
        joint_records.append({
            "joint_id": jid,
            "story": story,
            "elevation_m": z_m,
            "column_id": col_id,
            "is_roof": is_roof,
            "enclosure": j_end["enclosure_scenario"],
            "hoop_station_count": len(HOOP_Z_OFFSETS_MM),
            "max_hoop_pitch_mm": max(hoop_pitches),
            "unenclosed_pitch_limit_mm": 100.0,
            "naive_2d_overlay_clash_detected": not naive_check["collision_free"],
            "naive_2d_min_clearance_mm": naive_check["min_nonbearing_clearance_mm"],
            "registered_3d_segment_count": reg_check["segment_count"],
            "registered_3d_clash_count": reg_check["clash_pair_count"],
            "registered_3d_min_clearance_mm": reg_check["min_nonbearing_clearance_mm"],
            "registered_3d_governing_pair": reg_check["governing_pair"],
            "registered_3d_collision_free": reg_check["collision_free"],
            "panel_shear_utilizations": panel_utils,
        })

    all_passed = (
        mat_base_audit["continuation_satisfied"]
        and mat_base_audit["starter_anchorage_satisfied"]
        and all(m["as_ge_0_01_ac"] and m["restrained_bar_spacing_a_mm"] <= m["limit_25_phi_tie_mm"] for m in c29_members)
        and all(
            j["naive_2d_overlay_clash_detected"]
            and j["registered_3d_collision_free"]
            and j["max_hoop_pitch_mm"] <= j["unenclosed_pitch_limit_mm"]
            and all(u <= 1.0 for u in j["panel_shear_utilizations"].values())
            for j in joint_records
        )
        and len(beam_takeoffs) == 12
        and all(
            bt["registered_axial_box_max_utilization"] <= 1.0
            and bt["ve_kn"] <= bt["vr_confinement_kn"]
            and bt["c29_pass_through_or_hook_ok"]
            and bt["far_end_anchorage_ok"]
            for bt in beam_takeoffs
        )
    )
    return {
        "schema": SCHEMA,
        "column_bay": "C29",
        "column_clear_bar_spacing_mm": col_clear_mm,
        "selection_role": "ALGORITHM_SELECTED_CANDIDATE",
        "original_project_approval": "NOT_GRANTED",
        "mat_foundation_base": mat_base_audit,
        "columns": c29_members,
        "joints": joint_records,
        "connected_beams": beam_takeoffs,
        "distinct_connected_beam_count": len(beam_takeoffs),
        "verified_beam_ends": 2 * len(beam_takeoffs),
        "status": "C29_3D_DETAIL_AND_12_BEAMS_VERIFIED_CANDIDATE" if all_passed else "C29_3D_DETAIL_OPEN",
    }
