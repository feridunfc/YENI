"""VS06-C2: calculate LC_WDL candidate wall face area from a SHA-sealed capture.

Read-only, offline. Keeps original database ret=1 and per-object API failures.
All area values are candidate wall assumptions, not B1 wall-shear proof.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path

from tools.etabs_source_gateway_windows import read_json, save_new
from tbdy_next.vs06_drift_scenario import options, _wall_candidates


def review_capture(
    source: dict, *, load_pattern: str = "LC_WDL",
    wall_height_m: str = "2.8", coverage_pct: str = "100",
    opening_pct: str = "0", thickness_m: str = "0.19",
) -> dict:
    opt = options({
        "wall_load_pattern": load_pattern, "wall_height_m": wall_height_m,
        "coverage_pct": coverage_pct, "opening_pct": opening_pct,
        "thickness_m": thickness_m,
    })
    summary = _wall_candidates({
        "source_snapshot": {"vs06_wall_load_source": source},
    }, opt)
    per_story: dict[str, dict] = defaultdict(lambda: {"candidate_beam_count": 0,
                                                        "loaded_length_m": Decimal(0)})
    for row in summary["candidate_spans"]:
        story = str(row["story"])
        per_story[story]["candidate_beam_count"] += 1
        per_story[story]["loaded_length_m"] += Decimal(row["candidate_loaded_length_m"])
    story_rows = []
    h = Decimal(opt["wall_height_m"])
    coverage = Decimal(opt["coverage_pct"]) / 100
    opening = Decimal(opt["opening_pct"]) / 100
    for name, value in sorted(per_story.items()):
        length = value["loaded_length_m"]
        story_rows.append({
            "story": name,
            "candidate_beam_count": value["candidate_beam_count"],
            "candidate_loaded_length_m": str(length),
            "assumed_net_face_area_m2": str(length * h * coverage * (1-opening)),
        })
    return {
        "schema": "tbdy.next.vs06.wall-load-candidate-review.v1",
        "model": source.get("model"),
        "original_source_sha256": source.get("payload_sha256"),
        "load_pattern": opt["wall_load_pattern"],
        "source_method": summary["source_method"],
        "source_status": summary["source_status"],
        "original_distributed_table_status": summary["original_distributed_table_status"],
        "source_census_complete": summary["source_census_complete"],
        "unresolved_beam_count": summary["unresolved_beam_count"],
        "candidate_beam_count": summary["candidate_beam_count"],
        "candidate_total_loaded_length_m": summary["candidate_total_length_m"],
        "assumed_net_face_area_m2": summary["assumed_net_face_area_m2"],
        "assumed_wall_volume_m3": summary["assumed_wall_volume_m3"],
        "per_story": story_rows,
        "candidate_spans": summary["candidate_spans"],
        "scenario_assumptions": opt,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--pattern", default="LC_WDL")
    p.add_argument("--wall-height-m", default="2.8")
    p.add_argument("--coverage-pct", default="100")
    p.add_argument("--opening-pct", default="0")
    p.add_argument("--thickness-m", default="0.19")
    a = p.parse_args()
    result = review_capture(
        read_json(a.input),
        load_pattern=a.pattern, wall_height_m=a.wall_height_m,
        coverage_pct=a.coverage_pct, opening_pct=a.opening_pct,
        thickness_m=a.thickness_m,
    )
    save_new(a.out, result)
    print(json.dumps({
        k: v for k, v in result.items()
        if k not in ("candidate_spans", "scenario_assumptions")
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
