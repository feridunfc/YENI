"""Replay B2 from an existing run; no COM, new capture, or receipt mutation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tbdy_next.history import quick_history
from tbdy_next.reporting import build_complete_report, build_printable_html


def verify(root: Path, run_id: str, *, export_dir: Path | None = None) -> dict:
    report = build_complete_report(root, run_id)
    b2 = report.get("soft_story_b2")
    if not isinstance(b2, dict):
        raise ValueError("B2_ARCHIVED_SOURCE_NOT_ATTEMPTED")
    coverage = b2["comparison_coverage"]
    sources = b2["source_coverage"]
    if b2["coverage_known"]:
        n = len(b2["stories"])
        if (b2["declared_story_count"] != n + len(b2.get("excluded_stories", []))
                or sources["expected"] != 2 * n
                or sum(sources[k] for k in ("resolved", "missing", "invalid")) != 2 * n
                or coverage["expected"] != 4 * max(n - 1, 0)
                or coverage["resolved"] + coverage["unresolved"] != coverage["expected"]
                or len(b2["items"]) != coverage["expected"]):
            raise ValueError("B2_SOURCE_OR_COMPARISON_ACCOUNTING_CONFLICT")
    if (b2["formal_compliance"] != "NOT_PROVEN"
            or b2["normative_b2_classification"] != "NOT_PROVEN"
            or b2["engineering_release"] != "NOT_READY"
            or b2["numerical_pass_issued"] is not False
            or sum(e["check_id"] == "SOFT_STORY_B2" for e in report["check_inventory"]["entries"]) != 1):
        raise ValueError("B2_AUTHORITY_OR_INVENTORY_CONFLICT")
    html = build_printable_html(report)
    if "B2 yumuşak kat" not in html or b2["result_sha256"] not in html:
        raise ValueError("B2_HTML_RESULT_MISSING")
    if export_dir is not None:
        export_dir.mkdir(parents=True, exist_ok=True)
        stem = "TBDY_NEXT_" + run_id + "_B2_all_checks"
        (export_dir / (stem + ".json")).write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
        (export_dir / (stem + ".html")).write_text(html, encoding="utf-8")
    return {
        "replay_status": "B2_ARCHIVED_REPLAY_ACCOUNTING_VERIFIED",
        "run_id": run_id, "model": report["model"],
        "source_mode": report["source_mode"],
        "b2_source_status": b2["status"],
        "numeric_condition": b2["numeric_condition"],
        "source_coverage": sources, "comparison_coverage": coverage,
        "source_coverage_status": b2.get("source_coverage_status", "UNKNOWN"),
        "defined_story_count": b2.get("declared_story_count"),
        "physical_story_count": (b2.get("physical_story_scope") or {}).get("physical_story_count"),
        "excluded_stories": b2.get("excluded_stories", []),
        "physical_scope_reason_codes": (b2.get("physical_story_scope") or {}).get("reason_codes", []),
        "threshold_exceeded_comparisons": b2["threshold_exceeded_comparisons"],
        "source_payload_sha256": b2["source_payload_sha256"],
        "result_sha256": b2["result_sha256"],
        "reason_codes": b2["reason_codes"],
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(".receipts"))
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--run-id")
    selection.add_argument("--latest", action="store_true",
                           help="Latest verified local run that attempted the existing drift capture")
    parser.add_argument("--export-dir", type=Path)
    args = parser.parse_args()
    run_id = args.run_id
    if args.latest:
        eligible = [r for r in quick_history(args.root) if "story_drift" in r]
        if not eligible:
            parser.error("No verified archived run with a drift capture; choose the existing receipt root.")
        run_id = eligible[0]["run_id"]
    result = verify(args.root, run_id, export_dir=args.export_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
