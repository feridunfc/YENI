"""VS26 source-bound sign candidates, separate from physical analysis states.

Only matched direct Linear Add envelopes with captured single global-axis RS
definitions enter this conditional CSI design convention. Existing static
states and their hashes remain unchanged. No code compliance is inferred from
combination names, coefficient patterns, or the eight generated corners.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction

from ..earthquake_combinations import coefficient_subcondition, companion_coverage
from .demand_chain import build_demand_chain
from .demand_types import (CaseContribution, CodeDesignDemandCandidate, NativeCut,
    PhysicalStaticForceState, RecordedForceRow, SpectralComponentEnvelope,
    PERMUTATION_POLICY, CSI_RULE, sign_candidates)
from .native_archive import BankError, digest
from .source_bank import COMPONENTS
from .spectral_envelope import build_spectral_envelopes, _source_ref

SCHEMA = "tbdy.next.spectral-design-population.v1"
VIEW = "spectral-design"
DETAIL_VIEW = "spectral-candidates"
REFERENCES = {
    "csi_design_convention": "https://docs.csiamerica.com/manuals/etabs/Concrete%20Frame%20Design/CFD-ACI-318-08.pdf",
    "csi_nonconcurrency": "https://wikicsiamerica.atlassian.net/wiki/spaces/kb/pages/2006323/Response-spectrum+analysis+FAQ",
    "tbdy_official": "https://www.aile.gov.tr/eyhgm/mevzuat/ulusal-mevzuat/yonetmelikler/turkiye-bina-deprem-yonetmeligi/",
    "tbdy_attachment": "https://www.aile.gov.tr/media/vixjx01s/deprem_yonetmelik_eki.docx",
    "tbdy_attachment_sha256": "122b7eea53099c42b5cb080f0a6fcff89bdea445d2b0e9005e9e8acae557db5d",
    "reference_algorithm": "https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/design/columns/design_demand_states.py",
}
BLOCKERS = (
    "TBDY_4_4_2_AND_4_10_PROJECT_DIRECTION_AND_COMMON_FACTOR_AUTHORITY",
    "TBDY_4_4_3_VERTICAL_APPLICABILITY_AND_SOURCE_ROLE_BINDING",
    "TBDY_4_4_4_GRAVITY_SNOW_EARTH_PRESSURE_AND_DESIGN_SELECTION",
    "ANNEX_4B_MODAL_MASS_SCALING_DAMPING_AND_ANALYSIS_GENERATION",
    "INTERMEDIATE_AXIAL_DEMAND_ENVELOPE_COMPLETENESS_NOT_PROVEN",
    "GLOBAL_P_DELTA_LOCAL_P_DELTA_AND_MINIMUM_ECCENTRICITY_NOT_APPLIED",
    "PROPOSED_REINFORCEMENT_NOT_SELECTED_OR_AS_BUILT",
)


@dataclass(frozen=True, slots=True)
class DesignPopulation:
    summary: dict
    replay: dict
    static_chain: dict
    static_states: tuple
    envelopes: tuple
    candidates: tuple
    blocked_pairs: tuple


def _construction_scope(combination):
    if combination["scope"] != "DIRECT_SPECTRAL_LINEAR_ADD":
        return combination["reason"]
    terms = combination["coefficient_context"]["spectral_terms"]
    if not 1 <= len(terms) <= 2:
        return "SIGN_POLICY_REQUIRES_ONE_OR_TWO_SINGLE_GLOBAL_AXIS_SPECTRA"
    if any(t["global_axis"] not in ("U1", "U2") for t in terms):
        return "SPECTRUM_GLOBAL_DIRECTION_NOT_SOURCE_BOUND"
    if len({t["global_axis"] for t in terms}) != len(terms):
        return "REPEATED_SPECTRUM_DIRECTION_OUTSIDE_SIGN_POLICY"
    return None


def _direction_diagnostics(combinations):
    """Reuse VS10's exact coefficient and companion logic, never name parsing."""
    items = []
    for combination in combinations:
        if _construction_scope(combination) is not None:
            continue
        terms = combination["coefficient_context"]["spectral_terms"]
        factors = {t["global_axis"]: t["factor"] for t in terms}
        try:
            row = {"combination": combination["combination"],
                **coefficient_subcondition(factors.get("U1", 0), factors.get("U2", 0))}
            rs_names = {t["case_name"] for t in terms}
            others = {t["name"]: str(Fraction(str(t["factor"])))
                for t in combination["definition"]["terms"] if t["name"] not in rs_names}
            # Identity of both horizontal cases belongs to the context too.
            row.update(other_case_coefficients=others,
                context_sha256=digest({"cases": sorted((t["global_axis"], t["case_name"]) for t in terms),
                    "other": others, "common_factor": row["common_factor"]}))
        except ValueError as exc:
            row = {"combination": combination["combination"], "status": "NOT_PROVEN", "reason": str(exc)}
        items.append(row)
    return {"coefficient_checks": items, "companion_groups": companion_coverage(items),
        "scope": "CAPTURED_COEFFICIENT_SUBCONDITIONS_ONLY", "normative_qualification": "NOT_PROVEN",
        "additional_100_30_applied": False, "common_factor_interpreted_as_D": False}


def _static_definition_facts(bank, archive):
    facts = []
    names = {t["name"] for c in bank["combination_definitions"] for t in c.get("terms", []) if t.get("type") == 0}
    for case in bank["case_definitions"]:
        if case.get("case_type") != 1 or case["name"] not in names:
            continue
        item = {"case_name": case["name"], "case_definition": deepcopy(case),
            "load_definition": None, "reason": None, "project_action_role": "NOT_PROVEN"}
        try:
            observed = archive.native("LoadCases.StaticLinear.GetLoads", "case", case["name"])
            if observed is None:
                raise BankError("STATIC_LOAD_DEFINITION_NOT_OBSERVED")
            item["load_definition"] = {"values": observed[0], "source": observed[1]}
        except (ValueError, KeyError, TypeError) as exc:
            item["reason"] = str(exc)
        facts.append(item)
    return facts


def build_design_population(bank, archive):
    """Re-read native evidence here; a caller-supplied matched flag is no proof."""
    replay = build_spectral_envelopes(bank, archive)
    chain = build_demand_chain(bank, archive)
    rows_by_id = {r["source_row_id"]: r for r in bank["force_states"]}
    static = tuple(PhysicalStaticForceState(s["state_id"], archive.sha256, chain["result_sha256"],
        RecordedForceRow.from_ref(_source_ref(rows_by_id[s["source_row_id"]]))) for s in chain["candidates"])
    combinations = {c["combination"]: c for c in replay["combinations"]}
    envelopes, candidates, blocked = [], [], []
    for row in replay["rows"]:
        reason = (_construction_scope(combinations[row["output_case"]])
            or ("CAPTURE_CONTEXT_UNRESOLVED" if not replay["capture_context_observed"] else None)
            or (row["reason"] or row["status"] if row["status"] != "NUMERICAL_MATCH" else None))
        if reason:
            blocked.append({"envelope_id": row["result_id"], "member_id": row["member_id"],
                "source_combination": row["output_case"], "station_key": row["station_key"], "reason": reason})
            continue
        envelope = SpectralComponentEnvelope(row["result_id"], bank.get("run_id"), archive.sha256,
            replay["result_sha256"], NativeCut.from_key(row["station_key"]), row["output_case"],
            tuple(row["center"][c] for c in COMPONENTS), tuple(row["spectral_radius"][c] for c in COMPONENTS),
            tuple(CaseContribution(t["case_type"], t["factor"], RecordedForceRow.from_ref(t)) for t in row["source_terms"]),
            tuple(RecordedForceRow.from_ref(t) for t in row["native_steps"]))
        envelopes.append(envelope); candidates.extend(sign_candidates(envelope))
    classifications = []
    routes = {c["combination"]: c for c in chain["combinations"]}
    for combo in replay["combinations"]:
        reason = _construction_scope(combo)
        classifications.append({"combination": combo["combination"],
            "classification": routes[combo["combination"]]["classification"],
            "replay_scope": combo["scope"], "sign_construction_scope": "SUPPORTED_CONDITIONAL" if reason is None else "OUTSIDE_RECIPE",
            "reason": reason, "recorded_terms": deepcopy(combo["definition"].get("terms", [])),
            "expected_pairs": combo["expected_pair_count"], "matched_rows": combo["matched_rows"],
            "unresolved_pairs": combo["unresolved_pair_count"], "mismatched_rows": combo["mismatched_rows"]})
    summary = {"schema": SCHEMA, "source_run_id": bank.get("run_id"), "source_archive_sha256": archive.sha256,
        "source_bank_result_sha256": bank["result_sha256"], "source_replay_result_sha256": replay["result_sha256"],
        "source_static_demand_result_sha256": chain["result_sha256"],
        "static_reference_count": len(static), "static_reference_identity_sha256": digest([s.state_id for s in static]),
        "static_reference_content_sha256": digest([s.as_dict() for s in static]),
        "selected_member_count": len(bank["members"]), "native_station_count": replay["known_station_count"],
        "eligible_combination_count": replay["eligible_combination_count"], "envelope_count": len(envelopes),
        "candidate_count": len(candidates), "expected_candidate_count": 8*replay["expected_pair_count"],
        "candidate_identity_sha256": digest([c.candidate_id for c in candidates]),
        "envelope_content_identity_sha256": digest([e.content_sha256 for e in envelopes]),
        "blocked_pair_count": len(blocked), "blocked_reason_counts": dict(Counter(r["reason"] for r in blocked)),
        "construction_complete_for_recorded_scope": bool(candidates) and not blocked
            and replay["source_coverage_status"] == "SOURCE_COVERAGE_COMPLETE",
        "permutation_policy": PERMUTATION_POLICY, "applicable_design_rule": CSI_RULE,
        "rule_application": "CONDITIONAL_CSI_CONVENTION_NOT_TBDY_APPROVAL",
        "classifications": classifications, "direction_diagnostics": _direction_diagnostics(replay["combinations"]),
        "static_load_definition_facts": _static_definition_facts(bank, archive),
        "references": REFERENCES.copy(), "members": [{"member_id": m["frame_name"],
            "story": m.get("context", {}).get("frame", {}).get("story_label"),
            "column_label": m.get("context", {}).get("frame", {}).get("column_label")} for m in bank["members"]],
        "additional_directional_factor_applied": False, "spectrum_scale_reapplied": False,
        "second_order_applied": False, "minimum_eccentricity_applied": False,
        "physical_concurrency_proven": False, "analysis_generation_id": None,
        "analysis_generation_qualified": False, "continuous_axial_envelope_complete": False,
        "normative_qualification": "NOT_PROVEN", "design_demand_authority": "DENIED",
        "engineering_release": "NOT_READY", "final_design_eligible": False, "blockers": list(BLOCKERS)}
    summary["result_sha256"] = digest(summary)
    return DesignPopulation(summary, replay, chain, static, tuple(envelopes), tuple(candidates), tuple(blocked))
