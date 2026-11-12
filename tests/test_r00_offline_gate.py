"""R00 tests: source provenance, 1:1 census, fail-closed, read-only SQLite."""
import contextlib
import copy
from hashlib import sha256
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from r00_offline_gate import SourceGateError, _canonical, audit_batch, audit_sqlite, main


def sealed(data):
    data = copy.deepcopy(data)
    data["payload_sha256"] = sha256(_canonical(data)).hexdigest()
    return data


def make_zip(path, *, force=False, bad_ids=False, mode="GETTERS_ONLY"):
    frame = "C1"
    call = {"api": "Results.FrameForce", "call_id": "CALL-0001",
            "return_code": 0 if force else 1,
            "status": "OBSERVED" if force else "MISSING"}
    if force:
        call["values"] = {"NumberResults": 1, "Obj": [frame], "ObjSta": [0.0],
                          "Elm": [frame], "ElmSta": [0.0], "LoadCase": ["LC_DL"],
                          "StepType": ["Single Value"], "StepNum": [0.0], "P": [-1.0],
                          "V2": [0.0], "V3": [0.0], "T": [0.0], "M2": [0.0], "M3": [0.0]}
    trans = None
    if mode == "EXPLICIT_TEMPORARY_OUTPUT_AND_DISPLAY":
        trans = {"mode": mode, "restoration": "VERIFIED", "output_flags_restored_exactly": True,
                 "model_analysis_design_save_setters_used": False,
                 "display_before": {"cases": ["LC_DL"], "combinations": []},
                 "display_after": {"cases": ["LC_DL"], "combinations": []},
                 "original_selected_output_cases": ["LC_DL"],
                 "restored_selected_output_cases": ["LC_DL"],
                 "original_selected_output_combinations": [],
                 "restored_selected_output_combinations": []}
    elif mode == "UNKNOWN":
        trans = {"mode": "UNRECOGNIZED"}
    index = {"schema": "tbdy.next.column-batch-live.v1",
             "source": {"units_code": 6, "model_locked": True, "model_filename": "M.EDB"},
             "selection_transaction": trans, "no_etabs_setters_used": mode != "EXPLICIT_TEMPORARY_OUTPUT_AND_DISPLAY",
             "analysis_generation_proven": False, "observed_column_count": 1,
             "columns": [{"frame_name": "OTHER" if bad_ids else frame}]}
    common = {"schema": index["schema"], "source": index["source"],
              "no_etabs_setters_used": index["no_etabs_setters_used"],
              "selection_transaction": trans,
              "population": {"columns": [frame]}}
    column = {"schema": "tbdy.next.column-batch-member.v1", "frame_name": frame,
              "final_design_eligible": False,
              "native_calls": [call], "force": {"source_call_id": "CALL-0001",
                                               "status": "CAPTURED" if force else "MISSING",
                                               "native_row_count": 1 if force else 0},
              "design_summary": {"status": "MISSING"}}
    objects = {"common.json": sealed(common), "columns/C1.json": sealed(column)}
    raw = {k: _canonical(v) for k, v in objects.items()}
    index["payload_file_sha256"] = {k: sha256(v).hexdigest() for k, v in raw.items()}
    raw["index.json"] = _canonical(sealed(index))
    manifest = {"schema": index["schema"],
                "files": {k: sha256(v).hexdigest() for k, v in raw.items()}}
    raw["manifest.json"] = _canonical(sealed(manifest))
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in raw.items():
            z.writestr(name, data)
    return raw


class OfflineGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "batch.zip"

    def test_incomplete_archive_is_valid_but_blocked(self):
        make_zip(self.path)
        result = audit_batch(self.path, expected_columns=1)
        self.assertTrue(result["archive_manifest_verified"])
        self.assertEqual(result["native_force_rows"], 0)
        self.assertEqual(result["source_readiness"], "BLOCKED_NO_NATIVE_FORCE_ROWS")
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_force_rows_only_eligible_for_replay(self):
        make_zip(self.path, force=True)
        result = audit_batch(self.path, expected_columns=1)
        self.assertEqual(result["source_readiness"], "SOURCE_ROWS_PRESENT_REPLAY_REQUIRED")
        self.assertFalse(result["normative_design_approved"])
        self.assertFalse(result["spectral_replay_verified"])

    def test_qualified_temporary_selection_requires_restore(self):
        make_zip(self.path, force=True, mode="EXPLICIT_TEMPORARY_OUTPUT_AND_DISPLAY")
        self.assertEqual(audit_batch(self.path)["selection_provenance"], "TEMPORARY_RESTORED")

    def test_unknown_selection_mode_rejected(self):
        make_zip(self.path, mode="UNKNOWN")
        with self.assertRaisesRegex(SourceGateError, "UNKNOWN_SELECTION_MODE"):
            audit_batch(self.path)

    def test_census_conflict_rejected(self):
        make_zip(self.path, bad_ids=True)
        with self.assertRaisesRegex(SourceGateError, "PHYSICAL_COLUMN_CENSUS_MISMATCH"):
            audit_batch(self.path)

    def test_wrong_expected_count_rejected(self):
        make_zip(self.path)
        with self.assertRaisesRegex(SourceGateError, "PHYSICAL_COLUMN_CENSUS_MISMATCH"):
            audit_batch(self.path, expected_columns=87)

    def test_tamper_hash_rejected(self):
        raw = make_zip(self.path)
        raw["columns/C1.json"] = raw["columns/C1.json"].replace(b'"frame_name":"C1"', b'"frame_name":"C2"')
        with zipfile.ZipFile(self.path, "w") as z:
            for n, v in raw.items():
                z.writestr(n, v)
        with self.assertRaisesRegex(SourceGateError, "ZIP_CONTENT_HASH_MISMATCH"):
            audit_batch(self.path)

    def test_duplicate_zip_member_rejected(self):
        make_zip(self.path)
        with zipfile.ZipFile(self.path, "a") as z:
            with __import__("warnings").catch_warnings():
                __import__("warnings").simplefilter("ignore", UserWarning)
                z.writestr("index.json", b"{}")
        with self.assertRaisesRegex(SourceGateError, "UNSAFE_OR_DUPLICATE_ZIP_MEMBER"):
            audit_batch(self.path)

    def test_bad_path_rejected(self):
        raw = make_zip(self.path)
        with zipfile.ZipFile(self.path, "w") as z:
            for n, v in raw.items():
                z.writestr(n, v)
            z.writestr("../unsafe.txt", "oops")
        with self.assertRaisesRegex(SourceGateError, "UNSAFE_OR_DUPLICATE_ZIP_MEMBER"):
            audit_batch(self.path)

    def test_cli_expected_exit_two_when_no_force(self):
        make_zip(self.path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--archive", str(self.path), "--expected-columns", "1", "--require-force"]), 2)

    def test_cli_does_not_overwrite_existing_report(self):
        make_zip(self.path)
        report = Path(self.temp.name) / "report.json"
        report.write_text("LEAVE_ME", encoding="utf8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--archive", str(self.path), "--output", str(report)]), 3)
        self.assertEqual(report.read_text(), "LEAVE_ME")

    def test_sqlite_read_only_sha(self):
        db = Path(self.temp.name) / "cache.sqlite"
        with sqlite3.connect(db) as c:
            c.execute("CREATE TABLE t (v INT)")
            c.execute("INSERT INTO t VALUES (42)")
        before = sha256(db.read_bytes()).hexdigest()
        result = audit_sqlite(db)
        self.assertTrue(result["read_only"])
        self.assertTrue(result["integrity_ok"])
        self.assertEqual(result["table_count"], 1)
        self.assertEqual(result["sha256"], before)
        self.assertEqual(sha256(db.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
