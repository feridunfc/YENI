"""Local VS01 web UI: explicit, user-triggered Windows ETABS connection.

A live POST captures one modal table on a COM-initialized worker, then uses the
same owned schema, modal and receipt functions as the CLI. Never saves or runs
ETABS analysis; localhost only. Existing offline import remains optional.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import ntpath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from .wall_batch_source import LIVE_CAPTURE_LOCK as _LIVE_CAPTURE_LOCK, read_missing_wall_forces
from . import __version__
from .check_labels import display_check_group
from .live_etabs import CAPTURE_UNIT_CODE, CAPTURE_UNIT_LABEL, EtabsConnectionError, EtabsUnitsError
from .modal import evaluate_modal_mass
from .history import _MAX_SOURCE_BYTES, modal_history, modal_source_table, quick_history
from .quick_checks import check_registry, evaluate_geometry_capture
from .next_checks import evaluate_next_capture
from .analysis_sources import review_analysis_sources
from .analysis_numerics import evaluate_analysis_numerics
from .normative_basis import review_normative_readiness
from .live_source_pipeline import evaluate_single_run_source_pipeline
from .member_groups import material_member_groups
from .reporting import ReportUnavailable, build_complete_report, build_printable_html
from .receipts import ReceiptRun, receipt_paths
from .schema import review_modal_schema
from .source import SourceError, parse_modal_capture, review_preflight

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
_RUN_ID_PATTERN = re.compile(r"RUN-[a-f0-9]{32}\Z")


def _parse_rebar_selection_spec(raw_value: Any, kind: str) -> dict[str, Any] | None:
    from .engineering.design_scenario import normalize_selection_overrides

    if isinstance(raw_value, str):
        if len(raw_value) > 32_000:
            raise ValueError(f"Rebar selection payload too large: {kind}")
        parsed = "default" if raw_value.strip().lower() in ("default", "true", "1") else json.loads(raw_value)
    else:
        parsed = raw_value
    key = kind + "_selection"
    return normalize_selection_overrides({key: parsed})[key]


def _execute_and_reply_live_payload(
    handler: Any,
    output_root: Path,
    payload: dict[str, Any],
    case: str,
    *,
    suite: bool,
    source_raw: bytes | None = None,
    source_directory: Path | None = None,
    selection_overrides: Mapping[str, Any] | None = None,
    scenario_request: Mapping[str, Any] | None = None,
    whole_building: bool = False,
    pier_forces: Mapping[str, Any] | None = None,
    wall_hinge_aggregate_storeys: list[str] | None = None,
) -> None:
    from .engineering.design_scenario import prepare_pipeline_source

    raw = (source_raw if source_raw is not None else
           json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    if len(raw) > _MAX_SOURCE_BYTES:
        handler.reply(422, {"status": "CAPTURE_REJECTED", "reason": "ETABS_SOURCE_ARCHIVE_TOO_LARGE"})
        return
    try:
        prepared = prepare_pipeline_source(raw, source_directory=source_directory,
                                           selection_overrides=selection_overrides, request=scenario_request,
                                           whole_building=whole_building,
                                           pier_forces=pier_forces,
                                           wall_hinge_aggregate_storeys=wall_hinge_aggregate_storeys)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        handler.reply(422, {"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"})
        return
    raw, payload = prepared.raw, prepared.payload
    input_sha = sha256(raw).hexdigest()
    run = ReceiptRun(output_root)
    run.archive_input(raw, expected_sha256=input_sha)
    prepared.archive_parent(run.root)
    try:
        # One owner for stage order: engineering/pipeline.py (registry + runner).
        from .engineering.pipeline import EnginePipelineRunner
        stages = EnginePipelineRunner().run(payload, case=case, run=run, input_sha=input_sha, suite=suite)
        result, geometry, extra = stages["result"], stages["geometry"], stages["extra"]
        vs04, vs04_numerics = stages["vs04"], stages["vs04_numerics"]
        vs04_readiness, vs04_pipeline = stages["vs04_readiness"], stages["vs04_pipeline"]
        story_drift, analysis_setup = stages["story_drift"], stages["analysis_setup"]
        analysis_setup_reconciliation = stages.get("analysis_setup_reconciliation")
        column_axial, column_pmm = stages["column_axial"], stages["column_pmm"]
        column_gates, beam_r10, r10_live = stages["column_gates"], stages.get("beam_r10"), stages["r10_live"]
        r08_second_order, r08_local_slenderness = stages["r08_second_order"], stages.get("r08_local_slenderness")
        r14_closure = stages.get("r14_closure")
        axial_ledger = stages["report_evidence"].get("column_axial_expected_instances")
        pmm_scope = stages["report_evidence"].get("column_pmm_expected_instances")
        meta = payload.get("capture_metadata") or {}
        handler.reply(200, {
            "run_id": run.run_id, "result": result,
            "engine_snapshot": stages["engine_snapshot"],
            **({"building_design": stages["report_evidence"]["building_design"]}
               if "building_design" in stages["report_evidence"] else {}),
            "model_name": ntpath.basename(str(meta.get("model_filename", ""))),
            "case_row_count": meta.get("case_row_count"),
            "source_rows": payload["table"]["row_count"],
            "source_mode": "LIVE_ETABS", "geometry": display_check_group(geometry),
            **({"etabs_session": meta["etabs_session"]} if "etabs_session" in meta else {}),
            **({"etabs_session_after_scan": meta["etabs_session_after_scan"]}
               if "etabs_session_after_scan" in meta else {}),
            "extra_checks": display_check_group(extra),
            "material_member_groups": material_member_groups(geometry["checks"] if geometry else []),
            "vs04_schema": vs04, "vs04_numerics": vs04_numerics,
            "vs04_readiness": vs04_readiness,
            "vs04_pipeline": display_check_group(vs04_pipeline),
            **({"analysis_setup": analysis_setup} if analysis_setup is not None else {}),
            **({"analysis_setup_reconciliation": analysis_setup_reconciliation} if analysis_setup_reconciliation is not None else {}),
            **({"column_axial": {key: column_axial[key] for key in (
                "status", "expected_column_count", "completed_column_count",
                "native_force_row_count", "combination_plan",
            )}} if column_axial is not None else {}),
            **({"column_axial_coverage": {key: axial_ledger[key] for key in (
                "scope_complete", "expected_count", "evaluated_count", "not_proven_count", "dependency_blockers",
            )}} if axial_ledger is not None else {}),
            **({"column_pmm": {key: column_pmm[key] for key in (
                "member_id", "status", "expected_station_count", "evaluated_station_count",
            )}} if column_pmm is not None else {}),
            **({"column_pmm_coverage": {key: pmm_scope[key] for key in (
                "expected_member_combination_count", "numerically_complete_signed_pair_count",
                "independent_cut_census_proven", "dependency_blockers", "local_second_order_dependency_blockers",
            )}} if pmm_scope is not None else {}),
            **({"column_gates": column_gates} if column_gates is not None else {}),
            **({"beam_r10": {
                "target_member_id": beam_r10.get("target_member_id"),
                "beam_count": beam_r10.get("beam_count"),
                "calculated_beam_count": beam_r10.get("calculated_beam_count"),
                "engineer_selection_active": "beam_selection_policy" in beam_r10,
                "status": beam_r10.get("status"),
                "formal_compliance": beam_r10.get("formal_compliance"),
                "engineering_release": beam_r10.get("engineering_release"),
            }} if beam_r10 is not None else {}),
            **({"r10_live": {
                "member_id": r10_live.get("member_id"),
                "local_axis_angle_deg": r10_live.get("local_axis_angle_deg"),
                "joint_end_count": r10_live.get("joint_end_count"),
                "joint_status_counts": r10_live.get("joint_status_counts"),
                "enclosure_counts": r10_live.get("enclosure_counts"),
                "narrow_beam_joint_count": r10_live.get("narrow_beam_joint_count"),
                "scwb_joint_count": len(r10_live.get("scwb_joints") or ()),
                "column_transverse_status": (r10_live.get("column_transverse_and_shear") or {}).get("status"),
                **({"engineer_column_selection_status": r10_live["engineer_column_selection"].get("status")}
                   if r10_live.get("engineer_column_selection") is not None else {}),
                "formal_compliance": r10_live.get("formal_compliance"),
                "engineering_release": r10_live.get("engineering_release"),
            }} if r10_live is not None else {}),
            **({"r08_local_slenderness": {
                "member_id": r08_local_slenderness.get("member_id"),
                "scope": r08_local_slenderness.get("scope"),
                "evaluated_column_count": r08_local_slenderness.get("evaluated_column_count"),
                "status": r08_local_slenderness.get("status"),
                "candidate_span_mm": r08_local_slenderness.get("candidate_span_mm"),
                "span_basis": r08_local_slenderness.get("span_basis"),
                "max_reference_beta_sway_prevented": r08_local_slenderness.get("max_reference_beta_sway_prevented"),
                "formal_compliance": r08_local_slenderness.get("formal_compliance"),
                "engineering_release": r08_local_slenderness.get("engineering_release"),
            }} if r08_local_slenderness is not None else {}),
            **({"r14_closure": {
                "scope": r14_closure.get("scope"),
                "member_id": r14_closure.get("member_id"),
                "status": r14_closure.get("status"),
                "expected_column_count": r14_closure.get("expected_column_count"),
                "evaluated_column_count": r14_closure.get("evaluated_column_count"),
                "numerically_closed_count": r14_closure.get("numerically_closed_count"),
                "normative_fail_count": r14_closure.get("normative_fail_count"),
                "formal_compliance": r14_closure.get("formal_compliance"),
                "engineering_release": r14_closure.get("engineering_release"),
            }} if r14_closure is not None else {}),
            **({"story_drift": story_drift}
               if story_drift is not None else {}),
            **({"r08_second_order": r08_second_order}
               if r08_second_order is not None else {}),
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
        })
    except (ValueError, TypeError, KeyError) as exc:
        result = {"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}
        run.record("rejected", result, input_sha256=input_sha)
        handler.reply(422, {"run_id": run.run_id, "result": result})


def _column_axial_request(query: dict, output_root: Path) -> dict:
    from .engineering.design_assignments import ASSIGNED_DESIGN, COLUMN_AXIAL_ID, bind_assigned_combinations
    from .frame_force_capture import MAX_RESPONSE_COMBINATIONS

    base_runs = query.get("base_run_id", [])
    modes = query.get("combination_source", [])
    names = query.get("combination", [])
    offered = query.get("assignments", [])
    checks = query.get("check", [])
    pmm = checks == ["column-pmm"]
    members = query.get("member", [])
    reference_cases = query.get("reference_static_case", [])
    if (set(query) - {"case", "check", "base_run_id", "combination_source", "combination", "assignments", "member", "reference_static_case"}
            or checks not in (["column-axial"], ["column-pmm"])
            or (reference_cases and (not pmm or members != ["ALL"] or modes != [ASSIGNED_DESIGN]))
            or len(reference_cases) > MAX_RESPONSE_COMBINATIONS or len(set(reference_cases)) != len(reference_cases)
            or any(not n or n != n.strip() or len(n) > 160 for n in reference_cases)
            or len(members) != int(pmm)
            or any(not uid or uid != uid.strip() or len(uid) > 160 for uid in members)
            or len(base_runs) != 1 or _RUN_ID_PATTERN.fullmatch(base_runs[0]) is None
            or modes not in (["ETABS_STRENGTH"], ["SAVED_DEFAULTS"], [ASSIGNED_DESIGN])
            or bool(names) != (modes == ["SAVED_DEFAULTS"])
            or len(offered) != int(modes == [ASSIGNED_DESIGN])
            or any(len(value) > 32_000 for value in offered)
            or len(names) > MAX_RESPONSE_COMBINATIONS or len(set(names)) != len(names)
            or any(not name or name != name.strip() or len(name) > 160 for name in names)):
        raise ValueError("Select a live source run and an exact column strength combination set.")
    report = build_complete_report(output_root, base_runs[0])
    setup = report.get("analysis_setup") or {}
    filename = report["capture_metadata"].get("model_filename")
    if report["source_mode"] != "LIVE_ETABS" or not filename or not setup.get("definition_coverage_known"):
        raise ValueError("The selected source run has no verified ETABS combination catalog.")
    assignment_check = COLUMN_AXIAL_ID
    if pmm:
        from .engineering.column_pmm import COLUMN_PMM_ID

        assignment_check = COLUMN_PMM_ID
        if members[0] != "ALL":
            roster = next((check["items"] for check in report["checks"] if check["check_id"] == "column_rect_min"), ())
            if sum(row["element_id"] == members[0] and row["status"] != "NOT_APPLICABLE" for row in roster) != 1:
                raise ValueError("Select a column by its exact ETABS Unique ID from the verified source run.")
    assignment = None
    if offered:
        assignment = bind_assigned_combinations(
            report["design_assignments"], check=assignment_check, offered=json.loads(offered[0]),
            catalog=setup["defined_combination_names"],
        )
        names = sorted({name for group in assignment["groups"].values() for name in group})
        if not 0 < len(names) <= MAX_RESPONSE_COMBINATIONS:
            raise ValueError("Assign a nonempty column strength combination set within the capture limit.")
    if not set(names).issubset(setup["defined_combination_names"]):
        raise ValueError("Saved combinations missing from the selected ETABS catalog.")
    return {
        "base_run_id": base_runs[0], "model_filename": filename, "combination_source": modes[0],
        "combinations": sorted(names), "combination_graph_sha256": setup["typed_graph_source_sha256"],
        "base_input_sha256": report["source_provenance"]["input_sha256"],
        **({"design_assignment": assignment} if assignment is not None else {}),
        **({"reference_static_cases": sorted(reference_cases)} if reference_cases else {}),
        **({"pmm_member": members[0]} if pmm else {}),
    }


def _runs(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    output = []
    for directory in sorted(root.glob("RUN-*"), reverse=True)[:60]:
        if not directory.is_dir() or not _RUN_ID_PATTERN.fullmatch(directory.name):
            continue
        steps: list[dict[str, Any]] = []
        try:
            files = receipt_paths(directory)
        except (OSError, ValueError):
            continue
        for file in files:
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            steps.append({"stage": data.get("stage"), "status": (data.get("payload") or {}).get("status"), "receipt_sha256": data.get("receipt_sha256")})
        output.append({"run_id": directory.name, "steps": steps})
    return output


from .engineering.pipeline import calculate_modal as _calculate_modal  # noqa: E402


def make_handler(output_root: Path, *, live_capture=None, etabs_pid: int | None = None, allow_private_wall_analysis=False):
    """Injectable capture callback makes endpoint testable without Windows COM."""
    # Each serving process uses the UI assets it started with and its own engine.
    static = resources.files("tbdy_next").joinpath("static")
    scripts = {name: static.joinpath(name).read_bytes() for name in (
        "quick.js", "column.js", "engine-console.js", "workspace.js", "workspace-source.js",
    )}
    version_label = f'<span class="app-version"> · v{escape(__version__)}</span>'.encode("utf-8")
    pages = {
        name: static.joinpath(name).read_bytes().replace(b'<span class="app-version" hidden></span>', version_label)
        for name in ("workspace.html", "index.html")
    }
    if allow_private_wall_analysis and etabs_pid:
        pages["workspace.html"] = pages["workspace.html"].replace(
            b'id="deskPrivateWallOption" hidden', b'id="deskPrivateWallOption"')

    class Handler(BaseHTTPRequestHandler):
        server_version = "TBDYNext/VS04-Partial"

        def log_message(self, format: str, *args: object) -> None:
            # No request bodies, file contents, or user data in access logs.
            return

        def reply(self, code: int, data: Mapping[str, Any]) -> None:
            payload = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            url = urlsplit(self.path)
            if url.path in ("/api/column-history", "/api/column-bank", "/api/export-column-bank", "/report/column-bank", "/api/export-spectral-design"):
                self.column_get(url)
            elif url.path in ("/", "/index.html", "/workspace", "/source"):
                page = "index.html" if url.path == "/source" else "workspace.html"
                contents = pages[page]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(contents)))
                self.end_headers()
                self.wfile.write(contents)
            elif url.path == "/api/health":
                self.reply(200, {"status": "PARTIAL_UNIFIED_VS04_SCREENING", "implemented_slices": ["MODAL_MASS_RATIO", "MATERIAL_FCK_25", "A1_X_Y_SOURCE_CLASSIFICATION"], "source_only_slices": ["VS04_ANALYSIS_SOURCE_SCHEMA", "VS04_ANALYSIS_NUMERIC_SOURCE", "VS04_E_NORMATIVE_READINESS"], "live_web_f_to_j_integrated": True, "single_primary_action": "/api/live-vs04", "on_demand_force_checks": ["column-axial", "column-pmm"], "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"})
            elif url.path == "/api/pipeline":
                from .engineering.pipeline import dag_coverage, stage_registry
                self.reply(200, {"stages": stage_registry(), "dag_coverage": dag_coverage(),
                                 "engineering_release": "NOT_READY"})
            elif url.path == "/api/runs":
                self.reply(200, {"runs": _runs(output_root)})
            elif url.path == "/api/check-registry":
                self.reply(200, {"checks": check_registry(), "implemented_check_count": len(check_registry())})
            elif url.path == "/api/quick-history":
                query = parse_qs(url.query)
                if query not in ({}, {"view": ["summary"]}):
                    self.reply(400, {"error": "QUICK_HISTORY_VIEW_INVALID"})
                    return
                self.reply(200, {"runs": quick_history(output_root, summary=bool(query)),
                                 "engineering_release": "NOT_READY"})
            elif url.path == "/api/modal-history":
                self.reply(200, {"runs": modal_history(output_root), "engineering_release": "NOT_READY"})
            elif url.path in ("/api/export-checks", "/report/print",
                                "/api/vs06-drift-scenario"):
                query = parse_qs(url.query)
                ids = query.get("run_id", [])
                if len(ids) != 1 or _RUN_ID_PATTERN.fullmatch(ids[0]) is None:
                    self.reply(400, {"error": "EXACT_RUN_ID_REQUIRED"})
                    return
                try:
                    report = build_complete_report(output_root, ids[0])
                    # C2: optional read-only numerical scenario over a sealed
                    # archived run. Does not start ETABS or edit a receipt.
                    from .vs06_drift_scenario import ALLOWED, evaluate_drift_scenario
                    offered = {k: v for k, v in query.items() if k != "run_id"}
                    if set(offered) - ALLOWED or any(len(v) != 1 for v in offered.values()):
                        self.reply(400, {"error": "VS06_SCENARIO_QUERY_INVALID"})
                        return
                    if url.path == "/api/vs06-drift-scenario" or offered:
                        params = {k: v[0] for k, v in offered.items()}
                        scenario = evaluate_drift_scenario(report, params)
                        if url.path == "/api/vs06-drift-scenario":
                            self.reply(200, scenario)
                            return
                        report["vs06_drift_scenario"] = scenario
                    if url.path == "/api/export-checks":
                        data = (json.dumps(report, ensure_ascii=False, indent=2,
                                           sort_keys=True) + "\n").encode("utf-8")
                        mime = "application/json; charset=utf-8"
                        disposition = f'attachment; filename="TBDY_NEXT_{ids[0]}_all_checks.json"'
                    else:
                        data = build_printable_html(report).encode("utf-8")
                        mime = "text/html; charset=utf-8"
                        disposition = f'inline; filename="TBDY_NEXT_{ids[0]}_report.html"'
                except (ReportUnavailable, OSError, UnicodeError, TypeError, ValueError, KeyError) as exc:
                    # A rejected scenario is a bad request, not a fabricated
                    # missing archive or an authorized normative PASS.
                    from .vs06_drift_scenario import DriftScenarioError
                    if isinstance(exc, DriftScenarioError):
                        self.reply(422, {"error": str(exc), "formal_compliance": "NOT_PROVEN"})
                        return
                    self.reply(404, {"error": "VERIFIED_FIVE_CHECK_REPORT_NOT_FOUND"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Disposition", disposition)
                self.send_header("X-Frame-Options", "DENY")
                if url.path == "/report/print":
                    self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif url.path == "/api/modal-table":
                ids = parse_qs(url.query).get("run_id", [])
                if len(ids) != 1 or _RUN_ID_PATTERN.fullmatch(ids[0]) is None:
                    self.reply(400, {"error": "EXACT_RUN_ID_REQUIRED"})
                    return
                table = modal_source_table(output_root, ids[0])
                if table is None:
                    self.reply(404, {"error": "VERIFIED_MODAL_TABLE_NOT_FOUND"})
                    return
                self.reply(200, {"table": table})
            elif url.path in ("/quick.js", "/column.js", "/engine-console.js", "/workspace.js", "/workspace-source.js"):
                source = scripts[url.path[1:]]
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(source)))
                self.end_headers()
                self.wfile.write(source)
            elif url.path in ("/api/column-127-gates", "/api/column-127-workspace", "/report/column-127"):
                try:
                    from .engineering.live_column import load_and_evaluate_127_from_receipts
                    from .reporting import build_column_127_gate_html
                    receipt_dir = output_root / "column_127_receipts"
                    bundle = load_and_evaluate_127_from_receipts(receipt_dir if receipt_dir.is_dir() else None)
                    if url.path == "/api/column-127-gates":
                        self.reply(200, bundle["p0_gate_report"])
                        return
                    if url.path == "/api/column-127-workspace":
                        from .engineering.design_assignments import design_assignments
                        setup = bundle["p0_gate_report"]["p0c_model_analysis_setup_audit"]
                        self.reply(200, {**bundle, "source_mode": "ARCHIVED_COLUMN_RECEIPT",
                                         "design_assignments": design_assignments(setup)})
                        return
                    html_bytes = build_column_127_gate_html(bundle).encode("utf-8")
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    self.reply(404, {"error": f"COLUMN_127_RECEIPTS_UNAVAILABLE:{exc}"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.end_headers()
                self.wfile.write(html_bytes)
            elif url.path == "/history.js":
                source = resources.files("tbdy_next").joinpath("static/history.js").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(source)))
                self.end_headers()
                self.wfile.write(source)
            else:
                self.reply(404, {"error": "NOT_FOUND"})

        def column_get(self, url) -> None:
            """Read only, explicitly selected archive; never join the live run."""
            import sqlite3
            from .column_engine.store import column_bank_history, read_column_bank, verified_database
            from .reporting import build_column_bank_html
            if url.path == "/api/column-history":
                self.reply(200, {"runs": column_bank_history(output_root), "engineering_release": "NOT_READY"})
                return
            query = parse_qs(url.query, keep_blank_values=True)
            if url.path == "/api/export-spectral-design":
                if (set(query) != {"run_id"} or len(query["run_id"]) != 1
                        or not _RUN_ID_PATTERN.fullmatch(query["run_id"][0])):
                    self.reply(400, {"error": "FULL_SPECTRAL_EXPORT_REQUIRES_RUN_ONLY_NO_FILTERS"})
                    return
                from tempfile import SpooledTemporaryFile
                from .column_engine.demand_view import verified_spectral_design
                from .column_engine.spectral_projection import write_spectral_forensic
                with SpooledTemporaryFile(max_size=8*1024*1024) as stream:
                    try:
                        run_id = query["run_id"][0]
                        _, result = verified_spectral_design(output_root, run_id)
                        write_spectral_forensic(result, stream)
                        verified_database(output_root, run_id)
                    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
                        self.reply(404, {"error": "VERIFIED_COLUMN_BANK_NOT_FOUND"})
                        return
                    length = stream.tell(); stream.seek(0)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Content-Disposition", f'attachment; filename="YENI_{run_id}_VS26_full_forensic.zip"')
                    self.send_header("Content-Length", str(length)); self.end_headers()
                    while chunk := stream.read(256*1024): self.wfile.write(chunk)
                return
            allowed = {"run_id", "member", "case", "offset", "view", "column_cage", "beam_diameter"} if url.path == "/api/column-bank" else {"run_id", "format", "view", "member", "case", "offset", "column_cage"} if url.path == "/api/export-column-bank" else {"run_id", "view", "member", "case", "offset", "column_cage"}
            if (set(query) - allowed or any(len(v) != 1 for v in query.values())
                    or not _RUN_ID_PATTERN.fullmatch(query.get("run_id", [""])[0])):
                self.reply(400, {"error": "COLUMN_QUERY_INVALID"})
                return
            run_id = query["run_id"][0]
            fmt = query.get("format", ["json"])[0]
            offset = query.get("offset", ["0"])[0]
            view = query.get("view", ["native"])[0]
            column_label=query.get('column_cage',[None])[0]
            beam_diameter=query.get('beam_diameter',[None])[0]
            bounded_spectral = view in ("spectral-envelopes", "spectral-design", "spectral-candidates")
            if (fmt not in ("json", "sqlite") or not offset.isdecimal() or len(offset) > 9
                    or view not in ("native", "static", "design", "critical", "reinforcement", "stiffness", "eccentricity", "cages", "pmm", "transverse", "shear", "joints", "joint-ties", "end-forces", "kinematics", "stiffness-scenarios", "length-sensitivity", "overview", "pmm-quality", "scwb", "beam-cages", "scwb-scenarios", "spectral-envelopes", "spectral-design", "spectral-candidates")
                    or url.path != "/api/column-bank" and bool(set(query) & {"view", "member", "case", "offset", "column_cage"}) and not bounded_spectral
                    or bounded_spectral and fmt != "json"
                    or column_label is not None and view not in ('scwb-scenarios','spectral-design','spectral-candidates')
                    or beam_diameter is not None and view!='scwb-scenarios'
                    or column_label is not None and column_label not in ('16Φ24','16Φ28','16Φ32')
                    or beam_diameter is not None and beam_diameter not in ('16','20','24')
                    or (view in ("reinforcement", "stiffness", "cages", "transverse", "joints", "joint-ties", "stiffness-scenarios", "beam-cages") and "case" in query)):
                self.reply(400, {"error": "COLUMN_QUERY_INVALID"})
                return
            try:
                if url.path == "/api/export-column-bank" and fmt == "sqlite":
                    database, _ = verified_database(output_root, run_id)
                    data, mime, extension = database.read_bytes(), "application/vnd.sqlite3", "sqlite"
                else:
                    report = read_column_bank(output_root, run_id,
                        member_id=query.get("member", [None])[0], output_case=query.get("case", [None])[0],
                        offset=int(offset), view="pmm-quality" if url.path == "/report/column-bank" and not bounded_spectral else view,
                        column_label=column_label,beam_diameter=int(beam_diameter) if beam_diameter is not None else None,
                        full=url.path == "/api/export-column-bank" and not bounded_spectral)
                    if url.path == "/api/column-bank":
                        self.reply(200, report)
                        return
                    if url.path == "/report/column-bank":
                        if view == "spectral-envelopes":
                            from .spectral_report import build_spectral_html
                            data = build_spectral_html(report).encode("utf-8")
                        elif view in ("spectral-design", "spectral-candidates"):
                            from .spectral_design_report import build_spectral_design_html
                            data = build_spectral_design_html(report).encode("utf-8")
                        else:
                            data = build_column_bank_html(report).encode("utf-8")
                        mime, extension = "text/html; charset=utf-8", "html"
                    else:
                        data = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
                        mime, extension = "application/json; charset=utf-8", "json"
            except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
                self.reply(404, {"error": "VERIFIED_COLUMN_BANK_NOT_FOUND"})
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            disposition = "inline" if extension == "html" else "attachment"
            suffix = f"spectral_page_{offset}" if view == "spectral-envelopes" else f"{view}_page_{offset}" if bounded_spectral else "columns"
            self.send_header("Content-Disposition", f'{disposition}; filename="YENI_{run_id}_{suffix}.{extension}"')
            if extension == "html":
                self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            url = urlsplit(self.path)
            if url.path == "/api/vs06-b1-preview":
                # Read-only mathematical preview of two independently SHA-sealed
                # ETABS captures. No COM call, no receipt mutation and no
                # uploaded source echoed to an external service.
                origin = self.headers.get("Origin")
                host = self.headers.get("Host", "")
                if (self.headers.get("Sec-Fetch-Site") == "cross-site"
                        or (origin and origin != "http://" + host)):
                    # Windows (WinError 10053): closing an HTTP/1.0 socket
                    # while the client still has POST bytes in flight can
                    # generate a TCP reset before the 403 response is read.
                    # Drain ONLY a declared, bounded request body. This is
                    # byte disposal, never JSON parsing or ETABS processing.
                    # An invalid, transfer-encoded, or oversized body is
                    # rejected without an unbounded drain.
                    try:
                        rejected_length = int(self.headers.get("Content-Length", "-1"))
                    except ValueError:
                        rejected_length = -1
                    if (0 <= rejected_length <= MAX_UPLOAD_BYTES
                            and not self.headers.get("Transfer-Encoding")):
                        previous_timeout = self.connection.gettimeout()
                        try:
                            self.connection.settimeout(2.0)
                            remaining = rejected_length
                            while remaining:
                                chunk = self.rfile.read(min(65536, remaining))
                                if not chunk:
                                    break
                                remaining -= len(chunk)
                        except OSError:
                            # Still deny the request; never hand its bytes to
                            # JSON parsing or evaluate any engineering source.
                            pass
                        finally:
                            self.connection.settimeout(previous_timeout)
                    self.reply(403, {"error": "CROSS_ORIGIN_DENIED"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", ""))
                except ValueError:
                    length = -1
                if length < 1 or length > MAX_UPLOAD_BYTES or self.headers.get("Transfer-Encoding"):
                    self.reply(413, {"error": "VS06_B1_PREVIEW_SIZE_INVALID",
                                     "max_bytes": MAX_UPLOAD_BYTES})
                    return
                try:
                    raw = self.rfile.read(length)
                    data = json.loads(raw.decode("utf-8"))
                    if not isinstance(data, dict) or set(data) != {"geometry", "wall_loads", "options"}:
                        raise ValueError("VS06_B1_PREVIEW_PAYLOAD_SHAPE")
                    options = data["options"]
                    if not isinstance(options, dict) or set(options) - {
                        "wall_type", "unit_weight_kN_m3",
                        "unit_weight_min_kN_m3", "unit_weight_max_kN_m3",
                        "opening_fraction", "low_load_ratio_cutoff",
                        "shear_modulus_mpa", "R_base"}:
                        raise ValueError("VS06_B1_PREVIEW_OPTIONS_INVALID")
                    from .b1_source_bridge import evaluate_b1_sources
                    from .b1_source_bridge import render_b1_html
                    result = evaluate_b1_sources(data["geometry"], data["wall_loads"], **options)
                    self.reply(200, {"result": result, "html": render_b1_html(result)})
                except (UnicodeError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
                    self.reply(422, {"error": str(exc),
                                     "formal_compliance": "NOT_PROVEN"})
                return
            if url.path == "/api/apply-rebar-selection":
                origin = self.headers.get("Origin")
                host = self.headers.get("Host", "")
                if (self.headers.get("Sec-Fetch-Site") == "cross-site"
                        or (origin and origin not in ("http://" + host,))):
                    self.reply(403, {"status": "REJECTED", "reason": "CROSS_ORIGIN_DENIED"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0") or "0")
                except ValueError:
                    self.reply(400, {"status": "REJECTED", "reason": "INVALID_CONTENT_LENGTH"})
                    return
                if not 0 <= length <= 1_048_576 or self.headers.get("Transfer-Encoding"):
                    self.reply(400, {"status": "REJECTED", "reason": "INVALID_BODY_LENGTH"})
                    return
                try:
                    body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
                    if not isinstance(body, dict):
                        raise ValueError("JSON_OBJECT_REQUIRED")
                    q = parse_qs(url.query)
                    base_run_id = body.get("base_run_id") or (q.get("base_run_id") or [""])[0]
                    if not isinstance(base_run_id, str) or _RUN_ID_PATTERN.fullmatch(base_run_id) is None:
                        raise ValueError("VALID_BASE_RUN_ID_REQUIRED")
                    base_report = build_complete_report(output_root, base_run_id)
                    if base_report["source_mode"] != "LIVE_ETABS":
                        raise ValueError("LIVE_ETABS_BASE_RUN_REQUIRED")
                    source_directory = output_root / base_run_id
                    source_path = source_directory / "input.source"
                    if (source_path.is_symlink() or not source_path.is_file()
                            or not 0 < source_path.stat().st_size <= _MAX_SOURCE_BYTES):
                        raise ValueError("SOURCE_PATH_MISSING_OR_UNSAFE")
                    source_raw = source_path.read_bytes()
                    if sha256(source_raw).hexdigest() != base_report["source_provenance"]["input_sha256"]:
                        raise ValueError("SCENARIO_BASE_SOURCE_HASH_MISMATCH")
                    selection_overrides = {}
                    for key, kind in (("beam_selection", "beam"), ("column_selection", "column")):
                        if key in body:
                            selection_overrides[key] = _parse_rebar_selection_spec(body[key], kind)
                        elif key in q:
                            if len(q[key]) != 1:
                                raise ValueError(f"Multiple {key} parameters are not allowed.")
                            selection_overrides[key] = _parse_rebar_selection_spec(q[key][0], kind)
                    scenario_request = body.get("design_scenario")
                    if scenario_request is not None:
                        if not isinstance(scenario_request, dict):
                            raise ValueError("SCENARIO_REQUEST_OBJECT_REQUIRED")
                        if selection_overrides:
                            raise ValueError("SCENARIO_AND_SELECTION_FLAGS_ARE_EXCLUSIVE")
                        selection_overrides = None
                    case = base_report["modal_case"]
                    pier_forces = body.get("pier_forces")
                    solve_copy = body.get("solve_wall_copy") is True
                    if solve_copy and not (allow_private_wall_analysis and etabs_pid and body.get("read_missing_wall_forces") is True):
                        raise ValueError("PRIVATE_WALL_ANALYSIS_REQUIRES_ENABLED_SERVER_AND_EXPLICIT_WALL_REQUEST")
                    if body.get("read_missing_wall_forces") is True:
                        if body.get("whole_building") is not True or pier_forces is not None or scenario_request is not None:
                            raise ValueError("WALL_BATCH_REQUIRES_ONE_WHOLE_BUILDING_SOURCE")
                        pier_forces = read_missing_wall_forces(json.loads(source_raw), source_raw, source_directory, etabs_pid,
                                                              private_replay_root=output_root if solve_copy else None)
                except ReportUnavailable as exc:
                    self.reply(404, {"status": "REJECTED", "reason": str(exc)})
                    return
                except (OSError, ValueError, TypeError, RuntimeError, KeyError) as exc:
                    self.reply(422, {"status": "REJECTED", "reason": str(exc)})
                    return
                _execute_and_reply_live_payload(
                    self, output_root, base_report["source_snapshot"], case, suite=True,
                    source_raw=source_raw, source_directory=source_directory,
                    selection_overrides=selection_overrides,
                    scenario_request=scenario_request,
                    whole_building=body.get("whole_building", False),
                    pier_forces=pier_forces,
                    wall_hinge_aggregate_storeys=body.get("wall_hinge_aggregate_storeys"),
                )
                return
            if url.path in ("/api/live-modal", "/api/live-suite", "/api/live-vs04", "/api/etabs-session"):
                # Browser can POST to loopback from a foreign page; reject any
                # declared cross-site origin before touching the ETABS session.
                origin = self.headers.get("Origin")
                host = self.headers.get("Host", "")
                if (self.headers.get("Sec-Fetch-Site") == "cross-site"
                    or (origin and origin not in ("http://" + host,))):
                    self.reply(403, {"status": "REJECTED", "reason": "CROSS_ORIGIN_DENIED"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = -1
                if length != 0 or self.headers.get("Transfer-Encoding"):
                    self.reply(400, {"status": "REJECTED", "reason": "LIVE_REQUEST_MUST_HAVE_NO_BODY"})
                    return
                query = parse_qs(url.query)
                session_only = url.path == "/api/etabs-session"
                cases = query.get("case", [])
                case = cases[0] if len(cases) == 1 else ""
                if session_only and query:
                    self.reply(400, {"status": "REJECTED", "reason": "ETABS_SESSION_TAKES_NO_PARAMETERS"})
                    return
                if not session_only and (not case or case != case.strip() or len(case) > 120):
                    self.reply(400, {"status": "REJECTED", "reason": "EXACT_MODAL_CASE_REQUIRED"})
                    return
                capture_options = {}
                rebar_selection_opts: dict[str, Any] = {}
                whole_building = False
                hinge_storeys = None
                if not session_only and set(query) != {"case"}:
                    try:
                        if url.path != "/api/live-vs04":
                            raise ValueError("Use the combined capture for check-specific options.")
                        if "whole_building" in query:
                            if query["whole_building"] not in (["true"], ["false"]):
                                raise ValueError("BUILDING_SCOPE_OPTION_INVALID")
                            whole_building = query["whole_building"] == ["true"]
                        hinge_storeys = query.get("wall_hinge_aggregate_storey")
                        if hinge_storeys is not None and not whole_building:
                            raise ValueError("BUILDING_SCOPE_OPTION_INVALID")
                        for sel_key, sel_kind in (("beam_selection", "beam"), ("column_selection", "column")):
                            if sel_key in query:
                                vals = query[sel_key]
                                if len(vals) != 1:
                                    raise ValueError(f"Multiple {sel_key} parameters are not allowed.")
                                rebar_selection_opts[sel_key] = _parse_rebar_selection_spec(vals[0], sel_kind)
                        axial_query = {
                            k: v for k, v in query.items()
                            if k not in ("beam_selection", "column_selection", "whole_building", "wall_hinge_aggregate_storey")
                        }
                        if set(axial_query) - {"case"}:
                            capture_options["column_axial_request"] = _column_axial_request(axial_query, output_root)
                        if whole_building and (capture_options.get("column_axial_request") or {}).get("pmm_member") != "ALL":
                            raise ValueError("BUILDING_DESIGN_REQUIRES_ALL_COLUMNS")
                    except (ReportUnavailable, ValueError, TypeError) as exc:
                        self.reply(422, {"status": "CAPTURE_REJECTED", "reason": str(exc)})
                        return
                # Import COM only for explicit requests. The worker owns its COM lifecycle.
                if not _LIVE_CAPTURE_LOCK.acquire(blocking=False):
                    self.reply(409, {"status": "CAPTURE_BUSY", "reason": "ETABS_CAPTURE_ALREADY_RUNNING"})
                    return
                try:
                    if session_only:
                        from .live_etabs import select_etabs_capture_units
                        session = select_etabs_capture_units(etabs_pid)["after"]
                        self.reply(200, {
                            "etabs_session": session, "required_units_code": CAPTURE_UNIT_CODE,
                            "required_units_label": CAPTURE_UNIT_LABEL,
                        })
                        return
                    if live_capture is not None:
                        payload = live_capture(case, **capture_options)
                    else:
                        if url.path in ("/api/live-suite", "/api/live-vs04"):
                            from .live_etabs import read_quick_suite_from_running_etabs
                            payload = read_quick_suite_from_running_etabs(
                                case, with_vs04=(url.path == "/api/live-vs04"), process_id=etabs_pid,
                                **capture_options)
                        else:
                            from .live_etabs import read_modal_from_running_etabs
                            payload = read_modal_from_running_etabs(case, process_id=etabs_pid)
                except EtabsConnectionError as exc:
                    self.reply(503, {
                        "status": "CAPTURE_REJECTED", "code": "ETABS_CONNECTION_UNAVAILABLE",
                        "reason": str(exc), "engineering_release": "NOT_READY",
                    })
                    return
                except EtabsUnitsError as exc:
                    self.reply(503, {
                        "status": "CAPTURE_REJECTED", "reason": f"{type(exc).__name__}: {exc}",
                        "etabs_session": exc.session, "required_units_code": CAPTURE_UNIT_CODE,
                        "required_units_label": CAPTURE_UNIT_LABEL, "engineering_release": "NOT_READY",
                    })
                    return
                except Exception as exc:
                    self.reply(503, {
                        "status": "CAPTURE_REJECTED", "reason": f"{type(exc).__name__}: {exc}",
                        "engineering_release": "NOT_READY",
                    })
                    return
                finally:
                    _LIVE_CAPTURE_LOCK.release()
                # Actual OAPI source is now represented by this immutable local
                # input; it is never sent to GitHub or to another host.
                if not isinstance(payload, dict) or payload.get("source_mode") != "LIVE_ETABS":
                    self.reply(422, {"status": "CAPTURE_REJECTED", "reason": "LIVE_SOURCE_MODE_REQUIRED"})
                    return
                if capture_options and ((payload.get("column_axial") or {}).get("request")
                                        != capture_options["column_axial_request"]):
                    self.reply(422, {"status": "CAPTURE_REJECTED", "reason": "COLUMN_AXIAL_SOURCE_REQUEST_UNBOUND"})
                    return
                if url.path == "/api/live-vs04" and "analysis_sources" not in payload:
                    self.reply(422, {"status": "CAPTURE_REJECTED", "reason": "VS04_CAPTURE_MISSING"})
                    return
                if url.path == "/api/live-vs04" and (
                        payload["analysis_sources"].get("pipeline_stage_required") is True
                        and not all(isinstance(payload.get(k), dict) for k in
                                    ("vs04_basis_probe", "vs04_diaphragm_probe"))):
                    self.reply(422, {"status": "CAPTURE_REJECTED",
                                     "reason": "VS04_REQUIRED_SAME_SESSION_SOURCES_MISSING"})
                    return
                source_raw = None
                pier_forces = None
                if whole_building and etabs_pid is not None and live_capture is None:
                    source_raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    try:
                        pier_forces = read_missing_wall_forces(payload, source_raw, output_root, etabs_pid)
                    except (OSError, ValueError, TypeError, RuntimeError, KeyError) as exc:
                        self.reply(422, {"status": "BLOCKED_ENGINEERING_SOURCE", "reason": str(exc),
                                         "engineering_release": "NOT_READY"})
                        return
                _execute_and_reply_live_payload(
                    self, output_root, payload, case,
                    suite=url.path in ("/api/live-suite", "/api/live-vs04"),
                    source_raw=source_raw, pier_forces=pier_forces,
                    selection_overrides=rebar_selection_opts or None,
                    whole_building=whole_building, wall_hinge_aggregate_storeys=hinge_storeys,
                )
                return
            if url.path not in ("/api/discovery", "/api/modal", "/api/modal-schema"):
                self.reply(404, {"error": "NOT_FOUND"})
                return
            length_value = self.headers.get("Content-Length")
            try:
                length = int(length_value or "")
            except ValueError:
                self.reply(411, {"error": "CONTENT_LENGTH_REQUIRED"})
                return
            if length <= 0 or length > MAX_UPLOAD_BYTES:
                self.reply(413, {"error": "UPLOAD_SIZE_INVALID", "limit_bytes": MAX_UPLOAD_BYTES})
                return
            raw = self.rfile.read(length)
            input_sha = sha256(raw).hexdigest()
            run = ReceiptRun(output_root)
            # Preserve input on disk under a non-JSON extension so the old CLI
            # receipt discovery keeps its previous semantics.
            run.archive_input(raw, expected_sha256=input_sha)
            try:
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise SourceError("The source JSON must be an object")
                if url.path == "/api/discovery":
                    result = review_preflight(payload)
                    run.record("discovery", result, input_sha256=input_sha)
                elif url.path == "/api/modal-schema":
                    result = review_modal_schema(payload)
                    run.record("schema-discovery", result, input_sha256=input_sha)
                else:
                    query = parse_qs(url.query)
                    case = query.get("case", [""])[0].strip()
                    if not case:
                        raise SourceError("A modal case name is required")
                    result = _calculate_modal(payload, case=case, run=run, input_sha=input_sha)
                self.reply(200, {"run_id": run.run_id, "result": result, "engineering_release": "NOT_READY"})
            except (ValueError, UnicodeError, KeyError, TypeError) as exc:
                result = {"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}
                run.record("rejected", result, input_sha256=input_sha)
                self.reply(422, {"run_id": run.run_id, "result": result})

    return Handler


def serve(*, host: str = "127.0.0.1", port: int = 8765, output_root: Path = Path(".receipts"),
          etabs_pid: int | None = None, allow_private_wall_analysis=False) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("VS01 web UI accepts localhost only; use a trusted port forward in Codespaces")
    with ThreadingHTTPServer((host, port), make_handler(
            Path(output_root), etabs_pid=etabs_pid, allow_private_wall_analysis=allow_private_wall_analysis)) as server:
        target = f"PID {etabs_pid}" if etabs_pid is not None else "active instance"
        print(f"TBDY Next Engine VS01: http://{host}:{server.server_port} | receipts: {output_root} "
              f"| ETABS: {target}, connection sets {CAPTURE_UNIT_LABEL}",
              flush=True)
        server.serve_forever()
