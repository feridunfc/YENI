"""Conditional TS 500 frame restraint references from verified model geometry."""
from math import fsum, isclose, ulp

from ..column_engine.ts500_column import (
    SWAY_PERMITTED, SWAY_PREVENTED, effective_length_factor, eq729_length_comparison,
    euler_load_kn, evaluate_slenderness,
)
from .column_clear_length import proven_clear_length_m
from .frame_geometry import build_frame_catalog


def _within_axis(a, b):
    return isclose(abs(fsum(x*y for x, y in zip(a, b))), 1.0, rel_tol=0, abs_tol=1e-8)


def _flanged_i(width, depth, thickness, length):
    """Comparison with the maximum two-sided flange in this assumed slab thickness."""
    if not 0 < thickness < depth:
        return width * depth**3 / 12
    overhang = min(6 * thickness, .15 * length)
    flange_width = width + 2 * overhang
    web_depth = depth - thickness
    area_web, area_flange = width * web_depth, flange_width * thickness
    y_web, y_flange = web_depth/2, depth - thickness/2
    center = (area_web*y_web + area_flange*y_flange) / (area_web + area_flange)
    return (width*web_depth**3/12 + area_web*(y_web-center)**2
            + flange_width*thickness**3/12 + area_flange*(y_flange-center)**2)


def reference_end_ratios(source, physical_members):
    """Use axis lengths in I/L; keep the proof's face length for k*ln."""
    if not any(proven_clear_length_m(row, uid) for uid, row in physical_members.items()):
        return {}
    frames, _, meta = build_frame_catalog(source)
    table = source["geometry_capture"]["tables"].get("FRAME_ASSIGNMENTS") or {}
    if table.get("field_metadata", {}).get("units_by_field", {}).get("Length") != "m":
        return {}
    lengths = {r["UniqueName"]: float(r["Length"]) for r in table["rows"] if r.get("Type") in {"Beam", "Column"}
               and r.get("UniqueName") in frames and r.get("Length") not in (None, "", "None")}
    result = {}
    for uid, proof in physical_members.items():
        if proven_clear_length_m(proof, uid) is None or uid not in frames:
            continue
        target = frames[uid]
        if target["axes_global"] is None or not target["material_name"]:
            continue
        ratio_axes = {}
        for axis, i_axis, transverse in (("M2", 1, 2), ("M3", 2, 1)):
            ends = {}
            for side, face in proof.get("faces", {}).items():
                if face.get("walls_below"):
                    ends[side] = {"basis": "WALL_BELOW_ROTATIONAL_STIFFNESS_UNBOUND",
                                  "joint_id": face["joint_id"]}
                    continue
                if not face["beams"]:
                    if any(s["type"] == "Mat" for s in face["slabs"]):
                        ends[side] = {"basis": "MAT_ROTATIONAL_STIFFNESS_UNBOUND", "joint_id": face["joint_id"]}
                    continue
                terms = []
                thickness = max((s["thickness_m"] for s in face["slabs"]), default=0)
                for end in meta["adjacency"].get(face["joint_id"], ()):
                    name = end["frame_id"]
                    frame = frames[name]
                    dims, axes, length = frame["dims"], frame["axes_global"], lengths.get(name)
                    if (dims is None or axes is None or not length or length <= 0
                            or frame["material_name"] != target["material_name"]):
                        break
                    d2, d3 = dims.local2_extent_mm / 1000, dims.local3_extent_mm / 1000
                    if frame["type"] == "Column":
                        if _within_axis(axes[1], target["axes_global"][i_axis]):
                            inertia = d2 * d3**3 / 12
                        elif _within_axis(axes[2], target["axes_global"][i_axis]):
                            inertia = d3 * d2**3 / 12
                        else:
                            break
                        web = flange = inertia / length
                    elif _within_axis(axes[0], target["axes_global"][transverse]):
                        web = .5 * d3 * d2**3 / 12 / length
                        flange = .5 * _flanged_i(d3, d2, thickness, length) / length
                    elif _within_axis(axes[0], target["axes_global"][i_axis]):
                        continue
                    else:
                        break
                    terms.append({"id": name, "end": end["end"], "type": frame["type"], "axis_length_m": length,
                                  "web_i_over_l_m3": web, "flange_comparison_i_over_l_m3": flange})
                else:
                    cols = fsum(x["web_i_over_l_m3"] for x in terms if x["type"] == "Column")
                    beams = [x for x in terms if x["type"] == "Beam"]
                    if cols > 0 and beams:
                        ends[side] = {"basis": "FRAME_SECTION_REFERENCE", "joint_id": face["joint_id"], "terms": terms,
                                      "alpha_web": cols / fsum(x["web_i_over_l_m3"] for x in beams),
                                      "alpha_flange_comparison": cols / fsum(x["flange_comparison_i_over_l_m3"] for x in beams)}
            if set(ends) == {"I", "J"} and any("alpha_web" in e for e in ends.values()):
                ratio_axes[axis] = ends
        if ratio_axes:
            result[uid] = ratio_axes
    return result


def resolve_adopted_frame_k(axis_basis, ends):
    """Recompute an explicitly selected, fully bound two-frame-end reference.

    A mat/wall rotation is never substituted with a guessed fixed or hinged
    end. Those conditional external restraint decisions use explicit adopted
    K and a decision reference instead of this narrow source selection.
    """
    selection = axis_basis.get("k_source")
    if selection is None:
        return axis_basis["k"], None
    if (set(ends or {}) != {"I", "J"}
            or any(ends[side].get("basis") != "FRAME_SECTION_REFERENCE" for side in ("I", "J"))):
        raise ValueError("ADOPTED_K_REQUIRES_TWO_BOUND_FRAME_END_RATIOS")
    field = selection["section"]
    if any(field not in ends[side] for side in ("I", "J")):
        raise ValueError("ADOPTED_K_FRAME_SECTION_REFERENCE_MISSING")
    alpha_i, alpha_j = (ends[side][field] for side in ("I", "J"))
    k = effective_length_factor(alpha_i=alpha_i, alpha_j=alpha_j, sway=axis_basis["sway"])
    if abs(k - axis_basis["k"]) > 8 * max(ulp(k), ulp(axis_basis["k"])):
        raise ValueError("ADOPTED_K_VALUE_CONFLICTS_WITH_CURRENT_FRAME_REFERENCE")
    return k, {"status": "CURRENT_FRAME_REFERENCE_CONSUMED", "method": selection["method"], "section": field,
               "sway": axis_basis["sway"], "alpha_i": alpha_i, "alpha_j": alpha_j, "computed_k": k,
               "ends": ends, "engineering_approval": "NOT_GRANTED"}


def effective_length_reference(axes, local, section_evidence):
    """Sensitivity cases never modify PMM demand, global stability or approved restraint."""
    out = {}
    fck = section_evidence["fck_mpa"]
    area = section_evidence["native_t2_mm"] * section_evidence["native_t3_mm"]
    for axis, ends in axes.items():
        stiffness = local["stiffness_and_euler"][axis]
        ln = local["candidate_span_mm"]
        radius = stiffness["radius_mm"]
        ei = stiffness.get("selected_ei_ts500_7_20_nmm2") or stiffness["ei_ts500_7_21_nmm2"]
        cases = []
        for section in ("alpha_web", "alpha_flange_comparison"):
            i, j = (ends[side].get(section) for side in ("I", "J"))
            hypotheses = [("FRAME_JOINTS", i, j)]
            if i is None or j is None:
                unresolved = ends["I" if i is None else "J"].get("basis")
                label = "WALL" if unresolved == "WALL_BELOW_ROTATIONAL_STIFFNESS_UNBOUND" else "MAT"
                hypotheses = [(label + "_FIXED", 0.0 if i is None else i, 0.0 if j is None else j),
                              (label + "_HINGED", i, j)]
            for support, a, b in hypotheses:
                for sway in (SWAY_PREVENTED, SWAY_PERMITTED):
                    k = effective_length_factor(alpha_i=a, alpha_j=b, sway=sway)
                    length = evaluate_slenderness(free_length_ln_mm=ln, k=k, radius_mm=radius, sway=sway)
                    checks = []
                    for combo in local["combination_scenarios"]:
                        nd = combo["governing_nd_kn"]
                        if nd > 0 and sway == SWAY_PERMITTED:
                            checks.append({"combination":combo["combination"],
                                           **eq729_length_comparison(free_length_ln_mm=ln,
                                               effective_length_lk_mm=length["lk_mm"], radius_mm=radius, nd_kn=nd,
                                               fck_mpa=fck, area_mm2=area)})
                    cases.append({"section":section,"support":support,"sway":sway,
                                  "assumed_end_alpha": {"I": a, "J": b}, **length,
                                  "nk_rm0_kn":euler_load_kn(effective_ei_nmm2=ei, effective_length_lk_mm=length["lk_mm"]),
                                  "eq729_reference": checks})
        out[axis] = {"ends": ends, "cases": cases}
    return {"status": "CONDITIONAL_FRAME_END_RESTRAINT_REFERENCE",
            "assumptions": ["Common concrete modulus, uncracked columns, and 0.5 gross beam inertia.",
                            "Beam continuity and flange transfer are scenario assumptions.",
                            "The flange comparison uses the largest slab thickness at the joint and two maximum overhangs.",
                            "Euler results use Rm=0. The sway class and unbound support rotation remain conditional."],
            "axes": out}
