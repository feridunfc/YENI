"""VS06-B: bounded physical connectivity and displacement-projection evidence.

No new ETABS reader. This reviewer consumes the original SHA-sealed generic
capture *after* the VS05 receipt and VS06-A slot ledger are reconciled.
It never infers a full physical census, response-spectrum joint concurrence,
analysis-generation certification, or TBDY drift compliance.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from typing import Any, Mapping

from .story_delta import dec, story_heights, tbl
from .story_slot_ledger import build_story_slot_ledger

SCHEMA = "tbdy.next.vs06.physical-source-review.v1"


class PhysicalSourceError(ValueError):
    """Contradictory observed topology or source projection."""


def _canonical(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def review_story_physical_source(
    source: Mapping[str, Any],
    record: Mapping[str, Any],
    slot_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit recorded connectivity and source *types*, never authorize design.

    The full, original VS05 source-numeric record must have already been
    obtained from receipt replay. Rebuilding the VS06-A ledger here prevents a
    caller from removing unobserved slots or changing their source status.
    """
    if not isinstance(slot_ledger, Mapping) or not isinstance(record, Mapping):
        raise PhysicalSourceError("REVIEW_INPUT_NOT_OBJECT")
    expected_ledger = build_story_slot_ledger(source, record)
    if dict(slot_ledger) != expected_ledger:
        raise PhysicalSourceError("STORY_SLOT_LEDGER_REPLAY_MISMATCH")

    heights = story_heights(source)
    points = tbl(source, "Point Object Connectivity",
                 {"UniqueName", "Story", "X", "Y", "Z"},
                 {"X": "m", "Y": "m", "Z": "m"})
    columns = tbl(source, "Column Object Connectivity",
                  {"UniqueName", "Story", "UniquePtI", "UniquePtJ", "Length"},
                  {"Length": "m"})
    displacements = tbl(source, "Joint Displacements",
                        {"UniqueName", "Story", "OutputCase", "CaseType",
                         "StepType", "StepNumber", "Ux", "Uy"},
                        {"Ux": "m", "Uy": "m"})

    point_index: dict[str, dict[str, str]] = {}
    for row in points:
        name = row["UniqueName"]
        if not name or name in point_index:
            raise PhysicalSourceError("DUPLICATE_OR_EMPTY_POINT_ID")
        # Validate coordinates, but do not infer approval of diaphragm or mesh.
        for axis in ("X", "Y", "Z"):
            dec(row[axis], "POINT_" + axis)
        point_index[name] = row

    assigned = Counter()
    linked = Counter()
    unresolved: list[dict[str, str]] = []
    observed_connections: list[dict[str, str]] = []
    frames: set[str] = set()
    for row in columns:
        frame, story = row["UniqueName"], row["Story"]
        if not frame or frame in frames:
            raise PhysicalSourceError("DUPLICATE_OR_EMPTY_COLUMN_ID")
        frames.add(frame)
        if story not in heights:
            raise PhysicalSourceError("COLUMN_STORY_OUTSIDE_OBSERVED_STORIES")
        assigned[story] += 1
        length = dec(row["Length"], "COLUMN_LENGTH")
        if length <= 0:
            raise PhysicalSourceError("NONPOSITIVE_COLUMN_LENGTH")
        i, j = row["UniquePtI"], row["UniquePtJ"]
        if not i or not j or i == j or i not in point_index or j not in point_index:
            unresolved.append({
                "column": frame, "story": story,
                "reason": "MISSING_OR_IDENTICAL_END_POINT",
            })
            continue
        zi = dec(point_index[i]["Z"], "POINT_Z")
        zj = dec(point_index[j]["Z"], "POINT_Z")
        if zi == zj:
            unresolved.append({
                "column": frame, "story": story,
                "reason": "NO_VERTICAL_SEPARATION",
            })
            continue
        lower, upper = (i, j) if zi < zj else (j, i)
        linked[story] += 1
        observed_connections.append({
            "column": frame, "assigned_story": story,
            "lower_point": lower, "upper_point": upper,
            "lower_z_m": str(min(zi, zj)), "upper_z_m": str(max(zi, zj)),
            "source_length_m": str(length),
            "classification": "COLUMN_ENDPOINTS_OBSERVED_NOT_FULL_CENSUS",
        })

    # Source projection is a categorical proof gate, not displacement math.
    projection_count = Counter()
    max_rows = 0
    modal_rows = 0
    other_rows = 0
    for row in displacements:
        if row["UniqueName"] not in point_index:
            # A result point may be an analysis mesh node rather than a point
            # object. Keep it distinct from a verified physical object node.
            other_rows += 1
        case = row["OutputCase"]
        kind, step = row["CaseType"], row["StepType"]
        if case in ("RSX", "RSY"):
            if (kind, step) != ("LinRespSpec", "Max"):
                raise PhysicalSourceError("SPECTRUM_DISPLACEMENT_PROJECTION_UNEXPECTED")
            max_rows += 1
            projection_count[case] += 1
        elif case == "Modal":
            if (kind, step) != ("LinModRitz", "Mode"):
                raise PhysicalSourceError("MODAL_DISPLACEMENT_PROJECTION_UNEXPECTED")
            modal_rows += 1
        # Other combinations/time histories are not trusted or analyzed here.

    story_rows = []
    for story in sorted(heights):
        count, linked_count = assigned[story], linked[story]
        story_rows.append({
            "story": story, "height_m": str(heights[story]),
            "assigned_columns_observed": count,
            "endpoint_linked_columns_observed": linked_count,
            "member_presence_evidence": (
                "COLUMN_CONNECTIVITY_OBSERVED" if linked_count
                else ("COLUMN_ASSIGNMENT_WITH_UNRESOLVED_ENDPOINTS" if count
                      else "NO_COLUMN_CONNECTIVITY_OBSERVED")
            ),
            "physical_story_applicability": "NOT_PROVEN",
            "all_vertical_members_enumerated": False,
            "area_wall_null_and_mesh_census": "NOT_PROVEN",
        })
    by_story = {row["story"]: row for row in story_rows}
    slot_rows = []
    for slot in slot_ledger["slots"]:
        story = slot["story"]
        profile = by_story[story]
        slot_rows.append({
            "story": story, "case": slot["case"], "direction": slot["direction"],
            "source_status": slot["source_status"],
            "member_presence_evidence": profile["member_presence_evidence"],
            "candidate_column_count": profile["endpoint_linked_columns_observed"],
            "physical_applicability": "NOT_PROVEN",
            "signed_concurrent_spectrum_delta_available": False,
            "regulatory_status": "NOT_PROVEN",
            "reason_code": (
                "MISSING_SPECTRUM_STORY_DRIFT_ROW" if slot["source_status"] == "SOURCE_MISSING"
                else "SPECTRUM_SOURCE_NUMERIC_ONLY"
            ),
        })
    if len(slot_rows) != slot_ledger["expected_slot_count"]:
        raise PhysicalSourceError("PHYSICAL_SLOT_DENOMINATOR_MISMATCH")

    review = {
        "schema": SCHEMA,
        "check_id": "STORY_DRIFT",
        "dag_node_id": "STORY_DRIFT",
        "dag_execution_authority": "DENIED",
        "source_payload_sha256": source["payload_sha256"],
        "slot_ledger_sha256": slot_ledger["ledger_sha256"],
        "observed_column_count": len(columns),
        "endpoint_linked_column_count": len(observed_connections),
        "unresolved_column_count": len(unresolved),
        "observed_point_object_count": len(points),
        "joint_result_point_not_in_point_objects_count": other_rows,
        "response_spectrum_independent_max_rows": max_rows,
        "response_spectrum_max_by_case": dict(sorted(projection_count.items())),
        "ritz_modal_shape_rows": modal_rows,
        "signed_concurrent_spectrum_design_pairs_proven": 0,
        "full_physical_story_census_proven": False,
        "analysis_generation_independently_proven": False,
        "physical_applicability_proven": False,
        "normative_checks_issued": 0,
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "observed_stories": story_rows,
        "observed_columns": sorted(observed_connections, key=lambda r: r["column"]),
        "unresolved_columns": sorted(unresolved, key=lambda r: r["column"]),
        "slots": slot_rows,
        "note": (
            "Column endpoint existence is only an observed partial Frame connectivity "
            "fact. A zero count does not prove a physically absent story. "
            "RSX/RSY Max point displacements are independent non-concurrent "
            "envelopes; modal signed differences are not design earthquake drifts."
        ),
    }
    review["review_sha256"] = sha256(_canonical(review)).hexdigest()
    return review
