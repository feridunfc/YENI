"""Windows CLI wrapper for the tbdy_next ETABS VS01 modal adapter.

Kept for backward compatibility with already-tested PyCharm commands.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tbdy_next.etabs_modal import ModalCaptureError, capture_modal


def main() -> int:
    parser = argparse.ArgumentParser(description="TBDY Next VS01 — hedefli canlı modal aktarım")
    parser.add_argument("--case", default="Modal")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        from tbdy_next.live_etabs import read_modal_from_running_etabs
        data = read_modal_from_running_etabs(args.case)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"SOURCE_CAPTURED rows={data['table']['row_count']} case_rows={data['capture_metadata']['case_row_count']} out={args.output}")
        print(f"NEXT: python -m tbdy_next.cli check-modal --input {args.output} --case {args.case} --out .receipts")
        return 0
    except Exception as exc:
        print(f"CAPTURE_REJECTED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
