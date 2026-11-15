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
from .csi_geometry import LocalSectionDims, NativeSectionDims, local_dimensions, to_local_dimensions

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
    """Native CSI dimensions: M2 bends through T2; M3 through T3."""
    d2, d3 = local_dimensions(t2_mm, t3_mm)
    area = d2 * d3
    i22, i33 = d2 * d3**3 / 12, d3 * d2**3 / 12
    result = {"area_mm2": area, "i22_mm4": i22, "i33_mm4": i33,
        "r22_exact_mm": math.sqrt(i22 / area), "r33_exact_mm": math.sqrt(i33 / area),
        "r22_ts500_approx_mm": .30 * d3, "r33_ts500_approx_mm": .30 * d2}
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


def apply_minimum_eccentricity(
    *,
    nd_kn: float,
    m2_knm: float,
    m3_knm: float,
    dims: NativeSectionDims | LocalSectionDims,
    local_axis_angle_deg: float = 0.0,
) -> dict:
    """TS500 §6.3.10 Eq.(6.16) minimum eccentricity demand floor (F02, F08, F09).

    Under axial compression (nd_kn > 0), design moments about local 2 and local 3
    must be at least Nd * e_min, where e_min = 15 mm + 0.03 * h_bending:
      - M2 bends in local 1-3 plane through depth along local 3 (= native T2).
      - M3 bends in local 1-2 plane through depth along local 2 (= native T3).
    """
    nd = finite(nd_kn, "nd_kn")
    m2 = finite(m2_knm, "m2_knm")
    m3 = finite(m3_knm, "m3_knm")
    angle = finite(local_axis_angle_deg, "local_axis_angle_deg")
    local_dims = to_local_dimensions(dims) if isinstance(dims, NativeSectionDims) else dims
    if not isinstance(local_dims, LocalSectionDims):
        raise TypeError("NATIVE_OR_LOCAL_SECTION_DIMS_REQUIRED")

    h_m2_mm = local_dims.bending_depth_m2_mm
    h_m3_mm = local_dims.bending_depth_m3_mm
    e_min_m2_mm = float(minimum_eccentricity_mm(h_m2_mm))
    e_min_m3_mm = float(minimum_eccentricity_mm(h_m3_mm))

    if nd > 0:
        m2_min_knm = nd * e_min_m2_mm / 1000.0
        m3_min_knm = nd * e_min_m3_mm / 1000.0
        sign2 = -1.0 if m2 < 0 else 1.0
        sign3 = -1.0 if m3 < 0 else 1.0
        m2_design = sign2 * max(abs(m2), m2_min_knm)
        m3_design = sign3 * max(abs(m3), m3_min_knm)
        m2_governed = abs(m2) < m2_min_knm
        m3_governed = abs(m3) < m3_min_knm
    else:
        m2_min_knm = 0.0
        m3_min_knm = 0.0
        m2_design = m2
        m3_design = m3
        m2_governed = False
        m3_governed = False

    rad = math.radians(angle)
    c, s = math.cos(rad), math.sin(rad)
    # Global moment projection of the local design moments for rotated columns
    mx_global_knm = m2_design * c - m3_design * s
    my_global_knm = m2_design * s + m3_design * c

    return {
        "canonical_id": "TS500:6.3.10:MIN_ECCENTRICITY_6_16:COLUMN:2000R2018",
        "check_code": "CHK-115",
        "nd_compression_kn": nd,
        "local2_extent_mm": local_dims.local2_extent_mm,
        "local3_extent_mm": local_dims.local3_extent_mm,
        "h_m2_mm": h_m2_mm,
        "h_m3_mm": h_m3_mm,
        "e_min_m2_mm": e_min_m2_mm,
        "e_min_m3_mm": e_min_m3_mm,
        "m2_min_knm": m2_min_knm,
        "m3_min_knm": m3_min_knm,
        "m2_raw_knm": m2,
        "m3_raw_knm": m3,
        "m2_design_knm": m2_design,
        "m3_design_knm": m3_design,
        "m2_floor_governed": m2_governed,
        "m3_floor_governed": m3_governed,
        "local_axis_angle_deg": angle,
        "mx_global_design_knm": mx_global_knm,
        "my_global_design_knm": my_global_knm,
    }


def section_axial_limits_kn(*, fck_mpa: float, fcd_mpa: float, ac_mm2: float) -> dict:
    """TS 500 and TBDY concrete-section limits, independent of cage selection."""
    fck = positive(fck_mpa, "fck_mpa")
    fcd = positive(fcd_mpa, "fcd_mpa")
    ac = positive(ac_mm2, "ac_mm2")
    return {
        "ts500_eq_7_7_max_nd_kn": 0.90 * fcd * ac / 1000.0,
        "tbdy_7_3_1_2_max_ndm_kn": 0.40 * fck * ac / 1000.0,
    }


def axial_compression_caps_kn(
    *,
    fck_mpa: float,
    fcd_mpa: float,
    fyd_mpa: float,
    ac_mm2: float,
    ast_mm2: float = 0.0,
) -> dict:
    """Normative axial compression ceilings vs raw plastic N0 (F01: CHK-004 & CHK-005).

    - Raw plastic compression capacity: N0 = (0.85 * fcd * (Ac - Ast) + fyd * Ast) / 1000 kN
    - TS500 §7.4 Eq.(7.7) (CHK-005): Nd <= 0.90 * fcd * Ac / 1000 kN (NOT 0.80 * N0)
    - TBDY 2018 §7.3.1.2 (CHK-004): Ndm <= 0.40 * fck * Ac / 1000 kN
    """
    limits = section_axial_limits_kn(fck_mpa=fck_mpa, fcd_mpa=fcd_mpa, ac_mm2=ac_mm2)
    fcd = positive(fcd_mpa, "fcd_mpa")
    fyd = positive(fyd_mpa, "fyd_mpa")
    ac = positive(ac_mm2, "ac_mm2")
    ast = finite(ast_mm2, "ast_mm2")
    if ast < 0 or ast >= ac:
        raise BankError("INVALID_REBAR_AREA_AST")
    n0_kn = (0.85 * fcd * (ac - ast) + fyd * ast) / 1000.0
    return {
        "raw_plastic_n0_kn": n0_kn,
        **limits,
        "non_ts500_080_n0_reference_kn": 0.80 * n0_kn,
        "080_n0_is_ts500_7_7": False,
    }


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
