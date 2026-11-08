"""VS09: two source-ready subconditions, without changing accepted receipts.

Concrete upper strength and modal SRSS spacing reuse the captured source bank.
The modal method is distinct from directional combination. No analysis rerun,
force combination, damping approval or full engineering acceptance is issued.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any, Mapping

from .basis_linkage import SPECTRUM_CASE
from .diaphragm_probe import SCHEMA as DIAPHRAGM_SCHEMA, SPECTRUM_MODAL_TABLE
from .next_checks import _material_items
from .physical_story_scope import _digest
from .quick_checks import CheckDefinition
from .source import parse_modal_capture
from .spectrum_reconstruction import _capture_rows
from .story_delta import dec
from .story_drift_binding import _verify_generic_capture
from .story_geometry import read_source_table


CHECKS = (
    CheckDefinition("concrete_fck_80", "Beton üst dayanım sınırı ≤ 80 MPa", 1,
                    "TBDY 2018 7.1.3 / 7.2.5.3(a)", "MATERIAL_SCREENING"),
    CheckDefinition("modal_combination_spacing", "Yakın modlar · SRSS / CQC seçimi", 7,
                    "TBDY 2018 4B.2.4(d)", "SOURCE_NUMERICAL"),
)
PANELS = {"concrete_fck_80": "concreteUpperPanel",
          "modal_combination_spacing": "modalSpacingPanel"}
PERIODS = "Modal Periods And Frequencies"
MET, UNMET, UNKNOWN = "MEETS_SUBCONDITION", "DOES_NOT_MEET_SUBCONDITION", "NOT_PROVEN"


def concrete_upper_subcondition(fck_mpa: Any) -> dict:
    """Only the upper scalar bound; lower strength remains the VS03 check."""
    fck = dec(fck_mpa, "FCK_MPA")
    if fck <= 0:
        raise ValueError("FCK_MUST_BE_POSITIVE")
    return {"value": str(fck), "fck_mpa": str(fck), "limit": "80", "operator": "<=",
            "unit": "MPa", "status": MET if fck <= 80 else UNMET,
            "strength_scope_observation": "WITHIN_NUMERIC_UPPER_BOUND" if fck <= 80 else
                                          "ABOVE_TBDY_STRENGTH_SCOPE"}


def modal_spacing(periods: Mapping[int, Any]) -> dict:
    """Sorted adjacent periods suffice to prove the all-distinct-pairs bound.

    For 0 < T1 <= ... <= Tn, every nonadjacent short/long ratio is no
    larger than an intervening adjacent ratio. Equality at 0.8 fails.
    This operates on displayed source values, not unrounded solver values.
    """
    if not isinstance(periods, Mapping) or not periods:
        raise ValueError("MODAL_PERIOD_POPULATION_EMPTY")
    values = []
    for mode, raw in periods.items():
        if type(mode) is not int or mode < 1:
            raise ValueError("MODE_IDENTITY_INVALID")
        period = dec(raw, "PERIOD_SECONDS")
        if period <= 0:
            raise ValueError("PERIOD_MUST_BE_POSITIVE")
        values.append((period, mode))
    values.sort()
    pairs = []
    with localcontext() as ctx:
        ctx.prec = 35
        for (short, short_mode), (long, long_mode) in zip(values, values[1:]):
            pairs.append({"short_mode": short_mode, "long_mode": long_mode,
                "short_period_s": str(short), "long_period_s": str(long),
                "period_ratio": str(short / long), "limit": "0.8", "operator": "<",
                "status": MET if 5 * short < 4 * long else UNMET})
    unmet = sum(p["status"] == UNMET for p in pairs)
    governing = max(pairs, key=lambda p: Decimal(p["period_ratio"]), default=None)
    return {"mode_count": len(values), "all_distinct_pair_count": len(values) * (len(values) - 1) // 2,
            "tested_adjacent_pair_count": len(pairs), "unmet_adjacent_pair_count": unmet,
            "spacing_status": UNMET if unmet else MET,
            "maximum_period_ratio": governing["period_ratio"] if governing else None,
            "governing_pair": governing, "pairs": pairs,
            "pair_proof": "POSITIVE_SORTED_ADJACENT_RATIOS_BOUND_EVERY_DISTINCT_PAIR"}


def _finish(spec: CheckDefinition, rows: list[dict], *, notes: list[str],
            gaps: list[str], provenance: dict, reasons: list[str] | None = None) -> dict:
    met = sum(r["status"] == MET for r in rows)
    unmet = sum(r["status"] == UNMET for r in rows)
    unknown = len(rows) - met - unmet
    result = {**spec.as_dict(), "expected_count": len(rows), "evaluated_count": met + unmet,
        "met_count": met, "unmet_count": unmet, "not_proven_count": unknown,
        "not_applicable_count": 0, "items": rows,
        "status": UNMET if unmet else "PARTIAL" if unknown and met else
                  UNKNOWN if unknown or not rows else MET,
        "reason_codes": sorted(set((reasons or []) + [r["reason"] for r in rows if r.get("reason")])),
        "assumptions_notes": notes, "unevaluated_requirements": gaps,
        "source_provenance": provenance, "formal_compliance": UNKNOWN,
        "engineering_release": "NOT_READY", "dag_execution_authority": "DENIED"}
    return {**result, "result_sha256": _digest(result)}


def _concrete(snapshot: Mapping[str, Any]) -> dict:
    geometry, capture = snapshot.get("geometry_capture"), snapshot.get("next_capture")
    observed_types = geometry.get("material_types") if isinstance(geometry, Mapping) else None
    observed_facts = observed_types.get("facts") if isinstance(observed_types, Mapping) else None
    observed_names = []
    if isinstance(observed_facts, Mapping):
        for name, fact in observed_facts.items():
            nonconcrete = (observed_types.get("source_api") == "PropMaterial.GetTypeOAPI"
                and isinstance(fact, Mapping) and fact.get("status") == "TYPE_RESOLVED"
                and type(fact.get("material_type_code")) is int
                and fact["material_type_code"] in (1, 3, 4, 5, 6, 7, 8))
            if not nonconcrete:
                observed_names.append(str(name))
    rows, reasons = [], []
    try:
        if (not isinstance(geometry, Mapping) or geometry.get("schema") != "tbdy.next.geometry.capture.v2"
                or geometry.get("present_units") != 6 or geometry.get("present_units_after") != 6
                or geometry.get("unit_state_unchanged") is not True
                or not isinstance(capture, Mapping) or capture.get("schema") != "tbdy.next.vs03.capture.v1"
                or capture.get("units_before") != 6 or capture.get("units_after") != 6):
            raise ValueError("MATERIAL_CAPTURE_CONTEXT_INVALID")
        types = geometry.get("material_types")
        if (not isinstance(types, Mapping) or types.get("source_api") != "PropMaterial.GetTypeOAPI"
                or not isinstance(types.get("facts"), Mapping) or not types["facts"]):
            raise ValueError("MATERIAL_TYPE_POPULATION_UNAVAILABLE")
        material_table = capture.get("material_table")
        if (not isinstance(material_table, Mapping)
                or material_table.get("table_key") != "Material Properties - Concrete Data"):
            raise ValueError("MATERIAL_STRENGTH_TABLE_IDENTITY_INVALID")
        # Keep malformed facts as unresolved population; never convert them
        # to concrete or silently exclude them. The legacy evaluator is intact.
        facts, unresolved = {}, []
        for name, fact in types["facts"].items():
            if (not isinstance(name, str) or not name or name != name.strip()
                    or not isinstance(fact, Mapping) or fact.get("status") != "TYPE_RESOLVED"
                    or type(fact.get("material_type_code")) is not int
                    or fact["material_type_code"] not in range(1, 9)):
                unresolved.append({"material_name": str(name), "status": UNKNOWN,
                                   "reason": "MATERIAL_TYPE_UNRESOLVED"})
            else:
                facts[name] = dict(fact)
        safe_geometry = {**geometry, "material_types": {**types, "facts": facts}}
        if any(f["material_type_code"] == 2 for f in facts.values()):
            for previous in _material_items(capture, safe_geometry):
                item = {"material_name": previous.get("material_name"),
                        "source_units": previous.get("source_units"), "status": UNKNOWN}
                if previous.get("fck_mpa") is None:
                    item["reason"] = previous.get("reason", "MATERIAL_FC_UNRESOLVED")
                else:
                    item.update(concrete_upper_subcondition(previous["fck_mpa"]))
                rows.append(item)
        rows.extend(unresolved)
        if not rows:
            raise ValueError("NO_OBSERVED_USED_CONCRETE_MATERIAL")
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        reasons.append(str(exc))
        rows = [{"material_name": name, "status": UNKNOWN, "reason": str(exc)}
                for name in (observed_names or [None])]
    return _finish(CHECKS[0], rows, notes=[
        "Önceden gözlenen kullanılan beton malzemeleri ve aynı Fc birim dönüşümü kullanılır; malzeme adından dayanım çıkarılmaz.",
        "Bu yeni alt koşul yalnız fck ≤ 80 MPa sınırıdır; fck ≥ 25 MPa hesabı mevcut kontrolde korunur.",
        "7.2.5.3(a) deprem etkisini karşılayan betonarme elemanları kapsar. Kaynak Fc sayısı tek başına TS EN 206 sınıfı veya malzeme kabulü değildir.",
        "80 MPa üstü gözlem, sıradan dayanım yetersizliği olarak değil 7.1.3 yönetmelik dayanım kapsamının aşılması olarak işaretlenir.",
    ], gaps=["SEISMIC_RESISTING_MEMBER_APPLICABILITY_NOT_PROVEN",
             "TS_EN_206_CONCRETE_CLASS_AGE_AND_QUALITY_NOT_PROVEN",
             "FULL_MATERIAL_USAGE_POPULATION_NOT_PROVEN"],
        provenance={"material_capture_sha256": _digest(capture),
                    "material_type_facts_sha256": _digest((geometry or {}).get("material_types"))
                    if isinstance(geometry, Mapping) else None}, reasons=reasons)


def _mode(raw: Any) -> int:
    if not isinstance(raw, str) or not raw.isascii() or not raw.isdigit() or str(int(raw)) != raw or int(raw) < 1:
        raise ValueError("MODE_IDENTITY_INVALID")
    return int(raw)


def _spacing(snapshot: Mapping[str, Any]) -> dict:
    basis, probe, delta = (snapshot.get(k) for k in
                          ("vs04_basis_probe", "vs04_diaphragm_probe", "vs05_delta_source"))
    capture = snapshot.get("next_capture")
    capture = capture if isinstance(capture, Mapping) else {}
    names = [(direction, capture.get(key)) for direction, key in (("X", "x_case"), ("Y", "y_case"))]
    rows = [{"direction": d, "source_case": name, "status": UNKNOWN} for d, name in names]
    reasons = []
    try:
        if (not isinstance(basis, Mapping) or basis.get("schema") != "tbdy.next.vs04e.basis-source-probe.v1"
                or basis.get("read_only_invariant_proven") is not True
                or basis.get("units_before") != 6 or basis.get("units_after") != 6
                or basis.get("display_cases_before") != basis.get("display_cases_after")):
            raise ValueError("MODAL_BASIS_CAPTURE_CONTEXT_INVALID")
        if (not isinstance(probe, Mapping) or probe.get("schema") != DIAPHRAGM_SCHEMA
                or probe.get("display_selection_restored") is not True
                or probe.get("units_before") != 6 or probe.get("units_after") != 6):
            raise ValueError("SPECTRUM_MODAL_CAPTURE_CONTEXT_INVALID")
        if not isinstance(delta, Mapping):
            raise ValueError("SEALED_MODAL_PERIOD_SOURCE_ABSENT")
        _verify_generic_capture(delta)
        if (delta.get("schema") != "tbdy.next.etabs.generic-source-capture.v1"
                or delta.get("status") not in ("CAPTURED", "PARTIAL", "SOURCE_PARTIAL")
                or delta.get("model_locked") is not True or delta.get("model_units_code") != 6
                or delta.get("model_units_unchanged") is not True or delta.get("selection_restored") is not True):
            raise ValueError("SEALED_MODAL_PERIOD_CONTEXT_INVALID")
        model = (snapshot.get("capture_metadata") or {}).get("model_filename")
        if not isinstance(model, str) or not model or delta.get("model") != model:
            raise ValueError("MODAL_PERIOD_MODEL_CONFLICT")
        cases = _capture_rows((basis.get("table_reads") or {}).get(SPECTRUM_CASE), SPECTRUM_CASE,
                             ("Name", "ModalCase", "ModalCombo", "DirCombo", "LoadName", "CoordSys", "Angle"), {"Angle": "deg"})
        modes = _capture_rows(probe.get("spectrum_modal_selected_cases"), SPECTRUM_MODAL_TABLE,
                             ("SpecCase", "ModalCase", "Mode", "Period"), {"Period": "sec"})
        period_rows = read_source_table(delta, PERIODS, ("Case", "Mode", "Period"), {"Period": "sec"})
        if (any(not isinstance(n, str) or not n.strip() for _, n in names)
                or len({n for _, n in names}) != 2):
            raise ValueError("DIRECTIONAL_SPECTRUM_CASE_IDENTITY_INVALID")
        for item in rows:
            try:
                name = item["source_case"]
                matches = [r for r in cases if r["Name"] == name]
                # Multi-component / continuation-case adapters require their
                # own reviewed interpretation; never take the last row.
                if len(matches) != 1:
                    raise ValueError("SPECTRUM_CASE_MISSING_DUPLICATE_OR_MULTICOMPONENT")
                case = matches[0]
                item.update(modal_case=case["ModalCase"], modal_combination=case["ModalCombo"],
                            directional_combination=case["DirCombo"])
                if (case["LoadName"] != ("U1" if item["direction"] == "X" else "U2")
                        or case["CoordSys"] != "Global" or dec(case["Angle"], "ANGLE") != 0):
                    raise ValueError("SPECTRUM_DIRECTION_BINDING_UNSUPPORTED")
                mass_table = parse_modal_capture(snapshot, case=case["ModalCase"])
                expected = {r.mode for r in mass_table.rows}
                bank = {}
                for r in period_rows:
                    if r["Case"] != case["ModalCase"]:
                        continue
                    mode = _mode(r["Mode"])
                    if mode in bank:
                        raise ValueError("DUPLICATE_MODAL_PERIOD_IDENTITY")
                    bank[mode] = dec(r["Period"], "PERIOD_SECONDS")
                selected = {}
                for r in modes:
                    if r["SpecCase"] != name:
                        continue
                    mode = _mode(r["Mode"])
                    if mode in selected or r["ModalCase"] != case["ModalCase"]:
                        raise ValueError("SPECTRUM_MODAL_IDENTITY_CONFLICT")
                    selected[mode] = dec(r["Period"], "PERIOD_SECONDS")
                if set(bank) != expected or set(selected) != expected:
                    raise ValueError("MODAL_MASS_PERIOD_AND_SPECTRUM_POPULATION_CONFLICT")
                if bank != selected:
                    raise ValueError("MODAL_PERIOD_CROSS_SOURCE_CONFLICT")
                item.update(modal_spacing(bank))
                if case["ModalCombo"] not in ("SRSS", "CQC"):
                    raise ValueError("MODAL_COMBINATION_METHOD_UNSUPPORTED")
                # DirCombo='SRSS' says nothing about combination of MODES.
                item["status"] = MET if case["ModalCombo"] == "CQC" else item["spacing_status"]
                item["method_condition"] = ("CQC_SELECTED_SOURCE_ONLY" if case["ModalCombo"] == "CQC" else
                    "SRSS_SPACING_CONDITION_MET" if item["status"] == MET else "SRSS_SPACING_CONDITION_NOT_MET")
            except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
                item.update(status=UNKNOWN, reason=str(exc))
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        reasons.append(str(exc))
        for item in rows:
            item.update(status=UNKNOWN, reason=str(exc))
    return _finish(CHECKS[1], rows, notes=[
        "4B.2.4(d): farklı modların kısa/uzun periyot oranları 0,8'den küçükse SRSS seçeneği kullanılabilir. Eşitlik yeterli değildir.",
        "Pozitif periyotlar sıralanır; komşu çiftlerin en büyük oranı bütün farklı çiftleri sınırlar. Bütün seçilmiş modlar kapsama alınır.",
        "ModalCombo mod birleştirme, DirCombo yön birleştirme seçimidir. DirCombo=SRSS, modların SRSS ile birleştirildiği anlamına gelmez.",
        "CQC seçiminin gözlenmesi, korelasyon katsayıları veya birleşmiş kuvvetlerin doğrulandığı anlamına gelmez. Bu ayrıklık koşuluna ayrıca %5 sönüm şartı eklenmez.",
    ], gaps=["UNROUNDED_SOLVER_PERIODS_AND_ANALYSIS_GENERATION_NOT_PROVEN",
             "CQC_CORRELATION_DAMPING_AND_COMBINED_FORCES_NOT_EVALUATED",
             "FULL_MODAL_AND_DIRECTIONAL_ANALYSIS_COMPLIANCE_NOT_PROVEN"],
        provenance={"basis_probe_sha256": _digest(basis), "spectrum_modal_probe_sha256": _digest(probe),
                    "period_source_payload_sha256": delta.get("payload_sha256") if isinstance(delta, Mapping) else None},
        reasons=reasons)


def bind_source_controls(snapshot: Mapping[str, Any]) -> dict:
    checks = []
    if "next_capture" in snapshot:
        checks.append(_concrete(snapshot))
    if "vs04_basis_probe" in snapshot or "vs04_diaphragm_probe" in snapshot:
        checks.append(_spacing(snapshot))
    result = {"schema": "tbdy.next.vs09.source-controls.v1", "checks": checks,
              "formal_compliance": UNKNOWN, "engineering_release": "NOT_READY",
              "source_identity": snapshot.get("source_identity")}
    return {**result, "result_sha256": _digest(result)}
