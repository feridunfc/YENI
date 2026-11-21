"""Independent source contracts and arithmetic for the revised story producer."""
from copy import deepcopy
import hashlib
from math import pi
import unittest

from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.engineering.column_clear_length import FACE_BASIS, WALL_CONNECTIVITY
from tbdy_next.engineering.gravity_story_basis import (
    AXES, FRAME_FORCE, STORY_BASIS_SCHEMA, WALL_FORCE,
    produce_story_basis, project_native_story_frame_forces,
)
from test_r03_analysis_setup import capture_table
from test_r10_live import _rowset


CONTRIBUTOR_MODIFIER_SCHEMA = "tbdy.next.gravity-story-contributor-modifiers.v1"


def _register_table(tables, key, fields, rows, units=None):
    record = capture_table(key, list(fields), [tuple(row.get(field, "") for field in fields) for row in rows])
    record["field_metadata"]["units_by_field"].update(units or {})
    tables[key] = record


def _prepare_geometry_table(tables, key, record, units):
    if record.get("status") == "CAPTURED" and (record.get("field_metadata") or {}).get("status") == "OK":
        bound = deepcopy(record)
        for field, unit in units.items():
            if field in bound["fields"]:
                bound["field_metadata"]["units_by_field"].setdefault(field, unit)
        tables[key] = bound
        return
    rows = record["rows"]
    _register_table(tables, key, tuple(record.get("fields") or rows[0]), rows, units)


def add_bound_story_basis(source, level, uid, cases, *, ln_mm, ei_nmm2, story_id=None):
    """Prepare a synthetic one-column free body with an independent K=2 oracle."""
    geometry = source["geometry_capture"]["tables"]
    col = geometry["COLUMN_CONNECTIVITY"]
    _prepare_geometry_table(geometry, "COLUMN_CONNECTIVITY", col, {"Length": "m"})
    member, = [row for row in col["rows"] if row["UniqueName"] == uid]
    story = story_id or member["Story"]
    if member["Story"] != story:
        raise ValueError("Synthetic story label must agree with the column")
    joints = member["UniquePtI"], member["UniquePtJ"]
    branch = source.setdefault("vs06_b1_geometry_source", {}).setdefault("table_reads", {})
    point_table = branch.get("Point Object Connectivity")
    if point_table is None:
        point_table = source["vs05_delta_source"]["table_reads"]["Point Object Connectivity"]
    _prepare_geometry_table(branch, "Point Object Connectivity", point_table, dict.fromkeys("XYZ", "m"))
    if WALL_CONNECTIVITY not in branch:
        _register_table(branch, WALL_CONNECTIVITY,
                        ("UniqueName", "Story", "UniquePt1", "UniquePt2", "UniquePt3", "UniquePt4"), [])
    if "Area Assignments - Section Properties" not in branch:
        _register_table(branch, "Area Assignments - Section Properties", ("UniqueName", "Story", "PropType"), [])
    mesh = min(level["mesh"][uid], key=lambda r: r["i_xyz"][2])
    z = mesh["i_xyz"][2]
    names = {p["first"] for p in cases.values()}
    forces, balance = [], {}
    native = native_frame_force_rows(level["force_source"]["rowsets"][uid], uid)
    for _, _, element, station, name, step, number, p, v2, v3, *_ in native:
        if element == mesh["element"] and station == 0. and name in names:
            forces.append({"kind": "COLUMN", "object_id": uid, "element_id": element, "case": name,
                           "step_type": step, "step_number": number, "z_m": z, "representation": FRAME_FORCE,
                           "vector_kn": [p, v2, v3]})
            balance[name] = {"upper_external_applied_kn": -p-10, "upper_self_weight_kn": 10.,
                             "reference": "Manufactured upper free body, 10 kN independently applied self weight"}
    fa, = [row for row in geometry["FRAME_ASSIGNMENTS"]["rows"] if row["UniqueName"] == uid]
    rect, = [row for row in geometry["RECTANGULAR_SECTIONS"]["rows"] if row["Name"] == fa["AnalysisSect"]]
    d2, d3 = (float(rect[k]) * 1000 for k in ("t2", "t3"))
    generation = level.setdefault("analysis_generation", hashlib.sha256(("synthetic-run|" + level["model_sha256"]).encode()).hexdigest())
    block = level.setdefault("story_basis_source", {"schema": STORY_BASIS_SCHEMA, "model_sha256": level["model_sha256"],
        "analysis_generation": generation, "units_code": 6, "story_cuts": {}, "columns": {}})
    block["story_cuts"][story] = {"z_m": z, "forces": forces, "equilibrium": balance}
    block["columns"][uid] = {"ln_mm": ln_mm, "sway": "SWAY_PERMITTED", "creep_reference": "Manufactured effective EI",
                            "axes": {}}
    for axis, i, inertia in (("M2", 4, d2*d3**3/12), ("M3", 5, d3*d2**3/12)):
        # With equal springs rho = pi/2, z = pi/2 solves z=2*atan(rho/z).
        ei = ei_nmm2[axis] if isinstance(ei_nmm2, dict) else ei_nmm2
        k_theta = (pi/2) * ei/1e9 / (ln_mm/1000)
        modifier = level["frame_object_modifiers"][uid][i]
        ends = {side: {"joint_id": joint, "k_knm_per_rad": k_theta,
                       "reference": "Manufactured end spring; K=2 by symmetry"} for side, joint in zip(("i", "j"), joints)}
        block["columns"][uid]["axes"][axis] = {"ec_mpa": 34000., "i_mm4": inertia,
            "section_modifier": ei/(34000*inertia*modifier), "object_modifier": modifier,
            "restraint": {"method": "ELASTIC_SWAY_END_SPRINGS", **ends}}
    return block


def _example():
    uid, cases, ei = "C", {"G": {"first": "F", "second": "P"}}, 2.2e14
    source = {"geometry_capture": {"tables": {
        "COLUMN_CONNECTIVITY": {"rows": [{"UniqueName": uid, "Story": "S1", "UniquePtI": "I", "UniquePtJ": "J"}]},
        "FRAME_ASSIGNMENTS": {"rows": [{"UniqueName": uid, "AnalysisSect": "REC", "Story": "S1", "AxisAngle": "7.0"}]},
        "RECTANGULAR_SECTIONS": {"rows": [{"Name": "REC", "Material": "C35", "t2": "0.8", "t3": "0.8"}]},
    }}, "vs06_b1_geometry_source": {"table_reads": {"Point Object Connectivity": {"rows": [
        {"UniqueName": "I", "X": 0., "Y": 0., "Z": 0.}, {"UniqueName": "M", "X": 0., "Y": 0., "Z": 2.},
        {"UniqueName": "J", "X": 0., "Y": 0., "Z": 4.}]}}}}
    mesh = [{"element": "A", "i_xyz": [0., 0., 0.], "j_xyz": [0., 0., 2.]},
            {"element": "B", "i_xyz": [0., 0., 2.], "j_xyz": [0., 0., 4.]}]
    level = {"divisions": 2, "model_sha256": "a"*64, "mesh": {uid: mesh}, "frame_object_modifiers": {uid: [1.]*8},
             "force_source": {"rowsets": {uid: _rowset([(uid, 0., "A", 0., "F", "Step", 1., -950., 12., 3., 0., 40., 0.)])}}}
    local = {"physical_clear_length": {"member_id": uid, "status": FACE_BASIS, "physical_length_m": 4.,
                                       "faces": {"I": {"top_z_m": 0.}}},
             "stiffness_and_euler": {axis: {"selected_ei_nmm2": ei} for axis in AXES},
             "adopted_second_order_basis": {"member": {"axes": {axis: {"sway": "SWAY_PERMITTED"} for axis in AXES}}}}
    add_bound_story_basis(source, level, uid, cases, ln_mm=4000., ei_nmm2=ei)
    return source, local, level, uid, cases


class RevisedStoryBasisTests(unittest.TestCase):
    def test_native_frame_conversion_uses_the_upper_element_once(self):
        source, local, level, uid, cases = _example()
        headers = ("ElmName", "GlobalX", "GlobalY", "GlobalZ")
        tables = {}
        _register_table(tables, "Objects and Elements - Joints", headers,
                        [dict(zip(headers, (n, 0., 0., z))) for n, z in (("I", 0.), ("M", 2.), ("J", 4.))],
                        dict.fromkeys(headers[1:], "m"))
        _register_table(tables, "Objects and Elements - Frames", ("ObjType", "ObjName", "ElmName", "ElmJtI", "ElmJtJ"),
                        [{"ObjType": "Frame", "ObjName": uid, "ElmName": eid, "ElmJtI": a, "ElmJtJ": b}
                         for eid, a, b in (("A", "I", "M"), ("B", "M", "J"))])
        selection = {"cases": {"F": False}, "combos": {"G": True}}
        sidecar = {
            "model_sha256": level["model_sha256"], "analysis_generation": level["analysis_generation"],
            "tables": {"model_locked": True, "model_units_code": 6, "selection_restored": True,
                       "case_selection_before": [], "case_selection_after": [], "table_reads": tables},
            "columns": {"schema": "tbdy.next.etabs-frame-force-source.v1", "units_code": 6, "api": "Results.FrameForce",
                         "item_type": "ObjectElm", "output_selection_before": selection, "output_selection_after": selection,
                         "output_selection_during": {"cases": {"F": True}, "combos": {"G": False}},
                         "rowsets": {uid: _rowset([
                            (uid, 2., "A", 2., "F", "Step", 1., -930., 0., 0., 0., 40., 0.),
                            (uid, 2., "B", 0., "F", "Step", 1., -920., 0., 0., 0., 40., 0.),
                         ])}}
        }
        projected = project_native_story_frame_forces(source, level, uid, 2., cases, sidecar)
        self.assertEqual(projected["status"], "STORY_NATIVE_FRAME_SOURCE_CALCULATED", projected)
        self.assertEqual([(r["element_id"], r["vector_kn"][0]) for r in projected["forces"]], [("B", -920.)])
        frame_table = tables["Objects and Elements - Frames"]
        frame_table["rows"].append({"ObjType": "Shell", "ObjName": uid, "ElmName": "B",
                                    "ElmJtI": "SHELL_I", "ElmJtJ": "SHELL_J"})
        frame_table["row_count"] += 1
        shell_overlap = project_native_story_frame_forces(source, level, uid, 2., cases, sidecar)
        self.assertEqual(shell_overlap, projected)
        missing_type = deepcopy(sidecar)
        table = missing_type["tables"]["table_reads"]["Objects and Elements - Frames"]
        table["fields"].remove("ObjType")
        for row in table["rows"]:
            row.pop("ObjType")
        rejected = project_native_story_frame_forces(source, level, uid, 2., cases, missing_type)
        self.assertEqual(rejected["status"], "STORY_NATIVE_FRAME_SOURCE_UNBOUND")
        self.assertIn("STORY_GEOMETRY_TABLE_UNBOUND:Objects and Elements - Frames", rejected["reasons"])

    def test_separate_contributor_modifiers_bind_generation_and_agree_with_paired_member(self):
        source, local, level, uid, cases = _example()
        level["story_basis_source"]["contributor_modifiers"] = {
            "schema": CONTRIBUTOR_MODIFIER_SCHEMA, "model_sha256": level["model_sha256"],
            "analysis_generation": level["analysis_generation"],
            "modifiers": deepcopy(level["frame_object_modifiers"]),
        }
        result = produce_story_basis(source, local, level, uid, cases)
        self.assertEqual(result["status"], "REVISED_STORY_BASIS_CALCULATED", result)
        self.assertEqual(result["contributor_modifier_source"]["expected_column_ids"], [uid])
        for defect, code in (
            ("generation", "STORY_CONTRIBUTOR_MODIFIER_MODEL_GENERATION_MISMATCH"),
            ("model", "STORY_CONTRIBUTOR_MODIFIER_MODEL_GENERATION_MISMATCH"),
            ("missing", "STORY_CONTRIBUTOR_MODIFIER_SCOPE_INCOMPLETE:" + uid),
            ("conflict", "STORY_CONTRIBUTOR_MODIFIER_PAIRED_MEMBER_CONFLICT:" + uid),
        ):
            with self.subTest(defect=defect):
                changed = deepcopy(level)
                capture = changed["story_basis_source"]["contributor_modifiers"]
                if defect == "generation":
                    capture["analysis_generation"] = "b" * 64
                elif defect == "model":
                    capture["model_sha256"] = "b" * 64
                elif defect == "missing":
                    capture["modifiers"].pop(uid)
                else:
                    capture["modifiers"][uid][4] *= .5
                actual = produce_story_basis(source, local, changed, uid, cases)
                self.assertEqual(actual["story_inputs"], {})
                self.assertIn(code, actual["reasons"])

    def test_symmetric_springs_and_free_body_use_existing_owners(self):
        source, local, level, uid, cases = _example()
        result = produce_story_basis(source, local, level, uid, cases)
        self.assertEqual(result["status"], "REVISED_STORY_BASIS_CALCULATED", result)
        self.assertEqual(result["cases"]["G"]["signed_vertical_sum_kn"], 950.)
        self.assertEqual(result["cases"]["G"]["equilibrium_residual_kn"], 0.)
        expected_nk = pi**2 * 2.2e14 / 8000**2 / 1000
        for axis in AXES:
            basis = result["story_inputs"][axis]
            self.assertAlmostEqual(basis["k"], 2.)
            self.assertAlmostEqual(basis["story_aggregates"]["G"]["nk_kn"], expected_nk)
            self.assertAlmostEqual(result["axes"][axis]["target"]["lk_mm"], 8000.)
        self.assertEqual(result["engineering_approval"], "NOT_GRANTED")

    def test_missing_wall_stays_in_independent_force_and_stability_population(self):
        source, local, level, uid, cases = _example()
        tables = source["vs06_b1_geometry_source"]["table_reads"]
        fields = tuple(tables["Point Object Connectivity"]["fields"])
        rows = deepcopy(tables["Point Object Connectivity"]["rows"])
        rows.extend(({"UniqueName": "WI", "X": 1., "Y": 0., "Z": 0.},
                     {"UniqueName": "WJ", "X": 1., "Y": 0., "Z": 4.}))
        _register_table(tables, "Point Object Connectivity", fields, rows, dict.fromkeys("XYZ", "m"))
        _register_table(tables, WALL_CONNECTIVITY, ("UniqueName", "Story", "UniquePt1", "UniquePt2", "UniquePt3", "UniquePt4"),
                        [{"UniqueName": "W", "Story": "S1", "UniquePt1": "I", "UniquePt2": "WI",
                          "UniquePt3": "WJ", "UniquePt4": "J"}])
        _register_table(tables, "Area Assignments - Section Properties", ("UniqueName", "Story", "PropType"),
                        [{"UniqueName": "W", "Story": "S1", "PropType": "Wall"}])
        cut = level["story_basis_source"]["story_cuts"]["S1"]
        result = produce_story_basis(source, local, level, uid, cases)
        self.assertEqual(result["cases"]["G"]["expected_count"], 2)
        self.assertIn("STORY_FORCE_MISSING:WALL:W", result["cases"]["G"]["reasons"])
        self.assertIn("STORY_WALL_CRITICAL_LOAD_METHOD_UNSUPPORTED:W", result["axes"]["M2"]["reasons"])
        self.assertGreater(result["axes"]["M2"]["supported_critical_load_sum_kn"], 0)

        cut["forces"].append({"kind": "WALL", "object_id": "W", "element_id": "INTEGRATED_W",
            "case": "F", "step_type": "Step", "step_number": 1., "z_m": 0., "representation": WALL_FORCE,
            "vector_kn": [0., 0., 100.]})
        cut["equilibrium"]["F"]["upper_external_applied_kn"] += 100
        result = produce_story_basis(source, local, level, uid, cases)
        self.assertEqual(result["cases"]["G"]["supported_compression_kn"], 1050.)
        self.assertEqual(result["cases"]["G"]["status"], "STORY_COMPRESSION_BOUND")
        self.assertEqual(result["story_inputs"], {})

    def test_basis_fails_closed_on_source_identity_duplicates_and_mismatched_stiffness(self):
        source, local, level, uid, cases = _example()
        for defect in ("generation", "units", "contributor", "native", "equilibrium", "ei"):
            with self.subTest(defect=defect):
                changed = deepcopy(level)
                block = changed["story_basis_source"]
                cut = block["story_cuts"]["S1"]
                if defect == "generation":
                    block["analysis_generation"] = "b"*64
                elif defect == "units":
                    block["units_code"] = 12
                elif defect == "contributor":
                    cut["forces"].append({**cut["forces"][0], "element_id": "LOWER_SIDE"})
                elif defect == "native":
                    cut["forces"][0]["vector_kn"][0] -= 50
                    cut["equilibrium"]["F"]["upper_external_applied_kn"] += 50
                elif defect == "equilibrium":
                    cut["equilibrium"]["F"]["upper_self_weight_kn"] += 50
                else:
                    block["columns"][uid]["axes"]["M2"]["section_modifier"] *= .9
                result = produce_story_basis(source, local, changed, uid, cases)
                self.assertNotIn("M2", result["story_inputs"], result)
                if defect == "ei":
                    self.assertIn("M3", result["story_inputs"])
                else:
                    self.assertEqual(result["story_inputs"], {})

    def test_changed_measured_end_spring_changes_k_and_nk(self):
        source, local, level, uid, cases = _example()
        baseline = produce_story_basis(source, local, level, uid, cases)
        changed = deepcopy(level)
        changed["story_basis_source"]["columns"][uid]["axes"]["M3"]["restraint"]["i"]["k_knm_per_rad"] *= 2
        actual = produce_story_basis(source, local, changed, uid, cases)
        self.assertEqual(actual["story_inputs"]["M2"], baseline["story_inputs"]["M2"])
        self.assertLess(actual["story_inputs"]["M3"]["k"], baseline["story_inputs"]["M3"]["k"])
        self.assertGreater(actual["story_inputs"]["M3"]["story_aggregates"]["G"]["nk_kn"],
                           baseline["story_inputs"]["M3"]["story_aggregates"]["G"]["nk_kn"])
