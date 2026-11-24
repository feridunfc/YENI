"""Section equilibrium and side identities independent of private model files."""

from unittest import TestCase

from tbdy_next.engineering.wall_shell_section import _line_element, recover_panel, uniform_edge_load
from tbdy_next.engineering.wall_transition import changes, section_plan
from tbdy_next.engineering.wall_transition_shell import _zone
from tbdy_next.wall_transition_report import transition_tables
from tbdy_next.wall_analysis_replay import pier_controls


class SectionRecoveryTests(TestCase):
    def test_reanalysis_controls_match_only_the_same_case_face_and_step(self):
        fields = dict.fromkeys(("P", "V2", "V3", "T", "M2", "M3"), "1.0000")

        def record(face, value):
            r = dict(
                fields,
                Pier="P",
                Story="L",
                Location=face,
                OutputCase="G",
                StepType="Single Value",
                P=value,
                CaseType="Combination",
            )
            return {
                "tables": {
                    "table_reads": {
                        "Pier Forces": {"rows": [r]},
                        "Pier Section Properties": {"rows": []},
                        "Area Assignments - Pier Labels": {"rows": []},
                    }
                }
            }

        original = record("Bottom", "1.0000")
        observed = record("Bottom", "1.0000")
        rows = observed["tables"]["table_reads"]["Pier Forces"]["rows"]
        rows[0].update(StepType=None, StepNum="0")
        rows.append(dict(rows[0], CaseType="LinStatic", OutputCase="Dead", P="-513.4"))
        controls = pier_controls(original, observed)
        self.assertEqual(
            (controls["rows"], controls["reported_rows"], controls["outside_tolerance"]), (1, 2, 0)
        )
        self.assertEqual(pier_controls(original, record("Bottom", "1.0001"))["outside_tolerance"], 0)
        self.assertEqual(pier_controls(original, record("Bottom", "1.0010"))["outside_tolerance"], 1)
        with self.assertRaisesRegex(ValueError, "SCOPE_DIFFERS"):
            pier_controls(original, record("Top", "1.0000"))

    def setUp(self):
        self.xyz = {"a": (1.0, 0.0, -2.0), "b": (3.0, 0.0, -2.0), "c": (3.0, 0.0, 0.0), "d": (1.0, 0.0, 0.0)}
        self.mesh = {"quad": ("a", "b", "c", "d")}
        self.basis = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
        self.panel = {"point_ids": ["a", "b", "c", "d"], "bottom_m": -2.0, "top_m": 0.0}

    def test_force_and_signed_first_moment_of_linear_axial_traction(self):
        fields = [[0.0, -10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, -20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
        action = _line_element([(1.0, 0.0, -1.0), (3.0, 0.0, -1.0)], fields, self.basis, (0.0, 0.0, -1.0))
        self.assertAlmostEqual(action[2], 30.0)
        self.assertAlmostEqual(action[4], -190.0 / 3)
        self.assertEqual(action[0:2], [0.0, 0.0])

    def test_both_faces_at_an_interior_plane_and_signed_shell_couples(self):
        # A constant positive M22 on the lower face acts about negative local 1.
        fields = {
            "corners": [["quad", p] for p in self.mesh["quad"]],
            "axes": {"quad": sum(self.basis, ())},
            "cases": {"Load": [[0.0, -z, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0] for z in (10.0, 10.0, 30.0, 30.0)]},
        }
        for retain_above in [True, False]:
            v = recover_panel(
                fields,
                self.mesh,
                self.xyz,
                self.panel,
                self.xyz,
                -1.0,
                retain_above,
                ["Load"],
                (2.0, 0.0, -1.0),
            )
            self.assertEqual(v["Load"], [0.0, 0.0, 40.0, -6.0, 0.0, 0.0])
        fields["corners"].pop()
        with self.assertRaises(ValueError):
            recover_panel(
                fields, self.mesh, self.xyz, self.panel, self.xyz, -1.0, True, ["Load"], (2.0, 0.0, -1.0)
            )

    def test_native_mesh_and_physical_plane_remain_distinct(self):
        band = {"bottom_m": -2.0, "top_m": -1.0, "members": ["wall"]}
        plan = section_plan(band, -1.0, "Below", {"wall": 2.0}, {"wall": self.mesh}, self.xyz)
        self.assertEqual((plan["z_m"], plan["element_face"], plan["at_transition"]), (-2.0, "Bottom", False))
        self.assertEqual(len(plan["corners"]["wall"]), 2)
        self.assertEqual(_zone((1.0, 0.0, -2.0), self.panel, self.xyz), "I Bottom")
        self.assertEqual(_zone((1.0, 0.0, -1.0), self.panel, self.xyz), "I")
        self.assertEqual(_zone((2.0, 0.0, -1.0), self.panel, self.xyz), "Interior")

    def test_uniform_edge_pressure_and_weight_keep_their_nodal_moment_arms(self):
        # At either horizontal edge two of the four bilinear weights contribute.
        loads = {
            "wall": {
                "surface_m2": 4.0,
                "combinations": [{"combination": "Load", "pressure_kn_m2": -5.0, "self_weight_kn": 40.0}],
            }
        }
        for face, nodes, expected in (
            ("Bottom", ["a", "b"], [0.0, 10.0, -20.0, 20.0, 40.0, 20.0]),
            ("Top", ["c", "d"], [0.0, -10.0, 20.0, 0.0, -40.0, -20.0]),
        ):
            plan = {"element_face": face, "corners": {"wall": [("quad", n) for n in nodes]}}
            applied = uniform_edge_load(
                plan,
                {"wall": self.mesh},
                self.xyz,
                {"wall": self.panel},
                self.xyz,
                loads,
                "Load",
                (0.0, 0.0, 0.0),
            )
            self.assertEqual(applied, expected)

    def test_equal_area_membership_change_still_has_two_sides(self):
        bands = [{"members": ["u", "v"]}, {"members": ["u", "x"]}, {"members": ["u", "x"]}]
        self.assertEqual([ids for _, _, ids in changes({"bands": bands})], [["v", "x"]])
        self.assertEqual(transition_tables([{"pier": "old", "story": "L"}]), {})
