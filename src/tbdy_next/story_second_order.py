"""R08 product-owned ETABS source binding into the EXISTING engineering kernel.

The 94-node DAG already owns GLOBAL_SECOND_ORDER.  This module is an
identity/units/provenance adapter, not a second theta or beta implementation.
Source numerical owner: tbdy_next.engineering.story_pdelta.review_story_pdelta.
"""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
import math
from typing import Any, Mapping

from .story_delta import dec, tbl, DeltaSourceError
from .story_geometry import read_story_levels
from .story_drift_binding import _verify_generic_capture
from .engineering.story_pdelta import StorySourceError, review_story_pdelta

CHECK_ID = "GLOBAL_SECOND_ORDER"
SCHEMA = "tbdy.next.r08.story-pdelta-source-numerical.v2"
CAPTURE_SCHEMA = "tbdy.next.r08.story-pdelta-capture.v1"
WEIGHT_TERMS = {
    "LC_DL": Decimal("1"), "LC_SDL": Decimal("1"),
    "LC_WDL": Decimal("1"), "LC_DDL": Decimal("1"),
    "LC_LL": Decimal("0.3"),
}
MISSING_GATES = [
    "FULL_PHYSICAL_STORY_SCOPE",
    "COLUMN_AND_WALL_AVERAGE_DRIFT",
    "WGHT_VS_SEISMIC_MASSSOURCE",
    "SPECTRAL_BETA_TE_AND_ANALYSIS_GENERATION",
    "GLOBAL_PDELTA_ORDER_AND_DOUBLE_COUNT",
    "R_D_CH_PROJECT_APPROVAL",
    "TS500_LOCAL_P_SMALL_DELTA_SEPARATE",
    "INDEPENDENT_ETEX_AND_ENGINEERING_ACCEPTANCE",
]


def _base(error: str | None) -> dict:
    return {
        "schema": SCHEMA, "check_id": CHECK_ID,
        "dag_node_id": CHECK_ID, "dag_node_type": "REGULATORY_CHECK",
        "dag_declared_dependencies": ["BASE_SHEAR", "STORY_DRIFT"],
        "dag_execution_authority": "DENIED",
        "code_ref": "TBDY 2018 §4.9.2 / 4.35–4.37",
        "status": "BLOCKED_SOURCE_UNAVAILABLE", "execution_status": "BLOCKED",
        "expected_story_direction_count": 0,
        "evaluated_story_direction_count": 0,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "global_p_delta_design_applied": False,
        "design_demand_approved": False,
        "source_capture_error": error,
        "results": [], "direction_results": {},
        "missing_story_direction": [],
        "missing_authorities": list(MISSING_GATES),
        "reason_codes": [], "source_sha256": None,
        "formula_owner": "tbdy_next.engineering.story_pdelta.review_story_pdelta",
    }


def _capture_valid(capture: Mapping, model: str) -> None:
    _verify_generic_capture(capture)
    if (capture.get("schema") != "tbdy.next.etabs.generic-source-capture.v1"
            or capture.get("action") != "capture"
            or capture.get("status") != "CAPTURED"
            or capture.get("model") != model
            or capture.get("model_locked") is not True
            or capture.get("model_units_code") != 6
            or capture.get("model_units_unchanged") is not True
            or capture.get("selection_restored") is not True
            or capture.get("analysis_generation_proven") is not False):
        raise DeltaSourceError("R08_SOURCE_IDENTITY_UNITS_OR_LOCK_INVALID")


def _index_story(rows: list[dict], case: str, case_type: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in rows:
        if row["OutputCase"] != case or row["Location"] != "Bottom":
            continue
        if row["CaseType"] != case_type:
            raise DeltaSourceError("R08_STORY_CASE_TYPE_INVALID:" + case)
        key = row["Story"]
        if not key or key in result:
            raise DeltaSourceError("R08_STORY_SHEAR_DUPLICATED:" + case + ":" + key)
        result[key] = row
    return result


def _index_drift(rows: list[dict], case: str, axis: str) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for row in rows:
        if row["OutputCase"] != case or row["Direction"] != axis:
            continue
        if row["CaseType"] != "LinRespSpec":
            raise DeltaSourceError("R08_DRIFT_NOT_LIN_RESP_SPEC")
        key = row["Story"]
        if not key or key in result:
            raise DeltaSourceError("R08_DRIFT_DUPLICATED:" + case + ":" + key)
        delta = dec(row["Avg Drift"], "AVG_DRIFT")
        if delta < 0:
            raise DeltaSourceError("R08_NEGATIVE_AVERAGE_DRIFT")
        result[key] = delta
    return result


def _combo_terms(source: Mapping) -> dict[str, Decimal]:
    rows = tbl(source, "Load Combination Definitions",
               {"Name", "Type", "LoadName", "SF"})
    items = [r for r in rows if r["Name"] == "WGHT"]
    if not items or items[0]["Type"] != "Linear Add":
        raise DeltaSourceError("R08_WEIGHT_COMBINATION_NOT_LINEAR_ADD")
    terms: dict[str, Decimal] = {}
    for r in items:
        if r["LoadName"] in terms or not r["LoadName"]:
            raise DeltaSourceError("R08_WGHT_DUPLICATE_TERM")
        terms[r["LoadName"]] = dec(r["SF"], "WGHT_FACTOR")
    expected = dict(WEIGHT_TERMS)
    if "LC_S" in terms:
        expected["LC_S"] = Decimal("0.3")
    if terms != expected:
        raise DeltaSourceError("R08_WGHT_G_PLUS_NQ_COMPONENTS_NOT_AS_DECLARED")
    return terms


def bind_story_second_order(capture: Mapping | None, *,
                            capture_error: str | None = None) -> dict:
    """Bind native ETABS tables to the existing GLOBAL_SECOND_ORDER owner."""
    out = _base(capture_error)
    if capture_error:
        return out | {"reason_codes": ["LIVE_ETABS_R08_CAPTURE_FAILED"]}
    if not isinstance(capture, Mapping):
        return out | {"reason_codes": ["R08_CAPTURE_ABSENT"]}
    try:
        if (capture.get("schema") != CAPTURE_SCHEMA
                or capture.get("status") != "CAPTURED"
                or capture.get("same_sapmodel_session") is not True
                or capture.get("combination_selection_restored") is not True
                or capture.get("analysis_generation_proven") is not False
                or capture.get("configuration_approved") is not False):
            raise DeltaSourceError("R08_CAPTURE_BUNDLE_NOT_QUALIFIED")
        model = capture["model"]
        rs = capture["spectrum_source"]
        wsrc = capture["weight_source"]
        _capture_valid(rs, model)
        _capture_valid(wsrc, model)
        cfg = capture["configuration"]
        if (not isinstance(cfg, Mapping) or set(cfg) !=
                {"x_case", "y_case", "weight_combo", "R", "D", "Ch", "live_model_basename"}
                or cfg["x_case"] != "RSX" or cfg["y_case"] != "RSY"
                or cfg["weight_combo"] != "WGHT"
                or cfg["live_model_basename"].casefold() !=
                   model.replace("\\", "/").split("/")[-1].casefold()):
            raise DeltaSourceError("R08_EXACT_PROJECT_CASE_BINDING_REQUIRED")
        r, d, ch = (dec(cfg[k], k) for k in ("R", "D", "Ch"))
        if any(x <= 0 for x in (r, d, ch)):
            raise DeltaSourceError("R08_R_D_CH_NONPOSITIVE")
        terms = _combo_terms(rs)
        levels, story_evidence = read_story_levels(rs)
        ordered = list(reversed(levels))  # highest to lowest, as code Eq 4.35 requires
        if not ordered:
            raise DeltaSourceError("R08_STORY_DEFINITIONS_MISSING")
        raw_rs = tbl(rs, "Story Forces",
                     {"Story", "OutputCase", "CaseType", "Location", "VX", "VY"},
                     {"VX": "kN", "VY": "kN"})
        raw_w = tbl(wsrc, "Story Forces",
                    {"Story", "OutputCase", "CaseType", "Location", "P"},
                    {"P": "kN"})
        raw_drift = tbl(rs, "Story Max Over Avg Drifts",
                        {"Story", "OutputCase", "CaseType", "Direction", "Avg Drift"},
                        {"Avg Drift": "m"})
        forces = {axis: _index_story(raw_rs, name, "LinRespSpec")
                  for axis, name in (("X", "RSX"), ("Y", "RSY"))}
        weights = _index_story(raw_w, "WGHT", "Combination")
        drifts = {axis: _index_drift(raw_drift, name, axis)
                  for axis, name in (("X", "RSX"), ("Y", "RSY"))}
        if not weights or any(not x for x in (*forces.values(), *drifts.values())):
            raise DeltaSourceError("R08_SOURCE_ROWS_MISSING")
        declared = {s.story for s in ordered}
        for index in (weights, *forces.values(), *drifts.values()):
            if not set(index).issubset(declared):
                raise DeltaSourceError("R08_UNKNOWN_STORY_OUTPUT")
        # Check the response spectrum 'Max' semantics on original Base Reactions;
        # Story Forces themselves do not contain a StepType column.
        base_rs = tbl(rs, "Base Reactions",
                      {"OutputCase", "CaseType", "StepType"})
        for axis in ("X", "Y"):
            found = [a for a in base_rs if a["OutputCase"] == ("RSX" if axis == "X" else "RSY")]
            if (len(found) != 1 or found[0]["CaseType"] != "LinRespSpec"
                    or found[0]["StepType"] != "Max"):
                raise DeltaSourceError("R08_SPECTRAL_BASE_MAX_STEP_UNPROVEN:" + axis)
        base_w = tbl(wsrc, "Base Reactions",
                     {"OutputCase", "CaseType", "FZ"}, {"FZ": "kN"})
        base_found = [a for a in base_w if a["OutputCase"] == "WGHT"]
        if len(base_found) != 1 or base_found[0]["CaseType"] != "Combination":
            raise DeltaSourceError("R08_WGHT_BASE_REACTION_MISSING")
        base_fz = abs(dec(base_found[0]["FZ"], "BASE_FZ"))
        weight_last = max(abs(dec(a["P"], "W_P")) for a in weights.values())
        if (base_fz <= 0 or
                abs(base_fz - weight_last) > max(Decimal("0.05"),
                                                base_fz * Decimal("0.00001"))):
            raise DeltaSourceError("R08_WGHT_BASE_STORY_BALANCE_MISMATCH")
        rows = []
        missing = []
        prev_cumulative = Decimal(0)
        saw_first = False
        for level in ordered:
            story = level.story
            if story not in weights:
                missing.extend({"story": story, "direction": axis, "reason": "STORY_WEIGHT_ROW_MISSING"}
                               for axis in ("X", "Y"))
                if saw_first:
                    # An interior missing story would silently roll its load into a lower one.
                    raise DeltaSourceError("R08_INTERIOR_STORY_WEIGHT_GAP")
                continue
            saw_first = True
            if any(story not in forces[axis] or story not in drifts[axis]
                   for axis in ("X", "Y")):
                raise DeltaSourceError("R08_SPECTRAL_STORY_MISSING_NO_INFERRED_ZERO:" + story)
            total = abs(dec(weights[story]["P"], "CUMULATIVE_STORY_W"))
            wi = total - prev_cumulative
            if wi <= 0:
                raise DeltaSourceError("R08_CUMULATIVE_WEIGHT_NOT_STRICTLY_INCREASING")
            prev_cumulative = total
            h = level.height_m
            vx = abs(dec(forces["X"][story]["VX"], "RSX_VX"))
            vy = abs(dec(forces["Y"][story]["VY"], "RSY_VY"))
            if h <= 0 or vx <= 0 or vy <= 0:
                raise DeltaSourceError("R08_HEIGHT_OR_SHEAR_NONPOSITIVE")
            rows.append({
                "story": story, "level_m": float(level.elevation_m),
                "height_m": float(h), "individual_w_kN": float(wi),
                "shear_kN": {"X": float(vx), "Y": float(vy)},
                "average_reduced_drift_m": {
                    "X": float(drifts["X"][story]), "Y": float(drifts["Y"][story])
                },
            })
        if not rows:
            raise DeltaSourceError("R08_NO_CONCURRENT_STORY_SOURCE_ROWS")
        owner_input = {
            "schema": "tbdy.next.r08.story-source.v1",
            "weight_basis": "G_PLUS_NQ", "weight_kind": "INDIVIDUAL_STORY_WEIGHT",
            "weight_units": "kN", "shear_units": "kN",
            "drift_units": "m", "height_units": "m",
            "combination_name": "WGHT", "weight_operator": "Linear Add",
            "weight_terms": {k: float(v) for k, v in terms.items()},
            "n_live": 0.3,
            "directions": {
                axis: {"shear_case": case, "drift_case": case,
                       "case_type": "LinRespSpec", "step_type": "Max"}
                for axis, case in (("X", "RSX"), ("Y", "RSY"))
            },
            "design_parameters": {"R_X": float(r), "R_Y": float(r),
                                  "D_X": float(d), "D_Y": float(d),
                                  "Ch": float(ch)},
            "stories": rows,
        }
        owner = review_story_pdelta(owner_input)
        # Project source rows into the existing product CheckResult convention.
        mapped = []
        for original, evaluated in zip(rows, owner["rows"]):
            if (original["story"] != evaluated["story"] or
                    not math.isclose(evaluated["cumulative_weight_kN"],
                                     sum(x["individual_w_kN"] for x in
                                         rows[:rows.index(original) + 1]),
                                     rel_tol=1e-10, abs_tol=0.001)):
                raise DeltaSourceError("R08_OWNER_WEIGHT_RECONCILIATION_FAILED")
            for axis in ("X", "Y"):
                ax = evaluated["axes"][axis]
                mapped.append({
                    "check_instance_id": "GLOBAL_SECOND_ORDER:" + original["story"] + ":" + axis,
                    "story": original["story"], "direction": axis,
                    "case": "RSX" if axis == "X" else "RSY",
                    "weight_combo": "WGHT",
                    "story_height_m": str(original["height_m"]),
                    "individual_seismic_weight_kn_candidate": str(original["individual_w_kN"]),
                    "cumulative_seismic_weight_kn_candidate": str(evaluated["cumulative_weight_kN"]),
                    "reduced_story_shear_kn_candidate": str(ax["shear_kN"]),
                    "etabs_avg_drift_m_candidate": str(ax["average_reduced_drift_m"]),
                    "theta_ii_candidate": str(ax["theta_II_reference"]),
                    "source_numeric_status": "SOURCE_NUMERICAL_CALCULATED",
                    "formal_compliance": "NOT_PROVEN",
                })
        directions = {axis: {
            "theta_max_candidate": str(owner["theta_max"][axis]),
            "theta_limit_reference": str(owner["limit_reference"][axis]),
            "beta_ii_candidate": str(max(
                a["axes"][axis]["beta_II_candidate"] for a in owner["rows"]
                if a["axes"][axis]["beta_II_candidate"] is not None
            )) if owner["all_observed_below_numeric_limit"] else None,
            "within_reference_limit_candidate": owner["theta_max"][axis] <=
                                                  owner["limit_reference"][axis],
            "applied_to_design_forces": False,
        } for axis in ("X", "Y")}
        input_sha = sha256(json.dumps(capture, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        out.update({
            "status": "NUMERIC_PRECHECK_UNAPPROVED",
            "execution_status": "SOURCE_NUMERICAL_ONLY",
            "source_sha256": input_sha,
            "case_source_sha256": rs["payload_sha256"],
            "weight_source_sha256": wsrc["payload_sha256"],
            "model": model, "configuration": dict(cfg),
            "weight_components": {k: str(v) for k, v in terms.items()},
            "weight_base_reaction_kn": str(base_fz),
            "mass_source_comparison": {
                "status": "NOT_PROVEN",
                "reason": "WGHT_CUMULATIVE_REACTION_NOT_SEISMIC_MASS_PROOF",
            },
            "physical_story_source_scope": story_evidence,
            "expected_story_direction_count": 2 * len(ordered),
            "evaluated_story_direction_count": len(mapped),
            "missing_story_direction": missing,
            "results": mapped, "direction_results": directions,
            "owner_result_sha256": owner["result_sha256"],
            "reason_codes": (["R08_DECLARED_STORY_COVERAGE_INCOMPLETE"]
                             if missing else []) +
                            ["R08_NORMATIVE_PDELTA_AND_COLUMN_WALL_AVG_NOT_APPROVED"],
        })
    except (StorySourceError, DeltaSourceError, KeyError,
            ValueError, TypeError, ArithmeticError) as exc:
        out.update(status="BLOCKED_SOURCE_INVALID", reason_codes=[str(exc)])
    return out
