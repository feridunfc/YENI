"""Generic read-only ETABS v23 table gateway — Windows, source-first.

Commands:
  discover: list all available exact ETABS table keys + metadata (no guessed names)
  capture : capture any requested tables and source rows, with selected load cases
  template: create exact observed-field binding template from a capture
  bind    : apply a reviewed field/unit binding to captured rows offline

Only reversible temporary DISPLAY selection may be changed. No analysis,
model edit/save, material/units mutation, or engineering compliance decision.
Self-contained except for comtypes on Windows live commands.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping

SCHEMA = "tbdy.next.etabs.generic-source-capture.v1"
BIND_SCHEMA = "tbdy.next.etabs.typed-field-binding.v1"
OUTPUT_SCHEMA = "tbdy.next.etabs.typed-source-variables.v1"
PROFILES = {
    # Table-key discovery hints, NOT approved engineering field bindings.
    "delta": {
        "required": (
            "Joint Displacements", "Story Definitions",
            "Tower and Base Story Definitions", "Column Object Connectivity",
        ),
        "optional": (
            "Joint Coordinates", "Point Object Connectivity",
            "Joint Object Connectivity", "Joint Assignments - Diaphragms",
            "Story Drifts", "Story Max Over Avg Drifts",
            "Modal Periods And Frequencies",
        ),
    },
}


class SourceError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def seal(value: dict[str, Any]) -> dict[str, Any]:
    if "payload_sha256" in value:
        raise SourceError("ALREADY_SEALED")
    value["payload_sha256"] = sha256(canonical(value)).hexdigest()
    return value


def verify(record: Mapping[str, Any]) -> None:
    if not isinstance(record, Mapping):
        raise SourceError("SOURCE_NOT_OBJECT")
    digest = record.get("payload_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise SourceError("SOURCE_DIGEST_MISSING")
    unsigned = {k: v for k, v in record.items() if k != "payload_sha256"}
    if sha256(canonical(unsigned)).hexdigest() != digest:
        raise SourceError("SOURCE_SHA256_MISMATCH")


def save_new(path: Path, data: Mapping[str, Any]) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise SourceError("NO_OVERWRITE_OF_CAPTURE")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SourceError("INPUT_JSON_NOT_OBJECT")
    return obj


def return_code(value: Any, label: str) -> int:
    if type(value) is int:
        return value
    if isinstance(value, (list, tuple)) and value and type(value[-1]) is int:
        return value[-1]
    raise SourceError(label + ":UNKNOWN_RETURN_CODE")


def available_tables(db: Any) -> list[dict[str, Any]]:
    raw = db.GetAvailableTables()
    if not isinstance(raw, (list, tuple)) or len(raw) not in (5, 6):
        raise SourceError("GET_AVAILABLE_TABLES_ABI_UNKNOWN")
    count, keys, names, types = raw[:4]
    if (return_code(raw, "GetAvailableTables") != 0
            or type(count) is not int or count < 0
            or any(not isinstance(x, (list, tuple)) or len(x) != count
                   for x in (keys, names, types))
            or any(not isinstance(k, str) or not k or k != k.strip() for k in keys)
            or len(set(keys)) != count):
        raise SourceError("GET_AVAILABLE_TABLES_INVALID")
    return [{"table_key": k, "table_name": str(names[i]), "import_type": types[i]}
            for i, k in enumerate(keys)]


def field_schema(db: Any, key: str) -> dict[str, Any]:
    try:
        raw = db.GetAllFieldsInTable(key)
        if not isinstance(raw, (list, tuple)) or len(raw) != 8:
            raise SourceError("GET_ALL_FIELDS_ABI_UNKNOWN")
        version, count, keys, names, desc, units, imports, code = raw
        if (type(code) is not int or code != 0 or type(count) is not int or count < 1
                or any(not isinstance(v, (list, tuple)) or len(v) != count
                       for v in (keys, names, desc, units, imports))
                or len(set(keys)) != count
                or any(not isinstance(v, str) or not v for v in keys)):
            raise SourceError("GET_ALL_FIELDS_INVALID")
        return {
            "status": "OK", "table_version": version, "field_count": count,
            "field_keys": list(keys), "field_names": list(names),
            "field_descriptions": list(desc),
            "units_by_field": dict(zip(keys, units)),
            "importable_by_field": dict(zip(keys, imports)),
        }
    except Exception as exc:
        return {"status": "METADATA_ERROR", "error": f"{type(exc).__name__}: {exc}"}


def read_table(db: Any, key: str, *, max_rows: int = 500_000) -> dict[str, Any]:
    problems = []
    for signature, args in (
        ("seven_list", (key, [], "", 0, [], 0, [])),
        ("seven_string", (key, "", "", 0, [], 0, [])),
    ):
        try:
            raw = db.GetTableForDisplayArray(*args)
            if not isinstance(raw, (list, tuple)) or len(raw) < 6:
                raise SourceError("GET_TABLE_DISPLAY_ABI_UNKNOWN")
            if return_code(raw, "GetTableForDisplayArray") != 0:
                raise SourceError(f"ETABS_RET_CODE_{raw[-1]}")
            fields, count, flat = raw[2], raw[3], raw[4]
            if (not isinstance(fields, (list, tuple)) or not fields
                    or any(not isinstance(v, str) or not v for v in fields)
                    or len(set(fields)) != len(fields)
                    or type(count) is not int or count < 0
                    or not isinstance(flat, (list, tuple))
                    or len(flat) != count * len(fields)):
                raise SourceError("DISPLAY_ARRAY_INVALID_OR_INCOMPLETE")
            if count > max_rows:
                raise SourceError(f"ROW_LIMIT_EXCEEDED:{count}>{max_rows}")
            n = len(fields)
            rows = [dict(zip(fields, (str(v) for v in flat[i:i+n])))
                    for i in range(0, len(flat), n)]
            return {"table_key": key, "status": "CAPTURED" if count else "EMPTY_TABLE",
                    "fields": list(fields), "row_count": count, "rows": rows,
                    "api_signature": signature}
        except Exception as exc:
            problems.append(f"{signature}: {type(exc).__name__}: {exc}")
    return {"table_key": key, "status": "CAPTURE_ERROR", "fields": [],
            "row_count": 0, "rows": [], "error": " | ".join(problems)}



def capture_distributed_frame_loads_by_object(
    sap: Any, beam_table: Mapping[str, Any], *, max_beams: int = 50000,
    max_loads: int = 200000,
) -> dict[str, Any]:
    """Read ETABS FrameObj.GetLoadDistributed on observed beam objects only.

    Source adapter inside the EXISTING generic ETABS COM gateway, not a
    second COM attachment. Retains every failed object and all returned load
    spans; a failed object is NEVER interpreted as an empty assignment.
    CSI GetLoadDistributed outputs 12 fields followed by a return code.
    """
    schema = "tbdy.next.etabs.frame-object-distributed-load-probe.v1"
    if sap.GetModelIsLocked() is not True or sap.GetPresentUnits() != 6:
        raise SourceError("FRAME_LOAD_PROBE_REQUIRES_LOCKED_KN_M_C")
    if (not isinstance(beam_table, Mapping)
            or beam_table.get("status") != "CAPTURED"
            or beam_table.get("table_key") != "Beam Object Connectivity"
            or not {"UniqueName", "Story", "Length"}.issubset(
                beam_table.get("fields") or [])
            or (beam_table.get("field_metadata") or {}).get(
                "units_by_field", {}).get("Length") != "m"):
        raise SourceError("FRAME_LOAD_PROBE_BEAM_SCHEMA_INVALID")
    beam_rows = beam_table.get("rows")
    if (not isinstance(beam_rows, list)
            or beam_table.get("row_count") != len(beam_rows)
            or len(beam_rows) > max_beams):
        raise SourceError("FRAME_LOAD_PROBE_BEAM_CENSUS_INVALID")
    seen: set[str] = set()
    output: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    successful = 0
    source = sap.FrameObj  # read-only GetLoadDistributed only
    for beam in beam_rows:
        name = beam.get("UniqueName")
        if not isinstance(name, str) or not name or name in seen:
            raise SourceError("FRAME_LOAD_PROBE_DUPLICATE_BEAM_ID")
        seen.add(name)
        try:
            raw = source.GetLoadDistributed(name)
            if not isinstance(raw, (tuple, list)) or len(raw) != 13:
                raise SourceError("GET_LOAD_DISTRIBUTED_ABI_UNKNOWN")
            count = raw[0]
            if type(count) is not int or count < 0 or return_code(raw, "GetLoadDistributed") != 0:
                raise SourceError("GET_LOAD_DISTRIBUTED_RET_OR_COUNT")
            arrays = raw[1:12]
            if any(not isinstance(a, (tuple, list)) or len(a) != count
                   for a in arrays):
                raise SourceError("GET_LOAD_DISTRIBUTED_ARRAY_LENGTH_INVALID")
            parsed = []
            for i in range(count):
                frame_id, pattern, my_type, coordinate, direction = (
                    arrays[0][i], arrays[1][i], arrays[2][i], arrays[3][i],
                    arrays[4][i])
                if (frame_id != name or not isinstance(pattern, str)
                        or not pattern or type(my_type) is not int
                        or type(direction) is not int
                        or not isinstance(coordinate, str)):
                    raise SourceError("GET_LOAD_DISTRIBUTED_IDENTITY_INVALID")
                nums = []
                for a in arrays[5:11]:
                    try:
                        v = Decimal(str(a[i]))
                    except (ValueError, InvalidOperation):
                        raise SourceError("GET_LOAD_DISTRIBUTED_NUMERIC_INVALID") from None
                    if not v.is_finite():
                        raise SourceError("GET_LOAD_DISTRIBUTED_NONFINITE")
                    nums.append(v)
                rd1, rd2, d1, d2, v1, v2 = nums
                if rd1 < 0 or rd2 > 1 or rd1 > rd2 or d1 < 0 or d2 < d1:
                    raise SourceError("GET_LOAD_DISTRIBUTED_SPAN_INVALID")
                parsed.append({
                    "UniqueName": name, "Story": str(beam["Story"]),
                    "LoadPattern": pattern, "MyType": str(my_type),
                    "CSys": coordinate, "Dir": str(direction),
                    "RelDistA": str(rd1), "RelDistB": str(rd2),
                    "AbsDistA": str(d1), "AbsDistB": str(d2),
                    "ValA": str(v1), "ValB": str(v2),
                })
            if len(output) + len(parsed) > max_loads:
                raise SourceError("FRAME_LOAD_PROBE_LOAD_ROW_LIMIT_EXCEEDED")
            output.extend(parsed)
            successful += 1
        except Exception as exc:
            # Do not misclassify API failures as no load on that beam.
            unresolved.append({"UniqueName": name, "reason": f"{type(exc).__name__}:{exc}"})
    return {
        "schema": schema,
        "source_method": "SapModel.FrameObj.GetLoadDistributed",
        "status": "CAPTURED" if not unresolved else "SOURCE_PARTIAL",
        "model_units_code": 6,
        "beam_count": len(beam_rows),
        "successful_beam_count": successful,
        "unresolved_beam_count": len(unresolved),
        "load_row_count": len(output),
        "rows": output,
        "unresolved_beams": unresolved,
        "units_by_field": {
            "RelDistA": "", "RelDistB": "", "AbsDistA": "m",
            "AbsDistB": "m", "ValA": "kN/m", "ValB": "kN/m",
        },
        "engineering_release": "NOT_READY",
    }

def selected_cases(db: Any) -> tuple[str, ...]:
    try:
        raw = db.GetLoadCasesSelectedForDisplay()
    except TypeError:
        raw = db.GetLoadCasesSelectedForDisplay(0, [])
    if not isinstance(raw, (list, tuple)) or len(raw) < 3:
        raise SourceError("SELECTED_CASES_ABI_UNKNOWN")
    count, names = raw[:2]
    code = return_code(raw, "SelectedCases")
    if type(count) is not int or count < 0 or not isinstance(names, (list, tuple)):
        raise SourceError("SELECTED_CASES_INVALID")
    if count == 0 and code == 1 and all(x is None or x == "" for x in names):
        return ()  # observed ETABS 23.2 no-selection projection
    if code != 0 or len(names) < count:
        raise SourceError("SELECTED_CASES_RET_OR_ARRAY_INVALID")
    chosen = tuple(names[:count])
    if any(not isinstance(x, str) or not x.strip() for x in chosen) or len(set(chosen)) != count:
        raise SourceError("SELECTED_CASES_NAMES_INVALID")
    return chosen


def set_cases(db: Any, values: tuple[str, ...]) -> None:
    request = list(values) if values else [""]
    code = return_code(db.SetLoadCasesSelectedForDisplay(request), "SetSelectedCases")
    if code != 0:
        raise SourceError(f"SET_SELECTED_CASES_RET_{code}")


def model_file(sap: Any) -> str:
    raw = sap.GetModelFilename(True)
    if isinstance(raw, (list, tuple)):
        raw = raw[0]
    if not isinstance(raw, str) or not raw:
        raise SourceError("ETABS_MODEL_FILENAME_UNAVAILABLE")
    return raw


def resolve_keys(inventory: list[dict[str, Any]], *, preset: str | None = None,
                 exact: tuple[str, ...] = (), matching: tuple[str, ...] = (),
                 all_tables: bool = False) -> tuple[list[str], list[str], list[str]]:
    available = [item["table_key"] for item in inventory]
    if all_tables:
        return sorted(available), [], []
    if preset and preset not in PROFILES:
        raise SourceError("UNKNOWN_PRESET")
    found: set[str] = set()
    unmatched: list[str] = []
    optional_missed: list[str] = []
    # Preset titles are discovery hints. Optional synonyms do not falsely
    # reject an otherwise complete request for the mandatory source tables.
    if preset:
        for level in ("required", "optional"):
            for query in PROFILES[preset][level]:
                matches = ([query] if query in available else []) if level == "required" else [
                    key for key in available if query.casefold() in key.casefold()]
                if not matches:
                    (unmatched if level == "required" else optional_missed).append(query)
                found.update(matches)
    for query in exact:
        if query not in available:
            unmatched.append(query)
        else:
            found.add(query)
    for query in matching:
        matches = [key for key in available if query.casefold() in key.casefold()]
        if not matches:
            unmatched.append(query)
        found.update(matches)
    return sorted(found), sorted(set(unmatched)), sorted(set(optional_missed))


def capture(sap: Any, *, action: str, cases: tuple[str, ...] = (),
            preset: str | None = None, exact: tuple[str, ...] = (),
            matching: tuple[str, ...] = (), all_tables: bool = False,
            max_rows: int = 500_000,
            frame_load_probe: bool = False) -> dict[str, Any]:
    if action not in ("discover", "capture"):
        raise SourceError("UNKNOWN_CAPTURE_ACTION")
    if any(not isinstance(c, str) or not c or c != c.strip() for c in cases) or len(set(cases)) != len(cases):
        raise SourceError("INVALID_CASE_SELECTION")
    if max_rows < 1:
        raise SourceError("MAX_ROWS_NONPOSITIVE")
    if frame_load_probe and action != "capture":
        raise SourceError("FRAME_LOAD_PROBE_CAPTURE_ONLY")
    db = sap.DatabaseTables
    original = selected_cases(db)
    before_units = sap.GetPresentUnits()
    locked = sap.GetModelIsLocked()
    if type(before_units) is not int or type(locked) is not bool:
        raise SourceError("MODEL_UNITS_OR_LOCK_STATE_UNKNOWN")
    if action == "capture" and not locked:
        raise SourceError("MODEL_NOT_LOCKED_RESULTS_NOT_AVAILABLE_NO_ANALYSIS_RUN")
    model = model_file(sap)
    inventory = available_tables(db)
    keys, missed, optional_missed = resolve_keys(
        inventory, preset=preset, exact=exact, matching=matching,
        all_tables=all_tables)
    if action == "capture" and not (all_tables or preset or exact or matching):
        raise SourceError("EXPLICIT_TABLE_TARGET_OR_PRESET_REQUIRED")
    result: dict[str, Any] = {}
    if action == "discover":
        # Schema for available/selected tables; avoid leaking unbounded rows.
        for key in keys if keys else [v["table_key"] for v in inventory]:
            result[key] = {"table_key": key, "status": "SCHEMA_ONLY",
                           "field_metadata": field_schema(db, key)}
    else:
        changed = tuple(cases) != original if cases else False
        error: Exception | None = None
        try:
            if changed:
                set_cases(db, cases)
                if selected_cases(db) != cases:
                    raise SourceError("TEMPORARY_CASE_SELECTION_NOT_CONFIRMED")
            for key in keys:
                val = read_table(db, key, max_rows=max_rows)
                val["field_metadata"] = field_schema(db, key)
                result[key] = val
        except Exception as exc:
            error = exc
        finally:
            if changed:
                # Restore even when setter or a table read fails.
                try:
                    set_cases(db, original)
                    if selected_cases(db) != original:
                        raise SourceError("SELECTION_NOT_RESTORED")
                except Exception as exc:
                    raise SourceError("CRITICAL_ETABS_DISPLAY_SELECTION_RESTORE_FAILED: " + str(exc)) from exc
        if error:
            raise SourceError("ETABS_CAPTURE_ABORTED: " + str(error)) from error
    # Preserve the original table CAPTURE_ERROR while independently probing
    # actual object assignments through the same SapModel. Never overwrite a
    # failed DatabaseTables response with manufactured successful rows.
    frame_probe = None
    if frame_load_probe:
        beam_table = result.get("Beam Object Connectivity")
        if beam_table is None:
            raise SourceError("FRAME_LOAD_PROBE_REQUIRES_BEAM_TABLE")
        frame_probe = capture_distributed_frame_loads_by_object(sap, beam_table)
    after_units = sap.GetPresentUnits()
    restored = selected_cases(db)
    if before_units != after_units or restored != original:
        raise SourceError("CRITICAL_ETABS_UNITS_OR_DISPLAY_SELECTION_CHANGED")
    summary = "SCHEMA_DISCOVERED" if action == "discover" else (
        "CAPTURED" if keys and not missed and all(v["status"] == "CAPTURED" and
                                     v["field_metadata"]["status"] == "OK" for v in result.values())
        else "SOURCE_PARTIAL")
    record = {
        "schema": SCHEMA,
        "action": action,
        "status": summary,
        "model": model,
        "model_locked": locked,
        "model_units_code": before_units,
        "model_units_unchanged": True,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_selection_before": list(original),
        "case_selection_during": list(cases) if action == "capture" and cases else list(original),
        "case_selection_after": list(restored),
        "selection_restored": True,
        "inventory": inventory,
        "table_queries_not_found": missed,
        "preset_optional_hints_not_found": optional_missed,
        "table_reads": result,
        **({"frame_load_object_probe": frame_probe} if frame_probe is not None else {}),
        "source_only": True,
        "analysis_generation_proven": False,
        "engineering_release": "NOT_READY",
    }
    return seal(record)


def make_template(record: Mapping[str, Any]) -> dict[str, Any]:
    verify(record)
    if record.get("schema") != SCHEMA or record.get("action") != "capture":
        raise SourceError("CAPTURE_REQUIRED_FOR_TEMPLATE")
    entries = []
    for key, tab in record.get("table_reads", {}).items():
        if tab.get("status") != "CAPTURED" or tab.get("field_metadata", {}).get("status") != "OK":
            continue
        meta = tab["field_metadata"]
        entries.append({"table_key": key, "source_table_sha256": sha256(canonical(tab)).hexdigest(),
                        "identity": [], "fields": {
                            field: {"field": field, "kind": "text", "unit": meta["units_by_field"].get(field, "")}
                            for field in tab["fields"]
                        }})
    return {"schema": BIND_SCHEMA, "capture_sha256": record["payload_sha256"],
            "status": "UNREVIEWED_BINDING_TEMPLATE", "bindings": entries,
            "note": "Edit identity and numeric kinds after inspecting real schema. No automated semantic approval."}


def bind(record: Mapping[str, Any], specification: Mapping[str, Any]) -> dict[str, Any]:
    verify(record)
    if (record.get("schema") != SCHEMA or record.get("action") != "capture"
            or not isinstance(specification, Mapping)
            or specification.get("schema") != BIND_SCHEMA
            or specification.get("capture_sha256") != record.get("payload_sha256")):
        raise SourceError("BINDING_SOURCE_OR_SCHEMA_MISMATCH")
    if specification.get("status") != "REVIEWED_EXACT_FIELDS":
        raise SourceError("BINDING_TEMPLATE_NOT_REVIEWED")
    output: dict[str, Any] = {}
    for config in specification.get("bindings", []):
        key = config.get("table_key")
        tab = record.get("table_reads", {}).get(key)
        if not tab or tab.get("status") != "CAPTURED" or tab.get("field_metadata", {}).get("status") != "OK":
            raise SourceError("BINDING_TABLE_NOT_CAPTURED:" + str(key))
        if sha256(canonical(tab)).hexdigest() != config.get("source_table_sha256"):
            raise SourceError("BINDING_TABLE_HASH_CHANGED:" + str(key))
        mapping = config.get("fields")
        if not isinstance(mapping, dict) or not mapping:
            raise SourceError("BINDING_FIELDS_MISSING")
        source_units = tab["field_metadata"]["units_by_field"]
        for variable, field_spec in mapping.items():
            if (not isinstance(field_spec, Mapping) or field_spec.get("field") not in tab["fields"]
                    or field_spec.get("kind") not in ("text", "decimal")
                    or field_spec.get("unit") != source_units.get(field_spec["field"])):
                raise SourceError("FIELD_KEY_KIND_OR_UNIT_MISMATCH:" + str(variable))
        identities = config.get("identity", [])
        if not isinstance(identities, list) or any(x not in mapping for x in identities):
            raise SourceError("IDENTITY_FIELD_NOT_BOUND")
        observed = set()
        typed = []
        for row in tab["rows"]:
            values = {}
            for name, v in mapping.items():
                value = row[v["field"]]
                if v["kind"] == "decimal":
                    try:
                        number = Decimal(value)
                    except InvalidOperation as exc:
                        raise SourceError("NONNUMERIC_FIELD:" + name) from exc
                    if not number.is_finite():
                        raise SourceError("NONFINITE_FIELD:" + name)
                    values[name] = str(number)  # preserve exact observed precision
                else:
                    values[name] = value
            if identities:
                ident = tuple(values[n] for n in identities)
                if ident in observed:
                    raise SourceError("DUPLICATE_TYPED_ROW_IDENTITY:" + str(key))
                observed.add(ident)
            typed.append(values)
        output[key] = {"source_row_count": tab["row_count"], "row_count": len(typed),
                       "identity": identities, "field_units": {
                           name: f["unit"] for name, f in mapping.items()}, "rows": typed}
    return seal({"schema": OUTPUT_SCHEMA, "source_capture_sha256": record["payload_sha256"],
                 "binding_sha256": sha256(canonical(specification)).hexdigest(),
                 "tables": output, "source_only": True, "formal_compliance": "NOT_PROVEN"})


def attach_live(action: str, **kwargs: Any) -> dict[str, Any]:
    if sys.platform != "win32":
        raise SourceError("LIVE_ETABS_REQUIRES_WINDOWS")
    try:
        import comtypes
        import comtypes.client
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("comtypes"):
            raise SourceError(
                "COMTYPES_MISSING: install with python -m pip install -e .[etabs-windows]"
            ) from exc
        raise
    comtypes.CoInitialize()
    app = sap = None
    try:
        app = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        sap = app.SapModel
        if sap is None:
            raise SourceError("ACTIVE_ETABS_SAPMODEL_NOT_AVAILABLE")
        return capture(sap, action=action, **kwargs)
    finally:
        sap = app = None
        comtypes.CoUninitialize()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("discover", "capture"):
        q = sub.add_parser(name)
        q.add_argument("--out", type=Path, required=True)
        q.add_argument("--preset", choices=sorted(PROFILES), default=None)
        q.add_argument("--table", action="append", default=[], help="Exact ETABS table key, repeatable")
        q.add_argument("--match", action="append", default=[], help="Case-insensitive table key substring, repeatable")
        q.add_argument("--all", action="store_true", help="Explicitly enumerate/capture ALL tables")
        q.add_argument("--max-rows", type=int, default=500000)
        q.add_argument("--case", action="append", default=[], help="Select a case temporarily; repeat e.g. Modal RSX RSY")
        q.add_argument("--frame-load-probe", action="store_true", help="Read-only FrameObj.GetLoadDistributed fallback on captured beam objects")
    q = sub.add_parser("template")
    q.add_argument("--input", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    q = sub.add_parser("bind")
    q.add_argument("--input", type=Path, required=True)
    q.add_argument("--map", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if args.command == "template":
        data = make_template(read_json(args.input))
    elif args.command == "bind":
        data = bind(read_json(args.input), read_json(args.map))
    else:
        data = attach_live(args.command, cases=tuple(args.case),
                           preset=args.preset, exact=tuple(args.table),
                           matching=tuple(args.match), all_tables=args.all,
                           max_rows=args.max_rows,
                           frame_load_probe=args.frame_load_probe)
    save_new(args.out, data)
    print("STATUS:", data.get("status", data.get("schema")))
    if data.get("table_reads") is not None:
        print("MODEL:", data["model"], "UNIT_CODE:", data["model_units_code"])
        print("AVAILABLE TABLES:", len(data["inventory"]))
        print("CAPTURED TABLES:", sum(x["status"] == "CAPTURED" for x in data["table_reads"].values()))
        for key, item in data["table_reads"].items():
            print("-", key, "|", item["status"], "|", item.get("row_count", "schema"))
        print("MISSING REQUIRED TARGETS:", data["table_queries_not_found"])
        print("OPTIONAL PRESET HINTS NOT FOUND:", data["preset_optional_hints_not_found"])
    print("OUTPUT:", args.out.resolve())
    return 0 if data.get("status") not in ("SOURCE_PARTIAL",) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SourceError, OSError) as exc:
        print("SOURCE_CAPTURE_ERROR:", exc, file=sys.stderr)
        raise SystemExit(3)
