"""Bind the TBDY 7.3.5.3(a) decision to native column ends for R10."""
from collections import defaultdict
from math import isclose

from ..column_engine.beam_references import station_budget
from ..column_engine.csi_geometry import physical_column_side_at_joint
from ..column_engine.native_archive import BankError
from ..column_engine.scwb_kernel import low_axial_limit_kn
from ..column_engine.source_bank import native_frame_force_rows
from .column_pmm import _oriented_element_chain
from .design_dependencies import _topology
from .design_scenario import _digest
from .mixed_demands import SCHEMA as MIXED_SCHEMA, SPECTRAL_METHOD, verify_combined_seismic_axial_cases


def _configured_end(scope, frame, end):
    uid = frame["frame_id"]
    mesh = scope["analysis_mesh"]["members"].get(uid, {})
    grid = scope["configured_output_cuts"].get(uid, {})
    if not mesh.get("roster_bound") or grid.get("status") != "REQUIRED_SUBSET_BOUND":
        raise BankError("SCWB_CONFIGURED_COLUMN_END_UNBOUND")
    chain = _oriented_element_chain(mesh["expected_analysis_element_ids"], mesh["analysis_element_end_joints"],
                                    frame["point_i"], frame["point_j"])
    if not chain:
        raise BankError("SCWB_COLUMN_ANALYSIS_ENDS_UNBOUND")
    length = grid["length_m"]
    obj = grid["offset_i_m"] if end == "I" else length - grid["offset_j_m"]
    elm = chain[0][0 if end == "I" else -1]
    cuts = [cut for cut in grid["cuts"] if cut["analysis_element_id"] == elm and
            abs(cut["object_station_m"] - obj) <= station_budget(cut["object_station_m"], obj, length)]
    if len(cuts) != 1:
        raise BankError("SCWB_CONFIGURED_COLUMN_END_MISSING_OR_AMBIGUOUS")
    cut = cuts[0]
    return (uid, cut["object_station_m"], elm, cut["element_station_m"]), length


def _spectral_upper(rows, pairs, limit):
    if len(rows) != 2 or {r[5] for r in rows} != {"Max", "Min"} or rows[0][:4] != rows[1][:4]:
        raise BankError("SCWB_TWO_SPECTRAL_EXTREMA_REQUIRED")
    if len(pairs) != 1 or pairs[0]["status"] != "SAME_SOURCE_COMPONENT_REPLAY_MATCH":
        raise BankError("SCWB_SAME_SOURCE_AXIAL_REPLAY_REQUIRED")
    cuts = [c for c in pairs[0]["cuts"] if tuple(c["native_cut"]) == rows[0][:4] and c["configured_required_cut"]]
    if len(cuts) != 1 or cuts[0]["primitive_replay"]["status"] != "NUMERICAL_MATCH":
        raise BankError("SCWB_COLUMN_END_AXIAL_REPLAY_UNRESOLVED")
    by_step = {row[5]: -row[7] for row in rows}  # ETABS P is negative in compression.
    nd = [by_step["Max"], by_step["Min"]]
    if nd[0] > nd[1]:
        raise BankError("SCWB_AXIAL_BOUNDS_REVERSED")
    for bounds in (cuts[0]["nd_bounds_kn"], cuts[0]["primitive_replay"]["nd_bounds_kn"]):
        if len(bounds) != 2 or not all(isclose(a, b, abs_tol=1e-9, rel_tol=1e-12) for a, b in zip(nd, bounds)):
            raise BankError("SCWB_COLUMN_END_AXIAL_BOUNDS_CONFLICT")
        if (bounds[1] <= limit) != (nd[1] <= limit):
            raise BankError("SCWB_AXIAL_THRESHOLD_STRADDLED_BY_REPLAY")
    return nd[1]


def _column_end_axial(joint, frame, end, points, scope, section, rowset, semantics, seismic, pairs):
    uid = frame["frame_id"]
    first, last = frame["point_i"], frame["point_j"]
    if end not in ("I", "J") or joint != (first if end == "I" else last):
        raise BankError("SCWB_PHYSICAL_END_IDENTITY_CONFLICT")
    side = physical_column_side_at_joint(points.get(joint), points.get(last if end == "I" else first))
    key, length = _configured_end(scope, frame, end)
    limit = low_axial_limit_kn(section.get("gross_area_mm2"), section.get("fck_mpa"))
    grouped = defaultdict(list)
    for row in native_frame_force_rows(rowset, uid):
        if (row[2] == key[2] and abs(row[1] - key[1]) <= station_budget(row[1], key[1], length)
                and abs(row[3] - key[3]) <= station_budget(row[3], key[3], length)):
            grouped[row[4]].append(row)
    maxima = {}
    other_unresolved = {}
    for name, role in semantics.items():
        sample = grouped[name]
        try:
            if not sample or any(r[6] != 0 for r in sample):
                raise BankError("SCWB_ASSIGNED_ZERO_STEP_END_MISSING")
            if role == "SCALAR_COMPONENT_ENVELOPE":
                maxima[name] = _spectral_upper(sample, pairs[uid, name], limit)
            elif role == "STATIC_SIGNED_VECTOR" and len(sample) == 1 and sample[0][5] in ("", "Single Value"):
                maxima[name] = -sample[0][7]
            else:
                raise BankError("SCWB_ASSIGNED_END_FORCE_UNSUPPORTED_OR_AMBIGUOUS")
        except BankError as exc:
            if name in seismic:
                raise BankError(f"{exc}:{name}") from exc
            other_unresolved[name] = str(exc)
    governing = None if other_unresolved else max(maxima, key=maxima.get)
    governing_seismic = max(seismic, key=maxima.get)
    return {"member_id": uid, "physical_side": side, "end": end, "configured_cut": list(key),
            "gross_area_mm2": section["gross_area_mm2"], "fck_mpa": section["fck_mpa"], "limit_kn": limit,
            "nd_max_by_combination_kn": maxima, "other_unresolved_combinations": other_unresolved,
            "governing_combination": governing, "max_nd_kn": maxima.get(governing),
            "governing_seismic_combination": governing_seismic, "max_seismic_nd_kn": maxima[governing_seismic]}


def joint_low_axial_decisions(source, axial, scope, mixed, dependency_plan, frames, points, adjacency,
                              seismic, *, input_sha):
    """Use assigned combinations at the two physical ends. Axial bounds need no concurrent moment or shear."""
    plan = axial.get("combination_plan") or {}
    if scope is None or plan.get("source") != "ASSIGNED_DESIGN":
        return {}
    assigned = (plan.get("design_assignment") or {}).get("groups") or {}
    expected = {name for group in assigned.values() for name in group}
    combos = plan.get("combinations") or []
    semantics = {row["name"]: row.get("force_semantics") for row in combos}
    force = (source.get("column_axial") or {}).get("force_source") or {}
    error = None
    if not input_sha or scope.get("input_sha256") != input_sha or scope.get("dependency_blockers"):
        error = "SCWB_INPUT_SCOPE_UNVERIFIED"
    elif plan.get("blockers") or not seismic or expected != semantics.keys() or len(combos) != len(semantics):
        error = "SCWB_ASSIGNED_COMBINATIONS_UNBOUND"
    elif (force.get("schema") != "tbdy.next.etabs-frame-force-source.v1" or force.get("api") != "Results.FrameForce"
          or force.get("units_code") != 6):
        error = "SCWB_NATIVE_FORCE_SOURCE_OR_UNITS_UNVERIFIED"
    else:
        try:
            verify_combined_seismic_axial_cases(source, seismic, semantics)
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            error = str(exc)
    pairs = defaultdict(list)
    if not error and "SCALAR_COMPONENT_ENVELOPE" in semantics.values():
        source_hash = dependency_plan["source_payload_sha256"] if dependency_plan else _digest(source)
        if (not mixed or mixed.get("schema") != MIXED_SCHEMA or mixed.get("method") != SPECTRAL_METHOD
                or mixed.get("input_sha256") != input_sha or mixed.get("source_payload_sha256") != source_hash
                or mixed.get("sha256") != _digest({k: v for k, v in mixed.items() if k != "sha256"})):
            if any(semantics[name] == "SCALAR_COMPONENT_ENVELOPE" for name in seismic):
                error = "SCWB_SAME_SOURCE_AXIAL_REPLAY_REQUIRED"
        else:
            for row in mixed["rows"]:
                pairs[row["member_id"], row["combination"]].append(row)
    topology_errors = dependency_plan["topology_blockers"] if dependency_plan else _topology(source)[2]
    sections = {c["element_id"]: c for c in axial.get("columns", ())}
    results = {}
    for joint, incident in adjacency.items():
        if not any(item["type"] == "Beam" for item in incident):
            continue
        cols = [item for item in incident if item["type"] == "Column"]
        if not cols:
            continue
        decision = {"clause": "TBDY 7.3.5.3(a)", "input_sha256": input_sha, "status": "UNRESOLVED",
                    "basis": "MAX_ASSIGNED_COMBINED_SEISMIC_ND_AT_CONFIGURED_COLUMN_ENDS",
                    "exempt": None, "assigned_combinations": sorted(expected), "seismic_combinations": sorted(seismic),
                    "column_ends": [], "reasons": []}
        results[joint] = decision
        if topology_errors:
            decision["reasons"] = list(topology_errors)
            continue
        if len(cols) != 2 or len({item["frame_id"] for item in cols}) != 2:
            decision["status"] = "NOT_A_TWO_COLUMN_JOINT"
            continue
        if dependency_plan is not None:
            expected_joint = dependency_plan["joints"].get(joint) or {}
            if set(expected_joint.get("column_ids", ())) != {item["frame_id"] for item in cols}:
                decision["reasons"].append("SCWB_EXPECTED_COLUMN_PAIR_UNBOUND")
                continue
            if expected_joint.get("source_blockers"):
                decision["reasons"].extend(expected_joint["source_blockers"])
                continue
        if error:
            decision["reasons"].append(error)
            continue
        for item in cols:
            uid = item["frame_id"]
            try:
                result = _column_end_axial(joint, frames[uid], item["end"], points, scope, sections.get(uid, {}),
                                           force["rowsets"].get(uid, {}), semantics, seismic, pairs)
                decision["column_ends"].append(result)
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                decision["reasons"].append(f"{uid}:{exc}")
        ends = decision["column_ends"]
        if decision["reasons"]:
            continue
        if {end["physical_side"] for end in ends} != {"UPPER", "LOWER"}:
            decision["reasons"].append("SCWB_OPPOSITE_COLUMN_SIDES_REQUIRED")
            continue
        exempt = all(end["max_seismic_nd_kn"] <= end["limit_kn"] for end in ends)
        decision.update(exempt=exempt, status="EXEMPT_LOW_AXIAL" if exempt else "LOW_AXIAL_LIMIT_EXCEEDED")
    return results
