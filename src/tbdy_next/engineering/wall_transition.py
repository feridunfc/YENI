"""Physical sections, opening loads and signed frame transfer at changes of wall membership."""

from collections import defaultdict
from itertools import pairwise
from math import dist, fsum, isclose, isfinite
import re

from ..column_engine.source_bank import native_frame_force_rows
from .basement_pier_geometry import required
from .basement_wall_pressure import pressure_cases
from .mixed_demands import _static_pattern_loads, linear_coefficients, native_graph

FRAME_COMPONENTS = ("P", "V2", "V3", "T", "M2", "M3")
GLOBAL_COMPONENTS = ("FX", "FY", "FZ", "MX", "MY", "MZ")
TOL = 2e-5  # Coordinates in the native mesh table are reported to 0.00001 m.


def mesh_geometry(source):
    tables = source["column_axial"]["r10_source"]["table_reads"]
    coords = {
        r["ElmName"]: tuple(float(r["Global" + a]) for a in "XYZ")
        for r in tables["Objects and Elements - Joints"]["rows"]
    }
    areas = defaultdict(dict)
    for r in tables["Objects and Elements - Areas"]["rows"]:
        if r["ObjType"] != "Wall":
            continue
        uid, elm = r["ObjName"], r["ElmName"]
        nodes = tuple(
            r[k] for k in ("ElmJt1", "ElmJt2", "ElmJt3", "ElmJt4") if r.get(k) not in (None, "", "None")
        )
        required(
            elm not in areas[uid]
            and len(nodes) in (3, 4)
            and len(set(nodes)) == len(nodes)
            and all(n in coords for n in nodes),
            "WALL_ANALYSIS_MESH_UNRESOLVED",
        )
        areas[uid][elm] = nodes
    return coords, areas


def changes(profile):
    for below, above in pairwise(profile["bands"]):
        lower, upper = set(below["members"]), set(above["members"])
        if lower != upper:
            yield below, above, sorted(lower ^ upper)


def _cut_edges(member, z, face, length, mesh, coords):
    """A native section exists only on a complete contiguous line of element edges."""
    segments, corners = [], []
    for elm, nodes in mesh[member].items():
        heights = [coords[n][2] for n in nodes]
        end = min(heights) if face == "Bottom" else max(heights)
        if abs(end - z) > TOL or max(heights) - min(heights) <= TOL:
            continue
        for a, b in zip(nodes, nodes[1:] + nodes[:1]):
            if max(abs(coords[n][2] - z) for n in (a, b)) <= TOL:
                segments.append((coords[a][:2], coords[b][:2]))
                corners.extend(((elm, a), (elm, b)))
    if not segments:
        return []
    points = [p for segment in segments for p in segment]
    axis = max((0, 1), key=lambda i: max(p[i] for p in points) - min(p[i] for p in points))
    intervals = sorted(tuple(sorted((a[axis], b[axis]))) for a, b in segments)
    if any(abs(right[0] - left[1]) > TOL for left, right in pairwise(intervals)) or not isclose(
        fsum(dist(a, b) for a, b in segments), length, rel_tol=1e-6, abs_tol=TOL
    ):
        return []
    return corners


def section_plan(band, z, side, lengths, mesh, coords):
    members = band["members"]
    levels = None
    for uid in members:
        available = {
            coords[n][2]
            for nodes in mesh.get(uid, {}).values()
            for n in nodes
            if band["bottom_m"] - TOL <= coords[n][2] <= band["top_m"] + TOL
        }
        levels = available if levels is None else levels & available
    for level in sorted(levels or (), key=lambda v: abs(v - z)):
        face = "Top" if side == "Below" else "Bottom"
        if abs(level - band["bottom_m"]) <= TOL:
            face = "Bottom"
        elif abs(level - band["top_m"]) <= TOL:
            face = "Top"
        corners = {uid: _cut_edges(uid, level, face, lengths[uid], mesh, coords) for uid in members}
        if all(corners.values()):
            return {
                "z_m": level,
                "element_face": face,
                "at_transition": abs(level - z) <= TOL,
                "members": members,
                "corners": corners,
            }
    return {"members": members, "reason": "COMMON_ANALYSIS_SECTION_UNAVAILABLE", "corners": {}}


def weighted_vectors(rows):
    return [fsum(factor * vector[i] for factor, vector in rows) for i in range(6)]


def _jamb_forces(source, context, story, point, cases, seismic):
    xyz = context[0]
    target = xyz[point]
    tables = source["column_axial"]["r10_source"]["table_reads"]
    coords = {
        r["ElmName"]: tuple(float(r["Global" + a]) for a in "XYZ")
        for r in tables["Objects and Elements - Joints"]["rows"]
    }
    matches = [
        r
        for r in context[7]
        if r["Story"] == story
        and all(dist(xyz[r[key]][:2], target[:2]) <= TOL for key in ("UniquePtI", "UniquePtJ"))
        and xyz[r["UniquePtI"]][2] < target[2] < xyz[r["UniquePtJ"]][2]
    ]
    if not matches:
        return {"point": point, "status": "NO_THROUGH_COLUMN"}
    required(len(matches) == 1, "UNIQUE_THROUGH_COLUMN_REQUIRED")
    col = matches[0]
    uid = col["UniqueName"]
    parts = [
        r
        for r in tables["Objects and Elements - Frames"]["rows"]
        if r["ObjType"] == "Frame" and r["ObjName"] == uid
    ]
    pairs = [
        (a, b)
        for a in parts
        for b in parts
        if a["ElmJtJ"] == b["ElmJtI"]
        and dist(coords[a["ElmJtJ"]], target) <= TOL
        and all(dist(coords[r[k]][:2], target[:2]) <= TOL for r, k in ((a, "ElmJtI"), (b, "ElmJtJ")))
        and coords[a["ElmJtI"]][2] < target[2] < coords[b["ElmJtJ"]][2]
    ]
    required(len(pairs) == 1, "TWO_ADJACENT_FRAME_ELEMENTS_AT_PHYSICAL_SECTION_REQUIRED")
    lo, hi = pairs[0]
    station = dist(xyz[col["UniquePtI"]], target)
    bank = source["column_axial"]["demand_support"]["force_source"]
    required(
        bank["units_code"] == 6
        and not bank["errors"]
        and bank["output_selection_before"] == bank["output_selection_after"],
        "SIGNED_FRAME_SOURCE_OR_SELECTION_UNQUALIFIED",
    )

    def at_point(raw, steps):
        indexed = defaultdict(dict)
        for _, x, elm, ex, case, step, number, *v in native_frame_force_rows(raw, uid):
            if abs(x - station) > TOL or elm not in (lo["ElmName"], hi["ElmName"]) or step not in steps:
                continue
            local_end = dist(coords[lo["ElmJtI"]], coords[lo["ElmJtJ"]]) if elm == lo["ElmName"] else 0.0
            required(
                abs(ex - local_end) <= TOL and all(isfinite(n) for n in v), "COLUMN_FACE_STATION_MISMATCH"
            )
            k = case, step, number
            required(elm not in indexed[k], "DUPLICATE_COLUMN_FACE")
            indexed[k][elm] = v
        return indexed

    primitive = at_point(bank["rowsets"][uid], {"Single Value", "Max"})
    direct = at_point(source["column_axial"]["force_source"]["rowsets"][uid], {"Single Value"})
    result = {
        "point": point,
        "analysis_joint": lo["ElmJtJ"],
        "column": uid,
        "label": col.get("ColumnBay"),
        "elements": [lo["ElmName"], hi["ElmName"]],
        "component_order": FRAME_COMPONENTS,
        "status": "NATIVE_COLUMN_FACE_ACTIONS",
        "combinations": [],
        "seismic_bounds": [],
    }
    for name, factors in cases.items():
        rec = {"combination": name}
        result["combinations"].append(rec)
        try:
            faces = [
                weighted_vectors(
                    [(float(f), primitive[k, "Single Value", 0][elm]) for k, f in factors.items()]
                )
                for elm in result["elements"]
            ]
            check = direct.get((name, "Single Value", 0))
            if check is not None:
                required(
                    all(
                        isclose(v, x, abs_tol=1e-6, rel_tol=1e-8)
                        for elm, face in zip(result["elements"], faces)
                        for v, x in zip(face, check[elm])
                    ),
                    "NATIVE_COLUMN_COMBINATION_CONTROL_DIFFERS",
                )
            rec.update(
                below=faces[0],
                above=faces[1],
                above_minus_below=[b - a for a, b in zip(*faces)],
                direct_control=check is not None,
            )
        except (KeyError, ValueError) as exc:
            rec["reason"] = str(exc)
    if seismic:
        _, types, graph = native_graph(source)
        for name, static in seismic.items():
            rec = {"combination": name}
            result["seismic_bounds"].append(rec)
            try:
                factors = linear_coefficients(name, graph, types)
                spectra = {k: f for k, f in factors.items() if types[k]["type"] == "Response Spectrum"}
                required(
                    spectra and set(static) | set(spectra) == set(factors),
                    "SIGNED_AND_SPECTRAL_COMPONENTS_REQUIRED",
                )
                ends = result["elements"]
                center = weighted_vectors(
                    [
                        (
                            float(f),
                            [
                                b - a
                                for a, b in zip(
                                    primitive[k, "Single Value", 0][ends[0]],
                                    primitive[k, "Single Value", 0][ends[1]],
                                )
                            ],
                        )
                        for k, f in static.items()
                    ]
                )
                radius = weighted_vectors(
                    [
                        (
                            abs(float(f)),
                            [
                                abs(a) + abs(b)
                                for a, b in zip(
                                    primitive[k, "Max", 0][ends[0]], primitive[k, "Max", 0][ends[1]]
                                )
                            ],
                        )
                        for k, f in spectra.items()
                    ]
                )
                rec.update(
                    minimum=[c - r for c, r in zip(center, radius)],
                    maximum=[c + r for c, r in zip(center, radius)],
                )
            except (KeyError, ValueError) as exc:
                rec["reason"] = str(exc)
    return result


def panel_loads(source, bound, scope, row, panel):
    """Directly imposed panel loads. Attachment forces require their own native read."""
    uid, label, story = panel["member"], panel["label"], row["story"]
    section = source["vs06_b1_geometry_source"]["table_reads"]["Wall Property Definitions - Specified"][
        "rows"
    ]
    prop = next(r for r in section if r["Name"] == panel["section"])
    mechanics = source["column_axial"]["pmm_section_source"]["table_reads"][
        "Material Properties - Basic Mechanical Properties"
    ]["rows"]
    weights = [float(r["UnitWeight"]) for r in mechanics if r["Material"] == panel["material"]]
    required(len(weights) == 1 and weights[0] > 0 and float(prop["WMod"]) >= 0, "WALL_UNIT_WEIGHT_REQUIRED")
    records = [
        line
        for line in bound["deck"].splitlines()
        if re.match(
            r'^\s*AREAASSIGN\s+"' + re.escape(label) + r'"\s+"' + re.escape(story) + r'"(?:\s|$)', line
        )
    ]
    required(
        records
        and not any(
            re.search(r"\b(?:\w*MOD\w*WEIGHT\w*|\w*WEIGHT\w*MOD\w*|WMOD)\b", line, re.I) for line in records
        ),
        "WALL_OBJECT_WEIGHT_MODIFIER_REQUIRES_BINDING",
    )
    area = panel["length_m"] * (panel["top_m"] - panel["bottom_m"])
    weight = area * panel["thickness_m"] * weights[0] * float(prop["WMod"])
    combos, _ = pressure_cases(
        source, bound, scope, row["pier"], story, [{"member": uid, "wall": label}], allow_unloaded=True
    )
    tables, cases, graph = native_graph(source)
    result = []
    for name, c in combos.items():
        terms = scope["native_seismic"].get(name)
        if terms is None:
            terms = linear_coefficients(name, graph, cases)
        patterns, loads = _static_pattern_loads(tables, terms, cases)
        g = fsum(
            float(f * factor) * float(patterns[p]["self_weight_multiplier"])
            for k, f in terms.items()
            for p, factor in loads[k]
        )
        result.append(
            {
                "combination": name,
                "role": c["role"],
                "pressure_kn_m2": c["pressure_kn_m2"][uid],
                "normal_force_kn": area * c["pressure_kn_m2"][uid],
                "self_weight_kn": g * weight,
                "scope": "DIRECT_PANEL_LOAD_TERMS" if c["spectral"] else "STATIC_PANEL_LOAD_TERMS",
            }
        )
    return {
        "member": uid,
        "label": label,
        "surface_m2": area,
        "volume_m3": area * panel["thickness_m"],
        "unfactored_weight_kn": weight,
        "combinations": result,
    }


def transition_results(source, context, row, bound, scope, fck, *, column_sections=()):
    profile = row.get("physical_profile") or {}
    if not profile.get("bands") or not any(changes(profile)):
        return []
    coords, mesh = mesh_geometry(source)
    panels = {p["member"]: p for p in profile["panels"]}
    lengths = {uid: p["length_m"] for uid, p in panels.items()}
    result = []
    for lower, upper, changed in changes(profile):
        z = upper["bottom_m"]
        out = {
            "z_m": z,
            "started": sorted(set(upper["members"]) - set(lower["members"])),
            "ended": sorted(set(lower["members"]) - set(upper["members"])),
            "sections": [],
            "panel_loads": [],
            "jambs": [],
        }
        result.append(out)
        plans = {}
        for side, band in (("Below", lower), ("Above", upper)):
            plan = section_plan(band, z, side, lengths, mesh, coords)
            plans[side] = plan
            sec = {
                "side": side,
                "z_m": z,
                "members": band["members"],
                "net_area_m2": band["net_area_m2"],
                "gross_area_m2": band["shell_area_m2"],
                "mesh_section": {k: v for k, v in plan.items() if k != "corners"},
            }
            if fck is not None and isfinite(fck) and fck > 0:
                sec["axial_limit_kn"] = 0.35 * band["net_area_m2"] * 1000 * fck
            out["sections"].append(sec)
        points = set()
        panel_actions = {}
        for uid in changed:
            p = panels[uid]
            points.update(p["point_ids"][:2] if uid in out["started"] else p["point_ids"][2:])
            try:
                panel_actions[uid] = panel_loads(source, bound, scope, row, p)
                out["panel_loads"].append(panel_actions[uid])
            except (KeyError, IndexError, StopIteration, TypeError, ValueError) as exc:
                out["panel_loads"].append({"member": uid, "label": p["label"], "reason": str(exc)})
        for point in sorted(points):
            try:
                out["jambs"].append(
                    _jamb_forces(
                        source, context, row["story"], point, scope["native_static"], scope["native_seismic"]
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                out["jambs"].append({"point": point, "reason": str(exc)})
        from .wall_transition_shell import project_transition_shells

        for jamb in out["jambs"]:
            if not jamb.get("column"):
                continue
            matches = [m for m in column_sections if m.get("member_id") == jamb["column"]]
            if len(matches) == 1 and matches[0].get("section") == context[5][jamb["column"]]["SectProp"]:
                evidence = matches[0].get("section_evidence") or {}
                jamb["model_detail"] = {
                    "section": matches[0]["section"],
                    **{
                        k: evidence[k]
                        for k in (
                            "reinforcement_role",
                            "t2_mm",
                            "t3_mm",
                            "bar_count",
                            "longitudinal_bar_diameter_mm",
                            "tie_diameter_mm",
                            "cover_to_tie_mm",
                        )
                        if k in evidence
                    },
                }
        out["connection_detail_status"] = "OPENING_BAR_CONTINUITY_AND_DEVELOPMENT_REQUIRED"

        if ((source.get("pier_section_forces") or {}).get("read") or {}).get("transition_shells"):
            for uid in (set(lower["members"]) | set(upper["members"])) - set(changed):
                try:
                    panel_actions[uid] = panel_loads(source, bound, scope, row, panels[uid])
                except (KeyError, IndexError, StopIteration, TypeError, ValueError) as exc:
                    panel_actions[uid] = {"reason": str(exc)}
        out["shell_actions"] = project_transition_shells(
            source, bound, scope, out, panels, plans, coords, mesh, context[0], panel_actions
        )
    return result
