"""Source-bound design of the frame columns in every captured storey."""
from collections import defaultdict
from math import fsum, isclose, isfinite

from ..column_engine.beam_references import station_budget
from ..column_engine.source_bank import native_frame_force_rows
from ..column_engine.ts500_column import (
    SWAY_PERMITTED, effective_length_factor, effective_stiffness_nmm2, euler_load_kn, moment_magnification_factors, rectangle_properties,
)
from .column_clear_length import proven_clear_length_m
from .column_effective_length import SUPPORT_ENVELOPE, lower_support_factors
from .column_pmm_section import MECHANICAL, _named_row, _rows
from .frame_geometry import build_frame_catalog
from .second_order_basis import (
    AXIAL_IDEALIZATION_APPLICABILITY, AXIAL_IDEALIZATION_METHOD, ROLE, SCHEMA, SWAY_POLICY,
    normalize_second_order_basis,
)

BUILDING_SCHEMA = "tbdy.next.building-design.v1"
FRAME_METHOD = "TS500_7_21_SWAY_WEB_RM1_SELF_WEIGHT_NMAX"


def normalize_building_design(raw, *, source_data_sha256):
    fields = {"schema", "source_data_sha256", "frame_method", "wall_hinge_aggregate_storeys", "decision_reference"}
    if (not isinstance(raw, dict) or set(raw) - {"maximum_aggregate_mm"} != fields or raw["schema"] != BUILDING_SCHEMA
            or raw["source_data_sha256"] != source_data_sha256 or raw["frame_method"] != FRAME_METHOD):
        raise ValueError("BUILDING_DESIGN_POLICY_OR_SOURCE_INVALID")
    if "maximum_aggregate_mm" in raw:
        aggregate = raw["maximum_aggregate_mm"]
        if type(aggregate) not in (float, int) or not isfinite(aggregate) or aggregate <= 0:
            raise ValueError("MAXIMUM_AGGREGATE_MUST_BE_FINITE_POSITIVE_MM")
    storeys = raw["wall_hinge_aggregate_storeys"]
    ref = raw["decision_reference"]
    if (not isinstance(storeys, list) or any(not isinstance(s, str) or not s or s.strip() != s for s in storeys)
            or len(set(storeys)) != len(storeys) or not isinstance(ref, str) or not ref or ref.strip() != ref):
        raise ValueError("BUILDING_DESIGN_DECISION_INVALID")
    return {**raw, "wall_hinge_aggregate_storeys": sorted(storeys)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def lateral_directions(frame):
    """Map bending about local 2/3 to the orthogonal horizontal storey direction."""
    axes = frame.get("axes_global")
    if not axes or abs(axes[0][2] - 1.0) > 1e-8:
        return {}
    directions = {}
    for moment, displacement in (("M2", axes[2]), ("M3", axes[1])):
        matches = [name for index, name in enumerate(("X", "Y")) if abs(displacement[index]) >= 1 - 1e-8]
        if len(matches) == 1:
            directions[moment] = matches[0]
    return directions if set(directions.values()) == {"X", "Y"} else {}


def storey_compression(source, physical, groups):
    force_source = source["column_axial"]["force_source"]
    names = set(groups["gravity"]) | set(groups["ductile"])
    sums = defaultdict(list)
    for uid, proof in physical.items():
        require(uid in force_source["rowsets"], f"Missing original storey contributor {uid}")
        cut_steps = defaultdict(lambda: defaultdict(set))
        cuts = set()
        pressures = defaultdict(list)
        for row in native_frame_force_rows(force_source["rowsets"][uid], uid):
            case, step, number, p = row[4:8]
            if case in names:
                require(number == 0, f"Unsupported output step in {uid}/{case}")
                cut = (row[1], row[2], row[3])
                cuts.add(cut)
                cut_steps[case][cut].add(step)
                pressures[case].append(-p)
        ends = proof.get("end_cuts", {})
        require(set(ends) == {"I", "J"}, f"Missing physical end identities for {uid}")
        for end in ends.values():
            require(len(end) == 4 and end[0] == uid, f"Invalid physical end identity for {uid}")
            _, obj, element, local = end
            length = ends["J"][1]
            matches = [cut for cut in cuts if cut[1] == element
                       and abs(cut[0]-obj) <= station_budget(cut[0], obj, length)
                       and abs(cut[2]-local) <= station_budget(cut[2], local, length)]
            require(len(matches) == 1, f"Assigned forces lack a unique physical end cut for {uid}")
        for case in names:
            expected = {"Single Value"} if case in groups["gravity"] else {"Max", "Min"}
            require(cuts and set(cut_steps[case]) == cuts and all(steps == expected for steps in cut_steps[case].values()),
                    f"Missing assigned case, cut or step in {uid}/{case}")
            sums[case].append(max(0.0, max(pressures[case])))
    return {case: fsum(sums[case]) for case in sorted(names)}


def _axis_restraint(ends, allow_wall_hinge):
    lower, upper = ends.get("I", {}), ends.get("J", {})
    if upper.get("basis") != "FRAME_SECTION_REFERENCE":
        raise ValueError("UPPER_FRAME_END_UNBOUND")
    if lower.get("basis") == "FRAME_SECTION_REFERENCE":
        return effective_length_factor(alpha_i=lower["alpha_web"], alpha_j=upper["alpha_web"],
                                       sway=SWAY_PERMITTED), "FRAME_END_RATIOS"
    if lower.get("basis") == "WALL_BELOW_ROTATIONAL_STIFFNESS_UNBOUND" and not allow_wall_hinge:
        raise ValueError("WALL_BELOW_ROTATIONAL_STIFFNESS_UNBOUND")
    return max(r["k"] for r in lower_support_factors(ends)), SUPPORT_ENVELOPE


def storey_critical_loads(source, storey, physical, ratios, *, allow_wall_hinge):
    """Compute directional Euler sums using the adopted frame-storey assumptions."""
    material_rows = _rows(source["column_axial"]["pmm_section_source"]["table_reads"],
                          MECHANICAL, {"Material"}, {"E1": "kN/m2"})
    loads = defaultdict(list)
    for uid, frame in storey.items():
        if physical[uid].get("status") == "ETABS_WALL_COUPLED_COLUMN_MESH":
            continue  # No Euler credit. Its full compressive demand enters storey_compression.
        length = proven_clear_length_m(physical[uid], uid)
        directions = lateral_directions(frame)
        require(length and directions, f"Storey contributor geometry is unresolved for {uid}")
        modulus = float(_named_row(material_rows, "Material", frame["material_name"], MECHANICAL)["E1"]) / 1000
        dims = frame["dims"]
        section = rectangle_properties(dims.bending_depth_m2_mm, dims.bending_depth_m3_mm)
        for axis, direction in directions.items():
            ends = ratios.get(uid, {}).get(axis, {})
            require(set(ends) == {"I", "J"}, f"Missing storey frame ends for {uid}/{axis}")
            k, _ = _axis_restraint(ends, allow_wall_hinge)
            inertia = section["i22_mm4"] if axis == "M2" else section["i33_mm4"]
            ei = effective_stiffness_nmm2(ec_mpa=modulus, ic_mm4=inertia, creep_ratio=1, method="TS500_7_21")
            loads[direction].append(euler_load_kn(effective_ei_nmm2=ei, effective_length_lk_mm=1000 * length * k))
    return {direction: fsum(values) for direction, values in loads.items()}


def wall_compression_scope(frames, wall_rows):
    """Show signed bottom-pier compression omitted from the frame-only critical-load calculation."""
    by_storey = defaultdict(list)
    for w in wall_rows:
        by_storey[w["story"]].append(w)
    output = []
    for story, record in frames.get("storeys", {}).items():
        for case, frame_nd in record.get("compression_kn", {}).items():
            walls = by_storey[story]
            # Only compare a directly assigned, signed static load combination.
            if not any(c["combination"] == case and c["role"] == "ASSIGNED_STATIC" for w in walls for c in w["cuts"]):
                continue
            values = {}
            for w in walls:
                cuts = [c for c in w["cuts"] if c["combination"] == case and c["face"] == "Bottom"
                        and c.get("force_basis") == "SIGNED_STATIC" and c.get("compression_kn") is not None]
                if w["pier"] and w["pier"] not in values and len(cuts) == 1:
                    values[w["pier"]] = cuts[0]["compression_kn"]
            wall_nd = fsum(values.values())
            complete = len(values) == len(walls) and bool(walls)
            output.append({"story": story, "combination": case, "expected_pier_groups": len(walls),
                "evaluated_pier_groups": len(values), "wall_bottom_compression_by_pier_kn": values,
                "frame_member_max_sum_kn": frame_nd, "known_wall_bottom_compression_kn": wall_nd,
                "omitted_compression_fraction": wall_nd/(wall_nd + frame_nd) if complete and wall_nd + frame_nd > 0 else None,
                "system_status": "STORY_WALL_CRITICAL_LOAD_METHOD_UNSUPPORTED",
                "comparison": "Frame member maxima and pier bottom compression. Coupled system critical load unbound."})
    return output


def _member_restraint_hold(uid, frame, physical, ratios, allow_wall_hinge):
    proof = physical.get(uid, {})
    if proven_clear_length_m(proof, uid) is None:
        return proof.get("status") or "PHYSICAL_COLUMN_FACES_UNAVAILABLE"
    if not lateral_directions(frame):
        return "HORIZONTAL_STORY_AXES_UNBOUND"
    for axis in ("M2", "M3"):
        try:
            _axis_restraint(ratios.get(uid, {}).get(axis, {}), allow_wall_hinge)
        except (KeyError, ValueError) as exc:
            return str(exc)
    return None


def _member_basis(frame, ratios, gravity, totals, allow_wall_hinge):
    axes = {}
    for axis, direction in lateral_directions(frame).items():
        ends = ratios[axis]
        k, method = _axis_restraint(ends, allow_wall_hinge)
        axes[axis] = {
            "k": k, "k_source": {"method": method, "section": "alpha_web"},
            "sway": SWAY_PERMITTED, "creep_ratio_rm": 1.0, "ei_method": "TS500_7_21",
            "cm_policy": "UNITY", "eq729_length_reading": "EFFECTIVE_LENGTH",
            "decision_reference": "Model-derived framing or a lower-support envelope, rectangular webs and sway permitted.",
            "story_aggregates": totals[direction],
        }
    return {"axes": axes, "combinations": sorted(totals["X"]),
            "applicability": AXIAL_IDEALIZATION_APPLICABILITY,
            "decision_reference": "Prismatic frame member with verified support identities on both axes.",
            "axial_idealization": {"method": AXIAL_IDEALIZATION_METHOD, "combinations": sorted(gravity),
                "decision_reference": "Member maximum compression for factors and local compression for signed PMM."}}


def building_frame_basis(source, physical, ratios, pmm, scope):
    """Freeze the native column roster before solving. Each storey uses all its contributors."""
    policy = source["building_design"]
    request = source["column_axial"]["request"]
    groups = (request.get("design_assignment") or {}).get("groups", {})
    assignments = list(request.get("combinations", ()))
    loads = set(assignments)
    frames, _, _ = build_frame_catalog(source)
    native = source.get("geometry_capture", {}).get("tables", {}).get("COLUMN_CONNECTIVITY", {})
    by_storey = defaultdict(dict)
    seen = set()
    for row in native.get("rows", ()):
        uid, story = row["UniqueName"], row["Story"]
        require(isinstance(uid, str) and uid and isinstance(story, str) and story and uid not in seen,
                "BUILDING_COLUMN_IDENTITY_INVALID")
        by_storey[story][uid] = row["ColumnBay"]
        seen.add(uid)
    require(native.get("row_count") == len(seen) and seen, "BUILDING_COLUMN_CENSUS_INCOMPLETE")
    require(set(policy["wall_hinge_aggregate_storeys"]) <= by_storey.keys(), "BUILDING_HINGE_STOREY_UNKNOWN")
    old = source.get("second_order_basis") or {}
    existing = old.get("members", {})
    require(existing.keys() <= seen, "SECOND_ORDER_BASIS_MEMBER_OUTSIDE_PHYSICAL_ROSTER")
    if old:
        require(old["source_analysis_order"] == "FIRST_ORDER" and old["global_factor_policy"] == SWAY_POLICY,
                "BUILDING_DESIGN_SECOND_ORDER_POLICY_CONFLICT")
    bound_cuts = defaultdict(set)
    for entry in (scope or {}).get("instances", ()):
        if entry.get("configured_cut_coverage", {}).get("exact_cut_census") is True and entry.get(
                "independent_cut_census_proven") is True:
            bound_cuts[entry["element_id"]].add(entry["combination"])
    held = None
    if (not pmm or pmm.get("analysis_order") != "FIRST_ORDER" or not pmm.get("archived_solver_log_sha256")):
        held = "FIRST_ORDER_ASSIGNED_CASE_GENERATION_UNBOUND"
    elif (not loads or set(groups) != {"gravity", "ductile"} or not all(groups.values())
          or set(groups["gravity"]) & set(groups["ductile"])
          or set(groups["gravity"]) | set(groups["ductile"]) != loads):
        held = "FRAME_STOREY_ASSIGNED_COMBINATIONS_UNSUPPORTED"
    members, storeys = {}, {}
    # An explicitly calibrated end may be used for its original member only.
    calibrated = {uid for uid, item in existing.items() if all("k_source" not in a for a in item["axes"].values())}
    for story, labels in sorted(by_storey.items()):
        rows = {uid: {"label": label} for uid, label in sorted(labels.items())}
        record = {"columns": rows, "expected_count": len(rows)}
        storeys[story] = record
        storey = {uid: f for uid, f in frames.items() if f["type"] == "Column" and f["story"] == story}
        source_error = held
        if set(storey) != set(rows):
            source_error = "FRAME_STOREY_COLUMN_CATALOG_MISMATCH"
        elif any(bound_cuts[uid] != loads for uid in rows):
            source_error = "FRAME_STOREY_ASSIGNED_CUT_POPULATION_INCOMPLETE"
        totals, nd = {}, {}
        layer = {uid: physical.get(uid, {}) for uid in rows}
        allow_wall_hinge = story in policy["wall_hinge_aggregate_storeys"]
        if not source_error:
            try:
                nd = storey_compression(source, layer, groups)
                require(all(isfinite(v) and v > 0 for v in nd.values()), "FRAME_STOREY_COMPRESSION_UNSUPPORTED")
                record["compression_kn"] = nd
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                source_error = str(exc)
        if not source_error:
            try:
                nk = storey_critical_loads(source, storey, layer, ratios,
                                          allow_wall_hinge=allow_wall_hinge)
                require(set(nk) == {"X", "Y"} and all(isfinite(v) and v > 0 for v in nk.values()),
                        "FRAME_STOREY_STIFFNESS_UNSUPPORTED")
                totals = {direction: {case: {"nd_kn": load, "nk_kn": nk[direction],
                          "reference": f"All {len(layer)} frame columns on {story}, {direction}, {case}."}
                          for case, load in nd.items()} for direction in ("X", "Y")}
                record["critical_load_kn"] = nk
                excluded = sorted(u for u, v in layer.items() if v.get("status") == "ETABS_WALL_COUPLED_COLUMN_MESH")
                record["frame_sway_bound"] = {
                    "scope": "FRAME_COLUMN_COMPRESSION_ONLY", "compression_members": sorted(layer),
                    "euler_members": sorted(layer.keys()-set(excluded)), "zero_credit_columns": excluded,
                    "wall_euler_credit_kn": 0., "wall_compression_in_numerator": False,
                    "max_compression_case": max(nd, key=nd.get), "max_compression_kn": max(nd.values()),
                    "minimum_critical_load_kn": nk,
                    "max_load_ratio": {d: max(nd.values())/v for d, v in nk.items()},
                    "max_beta_story": {d: moment_magnification_factors(nd_kn=0., nk_kn=v, sway=SWAY_PERMITTED,
                        allow_noncompression=True, story_nd_kn=max(nd.values()), story_nk_kn=v)["beta_story"]
                        for d,v in nk.items()},
                }
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                record["aggregate_hold"] = str(exc)
        else:
            record["aggregate_hold"] = source_error
        for uid, row in rows.items():
            if uid in calibrated and not source_error:
                # A known contradiction in a shared storey demand cannot be overridden by an older member input.
                declared = existing[uid]["axes"]
                if any(set(a["story_aggregates"]) != loads or any(
                        not isclose(a["story_aggregates"][case]["nd_kn"], nd[case], rel_tol=1e-12, abs_tol=1e-8)
                        for case in loads) for a in declared.values()):
                    row.update(basis="HOLD", reason="EXPLICIT_MEMBER_STOREY_COMPRESSION_DIFFERS")
                    continue
                if totals and any(not isclose(declared[axis]["story_aggregates"][case]["nk_kn"],
                                              totals[direction][case]["nk_kn"], rel_tol=1e-12, abs_tol=1e-8)
                                  for axis, direction in lateral_directions(storey[uid]).items() for case in loads):
                    row.update(basis="HOLD", reason="EXPLICIT_MEMBER_STOREY_CRITICAL_LOAD_DIFFERS")
                    continue
                members[uid] = existing[uid]
                row["basis"] = "EXPLICIT_MEMBER_BASIS"
                continue
            reason = source_error or _member_restraint_hold(uid, storey[uid], physical, ratios, allow_wall_hinge)
            if not reason and not totals:
                reason = record["aggregate_hold"]
            if reason:
                row.update(basis="HOLD", reason=reason)
                continue
            members[uid] = _member_basis(storey[uid], ratios[uid], groups["gravity"], totals, allow_wall_hinge)
            row["basis"] = "ENGINE_FRAME_ENDS_AND_STOREY_LOADS"
    basis = None
    if members:
        document = {"schema": SCHEMA, "basis_id": "building-frame-storeys", "basis_role": ROLE,
            "engineering_approval": "NOT_GRANTED", "source_data_sha256": policy["source_data_sha256"],
            "source_analysis_order": "FIRST_ORDER", "source_order_reference": pmm["archived_solver_log_sha256"],
            "global_factor_policy": SWAY_POLICY, "global_factor_reference": policy["decision_reference"],
            "members": members}
        basis = normalize_second_order_basis(document, source_data_sha256=policy["source_data_sha256"])
    return basis, {"schema": "tbdy.next.building-frame-results.v1", "frame_method": FRAME_METHOD,
                   "expected_columns": len(seen), "bound_columns": len(members), "storeys": storeys}
