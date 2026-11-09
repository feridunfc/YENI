"""Read-only CE-02 projection; reuse the existing sealed ZIP and SQLite.

Only a small, bounded process-local cache is used. Its key binds both source
hashes; callers verify those files before every access, including cache hits.
"""
from contextlib import closing
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import sqlite3

from .demand_chain import build_demand_chain
from .column_prechecks import build_column_prechecks, critical_selection
from .native_archive import BankError, NativeArchive, decode


@lru_cache(maxsize=2)
def _derive(source_path, database_path, source_sha, database_sha, bank_result_sha):
    source, database = Path(source_path), Path(database_path)
    if sha256(database.read_bytes()).hexdigest() != database_sha:
        raise BankError("DEMAND_DATABASE_CHANGED")
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        bank = decode(db.execute("SELECT value FROM metadata WHERE key='report'").fetchone()[0])
        if bank["result_sha256"] != bank_result_sha:
            raise BankError("DEMAND_BANK_BINDING_MISMATCH")
        bank["force_states"] = [decode(r[0]) for r in db.execute("SELECT data_json FROM force_states ORDER BY rowid")]
        bank["static_replay"]["items"] = [decode(r[0]) for r in db.execute("SELECT data_json FROM combination_replay ORDER BY rowid")]
    archive = NativeArchive(source.read_bytes())
    try:
        if archive.sha256 != source_sha:
            raise BankError("DEMAND_SOURCE_CHANGED")
        chain = build_demand_chain(bank, archive)
        return {"demand_chain": chain, "column_prechecks": build_column_prechecks(bank, chain)}
    finally:
        archive.close()


def demand_view(database, report, *, member_id=None, output_case=None, offset=0, limit=200,
                view="native", full=False):
    """Called only after store.verified_database has verified this exact run."""
    database = database.resolve()
    derived = _derive(str(database.parent / "input.source"), str(database),
        report["source_archive_sha256"], report["database_sha256"], report["result_sha256"])
    chain, prechecks = derived["demand_chain"], derived["column_prechecks"]
    if full:
        return deepcopy(derived)
    summary = {k: v for k, v in chain.items() if k not in ("candidates", "design_summary")}
    summary["design_summary"] = {k: v for k, v in chain["design_summary"].items() if k != "rows"}
    precheck_summary = {k: v for k, v in prechecks.items() if k not in ("critical_selection", "reinforcement_bounds")}
    precheck_summary["critical_selection"] = {k: v for k, v in prechecks["critical_selection"].items() if k != "rows"}
    precheck_summary["reinforcement_bounds"] = {k: v for k, v in prechecks["reinforcement_bounds"].items() if k != "source_comparisons"}
    result = {"demand_chain": deepcopy(summary), "column_prechecks": deepcopy(precheck_summary)}
    if view == "native":
        return result
    if view == "critical":
        selection = critical_selection(chain, prechecks["population"], member_id=member_id, output_case=output_case)
        rows = selection["rows"]
        result["critical_scope"] = deepcopy({k: v for k, v in selection.items() if k != "rows"})
    elif view == "reinforcement":
        rows = [r for r in prechecks["reinforcement_bounds"]["rows"] if member_id is None or r["member_id"] == member_id]
    elif view == "static":
        rows = [r for r in chain["candidates"] if
            (member_id is None or r["native_key"]["Obj"] == member_id) and
            (output_case is None or r["native_key"]["LoadCase"] == output_case)]
    else:
        rows = [r for r in chain["design_summary"]["rows"] if
            (member_id is None or r["member_id"] == member_id) and
            (output_case is None or any(ref["combination"] == output_case for ref in r["references"]))]
    result["demand_page"] = {"view": view, "member_id": member_id, "output_case": output_case,
        "offset": offset, "limit": limit, "total": len(rows), "rows": deepcopy(rows[offset:offset + limit])}
    return result
