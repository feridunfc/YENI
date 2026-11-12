"""R06 — archived static vector versus non-concurrent spectrum demand audit.

Source-only replay; design authority remains denied. No ETABS, PMM or
reapplication of spectrum/directional amplification is performed.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from typing import Mapping

from .column_engine.native_archive import BankError, NativeArchive, digest
from .column_engine.demand_types import (
    PhysicalStaticForceState, SpectralComponentEnvelope,
    CodeDesignDemandCandidate, PERMUTATION_POLICY)
from .column_engine.source_bank import COMPONENTS
from .column_engine.spectral_design import build_design_population

SCHEMA = "tbdy.next.r06-native-demand-semantics.v1"
EXPECTED = {"members": 87, "native_rows": 34170, "cuts": 402,
            "static": 2412, "spectral_combos": 24,
            "pairs": 9648, "native_steps": 19296,
            "scalars": 115776, "signs": 77184}
SIGNS = {(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)}


class R06EvidenceError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise R06EvidenceError(reason)


def _receipts(bank, receipts):
    required = {"R01": "tbdy.next.r01-archived-source-acceptance.v1",
                "R02": "tbdy.next.r02-physical-analysis-ledger.v1",
                "R03": "tbdy.next.r03-unapproved-combobook.v1"}
    states = {}
    for key, schema in required.items():
        row = receipts.get(key)
        if row is None:
            states[key] = "NOT_SUPPLIED"
            continue
        require(isinstance(row, Mapping) and row.get("schema") == schema,
                key + "_RECEIPT_SCHEMA_INVALID")
        require(row.get("source_archive_sha256") == bank["source_archive_sha256"]
                and row.get("engineering_release") == "NOT_READY",
                key + "_FOREIGN_ARCHIVE_OR_RELEASE")
        if key == "R01":
            require(row.get("archive_run_id") == bank["run_id"]
                    and row.get("bank_zip_sha256") == receipts["bank_zip_sha256"]
                    and row.get("source_archive_file_reverified") is True
                    and row.get("analysis_generation_proven") is False
                    and row.get("static_replay", {}).get("status") == "INDEPENDENT_OFFLINE_NUMERICAL_MATCH"
                    and row.get("static_replay", {}).get("matched_rows") == EXPECTED["static"]
                    and row.get("static_replay", {}).get("component_comparisons") == EXPECTED["static"] * 6,
                    "R01_STATIC_REPLAY_NOT_SOURCE_BOUND")
        else:
            require(row.get("source_run_id") == bank["run_id"]
                    and row.get("source_bank_result_sha256") == bank["result_sha256"],
                    key + "_BANK_RUN_MISMATCH")
        if key == "R02":
            require(row.get("selected_physical_columns") == EXPECTED["members"]
                    and row.get("physical_joint_face_population_proven") is False
                    and row.get("analysis_generation_qualified") is False
                    and {m.get("physical_frame_id") for m in row.get("members", ())}
                    == {m["frame_name"] for m in bank["members"]},
                    "R02_ROSTER_OR_FALSE_PHYSICAL_PROOF")
        if key == "R03":
            require(row.get("execution_authority") == "DENIED"
                    and row.get("formal_compliance") == "NOT_PROVEN"
                    and row.get("case_count") == bank["defined_case_count"]
                    and row.get("combination_count") == bank["defined_combination_count"]
                    and all(c.get("design_role") is None
                            for c in row.get("cases", ()))
                    and all(v.get("source_name") is None
                            for v in row.get("normative_load_roles", {}).values()),
                    "R03_FALSE_DESIGN_ROLE_PROOF")
            unsigned = {k: v for k, v in row.items() if k != "candidate_graph_sha256"}
            sha = sha256(json.dumps(unsigned, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            require(sha == row.get("candidate_graph_sha256"),
                    "R03_GRAPH_CONTENT_CHANGED")
            combos = {x["name"]: x for x in bank["combination_definitions"]}
            require({x.get("source_name") for x in row.get("combinations", ())} == set(combos),
                    "R03_COMBINATION_ROSTER_CHANGED")
            for candidate in row["combinations"]:
                native = combos[candidate["source_name"]]
                require(candidate.get("operator") ==
                        {0: "LINEAR_ADD", 1: "ENVELOPE"}.get(native["operator"], "UNSUPPORTED_OPERATOR")
                        and len(candidate.get("terms", ())) == len(native["terms"]),
                        "R03_COMBINATION_OPERATOR_CHANGED")
                for actual, original in zip(candidate["terms"], native["terms"]):
                    require(actual["reference_kind"] ==
                            ("CASE" if original["type"] == 0 else "COMBINATION")
                            and actual["source_name"] == original["name"]
                            and actual["exact_factor"] == str(Fraction(str(original["factor"]))),
                            "R03_SOURCE_FACTOR_CHANGED")
        states[key] = "SAME_HISTORICAL_SOURCE_BOUND_NOT_NORMATIVE"
    return states


def review_r06_native_demand(bank: Mapping, archive: NativeArchive, *,
                             r01=None, r02=None, r03=None, bank_zip_sha256=None) -> dict:
    """Recompute exact VS26 typed population from the same immutable archive."""
    require(bank.get("schema") == "tbdy.next.column-source-bank.v1"
            and bank.get("source_archive_sha256") == archive.sha256
            and bank.get("source_mode") == "OFFLINE_RECORDED_ETABS",
            "BANK_ARCHIVE_SOURCE_MISMATCH")
    require(bank.get("engineering_release") == "NOT_READY"
            and bank.get("design_demand_authority") == "DENIED"
            and bank.get("analysis_generation_proven") is False
            and bank.get("all_building_columns_proven") is False,
            "BANK_FALSE_ENGINEERING_AUTHORITY")
    require(digest({k: v for k, v in bank.items() if k != "result_sha256"})
            == bank.get("result_sha256"), "BANK_CONTENT_SHA_MISMATCH")
    require(bank.get("selected_column_count") == EXPECTED["members"]
            and bank.get("force_row_count") == EXPECTED["native_rows"]
            and len(bank.get("members", ())) == EXPECTED["members"]
            and {m["frame_name"] for m in bank["members"]} == set(archive.selected),
            "PINNED_COLUMN_POPULATION_MISMATCH")

    relation = _receipts(bank, {"R01": r01, "R02": r02, "R03": r03,
                                "bank_zip_sha256": bank_zip_sha256})
    p = build_design_population(bank, archive)
    s, rep, chain = p.summary, p.replay, p.static_chain
    require(all(digest({k: v for k, v in x.items() if k != "result_sha256"})
                == x.get("result_sha256") for x in (s, rep, chain)),
            "SOURCE_DERIVATIVE_HASH_MISMATCH")
    require(s.get("source_run_id") == bank["run_id"]
            and s.get("source_archive_sha256") == archive.sha256
            and s.get("source_bank_result_sha256") == bank["result_sha256"],
            "SOURCE_DERIVATION_RUN_MISMATCH")
    require(s.get("construction_complete_for_recorded_scope") is True
            and s.get("selected_member_count") == EXPECTED["members"]
            and s.get("native_station_count") == EXPECTED["cuts"]
            and s.get("eligible_combination_count") == EXPECTED["spectral_combos"]
            and s.get("static_reference_count") == EXPECTED["static"]
            and s.get("envelope_count") == EXPECTED["pairs"]
            and s.get("candidate_count") == EXPECTED["signs"]
            and s.get("expected_candidate_count") == EXPECTED["signs"]
            and s.get("blocked_pair_count") == 0,
            "TYPED_DEMAND_POPULATION_INCOMPLETE")
    require(rep.get("matched_rows") == EXPECTED["native_steps"]
            and rep.get("scalar_comparisons") == EXPECTED["scalars"]
            and rep.get("over_tolerance_components") == 0
            and rep.get("unresolved_pair_count") == 0
            and rep.get("replay_status") == "NUMERICAL_MATCH",
            "NATIVE_SPECTRAL_COMPONENT_REPLAY_MISMATCH")
    require(s.get("physical_concurrency_proven") is False
            and s.get("continuous_axial_envelope_complete") is False
            and s.get("analysis_generation_qualified") is False
            and s.get("second_order_applied") is False
            and s.get("spectrum_scale_reapplied") is False
            and s.get("additional_directional_factor_applied") is False
            and s.get("design_demand_authority") == "DENIED"
            and s.get("normative_qualification") == "NOT_PROVEN",
            "SPECTRAL_CANDIDATES_FALSELY_AUTHORIZED")

    rows = {v["source_row_id"]: v for v in bank["force_states"]}
    require(len(rows) == EXPECTED["native_rows"], "SOURCE_ROW_IDS_NOT_UNIQUE")
    static_ids = set()
    statics = Counter()
    for state in p.static_states:
        require(type(state) is PhysicalStaticForceState
                and state.row.source_row_id in rows
                and state.row.step_type == "Single Value"
                and state.row.step_number == 0
                and state.row.source_row_id not in static_ids,
                "STATIC_SOURCE_TUPLE_NOT_UNIQUE")
        original = rows[state.row.source_row_id]
        cut = state.row.cut
        require((cut.member_id, cut.object_station_m, cut.element_id,
                 cut.element_station_m, state.row.output_case,
                 state.row.step_type, state.row.step_number)
                == tuple(original[k] for k in
                   ("Obj", "ObjSta", "Elm", "ElmSta", "LoadCase", "StepType", "StepNum"))
                and state.row.values == tuple(original[k] for k in COMPONENTS),
                "STATIC_N_M2_M3_DIFFERENT_CASE_OR_CUT")
        static_ids.add(state.row.source_row_id)
        statics[cut.member_id] += 1
    require(len(static_ids) == EXPECTED["static"], "SIGNED_STATIC_CENSUS_MISMATCH")

    envelope_map = {}
    for envelope in p.envelopes:
        require(type(envelope) is SpectralComponentEnvelope
                and envelope.envelope_id not in envelope_map
                and envelope.source_archive_sha256 == archive.sha256
                and envelope.source_run_id == bank["run_id"]
                and len(envelope.native_steps) == 2
                and {x.step_type for x in envelope.native_steps} == {"Max", "Min"}
                and digest(envelope._content()) == envelope.content_sha256,
                "STATISTICAL_ENVELOPE_IDENTITY_INVALID")
        envelope_map[envelope.envelope_id] = envelope
    signs = defaultdict(set)
    candidate_ids = set()
    per_member_signs = Counter()
    for candidate in p.candidates:
        require(type(candidate) is CodeDesignDemandCandidate
                and candidate.permutation_policy == PERMUTATION_POLICY
                and candidate.envelope is envelope_map.get(candidate.envelope.envelope_id)
                and candidate.signs in SIGNS
                and candidate.candidate_id not in candidate_ids,
                "CONDITIONAL_CANDIDATE_NOT_TYPED_OR_DUPLICATE")
        e = candidate.envelope
        n, m2, m3 = candidate.values
        require(n == -(e.center[0] + candidate.signs[0] * e.radius[0])
                and m2 == e.center[4] + candidate.signs[1] * e.radius[4]
                and m3 == e.center[5] + candidate.signs[2] * e.radius[5],
                "N_EQUALS_MINUS_NATIVE_P_OR_AXES_CONFLICT")
        candidate_ids.add(candidate.candidate_id)
        signs[e.envelope_id].add(candidate.signs)
        per_member_signs[e.cut.member_id] += 1
    require(len(candidate_ids) == EXPECTED["signs"]
            and set(signs) == set(envelope_map)
            and all(z == SIGNS for z in signs.values())
            and set(statics) == set(per_member_signs)
            == {m["frame_name"] for m in bank["members"]},
            "EIGHT_CORNER_OR_MEMBER_CENSUS_MISMATCH")

    out = {"schema": SCHEMA, "status": "SOURCE_DEMAND_SEMANTICS_RECONCILED_NORMATIVE_HOLD",
           "source_run_id": bank["run_id"], "source_archive_sha256": archive.sha256,
           "source_bank_result_sha256": bank["result_sha256"],
           "vs26_population_sha256": s["result_sha256"],
           "static_demand_chain_sha256": chain["result_sha256"],
           "spectral_native_replay_sha256": rep["result_sha256"],
           "r01_r02_r03": relation,
           "cross_slice_receipts_complete": all(v != "NOT_SUPPLIED" for v in relation.values()),
           "signed_native_static_states": len(static_ids),
           "matched_statistical_spectral_pairs": len(envelope_map),
           "matched_native_max_min_rows": rep["matched_rows"],
           "independent_component_comparisons": rep["scalar_comparisons"],
           "conditional_corner_candidates": len(candidate_ids),
           "member_census": [
               {"member_id": k, "signed_static_states": statics[k],
                "conditional_spectral_candidates": per_member_signs[k],
                "physical_joint_face_proven": False}
               for k in sorted(statics)],
           "force_meanings": {
               "static": "SAME_CASE_STEP_EXACT_OBJ_ELM_STATION_SIGNED_VECTOR",
               "spectrum": "INDEPENDENT_MAX_MIN_PER_COMPONENT_NOT_CONCURRENT",
               "candidate": "EXPLICIT_EIGHT_CORNER_CODE_CHECK_ONLY_NOT_PHYSICAL",
               "native_axial_P_positive": "TENSION",
               "domain_axial_N_positive": "COMPRESSION",
               "source_units": "kN_m_C"},
           "actual_design_demand_signed_vector_authorized": False,
           "full_building_column_population_proven": False,
           "analysis_generation_qualified": False,
           "continuous_axial_envelope_complete": False,
           "actual_second_order_applied": False,
           "design_demand_authority": "DENIED",
           "formal_compliance": "NOT_PROVEN",
           "engineering_release": "NOT_READY",
           "missing_authorities": [
               "ANALYSIS_GENERATION_AND_ALL_BUILDING_DENOMINATOR",
               "TBDY_4_4_VERTICAL_AND_DIRECTIONAL_COMBINATION_SCOPE",
               "SPECTRUM_SCALE_MASS_MODAL_AND_BETA_SOURCE",
               "PHYSICAL_JOINT_FACE_AND_MEMBER_END_BINDING",
               "SECOND_ORDER_AND_MINIMUM_ECCENTRICITY_NOT_APPLIED",
               "INTERMEDIATE_AXIAL_ENVELOPE_COMPLETENESS_NOT_PROVEN",
               "ACTUAL_SELECTED_REBAR_AND_INDEPENDENT_GOLDEN"],
           "pmm_solver_executed": False}
    out["result_sha256"] = digest(out)
    return out
