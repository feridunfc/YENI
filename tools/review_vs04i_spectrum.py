"""Offline source-only VS04-I TSC-2018 spectrum replay, without ETABS COM.

Inputs: the original VS04-E basis probe, VS04-G selected response-spectrum
modal source, and VS04-D modal replay. Original files are never modified.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.spectrum_reconstruction import review_spectrum_reconstruction

MAX_INPUT_BYTES = 16 * 1024 * 1024


def _read(path: Path) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("INVALID_INPUT_FILE_OR_SIZE")
    payload = path.read_bytes()
    if not payload:
        raise ValueError("EMPTY_SOURCE_FILE")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("NON_JSON_UTF8_INPUT") from exc
    if not isinstance(value, dict):
        raise ValueError("SOURCE_TOP_LEVEL_MUST_BE_OBJECT")
    return value, sha256(payload).hexdigest()


def replay(basis_file: Path, modal_info_file: Path, prior_modal_file: Path,
           output_file: Path) -> dict:
    inputs = [Path(basis_file), Path(modal_info_file), Path(prior_modal_file)]
    dest = Path(output_file)
    if dest.is_symlink() or dest.exists() or any(
            dest.resolve() == p.resolve() for p in inputs):
        raise ValueError("OUTPUT_EXISTS_OR_OVERWRITES_SOURCE")
    values = [_read(p) for p in inputs]
    result = review_spectrum_reconstruction(*(x[0] for x in values))
    receipt = {
        "schema": "tbdy.next.vs04i.spectrum-reconstruction-replay.v1",
        "basis_source_sha256": values[0][1],
        "spectrum_modal_source_sha256": values[1][1],
        "prior_modal_replay_sha256": values[2][1],
        "source_raw_included": False,
        "spectrum_reconstruction": result,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf-8") as file:
        json.dump(receipt, file, indent=2, sort_keys=True, ensure_ascii=False)
        file.write("\n")
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--modal-info", type=Path, required=True)
    parser.add_argument("--prior-modal", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = replay(args.basis, args.modal_info, args.prior_modal, args.out)
    result = report["spectrum_reconstruction"]
    print("VS04-I:", result["status"])
    print("Analytical function points:", result.get("analytical_knot_consistency_count"),
          "/", result.get("source_knot_count"))
    print("Modal reconstructed:", result.get("reconstructed_modal_rows"),
          "/", result.get("modal_source_rows"))
    print("Max residual (m/s2):", result.get("max_absolute_residual_m_s2"))
    print("Reason codes:", ",".join(result.get("reason_codes", [])))
    print("Output:", args.out.resolve())
    print("Regulatory checks executed: 0; ENGINEERING_RELEASE=NOT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
