"""Check gravity equilibrium between observed, physically bound column cuts."""

from decimal import Decimal
from math import isclose, isfinite

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


def _idealization_geometry(source, pmm, length, frame_length):
    """Rebind the existing geometry owners before accepting the declared scope."""
    from .column_clear_length import FACE_BASIS, project_column_clear_lengths
    from .column_pmm import bind_configured_output_cuts, bind_pmm_mesh_source
    from .frame_geometry import build_frame_catalog

    uid = pmm["member_id"]
    frames, _, graph = build_frame_catalog(source)
    frame = frames[uid]
    if frame["type"] != "Column" or frame["section_name"] != pmm["section"]:
        raise ValueError("AXIAL_IDEALIZATION_SECTION_ASSIGNMENT_CONFLICT")
    mesh = bind_pmm_mesh_source(source, {uid: frame["story"]})
    member_mesh = mesh["members"][uid]
    if not member_mesh["roster_bound"] or len(member_mesh["expected_analysis_element_ids"]) != 1:
        raise ValueError("AXIAL_IDEALIZATION_SINGLE_ANALYSIS_ELEMENT_REQUIRED")
    grids = bind_configured_output_cuts(source, mesh["members"])
    grid = grids[uid]
    if grid["status"] != "REQUIRED_SUBSET_BOUND":
        raise ValueError("AXIAL_IDEALIZATION_INDEPENDENT_CUTS_UNBOUND:" + str(grid.get("reason")))
    physical = project_column_clear_lengths(source, frames, graph["adjacency"], [uid],
        {"analysis_mesh": mesh, "configured_output_cuts": grids})
    current = ((physical or {}).get("per_member") or {}).get(uid) or {}
    if current.get("status") != FACE_BASIS:
        raise ValueError("AXIAL_IDEALIZATION_PRISMATIC_UNCOUPLED_SPAN_UNBOUND:"
                         + str(current.get("reason") or (physical or {}).get("source_error")))
    if (length != current or not isclose(float(frame_length), grid["length_m"], rel_tol=0, abs_tol=1e-6)):
        raise ValueError("AXIAL_IDEALIZATION_PHYSICAL_LENGTH_CONTEXT_MISMATCH")
    # A single native rectangular assignment is the supported prismatic branch.
    table = source["geometry_capture"]["tables"]["RECTANGULAR_SECTIONS"]
    rectangle = _named_row(_rows({table["table_key"]: table}, table["table_key"], {"Name"},
                                 {"t2": "m", "t3": "m"}), "Name", pmm["section"], table["table_key"])
    area = _positive(rectangle["t2"], "t2") * _positive(rectangle["t3"], "t3")
    return current, grid, area


def _idealization_cut_rows(rows, name, grid):
    """Use the pre-force configured grid, retaining the full native cut identity."""
    from .column_pmm import _required_cut_coverage

    selected = [row for row in rows if row[4] == name]
    if any(row[5] not in ("Single Value", "") or row[6] != 0 for row in selected):
        raise ValueError("AXIAL_IDEALIZATION_SIGNED_STEP_UNBOUND:" + name)
    indexed = {tuple(row[:4]): row for row in selected}
    if len(indexed) != len(selected):
        raise ValueError("AXIAL_IDEALIZATION_DUPLICATE_CUT:" + name)
    coverage = _required_cut_coverage(selected, grid)
    if not coverage["exact_cut_census"]:
        raise ValueError("AXIAL_IDEALIZATION_EXACT_CONFIGURED_CENSUS_REQUIRED:" + name)
    return indexed, coverage


def project_self_weight_nmax_idealization(source, pmm, length, frame_length, adopted_basis):
    """Check an explicit Nmax surrogate's source premises, not its engineering validity.

    The supported numerical scenario is a first-order, upright, single-element
    rectangular column with an exact three-cut source census. Every primitive
    axial change must reconcile with its declared self weight, and every signed
    combination P must also reconcile absolutely at each identical cut. The
    existing equilibrium owner supplies the weight calculation. This function
    performs no second-order or capacity calculation and never proves that an
    Nmax surrogate bounds the variable-N member.
    """
    from .column_axial import column_strength_plan
    from .design_scenario import _digest, _source_data

    native_sha = _digest(_source_data(source))
    result = {
        "schema": "tbdy.next.self-weight-nmax-inputs.v1", "method": "SELF_WEIGHT_NMAX",
        "status": "SELF_WEIGHT_NMAX_INPUTS_REJECTED", "reasons": [],
        "source_data_sha256": native_sha, "input_payload_sha256": _digest(source),
        "member_id": pmm.get("member_id"), "combinations": {},
        "original_constant_axial_clause_satisfied": False,
        "engineering_approval": "NOT_GRANTED", "conservative_bound_proven": False,
        "scope": "EXPLICIT_NUMERICAL_IDEALIZATION_NOT_TS500_APPLICABILITY_PROOF",
        "superposition_absolute_tolerance_kn": 1e-8,
        # 0.001 kN is a numerical equilibrium control budget, not a design margin.
        # It caps the existing displayed-material rounding allowance so coarse
        # material text cannot justify an arbitrarily large force discrepancy.
        "self_weight_residual_absolute_cap_kn": .001,
    }
    try:
        uid = pmm["member_id"]
        member = adopted_basis["member"]
        policy = member["axial_idealization"]
        names = policy["combinations"]
        if (adopted_basis.get("source_data_sha256") != native_sha
                or adopted_basis.get("member_id") != uid):
            raise ValueError("AXIAL_IDEALIZATION_ADOPTED_SOURCE_OR_MEMBER_MISMATCH")
        if (member.get("applicability") != "ADOPTED_PRISMATIC_SELF_WEIGHT_NMAX_IDEALIZATION"
                or policy.get("method") != "SELF_WEIGHT_NMAX"
                or not isinstance(names, list) or not names or len(set(names)) != len(names)
                or any(not isinstance(name, str) or not name or name.strip() != name for name in names)
                or not isinstance(policy.get("decision_reference"), str) or not policy["decision_reference"].strip()
                or any(member["axes"][axis].get("cm_policy") != "UNITY" for axis in ("M2", "M3"))):
            raise ValueError("AXIAL_IDEALIZATION_EXPLICIT_POLICY_INVALID")
        if (adopted_basis.get("source_analysis_order") != "FIRST_ORDER"
                or pmm.get("actual_second_order_applied") is True
                or pmm.get("analysis_order") not in (None, "UNVERIFIED", "NOT_PROVEN", "FIRST_ORDER")):
            raise ValueError("AXIAL_IDEALIZATION_FIRST_ORDER_REQUIRED_NO_DOUBLE_APPLICATION")
        result.update(decision_reference=policy["decision_reference"], requested_combinations=sorted(names),
                      source_order_basis="EXPLICIT_FIRST_ORDER_ADOPTION_ENGINEERING_ACCEPTANCE_PENDING")
        plan = column_strength_plan(source, source["column_axial"]["request"])
        if plan.get("blockers") or plan != pmm.get("combination_plan"):
            raise ValueError("AXIAL_IDEALIZATION_CURRENT_COMBINATION_PLAN_UNBOUND")
        signed = {row["name"] for row in plan["combinations"]
                  if row.get("force_semantics") == "STATIC_SIGNED_VECTOR"}
        if not set(names) <= signed or not set(names) <= set(member["combinations"]):
            raise ValueError("AXIAL_IDEALIZATION_EXACT_SIGNED_COMBINATION_SCOPE_REQUIRED")
        current, grid, geometric_area = _idealization_geometry(source, pmm, length, frame_length)
        result["physical_scope"] = {"section": pmm["section"], "physical_length_m": current["physical_length_m"],
            "end_cuts": current["end_cuts"], "configured_grid": grid,
            "basis": "EXISTING_PHYSICAL_FACE_AND_CONFIGURED_CUT_OWNERS"}
        rows = component_force_rows(source, uid, plan)
        native_by_case = {}
        variable = set()
        for name in sorted(signed):
            indexed, _ = _idealization_cut_rows(rows, name, grid)
            native_by_case[name] = indexed
            forces = [row[7] for row in indexed.values()]
            if max(forces) - min(forces) > 1e-8:
                variable.add(name)
        if not variable or not variable <= set(names):
            raise ValueError("AXIAL_IDEALIZATION_VARIABLE_SIGNED_SCOPE_NOT_COVERED")
        result["observed_variable_combinations"] = sorted(variable)
        # Reuse the equilibrium owner for the explicitly selected signed scope;
        # do not reclassify these combinations as project gravity design roles.
        scoped_pmm = {**pmm, "combination_plan": {**plan, "design_assignment": {"groups": {"gravity": names}}}}
        balance = project_gravity_axial_balance(source, scoped_pmm, current, frame_length)
        if not balance or balance.get("status") == "GRAVITY_AXIAL_BALANCE_UNBOUND":
            raise ValueError("AXIAL_IDEALIZATION_SELF_WEIGHT_INPUTS_UNBOUND:" + str((balance or {}).get("reason")))
        if not isclose(balance["area_m2"], geometric_area, rel_tol=0, abs_tol=1e-10):
            raise ValueError("AXIAL_IDEALIZATION_RECTANGULAR_AREA_CONFLICT")
        result["gravity_axial_balance"] = balance
        tables, cases, graph = native_graph(source)
        records = {record["name"]: record for record in pmm["combinations"]}
        static = tables["Load Case Definitions - Linear Static"]["rows"]
        for name in sorted(names):
            if records.get(name, {}).get("status") != "NUMERICAL_COMPLETE":
                raise ValueError("AXIAL_IDEALIZATION_PMM_COMBINATION_UNRESOLVED:" + name)
            own_balance = balance["combinations"][name]
            residuals = [abs(value) for interval in own_balance["intervals"]
                         for value in (interval["residual_kn"], *interval["primitive_residuals_kn"].values())]
            if (own_balance["status"] != "SELF_WEIGHT_BALANCED_AT_SIGNED_CUTS"
                    or max(residuals, default=float("inf")) > result["self_weight_residual_absolute_cap_kn"]):
                raise ValueError("AXIAL_IDEALIZATION_SELF_WEIGHT_RECONCILIATION_FAILED:" + name)
            coefficients = linear_coefficients(name, graph, cases)
            primitives = {}
            for case in coefficients:
                definitions = [row for row in static if row["Name"] == case]
                if not definitions or any(
                    row.get("StiffType") not in {"Unstressed", "Zero Initial Conditions", "Nonlinear Case"}
                    or row.get("StiffType") == "Nonlinear Case" and row.get("NonlinCase") not in (None, "", "None")
                    for row in definitions
                ):
                    raise ValueError("AXIAL_IDEALIZATION_PRIMITIVE_FIRST_ORDER_UNBOUND:" + case)
                primitives[case], _ = _idealization_cut_rows(rows, case, grid)
            evaluated = [row for row in pmm["rows"] if row["combination"] == name]
            pmm_by_cut = {(uid, row["object_station_m"], row["analysis_element_id"], row["element_station_m"]): row
                          for row in evaluated}
            own_rows = native_by_case[name]
            if len(pmm_by_cut) != len(evaluated) or pmm_by_cut.keys() != own_rows.keys():
                raise ValueError("AXIAL_IDEALIZATION_PMM_NATIVE_CUT_SCOPE_MISMATCH:" + name)
            cuts = []
            for key, row in sorted(own_rows.items()):
                nd = -row[7]
                if not isfinite(nd) or nd <= 0:
                    raise ValueError("AXIAL_IDEALIZATION_POSITIVE_COMPRESSION_REQUIRED:" + name)
                projected = pmm_by_cut[key]
                if (projected["nd_kn"] != nd or projected["step_type"] != row[5]
                        or projected["step_number"] != row[6]):
                    raise ValueError("AXIAL_IDEALIZATION_PMM_NATIVE_AXIAL_OR_STEP_MISMATCH:" + name)
                combined = sum(_number(primitives[case][key][7]) * factor for case, factor in coefficients.items())
                residual = float(_number(row[7]) - combined)
                if abs(residual) > result["superposition_absolute_tolerance_kn"]:
                    raise ValueError("AXIAL_IDEALIZATION_ABSOLUTE_PRIMITIVE_SUPERPOSITION_FAILED:" + name)
                cuts.append({"member_id": uid, "object_station_m": row[1], "analysis_element_id": row[2],
                    "element_station_m": row[3], "combination": name, "step_type": row[5], "step_number": row[6],
                    "native_p_kn": row[7], "nd_kn": nd, "reconstructed_native_p_kn": float(combined),
                    "superposition_residual_kn": residual})
            result["combinations"][name] = {"nmax_kn": max(cut["nd_kn"] for cut in cuts),
                "nmin_kn": min(cut["nd_kn"] for cut in cuts), "cuts": cuts,
                "expected_cut_count": len(grid["cuts"]), "evaluated_cut_count": len(cuts),
                "primitive_coefficients": {case: str(value) for case, value in coefficients.items()}}
        result["status"] = "SELF_WEIGHT_NMAX_INPUTS_ELIGIBLE"
    except (ArithmeticError, KeyError, TypeError, ValueError, AttributeError) as exc:
        result["reasons"].append(str(exc))
    return {**result, "evidence_sha256": _digest(result)}
