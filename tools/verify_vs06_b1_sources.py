"""Read-only VS06-D1 B1 calculation and self-contained engineering HTML report.

Usage:
python -m tools.verify_vs06_b1_sources --geometry B1_GEOMETRY.json
 --wall-loads LC_WDL_OBJECT.json --out B1_RESULT.json --html B1_RESULT.html

Never rewrites or changes original ETABS captures.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tbdy_next.b1_source_bridge import _td, evaluate_b1_sources, render_b1_html
from tbdy_next.etabs_source_gateway_windows import read_json, save_new


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--geometry",type=Path,required=True)
    p.add_argument("--wall-loads",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--html",type=Path)
    p.add_argument("--wall-type",choices=("BRITTLE","FLEXIBLE"),default="BRITTLE")
    p.add_argument("--brick-gamma",default="10")
    p.add_argument("--brick-gamma-min",default="6")
    p.add_argument("--brick-gamma-max",default="20")
    p.add_argument("--opening-fraction",default="0.5")
    p.add_argument("--opening-cutoff",default="0.75")
    p.add_argument("--shear-modulus-mpa",default="500")
    p.add_argument("--r",default="7")
    args=p.parse_args()
    result=evaluate_b1_sources(
        read_json(args.geometry),read_json(args.wall_loads),
        wall_type=args.wall_type,
        unit_weight_kN_m3=args.brick_gamma,
        unit_weight_min_kN_m3=args.brick_gamma_min,
        unit_weight_max_kN_m3=args.brick_gamma_max,
        opening_fraction=args.opening_fraction,
        low_load_ratio_cutoff=args.opening_cutoff,
        shear_modulus_mpa=args.shear_modulus_mpa,
        R_base=args.r,
    )
    save_new(args.out,result)
    if args.html:
        html=render_b1_html(result)
        args.html.parent.mkdir(parents=True,exist_ok=True)
        if args.html.exists():
            raise FileExistsError("Refusing to overwrite existing B1 HTML report")
        args.html.write_text(html,encoding="utf-8")
    print(json.dumps({
        "schema":result["schema"],
        "model":result["model"],
        "story_direction_areas":result["story_direction_areas"],
        "b1_eta_min":result["b1_numerical"]["eta_ci_min"],
        "b1_numeric_condition":result["b1_numerical"]["numeric_condition"],
        "expected_b1_pairs":result["b1_numerical"]["expected_story_direction_pairs"],
        "source_wall_load_rows":result["source_wall_load_rows"],
        "source_candidate_wall_beams":result["source_candidate_wall_beams"],
        "assumption_count":len(result["assumptions_notes"]),
        "result_sha256":result["result_sha256"],
        "formal_compliance":result["formal_compliance"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
