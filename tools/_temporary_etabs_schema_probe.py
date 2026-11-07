"""Temporary ETABS 23.2 geometry schema probe — remove after review.

Inspects exact native database table names, field keys, field-unit metadata,
record counts, and at most two preview rows. Console only. No ETABS mutation:
no File.Save, Analyze.RunAnalysis, SetPresentUnits, display-selection setter,
or design call. Does not assert engineering compliance.
"""
from __future__ import annotations

import argparse
import json
import ntpath
import sys
from typing import Any

TARGETS = (
    ("FRAME_ASSIGNMENTS", "Frame Assignments - Summary"),
    ("RECTANGULAR_SECTIONS", "Frame Section Property Definitions - Concrete Rectangular"),
    ("SECTION_ASSIGNMENTS", "Frame Assignments - Section Properties"),
    ("COLUMN_CONNECTIVITY", "Column Object Connectivity"),
    ("BEAM_CONNECTIVITY", "Beam Object Connectivity"),
    ("SECTION_SUMMARY", "Frame Section Property Definitions - Summary"),
    ("MODAL_MASS", "Modal Participating Mass Ratios"),
)

# Suggestions for comparing field names; never automatically approve an alias.
EXPECTED = {
    "FRAME_ASSIGNMENTS": {
        "component_id": ("UniqueName", "Unique Name", "GUID"),
        "story": ("Story", "Story Name"),
        "element_type": ("Type", "FrameType", "ObjectType"),
        "design_section": ("DesignSect", "Design Section", "DesignSec"),
    },
    "RECTANGULAR_SECTIONS": {
        "section_name": ("Name", "SectionName", "PropName"),
        "width": ("t2", "Width", "B"),
        "depth": ("t3", "Depth", "H"),
    },
    "SECTION_ASSIGNMENTS": {
        "element_id": ("UniqueName", "Unique Name", "GUID"),
        "section_name": ("Section", "PropName", "DesignSect"),
    },
    "COLUMN_CONNECTIVITY": {
        "column_id": ("UniqueName", "Unique Name", "GUID"),
        "story": ("Story", "Story Name"),
    },
    "BEAM_CONNECTIVITY": {
        "beam_id": ("UniqueName", "Unique Name", "GUID"),
        "story": ("Story", "Story Name"),
    },
    "MODAL_MASS": {
        "mode": ("Mode",),
        "ux": ("UX",),
        "uy": ("UY",),
        "sum_ux": ("SumUX",),
        "sum_uy": ("SumUY",),
    },
}

SAMPLE_FIELDS = (
    "Name", "UniqueName", "Story", "Label", "Type", "DesignSect",
    "AnalysisSect", "Section", "PropName", "Material", "t2", "t3",
    "Width", "Depth", "Mode", "UX", "UY", "SumUX", "SumUY",
)


def _ret(raw: Any) -> int:
    code = raw[-1] if isinstance(raw, (tuple, list)) and raw else raw
    if type(code) is not int:
        raise ValueError("ETABS return code is not an exact integer")
    return code


def _available(db: Any) -> tuple[str, ...]:
    raw = db.GetAvailableTables(0, [], [], [])
    if not isinstance(raw, (tuple, list)) or len(raw) < 5 or _ret(raw) != 0:
        raise ValueError("GetAvailableTables failed or returned unknown ABI")
    count, keys = raw[0], raw[1]
    if type(count) is not int or not isinstance(keys, (list, tuple)) or len(keys) < count:
        raise ValueError("GetAvailableTables count/keys mismatch")
    names = tuple(keys[:count])
    if any(not isinstance(x, str) or not x for x in names) or len(set(names)) != len(names):
        raise ValueError("GetAvailableTables contains invalid or duplicate names")
    return names


def _field_metadata(db: Any, key: str) -> dict[str, Any]:
    try:
        raw = db.GetAllFieldsInTable(key)
        if not isinstance(raw, (tuple, list)) or len(raw) != 8:
            return {"status": "ABI_UNRECOGNIZED", "shape": len(raw) if isinstance(raw, (tuple, list)) else type(raw).__name__}
        version, count, fields, _names, _desc, units, _importable, code = raw
        if code != 0 or type(count) is not int or not isinstance(fields, (list, tuple)) or not isinstance(units, (list, tuple)):
            return {"status": "UNAVAILABLE", "ret_code": code}
        if len(fields) != count or len(units) != count:
            return {"status": "ARRAY_LENGTH_MISMATCH"}
        return {
            "status": "OK", "table_version": version,
            "fields": list(fields),
            "units_by_field": {str(field): str(unit) for field, unit in zip(fields, units)},
        }
    except Exception as exc:
        return {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}


def _display(db: Any, key: str, sample_count: int) -> dict[str, Any]:
    attempts = (
        ("seven_list", (key, [], "", 0, [], 0, [])),
        ("seven_string", (key, "", "", 0, [], 0, [])),
    )
    errors: list[str] = []
    for signature, args in attempts:
        try:
            raw = db.GetTableForDisplayArray(*args)
            if not isinstance(raw, (list, tuple)) or len(raw) < 6:
                raise ValueError("Unexpected display-table ABI")
            if _ret(raw) != 0:
                raise ValueError(f"ret_code={_ret(raw)}")
            fields, count, flat = raw[2], raw[3], raw[4]
            if not isinstance(fields, (list, tuple)) or not isinstance(flat, (list, tuple)):
                raise ValueError("Field/data arrays unavailable")
            if not fields or len(set(fields)) != len(fields) or type(count) is not int or count < 0:
                raise ValueError("Invalid fields/count")
            if len(flat) != count * len(fields):
                raise ValueError(f"Cell count mismatch: {len(flat)} != {count} × {len(fields)}")
            examples = []
            n = len(fields)
            for idx in range(min(count, sample_count)):
                row = dict(zip(fields, flat[idx*n:(idx+1)*n]))
                examples.append({key: str(row[key]) for key in SAMPLE_FIELDS if key in row})
            return {
                "status": "READ_OK", "api_signature": signature,
                "field_keys": list(fields), "record_count": count,
                "sample_rows": examples,
            }
        except Exception as exc:
            errors.append(f"{signature}: {type(exc).__name__}: {exc}")
    return {"status": "READ_UNAVAILABLE", "errors": errors}


def _compare(role: str, fields: list[str]) -> dict[str, Any]:
    observed = set(fields)
    out = {}
    for requirement, alternatives in EXPECTED.get(role, {}).items():
        matched = [name for name in alternatives if name in observed]
        out[requirement] = {
            "observed_candidates": matched,
            "status": "FOUND_NAME_NOT_SEMANTICALLY_APPROVED" if len(matched) == 1 else
                      "AMBIGUOUS" if len(matched) > 1 else "MISSING",
        }
    return out


def run_probe(sap: Any, sample_count: int = 2) -> dict[str, Any]:
    db = sap.DatabaseTables
    model = sap.GetModelFilename(True)
    if isinstance(model, (tuple, list)):
        model = model[0]
    keys = set(_available(db))
    results = []
    for role, key in TARGETS:
        if key not in keys:
            results.append({"role": role, "table_key": key, "status": "TABLE_NOT_LISTED"})
            continue
        meta = _field_metadata(db, key)
        display = _display(db, key, sample_count)
        fields = display.get("field_keys") or meta.get("fields") or []
        results.append({
            "role": role, "table_key": key, "status": "OBSERVED",
            "metadata": meta, "display": display,
            "field_name_comparison": _compare(role, fields),
        })
    return {
        "scope": "ETABS_GEOMETRY_AND_MODAL_HEADERS_ONLY",
        "model_basename": ntpath.basename(str(model)),
        "present_units_enum": sap.GetPresentUnits(),
        "available_table_count": len(keys),
        "tables": results,
        "engineering_checks_executed": 0,
        "etabs_state_mutation": "NONE",
        "conclusion": "SCHEMA_PROBE_ONLY_NOT_ENGINEERING_PASS",
    }


def self_test() -> int:
    class DB:
        def GetAvailableTables(self, *_):
            keys = [key for _, key in TARGETS]
            return len(keys), keys, keys, [0] * len(keys), 0
        def GetAllFieldsInTable(self, key):
            fields = ["Name", "t2", "t3"]
            return 1, 3, fields, fields, [""] * 3, ["", "m", "m"], [False] * 3, 0
        def GetTableForDisplayArray(self, key, *_):
            fields = ["Name", "t2", "t3"]
            return None, 1, fields, 1, ["C40", "0.4", "0.4"], 0
    class Model:
        DatabaseTables = DB()
        def GetModelFilename(self, full):
            return r"C:\tmp\synthetic.edb"
        def GetPresentUnits(self):
            return 6
    result = run_probe(Model(), 2)
    section = next(t for t in result["tables"] if t["role"] == "RECTANGULAR_SECTIONS")
    assert section["display"]["record_count"] == 1
    assert section["metadata"]["units_by_field"]["t2"] == "m"
    assert section["field_name_comparison"]["depth"]["status"] == "FOUND_NAME_NOT_SEMANTICALLY_APPROVED"
    assert result["engineering_checks_executed"] == 0
    print("SELF_TEST_PASS: no COM, no checks, exact table/metadata shape")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Temporary ETABS 23.2 live schema reader (console only)")
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.samples < 0 or args.samples > 5:
        parser.error("--samples must be between 0 and 5")
    if sys.platform != "win32":
        print("ERROR: live ETABS COM requires Windows")
        return 2
    import comtypes
    import comtypes.client
    comtypes.CoInitialize()
    etabs = sap = None
    try:
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        sap = etabs.SapModel
        if sap is None:
            raise RuntimeError("ETABS SapModel unavailable")
        result = run_probe(sap, args.samples)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        print("\nSCHEMA_PROBE_COMPLETE; no check executed; no ETABS setting modified.")
        return 0
    except Exception as exc:
        print(f"SCHEMA_PROBE_ERROR: {type(exc).__name__}: {exc}")
        return 2
    finally:
        sap = None
        etabs = None
        comtypes.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
