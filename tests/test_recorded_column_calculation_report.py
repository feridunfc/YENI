"""Saved calculation sheets must show their governing inputs without recalculation.

The numbers below are explicit presentation fixtures, not independent structural
solutions or a replay of the private C29 model.
"""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tbdy_next.reporting import (
    _column_r10_html, _column_r14_r15_html, build_complete_report, build_printable_html,
)


def recorded_column(uid="C29", combination="Grav_Ult"):
    return {
        "member_id": uid, "story": "+9.00", "section": "S800",
        "status": "R14_PARTIAL", "normative_failures": [],
        "pillars": {"second_order_selected_pmm": {
            "selection_status": "ENGINEER_COLUMN_SELECTED_NOT_PROVEN",
            "longitudinal_label": "32Φ16", "transverse_label": "Φ10/90",
            "magnified_pmm_status": "MAGNIFIED_PMM_WITHIN_CAPACITY_NOT_PROVEN",
            "max_magnified_utilization": .3049,
            "governing_static_station": {
                "combination": combination, "object_station_m": 3.25,
                "analysis_element_id": uid + "-E2", "element_station_m": 1.25,
                "step_type": "Single Value", "step_number": 0., "nd_kn": 1025.20,
                "first_order_m2_knm": 321.45, "first_order_m3_knm": -83.21,
                "first_order_m2_design_knm": 321.45, "first_order_m3_design_knm": -83.21,
                "beta_m2": 1.11, "beta_m3": 1.12, "global_beta_ii_applied": 1.03,
                "magnified_m2_design_knm": 367.52, "magnified_m3_design_knm": -95.87,
                "moment_demand_knm": 379.73, "radial_capacity_knm": 1245.60,
                "moment_reserve_knm": 865.87, "utilization": .3049,
                "status": "WITHIN_SCENARIO_SURFACE",
            },
        }},
    }


def recorded_joint(uid="C29", point="ROOF-29"):
    return {
        "scope": "SINGLE_COLUMN", "member_id": uid, "local_axis_angle_deg": 90.,
        "formal_compliance": "NOT_PROVEN", "scwb_joints": [],
        "engineer_column_selection": {"selected": {"label": "32Φ16"}},
        "member_joint_ends": [{
            "member_id": uid, "point_id": point, "end": "J", "story": "+9.00",
            "section_name": "S800", "status": "JOINT_GEOMETRIC_REFERENCES_CALCULATED",
            "enclosure_scenario": "UNENCLOSED", "axes": [{
                "axis": "V2", "status": "GEOMETRIC_REFERENCE_ONLY",
                "calculation": {"b_mm": 800., "h_mm": 800., "bj_mm": 800.,
                    "fck_mpa": 35., "geometric_limit_kn": 3786.29,
                    "centered_sections_assumed": True, "physical_geometry_proven": False},
                "joint_shear_ve": {
                    "target_axis": "V2", "global_direction": [0., 1., 0.],
                    "sway_a_tension_kn": 1786.78, "sway_b_tension_kn": 1432.15,
                    "v_kol_used_kn": 0., "v_kol_basis": "ROOF_JOINT_NO_UPPER_COLUMN_VKOL_ZERO",
                    "sway_a_ve_kn": 1786.78, "sway_b_ve_kn": 1432.15,
                    "governing_ve_kn": 1786.78, "geometric_limit_kn": 3786.29,
                    "utilization": .4719, "within_geometric_limit": True,
                    "status": "JOINT_SHEAR_VE_CALCULATED_NOT_PROVEN", "formal_compliance": "NOT_PROVEN",
                    "faces": {"2+": {"present": True, "frame_id": "B29", "native_end": "I",
                        "fyk_mpa": 420., "as_top_mm2": 2000., "as_bot_mm2": 1800.,
                        "t_top_kn": 1050., "t_bot_kn": 945.}},
                },
                "joint_transverse_7_5_2_3": {
                    "target_axis": "V2", "global_direction": [0., 1., 0.],
                    "lower_column_id": uid, "lower_axis": "V3", "axis_mapping_status": "PHYSICAL_AXIS_BOUND",
                    "axial_branch": "LOW_AXIAL_LE_0_2_AC_FCK", "lower_required_ash_mm2": 335.48,
                    "lower_spacing_mm": 90., "fraction_of_lower_required_density": .6,
                    "required_ash_per_s_mm2_per_mm": 2.2365,
                    "required_ash_at_joint_spacing_mm2": 201.29, "proposed_ash_mm2": 392.70,
                    "tie_diameter_mm": 10., "joint_spacing_mm": 90., "spacing_limit_mm": 100,
                    "max_whole_spacing_for_selected_tie_mm": 100,
                    "required_to_proposed_ratio": .5126, "all_references_met": True,
                },
            }],
        }],
    }


def all_columns(columns):
    return {"scope": "ALL_COLUMNS", "columns": columns,
            "expected_column_count": len(columns), "evaluated_column_count": len(columns),
            "numerically_closed_count": 0, "partial_or_unbound_count": len(columns),
            "normative_fail_count": 0, "status": "R15_PARTIAL", "formal_compliance": "NOT_PROVEN"}


def all_joints(members):
    # The real all-column R10 shape keeps detailed ends only inside per_member.
    return {"scope": "ALL_COLUMNS", "member_id": "ALL", "member_joint_ends": [],
            "per_member": {member["member_id"]: member for member in members},
            "formal_compliance": "NOT_PROVEN"}


class RecordedColumnCalculationReportTests(unittest.TestCase):
    def test_static_cut_force_and_capacity_are_visible_in_both_scopes(self):
        for record in (recorded_column(), all_columns([recorded_column(), recorded_column("C30", "Other_G")])):
            with self.subTest(scope=record.get("scope", "SINGLE_COLUMN")):
                html = _column_r14_r15_html(record)
                for text in ("Grav_Ult", "C29-E2", "3.25", "1.25", "1025.2", "321.45", "-83.21",
                             "1.11", "1.12", "1.03", "367.52", "-95.87", "379.73", "1245.6", "865.87",
                             "32Φ16", "Φ10/90", "Single Value", "WITHIN_SCENARIO_SURFACE"):
                    self.assertIn(text, html)
                self.assertIn("Radial capacity at recorded N", html)
                self.assertIn("M2 after eccentricity floor", html)
                self.assertIn("M3 after eccentricity floor", html)
                if record.get("scope") == "ALL_COLUMNS":
                    self.assertIn("C30-E2", html)
                    self.assertIn("Other_G", html)

    def test_changed_governing_station_changes_html_with_same_summary_utilization(self):
        edits = {"combination": "Changed_G", "object_station_m": 2.625,
                 "analysis_element_id": "CHANGED-ELEMENT", "element_station_m": .625,
                 "step_type": "Changed step", "step_number": 4., "nd_kn": 925.,
                 "first_order_m2_design_knm": 322.75, "first_order_m3_design_knm": -84.25,
                 "moment_demand_knm": 410., "radial_capacity_knm": 1400., "moment_reserve_knm": 990.}
        for scope in ("SINGLE_COLUMN", "ALL_COLUMNS"):
            for key, value in edits.items():
                with self.subTest(scope=scope, field=key):
                    before = recorded_column()
                    after = deepcopy(before)
                    after["pillars"]["second_order_selected_pmm"]["governing_static_station"][key] = value
                    wrap = (lambda r: all_columns([r])) if scope == "ALL_COLUMNS" else (lambda r: r)
                    self.assertNotEqual(_column_r14_r15_html(wrap(before)), _column_r14_r15_html(wrap(after)))

    def test_joint_shear_tie_pitch_and_physical_axes_are_visible_in_both_scopes(self):
        for record in (recorded_joint(), all_joints([recorded_joint(), recorded_joint("C30", "ROOF-30")])):
            with self.subTest(scope=record["scope"]):
                html = _column_r10_html(record)
                for text in ("ROOF-29", "C29", "V2", "V3", "PHYSICAL_AXIS_BOUND", "[0.0, 1.0, 0.0]",
                             "1786.78", "1432.15", "3786.29", "201.29", "392.7", "335.48", "2.24",
                             "Maximum whole-mm pitch", "Selected pitch", "B29", "1050", "945",
                             "ROOF_JOINT_NO_UPPER_COLUMN_VKOL_ZERO"):
                    self.assertIn(text, html)
                self.assertNotIn("Beam actual reinforcement and capacity-design Ve remain unbound", html)
                if record["scope"] == "ALL_COLUMNS":
                    self.assertIn("ROOF-30", html)

    def test_changed_joint_detail_changes_html_with_same_summary(self):
        for scope in ("SINGLE_COLUMN", "ALL_COLUMNS"):
            for block, key, value in (
                ("joint_transverse_7_5_2_3", "max_whole_spacing_for_selected_tie_mm", 50),
                ("joint_transverse_7_5_2_3", "required_ash_at_joint_spacing_mm2", 801.29),
                ("joint_transverse_7_5_2_3", "proposed_ash_mm2", 502.7),
                ("joint_transverse_7_5_2_3", "lower_axis", "V2"),
                ("joint_shear_ve", "v_kol_used_kn", .5),
                ("joint_shear_ve", "sway_b_ve_kn", 1787.),
            ):
                with self.subTest(scope=scope, field=key):
                    before, after = recorded_joint(), recorded_joint()
                    after["member_joint_ends"][0]["axes"][0][block][key] = value
                    wrap = (lambda r: all_joints([r])) if scope == "ALL_COLUMNS" else (lambda r: r)
                    self.assertNotEqual(_column_r10_html(wrap(before)), _column_r10_html(wrap(after)))

    def test_missing_legacy_details_remain_missing_and_zero_values_are_preserved(self):
        column = recorded_column()
        column["pillars"]["second_order_selected_pmm"].pop("governing_static_station")
        self.assertIn("Governing static station was not recorded", _column_r14_r15_html(column))
        joint = recorded_joint()
        axis = joint["member_joint_ends"][0]["axes"][0]
        axis.pop("joint_transverse_7_5_2_3")
        self.assertIn("NOT_RECORDED", _column_r10_html(joint))
        self.assertNotIn("PHYSICAL_AXIS_BOUND", _column_r10_html(joint))
        self.assertIn("<td>0</td>", _column_r10_html(joint))
        self.assertIn("joint calculation details were not recorded", _column_r10_html({"member_id": "C1"}))

    def test_new_trace_fields_escape_source_labels_and_diagnostics(self):
        malicious = '<img src=x onerror="alert(1)">'
        column = recorded_column(malicious, malicious)
        column["pillars"]["second_order_selected_pmm"]["longitudinal_label"] = malicious
        joint = recorded_joint(malicious, malicious)
        axis = joint["member_joint_ends"][0]["axes"][0]
        axis["joint_shear_ve"]["reason"] = malicious
        axis["joint_transverse_7_5_2_3"]["reason"] = malicious
        for html in (_column_r14_r15_html(all_columns([column])), _column_r10_html(all_joints([joint]))):
            self.assertNotIn(malicious, html)
            self.assertIn('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;', html)

    def test_unresolved_deduction_cases_and_conditional_basis_remain_visible(self):
        joint = recorded_joint()
        shear = joint["member_joint_ends"][0]["axes"][0]["joint_shear_ve"]
        shear.update(
            v_kol_applicability="Conditional zero deduction; sign and joint mechanism remain unverified.",
            expected_seismic_combinations=["EQ1", "EQ2"],
            missing_column_shear_combinations=["EQ2"], column_shear_scope_complete=False,
            column_topology_issues=["LOWER_COLUMN_NOT_BOUND"],
            column_shear_cases=[
                {"combination": "EQ1", "status": "BOUND", "upper_shear_kn": .5,
                 "lower_shear_kn": .8, "deduction_kn": .5, "missing_column_ids": []},
                {"combination": "EQ2", "status": "COLUMN_SHEAR_UNBOUND", "upper_shear_kn": None,
                 "lower_shear_kn": .8, "deduction_kn": None, "missing_column_ids": ["UPPER-42"]},
            ],
        )
        html = _column_r10_html(all_joints([joint]))
        for text in ("Conditional zero deduction", "EQ2", "COLUMN_SHEAR_UNBOUND", "UPPER-42",
                     "LOWER_COLUMN_NOT_BOUND", "Deduction scope complete", "<td>False</td>"):
            self.assertIn(text, html)

    def test_finalized_export_and_print_only_read_recorded_calculation_details(self):
        from tbdy_next.engineering.pipeline import EnginePipelineRunner
        from tbdy_next.engineering.pipeline_snapshot import record_snapshot
        from tbdy_next.receipts import ReceiptRun
        from test_quick_suite import fake_live_suite

        payload = fake_live_suite("Modal")
        raw = json.dumps(payload).encode("utf-8")
        digest = sha256(raw).hexdigest()

        def seal_presentation_fixture(run, *, input_sha, results, registry):
            # Supply explicit stored result fixtures before the normal seal is
            # created. This verifies presentation/archival behavior, not their
            # structural derivation. Never change an existing sealed receipt.
            results = {**results, "r10_live": all_joints([recorded_joint()]),
                       "r14_closure": all_columns([recorded_column()])}
            return record_snapshot(run, input_sha=input_sha, results=results, registry=registry)

        targets = (
            "tbdy_next.history.evaluate_modal_mass", "tbdy_next.reporting.evaluate_geometry_capture",
            "tbdy_next.engineering.pipeline.derive_report_evidence",
            "tbdy_next.engineering.column_axial.evaluate_column_axial",
            "tbdy_next.engineering.column_pmm.evaluate_column_pmm",
            "tbdy_next.engineering.beam_r10_live.project_beam_r10_live",
            "tbdy_next.engineering.column_r10_live.project_column_r10_live",
            "tbdy_next.engineering.column_live_gates.project_column_gates",
            "tbdy_next.engineering.column_r08_local_live.project_column_r08_local_live",
            "tbdy_next.engineering.column_r14_closure.project_column_r14_and_r15_closure",
            "tbdy_next.column_engine.joint_kernel.joint_transverse_reference",
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = ReceiptRun(root)
            run.archive_input(raw, expected_sha256=digest)
            with patch("tbdy_next.engineering.pipeline_snapshot.record_snapshot", side_effect=seal_presentation_fixture):
                EnginePipelineRunner().run(payload, case="Modal", run=run, input_sha=digest, suite=True)
            before = {path.name: path.read_bytes() for path in run.root.iterdir() if path.is_file()}
            with ExitStack() as stack:
                for target in targets:
                    stack.enter_context(patch(target, side_effect=AssertionError("REPORT_MUST_NOT_CALCULATE")))
                report = build_complete_report(root, run.root.name)
                html = build_printable_html(report)
                self.assertEqual(html, build_printable_html(build_complete_report(root, run.root.name)))
            self.assertTrue(report["design_stage_provenance"]["full_report_projection_only"])
            for text in ("C29-E2", "Grav_Ult", "ROOF-29", "1245.6", "Maximum whole-mm pitch", "201.29"):
                self.assertIn(text, html)
            self.assertEqual(before, {path.name: path.read_bytes() for path in run.root.iterdir() if path.is_file()})


if __name__ == "__main__":
    unittest.main()
