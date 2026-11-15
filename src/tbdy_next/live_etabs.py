"""Windows-only, on-demand VS01 ETABS modal source access.

The local web handler never holds a COM proxy. Each request initializes COM on
its request thread, obtains the active ETABS session, and releases COM on that
same thread. A process-local lock serializes this application's acquisitions.
Connections for capture select and verify kN·m·°C on the locked model.
The model stays locked and the API units remain selected for the session.
"""
from __future__ import annotations

from ntpath import basename, normcase
import sys
from threading import Lock
from typing import Callable

from .etabs_modal import ModalCaptureError, _model_name, capture_modal

_CAPTURE_LOCK = Lock()
_ETABS_OBJECT = "CSI.ETABS.API.ETABSObject"
CAPTURE_UNIT_CODE = 6
CAPTURE_UNIT_LABEL = "kN·m·°C"
_FORCE_UNITS = (None, "lb", "kip", "N", "kN", "kgf", "tonf")
_LENGTH_UNITS = (None, "in", "ft", "µm", "mm", "cm", "m")
_TEMPERATURE_UNITS = (None, "°F", "°C")
# Force, length and temperature enums in CSI's eUnits order.
_UNIT_COMPONENTS = (
    (1, 1, 1), (1, 2, 1), (2, 1, 1), (2, 2, 1),
    (4, 4, 2), (4, 6, 2), (5, 4, 2), (5, 6, 2),
    (3, 4, 2), (3, 6, 2), (6, 4, 2), (6, 6, 2),
    (4, 5, 2), (5, 5, 2), (3, 5, 2), (6, 5, 2),
)


class EtabsUnitsError(ModalCaptureError):
    def __init__(self, session: dict):
        super().__init__(
            f"LIVE_ETABS_UNITS_KN_M_C_REQUIRED:expected={CAPTURE_UNIT_CODE};"
            f"observed={session['units_code']!r}"
        )
        self.session = session


def _supports_capture_units(session: dict) -> bool:
    return session["units_code"] == CAPTURE_UNIT_CODE and session["units_api_agree"] is not False


def _attach_etabs(client, process_id: int | None):
    if process_id is None:
        return client.GetActiveObject(_ETABS_OBJECT)
    if type(process_id) is not int or not 1 <= process_id <= 2_147_483_647:
        raise ModalCaptureError("Enter a positive Windows ETABS process ID.")
    helper = client.CreateObject("ETABSv1.Helper")
    app = helper.GetObjectProcess(_ETABS_OBJECT, process_id)
    if not app:
        raise ModalCaptureError(f"ETABS PID {process_id} is unavailable in this Windows session.")
    return app


def _units_observation(sap) -> tuple[int | None, tuple[int, int, int] | None, bool | None]:
    raw = sap.GetPresentUnits()
    unit_code = raw if type(raw) is int else None
    expected = (_UNIT_COMPONENTS[unit_code - 1]
                if unit_code is not None and 1 <= unit_code <= len(_UNIT_COMPONENTS) else None)
    # Older ETABS interfaces may omit the second method. Its availability or
    # failure does not substitute for the numerical pipeline's enum-six gate.
    try:
        split = sap.GetPresentUnits_2(0, 0, 0)
    except Exception:
        return unit_code, expected, None
    if (not isinstance(split, (tuple, list)) or len(split) != 4
            or not all(type(value) is int for value in split) or split[3] != 0):
        return unit_code, expected, None
    parts = tuple(split[:3])
    return unit_code, parts if parts in _UNIT_COMPONENTS else None, parts == expected


def _unit_label(parts: tuple[int, int, int] | None) -> str | None:
    if parts is None:
        return None
    force, length, temperature = parts
    return f"{_FORCE_UNITS[force]}·{_LENGTH_UNITS[length]}·{_TEMPERATURE_UNITS[temperature]}"


def _session_info(sap, process_id: int | None, locked: bool) -> dict:
    unit_code, parts, units_agree = _units_observation(sap)
    try:
        name = basename(_model_name(sap))
    except ModalCaptureError:
        name = None
    return {
        "model_name": name, "model_locked": locked,
        "process_id": process_id, "attachment": "PROCESS_ID" if process_id else "ACTIVE_INSTANCE",
        "units_code": unit_code, "units_label": _unit_label(parts), "units_api_agree": units_agree,
    }


def _with_etabs(process_id: int | None, action: Callable) -> dict:
    if sys.platform != "win32":
        raise ModalCaptureError("Live ETABS is available on Windows.")
    import comtypes
    import comtypes.client

    with _CAPTURE_LOCK:
        comtypes.CoInitialize()
        app = None
        sap = None
        try:
            app = _attach_etabs(comtypes.client, process_id)
            sap = app.SapModel
            if sap is None:
                raise ModalCaptureError("Could not access ETABS SapModel.")
            return action(sap)
        finally:
            sap = None
            app = None
            comtypes.CoUninitialize()


def read_etabs_session(process_id: int | None = None) -> dict:
    """Identify the attached ETABS model without reading tables or changing settings."""
    return _with_etabs(process_id, lambda sap: _session_info(sap, process_id, sap.GetModelIsLocked() is True))


def _verify_connection(sap, filename: str, session: dict) -> None:
    if not session["model_locked"] or _model_name(sap) != filename:
        raise ModalCaptureError("The ETABS model or lock state changed during capture.")


def _prepare_etabs_session(sap, process_id: int | None) -> tuple[str, dict, dict]:
    if sap.GetModelIsLocked() is not True:
        raise ModalCaptureError("Live capture requires a locked ETABS model with available analysis results.")
    filename = _model_name(sap)
    before = _session_info(sap, process_id, True)
    if _supports_capture_units(before):
        return filename, before, before

    result = sap.SetPresentUnits(CAPTURE_UNIT_CODE)
    after = _session_info(sap, process_id, sap.GetModelIsLocked() is True)
    _verify_connection(sap, filename, after)
    if type(result) is not int or result != 0 or not _supports_capture_units(after):
        # The two CSI setters use different API entry points. Verify the same
        # required enum after either setter before any numeric table is read.
        force, length, temperature = _UNIT_COMPONENTS[CAPTURE_UNIT_CODE - 1]
        try:
            result = sap.SetPresentUnits_2(force, length, temperature)
        except AttributeError:
            raise EtabsUnitsError(after) from None
        after = _session_info(sap, process_id, sap.GetModelIsLocked() is True)
        _verify_connection(sap, filename, after)
        if type(result) is not int or result != 0 or not _supports_capture_units(after):
            raise EtabsUnitsError(after)
    return filename, before, after


def select_etabs_capture_units(process_id: int | None = None) -> dict:
    """Connect to the selected locked model and leave its API units in kN·m·°C."""
    def select(sap):
        _, before, after = _prepare_etabs_session(sap, process_id)
        return {"before": before, "after": after}

    return _with_etabs(process_id, select)


def _capture_on_connected_model(
    process_id: int | None, capture: Callable, *, expected_filename: str | None = None,
) -> dict:
    def run(sap):
        if expected_filename and normcase(_model_name(sap)) != normcase(expected_filename):
            raise ModalCaptureError("The active ETABS model differs from the selected source run.")
        filename, before, session = _prepare_etabs_session(sap, process_id)
        payload = capture(sap)
        after = _session_info(sap, process_id, sap.GetModelIsLocked() is True)
        _verify_connection(sap, filename, after)
        if not _supports_capture_units(after):
            raise EtabsUnitsError(after)
        payload["capture_metadata"].update(
            live_connection="ATTACHED_EXISTING_SESSION", model_locked_observed=True,
            etabs_session_before_scan=before, etabs_session=session, etabs_session_after_scan=after,
        )
        return payload

    return _with_etabs(process_id, run)


def read_modal_from_running_etabs(case: str, *, process_id: int | None = None) -> dict:
    """Read one case of the live ETABS modal table, restoring display selection."""
    if sys.platform != "win32":
        raise ModalCaptureError("Live ETABS is available on Windows.")
    if not isinstance(case, str) or not case or case != case.strip() or len(case) > 120:
        raise ModalCaptureError("Enter a valid modal case name.")

    return _capture_on_connected_model(process_id, lambda sap: capture_modal(sap, case))


def read_quick_suite_from_running_etabs(
    case: str, *, with_vs04: bool = False, process_id: int | None = None,
    column_axial_request: dict | None = None,
) -> dict:
    """Read modal + six exact geometry tables under one Windows COM session."""
    if sys.platform != "win32":
        raise ModalCaptureError("Live ETABS is available on Windows.")
    if not isinstance(case, str) or not case or case != case.strip() or len(case) > 120:
        raise ModalCaptureError("Enter a valid modal case name.")
    if column_axial_request is not None and not with_vs04:
        raise ModalCaptureError("Column axial capture requires the combined source run.")
    from .etabs_geometry import capture_geometry
    from .next_capture import capture_next_facts

    def capture(sap):
        payload = capture_modal(sap, case)
        payload["geometry_capture"] = capture_geometry(sap)
        payload["next_capture"] = capture_next_facts(sap, x_case="RSX", y_case="RSY")
        if with_vs04:
            from .analysis_sources import capture_analysis_sources
            payload["analysis_sources"] = capture_analysis_sources(sap, modal_case=case)
            payload["analysis_sources"]["numeric_stage_required"] = True
            payload["analysis_sources"]["readiness_stage_required"] = True
            # VS04-E/G source tables share this exact locked SapModel,
            # thread and COM session. Never open a second ETABS instance.
            from .basis_probe import capture_basis_probe
            from .diaphragm_probe import capture_diaphragm_modal_probe
            payload["vs04_basis_probe"] = capture_basis_probe(sap)
            payload["vs04_diaphragm_probe"] = capture_diaphragm_modal_probe(sap)
            payload["analysis_sources"]["pipeline_stage_required"] = True
            payload["analysis_sources"]["pipeline_contract_version"] = "v2"
            payload["capture_metadata"]["vs04_same_session_capture"] = True
            if column_axial_request is not None:
                from .engineering.column_axial import capture_column_axial
                payload["column_axial"] = capture_column_axial(sap, payload, column_axial_request)
            # VS05 STORY_DRIFT: reuse the ALREADY ACTIVE SapModel and
            # existing generic table gateway.  No second COM attach.
            try:
                from .etabs_source_gateway_windows import capture as capture_tables
                payload["vs05_delta_source"] = capture_tables(
                    sap, action="capture", preset="delta",
                    cases=(case, "RSX", "RSY"))
            except Exception as exc:
                # Do not lose accepted VS04 checks if an optional
                # VS05 table is unavailable.  Persist a BLOCKED check.
                payload["vs05_delta_capture_error"] = (
                    f"{type(exc).__name__}: {exc}")
            # VS06-C2: OPTIONAL exact LoadPattern=LC_WDL assignment evidence.
            # Same existing COM session and general table reader; no
            # new COM connection or ETABS model mutation. When the DB table
            # returns 1, probe the same beam objects via read-only FrameObj.
            # Unknown schema is
            # preserved as source-only, never guessed into wall area.
            try:
                from .etabs_source_gateway_windows import capture as capture_tables
                payload["vs06_wall_load_source"] = capture_tables(
                    sap, action="capture",
                    exact=("Frame Loads Assignments - Distributed", "Beam Object Connectivity"),
                    frame_load_probe=True)
            except Exception as exc:
                payload["vs06_wall_capture_error"] = (
                    f"{type(exc).__name__}: {exc}")
            # VS06-D1: X/Y B1 geometry via the SAME generic source reader
            # and already owned COM session, not a separate live workflow.
            # B1 remains optional, old accepted checks survive a missing
            # table while the exact cause is preserved.
            try:
                from .etabs_source_gateway_windows import capture as capture_tables
                payload["vs06_b1_geometry_source"] = capture_tables(
                    sap, action="capture",
                    exact=(
                        "Point Object Connectivity",
                        "Column Object Connectivity",
                        "Wall Object Connectivity",
                        "Frame Assignments - Section Properties",
                        "Frame Section Property Definitions - Concrete Rectangular",
                        "Area Assignments - Section Properties",
                        "Wall Property Definitions - Specified",
                        "Story Definitions",
                    ))
            except Exception as exc:
                payload["vs06_b1_geometry_capture_error"] = (
                    f"{type(exc).__name__}: {exc}")
            # R08: same SapModel / same COM thread; RSX/RSY and WGHT
            # selections are restored even on source failure. A source
            # failure blocks ONLY this new check, never accepted VS01–VS06.
            try:
                from .story_second_order_capture import capture_story_second_order
                payload["r08_second_order_source"] = capture_story_second_order(sap)
            except Exception as exc:
                payload["r08_second_order_capture_error"] = (
                    f"{type(exc).__name__}: {exc}")
        return payload

    return _capture_on_connected_model(
        process_id, capture, expected_filename=(column_axial_request or {}).get("model_filename"),
    )
