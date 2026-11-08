"""CE-02: typed combination routes, signed static candidates and design traces.

Reuse YENI's verified six-component static replay. The canonical TBDY demand
engine contributes name-blind classification, not its end-only spectral sign
permutations. Every state keeps the complete native station/element/step key.
No section capacity, moment magnification or engineering acceptance is granted.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import math
import zlib

from .native_archive import BankError, digest, finite
from .source_bank import COMPONENTS, FIELDS

SCHEMA = "tbdy.next.column-demand-chain.v1"
DESIGN_TABLE = "Concrete Column Design Summary - TS 500-2000(R2018)"
ROLES = {"PMM": "PMMCombo", "MAJOR_SHEAR": "VMajCombo", "MINOR_SHEAR": "VMinCombo"}
REQUIRED_DESIGN_FIELDS = ("UniqueName", "Story", "Label", "Station", "DesignSect",
    "DesignOpt", "Status", "PMMRatio", "PMMCombo", "VMajCombo", "VMinCombo", "WarnMsg", "ErrMsg")
CSI_FORCE_REFERENCE = (
    "https://docs.csiamerica.com/help-files/etabs-api-2016/html/87689f3e-4175-1627-618b-c4ebae5e89b5.htm")
CSI_SIGN_REFERENCE = (
    "https://docs.csiamerica.com/help-files/sap/Output/Frame_Element_Internal_Forces_Output_Conventions.htm")


def classify_combinations(cases, combinations):
    """Follow typed references, retaining nested, non-static and unknown routes."""
    memo = {}
    def walk(name, path):
        if name in path:
            raise BankError("COMBINATION_CYCLE")
        if len(path) >= 64:
            raise BankError("COMBINATION_DEPTH_LIMIT")
        if name in memo:
            return memo[name]
        definition = combinations.get(name)
        if not definition or definition.get("status") != "OBSERVED":
            raise BankError("COMBINATION_DEFINITION_UNRESOLVED")
        operator, terms = definition.get("operator"), definition.get("terms")
        if type(operator) is not int or operator not in range(5) or not terms:
            raise BankError("COMBINATION_OPERATOR_OR_TERMS_UNRESOLVED")
        refs = [(t.get("type"), t.get("name")) for t in terms]
        if len(set(refs)) != len(refs):
            raise BankError("REPEATED_REFERENCE_UNSUPPORTED_BY_ADAPTER")
        kinds, leaves, operators = set(), set(), {operator}
        for term in terms:
            finite(term.get("factor"), "combination_factor")
            kind, ref = term.get("type"), term.get("name")
            if type(kind) is not int or kind not in (0, 1):
                raise BankError("COMBINATION_REFERENCE_TYPE_INVALID")
            if kind == 1:
                child_kinds, child_leaves, child_ops = walk(ref, (*path, name))
                kinds.update(child_kinds); leaves.update(child_leaves); operators.update(child_ops)
            else:
                case = cases.get(ref, {})
                if case.get("status") != "OBSERVED" or type(case.get("case_type")) is not int:
                    raise BankError("CONSTITUENT_CASE_TYPE_UNRESOLVED")
                kinds.add(case["case_type"]); leaves.add(ref)
        memo[name] = kinds, leaves, operators
        return memo[name]

    result = {}
    for name, definition in combinations.items():
        row = {"combination": name, "classification": "DEFINITION_UNRESOLVED", "reason": None,
            "operator": definition.get("operator"), "case_names": [], "case_types": [],
            "static_candidate_count": 0, "design_selection_proven": False}
        try:
            kinds, leaves, operators = walk(name, ())
            row.update(case_names=sorted(leaves), case_types=sorted(kinds))
            if definition["operator"] == 1:
                row["classification"] = "ENVELOPE"
            elif operators != {0}:
                row["classification"] = "NON_LINEAR_ADD_ROUTE"
            elif not kinds <= {1, 4}:
                row["classification"] = "OTHER_ANALYSIS_CASE"
            elif 4 in kinds:
                row["classification"] = "RESPONSE_SPECTRUM_LINEAR_ADD"
            elif any(t["type"] == 1 for t in definition["terms"]):
                row["classification"] = "STATIC_NESTED_UNVERIFIED"
            else:
                row["classification"] = "STATIC_LINEAR_ADD"
        except (ValueError, KeyError, TypeError) as exc:
            row["reason"] = str(exc)
        result[name] = row
    return result


def _candidate(row, replay, definition, archive_sha):
    """Compression-positive N; all other signs and CSI local axes are retained.

    These are unqualified analysis-result inputs, not Nd/Md or magnified forces.
    Positive native P is tension; negative N remains tension (never clamped).
    """
    values = {"N_compression_kN": -row["P"], "V2_kN": row["V2"], "V3_kN": row["V3"],
        "T_kNcm": 100 * row["T"], "M2_kNcm": 100 * row["M2"], "M3_kNcm": 100 * row["M3"]}
    if any(not math.isfinite(v) for v in values.values()):
        raise BankError("DEMAND_UNIT_CONVERSION_OVERFLOW")
    key = {k: row[k] for k in FIELDS[:7]}
    return {"state_id": digest({"schema": SCHEMA, "archive": archive_sha,
                "source_row_id": row["source_row_id"], "key": key}),
        "source_row_id": row["source_row_id"], "native_key": key,
        "native_values": {k: row[k] for k in COMPONENTS}, "domain_values": values,
        "source_call_id": row["call_id"], "source_row_index": row["source_row_index"],
        "constituent_row_ids": replay["constituent_row_ids"],
        "constituent_factors": [t["factor"] for t in definition["terms"]],
        "source_archive_sha256": archive_sha, "vector_status": "SIGNED_STATIC_SOURCE_VECTOR",
        "coordinate_basis": "CSI_FRAME_LOCAL_1_2_3", "location_role": "RECORDED_STATION",
        "analysis_order": "NOT_PROVEN", "final_design_eligible": False}


def _decimal_station(value):
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise BankError("DESIGN_STATION_INVALID") from exc
    if not number.is_finite() or number < 0:
        raise BankError("DESIGN_STATION_INVALID")
    return number


def _design_traces(archive, bank, routes, candidate_ids):
    output = {"table_key": DESIGN_TABLE, "status": "NOT_OBSERVED", "reason": None,
        "source": None, "row_count": 0, "reference_count": 0, "known_combination_references": 0,
        "unique_static_links": 0, "link_status_counts": {}, "rows": [],
        "references_without_exact_station": 0, "ambiguous_design_station_rows": 0, "null_pmm_ratio_rows": 0,
        "selected_member_count": len(bank["members"]), "members_with_design_rows": 0,
        "missing_selected_members": [], "unexpected_members": [],
        "station_matching": "EXACT_DECIMAL_VALUE_NO_ROUNDING_OR_NEAREST", "full_design_selection_proven": False}
    members = {m["frame_name"]: m for m in bank["members"]}
    try:
        table = archive.table(DESIGN_TABLE, REQUIRED_DESIGN_FIELDS, required_units={"Station": "m"})
        if table is None:
            output["reason"] = "DESIGN_SUMMARY_NOT_IN_ARCHIVE"
            output["missing_selected_members"] = sorted(members)
            return output
        rows, proof = table
    except (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError) as exc:
        output.update(status="NOT_PROVEN", reason=str(exc), missing_selected_members=sorted(members))
        return output
    force_index = defaultdict(list)
    for r in bank["force_states"]:
        force_index[(r["Obj"], _decimal_station(r["ObjSta"]), r["LoadCase"])].append(r)
    stations = []
    for row in rows:
        try:
            stations.append(_decimal_station(row["Station"]))
        except ValueError:
            stations.append(None)
    multiplicity = Counter((r["UniqueName"], s) for r, s in zip(rows, stations))
    link_counts, observed_members, unexpected = Counter(), set(), set()
    for i, (raw, station) in enumerate(zip(rows, stations)):
        name = raw["UniqueName"]
        if name in members:
            observed_members.add(name)
        else:
            unexpected.add(str(name))
        frame = members.get(name, {}).get("context", {}).get("frame", {})
        identity_ok = (name in members and all(frame.get(k) for k in ("story_label", "column_label", "section_assigned"))
            and frame.get("story_label") == raw["Story"]
            and frame.get("column_label") == raw["Label"] and frame.get("section_assigned") == raw["DesignSect"])
        output["null_pmm_ratio_rows"] += raw["PMMRatio"] is None
        output["ambiguous_design_station_rows"] += multiplicity[(name, station)] > 1
        item = {"table_row_id": digest({"archive": archive.sha256, "call": proof["call_id"], "index": i}),
            "source_row_index": i, "member_id": name, "station_text": raw["Station"],
            "native_design_row": raw, "identity_matches_source_member": identity_ok,
            "design_station_occurrences": multiplicity[(name, station)], "references": []}
        for role, field in ROLES.items():
            combo = raw[field]
            matched = force_index.get((name, station, combo), ()) if station is not None else ()
            source_ids = [r["source_row_id"] for r in matched]
            output["references_without_exact_station"] += not matched
            route = routes.get(combo)
            if route:
                output["known_combination_references"] += 1
            if not identity_ok:
                status = "DESIGN_MEMBER_CONTEXT_UNRESOLVED"
            elif route is None:
                status = "COMBINATION_NOT_DEFINED"
            elif station is None:
                status = "DESIGN_STATION_INVALID"
            elif multiplicity[(name, station)] > 1:
                status = "AMBIGUOUS_DESIGN_STATION"
            elif not matched:
                status = "EXACT_NATIVE_STATION_NOT_FOUND"
            elif len(matched) > 1:
                status = "MULTIPLE_NATIVE_STATES"
            elif source_ids[0] in candidate_ids:
                status = "UNIQUE_STATIC_SOURCE_LINK"
                output["unique_static_links"] += 1
            else:
                status = "SOURCE_REFERENCE_ONLY"
            link_counts[status] += 1
            item["references"].append({"role": role, "combination": combo, "status": status,
                "classification": route["classification"] if route else "UNDEFINED",
                "source_row_ids": source_ids, "source_state_count": len(source_ids),
                "exact_station_found": bool(matched), "design_station_ambiguous": multiplicity[(name, station)] > 1,
                "final_design_eligible": False, "shear_axis_mapping_proven": False})
        output["rows"].append(item)
    output.update(status="OBSERVED_REFERENCES_ONLY" if rows else "EMPTY_TABLE", source=proof,
        row_count=len(rows), reference_count=3 * len(rows), link_status_counts=dict(link_counts),
        members_with_design_rows=len(observed_members), missing_selected_members=sorted(set(members) - observed_members),
        unexpected_members=sorted(unexpected))
    return output


def build_demand_chain(bank, archive):
    """Derived view of one verified bank; does not modify its ZIP or SQLite."""
    if bank["source_archive_sha256"] != archive.sha256:
        raise BankError("DEMAND_ARCHIVE_BINDING_MISMATCH")
    cases = {r["name"]: r for r in bank["case_definitions"]}
    combinations = {r["name"]: r for r in bank["combination_definitions"]}
    routes = classify_combinations(cases, combinations)
    by_id = {r["source_row_id"]: r for r in bank["force_states"]}
    if len(by_id) != len(bank["force_states"]):
        raise BankError("DEMAND_SOURCE_ROW_DUPLICATE")
    candidates, rejected = [], []
    for item in bank["static_replay"]["items"]:
        if item["status"] != "NUMERICAL_MATCH":
            continue
        name = item["combination"]
        if (not bank["capture_context_observed"]
                or routes.get(name, {}).get("classification") != "STATIC_LINEAR_ADD"):
            continue
        try:
            row = by_id[item["source_row_id"]]
            key = (item["member_id"], item["object_station_m"], item["analysis_element_id"], item["element_station_m"])
            if (tuple(row[k] for k in FIELDS[:4]) != key or row["LoadCase"] != name
                    or row["StepType"] != "Single Value" or item["observed"] != {k: row[k] for k in COMPONENTS}):
                raise BankError("STATIC_REPLAY_ROW_BINDING_MISMATCH")
            terms = combinations[name]["terms"]
            ids = item["constituent_row_ids"]
            if len(ids) != len(terms):
                raise BankError("STATIC_CONSTITUENT_BINDING_MISMATCH")
            for ref, term in zip(ids, terms):
                source = by_id[ref]
                if (tuple(source[k] for k in FIELDS[:4]) != key or source["LoadCase"] != term["name"]
                        or source["StepType"] != row["StepType"] or source["StepNum"] != row["StepNum"]):
                    raise BankError("STATIC_CONSTITUENT_BINDING_MISMATCH")
            candidates.append(_candidate(row, item, combinations[name], archive.sha256))
            routes[name]["static_candidate_count"] += 1
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            rejected.append({"source_row_id": item.get("source_row_id"), "reason": str(exc)})
    candidate_ids = {r["source_row_id"] for r in candidates}
    if len(candidate_ids) != len(candidates):
        raise BankError("DEMAND_CANDIDATE_DUPLICATE")
    traces = _design_traces(archive, bank, routes, candidate_ids)
    static_counts = Counter(r["native_key"]["Obj"] for r in candidates)
    member_traces = defaultdict(list)
    for row in traces["rows"]:
        member_traces[row["member_id"]].append(row)
    member_summaries = []
    for member in bank["members"]:
        name = member["frame_name"]
        rows = member_traces[name]
        refs = [ref for row in rows for ref in row["references"]]
        member_summaries.append({"member_id": name, "static_candidate_count": static_counts[name],
            "design_rows": len(rows), "unique_static_links": sum(r["status"] == "UNIQUE_STATIC_SOURCE_LINK" for r in refs),
            "pmm_combinations": sorted({r["combination"] for r in refs if r["role"] == "PMM" and r["combination"]}),
            "major_shear_combinations": sorted({r["combination"] for r in refs if r["role"] == "MAJOR_SHEAR" and r["combination"]}),
            "minor_shear_combinations": sorted({r["combination"] for r in refs if r["role"] == "MINOR_SHEAR" and r["combination"]})})
    result = {"schema": SCHEMA, "source_archive_sha256": archive.sha256,
        "source_bank_result_sha256": bank["result_sha256"], "source_run_id": bank.get("run_id"),
        "combination_count": len(routes), "classification_counts": dict(Counter(r["classification"] for r in routes.values())),
        "combinations": list(routes.values()), "static_candidate_count": len(candidates), "candidates": candidates,
        "rejected_candidates": rejected, "design_summary": traces, "members": member_summaries,
        "conversion": {"axial": "N_compression_kN = -P_native_kN", "moments": "kN-m * 100 = kN-cm",
            "axes": "CSI_FRAME_LOCAL_1_2_3", "kernel_axis_mapping_proven": False,
            "references": [CSI_FORCE_REFERENCE, CSI_SIGN_REFERENCE]},
        "analysis_order": "NOT_PROVEN", "design_selection_status": "NOT_PROVEN",
        "design_demand_authority": "DENIED", "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
    result["result_sha256"] = digest(result)
    return result
