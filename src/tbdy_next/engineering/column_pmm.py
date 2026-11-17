"""One-column PMM replay over signed forces in a combined ETABS capture."""

from collections import Counter, defaultdict
from math import isfinite, isclose
from typing import Mapping

from ..column_engine.beam_references import station_budget
from ..column_engine.csi_geometry import LocalSectionDims
from ..column_engine.section_capacity import solver
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.ts500_column import apply_minimum_eccentricity
from .column_axial import _columns
from .column_pmm_section import build_pmm_section

STAGE = "column-pmm"
COLUMN_PMM_ID = "4.4"
_EXCEEDED = {"EXCEEDS_SCENARIO_SURFACE", "OUTSIDE_SCENARIO_AXIAL_RANGE"}
_RESOLVED = _EXCEEDED | {"WITHIN_SCENARIO_SURFACE", "AXIAL_ONLY_SCENARIO"}


def _source_rows(source, key, units):
    """Qualify the exact ETABS 23 table and v1 field contract before binding any rows."""
    if not isinstance(source, Mapping):
        return None, "NOT_CAPTURED"
    tables = source.get("table_reads")
    table = tables.get(key) if isinstance(tables, Mapping) else None
    if table is None:
        errors = source.get("table_errors")
        return None, "CAPTURE_ERROR" if isinstance(errors, Mapping) and key in errors else "NOT_CAPTURED"
    if not _source_session_verified(source):
        return None, "UNVERIFIED_CAPTURE_SESSION"
    return _qualified_table_rows(table, key, units)


def _source_session_verified(source):
    return (source.get("schema") == "tbdy.next.r10-live-source.v1" and not source.get("error")
            and all(source.get(f"model_locked_{side}") is True and source.get(f"units_{side}") == 6
                    for side in ("before", "after")))


def _qualified_table_rows(table, key, units):
    if not isinstance(table, Mapping) or table.get("table_key") != key:
        return None, "UNSUPPORTED_TABLE_SCHEMA"
    if table.get("status") not in ("CAPTURED", "EMPTY_TABLE"):
        return None, "CAPTURE_ERROR"
    metadata = table.get("field_metadata")
    fields, rows = table.get("fields"), table.get("rows")
    if (not isinstance(metadata, Mapping) or metadata.get("status") != "OK"
            or type(metadata.get("table_version")) is not int or metadata["table_version"] != 1
            or not isinstance(fields, list) or any(not isinstance(f, str) for f in fields)
            or len(set(fields)) != len(fields) or not units.keys() <= set(fields)
            or not isinstance(metadata.get("units_by_field"), Mapping)
            or any(metadata["units_by_field"].get(field) != unit for field, unit in units.items())
            or not isinstance(rows, list) or type(table.get("row_count")) is not int or len(rows) != table["row_count"]
            or any(not isinstance(row, Mapping) or set(row) != set(fields) for row in rows)
            or bool(rows) != (table["status"] == "CAPTURED")):
        return None, "UNSUPPORTED_TABLE_SCHEMA"
    return rows, table["status"]


def _exact_id(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def bind_pmm_mesh_source(snapshot: Mapping, member_stories: Mapping[str, str | None]) -> dict:
    """Bind independently captured line elements and station assignments to physical Unique IDs."""
    from .column_r10_live import ANALYSIS_FRAME_ELEMENTS, FRAME_OUTPUT_STATIONS

    source = snapshot["column_axial"].get("r10_source")
    mesh_fields = dict.fromkeys(("Story", "ObjType", "ObjName", "ElmName", "ElmJtI", "ElmJtJ"), "")
    mesh, mesh_status = _source_rows(source, ANALYSIS_FRAME_ELEMENTS, mesh_fields)
    station_fields = {"Story": "", "UniqueName": "", "StationOpt": "", "MaxSpacing": "m", "MinStations": ""}
    stations, station_status = _source_rows(source, FRAME_OUTPUT_STATIONS, station_fields)
    by_uid, station_by_uid = defaultdict(list), defaultdict(list)
    elm_counts = Counter()
    for row in mesh or ():
        # ETABS can reuse names across Frame and Shell object/element namespaces.
        if row["ObjType"] != "Frame":
            continue
        if _exact_id(row["ElmName"]):
            elm_counts[row["ElmName"]] += 1
        if _exact_id(row["ObjName"]) and row["ObjName"] in member_stories:
            by_uid[row["ObjName"]].append(row)
    for row in stations or ():
        if _exact_id(row["UniqueName"]) and row["UniqueName"] in member_stories:
            station_by_uid[row["UniqueName"]].append(row)

    members = {}
    for uid, story in member_stories.items():
        expected = []
        reason = None
        if mesh is None:
            reason = "ANALYSIS_FRAME_ELEMENT_SOURCE_UNAVAILABLE"
        elif not by_uid[uid]:
            reason = "ANALYSIS_FRAME_OBJECT_MAPPING_MISSING"
        elif (not _exact_id(story) or any(row["Story"] != story or not _exact_id(row["ElmName"])
                                         or elm_counts[row["ElmName"]] != 1 for row in by_uid[uid])):
            reason = "ANALYSIS_FRAME_OBJECT_MAPPING_CONFLICT"
        else:
            expected = sorted(row["ElmName"] for row in by_uid[uid])
        element_joints = {}
        if expected:
            element_joints = {row["ElmName"]: [row["ElmJtI"], row["ElmJtJ"]] for row in by_uid[uid]
                              if _exact_id(row["ElmJtI"]) and _exact_id(row["ElmJtJ"])}
        assignments = station_by_uid[uid]
        exact_assignment = (assignments[0] if len(assignments) == 1 and _exact_id(story)
                            and assignments[0]["Story"] == story else None)
        members[uid] = {
            "expected_analysis_element_ids": expected, "roster_bound": reason is None, "reason": reason,
            "analysis_element_end_joints": element_joints,
            "single_element_end_joints": element_joints.get(expected[0]) if len(expected) == 1 else None,
            "station_assignment": ({field: exact_assignment[field] for field in station_fields}
                                   if exact_assignment else None),
            "station_assignment_status": ("CAPTURED_ASSIGNMENT" if exact_assignment else
                                          "ASSIGNMENT_CONFLICT" if assignments else
                                          "NO_EXPLICIT_ASSIGNMENT" if stations is not None else station_status),
        }
    return {"mesh_table_status": mesh_status, "station_table_status": station_status, "members": members}


def _analysis_element_coverage(rows, mesh):
    observed = {row[2] for row in rows}
    expected = set(mesh["expected_analysis_element_ids"])
    missing, extra = expected - observed, observed - expected
    reason = mesh["reason"]
    if mesh["roster_bound"] and (missing or extra):
        reason = "ANALYSIS_ELEMENT_FORCE_COVERAGE_UNRESOLVED"
    return {
        "expected_analysis_element_ids": sorted(expected), "observed_analysis_element_ids": sorted(observed),
        "missing_analysis_element_ids": sorted(missing) if mesh["roster_bound"] else [],
        "unmapped_analysis_element_ids": sorted(extra) if mesh["roster_bound"] else [],
        "roster_bound": mesh["roster_bound"], "reason": reason,
    }


def _station_count(value) -> int | None:
    text = str(value).strip()
    if text.isascii() and text.isdecimal() and len(text) <= 9 and int(text) >= 3:
        return int(text)
    return None


def configured_output_station_minimums(snapshot: dict, geometry: dict, *,
                                       mesh_members: Mapping[str, Mapping] | None = None) -> dict[str, int]:
    """Use the ETABS output assignment, with the captured summary for earlier acquisitions."""
    table = ((snapshot.get("geometry_capture") or {}).get("tables") or {}).get("FRAME_ASSIGNMENTS") or {}
    metadata = table.get("field_metadata") or {}
    rows = table.get("rows")
    result = {}
    units = metadata.get("units_by_field") or {}
    if (table.get("status") == "CAPTURED" and table.get("table_key") == "Frame Assignments - Summary"
            and metadata.get("status") == "OK" and units.get("MinNumSta") == "" and units.get("MaxStaSpcg") == "m"
            and isinstance(rows, list) and len(rows) == table.get("row_count")
            and all(isinstance(row, Mapping) for row in rows)):
        members = {row["element_id"]: row["story"] for row in _columns(geometry)}
        counts = Counter(row.get("UniqueName") for row in rows)
        for row in rows:
            uid, minimum = row.get("UniqueName"), _station_count(row.get("MinNumSta"))
            if (uid in members and counts[uid] == 1 and row.get("Story") == members[uid]
                    and str(row.get("Type", "")).casefold() == "column"
                    and row.get("MaxStaSpcg") in ("None", "") and minimum is not None):
                result[uid] = minimum
    for uid, member in (mesh_members or {}).items():
        status = member["station_assignment_status"]
        if status in ("CAPTURED_ASSIGNMENT", "ASSIGNMENT_CONFLICT"):
            result.pop(uid, None)
        policy = member.get("station_assignment")
        if policy and policy["StationOpt"] == "Min Stations" and policy["MaxSpacing"] in ("None", ""):
            minimum = _station_count(policy["MinStations"])
            if minimum is not None:
                result[uid] = minimum
    return result


def _oriented_element_chain(element_ids, end_joints, first, last):
    if not _exact_id(first) or not _exact_id(last) or first == last or set(element_ids) != end_joints.keys():
        return None
    by_start = {start: (element, end) for element, (start, end) in end_joints.items()}
    if len(by_start) != len(element_ids):
        return None
    chain, joints = [], [first]
    current = first
    while current != last:
        link = by_start.pop(current, None)
        if link is None:
            return None
        element, current = link
        chain.append(element)
        joints.append(current)
    return (chain, joints) if not by_start else None


def _analysis_joint_coordinates(source):
    """Use native doubles because the ETABS display table rounds global coordinates."""
    from .column_r10_live import ANALYSIS_JOINT_COORDINATE_SCHEMA

    read = source.get("analysis_joint_coordinates") if isinstance(source, Mapping) else None
    if read is None:
        return None, "NOT_CAPTURED"
    if not _source_session_verified(source):
        return None, "UNVERIFIED_CAPTURE_SESSION"
    if (not isinstance(read, Mapping) or read.get("schema") != ANALYSIS_JOINT_COORDINATE_SCHEMA
            or read.get("coordinate_system") != "Global" or read.get("units") != "m"
            or not isinstance(read.get("coordinates"), Mapping) or not isinstance(read.get("errors"), Mapping)):
        return None, "UNSUPPORTED_NATIVE_COORDINATE_SCHEMA"
    coordinates = {joint: xyz for joint, xyz in read["coordinates"].items()
                   if _exact_id(joint) and joint not in read["errors"]
                   and isinstance(xyz, list) and len(xyz) == 3
                   and all(type(value) is float and isfinite(value) for value in xyz)}
    return coordinates, "CAPTURED" if coordinates else "NO_VALID_NATIVE_COORDINATES"


def _mesh_cut_positions(mesh, member, coordinates, length, end):
    chain = _oriented_element_chain(mesh["expected_analysis_element_ids"], mesh["analysis_element_end_joints"],
                                   member["UniquePtI"], member["UniquePtJ"])
    if chain is None:
        return [], "ORIENTED_ANALYSIS_ELEMENT_CHAIN_UNVERIFIED"
    elements, joints = chain
    if any(joint not in coordinates for joint in joints):
        return [], "ANALYSIS_JOINT_COORDINATES_MISSING_OR_AMBIGUOUS"
    points = [coordinates[joint] for joint in joints]
    x0, y0, z0 = points[0]
    z1 = points[-1][2]
    direction = 1 if z1 > z0 else -1
    stations = [(z - z0) * direction for _, _, z in points]
    tolerance = station_budget(0.0, length, length)
    if (any(abs(x - x0) > station_budget(x, x0, length) or abs(y - y0) > station_budget(y, y0, length)
            for x, y, _ in points)
            or any(not isfinite(station) for station in stations)
            or abs(stations[-1] - length) > tolerance
            or any(b - a <= 2 * tolerance for a, b in zip(stations, stations[1:]))):
        return [], "VERTICAL_ANALYSIS_MESH_GEOMETRY_UNVERIFIED"
    if end - stations[-2] <= 2 * tolerance:
        return [], "J_OFFSET_REACHES_INTERIOR_ANALYSIS_JOINT"

    # Each internal joint provides distinct cuts on its adjoining analysis elements.
    cuts = [(0.0, elements[0], 0.0), (end, elements[-1], end - stations[-2])]
    for index, position in enumerate(stations[1:-1], start=1):
        cuts.extend([(position, elements[index - 1], position - stations[index - 1]),
                     (position, elements[index], 0.0)])
    midpoint = end / 2
    nearest_joint = min(abs(position - midpoint) for position in stations[1:-1])
    if nearest_joint > tolerance:
        if nearest_joint <= 2 * tolerance:
            return [], "CONFIGURED_CUT_POSITIONS_UNRESOLVABLE"
        index = next(index for index, finish in enumerate(stations[1:]) if midpoint < finish)
        cuts.append((midpoint, elements[index], midpoint - stations[index]))
    return sorted(cuts), None


def bind_configured_output_cuts(snapshot: Mapping, mesh_members: Mapping[str, Mapping]) -> dict[str, dict]:
    """Derive required ETABS nominal and mesh-end cuts before inspecting forces."""
    from .column_r10_live import ANALYSIS_JOINT_ELEMENTS, END_OFFSETS

    geometry = snapshot.get("geometry_capture") or {}
    connectivity = None
    if (geometry.get("schema") == "tbdy.next.geometry.capture.v2"
            and geometry.get("unit_state_unchanged") is True
            and geometry.get("present_units") == geometry.get("present_units_after") == 6):
        connectivity, _ = _qualified_table_rows(
            (geometry.get("tables") or {}).get("COLUMN_CONNECTIVITY"), "Column Object Connectivity",
            {"Story": "", "UniqueName": "", "UniquePtI": "", "UniquePtJ": "", "Length": "m"},
        )
    source = snapshot["column_axial"].get("r10_source")
    offsets, _ = _source_rows(source, END_OFFSETS,
                              {"Story": "", "UniqueName": "", "OffsetI": "m", "OffsetJ": "m"})
    _, joint_status = _source_rows(source, ANALYSIS_JOINT_ELEMENTS,
                                   {"ElmName": "", "GlobalX": "m", "GlobalY": "m", "GlobalZ": "m"})
    coordinates, coordinate_status = _analysis_joint_coordinates(source)
    columns, offsets_by_uid = defaultdict(list), defaultdict(list)
    for row in connectivity or ():
        columns[row["UniqueName"]].append(row)
    for row in offsets or ():
        offsets_by_uid[row["UniqueName"]].append(row)

    result = {}
    for uid, mesh in mesh_members.items():
        assignment = mesh.get("station_assignment") or {}
        end_joints = mesh.get("single_element_end_joints")
        elem_ids = mesh["expected_analysis_element_ids"]
        meshed = len(elem_ids) > 1
        member_rows, offset_rows = columns[uid], offsets_by_uid[uid]
        reason = None
        cuts = []
        if (assignment.get("StationOpt") != "Min Stations" or _station_count(assignment.get("MinStations")) != 3
                or assignment.get("MaxSpacing") not in ("None", "")):
            reason = "THREE_STATION_ASSIGNMENT_UNVERIFIED"
        elif not meshed and end_joints is None:
            reason = "SINGLE_ORIENTED_ANALYSIS_ELEMENT_UNVERIFIED"
        elif len(member_rows) != 1 or len(offset_rows) != 1:
            reason = "COLUMN_CONNECTIVITY_OR_END_OFFSET_UNVERIFIED"
        else:
            member, offset = member_rows[0], offset_rows[0]
            if (member["Story"] != assignment["Story"] or offset["Story"] != member["Story"]
                    or (not meshed and (end_joints != [member["UniquePtI"], member["UniquePtJ"]]
                                       or end_joints[0] == end_joints[1]))):
                reason = "COLUMN_END_JOINT_OR_STORY_BINDING_CONFLICT"
            else:
                try:
                    length, offset_i, offset_j = (float(value) for value in
                                                  (member["Length"], offset["OffsetI"], offset["OffsetJ"]))
                except (TypeError, ValueError, OverflowError):
                    length, offset_i, offset_j = 0.0, 0.0, 0.0
                if not all(isfinite(v) for v in (length, offset_i, offset_j)) or not 0 <= offset_j < length:
                    reason = "COLUMN_END_OFFSET_OR_LENGTH_INVALID"
                elif offset_i != 0.0:
                    reason = "NONZERO_I_OFFSET_OUTSIDE_VERIFIED_CUT_BRANCH"
                else:
                    end = length - offset_j
                    if end / 2 <= 2 * station_budget(0.0, end / 2, length):
                        reason = "CONFIGURED_CUT_POSITIONS_UNRESOLVABLE"
                    elif meshed:
                        if coordinates is None:
                            reason = "ANALYSIS_JOINT_COORDINATE_SOURCE_UNAVAILABLE"
                        else:
                            cuts, reason = _mesh_cut_positions(mesh, member, coordinates, length, end)
                    else:
                        cuts = [(value, elem_ids[0], value) for value in (0.0, end / 2, end)]
        result[uid] = {
            "basis": ("ETABS_CONFIGURED_THREE_STATIONS_AND_MESH_ENDS_ZERO_I_OFFSET" if meshed else
                      "ETABS_CONFIGURED_THREE_STATIONS_SINGLE_ELEMENT_ZERO_I_OFFSET"),
            "status": "REQUIRED_SUBSET_BOUND" if cuts else "NOT_PROVEN", "reason": reason,
            "cuts": [{"object_station_m": obj, "analysis_element_id": elm, "element_station_m": station}
                     for obj, elm, station in cuts],
        }
        if meshed:
            result[uid]["analysis_joint_table_status"] = joint_status
            result[uid]["analysis_joint_native_coordinate_status"] = coordinate_status
        if cuts:
            result[uid].update(length_m=length, offset_i_m=offset_i, offset_j_m=offset_j)
    return result


def _required_cut_coverage(rows, grid):
    observed = {row[:4] for row in rows}
    missing, ambiguous = [], []
    length = grid["length_m"]
    for cut in grid["cuts"]:
        elm = cut["analysis_element_id"]
        obj_sta, elm_sta = cut["object_station_m"], cut["element_station_m"]
        candidates = [row for row in observed if row[2] == elm
                      and abs(row[1] - obj_sta) <= station_budget(row[1], obj_sta, length)
                      and abs(row[3] - elm_sta) <= station_budget(row[3], elm_sta, length)]
        if not candidates:
            missing.append(cut)
        elif len(candidates) != 1:
            ambiguous.append(cut)
    return {"required_count": len(grid["cuts"]), "matched_count": len(grid["cuts"]) - len(missing) - len(ambiguous),
            "missing_cuts": missing, "ambiguous_cuts": ambiguous}


def _object_station_count(rows) -> int:
    distinct = []
    for station in sorted({row[1] for row in rows}):
        if not distinct or not isclose(station, distinct[-1], rel_tol=1e-12, abs_tol=1e-9):
            distinct.append(station)
    return len(distinct)


def _station_result(native, dims, capacity) -> dict:
    _, station, element, element_station, name, step, step_number, p, _, _, _, m2, m3 = native
    nd = -p
    item = {
        "combination": name, "analysis_element_id": element, "object_station_m": station,
        "element_station_m": element_station, "step_type": step, "step_number": step_number,
        "nd_kn": nd, "m2_knm": m2, "m3_knm": m3,
    }
    try:
        demand = apply_minimum_eccentricity(nd_kn=nd, m2_knm=m2, m3_knm=m3, dims=dims)
        m2_design, m3_design = demand["m2_design_knm"], demand["m3_design_knm"]
        if not all(isfinite(value) for value in (nd * 1000, m2_design * 1e6, m3_design * 1e6)):
            raise ValueError("PMM_DEMAND_OUTSIDE_NUMERICAL_RANGE")
        assessment = capacity.assess(nd * 1000, m2_design * 1e6, m3_design * 1e6)
    except (ValueError, ArithmeticError) as exc:
        return {**item, "m2_design_knm": None, "m3_design_knm": None, "utilization": None,
                "status": "NUMERIC_UNRESOLVED", "reason": str(exc)}
    return {
        **item,
        "m2_design_knm": m2_design, "m3_design_knm": m3_design,
        "utilization": (assessment["axial_utilization"] if assessment["status"] == "AXIAL_ONLY_SCENARIO"
                        else assessment["utilization"]),
        "status": assessment["status"], "reason": assessment["reason"],
        "minimum_eccentricity_mm": [demand["e_min_m2_mm"], demand["e_min_m3_mm"]],
        "capacity": assessment,
    }


def _evaluate_single_column_pmm(uid: str, snapshot: dict, geometry: dict, axial: dict,
                                *, station_minimum: int | None = None, mesh: Mapping | None = None,
                                configured_cuts: Mapping | None = None) -> dict:
    """Replay native station vectors for one column after shared axial source validation."""
    feature = snapshot["column_axial"]
    member = next((row for row in _columns(geometry) if row["element_id"] == uid), None)
    axial_member = next((row for row in axial["columns"] if row["element_id"] == uid), {})
    plan = axial["combination_plan"]
    source = feature.get("force_source") or {}
    rowset = source.get("rowsets", {}).get(uid)
    by_combo = defaultdict(list)
    if rowset is not None:
        for row in native_frame_force_rows(rowset, uid):
            by_combo[row[4]].append(row)
    cuts = {row[:4] for rows in by_combo.values() for row in rows}
    coverage = {row["combination"]: row for row in axial_member.get("combination_checks", [])}
    result = {
        "schema": "tbdy.next.column-pmm-check.v1", "member_id": uid,
        "story": member.get("story") if member else None, "section": member.get("section") if member else None,
        "combination_plan": plan, "section_evidence": None, "combinations": [], "rows": [],
        "analysis_order": "UNVERIFIED", "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
    }
    reason = None
    capacity = None
    if plan["blockers"]:
        reason = plan["blockers"][0]
    elif member is None:
        reason = "SELECTED_COLUMN_MISSING_FROM_CURRENT_MODEL"
    elif "fcd_mpa" not in axial_member or rowset is None:
        reason = axial_member.get("reason", "NATIVE_FRAME_FORCE_UNAVAILABLE")
    elif not any(combo.get("force_semantics") == "STATIC_SIGNED_VECTOR" for combo in plan["combinations"]):
        reason = "NO_SIGNED_STATIC_COMBINATION_SELECTED"
    else:
        try:
            section, evidence = build_pmm_section(
                feature.get("pmm_section_source") or {}, member, axial_member, feature["design_preferences"],
            )
            dims = LocalSectionDims(section.t2, section.t3)
            capacity = solver(section)
            result["section_evidence"] = evidence
        except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
            reason = str(exc) or "PMM_SECTION_INPUTS_UNVERIFIED"

    for combo in plan["combinations"]:
        name, semantics = combo["name"], combo.get("force_semantics")
        item = {"name": name, "status": "BLOCKED", "reason": reason,
                "expected_station_count": 0, "evaluated_station_count": 0}
        result["combinations"].append(item)
        if mesh is not None:
            elements = _analysis_element_coverage(by_combo[name], mesh)
            item["analysis_element_coverage"] = elements
            if elements["reason"] not in (None, "ANALYSIS_FRAME_ELEMENT_SOURCE_UNAVAILABLE"):
                item["reason"] = elements["reason"]
                if semantics == "STATIC_SIGNED_VECTOR":
                    item["expected_station_count"] = max(len(cuts), station_minimum or 0, len(elements["expected_analysis_element_ids"]))
                continue
        if configured_cuts and configured_cuts["status"] == "REQUIRED_SUBSET_BOUND":
            cut_coverage = _required_cut_coverage(by_combo[name], configured_cuts)
            item["configured_cut_coverage"] = cut_coverage
            if cut_coverage["required_count"] != cut_coverage["matched_count"]:
                item["reason"] = "ETABS_CONFIGURED_CUT_COVERAGE_UNRESOLVED"
                if semantics == "STATIC_SIGNED_VECTOR":
                    item["expected_station_count"] = max(len(cuts), cut_coverage["required_count"])
                continue
        if semantics == "SCALAR_COMPONENT_ENVELOPE":
            item.update(status="OUT_OF_SCOPE", reason="COMPONENT_ENVELOPE_HAS_NO_SIGNED_PMM_VECTOR")
        elif semantics != "STATIC_SIGNED_VECTOR":
            item["reason"] = reason or "COMBINATION_FORCE_SEMANTICS_UNSUPPORTED"
        else:
            item["expected_station_count"] = len(cuts)
            axial_check = coverage.get(name, {})
            if station_minimum is not None:
                observed = _object_station_count(by_combo[name])
                item["minimum_object_station_count"] = station_minimum
                item["observed_object_station_count"] = observed
                item["expected_station_count"] = max(len(cuts), station_minimum)
                if observed < station_minimum:
                    item["reason"] = "ETABS_ASSIGNED_MINIMUM_OUTPUT_STATIONS_MISSING"
                    continue
            if capacity is None or axial_check.get("status") not in {"WITHIN_LIMIT", "OUTSIDE_LIMIT"}:
                item["reason"] = reason or axial_check.get("reason") or "SIGNED_STATION_COVERAGE_UNVERIFIED"
                continue
            rows = [_station_result(row, dims, capacity) for row in sorted(by_combo[name], key=lambda x: x[:4])]
            result["rows"].extend(rows)
            count = sum(row["status"] in _RESOLVED for row in rows)
            if count == len(cuts):
                item.update(status="NUMERICAL_COMPLETE", reason=None, evaluated_station_count=count)
            else:
                item.update(status="NUMERICAL_PARTIAL" if count else "BLOCKED", evaluated_station_count=count,
                            reason="SECTION_SOLVER_UNRESOLVED_AT_SELECTED_STATIONS")
    expected = sum(item["expected_station_count"] for item in result["combinations"])
    evaluated = sum(item["evaluated_station_count"] for item in result["combinations"])
    incomplete = any(item["status"] in {"BLOCKED", "NUMERICAL_PARTIAL"} for item in result["combinations"])
    result.update(status=("NUMERICAL_COMPLETE" if evaluated and not incomplete
                          else "NUMERICAL_PARTIAL" if evaluated else "BLOCKED"),
                  reason=reason or ("SIGNED_SECTION_CHECK_INCOMPLETE" if incomplete else None),
                  expected_station_count=expected, evaluated_station_count=evaluated,
                  observed_exceedance_count=sum(row["status"] in _EXCEEDED for row in result["rows"]))
    return result


def evaluate_column_pmm(snapshot: dict, geometry: dict, axial: dict,
                         *, station_minimums: dict[str, int] | None = None,
                         mesh_members: Mapping[str, Mapping] | None = None,
                         configured_cuts: Mapping[str, Mapping] | None = None) -> dict:
    """Replay native station vectors for either one column (`pmm_member`) or all columns (`ALL`)."""
    feature = snapshot["column_axial"]
    target = feature["request"]["pmm_member"]
    station_minimums = station_minimums or {}
    mesh_members = mesh_members or {}
    configured_cuts = configured_cuts or {}
    if target != "ALL":
        return _evaluate_single_column_pmm(target, snapshot, geometry, axial,
                                           station_minimum=station_minimums.get(target), mesh=mesh_members.get(target),
                                           configured_cuts=configured_cuts.get(target))

    expected_ids = [row["element_id"] for row in _columns(geometry) if row.get("status") != "NOT_APPLICABLE"]
    members = [_evaluate_single_column_pmm(uid, snapshot, geometry, axial,
                                          station_minimum=station_minimums.get(uid), mesh=mesh_members.get(uid),
                                          configured_cuts=configured_cuts.get(uid)) for uid in expected_ids]
    complete_cols = sum(m["status"] == "NUMERICAL_COMPLETE" for m in members)
    blocked_cols = sum(m["status"] == "BLOCKED" for m in members)
    expected_sta = sum(m["expected_station_count"] for m in members)
    eval_sta = sum(m["evaluated_station_count"] for m in members)
    if members and complete_cols == len(members):
        overall = "NUMERICAL_COMPLETE"
    elif members and blocked_cols < len(members):
        overall = "NUMERICAL_PARTIAL"
    else:
        overall = "BLOCKED"
    return {
        "schema": "tbdy.next.column-pmm-check.v1",
        "scope": "ALL_COLUMNS",
        "member_id": "ALL",
        "combination_plan": axial["combination_plan"],
        "expected_column_count": len(expected_ids),
        "evaluated_column_count": len(members),
        "complete_column_count": complete_cols,
        "members": members,
        "expected_station_count": expected_sta,
        "evaluated_station_count": eval_sta,
        "observed_exceedance_count": sum(m["observed_exceedance_count"] for m in members),
        "status": overall,
        "reason": None if overall == "NUMERICAL_COMPLETE" else "ALL_COLUMNS_PMM_INCOMPLETE_OR_BLOCKED",
        "analysis_order": "UNVERIFIED",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
