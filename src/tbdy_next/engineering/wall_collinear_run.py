"""Unspliced rods through successive basement columns, including separate friction steel."""
from collections import defaultdict
from itertools import combinations
from math import ceil, fsum, pi

from .basement_joint_layout import check_joint_layout, layout_policy, level_grid
from .basement_wall_connection import _bar_clearance, support_profiles, tension_development
from .basement_wall_pressure import clear_limit
from .wall_membrane_design import SELECTION_LIMIT


def _shared_dowels(incident,details,profiles,geometry,mat,aggregate):
    (a,sa),(b,sb)=incident
    native=[p["native_support_edges"][side]["cuts"] for p,side in incident]
    loads=[{r["combination"]:r for r in cuts} for cuts in native]
    if not loads[0] or loads[0].keys()!=loads[1].keys():
        return None
    policy=layout_policy(geometry,a,details[0]["horizontal"]["cover_mm"],aggregate)
    if abs(a["width_direction"][0]) > .5:
        policy={**policy,"dowel_phase":policy["phase"]}
    cover=max(profiles[p["member"]][side]["cover"] for p,side in incident)
    for dia,pitch in sorted(((d,p) for d in (10,12,14,16,18,20) for p in (50,60,100,125,200)),key=lambda x:x[0]**2/x[1]):
        grid=level_grid(policy,dia,pitch,cover,dowel=True)
        if not grid:
            continue
        area=2*grid["guaranteed_bars_per_m"]*pi*dia**2/4
        steel=.6*area*mat.fyd/1000
        demand={name:sum(x[name]["equivalent_friction_demand_kn_m"] for x in loads) for name in loads[0]}
        if max(demand.values())>SELECTION_LIMIT*steel:
            continue
        rows=[]
        common_off=min(d["ends"][s]["transfer"]["offset_each_side_mm"] for (_,s),d in zip(incident,details))
        for (p,side),detail,actions in zip(incident,details,loads):
            e=detail["ends"][side]
            column=profiles[p["member"]][side]
            h,v=detail["horizontal"],detail["vertical"]
            main=500*p["thickness_m"]-h["cover_mm"]-h["curtain_inset_mm"]-1.5*h["diameter_mm"]
            vertical=v.get("offset_mm", main-(h["diameter_mm"]+v["diameter_mm"])/2)
            off=common_off
            required=tension_development(dia,mat.fyd,mat.fck,mat.fcd,cover,grid["clear_spacing_mm"])["position_i_mm"]
            embed=5*ceil(required/5)
            cap=e["transfer"]["concrete_limit_kn_m"]
            clearance=_bar_clearance(column,off,dia)
            if (clearance<clear_limit(aggregate,dia,column["bar_diameter"]) or 2*off-dia<clear_limit(aggregate,dia)
                or abs(vertical-off)-(dia+v["diameter_mm"])/2<clear_limit(aggregate,dia,v["diameter_mm"])
                or abs(main-off)-(dia+h["diameter_mm"])/2<clear_limit(aggregate,dia,h["diameter_mm"])
                or embed>500*p["clear_length_m"] or max(r["max_native_shear_kn_m"] for r in actions.values())>cap):
                break
            cuts=[{**r,"reaction_kn_m":r["equivalent_friction_demand_kn_m"],
                   "upper_ratio":max(r["equivalent_friction_demand_kn_m"]/steel,r["max_native_shear_kn_m"]/cap)} for r in actions.values()]
            pk=max(r["reaction_kn_m"] for r in cuts)
            rows.append({**e["transfer"],**grid,"diameter_mm":dia,"maximum_pitch_mm":pitch,"as_mm2_m":area,
                         "steel_resistance_kn_m":steel,"resistance_kn_m":min(steel,cap),"steel_ratio":pk/steel,
                         "steel_selection_limit":SELECTION_LIMIT,"peak_ratio":max(r["upper_ratio"] for r in cuts),
                         "force_margin_kn_m":min(steel-pk,cap-max(r["max_native_shear_kn_m"] for r in cuts)),
                         "wall_required_mm":required,"wall_embedment_mm":embed,"column_required_mm":None,
                         "column_embedment_mm":column["depth_mm"],"column_available_mm":column["depth_mm"],
                         "template_longitudinal_clearance_mm":clearance,"entry_required_mm":clear_limit(aggregate,dia,column["bar_diameter"]),
                         "basis":"UNSPLICED_DEDICATED_DOWELS_ACROSS_BOTH_INTERFACES","combinations":cuts})
        if len(rows)==2 and abs(rows[0]["offset_each_side_mm"]-rows[1]["offset_each_side_mm"])<1e-6:
            # Conservative change in dowel force across the column, using the weaker concrete there.
            col=profiles[a["member"]][sa]
            lb=tension_development(dia,mat.fyd,col["fck"],col["fcd"],cover,grid["clear_spacing_mm"])["position_i_mm"]
            bond=max(demand.values())/steel*lb
            if bond<=col["depth_mm"]-2*cover:
                return rows,{"both_interfaces_max_ratio":max(demand.values())/steel,"reserve":SELECTION_LIMIT,
                    "combined_demand_kn_m":demand,"bond_required_mm":bond,"bond_available_mm":col["depth_mm"]-2*cover,
                    "one_piece_length_mm":col["depth_mm"]+sum(r["wall_embedment_mm"] for r in rows)}
    return None


def qualify_run_terminals(panels, proofs):
    """Develop issued spans independently of a held far-end detail on the same bar line."""
    lookup = {p["member"]: p for p in panels}
    done = set()
    for proof in proofs.values():
        run = tuple(proof.get("run_members", ()))
        if not run or run in done:
            continue
        done.add(run)
        held = [uid for uid in run if lookup[uid].get("schedule_status") != "PRESSURE_PANEL_SCHEDULE_QUALIFIED"]
        if not held:
            continue
        lengths = list(proof["piece_lengths_by_face_mm"])
        starters = []
        for uid in held:
            if uid not in proof["terminals_by_member_mm"]:
                break
            panel = lookup[uid]
            shared = [s for s in ("I", "J") if panel["column_" + s.lower()] in proofs]
            if len(shared) != 1:
                break
            side = shared[0]
            end = panel["two_way_shell"]["proposed_detail"]["ends"][side]
            development = 5 * ceil(max(end["wall_side_required_mm"], end["position_i_mm"]) / 5)
            if (end["anchorage_type"] != "UNSPLICED_THROUGH_COLUMN"
                    or development > end["wall_side_available_mm"]):
                break
            for i, adjustment in enumerate(proof["terminals_by_member_mm"][uid]):
                lengths[i] += end["column_depth_mm"] / 2 + development - panel["span_m"] * 1000 - adjustment
            starters.append({"member": uid, "through_column": end["column"], "from": "FAR_COLUMN_FACE",
                             "full_bond_mm": end["wall_side_required_mm"], "straight_starter_mm": development,
                             "available_mm": end["wall_side_available_mm"]})
        issued = [uid for uid in run if uid not in held]
        if len(starters) != len(held):
            for uid in issued:
                lookup[uid].update(schedule_status="PRESSURE_PANEL_DETAIL_OPEN", reason="RUN_TERMINAL_DEVELOPMENT_UNBOUND")
            continue
        for row in proofs.values():
            if tuple(row.get("run_members", ())) == run:
                row.update(trial_piece_lengths_by_face_mm=row["piece_lengths_by_face_mm"],
                           piece_lengths_by_face_mm=lengths, one_piece_length_mm=max(lengths),
                           scheduled_spans=issued, straight_starters=starters,
                           detail="CONTINUOUS_ISSUED_SPANS_WITH_FULLY_DEVELOPED_STRAIGHT_STARTER")


def coordinate_run(geometry,states,designs,mat,aggregate,redesign,source,stages):
    """Trial a common physical cage and check every intermediate column before adopting any span."""
    from .basement_pier_design import _through_bar_proof
    panels=[p for p in geometry["panels"] if p.get("collinear_run")]
    if len(panels)<3:
        return {}
    joints=defaultdict(list)
    for p in panels:
        for side in ("I","J"):
            if p["column_"+side.lower()]:
                joints[p["column_"+side.lower()]].append((p,side))
    interior={k:v for k,v in joints.items() if len(v)==2}
    if len(interior)!=len(panels)-1:
        return {}
    for incident in interior.values():
        (a,sa),(b,sb)=incident
        dot=fsum(x*y for x,y in zip(a["width_direction"],b["width_direction"]))
        if a["joint_"+sa.lower()]!=b["joint_"+sb.lower()] or (1 if sa==sb else -1)*dot>-1+1e-9:
            return {}
    profiles={p["member"]:support_profiles(source,stages,p) for p in panels}
    current={p["member"]:designs[p["member"]] for p in panels}
    pairs=sorted({(d["horizontal"]["diameter_mm"],d["horizontal"]["maximum_pitch_mm"]) for d in current.values() if d.get("horizontal")},
                 key=lambda v:v[0]**2/v[1],reverse=True)
    for pair in pairs:
        trials={}
        for p in panels:
            uid=p["member"]
            d=current[uid]
            h=d.get("horizontal",{})
            if (h.get("diameter_mm"),h.get("maximum_pitch_mm"))!=pair:
                d=redesign(p,pair)
            shared_sides=[s for s in ("I","J") if p["column_"+s.lower()] in interior]
            if d.get("status")!="PROPOSED_COMBINED_CURTAINS":
                if not (len(shared_sides)==1 and d.get("status")=="UNQUALIFIED_CURTAIN_TRIAL"
                        and (d.get("membrane_and_plate") or {}).get("satisfied") and d.get("cut_pmm")
                        and d.get("ends",{}).get(shared_sides[0],{}).get("status")=="CONDITIONAL_PRESSURE_END_DESIGN"
                        and p["native_support_edges"][shared_sides[0]]["status"]=="NATIVE_EDGE_CONTROL_SATISFIED"):
                    break
            trials[uid]={**d,"ends":{s:dict(e) for s,e in d["ends"].items()}}
        if len(trials)!=len(panels):
            continue
        proofs={}
        for col,incident in interior.items():
            ds=[trials[p["member"]] for p,_ in incident]
            # A common bar must match in position and elevation on each physical face.
            levels=[d["horizontal"].get("opposite_face_levels") or d["horizontal"] for d in ds]
            if any(abs(levels[0][key]-levels[1][key])>1e-6 for key in ("first_station_mm","pitch_mm","layers")):
                break
            if incident[0][1]==incident[1][1] and any(d["horizontal"].get("opposite_face_levels") for d in ds):
                break
            proof=_through_bar_proof(incident,ds,states,mat,run=True)
            if not proof:
                break
            dowels=_shared_dowels(incident,ds,profiles,geometry,mat,aggregate)
            if not dowels:
                break
            for ((p,side),d,transfer) in zip(incident,ds,dowels[0]):
                h=d["horizontal"]
                lane=500*p["thickness_m"]-h["cover_mm"]-h["curtain_inset_mm"]-1.5*h["diameter_mm"]
                profile=profiles[p["member"]][side]
                clear=_bar_clearance(profile,lane,h["diameter_mm"])
                e=d["ends"][side]
                if clear<e["entry_required_mm"]:
                    break
                e.update(anchorage_type="UNSPLICED_THROUGH_COLUMN",hook=None,transfer=transfer,
                         specified_embedment_mm=e["column_depth_mm"],template_longitudinal_clearance_mm=clear)
            else:
                proofs[col]={**proof,"through_dowels":dowels[1]}
                continue
            break
        if len(proofs)!=len(interior):
            continue
        proposed=[{**p,"horizontal":trials[p["member"]]["horizontal"],"vertical":trials[p["member"]]["vertical"],
                   "pressure_connections":{"ends":{s:dict(e) for s,e in trials[p["member"]]["ends"].items()}}} for p in panels]
        checks=[check_joint_layout({"panels":proposed},aggregate,proofs,target=col)[0] for col in proofs]
        if not all(c.get("continuous_dowels") and c["status"]=="PROPOSED_PRESSURE_BARS_FIT" for c in checks):
            continue
        # Measure the one-piece paths, including their two actual terminal bends.
        net=fsum(p["span_m"]*1000 for p in panels)
        lengths=[net,net]
        terminals={}
        for p in panels:
            d=trials[p["member"]]
            for side,e in d["ends"].items():
                if p["column_"+side.lower()] in interior:
                    continue
                hook=e.get("hook") or {}
                terminals[p["member"]] = []
                for i,face in enumerate((-1,1)):
                    if hook:
                        proj=hook.get("face_projections_mm",[hook["projection_mm"]]*2)[i]
                        radius=hook["centreline_radius_mm"]
                        extra=proj-d["horizontal"]["diameter_mm"]/2-radius+pi*radius/2+hook["straight_tail_mm"]
                    elif e.get("bar_paths"):
                        path=next(q for q in e["bar_paths"] if q["face"]==face)
                        from math import dist
                        pts=path["points_mm"]
                        extra=dist(pts[0],pts[1])+(pi*e["centreline_radius_mm"]/2+dist(pts[-2],pts[-1]) if len(pts)>2 else 0.)
                    else:
                        extra=e["specified_embedment_mm"]
                    adjustment = extra-e["column_depth_mm"]/2
                    terminals[p["member"]].append(adjustment)
                    lengths[i]+=adjustment
        for proof in proofs.values():
            proof.update(run_members=[p["member"] for p in panels],piece_lengths_by_face_mm=lengths,
                         one_piece_length_mm=max(lengths),terminals_by_member_mm=terminals,
                         detail="CONTINUOUS_RUN_WITH_TWO_DEVELOPED_TERMINALS")
        designs.update(trials)
        return proofs
    return {}
