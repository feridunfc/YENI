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
from .history import modal_history
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
        server_version = "TBDYNext/VS01"

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
                self.reply(200, {"status": "READY_FOR_VS01", "implemented_slices": ["MODAL_MASS_RATIO"], "engineering_release": "NOT_READY"})
            elif url.path == "/api/runs":
                self.reply(200, {"runs": _runs(output_root)})
            elif url.path == "/api/modal-history":
                self.reply(200, {"runs": modal_history(output_root), "engineering_release": "NOT_READY"})
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
            if url.path == "/api/live-modal":
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
                raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                input_sha = sha256(raw).hexdigest()
                run = ReceiptRun(output_root)
                run.archive_input(raw, expected_sha256=input_sha)
                try:
                    result = _calculate_modal(payload, case=case, run=run, input_sha=input_sha)
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
                        "source_mode": "LIVE_ETABS", "engineering_release": "NOT_READY",
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
