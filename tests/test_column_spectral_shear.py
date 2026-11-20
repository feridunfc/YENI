"""Assigned spectral capacity shear, interval direction, model controls and conditional closure."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from test_mixed_design_demands import table
from test_scwb_axial_interval import independent_moment, section
from tbdy_next.column_engine.scwb_kernel import column_axis_interval_bound
from tbdy_next.engineering.column_spectral_shear import _axis_case, _case_cuts, _model_controls, complete_spectral_shear
from tbdy_next.engineering.design_scenario import _digest


def fixture(center=8., radius=12., nd=(500., 1000.)):
    native, cuts = {}, {}
    for sta in (0., 2., 4.):
        key = ("C", sta, "C", sta)
        primitive = {"status":"NUMERICAL_MATCH", "center_native":{"V2":center, "P":-sum(nd)/2},
                     "radius_native":{"V2":radius, "P":(nd[1]-nd[0])/2},
                     "nd_bounds_kn":list(nd)}
        cuts[key] = {"native_cut":list(key), "configured_required_cut":True, "nd_bounds_kn":list(nd),
                     "primitive_replay":primitive}
        native["E",key] = {step:(*key,"E",step,0.,-n,shear,0.,0.,0.,0.) for step,n,shear in
                           (("Min",nd[1],center-radius),("Max",nd[0],center+radius))}
    return cuts,native


def evaluate(center=8., radius=12., nd=(500.,1000.), control=True):
    cuts,native = fixture(center,radius,nd)
    sec = section()
    def resistance(axis,n,v):
        return {"branches":{"ts500":{"vr_kn":1600.}, "zero_concrete":{"vr_kn":1200.}},
                "tbdy_brittle_reference_kn":2800., "ts500_web_reference_kn":2500.}
    return _axis_case("E","V2","M3",cuts,native,{"I":min(cuts),"J":max(cuts)},sec,4.,
                      {"combination":"K","d_factor":2.5} if control else None,resistance)


class SpectralCapacityShearTests(TestCase):
    def test_control_requires_matching_gravity_case_function_and_unique_scaled_definition(self):
        defs="Load Case Definitions - Response Spectrum"
        curves="Functions - Response Spectrum - TSC-2018"
        tables={defs:table(defs,[{"Name":"R","Function":"F","LoadName":"U1"}]),
                curves:table(curves,[{"Name":"F","D":"2.5","Direction":"Horizontal"}])}
        def group(g,r):
            return {"operator_etabs":"Linear Add","rows":[{"ref":"G","ref_type":"CASE","factor":g},
                                                         {"ref":"R","ref_type":"CASE","factor":r}]}
        graph={"assigned":group("1","1"),"different-gravity":group("2","2.5"),"control":group("1","2.5")}
        cases={"G":{"type":"Linear Static"},"R":{"type":"Response Spectrum"}}
        with patch("tbdy_next.engineering.column_spectral_shear.native_graph",return_value=(tables,cases,graph)):
            self.assertEqual(_model_controls({},["assigned"])["assigned"]["combination"],"control")
            graph["ambiguous"]=group("1","2.5")
            self.assertEqual(_model_controls({},["assigned"]),{})
            del graph["ambiguous"]
            tables[defs]["rows"][0]["LoadName"]="U3"
            self.assertEqual(_model_controls({},["assigned"]),{})

    def test_upper_encloses_independent_section_through_interior_peak(self):
        sec = section()
        for axis in ("M2","M3"):
            bounds = column_axis_interval_bound(sec,axis,0.,8500.,include_upper=True)
            for nd in range(0,8501,250):
                mr = independent_moment(sec,axis,nd)
                self.assertLessEqual(mr,bounds["mr_upper_bound_knm"])
                self.assertGreaterEqual(mr,bounds["mr_lower_bound_knm"])

    def test_d_scales_only_radius_and_does_not_reduce_assigned_check(self):
        case=evaluate(center=-8.)
        self.assertEqual(case["vd_floor_kn"],20.)
        self.assertEqual(case["cap_control"]["abs_max_kn"],38.)
        self.assertEqual(case["cap_control"]["governing"]["step"],"Min")
        self.assertEqual(case["cap_control"]["bounded_ve_kn"],38.)
        self.assertEqual(case["cap_control"]["minimum_nd_kn"],125.)
        self.assertEqual(case["cap_control"]["zero_concrete_utilization"],38./1200.)
        self.assertGreater(case["ve_upper_kn"],38.)
        self.assertFalse(case["cap_control"]["applied_to_assigned_demand"])

    def test_ordinary_floor_can_govern_both_scenarios(self):
        case=evaluate(center=3000.)
        self.assertEqual(case["ve_upper_kn"],3012.)
        self.assertEqual(case["cap_control"]["bounded_ve_kn"],3012.)
        self.assertEqual(case["vd_governing"]["signed_kn"],3012.)

    def test_zero_concrete_at_inclusive_nd_threshold_and_separate_brittle_check(self):
        limit=.05*600*800*35/1000
        self.assertEqual(evaluate(nd=(limit,1000.))["vr_used_kn"],1200.)
        high=evaluate(nd=(limit+.01,1000.),control=False)
        self.assertEqual(high["vr_used_kn"],1600.)
        self.assertEqual(high["cap_control"]["status"],"MODEL_D_COMBINATION_UNRESOLVED")
        self.assertFalse(high["earthquake_share_and_confinement_required_proven"])
        self.assertEqual(high["brittle_utilization"],high["ve_upper_kn"]/2800.)

    def test_missing_extremum_cut_duplicate_or_reversed_axial_interval_blocks(self):
        for defect in ("step","missing","duplicate","reversed"):
            with self.subTest(defect=defect):
                obs,native=fixture()
                cuts=list(obs.values())
                if defect=="step":native["E",min(obs)].pop("Min")
                elif defect=="missing":cuts.pop()
                elif defect=="duplicate":cuts.append(cuts[0])
                else:cuts[0]["nd_bounds_kn"].reverse()
                with self.assertRaises(ValueError):
                    _case_cuts("C","E",{"cuts":cuts,"status":"SAME_SOURCE_COMPONENT_REPLAY_MATCH",
                        "expected_cut_count":3},native,set(obs))

    def test_r14_requires_both_axes_same_candidate_evidence_and_complete_cases(self):
        row=evaluate()
        res={"member_id":"C","input_sha256":"input","status":"CONSERVATIVE_SPECTRAL_SHEAR_WITHIN_LIMITS",
             "d_reduction_applied":False,"assigned_combinations":["E"],"calculated_axis_case_count":2,
             "axes":{a:{"cases":[dict(row,axis=a)]} for a in ("V2","V3")}}
        def ok(r,revision): return complete_spectral_shear(r,{"E"},"C","input",revision)
        self.assertTrue(ok(res,_digest(res)))
        damaged=deepcopy(res)
        damaged["axes"]["V3"]["cases"].clear()
        self.assertFalse(ok(damaged,_digest(res)))
        self.assertFalse(ok(damaged,_digest(damaged)))
        self.assertFalse(complete_spectral_shear(res,{"E","E2"},"C","input",_digest(res)))
