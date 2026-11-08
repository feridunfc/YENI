"""VS05 — deterministic candidate Engineering DAG compiler and FCR accountant.

This module implements the *architectural skeleton*, not 94 production
engineering formula kernels. All imported R1-C nodes have DENIED execution
authority. Profiles, case/combination books and expected instances are
untrusted until independently approved. No bool, status string, or caller-
supplied "PASS" can grant execution authority.

The boundary is:
  candidate catalog -> deterministic topological graph -> frozen candidate
  expected CheckInstance denominator -> fail-closed FCR / immutable result.

Promoting this scaffold to an executable normative plan requires a separate
trusted approval-verification facility; intentionally not provided here.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

CATALOG_SCHEMA = "tbdy.next.vs05.candidate-engineering-dag.v1"
PLAN_SCHEMA = "tbdy.next.vs05.candidate-execution-plan.v1"
FCR_SCHEMA = "tbdy.next.vs05.candidate-fcr.v1"
CHECK_TYPES = frozenset(("REGULATORY_CHECK", "DESIGN_CHECK"))
NODE_TYPES = frozenset(("SOURCE_GATE", "DERIVATION", *CHECK_TYPES))
EXPECTED_TYPE_COUNTS = {
    "SOURCE_GATE": 16, "DERIVATION": 10,
    "REGULATORY_CHECK": 32, "DESIGN_CHECK": 36,
}
OUTCOME_STATES = frozenset((
    "PASS", "FAIL", "NOT_PROVEN", "NOT_APPLICABLE",
    "REANALYSIS_REQUIRED",
))


class CompilationRejected(ValueError):
    pass


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _canonical_sha(value: Mapping[str, Any]) -> str:
    return sha256(canonical_json(value)).hexdigest()


def _identifier(value: Any, name: str) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 160):
        raise CompilationRejected(name + ": INVALID_IDENTITY")
    return value


def _catalog_nodes(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(catalog, Mapping) or catalog.get("schema") != CATALOG_SCHEMA:
        raise CompilationRejected("UNRECOGNIZED_CANDIDATE_CATALOG_SCHEMA")
    if (catalog.get("status") != "STATIC_RESEARCH_CANDIDATE"
            or catalog.get("authority") != "NONE"
            or catalog.get("node_count") != 94
            or catalog.get("edge_count") != 140):
        raise CompilationRejected("CATALOG_AUTHORITY_OR_EXPECTED_SIZE_CHANGED")
    nodes = catalog.get("nodes")
    if not isinstance(nodes, list) or len(nodes) != 94:
        raise CompilationRejected("CATALOG_NODE_COUNT_NOT_94")
    if not all(isinstance(n, dict) for n in nodes):
        raise CompilationRejected("NODE_RECORD_NOT_OBJECT")
    ids = [_identifier(n.get("node_id"), "node_id") for n in nodes]
    if len(set(ids)) != 94:
        raise CompilationRejected("DUPLICATE_CATALOG_NODE")
    if any(n["node_id"] != n["node_id"].upper()
           or not set(n["node_id"]).issubset(set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"))
           for n in nodes):
        raise CompilationRejected("INVALID_STATIC_NODE_ID")
    if any(n.get("node_type") not in NODE_TYPES or
           n.get("execution_authority") != "DENIED" or
           n.get("compliance_status") != "NOT_PROVEN"
           for n in nodes):
        raise CompilationRejected("CATALOG_NODE_AUTHORITY_MUST_BE_DENIED")
    counts = dict(Counter(n["node_type"] for n in nodes))
    if counts != EXPECTED_TYPE_COUNTS:
        raise CompilationRejected("CATALOG_NODE_TYPE_DENOMINATOR_CHANGED")
    edges = []
    for node in nodes:
        deps = node.get("depends_on")
        if not isinstance(deps, list):
            raise CompilationRejected("NONLIST_NODE_DEPENDENCIES")
        if len(deps) != len(set(deps)) or node["node_id"] in deps:
            raise CompilationRejected("DUPLICATE_OR_SELF_DEPENDENCY")
        if any(dep not in ids for dep in deps):
            raise CompilationRejected("UNKNOWN_DEPENDENCY_PRODUCER")
        edges.extend((dep, node["node_id"]) for dep in deps)
    if len(edges) != 140 or len(set(edges)) != 140:
        raise CompilationRejected("CATALOG_DEPENDENCY_COUNT_NOT_140")
    return nodes


def validate_candidate_catalog(catalog: Mapping[str, Any]) -> dict[str, Any]:
    nodes = _catalog_nodes(catalog)
    dependents = {n["node_id"]: [] for n in nodes}
    remaining = {n["node_id"]: len(n["depends_on"]) for n in nodes}
    for node in nodes:
        for dep in node["depends_on"]:
            dependents[dep].append(node["node_id"])
    waves = []
    ready = sorted(nid for nid, degree in remaining.items() if degree == 0)
    visited = set()
    while ready:
        waves.append(ready)
        for node_id in ready:
            if node_id in visited:
                raise CompilationRejected("NODE_SCHEDULE_DUPLICATE")
            visited.add(node_id)
        next_ready = []
        for node_id in ready:
            for follower in dependents[node_id]:
                remaining[follower] -= 1
                if remaining[follower] == 0:
                    next_ready.append(follower)
        ready = sorted(next_ready)
    if len(visited) != 94:
        raise CompilationRejected("CYCLIC_DEPENDENCIES_IN_CANDIDATE_DAG")
    return {
        "schema": "tbdy.next.vs05.candidate-dag-validation.v1",
        "catalog_sha256": _canonical_sha(catalog),
        "candidate_nodes": 94,
        "candidate_dependency_edges": 140,
        "source_gate_count": 16, "derivation_count": 10,
        "regulatory_candidate_count": 32,
        "design_candidate_count": 36,
        "candidate_check_node_count": 68,
        "topological_waves": waves,
        "execution_authorized_nodes": 0,
        "formal_compliance": "NOT_PROVEN",
    }


def read_candidate_catalog(path: Path) -> dict[str, Any]:
    """Read only the explicitly supplied research artifact, never remote code."""
    path = Path(path)
    if (not path.is_file() or path.is_symlink() or
            path.stat().st_size > 1024 * 1024):
        raise CompilationRejected("CATALOG_PATH_INVALID")
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise CompilationRejected("INVALID_CATALOG_UTF8_JSON") from exc
    validate_candidate_catalog(catalog)
    return catalog


def _declaration(value: Any, kind: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise CompilationRejected(kind + ": INVALID_RECORD")
    declared = dict(value)
    if declared.get("schema") != f"tbdy.next.vs05.{kind}.candidate.v1":
        raise CompilationRejected(kind + ": UNKNOWN_SCHEMA")
    for key in (("profile_id", "version", "source_model_sha256")
                if kind == "model_profile" else
                ("book_id", "version", "combo_definition_sha256")):
        _identifier(declared.get(key), kind + "." + key)
    # A self-declared APPROVED field must never be trusted as approval.
    return declared


class RegulatoryCompiler:
    """Explicit candidate-only plan builder.

    No approval-granting method is supplied. 'approved_*' declarations
    belong to a future independently verified authorized pipeline.
    """

    def __init__(self, catalog: Mapping[str, Any]):
        self.catalog = json.loads(canonical_json(catalog))
        self.graph = validate_candidate_catalog(self.catalog)
        self.nodes = {n["node_id"]: n for n in self.catalog["nodes"]}

    def compile_candidate(
        self, *,
        model_profile: Mapping[str, Any] | None,
        combo_book: Mapping[str, Any] | None,
        expected_instances: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        profile = _declaration(model_profile, "model_profile")
        book = _declaration(combo_book, "combo_book")
        if not isinstance(expected_instances, list):
            raise CompilationRejected("EXPECTED_INSTANCE_DENOMINATOR_NOT_LIST")
        instances = []
        for item in expected_instances:
            if not isinstance(item, Mapping):
                raise CompilationRejected("CHECK_INSTANCE_NOT_OBJECT")
            check_id = _identifier(item.get("check_instance_id"), "check_instance_id")
            node_id = _identifier(item.get("node_id"), "node_id")
            subject = _identifier(item.get("subject_id"), "subject_id")
            grain = _identifier(item.get("grain"), "grain")
            if node_id not in self.nodes or self.nodes[node_id]["node_type"] not in CHECK_TYPES:
                raise CompilationRejected("INSTANCE_NOT_OWNED_BY_FORMAL_CHECK_NODE")
            if check_id != node_id + ":" + subject:
                raise CompilationRejected("INSTANCE_ID_NOT_CANONICAL_NODE_SUBJECT")
            if grain not in ("GLOBAL_DIRECTION", "STORY_DIRECTION", "PHYSICAL_MEMBER",
                             "JOINT", "FOUNDATION", "CANDIDATE_NODE"):
                raise CompilationRejected("UNRECOGNIZED_EXPECTED_INSTANCE_GRAIN")
            instances.append({"check_instance_id":check_id, "node_id":node_id,
                              "subject_id":subject,"grain":grain,
                              "execution_authority":"DENIED",
                              "formal_compliance":"NOT_PROVEN"})
        keys = [item["check_instance_id"] for item in instances]
        if len(keys) != len(set(keys)):
            raise CompilationRejected("DUPLICATE_EXPECTED_CHECK_INSTANCE")
        # Freeze IDs in a deterministic order: cannot silently drop a
        # failed instance or shrink denominator by UI filter/report leaf.
        instances.sort(key=lambda item:item["check_instance_id"])
        frozen = {
            "schema": PLAN_SCHEMA,
            "source_catalog_sha256": self.graph["catalog_sha256"],
            "status":"CANDIDATE_PLAN_UNAUTHORIZED",
            "execution_authority":"DENIED",
            "model_profile_declaration_sha256": (
                _canonical_sha(profile) if profile else None),
            "combo_book_declaration_sha256": (
                _canonical_sha(book) if book else None),
            "model_profile_approval_proven": False,
            "combo_book_approval_proven": False,
            "analysis_generation_proven": False,
            "node_waves": self.graph["topological_waves"],
            "catalog_candidate_check_node_count": 68,
            "expected_check_instance_count": len(instances),
            "expected_check_instances":instances,
            "normative_execution_authorized":False,
            "engineering_release":"NOT_READY",
        }
        return {**frozen, "plan_sha256": _canonical_sha(frozen)}


def assess_candidate_plan(plan: Mapping[str, Any],
                          outcomes: list[Mapping[str, Any]]) -> dict[str, Any]:
    """FCR: reconcile complete expected denominator without inventing PASS.

    Every missing instance becomes explicit NOT_PROVEN. Extra, duplicate or
    invalid outcome IDs cause rejection rather than denominator reduction.
    Even caller-submitted PASS is not executable-authorized in candidate
    plans, so is reported as NOT_PROVEN with an explicit denial reason.
    """
    if not isinstance(plan, Mapping) or plan.get("schema") != PLAN_SCHEMA:
        raise CompilationRejected("PLAN_SCHEMA_INVALID")
    unsigned = dict(plan)
    hash_value = unsigned.pop("plan_sha256", None)
    if hash_value != _canonical_sha(unsigned):
        raise CompilationRejected("PLAN_CONTENT_HASH_MISMATCH")
    if (plan.get("status") != "CANDIDATE_PLAN_UNAUTHORIZED"
            or plan.get("execution_authority") != "DENIED"
            or plan.get("normative_execution_authorized") is not False
            or plan.get("model_profile_approval_proven") is not False
            or plan.get("combo_book_approval_proven") is not False
            or plan.get("analysis_generation_proven") is not False):
        raise CompilationRejected("UNTRUSTED_PLAN_EXECUTION_AUTHORITY")
    expected = plan.get("expected_check_instances")
    if not isinstance(expected, list) or len(expected) != plan.get(
            "expected_check_instance_count"):
        raise CompilationRejected("FROZEN_EXPECTED_DENOMINATOR_INVALID")
    ids = [x["check_instance_id"] for x in expected]
    if len(set(ids)) != len(ids):
        raise CompilationRejected("FROZEN_EXPECTED_IDS_DUPLICATED")
    if not isinstance(outcomes, list):
        raise CompilationRejected("OUTCOME_POPULATION_NOT_LIST")
    seen = set()
    source_outcomes = {}
    for outcome in outcomes:
        if not isinstance(outcome, Mapping):
            raise CompilationRejected("OUTCOME_NOT_OBJECT")
        key = _identifier(outcome.get("check_instance_id"), "outcome_id")
        if key in seen:
            raise CompilationRejected("DUPLICATE_OUTCOME_ID")
        if key not in ids:
            raise CompilationRejected("UNEXPECTED_OR_ORPHAN_CHECK_RESULT")
        if outcome.get("status") not in OUTCOME_STATES:
            raise CompilationRejected("INVALID_OUTCOME_STATUS")
        seen.add(key)
        source_outcomes[key] = outcome
    final = []
    for expected_instance in expected:
        key = expected_instance["check_instance_id"]
        supplied = source_outcomes.get(key)
        reason = ("EXPECTED_RESULT_MISSING" if supplied is None
                  else "EXECUTION_AUTHORITY_DENIED_FOR_CANDIDATE_DAG")
        final.append({
            "check_instance_id":key,
            "node_id":expected_instance["node_id"],
            "subject_id":expected_instance["subject_id"],
            "grain":expected_instance["grain"],
            "source_outcome_observed":supplied is not None,
            "source_outcome_status":supplied.get("status") if supplied else None,
            "status":"NOT_PROVEN",
            "applicability":"NOT_REVIEWED",
            "execution":"BLOCKED",
            "formal_compliance":"NOT_PROVEN",
            "reason_codes":[reason],
        })
    result = {
        "schema":FCR_SCHEMA,
        "status":"CANDIDATE_ASSESSMENT_ONLY",
        "plan_sha256":hash_value,
        "expected_count":len(expected),
        "submitted_count":len(outcomes),
        "missing_count":len(expected)-len(outcomes),
        "reconciled_count":len(final),
        "pass_count":0, "fail_count":0,
        "not_proven_count":len(final),
        "expected_check_instance_ids":ids,
        "outcomes":final,
        "engineering_release":"NOT_READY",
        "formal_compliance":"NOT_PROVEN",
    }
    return {**result,"fcr_sha256":_canonical_sha(result)}
