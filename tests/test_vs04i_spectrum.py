"""VS04-I: independent TSC 2018 spectrum reconstruction unit/negative tests.

All numerical fixtures are synthetic. Real ETABS replay remains a distinct
Windows acceptance gate; no test asserts code compliance or release.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from tbdy_next.spectrum_reconstruction import (
    PI, _spectrum, _interpolate, review_spectrum_reconstruction,
    SOURCE_ONLY,
)
from tbdy_next.quick_checks import check_registry
from tools.review_vs04i_spectrum import replay


def table(name, rows, units=None):
    fields = list(rows[0])
    return {
        "table_key": name, "status": "CAPTURED",
        "fields": fields, "rows": rows, "row_count": len(rows),
        "field_metadata": {
            "status": "OK", "field_keys": fields, "field_count": len(fields),
            "units_by_field": {k: (units or {}).get(k, "") for k in fields}
        },
    }


def fixture():
    params = {"SDS": Decimal("0.52578"), "SD1": Decimal("0.263958"),
              "R": Decimal("7"), "D": Decimal("2.5"),
              "I": Decimal("1.5"), "TL": Decimal("6")}
    with localcontext() as c:
        c.prec = 45
        ta = Decimal(".2") * params["SD1"] / params["SDS"]
        tb = params["SD1"] / params["SDS"]
        sample_periods = [Decimal(x) for x in
                          ("0", "0.8", "1", "1.2", "1.4", "1.6", "1.8",
                           "2", "2.5", "3", "3.5", "4", "4.5", "5",
                           "5.5", "6", "6.5", "7", "7.5", "8", "8.5",
                           "9", "9.5", "10")]
        sample_periods = sample_periods[:1] + [ta, tb] + sample_periods[1:]
        frows = []
        ordered_knots = []
        for idx, T in enumerate(sample_periods):
            displayed_T = ("0.1" if idx == 1 else
                           "0.502" if idx == 2 else str(T))
            analytic = _spectrum(T, sds=params["SDS"], sd1=params["SD1"],
                                 R=params["R"], D=params["D"],
                                 I=params["I"], TL=params["TL"])
            shown = str(analytic.quantize(Decimal(".000001")))
            frows.append({
                "Name": "RESP_YATAY", "Period": displayed_T, "Value": shown,
                **{k: str(v) if idx == 0 else "None" for k,v in params.items()},
            })
            ordered_knots.append((T, Decimal(shown), Decimal(".0000005")))
        case_rows = [
            {"Name": case, "LoadName": axis, "Function": "RESP_YATAY",
             "TransAccSF": "10", "ModalCase": "Modal"}
            for case,axis in (("RSX","U1"),("RSY","U2"))
        ]
        modal_rows = []
        prior_items = []
        for mode in range(1,101):
            T = Decimal(".47")/(Decimal(1)+Decimal(".05")*(mode-1))
            omega = 2*PI/T
            # Independent printed modal precision; no hidden data.
            wshown = str(omega.quantize(Decimal(".000000001")))
            modal_T = str(T.quantize(Decimal(".001")))
            p = _interpolate(ordered_knots, T)[0] * Decimal("10")
            acceleration = str(p.quantize(Decimal(".0001")))
            prior_items.append({
                "mode":str(mode),"period_sec":modal_T,
                "circular_frequency_rad_sec":wshown,
            })
            for case in ("RSX","RSY"):
                modal_rows.append({
                    "SpecCase":case, "ModalCase":"Modal", "Mode":str(mode),
                    "Period":modal_T, "DampRatio":"0.05",
                    "U1Acc":acceleration if case=="RSX" else "0",
                    "U2Acc":acceleration if case=="RSY" else "0",
                    "U3Acc":"0", "U1Amp":"0.0007" if case=="RSX" else "0",
                    "U2Amp":"-0.0008" if case=="RSY" else "0",
                    "U3Amp":"0",
                })
        E = {"schema":"tbdy.next.vs04e.basis-probe-receipt.v1",
             "source":{"schema":"tbdy.next.vs04e.basis-source-probe.v1",
                       "units_before":6, "units_after":6,
                       "analysis_generation_proven":False,
                       "read_only_invariant_proven":True,
                       "table_reads":{
                          "Functions - Response Spectrum - TSC-2018":
                              table("Functions - Response Spectrum - TSC-2018",
                                    frows, {"Period":"sec","Value":""}),
                          "Load Case Definitions - Response Spectrum":
                              table("Load Case Definitions - Response Spectrum",
                                    case_rows, {"TransAccSF":"m/sec2"}),
                       }}}
        G = {"schema":"tbdy.next.vs04g.diaphragm-source-receipt.v1",
             "source":{"schema":"tbdy.next.vs04g.diaphragm-modal-probe.v1",
                       "units_before":6,"units_after":6,
                       "display_selection_restored":True,
                       "temporary_display_cases":["RSX","RSY"],
                       "analysis_generation_proven":False,
                       "spectrum_modal_selected_cases":
                           table("Response Spectrum Modal Info", modal_rows,
                                 {"Period":"sec",
                                  "U1Acc":"m/sec2","U2Acc":"m/sec2",
                                  "U3Acc":"m/sec2"})}}
        M = {"schema":"tbdy.next.vs04.offline-source-replay.v1",
             "numeric_source_review":{"results":[{
                 "component":"MODAL_PERIOD_FREQUENCY_IDENTITY",
                 "status":"SOURCE_ARITHMETIC_OBSERVED",
                 "items":prior_items}]}}
    return E,G,M


class Vs04ISpectrumTest(unittest.TestCase):
    def setUp(self):
        self.e,self.g,self.m=fixture()

    def test_26_analytic_knots_and_200_modal_values_are_bounded(self):
        out=review_spectrum_reconstruction(self.e,self.g,self.m)
        self.assertEqual(out["status"],SOURCE_ONLY)
        self.assertEqual(out["source_knot_count"],26)
        self.assertEqual(out["analytical_knot_consistency_count"],26)
        self.assertEqual(out["reconstructed_modal_rows"],200)
        self.assertEqual(out["unexplained_modal_rows"],0)
        self.assertEqual(out["regulatory_checks_executed"],0)
        self.assertFalse(out["accidental_eccentricity_applied_proven"])
        self.assertEqual(out["engineering_release"],"NOT_READY")
        self.assertEqual(len(check_registry()),14)

    def test_known_tbd_y_2018_values_are_algebraically_reproduced(self):
        sds=Decimal("0.52578")
        sd1=Decimal("0.263958")
        args=dict(sds=sds,sd1=sd1,R=Decimal(7),
                  D=Decimal("2.5"),I=Decimal("1.5"),TL=Decimal(6))
        ta=Decimal(".2")*sd1/sds
        tb=sd1/sds
        self.assertLess(abs(_spectrum(Decimal(0),**args)-Decimal(".0841248")),
                        Decimal("0.000000000001"))
        self.assertLess(abs(_spectrum(ta,**args)-Decimal(".1792431818181818")),
                        Decimal("0.000000000001"))
        self.assertLess(abs(_spectrum(tb,**args)-Decimal(".1126671428571429")),
                        Decimal("0.000000000001"))

    def test_period_precision_and_corner_period_correction_materially_matter(self):
        out=review_spectrum_reconstruction(self.e,self.g,self.m)
        corners=out["derived_corner_periods_s"]
        self.assertGreater(Decimal(corners["T_A"]),Decimal(".1004"))
        self.assertGreater(Decimal(corners["T_B"]),Decimal(".5020"))
        # Positive result must never depend on an unbounded 1% tolerance.
        self.assertEqual(out["comparison_basis"],
                         "DISPLAY_DECIMAL_PRECISION_BOUNDS_NO_FIXED_PERCENT_TOLERANCE")

    def test_tampered_mode_acceleration_is_detected_without_global_tolerance(self):
        self.g["source"]["spectrum_modal_selected_cases"]["rows"][0]["U1Acc"]="2.7777"
        result=review_spectrum_reconstruction(self.e,self.g,self.m)
        self.assertEqual(result["status"],"SOURCE_RECONSTRUCTION_PARTIAL")
        self.assertEqual(result["unexplained_modal_rows"],1)
        self.assertEqual(result["reconstructed_modal_rows"],199)

    def test_missing_or_ambiguous_source_is_not_proven(self):
        out=review_spectrum_reconstruction(self.e,None,self.m)
        self.assertEqual(out["status"],"NOT_PROVEN")
        self.assertEqual(out["regulatory_checks_executed"],0)

    def test_bad_corner_ordinate_blocks_analytic_knot_audit(self):
        key="Functions - Response Spectrum - TSC-2018"
        self.e["source"]["table_reads"][key]["rows"][1]["Value"]="0.198321"
        result=review_spectrum_reconstruction(self.e,self.g,self.m)
        self.assertIn("TSC2018_ANALYTIC_KNOT_VALUES_INCONSISTENT",
                      result["reason_codes"])
        self.assertEqual(result["status"],"NOT_PROVEN")

    def test_spectrum_case_scale_mismatch_blocks(self):
        key="Load Case Definitions - Response Spectrum"
        self.e["source"]["table_reads"][key]["rows"][1]["TransAccSF"]="9"
        result=review_spectrum_reconstruction(self.e,self.g,self.m)
        self.assertIn("FUNCTION_CASE_SCALE_OR_POINT_POPULATION_NOT_EXACT",
                      result["reason_codes"])

    def test_one_modal_period_cannot_be_falsified(self):
        self.m["numeric_source_review"]["results"][0]["items"][0]["circular_frequency_rad_sec"]="400"
        result=review_spectrum_reconstruction(self.e,self.g,self.m)
        self.assertEqual(result["status"],"SOURCE_RECONSTRUCTION_PARTIAL")

    def test_case_and_mode_identity_fail_closed(self):
        self.g["source"]["spectrum_modal_selected_cases"]["rows"][0]["Mode"]="2"
        out=review_spectrum_reconstruction(self.e,self.g,self.m)
        self.assertEqual(out["status"],"NOT_PROVEN")
        self.assertIn(out["reason_codes"][0], (
            "DUPLICATE_OR_INVALID_RS_MODAL_KEY",
            "DIFFERENT_VS04D_VS04G_MODAL_DISPLAY_PERIOD",
        ))

    def test_nonfinite_modal_acceleration_rejected(self):
        self.g["source"]["spectrum_modal_selected_cases"]["rows"][0]["U1Acc"]="NaN"
        self.assertEqual(review_spectrum_reconstruction(
            self.e,self.g,self.m)["status"],"NOT_PROVEN")

    def test_missing_units_fail_closed(self):
        key="Response Spectrum Modal Info"
        self.g["source"]["spectrum_modal_selected_cases"]["field_metadata"]["units_by_field"]["U1Acc"]=""
        self.assertEqual(review_spectrum_reconstruction(
            self.e,self.g,self.m)["status"],"NOT_PROVEN")

    def test_report_is_offline_and_immutable(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            args=(self.e,self.g,self.m)
            paths=[]
            for idx,obj in enumerate(args):
                path=root/("source"+str(idx)+".json")
                path.write_text(json.dumps(obj,sort_keys=True),encoding="utf-8")
                paths.append(path)
            originals=[p.read_bytes() for p in paths]
            out=root/"source-only-review.json"
            result=replay(*paths,out)
            self.assertEqual(result["spectrum_reconstruction"]["reconstructed_modal_rows"],200)
            self.assertFalse(result["source_raw_included"])
            self.assertTrue(all(p.read_bytes()==v for p,v in zip(paths,originals)))
            with self.assertRaises(ValueError):
                replay(*paths,out)


if __name__ == "__main__":
    unittest.main()
