"""Physical identities and section inputs used for the independent G3 comparison."""
from math import hypot, isfinite

from .beam_r10_live import _beam_reinforcing_by_section, _design_factors, _materials_fck, _steel_grade_mpa
from .design_scenario import _digest
from .frame_geometry import build_frame_catalog
from .g2_contract import require


def section_inputs(source, stages, building):
    conditional = {r["member_id"] for r in building["columns"] if r["status"] == "conditional"}
    require(len(conditional) == 69, "EXPECTED_69_CONDITIONAL_COLUMNS")
    native = {r["member_id"]:r["section_evidence"] for r in stages["column_pmm"]["members"]}
    axial = {r["element_id"]:r for r in stages["column_axial"]["columns"]}
    columns = {}
    for uid in sorted(conditional):
        local = stages["r08_local_slenderness"]["per_member"][uid]
        choice = stages["r10_live"]["per_member"][uid]["engineer_column_selection"]["selected"]
        cage = {k:choice[k] for k in ("diameter_mm", "num_bars_2_dir", "num_bars_3_dir", "bar_count", "area_mm2")}
        cage["selected_transverse"] = {"tie_diameter_mm":choice["selected_transverse"]["tie_diameter_mm"]}
        section = {k:native[uid][k] for k in ("t2_mm","t3_mm","cover_to_tie_mm","fcd_mpa","fck_mpa","fyd_mpa","es_mpa")}
        cuts = {}
        for kind, row in (("static",local["magnified_selected_pmm"]["governing_station"]),
                          ("spectral_box",local["spectral_envelope_pmm_scenario"]["governing_corner"])):
            cut = {k:row[k] for k in ("combination","analysis_element_id","element_station_m","object_station_m",
                   "magnified_m2_design_knm","magnified_m3_design_knm","nd_kn","utilization")}
            require(row["utilization"] > 0, "INVALID_GOVERNING_PMM_UTILIZATION")
            cut["radial_capacity_knm"] = row.get("radial_capacity_knm",hypot(cut["magnified_m2_design_knm"],
                                                        cut["magnified_m3_design_knm"])/cut["utilization"])
            if kind == "static":
                cut.update(step_type=row["step_type"],step_number=row["step_number"])
            else:
                cut["basis"] = row["basis"]
            cuts[kind] = cut
        columns[uid] = {"section":section, "cage":cage, "cuts":cuts,
                        "ts500_limit_kn":axial[uid]["ts500_limit_kn"],
                        "tbdy_limit_kn":axial[uid]["tbdy_seismic_reference_limit_kn"]}
    feature = source["column_axial"]
    gc,gs = _design_factors(feature["design_preferences"])
    catalog,_,_ = build_frame_catalog(source)
    reinforcement = _beam_reinforcing_by_section(feature["r10_source"])
    concrete = _materials_fck(stages["extra"])
    beams = {}
    for beam in stages["beam_r10"]["beams"]:
        uid = beam["member_id"]
        require(uid not in beams and set(beam["ends"]) == {"I","J"}, "BEAM_END_POPULATION")
        section_name = beam["section_name"]
        fc = concrete[catalog[uid]["material_name"]]
        fy,es = _steel_grade_mpa(feature["pmm_section_source"],reinforcement[section_name]["rebar_material_long"])
        data = {"width_mm":beam["width_mm"],"height_mm":beam["height_mm"],"section":section_name,
                "fck_mpa":fc,"fcd_mpa":fc/gc,"fyd_mpa":fy/gs,"es_mpa":es,"ends":{}}
        for side,end in beam["ends"].items():
            selection = end["engineer_selection"]
            cap = selection["capacity"]
            require(cap["status"] == "BEAM_CAPACITY_REFERENCE" and cap["axial_force_scenario_n"] == 0,
                    "SIGNED_ZERO_AXIAL_BEAM_CAPACITY_REQUIRED")
            data["ends"][side] = {"joint":beam["point_"+side.lower()],"station_m":end["target_station_m"],
                "bars":selection["bars"],"positive_m3_knm":cap["positive_m3_knm"],"negative_m3_knm":cap["negative_m3_knm"]}
        beams[uid] = data
    expected_beams = {r["UniqueName"] for r in source["geometry_capture"]["tables"]["BEAM_CONNECTIVITY"]["rows"]}
    require(len(beams) == 180 and set(beams) == expected_beams, "EXPECTED_180_NATIVE_BEAMS")
    return {"columns":columns, "beams":beams}


def compare_reference(basis, reference):
    """Bind each independent result to the actual production inputs and examine its residuals."""
    require(reference["schema"] == "tbdy.next.g3-section-reference.v1"
            and reference["input_basis_sha256"] == _digest(basis), "INDEPENDENT_SECTION_INPUTS_CHANGED")
    for kind in ("columns","beams"):
        require(basis[kind].keys() == reference[kind].keys(), "INDEPENDENT_SECTION_ROSTER_CHANGED")
    maxima = {"column_capacity_knm":0., "beam_capacity_knm":0., "axial_limit_kn":0.}
    def residual(key, a, b, tolerance):
        difference = abs(a-b)
        require(isfinite(difference) and difference <= tolerance, "INDEPENDENT_" + key.upper() + "_RESIDUAL")
        maxima[key] = max(difference,maxima[key])
    for uid,inputs in basis["columns"].items():
        check = reference["columns"][uid]
        require(set(inputs["cuts"]) == {"static","spectral_box"}, "INDEPENDENT_STATIC_AND_SPECTRAL_CUTS_REQUIRED")
        for kind,cut in inputs["cuts"].items():
            row = check[kind]
            residual("column_capacity_knm",cut["radial_capacity_knm"],row["capacity_knm"],.01)
            require(0 <= row["axial_residual_n"] <= .001 and 0 <= row["perpendicular_residual_nmm"] <= .001,
                    "INDEPENDENT_COLUMN_EQUILIBRIUM")
        for limit in ("ts500_limit_kn","tbdy_limit_kn"):
            residual("axial_limit_kn",inputs[limit],check[limit],1.e-7)
    for uid,inputs in basis["beams"].items():
        for side,end in inputs["ends"].items():
            for sign in ("positive","negative"):
                key = sign+"_m3_knm"
                row = reference["beams"][uid][side][sign]
                residual("beam_capacity_knm",end[key],row["capacity_knm"],.01)
                require(0 <= row["axial_residual_n"] <= .001 and 0 <= row["maximum_tensile_strain"] <= .1,
                        "INDEPENDENT_BEAM_EQUILIBRIUM_OR_STRAIN")
    return {"input_basis_sha256":_digest(basis), "reference_sha256":_digest(reference),
            "independent_methods_sha256":reference["independent_methods_sha256"],
            "columns":len(basis["columns"]), "static_sections":len(basis["columns"]),
            "spectral_governing_corners":len(basis["columns"]), "axial_limits":2*len(basis["columns"]),
            "beams":len(basis["beams"]), "physical_beam_ends":2*len(basis["beams"]),
            "signed_beam_capacities":4*len(basis["beams"]), "maximum_residuals":maxima,
            "capacity_tolerance_knm":.01, "axial_limit_tolerance_kn":1.e-7,
            "scope":"Selected independent columns and zero-axial selected beam end sections"}
