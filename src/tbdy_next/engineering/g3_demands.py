"""Census the original design inputs at their native cut, step and analysis generation."""
from collections import defaultdict
from math import isfinite
from uuid import UUID

from ..column_engine.source_bank import native_frame_force_rows
from .design_scenario import _digest
from .g2_contract import require
from .mixed_demands import native_graph


def demand_census(source, stages, building):
    g1 = building["g1_contract"]
    gen = g1["generation"]
    book = g1["load_book"]
    _,cases,_ = native_graph(source)
    guids = gen["solved_case_guids"]
    require(set(guids) == set(cases) and len(set(guids.values())) == len(guids)
            and all(UUID(guids[k]) == UUID(cases[k]["guid"]) for k in guids),"NATIVE_GUID_ROSTER_CHANGED")
    definitions = book["definitions"]
    def recipe(name, ancestors=()):
        if name in ancestors:
            raise ValueError("CYCLIC_NATIVE_COMBINATION")
        if name in guids:
            return ["CASE",guids[name]]
        node = definitions[name]
        return [node["operator"], [[factor, ["CASE",guids[ref]] if typ=="CASE" else recipe(ref,ancestors+(name,))]
                for typ,ref,factor in node["terms"]]]
    recipes = {name:_digest(recipe(name)) for name in definitions}
    recipes.update({name:_digest(["CASE",guid]) for name,guid in guids.items()})
    source_frames = source["column_axial"]
    trace = source_frames["r10_source"]["table_reads"]
    mesh = defaultdict(set)
    for row in trace["Objects and Elements - Frames"]["rows"]:
        mesh[row["ObjName"]].add(row["ElmName"])
    roles = source["analysis_basis"]["design_groups"]
    expected = set(roles["ductile"]) | set(roles["gravity"])
    frame_results = {}
    for kind,record,key in (("columns",source_frames["force_source"],"COLUMN_CONNECTIVITY"),
                            ("beams",source_frames["r10_source"]["beam_force_source"],"BEAM_CONNECTIVITY")):
        roster = {r["UniqueName"]:str(UUID(r["GUID"])) for r in source["geometry_capture"]["tables"][key]["rows"]}
        require(roster.keys() == record["rowsets"].keys() and len(set(roster.values())) == len(roster),
                "DESIGN_FRAME_SOURCE_ROSTER")
        require(record["units_code"] == 6 and record["api"] == "Results.FrameForce" and not record["errors"],
                "DESIGN_FRAME_API_OR_UNITS")
        manifest = []
        pairs = 0
        for uid,guid in sorted(roster.items()):
            rows = sorted(native_frame_force_rows(record["rowsets"][uid],uid))
            by_case = defaultdict(set)
            cuts = defaultdict(set)
            for obj,sta,elm,local,name,step,number,*forces in rows:
                require(elm in mesh[uid] and name in recipes and len(forces) == 6, "FRAME_ELEMENT_OR_CASE_IDENTITY")
                by_case[name].add((sta,elm,local))
                cuts[name,sta,elm,local].add((step,number))
            require(by_case.keys() == expected and all(v == next(iter(by_case.values())) for v in by_case.values()),
                    "FRAME_CASE_OR_SIDE_MISSING")
            require(all(v in ({("Single Value",0.)},{("",0.)},{("Max",0.),("Min",0.)}) for v in cuts.values()),
                    "FRAME_MISSING_OR_AMBIGUOUS_NATIVE_STEP")
            if kind == "columns":
                cfg = stages["report_evidence"]["column_pmm_expected_instances"]["configured_output_cuts"][uid]
                observed = next(iter(by_case.values()))
                require(len(cfg["cuts"]) == len(observed) and all(sum(elm == q["analysis_element_id"]
                       and abs(sta-q["object_station_m"]) <= 1.e-7 and abs(local-q["element_station_m"]) <= 1.e-7
                       for sta,elm,local in observed) == 1 for q in cfg["cuts"]), "COLUMN_CONFIGURED_CUT_MISMATCH")
            manifest.append([uid,guid,_digest([[list(row[:7]),recipes[row[4]],list(row[7:])] for row in rows]),len(rows)])
            pairs += len(by_case)
        frame_results[kind] = {"members":len(roster),"member_combination_pairs":pairs,
            "native_vectors":sum(r[-1] for r in manifest),"manifest_sha256":_digest(manifest)}
    require(frame_results["columns"]["member_combination_pairs"] == 957 and frame_results["beams"]["members"] == 180,
            "ORIGINAL_FRAME_DENOMINATORS")
    design = trace["Concrete Beam Design Summary - TS 500-2000(R2018)"]
    owners = {row["member_id"]:row for row in stages["beam_r10"]["beams"]}
    beam_design = []
    missing = set()
    beam_force_cases = {uid:set(g["LoadCase"]) for uid,g in source_frames["r10_source"]["beam_force_source"]["rowsets"].items()}
    for row in design["rows"]:
        uid = row["UniqueName"]
        require(uid in owners and row["DesignSect"] == owners[uid]["section_name"],"BEAM_DESIGN_SECTION_MISMATCH")
        names = [row[k] for k in ("AsTopCombo","AsBotCombo","TLngCombo","VCombo","TTrnCombo") if row.get(k)]
        require(all(name in recipes for name in names), "BEAM_DESIGN_COMBINATION_UNBOUND")
        missing.update(set(names) - beam_force_cases[uid])
        beam_design.append([uid,row["Station"],[recipes[n] for n in names],_digest(row)])
    read = source["pier_section_forces"]["read"]
    table = read["tables"]["table_reads"]["Pier Forces"]
    assigned = set(book["native_strength_assignments"]["Wall"])
    indexed = defaultdict(dict)
    for row in table["rows"]:
        if row["OutputCase"] not in assigned:
            continue
        identity = (row["Pier"],row["Story"],row["Location"],row["OutputCase"])
        step = row.get("StepType","")
        require(step not in indexed[identity],"DUPLICATE_PIER_STEP")
        values = [float(row[q]) for q in ("P","V2","V3","T","M2","M3")]
        require(all(map(isfinite,values)),"NONFINITE_PIER_FORCE")
        indexed[identity][step] = values
    walls = building["wall_sections"]
    physical = set()
    faces = []
    for row in walls["batch"]["rows"]:
        physical.update(row["members"])
        if not row["pier"]:
            continue
        expected_faces = {(f,n) for f in ("Top","Bottom") for n in assigned}
        consumed = {(c["face"],c["combination"]) for c in row["cuts"] if c["role"].startswith("ASSIGNED_")}
        require(consumed == expected_faces, "INCOMPLETE_CONSUMED_PIER_FACES")
        for face,name in sorted(expected_faces):
            k = (row["pier"],row["story"],face,name)
            require(k in indexed and set(indexed[k]) in ({"Max","Min"},{""},{"None"},{"Single Value"}),"PIER_STEP_IDENTITY")
            faces.append([k,sorted(row["members"]),recipes[name],indexed[k]])
    shell = read["pressure_shells"]
    areas = {r for pier in walls["basement_piers"] for r in pier["members"]}
    supplemental = set(shell["members"])-areas
    panels = []
    for uid,field in sorted(shell["members"].items()):
        corners = list(map(tuple,field["corners"]))
        require(corners and len(corners) == len(set(corners)) and assigned <= field["cases"].keys(),"SHELL_CUT_ROSTER")
        for name,steps in sorted(field["cases"].items()):
            require(set(steps) in ({"Max","Min"},{"Single Value"},{""}) and all(len(rows)==len(corners)
                    and all(len(v)==8 and all(map(isfinite,v)) for v in rows) for rows in steps.values()),
                    "SHELL_CORNER_STEP_OR_COMPONENT_MISSING")
            panels.append([uid,name,recipes[name],_digest(corners),_digest(steps)])
    require(len(physical)==30 and len(faces)==len(indexed)==390 and len(areas)==17 and areas <= shell["members"].keys()
            and sum(p[0] in areas and p[1] in assigned for p in panels)==221,"WALL_OR_SHELL_DENOMINATORS")
    fields = set(design["fields"])
    return {"frame_force_sources":frame_results,"native_case_guids":guids,"recipe_manifest_sha256":_digest(recipes),
        "original_edb_sha256":gen["original_edb_sha256"],"solver_log_sha256":gen["solver_log_sha256"],
        "controlled_copy_sha256":gen["solved_copy_sha256"],"shell_solution_role":shell["solution_role"],
        "physical_walls":len(physical),"assigned_pier_faces":len(faces),"face_manifest_sha256":_digest(faces),
        "basement_panel_pairs":221,"additional_shell_members":sorted(supplemental),"shell_manifest_sha256":_digest(panels),
        "beam_design_rows":len(beam_design),"beam_design_manifest_sha256":_digest(beam_design),
        "design_combinations_without_same_case_beam_force_arrays":sorted(missing),
        "design_summary_has_native_element_side_and_step": {"Elm","ElmSta","StepType","StepNum"} <= fields,
        "native_pier_control_components":gen["pier_controls"]["components"],
        "original_generation_independently_verified":gen["analysis_generation_independently_verified"]}
