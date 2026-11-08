"""Independent B2 arithmetic oracle and hostile/partial source boundaries.

All fixtures in this file are SYNTHETIC. The historical 12-row VS05 projection
substituted Avg=Max and MUST NOT be reused as actual B2 average evidence.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal as D
import unittest

from tbdy_next.soft_story_b2 import (
    AVERAGES, BASE, DRIFTS, STORIES, MeanDrift, StoryLevel,
    bind_soft_story_b2, compare_adjacent,
)
from test_vs05_story_delta import table
from test_vs05_story_drift_binding import seal


def reseal(source):
    source = deepcopy(source)
    source.pop("payload_sha256", None)
    return seal(source)


def b2_source(*, numeric_names=False):
    names = ["+0.00", "+3.00", "+8.00"] if numeric_names else ["Lower", "Middle", "Roof"]
    heights = ["4", "3", "5"]
    elevations = ["0", "3", "8"]
    avg_x = ["0.012", "0.003", "0.010"]
    avg_y = ["0.004", "0.003", "0.005"]
    definitions = table(STORIES, ["Tower", "Story", "Height"], [
        {"Tower": "T1", "Story": s, "Height": h}
        for s, h in reversed(list(zip(names, heights)))], {"Height": "m"})
    base = table(BASE, ["Tower", "BSName", "BSElev"], [
        {"Tower": "T1", "BSName": "Base", "BSElev": "-4"}], {"BSElev": "m"})
    averages, drifts = [], []
    for story, height, ax, ay in zip(names, heights, avg_x, avg_y):
        for case, direction, average in (("RSX", "X", ax), ("RSY", "Y", ay)):
            maximum = D(average) * D("1.2")
            identity = {"Story": story, "OutputCase": case, "CaseType": "LinRespSpec",
                        "StepType": "Max", "Direction": direction}
            averages.append({**identity, "Max Drift": str(maximum),
                             "Avg Drift": average, "Ratio": "1.2"})
            drifts.append({**identity, "Drift": str(maximum / D(height)), "Label": "P"})
    avg_table = table(AVERAGES, list(averages[0]), averages,
                      {"Max Drift": "m", "Avg Drift": "m", "Ratio": ""})
    drift_table = table(DRIFTS, list(drifts[0]), drifts, {"Drift": ""})
    points = [{"UniqueName": "0", "Story": "Base", "X": "0", "Y": "0", "Z": "-4"}]
    points += [{"UniqueName": str(i), "Story": s, "X": "0", "Y": "0", "Z": z}
               for i, (s, z) in enumerate(zip(names, elevations), 1)]
    point_table = table("Point Object Connectivity", list(points[0]), points,
                        {"X": "m", "Y": "m", "Z": "m"})
    columns = [{"UniqueName": "C" + str(i), "Story": s,
                "UniquePtI": str(i - 1), "UniquePtJ": str(i), "Length": h}
               for i, (s, h) in enumerate(zip(names, heights), 1)]
    column_table = table("Column Object Connectivity", list(columns[0]), columns, {"Length": "m"})
    joints = [{"UniqueName": p["UniqueName"], "Story": p["Story"],
               "OutputCase": "Modal", "CaseType": "LinModRitz", "StepType": "Mode",
               "StepNumber": "1", "Ux": str(D(p["UniqueName"]) / 1000), "Uy": "0"}
              for p in points]
    joint_table = table("Joint Displacements", list(joints[0]), joints, {"Ux": "m", "Uy": "m"})
    return seal({
        "schema": "tbdy.next.etabs.generic-source-capture.v1",
        "status": "CAPTURED", "model": "SYNTHETIC_B2_ORACLE_ONLY.EDB",
        "model_locked": True, "model_units_code": 6,
        "model_units_unchanged": True, "selection_restored": True,
        "table_reads": {t["table_key"]: t for t in
                        (definitions, base, avg_table, drift_table, point_table, column_table, joint_table)},
    })


def oracle_means(top="0.010"):
    levels = [StoryLevel("S1", D("0"), D("4")),
              StoryLevel("S2", D("3"), D("3")),
              StoryLevel("S3", D("8"), D("5"))]
    means = [MeanDrift(story, direction, case, D(value))
             for story, x, y in (("S1", "0.012", "0.004"),
                                ("S2", "0.003", "0.003"), ("S3", top, "0.005"))
             for direction, case, value in (("X", "RSX", x), ("Y", "RSY", y))]
    return levels, means


class B2IndependentArithmeticTests(unittest.TestCase):
    def test_independent_hand_oracle_both_neighbours_and_height_normalization(self):
        r = compare_adjacent(*oracle_means())
        pairs = {(x["story"], x["adjacent_story"], x["direction"]): x for x in r["items"]}
        self.assertEqual(D(pairs["S1", "S2", "X"]["eta_ki_candidate"]), D("3"))
        self.assertEqual(D(pairs["S2", "S3", "X"]["eta_ki_candidate"]), D("0.5"))
        self.assertAlmostEqual(float(pairs["S2", "S1", "X"]["eta_ki_candidate"]), 1 / 3)
        # Raw displacement 10/3 would wrongly trigger. Normalized ratio is 2.
        self.assertEqual(D(pairs["S3", "S2", "X"]["eta_ki_candidate"]), D("2"))
        self.assertEqual(pairs["S3", "S2", "X"]["status"], "THRESHOLD_NOT_EXCEEDED")
        self.assertEqual(r["comparison_coverage"], {
            "expected": 8, "resolved": 8, "unresolved": 0, "complete": True})
        self.assertEqual((r["expected_count"], r["evaluated_count"]), (6, 6))
        self.assertEqual(r["threshold_exceeded_comparisons"], 1)

    def test_exact_strict_boundary_and_two_sides(self):
        for displacement, expected, status in (
            ("0.010", "2", "THRESHOLD_NOT_EXCEEDED"),
            ("0.010000005", "2.000001", "THRESHOLD_EXCEEDED"),
            ("0.009999995", "1.999999", "THRESHOLD_NOT_EXCEEDED"),
        ):
            with self.subTest(displacement=displacement):
                result = compare_adjacent(*oracle_means(displacement))
                item = next(x for x in result["items"] if x["story"] == "S3" and x["direction"] == "X")
                self.assertEqual(D(item["eta_ki_candidate"]), D(expected))
                self.assertEqual(item["status"], status)

    def test_missing_middle_keeps_all_expected_comparisons_no_new_adjacency(self):
        levels, means = oracle_means()
        means = [MeanDrift(m.story, m.direction, m.case, None, "SOURCE_MISSING", "MISSING")
                 if m.story == "S2" else m for m in means]
        result = compare_adjacent(levels, means)
        self.assertEqual(result["comparison_coverage"]["expected"], 8)
        self.assertEqual(result["comparison_coverage"]["resolved"], 0)
        self.assertEqual(result["evaluated_count"], 0)
        self.assertFalse(any({r["story"], r["adjacent_story"]} == {"S1", "S3"} for r in result["items"]))

    def test_zero_reference_stays_undefined_and_zero_numerator_is_zero(self):
        levels, means = oracle_means()
        means = [MeanDrift(m.story, m.direction, m.case, D(0))
                 if m.story == "S2" else m for m in means]
        result = compare_adjacent(levels, means)
        denominators = [r for r in result["items"] if r["adjacent_story"] == "S2"]
        self.assertTrue(all(r["status"] == "UNDEFINED_ZERO_REFERENCE_DRIFT" for r in denominators))
        numerators = [r for r in result["items"] if r["story"] == "S2"]
        self.assertTrue(all(D(r["eta_ki_candidate"]) == 0 for r in numerators))
        self.assertFalse(result["comparison_coverage"]["complete"])

    def test_rejects_duplicate_levels_nonfinite_nonpositive_and_mixed_cases(self):
        levels, means = oracle_means()
        candidates = [
            (levels + [levels[0]], means),
            ([StoryLevel("S1", D("NaN"), D("4")), *levels[1:]], means),
            ([StoryLevel("S1", D("0"), D("0")), *levels[1:]], means),
            (levels, [MeanDrift("S1", "X", "OTHER", D(".012")), *means[1:]]),
            (levels, [MeanDrift("S1", "X", "RSX", D("Infinity")), *means[1:]]),
            (levels, means + [means[0]]),
            (levels, means[:-1]),
        ]
        for pair in candidates:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                compare_adjacent(*pair)

    def test_single_story_does_not_invent_a_neighbour_or_code_pass(self):
        levels, means = oracle_means()
        result = compare_adjacent(levels[:1], means[:2])
        self.assertFalse(result["comparison_coverage"]["complete"])
        self.assertEqual(result["evaluated_count"], 0)
        self.assertTrue(all(x["reason"] == "NO_ADJACENT_DEFINED_STORY" for x in result["story_results"]))


class B2SourceBoundaryTests(unittest.TestCase):
    def test_existing_observed_schemas_bind_nonnumeric_story_names_without_COM(self):
        source = b2_source()
        before = deepcopy(source)
        result = bind_soft_story_b2(source)
        self.assertEqual(result["status"], "SOURCE_NUMERICAL")
        self.assertEqual(result["source_coverage"], {"expected": 6, "resolved": 6, "missing": 0, "invalid": 0})
        self.assertEqual(result["threshold_exceeded_comparisons"], 1)
        self.assertEqual(result["stories"][0]["story"], "Lower")
        self.assertEqual(result["stories"][-1]["elevation_m"], "8")
        self.assertEqual(result["source_payload_sha256"], source["payload_sha256"])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["normative_b2_classification"], "NOT_PROVEN")
        self.assertFalse(result["numerical_pass_issued"])
        self.assertEqual(bind_soft_story_b2(source), result)
        self.assertEqual(source, before)

    def test_missing_top_is_preserved_without_affecting_known_lower_pair(self):
        source = b2_source()
        for name in (AVERAGES, DRIFTS):
            raw = source["table_reads"][name]
            raw["rows"] = [r for r in raw["rows"] if r["Story"] != "Roof"]
            raw["row_count"] = len(raw["rows"])
        result = bind_soft_story_b2(reseal(source))
        self.assertEqual(len(result["stories"]), 3)
        self.assertEqual(result["source_coverage"]["missing"], 2)
        self.assertEqual(result["comparison_coverage"], {
            "expected": 8, "resolved": 4, "unresolved": 4, "complete": False})
        self.assertEqual(result["status"], "PARTIAL_SOURCE_NUMERICAL")

    def test_one_duplicate_or_eccentricity_envelope_is_never_collapsed_to_max(self):
        source = b2_source()
        raw = source["table_reads"][AVERAGES]
        duplicate = deepcopy(raw["rows"][0])
        duplicate.update({"Avg Drift": "9", "Max Drift": "10.8"})
        raw["rows"].append(duplicate)
        raw["row_count"] += 1
        result = bind_soft_story_b2(reseal(source))
        self.assertEqual(result["source_coverage"]["invalid"], 1)
        self.assertIn("B2_DUPLICATE_SOURCE_GRAIN", result["reason_codes"])
        self.assertFalse(any(r["average_drift_m"] == "9" for r in result["source_rows"]))

    def test_invalid_units_and_missing_table_keep_denominator(self):
        for action in ("units", "missing"):
            source = b2_source()
            if action == "units":
                source["table_reads"][AVERAGES]["field_metadata"]["units_by_field"]["Avg Drift"] = "mm"
            else:
                del source["table_reads"][AVERAGES]
            result = bind_soft_story_b2(reseal(source))
            self.assertTrue(result["coverage_known"])
            self.assertEqual(result["source_coverage"]["expected"], 6)
            self.assertEqual(result["comparison_coverage"]["expected"], 8)
            self.assertEqual(result["comparison_coverage"]["resolved"], 0)
            self.assertEqual(result["status"], "BLOCKED_SOURCE")

    def test_nonfinite_average_wrong_projection_and_maximum_conflict_block_only_slot(self):
        for field, value in (("Avg Drift", "NaN"), ("StepType", "Min"),
                             ("Max Drift", "999"), ("Ratio", "9")):
            source = b2_source()
            source["table_reads"][AVERAGES]["rows"][0][field] = value
            result = bind_soft_story_b2(reseal(source))
            self.assertEqual(result["source_coverage"]["invalid"], 1, (field, result))
            self.assertGreater(result["comparison_coverage"]["resolved"], 0)

    def test_capture_seal_and_context_cannot_be_bypassed_by_authority_flags(self):
        source = b2_source()
        source["table_reads"][AVERAGES]["rows"][0]["Avg Drift"] = "0.001"
        result = bind_soft_story_b2(source)
        self.assertIn("GENERIC_SOURCE_SEAL_MISMATCH", result["reason_codes"])
        for field, value in (("selection_restored", False), ("model_units_code", 5),
                             ("model_locked", False), ("table_reads", [])):
            source = b2_source()
            source[field] = value
            source["formal_compliance"] = "PASS"
            result = bind_soft_story_b2(reseal(source))
            self.assertEqual(result["status"], "BLOCKED_SOURCE")
            self.assertEqual(result["formal_compliance"], "NOT_PROVEN")

    def test_point_elevations_detect_wrong_table_order(self):
        source = b2_source()
        source["table_reads"][STORIES]["rows"].reverse()
        result = bind_soft_story_b2(reseal(source))
        self.assertEqual(result["status"], "BLOCKED_SOURCE")
        self.assertIn("B2_STORY_ORDER_POINT_ELEVATION_CONFLICT", result["reason_codes"][0])

    def test_adjacent_numbered_steps_and_one_sided_step_identity_are_rejected(self):
        for names in ((AVERAGES, DRIFTS), (AVERAGES,)):
            source = b2_source()
            for name in names:
                raw = source["table_reads"][name]
                raw["fields"].append("StepNumber")
                raw["field_metadata"]["field_keys"] = list(raw["fields"])
                raw["field_metadata"]["units_by_field"]["StepNumber"] = ""
                for row in raw["rows"]:
                    row["StepNumber"] = "1" if row["Story"] == "Lower" else "2"
            result = bind_soft_story_b2(reseal(source))
            self.assertEqual(result["comparison_coverage"]["resolved"], 0)
            self.assertIn("B2_NUMBERED_STEP_OR_BRANCH_UNSUPPORTED", result["reason_codes"])

    def test_no_trigger_wording_cannot_hide_missing_coverage(self):
        source = b2_source()
        for name in (AVERAGES, DRIFTS):
            raw = source["table_reads"][name]
            raw["rows"] = [r for r in raw["rows"] if r["Story"] != "Lower"]
            raw["row_count"] = len(raw["rows"])
        result = bind_soft_story_b2(reseal(source))
        self.assertEqual(result["threshold_exceeded_comparisons"], 0)
        self.assertEqual(result["numeric_condition"], "B2_SOURCE_SCENARIO_UNRESOLVED")

    def test_unrelated_capture_failure_does_not_block_b2(self):
        source = b2_source()
        source["status"] = "PARTIAL"
        source["table_reads"]["Joint Displacements"] = {"status": "CAPTURE_ERROR"}
        result = bind_soft_story_b2(reseal(source))
        self.assertEqual(result["status"], "SOURCE_NUMERICAL")
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_numeric_story_name_never_authorizes_basement_exclusion(self):
        result = bind_soft_story_b2(b2_source(numeric_names=True))
        self.assertEqual(result["expected_count"], 6)
        self.assertTrue(all(x["applicability"] == "BASEMENT_AND_PHYSICAL_SCOPE_NOT_PROVEN"
                            for x in result["story_results"]))

    def test_absent_capture_is_local_block_with_unknown_coverage(self):
        result = bind_soft_story_b2(None, capture_error="CAPTURE_FAILED")
        self.assertFalse(result["coverage_known"])
        self.assertEqual(result["items"], [])
        self.assertEqual(result["status"], "BLOCKED_SOURCE")

    def test_malformed_optional_capture_error_cannot_break_export_serialization(self):
        for error in (float("nan"), float("inf"), {"error": float("nan")}, False):
            result = bind_soft_story_b2(None, capture_error=error)
            self.assertEqual(result["status"], "BLOCKED_SOURCE")
            self.assertEqual(result["source_capture_error"], "B2_CAPTURE_ERROR_FIELD_NOT_TEXT")
            self.assertEqual(len(result["result_sha256"]), 64)

    def test_malformed_story_identity_cannot_claim_known_zero_denominator(self):
        source = b2_source()
        for raw in source["table_reads"].values():
            for row in raw["rows"]:
                if row.get("Story") == "Lower":
                    row["Story"] = " Lower"
        result = bind_soft_story_b2(reseal(source))
        self.assertFalse(result["coverage_known"])
        self.assertEqual(result["reason_codes"], ["B2_STORY_IDENTITY_INVALID"])
        self.assertEqual(result["source_rows"], [])


if __name__ == "__main__":
    unittest.main()
