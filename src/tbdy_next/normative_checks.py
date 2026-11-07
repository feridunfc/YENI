"""VS05 — TBDY 2018 directional base-shear and effective-drift rule kernels.

Independent, deterministic calculations, with explicit engineering source
prerequisites. This is *not yet* an authorized production code-check adapter:
self-asserted evidence booleans are never equivalent to independent model,
analysis, ETABS case/scaling or applied design proof. All outputs retain
formal_compliance=NOT_PROVEN and engineering_release=NOT_READY.

References: TBDY 2018 4.7.1.1 Eq 4.19, 4.8.4.1 Eq 4.31,
4.9.1.1-4 Eq 4.32-4.34 and 4.9.1.4 lambda.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping

from .normative_basis import (
    eq_4_19_equivalent_base_shear_kn,
    eq_4_31_base_scale,
    eq_4_34_effective_drift,
    eq_4_9_lambda,
    UnqualifiedEngineeringInput,
)

BASE_PROOFS = (
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
DRIFT_PROOFS = (
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


def _decimal(value: Any, name: str, *, allow_zero: bool = False,
             allow_signed: bool = False) -> Decimal:
    if type(value) not in (str, int, Decimal):
        raise UnqualifiedEngineeringInput(name + ": INVALID_NUMBER_TYPE")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise UnqualifiedEngineeringInput(name + ": INVALID_DECIMAL") from None
    if not d.is_finite() or (not allow_signed and
                            (d < 0 if allow_zero else d <= 0)):
        raise UnqualifiedEngineeringInput(name + ": NONFINITE_OR_SIGN")
    return d


def _basis(rule: str, direction: str, code: str, proof_fields: tuple[str, ...],
           evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    missing = [key for key in proof_fields
               if not isinstance(evidence, Mapping) or evidence.get(key) is not True]
    refs = (evidence or {}).get("source_refs") if isinstance(evidence, Mapping) else None
    if (not isinstance(refs, dict) or not all(isinstance(refs.get(k), str)
            and refs[k].strip() for k in ("model_generation", "analysis_case",
                                        "source_receipt", "independent_oracle"))):
        missing.append("exact_source_refs_and_independent_oracle")
    return {
        "check_id": rule + "_" + direction,
        "code_ref": code, "direction": direction,
        "applicability": "NOT_REVIEWED",
        "execution": "BLOCKED_BY_EVIDENCE",
        "numerical_condition": "NOT_PROVEN",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "status": "NOT_PROVEN",
        "source_only": True,
        "coverage": {"required_proof_count": len(proof_fields) + 1,
                     "proven_proof_count": len(proof_fields) + 1 - len(missing)},
        "missing_evidence": missing,
        "formula_inputs": {},
        "calculation": None,
        "source_refs": refs if isinstance(refs, dict) else {},
        "note": "Calculation does not authorize full building/regulatory compliance.",
    }


def _source_reference_mismatches(
    facts: Mapping[str, Any], evidence: Mapping[str, Any] | None
) -> list[str]:
    refs = (evidence or {}).get("source_refs") if isinstance(evidence,Mapping) else None
    if not isinstance(refs,Mapping):
        return ["SOURCE_REFERENCE_IDENTITY_NOT_AVAILABLE"]
    reasons=[]
    if refs.get("analysis_case") != facts.get("case"):
        reasons.append("ANALYSIS_CASE_SOURCE_REFERENCE_MISMATCH")
    if (not isinstance(facts.get("model_generation_id"),str)
            or not facts["model_generation_id"] or
            refs.get("model_generation") != facts["model_generation_id"]):
        reasons.append("MODEL_ANALYSIS_GENERATION_REFERENCE_MISMATCH")
    return reasons


def _valid_case(direction: str, payload: Mapping[str, Any]) -> None:
    required = "RSX" if direction == "X" else "RSY"
    if payload.get("direction") != direction or payload.get("case") != required:
        raise UnqualifiedEngineeringInput("CASE_OR_DIRECTION_SOURCE_IDENTITY_MISMATCH")


def directional_base_shear_check(facts: Mapping[str, Any] | None,
                                 evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compute full Eq 4.19 and Eq 4.31 without inventing missing authorities.

    The reported numerical condition is **applied beta >= required beta**.
    This is a single bounded condition, not a complete structural design PASS.
    """
    direction = (facts or {}).get("direction") if isinstance(facts, Mapping) else None
    if direction not in ("X", "Y"):
        direction = "UNKNOWN"
    base = _basis("base_shear", direction, "TBDY 2018 4.7.1.1 / 4.8.4.1",
                  BASE_PROOFS, evidence)
    if not isinstance(facts, Mapping):
        base["missing_evidence"].append("directional_base_shear_facts")
        return base
    try:
        _valid_case(direction, facts)
        base["missing_evidence"].extend(_source_reference_mismatches(facts,evidence))
        irregularities = facts.get("a1_b2_b3")
        if (not isinstance(irregularities, Mapping) or
                set(irregularities) != {"A1", "B2", "B3"} or
                any(irregularities[k] not in ("PRESENT", "ABSENT")
                    for k in ("A1", "B2", "B3"))):
            raise UnqualifiedEngineeringInput("FULL_A1_B2_B3_CLASSIFICATION_REQUIRED")
        if base["missing_evidence"]:
            return base
        gamma_any = any(irregularities[k] == "PRESENT" for k in ("A1", "B2", "B3"))
        mass = _decimal(facts.get("seismic_mass_kg"), "m_t")
        sar = _decimal(facts.get("sar_dd2_at_tp_m_s2"), "SaR_DD2_at_Tp")
        importance = _decimal(facts.get("importance_I"), "I")
        sds = _decimal(facts.get("sds_dd2"), "SDS_DD2")
        modal = _decimal(facts.get("vtx_pre_beta_kn"), "Vtx_PRE_BETA")
        applied = _decimal(facts.get("applied_beta"), "APPLIED_BETA")
        # Tp must be explicitly qualified even though Eq 4.19 uses SaR(Tp).
        period = _decimal(facts.get("qualified_tp_s"), "T_p")
        with localcontext() as ctx:
            ctx.prec = 35
            vte = eq_4_19_equivalent_base_shear_kn(
                seismic_mass_kg=mass,
                reduced_spectral_acceleration_m_s2=sar,
                importance_factor=importance,sds_dd2=sds)
            beta = eq_4_31_base_scale(
                equivalent_base_shear_kn=vte["equivalent_base_shear_kn"],
                modal_base_shear_kn=modal,
                irregularity_A1_B2_B3_any=gamma_any,
                irregularity_inventory_complete=True,
                basement_boundary_qualified=True)
            target = Decimal(beta["required_scale_factor"])
            met = applied >= target
        return {
            **base,
            "applicability": "APPLICABLE_SOURCE_ASSERTED",
            "execution": "EXECUTED_NUMERIC_FORMULA",
            "status": ("MEETS_NUMERICAL_CRITERION" if met else
                       "DOES_NOT_MEET_NUMERICAL_CRITERION"),
            "numerical_condition": ("APPLIED_SCALE_AT_LEAST_REQUIRED" if met else
                                    "APPLIED_SCALE_BELOW_REQUIRED"),
            "formula_inputs": {
                "qualified_tp_s": str(period),
                "seismic_mass_kg": str(mass),
                "sar_dd2_at_tp_m_s2": str(sar),
                "importance_I": str(importance),
                "sds_dd2": str(sds),
                "vtx_pre_beta_kn": str(modal),
                "applied_beta": str(applied),
                "irregularities": dict(irregularities),
            },
            "calculation": {**vte, **beta, "applied_beta":str(applied)},
            "note": ("Formula checked against source-asserted evidence; "
                     "independent model/analysis/source authorization "
                     "remains a separate production acceptance."),
        }
    except (UnqualifiedEngineeringInput, ValueError, InvalidOperation,
            ZeroDivisionError, KeyError, TypeError) as exc:
        base["missing_evidence"].append(str(exc))
        return base


def directional_effective_drift_check(facts: Mapping[str, Any] | None,
                                      evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """Maximum physical member-end drift per story, not ETABS 'Drift/' display.

    Δ_i = u_i - u_(i-1); δ_i = (R/I) Δ_i; λ=DD3_Sae(Tp)/DD2_Sae(Tp);
    λ max(|δ_i|)/h_i <= (0.008 or 0.016)*κ.
    """
    direction = (facts or {}).get("direction") if isinstance(facts, Mapping) else None
    if direction not in ("X","Y"):
        direction = "UNKNOWN"
    base = _basis("effective_drift",direction,
                  "TBDY 2018 4.9.1.1-4.9.1.4",
                  DRIFT_PROOFS,evidence)
    if not isinstance(facts,Mapping):
        base["missing_evidence"].append("directional_story_drift_facts")
        return base
    try:
        _valid_case(direction,facts)
        base["missing_evidence"].extend(_source_reference_mismatches(facts,evidence))
        if base["missing_evidence"]:
            return base
        level = facts.get("story")
        if not isinstance(level,str) or not level.strip():
            raise UnqualifiedEngineeringInput("PHYSICAL_STORY_ID_MISSING")
        height = _decimal(facts.get("story_height_m"),"h_i")
        r_value = _decimal(facts.get("R"),"R")
        imp = _decimal(facts.get("importance_I"),"I")
        sae3 = _decimal(facts.get("sae_dd3_at_same_tp_m_s2"),"DD3_SAE")
        sae2 = _decimal(facts.get("sae_dd2_at_same_tp_m_s2"),"DD2_SAE")
        tp = _decimal(facts.get("qualified_tp_s"),"Tp")
        members = facts.get("members")
        if not isinstance(members,list) or not members:
            raise UnqualifiedEngineeringInput("PHYSICAL_MEMBER_CENSUS_EMPTY")
        seen=set()
        member_rows=[]
        for row in members:
            if not isinstance(row,Mapping):
                raise UnqualifiedEngineeringInput("MEMBER_ROW_INVALID")
            ident=row.get("member_id")
            if not isinstance(ident,str) or not ident or ident in seen:
                raise UnqualifiedEngineeringInput("DUPLICATE_OR_INVALID_PHYSICAL_MEMBER_ID")
            seen.add(ident)
            upper=_decimal(row.get("u_upper_m"),"u_i",allow_signed=True)
            lower=_decimal(row.get("u_lower_m"),"u_i_minus_1",allow_signed=True)
            # Signed local displacements are valid. Preserve signs until
            # computing the absolute interstorey member-end difference.
            member_rows.append((ident,upper-lower))
        max_member,max_delta=max(member_rows,key=lambda row:abs(row[1]))
        lam=Decimal(eq_4_9_lambda(sae_dd3_m_s2=sae3,sae_dd2_m_s2=sae2))
        material=facts.get("material")
        wall=facts.get("wall_connection")
        flexible=facts.get("flexible_wall_capacity_documented") is True
        with localcontext() as ctx:
            ctx.prec=35
            # The base kernel requires delta>0. Zero physical drift is valid,
            # so handle that boundary explicitly without dividing by zero.
            if max_delta == 0:
                if material not in ("RC","STEEL"):
                    raise UnqualifiedEngineeringInput("UNSUPPORTED_MATERIAL")
                if wall not in ("ADHERED_BRITTLE","DOCUMENTED_FLEXIBLE"):
                    raise UnqualifiedEngineeringInput("WALL_CONNECTION_NOT_QUALIFIED")
                if wall=="DOCUMENTED_FLEXIBLE" and not flexible:
                    raise UnqualifiedEngineeringInput("FLEXIBLE_WALL_CAPACITY_NOT_DOCUMENTED")
                kappa=Decimal(1) if material=="RC" else Decimal("0.5")
                limit=(Decimal("0.008") if wall=="ADHERED_BRITTLE"
                       else Decimal("0.016"))*kappa
                calc={"effective_relative_displacement_m":"0",
                      "lambda_effective_drift_over_height":"0",
                      "limit":str(limit),"kappa":str(kappa)}
            else:
                calc=eq_4_34_effective_drift(
                    reduced_relative_displacement_m=abs(max_delta),
                    story_height_m=height,R=r_value,importance_factor=imp,
                    lambda_dd3_dd2=lam,
                    material=material,wall_connection=wall,
                    flexible_wall_capacity_documented=flexible)
            ratio=Decimal(calc["lambda_effective_drift_over_height"])
            limit=Decimal(calc["limit"])
        return {**base,"applicability":"APPLICABLE_SOURCE_ASSERTED",
                "execution":"EXECUTED_NUMERIC_FORMULA",
                "status":("MEETS_NUMERICAL_CRITERION" if ratio <= limit else
                          "DOES_NOT_MEET_NUMERICAL_CRITERION"),
                "numerical_condition":("MAX_EFFECTIVE_DRIFT_WITHIN_LIMIT" if ratio <= limit else
                                       "MAX_EFFECTIVE_DRIFT_EXCEEDS_LIMIT"),
                "formula_inputs":{
                    "story":level,"qualified_tp_s":str(tp),
                    "story_height_m":str(height),"R":str(r_value),
                    "importance_I":str(imp),"lambda_dd3_dd2":str(lam),
                    "material":material,"wall_connection":wall,
                    "complete_member_count":len(members),
                    "flexible_wall_capacity_documented":flexible,
                },
                "calculation":{**calc,"critical_member_id":max_member,
                               "maximum_reduced_relative_displacement_m":str(abs(max_delta)),
                               "member_count":len(members)},
                "note": ("Numerical stage uses member-end displacement differences. "
                         "No ETABS Drift/ direct semantics or overall building "
                         "code compliance is inferred."),
               }
    except (UnqualifiedEngineeringInput,ValueError,InvalidOperation,
            ZeroDivisionError,KeyError,TypeError) as exc:
        base["missing_evidence"].append(str(exc))
        return base
