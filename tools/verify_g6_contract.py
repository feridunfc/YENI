"""Seal or independently replay the scoped G6 Supervisor closure candidates (GAP-011, GAP-012)."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.cli_adapter import _write_new
from tbdy_next.engineering.g1_contract import require
from tbdy_next.engineering.g6_contract import g6_contract, g6_verification
from tbdy_next.engineering.pipeline_snapshot import read_receipts, read_snapshot
from verify_g5_contract import verify as verify_parent


def _compare_or_seal(path: Path, value: dict, seal: bool) -> None:
    if seal and not path.exists():
        _write_new(path, value)
    require(json.loads(path.read_bytes()) == value, "G6_VERIFICATION_CHANGED:" + path.name)


def verify(directory: Path, base_id: str, seal: bool = False) -> dict:
    verify_parent(directory, base_id, seal=False)
    raw = archive_bytes(directory / "input.source")
    digest = sha256(raw).hexdigest()
    records = read_receipts(directory, input_sha=digest)
    snapshot = read_snapshot(directory, input_sha=digest, receipts=records)
    g5_packet = json.loads((directory / "g5-contract.json").read_bytes())
    report_html = (directory / "report.html").read_text(encoding="utf-8")
    packet = g6_contract(json.loads(raw), snapshot, g5_packet, report_html)
    _compare_or_seal(directory / "g6-contract.json", packet, seal)
    record = g6_verification(directory, packet, snapshot)
    _compare_or_seal(directory / "g6-verification.json", record, seal)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--source-run", default="RUN-3bb6a4d5d57c4af8af503a20c4d69bbd")
    parser.add_argument("--seal", action="store_true")
    options = parser.parse_args()
    record = verify(options.run.resolve(), options.source_run, options.seal)
    print(json.dumps(record, indent=2))
    raise SystemExit(int(not all(row["closure_ready"] for row in record["gaps"].values())))
