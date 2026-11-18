#!/usr/bin/env python3
"""Replay one declared modal-to-alpha arithmetic fixture.

No production import, dynamic expression execution, COM, finite-element analysis,
RC section solver, or engineering acceptance is performed. JSON formula prose is
never interpreted. This fixed oracle uses Decimal arithmetic distinct from the
binary64 authoring calculation and the YENI production owners.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone


D = Decimal


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=True).encode()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cqc_rho(period1, period2, damping):
    beta = period2 / period1
    return (8*damping*damping*(1+beta)*beta*beta.sqrt()
            / ((1-beta*beta)**2+4*damping*damping*beta*(1+beta)**2))


def cqc(a, b, rho):
    # Stable covariance eigenbasis for equal diagonal correlations. This also
    # avoids subtraction of almost equal, large squared amplitudes.
    square = (1-rho)*(a*a+b*b)+rho*(a+b)*(a+b)
    if square < 0:
        raise ValueError('NEGATIVE_MODAL_VARIANCE')
    return square.sqrt()


def expected_grid(inputs):
    return {(direction+suffix,mode,'C'+str(i+1)+'_'+cut)
            for direction in ('X','Y')
            for suffix in ('_E_MINUS','_E_PLUS')
            for mode in inputs['modal_term_ids']
            for i in range(4)
            for cut in inputs['joint_end_ids_by_line']}


def complete_population(data):
    rows=data['modal_source_rows']
    keys=[(r['case_id'],r['mode_id'],r['physical_cut_id']) for r in rows]
    return len(keys)==len(set(keys)) and set(keys)==expected_grid(data['inputs'])


def replay(data):
    records=[]
    intermediate={}
    inputs=data['inputs'];expected=data['reference_values'];identity=data['identity']

    def check(name,observed,target,absolute='0',unit='1',reason='Exact identity or declared Boolean contract.'):
        if isinstance(observed,Decimal):
            wanted=D(str(target));difference=abs(observed-wanted)
            match=observed.is_finite() and wanted.is_finite() and difference<=D(absolute)
            observed=str(observed);target=str(wanted);difference=str(difference)
        else:
            difference=None;match=observed==target
        records.append({'name':name,'observed':observed,'expected':target,'unit':unit,
                        'absolute_tolerance':absolute,'absolute_difference':difference,
                        'tolerance_reason':reason,'status':'MATCH' if match else 'MISMATCH'})

    nreason='Independent Decimal(80) replay against fixed binary64-authored fixture values; numerical reproducibility only.'
    check('input_source_sha256',hashlib.sha256(canonical(inputs)).hexdigest(),identity['source_sha256'])
    check('complete_modal_population',complete_population(data),True)
    check('row_count',len(data['modal_source_rows']),128)
    check('physical_cut_count',len({r['physical_cut_id'] for r in data['modal_source_rows']}),16)
    check('active_damping_count',len(inputs['active_modal_damping_ratio']),2)
    check('active_damping_equal_branch',inputs['active_modal_damping_ratio'],['0.05','0.05'])
    check('case_count',len({r['case_id'] for r in data['modal_source_rows']}),4)
    check('combo_catalog_count',len(data['combination_catalog']),64)
    check('selected_combo_group',data['selected_combination_groups'],['ductile'])
    check('complete_selected_combo_ledger',sorted(data['design_combo_groups']['ductile']),sorted(r['combination_id'] for r in data['combination_catalog']))
    for row in data['modal_source_rows']:
        check('lineage_'+row['case_id']+'_'+row['mode_id']+'_'+row['physical_cut_id'],
              [row[k] for k in ['source_id','source_sha256','model_id','analysis_generation_id']],
              [identity[k] for k in ['source_id','source_sha256','model_id','analysis_generation_id']])

    for combo in data['combination_catalog']:
        magnitudes=sorted([abs(D(combo['X_coefficient'])),abs(D(combo['Y_coefficient']))])
        check('100_30_'+combo['combination_id'],magnitudes,[D('0.3'),D('1')])
        check('combo_identity_'+combo['combination_id'],[combo['source_id'],combo['analysis_generation_id'],combo['semantic_role']],
              [identity['source_id'],identity['analysis_generation_id'],'FORMULA_ON_SCALAR_ENVELOPES_NOT_A_CONCURRENT_VECTOR'])

    periods=[D(x) for x in inputs['periods_s']]
    rho=cqc_rho(*periods,D('0.05'))
    check('CQC_correlation',rho,expected['correlation_rho_12'],'1e-60',reason='Fixed analytic value stored to 80 decimal digits.')
    check('correlation_positive_semidefinite',D('0')<=rho<=D('1'),True)
    amplitudes={}
    branch_records=[]
    positions=[[D(x) for x in row] for row in inputs['plan_coordinates_m']]
    radius_square=sum(x*x+y*y for x,y in positions)
    check('torsion_response_operator_radius_square',radius_square,'72',unit='m2')
    for direction in ['X','Y']:
        for sign in [-1,1]:
            branch=direction+('_E_MINUS' if sign==-1 else '_E_PLUS')
            modes=[]
            for mi,mode in enumerate(inputs['modal_term_ids']):
                total=D(inputs['modal_storey_shear_kn'][direction][mi])
                eccentricity=D(str(sign))*D(inputs['accidental_eccentricity_ratio'])*D(inputs['diaphragm_width_m'][direction])
                mz=(-eccentricity if direction=='X' else eccentricity)*total
                vectors=[]
                for i,(x,y) in enumerate(positions):
                    p=D(inputs['centred_shear_fractions'][i])
                    tx=-mz*y/radius_square;ty=mz*x/radius_square
                    fx=(p*total if direction=='X' else D(0))+tx
                    fy=(p*total if direction=='Y' else D(0))+ty
                    n=D(inputs['centred_modal_compression_kn'][direction][mi][i])
                    vectors.append([fx,fy,n,tx,ty])
                    for cut in inputs['joint_end_ids_by_line']:
                        rows=[r for r in data['modal_source_rows'] if r['case_id']==branch and r['mode_id']==mode and r['physical_cut_id']=='C'+str(i+1)+'_'+cut]
                        if len(rows)!=1:
                            raise ValueError('SOURCE_POPULATION_NOT_UNIQUE')
                        row=rows[0]
                        side=D(1 if cut.endswith('_I') else -1)
                        quantities={'Fx_kn':fx,'Fy_kn':fy,'compression_N_kn':n,'applied_torsion_Fx_kn':tx,'applied_torsion_Fy_kn':ty,
                                    'moment_about_global_X_knm':-D('1.5')*fy*side,'moment_about_global_Y_knm':D('1.5')*fx*side}
                        for key,target in quantities.items():
                            check('source_'+branch+'_'+mode+'_'+row['physical_cut_id']+'_'+key,D(row[key]),target,'1e-11',unit='kN m' if 'moment' in key else 'kN',reason='15-significant-digit source-row serialization tolerance.')
                check(branch+'_'+mode+'_torsion_Fx_sum',sum(v[3] for v in vectors),'0','1e-65',unit='kN')
                check(branch+'_'+mode+'_torsion_Fy_sum',sum(v[4] for v in vectors),'0','1e-65',unit='kN')
                torque=sum(positions[i][0]*vectors[i][4]-positions[i][1]*vectors[i][3] for i in range(4))
                check(branch+'_'+mode+'_applied_torque',torque,mz,'1e-65',unit='kN m')
                check(branch+'_'+mode+'_axial_equilibrium',sum(v[2] for v in vectors),'0',unit='kN')
                modes.append(vectors)
            amplitudes[branch]=[[cqc(modes[0][i][j],modes[1][i][j],rho) for j in range(3)] for i in range(4)]
            axis=0 if direction=='X' else 1
            total_mode=[sum(modes[j][i][axis] for i in range(4)) for j in range(2)]
            eligible_mode=[sum(modes[j][i][axis] for i in range(3)) for j in range(2)]
            vik=cqc(*total_mode,rho);vis=cqc(*eligible_mode,rho);alpha=vis/vik
            # Equality of both signed modal shares is the special fixture proof.
            share0=eligible_mode[0]/total_mode[0];share1=eligible_mode[1]/total_mode[1]
            check(branch+'_same_modal_share',share0,share1,'1e-65',reason='Proportional response fields make the subset fraction equal at every common modal phase.')
            check(branch+'_alpha_exact_share',alpha,share0,'1e-65',reason='CQC is positively homogeneous for the same proportional signed response.')
            check(branch+'_storey_total',vik,expected[direction+'_storey_CQC_shear_kn'],'1e-9','kN',nreason)
            check(branch+'_native_directional_SRSS_single_load', (vik*vik+D(0)**2).sqrt(),vik,'1e-65',unit='kN',reason='Each fixture spectrum case has one active acceleration direction; internal directional SRSS is the identity.')
            branch_records.append({'case_id':branch,'direction':direction,'modal_total_kn':[str(v) for v in total_mode],'modal_eligible_kn':[str(v) for v in eligible_mode],'Vik_kn':str(vik),'Vis_kn':str(vis),'alpha':str(alpha),'proof':'Identical nonnegative signed modal allocation fractions in both modes.'})
    alpha=min(D(r['alpha']) for r in branch_records);factor=1/alpha
    check('governing_alpha',alpha,D(211)/240,'1e-65',reason='Exact fixture fraction 211/240.')
    check('factor',factor,D(240)/211,'1e-65',reason='Exact reciprocal 240/211.')
    intermediate['identity']=identity
    intermediate['branch_story_shares']=branch_records
    intermediate['modal_amplitudes']={b:[[str(v) for v in row] for row in rows] for b,rows in amplitudes.items()}

    capacities_old=[];capacities_new=[];base_m=[];base_v=[];revised_m=[];revised_v=[]
    axial=[]
    for i in range(4):
        x=amplitudes['X_E_PLUS'][i][2];y=amplitudes['Y_E_PLUS'][i][2]
        nX=x+D('0.3')*y;nY=D('0.3')*x+y
        n_bound=max(nX,nY)
        G=D(inputs['gravity_G_compression_kn'][i]);Q=D(inputs['gravity_Q_compression_kn'][i]);sds=D(inputs['SDS'])
        g_plus=G+Q+D('0.3')*(D(2)/3)*sds*G
        g_minus=D('0.9')*G-D('0.3')*(D(2)/3)*sds*G
        nlo=g_minus-n_bound;nhi=g_plus+n_bound
        refN=D(inputs['capacity_curve_reference_N_kn']);coefficient=D(inputs['capacity_curve_quadratic_coefficient_knm_per_kn2'])
        loss=coefficient*max((nlo-refN)**2,(nhi-refN)**2)
        old=(D(inputs['initial_column_pair_C0_knm'][i])-loss)/2
        new=(D(inputs['revised_column_pair_C0_knm'][i])-loss)/2
        capacities_old.append(old);capacities_new.append(new)
        table=expected['axial_and_capacity_results'][i]
        for key,v in [('X_CQC_axial_kn',x),('Y_CQC_axial_kn',y),('X_primary_axial_bound_kn',nX),('Y_primary_axial_bound_kn',nY),('compression_lower_kn',nlo),('compression_upper_kn',nhi),('governing_curve_argument_kn',nlo),('initial_single_column_Mr_lower_bound_knm',old),('revised_single_column_Mr_lower_bound_knm',new)]:
            check('C'+str(i+1)+'_'+key,v,table[key],'1e-9','kN m' if 'Mr' in key else 'kN',nreason)
        check('C'+str(i+1)+'_lower_N_governs_capacity',(nlo-refN)**2>(nhi-refN)**2,True)
        xFx=max(amplitudes[b][i][0] for b in ['X_E_MINUS','X_E_PLUS']);yFx=max(amplitudes[b][i][0] for b in ['Y_E_MINUS','Y_E_PLUS'])
        xFy=max(amplitudes[b][i][1] for b in ['X_E_MINUS','X_E_PLUS']);yFy=max(amplitudes[b][i][1] for b in ['Y_E_MINUS','Y_E_PLUS'])
        v=max(xFx+D('0.3')*yFx,D('0.3')*xFx+yFx,xFy+D('0.3')*yFy,D('0.3')*xFy+yFy)
        m=D(inputs['factored_gravity_moment_bound_knm'][i])+D('1.5')*v
        f=factor if i<3 else D(1)
        base_m.append(m);base_v.append(v);revised_m.append(f*m);revised_v.append(f*v)
        axial.append({'column_line_id':'C'+str(i+1),'N_lower_kn':str(nlo),'N_upper_kn':str(nhi),'capacity_pair_initial_knm':str(2*old),'capacity_pair_revised_knm':str(2*new),'governing_N_kn':str(nlo)})
    threshold=D('1.2')*2*D(inputs['beam_face_capacity_each_knm'])
    check('SCWB_threshold',threshold,'240',unit='kN m')
    eligible_old=['C'+str(i+1) for i,c in enumerate(capacities_old) if 2*c>=threshold]
    eligible_new=['C'+str(i+1) for i,c in enumerate(capacities_new) if 2*c>=threshold]
    check('SCWB_initial_eligible_columns',eligible_old,['C1','C2','C3'])
    check('SCWB_revised_eligible_columns',eligible_new,['C1','C2','C3'])
    low_axial=D('0.10')*D(inputs['column_gross_area_mm2'])*D(inputs['column_fck_mpa'])/1000
    check('SCWB_low_axial_exemption_threshold',low_axial,'225',unit='kN')
    check('SCWB_low_axial_exemption_not_used',all(D(r['N_lower_kn'])>low_axial for r in axial),True)
    joint_rows=[]
    for i in range(4):
        for joint in ['J1','J2']:
            for axis in ['X','Y']:
                for sign in [-1,1]:
                    joint_rows.append({'identity_ref':'#/intermediate_results/identity','joint_id':'C'+str(i+1)+'_'+joint,
                                       'direction':axis,'earthquake_sign':sign,'column_line_id':'C'+str(i+1),
                                       'capacity_lower_bound_knm':str(2*capacities_new[i]),'beam_threshold_knm':str(threshold),
                                       'meets_SCWB':2*capacities_new[i]>=threshold,'capacity_source':'Declared analytic bound covering both direction-compatible axial families.'})
    check('SCWB_joint_direction_sign_population',len(joint_rows),32)
    intermediate['SCWB_joint_direction_sign_rows']=joint_rows
    for key,values in [('base_moment_bounds_knm',base_m),('base_shear_bounds_kn',base_v),('revised_moment_bounds_knm',revised_m),('revised_shear_bounds_kn',revised_v)]:
        for i,v in enumerate(values):check('C'+str(i+1)+'_'+key,v,expected[key][i],'1e-9','kN m' if 'moment' in key else 'kN',nreason)
    old_without=[m<=c for m,c in zip(base_m,capacities_old)]
    old_with=[m<=c for m,c in zip(revised_m,capacities_old)]
    new_with=[m<=c for m,c in zip(revised_m,capacities_new)]
    check('initial_moment_checks_without_alpha',old_without,[True]*4)
    check('initial_moment_checks_with_alpha',old_with,[False,False,False,True])
    check('revised_moment_checks_with_alpha',new_with,[True]*4)
    check('revised_shear_checks',[v<=D(c) for v,c in zip(revised_v,inputs['declared_column_shear_capacity_kn'])],[True]*4)
    repeated=[base_m[i]*(factor if i<3 else 1) for i in range(4)]
    check('repeat_uses_original_demand',repeated,revised_m)
    check('compounded_demand_detected',all(revised_m[i]*factor>repeated[i] for i in range(3)),True)
    intermediate['axial_capacity_bounds']=axial
    intermediate['iteration_trace']=[
        {'iteration':0,'cage_revision':identity['initial_column_cage_revision'],'eligible':eligible_old,'alpha':str(alpha),'demand_factor':str(factor),'moment_check_after_feedback':old_with,'action':'Upgrade C1, C2 and C3 capacity input revisions.'},
        {'iteration':1,'cage_revision':identity['revised_column_cage_revision'],'eligible':eligible_new,'alpha':str(alpha),'demand_factor':str(factor),'moment_check_after_feedback':new_with,'action':'Recompute from frozen original demand; retain C4 factor 1.'},
        {'iteration':2,'cage_revision':identity['revised_column_cage_revision'],'eligible':eligible_new,'alpha':str(alpha),'demand_factor':str(factor),'moment_check_after_feedback':new_with,'action':'Fixed point of this declared arithmetic chain; production and engineering acceptance remain NOT_RUN.'}
    ]

    stress=data['precision_fixture'];p=[D(v) for v in stress['periods_s']]
    rs=cqc_rho(*p,D(stress['damping_ratio']));a,b=[D(v) for v in stress['signed_amplitudes']]
    result=cqc(a,b,rs)
    check('near_repeated_modes_rho',rs,stress['reference_rho'],'1e-60',reason='High precision correlation target; binary64 rounds away the small distance from one.')
    check('near_cancellation_response',result,stress['reference_response'],'1e-15','kN','Independent high precision cancellation fixture.')
    r64=float(rs);f64=math.hypot(math.sqrt(max(0,1-r64))*float(a),math.sqrt(max(0,1-r64))*float(b),math.sqrt(r64)*(float(a)+float(b)))
    check('binary64_stress_loss_detected',abs(D(str(f64))-result)>D('0.001'),True)
    intermediate['precision_stress']={'decimal80_response_kn':str(result),'binary64_response_kn':f64,'relative_error':str(abs(D(str(f64))-result)/result),'interpretation':'Precision-loss witness only; no ETABS or YENI defect asserted.'}

    removed=dict(data,modal_source_rows=data['modal_source_rows'][:-1])
    duplicated=dict(data,modal_source_rows=data['modal_source_rows'][:-1]+[data['modal_source_rows'][0]])
    check('missing_source_row_is_detected',complete_population(removed),False)
    check('duplicate_cannot_replace_missing_row',complete_population(duplicated),False)
    check('missing_active_damping_is_detectable',len(inputs['active_modal_damping_ratio'][:-1])==len(inputs['modal_term_ids']),False)
    # Non-proportional fields have no general subset-ratio guarantee.
    counter_total=cqc(D(10)+D(-9),D(0),rho);counter_eligible=cqc(D(10),D(0),rho)
    check('nonproportional_ratio_exceeds_one',counter_eligible/counter_total,'10',unit='1')
    member_modes=[(D(40),D(-10)),(D(30),D(20)),(D(20),D(25)),(D(10),D(15))]
    sum_peaks=sum(cqc(a,b,rho) for a,b in member_modes)
    total_peak=cqc(sum(a for a,b in member_modes),sum(b for a,b in member_modes),rho)
    check('sum_of_member_peaks_is_not_storey_peak',abs(sum_peaks-total_peak)>D(1),True)
    corner=D('2.1')/(D(2)+D('0.5')**2);interior=D('2.1')/D(2)
    check('eight_corner_counterexample_corners_pass',corner<=1,True)
    check('eight_corner_counterexample_interior_fails',interior>1,True)
    check('magnification_pole_inside_domain_detected',D('0.8')<=D(1)<=D('1.2'),True)
    intermediate['counterexamples']={'sum_individual_modal_peaks_kn':str(sum_peaks),'aggregate_then_combine_kn':str(total_peak),'invalid_subset_ratio':str(counter_eligible/counter_total),'nonconvex_box_corner_utilization':str(corner),'nonconvex_box_interior_utilization':str(interior)}
    return records,intermediate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=Path(__file__).resolve().parents[1]/'PRIORITY_CHAIN.json')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    data=json.loads(args.fixture.read_text())
    with localcontext() as ctx:
        ctx.prec=80
        records,intermediate=replay(data)
    failed=[r for r in records if r['status']!='MATCH']
    report={'schema_version':'1.0.0','verification_id':'VER-PRIORITY-CHAIN-ARITHMETIC-001','level':'INDEPENDENT_EXAMPLE_ARITHMETIC',
            'status':'MATCH' if not failed else 'MISMATCH','command':[Path(sys.executable).name, *sys.argv],
            'executed_at_utc':datetime.now(timezone.utc).isoformat(),
            'environment':{'python':platform.python_version(),'implementation':platform.python_implementation(),'platform':platform.system(),'decimal_precision':80,'dependencies':'Python standard library'},
            'fixture_sha256':digest(args.fixture),'verifier_sha256':digest(__file__),
            'source_id':data['identity']['source_id'],'source_sha256':data['identity']['source_sha256'],
            'assertion_count':len(records),'matched':len(records)-len(failed),'mismatched':len(failed),
            'production_owner_comparison':'NOT_RUN','recorded_pipeline_replay':'NOT_RUN','live_ETABS_source_validation':'NOT_RUN','engineering_acceptance':'NOT_RUN',
            'scope_limit':'One synthetic arithmetic-chain fixture. No production imports, FE eigenproblem, RC capacity solve, real bar-cage selection or actual-model engineering acceptance.',
            'results':records,'intermediate_results':intermediate}
    rendered=json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n'
    if args.output:
        args.output.write_text(rendered)
    print(json.dumps({k:v for k,v in report.items() if k not in ['results','intermediate_results']},indent=2))
    if failed:
        print(json.dumps(failed[:10],indent=2),file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':
    main()
