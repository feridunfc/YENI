"""TS500 7.19/7.21/7.24 parameter references, without design authority.

The zero-denominator length solves Nk = 1.3 * Nsource. It is neither the
Euler Nk=Nsource length nor an allowable member length. No k, ln, sway,
Cm, beta or design moment is inferred. Reuse the accepted TS500 kernels.
"""
from decimal import Decimal
import math

from .native_archive import BankError, finite
from .ts500_column import effective_stiffness_nmm2, euler_load_kn, positive

CREEP_SCENARIOS = (0.0, 0.5, 1.0)
REFERENCE_SLENDERNESSES = (22, 40, 100)
NUMERIC_ZERO_BAND = 1e-12  # Numerical ambiguity is blocked, never accepted as a positive margin.


def stiffness_family(*, ec_mpa, ic_mm4, radius_mm):
    radius = positive(radius_mm, "reference_radius")
    result = []
    for rm in CREEP_SCENARIOS:
        ei = effective_stiffness_nmm2(ec_mpa=ec_mpa, ic_mm4=ic_mm4, creep_ratio=rm, method="TS500_7_21")
        result.append({"creep_ratio_scenario": rm, "effective_ei_nmm2_scenario": ei,
            "length_references": [{"lk_over_i_reference": value, "effective_length_lk_mm_scenario": value*radius,
                "nk_kn_scenario": euler_load_kn(effective_ei_nmm2=ei, effective_length_lk_mm=value*radius)}
                for value in REFERENCE_SLENDERNESSES]})
    return result


def zero_denominator_length_mm(*, effective_ei_nmm2, source_n_compression_kn):
    ei = positive(effective_ei_nmm2, "EI_scenario")
    n = positive(source_n_compression_kn, "source_N_compression")
    return positive(math.pi*math.sqrt(ei/(1.3*n*1000)), "zero_denominator_length")


def source_denominator(*, source_n_compression_kn, nk_kn):
    n, nk = positive(source_n_compression_kn, "source_N_compression"), positive(nk_kn, "Nk_scenario")
    ratio = Decimal("1.3")*Decimal(str(n))/Decimal(str(nk))
    value = finite(float(Decimal(1)-ratio), "source_denominator")
    status = ("NUMERICALLY_NEAR_ZERO" if abs(value) <= NUMERIC_ZERO_BAND else
        "NONPOSITIVE_SOURCE_DENOMINATOR" if value <= 0 else "POSITIVE_SOURCE_DENOMINATOR")
    return {"source_denominator": value, "status": status,
        "beta": None, "design_stability_proven": False}


def source_length_scenarios(*, source_n_compression_kn, family, radius_mm):
    n = finite(source_n_compression_kn, "source_N_compression")
    radius = positive(radius_mm, "reference_radius")
    results = []
    for scenario in family:
        result = {"creep_ratio_scenario": scenario["creep_ratio_scenario"],
            "status": "NONCOMPRESSION_NOT_APPLICABLE", "zero_denominator_length_mm": None,
            "zero_length_over_radius": None, "zero_length_exceeds_100i_reference": None,
            "at_reference_lengths": []}
        if n > 0:
            length = zero_denominator_length_mm(effective_ei_nmm2=scenario["effective_ei_nmm2_scenario"],
                source_n_compression_kn=n)
            result.update(status="SOURCE_LENGTH_REFERENCES_CALCULATED", zero_denominator_length_mm=length,
                zero_length_over_radius=length/radius, zero_length_exceeds_100i_reference=length > 100*radius,
                at_reference_lengths=[{**ref, **source_denominator(source_n_compression_kn=n, nk_kn=ref["nk_kn_scenario"])}
                    for ref in scenario["length_references"]])
        results.append(result)
    return results
