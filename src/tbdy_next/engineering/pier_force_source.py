"""Source binding for signed native pier section resultants at a named storey and face."""
from collections import defaultdict
from hashlib import sha256
from math import isclose, isfinite
import re

from ..column_engine.source_bank import native_frame_force_rows
from ..etabs_source_gateway_windows import verify
from .analysis_archive import _archive_bytes

SCHEMA = "tbdy.next.pier-section-force-source.v1"
METHOD = "MATCHED_EI_FINAL_STEP"
ORIGINAL = "ORIGINAL_ASSIGNED_COMBINATIONS"
COMPONENTS = ("P", "V2", "V3", "T", "M2", "M3")


def normalize_pier_source(raw, *, source_data_sha256):
    if (not isinstance(raw, dict) or raw.get("schema") != SCHEMA
            or raw.get("source_data_sha256") != source_data_sha256):
        raise ValueError("PIER_NATIVE_SOURCE_BINDING_INVALID")
    kind = raw.get("kind")
    if kind == ORIGINAL:
        read = raw.get("read", {})
        verify(read)
        verify(read["tables"])
        if read.get("schema") != "tbdy.next.original-pier-read.v1":
            raise ValueError("PIER_ORIGINAL_READ_REQUIRED")
    elif kind == METHOD:
        deck = _archive_bytes(raw.get("model_export_base64"), 2_000_000)
        identity = raw.get("identity") or {}
        session = raw.get("session") or {}
        selection = raw.get("display_selection") or {}
        if (identity.get("deck_sha256") != sha256(deck).hexdigest()
                or any(not isinstance(raw.get(k), str) or not re.fullmatch(r"[0-9a-f]{64}", raw[k])
                       or identity.get(k) != raw[k] for k in ("model_sha256", "analysis_generation"))
                or identity.get("units") != 6 or session.get("units") != 6 or session.get("locked") is not True
                or session.get("file") != identity.get("model") or raw.get("restored") is not True
                or selection.get("confirmed") is not True or not identity.get("cases")
                or set(selection.get("observed_cases") or ()) != set(identity["cases"])
                or any(v != 4 or session.get("case_status", {}).get(k) != 4 for k, v in identity["cases"].items())):
            raise ValueError("PIER_METHOD_SOLVED_SOURCE_INVALID")
    else:
        raise ValueError("PIER_SOURCE_TYPE_UNSUPPORTED")
    return raw


def _table(tables, key):
    table = tables.get(key) or {}
    rows = table.get("rows")
    if (table.get("status") != "CAPTURED" or table.get("table_key") != key or not isinstance(rows, list)
            or not rows or table.get("row_count") != len(rows)):
        raise ValueError("PIER_SOURCE_TABLE_INCOMPLETE:" + key)
    return rows


def _deck_records(deck, record):
    return sorted(line.strip() for line in deck.splitlines() if line.split(None, 1)[:1] == [record])


def _method(raw, source, gravity, original_deck):
    pair = source.get("gravity_order_pair") or {}
    matched = [level for level in pair.get("refined_levels", []) if all(
        level.get(k) == raw[k] for k in ("model_sha256", "analysis_generation"))]
    if len(matched) != 1 or matched[0].get("kinematics", {}).get("case_step") != ["Step", 1]:
        raise ValueError("PIER_METHOD_SOLVED_GENERATION_NOT_IN_ENGINE_INPUT")
    deck = _archive_bytes(raw["model_export_base64"], 2_000_000).decode("latin-1")
    for record in ("AREA", "AREAASSIGN", "PIERNAME", "SHELLPROP", "FRAMESECTION", "MATERIAL", "STORY", "LINE"):
        original = _deck_records(original_deck, record)
        if not original or original != _deck_records(deck, record):
            raise ValueError("PIER_PHYSICAL_DEFINITION_CHANGED:" + record)
    for record in ("POINT", "POINTASSIGN"):
        original = set(_deck_records(original_deck, record))
        if not original or not original <= set(_deck_records(deck, record)):
            raise ValueError("PIER_PHYSICAL_DEFINITION_CHANGED:" + record)
    def physical_frame_assignments(text):
        # The METHOD experiment changes two bending modifiers and output stations.
        allowed = r"\b(?:PROPMODI22|PROPMODI33|MAXSTASPC|MINNUMSTA)\s+[-+.\dEe]+"
        return sorted(" ".join(re.sub(allowed, "", line).split()) for line in _deck_records(text, "LINEASSIGN"))

    if physical_frame_assignments(original_deck) != physical_frame_assignments(deck):
        raise ValueError("PIER_PHYSICAL_FRAME_ASSIGNMENTS_CHANGED")
    cases = {}
    for combo in gravity:
        spec = pair.get("cases", {}).get(combo) or {}
        name = spec.get("first")
        case = raw.get("case_definitions", {}).get(name) or {}
        storage = case.get("result_storage") or []
        if (name not in raw["identity"]["cases"] or case.get("geometry") != 0 or case.get("initial") != "None"
                or not storage or storage[0] is not False or case.get("loads") != spec.get("patterns")
                or (case.get("load_application") or [])[:2] != [1, 0]):
            raise ValueError("PIER_SINGLE_FINAL_FORCE_CONTROLLED_STEP_REQUIRED")
        cases[combo] = name
    return raw["table_reads"], cases, deck, raw["model_sha256"], raw["analysis_generation"]


def _original(raw, source, gravity, deck):
    read = raw["read"]
    receipt = read["tables"]
    if (read["parent_input_sha256"] != source["design_scenario"]["parent_input_sha256"]
            or read["model_sha256"] != source["analysis_archive"]["observed_edb_sha256"]
            or receipt.get("model_units_code") != 6 or receipt.get("model_locked") is not True
            or receipt.get("selection_restored") is not True or not set(gravity) <= set(read["combinations"])):
        raise ValueError("PIER_ORIGINAL_MODEL_OR_SELECTION_MISMATCH")
    control = read["frame_control"]
    uid = read["control_member"]
    rows = list(native_frame_force_rows(control["rowsets"][uid], uid))
    expected = {r[:7]: r[7:] for r in native_frame_force_rows(
        source["column_axial"]["force_source"]["rowsets"][uid], uid)}
    if (control.get("errors") or control.get("output_selection_before") != control.get("output_selection_after")
            or len(rows) != len(expected) or any(r[:7] not in expected or any(
                not isclose(v, w, rel_tol=1e-8, abs_tol=1e-6) for v, w in zip(r[7:], expected[r[:7]])) for r in rows)):
        raise ValueError("PIER_ORIGINAL_FRAME_CONTROLS_DIFFER")
    return receipt["table_reads"], {k: k for k in gravity}, deck, read["model_sha256"], read["payload_sha256"]


def bound_pier_forces(source, gravity):
    raw = source.get("pier_section_forces") or {}
    if not raw or not gravity:
        raise ValueError("ASSIGNED_GRAVITY_PIER_FORCE_SOURCE_REQUIRED")
    deck = _archive_bytes(source["analysis_archive"]["model_export_base64"], 2_000_000).decode("latin-1")
    if raw["kind"] == METHOD:
        tables, cases, deck, model, revision = _method(raw, source, gravity, deck)
    else:
        tables, cases, deck, model, revision = _original(raw, source, gravity, deck)
    rows = _table(tables, "Pier Forces")
    units = tables["Pier Forces"].get("field_metadata", {}).get("units_by_field", {})
    if any(units.get(k) != ("kN" if k in COMPONENTS[:3] else "kN-m") for k in COMPONENTS):
        raise ValueError("PIER_RESULT_UNITS_UNRESOLVED")
    groups = defaultdict(list)
    for row in rows:
        groups[row["Pier"], row["Story"], row["Location"], row["OutputCase"]].append(row)
    assignments = defaultdict(list)
    for row in _table(tables, "Area Assignments - Pier Labels"):
        assignments[row["PierName"], row["Story"]].append(row["UniqueName"])
    properties = defaultdict(list)
    if raw["kind"] == ORIGINAL:
        for row in _table(tables, "Pier Section Properties"):
            properties[row["Pier"], row["Story"]].append(row)
        meta = tables["Pier Section Properties"]["field_metadata"]["units_by_field"]
        lengths = ("WidthBot", "ThickBot", "WidthTop", "ThickTop", "CGBotX", "CGBotY", "CGBotZ",
                   "CGTopX", "CGTopY", "CGTopZ")
        if any(meta.get(k) != "m" for k in lengths) or meta.get("AxisAngle") not in ("deg", "degree"):
            raise ValueError("PIER_SECTION_PROPERTY_UNITS_UNRESOLVED")
    return {"kind": raw["kind"], "model_sha256": model, "solution_reference": revision, "cases": cases,
            "properties": properties,
            "groups": groups, "assignments": assignments, "deck": deck}


def force_vector(row):
    values = {k: float(row[k]) for k in COMPONENTS}
    if not all(isfinite(x) for x in values.values()):
        raise ValueError("PIER_FORCE_COMPONENT_NONFINITE")
    return values


def signed_vector(rows, kind):
    if kind == METHOD:
        if any(r.get("CaseType") != "NonStatic" for r in rows):
            raise ValueError("PIER_EXPECTED_NONLINEAR_FINAL_STATE")
        if len(rows) == 1 and rows[0].get("StepType") == "Step" and float(rows[0]["StepNumber"]) == 1:
            return force_vector(rows[0])
        if len(rows) == 2 and {r.get("StepType") for r in rows} == {"Max", "Min"}:
            lo, hi = map(force_vector, rows)
            if lo == hi:
                return lo
    # The owning combination plan must also classify this case as STATIC_LINEAR_ADD.
    elif kind == ORIGINAL:
        if (len(rows) == 1 and rows[0].get("CaseType") == "Combination"
                and rows[0].get("StepType") in (None, "", "None") and not rows[0].get("StepNumber")):
            return force_vector(rows[0])
        if len(rows) == 2 and {r.get("StepType") for r in rows} == {"Max", "Min"}:
            lo, hi = map(force_vector, rows)
            if lo == hi:
                return lo
    raise ValueError("SIGNED_CONCURRENT_PIER_CUT_REQUIRED")
