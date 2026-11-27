"""Independent equilibrium and schedule checks for the scoped G5 frame review."""
from functools import lru_cache
from math import acos, ceil, hypot, isclose, pi, sqrt

from ..engineering.design_scenario import _digest


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def equal(actual, expected, key, tolerance=1.e-6):
    if not isclose(actual, expected, rel_tol=1.e-9, abs_tol=tolerance):
        raise ValueError(f"{key}: recorded {actual:.9g}, expected {expected:.9g}")


def unique(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), "Duplicate frame shear identity: " + key)
    return result


@lru_cache(maxsize=16384)
def principal_mr(width, depth, across, along, radius, cover, fcd, fyd, es, nd):
    """C35 rectangular stress block, exact displaced bar segments, axial bisection."""
    area = pi * radius**2
    levels = [(depth/2-cover-radius)*(2*i/(along-1)-1) for i in range(along)]
    counts = [across] + [2]*(along-2) + [across]
    stress = .85*fcd
    low, high = 0., 16*depth
    for _ in range(47):
        neutral = (low+high)/2
        thickness = min(depth, .79*neutral)
        line = depth/2-thickness
        force = stress*width*thickness
        moment = force*(depth/2-thickness/2)
        for y, count in zip(levels, counts):
            steel = max(-fyd, min(fyd, .003*es*(1-(depth/2-y)/neutral))) * area
            distance = line-y
            removed, first = 0., 0.
            if distance <= -radius:
                removed = area
            elif distance < radius:
                chord = sqrt(radius**2-distance**2)
                removed = radius**2*acos(distance/radius)-distance*chord
                first = 2*chord**3/3
            bar = steel-stress*removed
            force += count*bar
            moment += count*(bar*y-stress*first)
        if force < nd*1000:
            low = neutral
        else:
            high = neutral
    equal(force, nd*1000, "Independent principal section axial residual", .001)
    return moment/1.e6


def schedule(row, length, zone, end_pitch, mid_pitch, diameter, *, column):
    s = row["schedule"]
    equal(s["clear_length_mm"], length, "Schedule physical clear length")
    equal(s["required_end_length_mm"], zone, "Required confinement length")
    equal(s["confined_union_mm"], min(length,2*zone), "Union of confinement intervals")
    for recorded, expected in zip(s["end_intervals_mm"]["I"]+s["end_intervals_mm"]["J"],
                                  [0.,min(length,zone),max(0.,length-zone),length], strict=True):
        equal(recorded, expected, "Confinement face coordinate")
    stations = [s["first_tie_mm"]]
    for run in s["runs"]:
        equal(run["from_mm"], stations[-1], "Gap in tie schedule")
        intervals = run["intervals"]
        require(isinstance(intervals,int) and intervals>0, "Nonpositive tie interval count")
        pitch = (run["to_mm"]-run["from_mm"])/intervals
        equal(pitch, run["pitch_mm"], "Tie coordinates and spacing")
        for step in range(1,intervals+1):
            pos = run["from_mm"] + pitch*step
            in_zone = stations[-1] < zone-1.e-7 or pos > length-zone+1.e-7
            require((50.-1.e-7 if column else 0.) <= pitch <= (end_pitch if in_zone else mid_pitch)+1.e-7,
                    "Tie station pitch outside physical zone limit")
            stations.append(pos)
    equal(stations[-1],s["last_tie_mm"],"Last tie coordinate")
    require(len(stations)==s["tie_count"] and 0<=stations[0]<=50 and 0<=length-stations[-1]<=50.000001,
            "First/last tie or station census")
    hooks = [(row["hook"],diameter)] if column else [(row["end_hook"],diameter[0]),(row["middle_hook"],diameter[1])]
    for hook,d in hooks:
        require(hook["hook_angle_deg"]==135 and hook["minimum_ribbed_tail_mm"]>=max(80,6*d)
                and hook["minimum_inside_bend_diameter_mm"]>=5*d, "Tie hook geometry")
    return len(stations)


def beam_check(beam, section, conf, native, gravity):
    length = beam["length_mm"]-sum(beam["end_offsets_mm"].values())
    equal(length, beam["clear_span_mm"], "Beam support faces")
    caps = [end["engineer_selection"]["capacity"] for end in (beam["ends"]["I"],beam["ends"]["J"])]
    sway = [1.4*(abs(caps[0][a+"_m3_knm"])+abs(caps[1][b+"_m3_knm"]))/(length/1000)
            for a,b in (("positive","negative"),("negative","positive"))]
    require(gravity.issubset(native["LoadCase"]), "Beam gravity combinations missing")
    vdy = max(abs(v) for name,v in zip(native["LoadCase"],native["V2"],strict=True) if name in gravity)
    ve = max(sway)+vdy
    terms = beam["engineer_shear_ve"]
    for key,value in zip(("earthquake_shear_sway_left_kn","earthquake_shear_sway_right_kn",
                          "gravity_shear_vdy_kn","scenario_ve_kn"),[*sway,vdy,ve],strict=True):
        equal(terms[key],value,key)
    ties = beam["engineer_stirrups"]
    bw,h = section["width_mm"],section["height_mm"]
    ends = [e["engineer_selection"] for e in beam["ends"].values()]
    # Effective cover is the centroid of the actual selected bar rows at each end.
    d = h-max(e["effective_"+face+"_centroid_mm"] for e in ends for face in ("top","bottom"))
    equal(ties["effective_depth_mm"],d,"Beam effective depth")
    web = .22*section["fcd_mpa"]*bw*d/1000
    equal(ties["vr_max_kn"],web,"Beam brittle web limit")
    require(ve <= web and beam["selected_design"]["status"]=="CONDITIONAL_DESIGN_CALCULATED",
            "Selected beam shear exceeds web")
    vcr = .65*.35*sqrt(section["fck_mpa"])*section["fcd_mpa"]/section["fck_mpa"]*bw*d/1000
    for name in ("confinement","span"):
        z = ties[name]
        area = z["legs"]*pi*z["diameter_mm"]**2/4
        vw = area/z["spacing_mm"]*ties["fywd_mpa"]*d/1000
        vr = vw+(0. if name=="confinement" else .8*vcr)
        for key,value in (("asw_mm2",area),("demand_kn",ve),("vw_kn",vw),("vcr_kn",vcr),
                          ("vr_conservative_kn",vr),("utilization_conservative",ve/vr)):
            equal(z[key],value,"Beam "+name+" "+key)
        fctd=.35*sqrt(section["fck_mpa"])*section["fcd_mpa"]/section["fck_mpa"]
        min_bar=min(b["diameter_mm"] for e in ends for b in e["bars"])
        pitch_limit=min(d/4,8*min_bar,150) if name=="confinement" else min(d/2,300)
        rho_min=.3*fctd/ties["fywd_mpa"]
        equal(z["rho_w_min"],rho_min,"Beam minimum shear reinforcement")
        equal(z["rho_w"],area/(z["spacing_mm"]*bw),"Beam installed shear reinforcement")
        equal(z["tbdy_spacing_limit_mm"],pitch_limit,"Beam tie pitch limit")
        require(ve<=vr and bw/(z["legs"]-1)<=350 and area/(z["spacing_mm"]*bw)>=rho_min
                and z["spacing_mm"]<=pitch_limit+1.e-7,
                "Beam transverse or capacity limit")
    end,mid = ties["confinement"],ties["span"]
    n = schedule(conf,length,2*h,end["spacing_mm"],mid["spacing_mm"],
                 (end["diameter_mm"],mid["diameter_mm"]),column=False)
    return {"Ve_kn":ve,"governing_ratio":max(ve/web,end["utilization_conservative"],mid["utilization_conservative"]),
            "tie_stations":n}


def joint_checks(record, beam_map, all_columns):
    out = []
    require(set(unique(record["member_joint_ends"],"end"))=={"I","J"},"Both physical column ends required")
    for end in record["member_joint_ends"]:
        if not end["axes"]:
            require(end["status"]=="NO_RECORDED_BEAM_AT_NODE" and not any(end["faces"].values())
                    and not any(end["point_id"] in (b["point_i"],b["point_j"]) for b in beam_map.values()),
                    "Missing framed column end")
            out.extend({"joint":end["point_id"],"end":end["end"],"axis":a,
                        "physical_role":"NO_FRAMING_BEAM_IN_DIRECTION"} for a in ("V2","V3"))
            continue
        require(set(unique(end["axes"],"axis"))=={"V2","V3"},"Both joint directions required")
        for axis in end["axes"]:
            geometry = axis.get("calculation")
            key = {"joint":end["point_id"],"end":end["end"],"axis":axis["axis"]}
            if not geometry:
                require(not any(v for k,v in end["faces"].items() if k.startswith(axis["axis"][-1])),
                        "Framed direction lacks a panel calculation")
                out.append({**key,"physical_role":"NO_FRAMING_BEAM_IN_DIRECTION"})
                continue
            panel = axis["joint_shear_ve"]
            ties = axis["joint_transverse_7_5_2_3"]
            enclosed = end["enclosure_scenario"]=="ENCLOSED"
            limit = (1.7 if enclosed else 1.)*geometry["bj_mm"]*geometry["h_mm"]*sqrt(end["fck_mpa"])/1000
            equal(geometry["bj_mm"],min(geometry["b_mm"],geometry["minimum_beam_width_mm"]+geometry["h_mm"]),
                  "Joint effective width")
            equal(geometry["geometric_limit_kn"],limit,"Joint shear capacity")
            faces = []
            for face,item in sorted(panel["faces"].items()):
                if not item["present"]:
                    require(not end["faces"].get(face),"Missing existing beam face")
                    faces.append((0.,0.))
                    continue
                beam = beam_map[item["frame_id"]]
                side = item["native_end"]
                require(beam["point_"+side.lower()]==end["point_id"],"Joint beam end identity")
                sel = beam["ends"][side]["engineer_selection"]
                steel = []
                for f,label in (("top","top"),("bot","bottom")):
                    area = sel["area_"+label+"_mm2"]
                    equal(item["as_"+f+"_mm2"],area,"Selected joint beam steel")
                    steel.append(1.25*beam["fyk_mpa"]*area/1000)
                faces.append(steel)
            (ta,ba),(tb,bb) = faces
            equal(panel["v_kol_used_kn"],0.,"Original spectral joint deduction")
            ve = max(ta+bb,ba+tb)
            equal(panel["governing_ve_kn"],ve,"Two-sense joint equilibrium")
            equal(panel["utilization"],ve/limit,"Joint utilization")
            lower = all_columns[ties["lower_column_id"]]["engineer_column_selection"]["selected"]["selected_transverse"]
            lower_axis = ties["lower_axis"].lower()
            ash = lower["confinement_"+lower_axis]["high_axial_required_ash_mm2"]
            f = .4 if enclosed else .6
            required = f*ash/lower["confinement_spacing_mm"]*ties["joint_spacing_mm"]
            equal(ties["required_ash_at_joint_spacing_mm2"],required,"Lower-column confinement density")
            equal(ties["proposed_ash_mm2"],lower["legs_"+lower_axis]*pi*ties["tie_diameter_mm"]**2/4,
                  "Joint transverse steel")
            require(ve<=limit and required<=ties["proposed_ash_mm2"]+1.e-7 and
                    ties["joint_spacing_mm"] <= (150 if enclosed else 100) and ties["tie_diameter_mm"]>=8,
                    "Joint panel or transverse limit")
            out.append({**key,"Ve_kn":ve,"panel_ratio":ve/limit,"tie_ratio":required/ties["proposed_ash_mm2"]})
    return out


def column_check(record, section, cage, conf, native, gravity, seismic, beam_map, all_columns):
    t = cage["selected_transverse"]
    owner = record["column_transverse_and_shear"]
    ve = owner["engineer_capacity_shear_ve"]
    length = 1000*(conf["face_z_m"][1]-conf["face_z_m"][0])
    equal(ve["clear_length_m"],length/1000,"Column face elevations")
    a,b = section["t2_mm"],section["t3_mm"]
    fc,fcd = section["fck_mpa"],section["fcd_mpa"]
    require(fc==35,"Column principal integration C35 scope")
    eq77 = .85*a*b*sqrt(fc)/1000
    out = []
    tie_d=t["tie_diameter_mm"]
    c=section["cover_to_tie_mm"]
    core=(a-2*c)*(b-2*c)
    bk_min=min(a,b)-2*c-tie_d
    require(tie_d>=max(8,cage["diameter_mm"]/3) and
            50<=t["confinement_spacing_mm"]<=min(150,6*cage["diameter_mm"],bk_min/3) and
            t["midspan_spacing_mm"]<=min(200,12*cage["diameter_mm"],bk_min/2),"Column tie diameter or pitch")
    for axis in ("V2","V3"):
        width,depth,nw,nh = (b,a,cage["num_bars_3_dir"],cage["num_bars_2_dir"]) if axis=="V2" else (
            a,b,cage["num_bars_2_dir"],cage["num_bars_3_dir"])
        ties = t["legs_"+axis.lower()]*pi*t["tie_diameter_mm"]**2/4
        bk=width-2*c-tie_d
        ash=max(.30*(a*b/core-1),.075)*t["confinement_spacing_mm"]*bk*fc/owner["fywk_mpa"]
        equal(t["confinement_"+axis.lower()]["high_axial_required_ash_mm2"],ash,"Column confinement steel requirement")
        legs=t["legs_"+axis.lower()]
        cross_pitch=ceil((nw-1)/(legs-1))*(width-2*c)/(nw-1)
        require(cross_pitch<=25*tie_d+1.e-7 and ties>=ash-1.e-7,"Column confinement area or leg spacing")
        cover = section["cover_to_tie_mm"]+t["tie_diameter_mm"]
        d = depth-cover-cage["diameter_mm"]/2
        gs = section["gamma_s"]
        vw = ties/t["confinement_spacing_mm"]*owner["fywk_mpa"]/gs*d/1000
        def mr(nd):
            return principal_mr(width,depth,nw,nh,cage["diameter_mm"]/2,cover,fcd,section["fyd_mpa"],section["es_mpa"],nd)
        static = unique(ve["axes"][axis]["cases"],"combination")
        spectral = unique(ve["assigned_spectral"]["axes"][axis]["cases"],"combination")
        require(set(static)==gravity and set(spectral)==seismic,"Column axis combination census")
        for name,row in {**static,**spectral}.items():
            inds = [i for i,case in enumerate(native["LoadCase"]) if case==name]
            floor = max(abs(native[axis][i]) for i in inds)
            equal(row["vd_floor_kn"],floor,"Native column cut shear floor")
            nd = min(-native["P"][i] for i in inds)
            axial = nd*1000/(a*b)
            vc = .8*.65*.35*sqrt(fc)*(fcd/fc)*width*d*(1+(.07 if axial>=0 else .30)*axial)/1000
            equal(row["vr_ts500_min_kn"],vc+vw,"Column concrete and transverse resistance")
            moments = []
            for side in ("I","J"):
                sta = (min if side=="I" else max)(native["ObjSta"][i] for i in inds)
                end_nd = [-native["P"][i] for i in inds if abs(native["ObjSta"][i]-sta)<1.e-8]
                if name in static:
                    require(len(end_nd)==1,"Ambiguous column static end cut")
                    moment = mr(end_nd[0])
                    for joint in record["scwb_joints"]:
                        if joint["direction"]==ve["axes"][axis]["direction"] and joint["target_end"]==side:
                            reference=max(r["target_column_capacity_knm"] for r in joint["engineer_selected_scwb"]["cases"]
                                          if r["output_case"]==name)
                            equal(reference,moment,"Independent SCWB end moment",.01)
                else:
                    ev = row["end_moments"][side]
                    require(len(end_nd)==2 and ev["cut"][0]==record["member_id"],"Spectral end identity")
                    equal(ev["nd_interval_kn"][0],min(end_nd),"End compression minimum")
                    equal(ev["nd_interval_kn"][1],max(end_nd),"End compression maximum")
                    equal(ev["lever_bound_m"],depth/2000,"Axial interval lever bound")
                    anchors=ev["anchors"]
                    require(len(anchors)==5 and anchors[0]["nd_kn"]<=min(end_nd)<=max(end_nd)<=anchors[-1]["nd_kn"],
                            "Uncovered axial interval")
                    values=[]
                    for anchor in anchors:
                        capacity=mr(anchor["nd_kn"])
                        equal(capacity,anchor["mr_knm"],"Independently integrated spectral anchor",.01)
                        tolerance=.001+.002*anchor["mr_knm"]+hypot(width,depth)/2.e6
                        equal(anchor["tolerance_knm"],tolerance,"Anchor tolerance")
                        values.append(capacity+tolerance)
                    moment=max(max(x,y)+(right["nd_kn"]-left["nd_kn"])*depth/4000 for
                               x,y,left,right in zip(values,values[1:],anchors,anchors[1:]))
                    equal(ev["mp_upper_knm"],1.4*moment,"Upper bound on spectral plastic moment",.015)
                moments.append(1.4*moment)
            demand=max(floor,sum(moments)/(length/1000))
            if name in static:
                equal(row["ve_unreduced_kn"],sum(moments)/(length/1000),"Static moment shear",.015)
                equal(row["ve_scwb_scenario_kn"],demand,"Static column Ve",.015)
                equal(row["vr_zero_concrete_min_kn"],vw,"Static zero concrete")
                ratio=demand/vw
            else:
                equal(row["ve_upper_kn"],demand,"Spectral column Ve",.015)
                equal(row["tbdy_eq7_7_limit_kn"],eq77,"Equation 7.7")
                limit=vw if nd<=.05*a*b*fc/1000 else vw+vc
                equal(row["vr_used_kn"],limit,"Spectral axial threshold")
                ratio=demand/limit
            require(demand<=eq77+.015 and ratio<=1.00001,"Column shear resistance or brittle limit")
            out.append({"axis":axis,"case":name,"Ve_kn":demand,"brittle_ratio":demand/eq77,"shear_ratio":ratio})
    n=schedule(conf,length,max(length/6,1.5*max(a,b),500),t["confinement_spacing_mm"],t["midspan_spacing_mm"],
               t["tie_diameter_mm"],column=True)
    require(conf["lateral_leg_spacing_mm"]<=25*t["tie_diameter_mm"],"Column tie cage")
    return {"shear":out,"tie_stations":n,"joint_directions":joint_checks(record,beam_map,all_columns)}


def frame_audit(source, stages, building):
    from ..engineering.g3_capacity import section_inputs
    basis=section_inputs(source,stages,building)
    feature=source["column_axial"]
    all_columns=stages["r10_live"]["per_member"]
    native_sections={r["member_id"]:r["section_evidence"] for r in stages["column_pmm"]["members"]}
    beam_map=unique(stages["beam_r10"]["beams"],"member_id")
    groups=stages["column_axial"]["combination_plan"]["design_assignment"]["groups"]
    gravity,seismic=set(groups["gravity"]),set(groups["ductile"])
    schedules={key:unique(building["frame_confinement"][key],"member_id") for key in ("beams","columns")}
    evidence={"columns":{},"beams":{},"foundation_failures":{},"issues":[]}
    for family, inputs in basis.items():
        for uid, item in sorted(inputs.items()):
            try:
                conf=schedules[family][uid]
                if family=="columns":
                    col=all_columns[uid]
                    rec=column_check(col,native_sections[uid],col["engineer_column_selection"]["selected"],conf,
                        feature["force_source"]["rowsets"][uid],gravity,seismic,beam_map,all_columns)
                else:
                    rec=beam_check(beam_map[uid],item,conf,feature["r10_source"]["beam_force_source"]["rowsets"][uid],gravity)
                evidence[family][uid]=rec
            except (KeyError,ValueError,ArithmeticError,TypeError,IndexError) as exc:
                evidence["issues"].append(f"{family}/{uid}: {exc}")
    for col in building["columns"]:
        if col["status"]=="failed":
            uid=col["member_id"]
            f=schedules["columns"][uid]["foundation_continuation"]
            require(f["model_depth_mm"]==600 and f["required_mm"]==800 and not f["gross_depth_sufficient"],
                    "Original foundation continuation failure changed")
            evidence["foundation_failures"][col["label"]]=[f["model_depth_mm"],f["required_mm"]]
    require(set(evidence["foundation_failures"])=={"C21","C22","C23","C24"},"Foundation failure census")
    evidence["totals"]={"conditional_columns":len(evidence["columns"]),"beams":len(evidence["beams"]),
        "static_axis_cases":sum(r["case"] in gravity for c in evidence["columns"].values() for r in c["shear"]),
        "spectral_axis_cases":sum(r["case"] in seismic for c in evidence["columns"].values() for r in c["shear"]),
        "joint_axes":sum("Ve_kn" in a for c in evidence["columns"].values() for a in c["joint_directions"]),
        "foundation_failures":len(evidence["foundation_failures"])}
    return evidence
