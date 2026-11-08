"""One CLI, two bounded commands; output receipts locally, never to GitHub."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .source import SourceError, artifact_sha256, parse_modal_capture, read_json, review_preflight
from .modal import evaluate_modal_mass
from .receipts import ReceiptRun


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TBDY Next Engine — verified small vertical slices")
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("inspect-preflight", "check-modal"):
        command = actions.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        if name == "check-modal":
            command.add_argument("--case", required=True)
    service = actions.add_parser("serve", help="Local web UI for one implemented vertical slice")
    service.add_argument("--host", default="127.0.0.1")
    service.add_argument("--port", type=int, default=8765)
    service.add_argument("--out", type=Path, default=Path(".receipts"))
    columns = actions.add_parser("import-column-bank", help="Verify an offline native column ZIP; no ETABS call")
    columns.add_argument("--input", type=Path, required=True)
    columns.add_argument("--historical-db", type=Path)
    columns.add_argument("--out", type=Path, default=Path(".receipts"))
    demands = actions.add_parser("inspect-column-demands", help="Derive CE-02 from an existing bank without copying its ZIP/SQLite")
    demands.add_argument("--run-id", required=True)
    demands.add_argument("--out", type=Path, default=Path(".receipts"))
    args = parser.parse_args(argv)
    if args.action == "serve":
        from .web import serve
        serve(host=args.host, port=args.port, output_root=args.out)
        return 0
    if args.action == "inspect-column-demands":
        import sqlite3
        from .column_engine.store import read_column_bank
        try:
            chain = read_column_bank(args.out, args.run_id)["demand_chain"]
            result = {k: chain[k] for k in ("source_run_id", "source_archive_sha256", "result_sha256",
                "classification_counts", "static_candidate_count", "formal_compliance", "engineering_release")}
            result["design_summary"] = {k: chain["design_summary"][k] for k in (
                "status", "row_count", "reference_count", "known_combination_references", "unique_static_links", "link_status_counts")}
        except (OSError, EOFError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            print(json.dumps({"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}, ensure_ascii=False))
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.action == "import-column-bank":
        import sqlite3
        from zipfile import BadZipFile
        from .column_engine.store import save_column_bank
        try:
            result = save_column_bank(args.input, args.out, historical_db=args.historical_db)
        except (OSError, EOFError, ValueError, KeyError, TypeError, BadZipFile, sqlite3.Error) as exc:
            print(json.dumps({"status": "REJECTED", "reason": str(exc),
                              "engineering_release": "NOT_READY"}, ensure_ascii=False))
            return 2
        summary = {k: result[k] for k in ("run_id", "source_kind", "selected_column_count",
            "observed_column_count", "force_row_count", "recorded_output_count", "formal_compliance", "engineering_release")}
        summary["static_replay_scalar_comparisons"] = result["static_replay"]["scalar_comparisons"]
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    source_sha = artifact_sha256(args.input)
    run = ReceiptRun(args.out)
    try:
        run.archive_input(args.input.read_bytes(), expected_sha256=source_sha)
        payload = read_json(args.input)
        if args.action == "inspect-preflight":
            result = review_preflight(payload)
            run.record("discovery", result, input_sha256=source_sha)
        else:
            table = parse_modal_capture(payload, case=args.case)
            run.record("schema", {
                "status": "SCHEMA_VALID",
                "table": "Modal Participating Mass Ratios",
                "target_case": table.target_case,
                "case_row_count": len(table.rows),
                "raw_row_count": table.all_rows_count,
                "source_mode": table.origin,
                "engineering_release": "NOT_READY",
            }, input_sha256=source_sha)
            result = evaluate_modal_mass(table).as_dict()
            run.record("modal", result, input_sha256=source_sha)
    except (SourceError, ValueError, KeyError) as exc:
        result = {"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}
        run.record("rejected", result, input_sha256=source_sha)
        print(json.dumps({"run_dir": str(run.root), **result}, ensure_ascii=False))
        return 2
    print(json.dumps({"run_dir": str(run.root), **result}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
