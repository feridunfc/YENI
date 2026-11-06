"""VS01: capture exactly one ETABS modal-mass table for TBDY Next Engine.

This product-owned Windows adapter is deliberately narrow.  It never saves a
model, launches analysis, changes present units or alters structural properties.
Only if needed, it temporarily selects an actual modal load-case for table
*display*, then restores and verifies the previous selection.

Run (with ETABS open and model already analyzed):
  .\\.venv\\Scripts\\python.exe -m pip install comtypes
  .\\.venv\\Scripts\\python.exe tools\\capture_modal_etabs23.py --case Modal \\
     --output .receipts\\etabs_modal_capture.json
  .\\.venv\\Scripts\\python.exe -m tbdy_next.cli check-modal \\
     --input .receipts\\etabs_modal_capture.json --case Modal --out .receipts

This is an observed table capture, not proof of analysis generation or release.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

TABLE_KEY = "Modal Participating Mass Ratios"
SCHEMA = "tbdy.next.modal.capture.v1"


class ModalCaptureError(RuntimeError):
    pass


def _code(raw: Any, op: str) -> int:
    v = raw[-1] if isinstance(raw, (list, tuple)) and raw else raw
    if type(v) is not int:
        raise ModalCaptureError(f"{op}: dönüş kodu tanınmıyor: {raw!r}")
    return v


def _selected_cases(db: Any) -> tuple[str, ...]:
    method = db.GetLoadCasesSelectedForDisplay
    try:
        raw = method()
    except TypeError:
        raw = method(0, [])
    if not isinstance(raw, (list, tuple)) or len(raw) < 3:
        raise ModalCaptureError("GetLoadCasesSelectedForDisplay: beklenmeyen dönüş şekli")
    count, payload = raw[0], raw[1]
    code = _code(raw, "GetLoadCasesSelectedForDisplay")
    if type(count) is not int or count < 0 or not isinstance(payload, (list, tuple)) or len(payload) < count:
        raise ModalCaptureError("GetLoadCasesSelectedForDisplay: sayı/dizi tutarsız")
    if count == 0 and code == 1 and all(v is None or v == "" for v in payload):
        return ()  # Observed ETABS 23.2 empty-selection projection
    if code != 0:
        raise ModalCaptureError(f"GetLoadCasesSelectedForDisplay: ret_code={code}")
    names = tuple(payload[:count])
    if any(not isinstance(x, str) or not x.strip() for x in names) or len(set(names)) != count:
        raise ModalCaptureError("GetLoadCasesSelectedForDisplay: geçersiz seçim")
    return names


def _set_cases(db: Any, values: tuple[str, ...]) -> None:
    request = list(values) if values else [""]  # CSI uses [""] for no selection
    code = _code(db.SetLoadCasesSelectedForDisplay(request), "SetLoadCasesSelectedForDisplay")
    if code != 0:
        raise ModalCaptureError(f"SetLoadCasesSelectedForDisplay: ret_code={code}")


def _read_table(db: Any) -> tuple[tuple[str, ...], list[dict[str, str]], int, str]:
    """Handle only known ETABS display-array projections; reject unrecognized ABI."""
    attempts = (
        ("seven_list", (TABLE_KEY, [], "", 0, [], 0, [])),
        ("seven_string", (TABLE_KEY, "", "", 0, [], 0, [])),
    )
    diagnostics = []
    for name, args in attempts:
        try:
            raw = db.GetTableForDisplayArray(*args)
            if not isinstance(raw, (list, tuple)) or len(raw) < 6:
                raise ModalCaptureError("dönüş şekli altı alan içermiyor")
            code = _code(raw, "GetTableForDisplayArray")
            if code != 0:
                raise ModalCaptureError(f"ret_code={code}")
            fields_raw, count_raw, data_raw = raw[2], raw[3], raw[4]
            if not isinstance(fields_raw, (tuple, list)) or not isinstance(data_raw, (tuple, list)):
                raise ModalCaptureError("alanlar ve veri dizisi bekleniyor")
            fields = tuple(fields_raw)
            if not fields or any(not isinstance(f, str) or not f for f in fields) or len(set(fields)) != len(fields):
                raise ModalCaptureError("alan listesi geçersiz veya tekrarlı")
            if type(count_raw) is not int or count_raw < 0:
                raise ModalCaptureError("kayıt sayısı geçersiz")
            cells = list(data_raw)
            if len(cells) != count_raw * len(fields):
                raise ModalCaptureError(f"hücre eksik/fazla: {len(cells)} != {count_raw}×{len(fields)}")
            rows = [dict(zip(fields, (str(v) for v in cells[i:i+len(fields)])))
                    for i in range(0, len(cells), len(fields))]
            return fields, rows, count_raw, name
        except (ModalCaptureError, TypeError, ValueError, AttributeError) as exc:
            diagnostics.append(f"{name}: {type(exc).__name__}: {exc}")
    raise ModalCaptureError("Modal tablo alınamadı; " + " | ".join(diagnostics))


def _model_name(sap: Any) -> str:
    raw = sap.GetModelFilename(True)
    if isinstance(raw, (tuple, list)):
        raw = raw[0]
    if not isinstance(raw, str) or not raw:
        raise ModalCaptureError("Aktif model adı okunamadı")
    return raw


def capture_modal(sap: Any, case: str) -> dict[str, Any]:
    if not isinstance(case, str) or not case.strip() or case != case.strip():
        raise ModalCaptureError("--case: kesin, boş olmayan vaka adı gerekli")
    db = sap.DatabaseTables
    model_name = _model_name(sap)
    original = _selected_cases(db)  # Snapshot before any temporary display mutation
    selected = original
    changed = False
    active_exc: Exception | None = None
    result: dict[str, Any] | None = None
    try:
        if case not in original:
            changed = True  # Set may mutate even if it raises; always attempt restoration
            _set_cases(db, (case,))
            selected = _selected_cases(db)
            if selected != (case,):
                raise ModalCaptureError(f"Geçici modal seçim doğrulanamadı: {selected!r}")
        fields, rows, count, signature = _read_table(db)
        if not rows:
            raise ModalCaptureError("Modal tablo boş; seçili analiz vakası ve mod ayarları incelenmeli")
        if "Case" not in fields:
            # Do not rewrite schema or silently approve aliases.
            raise ModalCaptureError(f"Canlı sütunlarda 'Case' yok: {fields!r}; hedefli şema incelemesi gerekli")
        selected_rows = [r for r in rows if r.get("Case") == case]
        if not selected_rows:
            raise ModalCaptureError(f"Modal tabloda '{case}' vakasının satırı yok")
        result = {
            "schema": SCHEMA,
            "source_mode": "LIVE_ETABS",
            "source_identity": "observed-model:" + hashlib.sha256(model_name.encode("utf-8")).hexdigest(),
            "table": {"table_key": TABLE_KEY, "fields": list(fields), "row_count": count, "rows": rows},
            "capture_metadata": {
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "model_filename": model_name,
                "case_requested": case,
                "case_row_count": len(selected_rows),
                "api_signature": signature,
                "display_selection_temporarily_changed": changed,
                "analysis_generation_proven": False,
                "engineering_release": "NOT_READY",
                "scope": "modal source table only; not full analysis-mode population proof",
            },
        }
    except Exception as exc:
        active_exc = exc
    finally:
        if changed:
            try:
                _set_cases(db, original)
                restored = _selected_cases(db)
                if restored != original:
                    raise ModalCaptureError(f"Eski ETABS vaka seçimi geri yüklenmedi: {restored!r} != {original!r}")
            except Exception as restore_exc:
                raise ModalCaptureError(f"ETABS görüntüleme seçimi geri yüklenemedi: {restore_exc}") from restore_exc
    if active_exc is not None:
        raise ModalCaptureError(str(active_exc)) from active_exc
    assert result is not None
    result["capture_metadata"]["display_selection_restored"] = True
    return result


