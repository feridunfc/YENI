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


def evaluate_single_run_source_pipeline(payload: Mapping[str, Any] | None) -> dict[str, Any]:
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
