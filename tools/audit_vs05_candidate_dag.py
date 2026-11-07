"""VS05 candidate-only DAG / FCR acceptance replay (offline, no ETABS).

Example:
 python tools/audit_vs05_candidate_dag.py \
   --catalog config/dag/tbdy_r1c_94_candidate.json \
   --plan-input tests/fixtures/vs05_candidate_plan_input.json \
   --out .receipts/VS05/CANDIDATE_DAG_FCR.json

Never promotes candidate nodes or untrusted self-declared approvals to
executable code checks. Deliberately separate from the live web route.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.compiled_dag import (
    CompilationRejected,
    RegulatoryCompiler,
    assess_candidate_plan,
    read_candidate_catalog,
)

MAX_MANIFEST_BYTES = 512 * 1024


def _manifest(path: Path) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise CompilationRejected("PLAN_INPUT_INVALID_OR_TOO_LARGE")
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise CompilationRejected("PLAN_INPUT_NOT_VALID_UTF8_JSON") from exc
    if (not isinstance(obj, dict) or obj.get("schema") !=
            "tbdy.next.vs05.candidate-plan-input.v1"):
        raise CompilationRejected("PLAN_INPUT_SCHEMA_INVALID")
    if obj.get("context") != "SYNTHETIC_ARCHITECTURE_FIXTURE_ONLY_NOT_BUILDING_PLAN":
        raise CompilationRejected("PLAN_INPUT_CONTEXT_NOT_EXPLICITLY_RESEARCH")
    return obj, sha256(raw).hexdigest()


def audit(catalog_file: Path, plan_input_file: Path, out: Path) -> dict:
    catalog_file, plan_input_file, out = map(
        Path, (catalog_file, plan_input_file, out))
    if (out.exists() or out.is_symlink() or
            out.resolve() in (catalog_file.resolve(), plan_input_file.resolve())):
        raise CompilationRejected("REFUSE_OVERWRITE_OR_SOURCE_OUTPUT")
    catalog = read_candidate_catalog(catalog_file)
    manifest, manifest_sha = _manifest(plan_input_file)
    compiler = RegulatoryCompiler(catalog)
    plan = compiler.compile_candidate(
        model_profile=manifest.get("model_profile"),
        combo_book=manifest.get("combo_book"),
        expected_instances=manifest.get("expected_instances"),
    )
    result = assess_candidate_plan(plan, manifest.get("caller_outcomes", []))
    receipt = {
        "schema": "tbdy.next.vs05.candidate-dag-audit.v1",
        "catalog_sha256": compiler.graph["catalog_sha256"],
        "candidate_plan_input_sha256": manifest_sha,
        "model_analysis_source_attestation": "NOT_PROVEN",
        "dag": compiler.graph,
        "execution_plan": plan,
        "fcr": result,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "note": "Research-only expected denominator. No approved building-wide expected check census.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")
    return receipt


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog", required=True, type=Path)
    p.add_argument("--plan-input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    r = audit(args.catalog, args.plan_input, args.out)
    print("VS05 candidate DAG:", r["dag"]["candidate_nodes"],
          "nodes,", r["dag"]["candidate_dependency_edges"], "edges")
    print("Topological waves:", len(r["dag"]["topological_waves"]))
    print("Execution authorized nodes:", r["dag"]["execution_authorized_nodes"])
    print("FCR expected:", r["fcr"]["expected_count"])
    print("FCR reconciled:", r["fcr"]["reconciled_count"])
    print("FCR NOT_PROVEN:", r["fcr"]["not_proven_count"])
    print("Plan SHA:", r["execution_plan"]["plan_sha256"])
    print("Report:", args.out.resolve())
    print("Regulatory compliance: NOT_PROVEN; engineering release: NOT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
