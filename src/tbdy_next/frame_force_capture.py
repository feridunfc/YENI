"""Read selected native frame forces on an already attached ETABS model."""
from __future__ import annotations

from .column_engine.source_bank import FIELDS, FORCE_SIGNATURE, native_frame_force_rows
from .etabs_source_gateway_windows import (
    SourceError, get_results_setup_state, restore_results_setup_state, return_code,
)

MAX_FORCE_ROWS = 100_000
MAX_RESPONSE_COMBINATIONS = 128
MAX_TARGET_FRAMES = 1500


class ForceSelectionRestoreError(SourceError):
    """The original output selection could not be verified after the read."""


def _catalog_names(raw):
    if not isinstance(raw, (tuple, list)) or len(raw) != 3:
        raise SourceError("FRAME_FORCE_OUTPUT_CATALOG_INVALID")
    count, names, ret = raw
    if (type(count) is not int or not 0 < count <= 20_000 or type(ret) is not int or ret != 0
            or not isinstance(names, (tuple, list)) or len(names) != count
            or any(not isinstance(name, str) or not name.strip() for name in names)
            or len(set(names)) != count):
        raise SourceError("FRAME_FORCE_OUTPUT_CATALOG_INVALID")
    return tuple(sorted(names))


def capture_frame_forces(sap, *, members: tuple[str, ...], combinations: tuple[str, ...]) -> dict:
    """Capture six signed or envelope components and preserve each native result key."""
    if (not 0 < len(members) <= MAX_TARGET_FRAMES or len(set(members)) != len(members)
            or not 0 < len(combinations) <= MAX_RESPONSE_COMBINATIONS
            or len(set(combinations)) != len(combinations)):
        raise SourceError("FRAME_FORCE_POPULATION_OUTSIDE_CAPTURE_SCOPE")
    if sap.GetModelIsLocked() is not True or sap.GetPresentUnits() != 6:
        raise SourceError("FRAME_FORCE_REQUIRES_LOCKED_KN_M_C")
    cases = _catalog_names(sap.LoadCases.GetNameList(0, [], 0))
    combos = _catalog_names(sap.RespCombo.GetNameList(0, []))
    wanted = set(combinations)
    if set(cases) & set(combos) or not wanted.issubset(combos):
        raise SourceError("FRAME_FORCE_COMBINATION_MISSING_FROM_NATIVE_CATALOG")

    results = sap.Results
    setup = results.Setup
    before = get_results_setup_state(setup, cases=cases, combos=combos)
    selected = {"cases": dict.fromkeys(cases, False), "combos": {c: c in wanted for c in combos}}
    rowsets, errors = {}, {}
    count = 0
    try:
        if before != selected:
            if return_code(setup.DeselectAllCasesAndCombosForOutput(), "DeselectAllCasesAndCombosForOutput") != 0:
                raise SourceError("FRAME_FORCE_OUTPUT_DESELECTION_REJECTED")
            for combo in combinations:
                if return_code(setup.SetComboSelectedForOutput(combo, True), "SetComboSelectedForOutput") != 0:
                    raise SourceError("FRAME_FORCE_OUTPUT_SELECTION_REJECTED:" + combo)
        if get_results_setup_state(setup, cases=cases, combos=combos) != selected:
            raise SourceError("FRAME_FORCE_OUTPUT_SELECTION_UNVERIFIED")

        for member in members:
            try:
                # CSI ObjectElm records both object and analysis-element stations.
                raw = results.FrameForce(member, 0, 0, *([] for _ in FIELDS))
                if not isinstance(raw, (list, tuple)) or len(raw) != len(FORCE_SIGNATURE):
                    raise SourceError("FRAME_FORCE_RESPONSE_FIELDS_INVALID")
                record = dict(zip(FORCE_SIGNATURE, raw))
                rows = tuple(native_frame_force_rows(record, member))
                if any(row[4] not in wanted for row in rows):
                    raise SourceError("FRAME_FORCE_RETURNED_UNSELECTED_OUTPUT")
                if count + len(rows) > MAX_FORCE_ROWS:
                    raise SourceError("FRAME_FORCE_CAPTURE_ROW_LIMIT")
                rowsets[member] = record
                count += len(rows)
            except Exception as exc:
                errors[member] = f"{type(exc).__name__}: {exc}"[:400]
        if get_results_setup_state(setup, cases=cases, combos=combos) != selected:
            raise SourceError("FRAME_FORCE_OUTPUT_SELECTION_CHANGED_DURING_READ")
    finally:
        try:
            if before != selected:
                restore_results_setup_state(setup, before)
            after = get_results_setup_state(setup, cases=cases, combos=combos)
            if after != before:
                raise SourceError("FRAME_FORCE_OUTPUT_SELECTION_CHANGED")
        except Exception as exc:
            raise ForceSelectionRestoreError("ETABS frame-force output selection restoration failed") from exc

    if sap.GetModelIsLocked() is not True or sap.GetPresentUnits() != 6:
        raise SourceError("FRAME_FORCE_MODEL_LOCK_OR_UNITS_CHANGED")
    return {
        "schema": "tbdy.next.etabs-frame-force-source.v1",
        "api": "Results.FrameForce", "item_type": "ObjectElm", "units_code": 6,
        "output_selection_before": before, "output_selection_during": selected,
        "output_selection_after": after, "rowsets": rowsets, "errors": errors,
    }
