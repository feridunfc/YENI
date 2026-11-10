"""One physical-object applicability scope for B1, B2 and story drift.

Absence requires an independently enumerated, stable all-object identity set,
complete frame/area connectivity, and every point's global coordinates.
This source census does not authorize the seismic analysis or code compliance.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any, Mapping

from .story_drift_binding import _verify_generic_capture
from .story_geometry import read_source_table, read_story_levels
from .story_delta import dec

SCHEMA = "tbdy.next.physical-story-scope.v1"
INVENTORY_SCHEMA = "tbdy.next.etabs.physical-object-inventory.v1"
TOLERANCE = Decimal("0.000001")


def _digest(value: Any) -> str:
    return sha256((json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False) + "\n").encode()).hexdigest()


def _index(rows: list[dict], key: str) -> dict[str, dict]:
    if not isinstance(rows, list) or any(not isinstance(r, Mapping) for r in rows):
        raise ValueError("PHYSICAL_OBJECT_ROWS_INVALID:" + key)
    result = {}
    for row in rows:
        name = row.get(key)
        if not isinstance(name, str) or not name or name != name.strip() or name in result:
            raise ValueError("PHYSICAL_DUPLICATE_OR_INVALID_ID:" + key)
        result[name] = row
    return result


def geometry_fingerprint(source: Mapping[str, Any]) -> str:
    points = read_source_table(source, "Point Object Connectivity",
                               ("UniqueName", "X", "Y", "Z"), {x: "m" for x in "XYZ"})
    heights = read_source_table(source, "Story Definitions", ("Tower", "Story", "Height"), {"Height": "m"})
    return _digest({
        "points": sorted((r["UniqueName"], *(r[k] for k in "XYZ")) for r in points),
        "heights": sorted((r["Tower"], r["Story"], r["Height"]) for r in heights),
    })


def verified_excluded_stories(scope: Mapping[str, Any] | None,
                              source: Mapping[str, Any], *,
                              inventory_source: Mapping[str, Any] | None = None) -> set[str]:
    """Consumers cannot apply a foreign or edited applicability projection."""
    if scope is None or scope.get("source_inventory_complete") is not True:
        return set()
    if (scope.get("schema") != SCHEMA or scope.get("model") != source.get("model")
            or scope.get("scope_sha256") != _digest({k: v for k, v in scope.items() if k != "scope_sha256"})
            or scope.get("geometry_fingerprint") != geometry_fingerprint(source)):
        raise ValueError("PHYSICAL_SCOPE_SOURCE_BINDING_CONFLICT")
    origin = source if inventory_source is None else inventory_source
    if (origin.get("payload_sha256") != scope.get("source_payload_sha256")
            or review_physical_story_scope(origin) != dict(scope)):
        raise ValueError("PHYSICAL_SCOPE_SOURCE_REPLAY_CONFLICT")
    if scope.get("source_payload_sha256") != source.get("payload_sha256"):
        # B1 uses another sealed geometry capture from the same SapModel.
        # Match all object identities and its resolved column/wall topology;
        # model filename and story names alone cannot authorize an exclusion.
        _verify_generic_capture(source)
        for kind, key in (("Frame", "Frame Assignments - Section Properties"),
                          ("Area", "Area Assignments - Section Properties")):
            rows = read_source_table(source, key, ("UniqueName",), {})
            ids = sorted(_index(rows, "UniqueName"))
            if _digest(ids) != scope["object_identity_sha256"][kind]:
                raise ValueError("PHYSICAL_SCOPE_OBJECT_IDENTITY_CONFLICT:" + kind)
        for kind, key, fields in (
            ("Column", "Column Object Connectivity", ("UniquePtI", "UniquePtJ")),
            ("Wall", "Wall Object Connectivity", ("UniquePt1", "UniquePt2", "UniquePt3", "UniquePt4")),
        ):
            rows = read_source_table(source, key, ("UniqueName", *fields), {})
            topology = sorted((r["UniqueName"], sorted(r[k] for k in fields)) for r in rows)
            if _digest(topology) != scope["resistance_topology_sha256"][kind]:
                raise ValueError("PHYSICAL_SCOPE_RESISTANCE_TOPOLOGY_CONFLICT:" + kind)
    excluded = {r["story"] for r in scope["stories"] if r["applicability"] == "NOT_APPLICABLE"}
    if excluded != set(scope["excluded_stories"]):
        raise ValueError("PHYSICAL_SCOPE_EXCLUSION_CONFLICT")
    return excluded


def review_physical_story_scope(source: Mapping[str, Any] | None) -> dict[str, Any]:
    scope = {"schema": SCHEMA, "status": "PHYSICAL_SCOPE_UNKNOWN",
             "source_inventory_complete": False, "source_payload_sha256": None,
             "model": None, "geometry_fingerprint": None, "stories": [],
             "defined_story_count": 0, "physical_story_count": None,
             "excluded_stories": [], "object_counts": {}, "reason_codes": [],
             "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
    try:
        if not isinstance(source, Mapping):
            raise ValueError("PHYSICAL_SOURCE_ABSENT")
        _verify_generic_capture(source)
        if (source.get("schema") != "tbdy.next.etabs.generic-source-capture.v1"
                or source.get("status") not in ("CAPTURED", "PARTIAL", "SOURCE_PARTIAL")
                or source.get("model_locked") is not True or source.get("model_units_code") != 6
                or source.get("model_units_unchanged") is not True or source.get("selection_restored") is not True):
            raise ValueError("PHYSICAL_SOURCE_CONTEXT_INVALID")
        levels, _ = read_story_levels(source)
        scope.update(model=source.get("model"), source_payload_sha256=source["payload_sha256"],
                     defined_story_count=len(levels), geometry_fingerprint=geometry_fingerprint(source))
        scope["stories"] = [{"story": s.story, "lower_elevation_m": str(s.elevation_m - s.height_m),
                             "upper_elevation_m": str(s.elevation_m), "height_m": str(s.height_m),
                             "applicability": "UNKNOWN", "reason": "COMPLETE_OBJECT_CENSUS_NOT_PROVEN",
                             "frames": None, "areas": None, "walls": None, "joints": None} for s in levels]
        probe = source.get("physical_object_inventory")
        if (not isinstance(probe, Mapping) or probe.get("schema") != INVENTORY_SCHEMA
                or probe.get("status") != "CAPTURED" or probe.get("scope") != "ALL_MODEL_OBJECTS"
                or probe.get("model_locked_before") is not True or probe.get("model_locked_after") is not True):
            raise ValueError("PHYSICAL_ALL_OBJECT_INVENTORY_NOT_CAPTURED")
        names = {}
        for kind in ("Frame", "Area", "Joint"):
            sets = []
            for when in ("names_before", "names_after"):
                entry = probe[when][kind]
                if not isinstance(entry, Mapping):
                    raise ValueError("PHYSICAL_NAME_SET_INVALID:" + kind)
                count, ids = entry["count"], entry["names"]
                if (type(count) is not int or count < 0
                        or type(entry.get("return_code")) is not int or entry["return_code"] != 0
                        or not isinstance(ids, list) or len(ids) != count
                        or any(not isinstance(x, str) or not x or x != x.strip() for x in ids)
                        or len(set(ids)) != count):
                    raise ValueError("PHYSICAL_NAME_SET_INVALID:" + kind)
                sets.append(set(ids))
            if sets[0] != sets[1]:
                raise ValueError("PHYSICAL_NAME_SET_CHANGED:" + kind)
            names[kind] = sets[0]
        points = _index(read_source_table(source, "Point Object Connectivity",
                         ("UniqueName", "X", "Y", "Z"), {x: "m" for x in "XYZ"}), "UniqueName")
        if set(points) != names["Joint"]:
            raise ValueError("PHYSICAL_JOINT_CENSUS_MISMATCH")
        for point in points.values():
            for axis in "XYZ":
                dec(point[axis], "PHYSICAL_POINT_" + axis)
        point_z = {name: dec(row["Z"], "PHYSICAL_POINT_Z") for name, row in points.items()}
        tables = {"table_reads": probe["table_reads"]}
        for kind, key in (("Frame", "Frame Assignments - Summary"),
                          ("Area", "Area Assignments - Section Properties")):
            raw = probe["table_reads"].get(key, {})
            if not names[kind] and (raw.get("rows") or raw.get("row_count", 0) not in (None, 0)):
                raise ValueError("PHYSICAL_ZERO_POPULATION_CONTRADICTION:" + kind)
        frames = (_index(read_source_table(tables, "Frame Assignments - Summary",
                           ("UniqueName", "Type"), {}), "UniqueName") if names["Frame"] else {})
        areas = (_index(read_source_table(tables, "Area Assignments - Section Properties",
                          ("UniqueName", "PropType"), {}), "UniqueName") if names["Area"] else {})
        if set(frames) != names["Frame"] or set(areas) != names["Area"]:
            raise ValueError("PHYSICAL_ASSIGNMENT_CENSUS_MISMATCH")
        wall_names = {name for name, row in areas.items() if row["PropType"] == "Wall"}
        wall_table = probe["table_reads"].get("Wall Object Connectivity", {})
        if wall_names or wall_table.get("rows"):
            walls = _index(read_source_table(tables, "Wall Object Connectivity", ("UniqueName",), {}), "UniqueName")
            if set(walls) != wall_names:
                raise ValueError("PHYSICAL_WALL_CENSUS_MISMATCH")
        spans = {"Frame": [], "Area": []}
        for kind in spans:
            objects = _index(probe["objects"][kind], "name")
            if set(objects) != names[kind]:
                raise ValueError("PHYSICAL_CONNECTIVITY_CENSUS_MISMATCH:" + kind)
            for name, row in objects.items():
                refs = row["point_names"]
                if (type(row.get("return_code")) is not int or row["return_code"] != 0
                        or not isinstance(refs, list)
                        or (len(refs) != 2 if kind == "Frame" else len(refs) < 3)
                        or any(not isinstance(x, str) or x not in points for x in refs)
                        or len(set(refs)) != len(refs)):
                    raise ValueError("PHYSICAL_ENDPOINT_OR_POLYGON_UNRESOLVED:" + kind + ":" + name)
                zs = [point_z[x] for x in refs]
                spans[kind].append((name, min(zs), max(zs)))
        rows = []
        for level, original in zip(levels, scope["stories"]):
            lower, upper = level.elevation_m - level.height_m, level.elevation_m
            # Lower-boundary-only roof/floor objects belong to the level below.
            # A long/inclined object crossing the band prevents an empty verdict
            # even when there is no joint or matching Story label in that band.
            overlaps = lambda lo, hi: hi > lower and lo <= upper + TOLERANCE
            fs = [name for name, lo, hi in spans["Frame"] if overlaps(lo, hi)]
            ar = [name for name, lo, hi in spans["Area"] if overlaps(lo, hi)]
            joint_count = sum(overlaps(z, z) for z in point_z.values())
            empty = not (fs or ar or joint_count)
            if empty:
                for key in ("Story Drifts", "Story Max Over Avg Drifts"):
                    if any(r.get("Story") == level.story for r in source.get("table_reads", {}).get(key, {}).get("rows", [])):
                        raise ValueError("PHYSICAL_EMPTY_STORY_HAS_ANALYSIS_ROWS:" + level.story)
            rows.append({**original, "applicability": "NOT_APPLICABLE" if empty else "IN_SCOPE",
                         "reason": "VERIFIED_EMPTY_PHYSICAL_STORY" if empty else "PHYSICAL_OBJECTS_INTERSECT_STORY_BAND",
                         "frames": len(fs), "areas": len(ar), "walls": len(set(ar) & wall_names),
                         "joints": joint_count})
        excluded = [r["story"] for r in rows if r["applicability"] == "NOT_APPLICABLE"]
        column_names = {name for name, row in frames.items() if row["Type"] == "Column"}
        topology = {
            kind: _digest(sorted((r["name"], sorted(r["point_names"]))
                                 for r in probe["objects"][family] if r["name"] in ids))
            for kind, family, ids in (("Column", "Frame", column_names), ("Wall", "Area", wall_names))
        }
        scope.update(status="PHYSICAL_SOURCE_CENSUS_COMPLETE", source_inventory_complete=True,
                     stories=rows, excluded_stories=excluded, physical_story_count=len(levels) - len(excluded),
                     object_identity_sha256={k: _digest(sorted(v)) for k, v in names.items()},
                     resistance_topology_sha256=topology,
                     object_counts={**{k: len(v) for k, v in names.items()}, "Wall": len(wall_names)})
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        scope["reason_codes"] = [str(exc)]
    return {**scope, "scope_sha256": _digest(scope)}


def scope_story_drift(record: Mapping[str, Any], source: Mapping[str, Any],
                      scope: Mapping[str, Any]) -> dict[str, Any]:
    excluded = verified_excluded_stories(scope, source)
    if not excluded or record.get("execution_status") != "EXECUTED_SOURCE_NUMERICAL":
        return dict(record)
    if record.get("source_payload_sha256") != source.get("payload_sha256"):
        raise ValueError("PHYSICAL_DRIFT_SOURCE_MISMATCH")
    projected = deepcopy(dict(record))
    projected["declared_source_coverage"] = {key: record[key] for key in (
        "expected_story_case_direction_count", "evaluated_story_case_direction_count", "all_stories_covered")}
    projected["items"] = [r for r in record["items"] if r["story"] not in excluded]
    projected["missing_story_case_direction"] = [r for r in record["missing_story_case_direction"] if r["story"] not in excluded]
    projected["expected_story_case_direction_count"] = record["expected_story_case_direction_count"] - 4 * len(excluded)
    projected["evaluated_story_case_direction_count"] = len(projected["items"])
    complete = len(projected["items"]) == projected["expected_story_case_direction_count"]
    projected.update(all_stories_covered=complete, physical_scope_sha256=scope["scope_sha256"],
                     excluded_stories=[r for r in scope["stories"] if r["story"] in excluded],
                     status="SOURCE_COVERAGE_COMPLETE" if complete else "NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE",
                     uncovered_stories=[s for s in record.get("uncovered_stories", []) if s not in excluded],
                     reason_codes=[] if complete else ["INCOMPLETE_STORY_DRIFT_CASE_COVERAGE"])
    if projected["expected_story_case_direction_count"] < 0:
        raise ValueError("PHYSICAL_DRIFT_DENOMINATOR_INVALID")
    return projected
