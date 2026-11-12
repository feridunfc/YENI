"""R05 offline story, A1/B1/B2 and drift evidence ledger; no live ETABS."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from tbdy_next.compiled_dag import read_candidate_catalog
from tbdy_next.r05_story_irregularity import review_r05_story_irregularities

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path, *, maximum: int):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("SOURCE_MISSING_SYMLINK_OR_OVERSIZED")
    data = path.read_bytes()
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("JSON_TOP_LEVEL_OBJECT_REQUIRED")
    return value, sha256(data).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--manifest", type=Path, default=ROOT / "config/r04_pinned_report.json")
    ap.add_argument("--catalog", type=Path, default=ROOT / "config/dag/tbdy_r1c_94_candidate.json")
    ap.add_argument("--r04", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        manifest, _ = _read(args.manifest, maximum=100_000)
        entry = manifest.get("historical_report", {})
        if manifest.get("schema") != "tbdy.next.r04-pinned-sources.v1":
            raise ValueError("UNTRUSTED_HISTORICAL_MANIFEST")
        report, digest = _read(args.report, maximum=25_000_000)
        if (entry.get("basename") != args.report.name or
                entry.get("sha256") != digest or
                entry.get("run_id") != report.get("run_id")):
            raise ValueError("HISTORICAL_REPORT_SHA_OR_RUN_MISMATCH")
        catalog = read_candidate_catalog(args.catalog)
        r04 = _read(args.r04, maximum=500_000)[0] if args.r04 else None
        outcome = review_r05_story_irregularities(
            report, digest, catalog=catalog, r04_receipt=r04)
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("EXISTING_OUTPUT_WILL_NOT_BE_OVERWRITTEN")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        blob = (json.dumps(outcome, sort_keys=True, ensure_ascii=False,
                           indent=2, allow_nan=False) + "\n").encode("utf-8")
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(blob)
        print(json.dumps({
            "status": outcome["status"], "run_id": outcome["run_id"],
            "declared_story_count": outcome.get("declared_story_count"),
            "drift_numeric_slots": outcome.get("source_drift", {}).get("observed_numeric_slots"),
            "drift_missing_slots": outcome.get("source_drift", {}).get("missing_source_slots"),
            "physical_census_proven": outcome.get("complete_physical_census_proven"),
            "reason_codes": outcome.get("reason_codes", []),
            "release": outcome["engineering_release"], "result_sha256": outcome["result_sha256"],
        }, ensure_ascii=False))
        return 0 if outcome["status"] == "SOURCE_SCENARIOS_REPLAYED_PARTIAL_PHYSICAL_AUTHORITY" else 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc),
                          "engineering_release": "NOT_READY"}, ensure_ascii=False), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
