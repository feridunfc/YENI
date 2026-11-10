"""Independent wall geometry oracles; every committed fixture is synthetic."""
from copy import deepcopy
from decimal import Decimal as D
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from tbdy_next.wall_geometry import bind_wall_geometry, geometry_subconditions, rectangular_vertical_panel
from tbdy_next.web import make_handler
from test_quick_suite import fake_live_suite
from test_vs07_physical_story_scope import b1_scope_sources
from test_vs07_soft_story_b2 import reseal


def snapshot():
    geometry, loads, delta = b1_scope_sources()
    geometry.update(model_locked=True, model_units_unchanged=True, selection_restored=True)
    props = geometry["table_reads"]["Wall Property Definitions - Specified"]
    for row in props["rows"]:
        row.update(Material="C35/45", ModelType="Shell-Thick")
    props["fields"].extend(["Material", "ModelType"])
    props["field_metadata"]["field_keys"] = props["fields"][:]
    payload = deepcopy(fake_live_suite("Modal"))
    payload.update(vs06_b1_geometry_source=reseal(geometry), vs06_wall_load_source=loads,
                   vs05_delta_source=delta)
    return payload


def reseal_sources(payload):
    for key in ("vs06_b1_geometry_source", "vs05_delta_source"):
        payload[key] = reseal(payload[key])
    return payload


class WallGeometryOracleTests(unittest.TestCase):
    def test_independent_exact_boundary_and_just_below(self):
        r = geometry_subconditions(panel_length_m="1.5", thickness_m=".25", story_height_m="4")
        self.assertEqual(D(r["panel_length_thickness_ratio"]), D(6))
        self.assertEqual(D(r["ordinary_branch_minimum_mm"]), D(250))
        self.assertTrue(all(s["status"] == "MEETS_SUBCONDITION" for s in r["subconditions"]))
        r = geometry_subconditions(panel_length_m="1.5", thickness_m=".2499", story_height_m="4")
        self.assertEqual([s["rule"] for s in r["subconditions"] if s["status"].startswith("DOES_NOT")],
                         ["thickness_250", "thickness_h16"])
        r = geometry_subconditions(panel_length_m="1.4999", thickness_m=".25", story_height_m="4")
        self.assertEqual(r["subconditions"][0]["status"], "DOES_NOT_MEET_SUBCONDITION")

    def test_unproven_special_branches_do_not_reduce_ordinary_limits(self):
        r = geometry_subconditions(panel_length_m="7.5", thickness_m=".25", story_height_m="5")
        self.assertEqual(D(r["ordinary_branch_minimum_mm"]), D("312.5"))
        self.assertEqual(r["subconditions"][2]["status"], "DOES_NOT_MEET_SUBCONDITION")
        r = geometry_subconditions(panel_length_m="1.2", thickness_m=".2", story_height_m="4")
        self.assertEqual(D(r["panel_length_thickness_ratio"]), D(6))
        self.assertEqual(D(r["ordinary_branch_minimum_mm"]), D(250))
        self.assertEqual(sum(s["status"].startswith("DOES_NOT") for s in r["subconditions"]), 2)

    def test_rotated_negative_coordinates_give_independent_three_four_five_length(self):
        points = [{"X": x, "Y": y, "Z": z} for x, y in (("-2", "-3"), ("1", "1")) for z in ("-1", "3")]
        shape = rectangular_vertical_panel(points)
        self.assertEqual((shape["length_m"], shape["panel_height_m"]), (D(5), D(4)))
        self.assertEqual((shape["area_m2"], shape["perimeter_m"]), (D(20), D(18)))
        points[0]["X"] = "-1.9"
        with self.assertRaises(ValueError): rectangular_vertical_panel(points)

    def test_invalid_dimensions_and_degenerate_polygons_do_not_compute(self):
        for value in ("0", "-1", "NaN", "Infinity", True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                geometry_subconditions(panel_length_m="2", thickness_m=value, story_height_m="4")
        with self.assertRaises(ValueError): rectangular_vertical_panel([{"X": "0", "Y": "0", "Z": "0"}] * 4)


class WallGeometrySourceTests(unittest.TestCase):
    def test_same_run_sources_replay_deterministically_without_edits_or_code_authority(self):
        src = snapshot()
        before = deepcopy(src)
        result = bind_wall_geometry(src)
        self.assertEqual(result["status"], "SOURCE_NUMERICAL", result["reason_codes"])
        self.assertEqual((result["expected_count"], result["evaluated_count"]), (2, 2))
        self.assertEqual((result["subconditions_evaluated"], result["subconditions_unmet"]), (6, 2))
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertFalse(result["numerical_pass_issued"])
        self.assertEqual({r["code_ref"] for r in result["unevaluated_requirements"]},
                         {"7.6.1", "7.6.1.1", "7.6.1.2", "7.6.1.2(b)", "7.6.1.2(c)", "7.6.1.3", "13.1.6"})
        self.assertEqual(bind_wall_geometry(src), result)
        self.assertEqual(src, before)

    def test_partial_height_panel_uses_full_story_height(self):
        src = snapshot()
        for key in ("vs06_b1_geometry_source", "vs05_delta_source"):
            tables = src[key]["table_reads"]
            for row in tables["Story Definitions"]["rows"]:
                if row["Story"] == "+3.00": row["Height"] = "5.2"
            for point in tables["Point Object Connectivity"]["rows"]:
                point["Z"] = {"0": "3.7", "3": "5.2", "6": "8.2"}[point["Z"]]
        src["vs06_b1_geometry_source"]["table_reads"]["Wall Property Definitions - Specified"]["rows"][0]["Thickness"] = ".3"
        r = bind_wall_geometry(reseal_sources(src))
        first = next(x for x in r["items"] if x["element_id"] == "W1")
        self.assertEqual(D(first["panel_height_m"]), D("1.5"))
        self.assertEqual(D(first["story_height_m"]), D("5.2"))
        self.assertEqual(D(first["ordinary_branch_minimum_mm"]), D(325))
        self.assertEqual(first["subconditions"][2]["status"], "DOES_NOT_MEET_SUBCONDITION")

    def test_missing_assignment_endpoint_native_vertex_or_property_keeps_denominator(self):
        for defect in ("assignment", "endpoint", "native_vertex", "story", "property"):
            src = snapshot()
            tables = src["vs06_b1_geometry_source"]["table_reads"]
            if defect == "assignment":
                t = tables["Area Assignments - Section Properties"]
                t["rows"] = [r for r in t["rows"] if r["UniqueName"] != "W1"]
                t["row_count"] = len(t["rows"])
            elif defect == "endpoint": tables["Wall Object Connectivity"]["rows"][0]["UniquePt1"] = "MISSING"
            elif defect == "native_vertex": src["vs05_delta_source"]["physical_object_inventory"]["objects"]["Area"][0]["point_names"].append("A4")
            elif defect == "story": tables["Area Assignments - Section Properties"]["rows"][0]["Story"] = "UNRESOLVED"
            else: tables["Area Assignments - Section Properties"]["rows"][0]["SectProp"] = "MISSING"
            result = bind_wall_geometry(reseal_sources(src))
            with self.subTest(defect=defect):
                self.assertEqual((result["expected_count"], result["evaluated_count"], result["not_proven_count"]), (2, 1, 1))
                self.assertEqual(result["items"][0]["status"], "NOT_PROVEN")

    def test_orphan_wall_assignment_remains_an_unresolved_expected_object(self):
        src = snapshot()
        t = src["vs06_b1_geometry_source"]["table_reads"]["Wall Object Connectivity"]
        t["rows"].pop(); t["row_count"] -= 1
        r = bind_wall_geometry(reseal_sources(src))
        self.assertEqual((r["expected_count"], r["evaluated_count"]), (2, 1))

    def test_bad_seal_units_or_foreign_story_geometry_blocks_check_only(self):
        for defect in ("seal", "units", "foreign", "missing", "duplicate"):
            src = snapshot()
            g = src["vs06_b1_geometry_source"]
            if defect == "seal": g["payload_sha256"] = "0" * 64
            elif defect == "units": g["table_reads"]["Wall Property Definitions - Specified"]["field_metadata"]["units_by_field"]["Thickness"] = "mm"
            elif defect == "foreign": src["vs05_delta_source"]["model"] = "OTHER.EDB"
            elif defect == "missing": del src["vs05_delta_source"]
            else:
                t = g["table_reads"]["Wall Object Connectivity"]
                t["rows"].append(deepcopy(t["rows"][0])); t["row_count"] += 1
            if defect not in ("seal", "missing"): reseal_sources(src)
            with self.subTest(defect=defect):
                r = bind_wall_geometry(src)
                self.assertEqual(r["status"], "BLOCKED_SOURCE")
                self.assertEqual(r["evaluated_count"], 0)
                self.assertEqual(r["engineering_release"], "NOT_READY")

    def test_material_name_and_user_flags_never_prove_concrete_or_exemption(self):
        src = snapshot()
        src["geometry_capture"]["material_types"]["facts"]["C35/45"]["material_type_code"] = True
        r = bind_wall_geometry(src)
        self.assertEqual(r["not_proven_count"], 2)
        src = snapshot()
        src.update(formal_compliance="PASS", basement_exemption=True, both_ends_restrained=True)
        self.assertEqual(bind_wall_geometry(src), bind_wall_geometry(snapshot()))

    def test_display_rounding_reconciles_but_real_area_conflict_does_not(self):
        src = snapshot()
        for key in ("vs06_b1_geometry_source", "vs05_delta_source"):
            for p in src[key]["table_reads"]["Point Object Connectivity"]["rows"]:
                if p["UniqueName"] in ("A2", "A5", "A7"): p["X"] = "1.7016666667"
        t = src["vs06_b1_geometry_source"]["table_reads"]["Wall Object Connectivity"]
        t["fields"].append("Area"); t["field_metadata"]["field_keys"] = t["fields"][:]
        t["field_metadata"]["units_by_field"]["Area"] = "m2"
        for row in t["rows"]: row["Area"] = "5.11"
        r = bind_wall_geometry(reseal_sources(src))
        self.assertEqual(r["evaluated_count"], 2, r["reason_codes"])
        src["vs06_b1_geometry_source"]["table_reads"]["Wall Object Connectivity"]["rows"][0]["Area"] = "5.13"
        r = bind_wall_geometry(reseal_sources(src))
        self.assertEqual((r["evaluated_count"], r["not_proven_count"]), (1, 1))

    def test_proven_non_concrete_is_explicit_not_applicable(self):
        src = snapshot()
        src["geometry_capture"]["material_types"]["facts"]["C35/45"]["material_type_code"] = 1
        r = bind_wall_geometry(src)
        self.assertEqual(r["not_applicable_count"], 2)
        self.assertEqual(r["evaluated_count"], 0)
        self.assertEqual(r["status"], "NOT_APPLICABLE")

    def test_malformed_material_fact_preserves_every_expected_panel(self):
        src = snapshot()
        src["geometry_capture"]["material_types"]["facts"]["C35/45"] = None
        r = bind_wall_geometry(src)
        self.assertEqual((r["expected_count"], len(r["items"]), r["not_proven_count"]), (2, 2, 2))
        self.assertEqual(r["evaluated_count"], 0)

    def test_duplicate_native_polygon_cannot_override_conflicting_vertices(self):
        records = []
        for reverse in (False, True):
            src = snapshot()
            native = src["vs05_delta_source"]["physical_object_inventory"]["objects"]["Area"]
            extra = deepcopy(native[0]); extra["point_names"].append("A4")
            native.insert(0, extra)
            if reverse: native.reverse()
            result = bind_wall_geometry(reseal_sources(src))
            self.assertEqual((result["evaluated_count"], result["not_proven_count"]), (1, 1))
            first = next(r for r in result["items"] if r["element_id"] == "W1")
            self.assertEqual(first["reason"], "WALL_NATIVE_POLYGON_DUPLICATE_IDENTITY")
            records.append(result["items"])
        self.assertEqual(*records)


class WallGeometryDeliveryTests(unittest.TestCase):
    def test_single_capture_report_html_registry_and_receipts(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            calls = []
            def capture(case):
                calls.append(case)
                return snapshot()
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, live_capture=capture))
            thread = Thread(target=server.serve_forever, daemon=True); thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            def get(route):
                with urlopen(base + route, timeout=10) as response: return response.read()
            try:
                request = Request(base + "/api/live-suite?case=Modal", data=b"", method="POST")
                with urlopen(request, timeout=10) as response: run_id = json.load(response)["run_id"]
                before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                report = json.loads(get("/api/export-checks?run_id=" + run_id))
                wall = report["wall_geometry"]
                self.assertEqual(wall["evaluated_count"], 2, wall["reason_codes"])
                self.assertEqual(sum(x["check_id"] == "WALL_GEOMETRY_CHECK" for x in report["check_inventory"]["entries"]), 1)
                html = get("/report/print?run_id=" + run_id).decode()
                for value in ("Perde kesit geometrisi", wall["result_sha256"], "UNRESTRAINED_PLAN_LENGTH_NOT_PROVEN", "NOT_PROVEN"):
                    self.assertIn(value, html)
                checks = json.loads(get("/api/check-registry"))["checks"]
                entry = next(x for x in checks if x["check_id"] == "WALL_GEOMETRY_CHECK")
                self.assertEqual((entry["tab_id"], entry["panel_id"]), (13, "wallGeometryPanel"))
                self.assertEqual(json.loads(get("/api/export-checks?run_id=" + run_id)), report)
                self.assertEqual({p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}, before)
                self.assertEqual(calls, ["Modal"])
            finally:
                server.shutdown(); server.server_close(); thread.join(3)


if __name__ == "__main__":
    unittest.main()
