"""TBDY 7.6.6.3 upper branch for slender piers, using native scalar V2 envelopes."""
import re

from .analysis_archive import _archive_bytes
from .column_spectral_shear import _model_controls
from .mixed_demands import linear_coefficients, native_graph
from .pier_force_source import ORIGINAL, force_vector, signed_vector

# Outward allowance in kN per displayed ordinate. The model capture displays four decimals.
DISPLAY_KN = 0.001


def wall_load_scope(source):
    text = _archive_bytes(source["analysis_archive"]["model_export_base64"], 2_000_000).decode("latin-1")
    names = sorted(set(re.findall(r'^\s*COMBO\s+"([^"]+)"\s+DESIGN\s+"Wall"\s+COMBOTYPE\s+"Strength"', text, re.M)))
    _, cases, graph = native_graph(source)
    static, seismic, other = {}, {}, []
    for name in names:
        try:
            terms = linear_coefficients(name, graph, cases)
        except ValueError:
            other.append(name)
            continue
        kinds = {cases[n]["type"] for n in terms}
        if kinds == {"Linear Static"}:
            static[name] = terms
        elif "Response Spectrum" in kinds and kinds <= {"Linear Static", "Response Spectrum"}:
            seismic[name] = {n: v for n, v in terms.items() if cases[n]["type"] == "Linear Static"}
        else:
            other.append(name)
    controls = _model_controls(source, seismic)
    return {"native_static": static, "native_seismic": seismic, "other": other, "controls": controls}


def envelope(rows):
    if (len(rows) != 2 or any(r.get("CaseType") != "Combination" for r in rows)
            or {r.get("StepType") for r in rows} != {"Min", "Max"}):
        raise ValueError("NATIVE_MIN_MAX_ENVELOPE_REQUIRED")
    bounds = {r["StepType"]: force_vector(r) for r in rows}
    if any(bounds["Max"][k] < v for k, v in bounds["Min"].items()):
        raise ValueError("NATIVE_PIER_ENVELOPE_REVERSED")
    return bounds


def _center_radius(bounds):
    lo, hi = bounds["Min"]["V2"], bounds["Max"]["V2"]
    return (lo + hi)/2, (hi - lo)/2


def vertical_component(scope, groups, key):
    """Isolate the EDZ shear from a native envelope centre and a matching signed gravity sum."""
    estimates = []
    for name, terms in scope["native_seismic"].items():
        factor = terms.get("EDZ")
        if not factor:
            continue
        rest = {k: v for k, v in terms.items() if k != "EDZ"}
        for gravity, loads in scope["native_static"].items():
            if loads == rest:
                center, _ = _center_radius(envelope(groups[*key, name]))
                static = signed_vector(groups[*key, gravity], ORIGINAL)["V2"]
                estimates.append(((center-static)/float(factor), 2*DISPLAY_KN/abs(float(factor))))
    if not estimates:
        raise ValueError("VERTICAL_EARTHQUAKE_SHEAR_SOURCE_UNRESOLVED")
    lo, hi = max(v-e for v, e in estimates), min(v+e for v, e in estimates)
    if lo > hi:
        raise ValueError("VERTICAL_EARTHQUAKE_COMPONENT_CONTROLS_DIFFER")
    return (lo+hi)/2, (hi-lo)/2


def upper_shear(scope, combo, groups, key, cap_roles, detail, edz):
    control = scope["controls"].get(combo) or {}
    cap = control.get("combination")
    if cap not in cap_roles:
        raise ValueError("NATIVE_WALL_COMBINATION_HAS_NO_MATCHED_D_CONTROL")
    native, amplified = envelope(groups[*key, combo]), envelope(groups[*key, cap])
    center, radius = _center_radius(native)
    cap_center, cap_radius = _center_radius(amplified)
    d = control["d_factor"]
    if abs(cap_center-center) > 2*DISPLAY_KN or abs(cap_radius - d*radius) > (1+d)*DISPLAY_KN:
        raise ValueError("AMPLIFIED_PIER_V2_ENVELOPE_CONTROL_DIFFERS")
    factor_z = float(scope["native_seismic"][combo].get("EDZ", 0))
    contribution, error = factor_z*edz[0], abs(factor_z)*edz[1]
    limits = {}
    for classification, factor, strut in (("solid", 1.2, "solid_strut_limit_kn"), ("coupled", 1.4, "coupled_strut_limit_kn")):
        # cap_radius already contains the horizontal D. Retain both possible treatments
        # of the signed vertical-earthquake term and use the larger upper bound.
        fixed_z = abs(cap_center) + factor*cap_radius
        scaled_z = abs(cap_center + (factor*d-1)*contribution) + factor*cap_radius
        allowance = (1+factor)*DISPLAY_KN + abs(factor*d-1)*error
        upper = max(fixed_z, scaled_z) + allowance
        resistance = min(detail["vr_kn"], detail[strut])
        limits[classification] = {"fixed_edz_upper_kn": fixed_z, "scaled_edz_upper_kn": scaled_z,
                                  "outward_allowance_kn": allowance, "ve_upper_kn": upper,
                                  "resistance_kn": resistance, "upper_utilization": upper/resistance}
    return {"combination": combo, "control_combination": cap, "d": d, "center_kn": center,
            "radius_kn": radius, "cap_radius_kn": cap_radius, "edz_term_kn": contribution, "branches": limits,
            "upper_utilization": max(r["upper_utilization"] for r in limits.values()),
            "status": "SHEAR_BOUND_SATISFIED" if all(r["upper_utilization"] <= 1 for r in limits.values())
                      else "EXACT_CAPACITY_SHEAR_OR_WALL_TYPE_REQUIRED"}
