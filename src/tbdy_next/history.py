"""Read-only, local-only history of verified run receipts.

Finalized runs are projected from sealed results. Legacy runs retain their
original parser and evaluator checks.
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


def _read_finalized_stages(directory: Path, *, input_sha: str) -> dict[str, Any] | None:
    from .engineering.pipeline_snapshot import SCHEMA, STAGE, TERMINAL, read_receipts, read_snapshot

    discovery = _read_receipt(directory, "schema-discovery")
    if discovery is None and any(directory.glob("[0-9][0-9]-schema-discovery.json")):
        raise ValueError("PIPELINE_SCHEMA_DISCOVERY_RECEIPT_INVALID")
    if ((discovery or {}).get("receipt_schema") is None
            and not any(directory.glob(f"[0-9][0-9]-{STAGE}.json"))):
        final_receipt = _read_receipt(directory, TERMINAL)
        if (final_receipt or {}).get("payload", {}).get("engine_snapshot") is None:
            return None
    receipts = read_receipts(directory, input_sha=input_sha)
    snapshot = read_snapshot(directory, input_sha=input_sha, receipts=receipts)
    return snapshot["results"] if snapshot is not None and snapshot["schema"] == SCHEMA else None


def _read_modal_with_stages(directory: Path) -> tuple[dict[str, Any], dict[str, Any] | None] | None:
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
        input_sha = sha256(raw).hexdigest()
        if input_sha != modal.get("input_sha256"):
            return None
        source = json.loads(raw)
        if not isinstance(source, dict):
            return None
        recorded = modal["payload"]
        case = recorded.get("case")
        if not isinstance(case, str) or not case:
            return None
        expected_schema = schema["payload"]
        if expected_schema.get("status") != "SCHEMA_VALID" or expected_schema.get("target_case") != case:
            return None
        stages = _read_finalized_stages(directory, input_sha=input_sha)
        origin = expected_schema.get("source_mode")
        case_count = expected_schema.get("case_row_count")
        raw_count = expected_schema.get("raw_row_count")
        if stages is None:
            table = parse_modal_capture(source, case=case)
            if (evaluate_modal_mass(table).as_dict() != recorded or origin != table.origin
                    or case_count != len(table.rows) or raw_count != table.all_rows_count):
                return None
        elif (stages["result"] != recorded or origin != "LIVE_ETABS" or origin != source.get("source_mode")
              or type(case_count) is not int or type(raw_count) is not int
              or not 0 < case_count <= raw_count or raw_count != source["table"]["row_count"]):
            return None
        meta = source.get("capture_metadata")
        model_name = ntpath.basename(str(meta.get("model_filename", ""))) if isinstance(meta, dict) else ""
        timestamp = modal.get("captured_at_utc")
        if not isinstance(timestamp, str):
            return None
        return {
            "run_id": directory.name,
            "captured_at_utc": timestamp,
            "source_mode": origin,
            "model_name": model_name or None,
            "case": case,
            "raw_row_count": raw_count,
            "case_row_count": case_count,
            "receipt_sha256": modal["receipt_sha256"],
            "input_sha256": modal["input_sha256"],
            "result": recorded,
            "engineering_release": "NOT_READY",
        }, stages
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, SourceError):
        return None


def _read_modal_run(directory: Path) -> dict[str, Any] | None:
    result = _read_modal_with_stages(directory)
    return result[0] if result is not None else None


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
        # The run verifies the selected case. Keep the original column order
        # and all captured rows for inspection.
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


def _quick_view(entry: dict[str, Any], modal: dict[str, Any], stages: dict[str, Any]) -> dict[str, Any]:
    from .check_labels import display_check_group
    from .member_groups import material_member_groups

    geometry = stages["geometry"]
    story_drift = stages["story_drift"]
    return {**entry,
            "geometry": display_check_group(geometry),
            "extra_checks": display_check_group(stages["extra"]), "vs04_schema": stages["vs04"],
            "material_member_groups": material_member_groups(geometry["checks"]),
            "vs04_numerics": stages["vs04_numerics"],
            "vs04_readiness": stages["vs04_readiness"],
            "vs04_pipeline": display_check_group(stages["vs04_pipeline"]),
            **({"story_drift": story_drift} if story_drift is not None else {}),
            "modal": modal["result"],
            "engineering_release": "NOT_READY"}


def quick_history(root: Path, *, limit: int = 15, summary: bool = False) -> list[dict[str, Any]]:
    """Recover only intact quick-suite receipts for locally archived source data."""
    from .quick_checks import evaluate_geometry_capture
    root = Path(root)
    if not root.is_dir():
        return []
    output: list[dict[str, Any]] = []
    for directory in root.glob("RUN-*"):
        found = _read_modal_with_stages(directory)
        if found is None:
            continue
        modal, stages = found
        quick = _read_receipt(directory, "quick-geometry")
        if quick is None or quick.get("input_sha256") != modal["input_sha256"]:
            continue
        entry = {key: modal[key] for key in ("run_id", "captured_at_utc", "source_mode", "model_name", "case")}
        if stages is not None:
            if stages["geometry"] != quick["payload"]:
                continue
            try:
                if summary:
                    member = (stages["column_pmm"] or {}).get("member_id")
                    if isinstance(member, str) and member:
                        entry["pmm_member_id"] = member
                    output.append(entry)
                else:
                    evidence = stages["report_evidence"]
                    output.append(_quick_view(entry, modal, {**stages, "story_drift": evidence.get("story_drift")}))
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
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
        vs04_numerics = None
        vs04_readiness = None
        vs04_pipeline = None
        if "analysis_sources" in source:
            from .analysis_sources import review_analysis_sources
            vs04_receipt = _read_receipt(directory, "vs04-schema")
            if vs04_receipt is None or vs04_receipt.get("input_sha256") != modal["input_sha256"]:
                continue
            vs04 = review_analysis_sources(source["analysis_sources"])
            if vs04 != vs04_receipt["payload"]:
                continue
            vs04_numeric_receipt = _read_receipt(directory, "vs04-numerics")
            if (source["analysis_sources"].get("numeric_stage_required") is True
                    and (vs04_numeric_receipt is None or
                         vs04_numeric_receipt.get("input_sha256") != modal["input_sha256"])):
                continue
            if vs04_numeric_receipt is not None:
                from .analysis_numerics import evaluate_analysis_numerics
                if vs04_numeric_receipt.get("input_sha256") != modal["input_sha256"]:
                    continue
                vs04_numerics = evaluate_analysis_numerics(source["analysis_sources"])
                if vs04_numerics != vs04_numeric_receipt["payload"]:
                    continue
            readiness_receipt = _read_receipt(directory, "vs04-readiness")
            if (source["analysis_sources"].get("readiness_stage_required") is True
                    and (readiness_receipt is None or
                         readiness_receipt.get("input_sha256") != modal["input_sha256"])):
                continue
            if readiness_receipt is not None:
                from .normative_basis import review_normative_readiness
                if readiness_receipt.get("input_sha256") != modal["input_sha256"]:
                    continue
                vs04_readiness = review_normative_readiness(source["analysis_sources"])
                if vs04_readiness != readiness_receipt["payload"]:
                    continue
            pipeline_receipt = _read_receipt(directory, "vs04-pipeline")
            required = source["analysis_sources"].get("pipeline_stage_required") is True
            if required and (pipeline_receipt is None or
                             pipeline_receipt.get("input_sha256") != modal["input_sha256"]):
                continue
            if pipeline_receipt is not None:
                from .live_source_pipeline import evaluate_single_run_source_pipeline
                if pipeline_receipt.get("input_sha256") != modal["input_sha256"]:
                    continue
                vs04_pipeline = evaluate_single_run_source_pipeline(source)
                if (vs04_pipeline != pipeline_receipt["payload"] or
                        vs04_pipeline.get("status") !=
                        "SOURCE_PIPELINE_EVALUATED_PENDING_ENGINEERING_REVIEW"):
                    continue
        story_drift = None
        stage = _read_receipt(directory, "vs05-story-drift")
        if ("vs05_delta_source" in source or
                "vs05_delta_capture_error" in source):
            if stage is None or stage.get("input_sha256") != modal["input_sha256"]:
                continue
            from .story_drift_binding import bind_story_drift
            story_drift = bind_story_drift(
                source.get("vs05_delta_source"),
                capture_error=source.get("vs05_delta_capture_error"))
            if story_drift != stage["payload"]:
                continue
        elif stage is not None:
            continue
        if summary:
            axial = source.get("column_axial")
            request = axial.get("request") if isinstance(axial, dict) else None
            member = request.get("pmm_member") if isinstance(request, dict) else None
            if isinstance(member, str) and member:
                pmm = _read_receipt(directory, "column-pmm")
                if (pmm is not None and pmm.get("input_sha256") == modal["input_sha256"]
                        and pmm["payload"].get("schema") == "tbdy.next.column-pmm-check.v1"
                        and pmm["payload"].get("member_id") == member):
                    entry["pmm_member_id"] = member
            output.append(entry)
            continue
        output.append(_quick_view(entry, modal, {
            "geometry": rechecked, "extra": extra, "vs04": vs04, "vs04_numerics": vs04_numerics,
            "vs04_readiness": vs04_readiness, "vs04_pipeline": vs04_pipeline, "story_drift": story_drift,
        }))
    return sorted(output, key=lambda x: (x["captured_at_utc"], x["run_id"]), reverse=True)[:limit]
