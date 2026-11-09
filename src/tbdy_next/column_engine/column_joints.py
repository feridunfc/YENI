"""CE-07A: sealed native endpoint graph and conditional TBDY 7.5 references.

All derivation is in memory. Native frame endpoints are not physical joint
faces. Missing insertion points, area connectivity and selected beam cages
remain open. Neither native zero rebar overrides nor required-area summaries
are substituted for a physical beam capacity. No SCWB or joint Ve is issued.
"""
from collections import Counter, defaultdict
import math

from .column_stability import OPTIONAL_ERRORS
from .column_prechecks import _number
from .csi_geometry import AXIS_CONVENTION, local_dimensions
from .joint_kernel import centered_joint_limit, joint_transverse_reference, width_reference
from .native_archive import BankError, digest, finite, identity
from .observed_context import EXPECTED_FIELDS
from .ts500_column import positive

SCENARIO = "CENTERLINE_AS_SECTION_CENTER_SCENARIO"
GEOMETRY_TOL = 1e-8  # Direction cosines and nominal global coordinates in m; not code inequalities.
REFERENCE = "https://webdosya.csb.gov.tr/db/yapiisleri/icerikler/tbdy_2018-20210506174126.pdf"
OPEN_BASIS = ["INSERTION_POINTS_AND_PHYSICAL_JOINT_FACES_NOT_BOUND", "AREA_AND_SLAB_JOINT_PARTICIPATION_NOT_PROVEN",
    "END_RELEASES_AND_CONNECTION_RIGIDITY_NOT_APPROVED", "PROJECT_HIGH_DUCTILITY_APPLICABILITY_NOT_APPROVED",
    "ACTUAL_OR_SELECTED_BEAM_REINFORCEMENT_NOT_BOUND", "EARTHQUAKE_COMPATIBLE_CAPACITIES_NOT_BOUND",
    "JOINT_VKOL_SAME_DESIGN_STATE_NOT_BOUND", "LOWER_COLUMN_COMPLETE_TRANSVERSE_DEMAND_NOT_BOUND"]


def _get(archive, api, kind, name, fields, **kwargs):
    observed = archive.native(api,kind,name,fields,**kwargs)
    if observed is None: raise BankError("JOINT_NATIVE_NOT_OBSERVED:"+api+":"+str(name))
    return observed


def _names(archive, catalogs, group, api):
    values,proof = _get(archive,api,group,None,("NumberNames","MyName","pRetVal"),entity_key=None)
    names,number = values["MyName"],values["NumberNames"]
    declared = catalogs.get("names",{}).get(group)
    if (catalogs.get("catalog_complete",{}).get(group) is not True
            or type(number) is not int or not 0<number<=10000 or not isinstance(names,list)
            or len(names)!=number or len(set(identity(n,group) for n in names))!=number
            or not isinstance(declared,list) or len(declared)!=number or set(declared)!=set(names)):
        raise BankError("JOINT_COMPLETE_NATIVE_CATALOG_NOT_BOUND:"+group)
    return names,proof


def _dot(a,b): return sum(x*y for x,y in zip(a,b))
def _difference(a,b): return [x-y for x,y in zip(a,b)]
def _length(a): return math.sqrt(_dot(a,a))


def _parallel(a,b):
    return abs(abs(_dot(a,b))-1)<=GEOMETRY_TOL


def _geometry(frame,points,archive,sections):
    """Matrix columns are local axes in Global; bind e1 to native I→J."""
    name = frame["frame_id"]
    values,proof = _get(archive,"FrameObj.GetTransformationMatrix","frame",name,("Value","pRetVal"),
        expected_args=[name,[],True])
    matrix = values["Value"]
    if not isinstance(matrix,list) or len(matrix)!=9:
        raise BankError("JOINT_TRANSFORM_SHAPE_INVALID")
    matrix = [finite(v,"matrix") for v in matrix]
    axes = [[matrix[r*3+c] for r in range(3)] for c in range(3)]
    if any(abs(_dot(axes[i],axes[j])-(1 if i==j else 0))>GEOMETRY_TOL for i in range(3) for j in range(3)):
        raise BankError("JOINT_TRANSFORM_NOT_ORTHONORMAL")
    a,b,c = axes
    determinant = _dot(a,[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]])
    delta = _difference(points[frame["point_j"]]["xyz_m"],points[frame["point_i"]]["xyz_m"])
    length = positive(_length(delta),"frame_length")
    if abs(determinant-1)>GEOMETRY_TOL or any(abs(a[i]-delta[i]/length)>GEOMETRY_TOL for i in range(3)):
        raise BankError("JOINT_TRANSFORM_HANDEDNESS_OR_IJ_MISMATCH")
    assigned,assignment = _get(archive,"FrameObj.GetSection","frame",name,EXPECTED_FIELDS["FrameObj.GetSection"])
    section_name = identity(assigned["PropName"],"section")
    if section_name not in sections:
        rect,rectangle = _get(archive,"PropFrame.GetRectangle","frame_section",section_name,
            EXPECTED_FIELDS["PropFrame.GetRectangle"])
        d2,d3 = local_dimensions(float(_number(rect["T2"],"T2")*1000),float(_number(rect["T3"],"T3")*1000))
        sections[section_name] = {"section_name":section_name,"local2_extent_mm":d2,"local3_extent_mm":d3,
            "concrete_material":identity(rect["MatProp"],"material"),"source_call":rectangle}
    return {"axes_global":axes,"length_m":length,"section":sections[section_name],
        "source_calls":{"transformation":proof,"section_assignment":assignment}}


def _graph(archive,selected):
    catalogs = archive.json("catalogs.json")
    frame_names,frame_source = _names(archive,catalogs,"frames","FrameObj.GetNameList")
    point_names,point_source = _names(archive,catalogs,"points","PointObj.GetNameList")
    points,frames,adjacency = {},{},defaultdict(list)
    for name in point_names:
        coords,proof = _get(archive,"PointObj.GetCoordCartesian","point",name,("X","Y","Z","pRetVal"),
            expected_args=[name,0.0,0.0,0.0,"Global"])
        points[name] = {"point_id":name,"xyz_m":[finite(coords[k],k) for k in ("X","Y","Z")],"source_call":proof}
    for name in frame_names:
        ends,end_source = _get(archive,"FrameObj.GetPoints","frame",name,("Point1","Point2","pRetVal"))
        orient,orientation_source = _get(archive,"FrameObj.GetDesignOrientation","frame",name,("DesignOrientation","pRetVal"))
        i,j = identity(ends["Point1"],"I"),identity(ends["Point2"],"J")
        kind = orient["DesignOrientation"]
        if i==j or i not in points or j not in points or type(kind) is not int or kind not in (1,2,3,4):
            raise BankError("JOINT_FRAME_ENDPOINT_OR_ORIENTATION_INVALID:"+name)
        frames[name] = {"frame_id":name,"point_i":i,"point_j":j,"design_orientation":kind,
            "source_calls":{"endpoints":end_source,"orientation":orientation_source},"geometry":None,"geometry_reason":None}
        for point,end in ((i,"I"),(j,"J")): adjacency[point].append({"frame_id":name,"end":end,"design_orientation":kind})
    if any(name not in frames or frames[name]["design_orientation"]!=1 for name in selected):
        raise BankError("JOINT_SELECTED_COLUMN_POPULATION_MISMATCH")
    nodes = sorted({frames[name][end] for name in selected for end in ("point_i","point_j")})
    needed = {r["frame_id"] for node in nodes for r in adjacency[node] if r["design_orientation"] in (1,2)}
    sections = {}
    for name in sorted(needed):
        try: frames[name]["geometry"] = _geometry(frames[name],points,archive,sections)
        except OPTIONAL_ERRORS as exc: frames[name]["geometry_reason"] = str(exc)
    node_rows = []
    for name in nodes:
        xyz = points[name]["xyz_m"]
        coincident = [p for p in point_names if p!=name and _length(_difference(points[p]["xyz_m"],xyz))<=GEOMETRY_TOL]
        interior = []
        for frame in frames.values():
            if name in (frame["point_i"],frame["point_j"]): continue
            a,b = points[frame["point_i"]]["xyz_m"],points[frame["point_j"]]["xyz_m"]
            delta = _difference(b,a); norm2 = _dot(delta,delta)
            if norm2<=GEOMETRY_TOL**2: continue
            relative = _difference(xyz,a); t = _dot(relative,delta)/norm2
            if 0<t<1 and _length([relative[k]-t*delta[k] for k in range(3)])<=GEOMETRY_TOL:
                interior.append(frame["frame_id"])
        node_rows.append({"point_id":name,"xyz_m":xyz,"incident_frames":adjacency[name],
            "coincident_other_point_ids":coincident,"possible_interior_frame_connections":interior})
    counts = Counter(f["design_orientation"] for f in frames.values())
    return {"status":"NATIVE_ENDPOINT_GRAPH_BOUND","reason":None,"frame_count":len(frames),"point_count":len(points),
        "native_column_count":counts[1],"native_beam_count":counts[2],"other_frame_count":counts[3]+counts[4],
        "selected_columns_cover_native_columns":set(selected)=={n for n,f in frames.items() if f["design_orientation"]==1},
        "source_calls":{"frames":frame_source,"points":point_source},
        "frames":list(frames.values()),"points":list(points.values()),"nodes":node_rows},frames,points


def _vertical(frame):
    if frame["geometry"] is None: raise BankError(frame["geometry_reason"] or "JOINT_FRAME_GEOMETRY_NOT_BOUND")
    axes = frame["geometry"]["axes_global"]
    if not _parallel(axes[0],[0,0,1]) or any(abs(a[2])>GEOMETRY_TOL for a in axes[1:]):
        raise BankError("JOINT_VERTICAL_COLUMN_SCENARIO_NOT_BOUND")
    return axes


def _beam_faces(node,column,frames,points):
    axes = _vertical(column)
    sec = column["geometry"]["section"]
    faces = {"2+":None,"2-":None,"3+":None,"3-":None}
    for incident in node["incident_frames"]:
        frame = frames[incident["frame_id"]]
        if frame["design_orientation"]!=2: continue
        geom = frame["geometry"]
        if geom is None: raise BankError(frame["geometry_reason"] or "JOINT_BEAM_GEOMETRY_NOT_BOUND")
        other = frame["point_j"] if frame["point_i"]==node["point_id"] else frame["point_i"]
        direction = _difference(points[other]["xyz_m"],node["xyz_m"])
        direction = [v/positive(_length(direction),"beam_length") for v in direction]
        matches = [i for i in (1,2) if _parallel(direction,axes[i])]
        if len(matches)!=1 or abs(direction[2])>GEOMETRY_TOL:
            raise BankError("JOINT_ORTHOGONAL_HORIZONTAL_BEAM_SCENARIO_NOT_BOUND")
        i = matches[0]; face = str(i+1)+("+" if _dot(direction,axes[i])>0 else "-")
        if faces[face] is not None: raise BankError("JOINT_MULTIPLE_BEAMS_ON_ONE_FACE")
        perp = axes[3-i]
        beam_axes = geom["axes_global"]
        width_axes = [j for j in (1,2) if _parallel(beam_axes[j],perp)]
        if len(width_axes)!=1:
            raise BankError("JOINT_BEAM_SECTION_ROLL_NOT_ORTHOGONAL")
        bs = geom["section"]
        # The orthogonal scenario binds a physical dimension directly. Do not
        # let cosine round-off change the inclusive 3/4 dimensional boundary.
        bw = bs["local2_extent_mm"] if width_axes[0]==1 else bs["local3_extent_mm"]
        width = sec["local3_extent_mm"] if i==1 else sec["local2_extent_mm"]
        faces[face] = {"frame_id":frame["frame_id"],"native_end":incident["end"],"face":face,
            "beam_width_mm":bw,"column_transverse_width_mm":width,"width_ratio":bw/width,
            "width_reference_met":width_reference(bw,width),"beam_section_name":bs["section_name"]}
    return faces


def _tie_rows(node,column,frames,points,transverse,enclosure):
    lower = []
    for incident in node["incident_frames"]:
        frame = frames[incident["frame_id"]]
        if frame["design_orientation"]!=1: continue
        _vertical(frame)
        other = frame["point_j"] if frame["point_i"]==node["point_id"] else frame["point_i"]
        if points[other]["xyz_m"][2]<node["xyz_m"][2]-GEOMETRY_TOL: lower.append(frame)
    if len(lower)!=1: raise BankError("JOINT_UNIQUE_LOWER_COLUMN_NOT_BOUND")
    lower = lower[0]
    member = next((m for m in transverse["members"] if m["member_id"]==lower["frame_id"]),None)
    proposals = [p for p in transverse["proposals"] if member and p["profile_id"]==member["profile_id"]]
    if not member or member["status"]!="TRANSVERSE_MATERIAL_BOUND" or len(proposals)!=3:
        raise BankError("JOINT_LOWER_TRANSVERSE_SOURCE_NOT_BOUND")
    rows = []
    for axis in (2,3):
        direction = column["geometry"]["axes_global"][axis-1]
        matches = [a for a in (2,3) if _parallel(direction,lower["geometry"]["axes_global"][a-1])]
        if len(matches)!=1: raise BankError("JOINT_LOWER_AXIS_MAPPING_NOT_BOUND")
        lower_axis = "V"+str(matches[0])
        for proposal in proposals:
            if proposal["status"]!="PROPOSED_TRANSVERSE_REFERENCES_CALCULATED":
                raise BankError("JOINT_LOWER_CONFINEMENT_REFERENCE_NOT_BOUND")
            ref,layout = proposal["axes"][lower_axis],proposal["layout"]
            branches = {branch:joint_transverse_reference(lower_required_ash_mm2=ref["confinement"][branch+"_axial_required_ash_mm2"],
                lower_spacing_mm=layout["spacing_mm"],proposed_ash_mm2=ref["ash_mm2"],
                joint_spacing_mm=layout["spacing_mm"],tie_diameter_mm=layout["tie_diameter_mm"],enclosure=enclosure)
                for branch in ("high","low")}
            rows.append({"axis":"V"+str(axis),"lower_column_id":lower["frame_id"],"lower_axis":lower_axis,
                "candidate_label":proposal["candidate_label"],"candidate_id":proposal["candidate_id"],
                "source_transverse_id":proposal["transverse_id"],"branches":branches,"axial_branch_selected":None,
                "basis":"EQ7_1_CONFINEMENT_BASELINE_ONLY","actual_joint_minimum_proven":False})
    return lower["frame_id"],rows


def build_column_joints(bank,chain,cages,transverse,archive):
    if (cages.get("axis_convention")!=AXIS_CONVENTION or transverse.get("axis_convention")!=AXIS_CONVENTION
            or bank["source_archive_sha256"]!=archive.sha256 or chain["source_archive_sha256"]!=archive.sha256
            or chain["source_bank_result_sha256"]!=bank["result_sha256"]
            or cages["source_archive_sha256"]!=archive.sha256 or transverse["source_archive_sha256"]!=archive.sha256
            or cages["source_demand_result_sha256"]!=chain["result_sha256"]
            or transverse["source_demand_result_sha256"]!=chain["result_sha256"]
            or transverse["source_cages_result_sha256"]!=cages["result_sha256"]
            or bank.get("run_id")!=chain["source_run_id"] or cages["source_run_id"]!=chain["source_run_id"]
            or transverse["source_run_id"]!=chain["source_run_id"]):
        raise BankError("JOINT_SOURCE_BINDING_MISMATCH")
    selected = [m["frame_name"] for m in bank["members"]]
    if len(set(selected))!=len(selected): raise BankError("JOINT_DUPLICATE_SELECTED_MEMBER")
    graph = {"status":"BLOCKED_INPUTS","reason":None,"frame_count":0,"point_count":0,"native_column_count":0,
        "native_beam_count":0,"other_frame_count":0,"selected_columns_cover_native_columns":False,
        "source_calls":{},"frames":[],"points":[],"nodes":[]}
    frames,points = {},{}
    try: graph,frames,points = _graph(archive,selected)
    except OPTIONAL_ERRORS as exc: graph["reason"] = str(exc)
    nodes = {r["point_id"]:r for r in graph["nodes"]}
    profiles = {p["profile_id"]:p for p in cages["profiles"]}
    members = {m["member_id"]:m for m in cages["members"]}
    rows = []
    for member in bank["members"]:
        name = member["frame_name"]
        for end in ("I","J"):
            row = {"member_id":name,"end":end,"point_id":None,
                "story":((member.get("context") or {}).get("frame") or {}).get("story_label"),
                "status":"BLOCKED_INPUTS","reason":graph["reason"],"scenario":SCENARIO,
                "geometry_column_id":name,"section_name":None,"fck_mpa":None,
                "enclosure_scenario":None,"faces":{},"missing_faces":[],"narrow_faces":[],"axes":[],
                "lower_column_id":None,"tie_status":"BLOCKED_INPUTS","tie_reason":None,"tie_references":[],
                "joint_ve_kn":None,"scwb_ratio":None,"physical_geometry_proven":False,"final_design_eligible":False}
            if name in frames:
                try:
                    column = frames[name]; node = nodes[column["point_"+end.lower()]]
                    row["point_id"] = node["point_id"]
                    if node["coincident_other_point_ids"]: raise BankError("JOINT_COINCIDENT_DISTINCT_POINT_IDS")
                    if node["possible_interior_frame_connections"]: raise BankError("JOINT_INTERIOR_FRAME_CONNECTION_NOT_BOUND")
                    if any(r["design_orientation"] not in (1,2) for r in node["incident_frames"]):
                        raise BankError("JOINT_OTHER_INCIDENT_FRAME_NOT_CLASSIFIED")
                    faces = _beam_faces(node,column,frames,points)
                    row.update(faces=faces,missing_faces=[f for f,v in faces.items() if v is None],
                        narrow_faces=[f for f,v in faces.items() if v and not v["width_reference_met"]])
                    if all(v is None for v in faces.values()):
                        row.update(status="NO_RECORDED_BEAM_AT_NODE",reason=None,tie_reason="NO_RECORDED_BEAM_AT_NODE")
                    else:
                        profile = profiles.get((members.get(name) or {}).get("profile_id"))
                        sec = column["geometry"]["section"]
                        if (not profile or profile["section_name"]!=sec["section_name"]
                                or local_dimensions(profile["t2_mm"],profile["t3_mm"])!=(sec["local2_extent_mm"],sec["local3_extent_mm"])):
                            raise BankError("JOINT_COLUMN_PROFILE_NOT_BOUND")
                        enclosure = "ENCLOSED" if not row["missing_faces"] and not row["narrow_faces"] else "UNENCLOSED"
                        fc = profile["material"]["fck"]
                        row.update(status="JOINT_GEOMETRIC_REFERENCES_CALCULATED",reason=None,enclosure_scenario=enclosure,
                            section_name=sec["section_name"],fck_mpa=fc)
                        for axis,b,h in ((2,sec["local3_extent_mm"],sec["local2_extent_mm"]),
                                         (3,sec["local2_extent_mm"],sec["local3_extent_mm"])):
                            widths = [v["beam_width_mm"] for f,v in faces.items() if f[0]==str(axis) and v]
                            row["axes"].append({"axis":"V"+str(axis),"status":"GEOMETRIC_REFERENCE_ONLY" if widths
                                else "NO_RECORDED_BEAM_IN_DIRECTION","calculation":centered_joint_limit(column_width_mm=b,
                                    column_depth_mm=h,beam_widths_mm=widths,fck_mpa=fc,enclosure=enclosure) if widths else None})
                        try:
                            lower,ties = _tie_rows(node,column,frames,points,transverse,enclosure)
                            row.update(lower_column_id=lower,tie_references=ties,tie_status="EQ71_BASELINE_REFERENCES_CALCULATED")
                        except OPTIONAL_ERRORS as exc: row["tie_reason"] = str(exc)
                except OPTIONAL_ERRORS as exc: row.update(status="BLOCKED_INPUTS",reason=str(exc),enclosure_scenario=None,axes=[])
            if row["tie_status"]=="BLOCKED_INPUTS" and row["tie_reason"] is None:
                row["tie_reason"] = row["reason"] or row["status"]
            row["joint_end_id"] = "JOINT-END-"+digest({"source":archive.sha256,"member":name,"end":end})[:24]
            rows.append(row)
    result = {"schema":"tbdy.next.column-joint-references.v1","axis_convention":AXIS_CONVENTION,
        "source_run_id":chain["source_run_id"],"source_archive_sha256":archive.sha256,
        "source_bank_result_sha256":bank["result_sha256"],"source_demand_result_sha256":chain["result_sha256"],
        "source_cages_result_sha256":cages["result_sha256"],"source_transverse_result_sha256":transverse["result_sha256"],
        "scenario":SCENARIO,"graph":graph,"selected_member_count":len(selected),"column_end_count":len(rows),
        "joint_node_count":len(nodes),"nodes_with_beams":sum(any(i["design_orientation"]==2 for i in n["incident_frames"]) for n in nodes.values()),
        "status_counts":dict(Counter(r["status"] for r in rows)),
        "enclosure_counts":dict(Counter(r["enclosure_scenario"] for r in rows if r["enclosure_scenario"])),
        "geometric_limit_count":sum(a["calculation"] is not None for r in rows for a in r["axes"]),
        "tie_reference_count":sum(len(r["tie_references"]) for r in rows),"rows":rows,
        "geometry_tolerances":{"direction_cosine":GEOMETRY_TOL,"global_distance_m":GEOMETRY_TOL},
        "references":{"tbdy_7_5":REFERENCE},"open_basis":list(OPEN_BASIS),
        "physical_joint_population_proven":False,"physical_geometry_proven":False,
        "scwb_status":"NOT_PROVEN","ve_status":"NOT_PROVEN","selected_design":None,
        "design_demand_authority":"DENIED","formal_compliance":"NOT_PROVEN","engineering_release":"NOT_READY"}
    result["result_sha256"] = digest(result)
    return result


def joint_tie_rows(joints,member_id=None):
    rows = []
    for end in joints["rows"]:
        if member_id is not None and end["member_id"]!=member_id: continue
        base = {k:end[k] for k in ("joint_end_id","member_id","end","point_id","geometry_column_id",
            "enclosure_scenario","tie_status","tie_reason","scenario")}
        rows.extend({**base,**r} for r in end["tie_references"] or [{"axis":None,"lower_column_id":None,
            "candidate_label":None,"branches":{},"basis":"EQ7_1_CONFINEMENT_BASELINE_ONLY","actual_joint_minimum_proven":False}])
    return rows


def joint_summaries(joints):
    return [{**{k:r[k] for k in ("member_id","end","point_id","status","reason","enclosure_scenario",
                "missing_faces","narrow_faces","lower_column_id","tie_status","tie_reason")},
        "beam_ids":[v["frame_id"] for v in r["faces"].values() if v],
        **{"limit_"+a["axis"]+"_kn":a["calculation"]["geometric_limit_kn"] if a["calculation"] else None for a in r["axes"]},
        "tie_reference_count":len(r["tie_references"])} for r in joints["rows"]]


def joint_tie_summaries(joints):
    return [{**{k:r[k] for k in ("member_id","end","point_id","lower_column_id","axis","candidate_label","tie_reason")},
        "lower_axis":r.get("lower_axis"),
        **{field:r["branches"].get(branch,{}).get(key) for field,branch,key in (
            ("required_high_mm2","high","required_ash_at_joint_spacing_mm2"),
            ("required_low_mm2","low","required_ash_at_joint_spacing_mm2"),
            ("proposed_ash_mm2","high","proposed_ash_mm2"),("spacing_mm","high","joint_spacing_mm"))}}
        for r in joint_tie_rows(joints)]
