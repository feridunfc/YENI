"""VS04-E: TBDY 2018 Chapter 4 pure formula kernels and fail-closed basis gates.

This module deliberately does not read a bare ETABS Story Drifts cell as
Delta_i/h_i or a Base Reactions component as a qualified V_tx. The numerical
kernels are independently unit-tested; no actual model gets PASS without
authoritative source lineage, case/scaling and applicability evidence.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping

from .analysis_sources import review_analysis_sources, TABLES
from .analysis_numerics import evaluate_analysis_numerics

GATES = (
    ("modal_case_lineage", "TBDY 4.8.1 and 4.7.3",
     ("source_model_generation", "modal_case_population", "governing_period_XY")),
    ("base_shear_X", "TBDY 4.7.1.1 + 4.8.4.1",
     ("source_model_generation", "seismic_mass_mt", "SaR_at_qualified_Tp_X",
      "importance_I", "SDS_DD2", "eq_4_19_equivalent_shear_X",
      "gammaE_from_A1_B2_B3", "Vtx_pre_scaling_X",
      "response_spectrum_case_scale_X", "basement_boundary_X")),
    ("base_shear_Y", "TBDY 4.7.1.1 + 4.8.4.1",
     ("source_model_generation", "seismic_mass_mt", "SaR_at_qualified_Tp_Y",
      "importance_I", "SDS_DD2", "eq_4_19_equivalent_shear_Y",
      "gammaE_from_A1_B2_B3", "Vtx_pre_scaling_Y",
      "response_spectrum_case_scale_Y", "basement_boundary_Y")),
    ("effective_drift_X", "TBDY 4.9.1.1-4.9.1.4",
     ("source_model_generation", "complete_physical_story_inventory",
      "reduced_relative_displacements_X", "drift_ratio_semantics_X",
      "R_over_I_X", "lambda_DD3_over_DD2_at_Tp_X",
      "h_i_each_story", "wall_joint_classification_X",
      "material_kappa_X", "spectrum_scaling_for_drift_X")),
    ("effective_drift_Y", "TBDY 4.9.1.1-4.9.1.4",
     ("source_model_generation", "complete_physical_story_inventory",
      "reduced_relative_displacements_Y", "drift_ratio_semantics_Y",
      "R_over_I_Y", "lambda_DD3_over_DD2_at_Tp_Y",
      "h_i_each_story", "wall_joint_classification_Y",
      "material_kappa_Y", "spectrum_scaling_for_drift_Y")),
)


class UnqualifiedEngineeringInput(ValueError):
    pass


def _positive(value: Any, name: str) -> Decimal:
    if type(value) not in (Decimal, int, float, str):
        raise UnqualifiedEngineeringInput(f"{name}: INVALID_VALUE_TYPE")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise UnqualifiedEngineeringInput(f"{name}: NONNUMERIC") from None
    if not number.is_finite() or number <= 0:
        raise UnqualifiedEngineeringInput(f"{name}: NONPOSITIVE_OR_NONFINITE")
    return number


def eq_4_19_equivalent_base_shear_kn(
    *, seismic_mass_kg: Any, reduced_spectral_acceleration_m_s2: Any,
    importance_factor: Any, sds_dd2: Any, gravity_m_s2: Any = "9.80665",
) -> dict[str, str]:
    """V_tE=max(m_t SaR(T_p), 0.04 m_t I S_DS g), returned in kN.

    The caller must provide qualified mass, spectrum and Tp semantics; this
    kernel never infers them from ETABS Base Reactions or modal frequencies.
    """
    mass = _positive(seismic_mass_kg, "seismic_mass_kg")
    sar = _positive(reduced_spectral_acceleration_m_s2, "SaR")
    I = _positive(importance_factor, "I")
    sds = _positive(sds_dd2, "SDS_DD2")
    gravity = _positive(gravity_m_s2, "gravity_m_s2")
    with localcontext() as c:
        c.prec = 35
        spectral = mass * sar / 1000
        floor = Decimal("0.04") * mass * I * sds * gravity / 1000
        vt = max(spectral, floor)
    return {"spectral_base_shear_kn": str(spectral),
            "minimum_base_shear_kn": str(floor),
            "equivalent_base_shear_kn": str(vt),
            "source_status": "FORMULA_ONLY_UNQUALIFIED"}


def eq_4_31_base_scale(
    *, equivalent_base_shear_kn: Any, modal_base_shear_kn: Any,
    irregularity_A1_B2_B3_any: bool, irregularity_inventory_complete: bool,
    basement_boundary_qualified: bool,
) -> dict[str, str]:
    """beta=max(1,gamma_E V_tE/V_tx). No automatic B2/B3 inference from A1."""
    if type(irregularity_A1_B2_B3_any) is not bool:
        raise UnqualifiedEngineeringInput("IRREGULARITY_DECISION_NOT_BOOLEAN")
    if irregularity_inventory_complete is not True:
        raise UnqualifiedEngineeringInput("A1_B2_B3_INVENTORY_NOT_QUALIFIED")
    if basement_boundary_qualified is not True:
        raise UnqualifiedEngineeringInput("BASEMENT_BOUNDARY_NOT_QUALIFIED")
    vte = _positive(equivalent_base_shear_kn, "VtE_kN")
    vtx = _positive(modal_base_shear_kn, "Vtx_kN")
    gamma = Decimal("0.90") if irregularity_A1_B2_B3_any else Decimal("0.80")
    with localcontext() as c:
        c.prec = 35
        target = gamma * vte
        beta = max(Decimal(1), target / vtx)
    return {"gamma_E": str(gamma), "minimum_modal_base_shear_kn": str(target),
            "modal_base_shear_kn": str(vtx), "required_scale_factor": str(beta),
            "scaling_required": str(beta > 1).lower(),
            "source_status": "FORMULA_ONLY_UNQUALIFIED"}


def eq_4_34_effective_drift(
    *, reduced_relative_displacement_m: Any,
    story_height_m: Any, R: Any, importance_factor: Any,
    lambda_dd3_dd2: Any, material: str, wall_connection: str,
    flexible_wall_capacity_documented: bool = False,
) -> dict[str, str]:
    """TBDY Eq 4.33/4.34, *provided* delta, height and basis are qualified.

    No blind use of ETABS 'Drift' / 'Drift/' display fields.
    """
    delta = _positive(reduced_relative_displacement_m, "reduced_delta_m")
    h = _positive(story_height_m, "story_height_m")
    Rv = _positive(R, "R")
    Iv = _positive(importance_factor, "I")
    lam = _positive(lambda_dd3_dd2, "lambda")
    if material not in ("RC", "STEEL"):
        raise UnqualifiedEngineeringInput("UNSUPPORTED_BUILDING_MATERIAL")
    if wall_connection not in ("ADHERED_BRITTLE", "DOCUMENTED_FLEXIBLE"):
        raise UnqualifiedEngineeringInput("WALL_CONNECTION_NOT_QUALIFIED")
    if wall_connection == "DOCUMENTED_FLEXIBLE" and flexible_wall_capacity_documented is not True:
        raise UnqualifiedEngineeringInput("FLEXIBLE_WALL_CAPACITY_NOT_DOCUMENTED")
    kappa = Decimal(1) if material == "RC" else Decimal("0.5")
    coefficient = Decimal("0.008") if wall_connection == "ADHERED_BRITTLE" else Decimal("0.016")
    with localcontext() as c:
        c.prec = 35
        delta_effective = delta * Rv / Iv
        scaled_ratio = lam * delta_effective / h
        limit = coefficient * kappa
    return {"effective_relative_displacement_m": str(delta_effective),
            "lambda_effective_drift_over_height": str(scaled_ratio),
            "limit": str(limit), "kappa": str(kappa),
            "condition_satisfied_if_all_input_proofs_accepted": str(scaled_ratio <= limit).lower(),
            "source_status": "FORMULA_ONLY_UNQUALIFIED"}


def eq_4_9_lambda(*, sae_dd3_m_s2: Any, sae_dd2_m_s2: Any) -> str:
    """Lambda only from independently qualified *same Tp* DD3 and DD2 Sae."""
    dd3 = _positive(sae_dd3_m_s2, "Sae_DD3_at_Tp")
    dd2 = _positive(sae_dd2_m_s2, "Sae_DD2_at_Tp")
    with localcontext() as c:
        c.prec = 35
        return str(dd3 / dd2)


def review_normative_readiness(analysis_sources: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compile every expected norm-dependent check instance even if no evidence.

    SOURCE_ARITHMETIC_OBSERVED is not proof of regulatory applicability,
    result generation, case scale, or complete story/member inventory.
    """
    shape = review_analysis_sources(analysis_sources)
    numerical = evaluate_analysis_numerics(analysis_sources)
    numeric_by_id = {x["component"]: x for x in numerical.get("results", ())}
    rows = []
    for name, regulation, dependencies in GATES:
        observed_hint = []
        if name == "modal_case_lineage":
            hint = numeric_by_id.get("MODAL_PERIOD_FREQUENCY_IDENTITY", {})
            if hint.get("status") == "SOURCE_ARITHMETIC_OBSERVED":
                observed_hint.append("MODAL_PERIOD_ARITHMETIC_ONLY")
        elif name.startswith("base_shear_"):
            d = name[-1]
            if numeric_by_id.get("BASE_REACTION_" + d, {}).get("status") == "SOURCE_ARITHMETIC_OBSERVED":
                observed_hint.append(f"BASE_REACTION_{d}_DISPLAY_COMPONENT_ONLY")
        elif name.startswith("effective_drift_"):
            d = name[-1]
            if numeric_by_id.get("STORY_DRIFT_" + d, {}).get("status") == "SOURCE_ARITHMETIC_OBSERVED":
                observed_hint.append(f"STORY_DRIFT_{d}_DISPLAY_RECIPROCAL_ONLY")
        rows.append({
            "check_id": name,
            "code_ref": regulation,
            "status": "NOT_PROVEN",
            "required_evidence": list(dependencies),
            "missing_evidence": list(dependencies),
            "source_only_hints": observed_hint,
            "formula_executed": False,
            "formal_compliance": "NOT_PROVEN",
        })
    return {"stage": "VS04_E_NORMATIVE_READINESS",
            "status": "EVIDENCE_REQUIRED",
            "engineering_release": "NOT_READY",
            "formal_compliance": "NOT_PROVEN",
            "regulatory_checks_executed": 0,
            "expected_check_count": len(GATES),
            "proven_check_count": 0,
            "source_capture_status": shape.get("status"),
            "source_numeric_status": numerical.get("status"),
            "checks": rows,
            "note": "No implicit approval of response spectrum roles, story drift units, R/I, lambda, gammaE, basement boundary or model generation."}
