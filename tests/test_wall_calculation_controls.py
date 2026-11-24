"""Discriminating force, geometry and reinforcement examples for the wall calculation owners."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tbdy_next.column_engine.section_capacity import Material, Section, perimeter
from tbdy_next.engineering.basement_joint_layout import level_grid
from tbdy_next.engineering.frame_storey_design import wall_compression_scope
from tbdy_next.engineering.pier_height_design import _branch
from tbdy_next.engineering.pier_seismic_shear import upper_shear
from tbdy_next.engineering.wall_interface_transfer import _polygon
from tbdy_next.engineering.wall_section import _gravity_check
from tbdy_next.engineering.wall_transition import _periodic_jumps
from tbdy_next.engineering.wall_transition_shell import field_control
from tbdy_next.wall_modal_capture import _point_basis
from tbdy_next.wall_transition_capture import _shell_fields


class WallCalculationControls(unittest.TestCase):
    def test_signed_cut_compression_and_shear_exceedance_are_independent(self):
        bars, _, _ = perimeter(800, 400, 40, 10, 16, 5, 3)
        section = Section(800, 400, tuple(bars), Material(35, 35 / 1.5, 500 / 1.15))
        detail = {"vr_kn": 100., "solid_strut_limit_kn": 130., "coupled_strut_limit_kn": 115.}
        forces = {"P": -100., "M2": 0., "M3": 0., "V2": -50.}
        low = _gravity_check(section, detail, forces)
        self.assertEqual((low["compression_kn"], low["v2_over_vr"], low["status"]), (100., .5, "GRAVITY_CUT_CALCULATED"))
        high = _gravity_check(section, detail, {**forces, "V2": -101.})
        self.assertEqual(high["pmm_ratio"], low["pmm_ratio"])
        self.assertEqual(high["status"], "NUMERICAL_EXCEEDANCE")

    def test_frame_only_fraction_requires_all_signed_bottom_cuts(self):
        frames = {"storeys": {"s": {"compression_kn": {"G": 700.}}}}
        cut = {"role": "ASSIGNED_STATIC", "combination": "G", "face": "Bottom", "force_basis": "SIGNED_STATIC", "compression_kn": 300.}
        wall = {"pier": "P", "story": "s", "cuts": [cut, {**cut, "face": "Top"}]}
        self.assertEqual(wall_compression_scope(frames, [wall])[0]["omitted_compression_fraction"], .3)
        incomplete = wall_compression_scope(frames, [wall, {"story": "s", "pier": None, "cuts": []}])[0]
        self.assertEqual((incomplete["expected_pier_groups"], incomplete["evaluated_pier_groups"]), (2, 1))
        self.assertIsNone(incomplete["omitted_compression_fraction"])

    def test_point_local_axes_require_matching_position_and_resolved_orientation(self):
        api = Mock(spec=["GetCoordCartesian", "GetLocalAxes"])
        api.GetCoordCartesian.return_value = [2., 3., 4., 0]
        api.GetLocalAxes.return_value = [0., 0., 0., 0]
        sap = SimpleNamespace(PointElm=api)
        _, axes = _point_basis(sap, "p", [2., 3., 4.])
        self.assertEqual(axes, [1.,0.,0.,0.,1.,0.,0.,0.,1.])
        with self.assertRaisesRegex(ValueError, "COORDINATES_DIFFER"):
            _point_basis(sap, "p", [2., 3., 4.1])
        api.GetLocalAxes.return_value = [45., 0., 0., 0]
        with self.assertRaisesRegex(ValueError, "POINT_AXES_REQUIRED"):
            _point_basis(sap, "p", [2., 3., 4.])

    def test_wall_face_reversal_changes_pressure_sign_and_preserves_area_and_centroid(self):
        points = [(10,2,1), (14,2,1), (14,2,4), (10,2,4)]
        for polygon, sign in ((points, -1), (points[::-1], 1)):
            self.assertEqual(_polygon(polygon), (12., [12., 2., 2.5], sign))
        with self.assertRaisesRegex(ValueError, "OUT_OF_PLANE"):
            _polygon([*points[:3], (10, 2.1, 4)])

    def test_shell_fields_require_unique_signed_element_corners(self):
        api = Mock()
        unit_axes = [1., 0., 0., 0., 1., 0., 0., 0., 1.]
        api.AreaElm.GetTransformationMatrix.return_value = [unit_axes, 0]
        row = ["w", "elm", "j", "G", "Static", 0, *range(6, 23)]

        def result(rows):
            return [len(rows), *(list(values) for values in zip(*rows)), 0]

        api.Results.AreaForceShell.return_value = result([row])
        fields = _shell_fields(api, "w", {("elm", "j")}, ["G"])
        self.assertEqual(fields["cases"]["G"], [[6,7,8,13,14,15,19,20]])
        self.assertEqual(fields["axes"]["elm"], unit_axes)
        for rows in ([row, row], [[*row[:4], "Max", *row[5:]]]):
            api.Results.AreaForceShell.return_value = result(rows)
            with self.assertRaisesRegex(ValueError, "INVALID_SIGNED_SHELL_FIELD"):
                _shell_fields(api, "w", {("elm", "j")}, ["G"])

    def test_anchorage_grid_observes_actual_clear_spacing(self):
        policy = {"height": 3000., "module": 40., "phase": 0., "start": 48., "inner": False, "aggregate_mm":16.}
        grid = level_grid(policy, 14, 50, 40)
        self.assertEqual((grid["pitch_mm"], grid["clear_spacing_mm"]), (40., 26.))
        self.assertGreaterEqual(grid["minimum_in_any_full_metre"], 20)
        self.assertEqual(level_grid({**policy, "module": 38.}, 14, 50, 40), {})

    def test_seismic_shear_uses_validated_amplified_range_once(self):
        def pair(lo, hi):
            return [dict(CaseType="Combination", StepType=s, P=0, M2=0, M3=0, V2=v, V3=0, T=0)
                    for s, v in (("Min", lo), ("Max", hi))]
        key = ("P", "s", "Bottom")
        groups = {(*key, "E"): pair(-10, 30), (*key, "Cap"): pair(-30, 50)}
        scope = {"controls": {"E": {"combination":"Cap", "d_factor":2}}, "native_seismic":{"E":{}}}
        detail = {"vr_kn":100., "solid_strut_limit_kn":110., "coupled_strut_limit_kn":120.}
        def solve():
            return upper_shear(scope, "E", groups, key, {"Cap"}, detail, (0., 0.))
        result = solve()
        self.assertEqual(result["cap_radius_kn"], 40.)
        self.assertAlmostEqual(result["branches"]["solid"]["ve_upper_kn"], 58.0022)
        groups[(*key, "Cap")] = pair(-29, 49)
        with self.assertRaisesRegex(ValueError, "AMPLIFIED_PIER_V2_ENVELOPE_CONTROL_DIFFERS"):
            solve()

    def test_field_error_uses_absolute_and_relative_units_per_component(self):
        ref = [100., 1000., 0., 0., -2000., 20.]
        self.assertEqual(field_control(ref,[5., 20., 0., -5., 40., 1.])["failed_components"], [])
        self.assertEqual(field_control(ref,[5.01, 20., 0., -5., -40.01, 1.])["failed_components"], ["FX","MY"])
        with self.assertRaisesRegex(ValueError, "INVALID_FIELD_CONTROL"):
            field_control(ref, [float("nan")] * 6)

    def test_modewise_face_jump_includes_opposing_signs(self):
        bank = {"expected_modal_modes": {"M":[1]}}
        ends = ("below","above")
        primitive = {("M","Mode",1): {"below":[-4.] * 6,"above":[4.] * 6},
                     ("X","Max",0): {"below":[8.] * 6,"above":[8.] * 6}}
        source = {"X": ("X", [2.], [.5], .05, 0.)}
        with patch("tbdy_next.engineering.wall_modal_balance._case_modes", return_value=source):
            result = _periodic_jumps(bank, {}, primitive, ends)["X"]
            self.assertTrue(result["native_zero_eccentricity_faces_verified"])
            self.assertEqual(result["amplitudes_kn_knm"], [16.] * 6)
            del primitive["M","Mode",1]["above"]
            with self.assertRaisesRegex(ValueError, "BOTH_JAMB_FACES_REQUIRED"):
                _periodic_jumps(bank, {}, primitive, ends)

    def test_figure_712_base_retains_larger_force_above_base(self):
        rows = [dict(member=m, face=f, z_m=z, solid=v, coupled=v, m2=10., m3=20.) for m, f, z, v in [
            ("lower","Bottom",0.,80.), ("lower","Top",3.,60.), ("upper","Bottom",3.,140.), ("upper","Top",6.,40.)]]
        result = _branch(rows, rows[0], {"reference_z_m":0., "wall_height_mm":6000., "minimum_hcr_mm":1500.}, 6.)
        self.assertEqual(result["solid"]["ve_upper_kn"], 140.)
        self.assertEqual(result["solid"]["base_upper_kn"], 140.)
