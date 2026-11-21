#!/usr/bin/env python3
"""Reproduce YSA-03 using YENI's actual receipt writer and readers.

This is a bounded audit diagnostic, not a structural model or building fixture.
All test receipts are created in a TemporaryDirectory and removed on exit. The
selected repository is imported read-only. Only the explicitly requested JSON
output is retained.

Example (from a YENI checkout):
    python -B docs/supervisor/audit_20261121/reproduce_receipt_index.py \
        --repo . --output /tmp/yeni_receipt_index_probe.json

Exit codes:
    0: the baseline defect is reproduced (100 written, 99 read).
    1: behavior differs from that defect; inspect the recorded result (a corrected
       implementation is expected to load all 100 records).
    2: invalid repository/import or diagnostic execution failure.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory

BASELINE_COMMIT = "c71a4dda4ab9453f428a38b3ed79931f8e6eeea3"
BASELINE_SOURCE_HASHES = {
    "src/tbdy_next/receipts.py":
        "b413cb3ebb3d70e48fb7c7731c942777e90a3b877445b410d3d845723f52b653",
    "src/tbdy_next/history.py":
        "b88e933ec29044ea4f6d9cd7012b22d25305fdeb2f53796043859180355f028b",
    "src/tbdy_next/engineering/pipeline_snapshot.py":
        "12ed0f6b4ac939430f703c4942a5a95ba0de8e5684a86b51b0ff75562b819f21",
}
EXPECTED_DEFECT = {
    "written_receipts": 100,
    "read_receipts": 99,
    "hundredth_file_exists": True,
    "hundredth_record_loaded": False,
    "history_hundredth_record_loaded": False,
}


def _git(repo: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *arguments], check=False,
            text=True, capture_output=True,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True,
                        help="YENI checkout to inspect; production files are not modified")
    parser.add_argument("--output", type=Path, required=True,
                        help="Path for the diagnostic JSON result")
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    output = args.output.expanduser().resolve()
    package = repo / "src" / "tbdy_next"
    if not (package / "__init__.py").is_file():
        parser.error("--repo does not contain src/tbdy_next/__init__.py")
    if output.is_relative_to(package):
        parser.error("--output must not write into the production package")
    if output == Path(__file__).resolve():
        parser.error("--output must not overwrite the diagnostic script")
    sources = {relative: repo / relative for relative in BASELINE_SOURCE_HASHES}
    if not all(path.is_file() for path in sources.values()):
        parser.error("--repo does not contain the required receipt source files")
    if output in {path.resolve() for path in sources.values()}:
        parser.error("--output must not overwrite a source file")
    hashes = {relative: sha256(path.read_bytes()).hexdigest()
              for relative, path in sources.items()}
    result = {
        "diagnostic_id": "YSA-03-RECEIPT-INDEX-BOUNDARY",
        "diagnostic_script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "API receipt-index diagnostic; no structural model, ETABS or engineering calculation",
        "baseline_commit": BASELINE_COMMIT,
        "inspected_commit": _git(repo, "rev-parse", "HEAD"),
        "baseline_source_hashes": BASELINE_SOURCE_HASHES,
        "inspected_source_hashes": hashes,
        "baseline_source_hashes_match": hashes == BASELINE_SOURCE_HASHES,
        "environment": {"platform": platform.system(), "python_version": platform.python_version()},
        "expected_defect": EXPECTED_DEFECT,
        "production_files_modified": False,
        "temporary_receipts_retained": False,
    }
    exit_code = 2
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(repo / "src"))
        import tbdy_next.receipts as receipt_module
        import tbdy_next.history as history_module
        import tbdy_next.engineering.pipeline_snapshot as snapshot_module
        for module in (receipt_module, history_module, snapshot_module):
            location = Path(module.__file__).resolve()
            if not location.is_relative_to(package):
                raise RuntimeError("Imported module is outside the selected repository: " + module.__name__)
        with TemporaryDirectory(prefix="yeni-receipt-index-audit-") as temporary:
            run = receipt_module.ReceiptRun(Path(temporary))
            raw = b"{}"
            input_sha = sha256(raw).hexdigest()
            run.archive_input(raw, expected_sha256=input_sha)
            paths = [run.record("probe-" + str(index), {"index": index}, input_sha256=input_sha)
                     for index in range(1, 101)]
            loaded = snapshot_module.read_receipts(run.root, input_sha=input_sha)
            hundredth = history_module._read_receipt(run.root, "probe-100")
            observed = {
                "written_receipts": sum(path.is_file() for path in paths),
                "read_receipts": len(loaded),
                "hundredth_file_exists": paths[-1].is_file(),
                "hundredth_record_loaded": "probe-100" in loaded,
                "history_hundredth_record_loaded": hundredth is not None,
            }
            result["observed"] = observed
            result["hundredth_filename"] = paths[-1].name
        matches = observed == EXPECTED_DEFECT
        result["baseline_defect_reproduced"] = matches
        result["status"] = "BASELINE_DEFECT_REPRODUCED" if matches else "BEHAVIOR_DIFFERS_FROM_BASELINE_DEFECT"
        result["interpretation"] = (
            "Exactly two-digit reader globs omit the writer's 100th receipt. "
            "The current recorded 16-receipt C29 run is outside this failing boundary."
            if matches else
            "The baseline 100-written/99-read behavior was not reproduced. "
            "A corrected implementation should read all 100 receipts; inspect observed values and source hashes."
        )
        exit_code = 0 if matches else 1
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_ERROR"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    after = {relative: sha256(path.read_bytes()).hexdigest()
             for relative, path in sources.items()}
    if after != hashes:
        result["status"] = "SOURCE_CHANGED_DURING_DIAGNOSTIC"
        result["source_hashes_after"] = after
        exit_code = 2
    result["exit_code"] = exit_code
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(output),
                      "observed": result.get("observed"), "exit_code": exit_code}, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
