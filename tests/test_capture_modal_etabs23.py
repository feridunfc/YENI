"""Mock ETABS tests for the VS01 Windows modal capture adapter."""
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "capture_modal_etabs23.py"
spec = importlib.util.spec_from_file_location("vs01_etabs_capture", MODULE_PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
from tbdy_next.source import parse_modal_capture
from tbdy_next.modal import evaluate_modal_mass


class DB:
    def __init__(self, *, cases=("LC_DL",), broken=False, bad_code=False):
        self.cases = tuple(cases)
        self.broken = broken
        self.bad_code = bad_code
        self.writes = []

    def GetLoadCasesSelectedForDisplay(self):
        return len(self.cases), list(self.cases), 0

    def SetLoadCasesSelectedForDisplay(self, values):
        self.writes.append(tuple(values))
        self.cases = tuple(v for v in values if v)
        return 0

    def GetTableForDisplayArray(self, *args):
        if self.bad_code:
            return [], 0, [], 0, [], 1
        fields = ["Case", "Mode", "UX", "UY", "SumUX", "SumUY"]
        flat = [
            "Modal", "1", "0.80", "0.78", "0.80", "0.78",
            "Modal", "2", "0.16", "0.18", "0.96", "0.96",
        ]
        if self.broken:
            flat.pop()
        return None, 1, fields, 2, flat, 0


class Sap:
    def __init__(self, db):
        self.DatabaseTables = db

    def GetModelFilename(self, full):
        assert full
        return "C:\\tmp\\kompakt_b.EDB"


class CaptureTests(unittest.TestCase):
    def test_capture_valid_and_restores_selection(self):
        db = DB()
        data = m.capture_modal(Sap(db), "Modal")
        self.assertEqual(db.cases, ("LC_DL",))
        self.assertEqual(db.writes, [("Modal",), ("LC_DL",)])
        table = parse_modal_capture(data, case="Modal")
        self.assertEqual(evaluate_modal_mass(table).numerical_status, "MEETS_NUMERICAL_CRITERION")
        self.assertFalse(data["capture_metadata"]["analysis_generation_proven"])

    def test_does_not_change_selection_when_modal_already_selected(self):
        db = DB(cases=("Modal", "RSX"))
        self.assertEqual(m.capture_modal(Sap(db), "Modal")["table"]["row_count"], 2)
        self.assertEqual(db.writes, [])

    def test_shape_error_still_restores(self):
        db = DB(broken=True)
        with self.assertRaises(m.ModalCaptureError):
            m.capture_modal(Sap(db), "Modal")
        self.assertEqual(db.cases, ("LC_DL",))

    def test_nonzero_api_rejected(self):
        db = DB(bad_code=True)
        with self.assertRaises(m.ModalCaptureError):
            m.capture_modal(Sap(db), "Modal")
        self.assertEqual(db.cases, ("LC_DL",))

    def test_empty_selection_restored_with_blank_name(self):
        db = DB(cases=())
        m.capture_modal(Sap(db), "Modal")
        self.assertEqual(db.cases, ())
        self.assertEqual(db.writes[-1], ("",))

    def test_case_must_be_exact(self):
        with self.assertRaises(m.ModalCaptureError):
            m.capture_modal(Sap(DB()), " Modal ")


if __name__ == "__main__":
    unittest.main()
