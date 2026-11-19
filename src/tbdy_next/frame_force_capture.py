"""Read selected native frame forces on an already attached ETABS model."""
from __future__ import annotations

import json
import math

from .column_engine.source_bank import FIELDS, FORCE_SIGNATURE, native_frame_force_rows
from .etabs_source_gateway_windows import (
    SourceError, get_results_setup_state, restore_results_setup_state, return_code,
)

MAX_FORCE_ROWS = 100_000
MAX_RESPONSE_COMBINATIONS = 128
MAX_TARGET_FRAMES = 1500
MODAL_RESULT_FIELDS = {
    "ModalPeriod": ("LoadCase", "StepType", "StepNum", "Period", "Frequency", "CircFreq", "EigenValue"),
    "ModalParticipationFactors": ("LoadCase", "StepType", "StepNum", "Period", "UX", "UY", "UZ",
                                 "RX", "RY", "RZ", "ModalMass", "ModalStiff"),
}
MODAL_RESULTS_SCHEMA = "tbdy.next.native-modal-results.v1"
ECCENTRICITY_SCHEMA = "tbdy.next.native-spectrum-eccentricity.v1"
SPECTRUM_INPUT_SCHEMA = "tbdy.next.native-spectrum-inputs.v1"


def _spectrum_getter(owner, api, name, fields, *outputs):
    """Keep the requested identity and the JSON-safe native return, including errors."""
    record = {"api": api, "name": name}
    try:
        raw = getattr(owner, api.rsplit(".", 1)[-1])(name, *outputs)
        if not isinstance(raw, (tuple, list)) or len(raw) > 32 or any(
            isinstance(v, (list, tuple)) and len(v) > MAX_FORCE_ROWS for v in raw
        ):
            raise SourceError("SPECTRUM_GETTER_RETURN_SHAPE_INVALID")
        try:
            json.dumps(raw, allow_nan=False)
        except (ValueError, TypeError):
            record["invalid_native_values"] = [
                {"field_index": i, "item_index": j, "type": type(v).__name__, "representation": repr(v)[:100]}
                for i, field in enumerate(raw)
                for j, v in enumerate(field if isinstance(field, (list, tuple)) else [field])
                if type(v) not in (str, int, float, bool, type(None)) or type(v) is float and not math.isfinite(v)
            ][:16]
            raise
        record["raw"] = raw
        if len(raw) != len(fields) + 1 or type(raw[-1]) is not int or raw[-1] != 0:
            raise SourceError("SPECTRUM_GETTER_ABI_OR_RETURN_INVALID")
        record["status"] = "CAPTURED"
    except Exception as exc:
        record.update(status="CAPTURE_ERROR", error=f"{type(exc).__name__}: {exc}"[:400])
    return record


SPECTRUM_GETTERS = {
    "GetModalCase": (("ModalCase",), ("",)),
    "GetLoads": (("NumberLoads", "LoadName", "Func", "SF", "CSys", "Ang"), (0, (), (), (), (), ())),
    "GetDampType": (("DampType",), (0,)),
    "GetDampConstant": (("Damp",), (0.,)),
    "GetDampOverrides": (("NumberItems", "Mode", "Damp"), (0, (), ())),
}
CURVE_FIELDS = ("NumberItems", "MyTime", "Value")


def capture_spectrum_damping_properties(sap, material_names, linear_link_names):
    """Read native damping parameters for names from the same model's property tables."""
    materials = {name: _spectrum_getter(getattr(sap, "PropMaterial", None), "PropMaterial.GetDamping", name,
        ("ModalRatio", "ViscousMassCoeff", "ViscousStiffCoeff", "HystereticMassCoeff", "HystereticStiffCoeff"),
        0., 0., 0., 0., 0., 0.) for name in material_names}
    links = {name: _spectrum_getter(getattr(sap, "PropLink", None), "PropLink.GetLinear", name,
        ("DOF", "Fixed", "Ke", "Ce", "DJ2", "DJ3", "KeCoupled", "CeCoupled", "Notes", "GUID"),
        [], [], [], [], 0., 0., False, False, "", "") for name in linear_link_names}
    return {"material_temperature": 0., "materials": materials, "linear_links": links}


def _capture_spectrum_inputs(sap, cases):
    records, functions = {}, {}
    for case in cases:
        methods = {}
        for method, (fields, outputs) in SPECTRUM_GETTERS.items():
            methods[method] = _spectrum_getter(sap.LoadCases.ResponseSpectrum,
                "LoadCases.ResponseSpectrum." + method, case, fields,
                *([] if isinstance(value, tuple) else value for value in outputs))
        records[case] = methods
        loads = methods["GetLoads"]
        if loads["status"] == "CAPTURED":
            count, _, names, *_ = loads["raw"]
            if (type(count) is int and 0 < count <= MAX_RESPONSE_COMBINATIONS
                    and isinstance(names, (tuple, list)) and len(names) == count):
                for name in names:
                    if isinstance(name, str) and name and name == name.strip() and name not in functions:
                        functions[name] = _spectrum_getter(getattr(sap, "Func", None), "Func.GetValues", name,
                                                          CURVE_FIELDS, 0, [], [])
    return {"schema": SPECTRUM_INPUT_SCHEMA, "units_code": 6, "cases": records, "functions": functions}


def native_modal_rows(record, method, modes, *, period_record=None):
    """Validate native values and bind identities without changing raw API fields.

    The observed ETABS 23 participation return omits step identity (null/zero).
    Only a unique exact period in the same case and complete companion getter
    can resolve it. Repeated periods, nearest matches and row order are unsafe.
    """
    fields = MODAL_RESULT_FIELDS[method]
    if not isinstance(record, dict) or set(record) != {"NumberResults", "ret", *fields}:
        raise SourceError("NATIVE_MODAL_RESULT_FIELDS_INVALID")
    count = record["NumberResults"]
    if (type(count) is not int or not 0 <= count <= MAX_FORCE_ROWS
            or type(record["ret"]) is not int or record["ret"] != 0
            or any(not isinstance(record[k], (list, tuple)) or len(record[k]) != count for k in fields)):
        raise SourceError("NATIVE_MODAL_RESULT_ARRAYS_INVALID")
    rows, seen, period_index = [], set(), None
    for values in zip(*(record[k] for k in fields)):
        row = dict(zip(fields, values))
        if (not isinstance(row["LoadCase"], str) or row["LoadCase"] not in modes
                or any(type(row[k]) not in (int, float) or not math.isfinite(row[k]) for k in fields[2:])
                or row["StepNum"] != int(row["StepNum"])):
            raise SourceError("NATIVE_MODAL_RESULT_IDENTITY_OR_NUMBER_INVALID")
        if row["StepType"] == "Mode" and row["StepNum"] in modes[row["LoadCase"]]:
            mode, basis = int(row["StepNum"]), "NATIVE_CASE_STEP"
        elif method == "ModalParticipationFactors" and row["StepType"] is None and row["StepNum"] == 0:
            if period_index is None:
                companions = native_modal_rows(period_record, "ModalPeriod", modes)
                expected = {(case, mode) for case, values in modes.items() for mode in values}
                if {(r["LoadCase"], r["mode_identity"]["mode"]) for r in companions} != expected:
                    raise SourceError("NATIVE_MODAL_IDENTITY_PERIOD_INVENTORY_INCOMPLETE")
                period_index = {}
                for companion in companions:
                    key = companion["LoadCase"], companion["Period"]
                    period_index.setdefault(key, []).append(companion["mode_identity"]["mode"])
            candidates = period_index.get((row["LoadCase"], row["Period"]), [])
            if len(candidates) != 1:
                raise SourceError("NATIVE_MODAL_IDENTITY_PERIOD_MATCH_NOT_UNIQUE")
            mode, basis = candidates[0], "UNIQUE_EXACT_SAME_CASE_PERIOD"
        else:
            raise SourceError("NATIVE_MODAL_RESULT_IDENTITY_OR_NUMBER_INVALID")
        identity = row["LoadCase"], mode
        if identity in seen:
            raise SourceError("NATIVE_MODAL_RESULT_DUPLICATE_MODE")
        if any(row[k] <= 0 for k in (("Period", "Frequency", "CircFreq", "EigenValue")
                if method == "ModalPeriod" else ("Period", "ModalMass", "ModalStiff"))):
            raise SourceError("NATIVE_MODAL_RESULT_NONPOSITIVE_PROPERTY")
        seen.add(identity)
        row["mode_identity"] = {"mode": mode, "basis": basis}
        rows.append(row)
    return rows


def native_eccentricity(record):
    """Native definition only: these coefficients are not applied torsion forces."""
    if not isinstance(record, dict) or set(record) != {"default_ratio", "override_lengths_m"}:
        raise SourceError("NATIVE_ECCENTRICITY_FIELDS_INVALID")
    ratio, overrides = record["default_ratio"], record["override_lengths_m"]
    if (type(ratio) not in (int, float) or not math.isfinite(ratio) or ratio < 0
            or not isinstance(overrides, dict)
            or any(not isinstance(k, str) or not k or k != k.strip()
                   or type(v) not in (int, float) or not math.isfinite(v) or v < 0 for k, v in overrides.items())):
        raise SourceError("NATIVE_ECCENTRICITY_VALUE_INVALID")
    return record


def _capture_modal_numbers(results, modes):
    methods = {}
    for method, fields in MODAL_RESULT_FIELDS.items():
        record = {"api": "Results." + method}
        try:
            raw = getattr(results, method)(0, *([] for _ in fields))
            if not isinstance(raw, (list, tuple)) or len(raw) != len(fields) + 2:
                raise SourceError("NATIVE_MODAL_RESULT_ABI_UNKNOWN")
            data = dict(zip(("NumberResults", *fields, "ret"), raw))
            # Keep the native return as source evidence even when validation fails.
            # CAPTURE_ERROR is never eligible for the numeric evidence owner.
            # Non-JSON values must not poison the otherwise valid source capture.
            if any(isinstance(value, (list, tuple)) and len(value) > MAX_FORCE_ROWS
                   for value in data.values()):
                raise SourceError("NATIVE_MODAL_RESULT_ARRAYS_INVALID")
            try:
                json.dumps(data, allow_nan=False)
            except (TypeError, ValueError):
                record["unserializable_native_values"] = [
                    {"field": field, "index": index, "type": type(value).__name__,
                     "representation": repr(value)[:160]}
                    for field, values in data.items()
                    for index, value in enumerate(values if isinstance(values, (tuple, list)) else [values])
                    if (type(value) not in (str, int, float, bool, type(None))
                        or type(value) is float and not math.isfinite(value))
                ][:32]
            else:
                record["data"] = data
            period = methods.get("ModalPeriod", {})
            native_modal_rows(data, method, modes,
                              period_record=period.get("data") if period.get("status") == "CAPTURED" else None)
            record.update(status="CAPTURED", data=data)
        except Exception as exc:
            record.update(status="CAPTURE_ERROR", error=f"{type(exc).__name__}: {exc}"[:400])
        methods[method] = record
    return {"schema": MODAL_RESULTS_SCHEMA, "units_code": 6, "methods": methods}


def _capture_spectrum_eccentricity(sap, cases):
    records = {}
    for case in cases:
        record = {"api": ["LoadCases.ResponseSpectrum.GetEccentricity",
                          "LoadCases.ResponseSpectrum.GetDiaphragmEccentricityOverride"]}
        try:
            api = sap.LoadCases.ResponseSpectrum
            default = api.GetEccentricity(case, 0.)
            overrides = api.GetDiaphragmEccentricityOverride(case, 0, [], [])
            if (not isinstance(default, (list, tuple)) or len(default) != 2
                    or type(default[-1]) is not int or default[-1] != 0
                    or not isinstance(overrides, (list, tuple)) or len(overrides) != 4
                    or type(overrides[-1]) is not int or overrides[-1] != 0):
                raise SourceError("NATIVE_ECCENTRICITY_ABI_OR_RETURN_INVALID")
            count, names, values, _ = overrides
            if count == 0:
                names = [] if names is None else names
                values = [] if values is None else values
            if (type(count) is not int or not 0 <= count <= 10000
                    or not isinstance(names, (list, tuple)) or not isinstance(values, (list, tuple))
                    or len(names) != count or len(values) != count or len(set(names)) != count):
                raise SourceError("NATIVE_ECCENTRICITY_OVERRIDE_ARRAYS_INVALID")
            # CSI overwrite values are absolute lengths, not eccentricity ratios.
            # The API exposes no separate story field; retain its identifiers as-is.
            data = native_eccentricity({"default_ratio": default[0], "override_lengths_m": dict(zip(names, values))})
            record.update(status="CAPTURED", data=data)
        except Exception as exc:
            record.update(status="CAPTURE_ERROR", error=f"{type(exc).__name__}: {exc}"[:400])
        records[case] = record
    return {"schema": ECCENTRICITY_SCHEMA, "units_code": 6, "cases": records}


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


def _mode_shape_option(setup):
    raw = setup.GetOptionModeShape(1, 1, False)
    if (not isinstance(raw, (tuple, list)) or len(raw) != 4
            or any(type(v) is not int for v in raw[:2]) or type(raw[2]) is not bool
            or type(raw[3]) is not int or raw[3] != 0):
        raise SourceError("FRAME_FORCE_MODE_OPTION_UNVERIFIED")
    return tuple(raw[:3])


def capture_frame_forces(sap, *, members: tuple[str, ...], combinations: tuple[str, ...] = (),
                         cases: tuple[str, ...] = (), modal_modes: dict | None = None,
                         spectrum_cases: tuple[str, ...] = ()) -> dict:
    """Capture six signed or envelope components and preserve each native result key."""
    if (not 0 < len(members) <= MAX_TARGET_FRAMES or len(set(members)) != len(members)
            or not 0 < len(combinations) + len(cases) <= MAX_RESPONSE_COMBINATIONS
            or len(set(combinations)) != len(combinations) or len(set(cases)) != len(cases)):
        raise SourceError("FRAME_FORCE_POPULATION_OUTSIDE_CAPTURE_SCOPE")
    requested_cases = set(cases)
    if len(set(spectrum_cases)) != len(spectrum_cases) or not set(spectrum_cases) <= requested_cases:
        raise SourceError("FRAME_FORCE_SPECTRUM_CASE_INVENTORY_INVALID")
    if modal_modes is not None and (not modal_modes or not set(modal_modes) <= requested_cases
            or any(not modes or any(type(m) is not int or m < 1 for m in modes)
                   or len(set(modes)) != len(modes) for modes in modal_modes.values())):
        raise SourceError("FRAME_FORCE_MODAL_INVENTORY_INVALID")
    if sap.GetModelIsLocked() is not True or sap.GetPresentUnits() != 6:
        raise SourceError("FRAME_FORCE_REQUIRES_LOCKED_KN_M_C")
    cases = _catalog_names(sap.LoadCases.GetNameList(0, [], 0))
    combos = _catalog_names(sap.RespCombo.GetNameList(0, []))
    wanted = set(combinations)
    if set(cases) & set(combos) or not wanted.issubset(combos):
        raise SourceError("FRAME_FORCE_COMBINATION_MISSING_FROM_NATIVE_CATALOG")
    if not requested_cases <= set(cases):
        raise SourceError("FRAME_FORCE_CASE_MISSING_FROM_NATIVE_CATALOG")

    results = sap.Results
    setup = results.Setup
    before = get_results_setup_state(setup, cases=cases, combos=combos)
    selected = {"cases": {c: c in requested_cases for c in cases}, "combos": {c: c in wanted for c in combos}}
    wanted |= requested_cases
    mode_before = _mode_shape_option(setup) if modal_modes else None
    mode_during = mode_before
    rowsets, errors = {}, {}
    modal_numbers = eccentricity = spectrum_inputs = None
    count = 0
    try:
        if before != selected:
            if return_code(setup.DeselectAllCasesAndCombosForOutput(), "DeselectAllCasesAndCombosForOutput") != 0:
                raise SourceError("FRAME_FORCE_OUTPUT_DESELECTION_REJECTED")
            for combo in combinations:
                if return_code(setup.SetComboSelectedForOutput(combo, True), "SetComboSelectedForOutput") != 0:
                    raise SourceError("FRAME_FORCE_OUTPUT_SELECTION_REJECTED:" + combo)
            for case in sorted(requested_cases):
                if return_code(setup.SetCaseSelectedForOutput(case, True), "SetCaseSelectedForOutput") != 0:
                    raise SourceError("FRAME_FORCE_CASE_SELECTION_REJECTED:" + case)
        if get_results_setup_state(setup, cases=cases, combos=combos) != selected:
            raise SourceError("FRAME_FORCE_OUTPUT_SELECTION_UNVERIFIED")
        if modal_modes:
            # Request ALL available modes, not the application's current display range.
            if return_code(setup.SetOptionModeShape(1, max(max(m) for m in modal_modes.values()), True),
                           "SetOptionModeShape") != 0:
                raise SourceError("FRAME_FORCE_MODE_SELECTION_REJECTED")
            mode_during = _mode_shape_option(setup)
            if mode_during[2] is not True:
                raise SourceError("FRAME_FORCE_ALL_MODES_NOT_SELECTED")

            # Same SapModel and selected output scope as the supporting frame forces.
            modal_numbers = _capture_modal_numbers(results, modal_modes)
        if spectrum_cases:
            eccentricity = _capture_spectrum_eccentricity(sap, spectrum_cases)
            spectrum_inputs = _capture_spectrum_inputs(sap, spectrum_cases)

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
        if modal_modes and _mode_shape_option(setup) != mode_during:
            raise SourceError("FRAME_FORCE_MODE_OPTION_CHANGED_DURING_READ")
    finally:
        restore_errors = []
        try:
            if before != selected:
                restore_results_setup_state(setup, before)
            after = get_results_setup_state(setup, cases=cases, combos=combos)
            if after != before:
                raise SourceError("FRAME_FORCE_OUTPUT_SELECTION_CHANGED")
        except Exception as exc:
            restore_errors.append(exc)
        # Restore independently: failure of one hook must not skip the other.
        if mode_before is not None:
            try:
                if return_code(setup.SetOptionModeShape(*mode_before), "SetOptionModeShape") != 0:
                    raise SourceError("FRAME_FORCE_MODE_RESTORE_REJECTED")
                mode_after = _mode_shape_option(setup)
                if mode_after != mode_before:
                    raise SourceError("FRAME_FORCE_MODE_RESTORE_MISMATCH")
            except Exception as exc:
                restore_errors.append(exc)
        if restore_errors:
            raise ForceSelectionRestoreError("ETABS frame-force output selection restoration failed") from restore_errors[0]

    if sap.GetModelIsLocked() is not True or sap.GetPresentUnits() != 6:
        raise SourceError("FRAME_FORCE_MODEL_LOCK_OR_UNITS_CHANGED")
    return {
        "schema": "tbdy.next.etabs-frame-force-source.v1",
        "api": "Results.FrameForce", "item_type": "ObjectElm", "units_code": 6,
        "output_selection_before": before, "output_selection_during": selected,
        "output_selection_after": after, "rowsets": rowsets, "errors": errors,
        **({"native_modal_results": modal_numbers} if modal_numbers is not None else {}),
        **({"native_spectrum_eccentricity": eccentricity} if eccentricity is not None else {}),
        **({"native_spectrum_inputs": spectrum_inputs} if spectrum_inputs is not None else {}),
        **({"mode_shape_option": {"before": list(mode_before), "during": list(mode_during),
                                  "after": list(mode_after)},
            "expected_modal_modes": {k: list(v) for k, v in sorted(modal_modes.items())}}
           if modal_modes else {}),
    }
