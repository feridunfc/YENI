"""VS04 one-run source-to-check integration, still NOT normative design.

All VS04 E through J stages are evaluated from the archived same-session
ETABS table captures, not independent handoff files. No COM occurs here.
Output never promotes an engineering compliance PASS.
"""
from __future__ import annotations
from typing import Any, Mapping

from .analysis_numerics import evaluate_analysis_numerics
from .basis_probe import review_basis_probe
from .basis_linkage import review_basis_linkage
from .diaphragm_probe import review_diaphragm_modal_probe
from .diaphragm_linkage import review_vs04h_source
from .spectrum_reconstruction import review_spectrum_reconstruction
from .base_shear_screening import review_base_shear_screening

COMPONENTS = (
    ("vs04_e", "BASIS_PROBE", "Kaynak deprem esasları"),
    ("vs04_f", "BASIS_LINKAGE", "Kütle, vaka ve geometri bağları"),
    ("vs04_g", "DIAPHRAGM_PROBE", "Diyafram ve modal kaynak"),
    ("vs04_h", "DIAPHRAGM_LINKAGE", "Diyafram ve spektrum modları"),
    ("vs04_i", "SPECTRUM_RECONSTRUCTION", "26 nokta ve 200 mod"),
    ("vs04_j", "BASE_SHEAR_SCREENING", "Denklem 4.19 koşullu alt terimi"),
)


def _source_status(key: str, report: Mapping[str, Any]) -> str:
    """Do not label partial table inventory or conditional equations PASS."""
    if key == "vs04_e" and (
        report.get("status") == "SOURCE_CANDIDATES_OBSERVED_PENDING_REVIEW"
        and report.get("candidate_count") == report.get("observed_candidate_count")
        and report.get("candidate_count", 0) > 0
    ):
        return "SOURCE_OBSERVED_UNAPPROVED"
    if key == "vs04_f" and (
        report.get("observed_component_count") == report.get("expected_component_count") == 4
    ):
        return "SOURCE_OBSERVED_UNAPPROVED"
    if key == "vs04_g" and (
        report.get("source_success_count") == report.get("source_expected_count") == 5
    ):
        return "SOURCE_OBSERVED_UNAPPROVED"
    if key == "vs04_h" and (
        report.get("observed_source_component_count") == report.get("source_component_count") == 4
    ):
        return "SOURCE_OBSERVED_UNAPPROVED"
    if key == "vs04_i" and (
        report.get("status") == "SOURCE_NUMERICAL_RECONSTRUCTED_PENDING_ENGINEERING_REVIEW"
        and report.get("analytical_knot_consistency_count") == 26
        and report.get("reconstructed_modal_rows") == 200
        and report.get("unexplained_modal_rows") == 0
    ):
        return "SOURCE_OBSERVED_UNAPPROVED"
    if key == "vs04_j" and report.get("status") == "CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING":
        return "CONDITIONAL_ONLY_NOT_CODE_APPROVED"
    return "NOT_PROVEN"


def _legacy_single_run_source_pipeline(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compute all six E/F/G/H/I/J stages from one immutable source snapshot."""
    base = {
        "stage": "VS04_E_TO_J_SAME_RUN_SOURCE_PIPELINE",
        "engineering_release": "NOT_READY",
        "formal_compliance": "NOT_PROVEN",
        "regulatory_checks_executed": 0,
        "same_analysis_generation_proven": False,
        "full_equivalent_base_shear_proven": False,
        "effective_drift_proven": False,
        "source_only": True,
    }
    if not isinstance(payload, Mapping):
        return {**base, "status": "SOURCE_NOT_CAPTURED", "components": [],
                "reason_codes": ["LIVE_PAYLOAD_MISSING"]}
    sources = payload.get("analysis_sources")
    e = payload.get("vs04_basis_probe")
    g = payload.get("vs04_diaphragm_probe")
    if not all(isinstance(x, dict) for x in (sources, e, g)):
        return {**base, "status": "SOURCE_NOT_CAPTURED", "components": [],
                "reason_codes": ["SAME_SESSION_SOURCE_TRIPLET_REQUIRED"]}
    if sources.get("pipeline_stage_required") is not True:
        return {**base, "status": "SOURCE_REJECTED", "components": [],
                "reason_codes": ["PIPELINE_CAPTURE_CONTRACT_NOT_ENABLED"]}
    e_receipt = {
        "schema": "tbdy.next.vs04e.basis-probe-receipt.v1",
        "source": e,
        "review": review_basis_probe(e),
    }
    g_receipt = {
        "schema": "tbdy.next.vs04g.diaphragm-source-receipt.v1",
        "source": g,
        "review": review_diaphragm_modal_probe(g),
    }
    prior = {
        "schema": "tbdy.next.vs04.offline-source-replay.v1",
        "numeric_source_review": evaluate_analysis_numerics(sources),
    }
    try:
        stages = {
            "vs04_e": review_basis_probe(e),
            "vs04_f": review_basis_linkage(e_receipt),
            "vs04_g": review_diaphragm_modal_probe(g),
            "vs04_h": review_vs04h_source(g_receipt, prior_modal_replay=prior),
            "vs04_i": review_spectrum_reconstruction(e_receipt, g_receipt, prior),
            "vs04_j": review_base_shear_screening(e_receipt, g_receipt, prior),
        }
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return {**base, "status": "SOURCE_REJECTED", "components": [],
                "reason_codes": [type(exc).__name__ + ": " + str(exc)]}
    summaries = []
    for key, check_id, title in COMPONENTS:
        value = stages[key]
        summaries.append({
            "check_id": check_id,
            "title": title,
            "stage_key": key,
            "status": _source_status(key, value),
            "source_status": value.get("status", "NOT_PROVEN"),
            "applicability": "NOT_REVIEWED",
            "formal_compliance": "NOT_PROVEN",
            "reason_codes": value.get("reason_codes", []),
            "source": "SAME_RUN_ARCHIVED_ETABS_CAPTURE",
        })
    return {
        **base,
        "status": "SOURCE_PIPELINE_EVALUATED_PENDING_ENGINEERING_REVIEW",
        "source_component_count": len(COMPONENTS),
        "source_observed_count": sum(x["status"] == "SOURCE_OBSERVED_UNAPPROVED"
                                     for x in summaries),
        "conditional_component_count": sum(x["status"] == "CONDITIONAL_ONLY_NOT_CODE_APPROVED"
                                           for x in summaries),
        "checks": summaries,
        "stages": stages,
        "note": ("F–J are source-consistency/screening results only. "
                 "No full TBDY base shear or effective story drift PASS."),
    }


# V2 is opt-in for newly acquired sources. The v1 evaluator above must stay
# byte-for-byte stable: old receipts are content-sealed and re-evaluated on
# export. Reinterpreting v1 would make previously accepted runs unreadable.
_SELECT_MODAL = "Response Spectrum Modal Info"
_MODAL_SELECTION_DEPENDENCY = "INITIAL_UNSELECTED_MODAL_INFO_RET_CODE_1"
_MODAL_SELECTED_RECOVERY = "RSX_RSY_SELECTED_MODAL_200_ROWS_INDEPENDENTLY_RECONCILED"
_DIAGNOSTIC_STATUS = "SOURCE_PARTIAL_DISPLAY_DEPENDENCY_EXPLAINED"


def _count_status(rows: list[dict[str, Any]], expected: str, key: str) -> int:
    return sum(r.get(key) == expected for r in rows)


def _v2_modal_display_resolution(
    payload: Mapping[str, Any], legacy: Mapping[str, Any]
) -> dict[str, Any]:
    """Link only the *single* expected selection-dependent ETABS table.

    This never changes the original per-table source results or equates
    failed display reads with successful captures. All other missing source
    fields remain hard NOT_PROVEN.
    """
    explanation = {
        "table_key": _SELECT_MODAL,
        "status": "NOT_PROVEN",
        "reason_codes": [],
        "original_read_still_failed": True,
        "selected_case_read_observed": False,
        "selected_case_row_count": 0,
        "same_request_source_capture_observed": False,
        "analysis_generation_proven": False,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
    stages = legacy.get("stages") or {}
    e = stages.get("vs04_e") or {}
    f = stages.get("vs04_f") or {}
    g = stages.get("vs04_g") or {}
    h = stages.get("vs04_h") or {}
    i = stages.get("vs04_i") or {}
    e_candidates = e.get("candidates")
    f_components = f.get("components")
    g_rows = g.get("tables")
    cap = payload.get("capture_metadata") or {}
    raw_e = payload.get("vs04_basis_probe") or {}
    raw_g = payload.get("vs04_diaphragm_probe") or {}
    if (not isinstance(e_candidates, list) or not isinstance(f_components, list)
            or not isinstance(g_rows, list) or len(g_rows) != 5
            or cap.get("vs04_same_session_capture") is not True):
        return {**explanation, "reason_codes": [
            "SAME_SESSION_OR_EXACT_SOURCE_INVENTORY_NOT_ESTABLISHED"]}
    same_request = True
    explanation["same_request_source_capture_observed"] = same_request
    e_failed = [r for r in e_candidates if r.get("status") != "OBSERVED_UNAPPROVED"]
    f_failed = [r for r in f_components if r.get("status") !=
                "SOURCE_CONTRACT_OBSERVED_UNAPPROVED"]
    g_failed = [r for r in g_rows if r.get("source_status") != "OBSERVED_UNAPPROVED"]
    selected = (raw_g.get("spectrum_modal_selected_cases") or {})
    original = (raw_g.get("spectrum_modal_original_selection") or {})
    first = (raw_e.get("table_reads") or {}).get(_SELECT_MODAL) or {}
    second = (g_rows[4] if len(g_rows) == 5 else {})
    expect = (
        e.get("candidate_count") == 15 and e.get("observed_candidate_count") == 14
        and len(e_failed) == 1 and e_failed[0].get("table_key") == _SELECT_MODAL
        and f.get("expected_component_count") == 4
        and f.get("observed_component_count") == 3
        and len(f_failed) == 1 and f_failed[0].get("component") == "SPECTRUM_MODAL_OUTPUT"
        and g.get("source_expected_count") == 5
        and g.get("source_success_count") == 4
        and len(g_failed) == 1
        and g_failed[0].get("table_key") == _SELECT_MODAL
        and g_failed[0].get("capture_phase") == "original_selection"
        and second.get("capture_phase") == "selected_RSX_RSY"
        and second.get("source_status") == "OBSERVED_UNAPPROVED"
        and second.get("rows") == 200
        and original.get("status") == "CAPTURE_ERROR"
        and selected.get("status") == "CAPTURED"
        and selected.get("row_count") == 200
        and first.get("status") == "CAPTURE_ERROR"
        and "ret_code=1" in str(first.get("error", ""))
        and "ret_code=1" in str(original.get("error", ""))
        and raw_e.get("display_cases_before") == []
        and raw_g.get("original_display_cases") == []
        and raw_g.get("temporary_display_cases") == ["RSX", "RSY"]
        and raw_g.get("display_selection_restored") is True
        and h.get("observed_source_component_count") == 4
        and h.get("source_component_count") == 4
        and i.get("status") == "SOURCE_NUMERICAL_RECONSTRUCTED_PENDING_ENGINEERING_REVIEW"
        and i.get("analytical_knot_consistency_count") == 26
        and i.get("reconstructed_modal_rows") == 200
        and i.get("unexplained_modal_rows") == 0
    )
    if not expect:
        return {**explanation, "reason_codes": [
            "UNSELECTED_MODAL_ERROR_NOT_THE_ONLY_OPEN_SOURCE_DEPENDENCY",
            "SELECTED_RSX_RSY_200_ROW_RECONCILIATION_NOT_ESTABLISHED"]}
    return {
        **explanation,
        "status": "SOURCE_DISPLAY_SELECTION_DEPENDENCY_RECONCILED",
        "reason_codes": [_MODAL_SELECTION_DEPENDENCY, _MODAL_SELECTED_RECOVERY],
        "selected_case_read_observed": True,
        "selected_case_row_count": 200,
        "source_modal_output_proven_by": [
            "vs04_g.selected_RSX_RSY", "vs04_h", "vs04_i"],
        "original_error_preserved": str(original["error"]),
        "note": ("The first no-case display read remains a failed source read. "
                 "RSX/RSY selection in the same request supplies an independently "
                 "reconciled 200-row source, not code compliance."),
    }


def _v2_source_coverage(key: str, report: Mapping[str, Any]) -> dict[str, Any]:
    specs = {
        "vs04_e": ("candidate_count", "observed_candidate_count"),
        "vs04_f": ("expected_component_count", "observed_component_count"),
        "vs04_g": ("source_expected_count", "source_success_count"),
        "vs04_h": ("source_component_count", "observed_source_component_count"),
        "vs04_i": ("modal_source_rows", "reconstructed_modal_rows"),
    }
    if key in specs:
        a, b = specs[key]
        expected, observed = report.get(a), report.get(b)
    else:
        expected = observed = 1 if report.get("status") == (
            "CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING") else 0
    if type(expected) is not int or type(observed) is not int:
        expected = observed = 0
    return {
        "expected": expected,
        "observed_in_original_stage": observed,
        "unobserved_in_original_stage": max(expected - observed, 0),
        "independent_selected_case_reconciliation_count": 0,
    }


def _v2_source_reasons(key: str, report: Mapping[str, Any]) -> list[str]:
    reasons = [str(r) for r in report.get("reason_codes", [])]
    if key == "vs04_e":
        for row in report.get("candidates", []):
            if row.get("status") != "OBSERVED_UNAPPROVED":
                reasons.extend(row.get("reason_codes", []) or
                               ["SOURCE_TABLE_NOT_OBSERVED"])
    elif key == "vs04_f":
        for row in report.get("components", []):
            if row.get("status") != "SOURCE_CONTRACT_OBSERVED_UNAPPROVED":
                reasons.extend(row.get("reason_codes", []) or
                               ["SOURCE_COMPONENT_NOT_OBSERVED"])
    elif key == "vs04_g":
        for row in report.get("tables", []):
            if row.get("source_status") != "OBSERVED_UNAPPROVED":
                reasons.extend(row.get("reason_codes", []) or
                               ["SOURCE_TABLE_NOT_OBSERVED"])
    elif key == "vs04_h":
        for row in report.get("components", []):
            if row.get("status") != "SOURCE_CONTRACT_OBSERVED_UNAPPROVED":
                reasons.extend(row.get("reason_codes", []) or
                               ["SOURCE_COMPONENT_NOT_OBSERVED"])
    return list(dict.fromkeys(reasons))


def _v2_missing_normative_authority(key: str, stage: Mapping[str, Any]) -> list[str]:
    missing = (stage.get("mandatory_holds") or stage.get("missing_authorities")
               or [])
    if not isinstance(missing, list):
        missing = ["UNQUALIFIED_ENGINEERING_AUTHORITY"]
    return list(dict.fromkeys(str(x) for x in missing)) or [
        "MODEL_ANALYSIS_GENERATION_NOT_INDEPENDENTLY_PROVEN",
        "FULL_TBDY_APPLICABILITY_AND_SPECTRAL_SCALING_NOT_PROVEN",
    ]


def _v2_single_run_source_pipeline(payload: Mapping[str, Any]) -> dict[str, Any]:
    original = _legacy_single_run_source_pipeline(payload)
    if original.get("status") != "SOURCE_PIPELINE_EVALUATED_PENDING_ENGINEERING_REVIEW":
        return original
    diag = _v2_modal_display_resolution(payload, original)
    resolved = diag["status"] == "SOURCE_DISPLAY_SELECTION_DEPENDENCY_RECONCILED"
    stages = original["stages"]
    checks = []
    for old in original["checks"]:
        key = old["stage_key"]
        stage = stages[key]
        coverage = _v2_source_coverage(key, stage)
        status = old["status"]
        reasons = _v2_source_reasons(key, stage)
        if resolved and key in ("vs04_e", "vs04_f", "vs04_g"):
            status = _DIAGNOSTIC_STATUS
            coverage["independent_selected_case_reconciliation_count"] = 1
            reasons = [_MODAL_SELECTION_DEPENDENCY, _MODAL_SELECTED_RECOVERY]
        elif status == "NOT_PROVEN" and not reasons:
            reasons = ["SOURCE_EVIDENCE_INCOMPLETE"]
        checks.append({
            **old,
            "status": status,
            "execution_status": (
                "CONDITIONAL_ONLY" if key == "vs04_j" and
                status == "CONDITIONAL_ONLY_NOT_CODE_APPROVED" else
                "SOURCE_EVALUATED" if status != "NOT_PROVEN" else "BLOCKED_BY_SOURCE"),
            "coverage": coverage,
            "reason_codes": reasons,
            "missing_evidence": _v2_missing_normative_authority(key, stage),
            "source_identity": {
                "capture": "CURRENT_RUN_ETABS_SNAPSHOT",
                "source_table_key": _SELECT_MODAL if key in
                    ("vs04_e", "vs04_f", "vs04_g", "vs04_h", "vs04_i") else
                    "Base Reactions / Mass Summary by Story",
                "receipt_integrity_check": "ON_JSON_HTML_EXPORT_AND_HISTORY_REPLAY",
            },
        })
    return {
        **original,
        "pipeline_contract_version": "v2",
        "checks": checks,
        "modal_display_selection_reconciliation": diag,
        "source_diagnostic_resolved_count": sum(
            c["status"] == _DIAGNOSTIC_STATUS for c in checks),
        "source_unresolved_count": sum(
            c["status"] == "NOT_PROVEN" for c in checks),
        "note": (
            "E/F/G remain partially observed in their original source records; "
            "only the single display-selection dependency is independently "
            "explained by selected RSX/RSY 200-row output. "
            "No formal TBDY check is proven."),
    }


def evaluate_single_run_source_pipeline(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Versioned source interpretation; do not invalidate historical receipts."""
    if (isinstance(payload, Mapping) and
            isinstance(payload.get("analysis_sources"), Mapping) and
            payload["analysis_sources"].get("pipeline_contract_version") == "v2"):
        return _v2_single_run_source_pipeline(payload)
    return _legacy_single_run_source_pipeline(payload)
