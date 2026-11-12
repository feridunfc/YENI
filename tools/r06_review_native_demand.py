"""Codespaces-only R06: validate pinned native ZIP + signed/spectral semantics."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys

from tbdy_next.column_engine.native_archive import BankError, NativeArchive
from tbdy_next.r06_demand_semantics import R06EvidenceError, review_r06_native_demand
from r01_verify_archived_bank import read_bank, file_sha, R01Error

ROOT = Path(__file__).resolve().parents[1]


def read_json(path, maximum=6_000_000):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise R06EvidenceError("INPUT_FILE_INVALID")
    obj = json.loads(path.read_bytes())
    if not isinstance(obj, dict):
        raise R06EvidenceError("INPUT_JSON_OBJECT_REQUIRED")
    return obj


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bank", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--r01", type=Path)
    p.add_argument("--r02", type=Path)
    p.add_argument("--r03", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path,
                   default=ROOT / "config/r01_archived_sources.json")
    args = p.parse_args(argv)
    try:
        m = read_json(args.manifest, 100_000)
        if m.get("schema") != "tbdy.next.r01-archived-sources.v1":
            raise R06EvidenceError("INVALID_PINNED_MANIFEST")
        if (args.bank.name != m["bank_filename"]
                or args.native.name != m["native_archive_filename"]
                or args.bank.is_symlink() or args.native.is_symlink()
                or args.native.stat().st_size > 64 * 1024 * 1024
                or args.bank.stat().st_size > 64 * 1024 * 1024):
            raise R06EvidenceError("SOURCE_FILE_PATH_OR_SIZE_INVALID")
        if (file_sha(args.native) != m["native_archive_sha256"]
                or file_sha(args.bank) != m["bank_zip_sha256"]):
            raise R06EvidenceError("SOURCE_ZIP_SHA_MISMATCH")
        bank = read_bank(args.bank, m["bank_zip_sha256"])
        if (bank.get("run_id") != m["source_run_id"]
                or bank.get("source_archive_sha256") != m["native_archive_sha256"]):
            raise R06EvidenceError("HISTORICAL_ARCHIVE_RUN_MISMATCH")
        receipts = {k: read_json(getattr(args, k)) if getattr(args, k) else None
                    for k in ("r01", "r02", "r03")}
        if args.output.is_symlink() or args.output.exists():
            raise R06EvidenceError("REFUSING_TO_OVERWRITE_RESULT")
        with closing(NativeArchive(args.native.read_bytes())) as archive:
            result = review_r06_native_demand(
                bank, archive, **receipts, bank_zip_sha256=m["bank_zip_sha256"])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write((json.dumps(result, ensure_ascii=False, sort_keys=True,
                                     indent=2, allow_nan=False) + "\n").encode())
        print(json.dumps({
            "status": result["status"], "run": result["source_run_id"],
            "static": result["signed_native_static_states"],
            "spectral_pairs": result["matched_statistical_spectral_pairs"],
            "conditional_candidates": result["conditional_corner_candidates"],
            "cross_slice_receipts_complete": result["cross_slice_receipts_complete"],
            "design_demand_authority": result["design_demand_authority"],
            "engineering_release": result["engineering_release"]}, ensure_ascii=False))
        return 0
    except (R01Error, R06EvidenceError, BankError, OSError, ValueError,
            KeyError, TypeError, AttributeError, MemoryError) as exc:
        print(json.dumps({"status": "BLOCKED_SOURCE_DEMAND",
                          "reason": str(exc), "engineering_release": "NOT_READY"},
                         ensure_ascii=False), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
