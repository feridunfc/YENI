"""R00/R01: deterministic, read-only VS27 batch ZIP and SQLite source gate.

No ETABS, COM, web, native design inference, or archive rewriting.
A valid archive with missing FrameForce is a *valid blocked* source, never PASS.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import sys
import zipfile

BATCH_SCHEMA = "tbdy.next.column-batch-live.v1"
MEMBER_SCHEMA = "tbdy.next.column-batch-member.v1"
MAX_MEMBERS = 2500
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024


class SourceGateError(ValueError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _sealed(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise SourceGateError(f"NOT_OBJECT:{label}")
    claimed = value.get("payload_sha256")
    if type(claimed) is not str or _sha(_canonical({k: v for k, v in value.items()
                                               if k != "payload_sha256"})) != claimed:
        raise SourceGateError(f"PAYLOAD_SEAL_MISMATCH:{label}")
    return value


def _safe_members(z: zipfile.ZipFile):
    infos = z.infolist()
    if not 3 <= len(infos) <= MAX_MEMBERS:
        raise SourceGateError("ZIP_MEMBER_COUNT_OUT_OF_BOUNDS")
    if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        raise SourceGateError("ZIP_TOO_LARGE")
    seen = set()
    for i in infos:
        name = i.filename
        pure = PurePosixPath(name)
        if (not name or name in seen or name.startswith(("/", "\\"))
                or "\\" in name or ":" in name or ".." in pure.parts or pure.is_absolute()
                or i.file_size > MAX_MEMBER_BYTES or i.is_dir()
                or stat.S_ISLNK(i.external_attr >> 16)):
            raise SourceGateError("UNSAFE_OR_DUPLICATE_ZIP_MEMBER")
        seen.add(name)
    return seen


def _selection(index, common):
    a, b = index.get("selection_transaction"), common.get("selection_transaction")
    if a != b:
        raise SourceGateError("SELECTION_PROVENANCE_CONFLICT")
    if a is None or a.get("mode") == "GETTERS_ONLY":
        if index.get("no_etabs_setters_used") is not True or common.get("no_etabs_setters_used") is not True:
            raise SourceGateError("FALSE_GETTERS_ONLY_CLAIM")
        return "GETTERS_ONLY"
    if a.get("mode") != "EXPLICIT_TEMPORARY_OUTPUT_AND_DISPLAY":
        raise SourceGateError("UNKNOWN_SELECTION_MODE")
    if (a.get("restoration") != "VERIFIED" or a.get("output_flags_restored_exactly") is not True
            or a.get("model_analysis_design_save_setters_used") is not False
            or index.get("no_etabs_setters_used") is not False
            or common.get("no_etabs_setters_used") is not False):
        raise SourceGateError("TEMPORARY_SELECTION_NOT_VERIFIED")
    if "table_display_phase_closed" in a and a["table_display_phase_closed"] is not True:
        raise SourceGateError("DISPLAY_PHASE_NOT_CLOSED")
    for prefix in ("display", "output"):
        if prefix == "display":
            before, after = a.get("display_before"), a.get("display_after")
        else:
            before = {k: a.get("original_selected_output_" + k) for k in ("cases", "combinations")}
            after = {k: a.get("restored_selected_output_" + k) for k in ("cases", "combinations")}
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise SourceGateError("RESTORATION_SNAPSHOT_MISSING")
        for k in ("cases", "combinations"):
            x, y = before.get(k), after.get(k)
            if (not isinstance(x, list) or not isinstance(y, list)
                    or len(x) != len(set(x)) or len(y) != len(set(y)) or set(x) != set(y)):
                raise SourceGateError("SELECTION_RESTORATION_CONFLICT:" + prefix + ":" + k)
    return "TEMPORARY_RESTORED"


def _force_count(record: dict, frame: str) -> int:
    if record.get("frame_name") != frame or record.get("schema") != MEMBER_SCHEMA:
        raise SourceGateError("FRAME_OR_SCHEMA_MISMATCH:" + frame)
    if record.get("final_design_eligible") is not False:
        raise SourceGateError("FORGED_DESIGN_RELEASE:" + frame)
    force = record.get("force", {})
    rows = force.get("native_row_count")
    if type(rows) is not int or rows < 0:
        raise SourceGateError("INVALID_FRAME_ROW_COUNT:" + frame)
    calls = [x for x in record.get("native_calls", []) if x.get("api") == "Results.FrameForce"]
    if len(calls) != 1 or calls[0].get("call_id") != force.get("source_call_id"):
        raise SourceGateError("FRAMEFORCE_CALL_UNBOUND:" + frame)
    call = calls[0]
    if rows == 0:
        if force.get("status") == "CAPTURED" or call.get("return_code") == 0:
            raise SourceGateError("EMPTY_FRAMEFORCE_MISLABELED:" + frame)
        return 0
    if (force.get("status") != "CAPTURED" or call.get("return_code") != 0
            or call.get("status") != "OBSERVED"):
        raise SourceGateError("FRAMEFORCE_ROWS_NOT_OBSERVED:" + frame)
    values = call.get("values", {})
    fields = ("Obj", "ObjSta", "Elm", "ElmSta", "LoadCase", "StepType", "StepNum",
              "P", "V2", "V3", "T", "M2", "M3")
    if values.get("NumberResults") != rows or any(type(values.get(k)) is not list
                                                    or len(values[k]) != rows for k in fields):
        raise SourceGateError("FRAMEFORCE_ARRAY_LENGTH_MISMATCH:" + frame)
    for i in range(rows):
        if values["Obj"][i] != frame or not values["Elm"][i] or not values["LoadCase"][i]:
            raise SourceGateError("FRAMEFORCE_ROW_IDENTITY_ERROR:" + frame)
        for k in ("ObjSta", "ElmSta", "StepNum", "P", "V2", "V3", "T", "M2", "M3"):
            v = values[k][i]
            if type(v) not in (int, float) or not math.isfinite(v):
                raise SourceGateError("FRAMEFORCE_NONFINITE_VALUE:" + frame + ":" + k)
    return rows


def audit_batch(path, *, expected_columns=None) -> dict:
    path = Path(path)
    if not path.is_file():
        raise SourceGateError("ARCHIVE_MISSING")
    with zipfile.ZipFile(path, "r") as z:
        names = _safe_members(z)
        if not {"manifest.json", "index.json", "common.json"}.issubset(names):
            raise SourceGateError("BATCH_ROOT_DOCUMENT_MISSING")
        get = lambda n: _sealed(json.loads(z.read(n)), n)
        manifest = get("manifest.json")
        declared = manifest.get("files")
        if manifest.get("schema") != BATCH_SCHEMA or not isinstance(declared, dict) or set(declared) != names - {"manifest.json"}:
            raise SourceGateError("MANIFEST_POPULATION_MISMATCH")
        for name, claimed in declared.items():
            if type(claimed) is not str or _sha(z.read(name)) != claimed:
                raise SourceGateError("ZIP_CONTENT_HASH_MISMATCH:" + name)
        index, common = get("index.json"), get("common.json")
        if (index.get("schema") != BATCH_SCHEMA or common.get("schema") != BATCH_SCHEMA
                or index.get("payload_file_sha256") != {k: v for k, v in declared.items() if k != "index.json"}):
            raise SourceGateError("INDEX_MANIFEST_BINDING_MISMATCH")
        source = common.get("source", {})
        if (source != index.get("source") or source.get("units_code") != 6
                or source.get("model_locked") is not True):
            raise SourceGateError("SOURCE_CONTEXT_MISMATCH")
        selection = _selection(index, common)
        ids = common.get("population", {}).get("columns")
        if (not isinstance(ids, list) or not ids or any(type(v) is not str or not v for v in ids)
                or len(set(ids)) != len(ids) or index.get("observed_column_count") != len(ids)
                or (expected_columns is not None and len(ids) != expected_columns)
                or set("columns/" + v + ".json" for v in ids) != {n for n in names if n.startswith("columns/")}
                or [c.get("frame_name") for c in index.get("columns", [])] != ids):
            raise SourceGateError("PHYSICAL_COLUMN_CENSUS_MISMATCH")
        counts = Counter()
        rows = 0
        for frame in ids:
            rec = get("columns/" + frame + ".json")
            n = _force_count(rec, frame)
            rows += n
            counts["frames_with_force_rows" if n else "frames_without_force_rows"] += 1
            summary = rec.get("design_summary", {})
            if summary.get("status") == "OBSERVED" and summary.get("values", {}).get("NumberItems", 0) > 0:
                counts["frames_with_commercial_summary"] += 1
        if rows == 0:
            readiness = "BLOCKED_NO_NATIVE_FORCE_ROWS"
        elif counts["frames_without_force_rows"]:
            readiness = "PARTIAL_NATIVE_FORCE_POPULATION"
        else:
            readiness = "SOURCE_ROWS_PRESENT_REPLAY_REQUIRED"
        return {
            "schema": "tbdy.next.r00-offline-source-gate.v1",
            "archive_sha256": _file_sha(path),
            "archive_manifest_verified": True,
            "member_count": len(ids), "native_force_rows": rows,
            "member_force_count": counts["frames_with_force_rows"],
            "member_force_missing_count": counts["frames_without_force_rows"],
            "commercial_summary_member_count": counts["frames_with_commercial_summary"],
            "selection_provenance": selection,
            "source_generation_proven": bool(index.get("analysis_generation_proven") is True),
            "source_readiness": readiness,
            "spectral_replay_verified": False,
            "normative_design_approved": False,
            "engineering_release": "NOT_READY",
        }


def _file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit_sqlite(path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise SourceGateError("SQLITE_MISSING")
    original = _file_sha(p)
    try:
        uri = p.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA trusted_schema=OFF")
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            tables = connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        raise SourceGateError("SQLITE_READ_ONLY_VALIDATION_FAILED") from exc
    if _file_sha(p) != original:
        raise SourceGateError("SQLITE_MUTATED")
    return {"sha256": original, "quick_check": integrity, "table_count": tables,
            "read_only": True, "integrity_ok": integrity == "ok"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--expected-columns", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-force", action="store_true",
                        help="Exit 2 if source does not contain native FrameForce rows for every member")
    args = parser.parse_args(argv)
    try:
        result = audit_batch(args.archive, expected_columns=args.expected_columns)
        if args.database:
            result["database"] = audit_sqlite(args.database)
            if not result["database"]["integrity_ok"]:
                raise SourceGateError("SQLITE_QUICK_CHECK_NOT_OK")
    except (SourceGateError, ValueError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(json.dumps({"source_gate": "INVALID", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    if args.output:
        if args.output.exists():
            print("OUTPUT_EXISTS_USE_DIFFERENT_PATH", file=sys.stderr)
            return 3
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.require_force and result["source_readiness"] != "SOURCE_ROWS_PRESENT_REPLAY_REQUIRED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
