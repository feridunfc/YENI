"""Codespaces R04 replay. Offline only: never contacts ETABS or alters archives."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from tbdy_next.r04_offline_evidence import R04SourceError, review_r04_historical_run

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "config/r04_pinned_report.json"


def _read_json(path: Path, size_limit: int):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > size_limit:
        raise R04SourceError("MISSING_SYMLINK_OR_OVERSIZED_INPUT")
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise R04SourceError("INVALID_JSON_INPUT") from exc
    if not isinstance(value, dict):
        raise R04SourceError("TOP_LEVEL_JSON_OBJECT_REQUIRED")
    return value, sha256(raw).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--r03", type=Path, help="optional R03 candidate; cross-run join remains denied")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        manifest, manifest_sha = _read_json(args.manifest, 100_000)
        if manifest.get("schema") != "tbdy.next.r04-pinned-sources.v1":
            raise R04SourceError("INVALID_R04_MANIFEST_SCHEMA")
        report, actual_sha = _read_json(args.report, 25_000_000)
        pinned = manifest.get("historical_report")
        if not isinstance(pinned, dict):
            raise R04SourceError("MISSING_PINNED_REPORT")
        if (args.report.name != pinned.get("basename")
                or actual_sha != pinned.get("sha256")
                or report.get("run_id") != pinned.get("run_id")):
            raise R04SourceError("UNTRUSTED_HISTORICAL_RUN_FILE")
        relation = _read_json(args.r03, 8_000_000)[0] if args.r03 else None
        result = review_r04_historical_run(report, actual_sha, relation)
        result["manifest_sha256"] = manifest_sha
        result["manifest_authority"] = "LOCAL_SHA_PIN_NOT_INDEPENDENT_ANALYSIS_PROOF"
        result["receipt_sha256"] = sha256(json.dumps(
            result, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        if args.output.is_symlink() or args.output.exists():
            raise R04SourceError("OUTPUT_ALREADY_EXISTS")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(args.output, flags, 0o600)
        with os.fdopen(fd, "wb") as dest:
            dest.write(payload)
        print(json.dumps({"status": result["status"],
                          "run_id": result.get("run_id"),
                          "reason_codes": result.get("reason_codes", []),
                          "engineering_release": result["engineering_release"],
                          "output": str(args.output)}, ensure_ascii=False))
        return 0 if result["status"] == "HISTORICAL_SOURCE_NUMERIC_REPLAY_RECONCILED" else 2
    except (R04SourceError, OSError, TypeError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc),
                          "engineering_release": "NOT_READY"}, ensure_ascii=False),
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
