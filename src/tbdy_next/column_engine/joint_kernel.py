"""TBDY 7.5 references for explicit centered, orthogonal joint scenarios.

No routine supplies joint Ve, SCWB capacities, actual reinforcement, offsets
or physical connection authority. Units: mm, mm2, MPa and explicitly kN.
"""
from decimal import Decimal
import math

from .native_archive import BankError, finite
from .ts500_column import positive


def _class(enclosure):
    if enclosure not in ("ENCLOSED", "UNENCLOSED"):
        raise BankError("JOINT_ENCLOSURE_SCENARIO_REQUIRED")
    return enclosure == "ENCLOSED"


def width_reference(beam_width_mm, column_width_mm):
    """7.5.1 prose includes equality; no tolerance expands this inequality."""
    bw, b = positive(beam_width_mm, "beam_width"), positive(column_width_mm, "column_width")
    return Decimal(str(bw)) >= Decimal(".75") * Decimal(str(b))


def centered_joint_limit(*, column_width_mm, column_depth_mm, beam_widths_mm, fck_mpa, enclosure):
    """Fig.7.10 / 7.12–13: b1=b2=b/2, with the bw_min+h bound.

    Valid only for the stated centered orthogonal scenario. Missing beams do
    not supply a width; the caller handles a direction without recorded beams.
    """
    confined = _class(enclosure)
    b,h,fc = (positive(v,k) for v,k in ((column_width_mm,"b"),(column_depth_mm,"h"),(fck_mpa,"fck")))
    if not isinstance(beam_widths_mm,(list,tuple)) or not 1 <= len(beam_widths_mm) <= 2:
        raise BankError("ONE_OR_TWO_BOUND_BEAM_WIDTHS_REQUIRED")
    bw = min(positive(v,"beam_width") for v in beam_widths_mm)
    bj = min(b, bw+h)
    coefficient = 1.7 if confined else 1.0
    limit = positive(coefficient*bj*h*math.sqrt(fc)/1000,"joint_limit_kn")
    return {"b_mm":b,"h_mm":h,"bj_mm":bj,"minimum_beam_width_mm":bw,"fck_mpa":fc,
        "coefficient":coefficient,"geometric_limit_kn":limit,"enclosure_scenario":enclosure,
        "b1_mm":b/2,"b2_mm":b/2,"centered_sections_assumed":True,
        "ve_kn":None,"utilization":None,"physical_geometry_proven":False,
        "code_ref":"TBDY 7.5.2.2 / Fig.7.10","formal_compliance":"NOT_PROVEN"}


def joint_transverse_reference(*, lower_required_ash_mm2, lower_spacing_mm, proposed_ash_mm2,
                              joint_spacing_mm, tie_diameter_mm, enclosure):
    """7.5.2.3 transfer uses Ash/s; do not compare areas at unequal pitches."""
    confined = _class(enclosure)
    lower,ls,ash,s,t = (positive(v,k) for v,k in ((lower_required_ash_mm2,"lower_required_Ash"),
        (lower_spacing_mm,"lower_spacing"),(proposed_ash_mm2,"proposed_Ash"),
        (joint_spacing_mm,"joint_spacing"),(tie_diameter_mm,"tie_diameter")))
    fraction,cap = (.4,150) if confined else (.6,100)
    required_density = positive(fraction*lower/ls,"required_joint_density")
    required_area = positive(required_density*s,"required_joint_area")
    met = Decimal(str(ash))/Decimal(str(s)) >= Decimal(str(fraction))*Decimal(str(lower))/Decimal(str(ls))
    ratio = finite(required_area/ash,"joint_transverse_ratio")
    return {"fraction_of_lower_required_density":fraction,"lower_required_ash_mm2":lower,
        "lower_spacing_mm":ls,"required_ash_per_s_mm2_per_mm":required_density,
        "required_ash_at_joint_spacing_mm2":required_area,"proposed_ash_mm2":ash,
        "joint_spacing_mm":s,"tie_diameter_mm":t,"spacing_limit_mm":cap,
        "minimum_diameter_mm":8,"density_reference_met":met,"required_to_proposed_ratio":ratio,
        "spacing_reference_met":s<=cap,"diameter_reference_met":t>=8,
        "all_references_met":met and s<=cap and t>=8,
        "code_ref":"TBDY 7.5.2.3","formal_compliance":"NOT_PROVEN"}
