"""Conditional column shear/confinement arithmetic in N, mm and MPa.

Adapted narrowly from TBDY 1440df1 regulatory/column_shear_p7.py and
column_transverse_confinement.py; checked against TS500 8.1 and TBDY 7.3.
The caller must supply the physical layout, design cut, Ve and applicability.
No function selects a design, a seismic branch or an actual confinement region.
"""
from decimal import Decimal
import math

from .native_archive import BankError, finite
from .ts500_column import positive


def zero_concrete_gate(*, in_confinement, earthquake_only_kn, seismic_total_kn,
                       n_compression_kn, area_mm2, fck_mpa):
    """TBDY 7.3.7.6: strict E share, inclusive signed axial threshold.

None is an unknown input, not False or zero. The seismic-total magnitude must
be positive to establish the stated ratio. The low-tension TS500 exception is
not inferred here or in shear_reference.
"""
    inputs = (in_confinement, earthquake_only_kn, seismic_total_kn, n_compression_kn)
    if any(v is None for v in inputs):
        return {"status":"NOT_PROVEN", "required":None}
    if type(in_confinement) is not bool:
        raise BankError("CONFINEMENT_LOCATION_BOOLEAN_REQUIRED")
    eq = abs(finite(earthquake_only_kn,"earthquake_only"))
    total = positive(seismic_total_kn,"seismic_total_magnitude")
    n = finite(n_compression_kn,"N_compression")
    area,fc = positive(area_mm2,"Ac"),positive(fck_mpa,"fck")
    required = (in_confinement and Decimal(str(eq)) > Decimal(".5")*Decimal(str(total))
        and Decimal(str(n))*1000 <= Decimal(".05")*Decimal(str(area))*Decimal(str(fc)))
    return {"status":"CONDITION_EVALUATED", "required":required}


def confinement_reference(*, area_mm2, core_area_mm2, bk_mm, spacing_mm,
                          fck_mpa, fywk_mpa, ash_mm2):
    """Both TBDY 7.1/7.3.4.1(d) branches; never choose from partial source N."""
    ac,ack,bk,s,fc,fy,ash = (positive(v,k) for v,k in (
        (area_mm2,"Ac"),(core_area_mm2,"Ack"),(bk_mm,"bk"),(spacing_mm,"s"),
        (fck_mpa,"fck"),(fywk_mpa,"fywk"),(ash_mm2,"Ash")))
    if ack >= ac: raise BankError("CORE_AREA_MUST_BE_SMALLER_THAN_GROSS_AREA")
    a = .30*s*bk*(ac/ack-1)*fc/fy
    b = .075*s*bk*fc/fy
    high = max(a,b)
    positive(high,"required_Ash")
    result = {"bk_mm":bk,"ash_mm2":ash,"eq71_a_mm2":a,"eq71_b_mm2":b,
        "high_axial_required_ash_mm2":high,"low_axial_required_ash_mm2":(2/3)*high,
        "high_axial_ratio":high/ash,"low_axial_ratio":(2/3)*high/ash,
        "high_axial_spacing_bound_mm":s*ash/high,
        "low_axial_spacing_bound_mm":s*ash/((2/3)*high),
        "high_axial_reference_met":ash>=high,"low_axial_reference_met":ash>=(2/3)*high,
        "axial_branch_selected":None,"formal_compliance":"NOT_PROVEN"}
    for key,value in result.items():
        if type(value) in (int,float): finite(value,key)
    return result


def shear_reference(*, n_compression_kn, shear_kn, area_mm2, bw_mm, d_mm,
                    fck_mpa, fywk_mpa, asw_mm2, spacing_mm, gamma_c, gamma_s):
    """Compare one signed static source component with two explicit scenarios.

V2/V3 mapping belongs to the supplied geometry, not major/minor labels.
Asw/s from force balance is not a complete code minimum or final selection.
TS500 8.7 is retained as a section-8 web reference, with column applicability
unapproved. Neither source V nor this comparison supplies TBDY design Ve.
"""
    n,v = finite(n_compression_kn,"N_compression"),finite(shear_kn,"V")
    ac,bw,d,fc,fy,asw,s,gc,gs = (positive(value,key) for value,key in (
        (area_mm2,"Ac"),(bw_mm,"bw"),(d_mm,"d"),(fck_mpa,"fck"),(fywk_mpa,"fywk"),
        (asw_mm2,"Asw"),(spacing_mm,"s"),(gamma_c,"gamma_c"),(gamma_s,"gamma_s")))
    if d >= ac/bw: raise BankError("EFFECTIVE_DEPTH_MUST_BE_LESS_THAN_SECTION_DEPTH")
    fctk = .35*math.sqrt(fc)
    fctd,fcd,fywd = fctk/gc,fc/gc,fy/gs
    stress = n*1000/ac
    # Eq.8.1 uses a POSITIVE Nd magnitude with gamma=-.3 in tension.
    factor = 1 + (.07 if n>=0 else .30)*stress
    vcr = .65*fctd*bw*d*factor/1000 if factor>=0 else None
    vc = .8*vcr if vcr is not None else None
    vw = asw/s*fywd*d/1000
    branches = {}
    for name,concrete in (("ts500",vc),("zero_concrete",0)):
        item = {"vc_kn":concrete,"vw_kn":vw,"vr_kn":None,"source_utilization":None,
            "balance_asw_per_s_mm2_per_mm":None,"balance_spacing_bound_mm":None,
            "status":"OUTSIDE_CRACKING_FORMULA_DOMAIN"}
        if concrete is not None:
            resistance = concrete+vw
            required = max(0,abs(v)-concrete)*1000/(fywd*d)
            item.update(vr_kn=resistance,source_utilization=abs(v)/resistance,
                balance_asw_per_s_mm2_per_mm=required,
                balance_spacing_bound_mm=asw/required if required>0 else None,
                status="WITHIN_REFERENCE_RESISTANCE" if abs(v)<=resistance else "EXCEEDS_REFERENCE_RESISTANCE")
        branches[name] = item
    web = .22*fcd*bw*d/1000
    brittle = .85*ac*math.sqrt(fc)/1000
    result = {"source_signed_v_kn":v,"source_abs_v_kn":abs(v),"n_compression_kn":n,
        "axial_stress_mpa":stress,"axial_factor":factor,"fctk_mpa":fctk,"fctd_mpa":fctd,
        "fcd_mpa":fcd,"fywd_mpa":fywd,"vcr_kn":vcr,"asw_mm2":asw,"spacing_mm":s,
        "asw_per_s_mm2_per_mm":asw/s,"bw_mm":bw,"d_mm":d,"branches":branches,
        "ts500_web_reference_kn":web,"tbdy_brittle_reference_kn":brittle,
        "source_within_ts500_web_reference":abs(v)<=web,"source_within_tbdy_brittle_reference":abs(v)<=brittle,
        "ts500_web_column_applicability":"NOT_PROVEN",
        "tension_gamma_zero_exception_applied":False,"vc_branch_selected":None,
        "ve_kn":None,"ve_status":"NOT_PROVEN","final_design_eligible":False}
    # Reject overflow in supplied or derived quantities; never emit JSON NaN/Inf.
    for value in (stress,factor,fctk,fctd,fcd,fywd,vw,web,brittle): finite(value,"shear_result")
    for branch in branches.values():
        for key,value in branch.items():
            if key!="status" and value is not None: finite(value,"shear_branch_result")
    return result
