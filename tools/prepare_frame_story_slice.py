"""Extend a sealed original-building frame design using the target storey and its original assigned loads."""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import json
from math import fsum, isclose
from pathlib import Path

from prepare_axial_idealization_scenario import read_scenario_run
from tbdy_next.column_engine.native_archive import decode
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.column_engine.ts500_column import (
    SWAY_PERMITTED, effective_length_factor, effective_stiffness_nmm2, euler_load_kn, rectangle_properties,
)
from tbdy_next.engineering.column_clear_length import proven_clear_length_m
from tbdy_next.engineering.column_effective_length import reference_end_ratios
from tbdy_next.engineering.column_pmm_section import MECHANICAL, _named_row, _rows
from tbdy_next.engineering.column_r10_live import _build_frame_catalog
from tbdy_next.engineering.design_scenario import create_design_scenario
from tbdy_next.engineering.second_order_basis import (
    AXIAL_IDEALIZATION_APPLICABILITY, AXIAL_IDEALIZATION_METHOD, SWAY_POLICY,
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def lateral_directions(frame):
    """Map bending about local 2/3 to the orthogonal horizontal storey direction."""
    axes = frame.get("axes_global")
    if not axes or abs(axes[0][2] - 1.0) > 1e-8:
        return {}
    directions = {}
    for moment, displacement in (("M2", axes[2]), ("M3", axes[1])):
        matches = [name for index, name in enumerate(("X", "Y")) if abs(displacement[index]) >= 1 - 1e-8]
        if len(matches) == 1:
            directions[moment] = matches[0]
    return directions if set(directions.values()) == {"X", "Y"} else {}


def storey_compression(source, physical, groups):
    force_source = source["column_axial"]["force_source"]
    names = set(groups["gravity"]) | set(groups["ductile"])
    sums = defaultdict(list)
    for uid, proof in physical.items():
        require(uid in force_source["rowsets"], f"Missing original storey contributor {uid}")
        cut_steps = defaultdict(lambda: defaultdict(set))
        cuts = set()
        pressures = defaultdict(list)
        for row in native_frame_force_rows(force_source["rowsets"][uid], uid):
            case, step, number, p = row[4:8]
            if case in names:
                require(number == 0, f"Unsupported output step in {uid}/{case}")
                cut = (row[1], row[2], row[3])
                cuts.add(cut)
                cut_steps[case][cut].add(step)
                pressures[case].append(-p)
        ends = proof.get("end_cuts", {})
        require(set(ends) == {"I", "J"} and all(len(end) == 4 and end[0] == uid and tuple(end[1:]) in cuts
                                                for end in ends.values()),
                f"Assigned forces lack a verified physical end cut for {uid}")
        for case in names:
            expected = {"Single Value"} if case in groups["gravity"] else {"Max", "Min"}
            require(cuts and set(cut_steps[case]) == cuts and all(steps == expected for steps in cut_steps[case].values()),
                    f"Missing assigned case, cut or step in {uid}/{case}")
            sums[case].append(max(0.0, max(pressures[case])))
    return {case: fsum(sums[case]) for case in sorted(names)}


def storey_critical_loads(source, storey, physical, ratios, *, allow_wall_hinge):
    """Compute directional Euler sums using the adopted frame-storey assumptions."""
    material_rows = _rows(source["column_axial"]["pmm_section_source"]["table_reads"],
                          MECHANICAL, {"Material"}, {"E1": "kN/m2"})
    loads = defaultdict(list)
    for uid, frame in storey.items():
        length = proven_clear_length_m(physical[uid], uid)
        directions = lateral_directions(frame)
        require(length and directions, f"Storey contributor geometry is unresolved for {uid}")
        modulus = float(_named_row(material_rows, "Material", frame["material_name"], MECHANICAL)["E1"]) / 1000
        dims = frame["dims"]
        section = rectangle_properties(dims.bending_depth_m2_mm, dims.bending_depth_m3_mm)
        for axis, direction in directions.items():
            ends = ratios.get(uid, {}).get(axis, {})
            require(set(ends) == {"I", "J"}, f"Missing storey frame ends for {uid}/{axis}")
            supported_i = ends["I"]["basis"] == "FRAME_SECTION_REFERENCE" or (
                allow_wall_hinge and ends["I"]["basis"] == "WALL_BELOW_ROTATIONAL_STIFFNESS_UNBOUND")
            require(ends["J"]["basis"] == "FRAME_SECTION_REFERENCE" and supported_i,
                    f"Unsupported frame-storey reference end for {uid}/{axis}")
            # The sealed storey calculation assumes a hinge for a wall-supported lower end.
            # A column using this assumption cannot enter the member design extension.
            k = effective_length_factor(alpha_i=ends["I"].get("alpha_web"), alpha_j=ends["J"].get("alpha_web"),
                                        sway=SWAY_PERMITTED)
            inertia = section["i22_mm4"] if axis == "M2" else section["i33_mm4"]
            ei = effective_stiffness_nmm2(ec_mpa=modulus, ic_mm4=inertia, creep_ratio=1, method="TS500_7_21")
            loads[direction].append(euler_load_kn(effective_ei_nmm2=ei, effective_length_lk_mm=1000 * length * k))
    return {direction: fsum(values) for direction, values in loads.items()}


def frame_storey(source, frames, local, story, groups, *, allow_wall_hinge):
    storey = {uid: frame for uid, frame in frames.items() if frame["type"] == "Column" and frame["story"] == story}
    rows = source["geometry_capture"]["tables"]["COLUMN_CONNECTIVITY"]["rows"]
    expected = [r["UniqueName"] for r in rows if r["Story"] == story]
    require(storey and len(expected) == len(storey) and set(expected) == storey.keys() and storey.keys() <= local.keys(),
            f"Incomplete physical column census on storey {story}")
    physical = {uid: local[uid]["physical_clear_length"] for uid in storey}
    ratios = reference_end_ratios(source, physical)
    nd = storey_compression(source, physical, groups)
    nk = storey_critical_loads(source, storey, physical, ratios, allow_wall_hinge=allow_wall_hinge)
    return storey, physical, ratios, nd, nk


def prepare(parent, prior, results, *, anchor, story, labels, scenario_id, derive_storey=False):
    source = decode(parent)
    frames, _, _ = _build_frame_catalog(source)
    require(anchor in frames and frames[anchor]["type"] == "Column", "Anchor must be a physical column")
    anchor_story = frames[anchor]["story"]
    require(derive_storey or anchor_story == story, "The anchor and requested columns must share a storey")
    members = prior["second_order_basis"]["members"]
    require(anchor in members, "Anchor column has no recorded second-order basis")
    anchor_row = next((row for row in results["r14_closure"]["columns"] if row["member_id"] == anchor), {})
    context = anchor_row.get("pillars", {}).get("second_order_selected_pmm", {}).get("adopted_calculation_context")
    require(anchor_row.get("status") == "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES" and context,
            "Anchor requires a finished conditional R14 calculation")
    reference = members[anchor]
    groups = source["column_axial"]["request"]["design_assignment"]["groups"]
    require(prior["second_order_basis"]["global_factor_policy"] == SWAY_POLICY
            and prior["second_order_basis"]["source_analysis_order"] == "FIRST_ORDER"
            and reference["applicability"] == AXIAL_IDEALIZATION_APPLICABILITY
            and reference["axial_idealization"]["method"] == AXIAL_IDEALIZATION_METHOD
            and set(reference["axial_idealization"]["combinations"]) == set(groups["gravity"]),
            "The source must carry the first-order self-weight Nmax frame scenario")
    anchor_dirs = lateral_directions(frames[anchor])
    require(set(anchor_dirs) == {"M2", "M3"}, "Anchor requires identifiable horizontal bending directions")
    story_axes = {direction: reference["axes"][axis] for axis, direction in anchor_dirs.items()}
    require(all((a["sway"], a["creep_ratio_rm"], a["ei_method"], a["cm_policy"], a["eq729_length_reading"])
                == (SWAY_PERMITTED, 1.0, "TS500_7_21", "UNITY", "EFFECTIVE_LENGTH") for a in story_axes.values()),
            "Anchor calculation assumptions differ from the supported frame slice")
    local = results["r08_local_slenderness"]["per_member"]
    storey, physical, ratios, nd, nk = frame_storey(source, frames, local, anchor_story, groups, allow_wall_hinge=True)
    for direction, config in story_axes.items():
        totals = config["story_aggregates"]
        require(totals.keys() == nd.keys(), "Anchor storey cases differ from the native assignment")
        for case, aggregate in totals.items():
            require(isclose(aggregate["nd_kn"], nd[case], rel_tol=1e-12, abs_tol=1e-8),
                    f"Anchor storey compression differs from original frame forces in {case}")
            require(isclose(aggregate["nk_kn"], nk[direction], rel_tol=1e-12, abs_tol=1e-8),
                    f"Anchor critical load differs from the original frame-storey sum in {direction}")
    if anchor_story != story:
        storey, physical, ratios, nd, nk = frame_storey(source, frames, local, story, groups, allow_wall_hinge=False)
        # Carry the adopted method only. Replace all load and stiffness totals for both target directions.
        story_axes = {
            direction: {**config, "story_aggregates": {
                case: {"nd_kn": load, "nk_kn": nk[direction],
                       "reference": f"Conditional frame-only TS500 (7.27), {story}, {direction}, {case}. "
                                    f"All {len(storey)} original columns; same-case upper compression; "
                                    "two model-derived web-reference ends, Eq. 7.21, Rm=1."}
                for case, load in nd.items()}}
            for direction, config in story_axes.items()
        }
    scope = {f["label"]: uid for uid, f in storey.items()}
    require(len(scope) == len(storey) and labels and len(set(labels)) == len(labels)
            and set(labels) <= set(scope), "Supply distinct physical column labels on the requested storey")
    new = deepcopy(prior)
    new["scenario_id"] = scenario_id
    basis = new["second_order_basis"]
    prior_scope = set(basis["members"])
    basis["basis_id"] = scenario_id
    roster = []
    for label in labels:
        uid = scope[label]
        row = {"label": label, "member_id": uid}
        roster.append(row)
        if uid in prior_scope:
            row["disposition"] = "EXISTING_BASIS_RETAINED"
            continue
        directions = lateral_directions(storey[uid])
        by_axis = ratios.get(uid, {})
        if proven_clear_length_m(physical[uid], uid) is None:
            row["disposition"] = physical[uid]["status"]
            continue
        if not directions:
            row["disposition"] = "HORIZONTAL_STORY_AXES_UNBOUND"
            continue
        missing = {f"{axis}/{end}": by_axis.get(axis, {}).get(end, {}).get("basis", "MISSING")
                   for axis in directions for end in ("I", "J")
                   if by_axis.get(axis, {}).get(end, {}).get("basis") != "FRAME_SECTION_REFERENCE"}
        if missing:
            row.update(disposition="FRAME_END_RESTRAINT_UNBOUND", ends=missing)
            continue
        member = deepcopy(reference)
        member["decision_reference"] = "Original prismatic frame column with two model-derived frame ends on each axis."
        member["axial_idealization"]["decision_reference"] = (
            "Self-weight Nmax for coefficients and local compression at each signed gravity PMM cut.")
        for axis, direction in directions.items():
            ends = by_axis[axis]
            k = effective_length_factor(alpha_i=ends["I"]["alpha_web"], alpha_j=ends["J"]["alpha_web"],
                                        sway=SWAY_PERMITTED)
            # Only the same-storey global-direction totals and method are shared. Each member supplies its own k.
            member["axes"][axis] = {**deepcopy(story_axes[direction]), "k": k,
                "k_source": {"method": "FRAME_END_RATIOS", "section": "alpha_web"},
                "decision_reference": "Both current frame ends, rectangular beam web reference, sway permitted and Rm=1."}
        basis["members"][uid] = member
        row["disposition"] = "FRAME_BASIS_REQUESTED"
    require(set(basis["members"]) > prior_scope, "The selected population adds no supported frame member")
    create_design_scenario(parent, new)
    return new, roster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-run", type=Path, required=True)
    parser.add_argument("--anchor", required=True, help="ETABS unique ID of the existing conditional design")
    parser.add_argument("--story", required=True)
    parser.add_argument("--derive-storey", action="store_true",
                        help="Use the anchor method on another storey and derive all its forces and critical loads")
    parser.add_argument("--columns", nargs="+", required=True, help="Physical labels on the requested storey")
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        parent, prior, _, snapshot = read_scenario_run(args.from_run)
        request, roster = prepare(parent, prior, snapshot["results"], anchor=args.anchor, story=args.story,
                                  labels=args.columns, scenario_id=args.scenario_id, derive_storey=args.derive_storey)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf8") as stream:
            json.dump(request, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        print(json.dumps({"story": args.story, "columns": roster, "scenario": str(args.out)}, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Frame design request rejected: {error}\n")


if __name__ == "__main__":
    main()
