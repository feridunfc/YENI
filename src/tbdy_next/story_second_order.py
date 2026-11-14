"""TBDY 2018 §4.9.2 story P–Delta SOURCE-NUMERICAL engine node.

This belongs to the YENI product DAG/receipt path, not to an exploration script.
No ETABS COM in this module.  Two SHA-sealed same-session gateway captures are
consumed; no load combination is silently treated as a response-spectrum case.
"""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
from typing import Any, Mapping

from .story_delta import dec, tbl, DeltaSourceError
from .story_drift_binding import _verify_generic_capture

CHECK_ID = "GLOBAL_SECOND_ORDER"
SCHEMA = "tbdy.next.r08.story-pdelta-source-numerical.v1"
CAPTURE_SCHEMA = "tbdy.next.r08.story-pdelta-capture.v1"
WEIGHT_TERMS = {
    "LC_DL": Decimal("1"), "LC_SDL": Decimal("1"),
    "LC_WDL": Decimal("1"), "LC_DDL": Decimal("1"),
    "LC_LL": Decimal("0.3"),
}
REQUIRED_GATE = (
    "SPECTRAL_METHOD_AND_BETA_TE_APPROVAL",
    "COLUMN_WALL_AVERAGE_DRIFT_NOT_PROVEN_BY_ETABS_AVG_DRIFT",
    "WGHT_VS_MASSSOURCE_AND_G_PLUS_NQ_NOT_APPROVED",
    "ANALYSIS_GENERATION_AND_PDELTA_ORDER_NOT_PROVEN",
    "R_D_CH_PROJECT_SELECTION_NOT_APPROVED",
    "INDEPENDENT_ETEX_AND_CODE_CHECK_PENDING",
)


def _base(capture_error: str | None) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "check_id": CHECK_ID,
        "dag_node_id": CHECK_ID, "dag_node_type": "REGULATORY_CHECK",
        "dag_declared_dependencies": ["BASE_SHEAR", "STORY_DRIFT"],
        "dag_execution_authority": "DENIED",
        "code_ref": "TBDY 2018 4.9.2.1–4.9.2.4 / 4.35–4.37",
        "status": "BLOCKED_SOURCE_UNAVAILABLE",
        "execution_status": "BLOCKED",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "global_p_delta_design_applied": False,
        "design_demand_approved": False,
        "results": [], "direction_results": {},
        "expected_story_direction_count": 0,
        "evaluated_story_direction_count": 0,
        "source_capture_error": capture_error,
        "missing_authorities": list(REQUIRED_GATE),
        "reason_codes": [],
        "source_sha256": None,
        "note": "Source-numerical theta only: never a global P–Delta design or a local P–delta calculation.",
    }


def _check_source(source: Mapping[str, Any], name: str, model: str) -> None:
    _verify_generic_capture(source)
    if (source.get("schema") != "tbdy.next.etabs.generic-source-capture.v1"
            or source.get("status") != "CAPTURED"
            or source.get("action") != "capture"
            or source.get("model") != model
            or source.get("model_locked") is not True
            or source.get("model_units_code") != 6
            or source.get("model_units_unchanged") is not True
            or source.get("selection_restored") is not True
            or source.get("analysis_generation_proven") is not False):
        raise DeltaSourceError("R08_SOURCE_INTEGRITY_OR_UNITS_INVALID:" + name)


def _table(source: Mapping[str, Any], key: str, required: set[str],
           units: dict[str, str] | None = None) -> list[dict[str, str]]:
    return tbl(source, key, required, units)


def _story_index(rows: list[dict[str, str]], case: str,
                 case_type: str) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["OutputCase"] != case or row["Location"] != "Bottom":
            continue
        if row["CaseType"] != case_type:
            raise DeltaSourceError("R08_STORY_FORCE_CASE_TYPE_INVALID:" + case)
        if "StepType" in row and row["StepType"] not in ("Max", "", "None"):
            raise DeltaSourceError("R08_STORY_FORCE_STEP_TYPE_INVALID:" + case)
        story = row["Story"]
        if not story or story in found:
            raise DeltaSourceError("R08_DUPLICATE_STORY_FORCE:" + case + ":" + story)
        found[story] = row
    return found


def _delta_index(rows: list[dict[str, str]], case: str,
                 direction: str) -> dict[str, Decimal]:
    found: dict[str, Decimal] = {}
    for row in rows:
        if row["OutputCase"] != case or row["Direction"] != direction:
            continue
        if row["CaseType"] != "LinRespSpec":
            raise DeltaSourceError("R08_AVG_DRIFT_CASE_TYPE_INVALID:" + case)
        if "StepType" in row and row["StepType"] not in ("Max", "", "None"):
            raise DeltaSourceError("R08_AVG_DRIFT_STEP_TYPE_INVALID:" + case)
        story = row["Story"]
        if not story or story in found:
            raise DeltaSourceError("R08_DUPLICATE_AVG_DRIFT:" + case + ":" + story)
        delta = dec(row["Avg Drift"], "R08_AVG_DRIFT")
        if delta < 0:
            raise DeltaSourceError("R08_NEGATIVE_AVG_DRIFT")
        found[story] = delta
    return found


def _combo_terms(source: Mapping[str, Any], combo: str) -> dict[str, Decimal]:
    rows = _table(source, "Load Combination Definitions",
                  {"Name", "LoadName", "SF", "Type"})
    selected = [r for r in rows if r["Name"] == combo]
    if not selected or selected[0]["Type"] != "Linear Add":
        raise DeltaSourceError("R08_WEIGHT_COMBO_NOT_LINEAR_ADD")
    terms: dict[str, Decimal] = {}
    for row in selected:
        name = row["LoadName"]
        if not name or name in terms:
            raise DeltaSourceError("R08_WEIGHT_COMBO_DUPLICATE_COMPONENT")
        terms[name] = dec(row["SF"], "R08_WEIGHT_SCALE_FACTOR")
    # LC_S may be included at 0.3 if the model has actual snow loading.
    expected = WEIGHT_TERMS | ({"LC_S": Decimal("0.3")} if "LC_S" in terms else {})
    if terms != expected:
        raise DeltaSourceError("R08_WGHT_G_PLUS_NQ_COMPONENTS_NOT_AS_DECLARED")
    return terms


def _mass_source_comparison(source: Mapping[str, Any],
                            observed: dict[str, Decimal]) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "NOT_PROVEN", "source_pattern_match": False}
    try:
        rows = _table(source, "Mass Source Definition",
                      {"Name", "IsDefault", "SourceSelf", "SourceLoads", "LoadPattern", "Multiplier"})
        defaults = {r["Name"] for r in rows if r["IsDefault"] == "Yes"}
        if len(defaults) != 1:
            return result | {"reason": "DEFAULT_MASS_SOURCE_AMBIGUOUS"}
        name = next(iter(defaults))
        selected = [r for r in rows if r["Name"] == name]
        if not selected or selected[0]["SourceSelf"] != "Yes" or selected[0]["SourceLoads"] != "Yes":
            return result | {"reason": "MASS_SOURCE_SELF_AND_LOAD_BASIS_NOT_CONFIRMED"}
        factors = {r["LoadPattern"]: dec(r["Multiplier"], "MASS_FACTOR")
                   for r in selected if r["LoadPattern"] not in ("", "None")}
        projected = {k: v for k, v in observed.items() if k != "LC_DL" and v != 0}
        return {**result, "name": name, "source_pattern_match": factors == projected,
                "status": "PATTERN_COEFFICIENTS_MATCH_SELF_MASS_CONDITIONAL"
                          if factors == projected else "PATTERN_COEFFICIENTS_DIFFER",
                "reason": "ELEMENT_SELF_MASS_VS_LC_DL_AND_STORY_WEIGHT_STILL_UNPROVEN"}
    except (DeltaSourceError, TypeError, KeyError, ValueError) as exc:
        return result | {"reason": str(exc)}


def bind_story_second_order(capture: Mapping[str, Any] | None, *,
                            capture_error: str | None = None) -> dict[str, Any]:
    """Evaluate one immutable R08 source bundle without promoting compliance."""
    out = _base(capture_error)
    if capture_error:
        return out | {"reason_codes": ["LIVE_ETABS_R08_SOURCE_CAPTURE_FAILED"]}
    if not isinstance(capture, Mapping):
        return out | {"reason_codes": ["R08_SOURCE_ABSENT"]}
    try:
        if (capture.get("schema") != CAPTURE_SCHEMA or capture.get("status") != "CAPTURED"
                or capture.get("same_sapmodel_session") is not True
                or capture.get("combination_selection_restored") is not True
                or capture.get("analysis_generation_proven") is not False
                or capture.get("configuration_approved") is not False):
            raise DeltaSourceError("R08_SOURCE_BUNDLE_CONTRACT_INVALID")
        case_source = capture["spectrum_source"]
        weight_source = capture["weight_source"]
        model = capture["model"]
        _check_source(case_source, "RS", model)
        _check_source(weight_source, "WGHT", model)
        if not isinstance(model, str) or not model:
            raise DeltaSourceError("R08_MODEL_IDENTITY_EMPTY")
        config = capture["configuration"]
        if (not isinstance(config, Mapping) or set(config) !=
                {"x_case", "y_case", "weight_combo", "R", "D", "Ch", "live_model_basename"}):
            raise DeltaSourceError("R08_CONFIGURATION_SHAPE_INVALID")
        x, y, combo = config["x_case"], config["y_case"], config["weight_combo"]
        if (x != "RSX" or y != "RSY" or combo != "WGHT"
                or not isinstance(config["live_model_basename"], str)
                or model.replace("\\", "/").split("/")[-1].casefold() !=
                   config["live_model_basename"].casefold()):
            raise DeltaSourceError("R08_EXACT_CASE_OR_MODEL_ROLE_NOT_BOUND")
        r, d, ch = (dec(config[k], "R08_" + k) for k in ("R", "D", "Ch"))
        if not all(v > 0 for v in (r, d, ch)):
            raise DeltaSourceError("R08_NONPOSITIVE_R_D_CH")
        terms = _combo_terms(case_source, combo)
        heights_rows = _table(case_source, "Story Definitions",
                              {"Story", "Tower", "Height"}, {"Height": "m"})
        if len({r["Tower"] for r in heights_rows}) != 1:
            raise DeltaSourceError("R08_MULTI_TOWER_NEEDS_EXPLICIT_SCOPE")
        heights: dict[str, Decimal] = {}
        for row in heights_rows:
            story = row["Story"]
            if not story or story in heights:
                raise DeltaSourceError("R08_DUPLICATE_STORY_DEFINITION")
            h = dec(row["Height"], "R08_STORY_HEIGHT")
            if h <= 0:
                raise DeltaSourceError("R08_NONPOSITIVE_STORY_HEIGHT")
            heights[story] = h
        case_rows = _table(case_source, "Story Forces",
                           {"Story", "OutputCase", "CaseType", "Location", "VX", "VY"},
                           {"VX": "kN", "VY": "kN"})
        gravity_rows = _table(weight_source, "Story Forces",
                              {"Story", "OutputCase", "CaseType", "Location", "P"},
                              {"P": "kN"})
        drift_rows = _table(case_source, "Story Max Over Avg Drifts",
                            {"Story", "OutputCase", "CaseType", "Direction", "Avg Drift"},
                            {"Avg Drift": "m"})
        weights = _story_index(gravity_rows, combo, "Combination")
        cases = {axis: _story_index(case_rows, name, "LinRespSpec")
                 for axis, name in (("X", x), ("Y", y))}
        deltas = {axis: _delta_index(drift_rows, name, axis)
                  for axis, name in (("X", x), ("Y", y))}
        if any(not table for table in (weights, *cases.values(), *deltas.values())):
            raise DeltaSourceError("R08_REQUIRED_STORY_NUMERICAL_ROWS_ABSENT")
        if any(story not in heights for rowset in [weights, *cases.values(), *deltas.values()]
               for story in rowset):
            raise DeltaSourceError("R08_RESULTS_UNDECLARED_STORY")
        rows: list[dict[str, Any]] = []
        missing: list[dict[str, str]] = []
        theta_by_axis: dict[str, list[Decimal]] = {"X": [], "Y": []}
        for story in heights:
            for axis in ("X", "Y"):
                if (story not in weights or story not in cases[axis]
                        or story not in deltas[axis]):
                    missing.append({"story": story, "direction": axis,
                                    "reason": "SOURCE_ROW_OR_PHYSICAL_SCOPE_MISSING"})
                    continue
                w = abs(dec(weights[story]["P"], "R08_WGHT_CUMULATIVE_P"))
                shear_key = "VX" if axis == "X" else "VY"
                v = abs(dec(cases[axis][story][shear_key], "R08_STORY_SHEAR"))
                delta = deltas[axis][story]
                if w <= 0 or v <= 0:
                    raise DeltaSourceError("R08_NONPOSITIVE_WEIGHT_OR_STORY_SHEAR")
                theta = delta * w / (v * heights[story])
                theta_by_axis[axis].append(theta)
                rows.append({
                    "check_instance_id": f"R08:SECOND_ORDER_PDELTA:{story}:{axis}",
                    "story": story, "direction": axis,
                    "case": x if axis == "X" else y,
                    "weight_combo": combo, "story_height_m": str(heights[story]),
                    "cumulative_seismic_weight_kn_candidate": str(w),
                    "reduced_story_shear_kn_candidate": str(v),
                    "etabs_avg_drift_m_candidate": str(delta),
                    "theta_ii_candidate": str(theta),
                    "source_numeric_status": "SOURCE_NUMERICAL_CALCULATED",
                    "formal_compliance": "NOT_PROVEN",
                })
        limit = Decimal("0.12") * d / (ch * r)
        directions: dict[str, dict[str, Any]] = {}
        for axis in ("X", "Y"):
            theta_max = max(theta_by_axis[axis]) if theta_by_axis[axis] else None
            beta = (max(Decimal(1), Decimal("0.88") + ch * r * theta_max / d)
                    if theta_max is not None and theta_max > limit else Decimal(1))
            directions[axis] = {
                "theta_max_candidate": str(theta_max) if theta_max is not None else None,
                "theta_limit_reference": str(limit),
                "beta_ii_candidate": str(beta) if theta_max is not None else None,
                "within_reference_limit_candidate": (theta_max <= limit
                                                       if theta_max is not None else None),
                "applied_to_design_forces": False,
            }
        # Check that WGHT at the bottom matches its Base Reaction. Independent
        # mass sums can differ from combination weights; do not invent equality.
        base_rows = _table(weight_source, "Base Reactions",
                           {"OutputCase", "CaseType", "FZ"}, {"FZ": "kN"})
        base = [r for r in base_rows if r["OutputCase"] == combo]
        if len(base) != 1 or base[0]["CaseType"] != "Combination":
            raise DeltaSourceError("R08_WGHT_BASE_REACTION_UNAVAILABLE")
        base_fz = abs(dec(base[0]["FZ"], "R08_BASE_FZ"))
        if not weights:
            raise DeltaSourceError("R08_EMPTY_WEIGHTS")
        bottom_weight = max(abs(dec(r["P"], "R08_P")) for r in weights.values())
        if abs(base_fz - bottom_weight) > max(Decimal("0.05"), base_fz * Decimal("0.00001")):
            raise DeltaSourceError("R08_WGHT_STORY_BASE_BALANCE_MISMATCH")
        source_hash = sha256(json.dumps(capture, sort_keys=True, ensure_ascii=False,
                                        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        out.update({
            "status": "NUMERIC_PRECHECK_UNAPPROVED" if rows else "BLOCKED_REQUIRED_STORY_ROWS",
            "execution_status": "SOURCE_NUMERICAL_ONLY" if rows else "BLOCKED",
            "model": model, "source_sha256": source_hash,
            "case_source_sha256": case_source["payload_sha256"],
            "weight_source_sha256": weight_source["payload_sha256"],
            "configuration": dict(config),
            "weight_components": {k: str(v) for k, v in terms.items()},
            "mass_source_comparison": _mass_source_comparison(case_source, terms),
            "weight_base_reconciliation_kn": str(base_fz - bottom_weight),
            "weight_base_reaction_kn": str(base_fz),
            "expected_story_direction_count": 2 * len(heights),
            "evaluated_story_direction_count": len(rows),
            "missing_story_direction": missing,
            "results": rows, "direction_results": directions,
            "reason_codes": (["R08_DEFINED_STORY_COVERAGE_INCOMPLETE"]
                             if missing else []) +
                ["R08_FORMAL_PDELTA_AND_COLUMN_WALL_AVG_DRIFT_NOT_PROVEN"],
        })
    except (DeltaSourceError, KeyError, ValueError, TypeError, ArithmeticError) as exc:
        out.update(status="BLOCKED_SOURCE_INVALID", reason_codes=[str(exc)])
    return out
