"""Reopen the sealed pipeline result and reproduce its G2 evidence without solving the model."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.g2_contract import g2_contract, require, verification_record
from tbdy_next.engineering.pipeline_snapshot import read_snapshot


def verify(directory):
    input_sha=sha256(archive_bytes(directory/"input.source")).hexdigest()
    sources=[]
    sealed=read_snapshot(directory,input_sha=input_sha,on_verified_source=sources.append)
    require(bool(sealed) and len(sources)==1,"SEALED_SOURCE_AND_TERMINAL_REQUIRED")
    building=sealed["results"]["building_design"]
    require(building["g2_contract"]==g2_contract(building["g1_contract"],sources[0],sealed["results"]["r08_local_slenderness"]),"G2_REPLAY_MISMATCH")
    verification=verification_record(directory,building,input_sha)
    require(verification==json.loads((directory/"g2-verification.json").read_bytes()),"G2_VERIFICATION_RECORD_MISMATCH")
    return verification


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("run",type=Path)
    print(json.dumps(verify(cli.parse_args().run),indent=2))
