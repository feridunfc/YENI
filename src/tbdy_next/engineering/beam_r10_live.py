"""Live R10 beam capacity, CHK-131..136 multi-row rebar and capacity-shear projection.

Deterministic report-time projection over the SAME locked LIVE_ETABS run receipts
(`geometry_capture`, `next_capture`, `column_axial.r10_source`, `column_axial.pmm_section_source`,
`column_axial.design_preferences`, `column_axial.force_source`).

Reuses existing formula owners (`beam_capacity`, `beam_references`, `section_capacity`,
`transverse_kernel`, `ts500_column`) with zero formula duplication. Candidate rebar scenarios
(16/20/24 mm, single or multi-row via CHK-132) remain engineering scenarios only and never
become physical/as-built beam reinforcement or final code PASS without engineer selection.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from ..column_engine.beam_capacity import (
    DIAMETERS,
    POLICY as BEAM_POLICY,
    propose_beam_cage_chk132,
    signed_beam_capacity,
)
from ..column_engine.beam_references import AREA_FIELDS, station_budget
from ..column_engine.section_capacity import Bar, Material, Section
from ..column_engine.native_archive import BankError
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.transverse_kernel import max_shear_web_kn
from ..column_engine.ts500_column import positive
from .frame_geometry import build_frame_catalog
from .column_r10_live import (
    BEAM_DESIGN_SUMMARY,
    BEAM_REINFORCING,
    END_OFFSETS,
    RELEASES,
    _GEOMETRY_TOL,
    _float_or_none,
    _materials_fck,
)
from .rebar_selection import (
    evaluate_beam_stirrups,
    normalize_beam_selection_policy,
    select_beam_station_rebar,
)

SCHEMA = "tbdy.next.beam-r10-live.v1"
DEFAULT_BEAM_DIAMETER_MM = 20
TBDY_BEAM_OVERSTRENGTH = 1.4
TBDY_BEAM_RHO_MAX = 0.02

_LEN_SCALE_TO_M = {"m": 1.0, "cm": 0.01, "mm": 0.001}
_AREA_SCALE_TO_MM2 = {"m2": 1_000_000.0, "cm2": 100.0, "mm2": 1.0}
_STRESS_SCALE_TO_MPA = {"kN/m2": 0.001, "MPa": 1.0, "N/mm2": 1.0, "kgf/cm2": 0.0980665}


def _unit_scale(table: Mapping[str, Any], field: str, scale_map: Mapping[str, float], default: float | None = None) -> float:
    units = ((table.get("field_metadata") or {}).get("units_by_field") or {}).get(field)
    if units in scale_map:
        return scale_map[units]
    if default is not None and (units is None or units == ""):
        return default
    raise ValueError(f"UNSUPPORTED_UNIT:{field}:{units!r}")


def _beam_longitudinal_rho_bounds(*, fck_mpa: float, fyd_mpa: float, gamma_c: float) -> dict[str, float]:
    """TBDY 2018 §7.4.2.1 / TS 500 Eq. 7.3 beam longitudinal ratio bounds."""
    fc = positive(fck_mpa, "fck")
    fyd = positive(fyd_mpa, "fyd")
    gc = positive(gamma_c, "gamma_c")
    fctk = 0.35 * math.sqrt(fc)
    fctd = fctk / gc
    return {
        "fctd_mpa": fctd,
        "rho_min": 0.8 * fctd / fyd,
        "rho_max": TBDY_BEAM_RHO_MAX,
    }


def _table_rows(r10_source: Mapping[str, Any] | None, key: str) -> tuple[Mapping[str, Any] | None, list[Mapping[str, Any]]]:
    if not isinstance(r10_source, Mapping):
        return None, []
    table = (r10_source.get("table_reads") or {}).get(key)
    if not isinstance(table, Mapping):
        return None, []
    rows = table.get("rows")
    if not isinstance(rows, list):
        return table, []
    return table, rows


def _beam_lengths_mm(source: Mapping[str, Any]) -> dict[str, float]:
    table = ((source.get("geometry_capture") or {}).get("tables") or {}).get("BEAM_CONNECTIVITY") or {}
    rows = table.get("rows") or []
    try:
        scale_m = _unit_scale(table, "Length", _LEN_SCALE_TO_M, default=1.0)
    except ValueError:
        return {}
    out: dict[str, float] = {}
    for row in rows:
        uid = row.get("UniqueName")
        val = _float_or_none(row.get("Length"))
        if isinstance(uid, str) and uid and val is not None and val > 0:
            out[uid] = val * scale_m * 1000.0
    return out


def _beam_end_offsets_mm(r10_source: Mapping[str, Any] | None) -> dict[str, tuple[float, float]]:
    table, rows = _table_rows(r10_source, END_OFFSETS)
    if not table or not rows:
        return {}
    fields = set(table.get("fields") or ())
    i_key = next((k for k in ("LengthI", "Length1", "OffsetI") if k in fields), None)
    j_key = next((k for k in ("LengthJ", "Length2", "OffsetJ") if k in fields), None)
    if not i_key or not j_key:
        return {}
    try:
        scale_i = _unit_scale(table, i_key, _LEN_SCALE_TO_M, default=1.0)
        scale_j = _unit_scale(table, j_key, _LEN_SCALE_TO_M, default=1.0)
    except ValueError:
        return {}
    out: dict[str, tuple[float, float]] = {}
    for row in rows:
        uid = row.get("UniqueName")
        vi, vj = _float_or_none(row.get(i_key)), _float_or_none(row.get(j_key))
        if isinstance(uid, str) and uid and vi is not None and vj is not None and min(vi, vj) >= 0:
            out[uid] = (vi * scale_i * 1000.0, vj * scale_j * 1000.0)
    return out


def _released_moment_ends(r10_source: Mapping[str, Any] | None) -> dict[str, dict[str, bool]]:
    table, rows = _table_rows(r10_source, RELEASES)
    if not table or not rows:
        return {}
    out: dict[str, dict[str, bool]] = {}
    for row in rows:
        uid = row.get("UniqueName")
        if not isinstance(uid, str) or not uid:
            continue
        def _is_rel(val: Any) -> bool:
            return str(val).strip().lower() in ("yes", "true", "1")
        i_rel = any(_is_rel(row.get(k)) for k in ("M2I", "M3I") if k in row)
        j_rel = any(_is_rel(row.get(k)) for k in ("M2J", "M3J") if k in row)
        out[uid] = {"I": i_rel, "J": j_rel}
    return out


def _design_factors(prefs: Mapping[str, Any] | None) -> tuple[float | None, float | None]:
    rows = (prefs or {}).get("rows") or []
    if len(rows) != 1:
        return None, None
    gc = _float_or_none(rows[0].get("GammaC"))
    gs = _float_or_none(rows[0].get("GammaS"))
    return (gc if gc and gc > 0 else None, gs if gs and gs > 0 else None)


def _steel_grade_mpa(pmm_sec_source: Mapping[str, Any] | None, mat_name: str | None) -> tuple[float | None, float | None]:
    if not pmm_sec_source or not mat_name:
        return None, None
    tables = pmm_sec_source.get("table_reads") or {}
    rebar_tbl = tables.get("Material Properties - Rebar Data") or {}
    mech_tbl = tables.get("Material Properties - Basic Mechanical Properties") or {}
    fy_mpa = es_mpa = None
    try:
        fy_scale = _unit_scale(rebar_tbl, "Fy", _STRESS_SCALE_TO_MPA, default=0.001)
        for row in rebar_tbl.get("rows") or ():
            if row.get("Material") == mat_name:
                val = _float_or_none(row.get("Fy"))
                if val and val > 0:
                    fy_mpa = val * fy_scale
                break
    except ValueError:
        fy_mpa = None
    try:
        es_scale = _unit_scale(mech_tbl, "E1", _STRESS_SCALE_TO_MPA, default=0.001)
        for row in mech_tbl.get("rows") or ():
            if row.get("Material") == mat_name:
                val = _float_or_none(row.get("E1"))
                if val and val > 0:
                    es_mpa = val * es_scale
                break
    except ValueError:
        es_mpa = None
    return fy_mpa, es_mpa


def _beam_reinforcing_by_section(r10_source: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    table, rows = _table_rows(r10_source, BEAM_REINFORCING)
    if not table or not rows:
        return {}
    fields = set(table.get("fields") or ())
    cov_top_key = "CoverTop" if "CoverTop" in fields else ("TopCover" if "TopCover" in fields else None)
    cov_bot_key = "CoverBot" if "CoverBot" in fields else ("BotCover" if "BotCover" in fields else None)
    if not cov_top_key or not cov_bot_key:
        return {}
    try:
        cov_top_mm = _unit_scale(table, cov_top_key, _LEN_SCALE_TO_M, default=1.0) * 1000.0
        cov_bot_mm = _unit_scale(table, cov_bot_key, _LEN_SCALE_TO_M, default=1.0) * 1000.0
    except ValueError:
        return {}
    mat_key = "RebarMatL" if "RebarMatL" in fields else ("MatPropLong" if "MatPropLong" in fields else None)
    override_aliases = (
        ("TopLeftArea", ("TopLeftArea", "TopIEndArea")),
        ("TopRightArea", ("TopRightArea", "TopJEndArea")),
        ("BotLeftArea", ("BotLeftArea", "BotIEndArea")),
        ("BotRightArea", ("BotRightArea", "BotJEndArea")),
    )
    ov_sources: dict[str, tuple[str, float]] = {}
    for canonical_k, candidates in override_aliases:
        src_k = next((c for c in candidates if c in fields), None)
        if src_k:
            try:
                ov_sources[canonical_k] = (src_k, _unit_scale(table, src_k, _AREA_SCALE_TO_MM2, default=1_000_000.0))
            except ValueError:
                ov_sources[canonical_k] = (src_k, 0.0)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row.get("Name")
        ct, cb = _float_or_none(row.get(cov_top_key)), _float_or_none(row.get(cov_bot_key))
        if not isinstance(name, str) or not name or ct is None or cb is None:
            continue
        overrides = {
            canonical_k: (_float_or_none(row.get(src_k)) or 0.0) * scale
            for canonical_k, (src_k, scale) in ov_sources.items()
        }
        out[name] = {
            "section_name": name,
            "rebar_material_long": row.get(mat_key) if mat_key else None,
            "rebar_material_conf": row.get("RebarMatC") or row.get("MatPropConfine"),
            "cover_top_mm": ct * cov_top_mm,
            "cover_bottom_mm": cb * cov_bot_mm,
            "override_areas_mm2": overrides,
        }
    return out


def _beam_design_rows_by_member(r10_source: Mapping[str, Any] | None) -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    table, rows = _table_rows(r10_source, BEAM_DESIGN_SUMMARY)
    if table is None:
        return {}, "BEAM_DESIGN_SUMMARY_NOT_CAPTURED"
    if not rows:
        return {}, "BEAM_DESIGN_SUMMARY_EMPTY"
    fields = set(table.get("fields") or ())
    if not {"UniqueName", "Station", "AsTop", "AsBot"}.issubset(fields):
        return {}, "BEAM_DESIGN_SUMMARY_MISSING_REQUIRED_FIELDS"
    try:
        sta_scale = _unit_scale(table, "Station", _LEN_SCALE_TO_M, default=1.0)
        area_scales = {
            k: _unit_scale(table, k, _AREA_SCALE_TO_MM2, default=1_000_000.0)
            for k in AREA_FIELDS
            if k in fields
        }
    except ValueError as exc:
        return {}, str(exc)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        uid = row.get("UniqueName")
        sta = _float_or_none(row.get("Station"))
        if not isinstance(uid, str) or not uid or sta is None:
            continue
        areas = {
            k: (_float_or_none(row.get(k)) or 0.0) * area_scales[k]
            for k in AREA_FIELDS
            if k in area_scales
        }
        grouped.setdefault(uid, []).append({
            "unique_name": uid,
            "design_sect": row.get("DesignSect"),
            "station_m": sta * sta_scale,
            "status": str(row.get("Status") or "No Message"),
            "warn_msg": str(row.get("WarnMsg") or "No Message"),
            "err_msg": str(row.get("ErrMsg") or "No Message"),
            "as_top_combo": row.get("AsTopCombo"),
            "as_bot_combo": row.get("AsBotCombo"),
            "t_lng_combo": row.get("TLngCombo"),
            "areas_mm2": areas,
        })
    return grouped, None


def _override_capacity_scenario(
    *,
    h_mm: float,
    b_mm: float,
    cov_top_mm: float,
    cov_bot_mm: float,
    area_top_mm2: float,
    area_bot_mm2: float,
    material: Material,
) -> dict[str, Any] | None:
    """Evaluate signed N=0 section capacity strictly as OVERRIDE_SCENARIO when ETABS overrides > 0."""
    if min(area_top_mm2, area_bot_mm2) <= 0:
        return None
    half_x3 = max(1.0, b_mm / 2.0 - BEAM_POLICY["side_clear_cover_to_tie_mm"] - BEAM_POLICY["tie_diameter_mm"] - 10.0)
    bars = (
        Bar(h_mm / 2.0 - cov_top_mm, -half_x3, area_top_mm2 / 2.0),
        Bar(h_mm / 2.0 - cov_top_mm, half_x3, area_top_mm2 / 2.0),
        Bar(-h_mm / 2.0 + cov_bot_mm, -half_x3, area_bot_mm2 / 2.0),
        Bar(-h_mm / 2.0 + cov_bot_mm, half_x3, area_bot_mm2 / 2.0),
    )
    cap = signed_beam_capacity(Section(h_mm, b_mm, bars, material))
    return {
        "origin": "ETABS_SECTION_OVERRIDE_SCENARIO_ONLY",
        "selected_design": False,
        "area_top_mm2": area_top_mm2,
        "area_bot_mm2": area_bot_mm2,
        "capacity": cap,
    }


def _evaluate_beam_end(
    *,
    end: str,
    target_sta_m: float,
    length_m: float,
    section_name: str,
    profile: Mapping[str, Any],
    material: Material,
    design_rows: list[Mapping[str, Any]],
    override_top_mm2: float,
    override_bot_mm2: float,
    rho_bounds: Mapping[str, float],
    released: bool,
    beam_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    matches = [r for r in design_rows if abs(r["station_m"] - target_sta_m) <= station_budget(r["station_m"], target_sta_m, length_m)]
    row: dict[str, Any] = {
        "end": end,
        "target_station_m": target_sta_m,
        "design_match_count": len(matches),
        "released_for_bending": released,
        "status": "BEAM_END_BLOCKED",
        "reason": None,
        "targets_mm2": None,
        "candidates": {},
        "default_diameter_mm": DEFAULT_BEAM_DIAMETER_MM,
        "override_scenario": _override_capacity_scenario(
            h_mm=profile["local2_height_mm"],
            b_mm=profile["local3_width_mm"],
            cov_top_mm=profile["cover_top_centroid_mm"],
            cov_bot_mm=profile["cover_bottom_centroid_mm"],
            area_top_mm2=override_top_mm2,
            area_bot_mm2=override_bot_mm2,
            material=material,
        ),
        "formal_compliance": "NOT_PROVEN",
    }
    if not matches:
        row["reason"] = "BEAM_DESIGN_STATION_NOT_FOUND"
        return row
    distinct_stations = {float(r["station_m"]) for r in matches}
    if len(distinct_stations) > 1:
        row["reason"] = "BEAM_DESIGN_STATION_AMBIGUOUS"
        return row
    row["station_discontinuity_envelope"] = len(matches) > 1
    for m in matches:
        if m["design_sect"] and m["design_sect"] != section_name:
            row["reason"] = "BEAM_DESIGN_SECTION_MISMATCH"
            return row
        if any(m[k] not in ("No Message", "") for k in ("status", "warn_msg", "err_msg")):
            row["reason"] = "BEAM_DESIGN_MESSAGE_NOT_CLEAR"
            return row
        areas = m["areas_mm2"]
        if min(
            max(areas.get("AsTop", 0.0), areas.get("AsMinTop", 0.0), areas.get("totTopRebar", 0.0)),
            max(areas.get("AsBot", 0.0), areas.get("AsMinBot", 0.0), areas.get("totBotRebar", 0.0)),
        ) < 0:
            row["reason"] = "BEAM_REQUIRED_AREA_NEGATIVE"
            return row

    def _row_top(m_row: Mapping[str, Any]) -> float:
        a = m_row["areas_mm2"]
        return max(a.get("AsTop", 0.0), a.get("AsMinTop", 0.0), a.get("totTopRebar", 0.0))

    def _row_bot(m_row: Mapping[str, Any]) -> float:
        a = m_row["areas_mm2"]
        return max(a.get("AsBot", 0.0), a.get("AsMinBot", 0.0), a.get("totBotRebar", 0.0))

    top_gov = max(matches, key=_row_top)
    bot_gov = max(matches, key=_row_bot)
    tlng_gov = max(matches, key=lambda r: r["areas_mm2"].get("TLngRebar", 0.0))
    top_req = _row_top(top_gov)
    bot_req = _row_bot(bot_gov)
    row["targets_mm2"] = {
        "top_mm2": top_req,
        "bottom_mm2": bot_req,
        "torsion_long_mm2": tlng_gov["areas_mm2"].get("TLngRebar", 0.0),
        "top_combination": top_gov["as_top_combo"],
        "bottom_combination": bot_gov["as_bot_combo"],
        "torsion_combination": tlng_gov["t_lng_combo"],
        "total_required_area_is_provided": False,
        "station_discontinuity_envelope": len(matches) > 1,
    }
    h = profile["local2_height_mm"]
    b = profile["local3_width_mm"]
    cands: dict[str, Any] = {}
    for diam in DIAMETERS:
        try:
            cand = propose_beam_cage_chk132(profile, top_req, bot_req, diam, allow_multi_row=True)
            eff_d_top = h - cand.get("effective_bottom_centroid_mm", profile["cover_bottom_centroid_mm"])
            eff_d_bot = h - cand.get("effective_top_centroid_mm", profile["cover_top_centroid_mm"])
            rho_top = cand["area_top_mm2"] / (b * eff_d_top) if cand.get("area_top_mm2") and eff_d_top > 0 else None
            rho_bot = cand["area_bottom_mm2"] / (b * eff_d_bot) if cand.get("area_bottom_mm2") and eff_d_bot > 0 else None
            rho_ok = (
                rho_top is not None
                and rho_bot is not None
                and rho_bounds["rho_min"] <= rho_top <= rho_bounds["rho_max"]
                and rho_bounds["rho_min"] <= rho_bot <= rho_bounds["rho_max"]
            )
            cands[str(diam)] = {
                **cand,
                "chk133_rho_top": rho_top,
                "chk133_rho_bottom": rho_bot,
                "chk133_rho_min": rho_bounds["rho_min"],
                "chk133_rho_max": rho_bounds["rho_max"],
                "chk133_bounds_reference_met": rho_ok,
                "chk133_compression_at_least_half_tension": (
                    cand["area_bottom_mm2"] >= 0.5 * cand["area_top_mm2"]
                    if cand.get("area_top_mm2") is not None and cand.get("area_bottom_mm2") is not None
                    else None
                ),
            }
        except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
            cands[str(diam)] = {"diameter_mm": diam, "status": "BEAM_PROPOSAL_BLOCKED", "reason": str(exc), "capacity": None}
    row["candidates"] = cands
    if beam_policy is not None:
        row["engineer_selection"] = select_beam_station_rebar(
            profile=profile,
            top_req_mm2=top_req,
            bot_req_mm2=bot_req,
            rho_bounds=rho_bounds,
            policy=beam_policy,
            is_support=True,
        )
    default_cand = cands.get(str(DEFAULT_BEAM_DIAMETER_MM)) or {}
    row["status"] = (
        "BEAM_CANDIDATE_CALCULATED_NOT_PROVEN"
        if default_cand.get("status") == "BEAM_PROPOSAL_CALCULATED"
        else "BEAM_CANDIDATE_BLOCKED"
    )
    if row["status"] != "BEAM_CANDIDATE_CALCULATED_NOT_PROVEN":
        row["reason"] = default_cand.get("reason") or "BEAM_DEFAULT_CANDIDATE_BLOCKED"
    return row


def _beam_gravity_shear_kn(force_rowsets: Mapping[str, Any], uid: str, axial: Mapping[str, Any]) -> float | None:
    rowset = force_rowsets.get(uid)
    if rowset is None:
        return None
    plan = axial.get("combination_plan") or {}
    gravity_names = {
        c["name"]
        for c in plan.get("combinations", ())
        if c.get("role") == "gravity"
    }
    if plan.get("source") == "ASSIGNED_DESIGN" and isinstance(plan.get("design_assignment"), Mapping):
        gravity_names |= set((plan["design_assignment"].get("groups") or {}).get("gravity", ()))
    if not gravity_names:
        return None
    try:
        rows = [r for r in native_frame_force_rows(rowset, uid) if r[4] in gravity_names]
    except BankError:
        return None
    # A partial gravity case or lone envelope extreme can underestimate the full Ve.
    by_case = {name: {} for name in gravity_names}
    for row in rows:
        if row[6] != 0:
            return None
        by_case[row[4]].setdefault(row[:4], set()).add(row[5])
    cuts = {row[:4] for row in rows}
    if not cuts or any(case.keys() != cuts for case in by_case.values()):
        return None
    if any(steps not in ({"Single Value"}, {""}, {"Min", "Max"})
           for case in by_case.values() for steps in case.values()):
        return None
    return max(abs(float(r[8])) for r in rows)


def _beam_shear_ve(
    *,
    uid: str,
    end_i: Mapping[str, Any],
    end_j: Mapping[str, Any],
    ln_mm: float | None,
    has_end_offsets: bool,
    b_mm: float,
    h_mm: float,
    cov_top_mm: float,
    material: Material,
    force_rowsets: Mapping[str, Any],
    axial: Mapping[str, Any],
    use_engineer_selection: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "clear_span_mm": ln_mm,
        "end_offsets_applied": has_end_offsets,
        "overstrength_factor": TBDY_BEAM_OVERSTRENGTH,
        "earthquake_shear_sway_right_kn": None,
        "earthquake_shear_sway_left_kn": None,
        "earthquake_capacity_shear_term_kn": None,
        "gravity_shear_vdy_kn": None,
        "scenario_ve_kn": None,
        "ts500_max_shear_vr_max_kn": max_shear_web_kn(fcd_mpa=material.fcd, bw_mm=b_mm, d_mm=max(1.0, h_mm - cov_top_mm)),
        "exceeds_vr_max_without_vdy": None,
        "status": "BEAM_SHEAR_VE_NOT_BOUND",
    }
    if use_engineer_selection:
        ci = end_i.get("engineer_selection") or {}
        cj = end_j.get("engineer_selection") or {}
    else:
        ci = (end_i.get("candidates") or {}).get(str(DEFAULT_BEAM_DIAMETER_MM)) or {}
        cj = (end_j.get("candidates") or {}).get(str(DEFAULT_BEAM_DIAMETER_MM)) or {}
    capi = ci.get("capacity") or {}
    capj = cj.get("capacity") or {}
    if (
        capi.get("status") != "BEAM_CAPACITY_REFERENCE"
        or capj.get("status") != "BEAM_CAPACITY_REFERENCE"
        or ln_mm is None
        or ln_mm <= 0
    ):
        return out
    ln_m = ln_mm / 1000.0
    mp_i_pos = TBDY_BEAM_OVERSTRENGTH * abs(float(capi["positive_m3_knm"]))
    mp_i_neg = TBDY_BEAM_OVERSTRENGTH * abs(float(capi["negative_m3_knm"]))
    mp_j_pos = TBDY_BEAM_OVERSTRENGTH * abs(float(capj["positive_m3_knm"]))
    mp_j_neg = TBDY_BEAM_OVERSTRENGTH * abs(float(capj["negative_m3_knm"]))
    # Anti-symmetric seismic bending across a beam span: (Mpi- + Mpj+)/ln and (Mpi+ + Mpj-)/ln
    ve_right = (mp_i_neg + mp_j_pos) / ln_m
    ve_left = (mp_i_pos + mp_j_neg) / ln_m
    ve_eq = max(ve_right, ve_left)
    v_dy = _beam_gravity_shear_kn(force_rowsets, uid, axial)
    ve_total = (v_dy + ve_eq) if v_dy is not None else None
    out.update({
        "earthquake_shear_sway_right_kn": ve_right,
        "earthquake_shear_sway_left_kn": ve_left,
        "earthquake_capacity_shear_term_kn": ve_eq,
        "gravity_shear_vdy_kn": v_dy,
        "scenario_ve_kn": ve_total,
        "exceeds_vr_max_without_vdy": ve_eq > out["ts500_max_shear_vr_max_kn"],
        "status": "SCENARIO_VE_CALCULATED_NOT_PROVEN" if ve_total is not None else "MOMENT_PAIR_SHEAR_TERM_ONLY_VDY_NOT_CAPTURED",
    })
    return out


def _selected_beam_design(beam):
    """Follow the same selected cage through end capacities, full Ve and both stirrup zones."""
    missing, failures = [], []
    for face, selected in (("I", (beam["ends"].get("I") or {}).get("engineer_selection")),
                           ("J", (beam["ends"].get("J") or {}).get("engineer_selection")),
                           ("SPAN", beam.get("engineer_midspan"))):
        if not selected or selected.get("status") != "BEAM_SELECTED_CALCULATED":
            missing.append("SELECTED_SECTION_UNAVAILABLE:" + face)
            continue
        capacity = selected.get("capacity") or {}
        if (capacity.get("status") != "BEAM_CAPACITY_REFERENCE" or capacity.get("positive_m3_knm") is None
                or capacity.get("negative_m3_knm") is None):
            missing.append("SIGNED_CAPACITY_UNAVAILABLE:" + face)
        for field in ("covers_targets", "rho_bounds_met"):
            if selected.get(field) is False:
                failures.append(face + ":" + field)
            elif selected.get(field) is not True:
                missing.append(face + ":" + field)
    stirrups = beam.get("engineer_stirrups") or {}
    shear = beam.get("engineer_shear_ve") or {}
    demand = shear.get("scenario_ve_kn")
    limits = {"WEB": shear.get("ts500_max_shear_vr_max_kn")}
    for zone in ("confinement", "span"):
        ties = stirrups.get(zone) or {}
        limits[zone.upper()] = ties.get("vr_conservative_kn")
        for field in ("spacing_ok", "min_ratio_ok"):
            if ties.get(field) is False:
                failures.append(zone + ":" + field)
            elif ties.get(field) is not True:
                missing.append(zone + ":" + field)
    ratios = {}
    if demand is None or not math.isfinite(demand) or demand < 0:
        missing.append("FULL_CAPACITY_SHEAR_UNAVAILABLE")
    else:
        for check, resistance in limits.items():
            if resistance is None or not math.isfinite(resistance) or resistance <= 0:
                missing.append("RESISTANCE_UNAVAILABLE:" + check)
            else:
                ratios[check] = demand / resistance
                if ratios[check] > 1.0:
                    failures.append("CAPACITY_SHEAR_EXCEEDS:" + check)
    if beam.get("tbdy_7_4_1_1_geometry_ok") is False:
        failures.append("BEAM_SECTION_DIMENSION_SCREEN")
    status = "NUMERICAL_EXCEEDANCE" if failures else "HOLD" if missing else "CONDITIONAL_DESIGN_CALCULATED"
    return {"status": status, "full_ve_kn": demand, "resistances_kn": limits, "utilizations": ratios,
            "failures": failures, "missing": missing}


def project_beam_r10_live(
    source: Mapping[str, Any],
    geometry: Mapping[str, Any] | None,
    axial: Mapping[str, Any] | None,
    pmm: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Deterministic beam demand, CHK-131..136 multi-row cages, signed M3 and Ve projection."""
    if axial is None or geometry is None or "column_axial" not in source:
        return None
    frames, points, graph_meta = build_frame_catalog(source)
    adjacency = graph_meta.pop("adjacency")
    pmm_id = (pmm or {}).get("member_id")
    if pmm_id and pmm_id in frames:
        col = frames[pmm_id]
        target_beam_ids = sorted({
            item["frame_id"]
            for pt in (col["point_i"], col["point_j"])
            for item in adjacency.get(pt, ())
            if item["type"] == "Beam"
        })
    else:
        target_beam_ids = sorted(fid for fid, f in frames.items() if f["type"] == "Beam")

    feature = source.get("column_axial") or {}
    r10_source = feature.get("r10_source")
    pmm_sec_source = feature.get("pmm_section_source")
    gamma_c, gamma_s = _design_factors(feature.get("design_preferences"))
    fck_map = _materials_fck(extra)
    lengths_mm = _beam_lengths_mm(source)
    offsets_mm = _beam_end_offsets_mm(r10_source)
    releases = _released_moment_ends(r10_source)
    reinf_by_sect = _beam_reinforcing_by_section(r10_source)
    design_rows_by_uid, design_tbl_err = _beam_design_rows_by_member(r10_source)
    beam_force_rowsets = ((r10_source or {}).get("beam_force_source") or {}).get("rowsets") or {}
    force_rowsets = {
        **beam_force_rowsets,
        **((feature.get("force_source") or {}).get("rowsets") or {}),
    }
    scope = "CONNECTED_TO_COLUMN" if (pmm_id and pmm_id in frames) else "ALL_BEAMS"
    beam_policy = normalize_beam_selection_policy(source.get("beam_selection")) if source.get("beam_selection") is not None else None

    beam_records: list[dict[str, Any]] = []
    for uid in target_beam_ids:
        beam = frames[uid]
        dims = beam["dims"]
        sect = beam["section_name"]
        len_mm = lengths_mm.get(uid)
        off_pair = offsets_mm.get(uid)
        axes = beam.get("axes_global")
        horizontal_local2_up = bool(
            axes is not None and abs(axes[0][2]) <= _GEOMETRY_TOL and abs(axes[1][2] - 1.0) <= _GEOMETRY_TOL
        )
        reinf = reinf_by_sect.get(sect or "")
        fck_mpa = fck_map.get(beam.get("material_name") or "")
        fy_mpa, es_mpa = _steel_grade_mpa(pmm_sec_source, (reinf or {}).get("rebar_material_long"))

        reasons: list[str] = []
        if not dims:
            reasons.append("BEAM_RECTANGULAR_DIMENSIONS_MISSING")
        if len_mm is None:
            reasons.append("BEAM_LENGTH_MISSING")
        if not horizontal_local2_up:
            reasons.append("BEAM_HORIZONTAL_LOCAL2_UP_NOT_BOUND")
        if reinf is None:
            reasons.append("BEAM_REINFORCING_NOT_CAPTURED")
        if design_tbl_err is not None:
            reasons.append(design_tbl_err)
        if fck_mpa is None:
            reasons.append("BEAM_CONCRETE_FCK_MISSING")
        if fy_mpa is None or es_mpa is None:
            reasons.append("BEAM_REBAR_MATERIAL_MISSING")
        if gamma_c is None or gamma_s is None:
            reasons.append("TS500_DESIGN_FACTORS_MISSING")

        if reasons:
            beam_records.append({
                "member_id": uid,
                "label": beam["label"],
                "story": beam["story"],
                "section_name": sect,
                "point_i": beam["point_i"],
                "point_j": beam["point_j"],
                "length_mm": len_mm,
                "clear_span_mm": (len_mm - sum(off_pair)) if (len_mm is not None and off_pair is not None) else None,
                "horizontal_local2_up": horizontal_local2_up,
                "status": "BEAM_INPUTS_INCOMPLETE",
                "reasons": reasons,
                "ends": {},
                "shear_ve": None,
                "formal_compliance": "NOT_PROVEN",
            })
            continue

        h_mm = dims.local2_extent_mm
        b_mm = dims.local3_extent_mm
        off_i_mm, off_j_mm = off_pair if off_pair is not None else (0.0, 0.0)
        ln_mm = len_mm - off_i_mm - off_j_mm
        material = Material(fck=fck_mpa, fcd=fck_mpa / gamma_c, fyd=fy_mpa / gamma_s, es=es_mpa)
        rho_bounds = _beam_longitudinal_rho_bounds(fck_mpa=fck_mpa, fyd_mpa=material.fyd, gamma_c=gamma_c)
        profile = {
            "section_name": sect,
            "local2_height_mm": h_mm,
            "local3_width_mm": b_mm,
            "cover_top_centroid_mm": reinf["cover_top_mm"],
            "cover_bottom_centroid_mm": reinf["cover_bottom_mm"],
            "material": {
                "fck": material.fck,
                "fcd": material.fcd,
                "fyd": material.fyd,
                "es": material.es,
                "ecu": material.ecu,
            },
        }
        ov = reinf["override_areas_mm2"]
        rel = releases.get(uid, {"I": False, "J": False})
        d_rows = design_rows_by_uid.get(uid, [])
        length_m = len_mm / 1000.0
        ends: dict[str, Any] = {}
        for end, sta_m, ov_top, ov_bot in (
            ("I", off_i_mm / 1000.0, ov.get("TopLeftArea", 0.0), ov.get("BotLeftArea", 0.0)),
            ("J", (len_mm - off_j_mm) / 1000.0, ov.get("TopRightArea", 0.0), ov.get("BotRightArea", 0.0)),
        ):
            ends[end] = _evaluate_beam_end(
                end=end,
                target_sta_m=sta_m,
                length_m=length_m,
                section_name=sect or "",
                profile=profile,
                material=material,
                design_rows=d_rows,
                override_top_mm2=ov_top,
                override_bot_mm2=ov_bot,
                rho_bounds=rho_bounds,
                released=rel[end],
                beam_policy=beam_policy,
            )
        shear_ve = _beam_shear_ve(
            uid=uid,
            end_i=ends["I"],
            end_j=ends["J"],
            ln_mm=ln_mm,
            has_end_offsets=off_pair is not None,
            b_mm=b_mm,
            h_mm=h_mm,
            cov_top_mm=reinf["cover_top_mm"],
            material=material,
            force_rowsets=force_rowsets,
            axial=axial,
        )
        eng_extra: dict[str, Any] = {}
        if beam_policy is not None:
            sta_i = off_i_mm / 1000.0
            sta_j = (len_mm - off_j_mm) / 1000.0
            bud_i = station_budget(sta_i, sta_i, length_m)
            bud_j = station_budget(sta_j, sta_j, length_m)
            interior = [
                r for r in d_rows
                if (r["station_m"] > sta_i + bud_i and r["station_m"] < sta_j - bud_j)
                and not any(r[k] not in ("No Message", "") for k in ("status", "warn_msg", "err_msg"))
            ]
            if interior:
                mid_top = max(max(r["areas_mm2"].get("AsTop", 0.0), r["areas_mm2"].get("AsMinTop", 0.0), r["areas_mm2"].get("totTopRebar", 0.0)) for r in interior)
                mid_bot = max(max(r["areas_mm2"].get("AsBot", 0.0), r["areas_mm2"].get("AsMinBot", 0.0), r["areas_mm2"].get("totBotRebar", 0.0)) for r in interior)
                eng_mid = select_beam_station_rebar(
                    profile=profile, top_req_mm2=mid_top, bot_req_mm2=mid_bot,
                    rho_bounds=rho_bounds, policy=beam_policy, is_support=False,
                )
                eng_mid["midspan_station_count"] = len(interior)
            else:
                eng_mid = {"selection_status": "MIDSPAN_STATIONS_NOT_IN_SUMMARY"}
            # A common conservative depth covers both bending signs and all selected stations.
            selected_stations = [ends[e].get("engineer_selection") or {} for e in ("I", "J")]
            selected_stations.append(eng_mid or {})
            centroid_cover = max(
                [reinf["cover_top_mm"], reinf["cover_bottom_mm"]]
                + [station[key] for station in selected_stations
                   for key in ("effective_top_centroid_mm", "effective_bottom_centroid_mm")
                   if station.get(key) is not None])
            eng_ve = _beam_shear_ve(
                uid=uid, end_i=ends["I"], end_j=ends["J"], ln_mm=ln_mm, has_end_offsets=off_pair is not None,
                b_mm=b_mm, h_mm=h_mm, cov_top_mm=centroid_cover, material=material,
                force_rowsets=force_rowsets, axial=axial, use_engineer_selection=True,
            )
            fywk_conf, _ = _steel_grade_mpa(pmm_sec_source, reinf.get("rebar_material_conf") or reinf.get("rebar_material_long"))
            sel_diams = [
                d for e_key in ("I", "J")
                for d in ((ends[e_key].get("engineer_selection") or {}).get("min_longitudinal_diameter_mm"),)
                if d is not None
            ]
            min_long_d = min(sel_diams) if sel_diams else int(beam_policy["top_continuous"]["diameter_mm"])
            eng_stirrups = evaluate_beam_stirrups(
                b_mm=b_mm, h_mm=h_mm, d_eff_mm=h_mm - centroid_cover,
                min_long_diameter_mm=min_long_d, fctd_mpa=rho_bounds["fctd_mpa"], fcd_mpa=material.fcd,
                fywk_mpa=fywk_conf, gamma_s=gamma_s,
                ve_eq_kn=eng_ve.get("earthquake_capacity_shear_term_kn"),
                ve_total_kn=eng_ve.get("scenario_ve_kn"),
                policy=beam_policy,
            )
            eng_extra = {
                "engineer_midspan": eng_mid,
                "engineer_shear_ve": eng_ve,
                "engineer_stirrups": eng_stirrups,
            }
        both_calc = all(ends[e]["status"] == "BEAM_CANDIDATE_CALCULATED_NOT_PROVEN" for e in ("I", "J"))
        beam_records.append({
            "member_id": uid,
            "label": beam["label"],
            "story": beam["story"],
            "section_name": sect,
            "point_i": beam["point_i"],
            "point_j": beam["point_j"],
            "width_mm": b_mm,
            "height_mm": h_mm,
            "fyk_mpa": fy_mpa,
            "length_mm": len_mm,
            "clear_span_mm": ln_mm,
            "end_offsets_applied": off_pair is not None,
            "end_offsets_mm": dict(zip(("I", "J"), off_pair)) if off_pair is not None else None,
            "horizontal_local2_up": horizontal_local2_up,
            "tbdy_7_4_1_1_geometry_ok": b_mm >= 250.0 and h_mm >= 300.0 and h_mm <= 3.5 * b_mm,
            "ends": ends,
            "shear_ve": shear_ve,
            **eng_extra,
            "status": "BEAM_CANDIDATES_CALCULATED_NOT_PROVEN" if both_calc else "BEAM_PARTIAL_OR_BLOCKED",
            "reasons": [] if both_calc else [ends[e].get("reason") for e in ("I", "J") if ends[e].get("reason")],
            "formal_compliance": "NOT_PROVEN",
        })

    if source.get("building_design") is not None:
        for beam in beam_records:
            beam["selected_design"] = _selected_beam_design(beam)
    calc_count = sum(b["status"] == "BEAM_CANDIDATES_CALCULATED_NOT_PROVEN" for b in beam_records)
    overall_status = (
        "NO_BEAMS_IN_SCOPE"
        if not beam_records
        else "BEAM_CANDIDATE_SCENARIOS_CALCULATED_NOT_PROVEN"
        if calc_count == len(beam_records)
        else "BEAM_PARTIAL_OR_UNBOUND"
        if calc_count > 0
        else "BEAM_CAPACITY_NOT_BOUND"
    )
    return {
        "schema": SCHEMA,
        "scope": scope,
        "target_member_id": pmm_id,
        "default_diameter_mm": DEFAULT_BEAM_DIAMETER_MM,
        **({"beam_selection_policy": beam_policy} if beam_policy is not None else {}),
        "beam_count": len(beam_records),
        "calculated_beam_count": calc_count,
        "beams": beam_records,
        "status": overall_status,
        "open_gates": [
            "ETABS_REQUIRED_BEAM_STEEL_NOT_AS_BUILT_SELECTED_DESIGN",
            "N_ZERO_SCENARIO_ONLY_SOURCE_BEAM_AXIAL_FORCE_NOT_APPLIED",
            "BEAM_TORSION_ANCHORAGE_AND_SLAB_PARTICIPATION_NOT_BOUND",
        ],
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
