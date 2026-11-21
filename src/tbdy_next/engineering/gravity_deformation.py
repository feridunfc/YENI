"""Reconstruct a qualified prismatic frame displacement representation.

CSI Analysis Reference, printed pp. 415–416, describes the P–Delta
representation as cubic bending plus linear shear between rigid ends.
The supported reconstruction uses a homogeneous Timoshenko interpolation
(constant shear strain, quadratic section rotation) on each flexible
interval. It exposes a numerical representation and its refinement error.
The joint rotations must be valid member-end rotations for this setup;
panel-zone, insertion or release transformations require separate support.
"""

from collections.abc import Mapping
from heapq import heappop, heappush
from itertools import count
from math import hypot, isclose, isfinite, sqrt, ulp

from ..column_engine.column_kinematics import COMPONENTS, COORDINATE_CONTRACT
from ..column_engine.kinematics_kernel import joint_chord_kinematics


SCHEMA = "tbdy.next.gravity-frame-kinematics.v1"
METHOD = "PRISMATIC_CUBIC_BENDING_LINEAR_SHEAR_WITH_RIGID_ENDS"
KINEMATICS_BASIS = "PRISMATIC_CENTROIDAL_UNRELEASED_GLOBAL_JOINTS"
UNVERIFIED = "UNVERIFIED_BETWEEN_NATIVE_JOINTS"
UNITS = {"translational": "m", "rotational": "rad", "stiffness": "kN,m"}
POSITION_TOL_M = 1e-6
SEARCH_TOL_MM = 1e-5
_MAX_SPLITS = 20000


def _item(value, fields, reason):
    if not isinstance(value, Mapping) or set(value) != set(fields):
        raise ValueError(reason)
    return value


def _number(value, reason):
    if type(value) not in (float, int) or not isfinite(value):
        raise ValueError(reason)
    return float(value)


def _pair(value, reason):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(reason)
    return [_number(item, reason) for item in value]


def _interpolate(a, b, t):
    return [(1 - t) * x + t * y for x, y in zip(a, b)]


def _split(controls, t):
    """Split a cubic Bézier piece without changing its representation."""
    a, b, c, d = controls
    ab, bc, cd = _interpolate(a, b, t), _interpolate(b, c, t), _interpolate(c, d, t)
    abc, bcd = _interpolate(ab, bc, t), _interpolate(bc, cd, t)
    middle = _interpolate(abc, bcd, t)
    return [a, ab, abc, middle], [middle, bcd, cd, d]


def _clip(piece, low, high):
    start, end, controls = piece
    if not start <= low < high <= end:
        raise ValueError("GRAVITY_DEFORMATION_PHYSICAL_INTERVAL_NOT_COVERED")
    if high < end:
        controls, _ = _split(controls, (high - start) / (end - start))
    if low > start:
        _, controls = _split(controls, (low - start) / (high - start))
    return [low, high, controls]


def _value(pieces, station):
    for start, end, controls in pieces:
        if start <= station <= end:
            return _split(controls, (station - start) / (end - start))[0][-1]
    return None


def _extremum(pieces, magnitude):
    """Bound the maximum by Bézier convex hulls and evaluated points.

    Both the vector norm and absolute component magnitudes are convex.
    Their maximum over any piece is bounded above by the largest control
    magnitude and below by evaluations. Subdivision closes that bracket.
    The returned location is the evaluated lower-bound point.
    """
    queue, order = [], count()
    best = -1.0
    station, vector = None, None

    def offer(x, v):
        nonlocal best, station, vector
        value = magnitude(v)
        if value > best or (value == best and x < station):
            best, station, vector = value, x, v

    def queue_piece(lo, hi, controls):
        unpadded = max(magnitude(v) for v in controls)
        # Retain a floating-point cushion in addition to the search gap.
        upper = unpadded + 128 * ulp(max(1.0, unpadded))
        heappush(queue, (-upper, next(order), lo, hi, controls))

    for low, high, controls in pieces:
        offer(low, controls[0])
        offer(high, controls[-1])
        queue_piece(low, high, controls)
    if not queue:
        raise ValueError("GRAVITY_DEFORMATION_PHYSICAL_INTERVAL_NOT_COVERED")
    subdivisions = 0
    while -queue[0][0] - best > SEARCH_TOL_MM:
        _, _, lo, hi, controls = heappop(queue)
        mid = (lo + hi) / 2
        subdivisions += 1
        if subdivisions > _MAX_SPLITS or not lo < mid < hi:
            raise ArithmeticError("GRAVITY_DEFORMATION_EXTREMUM_BOUND_NOT_RESOLVED")
        left, right = _split(controls, .5)
        offer(mid, left[-1])
        queue_piece(lo, mid, left)
        queue_piece(mid, hi, right)
    possible_locations = [(lo, hi) for negative_bound, _, lo, hi, _ in queue if -negative_bound >= best]
    return {"station_m": station, "signed_xy_mm": vector, "value_mm": best,
            "station_bracket_m": [min(lo for lo, _ in possible_locations),
                                  max(hi for _, hi in possible_locations)],
            "search_error_mm": max(0.0, -queue[0][0] - best)}


def _segment(element, section, movements, chord, global_low, input_error):
    i, j = element["i_joint"], element["j_joint"]
    start, end = (element[key][2] for key in ("i_xyz", "j_xyz"))
    length = end - start
    u_i, r_i = movements[i][:3], movements[i][3:]
    u_j, r_j = movements[j][:3], movements[j][3:]
    axes = section["axes_global"]
    # This validates the native triad and resolves right-hand-rule rotations.
    values = joint_chord_kinematics(axes, length, u_i, u_j, r_i, r_j)
    left = values["joint_i_u_local_m"][1:]
    right = values["joint_j_u_local_m"][1:]
    ra, rb = (values[f"joint_{end}_r_local_rad"] for end in ("i", "j"))
    slope_i, slope_j = [ra[2], -ra[1]], [rb[2], -rb[1]]
    offset_i, offset_j = section["offsets_m"]
    factor = section["rigid_end_factor"]
    rigid_i, rigid_j = offset_i * factor, offset_j * factor
    flexible = length - rigid_i - rigid_j
    face_i = [u + rigid_i * r for u, r in zip(left, slope_i)]
    face_j = [u - rigid_j * r for u, r in zip(right, slope_j)]
    # Local-2 translation bends about local-3. Local-3 bends about local-2.
    compliance = [1 / (1 + ga * flexible ** 2 / (12 * ei))
                  for ga, ei in zip(section["ga_kn"], reversed(section["ei_knm2"]))]
    shear = [c * ((b - a) / flexible - (ra + rb) / 2)
             for a, b, ra, rb, c in zip(face_i, face_j, slope_i, slope_j, compliance)]
    controls = [
        face_i,
        [v + flexible * (r + g) / 3 for v, r, g in zip(face_i, slope_i, shear)],
        [v - flexible * (r + g) / 3 for v, r, g in zip(face_j, slope_j, shear)],
        face_j,
    ]
    local_pieces = [[start + rigid_i, end - rigid_j, controls]]
    if rigid_i:
        local_pieces.insert(0, [start, start + rigid_i,
                            [_interpolate(left, face_i, t / 3) for t in range(4)]])
    if rigid_j:
        local_pieces.append([end - rigid_j, end,
                             [_interpolate(face_j, right, t / 3) for t in range(4)]])
    pieces = []
    for a, b, local_controls in local_pieces:
        # Subtract the original endpoint joint chord from each control.
        global_controls = []
        for index, (u2, u3) in enumerate(local_controls):
            z = a + (b - a) * index / 3
            global_controls.append([(axes[1][d] * u2 + axes[2][d] * u3 - chord(z)[d]) * 1000 for d in (0, 1)])
        pieces.append([a - global_low, b - global_low, global_controls])
    # Each control is affine in the native motion. Bound projection, rigid
    # offsets, derived shear and original-chord subtraction separately.
    eu, er = (sqrt(3) * item for item in input_error)
    ea, eb = eu + rigid_i * er, eu + rigid_j * er
    eg = max(compliance) * ((ea + eb) / flexible + er)
    precision_mm = 1000 * (sqrt(2) * (max(ea, eb) + flexible * (er + eg) / 3) + eu)
    return pieces, precision_mm


def _section(raw, expected, length, offsets):
    row = _item(raw, ("axes_global", "offsets_m", "rigid_end_factor", "kinematics_basis", "ei_knm2", "ga_kn"),
                "GRAVITY_DEFORMATION_ELEMENT_METADATA_UNBOUND")
    axes = row["axes_global"]
    if (row["kinematics_basis"] != KINEMATICS_BASIS or not isinstance(axes, (tuple, list)) or len(axes) != 3
            or not isinstance(axes[0], (tuple, list)) or len(axes[0]) != 3
            or any(not isclose(_number(a, "GRAVITY_DEFORMATION_LOCAL_AXIS_UNBOUND"), b, rel_tol=0, abs_tol=1e-8)
                   for a, b in zip(axes[0], (0, 0, 1)))):
        raise ValueError("GRAVITY_DEFORMATION_ELEMENT_TRANSFORMATION_UNSUPPORTED")
    observed = _pair(row["offsets_m"], "GRAVITY_DEFORMATION_OFFSETS_UNBOUND")
    factor = _number(row["rigid_end_factor"], "GRAVITY_DEFORMATION_RIGID_END_FACTOR_UNBOUND")
    if (min(observed) < 0 or sum(observed) >= length or not 0 <= factor <= 1
            or any(not isclose(a, b, rel_tol=0, abs_tol=POSITION_TOL_M) for a, b in zip(observed, offsets))):
        raise ValueError("GRAVITY_DEFORMATION_OFFSETS_INCONSISTENT")
    ei = _pair(row["ei_knm2"], "GRAVITY_DEFORMATION_EI_UNBOUND")
    ga = _pair(row["ga_kn"], "GRAVITY_DEFORMATION_SHEAR_STIFFNESS_UNBOUND")
    if min(ei) <= 0 or any(not isclose(a, b, rel_tol=1e-6) for a, b in zip(ei, expected)):
        raise ValueError("GRAVITY_DEFORMATION_EI_REVISION_MISMATCH")
    if min(ga) <= 0:
        raise ValueError("GRAVITY_DEFORMATION_POSITIVE_SHEAR_STIFFNESS_REQUIRED")
    return {**row, "offsets_m": observed, "rigid_end_factor": factor, "ei_knm2": ei, "ga_kn": ga}


def _recover_case(elements, sections, raw_joints, nodes, low, high, error):
    joints = _item(raw_joints, nodes, "GRAVITY_DEFORMATION_NATIVE_JOINT_POPULATION_MISMATCH")
    motions = {name: [_number(row[component], f"GRAVITY_DEFORMATION_{component.upper()}_UNBOUND")
                      for component in COMPONENTS]
               for name, raw in joints.items()
               for row in [_item(raw, COMPONENTS, "GRAVITY_DEFORMATION_SIX_DOF_REQUIRED")]}
    start, end = tuple(nodes.values())[0], tuple(nodes.values())[-1]
    a, b = (motions[name][:2] for name in (elements[0]["i_joint"], elements[-1]["j_joint"]))

    def chord(z):
        return _interpolate(a, b, (z - start) / (end - start))

    pieces, precision_mm = [], 0.0
    clear_length = high - low
    for element, section in zip(elements, sections):
        native_pieces, precision = _segment(element, section, motions, chord, low, error)
        precision_mm = max(precision_mm, precision)
        for piece in native_pieces:
            left, right = max(0.0, piece[0]), min(clear_length, piece[1])
            if left < right:
                pieces.append(_clip(piece, left, right))
    if not all(isfinite(v) for piece in pieces for xy in piece[2] for v in xy) or not isfinite(precision_mm):
        raise ArithmeticError("GRAVITY_DEFORMATION_ARITHMETIC_OVERFLOW")
    native = [{"joint_id": name, "station_m": z - low,
               "signed_xy_mm": [(u - c) * 1000 for u, c in zip(motions[name][:2], chord(z))]}
              for name, z in nodes.items() if low <= z <= high]
    return {"status": "RECOVERED", "pieces": pieces, "native_samples": native, "source_precision_bound_mm": precision_mm,
            "peak": _extremum(pieces, lambda vector: hypot(*vector))}


def recover_level(level, uid, elements, cases, low, high, stiffness_comparison):
    """Bind one refined model's named six-DOF results to its physical mesh."""
    record = level.get("kinematics")
    result = {"status": UNVERIFIED, "method": METHOD, "clear_length_m": high - low,
              "reference_chord": "ORIGINAL_ENDPOINT_JOINTS_GLOBAL_XY", "cases": {},
              "expected_case_count": len(cases), "recovered_case_count": 0}
    try:
        if record is None:
            raise ValueError("GRAVITY_DEFORMATION_KINEMATICS_UNAVAILABLE")
        _item(record, ("schema", "model_sha256", "analysis_generation", "case_step", "coordinate_contract",
                       "units", "translation_error_m", "rotation_error_rad", "members"),
              "GRAVITY_DEFORMATION_PACKET_INVALID")
        if (record["schema"] != SCHEMA or record["model_sha256"] != level["model_sha256"]
                or not isinstance(record["analysis_generation"], str) or not record["analysis_generation"]
                or record["analysis_generation"] != level.get("analysis_generation")):
            raise ValueError("GRAVITY_DEFORMATION_MODEL_OR_GENERATION_MISMATCH")
        step = record["case_step"]
        if (record["units"] != UNITS or record["coordinate_contract"] != COORDINATE_CONTRACT
                or not isinstance(step, list) or len(step) != 2 or step[0] != "Step"
                or _number(step[1], "GRAVITY_DEFORMATION_CASE_STEP_UNBOUND") != 1):
            raise ValueError("GRAVITY_DEFORMATION_CASE_STEP_AXES_OR_UNITS_UNBOUND")
        error = tuple(_number(record[field], "GRAVITY_DEFORMATION_SOURCE_PRECISION_UNBOUND")
                      for field in ("translation_error_m", "rotation_error_rad"))
        if min(error) < 0:
            raise ValueError("GRAVITY_DEFORMATION_SOURCE_PRECISION_UNBOUND")
        member = _item(record["members"][uid], ("joints", "elements"), "GRAVITY_DEFORMATION_MEMBER_KINEMATICS_UNBOUND")
        ids = [element["element"] for element in elements]
        sequence = [(element["i_joint"], element["i_xyz"][2]) for element in elements]
        sequence.append((elements[-1]["j_joint"], elements[-1]["j_xyz"][2]))
        nodes = dict(sequence)
        labels = [case["second"] for case in cases.values()]
        if (len(nodes) != len(sequence) or len(set(ids)) != len(ids) or len(set(labels)) != len(labels)
                or not labels or not low < high or not sequence[0][1] <= low < high <= sequence[-1][1]):
            raise ValueError("GRAVITY_DEFORMATION_MESH_IDENTITIES_OR_FACES_INCONSISTENT")
        for element, ((_, a), (expected_end, b)) in zip(elements, zip(sequence, sequence[1:])):
            if (element["j_joint"] != expected_end or element["j_xyz"][2] != b or a >= b
                    or element["i_xyz"][:2] != element["j_xyz"][:2]):
                raise ValueError("GRAVITY_DEFORMATION_MESH_IDENTITIES_OR_FACES_INCONSISTENT")
        meta = _item(member["elements"], ids, "GRAVITY_DEFORMATION_NATIVE_ELEMENT_POPULATION_MISMATCH")
        ei = [stiffness_comparison[axis]["etabs_ei_nmm2"] / 1e9 for axis in ("M2", "M3")]
        sections = [
            _section(meta[element["element"]], ei, b - a, (max(0.0, low - a), max(0.0, b - high)))
            for element, ((_, a), (_, b)) in zip(elements, zip(sequence, sequence[1:]))
        ]
        if not isinstance(member["joints"], Mapping) or set(member["joints"]) - set(labels):
            raise ValueError("GRAVITY_DEFORMATION_CASE_POPULATION_MISMATCH")
        for name, label in zip(cases, labels):
            try:
                row = _recover_case(elements, sections, member["joints"].get(label), nodes, low, high, error)
            except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
                row = {"status": UNVERIFIED, "reason": str(exc)}
            result["cases"][name] = {**row, "output_case": label}
        result["recovered_case_count"] = sum(row["status"] == "RECOVERED" for row in result["cases"].values())
        if result["recovered_case_count"] == len(cases):
            result["status"] = "FULL_SPAN_RECOVERED"
        result.update(model_sha256=record["model_sha256"], analysis_generation=record["analysis_generation"])
    except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
        result["reason"] = str(exc)
        result["cases"] = {name: {"status": UNVERIFIED, "reason": result["reason"], "output_case": case["second"]}
                           for name, case in cases.items()}
    return result


def _difference(before, after, length):
    knots = sorted({0.0, length, *(z for p in [*before, *after] for z in p[:2])})
    result = []
    for low, high in zip(knots, knots[1:]):
        a, b = (_clip(next(p for p in field if p[0] <= low and high <= p[1]), low, high)[2]
                for field in (before, after))
        result.append([low, high, [[y - x for x, y in zip(v, w)] for v, w in zip(a, b)]])
    return result


def _compare_case(a, b, length, limit):
    field = _difference(a["pieces"], b["pieces"], length)
    max_diff = _extremum(field, lambda vector: hypot(*vector))
    axes = {name: _extremum(field, lambda vector: abs(vector[i])) for i, name in enumerate(("X", "Y"))}
    # Extra finer-mesh joints are deliberately withheld from the coarser fit.
    original = [row["station_m"] for row in a["native_samples"]]
    residuals = []
    for row in b["native_samples"]:
        x = row["station_m"]
        if 0 < x < length and all(abs(x - station) > POSITION_TOL_M for station in original):
            prediction = _value(a["pieces"], x)
            delta = [y - z for y, z in zip(row["signed_xy_mm"], prediction)]
            residuals.append({**row, "prediction_xy_mm": prediction, "difference_xy_mm": delta, "norm_mm": hypot(*delta)})
    if not residuals:
        raise ValueError("GRAVITY_DEFORMATION_WITHHELD_FINE_JOINTS_UNAVAILABLE")
    held_out = max(residuals, key=lambda row: row["norm_mm"])
    budget = {
        "source_precision_mm": a["source_precision_bound_mm"] + b["source_precision_bound_mm"],
        "withheld_joint_recovery_discretization_mm": held_out["norm_mm"],
        "mesh_vector_difference_mm": max_diff["value_mm"],
        "extremum_search_mm": max(max_diff["search_error_mm"],
                                  a["peak"]["search_error_mm"] + b["peak"]["search_error_mm"]),
        "tolerance_mm": limit,
    }
    budget["total_mm"] = sum(value for key, value in budget.items() if key != "tolerance_mm")
    if not isfinite(budget["total_mm"]):
        raise ArithmeticError("GRAVITY_DEFORMATION_ERROR_BUDGET_OVERFLOW")
    return {"status": "WITHIN_NUMERICAL_TOLERANCE" if budget["total_mm"] <= limit else "OUTSIDE_NUMERICAL_TOLERANCE",
            "before_peak": a["peak"], "after_peak": b["peak"],
            "peak_change_mm": b["peak"]["value_mm"] - a["peak"]["value_mm"],
            "peak_station_change_m": b["peak"]["station_m"] - a["peak"]["station_m"],
            "max_vector_difference": max_diff, "max_component_differences": axes,
            "withheld_joint_count": len(residuals), "withheld_joint_max": held_out, "error_budget": budget}


def compare_recovered(before, after, tolerance_mm):
    """Compare two piecewise fields over the full common physical interval."""
    result = {"status": UNVERIFIED, "within_tolerance": None, "method": METHOD, "tolerance_mm": tolerance_mm, "cases": {},
              "reference_chord": "ORIGINAL_ENDPOINT_JOINTS_GLOBAL_XY"}
    if before is None or after is None:
        return result
    a, b = before["cases"], after["cases"]
    if not a or a.keys() != b.keys() or before["clear_length_m"] != after["clear_length_m"]:
        return {**result, "reason": "GRAVITY_DEFORMATION_COMMON_PHYSICAL_SCOPE_UNBOUND"}
    length = after["clear_length_m"]
    result["clear_length_m"] = length
    for name in a:
        if a[name]["status"] != "RECOVERED" or b[name]["status"] != "RECOVERED":
            result["cases"][name] = {"status": UNVERIFIED, "reason": a[name].get("reason") or b[name].get("reason")}
            continue
        try:
            result["cases"][name] = _compare_case(a[name], b[name], length, tolerance_mm)
        except (ArithmeticError, KeyError, StopIteration, TypeError, ValueError) as exc:
            result["cases"][name] = {"status": UNVERIFIED, "reason": str(exc)}
    statuses = {row["status"] for row in result["cases"].values()}
    if "OUTSIDE_NUMERICAL_TOLERANCE" in statuses:
        result.update(status="OUTSIDE_NUMERICAL_TOLERANCE", within_tolerance=False)
    elif statuses == {"WITHIN_NUMERICAL_TOLERANCE"}:
        result.update(status="WITHIN_NUMERICAL_TOLERANCE", within_tolerance=True)
    return result
