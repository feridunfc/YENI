"""Same-corner membrane, bending and transverse shear resistance of orthogonal wall curtains."""
from math import floor, hypot, isfinite, pi, sqrt

from .basement_pier_geometry import required
from .wall_shell_section import _basis

# Project selection reserve for proposed curtains. Unity is the resistance limit.
SELECTION_LIMIT = .85


def corner_states(panel, item, combinations):
    from .wall_pressure_shell import directional_actions
    direction = panel["width_direction"]
    matrices = {elm: _basis(matrix, (direction[1], -direction[0], 0.))
                for elm, matrix in item["axes"].items()}
    groups = {}
    for name, spec in combinations.items():
        steps = item["cases"][name]
        if set(steps) == {"Min", "Max"}:
            lows, highs = steps["Min"], steps["Max"]
        else:
            required(not spec["spectral"] and len(steps) == 1 and next(iter(steps)) in ("", "Static", "Single Value"),
                     "SIGNED_STATIC_OR_NATIVE_SPECTRAL_INTERVAL_REQUIRED")
            lows = highs = next(iter(steps.values()))
        required(len(lows) == len(highs) == len(item["corners"]), "MEMBRANE_CORNER_POPULATION_MISMATCH")
        states = []
        for (elm, pt), lo, hi in zip(item["corners"], lows, highs):
            required(len(lo) == len(hi) == 8 and all(isfinite(x) and isfinite(y) and x <= y
                     for x, y in zip(lo, hi)), "ALL_EIGHT_NATIVE_SHELL_RESULTANTS_REQUIRED")
            required(spec["spectral"] or all(abs(a-b) <= 1e-9 + 1e-10*max(abs(a),abs(b)) for a,b in zip(lo,hi)),
                     "STATIC_MEMBRANE_AND_PLATE_STEP_MISMATCH")
            basis = matrices[elm]
            membrane = directional_actions(basis, direction, [*lo[:3],0.,0.], [*hi[:3],0.,0.])[:3]
            plate = directional_actions(basis, direction, lo[3:], hi[3:])
            states.append((elm, pt, membrane, plate))
        groups[name] = states
    return groups


def required_face_forces(membrane, moments, face_sign, arm_m):
    """Face steel ties plus a negative-semidefinite concrete stress tensor in equilibrium."""
    ranges = []
    for (nl, nu), (ml, mu) in zip(membrane, moments):
        # CSI's positive moment compresses positive local 3.
        a, b = -face_sign*ml/arm_m, -face_sign*mu/arm_m
        ranges.append((nl/2+min(a,b), nu/2+max(a,b)))
    nx, ny, shear = ranges
    tau = max(abs(v) for v in shear)
    steel_h, steel_v = max(0., nx[1]+tau), max(0., ny[1]+tau)
    cx, cy = max(-nx[0], tau), max(-ny[0], tau)
    compression = .5*(cx+cy+hypot(cx-cy, 2*tau))
    return steel_h, steel_v, compression


def layer_demands(groups, arm_mm, thickness, fcd_cracked, shear_strength):
    """Envelope only after combining all eight components at an identified physical corner."""
    out = {}
    for name, states in groups.items():
        peaks = [None]*4
        for elm, point, membrane, plate in states:
            transverse = hypot(max(map(abs,plate[3])), max(map(abs,plate[4])))
            faces = {side:required_face_forces(membrane,plate[:3],side,arm_mm/1000) for side in (-1,1)}
            # Compression fields change with the load and location. At this same corner,
            # centre the two equal face zones on the tie planes and reserve a separate core.
            c = max(f[2] for f in faces.values())/fcd_cracked
            q = transverse/shear_strength
            minimum = min(.5,thickness-arm_mm,arm_mm/2)
            face_t = min(thickness-arm_mm,arm_mm-minimum,
                         max(minimum,arm_mm*c/(c+q) if c+q else arm_mm/2))
            core_t = arm_mm-face_t
            for face, ties in faces.items():
                for i, value in enumerate((*ties,transverse)):
                    capacity = (face_t*fcd_cracked if i==2 else core_t*shear_strength if i==3 else None)
                    score = value/capacity if capacity else value
                    if peaks[i] is None or score > peaks[i]["score"]:
                        peaks[i] = {"demand_kn_m":value,"score":score,"concrete_resistance_kn_m":capacity,
                                    "concrete_face_mm":face_t,"core_mm":core_t,"element":elm,"point":point,
                                    "local_3_face":face if i != 3 else 0,
                                    "membrane_intervals_kn_m":membrane,"moment_intervals_knm_m":plate[:3],
                                    "transverse_intervals_kn_m":plate[3:]}
        out[name] = peaks
    return out


def check_curtains(states, cache, thickness, horizontal, vertical, material, offset, *, vertical_offset_mm=None):
    vertical_offset = offset-(horizontal["diameter_mm"]+vertical["diameter_mm"])/2 if vertical_offset_mm is None else vertical_offset_mm
    if vertical_offset_mm is not None:
        required(0 < vertical_offset <= (thickness-vertical["diameter_mm"])/2, "VERTICAL_CURTAIN_OUTSIDE_SECTION")
    arm = 2*min(offset, vertical_offset)
    required(0 < arm < thickness, "SANDWICH_REINFORCEMENT_ARM_INVALID")
    # The equivalent ties at the inner arm can be distributed to actual symmetric
    # layers at a larger arm by nonnegative weights (1 +/- inner/actual)/2.
    fcd_cracked = .6*(1-material.fck/250)*material.fcd
    fctd = .35*sqrt(material.fck)*material.fcd/material.fck
    required(fcd_cracked > 0 and fctd > 0, "SANDWICH_CONCRETE_STRENGTH_INVALID")
    if arm not in cache:
        cache[arm] = layer_demands(states,arm,thickness,fcd_cracked,.65*fctd)
    peaks = cache[arm]
    horizontal_area = horizontal["guaranteed_bars_per_m"]*pi*horizontal["diameter_mm"]**2/4
    vertical_area = floor(1000/vertical["pitch_mm"]+1e-9)*pi*vertical["diameter_mm"]**2/4
    resistance = (horizontal_area*material.fyd/1000, vertical_area*material.fyd/1000)
    required(min(resistance)>0, "SANDWICH_LAYER_RESISTANCE_INVALID")
    actions = ("Horizontal steel","Vertical steel","Face concrete compression","Core transverse shear")
    checks = []
    for name, values in peaks.items():
        for i, entry in enumerate(values):
            capacity = resistance[i] if i < 2 else entry["concrete_resistance_kn_m"]
            checks.append({"combination":name,"action":actions[i],
                           **{k:v for k,v in entry.items() if k not in {"score","concrete_resistance_kn_m"}},
                           "resistance_kn_m":capacity,"utilization":entry["demand_kn_m"]/capacity})
    steel = max(r["utilization"] for r in checks if r["action"] in actions[:2])
    governing = max(checks,key=lambda r:r["utilization"])
    return {"method":"EQUILIBRATED_TWO_FACE_SANDWICH_UNCRACKED_CORE", "lever_arm_mm":arm,
            "concrete_face_mm":governing["concrete_face_mm"], "core_mm":governing["core_mm"], "cracked_concrete_limit_mpa":fcd_cracked,
            "core_shear_limit_mpa":.65*fctd, "steel_selection_limit":SELECTION_LIMIT,
            "steel_max":steel, "governing":governing, "checks":checks,
            "satisfied":governing["utilization"] <= 1. and steel <= SELECTION_LIMIT}
