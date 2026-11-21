"""Independent full-span field and error-budget checks."""

from copy import deepcopy
from math import sqrt
import unittest

from tbdy_next.column_engine.column_kinematics import COMPONENTS, COORDINATE_CONTRACT
from tbdy_next.engineering.gravity_deformation import (
    KINEMATICS_BASIS, SCHEMA, UNITS, UNVERIFIED, compare_recovered, recover_level,
)


CASES = {"Grav_Ult": {"second": "ULT_P"}}
AXES = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]
CLEAR = (0.4, 3.6)
EI = 5000.0
GA = 8000.0
STIFFNESS = {axis: {"etabs_ei_nmm2": EI * 1e9} for axis in ("M2", "M3")}


def analytical_motion(z):
    """Manufactured cubic displacement, nonzero Timoshenko shear, rigid tips.

    The polynomial is prescribed independently of recovery. In the flexible
    region q has a constant third derivative, so the analytical shear
    strain is -EI*q'''/GA, and section rotation is q' minus this strain.
    Extend translations by the section rotation inside a rigid tip.
    """
    a, b, c = .001, .0003, -.00015
    left, right = .2, 3.8
    shear = -6 * c * EI / GA
    x = min(max(z, left), right) - left
    q = a*x + b*x*x + c*x**3
    rotation = a + 2*b*x + 3*c*x*x - shear
    q += rotation * (z - (left + x))
    return q, rotation


def analytical_peak():
    a, b, c = .001, .0003, -.00015
    u_i, u_j = analytical_motion(0)[0], analytical_motion(4)[0]
    chord_slope = (u_j - u_i) / 4
    # The positive root of q'(x) = chord slope lies in the clear interval.
    x = (-2*b - sqrt((2*b)**2 - 12*c*(a - chord_slope))) / (6*c)
    z = .2 + x
    peak = 1000 * (analytical_motion(z)[0] - u_i - chord_slope*z)
    return z - CLEAR[0], peak


def frame_fixture(divisions):
    low, high = CLEAR
    coordinates = [0, *(low + (high-low)*i/divisions for i in range(1, divisions)), 4]
    points = ["I", *(f"N_{divisions}_{i}" for i in range(1, divisions)), "J"]
    mesh, metadata = [], {}
    for i, (a, b) in enumerate(zip(coordinates, coordinates[1:])):
        eid = f"E_{divisions}_{i}"
        mesh.append({"element": eid, "i_joint": points[i], "j_joint": points[i+1],
                     "i_xyz": [0, 0, a], "j_xyz": [0, 0, b]})
        metadata[eid] = {"axes_global": AXES, "offsets_m": [max(0, low-a), max(0, b-high)],
                         "rigid_end_factor": .5, "kinematics_basis": KINEMATICS_BASIS,
                         "ei_knm2": [EI, EI], "ga_kn": [GA, GA]}
    response = {}
    for point, z in zip(points, coordinates):
        translation, rotation = analytical_motion(z)
        response[point] = dict(zip(COMPONENTS, [translation, 0, 0, 0, rotation, 0]))
    level = {"divisions": divisions, "analysis_generation": f"test-gen-{divisions}", "model_sha256": str(divisions) * 64}
    level["kinematics"] = {
        "schema": SCHEMA, "model_sha256": level["model_sha256"], "analysis_generation": level["analysis_generation"],
        "case_step": ["Step", 1.0], "coordinate_contract": COORDINATE_CONTRACT,
        "units": UNITS, "translation_error_m": 0, "rotation_error_rad": 0,
        "members": {"225": {"joints": {"ULT_P": response}, "elements": metadata}},
    }
    return level, mesh


def recover(level, mesh, cases=CASES):
    return recover_level(level, "225", mesh, cases, *CLEAR, STIFFNESS)


class FullSpanDeformationTests(unittest.TestCase):
    def test_known_interior_peak_with_nonzero_shear_and_rigid_offsets(self):
        calculated = [recover(*frame_fixture(i)) for i in (4, 8)]
        station, magnitude = analytical_peak()
        for result in calculated:
            self.assertEqual(result["status"], "FULL_SPAN_RECOVERED")
            peak = result["cases"]["Grav_Ult"]["peak"]
            self.assertLess(abs(peak["value_mm"] - magnitude), 1e-5)
            self.assertLess(peak["station_bracket_m"][0], station)
            self.assertGreater(peak["station_bracket_m"][1], station)
            self.assertGreater(peak["signed_xy_mm"][0], 0)
            self.assertEqual(peak["signed_xy_mm"][1], 0)
        result = compare_recovered(*calculated, .01)
        self.assertIs(result["within_tolerance"], True)
        row = result["cases"]["Grav_Ult"]
        self.assertEqual(row["withheld_joint_count"], 4)
        self.assertLess(row["withheld_joint_max"]["norm_mm"], 1e-10)
        self.assertLess(row["max_vector_difference"]["value_mm"], 1e-10)
        self.assertLess(row["error_budget"]["total_mm"], .01)

    def test_rotation_changes_fine_field_and_reports_calculated_excess(self):
        baseline = recover(*frame_fixture(4))
        level, mesh = frame_fixture(8)
        pitch = level["kinematics"]["members"]["225"]["joints"]["ULT_P"]["N_8_3"]
        pitch["Rx"] += .003
        perturbed = recover(level, mesh)
        result = compare_recovered(baseline, perturbed, .01)
        self.assertIs(result["within_tolerance"], False)
        row = result["cases"]["Grav_Ult"]
        self.assertGreater(row["max_vector_difference"]["value_mm"], .01)
        self.assertGreater(abs(row["max_component_differences"]["Y"]["signed_xy_mm"][1]), .01)
        self.assertLess(abs(row["max_component_differences"]["X"]["signed_xy_mm"][0]), 1e-10)
        self.assertLess(row["withheld_joint_max"]["norm_mm"], 1e-10)

    def test_generation_units_axes_and_end_conditions_fail_closed(self):
        source, mesh = frame_fixture(4)
        corruptions = [
            ("GRAVITY_DEFORMATION_MODEL_OR_GENERATION_MISMATCH",
             lambda raw: raw.update(analysis_generation="different-generation")),
            ("GRAVITY_DEFORMATION_CASE_STEP_AXES_OR_UNITS_UNBOUND",
             lambda raw: raw.update(units={**UNITS, "rotational": "degree"})),
            ("GRAVITY_DEFORMATION_ELEMENT_TRANSFORMATION_UNSUPPORTED",
             lambda raw: raw["members"]["225"]["elements"]["E_4_0"].update(kinematics_basis="PANEL_ZONE_UNBOUND")),
            ("GRAVITY_DEFORMATION_OFFSETS_INCONSISTENT",
             lambda raw: raw["members"]["225"]["elements"]["E_4_0"].update(offsets_m=[0, 0])),
            ("GRAVITY_DEFORMATION_EI_REVISION_MISMATCH",
             lambda raw: raw["members"]["225"]["elements"]["E_4_0"].update(ei_knm2=[EI, EI * 1.1])),
        ]
        for code, corrupt in corruptions:
            with self.subTest(reason=code):
                level = deepcopy(source)
                corrupt(level["kinematics"])
                result = recover(level, mesh)
                self.assertEqual(result["status"], UNVERIFIED)
                self.assertEqual(result["reason"], code)
                self.assertEqual(result["recovered_case_count"], 0)

    def test_legacy_translations_and_missing_joint_rotations_are_unverified(self):
        level, mesh = frame_fixture(4)
        old = {k: v for k, v in level.items() if k != "kinematics"}
        old["joint_displacements"] = {"225": {"ULT_P": {row["i_joint"]: [0., 0., 0.] for row in mesh}}}
        previous = recover(old, mesh)
        self.assertEqual(previous["reason"], "GRAVITY_DEFORMATION_KINEMATICS_UNAVAILABLE")
        del level["kinematics"]["members"]["225"]["joints"]["ULT_P"]["I"]["Ry"]
        current = recover(level, mesh)
        self.assertEqual(current["cases"]["Grav_Ult"]["reason"], "GRAVITY_DEFORMATION_SIX_DOF_REQUIRED")
        output = compare_recovered(previous, current, .01)
        self.assertIsNone(output["within_tolerance"])
        self.assertEqual(output["cases"]["Grav_Ult"]["status"], UNVERIFIED)

    def test_duplicate_mesh_element_or_native_case_identity_is_rejected(self):
        level, mesh = frame_fixture(4)
        duplicate = deepcopy(mesh)
        duplicate[1]["element"] = duplicate[0]["element"]
        self.assertEqual(recover(level, duplicate)["reason"], "GRAVITY_DEFORMATION_MESH_IDENTITIES_OR_FACES_INCONSISTENT")
        cases = {**CASES, "Duplicate": CASES["Grav_Ult"]}
        self.assertEqual(recover(level, mesh, cases)["reason"], "GRAVITY_DEFORMATION_MESH_IDENTITIES_OR_FACES_INCONSISTENT")
