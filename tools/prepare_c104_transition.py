"""Package the two archived C104 native mesh solves for the normal design-scenario runner."""
import argparse
import json
from pathlib import Path
import shlex

from prepare_c29_story_balance import arrays, checksum, field, read, require
from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.engineering.coupled_wall_transition import IDENTITY, SCHEMA, SIGNED_CASES, normalize_transition
from tbdy_next.engineering.design_scenario import SCHEMA as REQUEST_SCHEMA, _digest, _source_data

FRAME = "211"
WALLS = {"436": "W21", "437": "W22"}
ORIGIN = [74, .4, -1.5]
LOW, HIGH = -1.55, -1.45
# Model-specific source fingerprints from the archived experiment. The two EDBs
# used in the solves are identified separately in each native finished record.
EXPORT_SHA = "6df8a68d8816babed0aec01c1a1c8e96f8e63ff2529e1cd3078730cf78ac4910"
GEOMETRY_SHA = "8abcabc8dc322cbe3de27a9adbefbc38d1317bf33d81c6a018fc4366bda038bb"
PARENT_SHA = "703e202fc8b08f60043c571d9970945b6307e5cee99e8a45e6377c8446da56fc"


def one(items):
    items = list(items)
    require(len(items) == 1, "Expected one model definition")
    return items[0]


def load_basis(export_path, geometry, parent):
    require(checksum(export_path) == EXPORT_SHA, "C104 solved model export changed")
    # Control tokens and object names in the ETABS export are ASCII. An unrelated
    # free-text title or history line may use the localized Windows code page.
    deck = [shlex.split(s.strip()) for s in export_path.read_bytes().decode("latin-1").splitlines()
            if s.startswith("  ") and s.strip() and not s.strip().startswith("$")]

    def named(kind, name):
        return [r for r in deck if r[:2] == [kind, name]]

    def assignment(kind, label):
        return one(r for r in named(kind, label) if r[2] == "+0.00")

    def section_and_weight(kind, assigned):
        records = named(kind, field(assigned, "SECTION"))
        section = one(r for r in records if "MATERIAL" in r)
        material = one(r for r in named("MATERIAL", field(section, "MATERIAL")) if "WEIGHTPERVOLUME" in r)
        require(all(float(field(row, k)) == 1 for row in [assigned, *records]
                    for k in ("WMOD", "WEIGHTMOD") if k in row), "Unexpected weight modifier")
        return section, float(field(material, "WEIGHTPERVOLUME"))

    points = [r for r in deck if r[0] == "POINTASSIGN"]
    require(points and all(set(r[3::2]) <= {"DIAPH", "RESTRAINT", "USERJOINT"} for r in points),
            "Default point-element axes not established by the complete model export")
    require(not any(r[0] in ("POINTLOAD", "JOINTLOAD") or ("POINT" in r[0] and "AX" in r[0])
                    for r in deck), "Unsupported joint assignment in the model export")
    stories = [r for r in deck if r[0] == "STORY"]
    require("ELEV" in stories[-1] and all("HEIGHT" in r for r in stories[:-1]), "Unexpected story coordinates")
    elevations = {stories[-1][1]: float(field(stories[-1], "ELEV"))}
    z = elevations[stories[-1][1]]
    for row in reversed(stories[:-1]):
        z += float(field(row, "HEIGHT"))
        elevations[row[1]] = z
    storeys = parent["vs06_b1_geometry_source"]["table_reads"]["Story Definitions"]["rows"]
    require(len({r["Tower"] for r in storeys}) == 1 and
            {r["Story"]:float(r["Height"]) for r in storeys} == {r[1]:float(field(r, "HEIGHT")) for r in stories[:-1]},
            "Original and remeshed story definitions differ")
    cases = {}
    for case in SIGNED_CASES:
        definitions = named("LOADCASE", case)
        require(len(definitions) == 2 and definitions[0][2:] == ["TYPE", "Linear Static", "INITCOND", "NONE"]
                and definitions[1][2:] == ["LOADPAT", case, "SF", "1"], "Signed linear static case changed")
        pattern = one(named("LOADPATTERN", case))
        cases[case] = {"type":"Linear Static", "step":["Single Value", 0], "initial_condition":"NONE",
                       "scale":1, "weight_multiplier":float(field(pattern, "SELFWEIGHT")),
                       "auto_lateral":field(pattern, "TYPE") == "Seismic"}
        if cases[case]["auto_lateral"]:
            seismic = one(named("SEISMIC", case))
            require(seismic[2] == "TSC-2018" and field(seismic, "BOTTOMSTORY") == stories[-1][1]
                    and field(seismic, "TOPSTORY") == stories[0][1]
                    and not any(r[0] in ("POINTLOAD", "LINELOAD", "AREALOAD") and "LC" in r
                                and field(r, "LC") == case for r in deck), "Unsupported seismic point-load scope")
            cases[case]["story_application"] = {"code":"TSC-2018", "levels_m":elevations, "towers":1,
                "additional_object_loads":0, "bottom_story":stories[-1][1], "top_story":stories[0][1]}

    walls = {}
    for uid, label in WALLS.items():
        assigned = assignment("AREAASSIGN", label)
        section, density = section_and_weight("SHELLPROP", assigned)
        require(field(assigned, "CARDINALPOINT") == "MIDDLE"
                and not {"ANG","ANGLE","ADVANCEDAXES","OFFSET"}.intersection(assigned), "Wall orientation changed")
        plan = geometry["walls"][label]
        thickness = float(field(section, "WALLTHICKNESS"))
        require(thickness == float(plan["thickness_m"]), "Wall thickness changed")
        pressures = dict.fromkeys(SIGNED_CASES, 0.)
        loads = [r for r in named("AREALOAD", label) if r[2] == "+0.00"]
        require(len(loads) == 3, "Unexpected wall load assignments")
        for row in loads:
            case = field(row, "LC")
            if field(row, "TYPE") == "TEMP":
                require(case == "LC_T", "Unexpected thermal assignment")
            else:
                require(case in ("LC_H","LC_HE") and field(row,"DIR") == "3" and field(row,"TYPE") == "UNIFF",
                        "Unsupported wall surface load")
                pressures[case] += float(field(row, "FVAL"))
        walls[uid] = {"label":label, "x_m":list(map(float, plan["x_range_m"])),
                      "z_m":list(map(float, plan["z_range_m"])), "weight_kn_per_m2":density*thickness,
                      "pressure_kn_per_m2":pressures}
    frame = assignment("LINEASSIGN", "C104")
    section, density = section_and_weight("FRAMESECTION", frame)
    require(not {"ANG","OFFSET","CARDINALPT","ADVANCEDAXES"}.intersection(frame) and
            all(field(r,"TYPE") == "TEMP" and field(r,"LC") == "LC_T" for r in named("LINELOAD","C104")
                if r[2] == "+0.00"), "Unsupported frame axis, offset or load")
    return cases, walls, density*float(field(section,"D"))*float(field(section,"B"))


def native_slice(directory, pitch):
    archive = {key:checksum(directory/(key+".json"))
               for key in ("analysis_mesh","frame_forces","static_shell_forces","case_statuses")}
    seal = read(directory/"finished.json")
    require(archive["frame_forces"] == seal["frame_sha"] and archive["static_shell_forces"] == seal["shear_shell_sha"]
            and seal["column_segments"] == seal["wall_common_segments"] == round(5.15/pitch), "Mesh solve seal mismatch")
    status = read(directory/"case_statuses.json")
    require(status["return"] == 0 and all(status["statuses"][c] == 4 for c in SIGNED_CASES), "Unfinished case")
    mesh = read(directory/"analysis_mesh.json")
    coords = mesh["joint_coords"]
    shells, rings = [], {}
    for row in mesh["area_elements"]:
        nodes = [row["ElmJt"+str(i)] for i in (1,2,3,4)]
        if all(LOW-1e-7 <= coords[n][2] <= HIGH+1e-7 for n in nodes):
            require(row["ObjType"] == "Wall" and row["ObjLabel"] == WALLS[row["ObjName"]], "Wall namespace changed")
            shells.append([row["ObjName"], row["ElmName"], nodes])
            rings[row["ElmName"]] = nodes
    kept_coords = {n:coords[n] for nodes in rings.values() for n in nodes}
    shell_forces = read(directory/"static_shell_forces.json")
    shell_rows = [row for uid in WALLS for row in arrays(shell_forces[uid],12) if row[1] in rings]
    segments = {}
    for row in mesh["frame_elements"]:
        if row["ObjType"] == "Frame" and row["ObjName"] == FRAME:
            i,j = row["ElmJtI"],row["ElmJtJ"]
            if LOW-1e-7 <= coords[i][2] < coords[j][2] <= HIGH+1e-7:
                segments[row["ElmName"]] = (i,j)
    capture = read(directory/"frame_forces.json")
    require(not capture["errors"] and capture["units_code"] == 6, "Unqualified frame result acquisition")
    frame_rows = []
    for uid, station, element, es, case, step, number, *v in native_frame_force_rows(capture["rowsets"][FRAME], FRAME):
        if element not in segments or case not in SIGNED_CASES:
            continue
        i,j = segments[element]
        for end, node, pos in (("I",i,0), ("J",j,coords[j][2]-coords[i][2])):
            if abs(es-pos) < 2e-6:
                require(abs(station-coords[node][2]-5.15) < 2e-6, "Frame station and native joint disagree")
                frame_rows.append([uid,element,end,case,step,number,*v])
    model_sha = seal["model_sha_before_final_save"]
    result = {"pitch_m":pitch, "model_sha256":model_sha, "archives":archive,
              "generation_sha256":_digest([model_sha,archive]), "units_code":6,
              "case_statuses":{c:status["statuses"][c] for c in SIGNED_CASES}, "coordinates":kept_coords,
              "point_matrices":dict.fromkeys(kept_coords,IDENTITY), "frame_matrix":[0,1,0,0,0,1,1,0,0],
              "frame_segments":[[e,*nodes] for e,nodes in segments.items()], "shells":shells,
              "shell_rows":shell_rows, "frame_rows":frame_rows}
    result["slice_sha256"] = _digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("mesh-run","deck","original-edb","solved-edb","geometry","seed-run","out"):
        parser.add_argument("--"+arg, required=True, type=Path)
    args = parser.parse_args()
    parent = args.seed_run/"parent.source"
    require(checksum(parent) == PARENT_SHA and checksum(args.geometry) == GEOMETRY_SHA, "Wrong C104 parent or geometry")
    completed = read(args.mesh_run/"finished.json")
    require(checksum(args.original_edb) == completed["original_sha"]
            and checksum(args.solved_edb) == completed["final_private_sha"], "EDB fingerprint mismatch")
    source = read(parent)
    cases, walls, frame_weight = load_basis(args.deck, read(args.geometry), source)
    source_sha = _digest(_source_data(source))
    basis = {"schema":SCHEMA, "source_data_sha256":source_sha, "member_id":FRAME, "origin_m":ORIGIN,
             "bracket_m":[LOW,HIGH], "cases":cases, "walls":walls, "frame_weight_kn_per_m":frame_weight,
             "point_axes_source":"ETABS default XYZ. Full point assignment inventory has no axis overrides; generated mesh joints use the model default.",
             "axis_and_load_export_sha256":EXPORT_SHA, "original_edb_sha256":completed["original_sha"],
             "levels":[native_slice(args.mesh_run/name, pitch) for name,pitch in (("mesh-1",.05),("mesh-2",.025))]}
    normalize_transition(basis, source_data_sha256=source_sha)
    previous = read(args.seed_run/"input.source")
    require(previous["design_scenario"]["parent_input_sha256"] == PARENT_SHA, "Selection scenario parent mismatch")
    request = {"schema":REQUEST_SCHEMA, "scenario_id":"C104-signed-transition", "parent_input_sha256":PARENT_SHA,
               "column_selection":previous["column_selection"], "beam_selection":previous["beam_selection"],
               "coupled_wall_transition":basis}
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(request, output, allow_nan=False)


if __name__ == "__main__":
    main()
