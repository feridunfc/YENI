"""B2 adjacent-storey arithmetic over the existing, sealed ETABS source.

TBDY 2018 Table 3.6 / 3.6.2.1: compare (Delta/h)_avg to BOTH neighbours,
with a strict > 2 threshold. Basement applicability and the required 4.7 /
±5% eccentricity basis are NOT established by the RSX/RSY source.
ETABS Avg Drift is an explicitly assumed mean-relative-drift candidate.
No independent spectrum point maxima are subtracted or enveloped here.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from .archived_source_bridge import _source_table
from .quick_checks import CheckDefinition
from .story_delta import PRIMARY, SOURCE_SCHEMA, dec, story_heights
from .story_drift_binding import _verify_generic_capture

CHECK = CheckDefinition(
    "SOFT_STORY_B2", "B2 yumuşak kat — koşullu kaynak hesabı", 9,
    "TBDY 2018 Tablo 3.6 / §3.6.2.1", "CONDITIONAL_SOURCE_NUMERICAL")
STORIES = "Story Definitions"
BASE = "Tower and Base Story Definitions"
AVERAGES = "Story Max Over Avg Drifts"
DRIFTS = "Story Drifts"
LIMIT = Decimal("2")


@dataclass(frozen=True)
class StoryLevel:
    story: str
    elevation_m: Decimal
    height_m: Decimal


@dataclass(frozen=True)
class MeanDrift:
    story: str
    direction: str
    case: str
    average_m: Decimal | None
    source_status: str = "SOURCE_NUMERICAL"
    reason: str = ""


def compare_adjacent(
    levels: Sequence[StoryLevel], means: Sequence[MeanDrift],
) -> dict[str, Any]:
    """Pure arithmetic; ordered physical levels are inputs, never story names."""
    for s in levels:
        if (not isinstance(s.story, str) or not s.story or s.story != s.story.strip()
                or not isinstance(s.height_m, Decimal) or not s.height_m.is_finite()
                or s.height_m <= 0 or not isinstance(s.elevation_m, Decimal)
                or not s.elevation_m.is_finite()):
            raise ValueError("B2_INVALID_STORY_LEVEL")
    ordered = sorted(levels, key=lambda s: s.elevation_m)
    if (not ordered or len({s.story for s in ordered}) != len(ordered)
            or len({s.elevation_m for s in ordered}) != len(ordered)):
        raise ValueError("B2_EMPTY_OR_DUPLICATE_STORY_LEVEL")
    for lower, upper in zip(ordered, ordered[1:]):
        if abs(upper.elevation_m - lower.elevation_m - upper.height_m) > Decimal("0.000001"):
            raise ValueError("B2_NONADJACENT_LEVEL_GEOMETRY")
    expected_keys = {(s.story, d) for s in ordered for d in ("X", "Y")}
    indexed = {}
    for m in means:
        key = (m.story, m.direction)
        if key not in expected_keys or key in indexed or not m.case:
            raise ValueError("B2_DUPLICATE_OR_UNEXPECTED_MEAN_SLOT")
        if m.average_m is not None and (
                not isinstance(m.average_m, Decimal) or not m.average_m.is_finite()
                or m.average_m < 0):
            raise ValueError("B2_INVALID_MEAN_DRIFT")
        indexed[key] = m
    if set(indexed) != expected_keys:
        raise ValueError("B2_MEAN_SLOT_DENOMINATOR_MISMATCH")
    if any(len({m.case for m in means if m.direction == d}) != 1 for d in ("X", "Y")):
        raise ValueError("B2_MIXED_CASE_BASIS")

    items, story_results = [], []
    with localcontext() as ctx:
        ctx.prec = 34
        for i, story in enumerate(ordered):
            neighbours = [(j, ordered[j]) for j in (i - 1, i + 1)
                          if 0 <= j < len(ordered)]
            for direction in ("X", "Y"):
                current = indexed[story.story, direction]
                own = []
                for j, neighbour in neighbours:
                    reference = indexed[neighbour.story, direction]
                    item = {
                        "story": story.story, "adjacent_story": neighbour.story,
                        "neighbour_role": "ABOVE" if j > i else "BELOW",
                        "direction": direction, "case": current.case,
                        "height_m": str(story.height_m),
                        "adjacent_height_m": str(neighbour.height_m),
                        "average_drift_m": (str(current.average_m) if current.average_m is not None else None),
                        "adjacent_average_drift_m": (str(reference.average_m) if reference.average_m is not None else None),
                        "normalized_mean": None, "adjacent_normalized_mean": None,
                        "eta_ki_candidate": None, "threshold": "2.0",
                        "status": "UNRESOLVED_SOURCE", "reason_codes": [],
                        "formal_compliance": "NOT_PROVEN",
                    }
                    if current.average_m is None or reference.average_m is None:
                        item["reason_codes"] = [
                            f"{m.story}/{direction}:{m.reason or m.source_status}"
                            for m in (current, reference) if m.average_m is None]
                    else:
                        ratio = current.average_m / story.height_m
                        reference_ratio = reference.average_m / neighbour.height_m
                        item.update(normalized_mean=str(ratio),
                                    adjacent_normalized_mean=str(reference_ratio))
                        if reference_ratio == 0:
                            item["status"] = "UNDEFINED_ZERO_REFERENCE_DRIFT"
                            item["reason_codes"] = ["B2_ZERO_DENOMINATOR"]
                        else:
                            eta = ratio / reference_ratio
                            item.update(
                                eta_ki_candidate=str(eta),
                                status=("THRESHOLD_EXCEEDED" if eta > LIMIT
                                        else "THRESHOLD_NOT_EXCEEDED"))
                    items.append(item)
                    own.append(item)
                resolved = [x for x in own if x["eta_ki_candidate"] is not None]
                complete = bool(own) and len(resolved) == len(own)
                values = [Decimal(x["eta_ki_candidate"]) for x in resolved]
                exceeded = any(x > LIMIT for x in values)
                story_results.append({
                    "story": story.story, "direction": direction, "case": current.case,
                    "max_observed_eta": str(max(values)) if values else None,
                    "eta_ki_candidate": str(max(values)) if values and complete else None,
                    "numeric_complete": complete, "observed_threshold_exceeded": exceeded,
                    "expected_neighbours": len(own), "resolved_neighbours": len(resolved),
                    "status": ("THRESHOLD_EXCEEDED" if exceeded else
                               "THRESHOLD_NOT_EXCEEDED" if complete else "UNRESOLVED"),
                    "reason": "" if own else "NO_ADJACENT_DEFINED_STORY",
                    "applicability": "BASEMENT_AND_PHYSICAL_SCOPE_NOT_PROVEN",
                    "formal_compliance": "NOT_PROVEN",
                })
    computed = sum(x["eta_ki_candidate"] is not None for x in items)
    triggered = sum(x["status"] == "THRESHOLD_EXCEEDED" for x in items)
    complete = bool(items) and computed == len(items)
    return {
        "items": items, "story_results": story_results,
        "expected_count": len(story_results),
        "evaluated_count": sum(x["numeric_complete"] for x in story_results),
        "comparison_coverage": {
            "expected": len(items), "resolved": computed,
            "unresolved": len(items) - computed, "complete": complete,
        },
        "threshold_exceeded_comparisons": triggered,
        "numeric_condition": (
            "B2_THRESHOLD_EXCEEDED_IN_SOURCE_SCENARIO" if triggered else
            "NO_B2_THRESHOLD_EXCEEDANCE_IN_CAPTURED_CASES" if complete else
            "B2_SOURCE_SCENARIO_UNRESOLVED"),
    }


def _read(source: Mapping[str, Any], name: str, fields: tuple[str, ...],
          units: Mapping[str, str]) -> list[dict[str, str]]:
    tables = source.get("table_reads")
    if not isinstance(tables, Mapping) or not isinstance(tables.get(name), Mapping):
        raise ValueError("B2_SOURCE_TABLE_MISSING:" + name)
    if tables[name].get("table_key") != name:
        raise ValueError("B2_SOURCE_TABLE_IDENTITY_CONFLICT:" + name)
    return _source_table(tables, name, fields, units)


def _levels(source: Mapping[str, Any]) -> tuple[list[StoryLevel], dict]:
    heights = story_heights(source)
    rows = _read(source, STORIES, ("Tower", "Story", "Height"), {"Height": "m"})
    bases = _read(source, BASE, ("Tower", "BSName", "BSElev"), {"BSElev": "m"})
    if len(bases) != 1 or any(r["Tower"] != bases[0]["Tower"] for r in rows):
        raise ValueError("B2_SINGLE_TOWER_BASE_REQUIRED")
    base = bases[0]
    if (any(not base[k] or base[k] != base[k].strip() or base[k] == "None"
            for k in ("Tower", "BSName")) or base["BSName"] in heights):
        raise ValueError("B2_BASE_STORY_IDENTITY_INVALID")
    if any(not r["Story"] or r["Story"] != r["Story"].strip() or r["Story"] == "None" for r in rows):
        raise ValueError("B2_STORY_IDENTITY_INVALID")
    z = dec(base["BSElev"], "B2_BASE_ELEVATION")
    levels = []
    # Reuse the observed ETABS top-to-bottom ordering convention from
    # archived_source_bridge. This is a disclosed candidate, not a census.
    for row in reversed(rows):
        z += heights[row["Story"]]
        levels.append(StoryLevel(row["Story"], z, heights[row["Story"]]))
    point_levels = set()
    point_counts = {s.story: {
        "story": s.story, "lower_elevation_m": str(s.elevation_m - s.height_m),
        "upper_elevation_m": str(s.elevation_m), "at_level_points": 0,
        "intermediate_points": 0, "lower_boundary_points": 0,
    } for s in levels}
    point_table = (source.get("table_reads") or {}).get("Point Object Connectivity")
    points_captured = isinstance(point_table, Mapping) and point_table.get("status") == "CAPTURED"
    if points_captured:
        points = _read(source, "Point Object Connectivity",
                       ("UniqueName", "Story", "Z"), {"Z": "m"})
        bounds = {s.story: (s.elevation_m - s.height_m, s.elevation_m) for s in levels}
        tolerance = Decimal("0.000001")
        for row in points:
            if row["Story"] in bounds:
                lower, upper = bounds[row["Story"]]
                point_z = dec(row["Z"], "B2_POINT_Z")
                # A point assigned to a story may lie inside its vertical span.
                # Only points at its upper plane corroborate the story elevation;
                # neither interior points nor lower-boundary points move a level.
                if point_z < lower - tolerance or point_z > upper + tolerance:
                    raise ValueError("B2_STORY_ORDER_POINT_ELEVATION_CONFLICT:" + row["Story"])
                counts = point_counts[row["Story"]]
                if abs(point_z - upper) <= tolerance:
                    point_levels.add(row["Story"])
                    counts["at_level_points"] += 1
                elif abs(point_z - lower) <= tolerance:
                    counts["lower_boundary_points"] += 1
                else:
                    counts["intermediate_points"] += 1
    return levels, {
        "basis": "OBSERVED_TOP_TO_BOTTOM_TABLE_ORDER_PLUS_BASE_AND_HEIGHTS",
        "base_story": base["BSName"], "base_elevation_m": base["BSElev"],
        "point_elevation_confirmed_stories": sorted(point_levels),
        "stories_without_point_elevation_confirmation": [
            s.story for s in levels if s.story not in point_levels],
        "point_table_captured": points_captured,
        "point_story_span_counts": list(point_counts.values()),
        "intermediate_point_count": sum(r["intermediate_points"] for r in point_counts.values()),
        "lower_boundary_point_count": sum(r["lower_boundary_points"] for r in point_counts.values()),
        "full_physical_census_proven": False,
    }


def _finish(record: dict) -> dict:
    raw = (json.dumps(record, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    return {**record, "result_sha256": sha256(raw).hexdigest()}


def bind_soft_story_b2(source: Mapping[str, Any] | None, *,
                       capture_error: str | None = None) -> dict[str, Any]:
    """One optional same-run derivation; malformed B2 never erases other checks."""
    if capture_error is not None and not isinstance(capture_error, str):
        capture_error = "B2_CAPTURE_ERROR_FIELD_NOT_TEXT"
    record = {
        **CHECK.as_dict(), "schema": "tbdy.next.vs07.soft-story-b2.v1",
        "dag_node_id": CHECK.check_id, "dag_declared_dependencies": ["STORY_DRIFT"],
        "dag_execution_authority": "DENIED",
        "result_kind": "CONDITIONAL_AVERAGE_DRIFT_SCENARIO",
        "formula": "eta_ki = (AvgDrift_i / h_i) / (AvgDrift_adjacent / h_adjacent)",
        "threshold_rule": "> 2.0", "status": "BLOCKED_SOURCE",
        "execution_status": "BLOCKED", "coverage_known": False,
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
        "normative_b2_classification": "NOT_PROVEN", "numerical_pass_issued": False,
        "case_roles": dict(PRIMARY), "source_payload_sha256": None,
        "source_capture_error": capture_error, "source_rows": [], "stories": [],
        "items": [], "story_results": [], "reason_codes": [],
        "expected_count": 0, "evaluated_count": 0,
        "source_coverage": {"expected": 0, "resolved": 0, "missing": 0, "invalid": 0},
        "comparison_coverage": {"expected": 0, "resolved": 0, "unresolved": 0, "complete": False},
        "threshold_exceeded_comparisons": 0,
        "numeric_condition": "B2_SOURCE_SCENARIO_UNRESOLVED",
        "authority_gaps": [
            "ETABS_AVG_DRIFT_EQUIVALENCE_TO_CODE_MEAN_NOT_PROVEN",
            "TBDY_4_7_PLUS_MINUS_5_PERCENT_ECCENTRICITY_NOT_PROVEN",
            "BASEMENT_APPLICABILITY_AND_FULL_PHYSICAL_CENSUS_NOT_PROVEN",
            "MODEL_ANALYSIS_GENERATION_NOT_INDEPENDENTLY_PROVEN",
        ],
        "assumptions_notes": [
            "ETABS Avg Drift / h, ortalama göreli kat ötelemesi oranı ADAYI olarak alınır; ortalama tanımı henüz normatif olarak doğrulanmamıştır.",
            "RSX/X ve RSY/Y aynı vaka ve Max izdüşümünde karşılaştırılır. ±%5 dışmerkezlik kolları ve TBDY 4.7 hesabı bu kayıttan kanıtlanmaz.",
            "Kat kotları, mevcut ETABS üstten alta tablo sırası ve temel kotuyla kurulur. Kat içi ara noktalar yükseklikleri değiştirmez; yalnız üst düzlem noktaları kotu destekler, kat aralığı dışındaki noktalar reddedilir.",
            "Bodrum niteliği ve fiziksel kapsam onaylanmadığından tüm tanımlı katlar korunur; eksik bir kat atlanarak yeni komşuluk kurulmaz.",
            "ηki > 2,0 yalnız koşullu kaynak hesabında eşik aşımıdır; yönetmelik B2 VAR/YOK veya bina PASS kararı değildir. Yuvarlatılmış kaynak hassasiyeti korunur.",
        ],
    }
    if capture_error or not isinstance(source, Mapping):
        record["reason_codes"] = ["B2_CAPTURE_UNAVAILABLE"]
        return _finish(record)
    try:
        _verify_generic_capture(source)
        if (source.get("schema") != SOURCE_SCHEMA
                or source.get("status") not in ("CAPTURED", "PARTIAL")
                or source.get("model_locked") is not True
                or source.get("model_units_code") != 6
                or source.get("model_units_unchanged") is not True
                or source.get("selection_restored") is not True
                or not isinstance(source.get("table_reads"), Mapping)):
            raise ValueError("B2_CAPTURE_CONTEXT_INVALID")
        record["source_payload_sha256"] = source["payload_sha256"]
        levels, ordering = _levels(source)
        record.update(
            coverage_known=True, story_order=ordering,
            stories=[{"story": s.story, "elevation_m": str(s.elevation_m),
                      "height_m": str(s.height_m)} for s in levels])
        names = {s.story for s in levels}
        groups, table_errors, descriptors = {}, {}, {}
        for name, values, units in (
            (AVERAGES, ("Max Drift", "Avg Drift", "Ratio"), {"Max Drift": "m", "Avg Drift": "m"}),
            (DRIFTS, ("Drift",), {"Drift": ""}),
        ):
            groups[name] = defaultdict(list)
            try:
                rows = _read(source, name,
                             ("Story", "OutputCase", "CaseType", "StepType", "Direction", *values), units)
                for index, row in enumerate(rows):
                    if row["OutputCase"] not in PRIMARY:
                        continue
                    if row["Story"] not in names or row["Direction"] not in ("X", "Y"):
                        raise ValueError("B2_UNEXPECTED_STORY_OR_DIRECTION:" + name)
                    if PRIMARY[row["OutputCase"]] == row["Direction"]:
                        groups[name][row["Story"], row["Direction"]].append((index, row))
                raw = source["table_reads"][name]
                descriptor = {k: raw.get(k) for k in ("table_key", "fields", "row_count", "field_metadata")}
                descriptor["schema_sha256"] = sha256(json.dumps(
                    {"fields": raw["fields"], "metadata": raw["field_metadata"]},
                    sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
                descriptors[name] = descriptor
            except (ValueError, TypeError, KeyError) as exc:
                table_errors[name] = str(exc)
        means = []
        for level in levels:
            for case, direction in PRIMARY.items():
                entry = {
                    "story": level.story, "direction": direction, "case": case,
                    "height_m": str(level.height_m), "average_drift_m": None,
                    "status": "SOURCE_MISSING", "reason": "",
                }
                mean = None
                try:
                    if table_errors:
                        raise ValueError("B2_TABLE_INVALID:" + " | ".join(table_errors.values()))
                    a = groups[AVERAGES].get((level.story, direction), [])
                    d = groups[DRIFTS].get((level.story, direction), [])
                    if len(a) > 1 or len(d) > 1:
                        raise ValueError("B2_DUPLICATE_SOURCE_GRAIN")
                    if not a or not d:
                        entry["reason"] = "B2_AVERAGE_OR_CROSSCHECK_ROW_MISSING"
                    else:
                        ai, ar = a[0]
                        di, dr = d[0]
                        if any(r["CaseType"] != "LinRespSpec" or r["StepType"] != "Max" for r in (ar, dr)):
                            raise ValueError("B2_CASE_STEP_PROJECTION_UNSUPPORTED")
                        # This observed adapter supports one unnumbered RS Max
                        # projection only. Never compare distinct step/branch
                        # envelopes, even if each local table pair agrees.
                        if any(r.get("StepNumber", "") not in ("", "None") for r in (ar, dr)):
                            raise ValueError("B2_NUMBERED_STEP_OR_BRANCH_UNSUPPORTED")
                        avg = dec(ar["Avg Drift"], "B2_AVERAGE")
                        maximum = dec(ar["Max Drift"], "B2_MAXIMUM")
                        ratio = dec(dr["Drift"], "B2_DRIFT_RATIO")
                        if avg < 0 or maximum < avg or ratio < 0:
                            raise ValueError("B2_NEGATIVE_OR_INCONSISTENT_DRIFT")
                        if avg > 0:
                            eta_bi = dec(ar["Ratio"], "B2_SOURCE_MAX_AVG_RATIO")
                            if eta_bi < 1 or (
                                    avg >= Decimal("0.000001")
                                    and abs(maximum / avg - eta_bi) >
                                    max(Decimal("0.01"), eta_bi * Decimal("0.01"))):
                                raise ValueError("B2_AVERAGE_RATIO_CROSSCHECK_CONFLICT")
                        residual = ratio * level.height_m - maximum
                        # Same source display-resolution reconciliation as story_delta.
                        tolerance = max(Decimal("0.000005"), level.height_m * Decimal("0.000001"))
                        if abs(residual) > tolerance:
                            raise ValueError("B2_MAXIMUM_CROSSCHECK_CONFLICT")
                        mean = avg
                        entry.update(
                            status="SOURCE_NUMERICAL", average_drift_m=str(avg),
                            max_drift_m=str(maximum), source_drift_ratio=str(ratio),
                            crosscheck_residual_m=str(residual),
                            average_table_row_index=ai, drift_table_row_index=di,
                            source_average_row=dict(ar), source_drift_row=dict(dr))
                except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
                    entry.update(status="SOURCE_INVALID", reason=str(exc))
                means.append(MeanDrift(level.story, direction, case, mean,
                                       entry["status"], entry["reason"]))
                record["source_rows"].append(entry)
        result = compare_adjacent(levels, means)
        record.update(result)
        numeric = sum(m.average_m is not None for m in means)
        record.update(
            status=("SOURCE_NUMERICAL" if result["comparison_coverage"]["complete"] else
                    "PARTIAL_SOURCE_NUMERICAL" if result["comparison_coverage"]["resolved"] else "BLOCKED_SOURCE"),
            execution_status=("EXECUTED_CONDITIONAL_NUMERICAL" if result["comparison_coverage"]["resolved"] else "BLOCKED"),
            source_tables=descriptors,
            source_coverage={
                "expected": len(means), "resolved": numeric,
                "missing": sum(m.source_status == "SOURCE_MISSING" for m in means),
                "invalid": sum(m.source_status == "SOURCE_INVALID" for m in means),
            },
            reason_codes=sorted({m.reason for m in means if m.reason}),
        )
    except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
        record["reason_codes"] = [str(exc)]
    return _finish(record)
