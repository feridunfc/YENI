"""VS04 bounded, pure analysis-source arithmetic; not TBDY compliance.

Uses *observed* ETABS 23.2 field names from the live schema log.
Checks only modal T/f/omega/eigen algebra, separately signed base-reaction
components, and unqualified story-drift display scalars. All derived values
are evidence for subsequent engineering review, never an approval of ETABS
analysis generation, spectrum scaling, or story-drift code requirements.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping

from .analysis_sources import TABLES, review_analysis_sources

_PI = Decimal("3.141592653589793238462643383279502884")
_REL_TOL = Decimal("0.01")
_ABS_TOL = Decimal("0.00000001")

MODAL_FIELDS = frozenset({"Case", "Mode", "Period", "Frequency", "CircFreq", "Eigenvalue"})
BASE_FIELDS = frozenset({
    "OutputCase", "CaseType", "StepType", "StepNumber",
    "FX", "FY", "FZ", "MX", "MY", "MZ", "X", "Y", "Z"
})
DRIFT_FIELDS = frozenset({
    "Story", "OutputCase", "CaseType", "StepType", "StepNumber",
    "Direction", "Drift", "Drift/", "Label", "X", "Y", "Z"
})


def _number(v: Any, *, positive: bool = False) -> Decimal:
    if type(v) not in (str, int, float, Decimal):
        raise ValueError("NUMERIC_TYPE_NOT_ACCEPTED")
    try:
        x = Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        raise ValueError("NUMERIC_PARSE_FAILED") from None
    if not x.is_finite() or (positive and x <= 0):
        raise ValueError("NONFINITE_OR_NONPOSITIVE_NUMBER")
    return x


def _expected_units(table_key: str) -> dict[str, str]:
    if table_key == TABLES[0]:
        return {"Period": "sec", "Frequency": "cyc/sec",
                "CircFreq": "rad/sec", "Eigenvalue": "rad2/sec2"}
    if table_key == TABLES[1]:
        return {**dict.fromkeys(("FX", "FY", "FZ"), "kN"),
                **dict.fromkeys(("MX", "MY", "MZ"), "kN-m"),
                **dict.fromkeys(("X", "Y", "Z"), "m")}
    if table_key == TABLES[2]:
        # Blank units are observed but NOT affirmative dimensionless proof.
        return {"Drift": "", "Drift/": "",
                "X": "m", "Y": "m", "Z": "m"}
    raise ValueError("UNKNOWN_TABLE")


def _require_table(source: Mapping[str, Any], index: int) -> list[Mapping[str, str]]:
    key = TABLES[index]
    reviewed = review_analysis_sources(source)
    record = next((x for x in reviewed["tables"] if x["table_key"] == key), None)
    if record is None or record["status"] != "OBSERVED_UNAPPROVED":
        raise ValueError("SOURCE_TABLE_NOT_STRUCTURALLY_OBSERVED")
    table = source["tables"][key]
    fields = table["fields"]
    requirements = (MODAL_FIELDS, BASE_FIELDS, DRIFT_FIELDS)[index]
    if not requirements.issubset(set(fields)):
        raise ValueError("EXACT_OBSERVED_FIELDS_NOT_AVAILABLE")
    units = table["field_metadata"]["units_by_field"]
    if any(units.get(k) != v for k, v in _expected_units(key).items()):
        raise ValueError("EXACT_FIELD_UNIT_CONTRACT_NOT_OBSERVED")
    return table["rows"]


def _within(actual: Decimal, expected: Decimal) -> bool:
    return abs(actual - expected) <= max(_ABS_TOL, abs(expected) * _REL_TOL)


def _summary(code: str, *, rows: list[dict] | None = None, reasons: list[str] | None = None,
             captured: int = 0) -> dict:
    rows = rows or []
    reasons = reasons or []
    bad = sum(x["status"] == "NOT_PROVEN" for x in rows)
    return {
        "component": code,
        "status": ("NOT_PROVEN" if reasons or bad or not rows else
                   "SOURCE_ARITHMETIC_OBSERVED"),
        "expected_row_count": len(rows),
        "observed_row_count": len(rows) - bad,
        "captured_source_row_count": captured,
        "not_proven_row_count": bad,
        "reason_codes": reasons,
        "items": rows,
        "formal_compliance": "NOT_PROVEN",
    }


def _periods(source: Mapping[str, Any]) -> dict:
    case = (source.get("requested_cases") or {}).get("modal")
    try:
        rows = _require_table(source, 0)
    except (ValueError, KeyError, TypeError) as e:
        return _summary("MODAL_PERIOD_FREQUENCY_IDENTITY", reasons=[str(e)])
    selected = [row for row in rows if row["Case"] == case]
    if not selected:
        return _summary("MODAL_PERIOD_FREQUENCY_IDENTITY", reasons=["TARGET_MODAL_CASE_NOT_IN_TABLE"], captured=len(rows))
    seen = set()
    items: list[dict] = []
    for row in selected:
        item = {"case": case, "mode": row["Mode"],
                "period_sec": row["Period"], "frequency_cyc_sec": row["Frequency"],
                "circular_frequency_rad_sec": row["CircFreq"],
                "eigenvalue_rad2_sec2": row["Eigenvalue"], "status": "NOT_PROVEN"}
        try:
            mode = _number(row["Mode"], positive=True)
            if mode != mode.to_integral_value() or str(mode) != str(row["Mode"]).strip():
                raise ValueError("NONCANONICAL_MODAL_MODE")
            mode_int = int(mode)
            if mode_int in seen:
                raise ValueError("DUPLICATE_CASE_MODE")
            seen.add(mode_int)
            t = _number(row["Period"], positive=True)
            f = _number(row["Frequency"], positive=True)
            omega = _number(row["CircFreq"], positive=True)
            eigen = _number(row["Eigenvalue"], positive=True)
            with localcontext() as ctx:
                ctx.prec = 32
                # Three independent relationships; compare measured to
                # measured, never generate an ETABS substitute source row.
                expected_f = Decimal(1) / t
                expected_w = 2 * _PI * f
                expected_eigen = omega * omega
                item.update(
                    expected_frequency_cyc_sec=str(expected_f),
                    expected_circular_frequency_rad_sec=str(expected_w),
                    expected_eigenvalue_rad2_sec2=str(expected_eigen),
                    relative_error_f=str(abs(f - expected_f) / expected_f),
                    relative_error_omega=str(abs(omega - expected_w) / expected_w),
                    relative_error_eigen=str(abs(eigen - expected_eigen) / expected_eigen),
                )
                if not all((_within(f, expected_f),
                            _within(omega, expected_w),
                            _within(eigen, expected_eigen))):
                    raise ValueError("PERIOD_FREQUENCY_EIGEN_INCONSISTENT_OR_ROUNDED")
            item["status"] = "SOURCE_ARITHMETIC_OBSERVED"
        except (ValueError, InvalidOperation, OverflowError) as exc:
            item["reason"] = str(exc)
        items.append(item)
    modes = sorted(seen)
    reasons = []
    if modes != list(range(1, len(modes) + 1)):
        reasons.append("MODE_POPULATION_NOT_CONTIGUOUS_FROM_ONE")
    return _summary("MODAL_PERIOD_FREQUENCY_IDENTITY", rows=items,
                    reasons=reasons, captured=len(rows))


def _base_reactions(source: Mapping[str, Any], direction: str) -> dict:
    try:
        rows = _require_table(source, 1)
    except (ValueError, KeyError, TypeError) as e:
        return _summary("BASE_REACTION_" + direction, reasons=[str(e)])
    case = (source.get("requested_cases") or {}).get(
        "x_candidate" if direction == "X" else "y_candidate")
    selected = [r for r in rows if r["OutputCase"] == case and
                r["CaseType"] == "LinRespSpec" and r["StepType"] == "Max"]
    if len(selected) != 1:
        return _summary("BASE_REACTION_" + direction,
                        reasons=["RESPONSE_SPECTRUM_MAX_ROW_MISSING_OR_AMBIGUOUS"],
                        captured=len(rows))
    row = selected[0]
    item: dict[str, Any] = {
        "output_case": case, "case_type": row["CaseType"],
        "step_type": row["StepType"], "step_number": row["StepNumber"],
        "status": "NOT_PROVEN",
        "simultaneous_force_vector_proven": False,
    }
    try:
        for f in ("FX", "FY", "FZ", "MX", "MY", "MZ", "X", "Y", "Z"):
            val = _number(row[f])
            item[f] = str(val)
        axis = "FX" if direction == "X" else "FY"
        item["component"] = axis
        item["absolute_reaction_kn"] = str(abs(_number(row[axis])))
        # No equivalent-static VtE and response-spectrum scaling proof.
        item["status"] = "SOURCE_COMPONENT_OBSERVED"
        item["source_semantics"] = "COMPONENT_EXTREME_ONLY"
    except (KeyError, ValueError) as exc:
        item["reason"] = str(exc)
    # Displayed response-spectrum Max can be component envelopes; this is
    # never an algebraically concurrent signed six-component vector.
    if item["status"] == "SOURCE_COMPONENT_OBSERVED":
        item["status"] = "SOURCE_ARITHMETIC_OBSERVED"
    return _summary("BASE_REACTION_" + direction, rows=[item], captured=len(rows))


def _story_drifts(source: Mapping[str, Any], direction: str) -> dict:
    try:
        rows = _require_table(source, 2)
    except (ValueError, KeyError, TypeError) as e:
        return _summary("STORY_DRIFT_" + direction, reasons=[str(e)])
    case = (source.get("requested_cases") or {}).get(
        "x_candidate" if direction == "X" else "y_candidate")
    selected = [r for r in rows if r["OutputCase"] == case and
                r["Direction"] == direction and
                r["CaseType"] == "LinRespSpec" and r["StepType"] == "Max"]
    if not selected:
        return _summary("STORY_DRIFT_" + direction,
                        reasons=["STORY_DRIFT_CASE_DIRECTION_ROWS_MISSING"],
                        captured=len(rows))
    seen: set[tuple] = set()
    items = []
    for row in selected:
        id_fields = ("Story", "OutputCase", "CaseType", "StepType",
                     "StepNumber", "Direction", "Label", "X", "Y", "Z")
        grain = tuple(row[k] for k in id_fields)
        item = {"story": row["Story"], "source_case": case,
                "direction": direction, "label": row["Label"],
                "drift_raw": row["Drift"], "drift_reciprocal_raw": row["Drift/"],
                "status": "NOT_PROVEN", "ratio_units_approved": False,
                "effective_drift_code_check_executed": False}
        try:
            if grain in seen:
                raise ValueError("DUPLICATE_STORY_DRIFT_GRAIN")
            seen.add(grain)
            if not row["Story"].strip() or not row["Label"].strip():
                raise ValueError("STORY_DRIFT_PHYSICAL_GRAIN_MISSING")
            drift = _number(row["Drift"])
            recip = _number(row["Drift/"])
            if drift <= 0 or recip <= 0:
                raise ValueError("ZERO_OR_NEGATIVE_DRIFT_NO_RECIPROCAL")
            product = drift * recip
            item["observed_reciprocal_product"] = str(product)
            if not _within(product, Decimal(1)):
                raise ValueError("DRIFT_RECIPROCAL_DISPLAY_MISMATCH")
            item["status"] = "SOURCE_ARITHMETIC_OBSERVED"
        except (KeyError, ValueError) as exc:
            item["reason"] = str(exc)
        items.append(item)
    return _summary("STORY_DRIFT_" + direction, rows=items, captured=len(rows))


def evaluate_analysis_numerics(source: Mapping[str, Any] | None) -> dict[str, Any]:
    """Deterministically re-evaluate the raw source; never emit a code PASS.

    This is a *source arithmetic* stage. Modal modal-frequency consistency is
    not the TBDY period-bound check. Base reaction magnitudes are not code Vt
    or spectrum scale factors. ETABS Drift and Drift/ semantics and related
    story/height/role are not approved by an algebraic reciprocal equality.
    """
    baseline = {
        "stage": "VS04_ANALYSIS_NUMERIC_SOURCE",
        "formal_compliance": "NOT_PROVEN",
        "engineering_release": "NOT_READY",
        "numeric_regulatory_checks_executed": 0,
        "source_semantics_approved": False,
        "analysis_generation_proven": False,
        "scope_note": (
            "Modal T/f/omega/eigen internal identity; source-only response-"
            "spectrum base components; algebraic Drift and Drift/ consistency. "
            "No TBDY effective drift, base shear, or analysis-generation verdict."
        ),
    }
    if not isinstance(source, Mapping):
        return {**baseline, "status": "SOURCE_UNAVAILABLE", "results": []}
    review = review_analysis_sources(source)
    if review["status"] == "SOURCE_UNAVAILABLE":
        return {**baseline, "status": "SOURCE_UNAVAILABLE", "results": []}
    results = [_periods(source), _base_reactions(source, "X"),
               _base_reactions(source, "Y"), _story_drifts(source, "X"),
               _story_drifts(source, "Y")]
    good = sum(x["status"] == "SOURCE_ARITHMETIC_OBSERVED" for x in results)
    return {
        **baseline,
        "status": "SOURCE_NUMERICAL_OBSERVED_PENDING_ENGINEERING_REVIEW" if good == 5
                  else "SOURCE_NUMERICAL_PARTIAL",
        "observed_component_count": good,
        "expected_component_count": 5,
        "results": results,
        "reportable_check_count_change": 0,
    }
