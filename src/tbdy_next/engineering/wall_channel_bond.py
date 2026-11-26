"""A statically admissible shell tie field with bounded stress change across a short link."""
from math import hypot

from .wall_membrane_design import SELECTION_LIMIT


def _face(membrane, plate, sign, arm):
    ranges = []
    for (low, high), (ml, mh) in zip(membrane, plate[:3]):
        a, b = -sign * ml / arm, -sign * mh / arm
        ranges.append((low / 2 + min(a,b), high / 2 + max(a,b)))
    nx, ny, shear = ranges
    tau = max(map(abs,shear))
    return nx[0], max(0.,nx[1]+tau), max(-nx[0],tau), max(-ny[0],tau), tau


def combined_bond(states, edges, arm_mm, thickness, material, steel, length, development):
    """Increase the smaller tie force where necessary and equilibrate the additional compression.

    If the two required total tensions are a and b, adopt max(a,b-D) and max(b,a-D).
    They differ by at most the developed stress increment D. Added horizontal tie force
    is balanced by compression at the same lever arm. Bound its concrete stress at every
    native element/node, on both faces and in either direction of transfer.
    """
    face_strength = .6*(1-material.fck/250)*material.fcd
    core_strength = .65*.35*material.fck**.5*material.fcd/material.fck
    developed = steel*min(1., length/development)
    grids = [{c["combination"]:c["tension_intervals"] for c in edges[s]["cuts"]} for s in ("I","J")]
    if not states or any(g.keys()!=states.keys() for g in grids):
        raise ValueError("LINK_SHELL_AND_FRICTION_CASE_MISMATCH")
    rows=[]
    for name, native in states.items():
        corners={(elm,node):(m,p) for elm,node,m,p in native}
        if len(corners)!=len(native):
            raise ValueError("DUPLICATE_LINK_SHELL_CORNER")
        seen=set()
        peak=None
        left,right=(g[name] for g in grids)
        if len(left)!=len(right):
            raise ValueError("LINK_ELEVATION_CENSUS_MISMATCH")
        for a,b in zip(left,right):
            ai,bi=a["element_intervals"],b["element_intervals"]
            if not ai or ai.keys()!=bi.keys() or abs(a["z_m"]-b["z_m"])>1.e-8:
                raise ValueError("LINK_PHYSICAL_SLICES_DIFFER")
            # |max X_i - max Y_i| uses paired indices, even when the maximizing index changes.
            for here,there,local,other in ((a,b,ai,bi),(b,a,bi,ai)):
                friction_jump=max(other[k][1]-local[k][0] for k in local)/1.2
                for elm,node in corners:
                    if node!=here["node"]:
                        continue
                    seen.add((elm,node))
                    m,p=corners[elm,node]
                    om,op=corners[elm,there["node"]]
                    shear=hypot(max(map(abs,p[3])),max(map(abs,p[4])))
                    for sign in (-1,1):
                        nx,hi,cx,cy,tau=_face(m,p,sign,arm_mm/1000)
                        _,other_high,*_=_face(om,op,sign,arm_mm/1000)
                        cx=max(cx, other_high + friction_jump - developed - nx)
                        c=.5*(cx+cy+hypot(cx-cy,2*tau))/face_strength
                        q=shear/core_strength
                        floor_t=min(.5,thickness-arm_mm,arm_mm/2)
                        t=min(thickness-arm_mm,arm_mm-floor_t,max(floor_t,arm_mm*c/(c+q) if c+q else arm_mm/2))
                        ratio=max(c/t,q/(arm_mm-t))
                        descriptor={"combination":name,"element":elm,"node":node,"receiving_face":sign,
                                    "face_thickness_mm":t,"core_thickness_mm":arm_mm-t,
                                    "face_concrete_ratio":c/t,"core_shear_ratio":q/(arm_mm-t),
                                    "utilization":ratio}
                        if peak is None or ratio>peak["utilization"]:
                            peak=descriptor
        if seen!=corners.keys() or peak is None:
            raise ValueError("INCOMPLETE_LINK_OPPOSITE_CORNER_CENSUS")
        rows.append({**peak,"native_corners":len(seen)})
    return {"method":"OPPOSITE_ELEMENT_CORNERS_BOUNDED_TOTAL_TIE_INCREMENT","available_length_mm":length,
            "yield_development_mm":development,"allowed_total_tension_change_kn_m":developed,
            "governing":max(rows,key=lambda r:r["utilization"]),"combinations":rows,
            "satisfied":all(r["utilization"]<=SELECTION_LIMIT for r in rows)}
