"""Bind revised gravity story totals and member Euler inputs to their analysis generation."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from math import copysign, dist, fsum, isclose, isfinite
import re

from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.ts500_column import (
    SWAY_PERMITTED, SWAY_PREVENTED, effective_length_factor, elastic_sway_length_factor, euler_load_kn,
)
from .column_clear_length import WALL_CONNECTIVITY, WALL_COUPLED, proven_clear_length_m
from .column_pmm_section import MECHANICAL
from .column_r10_live import _build_frame_catalog

STORY_BASIS_SCHEMA = "tbdy.next.gravity-story-basis.v1"
CONTRIBUTOR_MODIFIER_SCHEMA = "tbdy.next.gravity-story-contributor-modifiers.v1"
CONDITIONAL_FRAME_BASIS_SCHEMA = "tbdy.next.gravity-story-conditional-frame-basis.v1"
CONDITIONAL_FRAME_SCOPE = "ADOPTED_CONDITIONAL_FRAME_COLUMNS_ONLY"
_CONDITIONAL_SUPPORTS = {
    "MAT_HINGED_REFERENCE": "MAT_ROTATIONAL_STIFFNESS_UNBOUND",
    "WALL_BELOW_HINGED_REFERENCE": "WALL_BELOW_ROTATIONAL_STIFFNESS_UNBOUND",
}
FRAME_FORCE = "NATIVE_FRAME_LOCAL_P_V2_V3"
WALL_FORCE = "INTEGRATED_WALL_GLOBAL_UPPER_FREE_BODY"
AXES = ("M2", "M3")
_CUT_TOL_M = 1e-6
_BALANCE_TOL_KN = .01
_BALANCE_REL_TOL = 1e-6
_SHA256 = re.compile(r"[a-f0-9]{64}")


def _checked(value, code):
    if not value:
        raise ValueError(code)


def _number(value, *, positive=False, native=False):
    if type(value) not in ((int, float, str) if native else (int, float)):
        raise ValueError("STORY_NUMERIC_INPUT_INVALID")
    result = float(value)
    if not isfinite(result) or positive and result <= 0:
        raise ValueError("STORY_NUMERIC_INPUT_INVALID")
    return result


def _text(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def _keys(value, fields, code):
    _checked(isinstance(value, Mapping) and set(value) == fields, code)
    return value


def _rows(tables, name, fields, *, units=None, allow_empty=False):
    table = tables.get(name) or {}
    rows, actual = table.get("rows"), table.get("fields")
    metadata = table.get("field_metadata") or {}
    _checked(table.get("status") == "CAPTURED" and metadata.get("status") == "OK" and
             isinstance(actual, list) and len(set(actual)) == len(actual) and fields <= set(actual) and
             isinstance(rows, list) and len(rows) == table.get("row_count") and (allow_empty or rows),
             "STORY_GEOMETRY_TABLE_UNBOUND:" + name)
    _checked(all(isinstance(row, Mapping) and set(row) == set(actual) for row in rows) and
             all((metadata.get("units_by_field") or {}).get(key) == unit for key, unit in (units or {}).items()),
             "STORY_GEOMETRY_TABLE_FORMAT_INVALID:" + name)
    return rows


def _index(rows, field):
    result = {}
    for row in rows:
        key = row[field]
        _checked(_text(key) and key not in result, "STORY_DUPLICATE_OR_INVALID_GEOMETRY_ID:" + field)
        result[key] = row
    return result


def _crosses(z, levels):
    # Use the upper part of the model. A member starting on the plane contributes;
    # the member ending at that plane from below belongs to the other free body.
    return min(levels) <= z + _CUT_TOL_M < max(levels)


def _physical_population(source, z):
    frames, frame_points, metadata = _build_frame_catalog(source)
    geometry = source["geometry_capture"]["tables"]
    native = source["vs06_b1_geometry_source"]["table_reads"]
    columns = _index(_rows(geometry, "COLUMN_CONNECTIVITY",
                           {"UniqueName", "Story", "UniquePtI", "UniquePtJ"}), "UniqueName")
    points = _index(_rows(native, "Point Object Connectivity", {"UniqueName", "X", "Y", "Z"},
                          units=dict.fromkeys("XYZ", "m")), "UniqueName")
    walls = _index(_rows(native, WALL_CONNECTIVITY, {"UniqueName", "Story", "UniquePt1", "UniquePt2", "UniquePt3"},
                         allow_empty=True), "UniqueName")
    assignments = _index(_rows(native, "Area Assignments - Section Properties", {"UniqueName", "Story", "PropType"},
                               allow_empty=True), "UniqueName")
    _checked(set(walls) == {uid for uid, row in assignments.items() if row["PropType"] == "Wall"},
             "STORY_WALL_CONNECTIVITY_ASSIGNMENT_SCOPE_CONFLICT")
    population = {}
    for uid, row in sorted(columns.items()):
        i, j = row["UniquePtI"], row["UniquePtJ"]
        coords = [[_number(points[pt][axis], native=True) for axis in "XYZ"] for pt in (i, j)]
        frame = frames[uid]
        _checked(frame["type"] == "Column" and frame["story"] == row["Story"] and
                 (frame["point_i"], frame["point_j"]) == (i, j) and
                 all(all(isclose(a, b, abs_tol=_CUT_TOL_M, rel_tol=0) for a, b in zip(xyz, frame_points[pt]))
                     for xyz, pt in zip(coords, (i, j))) and
                 abs(coords[0][2] - coords[1][2]) > _CUT_TOL_M,
                 "STORY_COLUMN_GEOMETRY_CONFLICT:" + uid)
        if _crosses(z, [xyz[2] for xyz in coords]):
            population["COLUMN", uid] = frame
    for uid, row in sorted(walls.items()):
        _checked(row["Story"] == assignments[uid]["Story"], "STORY_WALL_STORY_CONFLICT:" + uid)
        corners = [p for key, p in row.items() if re.fullmatch(r"UniquePt[0-9]+", key) and p not in (None, "", "None")]
        _checked(len(corners) >= 3 and len(corners) == len(set(corners)), "STORY_WALL_POLYGON_UNBOUND:" + uid)
        levels = [_number(points[p]["Z"], native=True) for p in corners]
        _checked(max(levels) - min(levels) > _CUT_TOL_M, "STORY_WALL_POLYGON_UNBOUND:" + uid)
        if _crosses(z, levels):
            population["WALL", uid] = row
    return population, frames, frame_points, metadata["adjacency"]


def _free_body_force(row, item):
    vector = row["vector_kn"]
    _checked(isinstance(vector, list) and len(vector) == 3, "STORY_FORCE_VECTOR_SHAPE_INVALID")
    values = [_number(value) for value in vector]
    if row["kind"] == "WALL":
        _checked(row["representation"] == WALL_FORCE, "STORY_WALL_FORCE_NOT_INDEPENDENTLY_INTEGRATED")
        return values[2], max(0.0, values[2])
    axis = item["axes_global"]
    _checked(row["representation"] == FRAME_FORCE and axis is not None and abs(axis[0][2]) > _CUT_TOL_M,
             "STORY_FRAME_FORCE_AXES_UNBOUND")
    # ETABS P is tension-positive on the positive I-to-J face. Convert the
    # vector to the force exerted on the upper free body's lower face.
    vertical = -copysign(1, axis[0][2]) * fsum(v * axis[i][2] for i, v in enumerate(values))
    return vertical, max(0.0, -values[0])


def _reference_target_rows(level, uid, labels, z):
    elements = tuple(level["mesh"][uid])
    # Coarser meshes and the physical model can have several segments at the
    # plane. Pick the segment on the upper side, never the two interface sides.
    elem = [r for r in elements if _crosses(z, (r["i_xyz"][2], r["j_xyz"][2]))]
    _checked(len(elem) == 1, "STORY_REFERENCE_UPPER_ELEMENT_UNRESOLVED")
    elem = elem[0]
    a, b = elem["i_xyz"], elem["j_xyz"]
    length = dist(a, b)
    station = (z - a[2]) / (b[2] - a[2]) * length
    native = native_frame_force_rows(level["force_source"]["rowsets"][uid], uid)
    observed = {}
    for _, _, element, elm_station, name, step, step_no, p, v2, v3, *_ in native:
        if (element == elem["element"] and name in labels and (step, step_no) == ("Step", 1.0) and
                isclose(elm_station, station, abs_tol=_CUT_TOL_M, rel_tol=0)):
            _checked(name not in observed, "STORY_REFERENCE_DUPLICATE_NATIVE_CUT:" + name)
            observed[name] = (element, (p, v2, v3))
    return observed


def project_native_story_frame_forces(source, level, uid, cut_z_m, cases, capture):
    """Convert verified native first-order frame arrays to upper-free-body input rows.

    Wall geometry stays in the expected census. A separate integrated wall
    reading is needed for its force term.
    """
    result = {"member_id": uid, "status": "STORY_NATIVE_FRAME_SOURCE_UNBOUND", "reasons": [], "forces": []}
    try:
        _checked(capture.get("model_sha256") == level["model_sha256"] and
                 capture.get("analysis_generation") == level["analysis_generation"] and
                 _text(level["analysis_generation"]) and _SHA256.fullmatch(level["analysis_generation"]),
                 "STORY_NATIVE_FRAME_MODEL_GENERATION_MISMATCH")
        z = _number(cut_z_m)
        population, frames, points, _ = _physical_population(source, z)
        target = population["COLUMN", uid]
        result.update(story=target["story"], cut_z_m=z, expected_contributors=[
            {"kind": kind, "object_id": member} for kind, member in sorted(population)])
        named = capture["tables"]
        _checked(named.get("model_locked") is True and named.get("model_units_code") == 6 and
                 named.get("selection_restored") is True and named.get("case_selection_before") == named.get("case_selection_after"),
                 "STORY_NATIVE_FRAME_MESH_CAPTURE_CONTEXT_MISMATCH")
        tables = named["table_reads"]
        joints = _index(_rows(tables, "Objects and Elements - Joints", {"ElmName", "GlobalX", "GlobalY", "GlobalZ"},
                              units={f"Global{x}": "m" for x in "XYZ"}), "ElmName")
        mesh = defaultdict(list)
        used = set()
        for row in _rows(tables, "Objects and Elements - Frames", {"ObjType", "ObjName", "ElmName", "ElmJtI", "ElmJtJ"}):
            # ETABS also returns generated Shell rows in this table. Their
            # object/element names can overlap the native Frame namespace.
            if row["ObjType"] != "Frame":
                continue
            if ("COLUMN", row["ObjName"]) not in population:
                continue
            name = row["ElmName"]
            _checked(_text(name) and name not in used, "STORY_NATIVE_FRAME_MESH_DUPLICATE_ELEMENT")
            used.add(name)
            a, b = ([_number(joints[row[side]][key], native=True) for key in ("GlobalX", "GlobalY", "GlobalZ")]
                    for side in ("ElmJtI", "ElmJtJ"))
            if _crosses(z, (a[2], b[2])):
                mesh[row["ObjName"]].append((name, a, b))
        force = capture["columns"]
        labels = {pair["first"] for pair in cases.values()}
        during = force.get("output_selection_during") or {}
        _checked(force.get("schema") == "tbdy.next.etabs-frame-force-source.v1" and force.get("units_code") == 6 and
                 force.get("api") == "Results.FrameForce" and force.get("item_type") == "ObjectElm" and
                 force.get("output_selection_before") and force["output_selection_before"] == force.get("output_selection_after") and
                 {n for n, on in during.get("cases", {}).items() if on is True} == labels and
                 not any(during.get("combos", {}).values()), "STORY_NATIVE_FRAME_FORCE_CONTRACT_UNVERIFIED")
    except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError) as exc:
        result["reasons"].append(str(exc))
        return result

    members = [name for kind, name in population if kind == "COLUMN"]
    for member in sorted(members):
        try:
            _checked(len(mesh[member]) == 1, "STORY_NATIVE_FRAME_UPPER_ELEMENT_MISSING_OR_AMBIGUOUS")
            element, a, b = mesh[member][0]
            frame = frames[member]
            axes = frame["axes_global"]
            _checked(axes is not None and abs(axes[0][2]) > _CUT_TOL_M, "STORY_NATIVE_FRAME_AXIS_UNBOUND")
            axis = axes[0]
            origin = points[frame["point_i"]]
            element_sta = (z - a[2]) / axis[2]
            object_sta = (z - origin[2]) / axis[2]
            _checked(all(isclose(a[i] + element_sta * axis[i], origin[i] + object_sta * axis[i],
                                 rel_tol=0, abs_tol=_CUT_TOL_M) for i in range(3)) and
                     (b[2] - a[2]) * axis[2] > 0, "STORY_NATIVE_FRAME_MESH_AXIS_UNVERIFIED")
            by_case = {}
            for _, obj, elm, sta, case, step, num, p, v2, v3, *_ in native_frame_force_rows(force["rowsets"][member], member):
                if (elm == element and isclose(sta, element_sta, abs_tol=_CUT_TOL_M, rel_tol=0) and
                        isclose(obj, object_sta, abs_tol=_CUT_TOL_M, rel_tol=0)):
                    _checked(case in labels and case not in by_case and (step, num) == ("Step", 1.0),
                             "STORY_NATIVE_FRAME_CASE_STEP_OR_SIDE_UNVERIFIED")
                    by_case[case] = {"kind": "COLUMN", "object_id": member, "element_id": elm, "case": case,
                                     "step_type": step, "step_number": num, "z_m": z,
                                     "representation": FRAME_FORCE, "vector_kn": [p, v2, v3]}
            result["forces"].extend(by_case.values())
            result["reasons"].extend(f"STORY_NATIVE_FRAME_FORCE_MISSING:{member}:{case}" for case in sorted(labels-by_case.keys()))
        except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError) as exc:
            result["reasons"].append(f"{exc}:{member}")
    result["status"] = "STORY_NATIVE_FRAME_SOURCE_INCOMPLETE" if result["reasons"] else "STORY_NATIVE_FRAME_SOURCE_CALCULATED"
    return result


def _force_results(rows, equilibrium, population, reference, labels, uid, z, *, frame_scope=False):
    lines = defaultdict(dict)
    issues = defaultdict(list)
    for row in rows:
        _keys(row, {"kind", "object_id", "element_id", "case", "step_type", "step_number", "z_m",
                    "representation", "vector_kn"}, "STORY_FORCE_ROW_SHAPE_INVALID")
        name = row["case"]
        _checked(_text(name) and name in labels, "STORY_FORCE_CASE_NOT_EXPECTED")
        kind, object_id = row["kind"], row["object_id"]
        _checked(kind in ("COLUMN", "WALL") and _text(object_id), "STORY_FORCE_CONTRIBUTOR_ID_INVALID")
        key = kind, object_id
        label = f"{kind}:{object_id}"
        if key not in population:
            issues[name].append((kind, "STORY_FORCE_CONTRIBUTOR_NOT_EXPECTED:" + label))
            continue
        if key in lines[name]:
            issues[name].append((kind, "STORY_FORCE_DUPLICATE_CONTRIBUTOR:" + label))
            continue
        try:
            _checked(_text(row["element_id"]) and row["step_type"] == "Step" and _number(row["step_number"]) == 1
                     and isclose(_number(row["z_m"]), z, abs_tol=_CUT_TOL_M, rel_tol=0),
                     "STORY_FORCE_CUT_OR_STEP_MISMATCH")
            vertical, compression = _free_body_force(row, population[key])
            if key == ("COLUMN", uid):
                same = reference.get(name)
                _checked(same is not None and same[0] == row["element_id"] and all(
                    isclose(a, b, rel_tol=1e-9, abs_tol=1e-6) for a, b in zip(same[1], row["vector_kn"])),
                    "STORY_FORCE_DOES_NOT_MATCH_REFINED_FIRST_ORDER_CUT")
            lines[name][key] = {"kind": kind, "object_id": object_id, "element_id": row["element_id"],
                                "representation": row["representation"], "vertical_kn": vertical,
                                "compression_kn": compression}
        except ValueError as exc:
            issues[name].append((kind, f"{exc}:{label}"))
    for key in population:
        native_ids = {r[key]["element_id"] for r in lines.values() if key in r}
        if len(native_ids) > 1:
            for name in labels:
                issues[name].append((key[0], "STORY_FORCE_CONTRIBUTOR_ELEMENT_CHANGED:" + ":".join(key)))

    result = {}
    for name in sorted(labels):
        forces = lines[name]
        missing = sorted(population.keys() - forces.keys())
        case_issues = issues[name] + [(key[0], "STORY_FORCE_MISSING:" + ":".join(key)) for key in missing]
        reasons = [reason for _, reason in case_issues]
        signed = fsum(row["vertical_kn"] for row in forces.values())
        compression = fsum(row["compression_kn"] for row in forces.values())
        total = {"native_case": name, "expected_count": len(population), "evaluated_count": len(forces),
                 "contributors": [row for _, row in sorted(forces.items())], "signed_vertical_sum_kn": signed,
                 "supported_compression_kn": compression, "reasons": reasons}
        try:
            eq = _keys(equilibrium.get(name), {"upper_external_applied_kn", "upper_self_weight_kn", "reference"},
                       "STORY_FREE_BODY_EQUILIBRIUM_UNAVAILABLE")
            load, weight = (_number(eq[key]) for key in ("upper_external_applied_kn", "upper_self_weight_kn"))
            _checked(weight >= 0 and _text(eq["reference"]), "STORY_FREE_BODY_EQUILIBRIUM_UNAVAILABLE")
            expected = load + weight
            total.update(free_body=dict(eq), free_body_load_kn=expected, equilibrium_residual_kn=signed - expected)
            if not isclose(signed, expected, abs_tol=_BALANCE_TOL_KN, rel_tol=_BALANCE_REL_TOL):
                reasons.append("STORY_FREE_BODY_VERTICAL_IMBALANCE")
        except ValueError as exc:
            reasons.append(str(exc))
        if compression <= 0:
            reasons.append("STORY_COMPRESSION_NONPOSITIVE")
        total.update(status="STORY_COMPRESSION_BOUND" if not reasons else "STORY_COMPRESSION_INCOMPLETE")
        if frame_scope:
            frames = [row for row in forces.values() if row["kind"] == "COLUMN"]
            frame_nd = fsum(row["compression_kn"] for row in frames)
            frame_reasons = [reason for kind, reason in case_issues if kind == "COLUMN"]
            if frame_nd <= 0:
                frame_reasons.append("STORY_FRAME_COLUMN_COMPRESSION_NONPOSITIVE")
            total["frame_column_compression"] = {
                "status": "STORY_FRAME_COLUMN_COMPRESSION_BOUND" if not frame_reasons
                          else "STORY_FRAME_COLUMN_COMPRESSION_INCOMPLETE",
                "expected_count": sum(kind == "COLUMN" for kind, _ in population),
                "evaluated_count": len(frames), "nd_kn": frame_nd, "reasons": frame_reasons,
            }
        result[name] = total
    return result


def _end_restraint(record, joints, neighbors, frames, uid, axis_ref, ln, ei, sway, end_references=None):
    _keys(record, {"method", "i", "j"}, "STORY_END_RESTRAINT_METHOD_UNBOUND")
    details, numerical = [], []
    method = record["method"]
    for side, joint in zip(("i", "j"), joints):
        end = record[side]
        if method == "ELASTIC_SWAY_END_SPRINGS":
            _keys(end, {"joint_id", "k_knm_per_rad", "reference"}, "STORY_END_SPRING_UNBOUND")
            value = _number(end["k_knm_per_rad"])
            _checked(value >= 0, "STORY_NEGATIVE_END_SPRING")
        elif method == "TS500_FRAME_JOINT_RATIO" and isinstance(end, Mapping) and "support_idealization" in end:
            _keys(end, {"joint_id", "support_idealization", "reference"}, "STORY_CONDITIONAL_SUPPORT_UNBOUND")
            expected = _CONDITIONAL_SUPPORTS.get(end["support_idealization"])
            observed = (end_references or {}).get(side.upper(), {})
            _checked(expected is not None and observed.get("basis") == expected and observed.get("joint_id") == joint,
                     "STORY_CONDITIONAL_SUPPORT_GEOMETRY_MISMATCH")
            value = None
        elif method == "TS500_FRAME_JOINT_RATIO":
            _keys(end, {"joint_id", "column_terms", "beam_terms", "reference"}, "STORY_FRAME_JOINT_RATIO_UNBOUND")
            potential = {}
            for neighbor in neighbors[joint]:
                member, kind = neighbor["frame_id"], neighbor["type"]
                basis = frames[member]["axes_global"]
                _checked(basis is not None, "STORY_FRAME_END_NEIGHBOR_AXES_UNBOUND")
                along, about_2, about_3 = (abs(fsum(x*y for x, y in zip(a, axis_ref))) for a in basis)
                # A beam parallel to the moment axis is a torsional path.
                # This framed ratio credits directional bending only.
                if kind == "Beam" and isclose(along, 1., rel_tol=0, abs_tol=1e-8):
                    continue
                _checked(any(isclose(a, 1., rel_tol=0, abs_tol=1e-8) for a in (about_2, about_3)),
                         "STORY_FRAME_END_SKEW_NEIGHBOR_UNSUPPORTED")
                potential[member] = kind
            subtotal, used = [], set()
            for terms, kind in ((end["column_terms"], "Column"), (end["beam_terms"], "Beam")):
                _checked(isinstance(terms, list) and terms, "STORY_FRAME_JOINT_RATIO_TERMS_MISSING")
                values = []
                for term in terms:
                    _keys(term, {"object_id", "ei_nmm2", "length_mm"}, "STORY_FRAME_END_TERM_UNBOUND")
                    member = term["object_id"]
                    _checked(_text(member) and potential.get(member) == kind and member not in used,
                             "STORY_FRAME_END_TERM_ID_CONFLICT")
                    used.add(member)
                    term_ei = _number(term["ei_nmm2"], positive=True)
                    _checked(member != uid or isclose(term_ei, ei, rel_tol=1e-6, abs_tol=0),
                             "STORY_FRAME_END_TARGET_TERM_EI_MISMATCH")
                    values.append(term_ei / _number(term["length_mm"], positive=True))
                subtotal.append(fsum(values))
            _checked(used == potential.keys(), "STORY_FRAME_END_NEIGHBOR_POPULATION_INCOMPLETE")
            value = subtotal[0] / subtotal[1]
        else:
            raise ValueError("STORY_END_RESTRAINT_METHOD_UNSUPPORTED")
        _checked(end["joint_id"] == joint and _text(end["reference"]), "STORY_END_RESTRAINT_IDENTITY_UNBOUND")
        numerical.append(value)
        details.append({**end, "resolved_value": value})
    if method == "ELASTIC_SWAY_END_SPRINGS":
        _checked(sway == SWAY_PERMITTED, "STORY_END_SPRING_SWAY_POLICY_MISMATCH")
        k = elastic_sway_length_factor(clear_length_m=ln/1000, ei_knm2=ei/1e9,
                                       k_i_knm_per_rad=numerical[0], k_j_knm_per_rad=numerical[1])
    elif None in numerical:
        _checked(numerical.count(None) == 1, "STORY_CONDITIONAL_TWO_UNBOUND_SUPPORTS_UNSUPPORTED")
        fixed = [0.0 if value is None else value for value in numerical]
        candidates = {"fixed": effective_length_factor(alpha_i=fixed[0], alpha_j=fixed[1], sway=sway),
                      "hinged": effective_length_factor(alpha_i=numerical[0], alpha_j=numerical[1], sway=sway)}
        return max(candidates.values()), {"method": method, "basis": "CONDITIONAL_EXTERNAL_RESTRAINT_ASSUMPTION",
                                         "ends": details, "candidate_k": candidates}
    else:
        k = effective_length_factor(alpha_i=numerical[0], alpha_j=numerical[1], sway=sway)
    return k, {"method": method, "basis": "ADOPTED_MODEL_BOUND_END_RESTRAINTS", "ends": details}


def _column_axis(column, uid, axis, frames, frames_points, adjacency, expected_ln, expected_ei, modifiers,
                 end_references=None):
    _keys(column, {"ln_mm", "sway", "creep_reference", "axes"}, "STORY_COLUMN_STIFFNESS_BASIS_UNBOUND")
    _checked(column["sway"] in (SWAY_PERMITTED, SWAY_PREVENTED) and _text(column["creep_reference"]),
             "STORY_COLUMN_CREEP_OR_SWAY_BASIS_UNBOUND")
    frame = frames[uid]
    ln = _number(column["ln_mm"], positive=True)
    joints = frame["point_i"], frame["point_j"]
    full = dist(frames_points[joints[1]], frames_points[joints[0]]) * 1000
    _checked(ln <= full + .001 and (expected_ln is None or isclose(ln, expected_ln, abs_tol=.001, rel_tol=0)),
             "STORY_COLUMN_CLEAR_LENGTH_MISMATCH")
    info = _keys(column["axes"].get(axis), {"ec_mpa", "i_mm4", "section_modifier", "object_modifier", "restraint"},
                 "STORY_COLUMN_AXIS_STIFFNESS_UNBOUND")
    e, inertia, section, obj = (_number(info[key], positive=True)
                                for key in ("ec_mpa", "i_mm4", "section_modifier", "object_modifier"))
    dims = frame["dims"]
    _checked(dims is not None, "STORY_COLUMN_RECTANGULAR_SECTION_UNBOUND")
    d2, d3 = dims.local2_extent_mm, dims.local3_extent_mm
    native_inertia = (d2 * d3**3 if axis == "M2" else d3 * d2**3) / 12
    ei = e * inertia * section * obj
    _checked(isclose(inertia, native_inertia, rel_tol=1e-6, abs_tol=0) and isfinite(ei) and
             (expected_ei is None or isclose(ei, expected_ei, rel_tol=1e-6, abs_tol=0)) and
             (modifiers is None or isclose(obj, modifiers[4 if axis == "M2" else 5], rel_tol=1e-6, abs_tol=0)),
             "STORY_COLUMN_NATIVE_OR_SELECTED_EI_MISMATCH")
    axis_vector = frame["axes_global"][1 if axis == "M2" else 2]
    k, restraint = _end_restraint(info["restraint"], joints, adjacency, frames, uid, axis_vector, ln, ei,
                                  column["sway"], end_references)
    lk = k * ln
    return {"member_id": uid, "axis": axis, "ec_mpa": e, "native_i_mm4": inertia,
            "section_modifier": section, "object_modifier": obj, "effective_ei_nmm2": ei,
            "ln_mm": ln, "k": k, "lk_mm": lk, "member_nk_kn": euler_load_kn(effective_ei_nmm2=ei, effective_length_lk_mm=lk),
            "sway": column["sway"], "creep_reference": column["creep_reference"], "restraint": restraint}


def _reported_column_details(source):
    """Optional independent native tables used to bind non-target column data."""
    axial = source.get("column_axial") or {}
    motion = (axial.get("r10_source") or {}).get("table_reads") or {}
    props = (axial.get("pmm_section_source") or {}).get("table_reads") or {}
    geometry = source["geometry_capture"]["tables"]
    name = "Frame Assignments - End Length Offsets"
    offsets = (_index(_rows(motion, name, {"UniqueName", "OffsetI", "OffsetJ"},
                            units={"OffsetI": "m", "OffsetJ": "m"}), "UniqueName")
               if name in motion else {})
    materials = (_index(_rows(props, MECHANICAL, {"Material", "E1"}, units={"E1": "kN/m2"}), "Material")
                 if MECHANICAL in props else {})
    table = geometry.get("SECTION_SUMMARY") or {}
    sections = (_index(_rows(geometry, "SECTION_SUMMARY", {"Name", "I2Mod", "I3Mod"}), "Name")
                if {"I2Mod", "I3Mod"} <= set(table.get("fields") or ()) else {})
    return offsets, materials, sections


def _contributor_modifiers(block, level, population, frames):
    """Keep the story stiffness census separate from the paired-refinement mesh."""
    capture = block.get("contributor_modifiers")
    if capture is None:
        # Legacy records retain their original paired-member scope. Missing
        # non-paired contributors remain explicitly unresolved downstream.
        return level["frame_object_modifiers"], None
    _keys(capture, {"schema", "model_sha256", "analysis_generation", "modifiers"},
          "STORY_CONTRIBUTOR_MODIFIER_SOURCE_INVALID")
    _checked(capture["schema"] == CONTRIBUTOR_MODIFIER_SCHEMA and
             capture["model_sha256"] == level["model_sha256"] and
             capture["analysis_generation"] == level["analysis_generation"],
             "STORY_CONTRIBUTOR_MODIFIER_MODEL_GENERATION_MISMATCH")
    values = capture["modifiers"]
    expected = {uid for kind, uid in population if kind == "COLUMN"}
    allowed = {uid for uid, frame in frames.items() if frame["type"] == "Column"}
    _checked(isinstance(values, Mapping) and set(values) <= allowed,
             "STORY_CONTRIBUTOR_MODIFIER_POPULATION_CONFLICT")
    _checked(expected <= values.keys(), "STORY_CONTRIBUTOR_MODIFIER_SCOPE_INCOMPLETE:" +
             ",".join(sorted(expected - values.keys())))
    normalized = {}
    for uid, row in values.items():
        _checked(isinstance(row, list) and len(row) == 8,
                 "STORY_CONTRIBUTOR_MODIFIER_VECTOR_INVALID:" + uid)
        normalized[uid] = [_number(value) for value in row]
        paired = level["frame_object_modifiers"].get(uid)
        _checked(paired is None or normalized[uid] == paired,
                 "STORY_CONTRIBUTOR_MODIFIER_PAIRED_MEMBER_CONFLICT:" + uid)
    from .design_scenario import _digest

    return normalized, {"schema": CONTRIBUTOR_MODIFIER_SCHEMA,
        "model_sha256": capture["model_sha256"], "analysis_generation": capture["analysis_generation"],
        "source_sha256": _digest(capture), "expected_column_ids": sorted(expected),
        "captured_column_ids": sorted(normalized)}


def _conditional_frame_basis(block, story, uid, population, physical_lengths):
    adoption = _keys(block["conditional_frame_basis"], {"schema", "decision_reference", "stories"},
                     "STORY_CONDITIONAL_FRAME_SOURCE_INVALID")
    _checked(adoption["schema"] == CONDITIONAL_FRAME_BASIS_SCHEMA and _text(adoption["decision_reference"])
             and isinstance(adoption["stories"], Mapping), "STORY_CONDITIONAL_FRAME_SOURCE_INVALID")
    row = _keys(adoption["stories"].get(story), {"credited_column_ids", "excluded_coupled_column_ids"},
                "STORY_CONDITIONAL_FRAME_POPULATION_UNBOUND")
    _checked(all(isinstance(ids, list) and all(_text(col) for col in ids) and len(set(ids)) == len(ids)
                 for ids in row.values()), "STORY_CONDITIONAL_FRAME_POPULATION_INVALID")
    credited, coupled = (set(row[key]) for key in ("credited_column_ids", "excluded_coupled_column_ids"))
    expected = {col for kind, col in population if kind == "COLUMN"}
    _checked(uid in credited and credited.isdisjoint(coupled) and credited | coupled == expected,
             "STORY_CONDITIONAL_FRAME_POPULATION_MISMATCH")
    for col in sorted(credited):
        _checked(proven_clear_length_m(physical_lengths.get(col), col) is not None,
                 "STORY_CONDITIONAL_ISOLATED_LENGTH_UNBOUND:" + col)
    for col in sorted(coupled):
        proof = physical_lengths.get(col) or {}
        _checked(proof.get("member_id") == col and proof.get("status") == WALL_COUPLED,
                 "STORY_CONDITIONAL_EXCLUDED_COLUMN_COUPLING_UNPROVEN:" + col)
    return {"schema": adoption["schema"], "scope": CONDITIONAL_FRAME_SCOPE,
            "decision_reference": adoption["decision_reference"], "engineering_approval": "NOT_GRANTED",
            "expected_column_ids": sorted(expected), "credited_column_ids": sorted(credited),
            "excluded_coupled_column_ids": sorted(coupled),
            "excluded_wall_ids": sorted(col for kind, col in population if kind == "WALL"),
            "cases": {}, "axes": {}, "story_inputs": {}}


def produce_story_basis(source, local, level, uid, cases, *, story_geometry=None):
    """Compute a story basis from one mesh's force and stiffness source.

    Full-story scope and signed equilibrium come from the horizontal free body.
    Explicit adoption can also use the complete frame-column compression and
    the independently isolated critical-load population under a separate scope.
    """
    result = {"status": "REVISED_STORY_BASIS_SOURCE_UNAVAILABLE", "member_id": uid, "story_inputs": {},
              "reasons": [], "cases": {}, "axes": {}, "engineering_approval": "NOT_GRANTED"}
    block = level.get("story_basis_source")
    if block is None:
        return result
    try:
        required = {"schema", "model_sha256", "analysis_generation", "units_code", "story_cuts", "columns"}
        optional = {"contributor_modifiers", "conditional_frame_basis"}
        _keys(block, required | (optional & block.keys()), "STORY_BASIS_SCHEMA_INVALID")
        generation = level.get("analysis_generation")
        _checked(block["schema"] == STORY_BASIS_SCHEMA and block["model_sha256"] == level["model_sha256"] and
                 _text(generation) and _SHA256.fullmatch(generation) and block["analysis_generation"] == generation and
                 type(block["units_code"]) is int and block["units_code"] == 6,
                 "STORY_BASIS_MODEL_GENERATION_OR_UNITS_MISMATCH")
        _checked(isinstance(block["story_cuts"], Mapping) and isinstance(block["columns"], Mapping),
                 "STORY_BASIS_SOURCE_SCOPE_INVALID")
        physical = local.get("physical_clear_length")
        ln = proven_clear_length_m(physical, uid)
        _checked(ln is not None, "STORY_TARGET_PHYSICAL_CLEAR_LENGTH_UNBOUND")
        lower = _number(physical["faces"]["I"]["top_z_m"])
        population, frames, frame_points, adjacency = _physical_population(source, lower)
        target = population["COLUMN", uid]
        _checked(target["axes_global"] is not None and _text(target["story"]), "STORY_TARGET_AXES_OR_ID_UNBOUND")
        story = target["story"]
        result.update(story=story, cut_z_m=lower, model_sha256=block["model_sha256"], analysis_generation=generation,
                      expected_contributors=[{"kind": k, "object_id": v} for k, v in sorted(population)],
                      sign_convention="UPPER_FREE_BODY_LOWER_FACE_UPWARD_FORCE_POSITIVE")
    except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError) as exc:
        result.update(status="REVISED_STORY_BASIS_UNBOUND", reasons=[str(exc)])
        return result

    geometry = story_geometry or {}
    physical_lengths = geometry.get("physical_lengths", {})
    conditional = None
    if "conditional_frame_basis" in block:
        try:
            _checked("contributor_modifiers" in block, "STORY_CONDITIONAL_FRAME_MODIFIERS_REQUIRED")
            conditional = _conditional_frame_basis(block, story, uid, population, physical_lengths)
            result["conditional_frame_basis"] = conditional
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            result["conditional_frame_basis"] = {
                "status": "REVISED_CONDITIONAL_FRAME_BASIS_UNBOUND", "reasons": [str(exc)]}
    credited = set(conditional["credited_column_ids"]) if conditional is not None else set()
    coupled = set(conditional["excluded_coupled_column_ids"]) if conditional is not None else set()
    labels = {pair["first"]: name for name, pair in cases.items()}
    try:
        section = _keys(block["story_cuts"].get(story), {"z_m", "forces", "equilibrium"}, "STORY_CUT_SOURCE_UNAVAILABLE:" + story)
        _checked(isclose(_number(section["z_m"]), lower, rel_tol=0, abs_tol=_CUT_TOL_M) and
                 isinstance(section["forces"], list) and isinstance(section["equilibrium"], Mapping) and
                 set(section["equilibrium"]) <= set(labels), "STORY_CUT_SOURCE_PLANE_OR_CASE_MISMATCH")
        reference = _reference_target_rows(level, uid, labels, lower)
        result["cases"] = {labels[name]: v for name, v in
                           _force_results(section["forces"], section["equilibrium"], population, reference, labels, uid,
                                          lower, frame_scope=conditional is not None).items()}
        if conditional is not None:
            conditional["cases"] = {name: row["frame_column_compression"] for name, row in result["cases"].items()}
    except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError) as exc:
        result["reasons"].append(str(exc))

    try:
        offsets, materials, sections = _reported_column_details(source)
    except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError) as exc:
        offsets = materials = sections = {}
        result["reasons"].append(str(exc))
    try:
        modifier_rows, modifier_evidence = _contributor_modifiers(block, level, population, frames)
        if modifier_evidence is not None:
            result["contributor_modifier_source"] = modifier_evidence
    except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError) as exc:
        modifier_rows = {}
        result["reasons"].append(str(exc))
    supported = {}
    for axis, i in zip(AXES, (1, 2)):
        rows, gaps = [], []
        credited_rows, credited_gaps = [], []
        axis_ref = target["axes_global"][i]
        for kind, element in sorted(population):
            if kind == "WALL":
                gaps.append("STORY_WALL_CRITICAL_LOAD_METHOD_UNSUPPORTED:" + element)
                continue
            if element in coupled:
                gaps.append("STORY_COUPLED_COLUMN_CRITICAL_LOAD_UNSUPPORTED:" + element)
                continue
            try:
                frame = frames[element]
                check = frame["axes_global"]
                _checked(check is not None, "STORY_COLUMN_AXIS_UNBOUND")
                aligned = [name for name, u in zip(AXES, check[1:])
                           if isclose(abs(fsum(x*y for x, y in zip(u, axis_ref))), 1., rel_tol=0, abs_tol=1e-8)]
                _checked(len(aligned) == 1, "STORY_COUPLED_COLUMN_AXIS_UNSUPPORTED")
                chosen = aligned[0]
                known_ei = local["stiffness_and_euler"][axis]["selected_ei_nmm2"] if element == uid else None
                modifiers = modifier_rows.get(element)
                clear_mm = ln * 1000 if element == uid else None
                if element in credited:
                    _checked(modifiers is not None, "STORY_COLUMN_REVISED_OBJECT_MODIFIER_UNAVAILABLE")
                    clear_mm = 1000 * proven_clear_length_m(physical_lengths[element], element)
                elif element != uid:
                    _checked(modifiers is not None, "STORY_COLUMN_REVISED_OBJECT_MODIFIER_UNAVAILABLE")
                    offset = offsets.get(element)
                    _checked(offset is not None, "STORY_COLUMN_NATIVE_CLEAR_LENGTH_UNAVAILABLE")
                    offsets_m = [_number(offset[key], native=True) for key in ("OffsetI", "OffsetJ")]
                    _checked(min(offsets_m) >= 0, "STORY_COLUMN_NATIVE_OFFSETS_INVALID")
                    clear_mm = 1000 * (dist(frame_points[frame["point_i"]], frame_points[frame["point_j"]]) - fsum(offsets_m))
                    _checked(clear_mm > 0, "STORY_COLUMN_NATIVE_CLEAR_LENGTH_INVALID")
                end_refs = geometry.get("end_ratios", {}).get(element, {}).get(chosen) if element in credited else None
                row = _column_axis(block["columns"].get(element), element, chosen, frames, frame_points, adjacency,
                                   clear_mm, known_ei, modifiers, end_refs)
                material, section = materials.get(frame["material_name"]), sections.get(frame["section_name"])
                if element != uid:
                    _checked(material is not None and section is not None,
                             "STORY_COLUMN_NATIVE_MATERIAL_OR_SECTION_UNAVAILABLE")
                if material is not None:
                    native_e = _number(material["E1"], positive=True, native=True) / 1000
                    _checked(isclose(row["ec_mpa"], native_e, rel_tol=1e-6, abs_tol=0),
                             "STORY_COLUMN_NATIVE_ELASTIC_MODULUS_MISMATCH")
                if section is not None:
                    native_modifier = _number(section[f"I{chosen[-1]}Mod"], positive=True, native=True)
                    _checked(isclose(row["section_modifier"], native_modifier, rel_tol=1e-6, abs_tol=0),
                             "STORY_COLUMN_NATIVE_SECTION_MODIFIER_MISMATCH")
                cfg = local.get("adopted_second_order_basis", {}).get("member", {}).get("axes", {}).get(axis, {})
                if element == uid:
                    _checked(row["sway"] == cfg.get("sway"), "STORY_TARGET_SWAY_POLICY_MISMATCH")
                    supported[axis] = row
                if element in credited:
                    credited_rows.append(row)
                if row["restraint"]["basis"] == "CONDITIONAL_EXTERNAL_RESTRAINT_ASSUMPTION":
                    gaps.append("STORY_COLUMN_CONDITIONAL_SUPPORT_ONLY:" + element)
                else:
                    rows.append(row)
            except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError) as exc:
                reason = f"{exc}:{element}"
                gaps.append(reason)
                if element in credited:
                    credited_gaps.append(reason)
        nk = fsum(row["member_nk_kn"] for row in rows)
        result["axes"][axis] = {"status": "STORY_CRITICAL_LOAD_BOUND" if not gaps else "STORY_CRITICAL_LOAD_INCOMPLETE",
                                "expected_count": len(population), "evaluated_count": len(rows), "contributors": rows,
                                "supported_critical_load_sum_kn": nk, "target": supported.get(axis), "reasons": gaps}
        if not result["reasons"] and not gaps and nk > 0 and axis in supported:
            case_values = {name: {"nd_kn": v["supported_compression_kn"], "nk_kn": nk}
                           for name, v in result["cases"].items() if v["status"] == "STORY_COMPRESSION_BOUND"}
            if case_values:
                result["story_inputs"][axis] = {"k": supported[axis]["k"], "story_aggregates": case_values}
        if conditional is not None:
            credited_nk = fsum(row["member_nk_kn"] for row in credited_rows)
            axis_ready = not credited_gaps and len(credited_rows) == len(credited) and credited_nk > 0 and axis in supported
            conditional["axes"][axis] = {
                "status": "STORY_CONDITIONAL_FRAME_NK_BOUND" if axis_ready else "STORY_CONDITIONAL_FRAME_NK_INCOMPLETE",
                "expected_count": len(credited), "evaluated_count": len(credited_rows),
                "nk_kn": credited_nk, "contributors": credited_rows, "reasons": credited_gaps,
            }
            if axis_ready and not result["reasons"]:
                case_values = {name: {"nd_kn": row["nd_kn"], "nk_kn": credited_nk}
                               for name, row in conditional["cases"].items()
                               if row["status"] == "STORY_FRAME_COLUMN_COMPRESSION_BOUND"}
                if case_values:
                    conditional["story_inputs"][axis] = {"k": supported[axis]["k"], "story_aggregates": case_values}
    if conditional is not None:
        available = conditional["story_inputs"]
        ready = set(available) == set(AXES) and all(set(row["story_aggregates"]) == set(cases) for row in available.values())
        conditional["status"] = ("REVISED_CONDITIONAL_FRAME_BASIS_CALCULATED" if ready
                                 else "REVISED_CONDITIONAL_FRAME_BASIS_INCOMPLETE")
    complete = (set(result["story_inputs"]) == set(AXES) and
                all(set(v["story_aggregates"]) == set(cases) for v in result["story_inputs"].values()))
    result["status"] = "REVISED_STORY_BASIS_CALCULATED" if complete else "REVISED_STORY_BASIS_INCOMPLETE"
    return result
