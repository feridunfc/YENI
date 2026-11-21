import unittest

from tbdy_next.engineering.column_clear_length import project_column_clear_lengths
from tbdy_next.engineering.column_mat_support import BOUND, project_mat_horizontal_supports
from tbdy_next.engineering.column_r10_live import _build_frame_catalog
from tbdy_next.etabs_geometry import POINT_RESTRAINT_SCHEMA, capture_point_restraints
from tbdy_next.etabs_source_gateway_windows import seal
from test_column_clear_length import fixture, table


def setup():
    source, _, scope = fixture()
    source["column_axial"]["r10_source"]["point_restraints"] = {
        "schema": POINT_RESTRAINT_SCHEMA, "point_ids": ["P0"], "errors": {},
        "observations": {"P0": {"local_dof": [True, True, False, False, False, False],
                                "axes_angles_deg": [0., 0., 0.], "advanced_axes": False}},
    }
    disp = table("UniqueName OutputCase CaseType StepType StepNumber Ux Uy", [
        ("P0", "RSX", "LinRespSpec", "Max", "None", "0", "0"),
        ("P0", "RSY", "LinRespSpec", "Max", "None", "0", "0"),
        ("P1", "RSX", "LinRespSpec", "Max", "None", ".001956", ".001"),
        ("P1", "RSY", "LinRespSpec", "Max", "None", ".001", ".001931"),
    ], units={"Ux": "m", "Uy": "m"})
    raw = {"model": source["capture_metadata"]["model_filename"], "model_locked": True, "model_units_code": 6,
           "model_units_unchanged": True, "selection_restored": True, "case_selection_before": [],
           "case_selection_after": [], "table_reads": {"Joint Displacements": disp}}
    source["vs05_delta_source"] = seal(raw)
    return source, scope


def evaluate(source, scope):
    frames, _, meta = _build_frame_catalog(source)
    faces = project_column_clear_lengths(source, frames, meta["adjacency"], ["C"], scope)
    return project_mat_horizontal_supports(source, faces["per_member"])["C"]


class ColumnMatSupportTests(unittest.TestCase):
    def test_kinematic_restraint_and_displacements(self):
        source, scope = setup()
        got = evaluate(source, scope)
        self.assertEqual(got["status"], BOUND)
        self.assertEqual(got["mat_analysis_elements"], {"M": ["M-1"]})
        self.assertFalse(got["global_dof_restrained"]["RX"])
        self.assertFalse(got["global_dof_restrained"]["RY"])
        self.assertEqual(got["spectral_joint_reference"]["X"]["relative_m"], .001956)
        self.assertEqual(got["spectral_joint_reference"]["Y"]["relative_m"], .001931)

    def test_foundation_remains_known_when_the_force_cut_span_is_unresolved(self):
        source, scope = setup()
        scope["configured_output_cuts"].clear()
        self.assertEqual(evaluate(source, scope)["status"], BOUND)

    def test_horizontal_rotation_preserves_xy_and_tilt_does_not(self):
        source, scope = setup()
        row = source["column_axial"]["r10_source"]["point_restraints"]["observations"]["P0"]
        row["axes_angles_deg"][0] = 20
        self.assertEqual(evaluate(source, scope)["status"], BOUND)
        row["axes_angles_deg"][1] = 20
        self.assertEqual(evaluate(source, scope)["reason"], "HORIZONTAL_X_AND_Y_RESTRAINT_REQUIRED")
        row["axes_angles_deg"] = [0, 0, 0]
        row["local_dof"][1] = False
        self.assertEqual(evaluate(source, scope)["reason"], "HORIZONTAL_X_AND_Y_RESTRAINT_REQUIRED")

    def test_a_nonzero_base_record_is_not_subtracted_from_a_spectral_maximum(self):
        source, scope = setup()
        snap = source["vs05_delta_source"]
        snap["table_reads"]["Joint Displacements"]["rows"][0]["Ux"] = ".0001"
        source["vs05_delta_source"] = seal({k: v for k, v in snap.items() if k != "payload_sha256"})
        got = evaluate(source, scope)
        self.assertEqual(got["reason"], "NONZERO_RESTRAINED_BASE_DISPLACEMENT")
        self.assertNotIn("X", got["spectral_joint_reference"])

    def test_capture_reads_point_restraints_and_axes(self):
        class Native:
            @staticmethod
            def GetRestraint(uid, _):
                return ((True, True, False, False, False, False), 0 if uid == "P0" else 1)

            @staticmethod
            def GetLocalAxes(uid, *_):
                return (0., 0., 0., False, 0)

        class Sap:
            PointObj = Native()

        result = capture_point_restraints(Sap(), ("P0", "bad"))
        self.assertEqual(result["observations"]["P0"]["local_dof"], [True, True, False, False, False, False])
        self.assertIn("bad", result["errors"])
