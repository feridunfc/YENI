"""VS26 adapter to the existing VS25 fixed-N/fixed-direction capacity solver.

All identities survive exact numeric memoization. Evidence is compressed in
process memory and emitted separately in the forensic export; the native ZIP
and SQLite are never changed. Selection is the maximum *resolved* ratio among
the finite generated candidates, not a proof over an axial-force continuum.
"""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import zlib

from .column_pmm import DIAMETERS, OPEN_BASIS, POLICY as CAGE_POLICY, _section, cage_rows
from .csi_geometry import AXIS_CONVENTION
from .demand_types import CodeDesignDemandCandidate, pmm_arguments
from .native_archive import BankError, canonical, decode, digest
from .section_capacity import (ANGLE_COUNTS, DIRECTION_MAX_ITERATIONS, DIRECTION_TOL_NMM,
    FORCE_TOL_N, MAX_ANGLE_COUNT, MOMENT_ABS_TOL_NMM, MOMENT_REL_TOL, RADIAL_BASIS, solver)
from .spectral_design import DesignPopulation, BLOCKERS

SCHEMA = "tbdy.next.spectral-pmm-scenarios.v1"
GOVERNING_BASIS = "MAX_RESOLVED_RADIAL_RATIO_AMONG_ALL_RECORDED_CUTS_AND_EIGHT_SIGN_CANDIDATES"
RESOLVED = frozenset(("WITHIN_SCENARIO_SURFACE", "EXCEEDS_SCENARIO_SURFACE", "AXIAL_ONLY_SCENARIO"))


@dataclass(frozen=True, slots=True)
class Evaluation:
    candidate: CodeDesignDemandCandidate
    cage_id: str | None
    cage_label: str
    evidence_id: str | None
    status: str
    reason: str | None
    utilization: float | None
    radial_capacity_kNm: float | None
    axial_utilization: float | None

    @property
    def evaluation_id(self):
        return digest({"schema": SCHEMA, "candidate": self.candidate.candidate_id,
            "cage": self.cage_id, "label": self.cage_label, "evidence": self.evidence_id,
            "status": self.status, "reason": self.reason})

    def as_dict(self, *, detailed=False):
        candidate = self.candidate
        row = {"evaluation_id": self.evaluation_id, "candidate_id": candidate.candidate_id,
            "member_id": candidate.envelope.cut.member_id,
            "combination": candidate.envelope.combination, "station_key": candidate.envelope.cut.as_dict(),
            "sign_id": candidate.sign_id, "forces": dict(zip(("N_kN", "M2_kNm", "M3_kNm"), candidate.values)),
            "cage_id": self.cage_id, "reinforcement": self.cage_label,
            "numerical_status": self.status, "reason": self.reason,
            "conditional_pmm_ratio": self.utilization, "radial_capacity_kNm": self.radial_capacity_kNm,
            "axial_utilization": self.axial_utilization, "numerical_evidence_id": self.evidence_id,
            "engineering_status": "CONDITIONAL", "final_design_eligible": False,
            "second_order_applied": False, "normative_qualification": "NOT_PROVEN"}
        if detailed:
            row["design_candidate"] = candidate.as_dict()
        return row


@dataclass(frozen=True, slots=True)
class SpectralPMM:
    summary: dict
    population: DesignPopulation
    cages: dict
    rows: tuple
    evidence: dict
    sections: dict

    def evidence_record(self, evidence_id):
        return decode(zlib.decompress(self.evidence[evidence_id]))


def _cage_reason(cage):
    if cage["geometry_status"] != "PROPOSED_GEOMETRY_CALCULATED":
        return cage.get("reason") or "PROPOSED_GEOMETRY_NOT_BOUND"
    if cage["area_ratio_status"] != "WITHIN_1_TO_4_PERCENT_REFERENCE":
        return "PROPOSED_AREA_OUTSIDE_REFERENCE"
    if cage["spacing_status"] == "BELOW_SPACING_REFERENCE":
        return "PROPOSED_SPACING_BELOW_REFERENCE"
    if not cage["tie_diameter_reference_met"]:
        return "PROPOSED_TIE_DIAMETER_BELOW_REFERENCE"
    return None


def summarize_group(rows, *, source_complete):
    """Failures remain independent of a small resolved ratio; no PASS output."""
    counts = Counter(r.status for r in rows)
    numeric = [r for r in rows if r.utilization is not None]
    maximum = max((r.utilization for r in numeric), default=None)
    critical = [r for r in numeric if r.utilization == maximum]
    failures = [r for r in rows if r.status not in RESOLVED]
    return {"assessment_count": len(rows), "status_counts": dict(counts),
        "maximum_resolved_conditional_ratio": maximum,
        "governing_resolved": critical[0].as_dict() if critical else None,
        "governing_resolved_tie_count": len(critical),
        "unresolved_or_axial_outside_count": len(failures),
        "first_unresolved_or_axial_outside": failures[0].as_dict() if failures else None,
        "numerical_selection_complete": bool(rows) and source_complete and not failures,
        "selection_basis": GOVERNING_BASIS,
        "selection_scope": "FINITE_GENERATED_CANDIDATES_ONLY",
        "continuous_axial_envelope_complete": False, "engineering_status": "CONDITIONAL",
        "second_order_status": "NOT_APPLIED_NOT_PROVEN", "normative_qualification": "NOT_PROVEN",
        "final_design_eligible": False}


def build_spectral_pmm(population, cages, *, progress=None):
    if type(population) is not DesignPopulation:
        raise BankError("TYPED_DESIGN_POPULATION_REQUIRED")
    parent = population.summary
    if (digest({k: v for k, v in parent.items() if k != "result_sha256"}) != parent["result_sha256"]
            or digest({k: v for k, v in population.replay.items() if k != "result_sha256"}) != parent["source_replay_result_sha256"]
            or len(population.envelopes) != parent["envelope_count"]
            or digest([e.content_sha256 for e in population.envelopes]) != parent["envelope_content_identity_sha256"]
            or any(digest(e._content()) != e.content_sha256 for e in population.envelopes)
            or digest([s.as_dict() for s in population.static_states]) != parent["static_reference_content_sha256"]):
        raise BankError("SPECTRAL_PMM_POPULATION_CONTENT_MISMATCH")
    envelope_map = {e.envelope_id: e for e in population.envelopes}
    if (cages.get("axis_convention") != AXIS_CONVENTION
            or cages["source_archive_sha256"] != parent["source_archive_sha256"]
            or cages["source_demand_result_sha256"] != parent["source_static_demand_result_sha256"]
            or cages["source_run_id"] != parent["source_run_id"]
            or digest({k: v for k, v in cages.items() if k != "result_sha256"}) != cages["result_sha256"]):
        raise BankError("SPECTRAL_PMM_CAGE_BINDING_MISMATCH")
    if (len(population.candidates) != parent["candidate_count"]
            or digest([c.candidate_id for c in population.candidates]) != parent["candidate_identity_sha256"]
            or any(type(c) is not CodeDesignDemandCandidate
                or c.envelope.source_archive_sha256 != parent["source_archive_sha256"]
                or c.envelope.source_replay_result_sha256 != parent["source_replay_result_sha256"]
                or c.envelope != envelope_map.get(c.envelope.envelope_id)
                for c in population.candidates)):
        raise BankError("SPECTRAL_PMM_CANDIDATE_BINDING_MISMATCH")
    profiles = {p["profile_id"]: p for p in cages["profiles"]}
    proposals, sections, section_keys = defaultdict(list), {}, {}
    for cage in cage_rows(cages):
        proposals[cage["member_id"]].append(cage)
        if _cage_reason(cage) is None:
            section = _section(profiles[cage["profile_id"]], cage)
            section_id = digest(asdict(section))
            sections[section_id] = asdict(section)
            section_keys[cage["candidate_id"]] = (section_id, section)
    if set(proposals) != {m["member_id"] for m in parent["members"]}:
        raise BankError("SPECTRAL_PMM_MEMBER_POPULATION_MISMATCH")
    by_member = defaultdict(list)
    for candidate in population.candidates:
        by_member[candidate.envelope.cut.member_id].append(candidate)
    rows, evidence, memo = [], {}, {}
    for index, member in enumerate(parent["members"]):
        name = member["member_id"]
        for candidate in by_member[name]:
            args = pmm_arguments(candidate)
            for cage in proposals[name]:
                reason = _cage_reason(cage)
                numeric = {"status": "BLOCKED_INPUTS", "reason": reason, "utilization": None,
                    "radial_capacity_kNm": None, "axial_utilization": None}
                evidence_id = None
                if reason is None:
                    section_id, section = section_keys[cage["candidate_id"]]
                    # Exact signed inputs + complete section. No quantization,
                    # axial monotonicity, symmetry pruning or corner reduction.
                    key = (section_id, *args)
                    if key not in memo:
                        try:
                            full = solver(section).assess(*args)
                        except (ValueError, OverflowError) as exc:
                            full = {**numeric, "status": "NUMERIC_UNRESOLVED", "reason": str(exc)}
                        record = {"section_id": section_id, "N_N": args[0], "M2_Nmm": args[1],
                            "M3_Nmm": args[2], "solver_revision": "VS25_DIRECTION_ROOT", "result": full}
                        evidence_id = digest(record)
                        evidence[evidence_id] = zlib.compress(canonical(record), 1)
                        memo[key] = (evidence_id, {k: full.get(k) for k in
                            ("status", "reason", "utilization", "radial_capacity_kNm", "axial_utilization")})
                    evidence_id, numeric = memo[key]
                rows.append(Evaluation(candidate, cage["candidate_id"], cage["label"], evidence_id,
                    numeric["status"], numeric["reason"], numeric["utilization"],
                    numeric["radial_capacity_kNm"], numeric["axial_utilization"]))
        if progress:
            progress(index+1, len(parent["members"]), len(rows), len(evidence))
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.candidate.envelope.cut.member_id, row.cage_label)].append(row)
    members = []
    for cage in cage_rows(cages):
        group = grouped[cage["member_id"], cage["label"]]
        complete = parent["construction_complete_for_recorded_scope"]
        members.append({"member_id": cage["member_id"], "story": cage["story"],
            "column_label": cage.get("column_label"), "reinforcement": cage["label"],
            "cage_id": cage["candidate_id"], "area_cm2": cage.get("as_cm2"),
            **summarize_group(group, source_complete=complete)})
    summary = {"schema": SCHEMA, "source_run_id": parent["source_run_id"],
        "source_archive_sha256": parent["source_archive_sha256"],
        "source_population_result_sha256": parent["result_sha256"],
        "source_cages_result_sha256": cages["result_sha256"],
        "source_static_demand_result_sha256": parent["source_static_demand_result_sha256"],
        "candidate_count": len(population.candidates), "assessment_count": len(rows),
        "expected_assessment_count": parent["expected_candidate_count"]*len(DIAMETERS),
        "unique_numeric_problem_count": len(memo), "evaluation_identity_sha256": digest([r.evaluation_id for r in rows]),
        "numeric_evidence_identity_sha256": digest(sorted(evidence)), "members": members,
        "status_counts": dict(Counter(r.status for r in rows)),
        "reason_counts": dict(Counter(r.reason for r in rows if r.reason)),
        "selection_basis": GOVERNING_BASIS, "selection_scope": "FINITE_GENERATED_CANDIDATES_ONLY",
        "numeric_memo_policy": "EXACT_FULL_SECTION_AND_SIGNED_N_M2_M3_NO_IDENTITY_REDUCTION",
        "numerical_policy": {"solver_revision": "VS25_DIRECTION_ROOT", "basis": RADIAL_BASIS,
            "initial_angle_counts": list(ANGLE_COUNTS), "maximum_angle_count": MAX_ANGLE_COUNT,
            "axial_tolerance_n": FORCE_TOL_N, "moment_absolute_tolerance_nmm": MOMENT_ABS_TOL_NMM,
            "moment_relative_tolerance": MOMENT_REL_TOL, "direction_absolute_tolerance_nmm": DIRECTION_TOL_NMM,
            "direction_maximum_iterations": DIRECTION_MAX_ITERATIONS,
            "continuous_error_bound_proven": False, "global_root_uniqueness_proven": False},
        "proposal_policy": CAGE_POLICY.copy(), "static_reference_count": parent["static_reference_count"],
        "static_population_changed": False, "continuous_axial_envelope_complete": False,
        "second_order_applied": False, "minimum_eccentricity_applied": False,
        "physical_concurrency_proven": False, "analysis_generation_qualified": False,
        "engineering_status": "CONDITIONAL", "normative_qualification": "NOT_PROVEN",
        "design_demand_authority": "DENIED", "engineering_release": "NOT_READY", "final_design_eligible": False,
        "blockers": list(dict.fromkeys((*BLOCKERS, *OPEN_BASIS)))}
    summary["result_sha256"] = digest(summary)
    return SpectralPMM(summary, population, cages, tuple(rows), evidence, sections)
