"""P0-A / P0-B / P0-C Canonical Engineering Gates & Single Owner Contract.

Implements the mandatory engineering gates specified in
YENI_MASTER_HANDOFF_ENGINEERING_RECIPE_2026-11-14.md (handoff-r1):
- §2: Namespace & Catalog Reconciliation (73 Recipe <-> 94 DAG <-> 242 Atomic;
      CHK-108 -> PLAN_PROTRUSIONS_A3, CHK-111 -> VERTICAL_DISCONTINUITY_B3,
      CHK-008 -> None)
- §3: Single Owner Contract (OwnerRegister)
- §5 / §6:
  - F01: Normative axial compression ceilings CHK-005 (TS500 Eq. 7.7: 0.90*fcd*Ac)
         and CHK-004 (TBDY 7.3.1.2: 0.40*fck*Ac), separated from raw N0.
  - F02 / F08 / F09: TS500 6.3.10 Eq. 6.16 minimum eccentricity demand floor
         with typed NativeSectionDims -> LocalSectionDims single conversion.
  - F03: Explicit separation of TEMPLATE (IsDesigned=Yes, e.g. 12Phi20) vs
         PROPOSED (e.g. 16Phi24) vs SELECTED/AS_BUILT reinforcement states.
  - F04: ModelAnalysisSetupAuditor (auditing missing seismic combinations in
         Concrete Frame Design Load Combination Data, service combo misplacement,
         and NonlinCase=None with analysis generation proof).
  - F05: Tolerant unique station matching (tol_m=1e-6).
  - F07: Transverse reinforcement leg topology (CHK-123, TBDY 7.3.4.1(a):
         horizontal leg spacing a_i <= 25*phi_transverse and vertical spacing
         50 mm <= s <= min(b_min/3, 6*phi_longitudinal, 150 mm)).
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from tbdy_next.column_engine.csi_geometry import (
    LocalSectionDims,
    NativeSectionDims,
    local_dimensions,
    to_local_dimensions,
)
from tbdy_next.column_engine.native_archive import BankError, digest, finite
from tbdy_next.column_engine.section_capacity import Bar, Material, Section, solver
from tbdy_next.column_engine.ts500_column import (
    apply_minimum_eccentricity,
    axial_compression_caps_kn,
    minimum_eccentricity_mm,
)
from .analysis_setup import audit_model_analysis_setup


# ---------------------------------------------------------------------------
# §2 Namespace & Catalog Reconciliation
# ---------------------------------------------------------------------------

NAMESPACE_RECONCILIATION: dict[str, dict[str, Any]] = {
    "Rxx": {
        "range": "R00..R20",
        "count": 21,
        "kind": "PRODUCT_CLOSURE_PHASE",
        "equatable_to_checks": False,
    },
    "VSxx": {
        "range": "VS01..VS27",
        "count": 27,
        "kind": "HISTORICAL_VERTICAL_SLICE",
        "equatable_to_checks": False,
    },
    "LEGACY73": {
        "prefix": "LEGACY73:CHK-",
        "count": 73,
        "kind": "RECIPE_CHECK_CATALOG",
        "equatable_to_dag94": False,
        "equatable_to_legacy242": False,
    },
    "LEGACY242": {
        "prefix": "LEGACY242:CHK-",
        "count": 242,
        "kind": "ATOMIC_RULE_CANDIDATE_CATALOG",
        "equatable_to_legacy73": False,
    },
    "DAG94": {
        "count": 94,
        "breakdown": {"gate": 16, "derivation": 10, "regulatory": 32, "design": 36},
        "kind": "COMPILED_NORMATIVE_DAG",
        "equatable_to_legacy73": False,
    },
}

LEGACY73_CATALOG_FIXES: dict[str, dict[str, Any] | None] = {
    "LEGACY73:CHK-108": {
        "legacy_id": "LEGACY73:CHK-108",
        "canonical_name": "PLAN_PROTRUSIONS_A3",
        "canonical_id": "TBDY2018:3.6.1.1:PLAN_PROTRUSIONS_A3:STORY_POLYGON:2018",
        "description_tr": "A3 plan projection irregularity (ax > 0.20*Lx and ay > 0.20*Ly)",
        "invalid_rejected_labels": ("storey discontinuity", "story discontinuity"),
    },
    "LEGACY73:CHK-111": {
        "legacy_id": "LEGACY73:CHK-111",
        "canonical_name": "VERTICAL_DISCONTINUITY_B3",
        "canonical_id": "TBDY2018:3.6.2.4:VERTICAL_DISCONTINUITY_B3:SYSTEM:2018",
        "description_tr": "B3 discontinuity of vertical structural elements",
        "invalid_rejected_labels": ("mass irregularity",),
    },
    "CHK-008": None,
    "LEGACY73:CHK-008": None,
}


def parse_canonical_rule_id(canonical_id: str) -> dict[str, str]:
    """Validate and parse canonical rule ID in standard:clause:rule:scope:revision format."""
    if not isinstance(canonical_id, str):
        raise ValueError("CANONICAL_ID_MUST_BE_STRING")
    parts = canonical_id.split(":")
    if len(parts) != 5 or any(not p.strip() for p in parts):
        raise ValueError(f"INVALID_CANONICAL_ID_FORMAT:{canonical_id}")
    standard, clause, rule, scope, revision = parts
    return {
        "standard": standard,
        "clause": clause,
        "rule": rule,
        "scope": scope,
        "revision": revision,
        "canonical_id": canonical_id,
    }


def resolve_legacy73_catalog_entry(check_id: str, *, proposed_label: str | None = None) -> dict[str, Any] | None:
    """Resolve Legacy 73 catalog corrections (§2): CHK-108, CHK-111, and absent CHK-008."""
    normalized = check_id.strip()
    if normalized in ("CHK-008", "LEGACY73:CHK-008"):
        return None
    if not normalized.startswith("LEGACY73:") and normalized.startswith("CHK-"):
        normalized = "LEGACY73:" + normalized
    if normalized in LEGACY73_CATALOG_FIXES:
        entry = LEGACY73_CATALOG_FIXES[normalized]
        if entry is None:
            return None
        if proposed_label is not None:
            low = proposed_label.strip().casefold()
            if any(bad in low for bad in entry["invalid_rejected_labels"]):
                raise ValueError(f"INVALID_LEGACY73_CATALOG_LABEL:{normalized}:{proposed_label}")
        return dict(entry)
    raise KeyError(f"UNREGISTERED_LEGACY73_CHECK:{check_id}")


# ---------------------------------------------------------------------------
# §3 Single Owner Contract (OwnerRegister)
# ---------------------------------------------------------------------------

SINGLE_OWNER_MATRIX: tuple[dict[str, Any], ...] = (
    {
        "capability": "ETABS_COM_AND_TABLE_CAPTURE",
        "source_owner": ("tbdy_next.live_etabs", "tbdy_next.etabs_source_gateway_windows"),
        "formula_owner": None,
        "execution_status": "GH_VERIFIED",
    },
    {
        "capability": "SEISMIC_MASS_AND_STORY_GEOMETRY_LINKAGE",
        "source_owner": ("tbdy_next.basis_linkage",),
        "formula_owner": "tbdy_next.normative_basis",
        "execution_status": "SOURCE_AND_ROLEBOOK_BOUND",
    },
    {
        "capability": "GLOBAL_SECOND_ORDER_THETA_II",
        "source_owner": ("tbdy_next.story_second_order",),
        "formula_owner": "tbdy_next.engineering.story_pdelta",
        "execution_status": "PARTIAL_SOURCE_NUMERIC",
    },
    {
        "capability": "SECTION_STRAIN_COMPATIBILITY_PMM",
        "source_owner": ("tbdy_next.column_engine.column_pmm", "tbdy_next.engineering.live_column"),
        "formula_owner": "tbdy_next.column_engine.section_capacity",
        "execution_status": "PARTIAL_NUMERIC",
    },
    {
        "capability": "SECTION_QUALITY_AND_K1_VERIFICATION",
        "source_owner": ("tbdy_next.column_engine.column_pmm",),
        "formula_owner": "tbdy_next.column_engine.column_pmm_quality",
        "execution_status": "GH_VERIFIED_CONTINUOUS_K1",
    },
    {
        "capability": "LOCAL_SLENDERNESS_AND_MOMENT_MAGNIFICATION",
        "source_owner": ("tbdy_next.column_engine.column_stability",),
        "formula_owner": "tbdy_next.column_engine.ts500_column",
        "execution_status": "REFERENCE_AND_E_MIN_GATE",
    },
    {
        "capability": "SINGLE_COLUMN_LIVE_BRIDGE_127_C88",
        "source_owner": ("tbdy_next.engineering.live_column", "tbdy_next.engineering.column_gates"),
        "formula_owner": ("tbdy_next.column_engine.section_capacity", "tbdy_next.column_engine.ts500_column"),
        "execution_status": "SCENARIO_AND_P0_GATES_WIRED",
    },
    {
        "capability": "DAG_COMPILER_AND_FCR",
        "source_owner": ("tbdy_next.archived_source_bridge",),
        "formula_owner": "tbdy_next.compiled_dag",
        "execution_status": "DENIED_STATIC_PLANNER_ONLY",
    },
    {
        "capability": "PRESENTATION_AND_EXPORT",
        "source_owner": ("tbdy_next.history",),
        "formula_owner": None,
        "presentation_only": ("tbdy_next.reporting", "tbdy_next.web"),
        "execution_status": "SEALED_RUN_RESULT_ONLY",
    },
)


def verify_single_owner_contract() -> dict[str, Any]:
    """Verify the Single Owner Contract (§3) and package self-containment (F12)."""
    import tbdy_next

    pkg_root = Path(tbdy_next.__file__).resolve().parent
    tools_imports_in_pkg: list[str] = []
    for py_file in sorted(pkg_root.rglob("*.py")):
        text = py_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("from tools.") or stripped.startswith("import tools."):
                tools_imports_in_pkg.append(f"{py_file.relative_to(pkg_root)}:{stripped}")

    capabilities = [row["capability"] for row in SINGLE_OWNER_MATRIX]
    unique_capabilities = len(capabilities) == len(set(capabilities))
    presentation_row = next(r for r in SINGLE_OWNER_MATRIX if r["capability"] == "PRESENTATION_AND_EXPORT")
    presentation_has_no_formula = presentation_row["formula_owner"] is None

    ok = unique_capabilities and presentation_has_no_formula and not tools_imports_in_pkg
    return {
        "schema": "tbdy.next.p0a.single-owner-contract.v1",
        "status": "VERIFIED" if ok else "VIOLATION",
        "package_root": str(pkg_root),
        "capability_count": len(SINGLE_OWNER_MATRIX),
        "unique_capabilities": unique_capabilities,
        "presentation_has_no_formula_owner": presentation_has_no_formula,
        "tools_imports_in_src_tbdy_next": tools_imports_in_pkg,
        "single_owner_matrix": list(SINGLE_OWNER_MATRIX),
        "namespace_reconciliation": NAMESPACE_RECONCILIATION,
    }


# ---------------------------------------------------------------------------
# F01: Normative Axial Compression Ceiling Gates (CHK-004 & CHK-005)
# ---------------------------------------------------------------------------

def evaluate_axial_caps(
    *,
    nd_kn: float,
    fck_mpa: float,
    fcd_mpa: float,
    fyd_mpa: float,
    ac_mm2: float,
    ast_mm2: float,
    is_seismic_combo: bool = False,
    pmm_utilization: float | None = None,
) -> dict[str, Any]:
    """Evaluate TS500 Eq.(7.7) (CHK-005) and TBDY §7.3.1.2 (CHK-004) axial caps (F01).

    Even if raw PMM radial utilization < 1.0 (because RadialSolver terminates at
    raw plastic N0 = 0.85*fcd*(Ac-Ast) + fyd*Ast), exceeding TS500 7.7 (0.90*fcd*Ac)
    or TBDY 7.3.1.2 (0.40*fck*Ac under seismic combinations) produces an explicit
    normative FAIL.
    """
    nd = finite(nd_kn, "nd_kn")
    caps = axial_compression_caps_kn(
        fck_mpa=fck_mpa,
        fcd_mpa=fcd_mpa,
        fyd_mpa=fyd_mpa,
        ac_mm2=ac_mm2,
        ast_mm2=ast_mm2,
    )
    ts500_cap = caps["ts500_eq_7_7_max_nd_kn"]
    tbdy_cap = caps["tbdy_7_3_1_2_max_ndm_kn"]
    n0_kn = caps["raw_plastic_n0_kn"]

    ts500_ratio = max(0.0, nd) / ts500_cap
    tbdy_ratio = max(0.0, nd) / tbdy_cap
    ts500_exceeded = nd > ts500_cap
    tbdy_exceeded = nd > tbdy_cap

    reasons: list[str] = []
    if ts500_exceeded:
        reasons.append("CHK005_TS500_7_7_AXIAL_LIMIT_EXCEEDED")
    if is_seismic_combo and tbdy_exceeded:
        reasons.append("CHK004_TBDY_7_3_1_2_AXIAL_LIMIT_EXCEEDED")

    failed = bool(reasons)
    return {
        "checks": {
            "CHK-005": {
                "canonical_id": "TS500:7.7:AXIAL_COMPRESSION_MAX:COLUMN:2000R2018",
                "formula": "Nd <= 0.90 * fcd * Ac",
                "nd_kn": nd,
                "limit_kn": ts500_cap,
                "utilization_ratio": ts500_ratio,
                "exceeded": ts500_exceeded,
                "status": "FAIL" if ts500_exceeded else "WITHIN_NUMERIC_CAP",
            },
            "CHK-004": {
                "canonical_id": "TBDY2018:7.3.1.2:AXIAL_FORCE_LIMIT:COLUMN:2018",
                "formula": "Ndm <= 0.40 * fck * Ac",
                "nd_kn": nd,
                "limit_kn": tbdy_cap,
                "utilization_ratio": tbdy_ratio,
                "exceeded": tbdy_exceeded,
                "applicable_to_combo": is_seismic_combo,
                "status": (
                    "FAIL" if (is_seismic_combo and tbdy_exceeded)
                    else ("EXCEEDS_SEISMIC_CAP_ON_GRAVITY_CASE" if tbdy_exceeded else "WITHIN_NUMERIC_CAP")
                ),
            },
        },
        "raw_plastic_n0_kn": n0_kn,
        "non_ts500_080_n0_reference_kn": caps["non_ts500_080_n0_reference_kn"],
        "080_n0_is_ts500_7_7": False,
        "pmm_utilization_input": pmm_utilization,
        "overrides_pmm_pass": bool(failed and pmm_utilization is not None and pmm_utilization < 1.0),
        "status": "FAIL" if failed else "WITHIN_AXIAL_CAPS",
        "formal_compliance": "FAIL" if failed else "NOT_PROVEN",
        "reason_codes": reasons,
    }


# ---------------------------------------------------------------------------
# F03: Reinforcement State Classification (TEMPLATE vs PROPOSED vs SELECTED)
# ---------------------------------------------------------------------------

def evaluate_reinforcement_state(
    *,
    role: str,
    ac_mm2: float,
    bar_count: int,
    bar_diameter_mm: float | None = None,
    ast_mm2: float | None = None,
    is_designed_flag: bool | None = None,
    selection_approved: bool = False,
    has_lap_splice_at_section: bool = False,
) -> dict[str, Any]:
    """Classify and gate column longitudinal reinforcement (F03: CHK-117).

    Roles:
    - TEMPLATE: ETABS section property template when IsDesigned=Yes (e.g. 12Phi20,
      rho=0.589%). Never treated as as-built/selected reinforcement, and flagged
      with would_fail_if_selected=True when rho < 1%.
    - PROPOSED: Candidate constructible cage (e.g. 16Phi24, rho=1.131%). Evaluated
      as scenario only; formal_compliance remains NOT_PROVEN until selected.
    - SELECTED: Actual selected / as-built reinforcement. Enforces TBDY 7.3.2.1
      (0.01 <= rho <= 0.04, or <= 0.06 at lap splices) and produces explicit FAIL
      when violated.
    """
    if role not in ("TEMPLATE", "PROPOSED", "SELECTED"):
        raise ValueError(f"INVALID_REINFORCEMENT_ROLE:{role}")
    ac = finite(ac_mm2, "ac_mm2")
    if ac <= 0:
        raise BankError("POSITIVE_AC_REQUIRED")
    if type(bar_count) is not int or bar_count <= 0:
        raise BankError("POSITIVE_INT_BAR_COUNT_REQUIRED")

    if ast_mm2 is None:
        if bar_diameter_mm is None or bar_diameter_mm <= 0:
            raise BankError("BAR_DIAMETER_OR_AST_REQUIRED")
        ast = bar_count * math.pi * (float(bar_diameter_mm) ** 2) / 4.0
    else:
        ast = float(finite(ast_mm2, "ast_mm2"))

    rho = ast / ac
    rho_min = 0.01
    rho_max = 0.06 if has_lap_splice_at_section else 0.04

    reasons: list[str] = []
    if rho < rho_min:
        reasons.append("RHO_BELOW_TBDY_MIN_001")
    if rho > rho_max:
        reasons.append("RHO_ABOVE_TBDY_MAX")
    if bar_count < 4:
        reasons.append("BAR_COUNT_BELOW_MIN_4")
    if bar_diameter_mm is not None and bar_diameter_mm < 14:
        reasons.append("BAR_DIAMETER_BELOW_TBDY_MIN_14MM")

    geom_ok = not reasons

    if role == "TEMPLATE":
        return {
            "canonical_id": "TBDY2018:7.3.2.1:LONGITUDINAL_REBAR_LIMITS:COLUMN:2018",
            "check_code": "CHK-117",
            "role": "TEMPLATE",
            "etabs_is_designed_to_be_designed": bool(is_designed_flag),
            "bar_count": bar_count,
            "bar_diameter_mm": bar_diameter_mm,
            "ast_mm2": ast,
            "ac_mm2": ac,
            "rho": rho,
            "rho_min": rho_min,
            "rho_max": rho_max,
            "would_fail_if_selected": not geom_ok,
            "status": "TEMPLATE_ONLY_NOT_SELECTED_CAGE",
            "formal_compliance": "NOT_PROVEN",
            "selection_approved": False,
            "reason_codes": ["ETABS_IS_DESIGNED_TEMPLATE_NOT_AS_BUILT"] + reasons,
        }

    if role == "PROPOSED":
        return {
            "canonical_id": "TBDY2018:7.3.2.1:LONGITUDINAL_REBAR_LIMITS:COLUMN:2018",
            "check_code": "CHK-117",
            "role": "PROPOSED",
            "bar_count": bar_count,
            "bar_diameter_mm": bar_diameter_mm,
            "ast_mm2": ast,
            "ac_mm2": ac,
            "rho": rho,
            "rho_min": rho_min,
            "rho_max": rho_max,
            "status": "FAIL" if not geom_ok else "PROPOSED_SCENARIO_ONLY",
            "formal_compliance": "FAIL" if not geom_ok else "NOT_PROVEN",
            "selection_approved": False,
            "reason_codes": reasons if not geom_ok else ["PROPOSED_CAGE_AWAITING_DESIGN_APPROVAL"],
        }

    # role == "SELECTED"
    return {
        "canonical_id": "TBDY2018:7.3.2.1:LONGITUDINAL_REBAR_LIMITS:COLUMN:2018",
        "check_code": "CHK-117",
        "role": "SELECTED",
        "bar_count": bar_count,
        "bar_diameter_mm": bar_diameter_mm,
        "ast_mm2": ast,
        "ac_mm2": ac,
        "rho": rho,
        "rho_min": rho_min,
        "rho_max": rho_max,
        "status": "FAIL" if not geom_ok else ("SELECTED_WITHIN_LIMITS" if selection_approved else "SELECTED_UNAPPROVED"),
        "formal_compliance": "FAIL" if not geom_ok else "NOT_PROVEN",
        "selection_approved": bool(selection_approved and geom_ok),
        "reason_codes": reasons,
    }


# ---------------------------------------------------------------------------
# F07: Transverse Reinforcement Leg Topology (CHK-123, TBDY 7.3.4.1(a))
# ---------------------------------------------------------------------------

def evaluate_transverse_leg_topology(
    *,
    b_min_mm: float,
    longitudinal_bar_diameter_mm: float,
    transverse_bar_diameter_mm: float,
    vertical_spacing_s_mm: float | None,
    face_bar_coords_mm: Sequence[float] | None,
    tied_bar_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Evaluate TBDY 2018 §7.3.4.1(a) transverse leg spacing a_i and hoop spacing s (F07: CHK-123).

    Distinguishes:
    - Horizontal distance between adjacent stirrup/crosstie legs:
        a_i <= 25 * phi_transverse (e.g., 300 mm for Phi12, 250 mm for Phi10).
        168 mm bar center spacing is NOT an automatic a_i > 150 mm failure!
    - Vertical hoop/crosstie spacing in confinement zones:
        50 mm <= s <= min(b_min / 3, 6 * phi_longitudinal, 150 mm).
    """
    b_min = finite(b_min_mm, "b_min_mm")
    phi_l = finite(longitudinal_bar_diameter_mm, "longitudinal_bar_diameter_mm")
    phi_e = finite(transverse_bar_diameter_mm, "transverse_bar_diameter_mm")
    s_mm = None if vertical_spacing_s_mm is None else finite(vertical_spacing_s_mm, "vertical_spacing_s_mm")
    if min(b_min, phi_l, phi_e) <= 0 or (s_mm is not None and s_mm <= 0):
        raise BankError("POSITIVE_TRANSVERSE_INPUTS_REQUIRED")

    ai_limit_mm = 25.0 * phi_e
    coords = sorted(float(finite(c, "bar_coord")) for c in face_bar_coords_mm) if face_bar_coords_mm is not None else []
    tied_idx, tied_coords, leg_spacings_ai, bar_center_spacings = [], [], [], []
    max_ai_mm = ai_met = None
    if face_bar_coords_mm is not None and len(coords) < 2:
        raise BankError("AT_LEAST_TWO_FACE_BARS_REQUIRED")
    if tied_bar_indices is not None:
        tied_idx = sorted(set(int(i) for i in tied_bar_indices))
        if 0 not in tied_idx or (len(coords) - 1) not in tied_idx:
            raise BankError("CORNER_BARS_MUST_BE_TIED_BY_PERIMETER_HOOP")
        if any(i < 0 or i >= len(coords) for i in tied_idx):
            raise BankError("TIED_BAR_INDEX_OUT_OF_RANGE")
        tied_coords = [coords[i] for i in tied_idx]
        leg_spacings_ai = [right - left for left, right in zip(tied_coords, tied_coords[1:])]
        bar_center_spacings = [right - left for left, right in zip(coords, coords[1:])]
        max_ai_mm = max(leg_spacings_ai)
        ai_met = max_ai_mm <= ai_limit_mm + 1e-9

    s_max_b3 = b_min / 3.0
    s_max_6phi = 6.0 * phi_l
    s_max_150 = 150.0
    s_upper_limit_mm = min(s_max_b3, s_max_6phi, s_max_150)
    s_lower_limit_mm = 50.0
    s_met = None if s_mm is None else (s_lower_limit_mm - 1e-9) <= s_mm <= (s_upper_limit_mm + 1e-9)

    reasons: list[str] = []
    if ai_met is False:
        reasons.append("AI_EXCEEDS_25_PHI_TRANSVERSE")
    if ai_met is None:
        reasons.append("TRANSVERSE_LEG_COORDINATES_NOT_OBSERVED")
    if s_mm is None:
        reasons.append("VERTICAL_TIE_SPACING_NOT_OBSERVED")
    else:
        if s_mm < s_lower_limit_mm - 1e-9:
            reasons.append("S_BELOW_50MM_MIN")
        if s_mm > s_max_150 + 1e-9:
            reasons.append("S_EXCEEDS_150MM_MAX")
        if s_mm > s_max_6phi + 1e-9:
            reasons.append("S_EXCEEDS_6_PHI_LONGITUDINAL")
        if s_mm > s_max_b3 + 1e-9:
            reasons.append("S_EXCEEDS_B_MIN_OVER_3")

    failed = ai_met is False or s_met is False
    status = "WITHIN_TOPOLOGY_LIMITS"
    if failed:
        status = "FAIL"
    elif ai_met is None or s_met is None:
        status = "NOT_PROVEN"
    return {
        "canonical_id": "TBDY2018:7.3.4.1:CONFINEMENT_ZONE_TRANSVERSE_REBAR:COLUMN:2018",
        "check_code": "CHK-123",
        "face_bar_coords_mm": coords,
        "tied_bar_indices": tied_idx,
        "tied_leg_coords_mm": tied_coords,
        "leg_count_per_axis": len(tied_coords) if ai_met is not None else None,
        "bar_center_spacings_mm": bar_center_spacings,
        "clear_bar_spacings_mm": [spacing - phi_l for spacing in bar_center_spacings],
        "leg_spacings_ai_mm": leg_spacings_ai,
        "max_ai_mm": max_ai_mm,
        "ai_limit_25_phi_e_mm": ai_limit_mm,
        "ai_met": ai_met,
        "vertical_spacing_s_mm": s_mm,
        "s_min_limit_mm": s_lower_limit_mm,
        "s_max_limit_mm": s_upper_limit_mm,
        "s_max_components_mm": {
            "b_min_over_3_mm": s_max_b3,
            "six_phi_l_mm": s_max_6phi,
            "absolute_150_mm": s_max_150,
        },
        "s_met": s_met,
        "status": status,
        "formal_compliance": "FAIL" if failed else "NOT_PROVEN",
        "reason_codes": reasons,
    }


# ---------------------------------------------------------------------------
# F05: Tolerant Unique Station Matching
# ---------------------------------------------------------------------------

def match_station_with_tolerance(
    prior_map: Mapping[tuple[float, float, str, float], Any],
    obj_sta_m: float,
    elm_sta_m: float,
    step_type: str,
    step_num: float,
    *,
    tol_m: float = 1e-6,
) -> tuple[tuple[float, float, str, float], Any]:
    """Match (ObjSta, ElmSta, StepType, StepNum) within tol_m while enforcing uniqueness (F05)."""
    exact_key = (obj_sta_m, elm_sta_m, step_type, step_num)
    if exact_key in prior_map:
        return exact_key, prior_map[exact_key]
    matches = [
        (k, v) for k, v in prior_map.items()
        if k[2] == step_type
        and abs(k[3] - step_num) <= tol_m
        and abs(k[0] - obj_sta_m) <= tol_m
        and abs(k[1] - elm_sta_m) <= tol_m
    ]
    if len(matches) != 1:
        raise ValueError(f"STATION_TOLERANCE_MATCH_AMBIGUOUS_OR_MISSING:{obj_sta_m}:{elm_sta_m}")
    return matches[0]


# ---------------------------------------------------------------------------
# End-to-End Column 127/C88 P0 Gate Evaluation
# ---------------------------------------------------------------------------

def evaluate_column_p0_gates(
    *,
    live: Mapping[str, Any],
    lc_run: Mapping[str, Any],
    combo: Mapping[str, Any],
    pmm_run: Mapping[str, Any],
    geometry: Mapping[str, Any],
    setup_capture: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run all P0-A, P0-B, and P0-C gates on Column 127/C88 receipts and return sealed report."""
    from .live_column import (
        IDENTITY, _gateway_ready, _material_and_cage, _profile, require, review_live_column, table, text_number, unique,
    )

    baseline = review_live_column(
        live=dict(live),
        lc_run=dict(lc_run),
        combo=dict(combo),
        pmm_run=dict(pmm_run),
        geometry=dict(geometry),
    )
    member = baseline["member"]
    section, cage = _material_and_cage(live, lc_run, member)
    col, assign, rect = _profile(live, member)
    cg = live["gateway_capture"]
    reinf_row = unique(
        table(cg, "Frame Section Property Definitions - Concrete Column Reinforcing"),
        "Name",
        assign["SectProp"],
    )

    native_dims = NativeSectionDims(
        native_t2_mm=text_number(rect["t2"], "t2") * 1000.0,
        native_t3_mm=text_number(rect["t3"], "t3") * 1000.0,
    )
    local_dims = to_local_dimensions(native_dims)
    ac_mm2 = local_dims.local2_extent_mm * local_dims.local3_extent_mm
    ast_proposed_mm2 = sum(b.area for b in section.bars)

    # These ETABS fields contain bar names. The numeric-label scenario is
    # conditional on the project's bar catalogue confirming the diameters.
    n_r2 = int(reinf_row["NumBars2Dir"])
    n_r3 = int(reinf_row["NumBars3Dir"])
    require(reinf_row.get("ReinfConfig") == "Rectangular" and min(n_r2, n_r3) >= 2,
            "RECTANGULAR_REBAR_TEMPLATE_NOT_BOUND")
    template_bar_count = 2 * (n_r2 + n_r3) - 4
    template_bar_dia = text_number(reinf_row["BarSizeLong"], "BarSizeLong")
    template_corner_dia = text_number(reinf_row["BarSizeCorn"], "BarSizeCorn")
    template_tie_dia = text_number(reinf_row["BarSizeConf"], "BarSizeConf")
    require(min(template_bar_dia, template_corner_dia, template_tie_dia) > 0,
            "POSITIVE_NUMERIC_BAR_LABELS_REQUIRED")
    template_ast = math.pi * (
        (template_bar_count - 4) * template_bar_dia**2 + 4 * template_corner_dia**2
    ) / 4
    template_bar_dia = min(template_bar_dia, template_corner_dia)
    template_tie_s_mm = text_number(reinf_row["SpacingConf"], "SpacingConf") * 1000.0
    is_designed = reinf_row.get("IsDesigned") == "Yes"

    template_state = evaluate_reinforcement_state(
        role="TEMPLATE",
        ac_mm2=ac_mm2,
        bar_count=template_bar_count,
        bar_diameter_mm=template_bar_dia,
        ast_mm2=template_ast,
        is_designed_flag=is_designed,
    )
    proposed_state = evaluate_reinforcement_state(
        role="PROPOSED",
        ac_mm2=ac_mm2,
        bar_count=int(cage["bar_count"]),
        bar_diameter_mm=float(cage["bar_diameter_mm"]),
        ast_mm2=ast_proposed_mm2,
    )
    template_state["diameter_basis"] = "ETABS_BAR_NAMES_ASSUMED_MM_FOR_SCENARIO"
    selected_if_template_used = {
        **template_state,
        "role": "HYPOTHETICAL_SELECTION",
        "status": "FAIL" if template_state["would_fail_if_selected"] else "SELECTED_UNAPPROVED",
    }

    # A longitudinal cage alone proves neither the stirrup legs nor their pitch.
    proposed_transverse = evaluate_transverse_leg_topology(
        b_min_mm=min(local_dims.local2_extent_mm, local_dims.local3_extent_mm),
        longitudinal_bar_diameter_mm=float(cage["bar_diameter_mm"]),
        transverse_bar_diameter_mm=float(cage["tie_diameter_mm"]),
        vertical_spacing_s_mm=cage.get("confinement_spacing_mm"),
        face_bar_coords_mm=None,
    )
    template_transverse = evaluate_transverse_leg_topology(
        b_min_mm=min(local_dims.local2_extent_mm, local_dims.local3_extent_mm),
        longitudinal_bar_diameter_mm=template_bar_dia,
        transverse_bar_diameter_mm=template_tie_dia,
        vertical_spacing_s_mm=template_tie_s_mm,
        face_bar_coords_mm=None,
    )
    template_transverse.update(
        diameter_basis="ETABS_BAR_NAMES_ASSUMED_MM_FOR_SCENARIO",
        formal_compliance="NOT_PROVEN",
    )

    # F01 & F02: Station-by-station axial caps + e_min floor + PMM with e_min
    own_solver = solver(section)
    angle_deg = baseline["r08"]["geometry"]["local_axis_rotation_deg"]
    station_gates = []
    for st in baseline["r07"]["stations"]:
        nd_compression_kn = -float(st["signed_P_kN"])
        m2_raw = float(st["signed_M2_kNm"])
        m3_raw = float(st["signed_M3_kNm"])
        emin_res = apply_minimum_eccentricity(
            nd_kn=nd_compression_kn,
            m2_knm=m2_raw,
            m3_knm=m3_raw,
            dims=local_dims,
            local_axis_angle_deg=angle_deg,
        )
        pmm_with_emin = own_solver.assess(
            nd_compression_kn * 1000.0,
            emin_res["m2_design_knm"] * 1e6,
            emin_res["m3_design_knm"] * 1e6,
        )
        axial_res = evaluate_axial_caps(
            nd_kn=nd_compression_kn,
            fck_mpa=section.material.fck,
            fcd_mpa=section.material.fcd,
            fyd_mpa=section.material.fyd,
            ac_mm2=ac_mm2,
            ast_mm2=ast_proposed_mm2,
            is_seismic_combo=False,
            pmm_utilization=pmm_with_emin["utilization"],
        )
        station_gates.append({
            "object_station_m": st["object_station_m"],
            "element_station_m": st["element_station_m"],
            "nd_compression_kn": nd_compression_kn,
            "raw_pmm_utilization": st["numeric_utilization"],
            "e_min_gate": emin_res,
            "pmm_with_e_min_utilization": pmm_with_emin["utilization"],
            "pmm_with_e_min_status": pmm_with_emin["status"],
            "axial_cap_gate": axial_res,
        })

    # LC_DL single-station e_min + PMM check
    lc_forces = live["native_force_row"]
    require(all(lc_forces.get(key) == live["selected_identity"][key] for key in IDENTITY),
            "LC_DL_FORCE_ROW_IDENTITY_MISMATCH")
    lc_nd_kn = -finite(lc_forces["P"], "LC_DL.P")
    lc_pmm = next(check["numeric_detail"]["owner_pmm_result"]
                  for check in lc_run["check_instances"] if check["stage"] == "R07")
    lc_emin = apply_minimum_eccentricity(
        nd_kn=lc_nd_kn,
        m2_knm=finite(lc_forces["M2"], "LC_DL.M2"),
        m3_knm=finite(lc_forces["M3"], "LC_DL.M3"),
        dims=local_dims,
        local_axis_angle_deg=angle_deg,
    )
    lc_pmm_emin = own_solver.assess(
        lc_nd_kn * 1000.0,
        lc_emin["m2_design_knm"] * 1e6,
        lc_emin["m3_design_knm"] * 1e6,
    )

    # F04: ModelAnalysisSetupAuditor
    if setup_capture is not None:
        _gateway_ready(setup_capture, live["model_filename"])
        require(setup_capture["payload_sha256"] == combo.get("original_combinations_capture_sha256"),
                "COMBINATION_SETUP_RECEIPT_NOT_BOUND")
    setup_audit = audit_model_analysis_setup(
        cg,
        combo_capture=setup_capture,
    )
    setup_audit["combination_capture_sha256"] = None if setup_capture is None else setup_capture["payload_sha256"]

    out = {
        "schema": "tbdy.next.p0.column-127-gate-report.v1",
        "member": member,
        "label": baseline["r08"]["geometry"]["label"],
        "story": baseline["r08"]["geometry"]["story"],
        "section_name": baseline["r08"]["geometry"]["section_name"],
        "native_dims_mm": {
            "native_t2_mm": native_dims.native_t2_mm,
            "native_t3_mm": native_dims.native_t3_mm,
        },
        "local_dims_mm": {
            "local2_extent_mm": local_dims.local2_extent_mm,
            "local3_extent_mm": local_dims.local3_extent_mm,
        },
        "baseline_reconciled_sha256": baseline["result_sha256"],
        "p0a_single_owner_contract": verify_single_owner_contract(),
        "p0b_gates": {
            "f01_axial_caps_summary": station_gates[0]["axial_cap_gate"],
            "f02_lc_dl_station0_e_min": {
                "e_min_gate": lc_emin,
                "raw_pmm_utilization": lc_pmm["utilization"],
                "pmm_with_e_min_utilization": lc_pmm_emin["utilization"],
            },
            "f02_grav_ult_stations": station_gates,
            "f03_reinforcement_states": {
                "etabs_template_12phi20": template_state,
                "proposed_scenario_16phi24": proposed_state,
                "selected_if_template_12phi20_used": selected_if_template_used,
            },
            "f07_transverse_topology": {
                "proposed_16phi24": proposed_transverse,
                "etabs_template_12phi20_phi10_s150": template_transverse,
            },
        },
        "p0c_model_analysis_setup_audit": setup_audit,
        "verdict_summary": {
            "template_12phi20_if_selected": selected_if_template_used["status"],
            "template_tie_phi10_s150": template_transverse["status"],
            "proposed_16phi24_grav_ult_raw_max_utilization": baseline["r07"]["maximum_numeric_utilization"],
            "proposed_16phi24_grav_ult_with_e_min_max_utilization": max(
                s["pmm_with_e_min_utilization"] for s in station_gates
            ),
            "analysis_setup_status": setup_audit["status"],
            "analysis_setup_verdict": setup_audit["verdict"],
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
            "production_ready": "NO",
        },
    }
    out["result_sha256"] = digest(out)
    return out
