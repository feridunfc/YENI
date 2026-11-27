"""Replay and verify the original G4 scope and outcomes from the sealed run."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.g1_contract import require
from tbdy_next.engineering.g4_contract import g4_contract,g4_verification
from tbdy_next.engineering.g4_population import freeze_population
from tbdy_next.engineering.pipeline_snapshot import read_snapshot
from verify_g3_contract import verify as verify_g3


def verify(directory):
    verify_g3(directory)
    raw=archive_bytes(directory/"input.source")
    source=json.loads(raw)
    digest=sha256(raw).hexdigest()
    stages=read_snapshot(directory,input_sha=digest)["results"]
    building=stages["building_design"]
    frozen=freeze_population(source,digest)
    require(frozen==json.loads((directory/"g4-expected.json").read_bytes()),"G4_PREFROZEN_INSTANCE_REPLAY")
    reviewed = "supervisor_acceptance" in building["g4_contract"]
    require(g4_contract(source,stages,building,frozen,apply_review=reviewed)==building["g4_contract"],"G4_OUTCOME_REPLAY")
    result=g4_verification(directory,building,digest)
    require(result==json.loads((directory/"g4-verification.json").read_bytes()),"G4_VERIFICATION_CHANGED")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    print(json.dumps(verify(parser.parse_args().run),indent=2))
