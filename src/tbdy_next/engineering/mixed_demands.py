"""Same-snapshot load-component algebra; never turn spectral extrema into vectors.

The signed path represents an earthquake-only linear functional by captured
signed case/combination rows. Exact rational coefficient identities establish
what is subtracted; all six values retain one native cut/step. No name matching,
external bank join, inferred analysis generation, or additional 100/30 scaling.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from decimal import Decimal, InvalidOperation
import math
from typing import Mapping

from ..column_engine.beam_references import station_budget
from ..column_engine.source_bank import native_frame_force_rows
from ..vs05_d4_source_authority import _case_summary, _combo_source, _source_table
from .design_scenario import _digest

SCHEMA = "tbdy.next.mixed-demand-components.v1"
METHOD = "native-linear-component-algebra.v1"


def _number(value):
    if isinstance(value, bool) or len(str(value)) > 128:
        raise ValueError("COMPONENT_FACTOR_INVALID")
    try:
        if "/" not in str(value):
            decimal = Decimal(str(value))
            if not decimal.is_finite() or abs(decimal.as_tuple().exponent) > 400:
                raise ValueError("COMPONENT_FACTOR_INVALID")
        number = Fraction(str(value))
        if not math.isfinite(float(number)):
            raise ValueError("COMPONENT_FACTOR_INVALID")
        return number
    except (ValueError, TypeError, InvalidOperation, OverflowError, ZeroDivisionError) as exc:
        raise ValueError("COMPONENT_FACTOR_INVALID") from exc


def native_graph(source):
    tables = (source.get("vs04_basis_probe") or {}).get("table_reads") or {}
    cases = _case_summary(tables, require_key=True)
    parsed = _combo_source(tables, cases, include_graph=True, require_key=True)
    if not parsed["candidate_operator_reference_shape_observed"]:
        raise ValueError("COMPONENT_GRAPH_UNQUALIFIED")
    return tables, cases, parsed["typed_graph"]


def linear_coefficients(name, graph, cases, path=()):
    """Expand ONLY linear sums. Repeated signed static leaves are algebraic sums."""
    if name in path or len(path) >= 64:
        raise ValueError("COMPONENT_COMBINATION_CYCLE_OR_DEPTH")
    if name in cases:
        if name in graph:
            raise ValueError("COMPONENT_CASE_COMBO_COLLISION")
        return {name: Fraction(1)}
    group = graph.get(name)
    if not group or group.get("operator_etabs") != "Linear Add" or not group.get("rows"):
        raise ValueError("COMPONENT_NON_LINEAR_ADD_OR_MISSING_DEFINITION:" + name)
    result = {}
    for row in group["rows"]:
        kind, ref = row.get("ref_type"), row.get("ref")
        if kind not in ("CASE", "COMBO") or ref not in (cases if kind == "CASE" else graph):
            raise ValueError("COMPONENT_REFERENCE_KIND_INVALID")
        factor = _number(row["factor"])
        for case, coefficient in linear_coefficients(ref, graph, cases, (*path, name)).items():
            result[case] = result.get(case, Fraction(0)) + factor * coefficient
    return {case: value for case, value in sorted(result.items()) if value}


def represent_linear_effect(target, observations):
    """Solve A*w=b over rational coefficients; free weights are deterministically zero.

    This proves an identity between recorded load definitions, not an independent
    solution of the structural model. Failure of rank is not repaired with least
    squares, rounded coefficients or an inferred force vector.
    """
    names = sorted(observations, key=lambda n: (len(observations[n]), n))
    dimensions = sorted(set(target) | {k for value in observations.values() for k in value})
    if len(names) > 512 or len(dimensions) > 512:
        raise ValueError("COMPONENT_ALGEBRA_SCOPE_LIMIT")
    matrix = [[_number(observations[n].get(k, 0)) for n in names] + [_number(target.get(k, 0))]
              for k in dimensions]
    pivots, row = [], 0
    for column in range(len(names)):
        pivot = next((i for i in range(row, len(matrix)) if matrix[i][column]), None)
        if pivot is None:
            continue
        matrix[row], matrix[pivot] = matrix[pivot], matrix[row]
        value = matrix[row][column]
        matrix[row] = [v / value for v in matrix[row]]
        for i in range(len(matrix)):
            if i != row and matrix[i][column]:
                value = matrix[i][column]
                matrix[i] = [a - value * b for a, b in zip(matrix[i], matrix[row])]
        pivots.append(column)
        row += 1
        if row == len(matrix):
            break
    if any(not any(r[:-1]) and r[-1] for r in matrix):
        raise ValueError("EARTHQUAKE_COMPONENT_NOT_IDENTIFIABLE_FROM_CAPTURED_SIGNED_OUTPUTS")
    solution = {names[column]: matrix[i][-1] for i, column in enumerate(pivots) if matrix[i][-1]}
    if any(sum(solution.get(n, 0) * _number(observations[n].get(k, 0)) for n in names)
           != _number(target.get(k, 0)) for k in dimensions):
        raise ValueError("COMPONENT_COEFFICIENT_IDENTITY_FAILED")
    return {name: str(value) for name, value in sorted(solution.items())}


def _static_roles(tables, required, cases):
    key = "Load Case Definitions - Linear Static"
    table = tables.get(key) or {}
    fields = set(table.get("fields") or ())
    # ETABS 23 uses LoadSF. Legacy verified fixtures use SF; ambiguity is rejected.
    factor_fields = fields & {"LoadSF", "SF"}
    if not factor_fields:
        raise ValueError("STATIC_LOAD_FACTOR_FIELD_UNAVAILABLE")
    rows = _source_table(tables, key, {"Name", "LoadType", "LoadName", *factor_fields}, require_key=True)
    patterns = _source_table(tables, "Load Pattern Definitions", {"LoadPat", "DesignType", "SelfWtMult"}, require_key=True)
    by_pattern = {}
    for p in patterns:
        if p["LoadPat"] in by_pattern:
            raise ValueError("COMPONENT_LOAD_PATTERN_DUPLICATE")
        by_pattern[p["LoadPat"]] = p
    roles = {}
    for case in sorted(required):
        loads = [r for r in rows if r["Name"] == case]
        if cases[case]["type"] != "Linear Static" or not loads:
            raise ValueError("COMPONENT_SIGNED_STATIC_CASE_REQUIRED:" + case)
        kinds = set()
        for load in loads:
            coefficients = {_number(load[k]) for k in factor_fields}
            if len(coefficients) != 1:
                raise ValueError("STATIC_LOAD_FACTOR_FIELDS_CONFLICT:" + case)
            if not next(iter(coefficients)):
                continue
            pattern = by_pattern.get(load["LoadName"])
            if load["LoadType"] != "Load" or pattern is None:
                raise ValueError("COMPONENT_PATTERN_BINDING_UNAVAILABLE:" + case)
            role = pattern["DesignType"]
            weight = _number(pattern["SelfWtMult"])
            if role in ("Quake", "Seismic"):
                if weight:
                    raise ValueError("EARTHQUAKE_ONLY_SHEAR_NOT_SEPARATED:SELF_WEIGHT:" + case)
                kinds.add("EARTHQUAKE")
            elif role in ("Dead", "Super Dead", "SuperDead", "Live", "Reducible Live", "Roof Live", "Snow", "Temperature"):
                kinds.add("NON_EARTHQUAKE")
            else:
                raise ValueError("COMPONENT_PATTERN_ROLE_UNSUPPORTED:" + case + ":" + role)
        if len(kinds) != 1:
            raise ValueError("STATIC_CASE_MIXES_ACTION_ROLES_OR_HAS_NO_LOAD:" + case)
        roles[case] = next(iter(kinds))
    return roles


def earthquake_partition(source, names, plan):
    """Bind a quake-only linear functional for each selected signed mixed combo."""
    tables, cases, graph = native_graph(source)
    definitions = {name: linear_coefficients(name, graph, cases) for name in names}
    declared = {c["name"]: set(c.get("case_names", ())) for c in plan["combinations"]}
    for name, coefficients in definitions.items():
        if not coefficients or not set(coefficients) <= declared.get(name, set()):
            raise ValueError("ALPHA_SEISMIC_CASE_LINEAGE_CONFLICT:" + name)
    roles = _static_roles(tables, {c for d in definitions.values() for c in d}, cases)
    rowsets = ((source.get("column_axial") or {}).get("force_source") or {}).get("rowsets") or {}
    observed_names = {row[4] for uid, rowset in rowsets.items() for row in native_frame_force_rows(rowset, uid)
                      if row[5] in ("Single Value", "") and row[6] == 0}
    observations = {}
    for name in sorted(observed_names):
        try:
            coefficients = linear_coefficients(name, graph, cases)
        except ValueError:
            continue
        if coefficients and all(cases[c]["type"] == "Linear Static" for c in coefficients):
            observations[name] = coefficients
    recipes = {}
    for name, coefficients in definitions.items():
        quake = {c: v for c, v in coefficients.items() if roles[c] == "EARTHQUAKE"}
        if not quake:
            raise ValueError("EARTHQUAKE_ONLY_SHEAR_NOT_SEPARATED:NO_NATIVE_QUAKE:" + name)
        other = {c: v for c, v in coefficients.items() if roles[c] != "EARTHQUAKE"}
        weights = {name: "1"} if not other else represent_linear_effect(quake, observations)
        recipes[name] = {"quake_coefficients": {c: str(v) for c, v in quake.items()},
                         "other_coefficients": {c: str(v) for c, v in other.items()},
                         "observation_weights": weights,
                         "mixed": bool(other)}
    return {"basis": "NATIVE_SIGNED_LINEAR_EARTHQUAKE_COMPONENT",
            "combination_cases": {n: sorted(d) for n, d in definitions.items()}, "recipes": recipes,
            "case_roles": roles, "native_definitions_sha256": _digest(tables),
            "load_role_engineering_approval": "NOT_PROVEN", "method": METHOD}


def earthquake_row(rows, target, recipe, *, length):
    """Linear algebra at the SAME object/element-side cut, never nearest station."""
    vector = [Fraction(0)] * 6
    evidence = []
    for name, coefficient in recipe["observation_weights"].items():
        matches = [r for r in rows if r[0] == target[0] and r[2] == target[2] and r[4] == name
                   and r[5] in ("Single Value", "") and r[6] == target[6] == 0
                   and abs(r[1] - target[1]) <= station_budget(r[1], target[1], length)
                   and abs(r[3] - target[3]) <= station_budget(r[3], target[3], length)]
        if len(matches) != 1:
            raise ValueError("EARTHQUAKE_COMPONENT_CUT_MISSING_OR_AMBIGUOUS:" + name)
        row = matches[0]
        for i, value in enumerate(row[7:]):
            vector[i] += _number(coefficient) * _number(value)
        evidence.append({"native_key": list(row[:7]), "factor": coefficient, "row_sha256": _digest(row)})
    values = tuple(float(v) for v in vector)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("EARTHQUAKE_COMPONENT_ARITHMETIC_OVERFLOW")
    return (*target[:7], *values), evidence


def spectral_component_evidence(source, axial, scope, *, input_sha):
    """Persist observed Max/Min intervals. This is NOT independent leaf replay.

    Uses the existing spectral owner's interval arithmetic; the configured cut
    ledger remains explicit. Missing required pairs remain in the denominator.
    The result cannot authorize signed SCWB or alpha on aggregate RSA maxima.
    """
    from ..column_engine.spectral_envelope import observed_component_interval
    plan = (axial or {}).get("combination_plan") or {}
    names = sorted(c["name"] for c in plan.get("combinations", ()) if c.get("force_semantics") == "SCALAR_COMPONENT_ENVELOPE")
    if not names:
        return None
    grids = (scope or {}).get("configured_output_cuts") or {}
    rowsets = ((source.get("column_axial") or {}).get("force_source") or {}).get("rowsets") or {}
    instances = (scope or {}).get("instances") or []
    members = sorted({i["element_id"] for i in instances} | set(grids))
    instance_map = {(i["element_id"], i["combination"]): i for i in instances}
    rows, errors = [], list((scope or {}).get("dependency_blockers") or [])
    force = (source.get("column_axial") or {}).get("force_source") or {}
    if (force.get("schema") != "tbdy.next.etabs-frame-force-source.v1"
            or force.get("api") != "Results.FrameForce" or force.get("units_code") != 6):
        errors.append("NATIVE_FORCE_SCHEMA_OR_UNITS_UNQUALIFIED")
    keys = [(i["element_id"], i["combination"]) for i in instances]
    if len(keys) != len(set(keys)) or len(names) != len(set(names)):
        errors.append("DUPLICATE_EXPECTED_MEMBER_COMBINATION")
    try:
        _, cases, graph = native_graph(source)
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        cases, graph = {}, {}
        errors.append("COMPONENT_GRAPH_UNAVAILABLE:" + str(exc))
    for uid in members:
        member_errors = []
        try:
            native = list(native_frame_force_rows(rowsets[uid], uid)) if uid in rowsets else []
        except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
            native = []
            member_errors.append("NATIVE_FORCE_ROWS_INVALID:" + str(exc))
        grid = grids.get(uid) or {}
        # Configured coordinates are mapped uniquely at the existing machine
        # tolerance to native identities. No second cut is invented for a ULP.
        cuts = {r[:4] for r in native}
        length = grid.get("length_m", 0.0)
        required_native = set()
        for cut in grid.get("cuts", ()):
            key = (uid, cut["object_station_m"], cut["analysis_element_id"], cut["element_station_m"])
            matches = [c for c in cuts if c[2] == key[2]
                       and abs(c[1]-key[1]) <= station_budget(c[1], key[1], length)
                       and abs(c[3]-key[3]) <= station_budget(c[3], key[3], length)]
            if len(matches) == 1:
                required_native.add(matches[0])
            else:
                cuts.add(key)
                required_native.add(key)
                member_errors.append("REQUIRED_CUT_MISSING_OR_AMBIGUOUS:" + str(key))
        for name in names:
            item = {"member_id": uid, "combination": name, "status": "OBSERVED_INTERVALS_DECOMPOSED",
                    "expected_cut_count": len(cuts), "required_cut_count": len(grid.get("cuts", ())),
                    "cuts": [], "reason_codes": [*errors, *member_errors]}
            if instances:
                pair = instance_map.get((uid, name))
                if pair is None:
                    item["reason_codes"].append("EXPECTED_PAIR_LEDGER_ENTRY_MISSING")
                else:
                    if pair.get("execution_status") == "BLOCKED":
                        item["reason_codes"].append("UPSTREAM_PAIR_BLOCKED:" + str(pair.get("reason")))
                    for label in ("analysis_element_coverage", "configured_cut_coverage"):
                        coverage = pair.get(label) or {}
                        if (coverage.get("reason") or coverage.get("missing_cuts")
                                or coverage.get("ambiguous_cuts") or coverage.get("missing_analysis_element_ids")
                                or coverage.get("unmapped_analysis_element_ids")):
                            item["reason_codes"].append("UPSTREAM_" + label.upper() + "_UNRESOLVED")
            group = graph.get(name) or {}
            try:
                coefficients = linear_coefficients(name, graph, cases)
                if (any(r.get("ref_type") != "CASE" for r in group.get("rows", ()))
                        or any(cases[c]["type"] not in ("Linear Static", "Response Spectrum") for c in coefficients)
                        or not any(cases[c]["type"] == "Response Spectrum" for c in coefficients)
                        or len({r["ref"] for r in group["rows"]}) != len(group["rows"])):
                    raise ValueError("SPECTRAL_COMPONENT_REQUIRES_DIRECT_LINEAR_ADD")
                item["static_case_coefficients"] = {c: str(v) for c, v in coefficients.items() if cases[c]["type"] == "Linear Static"}
                item["spectral_case_coefficients"] = {c: str(v) for c, v in coefficients.items() if cases[c]["type"] == "Response Spectrum"}
            except (KeyError, ValueError, TypeError) as exc:
                item["reason_codes"].append(str(exc))
            if not cuts or grid.get("status") != "REQUIRED_SUBSET_BOUND":
                item["reason_codes"].append("CONFIGURED_CUT_SUBSET_UNVERIFIED")
            for cut in sorted(cuts):
                matches = [r for r in native if r[:4] == cut and r[4] == name]
                try:
                    if len(matches) != 2 or {r[5] for r in matches} != {"Max", "Min"} or any(r[6] != 0 for r in matches):
                        raise ValueError("EXACT_MAX_MIN_PAIR_MISSING_OR_AMBIGUOUS")
                    by_step = {r[5]: r for r in matches}
                    detail = observed_component_interval(by_step["Min"][7:], by_step["Max"][7:])
                    item["cuts"].append({"native_cut": list(cut), "configured_required_cut": cut in required_native,
                                         **detail, "source_rows_sha256": _digest(matches)})
                except (ValueError, KeyError, TypeError) as exc:
                    item["reason_codes"].append(str(exc) + ":" + str(cut))
            if item["reason_codes"]:
                item["status"] = "NOT_PROVEN"
            rows.append(item)
    result = {"schema": SCHEMA, "method": METHOD, "input_sha256": input_sha,
              "source_payload_sha256": _digest(source), "expected_member_ids": members,
              "expected_combinations": names, "expected_pair_count": len(members)*len(names),
              "rows": rows, "status_counts": dict(Counter(r["status"] for r in rows)), "reason_codes": errors,
              "basis": "OBSERVED_DIRECT_LINEAR_ADD_INTERVALS_NOT_INDEPENDENT_CONSTITUENT_REPLAY",
              "additional_directional_or_scale_factor_applied": False,
              "physical_concurrency_proven": False, "signed_alpha_input_eligible": False,
              "independent_full_cut_census_proven": False, "engineering_release": "NOT_READY"}
    result["sha256"] = _digest(result)
    return result
