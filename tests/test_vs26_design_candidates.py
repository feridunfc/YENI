"""Hand sign oracles and independent PMM integration; no self-comparisons."""
from contextlib import closing
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import itertools
import json
import math
import unittest
from unittest.mock import patch

from column_spectral_fixture import SpectralBank
from tbdy_next.column_engine.column_pmm import build_column_cages
from tbdy_next.column_engine.column_prechecks import build_column_prechecks
from tbdy_next.column_engine.demand_types import (CodeDesignDemandCandidate, PhysicalStaticForceState,
    SpectralComponentEnvelope, pmm_arguments, sign_candidates)
from tbdy_next.column_engine.native_archive import BankError, NativeArchive
from tbdy_next.column_engine.section_reference import ReferenceSection, reference_radial_capacity
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.spectral_design import build_design_population
from tbdy_next.column_engine.spectral_pmm import build_spectral_pmm, summarize_group


def population(fixture=None):
    raw = (fixture or SpectralBank()).build()
    bank = recover_column_bank(raw)
    with closing(NativeArchive(raw)) as archive:
        result = build_design_population(bank, archive)
        cages = build_column_cages(bank, result.static_chain,
            build_column_prechecks(bank, result.static_chain), archive)
    return result, cages


def first_eight(result, combination="RS_SUM"):
    return [c for c in result.candidates if c.envelope.combination == combination
        and c.envelope.cut.member_id == "C_SYNTHETIC_1" and c.envelope.cut.object_station_m == 0]


def single_spectrum_fixture(static, spectrum, maximum, minimum):
    """Literal golden targets are supplied independently by each test."""
    f = SpectralBank()
    f.combos = {"ONLY": (0, [(0, "G", 1), (0, "RS", 1)])}
    for member in f.members:
        f.forces[member] = [[member, 0, member+"A", 0, case, step, 0, *values]
            for case, step, values in (("G", "Single Value", static), ("RS", "Max", spectrum),
                ("ONLY", "Max", maximum), ("ONLY", "Min", minimum))]
    return f


class TypedCandidateGoldens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result, cls.cages = population()

    def test_eight_independent_signed_corner_values_and_units(self):
        rows = first_eight(self.result)
        expected = [(99, -49, -79), (99, -49, 59), (99, 66, -79), (99, 66, 59),
                    (76, -49, -79), (76, -49, 59), (76, 66, -79), (76, 66, 59)]
        self.assertEqual([r.values for r in rows], expected)
        self.assertEqual(pmm_arguments(rows[0]), (99000, -49_000_000, -79_000_000))
        self.assertEqual(len({r.candidate_id for r in rows}), 8)
        self.assertEqual(rows[0].sign_id, "P-1_M2-1_M3-1")
        self.assertEqual(rows[4].sign_id, "P+1_M2-1_M3-1")

    def test_single_spectrum_literal_oracle(self):
        f = single_spectrum_fixture([-100, 2, -3, 4, 5, -6], [10, 20, 30, 40, 50, 60],
            [-90, 22, 27, 44, 55, 54], [-110, -18, -33, -36, -45, -66])
        p, _ = population(f)
        self.assertEqual({c.values for c in first_eight(p, "ONLY")},
            set(itertools.product((90, 110), (-45, 55), (-66, 54))))
        self.assertFalse(p.summary["continuous_axial_envelope_complete"])

    def test_existing_static_population_and_three_force_meanings_stay_separate(self):
        p = self.result
        self.assertEqual((len(p.static_states), len(p.envelopes), len(p.candidates)), (8, 16, 128))
        self.assertIs(type(p.static_states[0]), PhysicalStaticForceState)
        self.assertIs(type(p.envelopes[0]), SpectralComponentEnvelope)
        self.assertIs(type(p.candidates[0]), CodeDesignDemandCandidate)
        self.assertEqual([s.state_id for s in p.static_states], [s["state_id"] for s in p.static_chain["candidates"]])
        for invalid in (p.static_states[0], p.envelopes[0], p.candidates[0].as_dict(), None):
            with self.assertRaisesRegex(BankError, "TYPED_CODE"): pmm_arguments(invalid)
        with self.assertRaises(BankError): sign_candidates(p.static_states[0])

    def test_no_fictitious_shear_vector_or_acceptance_from_candidate_type(self):
        c = first_eight(self.result)[0].as_dict()
        self.assertEqual(set(c["forces"]), {"N_kN", "M2_kNm", "M3_kNm"})
        for key in ("physical_concurrency_proven", "second_order_applied", "analysis_generation_qualified", "final_design_eligible"):
            self.assertFalse(c[key])
        self.assertIsNone(c["analysis_generation_id"])
        self.assertEqual(c["normative_qualification"], "NOT_PROVEN")
        self.assertEqual(len(c["native_max_min_row_ids"]), 2)

    def test_immutable_arithmetic_and_station_bindings(self):
        e = self.result.envelopes[0]
        with self.assertRaises(FrozenInstanceError): e.center = (0,)*6
        with self.assertRaisesRegex(BankError, "ARITHMETIC_MISMATCH"): replace(e, center=(0,)*6)
        with self.assertRaisesRegex(BankError, "CONTRIBUTIONS_INVALID"):
            replace(e, cut=replace(e.cut, element_id="OTHER"))
        with self.assertRaisesRegex(BankError, "NATIVE_STEPS_INVALID"):
            replace(e, native_steps=(e.native_steps[0], e.native_steps[0]))

    def test_nonfinite_boolean_and_wrong_sign_policy_are_rejected(self):
        c = self.result.candidates[0]
        for signs in ((True, 1, 1), (0, 1, 1), (-1, 1), [1, 1, 1]):
            with self.assertRaises(BankError): replace(c, signs=signs)
        with self.assertRaises(BankError): replace(c, permutation_policy="PHYSICAL_VECTOR")
        for value in (math.nan, math.inf, -math.inf, True):
            with self.assertRaises(BankError): replace(c.envelope, center=(value, 0, 0, 0, 0, 0))

    def test_captured_negative_coefficients_and_100_30_are_used_once(self):
        f = SpectralBank(); f.combos["RS_SUM"][1][2] = (0, "RS", -1)
        p, _ = population(f)
        self.assertEqual([r.values for r in first_eight(p)], [r.values for r in first_eight(self.result)])
        self.assertEqual(first_eight(p)[0].as_dict()["source_terms"][2]["factor"], -1)
        self.assertEqual(first_eight(p, "CAPTURED_HIGH")[0].values, (116.25, -135.25, -182.5))
        self.assertFalse(p.summary["additional_directional_factor_applied"])
        self.assertFalse(p.summary["spectrum_scale_reapplied"])

    def test_equal_max_min_preserves_all_eight_policy_identities(self):
        f = single_spectrum_fixture([-100, 0, 0, 0, 5, -6], [0]*6,
            [-100, 0, 0, 0, 5, -6], [-100, 0, 0, 0, 5, -6])
        p, _ = population(f); rows = first_eight(p, "ONLY")
        self.assertEqual(len(rows), 8); self.assertEqual(len({r.candidate_id for r in rows}), 8)
        self.assertEqual({r.values for r in rows}, {(100, 5, -6)})

    def test_missing_wrong_station_duplicate_or_mismatch_never_creates_candidate(self):
        for failure in ("missing", "duplicate", "element", "station", "mismatch", "case_definition"):
            with self.subTest(failure=failure):
                f = SpectralBank(); row = f.source_row("RS_SUM", "Min")
                if failure == "missing": f.forces[f.members[0]].remove(row)
                elif failure == "duplicate": f.forces[f.members[0]].append(deepcopy(row))
                elif failure == "element": row[2] = "ANOTHER_ELEMENT"
                elif failure == "station": row[1] = 1e-14
                elif failure == "mismatch": row[11] += .1
                else: f.omitted.add(("LoadCases.GetTypeOAPI_1", "case", "RS"))
                p, _ = population(f)
                self.assertFalse(first_eight(p))
                self.assertFalse(p.summary["construction_complete_for_recorded_scope"])

    def test_missing_global_axis_or_unstable_capture_blocks_design_only(self):
        for failure in ("direction", "capture"):
            f = SpectralBank()
            if failure == "direction": f.omitted.add(("LoadCases.ResponseSpectrum.GetLoads", "case", "RS"))
            else: f.context["identity_unchanged"] = False
            p, _ = population(f)
            self.assertEqual(p.replay["matched_rows"], 32)
            self.assertEqual(len(p.candidates), 0)
            self.assertEqual(p.summary["blocked_pair_count"], 16)

    def test_unsupported_operator_and_nested_route_have_explicit_classification(self):
        f = SpectralBank(); f.combos["NESTED_RS"] = (0, [(1, "RS_SUM", 1)])
        f.combos["SRSS"] = (2, [(0, "RS", 1)])
        p, _ = population(f); routes = {r["combination"]: r for r in p.summary["classifications"]}
        self.assertEqual(routes["SUM"]["classification"], "STATIC_LINEAR_ADD")
        self.assertEqual(routes["ENV"]["classification"], "ENVELOPE")
        for name in ("NESTED_RS", "SRSS"):
            self.assertEqual(routes[name]["sign_construction_scope"], "OUTSIDE_RECIPE")
            self.assertTrue(routes[name]["reason"])


class ConditionalPMMGoldens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.population, cls.cages = population()
        cls.result = build_spectral_pmm(cls.population, cls.cages)

    def test_all_candidate_proposal_identities_survive_numeric_memoization(self):
        r = self.result
        self.assertEqual((len(r.rows), r.summary["expected_assessment_count"]), (384, 384))
        self.assertEqual(len({x.evaluation_id for x in r.rows}), 384)
        self.assertLess(r.summary["unique_numeric_problem_count"], len(r.rows))
        self.assertEqual(r.summary["static_reference_count"], 8)
        self.assertFalse(r.summary["static_population_changed"])
        for row in r.rows:
            evidence = r.evidence_record(row.evidence_id)
            self.assertEqual((evidence["N_N"], evidence["M2_Nmm"], evidence["M3_Nmm"]), pmm_arguments(row.candidate))
            self.assertEqual(evidence["solver_revision"], "VS25_DIRECTION_ROOT")

    def test_independent_integration_verifies_governing_low_N_corner(self):
        # Hand geometry: 800 square, 40 cover + 12 tie + 12 bar radius.
        # Hand demand at ObjSta=3.3: N=350±115, M2=34±575, M3=-40±690.
        coords = [(x,y) for x in (-336,336) for y in (-336,-168,0,168,336)]
        coords += [(x,y) for y in (-336,336) for x in (-168,0,168)]
        section = ReferenceSection(800,800,tuple((x,y,144*math.pi) for x,y in coords), .85*35/1.5,.79,500/1.15)
        oracle = []
        with patch('tbdy_next.column_engine.section_capacity.solver', side_effect=AssertionError('production solver in oracle')):
            for n, m2, m3 in itertools.product((465,235), (-541,609), (-730,650)):
                value = reference_radial_capacity(section, n*1000, m2*1e6, m3*1e6)
                self.assertEqual(value['status'], 'REFERENCE_OBSERVED_STABLE')
                oracle.append((value['utilization'], (n,m2,m3)))
        maximum, forces = max(oracle)
        self.assertEqual(forces, (235,609,-730))
        member = self.result.summary['members'][0]; target = member['governing_resolved']
        self.assertEqual(target['combination'], 'CAPTURED_HIGH')
        self.assertEqual(target['sign_id'], 'P+1_M2+1_M3-1')
        self.assertAlmostEqual(target['conditional_pmm_ratio'], maximum, delta=.002*maximum)
        self.assertEqual(target['station_key']['ObjSta'], 3.3)

    def test_tension_and_compression_outside_limits_are_not_zero_ratios(self):
        f = single_spectrum_fixture([0]*6, [20000,0,0,0,0,0], [20000,0,0,0,0,0], [-20000,0,0,0,0,0])
        p, cages = population(f); r = build_spectral_pmm(p,cages)
        self.assertEqual({v.status for v in r.rows}, {'OUTSIDE_SCENARIO_AXIAL_RANGE'})
        self.assertEqual({v.candidate.values[0] for v in r.rows}, {-20000,20000})
        self.assertTrue(all(v.utilization is None for v in r.rows))
        self.assertTrue(all(not m['numerical_selection_complete'] for m in r.summary['members']))
        self.assertTrue(all(m['first_unresolved_or_axial_outside'] is not None for m in r.summary['members']))

    def test_axial_only_retains_axial_utilization_separate_from_radial_ratio(self):
        f = single_spectrum_fixture([0]*6, [1000,0,0,0,0,0], [1000,0,0,0,0,0], [-1000,0,0,0,0,0])
        p,cages = population(f); r = build_spectral_pmm(p,cages)
        self.assertEqual({v.status for v in r.rows}, {'AXIAL_ONLY_SCENARIO'})
        self.assertTrue(all(v.utilization is None and v.axial_utilization > 0 for v in r.rows))
        self.assertTrue(all(m['engineering_status']=='CONDITIONAL' for m in r.summary['members']))
        json.dumps(r.summary,allow_nan=False)

    def test_unresolved_root_is_retained_and_small_ratio_does_not_hide_it(self):
        with patch('tbdy_next.column_engine.section_capacity.DIRECTION_MAX_ITERATIONS',0):
            r=build_spectral_pmm(self.population,self.cages)
        self.assertIn('NUMERIC_UNRESOLVED',r.summary['status_counts'])
        a=self.result.rows[0]; b=replace(a,status='NUMERIC_UNRESOLVED',utilization=None,reason='GOLDEN_ROOT_FAILURE')
        group=summarize_group([a,b],source_complete=True)
        self.assertIsNotNone(group['maximum_resolved_conditional_ratio'])
        self.assertFalse(group['numerical_selection_complete'])
        self.assertEqual(group['unresolved_or_axial_outside_count'],1)

    def test_corners_cannot_claim_continuous_axial_or_normative_completeness(self):
        # Independent logical counterexample, NOT a constitutive PMM model:
        # C(N)=1+(N-1)^2, M=1. Endpoints N=0,2 give .5, middle N=1 gives 1.
        self.assertGreater(1/(1+(1-1)**2),max(1/(1+(n-1)**2) for n in (0,2)))
        for m in self.result.summary['members']:
            self.assertEqual(m['selection_scope'],'FINITE_GENERATED_CANDIDATES_ONLY')
            self.assertFalse(m['continuous_axial_envelope_complete'])
            self.assertFalse(m['final_design_eligible'])
            self.assertEqual(m['engineering_status'],'CONDITIONAL')

    def test_wrong_cage_source_and_changed_material_rejected_before_solve(self):
        for change in ('source','material'):
            cages=deepcopy(self.cages)
            if change=='source':cages['source_archive_sha256']='0'*64
            else:cages['profiles'][0]['material']['fcd']*=1.1
            with self.assertRaisesRegex(BankError,'CAGE_BINDING'):
                build_spectral_pmm(self.population,cages)

    def test_coherent_leaf_native_center_change_with_retained_ids_is_rejected(self):
        p=deepcopy(self.population); original=p.candidates[0]; e=original.envelope
        def shift(row):return replace(row,values=(row.values[0]+1000,*row.values[1:]))
        changed=replace(e,center=(e.center[0]+1000,*e.center[1:]),
            contributions=(replace(e.contributions[0],row=shift(e.contributions[0].row)),*e.contributions[1:]),
            native_steps=tuple(shift(r) for r in e.native_steps))
        forged=replace(original,envelope=changed)
        self.assertEqual(changed.envelope_id,e.envelope_id)
        self.assertEqual(changed.contributions[0].row.source_row_id,e.contributions[0].row.source_row_id)
        self.assertNotEqual(forged.candidate_id,original.candidate_id)
        self.assertEqual(forged.values[0],original.values[0]-1000)
        altered=replace(p,candidates=(forged,*p.candidates[1:]))
        with patch('tbdy_next.column_engine.spectral_pmm.solver',side_effect=AssertionError('must reject before solve')):
            with self.assertRaisesRegex(BankError,'CANDIDATE_BINDING'):build_spectral_pmm(altered,self.cages)

    def test_stale_summary_hash_cannot_promote_incomplete_population(self):
        f=SpectralBank();f.forces[f.members[0]].remove(f.source_row('RS_SUM','Min'))
        p,cages=population(f)
        self.assertEqual((p.summary['candidate_count'],p.summary['expected_candidate_count']),(120,128))
        self.assertFalse(p.summary['construction_complete_for_recorded_scope'])
        p.summary['construction_complete_for_recorded_scope']=True
        with patch('tbdy_next.column_engine.spectral_pmm.solver',side_effect=AssertionError('must reject before solve')):
            with self.assertRaisesRegex(BankError,'POPULATION_CONTENT'):build_spectral_pmm(p,cages)


if __name__ == '__main__': unittest.main()
