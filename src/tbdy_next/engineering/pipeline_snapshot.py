"""Persist and verify the outputs of one pipeline run without evaluating them."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import platform
from typing import Any, Mapping

from ..archive_blobs import archive_bytes, copy_archive
from ..history import _MAX_SOURCE_BYTES, _read_receipt_file
from ..receipts import ReceiptRun, receipt_paths

STAGE = "engine-results"
LEGACY_SCHEMA = "tbdy.next.pipeline-stage-snapshot.v1"
EVIDENCE_SCHEMA = "tbdy.next.pipeline-stage-snapshot.v2"
SCHEMA = "tbdy.next.pipeline-stage-snapshot.v3"
SEALED_SCHEMAS = (EVIDENCE_SCHEMA, SCHEMA)
TERMINAL = "live-capture"
_LEGACY_KEYS = frozenset((
    "result", "geometry", "extra", "vs04", "vs04_numerics", "vs04_readiness",
    "vs04_pipeline", "story_drift", "analysis_setup", "analysis_setup_reconciliation",
    "column_axial", "column_pmm", "column_gates", "beam_r10", "r10_live",
    "r08_second_order", "r08_local_slenderness", "r14_closure",
))
_EVIDENCE_KEYS = _LEGACY_KEYS | {"report_evidence"}
REQUIRED_KEYS = _EVIDENCE_KEYS | {"building_design"}


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def method_fingerprint() -> dict[str, Any]:
    """Content, not mtime/path: moving an identical checkout preserves identity."""
    package = Path(__file__).resolve().parents[1]
    files = {str(p.relative_to(package)): sha256(p.read_bytes()).hexdigest()
             for p in sorted(package.rglob("*.py"))}
    config = package.parent.parent / "config"
    configs = {"repository/" + str(p.relative_to(config)): sha256(p.read_bytes()).hexdigest()
               for p in sorted(config.rglob("*")) if p.is_file()
               and p.suffix.lower() in (".json", ".yaml", ".yml")}
    internal_config = package / "config"
    configs.update({"package/" + str(p.relative_to(internal_config)): sha256(p.read_bytes()).hexdigest()
                    for p in sorted(internal_config.rglob("*")) if p.is_file()
                    and p.suffix.lower() in (".json", ".yaml", ".yml")})
    return {"python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "package_sha256": _digest(files), "configuration_sha256": _digest(configs),
            "file_count": len(files), "configuration_file_count": len(configs)}


def read_receipts(directory: Path, *, input_sha: str) -> dict[str, dict[str, Any]]:
    """Read the exact on-disk stage inventory, with source and receipt hashes checked."""
    records = {}
    for path in receipt_paths(directory):
        stage = path.stem.split("-", 1)[1]
        record = _read_receipt_file(path, stage)
        if record is None or record.get("input_sha256") != input_sha or stage in records:
            raise ValueError("PIPELINE_STAGE_RECEIPT_INVALID:" + stage)
        records[stage] = record
    return records


def _stage_inventory(records: Mapping[str, Mapping[str, Any]]) -> list[dict[str, str]]:
    return [{"stage": stage, "payload_sha256": _digest(record["payload"])}
            for stage, record in records.items() if stage not in (STAGE, TERMINAL)]


def record_snapshot(run: ReceiptRun, *, input_sha: str, results: Mapping[str, Any],
                    registry: list[dict[str, Any]]) -> dict[str, str]:
    if set(results) != REQUIRED_KEYS or not isinstance(results["report_evidence"], Mapping):
        raise ValueError("PIPELINE_SNAPSHOT_RESULT_KEYS_INCOMPLETE")
    receipts = read_receipts(run.root, input_sha=input_sha)
    if not receipts or STAGE in receipts or TERMINAL in receipts:
        raise ValueError("PIPELINE_UNEXPECTED_STAGE_INVENTORY")
    snapshot = {"schema": SCHEMA, "input_sha256": input_sha,
                "method": method_fingerprint(), "stage_plan_sha256": _digest(registry),
                "results_sha256": _digest(results), "results": dict(results),
                "stage_inventory": _stage_inventory(receipts),
                "engineering_release": "NOT_READY", "formal_compliance": "NOT_PROVEN",
                "scope": "PIPELINE_RESULTS_AND_REPORT_EVIDENCE"}
    snapshot_sha = _digest(snapshot)
    run.record(STAGE, snapshot, input_sha256=input_sha)
    return {"schema": SCHEMA, "snapshot_sha256": snapshot_sha,
            "results_sha256": snapshot["results_sha256"]}


def read_snapshot(directory: Path, *, input_sha: str,
                  receipts: Mapping[str, Mapping[str, Any]] | None = None, on_verified_source=None) -> dict[str, Any] | None:
    records = receipts if receipts is not None else read_receipts(Path(directory), input_sha=input_sha)
    record = records.get(STAGE)
    link = (records.get(TERMINAL) or {}).get("payload", {}).get("engine_snapshot")
    declared_schema = (records.get("schema-discovery") or {}).get("receipt_schema")
    if record is None:
        if link is not None or declared_schema is not None:
            raise ValueError("PIPELINE_REQUIRED_SNAPSHOT_MISSING")
        return None
    value = record["payload"]
    results = value.get("results")
    schema = value.get("schema")
    required = {LEGACY_SCHEMA: _LEGACY_KEYS, EVIDENCE_SCHEMA: _EVIDENCE_KEYS, SCHEMA: REQUIRED_KEYS}.get(schema, ())
    if (record.get("input_sha256") != input_sha or value.get("input_sha256") != input_sha
            or schema not in (LEGACY_SCHEMA, *SEALED_SCHEMAS) or not isinstance(results, Mapping)
            or set(results) != required
            or value.get("results_sha256") != _digest(results)):
        raise ValueError("PIPELINE_SNAPSHOT_SOURCE_OR_RESULTS_INVALID")
    if schema in SEALED_SCHEMAS:
        from ..column_engine.native_archive import decode
        from .design_scenario import verify_archived_scenario

        source = directory / "input.source"
        if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= _MAX_SOURCE_BYTES:
            raise ValueError("PIPELINE_SOURCE_MISSING_OR_UNSAFE")
        raw = archive_bytes(source)
        if sha256(raw).hexdigest() != input_sha:
            raise ValueError("PIPELINE_SOURCE_HASH_MISMATCH")
        source_payload = decode(raw)
        if not isinstance(source_payload, Mapping):
            raise ValueError("PIPELINE_SOURCE_NOT_OBJECT")
        scenario = verify_archived_scenario(directory, source_payload)
        if scenario != results["report_evidence"].get("design_scenario"):
            raise ValueError("PIPELINE_SCENARIO_SNAPSHOT_MISMATCH")
        expected_link = {"schema": schema, "snapshot_sha256": _digest(value),
                         "results_sha256": value["results_sha256"]}
        if (declared_schema != schema or link != expected_link
                or list(records)[-2:] != [STAGE, TERMINAL]):
            raise ValueError("PIPELINE_FINALIZATION_MISSING_OR_INVALID")
        if (not isinstance(results["report_evidence"], Mapping)
                or not value.get("stage_inventory") or value["stage_inventory"] != _stage_inventory(records)):
            raise ValueError("PIPELINE_STAGE_INVENTORY_MISMATCH")
        if schema == SCHEMA:
            building = results["building_design"]
            pointer = records.get("building-design")
            if "building_design" in results["report_evidence"] or (building is None) != (pointer is None):
                raise ValueError("BUILDING_STAGE_OWNERSHIP_MISMATCH")
            if building is not None and pointer["payload"].get("results_sha256") != _digest(building):
                raise ValueError("BUILDING_STAGE_HASH_MISMATCH")
        if on_verified_source is not None:
            on_verified_source(source_payload)
    elif link is not None or declared_schema is not None:
        raise ValueError("PIPELINE_FINALIZATION_SCHEMA_MISMATCH")
    return value


def compare_runs(reference: Path, current: Path) -> dict[str, Any]:
    """Verify every receipt and source; never claim identity for legacy partial coverage."""
    def read_all(root: Path) -> tuple[dict[str, Any], str, bool]:
        root = Path(root)
        source = root / "input.source"
        if source.is_symlink() or not source.is_file():
            raise ValueError("REPLAY_SOURCE_MISSING_OR_UNSAFE")
        input_sha = copy_archive(source)
        records = read_receipts(root, input_sha=input_sha)
        if not records:
            raise ValueError("REPLAY_NO_RECEIPTS")
        snapshot = read_snapshot(root, input_sha=input_sha, receipts=records)
        return ({stage: record["payload"] for stage, record in records.items()}, input_sha,
                bool(snapshot and snapshot.get("schema") in SEALED_SCHEMAS))
    old, old_sha, old_complete = read_all(reference)
    new, new_sha, new_complete = read_all(current)
    common = set(old) & set(new)
    changed = sorted(k for k in common if old[k] != new[k])
    missing, extra = sorted(set(old) - set(new)), sorted(set(new) - set(old))
    complete = old_complete and new_complete
    same = not changed and not missing and not extra and old_sha == new_sha
    return {"reference_stages": len(old), "current_stages": len(new),
            "mismatched_stages": changed, "missing_stages": missing, "extra_stages": extra,
            "source_identical": old_sha == new_sha, "sealed_stage_coverage": complete,
            "comparison_scope": "PIPELINE_RESULTS_REPORT_EVIDENCE_AND_ALL_RECORDED_RECEIPTS",
            "status": ("IDENTICAL" if same else "DIFFERENT") if complete
                      else "LEGACY_PARTIAL_COMPARISON"}
