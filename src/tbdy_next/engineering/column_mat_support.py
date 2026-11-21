"""Bind horizontal foundation restraints and same-case supported joint drift for R08."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from math import cos, isfinite, radians, sin
from typing import Mapping

from ..etabs_geometry import POINT_RESTRAINT_SCHEMA
from ..quick_checks import _rows
from ..story_drift_binding import _verify_generic_capture

BOUND = "MAT_HORIZONTAL_BOUNDARY_VERIFIED"
SPECTRAL_CASES = {"RSX": ("X", "Ux"), "RSY": ("Y", "Uy")}


def _global_restrained(flags, angles):
    # CSI's intrinsic rotations are about 3, then the new 2, then the new 1.
    a, b, c = map(radians, angles)
    sa, sb, sc = sin(a), sin(b), sin(c)
    ca, cb, cc = cos(a), cos(b), cos(c)
    global_rows = (
        (ca * cb, ca * sb * sc - sa * cc, ca * sb * cc + sa * sc),
        (sa * cb, sa * sb * sc + ca * cc, sa * sb * cc - ca * sc),
        (-sb, cb * sc, cb * cc),
    )
    # A global component is restrained only if every local free axis has zero
    # projection onto it. The same basis maps translations and rotations.
    return {
        dof: all(flags[start + i] or abs(cosine) <= 1e-12 for i, cosine in enumerate(row))
        for start, names in ((0, ("UX", "UY", "UZ")), (3, ("RX", "RY", "RZ")))
        for dof, row in zip(names, global_rows)
    }


def _read_displacements(source, point_ids):
    capture = source.get("vs05_delta_source") or {}
    try:
        model = (source.get("capture_metadata") or {}).get("model_filename")
        if (not model or capture.get("model") != model or capture.get("model_locked") is not True
                or capture.get("model_units_code") != 6 or capture.get("model_units_unchanged") is not True
                or capture.get("selection_restored") is not True
                or capture.get("case_selection_before") != capture.get("case_selection_after")):
            raise ValueError("Joint displacement capture session is unbound")
        _verify_generic_capture(capture)
        name = "Joint Displacements"
        tables = capture["table_reads"]
        required = {"UniqueName", "OutputCase", "CaseType", "StepType", "StepNumber", "Ux", "Uy"}
        rows = _rows({"tables": tables}, name, required)
        units = tables[name]["field_metadata"]["units_by_field"]
        if units["Ux"] != "m" or units["Uy"] != "m":
            raise ValueError("Joint displacement units must be m")
        by_point_case = defaultdict(list)
        for row in rows:
            point, case = row["UniqueName"], row["OutputCase"]
            if point in point_ids and case in SPECTRAL_CASES:
                by_point_case[point, case].append(row)
        return by_point_case, None
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return {}, str(exc)


def _spectral_drift(rows, i, j):
    """A zero restrained base permits the upper response without envelope subtraction."""
    references = {}
    missing = []
    conflicts = []
    for case, (direction, key) in SPECTRAL_CASES.items():
        try:
            base, = rows.get((i, case), ())
            upper, = rows.get((j, case), ())
            native_step = (base["StepType"], base["StepNumber"])
            if (base["CaseType"] != "LinRespSpec" or upper["CaseType"] != "LinRespSpec"
                    or native_step != (upper["StepType"], upper["StepNumber"])
                    or native_step[0] != "Max"):
                raise ValueError("Unbound native response-spectrum step")
            values = [Decimal(base[k]) for k in ("Ux", "Uy")]
            if not all(x.is_finite() for x in values):
                raise ValueError("Nonfinite base displacement")
            if any(x != 0 for x in values):
                conflicts.append(case)
                continue
            top = Decimal(upper[key])
            if not top.is_finite() or top < 0:
                raise ValueError("Invalid upper displacement envelope")
            references[direction] = {"case": case, "component": key, "step_type": native_step[0],
                                      "step_number": native_step[1], "base_m": 0.0, "upper_m": float(top),
                                      "relative_m": float(top), "basis": "ZERO_BASE_SPECTRAL_RESPONSE"}
        except (ValueError, KeyError, TypeError, ArithmeticError):
            missing.append(case)
    return references, missing, conflicts


def project_mat_horizontal_supports(source, physical_members):
    """Match only the verified mat contacts in the current model, by native joint UID."""
    r10 = (source.get("column_axial") or {}).get("r10_source") or {}
    captured = r10.get("point_restraints")
    if not isinstance(captured, Mapping):
        return {}  # Older sealed runs do not contain the native support read.
    members = {uid: row["mat_contact"] for uid, row in physical_members.items() if row.get("mat_contact")}
    if not members:
        return {}
    point_ids = {contact[k] for contact in members.values() for k in ("base_joint_id", "upper_joint_id")}
    displacements, displacement_error = _read_displacements(source, point_ids)
    observed = captured.get("observations") or {}
    errors = captured.get("errors") or {}
    roster = captured.get("point_ids") or []
    valid_capture = (isinstance(observed, Mapping) and isinstance(errors, Mapping) and isinstance(roster, list)
                     and all(isinstance(uid, str) and uid for uid in roster)
                     and captured.get("schema") == POINT_RESTRAINT_SCHEMA
                     and r10.get("model_locked_before") is True and r10.get("model_locked_after") is True
                     and r10.get("units_before") == r10.get("units_after") == 6
                     and len(roster) == len(set(roster))
                     and set(roster) == observed.keys() | errors.keys()
                     and not observed.keys() & errors.keys())
    result = {}
    for uid, contact in sorted(members.items()):
        base, upper = contact["base_joint_id"], contact["upper_joint_id"]
        row = result[uid] = {"status": "MAT_HORIZONTAL_BOUNDARY_UNRESOLVED", **contact,
                             "model_role": "NATIVE_POINT_RESTRAINT"}
        record = observed.get(base) if valid_capture else None
        if not isinstance(record, Mapping):
            row["reason"] = (errors.get(base) if valid_capture else None) or "NATIVE_POINT_RESTRAINT_NOT_BOUND"
            continue
        flags, angles = record.get("local_dof"), record.get("axes_angles_deg")
        if (not isinstance(flags, list) or len(flags) != 6 or any(type(x) is not bool for x in flags)
                or record.get("advanced_axes") is not False
                or not isinstance(angles, list) or len(angles) != 3
                or any(type(a) not in (int, float) or not isfinite(a) for a in angles)):
            row["reason"] = "POINT_RESTRAINT_GLOBAL_AXES_UNVERIFIED"
            continue
        row["global_dof_restrained"] = global_dof = _global_restrained(flags, angles)
        if not (global_dof["UX"] and global_dof["UY"]):
            row["reason"] = "HORIZONTAL_X_AND_Y_RESTRAINT_REQUIRED"
            continue
        values, missing, conflicts = _spectral_drift(displacements, base, upper)
        row.update(spectral_joint_reference=values, missing_spectral_cases=missing)
        if displacement_error:
            row["displacement_source_error"] = displacement_error
        if conflicts:
            row.update(reason="NONZERO_RESTRAINED_BASE_DISPLACEMENT", conflicting_cases=conflicts)
            continue
        row["status"] = BOUND
    return result
