"""VS04-I: independent source-value reconstruction for TSC2018 / ETABS modal spectrum.

TBDY 2018 horizontal elastic spectrum (Eq 2.2), reduction function
(Eq 4.1), SaR=Sae/Ra (Eq 4.8). Check the 26 displayed function ordinates
against the analytical function, then the 200 selected RSX/RSY modal
accelerations against *piecewise-linear interpolation of the stored function*
at T=2*pi/omega (not the coarsely displayed Period).

All error limits below derive solely from source decimal display intervals;
no arbitrary wide percentage tolerance. This module NEVER certifies a
regulatory analysis, applied accidental eccentricity, base shear or drift.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from itertools import product
from typing import Any, Mapping

PI = Decimal("3.14159265358979323846264338327950288419716939937510")
FUNCTION = "Functions - Response Spectrum - TSC-2018"
CASES = "Load Case Definitions - Response Spectrum"
MODAL = "Response Spectrum Modal Info"
SOURCE_ONLY = "SOURCE_NUMERICAL_RECONSTRUCTED_PENDING_ENGINEERING_REVIEW"


def _d(value: Any, name: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or not value or value == "None":
        raise ValueError(name + ":VALUE_NOT_PRINTED")
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(name + ":NOT_DECIMAL") from None
    if not number.is_finite() or (positive and number <= 0):
        raise ValueError(name + ":NONFINITE_OR_NONPOSITIVE")
    return number


def _half(value: str, name: str) -> Decimal:
    number = _d(value, name)
    return Decimal(1).scaleb(number.as_tuple().exponent) / Decimal(2)


def _capture_rows(rec: Any, key: str, fields: tuple[str, ...],
                  units: Mapping[str, str]) -> list[dict]:
    if not isinstance(rec, dict) or rec.get("table_key") != key or rec.get("status") != "CAPTURED":
        raise ValueError("TABLE_NOT_CAPTURED:" + key)
    columns, rows, meta = rec.get("fields"), rec.get("rows"), rec.get("field_metadata")
    if (not isinstance(columns, list) or len(columns) != len(set(columns))
            or not set(fields).issubset(columns) or not isinstance(rows, list)
            or type(rec.get("row_count")) is not int or len(rows) != rec["row_count"]
            or not rows or not isinstance(meta, dict) or meta.get("status") != "OK"
            or not isinstance(meta.get("field_keys"), list)
            or not set(columns).issubset(meta["field_keys"])
            or not isinstance(meta.get("units_by_field"), dict)
            or any(meta["units_by_field"].get(k) != v for k, v in units.items())
            or any(not isinstance(r, dict) or set(r) != set(columns)
                   or any(not isinstance(v, str) for v in r.values()) for r in rows)):
        raise ValueError("CAPTURED_ROW_OR_UNIT_CONTRACT_INVALID:" + key)
    return rows


def _spectrum(T: Decimal, *, sds: Decimal, sd1: Decimal,
              R: Decimal, D: Decimal, I: Decimal, TL: Decimal) -> Decimal:
    if T < 0:
        raise ValueError("NEGATIVE_PERIOD")
    ta = Decimal("0.2") * sd1 / sds
    tb = sd1 / sds
    if not (0 < ta < tb < TL) or R / I < D:
        raise ValueError("INVALID_SPECTRUM_PARAMETERS")
    if T <= ta:
        sae = (Decimal("0.4") + Decimal("0.6") * T / ta) * sds
    elif T <= tb:
        sae = sds
    elif T <= TL:
        sae = sd1 / T
    else:
        sae = sd1 * TL / (T * T)
    ra = D + (R / I - D) * T / tb if T <= tb else R / I
    return sae / ra


def _interpolate(knots: list[tuple[Decimal, Decimal, Decimal]],
                 t: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    for (t0, v0, h0), (t1, v1, h1) in zip(knots, knots[1:]):
        if t0 <= t <= t1:
            a = (t - t0) / (t1 - t0)
            return (v0 + (v1 - v0) * a,
                    (Decimal(1) - a) * h0 + a * h1,
                    t1 - t0)
    raise ValueError("MODAL_PERIOD_OUTSIDE_AVAILABLE_FUNCTION_RANGE")


def _predict_interval(
    Tlo: Decimal, Thi: Decimal, ta_range: tuple[Decimal, Decimal],
    tb_range: tuple[Decimal, Decimal],
    base_knots: list[tuple[Decimal, Decimal, Decimal]],
    scale: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    lo = None
    hi = None
    central = None
    for ta, tb in product(ta_range, tb_range):
        knots = list(base_knots)
        knots[1] = (ta, knots[1][1], knots[1][2])
        knots[2] = (tb, knots[2][1], knots[2][2])
        if not (knots[0][0] < ta < tb < knots[3][0]):
            raise ValueError("RECONSTRUCTED_CORNER_ORDER_CONFLICT")
        if Thi >= tb:
            raise ValueError("MODE_PERIOD_CROSSES_TB_NOT_IN_CURRENT_BOUNDED_SCOPE")
        sample_times = [Tlo, Thi]
        if Tlo <= ta <= Thi:
            sample_times.append(ta)
        for t in sample_times:
            value, err, _ = _interpolate(knots, t)
            observed_lo = scale * (value - err)
            observed_hi = scale * (value + err)
            lo = observed_lo if lo is None else min(lo, observed_lo)
            hi = observed_hi if hi is None else max(hi, observed_hi)
    with localcontext() as ctx:
        ctx.prec = 45
        ta = (ta_range[0] + ta_range[1]) / 2
        tb = (tb_range[0] + tb_range[1]) / 2
        knots = list(base_knots)
        knots[1] = (ta, knots[1][1], knots[1][2])
        knots[2] = (tb, knots[2][1], knots[2][2])
        middle = (Tlo + Thi) / 2
        central = _interpolate(knots, middle)[0] * scale
    assert lo is not None and hi is not None
    return lo, hi, central


def review_spectrum_reconstruction(
    basis: Mapping[str, Any] | None,
    modal_info: Mapping[str, Any] | None,
    prior_modal: Mapping[str, Any] | None,
) -> dict[str, Any]:
    base = {"stage": "VS04I_TSC2018_SPECTRUM_SOURCE_RECONSTRUCTION",
            "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
            "regulatory_checks_executed": 0, "analysis_generation_proven": False,
            "spectrum_scale_code_approved": False,
            "accidental_eccentricity_applied_proven": False}
    try:
        if (not isinstance(basis, Mapping) or basis.get("schema") != "tbdy.next.vs04e.basis-probe-receipt.v1"
                or not isinstance(modal_info, Mapping) or
                modal_info.get("schema") != "tbdy.next.vs04g.diaphragm-source-receipt.v1" or
                not isinstance(prior_modal, Mapping) or
                prior_modal.get("schema") != "tbdy.next.vs04.offline-source-replay.v1"):
            raise ValueError("THREE_EXACT_SOURCE_RECEIPTS_REQUIRED")
        e = basis["source"]
        g = modal_info["source"]
        if (e.get("schema") != "tbdy.next.vs04e.basis-source-probe.v1"
                or g.get("schema") != "tbdy.next.vs04g.diaphragm-modal-probe.v1"
                or e.get("units_before") != e.get("units_after") != 6):
            # the precise units check is repeated below; do not bypass it
            raise ValueError("SOURCE_SCHEMA_OR_UNIT_STATE_INVALID")
        if (e.get("units_before") != 6 or
                g.get("units_before") != g.get("units_after") or
                g.get("units_before") != 6 or
                e.get("read_only_invariant_proven") is not True or
                g.get("display_selection_restored") is not True or
                g.get("temporary_display_cases") != ["RSX", "RSY"] or
                e.get("analysis_generation_proven") is not False or
                g.get("analysis_generation_proven") is not False):
            raise ValueError("CAPTURE_INVARIANT_INVALID")

        tables = e["table_reads"]
        spectrum = _capture_rows(
            tables[FUNCTION], FUNCTION,
            ("Name", "Period", "Value", "SDS", "SD1", "R", "D", "I", "TL"),
            {"Period": "sec", "Value": ""})
        cs = _capture_rows(
            tables[CASES], CASES,
            ("Name", "LoadName", "Function", "TransAccSF", "ModalCase"),
            {"TransAccSF": "m/sec2"})
        selected = _capture_rows(
            g["spectrum_modal_selected_cases"], MODAL,
            ("SpecCase", "ModalCase", "Mode", "Period", "DampRatio",
             "U1Acc", "U2Acc", "U3Acc", "U1Amp", "U2Amp", "U3Amp"),
            {"Period": "sec", "U1Acc": "m/sec2", "U2Acc": "m/sec2", "U3Acc": "m/sec2"})
        results = prior_modal["numeric_source_review"]["results"]
        source_modes = next((r["items"] for r in results
                             if r.get("component") == "MODAL_PERIOD_FREQUENCY_IDENTITY"
                             and r.get("status") == "SOURCE_ARITHMETIC_OBSERVED"), None)
        if not isinstance(source_modes, list) or len(source_modes) != 100:
            raise ValueError("MODAL_100_MODE_SOURCE_ARITHMETIC_MISSING")
        modes = {r["mode"]: r for r in source_modes}
        if set(modes) != set(str(i) for i in range(1, 101)):
            raise ValueError("MODAL_MODE_ID_POPULATION_INVALID")
        if (len(cs) != 2 or {r["Name"] for r in cs} != {"RSX", "RSY"} or
                any(r["ModalCase"] != "Modal" or r["Function"] != "RESP_YATAY"
                    or r["LoadName"] != ("U1" if r["Name"] == "RSX" else "U2")
                    for r in cs)):
            raise ValueError("SPECTRUM_CASE_BINDINGS_NOT_EXACT")
        scale = {}
        for r in cs:
            scale[r["Name"]] = _d(r["TransAccSF"], "TransAccSF", positive=True)
        if scale["RSX"] != scale["RSY"] or len(spectrum) != 26 or any(
                r["Name"] != "RESP_YATAY" for r in spectrum):
            raise ValueError("FUNCTION_CASE_SCALE_OR_POINT_POPULATION_NOT_EXACT")
        h = spectrum[0]
        params = {k: _d(h[k], k, positive=True)
                  for k in ("SDS", "SD1", "R", "D", "I", "TL")}
        ta = Decimal("0.2") * params["SD1"] / params["SDS"]
        tb = params["SD1"] / params["SDS"]
        sds = params["SDS"]
        sd1 = params["SD1"]
        ta_range = (Decimal("0.2") * (sd1 - _half(h["SD1"], "SD1"))
                    / (sds + _half(h["SDS"], "SDS")),
                    Decimal("0.2") * (sd1 + _half(h["SD1"], "SD1"))
                    / (sds - _half(h["SDS"], "SDS")))
        tb_range = ((sd1 - _half(h["SD1"], "SD1"))
                    / (sds + _half(h["SDS"], "SDS")),
                    (sd1 + _half(h["SD1"], "SD1"))
                    / (sds - _half(h["SDS"], "SDS")))
        points = []
        bad_knots = []
        for i, r in enumerate(spectrum):
            reported = _d(r["Period"], "Period")
            T = ta if i == 1 else tb if i == 2 else reported
            value = _d(r["Value"], "Value", positive=True)
            if (i in (1, 2) and abs(reported - T) >
                    _half(r["Period"], "Period")):
                raise ValueError("DISPLAYED_CORNER_PERIOD_DOES_NOT_ENCLOSE_DERIVED_VALUE")
            computed = _spectrum(T, sds=params["SDS"], sd1=params["SD1"],
                                 R=params["R"], D=params["D"],
                                 I=params["I"], TL=params["TL"])
            if abs(computed - value) > _half(r["Value"], "Value"):
                bad_knots.append({"row": i + 1, "observed_period": r["Period"],
                                  "observed_value": r["Value"],
                                  "reconstructed_value": str(computed)})
            if points and T <= points[-1][0]:
                raise ValueError("SPECTRUM_PERIODS_NOT_STRICTLY_INCREASING")
            points.append((T, value, _half(r["Value"], "Value")))
        if bad_knots:
            raise ValueError("TSC2018_ANALYTIC_KNOT_VALUES_INCONSISTENT")

        if len(selected) != 200:
            raise ValueError("SELECTED_SPECTRUM_MODAL_OUTPUT_NOT_200")
        seen = set()
        invalid = []
        largest = Decimal(0)
        sum_abs = Decimal(0)
        per_case = {"RSX": 0, "RSY": 0}
        for row in selected:
            key = (row["SpecCase"], row["Mode"])
            if (key in seen or key[0] not in per_case or
                    row["ModalCase"] != "Modal" or
                    _d(row["DampRatio"], "DampRatio", positive=True) != Decimal("0.05")):
                raise ValueError("DUPLICATE_OR_INVALID_RS_MODAL_KEY")
            seen.add(key)
            if row["Period"] != modes.get(row["Mode"], {}).get("period_sec"):
                raise ValueError("DIFFERENT_VS04D_VS04G_MODAL_DISPLAY_PERIOD")
            omega_text = modes[row["Mode"]]["circular_frequency_rad_sec"]
            omega = _d(omega_text, "CircFreq", positive=True)
            delta = _half(omega_text, "CircFreq")
            if omega - delta <= 0:
                raise ValueError("CIRCULAR_FREQUENCY_INTERVAL_NONPOSITIVE")
            with localcontext() as ctx:
                ctx.prec = 45
                Tlo, Thi = (2 * PI / (omega + delta),
                            2 * PI / (omega - delta))
                low, high, predicted = _predict_interval(
                    Tlo, Thi, ta_range, tb_range, points, scale[key[0]])
            axis = "U1Acc" if key[0] == "RSX" else "U2Acc"
            val = _d(row[axis], axis, positive=True)
            err = _half(row[axis], axis)
            other_cols = ("U2Acc", "U3Acc") if key[0] == "RSX" else ("U1Acc", "U3Acc")
            if any(_d(row[k], k) != 0 for k in other_cols):
                raise ValueError("CROSS_DIRECTION_SPECTRUM_ACCELERATION_NOT_ZERO")
            diff = abs(predicted - val)
            largest = max(largest, diff)
            sum_abs += diff
            per_case[key[0]] += 1
            if val + err < low or val - err > high:
                invalid.append({
                    "case": key[0], "mode": row["Mode"],
                    "displayed_acceleration": row[axis],
                    "predicted_center": str(predicted),
                    "predicted_interval": [str(low), str(high)],
                    "display_half_quantum": str(err),
                })
        if per_case != {"RSX": 100, "RSY": 100}:
            raise ValueError("MODE_CASE_COUNTS_NOT_100_EACH")
        return {**base,
                "status": SOURCE_ONLY if not invalid else "SOURCE_RECONSTRUCTION_PARTIAL",
                "source_knot_count": 26,
                "analytical_knot_consistency_count": 26,
                "modal_source_rows": 200,
                "reconstructed_modal_rows": 200 - len(invalid),
                "unexplained_modal_rows": len(invalid),
                "case_row_count": per_case,
                "derived_corner_periods_s": {"T_A": str(ta), "T_B": str(tb)},
                "comparison_basis": "DISPLAY_DECIMAL_PRECISION_BOUNDS_NO_FIXED_PERCENT_TOLERANCE",
                "max_absolute_residual_m_s2": str(largest),
                "mean_absolute_residual_m_s2": str(sum_abs / len(selected)),
                "unexplained_examples": invalid[:16],
                "mandatory_holds": [
                    "MODEL_ANALYSIS_GENERATION_NOT_QUALIFIED",
                    "APPLIED_ECCENTRICITY_AND_DIAPHRAGM_MASS_NOT_QUALIFIED",
                    "DD2_AND_DD3_DESIGN_SPECTRUM_SCOPE_NOT_QUALIFIED",
                    "TBDY_BASE_SHEAR_AND_EFFECTIVE_STORY_DRIFT_NOT_EXECUTED",
                ]}
    except (ValueError, KeyError, TypeError, ZeroDivisionError, InvalidOperation) as exc:
        return {**base, "status": "NOT_PROVEN", "reason_codes": [str(exc)],
                "modal_source_rows": 0, "reconstructed_modal_rows": 0}
