"""Local VS01 web UI: explicit, user-triggered Windows ETABS connection.

A live POST captures one modal table on a COM-initialized worker, then uses the
same owned schema, modal and receipt functions as the CLI. Never saves or runs
ETABS analysis; localhost only. Existing offline import remains optional.
"""
from __future__ import annotations

from hashlib import sha256
import ntpath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from .modal import evaluate_modal_mass
from .history import modal_history, modal_source_table, quick_history
from .quick_checks import check_registry, evaluate_geometry_capture
from .next_checks import evaluate_next_capture
from .analysis_sources import review_analysis_sources
from .analysis_numerics import evaluate_analysis_numerics
from .normative_basis import review_normative_readiness
from .live_source_pipeline import evaluate_single_run_source_pipeline
from .reporting import ReportUnavailable, build_complete_report, build_printable_html
from .receipts import ReceiptRun
from .schema import review_modal_schema
from .source import SourceError, parse_modal_capture, review_preflight

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
_RUN_ID_PATTERN = re.compile(r"RUN-[a-f0-9]{32}\Z")


def _runs(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    output = []
    for directory in sorted(root.glob("RUN-*"), reverse=True)[:60]:
        if not directory.is_dir() or not _RUN_ID_PATTERN.fullmatch(directory.name):
            continue
        steps: list[dict[str, Any]] = []
        for file in sorted(directory.glob("[0-9][0-9]-*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            steps.append({"stage": data.get("stage"), "status": (data.get("payload") or {}).get("status"), "receipt_sha256": data.get("receipt_sha256")})
        output.append({"run_id": directory.name, "steps": steps})
    return output


def _calculate_modal(payload: Mapping[str, Any], *, case: str, run: ReceiptRun, input_sha: str) -> dict[str, Any]:
    """One authoritative postprocess path for both live and imported data."""
    schema_review = review_modal_schema(payload)
    run.record("schema-discovery", schema_review, input_sha256=input_sha)
    table = parse_modal_capture(payload, case=case)
    run.record("schema", {
        "stage": "MODAL_ROW_VALIDATION", "status": "SCHEMA_VALID", "target_case": case,
        "case_row_count": len(table.rows), "raw_row_count": table.all_rows_count,
        "source_mode": table.origin, "engineering_release": "NOT_READY",
    }, input_sha256=input_sha)
    result = evaluate_modal_mass(table).as_dict()
    run.record("modal", result, input_sha256=input_sha)
    return result


def make_handler(output_root: Path, *, live_capture=None):
    """Injectable capture callback makes endpoint testable without Windows COM."""
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
            if url.path in ("/", "/index.html"):
                contents = resources.files("tbdy_next").joinpath("static/index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(contents)))
                self.end_headers()
                self.wfile.write(contents)
            elif url.path == "/api/health":
                self.reply(200, {"status": "PARTIAL_UNIFIED_VS04_SCREENING", "implemented_slices": ["MODAL_MASS_RATIO", "MATERIAL_FCK_25", "A1_X_Y_SOURCE_CLASSIFICATION"], "source_only_slices": ["VS04_ANALYSIS_SOURCE_SCHEMA", "VS04_ANALYSIS_NUMERIC_SOURCE", "VS04_E_NORMATIVE_READINESS"], "live_web_f_to_j_integrated": True, "single_primary_action": "/api/live-vs04", "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"})
            elif url.path == "/api/runs":
                self.reply(200, {"runs": _runs(output_root)})
            elif url.path == "/api/check-registry":
                self.reply(200, {"checks": check_registry(), "implemented_check_count": len(check_registry())})
            elif url.path == "/api/quick-history":
                self.reply(200, {"runs": quick_history(output_root), "engineering_release": "NOT_READY"})
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
            elif url.path == "/quick.js":
                source = resources.files("tbdy_next").joinpath("static/quick.js").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(source)))
                self.end_headers()
                self.wfile.write(source)
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
                    from tools.verify_vs06_b1_sources import render_b1_html
                    result = evaluate_b1_sources(data["geometry"], data["wall_loads"], **options)
                    self.reply(200, {"result": result, "html": render_b1_html(result)})
                except (UnicodeError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
                    self.reply(422, {"error": str(exc),
                                     "formal_compliance": "NOT_PROVEN"})
                return
            if url.path in ("/api/live-modal", "/api/live-suite", "/api/live-vs04"):
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
                cases = query.get("case", [])
                case = cases[0] if len(cases) == 1 else ""
                if not case or case != case.strip() or len(case) > 120:
                    self.reply(400, {"status": "REJECTED", "reason": "EXACT_MODAL_CASE_REQUIRED"})
                    return
                # Import Windows/COM lazily and only after the user clicks the
                # live button. The request thread owns its COM lifecycle.
                try:
                    if live_capture is not None:
                        payload = live_capture(case)
                    else:
                        if url.path in ("/api/live-suite", "/api/live-vs04"):
                            from .live_etabs import read_quick_suite_from_running_etabs
                            payload = read_quick_suite_from_running_etabs(
                                case, with_vs04=(url.path == "/api/live-vs04"))
                        else:
                            from .live_etabs import read_modal_from_running_etabs
                            payload = read_modal_from_running_etabs(case)
                except Exception as exc:
                    self.reply(503, {
                        "status": "CAPTURE_REJECTED", "reason": f"{type(exc).__name__}: {exc}",
                        "engineering_release": "NOT_READY",
                    })
                    return
                # Actual OAPI source is now represented by this immutable local
                # input; it is never sent to GitHub or to another host.
                if not isinstance(payload, dict) or payload.get("source_mode") != "LIVE_ETABS":
                    self.reply(422, {"status": "CAPTURE_REJECTED", "reason": "LIVE_SOURCE_MODE_REQUIRED"})
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
                raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                input_sha = sha256(raw).hexdigest()
                run = ReceiptRun(output_root)
                run.archive_input(raw, expected_sha256=input_sha)
                try:
                    result = _calculate_modal(payload, case=case, run=run, input_sha=input_sha)
                    geometry = None
                    if url.path in ("/api/live-suite", "/api/live-vs04"):
                        geometry = evaluate_geometry_capture(payload.get("geometry_capture"))
                        run.record("quick-geometry", geometry, input_sha256=input_sha)
                    extra = None
                    if url.path in ("/api/live-suite", "/api/live-vs04") and "next_capture" in payload:
                        extra = evaluate_next_capture(payload["next_capture"], payload.get("geometry_capture"))
                        run.record("quick-extra", extra, input_sha256=input_sha)
                    vs04 = None
                    vs04_numerics = None
                    vs04_readiness = None
                    vs04_pipeline = None
                    if "analysis_sources" in payload:
                        vs04 = review_analysis_sources(payload["analysis_sources"])
                        run.record("vs04-schema", vs04, input_sha256=input_sha)
                        vs04_numerics = evaluate_analysis_numerics(payload["analysis_sources"])
                        run.record("vs04-numerics", vs04_numerics, input_sha256=input_sha)
                        vs04_readiness = review_normative_readiness(payload["analysis_sources"])
                        run.record("vs04-readiness", vs04_readiness, input_sha256=input_sha)
                        if payload["analysis_sources"].get("pipeline_stage_required") is True:
                            vs04_pipeline = evaluate_single_run_source_pipeline(payload)
                            run.record("vs04-pipeline", vs04_pipeline, input_sha256=input_sha)
                    story_drift = None
                    if ("vs05_delta_source" in payload or
                            "vs05_delta_capture_error" in payload):
                        from .story_drift_binding import bind_story_drift
                        story_drift = bind_story_drift(
                            payload.get("vs05_delta_source"),
                            capture_error=payload.get("vs05_delta_capture_error"))
                        run.record("vs05-story-drift", story_drift, input_sha256=input_sha)
                    meta = payload.get("capture_metadata") or {}
                    run.record("live-capture", {
                        "status": "SOURCE_CAPTURED", "source_mode": "LIVE_ETABS",
                        "case": case, "source_rows": payload["table"]["row_count"],
                        "display_selection_restored": bool(meta.get("display_selection_restored")),
                        "engineering_release": "NOT_READY",
                    }, input_sha256=input_sha)
                    self.reply(200, {
                        "run_id": run.run_id, "result": result,
                        "model_name": ntpath.basename(str(meta.get("model_filename", ""))),
                        "case_row_count": meta.get("case_row_count"),
                        "source_rows": payload["table"]["row_count"],
                        "source_mode": "LIVE_ETABS", "geometry": geometry, "extra_checks": extra,
                        "vs04_schema": vs04, "vs04_numerics": vs04_numerics,
                        "vs04_readiness": vs04_readiness,
                        "vs04_pipeline": vs04_pipeline,
                        **({"story_drift": story_drift}
                           if story_drift is not None else {}),
                        "formal_compliance": "NOT_PROVEN",
                        "engineering_release": "NOT_READY",
                    })
                except (ValueError, TypeError, KeyError) as exc:
                    result = {"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}
                    run.record("rejected", result, input_sha256=input_sha)
                    self.reply(422, {"run_id": run.run_id, "result": result})
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
                    raise SourceError("Kaynak JSON nesne olmalı")
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
                        raise SourceError("Modal vaka adı zorunlu")
                    result = _calculate_modal(payload, case=case, run=run, input_sha=input_sha)
                self.reply(200, {"run_id": run.run_id, "result": result, "engineering_release": "NOT_READY"})
            except (ValueError, UnicodeError, KeyError, TypeError) as exc:
                result = {"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}
                run.record("rejected", result, input_sha256=input_sha)
                self.reply(422, {"run_id": run.run_id, "result": result})

    return Handler


def serve(*, host: str = "127.0.0.1", port: int = 8765, output_root: Path = Path(".receipts")) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("VS01 web UI accepts localhost only; use a trusted port forward in Codespaces")
    with ThreadingHTTPServer((host, port), make_handler(Path(output_root))) as server:
        print(f"TBDY Next Engine VS01: http://{host}:{server.server_port} | receipts: {output_root}")
        server.serve_forever()
