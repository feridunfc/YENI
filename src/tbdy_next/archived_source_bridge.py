"""VS05-ARCH-D3: live-derived, archived source -> typed candidate facts -> FCR.

Pure offline reader. The source argument must come from the independently
receipt-verified build_complete_report() boundary. A caller-supplied JSON
claim of integrity is NOT trusted by this module as official certification.
No COM operations; no new ETABS analysis; no normative design PASS.

A limited, explicitly incomplete candidate compilation covers observed
tower/story labels and exact frame COLUMN/BEAM I/J connectivity; all absent
area/wall/NULL/combination semantics are recorded as open source gaps.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Mapping

from .candidate_model_contracts import (
    PROFILE_SCHEMA, COMBO_SCHEMA, BASE, UPPER,
    compile_limited_source_candidates,
)
from .compiled_dag import (
    CompilationRejected, RegulatoryCompiler, assess_candidate_plan,
    canonical_json,
)

REPORT_SCHEMA = "tbdy.next.complete.engineering.report.v1"
RESULT_SCHEMA = "tbdy.next.vs05.arch-d3.source-bound-candidate-run.v1"
STORIES_KEY = "Story Definitions"
BASE_KEY = "Tower and Base Story Definitions"
CASE_KEY = "Load Case Definitions - Summary"
COMBOS_KEY = "Load Combination Definitions"
SPECTRUM_KEY = "Load Case Definitions - Response Spectrum"
FRAME_TYPES = {"Column": "COLUMN", "Beam": "BEAM"}


def _source_table(
    tables: Mapping[str, Any], name: str, required: tuple[str, ...],
    expected_units: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    table = tables.get(name)
    if not isinstance(table, Mapping) or table.get("status") != "CAPTURED":
        raise CompilationRejected(name + ":SOURCE_TABLE_NOT_CAPTURED")
    fields = table.get("fields")
    rows = table.get("rows")
    metadata = table.get("field_metadata")
    if (not isinstance(fields, list) or len(fields) != len(set(fields))
            or not set(required).issubset(set(fields))
            or not isinstance(rows, list) or not rows
            or type(table.get("row_count")) is not int
            or len(rows) != table["row_count"]
            or not isinstance(metadata, Mapping)
            or metadata.get("status") != "OK"
            or not isinstance(metadata.get("field_keys"), list)
            or not set(fields).issubset(set(metadata["field_keys"]))
            or not isinstance(metadata.get("units_by_field"), Mapping)):
        raise CompilationRejected(name + ":TABLE_FIELDS_ROWS_METADATA_INVALID")
    units = metadata["units_by_field"]
    if any(units.get(k) != v for k, v in (expected_units or {}).items()):
        raise CompilationRejected(name + ":SOURCE_UNIT_MISMATCH")
    if any(not isinstance(row, dict) or set(row) != set(fields)
           or any(not isinstance(value, str) for value in row.values())
           for row in rows):
        raise CompilationRejected(name + ":SOURCE_ROW_SHAPE_INVALID")
    return rows


def _number(value: Any, label: str, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CompilationRejected(label + ":DECIMAL_STRING_REQUIRED")
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise CompilationRejected(label + ":INVALID_DECIMAL") from None
    if not d.is_finite() or (positive and d <= 0):
        raise CompilationRejected(label + ":NONFINITE_OR_NONPOSITIVE")
    return d


def _nonblank(value: Any, label: str) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or value == "None"):
        raise CompilationRejected(label + ":IDENTITY_MISSING")
    return value


def _build_profile(
    report: Mapping[str, Any], source: Mapping[str, Any],
    snapshot_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    geo = source.get("geometry_capture")
    basis = source.get("vs04_basis_probe")
    if (not isinstance(geo, Mapping) or
            geo.get("schema") != "tbdy.next.geometry.capture.v2" or
            geo.get("present_units") != geo.get("present_units_after") or
            geo.get("present_units") != 6 or
            geo.get("unit_state_unchanged") is not True or
            not isinstance(basis, Mapping) or
            basis.get("schema") != "tbdy.next.vs04e.basis-source-probe.v1" or
            basis.get("read_only_invariant_proven") is not True or
            basis.get("units_before") != basis.get("units_after") or
            basis.get("units_before") != 6):
        raise CompilationRejected("EXACT_LIVE_GEOMETRY_AND_BASIS_SOURCE_UNITS_REQUIRED")
    tables = basis.get("table_reads")
    geometry_tables = geo.get("tables")
    if not isinstance(tables, Mapping) or not isinstance(geometry_tables, Mapping):
        raise CompilationRejected("SOURCE_TABLE_REGISTRY_MISSING")

    definitions = _source_table(
        tables, STORIES_KEY, ("Tower", "Story", "Height", "GUID"),
        {"Height": "m"})
    bases = _source_table(
        tables, BASE_KEY, ("Tower", "BSName", "BSElev", "GUID"),
        {"BSElev": "m"})
    if len(bases) != 1 or not definitions:
        raise CompilationRejected("SINGLE_TOWER_BASE_AND_STORIES_REQUIRED")
    tower = _nonblank(bases[0]["Tower"], "tower")
    base_name = _nonblank(bases[0]["BSName"], "base_story_name")
    base_elev = _number(bases[0]["BSElev"], "base_elevation")
    all_stories = [{
        "story_id": base_name, "role": BASE,
        "elevation_m": str(base_elev), "height_m": None,
    }]
    # ETABS v23 observed Story Definitions table has top-to-bottom order.
    # We record this as a candidate ordering assumption, never engineering
    # level completeness or physical basement proof.
    elev = base_elev
    story_names = {base_name}
    for row in reversed(definitions):
        name = _nonblank(row["Story"], "story_name")
        if row["Tower"] != tower or name in story_names:
            raise CompilationRejected("TOWER_STORY_IDENTITY_COLLISION")
        story_names.add(name)
        height = _number(row["Height"], "story_height",positive=True)
        elev += height
        all_stories.append({
            "story_id": name, "role": UPPER,
            "elevation_m": str(elev), "height_m": str(height),
        })
    assignment = _source_table(
        geometry_tables, "FRAME_ASSIGNMENTS",
        ("Story", "UniqueName", "Type"))
    columns = _source_table(
        geometry_tables, "COLUMN_CONNECTIVITY",
        ("Story","UniqueName","UniquePtI","UniquePtJ"))
    beams = _source_table(
        geometry_tables, "BEAM_CONNECTIVITY",
        ("Story","UniqueName","UniquePtI","UniquePtJ"))
    by_type = {}
    for typ, rows in (("Column", columns),("Beam",beams)):
        for row in rows:
            identity = (_nonblank(row["Story"], "member_story"),
                        _nonblank(row["UniqueName"], "member_id"))
            if identity in by_type:
                raise CompilationRejected("DUPLICATE_FRAME_CONNECTION_OR_CROSS_TYPE")
            if identity[0] not in story_names:
                raise CompilationRejected("FRAME_REFERENCES_UNKNOWN_STORY")
            start = _nonblank(row["UniquePtI"], "UniquePtI")
            end = _nonblank(row["UniquePtJ"], "UniquePtJ")
            if start == end:
                raise CompilationRejected("FRAME_ENDPOINTS_IDENTICAL")
            by_type[identity] = (typ, start, end)
    census = {}
    unknown_frame_types = {}
    for row in assignment:
        key = (_nonblank(row["Story"], "frame_story"),
               _nonblank(row["UniqueName"], "frame_id"))
        if key in census or key[0] not in story_names:
            raise CompilationRejected("FRAME_ASSIGNMENT_DUPLICATE_OR_UNKNOWN_STORY")
        typ = _nonblank(row["Type"], "frame_type")
        census[key] = typ
        if typ not in FRAME_TYPES:
            unknown_frame_types[typ] = unknown_frame_types.get(typ, 0) + 1
    for key, (kind, _, _) in by_type.items():
        if census.get(key) != kind:
            raise CompilationRejected("GEOMETRY_SUMMARY_CONNECTIVITY_DISAGREEMENT")
    missing_connections = [
        key for key, typ in census.items()
        if typ in FRAME_TYPES and key not in by_type
    ]
    if missing_connections:
        raise CompilationRejected("STRUCTURAL_FRAME_CONNECTIVITY_MISSING")
    elements = [{
        "element_id": unique,
        "story_id": level,
        "element_type": FRAME_TYPES[kind],
        "point_i": start,
        "point_j": end,
    } for (level,unique),(kind,start,end) in sorted(by_type.items())]
    model = _nonblank(str(report.get("model") or ""), "model_name")
    profile = {
        "schema": "tbdy.next.vs05.typed-model-profile.candidate.v2",
        "project_id": "UNAPPROVED_ETABS_PROJECT_CANDIDATE",
        "model_id": model,
        "version": "arch-d3-receipt-derived-candidate",
        "source_snapshot_sha256": snapshot_hash,
        "analysis_generation_id": None,
        "units": "kN_m_C",
        "stories": all_stories,
        "physical_elements": elements,
    }
    gaps = [
        "MODEL_ANALYSIS_GENERATION_NOT_INDEPENDENTLY_PROVEN",
        "ETABS_STORY_DEFINITIONS_TOP_TO_BOTTOM_ORDER_UNAPPROVED",
        "AREA_WALL_PHYSICAL_CONNECTIVITY_AND_CENSUS_NOT_OBSERVED",
        "APPROVED_PROJECT_MODEL_PROFILE_MISSING",
        "PHYSICAL_MEMBER_TO_ANALYSIS_MESH_ID_NOT_BOUND",
    ]
    if unknown_frame_types:
        gaps.append("UNRESOLVED_NON_COLUMN_BEAM_FRAME_TYPES")
    return profile, {
        "tower": tower,
        "candidate_base_name": base_name,
        "frame_assignment_row_count": len(assignment),
        "candidate_structural_frame_count": len(elements),
        "candidate_column_frame_count": len(columns),
        "candidate_beam_frame_count": len(beams),
        "non_column_beam_type_counts": dict(sorted(unknown_frame_types.items())),
        "missing_frame_connection_count": 0,
        "raw_scope_gaps": gaps,
    }


def _build_case_only_book(
    source: Mapping[str, Any], snapshot_hash: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    basis = source["vs04_basis_probe"]
    tables = basis["table_reads"]
    cases = _source_table(tables, CASE_KEY, ("Name", "Type", "GUID"))
    selected = _source_table(tables, SPECTRUM_KEY,
                             ("Name", "ModalCase", "LoadName", "Function"))
    raw_combos = _source_table(tables, COMBOS_KEY,
                               ("Name", "Type", "LoadName", "SF"))
    if not isinstance(selected,list) or len(selected) != 2:
        raise CompilationRejected("RESPONSE_SPECTRUM_XY_SOURCE_ROWS_NOT_EXACT")
    case_map = {}
    for row in cases:
        name = _nonblank(row["Name"], "case_id")
        guid = _nonblank(row["GUID"], "case_guid")
        if name in case_map:
            raise CompilationRejected("DUPLICATE_SOURCE_LOAD_CASE")
        case_map[name] = {"case_id": name, "source_case_guid": guid}
    if {r["Name"] for r in selected} != {"RSX","RSY"}:
        raise CompilationRejected("RESPONSE_SPECTRUM_CASE_NAMES_NOT_EXACT")
    if any(case_map.get(r["Name"]) is None
           or r["LoadName"] != ("U1" if r["Name"] == "RSX" else "U2")
           or r["ModalCase"] != "Modal" for r in selected):
        raise CompilationRejected("RSXY_SOURCE_CASE_OR_DIRECTION_NOT_MATCHED")
    book = {
        "schema":"tbdy.next.vs05.typed-combo-book.candidate.v2",
        "book_id":"SOURCE_CASES_ONLY_UNAPPROVED",
        "version":"arch-d3-case-list-candidate",
        "source_snapshot_sha256":snapshot_hash,
        "cases":sorted(case_map.values(),key=lambda r:r["case_id"]),
        # Full 271 raw combination rows cannot be silently promoted
        # into operator-verified consumer roles or concurrent forces.
        "combinations":[],
        "consumer_roles":[
            {"role_id":"SEISMIC_RESPONSE_X","source_ref_type":"CASE",
             "source_ref_id":"RSX","requires_concurrent_vector":False},
            {"role_id":"SEISMIC_RESPONSE_Y","source_ref_type":"CASE",
             "source_ref_id":"RSY","requires_concurrent_vector":False},
        ],
    }
    return book, {
        "source_case_count":len(cases),
        "source_case_only_consumer_count":2,
        "raw_combo_definition_row_count":len(raw_combos),
        "typed_combo_definitions_executed":0,
        "candidate_case_book_scope":"CASES_ONLY_NO_APPROVED_COMBO_GRAPH",
        "combo_gaps":[
            "FULL_NESTED_271_COMBINATION_OPERATOR_GRAPH_NOT_QUALIFIED",
            "COMBO_CONCURRENT_VECTOR_AND_DESIGN_ROLE_NOT_AUTHORIZED",
            "CASE_AND_COMBO_ANALYSIS_GENERATION_UNPROVEN",
        ],
    }


def compile_archived_source_candidate(
    report: Mapping[str, Any], compiler: RegulatoryCompiler
) -> dict[str, Any]:
    """Produce reduced typed candidate facts + frozen denominator + FCR.

    The caller is responsible for obtaining report through the original
    source/receipt verifier (build_complete_report) rather than trusting an
    unverified file with the same JSON fields.
    """
    if (not isinstance(report, Mapping) or report.get("schema") != REPORT_SCHEMA
            or report.get("source_mode") != "LIVE_ETABS"
            or report.get("formal_compliance") != "NOT_PROVEN"
            or report.get("engineering_release") != "NOT_READY"):
        raise CompilationRejected("EXACT_LIVE_REPORT_CONTRACT_REQUIRED")
    source = report.get("source_snapshot")
    if (not isinstance(source, Mapping) or
            source.get("source_mode") != "LIVE_ETABS"
            or not isinstance(source.get("analysis_sources"), Mapping)):
        raise CompilationRejected("ORIGINAL_LIVE_SOURCE_SNAPSHOT_MISSING")
    if source["analysis_sources"].get("analysis_generation_proven") is not False:
        raise CompilationRejected("SOURCE_ANALYSIS_GENERATION_STATE_INVALID")
    # Canonical source fingerprint is independent of report file pretty-
    # print bytes; it does not substitute for archived input.source receipt.
    snapshot_hash = sha256(canonical_json(source)).hexdigest()
    profile, physical = _build_profile(report,source,snapshot_hash)
    case_book, combinations = _build_case_only_book(source,snapshot_hash)
    compiled = compile_limited_source_candidates(compiler,profile,case_book)
    fcr = assess_candidate_plan(compiled["plan"], [])
    if (fcr["pass_count"] or fcr["fail_count"] or
            fcr["expected_count"] != fcr["reconciled_count"]):
        raise CompilationRejected("CANDIDATE_FCR_INCONSISTENT")
    return {
        "schema": RESULT_SCHEMA,
        "run_id": report["run_id"],
        "status": "LIVE_ARCHIVE_DERIVED_CANDIDATE_ONLY",
        "source_snapshot_sha256_canonical": snapshot_hash,
        "original_input_receipt_sha256_claim": (report.get("source_provenance")
                                                 or {}).get("input_sha256"),
        "profile_review":compiled["profile_review"],
        "combo_review":compiled["combo_review"],
        "candidate_physical_summary":physical,
        "candidate_combo_summary":combinations,
        "candidate_plan":compiled["plan"],
        "fcr":fcr,
        "source_only":True,
        "model_analysis_generation_proven":False,
        "formal_compliance":"NOT_PROVEN",
        "engineering_release":"NOT_READY",
        "note":("This view is derived from original verified run sources by "
                "an offline tool. It is not a new live ETABS analysis or "
                "a normative PASS."),
    }
