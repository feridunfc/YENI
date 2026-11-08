"""VS05 D4 — read-only ETABS source authority analysis, never regulatory PASS.

Pure decoder over an already receipt-verified VS04 report. The caller MUST use
build_complete_report on the ORIGINAL receipt directory, not a user-edited
exported report. This module cannot independently attest model/analysis epoch,
physical-model completeness, approved ModelProfile or approved ComboBook.

Result semantics are deliberately asymmetric: observations may be established;
structural-design authority is never inferred from a SHA, case name, ETABS
locked state, or successful arithmetic alone.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

REPORT_SCHEMA = "tbdy.next.complete.engineering.report.v1"
D4_SCHEMA = "tbdy.next.vs05.d4.source-authority-review.v1"
SUMMARY = "Load Case Definitions - Summary"
SPECTRUM = "Load Case Definitions - Response Spectrum"
COMBOS = "Load Combination Definitions"
OPERATOR_MAP = {
    "Linear Add": "SUM", "Envelope": "ENVELOPE",
    "SRSS": "SRSS", "Absolute Add": "ABSOLUTE_ADD",
    "Range Add": "RANGE_ADD",
}

BASE_REQUIRED = (
    "same_model_analysis_generation",
    "upper_building_mass_scope",
    "dd2_spectrum_and_reduced_sar_at_directional_tp",
    "directional_tp_bound_and_applicability",
    "complete_a1_b2_b3_irregularity_inventory",
    "basement_upper_lower_boundary",
    "pre_beta_modal_base_shear_not_scaled",
    "response_spectrum_case_and_combination_lineage",
    "applied_beta_scale_factor_source",
    "independent_source_authority",
)
DRIFT_REQUIRED = (
    "same_model_analysis_generation",
    "physical_story_and_end_node_identity",
    "complete_col_perde_member_census",
    "reduced_displacements_without_eq4_19_minimum",
    "reduced_displacements_without_tp_period_cap",
    "matched_dd2_dd3_at_same_directional_tp",
    "r_over_i_and_material_system",
    "wall_connection_and_capacity_applicability",
    "spectrum_scale_and_case_lineage",
    "independent_source_authority",
)


class SourceContractError(ValueError):
    """Malformed, contradictory or missing source data; do not silently infer."""


def _canonical(obj: Mapping[str, Any]) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(obj: Mapping[str, Any]) -> str:
    return sha256(_canonical(obj)).hexdigest()


def _text(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        raise SourceContractError(label + ":INVALID_TEXT")
    return raw


def _finite_decimal(raw: Any, label: str) -> Decimal:
    if not isinstance(raw, str) or raw != raw.strip() or not raw:
        raise SourceContractError(label + ":NOT_DECIMAL_TEXT")
    try:
        val = Decimal(raw)
    except InvalidOperation as exc:
        raise SourceContractError(label + ":INVALID_DECIMAL") from exc
    if not val.is_finite():
        raise SourceContractError(label + ":NONFINITE")
    return val


def _source_table(tables: Mapping[str, Any], key: str,
                  mandatory: set[str]) -> list[dict[str, str]]:
    rowset = tables.get(key)
    if not isinstance(rowset, Mapping) or rowset.get("status") != "CAPTURED":
        raise SourceContractError(key + ":NOT_CAPTURED")
    fields, rows, info = (rowset.get("fields"), rowset.get("rows"),
                          rowset.get("field_metadata"))
    if (not isinstance(fields, list) or not fields or
            len(fields) != len(set(fields)) or not mandatory.issubset(fields) or
            not isinstance(rows, list) or not rows or
            type(rowset.get("row_count")) is not int or
            rowset["row_count"] != len(rows) or
            not isinstance(info, Mapping) or info.get("status") != "OK" or
            not isinstance(info.get("field_keys"), list) or
            not set(fields).issubset(info["field_keys"]) or
            not isinstance(info.get("units_by_field"), Mapping)):
        raise SourceContractError(key + ":FIELDS_ROWS_OR_METADATA_INVALID")
    if any(not isinstance(r, dict) or set(r) != set(fields) or
           any(not isinstance(v, str) for v in r.values()) for r in rows):
        raise SourceContractError(key + ":ROW_SHAPE_INVALID")
    return rows


def _case_source(tables: Mapping[str, Any]) -> dict[str, Any]:
    rows = _source_table(tables, SUMMARY, {"Name", "Type", "GUID"})
    out = {}
    guids = set()
    for row in rows:
        name = _text(row["Name"], "CASE_NAME")
        guid = _text(row["GUID"], "CASE_GUID")
        if name in out or guid == "None" or guid in guids:
            raise SourceContractError("CASE_ID_OR_GUID_NOT_UNIQUE")
        guids.add(guid)
        out[name] = {"type": row["Type"], "guid": guid}
    rs = _source_table(tables, SPECTRUM,
                       {"Name", "LoadName", "ModalCase", "Function"})
    direction_roles = {}
    for row in rs:
        name = _text(row["Name"], "RESPONSE_SPECTRUM_CASE")
        if name in direction_roles:
            raise SourceContractError("DUPLICATE_RESPONSE_SPECTRUM_CASE")
        if name in out:
            direction_roles[name] = {
                "case_in_summary": True,
                "summary_type": out[name]["type"],
                "acceleration_axis": row["LoadName"],
                "modal_case": row["ModalCase"],
                "function": row["Function"],
            }
        else:
            raise SourceContractError("RS_CASE_MISSING_FROM_CASE_SUMMARY:" + name)
    expected = {"RSX": "U1", "RSY": "U2"}
    qualified = (set(direction_roles) == set(expected)
                 and all(direction_roles[name]["acceleration_axis"] == axis
                         and direction_roles[name]["summary_type"] == "Response Spectrum"
                         and direction_roles[name]["modal_case"] in out
                         and direction_roles[name]["function"] not in ("", "None")
                         for name, axis in expected.items()))
    return {
        "case_count": len(out),
        "cases": out,
        "spectrum_case_roles": direction_roles,
        "x_y_case_shape_consistent": qualified,
        "regulatory_role_approved": False,
        "analysis_generation_proven": False,
    }


def _combo_source(tables: Mapping[str, Any], cases: Mapping[str, Any]) -> dict[str, Any]:
    rows = _source_table(tables, COMBOS,
                         {"Name", "Type", "LoadName", "SF", "GUID"})
    # ETABS prints Type/GUID on a combination's first row and 'None' on
    # continuation rows. Preserve this distinction; never forward-fill across
    # a different Name, invent an operator or infer design roles by prefixes.
    groups: dict[str, dict[str, Any]] = {}
    previous = None
    warnings = []
    for index, row in enumerate(rows):
        name = _text(row["Name"], "COMBO_NAME")
        ref = _text(row["LoadName"], "LOAD_NAME")
        factor = _finite_decimal(row["SF"], "COMBO_FACTOR")
        if name not in groups:
            if row["Type"] in ("", "None"):
                raise SourceContractError("FIRST_COMBO_ROW_HAS_NO_OPERATOR:" + name)
            if name in cases:
                raise SourceContractError("CASE_AND_COMBO_NAME_COLLISION:" + name)
            groups[name] = {
                "operator_etabs": row["Type"],
                "operator_candidate": OPERATOR_MAP.get(row["Type"]),
                "guid": row["GUID"],
                "rows": [],
            }
        else:
            if name != previous:
                warnings.append("NONCONTIGUOUS_COMBO_DEFINITION:" + name)
            if row["Type"] not in ("None", "", groups[name]["operator_etabs"]):
                warnings.append("INCONSISTENT_REPEATED_OPERATOR:" + name)
        if index and name == previous and row["Type"] not in (
                "", "None", groups[name]["operator_etabs"]):
            warnings.append("CONTINUATION_OPERATOR_CONTRADICTION:" + name)
        groups[name]["rows"].append({"ref": ref, "factor": str(factor),
                                      "raw_row_index": index})
        previous = name
    unknown_refs = []
    graph = {}
    for name, group in groups.items():
        child_combos = []
        for row in group["rows"]:
            if row["ref"] in groups:
                row["ref_type"] = "COMBO"
                child_combos.append(row["ref"])
            elif row["ref"] in cases:
                row["ref_type"] = "CASE"
            else:
                row["ref_type"] = "UNKNOWN"
                unknown_refs.append({"combo": name, "ref": row["ref"],
                                     "row_index": row["raw_row_index"]})
        graph[name] = sorted(set(child_combos))
    cycles = []
    visiting = set()
    visited = set()
    def walk(n: str):
        if n in visiting:
            cycles.append(n)
            return
        if n in visited:
            return
        visiting.add(n)
        for child in graph[n]:
            walk(child)
        visiting.remove(n)
        visited.add(n)
    for name in sorted(graph):
        walk(name)
    if cycles:
        warnings.append("NESTED_COMBO_CYCLE_OBSERVED")
    types = dict(sorted(Counter(g["operator_etabs"] for g in groups.values()).items()))
    unsupported = sorted(n for n, g in groups.items()
                         if g["operator_candidate"] is None)
    # A nominal SUM can contain a nested ENVELOPE or a response-spectrum
    # case several levels down. Evaluate transitive risk, not just direct
    # children, and reject cyclic/unknown references from being concurrent.
    def risk_ancestry(name: str, stack: frozenset[str]):
        if name in stack:
            return True, set(), {"CYCLIC_NESTED_COMBO"}
        group = groups[name]
        risky = group["operator_candidate"] != "SUM"
        spectra: set[str] = set()
        reasons: set[str] = set()
        if risky:
            reasons.add("NON_SUM_OPERATOR_OR_UNKNOWN_OPERATOR")
        for row in group["rows"]:
            if row["ref_type"] == "UNKNOWN":
                risky = True
                reasons.add("UNKNOWN_SOURCE_REFERENCE")
            elif row["ref_type"] == "CASE" and (
                cases[row["ref"]]["type"] == "Response Spectrum"):
                risky = True
                spectra.add(row["ref"])
                reasons.add("RESPONSE_SPECTRUM_MODAL_ENVELOPE_CASE")
            elif row["ref_type"] == "COMBO":
                child_risky, child_spectra, child_reasons = risk_ancestry(
                    row["ref"], stack | {name})
                risky |= child_risky
                spectra.update(child_spectra)
                reasons.update(child_reasons)
        return risky, spectra, reasons

    risk = []
    for name, group in groups.items():
        risky, spectra, reasons = risk_ancestry(name, frozenset())
        if risky:
            risk.append({"combo": name,
                         "risk": "NONCONCURRENT_SOURCE_VECTOR_NOT_AUTHORIZED",
                         "spectrum_source_cases": sorted(spectra),
                         "reason_codes": sorted(reasons),
                         "operator": group["operator_etabs"]})
    summary = {
        "raw_row_count": len(rows),
        "parsed_combination_count": len(groups),
        "operator_counts": types,
        "unknown_reference_count": len(unknown_refs),
        "unknown_references": unknown_refs[:50],
        "unknown_reference_count_truncated": max(0, len(unknown_refs)-50),
        "unsupported_operator_combinations": unsupported,
        "cycle_candidates": sorted(set(cycles)),
        "source_warnings": sorted(set(warnings)),
        "nonconcurrent_vector_risk_count": len(risk),
        "nonconcurrent_vector_risks": sorted(risk, key=lambda x: x["combo"]),
        "typed_graph_source_hash": _digest(groups),
        "case_step_station_concurrence_proven": False,
        "complete_combo_book_approved": False,
        "design_demand_vector_authorized": False,
        "candidate_operator_reference_shape_observed": not (
            unknown_refs or unsupported or cycles or warnings),
    }
    return summary


def _seismic_mass(report: Mapping[str, Any]) -> dict[str, Any]:
    pipeline = report.get("vs04_pipeline")
    stages = (pipeline or {}).get("stages", {}) if isinstance(pipeline, Mapping) else {}
    stage = stages.get("vs04_f", {}) if isinstance(stages, Mapping) else {}
    components = stage.get("components", []) if isinstance(stage, Mapping) else []
    match = [c for c in components if isinstance(c, Mapping) and
             c.get("component") == "SEISMIC_MASS_RECONCILIATION"]
    base = {"mass_reconciliation_source_observed": False,
            "seismic_mass_scope_approved": False,
            "mass_source_generation_proven": False,
            "candidate_mass_ton": None,
            "reason_codes": ["MASS_SOURCE_NOT_INDEPENDENTLY_AUTHORIZED"]}
    if len(match) != 1 or match[0].get("status") != "SOURCE_CONTRACT_OBSERVED_UNAPPROVED":
        base["reason_codes"].append("VS04F_MASS_SOURCE_COMPONENT_NOT_OBSERVED")
        return base
    facts = match[0].get("source_facts")
    if not isinstance(facts, Mapping):
        base["reason_codes"].append("MASS_SOURCE_FACTS_MISSING")
        return base
    compares = facts.get("comparisons")
    if (not isinstance(compares, Mapping) or len(compares) < 4 or
            not all(compares.get(k) is True for k in (
                "joint_to_group_UX", "joint_to_group_UY",
                "story_to_group_UX", "story_to_group_UY"))):
        base["reason_codes"].append("MASS_SOURCE_GROUP_STORY_JOINT_MISMATCH")
        return base
    sums = facts.get("group_sums")
    if not isinstance(sums, Mapping):
        base["reason_codes"].append("GROUP_MASS_FACTS_UNAVAILABLE")
        return base
    ux = _finite_decimal(sums.get("UX_ton"), "UX_ton")
    uy = _finite_decimal(sums.get("UY_ton"), "UY_ton")
    if ux <= 0 or ux != uy:
        base["reason_codes"].append("DIRECTIONAL_MASS_SCOPE_MISMATCH")
        return base
    return {**base, "mass_reconciliation_source_observed": True,
            "candidate_mass_ton": str(ux),
            "source_mass_id": facts.get("mass_source"),
            "reason_codes": ["MASS_MT_UPPER_BUILDING_BASEMENT_SCOPE_UNAPPROVED",
                             "SEMI_RIGID_DIAPHRAGM_MASS_ASSIGNMENT_NOT_PROVEN"]}


def audit_d4_source_authority(
    report: Mapping[str, Any], d3_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic audit over a *verified-by-caller* archived run report.

    Direct dict calls are only source-level diagnostics; they never count as
    independent receipt/model-generation proof. The CLI guards the trust
    boundary by invoking build_complete_report on the original receipt root.
    """
    if (not isinstance(report, Mapping) or report.get("schema") != REPORT_SCHEMA
            or report.get("source_mode") != "LIVE_ETABS"
            or report.get("formal_compliance") != "NOT_PROVEN"
            or report.get("engineering_release") != "NOT_READY"):
        raise SourceContractError("REPORT_SCOPE_NOT_LIVE_OR_NOT_FAIL_CLOSED")
    run_id = _text(report.get("run_id"), "RUN_ID")
    source = report.get("source_snapshot")
    if not isinstance(source, Mapping):
        raise SourceContractError("SOURCE_SNAPSHOT_MISSING")
    probe = source.get("vs04_basis_probe")
    if (not isinstance(probe, Mapping) or
            probe.get("schema") != "tbdy.next.vs04e.basis-source-probe.v1" or
            probe.get("read_only_invariant_proven") is not True or
            probe.get("units_before") != probe.get("units_after") or
            probe.get("units_before") != 6):
        raise SourceContractError("READ_ONLY_BASIS_CAPTURE_CONTRACT_INVALID")
    tables = probe.get("table_reads")
    if not isinstance(tables, Mapping):
        raise SourceContractError("BASIS_TABLE_REGISTRY_MISSING")
    # Source-level claims of a *proven* generation cannot be accepted from
    # raw rows. Only an independent, signed/qualified analysis generation
    # can eventually satisfy this gate; it is not available in D4.
    src_analysis = source.get("analysis_sources")
    if not isinstance(src_analysis, Mapping) or src_analysis.get(
            "analysis_generation_proven") is not False:
        raise SourceContractError("UNTRUSTED_ANALYSIS_GENERATION_AUTHORITY_CLAIM")
    metadata = report.get("capture_metadata") or source.get("capture_metadata") or {}
    if not isinstance(metadata, Mapping) or metadata.get(
            "analysis_generation_proven") is not False:
        raise SourceContractError("CAPTURE_ANALYSIS_GENERATION_MUST_BE_UNPROVEN")
    case = _case_source(tables)
    combos = _combo_source(tables, case["cases"])
    mass = _seismic_mass(report)
    same_session = metadata.get("vs04_same_session_capture") is True
    restored = metadata.get("display_selection_restored") is True
    # A shared read-only session is not an ETABS analysis-generation ID.
    model_epoch_proven = False
    if d3_result is not None:
        if (not isinstance(d3_result, Mapping) or
                d3_result.get("run_id") != run_id or
                d3_result.get("model_analysis_generation_proven") is not False or
                d3_result.get("formal_compliance") != "NOT_PROVEN"):
            raise SourceContractError("D3_SOURCE_LINEAGE_MISMATCH")
        snapshot_hash = d3_result.get("source_snapshot_sha256_canonical")
        if snapshot_hash != _digest(source):
            raise SourceContractError("D3_SOURCE_HASH_MISMATCH")
        d3_fcr = d3_result.get("fcr") or {}
        if (d3_fcr.get("expected_count") != d3_fcr.get("reconciled_count")
                or d3_fcr.get("not_proven_count") != d3_fcr.get("expected_count")
                or d3_fcr.get("pass_count") != 0):
            raise SourceContractError("D3_FCR_DENOMINATOR_OR_STATUS_MISMATCH")
    else:
        snapshot_hash = _digest(source)
        d3_fcr = None
    incomplete = []
    if not same_session:
        incomplete.append("SAME_REQUEST_CAPTURE_NOT_PROVEN")
    if not restored:
        incomplete.append("ORIGINAL_DISPLAY_SELECTION_NOT_RESTORED")
    if not case["x_y_case_shape_consistent"]:
        incomplete.append("RSX_RSY_CASE_ROLE_LINKAGE_INCOMPLETE")
    if not combos["candidate_operator_reference_shape_observed"]:
        incomplete.append("COMBO_OPERATOR_REFERENCE_GRAPH_INCOMPLETE")
    if not mass["mass_reconciliation_source_observed"]:
        incomplete.append("SEISMIC_MASS_SOURCE_RECONCILIATION_INCOMPLETE")
    return {
        "schema": D4_SCHEMA,
        "run_id": run_id,
        "status": ("SOURCE_GATES_PARTIAL_NOT_REGULATORY_APPROVED" if incomplete
                   else "SOURCE_GATES_OBSERVED_NOT_REGULATORY_APPROVED"),
        "source_blocker_codes": incomplete,
        "source_snapshot_sha256_canonical": snapshot_hash,
        "source_capture": {
            "same_request_observed": same_session,
            "display_selection_restored": restored,
            "locked_model_is_analysis_generation_proof": False,
            "analysis_generation_proven": model_epoch_proven,
            "source_only": True,
            "reason_codes": ["NO_STABLE_ETABS_ANALYSIS_EPOCH_CERTIFICATE",
                             "SAME_SESSION_CAPTURE_IS_NOT_ANALYSIS_GENERATION_PROOF"],
        },
        "source_case_catalog": case,
        "source_combination_graph": combos,
        "source_mass_reconciliation": mass,
        "d3_fcr": ({"expected": d3_fcr["expected_count"],
                     "reconciled": d3_fcr["reconciled_count"],
                     "not_proven": d3_fcr["not_proven_count"]}
                    if d3_fcr is not None else None),
        "source_identity_authorized": False,
        "approved_model_profile": False,
        "approved_combo_book": False,
        "gamma_e_authorized": False,
        "a1_b2_b3_full_inventory_proven": False,
        "directional_tp_qualified": False,
        "dd2_dd3_spectra_qualified": False,
        "vtx_pre_beta_authorized": False,
        "normative_base_shear_missing_evidence": list(BASE_REQUIRED),
        "normative_story_drift_missing_evidence": list(DRIFT_REQUIRED),
        "normative_check_instances_promoted": 0,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "note": ("Observed tables/rows and internally consistent mass do not "
                 "authorize physical model, analysis generation or design. "
                 "Response spectrum envelope cannot be a signed concurrent "
                 "P/M2/M3 source tuple."),
    }
