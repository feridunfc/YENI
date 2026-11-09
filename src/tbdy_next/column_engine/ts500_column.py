"""Pure TS500 column arithmetic; callers own the engineering input authority.

Adapted from TBDY 1440df1 / slenderness.py and moment_magnification.py.
The original 1.3 denominator placement is corrected against TS500 7.24/7.27.
No routine supplies k, creep, sway, analysis order or a physical free length.
Eq.7.29's prose/symbol conflict is retained explicitly, never silently resolved.
Kernel units: N, mm, MPa; Euler load is returned explicitly in kN.
"""
from decimal import Decimal
import math

from .native_archive import BankError, finite

TS500_REFERENCE = "https://staff.emu.edu.tr/cemalgenes/Documents/courses/INSA471_2019_20_Bahar/TS500.pdf"
SWAY_PREVENTED = "SWAY_PREVENTED"
SWAY_PERMITTED = "SWAY_PERMITTED"


def positive(value, label):
    value = finite(value, label)
    if value <= 0:
        raise BankError("POSITIVE_VALUE_REQUIRED:" + label)
    return value


def _sway(value):
    if value not in (SWAY_PREVENTED, SWAY_PERMITTED):
        raise BankError("SWAY_BASIS_REQUIRED")
    return value


def _ratio(value):
    value = finite(value, "signed_end_moment_ratio")
    if not -1 <= value <= 1:
        raise BankError("END_MOMENT_RATIO_OUTSIDE_MINUS_ONE_PLUS_ONE")
    return value


def rectangle_properties(t2_mm, t3_mm):
    """CSI M2 bends about local 2: h=T3; M3 about local 3: h=T2."""
    t2, t3 = positive(t2_mm, "T2"), positive(t3_mm, "T3")
    area = t2 * t3
    i22, i33 = t2 * t3**3 / 12, t3 * t2**3 / 12
    result = {"area_mm2": area, "i22_mm4": i22, "i33_mm4": i33,
        "r22_exact_mm": math.sqrt(i22 / area), "r33_exact_mm": math.sqrt(i33 / area),
        "r22_ts500_approx_mm": .30 * t3, "r33_ts500_approx_mm": .30 * t2}
    for name, value in result.items():
        positive(value, name)
    return result


def minimum_eccentricity_mm(bending_dimension_mm):
    """Exact decimal TS500 6.16 reference; end-design applicability is separate."""
    if type(bending_dimension_mm) not in (int, float, Decimal):
        raise BankError("INVALID_BENDING_DIMENSION")
    h = Decimal(str(bending_dimension_mm))
    if not h.is_finite() or h <= 0:
        raise BankError("POSITIVE_BENDING_DIMENSION_REQUIRED")
    return Decimal(15) + Decimal(".03") * h


def evaluate_slenderness(*, free_length_ln_mm, k, radius_mm, sway, signed_end_moment_ratio=None):
    ln, k, radius = (positive(v, label) for v, label in
        ((free_length_ln_mm, "ln"), (k, "k"), (radius_mm, "radius")))
    _sway(sway)
    ratio = None if signed_end_moment_ratio is None else _ratio(signed_end_moment_ratio)
    lk = positive(k * ln, "lk")
    slenderness = finite(lk / radius, "lk_over_i")
    limit = 22 if sway == SWAY_PERMITTED else min(40, 34 - 12 * ratio) if ratio is not None else None
    if slenderness > 100:
        status = "GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED"
    elif limit is not None:
        status = "NEGLECT_LIMIT_MET_NUMERICALLY" if slenderness <= limit else "MOMENT_MAGNIFICATION_REQUIRED"
    elif slenderness <= 22:
        status = "NEGLECT_LIMIT_MET_FOR_ALL_SIGNED_END_RATIOS"
    elif slenderness <= 40:
        status = "SIGNED_END_MOMENT_RATIO_REQUIRED"
    else:
        status = "MOMENT_MAGNIFICATION_REQUIRED"
    return {"ln_mm": ln, "k": k, "lk_mm": lk, "radius_mm": radius,
        "lk_over_i": slenderness, "neglect_limit": limit, "status": status,
        "code_ref": "TS500 7.6.1 / 7.17 / 7.18", "formal_compliance": "NOT_PROVEN"}


def effective_stiffness_nmm2(*, ec_mpa, ic_mm4, creep_ratio, method, es_mpa=None, is_mm4=None):
    ec, ic = positive(ec_mpa, "Ec"), positive(ic_mm4, "Ic")
    rm = finite(creep_ratio, "Rm")
    if not 0 <= rm <= 1:
        raise BankError("CREEP_RATIO_OUTSIDE_ZERO_ONE")
    if method == "TS500_7_20":
        es, steel_i = positive(es_mpa, "Es"), finite(is_mm4, "Is")
        if steel_i < 0:
            raise BankError("NEGATIVE_REBAR_INERTIA")
        ei = (.2 * ec * ic + es * steel_i) / (1 + rm)
    elif method == "TS500_7_21" and es_mpa is None and is_mm4 is None:
        ei = .4 * ec * ic / (1 + rm)
    else:
        raise BankError("EXPLICIT_EI_METHOD_AND_MATCHING_INPUTS_REQUIRED")
    return positive(ei, "EI")


def euler_load_kn(*, effective_ei_nmm2, effective_length_lk_mm):
    ei = positive(effective_ei_nmm2, "EI")
    lk = positive(effective_length_lk_mm, "lk")
    return positive(math.pi**2 * ei / lk**2 / 1000, "Nk_kN")


def moment_magnification_factors(*, nd_kn, nk_kn, sway, signed_end_moment_ratio=None,
                                  horizontal_load_between_ends=None, story_nd_kn=None, story_nk_kn=None):
    """Coefficients only; does not mutate or authorize a concurrent demand vector."""
    nd, nk = positive(nd_kn, "Nd"), positive(nk_kn, "Nk")
    _sway(sway)
    output = {"status": "COEFFICIENTS_ONLY", "cm": None, "beta": None, "beta_story": None,
        "final_factor": None, "reason": None, "formal_compliance": "NOT_PROVEN"}
    if sway == SWAY_PREVENTED:
        if story_nd_kn is not None or story_nk_kn is not None:
            raise BankError("STORY_AGGREGATES_CONFLICT_WITH_SWAY_PREVENTED")
        if type(horizontal_load_between_ends) is not bool:
            raise BankError("TRANSVERSE_LOAD_BASIS_REQUIRED")
        cm = 1 if horizontal_load_between_ends else max(.4, .6 + .4 * _ratio(signed_end_moment_ratio))
    else:
        cm = 1
        sn, sk = positive(story_nd_kn, "story_Nd"), positive(story_nk_kn, "story_Nk")
        if Decimal(str(sn)) > Decimal(".45") * Decimal(str(sk)):
            output.update(status="BLOCKED", reason="TS500_7_28_STORY_LIMIT_EXCEEDED")
            return output
        story_denominator = Decimal(1) - Decimal("1.3") * Decimal(str(sn)) / Decimal(str(sk))
        output["beta_story"] = float(max(Decimal(1), Decimal(1) / story_denominator))
    output["cm"] = cm
    denominator = Decimal(1) - Decimal("1.3") * Decimal(str(nd)) / Decimal(str(nk))
    if denominator <= 0:
        output.update(status="BLOCKED", reason="TS500_7_24_NONPOSITIVE_DENOMINATOR")
        return output
    output["beta"] = float(max(Decimal(1), Decimal(str(cm)) / denominator))
    if sway == SWAY_PREVENTED:
        output["final_factor"] = output["beta"]
    else:
        output.update(status="EQ729_DECISION_NOT_PROVEN", reason="NORMATIVE_LENGTH_SYMBOL_CONFLICT")
    return output


def eq729_length_comparison(*, free_length_ln_mm, effective_length_lk_mm, radius_mm, nd_kn, fck_mpa, area_mm2):
    """Show both readings of Eq.7.29; neither gains automatic design authority."""
    ln, lk, radius, nd, fck, area = (positive(v, label) for v, label in
        ((free_length_ln_mm, "ln"), (effective_length_lk_mm, "lk"), (radius_mm, "radius"),
         (nd_kn, "Nd"), (fck_mpa, "fck"), (area_mm2, "Ac")))
    threshold = 35 / math.sqrt(nd * 1000 / (fck * area))
    return {"ln_over_i": ln / radius, "lk_over_i": lk / radius, "threshold": threshold,
        "free_length_reading_requires_product": ln / radius > threshold,
        "printed_symbol_reading_requires_product": lk / radius > threshold,
        "status": "NORMATIVE_LENGTH_SYMBOL_CONFLICT", "product_authorized": False,
        "code_ref": "TS500 7.29: prose=free length; printed symbol=lk", "formal_compliance": "NOT_PROVEN"}
