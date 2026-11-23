"""Recover individual directional pier bending amplitudes at native centroids."""
from itertools import combinations
from math import isclose, isfinite

from .mixed_demands import linear_coefficients, native_graph
from .pier_seismic_shear import envelope


def directional_model(source, scope):
    """Read the two horizontal spectra and their coefficients from the model itself."""
    _, cases, graph = native_graph(source)
    table = source["vs04_basis_probe"]["table_reads"]["Load Case Definitions - Response Spectrum"]
    if table.get("status") != "CAPTURED" or table.get("row_count") != len(table["rows"]):
        raise ValueError("SPECTRUM_DEFINITIONS_REQUIRED")
    cases_used = {}
    names = set(scope["native_seismic"])
    names.update(c["combination"] for c in scope["controls"].values() if c.get("combination"))
    equations = {}
    for name in sorted(names):
        terms = linear_coefficients(name, graph, cases)
        if any(cases[k]["type"] not in ("Linear Static", "Response Spectrum") for k in terms):
            raise ValueError("LINEAR_STATIC_AND_SPECTRUM_TERMS_REQUIRED")
        pair = {"X": 0., "Y": 0.}
        for key, factor in terms.items():
            if cases[key]["type"] != "Response Spectrum":
                continue
            rows = [r for r in table["rows"] if r["Name"] == key]
            if len(rows) != 1 or rows[0]["CoordSys"] != "Global" or float(rows[0]["Angle"]) % 360 != 0:
                raise ValueError("SINGLE_GLOBAL_HORIZONTAL_SPECTRUM_REQUIRED")
            r = rows[0]
            direction = {"U1": "X", "U2": "Y"}.get(r.get("LoadName"))
            if not direction or r.get("GUID") != cases[key]["guid"] or cases_used.setdefault(direction, key) != key:
                raise ValueError("UNIQUE_DIRECTIONAL_SPECTRUM_REQUIRED")
            pair[direction] = abs(float(factor))
        equations[name] = pair["X"], pair["Y"]
    if set(cases_used) != {"X", "Y"}:
        raise ValueError("TWO_DIRECTIONAL_SPECTRA_REQUIRED")
    return cases_used, equations


def recover_amplitudes(equations, radii):
    """Invert two independent linear-add radii and validate every other combination.

    A symmetric scalar spectrum contributes |factor| times its magnitude on each
    side of the static centre. An interval error is carried through the inversion.
    """
    allowance = .0001  # kN·m, covers ETABS four-decimal display rounding of each radius
    if set(equations) != set(radii) or len(equations) < 3:
        raise ValueError("INDEPENDENT_SPECTRAL_AMPLITUDE_CONTROLS_REQUIRED")
    if any(not isfinite(v) or v < 0 for v in radii.values()):
        raise ValueError("INVALID_PIER_MOMENT_RADIUS")
    best = None
    for left, right in combinations(sorted(equations), 2):
        a, b = equations[left]
        c, d = equations[right]
        det = a*d-b*c
        if abs(det) > 1e-10:
            score = max(abs(b)+abs(d), abs(a)+abs(c))/abs(det)
            if best is None or score < best[0]:
                best = score, left, right, det
    if best is None:
        raise ValueError("DIRECTIONAL_SPECTRAL_RADII_NOT_IDENTIFIABLE")
    _, left, right, det = best
    a, b = equations[left]
    c, d = equations[right]
    x = (d*radii[left]-b*radii[right])/det
    y = (a*radii[right]-c*radii[left])/det
    ex, ey = allowance*(abs(d)+abs(b))/abs(det), allowance*(abs(c)+abs(a))/abs(det)
    if x < -ex or y < -ey:
        raise ValueError("INCONSISTENT_NEGATIVE_SPECTRAL_AMPLITUDE")
    residuals = []
    for name, (u, v) in equations.items():
        residual = abs(u*x+v*y-radii[name])
        if residual > allowance+u*ex+v*ey+1e-10:
            raise ValueError("PIER_SPECTRAL_AMPLITUDE_CONTROLS_DIFFER")
        residuals.append(residual)
    return {"X": max(0., x), "Y": max(0., y), "uncertainty_knm": {"X": ex, "Y": ey},
            "equations": len(radii), "solved_from": [left, right], "max_control_error_knm": max(residuals)}


def directional_components(angle):
    angle = float(angle)
    if not isfinite(angle) or not isclose(angle/90, round(angle/90), rel_tol=0, abs_tol=1e-7):
        raise ValueError("OBLIQUE_PIER_NEEDS_PROJECTED_MOMENT_BEFORE_MODAL_COMBINATION")
    along_x = round(angle/90) % 2 == 0
    return {"X": "M3" if along_x else "M2", "Y": "M2" if along_x else "M3"}


def pier_moments(model, groups, pier, storey, native):
    cases, equations = model
    components = directional_components(native["AxisAngle"])
    spectra = {k: envelope(groups[pier, storey, "Bottom", k]) for k in equations}
    result = {}
    for direction, component in components.items():
        radii = {k: (v["Max"][component]-v["Min"][component])/2 for k, v in spectra.items()}
        calc = recover_amplitudes(equations, radii)
        result[direction] = {"case": cases[direction], "component": component, "global_moment_axis": "Y" if direction=="X" else "X",
                             "magnitude_knm": calc[direction], "uncertainty_knm": calc["uncertainty_knm"][direction],
                             "combination_controls": calc["equations"], "solved_from": calc["solved_from"],
                             "max_control_error_knm": calc["max_control_error_knm"]}
    return result


def storey_reference(source, storey, direction, case):
    """Whole-storey diagnostic at the same bottom cut, in the archived global result axes."""
    spec = source["r08_second_order_source"]["spectrum_source"]["table_reads"]["Story Forces"]
    component = "MY" if direction == "X" else "MX"
    if (spec.get("status") != "CAPTURED" or spec.get("row_count") != len(spec["rows"])
            or spec["field_metadata"]["units_by_field"].get(component) != "kN-m"):
        raise ValueError("UNIT_VERIFIED_STOREY_MOMENT_REQUIRED")
    matches = [r for r in spec["rows"] if (r.get("Story"), r.get("Location"), r.get("OutputCase"),
        r.get("CaseType"), r.get("StepType")) == (storey, "Bottom", case, "LinRespSpec", "Max")]
    if len(matches) != 1:
        raise ValueError("UNIQUE_DIRECTIONAL_STOREY_MOMENT_REQUIRED")
    value = float(matches[0][component])
    if not isfinite(value) or value <= 0:
        raise ValueError("POSITIVE_STOREY_MOMENT_REQUIRED")
    return value
