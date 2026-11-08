"""Five project-owned, bounded numerical checks: modal + four RC geometry screens.

The geometry comparisons intentionally DO NOT conclude full TBDY §7.3/§7.4
compliance. Source shape, assigned section, member identity and units are checked
before evaluating *numerical subconditions*. No legacy runtime dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


@dataclass(frozen=True)
class CheckDefinition:
    check_id: str
    title: str
    tab_id: int
    code_ref: str
    category: str

    def as_dict(self) -> dict[str, str | int]:
        return {"check_id": self.check_id, "title": self.title,
                "tab_id": self.tab_id, "code_ref": self.code_ref,
                "category": self.category, "implemented": True}


# The navigation tree is generated from these five actual checks, not a fake count.
CHECKS: tuple[CheckDefinition, ...] = (
    CheckDefinition("modal_mass_95", "Modal etkin kütle ≥ %95", 7, "TBDY 2018 4.8.1.2(a)", "NUMERICAL_SUBCONDITION"),
    CheckDefinition("column_rect_min", "Kolon kısa kenar ≥ 300 mm", 12, "TBDY 2018 7.3.1.1", "GEOMETRY_SCREENING"),
    CheckDefinition("beam_width_min", "Kiriş gövde genişliği ≥ 250 mm", 11, "TBDY 2018 7.4.1.1(a)", "GEOMETRY_SCREENING"),
    CheckDefinition("beam_depth_min", "Kiriş yüksekliği ≥ 300 mm", 11, "TBDY 2018 7.4.1.1(b)", "GEOMETRY_SCREENING"),
    CheckDefinition("beam_depth_width", "Kiriş h/b ≤ 3,5", 11, "TBDY 2018 7.4.1.1(b)", "GEOMETRY_SCREENING"),
)
assert len({c.check_id for c in CHECKS}) == len(CHECKS), "duplicate check id"
GEOMETRY_CHECKS = tuple(c for c in CHECKS if c.category == "GEOMETRY_SCREENING")


def check_registry() -> list[dict[str, Any]]:
    from .next_checks import EXTRA_CHECKS
    from .soft_story_b2 import CHECK as B2_CHECK
    # Existing same-run derivations are navigable checks, not new evaluators.
    # Effective drift is a scenario of STORY_DRIFT, not a duplicate check ID.
    derived = (
        CheckDefinition("STORY_DRIFT", "Göreli / etkin kat ötelemesi", 8,
                        "TBDY 2018 §4.9.1", "SOURCE_NUMERICAL"),
        CheckDefinition("WEAK_STORY_B1", "B1 zayıf kat — koşullu hesap", 9,
                        "TBDY 2018 Tablo 3.6 / §3.6.2.3", "CONDITIONAL_SOURCE_NUMERICAL"),
    )
    panels = {"STORY_DRIFT": "storyDriftPanel",
              "WEAK_STORY_B1": "vs06-b1-panel", "SOFT_STORY_B2": "b2Panel"}
    return [{**c.as_dict(), **({"panel_id": panels[c.check_id]} if c.check_id in panels else {})}
            for c in (*CHECKS, *EXTRA_CHECKS, *derived, B2_CHECK)]


def _numeric(raw: object) -> Decimal:
    if isinstance(raw, bool):
        raise ValueError("Boole değeri boyut olamaz")
    try:
        value = Decimal(str(raw).strip())
    except (ValueError, InvalidOperation):
        raise ValueError(f"Geçersiz kesit boyutu: {raw!r}") from None
    if not value.is_finite() or value <= 0:
        raise ValueError(f"Pozitif sonlu kesit boyutu gerekli: {raw!r}")
    return value


def _aggregate(definition: CheckDefinition, rows: list[dict[str, Any]], reason: str = "") -> dict[str, Any]:
    met = sum(row["status"] == "MEETS_SUBCONDITION" for row in rows)
    unmet = sum(row["status"] == "DOES_NOT_MEET_SUBCONDITION" for row in rows)
    evaluated = met + unmet
    na = sum(row["status"] == "NOT_APPLICABLE" for row in rows)
    unproven = len(rows) - evaluated - na
    status = ("DOES_NOT_MEET_SUBCONDITION" if unmet else
              "PARTIAL" if unproven else
              "MEETS_SUBCONDITION" if evaluated else
              "NOT_APPLICABLE" if na else "NOT_PROVEN")
    return {"check_id": definition.check_id, "title": definition.title,
            "code_ref": definition.code_ref, "category": definition.category,
            "status": status, "expected_count": len(rows), "evaluated_count": evaluated,
            "met_count": met, "unmet_count": unmet,
            "not_proven_count": unproven, "not_applicable_count": na,
            "proven_non_concrete_count": sum(x.get("material_classification") == "PROVEN_NON_CONCRETE" for x in rows),
            "reason": reason, "items": rows, "formal_compliance": "NOT_PROVEN"}


def _not_ready(reason: str, source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = source or {}
    return {"stage": "QUICK_GEOMETRY_SCREENING", "status": "SOURCE_SCHEMA_REVIEW_REQUIRED",
            "reason": reason, "source_units": source.get("present_units"),
            "observed_schemas": {
                name: {"table_key": table.get("table_key"), "fields": table.get("fields", []),
                       "row_count": table.get("row_count"), "status": table.get("status"),
                       "field_metadata": table.get("field_metadata", {}),
                       "error": table.get("error")}
                for name, table in source.get("tables", {}).items() if isinstance(table, Mapping)},
            "checks": [_aggregate(c, [], reason) for c in GEOMETRY_CHECKS],
            "engineering_release": "NOT_READY",
            "scope_note": "Source/schema not qualified; no geometric check was executed"}


def _rows(source: Mapping[str, Any], name: str, fields_needed: set[str]) -> list[Mapping[str, str]]:
    table = source.get("tables", {}).get(name, {})
    if not isinstance(table, Mapping) or table.get("status") != "CAPTURED":
        raise ValueError(f"{name}: source table not captured")
    fields, rows = table.get("fields"), table.get("rows")
    if not isinstance(fields, list) or not fields_needed.issubset(set(fields)):
        raise ValueError(f"{name}: required fields missing; need {sorted(fields_needed)}, observed {fields}")
    if len(fields) != len(set(fields)) or not isinstance(rows, list) or len(rows) != table.get("row_count") or not rows:
        raise ValueError(f"{name}: duplicate fields, empty rows or row-count mismatch")
    if any(not isinstance(row, dict) or set(row) != set(fields) for row in rows):
        raise ValueError(f"{name}: row/header shape mismatch")
    metadata = table.get("field_metadata", {})
    if not isinstance(metadata, Mapping) or metadata.get("status") != "OK":
        raise ValueError(f"{name}: source field-unit metadata unavailable")
    known_fields = metadata.get("field_keys", [])
    if not isinstance(known_fields, list) or not set(fields).issubset(set(known_fields)):
        raise ValueError(f"{name}: display/metadata field mismatch")
    return rows


def _unique(rows: list[Mapping[str, str]], *, id_field: str, story: bool = True) -> dict[tuple[str, str], Mapping[str, str]]:
    out: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        element = str(row[id_field]).strip()
        level = str(row.get("Story", "")).strip() if story else ""
        if not element or (story and not level):
            raise ValueError("MISSING_UNIQUE_NAME_OR_STORY")
        key = (level, element)
        if key in out:
            raise ValueError("DUPLICATE_FRAME_UNIQUE_ID_OR_STORY")
        out[key] = row
    return out


def _unproven(story: str, uid: str, section: str, reason: str, **other: Any) -> dict[str, Any]:
    return {"story": story, "element_id": uid, "section": section,
            "status": "NOT_PROVEN", "reason": reason, "width_mm": None,
            "depth_mm": None, **other}


def evaluate_geometry_capture(source: Mapping[str, Any] | None) -> dict[str, Any]:
    """Member inventory -> exact SectProp join -> rectangular t2/t3 (m) -> mm.

    Only the numerical geometric predicates are evaluated. A beam's membership
    of TBDY §7.4.1.1 or the column's relevant ductility is not inferred from
    ETABS `Type` alone. Such applicability remains unqualified.
    """
    if not isinstance(source, Mapping) or source.get("schema") != "tbdy.next.geometry.capture.v2":
        return _not_ready("MISSING_OR_UNKNOWN_GEOMETRY_CAPTURE_SCHEMA", source)
    if (source.get("present_units") != 6 or source.get("present_units_after") != 6
            or source.get("unit_state_unchanged") is not True):
        return _not_ready("ETABS_PRESENT_UNITS_NOT_STABLE_KN_M_C", source)
    try:
        summary = _rows(source, "FRAME_ASSIGNMENTS", {"Story", "UniqueName", "Type", "AnalysisSect", "DesignSect"})
        assignments = _rows(source, "SECTION_ASSIGNMENTS", {"Story", "UniqueName", "SectProp"})
        section_rows = _rows(source, "RECTANGULAR_SECTIONS", {"Name", "t2", "t3"})
        columns = _rows(source, "COLUMN_CONNECTIVITY", {"Story", "UniqueName"})
        beams = _rows(source, "BEAM_CONNECTIVITY", {"Story", "UniqueName"})
        # Section summary is captured but does not authorize actual dimensions.
        section_summary = _rows(source, "SECTION_SUMMARY", {"Name", "Area", "Shape", "Material"})
        field_units = source["tables"]["RECTANGULAR_SECTIONS"]["field_metadata"]["units_by_field"]
        if field_units.get("t2") != "m" or field_units.get("t3") != "m":
            raise ValueError(f"RECTANGULAR_SECTIONS: t2/t3 units must be m; observed {field_units}")
        summary_by_id = _unique(summary, id_field="UniqueName")
        assigned_by_id = _unique(assignments, id_field="UniqueName")
        column_by_id = _unique(columns, id_field="UniqueName")
        beam_by_id = _unique(beams, id_field="UniqueName")
        if set(column_by_id).intersection(beam_by_id):
            raise ValueError("COLUMN_AND_BEAM_CONNECTIVITY_OVERLAP")
        material_source = source.get("material_types", {})
        if (not isinstance(material_source, Mapping)
                or material_source.get("source_api") != "PropMaterial.GetTypeOAPI"
                or not isinstance(material_source.get("facts"), Mapping)):
            raise ValueError("MATERIAL_TYPE_POPULATION_NOT_CAPTURED")
        material_facts = material_source["facts"]
        section_summary_by_name: dict[str, Mapping[str, str]] = {}
        for row in section_summary:
            name = str(row["Name"]).strip()
            if not name or name in section_summary_by_name:
                raise ValueError("DUPLICATE_OR_EMPTY_SECTION_SUMMARY_IDENTITY")
            section_summary_by_name[name] = row
    except (KeyError, TypeError, ValueError) as exc:
        return _not_ready(str(exc), source)

    by_section: dict[str, tuple[Decimal, Decimal, str]] = {}
    invalid_section_ids: set[str] = set()
    for row in section_rows:
        key = str(row["Name"]).strip()
        if not key or key in by_section or key in invalid_section_ids:
            return _not_ready("DUPLICATE_OR_EMPTY_RECTANGULAR_SECTION_NAME", source)
        try:
            by_section[key] = (_numeric(row["t2"]) * 1000, _numeric(row["t3"]) * 1000, str(row.get("Material", "")).strip())
        except ValueError:
            invalid_section_ids.add(key)

    by_kind: dict[str, list[dict[str, Any]]] = {"column": [], "beam": []}
    connectivity = {"column": column_by_id, "beam": beam_by_id}
    summary_types = {"column": set(), "beam": set()}
    unexpected_types: set[str] = set()
    for key, row in summary_by_id.items():
        kind = str(row["Type"]).strip().casefold()
        if kind in summary_types:
            summary_types[kind].add(key)
        else:
            unexpected_types.add(str(row["Type"]))
    for kind in ("column", "beam"):
        # Use the *union* so orphan connectivity or missing summary cannot vanish
        # from the check denominator.
        for story, uid in sorted(set(connectivity[kind]) | summary_types[kind]):
            src = summary_by_id.get((story, uid))
            conn = connectivity[kind].get((story, uid))
            assignment = assigned_by_id.get((story, uid))
            assigned = str(assignment.get("SectProp", "")).strip() if assignment else ""
            design = str(src.get("DesignSect", "")).strip() if src else ""
            analysis = str(src.get("AnalysisSect", "")).strip() if src else ""
            details = {"design_section": design or None, "analysis_section": analysis or None,
                       "assigned_section": assigned or None,
                       "section_design_difference": bool(design and assigned and design != assigned)}
            if not src or not conn or str(src.get("Type", "")).strip().casefold() != kind:
                item = _unproven(story, uid, assigned, "CONNECTIVITY_SUMMARY_IDENTITY_MISMATCH", **details)
            elif not assignment or not assigned:
                item = _unproven(story, uid, assigned, "SECTPROP_MISSING_FOR_MEMBER", **details)
            elif assigned not in section_summary_by_name:
                item = _unproven(story, uid, assigned, "ASSIGNED_SECTION_DEFINITION_MISSING", **details)
            elif not str(section_summary_by_name[assigned].get("Material", "")).strip():
                item = _unproven(story, uid, assigned, "ASSIGNED_SECTION_MATERIAL_IDENTITY_MISSING", **details)
            elif ((mat := str(section_summary_by_name[assigned]["Material"]).strip()) not in material_facts
                  or material_facts[mat].get("status") != "TYPE_RESOLVED"):
                item = _unproven(story, uid, assigned, "MATERIAL_TYPE_UNRESOLVED", material_name=mat, **details)
            elif material_facts[mat].get("material_type_code") != 2:
                item = {"story": story, "element_id": uid, "section": assigned,
                        "status": "NOT_APPLICABLE", "reason": "PROVEN_NON_CONCRETE_MATERIAL",
                        "material_name": mat, "material_type_code": material_facts[mat]["material_type_code"],
                        "material_classification": "PROVEN_NON_CONCRETE",
                        "width_mm": None, "depth_mm": None, **details}
            elif analysis and analysis != assigned:
                item = _unproven(story, uid, assigned, "ANALYSIS_SECTION_SECTPROP_MISMATCH", material_name=mat, **details)
            elif assigned in invalid_section_ids:
                item = _unproven(story, uid, assigned, "RECTANGULAR_SECTION_DIMENSIONS_INVALID", **details)
            elif assigned not in by_section:
                item = _unproven(story, uid, assigned, "CONCRETE_RECTANGULAR_SECTION_NOT_RESOLVED", material_name=mat, **details)
            elif by_section[assigned][2] and by_section[assigned][2] != mat:
                item = _unproven(story, uid, assigned, "RECTANGULAR_SECTION_MATERIAL_CONFLICT", material_name=mat, **details)
            else:
                width, depth, _ = by_section[assigned]
                item = {"story": story, "element_id": uid, "section": assigned,
                        "material_name": mat, "material_type_code": 2,
                        "material_classification": "RESOLVED_CONCRETE_USAGE",
                        "width_mm": str(width), "depth_mm": str(depth), **details}
            by_kind[kind].append(item)

    checks = []
    for definition in GEOMETRY_CHECKS:
        kind = "column" if definition.tab_id == 12 else "beam"
        items = []
        for member in by_kind[kind]:
            item = dict(member)
            if item.get("status") in {"NOT_PROVEN", "NOT_APPLICABLE"}:
                items.append(item)
                continue
            width = Decimal(item["width_mm"])
            depth = Decimal(item["depth_mm"])
            if definition.check_id == "column_rect_min":
                val, lim, ok, unit = min(width, depth), Decimal("300"), min(width, depth) >= 300, "mm"
            elif definition.check_id == "beam_width_min":
                val, lim, ok, unit = width, Decimal("250"), width >= 250, "mm"
            elif definition.check_id == "beam_depth_min":
                val, lim, ok, unit = depth, Decimal("300"), depth >= 300, "mm"
            else:
                val, lim, unit = depth / width, Decimal("3.5"), "ratio"
                ok = val <= lim
            item.update(value=str(val), limit=str(lim), unit=unit,
                        ratio=str(val / lim),
                        status="MEETS_SUBCONDITION" if ok else "DOES_NOT_MEET_SUBCONDITION")
            items.append(item)
        checks.append(_aggregate(definition, items))

    return {"stage": "QUICK_GEOMETRY_SCREENING",
            "status": ("NO_DATA" if not any(c["evaluated_count"] for c in checks) else
                       "SCREENING_PARTIAL" if any(c["not_proven_count"] for c in checks) else
                       "SCREENING_COMPLETE"),
            "source_units": "kN_m_C (ETABS enum 6)",
            "source_row_count": len(summary), "section_assignment_row_count": len(assignments),
            "rectangular_section_count": len(section_rows),
            "material_type_fact_count": len(material_facts),
            "material_type_source_status": material_source.get("status"),
            "column_connectivity_count": len(column_by_id), "beam_connectivity_count": len(beam_by_id),
            "unclassified_frame_types": sorted(unexpected_types),
            "checks": checks, "engineering_release": "NOT_READY",
            "scope_note": "Concrete-material rectangular geometry screens only. Proven non-concrete excluded; unresolved held. TBDY applicability not established."}
