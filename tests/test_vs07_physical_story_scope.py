"""Synthetic object census, geometric exclusion and cross-check scope oracles."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from tbdy_next.physical_story_scope import (
    INVENTORY_SCHEMA, review_physical_story_scope, scope_story_drift,
    verified_excluded_stories, _digest,
)
from tbdy_next.soft_story_b2 import bind_soft_story_b2
from tbdy_next.story_drift_binding import bind_story_drift
from tbdy_next.vs06_drift_scenario import evaluate_drift_scenario
from tbdy_next.b1_source_bridge import B1BridgeError, evaluate_b1_sources
from test_vs05_story_delta import table
from test_vs07_soft_story_b2 import b2_source, reseal, STORIES, BASE, DRIFTS, AVERAGES
from test_vs06_c2_drift_scenario import scenario_report
from test_vs06_b1_source_bridge import sources as b1_sources
from test_etabs_source_gateway import FakeSap, FakeDb
from tools.etabs_source_gateway_windows import capture, capture_physical_object_inventory


def with_inventory(source, frames, areas):
    """frames/areas map ID to (observed type, all point IDs), never Story filters."""
    source = deepcopy(source)
    names = {"Frame": list(frames), "Area": list(areas), "Joint": [
        r["UniqueName"] for r in source["table_reads"]["Point Object Connectivity"]["rows"]]}
    sets = {kind: {"count": len(ids), "names": sorted(ids), "return_code": 0}
            for kind, ids in names.items()}
    frame_rows = [{"UniqueName": k, "Type": v[0]} for k, v in frames.items()]
    area_rows = [{"UniqueName": k, "PropType": v[0]} for k, v in areas.items()]
    wall_rows = [{"UniqueName": k} for k, v in areas.items() if v[0] == "Wall"]
    tables = [table("Frame Assignments - Summary", ["UniqueName", "Type"], frame_rows, {}),
              table("Area Assignments - Section Properties", ["UniqueName", "PropType"], area_rows, {}),
              table("Wall Object Connectivity", ["UniqueName"], wall_rows, {})]
    for raw in tables:
        if not raw["rows"]:
            raw["status"] = "EMPTY_TABLE"
    source["physical_object_inventory"] = {
        "schema": INVENTORY_SCHEMA, "status": "CAPTURED", "scope": "ALL_MODEL_OBJECTS",
        "model_locked_before": True, "model_locked_after": True,
        "names_before": deepcopy(sets), "names_after": deepcopy(sets),
        "objects": {kind: [{"name": k, "point_names": list(v[1]), "return_code": 0}
                           for k, v in family.items()]
                    for kind, family in (("Frame", frames), ("Area", areas))},
        "table_reads": {r["table_key"]: r for r in tables}, "reason_codes": [],
    }
    return reseal(source)


def physical_source():
    source = b2_source(numeric_names=True)
    definitions = source["table_reads"][STORIES]
    definitions["rows"].insert(0, {"Tower": "T1", "Story": "+13.00", "Height": "5"})
    definitions["row_count"] += 1
    points = source["table_reads"]["Point Object Connectivity"]
    for uid, x, y in (("4", "1", "0"), ("5", "1", "1"), ("6", "0", "1"), ("7", "-1", ".5")):
        points["rows"].append({"UniqueName": uid, "Story": "+8.00", "X": x, "Y": y, "Z": "8"})
    points["row_count"] = len(points["rows"])
    # Complete four case/direction slots per occupied level for STORY_DRIFT.
    for key in (DRIFTS, AVERAGES):
        raw = source["table_reads"][key]
        cross = [{**r, "Direction": "Y" if r["Direction"] == "X" else "X"} for r in raw["rows"]]
        raw["rows"].extend(cross)
        raw["row_count"] = len(raw["rows"])
    frames = {r["UniqueName"]: ("Column", [r["UniquePtI"], r["UniquePtJ"]])
              for r in source["table_reads"]["Column Object Connectivity"]["rows"]}
    frames["N1"] = ("Null", ["3", "4"])
    areas = {"S1": ("Slab", ["3", "4", "5", "6", "7"]),
             "O1": ("Opening", ["3", "4", "5"])}
    return with_inventory(source, frames, areas)


def b1_scope_sources():
    geometry, loads = b1_sources()
    heights = geometry["table_reads"][STORIES]
    heights["rows"] = [{"Tower": "T1", **r} for r in reversed(heights["rows"])]
    heights["fields"].insert(0, "Tower")
    heights["field_metadata"]["field_keys"] = heights["fields"][:]
    points = geometry["table_reads"]["Point Object Connectivity"]
    for row in points["rows"]:
        row["Story"] = {"0": "Base", "3": "+3.00", "6": "+6.00"}[row["Z"]]
    points["fields"].append("Story")
    points["field_metadata"]["field_keys"] = points["fields"][:]
    geometry = reseal(geometry)
    delta = deepcopy(geometry)
    delta.update(model_locked=True, model_units_unchanged=True, selection_restored=True)
    delta["table_reads"][BASE] = table(BASE, ["Tower", "BSName", "BSElev"],
        [{"Tower": "T1", "BSName": "Base", "BSElev": "0"}], {"BSElev": "m"})
    frames = {r["UniqueName"]: ("Column", [r["UniquePtI"], r["UniquePtJ"]])
              for r in delta["table_reads"]["Column Object Connectivity"]["rows"]}
    frames.update({r["UniqueName"]: ("Beam", [r["UniquePtI"], r["UniquePtJ"]])
                   for r in loads["table_reads"]["Beam Object Connectivity"]["rows"]})
    areas = {r["UniqueName"]: ("Wall", [r["UniquePt" + str(i)] for i in range(1, 5)])
             for r in delta["table_reads"]["Wall Object Connectivity"]["rows"]}
    return geometry, loads, with_inventory(delta, frames, areas)


class PhysicalScopeTests(unittest.TestCase):
    def test_complete_census_excludes_only_empty_top_and_preserves_eight_ratios(self):
        source = physical_source()
        before = deepcopy(source)
        scope = review_physical_story_scope(source)
        self.assertTrue(scope["source_inventory_complete"], scope["reason_codes"])
        self.assertEqual(scope["excluded_stories"], ["+13.00"])
        self.assertEqual((scope["defined_story_count"], scope["physical_story_count"]), (4, 3))
        top = scope["stories"][-1]
        self.assertEqual([top[k] for k in ("frames", "areas", "walls", "joints")], [0, 0, 0, 0])
        self.assertEqual(top["applicability"], "NOT_APPLICABLE")
        self.assertEqual(scope["object_counts"], {"Frame": 4, "Area": 2, "Joint": 8, "Wall": 0})
        b2 = bind_soft_story_b2(source)
        self.assertEqual(b2["comparison_coverage"], {"expected": 8, "resolved": 8, "unresolved": 0, "complete": True})
        self.assertEqual(b2["items"], bind_soft_story_b2(b2_source(numeric_names=True))["items"])
        self.assertEqual(b2["source_coverage_status"], "SOURCE_COVERAGE_COMPLETE")
        self.assertEqual(b2["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(source, before)

    def test_old_or_incomplete_inventory_keeps_twelve_expected_comparisons(self):
        for defect in ("absent", "failed", "filtered", "duplicate", "changed", "missing_frame",
                       "missing_point", "unresolved_endpoint", "truncated_polygon", "bool_return", "wall_mismatch"):
            source = physical_source()
            probe = source["physical_object_inventory"]
            if defect == "absent": del source["physical_object_inventory"]
            elif defect == "failed": probe["status"] = "CAPTURE_ERROR"
            elif defect == "filtered": probe["scope"] = "SELECTED_OBJECTS"
            elif defect == "duplicate": probe["names_before"]["Joint"]["names"][0] = "1"
            elif defect == "changed": probe["names_after"]["Frame"]["names"][0] = "OTHER"
            elif defect == "missing_frame": probe["objects"]["Frame"].pop()
            elif defect == "missing_point": probe["names_before"]["Joint"]["count"] += 1
            elif defect == "unresolved_endpoint": probe["objects"]["Frame"][0]["point_names"][0] = "MISSING"
            elif defect == "truncated_polygon": probe["objects"]["Area"][0]["point_names"] = ["3", "4"]
            elif defect == "bool_return": probe["objects"]["Area"][0]["return_code"] = False
            elif defect == "wall_mismatch": probe["table_reads"]["Area Assignments - Section Properties"]["rows"][0]["PropType"] = "Wall"
            source = reseal(source)
            with self.subTest(defect=defect):
                scope = review_physical_story_scope(source)
                self.assertFalse(scope["source_inventory_complete"])
                self.assertEqual(scope["excluded_stories"], [])
                self.assertTrue(all(r["applicability"] == "UNKNOWN" for r in scope["stories"]))
                self.assertEqual(bind_soft_story_b2(source)["comparison_coverage"]["expected"], 12)

    def test_null_frame_and_polygon_crossing_band_without_interior_joint_prevent_exclusion(self):
        for kind in ("Frame", "Area"):
            source = physical_source()
            points = source["table_reads"]["Point Object Connectivity"]
            # Its Story label intentionally does not select the candidate band.
            points["rows"].append({"UniqueName": "HIGH", "Story": "Unassigned", "X": "1", "Y": "1", "Z": "20"})
            points["row_count"] += 1
            p = source["physical_object_inventory"]
            for when in ("names_before", "names_after"):
                p[when]["Joint"]["names"].append("HIGH")
                p[when]["Joint"]["count"] += 1
            target = next(r for r in p["objects"][kind] if r["name"] == ("N1" if kind == "Frame" else "S1"))
            target["point_names"][-1] = "HIGH"
            scope = review_physical_story_scope(reseal(source))
            self.assertTrue(scope["source_inventory_complete"], scope["reason_codes"])
            top = scope["stories"][-1]
            self.assertEqual(top["joints"], 0)
            self.assertEqual(top["applicability"], "IN_SCOPE")
            self.assertGreater(top["frames" if kind == "Frame" else "areas"], 0)

    def test_any_joint_above_lower_boundary_keeps_story_even_inside_coordinate_tolerance(self):
        source = physical_source()
        for row in source["table_reads"]["Point Object Connectivity"]["rows"]:
            if row["UniqueName"] == "7": row["Z"] = "8.0000001"
        scope = review_physical_story_scope(reseal(source))
        self.assertTrue(scope["source_inventory_complete"])
        self.assertEqual(scope["excluded_stories"], [])

    def test_native_zero_conflicting_with_table_and_empty_story_with_demand_stay_unknown(self):
        for defect in ("zero", "demand"):
            source = physical_source()
            if defect == "zero":
                p = source["physical_object_inventory"]
                for when in ("names_before", "names_after"):
                    p[when]["Area"] = {"count": 0, "names": [], "return_code": 0}
                p["objects"]["Area"] = []
            else:
                raw = source["table_reads"][DRIFTS]
                raw["rows"].append({**raw["rows"][0], "Story": "+13.00"})
                raw["row_count"] += 1
            scope = review_physical_story_scope(reseal(source))
            self.assertFalse(scope["source_inventory_complete"])
            self.assertEqual(scope["excluded_stories"], [])

    def test_story_drift_and_c2_share_scope_without_editing_raw_records(self):
        source = physical_source()
        raw = bind_story_drift(source)
        before = deepcopy(raw)
        self.assertEqual((len(raw["items"]), raw["expected_story_case_direction_count"]), (12, 16))
        scope = review_physical_story_scope(source)
        scoped = scope_story_drift(raw, source, scope)
        self.assertEqual(scoped["expected_story_case_direction_count"], 12)
        self.assertTrue(scoped["all_stories_covered"])
        self.assertEqual(scoped["status"], "SOURCE_COVERAGE_COMPLETE")
        report = scenario_report((source, raw))
        report.update(story_drift=scoped, physical_story_scope=scope)
        result = evaluate_drift_scenario(report)
        self.assertEqual((result["source_numeric_count"], result["expected_story_direction_count"]), (6, 6))
        self.assertEqual(result["excluded_stories"], scoped["excluded_stories"])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(raw, before)
        blocked = bind_story_drift(None)
        self.assertEqual(scope_story_drift(blocked, source, scope), blocked)

    def test_b1_shares_verified_scope_and_rejects_foreign_geometry_and_topology(self):
        geometry, loads, delta = b1_scope_sources()
        scope = review_physical_story_scope(delta)
        self.assertTrue(scope["source_inventory_complete"], scope["reason_codes"])
        baseline = evaluate_b1_sources(geometry, loads)
        result = evaluate_b1_sources(geometry, loads, physical_scope=scope, physical_scope_source=delta)
        self.assertEqual(result["b1_numerical"], baseline["b1_numerical"])
        self.assertEqual(result["excluded_stories"][0]["story"], "+9.00")
        self.assertEqual(result["physical_source_coverage"], "SOURCE_COVERAGE_COMPLETE")
        self.assertEqual(baseline["physical_source_coverage"], "UNKNOWN")
        for defect in ("point", "frame", "wall"):
            changed = deepcopy(geometry)
            key = {"point": "Point Object Connectivity", "frame": "Frame Assignments - Section Properties",
                   "wall": "Wall Object Connectivity"}[defect]
            row = changed["table_reads"][key]["rows"][0]
            row[{"point": "Z", "frame": "UniqueName", "wall": "UniquePt1"}[defect]] = {"point": "1", "frame": "OTHER", "wall": "A6"}[defect]
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                verified_excluded_stories(scope, reseal(changed), inventory_source=delta)

    def test_scope_digest_and_source_geometry_cannot_be_replaced(self):
        source = physical_source()
        scope = review_physical_story_scope(source)
        scope["excluded_stories"].append("+8.00")
        with self.assertRaises(ValueError): verified_excluded_stories(scope, source)
        self.assertEqual(bind_soft_story_b2(source, physical_scope=scope)["status"], "BLOCKED_SOURCE")

    def test_empty_internal_level_does_not_invent_a_new_b2_height_or_neighbour(self):
        source = physical_source()
        point = next(r for r in source["table_reads"]["Point Object Connectivity"]["rows"] if r["UniqueName"] == "2")
        point["Z"] = "0"
        frame = next(r for r in source["physical_object_inventory"]["objects"]["Frame"] if r["name"] == "C3")
        frame["point_names"] = ["3", "4"]
        for key in (DRIFTS, AVERAGES):
            raw = source["table_reads"][key]
            raw["rows"] = [r for r in raw["rows"] if r["Story"] != "+3.00"]
            raw["row_count"] = len(raw["rows"])
        source = reseal(source)
        scope = review_physical_story_scope(source)
        self.assertEqual(scope["excluded_stories"], ["+3.00", "+13.00"])
        result = bind_soft_story_b2(source)
        self.assertEqual(result["status"], "BLOCKED_SOURCE")
        self.assertIn("B2_PHYSICAL_STORY_HEIGHT_GAP_NO_ADJACENCY_INVENTED", result["reason_codes"])
        self.assertEqual(result["items"], [])

    def test_b1_physical_presence_without_vertical_resistance_cannot_be_silently_excluded(self):
        geometry, loads, delta = b1_scope_sources()
        row = {"UniqueName": "SPECIAL", "Story": "+9.00", "X": "0", "Y": "0", "Z": "7"}
        for source in (geometry, delta):
            raw = source["table_reads"]["Point Object Connectivity"]
            raw["rows"].append(dict(row))
            raw["row_count"] += 1
        for when in ("names_before", "names_after"):
            names = delta["physical_object_inventory"][when]["Joint"]
            names["names"].append("SPECIAL")
            names["count"] += 1
        geometry, delta = reseal(geometry), reseal(delta)
        scope = review_physical_story_scope(delta)
        self.assertEqual(scope["excluded_stories"], [])
        with self.assertRaisesRegex(B1BridgeError, "PHYSICAL_STORY_VERTICAL_RESISTANCE_UNRESOLVED"):
            evaluate_b1_sources(geometry, loads, physical_scope=scope, physical_scope_source=delta)

    def test_resealed_scope_cannot_remove_an_exceedance_from_unchanged_source(self):
        source = physical_source()
        scope = review_physical_story_scope(source)
        scope["stories"][0]["applicability"] = "NOT_APPLICABLE"
        scope["excluded_stories"].append("+0.00")
        scope["scope_sha256"] = _digest({k: v for k, v in scope.items() if k != "scope_sha256"})
        with self.assertRaisesRegex(ValueError, "SOURCE_REPLAY_CONFLICT"):
            verified_excluded_stories(scope, source)
        self.assertEqual(bind_soft_story_b2(source, physical_scope=scope)["status"], "BLOCKED_SOURCE")


class PhysicalGatewayTests(unittest.TestCase):
    def sap(self):
        source = physical_source()
        probe = source["physical_object_inventory"]
        sap = FakeSap(FakeDb())
        self.calls = []
        for kind, attr in (("Frame", "FrameObj"), ("Area", "AreaObj"), ("Joint", "PointObj")):
            ids = probe["names_before"][kind]["names"]
            objects = {r["name"]: r["point_names"] for r in probe["objects"].get(kind, [])}
            def get_points(name, family=kind, rows=objects):
                self.calls.append((family, name))
                refs = rows[name]
                return (*refs, 0) if family == "Frame" else (len(refs), tuple(refs), 0)
            setattr(sap, attr, SimpleNamespace(GetNameList=lambda ids=ids: (len(ids), tuple(ids), 0),
                                               GetPoints=get_points))
        for key, raw in probe["table_reads"].items():
            sap.DatabaseTables.fake_rows[key] = (tuple(raw["fields"]),
                [tuple(row[f] for f in raw["fields"]) for row in raw["rows"]], {})
        return sap

    def test_native_census_reads_null_frame_and_every_polygon_vertex_without_writes(self):
        sap = self.sap()
        result = capture_physical_object_inventory(sap, max_objects=100)
        self.assertEqual(result["status"], "CAPTURED", result["reason_codes"])
        self.assertIn(("Frame", "N1"), self.calls)
        slab = next(r for r in result["objects"]["Area"] if r["name"] == "S1")
        self.assertEqual(slab["point_names"], ["3", "4", "5", "6", "7"])
        self.assertEqual(sap.DatabaseTables.set_calls, [])

    def test_missing_api_or_failed_connectivity_is_optional_capture_error_not_empty(self):
        for defect in ("api", "return", "polygon", "limit"):
            sap = self.sap()
            if defect == "api": del sap.AreaObj
            elif defect == "return": sap.FrameObj.GetPoints = lambda name: ("0", "1", 1)
            elif defect == "polygon": sap.AreaObj.GetPoints = lambda name: (5, ["3", "4", "5"], 0)
            result = capture_physical_object_inventory(sap, max_objects=2 if defect == "limit" else 100)
            self.assertEqual(result["status"], "CAPTURE_ERROR")
            self.assertTrue(result["reason_codes"])
        ordinary = capture(FakeSap(), action="capture", preset="delta", cases=("RSX", "RSY"))
        self.assertEqual(ordinary["status"], "CAPTURED")
        self.assertEqual(ordinary["physical_object_inventory"]["status"], "CAPTURE_ERROR")
        self.assertTrue(ordinary["selection_restored"])

    def test_native_population_change_and_boolean_return_are_not_zero_success(self):
        for defect in ("changed", "boolean"):
            sap = self.sap()
            responses = iter([(8, tuple(str(i) for i in range(8)), 0), (1, ("OTHER",), 0)])
            sap.PointObj.GetNameList = (lambda: next(responses)) if defect == "changed" else lambda: (0, (), False)
            result = capture_physical_object_inventory(sap, max_objects=100)
            self.assertEqual(result["status"], "CAPTURE_ERROR")


if __name__ == "__main__":
    unittest.main()
