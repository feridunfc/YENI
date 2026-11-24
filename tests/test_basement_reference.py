"""Checks on the basement ratio and the observed two directional modal masses."""
import unittest

from tbdy_next.engineering.basement_matrices import _model_lines
from tbdy_next.engineering.basement_reference import _dominant, _period_decision


class BasementReferenceTests(unittest.TestCase):
    def setUp(self):
        self.full = [
            {"mode": 1, "period_s": .4698506312, "X": .697444179, "Y": .025930625},
            {"mode": 2, "period_s": .4406171180, "X": .014330569, "Y": .643513384}]
        self.upper = [
            {"mode": 1, "period_s": .4575457886, "X": .889208101, "Y": .027611173},
            {"mode": 2, "period_s": .4317844230, "X": .015299441, "Y": .816708480}]
        self.native = [
            {"direction": "X", "full_period_s": .46985063753970846, "full_participating_ratio": .6974},
            {"direction": "Y", "full_period_s": .4406171030174019, "full_participating_ratio": .6435}]

    def test_two_axes_select_their_own_dominant_mode(self):
        rows = _period_decision(self.native, {"full": self.full[::-1], "upper": self.upper})
        self.assertEqual([r["upper_mode"] for r in rows], [1, 2])
        self.assertAlmostEqual(rows[0]["period_ratio"], 1.0268931392)
        self.assertAlmostEqual(rows[1]["period_ratio"], 1.0204562613)
        self.assertEqual([r["status"] for r in rows], ["SATISFIED", "SATISFIED"])

    def test_boundary_and_exceedance(self):
        self.upper[0]["period_s"] = self.full[0]["period_s"] / 1.1
        self.upper[1]["period_s"] = self.full[1]["period_s"] / 1.11
        rows = _period_decision(self.native, {"full": self.full, "upper": self.upper})
        self.assertEqual([r["status"] for r in rows], ["LIMIT_REQUIRES_REVIEW", "EXCEEDED"])

    def test_unresolved_dominance_and_native_control(self):
        self.full[0]["X"] = .25
        with self.assertRaisesRegex(ValueError, "DOMINANT_MODE_NOT_SEPARATED"):
            _dominant(self.full, "X")
        self.full[0]["X"] = .75
        with self.assertRaisesRegex(ValueError, "DIFFERS_FROM_NATIVE_RITZ"):
            _period_decision(self.native, {"full": self.full, "upper": self.upper})

    def test_model_comparison_retains_physical_records_and_ignores_save_history(self):
        model = b'$ File source\n  UNITS "KN" "M" "C"\n$ LOG\n  END\n'
        saved = model.replace(b"source", b"copy").replace(b"  END", b"ETABS UltimateC 23.2.0 File saved as private.EDB\n  END")
        self.assertEqual(_model_lines(saved), _model_lines(model))
        self.assertNotEqual(_model_lines(saved.replace(b'"KN"', b'"TF"')), _model_lines(model))
