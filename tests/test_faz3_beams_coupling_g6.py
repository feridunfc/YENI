"""Counterexample unit tests for Faz 3 coupling beams, independent beam N-M3/torsion, C29 3D detail, and G6 oracle."""
from __future__ import annotations

import base64
from copy import deepcopy
import math
import unittest

from tbdy_next.column_engine.section_capacity import Bar, Material, Section, _Curve, perimeter
from tbdy_next.engineering.beam_independent_design import evaluate_beam_independent_design
from tbdy_next.engineering.c29_joint_detail import (
    HOOP_Z_OFFSETS_MM,
    assign_registered_joint_bars,
    check_joint_3d_congestion,
)
from tbdy_next.engineering.coupling_beam_design import evaluate_coupling_beams
from tbdy_next.engineering.g6_contract import _independent_beam_mr_knm


def _synthetic_wall_beam_fixture(*, length_m: float = 3.4, v2_kn: float = 120.0, p_kn: float = 80.0, t_knm: float = 8.0, add_release: bool = False):
    e2k = (
        '$ FRAME SECTIONS\n'
        '  FRAMESECTION "B60x70" MATERIAL "C35/45" SHAPE "Concrete Rectangular" D 0.7 B 0.6\n'
        '  FRAMESECTION "B60x70" I2MOD 0.35 I3MOD 0.35\n'
        '$ LINE ASSIGNS\n'
        + ('  LINEASSIGN "B165" "+4.50" SECTION "B60x70" RELEASE "TI"\n' if add_release else '  LINEASSIGN "B165" "+4.50" SECTION "B60x70"\n')
    )
    b64 = base64.b64encode(e2k.encode("utf-8")).decode("ascii")
    source = {
        "analysis_archive": {"model_export_base64": b64},
        "analysis_basis": {"design_groups": {"gravity": ["Grav_Ult"], "ductile": ["Duct_SeisX"]}},
        "geometry_capture": {
            "tables": {
                "BEAM_CONNECTIVITY": {
                    "status": "CAPTURED",
                    "row_count": 2,
                    "rows": [
                        {"UniqueName": "767", "Story": "+4.50", "BeamBay": "B165", "UniquePtI": "P1", "UniquePtJ": "P2"},
                        {"UniqueName": "556", "Story": "+4.50", "BeamBay": "B78", "UniquePtI": "P2", "UniquePtJ": "P3"},
                    ],
                },
                "COLUMN_CONNECTIVITY": {
                    "status": "CAPTURED",
                    "row_count": 1,
                    "rows": [{"UniqueName": "C1", "Story": "+4.50", "ColumnBay": "C30", "UniquePtI": "P3B", "UniquePtJ": "P3"}],
                },
                "RECTANGULAR_SECTIONS": {
                    "status": "CAPTURED",
                    "row_count": 2,
                    "rows": [
                        {"Name": "B60x70", "t3": "0.7", "t2": "0.6"},
                        {"Name": "Column_80x80", "t3": "0.8", "t2": "0.8"},
                    ],
                },
                "FRAME_ASSIGNMENTS": {
                    "status": "CAPTURED",
                    "row_count": 3,
                    "rows": [
                        {"UniqueName": "767", "AnalysisSect": "B60x70"},
                        {"UniqueName": "556", "AnalysisSect": "B60x70"},
                        {"UniqueName": "C1", "AnalysisSect": "Column_80x80"},
                    ],
                },
            }
        },
        "vs06_b1_geometry_source": {
            "table_reads": {
                "Point Object Connectivity": {
                    "status": "CAPTURED",
                    "row_count": 12,
                    "rows": [
                        {"UniqueName": "P1", "X": "0.0", "Y": "2.0", "Z": "4.5"},
                        {"UniqueName": "P2", "X": str(length_m), "Y": "2.0", "Z": "4.5"},
                        {"UniqueName": "P3", "X": str(length_m + 5.0), "Y": "2.0", "Z": "4.5"},
                        {"UniqueName": "P3B", "X": str(length_m + 5.0), "Y": "2.0", "Z": "0.0"},
                        # Wall W1 along Y at X=0.0 (Y in [0, 4.4], Z in [0, 4.5] so top edge is at Z=4.5)
                        {"UniqueName": "W1A", "X": "0.0", "Y": "0.0", "Z": "0.0"},
                        {"UniqueName": "W1B", "X": "0.0", "Y": "4.4", "Z": "0.0"},
                        {"UniqueName": "W1C", "X": "0.0", "Y": "4.4", "Z": "4.5"},
                        {"UniqueName": "W1D", "X": "0.0", "Y": "0.0", "Z": "4.5"},
                        # Wall W2 along Y at X=length_m (Z in [0, 4.5])
                        {"UniqueName": "W2A", "X": str(length_m), "Y": "0.0", "Z": "0.0"},
                        {"UniqueName": "W2B", "X": str(length_m), "Y": "4.4", "Z": "0.0"},
                        {"UniqueName": "W2C", "X": str(length_m), "Y": "4.4", "Z": "4.5"},
                        {"UniqueName": "W2D", "X": str(length_m), "Y": "0.0", "Z": "4.5"},
                    ],
                },
                "Wall Object Connectivity": {
                    "status": "CAPTURED",
                    "row_count": 2,
                    "rows": [
                        {"UniqueName": "W1", "Story": "+4.50", "WallBay": "W1", "UniquePt1": "W1A", "UniquePt2": "W1B", "UniquePt3": "W1C", "UniquePt4": "W1D"},
                        {"UniqueName": "W2", "Story": "+4.50", "WallBay": "W2", "UniquePt1": "W2A", "UniquePt2": "W2B", "UniquePt3": "W2C", "UniquePt4": "W2D"},
                    ],
                },
                "Area Assignments - Section Properties": {
                    "status": "CAPTURED",
                    "row_count": 2,
                    "rows": [
                        {"UniqueName": "W1", "PropType": "Wall", "SectProp": "Wall_40cm"},
                        {"UniqueName": "W2", "PropType": "Wall", "SectProp": "Wall_40cm"},
                    ],
                },
                "Wall Property Definitions - Specified": {
                    "status": "CAPTURED",
                    "row_count": 1,
                    "rows": [{"Name": "Wall_40cm", "Thickness": "0.4"}],
                },
            }
        },
        "pier_section_forces": {
            "read": {
                "tables": {
                    "table_reads": {
                        "Area Assignments - Pier Labels": {
                            "rows": [
                                {"UniqueName": "W1", "PierName": "P4"},
                                {"UniqueName": "W2", "PierName": "P5"},
                            ]
                        }
                    }
                }
            }
        },
        "column_axial": {
            "r10_source": {
                "beam_force_source": {
                    "rowsets": {
                        uid: {
                            "LoadCase": ["Grav_Ult", "Duct_SeisX", "Duct_SeisX"],
                            "ObjSta": [0.0, 0.0, len_m_b],
                            "Elm": [uid + "-1", uid + "-1", uid + "-1"],
                            "P": [-p_kn, -p_kn, p_kn],
                            "V2": [50.0, v2_kn, -v2_kn],
                            "T": [t_knm, t_knm, -t_knm],
                            "M3": [-120.0, -180.0, 140.0],
                        }
                        for uid, len_m_b in (("767", length_m), ("556", 5.0))
                    }
                }
            }
        },
    }

    bar_area_20 = math.pi * 20.0 * 20.0 / 4.0
    bars = [
        {"x2_mm": 290.0, "x3_mm": -250.0, "area_mm2": bar_area_20, "diameter_mm": 20},
        {"x2_mm": 290.0, "x3_mm": -80.0, "area_mm2": bar_area_20, "diameter_mm": 20},
        {"x2_mm": 290.0, "x3_mm": 80.0, "area_mm2": bar_area_20, "diameter_mm": 20},
        {"x2_mm": 290.0, "x3_mm": 250.0, "area_mm2": bar_area_20, "diameter_mm": 20},
        {"x2_mm": -290.0, "x3_mm": -250.0, "area_mm2": bar_area_20, "diameter_mm": 20},
        {"x2_mm": -290.0, "x3_mm": -80.0, "area_mm2": bar_area_20, "diameter_mm": 20},
        {"x2_mm": -290.0, "x3_mm": 80.0, "area_mm2": bar_area_20, "diameter_mm": 20},
        {"x2_mm": -290.0, "x3_mm": 250.0, "area_mm2": bar_area_20, "diameter_mm": 20},
    ]
    sel = {
        "bars": bars,
        "area_top_mm2": 4.0 * bar_area_20,
        "area_bottom_mm2": 4.0 * bar_area_20,
        "effective_top_centroid_mm": 60.0,
        "effective_bottom_centroid_mm": 60.0,
        "max_longitudinal_diameter_mm": 20,
        "capacity": {"positive_m3_knm": 310.0, "negative_m3_knm": -310.0},
    }

    def _beam_rec(uid: str, pi: str, pj: str, L_mm: float, off_j: float):
        ln = L_mm - off_j
        return {
            "member_id": uid,
            "label": "B165" if uid == "767" else "B78",
            "story": "+4.50",
            "section_name": "B60x70",
            "point_i": pi,
            "point_j": pj,
            "width_mm": 600.0,
            "height_mm": 700.0,
            "fyk_mpa": 500.0,
            "length_mm": L_mm,
            "clear_span_mm": ln,
            "end_offsets_mm": {"I": 0.0, "J": off_j},
            "ends": {
                "I": {"target_station_m": 0.0, "engineer_selection": deepcopy(sel)},
                "J": {"target_station_m": (L_mm - off_j) / 1000.0, "engineer_selection": deepcopy(sel)},
            },
            "engineer_midspan": deepcopy(sel),
            "engineer_shear_ve": {
                "gravity_shear_vdy_kn": 50.0,
                "scenario_ve_kn": 50.0 + 1.4 * 620.0 / (ln / 1000.0),
            },
            "engineer_stirrups": {
                "fywd_mpa": 500.0 / 1.15,
                "effective_depth_mm": 640.0,
                "vr_max_kn": 1971.2,
                "confinement": {"diameter_mm": 10, "spacing_mm": 90.0, "asw_mm2": 314.159265, "vr_conservative_kn": 971.3},
                "span": {"diameter_mm": 10, "spacing_mm": 90.0, "asw_mm2": 314.159265, "vr_conservative_kn": 1247.0},
            },
            "selected_design": {"status": "CONDITIONAL_DESIGN_CALCULATED"},
        }

    # Add collinear beam on West side of W1 as well so both ends of 767 have continuity, or let W1 be coplanar/continuous!
    source["vs06_b1_geometry_source"]["table_reads"]["Point Object Connectivity"]["rows"].append(
        {"UniqueName": "P0", "X": "-5.0", "Y": "2.0", "Z": "4.5"}
    )
    source["geometry_capture"]["tables"]["BEAM_CONNECTIVITY"]["rows"].append(
        {"UniqueName": "555", "Story": "+4.50", "BeamBay": "B32", "UniquePtI": "P0", "UniquePtJ": "P1"}
    )
    source["geometry_capture"]["tables"]["FRAME_ASSIGNMENTS"]["rows"].append(
        {"UniqueName": "555", "AnalysisSect": "B60x70"}
    )
    source["column_axial"]["r10_source"]["beam_force_source"]["rowsets"]["555"] = deepcopy(
        source["column_axial"]["r10_source"]["beam_force_source"]["rowsets"]["556"]
    )
    source["column_axial"]["r10_source"]["beam_force_source"]["rowsets"]["555"]["Elm"] = ["555-1", "555-1", "555-1"]

    stages = {
        "beam_r10": {
            "beams": [
                _beam_rec("767", "P1", "P2", length_m * 1000.0, 0.0),
                _beam_rec("556", "P2", "P3", 5000.0, 400.0),
                _beam_rec("555", "P0", "P1", 5000.0, 0.0),
            ]
        }
    }
    return source, stages


class Faz3BeamsCouplingG6Tests(unittest.TestCase):
    def test_coupling_beam_qualifies_7_6_8_1_and_rejects_short_or_high_shear_spandrel(self):
        src, stg = _synthetic_wall_beam_fixture(length_m=3.4, v2_kn=120.0)
        res = evaluate_coupling_beams(src, stg)
        self.assertEqual(res["role_review_count"], 1)
        self.assertEqual(res["satisfied_count"], 1)
        self.assertEqual(res["not_applicable_count"], 2)
        b767 = next(r for r in res["beams"] if r["member_id"] == "767")
        self.assertEqual(b767["status"], "TBDY_7_6_8_QUALIFIED_FRAME_BEAM_DESIGN")
        self.assertAlmostEqual(b767["physical_clear_span_mm"], 3000.0)
        self.assertGreater(b767["ln_over_h_physical"], 4.28)

        # Counterexample 1: short coupling beam (L = 1.6 m -> ln_phys = 1.2 m, ln/h = 1.714 <= 2.0) requires diagonal cage
        src_short, stg_short = _synthetic_wall_beam_fixture(length_m=1.6, v2_kn=120.0)
        res_short = evaluate_coupling_beams(src_short, stg_short)
        self.assertEqual(res_short["failed_count"], 1)
        b_short = next(r for r in res_short["beams"] if r["member_id"] == "767")
        self.assertEqual(b_short["status"], "NUMERICAL_EXCEEDANCE")
        self.assertIn("TBDY_7_6_8_2_DIAGONAL_CAGE_REQUIRED", b_short["failures"])

        # Counterexample 2: shear Vd > 1.5 * bw * d * fctd (~795 kN) rejects frame-beam rule
        src_shear, stg_shear = _synthetic_wall_beam_fixture(length_m=3.4, v2_kn=850.0)
        res_shear = evaluate_coupling_beams(src_shear, stg_shear)
        self.assertEqual(res_shear["failed_count"], 1)
        b_shear = next(r for r in res_shear["beams"] if r["member_id"] == "767")
        self.assertIn("TBDY_7_6_8_2_DIAGONAL_CAGE_REQUIRED", b_shear["failures"])

    def test_beam_independent_design_catches_axial_torsion_crushing_and_e2k_release(self):
        src, stg = _synthetic_wall_beam_fixture(length_m=3.4, v2_kn=120.0, p_kn=100.0, t_knm=10.0)
        ok = evaluate_beam_independent_design(src, stg)
        self.assertEqual(ok["uls_axial_flexure_torsion_status"], "ALL_180_BEAMS_ULS_QUALIFIED")
        self.assertLess(ok["max_axial_interval_box_utilization"], 1.0)

        # Counterexample 1: axial force |P| > 0.10 * Ac * fck (0.10 * 600 * 700 * 35 / 1000 = 1470 kN)
        src_ax, stg_ax = _synthetic_wall_beam_fixture(p_kn=1600.0)
        bad_ax = evaluate_beam_independent_design(src_ax, stg_ax)
        self.assertEqual(bad_ax["uls_axial_flexure_torsion_status"], "EXCEEDANCE_DETECTED")
        self.assertLess(bad_ax["tbdy_7_4_1_2_axial_qualified_beams"], 3)

        # Counterexample 2: TS 500 Eq. 8.23 combined shear + torsion web crushing > 0.22 * fcd
        src_t, stg_t = _synthetic_wall_beam_fixture(v2_kn=900.0, t_knm=350.0)
        bad_t = evaluate_beam_independent_design(src_t, stg_t)
        self.assertEqual(bad_t["uls_axial_flexure_torsion_status"], "EXCEEDANCE_DETECTED")
        self.assertGreater(bad_t["combined_web_crushing_exceedances"], 0)

        # Counterexample 3: frame release in E2K invalidates zero-release audit
        src_rel, stg_rel = _synthetic_wall_beam_fixture(add_release=True)
        bad_rel = evaluate_beam_independent_design(src_rel, stg_rel)
        self.assertFalse(bad_rel["e2k_modifiers_and_releases"]["verified"])
        self.assertEqual(bad_rel["uls_axial_flexure_torsion_status"], "EXCEEDANCE_DETECTED")

    def test_c29_3d_congestion_detector_catches_unshifted_clash_and_passes_registered_layers(self):
        col_bars, _, _ = perimeter(800.0, 800.0, 40.0, 10.0, 16.0, n2=9, n3=9)
        sel_x = {
            "top_continuous": {"count": 2, "diameter_mm": 12},
            "top_additional": {"count": 5, "diameter_mm": 20},
            "bottom_continuous": {"count": 2, "diameter_mm": 14},
            "bottom_additional": {"count": 4, "diameter_mm": 16},
        }
        sel_y = {
            "top_continuous": {"count": 2, "diameter_mm": 12},
            "top_additional": {"count": 3, "diameter_mm": 22},
            "bottom_continuous": {"count": 2, "diameter_mm": 14},
            "bottom_additional": {"count": 2, "diameter_mm": 22},
        }
        # Naive 2D overlay puts both X and Y at z=+290 and x3=-254 near column bar -256.5 -> clash!
        naive_x = [(290.0, -254.0, 20), (290.0, 0.0, 20), (-290.0, -254.0, 16)]
        naive_y = [(290.0, -254.0, 22), (-290.0, -254.0, 22)]
        clash_res = check_joint_3d_congestion(
            col_bars,
            [("541", False, (-500.0, 0.0), naive_x), ("533", True, (-500.0, 0.0), naive_y)],
            is_roof=False,
            include_hoops=False,
        )
        self.assertFalse(clash_res["collision_free"])
        self.assertLess(clash_res["min_nonbearing_clearance_mm"], 0.0)

        # Registered Y-outer / X-inner lanes + 9 Φ10 joint hoops & crossties (max pitch 86 mm <= 100 mm)
        reg_x = assign_registered_joint_bars(sel_x, 600.0, is_y_beam=False, y_outer_layer=True)
        reg_y = assign_registered_joint_bars(sel_y, 600.0, is_y_beam=True, y_outer_layer=True)
        clear_res = check_joint_3d_congestion(
            col_bars,
            [("541", False, (-500.0, 0.0), reg_x), ("533", True, (-500.0, 0.0), reg_y)],
            is_roof=False,
            include_hoops=True,
        )
        self.assertTrue(clear_res["collision_free"])
        self.assertEqual(clear_res["clash_pair_count"], 0)
        self.assertGreaterEqual(clear_res["min_nonbearing_clearance_mm"], 2.0 - 1e-6)
        pitches = [b - a for a, b in zip(HOOP_Z_OFFSETS_MM, HOOP_Z_OFFSETS_MM[1:])]
        self.assertLessEqual(max(pitches), 90.0)

    def test_independent_g6_beam_bisection_matches_section_kernel(self):
        a20 = math.pi * 20.0 * 20.0 / 4.0
        a16 = math.pi * 16.0 * 16.0 / 4.0
        bars_dict = [
            {"x2_mm": 290.0, "x3_mm": -220.0, "area_mm2": a20, "diameter_mm": 20},
            {"x2_mm": 290.0, "x3_mm": 220.0, "area_mm2": a20, "diameter_mm": 20},
            {"x2_mm": 235.0, "x3_mm": -220.0, "area_mm2": a20, "diameter_mm": 20},
            {"x2_mm": 235.0, "x3_mm": 220.0, "area_mm2": a20, "diameter_mm": 20},
            {"x2_mm": -290.0, "x3_mm": -220.0, "area_mm2": a16, "diameter_mm": 16},
            {"x2_mm": -290.0, "x3_mm": 220.0, "area_mm2": a16, "diameter_mm": 16},
        ]
        mat = Material(fck=35.0, fcd=35.0 / 1.5, fyd=500.0 / 1.15, es=200000.0)
        sec = Section(700.0, 600.0, tuple(Bar(b["x2_mm"], b["x3_mm"], b["area_mm2"]) for b in bars_dict), mat)
        for nd_kn in (0.0, 350.0, -180.0):
            for pos_flag, angle in ((True, 0), (False, 180)):
                pt, _ = _Curve(sec, angle).solve(nd_kn * 1000.0)
                expected_knm = abs(pt["m3_nmm"]) / 1e6
                mr_ind, res_n = _independent_beam_mr_knm(
                    600.0, 700.0, bars_dict, 35.0 / 1.5, 500.0 / 1.15, 200000.0, nd_kn, pos_flag
                )
                self.assertAlmostEqual(mr_ind, expected_knm, places=3)
                self.assertLess(res_n, 0.01)


if __name__ == "__main__":
    unittest.main()
