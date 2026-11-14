"""Source-typed TBDY 4.9.2 story second-order numeric screening.

This is NOT an ETABS geometric-nonlinear analysis and is NOT a local P-delta
magnification. It cannot certify compliance without approved story population,
spectrum scaling, weight/mass source, and direction-matched displacements.
"""
from __future__ import annotations

import math

from tbdy_next.column_engine.native_archive import digest


class StorySourceError(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise StorySourceError(reason)


def finite(value, name: str, *, positive=False):
    need(type(value) in (int, float) and math.isfinite(value),
         "INVALID_STORY_NUMBER:" + name)
    x = float(value)
    need(x > 0 if positive else x >= 0, "INVALID_STORY_VALUE:" + name)
    return x


def review_story_pdelta(source: dict) -> dict:
    """Evaluate one consistent story census, returning reference-only theta_II.

    Required rows are individual story weights, *not cumulative ETEX Wi*.
    Each direction has its own response-spectrum shear and average drift.
    """
    need(isinstance(source, dict)
         and source.get("schema") == "tbdy.next.r08.story-source.v1",
         "STORY_SOURCE_SCHEMA_REQUIRED")
    need(source.get("weight_basis") == "G_PLUS_NQ"
         and source.get("weight_kind") == "INDIVIDUAL_STORY_WEIGHT"
         and source.get("weight_units") == "kN"
         and source.get("shear_units") == "kN"
         and source.get("drift_units") == "m"
         and source.get("height_units") == "m",
         "STORY_WEIGHT_OR_UNITS_SEMANTICS_UNPROVEN")
    need(source.get("combination_name") not in ("Grav_Service", "Grav_Ult")
         and source.get("weight_operator") == "Linear Add",
         "GRAVITY_COMBINATION_IS_NOT_SEISMIC_WEIGHT")
    weight_factors = source.get("weight_terms")
    need(isinstance(weight_factors, dict) and weight_factors,
         "WEIGHT_COMBINATION_AST_MISSING")
    need(all(isinstance(k, str) and k and type(v) in (int, float)
             and math.isfinite(v) and v >= 0
             for k, v in weight_factors.items()),
         "INVALID_WEIGHT_COEFFICIENT")
    need("LC_LL" in weight_factors, "LIVE_LOAD_MASS_PARTICIPATION_MISSING")
    n = finite(source.get("n_live"), "n_live")
    need(n <= 1 and abs(weight_factors["LC_LL"] - n) < 1e-12,
         "N_LIVE_FACTOR_NOT_RECONCILED")
    source_path = source.get("directions")
    need(isinstance(source_path, dict)
         and set(source_path) == {"X", "Y"}, "MISSING_DIRECTION_SOURCE_PATH")
    for axis, desired in (("X", "RSX"), ("Y", "RSY")):
        p = source_path[axis]
        need(isinstance(p, dict) and p.get("shear_case") == desired
             and p.get("drift_case") == desired
             and p.get("case_type") == "LinRespSpec"
             and p.get("step_type") == "Max",
             "MIXED_CASE_OR_UNSUPPORTED_SPECTRAL_DIRECTION:" + axis)
    meta = source.get("design_parameters")
    need(isinstance(meta, dict), "R_D_CH_BASIS_REQUIRED")
    ch = finite(meta.get("Ch"), "Ch", positive=True)
    limit = {}
    for axis in ("X", "Y"):
        r = finite(meta.get("R_" + axis), "R_" + axis, positive=True)
        d = finite(meta.get("D_" + axis), "D_" + axis, positive=True)
        limit[axis] = .12 * d / (ch * r)
    rows = source.get("stories")
    need(isinstance(rows, list) and rows, "STORY_POPULATION_EMPTY")
    need(len(rows) == len({row.get("story") for row in rows}),
         "DUPLICATE_STORY_ID")
    # The rows are ordered from highest story to lowest; this is the vertical sum in Eq.4.35.
    observed = []
    total_w = 0.
    previous_level = float("inf")
    for row in rows:
        need(isinstance(row, dict) and isinstance(row.get("story"), str)
             and row["story"], "INVALID_STORY_ROW")
        z = finite(row.get("level_m"), "level_m")
        need(z < previous_level, "STORIES_MUST_BE_TOP_TO_BOTTOM")
        previous_level = z
        wi = finite(row.get("individual_w_kN"), "individual_w_kN", positive=True)
        h = finite(row.get("height_m"), "height_m", positive=True)
        total_w += wi
        v = row.get("shear_kN")
        delta = row.get("average_reduced_drift_m")
        need(isinstance(v, dict) and set(v) == {"X", "Y"}
             and isinstance(delta, dict) and set(delta) == {"X", "Y"},
             "DIRECTIONAL_SHEAR_DRIFT_MISSING")
        axes = {}
        for axis in ("X", "Y"):
            vi = finite(v[axis], "V_" + axis, positive=True)
            di = finite(delta[axis], "delta_" + axis)
            theta = di * total_w / (vi * h)
            axes[axis] = {
                "case": source_path[axis]["shear_case"], "shear_kN": vi,
                "average_reduced_drift_m": di, "theta_II_reference": theta,
                "limit_reference": limit[axis],
                "below_limit_numeric": theta <= limit[axis],
                "beta_II_candidate": 1.0 if theta <= limit[axis] else None,
            }
        observed.append({
            "story": row["story"], "level_m": z, "height_m": h,
            "individual_weight_kN": wi, "cumulative_weight_kN": total_w,
            "axes": axes,
        })
    theta_max = {axis: max(row["axes"][axis]["theta_II_reference"] for row in observed)
                 for axis in ("X", "Y")}
    out = {
        "schema": "tbdy.next.r08.story-screening-result.v1",
        "status": "NUMERIC_REFERENCE_ONLY_NOT_DESIGN_ACCEPTANCE",
        "source_cases": source_path, "weight_basis": "G_PLUS_NQ",
        "source_declared_weights": "INDIVIDUAL_NOT_CUMULATIVE",
        "code_reference": "TBDY 2018 4.9.2 / Eq.4.35-4.36",
        "R_is_behavior_factor": True, "D_is_overstrength_factor": True,
        "rows": observed, "theta_max": theta_max, "limit_reference": limit,
        "all_observed_below_numeric_limit":
            all(theta_max[k] <= limit[k] for k in ("X", "Y")),
        "mass_source_vs_load_combination_proven_equivalent": False,
        "spectral_scale_and_full_story_population_proven": False,
        "actual_global_P_Delta_applied_proven": False,
        "local_column_P_delta_evaluated": False,
        "design_demand_approved": False,
        "engineering_verdict": "NOT_PROVEN", "engineering_release": "NOT_READY",
    }
    out["result_sha256"] = digest(out)
    return out
