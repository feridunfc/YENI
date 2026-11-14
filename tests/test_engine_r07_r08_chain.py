"""Synthetic contract tests. No private ETABS EDB/JSON or mock engineering PASS."""
import copy
import unittest
from unittest.mock import patch, Mock

from tbdy_next.column_engine.native_archive import digest
from tbdy_next.engineering.live_column import (
    LiveEvidenceError, review_live_column,
)


def seal(payload, field="payload_sha256"):
    payload[field] = digest(payload)
    return payload


def table(rows):
    return {"status": "CAPTURED", "field_metadata": {"status": "OK"},
            "row_count": len(rows), "rows": rows}


def gateway(path, tables):
    return seal({
        "schema": "tbdy.next.etabs.generic-source-capture.v1",
        "status": "CAPTURED", "model": path,
        "source_only": True, "model_locked": True, "model_units_code": 6,
        "model_units_unchanged": True, "selection_restored": True,
        "case_selection_before": [], "case_selection_after": [],
        "table_reads": {key: table(value) for key, value in tables.items()},
    })


def sample_receipts():
    model, sha, member = "synthetic_readonly.edb", "a" * 64, "101"
    col = {"UniqueName": member, "Story": "+4.50", "Length": "4.5",
           "UniquePtI": "P1", "UniquePtJ": "P2"}
    assign = {"UniqueName": member, "Story": "+4.50",
              "Label": "C1", "Shape": "Concrete Rectangular", "SectProp": "C80"}
    rect = {"Name": "C80", "DesignType": "Column",
            "Material": "C35", "t2": "0.8", "t3": "0.8"}
    base = {
        "Column Object Connectivity": [col],
        "Frame Assignments - Section Properties": [assign],
        "Frame Section Property Definitions - Concrete Rectangular": [rect],
        "Material Properties - Concrete Data": [
            {"Material": "C35", "Fc": "35000"}],
        "Frame Section Property Definitions - Concrete Column Reinforcing": [
            {"Name": "C80", "RebarMatL": "Rebar500"}],
        "Material Properties - Rebar Data": [
            {"Material": "Rebar500", "Fy": "500000"}],
        "Concrete Frame Design Preferences - TS 500-2000(R2018)": [
            {"GammaC": "1.5", "GammaS": "1.15"}],
    }
    live = seal({
        "schema": "tbdy.next.r07-r09.live-readonly.v1",
        "model_filename": model, "requested_member": member,
        "selected_identity": {"Obj": member, "LoadCase": "LC_DL", "StepType": "Single Value"},
        "analysis_generation_proven": False,
        "edb_sha256_before": sha, "edb_sha256_after": sha,
        "model_units_before": 6, "model_units_after": 6,
        "model_locked_before": True, "model_locked_after": True,
        "gateway_capture": gateway(model, base),
    })
    bars = [{"x2": a, "x3": b, "area": 2000.0}
            for a in (-300., 300.) for b in (-300., 300.)]
    cage_sha = "b" * 64
    checks = [
        {"stage": "R07", "numeric_detail": {
            "kernel_inputs": {"material_owner": {
                "fck": 35., "fcd": 35./1.5, "fyd": 500./1.15,
                "es": 200000., "ecu": .003}}}},
        {"stage": "R08", "numeric_detail": {}},
        {"stage": "R09", "numeric_detail": {
            "role": "PROPOSED", "constructible_scenario": True,
            "cage_revision_sha256": cage_sha,
            "bar_count": 4, "steel_ratio": 8000./640000.,
            "area_ratio_reference_met": True,
            "spacing_reference_met": True,
            "tie_diameter_reference_met": True,
            "bar_area_geometry": bars}},
    ]
    for ci in checks:
        seal(ci, "instance_sha256")
    lc = {
        "schema": "tbdy.next.r07-r09.one-column-run-result.v1",
        "source": {
            "source_sha256": live["payload_sha256"],
            "physical_object_id": member, "model_edb_sha256": sha,
            "output_case": "LC_DL"},
        "cage_revision_sha256": cage_sha,
        "check_instances": checks, "engineering_release": "NOT_READY",
        "design_demand_approved": False,
    }
    seal(lc, "run_result_sha256")
    terms = [{"case": case, "factor": factor, "case_type": "Linear Static"}
             for case, factor in (
                 ("LC_DL", "1.4"), ("LC_SDL", "1.4"), ("LC_WDL", "1.4"),
                 ("LC_LL", "1.6"), ("LC_DDL", "1.6"), ("LC_S", "1.6"))]
    rows = []
    for station, p, m2 in ((0., -100., 10.), (1.9, -95., 20.), (3.8, -90., -25.)):
        rows.append({
            "Obj": member, "Elm": member, "ObjSta": station, "ElmSta": station,
            "LoadCase": "Grav_Ult", "StepType": "Single Value", "StepNum": 0.,
            "P": p, "V2": 1., "V3": 2., "T": 0., "M2": m2, "M3": 3.,
        })
    combo = seal({
        "schema": "tbdy.next.r07.gravult-combo-live-capture.v1",
        "combo_station_count": 3, "member_id": member, "rows": rows,
        "source_only": True, "analysis_generation_proven": False,
        "same_cut_proven": False,
        "combo": {
            "name": "Grav_Ult", "operator": "Linear Add",
            "concrete_design_list": "Strength", "terms": terms},
        "model_filename": model, "model_edb_sha256": sha,
        "results_combo_flag_before": False, "results_combo_flag_after": False,
    })
    previous = []
    for row in rows:
        item = {
            "physical_object_id": member, "analysis_element_id": member,
            "case": "Grav_Ult", "source_sha256": combo["payload_sha256"],
            "obj_station_m": row["ObjSta"], "elm_station_m": row["ElmSta"],
            "step_type": row["StepType"], "step_number": row["StepNum"],
            "signed_source_six": {k: row[k] for k in ("P", "V2", "V3", "T", "M2", "M3")},
            "owner_pmm_result": {
                "status": "WITHIN_SCENARIO_SURFACE", "utilization": .05},
        }
        previous.append(seal(item, "instance_sha256"))
    pmm = {
        "schema": "tbdy.next.r07.gravult-combo-pmm-run-result.v1",
        "source_capture_sha256": combo["payload_sha256"],
        "reference_lc_dl_run_sha256": lc["run_result_sha256"],
        "original_cage_sha256": cage_sha, "model_edb_sha256": sha,
        "observed_station_count": 3, "numeric_pmm_station_count": 3,
        "check_instances": previous,
        "engineering_release": "NOT_READY",
    }
    seal(pmm, "run_result_sha256")
    geom = gateway(model, {
        "Frame Assignments - End Length Offsets": [
            {"UniqueName": member, "OffsetI": "0", "OffsetJ": "0.7",
             "OffsetOpt": "Auto", "RigidFact": "0"}],
        "Frame Assignments - Local Axes": [
            {"UniqueName": member, "Angle": "90"}],
        "Point Object Connectivity": [
            {"UniqueName": "P1", "X": "10", "Y": "5", "Z": "0"},
            {"UniqueName": "P2", "X": "10", "Y": "5", "Z": "4.5"}],
    })
    geom["analysis_generation_proven"] = False
    geom = seal({k: v for k, v in geom.items() if k != "payload_sha256"})
    return {
        "live": live, "lc_run": lc, "combo": combo,
        "pmm_run": pmm, "geometry": geom,
    }


class SourceChainTests(unittest.TestCase):
    def test_three_station_owned_replay_and_geometry(self):
        fixtures = sample_receipts()
        fake = Mock()
        fake.assess.return_value = {
            "status": "WITHIN_SCENARIO_SURFACE", "utilization": .05}
        with patch("tbdy_next.engineering.live_column.solver", return_value=fake):
            result = review_live_column(**fixtures)
        self.assertEqual(fake.assess.call_count, 3)
        self.assertEqual(result["r07"]["governing_observed_station_m"], 0.0)
        self.assertEqual(result["r08"]["geometry"]["observed_output_span_m"], 3.8)
        self.assertEqual(result["r08"]["geometry"]["length_i_j_m"], 4.5)
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertFalse(result["r07"]["formal_pmm_pass"])
        self.assertEqual(result["result_sha256"],
                         digest({k: v for k, v in result.items() if k != "result_sha256"}))

    def test_proposed_bar_ratio_is_recomputed(self):
        from tbdy_next.engineering.live_column import _material_and_cage
        fixtures = sample_receipts()
        fixtures["lc_run"]["check_instances"][2]["numeric_detail"]["steel_ratio"] = .02
        with self.assertRaisesRegex(LiveEvidenceError, "PROPOSED_REBAR_AREA_OR_RATIO_MISMATCH"):
            _material_and_cage(fixtures["live"], fixtures["lc_run"], "101")

    def test_tampered_combo_is_rejected(self):
        fixtures = sample_receipts()
        fixtures["combo"]["rows"][0]["M2"] = 9999.
        with self.assertRaisesRegex(LiveEvidenceError, "RECEIPT_SHA_MISMATCH"):
            review_live_column(**fixtures)

    def test_nonconcurrent_combo_is_rejected(self):
        fixtures = sample_receipts()
        fixtures["combo"]["rows"][0]["StepType"] = "Max"
        fixtures["combo"] = seal({k: v for k, v in fixtures["combo"].items()
                                  if k != "payload_sha256"})
        with self.assertRaisesRegex(LiveEvidenceError, "CROSS_SOURCE|RECEIPT_SHA_MISMATCH"):
            # The dependent PMM receipt must also be resealed; otherwise chain breaks earlier.
            review_live_column(**fixtures)

    def test_wrong_model_sha_is_rejected(self):
        fixtures = sample_receipts()
        fixtures["combo"]["model_edb_sha256"] = "f" * 64
        fixtures["combo"] = seal({k: v for k, v in fixtures["combo"].items()
                                  if k != "payload_sha256"})
        with self.assertRaisesRegex(LiveEvidenceError, "CROSS_SOURCE"):
            review_live_column(**fixtures)


if __name__ == "__main__":
    unittest.main()
