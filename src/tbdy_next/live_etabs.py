"""Windows-only, on-demand VS01 ETABS modal source access.

The local web handler never holds a COM proxy. Each request initializes COM on
its request thread, obtains the active ETABS session, and releases COM on that
same thread. A process-local lock serializes this application's acquisitions.
No analysis, model save, design execution or unit changes occur here.
"""
from __future__ import annotations

from threading import Lock
import sys

from .etabs_modal import ModalCaptureError, capture_modal

_CAPTURE_LOCK = Lock()


def read_modal_from_running_etabs(case: str) -> dict:
    """Read one case of the live ETABS modal table, restoring display selection."""
    if sys.platform != "win32":
        raise ModalCaptureError("Canlı ETABS bağlantısı yalnız Windows üzerinde kullanılabilir.")
    if not isinstance(case, str) or not case or case != case.strip() or len(case) > 120:
        raise ModalCaptureError("Geçerli bir modal vaka adı gerekli.")

    # Run all COM operations on one initialized request thread, never transfer
    # raw COM pointers to the server or to other worker threads.
    import comtypes
    import comtypes.client

    with _CAPTURE_LOCK:
        comtypes.CoInitialize()
        etabs = None
        sap = None
        try:
            etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
            sap = etabs.SapModel
            if sap is None:
                raise ModalCaptureError("ETABS SapModel alınamadı.")
            # Locked is a bounded prerequisite for this already-analyzed model
            # workflow; it is NOT a proof of analysis-generation freshness.
            locked = sap.GetModelIsLocked()
            if type(locked) is not bool:
                raise ModalCaptureError("ETABS model kilit durumu kesin olarak okunamadı.")
            if not locked:
                raise ModalCaptureError("ETABS modeli kilitli değil; analiz BAŞLATILMADI, önce mevcut analiz durumunu kontrol edin.")
            data = capture_modal(sap, case)
            data["capture_metadata"]["live_connection"] = "ATTACHED_EXISTING_SESSION"
            data["capture_metadata"]["model_locked_observed"] = True
            return data
        finally:
            # Release COM proxies on the same initialized thread.
            sap = None
            etabs = None
            comtypes.CoUninitialize()


def read_quick_suite_from_running_etabs(case: str, *, with_vs04: bool = False) -> dict:
    """Read modal + six exact geometry tables under one Windows COM session."""
    if sys.platform != "win32":
        raise ModalCaptureError("Canlı ETABS bağlantısı yalnız Windows üzerinde kullanılabilir.")
    if not isinstance(case, str) or not case or case != case.strip() or len(case) > 120:
        raise ModalCaptureError("Geçerli bir modal vaka adı gerekli.")
    from .etabs_geometry import capture_geometry
    from .next_capture import capture_next_facts
    import comtypes
    import comtypes.client
    with _CAPTURE_LOCK:
        comtypes.CoInitialize()
        etabs = None
        sap = None
        try:
            etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
            sap = etabs.SapModel
            if sap is None or sap.GetModelIsLocked() is not True:
                raise ModalCaptureError("ETABS modeli analizli ve kilitli olmalıdır; analiz başlatılmadı.")
            payload = capture_modal(sap, case)
            payload["capture_metadata"]["live_connection"] = "ATTACHED_EXISTING_SESSION"
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
                # VS05 STORY_DRIFT: reuse the ALREADY ACTIVE SapModel and
                # existing generic table gateway.  No second COM attach.
                try:
                    from tools.etabs_source_gateway_windows import capture as capture_tables
                    payload["vs05_delta_source"] = capture_tables(
                        sap, action="capture", preset="delta",
                        cases=(case, "RSX", "RSY"))
                except Exception as exc:
                    # Do not lose accepted VS04 checks if an optional
                    # VS05 table is unavailable.  Persist a BLOCKED check.
                    payload["vs05_delta_capture_error"] = (
                        f"{type(exc).__name__}: {exc}")
                # VS06-C2: OPTIONAL exact LoadPat=LC_WALL assignment evidence.
                # Same existing COM session and general table reader; no
                # new reader or ETABS model mutation. Unknown schema is
                # preserved as source-only, never guessed into wall area.
                try:
                    from tools.etabs_source_gateway_windows import capture as capture_tables
                    payload["vs06_wall_load_source"] = capture_tables(
                        sap, action="capture",
                        exact=("Frame Loads - Distributed", "Beam Object Connectivity"))
                except Exception as exc:
                    payload["vs06_wall_capture_error"] = (
                        f"{type(exc).__name__}: {exc}")
            return payload
        finally:
            sap = None
            etabs = None
            comtypes.CoUninitialize()
