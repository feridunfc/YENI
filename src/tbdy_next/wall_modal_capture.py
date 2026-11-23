"""Read signed modal wall and storey cuts from an already solved ETABS session."""

from collections import defaultdict
from math import dist, fsum, isclose

from .etabs_source_gateway_windows import (
    SourceError,
    field_schema,
    get_results_setup_state,
    read_table,
    restore_results_setup_state,
    return_code,
    seal,
    selected_cases,
    selected_combinations,
    set_cases,
    set_combinations,
)
from .frame_force_capture import _catalog_names, _mode_shape_option
from .story_geometry import read_story_levels


def _native(raw, method):
    if return_code(raw, method) != 0:
        raise SourceError("WALL_MODAL_READ_FAILED:" + method)
    return list(raw[:-1]) if isinstance(raw, (list, tuple)) else []


def wall_cut_plan(source):
    """Select lower edges of shells above each storey base using the physical source."""
    geom = source["vs06_b1_geometry_source"]["table_reads"]
    cuts = source["column_axial"]["r10_source"]["table_reads"]
    xyz = {
        r["UniqueName"]: tuple(float(r[k]) for k in "XYZ") for r in geom["Point Object Connectivity"]["rows"]
    }
    walls = geom["Wall Object Connectivity"]["rows"]
    levels, _ = read_story_levels(source["vs04_basis_probe"])
    bases = {r.story: float(r.elevation_m - r.height_m) for r in levels}
    spans = {}
    for r in walls:
        uid, story = r["UniqueName"], r["Story"]
        a, b, c, d = (xyz[r["UniquePt" + str(i)]] for i in range(1, 5))
        if a[:2] != d[:2] or b[:2] != c[:2] or a[2] != b[2] or c[2] != d[2] or a[2] >= c[2] or uid in spans:
            raise ValueError("VERTICAL_RECTANGULAR_WALL_AT_IDENTIFIED_CUT_REQUIRED")
        if story not in bases or a[2] < bases[story] - 1e-7:
            raise ValueError("WALL_LOWER_END_OUTSIDE_NATIVE_STOREY:" + uid)
        spans[uid] = (story, a, b)
    joints = {
        r["ElmName"]: tuple(float(r["Global" + k]) for k in "XYZ")
        for r in cuts["Objects and Elements - Joints"]["rows"]
    }
    plans = {
        uid: {
            "story": s,
            "origin_m": [(a[i] + b[i]) / 2 for i in range(3)],
            "corners": set(),
            "length_m": dist(a, b),
        }
        for uid, (s, a, b) in spans.items()
        if isclose(a[2], bases[s], abs_tol=1e-7, rel_tol=0)
    }
    lengths = defaultdict(list)
    for r in cuts["Objects and Elements - Areas"]["rows"]:
        uid = r["ObjName"]
        if r["ObjType"] != "Wall" or uid not in plans:
            continue
        plan = plans[uid]
        nodes = [r[k] for k in ("ElmJt1", "ElmJt2", "ElmJt3", "ElmJt4") if r.get(k) not in (None, "", "None")]
        z = plan["origin_m"][2]
        edge = [p for p in nodes if abs(joints[p][2] - z) < 1e-7]
        if not edge:
            continue
        if (
            len(edge) != 2
            or min(joints[n][2] for n in nodes) < z - 1e-7
            or max(joints[n][2] for n in nodes) <= z + 1e-7
            or not any({u, v} == set(edge) for u, v in zip(nodes, nodes[1:] + nodes[:1]))
        ):
            raise ValueError("COMPLETE_UPPER_SHELL_EDGE_REQUIRED:" + uid)
        for p in edge:
            corner = r["ElmName"], p
            if corner in plan["corners"]:
                raise ValueError("DUPLICATE_WALL_CUT_CORNER:" + uid)
            plan["corners"].add(corner)
        lengths[uid].append(dist(joints[edge[0]], joints[edge[1]]))
    for uid, plan in plans.items():
        if not isclose(fsum(lengths[uid]), plan["length_m"], rel_tol=1e-6, abs_tol=2e-5):
            raise ValueError("ANALYSIS_EDGE_LENGTH_DIFFERS_FROM_PHYSICAL_WALL:" + uid)
    return plans, joints


def _display_options(db):
    return _native(
        db.GetOutputOptionsForDisplay(False, 0.0, 0.0, 0.0, False, 1, 1, False, 1, 1, 1, 1, 1, 1, 1),
        "GetOutputOptionsForDisplay",
    )


def _modal_tables(db, cases, highest):
    before = _display_options(db)
    chosen, combinations = selected_cases(db), selected_combinations(db)
    options = before.copy()
    options[4:7] = [True, 1, highest]
    try:
        _native(db.SetOutputOptionsForDisplay(*options), "Set all database modes")
        set_cases(db, tuple(cases))
        set_combinations(db, ())
        if set(selected_cases(db)) != set(cases) or selected_combinations(db) or not _display_options(db)[4]:
            raise SourceError("WALL_DATABASE_MODAL_SELECTION_NOT_CONFIRMED")
        tables = {}
        for name in ("Story Forces", "Pier Forces", "Base Reactions"):
            table = read_table(db, name)
            table["field_metadata"] = field_schema(db, name)
            tables[name] = table
        return tables
    finally:
        try:
            set_cases(db, chosen)
        finally:
            try:
                set_combinations(db, combinations)
            finally:
                _native(db.SetOutputOptionsForDisplay(*before), "Restore database output options")
        if (
            set(selected_cases(db)) != set(chosen)
            or set(selected_combinations(db)) != set(combinations)
            or _display_options(db) != before
        ):
            raise SourceError("WALL_DATABASE_SELECTION_RESTORE_FAILED")


def _point_basis(sap, point, archived):
    pos = _native(sap.PointElm.GetCoordCartesian(point, 0.0, 0.0, 0.0, "Global"), "GetCoordCartesian")
    if len(pos) != 3 or dist(pos, archived) > 0.001:
        raise SourceError("WALL_ANALYSIS_JOINT_COORDINATES_DIFFER:" + point)
    try:
        (matrix,) = _native(
            sap.PointElm.GetTransformationMatrix(point, []), "PointElm.GetTransformationMatrix"
        )
    except (AttributeError, OSError, SourceError, ValueError):
        if _native(sap.PointElm.GetLocalAxes(point, 0.0, 0.0, 0.0), "PointElm.GetLocalAxes") != [
            0.0,
            0.0,
            0.0,
        ]:
            raise SourceError("WALL_POINT_AXES_REQUIRED:" + point)
        matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    return pos, matrix


def capture_wall_modes(sap, parent, file_sha):
    from .engineering.gravity_wall_cut import joint_action_at_origin

    first = parent["column_axial"]["demand_support"]["force_source"]["expected_modal_modes"]
    if len(first) != 1:
        raise SourceError("ONE_MODAL_CASE_REQUIRED_FOR_WALL_CAPTURE")
    modal, modes = next(iter(first.items()))
    definitions = parent["vs04_basis_probe"]["table_reads"]
    spectra = sorted({r["Name"] for r in definitions["Load Case Definitions - Response Spectrum"]["rows"]})
    names = _catalog_names(sap.LoadCases.GetNameList(0, [], 0))
    combos = _catalog_names(sap.RespCombo.GetNameList(0, []))
    seismic = {r["Name"] for r in definitions["Load Pattern Definitions"]["rows"] if r["Type"] == "Seismic"}
    static_loads = defaultdict(list)
    for row in definitions["Load Case Definitions - Linear Static"]["rows"]:
        static_loads[row["Name"]].append(row)
    roster = parent["column_axial"]["demand_support"]["force_source"]["output_selection_during"]["cases"]
    statics = sorted(
        k
        for k, rows in static_loads.items()
        if k in names
        and roster.get(k)
        and all(r["LoadType"] == "Load" and r["LoadName"] in seismic for r in rows)
    )
    selected = [modal] + statics
    tables = _modal_tables(sap.DatabaseTables, selected + spectra, max(modes))
    plans, coords = wall_cut_plan(parent)
    setup = sap.Results.Setup
    flags = get_results_setup_state(setup, cases=names, combos=combos)
    old = _mode_shape_option(setup)
    basis = {}
    for p in sorted({p for plan in plans.values() for _, p in plan["corners"]}):
        basis[p] = _point_basis(sap, p, coords[p])
    panels = {}
    try:
        _native(setup.DeselectAllCasesAndCombosForOutput(), "Clear result flags")
        for case in selected:
            _native(setup.SetCaseSelectedForOutput(case, True), "Select " + case)
        _native(setup.SetOptionModeShape(1, max(modes), True), "Select all mode shapes")
        during = get_results_setup_state(setup, cases=names, combos=combos)
        if (
            {k for k, v in during["cases"].items() if v} != set(selected)
            or any(during["combos"].values())
            or not _mode_shape_option(setup)[2]
        ):
            raise SourceError("WALL_NATIVE_MODAL_SELECTION_NOT_CONFIRMED")
        for uid, plan in plans.items():
            n, *columns = _native(
                sap.Results.AreaJointForceShell(uid, 0, 0, *([] for _ in range(12))),
                "AreaJointForceShell " + uid,
            )
            if len(columns) != 12 or any(len(column) != n for column in columns):
                raise SourceError("UNEXPECTED_SHELL_JOINT_FORCE_ABI:" + uid)
            cases = defaultdict(dict)
            for obj, elm, point, case, step, num, *forces in zip(*columns):
                corner = elm, point
                if obj != uid or corner not in plan["corners"]:
                    continue
                if (
                    (case == modal and (step != "Mode" or num not in modes))
                    or (case in statics and num != 0)
                    or case not in selected
                ):
                    raise SourceError("UNEXPECTED_WALL_CASE_OR_STEP:" + uid)
                key = case, int(num)
                if corner in cases[key]:
                    raise SourceError("DUPLICATE_MODAL_CORNER_RESULT:" + uid)
                pos, axes = basis[point]
                cases[key][corner] = joint_action_at_origin(forces, axes, pos, plan["origin_m"])
            if set(cases) != {(modal, m) for m in modes} | {(s, 0) for s in statics} or any(
                set(v) != plan["corners"] for v in cases.values()
            ):
                raise SourceError("INCOMPLETE_SIGNED_WALL_CUT:" + uid)
            panels[uid] = {
                "story": plan["story"],
                "origin_m": plan["origin_m"],
                "corners": sorted(plan["corners"]),
                "rows": [
                    [case, mode, *map(fsum, zip(*actions.values()))]
                    for (case, mode), actions in sorted(cases.items())
                ],
            }
    finally:
        try:
            restore_results_setup_state(setup, flags)
        finally:
            _native(setup.SetOptionModeShape(*old), "Restore mode shape option")
        if _mode_shape_option(setup) != old:
            raise SourceError("WALL_NATIVE_MODAL_SELECTION_RESTORE_FAILED")
    return seal(
        {
            "schema": "tbdy.next.original-wall-modal-cuts.v1",
            "modal_case": modal,
            "modes": modes,
            "static_cases": statics,
            "units": 6,
            "selection_restored": True,
            "model_sha256": file_sha,
            "tables": tables,
            "panels": panels,
            "point_bases": basis,
        }
    )
