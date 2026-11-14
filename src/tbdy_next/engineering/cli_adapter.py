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


def run_cli(args) -> int:
    try:
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
