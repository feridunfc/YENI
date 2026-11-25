"""Supervisor review packet for the source-bound original frame-and-wall project."""
from base64 import b64decode
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import re

from ..column_engine.beam_references import station_budget
from ..column_engine.source_bank import native_frame_force_rows
from .design_scenario import _digest
from .mixed_demands import linear_coefficients, native_graph
from .pier_seismic_shear import wall_load_scope

GAPS = ("GAP-001", "GAP-002", "GAP-003", "GAP-004", "GAP-007")
ABSTOL, RELTOL = Fraction("1e-9"), Fraction("1e-12")
STATIC = ("Grav_TempNeg", "Grav_TempPos", "Grav_Ult")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def export_catalog(deck, graph, cases):
    """Compare the text deck's complete combination book to database tables with rational factors."""
    types, terms, assignments = {}, defaultdict(list), defaultdict(set)
    for line in deck.splitlines():
        if not line.lstrip().startswith("COMBO "):
            continue
        name, prop, value, tail = re.fullmatch(r'\s*COMBO\s+"([^"]+)"\s+(\w+)\s+"([^"]+)"(.*)', line).groups()
        if prop == "TYPE":
            require(not tail.strip() and name not in types, "DUPLICATE_OR_INVALID_COMBO_TYPE")
            types[name] = value
        elif prop in {"LOADCASE", "LOADCOMBO"}:
            scale = re.fullmatch(r'\s+SF\s+(\S+)\s*', tail)
            require(scale, "MISSING_NATIVE_COMBINATION_FACTOR")
            terms[name].append(("CASE" if prop == "LOADCASE" else "COMBO", value, Fraction(scale[1])))
        elif prop == "DESIGN":
            require(tail.strip() == 'COMBOTYPE "Strength"', "UNSUPPORTED_DESIGN_ASSIGNMENT")
            assignments[value].add(name)
        else:
            raise ValueError("UNSUPPORTED_NATIVE_DECK_COMBINATION_FIELD")
    require(types and set(types) == set(terms) == set(graph), "COMBINATION_BOOK_ROSTER_DIFFERS")
    book = {}
    for name, node in sorted(graph.items()):
        expected = terms[name]
        observed = [(r["ref_type"], r["ref"], Fraction(r["factor"])) for r in node["rows"]]
        require(node["operator_etabs"] == types[name] and Counter(observed) == Counter(expected),
                "OPERATOR_OR_SIGNED_FACTOR_DIFFERS:" + name)
        require(all(ref in (cases if typ == "CASE" else graph) for typ, ref, factor in expected),
                "UNRESOLVED_NATIVE_REFERENCE:" + name)
        book[name] = {"operator": types[name], "terms": [[t, r, str(f)] for t, r, f in expected]}
    return book, {k: sorted(v) for k, v in assignments.items()}


def force_index(rowset, uid, names):
    by_case = defaultdict(dict)
    for row in native_frame_force_rows(rowset, uid):
        if row[4] in names:
            key = row[:4]
            require(row[5] in ("", "Single Value") and row[6] == 0 and key not in by_case[row[4]],
                    "MISSING_OR_NONUNIQUE_STATIC_STATE")
            by_case[row[4]][key] = tuple(Fraction(str(v)) for v in row[7:])
    return by_case


def exact_replay(source, grid, cases, graph):
    force = source["column_axial"]
    members = source["geometry_capture"]["tables"]["COLUMN_CONNECTIVITY"]
    roster = {r["UniqueName"] for r in members["rows"]}
    require(len(roster) == members["row_count"] == 87 and roster == set(grid), "STATIC_COLUMN_ROSTER_DIFFERS")
    coefs = {n: linear_coefficients(n, graph, cases) for n in STATIC}
    leaves = {c for v in coefs.values() for c in v}
    require(all(cases[c]["type"] == "Linear Static" for c in leaves), "SIGNED_LINEAR_STATIC_LEAVES_REQUIRED")
    counts = Counter()
    worst, proof = Fraction(), []
    for uid in sorted(roster):
        targets = force_index(force["force_source"]["rowsets"][uid], uid, STATIC)
        primitives = force_index(force["demand_support"]["force_source"]["rowsets"][uid], uid, leaves)
        length = grid[uid]["length_m"]
        configured = [(uid, q["object_station_m"], q["analysis_element_id"], q["element_station_m"])
                      for q in grid[uid]["cuts"]]
        require(configured and len(set(configured)) == len(configured), "CONFIGURED_CUT_ROSTER_INVALID")
        for name, recipe in coefs.items():
            cuts = targets[name]
            require(len(cuts) == len(configured) and all(cuts.keys() == primitives[c].keys() for c in recipe),
                    "MISSING_PRIMITIVE_OR_OPPOSITE_ELEMENT_SIDE:" + uid)
            matched = set()
            for obj, sta, elm, local in configured:
                unique = [k for k in cuts if (k[0], k[2]) == (obj, elm) and
                          abs(k[1]-sta) <= station_budget(k[1], sta, length) and
                          abs(k[3]-local) <= station_budget(k[3], local, length)]
                require(len(unique) == 1 and unique[0] not in matched, "AMBIGUOUS_CONFIGURED_STATIC_CUT")
                key = unique[0]
                matched.add(key)
                expected = [sum(f * primitives[c][key][i] for c, f in recipe.items()) for i in range(6)]
                observed = cuts[key]
                for a, b in zip(expected, observed):
                    error = abs(a-b)
                    worst = max(worst, error)
                    counts["compared"] += 1
                    counts["matched"] += error <= ABSTOL + RELTOL * max(abs(a), abs(b))
                proof.append([name, key, list(map(str, expected)), list(map(str, observed))])
    return {"combinations": list(STATIC), "cuts": sum(len(v["cuts"]) for v in grid.values()),
            "components": ["P","V2","V3","T","M2","M3"], "compared": counts["compared"],
            "matched": counts["matched"], "absolute_tolerance": str(ABSTOL), "relative_tolerance": str(RELTOL),
            "max_absolute_error": float(worst), "paired_fraction_rows_sha256": _digest(proof)}


def selection_evidence(source):
    flags = {"capture_metadata":"display_selection_restored", "next_capture":"case_selection_restored",
             "analysis_sources":"display_selection_restored", "vs04_diaphragm_probe":"display_selection_restored",
             "vs05_delta_source":"selection_restored", "vs06_b1_geometry_source":"selection_restored",
             "vs06_wall_load_source":"selection_restored", "r08_second_order_source":"combination_selection_restored"}
    restored = {k:source[k].get(field) is True for k, field in flags.items()}
    probe = source["vs04_basis_probe"]
    restored["basis_display"] = (probe["display_cases_before"] == probe["display_cases_after"])
    reads = source["pier_section_forces"]["read"]
    restored["pressure_shells"] = reads["pressure_shells"]["selection_restored"] is True
    for label, f in (("design_frames",source["column_axial"]["force_source"]),
                     ("primitive_frames",source["column_axial"]["demand_support"]["force_source"]),
                     ("frame_control",reads["frame_control"])):
        before = f.get("output_selection_before")
        restored[label] = bool(before) and before == f.get("output_selection_after")
        require(f.get("units_code") == 6 and f.get("api") == "Results.FrameForce" and not f.get("errors")
                and f.get("schema") == "tbdy.next.etabs-frame-force-source.v1", "NATIVE_FRAME_SCHEMA_OR_UNITS_DIFFER")
    return restored


# Independent, frozen review inputs for the nominated original project. A new project needs its own packet.
BOOK_SHA = "52eac87544b1b5cd354a16a4677dfaf1010d84948485e3c98871d715e5580b11"
ROLES_SHA = "8d26c05d8bb28e6828c138ee291db4af897f278bef98d8355ca43a4282f1959e"
GROUPS_SHA = "2d0ebd6bfb0dc725bbd067457db8cc1260d827060ebcb2a4000001c499a88f93"


def _review(source, reconciliation, grids, project, packet):
    from ..etabs_source_gateway_windows import verify
    from .analysis_archive import _archive_bytes

    archive = source["analysis_archive"]
    matched = reconciliation["archived_analysis_order"]
    deck = _archive_bytes(archive["model_export_base64"], 2_000_000)
    log = b64decode(archive["log_base64"], validate=True)
    require(sha256(deck).hexdigest() == matched["model_export_sha256"]
            and sha256(log).hexdigest() == matched["solver_log_sha256"], "ARCHIVED_SOLVER_OR_EXPORT_HASH_DIFFERS")
    version = re.findall(r'^\s*PROGRAM\s+"ETABS"\s+VERSION\s+"([^"]+)"', deck.decode("latin-1"), re.M)
    basis = source["analysis_basis"]
    review = project["review"]
    packet["standard_profile"] = {"standards": ["TBDY 2018", "TS 500:2000"],
        "edition_basis":"Project-specified editions, subject to Supervisor acceptance",
        "model_profile":basis["model_profile"], "project_fields":project["fields"], "review":review,
        "source_data_sha256":basis["source_data_sha256"], "engineering_approval":basis["engineering_approval"]}
    meta = source["capture_metadata"]
    require(version and len(version)==1 and version[0].split(".")[0]=="23", "UNSUPPORTED_ETABS_EXPORT_VERSION")
    _, cases, graph = native_graph(source)
    book, assigned = export_catalog(deck.decode("latin-1"), graph, cases)
    roles = basis["case_roles"]
    groups = basis["design_groups"]
    catalog = reconciliation["assigned_design_families"]["project_role_catalog"]
    require(set(cases) == set(roles) and all(n in book for a in groups.values() for n in a),
            "UNRESOLVED_PROJECT_ROLE")
    wall = wall_load_scope(source)
    wall_names = set(wall["native_static"]) | set(wall["native_seismic"])
    role_match = (_digest(roles)==ROLES_SHA and _digest(groups)==GROUPS_SHA
                  and all(set(catalog["available_groups"][k])==set(v) for k,v in groups.items())
                  and not catalog["incomplete_families"] and not wall["other"] and wall_names==set(assigned["Wall"]))
    packet["load_book"] = {"project_case_roles":roles, "calculation_roles":groups,
        "native_strength_assignments":assigned, "wall_signed_static":sorted(wall["native_static"]),
        "wall_spectral_bounds":sorted(wall["native_seismic"]), "definitions":book,
        "export_and_table_agree":True, "expected_book_sha256":BOOK_SHA, "actual_book_sha256":_digest(book),
        "operator_counts":dict(Counter(n["operator"] for n in book.values())),
        "nonconcurrent_operators":sorted(k for k,v in book.items() if v["operator"]!="Linear Add"),
        "spectral_use":"Scalar intervals only", "role_sets_match":role_match}
    reads = source["pier_section_forces"]["read"]
    shells = reads["pressure_shells"]
    verify(shells)
    sol = reads["transition_shells"]["solution"]
    controls = shells["pier_controls"]
    native_cases = matched["solved_case_guids"]
    model_hash = archive["observed_edb_sha256"]
    generation = (matched["status"]=="ARCHIVED_SOLVER_FIRST_ORDER_MATCHED" and matched["source_analysis_order"]=="FIRST_ORDER"
                  and model_hash==matched["observed_edb_sha256"]==reads["model_sha256"]==sol["input_sha256"]==shells["model_sha256"]
                  and shells["solution_role"]==sol["method"]=="INPUT_IDENTICAL_PRIVATE_REANALYSIS"
                  and shells["solved_sha256"]==sol["solved_sha256"] and bool(sol["solved_sha256"])
                  and sol["frame_control_matched"] is True and set(sol["cases"])==set(native_cases)==set(cases)
                  and len(native_cases)==len(set(native_cases.values()))==15
                  and all(cases[k]["guid"].lower()==g.lower() for k,g in native_cases.items())
                  and controls==sol["pier_controls"] and controls["rows"]*6==controls["components"]==11700
                  and controls["outside_tolerance"]==0)
    packet["generation"] = {"original_edb_sha256":model_hash, "solved_copy_sha256":sol["solved_sha256"],
        "export_sha256":matched["model_export_sha256"], "solver_log_sha256":matched["solver_log_sha256"],
        "solved_case_guids":native_cases, "frame_control_member":sol["frame_control_member"],
        "frame_control_matched":sol["frame_control_matched"], "pier_controls":controls,
        "pressure_capture_sha256":shells["payload_sha256"], "order":matched["source_analysis_order"],
        "analysis_generation_independently_verified":reconciliation["analysis_generation_independently_verified"]}
    restored = selection_evidence(source)
    sessions = [meta[k] for k in ("etabs_session_before_scan","etabs_session","etabs_session_after_scan")]
    units = all(s["model_locked"] is True and s["units_api_agree"] is True and s["units_code"]==6 for s in sessions)
    native = (units and shells["units"]==6 and meta["api_signature"]=="seven_list"
              and reads["schema"]=="tbdy.next.original-pier-read.v1"
              and shells["schema"]=="tbdy.next.wall-pressure-shell-fields.v2")
    packet["native_api"] = {"version":version[0], "units_code":shells["units"], "units_label":sessions[1]["units_label"],
        "modal_signature":meta["api_signature"], "pressure_schema":shells["schema"], "selections_restored":restored}
    replay = exact_replay(source, grids, cases, graph)
    packet["signed_linear_add"] = replay
    accepted_profile = (review["status"]=="CONFIRMED" and not review["issues"] and review["checks"]
                        and all(c["satisfied"] is True for c in review["checks"])
                        and review["sha256"]==source["project_parameter_inputs"]["confirmed_profile_sha256"]
                        and basis["source_data_sha256"]==reads["parent_input_sha256"]==review["source_sha256"]
                        and basis["model_profile"]["structural_system"]=="RC_FRAME_AND_WALL")
    return [bool(accepted_profile), role_match and _digest(book)==BOOK_SHA,
            generation and all(restored.values()), native and all(restored.values()),
            _digest(book)==BOOK_SHA and replay["cuts"]==402 and replay["compared"]==replay["matched"]==7236]


def g1_contract(source, reconciliation, scope, project, input_sha):
    packet = {"schema":"tbdy.next.supervisor-g1.v1", "input_sha256":input_sha,
              "scope":"Original model and the project-specific captured design book",
              "decision":"AWAITING_SUPERVISOR", "engineering_release":"NOT_READY"}
    try:
        ready = _review(source,reconciliation,scope["configured_output_cuts"],project,packet)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, ArithmeticError) as exc:
        packet["unresolved_input"] = str(exc)
        ready = [False]*len(GAPS)
    packet["gaps"] = {gap:{"closure_ready":ok, "supervisor_approval":"PENDING"} for gap,ok in zip(GAPS,ready)}
    packet["contract_sha256"] = _digest(packet)
    return packet
