"""VS04 read-only source capture for three ETABS analysis tables.

This slice OBSERVES the real ETABS 23.2 field schema and full source rows.
It does not guess field aliases, qualify result lineage, execute formulas,
or issue any TBDY/TS500 compliance verdict. All display selection changes
are temporary and verified on restoration.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from .etabs_geometry import _read_one
from .etabs_modal import ModalCaptureError, _selected_cases, _set_cases

TABLES = (
    "Modal Periods And Frequencies",
    "Base Reactions",
    "Story Drifts",
)
CAPTURE_SCHEMA = "tbdy.next.vs04.analysis-sources.v1"


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _full_metadata(db: Any, table_key: str) -> dict[str, Any]:
    """Capture all eight fields of the observed GetAllFieldsInTable ABI."""
    try:
        raw = db.GetAllFieldsInTable(table_key)
        if not isinstance(raw, (tuple, list)) or len(raw) != 8:
            raise ValueError("UNKNOWN_GET_ALL_FIELDS_ABI")
        version, count, keys, names, descriptions, units, importable, code = raw
        if type(code) is not int or code != 0 or type(count) is not int or count < 1:
            raise ValueError("FIELD_METADATA_CODE_OR_COUNT_INVALID")
        arrays = (keys, names, descriptions, units, importable)
        if not all(isinstance(x, (tuple, list)) and len(x) == count for x in arrays):
            raise ValueError("FIELD_METADATA_ARRAY_LENGTH_CONFLICT")
        if any(not isinstance(x, str) or not x for x in keys) or len(set(keys)) != count:
            raise ValueError("FIELD_KEYS_MISSING_OR_DUPLICATE")
        if any(not isinstance(x, str) for values in (names, descriptions, units) for x in values):
            raise ValueError("FIELD_METADATA_TEXT_INVALID")
        return {
            "status": "OK",
            "table_version": version,
            "field_keys": list(keys),
            "field_names": list(names),
            "field_descriptions": list(descriptions),
            "units_by_field": dict(zip(keys, units)),
            "importable_by_field": dict(zip(keys, importable)),
            "field_count": count,
        }
    except Exception as exc:
        return {"status": "METADATA_ERROR",
                "error": f"{type(exc).__name__}: {exc}"}


def _capture_table(db: Any, key: str) -> dict[str, Any]:
    try:
        table = _read_one(db, key)
    except Exception as exc:
        table = {"status": "CAPTURE_ERROR", "table_key": key,
                 "fields": [], "rows": [], "row_count": 0,
                 "error": f"{type(exc).__name__}: {exc}"}
    table["field_metadata"] = _full_metadata(db, key)
    return table


def capture_analysis_sources(
    sap: Any, *, modal_case: str, x_case: str = "RSX", y_case: str = "RSY"
) -> dict[str, Any]:
    """Read three tables within the caller-owned COM session; never run analysis.

    The X/Y case bindings are capture-selection candidates, NOT approved
    spectrum role or combination bindings. A failed restore invalidates the
    entire operation, even if all table reads succeeded.
    """
    candidates = (modal_case, x_case, y_case)
    if any(not isinstance(c, str) or not c or c != c.strip() or len(c) > 120
           for c in candidates) or len(set(candidates)) != len(candidates):
        raise ModalCaptureError("VS04 requires three distinct exact case names")
    db = sap.DatabaseTables
    before_units = sap.GetPresentUnits()
    original = _selected_cases(db)
    requested = tuple(candidates)
    changed = requested != original
    captured: dict[str, dict] = {}
    read_error: Exception | None = None
    try:
        if changed:
            # A setter can mutate display selection even if it raises.
            _set_cases(db, requested)
            if _selected_cases(db) != requested:
                raise ModalCaptureError("VS04_SELECTED_CASES_NOT_CONFIRMED")
        for key in TABLES:
            captured[key] = _capture_table(db, key)
    except Exception as exc:
        read_error = exc
    finally:
        if changed:
            try:
                _set_cases(db, original)
                if _selected_cases(db) != original:
                    raise ModalCaptureError("VS04_DISPLAY_SELECTION_RESTORE_MISMATCH")
            except Exception as exc:
                raise ModalCaptureError(f"VS04_DISPLAY_SELECTION_RESTORE_FAILED: {exc}") from exc
    if read_error is not None:
        raise ModalCaptureError(f"VS04_CAPTURE_REJECTED: {read_error}") from read_error
    after_units = sap.GetPresentUnits()
    return {
        "schema": CAPTURE_SCHEMA,
        "source_mode": "LIVE_ETABS",
        "tables": captured,
        "requested_cases": {"modal": modal_case, "x_candidate": x_case, "y_candidate": y_case},
        "display_selection_restored": True,
        "units_before": before_units if type(before_units) is int else None,
        "units_after": after_units if type(after_units) is int else None,
        "analysis_generation_proven": False,
        "combination_roles_approved": False,
        "engineering_release": "NOT_READY",
    }


def review_analysis_sources(source: Mapping[str, Any] | None) -> dict[str, Any]:
    """Reproducible source-only review; no numerical or regulatory PASS."""
    base = {"stage": "VS04_ANALYSIS_SOURCE_SCHEMA",
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
            "analysis_generation_proven": False,
            "numeric_checks_executed": 0,
            "scope_note": "Three exact ETABS table schemas and raw rows only; no drift/base-shear verdict"}
    if not isinstance(source, Mapping) or source.get("schema") != CAPTURE_SCHEMA:
        return {**base, "status": "SOURCE_UNAVAILABLE",
                "reason": "MISSING_OR_UNKNOWN_VS04_CAPTURE", "tables": []}
    safety = (source.get("source_mode") == "LIVE_ETABS"
              and source.get("display_selection_restored") is True
              and type(source.get("units_before")) is int
              and source.get("units_before") == source.get("units_after")
              and source.get("units_before") == 6
              and source.get("analysis_generation_proven") is False
              and source.get("combination_roles_approved") is False)
    observations: list[dict[str, Any]] = []
    tables = source.get("tables")
    for key in TABLES:
        value = tables.get(key) if isinstance(tables, Mapping) else None
        reasons: list[str] = []
        if not safety:
            reasons.append("CAPTURE_SELECTION_UNITS_OR_LINEAGE_NOT_QUALIFIED")
        if not isinstance(value, Mapping) or value.get("table_key") != key:
            reasons.append("TABLE_MISSING_OR_WRONG_IDENTITY")
            value = {}
        if value.get("status") != "CAPTURED":
            reasons.append("TABLE_NOT_CAPTURED")
        fields, rows, count, meta = (value.get("fields"), value.get("rows"),
                                     value.get("row_count"), value.get("field_metadata"))
        if (not isinstance(fields, list) or not fields
                or any(not isinstance(f, str) or not f for f in fields)
                or len(fields) != len(set(fields))):
            reasons.append("DISPLAY_FIELDS_INVALID")
        if (type(count) is not int or count < 1 or not isinstance(rows, list)
                or len(rows) != count):
            reasons.append("ROW_COUNT_MISSING_EMPTY_OR_CONFLICT")
        elif isinstance(fields, list) and (
                any(not isinstance(row, Mapping) or set(row) != set(fields)
                    or any(not isinstance(v, str) for v in row.values()) for row in rows)):
            reasons.append("ROW_HEADER_OR_VALUE_SHAPE_INVALID")
        if not isinstance(meta, Mapping) or meta.get("status") != "OK":
            reasons.append("FIELD_METADATA_UNAVAILABLE")
            meta = {}
        else:
            keys = meta.get("field_keys")
            if (not isinstance(keys, list) or len(keys) != meta.get("field_count")
                    or len(keys) != len(set(keys))
                    or not isinstance(fields, list) or not set(fields).issubset(set(keys))):
                reasons.append("DISPLAY_METADATA_FIELD_CONFLICT")
            units = meta.get("units_by_field")
            if not isinstance(units, Mapping) or not all(
                    isinstance(units.get(k), str) for k in keys or () if isinstance(k, str)):
                reasons.append("FIELD_UNITS_NOT_OBSERVED")
        valid = not reasons
        observations.append({
            "table_key": key,
            "status": "OBSERVED_UNAPPROVED" if valid else "NOT_PROVEN",
            "reason_codes": reasons,
            "row_count": count if type(count) is int else None,
            "fields": fields if isinstance(fields, list) else [],
            "table_version": meta.get("table_version"),
            "field_metadata": dict(meta),
            "source_sha256": _digest(value) if value else None,
            "schema_sha256": _digest({"fields": fields, "metadata": meta}) if valid else None,
        })
    good = sum(x["status"] == "OBSERVED_UNAPPROVED" for x in observations)
    return {
        **base,
        "status": "SOURCE_SCHEMA_CAPTURED_PENDING_REVIEW" if good == 3 else "SOURCE_SCHEMA_INCOMPLETE",
        "captured_table_count": good,
        "expected_table_count": 3,
        "requested_cases": source.get("requested_cases"),
        "units_before": source.get("units_before"),
        "units_after": source.get("units_after"),
        "tables": observations,
    }
