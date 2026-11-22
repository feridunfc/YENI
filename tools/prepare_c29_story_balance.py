"""Prepare the C29 eight-part upper-body balance from independently captured native inputs."""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from math import dist, fsum, hypot, isclose, isfinite
from pathlib import Path
import shlex
from tempfile import TemporaryDirectory

from tbdy_next.column_engine.source_bank import native_frame_force_rows
from tbdy_next.engineering.design_scenario import create_design_scenario
from tbdy_next.engineering.gravity_story_basis import project_native_story_frame_forces
from tbdy_next.engineering.gravity_wall_cut import project_upper_wall_forces

STORIES = {"+0.00": (-5.15, 32, 21), "+4.50": (0., 32, 4)}
CASES = ("C29G_U_F", "C29G_TN_F", "C29G_TP_F")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def read(path):
    return json.loads(path.read_bytes())


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def check_force_controls(current, archived):
    for uid in ("225", "142"):
        def index(capture):
            rows = list(native_frame_force_rows(capture["rowsets"][uid], uid))
            values = {tuple(row[:7]): row[7:] for row in rows}
            require(rows and len(values) == len(rows), "Duplicate or empty C29 frame control: " + uid)
            return values

        active, reference = index(current), index(archived)
        require(active.keys() == reference.keys() and all(
            len(active[key]) == len(reference[key]) == 6 and
            all(isclose(a, b, rel_tol=1e-9, abs_tol=1e-6) for a, b in zip(active[key], reference[key]))
            for key in active
        ), "Same-generation frame control mismatch: " + uid)


def input_deck(path):
    groups = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("$ "):
            section = line[2:]
            groups[section] = []
        elif line.strip():
            groups[section].append(shlex.split(line))
    return groups


def field(row, name):
    return row[row.index(name) + 1]


def arrays(raw, width):
    count, *columns = raw
    require(type(count) is int and len(columns) == width and all(len(c) == count for c in columns),
            "Invalid native input array lengths")
    return zip(*columns)


def above(z, points):
    elevations = [v[2] for v in points]
    require(not (min(elevations) < z - 1e-7 and max(elevations) > z + 1e-7),
            "Upper-body load requires clipping through an element interior")
    return max(elevations) > z + 1e-7


def area(points):
    require(len(points) in (3, 4), "Only planar triangle/quad analysis shells are supported")
    p = points[0]
    arms = [[v-u for v, u in zip(q, p)] for q in points[1:]]
    cross = [[v[1]*w[2] - v[2]*w[1], v[2]*w[0] - v[0]*w[2], v[0]*w[1] - v[1]*w[0]]
             for v, w in zip(arms, arms[1:])]
    if len(cross) == 2:
        require(isclose(hypot(*(a+b for a,b in zip(*cross))), fsum(hypot(*c) for c in cross),
                        rel_tol=1e-8, abs_tol=1e-10), "Warped or nonconvex shell")
    return 0.5 * hypot(*(fsum(v[i] for v in cross) for i in range(3)))


def load_definitions(deck, pairs, definitions):
    require(not deck["POINT OBJECT LOADS"], "Unqualified assigned point loads")
    require(all(row[2] in ("COLUMN", "BEAM", "LINE") for row in deck["LINE CONNECTIVITIES"]),
            "Unexpected link in the upper-body load path")
    load_scale = {r[1]: float(field(r, "SELFWEIGHT")) for r in deck["LOAD PATTERNS"] if r[0] == "LOADPATTERN"}
    combos = {}
    for pair in pairs.values():
        case = pair["first"]
        rows = [r for r in deck["LOAD CASES"] if r[1] == case]
        scales = {field(r, "LOADPAT"):float(field(r, "SF")) for r in rows if "LOADPAT" in r}
        native = definitions[case]
        require(scales == pair["patterns"] == native["loads"] and native["geometry"] == 0 and
                native["initial"] == "None" and native["result_storage"][0] is False and
                any("RESULTSSAVED" in r and field(r,"RESULTSSAVED") == "Final" for r in rows),
                "First-order load vector or saved step changed: " + case)
        combos[case] = scales
    require(set(combos) == set(CASES), "Unexpected first-order C29 case set")
    patterns = set().union(*combos.values())
    require(all(load_scale[p] == (1. if p == "LC_DL" else 0.) for p in patterns), "Self-weight pattern changed")
    for r in deck["FRAME OBJECT LOADS"] + deck["SHELL OBJECT LOADS"]:
        pat = field(r, "LC")
        if pat not in patterns:
            continue
        kind = field(r, "TYPE")
        require((kind == "TEMP" and pat == "LC_T") or
                (kind in ("TRAPF", "UNIFF") and field(r, "DIR") == "GRAV"),
                "Unsupported input load kind: " + str(r))
    return combos


def upper_loads(deck, tables, native, weight, cases):
    """Integrate external assignments and self-weight without reading any member force."""
    coord = read(native / "joint-coordinates.json")
    loads = read(native / "applied-loads.json")
    line_point = read(weight / "element-gravity.json")["point_line"]
    line = read(weight / "line-inputs.json")
    shell = read(weight / "area-inputs.json")
    shells = {r["ElmName"]: r for r in tables["Objects and Elements - Areas"]["rows"]}
    frames = {r["ElmName"]: r for r in tables["Objects and Elements - Frames"]["rows"] if r["ObjType"] == "Frame"}
    require(set(frames) == set(line) and set(shells) == set(shell), "Analysis weight coverage mismatch")
    joints = tables["Objects and Elements - Joints"]["rows"]
    require(set(coord) == {r["ElmName"] for r in joints} and
            all(len(v) == 3 and all(isfinite(x) for x in v) for v in coord.values()), "Analysis joint coverage mismatch")
    support_joints = {(r[1], r[2]) for r in deck["POINT ASSIGNS"] if "RESTRAINT" in r or "SPRINGPROP" in r}
    observed_supports = set()
    bottom = min(story[0] for story in STORIES.values())
    for r in joints:
        point = coord[r["ElmName"]]
        require(all(abs(point[i] - float(r["Global" + axis])) <= 0.0001 for i, axis in enumerate("XYZ")),
                "Precise native joint disagrees with eight-part mesh")
        location = r["ObjLabel"], r["Story"]
        if r["ObjType"] == "Joint" and location in support_joints:
            require(point[2] <= bottom + 1e-7, "Point support inside the upper free body")
            observed_supports.add(location)
    require(observed_supports == support_joints, "Unlocated upper-body support assignment")
    section = {r["Name"]:r for r in tables["Frame Section Property Definitions - Summary"]["rows"]}
    kind = {r[1]:r[2] for r in deck["LINE CONNECTIVITIES"]}
    opts = {r["UniqueName"]:r["SelfWtOpt"] for r in tables["Frame Assignments - End Length Offsets"]["rows"]}
    density = {r[1]:float(field(r,"WEIGHTPERVOLUME")) for r in deck["MATERIAL PROPERTIES"] if "WEIGHTPERVOLUME" in r}
    require(loads["concrete_weight"][0] == density["C35/45"], "Native concrete weight density conflict")
    properties = {}
    for r in deck["SLAB PROPERTIES"] + deck["WALL PROPERTIES"]:
        if "PROPTYPE" in r:
            th = "SLABTHICKNESS" if "SLABTHICKNESS" in r else "WALLTHICKNESS"
            properties[r[1]] = float(field(r,th)) * density[field(r,"MATERIAL")]
        else:
            require(not set(r) & {"WMOD","WEIGHTMOD","WEIGHTMODIFIER"}, "Unsupported section weight override")
    frame_pts = {e:[coord[r[k]] for k in ("ElmJtI","ElmJtJ")] for e,r in frames.items()}
    shell_pts = {e: [coord[r[k]] for k in ("ElmJt1", "ElmJt2", "ElmJt3", "ElmJt4")
                     if r.get(k) not in (None, "", "None")] for e, r in shells.items()}
    springs = {(r[1],r[2]) for r in deck["AREA ASSIGNS"] if "SPRINGPROP" in r}
    for e, r in shells.items():
        if (r["ObjLabel"], r["Story"]) in springs:
            require(max(q[2] for q in shell_pts[e]) <= bottom + 1e-7,
                    "Spring support inside the upper body")
    patterns = set().union(*cases.values())
    out = {}
    for story, (z, _, _) in STORIES.items():
        force = defaultdict(lambda: defaultdict(list))
        self_weight = defaultdict(list)
        short = []
        for e, model in line.items():
            pts = frame_pts[e]
            if not above(z,pts):
                continue
            row = frames[e]
            prop = section[model["section"][0]]
            require(opts[row["ObjName"]] == "Auto" and prop["Material"] == "C35/45" and model["material"] == ["None"] and
                    model["section"][2] is False and model["modifiers"][0][7] == 1. and float(prop["WMod"]) == 1. and
                    all(value == 0 for end in model["insertion"] for value in end), "Unsupported frame weight definition")
            length = dist(*pts)
            typ = kind[row["ObjLabel"]]
            require(typ in ("BEAM","COLUMN") and length > 0, "Unsupported analysis frame type")
            if typ == "BEAM":
                clear = length - fsum(model["offset"][:2])
                # CSI Analysis Reference Manual, Frame Element / End Offsets.
                effective = max(0.01*length, clear)
                if clear < 0.01*length:
                    short.append({"element":e, "full_length_m":length, "raw_clear_m":clear, "weight_length_m":effective})
            else:
                effective = length
            self_weight[typ].append(effective * float(prop["Area"]) * density[prop["Material"]])
        for e, model in shell.items():
            pts = shell_pts[e]
            if not above(z,pts):
                continue
            require(model["thickness"][0] == 0 and model["modifiers"][0][9] == 1. and model["material"] == ["None"],
                    "Unsupported area weight override")
            self_weight[shells[e]["ObjType"]].append(area(pts) * properties[model["section"][0]])
        # These are applied loads on the analysis model. Object assignments are
        # not added again after ETABS transfers null-line loading onto the mesh.
        for e, pat, typ, cs, direction, r1,r2,d1,d2,v1,v2 in arrays(loads["element_line"],11):
            if pat in patterns:
                pts = frame_pts[e]
                require((typ,cs,direction)==(1,"Global",6) and 0 <= r1 <= r2 <= 1.000000001 and
                        isclose(d2-d1,(r2-r1)*dist(*pts),rel_tol=1e-8,abs_tol=1e-8), "Unsupported distributed line load")
                if above(z,pts):
                    force[pat]["distributed_line"].append(-.5*(v1+v2)*(d2-d1))
        for e,pat,typ,cs,direction,rel,station,val in arrays(line_point,8):
            if pat in patterns:
                pts=frame_pts[e]
                require((typ,cs,direction)==(1,"Global",6) and 0 <= rel <= 1 and
                        isclose(station,rel*dist(*pts),abs_tol=1e-8), "Unsupported concentrated line load")
                if (1-rel)*pts[0][2] + rel*pts[1][2] > z + 1e-7:
                    force[pat]["point_on_line"].append(-val)
        for j,pat,step,cs,_,_,fz,*_moments in arrays(loads["point_element"],10):
            if pat in patterns:
                require(cs == "Global" and step == 0, "Point load is not a global pattern assignment")
                if above(z,[coord[j]]):
                    force[pat]["point"].append(-fz)
        for e,pat,cs,direction,value in arrays(loads["element_surface"],5):
            if pat in patterns:
                require((cs,direction)==("Global",6), "Unsupported distributed area load")
                if above(z,shell_pts[e]):
                    force[pat]["distributed_area"].append(-value*area(shell_pts[e]))
        by_kind = {k:fsum(v) for k,v in self_weight.items()}
        by_pat = {p:{k:fsum(v) for k,v in components.items()} for p,components in force.items()}
        eq = {}
        for name,coef in cases.items():
            eq[name] = {"upper_external_applied_kn":fsum(coef.get(p,0.)*fsum(vals.values()) for p,vals in by_pat.items()),
                        "upper_self_weight_kn":coef["LC_DL"]*fsum(by_kind.values())}
        out[story] = {"z_m":z,"applied_by_pattern_kn":by_pat,"self_weight_by_type_kn":by_kind,
                      "short_beams":short,"cases":eq}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source","scenario","readback","deck","native","weight","out"):
        parser.add_argument("--"+arg, type=Path, required=True)
    parser.add_argument("--ultimate-only", action="store_true")
    args = parser.parse_args()
    source_raw = args.source.read_bytes()
    request = read(args.scenario)
    require(request["parent_input_sha256"] == sha256(source_raw).hexdigest(), "Wrong physical parent source")
    source = json.loads(source_raw)
    pair = request["gravity_order_pair"]
    finest, = (s for s in pair["refined_levels"] if s["divisions"]==8)
    archive = read(args.readback/"story-8.json")
    identity = read(args.native/"complete.json")
    additional = read(args.weight/"complete.json")
    require(identity["deck_sha256"] == checksum(args.deck) == archive["panel_assignment_archive"]["source_sha256"]
            and identity["units"] == 6 and identity["cases"] == additional["load_case_status"] == dict.fromkeys(CASES,4),
            "Source deck, units or finished status differs from capture")
    for key in ("model_sha256","analysis_generation"):
        require(identity[key] == additional[key] == finest[key] == archive[key], "Source mismatch: "+key)
    check_force_controls(read(args.native / "frame-controls.json"), archive["columns"])
    selection = read(args.native/"selection.json")
    require(selection["before"] == selection["after"] and
            {k for k,v in selection["during"]["cases"].items() if v} == set(CASES)
            and not any(selection["during"]["combos"].values()), "Incomplete case selection or restoration")
    deck = input_deck(args.deck)
    cases = load_definitions(deck, pair["cases"], read(args.readback/"case-definitions-8.json")["readback"])
    tables = archive["tables"]["table_reads"]
    external = upper_loads(deck,tables,args.native,args.weight,cases)
    read_files = [args.deck,args.scenario,args.source,args.readback/"story-8.json",args.readback/"case-definitions-8.json"]
    read_files += [args.native/(n+".json") for n in ("complete","frame-controls","selection","shell-forces","joint-axes",
                                                      "applied-loads","joint-coordinates","input-tables")]
    read_files += [args.weight/(n+".json") for n in ("complete","element-gravity","line-inputs","area-inputs")]
    manifest = {f"{p.parent.name}/{p.name}":checksum(p) for p in read_files}
    identifier = sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    chosen = {CASES[0]} if args.ultimate_only else set(CASES)
    cuts = finest["story_basis_source"]["story_cuts"]
    raw = read(args.native/"shell-forces.json")
    xyz = read(args.native/"joint-coordinates.json")
    axes = read(args.native/"joint-axes.json")
    for story, (z, column_count, wall_count) in STORIES.items():
        cut = cuts[story]
        require(cut["z_m"] == z and not cut["equilibrium"] and len(cut["forces"]) == column_count*len(CASES)
                and all(v["kind"] == "COLUMN" for v in cut["forces"]), "Existing cut source changed")
        uid = "225" if story == "+0.00" else "142"
        columns = project_native_story_frame_forces(source, finest, uid, z, pair["cases"], archive)
        order = lambda force: (force["object_id"], force["case"])
        require(columns["status"] == "STORY_NATIVE_FRAME_SOURCE_CALCULATED" and
                sorted(columns["forces"], key=order) == sorted(cut["forces"], key=order),
                "Archived case, side or signed column force differs on " + story)
        walls = project_upper_wall_forces(source, finest, z, CASES, model_sha256=identity["model_sha256"],
            analysis_generation=identity["analysis_generation"], area_mesh=tables["Objects and Elements - Areas"]["rows"],
            joint_xyz=xyz, shell_forces=raw, joint_transformations=axes)
        require(len(walls)==len(CASES)*wall_count, "Wall census mismatch")
        cut["forces"].extend(row for row in walls if row["case"] in chosen)
        cut["equilibrium"] = {name:{**value,"reference":"NATIVE_ANALYSIS_INPUT_LOADS_AND_WEIGHT_SHA256_"+identifier}
                              for name,value in external[story]["cases"].items() if name in chosen}
    request["scenario_id"] = "c29-upper-free-body-ultimate" if args.ultimate_only else "c29-upper-free-body-three-gravity-cases"
    create_design_scenario(source_raw,request)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.out.parent) as staging:
        folder = Path(staging) / "bundle"
        folder.mkdir()
        for name, value in (("upper-loads", external), ("source-manifest", manifest), ("scenario", request)):
            with (folder / (name + ".json")).open("w", encoding="utf8") as stream:
                json.dump(value, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        if args.out.exists():
            require(all((args.out / p.name).is_file() and checksum(args.out / p.name) == checksum(p)
                        for p in folder.iterdir()), "An existing output contains a different or incomplete bundle")
        else:
            folder.rename(args.out)
    print(args.out/"scenario.json")


if __name__ == "__main__":
    main()
