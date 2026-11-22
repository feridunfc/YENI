"""Compare assigned C104 demands at the same physical faces in two ETABS meshes."""
from collections import defaultdict
from math import fsum, isclose

from .coupled_wall_transition import MESH_ABS, MESH_REL, SIGNED_CASES
from .design_scenario import _digest
from .gravity_wall_cut import _check, _real, _vector, joint_action_at_origin
from .mixed_demands import linear_coefficients, native_graph
from ..normative_basis import eq_4_31_base_scale

SCHEMA = "tbdy.next.transition-design-trace.v1"
COMPONENTS = ("P", "V2", "V3", "T", "M2", "M3")
GLOBAL = ("FX", "FY", "FZ", "MX", "MY", "MZ")
FACES = ("lower", "below_transition", "above_transition", "upper")
WALL = "437"


def checked_trace(raw):
    trace = raw.get("design_trace")
    _check(isinstance(trace, dict) and trace.get("schema") == SCHEMA
           and trace.get("sha256") == _digest({k:v for k,v in trace.items() if k != "sha256"}),
           "DESIGN_TRACE_CHANGED")
    levels = trace.get("levels")
    _check(isinstance(levels, list) and len(levels) == 2 and
           all(a["generation_sha256"] == b["generation_sha256"] for a,b in zip(raw["levels"], levels)),
           "DESIGN_TRACE_ARCHIVE_GENERATION_MISMATCH")
    return trace


def _comparison(a, b):
    limit = max(MESH_ABS, MESH_REL * max(abs(a), abs(b)))
    return {"a":a, "d":b, "difference":b-a, "limit":limit, "within_budget":abs(b-a) <= limit}


def _assigned(source, deck):
    tables, cases, graph = native_graph(source)
    req = source["column_axial"]["request"]
    groups = req["design_assignment"]["groups"]
    names = set(req["combinations"])
    _check(req["combination_source"] == "ASSIGNED_DESIGN" and
           names == set(groups["ductile"]) | set(groups["gravity"]) and
           not set(groups["ductile"]).intersection(groups["gravity"]), "DESIGN_ASSIGNMENT_ROSTER_MISMATCH")
    _check(set(deck["combinations"]) == names, "DESIGN_DECK_ASSIGNMENTS_MISMATCH")
    combinations = {}
    for name in sorted(names):
        leaves = {k:float(v) for k,v in linear_coefficients(name, graph, cases).items()}
        _check(leaves == deck["combinations"][name], "DESIGN_COMBINATION_DECK_DIFFERS:" + name)
        spectral = sorted(k for k in leaves if cases[k]["type"] == "Response Spectrum")
        _check(bool(spectral) == (name in groups["ductile"]), "DESIGN_STEP_SCOPE_CHANGED:" + name)
        combinations[name] = {"terms":leaves, "spectral_cases":spectral,
                              "steps":["Max","Min"] if spectral else ["Single Value"]}
    spectrum = {row["Name"]:row for row in tables["Load Case Definitions - Response Spectrum"]["rows"]}
    for axis in "XY":
        definition = deck["directions"][axis]
        row = spectrum[definition["spectrum_case"]]
        _check(row["Function"] == definition["function"] and row["LoadName"] == definition["load_name"]
               and row["ModalCase"] == definition["modal_case"] and row["CoordSys"] == "Global"
               and float(row["Angle"]) == 0 and float(row["TransAccSF"]) == definition["scale_m_s2"]
               and definition["scale_m_s2"] > 0, "DESIGN_SPECTRUM_SCALE_SOURCE_MISMATCH")
    return combinations


def _at_faces(raw, level, data, combinations):
    cuts = dict(zip(FACES, ((raw["bracket_m"][0],"I"), (raw["origin_m"][2],"J"),
                            (raw["origin_m"][2],"I"), (raw["bracket_m"][1],"J")), strict=True))
    coords = level["coordinates"]
    ends = {(e,end):coords[n][2] for e,i,j in level["frame_segments"] for end,n in (("I",i),("J",j))}
    result = {}
    for uid, elm, end, case, step, num, *values in data["assigned_frame_rows"]:
        _check(uid == raw["member_id"] and (elm,end) in ends and case in combinations and _real(num)
               and num == 0 and step in combinations[case]["steps"] and _vector(values,6), "DESIGN_FACE_ROW_INVALID")
        for face,(z,side) in cuts.items():
            if side == end and abs(z-ends[elm,end]) < 1e-7:
                key = (face,case,step)
                _check(key not in result, "DESIGN_FACE_ROW_DUPLICATE")
                result[key] = values
    expected = {(f,c,s) for f in cuts for c,v in combinations.items() for s in v["steps"]}
    _check(set(result) == expected, "DESIGN_FACE_POPULATION_INCOMPLETE")
    return result


def _base_rows(raw, required):
    count, cases, steps, numbers, *arrays, x, y, z = raw
    _check(type(count) is int and count == len(cases) and len(arrays) == 6 and _vector([x,y,z],3)
           and all(len(v) == count for v in (cases,steps,numbers,*arrays)), "DESIGN_BASE_REACTION_SHAPE")
    rows = {}
    for case, step, number, *values in zip(cases,steps,numbers,*arrays,strict=True):
        if case not in required:
            continue
        _check(number == 0 and step in (("Max",) if case in ("RSX","RSY") else ("Single Value",))
               and case not in rows and _vector(values,6), "DESIGN_BASE_REACTION_STEP")
        rows[case] = dict(zip(GLOBAL, values, strict=True))
    _check(set(rows) == set(required), "DESIGN_BASE_REACTION_POPULATION")
    return [x,y,z],rows


def wall_edge_distribution(raw, level):
    """Positive upward cut at the W22 horizontal soffit, with the signed Fz first moment."""
    origin = raw["origin_m"]
    coords = level["coordinates"]
    expected = {(element,node) for uid,element,nodes in level["shells"] if uid == WALL
                and min(coords[n][2] for n in nodes) >= origin[2]-1e-7 for node in nodes
                if abs(coords[node][2]-origin[2]) < 1e-7}
    seen, groups = set(), defaultdict(list)
    for uid, element, node, case, step, num, *native in level["shell_rows"]:
        if uid != WALL or (element,node) not in expected:
            continue
        key = (element,node,case)
        _check(key not in seen and case in SIGNED_CASES and [step,num] == ["Single Value",0],
               "DESIGN_SOFFIT_STEP_OR_DUPLICATE")
        seen.add(key)
        point = coords[node]
        v = joint_action_at_origin([-s for s in native], level["point_matrices"][node], point, point)
        groups[case,point[0]].append((v[2], (point[0]-origin[0])*v[2], v[4], (point[2]-origin[2])*v[0]))
    _check(expected and seen == {(e,n,c) for e,n in expected for c in SIGNED_CASES}, "DESIGN_SOFFIT_POPULATION")
    out = {}
    for case in SIGNED_CASES:
        total = [0.]*4
        stations = []
        for _, x in sorted(k for k in groups if k[0] == case):
            increment = [fsum(s) for s in zip(*groups[case,x], strict=True)]
            total = [fsum((a,b)) for a,b in zip(total,increment,strict=True)]
            stations.append({"x_m":x, "fz_kn":increment[0], "cumulative_fz_kn":total[0],
                             "cumulative_x_fz_knm":total[1], "point_my_knm":increment[2]})
        out[case] = {"stations":stations,"fz_kn":total[0],"x_fz_knm":total[1],
                     "point_my_knm":total[2],"z_fx_knm":total[3],"my_at_origin_knm":total[2]+total[3]-total[1]}
    return out


def scale_sensitivity(equivalent, observed, scale):
    """Full-model boundary hypotheses, using an already-scaled RSA observation as the comparison baseline."""
    _check(all(_real(v) and v>0 for v in (equivalent,observed,scale)), "DESIGN_SCALE_NONPOSITIVE")
    rows = []
    for irregular in (False, True):
        # The two hypothetical configurations explicitly qualify their *own* boundary and gamma.
        # No such qualification is granted to the project by this calculation.
        result = eq_4_31_base_scale(equivalent_base_shear_kn=str(equivalent), modal_base_shear_kn=str(observed),
                                    irregularity_A1_B2_B3_any=irregular, irregularity_inventory_complete=True,
                                    basement_boundary_qualified=True)
        additional = float(result["required_scale_factor"])
        rows.append({"gamma":float(result["gamma_E"]), "target_kn":float(result["minimum_modal_base_shear_kn"]),
                     "additional_factor_on_observed":additional, "case_scale_for_target_m_s2":scale*additional})
    return rows


def _story_shear(model, direction, story, case, spectral):
    table = model["tables"].get("Story Forces") or {}
    rows = [r for r in table.get("rows",()) if r.get("Story")==story and r.get("OutputCase")==case
            and r.get("Location")=="Bottom" and (r.get("StepType")=="Max" if spectral else
                                                 r.get("StepType") in (None,"","None","Single Value"))]
    if table.get("status")!="CAPTURED" or len(rows)!=1:
        return None
    return abs(float(rows[0]["V"+direction]))


def _drift_evidence(table, axis, case):
    rows = [{"story":r["Story"], "ratio":float(r["Ratio"])} for r in table.get("rows",())
            if r.get("Direction")==axis and r.get("OutputCase")==case and r.get("StepType")=="Max"
            and r.get("Ratio") not in (None,"","None")]
    return {"observed":rows,"maximum":max(rows,key=lambda r:r["ratio"]) if rows else None,
            "scope":"Native same-direction story drift ratios. Project A1/B2/B3 decision remains separate."}


def _conditional_scale(vte, vrs, scale):
    # A unit acceleration and standard-gravity reference are identifiable by linearity.
    # The ETABS total acceleration field does not document a project split into g and beta.
    reference_g = 9.80665
    at_g = vrs*reference_g/scale
    return {"reference_kn":vte, "as_applied_spectrum_kn":vrs, "response_per_m_s2":vrs/scale,
            "conditional_on_this_cut":scale_sensitivity(vte,vrs,scale),
            "standard_g_hypothesis":{"reference_m_s2":reference_g,"pre_beta_kn_if_normalized_by_standard_g":at_g,
                                      "effective_applied_ratio_if_standard_g":scale/reference_g,
                                      "required_if_standard_g":[{"gamma":r["gamma"],"beta":r["additional_factor_on_observed"]}
                                                                for r in scale_sensitivity(vte,at_g,reference_g)]}}


def _load_equivalence(native):
    specs = (("Mass Summary by Story",("Story",),("UX","UY","UZ")),
             ("Centers Of Mass And Rigidity",("Story","Diaphragm"),("MassX","MassY","XCM","YCM","XCR","YCR")),
             ("Story Forces",("Story","Location","OutputCase","StepType"),("P","VX","VY","T","MX","MY")))
    out={}
    for name,keys,fields in specs:
        tables=[m["tables"].get(name,{}) for m in native]
        if not all(t.get("status")=="CAPTURED" and t.get("rows") for t in tables):
            out[name]={"status":"SOURCE_TABLE_UNAVAILABLE","rows":[]}
            continue
        def indexed(table):
            result={}
            for item in table["rows"]:
                if name=="Story Forces" and item.get("OutputCase") not in (*SIGNED_CASES,"RSX","RSY"):
                    continue
                key=tuple(str(item.get(k,"")) for k in keys)
                _check(key not in result,"DESIGN_GLOBAL_STORY_ROW_DUPLICATE")
                result[key]=item
            return result
        a,d=map(indexed,tables)
        shared=sorted(a.keys() & d.keys())
        rows=[]
        for key in shared:
            for field in fields:
                va,vb=a[key].get(field),d[key].get(field)
                if va in ("","None",None) or vb in ("","None",None):
                    continue
                left,right=float(va),float(vb)
                _check(_real(left) and _real(right),"DESIGN_GLOBAL_STORY_NONFINITE")
                row={**dict(zip(keys,key)),"field":field,"a":left,"d":right,"difference":right-left}
                if name=="Story Forces":
                    row.update(_comparison(left,right))
                rows.append(row)
        out[name]={"status":"MATCHED_IDENTITIES" if a and a.keys()==d.keys() else "POPULATION_DIFFERS",
                   "expected_keys":len(a.keys()|d.keys()),"matched_keys":len(shared),"rows":rows}
    return out


def assigned_static_increments(raw, combinations, faces, transition_models):
    """Read the signed increment between two assigned envelopes sharing all spectral terms."""
    from fractions import Fraction
    from itertools import permutations
    groups = []
    signed_plan = {c:{"steps":["Single Value"]} for c in SIGNED_CASES}
    controls = [_at_faces(raw,level,{"assigned_frame_rows":level["frame_rows"]},signed_plan) for level in raw["levels"]]
    for lo,hi in permutations(sorted(combinations),2):
        a,b = (combinations[k] for k in (lo,hi))
        if a["steps"] != b["steps"] or a["spectral_cases"] != b["spectral_cases"]:
            continue
        difference = {k:Fraction(str(b["terms"].get(k,0))) - Fraction(str(a["terms"].get(k,0)))
                      for k in a["terms"].keys() | b["terms"].keys()}
        difference = {k:float(v) for k,v in difference.items() if v}
        if difference not in ({"LC_H":1.,"LC_HE":1.},{"LC_T":2.4}):
            continue
        checks, actions = [], []
        for face in FACES:
            for step in a["steps"]:
                for j,component in enumerate(COMPONENTS):
                    values = []
                    for observed,signed in zip(faces,controls,strict=True):
                        actual = observed[face,hi,step][j]-observed[face,lo,step][j]
                        predicted = fsum(coef*signed[face,case,"Single Value"][j] for case,coef in difference.items())
                        values.append({"assigned_difference":actual,"signed_prediction":predicted,"error":actual-predicted})
                    checks.append({"face":face,"step":step,"component":component,"a":values[0],"d":values[1],
                                   "matched":all(abs(v["error"])<=max(1e-6,1e-8*abs(v["signed_prediction"])) for v in values)})
            objects = transition_models[0]["cases"][next(iter(difference))]["actions_by_object"][face]
            for obj in sorted(objects):
                for component in ("N","V2","V3","T","M2","M3"):
                    values = [fsum(factor*m["cases"][case]["actions_by_object"][face][obj][component]
                                   for case,factor in difference.items()) for m in transition_models]
                    actions.append({"face":face,"object":obj,"component":component,**_comparison(*values)})
        groups.append({"from_combination":lo,"to_combination":hi,"isolated_cases":difference,
                       "checks":checks,"matched":sum(row["matched"] for row in checks),
                       "expected":len(checks),"coupled_cut_actions":actions})
    return groups


def mesh_effects(a,b,c,d):
    """B changes V, C changes H, D changes both. Effects are signed, in the ordinate's units."""
    return {"a":a,"b":b,"c":c,"d":d,"b_minus_a_vertical":b-a,"d_minus_c_vertical":d-c,
            "c_minus_a_horizontal":c-a,"d_minus_b_horizontal":d-b,
            "interaction":fsum((d,-b,-c,a)), "a_d_difference":d-a}


def _crossed_study(raw, cross, source, combinations, faces, section_models, models):
    from .coupled_wall_transition import _mesh_actions, _parent_geometry, check_transition_level
    _check(cross["schema"]=="tbdy.next.c104-crossed-mesh.v1" and set(cross["models"])=={"B","C"},
           "DESIGN_CROSSED_POPULATION")
    native=[m["native_interface"] for m in models]
    _check(all(native),"DESIGN_CROSSED_AD_STUDY_REQUIRED")
    topologies=[n["w23_mesh"] for n in native]
    policies=[n["auto_edge"] for n in native]
    normals=_parent_geometry(raw,source)
    samples={}
    for name,wanted in (("B",(2,1)),("C",(1,2))):
        data=cross["models"][name]
        level=data["level"]
        _check((data["vertical"],data["horizontal"])==wanted and level["pitch_m"]==.05/wanted[0],
               "DESIGN_CROSSED_LEVEL_IDENTITY")
        check_transition_level(level,raw["cases"])
        topologies.append(data["w23_mesh"])
        policies.append(data["policies"])
        section=_mesh_actions(raw,level,normals)
        frame=_at_faces(raw,level,data,combinations)
        _,base=_base_rows(data["base_reactions"],SIGNED_CASES)
        samples[name]={"section":section,"frame":frame,"base":base,"generation":level["generation_sha256"]}
    _check(all(t==topologies[0] for t in topologies) and all(p==policies[0] for p in policies),
           "DESIGN_CROSSED_W23_IS_AN_ADDITIONAL_VARIABLE")
    frames=[]
    for key,a in sorted(faces[0].items()):
        for j,component in enumerate(COMPONENTS):
            frames.append({"face":key[0],"case":key[1],"step":key[2],"component":component,
                           **mesh_effects(a[j],samples["B"]["frame"][key][j],samples["C"]["frame"][key][j],faces[1][key][j])})
    sections=[]
    sections_in_order=(section_models[0],samples["B"]["section"],samples["C"]["section"],section_models[1])
    for case in SIGNED_CASES:
        for face in FACES:
            for component in ("N","V2","V3","T","M2","M3"):
                values=[m["cases"][case]["cuts"][face][component] for m in sections_in_order]
                sections.append({"face":face,"case":case,"component":component,**mesh_effects(*values)})
    return {"schema":cross["schema"],"study_sha256":cross["pair_sha256"],
            "levels":{n:{"generation_sha256":x["generation"],"signed_base_reactions":x["base"],
                         "balanced_thin_bodies":sum(row["balance_status"]=="BALANCED" for row in x["section"]["cases"].values())}
                      for n,x in samples.items()},"w23_mesh":topologies[0],"edge_policies":policies[0],
            "assigned_frame_components":frames,"signed_coupled_components":sections,
            "scope":"Two-level mesh sensitivity with fixed physical inputs and W23 connectivity policy."}


def project_design_trace(raw, source, transition_models):
    from .wall_interface_transfer import physical_interface, retained_interface_side
    trace = checked_trace(raw)
    deck = trace["deck"]
    geometry = physical_interface(source)
    combos = _assigned(source, deck)
    roles = {c:[name for name,definition in combos.items() if c in definition["terms"]]
             for c in (*SIGNED_CASES,"RSX","RSY")}
    models, faces, bases = [], [], []
    for level,data in zip(raw["levels"],trace["levels"], strict=True):
        faces.append(_at_faces(raw,level,data,combos))
        origin,base = _base_rows(data["base_reactions"],SIGNED_CASES)
        more = data.get("interface_read")
        current = None
        if more:
            from .wall_interface_transfer import project_interface
            current = project_interface(raw, more, geometry, deck)
            rows = more.get("assigned_frame_rows")
            current["assigned_frame_replay"] = {"evaluated":0,"within_replay_tolerance":0}
            if rows:
                replay=_at_faces(raw,level,more,combos)
                checks=[(a,b) for key in faces[-1] for a,b in zip(faces[-1][key],replay[key],strict=True)]
                current["assigned_frame_replay"] = {
                    "evaluated":len(checks),"within_replay_tolerance":sum(isclose(a,b,abs_tol=1e-6,rel_tol=1e-8) for a,b in checks),
                    "maximum_absolute_difference":max(abs(a-b) for a,b in checks)}
        bases.append((origin,base))
        models.append({"pitch_m":level["pitch_m"], "generation_sha256":level["generation_sha256"],
                       "retained_w22":retained_interface_side(raw,data["retained_w22"],geometry,deck),
                       "soffit":wall_edge_distribution(raw,level), "native_interface":current})
    _check(bases[0][0] == bases[1][0], "DESIGN_BASE_REFERENCE_ORIGIN_CHANGED")
    design = [{"face":face,"case":case,"step":step,"component":component, **_comparison(a,b)}
              for (face,case,step), first in sorted(faces[0].items())
              for component,a,b in zip(COMPONENTS,first,faces[1][face,case,step],strict=True)]
    globals_ = [{"case":c,"component":k,**_comparison(bases[0][1][c][k],bases[1][1][c][k])}
                for c in SIGNED_CASES for k in GLOBAL]
    native = [m["native_interface"] for m in models]
    scale = []
    for axis,d in deck["directions"].items():
        k = "F"+axis
        record = {"axis":axis, **d,"model_reference_shear_kn":[abs(b[1][d["equivalent_case"]][k]) for b in bases],
                  "required_project_beta":None, "applied_project_beta":None,
                  "qualification":"PRE_BETA_NORMALIZATION_AND_ADOPTED_BASEMENT_SCOPE_REQUIRED"}
        for index,name in enumerate(("A","D")):
            if native[index] is None:
                continue
            obs = native[index]["base_reactions"]
            vte = abs(obs[d["equivalent_case"]][k])
            vrs = abs(obs[d["spectrum_case"]][k])
            record[name] = _conditional_scale(vte,vrs,d["scale_m_s2"])
            record[name]["irregularity_source"]=_drift_evidence(native[index]["tables"].get("Story Max Over Avg Drifts",{}),axis,d["spectrum_case"])
            upper_eq=_story_shear(native[index],axis,"+4.50",d["equivalent_case"],False)
            upper_rs=_story_shear(native[index],axis,"+4.50",d["spectrum_case"],True)
            record[name]["same_solution_story_cut_at_0m"] = (
                _conditional_scale(upper_eq,upper_rs,d["scale_m_s2"]) if upper_eq and upper_rs else None)
        parent_drifts = source["r08_second_order_source"]["spectrum_source"]["table_reads"].get("Story Max Over Avg Drifts",{})
        record["original_drift_screen"] = _drift_evidence(parent_drifts,axis,d["spectrum_case"])
        record["case_scale_owner"] = "ETABS translational acceleration scale applied to the reduced function"
        scale.append(record)
    parent_base = source["analysis_sources"]["tables"]["Base Reactions"]["rows"]
    parent_spectrum = [{"case":r["OutputCase"],"component":k, "kn":float(r[k])}
                       for axis in "XY" for k in ("F"+axis,) for r in parent_base
                       if r["OutputCase"] == deck["directions"][axis]["spectrum_case"] and r["StepType"] == "Max"]
    passed = sum(row["within_budget"] for row in design)
    increments = assigned_static_increments(raw,combos,faces,transition_models)
    crossed=None
    if "crossed_meshes" in trace:
        crossed=_crossed_study(raw,trace["crossed_meshes"],source,combos,faces,transition_models,models)
    return {"schema":SCHEMA,"crossed_meshes":crossed, "interface_geometry":geometry, "mass_definition":deck["mass_source"],
            "mass_patterns":deck["mass_patterns"], "member_id":raw["member_id"], "scope":"ASSIGNED_FIRST_ORDER_FRAME_COMPONENTS",
            "design_groups":source["column_axial"]["request"]["design_assignment"], "combinations":combos,"case_roles":roles,
            "direct_equivalent_case_conflict":bool(roles["LC_EQX"] or roles["LC_EQY"]),
            "face_elevations_m":dict(zip(FACES,[raw["bracket_m"][0],raw["origin_m"][2],raw["origin_m"][2],raw["bracket_m"][1]])),
            "scale":scale,"parent_spectrum_observations":parent_spectrum,"native_scale_reapplied":False,
            "global_load_equivalence":_load_equivalence(native) if all(native) else {},
            "global_reference_point_m":bases[0][0],"global_comparison":globals_,"models":models,
            "signed_design_increments":increments, "assigned_comparison":design,"within_budget":passed,"expected":len(design),
            "decision":"INVESTIGATE_INTERFACE_FOR_USED_DEMAND" if passed < len(design) else "ASSIGNED_FRAME_COMPONENTS_WITHIN_BUDGET",
            "construction_continuity":"UNVERIFIED","coupled_second_order":"METHOD_OPEN"}
