"""B7: independent oracle and explicit numeric-budget regression set.

These tests check numerical implementation within a declared model. They
are not independent certification of TS500 model assumptions.
"""
from dataclasses import replace
from math import pi
import json
import unittest
from unittest.mock import patch

from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.quantities import Force,Moment
from tbdy_column_core.domain.section_requests import (
    EnvelopeAtAxialForce,RadialCapacityAtAxialForce,SectionStatus)
from tbdy_column_core.engineering.triple_convergence import (
    assess_three_level_radial_refinement,TripleRefinementStatus)
from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter
from tbdy_column_core.reporting.section_report import section_report_json
from tests.independent.oracle import (
    OracleBar,OracleMaterial,solve_fixed_p_state,audit_fixed_p_roots,
    radial_capacity_dense_convex)


def oracle_input(problem):
    section=problem.section
    bars=tuple(OracleBar(i,b.x2.as_mm,b.x3.as_mm,
        b.diameter.as_mm,pi*b.diameter.as_mm**2/4)
        for i,b in enumerate(section.longitudinal.bars))
    return bars,OracleMaterial(35.,35./1.5,420./1.15,.79)


class B7IndependentAcceptanceEvidence(unittest.TestCase):
    def test_public_two_actual_cages_three_fixed_n_oracle_angles(self):
        for layout in ("A","B"):
            p=fixture_problem(layout=layout,angle_count=8,
                request=EnvelopeAtAxialForce(Force.kn(500)))
            result=calculate_section(p)
            self.assertEqual(result.status,SectionStatus.COMPLETE_ENVELOPE,
                             result.issues[:5])
            bars,mat=oracle_input(p)
            for i in (0,1,2):
                state=result.states[i]
                theta=i*45.
                independent=solve_fixed_p_state(
                    width_mm=400.,depth_mm=600.,bars=bars,material=mat,
                    theta_deg=theta,target_n=500000.,
                    axial_tolerance_n=1.,scan_count=700)
                self.assertIsNotNone(independent)
                self.assertLessEqual(abs(state.n.as_n-500000.),1.)
                self.assertAlmostEqual(state.m2.as_nmm,independent.m2_nmm,
                                       delta=15000.)
                self.assertAlmostEqual(state.m3.as_nmm,independent.m3_nmm,
                                       delta=15000.)
                self.assertAlmostEqual(state.c.as_mm,independent.c_mm,delta=.1)
            self.assertEqual(len(result.angular_coverage.resolved_indices),8)

    def test_three_level_72_144_288_measured_not_certified(self):
        p=fixture_problem(layout="B",angle_count=72,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        numeric=assess_three_level_radial_refinement(p)
        self.assertEqual(numeric.counts,(72,144,288))
        # The discontinuous point-bar replacement convention is now
        # checked explicitly. This fixed fixture has four axial jump
        # crossings at 288 sample angles; never relabel partial as full.
        self.assertEqual(numeric.statuses,(
            SectionStatus.COMPLETE_RADIAL,
            SectionStatus.COMPLETE_RADIAL,
            SectionStatus.PARTIAL_ENVELOPE))
        self.assertEqual(numeric.verdict,TripleRefinementStatus.NUMERIC_UNRESOLVED)
        self.assertTrue(any("AXIAL_JUMP_CROSSES_TARGET" in x
                            for x in numeric.issues))
        self.assertIsNotNone(numeric.differences_nmm[0])
        self.assertIsNone(numeric.differences_nmm[1])
        self.assertEqual(numeric.moment_budgets_nmm,(1000.,None))
        self.assertGreater(numeric.differences_nmm[0],1000.)
        self.assertIn("not a rigorous bound",numeric.interpretation)
        bars,mat=oracle_input(p)
        oracle=radial_capacity_dense_convex(
            width_mm=400.,depth_mm=600.,bars=bars,material=mat,
            target_n=500000.,demand_m2_nmm=40000000.,
            demand_m3_nmm=20000000.,angle_count=144,
            root_scan_count=160,axial_tolerance_n=1.)
        self.assertEqual(oracle.status,"PROVEN")
        # 3% is independently established baseline similarity for this
        # numeric model, NOT the stricter 1000 Nmm convergence budget.
        # 144-angle sampled value is still present. The 288-angle
        # value is intentionally withheld due to root ambiguity.
        self.assertIsNone(numeric.capacity_nmm[-1])
        self.assertAlmostEqual(numeric.capacity_nmm[1],oracle.capacity_nmm,
                               delta=.03*oracle.capacity_nmm)

    def test_failure_at_one_angle_keeps_other_angles_and_report_truth(self):
        p=fixture_problem(layout="B",angle_count=8,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        prior=SectionKernelAdapter.sample_axial_brackets
        def fail_angle(adapter,angle,target,material,bars,*,force_atol_n):
            if angle.as_deg==90.:
                raise ArithmeticError("simulated angle failure")
            return prior(adapter,angle,target,material,bars,
                         force_atol_n=force_atol_n)
        with patch.object(SectionKernelAdapter,"sample_axial_brackets",fail_angle):
            out=calculate_section(p)
        self.assertEqual(out.status,SectionStatus.PARTIAL_ENVELOPE)
        self.assertEqual(out.angular_coverage.missing_indices,(2,))
        self.assertEqual(len(out.states),7)
        self.assertIsNone(out.radial_capacity)
        doc=json.loads(section_report_json(out))
        self.assertEqual(doc["angular_coverage"]["missing_indices"],[2])
        self.assertIsNone(doc["radial_capacity_nmm"])
        self.assertFalse(doc["full_column_design_pass"])

    def test_extreme_force_is_unknown_not_physical_outside_or_false_fail(self):
        p=fixture_problem(layout="B",angle_count=8,
            request=EnvelopeAtAxialForce(Force.kn(10000)))
        out=calculate_section(p)
        self.assertEqual(out.status,SectionStatus.NUMERIC_UNRESOLVED)
        self.assertTrue(out.issues)
        self.assertEqual(out.angular_coverage.resolved_indices,())
        self.assertIsNone(out.radial_capacity)
        self.assertNotIn("OUTSIDE_AXIAL_CAPACITY",out.status.value)
