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
from .column_stability import build_column_stability
from .column_pmm import build_column_cages, build_column_pmm, cage_rows
from .column_transverse import build_column_transverse, build_column_shear, transverse_rows
from .column_joints import build_column_joints, joint_tie_rows, joint_summaries, joint_tie_summaries
from .column_kinematics import build_column_kinematics, kinematic_summaries
from .column_sensitivity import build_column_sensitivity, sensitivity_summaries
from .column_overview import build_column_overview
from .column_pmm_quality import build_column_pmm_quality
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
        prechecks = build_column_prechecks(bank, chain)
        cages = build_column_cages(bank, chain, prechecks, archive)
        transverse = build_column_transverse(chain, cages, archive)
        joints = build_column_joints(bank, chain, cages, transverse, archive)
        stability = build_column_stability(bank, chain, prechecks, archive)
        kinematics = build_column_kinematics(bank, chain, joints, archive)
        return {"demand_chain": chain, "column_prechecks": prechecks,
            "column_stability": stability,
            "column_cages": cages, "column_transverse": transverse,
            "column_joints": joints,
            "column_kinematics": kinematics,
            "column_sensitivity": build_column_sensitivity(chain, stability, kinematics)}
    finally:
        archive.close()


@lru_cache(maxsize=2)
def _pmm(source_path, database_path, source_sha, database_sha, bank_result_sha):
    derived = _derive(source_path,database_path,source_sha,database_sha,bank_result_sha)
    return build_column_pmm(derived["demand_chain"],derived["column_cages"],derived["column_stability"])


@lru_cache(maxsize=2)
def _shear(source_path, database_path, source_sha, database_sha, bank_result_sha):
    derived = _derive(source_path,database_path,source_sha,database_sha,bank_result_sha)
    return build_column_shear(derived["demand_chain"],derived["column_cages"],derived["column_transverse"])


@lru_cache(maxsize=4)
def _pmm_quality(source_path, database_path, source_sha, database_sha, bank_result_sha, member_id, output_case):
    key=(source_path,database_path,source_sha,database_sha,bank_result_sha)
    derived=_derive(*key)
    return build_column_pmm_quality(derived["demand_chain"],derived["column_cages"],_pmm(*key),
        member_id=member_id,output_case=output_case)


def demand_view(database, report, *, member_id=None, output_case=None, offset=0, limit=200,
                view="native", full=False):
    """Called only after store.verified_database has verified this exact run."""
    database = database.resolve()
    cache_key = (str(database.parent / "input.source"), str(database),
        report["source_archive_sha256"], report["database_sha256"], report["result_sha256"])
    derived = _derive(*cache_key)
    # Numerical capacity is requested explicitly; ordinary source navigation
    # remains fast. Full export includes every candidate x every static state.
    pmm = _pmm(*cache_key) if full or view in ("pmm", "overview", "pmm-quality") else None
    # PMM/report includes the related shear summary. Shear navigation itself
    # never invokes the more expensive PMM solver.
    shear = _shear(*cache_key) if full or view in ("pmm", "shear", "overview", "pmm-quality") else None
    quality = _pmm_quality(*cache_key,None if full else member_id,None if full else output_case) if full or view == "pmm-quality" else None
    chain, prechecks = derived["demand_chain"], derived["column_prechecks"]
    overview = build_column_overview(chain, derived["column_cages"], pmm, shear, derived["column_sensitivity"],
        member_id=None if full or view in ("pmm", "pmm-quality") else member_id,
        output_case=None if full or view in ("pmm", "pmm-quality") else output_case) if pmm is not None else None
    if full:
        return deepcopy({**derived,"column_pmm":pmm,"column_shear":shear,"column_overview":overview,"column_pmm_quality":quality})
    summary = {k: v for k, v in chain.items() if k not in ("candidates", "design_summary")}
    summary["design_summary"] = {k: v for k, v in chain["design_summary"].items() if k != "rows"}
    precheck_summary = {k: v for k, v in prechecks.items() if k not in ("critical_selection", "reinforcement_bounds")}
    precheck_summary["critical_selection"] = {k: v for k, v in prechecks["critical_selection"].items() if k != "rows"}
    precheck_summary["reinforcement_bounds"] = {k: v for k, v in prechecks["reinforcement_bounds"].items() if k != "source_comparisons"}
    result = {"demand_chain": deepcopy(summary), "column_prechecks": deepcopy(precheck_summary)}
    stability = derived["column_stability"]
    result["column_stability"] = deepcopy({k: v for k, v in stability.items() if k != "eccentricity"})
    result["column_stability"]["eccentricity"] = deepcopy({k: v for k, v in stability["eccentricity"].items() if k != "rows"})
    cages = derived["column_cages"]
    result["column_cages"] = deepcopy(cages)
    transverse = derived["column_transverse"]
    result["column_transverse"] = deepcopy(transverse)
    joints = derived["column_joints"]
    result["column_joints"] = deepcopy({k:v for k,v in joints.items() if k not in ("rows","graph")})
    result["column_joints"]["graph"] = deepcopy({k:v for k,v in joints["graph"].items() if k not in ("frames","points","nodes")})
    kinematics = derived["column_kinematics"]
    result["column_kinematics"] = deepcopy({k:v for k,v in kinematics.items() if k != "rows"})
    sensitivity = derived["column_sensitivity"]
    result["column_sensitivity"] = deepcopy({k:v for k,v in sensitivity.items() if k not in ("rows", "axes", "axial_profiles")})
    if view in ("pmm", "pmm-quality"):
        result["column_joints"]["end_summaries"] = joint_summaries(joints)
        result["column_joints"]["tie_summaries"] = joint_tie_summaries(joints)
        result["column_kinematics"]["summaries"] = kinematic_summaries(kinematics)
        result["column_sensitivity"]["axes"] = deepcopy(sensitivity["axes"])
        result["column_sensitivity"]["summaries"] = sensitivity_summaries(sensitivity)
        result["column_sensitivity"]["axial_profiles"] = deepcopy(sensitivity["axial_profiles"])
    if pmm is not None:
        result["column_pmm"] = deepcopy({k:v for k,v in pmm.items() if k != "rows"})
    if shear is not None:
        result["column_shear"] = deepcopy({k:v for k,v in shear.items() if k != "rows"})
    if overview is not None:
        result["column_overview"] = deepcopy({k:v for k,v in overview.items() if k != "rows" or view in ("pmm", "pmm-quality")})
    if quality is not None:
        # All critical ties (including failures) support the complete HTML report.
        # The UI table is paginated separately; ordinary views never compute this.
        result["column_pmm_quality"] = deepcopy(quality)
    if view == "native":
        return result
    if view == "overview":
        rows = overview["rows"]
    elif view == "pmm-quality":
        rows = quality["rows"]
    elif view == "critical":
        selection = critical_selection(chain, prechecks["population"], member_id=member_id, output_case=output_case)
        rows = selection["rows"]
        result["critical_scope"] = deepcopy({k: v for k, v in selection.items() if k != "rows"})
    elif view == "reinforcement":
        rows = [r for r in prechecks["reinforcement_bounds"]["rows"] if member_id is None or r["member_id"] == member_id]
    elif view == "stiffness":
        rows = [r for r in stability["sections"] if member_id is None or r["member_id"] == member_id]
    elif view == "cages":
        rows = cage_rows(cages,member_id)
    elif view == "transverse":
        rows = transverse_rows(transverse,member_id)
    elif view == "joints":
        rows = [r for r in joints["rows"] if member_id is None or r["member_id"] == member_id]
    elif view == "joint-ties":
        rows = joint_tie_rows(joints,member_id)
    elif view in ("end-forces", "kinematics"):
        rows = [r for r in kinematics["rows"] if
            (member_id is None or r["member_id"] == member_id) and
            (output_case is None or r["output_case"] == output_case)]
    elif view == "stiffness-scenarios":
        rows = [r for r in sensitivity["axes"] if member_id is None or r["member_id"] == member_id]
    elif view == "length-sensitivity":
        rows = [r for r in sensitivity["rows"] if
            (member_id is None or r["member_id"] == member_id) and
            (output_case is None or r["native_key"]["LoadCase"] == output_case)]
        result["column_sensitivity"]["axial_profiles"] = deepcopy([r for r in sensitivity["axial_profiles"] if
            (member_id is None or r["member_id"] == member_id) and
            (output_case is None or r["output_case"] == output_case)])
    elif view == "shear":
        rows = [r for r in shear["rows"] if (member_id is None or r["member_id"] == member_id)
            and (output_case is None or r["native_key"]["LoadCase"] == output_case)]
    elif view == "pmm":
        rows = [r for r in pmm["rows"] if (member_id is None or r["member_id"] == member_id)
            and (output_case is None or r["native_key"]["LoadCase"] == output_case)]
    elif view == "eccentricity":
        rows = [r for r in stability["eccentricity"]["rows"] if
            (member_id is None or r["member_id"] == member_id) and
            (output_case is None or r["native_key"]["LoadCase"] == output_case)]
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
