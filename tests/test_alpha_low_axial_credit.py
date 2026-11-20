"""Signed alpha consumer examples, with real axial/end-evidence owners.

The inherited SCWB Boolean fixture is an explicit consumer contract. This is
not a whole-building capacity/selection example or a spectral-alpha approval.
"""
from copy import deepcopy
import unittest

from test_mixed_design_demands import mixed_fixture
from test_r10_live import _rowset
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.engineering.alpha_iteration import qualify_story_alpha, build_demand_revision, revised_force_rows
from tbdy_next.engineering.column_axial import _member_result
from tbdy_next.engineering.column_r10_live import _build_frame_catalog
from tbdy_next.engineering.design_dependencies import SCHEMA as DEPENDENCY_SCHEMA
from tbdy_next.engineering.design_scenario import _digest
from tbdy_next.engineering.scwb_axial import joint_low_axial_decisions
from tbdy_next.reporting import _alpha_feedback_html


def credit_fixture(*, target_nd=340., middle_nd=None):
    source, axial, scope, dep, r10 = mixed_fixture()
    tables = source['geometry_capture']['tables']
    points = source['vs05_delta_source']['table_reads']['Point Object Connectivity']['rows']
    forces = source['column_axial']['force_source']
    forces.update(schema='tbdy.next.etabs-frame-force-source.v1', api='Results.FrameForce', units_code=6)
    rowsets = forces['rowsets']
    # The one story's earthquake shears are 60, 20, 20. C1 satisfies both-end
    # Eq.7.3; C2 receives optional low-N credit; C3 satisfies neither branch.
    third = []
    for row in native_frame_force_rows(rowsets['C2'], 'C2'):
        r=list(row);r[0]='C3';r[2]='C3-1';r[7]=-900. if r[4]=='Q' else -200.;third.append(tuple(r))
    rowsets['C3']=_rowset(third)
    r10['per_member']['C3']=deepcopy(r10['per_member']['C2'])
    for sta, name in enumerate(('C1','C2','C3')):
        if name=='C3':
            tables['FRAME_ASSIGNMENTS']['rows'].append(dict(UniqueName=name,Type='Column',AnalysisSect='Rect',AxisAngle='0',Story='Zemin'))
            tables['COLUMN_CONNECTIVITY']['rows'].append(dict(UniqueName=name,Story='Zemin',UniquePtI=name+'I',UniquePtJ=name+'J',Length='3'))
            points.extend([dict(UniqueName=name+'I',X='10',Y='0',Z='0'),dict(UniqueName=name+'J',X='10',Y='0',Z='3')])
            dep['members'][name]=deepcopy(dep['members']['C2']);dep['members'][name]['joint_ids']=['C3I','C3J']
            dep['joints'].update(C3I={'blockers':[]},C3J={'blockers':[]})
            dep['story_columns']['Zemin'].append(name)
        rows=list(native_frame_force_rows(rowsets[name],name))
        changed=[]
        for row in rows:
            r=list(row)
            if name=='C1' and row[4]=='Q' and row[1]==0:r[8]=r[9]=180. # 180 - 1.2*100 = 60
            if name=='C2' and row[4]=='Q':r[7]=-(middle_nd if row[1]==1.5 and middle_nd is not None else target_nd)
            changed.append(tuple(r))
        rowsets[name]=_rowset(changed)
    # Neighboring columns at C2's two ends deliberately exceed their own
    # low-N limits. The target may still receive per-column alpha credit.
    for uid,pi,pj,z0,z1 in [('L2','L2I','C2I',-3.,0.),('U2','C2J','U2J',3.,6.)]:
        tables['FRAME_ASSIGNMENTS']['rows'].append(dict(UniqueName=uid,Type='Column',AnalysisSect='Rect',AxisAngle='0',Story='Neighbor'))
        tables['COLUMN_CONNECTIVITY']['rows'].append(dict(UniqueName=uid,Story='Neighbor',UniquePtI=pi,UniquePtJ=pj,Length='3'))
        point_name=pi if uid=='L2' else pj
        points.append(dict(UniqueName=point_name,X='5',Y='0',Z=str(z0 if uid=='L2' else z1)))
        rowsets[uid]=_rowset([(uid,s,uid+'-1',s,c,'Single Value',0.,-900. if c=='Q' else -200.,0.,0.,0.,0.,0.)
                            for c in ('G','Q') for s in (0.,1.5,3.)])
    for end,z in [('I',0.),('J',3.)]:
        uid='B2'+end;point=uid+'tip'
        tables['FRAME_ASSIGNMENTS']['rows'].append(dict(UniqueName=uid,Type='Beam',AnalysisSect='Rect',AxisAngle='0',Story='Neighbor'))
        tables['BEAM_CONNECTIVITY']['rows'].append(dict(UniqueName=uid,Story='Neighbor',UniquePtI='C2'+end,UniquePtJ=point,Length='5'))
        points.append(dict(UniqueName=point,X='10',Y='0',Z=str(z)))
    axial['combination_plan']['design_assignment']['groups']['gravity']=['G']
    axial['columns']=[]
    for uid, rowset in rowsets.items():
        member=dict(element_id=uid,story='Zemin' if uid in ('C1','C2','C3') else 'Neighbor',section='Rect',
                    material_name='C30',status='RESOLVED',material_classification='RESOLVED_CONCRETE_USAGE',
                    section_design_difference=False,analysis_section='Rect',width_mm=300.,depth_mm=800.)
        axial['columns'].append(_member_result(member,axial['combination_plan'],rowset,fck=30.,gamma_c=1.5,source_error=None))
    frames,coords,graph=_build_frame_catalog(source)
    scope.update(input_sha256='bound-source',analysis_mesh={'members':{}})
    for uid in rowsets:
        f=frames[uid]
        scope['analysis_mesh']['members'][uid]={'roster_bound':True,'expected_analysis_element_ids':[uid+'-1'],
            'analysis_element_end_joints':{uid+'-1':[f['point_i'],f['point_j']]}}
        scope['configured_output_cuts'][uid]={'status':'REQUIRED_SUBSET_BOUND','offset_i_m':0.,'offset_j_m':0.,'length_m':3.,
            'cuts':[dict(object_station_m=s,analysis_element_id=uid+'-1',element_station_m=s) for s in (0.,1.5,3.)]}
    dep.update(schema=DEPENDENCY_SCHEMA,input_sha256='bound-source',source_payload_sha256=_digest(source))
    dep['joints']['C2I']['column_ids']=['L2','C2']
    dep['joints']['C2J']['column_ids']=['C2','U2']
    decisions=joint_low_axial_decisions(source,axial,scope,None,dep,frames,coords,graph['adjacency'],['Q'],input_sha='bound-source')
    for row in r10['per_member']['C2']['scwb_joints']:
        row['low_axial_exception']=decisions['C2'+row['target_end']]
    return source,axial,scope,dep,r10


class AlphaLowAxialCreditTests(unittest.TestCase):
    def test_independent_eighty_over_hundred_credit_does_not_claim_eq73(self):
        args=credit_fixture();before=deepcopy(args)
        result=qualify_story_alpha(*args)
        self.assertEqual(result['status'],'QUALIFIED_REFERENCE')
        for case in result['cases']:
            self.assertEqual((case['vis_kn'],case['vik_kn'],case['alpha'],case['factor']),(80.,100.,.8,1.25))
            self.assertEqual(case['eligible_member_ids'],['C1','C2'])
            self.assertEqual(case['amplification_member_ids'],['C1'])
            self.assertEqual(case['low_axial_credit_member_ids'],['C2'])
            term=next(t for t in case['terms'] if t['member_id']=='C2')
            self.assertFalse(term['two_end_scwb_satisfied'])
            self.assertTrue(term['low_axial_credit_used'])
            self.assertEqual(term['low_axial_credit']['limit_kn'],720.)
        self.assertEqual(args,before)
        self.assertEqual(args[-1]['per_member']['C2']['scwb_joints'][0]['low_axial_exception']['status'],'LOW_AXIAL_LIMIT_EXCEEDED')

    def test_credit_only_column_is_not_amplified(self):
        args=credit_fixture();cases=qualify_story_alpha(*args)['cases']
        revision=build_demand_revision(args[0],cases,input_sha='bound-source')
        self.assertEqual(set(revision['factors']),{'C1'})
        rows=args[0]['column_axial']['force_source']['rowsets']['C2']
        self.assertEqual(revised_force_rows(rows,'C2',revision),revised_force_rows(rows,'C2'))

    def test_inclusive_boundary_and_exceedance(self):
        for nd,eligible in [(720.,True),(720.000000001,False)]:
            with self.subTest(nd=nd):
                result=qualify_story_alpha(*credit_fixture(target_nd=nd))
                self.assertEqual(result['status'],'QUALIFIED_REFERENCE' if eligible else 'REANALYSIS_REQUIRED')
                self.assertEqual(result['cases'][0]['low_axial_optional_credit_used'],eligible)

    def test_interior_maximum_blocks_credit_despite_low_both_ends(self):
        result=qualify_story_alpha(*credit_fixture(middle_nd=900.))
        self.assertEqual(result['status'],'REANALYSIS_REQUIRED')
        case=result['cases'][0]
        self.assertEqual(case['alpha'],.6)
        target=next(t for t in case['terms'] if t['member_id']=='C2')
        self.assertEqual(target['low_axial_credit']['member_max_compression_by_combination_kn']['Q'],900.)
        self.assertFalse(target['low_axial_credit_used'])

    def test_missing_moment_ratio_can_use_valid_credit_but_not_missing_end_evidence(self):
        args=credit_fixture()
        for row in args[-1]['per_member']['C2']['scwb_joints']:row['engineer_selected_scwb']['cases']=[]
        self.assertEqual(qualify_story_alpha(*args)['status'],'QUALIFIED_REFERENCE')
        args[-1]['per_member']['C2']['scwb_joints'][0].pop('low_axial_exception')
        result=qualify_story_alpha(*args)
        self.assertEqual(result['status'],'BLOCKED_INPUTS')
        self.assertTrue(any('ALPHA_LOW_N_END_EVIDENCE_UNBOUND' in c for c in result['reason_codes']))
        self.assertEqual(result['cases'][0]['expected_member_ids'],['C1','C2','C3'])

    def test_stale_source_cut_and_nonfinite_proofs_cannot_supply_credit(self):
        for defect in ('source','cut','nonfinite','maximum'):
            with self.subTest(defect=defect):
                args=credit_fixture()
                for row in args[-1]['per_member']['C2']['scwb_joints']:row['engineer_selected_scwb']['cases']=[]
                proof=args[-1]['per_member']['C2']['scwb_joints'][0]['low_axial_exception']
                target=next(e for e in proof['column_ends'] if e['member_id']=='C2')
                if defect=='source':args[0]['changed_revision']='not-the-recorded-source'
                elif defect=='cut':target['configured_cut'][2]='other-element'
                elif defect=='nonfinite':target['configured_cut'][1]=float('nan')
                else:target['nd_max_by_combination_kn']['Q']=340.0000000001
                self.assertEqual(qualify_story_alpha(*args)['status'],'BLOCKED_INPUTS')

    def test_ambiguous_amplification_membership_is_rejected(self):
        args=credit_fixture();cases=qualify_story_alpha(*args)['cases']
        cases[0].pop('amplification_member_ids')
        with self.assertRaisesRegex(ValueError,'AMPLIFICATION_ELIGIBILITY_UNBOUND'):
            build_demand_revision(args[0],cases,input_sha='bound-source')

    def test_normal_report_distinguishes_credit_and_amplification(self):
        result=qualify_story_alpha(*credit_fixture())
        html=_alpha_feedback_html({'final_qualification':result,'trace':[]})
        self.assertIn('Vis columns',html)
        self.assertIn('1/alpha columns',html)
        self.assertIn('Optional low-N credit',html)


if __name__=='__main__':
    unittest.main()
