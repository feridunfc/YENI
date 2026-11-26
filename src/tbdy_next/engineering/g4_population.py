"""Freeze the physical grain of every building check before evaluating the first calculation."""
from collections import defaultdict
from itertools import product
from math import hypot

from ..earthquake_combinations import _graph_rows
from .design_scenario import _digest
from .g1_contract import require
from .mixed_demands import native_graph
from .pier_seismic_shear import wall_load_scope


FAMILIES = (
    ("Modal participating mass X/Y", "axis"),
    ("column_rect_min", "columns"),
    ("beam_width_min", "beams"),
    ("beam_depth_min", "beams"),
    ("beam_depth_width", "beams"),
    ("concrete_fck_25", "materials"),
    ("a1_torsion_x", "stories"),
    ("a1_torsion_y", "stories"),
    ("BASIS_PROBE", "basis_tables"),
    ("BASIS_LINKAGE", "basis_links"),
    ("DIAPHRAGM_PROBE", "diaphragm_probes"),
    ("DIAPHRAGM_LINKAGE", "diaphragm_links"),
    ("SPECTRUM_RECONSTRUCTION", "mode_cases"),
    ("BASE_SHEAR_SCREENING", "global"),
    ("earthquake_100_30", "combos"),
    ("earthquake_direction_pairs", "contexts"),
    ("Occupied-storey drift", "drift"),
    ("Global second-order precheck", "story_axes"),
    ("B1 weak-storey comparisons", "adjacent"),
    ("B2 soft-storey comparisons", "story_axes"),
    ("Wall geometry", "walls"),
    ("Column axial compression by assigned combination", "column_cases"),
    ("Selected beam flexure and capacity shear", "beams"),
    ("End-to-end column design", "columns"),
    ("Native assigned pier forces", "pier_faces"),
    ("Wall compression on concrete clear of columns", "pier_faces"),
    ("Wall web shear with two proposed Ø12/200 curtains", "pier_faces"),
    ("Rough construction plane with 0.75% proposed crossing steel", "pier_faces"),
    ("Directional pier bending at bottom-cut centroids", "pier_axes"),
    ("Wall panels with proposed reinforcement schedules", "walls"),
    ("Column confinement schedules", "columns"),
    ("Beam confinement schedules on model cuts", "beams"),
    ("Beam confinement ends at a connected column face", "beam_ends"),
    ("Wall objects with two calculated pier boundary zones", "walls"),
    ("Wall objects with proposed boundary hoops and crossties", "walls"),
    ("Pier gravity PMM and in-plane shear on rectangular stacks", "gravity_rect"),
    ("Wall in-plane seismic shear upper bounds", "seismic_rect"),
    ("Assigned pier axial compression against 0.35 fck Ac", "seismic_rect"),
    ("Pier design moment diagrams under both base scenarios", "seismic_rect"),
    ("Heightwise in-plane pier shear", "seismic_rect"),
    ("Pier PMM over the full assigned axial and moment intervals", "seismic_rect"),
    ("Pier construction joint in-plane shear friction", "seismic_rect_storeys"),
    ("Rectangular wall dimensions and two-curtain web crossties", "rect"),
    ("Strong-axis wall and selected beam end moment comparison", "seismic_rect_storeys"),
    ("Conditional seismic wall design on assigned physical cuts", "seismic_rect"),
    ("Full project-qualified seismic pier design on rectangular stacks", "seismic_rect"),
    ("Multi-panel pier net-web P–M checks at native cuts", "multi_cuts"),
    ("Basement combined membrane, two-way bending and shear by panel and combination", "panel_cases"),
    ("Multi-panel walls with a proposed web schedule", "basement"),
    ("Basement bar development and joint clearance at column and wall supports", "wall_ends"),
    ("Basement edge shear friction and normal tension", "wall_end_cases"),
    ("Project-approved wall reinforcement", "walls"),
    ("Diaphragm collectors and chords", "diaphragms"),
    ("Slab flexure and punching", "slabs"),
    ("Mat contact and reinforced concrete design", "mats"),
    ("Beam torsion and serviceability", "beams"),
    ("Coupling-beam design", "beams"),
)
BASIS_COMPONENTS = ("SEISMIC_MASS_RECONCILIATION","RESPONSE_SPECTRUM_CASE_BINDINGS",
                    "PHYSICAL_STORY_GEOMETRY","SPECTRUM_MODAL_OUTPUT")
DIAPHRAGM_COMPONENTS = ("DIAPHRAGM_DEFINITIONS","AREA_DIAPHRAGM_ASSIGNMENTS","JOINT_DIAPHRAGM_ASSIGNMENTS",
                        "SPECTRUM_MODAL_RSXY_SOURCE")
SOURCE_ERRORS = (ValueError,KeyError,IndexError,TypeError,ArithmeticError)


def identities(rows, key):
    ids = [row[key] for row in rows]
    require(all(isinstance(x,str) and x for x in ids) and len(ids)==len(set(ids)),"G4_DUPLICATE_OR_EMPTY_NATIVE_ID")
    return sorted(ids)


def _coupling_roles(beams, walls, points):
    # Use both sides of each floor. A wall can meet a beam at an interior edge point.
    edges = []
    for w in walls:
        coords = [points[w["UniquePt"+str(i)]] for i in range(1,5)]
        for a,b in zip(coords,coords[1:]+coords[:1]):
            if abs(a[2]-b[2])<1.e-7 and hypot(a[0]-b[0],a[1]-b[1])>1.e-7:
                edges.append((w["UniqueName"],a,b))
    roles={}
    for beam in beams:
        a,b=(points[beam[k]] for k in ("UniquePtI","UniquePtJ"))
        ends=[]
        for p in (a,b):
            hits=set()
            for uid,start,stop in edges:
                dx,dy=stop[0]-start[0],stop[1]-start[1]
                length=hypot(dx,dy)
                along=((p[0]-start[0])*dx+(p[1]-start[1])*dy)/length
                normal=abs((p[0]-start[0])*dy-(p[1]-start[1])*dx)/length
                if abs(p[2]-start[2])<1.e-6 and -1.e-6<=along<=length+1.e-6 and normal<=1.e-6:
                    hits.add(uid)
            ends.append(sorted(hits))
        # A beam with two wall endpoints needs an opening/clear-span and system-role decision.
        distinct = any(left!=right for left in ends[0] for right in ends[1])
        roles[beam["UniqueName"]]={"ends":ends,"status":"WALL_TO_WALL_ROLE_REVIEW" if distinct
            else "NO_TWO_DIRECT_WALL_SUPPORTS","points":[beam["UniquePtI"],beam["UniquePtJ"]]}
    return roles


def _freeze(source):
    geometry=source["geometry_capture"]["tables"]
    table=source["vs06_b1_geometry_source"]["table_reads"]
    def rows(record):
        require(record["status"]=="CAPTURED" and len(record["rows"])==record["row_count"],"G4_INCOMPLETE_SOURCE_TABLE")
        return record["rows"]
    cols,beams=(rows(geometry[k+"_CONNECTIVITY"]) for k in ("COLUMN","BEAM"))
    wrows=rows(table["Wall Object Connectivity"])
    points={r["UniqueName"]:tuple(float(r[a]) for a in "XYZ") for r in rows(table["Point Object Connectivity"])}
    axes=("X","Y")
    stories=sorted({r["Story"] for r in cols+beams+wrows},key=lambda s:max(p[2] for r in cols if r["Story"]==s
                     for p in (points[r["UniquePtI"]],points[r["UniquePtJ"]])))
    slabs=rows(source["column_axial"]["r10_source"]["table_reads"]["Slab Property Definitions"])
    props={r["Name"]:r["PropType"] for r in slabs}
    area=rows(table["Area Assignments - Section Properties"])
    wall_ids=identities(wrows,"UniqueName")
    require(set(wall_ids)=={r["UniqueName"] for r in area if r["PropType"]=="Wall"},"G4_WALL_PHYSICAL_INVENTORY")
    assignments=source["pier_section_forces"]["read"]["tables"]["table_reads"]["Area Assignments - Pier Labels"]["rows"]
    identities(assignments,"UniqueName")
    groups=defaultdict(list)
    for r in assignments:
        if r["PierName"] not in ("","None"):
            require(r["UniqueName"] in wall_ids,"G4_PIER_ASSIGNMENT_UNKNOWN_AREA")
            groups[r["PierName"],r["Story"]].append(r["UniqueName"])
    singles=[]; multiples=[]
    for k,ids in groups.items():
        # A single rectangular area throughout the labelled stack is a separate design family.
        if all(len(v)==1 for (pier,_),v in groups.items() if pier==k[0]):
            singles.extend(ids)
        else:
            multiples.append(k)
    basement=[uid for key in multiples for uid in groups[key]]
    scope=wall_load_scope(source)
    gravity=sorted(scope["native_static"])
    spectral=sorted(scope["native_seismic"])
    cases=gravity+spectral
    require(cases and not set(gravity)&set(spectral),"G4_WALL_ASSIGNMENTS_REQUIRED")
    tables,native,graph=native_graph(source)
    x,y=(source["next_capture"][key] for key in ("x_case","y_case"))
    from ..earthquake_combinations import _combo_source
    parsed=_combo_source(tables,native,include_graph=True,require_key=True)
    combo_rows=_graph_rows(graph,parsed,x,y)
    contexts=sorted({r["context_sha256"] for r in combo_rows if r.get("context_sha256")})
    require(not any(r["status"]=="NOT_PROVEN" for r in combo_rows),"G4_COMBINATION_CONTEXT_UNRESOLVED")
    col_ids,beam_ids=identities(cols,"UniqueName"),identities(beams,"UniqueName")
    frame_cases=sorted({name for k in ("gravity","ductile") for name in source["analysis_basis"]["design_groups"][k]})
    diaphragm=source["vs04_diaphragm_probe"]["diaphragm_tables"]
    defs={r["Name"] for r in rows(diaphragm["Diaphragm Definitions"])}
    diaphragms=sorted({(r["Story"],r["Diaphragm"]) for name in ("Area Assignments - Diaphragms","Joint Assignments - Diaphragms")
                       for r in rows(diaphragm[name]) if r["Diaphragm"] in defs})
    modes=rows(source["analysis_sources"]["tables"]["Modal Periods And Frequencies"])
    modal=source["analysis_sources"]["requested_cases"]["modal"]
    mode_ids=identities([r for r in modes if r["Case"]==modal],"Mode")
    sides=("Bottom","Top")
    def cuts(members,names):
        return [(*item,face,name) for k in members for item in [k if isinstance(k,tuple) else (k,)]
                for face,name in product(sides,names)]
    values=dict(axis=axes,columns=col_ids,beams=beam_ids,walls=wall_ids,stories=stories,
        materials=sorted(k for k,v in source["geometry_capture"]["material_types"]["facts"].items() if v["is_concrete"]),
        basis_tables=identities(source["vs04_basis_probe"]["candidate_tables"],"table_key"),basis_links=BASIS_COMPONENTS,
        diaphragm_probes=[(k,"default") for k in diaphragm]+[("Response Spectrum Modal Info",phase) for phase in ("original_selection","selected_RSX_RSY")],
        diaphragm_links=DIAPHRAGM_COMPONENTS,mode_cases=product((x,y),mode_ids),global_slots=["Eq4.19"],combos=graph,
        contexts=contexts,drift=product(stories,(x,y),axes),story_axes=product(stories,axes),
        adjacent=((lo,hi,axis) for lo,hi in zip(stories,stories[1:]) for axis in axes),
        column_cases=product(col_ids,frame_cases),pier_faces=cuts(groups,cases),
        pier_axes=[(*k,axis) for k in groups for axis in axes],beam_ends=product(beam_ids,("I","J")),
        gravity_rect=cuts(singles,gravity),seismic_rect=cuts(singles,spectral),seismic_rect_storeys=product(singles,spectral),
        rect=singles,multi_cuts=cuts(multiples,cases),panel_cases=product(basement,cases),basement=basement,
        wall_ends=product(basement,("I","J")),wall_end_cases=product(basement,("I","J"),cases),
        diaphragms=diaphragms,slabs=[r["UniqueName"] for r in area if r["PropType"]=="Slab" and props[r["SectProp"]]!="Mat"],
        mats=[r["UniqueName"] for r in area if r["PropType"]=="Slab" and props[r["SectProp"]]=="Mat"])
    values["global"]=values.pop("global_slots")
    grains={}
    for grain,keys in values.items():
        ids=sorted([list(k) if isinstance(k,(list,tuple)) else [k] for k in keys])
        require(len(ids)==len({tuple(k) for k in ids}),"G4_DUPLICATE_EXPECTED_INSTANCE:"+grain)
        grains[grain]=ids
    return {"grains":grains,"rules":dict(FAMILIES),"coupling_beam_applicability":_coupling_roles(beams,wrows,points),
            "coupled_transition_columns":sorted(r["UniqueName"] for r in cols if r["ColumnBay"]=="C104"),
            "inventory_fingerprint":_digest(sorted([r["UniqueName"],r["GUID"]] for r in cols+beams+wrows))}


def freeze_population(source,input_sha):
    out={"schema":"tbdy.next.expected-check-instances.v1","input_sha256":input_sha,
         "instance_key":["rule","native_grain_coordinates"],"phase":"BEFORE_MODAL_AND_MEMBER_CALCULATIONS"}
    try:
        out.update(_freeze(source))
    except SOURCE_ERRORS as exc:
        out["unresolved"]=[str(exc)]
    return {**out,"population_sha256":_digest(out)}
