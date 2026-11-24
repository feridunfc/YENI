"""R10 live-source bridge: joint topology, 7.5 limits, SCWB and column shear/confinement.

Pure deterministic projection over the SAME locked LIVE_ETABS run receipts
(`geometry_capture`, `vs05_delta_source` / `vs06_b1_geometry_source`,
`column_axial`, `column_pmm`, `next_capture`). Reuses the existing `column_engine`
formula owners (`joint_kernel`, `scwb_kernel`, `transverse_kernel`,
`joint_moment_signs`, `csi_geometry`, `ts500_column`) with zero formula duplication.

Never substitutes ETABS required beam steel or `IsDesigned=Yes` column templates
for selected/as-built reinforcement, and never emits PASS or READY.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
import math
from typing import Any, Mapping, MutableMapping, Sequence

from .frame_geometry import (
    _axis_angle_deg, _csi_frame_axes, _dot, _float_or_none, _normalize, build_frame_catalog as _build_frame_catalog,
)
from ..column_engine.csi_geometry import (
    physical_column_side_at_joint, physical_shear_axis,
)
from ..column_engine.joint_kernel import (
    beam_steel_tension_kn, centered_joint_limit, joint_shear_equilibrium_kn,
    joint_transverse_reference, width_reference,
)
from ..column_engine.joint_moment_signs import moment_sign_mapping
from ..column_engine.native_archive import BankError, finite
from ..column_engine.scwb_kernel import (
    JointCase,
    MemberMomentCapacity,
    column_axis_capacity,
    column_axis_interval_bound,
    compute_scwb_joint_result,
)
from ..column_engine.section_capacity import Section, perimeter
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.story_alpha import evaluate_story_alpha_reference
from ..column_engine.transverse_kernel import confinement_axial_threshold, confinement_reference, shear_reference
from ..column_engine.ts500_column import apply_minimum_eccentricity
from ..etabs_geometry import PHYSICAL_FACE_TABLES, capture_point_restraints
from ..etabs_source_gateway_windows import field_schema, read_table, return_code
from ..frame_force_capture import ForceSelectionRestoreError, capture_frame_forces

SCHEMA = "tbdy.next.column-r10-live.v1"
BEAM_REINFORCING = "Frame Section Property Definitions - Concrete Beam Reinforcing"
END_OFFSETS = "Frame Assignments - End Length Offsets"
RELEASES = "Frame Assignments - Releases and Partial Fixity"
BEAM_DESIGN_SUMMARY = "Concrete Beam Design Summary - TS 500-2000(R2018)"
ANALYSIS_FRAME_ELEMENTS = "Objects and Elements - Frames"
ANALYSIS_JOINT_ELEMENTS = "Objects and Elements - Joints"
ANALYSIS_JOINT_COORDINATE_SCHEMA = "tbdy.next.etabs-analysis-joint-coordinates.v1"
FRAME_OUTPUT_STATIONS = "Frame Assignments - Output Stations"
_GEOMETRY_TOL = 1e-8
_SUPPORTED_TYPES = {"Beam", "Column"}


@dataclass(frozen=True)
class SelectedColumnCage:
    """Couple a candidate and its numerical section for this run only."""

    selection: Mapping[str, Any]
    section: Section
    input_sha256: str | None = None
    candidate_sha256: str | None = None


def _capture_analysis_joint_coordinates(
    sap, frame_table: Mapping[str, Any] | None, column_members: tuple[str, ...],
) -> dict[str, Any] | None:
    """Read native coordinates for the joints of requested meshed column objects."""
    if not column_members or not frame_table or frame_table.get("status") != "CAPTURED":
        return None
    targets = set(column_members)
    by_object = defaultdict(list)
    for row in frame_table.get("rows", ()):
        if row.get("ObjType") == "Frame" and row.get("ObjName") in targets:
            by_object[row["ObjName"]].append(row)
    joint_ids = set()
    for rows in by_object.values():
        elm_names = [row.get("ElmName") for row in rows]
        joints = [row.get(key) for row in rows for key in ("ElmJtI", "ElmJtJ")]
        if (len(rows) > 1 and len(set(elm_names)) == len(rows)
                and all(isinstance(name, str) and name and name == name.strip()
                        for name in elm_names + joints)):
            joint_ids.update(joints)
    if not joint_ids:
        return None

    result = {"schema": ANALYSIS_JOINT_COORDINATE_SCHEMA, "coordinate_system": "Global", "units": "m",
              "coordinates": {}, "errors": {}}
    try:
        get_coordinates = sap.PointElm.GetCoordCartesian
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"[:300]
        result["errors"] = dict.fromkeys(sorted(joint_ids), reason)
        return result

    for name in sorted(joint_ids):
        try:
            # ETABS v23 exposes three in/out doubles, followed by its return code.
            raw = get_coordinates(name, 0.0, 0.0, 0.0, "Global")
            if not isinstance(raw, (list, tuple)) or len(raw) != 4:
                raise ValueError("POINT_ELM_COORDINATES_ABI_UNRECOGNIZED")
            code = return_code(raw, "PointElm.GetCoordCartesian")
            if code != 0:
                raise ValueError(f"POINT_ELM_COORDINATES_RETURN_CODE:{code}")
            xyz = raw[:3]
            if any(type(value) not in (int, float) or not math.isfinite(value) for value in xyz):
                raise ValueError("POINT_ELM_COORDINATES_NONFINITE_OR_INVALID")
            result["coordinates"][name] = [float(value) for value in xyz]
        except Exception as exc:
            result["errors"][name] = f"{type(exc).__name__}: {exc}"[:300]
    return result


def capture_r10_sources(
    sap,
    *,
    beam_members: tuple[str, ...] = (),
    combinations: tuple[str, ...] = (),
    column_members: tuple[str, ...] = (),
    column_joint_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Read optional R10 and PMM source evidence on the connected SapModel."""
    captured: dict[str, Any] = {
        "schema": "tbdy.next.r10-live-source.v1",
        "table_reads": {},
        "table_errors": {},
    }
    try:
        captured["model_locked_before"] = sap.GetModelIsLocked()
        captured["units_before"] = sap.GetPresentUnits()
        if captured["model_locked_before"] is not True or captured["units_before"] != 6:
            raise ValueError("R10_CAPTURE_REQUIRES_LOCKED_KN_M_C")
        db = sap.DatabaseTables
        for table_key in (BEAM_REINFORCING, END_OFFSETS, RELEASES, BEAM_DESIGN_SUMMARY,
                          ANALYSIS_FRAME_ELEMENTS, ANALYSIS_JOINT_ELEMENTS, FRAME_OUTPUT_STATIONS,
                          *PHYSICAL_FACE_TABLES):
            try:
                record = read_table(db, table_key)
                record["field_metadata"] = field_schema(db, table_key)
                captured["table_reads"][table_key] = record
            except Exception as exc:
                captured["table_errors"][table_key] = f"{type(exc).__name__}: {exc}"[:300]
        coordinates = _capture_analysis_joint_coordinates(
            sap, captured["table_reads"].get(ANALYSIS_FRAME_ELEMENTS), column_members,
        )
        if coordinates is not None:
            captured["analysis_joint_coordinates"] = coordinates
        if column_joint_ids:
            captured["point_restraints"] = capture_point_restraints(sap, column_joint_ids)
        if beam_members and combinations:
            try:
                captured["beam_force_source"] = capture_frame_forces(
                    sap, members=tuple(beam_members), combinations=tuple(combinations),
                )
            except ForceSelectionRestoreError:
                raise
            except Exception as exc:
                captured["beam_force_source_error"] = f"{type(exc).__name__}: {exc}"[:400]
        captured["model_locked_after"] = sap.GetModelIsLocked()
        captured["units_after"] = sap.GetPresentUnits()
    except ForceSelectionRestoreError:
        raise
    except Exception as exc:
        captured["error"] = f"{type(exc).__name__}: {exc}"[:400]
    return captured


def member_local_axis_angle_deg(source: Mapping[str, Any], member_id: str | None) -> float | None:
    """Return ETABS AxisAngle (deg) from captured FRAME_ASSIGNMENTS when available."""
    if not member_id:
        return None
    rows = (((source.get("geometry_capture") or {}).get("tables") or {}).get("FRAME_ASSIGNMENTS") or {}).get("rows") or []
    matches = [row for row in rows if row.get("UniqueName") == member_id]
    if len(matches) != 1:
        return None
    return _axis_angle_deg(matches[0])


def _parallel(a: list[float], b: list[float]) -> bool:
    return abs(abs(_dot(a, b)) - 1.0) <= _GEOMETRY_TOL


def _materials_fck(extra: Mapping[str, Any] | None) -> dict[str, float]:
    for check in (extra or {}).get("checks", ()):
        if check.get("check_id") == "concrete_fck_25":
            return {
                row["material_name"]: float(row["fck_mpa"])
                for row in check.get("items", ())
                if row.get("material_name") and row.get("fck_mpa") is not None
            }
    return {}


def _evaluate_joint_end(
    column: dict[str, Any],
    end: str,
    frames: dict[str, dict[str, Any]],
    points: dict[str, list[float]],
    adjacency: dict[str, list[dict[str, Any]]],
    fck_map: dict[str, float],
) -> dict[str, Any]:
    pt_id = column["point_i"] if end == "I" else column["point_j"]
    row: dict[str, Any] = {
        "member_id": column["frame_id"],
        "label": column["label"],
        "story": column["story"],
        "end": end,
        "point_id": pt_id,
        "section_name": column["section_name"],
        "status": "BLOCKED_INPUTS",
        "reason": None,
        "enclosure_scenario": None,
        "faces": {},
        "missing_faces": [],
        "narrow_faces": [],
        "axes": [],
        "scwb_status": "NOT_PROVEN",
        "ve_status": "NOT_PROVEN",
        "formal_compliance": "NOT_PROVEN",
    }
    if not points or pt_id not in points:
        row["reason"] = "POINT_COORDINATES_NOT_CAPTURED"
        return row
    col_axes = column.get("axes_global")
    col_dims = column.get("dims")
    if col_axes is None or col_dims is None:
        row["reason"] = "COLUMN_GEOMETRY_OR_AXES_UNVERIFIED"
        return row
    if not _parallel(col_axes[0], [0.0, 0.0, 1.0]) or any(abs(a[2]) > _GEOMETRY_TOL for a in col_axes[1:]):
        row["reason"] = "JOINT_VERTICAL_COLUMN_SCENARIO_NOT_BOUND"
        return row

    incident = adjacency.get(pt_id, [])
    if any(item["type"] not in _SUPPORTED_TYPES for item in incident):
        row["reason"] = "JOINT_OTHER_INCIDENT_FRAME_NOT_CLASSIFIED"
        return row

    faces: dict[str, dict[str, Any] | None] = {"2+": None, "2-": None, "3+": None, "3-": None}
    for item in incident:
        if item["type"] != "Beam":
            continue
        beam = frames[item["frame_id"]]
        b_axes = beam.get("axes_global")
        b_dims = beam.get("dims")
        if b_axes is None or b_dims is None:
            row["reason"] = f"JOINT_BEAM_GEOMETRY_NOT_BOUND:{beam['frame_id']}"
            return row
        other_pt = beam["point_j"] if beam["point_i"] == pt_id else beam["point_i"]
        direction = _normalize([b - a for a, b in zip(points[other_pt], points[pt_id])], "beam_dir")
        matches = [idx for idx in (1, 2) if _parallel(direction, col_axes[idx])]
        if len(matches) != 1 or abs(direction[2]) > _GEOMETRY_TOL:
            row["reason"] = "JOINT_ORTHOGONAL_HORIZONTAL_BEAM_SCENARIO_NOT_BOUND"
            return row
        axis_idx = matches[0]
        face_key = str(axis_idx + 1) + ("+" if _dot(direction, col_axes[axis_idx]) > 0 else "-")
        if faces[face_key] is not None:
            row["reason"] = "JOINT_MULTIPLE_BEAMS_ON_ONE_FACE"
            return row
        perp = col_axes[3 - axis_idx]
        width_axes = [j for j in (1, 2) if _parallel(b_axes[j], perp)]
        if len(width_axes) != 1:
            row["reason"] = "JOINT_BEAM_SECTION_ROLL_NOT_ORTHOGONAL"
            return row
        bw = b_dims.local2_extent_mm if width_axes[0] == 1 else b_dims.local3_extent_mm
        col_transverse_w = col_dims.local3_extent_mm if axis_idx == 1 else col_dims.local2_extent_mm
        faces[face_key] = {
            "frame_id": beam["frame_id"],
            "label": beam["label"],
            "native_end": item["end"],
            "face": face_key,
            "beam_section": beam["section_name"],
            "beam_width_mm": bw,
            "column_transverse_width_mm": col_transverse_w,
            "width_ratio": bw / col_transverse_w,
            "width_reference_met": width_reference(bw, col_transverse_w),
        }

    row["faces"] = faces
    row["missing_faces"] = [f for f, v in faces.items() if v is None]
    row["narrow_faces"] = [f for f, v in faces.items() if v is not None and not v["width_reference_met"]]
    if all(v is None for v in faces.values()):
        row["status"] = "NO_RECORDED_BEAM_AT_NODE"
        return row

    fck = fck_map.get(column.get("material_name") or "")
    if fck is None or fck <= 0:
        row["reason"] = "JOINT_CONCRETE_FCK_NOT_VERIFIED"
        return row

    enclosure = "ENCLOSED" if not row["missing_faces"] and not row["narrow_faces"] else "UNENCLOSED"
    row["enclosure_scenario"] = enclosure
    row["fck_mpa"] = fck
    row["status"] = "JOINT_GEOMETRIC_REFERENCES_CALCULATED"
    for axis, b_mm, h_mm in (
        (2, col_dims.local3_extent_mm, col_dims.local2_extent_mm),
        (3, col_dims.local2_extent_mm, col_dims.local3_extent_mm),
    ):
        widths = [v["beam_width_mm"] for f, v in faces.items() if f[0] == str(axis) and v is not None]
        calc = (
            centered_joint_limit(
                column_width_mm=b_mm,
                column_depth_mm=h_mm,
                beam_widths_mm=widths,
                fck_mpa=fck,
                enclosure=enclosure,
            )
            if widths
            else None
        )
        row["axes"].append({
            "axis": f"V{axis}",
            "status": "GEOMETRIC_REFERENCE_ONLY" if calc is not None else "NO_RECORDED_BEAM_IN_DIRECTION",
            "calculation": calc,
        })
    return row


def _beam_moment_capacity_for_sign(
    beam_id: str,
    beam_entry: Mapping[str, Any] | None,
    bend: str,
    b_axes: list[list[float]],
    direction: str,
    rot_sign: int,
    ctx: JointCase,
    *,
    diameter_mm: int | str = 20,
) -> MemberMomentCapacity:
    """Resolve signed N=0 beam scenario or engineer-selected capacity for one joint rotation sign."""
    if not beam_entry or beam_entry.get("status") == "BEAM_INPUTS_INCOMPLETE":
        return MemberMomentCapacity(
            ctx, beam_id, bend, "BEAM", None, None, reason="ACTUAL_OR_SELECTED_BEAM_REINFORCEMENT_NOT_BOUND",
        )
    end_data = (beam_entry.get("ends") or {}).get(bend) or {}
    if end_data.get("released_for_bending"):
        return MemberMomentCapacity(
            ctx, beam_id, bend, "BEAM", None, None, reason="BEAM_END_MOMENT_RELEASED",
        )
    if diameter_mm == "ENGINEER_SELECTED":
        cand = end_data.get("engineer_selection") or {}
        src_tag = f"live-beam-{beam_id}-{bend}-engineer-selected-N0"
    else:
        cand = (end_data.get("candidates") or {}).get(str(diameter_mm)) or {}
        src_tag = f"live-beam-{beam_id}-{bend}-phi{diameter_mm}-N0"
    cap = cand.get("capacity") or {}
    if cap.get("status") != "BEAM_CAPACITY_REFERENCE":
        reason = cand.get("reason") or end_data.get("reason") or "ACTUAL_OR_SELECTED_BEAM_REINFORCEMENT_NOT_BOUND"
        return MemberMomentCapacity(ctx, beam_id, bend, "BEAM", None, None, reason=reason)
    try:
        mapping = moment_sign_mapping(b_axes, bend, direction, rot_sign, "M3")
    except BankError as exc:
        return MemberMomentCapacity(ctx, beam_id, bend, "BEAM", None, None, reason=str(exc))
    sign = mapping["local_internal_moment_sign"]
    key = "positive_m3_knm" if sign == 1 else "negative_m3_knm"
    val = cap.get(key)
    pts = [p for p in cap.get("points") or () if p.get("rotation_sign") == sign]
    tol = float(pts[0]["tolerance_knm"] or 0.0) if pts and pts[0].get("tolerance_knm") is not None else 0.0
    if val is None or sign * float(val) <= 0:
        return MemberMomentCapacity(ctx, beam_id, bend, "BEAM", None, None, reason="BEAM_SIGNED_CAPACITY_INVALID")
    return MemberMomentCapacity(
        ctx, beam_id, bend, "BEAM", abs(float(val)), src_tag, tolerance_knm=tol,
    )


def _scwb_sign_evaluation(
    *,
    run_id: str,
    src_hash: str,
    pt_id: str,
    direction: str,
    combo: str,
    rot_sign: int,
    expected_cols: list[tuple[str, str]],
    expected_beams: list[tuple[str, str]],
    col_caps_base: list[MemberMomentCapacity],
    dir_beams: list[tuple[dict[str, Any], str]],
    beam_by_id: Mapping[str, Mapping[str, Any]],
    diameter_mm: int | str,
) -> dict[str, Any]:
    ctx_tag = "LIVE_ENGINEER_SELECTED_BEAM_N0" if diameter_mm == "ENGINEER_SELECTED" else f"LIVE_SCENARIO_PHI{diameter_mm}_N0"
    ctx_sign = JointCase(run_id, src_hash, pt_id, direction, rot_sign, combo, ctx_tag)
    col_caps = [replace(c, context=ctx_sign) for c in col_caps_base]
    beam_caps = [
        _beam_moment_capacity_for_sign(
            b["frame_id"], beam_by_id.get(b["frame_id"]), bend, b["axes_global"],
            direction, rot_sign, ctx_sign, diameter_mm=diameter_mm,
        )
        for b, bend in dir_beams
    ]
    agg = compute_scwb_joint_result(ctx_sign, expected_cols, expected_beams, col_caps + beam_caps)
    resolved_cols = [c for c in col_caps if c.capacity_knm is not None]
    mrc_sum = math.fsum(c.capacity_knm for c in resolved_cols) if len(resolved_cols) == len(col_caps) else None
    return {
        "output_case": combo,
        "rotation_sign": rot_sign,
        "beam_diameter_mm": diameter_mm,
        "sum_mrc_reference_knm": mrc_sum,
        "sum_mrb_reference_knm": agg["sum_mrb_reference_knm"],
        "required_mrc_reference_knm": agg["required_mrc_reference_knm"],
        "normalized_reference_ratio": agg["normalized_reference_ratio"],
        "raw_capacity_ratio": agg["raw_capacity_ratio"],
        "reference_satisfied": agg["reference_satisfied"],
        "status": agg["status"],
        "missing_capacities": agg["missing_capacities"],
    }


def _selected_scwb_interval(joint_id, direction, decision, plan, columns, beams, beam_ends,
                            directional_beams, beam_results, selected_sections, run_id):
    """Sufficient Eq. 7.3 check over complete assigned Nd intervals, for each sway sign."""
    names = decision["seismic_combinations"]
    result = {"method": "SELECTED_PRINCIPAL_SECTION_CONTINUOUS_ND_BOUND_V1",
              "input_sha256": decision["input_sha256"], "expected_checks": 2 * len(names),
              "status": "AXIAL_INTERVAL_UNRESOLVED", "sufficient": None, "cases": [], "reasons": [],
              "beam_basis": "SELECTED_BEAM_END_RESISTANCE_AT_N0", "formal_compliance": "NOT_PROVEN"}
    joint = (plan or {}).get("joints", {}).get(joint_id) or {}
    roster = joint.get("beam_ends") or []
    expected_beams = {(row["member_id"], row["end"]) for row in roster}
    ends = {end["member_id"]: end for end in decision["column_ends"]}
    ids = {col["frame_id"] for col in columns}
    if (not plan or not names or len(names) != len(set(names)) or not decision["input_sha256"]
            or plan.get("input_sha256") != decision["input_sha256"] or direction not in ("X", "Y")
            or joint.get("execution_allowed") is not True or len(ids) != 2 or ids != set(ends)
            or {end["physical_side"] for end in ends.values()} != {"UPPER", "LOWER"}
            or any(set(end.get("seismic_nd_intervals_kn", ())) != set(names) for end in ends.values())
            or len(expected_beams) != len(roster) or len(expected_beams) != len(beams)
            or ids != set(joint.get("column_ids", ())) or not ids <= selected_sections.keys()
            or expected_beams != {(b["frame_id"], beam_ends[b["frame_id"]]["end"]) for b in beams}):
        result["reasons"].append("SCWB_SELECTED_SECTION_OR_JOINT_SCOPE_UNBOUND")
        return result
    x, y = [1., 0., 0.], [0., 1., 0.]
    rot_axis = y if direction == "X" else [-1., 0., 0.]
    shear_axis = x if direction == "X" else y
    axes = {}
    try:
        for b in beams:
            base = b.get("axes_global")
            if not base or not any(_parallel(base[0], axis) for axis in (x, y)):
                raise BankError("SCWB_SKEW_OR_UNBOUND_BEAM_AXIS")
        for col in columns:
            uid = col["frame_id"]
            base = col.get("axes_global")
            mapped = [i for i in (1, 2) if base and _parallel(base[i], rot_axis)]
            if len(mapped) != 1 or not any(_parallel(base[i], shear_axis) for i in (1, 2)):
                raise BankError("SCWB_COLUMN_GLOBAL_AXIS_NOT_PRINCIPAL")
            axis = "M" + str(mapped[0] + 1)
            for sign in (-1, 1):
                moment_sign_mapping(base, ends[uid]["end"], direction, sign, axis)
            axes[uid] = axis
        for b, end in directional_beams:
            recorded = (beam_results[b["frame_id"]]["ends"] or {})[end]
            capacity = (recorded.get("engineer_selection") or {}).get("capacity") or {}
            points = capacity.get("points") or []
            if (recorded.get("released_for_bending") is not False or capacity.get("axial_force_scenario_n") != 0
                    or len(points) != 2 or {pt["rotation_sign"] for pt in points} != {-1, 1}
                    or any(finite(pt["tolerance_knm"], "beam_moment_tolerance") <= 0 for pt in points)):
                raise BankError("SCWB_SELECTED_SIGNED_BEAM_RESISTANCES_UNBOUND")
    except (ValueError, KeyError, ArithmeticError, TypeError) as exc:
        result["reasons"].append(str(exc))
        return result
    col_ids = sorted((uid, ends[uid]["end"]) for uid in ids)
    beam_ids = [(b["frame_id"], end) for b, end in directional_beams]
    for name in names:
        bounds = {}
        case = {"combination": name, "columns": bounds, "sways": []}
        result["cases"].append(case)
        try:
            for uid, end in col_ids:
                interval = ends[uid]["seismic_nd_intervals_kn"][name]
                bound = column_axis_interval_bound(selected_sections[uid], axes[uid], *interval)
                bounds[uid] = {**bound, "end": end, "configured_cut": ends[uid]["configured_cut"]}
                if bound["mr_lower_bound_knm"] <= 0:
                    raise BankError("SCWB_POSITIVE_RESISTANCE_BOUND_UNAVAILABLE")
            for sign in (-1, 1):
                ctx = JointCase(run_id, decision["input_sha256"], joint_id, direction, sign, name,
                                "SELECTED_CAGE_AXIAL_INTERVAL", "Axial interval", None)
                caps = [MemberMomentCapacity(ctx, uid, end, "COLUMN", bounds[uid]["mr_lower_bound_knm"],
                                             "SELECTED_SECTION_ND_INTERVAL") for uid, end in col_ids]
                caps.extend(_beam_moment_capacity_for_sign(b["frame_id"], beam_results[b["frame_id"]], end,
                            b["axes_global"], direction, sign, ctx, diameter_mm="ENGINEER_SELECTED")
                            for b, end in directional_beams)
                check = compute_scwb_joint_result(ctx, col_ids, beam_ids, caps)
                if check["missing_capacities"] or check["comparison_tolerance_knm"] is None:
                    raise BankError("SCWB_SELECTED_CAPACITY_SUM_UNBOUND")
                required = check["required_mrc_reference_knm"] + check["comparison_tolerance_knm"]
                lower = check["sum_mrc_reference_knm"]
                case["sways"].append({"rotation_sign": sign, "column_sum_lower_knm": lower,
                                      "required_sum_upper_knm": required, "ratio_lower": lower / required,
                                      "beam_ids": [uid for uid, _ in beam_ids],
                                      "sufficient": True if check["reference_satisfied"] is True else None})
        except (ValueError, KeyError, ArithmeticError, TypeError) as exc:
            result["reasons"].append(name + ":" + str(exc))
    checks = [(case["combination"], row) for case in result["cases"] for row in case["sways"]]
    result["evaluated_checks"] = len(checks)
    if not result["reasons"] and len(checks) == result["expected_checks"]:
        name, governing = min(checks, key=lambda item: item[1]["ratio_lower"])
        result.update(minimum_ratio_lower=governing["ratio_lower"], governing_combination=name,
                      governing_sway=governing["rotation_sign"], column_sum_lower_knm=governing["column_sum_lower_knm"],
                      required_sum_upper_knm=governing["required_sum_upper_knm"])
        if all(row["sufficient"] is True for _, row in checks):
            result.update(status="SCWB_EQ_7_3_INTERVAL_SUFFICIENT", sufficient=True)
        else:
            result.update(status="SCWB_AXIAL_INTERVAL_BOUND_INCONCLUSIVE")
    return result


def _evaluate_scwb_at_joint_ends(
    uid: str,
    frames: dict[str, dict[str, Any]],
    points: dict[str, list[float]],
    adjacency: dict[str, list[dict[str, Any]]],
    source: Mapping[str, Any],
    axial: Mapping[str, Any],
    pmm: Mapping[str, Any],
    geometry: Mapping[str, Any],
    beam_live: Mapping[str, Any] | None = None,
    engineer_col_section: Any = None,
    engineer_col_sections: Mapping[str, Any] | None = None,
    col_sections_cache: dict[str, tuple[Any, dict]] | None = None,
    dependency_plan: Mapping[str, Any] | None = None,
    low_axial_by_joint: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build TBDY 7.3.6 / CHK-125 SCWB reference summaries at I/J joints of `uid`."""
    from .column_axial import _columns
    from .column_pmm_section import build_pmm_section

    feature = source.get("column_axial") or {}
    pmm_sec_source = feature.get("pmm_section_source") or {}
    prefs = feature.get("design_preferences") or {}
    force_rowsets = (feature.get("force_source") or {}).get("rowsets") or {}
    static_combos = [
        c["name"]
        for c in (axial.get("combination_plan") or {}).get("combinations", ())
        if c.get("force_semantics") == "STATIC_SIGNED_VECTOR"
    ]
    if uid not in frames or not points:
        return []
    if not low_axial_by_joint and (not static_combos or not force_rowsets or not pmm_sec_source):
        return []

    beam_by_id = {b["member_id"]: b for b in (beam_live or {}).get("beams") or ()}
    beam_sel_active = bool((beam_live or {}).get("beam_selection_policy"))
    eng_secs = dict(engineer_col_sections or {})
    if engineer_col_section is not None and uid not in eng_secs:
        eng_secs[uid] = engineer_col_section
    geom_by_id = {row["element_id"]: row for row in _columns(geometry)}
    axial_by_id = {row["element_id"]: row for row in axial.get("columns", ())}
    cache = col_sections_cache if col_sections_cache is not None else {}
    run_id = str((feature.get("request") or {}).get("base_run_id") or "LIVE_RUN")
    src_hash = str((feature.get("request") or {}).get("base_input_sha256") or "live_capture")
    target_col = frames[uid]
    joint_summaries: list[dict[str, Any]] = []

    for end, pt_id in (("I", target_col["point_i"]), ("J", target_col["point_j"])):
        incident = adjacency.get(pt_id, [])
        applicability = (low_axial_by_joint or {}).get(pt_id)
        applicability_field = {"low_axial_exception": applicability} if applicability else {}
        if dependency_plan is not None:
            from .design_dependencies import joint_blockers
            blocked = joint_blockers(dependency_plan, pt_id)
            if blocked:
                for direction in ("X", "Y"):
                    joint_summaries.append({
                        "joint_id": pt_id, "target_member_id": uid, "target_end": end,
                        "direction": direction, "column_ids": [r["frame_id"] for r in incident if r["type"] == "Column"],
                        "beam_ids": [r["frame_id"] for r in incident if r["type"] == "Beam"],
                        "status": "BLOCKED_DEPENDENCY", "execution_status": "NOT_RUN", "reasons": blocked,
                        "cases": [], "scenario_reference_satisfied": None,
                        "sampled_minimum_normalized_ratio": None, "formal_compliance": "NOT_PROVEN",
                        **applicability_field,
                    })
                continue
        if pt_id not in points:
            continue
        inc_cols = [frames[item["frame_id"]] for item in incident if item["type"] == "Column"]
        inc_beams = [frames[item["frame_id"]] for item in incident if item["type"] == "Beam"]
        if not inc_beams:
            continue
        inc_items_by_id = {item["frame_id"]: item for item in incident}

        # Cache Section for each participating column whose section definition exists in pmm_section_source
        col_sections: dict[str, tuple[Any, dict]] = {}
        for col in inc_cols:
            cid = col["frame_id"]
            if cid in cache:
                col_sections[cid] = cache[cid]
            elif cid in geom_by_id and cid in axial_by_id and "fcd_mpa" in axial_by_id[cid]:
                try:
                    built = build_pmm_section(
                        pmm_sec_source, geom_by_id[cid], axial_by_id[cid], prefs, include_layout=False,
                    )
                    cache[cid] = built
                    col_sections[cid] = built
                except (ValueError, KeyError, TypeError, ArithmeticError):
                    pass

        for direction in ("X", "Y"):
            dir_vec = [1.0, 0.0, 0.0] if direction == "X" else [0.0, 1.0, 0.0]
            dir_beams = []
            dir_reasons = []
            for beam in inc_beams:
                b_axes = beam.get("axes_global")
                if b_axes is None:
                    dir_reasons.append(f"BEAM_AXES_MISSING:{beam['frame_id']}")
                    continue
                if _parallel(b_axes[0], dir_vec):
                    dir_beams.append((beam, inc_items_by_id[beam["frame_id"]]["end"]))
            if not dir_beams:
                continue

            interval_result = None
            if applicability and applicability.get("status") == "LOW_AXIAL_LIMIT_EXCEEDED":
                interval_result = _selected_scwb_interval(pt_id, direction, applicability, dependency_plan,
                    inc_cols, inc_beams, inc_items_by_id, dir_beams, beam_by_id, eng_secs, run_id)

            # Column participation along this global bending direction
            case_results = []
            eng_case_results = []
            for combo in static_combos:
                col_caps: list[MemberMomentCapacity] = []
                eng_col_caps: list[MemberMomentCapacity] = []
                expected_cols = [(c["frame_id"], inc_items_by_id[c["frame_id"]]["end"]) for c in inc_cols]
                expected_beams = [(b["frame_id"], bend) for b, bend in dir_beams]
                ctx = JointCase(run_id, src_hash, pt_id, direction, 1, combo, "LIVE_CAPTURED_SECTION_AT_END_N")

                for col in inc_cols:
                    cid = col["frame_id"]
                    cend = inc_items_by_id[cid]["end"]
                    c_axes = col.get("axes_global")
                    if cid not in col_sections or c_axes is None:
                        miss = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", None, None,
                            reason="COLUMN_SECTION_REINFORCEMENT_NOT_CAPTURED",
                        )
                        col_caps.append(miss)
                        eng_col_caps.append(miss)
                        continue
                    aligned = [i for i in (1, 2) if _parallel(c_axes[i], dir_vec)]
                    if len(aligned) != 1:
                        miss = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", None, None,
                            reason="SCWB_COLUMN_GLOBAL_AXIS_NOT_PRINCIPAL",
                        )
                        col_caps.append(miss)
                        eng_col_caps.append(miss)
                        continue
                    # Bending about global vector orthogonal to dir_vec (local 2 or local 3 axis aligned to Z cross d)
                    rot_axis = [0.0, 1.0, 0.0] if direction == "X" else [-1.0, 0.0, 0.0]
                    mom_idx = [i for i in (1, 2) if _parallel(c_axes[i], rot_axis)]
                    if len(mom_idx) != 1:
                        miss = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", None, None,
                            reason="SCWB_MOMENT_AXIS_NOT_PRINCIPAL",
                        )
                        col_caps.append(miss)
                        eng_col_caps.append(miss)
                        continue
                    bend_axis = "M2" if mom_idx[0] == 1 else "M3"
                    rowset = force_rowsets.get(cid)
                    if rowset is None:
                        miss = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", None, None,
                            reason="COLUMN_FORCE_ROWSET_MISSING",
                        )
                        col_caps.append(miss)
                        eng_col_caps.append(miss)
                        continue
                    rows = [r for r in native_frame_force_rows(rowset, cid) if r[4] == combo and r[6] == 0]
                    if not rows:
                        miss = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", None, None,
                            reason="COLUMN_COMBO_FORCE_ROWS_MISSING",
                        )
                        col_caps.append(miss)
                        eng_col_caps.append(miss)
                        continue
                    target_sta = min(r[1] for r in rows) if cend == "I" else max(r[1] for r in rows)
                    cut_rows = [r for r in rows if abs(r[1] - target_sta) <= 1e-7]
                    if len(cut_rows) != 1:
                        miss = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", None, None,
                            reason="COLUMN_END_CUT_AMBIGUOUS",
                        )
                        col_caps.append(miss)
                        eng_col_caps.append(miss)
                        continue
                    n_kn = -float(cut_rows[0][7])
                    section, sec_ev = col_sections[cid]
                    calc = column_axis_capacity(section, n_kn * 1000.0, bend_axis)
                    if calc["status"] != "COLUMN_CAPACITY_REFERENCE":
                        mc = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", None, None,
                            reason=calc.get("reason") or "COLUMN_CAPACITY_UNRESOLVED",
                        )
                    else:
                        mc = MemberMomentCapacity(
                            ctx, cid, cend, "COLUMN", calc["capacity_knm"],
                            f"live-{cid}-{cend}-{combo}-{bend_axis}",
                            tolerance_knm=calc["tolerance_knm"] or 0.0,
                        )
                        # Also validate sign mapping on participating axes
                        try:
                            moment_sign_mapping(c_axes, cend, direction, 1, bend_axis)
                        except BankError:
                            pass
                    col_caps.append(mc)
                    if cid in eng_secs:
                        eng_calc = column_axis_capacity(eng_secs[cid], n_kn * 1000.0, bend_axis)
                        if eng_calc["status"] != "COLUMN_CAPACITY_REFERENCE":
                            eng_col_caps.append(MemberMomentCapacity(
                                ctx, cid, cend, "COLUMN", None, None,
                                reason=eng_calc.get("reason") or "COLUMN_CAPACITY_UNRESOLVED",
                            ))
                        else:
                            eng_col_caps.append(MemberMomentCapacity(
                                ctx, cid, cend, "COLUMN", eng_calc["capacity_knm"],
                                f"live-eng-{cid}-{cend}-{combo}-{bend_axis}",
                                tolerance_knm=eng_calc["tolerance_knm"] or 0.0,
                            ))
                    else:
                        eng_col_caps.append(mc)

                target_cap_obj = next((c for c in col_caps if c.member_id == uid and c.capacity_knm is not None), None)
                if any(b["frame_id"] in beam_by_id for b, _ in dir_beams):
                    for rot_sign in (-1, 1):
                        ev_sign = _scwb_sign_evaluation(
                            run_id=run_id, src_hash=src_hash, pt_id=pt_id, direction=direction,
                            combo=combo, rot_sign=rot_sign, expected_cols=expected_cols,
                            expected_beams=expected_beams, col_caps_base=col_caps,
                            dir_beams=dir_beams, beam_by_id=beam_by_id, diameter_mm=20,
                        )
                        ev_sign["target_column_capacity_knm"] = target_cap_obj.capacity_knm if target_cap_obj else None
                        ev_sign["alt_diameters"] = {
                            str(d): {
                                "normalized_reference_ratio": (alt := _scwb_sign_evaluation(
                                    run_id=run_id, src_hash=src_hash, pt_id=pt_id, direction=direction,
                                    combo=combo, rot_sign=rot_sign, expected_cols=expected_cols,
                                    expected_beams=expected_beams, col_caps_base=col_caps,
                                    dir_beams=dir_beams, beam_by_id=beam_by_id, diameter_mm=d,
                                ))["normalized_reference_ratio"],
                                "reference_satisfied": alt["reference_satisfied"],
                            }
                            for d in (16, 24)
                        }
                        case_results.append(ev_sign)
                        if beam_sel_active:
                            eng_target_cap_obj = next(
                                (c for c in eng_col_caps if c.member_id == uid and c.capacity_knm is not None),
                                None,
                            )
                            eng_ev = _scwb_sign_evaluation(
                                run_id=run_id, src_hash=src_hash, pt_id=pt_id, direction=direction,
                                combo=combo, rot_sign=rot_sign, expected_cols=expected_cols,
                                expected_beams=expected_beams, col_caps_base=eng_col_caps,
                                dir_beams=dir_beams, beam_by_id=beam_by_id, diameter_mm="ENGINEER_SELECTED",
                            )
                            eng_ev["target_column_capacity_knm"] = (
                                eng_target_cap_obj.capacity_knm if eng_target_cap_obj else None
                            )
                            eng_case_results.append(eng_ev)
                else:
                    beam_caps = [
                        MemberMomentCapacity(
                            ctx, b["frame_id"], bend, "BEAM", None, None,
                            reason="ACTUAL_OR_SELECTED_BEAM_REINFORCEMENT_NOT_BOUND",
                        )
                        for b, bend in dir_beams
                    ]
                    agg = compute_scwb_joint_result(ctx, expected_cols, expected_beams, col_caps + beam_caps)
                    resolved_cols = [c for c in col_caps if c.capacity_knm is not None]
                    mrc_sum = math.fsum(c.capacity_knm for c in resolved_cols) if len(resolved_cols) == len(col_caps) else None
                    case_results.append({
                        "output_case": combo,
                        "rotation_sign": 1,
                        "sum_mrc_reference_knm": mrc_sum,
                        "sum_mrb_reference_knm": agg["sum_mrb_reference_knm"],
                        "required_mrc_reference_knm": agg["required_mrc_reference_knm"],
                        "normalized_reference_ratio": agg["normalized_reference_ratio"],
                        "reference_satisfied": agg["reference_satisfied"],
                        "target_column_capacity_knm": target_cap_obj.capacity_knm if target_cap_obj else None,
                        "status": agg["status"],
                        "missing_capacities": agg["missing_capacities"],
                    })

            mrc_values = [c["sum_mrc_reference_knm"] for c in case_results if c["sum_mrc_reference_knm"] is not None]
            mrb_values = [c["sum_mrb_reference_knm"] for c in case_results if c["sum_mrb_reference_knm"] is not None]
            ratios = [c["normalized_reference_ratio"] for c in case_results if c["normalized_reference_ratio"] is not None]
            complete_scenarios = bool(case_results) and len(ratios) == len(case_results)
            diameter_scenarios: dict[str, Any] = {}
            if mrb_values:
                expected_n = 2 * len(static_combos)
                for diam in (16, 20, 24):
                    if diam == 20:
                        d_ratios, d_sat = ratios, [c["reference_satisfied"] for c in case_results]
                    else:
                        alt_rows = [(c.get("alt_diameters") or {}).get(str(diam), {}) for c in case_results]
                        d_ratios = [r["normalized_reference_ratio"] for r in alt_rows if r.get("normalized_reference_ratio") is not None]
                        d_sat = [r["reference_satisfied"] for r in alt_rows if r.get("reference_satisfied") is not None]
                    diameter_scenarios[str(diam)] = {
                        "minimum_normalized_ratio": min(d_ratios) if len(d_ratios) == expected_n and d_ratios else None,
                        "scenario_reference_satisfied": (
                            None if len(d_sat) != expected_n else all(d_sat)
                        ),
                    }
            template_role = any(
                ev["reinforcement_role"] == "ETABS_DESIGN_TEMPLATE" for _, ev in col_sections.values()
            )
            if complete_scenarios:
                joint_status = "SCENARIO_SCWB_EVALUATED_NOT_PROVEN"
            elif mrb_values:
                joint_status = "SCENARIO_SCWB_PARTIAL_NOT_PROVEN"
            elif mrc_values:
                joint_status = "BEAM_CAPACITY_NOT_BOUND"
            else:
                joint_status = "COLUMN_AND_BEAM_INPUTS_INCOMPLETE"
            eng_scwb_block: dict[str, Any] | None = None
            if eng_case_results:
                eng_mrc = [c["sum_mrc_reference_knm"] for c in eng_case_results if c["sum_mrc_reference_knm"] is not None]
                eng_mrb = [c["sum_mrb_reference_knm"] for c in eng_case_results if c["sum_mrb_reference_knm"] is not None]
                eng_rat = [c["normalized_reference_ratio"] for c in eng_case_results if c["normalized_reference_ratio"] is not None]
                eng_complete = len(eng_rat) == len(eng_case_results)
                eng_scwb_block = {
                    "column_capacity_role": "ENGINEER_SELECTED_COLUMN_REBAR" if eng_secs else ("TEMPLATE_SCENARIO_ONLY" if template_role else "ETABS_CHECK_REINFORCEMENT"),
                    "beam_capacity_role": "ENGINEER_SELECTED_BEAM_REBAR",
                    "sampled_minimum_column_sum_knm": min(eng_mrc) if eng_mrc else None,
                    "sampled_minimum_beam_sum_knm": min(eng_mrb) if eng_mrb else None,
                    "sampled_minimum_normalized_ratio": min(eng_rat) if eng_complete and eng_rat else None,
                    "reference_satisfied": (
                        None if not eng_complete or any(c["reference_satisfied"] is None for c in eng_case_results)
                        else all(c["reference_satisfied"] for c in eng_case_results)
                    ),
                    "cases": eng_case_results,
                }

            joint_summaries.append({
                "joint_id": pt_id,
                "target_member_id": uid,
                "target_end": end,
                "direction": direction,
                "column_ids": [c["frame_id"] for c in inc_cols],
                "beam_ids": [b["frame_id"] for b, _ in dir_beams],
                "column_capacity_role": "TEMPLATE_SCENARIO_ONLY" if template_role else "ETABS_CHECK_REINFORCEMENT",
                "beam_capacity_role": "CANDIDATE_SCENARIO_PHI20_N0" if mrb_values else "UNBOUND",
                "sampled_minimum_column_sum_knm": min(mrc_values) if mrc_values else None,
                "sampled_minimum_beam_sum_knm": min(mrb_values) if mrb_values else None,
                "sampled_minimum_normalized_ratio": min(ratios) if complete_scenarios and ratios else None,
                "scenario_reference_satisfied": (
                    None if not complete_scenarios or any(c["reference_satisfied"] is None for c in case_results)
                    else all(c["reference_satisfied"] for c in case_results)
                ),
                "diameter_scenarios": diameter_scenarios,
                **({"engineer_selected_scwb": eng_scwb_block} if eng_scwb_block is not None else {}),
                "static_case_count": len(static_combos),
                "cases": case_results,
                "status": ("SCWB_EQ_7_3_EXEMPT_LOW_AXIAL" if applicability and applicability["exempt"] is True
                           else interval_result["status"] if interval_result and interval_result["sufficient"] else joint_status),
                **({"seismic_axial_interval_check": interval_result} if interval_result else {}),
                **applicability_field,
                "scwb_ratio": None,
                "formal_compliance": "NOT_PROVEN",
                "reasons": dir_reasons,
            })
    return joint_summaries


def _evaluate_column_shear_and_confinement_for_id(
    uid: str | None,
    source: Mapping[str, Any],
    geometry: Mapping[str, Any],
    axial: Mapping[str, Any],
    *, demand_revision: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Evaluate TBDY 7.3.4.1(d) confinement and TS500 8.1 / zero-concrete shear refs for one column."""
    from .column_axial import _columns
    from .column_pmm_section import build_pmm_section

    feature = source.get("column_axial") or {}
    pmm_source = feature.get("pmm_section_source")
    prefs = feature.get("design_preferences")
    rowset = (feature.get("force_source") or {}).get("rowsets", {}).get(uid)
    member = next((r for r in _columns(geometry) if r["element_id"] == uid), None)
    axial_member = next((r for r in axial.get("columns", ()) if r["element_id"] == uid), None)
    if not uid or not pmm_source or not prefs or rowset is None or not member or not axial_member:
        return None
    try:
        section, ev = build_pmm_section(pmm_source, member, axial_member, prefs, include_layout=True)
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return {"member_id": uid, "status": "BLOCKED_INPUTS", "reason": str(exc), "formal_compliance": "NOT_PROVEN"}

    return _finish_column_shear_and_confinement(uid, section, ev, pmm_source, rowset, axial, demand_revision=demand_revision)


def _evaluate_column_shear_and_confinement(
    source: Mapping[str, Any],
    geometry: Mapping[str, Any],
    axial: Mapping[str, Any],
    pmm: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Evaluate TBDY 7.3.4.1(d) confinement and TS500 8.1 / zero-concrete shear refs."""
    return _evaluate_column_shear_and_confinement_for_id(pmm.get("member_id"), source, geometry, axial)


def _finish_column_shear_and_confinement(
    uid: str,
    section: Any,
    ev: Mapping[str, Any],
    pmm_source: Mapping[str, Any],
    rowset: Mapping[str, Any],
    axial: Mapping[str, Any],
    *, demand_revision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:

    spacing_mm = ev.get("tie_spacing_mm")
    n_legs_2 = ev.get("tie_bars_parallel_2")
    n_legs_3 = ev.get("tie_bars_parallel_3")
    cover_mm = ev.get("cover_to_tie_mm")
    tie_mm = ev.get("tie_diameter_mm")
    tie_mat_name = ev.get("tie_material_name")
    tables = pmm_source.get("table_reads") or {}
    rebar_rows = (tables.get("Material Properties - Rebar Data") or {}).get("rows") or []
    tie_mat = next((r for r in rebar_rows if r.get("Material") == tie_mat_name), None)
    fywk_mpa = (_float_or_none(tie_mat.get("Fy")) / 1000.0) if tie_mat and _float_or_none(tie_mat.get("Fy")) else None
    if fywk_mpa is None:
        fywk_mpa = ev.get("fy_mpa")

    ac = section.t2 * section.t3
    # Center of outermost longitudinal bars for effective depth d (same as column_transverse)
    center = cover_mm + tie_mm + ev["longitudinal_bar_diameter_mm"] / 2.0
    ack = (section.t2 - 2.0 * cover_mm) * (section.t3 - 2.0 * cover_mm)
    bk2 = section.t3 - 2.0 * cover_mm - tie_mm  # axis 2 shear perpendicular bk along local 3
    bk3 = section.t2 - 2.0 * cover_mm - tie_mm  # axis 3 shear perpendicular bk along local 2

    confinement: dict[str, Any] = {}
    shear_stations: list[dict[str, Any]] = []
    if spacing_mm and fywk_mpa and n_legs_2 and n_legs_3 and n_legs_2 >= 2 and n_legs_3 >= 2:
        leg_area = math.pi * (tie_mm ** 2) / 4.0
        for axis, bw, depth, bk, n_legs in (
            ("V2", section.t3, section.t2, bk2, n_legs_2),
            ("V3", section.t2, section.t3, bk3, n_legs_3),
        ):
            asw = n_legs * leg_area
            confinement[axis] = {
                "legs": n_legs,
                "asw_mm2": asw,
                "spacing_mm": spacing_mm,
                "fywk_mpa": fywk_mpa,
                "d_mm": depth - center,
                **confinement_reference(
                    area_mm2=ac,
                    core_area_mm2=ack,
                    bk_mm=bk,
                    spacing_mm=spacing_mm,
                    fck_mpa=ev["fck_mpa"],
                    fywk_mpa=fywk_mpa,
                    ash_mm2=asw,
                ),
            }

        static_names = {
            c["name"]
            for c in (axial.get("combination_plan") or {}).get("combinations", ())
            if c.get("force_semantics") == "STATIC_SIGNED_VECTOR"
        }
        gamma_c = float(ev["fck_mpa"]) / float(ev["fcd_mpa"])
        gamma_s = float(ev["gamma_s"])
        from .alpha_iteration import revised_force_rows
        for row in sorted(revised_force_rows(rowset, uid, demand_revision), key=lambda r: (r[4], r[:4])):
            _, sta, elm, elm_sta, combo, _, _, p, v2, v3, _, _, _ = row
            if combo not in static_names:
                continue
            nd = -float(p)
            v2_ref = shear_reference(
                n_compression_kn=nd, shear_kn=float(v2), area_mm2=ac,
                bw_mm=section.t3, d_mm=section.t2 - center,
                fck_mpa=ev["fck_mpa"], fywk_mpa=fywk_mpa,
                asw_mm2=confinement["V2"]["asw_mm2"], spacing_mm=spacing_mm,
                gamma_c=gamma_c, gamma_s=gamma_s,
            )
            v3_ref = shear_reference(
                n_compression_kn=nd, shear_kn=float(v3), area_mm2=ac,
                bw_mm=section.t2, d_mm=section.t3 - center,
                fck_mpa=ev["fck_mpa"], fywk_mpa=fywk_mpa,
                asw_mm2=confinement["V3"]["asw_mm2"], spacing_mm=spacing_mm,
                gamma_c=gamma_c, gamma_s=gamma_s,
            )
            shear_stations.append({
                "combination": combo,
                "analysis_element_id": elm,
                "object_station_m": sta,
                "element_station_m": elm_sta,
                "nd_kn": nd,
                "v2_kn": float(v2),
                "v3_kn": float(v3),
                "v2_ts500_vr_kn": v2_ref["branches"]["ts500"]["vr_kn"],
                "v2_zero_concrete_vr_kn": v2_ref["branches"]["zero_concrete"]["vr_kn"],
                "v2_ts500_utilization": v2_ref["branches"]["ts500"]["source_utilization"],
                "v3_ts500_vr_kn": v3_ref["branches"]["ts500"]["vr_kn"],
                "v3_zero_concrete_vr_kn": v3_ref["branches"]["zero_concrete"]["vr_kn"],
                "v3_ts500_utilization": v3_ref["branches"]["ts500"]["source_utilization"],
                "ve_status": "NOT_PROVEN",
            })

    return {
        "member_id": uid,
        "reinforcement_role": ev["reinforcement_role"],
        "tie_material_name": tie_mat_name,
        "fywk_mpa": fywk_mpa,
        "spacing_mm": spacing_mm,
        "confinement": confinement,
        "shear_station_count": len(shear_stations),
        "shear_stations": shear_stations,
        "max_v2_ts500_utilization": max((s["v2_ts500_utilization"] for s in shear_stations if s["v2_ts500_utilization"] is not None), default=None),
        "max_v3_ts500_utilization": max((s["v3_ts500_utilization"] for s in shear_stations if s["v3_ts500_utilization"] is not None), default=None),
        "status": "SCENARIO_REFERENCES_CALCULATED" if confinement else "TRANSVERSE_DETAILS_INCOMPLETE",
        "ve_status": "NOT_PROVEN",
        "formal_compliance": "NOT_PROVEN",
    }


def _global_pmm_moment_projection(
    pmm: Mapping[str, Any] | None,
    dims: Any,
    angle_deg: float | None,
) -> list[dict[str, Any]]:
    if not pmm or dims is None or angle_deg is None:
        return []
    out = []
    for row in pmm.get("rows", ()):
        if row.get("nd_kn") is None or row.get("m2_knm") is None or row.get("m3_knm") is None:
            continue
        proj = apply_minimum_eccentricity(
            nd_kn=row["nd_kn"], m2_knm=row["m2_knm"], m3_knm=row["m3_knm"],
            dims=dims, local_axis_angle_deg=angle_deg,
        )
        out.append({
            "combination": row["combination"],
            "object_station_m": row["object_station_m"],
            "local_axis_angle_deg": angle_deg,
            "mx_global_design_knm": proj["mx_global_design_knm"],
            "my_global_design_knm": proj["my_global_design_knm"],
        })
    return out


def _column_clear_length_m(source: Mapping[str, Any], uid: str) -> tuple[float | None, str]:
    scale_map = {"m": 1.0, "cm": 0.01, "mm": 0.001}
    col_tbl = ((source.get("geometry_capture") or {}).get("tables") or {}).get("COLUMN_CONNECTIVITY") or {}
    col_unit = (((col_tbl.get("field_metadata") or {}).get("units_by_field") or {}).get("Length") or "m").strip()
    if col_unit not in scale_map:
        return None, "COLUMN_LENGTH_UNIT_UNSUPPORTED"
    col_scale = scale_map[col_unit]
    raw_len = next((_float_or_none(r.get("Length")) for r in col_tbl.get("rows") or () if r.get("UniqueName") == uid), None)
    if raw_len is None or raw_len <= 0:
        return None, "COLUMN_LENGTH_MISSING"
    frame_len_m = raw_len * col_scale
    r10 = (source.get("column_axial") or {}).get("r10_source") or {}
    off_tbl = (r10.get("table_reads") or {}).get(END_OFFSETS) or {}
    fields = set(off_tbl.get("fields") or ())
    ik = next((k for k in ("LengthI", "Length1", "OffsetI") if k in fields), None)
    jk = next((k for k in ("LengthJ", "Length2", "OffsetJ") if k in fields), None)
    if ik and jk:
        off_units = (off_tbl.get("field_metadata") or {}).get("units_by_field") or {}
        u_i = (off_units.get(ik) or "m").strip()
        u_j = (off_units.get(jk) or "m").strip()
        if u_i not in scale_map or u_j not in scale_map:
            return frame_len_m, "END_OFFSET_UNIT_UNSUPPORTED"
        row = next((r for r in off_tbl.get("rows") or () if r.get("UniqueName") == uid), None)
        if row:
            raw_i, raw_j = _float_or_none(row.get(ik)), _float_or_none(row.get(jk))
            if raw_i is not None and raw_j is not None:
                off_i, off_j = raw_i * scale_map[u_i], raw_j * scale_map[u_j]
                if min(off_i, off_j) >= 0 and off_i + off_j < frame_len_m:
                    return frame_len_m - off_i - off_j, "END_OFFSETS_SUBTRACTED"
    return frame_len_m, "UNREDUCED_FRAME_LENGTH_NOT_PROVEN"


def _compute_capacity_shear_axes(
    *,
    uid: str,
    col_frame: Mapping[str, Any],
    ln_m: float,
    scwb_joints: list[dict[str, Any]],
    stations: list[dict[str, Any]],
    static_combos: list[str],
    rowset: Mapping[str, Any] | None,
    section: Any,
    use_engineer: bool,
    vr_lookup: Any,
    demand_revision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute conditional CHK-126 capacity shear, with the 7.3.7.5 Vd floor.

    The original and revised demands use the same rule. Native case/cut/step
    identities survive the scalar Vd envelope; incomplete cases remain in the
    output and cannot produce a favorable complete-axis utilization.
    """
    c_axes = col_frame["axes_global"]
    by_joint_dir = {(j["target_end"], j["direction"]): j for j in scwb_joints}
    axes_out: dict[str, Any] = {}
    native_rows, demand_rows = [], []
    force_error = None
    if rowset is not None:
        try:
            native_rows = list(native_frame_force_rows(rowset, uid))
            if demand_revision is None:
                demand_rows = native_rows
            else:
                from .alpha_iteration import revised_force_rows
                demand_rows = revised_force_rows(rowset, uid, demand_revision)
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            force_error = "VD_FORCE_SOURCE_UNRESOLVED:" + str(exc)
    expected_cuts = {r[1:4] for r in native_rows}

    def _vd_floor(combo: str, v_axis: str) -> dict[str, Any]:
        key = "v2_kn" if v_axis == "V2" else "v3_kn"
        errors = [force_error] if force_error else []
        if rowset is not None:
            rows = [r for r in demand_rows if r[4] == combo]
            observed_cuts = {r[1:4] for r in rows}
            missing_cuts = sorted(expected_cuts - observed_cuts)
            if missing_cuts:
                errors.append("VD_REQUIRED_NATIVE_CUT_MISSING")
            if any(r[5] not in ("", "Single Value") or r[6] != 0 for r in rows):
                errors.append("VD_STATIC_SIGNED_STEP_REQUIRED")
            if len(observed_cuts) != len(rows):
                errors.append("VD_STATIC_CUT_AMBIGUOUS")
            references = [{
                "member_id": uid, "combination": combo,
                "object_station_m": r[1], "analysis_element_id": r[2], "element_station_m": r[3],
                "step_type": r[5], "step_number": r[6], "shear_axis": v_axis,
                "signed_shear_kn": r[8 if v_axis == "V2" else 9],
            } for r in rows]
            basis = "SOURCE_WIDE_NATIVE_CUT_CENSUS_NOT_PHYSICAL_CUT_ACCEPTANCE"
            expected_count = len(expected_cuts)
        else:
            # Retain the existing direct-owner station contract. The live
            # pipeline supplies its native rowset and never uses this fallback.
            references = [{
                "member_id": uid, "combination": combo,
                **{name: st.get(name) for name in (
                    "object_station_m", "analysis_element_id", "element_station_m", "step_type", "step_number")},
                "shear_axis": v_axis, "signed_shear_kn": st.get(key),
            } for st in stations if st.get("combination") == combo]
            missing_cuts, expected_count = [], None
            basis = "PROJECTED_SHEAR_STATIONS_REFERENCE_WITHOUT_NATIVE_CUT_CENSUS"
        if not references:
            errors.append("VD_REQUIRED_COMBINATION_MISSING")
        values = [_float_or_none(r["signed_shear_kn"]) for r in references]
        if any(value is None for value in values):
            errors.append("VD_SHEAR_VALUE_MISSING_OR_INVALID")
        witness = (max(zip(references, values), key=lambda pair: abs(pair[1]))
                   if references and not errors else None)
        return {
            "vd_floor_kn": abs(witness[1]) if witness else None,
            "vd_floor_basis": basis,
            "vd_governing_cut": witness[0] if witness else None,
            "vd_expected_cut_count": expected_count,
            "vd_observed_cut_count": len(references),
            "vd_missing_cuts": [{"object_station_m": c[0], "analysis_element_id": c[1],
                                 "element_station_m": c[2]} for c in missing_cuts],
            "reason_codes": sorted(set(errors)),
        }

    for direction, dir_vec in (("X", [1.0, 0.0, 0.0]), ("Y", [0.0, 1.0, 0.0])):
        shear_idx = [i for i in (1, 2) if _parallel(c_axes[i], dir_vec)]
        if len(shear_idx) != 1:
            continue
        v_axis = "V2" if shear_idx[0] == 1 else "V3"
        bend_axis = "M3" if v_axis == "V2" else "M2"
        j_i = by_joint_dir.get(("I", direction))
        j_j = by_joint_dir.get(("J", direction))
        has_framing_beams = bool(j_i or j_j)
        cases_ve: list[dict[str, Any]] = []
        for combo in static_combos:
            def _end_mp(joint_entry: Mapping[str, Any] | None, end_label: str) -> tuple[float | None, float | None, str]:
                if joint_entry:
                    src_block = (joint_entry.get("engineer_selected_scwb") or {}) if use_engineer else joint_entry
                    rows = [c for c in src_block.get("cases") or () if c["output_case"] == combo]
                    capacities = [_float_or_none(c.get("target_column_capacity_knm")) for c in rows]
                    m_col = (max(capacities) if capacities and all(v is not None and v >= 0 for v in capacities) else None)
                    if m_col is None:
                        return None, None, "COLUMN_CAPACITY_MISSING"
                    mp_unred = 1.4 * float(m_col)
                    # TBDY 7.3.7.2 distributes beam Mp using ANALYSIS end moments,
                    # not column Mr ratios. Without that evidence use the explicitly
                    # permitted unreduced 7.3.7.3 reference. Demand completeness,
                    # physical ln, governing Nd and the D*E alternative remain gates.
                    return mp_unred, mp_unred, "UNREDUCED_7_3_7_3_NO_ANALYSIS_MOMENT_SHARE"
                if section is None or rowset is None:
                    return None, None, "SUPPORT_END_SECTION_UNBOUND"
                f_rows = [r for r in native_rows if r[4] == combo and r[5] in ("", "Single Value") and r[6] == 0]
                if not f_rows:
                    return None, None, "SUPPORT_END_FORCE_MISSING"
                sta = min(r[1] for r in f_rows) if end_label == "I" else max(r[1] for r in f_rows)
                cuts = [r for r in f_rows if abs(r[1] - sta) <= 1e-7]
                if len(cuts) != 1:
                    return None, None, "SUPPORT_END_CUT_AMBIGUOUS"
                calc = column_axis_capacity(section, -float(cuts[0][7]) * 1000.0, bend_axis)
                if calc["status"] != "COLUMN_CAPACITY_REFERENCE":
                    return None, None, calc.get("reason") or "COLUMN_CAPACITY_UNRESOLVED"
                mp_val = 1.4 * float(calc["capacity_knm"])
                return mp_val, mp_val, "SUPPORT_UNREDUCED_1_4_MR"

            mp_i_unred, mp_i_eff, i_basis = _end_mp(j_i, "I")
            mp_j_unred, mp_j_eff, j_basis = _end_mp(j_j, "J")
            vd = _vd_floor(combo, v_axis)
            errors = list(vd.pop("reason_codes"))
            ends_resolved = all(_float_or_none(v) is not None and float(v) >= 0
                                for v in (mp_i_unred, mp_j_unred, mp_i_eff, mp_j_eff))
            if not ends_resolved:
                errors.append("CAPACITY_SHEAR_END_MOMENT_UNRESOLVED")
            ve_unred = (mp_i_unred + mp_j_unred) / ln_m if ends_resolved else None
            ve_eff = (max((mp_i_eff + mp_j_eff) / ln_m, vd["vd_floor_kn"])
                      if ends_resolved and not errors else None)
            vr_min, vr_z_min = vr_lookup(combo, v_axis, ve_eff) if ve_eff is not None else (None, None)
            vr_min, vr_z_min = _float_or_none(vr_min), _float_or_none(vr_z_min)
            if ve_eff is not None and (vr_min is None or vr_min <= 0 or vr_z_min is None or vr_z_min <= 0):
                errors.append("CAPACITY_SHEAR_RESISTANCE_MISSING_OR_INVALID")
            cases_ve.append({
                "combination": combo,
                "status": "CAPACITY_SHEAR_CASE_UNRESOLVED" if errors else "CAPACITY_SHEAR_CASE_CALCULATED_NOT_PROVEN",
                "reason_codes": sorted(set(errors)),
                "mp_i_basis": i_basis,
                "mp_j_basis": j_basis,
                "ve_unreduced_kn": ve_unred,
                "ve_scwb_scenario_kn": ve_eff,
                **vd,
                **({"revised_vd_floor_kn": vd["vd_floor_kn"], "alpha_demand_revision_sha256": demand_revision.get("sha256")} if demand_revision is not None else {}),
                "vr_ts500_min_kn": vr_min,
                "vr_zero_concrete_min_kn": vr_z_min,
                "utilization_ts500": (ve_eff / vr_min) if ve_eff is not None and vr_min is not None and vr_min > 0 else None,
                "utilization_zero_concrete": (ve_eff / vr_z_min) if ve_eff is not None and vr_z_min is not None and vr_z_min > 0 else None,
            })
        if cases_ve:
            complete = all(c["status"] == "CAPACITY_SHEAR_CASE_CALCULATED_NOT_PROVEN" for c in cases_ve)
            def _complete_max(key: str) -> float | None:
                values = [_float_or_none(c.get(key)) for c in cases_ve]
                return max(values) if all(v is not None for v in values) else None
            gov = (max(cases_ve, key=lambda item: item["ve_scwb_scenario_kn"])
                   if _complete_max("ve_scwb_scenario_kn") is not None else None)
            axes_out[v_axis] = {
                "direction": direction,
                "bending_axis": bend_axis,
                "status": "SCENARIO_VE_CALCULATED_NOT_PROVEN" if complete else "CAPACITY_SHEAR_INPUTS_UNRESOLVED",
                "expected_combination_count": len(static_combos),
                "evaluated_combination_count": sum(c["status"] == "CAPACITY_SHEAR_CASE_CALCULATED_NOT_PROVEN" for c in cases_ve),
                "unresolved_combinations": [c["combination"] for c in cases_ve if c["status"] != "CAPACITY_SHEAR_CASE_CALCULATED_NOT_PROVEN"],
                "reason_codes": sorted({reason for c in cases_ve for reason in c["reason_codes"]}),
                "ve_basis": (
                    "FRAMED_JOINT_ENDS"
                    if has_framing_beams
                    else "NO_FRAMING_BEAMS_BOTH_ENDS_1_4_MR"
                ),
                "governing_combination": gov["combination"] if gov else None,
                "max_ve_unreduced_kn": _complete_max("ve_unreduced_kn"),
                "max_ve_scwb_scenario_kn": _complete_max("ve_scwb_scenario_kn"),
                "max_utilization_ts500": _complete_max("utilization_ts500"),
                "max_utilization_zero_concrete": _complete_max("utilization_zero_concrete"),
                "cases": cases_ve,
            }
    return axes_out


def _column_capacity_shear_ve(
    *,
    uid: str,
    col_frame: Mapping[str, Any] | None,
    scwb_joints: list[dict[str, Any]],
    transverse_shear: dict[str, Any] | None,
    source: Mapping[str, Any],
    geometry: Mapping[str, Any],
    axial: Mapping[str, Any],
    engineer_col_section: Any = None,
    engineer_column_selection: Mapping[str, Any] | None = None,
    use_engineer_selection: bool = False,
    demand_revision: Mapping[str, Any] | None = None,
    spectral_context: Mapping[str, Any] | None = None,
    candidate_revision: str | None = None,
    physical_length: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """TBDY 2018 §7.3.7 (CHK-126) conditional column capacity shear Ve = (Ma + Mü) / ln."""
    if not col_frame or not transverse_shear or not col_frame.get("axes_global"):
        return None
    from .column_clear_length import FACE_BASIS, WALL_COUPLED, proven_clear_length_m

    if (physical_length and physical_length.get("member_id") == uid
            and physical_length.get("status") == WALL_COUPLED):
        return {
            "check_id": "CHK-126",
            "clear_length_m": None,
            "clear_length_basis": WALL_COUPLED,
            "axes": {},
            "status": "WALL_COUPLED_CAPACITY_SHEAR_REQUIRES_PHYSICAL_SPAN",
            "execution_status": "NOT_RUN",
            "formal_compliance": "NOT_PROVEN",
        }

    ln_m = proven_clear_length_m(physical_length, uid)
    ln_basis = FACE_BASIS
    if ln_m is None:
        ln_m, ln_basis = _column_clear_length_m(source, uid)
    if ln_m is None or ln_m <= 0:
        return None
    from .column_axial import _columns
    from .column_pmm_section import build_pmm_section

    feature = source.get("column_axial") or {}
    pmm_src = feature.get("pmm_section_source")
    prefs = feature.get("design_preferences")
    rowset = (feature.get("force_source") or {}).get("rowsets", {}).get(uid)
    member = next((r for r in _columns(geometry) if r["element_id"] == uid), None)
    axial_member = next((r for r in axial.get("columns", ()) if r["element_id"] == uid), None)
    base_section = None
    ev: dict[str, Any] = {}
    if pmm_src and prefs and member and axial_member and "fcd_mpa" in axial_member:
        try:
            base_section, ev = build_pmm_section(pmm_src, member, axial_member, prefs, include_layout=True)
        except (ValueError, KeyError, TypeError, ArithmeticError):
            base_section = None
    active_section = (
        engineer_col_section if (use_engineer_selection and engineer_col_section is not None) else base_section
    )

    static_combos = [
        c["name"]
        for c in (axial.get("combination_plan") or {}).get("combinations", ())
        if c.get("force_semantics") == "STATIC_SIGNED_VECTOR"
    ]
    stations = transverse_shear.get("shear_stations") or []

    def _template_vr_lookup(combo: str, v_axis: str, _ve_eff: float) -> tuple[float | None, float | None]:
        vr_key = "v2_ts500_vr_kn" if v_axis == "V2" else "v3_ts500_vr_kn"
        vr_z_key = "v2_zero_concrete_vr_kn" if v_axis == "V2" else "v3_zero_concrete_vr_kn"
        combo_sta = [s for s in stations if s["combination"] == combo]
        return (
            min((s[vr_key] for s in combo_sta if s.get(vr_key) is not None), default=None),
            min((s[vr_z_key] for s in combo_sta if s.get(vr_z_key) is not None), default=None),
        )

    vr_lookup = _template_vr_lookup
    sel_cage = (engineer_column_selection or {}).get("selected") or {}
    sel_tr = sel_cage.get("selected_transverse") or {}
    fywk_mpa = transverse_shear.get("fywk_mpa")
    if use_engineer_selection and sel_tr and active_section is not None and fywk_mpa and ev.get("gamma_s"):
        cover_mm = float(ev.get("cover_to_tie_mm") or 40.0)
        tie_d = float(sel_tr["tie_diameter_mm"])
        long_d = float(sel_cage["diameter_mm"])
        d_center = cover_mm + tie_d + long_d / 2.0
        leg_area = math.pi * (tie_d ** 2) / 4.0
        gamma_c = float(ev["fck_mpa"]) / float(ev["fcd_mpa"])
        gamma_s = float(ev["gamma_s"])
        ac = active_section.t2 * active_section.t3

        def _selected_vr_lookup(combo: str, v_axis: str, ve_eff: float) -> tuple[float | None, float | None]:
            combo_sta = [s for s in stations if s["combination"] == combo]
            if not combo_sta:
                return _template_vr_lookup(combo, v_axis, ve_eff)
            legs = sel_tr["legs_v2"] if v_axis == "V2" else sel_tr["legs_v3"]
            bw = active_section.t3 if v_axis == "V2" else active_section.t2
            d_eff = max(1.0, (active_section.t2 if v_axis == "V2" else active_section.t3) - d_center)
            vr_vals, vr_z_vals = [], []
            for st in combo_sta:
                ref = shear_reference(
                    n_compression_kn=st["nd_kn"], shear_kn=ve_eff, area_mm2=ac,
                    bw_mm=bw, d_mm=d_eff, fck_mpa=ev["fck_mpa"], fywk_mpa=fywk_mpa,
                    asw_mm2=legs * leg_area, spacing_mm=float(sel_tr["confinement_spacing_mm"]),
                    gamma_c=gamma_c, gamma_s=gamma_s,
                )
                vr_vals.append(ref["branches"]["ts500"]["vr_kn"])
                vr_z_vals.append(ref["branches"]["zero_concrete"]["vr_kn"])
            return min(vr_vals), min(vr_z_vals)

        vr_lookup = _selected_vr_lookup

    axes_out = _compute_capacity_shear_axes(
        uid=uid, col_frame=col_frame, ln_m=ln_m, scwb_joints=scwb_joints,
        stations=stations, static_combos=static_combos, rowset=rowset,
        section=active_section, use_engineer=use_engineer_selection, vr_lookup=vr_lookup, demand_revision=demand_revision,
    )
    if not axes_out:
        return None
    spectral = None
    if use_engineer_selection and spectral_context is not None:
        from .column_spectral_shear import selected_spectral_shear
        spectral = selected_spectral_shear(
            spectral_context, col_frame, rowset, engineer_col_section, sel_cage, ev, fywk_mpa,
            ln_m, ln_basis, axes_out, candidate_revision, demand_revision)
    return {
        "check_id": "CHK-126",
        "clear_length_m": ln_m,
        "clear_length_basis": ln_basis,
        "overstrength_factor": 1.4,
        **({"selection_basis": "ENGINEER_SELECTED_BEAM_AND_COLUMN"} if use_engineer_selection else {}),
        "axes": axes_out,
        **({"assigned_spectral": spectral} if spectral is not None else {}),
        "status": ("SCENARIO_VE_CALCULATED_NOT_PROVEN"
                   if all(axis["status"] == "SCENARIO_VE_CALCULATED_NOT_PROVEN" for axis in axes_out.values())
                   else "CAPACITY_SHEAR_INPUTS_UNRESOLVED"),
        "formal_compliance": "NOT_PROVEN",
    }


def _evaluate_engineer_column_selection(
    *,
    uid: str | None,
    source: Mapping[str, Any],
    geometry: Mapping[str, Any],
    axial: Mapping[str, Any],
    angle_deg: float | None,
    demand_revision: Mapping[str, Any] | None = None,
    additional_demands: Sequence[Mapping[str, Any]] = (),
    additional_shears: Sequence[Mapping[str, Any]] = (),
) -> tuple[dict[str, Any] | None, Section | None]:
    """Run deterministic engineer column rebar & Φ8/10 -> Φ10/Φ12 tie selection when configured."""
    if source.get("column_selection") is None or not uid:
        return None, None
    from ..column_engine.section_capacity import Material
    from .column_axial import _columns
    from .column_pmm_section import build_pmm_section
    from .rebar_selection import normalize_column_selection_policy, select_column_rebar

    col_policy = normalize_column_selection_policy(source.get("column_selection"))
    feature = source.get("column_axial") or {}
    pmm_source = feature.get("pmm_section_source")
    prefs = feature.get("design_preferences")
    rowset = (feature.get("force_source") or {}).get("rowsets", {}).get(uid)
    member = next((r for r in _columns(geometry) if r["element_id"] == uid), None)
    axial_member = next((r for r in axial.get("columns", ()) if r["element_id"] == uid), None)
    if not pmm_source or not prefs or rowset is None or not member or not axial_member:
        return {
            "schema": "tbdy.next.engineer-column-selection.v1",
            "member_id": uid,
            "policy": col_policy,
            "status": "ENGINEER_COLUMN_SELECTION_INPUTS_MISSING",
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
        }, None
    try:
        base_sec, ev = build_pmm_section(pmm_source, member, axial_member, prefs, include_layout=True)
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return {
            "schema": "tbdy.next.engineer-column-selection.v1",
            "member_id": uid,
            "policy": col_policy,
            "status": "ENGINEER_COLUMN_SELECTION_BLOCKED",
            "reason": str(exc),
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
        }, None

    tables = pmm_source.get("table_reads") or {}
    rebar_rows = (tables.get("Material Properties - Rebar Data") or {}).get("rows") or []
    tie_mat = next((r for r in rebar_rows if r.get("Material") == ev.get("tie_material_name")), None)
    fywk_mpa = (_float_or_none(tie_mat.get("Fy")) / 1000.0) if tie_mat and _float_or_none(tie_mat.get("Fy")) else ev.get("fy_mpa")
    gamma_c = float(ev["fck_mpa"]) / float(ev["fcd_mpa"])
    gamma_s = float(ev["gamma_s"])
    static_names = {
        c["name"]
        for c in (axial.get("combination_plan") or {}).get("combinations", ())
        if c.get("force_semantics") == "STATIC_SIGNED_VECTOR"
    }
    demand_vectors = []
    shear_demands = []
    from .alpha_iteration import revised_force_rows
    for row in sorted(revised_force_rows(rowset, uid, demand_revision), key=lambda r: (r[4], r[:4])):
        _, sta, _, _, combo, _, _, p, v2, v3, _, m2, m3 = row
        if combo not in static_names:
            continue
        nd = -float(p)
        demand_vectors.append({
            "combination": combo, "station_m": sta,
            "nd_kn": nd, "m2_knm": float(m2), "m3_knm": float(m3),
        })
        shear_demands.append({"nd_kn": nd, "v2_kn": float(v2), "v3_kn": float(v3)})

    shear_demands.extend(additional_shears)
    demand_vectors.extend(additional_demands)  # Same-run R08 constraints, not source mutations.
    res = select_column_rebar(
        t2_mm=base_sec.t2,
        t3_mm=base_sec.t3,
        cover_mm=float(ev["cover_to_tie_mm"]),
        fck_mpa=float(ev["fck_mpa"]),
        fcd_mpa=float(ev["fcd_mpa"]),
        fyd_mpa=float(ev["fyd_mpa"]),
        es_mpa=float(base_sec.material.es),
        fywk_mpa=float(fywk_mpa),
        gamma_c=gamma_c,
        gamma_s=gamma_s,
        local_axis_angle_deg=angle_deg,
        demand_vectors=demand_vectors,
        shear_demands=shear_demands,
        policy=col_policy,
    )
    res["member_id"] = uid
    res["policy"] = col_policy
    if demand_revision is not None:
        res["alpha_demand_revision_sha256"] = demand_revision["sha256"]
        res["r08_additional_constraint_count"] = len(additional_demands)
    sel_sec = None
    sel = res.get("selected")
    if sel and sel.get("num_bars_2_dir") and sel.get("selected_transverse"):
        tie_d = float(sel["selected_transverse"]["tie_diameter_mm"])
        bars, _, _ = perimeter(
            base_sec.t2, base_sec.t3, float(ev["cover_to_tie_mm"]),
            tie_d, float(sel["diameter_mm"]),
            n2=int(sel["num_bars_2_dir"]), n3=int(sel["num_bars_3_dir"]),
        )
        sel_sec = Section(
            base_sec.t2, base_sec.t3, bars,
            Material(float(ev["fck_mpa"]), float(ev["fcd_mpa"]), float(ev["fyd_mpa"]), float(base_sec.material.es)),
        )
    return res, sel_sec


def _assigned_seismic_combinations(axial: Mapping[str, Any]) -> list[str]:
    """Keep the assigned population independently of returned force rows."""
    plan = axial.get("combination_plan") or {}
    if plan.get("source") != "ASSIGNED_DESIGN" or not isinstance(plan.get("design_assignment"), Mapping):
        return []
    groups = plan["design_assignment"].get("groups") or {}
    return list(dict.fromkeys(name for group in ("ductile", "capacity") for name in groups.get(group, ())))


def _combo_roles(axial: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    plan = axial.get("combination_plan") or {}
    static_combos = [
        c["name"]
        for c in plan.get("combinations", ())
        if c.get("force_semantics") == "STATIC_SIGNED_VECTOR"
    ]
    seismic_set = set(_assigned_seismic_combinations(axial))
    seismic_combos = [c for c in static_combos if c in seismic_set]
    return static_combos, seismic_combos


def _projected_column_end_shear_kn(
    *,
    col_frame: Mapping[str, Any],
    pt_id: str,
    dir_unit: list[float],
    combo: str,
    rowset: Mapping[str, Any] | None,
    points: Mapping[str, list[float]],
) -> float | None:
    if rowset is None or not col_frame.get("axes_global"):
        return None
    uid = col_frame["frame_id"]
    try:
        rows = [r for r in native_frame_force_rows(rowset, uid) if r[4] == combo]
    except BankError:
        return None
    if not rows or any(r[5] not in ("Single Value", "") or r[6] != 0 for r in rows):
        return None
    pi, pj = col_frame.get("point_i"), col_frame.get("point_j")
    if pt_id not in (pi, pj) or pi not in points or pj not in points:
        return None
    # Native object endpoints are independent of the returned force population.
    # Nonzero physical face offsets are not inferred from the first/last row.
    try:
        length_m = math.dist(points[pi], points[pj])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(length_m) or length_m <= _GEOMETRY_TOL:
        return None
    sta = 0.0 if pi == pt_id else length_m
    cuts = [r for r in rows if abs(r[1] - sta) <= 1e-7]
    # A favorable deduction cannot be chosen from ambiguous element-side cuts.
    if len(cuts) != 1:
        return None
    c_axes = col_frame["axes_global"]
    row = cuts[0]
    return abs(float(row[8]) * _dot(c_axes[1], dir_unit) + float(row[9]) * _dot(c_axes[2], dir_unit))


def _attach_r13_joint_shear_and_transverse(
    *,
    end_rows: list[dict[str, Any]],
    frames: Mapping[str, Mapping[str, Any]],
    points: Mapping[str, list[float]],
    adjacency: Mapping[str, list[dict[str, Any]]],
    beam_by_id: Mapping[str, Mapping[str, Any]],
    force_rowsets: Mapping[str, Any],
    axial: Mapping[str, Any],
    eng_col_selections: Mapping[str, Mapping[str, Any]],
    transverse_by_uid: Mapping[str, Mapping[str, Any]],
    beam_sel_active: bool,
    col_sel_active: bool,
) -> None:
    """Attach R13 TBDY 7.5.2.1 joint shear Ve and 7.5.2.3 joint transverse checks when selected."""
    if not beam_sel_active and not col_sel_active:
        return
    _, seismic_combos = _combo_roles(axial)
    expected_seismic_combos = _assigned_seismic_combinations(axial)
    axial_by_id = {c["element_id"]: c for c in axial.get("columns", ())}

    for end_row in end_rows:
        if end_row.get("status") != "JOINT_GEOMETRIC_REFERENCES_CALCULATED":
            continue
        uid = end_row["member_id"]
        pt_id = end_row["point_id"]
        col_frame = frames.get(uid)
        if not col_frame or not col_frame.get("axes_global") or pt_id not in points:
            continue
        incident = adjacency.get(pt_id, ())
        lower_cols: list[Mapping[str, Any]] = []
        upper_cols: list[Mapping[str, Any]] = []
        topology_issues: list[str] = []
        for item in incident:
            if item["type"] != "Column":
                continue
            frame = frames.get(item["frame_id"])
            if frame is None:
                topology_issues.append(f"JOINT_COLUMN_FRAME_MISSING:{item['frame_id']}")
                continue
            pi, pj = frame.get("point_i"), frame.get("point_j")
            if pi == pt_id and pj != pt_id:
                other = pj
            elif pj == pt_id and pi != pt_id:
                other = pi
            else:
                topology_issues.append(f"JOINT_COLUMN_ENDPOINT_NOT_BOUND:{item['frame_id']}")
                continue
            try:
                side = physical_column_side_at_joint(points[pt_id], points.get(other), tolerance_m=_GEOMETRY_TOL)
            except BankError as exc:
                topology_issues.append(f"{exc}:{item['frame_id']}")
                continue
            (lower_cols if side == "LOWER" else upper_cols).append(frame)
        if len(lower_cols) > 1 or len(upper_cols) > 1:
            topology_issues.append("JOINT_UNIQUE_UPPER_LOWER_COLUMNS_NOT_BOUND")
        lower_uid = lower_cols[0]["frame_id"] if len(lower_cols) == 1 and not topology_issues else None

        faces = end_row.get("faces") or {}
        enclosure = end_row.get("enclosure_scenario")
        for axis_entry in end_row.get("axes", ()):
            calc = axis_entry.get("calculation")
            if calc is None:
                continue
            axis_key = axis_entry["axis"]
            axis_idx = 1 if axis_key == "V2" else 2
            face_pos, face_neg = f"{axis_idx + 1}+", f"{axis_idx + 1}-"
            dir_unit = col_frame["axes_global"][axis_idx]

            # 1) TBDY 7.5.2.1 Vj = 1.25 * fyk * (As1 + As2) - Vkol
            if beam_sel_active:
                face_terms: dict[str, dict[str, Any]] = {}
                missing_reason: str | None = None
                for fkey in (face_pos, face_neg):
                    finfo = faces.get(fkey)
                    if finfo is None:
                        face_terms[fkey] = {"present": False, "t_top_kn": 0.0, "t_bot_kn": 0.0, "as_top_mm2": 0.0, "as_bot_mm2": 0.0}
                        continue
                    b_entry = beam_by_id.get(finfo["frame_id"])
                    if not b_entry or not b_entry.get("horizontal_local2_up"):
                        missing_reason = f"BEAM_NOT_HORIZONTAL_OR_MISSING:{finfo['frame_id']}"
                        break
                    fyk_b = b_entry.get("fyk_mpa")
                    b_sel = ((b_entry.get("ends") or {}).get(finfo["native_end"]) or {}).get("engineer_selection") or {}
                    if b_sel.get("status") != "BEAM_SELECTED_CALCULATED" or not fyk_b:
                        missing_reason = f"BEAM_ENGINEER_SELECTION_UNBOUND:{finfo['frame_id']}"
                        break
                    as_t = float(b_sel["area_top_mm2"])
                    as_b = float(b_sel["area_bottom_mm2"])
                    face_terms[fkey] = {
                        "present": True,
                        "frame_id": finfo["frame_id"],
                        "native_end": finfo["native_end"],
                        "fyk_mpa": float(fyk_b),
                        "as_top_mm2": as_t,
                        "as_bot_mm2": as_b,
                        "t_top_kn": beam_steel_tension_kn(fyk_mpa=fyk_b, area_mm2=as_t),
                        "t_bot_kn": beam_steel_tension_kn(fyk_mpa=fyk_b, area_mm2=as_b),
                    }
                if missing_reason is None:
                    sway_a_t = face_terms[face_pos]["t_top_kn"] + face_terms[face_neg]["t_bot_kn"]
                    sway_b_t = face_terms[face_pos]["t_bot_kn"] + face_terms[face_neg]["t_top_kn"]
                    v_kol_kn = 0.0
                    roof_boundary = not upper_cols and bool(lower_cols) and not topology_issues
                    column_shear_cases: list[dict[str, Any]] = []
                    for combo in expected_seismic_combos:
                        case: dict[str, Any] = {
                            "combination": combo, "status": "COLUMN_SHEAR_UNBOUND",
                            "upper_shear_kn": None, "lower_shear_kn": None,
                            "deduction_kn": None, "missing_column_ids": [],
                        }
                        if roof_boundary:
                            case.update(status="ROOF_ZERO_BOUNDARY", upper_shear_kn=0.0, deduction_kn=0.0)
                        elif topology_issues or not upper_cols or not lower_cols:
                            case["status"] = "COLUMN_TOPOLOGY_UNBOUND"
                        elif combo not in seismic_combos:
                            # Retain assigned spectral/unclassified cases without treating
                            # their component extrema as signed column-shear deductions.
                            case["status"] = "STATIC_SIGNED_COMBINATION_NOT_BOUND"
                        else:
                            upper_values = {
                                c["frame_id"]: _projected_column_end_shear_kn(
                                    col_frame=c, pt_id=pt_id, dir_unit=dir_unit,
                                    combo=combo, rowset=force_rowsets.get(c["frame_id"]), points=points,
                                ) for c in upper_cols
                            }
                            lower_values = {
                                c["frame_id"]: _projected_column_end_shear_kn(
                                    col_frame=c, pt_id=pt_id, dir_unit=dir_unit,
                                    combo=combo, rowset=force_rowsets.get(c["frame_id"]), points=points,
                                ) for c in lower_cols
                            }
                            case["missing_column_ids"] = sorted(
                                cid for cid, value in (upper_values | lower_values).items() if value is None
                            )
                            if all(v is not None for v in upper_values.values()):
                                case["upper_shear_kn"] = math.fsum(upper_values.values())
                            if all(v is not None for v in lower_values.values()):
                                case["lower_shear_kn"] = math.fsum(lower_values.values())
                            if not case["missing_column_ids"]:
                                case.update(status="BOUND", deduction_kn=min(case["upper_shear_kn"], case["lower_shear_kn"]))
                        column_shear_cases.append(case)
                    missing_shear_combos = [c["combination"] for c in column_shear_cases if c["deduction_kn"] is None]
                    shear_scope_complete = bool(column_shear_cases) and not missing_shear_combos
                    if roof_boundary:
                        v_kol_basis = "ROOF_JOINT_NO_UPPER_COLUMN_VKOL_ZERO"
                    elif topology_issues or not upper_cols or not lower_cols:
                        v_kol_basis = "CONSERVATIVE_ZERO_VKOL_COLUMN_TOPOLOGY_UNBOUND"
                    elif not expected_seismic_combos:
                        v_kol_basis = "CONSERVATIVE_ZERO_VKOL_SEISMIC_CASES_UNBOUND"
                    elif not shear_scope_complete:
                        v_kol_basis = "CONSERVATIVE_ZERO_VKOL_INCOMPLETE_SEISMIC_SHEAR"
                    else:
                        # Every applicable case participates, including zero and sub-kN
                        # shears. Missing cases must never increase a favorable deduction.
                        v_kol_kn = min(c["deduction_kn"] for c in column_shear_cases)
                        v_kol_basis = "MIN_UPPER_LOWER_COLUMN_SHEAR"

                    ve_a = joint_shear_equilibrium_kn(beam_tension_kn=sway_a_t, column_shear_deduction_kn=v_kol_kn)
                    ve_b = joint_shear_equilibrium_kn(beam_tension_kn=sway_b_t, column_shear_deduction_kn=v_kol_kn)
                    ve_gov = max(ve_a, ve_b)
                    lim_kn = float(calc["geometric_limit_kn"])
                    axis_entry["joint_shear_ve"] = {
                        "code_ref": "TBDY 7.5.2.1 / Eq. 7.11",
                        "sway_a_tension_kn": sway_a_t,
                        "sway_b_tension_kn": sway_b_t,
                        "v_kol_used_kn": v_kol_kn,
                        "v_kol_basis": v_kol_basis,
                        "v_kol_applicability": "CONDITIONAL_NONNEGATIVE_DEDUCTION_FOR_QUALIFIED_SWAY_MECHANISM",
                        "target_axis": axis_key,
                        "global_direction": list(dir_unit),
                        "upper_column_ids": [c["frame_id"] for c in upper_cols],
                        "lower_column_ids": [c["frame_id"] for c in lower_cols],
                        "column_topology_issues": topology_issues,
                        "expected_seismic_combinations": expected_seismic_combos,
                        "column_shear_cases": column_shear_cases,
                        "missing_column_shear_combinations": missing_shear_combos,
                        "column_shear_scope_complete": shear_scope_complete,
                        "sway_a_ve_kn": ve_a,
                        "sway_b_ve_kn": ve_b,
                        "governing_ve_kn": ve_gov,
                        "geometric_limit_kn": lim_kn,
                        "utilization": ve_gov / lim_kn,
                        "within_geometric_limit": ve_gov <= lim_kn + 1e-6,
                        "faces": face_terms,
                        "status": "JOINT_SHEAR_VE_CALCULATED_NOT_PROVEN",
                        "formal_compliance": "NOT_PROVEN",
                    }
                else:
                    axis_entry["joint_shear_ve"] = {
                        "status": "JOINT_SHEAR_VE_UNBOUND",
                        "reason": missing_reason,
                        "formal_compliance": "NOT_PROVEN",
                    }

            # 2) TBDY 7.5.2.3 Joint transverse reinforcement (0.4 / 0.6 of lower column Ash/s)
            if col_sel_active and enclosure in ("ENCLOSED", "UNENCLOSED"):
                tie_result: dict[str, Any] = {
                    "status": "JOINT_TRANSVERSE_UNBOUND",
                    "reason": "JOINT_UNIQUE_LOWER_COLUMN_NOT_BOUND",
                    "target_axis": axis_key,
                    "global_direction": list(dir_unit),
                    "lower_column_id": lower_uid,
                    "lower_axis": None,
                    "axis_mapping_status": "NOT_BOUND",
                    "column_topology_issues": topology_issues,
                    "all_references_met": None,
                    "formal_compliance": "NOT_PROVEN",
                }
                axis_entry["joint_transverse_7_5_2_3"] = tie_result
                if lower_uid is None:
                    continue
                try:
                    lower_axis = physical_shear_axis(dir_unit, frames[lower_uid].get("axes_global"), tolerance=_GEOMETRY_TOL)
                except BankError as exc:
                    tie_result["reason"] = str(exc)
                    continue
                tie_result.update(lower_axis=lower_axis, axis_mapping_status="PHYSICAL_AXIS_BOUND",
                                  reason="JOINT_LOWER_CONFINEMENT_REFERENCE_NOT_BOUND")
                sel_col = (eng_col_selections.get(lower_uid) or {}).get("selected") or {}
                sel_tr = sel_col.get("selected_transverse") or {}
                conf_key = "confinement_" + lower_axis.lower()
                conf_lower = sel_tr.get(conf_key) or {}
                lower_ax = axial_by_id.get(lower_uid) or {}
                lower_t = transverse_by_uid.get(lower_uid) or {}
                if conf_lower and sel_tr.get("confinement_spacing_mm") and sel_tr.get("tie_diameter_mm"):
                    dims_l = frames[lower_uid].get("dims")
                    fck_l = _float_or_none(lower_ax.get("fck_mpa"))
                    n_max_l = _float_or_none(lower_ax.get("n_max_kn"))
                    axial_branch = "CONSERVATIVE_HIGH_AXIAL_REFERENCE_INPUTS_UNBOUND"
                    lower_req = conf_lower["high_axial_required_ash_mm2"]
                    if dims_l is not None and fck_l is not None and fck_l > 0 and n_max_l is not None:
                        threshold_kn = confinement_axial_threshold(
                            area_mm2=dims_l.local2_extent_mm * dims_l.local3_extent_mm, fck_mpa=fck_l,
                        )["axial_limit_kn"]
                        axial_branch = "HIGH_AXIAL_GT_0_2_AC_FCK"
                        if n_max_l <= threshold_kn:
                            axial_branch = "LOW_AXIAL_LE_0_2_AC_FCK"
                            lower_req = conf_lower["low_axial_required_ash_mm2"]
                    s_low = float(sel_tr["confinement_spacing_mm"])
                    ash_prop = float(conf_lower["ash_mm2"])
                    tie_d = float(sel_tr["tie_diameter_mm"])
                    tie_result.update({
                        "status": "JOINT_TRANSVERSE_REFERENCES_CALCULATED_NOT_PROVEN",
                        "reason": None,
                        "axial_branch": axial_branch,
                        "lower_column_has_confinement_calc": bool(lower_t),
                        **joint_transverse_reference(
                            lower_required_ash_mm2=lower_req,
                            lower_spacing_mm=s_low,
                            proposed_ash_mm2=ash_prop,
                            joint_spacing_mm=s_low,
                            tie_diameter_mm=tie_d,
                            enclosure=enclosure,
                        ),
                    })


def _evaluate_story_alpha_summary(
    *,
    evaluated_uids: Sequence[str],
    all_target_cols: Sequence[Mapping[str, Any]],
    frames: Mapping[str, Mapping[str, Any]],
    scwb_joints: Sequence[Mapping[str, Any]],
    force_rowsets: Mapping[str, Any],
    axial: Mapping[str, Any],
    use_engineer_selection: bool,
    dependency_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """TBDY 2018 §7.3.6.1 Eq. 7.4 story alpha_i = sum(V_is)/sum(V_ik) & 7.3.6.2 demand feedback."""
    static_combos, seismic_combos = _combo_roles(axial)
    target_combos = seismic_combos  # No gravity fallback for TBDY 7.3.6.
    if not target_combos or not all_target_cols or not scwb_joints:
        return None

    evaluated_set = set(evaluated_uids)
    # Map (col_id, direction) -> list of joint SCWB entries along that direction
    scwb_by_col_dir: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for j in scwb_joints:
        scwb_by_col_dir[(j["target_member_id"], j["direction"])].append(j)

    cols_by_story: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for c in all_target_cols:
        story = str(c.get("story") or "UNKNOWN")
        cols_by_story[story].append(c)

    stories_out: list[dict[str, Any]] = []
    any_partial_scope = False
    min_alpha_global: float | None = None
    max_demand_factor_global: float | None = None
    any_below_070 = False

    for story in sorted(cols_by_story):
        st_cols = cols_by_story[story]
        eval_in_story = [c["frame_id"] for c in st_cols if c["frame_id"] in evaluated_set]
        if not eval_in_story:
            continue
        full_story_denom = len(eval_in_story) == len(st_cols)
        if not full_story_denom:
            any_partial_scope = True

        if dependency_plan is not None:
            from .design_dependencies import story_blockers
            blocked = story_blockers(dependency_plan, story)
            if blocked:
                for direction in ("X", "Y"):
                    stories_out.append({
                        "story": story, "direction": direction, "story_column_count": len(st_cols),
                        "evaluated_column_count": len(eval_in_story),
                        "denominator_status": "FULL_STORY_COLUMN_DENOMINATOR",
                        "status": "BLOCKED_DEPENDENCY", "execution_status": "NOT_RUN",
                        "governing_combination": None, "governing_alpha_i": None, "governing_band": None,
                        "moment_magnification_factor_7_3_6_2": None,
                        "demand_feedback_action": "BLOCKED_DEPENDENCY", "reason_codes": blocked,
                        "cases": [{"combination": combo, "execution_status": "NOT_RUN",
                                   "reason_codes": blocked} for combo in target_combos],
                    })
                continue
        for direction, dir_vec in (("X", [1.0, 0.0, 0.0]), ("Y", [0.0, 1.0, 0.0])):
            combo_rows: list[dict[str, Any]] = []
            for combo in target_combos:
                vik = 0.0
                vis = 0.0
                missing_force_cols: list[str] = []
                unknown_scwb_cols: list[str] = []
                for col in st_cols:
                    cid = col["frame_id"]
                    axes = col.get("axes_global")
                    rowset = force_rowsets.get(cid)
                    if axes is None or rowset is None:
                        missing_force_cols.append(cid)
                        continue
                    f_rows = [r for r in native_frame_force_rows(rowset, cid) if r[4] == combo and r[6] == 0]
                    if not f_rows:
                        missing_force_cols.append(cid)
                        continue
                    idx_x = 0 if direction == "X" else 1
                    col_v = max(
                        abs(float(r[8]) * axes[1][idx_x] + float(r[9]) * axes[2][idx_x])
                        for r in f_rows
                    )
                    vik += col_v
                    # SCWB compliance on both column ends in this direction and combo
                    j_list = scwb_by_col_dir.get((cid, direction), [])
                    if cid not in evaluated_set:
                        unknown_scwb_cols.append(cid)
                        continue
                    if not j_list:
                        # No beam framing along `direction` at either end of this column
                        vis += col_v
                        continue
                    col_ok = True
                    col_unknown = False
                    for j in j_list:
                        src_blk = (j.get("engineer_selected_scwb") or {}) if use_engineer_selection else j
                        c_rows = [cr for cr in (src_blk.get("cases") or ()) if cr.get("output_case") == combo]
                        if not c_rows or any(cr.get("reference_satisfied") is None for cr in c_rows):
                            col_unknown = True
                            break
                        if not all(cr["reference_satisfied"] for cr in c_rows):
                            col_ok = False
                    if col_unknown:
                        unknown_scwb_cols.append(cid)
                    elif col_ok:
                        vis += col_v

                if vik <= 1e-6 or missing_force_cols:
                    continue
                ref = evaluate_story_alpha_reference(vis_kn=vis, vik_kn=vik)
                alpha_val = float(ref["alpha"])
                if not unknown_scwb_cols:
                    min_alpha_global = alpha_val if min_alpha_global is None else min(min_alpha_global, alpha_val)
                    if alpha_val < 0.70:
                        any_below_070 = True
                    elif alpha_val < 1.0:
                        fac = 1.0 / alpha_val
                        max_demand_factor_global = fac if max_demand_factor_global is None else max(max_demand_factor_global, fac)
                    else:
                        max_demand_factor_global = 1.0 if max_demand_factor_global is None else max(max_demand_factor_global, 1.0)
                combo_rows.append({
                    "combination": combo,
                    "vis_kn": vis,
                    "vik_kn": vik,
                    "alpha_i": alpha_val,
                    "limit": float(ref["limit"]),
                    "numeric_status": ref["numeric_status"],
                    "classification_review_required": ref["classification_review_required"],
                    "moment_magnification_factor_7_3_6_2": (
                        None if unknown_scwb_cols
                        else (1.0 if alpha_val >= 1.0 else (1.0 / alpha_val if alpha_val >= 0.70 else None))
                    ),
                    "demand_feedback_action": (
                        "PARTIAL_STORY_SCOPE_UNKNOWN_OTHER_COLUMNS"
                        if unknown_scwb_cols
                        else (
                            "NONE"
                            if alpha_val >= 1.0
                            else (
                                "AMPLIFY_COLUMN_DEMANDS_BY_1_OVER_ALPHA"
                                if alpha_val >= 0.70
                                else "STORY_SCWB_BELOW_0_70_SYSTEM_R_AND_DUCTILITY_REVIEW_REQUIRED"
                            )
                        )
                    ),
                    "unknown_scwb_columns": unknown_scwb_cols,
                })
            if combo_rows:
                worst = min(combo_rows, key=lambda r: r["alpha_i"])
                stories_out.append({
                    "story": story,
                    "direction": direction,
                    "story_column_count": len(st_cols),
                    "evaluated_column_count": len(eval_in_story),
                    "denominator_status": "FULL_STORY_COLUMN_DENOMINATOR" if full_story_denom else "SINGLE_COLUMN_PARTIAL_STORY_SCOPE",
                    "governing_combination": worst["combination"],
                    "governing_alpha_i": worst["alpha_i"],
                    "governing_band": worst["numeric_status"],
                    "moment_magnification_factor_7_3_6_2": worst["moment_magnification_factor_7_3_6_2"],
                    "demand_feedback_action": worst["demand_feedback_action"],
                    "cases": combo_rows,
                })

    if not stories_out:
        return None
    return {
        "schema": "tbdy.next.story-alpha-7-3-6.v1",
        "code_ref": "TBDY 2018 §7.3.6.1 / Eq. 7.4 / §7.3.6.2",
        "selection_basis": "ENGINEER_SELECTED_SCWB" if use_engineer_selection else "SCENARIO_SCWB",
        "denominator_scope": "SINGLE_COLUMN_PARTIAL_STORY_SCOPE" if any_partial_scope else "FULL_STORY_COLUMN_DENOMINATOR",
        "minimum_resolved_alpha_i": min_alpha_global,
        "max_column_demand_magnification_1_over_alpha": max_demand_factor_global,
        "any_story_below_0_70": any_below_070,
        "stories": stories_out,
        "formal_compliance": "NOT_PROVEN",
    }


def _evaluate_single_member_r10_details(
    *,
    uid: str,
    frames: Mapping[str, dict[str, Any]],
    points: dict[str, list[float]],
    adjacency: dict[str, list[dict[str, Any]]],
    source: Mapping[str, Any],
    geometry: Mapping[str, Any],
    axial: Mapping[str, Any],
    end_rows: Sequence[Mapping[str, Any]],
    beam_live: Mapping[str, Any] | None,
    eng_col_res: Mapping[str, Any] | None,
    eng_col_sections: Mapping[str, Any],
    col_sections_cache: dict[str, tuple[Any, dict]],
    beam_sel_active: bool,
    pmm_single: Mapping[str, Any] | None,
    dependency_plan: Mapping[str, Any] | None = None,
    demand_revision: Mapping[str, Any] | None = None,
    low_axial_by_joint: Mapping[str, Any] | None = None,
    spectral_context: Mapping[str, Any] | None = None,
    physical_length: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    angle_deg = member_local_axis_angle_deg(source, uid)
    scwb_joints = _evaluate_scwb_at_joint_ends(
        uid, dict(frames), points, adjacency, source, axial, pmm_single or {}, geometry,
        beam_live=beam_live,
        engineer_col_section=eng_col_sections.get(uid),
        engineer_col_sections=eng_col_sections,
        col_sections_cache=col_sections_cache, dependency_plan=dependency_plan, low_axial_by_joint=low_axial_by_joint,
    )
    transverse_shear = _evaluate_column_shear_and_confinement_for_id(uid, source, geometry, axial, demand_revision=demand_revision)
    dependency_blockers = []
    if dependency_plan is not None:
        from .design_dependencies import member_joint_blockers
        dependency_blockers = member_joint_blockers(dependency_plan, uid)
    capacity_ve = (
        _column_capacity_shear_ve(
            uid=uid, col_frame=frames.get(uid), scwb_joints=scwb_joints,
            transverse_shear=transverse_shear, source=source, geometry=geometry, axial=axial,
            demand_revision=demand_revision, physical_length=physical_length,
        )
        if transverse_shear and not dependency_blockers
        else None
    )
    eng_capacity_ve = None
    if transverse_shear and not dependency_blockers and (eng_col_res and eng_col_res.get("selected") or beam_sel_active):
        eng_capacity_ve = _column_capacity_shear_ve(
            uid=uid, col_frame=frames.get(uid), scwb_joints=scwb_joints,
            transverse_shear=transverse_shear, source=source, geometry=geometry, axial=axial, demand_revision=demand_revision,
            engineer_col_section=eng_col_sections.get(uid),
            engineer_column_selection=eng_col_res,
            use_engineer_selection=True,
            spectral_context=spectral_context, physical_length=physical_length,
            candidate_revision=((dependency_plan or {}).get("members", {}).get(uid) or {}).get("candidate_revision_sha256"),
        )
    if transverse_shear is not None:
        if dependency_blockers:
            transverse_shear["capacity_shear_dependency"] = {
                "status": "BLOCKED_DEPENDENCY", "execution_status": "NOT_RUN", "reason_codes": dependency_blockers,
            }
        transverse_shear["capacity_shear_ve"] = capacity_ve
        if eng_capacity_ve is not None:
            transverse_shear["engineer_capacity_shear_ve"] = eng_capacity_ve
        if capacity_ve is not None:
            transverse_shear["ve_status"] = capacity_ve["status"]
    dims = frames[uid]["dims"] if uid in frames else None
    global_moments = _global_pmm_moment_projection(pmm_single, dims, angle_deg)
    return {
        "member_id": uid,
        "local_axis_angle_deg": angle_deg,
        "global_moment_projections": global_moments,
        "member_joint_ends": [r for r in end_rows if r["member_id"] == uid],
        "scwb_joints": scwb_joints,
        "column_transverse_and_shear": transverse_shear,
        **({"engineer_column_selection": eng_col_res} if eng_col_res is not None else {}),
    }


def project_column_r10_live(
    source: Mapping[str, Any],
    geometry: Mapping[str, Any] | None,
    axial: Mapping[str, Any] | None,
    pmm: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
    *,
    beam_live: Mapping[str, Any] | None = None,
    target_member_ids: Sequence[str] | None = None,
    selected_cages_out: MutableMapping[str, SelectedColumnCage] | None = None,
    dependency_plan: Mapping[str, Any] | None = None,
    demand_revision: Mapping[str, Any] | None = None,
    previous_result: Mapping[str, Any] | None = None,
    previous_cages: Mapping[str, SelectedColumnCage] | None = None,
    reselect_member_ids: Sequence[str] | None = None,
    additional_demands: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    additional_shears: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    pmm_scope: Mapping[str, Any] | None = None,
    mixed_components: Mapping[str, Any] | None = None,
    input_sha: str | None = None,
) -> dict[str, Any] | None:
    """Deterministic R10-R13 projection (joints, 7.5 Ve/7.5.2.3, SCWB, story alpha_i, shear/Ve)."""
    if dependency_plan is not None:
        from .design_dependencies import verify_dependency_source
        verify_dependency_source(dependency_plan, source)
    if demand_revision is not None:
        from .alpha_iteration import validate_record, DEMAND_SCHEMA
        from .design_scenario import _digest
        validate_record(demand_revision, DEMAND_SCHEMA)
        if (dependency_plan is None or demand_revision["input_sha256"] != dependency_plan["input_sha256"]
                or demand_revision["source_payload_sha256"] != _digest(source)):
            raise ValueError("ALPHA_DEMAND_SOURCE_MISMATCH")
    if previous_result is not None:
        if dependency_plan is None or reselect_member_ids is None:
            raise ValueError("ALPHA_REUSE_CONTEXT_REQUIRED")
        from .design_dependencies import verify_dependency_source
        verify_dependency_source(previous_result.get("member_dependencies") or {}, source)
        from .design_scenario import _digest
        prior_factors = previous_result.get("alpha_demand_factors") or {}
        next_factors = (demand_revision or {}).get("factors") or {}
        for uid in set(prior_factors) | set(next_factors):
            if prior_factors.get(uid) != next_factors.get(uid) and uid not in reselect_member_ids:
                raise ValueError("ALPHA_CHANGED_DEMAND_OMITTED_FROM_RESELECTION:" + uid)
        for uid, cage in (previous_cages or {}).items():
            if (cage.input_sha256 != dependency_plan["input_sha256"]
                    or cage.candidate_sha256 != _digest({"selection": cage.selection, "section": asdict(cage.section)})):
                raise ValueError("ALPHA_PREVIOUS_CAGE_REVISION_INVALID:" + uid)
    if selected_cages_out:
        raise ValueError("R10_SELECTED_CAGE_OUTPUT_MUST_BE_EMPTY")
    if axial is None or geometry is None or "column_axial" not in source:
        return None
    if beam_live is None:
        r10_src = (source.get("column_axial") or {}).get("r10_source") or {}
        reads = r10_src.get("table_reads") or {}
        if BEAM_DESIGN_SUMMARY in reads or BEAM_REINFORCING in reads:
            from .beam_r10_live import project_beam_r10_live
            beam_live = project_beam_r10_live(source, geometry, axial, pmm, extra)

    frames, points, graph_meta = _build_frame_catalog(source)
    adjacency = graph_meta.pop("adjacency")
    from .scwb_axial import joint_low_axial_decisions
    low_axial_by_joint = joint_low_axial_decisions(
        source, axial, pmm_scope, mixed_components, dependency_plan, frames, points, adjacency,
        _assigned_seismic_combinations(axial), input_sha=input_sha)
    fck_map = _materials_fck(extra)

    target_cols = [
        frames[c["element_id"]]
        for c in axial.get("columns", ())
        if c.get("status") != "NOT_APPLICABLE" and c.get("element_id") in frames
    ]
    end_rows = [
        _evaluate_joint_end(col, end, frames, points, adjacency, fck_map)
        for col in target_cols
        for end in ("I", "J")
    ]
    pmm_id = (pmm or {}).get("member_id")
    pmm_members_map: dict[str, Mapping[str, Any]] = {}
    if pmm:
        if pmm.get("scope") == "ALL_COLUMNS" or pmm_id == "ALL":
            for m_res in pmm.get("members") or ():
                if m_res.get("member_id"):
                    pmm_members_map[m_res["member_id"]] = m_res
        elif pmm_id:
            pmm_members_map[pmm_id] = pmm

    if target_member_ids is not None:
        eval_uids = [u for u in target_member_ids if u in frames]
    elif pmm_members_map:
        eval_uids = [c["frame_id"] for c in target_cols if c["frame_id"] in pmm_members_map]
    else:
        eval_uids = []

    is_all_mode = bool(pmm and (pmm.get("scope") == "ALL_COLUMNS" or pmm_id == "ALL")) or (target_member_ids is not None)
    eng_col_selections: dict[str, dict[str, Any]] = {}
    eng_col_sections: dict[str, Section] = {}
    reselect = set(eval_uids if reselect_member_ids is None else reselect_member_ids)
    if reselect - set(eval_uids):
        raise ValueError("ALPHA_RESELECT_MEMBER_OUTSIDE_SCOPE")
    if source.get("column_selection") is not None and eval_uids:
        for uid in eval_uids:
            if dependency_plan is not None and not (dependency_plan["members"].get(uid) or {}).get("source_execution_allowed"):
                continue
            if previous_result is not None and uid not in reselect:
                cage = (previous_cages or {}).get(uid)
                if cage is not None:
                    eng_col_selections[uid], eng_col_sections[uid] = cage.selection, cage.section
                continue
            ang = member_local_axis_angle_deg(source, uid)
            e_res, e_sec = _evaluate_engineer_column_selection(
                uid=uid, source=source, geometry=geometry, axial=axial, angle_deg=ang,
                demand_revision=demand_revision, additional_demands=(additional_demands or {}).get(uid, ()),
                additional_shears=(additional_shears or {}).get(uid, ()),
            )
            if e_res is not None:
                eng_col_selections[uid] = e_res
            if e_sec is not None:
                eng_col_sections[uid] = e_sec

    if dependency_plan is not None:
        from .design_dependencies import bind_joint_candidates
        dependency_plan = bind_joint_candidates(dependency_plan, eng_col_sections, eng_col_selections, beam_live)
    from .column_spectral_shear import shear_context
    from .column_clear_length import project_column_clear_lengths
    from .confinement_regions import column_confinement
    spectral_context = shear_context(source, axial, pmm_scope, mixed_components, dependency_plan, input_sha)
    physical_lengths = project_column_clear_lengths(source, frames, adjacency, eval_uids, pmm_scope)
    by_member_length = (physical_lengths or {}).get("per_member", {})
    beam_by_id = {b["member_id"]: b for b in (beam_live or {}).get("beams") or ()}
    beam_sel_active = bool((beam_live or {}).get("beam_selection_policy"))
    col_sel_active = source.get("column_selection") is not None
    col_sections_cache: dict[str, tuple[Any, dict]] = {}

    affected = set(eval_uids) if previous_result is None else set(reselect)
    if dependency_plan is not None and previous_result is not None:
        for joint in dependency_plan["joints"].values():
            if set(joint["column_ids"]) & reselect:
                affected.update(joint["column_ids"])
    per_member: dict[str, dict[str, Any]] = {}
    all_scwb_joints: list[dict[str, Any]] = []
    transverse_by_uid: dict[str, dict[str, Any]] = {}
    for uid in eval_uids:
        if dependency_plan is not None and not (dependency_plan["members"].get(uid) or {}).get("source_execution_allowed"):
            from .design_dependencies import blocked_member_result
            per_member[uid] = {**blocked_member_result(uid, dependency_plan["members"][uid]["reason_codes"], schema=SCHEMA),
                              "member_joint_ends": [r for r in end_rows if r["member_id"] == uid],
                              "scwb_joints": [], "column_transverse_and_shear": None, "global_moment_projections": []}
            continue
        if previous_result is not None and uid not in affected:
            det = (previous_result.get("per_member") or {}).get(uid)
            if det is None:
                raise ValueError("ALPHA_PREVIOUS_MEMBER_RESULT_MISSING:" + uid)
            per_member[uid] = det
            all_scwb_joints.extend(det["scwb_joints"])
            if det["column_transverse_and_shear"]:
                transverse_by_uid[uid] = det["column_transverse_and_shear"]
            continue
        det = _evaluate_single_member_r10_details(
            uid=uid, frames=frames, points=points, adjacency=adjacency, source=source,
            geometry=geometry, axial=axial, end_rows=end_rows, beam_live=beam_live,
            eng_col_res=eng_col_selections.get(uid), eng_col_sections=eng_col_sections,
            col_sections_cache=col_sections_cache, beam_sel_active=beam_sel_active,
            pmm_single=pmm_members_map.get(uid), dependency_plan=dependency_plan, demand_revision=demand_revision,
            low_axial_by_joint=low_axial_by_joint,
            spectral_context=spectral_context, physical_length=by_member_length.get(uid),
        )
        if source.get("building_design") is not None:
            det["confinement_regions"] = column_confinement(uid, det, by_member_length.get(uid))
        per_member[uid] = det
        all_scwb_joints.extend(det["scwb_joints"])
        if det["column_transverse_and_shear"]:
            transverse_by_uid[uid] = det["column_transverse_and_shear"]

    # R13: Joint shear Ve (7.5.2.1) & joint transverse reinforcement (7.5.2.3) on target ends
    feature = source.get("column_axial") or {}
    force_rowsets = (feature.get("force_source") or {}).get("rowsets") or {}
    eval_uid_set = set(eval_uids)
    target_end_rows = [r for r in end_rows if r["member_id"] in eval_uid_set] if eval_uid_set else []
    if dependency_plan is not None:
        from .design_dependencies import joint_blockers
        for row in target_end_rows:
            codes = joint_blockers(dependency_plan, row["point_id"])
            row["design_dependency"] = {"status": "BLOCKED_DEPENDENCY" if codes else "REFERENCE_INPUTS_BOUND",
                                        "reason_codes": codes}
        target_end_rows = [row for row in target_end_rows if not joint_blockers(dependency_plan, row["point_id"])]
    if previous_result is not None:
        target_end_rows = [r for r in target_end_rows if r["member_id"] in affected]
    if target_end_rows and (beam_sel_active or col_sel_active):
        _attach_r13_joint_shear_and_transverse(
            end_rows=target_end_rows, frames=frames, points=points, adjacency=adjacency,
            beam_by_id=beam_by_id, force_rowsets=force_rowsets, axial=axial,
            eng_col_selections=eng_col_selections, transverse_by_uid=transverse_by_uid,
            beam_sel_active=beam_sel_active, col_sel_active=col_sel_active,
        )

    # R11: Story alpha_i & demand feedback (TBDY 7.3.6.1 / 7.3.6.2)
    story_alpha = _evaluate_story_alpha_summary(
        evaluated_uids=eval_uids,
        all_target_cols=target_cols,
        frames=frames,
        scwb_joints=all_scwb_joints,
        force_rowsets=force_rowsets,
        axial=axial,
        use_engineer_selection=beam_sel_active, dependency_plan=dependency_plan,
    )

    narrow_ends = [
        {k: r[k] for k in ("member_id", "label", "story", "end", "point_id", "narrow_faces", "enclosure_scenario")}
        for r in end_rows if r["narrow_faces"]
    ]
    single_det = per_member.get(pmm_id) if (not is_all_mode and pmm_id) else None
    angle_deg = single_det["local_axis_angle_deg"] if single_det else member_local_axis_angle_deg(source, pmm_id if not is_all_mode else None)
    global_moments = single_det["global_moment_projections"] if single_det else []
    pmm_ends = single_det["member_joint_ends"] if single_det else []
    transverse_shear = single_det["column_transverse_and_shear"] if single_det else None
    eng_col_res = single_det.get("engineer_column_selection") if single_det else None

    if demand_revision is not None:
        for uid in affected:
            if uid in per_member:
                per_member[uid]["alpha_joint_recheck_basis"] = "ORIGINAL_EQUILIBRIUM_VKOL_NOT_AMPLIFIED_SUBTRACTION"
                per_member[uid]["alpha_joint_recheck_open_gate"] = "JOINT_EQUILIBRIUM_AFTER_ALPHA_REVIEW_REQUIRED"
    if selected_cages_out is not None:
        for uid, section in eng_col_sections.items():
            selection = eng_col_selections.get(uid)
            if selection and selection.get("member_id") == uid and selection.get("selected"):
                selected_cages_out[uid] = SelectedColumnCage(
                    selection=selection, section=section,
                    input_sha256=dependency_plan["input_sha256"] if dependency_plan is not None else None,
                    candidate_sha256=(dependency_plan["members"][uid]["candidate_revision_sha256"]
                                      if dependency_plan is not None else None),
                )

    return {
        "schema": SCHEMA,
        **({"alpha_recalculation": {"selected_member_ids": sorted(reselect), "joint_consumer_member_ids": sorted(affected)}} if previous_result is not None else {}),
        **({"alpha_demand_factors": demand_revision["factors"]} if demand_revision is not None else {}),
        "scope": "ALL_COLUMNS" if is_all_mode else "SINGLE_COLUMN",
        "member_id": pmm_id,
        "evaluated_column_ids": ([uid for uid in eval_uids if dependency_plan["members"][uid]["source_execution_allowed"]]
                                 if dependency_plan is not None else eval_uids),
        **({"expected_column_ids": eval_uids, "member_dependencies": dependency_plan} if dependency_plan is not None else {}),
        "local_axis_angle_deg": angle_deg,
        "global_moment_projections": global_moments,
        "graph": graph_meta,
        "joint_end_count": len(end_rows),
        "joint_status_counts": dict(sorted(Counter(r["status"] for r in end_rows).items())),
        "enclosure_counts": dict(sorted(Counter(r["enclosure_scenario"] for r in end_rows if r["enclosure_scenario"]).items())),
        "narrow_beam_joint_count": len(narrow_ends),
        "narrow_beam_joints": narrow_ends,
        "member_joint_ends": pmm_ends,
        "scwb_joints": all_scwb_joints,
        "column_transverse_and_shear": transverse_shear,
        **({"engineer_column_selection": eng_col_res} if eng_col_res is not None else {}),
        **({"story_alpha": story_alpha} if story_alpha is not None else {}),
        **({"physical_clear_lengths": physical_lengths} if physical_lengths is not None else {}),
        **({"per_member": per_member} if is_all_mode else {}),
        "open_basis": [
            "ACTUAL_OR_SELECTED_BEAM_END_REINFORCEMENT_NOT_BOUND",
            "PHYSICAL_JOINT_FACES_INSERTION_OFFSETS_AND_RELEASES_NOT_PROVEN",
            "CAPACITY_DESIGN_VE_AND_EARTHQUAKE_COMPATIBLE_ND_NOT_BOUND",
            "HOOK_ANCHORAGE_AND_3D_CONGESTION_NOT_PROVEN",
        ],
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
