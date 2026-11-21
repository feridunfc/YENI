"""Export explicit synthetic inputs for the existing YENI pipeline.

Run from a source checkout with its normal editable installation. This command
only serializes a public contract fixture. It neither calculates a structure nor
acquires ETABS. The normal ``tbdy-next run-pipeline`` command owns calculation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stories", type=int, choices=(1, 2), default=1)
    parser.add_argument("--k", type=float, default=1.0)
    parser.add_argument("--rm", type=float, default=0.0)
    parser.add_argument("--tie-diameter-mm", type=int, choices=(10, 12))
    parser.add_argument("--tie-spacing-mm", type=int)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "tests"))
    from vertical_slice_fixture import COMBINATIONS, source_and_request

    raw, request = source_and_request(k=args.k, rm=args.rm, two_story=args.stories == 2,
                                     column_tie_diameter=args.tie_diameter_mm,
                                     column_tie_spacing=args.tie_spacing_mm)
    request_bytes = (json.dumps(request, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files = {"input.source": raw, "design-scenario.json": request_bytes}
    manifest = {
        "schema": "tbdy.next.public-vertical-slice-inputs.v1",
        "classification": "CONTRACT_FIXTURE",
        "origin": "GENERATED_OFFLINE_NOT_ETABS",
        "description": "Explicit synthetic signed forces, native-shaped tables and adopted calculation assumptions; no solver execution or project approval.",
        "expected_columns": args.stories,
        "expected_beams": 2 * args.stories,
        "expected_member_combination_pairs": len(COMBINATIONS) * args.stories,
        "expected_force_cut_rows": 3 * len(COMBINATIONS) * args.stories,
        "design_combinations": list(COMBINATIONS),
        "files": {name: {"sha256": sha256(data).hexdigest(), "bytes": len(data)}
                  for name, data in files.items()},
        "generator_files": {
            str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(), ROOT / "tests/vertical_slice_fixture.py")
        },
        "live_ETABS_validation": "NOT_RUN",
        "engineering_approval": "NOT_GRANTED",
    }
    files["SOURCE_MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    output = args.out.resolve()
    conflicts = [name for name in files if (output / name).exists()]
    if conflicts:
        parser.error("Output files already exist; use a new directory: " + ", ".join(conflicts))
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (output / name).write_bytes(data)
    print(json.dumps({"output_directory": str(output), **manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
