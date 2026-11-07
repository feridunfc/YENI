"""VS04-E targeted ETABS basis-table probe with NO display-case or model setters.

The inventory returns table name candidates (not approved semantic bindings).
It reads fields and complete rows only for a bounded, explicitly recorded
subset of listed keys; uncaptured candidates remain visible in the ledger.
"""
from __future__ import annotations

from typing import Any

from .analysis_sources import _full_metadata
from .etabs_geometry import _read_one
from .etabs_modal import ModalCaptureError, _selected_cases


def parse_available_tables(raw: Any) -> list[dict]:
    if not isinstance(raw, (tuple, list)) or len(raw) not in (5, 6):
        raise ModalCaptureError("VS04E_AVAILABLE_TABLES_UNKNOWN_ABI")
    n, keys, names, import_types = raw[:4]
    ret = raw[-1]
    if type(ret) is not int or ret != 0 or type(n) is not int or n < 0:
        raise ModalCaptureError("VS04E_AVAILABLE_TABLES_INVALID_RET_OR_COUNT")
    if not (isinstance(keys, (tuple, list)) and isinstance(names, (tuple, list))
            and isinstance(import_types, (tuple, list)) and
            len(keys) == len(names) == len(import_types) == n):
        raise ModalCaptureError("VS04E_AVAILABLE_TABLES_ARRAY_MISMATCH")
    if (any(not isinstance(k, str) or not k or not isinstance(names[i], str)
            for i, k in enumerate(keys)) or len(set(keys)) != n):
        raise ModalCaptureError("VS04E_AVAILABLE_TABLES_DUPLICATE_OR_INVALID_KEY")
    return [{"table_key":k, "table_name":names[i], "import_type":import_types[i]}
            for i,k in enumerate(keys)]


def _candidate_roles(name: str) -> list[str]:
    text = name.casefold()
    pairs = (
        ("story_geometry", ("story definitions", "story data", "story information")),
        ("seismic_mass", ("mass summary", "mass source", "assembled joint masses")),
        ("case_definition", ("load case definitions",)),
        ("spectrum_function", ("response spectrum functions", "functions - response spectrum")),
        ("combination_definition", ("load combination definitions",)),
        ("spectrum_or_scaling", ("response spectrum",)),
        ("modal_definition", ("modal case definitions",)),
    )
    return [role for role, tokens in pairs if any(t in text for t in tokens)]


def capture_basis_probe(sap: Any, *, max_tables: int = 24) -> dict:
    """Observe available ETABS candidate table keys and source fields/rows.

    One already-locked ETABS model only. The caller owns COM lifecycle.
    Neither load case selection nor present unit settings are altered.
    """
    if type(max_tables) is not int or not 1 <= max_tables <= 32:
        raise ValueError("max_tables must be an integer 1..32")
    if sap.GetModelIsLocked() is not True:
        raise ModalCaptureError("VS04E_REQUIRES_EXISTING_LOCKED_ANALYSIS_MODEL")
    db = sap.DatabaseTables
    before_units = sap.GetPresentUnits()
    original = _selected_cases(db)
    raw = db.GetAvailableTables()
    inventory = parse_available_tables(raw)
    relevant = []
    for item in inventory:
        roles = _candidate_roles(item["table_key"] + " " + item["table_name"])
        if roles:
            relevant.append({**item, "candidate_roles_not_approved":roles})
    relevant.sort(key=lambda x:x["table_key"])
    selected = relevant[:max_tables]
    reads = {}
    for item in selected:
        key = item["table_key"]
        try:
            table = _read_one(db,key)
        except Exception as exc:
            table = {"status":"CAPTURE_ERROR", "table_key":key,
                     "fields":[], "rows":[], "row_count":0,
                     "error":f"{type(exc).__name__}: {exc}"}
        table["field_metadata"] = _full_metadata(db,key)
        reads[key]=table
    after_units = sap.GetPresentUnits()
    restored = _selected_cases(db)
    if restored != original:
        raise ModalCaptureError("VS04E_READ_ONLY_CASE_SELECTION_CHANGED")
    if type(before_units) is not int or after_units != before_units:
        raise ModalCaptureError("VS04E_READ_ONLY_PRESENT_UNITS_CHANGED")
    return {
        "schema":"tbdy.next.vs04e.basis-source-probe.v1",
        "source_mode":"LIVE_ETABS",
        "read_only_invariant_proven":True,
        "units_before":before_units, "units_after":after_units,
        "display_cases_before":list(original), "display_cases_after":list(restored),
        "available_table_count":len(inventory), "available_tables":inventory,
        "candidate_table_count":len(relevant),
        "candidate_tables":relevant,
        "read_table_keys":[x["table_key"] for x in selected],
        "not_read_table_keys":[x["table_key"] for x in relevant[max_tables:]],
        "table_reads":reads,
        "schema_roles_approved":False,
        "analysis_generation_proven":False,
        "engineering_release":"NOT_READY",
    }


def review_basis_probe(payload: Any) -> dict:
    """Review all known candidate names even if tables are not safely readable."""
    base={"stage":"VS04_E_BASIS_SOURCE_PROBE", "engineering_release":"NOT_READY",
          "formal_compliance":"NOT_PROVEN","schema_roles_approved":False}
    if (not isinstance(payload,dict) or payload.get("schema") !=
        "tbdy.next.vs04e.basis-source-probe.v1" or
        payload.get("read_only_invariant_proven") is not True or
        payload.get("units_before") != payload.get("units_after") or
        payload.get("display_cases_before") != payload.get("display_cases_after")):
        return {**base,"status":"SOURCE_REJECTED","reason":"READONLY_CAPTURE_OR_SCHEMA_INVALID"}
    reads=payload.get("table_reads")
    relevant=payload.get("candidate_tables")
    if not isinstance(reads,dict) or not isinstance(relevant,list):
        return {**base,"status":"SOURCE_REJECTED","reason":"INVENTORY_INVALID"}
    rows=[]
    seen=set()
    for rec in relevant:
        if not isinstance(rec,dict) or not isinstance(rec.get("table_key"),str):
            return {**base,"status":"SOURCE_REJECTED","reason":"INVENTORY_KEY_INVALID"}
        key=rec["table_key"]
        if key in seen:
            return {**base,"status":"SOURCE_REJECTED","reason":"DUPLICATE_CANDIDATE"}
        seen.add(key)
        table=reads.get(key)
        status="CANDIDATE_NOT_READ"
        reasons=["KEY_NOT_CAPTURED_UNDER_LIMIT"]
        if isinstance(table,dict):
            status="OBSERVED_UNAPPROVED" if (
                table.get("status")=="CAPTURED" and
                isinstance(table.get("rows"),list) and
                type(table.get("row_count")) is int and
                table["row_count"]==len(table["rows"]) and
                isinstance(table.get("fields"),list) and
                table.get("field_metadata",{}).get("status")=="OK"
            ) else "NOT_PROVEN"
            reasons=[] if status=="OBSERVED_UNAPPROVED" else ["ROWS_OR_FIELD_METADATA_NOT_CAPTURED"]
        rows.append({"table_key":key,"roles_not_approved":rec.get("candidate_roles_not_approved",[]),
                     "status":status,"row_count":table.get("row_count") if isinstance(table,dict) else None,
                     "fields":table.get("fields") if isinstance(table,dict) else None,
                     "reason_codes":reasons})
    return {**base,
            "status":"SOURCE_CANDIDATES_OBSERVED_PENDING_REVIEW" if rows else "NO_CANDIDATE_TABLES",
            "candidate_count":len(rows),
            "observed_candidate_count":sum(x["status"]=="OBSERVED_UNAPPROVED" for x in rows),
            "available_table_count":payload.get("available_table_count"),
            "candidates":rows,
            "note":"Semantic field mapping, analysis generation and seismic design basis require separate verification."}
