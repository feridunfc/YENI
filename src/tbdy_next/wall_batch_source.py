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
    from .wall_pressure_capture import extend_pressure_read, pressure_field_plan
    parent_sha = sha256(parent_raw).hexdigest()
    from .engineering.wall_pressure_shell import SCHEMA
    existing = previous.get("pressure_shells") or {}
    complete = existing.get("schema") == SCHEMA and bool(existing.get("edge_actions"))
    pressure_plan = {} if complete else pressure_field_plan(payload)
    if modes:
        from .engineering.wall_transition_shell import native_plan

        labels = previous["tables"]["table_reads"]["Area Assignments - Pier Labels"]["rows"]
        if previous.get("transition_shells") or not native_plan(parent, labels)[0]:
            if not pressure_plan:
                return None
            def read_pressure(sap):
                from .wall_analysis_replay import active_wall_reference
                reference = active_wall_reference(sap, previous, parent_sha, private_replay_root)
                try:
                    return extend_pressure_read(sap, pid, parent, parent_sha, reference, pressure_plan)
                except (ValueError, RuntimeError) as exc:
                    # Only an explicit copy solve can recover unavailable or different native results.
                    if private_replay_root is None or not (str(exc).startswith("PIER_SOLVED_GENERATION_FRAME_CONTROL_MISMATCH")
                            or "requires a locked ETABS model" in str(exc)):
                        raise
                    from .wall_analysis_replay import solve_private_wall_source
                    return solve_private_wall_source(sap,pid,parent,parent_sha,reference,private_replay_root,
                                                     pressure_plan=pressure_plan)
            if not LIVE_CAPTURE_LOCK.acquire(blocking=False):
                raise ValueError("ETABS_CAPTURE_IN_PROGRESS")
            try:
                return _with_etabs(pid, read_pressure)
            finally:
                LIVE_CAPTURE_LOCK.release()
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
        def acquire(sap):
            if private_replay_root is not None and modes:
                from .wall_analysis_replay import solve_private_wall_source
                return solve_private_wall_source(sap,pid,parent,parent_sha,previous,private_replay_root,
                                                 pressure_plan=pressure_plan)
            read = capture_assigned_pier_forces(sap,pid,parent,parent_sha,wall_modes=modal_ready,retained_modes=modes)
            if not payload.get("analysis_archive"):
                return read
            from .engineering.design_scenario import prepare_pipeline_source
            attached = prepare_pipeline_source(raw,source_directory=directory,whole_building=True,pier_forces=read)
            targets = pressure_field_plan(attached.payload)
            return extend_pressure_read(sap,pid,parent,parent_sha,read,targets) if targets else read

        return _with_etabs(pid,acquire)
    finally:
        LIVE_CAPTURE_LOCK.release()
