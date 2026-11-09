from copy import deepcopy
import math
import unittest
from tbdy_next.column_engine.joint_moment_signs import moment_sign_mapping
from tbdy_next.column_engine.native_archive import BankError
from tbdy_next.column_engine.scwb_kernel import JointCase,MemberMomentCapacity,compute_scwb_joint_result

X_BEAM=[[1,0,0],[0,0,1],[0,-1,0]]
Y_BEAM=[[0,1,0],[0,0,1],[1,0,0]]
COLUMN=[[0,0,1],[1,0,0],[0,1,0]]


class JointSignOracles(unittest.TestCase):
    def test_member_on_joint_restoring_direction_uses_opposite_ends(self):
        for direction,axes in (('X',X_BEAM),('Y',Y_BEAM)):
            for sign in (-1,1):
                i=moment_sign_mapping(axes,'I',direction,sign,'M3')
                j=moment_sign_mapping(axes,'J',direction,sign,'M3')
                self.assertEqual((i['local_internal_moment_sign'],j['local_internal_moment_sign']),(sign,-sign))
                self.assertEqual(i['member_on_joint_unit_moment_global'],j['member_on_joint_unit_moment_global'])
                self.assertFalse(i['physical_joint_moment_transfer_proven'])

    def test_m2_has_opposite_stress_moment_factor_from_m3(self):
        x=moment_sign_mapping(COLUMN,'I','X',1,'M3')
        y=moment_sign_mapping(COLUMN,'I','Y',1,'M2')
        self.assertEqual((x['csi_stress_moment_factor'],y['csi_stress_moment_factor']),(1,-1))
        self.assertEqual((x['local_internal_moment_sign'],y['local_internal_moment_sign']),(-1,-1))
        self.assertEqual(x['member_on_joint_unit_moment_global'],[0,-1,0])
        self.assertEqual(y['member_on_joint_unit_moment_global'],[1,0,0])

    def test_asymmetric_two_beam_oracle_catches_wrong_positive_sum(self):
        capacities={'left':{1:120,-1:200},'right':{1:150,-1:100}}
        for sign,expected,ratio in ((1,350,6/7),(-1,220,15/11)):
            ctx=JointCase('RUN-TEST','archive','J','X',sign,'STATIC','C24/B20_N0')
            values=[MemberMomentCapacity(ctx,n,end,'COLUMN',m,'source-'+n) for n,end,m in (('below','J',170),('above','I',190))]
            for name,end in (('left','J'),('right','I')):
                mapping=moment_sign_mapping(X_BEAM,end,'X',sign,'M3')
                values.append(MemberMomentCapacity(ctx,name,end,'BEAM',capacities[name][mapping['local_internal_moment_sign']],'source-'+name))
            result=compute_scwb_joint_result(ctx,[('below','J'),('above','I')],[('left','J'),('right','I')],values)
            self.assertEqual(result['sum_mrb_reference_knm'],expected)
            self.assertAlmostEqual(result['normalized_reference_ratio'],ratio)
            self.assertEqual(result['reference_satisfied'],sign==-1)

    def test_native_ij_reversal_preserves_physical_capacity_branch(self):
        reverse=[[-v for v in X_BEAM[0]],X_BEAM[1],[-v for v in X_BEAM[2]]]
        for sign in (-1,1):
            a=moment_sign_mapping(X_BEAM,'I','X',sign,'M3')
            b=moment_sign_mapping(reverse,'J','X',sign,'M3')
            self.assertEqual(a['local_internal_moment_sign'],b['local_internal_moment_sign'])
            self.assertEqual(a['member_on_joint_unit_moment_global'],b['member_on_joint_unit_moment_global'])

    def test_global_quarter_turn_preserves_local_branch_and_capacity(self):
        for end in ('I','J'):
            for sign in (-1,1):
                a=moment_sign_mapping(X_BEAM,end,'X',sign,'M3');b=moment_sign_mapping(Y_BEAM,end,'Y',sign,'M3')
                self.assertEqual(a['local_internal_moment_sign'],b['local_internal_moment_sign'])
                v=a['member_on_joint_unit_moment_global']
                self.assertEqual(b['member_on_joint_unit_moment_global'],[-v[1],v[0],v[2]])

    def test_unknown_nonorthogonal_left_handed_and_nonfinite_axes_rejected(self):
        angle=math.pi/4;c,s=math.cos(angle),math.sin(angle)
        bad=[[[c,s,0],[0,0,1],[s,-c,0]],[[1,0,0],[0,0,1],[0,1,0]],
            [[2,0,0],[0,0,1],[0,-1,0]],[[float('nan'),0,0],[0,0,1],[0,-1,0]],[[1,0,0]]]
        for axes in bad:
            with self.subTest(axes=axes),self.assertRaises(BankError):moment_sign_mapping(axes,'I','X',1,'M3')
        for end,direction,sign,axis in (('K','X',1,'M3'),('I','Z',1,'M3'),('I','X',True,'M3'),('I','X',1,'T')):
            with self.assertRaises(BankError):moment_sign_mapping(X_BEAM,end,direction,sign,axis)
