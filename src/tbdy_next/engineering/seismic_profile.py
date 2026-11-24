"""Project seismic parameters from assigned ETABS functions and TBDY 2018 Tables 3.1–3.3."""
from __future__ import annotations

from collections import defaultdict
from math import isclose, isfinite

from ..basis_linkage import SPECTRUM_CASE, SPECTRUM_FUNCTION
from .seismic_input_review import physical_height, project_review, valid_review_digest

SCHEMA = "tbdy.next.seismic-project-profile.v1"
INPUT_SCHEMA = "tbdy.next.seismic-project-inputs.v1"
COMMON = ("I", "Ss", "S1", "TL", "SiteClass", "Fs", "F1", "SDS", "SD1", "DampRatio")
FIELDS = ("Rx", "Ry", "Dx", "Dy", *COMMON, "DD", "BKS", "DTS", "HN", "BYS")
CLASSES = {"BKS": (1, 2, 3), "BYS": tuple(range(1, 9)), "SiteClass": tuple("Z" + x for x in "ABCDEF"),
           "DD": tuple("DD-" + x for x in "1234"), "DTS": ("1", "1a", "2", "2a", "3", "3a", "4", "4a")}
MISSING = (None, "", "None", "N/A", "—")
IMPORTANCE = {1.5: 1, 1.2: 2, 1.0: 3}


def _value(key, raw):
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)) or raw in MISSING:
        raise ValueError("PROJECT_PARAMETER_INVALID:" + key)
    if key in ("DTS", "DD", "SiteClass"):
        value = str(raw).strip()
        if key == "DD":
            value = value.upper().replace("DD", "").lstrip("- ")
            value = "DD-" + value
        else:
            value = value.lower() if key == "DTS" else value.upper()
    else:
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("PROJECT_PARAMETER_INVALID:" + key) from None
        if not isfinite(value) or value < 0 or (value == 0 and key not in ("Ss", "S1", "SDS", "SD1", "DampRatio")):
            raise ValueError("PROJECT_PARAMETER_INVALID:" + key)
        if key == "DampRatio" and value >= 1:
            raise ValueError("PROJECT_PARAMETER_INVALID:" + key)
    if key in CLASSES and value not in CLASSES[key]:
        raise ValueError("PROJECT_PARAMETER_INVALID:" + key)
    return int(value) if key in ("BKS", "BYS") else value


def normalize_values(values):
    if not isinstance(values, dict) or not values or set(values) - set(FIELDS):
        raise ValueError("PROJECT_PARAMETER_FIELDS_INVALID")
    return {key: _value(key, raw) for key, raw in values.items()}


def normalize_inputs(raw, source_data_sha256):
    required = {"schema", "source_data_sha256", "values"}
    if (not isinstance(raw, dict) or not required <= raw.keys() <= required | {"confirmed_profile_sha256"}
            or raw["schema"] != INPUT_SCHEMA or raw["source_data_sha256"] != source_data_sha256):
        raise ValueError("PROJECT_PARAMETERS_NATIVE_SOURCE_MISMATCH")
    if "confirmed_profile_sha256" in raw:
        if not valid_review_digest(raw["confirmed_profile_sha256"]):
            raise ValueError("PROJECT_INPUT_REVIEW_DIGEST_INVALID")
        if raw["values"] == {}:
            return dict(raw)
    return {**raw, "values": normalize_values(raw["values"])}


def _rows(tables, key):
    table = tables.get(key) or {}
    rows = table.get("rows")
    if (table.get("status") != "CAPTURED" or table.get("table_key") != key or not isinstance(rows, list)
            or len(rows) != table.get("row_count") or not all(isinstance(row, dict) for row in rows)):
        return []
    return rows


def _axis(row):
    if row.get("CoordSys") != "Global" or row.get("LoadName") not in ("U1", "U2"):
        return None
    try:
        angle = float(row["Angle"]) + (90 if row["LoadName"] == "U2" else 0)
        turn = round(angle / 90)
    except (ValueError, KeyError, TypeError, OverflowError):
        return None
    if isclose(angle, turn * 90, abs_tol=1e-7, rel_tol=0):
        return "Y" if turn % 2 else "X"
    return None


def _height_class(height, dts):
    # Upper limits are inclusive. The last two columns share rows BYS 4–8.
    limits = {"1": (7, 10.5, 17.5, 28, 42, 56, 70), "2": (7, 10.5, 17.5, 28, 42, 56, 70),
              "3": (10.5, 17.5, 28, 42, 56, 70, 91), "4": (10.5, 17.5, 28, 42, 56, 91, 105)}
    return next((8 - i for i, upper in enumerate(limits[dts[0]]) if height <= upper), 1)


def _dts(sds, bks):
    grade = 4 - sum(sds >= limit for limit in (0.33, 0.50, 0.75))
    return str(grade) + ("a" if bks == 1 else "")


def _constant(rows, key):
    try:
        values = {_value(key, row[key]) for row in rows if row.get(key) not in MISSING}
    except ValueError:
        return None
    return next(iter(values)) if len(values) == 1 else None


def project_seismic_profile(source, *, physical_scope=None, basement=None, input_sha=None):
    probe = source.get("vs04_basis_probe") or {}
    tables = probe.get("table_reads") or {}
    if (probe.get("read_only_invariant_proven") is False
            or (source.get("capture_metadata") or {}).get("vs04_same_session_capture") is False):
        tables = {}
    functions = defaultdict(list)
    for row in _rows(tables, SPECTRUM_FUNCTION):
        functions[row.get("Name")].append(row)
    assignments = []
    for row in _rows(tables, SPECTRUM_CASE):
        if row.get("LoadName") == "U3":
            continue
        try:
            scale = float(row.get("TransAccSF"))
        except (TypeError, ValueError):
            scale = None
        if scale == 0:
            continue
        name = row.get("Function")
        definitions = functions.get(name, [])
        directions = {r["Direction"] for r in definitions if r.get("Direction") not in MISSING}
        assignments.append({"case": row.get("Name"), "function": name, "axis": _axis(row),
                            "load": row.get("LoadName"), "csys": row.get("CoordSys"), "angle_deg": row.get("Angle"),
                            "horizontal_tsc": bool(name and row.get("Name") and scale is not None and isfinite(scale)
                                                   and directions == {"Horizontal"})})

    fields = {k: {"value": None, "origin": "INPUT_REQUIRED", "basis": "Project input required"} for k in FIELDS}
    project_inputs = source.get("project_parameter_inputs") or {}
    inputs = project_inputs.get("values") or {}
    review_issues = []

    def resolve(key, value, origin, basis):
        if value is not None:
            manual = inputs.get(key)
            equivalent = (isclose(manual, value, rel_tol=1e-12, abs_tol=1e-14)
                          if isinstance(manual, (float, int)) and isinstance(value, (float, int)) else manual == value)
            if key in inputs and not equivalent:
                raise ValueError("PROJECT_PARAMETER_CONFLICT:" + key)
            fields[key] = {"value": value, "origin": origin, "basis": basis}
        elif key in inputs:
            fields[key] = {"value": inputs[key], "origin": "PROJECT_INPUT", "basis": "Source-bound project input"}
        else:
            fields[key]["basis"] = basis
        return fields[key]["value"]

    def from_functions(key, column, rows, *, axis=False):
        values = set()
        names = set()
        complete = bool(rows)
        for a in rows:
            names.add(str(a["case"]) + " / " + str(a["function"]))
            value = _constant(functions.get(a["function"], ()), column) if a["horizontal_tsc"] else None
            if value is None or (axis and not a["axis"]):
                complete = False
            values.add(value)
        value = next(iter(values)) if complete and len(values) == 1 else None
        basis = ", ".join(sorted(names)) or "Assigned horizontal response spectrum required"
        if rows and value is None:
            basis += " · unresolved " + column
        return resolve(key, value, "ETABS_FUNCTION", basis)

    for axis in "XY":
        rows = [a for a in assignments if a["axis"] in (None, axis)]
        for column in ("R", "D"):
            from_functions(column + axis.lower(), column, rows, axis=True)
    for key in COMMON:
        from_functions(key, key, assignments)
    for key, first, second in (("SDS", "Ss", "Fs"), ("SD1", "S1", "F1")):
        # Recover the product only when no assigned function reported that field.
        reported = any(row.get(key) not in MISSING for a in assignments for row in functions.get(a["function"], ()))
        left, right = fields[first]["value"], fields[second]["value"]
        if not reported and left is not None and right is not None:
            resolve(key, left * right, "DERIVED", "TBDY Eq. (2.1) / " + first + " × " + second)

    # Explicit user-defined Project Information items are also ETABS source data.
    # Consume only exact class/level identifiers, never infer DD from a case name.
    info = defaultdict(list)
    for row in _rows(tables, "Project Information"):
        key = str(row.get("Item", row.get("Name", ""))).strip().upper()
        info[key].append({"v": row.get("Data", row.get("Value"))})

    def classify(key, derived, basis, *, default=None):
        project_values = [r["v"] for r in info[key] if r["v"] not in MISSING]
        reported = [[r[key] for r in functions[a["function"]] if r.get(key) not in MISSING]
                    if a["horizontal_tsc"] else [] for a in assignments]
        native = project_values + [v for group in reported for v in group]
        if native:
            value = _constant([{key: v} for v in native], key)
            if value is None or (not project_values and not all(reported)) or (derived is not None and value != derived):
                issue = "ETABS project or spectrum values conflict with " + key + " / " + basis
                review_issues.append(issue)
                fields[key]["basis"] = issue
                return None
            return resolve(key, value, "ETABS_PROJECT", "ETABS / " + key)
        if derived is None and key not in inputs and default is not None:
            return resolve(key, default, "PROJECT_DEFAULT", basis)
        return resolve(key, derived, "DERIVED", basis)

    dd = classify("DD", None, "Strength design uses DD-2. Verify the assigned spectrum hazard level.",
                  default="DD-2")
    importance = fields["I"]["value"]
    bks = classify("BKS", IMPORTANCE.get(importance), "TBDY Table 3.1 / importance I")
    if importance is not None and importance not in IMPORTANCE:
        review_issues.append("Verify occupancy and importance I against TBDY Table 3.1.")
    sds = fields["SDS"]["value"]
    dts = classify("DTS", _dts(sds, bks) if dd == "DD-2" and sds is not None and bks else None,
                   "TBDY Table 3.2 / DD-2 SDS and BKS")

    ss, fs = fields["Ss"]["value"], fields["Fs"]["value"]
    if (dd == "DD-2" and bks and None not in (sds, ss, fs)
            and _dts(sds, bks) != _dts(ss * fs, bks)):
        review_issues.append("The reported SDS and Ss × Fs fall in different DTS bands in Table 3.2.")

    physical = physical_scope or {}
    stories = [r for r in physical.get("stories", ()) if r.get("applicability") == "IN_SCOPE"]
    roof = max((float(r["upper_elevation_m"]) for r in stories), default=None) if (
        physical.get("source_inventory_complete") is True) else None
    basement = basement or {}
    base = basement.get("design_base_m")
    extent = physical_height(stories) if physical.get("source_inventory_complete") is True else None
    height = roof - base if roof is not None and base is not None and roof > base else None
    basis = ("TBDY §3.3.1 / physical roof and adopted seismic base (m)" if height is not None or extent is None
             else "Sum of physical storey heights from the lowest floor to the roof. Verify the building base.")
    hn = classify("HN", height, basis, default=extent["total_m"] if extent else None)
    if hn is not None and extent and hn > extent["total_m"] + 1e-6:
        review_issues.append("The project height exceeds the verified physical storey stack.")
    height_basis = {"physical": extent, "profile_base_m": round(roof - hn, 9) if roof is not None and hn else None,
                    "roof_m": roof, "height_m": hn}
    classify("BYS", _height_class(hn, dts) if hn is not None and dts else None, "TBDY Table 3.3 / HN and DTS")
    comparison = dts or (_dts(sds, bks) if dd is None and sds is not None and bks else None)
    scenarios = []
    for cut in dict.fromkeys([basement.get("candidate_m"), basement.get("foundation_m")]):
        if roof is not None and cut is not None and cut < roof:
            h = roof - cut
            scenarios.append({"base_m": cut, "height_m": h, "DTS": comparison,
                              "assumed_DD": "DD-2" if comparison and not dts else None,
                              "BYS": _height_class(h, comparison) if comparison else None})
    profile = {"schema": SCHEMA, "fields": fields, "assignments": assignments, "physical_roof_m": roof,
               "height_basis": height_basis, "base_status": basement.get("status"),
               "height_scenarios": scenarios if fields["HN"]["origin"] in ("INPUT_REQUIRED", "PROJECT_DEFAULT") else [],
               "missing_inputs": [k for k in FIELDS if fields[k]["value"] is None]}
    parent_sha = (source.get("design_scenario") or {}).get("parent_input_sha256", input_sha)
    profile["review"] = project_review(profile, parent_sha, project_inputs.get("confirmed_profile_sha256"), review_issues)
    if profile["review"]["status"] == "CONFIRMED":
        profile["height_scenarios"] = []
    return profile
