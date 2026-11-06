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
