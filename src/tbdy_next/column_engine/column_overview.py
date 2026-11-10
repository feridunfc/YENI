"""VS20: readable member summaries of existing, conditional source calculations.

This projection neither selects reinforcement nor constructs a design vector.
Every displayed vector belongs to one unrounded governing source state; ties,
unresolved states, separate shear branches and reference-only stability remain.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import math

from .column_pmm import DIAMETERS, cage_rows
from .csi_geometry import AXIS_CONVENTION
from .native_archive import BankError, digest

SCHEMA = "tbdy.next.column-overview.v1"
LABELS = tuple(f"16Φ{d}" for d in DIAMETERS)
POLICY = "EXPLICIT_CAGE_DISPLAY_ONLY_SAME_SOURCE_VECTOR_V1"
RADIAL = {"WITHIN_SCENARIO_SURFACE", "EXCEEDS_SCENARIO_SURFACE"}
PMM_STATUSES = RADIAL | {"AXIAL_ONLY_SCENARIO", "OUTSIDE_SCENARIO_AXIAL_RANGE", "NUMERIC_UNRESOLVED", "BLOCKED_INPUTS"}


def _order(row):
    key = row["native_key"]
    return (str(key["LoadCase"]), Decimal(str(key["ObjSta"])), str(key["Elm"]),
            Decimal(str(key["ElmSta"])), str(key["StepType"]), Decimal(str(key["StepNum"])), row["state_id"])


def _source(row):
    native = row["native_values"]
    return {"state_id": row["state_id"], "source_row_id": row["source_row_id"],
        "native_key": deepcopy(row["native_key"]), "native_values": deepcopy(native),
        "source_values": {"n_compression_kn": -native["P"], "m2_knm": native["M2"], "m3_knm": native["M3"],
                          "v2_kn": native["V2"], "v3_kn": native["V3"], "t_knm": native["T"]},
        "final_design_eligible": False}


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def station_coverage(rows, *, member_id=None, output_case=None):
    """Count distinct row/role references; never add row counts to role counts."""
    missing, ambiguous, observed, missing_rows, ambiguous_rows = set(), set(), set(), set(), set()
    counts, details = Counter(), []
    for row in sorted(rows, key=lambda r: r["table_row_id"]):
        if member_id is not None and row["member_id"] != member_id:
            continue
        refs = [r for r in row["references"] if output_case is None or r["combination"] == output_case]
        if not refs:
            continue
        row_id = row["table_row_id"]
        if row_id in observed:
            raise BankError("OVERVIEW_DUPLICATE_DESIGN_ROW")
        observed.add(row_id)
        roles = set()
        for ref in refs:
            role = ref["role"]
            if role in roles:
                raise BankError("OVERVIEW_DUPLICATE_DESIGN_ROLE")
            roles.add(role); key = (row_id, role); counts[ref["status"]] += 1
            if not ref["exact_station_found"]:
                missing.add(key); missing_rows.add(row_id)
            if ref["design_station_ambiguous"]:
                ambiguous.add(key); ambiguous_rows.add(row_id)
        if any(r["status"] != "UNIQUE_STATIC_SOURCE_LINK" for r in refs):
            details.append({"table_row_id": row_id, "member_id": row["member_id"], "station_text": row["station_text"],
                "references": [{k: r[k] for k in ("role", "combination", "status", "exact_station_found",
                    "design_station_ambiguous", "source_state_count")} for r in refs]})
    return {"design_row_count": len(observed), "reference_count": sum(counts.values()),
        "link_status_counts": dict(sorted(counts.items())), "missing_exact_reference_count": len(missing),
        "ambiguous_reference_count": len(ambiguous), "overlap_reference_count": len(missing & ambiguous),
        "union_reference_count": len(missing | ambiguous), "missing_exact_row_count": len(missing_rows),
        "ambiguous_row_count": len(ambiguous_rows), "overlap_row_count": len(missing_rows & ambiguous_rows),
        "counting_basis": "DISTINCT_TABLE_ROW_ID_AND_ROLE", "nearest_station_matching_used": False,
        "unresolved_references": details}


def _validate(chain, cages, pmm, shear, sensitivity):
    for result in (chain, cages, pmm, shear, sensitivity):
        if (result["source_run_id"] != chain["source_run_id"]
                or result["source_archive_sha256"] != chain["source_archive_sha256"]
                or result["design_demand_authority"] != "DENIED" or result["formal_compliance"] != "NOT_PROVEN"
                or result["engineering_release"] != "NOT_READY"):
            raise BankError("OVERVIEW_SOURCE_OR_AUTHORITY_MISMATCH")
    for result in (cages, pmm, shear, sensitivity):
        if result["source_demand_result_sha256"] != chain["result_sha256"] or result["axis_convention"] != AXIS_CONVENTION:
            raise BankError("OVERVIEW_DERIVATION_BINDING_MISMATCH")
    if (pmm["source_cages_result_sha256"] != cages["result_sha256"]
            or shear["source_cages_result_sha256"] != cages["result_sha256"]
            or pmm["source_stability_result_sha256"] != sensitivity["source_stability_result_sha256"]
            or any(r["selected_design"] is not None for r in (cages, pmm, shear))
            or any(r["actual_second_order_applied"] is not False for r in (pmm, shear, sensitivity))
            or pmm["minimum_eccentricity_applied"] is not False or shear["ve_status"] != "NOT_PROVEN"
            or pmm["pmm_population_reduced"] is not False or shear["source_population_reduced"] is not False
            or sensitivity["source_population_reduced"] is not False):
        raise BankError("OVERVIEW_SCOPE_MISMATCH")
    states = {s["state_id"]: s for s in chain["candidates"]}
    members = {m["member_id"]: m for m in cages["members"]}
    proposals = {(r["member_id"], r["label"]): r for r in cage_rows(cages)}
    if (len(states) != len(chain["candidates"]) or len(states) != chain["static_candidate_count"]
            or len(members) != len(cages["members"]) or set(members) != {m["member_id"] for m in chain["members"]}
            or set(proposals) != {(m, label) for m in members for label in LABELS}):
        raise BankError("OVERVIEW_POPULATION_MISMATCH")
    indexes = []
    for result, kind in ((pmm, "pmm"), (shear, "shear"), (sensitivity, "sensitivity")):
        index = {}
        for row in result["rows"]:
            source = states.get(row["state_id"])
            if (source is None or row["member_id"] != source["native_key"]["Obj"]
                    or any(row[k] != source[k] for k in ("source_row_id", "native_key", "native_values"))
                    or row["final_design_eligible"] is not False):
                raise BankError("OVERVIEW_STATE_BINDING_MISMATCH")
            if kind == "sensitivity":
                key = (row["state_id"], row["axis"])
            else:
                proposal = proposals.get((row["member_id"], row["candidate_label"]))
                if proposal is None or row["candidate_id"] != proposal["candidate_id"]:
                    raise BankError("OVERVIEW_CANDIDATE_BINDING_MISMATCH")
                key = (row["state_id"], row["candidate_label"])
                if kind == "shear":
                    key += (row["shear_axis"],)
                elif (row["status"] not in PMM_STATUSES
                        or (row["status"] in RADIAL) != (row["utilization"] is not None)
                        or (row["utilization"] is not None and not _finite(row["utilization"]))
                        or (row["status"] == "AXIAL_ONLY_SCENARIO" and not _finite(row.get("axial_utilization")))):
                    raise BankError("OVERVIEW_PMM_STATUS_MISMATCH")
            if key in index:
                raise BankError("OVERVIEW_DUPLICATE_ASSESSMENT")
            index[key] = row
        expected = ({(state, axis) for state in states for axis in ("M2", "M3")} if kind == "sensitivity" else
            {(state, label, axis) for state in states for label in LABELS for axis in ("V2", "V3")} if kind == "shear" else
            {(state, label) for state in states for label in LABELS})
        if set(index) != expected:
            raise BankError("OVERVIEW_ASSESSMENT_POPULATION_MISMATCH")
        indexes.append(index)
    return states, members, proposals, indexes


def _maximum(rows, field):
    maximum = max((r[field] for r in rows), default=None)
    return maximum, [_source(r) for r in rows if r[field] == maximum]


def _pmm_summary(rows):
    counts = Counter(r["status"] for r in rows)
    radial = [r for r in rows if r["status"] in RADIAL]
    axial = [r for r in rows if r["status"] == "AXIAL_ONLY_SCENARIO"]
    outside = [r for r in rows if r["status"] == "OUTSIDE_SCENARIO_AXIAL_RANGE"]
    incomplete = [r for r in rows if r["status"] in ("NUMERIC_UNRESOLVED", "BLOCKED_INPUTS")]
    maximum, radial_ties = _maximum(radial, "utilization")
    axial_max, axial_ties = _maximum(axial, "axial_utilization")
    if outside:
        status, basis, critical = "AXIAL_RANGE_EXCEEDED", "AXIAL_LIMIT_FINDING", [_source(r) for r in outside]
    elif radial:
        status = "PARTIAL_NUMERICAL_COVERAGE" if incomplete else "RADIAL_PMM_RESOLVED"
        basis, critical = "MAXIMUM_RESOLVED_RADIAL_PMM", radial_ties
    elif axial:
        status = "PARTIAL_NUMERICAL_COVERAGE" if incomplete else "AXIAL_ONLY_REFERENCES"
        basis, critical = "MAXIMUM_AXIAL_ONLY_REFERENCE", axial_ties
    elif rows:
        status, basis, critical = "NUMERICAL_RESULTS_UNAVAILABLE", "UNRESOLVED_SOURCE_RECORD", [_source(r) for r in rows]
    else:
        status, basis, critical = "NO_STATIC_STATES", None, []
    return {"status": status, "status_counts": dict(sorted(counts.items())), "static_state_count": len(rows),
        "radial_pmm_count": len(radial), "axial_only_count": len(axial), "axial_outside_count": len(outside),
        "unresolved_count": counts["NUMERIC_UNRESOLVED"], "blocked_count": counts["BLOCKED_INPUTS"],
        "maximum_resolved_utilization": maximum, "radial_critical_states": radial_ties,
        "maximum_axial_utilization": axial_max, "axial_critical_states": axial_ties,
        "axial_outside_states": [_source(r) for r in outside],
        "unresolved_states": [{**_source(r), "status": r["status"], "reason": r["reason"]} for r in incomplete],
        "representative_basis": basis, "representative": critical[0] if critical else None,
        "critical_state_count": len(critical), "critical_states": critical,
        "all_states_have_radial_pmm": bool(rows) and len(radial) == len(rows),
        "trial_ratios_used": False, "rounded_values_used_for_selection": False}


def _shear_summary(rows, representative):
    summaries, limit_findings = [], []
    for row in rows:
        calculation = row["calculation"]
        if not calculation:
            continue
        for name in ("ts500_web", "tbdy_brittle"):
            if calculation["source_within_"+name+"_reference"] is False:
                limit_findings.append({**_source(row), "axis": row["shear_axis"], "reference": name,
                    "reference_limit_kn": calculation[name+"_reference_kn"],
                    "source_signed_v_kn": row["native_values"][row["shear_axis"]],
                    "column_applicability": calculation["ts500_web_column_applicability"] if name == "ts500_web" else "NOT_PROVEN",
                    "design_demand_qualified": False})
    for axis in ("V2", "V3"):
        axis_rows = [r for r in rows if r["shear_axis"] == axis]
        for branch in ("ts500", "zero_concrete"):
            valid = []
            for row in axis_rows:
                values = row["calculation"]["branches"][branch] if row["calculation"] else None
                if values and values["source_utilization"] is not None:
                    if not _finite(values["source_utilization"]):
                        raise BankError("OVERVIEW_SHEAR_RATIO_INVALID")
                    valid.append({**row, "ratio": values["source_utilization"]})
            maximum, critical = _maximum(valid, "ratio")
            summaries.append({"axis": axis, "branch": branch, "numeric_count": len(valid),
                "state_count": len(axis_rows), "maximum_source_utilization": maximum,
                "critical_source_states": critical, "source_exceedance_count": sum(r["ratio"] > 1 for r in valid)})
    numeric = sum(r["numeric_count"] for r in summaries)
    expected = len(rows) * 2
    branch_exceeded = sum(r["source_exceedance_count"] for r in summaries)
    exceeded = branch_exceeded + len(limit_findings)
    status = ("NO_STATIC_STATES" if not rows else "SOURCE_REFERENCE_EXCEEDED" if exceeded else
        "PARTIAL_SHEAR_REFERENCES" if numeric < expected else "CONDITIONAL_SHEAR_REFERENCES")
    same = [deepcopy(r) for r in rows if representative and r["state_id"] == representative["state_id"]]
    return {"status": status, "numeric_reference_count": numeric, "expected_reference_count": expected,
        "source_exceedance_count": exceeded, "branch_source_exceedance_count": branch_exceeded,
        "other_limit_exceedance_count": len(limit_findings), "other_limit_findings": limit_findings,
        "branches": summaries, "at_pmm_representative": same,
        "summary_scope": "ALL_FILTERED_STATIC_STATES_SEPARATE_GOVERNING_VECTORS", "ve_status": "NOT_PROVEN",
        "selected_concrete_branch": None}


def _second_order(rows):
    counts, findings = Counter(), []
    for row in rows:
        for scenario in row["scenarios"]:
            for ref in scenario["at_reference_lengths"]:
                counts[ref["status"]] += 1
                if ref["status"] in ("NONPOSITIVE_SOURCE_DENOMINATOR", "NUMERICALLY_NEAR_ZERO"):
                    findings.append({"state_id": row["state_id"], "source_row_id": row["source_row_id"],
                        "native_key": deepcopy(row["native_key"]), "axis": row["axis"],
                        "rm_scenario": scenario["creep_ratio_scenario"], "lk_over_i_reference": ref["lk_over_i_reference"],
                        "source_denominator": ref["source_denominator"], "status": ref["status"]})
    return {"status": "NOT_PROVEN", "state_axis_count": len(rows), "reference_count": sum(counts.values()),
        "denominator_status_counts": dict(sorted(counts.items())), "nonpositive_reference_count": len(findings),
        "nonpositive_source_state_count": len({r["state_id"] for r in findings}), "reference_findings": findings,
        "actual_ln_mm": None, "actual_k": None, "actual_lk_mm": None, "actual_cm": None, "actual_beta": None,
        "actual_second_order_applied": False, "actual_stability_failure_proven": False}


def build_column_overview(chain, cages, pmm, shear, sensitivity, *, member_id=None, output_case=None):
    states, members, proposals, (pmm_index, shear_index, sensitivity_index) = _validate(chain, cages, pmm, shear, sensitivity)
    selected_members = sorted(m for m in members if member_id is None or m == member_id)
    grouped = defaultdict(list)
    for state in sorted(states.values(), key=_order):
        if output_case is None or state["native_key"]["LoadCase"] == output_case:
            grouped[state["native_key"]["Obj"]].append(state)
    rows = []
    for name in selected_members:
        source_states = grouped[name]
        second = _second_order([sensitivity_index[(s["state_id"], axis)] for s in source_states for axis in ("M2", "M3")])
        row = {"member_id": name, "story": members[name]["story"], "column_label": members[name]["column_label"],
            "static_state_count": len(source_states), "static_combinations": sorted({s["native_key"]["LoadCase"] for s in source_states}),
            "station_coverage": station_coverage(chain["design_summary"]["rows"], member_id=name, output_case=output_case),
            "second_order": second, "scenarios": []}
        for label in LABELS:
            proposal = proposals[(name, label)]
            pm = _pmm_summary([pmm_index[(s["state_id"], label)] for s in source_states])
            sh = _shear_summary([shear_index[(s["state_id"], label, axis)] for s in source_states for axis in ("V2", "V3")], pm["representative"])
            row["scenarios"].append({"candidate_id": proposal["candidate_id"], "candidate_label": label,
                "as_cm2": proposal.get("as_cm2"), "geometry_status": proposal["geometry_status"], "pmm": pm, "shear": sh,
                "design_values": {"Nd_kn": None, "M2d_knm": None, "M3d_knm": None, "status": "NOT_PROVEN"},
                "selected_design": False, "final_design_eligible": False})
        rows.append(row)
    coverage = station_coverage(chain["design_summary"]["rows"], member_id=member_id, output_case=output_case)
    result = {"schema": SCHEMA, "policy": POLICY, "axis_convention": AXIS_CONVENTION,
        "source_run_id": chain["source_run_id"], "source_archive_sha256": chain["source_archive_sha256"],
        "source_demand_result_sha256": chain["result_sha256"], "source_cages_result_sha256": cages["result_sha256"],
        "source_pmm_result_sha256": pmm["result_sha256"], "source_shear_result_sha256": shear["result_sha256"],
        "source_sensitivity_result_sha256": sensitivity["result_sha256"],
        "member_id_filter": member_id, "output_case_filter": output_case,
        "candidate_labels": list(LABELS), "default_display_candidate": LABELS[0], "automatic_design_selection": False,
        "member_count": len(rows), "static_state_count": sum(r["static_state_count"] for r in rows),
        "members_without_static_states": sum(r["static_state_count"] == 0 for r in rows),
        "source_combination_classifications": dict(sorted(chain["classification_counts"].items())),
        "spectral_design_vectors_formed": False, "station_coverage": coverage,
        "nonpositive_reference_count": sum(r["second_order"]["nonpositive_reference_count"] for r in rows),
        "members_with_nonpositive_references": sum(r["second_order"]["nonpositive_reference_count"] > 0 for r in rows),
        "rows": rows, "underlying_source_population_reduced": False, "selected_design": None,
        "actual_second_order_applied": False, "design_demand_authority": "DENIED",
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
    result["result_sha256"] = digest(result)
    return result
