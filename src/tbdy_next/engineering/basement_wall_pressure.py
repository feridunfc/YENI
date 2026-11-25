"""Normal load on a horizontal one-metre strip between the two modelled column axes."""
from functools import lru_cache
from math import ceil, floor, isfinite, pi, sqrt
import re

from ..column_engine.beam_capacity import signed_beam_capacity
from ..column_engine.section_capacity import Bar, Section
from .basement_pier_geometry import required
from .mixed_demands import _static_pattern_loads, linear_coefficients, native_graph

DEFAULT_AGGREGATE_MM = 20.0


def clear_limit(aggregate, *diameters):
    """TS 500 §9.5.2 same-row clearance, also adopted for entry into a support cage."""
    if not all(type(v) in (int, float) and isfinite(v) and v > 0 for v in (aggregate, *diameters)):
        raise ValueError("POSITIVE_AGGREGATE_AND_BAR_DIAMETER_REQUIRED")
    return max(25., *diameters, 4*aggregate/3)


# A constant two-face proposal, in increasing steel area per metre.
PITCHES = (200, 125, 100)
DIAMETERS = (12, 14, 16, 18, 20, 22, 25)
CAGES = sorted(((dia, pitch) for pitch in PITCHES for dia in DIAMETERS),
               key=lambda pair: (pair[0]**2/pair[1], pair[0]))
_AREA_LOAD = re.compile(r'^\s*AREALOAD\s+"([^"]+)"\s+"([^"]+)"\s+TYPE\s+"([^"]+)"\s+(.*)$')
_NORMAL = re.compile(r'DIR\s+"3"\s+LC\s+"([^"]+)"\s+FVAL\s+([-+\d.eE]+)\s*')


def pressure_cases(source, bound, scope, pier, story, panels, *, allow_unloaded=False):
    tables, cases, graph = native_graph(source)
    assigned = {**scope["native_static"], **scope["native_seismic"]}
    required(not scope["other"] and assigned, "WALL_ASSIGNMENT_OPERATOR_UNRESOLVED")
    labels = {p["wall"] for p in panels}
    patterns = {label: {} for label in labels}
    for line in bound["deck"].splitlines():
        match = _AREA_LOAD.match(line)
        if not match or match[1] not in labels or match[2] != story:
            continue
        label, _, kind, fields = match.groups()
        if kind == "TEMP":
            continue
        normal = _NORMAL.fullmatch(fields)
        required(kind == "UNIFF" and normal is not None, "UNSUPPORTED_PANEL_LOAD_COMPONENT")
        pattern, value = normal[1], float(normal[2])
        required(pattern not in patterns[label] and isfinite(value), "AMBIGUOUS_PANEL_NORMAL_PRESSURE")
        patterns[label][pattern] = value
    required(allow_unloaded or all(patterns.values()), "NORMAL_PRESSURE_ASSIGNMENT_REQUIRED_ON_EVERY_WEB")
    applied = {key for terms in patterns.values() for key in terms}
    # Include captured static pressure design combinations even if they were not assigned to Wall.
    # Native wall assignments are always present in the expected population.
    extra = {}
    observed = {n for pn, st, _, n in bound["groups"] if (pn,st) == (pier,story)}
    for name in sorted(observed - assigned.keys()):
        try:
            terms = linear_coefficients(name, graph, cases)
        except ValueError:
            continue
        if terms and all(cases[n]["type"] == "Linear Static" for n in terms):
            extra[name] = terms
    all_cases = {**assigned, **extra}
    _, loads = _static_pattern_loads(tables, {n for terms in all_cases.values() for n in terms}, cases)
    result = {}
    for combo, terms in all_cases.items():
        weights = {}
        for case, factor in terms.items():
            for pattern, scale in loads[case]:
                if pattern in applied:
                    weights[pattern] = weights.get(pattern, 0.) + float(factor * scale)
        weights = {p:v for p,v in weights.items() if v}
        if combo in assigned or weights:
            result[combo] = {"role": "WALL_STRENGTH" if combo in assigned else "ADDITIONAL_STATIC_PRESSURE",
                "spectral": combo in scope["native_seismic"], "pressure_pattern_factors": weights,
                "pressure_kn_m2": {p["member"]: sum(weights.get(k,0.)*v for k,v in patterns[p["wall"]].items()) for p in panels}}
    return result, patterns


@lru_cache(maxsize=512)
def strip_resistance(thickness, cover, dia, pitch, mat):
    # A periodic one-metre strip has an integer number of bars in each face.
    count = 1000 // pitch
    required(count*pitch == 1000, "STRIP_REQUIRES_PERIODIC_REINFORCEMENT")
    return layer_resistance(thickness, thickness/2-cover-1.5*dia, dia, count, mat)


@lru_cache(maxsize=512)
def layer_resistance(thickness, offset, dia, count, mat):
    """Symmetric face layers per metre at the actual depth, with zero membrane force."""
    required(count > 0 and 0 < offset < thickness/2, "STRIP_LAYER_GEOMETRY_INVALID")
    area = pi * dia**2/4
    bars = tuple(Bar(s*offset, (2*i-count+1)*500/count, area) for s in (-1,1) for i in range(count))
    section = Section(thickness, 1000., bars, mat)
    result = signed_beam_capacity(section)
    required(result["status"] == "BEAM_CAPACITY_REFERENCE" and
             all(t["point"]["maximum_tensile_strain"] <= .1 for t in result["points"]), "STRIP_SECTION_CAPACITY_UNRESOLVED")
    mr = min(abs(result[field])-point["tolerance_knm"] for field,point in
             zip(("positive_m3_knm","negative_m3_knm"), result["points"]))
    # TS 500 Eq. 8.1 with zero axial force in the horizontal pressure strip.
    d = thickness/2+offset
    fctd = .35*sqrt(mat.fck)*mat.fcd/mat.fck
    return mr, .65*fctd*1000*d/1000


def finite_grid(height_mm, diameter, maximum_pitch, cover):
    """Centred end cover and at least the specified number of bars in every full metre."""
    if min(diameter, maximum_pitch, cover) <= 0 or height_mm < 1000 or 1000 % maximum_pitch:
        raise ValueError("ONE_METRE_PERIODIC_GRID_REQUIRED")
    edge = cover + diameter/2
    per_metre = 1000 // maximum_pitch
    required(height_mm > 2*edge and edge < 1000 and per_metre >= 2, "INSUFFICIENT_GRID_HEIGHT")
    # Interior windows may start just beyond a bar. At the ends the first bar
    # is fixed by the cover, so (n-1) spaces must also fit after that bar.
    limit = min(maximum_pitch, (1000-edge)/(per_metre-1))
    intervals = ceil((height_mm-2*edge)/limit)
    pitch = (height_mm-2*edge)/intervals
    return {"layers": intervals+1, "pitch_mm": pitch, "first_and_last_offset_mm": edge,
            "guaranteed_bars_per_m": per_metre, "clear_spacing_mm": pitch-diameter}


def panel_pressure_design(panel, combos, cover, mat, height, *, candidates=CAGES, grid_for=None, inset=0.,
                          aggregate=DEFAULT_AGGREGATE_MM):
    span = panel["span_m"]
    thickness = panel["thickness_m"]*1000
    pressures = {name: spec["pressure_kn_m2"][panel["member"]] for name,spec in combos.items()}
    governing = max(pressures, key=lambda case: abs(pressures[case]))
    peak = abs(pressures[governing])
    # Pin / fixed limits bracket passive independent rotational restraints with zero relative
    # transverse translation. This bounds both moment signs and both end reactions for uniform q.
    for dia, pitch in candidates:
        grid = grid_for(dia, pitch) if grid_for else {}
        rho = 2*pi*dia**2/4/(pitch*thickness)
        actual_pitch = height*1000/ceil(height*1000/pitch)
        if (rho < .0025 or grid.get("clear_spacing_mm", actual_pitch-dia) < clear_limit(aggregate, dia)
                or thickness <= 2*(cover+inset+1.5*dia) or (grid_for and not grid)):
            continue
        mr, vcr = strip_resistance(thickness,cover+inset,dia,pitch,mat)
        if peak*span**2/8 <= mr and 5*peak*span/8 <= vcr:
            break
    else:
        raise ValueError("NO_PROPOSED_HORIZONTAL_CAGE_MEETS_PRESSURE_BENDING_AND_CRACKING_SHEAR")
    n = ceil(height*1000/pitch)
    return {"pressure_model":"ONE_WAY_HORIZONTAL_UNIFORM_STRIP", "physical_height_mm":height*1000,
            "diameter_mm":dia, "maximum_pitch_mm":pitch, "layers":n, "pitch_mm":height*1000/n,
            **grid, "curtain_inset_mm":inset, "provided_ratio_at_maximum_pitch":rho, "cover_mm": cover, "governing":governing,
            "design_moment_resistance_knm_m":mr, "diagonal_cracking_kn_m":vcr,
            "cuts": [{"combination":name,"pressure_kn_m2":q,"moment_bound_knm_m":abs(q)*span**2/8,
                      "reaction_bound_kn_m":5*abs(q)*span/8, "moment_ratio":abs(q)*span**2/(8*mr),
                      "cracking_shear_ratio":5*abs(q)*span/(8*vcr)}
                     for name,q in pressures.items()]}


def vertical_section(panel, horizontal, cover, material, diameter, pitch, *, aggregate=DEFAULT_AGGREGATE_MM):
    length, thick = 1000*panel["clear_length_m"], 1000*panel["thickness_m"]
    count = max(2, ceil(length/pitch-1e-12))
    spacing = length/count
    offset = thick/2 - cover - horizontal.get("curtain_inset_mm",0.) - 2*horizontal["diameter_mm"] - diameter/2
    area = pi*diameter**2/4
    required(min(spacing-diameter, 2*offset-diameter) >= clear_limit(aggregate, diameter)
             and spacing/2 >= diameter/2 and 2*area/(spacing*thick) >= .0025,
             "VERTICAL_WEB_GRID_DOES_NOT_FIT")
    bars = tuple(Bar((2*i-count+1)*spacing/2, sign*offset, area) for i in range(count) for sign in (-1,1))
    # A crosstie at every vertical station and horizontal layer connects the two curtains.
    ties_per_m2 = floor(1000/spacing+1e-10)*floor(1000/horizontal["pitch_mm"]+1e-10)
    from .pier_height_design import section_dimensions
    actual_height = horizontal.get("physical_height_mm")
    required(actual_height and isfinite(actual_height) and actual_height > 0, "PHYSICAL_PANEL_HEIGHT_REQUIRED")
    dimensions = section_dimensions(1000*panel["span_m"], thick, actual_height)
    # Native folded pier length classifies the physical wall. The unsupported
    # limb length and its thickness still govern the actual web being detailed.
    physical_length = panel.get("folded_pier_length_m",panel["span_m"])
    dimensions.update(classification_length_mm=1000*physical_length,
                      classification_length_over_thickness=1000*physical_length/thick)
    if thick>=dimensions["required_thickness_mm"] and physical_length/panel["thickness_m"]>=7-1e-9:
        dimensions["status"] = "DIMENSIONS_SATISFIED"
    required(dimensions["status"] == "DIMENSIONS_SATISFIED" and ties_per_m2 >= 4
             and physical_length/panel["thickness_m"] >= 7-1e-9,
             "TBDY_WALL_DIMENSIONS_OR_WEB_CROSSTIE_MINIMUM_UNSATISFIED")
    return Section(length,thick,bars,material), {"diameter_mm":diameter,"pitch_mm":spacing,
        "stations_per_face":count,"as_two_faces_mm2":2*count*area,"vertical_ratio":2*count*area/(length*thick),
        "dimensions": dimensions, "crosstie_diameter_mm":horizontal["diameter_mm"], "crossties":count*horizontal["layers"],
        "min_crossties_full_m2":ties_per_m2, "steel_role":"PROPOSED_WEB_BETWEEN_COLUMN_FACES"}
