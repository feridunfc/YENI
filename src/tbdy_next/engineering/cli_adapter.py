"""Stable tbdy-next CLI entrypoint for integrated source receipts."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tbdy_next.column_engine.native_archive import decode
from .live_column import review_live_column
from .story_pdelta import review_story_pdelta


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 8_000_000:
        raise ValueError("SOURCE_PATH_MISSING_OR_UNSAFE:" + str(path))
    data = decode(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError("SOURCE_JSON_MUST_BE_OBJECT:" + str(path))
    return data


def _write_new(path: Path, value: dict) -> None:
    if path.is_symlink() or path.exists():
        raise ValueError("RESULT_PATH_EXISTS_NO_OVERWRITE:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(value, out, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
        out.write("\n")


def _load_selection_arg(value: str | None, kind: str) -> dict | None:
    from .rebar_selection import normalize_beam_selection_policy, normalize_column_selection_policy

    if not value:
        return None
    raw = "default" if value.strip().lower() == "default" else _read(Path(value))
    return normalize_beam_selection_policy(raw) if kind == "beam" else normalize_column_selection_policy(raw)


def _run_pipeline_replay(args) -> int:
    from hashlib import sha256
    from tbdy_next.receipts import ReceiptRun
    from .pipeline import EnginePipelineRunner

    raw = args.source.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("source_mode") != "LIVE_ETABS":
        raise ValueError("LIVE_ETABS_ARCHIVED_SOURCE_REQUIRED")
    beam_sel = _load_selection_arg(getattr(args, "beam_selection", None), "beam")
    col_sel = _load_selection_arg(getattr(args, "column_selection", None), "column")
    if beam_sel is not None:
        payload["beam_selection"] = beam_sel
    if col_sel is not None:
        payload["column_selection"] = col_sel
    if beam_sel is not None or col_sel is not None:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    input_sha = sha256(raw).hexdigest()
    run = ReceiptRun(args.out)
    run.archive_input(raw, expected_sha256=input_sha)
    suite = "geometry_capture" in payload or "analysis_sources" in payload
    stages = EnginePipelineRunner().run(payload, case=args.case, run=run, input_sha=input_sha, suite=suite)
    summary = {"run_dir": str(run.root), "input_sha256": input_sha,
               "engine_snapshot": stages["engine_snapshot"],
               "stages_recorded": sorted(path.name for path in run.root.glob("[0-9][0-9]-*.json")),
               "column_gates": (stages["column_gates"] or {}).get("status"),
               "beam_r10": (stages.get("beam_r10") or {}).get("status"),
               "r10_joints": (stages.get("r10_live") or {}).get("joint_end_count"),
               "r08_local_slenderness": (stages.get("r08_local_slenderness") or {}).get("status"),
               "engineering_release": "NOT_READY", "engineering_verdict": "NOT_PROVEN"}
    if args.compare_run is not None:
        from .pipeline_snapshot import compare_runs
        summary["compare"] = compare_runs(args.compare_run, run.root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("compare", {}).get("status", "IDENTICAL") == "IDENTICAL" else 3

def run_cli(args) -> int:
    try:
        if args.action == "pipeline-plan":
            from .pipeline import dag_coverage, stage_registry
            print(json.dumps({"stages": stage_registry(), "dag_coverage": dag_coverage(),
                              "engineering_release": "NOT_READY"}, ensure_ascii=False, indent=2))
            return 0
        if args.action == "run-pipeline":
            return _run_pipeline_replay(args)
        if args.action == "reconcile-live-column":
            receipt = review_live_column(
                live=_read(args.live_receipt), lc_run=_read(args.lc_dl_run),
                combo=_read(args.combo_capture), pmm_run=_read(args.combo_pmm),
                geometry=_read(args.geometry))
            summary = {
                "status": receipt["r07"]["status"],
                "member": receipt["member"],
                "case": receipt["case"],
                "stations": len(receipt["r07"]["stations"]),
                "max_numeric_utilization": receipt["r07"]["maximum_numeric_utilization"],
                "r08": receipt["r08"]["status"],
                "r09": receipt["r09"]["status"],
            }
        elif args.action == "precheck-story-pdelta":
            receipt = review_story_pdelta(_read(args.input))
            summary = {
                "status": receipt["status"],
                "theta_max": receipt["theta_max"],
                "limits": receipt["limit_reference"],
                "global_second_order_proven": False,
            }
        else:
            raise ValueError("UNSUPPORTED_ENGINEERING_CLI_ACTION")
        _write_new(args.out, receipt)
        print(json.dumps({
            **summary, "result_file": str(args.out),
            "result_sha256": receipt["result_sha256"],
            "engineering_release": "NOT_READY", "engineering_verdict": "NOT_PROVEN",
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(json.dumps({
            "status": "BLOCKED_ENGINEERING_SOURCE",
            "reason": type(exc).__name__ + ":" + str(exc),
            "engineering_release": "NOT_READY",
        }, ensure_ascii=False))
        return 2
