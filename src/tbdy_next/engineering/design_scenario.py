"""Offline design requests and dependency evidence; no engineering formulas.

A scenario changes selection policies and explicit calculation assumptions. The original
capture is retained byte-for-byte as parent.source, never edited in place.
These are algorithm-selected reference candidates, not engineer approvals.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from ..column_engine.native_archive import decode
from ..history import _MAX_SOURCE_BYTES
from .rebar_selection import (
    DEFAULT_BEAM_SELECTION_POLICY, DEFAULT_COLUMN_SELECTION_POLICY,
    normalize_beam_selection_policy, normalize_column_selection_policy,
)

SCHEMA = "tbdy.next.offline-design-scenario.v1"
LINEAGE = "tbdy.next.design-scenario-lineage.v1"
LINEAGE_WITH_BASIS = "tbdy.next.design-scenario-lineage.v2"
PARENT_FILE = "parent.source"
POLICIES = ("beam_selection", "column_selection")
CALCULATION_BASES = ("second_order_basis", "analysis_basis")


@dataclass(frozen=True)
class PreparedPipelineSource:
    """Validated bytes and original parent for the existing pipeline adapters."""

    raw: bytes
    payload: dict[str, Any]
    parent_raw: bytes | None

    def archive_parent(self, directory: Path) -> None:
        if self.parent_raw is not None:
            with (directory / PARENT_FILE).open("xb") as parent:
                parent.write(self.parent_raw)


def _bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_bytes(value)).hexdigest()


def _source_data(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k not in (*POLICIES, *CALCULATION_BASES, "design_scenario")}


def _calculation_basis(key: str, value: Any, source_data_sha256: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if key == "second_order_basis":
        from .second_order_basis import normalize_second_order_basis
        return normalize_second_order_basis(value, source_data_sha256=source_data_sha256)
    from .analysis_setup import normalize_analysis_basis
    return normalize_analysis_basis(value, source_data_sha256=source_data_sha256)


def _policy(raw: Any, kind: str) -> dict[str, Any] | None:
    if raw is None:
        return None  # Explicitly no selection; never silently enable a default.
    defaults = DEFAULT_BEAM_SELECTION_POLICY if kind == "beam_selection" else DEFAULT_COLUMN_SELECTION_POLICY
    if raw != "default":
        if not isinstance(raw, Mapping) or set(raw) - set(defaults):
            raise ValueError("SCENARIO_UNKNOWN_POLICY_FIELD:" + kind)
        for key, value in raw.items():
            expected = defaults[key]
            if isinstance(expected, dict):
                if not isinstance(value, Mapping) or set(value) - set(expected):
                    raise ValueError("SCENARIO_UNKNOWN_POLICY_FIELD:" + kind + ":" + key)
            elif isinstance(expected, bool) and type(value) is not bool:
                raise ValueError("SCENARIO_BOOLEAN_REQUIRED:" + kind + ":" + key)
            elif key in ("schema", "selection_mode") and value != expected:
                raise ValueError("SCENARIO_UNSUPPORTED_POLICY:" + kind + ":" + key)
    normalize = normalize_beam_selection_policy if kind == "beam_selection" else normalize_column_selection_policy
    return normalize(raw)


def normalize_selection_overrides(overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Validate requested policy fields before either adapter starts work."""
    if not isinstance(overrides, Mapping) or set(overrides) - set(POLICIES):
        raise ValueError("SCENARIO_SELECTION_FIELDS_INVALID")
    return {key: _policy(value, key) for key, value in overrides.items()}


def create_design_scenario(parent_raw: bytes, request: Mapping[str, Any]) -> bytes:
    """Derive a new input without altering any native source or request scope."""
    required = {"schema", "scenario_id", "parent_input_sha256", *POLICIES}
    if (not isinstance(request, Mapping) or not required <= set(request)
            or set(request) - required - set(CALCULATION_BASES) or request["schema"] != SCHEMA):
        raise ValueError("SCENARIO_REQUEST_SCHEMA_INVALID")
    name = request["scenario_id"]
    if not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", name) is None:
        raise ValueError("SCENARIO_ID_INVALID")
    parent_sha = sha256(parent_raw).hexdigest()
    if request["parent_input_sha256"] != parent_sha:
        raise ValueError("SCENARIO_PARENT_HASH_MISMATCH")
    parent = decode(parent_raw)
    if not isinstance(parent, dict) or parent.get("source_mode") != "LIVE_ETABS":
        raise ValueError("SCENARIO_ARCHIVED_LIVE_SOURCE_REQUIRED")
    if "design_scenario" in parent:
        raise ValueError("SCENARIO_NESTING_NOT_SUPPORTED_USE_ORIGINAL_CAPTURE")
    if any(parent.get(key) is not None for key in CALCULATION_BASES):
        raise ValueError("SCENARIO_NATIVE_PARENT_CONTAINS_UNBOUND_CALCULATION_BASIS")
    feature = parent.get("column_axial")
    column_request = feature.get("request") if isinstance(feature, Mapping) else None
    if not isinstance(column_request, Mapping) or not column_request.get("pmm_member"):
        raise ValueError("SCENARIO_PMM_REQUEST_REQUIRED")
    policies = {key: _policy(request[key], key) for key in POLICIES}
    if all(value is None for value in policies.values()):
        raise ValueError("SCENARIO_SELECTION_REQUIRED")
    native_sha = _digest(_source_data(parent))
    bases = {key: _calculation_basis(key, request[key], native_sha)
             for key in CALCULATION_BASES if key in request and request[key] is not None}
    result = deepcopy(parent)
    for key, value in policies.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = value
    result.update(bases)
    lineage = {
        "schema": LINEAGE_WITH_BASIS if bases else LINEAGE, "scenario_id": name, "parent_input_sha256": parent_sha,
        "source_data_sha256": native_sha, "policies": policies,
        "selection_role": "ALGORITHM_SELECTED_CANDIDATE", "engineering_approval": "NOT_GRANTED",
        **({"calculation_bases": bases} if bases else {}),
    }
    result["design_scenario"] = {**lineage, "scenario_sha256": _digest(lineage)}
    return _bytes(result)


def validate_design_scenario(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Validate the self-contained scenario binding before any calculation."""
    if "design_scenario" not in payload:
        return None
    item = payload["design_scenario"]
    keys = {"schema", "scenario_id", "parent_input_sha256", "source_data_sha256",
            "policies", "selection_role", "engineering_approval", "scenario_sha256"}
    if isinstance(item, Mapping) and item.get("schema") == LINEAGE_WITH_BASIS:
        keys.add("calculation_bases")
    if (not isinstance(item, Mapping) or set(item) != keys or item["schema"] not in {LINEAGE, LINEAGE_WITH_BASIS}
            or item["selection_role"] != "ALGORITHM_SELECTED_CANDIDATE"
            or item["engineering_approval"] != "NOT_GRANTED"):
        raise ValueError("SCENARIO_LINEAGE_INVALID")
    if (not isinstance(item["scenario_id"], str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", item["scenario_id"]) is None
            or any(not isinstance(item[k], str) or re.fullmatch(r"[0-9a-f]{64}", item[k]) is None
                   for k in ("parent_input_sha256", "source_data_sha256", "scenario_sha256"))):
        raise ValueError("SCENARIO_ID_OR_HASH_INVALID")
    if not isinstance(item["policies"], Mapping) or set(item["policies"]) != set(POLICIES):
        raise ValueError("SCENARIO_POLICIES_INVALID")
    bases = item.get("calculation_bases", {})
    if (not isinstance(bases, Mapping) or set(bases) - set(CALCULATION_BASES)
            or (item["schema"] == LINEAGE_WITH_BASIS and not bases)
            or bases != {key: payload[key] for key in CALCULATION_BASES if payload.get(key) is not None}):
        raise ValueError("SCENARIO_CALCULATION_BASIS_CHANGED")
    for key, value in bases.items():
        if _calculation_basis(key, value, item["source_data_sha256"]) != value:
            raise ValueError("SCENARIO_CALCULATION_BASIS_NOT_NORMALIZED")
    if (item["scenario_sha256"] != _digest({k: v for k, v in item.items() if k != "scenario_sha256"})
            or item["source_data_sha256"] != _digest(_source_data(payload))
            or item["policies"] != {k: payload.get(k) for k in POLICIES}):
        raise ValueError("SCENARIO_SOURCE_OR_POLICY_CHANGED")
    for key in POLICIES:
        if _policy(item["policies"][key], key) != item["policies"][key]:
            raise ValueError("SCENARIO_POLICY_NOT_NORMALIZED")
    return dict(item)


def verify_parent(payload: Mapping[str, Any], parent_raw: bytes) -> None:
    item = validate_design_scenario(payload)
    if item is None:
        raise ValueError("SCENARIO_LINEAGE_REQUIRED")
    if sha256(parent_raw).hexdigest() != item["parent_input_sha256"]:
        raise ValueError("SCENARIO_PARENT_HASH_MISMATCH")
    parent = decode(parent_raw)
    if (not isinstance(parent, dict) or parent.get("source_mode") != "LIVE_ETABS" or "design_scenario" in parent
            or any(parent.get(key) is not None for key in CALCULATION_BASES)
            or _digest(_source_data(parent)) != item["source_data_sha256"]):
        raise ValueError("SCENARIO_NATIVE_SOURCE_CHANGED")


def verify_archived_scenario(directory: Path, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    item = validate_design_scenario(payload)
    if item is not None:
        _read_verified_parent(directory, payload)
    return item


def _read_verified_parent(directory: Path | None, payload: Mapping[str, Any]) -> bytes:
    if directory is None:
        raise ValueError("SCENARIO_PARENT_SOURCE_MISSING_OR_UNSAFE")
    parent = directory / PARENT_FILE
    if parent.is_symlink() or not parent.is_file() or not 0 < parent.stat().st_size <= _MAX_SOURCE_BYTES:
        raise ValueError("SCENARIO_PARENT_SOURCE_MISSING_OR_UNSAFE")
    raw = parent.read_bytes()
    verify_parent(payload, raw)
    return raw


def prepare_pipeline_source(
    source_raw: bytes,
    *,
    source_directory: Path | None = None,
    request: Mapping[str, Any] | None = None,
    selection_overrides: Mapping[str, Any] | None = None,
) -> PreparedPipelineSource:
    """Prepare replay or selection identically for Web and CLI.

    Existing scenarios must pass lineage and original-parent verification before
    replay or policy revision. Revisions are siblings derived from those original
    bytes, not nested scenarios. Omitted policies inherit the selected scenario's
    policy; explicit null disables that selection. Embedded legacy policies also
    create a scenario for a new calculation. No native source is rewritten.
    """
    if not 0 < len(source_raw) <= _MAX_SOURCE_BYTES:
        raise ValueError("SCENARIO_SOURCE_EXCEEDS_ARCHIVE_LIMIT")
    if request is not None and selection_overrides is not None:
        raise ValueError("SCENARIO_AND_SELECTION_FLAGS_ARE_EXCLUSIVE")
    payload = decode(source_raw)
    if not isinstance(payload, dict) or payload.get("source_mode") != "LIVE_ETABS":
        raise ValueError("LIVE_ETABS_ARCHIVED_SOURCE_REQUIRED")
    scenario = validate_design_scenario(payload)
    if scenario is None and any(payload.get(key) is not None for key in CALCULATION_BASES):
        raise ValueError("CALCULATION_BASIS_REQUIRES_PREPARED_SCENARIO")
    parent_raw = _read_verified_parent(source_directory, payload) if scenario is not None else None
    if (scenario is None and request is None and selection_overrides is None
            and any(payload.get(key) is not None for key in POLICIES)):
        # Historical input bytes remain the parent. A fresh selection must use
        # the same required member/cut dependencies as an explicit request.
        selection_overrides = {key: payload.get(key) for key in POLICIES}
    if selection_overrides is not None:
        overrides = normalize_selection_overrides(selection_overrides)
        parent = parent_raw if parent_raw is not None else source_raw
        request = {
            "schema": SCHEMA,
            "scenario_id": scenario["scenario_id"] if scenario is not None else "selection",
            "parent_input_sha256": sha256(parent).hexdigest(),
            **{key: overrides[key] if key in overrides else payload.get(key) for key in POLICIES},
            **{key: payload[key] for key in CALCULATION_BASES if payload.get(key) is not None},
        }
    raw = source_raw
    if request is not None:
        parent_raw = parent_raw if parent_raw is not None else source_raw
        raw = create_design_scenario(parent_raw, request)
        payload = decode(raw)
    if len(raw) > _MAX_SOURCE_BYTES:
        raise ValueError("SCENARIO_SOURCE_EXCEEDS_ARCHIVE_LIMIT")
    return PreparedPipelineSource(raw, payload, parent_raw)


def design_dependency_ledger(scope: Mapping[str, Any] | None, *, input_sha: str) -> dict[str, Any]:
    """Conservative cohort gate over the existing PMM ledger, not another solver.

Shared joints make partial candidate cohorts unsafe until dependency scheduling
is extended to those joints. A blocked required pair therefore stops this run's
linked candidate design cohort, while upstream/source results remain visible.
Unsigned envelopes with verified subset coverage remain reference-only inputs.
"""
    scope = scope or {}
    instances = scope.get("instances") or []
    blockers = list(scope.get("dependency_blockers") or ())
    if (scope.get("schema") != "tbdy.next.column-pmm-expected-instances.v1"
            or scope.get("input_sha256") != input_sha
            or scope.get("known_member_combination_scope") is not True
            or type(scope.get("expected_member_combination_count")) is not int
            or scope["expected_member_combination_count"] != len(instances) or not instances):
        blockers.append("DESIGN_EXPECTED_SCOPE_UNVERIFIED")
    seen, blocked = set(), []
    for item in instances:
        key = (item.get("element_id"), item.get("combination"))
        reasons = []
        if any(not isinstance(k, str) or not k for k in key) or key in seen:
            reasons.append("DESIGN_DUPLICATE_OR_INVALID_EXPECTED_PAIR")
        seen.add(key)
        state, semantics = item.get("execution_status"), item.get("force_semantics")
        if semantics == "STATIC_SIGNED_VECTOR":
            if (state != "NUMERICAL_COMPLETE" or type(item.get("section_rows_evaluated")) is not int
                    or item["section_rows_evaluated"] <= 0):
                reasons.append("DESIGN_SIGNED_PMM_DEPENDENCY_UNRESOLVED")
        elif semantics == "SCALAR_COMPONENT_ENVELOPE":
            if state != "OUT_OF_SCOPE" or item.get("reason") != "COMPONENT_ENVELOPE_HAS_NO_SIGNED_PMM_VECTOR":
                reasons.append("DESIGN_ENVELOPE_SOURCE_DEPENDENCY_UNRESOLVED")
        else:
            reasons.append("DESIGN_FORCE_SEMANTICS_UNSUPPORTED")
        cuts = item.get("configured_cut_coverage") or {}
        if (type(cuts.get("required_count")) is not int or cuts["required_count"] <= 0
                or type(cuts.get("matched_count")) is not int or cuts["matched_count"] != cuts["required_count"]
                or cuts.get("missing_cuts") != [] or cuts.get("ambiguous_cuts") != []):
            reasons.append("DESIGN_CONFIGURED_CUT_SUBSET_UNVERIFIED")
        mesh = item.get("analysis_element_coverage") or {}
        if (mesh.get("roster_bound") is not True or mesh.get("reason") is not None
                or mesh.get("missing_analysis_element_ids") != []
                or mesh.get("unmapped_analysis_element_ids") != []):
            reasons.append("DESIGN_ANALYSIS_MESH_DEPENDENCY_UNVERIFIED")
        if reasons:
            blocked.append({"element_id": key[0], "combination": key[1], "reason_codes": reasons,
                            "source_reason": item.get("reason")})
    if blocked:
        blockers.append("DESIGN_COHORT_HAS_UNRESOLVED_REQUIRED_PAIRS")
    return {
        "schema": "tbdy.next.design-dependency-ledger.v1", "input_sha256": input_sha,
        "expected_member_combination_count": scope.get("expected_member_combination_count"),
        "blocked_pair_count": len(blocked), "blocked_pairs": blocked,
        "blockers": sorted(set(blockers)), "candidate_execution_allowed": not blockers,
        "status": "REFERENCE_CANDIDATE_INPUTS_BOUND" if not blockers else "BLOCKED_DEPENDENCY",
        "scope": "RUN_LINKED_CANDIDATE_COHORT", "independent_cut_census_proven": False,
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
    }


def selected_candidate_ledger(scope: Mapping[str, Any], cages: Mapping[str, Any],
                              r10: Mapping[str, Any] | None, *, input_sha: str) -> dict[str, Any]:
    """Bind R10's actual in-memory candidate sections, without selecting again."""
    from dataclasses import asdict
    from ..column_engine.section_capacity import Section
    from .column_r10_live import SelectedColumnCage

    expected = sorted({item["element_id"] for item in scope.get("instances", ())})
    r10 = r10 or {}
    reported = r10.get("per_member")
    if reported is None:
        reported = {r10.get("member_id"): r10}
    rows = []
    for uid in expected:
        cage = cages.get(uid)
        selection = (reported.get(uid) or {}).get("engineer_column_selection")
        bound = (isinstance(cage, SelectedColumnCage) and isinstance(cage.section, Section)
                 and cage.selection is selection and selection.get("member_id") == uid
                 and bool(selection.get("selected")))
        rows.append({"member_id": uid, "status": "SAME_RUN_CANDIDATE_BOUND" if bound else "BLOCKED_DEPENDENCY",
                     "candidate_sha256": _digest({"selection": selection, "section": asdict(cage.section)}) if bound else None,
                     "reason": None if bound else "SAME_RUN_SELECTED_COLUMN_CAGE_UNAVAILABLE"})
    extra = sorted(set(cages) - set(expected))
    return {"schema": "tbdy.next.selected-candidate-ledger.v1", "input_sha256": input_sha,
            "expected_column_count": len(expected), "bound_column_count": sum(r["reason"] is None for r in rows),
            "rows": rows, "unexpected_column_ids": extra,
            "downstream_execution_allowed": bool(expected) and not extra and all(r["reason"] is None for r in rows),
            "selection_role": "ALGORITHM_SELECTED_CANDIDATE", "engineering_release": "NOT_READY"}
