"""Read-only VS06-A/B audit of an existing complete VS05 live receipt archive.

This does NOT connect to ETABS, start analysis, mutate any receipt, or award
regulatory approval. Expected counts are optionally asserted by operator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tbdy_next.reporting import build_complete_report, build_printable_html


def verify(root: Path, run_id: str, *, expected_slots: int | None = None,
           expected_missing: int | None = None) -> dict:
    report = build_complete_report(root, run_id)
    a = report.get("vs06_story_slot_ledger")
    b = report.get("vs06_physical_source_review")
    drift = report.get("story_drift")
    if not isinstance(a, dict) or not isinstance(b, dict) or not isinstance(drift, dict):
        raise ValueError("VS06_AB_ARCHIVE_STAGE_MISSING")
    expected, missing = a["expected_slot_count"], a["source_missing_count"]
    if (expected_slots is not None and expected != expected_slots) or (
            expected_missing is not None and missing != expected_missing):
        raise ValueError("VS06_EXPECTED_COVERAGE_NOT_OBSERVED")
    if (a["accounted_slot_count"] != expected or
            a["source_numeric_count"] + missing != expected or
            drift["expected_story_case_direction_count"] != expected or
            drift["evaluated_story_case_direction_count"] != a["source_numeric_count"] or
            len(b["slots"]) != expected or
            a["ledger_sha256"] != b["slot_ledger_sha256"]):
        raise ValueError("VS06_ACCOUNTING_OR_LINEAGE_CONFLICT")
    if (a["engineering_release"] != "NOT_READY" or
            b["engineering_release"] != "NOT_READY" or
            report["engineering_release"] != "NOT_READY" or
            a["formal_compliance"] != "NOT_PROVEN" or
            b["formal_compliance"] != "NOT_PROVEN" or
            report["formal_compliance"] != "NOT_PROVEN" or
            b["signed_concurrent_spectrum_design_pairs_proven"] != 0 or
            b["analysis_generation_independently_proven"] is not False or
            b["full_physical_story_census_proven"] is not False):
        raise ValueError("VS06_REGULATORY_AUTHORITY_MISREPRESENTED")
    html = build_printable_html(report)
    if not ("VS06-A" in html and "VS06-B" in html and "NOT_PROVEN" in html):
        raise ValueError("VS06_HTML_EVIDENCE_SECTION_MISSING")
    return {
        "status": "VS06_AB_ARCHIVED_SOURCE_ACCOUNTING_REPLAYED",
        "run_id": run_id,
        "check_count": report["check_inventory"]["count"],
        "expected_story_case_direction_slots": expected,
        "source_numeric_slots": a["source_numeric_count"],
        "source_missing_slots": missing,
        "physical_column_connections_observed": b["endpoint_linked_column_count"],
        "column_connections_unresolved": b["unresolved_column_count"],
        "spectrum_independent_point_max_rows": b["response_spectrum_independent_max_rows"],
        "design_concurrent_displacement_pairs_proven": 0,
        "full_physical_census_proven": False,
        "source_ledger_sha256": a["ledger_sha256"],
        "physical_review_sha256": b["review_sha256"],
        "html_bytes": len(html.encode("utf-8")),
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".receipts"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-slots", type=int, default=None)
    parser.add_argument("--expected-missing", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.run_id,
                            expected_slots=args.expected_slots,
                            expected_missing=args.expected_missing),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
