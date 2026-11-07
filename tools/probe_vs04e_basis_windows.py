"""Windows-only VS04-E read-only ETABS seismic basis-table source probe.

Usage:
    .\.venv\Scripts\python.exe tools\probe_vs04e_basis_windows.py --out .receipts\VS04\VS04E_BASIS_PROBE.json

Output is PRIVATE local source evidence; do not commit an EDB or raw capture.
No RunAnalysis/SetPresentUnits/SetLoadCasesSelectedForDisplay/Save calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from tbdy_next.basis_probe import capture_basis_probe, review_basis_probe


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--max-tables",type=int,default=24)
    args=p.parse_args(argv)
    if sys.platform != "win32":
        raise SystemExit("LIVE_ETABS_WINDOWS_ONLY")
    import comtypes
    import comtypes.client

    comtypes.CoInitialize()
    app = sap = None
    try:
        app=comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        sap=app.SapModel
        if sap is None:
            raise RuntimeError("EXISTING_ETABS_SAPMODEL_MISSING")
        source=capture_basis_probe(sap,max_tables=args.max_tables)
    finally:
        sap = None
        app = None
        comtypes.CoUninitialize()

    summary=review_basis_probe(source)
    record={
       "schema":"tbdy.next.vs04e.basis-probe-receipt.v1",
       "captured_at_utc":datetime.now(timezone.utc).isoformat(),
       "source":source,
       "review":summary,
       "engineering_release":"NOT_READY",
    }
    payload=(json.dumps(record,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode("utf-8")
    out=args.out
    if out.is_symlink() or out.exists():
        raise ValueError("REFUSE_OVERWRITE_EXISTING_CAPTURE")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(payload)
    print("VS04-E source probe:",summary["status"])
    print("Available ETABS tables:",summary.get("available_table_count"))
    print("Candidate tables:",summary.get("candidate_count"))
    print("Observed candidate table rows:",summary.get("observed_candidate_count"))
    print("SHA256:",sha256(payload).hexdigest())
    for row in summary.get("candidates",[]):
        print(row["table_key"],"|",row["status"],"|",row["row_count"],
              "|",",".join(row["roles_not_approved"]))
    print("Capture:",out.resolve())
    print("ENGINEERING_RELEASE=NOT_READY")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
