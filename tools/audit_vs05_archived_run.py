"""VS05-ARCH-D3: verify an archived VS04 run, derive typed candidate facts/FCR.

No ETABS COM. The original archived receipt chain is independently
re-evaluated with build_complete_report before using its source snapshot.
Write a separate reduced VS05 candidate sidecar; never overwrite
accepted VS04 records, reporting, history or UI source of truth.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.archived_source_bridge import compile_archived_source_candidate
from tbdy_next.compiled_dag import (
    CompilationRejected, RegulatoryCompiler, canonical_json,
    read_candidate_catalog,
)
from tbdy_next.reporting import build_complete_report


def audit_archived_run(
    *, receipts_root: Path, run_id: str, catalog_file: Path, output_file: Path,
) -> dict:
    target = Path(output_file)
    root = Path(receipts_root)
    if (target.exists() or target.is_symlink() or
            target.resolve() == root.resolve() or
            not isinstance(run_id,str) or not run_id.startswith("RUN-")):
        raise CompilationRejected("CANDIDATE_OUTPUT_OR_RUN_ID_INVALID")
    # build_complete_report replays source and every stage receipt. A bare
    # exported JSON file cannot be substituted for this trusted boundary.
    report = build_complete_report(root, run_id)
    catalog = read_candidate_catalog(Path(catalog_file))
    compiler = RegulatoryCompiler(catalog)
    result = compile_archived_source_candidate(report,compiler)
    if result["run_id"] != run_id or result["fcr"]["pass_count"] != 0:
        raise CompilationRejected("RUN_ID_OR_CANDIDATE_AUTHORITY_INVALID")
    reduced = {
        "schema": "tbdy.next.vs05.archived-run-fcr-sidecar.v1",
        "run_id":run_id,
        "accepted_vs04_report_sha256":sha256(canonical_json(report)).hexdigest(),
        "candidate_source_result":result,
        "original_receipts_mutated":False,
        "normative_execution_authorized":False,
        "formal_compliance":"NOT_PROVEN",
        "engineering_release":"NOT_READY",
    }
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as f:
        json.dump(reduced,f,ensure_ascii=False,indent=2,sort_keys=True)
        f.write("\n")
    return reduced


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts-root",type=Path,required=True)
    parser.add_argument("--run-id",type=str,required=True)
    parser.add_argument("--catalog",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args(argv)
    result=audit_archived_run(
        receipts_root=args.receipts_root,run_id=args.run_id,
        catalog_file=args.catalog,output_file=args.out,
    )
    bridge=result["candidate_source_result"]
    print("VS05 D3:",bridge["status"])
    print("Run:",bridge["run_id"])
    print("Frame candidate census:",
          bridge["candidate_physical_summary"]["candidate_structural_frame_count"])
    print("Upper story candidate count:",
          len(bridge["profile_review"]["candidate_upper_story_ids"]))
    print("Unparsed raw combination rows:",
          bridge["candidate_combo_summary"]["raw_combo_definition_row_count"])
    print("Expected CheckInstances:",bridge["fcr"]["expected_count"])
    print("FCR reconciled:",bridge["fcr"]["reconciled_count"])
    print("FCR NOT_PROVEN:",bridge["fcr"]["not_proven_count"])
    print("Normative execution: DENIED; engineering release: NOT_READY")
    print("Output:",args.out.resolve())
    return 0


if __name__=="__main__":
    raise SystemExit(main())
