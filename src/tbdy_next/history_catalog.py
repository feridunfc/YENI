"""Small navigation records for the workspace. Opening a run verifies its sealed inputs."""

import json
import mmap
import ntpath
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .receipts import receipt_paths


_RUN = re.compile(r"RUN-[0-9a-f]{32}\Z")
_TAIL = 16384
_SHA = re.compile(rb'^  "receipt_sha256": "([0-9a-f]{64})"', re.M)
_STAGE = re.compile(rb'^  "stage": ("[^"\r\n]+")', re.M)
_STATUS = re.compile(rb'^    "status": ("[^"\r\n]*"|null),?\r?$', re.M)
_MEMBER = re.compile(rb'^    "member_id": ("[^"\r\n]+"),?\r?$', re.M)


def _value(pattern, data):
    match = pattern.search(data)
    return json.loads(match[1]) if match else None


def _legacy_header(path, stage):
    size = path.stat().st_size
    if size <= 65536:
        record = json.loads(path.read_bytes())
        if record.get("stage") != stage or record.get("run_id") != path.parent.name:
            return None
        return record
    with path.open("rb") as stream:
        stream.seek(max(0, size - _TAIL))
        tail = stream.read()
        receipt_sha = _SHA.search(tail)
        if not receipt_sha or _value(_STAGE, tail) != stage:
            return None
        status = _value(_STATUS, tail)
        payload = {"status": status}
        if stage != "engine-results" and (status is None or stage == "column-pmm"):
            # Historical receipts are indented by ReceiptRun. Only direct payload keys match.
            with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as body:
                payload["status"] = _value(_STATUS, body)
                if stage == "column-pmm":
                    payload["member_id"] = _value(_MEMBER, body)
        return {"stage": stage, "receipt_sha256": receipt_sha[1].decode("ascii"), "payload": payload}


def _legacy_model(directory, fallback):
    if fallback:
        return ntpath.basename(fallback)
    path = directory / "input.source"
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        return None
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as source:
        match = re.search(rb'"capture_metadata"\s*:\s*\{', source)
        if not match:
            return None
        # The original ETABS header is a small object in both compact and pretty-printed archives.
        try:
            meta, _ = json.JSONDecoder().raw_decode(source[match.end()-1:match.end()+65536].decode("utf-8", errors="replace"))
            return ntpath.basename(meta.get("model_filename", "")) or None
        except (ValueError, TypeError, AttributeError):
            return None


def _entry(directory):
    paths = receipt_paths(directory)
    if any(path.is_symlink() for path in paths):
        return None
    steps = []
    modal = schema = {}
    member = model = None
    for path in paths:
        stage = path.stem.partition("-")[2]
        try:
            record = _legacy_header(path, stage)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not record:
            continue
        steps.append(_step(record))
        payload = record["payload"]
        if stage == "modal":
            modal = record
        elif stage == "schema":
            schema = record
        elif stage == "column-pmm":
            member = payload.get("member_id")
        elif stage == "live-capture" and payload.get("model_basename"):
            model = payload["model_basename"]
        elif stage == "r08-second-order":
            model = (payload.get("configuration") or {}).get("live_model_basename")
    quick = None
    if (modal and schema and modal.get("input_sha256") == schema.get("input_sha256")
            and schema["payload"].get("target_case") == modal["payload"].get("case")
            and schema["payload"].get("status") == "SCHEMA_VALID"
            and any(s["stage"] == "quick-geometry" for s in steps)):
        quick = {"run_id": directory.name, "case": modal["payload"]["case"],
                 "captured_at_utc": modal["captured_at_utc"], "source_mode": schema["payload"].get("source_mode"),
                 "model_name": _legacy_model(directory, model)}
        if member:
            quick["pmm_member_id"] = member
    return {"steps": steps, "quick": quick, "modal_at": modal.get("captured_at_utc")}


def _step(record):
    return {"stage": record["stage"], "status": record["payload"].get("status"), "receipt_sha256": record["receipt_sha256"]}


def _stamp(directory):
    with os.scandir(directory) as files:
        stamps = []
        for f in files:
            if f.name.endswith((".json", ".source")):
                stat = f.stat(follow_symlinks=False)
                stamps.append((f.name, stat.st_size, stat.st_mtime_ns))
    return json.dumps(sorted(stamps), separators=(",", ":"))


def _database(root):
    cache = root / ".history-catalog.sqlite3"
    schema = "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, stamp TEXT, entry TEXT)"
    modal = "CREATE TABLE IF NOT EXISTS modal_verified (id TEXT PRIMARY KEY, digest TEXT, data TEXT)"
    db = None
    try:
        if cache.is_symlink():
            raise ValueError("HISTORY_INDEX_PATH_INVALID")
        db = sqlite3.connect(cache, timeout=0.1)
        db.execute(schema)
        db.execute(modal)
        db.execute("SELECT id, stamp, entry FROM runs LIMIT 0")
        return db
    except (OSError, ValueError, sqlite3.Error):
        if db is not None:
            db.close()
        db = sqlite3.connect(":memory:")
        db.execute(schema)
        db.execute(modal)
        return db


def record_listing(run, model_filename, case, pmm_member, suite, *, modal_result=None, source_rows=None):
    quick = None
    if suite:
        quick = {"run_id": run.run_id, "captured_at_utc": run.modal_timestamp,
                 "source_mode": "LIVE_ETABS", "model_name": ntpath.basename(model_filename or "") or None, "case": case}
        if pmm_member:
            quick["pmm_member_id"] = pmm_member
    try:
        with closing(_database(run.root.parent)) as db, db:
            db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?)",
                       (run.run_id, _stamp(run.root), json.dumps({"steps": run.listing_steps, "quick": quick, "modal_at":run.modal_timestamp})))
            if modal_result is not None:
                from .history import _read_receipt
                modal = _read_receipt(run.root, "modal")
                schema = _read_receipt(run.root, "schema")
                values = (schema or {}).get("payload", {})
                if (modal and schema and modal["payload"] == modal_result and values.get("status") == "SCHEMA_VALID"
                        and modal["input_sha256"] == schema["input_sha256"] and values.get("source_mode") == "LIVE_ETABS"
                        and values.get("target_case") == modal_result.get("case") == case
                        and type(source_rows) is int and source_rows == values.get("raw_row_count")
                        and 0 < values["case_row_count"] <= source_rows):
                    summary = {"run_id":run.run_id,"captured_at_utc":modal["captured_at_utc"],"case":case,
                               "model_name":ntpath.basename(model_filename or "") or None,"source_mode":"LIVE_ETABS",
                               "case_row_count":values["case_row_count"],"raw_row_count":source_rows,"result":modal_result,
                               "input_sha256":modal["input_sha256"],"receipt_sha256":modal["receipt_sha256"],
                               "engineering_release":"NOT_READY"}
                    db.execute("INSERT OR REPLACE INTO modal_verified VALUES (?,?,?)",
                               (run.run_id,verification_key(run.root),json.dumps(summary)))
    except (OSError, ValueError, sqlite3.Error):
        # A locked or read-only catalog can be reconstructed from the completed receipts.
        return


def listing(root, *, quick=False, modal=False, limit=60):
    """Catalog entries are navigation hints. No verdict or large result body is loaded here."""
    root = Path(root)
    if not root.is_dir():
        return []
    # The index is disposable and isolated from the append-only run directories.
    with closing(_database(root)) as db:
        cached = {key: (stamp, entry) for key, stamp, entry in db.execute("SELECT id, stamp, entry FROM runs")}
        output, updates = [], []
        with os.scandir(root) as directories:
            for child in directories:
                if not _RUN.fullmatch(child.name) or not child.is_dir(follow_symlinks=False):
                    continue
                try:
                    stamp = _stamp(child.path)
                    old_stamp, raw = cached.get(child.name, (None, None))
                    if stamp != old_stamp:
                        entry = _entry(Path(child.path))
                        raw = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
                        updates.append((child.name, stamp, raw))
                    else:
                        entry = json.loads(raw)
                    if entry is not None:
                        if modal:
                            if "modal_at" not in entry:
                                from .history import _read_receipt
                                record = _read_receipt(Path(child.path), "modal") or {}
                                entry["modal_at"] = record.get("captured_at_utc")
                                updates.append((child.name, stamp, json.dumps(entry)))
                            if entry["modal_at"]:
                                output.append({"run_id":child.name, "captured_at_utc":entry["modal_at"]})
                        elif not quick:
                            output.append({"run_id": child.name, "steps": entry["steps"]})
                        elif entry["quick"]:
                            output.append(entry["quick"])
                except (OSError, KeyError, TypeError, ValueError):
                    continue
        if updates:
            try:
                with db:
                    db.executemany("INSERT OR REPLACE INTO runs VALUES (?,?,?)", updates)
            except sqlite3.Error:
                pass  # Source-backed listing is still available when a cache write is denied.
    if quick or modal:
        return sorted(output, key=lambda r: (r["captured_at_utc"], r["run_id"]), reverse=True)[:limit]
    return sorted(output, key=lambda r: r["run_id"], reverse=True)[:limit]


def verification_key(directory):
    from hashlib import sha256
    from .archive_blobs import archive_file_hash
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("RUN_DIRECTORY_UNSAFE")
    paths = receipt_paths(directory) + [directory / "input.source"]
    for name in ("parent.source", "engine-results.payload"):
        path = directory / name
        if path.exists() or path.is_symlink():
            paths.append(path)
    return sha256(json.dumps([(p.name, archive_file_hash(p)) for p in paths]).encode()).hexdigest()


def _modal_key(directory):
    from .history import _read_receipt
    try:
        paths = receipt_paths(directory)
        if not any(p.stem.partition("-")[2] == "live-capture" for p in paths):
            discovery = _read_receipt(directory,"schema-discovery") or {}
            if discovery.get("receipt_schema") is not None:
                return None  # A modern run is visible as soon as its terminal seal is written.
        return verification_key(directory)
    except (OSError, ValueError):
        return None


def verified_modal_listing(root, limit):
    from concurrent.futures import ThreadPoolExecutor
    from .history import _read_modal_run, _read_receipt
    candidates = iter(listing(root, modal=True, limit=None))
    rows = []
    from itertools import islice
    with closing(_database(root)) as db, ThreadPoolExecutor(max_workers=min(4,limit)) as workers:
        while len(rows) < limit:
            dirs = [root/c["run_id"] for c in islice(candidates,limit-len(rows))]
            if not dirs:
                break
            for directory, digest in zip(dirs,workers.map(_modal_key,dirs)):
                if digest is None:
                    continue
                try:
                    rid = directory.name
                    hit = db.execute("SELECT data FROM modal_verified WHERE id=? AND digest=?", (rid,digest)).fetchone()
                    row = json.loads(hit[0]) if hit else None
                    modal = _read_receipt(directory, "modal")
                    if not (row and modal and row["receipt_sha256"] == modal["receipt_sha256"]
                            and row["result"] == modal["payload"] and row["input_sha256"] == modal["input_sha256"]
                            and row["run_id"] == rid and row["captured_at_utc"] == modal["captured_at_utc"]):
                        row = _read_modal_run(directory)
                        if row is None or digest != verification_key(directory):
                            continue
                        try:
                            with db:
                                db.execute("INSERT OR REPLACE INTO modal_verified VALUES (?,?,?)", (rid,digest,json.dumps(row)))
                        except sqlite3.Error:
                            pass
                    rows.append(row)
                except (OSError, ValueError, TypeError, KeyError):
                    continue
    return rows
