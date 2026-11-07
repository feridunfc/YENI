"""VS04-H: cross-reference real ETABS diaphragm assignments and modal RS tables.

Pure, deterministic and read-only. This validates observable source identities,
not effective diaphragm constraints, applied accidental eccentricity, spectrum
calibration or TBDY design compliance. No raw rows are exported by the reviewer.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .diaphragm_probe import (
    SCHEMA, DIAPHRAGM_TABLES, SPECTRUM_MODAL_TABLE,
    review_diaphragm_modal_probe,
)

MODAL_FIELDS = (
    "SpecCase", "ModalCase", "Mode", "Period", "DampRatio",
    "U1Acc", "U2Acc", "U3Acc", "U1Amp", "U2Amp", "U3Amp",
)
MODAL_UNITS = {
    "Period": "sec", "U1Acc": "m/sec2", "U2Acc": "m/sec2",
    "U3Acc": "m/sec2", "U1Amp": "m", "U2Amp": "m", "U3Amp": "m",
}


def _decimal(value: Any, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or not value.strip() or value == "None":
        raise ValueError("INVALID_NUMERIC_DISPLAY")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise ValueError("UNPARSABLE_NUMERIC_DISPLAY") from None
    if not parsed.is_finite() or (positive and parsed <= 0):
        raise ValueError("NONFINITE_OR_NONPOSITIVE_DISPLAY")
    return parsed


def _read_table(table: Any, key: str, required_fields: set[str],
                required_units: Mapping[str, str] | None = None) -> list[dict]:
    if not isinstance(table, dict) or table.get("status") != "CAPTURED" or table.get("table_key") != key:
        raise ValueError("TABLE_NOT_CAPTURED:" + key)
    fields, rows = table.get("fields"), table.get("rows")
    meta = table.get("field_metadata")
    if (not isinstance(fields, list) or not fields or len(set(fields)) != len(fields)
            or not required_fields.issubset(fields) or not isinstance(rows, list)
            or not rows or type(table.get("row_count")) is not int or
            len(rows) != table["row_count"] or not isinstance(meta, dict)
            or meta.get("status") != "OK" or
            not isinstance(meta.get("field_keys"), list) or
            len(meta["field_keys"]) != meta.get("field_count") or
            not set(fields).issubset(meta["field_keys"]) or
            not isinstance(meta.get("units_by_field"), dict)):
        raise ValueError("SOURCE_TABLE_OR_METADATA_INVALID:" + key)
    if any(meta["units_by_field"].get(k) != v
           for k, v in (required_units or {}).items()):
        raise ValueError("SOURCE_UNIT_CONTRACT_INVALID:" + key)
    if any(not isinstance(row, dict) or set(row) != set(fields)
           or any(not isinstance(v, str) for v in row.values()) for row in rows):
        raise ValueError("SOURCE_ROW_GRAIN_INVALID:" + key)
    return rows


def _check(stage: str, operation) -> dict:
    try:
        facts, cautions = operation()
    except (ValueError, KeyError, TypeError) as exc:
        return {"component": stage, "status": "NOT_PROVEN",
                "reason_codes": [str(exc)], "caution_codes": [],
                "source_facts": {}, "formal_compliance": "NOT_PROVEN"}
    return {"component": stage, "status": "SOURCE_CONTRACT_OBSERVED_UNAPPROVED",
            "reason_codes": [], "caution_codes": cautions,
            "source_facts": facts, "formal_compliance": "NOT_PROVEN"}


def _definitions(probe: Mapping[str, Any]):
    table = probe["diaphragm_tables"]["Diaphragm Definitions"]
    rows = _read_table(table, "Diaphragm Definitions", {"Name", "Rigidity", "GUID"},
                       {"Name": "", "Rigidity": ""})
    names = [r["Name"] for r in rows]
    guids = [r["GUID"] for r in rows]
    if (len(names) != len(set(names)) or len(guids) != len(set(guids)) or
            any(x in ("", "None") for x in names + guids)):
        raise ValueError("DIAPHRAGM_REGISTRY_DUPLICATE_OR_BLANK")
    if any(row["Rigidity"] not in ("Rigid", "Semi-Rigid") for row in rows):
        raise ValueError("DIAPHRAGM_RIGIDITY_ENUM_UNRECOGNIZED")
    return {"defined_names": sorted(names), "count": len(rows),
            "rigidities": {r["Name"]: r["Rigidity"] for r in rows}}, [
        "DIAPHRAGM_DEFINITION_IS_NOT_ASSIGNMENT_OR_APPLIED_CONSTRAINT"
    ]


def _assignment(probe: Mapping[str, Any], defined: set[str], *,
                joint: bool):
    key = ("Joint Assignments - Diaphragms" if joint else
           "Area Assignments - Diaphragms")
    rows = _read_table(probe["diaphragm_tables"][key], key,
                       {"Story", "Label", "UniqueName", "Diaphragm"},
                       {"Story": "", "Diaphragm": ""})
    names = [r["UniqueName"] for r in rows]
    if (len(set(names)) != len(names) or
            any(not r["Story"] or r["Story"] == "None" or
                not r["Label"] or r["Label"] == "None" or
                not r["UniqueName"] or r["UniqueName"] == "None"
                for r in rows)):
        raise ValueError("DUPLICATE_OR_INCOMPLETE_OBJECT_IDENTITY")
    allowed = defined | ({"None", "From Shell Object"} if joint else {"None"})
    unknown = sorted({r["Diaphragm"] for r in rows} - allowed)
    if unknown:
        raise ValueError("ASSIGNMENT_REFERENCES_UNKNOWN_DIAPHRAGM:" + ",".join(unknown))
    direct = [r for r in rows if r["Diaphragm"] in defined]
    by_name = dict(sorted(Counter(r["Diaphragm"] for r in direct).items()))
    by_story_name = dict(sorted(Counter(
        r["Story"] + "|" + r["Diaphragm"] for r in direct).items()))
    facts = {
        "table_key": key,
        "captured_row_count": len(rows),
        "direct_assignment_count": len(direct),
        "assigned_diaphragms": by_name,
        "story_diaphragm_counts": by_story_name,
        "explicit_none_count": sum(r["Diaphragm"] == "None" for r in rows),
        "from_shell_object_count": sum(
            r["Diaphragm"] == "From Shell Object" for r in rows),
        "unassigned_or_inherited_object_count": len(rows) - len(direct),
    }
    cautions = ["ANALYSIS_MESH_DIAPHRAGM_MASS_AND_CONSTRAINT_EFFECT_NOT_PROVEN"]
    if facts["explicit_none_count"]:
        cautions.append("EXPLICIT_NONE_ASSIGNMENTS_REQUIRE_APPLICABILITY_REVIEW")
    if facts["from_shell_object_count"]:
        cautions.append("FROM_SHELL_OBJECT_NEEDS_ANALYSIS_NODE_CONNECTIVITY")
    return facts, cautions


def _modal(probe: Mapping[str, Any], prior: Mapping[str, Any] | None):
    table = probe["spectrum_modal_selected_cases"]
    rows = _read_table(table, SPECTRUM_MODAL_TABLE, set(MODAL_FIELDS), MODAL_UNITS)
    groups = {}
    for row in rows:
        case, mode_raw = row["SpecCase"], row["Mode"]
        if case not in ("RSX", "RSY") or row["ModalCase"] != "Modal":
            raise ValueError("SELECTED_SPECTRUM_OR_MODAL_CASE_IDENTITY_UNKNOWN")
        mode = _decimal(mode_raw, positive=True)
        if mode != mode.to_integral_value() or str(int(mode)) != mode_raw:
            raise ValueError("MODE_INTEGER_IDENTITY_INVALID")
        if mode_raw in groups.setdefault(case, {}):
            raise ValueError("DUPLICATE_SPECTRUM_CASE_AND_MODE")
        period = _decimal(row["Period"], positive=True)
        if _decimal(row["DampRatio"], positive=True) != Decimal("0.05"):
            raise ValueError("SPECTRUM_MODAL_DAMPING_NOT_0_05")
        nums = {k: _decimal(row[k]) for k in
                ("U1Acc", "U2Acc", "U3Acc", "U1Amp", "U2Amp", "U3Amp")}
        active = "U1" if case == "RSX" else "U2"
        if nums[active + "Acc"] <= 0:
            raise ValueError("ACTIVE_DIRECTION_SPECTRAL_ACCELERATION_NOT_POSITIVE")
        for axis in {"U1", "U2", "U3"} - {active}:
            if nums[axis + "Acc"] != 0 or nums[axis + "Amp"] != 0:
                raise ValueError("UNEXPECTED_CROSS_DIRECTION_EXCITATION")
        groups[case][mode_raw] = row
    if set(groups) != {"RSX", "RSY"}:
        raise ValueError("NOT_BOTH_RESPONSE_SPECTRUM_CASES")
    mode_counts = {}
    for case in ("RSX", "RSY"):
        modes = sorted(int(s) for s in groups[case])
        if modes != list(range(1, 101)):
            raise ValueError("SPECTRUM_MODAL_100_MODE_POPULATION_NOT_EXACT")
        mode_counts[case] = len(modes)
    for mode in range(1, 101):
        x, y = groups["RSX"][str(mode)], groups["RSY"][str(mode)]
        if x["Period"] != y["Period"] or x["U1Acc"] != y["U2Acc"]:
            raise ValueError("RSX_RSY_EQUAL_FUNCTION_MODAL_SOURCE_MISMATCH")
    facts = {
        "output_rows": len(rows), "cases": ["RSX", "RSY"],
        "modes_by_case": mode_counts, "comparison_rows": 100,
        "modal_case": "Modal", "damping_ratio": "0.05",
        "equal_period_by_mode_count": 100,
        "equal_active_axis_acceleration_by_mode_count": 100,
        "selection_dependency_observed": (
            probe.get("original_display_cases") == [] and
            probe["spectrum_modal_original_selection"].get("status") == "CAPTURE_ERROR"
        ),
    }
    if prior is not None:
        if prior.get("schema") != "tbdy.next.vs04.offline-source-replay.v1":
            raise ValueError("PRIOR_MODAL_REPLAY_SCHEMA_INVALID")
        numerical = prior.get("numeric_source_review") or {}
        items = next((c.get("items") for c in numerical.get("results", [])
                      if c.get("component") == "MODAL_PERIOD_FREQUENCY_IDENTITY"
                      and c.get("status") == "SOURCE_ARITHMETIC_OBSERVED"), None)
        if (not isinstance(items, list) or len(items) != 100 or
                len({r.get("mode") for r in items}) != 100):
            raise ValueError("PRIOR_MODAL_REPLAY_NOT_100_PROVEN_SOURCE_ROWS")
        prior_period = {r["mode"]: r["period_sec"] for r in items}
        for mode in range(1, 101):
            if groups["RSX"][str(mode)]["Period"] != prior_period.get(str(mode)):
                raise ValueError("VS04D_VS04G_DISPLAYED_MODAL_PERIOD_MISMATCH")
        facts["compared_to_vs04d_modal_modes"] = 100
        facts["prior_source_input_sha256"] = prior.get("input_sha256")
    return facts, [
        "MODAL_AMPLITUDE_SIGN_IS_NOT_CONCURRENT_FORCE_VECTOR",
        "RESPONSE_SPECTRUM_FUNCTION_INTERPOLATION_OR_ANALYTIC_EVALUATION_NOT_PROVEN",
        "MODEL_GENERATION_CROSS_CAPTURE_IDENTITY_NOT_PROVEN",
    ]


def review_vs04h_source(
    receipt: Mapping[str, Any] | None,
    *, prior_modal_replay: Mapping[str, Any] | None = None,
) -> dict:
    base = {
        "stage": "VS04H_DIAPHRAGM_MODAL_SOURCE_LINKAGE",
        "engineering_release": "NOT_READY", "formal_compliance": "NOT_PROVEN",
        "regulatory_checks_executed": 0,
        "analysis_generation_proven": False,
        "accidental_eccentricity_applied_proven": False,
        "diaphragm_mass_explained": False,
        "source_only": True,
    }
    if not isinstance(receipt, Mapping):
        return {**base, "status": "SOURCE_UNAVAILABLE", "components": []}
    raw = receipt.get("source") if receipt.get("schema") == (
        "tbdy.next.vs04g.diaphragm-source-receipt.v1") else receipt
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        return {**base, "status": "SOURCE_REJECTED", "components": [],
                "reason_codes": ["CAPTURE_SOURCE_SCHEMA_INVALID"]}
    reviewed = review_diaphragm_modal_probe(raw)
    if (reviewed.get("status") == "SOURCE_REJECTED" or
            raw.get("source_mode") != "LIVE_ETABS" or
            raw.get("display_selection_restored") is not True or
            raw.get("units_before") != raw.get("units_after") or
            raw.get("units_before") != 6 or
            raw.get("analysis_generation_proven") is not False or
            raw.get("eccentricity_applied_proven") is not False or
            raw.get("diaphragm_constraints_applied_proven") is not False or
            raw.get("temporary_display_cases") != ["RSX", "RSY"]):
        return {**base, "status": "SOURCE_REJECTED", "components": [],
                "reason_codes": ["SOURCE_SELECTION_UNITS_OR_AUTHORITY_INVALID"]}
    definitions = _check("DIAPHRAGM_DEFINITIONS",
                         lambda: _definitions(raw))
    defined = set(definitions["source_facts"].get("defined_names", []))
    area = _check("AREA_DIAPHRAGM_ASSIGNMENTS",
                  lambda: _assignment(raw, defined, joint=False))
    joint = _check("JOINT_DIAPHRAGM_ASSIGNMENTS",
                   lambda: _assignment(raw, defined, joint=True))
    modal = _check("SPECTRUM_MODAL_RSXY_SOURCE",
                   lambda: _modal(raw, prior_modal_replay))
    parts = [definitions, area, joint, modal]
    successful = sum(x["status"] == "SOURCE_CONTRACT_OBSERVED_UNAPPROVED" for x in parts)
    assigned = set(area["source_facts"].get("assigned_diaphragms", {})) | set(
        joint["source_facts"].get("assigned_diaphragms", {}))
    unused = sorted(defined - assigned)
    return {**base,
            "status": "SOURCE_LINKAGE_OBSERVED_PENDING_ENGINEERING_REVIEW"
            if successful == len(parts) else "SOURCE_LINKAGE_PARTIAL",
            "source_component_count": len(parts),
            "observed_source_component_count": successful,
            "original_source_reads_observed": reviewed.get("source_success_count"),
            "original_source_reads_expected": reviewed.get("source_expected_count"),
            "defined_but_unassigned_diaphragms": unused,
            "components": parts,
            "mandatory_holds": [
                "DIAPHRAGM_ZERO_MASS_ROOT_CAUSE_NOT_QUALIFIED",
                "SEMI_RIGID_CONSTRAINT_EFFECT_NOT_PROVEN",
                "ACCIDENTAL_ECCENTRICITY_EFFECT_NOT_PROVEN",
                "SPECTRUM_PSEUDO_ACCELERATION_GENERATION_NOT_INDEPENDENTLY_PROVEN",
                "SEISMIC_MASS_ANALYSIS_GENERATION_AND_SOURCE_LINEAGE_NOT_PROVEN",
                "TBDY_NORMATIVE_DRIFT_AND_BASE_SHEAR_NOT_EXECUTED",
            ],
           }
