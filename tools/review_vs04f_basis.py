"""Read-only, offline VS04-F binding review against local VS04-E basis probe.

No COM, no ETABS session, no model alteration. Never commits raw source.
Reports provisional source bindings, missing normative inputs and SHA-256.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.basis_linkage import review_basis_linkage

MAX_BYTES = 32 * 1024 * 1024


def replay_basis(source_path: Path, out_path: Path) -> dict:
    source_path=Path(source_path)
    out_path=Path(out_path)
    if (not source_path.is_file() or source_path.is_symlink() or
            source_path.stat().st_size>MAX_BYTES):
        raise ValueError("BASIS_INPUT_INVALID_OR_TOO_LARGE")
    raw=source_path.read_bytes()
    if not raw:
        raise ValueError("BASIS_INPUT_EMPTY")
    try:
        source=json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("BASIS_INPUT_NOT_JSON_UTF8") from exc
    result=review_basis_linkage(source)
    output={
       "schema":"tbdy.next.vs04f.offline-source-linkage.v1",
       "source_sha256":sha256(raw).hexdigest(),
       "source_byte_count":len(raw),
       "source_raw_included":False,
       "basis_linkage":result,
       "engineering_release":"NOT_READY",
       "formal_compliance":"NOT_PROVEN",
    }
    if out_path.resolve()==source_path.resolve() or out_path.is_symlink() or out_path.exists():
        raise ValueError("REFUSE_OUTPUT_OVERWRITE")
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                        encoding="utf-8")
    return output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args(argv)
    output=replay_basis(args.input,args.out)
    review=output["basis_linkage"]
    print("VS04-F:",review["status"])
    print("Observed source components:",review.get("observed_component_count"),"/",
          review.get("expected_component_count"))
    for comp in review.get("components",[]):
        print(comp["component"],"|",comp["status"],"|",
              ",".join(comp["reason_codes"]),"|",
              ",".join(comp["caution_codes"]))
    print("Source hash:",output["source_sha256"])
    print("Output:",args.out.resolve())
    print("Normative checks executed: 0")
    print("Engineering release: NOT_READY")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
