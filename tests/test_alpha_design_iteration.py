"""D3: arithmetic oracles, explicit negative contracts, bounded orchestration.

Synthetic SCWB fixtures exercise the glue; they are not structural model approvals.
Production section/selection owners are exercised separately below.
"""
from copy import deepcopy
from decimal import Decimal
import math
import unittest
from unittest.mock import patch

from tbdy_next.column_engine.story_alpha import evaluate_story_alpha_reference, alpha_feedback_factor
from tbdy_next.engineering.alpha_iteration import (
    SCHEMA, DEMAND_SCHEMA, METHOD, _sealed, _digest, _axis_indices, _feasibility,
    qualify_story_alpha, build_demand_revision, revised_force_rows, revised_pmm_member,
    run_bounded_feedback, validate_record, _selection_constraints,
)
from test_r10_live import _rowset, _base_live_payload


def two_columns():
    frames, cols, points = [], [], []
    rowsets = {}
    dep = {"global_blockers": [], "topology_blockers": [], "members": {}, "joints": {},
           "story_columns": {"Zemin": ["C1", "C2"]}}
    r10 = {"per_member": {}}
    scope = {"configured_output_cuts": {}}
    for idx, (uid, shear, sat) in enumerate((("C1", 80., True), ("C2", 20., False))):
        pi,pj = uid+"I", uid+"J"
        frames.append(dict(UniqueName=uid, Type="Column", AnalysisSect="Rect", AxisAngle="0", Story="Zemin"))
        cols.append(dict(UniqueName=uid, Story="Zemin", UniquePtI=pi, UniquePtJ=pj, Length="3"))
        points.extend([dict(UniqueName=pi,X=str(idx*5),Y="0",Z="0"),dict(UniqueName=pj,X=str(idx*5),Y="0",Z="3")])
        rows = []
        for combo in ("G", "Q"):
            for sta in (0.,1.5,3.):
                # Midspan shear must not be used to inflate same-cut alpha.
                v = shear if sta == 0 else 9000. if uid == "C1" else 5.
                rows.append((uid,sta,uid+"-1",sta,combo,"Single Value",0.,-100.,v,v,3.,-20.,40.))
        rowsets[uid] = _rowset(rows)
        dep["members"][uid] = {"story":"Zemin","joint_ids":[pi,pj],"reason_codes":[],"source_execution_allowed":True}
        for jid in (pi,pj): dep["joints"][jid] = {"blockers":[]}
        r10["per_member"][uid] = {"scwb_joints": [
            {"target_end":end,"direction":d,"engineer_selected_scwb":{"cases":[
                {"output_case":"Q","rotation_sign":sg,"reference_satisfied":sat} for sg in (-1,1)]}}
            for end in ("I","J") for d in ("X","Y")]}
        scope["configured_output_cuts"][uid] = {"status":"REQUIRED_SUBSET_BOUND","offset_i_m":0.,"length_m":3.,
                "cuts":[{"object_station_m":v,"analysis_element_id":uid+"-1","element_station_m":v} for v in (0.,1.5,3.)]}
    source = {"geometry_capture":{"tables":{
        "FRAME_ASSIGNMENTS":{"rows":frames},"COLUMN_CONNECTIVITY":{"rows":cols},
        "BEAM_CONNECTIVITY":{"rows":[]},"RECTANGULAR_SECTIONS":{"rows":[dict(Name="Rect",Material="C30",t2=".3",t3=".8")]}}},
        "vs05_delta_source":{"table_reads":{"Point Object Connectivity":{"rows":points}}},
        "column_axial":{"force_source":{"rowsets":rowsets}}}
    axial = {"combination_plan":{"source":"ASSIGNED_DESIGN","blockers":[],
              "design_assignment":{"groups":{"ductile":["Q"]}},
              "combinations":[{"name":c,"force_semantics":"STATIC_SIGNED_VECTOR","case_names":["EQ"]} for c in ("G","Q")]}}
    def table(key, rows):
        fields=list(rows[0])
        return {"table_key":key,"status":"CAPTURED","rows":rows,"row_count":len(rows),"fields":fields,
                "field_metadata":{"status":"OK","field_keys":fields,"units_by_field":dict.fromkeys(fields,"")}}
    native = {
        "Load Case Definitions - Summary":[{"Name":"EQ","Type":"Linear Static","GUID":"eq-guid"}],
        "Load Combination Definitions":[{"Name":"Q","Type":"Linear Add","LoadName":"EQ","SF":"1","GUID":"combo-guid"}],
        "Load Case Definitions - Linear Static":[{"Name":"EQ","LoadType":"Load","LoadName":"quake-pattern","SF":"1"}],
        "Load Pattern Definitions":[{"LoadPat":"quake-pattern","DesignType":"Quake","SelfWtMult":"0"}],
    }
    source["vs04_basis_probe"]={"table_reads":{key:table(key,rows) for key,rows in native.items()}}
    return source, axial, scope, dep, r10


class AlphaArithmeticContracts(unittest.TestCase):
    def test_independent_eighty_over_hundred_factor_is_one_point_two_five(self):
        self.assertEqual(alpha_feedback_factor(evaluate_story_alpha_reference(vis_kn=80,vik_kn=100)),1.25)

    def test_inclusive_seventy_boundary(self):
        self.assertAlmostEqual(alpha_feedback_factor(evaluate_story_alpha_reference(vis_kn="70",vik_kn="100")),10/7)

    def test_below_limit_does_not_produce_a_factor(self):
        self.assertIsNone(alpha_feedback_factor(evaluate_story_alpha_reference(vis_kn="69.999",vik_kn="100")))

    def test_alpha_one(self):
        self.assertEqual(alpha_feedback_factor(evaluate_story_alpha_reference(vis_kn=100,vik_kn=100)),1.)

    def test_nonfinite_and_above_one_rejected(self):
        for x in (True,float('nan'),float('inf'),1.01,-.1):
            with self.subTest(x=x), self.assertRaises(ValueError): alpha_feedback_factor({"alpha":x})


class AlphaScopeContracts(unittest.TestCase):
    def test_full_same_cut_and_exact_eligible_subset(self):
        args=two_columns(); q=qualify_story_alpha(*args)
        self.assertEqual(q['status'],'QUALIFIED_REFERENCE')
        self.assertEqual(len(q['cases']),2)
        for c in q['cases']:
            self.assertEqual((c['vis_kn'],c['vik_kn'],c['alpha'],c['factor']),(80.,100.,.8,1.25))
            self.assertEqual(c['eligible_member_ids'],['C1'])
            self.assertEqual(c['expected_member_ids'],['C1','C2'])
            self.assertFalse(c['low_axial_optional_credit_used'])

    def test_unknown_end_is_not_dropped_from_population(self):
        source,axial,scope,dep,r10=two_columns()
        r10['per_member']['C2']['scwb_joints'].pop()
        q=qualify_story_alpha(source,axial,scope,dep,r10)
        self.assertEqual(q['status'],'BLOCKED_INPUTS')
        self.assertTrue(any('TWO_END' in x for x in q['reason_codes']))

    def test_one_rotation_sign_missing_is_not_success(self):
        args=two_columns();args[-1]['per_member']['C1']['scwb_joints'][0]['engineer_selected_scwb']['cases'].pop()
        self.assertEqual(qualify_story_alpha(*args)['status'],'BLOCKED_INPUTS')

    def test_seismic_envelope_does_not_fall_back_to_gravity(self):
        args=two_columns(); args[1]['combination_plan']['combinations'][1]['force_semantics']='SCALAR_COMPONENT_ENVELOPE'
        q=qualify_story_alpha(*args)
        self.assertEqual(q['cases'],[])
        self.assertIn('ALPHA_SIGNED_SEISMIC_DEMAND_REQUIRED:Q',q['reason_codes'])

    def test_missing_required_source_cut_blocks_instead_of_max_selection(self):
        args=two_columns(); rows=args[0]['column_axial']['force_source']['rowsets']['C2']
        for k,v in rows.items():
            if isinstance(v,list): del v[3]
        rows['NumberResults']-=1
        self.assertEqual(qualify_story_alpha(*args)['status'],'BLOCKED_INPUTS')

    def test_different_bottom_elevations_block(self):
        args=two_columns(); args[0]['vs05_delta_source']['table_reads']['Point Object Connectivity']['rows'][2]['Z']='0.1'
        self.assertIn('ALPHA_COMMON_PHYSICAL_CUT_ELEVATION_UNVERIFIED',qualify_story_alpha(*args)['reason_codes'])

    def test_counteracting_shears_block(self):
        args=two_columns(); args[0]['column_axial']['force_source']['rowsets']['C2']['V2'][3]=-20.
        self.assertIn('ALPHA_COUNTERACTING_SHEARS_OUTSIDE_SUPPORTED_BRANCH',qualify_story_alpha(*args)['reason_codes'])

    def test_same_negative_orientation_is_supported(self):
        args=two_columns()
        for rows in args[0]['column_axial']['force_source']['rowsets'].values():
            for k in ('V2','V3'): rows[k]=[-v for v in rows[k]]
        self.assertEqual(qualify_story_alpha(*args)['cases'][0]['alpha'],.8)

    def test_same_cut_below_threshold_requires_system_review(self):
        args=two_columns(); rows=args[0]['column_axial']['force_source']['rowsets']['C1']
        rows['V2'][3]=rows['V3'][3]=30.
        self.assertEqual(qualify_story_alpha(*args)['status'],'REANALYSIS_REQUIRED')

    def test_no_assigned_earthquake_does_not_infer_case_names(self):
        args=two_columns();args[1]['combination_plan']['design_assignment']['groups']={}
        self.assertEqual(qualify_story_alpha(*args)['status'],'BLOCKED_INPUTS')


class AlphaDemandContracts(unittest.TestCase):
    def setup_revision(self):
        args=two_columns();q=qualify_story_alpha(*args)
        return args[0],build_demand_revision(args[0],q['cases'],input_sha='source')

    def test_only_eligible_columns_and_earthquake_m_v_change(self):
        s,r=self.setup_revision();before=deepcopy(s)
        rowsets=s['column_axial']['force_source']['rowsets']
        a=revised_force_rows(rowsets['C1'],'C1',r)
        base=revised_force_rows(rowsets['C1'],'C1')
        for x,b in zip(a,base):
            for i in range(13):
                self.assertEqual(x[i],b[i]*1.25 if b[4]=='Q' and i in (8,9,11,12) else b[i])
        self.assertEqual(revised_force_rows(rowsets['C2'],'C2',r),revised_force_rows(rowsets['C2'],'C2'))
        self.assertEqual(s,before)

    def test_revision_does_not_compound(self):
        s,r=self.setup_revision();rowset=s['column_axial']['force_source']['rowsets']['C1']
        first=revised_force_rows(rowset,'C1',r); second=revised_force_rows(rowset,'C1',r)
        self.assertEqual(first,second);self.assertEqual(second[3][8],100.)

    def test_native_state_identity_preserved(self):
        s,r=self.setup_revision(); rows=s['column_axial']['force_source']['rowsets']['C1']
        self.assertEqual([x[:7] for x in revised_force_rows(rows,'C1',r)],[x[:7] for x in revised_force_rows(rows,'C1')])

    def test_changed_base_is_rejected(self):
        s,r=self.setup_revision();rows=s['column_axial']['force_source']['rowsets']['C1']; rows['P'][0]=-101.
        with self.assertRaisesRegex(ValueError,'BASE_ROWSET_CHANGED'):revised_force_rows(rows,'C1',r)

    def test_integrity_tamper_rejected(self):
        s,r=self.setup_revision();r['factors']['C1']['Q'][0]=10
        with self.assertRaisesRegex(ValueError,'INTEGRITY'):revised_force_rows(s['column_axial']['force_source']['rowsets']['C1'],'C1',r)

    def test_orthogonal_angle_axis_mapping(self):
        from tbdy_next.engineering.column_r10_live import _csi_frame_axes
        f={'axes_global':_csi_frame_axes([0,0,0],[0,0,3],90)}
        self.assertEqual(_axis_indices(f,'X'),(9,11));self.assertEqual(_axis_indices(f,'Y'),(8,12))

    def test_oblique_axes_not_silently_projected(self):
        from tbdy_next.engineering.column_r10_live import _csi_frame_axes
        with self.assertRaisesRegex(ValueError,'ORTHOGONAL'):
            _axis_indices({'axes_global':_csi_frame_axes([0,0,0],[0,0,3],37)},'X')

    def test_unsigned_force_row_is_rejected_even_with_valid_digest(self):
        s,r=self.setup_revision();rows=s['column_axial']['force_source']['rowsets']['C1'];rows['StepType'][3]='Max'
        r['base_rowset_sha256']['C1']=_digest(rows);r=_sealed({k:v for k,v in r.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'UNSIGNED'):revised_force_rows(rows,'C1',r)

    def test_duplicate_case_and_invalid_factor(self):
        args=two_columns();cases=qualify_story_alpha(*args)['cases']
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):build_demand_revision(args[0],cases+cases,input_sha='s')
        for v in (0,2,True,float('nan')):
            rows=deepcopy(cases);rows[0]['factor']=v
            with self.subTest(v=v),self.assertRaises(ValueError):build_demand_revision(args[0],rows,input_sha='s')


class BoundedIterationContracts(unittest.TestCase):
    def run_case(self, *, changing=False, cycle=False, status='QUALIFIED_REFERENCE', feasibility=None, limit=8):
        calls=[]
        def qualify(s):
            return {'status':status,'cases':[{'factor':1.25 if not cycle or s['n']%2==0 else 1.1}]}
        def demand(cases):
            return _sealed({'schema':DEMAND_SCHEMA,'factors':{'C1':{'Q':[cases[0]['factor']]*4}}})
        def rebuild(s,r,changed):
            calls.append(changed)
            return {'n':s['n']+1,'revision':r},{'recomputed':changed}
        def sig(s): return {'C1':s['n'] if changing else s['n']%2 if cycle else 0}
        feasible=feasibility or (lambda s:{'status':'FEASIBLE_REFERENCE','reselect_member_ids':[]})
        state,record=run_bounded_feedback(initial={'n':0,'revision':None},qualify=qualify,demand=demand,rebuild=rebuild,
                signature=sig,feasible=feasible,max_iterations=limit)
        return state,record,calls

    def test_converges_and_only_dirty_member_rebuilds(self):
        _,r,calls=self.run_case();self.assertEqual(r['status'],'FIXED_POINT_REFERENCE')
        self.assertEqual(calls,[['C1']]);self.assertTrue(r['feedback_consumed'])
        validate_record(r,SCHEMA)

    def test_below_threshold_no_iteration(self):
        _,r,calls=self.run_case(status='REANALYSIS_REQUIRED');self.assertEqual(r['status'],'REANALYSIS_REQUIRED');self.assertEqual(calls,[])

    def test_missing_evidence_no_iteration(self):
        _,r,calls=self.run_case(status='BLOCKED_INPUTS');self.assertEqual(r['status'],'BLOCKED_INPUTS');self.assertEqual(calls,[])

    def test_no_passing_candidate_is_distinct_terminal_state(self):
        _,r,calls=self.run_case(feasibility=lambda s:{'status':'NO_FEASIBLE_CANDIDATE'})
        self.assertEqual(r['status'],'NO_FEASIBLE_CANDIDATE');self.assertEqual(calls,[])

    def test_cycle_is_detected(self):
        _,r,calls=self.run_case(cycle=True);self.assertEqual(r['status'],'NO_CONVERGENCE_CYCLE');self.assertLess(len(calls),8)

    def test_iteration_budget_is_enforced(self):
        _,r,calls=self.run_case(changing=True,limit=2,feasibility=lambda s:{'status':'FEASIBLE_REFERENCE','reselect_member_ids':['C1']})
        self.assertEqual(r['status'],'NO_CONVERGENCE');self.assertEqual(len(calls),2)

    def test_unresolved_local_pmm_cannot_converge(self):
        _,r,calls=self.run_case(feasibility=lambda s:{'status':'NUMERIC_OR_DEPENDENCY_UNRESOLVED'})
        self.assertFalse(r['feedback_consumed']);self.assertEqual(calls,[])

    def test_reference_is_never_normative_pass(self):
        _,r,_=self.run_case();self.assertEqual(r['engineering_release'],'NOT_READY');self.assertEqual(r['formal_compliance'],'NOT_PROVEN')

    def test_invalid_iteration_limit(self):
        for v in (0,33,True,1.5):
            with self.subTest(v=v),self.assertRaises(ValueError):self.run_case(limit=v)


class ExistingOwnerConsumption(unittest.TestCase):
    def test_actual_selection_owner_receives_revised_m_v_without_capture_change(self):
        from tbdy_next.engineering.column_r10_live import _evaluate_engineer_column_selection
        from tbdy_next.engineering.rebar_selection import normalize_column_selection_policy
        source,geometry,extra,axial,pmm=_base_live_payload(axis_angle='0')
        source['column_selection']=normalize_column_selection_policy('default')
        uid='127'; combo=axial['combination_plan']['combinations'][0]['name']
        rows=source['column_axial']['force_source']['rowsets'][uid]
        rev=_sealed({'schema':DEMAND_SCHEMA,'factors':{uid:{combo:[1.25,1,1,1.25]}},
                     'base_rowset_sha256':{uid:_digest(rows)}})
        original=deepcopy(source)
        with patch('tbdy_next.engineering.rebar_selection.select_column_rebar',return_value={'selected':None}) as owner:
            _evaluate_engineer_column_selection(uid=uid,source=source,geometry=geometry,axial=axial,angle_deg=0,demand_revision=rev)
        args=owner.call_args.kwargs
        self.assertEqual(args['demand_vectors'][0]['m3_knm'],-87.5)
        self.assertEqual(args['demand_vectors'][0]['nd_kn'],1200.)
        self.assertEqual(args['shear_demands'][0]['v2_kn'],50.)
        self.assertEqual(source,original)

    def test_ve_floor_does_not_scale_plastic_moments(self):
        from tbdy_next.engineering.column_r10_live import _compute_capacity_shear_axes
        def joint(end,direction):
            return {'target_end':end,'direction':direction,'engineer_selected_scwb':{
                'cases':[{'output_case':'Q','target_column_capacity_knm':300.}]}}
        out=_compute_capacity_shear_axes(uid='C',col_frame={'axes_global':[[0,0,1],[1,0,0],[0,1,0]]},ln_m=3.,
            scwb_joints=[joint(e,d) for e in ('I','J') for d in ('X','Y')],
            stations=[{'combination':'Q','v2_kn':500.,'v3_kn':50.}],static_combos=['Q'],rowset=None,
            section=None,use_engineer=True,vr_lookup=lambda *a:(600.,300.),demand_revision={'sha256':'rev'})
        case=out['V2']['cases'][0]
        self.assertEqual(case['ve_unreduced_kn'],280.)
        self.assertEqual(case['ve_scwb_scenario_kn'],500.)
        self.assertEqual(case['revised_vd_floor_kn'],500.)
        self.assertAlmostEqual(case['utilization_ts500'],5/6)


class AlphaRevisionIntegration(unittest.TestCase):
    """Synthetic fixture calls the production iteration driver and its owner ports."""
    def run_driver(self, no_candidate=False):
        from dataclasses import replace
        from tbdy_next.engineering.alpha_iteration import run_alpha_design_iteration
        from test_design_member_dependencies import fixture, artifacts
        source, scope = fixture()
        plan, _, _, beam, r10, cages, _, r08 = artifacts(source, scope)
        def make_feasible(uid, detail):
            detail['column_transverse_and_shear'] = {'engineer_capacity_shear_ve': {
                'axes': {axis: {'max_utilization_ts500': .5, 'cases':[{'combination':'Q','ve_scwb_scenario_kn':50.,'vr_ts500_min_kn':100.,'utilization_ts500':.5}]} for axis in ('V2','V3')}}}
            r08['per_member'][uid] = {'magnified_selected_pmm': {
                'status':'MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN', 'global_beta_ii_factor':1.,
                'expected_row_count':1, 'evaluated_row_count':1, 'resolved_row_count':1, 'max_utilization':.5}, 'open_gates':[]}
        for uid, detail in r10['per_member'].items(): make_feasible(uid, detail)
        calls=[]
        def r10_owner(s,g,a,p,e,**kwargs):
            self.assertEqual(kwargs['reselect_member_ids'],['C1'])
            self.assertIs(kwargs['beam_live'],beam)
            result=deepcopy(kwargs['previous_result'])
            result['member_dependencies']=kwargs['dependency_plan']
            result['alpha_recalculation']={'selected_member_ids':['C1'], 'joint_consumer_member_ids':['C1','C2']}
            for uid,c in kwargs['previous_cages'].items():
                kwargs['selected_cages_out'][uid]=c
                result['per_member'][uid]['engineer_column_selection']=c.selection
            if no_candidate:
                result['per_member']['C1']['engineer_column_selection']={
                    'status':'ENGINEER_COLUMN_SELECTION_NO_PASSING_CAGE', 'selected':None}
                kwargs['selected_cages_out'].pop('C1')
            calls.append(('r10',kwargs['reselect_member_ids']))
            return result
        def r08_owner(*args,**kwargs):
            self.assertEqual(kwargs['recompute_member_ids'],['C1'])
            calls.append(('r08',kwargs['recompute_member_ids']))
            return kwargs['previous_result']
        cases=[{'story':'S1','direction':d,'combination':'Q','expected_member_ids':['C1'],
                'eligible_member_ids':['C1'],'alpha':.8,'factor':1.25,'status':'QUALIFIED_REFERENCE'} for d in ('X','Y')]
        def revision(*a,**kw):
            return _sealed({'schema':DEMAND_SCHEMA,'factors':{'C1':{'Q':[1.25]*4}},
                            'input_sha256':'input-hash','source_payload_sha256':_digest(source)})
        with patch('tbdy_next.engineering.alpha_iteration.qualify_story_alpha',return_value={
                'status':'QUALIFIED_REFERENCE','cases':cases,'reason_codes':[]}), \
             patch('tbdy_next.engineering.alpha_iteration.build_demand_revision',side_effect=revision), \
             patch('tbdy_next.engineering.column_r10_live.project_column_r10_live',side_effect=r10_owner), \
             patch('tbdy_next.engineering.column_r08_local_live.project_column_r08_local_live',side_effect=r08_owner):
            state,candidates,record=run_alpha_design_iteration(source=source,geometry={},axial={},pmm={},extra={},
                scope=scope,dependencies=plan,r10=r10,r08=r08,cages=cages,beam=beam,
                global_pdelta={},input_sha='input-hash')
        return source,scope,state,candidates,record,calls

    def test_production_driver_converges_and_seals_same_selected_outputs(self):
        _,_,state,cand,r,calls=self.run_driver()
        self.assertEqual(r['status'],'FIXED_POINT_REFERENCE')
        self.assertEqual(calls,[('r10',['C1']),('r08',['C1'])])
        self.assertEqual(r['iteration_count'],1)
        self.assertEqual(r['final_candidate_ledger_sha256'],_digest(cand))
        self.assertEqual(state['r10']['story_alpha']['stories'][0]['governing_alpha_i'],.8)
        self.assertEqual(r['trace'][0]['actions']['joint_consumer_member_ids'],['C1','C2'])
        self.assertFalse(r['trace'][0]['actions']['beam_owner_reexecuted'])
        validate_record(r,SCHEMA)

    def test_no_passing_cage_does_not_return_fixed_point(self):
        _,_,_,_,r,calls=self.run_driver(no_candidate=True)
        self.assertEqual(r['status'],'NO_FEASIBLE_CANDIDATE')
        self.assertFalse(r['feedback_consumed']); self.assertEqual(len(calls),2)

    def test_revision_ledger_consumes_verified_iteration_and_rejects_tamper(self):
        from tbdy_next.engineering.design_dependencies import build_revision_evidence
        _,_,state,cand,r,_=self.run_driver()
        ev=build_revision_evidence(state['dependencies'],cand,state['r10'],state['r08'],input_sha='input-hash')
        self.assertTrue(ev['alpha_demand_iteration_implemented'])
        self.assertTrue(ev['columns']['C1']['alpha_feedback_consumed'])
        self.assertIn('alpha-iteration',ev['artifacts'])
        state['r10']['alpha_iteration']['feedback_consumed']=False
        with self.assertRaisesRegex(ValueError,'INTEGRITY'):
            build_revision_evidence(state['dependencies'],cand,state['r10'],state['r08'],input_sha='input-hash')

    def test_foreign_iteration_source_and_candidate_ledger_are_rejected(self):
        from tbdy_next.engineering.design_dependencies import build_revision_evidence
        for field in ('input_sha256','final_candidate_ledger_sha256'):
            _,_,state,cand,r,_=self.run_driver()
            altered={k:v for k,v in r.items() if k!='sha256'}; altered[field]='foreign'
            state['r10']['alpha_iteration']=_sealed(altered)
            with self.subTest(field=field),self.assertRaises(ValueError):
                build_revision_evidence(state['dependencies'],cand,state['r10'],state['r08'],input_sha='input-hash')


class SelectiveR08Contracts(unittest.TestCase):
    def fixture(self):
        from test_design_member_dependencies import fixture,artifacts
        from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
        source,scope=fixture();p,_,_,_,r10,cages,_,_=artifacts(source,scope)
        pmm={'scope':'ALL_COLUMNS','member_id':'ALL','members':[{'member_id':u} for u in p['members']]}
        def inner(*args,**kw): return {'member_id':args[3]['member_id'],'open_gates':[]}
        with patch('tbdy_next.engineering.column_r08_local_live._project_single_r08_local',side_effect=inner):
            previous=project_column_r08_local_live(source,{}, {},pmm,r10_live=r10,selected_cages=cages,dependency_plan=p)
        return source,p,r10,cages,pmm,previous,inner

    def test_only_changed_member_is_executed_and_other_results_reused(self):
        from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
        s,p,r10,cages,pmm,previous,inner=self.fixture()
        with patch('tbdy_next.engineering.column_r08_local_live._project_single_r08_local',side_effect=inner) as owner:
            out=project_column_r08_local_live(s,{}, {},pmm,r10_live=r10,selected_cages=cages,dependency_plan=p,
                    previous_result=previous,recompute_member_ids=['C1'])
        self.assertEqual(owner.call_count,1);self.assertEqual(owner.call_args.args[3]['member_id'],'C1')
        self.assertIs(out['per_member']['C2'],previous['per_member']['C2'])
        self.assertEqual(out['expected_column_count'],3)

    def test_changed_pmm_member_or_global_order_cannot_reuse_old_result(self):
        from tbdy_next.engineering.column_r08_local_live import project_column_r08_local_live
        for change in ('pmm','global'):
            s,p,r10,cages,pmm,previous,_=self.fixture()
            global_order=None
            if change=='pmm':pmm['members'][1]['changed_demand']=1
            else:global_order={'beta':1.2}
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'INPUT_REVISION_CHANGED'):
                project_column_r08_local_live(s,{}, {},pmm,global_order,r10_live=r10,selected_cages=cages,
                    dependency_plan=p,previous_result=previous,recompute_member_ids=[])

    def test_r10_rejects_changed_alpha_factor_excluded_from_dirty_scope(self):
        from tbdy_next.engineering.column_r10_live import project_column_r10_live
        s,p,r10,cages,pmm,previous,_=self.fixture()
        r10['member_dependencies']=p
        rev=_sealed({'schema':DEMAND_SCHEMA,'factors':{'C1':{'Q':[1.25]*4}},
                     'input_sha256':'input-hash','source_payload_sha256':_digest(s)})
        with self.assertRaisesRegex(ValueError,'OMITTED_FROM_RESELECTION'):
            project_column_r10_live(s,{}, {},pmm,dependency_plan=p,demand_revision=rev,
                                   previous_result=r10,previous_cages=cages,reselect_member_ids=[])


class SecondOrderConstraintContracts(unittest.TestCase):
    def test_magnified_vector_retains_element_side_identity(self):
        rows=[{'combination':'Q','object_station_m':1.,'analysis_element_id':e,'element_station_m':st,
               'nd_kn':nd} for e,st,nd in [('a',1.,10.),('b',0.,20.)]]
        magnified=[dict(r,magnified_m2_design_knm=2*r['nd_kn'],magnified_m3_design_knm=-3*r['nd_kn']) for r in rows]
        state={'r08':{'per_member':{'C':{'magnified_selected_pmm':{'status':'MAGNIFIED_PMM_EXCEEDS_CAPACITY','rows':magnified}}}}}
        m,v=_selection_constraints(state,{'members':[{'member_id':'C','rows':rows}]},['C'])
        self.assertEqual([r['nd_kn'] for r in m['C']],[10.,20.])
        self.assertEqual([r['m3_knm'] for r in m['C']],[-30.,-60.])
        self.assertEqual([r['analysis_element_id'] for r in m['C']],['a','b'])
        self.assertEqual(v,{})

    def test_changed_axial_identity_not_repaired_by_joining_extrema(self):
        original={'combination':'Q','object_station_m':1.,'analysis_element_id':'a','element_station_m':1.,'nd_kn':10.}
        changed=dict(original,nd_kn=20.,magnified_m2_design_knm=1.,magnified_m3_design_knm=2.)
        state={'r08':{'per_member':{'C':{'magnified_selected_pmm':{'status':'MAGNIFIED_PMM_EXCEEDS_CAPACITY','rows':[changed]}}}}}
        with self.assertRaisesRegex(ValueError,'IDENTITY'):
            _selection_constraints(state,{'members':[{'member_id':'C','rows':[original]}]},['C'])


class SeismicSourceQualification(unittest.TestCase):
    def test_design_group_name_cannot_replace_native_earthquake_provenance(self):
        args=two_columns(); args[0].pop('vs04_basis_probe')
        q=qualify_story_alpha(*args)
        self.assertEqual(q['status'],'BLOCKED_INPUTS')
        self.assertTrue(q['reason_codes'][0].startswith('ALPHA_SEISMIC_SHEAR_PROVENANCE_UNVERIFIED'))

    def test_gravity_or_selfweight_pattern_is_not_earthquake_shear(self):
        for key,value in (('DesignType','Dead'),('SelfWtMult','1')):
            args=two_columns();rows=args[0]['vs04_basis_probe']['table_reads']['Load Pattern Definitions']['rows']
            rows[0][key]=value
            q=qualify_story_alpha(*args)
            self.assertEqual(q['status'],'BLOCKED_INPUTS')
            self.assertIn('EARTHQUAKE_ONLY_SHEAR_NOT_SEPARATED',q['reason_codes'][0])

    def test_case_lineage_conflict_blocks(self):
        args=two_columns(); args[1]['combination_plan']['combinations'][1]['case_names']=['other']
        self.assertEqual(qualify_story_alpha(*args)['status'],'BLOCKED_INPUTS')

    def test_report_is_a_projection_and_escapes_untrusted_reason(self):
        from tbdy_next.reporting import _alpha_feedback_html
        record={'status':'BLOCKED_INPUTS','iteration_count':0,'max_iterations':8,'feedback_consumed':False,
                'sha256':'s','trace':[],'final_qualification':{'cases':[],'reason_codes':['<script>unsafe</script>']}}
        with patch('tbdy_next.engineering.alpha_iteration.qualify_story_alpha',side_effect=AssertionError('report recalculation')) as owner:
            html=_alpha_feedback_html(record)
        owner.assert_not_called()
        self.assertIn('BLOCKED_INPUTS',html);self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)

    def test_registry_has_one_alpha_owner_and_typed_contracts(self):
        from tbdy_next.engineering.pipeline import STAGES, _validate_dependency_contracts
        _validate_dependency_contracts()
        stages=[s for s in STAGES if s.key=='alpha-feedback']
        self.assertEqual(len(stages),1)
        self.assertIn('r10_live',[c.key for c in stages[0].consumes])
        self.assertEqual([c.key for c in stages[0].produces],['alpha_iteration'])

    def test_finite_utilization_and_resolved_count_required_for_convergence(self):
        # Source and numerical failures may never be repaired by a truthy status label.
        states=[{'global_beta_ii_factor':float('nan')}, {'resolved_row_count':0}, {'max_utilization':float('nan')}]
        for mutation in states:
            mag={'status':'MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN','global_beta_ii_factor':1.,
                 'evaluated_row_count':1,'resolved_row_count':1,'expected_row_count':1,'max_utilization':.5,**mutation}
            state={'dependencies':{'members':{'C':{}}},'r10':{'per_member':{'C':{'engineer_column_selection':{'selected':{'label':'c'}}}}},
                   'r08':{'per_member':{'C':{'magnified_selected_pmm':mag}}}}
            self.assertEqual(_feasibility(state)['status'],'NUMERIC_OR_DEPENDENCY_UNRESOLVED')
