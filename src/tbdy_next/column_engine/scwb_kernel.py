"""Adapt TBDY's capacity-design joint aggregation to explicit source contexts.

Origin: TBDY 1440df1 / design/core/capacity_design.py. Missing participants
remain in the denominator population; no capacity/source-label fallback.
The comparison is a conditional arithmetic reference, never a design approval.
"""
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
import math

from .native_archive import BankError, finite, identity
from .section_capacity import _Curve, FORCE_TOL_N, MOMENT_ABS_TOL_NMM, MOMENT_REL_TOL

FACTOR=1.20
SOURCE="https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/design/core/capacity_design.py"


@dataclass(frozen=True)
class JointCase:
    source_run_id: str
    source_archive_sha256: str
    joint_id: str
    direction: str
    rotation_sign: int
    output_case: str
    scenario: str
    step_type: str="Single Value"
    step_number: float=0.0

    def __post_init__(self):
        for value in (self.source_run_id,self.source_archive_sha256,self.joint_id,self.output_case,self.scenario):
            identity(value,"SCWB_context")
        if (self.direction not in ("X","Y") or type(self.rotation_sign) is not int or self.rotation_sign not in (-1,1)
                or self.step_type!="Single Value" or type(self.step_number) not in (int,float) or self.step_number!=0):
            raise BankError("SCWB_CONTEXT_UNSUPPORTED")


@dataclass(frozen=True)
class MemberMomentCapacity:
    context: JointCase
    member_id: str
    end: str
    role: str
    capacity_knm: float | None
    source_id: str | None
    tolerance_knm: float=0.0
    reason: str | None=None

    def __post_init__(self):
        identity(self.member_id,"SCWB_member")
        if not isinstance(self.context,JointCase) or self.end not in ("I","J") or self.role not in ("COLUMN","BEAM"):
            raise BankError("SCWB_CAPACITY_IDENTITY_INVALID")
        if finite(self.tolerance_knm,"capacity_tolerance")<0:
            raise BankError("SCWB_CAPACITY_TOLERANCE_INVALID")
        if self.capacity_knm is not None:
            if finite(self.capacity_knm,"moment_capacity")<=0 or self.reason is not None:
                raise BankError("SCWB_CAPACITY_VALUE_INVALID")
            identity(self.source_id,"capacity_source")
        elif not self.reason:
            raise BankError("SCWB_MISSING_CAPACITY_REASON_REQUIRED")


def compute_scwb_joint_result(context,expected_columns,expected_beams,capacities):
    """Expected entries are exact (native member ID, I/J end) pairs.

    The context binds the entire joint/direction/sign/case/scenario. All
    supplied participants must belong to it; missing entries remain explicit.
    Independent constituent maxima and mixed cases cannot be silently summed.
    """
    if not isinstance(context,JointCase):raise BankError("SCWB_CONTEXT_INVALID")
    expected={}
    for role,entries in (("COLUMN",expected_columns),("BEAM",expected_beams)):
        entries=list(entries)
        if len(entries)!=len(set(entries)):raise BankError("SCWB_DUPLICATE_EXPECTED_MEMBER")
        for name,end in entries:
            identity(name,"expected_member")
            if end not in ("I","J"):raise BankError("SCWB_EXPECTED_END_INVALID")
            if any(k[1]==name for k in expected):raise BankError("SCWB_MEMBER_ROLE_OR_END_AMBIGUOUS")
            expected[(role,name,end)]=None
    observed={}
    for cap in capacities:
        if not isinstance(cap,MemberMomentCapacity) or cap.context!=context:
            raise BankError("SCWB_MIXED_SOURCE_OR_STATE")
        key=(cap.role,cap.member_id,cap.end)
        if key not in expected or key in observed:raise BankError("SCWB_UNEXPECTED_OR_DUPLICATE_CAPACITY")
        observed[key]=cap
    missing=[{"role":k[0],"member_id":k[1],"end":k[2],"reason":observed[k].reason if k in observed else "CAPACITY_NOT_SUPPLIED"}
        for k in sorted(expected) if k not in observed or observed[k].capacity_knm is None]
    def total(role):
        keys=[k for k in expected if k[0]==role]
        if not keys or any(k not in observed or observed[k].capacity_knm is None for k in keys):return None,None
        values=[observed[k] for k in keys]
        return math.fsum(c.capacity_knm for c in values),math.fsum(c.tolerance_knm for c in values)
    columns,ctol=total("COLUMN");beams,btol=total("BEAM")
    required=FACTOR*beams if beams is not None else None
    result={"sum_mrc_reference_knm":columns,"sum_mrb_reference_knm":beams,"required_mrc_reference_knm":required,
        "raw_capacity_ratio":None,"normalized_reference_ratio":None,"reference_satisfied":None,
        "comparison_tolerance_knm":None,"residual_knm":None,"missing_capacities":missing,
        "expected_column_count":len(expected_columns),"expected_beam_count":len(expected_beams),
        "status":"CAPACITY_INPUTS_INCOMPLETE","factor":FACTOR,"scwb_ratio":None,
        "formal_compliance":"NOT_PROVEN","design_demand_authority":"DENIED","engineering_release":"NOT_READY"}
    if not expected_columns or not expected_beams:
        result["status"]="NO_COLUMN_OR_BEAM_IN_DIRECTION"
    elif columns is not None and beams is not None:
        residual=columns-required;tolerance=ctol+FACTOR*btol
        within=abs(residual)<=tolerance and tolerance>0
        result.update(raw_capacity_ratio=columns/beams,normalized_reference_ratio=columns/required,
            residual_knm=residual,comparison_tolerance_knm=tolerance,
            reference_satisfied=None if within else residual>=0,
            status="NUMERIC_BOUNDARY_UNRESOLVED" if within else "CONDITIONAL_REFERENCE_SATISFIED" if residual>=0 else "CONDITIONAL_REFERENCE_NOT_SATISFIED")
    return result


@lru_cache(maxsize=24)
def _curve(section,axis):
    return _Curve(section,90 if axis=="M2" else 0)


@lru_cache(maxsize=4096)
def _column_axis_capacity(section,n_n,axis):
    if axis not in ("M2","M3") or not section.symmetric:
        raise BankError("SCWB_TWO_AXIS_SYMMETRIC_SECTION_REQUIRED")
    finite(n_n,"source_axial_force")
    point,reason=_curve(section,axis).solve(n_n)
    result={"status":"COLUMN_CAPACITY_UNRESOLVED","reason":reason,"capacity_knm":None,"tolerance_knm":None,
        "axis":axis,"n_source_kn":n_n/1000,"point":point,"axial_residual_n":None,
        "method":"CANONICAL_SECTION_FIXED_PRINCIPAL_PLANE_AT_SOURCE_N",
        "both_signs_equal_from_verified_symmetry":True,"capacity_at_source_demand_ray_used":False,
        "source_n_is_design_nd":False,"continuous_error_bound_proven":False}
    if point is None:return result
    field="m2_nmm" if axis=="M2" else "m3_nmm";other="m3_nmm" if axis=="M2" else "m2_nmm"
    moment=point[field];residual=abs(point["n_n"]-n_n)
    if moment<=0 or residual>FORCE_TOL_N or abs(point[other])>MOMENT_ABS_TOL_NMM:
        result["reason"]="SCWB_PRINCIPAL_PLANE_NOT_RESOLVED";return result
    tolerance=MOMENT_ABS_TOL_NMM+MOMENT_REL_TOL*moment+FORCE_TOL_N*math.hypot(section.t2,section.t3)/2
    if moment<=tolerance:
        result["reason"]="SCWB_ZERO_CAPACITY_BOUNDARY_UNRESOLVED";return result
    result.update(status="COLUMN_CAPACITY_REFERENCE",reason=None,capacity_knm=moment/1e6,
        tolerance_knm=tolerance/1e6,axial_residual_n=residual)
    return result


def column_axis_capacity(section,n_n,axis):
    """No reuse of a demand-vector PMM ratio; solve the requested pure axis."""
    return deepcopy(_column_axis_capacity(section,n_n,axis))
