"""Reproduce the G3 section evidence independently from a sealed original-building result."""
import argparse
from functools import lru_cache
from hashlib import sha256
import json
from math import acos, pi, sqrt
from pathlib import Path
import sys

from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.g3_capacity import section_inputs, compare_reference
from tbdy_next.engineering.pipeline_snapshot import read_snapshot

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tests"))
from g2_section_oracle import independent_capacity


@lru_cache(maxsize=2048)
def beam_capacity(width, height, fck, fcd, fyd, es, bars, sign):
    """Independently integrate an axis-aligned C35 compression block and circular bar intersections."""
    if fck != 35 or sign not in (-1,1) or not bars:
        raise ValueError("Expected C35 beam with scheduled reinforcement")
    lo,hi = 0.,height*10
    for _ in range(60):
        c = (lo+hi)/2
        block = min(height,.79*c)
        boundary = height/2-block
        stress = .85*fcd
        n = width*block*stress
        moment = n*(height-block)/2
        max_tension = 0.
        for x, y, dia, area in bars:
            r = dia/2
            if abs(area-pi*r*r)>1.e-7 or abs(y)+r>width/2 or abs(x)+r>height/2:
                raise ValueError("Beam bar outside supplied geometry or area inconsistent")
            q = sign*x
            strain = .003*(1-(height/2-q)/c)
            max_tension = max(max_tension,-strain)
            z = boundary-q
            displaced,first = 0.,0.
            if z <= -r:
                displaced = area
            elif z < r:
                h = sqrt(max(0.,r*r-z*z))
                displaced = r*r*acos(z/r)-z*h
                first = 2*h**3/3
            force = area*max(-fyd,min(fyd,es*strain))-stress*displaced
            n += force
            moment += q*force-stress*first
        if n < 0:
            lo = c
        else:
            hi = c
    return {"capacity_knm":sign*moment/1.e6,"axial_residual_n":abs(n),"maximum_tensile_strain":max_tension}


def reproduce(directory):
    data = archive_bytes(directory/"input.source")
    input_sha = sha256(data).hexdigest()
    st = read_snapshot(directory,input_sha=input_sha)["results"]
    basis = section_inputs(json.loads(data),st,st["building_design"])
    methods = ("tests/g2_section_oracle.py","tools/verify_g3_sections.py")
    result = {"schema":"tbdy.next.g3-section-reference.v1","source_sha256":input_sha,
              "independent_methods_sha256":{k:sha256((ROOT/k).read_text(encoding="utf-8").encode()).hexdigest() for k in methods},
              "input_basis_sha256":_digest(basis),"columns":{},"beams":{}}
    for uid,row in basis["columns"].items():
        section = row["section"]
        area = section["t2_mm"]*section["t3_mm"]
        check = {"ts500_limit_kn":.9*section["fcd_mpa"]*area/1000,
                 "tbdy_limit_kn":.4*section["fck_mpa"]*area/1000}
        for kind,cut in row["cuts"].items():
            check[kind] = independent_capacity(section,row["cage"],cut)
        result["columns"][uid] = check
    for uid,beam in basis["beams"].items():
        ends = {}
        for side,end in beam["ends"].items():
            bars = tuple(tuple(b[k] for k in ("x2_mm","x3_mm","diameter_mm","area_mm2")) for b in end["bars"])
            ends[side] = {name:beam_capacity(beam["width_mm"],beam["height_mm"],beam["fck_mpa"],
                         beam["fcd_mpa"],beam["fyd_mpa"],beam["es_mpa"],bars,sign)
                         for name,sign in (("positive",1),("negative",-1))}
        result["beams"][uid] = ends
    report = compare_reference(basis,result)
    return result,report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("run",type=Path)
    cli.add_argument("--write-reference",type=Path)
    args = cli.parse_args()
    result,report = reproduce(args.run)
    if args.write_reference:
        args.write_reference.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    else:
        reference = json.loads((ROOT/"src/tbdy_next/verification/data/g3_section_reference.json").read_bytes())
        if reference != result:
            raise ValueError("Recomputed independent section reference differs")
    print(json.dumps(report,indent=2))
