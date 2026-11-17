"""ETABS discovery and explicit modal-table schema boundaries.

Data-contract code here is specific to THIS product. It has no dependency on
TBDY or Column-Engine packages and does not execute ETABS COM calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class SourceError(ValueError):
    """Reject invalid input instead of silently repairing it."""


def artifact_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Mapping[str, Any]:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceError(f"Could not read source JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise SourceError("The source JSON must be an object")
    return result


def review_preflight(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Only says DISCOVERED, never that table columns/results are verified."""
    if payload.get("schema") != "tbdy.next.etabs.readonly.preflight.v1":
        raise SourceError("Unknown preflight schema")
    if payload.get("status") != "DISCOVERY_OK":
        raise SourceError("Preflight discovery failed")
    obs = payload.get("observations")
    if not isinstance(obs, dict):
        raise SourceError("observations eksik")
    tables = obs.get("available_tables", {})
    names = tables.get("tables", [])
    if not isinstance(names, list) or tables.get("status") != "OK" or tables.get("ret_code") != 0:
        raise SourceError("Table inventory failed")
    if tables.get("count") != len(names):
        raise SourceError("Inconsistent table inventory count")
    table_keys = [x.get("key") for x in names if isinstance(x, dict)]
    if len(table_keys) != len(names) or any(not isinstance(x, str) or not x for x in table_keys):
        raise SourceError("Table key is missing")
    if len(table_keys) != len(set(table_keys)):
        raise SourceError("Duplicate table key")
    for key in ("load_cases", "load_combinations"):
        row = obs.get(key, {})
        if row.get("status") != "OK" or row.get("ret_code") != 0:
            raise SourceError(f"{key} listing failed")
        names = row.get("names")
        if not isinstance(names, list) or row.get("count") != len(names):
            raise SourceError(f"{key} count is inconsistent")
        if len(names) != len(set(names)):
            raise SourceError(f"{key} names are duplicated")
    return {
        "stage": "SOURCE_DISCOVERY",
        "status": "DISCOVERED",
        "etabs_version": obs.get("etabs_version", {}).get("raw"),
        "available_table_count": len(table_keys),
        "load_case_count": len(obs["load_cases"]["names"]),
        "load_combination_count": len(obs["load_combinations"]["names"]),
        "modal_table_listed": "Modal Participating Mass Ratios" in table_keys,
        "modal_schema_verified": False,
        "modal_rows_captured": False,
        "analysis_generation_proven": payload.get("analysis_generation_proven") is True,
        "engineering_release": "NOT_READY",
    }


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise SourceError(f"{label} bool olamaz")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise SourceError(f"{label} must be numeric") from exc
    if not number.is_finite():
        raise SourceError(f"{label} must be finite")
    return number


@dataclass(frozen=True, slots=True)
class ModalRow:
    case: str
    mode: int
    ux: Decimal
    uy: Decimal
    sum_ux: Decimal
    sum_uy: Decimal


@dataclass(frozen=True, slots=True)
class ModalTable:
    target_case: str
    origin: str
    rows: tuple[ModalRow, ...]
    all_rows_count: int
    raw_source_identity: str


def parse_modal_capture(payload: Mapping[str, Any], *, case: str) -> ModalTable:
    """Validate full ETABS modal table coverage before numerical evaluation."""
    if payload.get("schema") != "tbdy.next.modal.capture.v1":
        raise SourceError("Invalid modal capture schema version")
    if payload.get("source_mode") not in {"SYNTHETIC", "OFFLINE_ETABS", "LIVE_ETABS"}:
        raise SourceError("Unknown source mode")
    if not isinstance(case, str) or not case.strip():
        raise SourceError("Modal case zorunlu")
    table = payload.get("table")
    if not isinstance(table, dict) or table.get("table_key") != "Modal Participating Mass Ratios":
        raise SourceError("Modal table key does not match")
    fields = table.get("fields")
    rows = table.get("rows")
    if not isinstance(fields, list) or len(fields) != len(set(fields)):
        raise SourceError("Invalid or duplicate table fields")
    expected = {"Case", "Mode", "UX", "UY", "SumUX", "SumUY"}
    if not expected.issubset(set(fields)):
        raise SourceError(f"Eksik modal alanlar: {sorted(expected - set(fields))}")
    if not isinstance(rows, list) or table.get("row_count") != len(rows):
        raise SourceError("Missing or inconsistent table row count")
    if any(not isinstance(row, dict) or set(row) != set(fields) for row in rows):
        raise SourceError("Modal row columns do not match the table schema")
    selected: list[ModalRow] = []
    for row in rows:
        if str(row["Case"]).strip() != case:
            continue
        try:
            mode = int(str(row["Mode"]).strip())
        except ValueError as exc:
            raise SourceError("Mode number must be an integer") from exc
        if str(row["Mode"]).strip() != str(mode):
            raise SourceError("Mode number must use canonical integer notation")
        numbers = [_decimal(row[k], f"Mode {mode}: {k}") for k in ("UX", "UY", "SumUX", "SumUY")]
        if any(value < 0 or value > 1 for value in numbers):
            raise SourceError(f"Mode {mode}: ratio is outside [0, 1]")
        selected.append(ModalRow(case, mode, *numbers))
    if not selected:
        raise SourceError(f"Requested modal case was unavailable: {case}")
    modes = [row.mode for row in selected]
    if modes != list(range(1, len(modes) + 1)):
        raise SourceError("Modes must run from 1 through N in order and without gaps or duplicates")
    cumulative_x = cumulative_y = Decimal("0")
    tolerance = Decimal("0.002")  # ETABS' export rounding; not a code-limit tolerance.
    for row in selected:
        cumulative_x += row.ux
        cumulative_y += row.uy
        if abs(cumulative_x - row.sum_ux) > tolerance or abs(cumulative_y - row.sum_uy) > tolerance:
            raise SourceError(f"Mode {row.mode}: cumulative ratio does not match the running row sum")
    identity = str(payload.get("source_identity", "UNKNOWN"))
    return ModalTable(case, payload["source_mode"], tuple(selected), len(rows), identity)
