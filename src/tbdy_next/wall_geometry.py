"""VS08: observed ETABS wall-panel geometry, not full wall design approval.

TBDY 2018 7.6.1.2 definition and ordinary (a) branch only. An ETABS area
panel is not automatically the physical wall/arm. Its length is never used
as the unrestrained length required by (b). Basement and special branches
remain explicit applicability gaps; 7.6.1.1 axial resistance is not evaluated.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any, Mapping, Sequence

from .physical_story_scope import _digest, geometry_fingerprint, verified_excluded_stories
from .quick_checks import CheckDefinition
from .story_delta import dec
from .story_drift_binding import _verify_generic_capture
from .story_geometry import read_source_table, read_story_levels

CHECK = CheckDefinition("WALL_GEOMETRY_CHECK", "Perde kesit geometrisi — kaynak alt koşulları",
                        13, "TBDY 2018 7.6.1.2 / 7.6.1.2(a)", "GEOMETRY_SCREENING")
TOL = Decimal("0.000001")
WALLS = "Wall Object Connectivity"
AREAS = "Area Assignments - Section Properties"
PROPERTIES = "Wall Property Definitions - Specified"
POINTS = "Point Object Connectivity"


def _positive(value: Any, name: str) -> Decimal:
    result = dec(value, name)
    if result <= 0:
        raise ValueError("WALL_NONPOSITIVE_" + name)
    return result


def geometry_subconditions(*, panel_length_m: Any, thickness_m: Any,
                            story_height_m: Any) -> dict[str, Any]:
    """Pure arithmetic under the stated ordinary-branch / panel-length assumptions."""
    length, thickness, height = (_positive(v, k) for v, k in (
        (panel_length_m, "PANEL_LENGTH"), (thickness_m, "THICKNESS"), (story_height_m, "STORY_HEIGHT")))
    with localcontext() as ctx:
        ctx.prec = 35
        ratio = length / thickness
        height_minimum = height * 1000 / 16
        minimum = max(Decimal(250), height_minimum)
        values = (("panel_ratio", ratio, Decimal(6), length >= 6 * thickness, "ratio"),
                  ("thickness_250", thickness * 1000, Decimal(250), thickness >= Decimal(".25"), "mm"),
                  ("thickness_h16", thickness * 1000, height_minimum, 16 * thickness >= height, "mm"))
        return {
            "panel_length_m": str(length), "thickness_mm": str(thickness * 1000),
            "story_height_m": str(height), "panel_length_thickness_ratio": str(ratio),
            "ordinary_branch_minimum_mm": str(minimum),
            "subconditions": [{"rule": key, "value": str(value), "limit": str(limit),
                "operator": ">=", "unit": unit,
                "status": "MEETS_SUBCONDITION" if met else "DOES_NOT_MEET_SUBCONDITION"}
                for key, value, limit, met, unit in values],
        }


def rectangular_vertical_panel(points: Sequence[Mapping[str, Any]]) -> dict[str, Decimal]:
    """Resolve a four-corner vertical rectangle in any global plan orientation."""
    if len(points) != 4:
        raise ValueError("WALL_FOUR_CORNERS_REQUIRED")
    xyz = sorted((dec(p["X"], "X"), dec(p["Y"], "Y"), dec(p["Z"], "Z")) for p in points)
    xyz.sort(key=lambda p: p[2])
    if len(set(xyz)) != 4:
        raise ValueError("WALL_DUPLICATE_CORNER_COORDINATES")
    lower, upper = xyz[:2], xyz[2:]
    if abs(lower[0][2] - lower[1][2]) > TOL or abs(upper[0][2] - upper[1][2]) > TOL:
        raise ValueError("WALL_NONRECTANGULAR_OR_SLOPED_PANEL")
    close_xy = lambda a, b: all(abs(a[i] - b[i]) <= TOL for i in (0, 1))
    if not (all(close_xy(lower[i], upper[i]) for i in (0, 1)) or
            all(close_xy(lower[i], upper[1-i]) for i in (0, 1))):
        raise ValueError("WALL_NONVERTICAL_OR_NONRECTANGULAR_PANEL")
    with localcontext() as ctx:
        ctx.prec = 35
        length = sum((lower[1][i] - lower[0][i]) ** 2 for i in (0, 1)).sqrt()
        zmin, zmax = min(p[2] for p in xyz), max(p[2] for p in xyz)
        height = zmax - zmin
        if min(length, height) <= TOL:
            raise ValueError("WALL_DEGENERATE_PANEL")
        return {"length_m": length, "panel_height_m": height,
                "lower_elevation_m": zmin, "upper_elevation_m": zmax,
                "area_m2": length * height, "perimeter_m": 2 * (length + height)}


def _index(rows: list[dict], field: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        key = row[field]
        if not key or key != key.strip() or key in result:
            raise ValueError("WALL_DUPLICATE_OR_EMPTY_IDENTITY:" + field)
        result[key] = row
    return result


def bind_wall_geometry(snapshot: Mapping[str, Any], *,
                       physical_scope: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Derive from the existing verified same-run snapshot; no new ETABS reads."""
    result = {**CHECK.as_dict(), "schema": "tbdy.next.vs08.wall-geometry.v1",
        "dag_node_id": CHECK.check_id, "dag_declared_dependencies": ["ASSIGNMENT_GATE", "MATERIAL_SECTION_GATE"],
        "dag_execution_authority": "DENIED", "status": "BLOCKED_SOURCE",
        "numeric_condition": "GEOMETRY_SOURCE_UNRESOLVED", "coverage_known": False,
        "expected_count": 0, "evaluated_count": 0, "not_proven_count": 0,
        "not_applicable_count": 0, "subconditions_evaluated": 0,
        "subconditions_met": 0, "subconditions_unmet": 0, "items": [], "reason_codes": [],
        "source_payload_sha256": None, "story_source_payload_sha256": None,
        "material_facts_sha256": None, "source_inventory_complete": False,
        "inventory_scope": "OBSERVED_WALL_OBJECT_UNION_NOT_APPROVED_PHYSICAL_WALL_GROUPS",
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
        "full_geometry_compliance": "NOT_PROVEN", "numerical_pass_issued": False,
        "unevaluated_requirements": [
            {"code_ref": "7.6.1", "status": "NOT_PROVEN", "reason": "BASEMENT_AND_DUCTILITY_APPLICABILITY_NOT_QUALIFIED"},
            {"code_ref": "7.6.1.2", "status": "NOT_PROVEN", "reason": "PHYSICAL_WALL_OR_ARM_LENGTH_NOT_QUALIFIED"},
            {"code_ref": "7.6.1.2(b)", "status": "NOT_PROVEN", "reason": "UNRESTRAINED_PLAN_LENGTH_NOT_PROVEN"},
            {"code_ref": "7.6.1.2(c)", "status": "NOT_PROVEN", "reason": "BOTH_ENDS_LATERAL_WALL_RESTRAINT_NOT_PROVEN"},
            {"code_ref": "7.6.1.3", "status": "NOT_PROVEN", "reason": "WALL_ONLY_SYSTEM_AND_EQ_7_14_NOT_PROVEN"},
            {"code_ref": "13.1.6", "status": "NOT_PROVEN", "reason": "HIGH_RISE_300_MM_REQUIREMENT_NOT_QUALIFIED"},
            {"code_ref": "7.6.1.1", "status": "NOT_PROVEN", "reason": "NET_SECTION_AXIAL_RESISTANCE_NOT_EVALUATED"},
        ],
        "assumptions_notes": [
            "Uzunluk, ETABS alan nesnesinin panel uzunluğudur; bütün fiziksel perde/kol boyu olduğu onaylanmamıştır.",
            "Standart 7.6.1.2(a) dalında bw ≥ max(250 mm, h_kat/16) sayısal olarak karşılaştırılır. Panelin kısmi yüksekliği kat yüksekliğinin yerine kullanılmaz.",
            "Bodrum, iki ucundan perdeyle tutulu kol ve 7.6.1.3 istisnaları kesit adından veya kat kotundan seçilmez.",
            "7.6.1.2(b) için tutulmamış plan boyu kanıtlanmadığından bu koşul hesaplanmaz; panel boyu yerine geçirilmez.",
            "Sayısal alt koşul sonucu resmî perde geometrisi, eksenel dayanım veya bina uygunluğu kararı değildir.",
        ]}
    try:
        geometry = snapshot.get("vs06_b1_geometry_source")
        story_source = snapshot.get("vs05_delta_source")
        for src in (geometry, story_source):
            if not isinstance(src, Mapping):
                raise ValueError("WALL_GEOMETRY_OR_STORY_SOURCE_ABSENT")
            _verify_generic_capture(src)
            if (src.get("schema") != "tbdy.next.etabs.generic-source-capture.v1"
                    or src.get("status") not in ("CAPTURED", "PARTIAL", "SOURCE_PARTIAL")
                    or src.get("model_locked") is not True or src.get("model_units_code") != 6
                    or src.get("model_units_unchanged") is not True or src.get("selection_restored") is not True):
                raise ValueError("WALL_SOURCE_CONTEXT_INVALID")
        if (geometry.get("model") != story_source.get("model")
                or geometry_fingerprint(geometry) != geometry_fingerprint(story_source)):
            raise ValueError("WALL_GEOMETRY_STORY_CAPTURE_CONFLICT")
        levels, _ = read_story_levels(story_source)
        levels = {r.story: r for r in levels}
        excluded = verified_excluded_stories(physical_scope, geometry, inventory_source=story_source)
        mats = snapshot.get("geometry_capture") or {}
        material_types = mats.get("material_types") or {}
        if (mats.get("schema") != "tbdy.next.geometry.capture.v2" or mats.get("present_units") != 6
                or mats.get("present_units_after") != 6 or mats.get("unit_state_unchanged") is not True
                or material_types.get("source_api") != "PropMaterial.GetTypeOAPI"
                or not isinstance(material_types.get("facts"), Mapping)):
            raise ValueError("WALL_MATERIAL_TYPE_SOURCE_UNAVAILABLE")
        facts = material_types["facts"]
        walls = _index(read_source_table(geometry, WALLS,
            ("UniqueName", "Story", "UniquePt1", "UniquePt2", "UniquePt3", "UniquePt4"), {}), "UniqueName")
        areas = _index(read_source_table(geometry, AREAS,
            ("UniqueName", "Story", "SectProp", "PropType"), {}), "UniqueName")
        properties = _index(read_source_table(geometry, PROPERTIES,
            ("Name", "Material", "Thickness", "ModelType"), {"Thickness": "m"}), "Name")
        points = _index(read_source_table(geometry, POINTS,
            ("UniqueName", "X", "Y", "Z"), {k: "m" for k in "XYZ"}), "UniqueName")
        expected = sorted(set(walls) | {uid for uid, r in areas.items() if r["PropType"] == "Wall"})
        native_rows = ((story_source.get("physical_object_inventory") or {}).get("objects") or {}).get("Area", [])
        if not isinstance(native_rows, list):
            raise ValueError("WALL_NATIVE_POLYGON_ROWS_INVALID")
        native = {}
        for entry in native_rows:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("name"), str) or not entry["name"]:
                raise ValueError("WALL_NATIVE_POLYGON_IDENTITY_INVALID")
            native.setdefault(entry["name"], []).append(entry)
        result.update(coverage_known=True, expected_count=len(expected),
            source_payload_sha256=geometry["payload_sha256"], story_source_payload_sha256=story_source["payload_sha256"],
            material_facts_sha256=_digest(facts),
            source_inventory_complete=bool(physical_scope and physical_scope.get("source_inventory_complete")))
        for uid in expected:
            wall, assignment = walls.get(uid), areas.get(uid)
            row = {"element_id": uid, "story": (wall or assignment)["Story"],
                   "section": assignment.get("SectProp") if assignment else None,
                   "status": "NOT_PROVEN", "reason": None, "subconditions": []}
            try:
                if not wall or not assignment or assignment["PropType"] != "Wall" or wall["Story"] != assignment["Story"]:
                    raise ValueError("WALL_CONNECTIVITY_ASSIGNMENT_MISMATCH")
                story = levels.get(wall["Story"])
                if story is None or story.story in excluded:
                    raise ValueError("WALL_STORY_IDENTITY_OR_EMPTY_SCOPE_CONFLICT")
                prop = properties.get(assignment["SectProp"])
                if prop is None:
                    raise ValueError("WALL_PROPERTY_NOT_RESOLVED")
                material = facts.get(prop["Material"], {})
                if not isinstance(material, Mapping):
                    raise ValueError("WALL_MATERIAL_TYPE_UNRESOLVED")
                code = material.get("material_type_code")
                row["material_name"] = prop["Material"]
                if material.get("status") != "TYPE_RESOLVED" or type(code) is not int or code not in range(1, 9):
                    raise ValueError("WALL_MATERIAL_TYPE_UNRESOLVED")
                if code != 2:
                    row.update(status="NOT_APPLICABLE", reason="PROVEN_NON_CONCRETE_MATERIAL")
                else:
                    if prop["ModelType"] not in ("Shell-Thin", "Shell-Thick", "Membrane"):
                        raise ValueError("WALL_PROPERTY_MODEL_TYPE_UNSUPPORTED")
                    refs = [wall["UniquePt" + str(i)] for i in range(1, 5)]
                    if len(set(refs)) != 4 or any(p not in points for p in refs):
                        raise ValueError("WALL_ENDPOINT_MISSING_OR_REPEATED")
                    if uid in native:
                        if len(native[uid]) != 1:
                            raise ValueError("WALL_NATIVE_POLYGON_DUPLICATE_IDENTITY")
                        obj = native[uid][0]
                        names = obj.get("point_names")
                        if (type(obj.get("return_code")) is not int or obj["return_code"] != 0
                                or not isinstance(names, list) or len(names) != 4
                                or any(not isinstance(p, str) for p in names) or set(names) != set(refs)):
                            raise ValueError("WALL_NATIVE_FULL_POLYGON_CONFLICT")
                    dims = rectangular_vertical_panel([points[p] for p in refs])
                    if (dims["lower_elevation_m"] < story.elevation_m - story.height_m - TOL
                            or dims["upper_elevation_m"] > story.elevation_m + TOL):
                        raise ValueError("WALL_PANEL_OUTSIDE_ASSIGNED_STORY")
                    meta = geometry["table_reads"][WALLS]["field_metadata"]["units_by_field"]
                    reconciliation = {}
                    for field, key, unit in (("Area", "area_m2", "m2"), ("Perimeter", "perimeter_m", "m")):
                        if field in wall:
                            observed = _positive(wall[field], field)
                            # Observed ETABS table rounds these fields to two
                            # decimals. Preserve a finer supplied precision;
                            # never widen the rounding allowance beyond .005.
                            rounding = min(Decimal(".005"), Decimal(1).scaleb(observed.as_tuple().exponent) / 2)
                            tolerance = rounding + max(Decimal(".00001"), dims[key] * Decimal(".000001"))
                            residual = observed - dims[key]
                            reconciliation[field] = {"source": str(observed), "derived": str(dims[key]),
                                "residual": str(residual), "tolerance": str(tolerance), "unit": unit}
                            if meta.get(field) != unit or abs(residual) > tolerance:
                                raise ValueError("WALL_PANEL_GEOMETRY_CROSSCHECK_CONFLICT:" + field)
                    row.update(geometry_subconditions(panel_length_m=dims["length_m"],
                        thickness_m=prop["Thickness"], story_height_m=story.height_m),
                        panel_height_m=str(dims["panel_height_m"]), point_ids=refs,
                        geometry_reconciliation=reconciliation,
                        status="SOURCE_NUMERICAL", applicability="PHYSICAL_WALL_AND_CODE_BRANCH_NOT_QUALIFIED")
            except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                row.update(status="NOT_PROVEN", reason=str(exc))
            result["items"].append(row)
        rows = result["items"]
        evaluated = sum(r["status"] == "SOURCE_NUMERICAL" for r in rows)
        na = sum(r["status"] == "NOT_APPLICABLE" for r in rows)
        unmet = sum(s["status"] == "DOES_NOT_MEET_SUBCONDITION" for r in rows for s in r["subconditions"])
        missing = len(rows) - evaluated - na
        result.update(evaluated_count=evaluated, not_proven_count=missing, not_applicable_count=na,
            subconditions_evaluated=3 * evaluated, subconditions_met=3 * evaluated - unmet,
            subconditions_unmet=unmet,
            status="PARTIAL_SOURCE_NUMERICAL" if evaluated and missing else "SOURCE_NUMERICAL" if evaluated else
                   "NOT_APPLICABLE" if na and not missing else "BLOCKED_SOURCE",
            numeric_condition="EVALUATED_SUBCONDITION_NOT_MET" if unmet else "SOURCE_GEOMETRY_PARTIAL" if missing else
                              "EVALUATED_SUBCONDITIONS_MET" if evaluated else "GEOMETRY_SOURCE_UNRESOLVED",
            reason_codes=sorted({r["reason"] for r in rows if r["reason"]}))
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        result["reason_codes"] = [str(exc)]
    return {**result, "result_sha256": _digest(result)}
