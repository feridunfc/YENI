"""Read-only, local-only presentation of existing CLI/modal VS01 receipts.

No ETABS connection and no second engineering calculator. Stored inputs are
revalidated with the same parser/evaluator used for the original VS01 run.
"""
from __future__ import annotations

import json
import ntpath
from hashlib import sha256
from pathlib import Path
import re
from typing import Any

from .modal import evaluate_modal_mass
from .receipts import canonical_bytes
from .source import SourceError, parse_modal_capture

_RUN = re.compile(r"RUN-[0-9a-f]{32}\Z")
_MAX_SOURCE_BYTES = 32 * 1024 * 1024


def _read_receipt(directory: Path, stage: str) -> dict[str, Any] | None:
    paths = sorted(directory.glob(f"[0-9][0-9]-{stage}.json"))
    if len(paths) != 1 or paths[0].is_symlink():
        return None
    try:
        record = json.loads(paths[0].read_text(encoding="utf-8"))
        if not isinstance(record, dict) or record.get("stage") != stage:
            return None
        actual_hash = record.get("receipt_sha256")
        if not isinstance(actual_hash, str):
            return None
        unsigned = {key: value for key, value in record.items() if key != "receipt_sha256"}
        if sha256(canonical_bytes(unsigned)).hexdigest() != actual_hash:
            return None
        if record.get("run_id") != directory.name:
            return None
        if not isinstance(record.get("payload"), dict):
            return None
        return record
    except (OSError, ValueError, TypeError):
        return None


def _read_modal_run(directory: Path) -> dict[str, Any] | None:
    if not directory.is_dir() or directory.is_symlink() or not _RUN.fullmatch(directory.name):
        return None
    modal = _read_receipt(directory, "modal")
    schema = _read_receipt(directory, "schema")
    if modal is None or schema is None:
        return None
    if modal.get("input_sha256") != schema.get("input_sha256"):
        return None
    source_file = directory / "input.source"
    try:
        if source_file.is_symlink() or not source_file.is_file() or source_file.stat().st_size > _MAX_SOURCE_BYTES:
            return None
        raw = source_file.read_bytes()
        if sha256(raw).hexdigest() != modal.get("input_sha256"):
            return None
        source = json.loads(raw)
        if not isinstance(source, dict):
            return None
        recorded = modal["payload"]
        case = recorded.get("case")
        if not isinstance(case, str) or not case:
            return None
        table = parse_modal_capture(source, case=case)
        recalculated = evaluate_modal_mass(table).as_dict()
        if recalculated != recorded:
            return None
        expected_schema = schema["payload"]
        if (expected_schema.get("status") != "SCHEMA_VALID"
                or expected_schema.get("target_case") != case
                or expected_schema.get("case_row_count") != len(table.rows)
                or expected_schema.get("raw_row_count") != table.all_rows_count
                or expected_schema.get("source_mode") != table.origin):
            return None
        meta = source.get("capture_metadata")
        model_name = ntpath.basename(str(meta.get("model_filename", ""))) if isinstance(meta, dict) else ""
        timestamp = modal.get("captured_at_utc")
        if not isinstance(timestamp, str):
            return None
        return {
            "run_id": directory.name,
            "captured_at_utc": timestamp,
            "source_mode": table.origin,
            "model_name": model_name or None,
            "case": case,
            "raw_row_count": table.all_rows_count,
            "case_row_count": len(table.rows),
            "receipt_sha256": modal["receipt_sha256"],
            "input_sha256": modal["input_sha256"],
            "result": recalculated,
            "engineering_release": "NOT_READY",
        }
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, SourceError):
        return None


def modal_history(root: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    """Return recent verified stage receipts; never return full ETABS rows."""
    if limit < 1 or limit > 100:
        raise ValueError("limit must be 1..100")
    root = Path(root)
    if not root.is_dir():
        return []
    results = []
    for path in root.glob("RUN-*"):
        entry = _read_modal_run(path)
        if entry is not None:
            results.append(entry)
    results.sort(key=lambda x: (x["captured_at_utc"], x["run_id"]), reverse=True)
    return results[:limit]


def modal_source_table(root: Path, run_id: str) -> dict[str, Any] | None:
    """Show all stored source rows for one verified run, not a truncated preview.

    The archived input, modal receipt and schema receipt must still agree.
    This function is presentation-only and never computes a second verdict.
    """
    if not isinstance(run_id, str) or _RUN.fullmatch(run_id) is None:
        return None
    directory = Path(root) / run_id
    entry = _read_modal_run(directory)
    if entry is None:
        return None
    try:
        source_file = directory / "input.source"
        if source_file.is_symlink() or source_file.stat().st_size > _MAX_SOURCE_BYTES:
            return None
        raw = source_file.read_bytes()
        if sha256(raw).hexdigest() != entry["input_sha256"]:
            return None
        source = json.loads(raw)
        table = source["table"]
        fields = table["fields"]
        rows = table["rows"]
        # parse_modal_capture has checked the selected case and row shape; retain
        # the original column ordering and *all* captured rows for inspection.
        if (not isinstance(fields, list) or not isinstance(rows, list)
                or table["row_count"] != len(rows)
                or any(not isinstance(row, dict) or set(row) != set(fields) for row in rows)):
            return None
        return {
            "run_id": run_id,
            "table_key": table["table_key"],
            "case": entry["case"],
            "model_name": entry["model_name"],
            "source_mode": entry["source_mode"],
            "fields": fields,
            "rows": rows,
            "row_count": len(rows),
            "case_row_count": entry["case_row_count"],
            "input_sha256": entry["input_sha256"],
            "engineering_release": "NOT_READY",
        }
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return None


def quick_history(root: Path, *, limit: int = 15) -> list[dict[str, Any]]:
    """Recover only intact quick-suite receipts for locally archived source data."""
    from .quick_checks import evaluate_geometry_capture
    root = Path(root)
    if not root.is_dir():
        return []
    output: list[dict[str, Any]] = []
    for directory in root.glob("RUN-*"):
        modal = _read_modal_run(directory)
        quick = _read_receipt(directory, "quick-geometry")
        if modal is None or quick is None or quick.get("input_sha256") != modal["input_sha256"]:
            continue
        try:
            source = json.loads((directory / "input.source").read_text(encoding="utf-8"))
            geometry = source.get("geometry_capture")
            if geometry is None:
                continue
            rechecked = evaluate_geometry_capture(geometry)
            if rechecked != quick["payload"]:
                continue
        except (OSError, UnicodeError, ValueError, TypeError, KeyError):
            continue
        extra = None
        if "next_capture" in source:
            from .next_checks import evaluate_next_capture
            extra_receipt = _read_receipt(directory, "quick-extra")
            if extra_receipt is None or extra_receipt.get("input_sha256") != modal["input_sha256"]:
                continue
            extra = evaluate_next_capture(source["next_capture"], source.get("geometry_capture"))
            if extra != extra_receipt["payload"]:
                continue
        vs04 = None
        if "analysis_sources" in source:
            from .analysis_sources import review_analysis_sources
            vs04_receipt = _read_receipt(directory, "vs04-schema")
            if vs04_receipt is None or vs04_receipt.get("input_sha256") != modal["input_sha256"]:
                continue
            vs04 = review_analysis_sources(source["analysis_sources"])
            if vs04 != vs04_receipt["payload"]:
                continue
        output.append({"run_id": directory.name, "captured_at_utc": modal["captured_at_utc"],
                       "source_mode": modal["source_mode"], "model_name": modal["model_name"],
                       "geometry": rechecked, "extra_checks": extra, "vs04_schema": vs04,
                       "modal": modal["result"],
                       "engineering_release": "NOT_READY"})
    return sorted(output, key=lambda x: (x["captured_at_utc"], x["run_id"]), reverse=True)[:limit]
