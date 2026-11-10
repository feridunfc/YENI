"""Independent report arithmetic retained from GOLDEN-01 (source ZIP pinned).

No YENI production kernel is imported. The original calculate function is
unchanged; GOLDEN-02 formulas below are the arithmetic in its seven tests.
These are report references, never a replacement production design engine.
"""
import math

def calculate(c):
    x=c['inputs']; k=c['id']
    if k == 'SDS': return x['Ss']*x['Fs']
    if k == 'SD1': return x['S1']*x['F1']
    if k == 'TA': return .2*x['SD1']/x['SDS']
    if k == 'TB': return x['SD1']/x['SDS']
    if k == 'PROVIDED_AS': return x['bar_count']*math.pi*(x['diameter_mm']**2)/4/100
    if k == 'CONFINEMENT_ASW_OVER_S': return x['legs']*math.pi*x['tie_diameter_mm']**2/4/100/(x['s_mm']/1000)
    if k == 'AC': return x['b_cm']*x['h_cm']
    if k == 'CONFINEMENT_AXIAL_BRANCH_THRESHOLD': return .2*x['Ac_cm2']*.1*x['fck_MPa']
    if k == 'AXIAL_TBDY_LIMIT': return .4*x['Ac_cm2']*.1*x['fck_MPa']
    if k == 'AXIAL_TS500_LIMIT': return .9*x['Ac_cm2']*.1*x['fcd_MPa']
    if k == 'JOINT_UNCONFINED_LIMIT': return x['bj_mm']*x['h_mm']*math.sqrt(x['fck_MPa'])/1000
    if k == 'JOINT_CONFINED_LIMIT': return 1.7*x['bj_mm']*x['h_mm']*math.sqrt(x['fck_MPa'])/1000
    if k == 'SCWB_COLUMN_SUM': return x['Mr_lower']+x['Mr_upper']
    if k == 'SCWB_BEAM_1P2_SUM': return 1.2*(x['Mr_beam_left']+x['Mr_beam_right'])
    if k == 'SCWB_NUMERIC_INEQUALITY': return (x['Mr_lower']+x['Mr_upper']) > 1.2*(x['Mr_beam_left']+x['Mr_beam_right'])
    if k == 'JOINT_VE_ONE_BEAM_APPROX': return 1.25*x['fyk_MPa']*x['As1_cm2']*100/1000-x['Vcol_kN']
    if k == 'JOINT_VE_TWO_BEAM_APPROX': return 1.25*x['fyk_MPa']*(x['As1_cm2']+x['As2_cm2'])*100/1000-x['Vcol_kN']
    if k in ('THETA_GROUND','THETA_UPPER'): return x['sum_W_above_kN']*(x['delta_avg_mm']/1000)/(x['story_shear_kN']*x['height_m'])
    if k in ('SWAY_PHI_GROUND','SWAY_PHI_UPPER'): return 1.5*(x['delta_mm']/1000)*x['sum_N_over_L_kN_per_m']/x['story_shear_kN']
    if k == 'DRIFT_LAMBDA': return x['Sae_DD3']/x['Sae_DD2']
    if k == 'LOCAL_BETA_NON_DIAGNOSTIC': return max(1.,x['Cm']/(1-1.3*x['Nd_kN']/x['Nk_kN']))
    raise ValueError(k)


def member_beta(nd, nk):
    return 1 / (1 - 1.3 * nd / nk)


def story_alpha(vis, vik):
    return vis / vik


def printed_eq729(lk_m, nd_kn):
    radius_m = .30 / math.sqrt(12)
    threshold = 35 / math.sqrt(nd_kn / (30000 * .30 * .30))
    return {"lk_over_i": lk_m / radius_m, "threshold": threshold,
            "product_branch_from_printed_symbol": lk_m / radius_m > threshold}
