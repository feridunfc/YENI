"""Product-owned same-session ETABS R08 read-only source capture.

Runs ONLY under live_etabs._CAPTURE_LOCK with a pre-analyzed locked model.
The generic gateway reads and sets combination display selection. This adapter
restores and verifies the original selection after the R08 captures.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .story_second_order import CAPTURE_SCHEMA

SPECTRUM_TABLES = (
    "Story Forces", "Story Max Over Avg Drifts", "Story Definitions",
    "Tower and Base Story Definitions", "Base Reactions",
    "Mass Summary by Story", "Mass Source Definition",
    "Load Combination Definitions", "Load Case Definitions - Summary",
)
WEIGHT_TABLES = ("Story Forces", "Base Reactions")


class StorySecondOrderCaptureError(ValueError):
    pass


def read_candidate_configuration() -> dict[str, str]:
    path = (Path(__file__).resolve().parents[2] / "config" /
            "second_order_kompakt_b_candidate.json")
    if not path.is_file():
        path = (Path(__file__).resolve().parent / "config" /
                "second_order_kompakt_b_candidate.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict)
            or data.get("schema") != "tbdy.next.r08.project-candidate-config.v1"
            or data.get("engineering_approval") is not False
            or not isinstance(data.get("parameters"), dict)):
        raise StorySecondOrderCaptureError("R08_PROJECT_CONFIGURATION_NOT_REVIEWED")
    return data["parameters"]


def capture_story_second_order(sap: Any, *,
                               configuration: Mapping[str, str] | None = None) -> dict[str, Any]:
    from .etabs_source_gateway_windows import SourceError, capture as gateway_capture, selected_combinations, set_combinations
    from .etabs_modal import _model_name
    if sap.GetModelIsLocked() is not True or sap.GetPresentUnits() != 6:
        raise StorySecondOrderCaptureError("R08_LOCKED_KN_M_C_REQUIRED")
    config = dict(configuration if configuration is not None
                  else read_candidate_configuration())
    if set(config) != {"x_case", "y_case", "weight_combo", "R", "D", "Ch",
                       "live_model_basename"}:
        raise StorySecondOrderCaptureError("R08_CONFIGURATION_KEYS_INVALID")
    model = _model_name(sap)
    if model.replace("\\", "/").split("/")[-1].casefold() != config["live_model_basename"].casefold():
        raise StorySecondOrderCaptureError("R08_PROJECT_MODEL_CONFIGURATION_MISMATCH")
    db = sap.DatabaseTables
    try:
        initial = selected_combinations(db)
    except SourceError as exc:
        raise StorySecondOrderCaptureError("R08_COMBINATION_SELECTION_UNAVAILABLE: " + str(exc)) from exc
    before_units = sap.GetPresentUnits()
    spectrum = None
    weight = None
    error: Exception | None = None
    changed = False
    try:
        spectrum = gateway_capture(
            sap, action="capture", cases=(config["x_case"], config["y_case"]),
            exact=SPECTRUM_TABLES)
        if spectrum.get("status") != "CAPTURED":
            raise StorySecondOrderCaptureError("R08_SPECTRUM_TABLES_INCOMPLETE")
        desired = (config["weight_combo"],)
        if initial != desired:
            changed = True  # Setter may mutate even if it raises.
            set_combinations(db, desired)
            if selected_combinations(db) != desired:
                raise StorySecondOrderCaptureError("R08_COMBO_DISPLAY_SELECTION_NOT_CONFIRMED")
        weight = gateway_capture(sap, action="capture", exact=WEIGHT_TABLES)
        if weight.get("status") != "CAPTURED":
            raise StorySecondOrderCaptureError("R08_WEIGHT_TABLES_INCOMPLETE")
    except Exception as exc:
        error = exc
    finally:
        if changed:
            try:
                set_combinations(db, initial)
                if selected_combinations(db) != initial:
                    raise StorySecondOrderCaptureError("R08_COMBO_DISPLAY_RESTORE_MISMATCH")
            except Exception as exc:
                raise StorySecondOrderCaptureError("CRITICAL_R08_COMBINATION_RESTORE_FAILED: " +
                                                   str(exc)) from exc
    if error is not None:
        raise StorySecondOrderCaptureError("R08_SOURCE_CAPTURE_FAILED: " + str(error)) from error
    restored = selected_combinations(db)
    if (sap.GetPresentUnits() != before_units or sap.GetModelIsLocked() is not True
            or restored != initial or _model_name(sap) != model):
        raise StorySecondOrderCaptureError("CRITICAL_R08_SAPMODEL_CHANGED_DURING_CAPTURE")
    if spectrum.get("model") != model or weight.get("model") != model:
        raise StorySecondOrderCaptureError("R08_CROSS_SOURCE_MODEL_MISMATCH")
    return {
        "schema": CAPTURE_SCHEMA, "status": "CAPTURED",
        "same_sapmodel_session": True, "analysis_generation_proven": False,
        "configuration_approved": False, "configuration": config,
        "model": model, "spectrum_source": spectrum, "weight_source": weight,
        "combination_selection_before": list(initial),
        "combination_selection_after": list(restored),
        "combination_selection_restored": True,
        "model_locked": True, "model_units_code": before_units,
        "source_only": True, "engineering_release": "NOT_READY",
    }
