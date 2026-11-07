r"""Windows VS04-G one-session diaphragm and spectrum-modal evidence capture.

ETABS must already be open and model analysis locked. This script reads
existing tables and temporarily changes *only display case selection*,
then restores it. No analysis, modeling, saving, unit or property setters.

Example (PowerShell):
  .\.venv\Scripts\python.exe tools\probe_vs04g_diaphragm_windows.py --out .receipts\VS04\VS04G_DIAPHRAGM.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from tbdy_next.diaphragm_probe import (
    capture_diaphragm_modal_probe, review_diaphragm_modal_probe,
)


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args(argv)
    if sys.platform!="win32":
        raise SystemExit("VS04G_WINDOWS_LIVE_ETABS_ONLY")
    target=args.out
    if target.exists() or target.is_symlink():
        raise ValueError("VS04G_OUTPUT_EXISTS_NO_OVERWRITE")
    import comtypes
    import comtypes.client
    comtypes.CoInitialize()
    app = sap = None
    try:
        app=comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        sap=app.SapModel
        if sap is None:
            raise RuntimeError("VS04G_ACTIVE_ETABS_MODEL_UNAVAILABLE")
        data=capture_diaphragm_modal_probe(sap)
    finally:
        sap=None
        app=None
        comtypes.CoUninitialize()
    review=review_diaphragm_modal_probe(data)
    receipt={"schema":"tbdy.next.vs04g.diaphragm-source-receipt.v1",
             "capture_utc":datetime.now(timezone.utc).isoformat(),
             "source":data,"review":review,
             "engineering_release":"NOT_READY"}
    payload=(json.dumps(receipt,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    target.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation: never overwrite an existing verification record.
    with target.open("xb") as output:
        output.write(payload)
    print("VS04-G:",review["status"])
    print("Source success:",review.get("source_success_count"),"/ 5")
    for entry in review.get("tables",[]):
        print(entry["table_key"],entry.get("capture_phase","diaphragm"),
              "|",entry["source_status"],"| rows:",entry["rows"],
              "|",",".join(entry["reason_codes"]))
    print("SHA256:",sha256(payload).hexdigest())
    print("File:",target.resolve())
    print("Regulatory compliance: NOT_PROVEN")
    print("Engineering release: NOT_READY")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
