"""Tests for live R10 column projection: joints, 7.5 limits, SCWB, shear/confinement and AxisAngle."""
from __future__ import annotations

import json
import math
from types import SimpleNamespace
import unittest

from tbdy_next.column_engine.source_bank import FIELDS
from tbdy_next.engineering.column_axial import PREFERENCES
from tbdy_next.engineering.column_live_gates import project_column_gates
from tbdy_next.engineering.column_pmm_section import (
    BAR_SIZES,
    COLUMN_REINFORCING,
    MECHANICAL,
    REBAR_DATA,
    SCHEMA as PMM_SEC_SCHEMA,
)
from tbdy_next.engineering.column_r10_live import (
    capture_r10_sources,
    member_local_axis_angle_deg,
    project_column_r10_live,
)
from tbdy_next.engineering.pipeline import STAGES, dag_coverage
import test_column_axial_live as live
from test_column_axial_live import SPECTRAL, STATIC
from test_r03_analysis_setup import capture_table


def _pmm_sec_source(*, name="Column_80x80", designed="Yes", bars2="4", bars3="4", spacing="0.15") -> dict:
    section = capture_table(
        COLUMN_REINFORCING,
        ["Name", "RebarMatL", "RebarMatC", "ReinfConfig", "IsDesigned", "Cover",
         "NumBars2Dir", "NumBars3Dir", "BarSizeLong", "BarSizeCorn", "BarSizeConf",
         "SpacingConf", "NumCBars2", "NumCBars3"],
        [(name, "B420C", "B420C", "Rectangular", designed, "0.04",
          bars2, bars3, "20", "20", "10", spacing, "3", "3")],
    )
    sizes = capture_table(BAR_SIZES, ["Name", "Diameter", "Area"], [
        ("20", "0.02", "0.000314"), ("10", "0.01", "0.0000785"),
    ])
    steel = capture_table(REBAR_DATA, ["Material", "Fy"], [("B420C", "420000")])
    elastic = capture_table(MECHANICAL, ["Material", "E1"], [("B420C", "200000000")])
    for table, units in (
        (section, {"Cover": "m", "SpacingConf": "m"}),
        (sizes, {"Diameter": "m", "Area": "m2"}),
        (steel, {"Fy": "kN/m2"}),
        (elastic, {"E1": "kN/m2"}),
    ):
        table["field_metadata"]["units_by_field"].update(units)
    return {
        "schema": PMM_SEC_SCHEMA, "model_locked_before": True, "model_locked_after": True,
        "units_before": 6, "units_after": 6,
        "table_reads": {t["table_key"]: t for t in (section, sizes, steel, elastic)},
    }


def _rowset(rows: list[tuple]) -> dict:
    cols = {name: [r[i] for r in rows] for i, name in enumerate(FIELDS)}
    return {"NumberResults": len(rows), "pRetVal": 0, **cols}


def _base_live_payload(*, axis_angle="90", enclosed_j=False, narrow_beam=False):
    """Build a minimal closed self-consistent LIVE_ETABS geometry/axial/pmm/source fixture."""
    rect_rows = [
        {"Name": "Column_80x80", "Material": "C35/45", "t2": "0.8", "t3": "0.8"},
        {"Name": "B60x70", "Material": "C35/45", "t2": "0.7", "t3": "0.6"},
    ]
    if narrow_beam:
        rect_rows.append({"Name": "B40x70", "Material": "C35/45", "t2": "0.4", "t3": "0.7"})

    beam_conns = [
        {"UniqueName": "511", "BeamBay": "B219", "Story": "+4.50", "UniquePtI": "412", "UniquePtJ": "413"},
        {"UniqueName": "516", "BeamBay": "B224", "Story": "+4.50", "UniquePtI": "412", "UniquePtJ": "414"},
    ]
    fa_rows = [
        {"UniqueName": "127", "Label": "C88", "Story": "+4.50", "AnalysisSect": "Column_80x80", "AxisAngle": axis_angle},
        {"UniqueName": "511", "Label": "B219", "Story": "+4.50", "AnalysisSect": "B60x70", "AxisAngle": "0"},
        {"UniqueName": "516", "Label": "B224", "Story": "+4.50", "AnalysisSect": "B60x70", "AxisAngle": "0"},
    ]
    pts = [
        {"UniqueName": "1044", "X": "0.0", "Y": "0.0", "Z": "0.0"},
        {"UniqueName": "412", "X": "0.0", "Y": "0.0", "Z": "4.5"},
        {"UniqueName": "413", "X": "6.0", "Y": "0.0", "Z": "4.5"},
        {"UniqueName": "414", "X": "0.0", "Y": "5.0", "Z": "4.5"},
    ]
    if enclosed_j:
        b3_sect = "B40x70" if narrow_beam else "B60x70"
        beam_conns += [
            {"UniqueName": "517", "BeamBay": "B225", "Story": "+4.50", "UniquePtI": "412", "UniquePtJ": "415"},
            {"UniqueName": "518", "BeamBay": "B226", "Story": "+4.50", "UniquePtI": "412", "UniquePtJ": "416"},
        ]
        fa_rows += [
            {"UniqueName": "517", "Label": "B225", "Story": "+4.50", "AnalysisSect": b3_sect, "AxisAngle": "0"},
            {"UniqueName": "518", "Label": "B226", "Story": "+4.50", "AnalysisSect": "B60x70", "AxisAngle": "0"},
        ]
        pts += [
            {"UniqueName": "415", "X": "-6.0", "Y": "0.0", "Z": "4.5"},
            {"UniqueName": "416", "X": "0.0", "Y": "-5.0", "Z": "4.5"},
        ]

    payload = {
        "source_mode": "LIVE_ETABS",
        "geometry_capture": {
            "tables": {
                "FRAME_ASSIGNMENTS": {"fields": ["UniqueName", "Label", "Story", "AnalysisSect", "AxisAngle"], "rows": fa_rows},
                "COLUMN_CONNECTIVITY": {"fields": ["UniqueName", "ColumnBay", "Story", "UniquePtI", "UniquePtJ"], "rows": [
                    {"UniqueName": "127", "ColumnBay": "C88", "Story": "+4.50", "UniquePtI": "1044", "UniquePtJ": "412"}
                ]},
                "BEAM_CONNECTIVITY": {"fields": ["UniqueName", "BeamBay", "Story", "UniquePtI", "UniquePtJ"], "rows": beam_conns},
                "RECTANGULAR_SECTIONS": {"fields": ["Name", "Material", "t2", "t3"], "rows": rect_rows},
            }
        },
        "vs05_delta_source": {
            "table_reads": {
                "Point Object Connectivity": {"fields": ["UniqueName", "X", "Y", "Z"], "rows": pts}
            }
        },
        "column_axial": {
            "request": {
                "check": "column-pmm", "member": "127", "pmm_member": "127",
                "base_run_id": "RUN-TEST", "base_input_sha256": "sha-test",
                "combination_source": "ASSIGNED_DESIGN",
                "design_assignment": {"groups": {"gravity": [STATIC], "ductile": [SPECTRAL]}},
            },
            "force_source": {
                "combinations": [STATIC, SPECTRAL],
                "rowsets": {
                    "127": _rowset([
                        ("127", 0.0, "127-1", 0.0, STATIC, "Single Value", 0.0, -1200.0, 40.0, -30.0, 0.0, 50.0, -70.0),
                        ("127", 4.5, "127-1", 4.5, STATIC, "Single Value", 0.0, -1000.0, 40.0, -30.0, 0.0, -45.0, 65.0),
                        ("127", 0.0, "127-1", 0.0, SPECTRAL, "Max", 0.0, 200.0, 10.0, 10.0, 0.0, 20.0, 20.0),
                        ("127", 0.0, "127-1", 0.0, SPECTRAL, "Min", 0.0, -900.0, -10.0, -10.0, 0.0, -20.0, -20.0),
                    ])
                },
            },
            "pmm_section_source": _pmm_sec_source(),
            "design_preferences": capture_table(PREFERENCES, ["GammaC", "GammaS"], [("1.5", "1.15")]),
        },
    }
    geometry = {
        "checks": [
            {"check_id": "column_rect_min", "status": "EVALUATED", "items": [
                {"element_id": "127", "label": "C88", "story": "+4.50",
                 "section": "Column_80x80", "analysis_section": "Column_80x80",
                 "section_design_difference": False,
                 "material_classification": "RESOLVED_CONCRETE_USAGE",
                 "material_name": "C35/45", "width_mm": 800.0, "depth_mm": 800.0,
                 "t2_mm": 800.0, "t3_mm": 800.0, "frame_length_m": 4.5,
                 "i_joint_id": "1044", "j_joint_id": "412"}
            ]},
        ]
    }
    extra = {
        "checks": [
            {"check_id": "concrete_fck_25", "status": "EVALUATED", "items": [
                {"material_name": "C35/45", "fck_mpa": 35.0}
            ]}
        ]
    }
    axial = {
        "status": "NUMERICAL_COMPLETE",
        "combination_plan": {
            "source": "ASSIGNED_DESIGN",
            "design_assignment": {"groups": {"gravity": [STATIC], "ductile": [SPECTRAL]}},
            "combinations": [
                {"name": STATIC, "force_semantics": "STATIC_SIGNED_VECTOR"},
                {"name": SPECTRAL, "force_semantics": "MAX_MIN_UNPAIRED_ENVELOPE"},
            ],
        },
        "columns": [{
            "element_id": "127",
            "section": "Column_80x80",
            "material_name": "C35/45",
            "status": "NUMERICAL_COMPLETE",
            "fck_mpa": 35.0,
            "fcd_mpa": 35.0 / 1.5,
            "ts500_limit_kn": 13440.0,
            "tbdy_seismic_reference_limit_kn": 8960.0,
            "combination_checks": [
                {"combination": STATIC, "status": "WITHIN_LIMIT", "nd_kn": 1200.0},
                {"combination": SPECTRAL, "status": "WITHIN_LIMIT", "nd_kn": 900.0},
            ],
        }],
    }
    pmm = {
        "member_id": "127",
        "status": "NUMERICAL_COMPLETE",
        "analysis_order": "UNVERIFIED",
        "rows": [
            {"combination": STATIC, "object_station_m": 0.0, "nd_kn": 1200.0, "m2_knm": 50.0, "m3_knm": -70.0,
             "utilization": 0.25, "status": "WITHIN_SCENARIO_SURFACE"},
            {"combination": STATIC, "object_station_m": 4.5, "nd_kn": 1000.0, "m2_knm": -45.0, "m3_knm": 65.0,
             "utilization": 0.22, "status": "WITHIN_SCENARIO_SURFACE"},
        ],
        "section_evidence": {
            "reinforcement_role": "ETABS_DESIGN_TEMPLATE",
            "t2_mm": 800.0, "t3_mm": 800.0,
            "bar_count": 12, "longitudinal_bar_area_mm2": 314.0, "longitudinal_bar_diameter_mm": 20.0,
            "fck_mpa": 35.0, "fcd_mpa": 35.0 / 1.5, "fyd_mpa": 420.0 / 1.15,
        },
    }
    return payload, geometry, extra, axial, pmm


class R10LiveUnitTests(unittest.TestCase):
    def test_r10_stage_is_bound_to_verified_94_node_ids(self):
        coverage = dag_coverage()
        self.assertEqual(coverage["unknown_node_ids"], [])
        self.assertIn("column-r10", {s.key for s in STAGES})
        for node_id in ("JOINT_TOPOLOGY_CHECK", "JOINT_SHEAR", "SCWB", "COLUMN_SHEAR", "COLUMN_SHEAR_REBAR"):
            self.assertIn("column-r10", coverage["bindings"][node_id])

    def test_corner_joint_unenclosed_limit_axis_angle_scwb_and_transverse(self):
        payload, geometry, extra, axial, pmm = _base_live_payload(axis_angle="90", enclosed_j=False)
        r10 = project_column_r10_live(payload, geometry, axial, pmm, extra)
        gates = project_column_gates(payload, axial, pmm, local_axis_angle_deg=r10["local_axis_angle_deg"])

        self.assertEqual(r10["local_axis_angle_deg"], 90.0)
        self.assertEqual(gates["local_axis_angle_deg"], 90.0)
        self.assertNotIn("LOCAL_AXIS_ANGLE_NOT_CAPTURED_LIVE", {g["code"] for g in gates["open_gates"]})
        self.assertEqual(len(r10["global_moment_projections"]), 2)

        end_i, end_j = r10["member_joint_ends"]
        self.assertEqual(end_i["status"], "NO_RECORDED_BEAM_AT_NODE")
        self.assertEqual(end_j["enclosure_scenario"], "UNENCLOSED")
        expected_lim = 1.0 * 800.0 * 800.0 * math.sqrt(35.0) / 1000.0
        for axis_entry in end_j["axes"]:
            self.assertAlmostEqual(axis_entry["calculation"]["geometric_limit_kn"], expected_lim, places=6)

        # SCWB never guesses beam steel
        self.assertEqual(len(r10["scwb_joints"]), 2)
        for j in r10["scwb_joints"]:
            self.assertEqual(j["status"], "BEAM_CAPACITY_NOT_BOUND")
            self.assertIsNone(j["scwb_ratio"])
            self.assertGreater(j["sampled_minimum_column_sum_knm"], 0.0)
            self.assertEqual(j["formal_compliance"], "NOT_PROVEN")

        # Transverse confinement and shear refs computed; never PASS
        ts = r10["column_transverse_and_shear"]
        self.assertEqual(ts["status"], "SCENARIO_REFERENCES_CALCULATED")
        self.assertEqual(ts["shear_station_count"], 2)
        self.assertEqual(ts["fywk_mpa"], 420.0)
        self.assertAlmostEqual(ts["confinement"]["V2"]["eq71_b_mm2"], 0.075 * 150.0 * 710.0 * 35.0 / 420.0, places=4)
        self.assertEqual(ts["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(r10["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(r10["engineering_release"], "NOT_READY")

    def test_enclosed_and_narrow_beam_enclosure_classification(self):
        payload, geometry, extra, axial, pmm = _base_live_payload(enclosed_j=True, narrow_beam=False)
        r10_enc = project_column_r10_live(payload, geometry, axial, pmm, extra)
        self.assertEqual(r10_enc["enclosure_counts"], {"ENCLOSED": 1})
        self.assertEqual(r10_enc["narrow_beam_joint_count"], 0)
        end_j_enc = r10_enc["member_joint_ends"][1]
        self.assertAlmostEqual(end_j_enc["axes"][0]["calculation"]["geometric_limit_kn"],
                               1.7 * 800.0 * 800.0 * math.sqrt(35.0) / 1000.0, places=6)

        # B40x70 on 800 mm column => ratio 0.50 < 0.75 => narrow beam downgrades to UNENCLOSED
        payload_n, geom_n, extra_n, axial_n, pmm_n = _base_live_payload(enclosed_j=True, narrow_beam=True)
        r10_narrow = project_column_r10_live(payload_n, geom_n, axial_n, pmm_n, extra_n)
        self.assertEqual(r10_narrow["enclosure_counts"], {"UNENCLOSED": 1})
        self.assertEqual(r10_narrow["narrow_beam_joint_count"], 1)
        self.assertEqual(r10_narrow["member_joint_ends"][1]["narrow_faces"], ["3-"])

    def test_missing_axis_angle_keeps_open_gate(self):
        payload, geometry, extra, axial, pmm = _base_live_payload()
        del payload["geometry_capture"]["tables"]["FRAME_ASSIGNMENTS"]["rows"][0]
        self.assertIsNone(member_local_axis_angle_deg(payload, "127"))
        gates = project_column_gates(payload, axial, pmm)
        self.assertIsNone(gates["local_axis_angle_deg"])
        self.assertIn("LOCAL_AXIS_ANGLE_NOT_CAPTURED_LIVE", {g["code"] for g in gates["open_gates"]})

    def test_capture_r10_sources_handles_missing_tables_without_crashing(self):
        class _FakeDb:
            def GetTableForDisplayArray(self, key, *_):
                if "Reinforcing" in key:
                    return (key, ["Name"], ["Name"], 0, [], 0)
                raise RuntimeError("TABLE_UNAVAILABLE")

            def GetAllFieldsInTable(self, _):
                return (1, 1, ["Name"], ["Name"], [""], [""], [False], 0)

        fake_sap = SimpleNamespace(
            GetModelIsLocked=lambda: True,
            GetPresentUnits=lambda: 6,
            DatabaseTables=_FakeDb(),
        )
        res = capture_r10_sources(fake_sap)
        self.assertEqual(res["schema"], "tbdy.next.r10-live-source.v1")
        self.assertEqual(res["table_reads"]["Frame Section Property Definitions - Concrete Beam Reinforcing"]["status"], "EMPTY_TABLE")
        self.assertEqual(res["table_reads"]["Frame Assignments - End Length Offsets"]["status"], "CAPTURE_ERROR")
        self.assertIn("TABLE_UNAVAILABLE", res["table_reads"]["Frame Assignments - End Length Offsets"]["error"])


def _add_field(table: dict, name: str) -> None:
    table["fields"].append(name)
    meta = table.setdefault("field_metadata", {})
    if isinstance(meta.get("field_keys"), list):
        meta["field_keys"].append(name)
    if isinstance(meta.get("units_by_field"), dict):
        meta["units_by_field"][name] = ""


class R10WebAndReportIntegration(live.ColumnAxialIntegration):
    def capture(self, case, *, column_axial_request=None):
        data = super().capture(case, column_axial_request=column_axial_request)
        tables = data["geometry_capture"]["tables"]
        _add_field(tables["FRAME_ASSIGNMENTS"], "AxisAngle")
        for row in tables["FRAME_ASSIGNMENTS"]["rows"]:
            row["AxisAngle"] = "90" if row["UniqueName"] in ("C1", "C2") else "0"
        col_pts = {"C1": ("P0", "P1"), "C2": ("P10", "P11")}
        for col in ("UniquePtI", "UniquePtJ"):
            _add_field(tables["COLUMN_CONNECTIVITY"], col)
            _add_field(tables["BEAM_CONNECTIVITY"], col)
        for row in tables["COLUMN_CONNECTIVITY"]["rows"]:
            pi, pj = col_pts[row["UniqueName"]]
            row["UniquePtI"], row["UniquePtJ"] = pi, pj
        beam_pts = {"B1": ("P1", "P2"), "B2": ("P1", "P3"), "B3": ("P11", "P12")}
        for row in tables["BEAM_CONNECTIVITY"]["rows"]:
            pi, pj = beam_pts[row["UniqueName"]]
            row["UniquePtI"], row["UniquePtJ"] = pi, pj
        data.setdefault("vs05_delta_source", {"table_reads": {}})["table_reads"]["Point Object Connectivity"] = {
            "fields": ["UniqueName", "X", "Y", "Z"],
            "rows": [
                {"UniqueName": "P0", "X": "0.0", "Y": "0.0", "Z": "0.0"},
                {"UniqueName": "P1", "X": "0.0", "Y": "0.0", "Z": "3.0"},
                {"UniqueName": "P2", "X": "5.0", "Y": "0.0", "Z": "3.0"},
                {"UniqueName": "P3", "X": "0.0", "Y": "5.0", "Z": "3.0"},
                {"UniqueName": "P10", "X": "5.0", "Y": "0.0", "Z": "0.0"},
                {"UniqueName": "P11", "X": "5.0", "Y": "0.0", "Z": "3.0"},
                {"UniqueName": "P12", "X": "10.0", "Y": "0.0", "Z": "3.0"},
            ],
        }
        return data

    def pmm_query(self) -> dict:
        query = self.query("ASSIGNED_DESIGN")
        query.update(check="column-pmm", member="C1",
                     assignments=json.dumps({"gravity": [STATIC], "ductile": [SPECTRAL]}))
        return query

    def test_live_vs04_pipeline_export_and_html_report_include_r10(self):
        ack = self.post(self.pmm_query())
        run_id = ack["run_id"]
        self.assertEqual(ack["r10_live"]["member_id"], "C1")
        self.assertEqual(ack["r10_live"]["local_axis_angle_deg"], 90.0)
        self.assertEqual(ack["r10_live"]["joint_end_count"], 4)
        self.assertEqual(ack["r10_live"]["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(ack["column_gates"]["local_axis_angle_deg"], 90.0)

        report = json.loads(self.get("/api/export-checks?run_id=" + run_id))
        self.assertEqual(report["r10_live"]["local_axis_angle_deg"], 90.0)
        self.assertIn("Column R10", self.get("/report/print?run_id=" + run_id).decode("utf-8"))

        pipeline_body = json.loads(self.get("/api/pipeline"))
        self.assertIn("column-r10", {s["key"] for s in pipeline_body["stages"]})
        self.assertEqual(pipeline_body["dag_coverage"]["unknown_node_ids"], [])


for _name in [n for n in dir(live.ColumnAxialIntegration) if n.startswith("test_")]:
    setattr(R10WebAndReportIntegration, _name, None)


if __name__ == "__main__":
    unittest.main()
