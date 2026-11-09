"""Append-only YENI receipts and a separate SQLite projection of column states.

The historical D7-B6 database is read-only. Original ZIP bytes and normalized
states stay local to their own run; frame IDs never join a different ETABS run.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3

from ..history import _RUN, _read_receipt
from ..receipts import ReceiptRun
from .native_archive import BankError, MAX_ARCHIVE_BYTES, canonical, digest, decode
from .source_bank import SCHEMA, recover_column_bank

APP_ID = 0x59434F4C
MAX_DATABASE_BYTES = 256 * 1024 * 1024


def _file_bytes(path, limit):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise BankError("REGULAR_BOUNDED_SOURCE_FILE_REQUIRED")
    return path.read_bytes()


def _readonly(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)


def reconcile_historical_db(bank, path):
    raw = _file_bytes(path, 16 * 1024 * 1024)
    with closing(_readonly(path)) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BankError("HISTORICAL_DB_INTEGRITY_ERROR")
        counts = {name: db.execute('SELECT count(*) FROM "' + name + '"').fetchone()[0]
                  for name in ("wall_reactions", "pier_forces", "d7b3_column_console")}
        targets = list(db.execute("SELECT story, output_case, column_P_kN FROM d7b3_column_console"))
    if len({(s, c) for s, c, _ in targets}) != len(targets):
        raise BankError("HISTORICAL_TARGET_DUPLICATE")
    by_member_case = defaultdict(list)
    for row in bank["force_states"]:
        by_member_case[(row["Obj"], row["LoadCase"])].append(row)
    groups = defaultdict(list)
    for member in bank["members"]:
        story = member.get("context", {}).get("frame", {}).get("story_label")
        groups[story].append(member["frame_name"])
    items = []
    for story, case, expected in targets:
        values, row_ids, missing = [], [], []
        for name in groups.get(story, []):
            candidates = [r for r in by_member_case[(name, case)]
                          if r["StepType"] == "Single Value" and abs(r["ObjSta"]) <= 1e-9]
            if len(candidates) != 1:
                missing.append(name)
            else:
                values.append(candidates[0]["P"]); row_ids.append(candidates[0]["source_row_id"])
        actual = math.fsum(values) if values and not missing else None
        if type(expected) not in (int, float) or not math.isfinite(expected):
            raise BankError("HISTORICAL_TARGET_NUMBER_INVALID")
        items.append({"story": story, "output_case": case, "column_count": len(values),
            "native_signed_p_sum_kN": actual, "historical_signed_p_kN": expected,
            "difference_kN": actual - expected if actual is not None else None,
            "numeric_match": actual is not None and abs(actual - expected) <= 1e-7,
            "missing_members": missing, "source_row_ids": row_ids})
    return {"source_sha256": sha256(raw).hexdigest(), "tables": counts, "items": items,
        "numeric_matches": sum(r["numeric_match"] for r in items),
        "scope": "HISTORICAL_SIGNED_P_REPRODUCTION_ONLY", "same_cut_proven": False,
        "analysis_generation_proven": False, "story_phi_authority": "DENIED"}


def save_column_bank(archive_path, output_root, *, historical_db=None):
    raw = _file_bytes(archive_path, MAX_ARCHIVE_BYTES)
    bank = recover_column_bank(raw)
    if historical_db is not None:
        bank["historical_reconciliation"] = reconcile_historical_db(bank, historical_db)
        bank["result_sha256"] = digest({k: v for k, v in bank.items() if k != "result_sha256"})
    run = ReceiptRun(Path(output_root))
    run.archive_input(raw, expected_sha256=bank["source_archive_sha256"])
    database = run.root / "column-bank.sqlite"
    summary = {k: v for k, v in bank.items() if k not in ("force_states", "static_replay")}
    summary["static_replay"] = {k: v for k, v in bank["static_replay"].items() if k != "items"}
    summary["run_id"] = run.run_id
    summary["imported_at_utc"] = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(database)) as db:
        db.executescript('''
            PRAGMA user_version = 1;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE members (member_id TEXT PRIMARY KEY, data_json TEXT NOT NULL);
            CREATE TABLE force_states (
                row_id TEXT PRIMARY KEY, member_id TEXT NOT NULL, output_case TEXT NOT NULL,
                analysis_element_id TEXT NOT NULL, object_station_m REAL NOT NULL,
                element_station_m REAL NOT NULL, step_type TEXT NOT NULL, step_number REAL NOT NULL,
                P_kN REAL NOT NULL, V2_kN REAL NOT NULL, V3_kN REAL NOT NULL,
                T_kNm REAL NOT NULL, M2_kNm REAL NOT NULL, M3_kNm REAL NOT NULL,
                source_call_id TEXT NOT NULL, source_row_index INTEGER NOT NULL, data_json TEXT NOT NULL);
            CREATE INDEX force_selection ON force_states(member_id, output_case);
            CREATE TABLE combination_replay (
                member_id TEXT NOT NULL, combination TEXT NOT NULL, status TEXT NOT NULL, data_json TEXT NOT NULL);
            CREATE INDEX replay_selection ON combination_replay(member_id, combination);
        ''')
        db.execute("PRAGMA application_id = " + str(APP_ID))
        db.execute("INSERT INTO metadata VALUES (?, ?)", ("report", canonical(summary).decode()))
        db.executemany("INSERT INTO members VALUES (?, ?)",
                       ((m["frame_name"], canonical(m).decode()) for m in bank["members"]))
        db.executemany("INSERT INTO force_states VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            (r["source_row_id"], r["Obj"], r["LoadCase"], r["Elm"], r["ObjSta"], r["ElmSta"],
             r["StepType"], r["StepNum"], r["P"], r["V2"], r["V3"], r["T"], r["M2"], r["M3"],
             r["call_id"], r["source_row_index"], canonical(r).decode()) for r in bank["force_states"]))
        db.executemany("INSERT INTO combination_replay VALUES (?,?,?,?)", (
            (r["member_id"], r["combination"], r["status"], canonical(r).decode())
            for r in bank["static_replay"]["items"]))
        db.commit()
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BankError("DERIVED_DATABASE_INTEGRITY_ERROR")
    db_sha = sha256(database.read_bytes()).hexdigest()
    run.record("column-bank", {"schema": SCHEMA, "database_sha256": db_sha,
        "result_sha256": bank["result_sha256"], "selected_column_count": bank["selected_column_count"],
        "force_row_count": bank["force_row_count"], "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY"}, input_sha256=bank["source_archive_sha256"])
    return summary | {"database_sha256": db_sha}


def verified_database(root, run_id):
    if not isinstance(run_id, str) or not _RUN.fullmatch(run_id):
        raise BankError("EXACT_COLUMN_RUN_ID_REQUIRED")
    directory = Path(root) / run_id
    if directory.is_symlink() or not directory.is_dir():
        raise BankError("COLUMN_RUN_UNAVAILABLE")
    receipt = _read_receipt(directory, "column-bank")
    if receipt is None or receipt["payload"].get("schema") != SCHEMA:
        raise BankError("COLUMN_RECEIPT_UNVERIFIED")
    source = _file_bytes(directory / "input.source", MAX_ARCHIVE_BYTES)
    database = directory / "column-bank.sqlite"
    raw = _file_bytes(database, MAX_DATABASE_BYTES)
    if (sha256(source).hexdigest() != receipt["input_sha256"]
            or sha256(raw).hexdigest() != receipt["payload"].get("database_sha256")):
        raise BankError("COLUMN_ARCHIVE_OR_DATABASE_CHANGED")
    with closing(_readonly(database)) as db:
        if db.execute("PRAGMA application_id").fetchone()[0] != APP_ID or db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise BankError("COLUMN_DATABASE_SCHEMA_INVALID")
        report = decode(db.execute("SELECT value FROM metadata WHERE key='report'").fetchone()[0])
        if (report.get("schema") != SCHEMA or report.get("run_id") != run_id
                or report.get("source_archive_sha256") != receipt["input_sha256"]
                or report.get("result_sha256") != receipt["payload"].get("result_sha256")
                or report.get("design_demand_authority") != "DENIED"
                or report.get("formal_compliance") != "NOT_PROVEN"
                or report.get("engineering_release") != "NOT_READY"):
            raise BankError("COLUMN_REPORT_CONTRACT_INVALID")
    return database, report | {"database_sha256": receipt["payload"]["database_sha256"]}


def column_bank_history(root):
    result = []
    for directory in sorted(Path(root).glob("RUN-*"), key=lambda p: p.name, reverse=True):
        if not list(directory.glob("[0-9][0-9]-column-bank.json")):
            continue
        try:
            _, report = verified_database(root, directory.name)
            result.append({k: report[k] for k in ("run_id", "source_archive_sha256", "selected_column_count",
                "force_row_count", "recorded_output_count", "source_kind", "formal_compliance", "imported_at_utc")})
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            continue
    return sorted(result, key=lambda r: r["imported_at_utc"], reverse=True)[:30]


def read_column_bank(root, run_id, *, member_id=None, output_case=None, offset=0, limit=200, full=False, view="native"):
    database, report = verified_database(root, run_id)
    if (type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500
            or view not in ("native", "static", "design", "critical", "reinforcement", "stiffness", "eccentricity", "cages", "pmm", "transverse", "shear", "joints", "joint-ties", "end-forces", "kinematics", "stiffness-scenarios", "length-sensitivity", "overview", "pmm-quality")):
        raise BankError("COLUMN_PAGE_INVALID")
    if view in ("reinforcement", "stiffness", "cages", "transverse", "joints", "joint-ties", "stiffness-scenarios") and output_case is not None:
        raise BankError("CASE_FILTER_NOT_APPLICABLE_TO_SECTION_VIEW")
    from .demand_view import demand_view
    report.update(demand_view(database, report, member_id=member_id, output_case=output_case,
        offset=offset, limit=limit, view=view, full=full))
    with closing(_readonly(database)) as db:
        if full:
            report["force_states"] = [decode(row[0]) for row in db.execute("SELECT data_json FROM force_states ORDER BY rowid")]
            report["static_replay"]["items"] = [decode(row[0]) for row in db.execute("SELECT data_json FROM combination_replay ORDER BY rowid")]
            return report
        where, values = [], []
        for column, value in (("member_id", member_id), ("output_case", output_case)):
            if value is not None:
                where.append(column + "=?"); values.append(value)
        clause = " WHERE " + " AND ".join(where) if where else ""
        total = db.execute("SELECT count(*) FROM force_states" + clause, values).fetchone()[0]
        rows = db.execute("SELECT data_json FROM force_states" + clause + " ORDER BY rowid LIMIT ? OFFSET ?", [*values, limit, offset])
        report["force_page"] = {"member_id": member_id, "output_case": output_case, "offset": offset,
            "limit": limit, "total": total, "rows": [decode(row[0]) for row in rows]}
    return report
