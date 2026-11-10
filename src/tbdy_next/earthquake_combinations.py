"""VS10: observed 100/30 coefficients and companion-direction source coverage.

Reuse the D4 operator/reference decoder. SUM coefficients are exact rational
arithmetic; envelope alternatives are never added or converted to concurrent
force vectors. Signs, design selection, common-factor meaning and full TBDY
load-combination compliance remain unproven.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Mapping

from .physical_story_scope import _digest
from .quick_checks import CheckDefinition
from .source_control_bundle import MET, UNMET, UNKNOWN, _finish
from .spectrum_reconstruction import _capture_rows
from .story_delta import dec
from .vs05_d4_source_authority import COMBOS, SUMMARY, SPECTRUM, _case_source, _combo_source


CHECKS = (
    CheckDefinition("earthquake_100_30", "Deprem birleşimleri · %100 / %30", 5,
                    "TBDY 2018 4.4.2.1 / Denk.(4.9)", "CONDITIONAL_SOURCE_NUMERICAL"),
    CheckDefinition("earthquake_direction_pairs", "Birleşimlerde X / Y yön kapsamı", 5,
                    "TBDY 2018 4.4.2.1 / Denk.(4.9)", "CONDITIONAL_SOURCE_NUMERICAL"),
)
PANELS = {"earthquake_100_30": "earthquakeRatioPanel",
          "earthquake_direction_pairs": "earthquakePairPanel"}
NA = "NOT_APPLICABLE"


def _literal(value: Fraction) -> str:
    # Inputs are finite decimal factors; coefficient products/sums therefore
    # terminate in base ten. Ratios may repeat; display precision is separate
    # from all exact Fraction decisions and grouping keys.
    with localcontext() as ctx:
        ctx.prec = max(40, len(str(abs(value.numerator))) + 3 * len(str(value.denominator)))
        return format(Decimal(value.numerator) / Decimal(value.denominator), "f").rstrip("0").rstrip(".") if value.denominator != 1 else str(value.numerator)


def coefficient_subcondition(x: Any, y: Any) -> dict:
    fx, fy = (v if isinstance(v, Fraction) else Fraction(dec(v, "HORIZONTAL_COEFFICIENT")) for v in (x, y))
    ax, ay = abs(fx), abs(fy)
    major, minor = max(ax, ay), min(ax, ay)
    if major == 0:
        raise ValueError("BOTH_SELECTED_HORIZONTAL_COEFFICIENTS_ZERO")
    return {"coefficient_x": _literal(fx), "coefficient_y": _literal(fy),
        "dominant_direction": "X" if ax > ay else "Y" if ay > ax else "TIED",
        "common_factor": _literal(major), "minor_major_ratio": _literal(minor / major),
        "ratio_limit": "0.3", "status": MET if 10 * minor == 3 * major else UNMET,
        "sign_pattern": ("+" if fx > 0 else "-" if fx < 0 else "0") +
                        ("+" if fy > 0 else "-" if fy < 0 else "0")}


def _observed_names(tables: Any) -> list[str | None]:
    raw = tables.get(COMBOS) if isinstance(tables, Mapping) else None
    rows = raw.get("rows") if isinstance(raw, Mapping) else None
    if not isinstance(rows, list):
        return [None]
    names = []
    for index, row in enumerate(rows):
        name = row.get("Name") if isinstance(row, Mapping) else None
        name = name if isinstance(name, str) and name else f"UNRESOLVED_SOURCE_ROW_{index}"
        if name not in names:
            names.append(name)
    return names or [None]


def _graph_rows(graph: Mapping[str, Any], summary: Mapping[str, Any],
                x_case: str, y_case: str) -> list[dict]:
    """Scalar coefficients only; reject nonlinear descendants and ambiguity."""
    warnings = set(summary["source_warnings"])
    memo = {}

    def validate(name: str, stack: frozenset[str]) -> None:
        if name in stack:
            raise ValueError("CYCLIC_SOURCE_COMBINATION")
        g = graph[name]
        if any(prefix + name in warnings for prefix in (
                "NONCONTIGUOUS_COMBO_DEFINITION:", "INCONSISTENT_REPEATED_OPERATOR:",
                "CONTINUATION_OPERATOR_CONTRADICTION:")):
            raise ValueError("COMBINATION_HEADER_OR_CONTINUATION_UNRESOLVED")
        refs = [r["ref"] for r in g["rows"]]
        if len(refs) != len(set(refs)):
            # ETABS can represent repeated terms. This bounded adapter does
            # not certify their envelope/sign semantics; not a model defect.
            raise ValueError("REPEATED_REFERENCE_UNSUPPORTED_BY_SCALAR_ADAPTER")
        if g["operator_candidate"] not in ("SUM", "ENVELOPE"):
            raise ValueError("COMBINATION_OPERATOR_UNSUPPORTED_BY_SCALAR_ADAPTER")
        for term in g["rows"]:
            if term["ref_type"] == "UNKNOWN":
                raise ValueError("UNRESOLVED_COMBINATION_REFERENCE:" + term["ref"])
            if term["ref_type"] == "COMBO":
                validate(term["ref"], stack | {name})

    def flatten(name: str) -> tuple[dict[str, Fraction], set[str]]:
        if name in memo:
            return memo[name]
        g = graph[name]
        if g["operator_candidate"] != "SUM":
            raise ValueError("NON_SUM_ANCESTOR_CANNOT_FORM_LINEAR_COEFFICIENTS")
        coefficients, referenced = {}, set()
        for term in g["rows"]:
            factor = Fraction(term["factor"])
            if term["ref_type"] == "CASE":
                child, refs = {term["ref"]: Fraction(1)}, {term["ref"]}
            else:
                child, refs = flatten(term["ref"])
            referenced.update(refs)
            for case, value in child.items():
                coefficients[case] = coefficients.get(case, Fraction(0)) + factor * value
        memo[name] = coefficients, referenced
        return coefficients, referenced

    result = []
    for name in sorted(graph):
        g = graph[name]
        item = {"combination": name, "operator": g["operator_etabs"], "status": UNKNOWN,
                "source_terms": g["rows"], "reason": None, "scope": "SELECTED_RS_PAIR_ONLY"}
        try:
            validate(name, frozenset())
            if g["operator_candidate"] == "ENVELOPE":
                item.update(status=NA, reason="ENVELOPE_ALTERNATIVES_NOT_A_SINGLE_LINEAR_COMBINATION",
                            envelope_alternatives=g["rows"])
            else:
                coefficients, refs = flatten(name)
                item["case_coefficients"] = {k: _literal(v) for k, v in sorted(coefficients.items())}
                if not ({x_case, y_case} & refs):
                    item.update(status=NA, reason="OUTSIDE_SELECTED_RS_PAIR_SCOPE")
                else:
                    x, y = coefficients.get(x_case, Fraction(0)), coefficients.get(y_case, Fraction(0))
                    item.update(coefficient_subcondition(x, y))
                    other = {k: v for k, v in sorted(coefficients.items()) if k not in (x_case, y_case) and v}
                    factor = max(abs(x), abs(y))
                    signature = {"selected_cases": [x_case, y_case], "common_factor_exact": str(factor),
                                 "other_case_coefficients_exact": {k: str(v) for k, v in other.items()}}
                    item.update(context_sha256=_digest(signature),
                                other_case_coefficients={k: _literal(v) for k, v in other.items()})
        except (ValueError, KeyError, TypeError, ArithmeticError, RecursionError) as exc:
            item.update(status=UNKNOWN, reason=str(exc))
        result.append(item)
    return result


def companion_coverage(items: list[dict]) -> list[dict]:
    """Match exact other-case coefficients/common factor, never combo names."""
    contexts = {}
    unresolved = [row for row in items if row["status"] == UNKNOWN]
    for row in items:
        key = row.get("context_sha256")
        if key is None or row["status"] == UNKNOWN:
            continue
        group = contexts.setdefault(key, {"context_sha256": key,
            "common_factor": row["common_factor"], "other_case_coefficients": row["other_case_coefficients"],
            "x_combinations": [], "y_combinations": [], "unqualified_combinations": [],
            "observed_sign_patterns": [], "status": UNKNOWN})
        if row["status"] == MET:
            group["x_combinations" if row["dominant_direction"] == "X" else "y_combinations"].append(row["combination"])
        else:
            group["unqualified_combinations"].append(row["combination"])
        if row["sign_pattern"] not in group["observed_sign_patterns"]:
            group["observed_sign_patterns"].append(row["sign_pattern"])
    for group in contexts.values():
        missing = [d for d, key in (("X", "x_combinations"), ("Y", "y_combinations")) if not group[key]]
        group["missing_directions"] = missing
        group["status"] = (UNKNOWN if missing and unresolved else UNMET if missing else MET)
        group["reason"] = ("SOURCE_GAPS_MAY_HIDE_COMPANION" if missing and unresolved else
                           "NO_QUALIFIED_COMPANION_IN_OBSERVED_CONTEXT" if missing else None)
        group["full_sign_envelope"] = UNKNOWN
    rows = list(contexts.values())
    # Unknown definitions cannot disappear merely because a context cannot be
    # constructed. These are unresolved context records, not invented families.
    rows.extend({"context_sha256": None, "unresolved_combination": row["combination"],
                 "status": UNKNOWN, "reason": row["reason"], "full_sign_envelope": UNKNOWN}
                for row in unresolved)
    if not rows:
        rows = [{"context_sha256": None, "status": NA,
                 "reason": "NO_LINEAR_SELECTED_RS_CONTEXT_OBSERVED", "full_sign_envelope": UNKNOWN}]
    return rows


def bind_earthquake_combinations(snapshot: Mapping[str, Any]) -> dict:
    basis = snapshot.get("vs04_basis_probe")
    tables = basis.get("table_reads") if isinstance(basis, Mapping) else None
    names = _observed_names(tables)
    rows, source_graph = [], None
    x_case = y_case = None
    try:
        if (not isinstance(basis, Mapping) or basis.get("schema") != "tbdy.next.vs04e.basis-source-probe.v1"
                or basis.get("read_only_invariant_proven") is not True
                or basis.get("units_before") != 6 or basis.get("units_after") != 6
                or basis.get("display_cases_before") != basis.get("display_cases_after")
                or not isinstance(tables, Mapping)):
            raise ValueError("COMBINATION_CAPTURE_CONTEXT_INVALID")
        _capture_rows(tables.get(COMBOS), COMBOS, ("Name", "Type", "LoadName", "SF", "GUID"), {"SF": ""})
        _capture_rows(tables.get(SUMMARY), SUMMARY, ("Name", "Type", "GUID"), {})
        definitions = _capture_rows(tables.get(SPECTRUM), SPECTRUM,
            ("Name", "ModalCase", "LoadName", "Function", "CoordSys", "Angle"), {"Angle": "deg"})
        book = _case_source(tables)
        capture = snapshot.get("next_capture")
        if (not isinstance(capture, Mapping) or capture.get("schema") != "tbdy.next.vs03.capture.v1"
                or capture.get("units_before") != 6 or capture.get("units_after") != 6
                or capture.get("case_selection_restored") is not True):
            raise ValueError("SELECTED_RS_CASE_CAPTURE_INVALID")
        x_case, y_case = capture.get("x_case"), capture.get("y_case")
        if not isinstance(x_case, str) or not isinstance(y_case, str) or not x_case or not y_case or x_case == y_case:
            raise ValueError("SELECTED_RS_CASE_IDENTITIES_INVALID")
        for name, axis in ((x_case, "U1"), (y_case, "U2")):
            match = [r for r in definitions if r["Name"] == name]
            if len(match) != 1 or name not in book["cases"]:
                raise ValueError("SELECTED_RS_CASE_DEFINITION_AMBIGUOUS_OR_MISSING")
            row = match[0]
            if (book["cases"][name]["type"] != "Response Spectrum" or row["LoadName"] != axis
                    or row["CoordSys"] != "Global" or dec(row["Angle"], "AXIS_ANGLE") != 0
                    or book["cases"].get(row["ModalCase"], {}).get("type") not in ("Modal - Ritz", "Modal - Eigen")
                    or row["Function"] in ("", "None") or row["Function"] != row["Function"].strip()):
                raise ValueError("SELECTED_RS_DIRECTION_ROLE_UNRESOLVED")
        source_graph = _combo_source(tables, book["cases"], include_graph=True)
        rows = _graph_rows(source_graph["typed_graph"], source_graph, x_case, y_case)
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, RecursionError) as exc:
        rows = [{"combination": name, "status": UNKNOWN, "reason": str(exc)} for name in names]
    provenance = {"basis_probe_sha256": _digest(basis), "selected_rs_cases": {"X": x_case, "Y": y_case},
                  "typed_graph_source_hash": source_graph["typed_graph_source_hash"] if source_graph else None}
    notes = [
        "Denk.(4.9) için seçili gerçek X/Y spektrum vakalarının katsayı mutlak değerleri karşılaştırılır. Ortak çarpan 1 veya 2,5 olabilir; anlamı otomatik D kabul edilmez.",
        "Yalnız Linear Add zinciri cebirsel katsayılara açılır. Zarf alternatifleri toplanmaz; iç içe zarf veya desteklenmeyen işlem görünür NOT_PROVEN kalır.",
        "Aynı diğer vaka katsayıları ve aynı pozitif ortak çarpanda iki baskın yön aranır. Birleşim adları sınıflandırma veya eşleştirme için kullanılmaz.",
        "Oran ve iki yönün kaynakta gözlenmesi; ± işaret zarfını, tasarımda seçilmeyi, 4.10 iç kuvvet kurallarını veya aynı anda oluşan kuvvet vektörünü kanıtlamaz.",
        "Seçili RS çiftini içermeyen birleşimler yalnız bu çiftin kapsamı dışındadır; deprem dışı oldukları sonucuna varılmaz.",
    ]
    gaps = ["FULL_PLUS_MINUS_SIGN_ENVELOPE_NOT_PROVEN", "DESIGN_COMBINATION_SELECTION_NOT_PROVEN",
            "COMMON_FACTOR_MEANING_AND_EQ_4_10_EFFECTS_NOT_PROVEN",
            "GRAVITY_VERTICAL_SEISMIC_AND_OTHER_ACTION_RULES_NOT_EVALUATED",
            "CASE_RESULT_CONCURRENCE_AND_ANALYSIS_GENERATION_NOT_PROVEN"]
    ratio = _finish(CHECKS[0], rows, notes=notes, gaps=gaps, provenance=provenance)
    pairs = _finish(CHECKS[1], companion_coverage(rows), notes=notes, gaps=gaps, provenance=provenance)
    result = {"schema": "tbdy.next.vs10.earthquake-combinations.v1", "checks": [ratio, pairs],
        "observed_combination_count": len(names) if names != [None] else 0,
        "coverage_known": source_graph is not None, "parsed_combination_count":
            source_graph["parsed_combination_count"] if source_graph else 0,
        "operator_counts": source_graph["operator_counts"] if source_graph else {},
        "resolved_context_count": sum(r.get("context_sha256") is not None for r in pairs["items"]),
        "unresolved_context_count": sum(r["status"] == UNKNOWN for r in pairs["items"]),
        "source_gate": "COMBINATION_DEFINITION_GATE", "formal_compliance": UNKNOWN,
        "engineering_release": "NOT_READY", "dag_execution_authority": "DENIED"}
    return {**result, "result_sha256": _digest(result)}
