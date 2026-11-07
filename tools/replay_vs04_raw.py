"""Offline VS04 replay of a PRIVATE, already captured ETABS RAW JSON.

No COM, no analysis, no design mutation or ETABS calls.
The derived report is a source-arithmetic candidate, NOT code compliance.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.analysis_sources import review_analysis_sources
from tbdy_next.analysis_numerics import evaluate_analysis_numerics

MAX_RAW_BYTES = 32 * 1024 * 1024


def replay_raw_file(input_file: Path, out_file: Path) -> dict:
    inp, dest = Path(input_file), Path(out_file)
    if inp.is_symlink() or not inp.is_file():
        raise ValueError("VS04_RAW file does not exist or is a symlink")
    data = inp.read_bytes()
    if not data or len(data) > MAX_RAW_BYTES:
        raise ValueError("VS04_RAW file exceeds size boundary or is empty")
    try:
        source = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("VS04_RAW must be valid UTF-8 JSON") from exc
    if not isinstance(source, dict):
        raise ValueError("VS04_RAW top level must be a JSON object")
    schema = review_analysis_sources(source)
    numeric = evaluate_analysis_numerics(source)
    output = {
        "schema": "tbdy.next.vs04.offline-source-replay.v1",
        "input_sha256": sha256(data).hexdigest(),
        "input_size_bytes": len(data),
        "source_schema_review": schema,
        "numeric_source_review": numeric,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "source_raw_included": False,
        "note": "This replay is source arithmetic, not a TBDY/TS500 code calculation.",
    }
    if dest.exists() and dest.is_symlink():
        raise ValueError("Refusing symlink output")
    if dest.resolve() == inp.resolve():
        raise ValueError("Cannot overwrite the original VS04_RAW source")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="VS04_RAW*.json")
    parser.add_argument("--out", required=True, type=Path, help="VS04_REPLAY*.json")
    args = parser.parse_args(argv)
    result = replay_raw_file(args.input, args.out)
    numeric = result["numeric_source_review"]
    print("VS04 schema:", result["source_schema_review"]["status"])
    print("VS04 numeric:", numeric["status"])
    print("Observed components:", numeric.get("observed_component_count", 0), "/ 5")
    for comp in numeric.get("results", []):
        print(comp["component"], "|", comp["status"],
              "|", comp["observed_row_count"], "/", comp["expected_row_count"],
              "|", ",".join(comp["reason_codes"]))
    print("Output:", args.out.resolve())
    print("Engineering release: NOT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
