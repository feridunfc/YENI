"""Check the short native transfer panel and its neighbour's selected boundary cage."""
from itertools import combinations
from math import ceil, hypot, isfinite


def best_hoop_phase_gap(heights, spacing, height):
    """Largest minimum centre separation, allowing any translation of a regular hoop grid."""
    if spacing <= 0:
        raise ValueError("Positive hoop pitch required")
    residues = sorted({z % spacing for z in heights if spacing <= z <= height - spacing})
    if not residues:
        return None
    return max(b - a for a, b in zip(residues, residues[1:] + [residues[0] + spacing])) / 2

from .basement_joint_layout import _families, _segments, _separation
from .basement_wall_pressure import clear_limit
from .wall_bar_paths import point_distance
from .wall_membrane_design import check_curtains


def series_interface_checks(edges, resistance, development, length, selection_limit):
    """One unspliced dowel field crosses two serial planes. Units are kN/m and mm.

    The recorded face actions are upper envelopes. Their difference is useful for
    detailing, but it need not bound the tension jump at one height or spectral step.
    Without a paired lower bound the two nonnegative tensions range from zero
    to the corresponding face demand. The friction coefficient is already present
    in both the equivalent demand and resistance and cancels in the stress ratio.
    """
    if not all(isfinite(v) and v > 0 for v in (resistance, development, length, selection_limit)):
        raise ValueError("BRIDGE_POSITIVE_STEEL_AND_BOND_REQUIRED")
    native = [{row["combination"]: row
               for row in edges[side]["cuts"]} for side in ("I", "J")]
    if (not native[0] or native[0].keys() != native[1].keys()
            or any(len(by_case) != len(edges[side]["cuts"])
                   for side, by_case in zip(("I", "J"), native))):
        raise ValueError("BRIDGE_CUT_POPULATION_MISMATCH")
    bond_capacity = resistance * min(1., length / development)
    rows = []
    for name in sorted(native[0]):
        left_row, right_row = (side[name] for side in native)
        left, right = (row["equivalent_friction_demand_kn_m"] for row in (left_row, right_row))
        if not all(isfinite(v) and v >= 0 for v in (left, right)):
            raise ValueError("BRIDGE_FORCE_ENVELOPE_INVALID")
        peak = max(left, right)
        jump = peak
        controlling = None
        intervals = [row.get("tension_intervals") for row in (left_row,right_row)]
        if any(grid is not None for grid in intervals):
            if not all(isinstance(grid,list) and len(grid)>=2 for grid in intervals):
                raise ValueError("BRIDGE_EDGE_HEIGHT_INTERVALS_INCOMPLETE")
            z = [[point["z_m"] for point in grid] for grid in intervals]
            if (any(not isfinite(v) for grid in z for v in grid)
                    or any(sorted(set(grid)) != grid for grid in z)
                    or len(z[0]) != len(z[1]) or any(abs(a-b)>1e-8 for a,b in zip(*z))):
                raise ValueError("BRIDGE_EDGES_REQUIRE_COMMON_PHYSICAL_HEIGHTS")
            for grid, face_peak in zip(intervals,(left,right)):
                if (any(not (isfinite(p["lower_kn_m"]) and isfinite(p["upper_kn_m"])
                             and 0 <= p["lower_kn_m"] <= p["upper_kn_m"]+1e-9) for p in grid)
                        or abs(max(p["upper_kn_m"] for p in grid)-face_peak)>1e-8):
                    raise ValueError("BRIDGE_EDGE_HEIGHT_FORCE_INVALID")
            differences = [(max(b["upper_kn_m"]-a["lower_kn_m"], a["upper_kn_m"]-b["lower_kn_m"]),
                            a["z_m"],a["node"],b["node"]) for a,b in zip(*intervals)]
            jump, elevation, node_i, node_j = max(differences)
            controlling = {"elevation_m":elevation,"node_i":node_i,"node_j":node_j}
        rows.append({"combination": name, "i_kn_m": left, "j_kn_m": right,
                     "series_demand_kn_m": peak, "friction_ratio": peak / resistance,
                     "face_envelope_difference_kn_m": abs(right - left),
                     "tension_difference_upper_equivalent_kn_m": jump, "governing_height":controlling,
                     "bond_required_mm": development * jump / resistance,
                     "bond_ratio": jump / bond_capacity})
    return {"basis": "SAME_COMBINATION_SERIAL_CUTS_NONNEGATIVE_TENSION_INTERVAL",
            "available_bond_mm": length, "yield_development_mm": development,
            "equivalent_bond_resistance_kn_m": bond_capacity, "combinations": rows,
            "peak_friction_ratio": max(row["friction_ratio"] for row in rows),
            "peak_bond_ratio": max(row["bond_ratio"] for row in rows),
            "friction_satisfied": all(row["friction_ratio"] <= selection_limit for row in rows),
            "bond_satisfied": all(row["bond_ratio"] <= 1 for row in rows)}


def _translated(family,x,y):
    segments=[((a[0]+x,a[1]+y),(b[0]+x,b[1]+y),err) for a,b,err in _segments(family)]
    u,v,w,z=family["bounds"]
    return {**family,"segments":segments,"bounds":(u+x,v+x,w+y,z+y)}


def bridge_checks(geometry,designs,boundaries,source,material,aggregate,states,cuts=()):
    """Keep any unbound joint out of the schedule, even if the short shell balances."""
    panels={p["member"]:p for p in geometry["panels"]}
    result={}
    for link in geometry.get("transfer_panels",[]):
        joints=[link["joint_i"],link["joint_j"]]
        receipt={"link":link["member"],"shared_joints":joints,"status":"HOLD"}
        try:
            if not link.get("edge_balance_verified"):
                raise ValueError("TRANSFER_PANEL_EDGE_BALANCE_UNVERIFIED")
            sources=[]
            for side in ("I","J"):
                end=link["support_sections"][side]
                leg,=[r for r in end["incident_walls"] if r["member"] in panels]
                p=panels[leg["member"]]
                ps=next(k for k in ("I","J") if p["joint_"+k.lower()]==end["joint"])
                d=designs[p["member"]]
                if d.get("status")!="PROPOSED_COMBINED_CURTAINS" or d["ends"][ps]["status"]!="CONDITIONAL_PRESSURE_END_DESIGN":
                    raise ValueError("TRANSFER_INCIDENT_CURTAINS_REQUIRED")
                sources.append((side,p,ps,d,leg))
            sources.sort(key=lambda r:r[-1]["across"])
            (near,straight,ns,sd,_),(far,turn,fs,td,_)=sources
            if sources[0][-1]["across"] or not sources[1][-1]["across"]:
                raise ValueError("STRAIGHT_AND_TURNING_BRIDGE_INTERFACES_REQUIRED")
            support=link["support_sections"][far]
            foreign,=[l for l in support["incident_walls"] if l["member"] not in panels]
            if not boundaries or foreign["across"]:
                raise ValueError("RECEIVING_BOUNDARY_CAGE_UNBOUND")
            pier,=[r for r in boundaries["piers"] if foreign["member"] in r["member_ids"]]
            from .wall_section import reinforced_section
            section,_=reinforced_section(pier,source["column_axial"])
            direction=foreign["direction"]
            normal=(-direction[1],direction[0])
            length=link["span_m"]*1000
            near_xy=(-length*direction[0],-length*direction[1])
            if (abs(section.t2-foreign["span_mm"])>1e-4 or abs(section.t3-foreign["thickness_mm"])>1e-4
                    or abs(sum(a*b for a,b in zip(straight["width_direction"],direction)))<1-1e-8):
                raise ValueError("BRIDGE_RECEIVING_SECTION_IDENTITY_REQUIRED")
            from .wall_bridge_trial import synchronous_trial
            try:
                receipt["synchronized_trial"] = synchronous_trial(straight,turn,link,ns,fs,section,pier,states,
                    material,aggregate,sd["horizontal"]["cover_mm"], (geometry["top_m"]-geometry["bottom_m"])*1000,cuts)
            except (KeyError,ValueError,TypeError,IndexError,StopIteration) as exc:
                receipt["synchronized_trial"] = {"status":"UNRESOLVED","reason":str(exc)}
            collected=[]
            for p,side,d,xy in ((straight,ns,sd,near_xy),(turn,fs,td,(0.,0.))):
                for f in _families({**p,"horizontal":d["horizontal"]},side,d["ends"][side]):
                    collected.append(_translated(f,*xy))
            receipt.update(receiving_panel=foreign["member"],receiving_pier=pier["pier"],length_mm=length,
                           native_link_edges=list(link["native_support_edges"]),receiving_vertical_bar_count=len(section.bars))
            checks=[_separation(a,b,aggregate) for a,b in combinations(collected,2)]
            # Same-run P2 bars are reconstructed by their original section owner, including both boundary zones.
            from math import pi,sqrt
            worst=None
            per_member={}
            for bar in section.bars:
                along=section.t2/2+bar.x2
                px,py=(along*direction[i]+bar.x3*normal[i] for i in (0,1))
                dia=sqrt(4*bar.area/pi)
                for family in collected:
                    space=min(point_distance((px,py),a,b)-err for a,b,err in _segments(family))-(dia+family["diameter"])/2
                    limit=clear_limit(aggregate,dia,family["diameter"])
                    check={"member":family["member"],"role":family["role"],"face":family["face"],
                           "receiving_bar_xy_mm":[px,py],"receiving_diameter_mm":dia,
                           "clear_mm":space,"required_mm":limit,"margin_mm":space-limit}
                    member=family["member"]
                    if member not in per_member or check["margin_mm"]<per_member[member]["margin_mm"]:
                        per_member[member]=check
                    if worst is None or check["margin_mm"]<worst["margin_mm"]:
                        worst=check
            receipt.update(receiving_vertical_governing=worst,receiving_clearance_by_member=per_member,mutual_governing=min(checks,key=lambda x:x["margin_mm"]))
            h,v=sd["horizontal"],sd["vertical"]
            anchors=[sd["ends"][ns],sd["ends"][ns]["transfer"].get("anchor",{})]
            through=all(a.get("return_shape")=="STRAIGHT_THROUGH_RECEIVING_WEB" and
                        a["receiving_members"]==[link["member"],foreign["member"]] for a in anchors)
            if not through:
                raise ValueError("BRIDGE_FULL_LENGTH_HORIZONTAL_FIELD_UNBOUND")
            width=link["thickness_m"]*1000
            if abs(width - straight["thickness_m"] * 1000) > 1e-6:
                raise ValueError("TRANSFER_VERTICAL_GRID_UNBOUND")
            offset = width / 2 - h["cover_mm"] - h["curtain_inset_mm"] - 1.5 * h["diameter_mm"]
            first = max(2, ceil(length / v["pitch_mm"]))
            last = int(length / (v["diameter_mm"] + clear_limit(aggregate, v["diameter_mm"])))
            if first > last:
                raise ValueError("TRANSFER_VERTICAL_GRID_UNBOUND")
            cache = {}
            for n in range(first, last + 1):
                layout = {**v, "pitch_mm": length / n, "stations_per_face": n}
                shell = check_curtains(states[link["member"]], cache, width, h, layout, material, offset)
                if shell["satisfied"]:
                    break
            receipt["bridge_curtains"]={"horizontal_member":straight["member"],"horizontal_diameter_mm":h["diameter_mm"],
                 "vertical_diameter_mm":v["diameter_mm"],"vertical_stations_per_face":n,"vertical_pitch_mm":length/n,
                 "membrane_and_plate_satisfied":shell["satisfied"],"governing":shell["governing"]}
            cage = pier["transverse_cage"]
            height = (geometry["top_m"] - geometry["bottom_m"]) * 1000
            # Every horizontal path through the near side of the closed W6 boundary hoop
            # crosses its transverse leg in plan. A plan crank alone cannot change this bound.
            heights = next(f["heights"] for f in collected if f["member"] == straight["member"] and f["role"] == "web")
            step = cage["spacing_mm"]
            pitches = sorted({step, height / ceil(height / step)})
            receipt["receiving_hoop_phase_trials"] = [
                {"hoop_pitch_mm": pitch, "best_centre_gap_mm": best_hoop_phase_gap(heights, pitch, height),
                 "touching_centre_distance_mm": (h["diameter_mm"] + cage["tie_diameter_mm"]) / 2}
                for pitch in pitches]
            # The W31 rods traverse the whole bridge. Verify their independent friction steel
            # against both native cuts and full tension development past the remote interface.
            transfer=sd["ends"][ns]["transfer"]
            cap=transfer["steel_resistance_kn_m"]
            series = series_interface_checks(link["native_support_edges"], cap, anchors[1]["position_i_mm"],
                                             length, transfer["steel_selection_limit"])
            ratio = series["peak_friction_ratio"]
            peak = max(row["series_demand_kn_m"] for row in series["combinations"])
            receipt.update(series_interface_checks=series, both_cut_friction_ratio=ratio, both_cut_upper_kn_m=peak,
                           dedicated_resistance_kn_m=cap, friction_selection_limit=transfer["steel_selection_limit"])
            # Also bound a regular one-level-per-hoop detail, using the largest catalogue dowel
            # that could develop inside the incident half-span, even before checking its track.
            from math import floor
            from .basement_wall_connection import tension_development
            trials = []
            for pitch in pitches:
                options = []
                for dia in (10, 12, 14, 16, 18, 20, 22, 25):
                    steel_area = 2 * floor(1000 / pitch + 1e-9) * pi * dia**2 / 4
                    full_bond = tension_development(dia, material.fyd, material.fck, material.fcd,
                                                    h["cover_mm"], pitch - dia)["position_i_mm"]
                    if full_bond <= sd["ends"][ns]["wall_side_available_mm"]:
                        options.append((.6 * steel_area * material.fyd / 1000, dia, full_bond))
                if options:
                    resistance, dia, bond = max(options)
                    trials.append({"pitch_mm":pitch, "largest_developed_diameter_mm":dia, "bond_mm":bond,
                                   "upper_steel_resistance_kn_m":resistance, "both_cut_ratio":peak/resistance})
            receipt["hoop_synchronized_dowel_trials"] = trials
            if worst["margin_mm"]<0:
                raise ValueError("TRANSFER_BARS_INTERSECT_RECEIVING_BOUNDARY_CAGE")
            if not shell["satisfied"] or not all(q["fits"] for q in checks):
                raise ValueError("TRANSFER_SHELL_OR_MUTUAL_BAR_LAYOUT_UNSATISFIED")
            if not series["friction_satisfied"] or not series["bond_satisfied"] or any(a["specified_embedment_mm"]-length<a["position_i_mm"] for a in anchors):
                raise ValueError("BRIDGE_FRICTION_OR_TERMINAL_BOND_UNSATISFIED")
            # Reserve all possible hook projections inside each complete transverse cage
            # at its specified layers. This is a conservative clearance certificate.
            tied=hk=0
            def inside(f,poly):
                from .wall_bar_paths import segment_distance
                def occupied(p):
                    u=sum(x*y for x,y in zip(p,direction))
                    t=sum(x*y for x,y in zip(p,normal))
                    return poly[0]<=u<=poly[1] and poly[2]<=t<=poly[3]
                corners=[(u*direction[0]+t*normal[0],u*direction[1]+t*normal[1])
                         for u,t in [(poly[0],poly[2]),(poly[1],poly[2]),(poly[1],poly[3]),(poly[0],poly[3])]]
                return min(0. if occupied(a) or occupied(b) else max(0.,min(segment_distance(a,b,c,d)
                       for c,d in zip(corners,corners[1:]+corners[:1]))-err) for a,b,err in _segments(f))
            from .basement_joint_layout import _closest_levels
            levels=ceil(height/cage["spacing_mm"])
            elevations=[(i+.5)*height/levels for i in range(levels)]
            cover=cage["cover_mm"]
            for f in collected:
                plan=inside(f,(cover,pier["adopted_constant_detail"]["end_width_mm"]-cover,
                                -section.t3/2+cover,section.t3/2-cover))
                dz=_closest_levels(f["heights"],elevations)[0]
                if hypot(plan,dz)-f["diameter"]/2-cage["tie_diameter_mm"]/2<clear_limit(aggregate,f["diameter"],cage["tie_diameter_mm"]):
                    raise ValueError("RECEIVING_BOUNDARY_HOOP_ENVELOPE_UNRESOLVED")
                hk+=1
            # Place the proposed link verticals and transverse ties at actual stations.
            vrt=offset-(h["diameter_mm"]+v["diameter_mm"])/2
            for i in range(n):
                along=-length+(i+.5)*length/n
                for f in collected:
                    if f["member"]==straight["member"] and f["role"]=="web":
                        continue  # The proposed W32 verticals tie to these continuing web rods.
                    for face in (-1,1):
                        pt=tuple(along*direction[j]+face*vrt*normal[j] for j in (0,1))
                        gap=min(point_distance(pt,a,b)-err for a,b,err in _segments(f))-(f["diameter"]+v["diameter_mm"])/2
                        if gap<clear_limit(aggregate,f["diameter"],v["diameter_mm"]):
                            raise ValueError("BRIDGE_RECEIVING_VERTICAL_CLEARANCE_UNSATISFIED")
                    tie=inside(f,(along-h["diameter_mm"],along+h["diameter_mm"],-offset,offset))
                    dz=_closest_levels(f["heights"],[h["first_station_mm"]+j*h["pitch_mm"] for j in range(h["layers"])])[0]
                    if hypot(tie,dz)<(f["diameter"]+h["diameter_mm"])/2:
                        raise ValueError("BRIDGE_CROSSTIE_CLEARANCE_UNSATISFIED")
                    tied+=1
            receipt.update(status="TRANSFER_CAGE_LAYOUT_VERIFIED",boundary_hoop_checks=hk,bridge_crosstie_checks=tied)
        except (KeyError,ValueError,TypeError,IndexError,StopIteration) as exc:
            receipt["reason"]=str(exc)
        for joint in joints:
            result["joint "+joint]=receipt
    return result
