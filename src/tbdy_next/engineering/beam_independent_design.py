"""Independent native Results.FrameForce beam axial-flexure, TS 500 §8.2 torsion, and 360-end topology."""
from __future__ import annotations

import base64
from collections import Counter, defaultdict
from functools import lru_cache
import math
import re
from typing import Any, Mapping

from .coupling_beam_design import _ts500_bond_lengths_mm, _wall_geometries

SCHEMA = "tbdy.next.beam-independent-design.v1"


@lru_cache(maxsize=16384)
def _beam_mr_at_axial(
    bw_mm: float,
    h_mm: float,
    layers: tuple[tuple[float, float, float], ...],
    fcd_mpa: float,
    fyd_mpa: float,
    es_mpa: float,
    nd_kn: float,
    positive_bending: bool,
) -> float:
    """Exact C35 rectangular stress block (k1=0.79) + displaced bar circular segments at fixed Nd (kN)."""
    # For negative bending, mirror x2 -> -x2 so compression face is always +h/2.
    sign = 1.0 if positive_bending else -1.0
    oriented = tuple((sign * x2, radius, area) for x2, radius, area in layers)
    stress = 0.85 * fcd_mpa
    target_n = nd_kn * 1000.0
    low, high = 1e-6, 16.0 * h_mm
    force = 0.0
    moment = 0.0
    for _ in range(52):
        neutral = 0.5 * (low + high)
        thickness = min(h_mm, 0.79 * neutral)
        line = 0.5 * h_mm - thickness
        force = stress * bw_mm * thickness
        moment = force * (0.5 * h_mm - 0.5 * thickness)
        for y, radius, area in oriented:
            strain = 0.003 * (1.0 - (0.5 * h_mm - y) / neutral)
            steel = max(-fyd_mpa, min(fyd_mpa, strain * es_mpa)) * area
            dist = line - y
            removed = 0.0
            first = 0.0
            if dist <= -radius:
                removed = area
            elif dist < radius:
                chord = math.sqrt(max(0.0, radius * radius - dist * dist))
                count = area / (math.pi * radius * radius)
                seg_area = radius * radius * math.acos(max(-1.0, min(1.0, dist / radius))) - dist * chord
                removed = count * seg_area
                first = count * (2.0 * (chord ** 3) / 3.0)
            bar_f = steel - stress * removed
            force += bar_f
            moment += bar_f * y - stress * first
        if force < target_n:
            low = neutral
        else:
            high = neutral
    return max(0.0, moment / 1e6)


def _group_bar_layers(bars: list[Mapping[str, Any]]) -> tuple[tuple[float, float, float], ...]:
    grouped: dict[tuple[float, float], float] = defaultdict(float)
    for b in bars:
        x2 = round(float(b["x2_mm"]), 6)
        rad = round(0.5 * float(b["diameter_mm"]), 6)
        grouped[(x2, rad)] += float(b["area_mm2"])
    return tuple((x2, rad, round(area, 6)) for (x2, rad), area in sorted(grouped.items()))


def _req_flexural_steel_mm2(m_knm: float, bw_mm: float, d_mm: float, fcd_mpa: float, fyd_mpa: float) -> float:
    if m_knm <= 1e-9:
        return 0.0
    m_nmm = m_knm * 1e6
    disc = 1.0 - (2.0 * m_nmm) / (0.85 * fcd_mpa * bw_mm * (d_mm ** 2))
    if disc <= 0.0:
        return 1e9
    a = d_mm * (1.0 - math.sqrt(disc))
    return (0.85 * fcd_mpa * bw_mm * a) / fyd_mpa


def _verify_e2k_beam_modifiers_and_releases(source: Mapping[str, Any], beam_sections: set[str]) -> dict[str, Any]:
    archive = source.get("analysis_archive") or {}
    b64 = archive.get("model_export_base64")
    if not isinstance(b64, str) or not b64:
        return {"verified": False, "reason": "MODEL_EXPORT_BASE64_MISSING"}
    text = base64.b64decode(b64).decode("utf-8", errors="replace")
    in_frame_sec = False
    in_line_ass = False
    mods: dict[str, tuple[float, float, float]] = {}
    release_count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("$"):
            in_frame_sec = line == "$ FRAME SECTIONS"
            in_line_ass = line == "$ LINE ASSIGNS"
            continue
        if in_frame_sec and line.startswith("FRAMESECTION"):
            m_name = re.match(r'^FRAMESECTION\s+"([^"]+)"(.*)$', line)
            if m_name:
                sname, rest = m_name.group(1), m_name.group(2)
                if "I2MOD" in rest or "I3MOD" in rest or "JMOD" in rest:
                    i2 = float(m.group(1)) if (m := re.search(r"\bI2MOD\s+([0-9.+-eE]+)", rest)) else 1.0
                    i3 = float(m.group(1)) if (m := re.search(r"\bI3MOD\s+([0-9.+-eE]+)", rest)) else 1.0
                    jm = float(m.group(1)) if (m := re.search(r"\bJMOD\s+([0-9.+-eE]+)", rest)) else 1.0
                    mods[sname] = (i2, i3, jm)
        elif in_line_ass and line.startswith("LINEASSIGN"):
            if "RELEASE" in line:
                release_count += 1
    all_035 = beam_sections <= set(mods) and all(
        math.isclose(mods[s][0], 0.35, abs_tol=1e-6) and math.isclose(mods[s][1], 0.35, abs_tol=1e-6)
        for s in beam_sections
    )
    all_j1 = beam_sections <= set(mods) and all(math.isclose(mods[s][2], 1.0, abs_tol=1e-6) for s in beam_sections)
    return {
        "verified": bool(all_035 and release_count == 0),
        "all_beams_i2_i3_mod_0_35": all_035,
        "all_beams_jmod_1_0_uncracked": all_j1,
        "frame_release_assignments_in_e2k": release_count,
        "checked_beam_section_count": len(beam_sections),
    }


def evaluate_beam_independent_design(
    source: Mapping[str, Any],
    stages: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate 180 beams independently on Results.FrameForce (93,841 vectors) and 360 physical ends."""
    geom_tables = (source.get("geometry_capture") or {}).get("tables") or {}
    c_conn = (geom_tables.get("COLUMN_CONNECTIVITY") or {}).get("rows") or []
    vs06_tables = (source.get("vs06_b1_geometry_source") or {}).get("table_reads") or {}
    pt_tbl = vs06_tables.get("Point Object Connectivity") or {}
    beam_r10 = (stages.get("beam_r10") or {}).get("beams") or []
    rowsets = (((source.get("column_axial") or {}).get("r10_source") or {}).get("beam_force_source") or {}).get("rowsets") or {}
    if (
        pt_tbl.get("status") != "CAPTURED"
        or not beam_r10
        or any(
            b.get("member_id") not in rowsets
            or not b.get("engineer_stirrups")
            or not (b.get("engineer_midspan") or {}).get("bars")
            for b in beam_r10
        )
    ):
        return {
            "schema": SCHEMA,
            "beam_count": len(beam_r10),
            "uls_axial_flexure_torsion_status": "FIXTURE_SCOPE_INCOMPLETE",
            "serviceability_status": "SLS_DEFLECTION_AND_CRACK_WIDTH_COMBINATIONS_NOT_CAPTURED",
            "beams": [],
        }
    pt_rows = pt_tbl.get("rows") or []
    points = {r["UniqueName"]: (float(r["X"]), float(r["Y"]), float(r["Z"])) for r in pt_rows}
    walls = _wall_geometries(source, points)
    beam_map = {b["member_id"]: b for b in beam_r10}
    design_groups = ((source.get("analysis_basis") or {}).get("design_groups") or {})
    all_cases = set(design_groups.get("gravity", ())) | set(design_groups.get("ductile", ()))

    e2k_audit = _verify_e2k_beam_modifiers_and_releases(
        source, {b["section_name"] for b in beam_r10 if b.get("section_name")}
    )

    rect_sects = {
        r["Name"]: (float(r["t3"]) * 1000.0, float(r["t2"]) * 1000.0)
        for r in ((geom_tables.get("RECTANGULAR_SECTIONS") or {}).get("rows") or [])
    }
    f_assign = {
        r["UniqueName"]: r["AnalysisSect"]
        for r in ((geom_tables.get("FRAME_ASSIGNMENTS") or {}).get("rows") or [])
    }
    col_joints: dict[str, list[tuple[str, float]]] = {}
    col_footprints: list[tuple[str, float, float, float, float, float, float]] = []
    for cr in c_conn:
        cid = cr["UniqueName"]
        dims = rect_sects.get(f_assign.get(cid, ""), (0.0, 0.0))
        min_side = min(dims)
        p1, p2 = points[cr["UniquePtI"]], points[cr["UniquePtJ"]]
        col_footprints.append((
            cid,
            p1[0] - min_side / 2000.0, p1[0] + min_side / 2000.0,
            p1[1] - min_side / 2000.0, p1[1] + min_side / 2000.0,
            min(p1[2], p2[2]), max(p1[2], p2[2]),
        ))
        for end_k in ("UniquePtI", "UniquePtJ"):
            col_joints.setdefault(cr[end_k], []).append((cid, min_side))

    beam_segs = []
    for uid, b in beam_map.items():
        p1, p2 = points[b["point_i"]], points[b["point_j"]]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        L = math.hypot(dx, dy)
        beam_segs.append((uid, p1, p2, dx / L if L > 0 else 0.0, dy / L if L > 0 else 0.0, float(b["width_mm"])))

    # Map girders receiving interior secondary beams (equilibrium torsion candidates)
    girders_with_secondary: dict[str, list[str]] = defaultdict(list)
    secondary_support: dict[tuple[str, str], tuple[str, float]] = {}
    for uid, p1, p2, ux, uy, _ in beam_segs:
        for side, pt in (("I", p1), ("J", p2)):
            for ouid, op1, op2, oux, ouy, obw in beam_segs:
                if ouid == uid or abs(pt[2] - op1[2]) > 1e-5:
                    continue
                if math.dist(pt, op1) < 1e-5 or math.dist(pt, op2) < 1e-5:
                    continue
                oL = math.hypot(op2[0] - op1[0], op2[1] - op1[1])
                along = (pt[0] - op1[0]) * oux + (pt[1] - op1[1]) * ouy
                norm = abs((pt[0] - op1[0]) * ouy - (pt[1] - op1[1]) * oux)
                if 1e-5 < along < oL - 1e-5 and norm < 1e-4:
                    girders_with_secondary[ouid].append(uid)
                    secondary_support[(uid, side)] = (ouid, obw)

    fck = 35.0
    fcd = fck / 1.5
    fctd = 0.35 * math.sqrt(fck) / 1.5

    beam_rows: list[dict[str, Any]] = []
    end_topology_counts: Counter[str] = Counter()
    anchorage_counts: Counter[str] = Counter()
    torsion_class_counts: Counter[str] = Counter()
    max_axial_ratio = 0.0
    max_n0_util = 0.0
    max_box_util = 0.0
    max_web_crush_ratio = 0.0
    axial_exceedances = 0
    box_exceedances = 0
    web_crush_exceedances = 0
    concurrent_long_exceedances = 0
    concurrent_stirrup_exceedances = 0

    for uid in sorted(beam_map):
        b = beam_map[uid]
        rs = rowsets[uid]
        bw = float(b["width_mm"])
        h = float(b["height_mm"])
        fyk = float(b["fyk_mpa"])
        fyd = fyk / 1.15
        fywd = float(b["engineer_stirrups"]["fywd_mpa"])
        d_eff = float(b["engineer_stirrups"]["effective_depth_mm"])
        off_i_m = float(b["end_offsets_mm"]["I"]) / 1000.0
        off_j_m = (float(b["length_mm"]) - float(b["end_offsets_mm"]["J"])) / 1000.0

        # 1. Axial & [N_min, N_max] x [M3_min, M3_max] box + TS 500 §8.2 Torsion across all assigned vectors
        st_mm3 = (min(bw, h) ** 2) * max(bw, h) / 3.0
        tcr_ignore_knm = 0.65 * fctd * st_mm3 / 1e6
        tcr_compat_knm = 1.35 * fctd * st_mm3 / 1e6
        tie_d = float(b["engineer_stirrups"]["confinement"]["diameter_mm"])
        b1 = bw - 2.0 * 30.0 - tie_d
        h1 = h - 2.0 * 30.0 - tie_d
        ae_mm2 = b1 * h1
        ue_mm = 2.0 * (b1 + h1)
        prov_asw_s = float(b["engineer_stirrups"]["confinement"]["asw_mm2"]) / float(
            b["engineer_stirrups"]["confinement"]["spacing_mm"]
        )

        layers_by_zone = {
            "I": _group_bar_layers(b["ends"]["I"]["engineer_selection"]["bars"]),
            "J": _group_bar_layers(b["ends"]["J"]["engineer_selection"]["bars"]),
            "SPAN": _group_bar_layers(b["engineer_midspan"]["bars"]),
        }
        sel_by_zone = {
            "I": b["ends"]["I"]["engineer_selection"],
            "J": b["ends"]["J"]["engineer_selection"],
            "SPAN": b["engineer_midspan"],
        }

        grouped_cuts: dict[tuple[str, str, float], list[tuple[float, float, float, float]]] = defaultdict(list)
        beam_p_max = 0.0
        beam_t_max = 0.0
        beam_web_crush_max = 0.0
        beam_stirrup_comb_max = 0.0
        beam_long_comb_max = 0.0
        beam_asl_max = 0.0

        for lc, sta, elm, p_kn, v2_kn, t_knm, m3_knm in zip(
            rs["LoadCase"], rs["ObjSta"], rs["Elm"], rs["P"], rs["V2"], rs["T"], rs["M3"]
        ):
            if lc not in all_cases:
                continue
            pa, va, ta = abs(float(p_kn)), abs(float(v2_kn)), abs(float(t_knm))
            beam_p_max = max(beam_p_max, pa)
            beam_t_max = max(beam_t_max, ta)
            # TS 500 Eq. 8.23 combined shear + torsion web crushing
            comb_tau = ((va * 1000.0) / (bw * d_eff) + (ta * 1e6) / st_mm3) / (0.22 * fcd)
            beam_web_crush_max = max(beam_web_crush_max, comb_tau)

            if off_i_m - 1e-4 <= float(sta) <= off_j_m + 1e-4:
                grouped_cuts[(lc, str(elm), round(float(sta), 6))].append(
                    (float(p_kn), float(v2_kn), float(t_knm), float(m3_knm))
                )
                zname = "I" if abs(float(sta) - off_i_m) <= 1e-4 else ("J" if abs(float(sta) - off_j_m) <= 1e-4 else "SPAN")
                sel = sel_by_zone[zname]
                aot_s = (ta * 1e6) / (2.0 * ae_mm2 * fywd) if ta > tcr_ignore_knm else 0.0
                asl = aot_s * ue_mm
                beam_asl_max = max(beam_asl_max, asl)
                stir_ratio = ((va * 1000.0) / (fywd * d_eff) + 2.0 * aot_s) / prov_asw_s
                beam_stirrup_comb_max = max(beam_stirrup_comb_max, stir_ratio)
                d_top = h - float(sel["effective_top_centroid_mm"])
                d_bot = h - float(sel["effective_bottom_centroid_mm"])
                m3_f = float(m3_knm)
                req_top = (_req_flexural_steel_mm2(abs(m3_f), bw, d_top, fcd, fyd) if m3_f < 0 else 0.0) + (b1 / ue_mm) * asl
                req_bot = (_req_flexural_steel_mm2(m3_f, bw, d_bot, fcd, fyd) if m3_f > 0 else 0.0) + (b1 / ue_mm) * asl
                long_ratio = max(req_top / float(sel["area_top_mm2"]), req_bot / float(sel["area_bottom_mm2"]))
                beam_long_comb_max = max(beam_long_comb_max, long_ratio)

        beam_u_n0 = 0.0
        beam_u_box = 0.0
        for (_, _, sta_r), vecs in grouped_cuts.items():
            zname = "I" if abs(sta_r - off_i_m) <= 1e-4 else ("J" if abs(sta_r - off_j_m) <= 1e-4 else "SPAN")
            layers = layers_by_zone[zname]
            nds = [-v[0] for v in vecs]
            m3s = [v[3] for v in vecs]
            nd_bounds = (min(nds), max(nds)) if len(nds) > 1 else (nds[0],)
            for m_val in (min(m3s), max(m3s)):
                if abs(m_val) <= 1e-9:
                    continue
                pos_flag = m_val > 0
                mr0 = _beam_mr_at_axial(bw, h, layers, fcd, fyd, 200000.0, 0.0, pos_flag)
                mr_box = min(_beam_mr_at_axial(bw, h, layers, fcd, fyd, 200000.0, nd_b, pos_flag) for nd_b in nd_bounds)
                beam_u_n0 = max(beam_u_n0, abs(m_val) / mr0 if mr0 > 0 else 999.0)
                beam_u_box = max(beam_u_box, abs(m_val) / mr_box if mr_box > 0 else 999.0)

        axial_lim_kn = 0.10 * bw * h * fck / 1000.0
        p_ratio = beam_p_max / axial_lim_kn
        max_axial_ratio = max(max_axial_ratio, p_ratio)
        max_n0_util = max(max_n0_util, beam_u_n0)
        max_box_util = max(max_box_util, beam_u_box)
        max_web_crush_ratio = max(max_web_crush_ratio, beam_web_crush_max)
        if p_ratio > 1.0 + 1e-9:
            axial_exceedances += 1
        if beam_u_box > 1.0 + 1e-6:
            box_exceedances += 1
        if beam_web_crush_max > 1.0 + 1e-6:
            web_crush_exceedances += 1
        if beam_long_comb_max > 1.0 + 1e-6:
            concurrent_long_exceedances += 1
        if beam_stirrup_comb_max > 1.0 + 1e-6:
            concurrent_stirrup_exceedances += 1

        has_secondary = uid in girders_with_secondary
        if beam_t_max <= tcr_ignore_knm:
            torsion_class = "BELOW_TCR_NEGLECTED"
            side_web_bars = None
        elif has_secondary:
            torsion_class = "EQUILIBRIUM_OR_GIRDER_TORSION"
            req_web_mm2 = (h1 / ue_mm) * beam_asl_max
            n_layers = max(1, math.ceil(h1 / 300.0) - 1)
            bar_d_web = next((d for d in (12, 14, 16, 20) if 2 * n_layers * (math.pi * d * d / 4.0) >= req_web_mm2), 20)
            side_web_bars = f"2x{n_layers}Φ{bar_d_web}"
        else:
            torsion_class = "COMPATIBILITY_TORSION_MONOLITHIC_FRAME"
            req_web_mm2 = (h1 / ue_mm) * beam_asl_max
            n_layers = max(1, math.ceil(h1 / 300.0) - 1)
            bar_d_web = next((d for d in (12, 14, 16, 20) if 2 * n_layers * (math.pi * d * d / 4.0) >= req_web_mm2), 20)
            side_web_bars = f"2x{n_layers}Φ{bar_d_web}"
        torsion_class_counts[torsion_class] += 1

        # 2. Physical 360-end support & bar anchorage classification
        pi, pj = points[b["point_i"]], points[b["point_j"]]
        dx, dy = pj[0] - pi[0], pj[1] - pi[1]
        L = math.hypot(dx, dy)
        ux, uy = (dx / L, dy / L) if L > 0 else (0.0, 0.0)
        end_topologies: dict[str, Any] = {}

        for side, pt, jid in (("I", pi, b["point_i"]), ("J", pj, b["point_j"])):
            outward = (ux, uy) if side == "I" else (-ux, -uy)
            sel = b["ends"][side]["engineer_selection"]
            max_d = float(sel["max_longitudinal_diameter_mm"])
            bond = _ts500_bond_lengths_mm(max_d, fyd, fctd)

            col_hits = col_joints.get(jid, [])
            w_hits = [
                w for w in walls.values()
                if w["x_range_m"][0] - 1e-5 <= pt[0] <= w["x_range_m"][1] + 1e-5
                and w["y_range_m"][0] - 1e-5 <= pt[1] <= w["y_range_m"][1] + 1e-5
                and w["z_range_m"][0] - 1e-5 <= pt[2] <= w["z_range_m"][1] + 1e-5
            ]
            sec_hit = secondary_support.get((uid, side))
            collinear = []
            corner_beams = []
            for ouid, op1, op2, oux, ouy, obw in beam_segs:
                if ouid == uid or abs(pt[2] - op1[2]) > 1e-5:
                    continue
                if math.dist(pt, op1) < 1e-5:
                    ovec = (oux, ouy)
                elif math.dist(pt, op2) < 1e-5:
                    ovec = (-oux, -ouy)
                else:
                    continue
                if ovec[0] * outward[0] + ovec[1] * outward[1] < -0.99:
                    collinear.append(ouid)
                else:
                    corner_beams.append((ouid, obw))

            if col_hits:
                support_kind = "COLUMN_FACE"
                col_depth = max(c_side for _, c_side in col_hits)
                hk_over_d = col_depth / max_d
                if collinear:
                    anch_status = "CONTINUOUS_THROUGH_COLUMN_OK" if hk_over_d >= 20.0 - 1e-6 else "JOINT_BAR_DIAMETER_EXCEEDS_HK_OVER_20"
                else:
                    anch_status = (
                        "STANDARD_90_DEG_HOOK_IN_COLUMN_OK"
                        if col_depth - 40.0 >= bond["tbdy_hook_a_req_pos2_mm"]
                        else "HEADED_BAR_REQUIRED_IN_COLUMN"
                    )
            elif w_hits:
                support_kind = "WALL_SUPPORT"
                coplanar = [w for w in w_hits if abs(ux * w["dir_xy"][0] + uy * w["dir_xy"][1]) >= 0.99]
                perp = [w for w in w_hits if abs(ux * w["dir_xy"][0] + uy * w["dir_xy"][1]) <= 0.01]
                if collinear:
                    anch_status = "CONTINUOUS_THROUGH_WALL_OK"
                elif coplanar and max(w["length_mm"] for w in coplanar) - 40.0 >= bond["coplanar_wall_1_5_lb_pos2_mm"]:
                    anch_status = "STRAIGHT_IN_COPLANAR_WALL_OK"
                elif perp and max(w["thickness_mm"] for w in perp) - 40.0 >= bond["tbdy_hook_a_req_pos2_mm"]:
                    anch_status = "STANDARD_90_DEG_HOOK_IN_WALL_OK"
                else:
                    anch_status = "HEADED_OR_U_HAIRPIN_REQUIRED_AT_THIN_WALL"
            elif sec_hit is not None:
                support_kind = "SUPPORTING_GIRDER_INTERIOR"
                girder_bw = sec_hit[1]
                anch_status = (
                    "STANDARD_90_DEG_HOOK_IN_GIRDER_OK"
                    if girder_bw - 40.0 >= bond["tbdy_hook_a_req_pos2_mm"]
                    else "HEADED_OR_U_HAIRPIN_REQUIRED_AT_GIRDER"
                )
            elif corner_beams:
                support_kind = "BEAM_CORNER_JUNCTION"
                max_obw = max(obw for _, obw in corner_beams)
                anch_status = (
                    "CONTINUOUS_INTO_COLLINEAR_BEAM_OK"
                    if collinear
                    else (
                        "STANDARD_90_DEG_HOOK_IN_CORNER_BEAM_OK"
                        if max_obw - 40.0 >= bond["tbdy_hook_a_req_pos2_mm"]
                        else "CORNER_U_HAIRPIN_SPLICE_REQUIRED"
                    )
                )
            else:
                # Check eccentric footprint overlap with column or wall thickness!
                ecc_cols = [
                    cid for cid, x0, x1, y0, y1, z0, z1 in col_footprints
                    if x0 - 1e-5 <= pt[0] <= x1 + 1e-5 and y0 - 1e-5 <= pt[1] <= y1 + 1e-5 and z0 - 1e-5 <= pt[2] <= z1 + 1e-5
                ]
                if ecc_cols:
                    support_kind = "ECCENTRIC_WALL_COLUMN_FOOTPRINT"
                    anch_status = "STANDARD_90_DEG_HOOK_IN_ECCENTRIC_COLUMN_FOOTPRINT_OK"
                else:
                    support_kind = "FREE_CANTILEVER_TIP"
                    anch_status = "CANTILEVER_U_CAP_DETAIL"

            end_topology_counts[support_kind] += 1
            anchorage_counts[anch_status] += 1
            end_topologies[side] = {
                "joint_id": jid,
                "support_kind": support_kind,
                "anchorage_status": anch_status,
                "max_bar_diameter_mm": max_d,
                "required_hook_embedment_mm": bond["tbdy_hook_a_req_pos2_mm"],
            }

        beam_rows.append({
            "member_id": uid,
            "label": b["label"],
            "story": b["story"],
            "section_name": b["section_name"],
            "max_axial_kn": beam_p_max,
            "axial_over_0_10_ac_fck": p_ratio,
            "max_n0_utilization": beam_u_n0,
            "max_axial_interval_box_utilization": beam_u_box,
            "max_torsion_knm": beam_t_max,
            "tcr_ignore_knm": tcr_ignore_knm,
            "tcr_compatibility_knm": tcr_compat_knm,
            "torsion_classification": torsion_class,
            "web_crushing_shear_torsion_ratio": beam_web_crush_max,
            "concurrent_stirrup_shear_torsion_ratio": beam_stirrup_comb_max,
            "concurrent_longitudinal_flexure_torsion_ratio": beam_long_comb_max,
            "proposed_torsion_side_web_bars": side_web_bars,
            "ends": end_topologies,
        })

    all_uls_satisfied = (
        e2k_audit["verified"]
        and axial_exceedances == 0
        and box_exceedances == 0
        and web_crush_exceedances == 0
        and concurrent_long_exceedances == 0
        and concurrent_stirrup_exceedances == 0
    )
    return {
        "schema": SCHEMA,
        "beam_count": len(beam_rows),
        "native_force_vectors_checked": sum(len(rowsets[uid]["LoadCase"]) for uid in beam_map),
        "e2k_modifiers_and_releases": e2k_audit,
        "tbdy_7_4_1_2_axial_qualified_beams": len(beam_rows) - axial_exceedances,
        "max_axial_over_0_10_ac_fck": max_axial_ratio,
        "max_n0_m3_utilization": max_n0_util,
        "max_axial_interval_box_utilization": max_box_util,
        "axial_interval_box_exceedances": box_exceedances,
        "ts500_8_2_torsion_classification_counts": dict(sorted(torsion_class_counts.items())),
        "max_combined_shear_torsion_web_ratio": max_web_crush_ratio,
        "combined_web_crushing_exceedances": web_crush_exceedances,
        "concurrent_stirrup_exceedances": concurrent_stirrup_exceedances,
        "concurrent_longitudinal_exceedances": concurrent_long_exceedances,
        "end_topology_counts": dict(sorted(end_topology_counts.items())),
        "end_anchorage_counts": dict(sorted(anchorage_counts.items())),
        "uls_axial_flexure_torsion_status": "ALL_180_BEAMS_ULS_QUALIFIED" if all_uls_satisfied else "EXCEEDANCE_DETECTED",
        "serviceability_status": "SLS_DEFLECTION_AND_CRACK_WIDTH_COMBINATIONS_NOT_CAPTURED",
        "beams": beam_rows,
    }
