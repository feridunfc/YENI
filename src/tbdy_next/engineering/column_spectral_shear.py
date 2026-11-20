"""Selected-cage column shear under assigned scalar response-spectrum envelopes (TBDY 7.3.7)."""
from collections import defaultdict
from math import isclose, pi

from ..column_engine.beam_references import station_budget
from ..column_engine.native_archive import finite
from ..column_engine.scwb_kernel import column_axis_interval_bound
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.transverse_kernel import shear_reference
from ..vs05_d4_source_authority import _source_table
from .design_scenario import _digest
from .mixed_demands import SCHEMA as MIXED_SCHEMA, SPECTRAL_METHOD, _number, linear_coefficients, native_graph
from .scwb_axial import _configured_end


def _model_controls(source, names):
    """Identify a unique model combination by its coefficients and case-bound horizontal D."""
    tables, cases, graph = native_graph(source)
    spectra = _source_table(tables, "Load Case Definitions - Response Spectrum",
                            {"Name", "Function", "LoadName"}, require_key=True)
    curves = _source_table(tables, "Functions - Response Spectrum - TSC-2018",
                           {"Name", "D", "Direction"}, require_key=True)
    coefficients = {}
    for name, group in graph.items():
        terms = group.get("rows") or []
        if (group.get("operator_etabs") == "Linear Add" and terms
                and all(t["ref_type"] == "CASE" for t in terms)
                and len({t["ref"] for t in terms}) == len(terms)):
            coefficients[name] = linear_coefficients(name, graph, cases)
    controls = {}
    for name in names:
        terms = coefficients.get(name, {})
        rs = {n for n in terms if cases[n]["type"] == "Response Spectrum"}
        definitions = [r for r in spectra if r["Name"] in rs]
        if (not rs or {r["Name"] for r in definitions} != rs
                or any(r["LoadName"] not in ("U1", "U2") for r in definitions)):
            continue
        functions = {r["Function"] for r in definitions}
        factors = [r for r in curves if r["Name"] in functions and r["D"] not in ("", "None", None)]
        if ({r["Name"] for r in factors} != functions or any(r["Direction"] != "Horizontal" for r in factors)):
            continue
        values = {_number(r["D"]) for r in factors}
        if len(values) != 1:
            continue
        d = values.pop()
        if d <= 1:
            continue
        target = {n: v*d if n in rs else v for n, v in terms.items()}
        matches = [key for key, terms_ in coefficients.items() if terms_ == target]
        if len(matches) == 1:
            controls[name] = {"combination": matches[0], "d_factor": float(d),
                              "spectral_cases": sorted(rs), "spectrum_functions": sorted(functions)}
    return controls


def shear_context(source, axial, scope, mixed, dependencies, input_sha):
    plan = (axial or {}).get("combination_plan") or {}
    groups = (plan.get("design_assignment") or {}).get("groups") or {}
    spectral = {c["name"] for c in plan.get("combinations", ()) if c.get("force_semantics") == "SCALAR_COMPONENT_ENVELOPE"}
    names = sorted(spectral & set(groups.get("ductile", ())))
    if plan.get("source") != "ASSIGNED_DESIGN" or not names or not dependencies:
        return None
    context = {"names": names, "scope": scope, "input_sha256": input_sha, "pairs": defaultdict(dict),
               "controls": {}, "error": None}
    if (plan.get("blockers") or not input_sha or not scope or scope.get("input_sha256") != input_sha
            or scope.get("dependency_blockers") or not mixed or mixed.get("input_sha256") != input_sha
            or dependencies.get("input_sha256") != input_sha or mixed.get("schema") != MIXED_SCHEMA
            or mixed.get("method") != SPECTRAL_METHOD
            or mixed.get("source_payload_sha256") != dependencies.get("source_payload_sha256")
            or mixed.get("reason_codes") or not mixed.get("primitive_source_sha256")
            or mixed.get("sha256") != _digest({k: v for k, v in mixed.items() if k != "sha256"})):
        context["error"] = "SPECTRAL_SHEAR_SAME_SOURCE_SCOPE_UNVERIFIED"
        return context
    for row in mixed["rows"]:
        by_name = context["pairs"][row["member_id"]]
        if row["combination"] in by_name:
            context["error"] = "SPECTRAL_SHEAR_DUPLICATE_MEMBER_COMBINATION"
        by_name[row["combination"]] = row
    try:
        context["controls"] = _model_controls(source, names)
    except (KeyError, TypeError, ValueError, ArithmeticError):
        pass  # The unreduced calculation is independent of the optional model control.
    return context


def _cut_match(end_key, keys, length):
    matches = [c for c in keys if c[0] == end_key[0] and c[2] == end_key[2]
               and all(abs(c[i] - end_key[i]) <= station_budget(c[i], end_key[i], length) for i in (1, 3))]
    if len(matches) != 1:
        raise ValueError("SPECTRAL_SHEAR_END_CUT_UNBOUND")
    return matches[0]


def _case_cuts(uid, name, pair, native, expected):
    if not pair or pair.get("status") != "SAME_SOURCE_COMPONENT_REPLAY_MATCH":
        raise ValueError("SPECTRAL_SHEAR_COMPONENT_REPLAY_UNRESOLVED")
    cuts = {tuple(c["native_cut"]): c for c in pair["cuts"]}
    if (set(cuts) != expected or len(cuts) != len(pair["cuts"]) or not cuts
            or len(cuts) != pair["expected_cut_count"]):
        raise ValueError("SPECTRAL_SHEAR_NATIVE_CUT_CENSUS_CONFLICT")
    for key, cut in cuts.items():
        rows = native.get((name, key), {})
        if (key[0] != uid or set(rows) != {"Min", "Max"} or cut["primitive_replay"]["status"] != "NUMERICAL_MATCH"
                or any(row[6] != 0 for row in rows.values())):
            raise ValueError("SPECTRAL_SHEAR_NATIVE_CASE_STEP_UNVERIFIED")
        nd = [-rows["Max"][7], -rows["Min"][7]]
        if nd[0] > nd[1] or any(not isclose(a, b, abs_tol=1e-9, rel_tol=1e-12)
                                 for bounds in (cut["nd_bounds_kn"], cut["primitive_replay"]["nd_bounds_kn"])
                                 for a, b in zip(nd, bounds, strict=True)):
            raise ValueError("SPECTRAL_SHEAR_AXIAL_INTERVAL_CONFLICT")
    return cuts


def _axis_case(name, axis, bend, cuts, native, end_keys, section, length, control, resistance):
    ends = {}
    for end, key in end_keys.items():
        cut = cuts[key]
        if not cut["configured_required_cut"]:
            raise ValueError("SPECTRAL_SHEAR_CONFIGURED_END_REQUIRED")
        bound = column_axis_interval_bound(section, bend, *cut["nd_bounds_kn"], include_upper=True)
        ends[end] = {"cut": list(key), "nd_interval_kn": bound["nd_interval_kn"],
                     "mr_upper_knm": bound["mr_upper_bound_knm"], "mp_upper_knm": 1.4 * bound["mr_upper_bound_knm"],
                     "anchors": bound["anchors"], "lever_bound_m": bound["lever_bound_m"]}
    moment_term = (ends["I"]["mp_upper_knm"] + ends["J"]["mp_upper_knm"]) / length
    floors, cap_envelopes = [], []
    control_axial_minima = []
    minimum_nd = min(c["nd_bounds_kn"][0] for c in cuts.values())
    for key, cut in sorted(cuts.items()):
        primitive = cut["primitive_replay"]
        center, radius = finite(primitive["center_native"][axis], "static_center"), finite(primitive["radius_native"][axis], "radius")
        if radius < 0:
            raise ValueError("SPECTRAL_SHEAR_NEGATIVE_RADIUS")
        if control:
            p_center = finite(primitive["center_native"]["P"], "static_axial_center")
            p_radius = finite(primitive["radius_native"]["P"], "spectral_axial_radius")
            if p_radius < 0:
                raise ValueError("SPECTRAL_SHEAR_NEGATIVE_AXIAL_RADIUS")
            control_axial_minima.append(-(p_center + control["d_factor"] * p_radius))
        for step, sign in (("Min", -1), ("Max", 1)):
            raw = native[name, key][step][8 if axis == "V2" else 9]
            if not isclose(raw, center + sign*radius, abs_tol=1e-9, rel_tol=1e-12):
                raise ValueError("SPECTRAL_SHEAR_COMPONENT_BOUNDS_CONFLICT")
            floors.append({"cut": list(key), "step": step, "signed_kn": raw})
            if control:
                cap_envelopes.append({"cut": list(key), "step": step, "signed_kn": center + sign*control["d_factor"]*radius})
    governing = max(floors, key=lambda row: abs(row["signed_kn"]))
    floor = abs(governing["signed_kn"])
    ve = max(moment_term, floor)
    ref = resistance(axis, minimum_nd, ve)
    ts, zero = ref["branches"]["ts500"]["vr_kn"], ref["branches"]["zero_concrete"]["vr_kn"]
    if ts is None or min(ts, zero, ref["tbdy_brittle_reference_kn"]) <= 0:
        raise ValueError("SPECTRAL_SHEAR_RESISTANCE_UNRESOLVED")
    limit_n = .05 * section.t2 * section.t3 * section.material.fck / 1000
    low_possible = minimum_nd <= limit_n
    # If any cut can cross the inclusive threshold, check the entire member with Vc=0.
    # This covers both shear-share possibilities without coupling independent extrema.
    selected_vr = zero if low_possible else ts
    cap = {"status": "MODEL_D_COMBINATION_UNRESOLVED", "bounded_ve_kn": None}
    if control:
        high = max(cap_envelopes, key=lambda row: abs(row["signed_kn"]))
        bounded = max(floor, min(moment_term, abs(high["signed_kn"])))
        cap = {**control, "status": "SAME_SOURCE_MODEL_CONTROL", "governing": high,
               "abs_max_kn": abs(high["signed_kn"]), "bounded_ve_kn": bounded,
               "minimum_nd_kn": min(control_axial_minima), "zero_concrete_utilization": bounded / zero,
               "brittle_utilization": bounded / ref["tbdy_brittle_reference_kn"],
               "cut_envelopes": cap_envelopes, "applied_to_assigned_demand": False}
    return {"combination": name, "status": "SPECTRAL_SHEAR_CALCULATED", "axis": axis, "bending_axis": bend,
            "end_moments": ends, "expected_cut_count": len(cuts), "extrema_count": len(floors),
            "vd_floor_kn": floor, "vd_governing": governing, "capacity_term_upper_kn": moment_term,
            "ve_upper_kn": ve, "minimum_nd_kn": minimum_nd, "low_axial_limit_kn": limit_n,
            "concrete_basis": "ZERO_CONCRETE_CONSERVATIVE" if low_possible else "AXIAL_THRESHOLD_EXCLUDED_AT_ALL_CUTS",
            "earthquake_share_and_confinement_required_proven": False, "vr_ts500_min_kn": ts,
            "vr_zero_concrete_kn": zero, "vr_used_kn": selected_vr, "tbdy_eq7_7_limit_kn": ref["tbdy_brittle_reference_kn"],
            "ts500_web_reference_kn": ref["ts500_web_reference_kn"], "resistance_utilization": ve / selected_vr,
            "brittle_utilization": ve / ref["tbdy_brittle_reference_kn"], "cap_control": cap}


def selected_spectral_shear(context, frame, rowset, section, selection, evidence, fywk, length, length_basis,
                            directions, candidate_revision, demand_revision):
    uid = frame["frame_id"]
    names = context["names"]
    result = {"method": "assigned-column-spectral-shear.v1", "member_id": uid, "input_sha256": context["input_sha256"],
              "candidate_revision_sha256": candidate_revision, "clear_length_m": length, "length_basis": length_basis,
              "assigned_combinations": names, "expected_axis_case_count": 2*len(names), "axes": {},
              "status": "SPECTRAL_SHEAR_UNRESOLVED", "reasons": [], "d_reduction_applied": False}
    try:
        if context["error"]:
            raise ValueError(context["error"])
        if (demand_revision is not None or length_basis != "END_OFFSETS_SUBTRACTED" or not candidate_revision
                or section is None or not selection or not fywk or set(directions) != {"V2", "V3"}):
            raise ValueError("SPECTRAL_SHEAR_SELECTED_SECTION_LENGTH_OR_DEMAND_UNBOUND")
        grid = context["scope"]["configured_output_cuts"][uid]
        keys = {end: _configured_end(context["scope"], frame, end)[0] for end in ("I", "J")}
        if not isclose(keys["J"][1]-keys["I"][1], length, abs_tol=1e-8, rel_tol=1e-10):
            raise ValueError("SPECTRAL_SHEAR_OFFSET_LENGTH_CONFLICT")
        native, expected = defaultdict(dict), set()
        for row in native_frame_force_rows(rowset, uid):
            key = row[:4]
            expected.add(key)
            if row[4] in names:
                steps = native[row[4], key]
                if row[5] in steps:
                    raise ValueError("SPECTRAL_SHEAR_DUPLICATE_NATIVE_STEP")
                steps[row[5]] = row
        end_keys = {end: _cut_match(key, expected, grid["length_m"]) for end, key in keys.items()}
        tr = selection["selected_transverse"]
        tie = tr["tie_diameter_mm"]
        center = evidence["cover_to_tie_mm"] + tie + selection["diameter_mm"]/2
        spacing = max(tr["confinement_spacing_mm"], tr["midspan_spacing_mm"])
        if min(tr["confinement_spacing_mm"], tr["midspan_spacing_mm"], tie) <= 0:
            raise ValueError("SPECTRAL_SHEAR_SELECTED_TIE_INVALID")
        def resistance(axis, nd, shear):
            b, h = (section.t3, section.t2) if axis == "V2" else (section.t2, section.t3)
            return shear_reference(n_compression_kn=nd, shear_kn=shear, area_mm2=b*h, bw_mm=b, d_mm=h-center,
                                   fck_mpa=evidence["fck_mpa"], fywk_mpa=fywk, spacing_mm=spacing,
                                   asw_mm2=tr["legs_"+axis.lower()]*pi*tie**2/4,
                                   gamma_c=evidence["fck_mpa"]/evidence["fcd_mpa"], gamma_s=evidence["gamma_s"])
        for axis in ("V2", "V3"):
            cases = []
            for name in names:
                try:
                    pair = context["pairs"].get(uid, {}).get(name)
                    cuts = _case_cuts(uid, name, pair, native, expected)
                    cases.append(_axis_case(name, axis, directions[axis]["bending_axis"], cuts, native, end_keys,
                                            section, length, context["controls"].get(name), resistance))
                except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                    cases.append({"combination": name, "axis": axis, "status": "SPECTRAL_SHEAR_UNRESOLVED", "reason": str(exc)})
            result["axes"][axis] = {"cases": cases, "direction": directions[axis]["direction"]}
        resolved = [c for axis in result["axes"].values() for c in axis["cases"] if c["status"] == "SPECTRAL_SHEAR_CALCULATED"]
        result["calculated_axis_case_count"] = len(resolved)
        if len(resolved) == result["expected_axis_case_count"]:
            result["max_resistance_utilization"] = max(c["resistance_utilization"] for c in resolved)
            result["max_brittle_utilization"] = max(c["brittle_utilization"] for c in resolved)
            result["status"] = ("CONSERVATIVE_SPECTRAL_SHEAR_WITHIN_LIMITS" if
                                max(result["max_resistance_utilization"], result["max_brittle_utilization"]) <= 1
                                else "CONSERVATIVE_BOUND_EXCEEDS_LIMIT_REVIEW_REQUIRED")
    except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
        result["reasons"].append(str(exc))
    return result


def complete_spectral_shear(result, names, uid, input_sha, revision):
    """Read a complete same-cage, same-source two-axis calculation at R14."""
    if (not result or not revision or revision != _digest(result)
            or result.get("member_id") != uid or result.get("input_sha256") != input_sha
            or not input_sha or result.get("status") != "CONSERVATIVE_SPECTRAL_SHEAR_WITHIN_LIMITS"
            or result.get("d_reduction_applied") is not False or not names
            or set(result.get("assigned_combinations", ())) != names
            or set(result.get("axes", {})) != {"V2", "V3"}
            or result.get("calculated_axis_case_count") != 2 * len(names)):
        return False
    for axis, rows in result["axes"].items():
        cases = rows["cases"]
        if len(cases) != len(names) or {c["combination"] for c in cases} != names:
            return False
        for case in cases:
            if (case.get("axis") != axis or case.get("status") != "SPECTRAL_SHEAR_CALCULATED"
                    or case["cap_control"].get("status") != "SAME_SOURCE_MODEL_CONTROL"
                    or not 0 <= case["vd_floor_kn"] <= case["ve_upper_kn"]
                    or not case["ve_upper_kn"] <= min(case["vr_used_kn"], case["tbdy_eq7_7_limit_kn"])):
                return False
    return True
