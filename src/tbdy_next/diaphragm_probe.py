"""VS04-G bounded ETABS diaphragm assignment and spectrum-modal probe.

This is an acquisition tool, not a verification of constraints, accidental
eccentricity, analysis generation or TBDY normative compliance.

Only three exact diaphragm definition/assignment tables plus one modal
spectrum output table are read. The modal table is deliberately probed
twice: under the existing display selection, then with RSX/RSY temporarily
selected and *exactly restored* in finally.
"""
from __future__ import annotations

from typing import Any

from .analysis_sources import _full_metadata
from .basis_probe import parse_available_tables
from .etabs_geometry import _read_one
from .etabs_modal import ModalCaptureError, _selected_cases, _set_cases

DIAPHRAGM_TABLES = (
    "Diaphragm Definitions",
    "Area Assignments - Diaphragms",
    "Joint Assignments - Diaphragms",
)
SPECTRUM_MODAL_TABLE = "Response Spectrum Modal Info"
REQUIRED_KEYS = DIAPHRAGM_TABLES + (SPECTRUM_MODAL_TABLE,)
SCHEMA = "tbdy.next.vs04g.diaphragm-modal-probe.v1"


def _capture(db: Any, key: str) -> dict:
    """Reuse the previously observed ETABS 23.2 ABI without alias guessing."""
    t = _read_one(db, key)
    t["field_metadata"] = _full_metadata(db, key)
    return t


def capture_diaphragm_modal_probe(
    sap: Any, *, spectrum_cases: tuple[str, str] = ("RSX", "RSY")
) -> dict:
    if sap is None or sap.GetModelIsLocked() is not True:
        raise ModalCaptureError("VS04G_LOCKED_EXISTING_ANALYSIS_REQUIRED")
    if (not isinstance(spectrum_cases, tuple) or len(spectrum_cases) != 2
            or any(not isinstance(x, str) or not x or x != x.strip() or
                   len(x) > 120 for x in spectrum_cases)
            or spectrum_cases[0] == spectrum_cases[1]):
        raise ModalCaptureError("VS04G_EXACT_DISTINCT_SPECTRUM_CASES_REQUIRED")
    db = sap.DatabaseTables
    units_before = sap.GetPresentUnits()
    # Validate units at the entry boundary. An unsupported *initial* unit is
    # not evidence that source-reading code modified ETABS display units.
    if type(units_before) is not int or units_before != 6:
        raise ModalCaptureError(
            f"VS04G_KN_M_C_REQUIRED:observed={units_before!r}:expected=6"
        )
    original = _selected_cases(db)
    inventory = parse_available_tables(db.GetAvailableTables())
    available = {r["table_key"] for r in inventory}
    observed = {}
    for key in DIAPHRAGM_TABLES:
        if key in available:
            observed[key] = _capture(db, key)
        else:
            observed[key] = {"status":"NOT_AVAILABLE","table_key":key,
                             "fields":[],"rows":[],"row_count":0,
                             "field_metadata":{"status":"UNAVAILABLE"}}
    if SPECTRUM_MODAL_TABLE in available:
        original_modal = _capture(db, SPECTRUM_MODAL_TABLE)
    else:
        original_modal = {"status":"NOT_AVAILABLE","table_key":SPECTRUM_MODAL_TABLE,
                          "fields":[],"rows":[],"row_count":0,
                          "field_metadata":{"status":"UNAVAILABLE"}}
    changed = original != spectrum_cases
    modal_selected = None
    read_error = None
    try:
        if changed:
            # The setter may mutate selection before raising, so ALWAYS
            # attempt exact original selection restoration in finally.
            _set_cases(db, spectrum_cases)
        selected = _selected_cases(db)
        if selected != spectrum_cases:
            raise ModalCaptureError("VS04G_TEMPORARY_CASE_SELECTION_UNCONFIRMED")
        if SPECTRUM_MODAL_TABLE in available:
            modal_selected = _capture(db, SPECTRUM_MODAL_TABLE)
        else:
            modal_selected = dict(original_modal)
    except Exception as exc:
        read_error = exc
    finally:
        if changed:
            try:
                _set_cases(db, original)
                restored = _selected_cases(db)
                if restored != original:
                    raise ModalCaptureError(
                        f"VS04G_DISPLAY_RESTORE_MISMATCH:{restored!r}!={original!r}")
            except Exception as exc:
                raise ModalCaptureError(
                    "VS04G_DISPLAY_RESTORE_FAILED:"+str(exc)) from exc
    if read_error is not None:
        raise ModalCaptureError("VS04G_SOURCE_READ_REJECTED:"+str(read_error)) from read_error
    if _selected_cases(db) != original:
        raise ModalCaptureError("VS04G_FINAL_CASE_SELECTION_CHANGED")
    units_after = sap.GetPresentUnits()
    if type(units_after) is not int or units_before != units_after:
        raise ModalCaptureError(
            f"VS04G_PRESENT_UNITS_CHANGED:before={units_before!r}:after={units_after!r}"
        )

    return {
        "schema":SCHEMA,"source_mode":"LIVE_ETABS",
        "original_display_cases":list(original),
        "temporary_display_cases":list(spectrum_cases),
        "display_selection_restored":True,
        "units_before":units_before, "units_after":units_after,
        "available_exact_table_keys":sorted(available.intersection(REQUIRED_KEYS)),
        "diaphragm_tables":observed,
        "spectrum_modal_original_selection":original_modal,
        "spectrum_modal_selected_cases":modal_selected,
        "analysis_generation_proven":False,
        "diaphragm_constraints_applied_proven":False,
        "eccentricity_applied_proven":False,
        "engineering_release":"NOT_READY",
    }


def review_diaphragm_modal_probe(payload: Any) -> dict:
    """Shape-only assessment, never an implicit engineering PASS."""
    base = {
        "stage":"VS04G_DIAPHRAGM_SPECTRUM_MODAL_SOURCE",
        "formal_compliance":"NOT_PROVEN",
        "engineering_release":"NOT_READY",
        "analysis_generation_proven":False,
        "accidental_eccentricity_applied_proven":False,
        "diaphragm_mass_explained":False,
    }
    if (not isinstance(payload, dict) or payload.get("schema") != SCHEMA or
            payload.get("source_mode") != "LIVE_ETABS" or
            payload.get("display_selection_restored") is not True or
            payload.get("units_before") != payload.get("units_after") or
            payload.get("units_before") != 6 or
            payload.get("analysis_generation_proven") is not False or
            payload.get("diaphragm_constraints_applied_proven") is not False):
        return {**base,"status":"SOURCE_REJECTED",
                "reason_codes":["CAPTURE_RESTORE_UNITS_OR_AUTHORITY_INVALID"],
                "tables":[]}

    record = payload.get("diaphragm_tables")
    if not isinstance(record, dict) or set(record) != set(DIAPHRAGM_TABLES):
        return {**base,"status":"SOURCE_REJECTED",
                "reason_codes":["DIAPHRAGM_TABLE_INVENTORY_INVALID"],
                "tables":[]}
    def item(key: str, table: Any) -> dict:
        reasons=[]
        if not isinstance(table,dict) or table.get("table_key") != key:
            reasons.append("TABLE_MISSING_OR_WRONG_ID")
            table={}
        fields=table.get("fields")
        rows=table.get("rows")
        meta=table.get("field_metadata") or {}
        if table.get("status") != "CAPTURED":
            reasons.append("ETABS_TABLE_NOT_CAPTURED")
        if (not isinstance(fields,list) or not isinstance(rows,list) or
                type(table.get("row_count")) is not int or
                not fields or not rows or len(rows)!=table.get("row_count") or
                any(not isinstance(row,dict) or set(row) != set(fields)
                    for row in rows)):
            reasons.append("TABLE_ROWS_OR_FIELDS_INVALID")
        if not isinstance(meta,dict) or meta.get("status") != "OK":
            reasons.append("TABLE_FIELD_METADATA_UNAVAILABLE")
        return {"table_key":key,
                "source_status":"OBSERVED_UNAPPROVED" if not reasons else "NOT_PROVEN",
                "rows":table.get("row_count"),
                "fields":fields if isinstance(fields,list) else [],
                "reason_codes":reasons,
                "source_error":table.get("error")}
    rows = [item(k,record[k]) for k in DIAPHRAGM_TABLES]
    rows += [item(SPECTRUM_MODAL_TABLE,payload.get("spectrum_modal_original_selection")),
             item(SPECTRUM_MODAL_TABLE,payload.get("spectrum_modal_selected_cases"))]
    for j,phase in ((3,"original_selection"),(4,"selected_RSX_RSY")):
        rows[j]["capture_phase"]=phase
    observed=sum(x["source_status"]=="OBSERVED_UNAPPROVED" for x in rows)
    return {**base,
            "status":"SOURCE_CAPTURES_PARTIAL" if observed < 5 else
                     "SOURCE_TABLE_SHAPES_OBSERVED_PENDING_REVIEW",
            "source_success_count":observed,
            "source_expected_count":5,
            "temporary_display_cases":payload.get("temporary_display_cases"),
            "original_display_cases":payload.get("original_display_cases"),
            "tables":rows,
            "note":"Source tables cannot independently prove diaphragm mass, diaphragm constraints or spectrum eccentricity application.",
           }
