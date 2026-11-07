"""VS04-J offline source-bound minimum base-shear screening.

No ETABS COM. It never declares VtE or beta-tE design compliant.
All input SHA-256 values are included; source bytes are excluded.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.base_shear_screening import review_base_shear_screening

MAX_BYTES = 16 * 1024 * 1024


def _read(path: Path) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("INVALID_INPUT_PATH_OR_SIZE")
    payload = path.read_bytes()
    if not payload:
        raise ValueError("EMPTY_SOURCE_INPUT")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("NOT_VALID_UTF8_JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("SOURCE_TOP_LEVEL_MUST_BE_OBJECT")
    return data, sha256(payload).hexdigest()


def replay_screening(basis_file: Path, modal_info_file: Path,
                     prior_modal_file: Path, output_file: Path) -> dict:
    paths = [Path(basis_file), Path(modal_info_file), Path(prior_modal_file)]
    dest = Path(output_file)
    if dest.is_symlink() or dest.exists() or any(
            dest.resolve() == path.resolve() for path in paths):
        raise ValueError("REFUSE_OUTPUT_OVERWRITE")
    values = [_read(path) for path in paths]
    review = review_base_shear_screening(*(v[0] for v in values))
    report = {
        "schema": "tbdy.next.vs04j.base-shear-source-screening.v1",
        "basis_source_sha256": values[0][1],
        "modal_info_sha256": values[1][1],
        "prior_modal_replay_sha256": values[2][1],
        "source_raw_included": False,
        "screening": review,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf-8") as f:
        json.dump(report, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", required=True, type=Path)
    parser.add_argument("--modal-info", required=True, type=Path)
    parser.add_argument("--prior-modal", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    payload = replay_screening(args.basis, args.modal_info,
                               args.prior_modal, args.out)
    result = payload["screening"]
    print("VS04-J:", result["status"])
    print("Candidate Eq 4.19 minimum term (kN):",
          result.get("conditional_eq_4_19_minimum_term_kn"))
    print("Source base components:",
          result.get("source_case_base_reaction_components_kn"))
    print("Full VtE:", result["full_equivalent_base_shear_kn"])
    print("beta_tE X/Y:", result["beta_tE_X"], result["beta_tE_Y"])
    print("Regulatory checks: 0; Engineering release: NOT_READY")
    print("Output:", args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
