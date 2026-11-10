"""Source-preserving extrema and TBDY 7.3.2.1 reinforcement-area bounds.

Extrema are navigation aids, never a replacement PMM demand population. The
reinforcement calculation gives required area bounds, not a provided cage or
capacity. The original native bank and CE-02A result remain unchanged.
"""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from .native_archive import BankError, digest

SCHEMA = "tbdy.next.column-prechecks.v1"
TBDY_REFERENCE = "https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf"
CRITERIA = (
    ("N_COMPRESSION_MAX", "N_compression_kN", "P", -1, "POSITIVE", "kN"),
    ("N_TENSION_MAX", "N_compression_kN", "P", -1, "NEGATIVE", "kN"),
    ("M2_ABS_MAX", "M2_kNcm", "M2", 100, "ABS", "kN-cm"),
    ("M3_ABS_MAX", "M3_kNcm", "M3", 100, "ABS", "kN-cm"),
    ("V2_ABS_MAX", "V2_kN", "V2", 1, "ABS", "kN"),
    ("V3_ABS_MAX", "V3_kN", "V3", 1, "ABS", "kN"),
    ("T_ABS_MAX", "T_kNcm", "T", 100, "ABS", "kN-cm"),
)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise BankError("PRECHECK_NUMBER_INVALID:" + label)
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise BankError("PRECHECK_NUMBER_INVALID:" + label) from exc
    if not number.is_finite() or (number and not -100 <= number.adjusted() <= 100):
        raise BankError("PRECHECK_NUMBER_INVALID:" + label)
    return number


def _text(value):
    return format(value.normalize(), "f")


def critical_selection(chain, population, *, member_id=None, output_case=None):
    """Recompute within the explicit filter; keep every exact tie and full vector."""
    routes = [r["combination"] for r in chain["combinations"] if r["classification"] == "STATIC_LINEAR_ADD"
              and (output_case is None or r["combination"] == output_case)]
    members = [r for r in population if member_id is None or r["member_id"] == member_id]
    allowed = {r["member_id"] for r in members}
    grouped = defaultdict(list)
    for state in chain["candidates"]:
        key = state["native_key"]
        if key["Obj"] in allowed and (output_case is None or key["LoadCase"] == output_case):
            grouped[key["Obj"]].append(state)
    selected, summaries = [], []
    for member in members:
        name = member["member_id"]
        states = grouped[name]
        if len({r["state_id"] for r in states}) != len(states):
            raise BankError("PRECHECK_DUPLICATE_STATE")
        if any(r["source_archive_sha256"] != chain["source_archive_sha256"]
               or r["vector_status"] != "SIGNED_STATIC_SOURCE_VECTOR"
               or r["native_key"]["LoadCase"] not in routes for r in states):
            raise BankError("PRECHECK_STATE_SCOPE_MISMATCH")
        expected = member["observed_station_count"] * len(routes) if member["observed_station_count"] and routes else None
        summary = {"member_id": name, "candidate_count": len(states), "expected_static_states": expected,
            "source_subset_coverage": "COMPLETE" if expected and expected == len(states) else
                "PARTIAL" if expected else "UNRESOLVED", "criteria": []}
        criteria_by_state = defaultdict(list)
        for criterion, component, native_component, factor, mode, unit in CRITERIA:
            # Float multiplication can collapse distinct native moments to one
            # displayed value. Select and convert from the native decimal value.
            values = [(r, _number(r["native_values"][native_component], native_component) * factor) for r in states]
            values = [(r, v) for r, v in values if mode == "ABS" or (mode == "POSITIVE" and v > 0)
                      or (mode == "NEGATIVE" and v < 0)]
            maximum = max((abs(v) for _, v in values), default=None)
            ties = [r for r, v in values if abs(v) == maximum]
            status = ("NO_CANDIDATES" if not states else "NO_OBSERVED_COMPRESSION" if mode == "POSITIVE" and not values
                      else "NO_OBSERVED_TENSION" if mode == "NEGATIVE" and not values
                      else "ALL_ZERO" if maximum == 0 else "OBSERVED_EXTREMUM")
            summary["criteria"].append({"criterion": criterion, "component": component, "status": status,
                "magnitude": _text(maximum) if maximum is not None else None, "unit": unit,
                "state_ids": sorted(r["state_id"] for r in ties)})
            for state in ties:
                criteria_by_state[state["state_id"]].append(criterion)
        for state in sorted(states, key=lambda r: r["state_id"]):
            if state["state_id"] in criteria_by_state:
                selected.append({"state_id": state["state_id"], "source_row_id": state["source_row_id"],
                    "member_id": name, "criteria": criteria_by_state[state["state_id"]],
                    "native_key": state["native_key"], "native_values": state["native_values"],
                    "domain_values": state["domain_values"], "final_design_eligible": False})
        summaries.append(summary)
    result = {"scope": "OBSERVED_STATIONS_AND_DEFINED_DIRECT_STATIC_COMBINATIONS", "member_id": member_id,
        "output_case": output_case, "static_combinations": sorted(routes), "members": summaries,
        "candidate_count": sum(r["candidate_count"] for r in summaries), "critical_state_count": len(selected),
        "rows": selected, "pmm_population_reduced": False, "comparison_basis": "NATIVE_DECIMAL_VALUES",
        "source_demand_result_sha256": chain["result_sha256"]}
    result["result_sha256"] = digest(result)
    return result


def _reinforcement_bounds(bank, chain):
    rows, comparisons = [], []
    by_member = {}
    for member in bank["members"]:
        context = member.get("context", {})
        geometry = context.get("geometry") or {}
        frame = context.get("frame") or {}
        sources = context.get("source_calls") or {}
        item = {"member_id": member["frame_name"], "story": frame.get("story_label"),
            "section_name": frame.get("section_assigned"), "status": "NOT_PROVEN", "reason": None,
            "code_ref": "TBDY 2018 7.3.2.1 AREA_RATIO_ONLY", "gross_area_cm2": None,
            "minimum_as_cm2": None, "maximum_as_cm2": None, "provided_as_cm2": None,
            "physical_cage_proven": False, "formal_compliance": "NOT_PROVEN", "asmin_source_counts": {}}
        try:
            rect, assignment = sources.get("section_rectangle", {}), sources.get("frame_section", {})
            if (not item["section_name"] or geometry.get("section_name") != item["section_name"]
                    or geometry.get("source_unit_system") != "kN-m-C"
                    or rect.get("api") != "PropFrame.GetRectangle" or rect.get("entity_name") != item["section_name"]
                    or rect.get("units_code") != 6 or assignment.get("api") != "FrameObj.GetSection"
                    or assignment.get("entity_name") != member["frame_name"] or assignment.get("units_code") != 6):
                raise BankError("ASSIGNED_RECTANGULAR_SECTION_NOT_BOUND")
            b2, b3 = (_number(geometry.get(k), k) for k in ("T2_native_m", "T3_native_m"))
            if min(b2, b3) <= 0:
                raise BankError("POSITIVE_RECTANGULAR_DIMENSIONS_REQUIRED")
            area = b2 * b3 * Decimal(10000)
            item.update(status="REQUIRED_AREA_BOUNDS_CALCULATED", b2_cm=_text(b2 * 100), b3_cm=_text(b3 * 100),
                gross_area_cm2=_text(area), minimum_as_cm2=_text(area * Decimal("0.01")),
                maximum_as_cm2=_text(area * Decimal("0.04")), source_calls={"rectangle": rect, "assignment": assignment})
        except (ValueError, TypeError, KeyError) as exc:
            item["reason"] = str(exc)
        rows.append(item); by_member[item["member_id"]] = item
    summary = chain["design_summary"]
    unit = (summary.get("source") or {}).get("field_units", {}).get("AsMin")
    for design_row in summary["rows"]:
        member = by_member.get(design_row["member_id"])
        comparison = {"table_row_id": design_row["table_row_id"], "source_row_index": design_row["source_row_index"],
            "member_id": design_row["member_id"], "source_asmin_raw": design_row["native_design_row"].get("AsMin"),
            "source_unit": unit, "source_asmin_cm2": None, "calculated_asmin_cm2": member["minimum_as_cm2"] if member else None,
            "status": "NOT_PROVEN", "difference_cm2": None, "reason": None}
        try:
            if (not member or member["status"] != "REQUIRED_AREA_BOUNDS_CALCULATED"
                    or not design_row["identity_matches_source_member"]):
                raise BankError("DESIGN_SECTION_IDENTITY_NOT_BOUND")
            if unit != "m2":
                raise BankError("ASMIN_FIELD_UNIT_NOT_OBSERVED_AS_M2")
            source = _number(comparison["source_asmin_raw"], "AsMin") * 10000
            if source < 0:
                raise BankError("ASMIN_NEGATIVE")
            calculated = Decimal(member["minimum_as_cm2"])
            difference = source - calculated
            comparison.update(source_asmin_cm2=_text(source), difference_cm2=_text(difference),
                status="NUMERICAL_MATCH" if difference == 0 else "SOURCE_ABOVE_REFERENCE" if difference > 0
                    else "SOURCE_BELOW_REFERENCE")
        except (ValueError, TypeError, KeyError) as exc:
            comparison["reason"] = str(exc)
        comparisons.append(comparison)
    for member in rows:
        member["asmin_source_counts"] = dict(Counter(c["status"] for c in comparisons if c["member_id"] == member["member_id"]))
    return {"code_ref": "TBDY 2018 7.3.2.1", "reference_url": TBDY_REFERENCE,
        "formula": "Ac=b2*b3; As_min=0.01*Ac; As_max=0.04*Ac", "scope": "SDY_COLUMN_AREA_RATIO_BOUNDS_ONLY",
        "applicability_proven": False, "provided_reinforcement_checked": False, "splice_checked": False,
        "bar_diameter_and_count_checked": False, "boundary_inclusive": True,
        "selected_member_count": len(rows), "calculated_member_count": sum(r["status"] == "REQUIRED_AREA_BOUNDS_CALCULATED" for r in rows),
        "rows": rows, "source_comparisons": comparisons, "source_comparison_counts": dict(Counter(c["status"] for c in comparisons)),
        "comparison_authority": "SOURCE_NUMERICAL_ONLY", "formal_compliance": "NOT_PROVEN"}


def build_column_prechecks(bank, chain):
    if (chain["source_archive_sha256"] != bank["source_archive_sha256"]
            or chain["source_bank_result_sha256"] != bank["result_sha256"]):
        raise BankError("PRECHECK_SOURCE_BINDING_MISMATCH")
    stations = defaultdict(set)
    for state in bank["force_states"]:
        stations[state["Obj"]].add((state["ObjSta"], state["Elm"], state["ElmSta"]))
    population = [{"member_id": m["frame_name"], "observed_station_count": len(stations[m["frame_name"]])}
                  for m in bank["members"]]
    result = {"schema": SCHEMA, "source_run_id": bank.get("run_id"), "source_archive_sha256": bank["source_archive_sha256"],
        "source_demand_result_sha256": chain["result_sha256"], "population": population,
        "critical_selection": critical_selection(chain, population), "reinforcement_bounds": _reinforcement_bounds(bank, chain),
        "design_demand_authority": "DENIED", "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
    result["result_sha256"] = digest(result)
    return result
