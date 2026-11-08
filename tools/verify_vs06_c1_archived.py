"""VS06-C1 read-only effective drift readiness audit over sealed real receipts.

No COM, model mutation, real R/I inference, response-spectrum Max subtraction
or normative authority. Complements tools/verify_vs06_archived_report.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tbdy_next.reporting import build_complete_report, build_printable_html


def verify(root: Path, run_id: str, *, expected_checks: int | None = None,
           expected_source_numeric: int | None = None) -> dict:
    report = build_complete_report(root, run_id)
    c = report.get("vs06_effective_drift_readiness")
    a = report.get("vs06_story_slot_ledger")
    b = report.get("vs06_physical_source_review")
    if not all(isinstance(x, dict) for x in (a, b, c)):
        raise ValueError("VS06_ABC_ARCHIVED_REPLAY_MISSING")
    expected = c["expected_story_direction_instances"]
    numeric = c["source_numeric_primary_instances"]
    if expected_checks is not None and expected_checks != expected:
        raise ValueError("VS06_C1_EXPECTED_CHECK_DENOMINATOR_CHANGED")
    if expected_source_numeric is not None and expected_source_numeric != numeric:
        raise ValueError("VS06_C1_OBSERVED_SOURCE_COUNT_CHANGED")
    if (c["candidate_fcr_expected"] != expected or
            c["candidate_fcr_reconciled"] != expected or
            c["candidate_fcr_not_proven"] != expected or
            c["candidate_fcr_pass"] != 0 or
            c["formula_executed_count"] != 0 or
            expected != a["expected_slot_count"] // 2 or
            numeric + c["source_missing_primary_instances"] != expected or
            c["physical_census_approved"] is not False or
            c["analysis_generation_approved"] is not False or
            c["reduced_design_displacement_approved"] is not False or
            c["r_i_dd2_dd3_wall_basis_approved"] is not False or
            c["dag_execution_authority"] != "DENIED" or
            c["formal_compliance"] != "NOT_PROVEN" or
            c["engineering_release"] != "NOT_READY"):
        raise ValueError("VS06_C1_NORMATIVE_OR_DENOMINATOR_UNSAFE")
    if any(row["formula_execution"] != "BLOCKED_BY_EVIDENCE" or
           row["regulatory_status"] != "NOT_PROVEN" or
           row["physical_applicability"] != "NOT_PROVEN"
           for row in c["check_instances"]):
        raise ValueError("VS06_C1_UNAUTHORIZED_CHECK_RESULT")
    html = build_printable_html(report)
    if "VS06-C1" not in html or "NOT_PROVEN" not in html:
        raise ValueError("VS06_C1_HTML_SECTION_MISSING")
    return {
        "status": "VS06_C1_DAG_FCR_SOURCE_READINESS_REPLAYED",
        "run_id": run_id,
        "story_direction_check_instances": expected,
        "source_numeric_primary_candidates": numeric,
        "source_missing_primary_candidates": c["source_missing_primary_instances"],
        "candidate_fcr_not_proven": c["candidate_fcr_not_proven"],
        "formula_executed_count": 0,
        "dag_catalog_sha256": c["candidate_catalog_sha256"],
        "candidate_plan_sha256": c["candidate_plan_sha256"],
        "candidate_fcr_sha256": c["candidate_fcr_sha256"],
        "readiness_sha256": c["readiness_sha256"],
        "html_bytes": len(html.encode("utf-8")),
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".receipts"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-checks", type=int, default=None)
    parser.add_argument("--expected-source-numeric", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.run_id,
                            expected_checks=args.expected_checks,
                            expected_source_numeric=args.expected_source_numeric),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
