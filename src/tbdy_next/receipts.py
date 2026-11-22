"""Small append-only on-disk stage receipts. No generic event bus or database."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import uuid
from typing import Any, Mapping


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def receipt_paths(directory: Path) -> list[Path]:
    """Return numbered receipts in append order, rejecting ambiguous ordinals."""
    by_index = {}
    for path in directory.glob("[0-9]*-*.json"):
        prefix = path.stem.partition("-")[0]
        if not prefix.isascii() or not prefix.isdecimal():
            continue
        index = int(prefix)
        if index in by_index:
            raise ValueError(f"DUPLICATE_RECEIPT_INDEX:{index}")
        by_index[index] = path
    return [by_index[index] for index in sorted(by_index)]


class ReceiptRun:
    def __init__(self, root: Path):
        self.run_id = "RUN-" + uuid.uuid4().hex
        self.root = Path(root) / self.run_id
        self.root.mkdir(parents=True, exist_ok=False)
        self._counter = 0

    def archive_input(self, payload: bytes, *, expected_sha256: str) -> Path:
        """Keep original uploaded input locally; never commit it to the public repo."""
        if sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("Source input SHA-256 mismatch")
        target = self.root / "input.source"
        with target.open("xb") as stream:
            stream.write(payload)
        return target

    def record(self, stage: str, payload: Mapping[str, Any], *, input_sha256: str,
               receipt_schema: str | None = None) -> Path:
        self._counter += 1
        record = {
            "run_id": self.run_id,
            "stage": stage,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_sha256": input_sha256,
            "payload": dict(payload),
        }
        if receipt_schema is not None:
            record["receipt_schema"] = receipt_schema
        record["receipt_sha256"] = sha256(canonical_bytes(record)).hexdigest()
        target = self.root / f"{self._counter:02d}-{stage.lower()}.json"
        with target.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        return target
