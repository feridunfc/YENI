"""VS06-C1: frozen TBDY 4.9 effective-drift readiness per physical story/direction.

Uses existing VS05 formula kernel, VS06-A/B source proofs, and the exact
94-node candidate DAG compiler/FCR. ETABS Story Drifts * h is a source
candidate, NOT an independently qualified Eq (4.32) member-end displacement.
No model-specific R/I, DD2/DD3, lambda, wall connection, generation or
concurrent displacement is inferred, and no normative PASS is issued.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from .compiled_dag import RegulatoryCompiler, assess_candidate_plan, canonical_json
from .normative_checks import directional_effective_drift_check
from .story_slot_ledger import build_story_slot_ledger
from .story_physical_source import review_story_physical_source

SCHEMA = "tbdy.next.vs06.effective-drift-readiness.v1"
PRIMARY_CASE = {"X": "RSX", "Y": "RSY"}
DAG_PARENTS = frozenset(("ANALYSIS_BASIS_GATE", "SEISMIC_DESIGN_BASIS"))


class EffectiveDriftReadinessError(ValueError):
    """Invalid or contradictory source/DAG/readiness evidence."""


def review_effective_drift_readiness(
    source: Mapping[str, Any],
    drift_record: Mapping[str, Any],
    slot_ledger: Mapping[str, Any],
    physical_review: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile *candidate* STORY_DIRECTION instances; execute zero formal checks."""
    verified_ledger = build_story_slot_ledger(source, drift_record)
    if not isinstance(slot_ledger, Mapping) or dict(slot_ledger) != verified_ledger:
        raise EffectiveDriftReadinessError("SOURCE_SLOT_LEDGER_NOT_VERIFIED")
    verified_physical = review_story_physical_source(
        source, drift_record, verified_ledger)
    if (not isinstance(physical_review, Mapping)
            or dict(physical_review) != verified_physical):
        raise EffectiveDriftReadinessError("PHYSICAL_SOURCE_REVIEW_NOT_VERIFIED")
    compiler = RegulatoryCompiler(catalog)
    dag_node = compiler.nodes.get("STORY_DRIFT")
    if (dag_node is None or dag_node.get("node_type") != "REGULATORY_CHECK"
            or dag_node.get("execution_authority") != "DENIED"
            or frozenset(dag_node.get("depends_on", [])) != DAG_PARENTS):
        raise EffectiveDriftReadinessError("DAG_STORY_DRIFT_DEPENDENCIES_CHANGED")

    slots = verified_ledger["slots"]
    physical_slots = verified_physical["slots"]
    physical_by_key = {(r["story"], r["case"], r["direction"]): r
                       for r in physical_slots}
    if len(physical_by_key) != len(physical_slots):
        raise EffectiveDriftReadinessError("DUPLICATE_PHYSICAL_SLOT")
    source_by_key = {(r["story"], r["case"], r["direction"]): r
                     for r in slots}
    if len(source_by_key) != len(slots) or set(source_by_key) != set(physical_by_key):
        raise EffectiveDriftReadinessError("STORY_SOURCE_SLOT_IDENTITY_CONFLICT")

    # Only primary RSX-X and RSY-Y define directional candidate grain.
    # Cross-direction RSX-Y and RSY-X remain visible source observations,
    # not extra instances or automatically combined design earthquake cases.
    chosen = sorted((slot for slot in slots
                     if slot["case"] == PRIMARY_CASE[slot["direction"]]),
                    key=lambda r: (r["story"], r["direction"]))
    stories = {r["story"] for r in verified_physical["observed_stories"]}
    if len(chosen) != 2 * len(stories):
        raise EffectiveDriftReadinessError("PRIMARY_STORY_DIRECTION_DENOMINATOR_MISMATCH")
    expected_instances = []
    submitted = []
    review_rows = []
    for slot in chosen:
        story, direction, case = slot["story"], slot["direction"], slot["case"]
        subject_id = direction + ":" + story
        instance_id = "STORY_DRIFT:" + subject_id
        expected_instances.append({
            "check_instance_id": instance_id,
            "node_id": "STORY_DRIFT",
            "subject_id": subject_id,
            "grain": "STORY_DIRECTION",
        })
        has_source = slot["source_status"] == "OBSERVED_SOURCE_NUMERIC"
        physical = physical_by_key[(story, case, direction)]
        if physical["source_status"] != slot["source_status"]:
            raise EffectiveDriftReadinessError("SOURCE_PHYSICAL_SLOT_MISMATCH")
        facts = {"direction": direction, "case": case, "story": story}
        # The existing VS05 normative kernel refuses formula execution
        # until the genuine evidence contract is satisfied.
        blocked = directional_effective_drift_check(facts, None)
        if (blocked["status"] != "NOT_PROVEN"
                or blocked["execution"] != "BLOCKED_BY_EVIDENCE"
                or blocked["calculation"] is not None
                or blocked["formal_compliance"] != "NOT_PROVEN"):
            raise EffectiveDriftReadinessError("NORMATIVE_FORMULA_UNEXPECTEDLY_EXECUTED")
        missing = list(blocked["missing_evidence"])
        missing.append("QUALIFIED_PHYSICAL_SIGNED_REDUCED_DELTA_NOT_AVAILABLE")
        if physical["member_presence_evidence"] == "NO_COLUMN_CONNECTIVITY_OBSERVED":
            missing.append("COMPLETE_PHYSICAL_OBJECT_CENSUS_REQUIRED_BEFORE_NOT_APPLICABLE")
        if not has_source:
            missing.append("ETABS_STORY_DRIFT_PRIMARY_SOURCE_MISSING")
        if has_source:
            # Observed means a source-numeric candidate exists. This is NOT
            # execution of an authorized normative candidate.
            submitted.append({"check_instance_id": instance_id,
                              "status": "NOT_PROVEN"})
        review_rows.append({
            "check_instance_id": instance_id, "dag_node_id": "STORY_DRIFT",
            "story": story, "direction": direction, "case": case,
            "source_numeric_status": slot["source_status"],
            "etabs_derived_delta_mm_candidate": slot["source_delta_mm"],
            "member_presence_evidence": physical["member_presence_evidence"],
            "physical_applicability": "NOT_PROVEN",
            "calculation_ready": False,
            "formula_execution": "BLOCKED_BY_EVIDENCE",
            "numerical_condition": "NOT_PROVEN",
            "regulatory_status": "NOT_PROVEN",
            "required_source_evidence": missing,
            "code_refs": ["TBDY 2018 4.9.1.1 Eq 4.32",
                          "TBDY 2018 4.9.1.2 Eq 4.33",
                          "TBDY 2018 4.9.1.3-4 Eq 4.34"],
        })
    plan = compiler.compile_candidate(
        model_profile=None, combo_book=None,
        expected_instances=expected_instances)
    fcr = assess_candidate_plan(plan, submitted)
    if (fcr["expected_count"] != len(chosen)
            or fcr["reconciled_count"] != len(chosen)
            or fcr["submitted_count"] != len(submitted)
            or fcr["missing_count"] != len(chosen)-len(submitted)
            or fcr["not_proven_count"] != len(chosen)
            or fcr["pass_count"] != 0 or fcr["fail_count"] != 0):
        raise EffectiveDriftReadinessError("EFFECTIVE_DRIFT_FCR_DENOMINATOR_CONFLICT")

    result = {
        "schema": SCHEMA,
        "check_id": "STORY_DRIFT",
        "dag_node_id": "STORY_DRIFT",
        "dag_node_type": "REGULATORY_CHECK",
        "dag_dependency_ids": sorted(DAG_PARENTS),
        "dag_execution_authority": "DENIED",
        "candidate_catalog_sha256": compiler.graph["catalog_sha256"],
        "candidate_plan_sha256": plan["plan_sha256"],
        "candidate_fcr_sha256": fcr["fcr_sha256"],
        "expected_story_direction_instances": len(chosen),
        "source_numeric_primary_instances": len(submitted),
        "source_missing_primary_instances": len(chosen)-len(submitted),
        "candidate_fcr_expected": fcr["expected_count"],
        "candidate_fcr_reconciled": fcr["reconciled_count"],
        "candidate_fcr_not_proven": fcr["not_proven_count"],
        "candidate_fcr_pass": fcr["pass_count"],
        "physical_census_approved": False,
        "analysis_generation_approved": False,
        "reduced_design_displacement_approved": False,
        "r_i_dd2_dd3_wall_basis_approved": False,
        "formula_executed_count": 0,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "check_instances": review_rows,
        "note": ("A source-numeric ETABS story drift is not the signed member-end "
                 "design displacement of Eq (4.32). Missing empty-story source "
                 "is not automatically NOT_APPLICABLE. This is a 94-node DAG "
                 "candidate FCR, never an authorized formula execution."),
    }
    result["readiness_sha256"] = sha256(canonical_json(result)).hexdigest()
    return result
