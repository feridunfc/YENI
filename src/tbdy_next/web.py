"""Local, dependency-free VS01 web UI and traceable JSON endpoints.

No ETABS COM, save, run, or hidden network calls. The UI processes uploaded JSON
using the same project-owned source and modal functions as the CLI.
"""
from __future__ import annotations

from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from .modal import evaluate_modal_mass
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


def make_handler(output_root: Path):
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
            else:
                self.reply(404, {"error": "NOT_FOUND"})

        def do_POST(self) -> None:
            url = urlsplit(self.path)
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
