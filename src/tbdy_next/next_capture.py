"""VS03: narrow ETABS data acquisition for used-concrete fck and story A1 ratios.

One existing COM session; no save, analysis, units changes or design writes.
The RSX/RSY display case selection is reversible and checked before/after.
"""
from __future__ import annotations

from typing import Any

from .etabs_geometry import _metadata, _read_one
from .etabs_modal import ModalCaptureError, _selected_cases, _set_cases

MATERIAL_TABLE = "Material Properties - Concrete Data"
A1_TABLE = "Story Max Over Avg Drifts"


def _safe_source_table(db: Any, name: str) -> dict:
    # Failure of a *new* VS03 source must not erase the already-working VS01/02
    # numerical results. Keep the failed source and its diagnostics as NO_DATA.
    try:
        record = _read_one(db, name)
        record["field_metadata"] = _metadata(db, name)
        return record
    except Exception as exc:
        return {"status": "CAPTURE_ERROR", "table_key": name,
                "fields": [], "rows": [], "row_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
                "field_metadata": {"status": "METADATA_UNAVAILABLE"}}


def capture_next_facts(sap: Any, *, x_case: str = "RSX", y_case: str = "RSY") -> dict:
    if (not isinstance(x_case, str) or not isinstance(y_case, str)
            or not x_case.strip() or not y_case.strip() or x_case == y_case
            or x_case != x_case.strip() or y_case != y_case.strip()):
        raise ModalCaptureError("Exact distinct X and Y load-case names required")
    db = sap.DatabaseTables
    before_units = sap.GetPresentUnits()
    # Material definitions are independent from selected output cases.
    material = _safe_source_table(db, MATERIAL_TABLE)
    original = _selected_cases(db)
    wanted = (x_case, y_case)
    changed = original != wanted
    a1 = None
    try:
        if changed:
            # Mark the transaction as mutated before calling a setter because
            # a failed setter could still change the ETABS UI selection.
            _set_cases(db, wanted)
            if _selected_cases(db) != wanted:
                raise ModalCaptureError("A1 display-case selection mismatch")
        a1 = _safe_source_table(db, A1_TABLE)
    finally:
        if changed:
            try:
                _set_cases(db, original)
                if _selected_cases(db) != original:
                    raise ModalCaptureError("A1 display selection restore mismatch")
            except Exception as exc:
                raise ModalCaptureError(f"A1 display selection restore failed: {exc}") from exc
    after_units = sap.GetPresentUnits()
    return {
        "schema": "tbdy.next.vs03.capture.v1",
        "material_table": material, "a1_table": a1,
        "x_case": x_case, "y_case": y_case,
        "case_selection_restored": True,
        "units_before": before_units if type(before_units) is int else None,
        "units_after": after_units if type(after_units) is int else None,
    }
