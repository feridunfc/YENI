"""VS26: replay native component envelopes, never a concurrent design vector.

The bounded recipe is direct Linear Add of signed static Single Value rows and
nonnegative response-spectrum Max amplitudes at the SAME native cut. Each
component is compared to both recorded Max/Min steps. Captured coefficients
are used once; no inferred 100/30, D, spectrum scale or sign permutations.

CSI's response-spectrum FAQ distinguishes nonconcurrent component maxima from
design envelopes. This module establishes source arithmetic only, not the
project's code-rule selection, analysis generation or second-order policy.
https://wikicsiamerica.atlassian.net/wiki/spaces/kb/pages/2006323
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
import math

from .native_archive import BankError, digest, finite
from .source_bank import ATOL, RTOL, COMPONENTS, FIELDS, _definitions, _read_forces

SCHEMA = "tbdy.next.column-spectral-envelopes.v1"
POLICY = "DIRECT_LINEAR_ADD_STATIC_CENTER_RS_SCALAR_RADIUS_V1"
VIEW = "spectral-envelopes"
RS_APIS = {
    "loads": "GetLoads", "modal_case": "GetModalCase", "directional_combination": "GetDirComb",
    "modal_combination": "GetModalComb_1", "damping_type": "GetDampType",
    "damping_constant_parameter": "GetDampConstant", "eccentricity": "GetEccentricity",
}


def _fraction(value):
    return Fraction(str(finite(value, "spectral_operand")))


def _as_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise BankError("SPECTRAL_ARITHMETIC_OVERFLOW")
    return number


def _case_context(archive, name):
    """Retain native parameters without guessing enum meanings/active damping."""
    facts, missing, loads = {}, [], []
    for role, method in RS_APIS.items():
        try:
            observed = archive.native("LoadCases.ResponseSpectrum." + method, "case", name)
            if observed is None:
                raise BankError("NATIVE_PARAMETER_NOT_OBSERVED")
            facts[role] = {"values": observed[0], "source": observed[1]}
        except (ValueError, KeyError, TypeError) as exc:
            missing.append({"parameter": role, "reason": str(exc)})
    try:
        raw = facts["loads"]["values"]
        n = raw["NumberLoads"]
        keys = ("LoadName", "Func", "SF", "CSys", "Ang")
        if (type(n) is not int or not 0 < n <= 100
                or any(not isinstance(raw[k], list) or len(raw[k]) != n for k in keys)):
            raise BankError("SPECTRUM_LOAD_SHAPE_INVALID")
        for i in range(n):
            if any(not isinstance(raw[k][i], str) or not raw[k][i] for k in ("LoadName", "Func", "CSys")):
                raise BankError("SPECTRUM_LOAD_ID_INVALID")
            loads.append({"load_name": raw["LoadName"][i], "function": raw["Func"][i],
                "scale": finite(raw["SF"][i], "spectrum_scale"), "coordinate_system": raw["CSys"][i],
                "angle_deg": finite(raw["Ang"][i], "spectrum_angle")})
    except (ValueError, KeyError, TypeError) as exc:
        loads = []
        missing.append({"parameter": "load_direction_binding", "reason": str(exc)})
    axis = (loads[0]["load_name"] if len(loads) == 1 and loads[0]["load_name"] in ("U1", "U2")
        and loads[0]["coordinate_system"] == "Global" and loads[0]["angle_deg"] == 0 else None)
    return {"case_name": name, "loads": loads, "single_global_axis": axis,
        "native_facts": facts, "missing_parameters": missing,
        "active_damping_proven": False, "analysis_generation_qualified": False}


def _route(definition, cases):
    if definition.get("status") != "OBSERVED":
        return "COMBINATION_DEFINITION_UNRESOLVED"
    if type(definition.get("operator")) is not int or definition["operator"] != 0:
        return "NON_LINEAR_ADD_OPERATOR_OUTSIDE_RECIPE"
    terms = definition.get("terms", [])
    if not terms:
        return "EMPTY_COMBINATION"
    if any(type(t.get("type")) is not int or t["type"] != 0 for t in terms):
        return "NESTED_REFERENCE_OUTSIDE_RECIPE"
    if len({t.get("name") for t in terms}) != len(terms):
        return "REPEATED_REFERENCE_OUTSIDE_RECIPE"
    if any(cases.get(t.get("name"), {}).get("status") != "OBSERVED" for t in terms):
        return "CONSTITUENT_CASE_TYPE_UNRESOLVED"
    try:
        for term in terms:
            _fraction(term["factor"])
    except (ValueError, KeyError, TypeError):
        return "COMBINATION_FACTOR_INVALID"
    kinds = {cases[t["name"]].get("case_type") for t in terms}
    if not kinds <= {1, 4}:
        return "ANALYSIS_CASE_TYPE_OUTSIDE_RECIPE"
    if 4 not in kinds:
        return "NO_SPECTRAL_TERM"
    return None


def _coefficient_pattern(terms, cases, contexts):
    rs = [{"case_name": t["name"], "factor": t["factor"],
           "global_axis": contexts[t["name"]]["single_global_axis"]}
          for t in terms if cases[t["name"]]["case_type"] == 4]
    ratios = None
    if len(rs) == 2 and {r["global_axis"] for r in rs} == {"U1", "U2"}:
        ordered = sorted(rs, key=lambda r: abs(_fraction(r["factor"])), reverse=True)
        major, minor = (abs(_fraction(r["factor"])) for r in ordered)
        if major:
            ratios = {"primary_case": ordered[0]["case_name"], "primary_factor": ordered[0]["factor"],
                "secondary_case": ordered[1]["case_name"], "secondary_factor": ordered[1]["factor"],
                "secondary_to_primary": _as_float(minor / major), "is_100_30_pattern": minor / major == Fraction(3, 10)}
    return {"spectral_terms": rs, "captured_directional_pattern": ratios,
        "interpretation": "CAPTURED_COEFFICIENTS_ONLY", "code_rule_qualified": False}


def _source_ref(row):
    return {"source_row_id": row["source_row_id"], "source_call_id": row["call_id"],
        "source_row_index": row["source_row_index"], "shard_sha256": row["shard_sha256"],
        "native_key": {k: row[k] for k in FIELDS[:7]},
        "native_values": {k: row[k] for k in COMPONENTS}}


def _bind_bank(bank, archive):
    """Re-read the sealed native shards; matching altered arrays is no proof.

    Store verifies the immutable SQLite hash on every request. This additional
    core boundary also protects direct callers and catches coherently altered
    leaves/targets/definitions even when their in-memory IDs are recomputed.
    A source member that the accepted reader itself cannot decode stays a gap.
    """
    cases, combos = _definitions(archive)
    if (bank["case_definitions"] != list(cases.values())
            or bank["combination_definitions"] != list(combos.values())):
        raise BankError("SPECTRAL_NATIVE_DEFINITIONS_MISMATCH")
    if [m["frame_name"] for m in bank["members"]] != list(archive.selected):
        raise BankError("SPECTRAL_NATIVE_POPULATION_MISMATCH")
    context = archive.json("collector-summary.json") if archive.subset is None else None
    stable = bool(context and context.get("identity_unchanged") is True
        and context.get("restoration_status") == "VERIFIED" and context.get("targeted_capture_attempts_complete") is True
        and context.get("error") is None and context.get("model_definitions_modified") is False
        and context.get("analysis_rerun_attempted") is False)
    if bank.get("capture_context_observed") is not stable:
        raise BankError("SPECTRAL_NATIVE_CAPTURE_CONTEXT_MISMATCH")
    supplied, inventories = defaultdict(list), defaultdict(list)
    for row in bank["force_states"]:
        supplied[row["Obj"]].append(row)
    if set(supplied) - set(archive.selected):
        raise BankError("SPECTRAL_SOURCE_IDENTITY_INVALID")
    for entry in archive.jsonlines("force-inventory.jsonl"):
        inventories[entry.get("frame_name")].append(entry)
    for member in bank["members"]:
        name = member["frame_name"]
        try:
            if len(inventories[name]) != 1:
                raise BankError("FORCE_INVENTORY_MISSING_OR_DUPLICATED")
            native, proof = _read_forces(archive, name, inventories[name][0])
        except (ValueError, KeyError, TypeError):
            if supplied[name] or member["force_status"] != "NOT_PROVEN":
                raise BankError("SPECTRAL_NATIVE_FORCE_BINDING_MISMATCH")
            continue
        if (member["force_status"] != "OBSERVED_NATIVE_TUPLES" or member.get("force_source") != proof
                or supplied[name] != [row.as_dict() for row in native]):
            raise BankError("SPECTRAL_NATIVE_FORCE_BINDING_MISMATCH")
        # The human-readable story is evidence too; never silently relabel a cut.
        label = archive.native("FrameObj.GetLabelFromName", "frame", name, ("Label", "Story", "pRetVal"))
        story = member.get("context", {}).get("frame", {}).get("story_label")
        if story is not None and (label is None or label[0]["Story"] != story):
            raise BankError("SPECTRAL_NATIVE_STORY_BINDING_MISMATCH")


def _pair(cut, definition, cases, index, member, source_sha):
    name = definition["name"]
    key = dict(zip(FIELDS[:4], cut))
    item = {"result_id": digest({"schema": SCHEMA, "policy": POLICY, "archive": source_sha,
            "combination": name, "cut": key}),
        "member_id": cut[0], "story": member.get("context", {}).get("frame", {}).get("story_label"),
        "output_case": name, "station_key": key, "status": "SOURCE_UNRESOLVED", "reason": None,
        "bounds": None, "native_bounds": None, "center": None, "spectral_radius": None,
        "source_terms": [], "native_steps": [], "comparisons": [],
        "matched_rows": 0, "mismatched_rows": 0, "scalar_comparisons": 0,
        "over_tolerance_components": 0, "maximum_absolute_difference_by_unit": {"kN": 0.0, "kNm": 0.0},
        "final_design_eligible": False, "concurrent_force_vector": None}
    try:
        target = index.get((cut, name), ())
        item["native_steps"] = [_source_ref(r) for r in target]
        # No silent deduplication or step/element/station interpolation.
        if (len(target) != 2 or {r["StepType"] for r in target} != {"Max", "Min"}
                or any(r["StepNum"] != 0 for r in target)):
            raise BankError("EXACT_MAX_MIN_PAIR_MISSING_OR_AMBIGUOUS")
        center, radius = dict.fromkeys(COMPONENTS, Fraction(0)), dict.fromkeys(COMPONENTS, Fraction(0))
        for term in definition["terms"]:
            kind = cases[term["name"]]["case_type"]
            rows = index.get((cut, term["name"]), ())
            if len(rows) != 1:
                raise BankError("EXACT_LEAF_ROW_MISSING_OR_AMBIGUOUS:" + term["name"])
            row = rows[0]
            if row["StepType"] != ("Max" if kind == 4 else "Single Value") or row["StepNum"] != 0:
                raise BankError("LEAF_STEP_OUTSIDE_RECIPE:" + term["name"])
            factor = _fraction(term["factor"])
            item["source_terms"].append({"case_type": kind, "factor": term["factor"], **_source_ref(row)})
            for component in COMPONENTS:
                value = _fraction(row[component])
                if kind == 4:
                    if value < 0:
                        raise BankError("NEGATIVE_SPECTRAL_MAX_AMPLITUDE:" + term["name"] + ":" + component)
                    radius[component] += abs(factor) * value
                else:
                    center[component] += factor * value
        observed = {r["StepType"]: r for r in target}
        if any(observed["Min"][c] > observed["Max"][c] for c in COMPONENTS):
            raise BankError("NATIVE_ENVELOPE_ORDER_INVALID")
        native_bounds = {c: {"lower": _as_float(center[c] - radius[c]),
                             "upper": _as_float(center[c] + radius[c])} for c in COMPONENTS}
        comparisons, maxima = [], {"kN": 0.0, "kNm": 0.0}
        for step, sign in (("Max", 1), ("Min", -1)):
            actual = observed[step]
            for component in COMPONENTS:
                value = center[component] + sign * radius[component]
                native = _fraction(actual[component])
                delta = abs(value - native)
                budget = ATOL + RTOL * max(abs(value), abs(native))
                unit = "kN" if component in ("P", "V2", "V3") else "kNm"
                difference = _as_float(delta)
                maxima[unit] = max(maxima[unit], difference)
                comparisons.append({"step_type": step, "component": component, "unit": unit,
                    "calculated": _as_float(value), "observed": _as_float(native),
                    "absolute_difference": difference, "tolerance": _as_float(budget), "match": delta <= budget})
        matched = sum(all(c["match"] for c in comparisons if c["step_type"] == step) for step in ("Max", "Min"))
        # N=-P reverses lower/upper. Other CSI local component signs are retained.
        bounds = {"N": {"lower": -native_bounds["P"]["upper"], "upper": -native_bounds["P"]["lower"]},
                  **{c: native_bounds[c] for c in COMPONENTS if c != "P"}}
        item.update(status="NUMERICAL_MATCH" if matched == 2 else "NUMERICAL_MISMATCH",
            bounds=bounds, native_bounds=native_bounds,
            center={c: _as_float(center[c]) for c in COMPONENTS},
            spectral_radius={c: _as_float(radius[c]) for c in COMPONENTS}, comparisons=comparisons,
            matched_rows=matched, mismatched_rows=2-matched, scalar_comparisons=12,
            over_tolerance_components=sum(not c["match"] for c in comparisons),
            maximum_absolute_difference_by_unit=maxima)
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        item["reason"] = str(exc)
    return item


def build_spectral_envelopes(bank, archive):
    if bank["source_archive_sha256"] != archive.sha256:
        raise BankError("SPECTRAL_ARCHIVE_BINDING_MISMATCH")
    _bind_bank(bank, archive)
    cases = {r["name"]: r for r in bank["case_definitions"]}
    definitions = bank["combination_definitions"]
    members = {m["frame_name"]: m for m in bank["members"]}
    index, cuts, seen_ids = defaultdict(list), set(), set()
    for row in bank["force_states"]:
        if row["Obj"] not in members or row["source_row_id"] in seen_ids:
            raise BankError("SPECTRAL_SOURCE_IDENTITY_INVALID")
        seen_ids.add(row["source_row_id"])
        cut = tuple(row[k] for k in FIELDS[:4])
        cuts.add(cut)
        index[cut, row["LoadCase"]].append(row)
    contexts = {name: _case_context(archive, name) for name, case in cases.items()
                if case.get("status") == "OBSERVED" and case.get("case_type") == 4}
    rows, summaries = [], []
    for definition in definitions:
        reason = _route(definition, cases)
        summary = {"combination": definition["name"], "definition": deepcopy(definition),
            "scope": "OUTSIDE_RECIPE" if reason else "DIRECT_SPECTRAL_LINEAR_ADD",
            "reason": reason, "expected_pair_count": 0, "matched_rows": 0, "mismatched_rows": 0,
            "unresolved_pair_count": 0, "scalar_comparisons": 0, "coefficient_context": None}
        if reason is None:
            summary["coefficient_context"] = _coefficient_pattern(definition["terms"], cases, contexts)
            pairs = [_pair(cut, definition, cases, index, members[cut[0]], archive.sha256) for cut in sorted(cuts)]
            rows.extend(pairs)
            summary.update(expected_pair_count=len(pairs), matched_rows=sum(r["matched_rows"] for r in pairs),
                mismatched_rows=sum(r["mismatched_rows"] for r in pairs),
                unresolved_pair_count=sum(r["status"] == "SOURCE_UNRESOLVED" for r in pairs),
                scalar_comparisons=sum(r["scalar_comparisons"] for r in pairs))
        summaries.append(summary)
    eligible = sum(s["scope"] == "DIRECT_SPECTRAL_LINEAR_ADD" for s in summaries)
    missing_members = sorted(set(members) - {cut[0] for cut in cuts})
    unresolved = sum(r["status"] == "SOURCE_UNRESOLVED" for r in rows)
    mismatched = sum(r["mismatched_rows"] for r in rows)
    coverage_complete = bool(eligible and rows and not missing_members and not unresolved
                             and bank.get("capture_context_observed") is True)
    result = {"schema": SCHEMA, "policy": POLICY, "source_run_id": bank.get("run_id"),
        "source_archive_sha256": archive.sha256, "source_bank_result_sha256": bank["result_sha256"],
        "components": list(COMPONENTS), "display_components": ["N", "V2", "V3", "T", "M2", "M3"],
        "units": {"force": "kN", "moment": "kNm", "station": "m", "native_p_positive": "TENSION", "display_n_positive": "COMPRESSION"},
        "absolute_tolerance_native": str(float(ATOL)), "relative_tolerance": str(float(RTOL)),
        "selected_member_count": len(members), "members_without_station_population": missing_members,
        "known_station_count": len(cuts), "station_population_basis": "UNION_OF_RECORDED_NATIVE_CUTS_PER_SELECTED_MEMBER",
        "combination_count": len(definitions), "eligible_combination_count": eligible,
        "excluded_combination_count": len(definitions) - eligible, "expected_pair_count": len(rows),
        "expected_native_row_count": 2 * len(rows), "matched_rows": sum(r["matched_rows"] for r in rows),
        "mismatched_rows": mismatched, "unresolved_pair_count": unresolved,
        "scalar_comparisons": sum(r["scalar_comparisons"] for r in rows),
        "over_tolerance_components": sum(r["over_tolerance_components"] for r in rows),
        "maximum_absolute_difference_by_unit": {u: max((r["maximum_absolute_difference_by_unit"][u] for r in rows), default=0.0) for u in ("kN", "kNm")},
        "source_coverage_status": "SOURCE_COVERAGE_COMPLETE" if coverage_complete else "PARTIAL" if eligible else "NOT_AVAILABLE",
        "replay_status": "NUMERICAL_MISMATCH" if mismatched else "NUMERICAL_MATCH" if coverage_complete else "NOT_PROVEN",
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "reason_counts": dict(Counter(r["reason"] for r in rows if r["reason"])),
        "capture_context_observed": bank.get("capture_context_observed") is True,
        "physical_concurrency_proven": False, "code_rule_qualified": False,
        "analysis_generation_qualified": False, "analysis_order": "NOT_PROVEN",
        "additional_directional_factor_applied": False, "spectrum_scale_reapplied": False,
        "strength_amplification_reapplied": False, "static_candidate_population_changed": False,
        "design_demand_authority": "DENIED", "final_design_eligible": False,
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
        "remaining_design_gates": ["PROJECT_DESIGN_COMBINATION_AND_DIRECTIONAL_RULE_ACCEPTANCE",
            "SPECTRUM_SCALING_MODAL_MASS_AND_ANALYSIS_GENERATION", "GLOBAL_AND_LOCAL_SECOND_ORDER_POLICY",
            "CODE_AUTHORIZED_PMM_DEMAND_ASSEMBLY"],
        "spectral_cases": list(contexts.values()), "combinations": summaries, "rows": rows}
    result["result_sha256"] = digest(result)
    return result


def spectral_projection(result, *, member_id=None, output_case=None, offset=0, limit=200):
    """Filter before paging; a scoped export contains exactly this visible page."""
    rows = [r for r in result["rows"] if (member_id is None or r["member_id"] == member_id)
            and (output_case is None or r["output_case"] == output_case)]
    summary = {k: v for k, v in result.items() if k != "rows"}
    summary.update(member_id_filter=member_id, output_case_filter=output_case,
        filtered_pair_count=len(rows), filtered_status_counts=dict(Counter(r["status"] for r in rows)))
    return deepcopy({"column_spectral_envelopes": summary,
        "demand_page": {"view": VIEW, "member_id": member_id, "output_case": output_case,
            "offset": offset, "limit": limit, "total": len(rows), "rows": rows[offset:offset+limit]}})
