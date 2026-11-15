"""Display groups for verified frame checks. Per-member results remain authoritative."""
from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Iterable, Mapping


_GEOMETRY_FIELDS = (
    "section", "assigned_section", "analysis_section", "design_section",
    "section_design_difference", "material_name", "material_type_code", "material_classification",
    "width_mm", "depth_mm", "value", "limit", "unit", "ratio", "status", "reason",
)
_KINDS = {"column_rect_min": "Column", "beam_width_min": "Beam"}
_DIGITS = re.compile(r"[0-9]+")


def _members_by_story(items: Iterable[Mapping[str, Any]]) -> list[dict]:
    stories = defaultdict(set)
    for item in items:
        stories[item.get("story")].add(item.get("element_id"))
    return [
        {"story": story, "member_ids": sorted(ids, key=lambda value: (value is None, str(value))),
         "member_ids_text": member_id_text(ids)}
        for story, ids in stories.items()
    ]


def geometry_groups(items: Iterable[Mapping[str, Any]]) -> list[dict]:
    """Group exactly equal check inputs and results within one check."""
    grouped = defaultdict(list)
    for item in items:
        grouped[tuple(item.get(key) for key in _GEOMETRY_FIELDS)].append(item)
    return [
        dict(zip(_GEOMETRY_FIELDS, key), member_count=len(rows), members_by_story=_members_by_story(rows))
        for key, rows in grouped.items()
    ]


def material_member_groups(checks: Iterable[Mapping[str, Any]]) -> list[dict]:
    """Use one verified roster per member type to avoid counting beams three times."""
    grouped = defaultdict(list)
    for check in checks:
        kind = _KINDS.get(check["check_id"])
        if kind is None:
            continue
        for item in check.get("items", []):
            material_class = item.get("material_classification")
            name = item.get("material_name")
            if material_class is None:
                if item.get("reason") == "MATERIAL_TYPE_UNRESOLVED":
                    material_class = "MATERIAL_TYPE_UNRESOLVED"
                else:
                    material_class = "ASSIGNED_MATERIAL_OBSERVED" if name else "MATERIAL_LINK_NOT_PROVEN"
            key = name, kind, material_class
            grouped[key].append(item)
    return [
        {"material_name": name, "member_type": kind, "material_classification": status,
         "member_count": len(rows), "members_by_story": _members_by_story(rows)}
        for (name, kind, status), rows in grouped.items()
    ]


def member_id_text(ids: Iterable[str | None]) -> str:
    """Compress exact consecutive canonical integer IDs. Preserve all other labels."""
    numbers, labels = set(), set()
    for identity in ids:
        if identity is None:
            labels.add("—")
        elif len(identity) <= 20 and _DIGITS.fullmatch(identity) and str(int(identity)) == identity:
            numbers.add(int(identity))
        else:
            labels.add(identity)
    spans = []
    for value in sorted(numbers):
        if spans and spans[-1][1] + 1 == value:
            spans[-1] = (spans[-1][0], value)
        else:
            spans.append((value, value))
    return ", ".join([str(start) if start == end else f"{start}–{end}" for start, end in spans] + sorted(labels))
