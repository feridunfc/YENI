"""Run the existing offline pipeline from a source or a private evidence ZIP.

Only the explicitly selected source entry is read. No repository files, Git
metadata, EDB or historical receipts are extracted or overwritten.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from tbdy_next.cli import main as pipeline_cli
from tbdy_next.column_engine.native_archive import decode
from tbdy_next.history import _MAX_SOURCE_BYTES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", type=Path)
    source.add_argument("--bundle", type=Path, help="Private build.zip; not committed to Git")
    parser.add_argument("--source-entry", default=".receipts/RUN-5f870820872545a6bac7492becab9032/input.source")
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    def run(path: Path) -> int:
        return pipeline_cli(["run-pipeline", "--source", str(path), "--case", args.case,
                             "--out", str(args.out), "--design-scenario", str(args.scenario)])

    if args.source is not None:
        return run(args.source)
    try:
        scenario = decode(args.scenario.read_bytes())
        with ZipFile(args.bundle) as bundle:
            matches = [info for info in bundle.infolist() if info.filename == args.source_entry]
            if len(matches) != 1:
                raise ValueError("EVIDENCE_SOURCE_ENTRY_MISSING_OR_DUPLICATE")
            info = matches[0]
            if (info.is_dir() or not 0 < info.file_size <= _MAX_SOURCE_BYTES
                    or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("EVIDENCE_SOURCE_ENTRY_UNSAFE")
            with bundle.open(info) as stream:
                raw = stream.read(_MAX_SOURCE_BYTES + 1)
            if len(raw) != info.file_size or sha256(raw).hexdigest() != scenario["parent_input_sha256"]:
                raise ValueError("EVIDENCE_SOURCE_HASH_MISMATCH")
        with TemporaryDirectory(prefix="yeni-source-") as temporary:
            path = Path(temporary) / "input.source"
            path.write_bytes(raw)
            return run(path)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Offline evidence rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
