"""Actual-source premises for an explicitly adopted self-weight Nmax surrogate.

The native-shaped fixtures are synthetic. No ETABS execution or engineering
acceptance is asserted, and the ordinary geometry, axial and PMM owners run.
"""
from copy import deepcopy
import json
import unittest

from tbdy_next.column_engine.native_archive import digest
from tbdy_next.engineering.column_axial import evaluate_column_axial
from tbdy_next.engineering.column_axial_balance import project_self_weight_nmax_idealization
from tbdy_next.engineering.column_clear_length import WALL_CONNECTIVITY, WALL_PROPERTIES, project_column_clear_lengths
from tbdy_next.engineering.column_pmm import (
    bind_configured_output_cuts, bind_pmm_mesh_source, evaluate_column_pmm,
)
from tbdy_next.engineering.column_pmm_section import MECHANICAL
from tbdy_next.engineering.column_r10_live import _build_frame_catalog
from tbdy_next.engineering.design_scenario import _digest, create_design_scenario
from tbdy_next.engineering.second_order_basis import resolve_member_second_order_basis
from tbdy_next.etabs_geometry import AREA_ELEMENTS, AREA_INSERTION
from tbdy_next.next_checks import evaluate_next_capture
from tbdy_next.quick_checks import evaluate_geometry_capture
from variable_axial_slice_fixture import bind_source, source_and_request
from vertical_slice_fixture import table


def actual_owner_inputs(*, data=None, request=None, uid="C1"):
    """Construct the small real-owner input context, without successful stage fakes."""
    if data is None:
        raw, request = source_and_request()
    else:
        raw, request = bind_source(data, request)
    source = json.loads(create_design_scenario(raw, request))
    geometry = evaluate_geometry_capture(source["geometry_capture"])
    extra = evaluate_next_capture(source["next_capture"], source["geometry_capture"])
    axial = evaluate_column_axial(source, geometry, extra)
    frames, _, graph = _build_frame_catalog(source)
    mesh = bind_pmm_mesh_source(source, {name: frame["story"] for name, frame in frames.items()
                                        if frame["type"] == "Column"})
    grids = bind_configured_output_cuts(source, mesh["members"])
    result = evaluate_column_pmm(source, geometry, axial, mesh_members=mesh["members"], configured_cuts=grids)
    pmm = next(member for member in result["members"] if member["member_id"] == uid)
    physical = project_column_clear_lengths(source, frames, graph["adjacency"], [uid],
        {"analysis_mesh": mesh, "configured_output_cuts": grids})
    length = (physical or {}).get("per_member", {}).get(uid, {})
    basis = resolve_member_second_order_basis(source, uid, [row["name"] for row in pmm["combinations"]])
    return {"source": source, "pmm": pmm, "length": length, "frame_length": 3., "adopted_basis": basis}


def source_inputs():
    raw, request = source_and_request()
    return json.loads(raw), request


def delete_force_row(rowset, index):
    for name, values in rowset.items():
        if isinstance(values, list):
            values.pop(index)
    rowset["NumberResults"] -= 1


class SelfWeightNmaxSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = actual_owner_inputs()

    def assert_rejected(self, result, reason):
        self.assertEqual(result["status"], "SELF_WEIGHT_NMAX_INPUTS_REJECTED", result)
        self.assertTrue(any(reason in item for item in result["reasons"]), result["reasons"])
        self.assertFalse(result["conservative_bound_proven"])
        self.assertFalse(result["original_constant_axial_clause_satisfied"])
        self.assertEqual(result["engineering_approval"], "NOT_GRANTED")

    def test_source_derived_nmax_and_full_cuts_remain_explicitly_unapproved(self):
        before = _digest(self.inputs)
        result = project_self_weight_nmax_idealization(**self.inputs)
        self.assertEqual(result["status"], "SELF_WEIGHT_NMAX_INPUTS_ELIGIBLE", result)
        self.assertEqual(len(result["combinations"]), 5)
        for case in result["combinations"].values():
            # Independently specified 0.64 m2 * 25 kN/m3 * 2.5 m = 40 kN.
            self.assertEqual((case["nmin_kn"], case["nmax_kn"]), (2500., 2540.))
            self.assertEqual([cut["nd_kn"] for cut in case["cuts"]], [2540., 2520., 2500.])
            self.assertEqual((case["expected_cut_count"], case["evaluated_cut_count"]), (3, 3))
            self.assertTrue(all(cut["analysis_element_id"] == "C1-elm" for cut in case["cuts"]))
            self.assertTrue(all(cut["superposition_residual_kn"] == 0 for cut in case["cuts"]))
        self.assertEqual(result["evidence_sha256"], _digest({key: value for key, value in result.items()
                                                           if key != "evidence_sha256"}))
        self.assertFalse(result["conservative_bound_proven"])
        self.assertFalse(result["original_constant_axial_clause_satisfied"])
        self.assertEqual(result["engineering_approval"], "NOT_GRANTED")
        self.assertEqual(_digest(self.inputs), before)

    def test_omitted_variable_combination_cannot_be_qualified_by_other_complete_cases(self):
        inputs = deepcopy(self.inputs)
        inputs["adopted_basis"]["member"]["axial_idealization"]["combinations"] = ["G"]
        self.assert_rejected(project_self_weight_nmax_idealization(**inputs), "VARIABLE_SIGNED_SCOPE_NOT_COVERED")

    def test_unknown_or_unsigned_requested_combination_is_rejected(self):
        inputs = deepcopy(self.inputs)
        inputs["adopted_basis"]["member"]["axial_idealization"]["combinations"].append("UNKNOWN")
        self.assert_rejected(project_self_weight_nmax_idealization(**inputs), "EXACT_SIGNED_COMBINATION_SCOPE_REQUIRED")

    def test_current_source_hash_and_actual_order_are_required(self):
        inputs = deepcopy(self.inputs)
        inputs["source"]["example_context"]["name"] = "Different native source"
        self.assert_rejected(project_self_weight_nmax_idealization(**inputs), "ADOPTED_SOURCE_OR_MEMBER_MISMATCH")
        for key, value in (("actual_second_order_applied", True), ("analysis_order", "SECOND_ORDER")):
            with self.subTest(key=key):
                inputs = deepcopy(self.inputs)
                inputs["pmm"][key] = value
                self.assert_rejected(project_self_weight_nmax_idealization(**inputs), "FIRST_ORDER_REQUIRED_NO_DOUBLE_APPLICATION")

    def test_missing_primitive_cut_is_rejected(self):
        data, request = source_inputs()
        rows = data["column_axial"]["demand_support"]["force_source"]["rowsets"]["C1"]
        delete_force_row(rows, 1)
        self.assert_rejected(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request)),
                             "SELF_WEIGHT_INPUTS_UNBOUND")

    def test_missing_cut_in_all_force_sources_does_not_shrink_expected_grid(self):
        data, request = source_inputs()
        main = data["column_axial"]["force_source"]["rowsets"]["C1"]
        primitives = data["column_axial"]["demand_support"]["force_source"]["rowsets"]["C1"]
        for rows in (main, primitives):
            for index in reversed(range(rows["NumberResults"])):
                if rows["ObjSta"][index] == 1.25:
                    delete_force_row(rows, index)
        self.assert_rejected(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request)),
                             "EXACT_CONFIGURED_CENSUS_REQUIRED")

    def test_absolute_primitive_superposition_rejects_constant_force_offset(self):
        data, request = source_inputs()
        rows = data["column_axial"]["force_source"]["rowsets"]["C1"]
        for index, name in enumerate(rows["LoadCase"]):
            if name == "G":
                rows["P"][index] -= 10.
        # The 20 kN interval gradient is unchanged, so gradient-only validation
        # would pass; the actual combination vector has a 10 kN offset.
        result = project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request))
        self.assert_rejected(result, "ABSOLUTE_PRIMITIVE_SUPERPOSITION_FAILED:G")
        self.assertEqual(result["gravity_axial_balance"]["combinations"]["G"]["status"],
                         "SELF_WEIGHT_BALANCED_AT_SIGNED_CUTS")

    def test_unexplained_axial_jump_does_not_become_self_weight(self):
        data, request = source_inputs()
        for rows in (data["column_axial"]["force_source"]["rowsets"]["C1"],
                     data["column_axial"]["demand_support"]["force_source"]["rowsets"]["C1"]):
            for index, (case, station) in enumerate(zip(rows["LoadCase"], rows["ObjSta"])):
                if station == 1.25 and case not in {"EX", "EY"}:
                    rows["P"][index] -= 1.
        self.assert_rejected(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request)),
                             "SELF_WEIGHT_RECONCILIATION_FAILED")

    def test_zero_or_tensile_local_cut_is_not_eligible(self):
        for shift in (2500., 2501.):
            with self.subTest(shift=shift):
                data, request = source_inputs()
                main = data["column_axial"]["force_source"]["rowsets"]["C1"]
                primitives = data["column_axial"]["demand_support"]["force_source"]["rowsets"]["C1"]
                main["P"] = [p + shift for p in main["P"]]
                primitives["P"] = [p + shift if name == "LC_DL" else p
                                     for p, name in zip(primitives["P"], primitives["LoadCase"])]
                self.assert_rejected(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request)),
                                     "POSITIVE_COMPRESSION_REQUIRED")

    def test_prepared_pmm_nd_or_physical_length_cannot_override_native_inputs(self):
        inputs = deepcopy(self.inputs)
        inputs["pmm"]["rows"][0]["nd_kn"] = 1.
        self.assert_rejected(project_self_weight_nmax_idealization(**inputs), "PMM_NATIVE_AXIAL_OR_STEP_MISMATCH")
        inputs = deepcopy(self.inputs)
        inputs["length"]["physical_length_m"] = 2.
        self.assert_rejected(project_self_weight_nmax_idealization(**inputs), "PHYSICAL_LENGTH_CONTEXT_MISMATCH")

    def test_independent_station_assignment_is_required_even_with_three_received_cuts(self):
        data, request = source_inputs()
        station_table = data["column_axial"]["r10_source"]["table_reads"]["Frame Assignments - Output Stations"]
        next(row for row in station_table["rows"] if row["UniqueName"] == "C1")["MinStations"] = "4"
        self.assert_rejected(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request)),
                             "INDEPENDENT_CUTS_UNBOUND:THREE_STATION_ASSIGNMENT_UNVERIFIED")

    def test_known_native_second_order_stiffness_cannot_be_adopted_as_first_order(self):
        data, request = source_inputs()
        rows = data["vs04_basis_probe"]["table_reads"]["Load Case Definitions - Linear Static"]["rows"]
        next(row for row in rows if row["Name"] == "LC_DL")["StiffType"] = "P-Delta"
        self.assert_rejected(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request)),
                             "PRIMITIVE_FIRST_ORDER_UNBOUND:LC_DL")

    def test_actual_interior_wall_geometry_withholds_isolated_member_premise(self):
        data, request = source_inputs()
        b1 = data["vs06_b1_geometry_source"]["table_reads"]
        r10 = data["column_axial"]["r10_source"]["table_reads"]

        def append(record, values):
            record["rows"].extend(dict(zip(record["fields"], row, strict=True)) for row in values)
            record["row_count"] = len(record["rows"])

        points = [("W0", "S1", "0", "0", ".5"), ("W1", "S1", "2", "0", ".5"),
                  ("W2", "S1", "2", "0", "2"), ("W3", "S1", "0", "0", "2")]
        append(b1["Point Object Connectivity"], points)
        b1[WALL_CONNECTIVITY] = table(WALL_CONNECTIVITY, "UniqueName Story WallBay UniquePt1 UniquePt2 UniquePt3 UniquePt4",
                                      [("W", "S1", "W", "W0", "W1", "W2", "W3")])
        b1[WALL_PROPERTIES] = table(WALL_PROPERTIES, "Name ModelType Thickness", [("PW", "Shell-Thick", ".4")],
                                    {"Thickness": "m"})
        append(b1["Area Assignments - Section Properties"], [("W", "S1", "W", "Wall", "PW")])
        append(r10[AREA_INSERTION], [("W", "S1", "W", "Middle")])
        append(r10[AREA_ELEMENTS], [("S1", "W-1", "Wall", "W", "W", "W0", "W1", "W2")])
        append(r10["Objects and Elements - Joints"], [(uid, uid, "Joint", story, x, y, z)
                                                       for uid, story, x, y, z in points])
        capture = data["vs06_b1_geometry_source"]
        capture["payload_sha256"] = digest({key: value for key, value in capture.items() if key != "payload_sha256"})
        self.assert_rejected(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request)),
                             "NONMATCHING_WALL_CONTACT_REQUIRES_CONNECTION_BASIS")

    def test_exact_integer_material_weight_is_valid_but_coarse_rounding_cannot_hide_error(self):
        data, request = source_inputs()
        materials = data["column_axial"]["pmm_section_source"]["table_reads"][MECHANICAL]["rows"]
        concrete = next(row for row in materials if row["Material"] == "C35/45")
        concrete["UnitWeight"] = "25"
        self.assertEqual(project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request))["status"],
                         "SELF_WEIGHT_NMAX_INPUTS_ELIGIBLE")
        raw, request = source_and_request(unit_weight_kn_m3=25.1)
        data = json.loads(raw)
        concrete = next(row for row in data["column_axial"]["pmm_section_source"]["table_reads"][MECHANICAL]["rows"]
                        if row["Material"] == "C35/45")
        concrete["UnitWeight"] = "25"
        result = project_self_weight_nmax_idealization(**actual_owner_inputs(data=data, request=request))
        self.assert_rejected(result, "SELF_WEIGHT_RECONCILIATION_FAILED")
        # The historical diagnostic admits half of the last printed digit;
        # the new source premise also applies the separate 0.001 kN cap.
        self.assertEqual(result["gravity_axial_balance"]["combinations"]["G"]["status"],
                         "SELF_WEIGHT_BALANCED_AT_SIGNED_CUTS")


if __name__ == "__main__":
    unittest.main()
