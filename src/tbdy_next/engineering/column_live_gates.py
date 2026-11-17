"""Column P0 gates projected over the SAME replayed live stage outputs.

This module owns no formula and recomputes no force. It binds the existing
formula owners (`column_engine.ts500_column`, `engineering.column_gates`) to the
already-verified `column-axial` / `column-pmm` stage results of one run, so the
live console, the HTML report and the archived 127/C88 path apply identical
normative gates. It is a pure, deterministic projection (no receipt of its own):
historical `column-axial` / `column-pmm` receipts stay byte-for-byte replayable.

Never emits PASS or READY. A locally proven FAIL is reported as FAIL and is
never folded into NOT_PROVEN.
"""
from __future__ import annotations

from typing import Any, Mapping

from ..column_engine.native_archive import BankError
from .column_gates import evaluate_axial_caps, evaluate_reinforcement_state

SCHEMA = "tbdy.next.column-live-gates.v1"
SEISMIC_GROUP = "ductile"
_RESOLVED_ROW = {"WITHIN_SCENARIO_SURFACE", "EXCEEDS_SCENARIO_SURFACE",
                 "OUTSIDE_SCENARIO_AXIAL_RANGE", "AXIAL_ONLY_SCENARIO"}


def _seismic_names(plan: Mapping[str, Any]) -> tuple[set[str], str]:
    """Seismic applicability comes only from the user's assigned design group."""
    assignment = plan.get("design_assignment")
    if plan.get("source") == "ASSIGNED_DESIGN" and isinstance(assignment, Mapping):
        return set((assignment.get("groups") or {}).get(SEISMIC_GROUP, ())), "ASSIGNED_DESIGN_GROUP"
    return set(), "COMBINATION_ROLE_UNASSIGNED"


def _axial_gates(axial: Mapping[str, Any], seismic: set[str], basis: str) -> dict:
    ts500_exceed, tbdy_exceed, tbdy_unassigned, rows = [], [], 0, []
    for column in axial.get("columns", ()):
        if "tbdy_seismic_reference_limit_kn" not in column:
            continue
        ts500_limit = column["ts500_limit_kn"]
        tbdy_limit = column["tbdy_seismic_reference_limit_kn"]
        for check in column.get("combination_checks", ()):
            if check.get("status") not in {"WITHIN_LIMIT", "OUTSIDE_LIMIT"}:
                continue
            nd, name = check["nd_kn"], check["combination"]
            applicable = None if basis != "ASSIGNED_DESIGN_GROUP" else name in seismic
            record = {
                "element_id": column["element_id"], "combination": name, "nd_kn": nd,
                "chk005_limit_kn": ts500_limit, "chk005_exceeded": nd > ts500_limit,
                "chk004_limit_kn": tbdy_limit, "chk004_ratio": nd / tbdy_limit,
                "chk004_exceeds_reference": nd > tbdy_limit,
                "chk004_applicable": applicable,
            }
            if record["chk005_exceeded"]:
                ts500_exceed.append(record)
            if applicable is None:
                tbdy_unassigned += int(record["chk004_exceeds_reference"])
            elif applicable and record["chk004_exceeds_reference"]:
                tbdy_exceed.append(record)
            rows.append(record)
    return {
        "chk005_rule": "TS500:7.7:AXIAL_COMPRESSION_MAX:COLUMN:2000R2018",
        "chk004_rule": "TBDY2018:7.3.1.2:AXIAL_FORCE_LIMIT:COLUMN:2018",
        "seismic_applicability_basis": basis,
        "evaluated_pair_count": len(rows),
        "chk005_exceedance_count": len(ts500_exceed),
        "chk004_proven_exceedance_count": len(tbdy_exceed),
        "chk004_exceeds_reference_but_role_unassigned_count": tbdy_unassigned,
        "chk004_proven_exceedances": tbdy_exceed,
        "chk005_exceedances": ts500_exceed,
    }


def _reinforcement_gate(pmm: Mapping[str, Any]) -> dict | None:
    evidence = pmm.get("section_evidence")
    if not evidence:
        return None
    role = {"ETABS_DESIGN_TEMPLATE": "TEMPLATE",
            "ETABS_CHECK_REINFORCEMENT": "SELECTED"}.get(evidence["reinforcement_role"])
    if role is None:
        return None
    ac = evidence["t2_mm"] * evidence["t3_mm"]
    ast = evidence["bar_count"] * evidence["longitudinal_bar_area_mm2"]
    try:
        gate = evaluate_reinforcement_state(
            role=role, ac_mm2=ac, ast_mm2=ast, bar_count=evidence["bar_count"],
            bar_diameter_mm=evidence["longitudinal_bar_diameter_mm"],
            is_designed_flag=role == "TEMPLATE", selection_approved=False)
    except (BankError, ValueError) as exc:
        return {"status": "UNRESOLVED", "reason": str(exc), "formal_compliance": "NOT_PROVEN"}
    return {**gate, "etabs_reinforcement_role": evidence["reinforcement_role"],
            "longitudinal_steel_area_mm2": ast, "gross_section_area_mm2": ac}


def _pmm_axial_override(pmm: Mapping[str, Any], axial: Mapping[str, Any],
                        seismic: set[str], basis: str) -> dict | None:
    evidence = pmm.get("section_evidence")
    column = next((c for c in axial.get("columns", ()) if c.get("element_id") == pmm.get("member_id")), None)
    if not evidence or column is None or "fcd_mpa" not in column:
        return None
    ac, ast = evidence["t2_mm"] * evidence["t3_mm"], evidence["bar_count"] * evidence["longitudinal_bar_area_mm2"]
    overridden = 0
    for row in pmm.get("rows", ()):
        if row.get("status") not in _RESOLVED_ROW or row.get("utilization") is None:
            continue
        gate = evaluate_axial_caps(
            nd_kn=row["nd_kn"], fck_mpa=evidence["fck_mpa"], fcd_mpa=evidence["fcd_mpa"],
            fyd_mpa=evidence["fyd_mpa"], ac_mm2=ac, ast_mm2=ast,
            is_seismic_combo=basis == "ASSIGNED_DESIGN_GROUP" and row["combination"] in seismic,
            pmm_utilization=row["utilization"])
        overridden += int(gate["overrides_pmm_pass"])
    return {"pmm_rows_where_axial_cap_overrides_section_surface": overridden,
            "raw_plastic_n0_note": "Raw N0 is a section reference, not a normative limit (not 0.80*N0)."}


def project_column_gates(source: Mapping[str, Any], axial: Mapping[str, Any] | None,
                         pmm: Mapping[str, Any] | None = None,
                         local_axis_angle_deg: float | None = None) -> dict | None:
    """Deterministic gate projection; None when the run has no column axial source."""
    if axial is None or "column_axial" not in source:
        return None
    plan = axial["combination_plan"]
    seismic, basis = _seismic_names(plan)
    axial_gates = _axial_gates(axial, seismic, basis)
    is_all_pmm = bool(pmm and (pmm.get("scope") == "ALL_COLUMNS" or pmm.get("member_id") == "ALL"))
    if is_all_pmm:
        member_reinf = [g for g in (_reinforcement_gate(m) for m in pmm.get("members", ())) if g is not None]
        reinforcement = None
        if member_reinf:
            tmpl_fail = sum(1 for g in member_reinf if g.get("would_fail_if_selected"))
            chk_fail = sum(1 for g in member_reinf if g.get("formal_compliance") == "FAIL")
            reinforcement = {
                "scope": "ALL_COLUMNS",
                "evaluated_column_count": len(member_reinf),
                "template_would_fail_count": tmpl_fail,
                "chk117_fail_count": chk_fail,
                "role": "TEMPLATE" if any(g.get("role") == "TEMPLATE" for g in member_reinf) else member_reinf[0].get("role"),
                "would_fail_if_selected": tmpl_fail > 0,
                "formal_compliance": "FAIL" if chk_fail > 0 else "NOT_PROVEN",
            }
    else:
        reinforcement = _reinforcement_gate(pmm) if pmm else None
    findings, open_gates = [], []

    if axial_gates["chk005_exceedance_count"]:
        findings.append({"code": "CHK005_TS500_7_7_AXIAL_LIMIT_EXCEEDED", "status": "FAIL",
                         "count": axial_gates["chk005_exceedance_count"]})
    if axial_gates["chk004_proven_exceedance_count"]:
        findings.append({"code": "CHK004_TBDY_7_3_1_2_AXIAL_LIMIT_EXCEEDED", "status": "FAIL",
                         "count": axial_gates["chk004_proven_exceedance_count"]})
    if basis != "ASSIGNED_DESIGN_GROUP":
        open_gates.append({"code": "SEISMIC_COMBINATION_ROLE_UNASSIGNED", "status": "NOT_PROVEN",
                           "effect": "CHK-004 reported as reference ratio only"})
    if reinforcement is not None:
        if reinforcement.get("role") == "TEMPLATE":
            open_gates.append({"code": "SELECTED_CAGE_MISSING", "status": "NOT_PROVEN",
                               "template_would_fail_if_selected": reinforcement.get("would_fail_if_selected"),
                               "rho": reinforcement.get("rho"), "rho_min": reinforcement.get("rho_min")})
            if reinforcement.get("would_fail_if_selected"):
                findings.append({"code": "TEMPLATE_CAGE_WOULD_FAIL_IF_SELECTED", "status": "INFORMATIONAL",
                                 "reason_codes": reinforcement.get("reason_codes")})
        elif reinforcement.get("formal_compliance") == "FAIL":
            findings.append({"code": "CHK117_TBDY_7_3_2_1_LONGITUDINAL_LIMITS", "status": "FAIL",
                             "reason_codes": reinforcement.get("reason_codes"), "rho": reinforcement.get("rho")})
        else:
            open_gates.append({"code": "SELECTED_CAGE_APPROVAL", "status": "NOT_PROVEN"})
    elif pmm is not None:
        open_gates.append({"code": "SELECTED_CAGE_MISSING", "status": "NOT_PROVEN",
                           "reason": pmm.get("reason")})
    if pmm is not None:
        angle = local_axis_angle_deg
        if angle is None and not is_all_pmm:
            from .column_r10_live import member_local_axis_angle_deg
            angle = member_local_axis_angle_deg(source, pmm.get("member_id"))
        open_gates += [
            {"code": "ANALYSIS_ORDER_UNVERIFIED", "status": "NOT_PROVEN", "value": pmm.get("analysis_order")},
            *([] if (angle is not None or is_all_pmm) else [
                {"code": "LOCAL_AXIS_ANGLE_NOT_CAPTURED_LIVE", "status": "NOT_PROVEN",
                 "effect": "Global moment projection only; local-axis e_min check unaffected"}
            ]),
            {"code": "CONFINEMENT_DETAIL_NOT_PROVEN", "status": "NOT_PROVEN", "rule": "LEGACY73:CHK-007"},
        ]
    else:
        angle = local_axis_angle_deg
    if is_all_pmm:
        overrides = [ov for ov in (_pmm_axial_override(m, axial, seismic, basis) for m in pmm.get("members", ())) if ov is not None]
        pmm_override = {
            "scope": "ALL_COLUMNS",
            "pmm_rows_where_axial_cap_overrides_section_surface": sum(
                ov["pmm_rows_where_axial_cap_overrides_section_surface"] for ov in overrides
            ),
            "raw_plastic_n0_note": "Raw N0 is a section reference, not a normative limit (not 0.80*N0).",
        } if overrides else None
    else:
        pmm_override = _pmm_axial_override(pmm, axial, seismic, basis) if pmm else None
    proven_fail = any(item["status"] == "FAIL" for item in findings)
    return {
        "schema": SCHEMA, "member_id": (pmm or {}).get("member_id"),
        "local_axis_angle_deg": angle,
        "bound_stage_status": {"column_axial": axial.get("status"),
                               "column_pmm": (pmm or {}).get("status")},
        "axial_gates": axial_gates,
        "reinforcement_gate": reinforcement,
        "pmm_axial_override": pmm_override,
        "local_findings": findings, "open_gates": open_gates,
        "canonical_design_pass_allowed": False,
        "status": "LOCAL_FAIL_PRESENT" if proven_fail else "GATES_EVALUATED_NOT_PROVEN",
        "formal_compliance": "FAIL" if proven_fail else "NOT_PROVEN",
        "engineering_release": "NOT_READY",
    }
