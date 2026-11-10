"""Shared, source-bound story geometry; no engineering applicability decision."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping
from .archived_source_bridge import _source_table
from .story_delta import dec, story_heights

STORIES = "Story Definitions"
BASE = "Tower and Base Story Definitions"

@dataclass(frozen=True)
class StoryLevel:
    story: str
    elevation_m: Decimal
    height_m: Decimal


def read_source_table(source: Mapping[str, Any], name: str, fields: tuple[str, ...],
          units: Mapping[str, str]) -> list[dict[str, str]]:
    tables = source.get("table_reads")
    if not isinstance(tables, Mapping) or not isinstance(tables.get(name), Mapping):
        raise ValueError("B2_SOURCE_TABLE_MISSING:" + name)
    if tables[name].get("table_key") != name:
        raise ValueError("B2_SOURCE_TABLE_IDENTITY_CONFLICT:" + name)
    return _source_table(tables, name, fields, units)


def read_story_levels(source: Mapping[str, Any]) -> tuple[list[StoryLevel], dict]:
    heights = story_heights(source)
    rows = read_source_table(source, STORIES, ("Tower", "Story", "Height"), {"Height": "m"})
    bases = read_source_table(source, BASE, ("Tower", "BSName", "BSElev"), {"BSElev": "m"})
    if len(bases) != 1 or any(r["Tower"] != bases[0]["Tower"] for r in rows):
        raise ValueError("B2_SINGLE_TOWER_BASE_REQUIRED")
    base = bases[0]
    if (any(not base[k] or base[k] != base[k].strip() or base[k] == "None"
            for k in ("Tower", "BSName")) or base["BSName"] in heights):
        raise ValueError("B2_BASE_STORY_IDENTITY_INVALID")
    if any(not r["Story"] or r["Story"] != r["Story"].strip() or r["Story"] == "None" for r in rows):
        raise ValueError("B2_STORY_IDENTITY_INVALID")
    z = dec(base["BSElev"], "B2_BASE_ELEVATION")
    levels = []
    # Reuse the observed ETABS top-to-bottom ordering convention from
    # archived_source_bridge. This is a disclosed candidate, not a census.
    for row in reversed(rows):
        z += heights[row["Story"]]
        levels.append(StoryLevel(row["Story"], z, heights[row["Story"]]))
    point_levels = set()
    point_counts = {s.story: {
        "story": s.story, "lower_elevation_m": str(s.elevation_m - s.height_m),
        "upper_elevation_m": str(s.elevation_m), "at_level_points": 0,
        "intermediate_points": 0, "lower_boundary_points": 0,
    } for s in levels}
    point_table = (source.get("table_reads") or {}).get("Point Object Connectivity")
    points_captured = isinstance(point_table, Mapping) and point_table.get("status") == "CAPTURED"
    if points_captured:
        points = read_source_table(source, "Point Object Connectivity",
                       ("UniqueName", "Story", "Z"), {"Z": "m"})
        bounds = {s.story: (s.elevation_m - s.height_m, s.elevation_m) for s in levels}
        tolerance = Decimal("0.000001")
        for row in points:
            if row["Story"] in bounds:
                lower, upper = bounds[row["Story"]]
                point_z = dec(row["Z"], "B2_POINT_Z")
                # A point assigned to a story may lie inside its vertical span.
                # Only points at its upper plane corroborate the story elevation;
                # neither interior points nor lower-boundary points move a level.
                if point_z < lower - tolerance or point_z > upper + tolerance:
                    raise ValueError("B2_STORY_ORDER_POINT_ELEVATION_CONFLICT:" + row["Story"])
                counts = point_counts[row["Story"]]
                if abs(point_z - upper) <= tolerance:
                    point_levels.add(row["Story"])
                    counts["at_level_points"] += 1
                elif abs(point_z - lower) <= tolerance:
                    counts["lower_boundary_points"] += 1
                else:
                    counts["intermediate_points"] += 1
    return levels, {
        "basis": "OBSERVED_TOP_TO_BOTTOM_TABLE_ORDER_PLUS_BASE_AND_HEIGHTS",
        "base_story": base["BSName"], "base_elevation_m": base["BSElev"],
        "point_elevation_confirmed_stories": sorted(point_levels),
        "stories_without_point_elevation_confirmation": [
            s.story for s in levels if s.story not in point_levels],
        "point_table_captured": points_captured,
        "point_story_span_counts": list(point_counts.values()),
        "intermediate_point_count": sum(r["intermediate_points"] for r in point_counts.values()),
        "lower_boundary_point_count": sum(r["lower_boundary_points"] for r in point_counts.values()),
        "full_physical_census_proven": False,
    }
