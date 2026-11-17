"""Engineer-controlled rebar selection for ductile beams and rectangular columns (TBDY 2018 / TS 500).

Pure deterministic engineering selection reusing existing formula owners
(`beam_capacity`, `section_capacity`, `transverse_kernel`, `ts500_column`).
Never alters raw ETABS source receipts or claims final regulatory sign-off
while source/seismic gates remain open (`formal_compliance = NOT_PROVEN`).
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from ..column_engine.beam_capacity import SELECTED_LONG_DIAMETERS, build_selected_beam_cage
from ..column_engine.csi_geometry import LocalSectionDims
from ..column_engine.section_capacity import Bar, Material, Section, perimeter, solver
from ..column_engine.transverse_kernel import confinement_reference, max_shear_web_kn, shear_reference
from ..column_engine.ts500_column import positive
from .column_gates import apply_minimum_eccentricity

BEAM_CONFINEMENT_REGION_FACTOR = 2.0  # 2 * h_beam per TBDY 2018 §7.4.4.3
COLUMN_MIN_RHO = 0.01
COLUMN_MAX_RHO = 0.04
COLUMN_ALLOWED_LONG_DIAMETERS = (14, 16, 20, 22, 24, 25)
TIE_ALLOWED_DIAMETERS = (8, 10, 12)

DEFAULT_BEAM_SELECTION_POLICY: dict[str, Any] = {
    "schema": "tbdy.next.beam-selection-policy.v1",
    "selection_mode": "ENGINEER_RULE",
    "top_continuous": {"count": 2, "diameter_mm": 12},
    "bottom_continuous": {"count": 2, "diameter_mm": 14},
    "allowed_additional_diameters_mm": [16, 20, 22, 24, 25],
    "stirrup_confinement": {"diameter_mm": 8, "spacing_mm": 100.0, "legs": 2},
    "stirrup_span": {"diameter_mm": 8, "spacing_mm": 150.0, "legs": 2},
    "strictly_exceed_required": True,
    "enforce_tbdy_rho_min": True,
    "enforce_support_half_ratio": True,
    "max_rows_per_face": 3,
}

DEFAULT_COLUMN_SELECTION_POLICY: dict[str, Any] = {
    "schema": "tbdy.next.column-selection-policy.v1",
    "selection_mode": "ENGINEER_RULE",
    "allowed_longitudinal_diameters_mm": list(COLUMN_ALLOWED_LONG_DIAMETERS),
    "tie_diameter_preference_mm": list(TIE_ALLOWED_DIAMETERS),
    "stirrup_confinement_spacing_mm": 100.0,
    "stirrup_span_spacing_mm": 150.0,
    "strictly_exceed_required": True,
    "min_rho": COLUMN_MIN_RHO,
    "max_rho": COLUMN_MAX_RHO,
}


def _int_diameter(val: Any, allowed: Sequence[int], label: str) -> int:
    if isinstance(val, bool) or not isinstance(val, int) or val not in allowed:
        raise ValueError(f"INVALID_DIAMETER:{label}:{val!r}")
    return val


def _pos_float(val: Any, label: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"INVALID_POSITIVE_NUMBER:{label}:{val!r}")
    fval = float(val)
    if not math.isfinite(fval) or fval <= 0:
        raise ValueError(f"INVALID_POSITIVE_NUMBER:{label}:{val!r}")
    return fval


def normalize_beam_selection_policy(raw: Mapping[str, Any] | str | None) -> dict[str, Any]:
    """Validate and normalize an engineer beam rebar selection policy."""
    if raw is None or raw == "default":
        return {
            **DEFAULT_BEAM_SELECTION_POLICY,
            "top_continuous": dict(DEFAULT_BEAM_SELECTION_POLICY["top_continuous"]),
            "bottom_continuous": dict(DEFAULT_BEAM_SELECTION_POLICY["bottom_continuous"]),
            "allowed_additional_diameters_mm": list(DEFAULT_BEAM_SELECTION_POLICY["allowed_additional_diameters_mm"]),
            "stirrup_confinement": dict(DEFAULT_BEAM_SELECTION_POLICY["stirrup_confinement"]),
            "stirrup_span": dict(DEFAULT_BEAM_SELECTION_POLICY["stirrup_span"]),
        }
    if not isinstance(raw, Mapping):
        raise ValueError("BEAM_SELECTION_POLICY_MUST_BE_MAPPING")
    merged = {
        **DEFAULT_BEAM_SELECTION_POLICY,
        "top_continuous": {**DEFAULT_BEAM_SELECTION_POLICY["top_continuous"], **(raw.get("top_continuous") or {})},
        "bottom_continuous": {**DEFAULT_BEAM_SELECTION_POLICY["bottom_continuous"], **(raw.get("bottom_continuous") or {})},
        "stirrup_confinement": {**DEFAULT_BEAM_SELECTION_POLICY["stirrup_confinement"], **(raw.get("stirrup_confinement") or {})},
        "stirrup_span": {**DEFAULT_BEAM_SELECTION_POLICY["stirrup_span"], **(raw.get("stirrup_span") or {})},
    }
    for face_key in ("top_continuous", "bottom_continuous"):
        cnt = merged[face_key].get("count")
        if isinstance(cnt, bool) or not isinstance(cnt, int) or cnt < 2:
            raise ValueError(f"BEAM_CONTINUOUS_COUNT_INVALID:{face_key}:{cnt!r}")
        _int_diameter(merged[face_key].get("diameter_mm"), SELECTED_LONG_DIAMETERS, face_key)

    add_raw = raw.get("allowed_additional_diameters_mm", DEFAULT_BEAM_SELECTION_POLICY["allowed_additional_diameters_mm"])
    if not isinstance(add_raw, (list, tuple)) or not add_raw:
        raise ValueError("BEAM_ALLOWED_ADDITIONAL_DIAMETERS_REQUIRED")
    merged["allowed_additional_diameters_mm"] = sorted({
        _int_diameter(d, SELECTED_LONG_DIAMETERS, "allowed_additional") for d in add_raw
    })

    for zone_key in ("stirrup_confinement", "stirrup_span"):
        zone = merged[zone_key]
        _int_diameter(zone.get("diameter_mm"), TIE_ALLOWED_DIAMETERS, zone_key)
        zone["spacing_mm"] = _pos_float(zone.get("spacing_mm"), f"{zone_key}.spacing_mm")
        legs = zone.get("legs")
        if isinstance(legs, bool) or not isinstance(legs, int) or legs < 2:
            raise ValueError(f"BEAM_STIRRUP_LEGS_INVALID:{zone_key}:{legs!r}")

    for flag in ("strictly_exceed_required", "enforce_tbdy_rho_min", "enforce_support_half_ratio"):
        merged[flag] = bool(raw.get(flag, DEFAULT_BEAM_SELECTION_POLICY[flag]))
    max_rows = raw.get("max_rows_per_face", DEFAULT_BEAM_SELECTION_POLICY["max_rows_per_face"])
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or not 1 <= max_rows <= 4:
        raise ValueError(f"BEAM_MAX_ROWS_INVALID:{max_rows!r}")
    merged["max_rows_per_face"] = max_rows
    return merged


def normalize_column_selection_policy(raw: Mapping[str, Any] | str | None) -> dict[str, Any]:
    """Validate and normalize an engineer column rebar selection policy."""
    if raw is None or raw == "default":
        return {
            **DEFAULT_COLUMN_SELECTION_POLICY,
            "allowed_longitudinal_diameters_mm": list(DEFAULT_COLUMN_SELECTION_POLICY["allowed_longitudinal_diameters_mm"]),
            "tie_diameter_preference_mm": list(DEFAULT_COLUMN_SELECTION_POLICY["tie_diameter_preference_mm"]),
        }
    if not isinstance(raw, Mapping):
        raise ValueError("COLUMN_SELECTION_POLICY_MUST_BE_MAPPING")
    long_raw = raw.get("allowed_longitudinal_diameters_mm", DEFAULT_COLUMN_SELECTION_POLICY["allowed_longitudinal_diameters_mm"])
    if not isinstance(long_raw, (list, tuple)) or not long_raw:
        raise ValueError("COLUMN_ALLOWED_LONGITUDINAL_DIAMETERS_REQUIRED")
    long_diams = sorted({
        _int_diameter(d, COLUMN_ALLOWED_LONG_DIAMETERS, "column_longitudinal") for d in long_raw
    })
    tie_raw = raw.get("tie_diameter_preference_mm", DEFAULT_COLUMN_SELECTION_POLICY["tie_diameter_preference_mm"])
    if not isinstance(tie_raw, (list, tuple)) or not tie_raw:
        raise ValueError("COLUMN_TIE_DIAMETERS_REQUIRED")
    # Preserve user ordering (e.g., [8, 10, 12] means try 8 first, then 10, 12)
    tie_diams: list[int] = []
    for d in tie_raw:
        val = _int_diameter(d, TIE_ALLOWED_DIAMETERS, "column_tie")
        if val not in tie_diams:
            tie_diams.append(val)
    min_rho = _pos_float(raw.get("min_rho", COLUMN_MIN_RHO), "min_rho")
    max_rho = _pos_float(raw.get("max_rho", COLUMN_MAX_RHO), "max_rho")
    if min_rho < COLUMN_MIN_RHO or max_rho > COLUMN_MAX_RHO:
        raise ValueError("COLUMN_POLICY_CANNOT_RELAX_SUPPORTED_TBDY_REBAR_LIMITS")
    if min_rho >= max_rho:
        raise ValueError("COLUMN_RHO_BOUNDS_INVALID")
    return {
        **DEFAULT_COLUMN_SELECTION_POLICY,
        "allowed_longitudinal_diameters_mm": long_diams,
        "tie_diameter_preference_mm": tie_diams,
        "stirrup_confinement_spacing_mm": _pos_float(
            raw.get("stirrup_confinement_spacing_mm", DEFAULT_COLUMN_SELECTION_POLICY["stirrup_confinement_spacing_mm"]),
            "stirrup_confinement_spacing_mm",
        ),
        "stirrup_span_spacing_mm": _pos_float(
            raw.get("stirrup_span_spacing_mm", DEFAULT_COLUMN_SELECTION_POLICY["stirrup_span_spacing_mm"]),
            "stirrup_span_spacing_mm",
        ),
        "strictly_exceed_required": bool(raw.get("strictly_exceed_required", True)),
        "min_rho": min_rho,
        "max_rho": max_rho,
    }


def _bar_area(diameter_mm: int) -> float:
    return math.pi * (diameter_mm ** 2) / 4.0


def _needed_additional_count(*, required_area_mm2: float, continuous_area_mm2: float, add_diam_mm: int, strict: bool) -> int:
    deficit = required_area_mm2 - continuous_area_mm2
    if deficit < 0 and (not strict or continuous_area_mm2 > required_area_mm2 + 1e-6):
        return 0
    if abs(deficit) <= 1e-6:
        return 1 if strict else 0
    a_bar = _bar_area(add_diam_mm)
    cnt = max(1, math.ceil(deficit / a_bar))
    if strict and (continuous_area_mm2 + cnt * a_bar) <= required_area_mm2 + 1e-6:
        cnt += 1
    return cnt


def select_beam_station_rebar(
    *,
    profile: Mapping[str, Any],
    top_req_mm2: float,
    bot_req_mm2: float,
    rho_bounds: Mapping[str, float],
    policy: Mapping[str, Any],
    is_support: bool = True,
) -> dict[str, Any]:
    """Select continuous + additional longitudinal beam bars strictly exceeding required area."""
    h_mm = float(profile["local2_height_mm"])
    b_mm = float(profile["local3_width_mm"])
    cov_top = float(profile["cover_top_centroid_mm"])
    cov_bot = float(profile["cover_bottom_centroid_mm"])

    top_cont_n = policy["top_continuous"]["count"]
    top_cont_d = policy["top_continuous"]["diameter_mm"]
    bot_cont_n = policy["bottom_continuous"]["count"]
    bot_cont_d = policy["bottom_continuous"]["diameter_mm"]
    tie_d = policy["stirrup_confinement"]["diameter_mm"]
    add_diams = tuple(policy["allowed_additional_diameters_mm"])
    strict = bool(policy["strictly_exceed_required"])

    # Nominal TBDY rho_min area reference (refined with effective depth after layout)
    nom_as_min_top = rho_bounds["rho_min"] * b_mm * max(1.0, h_mm - cov_top) if policy["enforce_tbdy_rho_min"] else 0.0
    nom_as_min_bot = rho_bounds["rho_min"] * b_mm * max(1.0, h_mm - cov_bot) if policy["enforce_tbdy_rho_min"] else 0.0
    t_top = max(top_req_mm2, nom_as_min_top)
    t_bot = max(bot_req_mm2, nom_as_min_bot)

    a_top_cont = top_cont_n * _bar_area(top_cont_d)
    a_bot_cont = bot_cont_n * _bar_area(bot_cont_d)

    # Evaluate valid (top_add_d, bot_add_d) combinations across allowed additional diameters
    top_choices: list[tuple[int, int]] = []
    if (not strict and a_top_cont >= t_top - 1e-6) or (strict and a_top_cont > t_top + 1e-6):
        top_choices.append((0, add_diams[0]))
    else:
        for d in add_diams:
            top_choices.append((_needed_additional_count(required_area_mm2=t_top, continuous_area_mm2=a_top_cont, add_diam_mm=d, strict=strict), d))

    viable: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for top_add_n, top_add_d in top_choices:
        a_top_prov = a_top_cont + top_add_n * _bar_area(top_add_d)
        bot_eff_target = max(t_bot, 0.5 * a_top_prov) if (is_support and policy["enforce_support_half_ratio"]) else t_bot
        bot_choices: list[tuple[int, int]] = []
        if (not strict and a_bot_cont >= bot_eff_target - 1e-6) or (strict and a_bot_cont > bot_eff_target + 1e-6):
            bot_choices.append((0, add_diams[0]))
        else:
            for d in add_diams:
                bot_choices.append((_needed_additional_count(required_area_mm2=bot_eff_target, continuous_area_mm2=a_bot_cont, add_diam_mm=d, strict=strict), d))
        for bot_add_n, bot_add_d in bot_choices:
            cage = build_selected_beam_cage(
                dict(profile),
                top_continuous_count=top_cont_n,
                top_continuous_diameter_mm=top_cont_d,
                top_additional_count=top_add_n,
                top_additional_diameter_mm=top_add_d,
                bottom_continuous_count=bot_cont_n,
                bottom_continuous_diameter_mm=bot_cont_d,
                bottom_additional_count=bot_add_n,
                bottom_additional_diameter_mm=bot_add_d,
                target_top_mm2=t_top,
                target_bottom_mm2=bot_eff_target,
                tie_diameter_mm=tie_d,
                max_rows_per_face=int(policy["max_rows_per_face"]),
            )
            eff_d_top = h_mm - (cage["effective_top_centroid_mm"] or cov_top)
            eff_d_bot = h_mm - (cage["effective_bottom_centroid_mm"] or cov_bot)
            rho_top = cage["area_top_mm2"] / (b_mm * eff_d_top) if eff_d_top > 0 else None
            rho_bot = cage["area_bottom_mm2"] / (b_mm * eff_d_bot) if eff_d_bot > 0 else None
            rho_ok = (
                rho_top is not None
                and rho_bot is not None
                and rho_bounds["rho_min"] <= rho_top <= rho_bounds["rho_max"]
                and rho_bounds["rho_min"] <= rho_bot <= rho_bounds["rho_max"]
            )
            half_ok = (
                not is_support
                or not policy["enforce_support_half_ratio"]
                or min(cage["area_top_mm2"], cage["area_bottom_mm2"]) >= 0.5 * max(cage["area_top_mm2"], cage["area_bottom_mm2"]) - 1e-6
            )
            excess_ratio_top = cage["area_top_mm2"] / t_top if t_top > 0 else None
            excess_ratio_bot = cage["area_bottom_mm2"] / t_bot if t_bot > 0 else None
            present_diams = [top_cont_d, bot_cont_d] + ([top_add_d] if top_add_n > 0 else []) + ([bot_add_d] if bot_add_n > 0 else [])
            entry = {
                **cage,
                "effective_target_top_mm2": t_top,
                "effective_target_bottom_mm2": bot_eff_target,
                "rho_top": rho_top,
                "rho_bottom": rho_bot,
                "rho_bounds_met": rho_ok,
                "support_compression_half_tension_met": half_ok,
                "excess_ratio_top": excess_ratio_top,
                "excess_ratio_bottom": excess_ratio_bot,
                "min_longitudinal_diameter_mm": min(present_diams),
                "max_longitudinal_diameter_mm": max(present_diams),
            }
            if (
                cage["status"] == "BEAM_SELECTED_CALCULATED"
                and (cage["strictly_exceeds_targets"] if strict else cage["covers_targets"])
                and rho_ok
                and half_ok
            ):
                viable.append(entry)
            else:
                if cage["status"] == "BEAM_SELECTED_CALCULATED" and not rho_ok:
                    entry["reason"] = "BEAM_SELECTED_RHO_OUTSIDE_TBDY_BOUNDS"
                elif cage["status"] == "BEAM_SELECTED_CALCULATED" and not half_ok:
                    entry["reason"] = "BEAM_SELECTED_SUPPORT_HALF_RATIO_NOT_MET"
                rejected.append(entry)

    if viable:
        viable.sort(key=lambda e: (
            0 if e["layout_mode"] == "SINGLE_ROW" else 1,
            round(e["area_top_mm2"] + e["area_bottom_mm2"], 3),
            e["max_longitudinal_diameter_mm"],
        ))
        best = viable[0]
        return {
            **best,
            "selection_status": "ENGINEER_REBAR_SELECTED_NOT_PROVEN",
            "alternative_valid_count": len(viable),
            "rejected_count": len(rejected),
        }

    # No candidate satisfied every constraint cleanly — return best failed diagnostic
    fallback = rejected[0] if rejected else {"status": "BEAM_SELECTED_CAGE_BLOCKED", "reason": "NO_VIABLE_BEAM_CAGE"}
    return {
        **fallback,
        "selection_status": "ENGINEER_REBAR_SELECTION_BLOCKED",
        "alternative_valid_count": 0,
        "rejected_count": len(rejected),
    }


def evaluate_beam_stirrups(
    *,
    b_mm: float,
    h_mm: float,
    d_eff_mm: float,
    min_long_diameter_mm: int,
    fctd_mpa: float,
    fcd_mpa: float,
    fywk_mpa: float | None,
    gamma_s: float,
    ve_eq_kn: float | None,
    ve_total_kn: float | None,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate TBDY 2018 §7.4.4 / §7.4.5 shear and confinement checks for Φ8/10 and Φ8/15."""
    vr_max_kn = max_shear_web_kn(fcd_mpa=fcd_mpa, bw_mm=b_mm, d_mm=d_eff_mm)
    fywd_mpa = positive(fywk_mpa, "fywk_mpa") / positive(gamma_s, "gamma_s") if fywk_mpa else None

    def _eval_zone(zone_key: str, zone_cfg: Mapping[str, Any], is_confinement: bool) -> dict[str, Any]:
        dw = int(zone_cfg["diameter_mm"])
        s = float(zone_cfg["spacing_mm"])
        legs = int(zone_cfg["legs"])
        asw = legs * _bar_area(dw)
        s_limit = (
            min(h_mm / 4.0, 8.0 * float(min_long_diameter_mm), 150.0)
            if is_confinement
            else min(d_eff_mm / 2.0, 300.0)
        )
        spacing_ok = s <= s_limit + 1e-6
        rho_w = asw / (b_mm * s)
        rho_w_min = (0.3 * fctd_mpa / fywd_mpa) if fywd_mpa else None
        min_ratio_ok = (rho_w >= rho_w_min - 1e-9) if rho_w_min is not None else None
        vw_kn = (asw / s) * fywd_mpa * d_eff_mm / 1000.0 if fywd_mpa else None
        vcr_kn = 0.65 * fctd_mpa * b_mm * d_eff_mm / 1000.0
        # TBDY 7.4.5.3: conservative Vc=0 in confinement zone until Ve seismic share <= 0.5*Ve is proven
        vr_conservative_kn = vw_kn if is_confinement else ((0.8 * vcr_kn + vw_kn) if vw_kn is not None else None)
        vr_with_vc_kn = (0.8 * vcr_kn + vw_kn) if vw_kn is not None else None
        demand_kn = ve_total_kn if ve_total_kn is not None else ve_eq_kn
        util_conservative = (demand_kn / vr_conservative_kn) if (demand_kn is not None and vr_conservative_kn) else None
        alerts: list[str] = []
        if not spacing_ok:
            if is_confinement and 8.0 * float(min_long_diameter_mm) < s:
                alerts.append(
                    f"TBDY_7_4_4_4_SPACING_EXCEEDS_8_D_MIN:{s:.0f}mm>{8*min_long_diameter_mm:.0f}mm"
                )
            else:
                alerts.append(f"TBDY_7_4_4_SPACING_EXCEEDS_LIMIT:{s:.0f}mm>{s_limit:.1f}mm")
        if min_ratio_ok is False:
            alerts.append("TS500_MIN_STIRRUP_RATIO_NOT_MET")
        if util_conservative is not None and util_conservative > 1.0:
            alerts.append("SHEAR_DEMAND_EXCEEDS_CONSERVATIVE_VR")
        return {
            "zone": zone_key,
            "label": f"Φ{dw}/{int(round(s))}" if abs(s - round(s)) < 1e-6 else f"Φ{dw}/{s:.1f}",
            "diameter_mm": dw,
            "spacing_mm": s,
            "legs": legs,
            "asw_mm2": asw,
            "zone_length_mm": BEAM_CONFINEMENT_REGION_FACTOR * h_mm if is_confinement else None,
            "tbdy_spacing_limit_mm": s_limit,
            "spacing_ok": spacing_ok,
            "rho_w": rho_w,
            "rho_w_min": rho_w_min,
            "min_ratio_ok": min_ratio_ok,
            "vw_kn": vw_kn,
            "vcr_kn": vcr_kn,
            "vr_conservative_kn": vr_conservative_kn,
            "vr_with_concrete_kn": vr_with_vc_kn,
            "demand_kn": demand_kn,
            "demand_basis": "FULL_VE" if ve_total_kn is not None else ("EQ_TERM_ONLY_VDY_MISSING" if ve_eq_kn is not None else "NOT_BOUND"),
            "utilization_conservative": util_conservative,
            "alerts": alerts,
        }

    conf = _eval_zone("CONFINEMENT_2H", policy["stirrup_confinement"], True)
    span = _eval_zone("MIDSPAN", policy["stirrup_span"], False)
    return {
        "fywk_mpa": fywk_mpa,
        "fywd_mpa": fywd_mpa,
        "vr_max_kn": vr_max_kn,
        "confinement": conf,
        "span": span,
        "alerts": [*conf["alerts"], *span["alerts"]],
    }


def _min_crosstie_legs_for_face(*, face_extent_mm: float, cover_mm: float, tie_mm: float, n_bars: int) -> tuple[int, float]:
    """Return minimum tied legs (>= 2) along a face so distance `a` between tied bars <= 25 * phi_tie."""
    max_a = 25.0 * tie_mm
    core_span = max(1.0, face_extent_mm - 2.0 * cover_mm)
    if n_bars <= 2 or core_span <= max_a:
        return 2, core_span
    bar_pitch = core_span / (n_bars - 1)
    # Try leg count from 2 up to n_bars; alternating ties work when bar_pitch <= max_a / 2 etc.
    for legs in range(2, n_bars + 1):
        # Maximum spacing between tied longitudinal bars when distributing `legs` ties across `n_bars` positions
        max_step = math.ceil((n_bars - 1) / (legs - 1))
        a_eff = max_step * bar_pitch
        if a_eff <= max_a + 1e-6:
            return legs, a_eff
    return n_bars, bar_pitch


def _column_pmm_demand_check(
    *,
    section: Section,
    dims_mm: Any,
    local_axis_angle_deg: float | None,
    demand_vectors: Sequence[Mapping[str, Any]],
) -> tuple[bool, float | None, str | None]:
    """Evaluate all captured static vectors against 3D fiber PMM solver (with min eccentricity)."""
    if not demand_vectors:
        return False, None, "COLUMN_DEMAND_VECTORS_MISSING"
    if local_axis_angle_deg is None:
        return False, None, "COLUMN_LOCAL_AXIS_ANGLE_MISSING"
    sol = solver(section)
    max_util = 0.0
    for vec in demand_vectors:
        nd_kn = float(vec["nd_kn"])
        m2_knm = float(vec["m2_knm"])
        m3_knm = float(vec["m3_knm"])
        ecc = apply_minimum_eccentricity(
            nd_kn=nd_kn, m2_knm=m2_knm, m3_knm=m3_knm,
            dims=dims_mm, local_axis_angle_deg=local_axis_angle_deg,
        )
        m2_d = ecc["m2_design_knm"]
        m3_d = ecc["m3_design_knm"]
        ev = sol.assess(nd_kn * 1000.0, m2_d * 1_000_000.0, m3_d * 1_000_000.0)
        util = ev.get("utilization")
        if util is None and ev.get("status") == "AXIAL_ONLY_SCENARIO":
            util = ev.get("axial_utilization")
        if util is None:
            return False, None, ev.get("reason") or ev.get("status") or "COLUMN_PMM_NUMERICAL_UNRESOLVED"
        max_util = max(max_util, float(util))
    # Strictly < 1.0 -> capacity strictly exceeds demand ("gerekenden fazla")
    return max_util < 1.0 - 1e-6, max_util, None


def _evaluate_column_transverse_choice(
    *,
    tie_d: int,
    s_conf_mm: float,
    s_span_mm: float,
    long_d: int,
    n2: int,
    n3: int,
    t2_mm: float,
    t3_mm: float,
    cover_mm: float,
    fck_mpa: float,
    fywk_mpa: float,
    gamma_c: float,
    gamma_s: float,
    shear_demands: Sequence[Mapping[str, float]],
) -> dict[str, Any]:
    """Evaluate TBDY 7.3.4 / 7.3.7 confinement and shear for a column tie diameter + spacing choice."""
    tie_area = _bar_area(tie_d)
    ts500_tie_min = max(8.0, long_d / 3.0)
    tie_size_ok = tie_d >= ts500_tie_min - 1e-6

    # Legs parallel to local 2 resist shear V2 & confine edge t3 (along n3 intervals)
    legs_2, a_3 = _min_crosstie_legs_for_face(face_extent_mm=t3_mm, cover_mm=cover_mm, tie_mm=float(tie_d), n_bars=n3)
    legs_3, a_2 = _min_crosstie_legs_for_face(face_extent_mm=t2_mm, cover_mm=cover_mm, tie_mm=float(tie_d), n_bars=n2)
    crossties_per_set_x2 = max(0, legs_3 - 2)
    crossties_per_set_x3 = max(0, legs_2 - 2)
    a_max_limit = 25.0 * tie_d
    a_ok = max(a_2, a_3) <= a_max_limit + 1e-6

    ac = t2_mm * t3_mm
    ack = max(1.0, (t2_mm - 2.0 * cover_mm) * (t3_mm - 2.0 * cover_mm))
    bk2 = max(1.0, t3_mm - 2.0 * cover_mm - tie_d)
    bk3 = max(1.0, t2_mm - 2.0 * cover_mm - tie_d)
    bk_min = min(bk2, bk3)

    conf_s_limit = min(bk_min / 3.0, 6.0 * float(long_d), 150.0)
    span_s_limit = min(bk_min / 2.0, 12.0 * float(long_d), 200.0)
    conf_s_ok = 50.0 <= s_conf_mm <= conf_s_limit + 1e-6
    span_s_ok = s_span_mm <= span_s_limit + 1e-6

    asw2 = legs_2 * tie_area
    asw3 = legs_3 * tie_area
    conf_v2 = confinement_reference(
        area_mm2=ac, core_area_mm2=ack, bk_mm=bk2, spacing_mm=s_conf_mm,
        fck_mpa=fck_mpa, fywk_mpa=fywk_mpa, ash_mm2=asw2,
    )
    conf_v3 = confinement_reference(
        area_mm2=ac, core_area_mm2=ack, bk_mm=bk3, spacing_mm=s_conf_mm,
        fck_mpa=fck_mpa, fywk_mpa=fywk_mpa, ash_mm2=asw3,
    )
    high_axial = (not shear_demands) or any(st["nd_kn"] * 1000.0 > 0.2 * ac * fck_mpa for st in shear_demands)
    ash_key = "high_axial_reference_met" if high_axial else "low_axial_reference_met"
    ash_ok = bool(conf_v2[ash_key] and conf_v3[ash_key])

    center = cover_mm + tie_d + long_d / 2.0
    max_v2_util = 0.0
    max_v3_util = 0.0
    max_v2_zero_util = 0.0
    max_v3_zero_util = 0.0
    vr_max_ok = True
    for st in shear_demands:
        v2_ref = shear_reference(
            n_compression_kn=st["nd_kn"], shear_kn=st["v2_kn"], area_mm2=ac,
            bw_mm=t3_mm, d_mm=max(1.0, t2_mm - center), fck_mpa=fck_mpa, fywk_mpa=fywk_mpa,
            asw_mm2=asw2, spacing_mm=s_conf_mm, gamma_c=gamma_c, gamma_s=gamma_s,
        )
        v3_ref = shear_reference(
            n_compression_kn=st["nd_kn"], shear_kn=st["v3_kn"], area_mm2=ac,
            bw_mm=t2_mm, d_mm=max(1.0, t3_mm - center), fck_mpa=fck_mpa, fywk_mpa=fywk_mpa,
            asw_mm2=asw3, spacing_mm=s_conf_mm, gamma_c=gamma_c, gamma_s=gamma_s,
        )
        if v2_ref["branches"]["ts500"]["source_utilization"] is not None:
            max_v2_util = max(max_v2_util, float(v2_ref["branches"]["ts500"]["source_utilization"]))
        if v3_ref["branches"]["ts500"]["source_utilization"] is not None:
            max_v3_util = max(max_v3_util, float(v3_ref["branches"]["ts500"]["source_utilization"]))
        if v2_ref["branches"]["zero_concrete"]["source_utilization"] is not None:
            max_v2_zero_util = max(max_v2_zero_util, float(v2_ref["branches"]["zero_concrete"]["source_utilization"]))
        if v3_ref["branches"]["zero_concrete"]["source_utilization"] is not None:
            max_v3_zero_util = max(max_v3_zero_util, float(v3_ref["branches"]["zero_concrete"]["source_utilization"]))
        if (
            not v2_ref["source_within_ts500_web_reference"]
            or not v3_ref["source_within_ts500_web_reference"]
            or not v2_ref["source_within_tbdy_brittle_reference"]
            or not v3_ref["source_within_tbdy_brittle_reference"]
        ):
            vr_max_ok = False

    shear_ts500_ok = vr_max_ok and max_v2_util <= 1.0 + 1e-6 and max_v3_util <= 1.0 + 1e-6
    shear_zero_ok = vr_max_ok and max_v2_zero_util <= 1.0 + 1e-6 and max_v3_zero_util <= 1.0 + 1e-6
    alerts: list[str] = []
    if not tie_size_ok:
        alerts.append(f"TS500_TIE_DIA_BELOW_LONG_OVER_3:Φ{tie_d}<{ts500_tie_min:.1f}mm")
    if not a_ok:
        alerts.append(f"TBDY_7_3_4_1_CROSSTIE_SPACING_EXCEEDS_25_PHI:{max(a_2, a_3):.1f}mm>{a_max_limit:.0f}mm")
    if not conf_s_ok:
        alerts.append(f"TBDY_7_3_4_1_CONFINEMENT_SPACING:{s_conf_mm:.0f}mm>{conf_s_limit:.1f}mm")
    if not span_s_ok:
        alerts.append(f"TBDY_7_3_4_2_MIDSPAN_SPACING:{s_span_mm:.0f}mm>{span_s_limit:.1f}mm")
    if not ash_ok:
        alerts.append("TBDY_7_3_4_1_ASH_REQUIRED_EXCEEDS_PROVIDED")
    if not shear_ts500_ok:
        alerts.append("COLUMN_SHEAR_EXCEEDS_TS500_OR_VRMAX")

    return {
        "confinement_label": f"Φ{tie_d}/{int(round(s_conf_mm))}",
        "midspan_label": f"Φ{tie_d}/{int(round(s_span_mm))}",
        "tie_diameter_mm": tie_d,
        "confinement_spacing_mm": s_conf_mm,
        "midspan_spacing_mm": s_span_mm,
        "legs_v2": legs_2,
        "legs_v3": legs_3,
        "crossties_parallel_v2": crossties_per_set_x3,
        "crossties_parallel_v3": crossties_per_set_x2,
        "crosstie_max_spacing_a_mm": max(a_2, a_3),
        "crosstie_limit_25_phi_mm": a_max_limit,
        "tie_size_ok": tie_size_ok,
        "crosstie_a_ok": a_ok,
        "confinement_spacing_limit_mm": conf_s_limit,
        "confinement_spacing_ok": conf_s_ok,
        "midspan_spacing_limit_mm": span_s_limit,
        "midspan_spacing_ok": span_s_ok,
        "ash_satisfied": ash_ok,
        "confinement_v2": conf_v2,
        "confinement_v3": conf_v3,
        "max_v2_ts500_utilization": max_v2_util if shear_demands else None,
        "max_v3_ts500_utilization": max_v3_util if shear_demands else None,
        "max_v2_zero_concrete_utilization": max_v2_zero_util if shear_demands else None,
        "max_v3_zero_concrete_utilization": max_v3_zero_util if shear_demands else None,
        "shear_ts500_ok": shear_ts500_ok,
        "shear_zero_concrete_ok": shear_zero_ok,
        "core_requirements_met": tie_size_ok and a_ok and ash_ok and shear_ts500_ok,
        "all_tbdy_checks_met": tie_size_ok and a_ok and conf_s_ok and span_s_ok and ash_ok and shear_ts500_ok,
        "alerts": alerts,
    }


def select_column_rebar(
    *,
    t2_mm: float,
    t3_mm: float,
    cover_mm: float,
    fck_mpa: float,
    fcd_mpa: float,
    fyd_mpa: float,
    es_mpa: float,
    fywk_mpa: float,
    gamma_c: float,
    gamma_s: float,
    local_axis_angle_deg: float | None,
    demand_vectors: Sequence[Mapping[str, Any]],
    shear_demands: Sequence[Mapping[str, float]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Select rectangular column longitudinal count (14,16,20,22,24,25) and Φ8->Φ10->Φ12 ties/crossties."""
    # Inputs are Section.t2/t3: extents along kernel local-2/local-3, not native CSI T2/T3.
    dims = LocalSectionDims(t2_mm, t3_mm)
    ac = t2_mm * t3_mm
    tbdy_minimum_area_mm2 = COLUMN_MIN_RHO * ac
    minimum_area_mm2 = max(tbdy_minimum_area_mm2, float(policy["min_rho"]) * ac)
    maximum_area_mm2 = min(COLUMN_MAX_RHO, float(policy["max_rho"])) * ac
    mat = Material(fck=fck_mpa, fcd=fcd_mpa, fyd=fyd_mpa, es=es_mpa)

    s_conf = float(policy["stirrup_confinement_spacing_mm"])
    s_span = float(policy["stirrup_span_spacing_mm"])
    tie_prefs = list(policy["tie_diameter_preference_mm"])

    candidates_by_diam: dict[str, Any] = {}
    passing_candidates: list[dict[str, Any]] = []

    for diam in policy["allowed_longitudinal_diameters_mm"]:
        bar_area = _bar_area(diam)
        min_legal_tie = next((t for t in tie_prefs if t >= diam / 3.0 - 1e-6), tie_prefs[-1])
        # Filter feasible (n2, n3) grids that meet clear spacing and 1%..4% rho bounds
        grid_options: list[tuple[float, int, int, int, tuple[Bar, ...], float]] = []
        min_clear_req = max(1.5 * diam, 40.0)
        for n2 in range(2, 17):
            for n3 in range(2, 17):
                total_bars = 2 * n2 + 2 * n3 - 4
                area_mm2 = total_bars * bar_area
                # TBDY §7.3.2.1 permits equality and does not permit a deficit.
                if not minimum_area_mm2 <= area_mm2 <= maximum_area_mm2:
                    continue
                try:
                    bars, _, spacing = perimeter(t2_mm, t3_mm, cover_mm, float(min_legal_tie), float(diam), n2=n2, n3=n3)
                except ValueError:
                    continue
                if spacing < min_clear_req - 1e-6:
                    continue
                # Prefer reasonably balanced face spacing over extreme aspect-mismatched cages of equal bar count
                balance_penalty = abs((t2_mm / max(1, n2 - 1)) - (t3_mm / max(1, n3 - 1)))
                grid_options.append((area_mm2 + 1e-3 * balance_penalty, total_bars, n2, n3, bars, spacing))
        grid_options.sort(key=lambda item: item[0])

        chosen_for_diam: dict[str, Any] | None = None
        last_failed: dict[str, Any] | None = None
        for _, total_bars, n2, n3, bars, spacing in grid_options:
            area_mm2 = total_bars * bar_area
            rho = area_mm2 / ac
            # Pick tie diameter in preference order [8, 10, 12]
            tie_evals: list[dict[str, Any]] = []
            selected_tie: dict[str, Any] | None = None
            for t_d in tie_prefs:
                t_res = _evaluate_column_transverse_choice(
                    tie_d=t_d, s_conf_mm=s_conf, s_span_mm=s_span, long_d=diam,
                    n2=n2, n3=n3, t2_mm=t2_mm, t3_mm=t3_mm, cover_mm=cover_mm,
                    fck_mpa=fck_mpa, fywk_mpa=fywk_mpa, gamma_c=gamma_c, gamma_s=gamma_s,
                    shear_demands=shear_demands,
                )
                tie_evals.append(t_res)
                if selected_tie is None and t_res["all_tbdy_checks_met"]:
                    selected_tie = t_res
            if selected_tie is None:
                selected_tie = next((t for t in tie_evals if t["core_requirements_met"]), tie_evals[0])

            eff_tie_d = int(selected_tie["tie_diameter_mm"])
            if eff_tie_d != min_legal_tie:
                try:
                    bars, _, spacing = perimeter(t2_mm, t3_mm, cover_mm, float(eff_tie_d), float(diam), n2=n2, n3=n3)
                except ValueError:
                    continue
                if spacing < min_clear_req - 1e-6:
                    continue
            sec = Section(t2_mm, t3_mm, bars, mat)
            pmm_ok, max_util, pmm_err = _column_pmm_demand_check(
                section=sec, dims_mm=dims, local_axis_angle_deg=local_axis_angle_deg, demand_vectors=demand_vectors,
            )

            record = {
                "label": f"{total_bars}Φ{diam}",
                "diameter_mm": diam,
                "bar_count": total_bars,
                "num_bars_2_dir": n2,
                "num_bars_3_dir": n3,
                "area_mm2": area_mm2,
                "rho": rho,
                "rho_percent": 100.0 * rho,
                "minimum_clear_spacing_mm": spacing,
                "pmm_satisfied": pmm_ok,
                "pmm_max_utilization": max_util,
                "pmm_error": pmm_err,
                "selected_transverse": selected_tie,
                "transverse_candidates_tried": tie_evals,
                "eligible": bool(pmm_ok and selected_tie["core_requirements_met"]),
            }
            if record["eligible"]:
                chosen_for_diam = record
                break
            if chosen_for_diam is None and pmm_ok:
                # Track first PMM-passing grid in case none meets transverse core_requirements
                last_failed = record
            elif last_failed is None:
                last_failed = record

        res_d = chosen_for_diam or last_failed or {
            "label": None, "diameter_mm": diam, "eligible": False,
            "pmm_satisfied": False, "pmm_error": "NO_GEOMETRICALLY_VALID_GRID_IN_1_TO_4_PERCENT",
        }
        candidates_by_diam[str(diam)] = res_d
        if res_d.get("eligible"):
            passing_candidates.append(res_d)

    recommended = min(passing_candidates, key=lambda c: (c["area_mm2"], c["diameter_mm"])) if passing_candidates else None
    return {
        "schema": "tbdy.next.engineer-column-selection.v1",
        "origin": "ENGINEER_SELECTED_COLUMN_REBAR",
        "status": (
            "ENGINEER_COLUMN_SELECTED_NOT_PROVEN"
            if recommended is not None
            else "ENGINEER_COLUMN_SELECTION_NO_PASSING_CAGE"
        ),
        "selected": recommended,
        "minimum_longitudinal_area_mm2": minimum_area_mm2,
        "tbdy_minimum_longitudinal_area_mm2": tbdy_minimum_area_mm2,
        "candidates_by_diameter": candidates_by_diam,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
