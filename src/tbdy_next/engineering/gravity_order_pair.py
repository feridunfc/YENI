"""Compare matched native gravity solutions at the existing R08 cuts."""

from collections.abc import Mapping
from math import isclose, isfinite

from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.ts500_column import apply_minimum_eccentricity
from .column_pmm_section import MECHANICAL, _named_row, _positive, _rows
from .mixed_demands import _static_pattern_loads, linear_coefficients, native_graph

SCHEMA = "tbdy.next.gravity-order-pair.v1"
METHOD = "ETABS_MATCHED_GRAVITY_COMPARISON_ONLY"
FORCE_FIELDS = ("p_kn", "v2_kn", "v3_kn", "t_knm", "m2_knm", "m3_knm")
CONTROL_ATOL = 0.001
CONTROL_RTOL = 1e-6


def _finite(value):
    return type(value) in (int, float) and isfinite(value)


def normalize_gravity_order_pair(raw, *, source_data_sha256):
    keys = {"schema", "source_data_sha256", "cases", "force_source", "section_name",
            "frame_section_modifiers", "frame_object_modifiers", "mesh"}
    if (not isinstance(raw, Mapping) or set(raw) != keys or raw["schema"] != SCHEMA
            or raw["source_data_sha256"] != source_data_sha256
            or not isinstance(raw["section_name"], str) or not raw["section_name"]):
        raise ValueError("GRAVITY_PAIR_SOURCE_BINDING_INVALID")
    cases, force = raw["cases"], raw["force_source"]
    if not isinstance(cases, Mapping) or not cases or not isinstance(force, Mapping):
        raise ValueError("GRAVITY_PAIR_CASES_OR_FORCE_SOURCE_INVALID")
    labels = []
    for combination, pair in cases.items():
        if (not isinstance(combination, str) or not combination
                or not isinstance(pair, Mapping) or set(pair) != {"first", "second", "patterns"}
                or not isinstance(pair["patterns"], Mapping) or not pair["patterns"]
                or not all(_finite(v) and v != 0 for v in pair["patterns"].values())
                or not all(isinstance(pair[key], str) and pair[key] for key in ("first", "second"))):
            raise ValueError("GRAVITY_PAIR_CASE_INVALID")
        labels.extend((pair["first"], pair["second"]))
    during = force.get("output_selection_during") or {}
    before, after = force.get("output_selection_before"), force.get("output_selection_after")
    rowsets = force.get("rowsets")
    if (len(set(labels)) != len(labels) or not isinstance(rowsets, Mapping) or not rowsets
            or force.get("schema") != "tbdy.next.etabs-frame-force-source.v1"
            or force.get("api") != "Results.FrameForce" or force.get("item_type") != "ObjectElm"
            or force.get("units_code") != 6 or force.get("errors") != {}
            or not before or before != after
            or {name for name, on in during.get("cases", {}).items() if on is True} != set(labels)
            or any(during.get("combos", {}).values())):
        raise ValueError("GRAVITY_PAIR_FORCE_SELECTION_OR_UNITS_UNVERIFIED")
    modifiers = raw["frame_object_modifiers"]
    mesh = raw["mesh"]
    if (not isinstance(modifiers, Mapping) or not isinstance(mesh, Mapping)
            or rowsets.keys() != modifiers.keys() or rowsets.keys() != mesh.keys()
            or any(not isinstance(ids, list) or not ids or len(ids) != len(set(ids))
                   or not all(isinstance(i, str) and i for i in ids) for ids in mesh.values())
            or any(not isinstance(values, list) or len(values) != 8 or not all(_finite(v) for v in values)
                   for values in [raw["frame_section_modifiers"], *modifiers.values()])):
        raise ValueError("GRAVITY_PAIR_MEMBER_OR_STIFFNESS_SCOPE_UNVERIFIED")
    return dict(raw)


def _patterns(source, names):
    tables, cases, graph = native_graph(source)
    definitions = {name: linear_coefficients(name, graph, cases) for name in names}
    _, case_loads = _static_pattern_loads(tables, {case for terms in definitions.values() for case in terms}, cases)
    result = {}
    for name, terms in definitions.items():
        vector = {}
        for case, factor in terms.items():
            for pattern, scale in case_loads[case]:
                vector[pattern] = vector.get(pattern, 0) + factor * scale
        result[name] = {pattern: float(value) for pattern, value in vector.items() if value}
    return result


def _native_ei(source, section_name, uid, record, stiffness):
    table = source["geometry_capture"]["tables"]["SECTION_SUMMARY"]
    name = table["table_key"]
    section = _named_row(_rows({name: table}, name, {"Name", "Material"}, {}), "Name", section_name, name)
    material_tables = source["column_axial"]["pmm_section_source"]["table_reads"]
    mechanical = _named_row(_rows(material_tables, MECHANICAL, {"Material"}, {"E1": "kN/m2"}),
                            "Material", section["Material"], MECHANICAL)
    ec_mpa = _positive(mechanical["E1"], "E1") / 1000.0
    source_modifiers = record["frame_section_modifiers"]
    object_modifiers = record["frame_object_modifiers"][uid]
    return {
        axis: {
            "etabs_ei_nmm2": ec_mpa * stiffness[axis]["ic_mm4"] * source_modifiers[index] * object_modifiers[index],
            "ts500_ei_nmm2": stiffness[axis]["selected_ei_nmm2"],
        }
        for axis, index in (("M2", 4), ("M3", 5))
    }


def compare_gravity_order_pair(source, pmm, local, dims, capacity):
    """Run the control check before assessing the P–Delta vector on the same cage."""
    record = source.get("gravity_order_pair")
    uid = pmm["member_id"]
    if not record or uid not in record["force_source"]["rowsets"]:
        return None
    out = {"method": METHOD, "status": "GRAVITY_PAIR_UNBOUND", "rows": [],
           "control_abs_tolerance": CONTROL_ATOL, "control_rel_tolerance": CONTROL_RTOL}
    try:
        cases = record["cases"]
        gravity = pmm["combination_plan"]["design_assignment"]["groups"]["gravity"]
        if record["section_name"] != pmm["section"]:
            raise ValueError("GRAVITY_PAIR_SECTION_MISMATCH")
        if set(cases) != set(gravity) or _patterns(source, cases) != {k: v["patterns"] for k, v in cases.items()}:
            raise ValueError("GRAVITY_PAIR_LOAD_VECTORS_MISMATCH")
        pair_rows = {}
        for row in native_frame_force_rows(record["force_source"]["rowsets"][uid], uid):
            key = (row[4], *row[1:4])
            if row[5:7] != ("Step", 1.0) or key in pair_rows:
                raise ValueError("GRAVITY_PAIR_FINAL_STEP_UNRESOLVED")
            pair_rows[key] = row[7:]
        vectors = {row[1:5]: row[7:] for row in native_frame_force_rows(
            source["column_axial"]["force_source"]["rowsets"][uid], uid)
            if row[4] in cases and row[5:7] == ("Single Value", 0.0)}
        magnified = {(row["object_station_m"], row["analysis_element_id"], row["element_station_m"], row["combination"]): row
                     for row in local["magnified_selected_pmm"]["rows"] if row["combination"] in cases}
        if (not vectors or magnified.keys() != vectors.keys()
                or {cut[1] for cut in vectors} != set(record["mesh"][uid])
                or set(pair_rows) != {(cases[name][order], station, element, elm_station)
                                      for station, element, elm_station, name in vectors for order in ("first", "second")}):
            raise ValueError("GRAVITY_PAIR_PHYSICAL_CUTS_OR_MESH_MISMATCH")
        out["stiffness_comparison"] = _native_ei(source, pmm["section"], uid, record, local["stiffness_and_euler"])
        out["analysis_elements"] = record["mesh"][uid]
        out["elastic_stiffness_matches_ts500"] = all(
            row["ts500_ei_nmm2"] is not None and isclose(row["etabs_ei_nmm2"], row["ts500_ei_nmm2"], rel_tol=1e-6)
            for row in out["stiffness_comparison"].values()
        )
        out["local_p_delta_mesh_convergence"] = "UNVERIFIED"
        controls = {
            cut: pair_rows[cases[cut[3]]["first"], *cut[:3]]
            for cut in vectors
        }
        matches = {cut: all(isclose(a, b, abs_tol=CONTROL_ATOL, rel_tol=CONTROL_RTOL)
                            for a, b in zip(original, controls[cut])) for cut, original in vectors.items()}
        all_matched = all(matches.values())

        for (station, element, elm_station, name), original in sorted(vectors.items()):
            original_key = (station, element, elm_station, name)
            control = controls[original_key]
            second = pair_rows[cases[name]["second"], station, element, elm_station]
            row = {
                "combination": name, "object_station_m": station, "analysis_element_id": element,
                "element_station_m": elm_station, "first_order_control_matches": matches[original_key],
                "original": dict(zip(FORCE_FIELDS, original)), "control": dict(zip(FORCE_FIELDS, control)),
                "control_difference": {field: act - ref for field, act, ref in zip(FORCE_FIELDS, control, original)},
                "second": dict(zip(FORCE_FIELDS, second)),
                "ts500_m2_knm": magnified[original_key]["magnified_m2_design_knm"],
                "ts500_m3_knm": magnified[original_key]["magnified_m3_design_knm"],
                "ts500_utilization": magnified[original_key]["utilization"],
            }
            if all_matched:
                demand = apply_minimum_eccentricity(nd_kn=-second[0], m2_knm=second[4], m3_knm=second[5], dims=dims)
                row["second_design_m2_knm"] = demand["m2_design_knm"]
                row["second_design_m3_knm"] = demand["m3_design_knm"]
                row["second_order_pmm"] = capacity.assess(-second[0] * 1000.0, demand["m2_design_knm"] * 1e6,
                                                           demand["m3_design_knm"] * 1e6)
            out["rows"].append(row)
        out["status"] = "GRAVITY_PAIR_COMPARED" if all_matched else "GRAVITY_PAIR_CONTROL_MISMATCH"
        assessed = [row for row in out["rows"] if (row.get("second_order_pmm") or {}).get("utilization") is not None]
        if assessed and out["status"] == "GRAVITY_PAIR_COMPARED":
            governing = max(assessed, key=lambda row: row["second_order_pmm"]["utilization"])
            out["governing"] = {key: governing[key] for key in ("combination", "object_station_m", "analysis_element_id")}
            out["governing"]["utilization"] = governing["second_order_pmm"]["utilization"]
            comparison_axes = {"M2": ("second_design_m2_knm", "ts500_m2_knm"),
                               "M3": ("second_design_m3_knm", "ts500_m3_knm")}
            differences = {axis: abs(governing[etabs] - governing[ts500]) for axis, (etabs, ts500) in comparison_axes.items()
                           if governing[ts500] is not None}
            if differences:
                out["governing"]["largest_design_moment_difference_axis"] = max(differences, key=differences.__getitem__)
        return out
    except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
        out.update(reason=str(exc))
        return out
