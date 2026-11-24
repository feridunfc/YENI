"""Present the governing operands already stored by the wall calculation owners."""

from math import isclose, isfinite


HEADERS = ["Check", "Governing combination", "Physical cut or joint", "Forces or design demand",
           "Resistance and calculation", "Utilization (%)"]
CHECKS = {"axial": "Net-area axial", "shear": "Design shear", "horizontal_joint": "Horizontal joint friction",
          "pmm": "Section PMM", "wall_beam": "Wall–beam flexural strength"}


def _number(value):
    return isinstance(value, (float, int)) and isfinite(value)


def _fmt(value):
    return f"{value:.2f}" if _number(value) else "unrecorded"


def _interval(values):
    if isinstance(values, (list, tuple)) and len(values) == 2:
        return f"[{_fmt(values[0])}, {_fmt(values[1])}]"
    return "unrecorded"


def _cut(members, face, z=None):
    name = ", ".join(str(m) for m in members)
    where = " ".join(part for part in (name, face) if part)
    return f"{where} (z = {_fmt(z)} m)" if _number(z) else where


def _shear(section, rect):
    detail = rect.get("reinforcement") or {}
    identity = ("member", "story", "face", "combination")
    control = next((r for r in rect.get("seismic_shear", ())
                    if all(r.get(key) == section.get(key) for key in identity)), {})
    # Keep every tied height assumption on the branch producing the reported ratio.
    # The highest demand and lowest resistance need not belong to the same branch.
    matches = {}
    for height, branch in section.get("height_branches", {}).items():
        for kind in ("solid", "coupled"):
            ve = (branch.get(kind) or {}).get("ve_upper_kn")
            vr, strut = detail.get("vr_kn"), detail.get(kind + "_strut_limit_kn")
            if all(_number(x) for x in (ve, vr, strut)) and min(vr, strut) > 0:
                if isclose(ve / min(vr, strut), section["shear_upper_ratio"], rel_tol=1e-12):
                    matches.setdefault((kind, ve, vr, strut), []).append(height)
    if not matches:
        return None
    demand, resistance = [], []
    for (kind, ve, vr, strut), heights in matches.items():
        labels = ", ".join(name.replace("_", " ").lower() for name in heights)
        demand.append(f"{kind} branch ({labels}), Ve ≤ {_fmt(ve)} kN")
        resistance.append(f"{kind}: min(web Vr {_fmt(vr)}, strut {_fmt(strut)}) = {_fmt(min(vr, strut))} kN")
    if control.get("control_combination"):
        demand.append(f"control {control['control_combination']}, D = {_fmt(control.get('d'))}")
    return (" / ".join(demand), "Ve / limiting resistance. " + " / ".join(resistance))


def _operands(key, summary, group, rect, basement):
    combo, face, ratio = summary.get("combination"), summary.get("face"), summary["ratio"]
    members = group.get("members") or []
    story = group.get("story")

    if key == "axial":
        for cut in group.get("cuts", ()):
            if (cut.get("combination") == combo and cut.get("face") == face
                    and str(cut.get("role", "")).startswith("ASSIGNED_") and cut.get("axial_ratio") == ratio):
                force = f"Compression {_fmt(cut.get('compression_kn'))} kN, N = −P {_interval(cut.get('axial_interval_kn'))} kN"
                basis = {"SIGNED_STATIC": "signed static", "COMPONENT_ENVELOPE": "component envelope"}.get(cut.get("force_basis"))
                if basis:
                    force += f" ({basis})"
                geometry = (group.get("faces") or {}).get(face) or {}
                method = f"Ncompression / (0.35 fck Anet). Axial limit {_fmt(cut.get('axial_limit_kn'))} kN."
                if _number(geometry.get("net_m2")):
                    method += f" Net concrete area {_fmt(geometry['net_m2'])} m²."
                return _cut(geometry.get("members", ()), face, geometry.get("z_m")), force, method
    if key == "pmm" and basement:
        for cut in basement.get("cuts", ()):
            if (cut.get("role") == "WALL_STRENGTH" and cut.get("combination") == combo
                    and cut.get("face") == face and cut.get("pmm_upper") == ratio):
                webs = [web for web in cut.get("web_demands", ()) if web.get("member") in members and web.get("pmm_upper") == ratio]
                if webs:
                    forces = [f"Web {v['member']}: N {_interval(v.get('nd_kn'))} kN, |M2| ≤ {_fmt(v.get('m2_upper_knm'))}, "
                              f"|M3| ≤ {_fmt(v.get('m3_upper_knm'))} kN·m" for v in webs]
                    return (_cut([v["member"] for v in webs], face), " / ".join(forces),
                            "Maximum net-web PMM interaction bound over its axial and moment intervals.")
        return None
    if key in ("shear", "pmm"):
        for cut in rect.get("seismic_sections", ()):
            if (cut.get("combination") != combo or cut.get("face") != face
                    or cut.get("story") != story or cut.get("member") not in members):
                continue
            where = _cut([cut["member"]], face, cut.get("z_m"))
            if key == "shear" and cut.get("shear_upper_ratio") == ratio:
                operands = _shear(cut, rect)
                if operands:
                    return (where, *operands)
            pmm = cut.get("pmm") or {}
            if key == "pmm" and pmm.get("upper_utilization") == ratio:
                force = (f"N (compression positive) {_interval(cut.get('nd_interval_kn'))} kN, |M2| ≤ {_fmt(cut.get('m2_design_knm'))}, "
                         f"|M3| ≤ {_fmt(cut.get('m3_design_knm'))} kN·m")
                cell = pmm.get("governing_cell") or {}
                method = "Proposed cage. Maximum of min(|M2|/Mr2, |M3|/Mr3) over the axial and angle cells."
                if cell:
                    method += (f" Governing cell: N {_interval(cell.get('axial_cell_kn'))} kN, "
                               f"angle {_interval(cell.get('angle_interval_deg'))}°, "
                               f"Mr2 and Mr3 lower bounds {_interval(cell.get('moment_component_floors_knm'))} kN·m.")
                return where, force, method
    if key == "horizontal_joint":
        for joint in rect.get("construction_joints", ()):
            if (joint.get("combination") == combo and joint.get("story") == story
                    and joint.get("upper_member") in members and joint.get("upper_utilization") == ratio):
                faces = ", ".join(_cut([m], f) for m, f in joint.get("faces", ()))
                return (_cut([faces], None, joint.get("z_m")),
                        f"In-plane Ve ≤ {_fmt(joint.get('ve_in_plane_upper_kn'))} kN, tension ≤ {_fmt(joint.get('tension_upper_kn'))} kN",
                        f"Ve / joint resistance {_fmt(joint.get('resistance_kn'))} kN. Minimum of rough concrete and steel "
                        f"{_fmt(joint.get('roughened_concrete_and_steel_kn'))}, wall limit {_fmt(joint.get('tbdy_7_19_concrete_cap_kn'))} "
                        f"and joint concrete limit {_fmt(joint.get('ts500_8_1_7_concrete_cap_kn'))} kN. "
                        f"μ = {_fmt(joint.get('mu'))}, available crossing steel {_fmt(joint.get('available_friction_steel_mm2'))} mm².")
    if key == "wall_beam":
        for joint in rect.get("strong_wall_connections", ()):
            if (joint.get("combination") == combo and joint.get("story") == story and joint.get("lower_member") in members
                    and joint.get("upper_utilization") == ratio):
                faces = ", ".join(_cut([w["member"]], w.get("face")) for w in joint.get("wall_terms", ()))
                beams = ", ".join(f"{end['beam']}/{end['face']}" for end in joint.get("selected_beam_ends", ()))
                return (_cut([faces], None, joint.get("z_m")),
                        f"1.2 Σ beam-end Mr = {_fmt(joint.get('required_mr_knm'))} kN·m. Beam ends {beams}.",
                        f"Required moment / Σ wall Mr (lower bound) {_fmt(joint.get('mr_wall_lower_knm'))} kN·m.")
    return None


def wall_design_calculations(sections):
    """Retain the owner's pier, storey, face, role and combination for each overview cell."""
    if not sections or not (sections.get("batch") or {}).get("rows"):
        return None
    rectangular = {p["pier"]: p for p in sections.get("piers", ())}
    basements = {(p["pier"], p["story"]): p for p in sections.get("basement_piers", ())}
    groups = []
    for group in sections["batch"]["rows"]:
        pier, story = group.get("pier"), group.get("story")
        design = group.get("design") or {}
        entries = []
        for key, label in CHECKS.items():
            summary = ((group.get("assigned") or {}) if key == "axial" else design).get(key) or {}
            ratio = summary.get("ratio")
            if not _number(ratio):
                source_reason = (group.get("area_reason") or group.get("material_reason")) if key == "axial" else None
                reason = group.get("reason") or source_reason or design.get("reason") or "No governing result recorded for this check."
                entries.append([label, None, None, None, reason, None])
                continue
            operands = _operands(key, summary, group, rectangular.get(pier, {}), basements.get((pier, story)))
            if operands is None:
                operands = (_cut(group.get("members", ()), summary.get("face")), None, "Governing operands unavailable in this saved result.")
            entries.append([label, summary.get("combination"), *operands, _fmt(100 * ratio)])
        groups.append({"pier": pier, "story": story, "members": group.get("members", []), "rows": entries})
    return {"headers": HEADERS, "groups": groups}
