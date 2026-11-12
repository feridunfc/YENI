"""R01: read-only, fail-closed examination of the archived 87-column native bank.

This is an offline source/numerical replay gate, NOT a design or code-compliance
checker. Never joins a later ETABS capture or silently replaces missing rows.
Only standard-library modules and the existing project source decoder are used.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import sys
import zipfile

from tbdy_next.column_engine.native_archive import decode

FIELDS = ("Obj", "ObjSta", "Elm", "ElmSta", "LoadCase", "StepType", "StepNum",
          "P", "V2", "V3", "T", "M2", "M3")
COMPONENTS = FIELDS[7:]
BANK_SCHEMA = "tbdy.next.column-source-bank.v1"
MAX_UNCOMPRESSED = 210 * 1024 * 1024
DATABASE_APP_ID = 0x59434F4C


class R01Error(ValueError):
    pass


def file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return sha256(stream.read()).hexdigest() if path.stat().st_size == 0 else _stream_sha(stream)


def _stream_sha(stream):
    h = sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(block)
    return h.hexdigest()


def _check_file(path: Path):
    if path.is_symlink() or not path.is_file():
        raise R01Error("REGULAR_SOURCE_FILE_REQUIRED:" + path.name)


def read_bank(path: Path, trusted_zip_sha: str) -> dict:
    _check_file(path)
    if file_sha(path) != trusted_zip_sha:
        raise R01Error("ARCHIVED_BANK_ZIP_SHA_MISMATCH")
    try:
        with zipfile.ZipFile(path) as z:
            members = z.infolist()
            if len(members) != 1:
                raise R01Error("BANK_ARCHIVE_MUST_HAVE_ONE_JSON")
            info = members[0]
            pure = PurePosixPath(info.filename)
            if (info.is_dir() or not info.filename.endswith(".json")
                    or pure.is_absolute() or ".." in pure.parts or "\\" in info.filename
                    or stat.S_ISLNK(info.external_attr >> 16)
                    or not 0 < info.file_size <= MAX_UNCOMPRESSED):
                raise R01Error("BANK_ARCHIVE_MEMBER_INVALID")
            bank = decode(z.read(info))
    except (zipfile.BadZipFile, RuntimeError, UnicodeDecodeError) as exc:
        raise R01Error("BANK_ARCHIVE_UNREADABLE") from exc
    if not isinstance(bank, dict) or bank.get("schema") != BANK_SCHEMA:
        raise R01Error("BANK_SCHEMA_MISMATCH")
    return bank


def _str(value, name):
    if not isinstance(value, str) or not value:
        raise R01Error("IDENTITY_MISSING:" + name)
    return value


def _num(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise R01Error("NONFINITE_OR_NONNUMERIC:" + name)
    return value


def _int(value, name):
    if type(value) is not int or value < 0:
        raise R01Error("INVALID_NONNEGATIVE_COUNT:" + name)
    return value


def force_inventory(bank: dict, expected_columns: int):
    members = bank.get("members")
    rows = bank.get("force_states")
    if not isinstance(members, list) or not isinstance(rows, list):
        raise R01Error("BANK_MEMBER_OR_FORCE_ARRAY_MISSING")
    ids = [_str(m.get("frame_name"), "frame_name") for m in members]
    if (len(ids) != len(set(ids)) or len(ids) != expected_columns
            or bank.get("selected_column_count") != len(ids)
            or bank.get("observed_column_count") != len(ids)
            or bank.get("force_row_count") != len(rows)):
        raise R01Error("MEMBER_OR_FORCE_POPULATION_CONFLICT")
    by_member = Counter()
    by_case = Counter()
    by_member_case = Counter()
    indexed = {}
    row_ids = set()
    for row in rows:
        if not isinstance(row, dict) or any(k not in row for k in FIELDS):
            raise R01Error("NATIVE_FORCE_FIELD_MISSING")
        name = _str(row["Obj"], "Obj")
        if name not in ids:
            raise R01Error("UNKNOWN_NATIVE_COLUMN:" + name)
        for k in ("Elm", "LoadCase", "StepType", "call_id", "source_row_id", "shard_sha256"):
            _str(row.get(k), k)
        if len(row["shard_sha256"]) != 64 or len(row["source_row_id"]) != 64:
            raise R01Error("SOURCE_ROW_OR_SHARD_ID_INVALID")
        for k in ("ObjSta", "ElmSta", "StepNum", *COMPONENTS):
            _num(row[k], k)
        if row["ObjSta"] < 0 or row["ElmSta"] < 0:
            raise R01Error("NEGATIVE_NATIVE_STATION")
        _int(row.get("source_row_index"), "source_row_index")
        key = tuple(row[k] for k in FIELDS[:7])
        if key in indexed or row["source_row_id"] in row_ids:
            raise R01Error("DUPLICATE_NATIVE_TUPLE_OR_ROW_ID")
        indexed[key] = row
        row_ids.add(row["source_row_id"])
        by_member[name] += 1
        by_case[row["LoadCase"]] += 1
        by_member_case[(name, row["LoadCase"])] += 1
    for m in members:
        name = m["frame_name"]
        if (m.get("force_rows") != by_member[name]
                or m.get("force_status") != "OBSERVED_NATIVE_TUPLES"
                or not by_member[name]):
            raise R01Error("MEMBER_FORCE_POPULATION_UNVERIFIED:" + name)
    coverage = bank.get("case_coverage")
    if not isinstance(coverage, list):
        raise R01Error("CASE_COVERAGE_ABSENT")
    observed_cases = set()
    for case in coverage:
        name = _str(case.get("name"), "case")
        if name in observed_cases or case.get("row_count") != by_case[name]:
            raise R01Error("CASE_COVERAGE_CONFLICT:" + name)
        expected = {m for (m, c), n in by_member_case.items() if c == name and n > 0}
        if (case.get("members_with_rows") != len(expected)
                or case.get("missing_members") != sorted(set(ids) - expected, key=ids.index)):
            # The missing roster is authoritative only if it is exactly the complete complement.
            # Preserve native roster ordering from the original bank when checking membership below.
            actual_missing = case.get("missing_members")
            if (case.get("members_with_rows") != len(expected)
                    or not isinstance(actual_missing, list)
                    or set(actual_missing) != set(ids) - expected
                    or len(actual_missing) != len(set(actual_missing))):
                raise R01Error("CASE_MEMBER_COVERAGE_CONFLICT:" + name)
        observed_cases.add(name)
    if observed_cases != set(by_case):
        raise R01Error("CASE_COVERAGE_DENOMINATOR_INCOMPLETE")
    if bank.get("design_demand_authority") != "DENIED" or bank.get("engineering_release") != "NOT_READY":
        raise R01Error("FORGED_DESIGN_AUTHORITY")
    return indexed, {"members": len(ids), "force_rows": len(rows),
                     "distinct_outputs": len(by_case), "member_force_population_complete": True,
                     "case_coverage_slots": len(coverage)}


def replay_recorded_static(bank: dict, indexed: dict) -> dict:
    """Independent six-component arithmetic; does not promote normative authority."""
    definitions = {r["name"]: r for r in bank.get("combination_definitions", [])}
    case_defs = {r["name"]: r for r in bank.get("case_definitions", [])}
    claimed = bank.get("static_replay", {}).get("combinations")
    if not isinstance(claimed, list):
        raise R01Error("RECORDED_STATIC_REPLAY_MISSING")
    allowed = [r for r in claimed if r.get("status") == "NUMERICAL_MATCH"]
    if len(allowed) != 6:
        raise R01Error("EXPECTED_SIX_STATIC_COMBINATIONS")
    by_case = defaultdict(list)
    for key, row in indexed.items():
        by_case[row["LoadCase"]].append((key, row))
    comparisons = 0
    matched_rows = 0
    max_diff = 0.0
    for report in allowed:
        name = _str(report.get("combination"), "combination")
        definition = definitions.get(name)
        if (not definition or definition.get("operator") != 0
                or definition.get("status") != "OBSERVED"):
            raise R01Error("UNSUPPORTED_STATIC_COMBINATION:" + name)
        terms = definition.get("terms", [])
        if not terms:
            raise R01Error("EMPTY_STATIC_TERMS:" + name)
        for term in terms:
            cd = case_defs.get(term.get("name"))
            if (term.get("type") != 0 or not cd or cd.get("case_type") != 1
                    or cd.get("status") != "OBSERVED"):
                raise R01Error("NONSTATIC_COMBINATION_LEAF:" + name)
            _num(term.get("factor"), "factor")
        outputs = by_case[name]
        if len(outputs) != _int(report.get("matched_rows"), "recorded matched_rows"):
            raise R01Error("STATIC_REPLAY_POPULATION_MISMATCH:" + name)
        for key, actual in outputs:
            station = key[:4]
            if key[5:] != ("Single Value", 0.0):
                raise R01Error("STATIC_OUTPUT_STEP_NOT_SINGLE:" + name)
            leaves = []
            for t in terms:
                lookup = (*station, t["name"], "Single Value", 0.0)
                if lookup not in indexed:
                    raise R01Error("STATIC_LEAF_MISSING:" + name + ":" + t["name"])
                leaves.append((Fraction(str(t["factor"])), indexed[lookup]))
            for component in COMPONENTS:
                expected = sum((factor * Fraction(str(leaf[component]))
                                for factor, leaf in leaves), Fraction(0))
                observed = Fraction(str(actual[component]))
                difference = abs(expected - observed)
                tolerance = Fraction("1e-9") + Fraction("1e-12") * max(abs(expected), abs(observed))
                if difference > tolerance:
                    raise R01Error("INDEPENDENT_STATIC_REPLAY_MISMATCH:" + name + ":" + component)
                max_diff = max(max_diff, float(difference))
                comparisons += 1
            matched_rows += 1
    if matched_rows != 2412 or comparisons != matched_rows * 6:
        raise R01Error("STATIC_REPLAY_TOTAL_UNEXPECTED")
    return {"status": "INDEPENDENT_OFFLINE_NUMERICAL_MATCH",
            "static_combinations": len(allowed), "matched_rows": matched_rows,
            "component_comparisons": comparisons, "maximum_abs_difference_native": max_diff,
            "normative_acceptance": "NOT_PROVEN"}


def read_projection(path: Path, bank: dict) -> dict:
    _check_file(path)
    original = file_sha(path)
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
            if db.execute("PRAGMA application_id").fetchone()[0] != DATABASE_APP_ID:
                raise R01Error("SQLITE_APPLICATION_ID_MISMATCH")
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise R01Error("SQLITE_SCHEMA_VERSION_MISMATCH")
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise R01Error("SQLITE_INTEGRITY_FAILED")
            meta = db.execute("SELECT value FROM metadata WHERE key='report'").fetchone()
            if meta is None:
                raise R01Error("SQLITE_METADATA_MISSING")
            report = decode(meta[0])
            if (report.get("source_archive_sha256") != bank["source_archive_sha256"]
                    or report.get("result_sha256") != bank["result_sha256"]):
                raise R01Error("SQLITE_BANK_SOURCE_BINDING_MISMATCH")
            member_rows = db.execute("SELECT count(*) FROM members").fetchone()[0]
            force_rows = db.execute("SELECT count(*) FROM force_states").fetchone()[0]
            if member_rows != len(bank["members"]) or force_rows != len(bank["force_states"]):
                raise R01Error("SQLITE_FORCE_DENOMINATOR_MISMATCH")
    except sqlite3.DatabaseError as exc:
        raise R01Error("SQLITE_QUERY_FAILED") from exc
    if file_sha(path) != original:
        raise R01Error("SQLITE_MUTATED")
    return {"sha256": original, "read_only": True, "integrity": "ok",
            "members": member_rows, "force_rows": force_rows,
            "projection_binding": "SOURCE_AND_RESULT_IDS_MATCH"}


def audit(*, bank_path: Path, config_path: Path, archive_path: Path | None = None,
          sqlite_path: Path | None = None) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    bank = read_bank(bank_path, config["bank_zip_sha256"])
    if bank.get("source_archive_sha256") != config["native_archive_sha256"]:
        raise R01Error("BANK_ARCHIVE_IDENTITY_MISMATCH")
    verified = False
    if archive_path:
        _check_file(archive_path)
        if file_sha(archive_path) != config["native_archive_sha256"]:
            raise R01Error("NATIVE_SOURCE_ARCHIVE_SHA_MISMATCH")
        verified = True
    index, counts = force_inventory(bank, expected_columns=config["expected_columns"])
    replay = replay_recorded_static(bank, index)
    result = {
        "schema": "tbdy.next.r01-archived-source-acceptance.v1",
        "archive_run_id": bank.get("run_id"),
        "source_archive_sha256": bank["source_archive_sha256"],
        "source_archive_file_reverified": verified,
        "bank_zip_sha256": config["bank_zip_sha256"],
        "native_source_census": counts,
        "static_replay": replay,
        "analysis_generation_proven": False,
        "all_building_columns_proven": False,
        "newer_capture_filled_from_old_archive": False,
        "design_demand_authority": "DENIED",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "scope": "HISTORICAL_OFFLINE_RUN_ONLY",
    }
    if sqlite_path:
        result["projection"] = read_projection(sqlite_path, bank)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--sqlite", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] /
                        "config/r01_archived_sources.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(bank_path=args.bank, config_path=args.manifest,
                       archive_path=args.source_archive, sqlite_path=args.sqlite)
        rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise R01Error("OUTPUT_EXISTS")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered)
        return 0
    except (R01Error, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"r01_status": "REJECTED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
