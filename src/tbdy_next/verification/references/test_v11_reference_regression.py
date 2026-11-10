import math
import unittest
from tbdy_column_workflow.recipe_v11.decisions import (
    GateError, SecondOrderSource, ForceState,LocalOnlyResult,select_second_order, concurrent_state,
    story_stability,beta_individual,eq729_choice,vc_zero_signed,
    scwb_at_joint,scwb_low_axial_exemption,story_alpha,capacity_design_shear,
    panel_confined,panel_bj_centered,panel_shear,result_status)
from tbdy_column_workflow.recipe_v11.pmm import (Bar,RectSection,PMMError,response,
                                     solve_c_at_n,pmm_utilization,ray_intersections)


def s400():
    return RectSection(400,400,30,1.5,420,1.15,.82,
                       tuple(Bar(x,y,20) for x in (-140,0,140) for y in (-140,140)))

class DecisionTests(unittest.TestCase):
    def st(self,source=SecondOrderSource.FIRST_ORDER):
        return ForceState('rev:run:member:combo:station:face',500,30,-40,12,8,source)
    def err(self,code,func,*a,**kw):
        with self.assertRaises(GateError) as e:func(*a,**kw)
        self.assertEqual(e.exception.code,code)

    def test_second_order_exactly_once(self):
        a=select_second_order(self.st(),1.5,1.3)
        self.assertEqual((a.m2_knm,a.m3_knm),(45,-52))
        self.assertEqual((a.v2_kn,a.signed_n_kn),(12,500))
        self.err('DUPLICATE_TS500_MAGNIFICATION',select_second_order,a,1.5,1.3)
    def test_second_order_global_needs_split_method(self):
        self.err('LOCAL_ONLY_METHOD_UNQUALIFIED',select_second_order,self.st(SecondOrderSource.GLOBAL_ONLY),1.5,1.3)
    def test_second_order_global_proof_still_no_full_beta(self):
        proof={'approved':True,'source_origin':self.st().origin,'method':'LOCAL_ONLY_QUALIFIED'}
        self.err('FULL_BETA_FORBIDDEN_AFTER_GLOBAL_PDELTA',select_second_order,self.st(SecondOrderSource.GLOBAL_ONLY),1.5,1.3,local_only_proof=proof)
        self.err('LOCAL_ONLY_RESULTS_MISSING',select_second_order,self.st(SecondOrderSource.GLOBAL_ONLY),local_only_proof=proof)
    def test_global_only_requires_actual_local_result_and_evidence(self):
        proof={'approved':True,'source_origin':self.st().origin,'method':'LOCAL_ONLY_QUALIFIED'}
        local=LocalOnlyResult(self.st().origin,35,-46,'solver-run-7')
        y=select_second_order(self.st(SecondOrderSource.GLOBAL_ONLY),local_only_proof=proof,local_only_result=local)
        self.assertEqual((y.m2_knm,y.m3_knm,y.source_mode),(35,-46,SecondOrderSource.GENERAL_BOTH))
        self.err('DUPLICATE_SECOND_ORDER_COVERAGE',select_second_order,y,1.2,1.2)
    def test_global_only_rejects_stale_local_source(self):
        proof={'approved':True,'source_origin':self.st().origin,'method':'LOCAL_ONLY_QUALIFIED'}
        local=LocalOnlyResult('foreign-origin',35,-46,'solver-run-7')
        self.err('LOCAL_ONLY_SOURCE_OR_EVIDENCE_INVALID',select_second_order,
                 self.st(SecondOrderSource.GLOBAL_ONLY),local_only_proof=proof,local_only_result=local)
    def test_second_order_full_both_no_repeat(self):
        self.assertEqual(select_second_order(self.st(SecondOrderSource.GENERAL_BOTH)),self.st(SecondOrderSource.GENERAL_BOTH))
        self.err('DUPLICATE_SECOND_ORDER_COVERAGE',select_second_order,self.st(SecondOrderSource.GENERAL_BOTH),1,1)
    def test_second_order_beta_negative(self):
        self.err('BETA_LESS_THAN_ONE',select_second_order,self.st(),.99,1.0)
    def test_second_order_applied_history(self):
        state=self.st()
        e=ForceState(state.origin,500,30,-40,12,8,SecondOrderSource.FIRST_ORDER,('OLD_GLOBAL',))
        self.err('UNQUALIFIED_PREVIOUS_EFFECTS',select_second_order,e,1.2,1.3)
    def test_concurrency_ok(self):
        p={k:{'origin':'A','semantics':'SIGNED_CONCURRENT','value':v} for k,v in zip(('N','M2','M3','V2','V3'),(500,11,12,13,14))}
        self.assertEqual(concurrent_state('A',p),(500,11,12,13,14))
    def test_concurrency_mixed(self):
        p={k:{'origin':'A','semantics':'SIGNED_CONCURRENT','value':v} for k,v in zip(('N','M2','M3','V2','V3'),(500,11,12,13,14))}
        p['M3']['origin']='B'
        self.err('MIXED_FORCE_STATES',concurrent_state,'A',p)
    def test_concurrency_abs_envelope(self):
        p={k:{'origin':'A','semantics':'SIGNED_CONCURRENT','value':1} for k in ('N','M2','M3','V2','V3')}
        p['M2']['semantics']='ENVELOPE_ABS'
        self.err('NONCONCURRENT_ENVELOPE',concurrent_state,'A',p)
    def test_concurrency_missing_axis(self):
        p={k:{'origin':'A','semantics':'SIGNED_CONCURRENT','value':1} for k in ('N','M2','M3','V2')}
        self.err('FORCE_FIELDS_INCOMPLETE',concurrent_state,'A',p)
    def test_story_sway_at_equality(self):
        a=story_stability(.05,100,300,census_digest='hash',case_id='C1')
        self.assertFalse(a['sway'])
    def test_story_sway_above(self):
        a=story_stability(.0500001,100,300,census_digest='hash',case_id='C1')
        self.assertTrue(a['sway'])
    def test_story_sum_limit(self):
        self.err('TS500_7_28_REDESIGN',story_stability,.06,451,1000,census_digest='h',case_id='c')
        self.assertTrue(story_stability(.06,450,1000,census_digest='h',case_id='c')['sway'])
    def test_story_missing_population(self):
        self.err('STORY_CENSUS_UNQUALIFIED',story_stability,.06,100,300,census_digest='',case_id='c')
    def test_beta_denominator_correct(self):
        self.assertAlmostEqual(beta_individual(471.11,1727.29,1),1/(1-1.3*471.11/1727.29))
    def test_beta_instability(self):
        self.err('APPROXIMATE_METHOD_UNSTABLE',beta_individual,100,130,1)
    def test_eq729_from_golden(self):
        d=eq729_choice(5000,5230,86.60254,471.11,30,90000,1.54935,1.19276,approved_policy='FREE_LENGTH_TEXT_V1')
        self.assertEqual(d['selected']['branch'],'MAX')
        self.assertEqual(d['printed']['branch'],'MAX')
    def test_eq729_interpretation_divergence(self):
        nd= (35/60)**2*30*160000/1000
        d=eq729_choice(4000,6000,80,nd,30,160000,1.5,1.2,approved_policy='FREE_LENGTH_TEXT_V1')
        self.assertEqual((d['textual']['branch'],d['printed']['branch']),('MAX','PRODUCT'))
        self.assertTrue(d['different']);self.assertEqual(d['selected']['factor'],1.5)
        d2=eq729_choice(4000,6000,80,nd,30,160000,1.5,1.2,approved_policy='PRINTED_EFFECTIVE_V1')
        self.assertAlmostEqual(d2['selected']['factor'],1.8)
    def test_eq729_unapproved(self):
        self.err('NORMATIVE_POLICY_UNAPPROVED',eq729_choice,4000,6000,80,500,30,160000,1.5,1.2,approved_policy=None)
    def test_eq729_missing_ln(self):
        self.err('FREE_LENGTH_NOT_PROVEN',eq729_choice,None,6000,80,500,30,160000,1.5,1.2,approved_policy='FREE_LENGTH_TEXT_V1')
    def test_eq729_tension_not_sway_compression(self):
        self.err('EQ729_REQUIRES_POSITIVE_COMPRESSION',eq729_choice,4000,6000,80,-500,30,160000,1.5,1.2,approved_policy='FREE_LENGTH_TEXT_V1')
    def test_vc0_positive_case(self):
        self.assertTrue(vc_zero_signed(is_confinement=True,Vseismic=60,Vgravity=10,Vtotal=70,nd_kn=135,ac_mm2=90000,fck_mpa=30))
    def test_vc0_axial_boundary(self):
        self.assertFalse(vc_zero_signed(is_confinement=True,Vseismic=60,Vgravity=10,Vtotal=70,nd_kn=135.001,ac_mm2=90000,fck_mpa=30))
    def test_vc0_half_equality(self):
        self.assertFalse(vc_zero_signed(is_confinement=True,Vseismic=50,Vgravity=50,Vtotal=100,nd_kn=0,ac_mm2=90000,fck_mpa=30))
    def test_vc0_tension(self):
        self.assertTrue(vc_zero_signed(is_confinement=True,Vseismic=-70,Vgravity=-20,Vtotal=-90,nd_kn=-100,ac_mm2=90000,fck_mpa=30))
    def test_vc0_zone_requirement(self):
        self.assertFalse(vc_zero_signed(is_confinement=False,Vseismic=60,Vgravity=10,Vtotal=70,nd_kn=0,ac_mm2=90000,fck_mpa=30))
    def test_vc0_decomposition_must_balance(self):
        self.err('SHEAR_COMPOSITION_INCONSISTENT',vc_zero_signed,is_confinement=True,Vseismic=60,Vgravity=10,Vtotal=60,nd_kn=0,ac_mm2=90000,fck_mpa=30)
    def test_vc0_cancellation(self):
        self.err('SHEAR_TOTAL_CANCELLATION_UNQUALIFIED',vc_zero_signed,is_confinement=True,Vseismic=60,Vgravity=-60,Vtotal=0,nd_kn=0,ac_mm2=90000,fck_mpa=30)
    def test_scwb_pass_and_fail(self):
        self.assertTrue(scwb_at_joint(200,200,100,100,complete_graph=True,exception=None)['pass'])
        self.assertFalse(scwb_at_joint(100,100,100,100,complete_graph=True,exception=None)['pass'])
    def test_scwb_missing_member(self):
        self.err('SCWB_CAPACITY_INCOMPLETE',scwb_at_joint,100,None,100,100,complete_graph=True,exception=None)
    def test_scwb_missing_graph(self):
        self.err('SCWB_JOINT_GRAPH_INCOMPLETE',scwb_at_joint,100,100,100,100,complete_graph=False,exception=None)
    def test_scwb_exemption_not_pass(self):
        d=scwb_at_joint(None,None,None,None,complete_graph=True,exception='TOP_NON_CONTINUING',exception_proof=True)
        self.assertIsNone(d['pass']);self.assertEqual(d['applicability'],'EXEMPT_BY_CODE')
        self.err('SCWB_EXEMPTION_UNPROVEN',scwb_at_joint,None,None,None,None,complete_graph=True,exception='TOP_NON_CONTINUING')
    def test_scwb_low_nd_two_columns_equality(self):
        self.assertTrue(scwb_low_axial_exemption(270,270,90000,90000,30,30))
        self.assertFalse(scwb_low_axial_exemption(270,270.01,90000,90000,30,30))
        self.assertTrue(scwb_low_axial_exemption(-10,-20,90000,90000,30,30))
    def test_alpha_below_limit(self):
        d=story_alpha({'A':69,'B':31},{'A'},('A','B'),'EX_POS');self.assertEqual(d['branch'],'RECLASSIFY_AND_REANALYZE')
    def test_alpha_equal_limit(self):
        d=story_alpha({'A':70,'B':30},{'A'},('A','B'),'EX_POS');self.assertAlmostEqual(d['eligible_factor'],10/7)
    def test_alpha_one(self):
        d=story_alpha({'A':70,'B':30},{'A','B'},('A','B'),'EX_POS');self.assertEqual(d['eligible_factor'],1)
    def test_alpha_incomplete(self):
        self.err('STORY_ALPHA_CENSUS_INCOMPLETE',story_alpha,{'A':70},{'A'},('A','B'),'EX_POS')
    def test_alpha_zero(self):
        self.err('STORY_ALPHA_ZERO_DENOMINATOR',story_alpha,{'A':0,'B':0},{'A'},('A','B'),'EX_POS')
    def test_capacity_shear_min_D_but_not_below_vd(self):
        self.assertAlmostEqual(capacity_design_shear(120,180,3000,80,50,end_a_authority='COLUMN_PLASTIC',end_u_authority='SCWB_BEAM_PLASTIC'),80)
        self.assertAlmostEqual(capacity_design_shear(120,180,3000,20,50,end_a_authority='COLUMN_PLASTIC',end_u_authority='SCWB_BEAM_PLASTIC'),50)
    def test_capacity_shear_no_authority(self):
        self.err('END_MOMENT_AUTHORITY_MISSING',capacity_design_shear,120,180,3000,80,None,end_a_authority='',end_u_authority='COLUMN_PLASTIC')
    def test_panel_class_four_faces_threshold(self):
        self.assertTrue(panel_confined(dict.fromkeys('EWNS',300),dict.fromkeys('EWNS',400),True))
        self.assertFalse(panel_confined({'E':300,'W':300,'N':300},dict.fromkeys('EWNS',400),True))
        self.assertFalse(panel_confined(dict.fromkeys('EWNS',299),dict.fromkeys('EWNS',400),True))
    def test_panel_graph_missing(self):
        self.err('JOINT_TOPOLOGY_UNQUALIFIED',panel_confined,dict.fromkeys('EWNS',300),dict.fromkeys('EWNS',400),False)
    def test_bj_supported_centered_only(self):
        self.assertEqual(panel_bj_centered(400,300,300,certified_fig710_geometry=True,aligned_centered=True),400)
        self.assertEqual(panel_bj_centered(400,150,150,certified_fig710_geometry=True,aligned_centered=True),300)
        self.err('PANEL_BJ_GEOMETRY_NOT_QUALIFIED',panel_bj_centered,400,300,300,certified_fig710_geometry=False,aligned_centered=True)
    def test_panel_shear_min_col(self):
        self.assertAlmostEqual(panel_shear(500,500,420,40,50),1.25*420-40)
    def test_panel_shear_sign_unqualified(self):
        self.err('PANEL_SHEAR_SIGN_UNQUALIFIED',panel_shear,500,500,420,40,-50)
    def test_result_pass_contract(self):
        self.assertEqual(result_status('REQUIRED','SOLVED','PASS','COMPLETE')['compliance'],'PASS')
        self.err('INVALID_PASS_STATE',result_status,'REQUIRED','INCOMPLETE','PASS','COMPLETE')
        self.err('EXEMPTION_IS_NOT_PASS',result_status,'EXEMPT_BY_CODE','SOLVED','FAIL','COMPLETE')

class PMMTests(unittest.TestCase):
    def test_real_cage_inside(self):
        s=s400();s.validate();self.assertEqual(len(s.bars),6)
    def test_bar_overlap_fails(self):
        s=RectSection(400,400,30,1.5,420,1.15,.82,(Bar(100,100,20),Bar(105,100,20)))
        with self.assertRaisesRegex(PMMError,'BAR_OVERLAP'):s.validate()
    def test_outside_fails(self):
        s=RectSection(400,400,30,1.5,420,1.15,.82,(Bar(198,100,20),))
        with self.assertRaisesRegex(PMMError,'BAR_OUTSIDE_CONCRETE'):s.validate()
    def test_c30_k1_concrete_area(self):
        s=s400();r=response(s,0,150)
        self.assertGreater(r.concrete_area,0);self.assertLessEqual(r.concrete_area,160000)
    def test_axial_residual(self):
        c,r=solve_c_at_n(s400(),0,500000)
        self.assertLessEqual(abs(r.n-500000),1)
        self.assertGreater(c,0)
    def test_unattainable_axial(self):
        with self.assertRaises(PMMError):solve_c_at_n(s400(),0,10000000)
    def test_pure_axial_is_explicit(self):
        with self.assertRaisesRegex(PMMError,'PURE_AXIAL_USE_SEPARATE_CHECK'):
            ray_intersections(s400(),500000,0,0,24)
    def test_in_plane_equilibrium_symmetry(self):
        r=response(s400(),0,130)
        self.assertAlmostEqual(r.m2,0,delta=1e-6)
        r2=response(s400(),math.pi/2,130)
        self.assertAlmostEqual(r2.m3,0,delta=1e-6)
    def test_all_four_signed_quadrants(self):
        a=[]
        for m2,m3 in ((50e6,50e6),(50e6,-50e6),(-50e6,50e6),(-50e6,-50e6)):
            r=pmm_utilization(s400(),500000,m2,m3,grids=(36,72),rel_tol=.01)
            self.assertTrue(r['converged']);a.append(r['utilization'])
        self.assertLess(max(a)-min(a),.0001)
    def test_demand_scale_metamorphic(self):
        a=pmm_utilization(s400(),500000,20e6,40e6,grids=(36,72),rel_tol=.02)
        b=pmm_utilization(s400(),500000,40e6,80e6,grids=(36,72),rel_tol=.02)
        self.assertAlmostEqual(b['utilization'],2*a['utilization'],delta=.0002)
    def test_angle_convergence_72_144(self):
        p=pmm_utilization(s400(),500000,50e6,50e6,grids=(72,144),rel_tol=.01)
        self.assertLess(p['relative_grid_spread'],.01)

if __name__=='__main__':unittest.main(verbosity=2)
