"""Independent hand-vector and source-failure tests; all committed data synthetic."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from column_bank_fixture import SyntheticBank, encoded, zipped, subset, historical_db
from tbdy_next.column_engine.native_archive import BankError, NativeArchive, decode
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.store import save_column_bank, read_column_bank, column_bank_history, reconcile_historical_db
from tbdy_next.cli import main


def summary(report, name="SUM"):
    return next(c for c in report["static_replay"]["combinations"] if c["combination"] == name)


class NativeBankTests(unittest.TestCase):
    def test_six_component_signed_vector_and_mesh_identity(self):
        source = SyntheticBank().build(); report = recover_column_bank(source)
        self.assertEqual((report["selected_column_count"], report["observed_column_count"],
            report["force_row_count"], report["analysis_element_count"]), (2, 2, 64, 4))
        self.assertEqual(report["source_archive_sha256"], sha256(source).hexdigest())
        self.assertEqual(len({r["source_row_id"] for r in report["force_states"]}), 64)
        rows = [r for r in report["force_states"] if r["Obj"] == "C_SYNTHETIC_1" and r["LoadCase"] == "G" and r["ObjSta"] == 2]
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["ElmSta"] for r in rows}, {0, 2})
        self.assertEqual([r["P"] for r in rows], [-200, -300])
        self.assertTrue(report["native_axial_sign_unchanged"])
        self.assertFalse(report["all_building_columns_proven"])

    def test_static_arithmetic_matches_independent_hand_vector(self):
        report = recover_column_bank(SyntheticBank().build()); replay = report["static_replay"]
        self.assertEqual((replay["matched_rows"], replay["scalar_comparisons"]), (8, 48))
        item = next(r for r in replay["items"] if r["member_id"] == "C_SYNTHETIC_1" and r["object_station_m"] == 0)
        expected = {"P": -180, "V2": -3.6, "V3": 3.8, "T": -4, "M2": -4.2, "M3": 4.4}
        self.assertEqual(item["calculated"], expected)
        self.assertEqual(item["observed"], expected)
        self.assertEqual(len(item["constituent_row_ids"]), 2)
        self.assertLess(replay["maximum_absolute_difference"], 1e-12)
        self.assertEqual((report["design_demand_authority"], report["formal_compliance"], report["engineering_release"]),
                         ("DENIED", "NOT_PROVEN", "NOT_READY"))

    def test_spectral_envelope_and_nested_do_not_gain_concurrence(self):
        report = recover_column_bank(SyntheticBank().build())
        for name, reason in (("RS_SUM", "SPECTRAL_OR_OTHER"), ("ENV", "NON_LINEAR_ADD"), ("NESTED", "NESTED_COMBINATION")):
            with self.subTest(name=name):
                row = summary(report, name)
                self.assertEqual((row["status"], row["scalar_comparisons"]), ("NOT_EVALUATED", 0))
                self.assertIn(reason, row["reason"])

    def test_source_catalog_retains_missing_case_and_only_recorded_mode(self):
        report = recover_column_bank(SyntheticBank().build())
        missing = next(r for r in report["case_coverage"] if r["name"] == "MISSING")
        modal = next(r for r in report["case_coverage"] if r["name"] == "MODAL")
        self.assertEqual((report["recorded_output_count"], report["defined_case_count"], report["defined_combination_count"]), (8, 5, 4))
        self.assertEqual((missing["row_count"], len(missing["missing_members"])), (0, 2))
        self.assertEqual((modal["step_types"], modal["step_numbers"]), (["Mode"], [1]))

    def test_offsets_are_not_joint_stations_or_effective_lengths(self):
        report = recover_column_bank(SyntheticBank().build())
        for member in report["members"]:
            geom = member["station_geometry"]
            self.assertEqual((geom["object_i_j_length_m"], geom["offset_j_m"], geom["observed_output_face_span_m"]), (4, .7, 3.3))
            self.assertTrue(geom["last_station_matches_j_offset"])
            self.assertFalse(geom["last_station_is_joint_j"])
            self.assertFalse(geom["ts500_free_length_proven"])
            self.assertFalse(geom["effective_length_proven"])

    def test_units_model_cage_and_distinct_steel_provenance(self):
        context = recover_column_bank(SyntheticBank().build())["members"][0]["context"]
        self.assertEqual((context["geometry"]["T2_cm"], context["geometry"]["T3_cm"]), (80, 80))
        self.assertEqual((context["material"]["fc_MPa"], context["material"]["fy_MPa"]), (35, 500))
        self.assertEqual(context["source_calls"]["steel"]["entity_name"], "STEEL_SYNTHETIC")
        self.assertEqual(context["source_calls"]["confinement_steel"]["entity_name"], "TIE_STEEL_SYNTHETIC")
        self.assertIsNone(context["rebar_configuration"]["actual_bar_coordinates"])
        self.assertFalse(context["ready_for_pmm_design"])

    def test_subset_lineage_recovers_tuples_without_parent_authority(self):
        raw = SyntheticBank().build(); part = recover_column_bank(subset(raw))
        self.assertEqual((part["source_kind"], part["force_row_count"]), ("D7B13_SUBSET", 64))
        self.assertEqual(part["parent_archive_sha256_claim"], sha256(raw).hexdigest())
        self.assertFalse(part["parent_archive_bytes_verified"])
        self.assertFalse(part["capture_context_observed"])
        self.assertEqual(part["static_replay"]["scalar_comparisons"], 0)

    def test_missing_selected_member_remains_in_population(self):
        fixture = SyntheticBank(); fixture.omitted.add(("Results.FrameForce", "frame", fixture.members[1]))
        report = recover_column_bank(fixture.build())
        self.assertEqual((report["selected_column_count"], report["observed_column_count"]), (2, 1))
        self.assertEqual(report["members"][1]["force_rows"], 0)
        self.assertTrue(report["members"][1]["reason_codes"])
        self.assertEqual((summary(report)["status"], summary(report)["unresolved_rows"]), ("PARTIAL", 1))

    def test_missing_constituent_or_result_does_not_reduce_expected_stations(self):
        for case in ("Q", "SUM"):
            fixture = SyntheticBank(); name = fixture.members[0]
            fixture.forces[name] = [r for r in fixture.forces[name] if not (r[4] == case and r[1] == 3.3)]
            row = summary(recover_column_bank(fixture.build()))
            self.assertEqual((row["expected_rows"], row["matched_rows"], row["unresolved_rows"]), (8, 7, 1))
            self.assertEqual(row["status"], "PARTIAL")

    def test_step_mismatch_or_ambiguity_cannot_form_a_vector(self):
        for change in ("different_step", "extra_step", "not_single"):
            fixture = SyntheticBank(); rows = fixture.forces[fixture.members[0]]
            q = next(r for r in rows if r[4] == "Q" and r[1] == 0)
            if change == "different_step": q[6] = 1
            elif change == "extra_step":
                other = deepcopy(q); other[6] = 1; rows.append(other)
            else: q[5] = "Max"
            row = summary(recover_column_bank(fixture.build()))
            self.assertEqual((row["matched_rows"], row["unresolved_rows"]), (7, 1))

    def test_wrong_force_value_is_a_mismatch_not_a_pass(self):
        fixture = SyntheticBank(); row = next(r for r in fixture.forces[fixture.members[0]] if r[4] == "SUM")
        row[11] += .01
        result = summary(recover_column_bank(fixture.build()))
        self.assertEqual((result["status"], result["mismatched_rows"]), ("NUMERICAL_MISMATCH", 1))
        self.assertAlmostEqual(result["maximum_absolute_difference"], .01)

    def test_missing_or_nonstatic_native_type_is_not_inferred_from_name(self):
        for missing in (False, True):
            fixture = SyntheticBank()
            if missing: fixture.omitted.add(("LoadCases.GetTypeOAPI_1", "case", "G"))
            else: fixture.cases["G"] = 4
            self.assertEqual(summary(recover_column_bank(fixture.build()))["status"], "NOT_EVALUATED")

    def test_unstable_capture_blocks_replay_without_dropping_source_rows(self):
        fixture = SyntheticBank(); fixture.context["identity_unchanged"] = False
        report = recover_column_bank(fixture.build())
        self.assertEqual(report["force_row_count"], 64)
        self.assertEqual(summary(report)["reason"], "CAPTURE_CONTEXT_NOT_STABLE")
        self.assertEqual(report["static_replay"]["scalar_comparisons"], 0)

    def test_duplicate_full_key_invalid_units_and_nonfinite_are_rejected(self):
        for defect in ("duplicate", "units", "bool", "nan"):
            fixture = SyntheticBank(); rows = fixture.forces[fixture.members[0]]
            if defect == "duplicate": rows.append(deepcopy(rows[0]))
            elif defect == "units": fixture.force_units = 5
            elif defect == "bool": rows[0][7] = True
            else: rows[0][7] = float('nan')
            report = recover_column_bank(fixture.build())
            self.assertEqual(report["members"][0]["force_status"], "NOT_PROVEN")
            self.assertEqual(summary(report)["status"], "PARTIAL")

    def test_bad_geometry_does_not_erase_valid_force_evidence(self):
        fixture = SyntheticBank()
        key = ("PointObj.GetCoordCartesian", "point", fixture.members[0]+"J")
        fixture.calls[key]["raw_response"][2] = 1
        report = recover_column_bank(fixture.build())
        self.assertEqual(report["force_row_count"], 64)
        self.assertIn("FORCE_STATION_OUTSIDE_OBJECT_LENGTH", report["members"][0]["reason_codes"])
        self.assertNotIn("station_geometry", report["members"][0])
        self.assertEqual(report["native_context_coverage"]["complete_station_geometry"], 1)

    def test_manifest_tampering_and_path_traversal_fail_closed(self):
        files = SyntheticBank().files(); files["collector-summary.json"] = b'{}'
        with self.assertRaisesRegex(BankError, "HASH_OR_SIZE"): recover_column_bank(zipped(files))
        files = SyntheticBank().files(); files['../escape'] = b'bad'
        with self.assertRaisesRegex(BankError, "MEMBERS_INVALID"): recover_column_bank(zipped(files))

    def test_duplicate_zip_members_and_json_keys_rejected(self):
        raw = SyntheticBank().build(); stream = BytesIO(raw)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(stream, 'a') as z: z.writestr('collector-summary.json', b'{}')
        with self.assertRaisesRegex(BankError, "MEMBERS_INVALID"): NativeArchive(stream.getvalue())
        for raw in ('{"x":1,"x":2}', '{"x":1e309}', '{"x":NaN}'):
            with self.assertRaises(ValueError): decode(raw)


class ColumnStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.archive = self.root/'bank.zip'
        self.archive.write_bytes(SyntheticBank().build())
        self.receipts = self.root/'receipts'

    def test_historical_db_read_only_totals_and_no_engineering_promotion(self):
        db = self.root/'historic.sqlite'; historical_db(db); original = db.read_bytes()
        summary_report = save_column_bank(self.archive, self.receipts, historical_db=db)
        self.assertEqual(db.read_bytes(), original)
        report = read_column_bank(self.receipts, summary_report["run_id"], full=True)
        history = report["historical_reconciliation"]
        self.assertEqual(history["numeric_matches"], 3)
        self.assertEqual(history["source_sha256"], sha256(original).hexdigest())
        self.assertEqual(history["story_phi_authority"], "DENIED")
        self.assertFalse(history["same_cut_proven"])
        self.assertEqual(len(report["force_states"]), 64)
        self.assertEqual(len(report["static_replay"]["items"]), 8)

    def test_missing_historical_constituent_never_becomes_zero(self):
        db = self.root/'historic.sqlite'; historical_db(db)
        report = recover_column_bank(self.archive.read_bytes())
        report["force_states"] = [r for r in report["force_states"] if not
            (r["Obj"] == 'C_SYNTHETIC_2' and r["LoadCase"] == 'G' and r["ObjSta"] == 0)]
        item = next(r for r in reconcile_historical_db(report, db)["items"] if r["output_case"] == 'G')
        self.assertIsNone(item["native_signed_p_sum_kN"])
        self.assertFalse(item["numeric_match"])

    def test_database_filtering_pagination_and_consistent_export(self):
        saved = save_column_bank(self.archive, self.receipts)
        run = saved["run_id"]
        full = read_column_bank(self.receipts, run, full=True)
        page = read_column_bank(self.receipts, run, member_id='C_SYNTHETIC_1', output_case='G', offset=1, limit=2)
        self.assertEqual((page["force_page"]["total"], len(page["force_page"]["rows"])), (4, 2))
        expected = [r for r in full["force_states"] if r['Obj']=='C_SYNTHETIC_1' and r['LoadCase']=='G'][1:3]
        self.assertEqual(page["force_page"]["rows"], expected)
        self.assertEqual(page["result_sha256"], saved["result_sha256"])
        empty = read_column_bank(self.receipts, run, member_id="' OR 1=1 --")["force_page"]
        self.assertEqual(empty["total"], 0)
        self.assertEqual(column_bank_history(self.receipts)[0]["run_id"], run)

    def test_changed_source_database_or_receipt_is_not_exposed(self):
        for filename in ("input.source", "column-bank.sqlite", "01-column-bank.json"):
            with self.subTest(filename=filename):
                saved = save_column_bank(self.archive, self.receipts); run = saved["run_id"]
                path = self.receipts/run/filename; original = path.read_bytes()
                path.write_bytes(original+b'CORRUPT')
                with self.assertRaises(ValueError): read_column_bank(self.receipts, run)
                self.assertNotIn(run, [r["run_id"] for r in column_bank_history(self.receipts)])

    def test_wrong_run_and_symlink_cannot_cross_source_boundary(self):
        saved = save_column_bank(self.archive, self.receipts)
        for run in ("../bank", saved["run_id"]+"/..", 'RUN-'+'a'*32):
            with self.assertRaises(ValueError): read_column_bank(self.receipts, run)
        path = self.receipts/saved["run_id"]/'input.source'
        path.unlink()
        try: path.symlink_to(self.archive)
        except OSError: self.skipTest('OS disallows creating symlinks')
        with self.assertRaises(ValueError): read_column_bank(self.receipts, saved["run_id"])

    def test_cli_import_uses_offline_path_and_preserves_original(self):
        original = self.archive.read_bytes()
        with patch('sys.stdout', new_callable=StringIO) as output:
            code = main(['import-column-bank', '--input', str(self.archive), '--out', str(self.receipts)])
        result = json.loads(output.getvalue())
        self.assertEqual((code, result["force_row_count"], result["static_replay_scalar_comparisons"]), (0, 64, 48))
        self.assertEqual(self.archive.read_bytes(), original)
        self.assertTrue((self.receipts/result['run_id']/'column-bank.sqlite').is_file())


if __name__ == '__main__':
    unittest.main()
