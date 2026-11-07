"""Offline VS04-H diary of exact diaphragm and spectrum modal source links.

Never connects to ETABS. The output omits original rows and retains SHA-256
of every exact input. No code compliance or engineering release is issued.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.diaphragm_linkage import review_vs04h_source

MAX_BYTES = 8 * 1024 * 1024


def _load(path: Path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise ValueError("SOURCE_FILE_INVALID_OR_TOO_LARGE")
    body = path.read_bytes()
    if not body:
        raise ValueError("SOURCE_FILE_EMPTY")
    try:
        value = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("SOURCE_NOT_UTF8_JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("SOURCE_TOP_LEVEL_NOT_OBJECT")
    return value, sha256(body).hexdigest(), len(body)


def review_files(source_file: Path, out_file: Path,
                 prior_modal_file: Path | None = None) -> dict:
    source_file, out_file = Path(source_file), Path(out_file)
    if out_file.resolve() == source_file.resolve() or out_file.is_symlink() or out_file.exists():
        raise ValueError("REFUSE_SOURCE_OR_EXISTING_OUTPUT_OVERWRITE")
    if prior_modal_file is not None and out_file.resolve() == Path(prior_modal_file).resolve():
        raise ValueError("REFUSE_PRIOR_MODAL_REPLAY_OVERWRITE")
    source, source_hash, size = _load(source_file)
    prior = prior_hash = None
    if prior_modal_file is not None:
        prior, prior_hash, _ = _load(Path(prior_modal_file))
    linkage = review_vs04h_source(source, prior_modal_replay=prior)
    result = {
        "schema": "tbdy.next.vs04h.offline-source-linkage.v1",
        "source_sha256": source_hash,
        "source_size_bytes": size,
        "prior_modal_replay_sha256": prior_hash,
        "source_raw_included": False,
        "linkage": linkage,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("x", encoding="utf-8") as f:
        json.dump(result, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--prior-modal", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    out = review_files(args.input, args.out, args.prior_modal)
    report = out["linkage"]
    print("VS04-H:", report["status"])
    print("Source checks:", report.get("observed_source_component_count"), "/",
          report.get("source_component_count"))
    print("Original ETABS read statuses:",
          report.get("original_source_reads_observed"), "/",
          report.get("original_source_reads_expected"))
    print("Defined but not assigned:",
          ",".join(report.get("defined_but_unassigned_diaphragms", [])))
    for item in report["components"]:
        print(item["component"], "|", item["status"],
              "|", ",".join(item["reason_codes"]))
    print("SHA-256:", out["source_sha256"])
    print("Output:", args.out.resolve())
    print("Normative checks: 0; ENGINEERING_RELEASE=NOT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
