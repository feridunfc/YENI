"""R04: offline source-bound replay of historical modal/spectral/base-shear evidence.

The input is a PINNED archived all-checks report, not the live ETABS model.
Recompute from its raw source snapshot; never join unrelated run generations,
issue normative PASS, or reinterpret spectrum maxima as concurrent forces.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

from .source import SourceError, parse_modal_capture
from .modal import evaluate_modal_mass
from .analysis_sources import review_analysis_sources
from .analysis_numerics import evaluate_analysis_numerics
from .spectrum_reconstruction import review_spectrum_reconstruction
from .base_shear_screening import review_base_shear_screening

SCHEMA = "tbdy.next.r04-historical-modal-spectral-replay.v1"
REPORT_SCHEMA = "tbdy.next.complete.engineering.report.v1"
REPLAY_MODAL = "MEETS_NUMERICAL_CRITERION"
REPLAY_SPECTRUM = "SOURCE_NUMERICAL_RECONSTRUCTED_PENDING_ENGINEERING_REVIEW"
REPLAY_BASE = "CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING"

class R04SourceError(ValueError):
    """An input/lineage or a source-to-recorded-result mismatch."""


def _require(value: bool, reason: str) -> None:
    if not value:
        raise R04SourceError(reason)


def _number_equal(a: Any, b: Any, reason: str) -> None:
    try:
        left, right = Decimal(str(a)), Decimal(str(b))
        _require(left.is_finite() and right.is_finite() and left == right, reason)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise R04SourceError(reason) from exc


def _fingerprint(value: Mapping[str, Any]) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _cross_run(r03: Mapping[str, Any] | None, report_run: str) -> dict[str, Any]:
    if r03 is None:
        return {"status": "NO_R03_ARTIFACT_SUPPLIED",
                "same_generation_proven": False, "design_roles_approved": False}
    _require(isinstance(r03, Mapping)
             and r03.get("schema") == "tbdy.next.r03-unapproved-combobook.v1"
             and r03.get("execution_authority") == "DENIED"
             and r03.get("engineering_release") == "NOT_READY",
             "R03_CANDIDATE_CONTRACT_INVALID")
    other = r03.get("source_run_id")
    _require(isinstance(other, str) and bool(other), "R03_SOURCE_RUN_ID_MISSING")
    return {
        "status": ("DIFFERENT_RUN_IDS_NO_SOURCE_JOIN" if other != report_run
                   else "MATCHED_RUN_ID_NOT_GENERATION_PROOF"),
        "r03_run_id": other,
        "same_generation_proven": False,
        "design_roles_approved": False,
        "design_demand_authority": "DENIED",
    }


def review_r04_historical_run(
    report: Mapping[str, Any],
    report_sha256: str,
    r03_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure re-evaluation, not an acceptance function.

    Never trust cached 'success' text: modal/source numeric/spectrum/base
    kernels are called again against all exact stored source rows. The input
    file's SHA must additionally be checked against a pinned manifest by CLI.
    """
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "source_file_sha256": report_sha256,
        "run_id": None,
        "status": "BLOCKED_SOURCE_REPLAY",
        "normative_check_count_authorized": 0,
        "design_demand_authority": "DENIED",
        "analysis_generation_proven": False,
        "physical_concurrence_proven": False,
        "spectrum_case_scale_code_authorized": False,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "full_equivalent_base_shear_kn": None,
        "applied_beta_x": None, "applied_beta_y": None,
        "reason_codes": [],
    }
    try:
        _require(isinstance(report, Mapping) and report.get("schema") == REPORT_SCHEMA,
                 "UNKNOWN_FULL_REPORT_SCHEMA")
        run_id = report.get("run_id")
        _require(isinstance(run_id, str) and run_id.startswith("RUN-"),
                 "SOURCE_RUN_ID_INVALID")
        base["run_id"] = run_id
        _require(report.get("formal_compliance") == "NOT_PROVEN"
                 and report.get("engineering_release") == "NOT_READY",
                 "UNAUTHORIZED_HISTORICAL_RELEASE_FLAG")
        snap = report.get("source_snapshot")
        _require(isinstance(snap, Mapping)
                 and snap.get("schema") == "tbdy.next.modal.capture.v1"
                 and snap.get("source_mode") == "LIVE_ETABS"
                 and isinstance(snap.get("source_identity"), str)
                 and bool(snap["source_identity"]),
                 "MODAL_SNAPSHOT_IDENTITY_MISSING")
        analysis = snap.get("analysis_sources")
        basis_raw = snap.get("vs04_basis_probe")
        diaphragm_raw = snap.get("vs04_diaphragm_probe")
        _require(isinstance(analysis, Mapping)
                 and isinstance(basis_raw, Mapping)
                 and isinstance(diaphragm_raw, Mapping),
                 "VS04_SOURCE_SNAPSHOTS_MISSING")
        _require(analysis.get("analysis_generation_proven") is False
                 and analysis.get("combination_roles_approved") is False
                 and analysis.get("requested_cases") ==
                     {"modal": "Modal", "x_candidate": "RSX", "y_candidate": "RSY"},
                 "UNAPPROVED_CASE_OR_GENERATION_CLAIM")
        _require(analysis.get("display_selection_restored") is True
                 and basis_raw.get("read_only_invariant_proven") is True
                 and diaphragm_raw.get("display_selection_restored") is True,
                 "READONLY_RESTORATION_NOT_OBSERVED")
        _require(analysis.get("units_before") == analysis.get("units_after") == 6
                 and basis_raw.get("units_before") == basis_raw.get("units_after") == 6
                 and diaphragm_raw.get("units_before") == diaphragm_raw.get("units_after") == 6,
                 "CAPTURE_UNIT_STATE_CONFLICT")

        source_review = review_analysis_sources(analysis)
        _require(source_review.get("status") == "SOURCE_SCHEMA_CAPTURED_PENDING_REVIEW"
                 and source_review.get("captured_table_count") == 3,
                 "THREE_ANALYSIS_SOURCE_TABLES_NOT_QUALIFIED")
        numeric = evaluate_analysis_numerics(analysis)
        _require(numeric.get("status") == "SOURCE_NUMERICAL_OBSERVED_PENDING_ENGINEERING_REVIEW"
                 and numeric.get("observed_component_count") == 5,
                 "VS04_D_SOURCE_NUMERIC_REPLAY_INCOMPLETE")

        recorded_numeric = report.get("vs04_numerics")
        _require(isinstance(recorded_numeric, Mapping)
                 and recorded_numeric.get("status") == numeric["status"]
                 and recorded_numeric.get("results") == numeric.get("results"),
                 "VS04_D_REPLAY_VS_RECORDED_RESULT_CONFLICT")

        modal_table = parse_modal_capture(snap, case="Modal")
        modal = evaluate_modal_mass(modal_table).as_dict()
        recorded_modal = next((r for r in report.get("checks", ())
                               if isinstance(r, Mapping)
                               and r.get("check_id") == "modal_mass_95"), None)
        _require(isinstance(recorded_modal, Mapping)
                 and recorded_modal.get("status") == modal["status"],
                 "MODAL_REPLAY_STATUS_CHANGED")
        for k in ("sum_ux", "sum_uy", "required_ratio"):
            _number_equal(modal[k], recorded_modal.get(k),
                          "MODAL_RECORDED_SCALAR_MISMATCH:" + k)
        _require(int(recorded_modal.get("governing_mode_count")) ==
                 modal["governing_mode_count"],
                 "MODAL_GOVERNING_MODE_COUNT_CONFLICT")

        basis = {"schema": "tbdy.next.vs04e.basis-probe-receipt.v1",
                 "source": basis_raw}
        g = {"schema": "tbdy.next.vs04g.diaphragm-source-receipt.v1",
             "source": diaphragm_raw}
        prior = {"schema": "tbdy.next.vs04.offline-source-replay.v1",
                 "numeric_source_review": numeric}
        spectrum = review_spectrum_reconstruction(basis, g, prior)
        _require(spectrum.get("status") == REPLAY_SPECTRUM
                 and spectrum.get("source_knot_count") == 26
                 and spectrum.get("reconstructed_modal_rows") == 200
                 and spectrum.get("unexplained_modal_rows") == 0,
                 "SPECTRAL_SOURCE_REPLAY_INCOMPLETE")
        base_shear = review_base_shear_screening(basis, g, prior)
        _require(base_shear.get("status") == REPLAY_BASE
                 and base_shear.get("spectrum_modal_rows_verified") == 200
                 and base_shear.get("full_equivalent_base_shear_kn") is None
                 and base_shear.get("beta_tE_X") is None
                 and base_shear.get("beta_tE_Y") is None,
                 "FULL_BASE_SHEAR_AUTHORITY_NOT_RECONCILED")

        prior_pipeline = report.get("vs04_pipeline")
        recorded_stages = prior_pipeline.get("stages") if isinstance(prior_pipeline, Mapping) else None
        _require(isinstance(recorded_stages, Mapping)
                 and isinstance(recorded_stages.get("vs04_i"), Mapping)
                 and isinstance(recorded_stages.get("vs04_j"), Mapping),
                 "RECORDED_PIPELINE_STAGES_MISSING")
        old_s = recorded_stages["vs04_i"]
        old_b = recorded_stages["vs04_j"]
        for key in ("status", "source_knot_count", "modal_source_rows",
                    "reconstructed_modal_rows", "unexplained_modal_rows"):
            _require(old_s.get(key) == spectrum.get(key),
                     "VS04_I_RECORDED_RESULT_CONFLICT:" + key)
        _require(old_b.get("status") == base_shear.get("status"),
                 "VS04_J_RECORDED_STATUS_CONFLICT")
        _number_equal(old_b.get("conditional_eq_4_19_minimum_term_kn"),
                      base_shear.get("conditional_eq_4_19_minimum_term_kn"),
                      "VS04_J_RECORDED_CONDITIONAL_FLOOR_CONFLICT")
        _require(old_b.get("full_equivalent_base_shear_kn") is None
                 and old_b.get("beta_tE_X") is None
                 and old_b.get("beta_tE_Y") is None,
                 "VS04_J_RECORDED_UNAUTHORIZED_BETA_OR_VTE")
        for k in ("RSX_FX", "RSY_FY"):
            _number_equal(old_b.get("source_case_base_reaction_components_kn", {}).get(k),
                          base_shear["source_case_base_reaction_components_kn"].get(k),
                          "VS04_J_REACTION_CONFLICT:" + k)

        relation = _cross_run(r03_candidate, run_id)
        base.update(
            status="HISTORICAL_SOURCE_NUMERIC_REPLAY_RECONCILED",
            recorded_source_mode="LIVE_ETABS_ARCHIVED_OFFLINE",
            original_run_id=run_id,
            model_source_identity_sha256=sha256(snap["source_identity"].encode()).hexdigest(),
            source_snapshot_sha256=_fingerprint(dict(snap)),
            analysis_source_sha256=_fingerprint(dict(analysis)),
            r03_relation=relation,
            modal_mass={"case": "Modal",
                        "observed_mode_count": len(modal_table.rows),
                        "numerical_status": modal["status"],
                        "sum_ux": modal["sum_ux"], "sum_uy": modal["sum_uy"],
                        "governing_mode_count": modal["governing_mode_count"],
                        "code_acceptance": "NOT_PROVEN"},
            spectrum_replay={"source_knot_count": spectrum["source_knot_count"],
                             "source_modal_rows": spectrum["modal_source_rows"],
                             "independently_reconstructed_rows": spectrum["reconstructed_modal_rows"],
                             "unexplained_rows": spectrum["unexplained_modal_rows"],
                             "status": spectrum["status"],
                             "normative_scale_authorized": False},
            base_shear_screening={
                "directional_native_component_envelopes_kn":
                    dict(base_shear["source_case_base_reaction_components_kn"]),
                "conditional_minimum_term_kn":
                    base_shear["conditional_eq_4_19_minimum_term_kn"],
                "minimum_term_is_not_full_vte": True,
                "base_shear_x_y_formal_status": "NOT_PROVEN",
                "beta_x_y": None,
            },
            expected_source_instance_counts={
                "modal_modes": 100, "spectrum_function_points": 26,
                "rsx_modal_accelerations": 100, "rsy_modal_accelerations": 100,
                "directional_base_reaction_components": 2},
            missing_authorities=sorted(set(
                base_shear.get("missing_authorities", ()) +
                ["MODEL_GENERATION_CROSS_RUN_UNPROVEN",
                 "SEISMIC_COMBO_ROLES_UNAPPROVED",
                 "TBDY_TP_PERIOD_BOUND_NOT_APPROVED",
                 "FULL_VTE_AND_BETA_SOURCE_NOT_AVAILABLE",
                 "DD3_AND_DRIFT_BASIS_NOT_APPROVED"])),
        )
    except (R04SourceError, SourceError, KeyError, TypeError, ValueError,
            InvalidOperation, ZeroDivisionError, OverflowError) as exc:
        base["reason_codes"] = [str(exc)]
    base["result_sha256"] = _fingerprint(base)
    return base
