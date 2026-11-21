"""Public synthetic source for one actual normal-pipeline calculation.

This is a one-story 800 mm column with two roof beams and a top-aligned mat.
All tables and signed force vectors are explicit fixture inputs. They are not an
ETABS solve, original-model evidence, or an independently validated structure.
The configured force-cut census is supplied independently of returned forces.
No selected cage, section resistance, R10/R08 outcome or closure is fabricated.
"""
from copy import deepcopy
from hashlib import sha256
import json

from tbdy_next.column_engine.native_archive import digest
from tbdy_next.engineering.analysis_setup import (
    ADOPTED_ANALYSIS_SCHEMA, DESIGN_COMBOS, STATIC_CASES, bind_analysis_setup,
)
from tbdy_next.engineering.column_axial import PREFERENCES
from tbdy_next.engineering.column_r10_live import (
    ANALYSIS_FRAME_ELEMENTS, FRAME_OUTPUT_STATIONS, END_OFFSETS,
    BEAM_REINFORCING, BEAM_DESIGN_SUMMARY, RELEASES,
)
from tbdy_next.engineering.design_scenario import SCHEMA, _digest, _source_data
from tbdy_next.engineering.second_order_basis import SCHEMA as BASIS_SCHEMA, NONSWAY_POLICY
from tbdy_next.etabs_geometry import (
    FRAME_INSERTION, AREA_INSERTION, SLAB_PROPERTIES, FLOOR_CONNECTIVITY, AREA_ELEMENTS,
)
from tbdy_next.etabs_source_gateway_windows import seal
from tbdy_next.story_second_order import CAPTURE_SCHEMA, WEIGHT_TERMS
from tbdy_next.vs05_d4_source_authority import COMBOS, SUMMARY
from test_quick_suite import fake_live_suite, tab
from test_r03_analysis_setup import capture_table
from test_r10_live import _pmm_sec_source, _rowset
from test_vs03 import source as material_source


MODEL = "C:/synthetic/vertical_slice.edb"
COMBINATIONS = ("G", "G+EX", "G-EX", "G+EY", "G-EY")
GROUPS = {"gravity": ["G"], "ductile": list(COMBINATIONS[1:]),
          "capacity": list(COMBINATIONS[1:]), "joint": list(COMBINATIONS[1:]),
          "wall": list(COMBINATIONS[1:]), "drift": list(COMBINATIONS[1:]), "weight": ["G"]}
CUTS = (0., 1.25, 2.5)


def table(name, fields, rows, units=None, *, version=1, omitted=()):
    columns = fields.split() if isinstance(fields, str) else list(fields)
    result = capture_table(name, columns, rows)
    result["api_signature"] = "seven_list"
    result["field_metadata"].update(table_version=version, field_keys=columns + list(omitted))
    result["field_metadata"]["units_by_field"].update(units or {})
    return result


def generic(reads):
    return seal({"schema": "tbdy.next.etabs.generic-source-capture.v1", "action": "capture",
                 "status": "CAPTURED", "model": MODEL, "model_locked": True,
                 "model_units_code": 6, "model_units_unchanged": True,
                 "selection_restored": True, "analysis_generation_proven": False,
                 "table_reads": reads})


def global_source():
    definitions = table("Story Definitions", "Story Tower Height", [("S1", "T1", "3")], {"Height": "m"})
    base = table("Tower and Base Story Definitions", "Tower BSName BSElev", [("T1", "Base", "0")], {"BSElev": "m"})
    weight_terms = table("Load Combination Definitions", "Name Type LoadName SF", [
        ("WGHT", "Linear Add" if index == 0 else "None", key, str(value))
        for index, (key, value) in enumerate(WEIGHT_TERMS.items())])
    rs = generic({"Story Definitions": definitions, "Tower and Base Story Definitions": base,
        "Load Combination Definitions": weight_terms,
        "Base Reactions": table("Base Reactions", "OutputCase CaseType StepType", [
            (name, "LinRespSpec", "Max") for name in ("RSX", "RSY")]),
        "Story Forces": table("Story Forces", "Story OutputCase CaseType Location VX VY", [
            ("S1", name, "LinRespSpec", "Bottom", "25", "20") for name in ("RSX", "RSY")], {"VX": "kN", "VY": "kN"}),
        "Story Max Over Avg Drifts": table("Story Max Over Avg Drifts",
            ["Story", "OutputCase", "CaseType", "Direction", "Avg Drift"], [
                ("S1", "RSX", "LinRespSpec", "X", ".001"),
                ("S1", "RSY", "LinRespSpec", "Y", ".001")], {"Avg Drift": "m"})})
    weights = generic({"Story Forces": table("Story Forces", "Story OutputCase CaseType Location P",
                      [("S1", "WGHT", "Combination", "Bottom", "500")], {"P": "kN"}),
        "Base Reactions": table("Base Reactions", "OutputCase CaseType FZ",
                                [("WGHT", "Combination", "500")], {"FZ": "kN"})})
    return {"schema": CAPTURE_SCHEMA, "status": "CAPTURED", "same_sapmodel_session": True,
            "combination_selection_restored": True, "analysis_generation_proven": False,
            "configuration_approved": False, "configuration": {
                "live_model_basename": "vertical_slice.edb", "x_case": "RSX", "y_case": "RSY",
                "weight_combo": "WGHT", "R": "7", "D": "2.5", "Ch": ".5"},
            "model": MODEL, "spectrum_source": rs, "weight_source": weights}


def source():
    data = fake_live_suite("Modal")
    data["capture_metadata"].update(model_filename=MODEL, model_locked_observed=True,
        vs04_same_session_capture=True, evidence_role="PUBLIC_SYNTHETIC_GETTER_FIXTURE_NOT_ETABS_EXECUTION")
    data["example_context"] = {"classification": "CONTRACT_FIXTURE", "origin": "GENERATED_OFFLINE_NOT_ETABS",
                               "name": "One-story signed column and roof-joint calculation"}
    data["next_capture"] = material_source()
    a1 = data["next_capture"]["a1_table"]
    a1["rows"] = [dict(row, Story="S1") for row in a1["rows"][:2]]
    a1["row_count"] = 2
    tables = data["geometry_capture"]["tables"]
    frames = [("S1", "C1", "Column", "C80", "C80", "0", "C1"),
              ("S1", "B1", "Beam", "B60x50", "B60x50", "0", "B1"),
              ("S1", "B2", "Beam", "B60x50", "B60x50", "0", "B2")]
    tables["FRAME_ASSIGNMENTS"] = tab("FRAME_ASSIGNMENTS",
        ["Story", "UniqueName", "Type", "AnalysisSect", "DesignSect", "AxisAngle", "Label"], frames)
    tables["FRAME_ASSIGNMENTS"]["field_metadata"]["units_by_field"]["AxisAngle"] = "deg"
    tables["SECTION_ASSIGNMENTS"] = tab("SECTION_ASSIGNMENTS", ["Story", "UniqueName", "SectProp"],
                                       [(r[0], r[1], r[3]) for r in frames])
    tables["COLUMN_CONNECTIVITY"] = tab("COLUMN_CONNECTIVITY",
        ["Story", "UniqueName", "ColumnBay", "UniquePtI", "UniquePtJ", "Length"],
        [("S1", "C1", "C1", "P0", "P1", "3")], {"Story": "", "UniqueName": "", "ColumnBay": "", "UniquePtI": "", "UniquePtJ": "", "Length": "m"})
    tables["BEAM_CONNECTIVITY"] = tab("BEAM_CONNECTIVITY",
        ["Story", "UniqueName", "BeamBay", "UniquePtI", "UniquePtJ", "Length"],
        [("S1", "B1", "B1", "P1", "P2", "5"), ("S1", "B2", "B2", "P1", "P3", "5")], {"Length": "m"})
    tables["RECTANGULAR_SECTIONS"] = tab("RECTANGULAR_SECTIONS", ["Name", "t2", "t3", "Material"],
        [("C80", ".8", ".8", "C35/45"), ("B60x50", ".6", ".5", "C35/45")], {"t2": "m", "t3": "m"})
    tables["SECTION_SUMMARY"] = tab("SECTION_SUMMARY",
        ["Name", "Area", "Shape", "Material", "I2Mod", "I3Mod", "AMod", "JMod"],
        [("C80", ".64", "Concrete Rectangular", "C35/45", ".7", ".7", "1", "1"),
         ("B60x50", ".30", "Concrete Rectangular", "C35/45", ".35", ".35", "1", "1")])
    points = [("P0", "Base", "0", "0", "0"), ("P1", "S1", "0", "0", "3"),
              ("P2", "S1", "5", "0", "3"), ("P3", "S1", "0", "5", "3"),
              ("S0", "Base", "-1", "-1", "0"), ("S1", "Base", "1", "-1", "0"),
              ("S2", "Base", "1", "1", "0"), ("S3", "Base", "-1", "1", "0")]
    point_table = table("Point Object Connectivity", "UniqueName Story X Y Z", points, dict.fromkeys("XYZ", "m"))
    r08 = global_source()
    data["r08_second_order_source"] = r08
    drift_reads = deepcopy(r08["spectrum_source"]["table_reads"])
    drift_reads["Point Object Connectivity"] = point_table
    data["vs05_delta_source"] = generic(drift_reads)

    case_roles = {"LC_DL": "GRAVITY", "LC_SDL": "GRAVITY", "LC_WDL": "GRAVITY",
                  "LC_DDL": "GRAVITY", "LC_LL": "GRAVITY", "EX": "STATIC_SEISMIC",
                  "EY": "STATIC_SEISMIC", "RSX": "RESPONSE_SPECTRUM", "RSY": "RESPONSE_SPECTRUM",
                  "Modal": "MODAL"}
    combination_rows = [("G", "Linear Add", "LC_DL", "1", "combo-G")]
    for name, case, factor in (("G+EX", "EX", "1"), ("G-EX", "EX", "-1"),
                                ("G+EY", "EY", "1"), ("G-EY", "EY", "-1")):
        combination_rows.extend([(name, "Linear Add", "LC_DL", "1", "combo-" + name),
                                 (name, "None", case, factor, "None")])
    reads = {
        SUMMARY: table(SUMMARY, "Name Type GUID", [(name, {"RESPONSE_SPECTRUM": "Response Spectrum", "MODAL": "Modal - Ritz"}.get(role, "Linear Static"), "case-" + name) for name, role in case_roles.items()]),
        COMBOS: table(COMBOS, "Name Type LoadName SF GUID", combination_rows),
        DESIGN_COMBOS: table(DESIGN_COMBOS, "ComboName ComboType", [(name, "Strength") for name in COMBINATIONS]),
        STATIC_CASES: table(STATIC_CASES, "Name StiffType NonlinCase LoadType LoadName LoadSF", [(name, "Unstressed", "None", "Load", name, "1") for name, role in case_roles.items() if role not in {"RESPONSE_SPECTRUM", "MODAL"}]),
        "Load Pattern Definitions": table("Load Pattern Definitions", "Name Type SelfWtMult", [(name, "Quake" if role == "STATIC_SEISMIC" else "Live" if name == "LC_LL" else "Dead", "1" if name == "LC_DL" else "0") for name, role in case_roles.items() if role not in {"RESPONSE_SPECTRUM", "MODAL"}]),
    }
    data["vs04_basis_probe"] = {"schema": "tbdy.next.vs04e.basis-source-probe.v1", "source_mode": "LIVE_ETABS",
        "read_only_invariant_proven": True, "units_before": 6, "units_after": 6,
        "display_cases_before": [], "display_cases_after": [], "table_reads": reads}
    setup = bind_analysis_setup(data)
    request = {"check": "column-pmm", "pmm_member": "ALL", "member": "ALL", "base_run_id": "RUN-PUBLIC-SYNTHETIC",
        "base_input_sha256": "f" * 64, "model_filename": MODEL, "combination_source": "ASSIGNED_DESIGN",
        "combinations": sorted(COMBINATIONS), "combination_graph_sha256": setup["typed_graph_source_sha256"],
        "design_assignment": {"groups": deepcopy(GROUPS)}}
    forces = []
    for name in COMBINATIONS:
        sx = 1 if name == "G+EX" else -1 if name == "G-EX" else 0
        sy = 1 if name == "G+EY" else -1 if name == "G-EY" else 0
        for station in CUTS:
            forces.append(("C1", station, "C1-elm", station, name, "Single Value", 0.,
                           -500., 25. * sx, 20. * sy, 0., 30. + (2.5 - station) * 20. * sy,
                           30. + (2.5 - station) * 25. * sx))
    offsets = table(END_OFFSETS, "Story UniqueName OffsetI OffsetJ",
                    [("S1", "C1", "0", ".5"), ("S1", "B1", ".4", ".4"), ("S1", "B2", ".4", ".4")], {"OffsetI": "m", "OffsetJ": "m"})
    frame_offsets = ("XI", "YI", "ZI", "XJ", "YJ", "ZJ")
    shell_offsets = ("Offset1", "Offset2", "Offset3")
    r10_reads = {
        ANALYSIS_FRAME_ELEMENTS: table(ANALYSIS_FRAME_ELEMENTS, "Story ObjType ObjName ElmName ElmJtI ElmJtJ", [("S1", "Frame", "C1", "C1-elm", "P0", "P1")]),
        FRAME_OUTPUT_STATIONS: table(FRAME_OUTPUT_STATIONS, "Story UniqueName StationOpt MaxSpacing MinStations", [("S1", "C1", "Min Stations", "None", "3")], {"MaxSpacing": "m"}),
        END_OFFSETS: offsets,
        RELEASES: table(RELEASES, "UniqueName M2I M3I M2J M3J", [(uid, "No", "No", "No", "No") for uid in ("B1", "B2")]),
        FRAME_INSERTION: table(FRAME_INSERTION, "UniqueName Story Label CardinalPt Mirror2 Mirror3", [("C1", "S1", "C1", "10 (Centroid)", "No", "No"), ("B1", "S1", "B1", "8 (Top Center)", "No", "No"), ("B2", "S1", "B2", "8 (Top Center)", "No", "No")], dict.fromkeys(frame_offsets, "m"), omitted=frame_offsets + ("OffsetCSys",)),
        AREA_INSERTION: table(AREA_INSERTION, "UniqueName Story Label CardinalPt", [("MAT", "Base", "MAT", "Top")], dict.fromkeys(shell_offsets, "m"), version=2, omitted=shell_offsets + ("CoordSys", "PointLabel", "PointName", "PointNumber")),
        SLAB_PROPERTIES: table(SLAB_PROPERTIES, "Name PropType ModelType Thickness", [("MAT1", "Mat", "Shell-Thick", ".9")], {"Thickness": "m"}),
        FLOOR_CONNECTIVITY: table(FLOOR_CONNECTIVITY, "UniqueName Story FloorBay UniquePt1 UniquePt2 UniquePt3 UniquePt4", [("MAT", "Base", "MAT", "S0", "S1", "S2", "S3")]),
        AREA_ELEMENTS: table(AREA_ELEMENTS, "Story ElmName ObjType ObjName ObjLabel ElmJt1 ElmJt2 ElmJt3", [("Base", "MAT-1", "Floor", "MAT", "MAT", "P0", "S0", "S1")]),
        "Objects and Elements - Joints": table("Objects and Elements - Joints", "ElmName ObjName ObjType Story GlobalX GlobalY GlobalZ", [(uid, uid, "Joint", story, x, y, z) for uid, story, x, y, z in points], dict.fromkeys(("GlobalX", "GlobalY", "GlobalZ"), "m")),
        BEAM_REINFORCING: table(BEAM_REINFORCING, "Name RebarMatL RebarMatC CoverTop CoverBot TopLeftArea TopRightArea BotLeftArea BotRightArea", [("B60x50", "B420C", "B420C", ".05", ".05", "0", "0", "0", "0")], {"CoverTop": "m", "CoverBot": "m", **dict.fromkeys(("TopLeftArea", "TopRightArea", "BotLeftArea", "BotRightArea"), "m2")}),
        BEAM_DESIGN_SUMMARY: table(BEAM_DESIGN_SUMMARY, "Story Label UniqueName DesignSect Station Status AsTopCombo AsMinTop AsTop AsBotCombo AsMinBot AsBot TLngCombo TLngRebar totTopRebar totBotRebar WarnMsg ErrMsg", [("S1", uid, uid, "B60x50", station, "No Message", "G", ".0005", ".0009", "G", ".0005", ".0009", "G", "0", ".0009", ".0009", "No Message", "No Message") for uid in ("B1", "B2") for station in (".4", "4.6")], {"Station": "m", **dict.fromkeys(("AsMinTop", "AsTop", "AsMinBot", "AsBot", "TLngRebar", "totTopRebar", "totBotRebar"), "m2")}),
    }
    b1 = {"model": MODEL, "source_only": True, "model_locked": True, "model_units_code": 6,
          "model_units_unchanged": True, "case_selection_before": [], "case_selection_after": [], "selection_restored": True,
          "table_reads": {"Point Object Connectivity": point_table,
              "Area Assignments - Section Properties": table("Area Assignments - Section Properties", "UniqueName Story Label PropType SectProp", [("MAT", "Base", "MAT", "Slab", "MAT1")])}}
    b1["payload_sha256"] = digest(b1)
    data["vs06_b1_geometry_source"] = b1
    data["column_axial"] = {"request": request, "design_preferences": capture_table(PREFERENCES, ["GammaC", "GammaS"], [("1.5", "1.15")]),
        "pmm_section_source": _pmm_sec_source(name="C80", bars2="9", bars3="9", spacing=".09"),
        "force_source": {"schema": "tbdy.next.etabs-frame-force-source.v1", "api": "Results.FrameForce",
            "item_type": "ObjectElm", "units_code": 6, "output_selection_before": {"cases": {}, "combos": {}},
            "output_selection_after": {"cases": {}, "combos": {}},
            "output_selection_during": {"cases": {}, "combos": dict.fromkeys(COMBINATIONS, True)},
            "errors": {}, "rowsets": {"C1": _rowset(forces)}},
        "r10_source": {"schema": "tbdy.next.r10-live-source.v1", "model_locked_before": True,
                       "model_locked_after": True, "units_before": 6, "units_after": 6,
                       "table_reads": r10_reads, "table_errors": {}, "beam_force_source": {"rowsets": {
                           uid: _rowset([(uid, station, uid + "-elm", station, "G", "Single Value", 0., 0., shear, 0., 0., 0., -50.) for station, shear in ((.4, 20.), (4.6, -20.))]) for uid in ("B1", "B2")}}}}
    return data, case_roles


def _add_upper_story(data):
    """Extend the source geometry/forces to an interior joint, without outcomes."""
    def append(record, values):
        record["rows"].extend(dict(zip(record["fields"], row, strict=True)) for row in values)
        record["row_count"] = len(record["rows"])

    data["example_context"]["name"] = "Two-story signed columns with an interior beam-column joint"
    tables = data["geometry_capture"]["tables"]
    append(tables["FRAME_ASSIGNMENTS"], [("S2", "C2", "Column", "C80", "C80", "0", "C2"),
        ("S2", "B3", "Beam", "B60x50", "B60x50", "0", "B3"),
        ("S2", "B4", "Beam", "B60x50", "B60x50", "0", "B4")])
    append(tables["SECTION_ASSIGNMENTS"], [("S2", "C2", "C80"), ("S2", "B3", "B60x50"), ("S2", "B4", "B60x50")])
    append(tables["COLUMN_CONNECTIVITY"], [("S2", "C2", "C2", "P1", "P4", "3")])
    append(tables["BEAM_CONNECTIVITY"], [("S2", "B3", "B3", "P4", "P5", "5"), ("S2", "B4", "B4", "P4", "P6", "5")])
    points = [("P4", "S2", "0", "0", "6"), ("P5", "S2", "5", "0", "6"), ("P6", "S2", "0", "5", "6")]
    b1 = data["vs06_b1_geometry_source"]
    append(b1["table_reads"]["Point Object Connectivity"], points)
    b1["payload_sha256"] = digest({key: value for key, value in b1.items() if key != "payload_sha256"})
    reads = data["column_axial"]["r10_source"]["table_reads"]
    append(reads[ANALYSIS_FRAME_ELEMENTS], [("S2", "Frame", "C2", "C2-elm", "P1", "P4")])
    append(reads[FRAME_OUTPUT_STATIONS], [("S2", "C2", "Min Stations", "None", "3")])
    append(reads[END_OFFSETS], [("S2", "C2", "0", ".5"), ("S2", "B3", ".4", ".4"), ("S2", "B4", ".4", ".4")])
    append(reads[RELEASES], [(uid, "No", "No", "No", "No") for uid in ("B3", "B4")])
    append(reads[FRAME_INSERTION], [("C2", "S2", "C2", "10 (Centroid)", "No", "No"),
        ("B3", "S2", "B3", "8 (Top Center)", "No", "No"), ("B4", "S2", "B4", "8 (Top Center)", "No", "No")])
    append(reads["Objects and Elements - Joints"], [(uid, uid, "Joint", story, x, y, z) for uid, story, x, y, z in points])
    summaries = reads[BEAM_DESIGN_SUMMARY]
    for row in deepcopy(summaries["rows"]):
        uid = "B3" if row["UniqueName"] == "B1" else "B4"
        summaries["rows"].append(dict(row, UniqueName=uid, Label=uid, Story="S2"))
    summaries["row_count"] = len(summaries["rows"])
    beam_rows = data["column_axial"]["r10_source"]["beam_force_source"]["rowsets"]
    for uid in ("B3", "B4"):
        beam_rows[uid] = _rowset([(uid, station, uid + "-elm", station, "G", "Single Value", 0., 0., shear, 0., 0., 0., -50.) for station, shear in ((.4, 20.), (4.6, -20.))])
    rowsets = data["column_axial"]["force_source"]["rowsets"]
    rowsets["C1"]["P"] = [-2500.] * rowsets["C1"]["NumberResults"]
    rowsets["C2"] = deepcopy(rowsets["C1"])
    rowsets["C2"].update(Obj=["C2"] * rowsets["C2"]["NumberResults"],
        Elm=["C2-elm"] * rowsets["C2"]["NumberResults"], P=[-1500.] * rowsets["C2"]["NumberResults"])
    global_capture = data["r08_second_order_source"]
    rs = global_capture["spectrum_source"]["table_reads"]
    rs["Story Definitions"]["rows"].insert(0, {"Story": "S2", "Tower": "T1", "Height": "3"})
    rs["Story Definitions"]["row_count"] = 2
    append(rs["Story Forces"], [("S2", name, "LinRespSpec", "Bottom", "25", "20") for name in ("RSX", "RSY")])
    append(rs["Story Max Over Avg Drifts"], [("S2", "RSX", "LinRespSpec", "X", ".001"), ("S2", "RSY", "LinRespSpec", "Y", ".001")])
    weights = global_capture["weight_source"]["table_reads"]
    weights["Story Forces"]["rows"][0]["P"] = "2500"
    append(weights["Story Forces"], [("S2", "WGHT", "Combination", "Bottom", "1500")])
    weights["Base Reactions"]["rows"][0]["FZ"] = "2500"
    global_capture["spectrum_source"] = generic(rs)
    global_capture["weight_source"] = generic(weights)
    drift_reads = deepcopy(rs)
    drift_reads["Point Object Connectivity"] = deepcopy(b1["table_reads"]["Point Object Connectivity"])
    data["vs05_delta_source"] = generic(drift_reads)
    a1 = data["next_capture"]["a1_table"]
    a1["rows"].extend(dict(row, Story="S2") for row in deepcopy(a1["rows"]))
    a1["row_count"] = len(a1["rows"])


def source_and_request(*, k=1., rm=0., two_story=False, column_tie_diameter=None, column_tie_spacing=None):
    data, case_roles = source()
    if two_story:
        _add_upper_story(data)
    native_sha = _digest(_source_data(data))
    analysis = {"schema": ADOPTED_ANALYSIS_SCHEMA, "basis_id": "public-synthetic-first-order",
        "basis_role": "ADOPTED_CALCULATION_ASSUMPTIONS", "engineering_approval": "NOT_GRANTED",
        "source_data_sha256": native_sha, "decision_reference": "Synthetic fixture input, no solver execution",
        "model_profile": {"profile_id": "public-two-story-frame" if two_story else "public-one-story-column", "structural_system": "FRAME", "ductility_level": "HIGH", "decision_reference": "Synthetic two-story frame with interior and roof joints" if two_story else "Synthetic one-story frame with roof joint"},
        "case_roles": case_roles, "design_groups": deepcopy(GROUPS),
        "generation": {"analysis_run_id": "SYNTHETIC-NOT-ETABS", "source_analysis_order": "FIRST_ORDER", "completed_case_names": sorted(case_roles), "decision_reference": "Adopted first-order scenario"}}
    second = {"schema": BASIS_SCHEMA, "basis_id": "public-synthetic-local-basis", "basis_role": "ADOPTED_CALCULATION_ASSUMPTIONS",
        "engineering_approval": "NOT_GRANTED", "source_data_sha256": native_sha, "source_analysis_order": "FIRST_ORDER",
        "source_order_reference": "Synthetic first-order source vectors", "global_factor_policy": NONSWAY_POLICY,
        "global_factor_reference": "Real global owner evaluates synthetic drift, weight and shear source tables",
        "members": {uid: {"combinations": sorted(COMBINATIONS), "applicability": "TS500_7_6_2_CONSTANT_SECTION_AND_AXIAL_FORCE", "decision_reference": "Prismatic synthetic member with constant compression along its own height",
            "axes": {axis: {"k": k, "creep_ratio_rm": rm, "ei_method": "TS500_7_20", "sway": "SWAY_PREVENTED", "cm_policy": "UNITY", "eq729_length_reading": "NOT_APPLICABLE", "decision_reference": "Adopted fixture sensitivity; not approval", "story_aggregates": {}} for axis in ("M2", "M3")}} for uid in (("C1", "C2") if two_story else ("C1",))}}
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    request = {"schema": SCHEMA, "scenario_id": "public-vertical-slice", "parent_input_sha256": sha256(raw).hexdigest(),
        "beam_selection": {"stirrup_confinement": {"diameter_mm": 10, "legs": 4, "spacing_mm": 90},
                           "stirrup_span": {"diameter_mm": 10, "legs": 4, "spacing_mm": 90}},
        "column_selection": {"tie_diameter_preference_mm": [column_tie_diameter or (12 if two_story else 10)],
                             "stirrup_confinement_spacing_mm": column_tie_spacing or (70 if two_story else 90),
                             "stirrup_span_spacing_mm": column_tie_spacing or (70 if two_story else 90)},
        "analysis_basis": analysis, "second_order_basis": second}
    return raw, request
