"""Read signed linear-static shell corner actions needed by the wall batch, using the existing connection."""

from collections import defaultdict
from math import isfinite

from .engineering.wall_transition_shell import SCHEMA, native_plan
from .etabs_source_gateway_windows import (
    SourceError,
    get_results_setup_state,
    restore_results_setup_state,
    seal,
)
from .frame_force_capture import _catalog_names
from .wall_modal_capture import _native, _point_basis


def _shell_fields(sap, uid, pairs, cases):
    """CSI AreaForceShell returns unaveraged element-corner resultants per unit length."""
    n, *columns = _native(
        sap.Results.AreaForceShell(uid, 0, 0, *([] for _ in range(23))), "AreaForceShell " + uid
    )
    if len(columns) != 23 or any(len(c) != n for c in columns):
        raise SourceError("UNEXPECTED_AREA_FORCE_SHELL_ABI:" + uid)
    indexed = defaultdict(dict)
    for row in zip(*columns):
        obj, elm, p, case, step, num = row[:6]
        key = elm, p
        if key not in pairs:
            continue
        values = [row[i] for i in (6, 7, 8, 13, 14, 15, 19, 20)]
        if (
            obj != uid
            or case not in cases
            or step not in (None, "", "Single Value", "Static")
            or num != 0
            or key in indexed[case]
            or not all(isfinite(v) for v in values)
        ):
            raise SourceError("INVALID_SIGNED_SHELL_FIELD:" + uid)
        indexed[case][key] = values
    if set(indexed) != set(cases) or any(set(v) != pairs for v in indexed.values()):
        raise SourceError("INCOMPLETE_SIGNED_SHELL_FIELDS:" + uid)
    axes = {}
    for elm in sorted({e for e, _ in pairs}):
        (matrix,) = _native(
            sap.AreaElm.GetTransformationMatrix(elm, []), "AreaElm.GetTransformationMatrix " + elm
        )
        axes[elm] = list(matrix)
    corners = sorted(pairs)
    return {"corners": corners, "axes": axes, "cases": {c: [indexed[c][k] for k in corners] for c in cases}}


def capture_transition_shells(sap, parent, labels, model_sha):
    wanted, coords, field_plan = native_plan(parent, labels, with_fields=True)
    if not wanted:
        return None
    tables = parent["vs04_basis_probe"]["table_reads"]
    cases = sorted({r["Name"] for r in tables["Load Case Definitions - Linear Static"]["rows"]})
    n, case_names, status = _native(sap.Analyze.GetCaseStatus(0, [], []), "Analyze.GetCaseStatus")
    if (
        n != len(case_names)
        or n != len(status)
        or not cases
        or any(dict(zip(case_names, status)).get(k) != 4 for k in cases)
    ):
        raise SourceError("SOLVED_LINEAR_STATIC_CASES_REQUIRED_FOR_TRANSITION")
    catalog = _catalog_names(sap.LoadCases.GetNameList(0, [], 0))
    combos = _catalog_names(sap.RespCombo.GetNameList(0, []))
    setup = sap.Results.Setup
    before = get_results_setup_state(setup, cases=catalog, combos=combos)
    points = {p for corners in wanted.values() for _, p in corners}
    bases = {p: _point_basis(sap, p, coords[p]) for p in sorted(points)}
    members = {}
    try:
        _native(setup.DeselectAllCasesAndCombosForOutput(), "Clear output selection")
        for case in cases:
            _native(setup.SetCaseSelectedForOutput(case, True), "Select " + case)
        during = get_results_setup_state(setup, cases=catalog, combos=combos)
        if {k for k, v in during["cases"].items() if v} != set(cases) or any(during["combos"].values()):
            raise SourceError("TRANSITION_RESULT_SELECTION_MISMATCH")
        for uid, pairs in wanted.items():
            n, *columns = _native(
                sap.Results.AreaJointForceShell(uid, 0, 0, *([] for _ in range(12))),
                "AreaJointForceShell " + uid,
            )
            if len(columns) != 12 or any(len(c) != n for c in columns):
                raise SourceError("TRANSITION_SHELL_RESULT_SHAPE_INVALID:" + uid)
            by_case = defaultdict(dict)
            for obj, elm, p, case, step, number, *v in zip(*columns):
                key = elm, p
                if key not in pairs:
                    continue
                if (
                    obj != uid
                    or case not in cases
                    or step not in (None, "", "Single Value", "Static")
                    or number != 0
                    or key in by_case[case]
                    or not all(isfinite(f) for f in v)
                ):
                    raise SourceError(
                        f"TRANSITION_SIGNED_CORNER_INVALID:{uid}:{elm}:{p}:{case}:{step}:{number}"
                    )
                by_case[case][key] = v
            if set(by_case) != set(cases) or any(set(v) != pairs for v in by_case.values()):
                raise SourceError("TRANSITION_SHELL_CASE_OR_CORNER_MISSING:" + uid)
            corners = sorted(pairs)
            members[uid] = {"corners": corners, "cases": {c: [by_case[c][k] for k in corners] for c in cases}}
        for uid, pairs in field_plan.items():
            try:
                members.setdefault(uid, {})["fields"] = _shell_fields(sap, uid, pairs, cases)
            except (AttributeError, OSError, ValueError) as exc:
                members.setdefault(uid, {})["field_reason"] = str(exc)
    finally:
        restore_results_setup_state(setup, before)
        if get_results_setup_state(setup, cases=catalog, combos=combos) != before:
            raise SourceError("TRANSITION_RESULT_SELECTION_RESTORE_FAILED")
    return seal(
        {
            "schema": SCHEMA,
            "model_sha256": model_sha,
            "units": 6,
            "cases": cases,
            "members": members,
            "point_bases": bases,
            "selection_restored": True,
        }
    )
