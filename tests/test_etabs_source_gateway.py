"""Offline fake ETABS 23.2 ABI tests; no Windows/COM required."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.engineering.column_r10_live import (
    ANALYSIS_FRAME_ELEMENTS, ANALYSIS_JOINT_COORDINATE_SCHEMA, ANALYSIS_JOINT_ELEMENTS,
    FRAME_OUTPUT_STATIONS, capture_r10_sources,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.etabs_source_gateway_windows import (
    SourceError, available_tables, bind, capture, field_schema, make_template,
    read_table, resolve_keys, save_new, selected_cases, selected_combinations, set_cases, verify,
)


class FakeDb:
    def __init__(self):
        self.keys = (
            "Joint Displacements", "Story Definitions", "Column Object Connectivity",
            "Story Drifts", "Tower and Base Story Definitions",
        )
        self.selected = ()
        self.set_calls = []
        self.fail_on_selection = False
        self.fail_restore = False
        self.fake_rows = {
            "Joint Displacements": (
                ("UniqueName", "OutputCase", "StepType", "StepNumber", "U1", "U2"),
                [("P1", "RSX", "Max", "", "0.015", "-0.003"),
                 ("P2", "RSX", "Max", "", "0.005", "-0.001")],
                {"U1": "m", "U2": "m"},
            ),
            "Story Definitions": (("Story", "Height"), [("+4.50", "4.5")], {"Height": "m"}),
            "Column Object Connectivity": (("UniqueName", "UniquePtI", "UniquePtJ"),
                                           [("C1", "P1", "P2")], {}),
            "Story Drifts": (("Story", "Direction", "Drift"),
                             [("+4.50", "X", "0.0015")], {"Drift": ""}),
            "Tower and Base Story Definitions": (("BSName", "BSElev"),
                                                 [("Base", "0")], {"BSElev": "m"}),
        }
        self.corrupt_return = None

    def GetAvailableTables(self):
        return (len(self.keys), self.keys, self.keys, [0]*len(self.keys), [1]*len(self.keys), 0)

    def GetAllFieldsInTable(self, key):
        fields, _, units = self.fake_rows[key]
        return (1, len(fields), fields, fields, fields,
                tuple(units.get(f, "") for f in fields), [False]*len(fields), 0)

    def GetTableForDisplayArray(self, *args):
        key = args[0]
        if self.corrupt_return == key:
            return (1, 0, [], 0, [], 0, 1)
        fields, rows, _ = self.fake_rows[key]
        flat = [v for row in rows for v in row]
        return (1, 0, fields, len(rows), flat, 0, 0)

    def GetLoadCasesSelectedForDisplay(self, *args):
        if not self.selected:
            return (0, [], 1)  # actual ETABS 23.2 observed empty-selection form
        return (len(self.selected), list(self.selected), 0)

    def SetLoadCasesSelectedForDisplay(self, cases):
        self.set_calls.append(tuple(cases))
        if cases == [""]:
            if self.fail_restore:
                return 1
            self.selected = ()
        else:
            self.selected = tuple(cases)
            if self.fail_on_selection:
                self.fail_on_selection = False
                return 1  # setter already mutated; must restore despite error
        return 0


class FakeSap:
    def __init__(self, db=None):
        self.DatabaseTables = db or FakeDb()
        self.units = 6
        self.locked = True
        self.name = "C:/models/kompakt_b.EDB"
    def GetPresentUnits(self): return self.units
    def GetModelIsLocked(self): return self.locked
    def GetModelFilename(self, with_path): return self.name


class GatewayTests(unittest.TestCase):
    def test_pmm_reads_mesh_and_station_assignments_through_one_connected_model(self):
        db = FakeDb()
        db.fake_rows[ANALYSIS_FRAME_ELEMENTS] = (
            ("Story", "ElmName", "ObjType", "ObjLabel", "ObjName", "ElmJtI", "ElmJtJ"),
            [("L1", "C1-1", "Column", "C1", "C1", "P1", "P2")], {},
        )
        db.fake_rows[ANALYSIS_JOINT_ELEMENTS] = (
            ("Story", "ElmName", "ObjType", "ObjLabel", "ObjName", "GlobalX", "GlobalY", "GlobalZ"),
            [("L1", "P2", "Point", "P2", "P2", "0", "0", "4.5")],
            {"GlobalX": "m", "GlobalY": "m", "GlobalZ": "m"},
        )
        db.fake_rows[FRAME_OUTPUT_STATIONS] = (
            ("Story", "Label", "UniqueName", "StationOpt", "MaxSpacing", "MinStations"),
            [("L1", "C1", "C1", "Min Stations", "", "3")], {"MaxSpacing": "m"},
        )
        sap = FakeSap(db)
        captured = capture_r10_sources(sap)
        mesh = captured["table_reads"][ANALYSIS_FRAME_ELEMENTS]
        joints = captured["table_reads"][ANALYSIS_JOINT_ELEMENTS]
        stations = captured["table_reads"][FRAME_OUTPUT_STATIONS]
        self.assertEqual(mesh["rows"][0]["ElmName"], "C1-1")
        self.assertEqual(joints["rows"][0]["ElmName"], mesh["rows"][0]["ElmJtJ"])
        self.assertEqual(joints["rows"][0]["GlobalZ"], "4.5")
        self.assertEqual(joints["field_metadata"]["units_by_field"]["GlobalZ"], "m")
        self.assertEqual(stations["rows"][0]["MinStations"], "3")
        self.assertEqual(stations["field_metadata"]["units_by_field"]["MaxSpacing"], "m")
        self.assertEqual((captured["units_before"], captured["units_after"]), (6, 6))
        self.assertTrue(captured["model_locked_before"] and captured["model_locked_after"])
        self.assertEqual(db.set_calls, [])

        db.corrupt_return = ANALYSIS_JOINT_ELEMENTS
        captured = capture_r10_sources(sap)
        self.assertEqual(captured["table_reads"][ANALYSIS_JOINT_ELEMENTS]["status"], "CAPTURE_ERROR")
        self.assertEqual(captured["table_reads"][ANALYSIS_FRAME_ELEMENTS]["status"], "CAPTURED")
        self.assertEqual(captured["table_reads"][FRAME_OUTPUT_STATIONS]["status"], "CAPTURED")

    def test_pmm_reads_unrounded_native_coordinates_only_for_meshed_columns(self):
        db = FakeDb()
        db.fake_rows[ANALYSIS_FRAME_ELEMENTS] = (
            ("Story", "ElmName", "ObjType", "ObjLabel", "ObjName", "ElmJtI", "ElmJtJ"),
            [("L1", "C1-1", "Frame", "C1", "C1", "P1", "P2"),
             ("L1", "C1-2", "Frame", "C1", "C1", "P2", "P3"),
             ("L1", "C2", "Frame", "C2", "C2", "U1", "U2"),
             ("L1", "B1-1", "Frame", "B1", "B1", "B1i", "B1m"),
             ("L1", "B1-2", "Frame", "B1", "B1", "B1m", "B1j")], {},
        )
        db.fake_rows[ANALYSIS_JOINT_ELEMENTS] = (
            ("ElmName", "GlobalX", "GlobalY", "GlobalZ"),
            [("P2", "0", "0", "0.85833")], {"GlobalX": "m", "GlobalY": "m", "GlobalZ": "m"},
        )
        calls = []

        class FakePointElm:
            def GetCoordCartesian(self, name, x, y, z, csys):
                calls.append((name, x, y, z, csys))
                return {"P1": (0.0, 0.0, 0.0, 0), "P2": [0.0, 0.0, 0.8583333589, 0],
                        "P3": (0.0, 0.0, 0.0, 1)}[name]

        sap = FakeSap(db)
        sap.PointElm = FakePointElm()
        captured = capture_r10_sources(sap, column_members=("C1", "C2"))
        native = captured["analysis_joint_coordinates"]
        self.assertEqual(native["schema"], ANALYSIS_JOINT_COORDINATE_SCHEMA)
        self.assertEqual((native["coordinate_system"], native["units"]), ("Global", "m"))
        self.assertEqual(native["coordinates"], {"P1": [0.0, 0.0, 0.0], "P2": [0.0, 0.0, 0.8583333589]})
        self.assertIn("POINT_ELM_COORDINATES_RETURN_CODE:1", native["errors"]["P3"])
        self.assertEqual(calls, [(name, 0.0, 0.0, 0.0, "Global") for name in ("P1", "P2", "P3")])
        self.assertEqual(captured["table_reads"][ANALYSIS_JOINT_ELEMENTS]["rows"][0]["GlobalZ"], "0.85833")
        self.assertEqual(db.set_calls, [])

    def test_realistic_etabs_abi_inventory_and_field_units(self):
        db = FakeDb()
        self.assertEqual(len(available_tables(db)), 5)
        schema = field_schema(db, "Joint Displacements")
        self.assertEqual(schema["status"], "OK")
        self.assertEqual(schema["units_by_field"]["U1"], "m")
        self.assertEqual(schema["field_keys"][0], "UniqueName")

    def test_early_discovery_sees_every_available_table_with_schema(self):
        x = capture(FakeSap(), action="discover")
        self.assertEqual(x["status"], "SCHEMA_DISCOVERED")
        self.assertEqual(len(x["inventory"]), 5)
        self.assertEqual(len(x["table_reads"]), 5)
        self.assertEqual(x["table_reads"]["Joint Displacements"]["status"], "SCHEMA_ONLY")
        verify(x)

    def test_preset_delta_captures_selected_rs_cases_and_restores(self):
        sap = FakeSap()
        x = capture(sap, action="capture", preset="delta", cases=("Modal", "RSX", "RSY"))
        self.assertEqual(x["status"], "CAPTURED")  # optional hints need not exist
        self.assertIn("Joint Coordinates", x["preset_optional_hints_not_found"])
        self.assertIn("Joint Displacements", x["table_reads"])
        self.assertEqual(x["table_reads"]["Joint Displacements"]["row_count"], 2)
        self.assertEqual(x["case_selection_after"], [])
        self.assertEqual(sap.DatabaseTables.selected, ())
        self.assertEqual(sap.DatabaseTables.set_calls[-1], ("",))
        self.assertFalse(x["analysis_generation_proven"])
        verify(x)

    def test_exact_single_table_success_without_guessed_alias(self):
        x = capture(FakeSap(), action="capture", exact=("Joint Displacements",), cases=("RSX",))
        self.assertEqual(x["status"], "CAPTURED")
        self.assertEqual(x["table_queries_not_found"], [])
        self.assertEqual(x["table_reads"]["Joint Displacements"]["row_count"], 2)

    def test_unmatched_exact_table_is_partial_and_not_replaced(self):
        x = capture(FakeSap(), action="capture", exact=("Joint Displacements - Fictional",))
        self.assertEqual(x["status"], "SOURCE_PARTIAL")
        self.assertEqual(x["table_reads"], {})
        self.assertEqual(x["table_queries_not_found"], ["Joint Displacements - Fictional"])

    def test_nonempty_original_display_selection_is_restored(self):
        sap = FakeSap()
        sap.DatabaseTables.selected = ("LC_DL",)
        x = capture(sap, action="capture", exact=("Joint Displacements",),
                    cases=("RSX", "RSY"))
        self.assertEqual(x["status"], "CAPTURED")
        self.assertEqual(x["case_selection_before"], ["LC_DL"])
        self.assertEqual(x["case_selection_after"], ["LC_DL"])
        self.assertEqual(sap.DatabaseTables.selected, ("LC_DL",))

    def test_combination_selection_reads_populated_prefix_and_empty_com_slots(self):
        db = FakeDb()
        for raw, expected in (
            ((0, ("",), 1), ()),
            ((0, [None], 0), ()),
            ((1, ("WGHT", "", None), 0), ("WGHT",)),
            ((1, ("WGHT", "Grav_Ult"), 0), ("WGHT",)),
        ):
            with self.subTest(raw=raw):
                db.GetLoadCombinationsSelectedForDisplay = lambda: raw
                self.assertEqual(selected_combinations(db), expected)

    def test_combination_selection_rejects_invalid_or_ambiguous_responses(self):
        db = FakeDb()
        for raw in (
            (1, ("WGHT",), 1),
            (2, ("WGHT",), 0),
            (2, ("WGHT", "WGHT"), 0),
            (1, ("",), 0),
        ):
            with self.subTest(raw=raw):
                db.GetLoadCombinationsSelectedForDisplay = lambda: raw
                with self.assertRaisesRegex(SourceError, "SELECTED_COMBINATIONS_"):
                    selected_combinations(db)

    def test_empty_table_not_called_captured(self):
        sap = FakeSap()
        original = sap.DatabaseTables.fake_rows["Joint Displacements"]
        sap.DatabaseTables.fake_rows["Joint Displacements"] = (original[0], [], original[2])
        x = capture(sap, action="capture", exact=("Joint Displacements",))
        self.assertEqual(x["status"], "SOURCE_PARTIAL")
        self.assertEqual(x["table_reads"]["Joint Displacements"]["status"], "EMPTY_TABLE")

    def test_bad_model_lock_denies_result_reads_no_analysis_started(self):
        sap = FakeSap()
        sap.locked = False
        with self.assertRaisesRegex(SourceError, "MODEL_NOT_LOCKED"):
            capture(sap, action="capture", exact=("Joint Displacements",))

    def test_selection_exception_restores_even_after_mutation(self):
        sap = FakeSap()
        sap.DatabaseTables.fail_on_selection = True
        with self.assertRaisesRegex(SourceError, "ETABS_CAPTURE_ABORTED"):
            capture(sap, action="capture", exact=("Joint Displacements",), cases=("RSX",))
        self.assertEqual(sap.DatabaseTables.selected, ())

    def test_failed_restore_is_hard_error(self):
        sap = FakeSap()
        sap.DatabaseTables.fail_restore = True
        with self.assertRaisesRegex(SourceError, "CRITICAL_ETABS_DISPLAY_SELECTION_RESTORE_FAILED"):
            capture(sap, action="capture", exact=("Joint Displacements",), cases=("RSX",))

    def test_table_row_limit_not_silent_truncation(self):
        x = capture(FakeSap(), action="capture", exact=("Joint Displacements",), max_rows=1)
        self.assertEqual(x["status"], "SOURCE_PARTIAL")
        self.assertEqual(x["table_reads"]["Joint Displacements"]["status"], "CAPTURE_ERROR")
        self.assertIn("ROW_LIMIT_EXCEEDED", x["table_reads"]["Joint Displacements"]["error"])

    def test_units_mutated_externally_hard_error(self):
        class ChangingSap(FakeSap):
            def GetPresentUnits(self):
                if not hasattr(self, "calls"): self.calls = 0
                self.calls += 1
                return 6 if self.calls == 1 else 10
        with self.assertRaisesRegex(SourceError, "CRITICAL_ETABS_UNITS"):
            capture(ChangingSap(), action="capture", exact=("Joint Displacements",))

    def test_raw_capture_digest_detects_tampering(self):
        x = capture(FakeSap(), action="capture", exact=("Joint Displacements",))
        x["table_reads"]["Joint Displacements"]["rows"][0]["U1"] = "1e10"
        with self.assertRaisesRegex(SourceError, "SHA256_MISMATCH"):
            verify(x)

    def test_exact_binding_of_real_observed_field_and_unit(self):
        x = capture(FakeSap(), action="capture", exact=("Joint Displacements",))
        b = make_template(x)
        self.assertEqual(b["status"], "UNREVIEWED_BINDING_TEMPLATE")
        with self.assertRaisesRegex(SourceError, "NOT_REVIEWED"):
            bind(x, b)
        b["status"] = "REVIEWED_EXACT_FIELDS"
        c = b["bindings"][0]
        c["identity"] = ["UniqueName", "OutputCase"]
        c["fields"]["U1"]["kind"] = "decimal"
        c["fields"]["U2"]["kind"] = "decimal"
        typed = bind(x, b)
        self.assertEqual(typed["tables"]["Joint Displacements"]["rows"][0]["U1"], "0.015")
        self.assertEqual(typed["tables"]["Joint Displacements"]["rows"][0]["U2"], "-0.003")
        self.assertEqual(typed["tables"]["Joint Displacements"]["field_units"]["U1"], "m")
        self.assertEqual(typed["formal_compliance"], "NOT_PROVEN")
        verify(typed)

    def test_binding_rejects_wrong_units(self):
        x = capture(FakeSap(), action="capture", exact=("Joint Displacements",))
        b = make_template(x)
        b["status"] = "REVIEWED_EXACT_FIELDS"
        b["bindings"][0]["fields"]["U1"]["unit"] = "mm"
        with self.assertRaisesRegex(SourceError, "UNIT_MISMATCH"):
            bind(x, b)

    def test_binding_rejects_duplicate_identity(self):
        x = capture(FakeSap(), action="capture", exact=("Joint Displacements",))
        b = make_template(x)
        b["status"] = "REVIEWED_EXACT_FIELDS"
        b["bindings"][0]["identity"] = ["OutputCase"]
        with self.assertRaisesRegex(SourceError, "DUPLICATE_TYPED_ROW_IDENTITY"):
            bind(x, b)

    def test_exclusive_output_never_overwrites_evidence(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp)/"source.json"
            save_new(dest, {"key":"value"})
            with self.assertRaisesRegex(SourceError, "NO_OVERWRITE"):
                save_new(dest, {"key":"new"})


if __name__ == "__main__":
    unittest.main()
