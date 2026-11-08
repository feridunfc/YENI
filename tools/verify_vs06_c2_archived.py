"""VS06-C2 read-only numeric scenario replay over an accepted archived ETABS run.

Separates conditional numerical utilization from formal TBDY suitability.
No ETABS COM, no receipt modification, no claim of physical member-end
design displacement from independent response spectrum Max rows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tbdy_next.reporting import build_complete_report, build_printable_html
from tbdy_next.vs06_drift_scenario import evaluate_drift_scenario


def verify(root: Path, run_id: str, *, R: str = "7", I: str = "1.5",
           lam: str = "0.5", wall_type: str = "BRITTLE",
           expected_checks: int | None = None,
           expected_numeric: int | None = None,
           wall_mode: str = "LC_WALL_BEAM_CANDIDATE",
           manual_wall_length_m: str = "0") -> dict:
    report = build_complete_report(root, run_id)
    scenario = evaluate_drift_scenario(report, {
        "r": R, "i": I, "lambda": lam,
        "wall_type": wall_type, "wall_mode": wall_mode,
        "manual_wall_length_m": manual_wall_length_m,
    })
    if expected_checks is not None and scenario["expected_story_direction_count"] != expected_checks:
        raise ValueError("EXPECTED_STORY_DIRECTION_CHECK_COUNT_MISMATCH")
    if expected_numeric is not None and scenario["source_numeric_count"] != expected_numeric:
        raise ValueError("EXPECTED_SOURCE_NUMERIC_CANDIDATE_COUNT_MISMATCH")
    if (scenario["expected_story_direction_count"] !=
            scenario["source_numeric_count"] + scenario["missing_source_count"] or
            scenario["formal_compliance"] != "NOT_PROVEN" or
            scenario["engineering_release"] != "NOT_READY" or
            scenario["result_kind"] != "CONDITIONAL_SENSITIVITY_SCENARIO"):
        raise ValueError("C2_DENOMINATOR_OR_AUTHORITY_CONFLICT")
    report["vs06_drift_scenario"] = scenario
    html = build_printable_html(report)
    if "VS06-C2" not in html or "FORMAL COMPLIANCE: NOT_PROVEN" not in html:
        raise ValueError("C2_HTML_EXPORT_MISSING")
    return {
        "status": "VS06_C2_SOURCE_NUMERICAL_SCENARIO_REPLAYED",
        "run_id": run_id,
        "expected_story_direction_count": scenario["expected_story_direction_count"],
        "source_numeric_count": scenario["source_numeric_count"],
        "missing_source_count": scenario["missing_source_count"],
        "conditionally_within_limit": scenario["conditional_within_count"],
        "conditionally_exceeds_limit": scenario["conditional_exceeds_count"],
        "limit": scenario["limit"],
        "wall_source_status": scenario["wall_candidate_inventory"]["source_status"],
        "wall_candidate_beams": scenario["wall_candidate_inventory"]["candidate_beam_count"],
        "estimated_wall_area_m2": scenario["wall_candidate_inventory"]["assumed_net_face_area_m2"],
        "scenario_sha256": scenario["scenario_sha256"],
        "html_bytes": len(html.encode("utf-8")),
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".receipts"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--r", default="7")
    parser.add_argument("--i", default="1.5")
    parser.add_argument("--lambda", dest="lam", default="0.5")
    parser.add_argument("--wall-type", choices=("BRITTLE", "FLEXIBLE"), default="BRITTLE")
    parser.add_argument("--wall-mode", choices=("MANUAL", "LC_WALL_BEAM_CANDIDATE"),
                        default="LC_WALL_BEAM_CANDIDATE")
    parser.add_argument("--manual-wall-length-m", default="0")
    parser.add_argument("--expected-checks", type=int)
    parser.add_argument("--expected-numeric", type=int)
    args = parser.parse_args()
    print(json.dumps(verify(
        args.root, args.run_id, R=args.r, I=args.i,
        lam=args.lam, wall_type=args.wall_type,
        wall_mode=args.wall_mode, manual_wall_length_m=args.manual_wall_length_m,
        expected_checks=args.expected_checks, expected_numeric=args.expected_numeric,
    ), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
