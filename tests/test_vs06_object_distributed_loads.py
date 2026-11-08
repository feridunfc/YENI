"""VS06-C2: read-only distributed load fallback when ETABS DB display ret=1.

Mocks actual source patterns and methods; no live ETABS, COM or writable API.
"""
from __future__ import annotations

from decimal import Decimal
import unittest

from tools.etabs_source_gateway_windows import (
    capture, capture_distributed_frame_loads_by_object, verify,
)
from test_etabs_source_gateway import FakeDb, FakeSap
from test_vs06_c2_drift_scenario import scenario_report
from tbdy_next.vs06_drift_scenario import evaluate_drift_scenario
from tools.review_vs06_wall_capture import review_capture


class DistributedDb(FakeDb):
    def __init__(self):
        super().__init__()
        self.keys += (
            "Beam Object Connectivity", "Frame Loads Assignments - Distributed",
        )
        self.fake_rows["Beam Object Connectivity"] = (
            ("UniqueName", "Story", "Length"),
            [("B1", "+9.00", "5"), ("B2", "+9.00", "4")],
            {"Length": "m"},
        )
        self.fake_rows["Frame Loads Assignments - Distributed"] = (
            ("UniqueName", "LoadPattern", "LoadType",
             "RelDistA", "RelDistB"),
            [], {},
        )
        self.corrupt_return = "Frame Loads Assignments - Distributed"


def frame_return(name, pattern, *, intervals=None):
    intervals = intervals or []
    count = len(intervals)
    return (
        count, [name] * count, [pattern] * count, [1] * count,
        ["Global"] * count, [10] * count,
        [a for a, b in intervals], [b for a, b in intervals],
        [a * 5 for a, b in intervals], [b * 5 for a, b in intervals],
        [5] * count, [5] * count, 0,
    )


class FakeFrameLoads:
    def __init__(self, *, partial=False):
        self.partial = partial
        self.calls = []
    def GetLoadDistributed(self, name):
        self.calls.append(name)
        if name == "B1":
            return frame_return(name, "LC_WDL", intervals=[(0, .7), (.3, 1)])
        if self.partial:
            raise RuntimeError("CSI OAPI unavailable on B2")
        return frame_return(name, "LC_WDL")


class DistributedProbeTests(unittest.TestCase):
    def sap(self, *, partial=False):
        sap = FakeSap(DistributedDb())
        sap.FrameObj = FakeFrameLoads(partial=partial)
        return sap

    def test_ret1_db_does_not_hide_successful_frame_getloads(self):
        sap = self.sap()
        src = capture(sap, action="capture", exact=(
            "Beam Object Connectivity", "Frame Loads Assignments - Distributed"),
            frame_load_probe=True)
        verify(src)
        self.assertEqual(src["status"], "SOURCE_PARTIAL")
        self.assertEqual(src["table_reads"]["Frame Loads Assignments - Distributed"]["status"], "CAPTURE_ERROR")
        probe = src["frame_load_object_probe"]
        self.assertEqual(probe["status"], "CAPTURED")
        self.assertEqual(probe["beam_count"], 2)
        self.assertEqual(probe["load_row_count"], 2)
        self.assertEqual(probe["unresolved_beam_count"], 0)
        self.assertEqual(sap.FrameObj.calls, ["B1", "B2"])
        self.assertEqual(sap.DatabaseTables.selected, ())
        self.assertEqual(sap.units, 6)

        report = scenario_report()
        report["source_snapshot"]["vs06_wall_load_source"] = src
        row = evaluate_drift_scenario(report)["wall_candidate_inventory"]
        self.assertEqual(row["load_pattern"], "LC_WDL")
        self.assertEqual(row["candidate_beams"], ["B1"])
        self.assertEqual(Decimal(row["candidate_total_length_m"]), Decimal("5"))
        self.assertEqual(Decimal(row["assumed_net_face_area_m2"]), Decimal("14"))
        self.assertTrue(row["source_census_complete"])
        self.assertEqual(row["original_distributed_table_status"], "CAPTURE_ERROR")
        offline = review_capture(src)
        self.assertEqual(offline["load_pattern"], "LC_WDL")
        self.assertEqual(Decimal(offline["candidate_total_loaded_length_m"]), Decimal("5"))
        self.assertEqual(len(offline["per_story"]), 1)
        self.assertEqual(offline["per_story"][0]["story"], "+9.00")
        self.assertEqual(Decimal(offline["per_story"][0]["assumed_net_face_area_m2"]), Decimal("14"))

    def test_partial_object_error_is_not_called_empty_load(self):
        sap = self.sap(partial=True)
        src = capture(sap, action="capture", exact=(
            "Frame Loads Assignments - Distributed", "Beam Object Connectivity"),
            frame_load_probe=True)
        probe = src["frame_load_object_probe"]
        self.assertEqual(probe["status"], "SOURCE_PARTIAL")
        self.assertEqual(probe["unresolved_beam_count"], 1)
        self.assertEqual(probe["successful_beam_count"], 1)
        self.assertEqual(len(probe["rows"]), 2)
        report = scenario_report()
        report["source_snapshot"]["vs06_wall_load_source"] = src
        wall = evaluate_drift_scenario(report)["wall_candidate_inventory"]
        self.assertEqual(wall["candidate_beam_count"], 1)
        self.assertEqual(wall["source_status"], "LOAD_PATTERN_OBSERVED_PARTIAL_OBJECT_PROBE")
        self.assertFalse(wall["source_census_complete"])
        self.assertEqual(wall["unresolved_beam_count"], 1)

    def test_wrong_units_rejected_before_com(self):
        sap = self.sap()
        sap.units = 8
        beam = capture(self.sap(), action="capture",
                       exact=("Beam Object Connectivity",))["table_reads"]["Beam Object Connectivity"]
        with self.assertRaisesRegex(ValueError, "LOCKED_KN_M_C"):
            capture_distributed_frame_loads_by_object(sap, beam)
        self.assertEqual(sap.FrameObj.calls, [])

    def test_zero_beam_load_response_not_fabricated(self):
        sap = self.sap()
        src = capture(sap, action="capture", exact=("Beam Object Connectivity",
                    "Frame Loads Assignments - Distributed"), frame_load_probe=True)
        self.assertEqual(src["frame_load_object_probe"]["successful_beam_count"], 2)
        self.assertEqual(src["frame_load_object_probe"]["rows"][0]["LoadPattern"], "LC_WDL")


if __name__ == "__main__":
    unittest.main()
