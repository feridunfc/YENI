"""VS04-J: source-bound, non-normative base-shear screening.

Only calculate the independent Eq (4.19) *minimum term* from tentative
seismic mass, SDS, I and g; do not calculate full VtE without qualified
dominant period and SaR(Tp), or beta without A1/B2/B3 and pre-scaled Vtx.

Explicit preconditions:
  - VS04-E story/group/joint mass source reconciliation (not a mt approval)
  - VS04-E actual spectrum-case, direction, Ritz and function bindings
  - VS04-G selected-case modal source and VS04-D modal periods
  - VS04-I 26-knot and 200-mode numerical reconstruction
  - VS04-D FX/FY component observations (NOT pre-beta modal Vtx proof)

In all outcomes the model-generation and normative release stay unproven.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping

from .basis_linkage import review_basis_linkage
from .spectrum_reconstruction import (
    review_spectrum_reconstruction, SOURCE_ONLY
)

G_STANDARD = Decimal("9.80665")


def _d(value: Any, label: str, *, positive: bool = True) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(label + ":NOT_STRING")
    try:
        x = Decimal(value)
    except InvalidOperation:
        raise ValueError(label + ":INVALID_DECIMAL") from None
    if not x.is_finite() or (positive and x <= 0):
        raise ValueError(label + ":NOT_FINITE_POSITIVE")
    return x


def _observed_reaction(prior: Mapping[str, Any], direction: str) -> str:
    review = prior.get("numeric_source_review")
    if not isinstance(review, Mapping) or review.get(
            "numeric_regulatory_checks_executed") != 0:
        raise ValueError("PRIOR_REPLAY_NUMERIC_SCOPE_INVALID")
    results = review.get("results")
    if not isinstance(results, list):
        raise ValueError("PRIOR_REPLAY_MISSING_RESULTS")
    key = "BASE_REACTION_" + direction
    matches = [r for r in results if isinstance(r, Mapping) and r.get("component") == key]
    if len(matches) != 1 or matches[0].get("status") != "SOURCE_ARITHMETIC_OBSERVED":
        raise ValueError("PRIOR_BASE_REACTION_COMPONENT_UNAVAILABLE:" + direction)
    items = matches[0].get("items")
    if not isinstance(items, list) or len(items) != 1:
        raise ValueError("PRIOR_BASE_REACTION_ROW_AMBIGUOUS")
    item = items[0]
    case, field = ("RSX", "FX") if direction == "X" else ("RSY", "FY")
    if (item.get("output_case") != case or item.get("component") != field
            or item.get("source_semantics") != "COMPONENT_EXTREME_ONLY"
            or item.get("simultaneous_force_vector_proven") is not False
            or item.get("case_type") != "LinRespSpec"
            or item.get("step_type") != "Max"):
        raise ValueError("RESPONSE_SPECTRUM_COMPONENT_PROVENANCE_UNQUALIFIED:" + direction)
    amount = _d(item.get("absolute_reaction_kn"), field)
    if amount != abs(_d(item.get(field), field, positive=False)):
        raise ValueError("RECORDED_COMPONENT_ABSOLUTE_MISMATCH:" + direction)
    return str(amount)


def review_base_shear_screening(
    basis: Mapping[str, Any] | None,
    selected_modal: Mapping[str, Any] | None,
    prior_modal: Mapping[str, Any] | None,
) -> dict[str, Any]:
    result = {
        "stage": "VS04J_SOURCE_BOUND_BASE_SHEAR_SCREENING",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "normative_checks_executed": 0,
        "source_only": True,
        "model_analysis_generation_proven": False,
        "seismic_mass_scope_authorized": False,
        "design_spectrum_DD2_authorized": False,
        "pre_beta_modal_base_shear_authorized": False,
        "governing_periods_XY_authorized": False,
        "irregularity_A1_B2_B3_inventory_authorized": False,
        "basement_boundary_authorized": False,
        "full_equivalent_base_shear_kn": None,
        "beta_tE_X": None,
        "beta_tE_Y": None,
    }
    try:
        if (not isinstance(basis, Mapping)
                or basis.get("schema") != "tbdy.next.vs04e.basis-probe-receipt.v1"
                or not isinstance(selected_modal, Mapping)
                or selected_modal.get("schema") != "tbdy.next.vs04g.diaphragm-source-receipt.v1"
                or not isinstance(prior_modal, Mapping)
                or prior_modal.get("schema") != "tbdy.next.vs04.offline-source-replay.v1"):
            raise ValueError("EXACT_THREE_SOURCE_RECEIPTS_REQUIRED")
        link = review_basis_linkage(basis)
        if link.get("status") != "BASIS_SOURCE_PARTIAL_PENDING_ENGINEERING_REVIEW":
            raise ValueError("VS04F_SOURCE_LINKAGE_NOT_AVAILABLE")
        components = {c["component"]: c for c in link.get("components", ())}
        required = ("SEISMIC_MASS_RECONCILIATION",
                    "RESPONSE_SPECTRUM_CASE_BINDINGS", "PHYSICAL_STORY_GEOMETRY")
        if any(components.get(name, {}).get("status") !=
               "SOURCE_CONTRACT_OBSERVED_UNAPPROVED" for name in required):
            raise ValueError("MASS_SPECTRUM_OR_STORY_SOURCE_NOT_CONSISTENT")
        numerical = review_spectrum_reconstruction(basis, selected_modal, prior_modal)
        if (numerical.get("status") != SOURCE_ONLY or
                numerical.get("analytical_knot_consistency_count") != 26 or
                numerical.get("reconstructed_modal_rows") != 200 or
                numerical.get("unexplained_modal_rows") != 0):
            raise ValueError("VS04I_SPECTRUM_NUMERICAL_SOURCE_NOT_RECONSTRUCTED")

        mass = components["SEISMIC_MASS_RECONCILIATION"]["source_facts"]
        if (mass.get("mass_source") != "MsSrc1"
                or mass.get("comparisons") != {
                    "joint_to_group_UX": True, "joint_to_group_UY": True,
                    "story_to_group_UX": True, "story_to_group_UY": True
                }):
            raise ValueError("MASS_COMPONENT_SOURCE_BINDINGS_INCOMPLETE")
        sums = mass["group_sums"]
        ux, uy = (_d(sums[k], k) for k in ("UX_ton", "UY_ton"))
        if ux != uy:
            raise ValueError("DIRECTIONAL_MASS_DIFFERENCE_NEEDS_SEPARATE_ENGINEERING_BASIS")
        function = components["RESPONSE_SPECTRUM_CASE_BINDINGS"]["source_facts"]
        if (function.get("function") != "RESP_YATAY"
                or function.get("modal_case") != "Modal"
                or function.get("mass_source") != "MsSrc1"):
            raise ValueError("FUNCTION_OR_MASS_CASE_BINDING_NOT_MATCHED")
        params = function["function_parameters"]
        i_factor = _d(params["I"], "importance_I")
        sds = _d(params["SDS"], "source_SDS")
        x_reaction = _observed_reaction(prior_modal, "X")
        y_reaction = _observed_reaction(prior_modal, "Y")
        with localcontext() as ctx:
            ctx.prec = 35
            tentative_kg = ux * Decimal(1000)
            minimum = Decimal("0.04") * tentative_kg * i_factor * sds * G_STANDARD / 1000

        return {
            **result,
            "status": "CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING",
            "source_mass_candidate_ton": str(ux),
            "source_mass_candidate_kg": str(tentative_kg),
            "source_mass_unit": "ton",
            "candidate_importance_factor": str(i_factor),
            "candidate_SDS": str(sds),
            "gravity_m_s2": str(G_STANDARD),
            "conditional_eq_4_19_minimum_term_kn": str(minimum),
            "source_case_base_reaction_components_kn": {
                "RSX_FX": x_reaction, "RSY_FY": y_reaction
            },
            "spectrum_function_samples_verified": 26,
            "spectrum_modal_rows_verified": 200,
            "source_mass_group_story_joint_consistent": True,
            "known_cautions": [
                "SOURCE_I_FIELD_UNIT_METADATA_SEC_NOT_DIMENSIONLESS_PROOF",
                "SEMI_RIGID_DIAPHRAGM_MASS_SUMMARY_ZERO",
                "CANDIDATE_FLOOR_IS_ONLY_ONE_TERM_OF_EQ_4_19",
                "DISPLAYED_BASE_REACTIONS_NOT_CERTIFIED_UNSCALED_VTX",
                "NO_TP_XY_NO_VTE_NO_GAMMA_NO_BETA",
            ],
            "missing_authorities": [
                "MODEL_ANALYSIS_GENERATION_SAME_AS_ALL_CAPTURES",
                "SEISMIC_MASS_INCLUSION_BOUNDARY",
                "DESIGN_SPECTRUM_GROUND_MOTION_DD2_AND_TP_XY",
                "A1_B2_B3_FULL_BUILDING_IRREGULARITY_INVENTORY",
                "BASEMENT_BOUNDARY_AND_MODAL_VTX_PRE_BETA",
                "ACTUAL_RESPONSE_SPECTRUM_SCALING_AND_COMBINATION_LINEAGE",
                "SEMI_RIGID_DIAPHRAGM_ECCENTRICITY_EFFECT",
            ],
        }
    except (ValueError, KeyError, TypeError, InvalidOperation, ZeroDivisionError) as exc:
        return {
            **result,
            "status": "NOT_PROVEN",
            "reason_codes": [str(exc)],
            "conditional_eq_4_19_minimum_term_kn": None,
            "source_case_base_reaction_components_kn": {},
        }
