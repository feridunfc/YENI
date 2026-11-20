"""Source-bound column faces and force-cut alignment."""
from unittest import TestCase

from tbdy_next.column_engine.native_archive import digest
from tbdy_next.engineering.column_clear_length import FACE_BASIS, project_column_clear_lengths
from tbdy_next.engineering.column_r08_local_live import PHYSICAL_CLEAR_LENGTH_GATE, project_column_r08_local_live
from tbdy_next.engineering.column_r10_live import _build_frame_catalog
from tbdy_next.etabs_geometry import AREA_ELEMENTS, AREA_INSERTION, FLOOR_CONNECTIVITY, FRAME_INSERTION, SLAB_PROPERTIES
from test_r08_local_live import _r08_local_fixture


def table(fields, rows, *, units=None, version=1, omitted=()):
    keys = fields.split()
    return {"status": "CAPTURED", "api_signature": "seven_list", "fields": keys, "row_count": len(rows),
            "rows": [dict(zip(keys, row, strict=True)) for row in rows],
            "field_metadata": {"status": "OK", "field_keys": keys + list(omitted),
                               "table_version": version, "units_by_field": units or {}}}


def fixture():
    model = "C:/model.edb"
    geometry_tables = {
        "RECTANGULAR_SECTIONS": table("Name t2 t3", [("Rect", ".5", ".7")], units={"t2": "m", "t3": "m"}),
        "COLUMN_CONNECTIVITY": table("UniqueName Story UniquePtI UniquePtJ Length",
                                     [("C", "L1", "P0", "P1", "4.5")], units={"Length": "m"}),
        "BEAM_CONNECTIVITY": table("UniqueName Story UniquePtI UniquePtJ", [("B", "L1", "P1", "P2")]),
        "FRAME_ASSIGNMENTS": table("UniqueName Story Label Type AnalysisSect AxisAngle",
                                   [("C", "L1", "C1", "Column", "Rect", "None"),
                                    ("B", "L1", "B1", "Beam", "Rect", "None")],
                                   units={"AxisAngle": "deg"}),
    }
    points = [("P0", "Base", "0", "0", "-4.5"), ("P1", "L1", "0", "0", "0"),
              ("P2", "L1", "3", "0", "0"), ("S1", "Base", "-1", "-1", "-4.5"),
              ("S2", "Base", "1", "-1", "-4.5"), ("S3", "Base", "1", "1", "-4.5"),
              ("S4", "Base", "-1", "1", "-4.5")]
    frame_offsets = ("XI", "YI", "ZI", "XJ", "YJ", "ZJ")
    shell_offsets = ("Offset1", "Offset2", "Offset3")
    r10_tables = {
        FRAME_INSERTION: table("UniqueName Story Label CardinalPt Mirror2 Mirror3",
                               [("C", "L1", "C1", "10 (Centroid)", "No", "No"),
                                ("B", "L1", "B1", "8 (Top Center)", "No", "No")],
                               units=dict.fromkeys(frame_offsets, "m"), omitted=frame_offsets + ("OffsetCSys",)),
        AREA_INSERTION: table("UniqueName Story Label CardinalPt", [("M", "Base", "F", "Top")], version=2,
                              units=dict.fromkeys(shell_offsets, "m"),
                              omitted=shell_offsets + ("CoordSys", "PointLabel", "PointName", "PointNumber")),
        SLAB_PROPERTIES: table("Name PropType ModelType Thickness", [("Mat1", "Mat", "Shell-Thick", "0.9")],
                               units={"Thickness": "m"}),
        FLOOR_CONNECTIVITY: table("UniqueName Story FloorBay UniquePt1 UniquePt2 UniquePt3 UniquePt4",
                                  [("M", "Base", "F", "S1", "S2", "S3", "S4")]),
        AREA_ELEMENTS: table("Story ElmName ObjType ObjName ObjLabel ElmJt1 ElmJt2 ElmJt3",
                             [("Base", "M-1", "Floor", "M", "F", "P0", "S1", "S2")]),
        "Objects and Elements - Joints": table(
            "ElmName ObjName ObjType Story GlobalX GlobalY GlobalZ",
            [(uid, uid, "Joint", story, x, y, z) for uid, story, x, y, z in points],
            units=dict.fromkeys(("GlobalX", "GlobalY", "GlobalZ"), "m")),
    }
    b1 = {
        "model": model, "source_only": True, "model_locked": True, "model_units_code": 6,
        "model_units_unchanged": True, "case_selection_before": [], "case_selection_after": [],
        "selection_restored": True,
        "table_reads": {
            "Point Object Connectivity": table("UniqueName Story X Y Z", points, units=dict.fromkeys("XYZ", "m")),
            "Area Assignments - Section Properties": table(
                "UniqueName Story Label PropType SectProp", [("M", "Base", "F", "Slab", "Mat1")]),
        },
    }
    b1["payload_sha256"] = digest(b1)
    source = {
        "source_mode": "LIVE_ETABS", "capture_metadata": {"model_filename": model, "model_locked_observed": True},
        "geometry_capture": {"present_units": 6, "present_units_after": 6, "unit_state_unchanged": True,
                             "tables": geometry_tables},
        "column_axial": {"r10_source": {"schema": "tbdy.next.r10-live-source.v1", "model_locked_before": True,
                                       "model_locked_after": True, "units_before": 6, "units_after": 6,
                                       "table_reads": r10_tables}},
        "vs06_b1_geometry_source": b1,
    }
    scope = {
        "analysis_mesh": {"members": {"C": {"roster_bound": True, "expected_analysis_element_ids": ["C"],
                                            "analysis_element_end_joints": {"C": ["P0", "P1"]}}}},
        "configured_output_cuts": {"C": {"status": "REQUIRED_SUBSET_BOUND", "length_m": 4.5, "offset_i_m": 0,
                                         "offset_j_m": .7, "cuts": [
                                            {"analysis_element_id": "C", "object_station_m": x, "element_station_m": x}
                                            for x in (0., 3.8)]}},
    }
    return source, r10_tables, scope


def project(source, scope):
    frames, _, meta = _build_frame_catalog(source)
    return project_column_clear_lengths(source, frames, meta["adjacency"], ["C"], scope)


class ColumnClearLengthTests(TestCase):
    def test_top_mat_and_beam_soffit_bind_both_native_end_cuts(self):
        source, _, scope = fixture()
        row = project(source, scope)["per_member"]["C"]
        self.assertEqual(row["status"], FACE_BASIS)
        self.assertEqual(row["physical_length_m"], 3.8)
        self.assertEqual(row["faces"]["I"]["slabs"][0]["analysis_element_ids"], ["M-1"])
        self.assertEqual(row["faces"]["J"]["beams"][0]["end"], "I")
        self.assertEqual(row["end_cuts"]["J"], ["C", 3.8, "C", 3.8])

    def test_equal_span_with_shifted_native_end_cuts_cannot_bind_geometry(self):
        source, _, scope = fixture()
        grid = scope["configured_output_cuts"]["C"]
        grid.update(offset_i_m=.1, offset_j_m=.6)
        for cut in grid["cuts"]:
            cut["object_station_m"] += .1
        row = project(source, scope)["per_member"]["C"]
        self.assertAlmostEqual(row["physical_length_m"], row["offset_length_m"])
        self.assertEqual(row["status"], "MODEL_CLEAR_LENGTH_UNRESOLVED")
        self.assertIn("both native force cuts", row["reason"])

    def test_top_center_with_native_translation_does_not_get_unshifted_faces(self):
        source, records, scope = fixture()
        insertion = records[FRAME_INSERTION]
        fields = [k for k in insertion["field_metadata"]["field_keys"] if k not in insertion["fields"]]
        insertion["fields"].extend(fields)
        for row in insertion["rows"]:
            row.update(dict.fromkeys(fields, "0"), OffsetCSys="Global")
        insertion["rows"][1]["ZI"] = ".1"
        row = project(source, scope)["per_member"]["C"]
        self.assertEqual(row["status"], "MODEL_CLEAR_LENGTH_UNRESOLVED")
        self.assertIn("Beam B", row["reason"])

    def test_mat_polygon_does_not_prove_contact_without_a_shared_analysis_joint(self):
        source, records, scope = fixture()
        records[AREA_ELEMENTS]["rows"][0]["ElmJt1"] = "S3"
        row = project(source, scope)["per_member"]["C"]
        self.assertEqual(row["status"], "MODEL_CLEAR_LENGTH_UNRESOLVED")
        self.assertIn("no supported beam panel or mat", row["reason"])

    def test_wall_contact_blocks_the_flat_support_model(self):
        source, records, scope = fixture()
        record = records[AREA_ELEMENTS]
        record["rows"].append({**record["rows"][0], "ObjType": "Wall", "ElmName": "W-1", "ObjName": "W"})
        record["row_count"] += 1
        self.assertIn("Wall contact", project(source, scope)["per_member"]["C"]["reason"])

    def test_old_capture_has_no_physical_face_projection(self):
        source, records, scope = fixture()
        records.clear()
        self.assertIsNone(project(source, scope))

    def test_r08_consumes_the_same_length_and_keeps_effective_length_gate(self):
        source, geometry, axial, pmm = _r08_local_fixture()
        proof = {"member_id": "127", "status": FACE_BASIS, "physical_length_m": 3.8}
        r10 = {"member_id": "127", "physical_clear_lengths": {"per_member": {"127": proof}}}
        output = project_column_r08_local_live(source, geometry, axial, pmm, r10_live=r10)
        self.assertEqual(output["candidate_span_mm"], 3800.0)
        self.assertEqual(output["span_basis"], FACE_BASIS)
        self.assertNotIn(PHYSICAL_CLEAR_LENGTH_GATE, output["open_gates"])
        self.assertIn("END_RESTRAINTS_K_AND_SWAY_CLASSIFICATION_NOT_APPROVED", output["open_gates"])
