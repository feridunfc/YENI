import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tbdy_next.basis_linkage import SPECTRUM_CASE, SPECTRUM_FUNCTION
from tbdy_next.engineering.design_scenario import prepare_pipeline_source
from tbdy_next.engineering.seismic_profile import _height_class, project_seismic_profile


def table(name, rows):
    return {"table_key": name, "status": "CAPTURED", "rows": rows, "row_count": len(rows)}


def model(functions, assignments, info=()):
    names = [dict(Name=n, Direction="Horizontal", R=r, D="2.5", I="1.5", SDS="0.52578") for n, r in functions]
    loads = [dict(Name=n, Function=f, LoadName=axis, Angle=angle, CoordSys=cs, TransAccSF="9.81")
             for n, f, axis, angle, cs in assignments]
    records = [table(SPECTRUM_FUNCTION, names), table(SPECTRUM_CASE, loads),
               table("Project Information", [{"Item": k, "Data": v} for k, v in info])]
    return {"source_mode": "LIVE_ETABS", "vs04_basis_probe": {"table_reads": {t["table_key"]: t for t in records}}}


class ProjectSpectrumTests(unittest.TestCase):
    def test_general_scan_fills_only_missing_fields_and_retains_both_runs(self):
        from test_quick_suite import fake_live_suite
        from tbdy_next.web import make_handler

        with TemporaryDirectory() as tmp:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Path(tmp), live_capture=fake_live_suite))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(thread.join, 3)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            base = "http://127.0.0.1:" + str(server.server_port)

            def post(path, body):
                req = Request(base + path, data=json.dumps(body).encode() if body else b"", method="POST",
                              headers={"Content-Type": "application/json"})
                with urlopen(req, timeout=15) as response:
                    return json.load(response)

            original = post("/api/live-suite?case=Modal", {})
            values = {"Rx": 5, "Ry": 4, "I": 1.2, "SDS": 0.50, "DD": "DD-2", "HN": 10.5}
            revised = post("/api/project-parameters", {"base_run_id": original["run_id"], "project_parameters": values})
            fields = revised["seismic_project_profile"]["fields"]
            self.assertEqual([fields[k]["value"] for k in ("BKS", "DTS", "BYS")], [2, "2", 7])
            self.assertNotEqual(original["run_id"], revised["run_id"])
            self.assertIsNone(original["seismic_project_profile"]["fields"]["BYS"]["value"])
            with urlopen(base + "/api/export-checks?run_id=" + revised["run_id"]) as response:
                report = json.load(response)
            self.assertEqual(report["seismic_profile_origin"], "SEALED_RUN_RESULT")
            self.assertEqual(report["seismic_project_profile"], revised["seismic_project_profile"])
            with self.assertRaises(HTTPError) as error:
                post("/api/project-parameters", {"base_run_id": revised["run_id"], "project_parameters": {"BKS": 3}})
            self.assertEqual(error.exception.code, 422)

    def test_two_assigned_functions_and_unused_function(self):
        source = model([("trans", "4"), ("long", "7"), ("unused", "2")],
                       [("north", "trans", "U1", 90, "Global"), ("east", "long", "U2", -90, "Global")])
        profile = project_seismic_profile(source)
        fields = profile["fields"]
        self.assertEqual([fields[k]["value"] for k in ("Rx", "Ry", "I", "BKS")], [7, 4, 1.5, 1])
        self.assertIn("east / long", fields["Rx"]["basis"])
        self.assertIsNone(fields["DTS"]["value"])

    def test_unmapped_secondary_case_and_conflicting_functions_require_input(self):
        source = model([("A", 4), ("B", 8)], [("one", "A", "U1", 0, "Global"),
                       ("two", "B", "U1", 0, "Global"), ("three", "B", "U2", 0, "Global")])
        fields = project_seismic_profile(source)["fields"]
        self.assertIsNone(fields["Rx"]["value"])
        self.assertEqual(fields["Ry"]["value"], 8)
        source["vs04_basis_probe"]["table_reads"][SPECTRUM_CASE]["rows"][1]["CoordSys"] = "Local"
        self.assertIsNone(project_seismic_profile(source)["fields"]["Ry"]["value"])

    def test_dd2_and_seismic_base_drive_height_not_empty_roof(self):
        source = model([("A", 7)], [("x", "A", "U1", 0, "Global")], [("DD", "DD-2")])
        physical = {"source_inventory_complete": True, "stories": [
            {"applicability": "IN_SCOPE", "upper_elevation_m": "9.0"},
            {"applicability": "NOT_APPLICABLE", "upper_elevation_m": "14.5"}]}
        basement = {"candidate_m": 0., "foundation_m": -5.15}
        p = project_seismic_profile(source, physical_scope=physical, basement=basement)
        self.assertEqual(p["fields"]["DTS"]["value"], "2a")
        self.assertEqual([s["BYS"] for s in p["height_scenarios"]], [7, 6])
        self.assertIsNone(p["fields"]["BYS"]["value"])
        basement["design_base_m"] = -5.15
        self.assertEqual(project_seismic_profile(source, physical_scope=physical, basement=basement)["fields"]["BYS"]["value"], 6)
        self.assertEqual([_height_class(h, "4a") for h in (10.5, 56., 91., 105., 106.)], [8, 4, 3, 2, 1])

    def test_native_project_classes_and_manual_input_are_bound_to_source(self):
        source = model([("curve", 7)], [("x", "curve", "U1", 0, "Global")], [("BYS", "7")])
        raw = json.dumps(source).encode()
        prepared = prepare_pipeline_source(raw, project_parameters={"Ry": 5, "DD": "DD-2"})
        with TemporaryDirectory() as tmp:
            prepared.archive_parent(Path(tmp))
            replay = prepare_pipeline_source(prepared.raw, source_directory=Path(tmp))
        fields = project_seismic_profile(replay.payload)["fields"]
        self.assertEqual((fields["Ry"]["value"], fields["Ry"]["origin"]), (5, "PROJECT_INPUT"))
        self.assertEqual(fields["BYS"]["origin"], "ETABS_PROJECT")
        self.assertEqual(fields["DTS"]["value"], "2a")
        with self.assertRaisesRegex(ValueError, "PROJECT_PARAMETER_CONFLICT:Rx"):
            project_seismic_profile(prepare_pipeline_source(raw, project_parameters={"Rx": 8}).payload)
        for key, value in (("Ry", False), ("BYS", 9), ("DTS", "unknown"), ("S1", "NaN")):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "PROJECT_PARAMETER_INVALID"):
                prepare_pipeline_source(raw, project_parameters={key: value})

    def test_verified_axis_factors_reach_the_two_numerical_owners(self):
        from test_r08_story_second_order import fixture
        from test_vs06_c2_drift_scenario import scenario_report
        from tbdy_next.story_second_order import bind_story_second_order
        from tbdy_next.vs06_drift_scenario import evaluate_drift_scenario

        source = model([("east", 7), ("north", 4)], [("RSX","east","U1",0,"Global"), ("RSY","north","U2",0,"Global")])
        profile = project_seismic_profile(source)
        owner = bind_story_second_order(fixture(), project_profile=profile)
        self.assertEqual(owner["project_design_parameters"], {"R_X":7., "R_Y":4., "D_X":2.5, "D_Y":2.5})
        dx = float(owner["direction_results"]["X"]["theta_limit_reference"])
        dy = float(owner["direction_results"]["Y"]["theta_limit_reference"])
        self.assertAlmostEqual(dy / dx, 7 / 4)
        report = {**scenario_report(), "seismic_project_profile": profile}
        directional = evaluate_drift_scenario(report)
        same_r = evaluate_drift_scenario(report, {"r":"7"})
        for row, ref in zip(directional["rows"], same_r["rows"], strict=True):
            if ref["effective_delta_mm"] and float(ref["effective_delta_mm"]) != 0:
                self.assertAlmostEqual(float(row["effective_delta_mm"]) / float(ref["effective_delta_mm"]),
                                       1 if row["direction"] == "X" else 4 / 7)
        source["vs04_basis_probe"]["read_only_invariant_proven"] = False
        missing = project_seismic_profile(source)
        self.assertIsNone(missing["fields"]["Rx"]["value"])
        blocked = bind_story_second_order(fixture(), project_profile=missing)
        self.assertEqual(blocked["evaluated_story_direction_count"], 0)
        self.assertGreater(blocked["expected_story_direction_count"], 0)

    def test_zero_damping_does_not_become_missing(self):
        source = model([("A", 7)], [("x", "A", "U1", 0, "Global")])
        source["vs04_basis_probe"]["table_reads"][SPECTRUM_FUNCTION]["rows"][0]["DampRatio"] = "0"
        self.assertEqual(project_seismic_profile(source)["fields"]["DampRatio"]["value"], 0)


if __name__ == "__main__":
    unittest.main()
