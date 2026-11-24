"""Stable tbdy-next CLI entrypoint for integrated source receipts."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tbdy_next.column_engine.native_archive import decode
from tbdy_next.etabs_modal import ModalCaptureError
from .live_column import review_live_column
from .story_pdelta import review_story_pdelta


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 8_000_000:
        raise ValueError("SOURCE_PATH_MISSING_OR_UNSAFE:" + str(path))
    data = decode(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError("SOURCE_JSON_MUST_BE_OBJECT:" + str(path))
    return data


def _write_new(path: Path, value: dict) -> None:
    if path.is_symlink() or path.exists():
        raise ValueError("RESULT_PATH_EXISTS_NO_OVERWRITE:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(value, out, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
        out.write("\n")


def _load_selection_arg(value: str | None, kind: str) -> dict | None:
    from .design_scenario import normalize_selection_overrides

    if not value:
        return None
    raw = "default" if value.strip().lower() == "default" else _read(Path(value))
    key = kind + "_selection"
    return normalize_selection_overrides({key: raw})[key]


def _run_pipeline_replay(args) -> int:
    from hashlib import sha256
    from tbdy_next.receipts import ReceiptRun, receipt_paths
    from .pipeline import EnginePipelineRunner

    from .design_scenario import prepare_pipeline_source, validate_design_scenario
    from ..archive_blobs import MAX_SOURCE_BYTES as _MAX_SOURCE_BYTES, archive_bytes

    if (args.source.is_symlink() or not args.source.is_file()
            or not 0 < args.source.stat().st_size <= _MAX_SOURCE_BYTES):
        raise ValueError("SOURCE_PATH_MISSING_OR_UNSAFE")
    raw = archive_bytes(args.source)
    beam_sel = _load_selection_arg(getattr(args, "beam_selection", None), "beam")
    col_sel = _load_selection_arg(getattr(args, "column_selection", None), "column")
    scenario_path = getattr(args, "design_scenario", None)
    if scenario_path is not None and (beam_sel is not None or col_sel is not None):
        raise ValueError("SCENARIO_AND_SELECTION_FLAGS_ARE_EXCLUSIVE")
    request = _read(scenario_path) if scenario_path is not None else None
    overrides = {key: value for key, value in (("beam_selection", beam_sel), ("column_selection", col_sel))
                 if value is not None}
    pier_forces = _read(args.pier_forces) if getattr(args, "pier_forces", None) else None
    pid = getattr(args, "etabs_pid", None)
    solve_copy = getattr(args, "solve_wall_copy", False)
    capture = getattr(args, "wall_replay_source", None)
    if capture is not None:
        from ..wall_analysis_replay import bind_private_wall_result
        if pid is not None or pier_forces or not args.whole_building or request is not None:
            raise ValueError("ONE_WHOLE_BUILDING_WALL_SOURCE_REQUIRED")
        if capture.is_symlink() or not capture.is_file() or not 0 < capture.stat().st_size <= _MAX_SOURCE_BYTES:
            raise ValueError("PRIVATE_WALL_READ_PATH_MISSING_OR_UNSAFE")
        pier_forces = bind_private_wall_result(decode(raw)["pier_section_forces"]["read"], decode(capture.read_bytes()))
    if solve_copy and pid is None:
        raise ValueError("PRIVATE_WALL_ANALYSIS_REQUIRES_AN_EXPLICIT_ETABS_PID")
    if pid is not None:
        if pid < 1 or not args.whole_building or pier_forces is not None or request is not None:
            raise ValueError("LIVE_WALL_READ_REQUIRES_ONE_WHOLE_BUILDING_SOURCE")
        from ..wall_batch_source import read_missing_wall_forces
        pier_forces = read_missing_wall_forces(decode(raw), raw, args.source.parent, pid,
                                              private_replay_root=args.out if solve_copy else None)
    prepared = prepare_pipeline_source(raw, source_directory=args.source.parent, request=request,
                                       selection_overrides=overrides or None,
                                       project_parameters=_read(args.project_parameters) if getattr(args, "project_parameters", None) else None,
                                       confirm_project_profile=getattr(args, "confirm_project_profile", None),
                                       whole_building=getattr(args, "whole_building", False),
                                       basement_matrices=getattr(args, "basement_matrices", None),
                                       basement_ground_storey=getattr(args, "basement_ground_storey", None),
                                       pier_forces=pier_forces,
                                       wall_hinge_aggregate_storeys=getattr(args, "wall_hinge_aggregate_storey", None))
    raw, payload = prepared.raw, prepared.payload
    scenario = validate_design_scenario(payload)
    input_sha = sha256(raw).hexdigest()
    run = ReceiptRun(args.out)
    run.archive_input(raw, expected_sha256=input_sha)
    prepared.archive_parent(run.root)
    suite = "geometry_capture" in payload or "analysis_sources" in payload
    stages = EnginePipelineRunner().run(payload, case=args.case, run=run, input_sha=input_sha, suite=suite)
    summary = {"run_dir": str(run.root), "input_sha256": input_sha,
               "engine_snapshot": stages["engine_snapshot"],
               "stages_recorded": [path.name for path in receipt_paths(run.root)],
               "column_gates": (stages["column_gates"] or {}).get("status"),
               "beam_r10": (stages.get("beam_r10") or {}).get("status"),
               "r10_joints": (stages.get("r10_live") or {}).get("joint_end_count"),
               "r08_local_slenderness": (stages.get("r08_local_slenderness") or {}).get("status"),
               "engineering_release": "NOT_READY", "engineering_verdict": "NOT_PROVEN"}
    summary["seismic_project_profile"] = stages["report_evidence"].get("seismic_project_profile")
    if getattr(args, "confirm_project_profile", None) is not None:
        from .seismic_input_review import require_reviewable
        require_reviewable(summary["seismic_project_profile"], args.confirm_project_profile)
    if scenario is not None:
        summary["design_scenario"] = scenario
    if scenario is not None and any(scenario["policies"].values()):
        summary["design_dependencies"] = stages["report_evidence"]["design_dependencies"]
        closure = stages.get("r14_closure") or {}
        summary["r14_closure"] = {key: closure.get(key) for key in
                                  ("status", "expected_column_count", "numerically_closed_count",
                                   "partial_or_unbound_count", "normative_fail_count")}
    if args.compare_run is not None:
        from .pipeline_snapshot import compare_runs
        summary["compare"] = compare_runs(args.compare_run, run.root)
    building = stages.get("building_design")
    if building:
        summary["building_design"] = {k: building[k] for k in
            ("column_count", "column_status_counts", "beam_count", "beam_status_counts", "storeys", "area_population")}
        if building.get("wall_sections"):
            summary["building_design"]["pier_checks"] = {k: building["wall_sections"][k] for k in
                ("basis", "expected_gravity", "evaluated_gravity", "gravity_exceedances",
                 "expected_shear_bounds", "evaluated_shear_bounds", "satisfied_shear_bounds", "expected_height_cuts",
                 "evaluated_height_cuts", "evaluated_height_shear", "evaluated_axial", "satisfied_height_shear", "evaluated_pmm_boxes",
                 "satisfied_pmm_boxes", "satisfied_sections", "expected_joints", "evaluated_joints", "satisfied_joints",
                 "expected_detail_panels", "evaluated_detail_panels", "satisfied_detail_panels",
                 "axial_limit_exceedances", "expected_strong_wall", "evaluated_strong_wall", "satisfied_strong_wall",
                 "conditional_seismic_sections", "conditional_piers")}
            summary["building_design"]["basement_piers"] = building["wall_sections"].get("basement_coverage")
            summary["building_design"]["wall_batch"] = (building["wall_sections"].get("batch") or {}).get("counts")
        summary["report_path"] = str(run.root / "report.html")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("compare", {}).get("status", "IDENTICAL") == "IDENTICAL" else 3

def run_cli(args) -> int:
    try:
        if args.action == "pipeline-plan":
            from .pipeline import dag_coverage, stage_registry
            print(json.dumps({"stages": stage_registry(), "dag_coverage": dag_coverage(),
                              "engineering_release": "NOT_READY"}, ensure_ascii=False, indent=2))
            return 0
        if args.action == "run-pipeline":
            return _run_pipeline_replay(args)
        if args.action == "reconcile-live-column":
            receipt = review_live_column(
                live=_read(args.live_receipt), lc_run=_read(args.lc_dl_run),
                combo=_read(args.combo_capture), pmm_run=_read(args.combo_pmm),
                geometry=_read(args.geometry))
            summary = {
                "status": receipt["r07"]["status"],
                "member": receipt["member"],
                "case": receipt["case"],
                "stations": len(receipt["r07"]["stations"]),
                "max_numeric_utilization": receipt["r07"]["maximum_numeric_utilization"],
                "r08": receipt["r08"]["status"],
                "r09": receipt["r09"]["status"],
            }
        elif args.action == "precheck-story-pdelta":
            receipt = review_story_pdelta(_read(args.input))
            summary = {
                "status": receipt["status"],
                "theta_max": receipt["theta_max"],
                "limits": receipt["limit_reference"],
                "global_second_order_proven": False,
            }
        else:
            raise ValueError("UNSUPPORTED_ENGINEERING_CLI_ACTION")
        _write_new(args.out, receipt)
        print(json.dumps({
            **summary, "result_file": str(args.out),
            "result_sha256": receipt["result_sha256"],
            "engineering_release": "NOT_READY", "engineering_verdict": "NOT_PROVEN",
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError, ModalCaptureError) as exc:
        print(json.dumps({
            "status": "BLOCKED_ENGINEERING_SOURCE",
            "reason": type(exc).__name__ + ":" + str(exc),
            "engineering_release": "NOT_READY",
        }, ensure_ascii=False))
        return 2
