"""VS03: project-owned material and torsional ratio numerical subconditions.

Both checks are conditional/source-only. The A1 sign is an observed category,
not a full code verdict until seismic/eccentricity basis is reviewed.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .quick_checks import CheckDefinition

EXTRA_CHECKS = (
    CheckDefinition("concrete_fck_25", "Kullanılan beton fck ≥ 25 MPa", 1,
                    "TBDY 2018 7.2.5.1", "MATERIAL_SCREENING"),
    CheckDefinition("a1_torsion_x", "A1 burulma katsayısı X", 9,
                    "TBDY 2018 3.6.2.1 / Tablo 3.6", "A1_SOURCE_CLASSIFICATION"),
    CheckDefinition("a1_torsion_y", "A1 burulma katsayısı Y", 9,
                    "TBDY 2018 3.6.2.1 / Tablo 3.6", "A1_SOURCE_CLASSIFICATION"),
)


def _num(value: Any, *, positive: bool = False) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError("invalid numeric value")
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid numeric value") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError("nonfinite/invalid numeric value")
    return result


def _table(source: Mapping[str, Any], key: str, fields: set[str]) -> list[dict] | None:
    table = source.get(key)
    if not isinstance(table, dict) or table.get("status") != "CAPTURED":
        return None
    cols, rows = table.get("fields"), table.get("rows")
    if (table.get("table_key") != ("Material Properties - Concrete Data" if key == "material_table" else "Story Max Over Avg Drifts")
            or not isinstance(cols, list) or not fields.issubset(set(cols))
            or len(cols) != len(set(cols)) or not isinstance(rows, list)
            or table.get("row_count") != len(rows)
            or any(not isinstance(r, dict) or set(r) != set(cols) for r in rows)):
        return None
    meta = table.get("field_metadata")
    if (not isinstance(meta, dict) or meta.get("status") != "OK"
            or not set(cols).issubset(set(meta.get("field_keys") or []))):
        return None
    return rows


def _aggregate(spec: CheckDefinition, rows: list[dict]) -> dict:
    present_a1 = sum(x["status"] == "A1_OBSERVED" for x in rows)
    absent_a1 = sum(x["status"] == "A1_NOT_OBSERVED" for x in rows)
    met = sum(x["status"] == "MEETS_SUBCONDITION" for x in rows)
    unmet = sum(x["status"] == "DOES_NOT_MEET_SUBCONDITION" for x in rows)
    unknown = len(rows) - met - unmet - present_a1 - absent_a1
    return {
        **spec.as_dict(),
        "status": "NOT_PROVEN" if unknown else "A1_CLASSIFIED" if spec.category == "A1_SOURCE_CLASSIFICATION" else
                  "DOES_NOT_MEET_SUBCONDITION" if unmet else "MEETS_SUBCONDITION" if met else "NOT_PROVEN",
        "expected_count": len(rows), "evaluated_count": met+unmet+present_a1+absent_a1,
        "a1_present_count": present_a1, "a1_not_observed_count": absent_a1,
        "met_count": met, "unmet_count": unmet, "not_proven_count": unknown,
        "not_applicable_count": 0, "proven_non_concrete_count": 0,
        "formal_compliance": "NOT_PROVEN", "items": rows,
    }


def _material_items(source: Mapping[str, Any], geometry: Mapping[str, Any]) -> list[dict]:
    facts = ((geometry.get("material_types") or {}).get("facts") or {})
    concrete = sorted(name for name, fact in facts.items()
                      if fact.get("status") == "TYPE_RESOLVED" and fact.get("material_type_code") == 2)
    # An unproven material classification must not be silently excluded.
    unresolved = sorted(name for name, fact in facts.items() if fact.get("status") != "TYPE_RESOLVED")
    rows = _table(source, "material_table", {"Material", "Fc"})
    metadata = (source.get("material_table") or {}).get("field_metadata") or {}
    unit = (metadata.get("units_by_field") or {}).get("Fc")
    conversion = {"kN/m2": Decimal("0.001"), "kN/m^2": Decimal("0.001"),
                  "kN/m²": Decimal("0.001"), "MPa": Decimal("1"),
                  "N/mm2": Decimal("1")}.get(unit)
    grouped: dict[str, list[dict]] = {}
    for row in rows or []:
        grouped.setdefault(str(row.get("Material", "")).strip(), []).append(row)
    output = []
    for name in concrete + unresolved:
        result = {"material_name": name, "status": "NOT_PROVEN", "fck_mpa": None,
                  "source_units": unit, "value": None, "limit": "25", "unit": "MPa"}
        if name in unresolved:
            result["reason"] = "MATERIAL_TYPE_UNRESOLVED"
        elif rows is None:
            result["reason"] = "MATERIAL_SOURCE_SCHEMA_NOT_VERIFIED"
        elif conversion is None:
            result["reason"] = "FC_FIELD_UNIT_NOT_REVIEWED"
        elif len(grouped.get(name, [])) != 1:
            result["reason"] = "MATERIAL_ROW_MISSING_OR_DUPLICATE"
        else:
            try:
                raw = _num(grouped[name][0]["Fc"], positive=True)
                fck = raw * conversion
                result.update(fck_mpa=str(fck), value=str(fck),
                              status="MEETS_SUBCONDITION" if fck >= 25 else "DOES_NOT_MEET_SUBCONDITION")
            except (ValueError, KeyError):
                result["reason"] = "FC_INVALID"
        output.append(result)
    if not output:
        output.append({"material_name": None, "status": "NOT_PROVEN",
                       "reason": "NO_USED_CONCRETE_MATERIAL_POPULATION"})
    return output


def _a1_items(source: Mapping[str, Any], geometry: Mapping[str, Any], direction: str) -> list[dict]:
    case = source.get("x_case") if direction == "X" else source.get("y_case")
    rows = _table(source, "a1_table", {"Story", "OutputCase", "Direction", "MaxDrift", "AvgDrift", "Ratio"})
    geometry_rows = ((geometry.get("tables") or {}).get("FRAME_ASSIGNMENTS") or {}).get("rows") or []
    stories = {str(row.get("Story", "")).strip() for row in geometry_rows
               if str(row.get("Type", "")).strip().casefold() in {"beam", "column"}}
    if rows:
        stories.update(str(row.get("Story", "")).strip() for row in rows if row.get("Story"))
    stories.discard("")
    if not stories:
        stories = {"UNKNOWN_STORY"}
    output = []
    for story in sorted(stories):
        item = {"story": story, "direction": direction, "source_case": case,
                "status": "NOT_PROVEN", "eta_bi": None, "limit": "1.2", "unit": "ratio"}
        if rows is None:
            item["reason"] = "A1_SOURCE_SCHEMA_NOT_VERIFIED"
        elif not isinstance(case, str) or not case:
            item["reason"] = "DIRECTION_CASE_NOT_DEFINED"
        elif source.get("case_selection_restored") is not True:
            item["reason"] = "DISPLAY_SELECTION_NOT_RESTORED"
        else:
            matching = [r for r in rows if r.get("Story") == story and r.get("OutputCase") == case
                        and str(r.get("Direction", "")).strip().upper() in
                        ({"X", "U1", "UX"} if direction == "X" else {"Y", "U2", "UY"})]
            if not matching:
                item["reason"] = "A1_CASE_DIRECTION_STORY_ROW_MISSING"
            else:
                parsed = []
                for r in matching:
                    try:
                        maximum = _num(r["MaxDrift"], positive=True)
                        average = _num(r["AvgDrift"], positive=True)
                        eta = _num(r["Ratio"], positive=True)
                        if (eta < 1 or maximum < average
                                or (average >= Decimal("0.000001")
                                    and abs(maximum/average-eta) > max(Decimal("0.03"),eta*Decimal("0.03")))):
                            raise ValueError("ratio/source drift conflict")
                        parsed.append(eta)
                    except (KeyError, ValueError):
                        parsed = []
                        break
                if parsed:
                    value = max(parsed)
                    item.update(eta_bi=str(value), value=str(value),
                                status="A1_OBSERVED" if value > Decimal("1.2") else "A1_NOT_OBSERVED")
                else:
                    item["reason"] = "A1_ROW_INVALID_OR_RATIO_CONFLICT"
        output.append(item)
    return output


def evaluate_next_capture(source: Mapping[str, Any] | None,
                          geometry: Mapping[str, Any] | None) -> dict:
    """One pure postprocessing path; no COM or code-level full-compliance claim."""
    if (not isinstance(source, Mapping) or source.get("schema") != "tbdy.next.vs03.capture.v1"
            or source.get("units_before") != 6 or source.get("units_after") != 6
            or not isinstance(geometry, Mapping)):
        return {"stage": "VS03_MATERIAL_A1", "status": "SOURCE_SCHEMA_REVIEW_REQUIRED",
                "checks": [_aggregate(s, [{"status":"NOT_PROVEN", "reason":"MISSING_VS03_CAPTURE"}])
                           for s in EXTRA_CHECKS], "engineering_release": "NOT_READY"}
    checks = [
        _aggregate(EXTRA_CHECKS[0], _material_items(source, geometry)),
        _aggregate(EXTRA_CHECKS[1], _a1_items(source, geometry, "X")),
        _aggregate(EXTRA_CHECKS[2], _a1_items(source, geometry, "Y")),
    ]
    return {"stage": "VS03_MATERIAL_A1",
            "status": "SOURCE_REVIEW_REQUIRED" if any(x["not_proven_count"] for x in checks) else "NUMERICAL_CLASSIFIED",
            "checks": checks,
            "case_roles": {"X": source.get("x_case"), "Y": source.get("y_case")},
            "source_tables": {
                "material": {k: (source.get("material_table") or {}).get(k)
                             for k in ("table_key", "status", "fields", "row_count", "field_metadata")},
                "a1": {k: (source.get("a1_table") or {}).get(k)
                       for k in ("table_key", "status", "fields", "row_count", "field_metadata")},
            },
            "applicability_basis": "NOT_REVIEWED",
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
            "scope_note": "Concrete fck minimum and observed A1 torsion classification only; building-level compliance not established"}
