"""Candidate display must retain missing members and distinguish source templates."""
from copy import deepcopy
import unittest

from tbdy_next.reporting import _column_candidate_schedule, _column_candidate_schedule_html


def recorded_results():
    members = [{"member_id": uid, "story": "+0.00", "section": "C80",
                "section_evidence": {"reinforcement_role": "ETABS_DESIGN_TEMPLATE", "bar_count": 12,
                                     "t2_mm": 800.0, "t3_mm": 800.0, "cover_to_tie_mm": 40.0}}
               for uid in ("210", "211")]
    selection = {"member_id": "210", "status": "ENGINEER_COLUMN_SELECTED_NOT_PROVEN",
                 "tbdy_minimum_longitudinal_area_mm2": 6400.0,
                 "selected": {"label": "32Φ16", "bar_count": 32, "diameter_mm": 16,
                              "area_mm2": 6433.98175455, "rho_percent": 1.005309649,
                              "pmm_max_utilization": .1, "pmm_satisfied": True,
                              "selected_transverse": {"tie_diameter_mm": 8, "confinement_spacing_mm": 90,
                                  "midspan_spacing_mm": 90, "legs_v2": 5, "legs_v3": 5,
                                  "crossties_parallel_v2": 3, "crossties_parallel_v3": 3,
                                  "all_tbdy_checks_met": True, "alerts": []}}}
    stages = {"column_pmm": {"members": members, "expected_column_count": 2},
              "r10_live": {"per_member": {"210": {"engineer_column_selection": selection},
                                         "211": {"status": "BLOCKED"}}},
              "r08_local_slenderness": {"per_member": {"210": {
                  "magnified_selected_pmm": {"status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN",
                      "max_utilization": .42, "resolved_row_count": 3, "expected_row_count": 3}}}}}
    evidence = {"design_dependencies": {"selected_candidates": {
        "expected_column_count": 2, "selection_role": "ALGORITHM_SELECTED_CANDIDATE",
        "rows": [{"member_id": "210", "status": "SAME_RUN_CANDIDATE_BOUND", "candidate_sha256": "a" * 64},
                 {"member_id": "211", "status": "CANDIDATE_BLOCKED"}]}}}
    return stages, evidence


class ColumnCandidateScheduleTests(unittest.TestCase):
    def test_candidates_never_replace_or_mutate_recorded_template_results(self):
        stages, evidence = recorded_results()
        before = deepcopy((stages, evidence))
        result = _column_candidate_schedule(stages, evidence)
        self.assertEqual((stages, evidence), before)
        row = result["rows"][0]
        self.assertEqual(row["bar_count"], 32)
        self.assertEqual(row["recorded_reinforcement_role"], "ETABS_DESIGN_TEMPLATE")
        self.assertEqual(row["magnified_pmm_utilization"], .42)
        self.assertEqual(result["selection_role"], "ALGORITHM_SELECTED_CANDIDATE")
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_expected_blocked_members_remain_in_schedule_and_denominator(self):
        stages, evidence = recorded_results()
        stages["column_pmm"]["members"].pop()
        stages["r10_live"]["per_member"].pop("211")
        result = _column_candidate_schedule(stages, evidence)
        self.assertEqual(result["expected_column_count"], 2)
        self.assertEqual(result["bound_column_count"], 1)
        self.assertEqual([r["member_id"] for r in result["rows"]], ["210", "211"])
        self.assertIsNone(result["rows"][1]["bar_count"])
        self.assertEqual(result["rows"][1]["binding_status"], "CANDIDATE_BLOCKED")

    def test_wrong_unique_id_cannot_display_another_members_cage(self):
        stages, evidence = recorded_results()
        stages["r10_live"]["per_member"]["210"]["engineer_column_selection"]["member_id"] = "WRONG"
        result = _column_candidate_schedule(stages, evidence)
        self.assertEqual(result["bound_column_count"], 0)
        row = result["rows"][0]
        self.assertEqual(row["binding_status"], "CANDIDATE_IDENTITY_MISMATCH")
        for key in ("label", "bar_count", "minimum_area_mm2", "tie_diameter_mm"):
            self.assertIsNone(row[key])

    def test_stale_bound_ledger_cannot_hide_a_missing_selected_record(self):
        stages, evidence = recorded_results()
        stages["r10_live"]["per_member"]["210"]["engineer_column_selection"].pop("selected")
        result = _column_candidate_schedule(stages, evidence)
        self.assertEqual(result["bound_column_count"], 0)
        self.assertEqual(result["rows"][0]["binding_status"], "RECORDED_CANDIDATE_UNAVAILABLE")

    def test_plain_capture_does_not_invent_a_selection_or_binding(self):
        stages, _ = recorded_results()
        stages["r10_live"] = {}
        self.assertIsNone(_column_candidate_schedule(stages, {}))
        stages, _ = recorded_results()
        result = _column_candidate_schedule(stages, {})
        self.assertEqual(result["bound_column_count"], 0)
        self.assertEqual(result["rows"][0]["binding_status"], "SAME_RUN_BINDING_UNAVAILABLE")

    def test_html_preserves_failed_and_missing_transverse_results(self):
        stages, evidence = recorded_results()
        tie = stages["r10_live"]["per_member"]["210"]["engineer_column_selection"]["selected"]["selected_transverse"]
        tie["all_tbdy_checks_met"] = False
        tie["alerts"] = ["SPACING_UNRESOLVED"]
        result = _column_candidate_schedule(stages, evidence)
        self.assertFalse(result["rows"][0]["all_tbdy_checks_met"])
        self.assertIsNone(result["rows"][1]["all_tbdy_checks_met"])
        html = _column_candidate_schedule_html(result)
        self.assertIn("approval pending", html)
        self.assertIn("not simultaneous force vectors", html)
        self.assertIn("CANDIDATE_BLOCKED", html)
        self.assertIn("<td>210</td>", html)
        self.assertIn("<td>211</td>", html)


if __name__ == "__main__":
    unittest.main()
