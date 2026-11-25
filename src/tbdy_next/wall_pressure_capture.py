"""Read unaveraged basement pressure-panel field results on the active solved ETABS generation."""
from collections import defaultdict
from math import isfinite
from pathlib import Path

from .engineering.basement_wall_pressure import pressure_cases
from .engineering.pier_force_source import bound_pier_forces
from .engineering.pier_seismic_shear import wall_load_scope
from .engineering.wall_transition import mesh_geometry
from .etabs_source_gateway_windows import (
    SourceError, get_results_setup_state, model_file, restore_results_setup_state, seal, verify,
)
from .frame_force_capture import _catalog_names
from .wall_modal_capture import _native


from .engineering.wall_pressure_shell import COMPONENTS, SCHEMA


def pressure_field_plan(source):
    if not (source.get("analysis_archive") and source.get("pier_section_forces") and source.get("design_scenario")):
        return {}
    scope = wall_load_scope(source)
    if not scope["native_static"]:
        return {}
    bound = bound_pier_forces(source, scope["native_static"])
    _, mesh = mesh_geometry(source)
    walls = source["vs06_b1_geometry_source"]["table_reads"]["Wall Object Connectivity"]["rows"]
    by_id = {r["UniqueName"]: r for r in walls}
    assigned = set()
    targets = set()
    combo_types = {name: False for name in scope["native_static"]}
    combo_types.update({name: True for name in scope["native_seismic"]})
    for (pier, story), ids in bound["assignments"].items():
        assigned.update(ids)
        if len(ids) < 2:
            continue
        targets.update(ids)
        panels = [{"member": uid, "wall": by_id[uid]["WallBay"]} for uid in ids]
        cases, _ = pressure_cases(source, bound, scope, pier, story, panels, allow_unloaded=True)
        combo_types.update({name: spec["spectral"] for name, spec in cases.items()})
    targets.update(by_id.keys() - assigned)
    if any(not mesh.get(uid) for uid in targets):
        raise SourceError("PRESSURE_PANEL_MESH_OR_IDENTITY_INVALID")
    return {uid: (mesh[uid], combo_types) for uid in sorted(targets)}


def _corner_results(method, uid, corners, targets, indices, column_count):
    """Preserve individual element contributions and the actual static or envelope step."""
    n, *columns = _native(method(uid, 0, 0, *([] for _ in range(column_count))), "Native corner results " + uid)
    if len(columns) != column_count or any(len(col) != n for col in columns):
        raise SourceError("PRESSURE_RESULT_ABI_MISMATCH:" + uid)
    population = set(corners)
    rows = defaultdict(lambda: defaultdict(dict))
    for raw in zip(*columns):
        obj, elm, pt, combo, step, number = raw[:6]
        key = (elm, pt)
        if combo not in targets or key not in population:
            continue
        tag = step or ""
        values = [raw[i] for i in indices]
        if (obj != uid or number != 0 or key in rows[combo][tag]
                or not all(isfinite(v) for v in values)):
            raise SourceError(f"PRESSURE_CORNER_OR_STEP_INVALID:{uid}:{key}:{combo}:{tag}:{number}")
        rows[combo][tag][key] = values
    cases = {}
    for combo, spectral in targets.items():
        steps = rows[combo]
        signed = len(steps) == 1 and next(iter(steps)) in ("", "Single Value", "Static")
        if (not (set(steps) == {"Min", "Max"} or (signed and not spectral))
                or any(set(points) != population for points in steps.values())):
            raise SourceError(f"PRESSURE_COMBINATION_INCOMPLETE:{uid}:{combo}:{list(steps)}")
        cases[combo] = {tag: [points[k] for k in corners] for tag, points in steps.items()}
    return {"corners": corners, "cases": cases}


def _panel_read(sap, uid, mesh, targets):
    corners = sorted((elm, pt) for elm, nodes in mesh.items() for pt in nodes)
    item = _corner_results(sap.Results.AreaForceShell, uid, corners, targets,
                           (6, 7, 8, 13, 14, 15, 19, 20), 23)
    axes = {}
    for elm in sorted(mesh):
        (matrix,) = _native(sap.AreaElm.GetTransformationMatrix(elm, []), "AreaElm.GetTransformationMatrix " + elm)
        axes[elm] = list(matrix)
    return {**item, "axes": axes}


def _edge_plan(source, plan):
    """Keep all shell and frame incidences at the physical mesh boundaries, including floors."""
    from collections import Counter
    coords, _ = mesh_geometry(source)
    boundaries = {}
    for uid, (mesh, _) in plan.items():
        counts = Counter(tuple(sorted((a,b))) for nodes in mesh.values()
                         for a,b in zip(nodes, nodes[1:] + nodes[:1]))
        if not counts or max(counts.values()) > 2:
            raise SourceError("NONMANIFOLD_PRESSURE_PANEL:" + uid)
        boundaries[uid] = sorted(edge for edge, count in counts.items() if count == 1)
    points = {p for edges in boundaries.values() for edge in edges for p in edge}
    tables = source["column_axial"]["r10_source"]["table_reads"]
    groups = {}
    for role, table, keys in (("areas", "Areas", ("ElmJt1","ElmJt2","ElmJt3","ElmJt4")),
                              ("frames", "Frames", ("ElmJtI","ElmJtJ"))):
        by_object = defaultdict(set)
        for row in tables["Objects and Elements - " + table]["rows"]:
            if (role == "frames" and row["ObjType"] != "Frame") or (role == "areas" and row["ObjType"] not in {"Wall","Floor","Ramp"}):
                continue
            for key in keys:
                pt = row.get(key)
                if pt in points:
                    by_object[row["ObjName"]].add((row["ElmName"], pt))
        groups[role] = {uid: sorted(pairs) for uid, pairs in by_object.items()}
    return boundaries, {p:coords[p] for p in sorted(points)}, groups


def _edge_read(sap, parent, plan, targets):
    from .wall_modal_capture import _point_basis
    boundaries, coords, groups = _edge_plan(parent, plan)
    bases = {p: _point_basis(sap,p,xyz) for p,xyz in coords.items()}
    data = {"boundaries": boundaries, "point_bases": bases,
            "components": ["F1","F2","F3","M1","M2","M3"]}
    for role, method in (("areas", sap.Results.AreaJointForceShell), ("frames", sap.Results.FrameJointForce)):
        data[role] = {uid: _corner_results(method,uid,corners,targets,range(6,12),12)
                      for uid,corners in groups[role].items()}
    return data


def extend_pressure_read(sap, pid, parent, parent_sha, previous, plan):
    from hashlib import sha256
    import json
    from .etabs_source_gateway_windows import capture_assigned_pier_forces
    from .wall_analysis_replay import _safe, pier_controls

    verify(previous)
    # Also recheck the solved original against the archived signed frame rows. Same-name
    # models or an edited source cannot supply this supplemental field.
    original = Path(parent["capture_metadata"]["model_filename"]).with_suffix(".EDB").resolve(strict=True)
    opened = Path(model_file(sap)).with_suffix(".EDB").resolve(strict=True)
    original_sha = previous["model_sha256"]
    if previous["parent_input_sha256"] != parent_sha or sha256(original.read_bytes()).hexdigest() != original_sha:
        raise SourceError("PRESSURE_SHELL_ORIGINAL_GENERATION_DIFFERS")
    clone = opened != original
    solved = original_sha
    if clone:
        proof = (previous.get("transition_shells") or {}).get("solution") or {}
        manifest = opened.parent / "source.json"
        if (opened.name.casefold() != original.name.casefold() or opened.parent.parent.name != "wall-analysis-copies"
                or not _safe(manifest) or not _safe(opened) or not manifest.is_file()
                or json.loads(manifest.read_bytes()) != {"original":str(original),"parent_sha256":parent_sha,"input_sha256":original_sha}
                or proof.get("method") != "INPUT_IDENTICAL_PRIVATE_REANALYSIS" or proof.get("input_sha256") != original_sha
                or not proof.get("frame_control_matched") or proof["pier_controls"]["outside_tolerance"] != 0):
            raise SourceError("PRESSURE_SHELL_IDENTIFIED_ORIGINAL_OR_VERIFIED_COPY_REQUIRED")
        solved = proof["solved_sha256"]
    if sha256(opened.read_bytes()).hexdigest() != solved:
        raise SourceError("PRESSURE_SHELL_SOLVED_GENERATION_DIFFERS")
    control = capture_assigned_pier_forces(sap, pid, parent, parent_sha, private_reference=opened if clone else None)
    checks = pier_controls(previous, control)
    if control["model_sha256"] != solved or checks["outside_tolerance"] or set(control["combinations"]) != set(previous["combinations"]):
        raise SourceError("PRESSURE_SHELL_FORCE_CONTROLS_DIFFER")
    case_names = _catalog_names(sap.LoadCases.GetNameList(0, [], 0))
    combo_names = control["combinations"]
    selected = sorted({combo for _, targets in plan.values() for combo in targets})
    setup = sap.Results.Setup
    before = get_results_setup_state(setup, cases=case_names, combos=combo_names)
    active = model_file(sap)
    members = {}
    try:
        _native(setup.DeselectAllCasesAndCombosForOutput(), "Clear output selection")
        for name in selected:
            _native(setup.SetComboSelectedForOutput(name, True), "Select " + name)
        current = get_results_setup_state(setup, cases=case_names, combos=combo_names)
        if any(current["cases"].values()) or {k for k,v in current["combos"].items() if v} != set(selected):
            raise SourceError("PRESSURE_SHELL_SELECTION_DIFFERS")
        for uid, (mesh, targets) in plan.items():
            members[uid] = _panel_read(sap, uid, mesh, targets)
        targets = {name: spectral for _, cases in plan.values() for name, spectral in cases.items()}
        edges = _edge_read(sap, parent, plan, targets)
    finally:
        restore_results_setup_state(setup, before)
        if get_results_setup_state(setup, cases=case_names, combos=combo_names) != before:
            raise SourceError("PRESSURE_SHELL_SELECTION_RESTORE_FAILED")
    model = Path(active).with_suffix(".EDB")
    if (model_file(sap) != active or not sap.GetModelIsLocked() or sap.GetPresentUnits() != 6
            or sha256(model.read_bytes()).hexdigest() != control["model_sha256"]):
        raise SourceError("PRESSURE_SHELL_MODEL_CHANGED_DURING_READ")
    field = seal({"schema": SCHEMA, "units": 6, "components": list(COMPONENTS),
                  "model_sha256": original_sha, "solved_sha256":solved, "parent_input_sha256": parent_sha,
                  "solution_role":"INPUT_IDENTICAL_PRIVATE_REANALYSIS" if clone else "SOLVED_ORIGINAL",
                  "pier_controls":checks,
                  "control_member": control["control_member"], "selection_restored": True, "members": members, "edge_actions":edges})
    return seal({**{k:v for k,v in previous.items() if k != "payload_sha256"}, "pressure_shells": field})
