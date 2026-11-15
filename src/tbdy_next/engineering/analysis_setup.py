"""R03 source audit for concrete design selections and analysis settings."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from typing import Any, Mapping

from ..compiled_dag import canonical_json
from ..vs05_d4_source_authority import COMBOS, SUMMARY, _case_summary, _combo_source, _source_table, _text

DESIGN_COMBOS = "Concrete Frame Design Load Combination Data"
STATIC_CASES = "Load Case Definitions - Linear Static"
GATE = "ANALYSIS_BASIS_GATE"
STAGE = "r03-analysis-setup"


def audit_model_analysis_setup(
    gateway_capture: Mapping[str, Any], *,
    combo_capture: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect native definitions and selections without assigning project roles."""
    gateway_tables = gateway_capture.get("table_reads") or {}
    combo_tables = gateway_tables if combo_capture is None else combo_capture.get("table_reads") or {}
    if not isinstance(gateway_tables, Mapping):
        gateway_tables = {}
    if not isinstance(combo_tables, Mapping):
        combo_tables = {}
    blockers, diagnostics = [], {}
    cases, graph, selections, settings = {}, None, None, []
    try:
        cases = _case_summary(combo_tables, require_key=True)
        parsed = _combo_source(combo_tables, cases, include_graph=True, require_key=True)
        if not parsed["candidate_operator_reference_shape_observed"]:
            diagnostics["combination_graph"] = {
                key: parsed[key] for key in ("source_warnings", "cycle_candidates",
                    "unknown_reference_count", "unknown_references", "unsupported_operator_combinations")
            }
            blockers.append("COMBINATION_GRAPH_UNRESOLVED")
        graph = parsed
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        diagnostics["combination_graph"] = str(exc)
        blockers.append("COMBINATION_GRAPH_UNAVAILABLE")

    try:
        rows = _source_table(combo_tables, DESIGN_COMBOS, {"ComboName", "ComboType"},
                             allow_empty=True, require_key=True)
        seen = set()
        selections = []
        for row in rows:
            name = _text(row["ComboName"], "DESIGN_COMBINATION_NAME")
            role = _text(row["ComboType"], "DESIGN_COMBINATION_TYPE")
            if name == "None" or role == "None" or (name, role) in seen:
                raise ValueError("DESIGN_COMBINATION_SELECTION_DUPLICATE_OR_INVALID")
            seen.add((name, role))
            selections.append({"combination": name, "design_type": role})
    except (ValueError, KeyError, TypeError) as exc:
        diagnostics["design_selection"] = str(exc)
        blockers.append("CONCRETE_DESIGN_COMBINATIONS_NOT_OBSERVED")
        selections = None

    if graph and selections is not None:
        unknown = sorted({r["combination"] for r in selections} - graph["typed_graph"].keys())
        if unknown:
            blockers.append("DESIGN_SELECTION_DEFINITION_UNRESOLVED")
            diagnostics["unresolved_selections"] = unknown

    try:
        raw_settings = _source_table(gateway_tables, STATIC_CASES, {"Name", "StiffType", "NonlinCase"},
                                     require_key=True)
        observed = {}
        for row in raw_settings:
            name = _text(row["Name"], "STATIC_CASE_NAME")
            stiffness = row["StiffType"]
            if stiffness not in ("", "None"):
                # Each case has one header followed by rows for additional load terms.
                if name in observed:
                    raise ValueError("STATIC_CASE_DUPLICATE_HEADER:" + name)
                observed[name] = {"case": name, "stiffness_setting": stiffness,
                                  "nonlinear_case": row["NonlinCase"]}
            elif name not in observed or row["NonlinCase"] not in ("", "None", observed[name]["nonlinear_case"]):
                raise ValueError("STATIC_CASE_SETTINGS_HEADER_UNRESOLVED:" + name)
        settings = list(observed.values())
        if cases and combo_capture is None:
            expected = {name for name, case in cases.items() if case["type"] == "Linear Static"}
            if expected != observed.keys():
                blockers.append("LINEAR_STATIC_SETTINGS_COVERAGE_UNRESOLVED")
                diagnostics["static_settings_coverage"] = {
                    "missing_cases": sorted(expected - observed.keys()),
                    "unknown_cases": sorted(observed.keys() - expected),
                }
    except (ValueError, KeyError, TypeError) as exc:
        diagnostics["static_settings"] = str(exc)
        blockers.append("LINEAR_STATIC_SETTINGS_NOT_OBSERVED")

    # Model scope, engineering load roles and demand authority require approval
    # external to table capture. Presence in Strength is an ETABS fact only.
    blockers.extend(("APPROVED_MODEL_PROFILE_MISSING", "APPROVED_LOAD_ROLES_AND_DESIGN_FAMILIES_MISSING",
                     "ANALYSIS_GENERATION_NOT_PROVEN"))
    strength = sorted(r["combination"] for r in selections or [] if r["design_type"] == "Strength")
    if selections is not None and not strength:
        blockers.append("STRENGTH_DESIGN_COMBINATION_SELECTION_EMPTY")
    risk = {r["combo"]: r for r in (graph or {}).get("nonconcurrent_vector_risks", [])}
    roles_by_combination = defaultdict(list)
    for r in selections or []:
        roles_by_combination[r["combination"]].append(r["design_type"])
    strength_names = set(strength)
    combination_audit = []
    for name, group in sorted((graph or {}).get("typed_graph", {}).items()):
        lineage = risk.get(name, {})
        combination_audit.append({
            "combination": name,
            "operator": group["operator_etabs"],
            "spectral_case_references": lineage.get("spectrum_source_cases", []),
            "nonconcurrent_source_reasons": lineage.get("reason_codes", []),
            "observed_design_types": sorted(roles_by_combination[name]) if selections is not None else None,
            "selected_for_strength": None if selections is None else name in strength_names,
        })

    return {
        "schema": "tbdy.next.r03.model-analysis-setup-audit.v2",
        "check_id": GATE, "dag_declared_dependencies": ["ANALYSIS_GENERATION_GATE", "COMBINATION_DEFINITION_GATE"],
        "source_capture_scope": "SAME_CAPTURE" if combo_capture is None else "SEPARATE_CAPTURES",
        "status": "BLOCKED", "verdict": "NOT_PROVEN", "dag_execution_authority": "DENIED",
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
        "analysis_generation_proven": False,
        "analysis_order_proven": False, "nonlin_case_none_alone_proves_first_order": False,
        "model_profile_approved": False, "load_roles_approved": False, "complete_combo_book_approved": False,
        "design_demand_authorized": False,
        "case_definition_count": len(cases) if cases else None,
        "definition_coverage_known": bool(graph and graph["candidate_operator_reference_shape_observed"]),
        "defined_combination_names": sorted((graph or {}).get("typed_graph", {})),
        "operator_counts": (graph or {}).get("operator_counts", {}),
        "typed_graph_source_sha256": (graph or {}).get("typed_graph_source_hash"),
        "design_selection_observed": selections is not None,
        "design_selection_count": len(selections) if selections is not None else None,
        "design_selection_type_counts": dict(sorted(Counter(r["design_type"] for r in selections or []).items())),
        "strength_design_combinations": strength if selections is not None else None,
        "design_selection": sorted(selections, key=lambda r: (r["design_type"], r["combination"])) if selections is not None else None,
        "combination_audit": combination_audit,
        "linear_static_settings": sorted(settings, key=lambda r: r["case"]),
        "linear_static_stiffness_counts": dict(sorted(Counter(r["stiffness_setting"] for r in settings).items())),
        "blocker_codes": blockers,
        "diagnostics": diagnostics,
        "source_tables_sha256": sha256(canonical_json({
            **{key: combo_tables.get(key) for key in (SUMMARY, COMBOS, DESIGN_COMBOS)},
            STATIC_CASES: gateway_tables.get(STATIC_CASES),
        })).hexdigest(),
    }


def bind_analysis_setup(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Reconcile the R03 source gate with the same combined capture."""
    probe = snapshot.get("vs04_basis_probe")
    metadata = snapshot.get("capture_metadata") or {}
    if (isinstance(probe, Mapping) and isinstance(metadata, Mapping)
            and probe.get("schema") == "tbdy.next.vs04e.basis-source-probe.v1"
            and probe.get("source_mode") == "LIVE_ETABS"
            and snapshot.get("source_mode") == "LIVE_ETABS"
            and metadata.get("vs04_same_session_capture") is True
            and probe.get("read_only_invariant_proven") is True
            and probe.get("units_before") == probe.get("units_after") == 6
            and probe.get("display_cases_before") == probe.get("display_cases_after")):
        return audit_model_analysis_setup(probe)
    result = audit_model_analysis_setup({})
    result["source_capture_scope"] = "UNVERIFIED"
    result["blocker_codes"].insert(0, "SAME_RUN_ANALYSIS_SETUP_CAPTURE_UNPROVEN")
    return result
