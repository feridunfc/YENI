"""R03 source audit for concrete design selections and analysis settings."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import re
from typing import Any, Mapping

from ..compiled_dag import canonical_json
from ..vs05_d4_source_authority import COMBOS, SUMMARY, _case_summary, _combo_source, _source_table, _text

DESIGN_COMBOS = "Concrete Frame Design Load Combination Data"
STATIC_CASES = "Load Case Definitions - Linear Static"
GATE = "ANALYSIS_BASIS_GATE"
STAGE = "r03-analysis-setup"
ADOPTED_ANALYSIS_SCHEMA = "tbdy.next.adopted-analysis-basis.v1"
ADOPTED_ANALYSIS_PENDING = "ADOPTED_ANALYSIS_BASIS_ENGINEERING_ACCEPTANCE_PENDING"
_ADMISSION_CODES = frozenset({"APPROVED_MODEL_PROFILE_MISSING",
    "APPROVED_LOAD_ROLES_AND_DESIGN_FAMILIES_MISSING", "LOAD_CASE_ROLES_UNAPPROVED",
    "ANALYSIS_GENERATION_NOT_PROVEN"})


def normalize_analysis_basis(raw: Any, *, source_data_sha256: str) -> dict[str, Any]:
    """Validate explicit calculation assumptions, never infer engineering approval.

    This is an input contract for a source-bound scenario. A supplied review
    reference is an attribution, not an independently verified solver log.
    Native source validation and formal acceptance remain separate outcomes.
    """
    keys = {"schema", "basis_id", "basis_role", "engineering_approval", "source_data_sha256",
            "decision_reference", "model_profile", "case_roles", "design_groups", "generation"}
    if (not isinstance(raw, Mapping) or set(raw) != keys or raw["schema"] != ADOPTED_ANALYSIS_SCHEMA
            or raw["basis_role"] != "ADOPTED_CALCULATION_ASSUMPTIONS"
            or raw["engineering_approval"] != "NOT_GRANTED"):
        raise ValueError("ANALYSIS_BASIS_SCHEMA_INVALID")
    if (not isinstance(source_data_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", source_data_sha256) is None
            or raw["source_data_sha256"] != source_data_sha256):
        raise ValueError("ANALYSIS_BASIS_NATIVE_SOURCE_MISMATCH")

    def label(value):
        return isinstance(value, str) and bool(value.strip()) and value == value.strip() and len(value) <= 2048

    def names(value):
        return (isinstance(value, list) and bool(value) and all(label(x) for x in value)
                and len(value) == len(set(value)))

    if not all(label(raw[key]) for key in ("basis_id", "decision_reference")):
        raise ValueError("ANALYSIS_BASIS_DECISION_REFERENCE_REQUIRED")
    profile = raw["model_profile"]
    if (not isinstance(profile, Mapping)
            or set(profile) != {"profile_id", "structural_system", "ductility_level", "decision_reference"}
            or not all(label(value) for value in profile.values())):
        raise ValueError("ANALYSIS_BASIS_MODEL_PROFILE_INVALID")
    roles, groups, generation = raw["case_roles"], raw["design_groups"], raw["generation"]
    allowed_roles = {"GRAVITY", "STATIC_SEISMIC", "RESPONSE_SPECTRUM", "MODAL", "WIND", "OTHER_STATIC"}
    if (not isinstance(roles, Mapping) or not roles or not all(label(k) for k in roles)
            or any(not isinstance(value, str) or value not in allowed_roles for value in roles.values())):
        raise ValueError("ANALYSIS_BASIS_CASE_ROLES_INVALID")
    if (not isinstance(groups, Mapping) or not groups or not all(label(k) for k in groups)
            or not all(names(value) for value in groups.values())):
        raise ValueError("ANALYSIS_BASIS_DESIGN_GROUPS_INVALID")
    if (not isinstance(generation, Mapping)
            or set(generation) != {"analysis_run_id", "source_analysis_order", "completed_case_names", "decision_reference"}
            or not all(label(generation[key]) for key in ("analysis_run_id", "decision_reference"))
            or generation["source_analysis_order"] != "FIRST_ORDER"
            or not names(generation["completed_case_names"])):
        raise ValueError("ANALYSIS_BASIS_GENERATION_INVALID_OR_UNSUPPORTED")
    result = deepcopy(dict(raw))
    result["generation"]["completed_case_names"] = sorted(generation["completed_case_names"])
    result["design_groups"] = {key: sorted(values) for key, values in sorted(groups.items())}
    result["case_roles"] = dict(sorted(roles.items()))
    return result


def _adopt_calculation_basis(snapshot, analysis_setup, assigned):
    """Require complete native definitions and exact assigned scope before use."""
    from .design_scenario import _digest, _source_data, validate_design_scenario
    lineage = validate_design_scenario(snapshot)
    if lineage is None:
        raise ValueError("ANALYSIS_BASIS_REQUIRES_PREPARED_SCENARIO")
    basis = normalize_analysis_basis(snapshot["analysis_basis"], source_data_sha256=_digest(_source_data(snapshot)))
    if (not analysis_setup.get("definition_coverage_known")
            or analysis_setup.get("source_capture_scope") != "SAME_CAPTURE"):
        raise ValueError("ANALYSIS_BASIS_NATIVE_DEFINITIONS_UNRESOLVED")
    combo_source = snapshot.get("vs04_basis_probe") or {}
    cases = _case_summary(combo_source.get("table_reads") or {}, require_key=True)
    if (set(basis["case_roles"]) != set(cases)
            or set(basis["generation"]["completed_case_names"]) != set(cases)):
        raise ValueError("ANALYSIS_BASIS_CASE_POPULATION_MISMATCH")
    for name, case in cases.items():
        kind, role = case["type"], basis["case_roles"][name]
        modal_kinds = {"Modal", "Modal - Ritz", "Modal - Eigen"}
        if ((kind == "Response Spectrum" and role != "RESPONSE_SPECTRUM")
                or (kind in modal_kinds and role != "MODAL")
                or (kind == "Linear Static" and role not in {"GRAVITY", "STATIC_SEISMIC", "WIND", "OTHER_STATIC"})
                or kind not in {"Response Spectrum", "Linear Static"} | modal_kinds):
            raise ValueError("ANALYSIS_BASIS_CASE_ROLE_OR_TYPE_UNSUPPORTED:" + name)
    groups = {k: sorted(v) for k, v in ((assigned or {}).get("assigned_groups") or {}).items() if v}
    if (not assigned or assigned.get("remaining_unassigned_families")
            or groups != basis["design_groups"]
            or not {name for values in groups.values() for name in values}
                   <= set(analysis_setup.get("defined_combination_names") or ())):
        raise ValueError("ANALYSIS_BASIS_ASSIGNED_GROUP_POPULATION_MISMATCH")
    # A named nonlinear stiffness predecessor contradicts this supported route.
    # NonlinCase=None, in contrast, is never treated as proof of first order.
    if any(row.get("nonlinear_case") not in (None, "", "None")
           for row in analysis_setup.get("linear_static_settings") or ()):
        raise ValueError("ANALYSIS_BASIS_FIRST_ORDER_CONFLICTS_WITH_NATIVE_PREDECESSOR")
    # An explicit P-Delta stiffness record cannot be relabelled first order.
    # A Nonlinear Case / None entry is an unresolved initial condition, so it
    # may only accompany the explicit adopted assumption, never source proof.
    if any(row.get("stiffness_setting") not in {"Unstressed", "Zero Initial Conditions", "Nonlinear Case"}
           for row in analysis_setup.get("linear_static_settings") or ()):
        raise ValueError("ANALYSIS_BASIS_FIRST_ORDER_STIFFNESS_SETTING_CONFLICT_OR_UNSUPPORTED")
    second = snapshot.get("second_order_basis")
    if second is not None and second.get("source_analysis_order") != basis["generation"]["source_analysis_order"]:
        raise ValueError("ANALYSIS_BASIS_SECOND_ORDER_INPUT_CONFLICT")
    return basis


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


def _to_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _audit_cracked_section_modifiers(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Check ETABS section stiffness factors against TBDY 2018 Table 4.2 (0.70 col, 0.35 beam)."""
    gc = snapshot.get("geometry_capture") or {}
    tables = gc.get("tables") if isinstance(gc, Mapping) else None
    if not isinstance(tables, Mapping):
        return {
            "status": "NO_GEOMETRY_CAPTURE_TABLES",
            "column_sections": [],
            "beam_sections": [],
            "all_columns_match_0_70": False,
            "all_beams_match_0_35": False,
        }
    summary_rows = ((tables.get("SECTION_SUMMARY") or {}).get("rows") or ())
    rect_rows = ((tables.get("RECTANGULAR_SECTIONS") or {}).get("rows") or ())
    assign_rows = ((tables.get("SECTION_ASSIGNMENTS") or {}).get("rows") or ())
    col_uids = {str(r.get("UniqueName")) for r in ((tables.get("COLUMN_CONNECTIVITY") or {}).get("rows") or ()) if r.get("UniqueName") is not None}
    beam_uids = {str(r.get("UniqueName")) for r in ((tables.get("BEAM_CONNECTIVITY") or {}).get("rows") or ()) if r.get("UniqueName") is not None}

    col_sec_names: set[str] = set()
    beam_sec_names: set[str] = set()
    for row in assign_rows:
        uid = str(row.get("UniqueName") or "")
        sec = row.get("SectProp") or row.get("SectionProperty") or row.get("AutoSelect")
        if not sec or sec in ("None", "N.A."):
            continue
        if uid in col_uids:
            col_sec_names.add(str(sec))
        elif uid in beam_uids:
            beam_sec_names.add(str(sec))

    assigned_sections: dict[str, set[str]] = {}
    for row in assign_rows:
        uid = str(row.get("UniqueName") or "")
        sec = row.get("SectProp") or row.get("SectionProperty")
        if uid and sec and str(sec) not in ("None", "N.A."):
            assigned_sections.setdefault(uid, set()).add(str(sec))
    assigned_cols = {uid for uid, sections in assigned_sections.items() if len(sections) == 1}
    assignment_coverage_proven = bool(col_uids or beam_uids) and (col_uids | beam_uids) <= assigned_cols
    fallback_columns = not col_sec_names
    fallback_beams = not beam_sec_names
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in rect_rows:
        name = row.get("Name")
        if name:
            by_name[str(name)] = row
            dtype = str(row.get("DesignType") or "")
            if fallback_columns and dtype == "Column":
                col_sec_names.add(str(name))
            elif fallback_beams and dtype == "Beam":
                beam_sec_names.add(str(name))
    for row in summary_rows:
        name = row.get("Name")
        if name:
            # Prefer SECTION_SUMMARY when available since it carries explicit modifiers.
            by_name[str(name)] = row

    def _entry(sec_name: str, target_i: float) -> dict[str, Any]:
        row = by_name.get(sec_name) or {}
        i2 = _to_float_or_none(row.get("I2Mod"))
        i3 = _to_float_or_none(row.get("I3Mod"))
        amod = _to_float_or_none(row.get("AMod"))
        jmod = _to_float_or_none(row.get("JMod"))
        matches = (
            i2 is not None
            and i3 is not None
            and abs(i2 - target_i) <= 1e-4
            and abs(i3 - target_i) <= 1e-4
        )
        return {
            "section": sec_name,
            "target_i_mod": target_i,
            "i2_mod": i2,
            "i3_mod": i3,
            "a_mod": amod,
            "j_mod": jmod,
            "matches_tbdy_table_4_2": matches,
        }

    col_entries = [_entry(name, 0.70) for name in sorted(col_sec_names)]
    beam_entries = [_entry(name, 0.35) for name in sorted(beam_sec_names)]
    all_cols_ok = assignment_coverage_proven and bool(col_entries) and all(e["matches_tbdy_table_4_2"] for e in col_entries)
    all_beams_ok = assignment_coverage_proven and bool(beam_entries) and all(e["matches_tbdy_table_4_2"] for e in beam_entries)
    status = (
        "ETABS_TABLE_4_2_MODIFIERS_VERIFIED"
        if all_cols_ok and all_beams_ok
        else "MODIFIERS_INCOMPLETE_OR_MISMATCHED"
    )
    return {
        "schema": "tbdy.next.cracked-stiffness-table-4-2-audit.v1",
        "code_ref": "TBDY 2018 §4.5.8 / Tablo 4.2",
        "status": status,
        "assignment_coverage_proven": assignment_coverage_proven,
        "missing_assignment_ids": sorted((col_uids | beam_uids) - assigned_cols),
        "column_sections": col_entries,
        "beam_sections": beam_entries,
        "all_columns_match_0_70": all_cols_ok,
        "all_beams_match_0_35": all_beams_ok,
        "notes": "Wall/slab area modifiers and TS500 creep ratio Rm require separate review.",
    }


def _reconcile_assigned_design_families(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    req = (snapshot.get("column_axial") or {}).get("request") or {}
    if req.get("combination_source") != "ASSIGNED_DESIGN":
        return None
    assignment = req.get("design_assignment")
    if not isinstance(assignment, Mapping):
        return None
    groups = assignment.get("groups")
    if not isinstance(groups, Mapping) or not groups:
        return None
    from .design_assignments import _PROFILE

    active_ids = [
        g["id"]
        for g in _PROFILE.get("groups", ())
        if g.get("checks")
    ]
    assigned_ids = sorted(k for k, v in groups.items() if isinstance(v, list) and v)
    remaining = sorted(gid for gid in active_ids if gid not in assigned_ids)
    return {
        "source": "ASSIGNED_DESIGN",
        "profile": assignment.get("profile") or _PROFILE.get("id"),
        "scope": assignment.get("scope"),
        "assigned_groups": {k: list(v) for k, v in sorted(groups.items())},
        "bound_families": assigned_ids,
        "remaining_unassigned_families": remaining,
    }


def project_analysis_setup_reconciliation(
    analysis_setup: Mapping[str, Any] | None,
    snapshot: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Reconcile base R03 audit against ASSIGNED_DESIGN families and ETABS Table 4.2 stiffness factors."""
    if not isinstance(analysis_setup, Mapping) or not isinstance(snapshot, Mapping):
        return None
    assigned = _reconcile_assigned_design_families(snapshot)
    stiffness = _audit_cracked_section_modifiers(snapshot)
    blockers = list(analysis_setup.get("blocker_codes") or ())
    if assigned and "APPROVED_LOAD_ROLES_AND_DESIGN_FAMILIES_MISSING" in blockers:
        idx = blockers.index("APPROVED_LOAD_ROLES_AND_DESIGN_FAMILIES_MISSING")
        replacement = (
            "LOAD_CASE_ROLES_AND_REMAINING_DESIGN_FAMILIES_UNAPPROVED"
            if assigned["remaining_unassigned_families"]
            else "LOAD_CASE_ROLES_UNAPPROVED"
        )
        blockers[idx] = replacement
    adopted = {}
    if snapshot.get("analysis_basis") is not None:
        try:
            basis = _adopt_calculation_basis(snapshot, analysis_setup, assigned)
            from .design_scenario import _digest
            blockers = [code for code in blockers if code not in _ADMISSION_CODES]
            blockers.append(ADOPTED_ANALYSIS_PENDING)
            adopted = {"calculation_basis_status": "ADOPTED_CALCULATION_BASIS_APPLIED_NOT_PROVEN",
                       "calculation_basis": basis, "calculation_basis_sha256": _digest(basis),
                       "analysis_generation_independently_verified": False,
                       "engineering_approval": "NOT_GRANTED"}
        except (KeyError, TypeError, ValueError) as exc:
            blockers.append("ADOPTED_ANALYSIS_BASIS_INVALID:" + str(exc))
    return {
        "schema": "tbdy.next.r03-reconciliation.v1",
        "design_families_assigned": bool(assigned),
        "assigned_design_families": assigned,
        "cracked_section_stiffness_audit": stiffness,
        "reconciled_blocker_codes": blockers,
        **adopted,
    }
