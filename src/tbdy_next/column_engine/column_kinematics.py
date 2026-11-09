"""CE-04B: same-case force-cut pairs and native point-object kinematics.

Reuse the sealed ZIP, signed static chain and VS17 global endpoint graph.
This is a source-state link, not an analysis-generation or design certificate.
Display-table values stay traceable and rounded; no magnifier is applied.
"""
from collections import Counter, defaultdict

from .column_prechecks import _number
from .column_stability import OPTIONAL_ERRORS
from .csi_geometry import AXIS_CONVENTION
from .kinematics_kernel import joint_chord_kinematics
from .native_archive import BankError, digest, finite, identity

SCHEMA = "tbdy.next.column-end-kinematics.v1"
DISPLACEMENTS = "Joint Displacements"
STATIC_DEFINITIONS = "Load Case Definitions - Linear Static"
COMPONENTS = ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz")
DISPLACEMENT_FIELDS = ("UniqueName", "OutputCase", "CaseType", "StepType", "StepNumber", "StepLabel", *COMPONENTS)
COORDINATE_CONTRACT = "ETABS_POINT_OBJECT_UX_UY_UZ_RX_RY_RZ_GLOBAL"
STATION_TOL_M = 1e-7  # Native geometric matching only; never a code inequality.
OPEN_BASIS = ["ANALYSIS_GENERATION_NOT_QUALIFIED", "INITIAL_STIFFNESS_AND_GEOMETRIC_NONLINEARITY_NOT_APPROVED",
    "CRACKED_STIFFNESS_AND_CREEP_NOT_BOUND", "PHYSICAL_LATERAL_SUPPORTS_AND_EFFECTIVE_LENGTH_NOT_PROVEN",
    "JOINT_ROTATIONS_NOT_MEMBER_SECTION_ROTATIONS", "DISPLAY_DISPLACEMENTS_ROUNDED_ERROR_BOUND_UNKNOWN",
    "SOURCE_OUTPUT_CUTS_NOT_PHYSICAL_JOINT_FACES", "DESIGN_COMBINATION_AND_SECOND_ORDER_POLICY_NOT_APPROVED"]
REFERENCES = {
    "CSI ETABS point-object displacements": "https://docs.csiamerica.com/help-files/etabs/Output_Conventions/Displacements.htm",
    "CSI ETABS panel-zone displacements": "https://docs.csiamerica.com/help-files/etabs/Output_Conventions/Panel_Zone_Output.htm"}


def _analysis_basis(bank, chain, archive):
    rows, proof, reason = [], None, None
    try:
        observed = archive.table(STATIC_DEFINITIONS, ("Name", "StiffType", "NonlinCase"),
            required_units={"Name": "", "StiffType": "", "NonlinCase": ""})
        if observed is None:
            raise BankError("STATIC_STIFFNESS_TABLE_NOT_OBSERVED")
        rows, proof = observed
    except OPTIONAL_ERRORS as exc:
        reason = str(exc)
    by_case = defaultdict(list)
    for index, row in enumerate(rows):
        if row.get("Name"):
            by_case[row["Name"]].append({"source_row_index": index, "raw": row})
    cases = []
    for case in bank["case_definitions"]:
        if case.get("case_type") != 1:
            continue
        recorded = by_case[case["name"]]
        stiffness = sorted({r["raw"]["StiffType"] for r in recorded if r["raw"]["StiffType"] not in (None, "")})
        initial = sorted({r["raw"]["NonlinCase"] for r in recorded if r["raw"]["NonlinCase"] not in (None, "")})
        why = reason or ("STATIC_STIFFNESS_CASE_NOT_OBSERVED" if not stiffness else
            "STATIC_STIFFNESS_METADATA_CONFLICT" if len(stiffness) != 1 or len(initial) > 1 else None)
        setting = stiffness[0] if not why else None
        status = ("RECORDED_PDELTA_STIFFNESS" if setting == "P-Delta" else
            "RECORDED_NONLINEAR_CASE_UNRESOLVED" if setting == "Nonlinear Case" else
            "RECORDED_STIFFNESS_SETTING" if setting else "BLOCKED_INPUTS")
        cases.append({"case_name": case["name"], "case_type": 1, "native_type_source": case.get("source"),
            "status": status, "reason": why, "stiffness_type": setting,
            # The literal string 'None' is evidence, not a verified null state.
            "nonlinear_case_raw": initial[0] if len(initial) == 1 else None,
            "recorded_rows": recorded, "analysis_order": "NOT_PROVEN"})
    definitions = {c["name"]: c for c in bank["combination_definitions"]}
    combinations = []
    for route in chain["combinations"]:
        if route["classification"] != "STATIC_LINEAR_ADD":
            continue
        definition = definitions[route["combination"]]
        combinations.append({"combination": route["combination"], "terms": definition["terms"],
            "definition_sources": definition.get("source"), "case_names": route["case_names"],
            "analysis_order": "NOT_PROVEN", "automatic_second_order_route": None})
    return {"table_source": proof, "reason": reason, "cases": cases, "combinations": combinations,
        "status_counts": dict(Counter(c["status"] for c in cases)),
        "case_type_alone_proves_first_order": False, "analysis_order": "NOT_PROVEN"}


def _displacements(archive, cases, points):
    observed = archive.table(DISPLACEMENTS, DISPLACEMENT_FIELDS,
        required_units={c: "m" if c.startswith("U") else "rad" for c in COMPONENTS}, max_records=50000)
    if observed is None:
        raise BankError("JOINT_DISPLACEMENT_TABLE_NOT_OBSERVED")
    rows, proof = observed
    index = defaultdict(list)
    for number, row in enumerate(rows):
        if row["OutputCase"] in cases and row["UniqueName"] in points:
            index[(row["UniqueName"], row["OutputCase"])].append((number, row))
    return index, proof | {"coordinate_contract": COORDINATE_CONTRACT,
        "precision_status": "ROUNDED_DISPLAY_VALUES_NO_ERROR_BOUND", "zero_value_proves_zero_motion": False}


def _joint(index, proof, point, case, archive_sha):
    matches = index.get((point, case), [])
    if len(matches) != 1:
        raise BankError("JOINT_DISPLACEMENT_MISSING" if not matches else "JOINT_DISPLACEMENT_AMBIGUOUS")
    number, row = matches[0]
    # Blank step metadata is the table contract for a single-valued linear
    # combination. Never equate a Max/Min/modal/time-history state to it.
    if row["CaseType"] != "Combination" or any(row[k] not in (None, "") for k in ("StepType", "StepNumber", "StepLabel")):
        raise BankError("JOINT_DISPLACEMENT_NOT_SINGLE_STATIC_COMBINATION")
    values = {c: finite(float(_number(row[c], c)), c) for c in COMPONENTS}
    return {"point_id": point, "output_case": case, "source_row_index": number,
        "source_row_id": digest({"archive": archive_sha, "shard": proof["shard_sha256"], "row": number}),
        "source_call_id": proof["call_id"], "raw": row, "global_values": values,
        "precision_status": "ROUNDED_DISPLAY_VALUES_NO_ERROR_BOUND"}


def _force_pair(member, frame, candidates):
    if not candidates:
        raise BankError("COLUMN_STATIC_FORCE_STATES_MISSING")
    if any(r["native_key"]["StepType"] != "Single Value" or r["native_key"]["StepNum"] != 0
           or r["vector_status"] != "SIGNED_STATIC_SOURCE_VECTOR" for r in candidates):
        raise BankError("COLUMN_FORCE_PAIR_NOT_SINGLE_STATIC_STATE")
    g = member.get("station_geometry", {})
    length = frame["geometry"]["length_m"]
    offsets = g.get("native_facts", {}).get("offsets")
    if offsets is None:
        raise BankError("COLUMN_ENDPOINT_OFFSETS_NOT_BOUND")
    i = finite(offsets["values"]["Length1"], "offset_i")
    j = finite(offsets["values"]["Length2"], "offset_j")
    if min(i, j) < 0 or i+j >= length:
        raise BankError("COLUMN_ENDPOINT_OFFSETS_INVALID")
    stations = (i, length-j)
    if stations[1]-stations[0] <= 2*STATION_TOL_M:
        raise BankError("COLUMN_FORCE_END_MATCH_WINDOWS_OVERLAP")
    ends = []
    for station in stations:
        matches = [r for r in candidates if abs(r["native_key"]["ObjSta"]-station) <= STATION_TOL_M]
        if len(matches) != 1:
            raise BankError("COLUMN_FORCE_END_NOT_RECORDED" if not matches else "COLUMN_FORCE_END_AMBIGUOUS")
        ends.append(matches[0])
    if (ends[0]["state_id"] == ends[1]["state_id"]
            or ends[1]["native_key"]["ObjSta"] <= ends[0]["native_key"]["ObjSta"]):
        raise BankError("COLUMN_FORCE_ENDS_NOT_DISTINCT_AND_ORDERED")
    return {"i": ends[0], "j": ends[1], "offset_i_m": i, "offset_j_m": j,
        "source_offsets": offsets["source"], "object_i_j_length_m": length,
        "output_cut_span_m": ends[1]["native_key"]["ObjSta"]-ends[0]["native_key"]["ObjSta"],
        "i_cut_at_joint_coordinate": i == 0, "j_cut_at_joint_coordinate": j == 0,
        "output_cuts_are_physical_support_faces": False, "source_station_tolerance_m": STATION_TOL_M,
        "interior_states_retained_in_demand_chain": True, "end_pair_is_design_envelope": False}


def build_column_kinematics(bank, chain, joints, archive):
    if (joints.get("axis_convention") != AXIS_CONVENTION
            or bank["source_archive_sha256"] != archive.sha256 or chain["source_archive_sha256"] != archive.sha256
            or joints["source_archive_sha256"] != archive.sha256
            or chain["source_bank_result_sha256"] != bank["result_sha256"]
            or joints["source_bank_result_sha256"] != bank["result_sha256"]
            or joints["source_demand_result_sha256"] != chain["result_sha256"]
            or bank.get("run_id") != chain["source_run_id"] or joints["source_run_id"] != chain["source_run_id"]):
        raise BankError("KINEMATICS_SOURCE_BINDING_MISMATCH")
    basis = _analysis_basis(bank, chain, archive)
    combinations = [c["combination"] for c in basis["combinations"]]
    frames = {f["frame_id"]: f for f in joints["graph"]["frames"]}
    points = {p["point_id"]: p for p in joints["graph"]["points"]}
    selected = [identity(m["frame_name"], "member") for m in bank["members"]]
    if len(set(selected)) != len(selected):
        raise BankError("KINEMATICS_DUPLICATE_MEMBER")
    endpoints = {f[k] for n, f in frames.items() if n in selected for k in ("point_i", "point_j")}
    disp_index, disp_proof, disp_reason = {}, None, None
    try:
        disp_index, disp_proof = _displacements(archive, set(combinations), endpoints)
    except OPTIONAL_ERRORS as exc:
        disp_reason = str(exc)
    force_index = defaultdict(list)
    for row in chain["candidates"]:
        key = row["native_key"]
        force_index[(key["Obj"], key["LoadCase"])].append(row)
    rows = []
    for member in bank["members"]:
        name = member["frame_name"]
        frame = frames.get(name)
        for case in combinations:
            row = {"member_id": name, "output_case": case, "point_i": None, "point_j": None,
                "story": ((member.get("context") or {}).get("frame") or {}).get("story_label"),
                "force_status": "BLOCKED_INPUTS", "force_reason": None, "force_pair": None,
                "kinematics_status": "BLOCKED_INPUTS", "kinematics_reason": None, "joint_i": None, "joint_j": None,
                "calculation": None, "geometry_sources": None, "analysis_order": "NOT_PROVEN",
                "section_end_rotations_proven": False, "design_demand_authority": "DENIED",
                "final_design_eligible": False}
            geometry_reason = joints["graph"].get("reason") or "KINEMATICS_NATIVE_FRAME_GEOMETRY_NOT_BOUND"
            valid = joints["graph"]["status"] == "NATIVE_ENDPOINT_GRAPH_BOUND" and frame and frame.get("geometry")
            if valid:
                row.update(point_i=frame["point_i"], point_j=frame["point_j"],
                    geometry_sources={"frame": frame["source_calls"], "geometry": frame["geometry"]["source_calls"],
                        "point_i": points[frame["point_i"]]["source_call"], "point_j": points[frame["point_j"]]["source_call"]})
            else:
                geometry_reason = (frame or {}).get("geometry_reason") or geometry_reason
            try:
                if not valid:
                    raise BankError(geometry_reason)
                row["force_pair"] = _force_pair(member, frame, force_index[(name, case)])
                row["force_status"] = "SAME_CASE_FORCE_CUT_PAIR_BOUND"
            except OPTIONAL_ERRORS as exc:
                row["force_reason"] = str(exc)
            try:
                if not valid:
                    raise BankError(geometry_reason)
                if disp_reason:
                    raise BankError(disp_reason)
                ji, jj = [_joint(disp_index, disp_proof, frame["point_"+end], case, archive.sha256) for end in ("i", "j")]
                v = lambda source, prefix: [source["global_values"][prefix+c] for c in "xyz"]
                calc = joint_chord_kinematics(frame["geometry"]["axes_global"], frame["geometry"]["length_m"],
                    v(ji, "U"), v(jj, "U"), v(ji, "R"), v(jj, "R"))
                row.update(joint_i=ji, joint_j=jj, calculation=calc, kinematics_status="JOINT_CHORD_KINEMATICS_CALCULATED")
            except OPTIONAL_ERRORS as exc:
                row["kinematics_reason"] = str(exc)
            row["status"] = ("SAME_CASE_SOURCE_LINKED" if row["force_pair"] and row["calculation"] else
                "PARTIAL_SOURCE_LINK" if row["force_pair"] or row["calculation"] else "BLOCKED_INPUTS")
            row["link_id"] = "COLUMN-ENDS-"+digest({"schema": SCHEMA, "archive": archive.sha256, "member": name, "case": case})[:24]
            rows.append(row)
    result = {"schema": SCHEMA, "axis_convention": AXIS_CONVENTION, "coordinate_contract": COORDINATE_CONTRACT,
        "source_run_id": chain["source_run_id"], "source_archive_sha256": archive.sha256,
        "source_bank_result_sha256": bank["result_sha256"], "source_demand_result_sha256": chain["result_sha256"],
        "source_joints_result_sha256": joints["result_sha256"], "selected_member_count": len(selected),
        "static_combination_count": len(combinations), "expected_member_case_count": len(selected)*len(combinations),
        "bound_force_pair_count": sum(r["force_pair"] is not None for r in rows),
        "calculated_kinematics_count": sum(r["calculation"] is not None for r in rows),
        "linked_member_case_count": sum(r["status"] == "SAME_CASE_SOURCE_LINKED" for r in rows),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "reason_counts": dict(Counter(r[k] for r in rows for k in ("force_reason", "kinematics_reason") if r[k])),
        "displacement_table_source": disp_proof, "displacement_table_reason": disp_reason,
        "analysis_basis": basis, "rows": rows, "references": dict(REFERENCES), "open_basis": list(OPEN_BASIS),
        "analysis_order": "NOT_PROVEN", "analysis_generation_qualified": False,
        "actual_second_order_applied": False, "ts500_sway_phi": None, "effective_length_factor": None,
        "cm": None, "beta": None, "magnified_design_moments": None, "selected_design": None,
        "design_demand_authority": "DENIED", "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
    result["result_sha256"] = digest(result)
    return result


def kinematic_summaries(result):
    """One row per member/case, retaining signs and explicit I/J cut identities."""
    rows = []
    for row in result["rows"]:
        pair, calc = row["force_pair"] or {}, row["calculation"] or {}
        flat = {k: row[k] for k in ("link_id", "member_id", "story", "output_case", "point_i", "point_j",
            "status", "force_reason", "kinematics_reason", "analysis_order")}
        for end in ("i", "j"):
            state = pair.get(end, {})
            flat[end+"_station_m"] = state.get("native_key", {}).get("ObjSta")
            flat[end+"_element"] = state.get("native_key", {}).get("Elm")
            for component in ("P", "M2", "M3", "V2", "V3"):
                flat[end+"_"+component] = state.get("native_values", {}).get(component)
        flat.update({k: pair.get(k) for k in ("offset_i_m", "offset_j_m", "output_cut_span_m")})
        flat.update({k: calc.get(k) for k in ("object_i_j_length_m", "delta_local_m", "chord_alpha2_rad", "chord_alpha3_rad",
            "joint_i_relative_r2_rad", "joint_i_relative_r3_rad", "joint_j_relative_r2_rad", "joint_j_relative_r3_rad")})
        rows.append(flat)
    return rows
