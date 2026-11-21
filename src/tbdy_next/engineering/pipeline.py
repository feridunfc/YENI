"""Single owner of live-source stage orchestration and the DAG execution registry.

Before this module the 13-stage live sequence lived inline in the HTTP handler
and four other flows (offline column bank, archived 127/C88 receipts, the
94-node catalog, CLI) had no common entry. Now:

* `STAGES` is the one declarative stage registry (owner module, receipts,
  94-node catalog bindings, mode). Node IDs are verified against the catalog.
* `run_source_pipeline` executes the live sequence once, for Web and CLI.
* The 94-node catalog keeps `execution_authority = DENIED`: binding a stage to
  a node documents coverage; it does not promote any node to code PASS.

Legacy receipts remain immutable. New runs additionally persist all returned
stage outputs under an engine-results receipt. Method changes are visible in
comparison; historical numerical equivalence is not assumed.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from ..analysis_numerics import evaluate_analysis_numerics
from ..analysis_sources import review_analysis_sources
from ..live_source_pipeline import evaluate_single_run_source_pipeline
from ..modal import evaluate_modal_mass
from ..next_checks import evaluate_next_capture
from ..normative_basis import review_normative_readiness
from ..quick_checks import evaluate_geometry_capture
from ..receipts import ReceiptRun
from ..schema import review_modal_schema
from ..source import parse_modal_capture

LIVE, ARCHIVED, OFFLINE_BANK = "LIVE_SOURCE_RUN", "ARCHIVED_RECEIPT_SCENARIO", "OFFLINE_COLUMN_BANK"


@dataclass(frozen=True)
class ArtifactContract:
    key: str
    field: str
    value: str

    def accepts(self, artifact: Any) -> bool:
        return isinstance(artifact, Mapping) and artifact.get(self.field) == self.value

    def describe(self) -> dict[str, str]:
        return {"key": self.key, "discriminator": self.field, "value": self.value}


_AXIAL_GEOMETRY = ArtifactContract("geometry", "stage", "QUICK_GEOMETRY_SCREENING")
_AXIAL_MATERIAL = ArtifactContract("extra", "stage", "VS03_MATERIAL_A1")
_AXIAL_SETUP = ArtifactContract("analysis_setup", "schema", "tbdy.next.r03.model-analysis-setup-audit.v2")
_AXIAL_FORCES = ArtifactContract("force_source", "schema", "tbdy.next.etabs-frame-force-source.v1")
_AXIAL_RESULT = ArtifactContract("column_axial", "schema", "tbdy.next.column-axial-check.v1")
_PMM_SECTION = ArtifactContract("pmm_section_source", "schema", "tbdy.next.etabs-column-pmm-section-source.v1")
_PMM_RESULT = ArtifactContract("column_pmm", "schema", "tbdy.next.column-pmm-check.v1")
_MIXED_COMPONENTS = ArtifactContract("mixed_demand_components", "schema", "tbdy.next.mixed-demand-components.v1")
_DEMAND_SOURCE = ArtifactContract("native_demand_sources", "schema", "tbdy.next.native-demand-source-evidence.v1")
_PMM_SCOPE = ArtifactContract("pmm_scope", "schema", "tbdy.next.column-pmm-expected-instances.v1")
_R08_LOCAL_RESULT = ArtifactContract("r08_local_slenderness", "schema", "tbdy.next.column-r08-local-live.v1")
_DESIGN_SCOPE = ArtifactContract("design_dependencies", "schema", "tbdy.next.member-design-dependencies.v1")
_DESIGN_REVISIONS = ArtifactContract("design_revisions", "schema", "tbdy.next.design-artifact-revisions.v1")
_R10_RESULT = ArtifactContract("r10_live", "schema", "tbdy.next.column-r10-live.v1")
_ALPHA_ITERATION = ArtifactContract("alpha_iteration", "schema", "tbdy.next.alpha-design-iteration.v1")
_CAPTURE_ARTIFACTS = (_AXIAL_FORCES, _PMM_SECTION)


@dataclass(frozen=True)
class StageSpec:
    key: str
    mode: str
    owner: str
    receipts: tuple[str, ...]
    dag_nodes: tuple[str, ...]
    summary: str
    condition: str = "ALWAYS"
    consumes: tuple[ArtifactContract, ...] = ()
    produces: tuple[ArtifactContract, ...] = ()
    method_version: str | None = None


STAGES: tuple[StageSpec, ...] = (
    StageSpec("modal", LIVE, "tbdy_next.modal", ("schema-discovery", "schema", "modal"),
              ("MODAL_MASS",), "Modal participating mass ratio"),
    StageSpec("geometry", LIVE, "tbdy_next.quick_checks", ("quick-geometry",),
              ("BEAM_GEOMETRY", "FRAME_CENSUS_GATE"), "Frame/section geometry census and minimum dimensions",
              "SUITE", produces=(_AXIAL_GEOMETRY,)),
    StageSpec("material-a1", LIVE, "tbdy_next.next_checks", ("quick-extra",),
              ("TORSION_A1", "MATERIAL_SECTION_GATE"), "Concrete fck screening and A1 torsion source classification",
              "NEXT_CAPTURE", produces=(_AXIAL_MATERIAL,)),
    StageSpec("vs04-source", LIVE, "tbdy_next.live_source_pipeline",
              ("vs04-schema", "vs04-numerics", "vs04-readiness", "vs04-pipeline"),
              ("ANALYSIS_BASIS_GATE", "DESIGN_SPECTRUM", "MODAL_PERIOD", "BASE_SHEAR"),
              "Analysis basis, spectrum and base-shear source screening", "ANALYSIS_SOURCES"),
    StageSpec("story-drift", LIVE, "tbdy_next.story_drift_binding", ("vs05-story-drift",),
              ("STORY_DRIFT", "STORY_CUT_GATE"), "Story drift source binding", "DELTA_SOURCE"),
    StageSpec("analysis-setup", LIVE, "tbdy_next.engineering.analysis_setup", ("r03-analysis-setup",),
              ("COMBINATION_DEFINITION_GATE", "LOAD_PATTERN_GATE", "ANALYSIS_GENERATION_GATE"),
              "ETABS definitions and explicit source-bound calculation assumptions", "BASIS_PROBE", produces=(_AXIAL_SETUP,),
              method_version="analysis-setup.adopted-basis.v1"),
    StageSpec("column-axial", LIVE, "tbdy_next.engineering.column_axial", ("column-axial",),
              ("COLUMN_AXIAL", "COLUMN_DEMAND"), "TS500 Eq. 7.7 axial compression over selected combinations",
              "COLUMN_REQUEST", consumes=(_AXIAL_GEOMETRY, _AXIAL_MATERIAL, _AXIAL_SETUP, _AXIAL_FORCES),
              produces=(_AXIAL_RESULT,), method_version="column-axial.v1"),
    StageSpec("column-pmm", LIVE, "tbdy_next.engineering.column_pmm", ("column-pmm",),
              ("COLUMN_PMM", "COLUMN_SECTION_CAPACITY"), "Signed-station P-M2-M3 with TS500 6.16 minimum eccentricity",
              "COLUMN_PMM_MEMBER", consumes=(_AXIAL_GEOMETRY, _AXIAL_FORCES, _AXIAL_RESULT, _PMM_SECTION),
              produces=(_PMM_RESULT, _PMM_SCOPE), method_version="column-pmm.v7"),
    StageSpec("design-dependencies", LIVE, "tbdy_next.engineering.design_dependencies", (), (),
              "Offline member/joint scope and fail-closed source dependencies; not a new code check",
              "DESIGN_SCENARIO", consumes=(_AXIAL_GEOMETRY, _PMM_SCOPE), produces=(_DESIGN_SCOPE,),
              method_version="offline-member-dependencies.d2.v1"),
    StageSpec("mixed-demand-components", LIVE, "tbdy_next.engineering.mixed_demands", (), (),
              "Native cut coverage, signed modal amplitude evidence, spectrum input definitions and same-source scalar replay",
              "PMM_SCOPE", consumes=(_AXIAL_RESULT, _PMM_SCOPE),
              produces=(_MIXED_COMPONENTS, _DEMAND_SOURCE), method_version="same-source-spectral-components.v8"),
    StageSpec("column-gates", LIVE, "tbdy_next.engineering.column_live_gates", (),
              ("COLUMN_REBAR", "COLUMN_AXIAL", "COLUMN_PMM"),
              "CHK-004/CHK-005 caps, reinforcement role and open gates over the SAME axial/PMM results "
              "(computed by pipeline; persisted in engine-results)", "COLUMN_REQUEST"),
    StageSpec("beam-r10-live", LIVE, "tbdy_next.engineering.beam_r10_live", (),
              ("BEAM_DEMAND", "BEAM_FLEXURE", "BEAM_REBAR", "BEAM_SHEAR"),
              "Beam end demand targets, CHK-131..136 multi-row cages, signed N=0 capacity and Ve terms "
              "(computed by pipeline; persisted in engine-results)", "COLUMN_REQUEST"),
    StageSpec("column-r10", LIVE, "tbdy_next.engineering.column_r10_live", (),
              ("JOINT_TOPOLOGY_CHECK", "JOINT_SHEAR", "SCWB", "COLUMN_SHEAR", "COLUMN_SHEAR_REBAR"),
              "TBDY 7.3.5 joint applicability, 7.3.6 SCWB, 7.5 joint shear and column confinement/shear "
              "(computed by pipeline; persisted in engine-results)", "COLUMN_REQUEST", produces=(_R10_RESULT,),
              method_version="column-r10-spectral-shear.v8"),
    StageSpec("second-order", LIVE, "tbdy_next.story_second_order", ("r08-second-order",),
              ("GLOBAL_SECOND_ORDER",), "TBDY 4.33 story second-order precheck", "R08_SOURCE"),
    StageSpec("column-r08-local", LIVE, "tbdy_next.engineering.column_r08_local_live", (),
              ("COLUMN_SLENDERNESS", "COLUMN_PMM"),
              "TS500 local slenderness, adopted EI/K/Rm and scoped self-weight axial idealization for selected-section PMM",
              "COLUMN_PMM_MEMBER", consumes=(_AXIAL_GEOMETRY, _AXIAL_RESULT, _PMM_RESULT, _PMM_SCOPE),
              produces=(_R08_LOCAL_RESULT,), method_version="column-r08-local.adopted-basis.v12"),
    StageSpec("alpha-feedback", LIVE, "tbdy_next.engineering.alpha_iteration", (), (),
              "Bounded qualified signed alpha demand revision and dirty-member rechecks", "EXPLICIT_DESIGN_SCENARIO",
              consumes=(_DESIGN_SCOPE, _PMM_SCOPE, _PMM_RESULT, _R10_RESULT, _R08_LOCAL_RESULT),
              produces=(_ALPHA_ITERATION,), method_version="alpha-feedback.mixed-signed-same-cut.v6"),
    StageSpec("design-revisions", LIVE, "tbdy_next.engineering.design_dependencies", (), (),
              "Recorded candidate/demand to joint/story/Ve/R14 dependency revisions and consumed alpha feedback; no persistent cache",
              "DESIGN_SCENARIO", consumes=(_DESIGN_SCOPE,), produces=(_DESIGN_REVISIONS,),
              method_version="offline-member-dependencies.d2.v1"),
    StageSpec("report-evidence", LIVE, "tbdy_next.engineering.pipeline", (), (),
              "Scoped story checks, source controls, design assignments and member evidence", "SUITE"),
    StageSpec("engine-results", LIVE, "tbdy_next.engineering.pipeline_snapshot", ("engine-results",), (),
              "Sealed returned-stage snapshot with source, method, registry and result hashes"),
    StageSpec("live-capture", LIVE, "tbdy_next.engineering.pipeline", ("live-capture",), (),
              "Completed live-source run bound to its engine results"),
    StageSpec("column-127-archived", ARCHIVED, "tbdy_next.engineering.live_column", (),
              ("COLUMN_PMM", "COLUMN_AXIAL", "COLUMN_SLENDERNESS"),
              "Archived R07-R09 127/C88 reconciliation; same gate primitives as the live path"),
    StageSpec("column-bank", OFFLINE_BANK, "tbdy_next.column_engine.store", ("column-bank",),
              ("COLUMN_DEMAND", "COLUMN_SHEAR", "SCWB", "JOINT_SHEAR"),
              "Native column ZIP/SQLite bank with PMM, shear, SCWB and joint views (offline; not fed by live capture)"),
)


def stage_registry() -> list[dict[str, Any]]:
    return [{"key": s.key, "mode": s.mode, "owner": s.owner, "receipts": list(s.receipts),
             "dag_nodes": list(s.dag_nodes), "condition": s.condition, "summary": s.summary,
             **({"consumes": [c.describe() for c in s.consumes]} if s.consumes else {}),
             **({"method_version": s.method_version} if s.method_version is not None else {}),
             **({"produces": [c.describe() for c in s.produces]} if s.produces else {})}
            for s in STAGES]


def _validate_dependency_contracts() -> None:
    """Require each typed pilot input to have exactly one preceding matching producer."""
    available = {artifact.key: artifact for artifact in _CAPTURE_ARTIFACTS}
    for stage in STAGES:
        for contract in stage.consumes:
            if available.get(contract.key) != contract:
                raise ValueError(f"INVALID_STAGE_DEPENDENCY:{stage.key}:{contract.key}")
        for contract in stage.produces:
            if contract.key in available:
                raise ValueError(f"DUPLICATE_STAGE_ARTIFACT_PRODUCER:{contract.key}")
            available[contract.key] = contract


def _stage_input_blockers(stage: StageSpec, artifacts: Mapping[str, Any]) -> list[str]:
    return [f"REQUIRED_ARTIFACT_UNAVAILABLE_OR_UNSUPPORTED:{spec.key}"
            for spec in stage.consumes if not spec.accepts(artifacts.get(spec.key))]


def dag_coverage(catalog: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Compare registry bindings with the 94-node catalog. Execution authority stays DENIED."""
    from ..compiled_dag import CANDIDATE_CATALOG_PATH, read_candidate_catalog

    catalog = catalog or read_candidate_catalog(CANDIDATE_CATALOG_PATH)
    nodes = {n["node_id"]: n["node_type"] for n in catalog["nodes"]}
    bound: dict[str, list[str]] = {}
    for stage in STAGES:
        for node in stage.dag_nodes:
            bound.setdefault(node, []).append(stage.key)
    unknown = sorted(set(bound) - set(nodes))
    covered = sorted(set(bound) & set(nodes))
    by_type: dict[str, dict[str, int]] = {}
    for node_id, node_type in nodes.items():
        row = by_type.setdefault(node_type, {"total": 0, "bound_to_stage": 0})
        row["total"] += 1
        row["bound_to_stage"] += node_id in bound
    return {
        "schema": "tbdy.next.pipeline-dag-coverage.v1",
        "catalog_node_count": len(nodes), "bound_node_count": len(covered),
        "unbound_node_count": len(nodes) - len(covered),
        "by_node_type": dict(sorted(by_type.items())),
        "unknown_node_ids": unknown, "bindings": {k: bound[k] for k in sorted(bound)},
        "dag_execution_authority": "DENIED",
        "note": "Bound means a registered stage computes related evidence; no node is promoted to code PASS.",
    }


def calculate_modal(payload: Mapping[str, Any], *, case: str, run: ReceiptRun, input_sha: str,
                    receipt_schema: str | None = None) -> dict[str, Any]:
    """One authoritative modal postprocess path for live, imported and CLI data."""
    schema_review = review_modal_schema(payload)
    run.record("schema-discovery", schema_review, input_sha256=input_sha, receipt_schema=receipt_schema)
    table = parse_modal_capture(payload, case=case)
    run.record("schema", {
        "stage": "MODAL_ROW_VALIDATION", "status": "SCHEMA_VALID", "target_case": case,
        "case_row_count": len(table.rows), "raw_row_count": table.all_rows_count,
        "source_mode": table.origin, "engineering_release": "NOT_READY",
    }, input_sha256=input_sha)
    result = evaluate_modal_mass(table).as_dict()
    run.record("modal", result, input_sha256=input_sha)
    return result


def derive_report_evidence(source: Mapping[str, Any], stages: Mapping[str, Any], *,
                           catalog: Mapping[str, Any] | None = None,
                           physical_scope: Mapping[str, Any] | None = None,
                           scoped_second_order: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Complete the evidence consumed by JSON and printable reports during execution."""
    from ..physical_story_scope import review_physical_story_scope, scope_story_drift
    from ..source_control_bundle import bind_source_controls
    from .design_assignments import design_assignments

    inventory = source.get("vs05_delta_source")
    if physical_scope is None and "vs05_delta_source" in source:
        physical_scope = review_physical_story_scope(inventory)
    declared_story_drift = stages.get("story_drift")
    declared_second_order = stages.get("r08_second_order")
    story_drift = declared_story_drift
    if physical_scope is not None and story_drift is not None:
        story_drift = scope_story_drift(story_drift, inventory, physical_scope)
    if scoped_second_order is None:
        scoped_second_order = declared_second_order
        if physical_scope is not None and declared_second_order is not None:
            from ..story_second_order import scope_story_second_order

            scoped_second_order = scope_story_second_order(
                declared_second_order, source.get("r08_second_order_source"), inventory, physical_scope,
            )

    slot_ledger = physical_source_review = effective_drift_readiness = None
    if (declared_story_drift is not None
            and declared_story_drift.get("execution_status") == "EXECUTED_SOURCE_NUMERICAL"):
        from ..effective_drift_readiness import review_effective_drift_readiness
        from ..story_physical_source import review_story_physical_source
        from ..story_slot_ledger import build_story_slot_ledger

        slot_ledger = build_story_slot_ledger(inventory, declared_story_drift)
        physical_source_review = review_story_physical_source(inventory, declared_story_drift, slot_ledger)
        if catalog is None:
            from ..compiled_dag import CANDIDATE_CATALOG_PATH, read_candidate_catalog

            catalog = read_candidate_catalog(CANDIDATE_CATALOG_PATH)
        effective_drift_readiness = review_effective_drift_readiness(
            inventory, declared_story_drift, slot_ledger, physical_source_review, catalog,
        )

    b1_result = b1_status = None
    b1_geometry = source.get("vs06_b1_geometry_source")
    wall_loads = source.get("vs06_wall_load_source")
    if any(key in source for key in ("vs06_b1_geometry_source", "vs06_wall_load_source", "vs06_b1_geometry_capture_error")):
        if isinstance(b1_geometry, Mapping) and isinstance(wall_loads, Mapping):
            from ..b1_source_bridge import B1BridgeError, evaluate_b1_sources

            try:
                b1_result = evaluate_b1_sources(b1_geometry, wall_loads, physical_scope=physical_scope,
                                                physical_scope_source=inventory)
                b1_status = "SOURCE_BOUND_NUMERICAL"
            except (B1BridgeError, ValueError, TypeError, KeyError) as exc:
                b1_status = "BLOCKED_SOURCE_BINDING: " + str(exc)
        else:
            b1_status = "BLOCKED_REQUIRED_B1_SOURCES_MISSING"

    b2 = wall_geometry = earthquake_combinations = None
    if "vs05_delta_source" in source or "vs05_delta_capture_error" in source:
        from ..soft_story_b2 import bind_soft_story_b2

        b2 = bind_soft_story_b2(inventory, capture_error=source.get("vs05_delta_capture_error"),
                                physical_scope=physical_scope)
    if "vs06_b1_geometry_source" in source or "vs06_b1_geometry_capture_error" in source:
        from ..wall_geometry import bind_wall_geometry

        wall_geometry = bind_wall_geometry(source, physical_scope=physical_scope)
    if "vs04_basis_probe" in source:
        from ..earthquake_combinations import bind_earthquake_combinations

        earthquake_combinations = bind_earthquake_combinations(source)
    source_controls = bind_source_controls(source)

    pmm_reinforcement = slenderness_evidence = None
    pmm = stages.get("column_pmm")
    if pmm is not None:
        if pmm.get("section_evidence") is not None:
            from .column_axial import _columns
            from .column_pmm_section import build_pmm_section

            uid = pmm["member_id"]
            feature = source["column_axial"]
            _, pmm_reinforcement = build_pmm_section(
                feature["pmm_section_source"], next(row for row in _columns(stages["geometry"]) if row["element_id"] == uid),
                next(row for row in stages["column_axial"]["columns"] if row["element_id"] == uid),
                feature["design_preferences"], include_layout=True,
            )
        local_slenderness = stages.get("r08_local_slenderness") or {}
        if pmm.get("scope") == "ALL_COLUMNS" or pmm.get("member_id") == "ALL":
            representative = next(iter(pmm.get("members") or ()), None)
            local_slenderness = ((local_slenderness.get("per_member") or {}).get(representative.get("member_id"), {})
                                 if representative is not None else {})
        else:
            representative = pmm
        if representative is not None:
            slenderness_evidence = local_slenderness.get("evidence")
            if slenderness_evidence is None:
                from .live_column import project_column_slenderness_evidence

                slenderness_evidence = project_column_slenderness_evidence(source, representative, scoped_second_order)

    return {
        "column_pmm_reinforcement": pmm_reinforcement,
        "column_slenderness_evidence": slenderness_evidence,
        "design_assignments": design_assignments(stages.get("analysis_setup") or {}),
        "physical_story_scope": physical_scope,
        "story_drift": story_drift,
        "r08_second_order": scoped_second_order,
        "declared_story_drift_source_record": declared_story_drift if story_drift != declared_story_drift else None,
        "declared_r08_second_order_source_record": (declared_second_order
                                                   if scoped_second_order != declared_second_order else None),
        "vs06_story_slot_ledger": slot_ledger,
        "vs06_physical_source_review": physical_source_review,
        "vs06_effective_drift_readiness": effective_drift_readiness,
        "vs06_b1_result": b1_result,
        "vs06_b1_source_status": b1_status,
        "soft_story_b2": b2,
        "wall_geometry": wall_geometry,
        "source_controls": source_controls if source_controls["checks"] else None,
        "earthquake_combinations": earthquake_combinations,
    }


def _run_column_axial(source: Mapping[str, Any], geometry: Mapping[str, Any] | None,
                     extra: Mapping[str, Any] | None, setup: Mapping[str, Any] | None,
                     *, input_sha: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the typed axial pilot; enumerate expected members and combinations before calculation."""
    from .column_axial import CHECK, _columns, evaluate_column_axial
    from .design_assignments import ASSIGNED_DESIGN

    feature = source["column_axial"]
    feature = feature if isinstance(feature, Mapping) else {}
    request = feature.get("request")
    request = request if isinstance(request, Mapping) else {}
    setup_data = setup if isinstance(setup, Mapping) else {}
    artifacts = {"geometry": geometry, "extra": extra, "analysis_setup": setup,
                 "force_source": feature.get("force_source")}
    stage = next(stage for stage in STAGES if stage.key == "column-axial")
    blockers = _stage_input_blockers(stage, artifacts)

    census_proven = (_AXIAL_GEOMETRY.accepts(geometry)
                     and type(geometry.get("column_connectivity_count")) is int)
    if census_proven:
        members = _columns(geometry)
    else:
        # Preserve identifiable observed members even when the census cannot be qualified.
        capture = source.get("geometry_capture")
        tables = capture.get("tables") if isinstance(capture, Mapping) else None
        table = tables.get("COLUMN_CONNECTIVITY") if isinstance(tables, Mapping) else None
        connectivity = table.get("rows") if isinstance(table, Mapping) else None
        connectivity = connectivity if isinstance(connectivity, list) else []
        members = [{"element_id": row["UniqueName"], "story": row.get("Story")}
                   for row in connectivity if isinstance(row, Mapping)
                   and isinstance(row.get("UniqueName"), str) and row["UniqueName"]]
        blockers.append("COLUMN_CENSUS_UNVERIFIED")
    by_id = {row["element_id"]: row for row in members if row.get("element_id")}
    if census_proven and len(by_id) != len(members):
        census_proven = False
        blockers.append("COLUMN_CENSUS_DUPLICATE_OR_MISSING_UNIQUE_ID")
    targets = {uid: row for uid, row in by_id.items() if row.get("status") != "NOT_APPLICABLE"}

    mode = request.get("combination_source")
    mode = mode if isinstance(mode, str) else None
    names = setup_data.get("strength_design_combinations") if mode == "ETABS_STRENGTH" else request.get("combinations")
    names_valid = (isinstance(names, list) and bool(names)
                   and all(isinstance(name, str) and name for name in names) and len(set(names)) == len(names))
    expected_names = sorted({name for name in names or () if isinstance(name, str) and name}) if isinstance(names, list) else []
    assignment = request.get("design_assignment")
    assignment_bound = False
    if mode == ASSIGNED_DESIGN:
        groups = assignment.get("groups") if isinstance(assignment, Mapping) else None
        if (not isinstance(groups, Mapping) or not groups
                or any(not isinstance(group, list) for group in groups.values())
                or any(not isinstance(name, str) or not name for group in groups.values() for name in group)):
            names_valid = False
        else:
            assigned_names = {name for group in groups.values() for name in group}
            names_valid = names_valid and assigned_names == set(expected_names)
            assignment_bound = names_valid
            expected_names = sorted(set(expected_names) | assigned_names)
    if mode not in ("ETABS_STRENGTH", "SAVED_DEFAULTS", ASSIGNED_DESIGN) or not names_valid:
        blockers.append("COLUMN_COMBINATION_POPULATION_UNVERIFIED")
    if isinstance(setup, Mapping) and setup.get("definition_coverage_known") is not True:
        blockers.append("COMBINATION_DEFINITIONS_UNVERIFIED")
    if isinstance(extra, Mapping) and extra.get("status") == "SOURCE_SCHEMA_REVIEW_REQUIRED":
        blockers.append("CONCRETE_MATERIAL_SOURCE_UNVERIFIED")

    expected = [(uid, name) for uid in sorted(targets) for name in expected_names]
    result = None
    if not blockers:
        try:
            result = evaluate_column_axial(source, geometry, extra, setup=setup)
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            blockers.append(f"COLUMN_AXIAL_SOURCE_INVALID:{exc}")
        if result is not None and not all(contract.accepts(result) for contract in stage.produces):
            raise ValueError("INVALID_STAGE_OUTPUT:column-axial")
        if result is not None:
            blockers.extend(result["combination_plan"]["blockers"])
    if result is None:
        plan = {
            "source": mode, "base_run_id": request.get("base_run_id"),
            "base_input_sha256": request.get("base_input_sha256"),
            "combination_graph_sha256": setup_data.get("typed_graph_source_sha256"),
            "combinations": [{"name": name} for name in expected_names], "blockers": blockers,
        }
        if assignment_bound:
            plan["design_assignment"] = assignment
        columns = []
        for uid, row in by_id.items():
            column = {key: row.get(key) for key in ("story", "element_id", "section", "material_name")}
            if uid in targets:
                column.update(status="BLOCKED", reason=blockers[0], governing=None,
                              evaluated_combinations=0, combination_checks=[])
            else:
                column.update(status="NOT_APPLICABLE", reason=row.get("reason"))
            columns.append(column)
        result = {
            "schema": _AXIAL_RESULT.value, "check_id": CHECK,
            "numerical_rule": "TS500:7.7:AXIAL_COMPRESSION_MAX:COLUMN:2000R2018",
            "status": "BLOCKED", "combination_plan": plan, "gamma_c": None,
            "expected_column_count": len(targets), "completed_column_count": 0,
            "expected_member_combination_count": len(expected), "evaluated_member_combination_count": 0,
            "native_force_row_count": 0, "observed_exceedance_count": 0, "columns": columns,
            "column_status_counts": dict(sorted(Counter(row["status"] for row in columns).items())),
            "tbdy_seismic_axial_check": "DESIGN_COMBINATION_BASIS_UNVERIFIED",
            "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
        }

    evaluated = {row["element_id"]: row for row in result["columns"]}
    observed = {}
    duplicate = set()
    expected_keys = set(expected)
    for uid, row in evaluated.items():
        for check in row.get("combination_checks", ()):
            key = uid, check["combination"]
            if key in observed:
                duplicate.add(key)
            observed[key] = check
    if len(evaluated) != len(result["columns"]) or duplicate or set(observed) - expected_keys:
        blockers.append("COLUMN_AXIAL_RESULT_IDENTITY_CONFLICT")
    instances = []
    for uid, name in expected:
        member = evaluated.get(uid, {})
        check = observed.get((uid, name), {})
        values = (check.get("nd_kn"), check.get("ratio"))
        numeric = ((uid, name) not in duplicate and check.get("status") in {"WITHIN_LIMIT", "OUTSIDE_LIMIT"}
                   and all(type(value) in (float, int) and isfinite(value) for value in values))
        instances.append({
            "element_id": uid, "story": targets[uid].get("story"), "combination": name,
            "status": check["status"] if numeric else "NOT_PROVEN",
            "reason": None if numeric else (check.get("reason") or member.get("reason")
                                            or "REQUIRED_INSTANCE_RESULT_MISSING"),
        })
    evaluated_count = sum(item["status"] != "NOT_PROVEN" for item in instances)
    ledger = {
        "schema": "tbdy.next.axial-check-instance-ledger.v1", "check_id": CHECK,
        "method_version": stage.method_version, "input_sha256": input_sha,
        "combination_source": mode, "scope_complete": bool(census_proven and names_valid),
        "observed_column_count": len(targets), "requested_combination_count": len(expected_names),
        "expected_count": len(instances), "evaluated_count": evaluated_count,
        "not_proven_count": len(instances) - evaluated_count,
        "dependency_blockers": blockers, "instances": instances,
        "formal_compliance": "NOT_PROVEN",
    }
    return result, ledger


def _run_column_pmm(source: Mapping[str, Any], geometry: Mapping[str, Any] | None,
                    axial: Mapping[str, Any], axial_ledger: Mapping[str, Any],
                    *, target: str, input_sha: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    from .column_axial import _columns
    from .column_pmm import (
        bind_configured_output_cuts, bind_pmm_mesh_source, configured_output_station_minimums, evaluate_column_pmm,
    )

    stage = next(stage for stage in STAGES if stage.key == "column-pmm")
    feature = source["column_axial"]
    section_source = feature.get("pmm_section_source")
    blockers = _stage_input_blockers(stage, {
        "geometry": geometry, "column_axial": axial, "force_source": feature.get("force_source"),
        "pmm_section_source": section_source,
    })
    blockers.extend(axial_ledger["dependency_blockers"])
    if _PMM_SECTION.accepts(section_source) and (
        section_source.get("error") or section_source.get("units_before") != 6
        or section_source.get("units_after") != 6 or section_source.get("model_locked_before") is not True
        or section_source.get("model_locked_after") is not True
    ):
        blockers.append("PMM_SECTION_SOURCE_SESSION_UNVERIFIED")

    members = _columns(geometry) if _AXIAL_GEOMETRY.accepts(geometry) else axial["columns"]
    eligible = {row["element_id"]: row.get("story") for row in members if row.get("status") != "NOT_APPLICABLE"}
    member_ids = sorted(eligible) if target == "ALL" else [target]
    target_known = bool(member_ids) and (target == "ALL" or target in eligible)
    if not target_known:
        blockers.append("PMM_REQUESTED_COLUMN_POPULATION_UNAVAILABLE")
    plan = axial["combination_plan"]["combinations"]
    if not plan:
        blockers.append("PMM_REQUESTED_COMBINATION_POPULATION_UNAVAILABLE")
    blockers = sorted(set(blockers))

    mesh = bind_pmm_mesh_source(source, {uid: eligible.get(uid) for uid in member_ids})
    configured_cuts = bind_configured_output_cuts(source, mesh["members"])
    station_minimums = (configured_output_station_minimums(source, geometry, mesh_members=mesh["members"])
                        if _AXIAL_GEOMETRY.accepts(geometry) else {})
    pmm = (evaluate_column_pmm(source, geometry, axial, station_minimums=station_minimums,
                               mesh_members=mesh["members"], configured_cuts=configured_cuts) if not blockers else None)
    if pmm is not None and not _PMM_RESULT.accepts(pmm):
        raise ValueError("INVALID_STAGE_OUTPUT:column-pmm")
    recorded_members = ((pmm or {}).get("members") or ()) if target == "ALL" else ([pmm] if pmm else [])
    recorded_by_id = {item["member_id"]: {c["name"]: c for c in item["combinations"]} for item in recorded_members}
    verified_steps = {(entry["element_id"], entry["combination"]) for entry in axial_ledger["instances"]
                      if entry["status"] in {"WITHIN_LIMIT", "OUTSIDE_LIMIT"}}
    known_scope = axial_ledger["scope_complete"] and target_known and bool(plan)
    instances = []
    for uid in member_ids:
        for combo in plan:
            observed = recorded_by_id.get(uid, {}).get(combo["name"], {})
            configured = observed.get("configured_cut_coverage") or {}
            elements = observed.get("analysis_element_coverage") or {}
            census = ((uid, combo["name"]) in verified_steps and configured.get("exact_cut_census") is True
                      and elements.get("roster_bound") is True and elements.get("reason") is None)
            instances.append({
                "element_id": uid, "combination": combo["name"], "force_semantics": combo.get("force_semantics"),
                "execution_status": observed.get("status", "BLOCKED"), "formal_compliance": "NOT_PROVEN",
                "minimum_object_station_count": station_minimums.get(uid),
                "observed_object_station_count": observed.get("observed_object_station_count"),
                "analysis_element_coverage": observed.get("analysis_element_coverage"),
                "configured_cut_coverage": observed.get("configured_cut_coverage"),
                "independent_cut_census_proven": census,
                "section_rows_evaluated": observed.get("evaluated_station_count", 0),
                "reason": observed.get("reason") or (blockers[0] if blockers else
                    None if census else "INDEPENDENT_ANALYSIS_CUT_CENSUS_NOT_PROVEN"),
            })
    return pmm, {
        "schema": _PMM_SCOPE.value, "method_version": stage.method_version, "input_sha256": input_sha,
        "target_member_id": target, "expected_member_combination_count": len(instances),
        "numerically_complete_signed_pair_count": sum(i["execution_status"] == "NUMERICAL_COMPLETE" for i in instances),
        "known_member_combination_scope": known_scope,
        "analysis_mesh": mesh,
        "configured_output_cuts": configured_cuts,
        "independent_cut_census_proven": bool(known_scope and not blockers and instances
                                             and all(x["independent_cut_census_proven"] for x in instances)),
        "dependency_blockers": blockers, "instances": instances,
        "formal_compliance": "NOT_PROVEN",
    }


def run_source_pipeline(payload: Mapping[str, Any], *, case: str, run: ReceiptRun, input_sha: str,
                        suite: bool, catalog: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Execute the live-source stage sequence once; receipts are written in registry order."""
    from .pipeline_snapshot import SCHEMA, record_snapshot

    from .design_scenario import CALCULATION_BASES, POLICIES, selected_candidate_ledger, verify_archived_scenario
    from .design_dependencies import build_member_dependency_plan, build_revision_evidence, bind_joint_candidates

    _validate_dependency_contracts()
    scenario = verify_archived_scenario(run.root, payload)
    if scenario is None and any(payload.get(key) is not None for key in POLICIES):
        raise ValueError("DESIGN_SELECTION_REQUIRES_PREPARED_SCENARIO")
    if scenario is None and any(payload.get(key) is not None for key in CALCULATION_BASES):
        raise ValueError("CALCULATION_BASIS_REQUIRES_PREPARED_SCENARIO")
    out: dict[str, Any] = {
        "result": calculate_modal(payload, case=case, run=run, input_sha=input_sha, receipt_schema=SCHEMA),
    }
    geometry = extra = None
    if suite:
        geometry = evaluate_geometry_capture(payload.get("geometry_capture"))
        run.record("quick-geometry", geometry, input_sha256=input_sha)
        if "next_capture" in payload:
            extra = evaluate_next_capture(payload["next_capture"], payload.get("geometry_capture"))
            run.record("quick-extra", extra, input_sha256=input_sha)
    out.update(geometry=geometry, extra=extra)

    vs04 = vs04_numerics = vs04_readiness = vs04_pipeline = None
    if "analysis_sources" in payload:
        vs04 = review_analysis_sources(payload["analysis_sources"])
        run.record("vs04-schema", vs04, input_sha256=input_sha)
        vs04_numerics = evaluate_analysis_numerics(payload["analysis_sources"])
        run.record("vs04-numerics", vs04_numerics, input_sha256=input_sha)
        vs04_readiness = review_normative_readiness(payload["analysis_sources"])
        run.record("vs04-readiness", vs04_readiness, input_sha256=input_sha)
        if payload["analysis_sources"].get("pipeline_stage_required") is True:
            vs04_pipeline = evaluate_single_run_source_pipeline(payload)
            run.record("vs04-pipeline", vs04_pipeline, input_sha256=input_sha)
    out.update(vs04=vs04, vs04_numerics=vs04_numerics, vs04_readiness=vs04_readiness,
               vs04_pipeline=vs04_pipeline)

    story_drift = None
    if "vs05_delta_source" in payload or "vs05_delta_capture_error" in payload:
        from ..story_drift_binding import bind_story_drift
        story_drift = bind_story_drift(payload.get("vs05_delta_source"),
                                       capture_error=payload.get("vs05_delta_capture_error"))
        run.record("vs05-story-drift", story_drift, input_sha256=input_sha)
    analysis_setup = None
    analysis_setup_reconciliation = None
    if "vs04_basis_probe" in payload:
        from .analysis_setup import STAGE, bind_analysis_setup, project_analysis_setup_reconciliation
        analysis_setup = bind_analysis_setup(payload)
        run.record(STAGE, analysis_setup, input_sha256=input_sha)
        analysis_setup_reconciliation = project_analysis_setup_reconciliation(analysis_setup, payload)
    column_axial = column_pmm = column_gates = beam_r10 = r10_live = axial_ledger = pmm_scope = None
    pmm_target = None
    if "column_axial" in payload:
        from .column_axial import STAGE as AXIAL_STAGE

        column_axial, axial_ledger = _run_column_axial(payload, geometry, extra, analysis_setup, input_sha=input_sha)
        run.record(AXIAL_STAGE, column_axial, input_sha256=input_sha)
        feature = payload["column_axial"]
        request = feature.get("request") if isinstance(feature, Mapping) else None
        pmm_target = request.get("pmm_member") if isinstance(request, Mapping) else None
        if isinstance(pmm_target, str) and pmm_target:
            from .column_pmm import STAGE as PMM_STAGE

            column_pmm, pmm_scope = _run_column_pmm(
                payload, geometry, column_axial, axial_ledger, target=pmm_target, input_sha=input_sha,
            )
            if column_pmm is not None:
                archive_order = (analysis_setup_reconciliation or {}).get("archived_analysis_order")
                combinations = column_axial["combination_plan"]["combinations"]
                if archive_order and combinations and all(
                    row.get("case_names") and set(row["case_names"]) <= archive_order["solved_case_guids"].keys()
                    for row in combinations
                ):
                    for item in [column_pmm, *column_pmm.get("members", ())]:
                        item["analysis_order"] = archive_order["source_analysis_order"]
                        item["archived_solver_log_sha256"] = archive_order["solver_log_sha256"]
                run.record(PMM_STAGE, column_pmm, input_sha256=input_sha)
    mixed_components = None
    demand_sources = None
    if pmm_scope is not None:
        from .mixed_demands import spectral_component_evidence
        from .demand_sources import native_demand_source_evidence
        component_stage = next(s for s in STAGES if s.key == "mixed-demand-components")
        component_blockers = _stage_input_blockers(component_stage, {"column_axial": column_axial, "pmm_scope": pmm_scope})
        component_scope = {**pmm_scope, "dependency_blockers": sorted(set(
            pmm_scope.get("dependency_blockers", ()) + component_blockers))}
        mixed_components = spectral_component_evidence(payload, column_axial, component_scope, input_sha=input_sha)
        if mixed_components is not None and not _MIXED_COMPONENTS.accepts(mixed_components):
            raise ValueError("INVALID_STAGE_OUTPUT:mixed-demand-components")
        demand_sources = native_demand_source_evidence(payload, column_axial, component_scope, input_sha=input_sha)
        if not _DEMAND_SOURCE.accepts(demand_sources):
            raise ValueError("INVALID_STAGE_OUTPUT:native-demand-sources")
    design_dependencies = build_member_dependency_plan(payload, pmm_scope, input_sha=input_sha) if scenario else None
    if scenario is not None and not _DESIGN_SCOPE.accepts(design_dependencies):
        raise ValueError("INVALID_STAGE_OUTPUT:design-dependencies")
    design_allowed = design_dependencies is None or design_dependencies["candidate_execution_allowed"]
    selected_cages = {}
    if axial_ledger is not None and not axial_ledger["dependency_blockers"]:
        from .column_live_gates import project_column_gates

        if design_allowed and (pmm_target is None or (column_pmm is not None and column_pmm["evaluated_station_count"] > 0)):
            from .beam_r10_live import project_beam_r10_live
            from .column_r10_live import project_column_r10_live

            beam_r10 = project_beam_r10_live(payload, geometry, column_axial, column_pmm, extra)
            r10_live = project_column_r10_live(
                payload, geometry, column_axial, column_pmm, extra, beam_live=beam_r10,
                selected_cages_out=selected_cages, pmm_scope=pmm_scope, mixed_components=mixed_components, input_sha=input_sha,
                **({"dependency_plan": design_dependencies} if scenario else {}),
            )
            if scenario and r10_live is not None:
                design_dependencies = r10_live["member_dependencies"]
        column_gates = project_column_gates(
            payload, column_axial, column_pmm,
            local_axis_angle_deg=(r10_live or {}).get("local_axis_angle_deg"),
        )

    if scenario is not None and r10_live is None:
        design_dependencies = bind_joint_candidates(design_dependencies, {}, {}, beam_r10)
    candidate_ledger = None
    if scenario is not None and payload.get("column_selection") is not None:
        candidate_ledger = selected_candidate_ledger(pmm_scope or {}, selected_cages, r10_live, input_sha=input_sha)
        ready = [r["member_id"] for r in candidate_ledger["rows"] if r["status"] == "SAME_RUN_CANDIDATE_BOUND"]
        if candidate_ledger["unexpected_column_ids"]:
            ready = []
            design_dependencies["blockers"].append("DESIGN_UNEXPECTED_SELECTED_CAGE")
        design_dependencies["r08_ready_member_ids"] = ready
        design_allowed = bool(ready)
        design_dependencies["selected_candidates"] = candidate_ledger
        design_dependencies["downstream_execution_allowed"] = design_allowed

    physical_scope = None
    if "vs05_delta_source" in payload:
        from ..physical_story_scope import review_physical_story_scope

        physical_scope = review_physical_story_scope(payload["vs05_delta_source"])
    declared_second_order = r08_second_order = None
    if "r08_second_order_source" in payload or "r08_second_order_capture_error" in payload:
        from ..story_second_order import bind_story_second_order, scope_story_second_order

        declared_second_order = bind_story_second_order(
            payload.get("r08_second_order_source"),
            capture_error=payload.get("r08_second_order_capture_error"))
        run.record("r08-second-order", declared_second_order, input_sha256=input_sha)
        r08_second_order = scope_story_second_order(
            declared_second_order, payload.get("r08_second_order_source"), payload.get("vs05_delta_source"), physical_scope,
        )
    r08_local_slenderness = None
    r14_closure = None
    if pmm_scope is not None:
        stage = next(stage for stage in STAGES if stage.key == "column-r08-local")
        r08_blockers = _stage_input_blockers(stage, {
            "geometry": geometry, "column_axial": column_axial, "column_pmm": column_pmm, "pmm_scope": pmm_scope,
        })
        if column_pmm is not None and not column_pmm["evaluated_station_count"]:
            r08_blockers.append("NO_EVALUATED_SIGNED_PMM_STATIONS")
        if not design_allowed and design_dependencies is not None:
            r08_blockers.extend(design_dependencies["blockers"] or ["DESIGN_NO_ELIGIBLE_MEMBER_CANDIDATES"])
        pmm_scope["local_second_order_dependency_blockers"] = r08_blockers
        if not r08_blockers:
            from .column_r08_local_live import project_column_r08_local_live

            r08_local_slenderness = project_column_r08_local_live(
                payload, geometry, column_axial, column_pmm, r08_second_order, r10_live=r10_live,
                selected_cages=selected_cages,
                **({"dependency_plan": design_dependencies} if scenario else {}),
            )
            if not all(contract.accepts(r08_local_slenderness) for contract in stage.produces):
                raise ValueError("INVALID_STAGE_OUTPUT:column-r08-local")
    alpha_iteration = None
    if scenario is not None and design_dependencies is not None:
        from .alpha_iteration import run_alpha_design_iteration
        alpha_state, candidate_ledger, alpha_iteration = run_alpha_design_iteration(
            source=payload, geometry=geometry, axial=column_axial, pmm=column_pmm, extra=extra,
            scope=pmm_scope or {}, dependencies=design_dependencies, r10=r10_live,
            r08=r08_local_slenderness, cages=selected_cages, beam=beam_r10,
            global_pdelta=r08_second_order, input_sha=input_sha, mixed_components=mixed_components)
        if not _ALPHA_ITERATION.accepts(alpha_iteration):
            raise ValueError("INVALID_STAGE_OUTPUT:alpha-feedback")
        r10_live, r08_local_slenderness = alpha_state["r10"], alpha_state["r08"]
        selected_cages, design_dependencies = alpha_state["cages"], alpha_state["dependencies"]
    dependency_revisions = None
    if scenario is not None:
        dependency_revisions = build_revision_evidence(
            design_dependencies, candidate_ledger, r10_live, r08_local_slenderness, input_sha=input_sha,
        )
        if not _DESIGN_REVISIONS.accepts(dependency_revisions):
            raise ValueError("INVALID_STAGE_OUTPUT:design-revisions")
    if column_pmm is not None:
        from .column_r14_closure import project_column_r14_and_r15_closure

        r14_closure = project_column_r14_and_r15_closure(
            geometry=geometry, axial=column_axial, pmm=column_pmm,
            r08_second_order=r08_second_order, r08_local=r08_local_slenderness,
            beam_r10=beam_r10, r10_live=r10_live,
            analysis_setup_reconciliation=analysis_setup_reconciliation,
            pmm_cut_census_proven=pmm_scope["independent_cut_census_proven"],
            **({"dependency_evidence": dependency_revisions} if scenario else {}),
        )
    out.update(story_drift=story_drift, analysis_setup=analysis_setup,
               analysis_setup_reconciliation=analysis_setup_reconciliation, column_axial=column_axial,
               column_pmm=column_pmm, column_gates=column_gates, beam_r10=beam_r10, r10_live=r10_live,
               r08_second_order=r08_second_order, r08_local_slenderness=r08_local_slenderness,
               r14_closure=r14_closure)
    out["report_evidence"] = (derive_report_evidence(
        payload, {**out, "r08_second_order": declared_second_order}, catalog=catalog,
        physical_scope=physical_scope, scoped_second_order=r08_second_order,
    ) if suite else {})
    if axial_ledger is not None:
        out["report_evidence"]["column_axial_expected_instances"] = axial_ledger
    if pmm_scope is not None:
        out["report_evidence"]["column_pmm_expected_instances"] = pmm_scope
    if mixed_components is not None:
        out["report_evidence"]["mixed_demand_components"] = mixed_components
    if demand_sources is not None:
        out["report_evidence"]["native_demand_sources"] = demand_sources
    if scenario is not None:
        out["report_evidence"]["design_scenario"] = scenario
        out["report_evidence"]["design_dependencies"] = design_dependencies
        out["report_evidence"]["design_revisions"] = dependency_revisions
        out["report_evidence"]["alpha_iteration"] = alpha_iteration
        if r14_closure is not None:
            # The report projects this exact recorded block, without a second calculation.
            r14_closure["design_scenario"] = scenario
            r14_closure["design_dependencies"] = design_dependencies
            r14_closure["design_revisions"] = dependency_revisions
            r14_closure["alpha_iteration"] = alpha_iteration
    snapshot = record_snapshot(run, input_sha=input_sha, results=out, registry=stage_registry())
    meta = payload.get("capture_metadata") or {}
    run.record("live-capture", {
        "status": "SOURCE_CAPTURED", "source_mode": "LIVE_ETABS", "case": case,
        "source_rows": payload["table"]["row_count"],
        "display_selection_restored": bool(meta.get("display_selection_restored")),
        "engineering_release": "NOT_READY", "engine_snapshot": snapshot,
    }, input_sha256=input_sha)
    out["engine_snapshot"] = snapshot
    return out


class EnginePipelineRunner:
    """Authoritative single pipeline runner integrated with the 94-node candidate DAG."""

    def __init__(self, catalog: Mapping[str, Any] | None = None) -> None:
        from ..compiled_dag import CANDIDATE_CATALOG_PATH, read_candidate_catalog

        self.stages = STAGES
        self.catalog = catalog or read_candidate_catalog(CANDIDATE_CATALOG_PATH)

    def registry(self) -> list[dict[str, Any]]:
        return stage_registry()

    def coverage(self) -> dict[str, Any]:
        return dag_coverage(self.catalog)

    def run(self, payload: Mapping[str, Any], *, case: str, run: ReceiptRun,
            input_sha: str, suite: bool) -> dict[str, Any]:
        return run_source_pipeline(payload, case=case, run=run, input_sha=input_sha, suite=suite, catalog=self.catalog)
