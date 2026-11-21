r"""CODE_DEFECT_PROBE_NOT_C29: reproduce two source-contract behaviors.

Use only existing repository fixtures and actual production owners. This is
an audit probe, not a live ETABS run, independent building validation, new
golden fixture, engineering acceptance test, or production code correction.

Example from the repository root:
    .venv/bin/python -B <path>/reproduce_engineering_findings.py --repo . --output <path>/targeted_reproductions.json

Windows:
    .\.venv\Scripts\python.exe -X utf8 -B <path>\reproduce_engineering_findings.py --repo . --output <path>\targeted_reproductions.json

The process succeeds when both probes execute and emit their observations.
The JSON's defect_reproduced fields distinguish an observed defect from a
fixed behavior. No precomputed successful engineering outputs are injected.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    for required in ("src/tbdy_next/engineering/gravity_story_basis.py", "tests/test_gravity_story_basis.py"):
        if not (repo / required).is_file():
            parser.error("--repo must identify the YENI checkout: missing " + required)
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "tests"))
    sys.path.insert(0, str(repo / "src"))

    import tbdy_next
    from test_gravity_story_basis import _example
    from test_engine_r08_story import example
    from test_r08_story_second_order import fixture, sealed
    from tbdy_next.engineering.gravity_story_basis import (
        CONTRIBUTOR_MODIFIER_SCHEMA, CONDITIONAL_FRAME_BASIS_SCHEMA,
        produce_story_basis,
    )
    from tbdy_next.engineering.story_pdelta import review_story_pdelta
    from tbdy_next.story_second_order import bind_story_second_order

    actual_import = Path(tbdy_next.__file__).resolve()
    if not actual_import.is_relative_to(repo / "src"):
        raise RuntimeError("The requested checkout was not imported")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          check=True, capture_output=True, text=True).stdout.strip()
    out = {
        "classification": "CODE_DEFECT_PROBE_NOT_C29",
        "baseline": head,
        "package_import": str(actual_import),
        "python_version": sys.version,
        "scope": "Existing test fixture inputs; actual production owners; no full regression or live ETABS run.",
    }

    # Existing one-column fixture, with the existing explicit conditional
    # frame contract added. Independent external-load evidence is then changed
    # by +100 kN while geometry, native column forces and stiffness are fixed.
    source, local, level, uid, cases = _example()
    block = level["story_basis_source"]
    block["contributor_modifiers"] = {
        "schema": CONTRIBUTOR_MODIFIER_SCHEMA,
        "model_sha256": level["model_sha256"],
        "analysis_generation": level["analysis_generation"],
        "modifiers": copy.deepcopy(level["frame_object_modifiers"]),
    }
    block["conditional_frame_basis"] = {
        "schema": CONDITIONAL_FRAME_BASIS_SCHEMA,
        "decision_reference": "Audit of an existing contract fixture; not engineering adoption",
        "stories": {"S1": {"credited_column_ids": [uid], "excluded_coupled_column_ids": []}},
    }
    kwargs = {"story_geometry": {"physical_lengths": {uid: local["physical_clear_length"]}}}
    before = produce_story_basis(source, local, level, uid, cases, **kwargs)
    block["story_cuts"]["S1"]["equilibrium"]["F"]["upper_external_applied_kn"] += 100.0
    after = produce_story_basis(source, local, level, uid, cases, **kwargs)

    def summarize_story(item):
        child = item.get("conditional_frame_basis") or {}
        return {
            "full_status": item["status"],
            "case": item["cases"]["G"],
            "conditional_status": child.get("status"),
            "conditional_story_inputs": child.get("story_inputs"),
        }

    out["conditional_known_imbalance"] = {
        "before": summarize_story(before), "after": summarize_story(after),
        "defect_reproduced": (
            "STORY_FREE_BODY_VERTICAL_IMBALANCE" in after["cases"]["G"]["reasons"]
            and bool((after.get("conditional_frame_basis") or {}).get("story_inputs"))
        ),
        "consumer_observation": (
            "gravity_pair_refinement.compare_level selects nonempty conditional story_inputs "
            "when the full story basis is not calculated; this script probes the producer only."
        ),
    }

    # No height, load, shear, drift or stiffness changes: shift only the
    # coordinate origin. The theta scalar has no absolute-elevation operand.
    source = example()
    before = review_story_pdelta(source)
    for row in source["stories"]:
        row["level_m"] -= 10.0
    try:
        after = review_story_pdelta(source)
        error = None
    except ValueError as exc:
        after, error = None, str(exc)
    out["global_theta_vertical_origin"] = {
        "before_theta_max": before["theta_max"],
        "translated_level_m": [r["level_m"] for r in source["stories"]],
        "after": after, "exception": error,
        "defect_reproduced": error == "INVALID_STORY_VALUE:level_m",
    }

    # Repeat through the product source adapter, using its existing fixture
    # and its standard source-sealing helper after changing the base datum.
    source = fixture()
    before = bind_story_second_order(source)
    tables = source["spectrum_source"]["table_reads"]
    tables["Tower and Base Story Definitions"]["rows"][0]["BSElev"] = "-10"
    source["spectrum_source"] = sealed(tables)
    after = bind_story_second_order(source)
    out["global_theta_product_adapter"] = {
        "before": {
            "status": before["status"], "evaluated": before["evaluated_story_direction_count"],
            "expected": before["expected_story_direction_count"], "directions": before["direction_results"],
        },
        "after": {
            "status": after["status"], "evaluated": after["evaluated_story_direction_count"],
            "expected": after["expected_story_direction_count"], "reasons": after["reason_codes"],
        },
        "defect_reproduced": "INVALID_STORY_VALUE:level_m" in after["reason_codes"],
        "expected_scope_lost": (before["expected_story_direction_count"] > 0
                                and after["expected_story_direction_count"] == 0),
    }
    paths = [
        "src/tbdy_next/engineering/gravity_story_basis.py",
        "src/tbdy_next/engineering/gravity_pair_refinement.py",
        "src/tbdy_next/engineering/story_pdelta.py",
        "src/tbdy_next/story_second_order.py",
        "tests/test_gravity_story_basis.py",
        "tests/test_engine_r08_story.py",
        "tests/test_r08_story_second_order.py",
    ]
    out["file_sha256"] = {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in paths}
    rendered = json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
