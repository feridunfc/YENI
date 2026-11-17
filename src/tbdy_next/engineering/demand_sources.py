"""Same-run primitive/modal evidence for the existing demand pipeline.

No COM attachment, force synthesis, modal combination or engineering approval.
The native period table supplies the mode denominator; force rows cannot supply it.
"""
from collections import Counter, defaultdict
from decimal import Decimal

from ..analysis_sources import _digest
from ..column_engine.source_bank import native_frame_force_rows
from ..diaphragm_linkage import MODAL_FIELDS, MODAL_UNITS, _decimal, _read_table
from ..diaphragm_probe import SCHEMA as MODAL_PROBE_SCHEMA, SPECTRUM_MODAL_TABLE
from ..vs05_d4_source_authority import _case_summary, _source_table

SUPPORT_SCHEMA = "tbdy.next.native-demand-support.v1"
EVIDENCE_SCHEMA = "tbdy.next.native-demand-source-evidence.v1"
MODAL_PARAMETER_SCHEMA = "tbdy.next.spectral-modal-parameters.v1"


def demand_capture_plan(source, combination_plan):
    tables = (source.get("vs04_basis_probe") or {}).get("table_reads") or {}
    catalog = _case_summary(tables, require_key=True)
    leaves = sorted({name for combo in combination_plan["combinations"]
                     for name in combo.get("case_names", ())})
    if not leaves or any(name not in catalog for name in leaves):
        raise ValueError("DEMAND_PRIMITIVE_CASE_LINEAGE_UNAVAILABLE")
    if any(catalog[n]["type"] not in {"Linear Static", "Response Spectrum"} for n in leaves):
        raise ValueError("DEMAND_PRIMITIVE_CASE_TYPE_UNSUPPORTED")
    spectrum = [n for n in leaves if catalog[n]["type"] == "Response Spectrum"]
    modal_bindings = {}
    modes = {}
    if spectrum:
        rows = _source_table(tables, "Load Case Definitions - Response Spectrum",
                             {"Name", "ModalCase"}, require_key=True)
        for name in spectrum:
            refs = {r["ModalCase"] for r in rows if r["Name"] == name}
            if len(refs) != 1 or catalog.get(next(iter(refs)), {}).get("type") not in {"Modal - Eigen", "Modal - Ritz"}:
                raise ValueError("DEMAND_SPECTRUM_MODAL_BINDING_UNAVAILABLE:" + name)
            modal_bindings[name] = next(iter(refs))
        periods = _source_table((source.get("analysis_sources") or {}).get("tables") or {},
                                "Modal Periods And Frequencies", {"Case", "Mode"}, require_key=True)
        for name in sorted(set(modal_bindings.values())):
            values = [Decimal(str(r["Mode"])) for r in periods if r["Case"] == name]
            if (not values or any(not v.is_finite() or v != v.to_integral_value() or not 1 <= v <= 5000 for v in values)
                    or len(values) != len(set(values))):
                raise ValueError("DEMAND_MODAL_PERIOD_INVENTORY_INVALID:" + name)
            expected = sorted(map(int, values))
            if expected != list(range(1, max(expected) + 1)):
                raise ValueError("DEMAND_MODAL_PERIOD_INVENTORY_INCOMPLETE:" + name)
            modes[name] = expected
    cases = sorted(set(leaves) | set(modes))
    return {"cases": cases, "case_definitions": {n: catalog[n] for n in cases},
            "primitive_cases": leaves, "spectrum_modal_bindings": modal_bindings,
            "modal_modes": modes, "mode_inventory_basis": "SAME_CAPTURE_MODAL_PERIODS_TABLE"}


def _verified_support(source, combination_plan):
    feature = source.get("column_axial") or {}
    support = feature.get("demand_support")
    if not isinstance(support, dict) or support.get("schema") != SUPPORT_SCHEMA:
        raise ValueError("NATIVE_DEMAND_SUPPORT_NOT_CAPTURED")
    plan = demand_capture_plan(source, combination_plan)
    if support.get("plan") != plan:
        raise ValueError("NATIVE_DEMAND_SUPPORT_PLAN_MISMATCH")
    force = support.get("force_source") or {}
    if not isinstance(force, dict):
        raise ValueError("NATIVE_DEMAND_SUPPORT_CONTRACT_INVALID")
    during = force.get("output_selection_during") or {}
    before, after = force.get("output_selection_before"), force.get("output_selection_after")
    members = set((feature.get("force_source") or {}).get("rowsets", {})) | set((feature.get("force_source") or {}).get("errors", {}))
    rowsets, errors = force.get("rowsets"), force.get("errors")
    states = (before, during, after)
    if any(not isinstance(state, dict) or set(state) != {"cases", "combos"}
           or any(not isinstance(g, dict) or any(type(v) is not bool for v in g.values())
                  for g in state.values()) for state in states):
        raise ValueError("NATIVE_DEMAND_SUPPORT_SELECTION_INVALID")
    if any(set(before[k]) != set(during[k]) for k in ("cases", "combos")):
        raise ValueError("NATIVE_DEMAND_SUPPORT_CATALOG_CHANGED")
    if (force.get("schema") != "tbdy.next.etabs-frame-force-source.v1"
            or force.get("api") != "Results.FrameForce" or force.get("item_type") != "ObjectElm"
            or force.get("units_code") != 6 or not before or before != after
            or {n for n, selected in during.get("cases", {}).items() if selected} != set(plan["cases"])
            or any(during.get("combos", {}).values())
            or not isinstance(rowsets, dict) or not isinstance(errors, dict)
            or set(rowsets) & set(errors) or set(rowsets) | set(errors) != members):
        raise ValueError("NATIVE_DEMAND_SUPPORT_CONTRACT_INVALID")
    if plan["modal_modes"]:
        option = force.get("mode_shape_option") or {}
        selected = option.get("during")
        if (any(not isinstance(option.get(k), list) or len(option[k]) != 3
                or any(type(v) is not int for v in option[k][:2]) or type(option[k][2]) is not bool
                for k in ("before", "during", "after")) or selected[2] is not True
                or option["before"] != option.get("after")
                or force.get("expected_modal_modes") != plan["modal_modes"]):
            raise ValueError("NATIVE_DEMAND_MODAL_SELECTION_UNVERIFIED")
    return plan, force


def component_force_rows(source, uid, combination_plan):
    """Expose same-source signed primitive rows to the existing component algebra."""
    feature = source.get("column_axial") or {}
    rows = list(native_frame_force_rows(feature["force_source"]["rowsets"][uid], uid))
    if "demand_support" not in feature:
        return rows  # Existing sealed archives retain their original evidence scope.
    plan, force = _verified_support(source, combination_plan)
    if uid not in force["rowsets"]:
        raise ValueError("NATIVE_DEMAND_MEMBER_UNAVAILABLE:" + uid)
    for row in native_frame_force_rows(force["rowsets"][uid], uid):
        if row[4] not in plan["case_definitions"]:
            raise ValueError("NATIVE_DEMAND_UNREQUESTED_CASE")
        if plan["case_definitions"][row[4]]["type"] == "Linear Static":
            if row[5] not in ("Single Value", "") or row[6] != 0:
                raise ValueError("NATIVE_DEMAND_STATIC_STEP_UNVERIFIED")
            rows.append(row)
    if len({r[:7] for r in rows}) != len(rows):
        raise ValueError("NATIVE_DEMAND_CASE_COMBINATION_IDENTITY_COLLISION")
    return rows


def spectral_modal_parameters(source, plan):
    """Bind existing selected-case output, never the failed initial display read.

    Reuse the strict native table/number contracts. Expected modes come from the
    independent period inventory, not from successfully returned parameter rows.
    Binding displayed parameters does not qualify modal response reconstruction.
    """
    bindings = plan["spectrum_modal_bindings"]
    result = {"schema": MODAL_PARAMETER_SCHEMA, "status": "BLOCKED_SOURCE",
              "source_path": "vs04_diaphragm_probe.spectrum_modal_selected_cases",
              "expected_case_count": len(bindings), "bound_case_count": 0,
              "expected_mode_rows": sum(len(plan["modal_modes"][m]) for m in bindings.values()),
              "bound_mode_rows": 0, "cases": [], "reason_codes": [],
              "native_full_precision_proven": False, "physical_concurrency_proven": False,
              "modal_superposition_qualified": False, "spectral_alpha_authorized": False,
              "engineering_release": "NOT_READY",
              "remaining_requirements": ["MODAL_OUTPUT_PRECISION_NOT_QUALIFIED",
                  "ACCIDENTAL_TORSION_CONTRIBUTIONS_NOT_BOUND",
                  "MODAL_DIRECTIONAL_AGGREGATION_NOT_INDEPENDENTLY_VERIFIED",
                  "SCWB_AXIAL_POLICY_AND_STORY_SHEAR_ALLOCATION_NOT_APPROVED"]}
    if not bindings:
        result.update(status="NOT_REQUIRED_NO_SPECTRAL_LEAVES", remaining_requirements=[])
        result["sha256"] = _digest(result)
        return result
    for case, modal in sorted(bindings.items()):
        result["cases"].append({"case": case, "case_guid": plan["case_definitions"][case]["guid"],
            "modal_case": modal, "modal_case_guid": plan["case_definitions"][modal]["guid"],
            "expected_modes": list(plan["modal_modes"][modal]), "expected_mode_count": len(plan["modal_modes"][modal]),
            "bound_mode_count": 0, "status": "BLOCKED_SOURCE", "mode_rows": [], "reason_codes": []})
    try:
        probe = source.get("vs04_diaphragm_probe") or {}
        analysis = source.get("analysis_sources") or {}
        basis = source.get("vs04_basis_probe") or {}
        selection = probe.get("temporary_display_cases")
        if (not isinstance(probe, dict) or probe.get("schema") != MODAL_PROBE_SCHEMA
                or (source.get("capture_metadata") or {}).get("vs04_same_session_capture") is not True
                or probe.get("display_selection_restored") is not True
                or type(probe.get("units_before")) is not int or probe["units_before"] != 6
                or type(probe.get("units_after")) is not int or probe["units_after"] != 6
                or not isinstance(selection, list) or any(not isinstance(n, str) or not n for n in selection)
                or len(set(selection)) != len(selection) or not set(bindings).issubset(selection)):
            raise ValueError("SPECTRAL_MODAL_SELECTED_CAPTURE_CONTEXT_INVALID")
        if (basis.get("schema") != "tbdy.next.vs04e.basis-source-probe.v1"
                or basis.get("read_only_invariant_proven") is not True
                or type(basis.get("units_before")) is not int or basis["units_before"] != 6
                or type(basis.get("units_after")) is not int or basis["units_after"] != 6
                or not isinstance(basis.get("display_cases_before"), list)
                or basis["display_cases_before"] != basis.get("display_cases_after")):
            raise ValueError("SPECTRAL_MODAL_BASIS_CAPTURE_CONTEXT_INVALID")
        if (analysis.get("schema") != "tbdy.next.vs04.analysis-sources.v1"
                or analysis.get("display_selection_restored") is not True
                or type(analysis.get("units_before")) is not int or analysis["units_before"] != 6
                or type(analysis.get("units_after")) is not int or analysis["units_after"] != 6):
            raise ValueError("SPECTRAL_MODAL_PERIOD_CAPTURE_CONTEXT_INVALID")
        table = probe.get("spectrum_modal_selected_cases")
        rows = _read_table(table, SPECTRUM_MODAL_TABLE, set(MODAL_FIELDS),
                          {**MODAL_UNITS, "DampRatio": "", "Mode": "", "SpecCase": "", "ModalCase": ""})
        if any(r["SpecCase"] not in selection for r in rows):
            raise ValueError("SPECTRAL_MODAL_ROW_OUTSIDE_SELECTED_CASES")
        period_table = (analysis.get("tables") or {}).get("Modal Periods And Frequencies")
        periods = _read_table(period_table, "Modal Periods And Frequencies", {"Case", "Mode", "Period"}, {"Period": "sec"})
        definitions_table = (basis.get("table_reads") or {}).get("Load Case Definitions - Response Spectrum")
        definitions = _read_table(definitions_table, "Load Case Definitions - Response Spectrum",
            {"Name", "ModalCase", "GUID", "LoadName", "CoordSys", "Angle", "Function", "TransAccSF",
             "ModalCombo", "DirCombo", "RigidResp", "EccenRatio"},
            {"Angle": "deg", "TransAccSF": "m/sec2", "EccenRatio": ""})
        result["source_table_sha256"] = _digest(table)
        result["period_table_sha256"] = _digest(period_table)
        result["case_definition_table_sha256"] = _digest(definitions_table)
        result["initial_unselected_read_status"] = (probe.get("spectrum_modal_original_selection") or {}).get("status")
        result["selection_restored"] = True
    except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError) as exc:
        result["reason_codes"] = [str(exc)]
        for case in result["cases"]:
            case["reason_codes"] = [str(exc)]
        result["sha256"] = _digest(result)
        return result
    for case in result["cases"]:
        try:
            name, modal = case["case"], case["modal_case"]
            matches = [r for r in definitions if r["Name"] == name]
            if len(matches) != 1:
                raise ValueError("SPECTRAL_CASE_DEFINITION_MISSING_DUPLICATE_OR_MULTICOMPONENT")
            definition = matches[0]
            if definition["GUID"] != case["case_guid"] or definition["ModalCase"] != modal:
                raise ValueError("SPECTRAL_CASE_GUID_OR_MODAL_BINDING_CONFLICT")
            axis = definition["LoadName"]
            if axis not in ("U1", "U2", "U3"):
                raise ValueError("SPECTRAL_ACCELERATION_AXIS_UNSUPPORTED")
            for key in ("CoordSys", "Function", "ModalCombo", "DirCombo", "RigidResp"):
                if not definition[key].strip() or definition[key] == "None":
                    raise ValueError("SPECTRAL_CASE_DEFINITION_INCOMPLETE:" + key)
            _decimal(definition["Angle"])
            _decimal(definition["TransAccSF"])
            eccentricity = _decimal(definition["EccenRatio"])
            if eccentricity < 0:
                raise ValueError("SPECTRAL_ECCENTRICITY_RATIO_INVALID")
            case.update(active_axis=axis, coordinate_system=definition["CoordSys"], angle_deg=definition["Angle"],
                modal_combination=definition["ModalCombo"], directional_combination=definition["DirCombo"],
                rigid_response=definition["RigidResp"], spectrum_function=definition["Function"],
                acceleration_scale_m_s2=definition["TransAccSF"], eccentricity_ratio=definition["EccenRatio"],
                accidental_torsion_status="DEFINED_NONZERO_CONTRIBUTIONS_UNBOUND" if eccentricity else "DEFINED_ZERO_APPLIED_EFFECT_UNPROVEN",
                case_definition_sha256=_digest(definition))
            period_by_mode = {}
            for row in periods:
                if row["Case"] != modal:
                    continue
                mode = _decimal(row["Mode"], positive=True)
                if mode != mode.to_integral_value() or int(mode) in period_by_mode:
                    raise ValueError("SPECTRAL_PERIOD_MODE_IDENTITY_INVALID")
                period_by_mode[int(mode)] = _decimal(row["Period"], positive=True)
            if set(period_by_mode) != set(case["expected_modes"]):
                raise ValueError("SPECTRAL_PERIOD_MODE_POPULATION_CONFLICT")
            selected = {}
            duplicate = set()
            for row in rows:
                if row["SpecCase"] != name:
                    continue
                mode = _decimal(row["Mode"], positive=True)
                if mode != mode.to_integral_value():
                    raise ValueError("SPECTRAL_PARAMETER_MODE_IDENTITY_INVALID")
                mode = int(mode)
                if mode in selected:
                    duplicate.add(mode)
                selected[mode] = row
            case["missing_modes"] = sorted(set(case["expected_modes"]) - set(selected))
            case["unexpected_modes"] = sorted(set(selected) - set(case["expected_modes"]))
            case["duplicate_modes"] = sorted(duplicate)
            if case["missing_modes"] or case["unexpected_modes"] or duplicate:
                case["reason_codes"].append("SPECTRAL_PARAMETER_MODE_POPULATION_CONFLICT")
            for mode in case["expected_modes"]:
                if mode not in selected or mode in duplicate:
                    continue
                row = selected[mode]
                try:
                    if row["ModalCase"] != modal or _decimal(row["Period"], positive=True) != period_by_mode[mode]:
                        raise ValueError("SPECTRAL_PARAMETER_MODAL_CASE_OR_PERIOD_CONFLICT")
                    damping = _decimal(row["DampRatio"])
                    if not 0 <= damping <= 1:
                        raise ValueError("SPECTRAL_PARAMETER_ACTIVE_DAMPING_INVALID")
                    for direction in ("U1", "U2", "U3"):
                        acceleration, amplitude = _decimal(row[direction + "Acc"]), _decimal(row[direction + "Amp"])
                        if direction != axis and (acceleration != 0 or amplitude != 0):
                            raise ValueError("SPECTRAL_PARAMETER_UNEXPECTED_AXIS_RESPONSE")
                    case["mode_rows"].append({"mode": mode, "native_values": dict(row), "source_row_sha256": _digest(row)})
                except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                    case["reason_codes"].append(f"MODE_{mode}:{exc}")
            case["bound_mode_count"] = len(case["mode_rows"])
            if case["mode_rows"]:
                damping = [_decimal(r["native_values"]["DampRatio"]) for r in case["mode_rows"]]
                case.update(active_damping_min=str(min(damping)), active_damping_max=str(max(damping)))
            case["status"] = "NATIVE_MODAL_PARAMETERS_BOUND" if not case["reason_codes"] else "SOURCE_PARTIAL"
        except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
            case["reason_codes"].append(str(exc))
    result["bound_case_count"] = sum(r["status"] == "NATIVE_MODAL_PARAMETERS_BOUND" for r in result["cases"])
    result["bound_mode_rows"] = sum(r["bound_mode_count"] for r in result["cases"])
    result["status"] = ("NATIVE_MODAL_PARAMETERS_BOUND" if result["bound_case_count"] == result["expected_case_count"] else "SOURCE_PARTIAL")
    result["sha256"] = _digest(result)
    return result


def native_demand_source_evidence(source, axial, scope, *, input_sha):
    """Check every configured element-side cut in every independently expected mode."""
    from .column_pmm import _required_cut_coverage
    from .mixed_demands import native_load_patterns

    result = {"schema": EVIDENCE_SCHEMA, "input_sha256": input_sha,
              "scope": "CONFIGURED_REQUIRED_CUTS_BY_MEMBER_CASE_AND_MODE",
              "engineering_release": "NOT_READY", "formal_compliance": "NOT_PROVEN",
              "physical_concurrency_proven": False, "independent_all_cut_census_proven": False,
              "spectral_alpha_authorized": False, "rows": [], "reason_codes": []}
    tables = (source.get("vs04_basis_probe") or {}).get("table_reads") or {}
    try:
        patterns = native_load_patterns(tables)
        result["load_pattern_count"] = len(patterns)
        result["load_pattern_definitions_captured"] = True
    except (ValueError, KeyError, TypeError) as exc:
        result.update(load_pattern_definitions_captured=False, load_pattern_count=0)
        result["reason_codes"].append("LOAD_PATTERN_DEFINITIONS_UNAVAILABLE:" + str(exc))
    try:
        plan, force = _verified_support(source, (axial or {}).get("combination_plan") or {})
        result["plan"] = plan
        result["source_sha256"] = _digest(source["column_axial"]["demand_support"])
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        result.update(status="BLOCKED_SOURCE", completed_member_case_count=0,
                      reason_codes=result["reason_codes"] + [str(exc)])
        result["sha256"] = _digest(result)
        return result
    result["spectral_modal_parameters"] = spectral_modal_parameters(source, plan)
    grids = (scope or {}).get("configured_output_cuts") or {}
    members = sorted({x["element_id"] for x in (scope or {}).get("instances", ())})
    result["expected_member_case_count"] = len(members) * len(plan["cases"])
    result["reason_codes"].extend((scope or {}).get("dependency_blockers", ()))
    if not members:
        result["reason_codes"].append("NATIVE_DEMAND_MEMBER_SCOPE_UNAVAILABLE")
    for uid in members:
        by_case = defaultdict(list)
        member_error = None
        try:
            for row in native_frame_force_rows(force["rowsets"][uid], uid):
                if row[4] not in plan["cases"]:
                    raise ValueError("NATIVE_DEMAND_UNREQUESTED_CASE")
                by_case[row[4]].append(row)
        except (KeyError, ValueError, TypeError) as exc:
            member_error = str(exc)
        grid = grids.get(uid) or {}
        for name in plan["cases"]:
            errors = []
            record = {"member_id": uid, "case": name, "case_type": plan["case_definitions"][name]["type"],
                      "expected_cut_slices": 0, "matched_cut_slices": 0, "missing_slices": []}
            if member_error:
                errors.append("NATIVE_DEMAND_MEMBER_UNAVAILABLE:" + member_error)
            if grid.get("status") != "REQUIRED_SUBSET_BOUND":
                errors.append("NATIVE_DEMAND_CONFIGURED_CUTS_UNBOUND")
            mode_ids = plan["modal_modes"].get(name)
            groups = defaultdict(list)
            expected = ([("Mode", m) for m in mode_ids] if mode_ids else
                        [("Max", 0)] if name in plan["spectrum_modal_bindings"] else [("Single Value", 0)])
            if name in plan["spectrum_modal_bindings"]:
                # Primitive ETABS response-spectrum cases expose scalar Max results.
                # This is not the Max/Min contract of a mixed design combination.
                record["force_semantics"] = "NATIVE_RESPONSE_SPECTRUM_SCALAR_MAXIMUM"
            if grid.get("status") == "REQUIRED_SUBSET_BOUND":
                record["expected_cut_slices"] = len(grid["cuts"]) * len(expected)
            for row in by_case[name]:
                step = (row[5] or "Single Value", row[6])
                if step not in expected:
                    errors.append("NATIVE_DEMAND_UNEXPECTED_STEP")
                groups[step].append(row)
            if mode_ids:
                record["expected_mode_count"] = len(mode_ids)
                record["observed_mode_ids"] = sorted({r[6] for r in by_case[name] if r[5] == "Mode"})
                record["observed_mode_count"] = len(record["observed_mode_ids"])
            if not errors:
                for step in expected:
                    values = groups[step]
                    if len({r[:4] for r in values}) != len(values):
                        errors.append("NATIVE_DEMAND_AMBIGUOUS_STEP_AT_CUT")
                    coverage = _required_cut_coverage(values, grid)
                    record["matched_cut_slices"] += coverage["matched_count"]
                    if coverage["matched_count"] != coverage["required_count"]:
                        record["missing_slices"].append({"step_type": step[0], "step_number": step[1],
                                                         **coverage})
                if record["missing_slices"]:
                    errors.append("NATIVE_DEMAND_REQUIRED_CASE_MODE_CUTS_MISSING")
            record.update(status="SOURCE_PARTIAL" if errors else "REQUIRED_SOURCE_COVERAGE_COMPLETE",
                          reason_codes=sorted(set(errors)))
            result["rows"].append(record)
    result["status_counts"] = dict(Counter(r["status"] for r in result["rows"]))
    result["completed_member_case_count"] = sum(r["status"] == "REQUIRED_SOURCE_COVERAGE_COMPLETE" for r in result["rows"])
    result["status"] = ("REQUIRED_SOURCE_COVERAGE_COMPLETE" if not result["reason_codes"]
                        and result["completed_member_case_count"] == result["expected_member_case_count"] else "SOURCE_PARTIAL")
    result["sha256"] = _digest(result)
    return result
