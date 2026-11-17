"""Bind a rectangular PMM section to the current ETABS reinforcement tables."""
from __future__ import annotations

from math import isfinite

from ..column_engine.csi_geometry import NativeSectionDims, to_local_dimensions
from ..column_engine.section_capacity import Bar, Material, Section, perimeter
from ..etabs_source_gateway_windows import field_schema, read_table
from ..vs05_d4_source_authority import _source_table
from .column_axial import PREFERENCES

SCHEMA = "tbdy.next.etabs-column-pmm-section-source.v1"
COLUMN_REINFORCING = "Frame Section Property Definitions - Concrete Column Reinforcing"
BAR_SIZES = "Reinforcing Bar Sizes"
REBAR_DATA = "Material Properties - Rebar Data"
MECHANICAL = "Material Properties - Basic Mechanical Properties"
TABLES = (COLUMN_REINFORCING, BAR_SIZES, REBAR_DATA, MECHANICAL)


def capture_pmm_section(sap) -> dict:
    """Read only reinforcement and material definitions on the attached model."""
    captured = {"schema": SCHEMA, "table_reads": {}}
    try:
        captured["model_locked_before"] = sap.GetModelIsLocked()
        captured["units_before"] = sap.GetPresentUnits()
        if captured["model_locked_before"] is not True or captured["units_before"] != 6:
            raise ValueError("PMM_SECTION_CAPTURE_REQUIRES_LOCKED_KN_M_C")
        db = sap.DatabaseTables
        for table_key in TABLES:
            record = read_table(db, table_key)
            record["field_metadata"] = field_schema(db, table_key)
            captured["table_reads"][table_key] = record
        captured["model_locked_after"] = sap.GetModelIsLocked()
        captured["units_after"] = sap.GetPresentUnits()
    except Exception as exc:
        captured["error"] = f"{type(exc).__name__}: {exc}"[:400]
    return captured


def _rows(tables: dict, key: str, fields: set[str], units: dict[str, str]) -> list[dict]:
    rows = _source_table(tables, key, fields | units.keys(), require_key=True)
    observed = tables[key]["field_metadata"]["units_by_field"]
    for field, unit in units.items():
        if observed.get(field) != unit:
            raise ValueError(f"{key}:UNEXPECTED_UNIT:{field}")
    return rows


def _named_row(rows: list[dict], key: str, name: str, table: str) -> dict:
    matches = [row for row in rows if row[key] == name]
    if not isinstance(name, str) or not name.strip() or len(matches) != 1:
        raise ValueError(f"{table}:ROW_NOT_UNIQUE:{name}")
    return matches[0]


def _positive(value, field: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"PMM_SECTION_INVALID_VALUE:{field}") from exc
    if isinstance(value, bool) or not isfinite(numeric) or numeric <= 0:
        raise ValueError(f"PMM_SECTION_INVALID_VALUE:{field}")
    return numeric


def build_pmm_section(source: dict, geometry_member: dict, axial_member: dict,
                      preferences: dict, *, include_layout: bool = False) -> tuple[Section, dict]:
    """Use the configured bars as arithmetic inputs and retain their actual role."""
    if (source.get("schema") != SCHEMA or source.get("error")
            or source.get("model_locked_before") is not True
            or source.get("model_locked_after") is not True
            or not source.get("units_before") == source.get("units_after") == 6):
        raise ValueError("PMM_SECTION_CAPTURE_UNVERIFIED")

    section_name = geometry_member.get("section")
    if (not section_name or geometry_member.get("analysis_section") != section_name
            or geometry_member.get("section_design_difference")
            or geometry_member.get("material_classification") != "RESOLVED_CONCRETE_USAGE"
            or not geometry_member.get("element_id")
            or any(geometry_member.get(key) != axial_member.get(key)
                   for key in ("element_id", "section", "material_name"))):
        raise ValueError("PMM_RECTANGULAR_ANALYSIS_AND_DESIGN_SECTION_UNVERIFIED")
    dims = to_local_dimensions(NativeSectionDims(
        _positive(geometry_member.get("width_mm"), "native_T2_mm"),
        _positive(geometry_member.get("depth_mm"), "native_T3_mm"),
    ))
    tables = source["table_reads"]
    reinforcement = _named_row(_rows(tables, COLUMN_REINFORCING, {
        "Name", "RebarMatL", "ReinfConfig", "IsDesigned", "NumBars2Dir", "NumBars3Dir",
        "BarSizeLong", "BarSizeCorn", "BarSizeConf",
    }, {"Cover": "m"}), "Name", section_name, COLUMN_REINFORCING)
    if reinforcement["ReinfConfig"] != "Rectangular":
        raise ValueError("PMM_REINFORCEMENT_LAYOUT_UNSUPPORTED")
    roles = {"Yes": "ETABS_DESIGN_TEMPLATE", "No": "ETABS_CHECK_REINFORCEMENT"}
    role = roles.get(reinforcement["IsDesigned"])
    if role is None:
        raise ValueError("PMM_ETABS_REINFORCEMENT_ROLE_UNVERIFIED")

    size_rows = _rows(tables, BAR_SIZES, {"Name"}, {"Diameter": "m", "Area": "m2"})
    long_bar, corner_bar, tie_bar = (
        _named_row(size_rows, "Name", reinforcement[field], BAR_SIZES)
        for field in ("BarSizeLong", "BarSizeCorn", "BarSizeConf")
    )
    if any(_positive(long_bar[field], field) != _positive(corner_bar[field], field)
           for field in ("Diameter", "Area")):
        raise ValueError("PMM_MIXED_LONGITUDINAL_BAR_SIZES_UNSUPPORTED")
    diameter_mm = _positive(long_bar["Diameter"], "Diameter") * 1000
    bar_area_mm2 = _positive(long_bar["Area"], "Area") * 1000000
    cover_mm = _positive(reinforcement["Cover"], "Cover") * 1000
    tie_mm = _positive(tie_bar["Diameter"], "TieDiameter") * 1000
    # Each ETABS count includes the corner bars along the corresponding axis.
    n2, n3 = int(reinforcement["NumBars2Dir"]), int(reinforcement["NumBars3Dir"])
    bars, _, _ = perimeter(dims.local2_extent_mm, dims.local3_extent_mm,
                           cover_mm, tie_mm, diameter_mm, n2=n2, n3=n3)
    bars = tuple(Bar(bar.x2, bar.x3, bar_area_mm2) for bar in bars)

    steel_name = reinforcement["RebarMatL"]
    steel = _named_row(_rows(tables, REBAR_DATA, {"Material"}, {"Fy": "kN/m2"}),
                       "Material", steel_name, REBAR_DATA)
    mechanical = _named_row(_rows(tables, MECHANICAL, {"Material"}, {"E1": "kN/m2"}),
                            "Material", steel_name, MECHANICAL)
    factors = _rows({PREFERENCES: preferences}, PREFERENCES, set(), {"GammaS": ""})
    if len(factors) != 1:
        raise ValueError("PMM_TS500_STEEL_FACTOR_UNVERIFIED")
    gamma_s = _positive(factors[0]["GammaS"], "GammaS")
    fy_mpa = _positive(steel["Fy"], "Fy") / 1000
    material = Material(
        fck=_positive(axial_member.get("fck_mpa"), "fck_mpa"),
        fcd=_positive(axial_member.get("fcd_mpa"), "fcd_mpa"),
        fyd=fy_mpa / gamma_s,
        es=_positive(mechanical["E1"], "E1") / 1000,
    )
    section = Section(dims.local2_extent_mm, dims.local3_extent_mm, bars, material)
    evidence = {
        "reinforcement_role": role, "bar_count": len(bars),
        "longitudinal_bar_name": long_bar["Name"], "longitudinal_bar_diameter_mm": diameter_mm,
        "longitudinal_bar_area_mm2": bar_area_mm2, "cover_to_tie_mm": cover_mm,
        "tie_diameter_mm": tie_mm, "t2_mm": section.t2, "t3_mm": section.t3,
        "native_t2_mm": section.t3, "native_t3_mm": section.t2,
        "steel_material_name": steel_name, "gamma_s": gamma_s,
        "fck_mpa": material.fck, "fcd_mpa": material.fcd, "fy_mpa": fy_mpa,
        "fyd_mpa": material.fyd, "es_mpa": material.es,
    }
    if include_layout:
        from .column_gates import evaluate_reinforcement_state

        steel_area = sum(bar.area for bar in section.bars)
        gross_area = section.t2 * section.t3
        is_design_template = role == "ETABS_DESIGN_TEMPLATE"
        ratio_check = evaluate_reinforcement_state(
            role="TEMPLATE" if is_design_template else "PROPOSED",
            ac_mm2=gross_area, ast_mm2=steel_area, bar_count=len(section.bars),
            bar_diameter_mm=diameter_mm, is_designed_flag=is_design_template,
        )
        minimum_area = gross_area * ratio_check["rho_min"]
        evidence.update(
            longitudinal_steel_area_mm2=steel_area,
            gross_section_area_mm2=gross_area,
            longitudinal_reinforcement_percent=ratio_check["rho"] * 100,
            tbdy_longitudinal_minimum={
                "code_ref": "TBDY 2018 §7.3.2.1",
                "minimum_percent": ratio_check["rho_min"] * 100,
                "minimum_area_mm2": minimum_area,
                "status": ("BELOW_MINIMUM" if ratio_check["rho"] < ratio_check["rho_min"]
                           else "MEETS_MINIMUM"),
                "formal_compliance": "NOT_PROVEN",
            },
        )
        units = tables[COLUMN_REINFORCING]["field_metadata"]["units_by_field"]
        spacing = None
        if units.get("SpacingConf") == "m":
            try:
                spacing = _positive(reinforcement.get("SpacingConf"), "SpacingConf") * 1000
            except ValueError:
                pass
        evidence.update(bars_per_face_2=n2, bars_per_face_3=n3, tie_spacing_mm=spacing,
                        tie_material_name=reinforcement.get("RebarMatC"),
                        bar_positions_mm=[[bar.x2, bar.x3] for bar in section.bars])
        for axis in (2, 3):
            key = f"NumCBars{axis}"
            value = reinforcement.get(key)
            evidence[f"tie_bars_parallel_{axis}"] = (
                int(value) if units.get(key) == "" and isinstance(value, str) and value.isascii() and value.isdecimal()
                else None)
    return section, evidence
