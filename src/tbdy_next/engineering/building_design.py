"""Building results from the physical inventory and the outputs of this same engine run."""
from collections import Counter

from ..etabs_geometry import SLAB_PROPERTIES
from .confinement_regions import frame_confinement
from .wall_boundary import wall_boundaries


def _inventory(table, key):
    if not table or table.get("status") != "CAPTURED":
        return None
    rows = table.get("rows")
    if not isinstance(rows, list) or table.get("row_count") != len(rows):
        return None
    by_id = {r[key]: r for r in rows if isinstance(r, dict) and isinstance(r.get(key), str) and r[key]}
    return by_id if len(by_id) == len(rows) else None


def _area_population(source):
    tables = (source.get("column_axial", {}).get("r10_source") or {}).get("table_reads", {})
    geometry = (source.get("vs06_b1_geometry_source") or {}).get("table_reads", {})
    assignments = _inventory(geometry.get("Area Assignments - Section Properties"), "UniqueName")
    if assignments is None:
        assignments = _inventory(tables.get("Area Assignments - Section Properties"), "UniqueName")
    properties = _inventory(tables.get(SLAB_PROPERTIES), "Name")
    result = {"wall": None, "slab": None, "mat": None, "diaphragm": None}
    if assignments is not None:
        result["wall"] = sum(r.get("PropType") == "Wall" for r in assignments.values())
        floors = [r for r in assignments.values() if r.get("PropType") == "Slab"]
        if properties is not None and all(r.get("SectProp") in properties for r in floors):
            types = Counter(properties[r["SectProp"]]["PropType"] for r in floors)
            result["mat"] = types["Mat"]
            if set(types) <= {"Slab", "Mat", "Ribbed", "Waffle", "Drop"}:
                result["slab"] = len(floors) - types["Mat"]
    diaphragms = (source.get("vs04_diaphragm_probe") or {}).get("diaphragm_tables", {})
    assignments = [_inventory(diaphragms.get(key), "UniqueName") for key in
                   ("Area Assignments - Diaphragms", "Joint Assignments - Diaphragms")]
    definitions = _inventory(diaphragms.get("Diaphragm Definitions"), "Name")
    if definitions is not None and all(a is not None for a in assignments):
        # Include a joint-only assignment. Automatic floor assignments carry no additional named diaphragm.
        pairs = {(r.get("Story"), r.get("Diaphragm")) for a in assignments for r in a.values()
                 if r.get("Diaphragm") in definitions}
        result["diaphragm"] = len(pairs)
    return result


def building_results(source, stages, evidence):
    tables = (source.get("geometry_capture") or {}).get("tables", {})
    columns = _inventory(tables.get("COLUMN_CONNECTIVITY"), "UniqueName")
    beams = _inventory(tables.get("BEAM_CONNECTIVITY"), "UniqueName")
    closure = {r["member_id"]: r for r in (stages.get("r14_closure") or {}).get("columns", ())}
    frames = (stages.get("r08_local_slenderness") or {}).get("building_frame_design") or {}
    storeys, column_rows = {}, []
    for uid, physical in (columns or {}).items():
        story = physical["Story"]
        outcome = closure.get(uid, {})
        frame = frames.get("storeys", {}).get(story, {}).get("columns", {}).get(uid, {})
        counts = storeys.setdefault(story, {"expected": 0, "conditional": 0, "hold": 0, "failed": 0})
        counts["expected"] += 1
        state = ("failed" if outcome.get("normative_failures") else "conditional"
                 if outcome.get("status") == "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES" else "hold")
        counts[state] += 1
        column_rows.append({"member_id": uid, "label": physical["ColumnBay"], "story": story, "status": state,
            "basis": frame.get("basis"), "reason": frame.get("reason") or frames.get("hold"),
            "failures": outcome.get("normative_failures", []),
            "open_gates": outcome.get("open_gates", ["COLUMN_DESIGN_INPUT_UNAVAILABLE"])})
    calculated = {b["member_id"]: b for b in (stages.get("beam_r10") or {}).get("beams", ())}
    beam_counts = Counter()
    governing = None
    for uid, physical in (beams or {}).items():
        selected = calculated.get(uid, {}).get("selected_design") or {}
        beam_counts[selected.get("status", "HOLD")] += 1
        for check, utilization in selected.get("utilizations", {}).items():
            if governing is None or utilization > governing["utilization"]:
                governing = {"member_id": uid, "label": physical["BeamBay"], "story": physical["Story"],
                             "check": check, "utilization": utilization, "full_ve_kn": selected["full_ve_kn"],
                             "resistance_kn": selected["resistances_kn"][check]}
    checks = []
    def add(name, expected, evaluated, outcome):
        checks.append({"name": name, "expected": expected, "evaluated": evaluated, "outcome": outcome})

    modal = stages.get("result") or {}
    add("Modal participating mass X/Y", 2, sum(modal.get(k) is not None for k in ("sum_ux", "sum_uy")),
        modal.get("status", "HOLD"))
    for group in (stages.get("geometry"), stages.get("extra")):
        for item in (group or {}).get("checks", ()):
            add(item["check_id"], item.get("expected_count"), item.get("evaluated_count"), item.get("status"))
    seismic = stages.get("vs04_pipeline") or {}
    for item in seismic.get("checks", ()):
        add(item["check_id"], item.get("expected_count"), item.get("evaluated_count"), item.get("status"))
    for item in (evidence.get("earthquake_combinations") or {}).get("checks", ()):
        add(item["check_id"], item.get("expected_count"), item.get("evaluated_count"), item.get("status"))
    for key, name, shape in (("story_drift", "Occupied-storey drift", "story_case_direction"),
                             ("r08_second_order", "Global second-order precheck", "story_direction")):
        item = evidence.get(key) or {}
        add(name, item.get("expected_" + shape + "_count"), item.get("evaluated_" + shape + "_count", 0),
            item.get("status", "HOLD"))
    b1 = (evidence.get("vs06_b1_result") or {}).get("b1_numerical") or {}
    add("B1 weak-storey comparisons", b1.get("expected_story_direction_pairs"),
        b1.get("computed_story_direction_pairs", 0), b1.get("numeric_condition", "HOLD"))
    for key, name in (("soft_story_b2", "B2 soft-storey comparisons"), ("wall_geometry", "Wall geometry")):
        item = evidence.get(key) or {}
        add(name, item.get("expected_count"), item.get("evaluated_count", 0), item.get("numeric_condition", "HOLD"))
    axial = stages.get("column_axial") or {}
    add("Column axial compression by assigned combination", axial.get("expected_member_combination_count"),
        axial.get("evaluated_member_combination_count", 0), axial.get("status", "HOLD"))
    beam_count = None if beams is None else len(beams)
    column_count = None if columns is None else len(columns)
    add("Selected beam flexure and capacity shear", beam_count, beam_counts["CONDITIONAL_DESIGN_CALCULATED"] +
        beam_counts["NUMERICAL_EXCEEDANCE"], "NUMERICAL_EXCEEDANCE" if beam_counts["NUMERICAL_EXCEEDANCE"] else
        "HOLD" if beams is None or beam_counts["HOLD"] else "CONDITIONAL_DESIGN_CALCULATED")
    states = Counter(r["status"] for r in column_rows)
    add("End-to-end column design", column_count, states["conditional"] + states["failed"],
        "NUMERICAL_EXCEEDANCE" if states["failed"] else "HOLD" if columns is None or states["hold"] else "CONDITIONAL_DESIGN_CALCULATED")
    areas = _area_population(source)
    detailing = frame_confinement(source, columns, beams, stages)
    section_table = (source.get("vs06_b1_geometry_source") or {}).get("table_reads", {})
    assignments = _inventory(section_table.get("Area Assignments - Section Properties"), "UniqueName")
    walls = None if assignments is None else {uid: row for uid, row in assignments.items() if row["PropType"] == "Wall"}
    boundaries = wall_boundaries(source, stages, evidence, walls)
    for family, population, title in (("columns", column_count, "Column confinement schedules"),
                                      ("beams", beam_count, "Beam confinement schedules on model cuts")):
        rows = detailing[family]
        evaluated = sum(r["status"] in {"SCHEDULE_CALCULATED", "NUMERICAL_EXCEEDANCE"} for r in rows)
        status = ("NUMERICAL_EXCEEDANCE" if any(r["status"] == "NUMERICAL_EXCEEDANCE" for r in rows)
                  else "SCHEDULE_CALCULATED" if population is not None and evaluated == population
                  else "PHYSICAL_FACES_OR_SELECTED_CAGE_REQUIRED")
        add(title, population, evaluated, status)
    face_count = sum(f["basis"] == "COLUMN_JOINT_AND_NATIVE_FACE_CUT" for row in detailing["beams"]
                     if "schedule" in row for f in row["faces"].values())
    add("Beam confinement ends at a connected column face", 2 * beam_count if beam_count is not None else None,
        face_count, "Column half width, native offset and selected design cut agree")
    wall_count = sum(r["status"] == "BOUNDARY_MINIMA_CALCULATED" for r in boundaries["walls"])
    add("Wall objects with two calculated pier boundary zones", areas["wall"], wall_count,
        "Constant rectangular pier detail under two model-base scenarios")
    add("Wall objects with proposed boundary hoops and crossties", areas["wall"],
        sum(r.get("cage_status") == "CONDITIONAL_TRANSVERSE_CAGE_CALCULATED" for r in boundaries["walls"]),
        "Two directions at both ends, TBDY 7.6.5.2")
    for name, population, reason in (
            ("Wall and pier reinforcement", areas["wall"], "Wall section design and detailing owner required"),
            ("Diaphragm collectors and chords", areas["diaphragm"], "Force path and design resistance required"),
            ("Slab flexure and punching", areas["slab"], "Slab design-strip and punching calculations required"),
            ("Mat contact and reinforced concrete design", areas["mat"], "Soil contact and mat design required"),
            ("Beam torsion and serviceability", beam_count, "Torsion, deflection and crack-width checks required"),
            ("Coupling-beam design", None, "Physical coupling-beam classification and design required")):
        add(name, population, 0, reason)
    return {"schema": "tbdy.next.building-results.v1", "checks": checks, "column_count": column_count,
            "column_status_counts": dict(states), "columns": column_rows, "storeys": storeys,
            "beam_count": beam_count, "beam_status_counts": dict(beam_counts), "governing_beam": governing,
            "area_population": areas, "frame_confinement": detailing, "wall_boundaries": boundaries,
            "engineering_release": "NOT_READY"}
