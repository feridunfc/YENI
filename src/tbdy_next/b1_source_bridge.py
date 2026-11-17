"""VS06-D1: real ETABS geometry + LC_WDL source -> B1 X/Y numerical scenario.

This is deliberately a B1 *area* calculation; masonry stiffness below is a
non-normative sensitivity proxy, not an analysis stiffness matrix. Gravity
line loads cannot uniquely identify brick type, thickness or openings.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

from .basis_linkage import LoadRoleBook, _story_floor_rank
from .story_drift_binding import _verify_generic_capture
from .weak_story_b1 import evaluate_b1

GEOM_SCHEMA = "tbdy.next.b1.source-bridge.v1"
TOLERANCE = Decimal("0.000001")
THICKNESSES = (Decimal("0.09"), Decimal("0.19"))


class B1BridgeError(ValueError):
    pass


def dec(value: Any, name: str, *, positive: bool = False) -> Decimal:
    try:
        v = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise B1BridgeError(name + "_DECIMAL_INVALID") from None
    if not v.is_finite() or (v <= 0 if positive else v < 0):
        raise B1BridgeError(name + "_RANGE_INVALID")
    return v


def captured(source: Mapping[str, Any], key: str, fields: set[str],
             units: Mapping[str, str] | None = None) -> list[Mapping[str, Any]]:
    table = source.get("table_reads", {}).get(key)
    if not isinstance(table, Mapping) or table.get("status") != "CAPTURED":
        raise B1BridgeError("B1_REQUIRED_SOURCE_MISSING_" + key)
    metadata = table.get("field_metadata") or {}
    observed = set(table.get("fields") or ())
    known = set(metadata.get("field_keys") or ())
    if (metadata.get("status") != "OK" or not fields.issubset(observed & known)
            or not observed.issubset(known) or len(observed) != len(table["fields"])
            or (units and any(metadata.get("units_by_field", {}).get(k) != v
                             for k, v in units.items()))):
        raise B1BridgeError("B1_SCHEMA_UNRECONCILED_" + key)
    rows = table.get("rows")
    if (not isinstance(rows, list) or table.get("row_count") != len(rows)
            or any(not isinstance(x, Mapping) or set(x) != observed for x in rows)):
        raise B1BridgeError("B1_SOURCE_ROWS_INVALID_" + key)
    return rows


def id_index(rows: list[Mapping[str, Any]], name: str) -> dict[str, Mapping[str, Any]]:
    out = {}
    for row in rows:
        uid = row.get("UniqueName")
        if not isinstance(uid, str) or not uid or uid in out:
            raise B1BridgeError(name + "_IDENTITY_DUPLICATE_OR_EMPTY")
        out[uid] = row
    return out


def axis(a: Mapping[str, Any], b: Mapping[str, Any]) -> tuple[str, Decimal]:
    dx = abs(dec(a["X"], "POINT_X")-dec(b["X"], "POINT_X"))
    dy = abs(dec(a["Y"], "POINT_Y")-dec(b["Y"], "POINT_Y"))
    if dx > TOLERANCE and dy <= TOLERANCE:
        return "X", dx
    if dy > TOLERANCE and dx <= TOLERANCE:
        return "Y", dy
    raise B1BridgeError("OBLIQUE_OR_ZERO_LENGTH_MEMBER_NEEDS_DIRECTIONAL_PROJECTION")


def inferred_wall(q: Decimal, h: Decimal, nominal_gamma: Decimal,
                  minimum_gamma: Decimal, maximum_gamma: Decimal,
                  opening_cutoff: Decimal, opening_fraction: Decimal) -> dict[str, Any]:
    """Rank thickness by full-wall density; opening is *separate* heuristic."""
    if q <= 0:
        raise B1BridgeError("NONPOSITIVE_LINE_LOAD_NOT_A_MASONRY_CANDIDATE")
    candidates = []
    for t in THICKNESSES:
        apparent = q / (h*t)
        plausible = minimum_gamma <= apparent <= maximum_gamma
        # Closest to nominal density, but in-range solutions always outrank
        # out-of-range ones. Neither implies actual brick identification.
        error = abs(apparent/nominal_gamma - 1)
        candidates.append((not plausible, error, t, apparent))
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    _, _, thickness, apparent = candidates[0]
    full_q = nominal_gamma * thickness * h
    ratio = q / full_q
    half = (ratio < opening_cutoff
            and minimum_gamma <= apparent / (1-opening_fraction) <= maximum_gamma)
    net = Decimal(1) - opening_fraction if half else Decimal(1)
    return {
        "thickness_m": str(thickness),
        "apparent_unit_weight_full_kN_m3": str(apparent),
        "unit_weight_in_assumed_range": minimum_gamma <= apparent <= maximum_gamma,
        "q_to_nominal_full_wall_ratio": str(ratio),
        "assumed_opening_fraction": str(opening_fraction if half else Decimal(0)),
        "assumed_net_masonry_fraction": str(net),
        "identification": "GRAVITY_LINE_LOAD_INFERRED_UNCONFIRMED",
        "opening_reason": (
            "LOW_LINE_LOAD_ASSUMED_HALF_OPENING" if half else
            "FULL_WALL_SCENARIO_ASSUMED"
        ),
        "candidate_thickness_options": [
            {"thickness_m": str(t), "apparent_gamma_full_kN_m3": str(g),
             "within_user_density_range": minimum_gamma <= g <= maximum_gamma}
            for _, __, t, g in sorted(candidates, key=lambda z: z[2])
        ],
    }


def _resolve_story_elevations(
    geometry: Mapping[str, Any],
    story_heights: Mapping[str, Decimal],
    scoped_rows: Mapping[str, Any],
) -> dict[str, Decimal]:
    if scoped_rows:
        return {name: Decimal(scoped_rows[name]["upper_elevation_m"]) for name in story_heights}
    parsed: dict[str, Decimal] = {}
    for name in story_heights:
        try:
            parsed[name] = Decimal(name.replace("+", ""))
        except InvalidOperation:
            parsed = {}
            break
    if parsed:
        return parsed

    # F11: Non-numeric story labels (e.g. "Zemin", "1. Kat", "2. Kat").
    # Resolve cumulative elevations from BSElev + Height bottom-up.
    base_elev = Decimal("0")
    base_table = (geometry.get("table_reads") or {}).get("Tower and Base Story Definitions")
    if isinstance(base_table, Mapping) and base_table.get("status") == "CAPTURED":
        base_rows = base_table.get("rows") or []
        if base_rows and "BSElev" in base_rows[0]:
            base_elev = dec(base_rows[0]["BSElev"], "BASE_ELEV")

    names = list(story_heights.keys())
    ranks = [_story_floor_rank(n) for n in names]
    if all(r is not None for r in ranks) and len(names) >= 2:
        paired = sorted(zip(ranks, range(len(names)), names), key=lambda item: (item[0], item[1]))
        names = [item[2] for item in paired]

    out: dict[str, Decimal] = {}
    curr = base_elev
    for name in names:
        curr = curr + story_heights[name]
        out[name] = curr
    return out


def evaluate_b1_sources(
    geometry: Mapping[str, Any], wall_loads: Mapping[str, Any],
    *, wall_type: str = "BRITTLE", unit_weight_kN_m3: str = "10",
    unit_weight_min_kN_m3: str = "6", unit_weight_max_kN_m3: str = "20",
    opening_fraction: str = "0.5", low_load_ratio_cutoff: str = "0.75",
    shear_modulus_mpa: str = "500", R_base: str = "7",
    physical_scope: Mapping[str, Any] | None = None,
    physical_scope_source: Mapping[str, Any] | None = None,
    wall_load_pattern: str = "LC_WDL",
    role_book: Mapping[str, Any] | LoadRoleBook | None = None,
) -> dict[str, Any]:
    """Compute source-bound B1 X/Y with every explicit assumption serialized."""
    roles = LoadRoleBook.from_any(role_book) if role_book is not None else None
    active_wall_pattern = roles.wall_load_pattern if (roles is not None and wall_load_pattern == "LC_WDL") else wall_load_pattern
    try:
        _verify_generic_capture(geometry)
        _verify_generic_capture(wall_loads)
    except (ValueError, TypeError) as exc:
        raise B1BridgeError("B1_GENERIC_CAPTURE_SHA_OR_SCHEMA_INVALID") from exc
    if (geometry.get("model") != wall_loads.get("model")
            or geometry.get("model_units_code") != 6
            or wall_loads.get("model_units_code") != 6):
        raise B1BridgeError("B1_CAPTURE_MODEL_OR_UNITS_MISMATCH")
    gamma=dec(unit_weight_kN_m3,"GAMMA",positive=True)
    gamma_min=dec(unit_weight_min_kN_m3,"GAMMA_MIN",positive=True)
    gamma_max=dec(unit_weight_max_kN_m3,"GAMMA_MAX",positive=True)
    if not (gamma_min <= gamma <= gamma_max):
        raise B1BridgeError("B1_GAMMA_RANGE_CONFLICT")
    opening=dec(opening_fraction,"OPENING_FRACTION")
    threshold=dec(low_load_ratio_cutoff,"OPENING_THRESHOLD")
    if not (Decimal(0) <= opening < 1 and 0 < threshold < 1):
        raise B1BridgeError("B1_OPENING_ASSUMPTION_OUT_OF_RANGE")
    shear=dec(shear_modulus_mpa,"SHEAR_MODULUS",positive=True)
    if wall_type not in ("BRITTLE", "FLEXIBLE"):
        raise B1BridgeError("B1_WALL_TYPE_UNKNOWN")
    pts=id_index(captured(geometry,"Point Object Connectivity",
                         {"UniqueName","X","Y","Z"},
                         {"X":"m","Y":"m","Z":"m"}), "POINT")
    frames=id_index(captured(geometry,"Frame Assignments - Section Properties",
                             {"UniqueName","Story","SectProp","Shape"}),"FRAME")
    sections_by_name={}
    for row in captured(geometry,"Frame Section Property Definitions - Concrete Rectangular",
                         {"Name","t2","t3","DesignType"},{"t2":"m","t3":"m"}):
        if row["Name"] in sections_by_name:
            raise B1BridgeError("B1_DUPLICATE_RECTANGULAR_SECTION")
        sections_by_name[row["Name"]]=row
    story_heights={}
    for row in captured(geometry,"Story Definitions",{"Story","Height"},{"Height":"m"}):
        name=row["Story"]
        if name in story_heights:
            raise B1BridgeError("B1_DUPLICATE_STORY")
        story_heights[name]=dec(row["Height"],"STORY_HEIGHT",positive=True)
    colrows=captured(geometry,"Column Object Connectivity",{"UniqueName","Story","UniquePtI","UniquePtJ"})
    area_by_id=id_index(captured(geometry,"Area Assignments - Section Properties",
                                {"UniqueName","Story","SectProp","PropType"}),"AREA")
    wall_properties={}
    for w in captured(geometry,"Wall Property Definitions - Specified",
                      {"Name","Thickness"},{"Thickness":"m"}):
        if w["Name"] in wall_properties:
            raise B1BridgeError("B1_DUPLICATE_WALL_PROPERTY")
        wall_properties[w["Name"]]=dec(w["Thickness"],"WALL_THICKNESS",positive=True)
    wallrows=captured(geometry,"Wall Object Connectivity",
                      {"UniqueName","Story","UniquePt1","UniquePt2","UniquePt3","UniquePt4"})
    beamrows=captured(wall_loads,"Beam Object Connectivity",
                      {"UniqueName","Story","UniquePtI","UniquePtJ","Length"},
                      {"Length":"m"})
    beam_by_id=id_index(beamrows,"BEAM")
    if any(x["UniqueName"] not in frames for x in colrows):
        raise B1BridgeError("B1_COLUMN_SECTION_JOIN_INCOMPLETE")
    by_story: dict[str, dict[str, Any]] = {}
    for name in story_heights:
        by_story[name]={"X":{"Aw":Decimal(0),"Ag":Decimal(0),"Ak":Decimal(0),
                             "stiff":Decimal(0),"beams":0,"length":Decimal(0),"walls":0},
                        "Y":{"Aw":Decimal(0),"Ag":Decimal(0),"Ak":Decimal(0),
                             "stiff":Decimal(0),"beams":0,"length":Decimal(0),"walls":0},
                        "columns":0}
    for c in colrows:
        name, story=c["UniqueName"],c["Story"]
        sect=sections_by_name.get(frames[name]["SectProp"])
        if story not in by_story or sect is None or sect["DesignType"]!="Column":
            raise B1BridgeError("B1_COLUMN_SECTION_OR_STORY_UNQUALIFIED")
        a=dec(sect["t2"],"COLUMN_T2",positive=True)*dec(sect["t3"],"COLUMN_T3",positive=True)
        for direction in ("X","Y"):
            by_story[story][direction]["Aw"]+=a
        by_story[story]["columns"]+=1
    for w in wallrows:
        name,story=w["UniqueName"],w["Story"]
        a=area_by_id.get(name)
        if story not in by_story or not a or a["PropType"]!="Wall" or a["Story"]!=story:
            raise B1BridgeError("B1_WALL_ASSIGNMENT_OR_STORY_UNQUALIFIED")
        t=wall_properties.get(a["SectProp"])
        if t is None:
            raise B1BridgeError("B1_WALL_THICKNESS_MISSING")
        points=[pts.get(w["UniquePt"+str(i)]) for i in range(1,5)]
        if any(p is None for p in points):
            raise B1BridgeError("B1_WALL_POINT_MISSING")
        plan={}
        for p in points:
            plan[(dec(p["X"],"POINT_X"),dec(p["Y"],"POINT_Y"))]=p
        if len(plan)!=2:
            raise B1BridgeError("B1_WALL_NOT_SIMPLE_VERTICAL_RECTANGLE")
        endpoints=list(plan.values())
        direction,length=axis(endpoints[0],endpoints[1])
        by_story[story][direction]["Ag"]+=length*t
        by_story[story][direction]["walls"]+=1

    probe=wall_loads.get("frame_load_object_probe")
    if (not isinstance(probe,Mapping)
            or probe.get("schema")!="tbdy.next.etabs.frame-object-distributed-load-probe.v1"
            or probe.get("status")!="CAPTURED"
            or probe.get("unresolved_beam_count")!=0
            or probe.get("beam_count")!=len(beam_by_id)
            or probe.get("load_row_count")!=len(probe.get("rows",[]))):
        raise B1BridgeError("B1_LC_WDL_OBJECT_PROBE_INCOMPLETE")
    loads=defaultdict(list)
    for row in probe["rows"]:
        if row["LoadPattern"]!=active_wall_pattern or row["MyType"]!="1" or row["Dir"]!="10":
            continue
        name=row["UniqueName"]
        if name not in beam_by_id:
            raise B1BridgeError("B1_DISTRIBUTED_LOAD_BEAM_JOIN_MISSING")
        loads[name].append(row)
    beam_details=[]
    for name,rows in sorted(loads.items()):
        beam=beam_by_id[name]
        story=beam["Story"]
        if story not in by_story:
            raise B1BridgeError("B1_BEAM_STORY_NOT_IN_GEOMETRY")
        bpts=[pts.get(beam["UniquePtI"]),pts.get(beam["UniquePtJ"])]
        if any(x is None for x in bpts):
            raise B1BridgeError("B1_BEAM_POINT_NOT_FOUND")
        direction,Lxy=axis(*bpts)
        L=dec(beam["Length"],"BEAM_LENGTH",positive=True)
        if abs(L-Lxy)>Decimal(".01"):
            raise B1BridgeError("B1_BEAM_LENGTH_GEOMETRY_CONFLICT")
        frame=frames.get(name)
        sect=sections_by_name.get(frame["SectProp"] if frame else None)
        if not frame or frame["Story"]!=story or sect is None or sect["DesignType"]!="Beam":
            raise B1BridgeError("B1_BEAM_SECTION_UNQUALIFIED")
        beam_depth=dec(sect["t3"],"BEAM_DEPTH",positive=True)
        clear=story_heights[story]-beam_depth
        if clear<=0:
            raise B1BridgeError("B1_NONPOSITIVE_CLEAR_WALL_HEIGHT")
        intervals=[]
        force_integral=Decimal(0)
        for row in rows:
            a,b=(dec(row["RelDistA"],"LOAD_START"),
                 dec(row["RelDistB"],"LOAD_END"))
            if b>1 or b<=a:
                raise B1BridgeError("B1_LOAD_INTERVAL_OUT_OF_BOUNDS")
            q1,q2=dec(row["ValA"],"LOAD_Q1"),dec(row["ValB"],"LOAD_Q2")
            if q1==0 and q2==0:continue
            intervals.append((a,b))
            force_integral+=(b-a)*L*(q1+q2)/2
        if not intervals:continue
        intervals.sort()
        combined=[]
        for a,b in intervals:
            if combined and a<=combined[-1][1]:
                combined[-1]=(combined[-1][0],max(combined[-1][1],b))
            else:
                combined.append((a,b))
        frac=sum((b-a for a,b in combined),Decimal(0))
        loaded=L*frac
        line=force_integral/loaded
        inferred=inferred_wall(line,clear,gamma,gamma_min,gamma_max,threshold,opening)
        thick=Decimal(inferred["thickness_m"])
        net=Decimal(inferred["assumed_net_masonry_fraction"])
        Ak=loaded*thick*net
        stiffness=(shear*1000)*Ak/clear
        output=by_story[story][direction]
        output["Ak"]+=Ak
        output["stiff"]+=stiffness
        output["beams"]+=1
        output["length"]+=loaded
        beam_details.append({
            "beam_id":name, "story":story,"direction":direction,
            "section":sect["Name"],"section_height_m":str(beam_depth),
            "story_height_m":str(story_heights[story]),
            "clear_wall_height_m":str(clear),
            "beam_length_m":str(L),"loaded_length_m":str(loaded),
            "line_load_total_kN_m":str(line),
            "total_force_kN":str(force_integral),
            "assignment_row_count":len(rows),
            "assumed_Ak_m2":str(Ak),
            "assumed_stiffness_proxy_kN_m":str(stiffness),
            **inferred,
        })

    from .physical_story_scope import verified_excluded_stories
    excluded = verified_excluded_stories(physical_scope, geometry, inventory_source=physical_scope_source)
    scoped_rows = ({r["story"]: r for r in physical_scope["stories"]}
                   if physical_scope and physical_scope.get("source_inventory_complete") is True else {})
    if scoped_rows and set(scoped_rows) != set(story_heights):
        raise B1BridgeError("B1_PHYSICAL_SCOPE_STORY_SET_CONFLICT")
    elevations = _resolve_story_elevations(geometry, story_heights, scoped_rows)
    levels=[]
    for story in sorted(story_heights,key=elevations.get):
        b=by_story[story]
        has_structure=b["columns"] or b["X"]["walls"] or b["Y"]["walls"]
        if not has_structure and any(b[x]["beams"] for x in ("X","Y")):
            raise B1BridgeError("B1_BEAM_LOAD_ON_UNSUPPORTED_STORY")
        if scoped_rows:
            if story in excluded and (has_structure or any(b[x]["beams"] for x in ("X", "Y"))):
                raise B1BridgeError("B1_EMPTY_SCOPE_HAS_RESISTANCE_SOURCE:" + story)
            if story not in excluded and not has_structure:
                raise B1BridgeError("B1_PHYSICAL_STORY_VERTICAL_RESISTANCE_UNRESOLVED:" + story)
        # An empty declared ETABS story may be excluded from a *conditional*
        # active-story candidate grain. This is not a complete null/mesh census.
        entry={"story":story,"elevation_m":str(elevations[story]),"active":bool(has_structure)}
        for d in ("X","Y"):
            v=b[d]
            entry[d]={"Aw_m2":str(v["Aw"]),"Ag_m2":str(v["Ag"]),
                      "Ak_m2":str(v["Ak"])}
        levels.append(entry)
    numeric=evaluate_b1(levels,wall_type=wall_type,R_base=R_base)
    output_summaries=[]
    for row in levels:
        st=row["story"]
        b=by_story[st]
        info={"story":st,"active":row["active"],
              "column_count":b["columns"],
              "story_height_m":str(story_heights[st])}
        if scoped_rows:
            info.update(physical_applicability=scoped_rows[st]["applicability"],
                        physical_scope_reason=scoped_rows[st]["reason"])
        for d in ("X","Y"):
            v=b[d]
            info[d]={
                "column_Aw_m2":str(v["Aw"]),"wall_Ag_m2":str(v["Ag"]),
                "infill_Ak_assumed_m2":str(v["Ak"]),
                "wall_count":v["walls"],"loaded_beam_count":v["beams"],
                "loaded_beam_length_m":str(v["length"]),
                "infill_shear_stiffness_proxy_kN_m":str(v["stiff"]),
            }
        output_summaries.append(info)
    provenance={
        "geometry_capture_sha256":geometry["payload_sha256"],
        "wall_load_capture_sha256":wall_loads["payload_sha256"],
        "same_model_path":geometry["model"],
        "analysis_generation_independently_proven":False,
        "source_method":"ETABS DatabaseTables + FrameObj.GetLoadDistributed",
    }
    out={
        "schema":GEOM_SCHEMA,"check_id":"WEAK_STORY_B1",
        "geometry_source_status":"REAL_ETABS_CAPTURE_JOINED",
        "model":geometry["model"],"provenance":provenance,
        "parameters":{
            "wall_type":wall_type,
            "brick_unit_weight_kN_m3":str(gamma),
            "brick_unit_weight_range_kN_m3":[str(gamma_min),str(gamma_max)],
            "candidate_thicknesses_m":[str(x) for x in THICKNESSES],
            "opening_fraction_assumption":str(opening),
            "opening_below_nominal_ratio":str(threshold),
            "masonry_shear_modulus_assumed_mpa":str(shear),
            "R_base_assumed":R_base,
        },
        "source_beam_count":len(beam_by_id),
        "source_wall_load_rows":sum(len(x) for x in loads.values()),
        "source_candidate_wall_beams":len(beam_details),
        "story_direction_areas":output_summaries,
        "beam_assumptions":beam_details,
        "b1_numerical":numeric,
        "assumptions_notes":[
            "The ETABS LC_WDL distributed dead load identifies a candidate infill on a beam. Its physical location requires separate evidence.",
            "Infill thickness is estimated from the 0.09 m and 0.19 m nominal brick options by comparing their unit weights with the observed kN/m.",
            "Assumed net wall height equals ETABS Story Definitions.Height minus the actual t3 depth of the corresponding upper beam. Slabs, plaster and joints are outside this estimate.",
            "The effective infill area is reduced by 50% when q/(γ_nominal×t×h_net) is below the selected threshold and the 50% opening is plausible within the selected γ range.",
            "A low distributed load can also reflect a low-density block, another infill thickness or a different modeling convention. Actual openings require a survey.",
            "B1 uses Ak = wall thickness × loaded beam length × assumed solid fraction. Beam length × wall height is the separate face area.",
            "K_proxy = Gm×Ak/h_net is an independent shear stiffness indicator for sensitivity. ETABS stiffness, equivalent compression struts and the code B2 check require separate calculations.",
            "The ETABS Story label is treated as the upper boundary of the relevant physical column or wall slice. A complete inventory of Null and mesh objects requires separate acceptance.",
            "TBDY 4.9.1.3(b) uses B1 Ak=0 for qualifying flexible connections. Connection capacity requires experimental evidence.",
        ],
        "formal_compliance":"NOT_PROVEN",
        "engineering_release":"NOT_READY",
        "declared_story_count":len(story_heights),
        "physical_source_coverage":("SOURCE_COVERAGE_COMPLETE" if scoped_rows else "UNKNOWN"),
        "code_refs":["TBDY 2018 Table 3.6","TBDY 2018 3.6.2.3"],
    }
    if scoped_rows:
        out.update(physical_scope_sha256=physical_scope["scope_sha256"],
                   excluded_stories=[scoped_rows[name] for name in sorted(excluded)])
        out["assumptions_notes"][7] = (
            "The empty-story exclusion comes from the complete Frame, Area, Wall and Joint source inventory in the same model. "
            "Analysis generation and formal TBDY compliance require additional evidence.")
    out["result_sha256"]=sha256(
        (json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()).hexdigest()
    return out


def _td(value: object) -> str:
    from html import escape
    return "<td>" + escape("—" if value is None else str(value)) + "</td>"


def render_b1_html(report: dict) -> str:
    from html import escape
    s=report["story_direction_areas"]
    parts=[]
    for level in s:
        for d in ("X","Y"):
            x=level[d]
            parts.append("<tr>"+ "".join(_td(v) for v in [
                level["story"], d, level["column_count"],x["wall_count"],
                x["loaded_beam_count"],x["loaded_beam_length_m"],
                x["column_Aw_m2"],x["wall_Ag_m2"],x["infill_Ak_assumed_m2"],
                x["infill_shear_stiffness_proxy_kN_m"],
            ])+"</tr>")
    pairs=[]
    for p in report["b1_numerical"]["paired_results"]:
        pairs.append("<tr>"+"".join(_td(p.get(v)) for v in [
            "lower_story","upper_story","direction","Ae_lower_m2",
            "Ae_upper_m2","eta_ci","numeric_condition",
            "infill_omitted_because_lower_more_than_upper",
        ])+"</tr>")
    beam_rows=[]
    for b in report["beam_assumptions"]:
        beam_rows.append("<tr>"+"".join(_td(b.get(v)) for v in [
            "beam_id","story","direction","beam_length_m","clear_wall_height_m",
            "line_load_total_kN_m","thickness_m","assumed_opening_fraction",
            "assumed_Ak_m2","assumed_stiffness_proxy_kN_m",
        ])+"</tr>")
    notes="<ol>"+ "".join("<li>"+escape(t)+"</li>" for t in report["assumptions_notes"])+"</ol>"
    def h(*headers):
        return "<thead><tr>"+"".join("<th>"+escape(x)+"</th>" for x in headers)+"</tr></thead>"
    css="""body{font:14px/1.5 system-ui,sans-serif;max-width:1200px;margin:40px auto;padding:0 24px;color:#263444}table{border-collapse:collapse;width:100%;font-size:12px}td,th{border:1px solid #d0dae4;padding:8px;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#edf4fa}h1,h2{color:#244e70}section{padding:14px 0}p.warning{border-left:4px solid #ae7940;padding:8px;background:#fff9ec}small{color:#687b8c}"""
    numerical=report["b1_numerical"]
    html=("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
          "<meta name='viewport' content='width=device-width, initial-scale=1'><title>B1 — VS06-D1</title>"
          "<style>"+css+"</style></head><body>"
          "<h1>VS06-D1 · B1 weak story · X/Y source geometry and assumed infill</h1>"
          "<p class='warning'><strong>Numerical calculation complete. Formal TBDY compliance is NOT_PROVEN.</strong> "
          "Physical infill layout requires evidence beyond the ETABS load pattern.</p>"
          "<p>TBDY 2018 Table 3.6 and §3.6.2.3 give ΣAe = ΣAw + ΣAg + 0.15ΣAk. "
          "ηci = lower Ae / upper Ae. Columns and walls use actual ETABS sections and coordinates. "
          "Infill areas use estimates based on observed loads.</p>"
          "<p>ηci,min = <strong>"+escape(numerical["eta_ci_min"])+"</strong>; "
          "Numerical status = <strong>"+escape(numerical["numeric_condition"])+"</strong>; "
          "R multiplier = "+escape(str(numerical["R_multiplier_both_directions"]))+"</p>"
          "<section><h2>Effective areas (m²) and scenario stiffness values (kN/m) by story and direction</h2><table>"+
          h("Story","Direction","Column","Shear wall","Loaded beams","L (m)","Aw (m²)","Ag (m²)","Scenario Ak (m²)","K proxy (kN/m)")+
          "<tbody>"+"".join(parts)+"</tbody></table></section>"
          "<section><h2>B1 interstory comparison</h2><table>"+
          h("Lower story","Upper story","Direction","Lower Ae (m²)","Upper Ae (m²)","ηci","Decision","Ak excluded")+
          "<tbody>"+"".join(pairs)+"</tbody></table></section>"
          "<section><h2>LC_WDL, height, masonry and opening assumptions by beam</h2><table>"+
          h("ETABS ID","Story","Direction","L (m)","Net h (m)","q (kN/m)","t (m)","Opening fraction","Ak (m²)","K proxy (kN/m)")+
          "<tbody>"+"".join(beam_rows)+"</tbody></table></section>"
          "<section><h2>Model assumptions and scope</h2>"+notes+"</section>"
          "<small>Geometry source SHA-256 "+escape(report["provenance"]["geometry_capture_sha256"])+
          " · Load source SHA-256 "+escape(report["provenance"]["wall_load_capture_sha256"])+
          " · Result SHA-256 "+escape(report["result_sha256"])+
          ". Analysis generation, model identity and actual wall layout require independent acceptance.</small>"
          "</body></html>")
    return html
