"""Project the same sealed wall-transition values into the workspace and the printable report."""


def transition_tables(walls):
    location = ["Pier", "Storey", "Opening z (m)"]
    global_axes = ["FX (kN)", "FY (kN)", "FZ (kN)", "MX (kN·m)", "MY (kN·m)", "MZ (kN·m)"]
    local_axes = ["P (kN)", "V2 (kN)", "V3 (kN)", "T (kN·m)", "M2 (kN·m)", "M3 (kN·m)"]
    sections, frames, loads = [], [], []
    bases = set()
    for wall in walls:
        for change in wall.get("transitions", ()):
            label = [wall["pier"], wall["story"], change["z_m"]]
            shell = change["shell_actions"]
            if shell.get("basis") == "INPUT_IDENTICAL_PRIVATE_REANALYSIS":
                bases.add(
                    f"Private replay of identical inputs, {shell['solution']['pier_controls']['rows']} original pier rows matched."
                )
            elif shell.get("basis") == "SOLVED_ORIGINAL":
                bases.add("Shell actions are from the solved original model.")
            for sec in change["sections"]:
                start = label + [
                    sec["side"],
                    ", ".join(sec["members"]),
                    sec["net_area_m2"],
                    sec.get("axial_limit_kn"),
                ]
                for key, method in (("sections", "Native shell edges"), ("recovered", "Shell corner field")):
                    for v in shell[key]:
                        if v["side"] != sec["side"]:
                            continue
                        deltas = v.get("control_delta_kn_knm")
                        sections.append(
                            start
                            + [
                                method,
                                v["z_m"],
                                v["combination"],
                                *v["global_kn_knm"],
                                v.get("reference_axial_ratio"),
                                v.get("control_z_m"),
                                max(map(abs, deltas[:3])) if deltas else None,
                                max(map(abs, deltas[3:])) if deltas else None,
                            ]
                        )
                        if "control_uniform_load_kn_knm" in v:
                            for name, field in (
                                ("Control difference before load projection", "control_delta_kn_knm"),
                                (
                                    "Uniform pressure and weight at control edge",
                                    "control_uniform_load_kn_knm",
                                ),
                                (
                                    "Control difference after load projection",
                                    "control_delta_after_uniform_load_kn_knm",
                                ),
                            ):
                                sections.append(
                                    start
                                    + [
                                        name,
                                        v["control_z_m"],
                                        v["combination"],
                                        *v[field],
                                        None,
                                        v["control_z_m"],
                                        None,
                                        None,
                                    ]
                                )
                if not any(s["side"] == sec["side"] for s in shell["recovered"]):
                    reason = shell.get("field_reasons", {}).get(
                        sec["side"], shell.get("reason", shell["status"])
                    )
                    sections.append(start + [reason, sec["mesh_section"].get("z_m"), None] + [None] * 10)
            for j in change["jambs"]:
                start = label + [j["point"], j.get("label") or j.get("column")]
                detail = j.get("model_detail") or {}
                if (
                    detail.get("bar_count")
                    and detail.get("longitudinal_bar_diameter_mm")
                    and detail.get("tie_diameter_mm")
                ):
                    text = (
                        f"{detail['section']}, {detail['bar_count']} Ø{detail['longitudinal_bar_diameter_mm']:g}, "
                        f"Ø{detail['tie_diameter_mm']:g} ties. {detail.get('reinforcement_role', '')}. "
                        "Opening bar continuity and development require a connection detail."
                    )
                    frames.append(start + ["Model reinforcement", None] + [None] * 6 + [text])
                for v in j.get("combinations", ()):
                    for kind, key in (
                        ("Below", "below"),
                        ("Above", "above"),
                        ("Above minus below", "above_minus_below"),
                    ):
                        frames.append(
                            start + [kind, v["combination"], *v.get(key, [None] * 6), v.get("reason")]
                        )
                for v in j.get("seismic_bounds", ()):
                    for kind, key in (("Lower bound", "minimum"), ("Upper bound", "maximum")):
                        frames.append(
                            start + [kind, v["combination"], *v.get(key, [None] * 6), v.get("reason")]
                        )
                if not j.get("combinations"):
                    frames.append(start + [None, None] + [None] * 6 + [j.get("reason") or j["status"]])
            for panel in change["panel_loads"]:
                start = label + [panel["label"]]
                for row in panel.get("combinations", ()):
                    loads.append(
                        start
                        + [row["combination"], row["scope"], row["normal_force_kn"], row["self_weight_kn"]]
                        + [None] * 6
                        + [None]
                    )
                if not panel.get("combinations"):
                    loads.append(start + [None, panel.get("reason")] + [None] * 9)
                for v in shell["panel_zones"]:
                    if v["member"] != panel["member"]:
                        continue
                    for zone, action in v["zones"].items():
                        loads.append(start + [v["combination"], zone, None, None, *action, None])
                    if "opening_edge_kn_knm" in v:
                        edge_label = v["opening_face"] + " edge subtotal (includes both end corners)"
                        loads.append(
                            start
                            + [v["combination"], edge_label, None, None, *v["opening_edge_kn_knm"], None]
                        )
                    if "residual_kn_knm" in v:
                        loads.append(
                            start
                            + [
                                v["combination"],
                                "Free-body residual",
                                None,
                                None,
                                *v["residual_kn_knm"],
                                v["balanced"],
                            ]
                        )
    if not sections and not frames and not loads:
        return {}
    return {
        "7.19": {
            "title": "Wall sections at openings",
            "columns": location
            + [
                "Side",
                "Wall IDs",
                "Net area (m²)",
                "0.35 Ac fck (kN)",
                "Force source",
                "Force z (m)",
                "Combination",
            ]
            + global_axes
            + ["Reference axial ratio", "Control z (m)", "Max control ΔF (kN)", "Max control ΔM (kN·m)"],
            "rows": sections,
            "note": " ".join(sorted(bases))
            + " Native actions use the printed mesh elevation. The recovered section integrates unaveraged element-corner fields at the opening. At each mesh control plane the bilinear load projection assigns one quarter of each rectangular element's uniform pressure and self-weight to each corner. The remaining difference measures agreement after these translational loads.",
        },
        "7.20": {
            "title": "Frame actions at opening jambs",
            "columns": location
            + ["Physical point", "Column", "Action", "Combination"]
            + local_axes
            + ["Source status"],
            "rows": frames,
            "note": "Signed static actions share one physical station and the frame local axes. A jump is the total change across the joint. Seismic intervals enclose each component separately.",
        },
        "7.21": {
            "title": "Opening panel loads and transfer",
            "columns": location
            + ["Panel", "Combination", "Load or joint zone", "Normal load (kN)", "Downward weight (kN)"]
            + global_axes
            + ["Balanced"],
            "rows": loads,
            "note": "Loads act on the changed panel. Native zones assign each element corner once, with corner nodes listed separately from edge interiors. Global moments use the midpoint of the changed panel ends at the opening elevation.",
        },
    }
