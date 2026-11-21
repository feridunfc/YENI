"""Check gravity equilibrium between observed, physically bound column cuts."""

from decimal import Decimal
from math import isclose

from .column_pmm_section import MECHANICAL, _named_row, _positive, _rows
from .demand_sources import component_force_rows
from .mixed_demands import _number, _static_pattern_loads, linear_coefficients, native_graph


def _check_combination(rows, name, coefficients, case_loads, patterns, weight, weight_tolerance, length):
    cuts = {case: {} for case in (name, *coefficients)}
    for row in rows:
        case, step, index = row[4:7]
        if case not in cuts:
            continue
        key = tuple(row[:4])
        if step not in ("Single Value", "") or index != 0 or key in cuts[case]:
            raise ValueError("GRAVITY_CUT_OR_STEP_UNRESOLVED:" + case)
        cuts[case][key] = row[7]
    stations = sorted(cuts[name], key=lambda row: row[1])
    ends = length["end_cuts"]
    if (len(stations) < 3 or any(set(values) != set(stations) for values in cuts.values())
            or len({key[1] for key in stations}) != len(stations)
            or len({key[2] for key in stations}) != 1
            or stations[0] != tuple(ends["I"]) or stations[-1] != tuple(ends["J"])
            or not isclose(stations[-1][1] - stations[0][1], length["physical_length_m"], abs_tol=1e-6)):
        raise ValueError("GRAVITY_ALIGNED_CLEAR_CUT_POPULATION_UNRESOLVED:" + name)
    self_weight_factors = {
        case: sum(scale * _number(patterns[pattern]["self_weight_multiplier"]) for pattern, scale in loads)
        for case, loads in case_loads.items()
    }
    combined_factor = sum(coefficients[case] * self_weight_factors[case] for case in coefficients)
    intervals = []
    matches = combined_factor > 0
    for start, end in zip(stations, stations[1:]):
        span = end[1] - start[1]
        changes = {case: values[end] - values[start] for case, values in cuts.items()}
        residuals = {
            case: changes[case] - float(factor) * weight * span
            for case, factor in self_weight_factors.items()
        }
        expected = float(combined_factor) * weight * span
        residual = changes[name] - expected
        combination_error = changes[name] - sum(float(coefficients[case]) * changes[case] for case in coefficients)
        tolerance = weight_tolerance * span
        matches &= (abs(residual) <= abs(float(combined_factor)) * tolerance + 1e-8
                    and abs(combination_error) <= 1e-8
                    and all(abs(value) <= abs(float(self_weight_factors[case])) * tolerance + 1e-8
                            for case, value in residuals.items()))
        intervals.append({
            "start_cut": start, "end_cut": end,
            "native_axial_change_kn": changes[name],
            "predicted_self_weight_change_kn": expected,
            "residual_kn": residual, "superposition_residual_kn": combination_error,
            "primitive_residuals_kn": residuals,
        })
    return {
        "status": "SELF_WEIGHT_BALANCED_AT_SIGNED_CUTS" if matches else "AXIAL_CHANGE_UNEXPLAINED_AT_SIGNED_CUTS",
        "factored_self_weight_multiplier": str(combined_factor),
        "primitive_self_weight_multipliers": {case: str(value) for case, value in self_weight_factors.items()},
        "combination_coefficients": {case: str(value) for case, value in coefficients.items()},
        "intervals": intervals,
    }


def project_gravity_axial_balance(source, pmm, length, frame_length):
    """Use the original signed cuts, section weight and linear load-case graph."""
    plan = pmm.get("combination_plan") or {}
    names = (((plan.get("design_assignment") or {}).get("groups") or {}).get("gravity") or ())
    if not names:
        return None
    uid = pmm["member_id"]
    try:
        faces = length["faces"]
        height = faces["J"]["joint_z_m"] - faces["I"]["joint_z_m"]
        if height <= 0 or not isclose(height, frame_length, abs_tol=1e-6):
            raise ValueError("VERTICAL_UPWARD_MEMBER_AXIS_NOT_BOUND")
        section = source["geometry_capture"]["tables"]["SECTION_SUMMARY"]
        fields = {"Shape", "Name", "Material", "WMod"}
        summary = _named_row(_rows({section["table_key"]: section}, section["table_key"], fields, {"Area": "m2"}),
                             "Name", pmm["section"], section["table_key"])
        if summary["Shape"] != "Concrete Rectangular":
            raise ValueError("RECTANGULAR_SECTION_WEIGHT_UNAVAILABLE")
        properties = source["column_axial"]["pmm_section_source"]["table_reads"]
        material = _named_row(_rows(properties, MECHANICAL, {"Material"}, {"UnitWeight": "kN/m3"}),
                              "Material", summary["Material"], MECHANICAL)
        area = _positive(summary["Area"], "Area")
        modifier = _positive(summary["WMod"], "WMod")
        unit_weight = _positive(material["UnitWeight"], "UnitWeight")
        weight_tolerance = float(Decimal(5).scaleb(Decimal(material["UnitWeight"]).as_tuple().exponent - 1))
        tables, cases, graph = native_graph(source)
        rows = component_force_rows(source, uid, plan)
        combinations = {}
        for name in names:
            coefficients = linear_coefficients(name, graph, cases)
            patterns, case_loads = _static_pattern_loads(tables, coefficients, cases)
            combinations[name] = _check_combination(
                rows, name, coefficients, case_loads, patterns, unit_weight * area * modifier,
                weight_tolerance * area * modifier, length,
            )
        return {
            "material": summary["Material"], "area_m2": area, "unit_weight_kn_m3": unit_weight,
            "section_weight_modifier": modifier, "combinations": combinations,
            "second_order_method_qualification": "VARIABLE_AXIAL_METHOD_NOT_ESTABLISHED",
        }
    except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
        return {"status": "GRAVITY_AXIAL_BALANCE_UNBOUND", "reason": str(exc)}
