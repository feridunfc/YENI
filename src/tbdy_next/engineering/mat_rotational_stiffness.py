"""Directional rotational restraint of a monolithic column on a linear Winkler mat."""
from collections import Counter
from math import fsum, isclose, isfinite
import re

from ..etabs_geometry import AREA_ELEMENTS, SLAB_PROPERTIES
from .analysis_archive import _archive_bytes
from .column_clear_length import FACE_BASIS, _records
from .column_pmm_section import MECHANICAL, _named_row, _rows


def _positive(value):
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError("Positive mat stiffness or dimension required")
    return value


def strip_rotational_stiffness(length, width, thickness, elastic, shear, bending_factor, shear_factor, subgrade, *, footprint_half=0.):
    """Lower bound in kN m/rad for a free-ended thick strip under a unit end moment.

    The statically admissible bilateral soil pressure is q(x)=12(x-L/2)/L³
    per unit couple (line reaction). It has zero resultant and unit first moment.
    The integrals of M², V² and q² are 13L/35, 6/(5L) and 12/L³.
    Complementary energy gives an upper flexibility, including transverse shear.
    """
    l, b, h, e, g, m, v, ks = map(_positive, (length, width, thickness, elastic, shear,
                                             bending_factor, shear_factor, subgrade))
    ei = e*m*b*h**3/12
    ga = (5/6)*g*v*b*h
    flexibility = 13*l/(35*ei) + 6/(5*l*ga) + 12/(l**3*ks*b)
    if footprint_half:
        # Transfer a self-balanced normal traction couple over each physical half-footprint.
        # Only the affine vertical displacement of the bonded frame section is prescribed.
        # Double the core compliance so orthogonal moment fields can share this area
        # by Cauchy-Schwarz. Exterior strips and their soil reactions are disjoint.
        a = _positive(footprint_half)
        flexibility += 2*(13*a/(35*ei) + 6/(5*a*ga))
    return 1/flexibility


def _mat_rect(elements, coordinates):
    """A complete flat, rectangular, connected native mesh, including its perimeter."""
    edges = Counter()
    areas = []
    points = {}
    element_ids = set()
    for elm in elements:
        nodes = [elm.get("ElmJt"+str(n)) for n in range(1,5)]
        nodes = [node for node in nodes if node not in (None, "", "None")]
        eid = elm["ElmName"]
        if len(nodes) < 3 or len(nodes) != len(set(nodes)) or eid in element_ids:
            raise ValueError("Invalid mat element topology")
        element_ids.add(eid)
        xyz = [coordinates[node] for node in nodes]
        points.update(zip(nodes, xyz))
        pairs = list(zip(nodes, nodes[1:]+nodes[:1]))
        edges.update(pairs)
        x, y, _ = xyz[0]
        areas.append(_positive(fsum((points[a][0]-x)*(points[b][1]-y)-(points[b][0]-x)*(points[a][1]-y)
                                    for a,b in pairs)/2))
    limits = [(min(p[i] for p in points.values()), max(p[i] for p in points.values())) for i in range(3)]
    if limits[2][1] != limits[2][0] or not isclose(fsum(areas),
            (limits[0][1]-limits[0][0])*(limits[1][1]-limits[1][0]), rel_tol=1e-8, abs_tol=1e-8):
        raise ValueError("Incomplete or non-horizontal rectangular mat")
    for (a,b), count in edges.items():
        if count != 1 or not edges[b,a] and not any(
                all(abs(points[n][i]-edge)<1e-7 for n in (a,b)) for i in (0,1) for edge in limits[i]):
            raise ValueError("Hole or nonmatching edge in mat")
    return limits, element_ids


def _mat_sources(source, slabs):
    tables = source["column_axial"]["r10_source"]["table_reads"]
    native = source["column_axial"]["pmm_section_source"]["table_reads"]
    materials = _rows(native, MECHANICAL, {"Material"}, {"E1":"kN/m2","G12":"kN/m2"})
    props = _rows(tables, SLAB_PROPERTIES, {"Name","Material","ModelType","PropType","m11Mod","m22Mod",
                                          "m12Mod","v13Mod","v23Mod"}, {"Thickness":"m"})
    joints = _records(tables,"Objects and Elements - Joints","ElmName GlobalX GlobalY GlobalZ",("GlobalX","GlobalY","GlobalZ"))
    coordinates = {j["ElmName"]:tuple(float(j[k]) for k in ("GlobalX","GlobalY","GlobalZ")) for j in joints}
    if len(coordinates) != len(joints):
        raise ValueError("Mat joint coordinates are ambiguous")
    elems = _records(tables,AREA_ELEMENTS,"ElmName ObjName ObjType Story ObjLabel ElmJt1 ElmJt2 ElmJt3")
    deck = _archive_bytes(source["analysis_archive"]["model_export_base64"],2_000_000).decode("latin-1")
    if not re.search(r'^\s*UNITS\s+"KN"\s+"M"\s+"C"\s*$',deck,re.M):
        raise ValueError("Spring export units are unbound")
    exports = [line.strip() for line in deck.splitlines()]
    out = {}
    for uid, slab in slabs.items():
        try:
            mesh = [e for e in elems if e["ObjName"]==uid and e["ObjType"]=="Floor"]
            identities = {(e["Story"],e["ObjLabel"]) for e in mesh}
            (story,label), = identities
            if label != slab["label"]:
                continue
            pattern = (r'AREAASSIGN\s+"'+re.escape(label)+r'"\s+"'+re.escape(story)+
                       r'"\s+SECTION\s+"'+re.escape(slab["section"])+r'"\s+SPRINGPROP\s+"([^"]+)"'
                       r'\s+ADDRESTRAINT\s+"No"\s+CARDINALPOINT\s+"TOP"\s+TRANSFORMSTIFFNESSFOROFFSETS\s+"No"')
            definitions = [line for line in exports if re.match(r'AREAASSIGN\s+"'+re.escape(label)+r'"\s+"'+re.escape(story)+r'"',line)]
            assignment, = definitions
            match = re.fullmatch(pattern,assignment)
            if match is None:
                continue
            name = match[1]
            spring, = [line for line in exports if re.match(r'AREASPRING\s+"'+re.escape(name)+r'"',line)]
            signed = re.fullmatch(r'AREASPRING\s+"[^"]+"\s+U3\s+([.\deE+\-]+)',spring)
            prop = _named_row(props,"Name",slab["section"],SLAB_PROPERTIES)
            if signed is None or prop["PropType"]!="Mat" or prop["ModelType"]!="Shell-Thick":
                continue
            mat = _named_row(materials,"Material",prop["Material"],MECHANICAL)
            bounds, ids = _mat_rect(mesh, coordinates)
            h = _positive(prop["Thickness"])
            if not isclose(h,slab["thickness_m"],abs_tol=1e-8):
                continue
            out[uid] = {"bounds":bounds, "ids":ids, "section":prop["Name"], "material":prop["Material"],
                        "spring":name, "subgrade":_positive(signed[1]), "thickness":h,
                        "elastic":_positive(mat["E1"]), "shear":_positive(mat["G12"]),
                        "bending_factor":min(_positive(prop[k]) for k in ("m11Mod","m22Mod","m12Mod")),
                        "shear_factor":min(_positive(prop[k]) for k in ("v13Mod","v23Mod"))}
        except (KeyError, ValueError, TypeError, ArithmeticError):
            continue
    # Read the native release assignments as well as the exact source line sections.
    lines = {}
    for line in exports:
        match = re.match(r'LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+(.*)$',line)
        if match:
            lines.setdefault((match[1],match[2]),[]).append(match[3])
    release_table = tables["Frame Assignments - Releases and Partial Fixity"]
    if release_table.get("row_count") != len(release_table["rows"]):
        raise ValueError("Frame release population mismatch")
    released = {r["UniqueName"] for r in release_table["rows"]}
    return out, materials, lines, released


def mat_rotation_bounds(source, physical, horizontal, frames, points, lengths, adjacency):
    """Column-footprint strip model. Its stiffness is never credited to the storey Euler sum."""
    contacts = {uid:row["mat_contact"] for uid,row in physical.items() if row.get("status")==FACE_BASIS and row.get("mat_contact")
                and horizontal.get(uid,{}).get("status")=="MAT_HORIZONTAL_BOUNDARY_VERIFIED"}
    slabs = {s["floor_id"]:s for uid in contacts for s in physical[uid]["faces"]["I"]["slabs"] if s["type"]=="Mat"}
    if not slabs:
        return {}
    try:
        mats, materials, lines, released = _mat_sources(source, slabs)
    except (KeyError, ValueError, TypeError, ArithmeticError):
        return {}
    results = {}
    for uid,contact in contacts.items():
        try:
            floor, = contact["mat_analysis_elements"]
            mat = mats[floor]
            foot = contact["base_joint_id"]
            frame = frames[uid]
            if (not set(contact["mat_analysis_elements"][floor]) <= mat["ids"]
                    or not contact["mat_analysis_elements"][floor] or frame["point_i"]!=foot
                    or len(adjacency[foot])!=1 or adjacency[foot][0]["frame_id"]!=uid
                    or uid in released):
                continue
            assignment, = lines[frame["label"],frame["story"]]
            if (not assignment.startswith('SECTION "'+frame["section_name"]+'"') or
                    any(flag in assignment for flag in ("RELEASE","PARTIAL","SPRING","OFFSET"))):
                continue
            x = points[foot]
            ec = _positive(_named_row(materials,"Material",frame["material_name"],MECHANICAL)["E1"])
            size = (frame["dims"].local2_extent_mm/1000, frame["dims"].local3_extent_mm/1000)
            basepoints = [points[f["point_i"]] for f in frames.values() if f["type"]=="Column"
                          and abs(points[f["point_i"]][2]-x[2])<1e-7 and f["frame_id"]!=uid]
            for iaxis,axis in enumerate(("M2","M3")):
                vector = frame["axes_global"][2-iaxis]
                direction = next(i for i in (0,1) if abs(abs(vector[i])-1)<1e-8)
                cross = 1-direction
                width,depth = size[iaxis], size[1-iaxis]
                xl,xh = mat["bounds"][direction]
                yl,yh = mat["bounds"][cross]
                if x[cross]-width/2 < yl or x[cross]+width/2 > yh:
                    continue
                spans = []
                for sign, edge in ((-1,xl),(1,xh)):
                    neighbours = [sign*(p[direction]-x[direction])/2 for p in basepoints
                                  if abs(p[cross]-x[cross])<width/2 and sign*(p[direction]-x[direction])>1e-7]
                    spans.append(min([sign*(edge-x[direction]), *neighbours])-depth/2)
                terms = [strip_rotational_stiffness(l,width,mat["thickness"],mat["elastic"],mat["shear"],
                                mat["bending_factor"],mat["shear_factor"],mat["subgrade"],footprint_half=depth/2) for l in spans]
                column = ec*width*depth**3/(12*_positive(lengths[uid]))
                # A fixed far end gives 4EI/L. Using Ktheta/4 for the denominator
                # upper-bounds the end-flexibility ratio of this member model.
                results.setdefault(uid,{})[axis] = {
                    "method":"MONOLITHIC_FOOTPRINT_FREE_STRIPS_LINEAR_WINKLER", "joint":foot, "mat":floor,
                    "section":mat["section"],"material":mat["material"],"thickness_m":mat["thickness"],
                    "spring_property":mat["spring"],"subgrade_kn_m3":mat["subgrade"],"width_m":width,
                    "axis":"XY"[direction],"lengths_m":spans,"elastic_kn_m2":mat["elastic"],"shear_kn_m2":mat["shear"],
                    "bending_modifier":mat["bending_factor"],"shear_modifier":mat["shear_factor"],
                    "column_ei_over_l_knm":column, "leg_stiffness_knm_rad":terms, "k_theta_min_knm_rad":fsum(terms),
                    "alpha_i_upper":4*column/fsum(terms), "footprint_model":"BONDED_FRAME_PLANE_SECTION_NORMAL_TRACTION_COUPLE",
                    "half_footprint_m":depth/2, "biaxial_core_compliance_factor":2.0,
                    "source_edb_sha256":source["analysis_archive"]["observed_edb_sha256"], "storey_euler_credit":False}
        except (KeyError, ValueError, TypeError, AttributeError, StopIteration, ArithmeticError):
            continue
    return results
