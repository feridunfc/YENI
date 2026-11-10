"""CE-04C: explicit effective-length/stiffness parameter families, offline.

Every recorded static station stays in the comparison population. Observed
Ec and gross I feed three illustrative Rm values; these do not establish an
actual EI range. Neither geometry length nor output offsets supply lk or ln.
"""
from collections import Counter, defaultdict
from copy import deepcopy

from .column_prechecks import _number, _text
from .column_stability import OPTIONAL_ERRORS
from .csi_geometry import AXIS_CONVENTION
from .native_archive import BankError, digest, finite
from .sensitivity_kernel import CREEP_SCENARIOS, NUMERIC_ZERO_BAND, stiffness_family, source_length_scenarios
from .ts500_column import TS500_REFERENCE, positive

SCHEMA = "tbdy.next.column-length-stiffness-sensitivity.v1"
POLICY = {"id": "TS500_EQ721_RM_0_0P5_1_REFERENCE_FAMILY", "stiffness_method": "TS500_7_21",
    "creep_ratio_scenarios": list(CREEP_SCENARIOS), "actual_creep_ratio": None, "actual_ei_interval_proven": False,
    "radius_basis": "TS500_RECTANGLE_0_30_BENDING_DIMENSION", "reference_slendernesses": [22, 40, 100],
    "reference_22": "SWAY_PERMITTED_NEGLECT_BOUND_IF_APPLICABILITY_PROVEN",
    "reference_40": "SWAY_PREVENTED_UPPER_CAP_NOT_A_GENERAL_NEGLECT_LIMIT",
    "reference_100": "APPROXIMATE_METHOD_SLENDERNESS_CEILING_ONLY",
    "critical_length_meaning": "EQ724_ZERO_DENOMINATOR_NK_EQUALS_1_3_NSOURCE_NOT_ALLOWED_LENGTH",
    "source_axial_force_is_design_nd": False, "numeric_zero_band": NUMERIC_ZERO_BAND}
OPEN_BASIS = ["SOURCE_AXIAL_FORCE_NOT_QUALIFIED_AS_DESIGN_ND", "ACTUAL_LN_K_LK_NOT_BOUND",
    "ACTUAL_RM_AND_EFFECTIVE_EI_NOT_BOUND", "SWAY_AND_CM_NOT_BOUND", "LINEAR_ELASTIC_ANALYSIS_BASIS_NOT_PROVEN",
    "CONSTANT_SECTION_AND_AXIAL_FORCE_ALONG_HEIGHT_NOT_PROVEN", "MINIMUM_ECCENTRICITY_AND_END_MOMENT_BASIS_NOT_PROVEN",
    "ANALYSIS_GENERATION_NOT_QUALIFIED", "EQ729_LENGTH_SYMBOL_CONFLICT_UNCHANGED"]


def _axis_references(stability):
    rows = []
    for member in stability["sections"]:
        for axis, inertia, exact, approx in (("M2", "i22_mm4", "r22_exact_mm", "r22_ts500_approx_mm"),
                                             ("M3", "i33_mm4", "r33_exact_mm", "r33_ts500_approx_mm")):
            row = {"member_id": member["member_id"], "story": member["story"], "section_name": member["section_name"],
                "axis": axis, "status": "BLOCKED_INPUTS", "reason": None, "ec_mpa_observed": None,
                "gross_inertia_mm4": None, "radius_exact_mm": None, "radius_reference_mm": None,
                "length_22i_mm": None, "length_40i_mm": None, "length_100i_mm": None,
                "source_calls": member["source_calls"], "scenarios": [], "actual_effective_length_lk_mm": None}
            try:
                if (member["geometry_status"] != "RECTANGLE_CALCULATED"
                        or member["property_comparison_status"] != "NUMERICAL_MATCH"
                        or member["elastic_status"] != "OBSERVED_GROSS_STIFFNESS_ONLY"):
                    raise BankError("SENSITIVITY_RECTANGLE_AND_ELASTIC_SOURCE_NOT_BOUND")
                sec, elastic = member["section"], member["elastic"]
                ec, ic = positive(elastic["observed_E_MPa"], "Ec"), positive(sec[inertia], "Ic")
                radius, radius_exact = positive(sec[approx], "radius_reference"), positive(sec[exact], "radius_exact")
                family = stiffness_family(ec_mpa=ec, ic_mm4=ic, radius_mm=radius)
                row.update(status="STIFFNESS_PARAMETER_FAMILY_CALCULATED", ec_mpa_observed=ec, gross_inertia_mm4=ic,
                    radius_exact_mm=radius_exact, radius_reference_mm=radius,
                    length_22i_mm=22*radius, length_40i_mm=40*radius, length_100i_mm=100*radius, scenarios=family)
            except OPTIONAL_ERRORS as exc:
                row["reason"] = str(exc)
            row["axis_reference_id"] = "LENGTH-AXIS-"+digest({"source": stability["result_sha256"], "member": row["member_id"],
                "axis": axis, "policy": POLICY})[:24]
            rows.append(row)
    return rows


def _axial_profiles(chain, kinematics):
    groups = defaultdict(list)
    for state in chain["candidates"]:
        key = state["native_key"]
        groups[(key["Obj"], key["LoadCase"])].append(state)
    pairs = {(r["member_id"], r["output_case"]): r for r in kinematics["rows"]}
    profiles = []
    for (member, case), states in sorted(groups.items()):
        values = [-_number(r["native_values"]["P"], "P") for r in states]
        lo, hi = min(values), max(values)
        link = pairs.get((member, case))
        pair = (link or {}).get("force_pair")
        end_values = {end: -_number(pair[end]["native_values"]["P"], "P") for end in ("i", "j")} if pair else {}
        profiles.append({"member_id": member, "output_case": case, "recorded_static_station_count": len(states),
            "recorded_min_n_kn": _text(lo), "recorded_max_n_kn": _text(hi), "recorded_range_kn": _text(hi-lo),
            "recorded_values_status": "RECORDED_AXIAL_VALUES_DIFFER" if hi != lo else "RECORDED_AXIAL_VALUES_EQUAL",
            "source_end_link_id": link["link_id"] if link else None,
            "n_i_kn": _text(end_values["i"]) if pair else None, "n_j_kn": _text(end_values["j"]) if pair else None,
            "end_n_j_minus_i_kn": _text(end_values["j"]-end_values["i"]) if pair else None,
            "constant_axial_force_along_height_proven": False, "approximate_method_applicability_proven": False})
    return profiles


def build_column_sensitivity(chain, stability, kinematics):
    if (stability.get("axis_convention") != AXIS_CONVENTION or kinematics.get("axis_convention") != AXIS_CONVENTION
            or stability["source_run_id"] != chain["source_run_id"] or kinematics["source_run_id"] != chain["source_run_id"]
            or stability["source_archive_sha256"] != chain["source_archive_sha256"]
            or kinematics["source_archive_sha256"] != chain["source_archive_sha256"]
            or stability["source_demand_result_sha256"] != chain["result_sha256"]
            or kinematics["source_demand_result_sha256"] != chain["result_sha256"]
            or kinematics["source_bank_result_sha256"] != chain["source_bank_result_sha256"]):
        raise BankError("SENSITIVITY_SOURCE_BINDING_MISMATCH")
    axes = _axis_references(stability)
    by_axis = {(r["member_id"], r["axis"]): r for r in axes}
    if len(by_axis) != len(axes):
        raise BankError("SENSITIVITY_DUPLICATE_MEMBER_AXIS")
    candidates = chain["candidates"]
    if len({r["state_id"] for r in candidates}) != len(candidates):
        raise BankError("SENSITIVITY_DUPLICATE_STATE")
    routes = {r["combination"] for r in chain["combinations"] if r["classification"] == "STATIC_LINEAR_ADD"}
    rows = []
    for state in candidates:
        key = state["native_key"]
        if (state["source_archive_sha256"] != chain["source_archive_sha256"]
                or state["vector_status"] != "SIGNED_STATIC_SOURCE_VECTOR" or key["LoadCase"] not in routes
                or key["StepType"] != "Single Value" or key["StepNum"] != 0):
            raise BankError("SENSITIVITY_STATE_SCOPE_MISMATCH")
        for axis in ("M2", "M3"):
            reference = by_axis.get((key["Obj"], axis))
            if reference is None:
                raise BankError("SENSITIVITY_STATE_MEMBER_NOT_BOUND")
            row = {"member_id": key["Obj"], "story": reference["story"], "axis": axis,
                "state_id": state["state_id"], "source_row_id": state["source_row_id"], "native_key": key,
                "native_values": state["native_values"], "source_call_id": state["source_call_id"],
                "source_row_index": state["source_row_index"], "axis_reference_id": reference["axis_reference_id"],
                "n_source_compression_kn": None, "status": "BLOCKED_INPUTS", "reason": None, "scenarios": [],
                "actual_lk_mm": None, "cm": None, "beta": None, "magnified_design_moment": None,
                "approximate_method_applicability_proven": False, "final_design_eligible": False}
            try:
                n_decimal = -_number(state["native_values"]["P"], "P")
                n = finite(float(n_decimal), "N_source")
                row["n_source_compression_kn"] = _text(n_decimal)
                if reference["status"] != "STIFFNESS_PARAMETER_FAMILY_CALCULATED":
                    raise BankError(reference["reason"] or "SENSITIVITY_AXIS_INPUTS_MISSING")
                row.update(scenarios=source_length_scenarios(source_n_compression_kn=n, family=reference["scenarios"],
                    radius_mm=reference["radius_reference_mm"]), status="SOURCE_LENGTH_REFERENCES_CALCULATED"
                        if n > 0 else "NONCOMPRESSION_NOT_APPLICABLE")
            except OPTIONAL_ERRORS as exc:
                row["reason"] = str(exc)
            rows.append(row)
    profiles = _axial_profiles(chain, kinematics)
    result = {"schema": SCHEMA, "axis_convention": AXIS_CONVENTION, "source_run_id": chain["source_run_id"],
        "source_archive_sha256": chain["source_archive_sha256"], "source_bank_result_sha256": chain["source_bank_result_sha256"],
        "source_demand_result_sha256": chain["result_sha256"], "source_stability_result_sha256": stability["result_sha256"],
        "source_kinematics_result_sha256": kinematics["result_sha256"], "policy": deepcopy(POLICY), "axes": axes, "rows": rows,
        "selected_member_count": stability["selected_member_count"], "static_state_count": len(candidates),
        "state_axis_count": len(rows), "calculated_axis_count": sum(r["status"] == "STIFFNESS_PARAMETER_FAMILY_CALCULATED" for r in axes),
        "stiffness_scenario_count": sum(len(r["scenarios"]) for r in axes),
        "euler_reference_count": sum(len(s["length_references"]) for r in axes for s in r["scenarios"]),
        "zero_length_reference_count": sum(s["zero_denominator_length_mm"] is not None for r in rows for s in r["scenarios"]),
        "source_denominator_count": sum(len(s["at_reference_lengths"]) for r in rows for s in r["scenarios"]),
        "status_counts": dict(Counter(r["status"] for r in rows)), "reason_counts": dict(Counter(r["reason"] for r in rows if r["reason"])),
        "denominator_status_counts": dict(Counter(v["status"] for r in rows for s in r["scenarios"] for v in s["at_reference_lengths"])),
        "axial_profiles": profiles, "axial_profile_status_counts": dict(Counter(r["recorded_values_status"] for r in profiles)),
        "source_population_reduced": False, "references": {"TS500 7.6.1–7.6.2 / 7.17–7.24": TS500_REFERENCE},
        "open_basis": list(OPEN_BASIS), "actual_second_order_applied": False, "actual_creep_ratio": None,
        "actual_effective_length_lk_mm": None, "actual_sway_classification": None, "actual_cm": None, "actual_beta": None,
        "magnified_design_moments": None, "approximate_method_applicability_proven": False, "analysis_order": "NOT_PROVEN",
        "design_demand_authority": "DENIED", "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
    result["result_sha256"] = digest(result)
    return result


def sensitivity_summaries(result):
    """Most restrictive mathematical length per member/axis; retain all ties."""
    grouped = defaultdict(list)
    for row in result["rows"]:
        grouped[(row["member_id"], row["axis"])].append(row)
    summaries = []
    for axis in result["axes"]:
        states = grouped[(axis["member_id"], axis["axis"])]
        valid = [r for r in states if r["status"] == "SOURCE_LENGTH_REFERENCES_CALCULATED"]
        maximum = max((_number(r["n_source_compression_kn"], "N") for r in valid), default=None)
        ties = [r for r in valid if _number(r["n_source_compression_kn"], "N") == maximum]
        summary = {k: axis[k] for k in ("member_id", "story", "axis", "section_name", "radius_reference_mm", "length_100i_mm")}
        summary.update(recorded_state_count=len(states), compression_state_count=len(valid),
            maximum_source_n_kn=_text(maximum) if maximum is not None else None,
            critical_source_states=[{"state_id": r["state_id"], "source_row_id": r["source_row_id"], "native_key": r["native_key"]} for r in ties],
            minimum_zero_lengths_mm=[s["zero_denominator_length_mm"] for s in ties[0]["scenarios"]] if ties else [],
            zero_lengths_exceed_100i=[s["zero_length_exceeds_100i_reference"] for s in ties[0]["scenarios"]] if ties else [],
            status_counts=dict(Counter(r["status"] for r in states)), actual_design_critical_state_selected=False)
        summaries.append(summary)
    return summaries
