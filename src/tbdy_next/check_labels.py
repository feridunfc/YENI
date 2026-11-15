"""English display labels for checks whose titles are stored in older receipts."""
from __future__ import annotations

from typing import Any, Mapping

from .member_groups import geometry_groups


_TITLES = {
    "modal_mass_95": "Effective modal mass ≥ 95%",
    "column_rect_min": "Short column side ≥ 300 mm",
    "beam_width_min": "Beam web width ≥ 250 mm",
    "beam_depth_min": "Beam depth ≥ 300 mm",
    "beam_depth_width": "Beam depth-to-width ratio h/b ≤ 3.5",
    "concrete_fck_25": "In-use concrete fck ≥ 25 MPa",
    "a1_torsion_x": "A1 torsional irregularity · X",
    "a1_torsion_y": "A1 torsional irregularity · Y",
    "STORY_DRIFT": "Relative and effective interstory drift",
    "WEAK_STORY_B1": "B1 weak story · Conditional calculation",
    "BASIS_PROBE": "Seismic basis source data",
    "BASIS_LINKAGE": "Mass, case and geometry links",
    "DIAPHRAGM_PROBE": "Diaphragm and modal source data",
    "DIAPHRAGM_LINKAGE": "Diaphragms and spectrum modes",
    "SPECTRUM_RECONSTRUCTION": "26 spectrum points and 200 modes",
    "BASE_SHEAR_SCREENING": "Conditional lower-bound term of Eq. 4.19",
}


def display_check(check: Mapping[str, Any]) -> dict[str, Any]:
    display = dict(check)
    title = _TITLES.get(check["check_id"])
    if title is not None:
        display["title"] = title
    if isinstance(code_ref := check.get("code_ref"), str):
        display["code_ref"] = code_ref.replace("Tablo 3.6", "Table 3.6")
    if check.get("category") == "GEOMETRY_SCREENING" and "items" in check:
        display["member_groups"] = geometry_groups(check["items"])
    return display


def display_check_group(group: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if group is None or "checks" not in group:
        return group
    return dict(group, checks=[display_check(check) for check in group["checks"]])
