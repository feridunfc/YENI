"""R08 engine-level regressions: exact source seals, typed roles and fail-closed.

No Windows/COM and no parallel exploratory calculation implementation.
"""
from __future__ import annotations
import copy
import unittest

from tbdy_next.story_second_order import bind_story_second_order, CAPTURE_SCHEMA
from tools.etabs_source_gateway_windows import seal

MODEL = r"C:\tmp\kompakt_b.EDB"
CONFIG = dict(live_model_basename="kompakt_b.EDB", x_case="RSX", y_case="RSY",
              weight_combo="WGHT", R="7", D="2.5", Ch="0.5")


def table(name, fields, rows, units=None):
    return {
        "table_key": name, "status": "CAPTURED", "fields": fields,
        "rows": rows, "row_count": len(rows),
        "field_metadata": {"status": "OK", "field_keys": fields,
                           "units_by_field": units or {}},
    }


def sealed(reads, model=MODEL):
    return seal({
        "schema": "tbdy.next.etabs.generic-source-capture.v1",
        "action": "capture", "status": "CAPTURED",
        "model": model, "model_locked": True, "model_units_code": 6,
        "model_units_unchanged": True, "selection_restored": True,
        "analysis_generation_proven": False, "table_reads": reads,
    })


def fixture():
    defs = table("Story Definitions", ["Story", "Tower", "Height"], [
        {"Story": "+9.00", "Tower": "T1", "Height": "4.5"},
        {"Story": "+4.50", "Tower": "T1", "Height": "4.5"},
    ], {"Height": "m"})
    base_level = table("Tower and Base Story Definitions",
        ["Tower", "BSName", "BSElev"], [
            {"Tower": "T1", "BSName": "Base", "BSElev": "0"}
        ], {"BSElev": "m"})
    rs_base = table("Base Reactions",
        ["OutputCase", "CaseType", "StepType"], [
            {"OutputCase": case, "CaseType": "LinRespSpec", "StepType": "Max"}
            for case in ("RSX", "RSY")
        ])
    forces = table("Story Forces",
        ["Story", "OutputCase", "CaseType", "Location", "VX", "VY"], [
            {"Story": story, "OutputCase": case, "CaseType": "LinRespSpec",
             "Location": "Bottom", "VX": vx, "VY": vy}
            for story, vx, vy in (("+4.50", "100", "105"), ("+9.00", "60", "63"))
            for case in ("RSX", "RSY")
        ], {"VX": "kN", "VY": "kN"})
    drifts = table("Story Max Over Avg Drifts",
        ["Story", "OutputCase", "CaseType", "Direction", "Avg Drift"], [
            {"Story": story, "OutputCase": case, "CaseType": "LinRespSpec",
             "Direction": axis, "Avg Drift": d}
            for story, d in (("+4.50", "0.001"), ("+9.00", "0.002"))
            for case, axis in (("RSX", "X"), ("RSY", "Y"))
        ], {"Avg Drift": "m"})
    combo = table("Load Combination Definitions",
        ["Name", "LoadName", "SF", "Type"], [
            {"Name": "WGHT", "LoadName": name, "SF": factor,
             "Type": "Linear Add" if idx == 0 else "None"}
            for idx, (name, factor) in enumerate((
                ("LC_DL", "1"), ("LC_SDL", "1"), ("LC_WDL", "1"),
                ("LC_LL", "0.3"), ("LC_DDL", "1")
            ))
        ])
    weight_forces = table("Story Forces",
        ["Story", "OutputCase", "CaseType", "Location", "P"], [
            {"Story": "+4.50", "OutputCase": "WGHT", "CaseType": "Combination",
             "Location": "Bottom", "P": "2000"},
            {"Story": "+9.00", "OutputCase": "WGHT", "CaseType": "Combination",
             "Location": "Bottom", "P": "1000"},
        ], {"P": "kN"})
    base = table("Base Reactions", ["OutputCase", "CaseType", "FZ"], [
        {"OutputCase": "WGHT", "CaseType": "Combination", "FZ": "2000"}
    ], {"FZ": "kN"})
    return {
        "schema": CAPTURE_SCHEMA, "status": "CAPTURED",
        "same_sapmodel_session": True, "combination_selection_restored": True,
        "analysis_generation_proven": False, "configuration_approved": False,
        "configuration": dict(CONFIG), "model": MODEL,
        "spectrum_source": sealed({
            "Story Definitions": defs,
            "Tower and Base Story Definitions": base_level,
            "Base Reactions": rs_base, "Story Forces": forces,
            "Story Max Over Avg Drifts": drifts,
            "Load Combination Definitions": combo
        }), "weight_source": sealed({
            "Story Forces": weight_forces, "Base Reactions": base
        })
    }


class StorySecondOrderEngineTests(unittest.TestCase):
    def test_all_stories_calculated_without_regulatory_approval(self):
        result = bind_story_second_order(fixture())
        self.assertEqual(result["status"], "NUMERIC_PRECHECK_UNAPPROVED")
        self.assertEqual(result["expected_story_direction_count"], 4)
        self.assertEqual(result["evaluated_story_direction_count"], 4)
        self.assertAlmostEqual(float(result["direction_results"]["X"]["beta_ii_candidate"]), 1.0)
        self.assertAlmostEqual(float(result["direction_results"]["Y"]["beta_ii_candidate"]), 1.0)
        self.assertAlmostEqual(float(result["direction_results"]["X"]["theta_limit_reference"]),
                               .12 * 2.5 / (.5 * 7))
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertIs(result["global_p_delta_design_applied"], False)

    def test_changed_wght_factor_rejected(self):
        data = fixture()
        t = data["spectrum_source"]["table_reads"]["Load Combination Definitions"]
        t["rows"][3]["SF"] = "1"
        data["spectrum_source"] = sealed(data["spectrum_source"]["table_reads"])
        result = bind_story_second_order(data)
        self.assertEqual(result["status"], "BLOCKED_SOURCE_INVALID")
        self.assertIn("R08_WGHT_G_PLUS_NQ_COMPONENTS_NOT_AS_DECLARED", result["reason_codes"][0])

    def test_sha_tamper_rejected(self):
        data = fixture()
        data["weight_source"]["table_reads"]["Base Reactions"]["rows"][0]["FZ"] = "4000"
        result = bind_story_second_order(data)
        self.assertEqual(result["status"], "BLOCKED_SOURCE_INVALID")
        self.assertIn("GENERIC_SOURCE_SEAL_MISMATCH", result["reason_codes"][0])

    def test_missing_story_direction_preserved(self):
        data = fixture()
        table_obj = data["spectrum_source"]["table_reads"]["Story Max Over Avg Drifts"]
        table_obj["rows"] = [r for r in table_obj["rows"]
                            if not (r["Story"] == "+9.00" and r["Direction"] == "Y")]
        table_obj["row_count"] = len(table_obj["rows"])
        data["spectrum_source"] = sealed(data["spectrum_source"]["table_reads"])
        result = bind_story_second_order(data)
        self.assertEqual(result["status"], "BLOCKED_SOURCE_INVALID")
        self.assertIn("R08_SPECTRAL_STORY_MISSING_NO_INFERRED_ZERO",
                      result["reason_codes"][0])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")

    def test_wrong_model_rejected(self):
        data = fixture()
        data["weight_source"] = sealed(data["weight_source"]["table_reads"],
                                       model="C:\\tmp\\another.EDB")
        result = bind_story_second_order(data)
        self.assertEqual(result["status"], "BLOCKED_SOURCE_INVALID")

    def test_weight_base_balance_rejected(self):
        data = fixture()
        data["weight_source"]["table_reads"]["Base Reactions"]["rows"][0]["FZ"] = "2100"
        data["weight_source"] = sealed(data["weight_source"]["table_reads"])
        result = bind_story_second_order(data)
        self.assertEqual(result["status"], "BLOCKED_SOURCE_INVALID")
        self.assertIn("R08_WGHT_BASE_STORY_BALANCE_MISMATCH", result["reason_codes"][0])


if __name__ == "__main__":
    unittest.main()
