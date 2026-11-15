"""Conditional TBDY 7.3.6.1 check for explicitly supplied story shear totals."""

from decimal import Decimal, InvalidOperation
from fractions import Fraction

from .native_archive import BankError

LIMIT = Decimal("0.70")


def _shear_kn(value, name):
    if type(value) not in (str, int, float, Decimal):
        raise BankError("STORY_ALPHA_INVALID_" + name)
    try:
        value = Decimal(str(value))
    except InvalidOperation:
        raise BankError("STORY_ALPHA_INVALID_" + name) from None
    if not value.is_finite() or value < 0:
        raise BankError("STORY_ALPHA_INVALID_" + name)
    return value


def evaluate_story_alpha_reference(*, vis_kn, vik_kn):
    """Compare V_is / V_ik against Eq. (7.4) using supplied kN magnitudes.

    The caller supplies the two totals for the same story and direction. Joint
    coverage, the population of contributing columns and load provenance
    require separate evidence before this can drive design or validation.
    """
    vis = _shear_kn(vis_kn, "VIS")
    vik = _shear_kn(vik_kn, "VIK")
    if vik == 0:
        raise BankError("STORY_ALPHA_ZERO_VIK")
    if vis > vik:
        raise BankError("STORY_ALPHA_VIS_EXCEEDS_VIK")
    ratio = Fraction(vis) / Fraction(vik)
    meets = ratio >= Fraction(LIMIT)
    return {
        "alpha": vis / vik,
        "limit": LIMIT,
        "numeric_status": "AT_OR_ABOVE_0P70" if meets else "BELOW_0P70",
        "classification_review_required": not meets,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
