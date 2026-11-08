"""Twelve source-published ETABS RSX/RSY drift table rows from compact_b.

This intentionally uses a reduced, manually extracted source projection, NOT
an invented full 2.18 MB ETABS capture and NOT a regulatory golden oracle.
"""
from __future__ import annotations
import unittest
from test_vs05_story_delta import fixture
from tbdy_next.story_delta import calculate

REAL_ROWS = [
    ("+9.00", "RSX", "X", "0.000776", "0.003492"),
    ("+9.00", "RSX", "Y", "0.000255", "0.001148"),
    ("+9.00", "RSY", "X", "0.000376", "0.001691"),
    ("+9.00", "RSY", "Y", "0.001196", "0.005380"),
    ("+4.50", "RSX", "X", "0.000797", "0.003586"),
    ("+4.50", "RSX", "Y", "0.000305", "0.001370"),
    ("+4.50", "RSY", "X", "0.000283", "0.001273"),
    ("+4.50", "RSY", "Y", "0.001180", "0.005309"),
    ("+0.00", "RSX", "X", "0.000509", "0.002624"),
    ("+0.00", "RSX", "Y", "0.000176", "0.000905"),
    ("+0.00", "RSY", "X", "0.000137", "0.000706"),
    ("+0.00", "RSY", "Y", "0.000387", "0.001991"),
]


class RealSnapshotTest(unittest.TestCase):
    def test_real_etabs_twelve_row_drift_tables_agree_with_5_micron_resolution(self):
        data = fixture()
        defs = data["table_reads"]["Story Definitions"]
        defs["rows"] += [
            {"Story":"+0.00","Tower":"T1","Height":"5.15"},
            {"Story":"+14.5","Tower":"T1","Height":"5.5"},
        ]
        defs["row_count"] = len(defs["rows"])
        drifts = data["table_reads"]["Story Drifts"]
        maxes = data["table_reads"]["Story Max Over Avg Drifts"]
        drifts["rows"] = [
            {"Story":s,"OutputCase":c,"CaseType":"LinRespSpec","StepType":"Max",
             "Direction":axis,"Drift":ratio,"Label":"real-capture-governing-label-not-copied"}
            for s,c,axis,ratio,maxm in REAL_ROWS
        ]
        maxes["rows"] = [
            {"Story":s,"OutputCase":c,"CaseType":"LinRespSpec","StepType":"Max",
             "Direction":axis,"Max Drift":maxm,"Avg Drift":maxm,"Ratio":"1"}
            for s,c,axis,ratio,maxm in REAL_ROWS
        ]
        drifts["row_count"] = maxes["row_count"] = len(REAL_ROWS)
        result = calculate(data)
        self.assertEqual(len(result["story_deltas"]), 12)
        self.assertEqual(result["story_delta_coverage"]["uncovered_stories"],["+14.5"])
        err = max(abs(float(row["etabs_reconciliation_residual_mm"])) for row in result["story_deltas"])
        self.assertAlmostEqual(err,0.00265, places=9)

    def test_candidate_is_not_tbd_y_pass(self):
        data=fixture()
        result=calculate(data)
        self.assertEqual(result["engineering_release"],"NOT_READY")
        self.assertFalse(result["design_spectrum_scaling_qualified"])

if __name__ == "__main__": unittest.main()
