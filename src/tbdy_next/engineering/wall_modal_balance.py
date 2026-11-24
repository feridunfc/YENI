"""Six-component equilibrium of signed wall and frame cuts in the original solved building."""

from collections import defaultdict
from decimal import Decimal
from math import cos, fsum, isclose, isfinite, radians, sin, sqrt
import shlex

from ..column_engine.source_bank import native_frame_force_rows
from ..etabs_source_gateway_windows import verify
from ..wall_modal_capture import wall_cut_plan
from .basement_pier_geometry import required
from .basement_reference import basement_reference
from .gravity_story_basis import _physical_population
from .pier_force_source import ORIGINAL, _table
from .wall_overturning import directional_components

COMPONENTS = ("FX", "FY", "FZ", "MX", "MY", "MZ")
STORY_FIELDS = ("VX", "VY", "P", "MX", "MY", "T")


def _translate(vector, point, origin):
    fx, fy, fz, mx, my, mz = vector
    x, y, z = (a - b for a, b in zip(point, origin))
    return (fx, fy, fz, mx + y * fz - z * fy, my + z * fx - x * fz, mz + x * fy - y * fx)


def _sum(vectors):
    return tuple(map(fsum, zip(*vectors, strict=True)))


def _printed_error(text):
    # Fixed-point result tables print four decimals below one million and whole
    # units for larger values. Scientific notation retains its own last place.
    val = Decimal(text)
    if not val.is_finite():
        raise ValueError("NONFINITE_WALL_REFERENCE")
    if "e" in str(text).lower():
        return float(Decimal(".5").scaleb(val.as_tuple().exponent))
    return 0.5 if abs(val) >= 1_000_000 and "." not in str(text) else 0.00005


def _index_results(tables, name, key_fields, components):
    table = tables[name]
    units = table["field_metadata"]["units_by_field"]
    moment = {"M2", "M3", "MX", "MY", "MZ", "T"}
    required(
        all(units[k] == ("kN-m" if k in moment else "kN") for k in components),
        "WALL_FORCE_OR_MOMENT_UNITS_DIFFER",
    )
    result = {}
    for row in _table(tables, name):
        step = row.get("StepType")
        if step == "Mode":
            number = float(row["StepNumber"])
            required(
                number.is_integer() and number > 0 and row["CaseType"] in ("LinModRitz", "LinModEigen"),
                "WALL_MODAL_STEP_IDENTITY_REQUIRED",
            )
            number = int(number)
        elif step in (None, "None", "") and row["CaseType"] == "LinStatic":
            number = 0
        elif step == "Max" and row["CaseType"] == "LinRespSpec":
            number = 0
        else:
            continue
        key = tuple(row[k] for k in key_fields) + (row["OutputCase"], number)
        required(
            key not in result and all(isfinite(float(row[k])) for k in components),
            "DUPLICATE_OR_INVALID_MODAL_CUT",
        )
        result[key] = row
    return result


def _frame_series(source, population, points, keys, origin):
    bank = source["column_axial"]["demand_support"]["force_source"]
    required(
        bank["units_code"] == 6
        and not bank["errors"]
        and bank["output_selection_before"] == bank["output_selection_after"],
        "ARCHIVED_COLUMN_OUTPUT_IDENTITY_REQUIRED",
    )
    series = defaultdict(list)
    for (kind, uid), frame in population.items():
        if kind != "COLUMN":
            continue
        pos = points[frame["point_i"]]
        axes = frame["axes_global"]
        required(
            axes and abs(axes[0][2] - 1) < 1e-8 and abs(pos[2] - origin[2]) < 1e-7,
            "UPWARD_VERTICAL_COLUMN_START_REQUIRED",
        )
        seen = set()
        for _, station, _, element_station, case, step, num, p, v2, v3, t, m2, m3 in native_frame_force_rows(
            bank["rowsets"][uid], uid
        ):
            key = case, num
            if key not in keys or abs(station) > 1e-7 or abs(element_station) > 1e-7:
                continue
            required(
                key not in seen
                and ((num > 0 and step == "Mode") or (num == 0 and step in ("Single Value", "", None))),
                "COLUMN_CUT_SIDE_OR_STEP_CONFLICT",
            )
            seen.add(key)
            # Negative face of an upward column. CSI M2 and M3 use their respective compression-face conventions.
            local = (-p, -v2, -v3), (-t, m2, -m3)
            vector = [
                fsum(v * axis[i] for v, axis in zip(triplet, axes)) for triplet in local for i in range(3)
            ]
            series[key].append(_translate(vector, pos, origin))
        required(seen == keys, "SIGNED_COLUMN_ENDS_MISSING:" + uid)
    return {key: _sum(vectors) for key, vectors in series.items()}


def _panel_series(raw, plans, ids, keys):
    values = {}
    for uid in ids:
        panel, plan = raw["panels"][uid], plans[uid]
        required(
            panel["story"] == plan["story"]
            and panel["origin_m"] == plan["origin_m"]
            and len(panel["corners"]) == len(plan["corners"])
            and {tuple(pair) for pair in panel["corners"]} == plan["corners"],
            "WALL_CUT_CORNER_OR_ORIGIN_MISMATCH:" + uid,
        )
        by_key = {}
        for case, mode, *vec in panel["rows"]:
            key = case, mode
            required(
                key not in by_key
                and len(vec) == 6
                and all(isinstance(x, (int, float)) and isfinite(x) for x in vec),
                "DUPLICATE_OR_INVALID_WALL_MODAL_VECTOR",
            )
            by_key[key] = vec
        required(set(by_key) == keys, "SIGNED_WALL_MODE_INVENTORY_DIFFERS:" + uid)
        values[uid] = by_key
    return values


def _pier_check(vector, native, row):
    a = radians(float(native["AxisAngle"]))
    c, s = cos(a), sin(a)
    fx, fy, fz, mx, my, mz = vector
    projected = (-c * fx - s * fy, s * fx - c * fy, -fz, c * mx + s * my, s * mx - c * my, -mz)
    # The native pier centroid is tabulated in metres to 0.001 m.
    extra = (
        0.00051 * (abs(c) + abs(s)) * abs(fz),
        0.00051 * (abs(c) + abs(s)) * abs(fz),
        0.00051 * (abs(fx) + abs(fy)),
    )
    for i, (k, v) in enumerate(zip(("V2", "V3", "P", "M2", "M3", "T"), projected)):
        allowance = _printed_error(row[k]) + (0.0 if i < 3 else extra[i - 3])
        if abs(v - float(row[k])) > allowance + 2e-7 + 1e-10 * abs(v):
            return False
    return True


def _case_modes(stages, modal, modes):
    params = stages["report_evidence"]["native_demand_sources"]["spectral_modal_parameters"]
    responses = {c["case"]: c for c in params["spectrum_response_evidence"]["cases"]}
    periods = {
        r["mode"]: r["period_api_values"]["Period"]
        for r in params["native_numeric_precision"]["rows"]
        if r["modal_case"] == modal and r["status"] == "NATIVE_DOUBLE_MODAL_INPUTS_BOUND"
    }
    required(set(periods) == set(modes), "FULL_MODAL_PERIODS_REQUIRED")
    output = {}
    for case in params["cases"]:
        direction = {"U1": "X", "U2": "Y"}.get(case.get("active_axis"))
        if not direction or case["modal_case"] != modal:
            continue
        required(
            case["coordinate_system"] == "Global"
            and float(case["angle_deg"]) == 0
            and case["modal_combination"] == "CQC"
            and case["directional_combination"] == "SRSS"
            and case["rigid_response"] == "No"
            and direction not in output,
            "SINGLE_GLOBAL_PERIODIC_CQC_CASE_REQUIRED",
        )
        response = responses[case["case"]]
        rows = {r["mode"]: r for r in response["rows"]}
        damping = response["case_damping"]
        required(
            set(rows) == set(modes)
            and len(rows) == len(response["rows"])
            and response["curve_status"] == "NATIVE_CURVE_AND_SCALE_BOUND"
            and not damping["overrides"]
            and all(
                r.get("curve_display_compatible") and r.get("damping_display_compatible")
                for r in rows.values()
            ),
            "QUALIFIED_CURVE_AND_CONSTANT_DAMPING_REQUIRED",
        )
        zeta = damping["constant_ratio"]
        required(
            0 < zeta < 1 and all(float(r["effective_display_ratio"]) == zeta for r in rows.values()),
            "CONSTANT_EFFECTIVE_DAMPING_REFERENCE_REQUIRED",
        )
        amps = [float(rows[m]["unadjusted_curve_amplitude_m"]) for m in modes]
        output[direction] = (
            case["case"],
            amps,
            [periods[m] for m in modes],
            zeta,
            float(case["eccentricity_ratio"]),
        )
    required(set(output) == {"X", "Y"}, "BOTH_MODAL_DIRECTIONS_REQUIRED")
    return output


def cqc_matrix(periods, damping):
    """Equal-damping periodic CQC coefficients (TBDY Annex 4B, Eq. 4B.5b)."""
    required(
        periods and 0 < damping < 1 and all(isfinite(v) and v > 0 for v in periods), "INVALID_CQC_PARAMETERS"
    )
    result = []
    for i, ti in enumerate(periods):
        line = []
        for tj in periods[:i]:
            r = min(ti, tj) / max(ti, tj)
            line.append(
                8 * damping**2 * (1 + r) * r**1.5 / ((1 - r * r) ** 2 + 4 * damping**2 * r * (1 + r) ** 2)
            )
        result.append(line)
    return result


def cqc(values, matrix):
    required(
        len(values) == len(matrix)
        and values
        and all(len(row) == i for i, row in enumerate(matrix))
        and all(isfinite(v) for v in values),
        "CQC_MODE_POPULATION_DIFFERS",
    )
    square = fsum(v * v + 2 * v * fsum(r * u for r, u in zip(row, values)) for v, row in zip(values, matrix))
    required(square >= -1e-12 * fsum(v * v for v in values), "CQC_QUADRATIC_FORM_NEGATIVE")
    return sqrt(max(0.0, square))


def _project_story(source, bound, raw, plans, story, z, modes, keys, spectra, native_story, native_piers):
    origin = [0.0, 0.0, z]
    population, _, points, _ = _physical_population(source, z)
    ids = {uid for kind, uid in population if kind == "WALL"}
    required(
        ids == {uid for uid, p in plans.items() if p["story"] == story}, "WALL_CUT_PHYSICAL_CENSUS_DIFFERS"
    )
    panels = _panel_series(raw, plans, ids, keys)
    columns = _frame_series(source, population, points, keys, origin)
    membership = {}
    group_origins = {}
    native_props = {}
    for (pier, st), members in bound["assignments"].items():
        if st != story:
            continue
        (props,) = bound["properties"][pier, st]
        required(
            int(props["NumLineObj"]) == 0 and int(props["NumAreaObj"]) == len(members),
            "SEPARATE_FRAME_AND_WALL_POPULATIONS_REQUIRED",
        )
        for uid in set(members) & ids:
            required(uid not in membership, "WALL_DOUBLE_ASSIGNED_AT_CUT")
            membership[uid] = pier
        native_props[pier] = props
        group_origins[pier] = [float(props["CGBot" + k]) for k in "XYZ"]
        required(abs(group_origins[pier][2] - z) < 1e-7, "PIER_AND_STOREY_CUT_DATUM_DIFFERS")
    unassigned = sorted(ids - set(membership))
    for uid in unassigned:
        label = "Unassigned " + uid
        membership[uid] = label
        group_origins[label] = plans[uid]["origin_m"]
    checked, controls = [], []
    for case, number in sorted(keys):
        key = case, number
        group = {
            label: _sum(
                [
                    _translate(panels[uid][key], plans[uid]["origin_m"], point)
                    for uid in sorted(ids)
                    if membership[uid] == label
                ]
            )
            for label, point in group_origins.items()
        }
        wall = _sum([_translate(vec, group_origins[label], origin) for label, vec in group.items()])
        frame = columns[key]
        reference = native_story[story, "Bottom", case, number]
        actual = [float(reference[k]) for k in STORY_FIELDS]
        delta = [w + c - s for w, c, s in zip(wall, frame, actual)]
        budgets = [
            _printed_error(reference[k]) + 2e-7 + 1e-10 * (abs(w) + abs(c))
            for k, w, c in zip(STORY_FIELDS, wall, frame)
        ]
        ok = all(abs(v) <= b for v, b in zip(delta, budgets))
        matched = sum(
            _pier_check(group[label], prop, native_piers[story, label, "Bottom", case, number])
            for label, prop in native_props.items()
        )
        checked.append(
            {
                "case": case,
                "mode": number,
                "wall": wall,
                "columns": frame,
                "storey": actual,
                "residual": delta,
                "rounding_budget": budgets,
                "balanced": ok,
                "pier_checks": matched,
                "centroidal_groups": group,
            }
        )
        if number == 0:
            controls.append({"case": case, "wall_kn_knm": wall, "storey_kn_knm": actual, "balanced": ok})
    ready = all(r["balanced"] and r["pier_checks"] == len(native_props) for r in checked)
    output = {
        "story": story,
        "cut_z_m": z,
        "origin_m": origin,
        "columns": len(population) - len(ids),
        "walls": len(ids),
        "unassigned_wall_ids": unassigned,
        "groups": len(group_origins),
        "modes_expected": len(modes),
        "modes_balanced": sum(r["mode"] > 0 and r["balanced"] for r in checked),
        "static_controls": controls,
        "pier_controls_matched": sum(r["pier_checks"] for r in checked),
        "pier_controls_expected": len(native_props) * len(checked),
        "component_order": list(COMPONENTS),
        "signed_cuts": checked,
        "directions": [],
        "status": "SIGNED_CUT_BALANCED" if ready else "WALL_OR_STOREY_CONTROL_MISMATCH",
    }
    if not ready:
        return output
    by_mode = {r["mode"]: r for r in checked if r["mode"] > 0}
    for direction, (rs, amps, periods, damping, ecc) in spectra.items():
        component = 4 if direction == "X" else 3
        matrix = cqc_matrix(periods, damping)

        def combined(extract):
            return cqc([a * extract(by_mode[m]) for a, m in zip(amps, modes)], matrix)

        wall = combined(lambda r: r["wall"][component])
        total = combined(lambda r: r["storey"][component])
        shear = 0 if direction == "X" else 1
        wall_shear = combined(lambda r: r["wall"][shear])
        storey_shear = combined(lambda r: r["storey"][shear])
        native = float(native_story[story, "Bottom", rs, 0][STORY_FIELDS[component]])
        centroidal = combined(lambda r: fsum(v[component] for v in r["centroidal_groups"].values()))
        individual = {
            label: combined(lambda r: r["centroidal_groups"][label][component]) for label in group_origins
        }
        centroid_controls = []
        for label, periodic in individual.items():
            control = {"group": label, "periodic_knm": periodic}
            centroid_controls.append(control)
            if label not in native_props:
                control["reason"] = "UNASSIGNED_SHELL_HAS_NO_NATIVE_PIER_SPECTRUM"
                continue
            try:
                field = directional_components(native_props[label]["AxisAngle"])[direction]
                value = abs(float(native_piers[story, label, "Bottom", rs, 0][field]))
                control.update(component=field, native_knm=value, native_minus_periodic_knm=value - periodic)
            except (KeyError, ValueError) as exc:
                control["reason"] = str(exc)
        required(total > 0 and native > 0 and storey_shear > 0, "POSITIVE_DIRECTIONAL_STOREY_ACTION_REQUIRED")
        output["directions"].append(
            {
                "direction": direction,
                "case": rs,
                "moment_axis": COMPONENTS[component],
                "modes": len(modes),
                "damping": damping,
                "native_eccentricity": ecc,
                "wall_common_origin_cqc_knm": wall,
                "storey_common_origin_cqc_knm": total,
                "wall_to_storey_common_origin": wall / total,
                "wall_cqc_shear_kn": wall_shear,
                "storey_cqc_shear_kn": storey_shear,
                "wall_to_storey_shear": wall_shear / storey_shear,
                "native_storey_spectrum_shear_kn": float(
                    native_story[story, "Bottom", rs, 0][STORY_FIELDS[shear]]
                ),
                "wall_centroidal_sum_before_cqc_knm": centroidal,
                "sum_individual_centroid_cqc_knm": fsum(individual.values()),
                "centroid_controls": centroid_controls,
                "native_storey_spectrum_knm": native,
                "native_minus_periodic_knm": native - total,
                "project_status": "BASE_COUPLING_AND_DESIGN_SPECTRUM_BASIS_REQUIRED",
            }
        )
    return output


def _floor_inertia(source, deck, storeys, native_story, modal, modes, spectra):
    """Recover floor horizontal forces by differencing signed storey shears, then form ΣFiHi."""
    tables = source["vs04_basis_probe"]["table_reads"]
    heights = _table(tables, "Story Definitions")
    required(
        tables["Story Definitions"]["field_metadata"]["units_by_field"]["Height"] == "m",
        "STOREY_HEIGHT_UNIT_REQUIRED",
    )
    required(len({r["Tower"] for r in heights}) == 1, "SINGLE_TOWER_REQUIRED_FOR_FLOOR_INERTIA")
    height = {r["Story"]: float(r["Height"]) for r in heights}
    layers = [(r["story"], r["cut_z_m"], r["cut_z_m"] + height[r["story"]]) for r in storeys]
    required(
        layers
        and all(hi > lo for _, lo, hi in layers)
        and all(isclose(a[2], b[1], rel_tol=0, abs_tol=1e-7) for a, b in zip(layers, layers[1:])),
        "CONTIGUOUS_STOREY_HEIGHTS_REQUIRED",
    )
    required(
        {k[0] for k in native_story if k[1:3] == ("Bottom", modal)} == {s for s, _, _ in layers},
        "FULL_NATIVE_STOREY_SHEAR_POPULATION_REQUIRED",
    )
    (base,) = _table(tables, "Tower and Base Story Definitions")
    required(
        isclose(float(base["BSElev"]), layers[0][1], abs_tol=1e-7, rel_tol=0),
        "FOUNDATION_TO_ROOF_CUT_SERIES_REQUIRED",
    )
    for line in deck.splitlines():
        record = line.split(None, 1)
        if not record or record[0] not in {
            "POINTASSIGN",
            "AREAASSIGN",
            "LINEASSIGN",
            "LINKASSIGN",
            "LINK",
            "LINE",
        }:
            continue
        words = shlex.split(line)
        if record[0] in {"LINK", "LINKASSIGN"} or record[0] == "LINE" and "LINK" in words:
            raise ValueError("LINK_ACTIONS_REQUIRE_SEPARATE_FLOOR_EQUILIBRIUM")
        if {"RESTRAINT", "SPRING", "SPRINGPROP", "POINTSPRING", "LINESPRING"}.intersection(words[3:]):
            required(words[2] == base["BSName"], "ABOVE_BASE_SUPPORT_ACTIONS_REQUIRED_FOR_FLOOR_LOADS")
    mass_table = tables["Assembled Joint Masses"]
    units = mass_table["field_metadata"]["units_by_field"]
    required(units["Z"] == "m" and units["UX"] == units["UY"] == "ton", "FLOOR_MASS_UNIT_REQUIRED")
    elevations = [layers[0][1], *(hi for _, _, hi in layers)]
    mass = defaultdict(lambda: [0.0, 0.0])
    for r in _table(tables, "Assembled Joint Masses"):
        z = float(r["Z"])
        amounts = [float(r[k]) for k in ("UX", "UY")]
        required(isfinite(z) and all(isfinite(v) and v >= 0 for v in amounts), "INVALID_TRANSLATIONAL_MASS")
        if any(amounts):
            level = next((e for e in elevations if abs(e - z) <= 1e-7), None)
            required(level is not None, "HORIZONTAL_MASS_BETWEEN_CUT_LEVELS")
            for i, v in enumerate(amounts):
                mass[level][i] += v
    required(all(all(mass[hi]) for _, _, hi in layers), "POSITIVE_HORIZONTAL_FLOOR_MASSES_REQUIRED")
    for level, storey in enumerate(storeys):
        storey["horizontal_floor_actions"] = {}
        for result in storey["directions"]:
            direction = result["direction"]
            _, amps, periods, damping, _ = spectra[direction]
            field = "VX" if direction == "X" else "VY"
            modal_moments = []
            modal_floor_forces = []
            for m in modes:
                shears = [float(native_story[s, "Bottom", modal, m][field]) for s, _, _ in layers[level:]]
                floor_forces = [a - b for a, b in zip(shears, shears[1:] + [0.0])]
                modal_floor_forces.append(floor_forces)
                modal_moments.append(
                    fsum(
                        force * (hi - storey["cut_z_m"])
                        for force, (_, _, hi) in zip(floor_forces, layers[level:])
                    )
                )
            mo = cqc([a * v for a, v in zip(amps, modal_moments)], cqc_matrix(periods, damping))
            required(mo > 0, "POSITIVE_LATERAL_FLOOR_MOMENT_REQUIRED")
            result["horizontal_floor_mo_cqc_knm"] = mo
            result["individual_centroid_sum_to_floor_mo"] = result["sum_individual_centroid_cqc_knm"] / mo
            controls = result["centroid_controls"]
            if controls and all("native_knm" in c for c in controls):
                result["separate_piers_native_sum_knm"] = fsum(c["native_knm"] for c in controls)
                result["separate_piers_native_to_floor_mo"] = result["separate_piers_native_sum_knm"] / mo
            storey["horizontal_floor_actions"][direction] = {
                "floor_elevations_m": [hi for _, _, hi in layers[level:]],
                "modes": modes,
                "signed_floor_forces_unit_mode_kn": modal_floor_forces,
                "signed_floor_moments_unit_mode_knm": modal_moments,
            }
    return [{"z_m": z, "mass_x_t": mass[z][0], "mass_y_t": mass[z][1]} for z in elevations]


def _base_reference(tables, modal, modes, spectra):
    units = tables["Base Reactions"]["field_metadata"]["units_by_field"]
    required(all(units[k] == "m" for k in "XYZ"), "BASE_REACTION_POINT_UNITS_REQUIRED")
    native = _index_results(tables, "Base Reactions", (), COMPONENTS)
    records = []
    for direction, (case, amps, periods, damping, _) in spectra.items():
        shear, moment = ("FX", "MY") if direction == "X" else ("FY", "MX")
        ref = native[case, 0]
        origin = [float(ref[k]) for k in "XYZ"]
        required(
            all([float(native[modal, m][k]) for k in "XYZ"] == origin for m in modes),
            "BASE_REACTION_REFERENCE_POINT_DIFFERS",
        )
        matrix = cqc_matrix(periods, damping)
        values = {
            k: cqc([a * float(native[modal, m][k]) for m, a in zip(modes, amps)], matrix)
            for k in (shear, moment)
        }
        records.append(
            {
                "direction": direction,
                "case": case,
                "origin_m": origin,
                "periodic_moment_knm": values[moment],
                "native_moment_knm": float(ref[moment]),
                "periodic_shear_kn": values[shear],
                "native_shear_kn": float(ref[shear]),
            }
        )
    return records


def modal_wall_balance(source, stages, bound):
    basis = source.get("pier_section_forces") or {}
    raw = (basis.get("read") or {}).get("wall_modes")
    result = {
        "schema": "tbdy.next.wall-modal-base.v1",
        "status": "SIGNED_WALL_CUT_SOURCE_REQUIRED",
        "storeys": [],
    }
    if not raw or bound.get("kind") != ORIGINAL:
        return result
    try:
        verify(raw)
        required(
            raw["schema"] == "tbdy.next.original-wall-modal-cuts.v1"
            and raw["units"] == 6
            and raw["selection_restored"] is True
            and raw["model_sha256"] == bound["model_sha256"],
            "WALL_MODAL_GENERATION_OR_UNIT_MISMATCH",
        )
        modal = raw["modal_case"]
        modes = source["column_axial"]["demand_support"]["force_source"]["expected_modal_modes"][modal]
        required(
            raw["modes"] == modes and modes == list(range(1, len(modes) + 1)) and modes,
            "WALL_MODAL_POPULATION_DIFFERS",
        )
        keys = {(modal, i) for i in modes} | {(k, 0) for k in raw["static_cases"]}
        plans, _ = wall_cut_plan(source)
        required(plans and set(plans) == set(raw["panels"]), "WALL_MODAL_PHYSICAL_OBJECT_POPULATION_DIFFERS")
        storeys = sorted({(p["origin_m"][2], p["story"]) for p in plans.values()})
        story_controls = _index_results(raw["tables"], "Story Forces", ("Story", "Location"), STORY_FIELDS)
        pier_controls = _index_results(
            raw["tables"], "Pier Forces", ("Story", "Pier", "Location"), ("V2", "V3", "P", "M2", "M3", "T")
        )
        try:
            spectra = _case_modes(stages, modal, modes)
        except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
            result["spectrum_reason"] = str(exc)
            spectra = {}
        for z, story in storeys:
            try:
                item = _project_story(
                    source, bound, raw, plans, story, z, modes, keys, spectra, story_controls, pier_controls
                )
            except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
                item = {
                    "story": story,
                    "cut_z_m": z,
                    "modes_expected": len(modes),
                    "modes_balanced": 0,
                    "status": "SOURCE_REQUIRED",
                    "reason": str(exc),
                    "directions": [],
                }
            result["storeys"].append(item)
        result["status"] = (
            "SIGNED_CUTS_BALANCED"
            if all(s["status"] == "SIGNED_CUT_BALANCED" for s in result["storeys"])
            else "CUT_CONTROLS_INCOMPLETE"
        )
        if spectra:
            try:
                result["base_reactions"] = _base_reference(raw["tables"], modal, modes, spectra)
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                result["base_reaction_reason"] = str(exc)
        if spectra and result["status"] == "SIGNED_CUTS_BALANCED":
            try:
                result["floor_masses"] = _floor_inertia(
                    source, bound["deck"], result["storeys"], story_controls, modal, modes, spectra
                )
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                result["floor_inertia_reason"] = str(exc)
        result["basement_reference"] = basement_reference(source, modal, result["storeys"])
    except (ValueError, RuntimeError, KeyError, TypeError, ArithmeticError) as exc:
        result.update(status="WALL_MODAL_SOURCE_UNQUALIFIED", reason=str(exc))
    return result
