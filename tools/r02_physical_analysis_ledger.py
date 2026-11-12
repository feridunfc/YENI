"""R02: immutable physical-to-analysis column identity ledger, offline only.

Consumes the pinned, historical 87-column source bank. This makes no claim
about the full building, physical joint faces, effective lengths, or a later run.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys

from r01_verify_archived_bank import R01Error, force_inventory, read_bank

SCHEMA = "tbdy.next.r02-physical-analysis-ledger.v1"


def _xyz(values, field):
    if (not isinstance(values, list) or len(values) != 3 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
        raise R01Error("INVALID_SOURCE_XYZ:" + field)
    return tuple(values)


def _positive(value, field):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise R01Error("INVALID_POSITIVE_LENGTH:" + field)
    return value


def build_ledger(bank: dict, expected_columns: int) -> dict:
    _, verified = force_inventory(bank, expected_columns=expected_columns)
    by_member = defaultdict(list)
    for r in bank["force_states"]:
        by_member[r["Obj"]].append(r)
    ledger = []
    all_elements = set()
    for member in bank["members"]:
        name = member["frame_name"]
        frame = member.get("context", {}).get("frame", {})
        station = member.get("station_geometry", {})
        errors = []
        i, j = frame.get("point_i_id"), frame.get("point_j_id")
        if not isinstance(i, str) or not isinstance(j, str) or not i or not j or i == j:
            errors.append("I_J_POINT_IDENTITY_MISSING")
        elements = member.get("analysis_elements", [])
        if (not isinstance(elements, list) or not elements or
                any(not isinstance(e, str) or not e for e in elements) or
                len(set(elements)) != len(elements)):
            errors.append("ANALYSIS_ELEMENT_LIST_INVALID")
            elements = []
        if set(elements) & all_elements:
            errors.append("ANALYSIS_ELEMENT_SHARED_BETWEEN_COLUMNS")
        all_elements.update(elements)
        try:
            xyz_i = _xyz(station.get("point_i_xyz_m"), name + ":I")
            xyz_j = _xyz(station.get("point_j_xyz_m"), name + ":J")
            length = _positive(station.get("object_i_j_length_m"), name + ":length")
            measured = math.dist(xyz_i, xyz_j)
            if measured <= 0 or abs(measured - length) > 1e-7 * max(1, length):
                errors.append("I_J_GEOMETRY_LENGTH_CONFLICT")
        except R01Error as exc:
            xyz_i = xyz_j = None
            length = None
            errors.append(str(exc))
        native = by_member[name]
        output_elements = {r["Elm"] for r in native}
        if not output_elements.issubset(set(elements)) or output_elements != set(elements):
            errors.append("FORCE_ANALYSIS_ELEMENT_ROSTER_INCOMPLETE")
        stations = {(r["ObjSta"], r["Elm"], r["ElmSta"]) for r in native}
        declared_stations = station.get("observed_object_stations_m")
        if not isinstance(declared_stations, list) or not declared_stations:
            errors.append("STATION_GEOMETRY_ROSTER_MISSING")
        else:
            actual_obj_stations = {r["ObjSta"] for r in native}
            if {float(v) for v in declared_stations} != actual_obj_stations:
                errors.append("OBJECT_STATION_POPULATION_MISMATCH")
        if (station.get("first_station_matches_i_offset") is not True or
                station.get("last_station_matches_j_offset") is not True):
            errors.append("END_OFFSET_STATION_NOT_VERIFIED")
        # Observations do not prove effective lengths or actual joint faces.
        ledger.append({
            "physical_frame_id": name, "story_label": frame.get("story_label"),
            "section_assigned": frame.get("section_assigned"),
            "point_i_id": i, "point_j_id": j,
            "point_i_xyz_m": list(xyz_i) if xyz_i else None,
            "point_j_xyz_m": list(xyz_j) if xyz_j else None,
            "measured_object_length_m": length,
            "analysis_element_ids": elements,
            "native_station_tuple_count": len(stations),
            "native_force_rows": len(native),
            "native_output_case_count": len({r["LoadCase"] for r in native}),
            "source_geometry_status": "SOURCE_IDENTITY_BOUND" if not errors else "SOURCE_PARTIAL",
            "source_geometry_reasons": errors,
            "joint_face_binding_proven": False,
            "effective_length_proven": False,
            "as_built_rebar_qualified": False,
            "final_design_eligible": False,
        })
    reasons = Counter(r["source_geometry_status"] for r in ledger)
    return {
        "schema": SCHEMA,
        "source_run_id": bank["run_id"],
        "source_archive_sha256": bank["source_archive_sha256"],
        "source_bank_result_sha256": bank["result_sha256"],
        "selected_physical_columns": len(ledger),
        "analysis_element_count": len(all_elements),
        "native_force_rows": verified["force_rows"],
        "physical_member_identity_status": "SOURCE_CENSUS_BOUND" if not reasons["SOURCE_PARTIAL"] else "PARTIAL",
        "source_status_counts": dict(reasons),
        "members": ledger,
        "full_building_column_population_proven": False,
        "physical_joint_face_population_proven": False,
        "analysis_generation_qualified": False,
        "normative_design_authority": "DENIED",
        "engineering_release": "NOT_READY",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] /
                        "config/r01_archived_sources.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.manifest.read_text(encoding="utf-8"))
        bank = read_bank(args.bank, config["bank_zip_sha256"])
        if bank.get("source_archive_sha256") != config["native_archive_sha256"]:
            raise R01Error("ARCHIVE_SOURCE_BINDING_MISMATCH")
        result = build_ledger(bank, config["expected_columns"])
        payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise R01Error("OUTPUT_EXISTS")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        print(json.dumps({key: result[key] for key in (
            "schema", "source_run_id", "selected_physical_columns",
            "analysis_element_count", "native_force_rows",
            "physical_member_identity_status", "engineering_release")},
            ensure_ascii=False, indent=2))
        return 0 if result["physical_member_identity_status"] == "SOURCE_CENSUS_BOUND" else 2
    except (R01Error, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"r02_status": "REJECTED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
