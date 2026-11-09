from dataclasses import replace
import math
import unittest

from tbdy_next.column_engine.scwb_kernel import JointCase,MemberMomentCapacity,compute_scwb_joint_result,column_axis_capacity
from tbdy_next.column_engine.section_capacity import Section,Bar,Material
from tbdy_next.column_engine.native_archive import BankError


class SCWBAggregationOracles(unittest.TestCase):
    def setUp(self):
        self.context=JointCase('RUN-TEST','archive-sha','J1','X',1,'STATIC','16Φ24')
        self.columns=[('C1','J'),('C2','I')];self.beams=[('B1','J'),('B2','I')]
    def cap(self,name,end,role,value,context=None,tol=0):
        return MemberMomentCapacity(context or self.context,name,end,role,value,'SOURCE-'+name if value is not None else None,
            tol,'MISSING_END_REBAR' if value is None else None)
    def inputs(self,columns=(180,180),beams=(200,200)):
        return [self.cap(n,e,'COLUMN',v) for (n,e),v in zip(self.columns,columns)]+[self.cap(n,e,'BEAM',v) for (n,e),v in zip(self.beams,beams)]
    def result(self,caps):return compute_scwb_joint_result(self.context,self.columns,self.beams,caps)

    def test_missing_beam_cannot_recreate_legacy_false_ok(self):
        r=self.result(self.inputs(beams=(200,None)))
        self.assertEqual(r['sum_mrc_reference_knm'],360)
        for k in ('sum_mrb_reference_knm','required_mrc_reference_knm','raw_capacity_ratio','normalized_reference_ratio','reference_satisfied','scwb_ratio'):
            self.assertIsNone(r[k])
        self.assertEqual(r['status'],'CAPACITY_INPUTS_INCOMPLETE')
        self.assertEqual(r['missing_capacities'],[{'role':'BEAM','member_id':'B2','end':'I','reason':'MISSING_END_REBAR'}])

    def test_fully_missing_entry_remains_in_expected_population(self):
        r=self.result(self.inputs()[:-1]);self.assertEqual(r['expected_beam_count'],2)
        self.assertIsNone(r['normalized_reference_ratio'])
        self.assertEqual(r['missing_capacities'][0]['reason'],'CAPACITY_NOT_SUPPLIED')

    def test_independent_raw_and_normalized_ratio_oracles(self):
        r=self.result(self.inputs())
        self.assertEqual((r['sum_mrc_reference_knm'],r['sum_mrb_reference_knm'],r['required_mrc_reference_knm']),(360,400,480))
        self.assertEqual((r['raw_capacity_ratio'],r['normalized_reference_ratio']),(.9,.75))
        self.assertFalse(r['reference_satisfied']);self.assertEqual(r['status'],'CONDITIONAL_REFERENCE_NOT_SATISFIED')
        self.assertIsNone(r['scwb_ratio']);self.assertEqual(r['formal_compliance'],'NOT_PROVEN')

    def test_exact_equality_and_nonzero_numerical_boundary_are_distinct(self):
        r=self.result(self.inputs(columns=(240,240)));self.assertTrue(r['reference_satisfied']);self.assertEqual(r['normalized_reference_ratio'],1)
        caps=self.inputs(columns=(240,240));caps[0]=replace(caps[0],tolerance_knm=.01)
        r=self.result(caps);self.assertIsNone(r['reference_satisfied']);self.assertEqual(r['status'],'NUMERIC_BOUNDARY_UNRESOLVED')

    def test_missing_column_nulls_complete_column_sum(self):
        r=self.result(self.inputs(columns=(180,None)))
        self.assertIsNone(r['sum_mrc_reference_knm']);self.assertIsNone(r['normalized_reference_ratio'])

    def test_run_archive_joint_case_direction_sign_scenario_and_step_cannot_mix(self):
        changes=[{'source_run_id':'OTHER'},{'source_archive_sha256':'other'},{'joint_id':'J2'},
            {'output_case':'OTHER'},{'direction':'Y'},{'rotation_sign':-1},{'scenario':'16Φ28'}]
        for values in changes:
            with self.subTest(values=values),self.assertRaises(BankError):
                caps=self.inputs();caps[0]=replace(caps[0],context=replace(self.context,**values));self.result(caps)
        for values in ({'step_type':'Max'},{'step_number':1},{'rotation_sign':True}):
            with self.assertRaises(BankError):replace(self.context,**values)

    def test_duplicate_unexpected_and_wrong_end_participants_rejected(self):
        for kind in ('duplicate','foreign','end','role'):
            with self.subTest(kind=kind),self.assertRaises(BankError):
                caps=self.inputs()
                if kind=='duplicate':caps.append(caps[0])
                elif kind=='foreign':caps[0]=replace(caps[0],member_id='C99')
                elif kind=='end':caps[0]=replace(caps[0],end='I')
                else:caps[0]=replace(caps[0],role='BEAM')
                self.result(caps)

    def test_zero_nonfinite_and_source_label_only_are_not_capacities(self):
        for value in (0,-1,float('nan'),float('inf'),True):
            with self.subTest(value=value),self.assertRaises(BankError):self.cap('B1','J','BEAM',value)
        with self.assertRaises(BankError):MemberMomentCapacity(self.context,'B1','J','BEAM',200,None)
        with self.assertRaises(BankError):compute_scwb_joint_result(self.context,[('C1','J'),('C1','J')],self.beams,[])

    def test_empty_beam_roster_is_not_an_exception_or_satisfied_ratio(self):
        r=compute_scwb_joint_result(self.context,self.columns,[],self.inputs()[:2])
        self.assertEqual(r['status'],'NO_COLUMN_OR_BEAM_IN_DIRECTION');self.assertIsNone(r['reference_satisfied'])


class ColumnAxisCapacityOracles(unittest.TestCase):
    def setUp(self):
        self.section=Section(400,400,tuple(Bar(x,y,1000) for x in (-150,150) for y in (-150,150)),Material(30,20,400))

    def test_known_half_block_returns_329_2_knm_at_source_n(self):
        for axis in ('M2','M3'):
            r=column_axis_capacity(self.section,1604000,axis)
            self.assertEqual(r['status'],'COLUMN_CAPACITY_REFERENCE')
            self.assertAlmostEqual(r['capacity_knm'],329.2,delta=.001)
            self.assertLessEqual(r['axial_residual_n'],1)
            self.assertFalse(r['source_n_is_design_nd']);self.assertFalse(r['capacity_at_source_demand_ray_used'])

    def test_unequal_section_principal_planes_have_separate_hand_oracles(self):
        sec=Section(400,600,tuple(Bar(x,y,1000) for x in (-150,150) for y in (-250,250)),Material(30,20,400))
        # Concrete half-block + net displaced concrete + centroid steel strains.
        a=column_axis_capacity(sec,2284000,'M3');b=column_axis_capacity(sec,2202000,'M2')
        self.assertAlmostEqual(a['capacity_knm'],397.2,delta=.001)
        self.assertAlmostEqual(b['capacity_knm'],648.5,delta=.001)

    def test_axial_out_of_range_and_asymmetric_cage_fail_closed(self):
        r=column_axis_capacity(self.section,1e9,'M2');self.assertIsNone(r['capacity_knm'])
        with self.assertRaises(BankError):column_axis_capacity(replace(self.section,bars=(Bar(50,0,1000),)),1e6,'M2')

    def test_n_affects_capacity_and_results_do_not_mutate_cache(self):
        a=column_axis_capacity(self.section,0,'M2');b=column_axis_capacity(self.section,1e6,'M2')
        self.assertNotEqual(a['capacity_knm'],b['capacity_knm'])
        expected=b['capacity_knm'];b['capacity_knm']=0;b['point']['m2_nmm']=0
        fresh=column_axis_capacity(self.section,1e6,'M2');self.assertEqual(fresh['capacity_knm'],expected);self.assertGreater(fresh['point']['m2_nmm'],0)
