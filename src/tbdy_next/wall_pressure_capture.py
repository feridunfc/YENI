"""Read unaveraged basement pressure-panel field results on the active solved ETABS generation."""
from collections import defaultdict
from math import isfinite
from pathlib import Path

from .engineering.basement_pier_geometry import folded_section
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
    plan = {}
    for (name, story), ids in bound["assignments"].items():
        if len(ids) < 2:
            continue
        try:
            geom = folded_section(source, bound, name, story, sorted(ids))
            cases, _ = pressure_cases(source, bound, scope, name, story, geom["panels"])
        except ValueError:
            continue  # The panel design owner retains the unsupported geometry or load reason.
        for panel in geom["panels"]:
            uid = panel["member"]
            if not mesh.get(uid) or uid in plan:
                raise SourceError("PRESSURE_PANEL_MESH_OR_IDENTITY_INVALID:" + uid)
            plan[uid] = (mesh[uid], {k: v["spectral"] for k, v in cases.items()})
    return plan


def _panel_read(sap, uid, mesh, targets):
    corners = sorted((elm, pt) for elm, nodes in mesh.items() for pt in nodes)
    population = set(corners)
    n, *columns = _native(sap.Results.AreaForceShell(uid, 0, 0, *([] for _ in range(23))), "AreaForceShell " + uid)
    if len(columns) != 23 or any(len(col) != n for col in columns):
        raise SourceError("PRESSURE_SHELL_ABI_MISMATCH:" + uid)
    rows = defaultdict(lambda: defaultdict(dict))
    for raw in zip(*columns):
        obj, elm, pt, combo, step, num = raw[:6]
        if combo not in targets:
            continue
        key = (elm, pt)
        tag = step or ""
        vals = [raw[i] for i in (13, 14, 15, 19, 20)]
        if (obj != uid or key not in population or num != 0 or key in rows[combo][tag]
                or not all(isfinite(v) for v in vals)):
            raise SourceError(f"PRESSURE_SHELL_CORNER_OR_STEP_INVALID:{uid}:{key}:{combo}:{tag}:{num}")
        rows[combo][tag][key] = vals
    cases = {}
    for combo, is_spectral in targets.items():
        sets = rows[combo]
        signed = len(sets) == 1 and next(iter(sets)) in ("", "Single Value", "Static")
        if (not (set(sets) == {"Min", "Max"} or (signed and not is_spectral))
                or any(set(points) != population for points in sets.values())):
            raise SourceError(f"PRESSURE_SHELL_COMBINATION_INCOMPLETE:{uid}:{combo}:{list(sets)}")
        cases[combo] = {tag: [points[k] for k in corners] for tag, points in sets.items()}
    axes = {}
    for elm in sorted(mesh):
        (matrix,) = _native(sap.AreaElm.GetTransformationMatrix(elm, []), "AreaElm.GetTransformationMatrix " + elm)
        axes[elm] = list(matrix)
    return {"corners": corners, "axes": axes, "cases": cases}


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
                  "control_member": control["control_member"], "selection_restored": True, "members": members})
    return seal({**{k:v for k,v in previous.items() if k != "payload_sha256"}, "pressure_shells": field})
