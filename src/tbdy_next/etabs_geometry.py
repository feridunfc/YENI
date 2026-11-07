"""Project-owned ETABS 23.2 geometry source reader.

Reads the six exact source tables observed in the local live schema probe.
There are no setters, analysis runs, model writes, or unit changes.
"""
from __future__ import annotations

from typing import Any

TABLES = {
    "FRAME_ASSIGNMENTS": "Frame Assignments - Summary",
    "SECTION_ASSIGNMENTS": "Frame Assignments - Section Properties",
    "RECTANGULAR_SECTIONS": "Frame Section Property Definitions - Concrete Rectangular",
    "COLUMN_CONNECTIVITY": "Column Object Connectivity",
    "BEAM_CONNECTIVITY": "Beam Object Connectivity",
    "SECTION_SUMMARY": "Frame Section Property Definitions - Summary",
}


def _metadata(db: Any, key: str) -> dict:
    """Use the observed eight-return ETABS GetAllFieldsInTable ABI."""
    try:
        response = db.GetAllFieldsInTable(key)
        if not isinstance(response, (list, tuple)) or len(response) != 8:
            raise ValueError("GetAllFieldsInTable output ABI not recognized")
        version, count, field_keys, field_names, descriptions, units, importable, code = response
        if type(code) is not int or code != 0 or type(count) is not int or count < 1:
            raise ValueError(f"GetAllFieldsInTable return code={code!r}, field count={count!r}")
        if not all(isinstance(value, (list, tuple)) and len(value) == count
                   for value in (field_keys, field_names, descriptions, units, importable)):
            raise ValueError("GetAllFieldsInTable field arrays inconsistent")
        if len(set(field_keys)) != count or any(not isinstance(f, str) or not f for f in field_keys):
            raise ValueError("GetAllFieldsInTable keys absent/duplicated")
        return {"status": "OK", "table_version": version, "field_keys": list(field_keys),
                "units_by_field": dict(zip(field_keys, units))}
    except Exception as exc:
        return {"status": "METADATA_ERROR", "error": f"{type(exc).__name__}: {exc}"}


def _read_one(db: Any, name: str) -> dict:
    errors: list[str] = []
    for signature, args in (
        ("seven_list", (name, [], "", 0, [], 0, [])),
        ("seven_string", (name, "", "", 0, [], 0, [])),
    ):
        try:
            raw = db.GetTableForDisplayArray(*args)
            if not isinstance(raw, (list, tuple)) or len(raw) < 6:
                raise ValueError("Unexpected ETABS display array tuple")
            if type(raw[-1]) is not int or raw[-1] != 0:
                raise ValueError(f"ETABS ret_code={raw[-1]!r}")
            fields, count, flat = list(raw[2]), raw[3], list(raw[4])
            if not fields or any(not isinstance(f, str) or not f for f in fields) or len(set(fields)) != len(fields):
                raise ValueError("Missing or duplicate field name")
            if type(count) is not int or count < 0 or len(flat) != count * len(fields):
                raise ValueError("ETABS record count/flat data mismatch")
            n = len(fields)
            rows = [dict(zip(fields, (str(v) for v in flat[i:i+n]))) for i in range(0, len(flat), n)]
            return {"status": "CAPTURED", "table_key": name, "fields": fields,
                    "row_count": count, "rows": rows, "signature": signature}
        except (AttributeError, TypeError, ValueError, IndexError) as exc:
            errors.append(f"{signature}: {exc}")
    return {"status": "CAPTURE_ERROR", "table_key": name, "fields": [], "rows": [],
            "row_count": 0, "error": " | ".join(errors)}



def _capture_used_material_types(sap: Any, tables: dict[str, Any]) -> dict[str, Any]:
    """Read exact, USED material classifications, not section-name heuristics.

    ETABS PropMaterial.GetTypeOAPI: known material enums 1..8, concrete = 2.
    Every failed call stays UNRESOLVED; no alternative/material-name fallback.
    The joined frame inventory is kept separate from engineering applicability.
    """
    assignments = tables.get("SECTION_ASSIGNMENTS", {})
    summaries = tables.get("SECTION_SUMMARY", {})
    if assignments.get("status") != "CAPTURED" or summaries.get("status") != "CAPTURED":
        return {"status": "SOURCE_UNAVAILABLE", "source_api": "PropMaterial.GetTypeOAPI", "facts": {}}
    required = {"SectProp"}
    if not required.issubset(set(assignments.get("fields") or ())) or not {"Name", "Material"}.issubset(set(summaries.get("fields") or ())):
        return {"status": "SOURCE_FIELDS_MISSING", "source_api": "PropMaterial.GetTypeOAPI", "facts": {}}
    section_rows: dict[str, list[dict]] = {}
    for row in summaries["rows"]:
        name = str(row.get("Name", "")).strip()
        if name:
            section_rows.setdefault(name, []).append(row)
    names: set[str] = set()
    for assignment in assignments["rows"]:
        section = str(assignment.get("SectProp", "")).strip()
        exact = section_rows.get(section, [])
        if len(exact) == 1:
            material = str(exact[0].get("Material", "")).strip()
            if material:
                names.add(material)
    facts: dict[str, dict] = {}
    for name in sorted(names):
        try:
            raw = sap.PropMaterial.GetTypeOAPI(name)
            if not isinstance(raw, (tuple, list)) or len(raw) != 3:
                raise ValueError(f"unrecognized API output shape {type(raw).__name__}")
            code, symmetry, ret = raw
            if type(ret) is not int or ret != 0 or type(code) is not int or code not in range(1, 9):
                raise ValueError(f"invalid material API result: type={code!r}, ret={ret!r}")
            facts[name] = {"status": "TYPE_RESOLVED", "material_type_code": code,
                           "symmetry_type_code": symmetry, "is_concrete": code == 2}
        except Exception as exc:
            facts[name] = {"status": "TYPE_UNRESOLVED", "material_type_code": None,
                           "error": f"{type(exc).__name__}: {exc}"}
    return {"status": "CAPTURED" if all(v["status"] == "TYPE_RESOLVED" for v in facts.values()) else "PARTIAL",
            "source_api": "PropMaterial.GetTypeOAPI", "facts": facts,
            "used_material_count": len(names)}

def capture_geometry(sap: Any) -> dict:
    """Snapshot all relevant structural-frame geometry once, within one COM session."""
    before = sap.GetPresentUnits()
    db = sap.DatabaseTables
    tables = {}
    for logical, name in TABLES.items():
        record = _read_one(db, name)
        record["field_metadata"] = _metadata(db, name)
        tables[logical] = record
    material_types = _capture_used_material_types(sap, tables)
    after = sap.GetPresentUnits()
    return {"schema": "tbdy.next.geometry.capture.v2",
            "present_units": before if type(before) is int else None,
            "present_units_after": after if type(after) is int else None,
            "unit_state_unchanged": type(before) is int and before == after,
            "tables": tables, "material_types": material_types}
