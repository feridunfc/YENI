"""Shared source acquisition for whole-building CLI and web runs."""

from hashlib import sha256
import json
from threading import Lock

LIVE_CAPTURE_LOCK = Lock()


def read_missing_wall_forces(payload, raw, directory, pid, *, private_replay_root=None):
    """Reuse a complete wall read or enrich the original source using the selected ETABS session."""
    from .engineering.pier_force_source import ORIGINAL

    basis = payload.get("pier_section_forces") or {}
    if pid is None or (basis and basis.get("kind") != ORIGINAL):
        return None
    from .engineering.design_scenario import _read_verified_parent
    from .etabs_source_gateway_windows import capture_assigned_pier_forces
    from .live_etabs import _with_etabs

    parent_raw = _read_verified_parent(directory, payload) if payload.get("design_scenario") else raw
    parent = json.loads(parent_raw)
    if not (parent.get("column_axial", {}).get("force_source") or {}).get("rowsets"):
        return None
    previous = basis.get("read") or {}
    modes = previous.get("wall_modes")
    if modes:
        if previous.get("transition_shells"):
            return None
        from .engineering.wall_transition_shell import native_plan

        labels = previous["tables"]["table_reads"]["Area Assignments - Pier Labels"]["rows"]
        if not native_plan(parent, labels)[0]:
            return None
    modal_bank = (parent["column_axial"].get("demand_support") or {}).get("force_source") or {}
    modal_ready = bool(modal_bank.get("expected_modal_modes") and modal_bank.get("rowsets"))
    if modal_ready:
        from .wall_modal_capture import wall_cut_plan

        try:
            plans, _ = wall_cut_plan(parent)
            modal_ready = bool(plans)
        except (KeyError, ValueError, TypeError):
            modal_ready = False
    if basis and not modal_ready:
        return None
    if not LIVE_CAPTURE_LOCK.acquire(blocking=False):
        raise ValueError("ETABS_CAPTURE_IN_PROGRESS")
    try:
        if private_replay_root is not None:
            from .wall_analysis_replay import solve_private_wall_source

            return _with_etabs(
                pid,
                lambda sap: solve_private_wall_source(
                    sap, pid, parent, sha256(parent_raw).hexdigest(), previous, private_replay_root
                ),
            )
        return _with_etabs(
            pid,
            lambda sap: capture_assigned_pier_forces(
                sap, pid, parent, sha256(parent_raw).hexdigest(), wall_modes=modal_ready, retained_modes=modes
            ),
        )
    finally:
        LIVE_CAPTURE_LOCK.release()
