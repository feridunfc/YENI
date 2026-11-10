"""One derivation for bounded UI/CLI/HTML and separate complete forensic ZIP."""
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from .native_archive import BankError, canonical
from .source_bank import COMPONENTS
from .spectral_design import VIEW, DETAIL_VIEW
from .spectral_pmm import summarize_group
from ..verification.golden_gate import build_golden_gate, golden_gate_summary

DEFAULT_CAGE = "16Φ24"
REPLAY_KEYS = ("schema", "policy", "result_sha256", "source_run_id", "source_archive_sha256",
    "source_bank_result_sha256", "eligible_combination_count", "expected_pair_count",
    "expected_native_row_count", "matched_rows", "mismatched_rows", "unresolved_pair_count",
    "scalar_comparisons", "over_tolerance_components", "maximum_absolute_difference_by_unit",
    "source_coverage_status", "replay_status", "members_without_station_population",
    "absolute_tolerance_native", "relative_tolerance")


def spectral_design_projection(result, *, view=VIEW, member_id=None, output_case=None,
                               column_label=None, offset=0, limit=200):
    label = column_label or DEFAULT_CAGE
    if (view not in (VIEW, DETAIL_VIEW) or label not in ("16Φ24", "16Φ28", "16Φ32")
            or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500):
        raise BankError("SPECTRAL_DESIGN_PAGE_INVALID")
    population = result.population
    filtered = [r for r in result.rows if r.cage_label == label
        and (member_id is None or r.candidate.envelope.cut.member_id == member_id)
        and (output_case is None or r.candidate.envelope.combination == output_case)]
    if view == DETAIL_VIEW:
        total = len(filtered)
        rows = []
        for row in filtered[offset:offset+limit]:
            item = row.as_dict(detailed=True)
            item["numerical_evidence"] = result.evidence_record(row.evidence_id) if row.evidence_id else None
            rows.append(item)
    else:
        grouped = defaultdict(list)
        for row in filtered:
            grouped[row.candidate.envelope.cut.member_id].append(row)
        rows = []
        for member in population.summary["members"]:
            if member_id is not None and member["member_id"] != member_id:
                continue
            item = {**member, "reinforcement": label,
                **summarize_group(grouped[member["member_id"]],
                    source_complete=population.summary["construction_complete_for_recorded_scope"])}
            rows.append(item)
        total = len(rows); rows = rows[offset:offset+limit]
    replay = population.replay
    differences = {c: {"component": c, "unit": "kN" if c in ("P", "V2", "V3") else "kNm",
        "comparisons": 0, "mismatches": 0, "maximum_absolute_difference": 0.0} for c in COMPONENTS}
    for pair in replay["rows"]:
        for comparison in pair["comparisons"]:
            d = differences[comparison["component"]]
            d["comparisons"] += 1; d["mismatches"] += not comparison["match"]
            d["maximum_absolute_difference"] = max(d["maximum_absolute_difference"], comparison["absolute_difference"])
    summary = {k: v for k, v in population.summary.items() if k not in ("members", "static_load_definition_facts")}
    summary.update(member_id_filter=member_id, output_case_filter=output_case, reinforcement_filter=label,
        filtered_assessment_count=len(filtered), filtered_status_counts=dict(Counter(r.status for r in filtered)))
    return deepcopy({"column_spectral_design": summary,
        "golden_regression_gate": golden_gate_summary(),
        "spectral_replay": {**{k: replay[k] for k in REPLAY_KEYS},
            "component_differences": list(differences.values()), "statistics_scope": "WHOLE_RECORDED_ARCHIVE"},
        "spectral_pmm": {k: v for k, v in result.summary.items() if k not in ("members", "proposal_policy")},
        "demand_page": {"view": view, "member_id": member_id, "output_case": output_case,
            "column_label": label, "offset": offset, "limit": limit, "total": total, "rows": rows,
            "scope": "SELECTED_FILTERED_PAGE", "raw_population_included": False}})


def write_spectral_forensic(result, target):
    """Stream all records, without filters or a giant intermediate JSON string.

    ZIP entries have deterministic timestamps. The manifest records the SHA
    of each uncompressed entry and its row count. References join by full IDs.
    This is a derived export, never a native ETABS archive or accepted design.
    """
    ledger = {}
    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        def write(name, records, *, lines=True):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)); info.compress_type = ZIP_DEFLATED
            hasher, size, count = sha256(), 0, 0
            with archive.open(info, "w", force_zip64=True) as stream:
                for record in records:
                    data = canonical(record); stream.write(data); hasher.update(data)
                    size += len(data); count += 1
            ledger[name] = {"sha256": hasher.hexdigest(), "bytes": size,
                "record_count": count if lines else None, "format": "NDJSON" if lines else "JSON"}
        population = result.population
        write("population.json", [population.summary], lines=False)
        write("replay-summary.json", [{k: v for k, v in population.replay.items() if k != "rows"}], lines=False)
        write("pmm-summary.json", [result.summary], lines=False)
        write("cages.json", [result.cages], lines=False)
        write("sections.json", [result.sections], lines=False)
        golden = build_golden_gate()
        write("golden-regression.json", [golden], lines=False)
        write("physical-static-states.ndjson", (r.as_dict() for r in population.static_states))
        write("component-replay.ndjson", population.replay["rows"])
        write("spectral-envelopes.ndjson", (r.as_dict() for r in population.envelopes))
        write("design-candidates.ndjson", (r.as_dict() for r in population.candidates))
        write("blocked-pairs.ndjson", population.blocked_pairs)
        write("pmm-evaluations.ndjson", (r.as_dict() for r in result.rows))
        write("numerical-evidence.ndjson", ({"evidence_id": key, **result.evidence_record(key)} for key in sorted(result.evidence)))
        manifest = {"schema": "tbdy.next.spectral-forensic-export.v1", "scope": "FULL_RECORDED_VS26_POPULATION_NO_FILTERS",
            "source_run_id": population.summary["source_run_id"],
            "source_archive_sha256": population.summary["source_archive_sha256"],
            "source_bank_result_sha256": population.summary["source_bank_result_sha256"],
            "replay_result_sha256": population.replay["result_sha256"],
            "population_result_sha256": population.summary["result_sha256"], "pmm_result_sha256": result.summary["result_sha256"],
            "golden_regression_result_sha256": golden["result_sha256"],
            "units": {"candidate_forces": "kN_kNm", "numeric_solver": "N_Nmm_MPa", "native_stations": "m"},
            "normative_qualification": "NOT_PROVEN", "engineering_release": "NOT_READY",
            "native_archive_replaced": False, "files": deepcopy(ledger)}
        write("manifest.json", [manifest], lines=False)
    return manifest
