"""Check the two-curtain W55 corridor bound directly against two archived shell corners."""

import argparse
from hashlib import sha256
import json
from math import hypot, pi, sqrt
from pathlib import Path

from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.basement_wall_pressure import clear_limit
from tbdy_next.engineering.pipeline_snapshot import read_snapshot
from tbdy_next.engineering.wall_membrane_design import corner_states
from tbdy_next.engineering.wall_section import reinforced_section


def verify(directory):
    input_sha = sha256(archive_bytes(directory / "input.source")).hexdigest()
    sources = []
    sealed = read_snapshot(directory, input_sha=input_sha, on_verified_source=sources.append)
    if not sealed or len(sources) != 1:
        raise ValueError("A verified whole-building snapshot is required")
    source, = sources
    building = sealed["results"]["building_design"]
    pier = next(row for row in building["wall_sections"]["basement_piers"] if row["pier"] == "yP2")
    panel = next(row for row in pier["geometry"]["panels"] if row["member"] == "464")
    edge = panel["support_sections"]["I"]
    receiving = next(row for row in edge["incident_walls"] if row["member"] == "472")
    if panel["width_direction"] != [0., -1.] or receiving["direction"] != [1., 0.]:
        raise ValueError("The recorded W55 and W6 local axes are required")
    link = next(row["transfer_connection"] for row in pier["two_way_support_layouts"] if row.get("transfer_connection"))
    trial = link["synchronized_trial"]
    w6 = next(row for row in building["wall_boundaries"]["piers"] if "472" in row["member_ids"])
    section, _ = reinforced_section(w6, source["column_axial"])
    stations = sorted({(round(section.t2 / 2 + bar.x2, 9), round(sqrt(4 * bar.area / pi), 9))
                       for bar in section.bars if section.t2 / 2 + bar.x2 >= 0})
    (x1, dia1), (x2, dia2) = stations[:2]
    if dia1 != 14 or dia2 != 14:
        raise ValueError("The two verified Ø14 receiving rows are required")
    cover = w6["transverse_cage"]["cover_mm"]
    tie = w6["transverse_cage"]["tie_diameter_mm"]
    pitch = trial["hoop_pitch_mm"]
    aggregate = pier["maximum_aggregate_mm"]
    clear = clear_limit(aggregate, 14, tie)
    if any(clear_limit(aggregate, d, other) != clear for d in (8, 10, 12, 14) for other in (tie, dia1, d)):
        raise ValueError("The common aggregate-controlled clear distance is required")
    if not (trial["maximum_diameter_by_hoop_mm"] == 14 and
            pitch / 2 - (14 + tie) / 2 >= clear > pitch / 2 - (16 + tie) / 2):
        raise ValueError("Hoop elevations do not limit the crossing catalogue to Ø14")
    # Use two receiving rows only. Other bars can further restrict the lanes.
    half = panel["thickness_m"] * 500
    exclusion = clear + (8 + dia1) / 2
    cells = [(0., x1 - exclusion), (x1 + exclusion, x2 - exclusion)]
    if not (0 < cells[0][1] and cells[1][0] <= cells[1][1] <= half - cover - 4 < x2 + exclusion
            and x2 - x1 < 2 * (clear + (10 + dia1) / 2)):
        raise ValueError("The two positive-face corridors and the Ø8 intermediate limit must hold")
    half_window = pitch / 2 - clear - (8 + tie) / 2
    if any(hypot(high - low, 2 * half_window) >= 8 + clear for low, high in cells):
        raise ValueError("Two crossing bars might fit in a single slot")
    # This physical one-metre interval contains twelve entire admissible windows.
    lower, upper = 87., 1087.
    slots = [k for k in range(1, trial["hoop_count"])
             if k * pitch + half_window >= lower and k * pitch - half_window <= upper]
    if slots != list(range(2, 14)):
        raise ValueError("The guaranteed one-metre count changed")
    case = "Crack_SeisY_Soil"
    member = source["pier_section_forces"]["read"]["pressure_shells"]["members"]["464"]
    field = corner_states(panel, member, {case: {"spectral": True}})[case]
    rows = []
    for element, node in (("464-12", "~5545"), ("464-6", "~5538")):
        (force, moment), = [(n, m) for e, pt, n, m in field if (e, pt) == (element, node)]
        # At global +X (negative local 3), the finite-depth tie check includes
        # h >= w*(Nxx+Nxz) + (Mxx+Mxz)/d. Take the recorded interval upper sides.
        rows.append({"element": element, "node": node, "A_kn_m": force[0][1] + force[2][1],
                     "B_knm_m": moment[0][1] + moment[2][1]})
    bmax = cells[1][1] / 1000
    residuals = [r["B_knm_m"] - bmax * r["A_kn_m"] for r in rows]
    weight = -residuals[1] / (residuals[0] - residuals[1])
    demand = weight * rows[0]["A_kn_m"] + (1 - weight) * rows[1]["A_kn_m"]
    moment = weight * rows[0]["B_knm_m"] + (1 - weight) * rows[1]["B_knm_m"]
    if not 0 < weight < 1 or abs(moment - bmax * demand) > 1e-8:
        raise ValueError("The two native corners do not certify the depth-independent lower bound")
    detail = panel["two_way_shell"]["proposed_detail"]
    horizontal = detail["horizontal"]
    cap = next(r["resistance_kn_m"] for r in detail["membrane_and_plate"]["checks"]
               if r["action"] == "Horizontal steel")
    fyd = cap * 1000 / (horizontal["guaranteed_bars_per_m"] * pi * horizontal["diameter_mm"]**2 / 4)
    capacity = len(slots) * pi * (14**2 + 8**2) * fyd / 4000
    return {"run_id": directory.name, "input_sha256": input_sha, "combination": case,
            "scope": "Uniform two-curtain sandwich with unequal offsets. All +X bars cross the registered W6 boundary row.",
            "positive_corridors_mm": cells, "positive_max_centroid_m": bmax, "crossing_diameters_mm": [14, 8],
            "max_one_per_slot": True, "midpoint_half_window_mm": half_window,
            "witness_interval_mm": [lower, upper], "possible_midpoint_indices": slots,
            "native_halfspaces": rows, "convex_weight_on_first_row": weight, "combined_B_knm_m": moment,
            "identity": "For opposite offsets a and b in metres, d=a+b, w=a/d and w+bmax/d >= 1.",
            "minimum_design_force_kn_m": demand, "steel_grade_design_mpa": fyd,
            "optimistic_positive_resistance_kn_m": capacity, "available_at_selection_limit_kn_m": trial["selection_limit"] * capacity,
            "minimum_utilization": demand / capacity, "selection_limit": trial["selection_limit"],
            "exceeds_selection_limit": demand > trial["selection_limit"] * capacity}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = verify(args.run)
    result = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf8")
    print(result)
