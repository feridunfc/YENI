"""Independent reference arithmetic for live joint adapter invariants.

These small synthetic inputs test the existing R13 owner. They are not an ETABS
source replay, a physical-face approval or a complete engineering acceptance.
"""
from copy import deepcopy
import math
import unittest

from tbdy_next.column_engine.source_bank import FIELDS
from tbdy_next.engineering.column_r10_live import _attach_r13_joint_shear_and_transverse
from tbdy_next.engineering.column_r14_closure import _evaluate_single_r14_column


class JointAdapterInvariantTests(unittest.TestCase):
    def setUp(self):
        axes = [[0., 0., 1.], [1., 0., 0.], [0., 1., 0.]]
        self.points = {"P0": [0., 0., 0.], "J": [0., 0., 3.], "P2": [0., 0., 6.]}
        self.frames = {
            "L": {"frame_id": "L", "point_i": "P0", "point_j": "J", "axes_global": deepcopy(axes)},
            "U": {"frame_id": "U", "point_i": "J", "point_j": "P2", "axes_global": deepcopy(axes)},
        }
        self.adjacency = {"J": [
            {"type": "Column", "frame_id": "L", "end": "J"},
            {"type": "Column", "frame_id": "U", "end": "I"},
        ]}
        self.limit_kn = 400 * 400 * math.sqrt(35) / 1000
        self.end_row = {
            "status": "JOINT_GEOMETRIC_REFERENCES_CALCULATED", "member_id": "U",
            "point_id": "J", "end": "I", "enclosure_scenario": "UNENCLOSED",
            "faces": {"2+": {"frame_id": "B+", "native_end": "I"},
                      "2-": {"frame_id": "B-", "native_end": "I"}},
            "axes": [{"axis": "V2", "calculation": {"geometric_limit_kn": self.limit_kn}}],
        }
        self.beams = {
            name: {"horizontal_local2_up": True, "fyk_mpa": 420., "ends": {"I": {"engineer_selection": {
                "status": "BEAM_SELECTED_CALCULATED", "area_top_mm2": 1000., "area_bottom_mm2": 1000.,
            }}}} for name in ("B+", "B-")
        }
        self.selections = {"L": {"selected": {"selected_transverse": {
            "confinement_spacing_mm": 100., "tie_diameter_mm": 10.,
            "confinement_v2": {"high_axial_required_ash_mm2": 300., "low_axial_required_ash_mm2": 300., "ash_mm2": 400.},
            "confinement_v3": {"high_axial_required_ash_mm2": 1000., "low_axial_required_ash_mm2": 1000., "ash_mm2": 200.},
        }}}}
        self.axial = {"combination_plan": {
            "source": "ASSIGNED_DESIGN", "design_assignment": {"groups": {"capacity": ["E1", "E2"]}},
            "combinations": [{"name": c, "force_semantics": "STATIC_SIGNED_VECTOR"} for c in ("E1", "E2")],
        }}

    @staticmethod
    def force_rows(uid, shear_e2=200.):
        return [(uid, station, uid + "-1", station, combo, "Single Value", 0., -100., shear, 0., 0., 0., 0.)
                for combo, shear in (("E1", 200.), ("E2", shear_e2)) for station in (0., 1.5, 3.)]

    def calculate(self, *, shear_e2=200., force_rows=None):
        rows = force_rows if force_rows is not None else {uid: self.force_rows(uid, shear_e2) for uid in ("L", "U")}
        rowsets = {uid: {"NumberResults": len(values), "pRetVal": 0,
                         **{name: [row[i] for row in values] for i, name in enumerate(FIELDS)}}
                   for uid, values in rows.items()}
        end = deepcopy(self.end_row)
        _attach_r13_joint_shear_and_transverse(
            end_rows=[end], frames=self.frames, points=self.points, adjacency=self.adjacency,
            beam_by_id=self.beams, force_rowsets=rowsets, axial=self.axial,
            eng_col_selections=self.selections, transverse_by_uid={"L": {"status": "CALCULATED"}},
            beam_sel_active=True, col_sel_active=True,
        )
        return end["axes"][0]

    def test_zero_small_and_threshold_shears_remain_in_governing_population(self):
        prior_demand = math.inf
        for shear in (0., .5, 1., 1.000000001, 150., 200.):
            with self.subTest(shear_kn=shear):
                result = self.calculate(shear_e2=shear)["joint_shear_ve"]
                expected = 1.25 * 420 * (1000 + 1000) / 1000 - min(200., shear)
                self.assertAlmostEqual(result["governing_ve_kn"], expected, places=9)
                self.assertEqual(result["within_geometric_limit"], expected <= self.limit_kn)
                self.assertLessEqual(result["governing_ve_kn"], prior_demand)
                self.assertTrue(result["column_shear_scope_complete"])
                self.assertEqual([c["combination"] for c in result["column_shear_cases"]], ["E1", "E2"])
                self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
                prior_demand = result["governing_ve_kn"]

    def test_complete_valid_shear_allows_positive_reference_deduction(self):
        result = self.calculate()["joint_shear_ve"]
        self.assertEqual(result["v_kol_used_kn"], 200.)
        self.assertEqual(result["governing_ve_kn"], 850.)
        self.assertTrue(result["within_geometric_limit"])
        self.assertEqual(result["upper_column_ids"], ["U"])
        self.assertEqual(result["lower_column_ids"], ["L"])

    def test_missing_expected_combination_uses_zero_bound_and_retains_case(self):
        rows = {uid: [r for r in self.force_rows(uid) if r[4] != "E2"] for uid in ("L", "U")}
        result = self.calculate(force_rows=rows)["joint_shear_ve"]
        self.assertEqual(result["v_kol_used_kn"], 0.)
        self.assertEqual(result["governing_ve_kn"], 1050.)
        self.assertFalse(result["within_geometric_limit"])
        self.assertFalse(result["column_shear_scope_complete"])
        self.assertEqual(result["missing_column_shear_combinations"], ["E2"])
        self.assertEqual(result["column_shear_cases"][1]["missing_column_ids"], ["L", "U"])

    def test_missing_case_may_pass_the_explicit_conditional_upper_bound(self):
        for beam in self.beams.values():
            beam["ends"]["I"]["engineer_selection"].update(area_top_mm2=500., area_bottom_mm2=500.)
        result = self.calculate(force_rows={"L": self.force_rows("L")})["joint_shear_ve"]
        self.assertEqual(result["governing_ve_kn"], 525.)
        self.assertTrue(result["within_geometric_limit"])
        self.assertEqual(result["v_kol_basis"], "CONSERVATIVE_ZERO_VKOL_INCOMPLETE_SEISMIC_SHEAR")
        self.assertIn("NONNEGATIVE_DEDUCTION", result["v_kol_applicability"])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")

    def test_assigned_unclassified_or_spectral_case_is_not_dropped(self):
        for semantics in (None, "SCALAR_COMPONENT_ENVELOPE"):
            with self.subTest(semantics=semantics):
                self.axial["combination_plan"]["combinations"] = [{"name": "E1", "force_semantics": "STATIC_SIGNED_VECTOR"}]
                if semantics:
                    self.axial["combination_plan"]["combinations"].append({"name": "E2", "force_semantics": semantics})
                result = self.calculate()["joint_shear_ve"]
                self.assertEqual(result["v_kol_used_kn"], 0.)
                self.assertEqual(result["missing_column_shear_combinations"], ["E2"])
                self.assertEqual(result["column_shear_cases"][1]["status"], "STATIC_SIGNED_COMBINATION_NOT_BOUND")

    def test_missing_physical_end_cannot_be_replaced_by_interior_row(self):
        for uid, endpoint in (("U", 0.), ("L", 3.)):
            with self.subTest(member=uid):
                rows = {c: self.force_rows(c) for c in ("L", "U")}
                rows[uid] = [r for r in rows[uid] if not (r[4] == "E2" and r[1] == endpoint)]
                result = self.calculate(force_rows=rows)["joint_shear_ve"]
                self.assertEqual(result["v_kol_used_kn"], 0.)
                self.assertEqual(result["missing_column_shear_combinations"], ["E2"])

    def test_ambiguous_element_side_and_nonstatic_rows_do_not_supply_deduction(self):
        for mode in ("ambiguous_element_side", "nonstatic_step", "unapproved_offset"):
            with self.subTest(mode=mode):
                rows = {c: self.force_rows(c) for c in ("L", "U")}
                index = next(i for i, r in enumerate(rows["U"]) if r[4] == "E2" and r[1] == 0.)
                row = list(rows["U"][index])
                if mode == "ambiguous_element_side":
                    row[2] = "U-OTHER"
                    rows["U"].append(tuple(row))
                else:
                    if mode == "nonstatic_step":
                        row[5] = "Max"
                    else:
                        row[1] = row[3] = .2
                    rows["U"][index] = tuple(row)
                result = self.calculate(force_rows=rows)["joint_shear_ve"]
                self.assertEqual(result["v_kol_used_kn"], 0.)
                self.assertEqual(result["missing_column_shear_combinations"], ["E2"])

    def test_rotated_unequal_lower_column_maps_confinement_by_physical_axis(self):
        self.frames["L"]["axes_global"] = [[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]]
        result = self.calculate()["joint_transverse_7_5_2_3"]
        self.assertEqual(result["target_axis"], "V2")
        self.assertEqual(result["global_direction"], [1., 0., 0.])
        self.assertEqual(result["lower_axis"], "V3")
        self.assertEqual(result["axis_mapping_status"], "PHYSICAL_AXIS_BOUND")
        self.assertEqual(result["required_ash_at_joint_spacing_mm2"], .6 * 1000.)
        self.assertEqual(result["proposed_ash_mm2"], 200.)
        self.assertEqual(result["required_to_proposed_ratio"], 3.)
        self.assertEqual(result["max_whole_spacing_for_selected_tie_mm"], 33)
        self.assertFalse(result["all_references_met"])

    def test_native_endpoint_reversal_preserves_physical_joint_calculations(self):
        for uid in ("L", "U"):
            frame = self.frames[uid]
            frame["point_i"], frame["point_j"] = frame["point_j"], frame["point_i"]
            frame["axes_global"] = [[0., 0., -1.], [1., 0., 0.], [0., -1., 0.]]
            self.adjacency["J"] = [{**item, "end": ("I" if item["end"] == "J" else "J")}
                                    if item["frame_id"] == uid else item for item in self.adjacency["J"]]
            if uid == "U":
                self.end_row["end"] = "J"
            result = self.calculate()
            self.assertEqual(result["joint_shear_ve"]["v_kol_used_kn"], 200.)
            self.assertEqual(result["joint_shear_ve"]["lower_column_ids"], ["L"])
            ties = result["joint_transverse_7_5_2_3"]
            self.assertEqual(ties["lower_column_id"], "L")
            self.assertEqual(ties["lower_axis"], "V2")
            self.assertAlmostEqual(ties["required_to_proposed_ratio"], .45)
            self.assertTrue(ties["all_references_met"])

    def test_oblique_lower_axis_has_explicit_unbound_result(self):
        a = math.sqrt(.5)
        self.frames["L"]["axes_global"] = [[0., 0., 1.], [a, a, 0.], [-a, a, 0.]]
        result = self.calculate()["joint_transverse_7_5_2_3"]
        self.assertEqual(result["reason"], "JOINT_LOWER_AXIS_MAPPING_NOT_BOUND")
        self.assertEqual(result["axis_mapping_status"], "NOT_BOUND")
        self.assertIsNone(result["all_references_met"])

    def test_missing_coordinate_and_branched_topology_cannot_use_native_end_fallback(self):
        del self.points["P0"]
        result = self.calculate()
        self.assertEqual(result["joint_shear_ve"]["v_kol_used_kn"], 0.)
        self.assertTrue(result["joint_shear_ve"]["column_topology_issues"])
        self.assertIsNone(result["joint_transverse_7_5_2_3"]["all_references_met"])
        self.points["P0"] = [0., 0., 0.]
        self.frames["L2"] = {**self.frames["L"], "frame_id": "L2"}
        self.adjacency["J"].append({"type": "Column", "frame_id": "L2", "end": "J"})
        result = self.calculate()
        self.assertEqual(result["joint_shear_ve"]["v_kol_used_kn"], 0.)
        self.assertIn("JOINT_UNIQUE_UPPER_LOWER_COLUMNS_NOT_BOUND", result["joint_shear_ve"]["column_topology_issues"])
        self.assertIsNone(result["joint_transverse_7_5_2_3"]["all_references_met"])

    def test_roof_boundary_still_uses_zero_without_requiring_shear_rows(self):
        del self.frames["U"]
        self.adjacency["J"] = [self.adjacency["J"][0]]
        self.end_row.update(member_id="L", end="J")
        result = self.calculate(force_rows={})
        self.assertEqual(result["joint_shear_ve"]["v_kol_basis"], "ROOF_JOINT_NO_UPPER_COLUMN_VKOL_ZERO")
        self.assertEqual(result["joint_shear_ve"]["governing_ve_kn"], 1050.)
        self.assertEqual(result["joint_transverse_7_5_2_3"]["lower_column_id"], "L")

    def closure(self, axis_result):
        end = deepcopy(self.end_row)
        end["axes"] = [axis_result]
        return _evaluate_single_r14_column(
            uid=end["member_id"], axial=self.axial, axial_col={}, pmm_col=None,
            r08_global=None, r08_local_col=None, beam_by_id={},
            r10_det={"member_joint_ends": [end]}, story_alpha=None,
        )

    def test_r14_missing_case_bound_exceedance_requires_refinement_not_proven_failure(self):
        result = self.closure(self.calculate(force_rows={"L": self.force_rows("L")}))
        self.assertEqual(result["status"], "R14_PARTIAL_OR_UNBOUND")
        self.assertEqual(result["normative_failures"], [])
        self.assertIn("JOINT_SHEAR_CONSERVATIVE_BOUND_EXCEEDS_LIMIT_REFINEMENT_REQUIRED:I:V2", result["open_gates"])
        bound = result["pillars"]["joint_shear_and_transverse"]["conservative_bound_exceedances"][0]
        self.assertEqual(bound["governing_ve_kn"], 1050.)
        self.assertAlmostEqual(bound["utilization"], 1050. / self.limit_kn)
        self.assertEqual(bound["missing_column_shear_combinations"], ["E1", "E2"])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")

    def test_r14_missing_topology_bound_retains_reason_without_proven_failure(self):
        del self.points["P0"]
        result = self.closure(self.calculate())
        self.assertEqual(result["normative_failures"], [])
        bound = result["pillars"]["joint_shear_and_transverse"]["conservative_bound_exceedances"][0]
        self.assertEqual(bound["v_kol_basis"], "CONSERVATIVE_ZERO_VKOL_COLUMN_TOPOLOGY_UNBOUND")
        self.assertTrue(bound["column_topology_issues"])
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_r14_complete_shear_exceedance_including_observed_zero_remains_failure(self):
        for shear in (0., .5):
            with self.subTest(shear_kn=shear):
                result = self.closure(self.calculate(shear_e2=shear))
                self.assertEqual(result["status"], "R14_FAILED_NORMATIVE_CHECK")
                self.assertIn("JOINT_SHEAR_VJ_EXCEEDS_7_5_2_2_LIMIT:I:V2", result["normative_failures"])
                self.assertEqual(result["pillars"]["joint_shear_and_transverse"]["conservative_bound_exceedances"], [])

    def test_r14_defined_roof_zero_exceedance_remains_failure(self):
        del self.frames["U"]
        self.adjacency["J"] = [self.adjacency["J"][0]]
        self.end_row.update(member_id="L", end="J")
        result = self.closure(self.calculate(force_rows={}))
        self.assertEqual(result["status"], "R14_FAILED_NORMATIVE_CHECK")
        self.assertIn("JOINT_SHEAR_VJ_EXCEEDS_7_5_2_2_LIMIT:J:V2", result["normative_failures"])
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_r14_passing_conditional_zero_bound_preserves_numeric_success_only(self):
        for beam in self.beams.values():
            beam["ends"]["I"]["engineer_selection"].update(area_top_mm2=500., area_bottom_mm2=500.)
        result = self.closure(self.calculate(force_rows={}))
        joint = result["pillars"]["joint_shear_and_transverse"]
        self.assertAlmostEqual(joint["max_vj_utilization"], 525. / self.limit_kn)
        self.assertEqual(joint["conservative_bound_exceedances"], [])
        self.assertEqual(result["normative_failures"], [])
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertEqual(result["engineering_release"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
