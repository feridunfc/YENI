r"""Offline VS05 story-delta calculation from already-captured ETABS JSON.

  .\.venv\Scripts\python.exe tools\calc_vs05_story_delta.py --source .receipts\VS05\DELTA_SOURCE_....json --out .receipts\VS05\DELTA_CALC_....json

No Windows/COM connection is required.  No ETABS model state is changed.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json

from tbdy_next.story_delta import DeltaSourceError, calculate_file


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.source.resolve() == args.out.resolve():
        raise SystemExit("REFUSE_OVERWRITE_SOURCE_CAPTURE")
    result = calculate_file(args.source)
    data = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as f:  # no overwrite
        f.write(data)
    print("STATUS:", result["status"])
    print("ETABS spectrum story deltas:", len(result["story_deltas"]))
    print("Missing whole-story/case/direction entries:", len(result["story_delta_coverage"]["missing_story_case_direction"]))
    print("Modal shape column-mode pairs:", len(result["column_modal_shape_differences"]))
    print("RSX/RSY 'Max' point values NOT subtracted:", result["modal_shape_coverage"]["spectrum_point_max_rows_not_subtracted"])
    for row in result["story_deltas"]:
        if row["primary_direction"]:
            print(f"{row['story']} {row['case']} {row['direction']} DeltaCandidate={row['etabs_derived_delta_mm']} mm")
    print("REGULATORY COMPLIANCE: NOT_PROVEN")
    print("OUTPUT:", args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
