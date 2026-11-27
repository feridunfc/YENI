"""Physical coverage and calculation boundaries for column-supported basement webs."""
import math
import unittest

from tbdy_next.column_engine.section_capacity import Material
from tbdy_next.engineering.basement_pier_design import _allocate, _section_terms, basement_coverage, basement_piers
from tbdy_next.engineering.basement_pier_geometry import _bounds, _union
from tbdy_next.engineering.basement_wall_pressure import panel_pressure_design, vertical_section
from tbdy_next.reporting import _basement_pier_tables


class BasementWebTests(unittest.TestCase):
    def test_fold_overlap_and_clear_section_are_different(self):
        web = _bounds((0, 0), (3, 0), .4)
        corner = _bounds((3, 0), (3, 8), .4)
        self.assertAlmostEqual(_union([web, corner]), (3 + 8)*.4 - .04)
        with self.assertRaisesRegex(ValueError, "ORTHOGONAL"):
            _bounds((0, 0), (3, 1), .4)

    def test_stress_first_moments_at_native_origin_and_when_translated(self):
        # Two rectangles of equal area at right angles. The imposed axial stress
        # is 360 + 5x - 7y (kN/m²) in the reference coordinate system.
        panels = [dict(member="a", width_direction=[1, 0], clear_centroid_xy_m=[1, 0]),
                  dict(member="b", width_direction=[0, 1], clear_centroid_xy_m=[2, 1])]
        for panel in panels:
            panel.update(clear_length_m=2., thickness_m=.4)
        area = .8
        axial = [area*365, area*(360+10-7)]
        strong = [area*4/12*5, area*4/12*(-7)]
        weak = [area*.16/12*(-7), area*.16/12*(-5)]
        total = sum(axial)
        qx = axial[0] + 2*axial[1] + strong[0] - weak[1]
        qy = axial[1] + weak[0] + strong[1]
        geom = dict(native_axes_2_xy=[1,0], net_centroid_xy_m=[1.5,.5],
                    panels=panels, clear_web_area_m2=1.6)
        for x, y in ((0., 0.), (102., 11.)):
            terms, inertia = _section_terms(geom, [x,y,0.])
            result, error = _allocate(terms, inertia, total, qx-total*x, qy-total*y)
            self.assertLess(max(map(abs, error)), 1e-8)
            for i, uid in enumerate(("a", "b")):
                for expected, observed in zip((axial[i], weak[i], strong[i]), result[uid]):
                    self.assertAlmostEqual(expected, observed, places=8)

    def test_eight_metre_web_pressure_strip_and_detail(self):
        panel = {"member":"460", "span_m":8., "clear_length_m":7.2, "thickness_m":.4}
        combos = {"NoPressure": {"pressure_kn_m2":{"460":0.}},
                  "Soil": {"pressure_kn_m2":{"460":-55.56}}}
        mat = Material(35., 35./1.5, 500./1.15)
        h = panel_pressure_design(panel, combos, 40., mat, 5.15)
        self.assertEqual((h["governing"], h["diameter_mm"], h["maximum_pitch_mm"]), ("Soil",22,100))
        self.assertAlmostEqual(h["cuts"][1]["moment_bound_knm_m"], 444.48)
        self.assertAlmostEqual(h["cuts"][1]["reaction_bound_kn_m"], 277.8)
        self.assertAlmostEqual(h["diagonal_cracking_kn_m"], .65*.35*math.sqrt(35)/1.5*(400-40-33))
        self.assertLess(max(h["cuts"][1][k] for k in ("moment_ratio","cracking_shear_ratio")), 1.)
        sec, v = vertical_section(panel,h,40.,mat,12,200)
        self.assertEqual((len(sec.bars), v["stations_per_face"], v["crossties"]), (72,36,1872))
        self.assertGreaterEqual(v["min_crossties_full_m2"], 4)

    def test_missing_capture_preserves_physical_and_unclassified_load_scope(self):
        walls = [{"member_id":uid, "pier":"yP1","story":"+0.00"} for uid in ("443","460","461","463","473")]
        scope = {"native_static":{"Grav_Ult":{}}, "native_seismic":{}, "other":["Unresolved"]}
        groups = basement_piers({}, {}, {"walls":walls}, {}, scope)
        count = basement_coverage(groups)
        self.assertEqual((count["assigned_cuts_evaluated"], count["assigned_cuts_expected"]), (0,4))
        self.assertEqual((count["scheduled_panels"], count["physical_panels"]), (0,5))
        self.assertEqual(count["assigned_pressure_panel_combinations_expected"], 10)
        self.assertIn("ORIGINAL_PIER_SECTION_AND_FORCE_SOURCE_REQUIRED", _basement_pier_tables({"basement_piers":groups}))
        self.assertEqual(_basement_pier_tables({}), "")

    def test_stepped_pier_face_allocation_and_spandrel_elevation_offset(self):
        from tbdy_next.engineering.basement_joint_layout import _families, layout_policy, level_grid
        from tbdy_next.engineering.basement_pier_design import _cut

        p1 = dict(member="w1", wall="W21", joint_i="a", joint_j="b", bottom_m=-5.15, top_m=0.0,
                  span_m=7.0, clear_length_m=6.2, thickness_m=0.4, width_direction=[1.0, 0.0],
                  clear_centroid_xy_m=[3.5, 0.0])
        p2 = dict(member="w2", wall="W22", joint_i="b", joint_j="c", bottom_m=-1.50, top_m=0.0,
                  span_m=3.4, clear_length_m=3.0, thickness_m=0.4, width_direction=[1.0, 0.0],
                  clear_centroid_xy_m=[8.9, 0.0])
        p3 = dict(member="w3", wall="W24", joint_i="d", joint_j="e", bottom_m=-5.15, top_m=0.0,
                  span_m=7.0, clear_length_m=6.2, thickness_m=0.4, width_direction=[1.0, 0.0],
                  clear_centroid_xy_m=[14.5, 0.0])
        geom = dict(
            panels=[p1, p2, p3], bottom_m=-5.15, top_m=0.0, stepped=True,
            native_axes_2_xy=[1.0, 0.0],
            native_face_origins_m={"Bottom": [9.0, 0.0, -5.15], "Top": [8.97, 0.0, 0.0]},
            face_sections={
                "Bottom": {"members": ["w1", "w3"], "clear_web_area_m2": 4.96, "net_centroid_xy_m": [9.0, 0.0]},
                "Top": {"members": ["w1", "w2", "w3"], "clear_web_area_m2": 6.16,
                        "net_centroid_xy_m": [(2.48*3.5 + 1.20*8.9 + 2.48*14.5)/6.16, 0.0]},
            },
            clear_web_area_m2=6.16, net_centroid_xy_m=[9.0, 0.0],
        )
        bound = {"groups": {
            ("xP2", "+0.00", "Bottom", "G"): [{"CaseType": "Combination", "StepType": "", "P": -1200.0, "V2": 0.0, "V3": 0.0, "T": 0.0, "M2": 40.0, "M3": 350.0}],
            ("xP2", "+0.00", "Top", "G"): [{"CaseType": "Combination", "StepType": "", "P": -900.0, "V2": 0.0, "V3": 0.0, "T": 0.0, "M2": 25.0, "M3": 210.0}],
        }}
        bot = _cut(geom, bound, "xP2", "+0.00", "Bottom", "G", {"spectral": False, "role": "WALL_STRENGTH"})
        top = _cut(geom, bound, "xP2", "+0.00", "Top", "G", {"spectral": False, "role": "WALL_STRENGTH"})
        self.assertEqual([d["member"] for d in bot["web_demands"]], ["w1", "w3"])
        self.assertEqual([d["member"] for d in top["web_demands"]], ["w1", "w2", "w3"])
        self.assertLess(max(bot["equilibrium_error_kn_knm"] + top["equilibrium_error_kn_knm"]), 1e-8)

        pol_spandrel = layout_policy(geom, p2, 40.0, 20.0)
        pol_full = layout_policy(geom, p1, 40.0, 20.0)
        self.assertAlmostEqual(pol_spandrel["base_offset_mm"], 3650.0)
        hg_s = level_grid(pol_spandrel, 14, 100, 40.0)
        hg_f = level_grid(pol_full, 14, 100, 40.0)
        self.assertAlmostEqual(hg_s["base_offset_mm"], 3650.0)
        end_stub = {"column_depth_mm": 800.0, "specified_embedment_mm": 650.0,
                    "transfer": {"diameter_mm": 14, "offset_each_side_mm": 42.75, "column_embedment_mm": 650.0, **hg_s}}
        fams = list(_families({**p2, "horizontal": {**hg_s, "diameter_mm": 14, "cover_mm": 40.0, "curtain_inset_mm": 0.0}}, "I", end_stub))
        self.assertGreater(fams[0]["heights"][0], 3690.0)
        self.assertLess(fams[0]["heights"][-1], 5110.0)
        # Every spandrel bar sits on the exact same vertical lattice module as the full-height web.
        rem = (fams[0]["heights"][0] - hg_f["first_station_mm"]) / hg_f["pitch_mm"]
        self.assertAlmostEqual(rem, round(rem), places=7)

    def test_exterior_vertical_curtain_respects_cover_and_restores_lever_arm(self):
        from tbdy_next.engineering.wall_membrane_design import check_curtains

        panel = {"member": "438", "span_m": 3.6, "clear_length_m": 3.2, "thickness_m": 0.4, "folded_pier_length_m": 35.0}
        mat = Material(35.0, 35.0/1.5, 500.0/1.15, 200000.0)
        h_inset = {"diameter_mm": 12, "pitch_mm": 49.57, "layers": 102, "guaranteed_bars_per_m": 19,
                   "cover_mm": 40.0, "curtain_inset_mm": 11.67, "physical_height_mm": 5150.0}
        _, v_in = vertical_section(panel, h_inset, 40.0, mat, 16, 100, exterior=False)
        _, v_out = vertical_section(panel, h_inset, 40.0, mat, 16, 100, exterior=True)
        self.assertEqual(v_out["curtain_position"], "EXTERIOR_OUTSIDE_HORIZONTAL")
        self.assertLessEqual(v_out["offset_mm"] + 8.0 + 40.0, 200.0 + 1e-7)
        states = {"C": [("e1", "p1", [(-200.0, -50.0), (-1250.0, -250.0), (-180.0, -20.0)],
                         [(-25.0, -25.0), (-145.0, -130.0), (-9.0, -7.0), (-10.0, -8.0), (-125.0, -120.0)])]}
        lane = 200.0 - 40.0 - 11.67 - 18.0
        chk_in = check_curtains(states, {}, 400.0, h_inset, v_in, mat, lane)
        chk_out = check_curtains(states, {}, 400.0, h_inset, v_out, mat, lane, vertical_offset_mm=v_out["offset_mm"])
        self.assertFalse(chk_in["satisfied"])
        self.assertTrue(chk_out["satisfied"])
        self.assertGreater(chk_out["lever_arm_mm"], chk_in["lever_arm_mm"])
        # Counterexample: without horizontal inset, placing Ø16 outside Ø12 violates 40 mm nominal cover (142 + 14 + 8 + 40 = 204 > 200).
        with self.assertRaisesRegex(ValueError, "VERTICAL_WEB_GRID_DOES_NOT_FIT"):
            vertical_section(panel, {**h_inset, "curtain_inset_mm": 0.0}, 40.0, mat, 16, 100, exterior=True)

    def test_cross_pier_shared_column_preserves_clear_corner_and_demotes_clash(self):
        from copy import deepcopy
        from tbdy_next.engineering.basement_pier_design import _verify_cross_pier_supports

        def make_pier(pier_name, uid, direction, side, first_mm, scheduled=True):
            h = {"diameter_mm": 12, "pitch_mm": 50.0, "first_station_mm": first_mm, "layers": 10,
                 "cover_mm": 40.0, "curtain_inset_mm": 12.0}
            tr = {"diameter_mm": 12, "pitch_mm": 50.0, "first_station_mm": first_mm, "layers": 10,
                  "offset_each_side_mm": 42.75, "column_embedment_mm": 600.0}
            end = {"column": "215", "column_depth_mm": 800.0, "specified_embedment_mm": 600.0,
                   "anchorage_type": "STRAIGHT", "status": "CONDITIONAL_PRESSURE_END_DESIGN",
                   "layout_status": "PROPOSED_PRESSURE_BARS_FIT", "transfer": tr}
            other_end = {**deepcopy(end), "column": "999_" + pier_name}
            ends = {side: end, ("I" if side == "J" else "J"): other_end}
            panel = {
                "member": uid, "wall": uid, "thickness_m": 0.4, "width_direction": direction,
                "column_i": ends["I"]["column"], "column_j": ends["J"]["column"],
                "support_sections": {"I": {"column": ends["I"]["column"]}, "J": {"column": ends["J"]["column"]}},
                "schedule_status": "PRESSURE_PANEL_SCHEDULE_QUALIFIED" if scheduled else "PRESSURE_PANEL_DETAIL_OPEN",
                "two_way_shell": {"proposed_detail": {"status": "PROPOSED_COMBINED_CURTAINS" if scheduled else "UNQUALIFIED_CURTAIN_TRIAL",
                                                      "horizontal": h, "vertical": {"diameter_mm": 14, "pitch_mm": 100.0, "stations_per_face": 10},
                                                      "ends": ends}},
            }
            return {
                "pier": pier_name, "maximum_aggregate_mm": 20.0, "geometry": {"panels": [panel]},
                "two_way_support_layouts": [
                    {"column": "215", "members": [uid], "status": "PROPOSED_PRESSURE_BARS_FIT"},
                    {"column": "999_" + pier_name, "members": [uid], "status": "PROPOSED_PRESSURE_BARS_FIT"},
                ],
            }

        # 1. Clear orthogonal corner (24.8 mm vertical offset > 12 mm bar touch limit): both remain qualified.
        ok_piers = [make_pier("xP2", "441", [1.0, 0.0], "J", 71.8), make_pier("yP1", "443", [0.0, 1.0], "I", 47.0)]
        _verify_cross_pier_supports(ok_piers)
        for r in ok_piers:
            self.assertEqual(r["geometry"]["panels"][0]["schedule_status"], "PRESSURE_PANEL_SCHEDULE_QUALIFIED")
            c215 = next(x for x in r["two_way_support_layouts"] if x["column"] == "215")
            self.assertEqual((c215["status"], c215["cross_pier_members"]), ("PROPOSED_PRESSURE_BARS_FIT", ["441", "443"]))

        # 2. Clashing orthogonal corner between two scheduled panels: both demoted honestly.
        bad_piers = [make_pier("xP2", "441", [1.0, 0.0], "J", 47.0), make_pier("yP1", "443", [0.0, 1.0], "I", 47.0)]
        _verify_cross_pier_supports(bad_piers)
        for r in bad_piers:
            p = r["geometry"]["panels"][0]
            self.assertEqual((p["schedule_status"], p["reason"]), ("PRESSURE_PANEL_DETAIL_OPEN", "CROSS_PIER_COLUMN_BARS_CLASH"))

        # 3. Unscheduled trial clashing with an already-scheduled peer: peer stays qualified, trial records clash.
        mixed = [make_pier("xP2", "436", [1.0, 0.0], "I", 47.0, scheduled=False), make_pier("yP2", "442", [0.0, 1.0], "J", 47.0, scheduled=True)]
        _verify_cross_pier_supports(mixed)
        self.assertEqual(mixed[1]["geometry"]["panels"][0]["schedule_status"], "PRESSURE_PANEL_SCHEDULE_QUALIFIED")
        c_open = next(x for x in mixed[0]["two_way_support_layouts"] if x["column"] == "215")
        self.assertEqual(c_open["status"], "PROPOSED_PRESSURE_BARS_CLASH")
