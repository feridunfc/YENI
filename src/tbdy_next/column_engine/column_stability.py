"""CE-04A: source stiffness, length distinctions and minimum-eccentricity references.

Everything is derived in memory from the same sealed CE-01 archive. Neither
output stations nor end offsets are promoted to TS500 free/effective length.
Eccentricity is a station reference comparison, not an end-design verdict.
"""
from collections import Counter
import math
import zlib

from .column_prechecks import _number, _text
from .native_archive import BankError, digest
from .ts500_column import TS500_REFERENCE, minimum_eccentricity_mm, positive, rectangle_properties

SCHEMA = "tbdy.next.column-stability-inputs.v1"
SECTION_FIELDS = ("Area", "As2", "As3", "Torsion", "I22", "I33", "S22", "S33", "Z22", "Z33", "R22", "R33", "pRetVal")
ELASTIC_FIELDS = ("E", "U", "A", "G", "pRetVal")
SOURCE_RTOL, SOURCE_ATOL = 1e-10, 1e-12  # Native m-based quantities; serialization comparison only.
MISSING_BASIS = ("TS500_FREE_LENGTH_NOT_BOUND", "EFFECTIVE_LENGTH_FACTOR_NOT_BOUND",
    "SWAY_CLASSIFICATION_NOT_BOUND", "CREEP_AND_EFFECTIVE_EI_NOT_BOUND", "END_MOMENT_CURVATURE_NOT_BOUND",
    "ANALYSIS_ORDER_NOT_BOUND", "APPROXIMATE_METHOD_APPLICABILITY_NOT_BOUND")
OPTIONAL_ERRORS = (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError, OverflowError)


def _section_row(member, bound, archive):
    name = member["frame_name"]
    context = member.get("context", {})
    frame, geometry = context.get("frame") or {}, member.get("station_geometry") or {}
    row = {"member_id": name, "story": frame.get("story_label"), "column_label": frame.get("column_label"),
        "section_name": frame.get("section_assigned"), "geometry_status": "NOT_PROVEN",
        "property_comparison_status": "NOT_PROVEN", "elastic_status": "NOT_PROVEN", "reason_codes": [],
        "section": None, "property_comparisons": [], "elastic": None, "source_calls": {},
        "lengths": {"object_i_j_m": geometry.get("object_i_j_length_m"),
            "offset_i_m": geometry.get("offset_i_m"), "offset_j_m": geometry.get("offset_j_m"),
            "output_face_span_m": geometry.get("observed_output_face_span_m"),
            "ts500_free_length_ln_mm": None, "effective_length_factor_k": None, "effective_length_lk_mm": None},
        "second_order": {"status": "BLOCKED_INPUTS", "missing_basis": list(MISSING_BASIS),
            "effective_ei_nmm2": None, "critical_load_nk_kn": None, "magnification_factor": None,
            "eq729_status": "NORMATIVE_LENGTH_SYMBOL_CONFLICT"},
        "formal_compliance": "NOT_PROVEN", "design_demand_authority": "DENIED"}
    try:
        if (not bound or bound["member_id"] != name or bound["status"] != "REQUIRED_AREA_BOUNDS_CALCULATED"
                or bound["section_name"] != row["section_name"]):
            raise BankError("ASSIGNED_RECTANGULAR_SECTION_NOT_BOUND")
        t2_exact, t3_exact = _number(bound["b2_cm"], "b2_cm") * 10, _number(bound["b3_cm"], "b3_cm") * 10
        t2, t3 = float(t2_exact), float(t3_exact)
        properties = rectangle_properties(t2, t3)
        row.update(geometry_status="RECTANGLE_CALCULATED", section={**properties, "t2_mm": t2, "t3_mm": t3,
            "t2_mm_decimal": _text(t2_exact), "t3_mm_decimal": _text(t3_exact),
            "e_min_m2_mm": _text(minimum_eccentricity_mm(t3_exact)),
            "e_min_m3_mm": _text(minimum_eccentricity_mm(t2_exact))})
        row["source_calls"].update(bound["source_calls"])
    except OPTIONAL_ERRORS as exc:
        row["reason_codes"].append(str(exc))
        return row
    try:
        observed = archive.native("PropFrame.GetSectProps", "frame_section", row["section_name"], SECTION_FIELDS)
        if observed is None:
            raise BankError("GROSS_SECTION_PROPERTIES_NOT_OBSERVED")
        native, proof = observed
        expected = {"Area": (properties["area_mm2"] / 1e6, "m2"),
            "I22": (properties["i22_mm4"] / 1e12, "m4"), "I33": (properties["i33_mm4"] / 1e12, "m4"),
            "R22": (properties["r22_exact_mm"] / 1000, "m"), "R33": (properties["r33_exact_mm"] / 1000, "m")}
        checks = []
        for key, (calculated, unit) in expected.items():
            value = positive(native[key], key)
            matches = math.isclose(value, calculated, rel_tol=SOURCE_RTOL, abs_tol=SOURCE_ATOL)
            checks.append({"property": key, "native": value, "calculated": calculated, "unit": unit,
                "difference": value - calculated, "status": "NUMERICAL_MATCH" if matches else "NUMERICAL_MISMATCH"})
        row.update(property_comparisons=checks, property_comparison_status="NUMERICAL_MATCH"
            if all(c["status"] == "NUMERICAL_MATCH" for c in checks) else "NUMERICAL_MISMATCH")
        row["source_calls"]["gross_properties"] = proof
    except OPTIONAL_ERRORS as exc:
        row["reason_codes"].append(str(exc))
    try:
        material = context.get("material") or {}
        concrete_name = material.get("concrete_name")
        source = (context.get("source_calls") or {}).get("concrete") or {}
        if (not concrete_name or source.get("api") != "PropMaterial.GetOConcrete"
                or source.get("entity_name") != concrete_name or source.get("units_code") != 6):
            raise BankError("CONCRETE_MATERIAL_IDENTITY_NOT_BOUND")
        observed = archive.native("PropMaterial.GetMPIsotropic", "material", concrete_name, ELASTIC_FIELDS)
        if observed is None:
            raise BankError("MATERIAL_ELASTIC_MODULUS_NOT_OBSERVED")
        native, proof = observed
        e_native = positive(native["E"], "E")
        e_mpa = positive(e_native / 1000, "E_MPa")
        elastic = {"material_name": concrete_name, "native_E_kN_per_m2": e_native, "observed_E_MPa": e_mpa,
            "gross_EI22_kNcm2": positive(e_mpa * properties["i22_mm4"] / 1e5, "gross_EI22"),
            "gross_EI33_kNcm2": positive(e_mpa * properties["i33_mm4"] / 1e5, "gross_EI33"),
            "basis": "OBSERVED_E_TIMES_CALCULATED_GROSS_RECTANGLE_I",
            "effective_stiffness_proven": False, "analysis_stiffness_modifiers_proven": False}
        row.update(elastic_status="OBSERVED_GROSS_STIFFNESS_ONLY", elastic=elastic)
        row["source_calls"]["elastic_modulus"] = proof
    except OPTIONAL_ERRORS as exc:
        row["reason_codes"].append(str(exc))
    return row


def _eccentricity_rows(chain, sections):
    rows = []
    for state in chain["candidates"]:
        name = state["native_key"]["Obj"]
        if name not in sections or state["source_archive_sha256"] != chain["source_archive_sha256"]:
            raise BankError("ECCENTRICITY_SOURCE_BINDING_MISMATCH")
        if state["vector_status"] != "SIGNED_STATIC_SOURCE_VECTOR":
            raise BankError("ECCENTRICITY_REQUIRES_STATIC_SOURCE_VECTOR")
        section = sections[name]["section"]
        n = -_number(state["native_values"]["P"], "P")
        item = {"state_id": state["state_id"], "source_row_id": state["source_row_id"],
            "member_id": name, "native_key": state["native_key"], "native_values": state["native_values"],
            "domain_values": state["domain_values"], "axes": [], "scope": "RECORDED_STATION_REFERENCE_ONLY",
            "design_end_binding_proven": False, "adjusted_demand_vector": None, "final_design_eligible": False}
        for axis, e_field in (("M2", "e_min_m2_mm"), ("M3", "e_min_m3_mm")):
            moment = abs(_number(state["native_values"][axis], axis)) * 100
            e_min = _number(section[e_field], "e_min") if section else None
            finding = {"axis": axis, "n_compression_kn": _text(n), "source_abs_moment_kNcm": _text(moment),
                "e_min_mm": _text(e_min) if e_min is not None else None, "source_eccentricity_mm": None,
                "reference_minimum_moment_kNcm": None, "status": "NOT_PROVEN", "code_ref": "TS500 6.16 REFERENCE_ONLY"}
            if n <= 0:
                finding["status"] = "NONCOMPRESSION_NOT_APPLICABLE"
            elif e_min is not None:
                reference = n * e_min / 10
                finding.update(source_eccentricity_mm=_text(moment * 10 / n),
                    reference_minimum_moment_kNcm=_text(reference), status="BELOW_REFERENCE" if moment < reference
                        else "AT_OR_ABOVE_REFERENCE")
            item["axes"].append(finding)
        rows.append(item)
    return rows


def build_column_stability(bank, chain, prechecks, archive):
    if (bank["source_archive_sha256"] != archive.sha256 or chain["source_archive_sha256"] != archive.sha256
            or prechecks["source_archive_sha256"] != archive.sha256
            or chain["source_bank_result_sha256"] != bank["result_sha256"]
            or prechecks["source_demand_result_sha256"] != chain["result_sha256"]):
        raise BankError("STABILITY_SOURCE_BINDING_MISMATCH")
    bounds = {r["member_id"]: r for r in prechecks["reinforcement_bounds"]["rows"]}
    sections = [_section_row(m, bounds.get(m["frame_name"]), archive) for m in bank["members"]]
    by_name = {r["member_id"]: r for r in sections}
    if len(by_name) != len(sections):
        raise BankError("DUPLICATE_STABILITY_MEMBER")
    eccentricity = _eccentricity_rows(chain, by_name)
    if len({r["state_id"] for r in eccentricity}) != len(eccentricity):
        raise BankError("DUPLICATE_ECCENTRICITY_STATE")
    counts = Counter(a["status"] for r in eccentricity for a in r["axes"])
    per_member = []
    for section in sections:
        states = [r for r in eccentricity if r["member_id"] == section["member_id"]]
        per_member.append({"member_id": section["member_id"], "candidate_count": len(states),
            "m2_counts": dict(Counter(r["axes"][0]["status"] for r in states)),
            "m3_counts": dict(Counter(r["axes"][1]["status"] for r in states))})
    result = {"schema": SCHEMA, "source_run_id": bank.get("run_id"), "source_archive_sha256": archive.sha256,
        "source_demand_result_sha256": chain["result_sha256"], "source_prechecks_result_sha256": prechecks["result_sha256"],
        "reference_url": TS500_REFERENCE, "selected_member_count": len(sections),
        "calculated_section_count": sum(r["section"] is not None for r in sections),
        "distinct_section_count": len({r["section_name"] for r in sections if r["section"] is not None}),
        "native_property_match_count": sum(c["status"] == "NUMERICAL_MATCH" for r in sections for c in r["property_comparisons"]),
        "elastic_member_count": sum(r["elastic"] is not None for r in sections), "sections": sections,
        "source_comparison_tolerances": {"relative": SOURCE_RTOL, "absolute_native_units": SOURCE_ATOL},
        "eccentricity": {"state_count": len(eccentricity), "axis_comparison_count": sum(counts.values()),
            "status_counts": dict(counts), "members": per_member, "rows": eccentricity,
            "scope": "ALL_RECORDED_STATIC_STATIONS_REFERENCE_ONLY", "normative_end_check_proven": False},
        "actual_second_order_applied": False, "design_demand_authority": "DENIED",
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
    result["result_sha256"] = digest(result)
    return result
