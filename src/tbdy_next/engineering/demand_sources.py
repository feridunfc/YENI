"""Same-run primitive/modal evidence for the existing demand pipeline.

No COM attachment, force synthesis, modal combination or engineering approval.
The native period table supplies the mode denominator; force rows cannot supply it.
"""
from collections import Counter, defaultdict
from decimal import Decimal

from ..analysis_sources import _digest
from ..column_engine.source_bank import native_frame_force_rows
from ..vs05_d4_source_authority import _case_summary, _source_table

SUPPORT_SCHEMA = "tbdy.next.native-demand-support.v1"
EVIDENCE_SCHEMA = "tbdy.next.native-demand-source-evidence.v1"


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
