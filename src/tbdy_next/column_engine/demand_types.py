"""VS26 immutable, versioned force meanings; no implicit type conversions.

A native static vector, a statistical component envelope and a deliberately
constructed design-check candidate are different types. Candidate signs refer
to native tension-positive P. Compression-positive N therefore reverses P's
sign. All exposed numbers use kN, kN.m and m; only the existing PMM adapter
converts to N and N.mm.
"""
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import product
from typing import ClassVar

from .native_archive import BankError, digest, finite, identity
from .source_bank import ATOL, RTOL, COMPONENTS, FIELDS

PERMUTATION_POLICY = "CSI_MAX_MIN_P_M2_M3_EIGHT_CORNERS_CONDITIONAL_V1"
CSI_RULE = "CSI_ETABS_CONCRETE_FRAME_DESIGN_2_1_MAX_MIN_PERMUTATIONS"
AXES = "CSI_FRAME_LOCAL_1_2_3"


def _numbers(values, count, name, nonnegative=False):
    if type(values) is not tuple or len(values) != count:
        raise BankError("TYPED_DEMAND_SHAPE:" + name)
    for value in values:
        finite(value, name)
        if nonnegative and value < 0:
            raise BankError("TYPED_DEMAND_NEGATIVE:" + name)


def _hash(value, name):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise BankError("TYPED_DEMAND_HASH:" + name)


@dataclass(frozen=True, slots=True)
class NativeCut:
    member_id: str
    object_station_m: float
    element_id: str
    element_station_m: float

    def __post_init__(self):
        identity(self.member_id, "member_id"); identity(self.element_id, "element_id")
        _numbers((self.object_station_m, self.element_station_m), 2, "station", True)

    @classmethod
    def from_key(cls, key):
        return cls(key["Obj"], key["ObjSta"], key["Elm"], key["ElmSta"])

    def as_dict(self):
        return dict(zip(FIELDS[:4], (self.member_id, self.object_station_m, self.element_id, self.element_station_m)))


@dataclass(frozen=True, slots=True)
class RecordedForceRow:
    cut: NativeCut
    output_case: str
    step_type: str
    step_number: float
    values: tuple
    source_row_id: str
    source_call_id: str
    source_row_index: int
    shard_sha256: str

    def __post_init__(self):
        if type(self.cut) is not NativeCut:
            raise BankError("NATIVE_CUT_TYPE_REQUIRED")
        identity(self.output_case, "output_case"); identity(self.step_type, "step_type")
        identity(self.source_call_id, "source_call_id")
        finite(self.step_number, "step_number"); _numbers(self.values, 6, "native_forces")
        _hash(self.source_row_id, "source_row"); _hash(self.shard_sha256, "shard")
        if type(self.source_row_index) is not int or self.source_row_index < 0:
            raise BankError("SOURCE_ROW_INDEX_INVALID")

    @classmethod
    def from_ref(cls, row):
        k = row["native_key"]
        return cls(NativeCut.from_key(k), k["LoadCase"], k["StepType"], k["StepNum"],
            tuple(row["native_values"][c] for c in COMPONENTS), row["source_row_id"], row["source_call_id"],
            row["source_row_index"], row["shard_sha256"])

    def as_dict(self):
        return {"native_key": {**self.cut.as_dict(), "LoadCase": self.output_case,
            "StepType": self.step_type, "StepNum": self.step_number},
            "native_values": dict(zip(COMPONENTS, self.values)), "source_row_id": self.source_row_id,
            "source_call_id": self.source_call_id, "source_row_index": self.source_row_index,
            "shard_sha256": self.shard_sha256, "units": "kN_m_C", "coordinate_basis": AXES}


@dataclass(frozen=True, slots=True)
class PhysicalStaticForceState:
    schema: ClassVar[str] = "tbdy.next.physical-static-force-state.v1"
    state_id: str
    source_archive_sha256: str
    source_demand_result_sha256: str
    row: RecordedForceRow

    def __post_init__(self):
        for name in ("state_id", "source_archive_sha256", "source_demand_result_sha256"):
            _hash(getattr(self, name), name)
        if (type(self.row) is not RecordedForceRow or self.row.step_type != "Single Value"
                or self.row.step_number != 0):
            raise BankError("PHYSICAL_STATIC_SINGLE_VALUE_REQUIRED")

    def as_dict(self):
        return {"schema": self.schema, "type": type(self).__name__, "state_id": self.state_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_demand_result_sha256": self.source_demand_result_sha256, **self.row.as_dict(),
            "physical_same_case_step_station": True, "analysis_generation_qualified": False,
            "analysis_generation_id": None,
            "normative_qualification": "NOT_PROVEN", "final_design_eligible": False}


@dataclass(frozen=True, slots=True)
class CaseContribution:
    case_type: int
    factor: float
    row: RecordedForceRow

    def __post_init__(self):
        if type(self.case_type) is not int or self.case_type not in (1, 4) or type(self.row) is not RecordedForceRow:
            raise BankError("CONTRIBUTION_CASE_TYPE_INVALID")
        finite(self.factor, "factor")
        if self.row.step_type != ("Max" if self.case_type == 4 else "Single Value") or self.row.step_number != 0:
            raise BankError("CONTRIBUTION_STEP_OUTSIDE_RECIPE")
        if self.case_type == 4:
            _numbers(self.row.values, 6, "spectral_amplitude", True)

    def as_dict(self):
        return {"case_type": self.case_type, "factor": self.factor, **self.row.as_dict()}


@dataclass(frozen=True, slots=True)
class SpectralComponentEnvelope:
    schema: ClassVar[str] = "tbdy.next.spectral-component-envelope.v1"
    envelope_id: str
    source_run_id: str | None
    source_archive_sha256: str
    source_replay_result_sha256: str
    cut: NativeCut
    combination: str
    center: tuple
    radius: tuple
    contributions: tuple
    native_steps: tuple
    content_sha256: str = field(init=False)

    def __post_init__(self):
        for name in ("envelope_id", "source_archive_sha256", "source_replay_result_sha256"):
            _hash(getattr(self, name), name)
        if type(self.cut) is not NativeCut:
            raise BankError("SPECTRAL_NATIVE_CUT_REQUIRED")
        identity(self.combination, "combination")
        _numbers(self.center, 6, "center"); _numbers(self.radius, 6, "radius", True)
        if (type(self.contributions) is not tuple or not self.contributions
                or any(type(c) is not CaseContribution or c.row.cut != self.cut for c in self.contributions)
                or len({c.row.output_case for c in self.contributions}) != len(self.contributions)
                or not any(c.case_type == 4 for c in self.contributions)):
            raise BankError("SPECTRAL_CONTRIBUTIONS_INVALID")
        if (type(self.native_steps) is not tuple or len(self.native_steps) != 2
                or any(type(r) is not RecordedForceRow or r.cut != self.cut or r.output_case != self.combination
                       or r.step_number != 0 for r in self.native_steps)
                or {r.step_type for r in self.native_steps} != {"Max", "Min"}):
            raise BankError("SPECTRAL_NATIVE_STEPS_INVALID")
        # The immutable envelope is also arithmetically bound to its leaves.
        # The builder separately binds those leaves to the sealed archive.
        center, radius = [Fraction(0)] * 6, [Fraction(0)] * 6
        for term in self.contributions:
            factor = Fraction(str(term.factor))
            target = radius if term.case_type == 4 else center
            for i, value in enumerate(term.row.values):
                target[i] += (abs(factor) if term.case_type == 4 else factor) * Fraction(str(value))
        if self.center != tuple(map(float, center)) or self.radius != tuple(map(float, radius)):
            raise BankError("SPECTRAL_TYPED_ARITHMETIC_MISMATCH")
        for row in self.native_steps:
            for i, native in enumerate(row.values):
                predicted = center[i] + (1 if row.step_type == "Max" else -1) * radius[i]
                observed = Fraction(str(native))
                if abs(predicted-observed) > ATOL+RTOL*max(abs(predicted), abs(observed)):
                    raise BankError("SPECTRAL_TYPED_NATIVE_MISMATCH")
        object.__setattr__(self, "content_sha256", digest(self._content()))

    def _content(self):
        return {"schema": self.schema, "type": type(self).__name__, "envelope_id": self.envelope_id,
            "source_run_id": self.source_run_id, "source_archive_sha256": self.source_archive_sha256,
            "source_replay_result_sha256": self.source_replay_result_sha256,
            "station_key": self.cut.as_dict(), "combination": self.combination,
            "static_contribution_native": dict(zip(COMPONENTS, self.center)),
            "spectral_magnitudes_native": dict(zip(COMPONENTS, self.radius)),
            "contributions": [c.as_dict() for c in self.contributions],
            "native_steps": [r.as_dict() for r in self.native_steps],
            "physical_concurrency_proven": False, "normative_qualification": "NOT_PROVEN",
            "analysis_generation_id": None, "analysis_generation_qualified": False,
            "final_design_eligible": False, "units": "kN_m_C", "coordinate_basis": AXES}

    def as_dict(self):
        return {**self._content(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class CodeDesignDemandCandidate:
    schema: ClassVar[str] = "tbdy.next.code-design-demand-candidate.v1"
    envelope: SpectralComponentEnvelope
    signs: tuple
    permutation_policy: str = PERMUTATION_POLICY

    def __post_init__(self):
        if type(self.envelope) is not SpectralComponentEnvelope:
            raise BankError("CODE_CANDIDATE_REQUIRES_SPECTRAL_ENVELOPE")
        if (type(self.signs) is not tuple or len(self.signs) != 3
                or any(type(s) is not int or s not in (-1, 1) for s in self.signs)
                or self.permutation_policy != PERMUTATION_POLICY):
            raise BankError("CODE_CANDIDATE_SIGN_POLICY_INVALID")
        _numbers(self.values, 3, "constructed_N_M2_M3")

    @property
    def sign_id(self):
        return "_".join(f"{label}{value:+d}" for label, value in zip(("P", "M2", "M3"), self.signs))

    @property
    def candidate_id(self):
        return digest({"schema": self.schema, "policy": self.permutation_policy,
            "source_replay_result_sha256": self.envelope.source_replay_result_sha256,
            "source_envelope_id": self.envelope.envelope_id, "source_envelope_content_sha256": self.envelope.content_sha256,
            "native_component_signs": self.signs})

    @property
    def values(self):
        c, a = self.envelope.center, self.envelope.radius
        # Each sign is a design-envelope choice, never a measured modal sign.
        return (-(c[0] + self.signs[0] * a[0]), c[4] + self.signs[1] * a[4], c[5] + self.signs[2] * a[5])

    def as_dict(self):
        e = self.envelope
        return {"schema": self.schema, "type": type(self).__name__, "candidate_id": self.candidate_id,
            "source_run_id": e.source_run_id, "source_archive_sha256": e.source_archive_sha256,
            "source_replay_result_sha256": e.source_replay_result_sha256, "source_envelope_id": e.envelope_id,
            "source_envelope_content_sha256": e.content_sha256,
            "source_combination": e.combination, "station_key": e.cut.as_dict(),
            "applicable_design_rule": CSI_RULE, "rule_application": "CONDITIONAL_DESIGN_CONVENTION",
            "tbdy_applicability": "NOT_PROVEN", "permutation_policy": self.permutation_policy,
            "sign_id": self.sign_id, "native_component_signs": dict(zip(("P", "M2", "M3"), self.signs)),
            "sign_convention": "SIGNS_ON_NATIVE_TENSION_POSITIVE_P_M2_M3_THEN_N_EQUALS_MINUS_P",
            "static_contribution": {"N_kN": -e.center[0], "M2_kNm": e.center[4], "M3_kNm": e.center[5]},
            "spectral_magnitudes": {"N_kN": e.radius[0], "M2_kNm": e.radius[4], "M3_kNm": e.radius[5]},
            "forces": dict(zip(("N_kN", "M2_kNm", "M3_kNm"), self.values)),
            "source_terms": [{"case_name": c.row.output_case, "case_type": c.case_type, "factor": c.factor,
                "source_row_id": c.row.source_row_id, "source_call_id": c.row.source_call_id,
                "source_row_index": c.row.source_row_index} for c in e.contributions],
            "native_max_min_row_ids": {r.step_type: r.source_row_id for r in e.native_steps},
            "analysis_generation_qualified": False, "analysis_order": "NOT_PROVEN",
            "analysis_generation_id": None,
            "physical_concurrency_proven": False, "normative_qualification": "NOT_PROVEN",
            "second_order_applied": False, "final_design_eligible": False, "coordinate_basis": AXES,
            "unpermuted_shear_and_torsion": "REMAIN_IN_COMPONENT_ENVELOPE_NOT_A_CONCURRENT_VECTOR"}


def sign_candidates(envelope):
    if type(envelope) is not SpectralComponentEnvelope:
        raise BankError("TYPED_SPECTRAL_ENVELOPE_REQUIRED")
    return tuple(CodeDesignDemandCandidate(envelope, signs) for signs in product((-1, 1), repeat=3))


def pmm_arguments(candidate):
    if type(candidate) is not CodeDesignDemandCandidate:
        raise BankError("TYPED_CODE_DESIGN_CANDIDATE_REQUIRED")
    n, m2, m3 = candidate.values
    result = (n * 1000, m2 * 1_000_000, m3 * 1_000_000)
    _numbers(result, 3, "PMM_N_NMM")
    return result
