"""Replay trusted VS04 receipt + D3 candidate bridge and write D4 source gates.

OFFLINE ONLY. Never opens ETABS, runs analysis, writes existing receipts or
promotes normalized source facts into regulatory PASS.

Run from project root with configured Python path, for example:
python -m tools.audit_vs05_d4_source_authority --receipts-root .receipts \
    --run-id RUN-... --catalog config/dag/tbdy_r1c_94_candidate.json \
    --out .receipts/VS05/VS05_D4_NEW.json
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import re

from tbdy_next.archived_source_bridge import compile_archived_source_candidate
from tbdy_next.compiled_dag import RegulatoryCompiler, read_candidate_catalog
from tbdy_next.reporting import build_complete_report
from tbdy_next.vs05_d4_source_authority import audit_d4_source_authority


def run(*, receipts_root: Path, run_id: str, catalog: Path,
        out: Path) -> dict:
    output = Path(out)
    root = Path(receipts_root)
    if not isinstance(run_id, str) or re.fullmatch(r"RUN-[a-f0-9]{32}", run_id) is None:
        raise ValueError("RUN_ID_NOT_CANONICAL")
    if (output.exists() or output.is_symlink() or
            output.resolve() == root.resolve() or
            output.resolve().is_relative_to((root / run_id).resolve())):
        raise ValueError("OUTPUT_ALREADY_EXISTS_OR_OVERLAPS_RECEIPTS_ROOT")
    # IMPORTANT: verify from original immutable input.source + stage receipts.
    # An exported JSON is not an admissible replacement for this call.
    verified_report = build_complete_report(Path(receipts_root), run_id)
    candidate = compile_archived_source_candidate(
        verified_report, RegulatoryCompiler(read_candidate_catalog(Path(catalog))))
    review = audit_d4_source_authority(verified_report, candidate)
    if review["normative_check_instances_promoted"] != 0:
        raise ValueError("UNAUTHORIZED_NORMATIVE_PROMOTION")
    result = {
        "schema": "tbdy.next.vs05.d4.offline-authority-sidecar.v1",
        "run_id": run_id,
        "review": review,
        "original_vs04_receipts_modified": False,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as writer:
        json.dump(result, writer, ensure_ascii=False, indent=2, sort_keys=True)
        writer.write("\n")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--receipts-root", required=True, type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--catalog", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)
    r = run(receipts_root=a.receipts_root, run_id=a.run_id,
            catalog=a.catalog, out=a.out)
    v = r["review"]
    print("VS05 D4:", v["status"])
    print("Original run:", v["run_id"])
    print("Case count:", v["source_case_catalog"]["case_count"])
    print("Raw combo rows:", v["source_combination_graph"]["raw_row_count"])
    print("Parsed candidate combos:",
          v["source_combination_graph"]["parsed_combination_count"])
    print("Unknown combo refs:",
          v["source_combination_graph"]["unknown_reference_count"])
    print("Mass candidate (ton):",
          v["source_mass_reconciliation"]["candidate_mass_ton"])
    print("Analysis-generation proven: False")
    print("Regulatory checks promoted: 0; release NOT_READY")
    print("Output:", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
