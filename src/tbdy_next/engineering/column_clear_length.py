"""Resolve vertical column clear lengths from ETABS model faces and native end cuts."""
from __future__ import annotations

from collections import defaultdict
from math import atan2, fsum, hypot, isclose, isfinite, pi
from typing import Any, Mapping

from ..column_engine.native_archive import identity
from ..etabs_geometry import AREA_ELEMENTS, AREA_INSERTION, FLOOR_CONNECTIVITY, FRAME_INSERTION, SLAB_PROPERTIES
from ..quick_checks import _rows
from .live_column import _gateway_ready, text_number
from .scwb_axial import _configured_end

FACE_BASIS = "ETABS_MODEL_PHYSICAL_FACES_AND_CUTS"
WALL_COUPLED = "ETABS_WALL_COUPLED_COLUMN_MESH"
WALL_CONNECTIVITY = "Wall Object Connectivity"
WALL_PROPERTIES = "Wall Property Definitions - Specified"
_TOL_M = 1e-8
_FRAME_TRANSLATION = ("XI", "YI", "ZI", "XJ", "YJ", "ZJ")
_SHELL_TRANSLATION = ("Offset1", "Offset2", "Offset3")


def _close(a: float, b: float) -> bool:
    return isclose(a, b, rel_tol=0.0, abs_tol=_TOL_M)


def _records(tables, name, fields, meters=()):
    rows = _rows({"tables": tables}, name, set(fields.split()))
    units = tables[name]["field_metadata"].get("units_by_field", {})
    if any(units.get(key) != "m" for key in meters):
        raise ValueError(f"{name}: required length fields must be in m")
    return rows


def _index(rows, key):
    out = {}
    for row in rows:
        value = identity(row[key], key)
        if value in out:
            raise ValueError(f"Duplicate native identity {key}={value}")
        out[value] = row
    return out


def _group(rows, key):
    out = defaultdict(list)
    for row in rows:
        out[identity(row[key], key)].append(row)
    return out


def _translation_fields(table, version, coordinates, context):
    """Recognize explicit offsets and the complete ETABS sparse display variant."""
    meta = table["field_metadata"]
    expected = set(coordinates) | set(context)
    if (meta.get("table_version") != version or not expected <= set(meta["field_keys"])
            or any(meta["units_by_field"].get(key) != "m" for key in coordinates)):
        raise ValueError("Unknown insertion offset schema")
    # The unfiltered native display suppresses the entire assignment group when unused.
    displayed = expected.intersection(table["fields"])
    if not displayed and table.get("api_signature") in {"seven_list", "seven_string"}:
        return ()
    if displayed == expected:
        return coordinates
    raise ValueError("Incomplete insertion offset assignment fields")


def _no_translation(row, fields):
    return all(text_number(row[k], k) == 0 for k in fields)


def _xyz(row, fields):
    return tuple(text_number(row[k], k) for k in fields)


def _turn(a, b, point):
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])


def _floor_at_joint(polygons, point_xyz, points):
    """Read a horizontal floor's ordered corners and check its shared mesh point."""
    if len(polygons) > 1:
        ordered = _index(polygons, "Order")
        if set(ordered) != {str(i) for i in range(1, len(polygons) + 1)}:
            raise ValueError("Invalid floor corner continuation order")
        polygons = [ordered[str(i)] for i in range(1, len(polygons) + 1)]
    corners = [row[k] for row in polygons for k in ("UniquePt1", "UniquePt2", "UniquePt3", "UniquePt4")
               if row.get(k) not in (None, "", "None")]
    coords = [_xyz(points[n], "XYZ") for n in corners]
    if (len(set(corners)) != len(corners) or len(set(coords)) != len(coords) or len(coords) < 3
            or not all(_close(z, point_xyz[2]) for _, _, z in coords)
            or any(row.get("CurvedEdges") not in (None, "", "None", "0") for row in polygons)):
        raise ValueError("Floor corners do not define a horizontal straight-sided support")
    edges = list(zip(coords, coords[1:] + coords[:1]))
    if fsum(_turn(a, b, coords[0]) for a, b in edges) <= 0:
        raise ValueError("Floor corner order does not face upward")
    angles = []
    for a, b in edges:
        ax, ay = a[0] - point_xyz[0], a[1] - point_xyz[1]
        bx, by = b[0] - point_xyz[0], b[1] - point_xyz[1]
        cross, dot = ax * by - ay * bx, ax * bx + ay * by
        if abs(cross) <= _TOL_M * hypot(bx - ax, by - ay) and dot <= _TOL_M ** 2:
            return corners
        angles.append(atan2(cross, dot))
    if fsum(angles) < pi:
        raise ValueError("Floor polygon does not contain the shared joint")
    return corners


def _beam_face(incident, beam, point, xyz, points, insertions, fields):
    row = insertions[beam["frame_id"]]
    other = beam["point_j"] if incident["end"] == "I" else beam["point_i"]
    axes, dims = beam.get("axes_global"), beam.get("dims")
    if (row["Story"] != point["Story"] or row["Story"] != beam["story"] or row["Label"] != beam["label"]
            or row["CardinalPt"] != "8 (Top Center)" or row["Mirror2"] != "No" or row["Mirror3"] != "No"
            or not _no_translation(row, fields) or dims is None or axes is None or not _close(axes[1][2], 1.0)
            or not _close(_xyz(points[other], "XYZ")[2], xyz[2])):
        raise ValueError(f"Beam {beam['frame_id']} lacks a horizontal, unshifted Top Center face")
    depth = dims.local2_extent_mm / 1000
    return {"beam_id": beam["frame_id"], "end": incident["end"], "depth_m": depth,
            "top_z_m": xyz[2], "soffit_z_m": xyz[2] - depth}


def project_column_clear_lengths(source, frames, adjacency, members, pmm_scope):
    """Share one projection between R10 and R08, with legacy sources using their existing spans."""
    r10 = (source.get("column_axial") or {}).get("r10_source") or {}
    tables = r10.get("table_reads") or {}
    if not any(key in tables for key in (FRAME_INSERTION, AREA_INSERTION, SLAB_PROPERTIES, FLOOR_CONNECTIVITY)):
        return None

    results: dict[str, dict[str, Any]] = {}
    plan = {"method": "column-model-clear-length.v2", "per_member": results}
    try:
        capture = source["capture_metadata"]
        geometry = source["geometry_capture"]
        b1 = source["vs06_b1_geometry_source"]
        model = capture["model_filename"]
        if (source.get("source_mode") != "LIVE_ETABS" or not model or capture.get("model_locked_observed") is not True
                or r10.get("schema") != "tbdy.next.r10-live-source.v1"
                or r10.get("model_locked_before") is not True or r10.get("model_locked_after") is not True
                or any(type(u) is not int or u != 6 for u in (r10["units_before"], r10["units_after"],
                                                            geometry["present_units"], geometry["present_units_after"]))
                or geometry.get("unit_state_unchanged") is not True):
            raise ValueError("Locked kN-m model geometry is required")
        _gateway_ready(b1, model)
        geom_tables = geometry["tables"]
        _index(_records(geom_tables, "RECTANGULAR_SECTIONS", "Name t2 t3", ("t2", "t3")), "Name")
        _index(_records(geom_tables, "FRAME_ASSIGNMENTS", "UniqueName Label Story Type AnalysisSect"), "UniqueName")
        if geom_tables["FRAME_ASSIGNMENTS"]["field_metadata"]["units_by_field"].get("AxisAngle") != "deg":
            raise ValueError("Frame local-axis angle units are unresolved")
        beams = _records(geom_tables, "BEAM_CONNECTIVITY", "UniqueName Story UniquePtI UniquePtJ")
        columns = _records(geom_tables, "COLUMN_CONNECTIVITY", "UniqueName Story UniquePtI UniquePtJ Length", ("Length",))
        if set(_index(beams + columns, "UniqueName")) != set(frames):
            raise ValueError("Native frame catalogue is incomplete")
        points = _index(_records(b1["table_reads"], "Point Object Connectivity", "UniqueName Story X Y Z", "XYZ"), "UniqueName")
        native_joints = _index(_records(tables, "Objects and Elements - Joints",
                                        "ElmName ObjName ObjType Story GlobalX GlobalY GlobalZ",
                                        ("GlobalX", "GlobalY", "GlobalZ")), "ElmName")
        insertions = _index(_records(tables, FRAME_INSERTION, "UniqueName Story Label CardinalPt Mirror2 Mirror3"), "UniqueName")
        frame_fields = _translation_fields(tables[FRAME_INSERTION], 1, _FRAME_TRANSLATION, ("OffsetCSys",))
        slab_fields = _translation_fields(tables[AREA_INSERTION], 2, _SHELL_TRANSLATION,
                                         ("CoordSys", "PointLabel", "PointName", "PointNumber"))
        slab_insertions = _group(_records(tables, AREA_INSERTION, "UniqueName Story Label CardinalPt"), "UniqueName")
        slabs = _index(_records(tables, SLAB_PROPERTIES, "Name PropType ModelType Thickness", ("Thickness",)), "Name")
        floors = _group(_records(tables, FLOOR_CONNECTIVITY, "UniqueName Story FloorBay UniquePt1 UniquePt2 UniquePt3"), "UniqueName")
        assignments = _index(_records(b1["table_reads"], "Area Assignments - Section Properties",
                                      "UniqueName Story Label PropType SectProp"), "UniqueName")
        floor_mesh = defaultdict(lambda: defaultdict(list))
        wall_edges = defaultdict(list)
        area_elements = _records(tables, AREA_ELEMENTS, "Story ElmName ObjType ObjName ObjLabel ElmJt1 ElmJt2 ElmJt3")
        for row in area_elements:
            obj = (row["ObjType"], row["ObjName"], row["Story"], row["ObjLabel"])
            nodes = [row[k] for k in ("ElmJt1", "ElmJt2", "ElmJt3", "ElmJt4") if row.get(k) not in (None, "", "None")]
            for node in nodes:
                floor_mesh[node][obj].append(row["ElmName"])
            if obj[0] == "Wall" and len(nodes) in (3, 4) and len(set(nodes)) == len(nodes):
                for a, b in zip(nodes, nodes[1:] + nodes[:1]):
                    wall_edges[frozenset((a, b))].append((obj, row["ElmName"]))
    except (KeyError, TypeError, ValueError) as exc:
        return {**plan, "source_error": str(exc)}

    def matching_model_joint(joint_id):
        point = points[joint_id]
        xyz = _xyz(point, "XYZ")
        native = native_joints[joint_id]
        if (native["ObjType"] != "Joint" or native["ObjName"] != joint_id or native["Story"] != point["Story"]
                or not all(_close(a, b) for a, b in zip(xyz, _xyz(native, ("GlobalX", "GlobalY", "GlobalZ"))))):
            raise ValueError(f"Model and analysis joint {joint_id} differ")
        return point, xyz

    def mat_contact(pi, pj):
        point, xyz_i = matching_model_joint(pi)
        _, xyz_j = matching_model_joint(pj)
        if xyz_i[2] >= xyz_j[2]:
            return None
        mats = {}
        for (kind, uid, story, label), elements in sorted(floor_mesh.get(pi, {}).items()):
            assignment = assignments.get(uid, {})
            if (kind == "Floor" and story == point["Story"] == assignment.get("Story")
                    and label == assignment.get("Label") and assignment.get("PropType") == "Slab"
                    and slabs.get(assignment.get("SectProp"), {}).get("PropType") == "Mat"
                    and any(r.get("Story") == story and r.get("FloorBay") == label for r in floors.get(uid, ()))):
                mats[uid] = sorted(elements)
        if mats:
            return {"base_joint_id": pi, "upper_joint_id": pj, "mat_analysis_elements": mats}
        return None

    wall_tables = b1["table_reads"]
    wall_roster = wall_sections = None
    if any(table in wall_tables for table in (WALL_CONNECTIVITY, WALL_PROPERTIES)):
        try:
            wall_roster = _index(_records(wall_tables, WALL_CONNECTIVITY,
                "UniqueName Story WallBay UniquePt1 UniquePt2 UniquePt3 UniquePt4"), "UniqueName")
            wall_sections = _index(_records(wall_tables, WALL_PROPERTIES,
                "Name ModelType Thickness", ("Thickness",)), "Name")
        except (KeyError, TypeError, ValueError):
            wall_roster = wall_sections = None

    def wall_contact(obj, elements):
        _, uid, story, label = obj
        if wall_roster is None:
            raise ValueError(f"Unverified Wall contact ({uid})")
        row, assign = wall_roster[uid], assignments[uid]
        insert, = slab_insertions[uid]
        if (row["Story"] != story or row["WallBay"] != label
                or assign["PropType"] != "Wall"
                or any(r["Story"] != story or r["Label"] != label for r in (assign, insert))
                or insert["CardinalPt"] != "Middle" or not _no_translation(insert, slab_fields)):
            raise ValueError(f"Wall {uid} lacks a matching centered structural assignment")
        prop = wall_sections[assign["SectProp"]]
        corners = [_xyz(points[row[f"UniquePt{i}"]], "XYZ") for i in range(1, 5)]
        if (prop["ModelType"] not in {"Shell-Thin", "Shell-Thick"} or len(set(corners)) != 4
                or len({p[:2] for p in corners}) != 2):
            raise ValueError(f"Wall {uid} does not define a vertical structural shell")
        lo, hi = min(p[2] for p in corners), max(p[2] for p in corners)
        thickness = text_number(prop["Thickness"], "Thickness")
        if hi <= lo or thickness <= 0:
            raise ValueError(f"Invalid Wall contact ({uid})")
        return {"wall_id": uid, "label": label, "section": prop["Name"], "base_z_m": lo, "top_z_m": hi,
                "thickness_m": thickness, "analysis_element_ids": sorted(set(elements))}, corners

    def support_at(joint_id, *, lower=False):
        point, xyz = matching_model_joint(joint_id)
        beams = [_beam_face(end, frames[end["frame_id"]], point, xyz, points, insertions, frame_fields)
                 for end in adjacency.get(joint_id, ()) if end["type"] == "Beam"]
        slab_faces, walls_below = [], []
        for (kind, uid, story, label), elements in sorted(floor_mesh[joint_id].items()):
            if kind == "Wall" and lower and story == point["Story"]:
                wall, corners = wall_contact((kind, uid, story, label), elements)
                edge = [p for p in corners if _close(p[2], xyz[2])]
                if (not _close(wall["top_z_m"], xyz[2]) or len(edge) != 2
                        or not _close(_turn(*edge, xyz), 0)
                        or any(x < min(a, b) - _TOL_M or x > max(a, b) + _TOL_M
                               for x, a, b in zip(xyz[:2], edge[0], edge[1]))):
                    raise ValueError(f"Wall {uid} does not end below lower joint {joint_id}")
                walls_below.append(wall)
                continue
            if kind != "Floor" or story != point["Story"]:
                raise ValueError(f"Joint {joint_id} has an unsupported {kind} contact ({uid})")
            polygons, assign = floors[uid], assignments[uid]
            first = [r for r in polygons if r.get("Order") == "1"] if len(polygons) > 1 else polygons
            rows = slab_insertions[uid]
            if (len(first) != 1 or len(rows) != 1 or assign["PropType"] != "Slab" or first[0]["FloorBay"] != label
                    or any(row["Story"] != story or row["Label"] != label for row in (assign, *rows))
                    or first[0]["Story"] != story or rows[0]["CardinalPt"] != "Top"
                    or not _no_translation(rows[0], slab_fields)):
                raise ValueError(f"Floor {uid} lacks an unshifted Top face")
            slab = slabs[assign["SectProp"]]
            thickness = text_number(slab["Thickness"], "Thickness")
            if (slab["PropType"] not in {"Slab", "Mat"} or slab["ModelType"] not in {"Shell-Thin", "Shell-Thick"}
                    or thickness <= 0):
                raise ValueError(f"Floor {uid} is outside the uniform structural slab scope")
            slab_faces.append({"floor_id": uid, "label": label, "section": slab["Name"], "type": slab["PropType"],
                               "corner_ids": _floor_at_joint(polygons, xyz, points),
                               "analysis_element_ids": sorted(elements), "thickness_m": thickness,
                               "top_z_m": xyz[2], "soffit_z_m": xyz[2] - thickness})

        if beams:
            soffit = beams[0]["soffit_z_m"]
            if (not all(_close(b["soffit_z_m"], soffit) for b in beams)
                    or any(s["type"] != "Slab" or s["soffit_z_m"] < soffit - _TOL_M for s in slab_faces)):
                raise ValueError(f"Joint {joint_id} has different support soffits")
        elif walls_below and slab_faces and all(s["type"] == "Slab" for s in slab_faces):
            soffit = min(s["soffit_z_m"] for s in slab_faces)
        elif len(slab_faces) == 1 and slab_faces[0]["type"] == "Mat":
            soffit = slab_faces[0]["soffit_z_m"]
        else:
            raise ValueError(f"Joint {joint_id} has no supported beam panel or mat")
        return {"joint_id": joint_id, "joint_z_m": xyz[2], "top_z_m": xyz[2], "soffit_z_m": soffit,
                "beams": beams, "slabs": slab_faces, **({"walls_below": walls_below} if walls_below else {})}

    def coupled_wall_mesh(mesh, inside, pi, pj, xyz_i, xyz_j):
        """Join the ordered column elements to shell edges by exact analysis joint IDs."""
        contacts = defaultdict(list)
        for node in inside | {pi, pj}:
            for obj, elements in floor_mesh.get(node, {}).items():
                if obj[0] == "Wall":
                    contacts[obj].extend(elements)
        witnesses = {obj: wall_contact(obj, elements) for obj, elements in sorted(contacts.items())}
        segments = []
        for element, nodes in mesh["analysis_element_end_joints"].items():
            xyz = sorted((_xyz(native_joints[n], ("GlobalX", "GlobalY", "GlobalZ")) for n in nodes), key=lambda p: p[2])
            a, b = xyz
            if (any(not all(_close(x, y) for x, y in zip(p[:2], xyz_i[:2])) for p in xyz)
                    or not xyz_i[2] <= a[2] < b[2] <= xyz_j[2]):
                raise ValueError("Wall-coupled frame analysis chain leaves its native column axis")
            matches = []
            for obj, shell in wall_edges.get(frozenset(nodes), ()):
                wall, corners = witnesses[obj]
                start, end = sorted({p[:2] for p in corners})
                if (any(not _close(_turn(start, end, p), 0) for p in xyz)
                        or any(x < min(l, h) - _TOL_M or x > max(l, h) + _TOL_M
                               for x, l, h in zip(a[:2], start, end))
                        or a[2] < wall["base_z_m"] - _TOL_M or b[2] > wall["top_z_m"] + _TOL_M):
                    raise ValueError(f"Wall {obj[1]} analysis edge leaves its physical shell")
                matches.append({"wall_id": obj[1], "shell_element_id": shell})
            segments.append({"analysis_element_id": element, "analysis_joint_ids": list(nodes),
                             "z_min_m": a[2], "z_max_m": b[2], "coincident_wall_edges": matches})
        segments.sort(key=lambda record: record["z_min_m"])
        if (not segments or not _close(segments[0]["z_min_m"], xyz_i[2])
                or not _close(segments[-1]["z_max_m"], xyz_j[2])
                or any(not _close(a["z_max_m"], b["z_min_m"]) for a, b in zip(segments, segments[1:]))
                or not any(s["coincident_wall_edges"] for s in segments)):
            raise ValueError("No continuous frame chain with verified wall shell edges")
        return {"analysis_segments": segments, "walls": [wall for wall, _ in witnesses.values()],
                "segments_with_common_shell_edge": sum(bool(s["coincident_wall_edges"]) for s in segments),
                "element_count": len(segments), "joint_ids": {"I": pi, "J": pj}}

    for uid in members:
        row = results[uid] = {"member_id": uid, "status": "MODEL_CLEAR_LENGTH_UNRESOLVED"}
        if "point_restraints" in r10 and uid in frames:
            try:
                frame = frames[uid]
                contact = mat_contact(frame["point_i"], frame["point_j"])
                if contact is not None:
                    row["mat_contact"] = contact
            except (KeyError, TypeError, ValueError):
                pass  # Clear-length evaluation records the independent member outcome below.
        try:
            frame = frames[uid]
            pi, pj = frame["point_i"], frame["point_j"]
            xyz_i, xyz_j = (_xyz(points[point], "XYZ") for point in (pi, pj))
            mesh = (pmm_scope or {})["analysis_mesh"]["members"][uid]
            column = insertions[uid]
            if (not all(_close(a, b) for a, b in zip(xyz_i[:2], xyz_j[:2])) or xyz_i[2] >= xyz_j[2]
                    or column["Story"] != frame["story"] or column["Label"] != frame["label"]
                    or column["CardinalPt"] not in {"5 (Middle Center)", "10 (Centroid)"}
                    or not _no_translation(column, frame_fields)):
                raise ValueError("Upright, centered column required")
            inside = {node for ends in mesh["analysis_element_end_joints"].values() for node in ends} - {pi, pj}
            shell_kinds = sorted({obj[0] for node in inside for obj in floor_mesh.get(node, ())})
            if shell_kinds == ["Wall"]:
                matching_model_joint(pi)
                matching_model_joint(pj)
                cut_i, length = _configured_end(pmm_scope, frame, "I")
                cut_j, _ = _configured_end(pmm_scope, frame, "J")
                if not _close(length, xyz_j[2] - xyz_i[2]):
                    raise ValueError("Wall-coupled frame object length differs from its analysis chain")
                wall_mesh = coupled_wall_mesh(mesh, inside, pi, pj, xyz_i, xyz_j)
                row.update(status=WALL_COUPLED, wall_mesh=wall_mesh, offset_length_m=cut_j[1] - cut_i[1],
                           end_cuts={"I": list(cut_i), "J": list(cut_j)},
                           reason="A standalone clear length requires a coupled wall-frame restraint model")
                continue
            if shell_kinds:
                raise ValueError(f"Column has intermediate shell contacts ({', '.join(shell_kinds)})")
            if inside.intersection(points):
                raise ValueError("Column has intermediate physical joints with unbound support")
            face_i, face_j = support_at(pi, lower=True), support_at(pj)
            if not face_j["beams"]:
                raise ValueError("Upper support requires a beam soffit")
            ln = face_j["soffit_z_m"] - face_i["top_z_m"]
            cut_i, length = _configured_end(pmm_scope, frame, "I")
            cut_j, _ = _configured_end(pmm_scope, frame, "J")
            row.update(faces={"I": face_i, "J": face_j}, physical_length_m=ln,
                       offset_length_m=cut_j[1] - cut_i[1], end_cuts={"I": list(cut_i), "J": list(cut_j)})
            if (ln <= 0 or not _close(length, xyz_j[2] - xyz_i[2])
                    or not _close(xyz_i[2] + cut_i[1], face_i["top_z_m"])
                    or not _close(xyz_i[2] + cut_j[1], face_j["soffit_z_m"])):
                raise ValueError("Physical support faces do not match both native force cuts")
            row["status"] = FACE_BASIS
        except (KeyError, TypeError, ValueError) as exc:
            row["reason"] = str(exc)
    return plan


def proven_clear_length_m(row: Mapping[str, Any] | None, uid: str):
    if row and row.get("member_id") == uid and row.get("status") == FACE_BASIS:
        length = row.get("physical_length_m")
        if type(length) in (int, float) and isfinite(length) and length > 0:
            return length
    return None
