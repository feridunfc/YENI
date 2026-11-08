"""VS05: ETABS-source-driven story displacement calculation.

Tables are read from one existing generic-source-capture JSON.  This module
never calls COM, never changes a model, and never promotes source numbers to
TBDY compliance.  Two different products are deliberately kept separate:

1. ETABS response-spectrum Story Drifts (dimensionless) * observed story
   height (m) -> a reduced story-drift *candidate* in metres, independently
   checked against ETABS Story Max Over Avg Drifts (metres).
2. Signed end-displacement differences from the *same Ritz mode* at each
   physical column's upper/lower nodes -> modal shape differential only.

A response spectrum 'Max' point displacement is NEVER subtracted from another
'Max' point displacement: they are not signed concurrent displacements.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
import json

SOURCE_SCHEMA = "tbdy.next.etabs.generic-source-capture.v1"
RESULT_SCHEMA = "tbdy.next.vs05.story-delta-candidate.v1"
PRIMARY = {"RSX": "X", "RSY": "Y"}


class DeltaSourceError(ValueError):
    pass


def dec(value: Any, what: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise DeltaSourceError(f"INVALID_NUMERIC_{what}")
    try:
        number = Decimal(str(value))
    except (ValueError, InvalidOperation):
        raise DeltaSourceError(f"INVALID_NUMERIC_{what}") from None
    if not number.is_finite():
        raise DeltaSourceError(f"NONFINITE_{what}")
    return number


def tbl(source: Mapping[str, Any], name: str, fields: set[str], units: dict[str, str] | None = None) -> list[dict[str, Any]]:
    raw = source.get("table_reads", {}).get(name)
    if not isinstance(raw, dict) or raw.get("table_key") != name or raw.get("status") != "CAPTURED":
        raise DeltaSourceError(f"TABLE_UNAVAILABLE:{name}")
    meta = raw.get("field_metadata")
    if not isinstance(meta, dict) or meta.get("status") != "OK":
        raise DeltaSourceError(f"TABLE_METADATA_UNAVAILABLE:{name}")
    declared = raw.get("fields")
    keys = meta.get("field_keys")
    if not isinstance(declared, list) or not isinstance(keys, list) or len(set(declared)) != len(declared) or not fields.issubset(set(declared)) or not fields.issubset(set(keys)):
        raise DeltaSourceError(f"TABLE_FIELDS_INVALID:{name}")
    if units:
        observed_units = meta.get("units_by_field") or {}
        if any(observed_units.get(k) != u for k, u in units.items()):
            raise DeltaSourceError(f"TABLE_UNITS_INVALID:{name}")
    rows = raw.get("rows")
    if not isinstance(rows, list) or type(raw.get("row_count")) is not int or len(rows) != raw["row_count"]:
        raise DeltaSourceError(f"TABLE_ROW_COUNT_CONFLICT:{name}")
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not fields.issubset(row) or any(not isinstance(row[k], str) for k in fields):
            raise DeltaSourceError(f"TABLE_ROW_FIELDS_INVALID:{name}:{i}")
    return rows


def story_heights(source: Mapping[str, Any]) -> dict[str, Decimal]:
    rows = tbl(source, "Story Definitions", {"Story", "Tower", "Height"}, {"Height": "m"})
    towers = {x["Tower"] for x in rows}
    if len(towers) != 1:
        raise DeltaSourceError("MULTITOWER_STORY_CONTEXT_NEEDS_EXPLICIT_BINDING")
    heights: dict[str, Decimal] = {}
    for row in rows:
        story = row["Story"]
        if not story or story in heights:
            raise DeltaSourceError("DUPLICATE_OR_EMPTY_STORY")
        height = dec(row["Height"], "STORY_HEIGHT")
        if height <= 0:
            raise DeltaSourceError("NONPOSITIVE_STORY_HEIGHT")
        heights[story] = height
    return heights


def _index_max_drift(source: Mapping[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows = tbl(source, "Story Max Over Avg Drifts", {"Story", "OutputCase", "CaseType", "StepType", "Direction", "Max Drift", "Avg Drift", "Ratio"}, {"Max Drift": "m", "Avg Drift": "m"})
    indexed = {}
    for row in rows:
        if row["OutputCase"] not in PRIMARY:
            continue
        key = (row["Story"], row["OutputCase"], row["Direction"])
        if key in indexed:
            raise DeltaSourceError(f"DUPLICATE_MAX_DRIFT:{key}")
        if row["CaseType"] != "LinRespSpec" or row["StepType"] != "Max":
            raise DeltaSourceError(f"WRONG_MAX_DRIFT_PROJECTION:{key}")
        if dec(row["Max Drift"], "MAX_DRIFT") < 0 or dec(row["Avg Drift"], "AVG_DRIFT") < 0:
            raise DeltaSourceError("NEGATIVE_ETABS_MAX_DRIFT")
        indexed[key] = row
    return indexed


def response_spectrum_story_deltas(source: Mapping[str, Any], heights: dict[str, Decimal]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = tbl(source, "Story Drifts", {"Story", "OutputCase", "CaseType", "StepType", "Direction", "Drift", "Label"}, {"Drift": ""})
    max_index = _index_max_drift(source)
    observed = set()
    results = []
    for row in rows:
        if row["OutputCase"] not in PRIMARY:
            continue
        key = (row["Story"], row["OutputCase"], row["Direction"])
        if key in observed:
            raise DeltaSourceError(f"DUPLICATE_STORY_DRIFT:{key}")
        observed.add(key)
        story, case, axis = key
        if axis not in ("X", "Y") or story not in heights:
            raise DeltaSourceError(f"UNKNOWN_STORY_OR_DIRECTION:{key}")
        if row["CaseType"] != "LinRespSpec" or row["StepType"] != "Max":
            raise DeltaSourceError(f"WRONG_SPECTRUM_PROJECTION:{key}")
        dr = dec(row["Drift"], "STORY_DRIFT")
        if dr < 0:
            raise DeltaSourceError("NEGATIVE_STORY_DRIFT_RATIO")
        ref = max_index.get(key)
        if ref is None:
            raise DeltaSourceError(f"MISSING_INDEPENDENT_ETABS_MAX_DRIFT:{key}")
        height = heights[story]
        delta = dr * height
        max_value = dec(ref["Max Drift"], "MAX_DRIFT")
        residual = delta - max_value
        # ETABS rows here print dimensionless Drift to 6 decimal places;
        # multiplied displacement and independent 'Max Drift' are rounded.
        # This is a display-resolution comparison, not an engineering limit.
        tolerance = max(Decimal("0.000005"), height * Decimal("0.000001"))
        if abs(residual) > tolerance:
            raise DeltaSourceError(f"STORY_DRIFT_TABLE_RECONCILIATION_FAILED:{key}:{residual}")
        results.append({
            "story": story, "case": case, "direction": axis,
            "primary_direction": axis == PRIMARY[case],
            "governing_joint_label_etabs": row["Label"],
            "height_m": str(height), "etabs_story_drift_ratio": str(dr),
            "etabs_derived_delta_m": str(delta),
            "etabs_derived_delta_mm": str(delta * 1000),
            "etabs_reported_max_drift_m": str(max_value),
            "etabs_reconciliation_residual_mm": str(residual * 1000),
            "calculation_type": "ETABS_STORY_DRIFT_RATIO_TIMES_STORY_HEIGHT",
            "regulatory_status": "NOT_PROVEN",
        })
    unexpected = set(max_index) - observed
    if unexpected:
        raise DeltaSourceError(f"UNPAIRED_MAX_OVER_AVG_DRIFT:{sorted(unexpected)}")
    missing = [
        {"story": story, "case": case, "direction": direction}
        for story in heights
        for case in sorted(PRIMARY)
        for direction in ("X", "Y")
        if (story, case, direction) not in observed
    ]
    results.sort(key=lambda x: (-float(x["story"]), x["case"], x["direction"]))
    covered_stories = sorted({x["story"] for x in results})
    return results, {
        "available_story_count": len(heights),
        "stories_with_spectrum_drift": covered_stories,
        "uncovered_stories": sorted(set(heights) - set(covered_stories)),
        "response_spectrum_rows": len(results),
        "missing_story_case_direction": missing,
        "all_source_rows_reconciled": True,
        "all_stories_covered": not missing,
    }


def modal_column_shape_differences(source: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    points = tbl(source, "Point Object Connectivity", {"UniqueName", "X", "Y", "Z", "Story"}, {"X": "m", "Y": "m", "Z": "m"})
    columns = tbl(source, "Column Object Connectivity", {"UniqueName", "UniquePtI", "UniquePtJ", "Story", "Length"}, {"Length": "m"})
    displacements = tbl(source, "Joint Displacements", {"UniqueName", "Story", "OutputCase", "CaseType", "StepType", "StepNumber", "Ux", "Uy"}, {"Ux": "m", "Uy": "m"})
    point_index = {}
    for p in points:
        if not p["UniqueName"] or p["UniqueName"] in point_index:
            raise DeltaSourceError("DUPLICATE_OR_BLANK_POINT_ID")
        point_index[p["UniqueName"]] = p
    modal = {}
    available_modes = set()
    spectrum_points_ignored = 0
    for r in displacements:
        if r["OutputCase"] in PRIMARY:
            spectrum_points_ignored += 1
            continue  # Never subtract independent RSX/RSY max values.
        if r["OutputCase"] != "Modal":
            continue
        if r["CaseType"] != "LinModRitz" or r["StepType"] != "Mode":
            raise DeltaSourceError("UNSUPPORTED_MODAL_DISPLACEMENT_PROJECTION")
        try:
            mode = int(r["StepNumber"])
        except ValueError:
            raise DeltaSourceError("INVALID_MODE_NUMBER") from None
        if mode < 1 or str(mode) != r["StepNumber"]:
            raise DeltaSourceError("INVALID_MODE_NUMBER")
        key = (r["UniqueName"], mode)
        if key in modal:
            raise DeltaSourceError(f"DUPLICATE_MODAL_NODE_MODE:{key}")
        modal[key] = (dec(r["Ux"], "MODAL_UX"), dec(r["Uy"], "MODAL_UY"))
        available_modes.add(mode)
    output = []
    missing = []
    seen_columns = set()
    for column in columns:
        frame = column["UniqueName"]
        if not frame or frame in seen_columns:
            raise DeltaSourceError("DUPLICATE_COLUMN_ID")
        seen_columns.add(frame)
        i, j = column["UniquePtI"], column["UniquePtJ"]
        if i == j or i not in point_index or j not in point_index:
            missing.append({"column": frame, "reason": "MISSING_OR_IDENTICAL_COLUMN_END_POINT"})
            continue
        zi = dec(point_index[i]["Z"], "POINT_Z")
        zj = dec(point_index[j]["Z"], "POINT_Z")
        if zi == zj:
            missing.append({"column": frame, "reason": "COINCIDENT_COLUMN_END_ELEVATIONS"})
            continue
        lower, upper = (i, j) if zi < zj else (j, i)
        upper_z, lower_z = (zj, zi) if zi < zj else (zi, zj)
        for mode in sorted(available_modes):
            low = modal.get((lower, mode))
            high = modal.get((upper, mode))
            if low is None or high is None:
                missing.append({"column": frame, "mode": mode, "reason": "JOINT_MODAL_DISPLACEMENT_NOT_OBSERVED"})
                continue
            output.append({
                "column": frame, "associated_story": column["Story"],
                "lower_point": lower, "upper_point": upper,
                "lower_z_m": str(lower_z), "upper_z_m": str(upper_z),
                "mode": mode, "signed_modal_shape_delta_ux_m": str(high[0] - low[0]),
                "signed_modal_shape_delta_uy_m": str(high[1] - low[1]),
                "interpretation": "RITZ_MODE_SHAPE_DIFFERENCE_NOT_DESIGN_EARTHQUAKE_DRIFT",
            })
    return output, {
        "observed_column_count": len(columns), "observed_point_count": len(points),
        "observed_joint_displacement_rows": len(displacements),
        "observed_modes": sorted(available_modes),
        "column_mode_shape_difference_count": len(output),
        "missing_modal_column_pairs": missing,
        "spectrum_point_max_rows_not_subtracted": spectrum_points_ignored,
    }


def calculate(source: Mapping[str, Any], *, source_sha256: str | None = None) -> dict[str, Any]:
    if not isinstance(source, Mapping) or source.get("schema") != SOURCE_SCHEMA or source.get("status") != "CAPTURED":
        raise DeltaSourceError("GENERIC_ETABS_CAPTURE_SCHEMA_OR_STATUS_INVALID")
    if not (source.get("model_locked") is True and source.get("model_units_code") == 6
            and source.get("model_units_unchanged") is True and source.get("selection_restored") is True):
        raise DeltaSourceError("CAPTURE_UNIT_LOCK_OR_SELECTION_RESTORE_INVALID")
    heights = story_heights(source)
    deltas, coverage = response_spectrum_story_deltas(source, heights)
    modal, modal_summary = modal_column_shape_differences(source)
    return {
        "schema": RESULT_SCHEMA,
        "model": source.get("model"),
        "source_capture_utc": source.get("captured_at_utc"),
        "source_file_sha256": source_sha256,
        "status": "ETABS_DERIVED_NUMERICAL_CANDIDATES_COMPUTED",
        "reduced_drift_load_basis_verified": False,
        "design_spectrum_scaling_qualified": False,
        "tbd_y_eq_4_32_4_34_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "story_deltas": deltas,
        "story_delta_coverage": coverage,
        "column_modal_shape_differences": modal,
        "modal_shape_coverage": modal_summary,
        "note": "Story delta candidates are reconstructed from ETABS's own response-spectrum drift ratios, NOT independently from signed concurrent joint displacements. Modal joint differences are Ritz shape differences only. No TBDY PASS.",
    }


def calculate_file(source_path: Path) -> dict[str, Any]:
    raw = source_path.read_bytes()
    try:
        source = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise DeltaSourceError("SOURCE_JSON_INVALID") from exc
    if not isinstance(source, dict):
        raise DeltaSourceError("SOURCE_JSON_OBJECT_REQUIRED")
    return calculate(source, source_sha256=sha256(raw).hexdigest())
