"""Verify the G3 filing against its original sealed source, stages and accepted G2 decision."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.g2_contract import require
from tbdy_next.engineering.g3_contract import g3_contract, g3_verification
from tbdy_next.engineering.pipeline_snapshot import read_snapshot
from verify_g2_contract import verify as verify_g2


def verify(directory):
    verify_g2(directory)
    raw = archive_bytes(directory/"input.source")
    digest = sha256(raw).hexdigest()
    stages = read_snapshot(directory,input_sha=digest)["results"]
    building = stages["building_design"]
    require(g3_contract(json.loads(raw),stages,building) == building["g3_contract"],"G3_REPLAY_MISMATCH")
    result = g3_verification(directory,building,digest)
    require(result == json.loads((directory/"g3-verification.json").read_bytes()),"G3_VERIFICATION_MISMATCH")
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("run",type=Path)
    print(json.dumps(verify(cli.parse_args().run),indent=2))
