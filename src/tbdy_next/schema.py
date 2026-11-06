"""VS01-only ETABS modal schema review; never invent field aliases."""
from __future__ import annotations

from typing import Any, Mapping

# Source vocabulary informed by observed ETABS formats and the prior TBDY table
# registry. Proposals are not auto-approved transformations.
MODAL_TABLE_KEY = "Modal Participating Mass Ratios"
REQUIRED_FIELDS = ("Case", "Mode", "UX", "UY", "SumUX", "SumUY")
ALIAS_PROPOSALS = {
    "Case": ("Output Case",),
    "Mode": ("Mode Number",),
    "UX": ("U1",),
    "UY": ("U2",),
    "SumUX": ("Sum UX", "Cumulative UX"),
    "SumUY": ("Sum UY", "Cumulative UY"),
}


def review_modal_schema(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Shape-only diagnostic, not modal engineering qualification."""
    table = payload.get("table")
    if not isinstance(table, dict):
        return {"stage": "MODAL_SCHEMA_DISCOVERY", "status": "SCHEMA_REVIEW_REQUIRED", "reason": "NO_TABLE_OBJECT", "missing_fields": list(REQUIRED_FIELDS), "engineering_release": "NOT_READY"}
    observed = table.get("fields", [])
    if not isinstance(observed, list) or any(not isinstance(f, str) for f in observed):
        observed = []
    missing = [f for f in REQUIRED_FIELDS if f not in observed]
    proposed = {key: [v for v in ALIAS_PROPOSALS[key] if v in observed] for key in missing}
    proposed = {key: vals for key, vals in proposed.items() if vals}
    complete = (table.get("table_key") == MODAL_TABLE_KEY and not missing and len(set(observed)) == len(observed))
    return {
        "stage": "MODAL_SCHEMA_DISCOVERY",
        "status": "SCHEMA_FIELDS_PRESENT" if complete else "SCHEMA_REVIEW_REQUIRED",
        "table_key": table.get("table_key"),
        "required_fields": list(REQUIRED_FIELDS),
        "observed_fields": list(observed),
        "missing_fields": missing,
        "additional_fields": [x for x in observed if x not in REQUIRED_FIELDS],
        "alias_candidates_not_approved": proposed,
        "reported_row_count": table.get("row_count"),
        "engineering_release": "NOT_READY",
        "note": "Matching fields does not verify the rows; aliases require a targeted ETABS review",
    }
