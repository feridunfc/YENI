"""TBDY 2018 Table 3.6 / 3.6.2.3: B1 weak-story numerical core.

Pure, typed and independent of ETABS table spellings. Calling this function
requires *effective* directional Aw/Ag/Ak areas (m2) attributed to the actual
physical storey, NOT gross facade area assigned to the beam's floor label.
The output distinguishes a numerical scenario from formal authorization.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "tbdy.next.b1.weak-story-numerical.v1"


class B1InputError(ValueError):
    pass


def _number(value: Any, name: str, *, positive: bool = False) -> Decimal:
    if type(value) not in (str, int, Decimal):
        raise B1InputError(name + "_INVALID_DECIMAL_TYPE")
    try:
        d = Decimal(str(value))
    except (ValueError, InvalidOperation):
        raise B1InputError(name + "_INVALID_DECIMAL") from None
    if not d.is_finite() or (d <= 0 if positive else d < 0):
        raise B1InputError(name + "_OUT_OF_RANGE")
    return d


def _serialize(data: Mapping[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def evaluate_b1(
    storeys: list[Mapping[str, Any]],
    *, wall_type: str = "BRITTLE", flex_connection_verified: bool = False,
    R_base: str | None = None, physical_census_proven: bool = False,
    source_directional_area_proven: bool = False,
) -> dict[str, Any]:
    """Compute all physical adjacent-story X/Y B1 ratios and building min.

    Input shape per storey:
      {"story":"+4.50", "elevation_m":"4.5", "active":true,
       "X":{"Aw_m2":"...", "Ag_m2":"...", "Ak_m2":"..."},
       "Y":{"Aw_m2":"...", "Ag_m2":"...", "Ak_m2":"..."}}
    An inactive ETABS story definition is excluded ONLY if the caller already
    authoritatively establishes its physical non-applicability.
    """
    if not isinstance(storeys, list) or not storeys:
        raise B1InputError("STORY_INPUT_MISSING")
    if wall_type not in ("BRITTLE", "FLEXIBLE"):
        raise B1InputError("WALL_TYPE_UNKNOWN")
    if type(flex_connection_verified) is not bool or type(physical_census_proven) is not bool or type(source_directional_area_proven) is not bool:
        raise B1InputError("EVIDENCE_FLAG_TYPE_INVALID")
    if R_base is not None:
        R = _number(R_base, "R_BASE", positive=True)
    else:
        R = None
    names: set[str] = set()
    levels: set[Decimal] = set()
    normalized = []
    for row in storeys:
        if not isinstance(row, Mapping):
            raise B1InputError("STORY_ROW_INVALID")
        label, active = row.get("story"), row.get("active")
        if not isinstance(label, str) or not label or label in names or type(active) is not bool:
            raise B1InputError("STORY_ID_OR_ACTIVITY_INVALID")
        z = _number(row.get("elevation_m"), "ELEVATION")
        if z in levels:
            raise B1InputError("DUPLICATE_STORY_ELEVATION")
        names.add(label)
        levels.add(z)
        directional: dict[str, dict[str, Decimal]] = {}
        for direction in ("X", "Y"):
            vals = row.get(direction)
            if not isinstance(vals, Mapping):
                raise B1InputError("DIRECTIONAL_AREA_INPUT_MISSING")
            components = {}
            for key in ("Aw_m2", "Ag_m2", "Ak_m2"):
                components[key] = _number(vals.get(key), key)
            if not active and any(v != 0 for v in components.values()):
                raise B1InputError("INACTIVE_STORY_CONTAINS_EFFECTIVE_AREA")
            directional[direction] = components
        normalized.append({"story": label, "z": z, "active": active, "directions": directional})
    normalized.sort(key=lambda r: r["z"])
    active = [r for r in normalized if r["active"]]
    if len(active) < 2:
        raise B1InputError("NOT_ENOUGH_PHYSICAL_ACTIVE_STORIES")
    pairs = []
    min_eta: Decimal | None = None
    for i in range(len(active)-1):
        lower, upper = active[i], active[i+1]
        for direction in ("X", "Y"):
            l, u = lower["directions"][direction], upper["directions"][direction]
            l_struct = l["Aw_m2"] + l["Ag_m2"]
            u_struct = u["Aw_m2"] + u["Ag_m2"]
            if u_struct <= 0:
                raise B1InputError("UPPER_STOREY_EFFECTIVE_STRUCTURAL_AREA_NONPOSITIVE")
            flexible = wall_type == "FLEXIBLE"
            l_ak = Decimal(0) if flexible else l["Ak_m2"]
            u_ak = Decimal(0) if flexible else u["Ak_m2"]
            raw_lower = l_struct + Decimal("0.15") * l_ak
            raw_upper = u_struct + Decimal("0.15") * u_ak
            preliminary = raw_lower / raw_upper
            omit_infill = (not flexible and preliminary < Decimal("0.80")
                           and l_ak > u_ak)
            lower_e = l_struct if omit_infill else raw_lower
            upper_e = u_struct if omit_infill else raw_upper
            eta = lower_e / upper_e
            min_eta = eta if min_eta is None else min(min_eta, eta)
            condition = (
                "REDESIGN_AND_REANALYZE" if eta < Decimal("0.60")
                else "B1_R_REDUCTION_REQUIRED" if eta < Decimal("0.80")
                else "NO_B1_NUMERIC_TRIGGER"
            )
            pairs.append({
                "lower_story": lower["story"], "upper_story": upper["story"],
                "direction": direction,
                "Aw_lower_m2": str(l["Aw_m2"]), "Ag_lower_m2": str(l["Ag_m2"]),
                "Ak_lower_m2": str(l["Ak_m2"]),
                "Aw_upper_m2": str(u["Aw_m2"]), "Ag_upper_m2": str(u["Ag_m2"]),
                "Ak_upper_m2": str(u["Ak_m2"]),
                "preliminary_eta": str(preliminary),
                "infill_omitted_because_lower_more_than_upper": omit_infill,
                "flexible_infill_omitted_by_4_9_1_3_b": flexible,
                "Ae_lower_m2": str(lower_e), "Ae_upper_m2": str(upper_e),
                "eta_ci": str(eta), "numeric_condition": condition,
                "code_ref": "TBDY 2018 Table 3.6; 3.6.2.3",
                "formal_compliance": "NOT_PROVEN",
            })
    assert min_eta is not None
    outcome = (
        "REDESIGN_AND_REANALYZE" if min_eta < Decimal("0.60")
        else "B1_R_REDUCTION_REQUIRED" if min_eta < Decimal("0.80")
        else "NO_B1_NUMERIC_TRIGGER"
    )
    multiplier = Decimal("1.25") * min_eta if outcome == "B1_R_REDUCTION_REQUIRED" else None
    # An experimental test/explicit approval, not a user tick, must prove
    # flexible wall classification before a code result is authorized.
    formal = (physical_census_proven and source_directional_area_proven
              and (wall_type != "FLEXIBLE" or flex_connection_verified))
    result = {
        "schema": SCHEMA, "check_id": "WEAK_STORY_B1",
        "code_refs": ["TBDY 2018 Table 3.6", "TBDY 2018 3.6.2.3",
                      "TBDY 2018 4.9.1.3(b) if flexible"],
        "wall_type": wall_type,
        "input_stories": len(normalized),
        "active_physical_stories": len(active),
        "inactive_stories": [x["story"] for x in normalized if not x["active"]],
        "expected_story_direction_pairs": 2*(len(active)-1),
        "computed_story_direction_pairs": len(pairs),
        "eta_ci_min": str(min_eta),
        "numeric_condition": outcome,
        "R_multiplier_both_directions": str(multiplier) if multiplier is not None else None,
        "R_adjusted_both_directions": str(R * multiplier) if R is not None and multiplier is not None else None,
        "R_base": str(R) if R is not None else None,
        "paired_results": pairs,
        "physical_census_approved": physical_census_proven,
        "directional_effective_area_approved": source_directional_area_proven,
        "formal_compliance": (
            "DOES_NOT_COMPLY" if formal and outcome == "REDESIGN_AND_REANALYZE"
            else "B1_PRESENT_REDUCTION_REQUIRED" if formal and outcome == "B1_R_REDUCTION_REQUIRED"
            else "MEETS_B1_CRITERION" if formal else "NOT_PROVEN"
        ),
        "engineering_release": "NOT_READY",
        "note": "Numeric calculation is not a B1 design release. R reduction requires reanalysis with the updated R. LC_WDL full beam loads are only candidate infill faces; orient and assign each wall to a physical storey.",
    }
    result["result_sha256"] = sha256(_serialize(result)).hexdigest()
    return result
