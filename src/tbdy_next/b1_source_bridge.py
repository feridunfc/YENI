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


def evaluate_b1_sources(
    geometry: Mapping[str, Any], wall_loads: Mapping[str, Any],
    *, wall_type: str = "BRITTLE", unit_weight_kN_m3: str = "10",
    unit_weight_min_kN_m3: str = "6", unit_weight_max_kN_m3: str = "20",
    opening_fraction: str = "0.5", low_load_ratio_cutoff: str = "0.75",
    shear_modulus_mpa: str = "500", R_base: str = "7",
) -> dict[str, Any]:
    """Compute source-bound B1 X/Y with every explicit assumption serialized."""
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
    geom_tables=geometry["table_reads"]
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
        if row["LoadPattern"]!="LC_WDL" or row["MyType"]!="1" or row["Dir"]!="10":
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

    levels=[]
    for story in sorted(story_heights,key=lambda x:Decimal(x.replace("+",""))):
        b=by_story[story]
        has_structure=b["columns"] or b["X"]["walls"] or b["Y"]["walls"]
        if not has_structure and any(b[x]["beams"] for x in ("X","Y")):
            raise B1BridgeError("B1_BEAM_LOAD_ON_UNSUPPORTED_STORY")
        # An empty declared ETABS story may be excluded from a *conditional*
        # active-story candidate grain. This is not a complete null/mesh census.
        entry={"story":story,"elevation_m":story.replace("+",""),"active":bool(has_structure)}
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
        "source_wall_load_rows":len(loads),
        "source_candidate_wall_beams":len(beam_details),
        "story_direction_areas":output_summaries,
        "beam_assumptions":beam_details,
        "b1_numerical":numeric,
        "assumptions_notes":[
            "ETABS LC_WDL self-weight line load was treated as a masonry candidate, not certified wall placement.",
            "Brick thickness was estimated as either 0.09 m or 0.19 m by matching a user-assumed 10 kN/m3 nominal unit weight.",
            "Heights are observed Story Definitions.Height minus observed upper-beam section t3; architectural finish and slab interfaces were not reconstructed.",
            "If q_line / (nominal_gamma*thickness*clear_height) < 0.75 and the 50% opening hypothesis yields plausible gamma, half of the inferred wall plan section is retained.",
            "Actual openings or the brick unit weight cannot be uniquely recovered from line load; classification is a selectable engineering sensitivity assumption.",
            "Ak = thickness*loaded wall length*assumed net masonry fraction; NOT facade gross wall area.",
            "Masonry shear stiffness K_proxy=Gm*Ak/hclear is an illustrative uncoupled shear proxy, not an equivalent strut model and not part of B1 eta.",
            "ETABS story label is interpreted as the upper boundary of that column/wall interval; full null and mesh inventory are not certified.",
            "Flexible infill is ignored in B1 Ak per TBDY 2018 4.9.1.3(b); choosing flexible does not itself prove valid flexible detailing.",
        ],
        "formal_compliance":"NOT_PROVEN",
        "engineering_release":"NOT_READY",
        "code_refs":["TBDY 2018 Table 3.6","TBDY 2018 3.6.2.3"],
    }
    out["result_sha256"]=sha256(
        (json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()).hexdigest()
    return out
