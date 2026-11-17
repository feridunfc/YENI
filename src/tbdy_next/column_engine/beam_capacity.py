"""VS23 finite beam proposals and signed N=0 rectangular-section references.

Uses the accepted strain-compatible section kernel; no fixed-50-mm cover,
clamped compression block, required-As-as-provided shortcut or SCWB approval.
Supports explicit single-row block (BLOCKED_UNSUPPORTED_LAYOUT) and multi-row
placement (CHK-132) when allow_multi_row=True (F13).
"""
from copy import deepcopy
from functools import lru_cache
import math

from .section_capacity import Bar,Material,Section,_Curve,number,FORCE_TOL_N,MOMENT_ABS_TOL_NMM,MOMENT_REL_TOL

DIAMETERS=(16,20,24)
BLOCKED_UNSUPPORTED_LAYOUT="BLOCKED_UNSUPPORTED_LAYOUT"
POLICY={"id":"VS23_SINGLE_ROW_PHI16_20_24_SOURCE_AREA_TARGET_N0_V1","diameters_mm":list(DIAMETERS),
    "default_display_diameter_mm":20,"side_clear_cover_to_tie_mm":30,"tie_diameter_mm":10,
    "gamma_concrete":1.5,"gamma_steel":1.15,"minimum_bars_per_face":2,
    "cover_basis":"CSI_FACE_TO_LONGITUDINAL_GROUP_CENTROID","minimum_spacing_without_aggregate_mm":25,
    "spacing_reference":"TS500_9_5_2","aggregate_max_mm":None,
    "axial_force_scenario_n":0,"source_beam_axial_force_applied":False,
    "automatic_design_selection":False,"candidate_population_exhaustive":False,
    "physical_cage_proven":False,"torsion_and_side_bars_designed":False,"slab_participation_applied":False}


@lru_cache(maxsize=512)
def _signed_capacity(section):
    if not isinstance(section,Section):raise ValueError('BEAM_SECTION_REQUIRED')
    bars={(b.x2,b.x3,b.area) for b in section.bars}
    if any((x,-y,a) not in bars for x,y,a in bars):raise ValueError('BEAM_WIDTH_SYMMETRY_REQUIRED')
    result={"status":"BEAM_CAPACITY_REFERENCE","positive_m3_knm":None,"negative_m3_knm":None,
        "axial_force_scenario_n":0,"source_beam_axial_force_applied":False,"points":[],
        "maximum_tensile_strain_limit":.1,"continuous_error_bound_proven":False,"final_design_eligible":False}
    for sign,angle,key in ((1,0,'positive_m3_knm'),(-1,180,'negative_m3_knm')):
        point,reason=_Curve(section,angle).solve(0)
        trace={'rotation_sign':sign,'angle_deg':angle,'point':point,'reason':reason,'tolerance_knm':None}
        if point is not None:
            magnitude=sign*point['m3_nmm'];residual=abs(point['n_n'])
            tolerance=MOMENT_ABS_TOL_NMM+MOMENT_REL_TOL*abs(magnitude)+FORCE_TOL_N*math.hypot(section.t2,section.t3)/2
            if magnitude<=tolerance or residual>FORCE_TOL_N or abs(point['m2_nmm'])>MOMENT_ABS_TOL_NMM:
                trace['reason']='BEAM_PRINCIPAL_PLANE_NOT_RESOLVED'
            else:
                result[key]=point['m3_nmm']/1e6;trace['tolerance_knm']=tolerance/1e6
        result['points'].append(trace)
    if result['positive_m3_knm'] is None or result['negative_m3_knm'] is None:result['status']='BEAM_CAPACITY_UNRESOLVED'
    return result


def signed_beam_capacity(section):
    """Local +2 compression gives +M3; width symmetry only, N=0 explicitly."""
    return deepcopy(_signed_capacity(section))


def _split_into_symmetric_rows(total_bars: int, max_per_row: int, max_rows: int) -> list[int] | None:
    """Split total_bars into up to max_rows layers, each with 2 <= n <= max_per_row."""
    if total_bars < 2 or max_per_row < 2 or max_rows < 1:
        return None
    if total_bars <= max_per_row:
        return [total_bars]
    rows: list[int] = []
    remaining = total_bars
    while remaining > 0:
        if len(rows) >= max_rows:
            return None
        take = min(max_per_row, remaining)
        if remaining - take == 1:
            # Avoid leaving a 1-bar inner layer, which cannot be placed at both corners symmetrically
            take -= 1
        if take < 2:
            return None
        rows.append(take)
        remaining -= take
    return rows


def propose_beam_cage_chk132(
    profile,
    target_top_mm2,
    target_bottom_mm2,
    diameter,
    *,
    allow_multi_row: bool = False,
    max_rows_per_face: int = 3,
    vertical_clear_spacing_mm: float = 25.0,
):
    """F13 / CHK-132: Beam bar layout returning BLOCKED_UNSUPPORTED_LAYOUT when single-row
    is exceeded and allow_multi_row=False, or multi-row layout and capacity when allow_multi_row=True.
    """
    single = proposed_beam_cage(profile, target_top_mm2, target_bottom_mm2, diameter)
    if single["status"] == "BEAM_PROPOSAL_CALCULATED":
        return {
            **single,
            "check_id": "CHK-132",
            "layout_mode": "SINGLE_ROW",
            "top_row_counts": [single["top_count"]],
            "bottom_row_counts": [single["bottom_count"]],
        }
    if not allow_multi_row:
        return {
            **single,
            "check_id": "CHK-132",
            "status": BLOCKED_UNSUPPORTED_LAYOUT,
            "layout_mode": "SINGLE_ROW_EXCEEDED",
        }
    h, b = (number(profile[k], k, positive=True) for k in ("local2_height_mm", "local3_width_mm"))
    top, bottom = (number(profile[k], k, positive=True) for k in ("cover_top_centroid_mm", "cover_bottom_centroid_mm"))
    v_clear = max(float(diameter), number(vertical_clear_spacing_mm, "vertical_clear_spacing_mm", positive=True), 25.0)
    tie = POLICY["tie_diameter_mm"]
    side = POLICY["side_clear_cover_to_tie_mm"]
    half = b / 2 - side - tie - diameter / 2
    spacing_ref = max(diameter, 25)
    if half <= 0 or min(top, bottom) < side + tie + diameter / 2:
        return {
            **single,
            "check_id": "CHK-132",
            "status": BLOCKED_UNSUPPORTED_LAYOUT,
            "layout_mode": "UNFIT_GEOMETRY",
        }
    max_per_row = int(math.floor((2 * half + 1e-9) / (diameter + spacing_ref))) + 1
    top_rows = _split_into_symmetric_rows(single["top_count"], max_per_row, max_rows_per_face)
    bot_rows = _split_into_symmetric_rows(single["bottom_count"], max_per_row, max_rows_per_face)
    if top_rows is None or bot_rows is None:
        return {
            **single,
            "check_id": "CHK-132",
            "status": BLOCKED_UNSUPPORTED_LAYOUT,
            "reason": "BEAM_MULTI_ROW_COUNT_EXCEEDS_MAX_ROWS",
            "layout_mode": "MULTI_ROW_EXCEEDED",
        }
    layer_pitch = diameter + v_clear
    top_x2 = [h / 2 - (top + r_idx * layer_pitch) for r_idx in range(len(top_rows))]
    bot_x2 = [-h / 2 + (bottom + r_idx * layer_pitch) for r_idx in range(len(bot_rows))]
    opposite_gap = min(top_x2) - max(bot_x2) - diameter
    if opposite_gap < spacing_ref:
        return {
            **single,
            "check_id": "CHK-132",
            "status": BLOCKED_UNSUPPORTED_LAYOUT,
            "reason": "BEAM_MULTI_ROW_OPPOSITE_FACE_CLEAR_SPACING_BELOW_REFERENCE",
            "opposite_face_clear_spacing_mm": opposite_gap,
            "layout_mode": "MULTI_ROW_EXCEEDED",
        }
    area = math.pi * diameter ** 2 / 4
    bars_list = []
    horiz_spacings = []
    for x2_coord, n_bars in [*zip(top_x2, top_rows), *zip(bot_x2, bot_rows)]:
        horiz_spacings.append(2 * half / (n_bars - 1) - diameter)
        for i in range(n_bars):
            bars_list.append(Bar(x2_coord, (2 * i - (n_bars - 1)) * half / (n_bars - 1), area))
    bars = tuple(bars_list)
    min_spacing = min([opposite_gap, v_clear, *horiz_spacings])
    section = Section(h, b, bars, Material(**profile["material"]))
    cap = signed_beam_capacity(section)
    max_layers = max(len(top_rows), len(bot_rows))
    eff_top = sum((top + idx * layer_pitch) * cnt for idx, cnt in enumerate(top_rows)) / sum(top_rows)
    eff_bot = sum((bottom + idx * layer_pitch) * cnt for idx, cnt in enumerate(bot_rows)) / sum(bot_rows)
    out = {
        **single,
        "check_id": "CHK-132",
        "layout_mode": "TWO_ROW" if max_layers == 2 else ("MULTI_ROW" if max_layers > 2 else "SINGLE_ROW"),
        "top_row_counts": top_rows,
        "bottom_row_counts": bot_rows,
        "vertical_clear_spacing_mm": v_clear,
        "effective_top_centroid_mm": eff_top,
        "effective_bottom_centroid_mm": eff_bot,
        "opposite_face_clear_spacing_mm": opposite_gap,
        "minimum_clear_spacing_mm": min_spacing,
        "bars": [{"x2_mm": bar.x2, "x3_mm": bar.x3, "area_mm2": bar.area, "diameter_mm": diameter} for bar in bars],
        "top_clear_cover_to_tie_mm": top - tie - diameter / 2,
        "bottom_clear_cover_to_tie_mm": bottom - tie - diameter / 2,
        "area_reference_status": "SOURCE_AREA_TARGETS_COVERED",
        "spacing_status": "AGGREGATE_NOT_BOUND",
        "reason": None,
        "capacity": cap,
        "status": "BEAM_PROPOSAL_CALCULATED" if cap["status"] == "BEAM_CAPACITY_REFERENCE" else "BEAM_PROPOSAL_NUMERIC_UNRESOLVED",
    }
    return out


def proposed_beam_cage(profile,target_top_mm2,target_bottom_mm2,diameter,*,allow_multi_row:bool=False,max_rows_per_face:int=3,vertical_clear_spacing_mm:float=25.0):
    """Three declared diameters; minimum integer counts to cover source targets.

    A target is an area envelope, not a concurrent force vector or provided
    reinforcement. No bar diameter is selected automatically as the design.
    """
    if allow_multi_row:
        return propose_beam_cage_chk132(
            profile,
            target_top_mm2,
            target_bottom_mm2,
            diameter,
            allow_multi_row=True,
            max_rows_per_face=max_rows_per_face,
            vertical_clear_spacing_mm=vertical_clear_spacing_mm,
        )
    if type(diameter) is not int or diameter not in DIAMETERS:raise ValueError('BEAM_PROPOSAL_DIAMETER_INVALID')
    targets=[number(v,'required_area') for v in (target_top_mm2,target_bottom_mm2)]
    if min(targets)<0:raise ValueError('BEAM_REQUIRED_AREA_NEGATIVE')
    h,b=(number(profile[k],k,positive=True) for k in ('local2_height_mm','local3_width_mm'))
    top,bottom=(number(profile[k],k,positive=True) for k in ('cover_top_centroid_mm','cover_bottom_centroid_mm'))
    area=math.pi*diameter**2/4
    counts=[max(POLICY['minimum_bars_per_face'],math.ceil(v/area)) for v in targets]
    row={'diameter_mm':diameter,'top_count':counts[0],'bottom_count':counts[1],
        'top_label':f'{counts[0]}Φ{diameter}','bottom_label':f'{counts[1]}Φ{diameter}',
        'target_top_mm2':targets[0],'target_bottom_mm2':targets[1],
        'area_top_mm2':counts[0]*area,'area_bottom_mm2':counts[1]*area,'bars':[],
        'top_source_area_ratio':counts[0]*area/targets[0] if targets[0] else None,
        'bottom_source_area_ratio':counts[1]*area/targets[1] if targets[1] else None,
        'minimum_clear_spacing_mm':None,'spacing_reference_mm':max(diameter,25),
        'status':'BEAM_PROPOSAL_BLOCKED','reason':None,'capacity':None,
        'selected_design':False,'physical_cage_proven':False,'final_design_eligible':False}
    tie=POLICY['tie_diameter_mm'];side=POLICY['side_clear_cover_to_tie_mm']
    half=b/2-side-tie-diameter/2
    if max(counts)>100 or half<=0 or min(top,bottom)<side+tie+diameter/2 or top+bottom+diameter>=h:
        row['reason']='BEAM_SINGLE_ROW_CAGE_DOES_NOT_FIT';return row
    # The extreme bars on opposite faces share the same width coordinates.
    # Their vertical gap is therefore part of the minimum, even for 2+2 bars.
    opposite_gap=h-top-bottom-diameter
    spacing=min(opposite_gap,*(2*half/(n-1)-diameter for n in counts))
    row['opposite_face_clear_spacing_mm']=opposite_gap
    row['minimum_clear_spacing_mm']=spacing
    if spacing<row['spacing_reference_mm']:
        row['reason']='BEAM_SINGLE_ROW_SPACING_BELOW_REFERENCE';return row
    bars=tuple(Bar(x,(2*i-(n-1))*half/(n-1),area)
        for x,n in ((h/2-top,counts[0]),(-h/2+bottom,counts[1])) for i in range(n))
    section=Section(h,b,bars,Material(**profile['material']))
    row.update(bars=[{'x2_mm':bar.x2,'x3_mm':bar.x3,'area_mm2':bar.area,'diameter_mm':diameter} for bar in bars],
        top_clear_cover_to_tie_mm=top-tie-diameter/2,bottom_clear_cover_to_tie_mm=bottom-tie-diameter/2,
        area_reference_status='SOURCE_AREA_TARGETS_COVERED',spacing_status='AGGREGATE_NOT_BOUND',
        capacity=signed_beam_capacity(section),status='BEAM_PROPOSAL_CALCULATED')
    if row['capacity']['status']!='BEAM_CAPACITY_REFERENCE':row['status']='BEAM_PROPOSAL_NUMERIC_UNRESOLVED'
    return row


SELECTED_LONG_DIAMETERS = (12, 14, 16, 20, 22, 24, 25)


def _place_selected_face_bars(
    *,
    b_mm: float,
    h_mm: float,
    face_cover_mm: float,
    tie_mm: float,
    side_cover_mm: float,
    cont_count: int,
    cont_d: int,
    add_count: int,
    add_d: int,
    is_top: bool,
    max_rows_per_face: int,
    vertical_clear_spacing_mm: float,
) -> tuple[list[tuple[float, float, float, int]], list[str], float, float | None] | tuple[None, None, str, None]:
    """Place continuous corner bars + symmetric additional bars on one face (single or multi-row)."""
    sign_x2 = 1.0 if is_top else -1.0
    half_cont = b_mm / 2.0 - side_cover_mm - tie_mm - cont_d / 2.0
    half_add = b_mm / 2.0 - side_cover_mm - tie_mm - add_d / 2.0
    s_ref = max(25.0, float(cont_d), float(add_d))
    if half_cont <= 0 or half_add <= 0 or face_cover_mm < side_cover_mm + tie_mm + max(cont_d, add_d) / 2.0:
        return None, None, "BEAM_SELECTED_CAGE_COVER_OR_WIDTH_UNFIT", None

    row0_inner_d = max(cont_d, add_d)
    # Continuous bars beyond the 2 corners occupy inner slots on Row 0 alongside additional bars
    inner_cont = max(0, cont_count - 2)
    inner_clear_0 = 2.0 * half_cont - cont_d
    # Reserve inner continuous bars first on Row 0, then fill Row 0 additional bars up to clear-spacing limit
    k_max_add_row0 = int(
        math.floor((inner_clear_0 - inner_cont * cont_d - (inner_cont + 1) * s_ref + 1e-9) / (add_d + s_ref))
    )
    if inner_cont > 0 and (inner_cont * cont_d + (inner_cont + 1) * s_ref) > inner_clear_0 + 1e-9:
        return None, None, "BEAM_SELECTED_CONTINUOUS_COUNT_EXCEEDS_ROW_WIDTH", None
    k_row0_add = min(add_count, max(0, k_max_add_row0))
    rem_add = add_count - k_row0_add
    extra_rows: list[int] = []
    if rem_add > 0:
        if rem_add == 1 and k_row0_add >= 1:
            k_row0_add -= 1
            rem_add = 2
        max_inner_row = int(math.floor((2.0 * half_add + 1e-9) / (add_d + s_ref))) + 1
        split = _split_into_symmetric_rows(rem_add, max_inner_row, max(0, max_rows_per_face - 1))
        if split is None:
            return None, None, "BEAM_SELECTED_REBAR_EXCEEDS_MAX_ROWS_OR_SPACING", None
        extra_rows = split

    v_clear = max(25.0, float(vertical_clear_spacing_mm), float(cont_d), float(add_d))
    row0_x2 = sign_x2 * (h_mm / 2.0 - face_cover_mm)
    area_cont = math.pi * (cont_d ** 2) / 4.0
    area_add = math.pi * (add_d ** 2) / 4.0

    coords: list[tuple[float, float, float, int]] = [
        (row0_x2, round(-half_cont, 9), area_cont, cont_d),
        (row0_x2, round(half_cont, 9), area_cont, cont_d),
    ]
    # Build ordered inner bars for Row 0 symmetrically around center
    inner_items = [(cont_d, area_cont)] * inner_cont + [(add_d, area_add)] * k_row0_add
    horiz_spacings: list[float] = []
    if not inner_items:
        horiz_spacings.append(2.0 * half_cont - cont_d)
    else:
        n_in = len(inner_items)
        # Check spacing using symmetric arrangement: put continuous first evenly or additional evenly
        gap_0 = (inner_clear_0 - sum(d for d, _ in inner_items)) / (n_in + 1)
        horiz_spacings.append(gap_0)
        # Construct strictly symmetric pairs (pairs from outer to inner, odd center if needed)
        if inner_cont > 0 and inner_cont % 2 == 1 and k_row0_add % 2 == 1:
            return None, None, "BEAM_SELECTED_ASYMMETRIC_ODD_MIX_CANNOT_MIRROR", None
        half_pairs: list[tuple[int, float]] = [(cont_d, area_cont)] * (inner_cont // 2) + [(add_d, area_add)] * (k_row0_add // 2)
        center_item = (cont_d, area_cont) if inner_cont % 2 == 1 else ((add_d, area_add) if k_row0_add % 2 == 1 else None)
        cursor = -half_cont + cont_d / 2.0 + gap_0
        for d_bar, a_bar in half_pairs:
            y_pos = round(cursor + d_bar / 2.0, 9)
            coords.append((row0_x2, y_pos, a_bar, d_bar))
            coords.append((row0_x2, -y_pos, a_bar, d_bar))
            cursor += d_bar + gap_0
        if center_item is not None:
            coords.append((row0_x2, 0.0, center_item[1], center_item[0]))

    total_area_face = cont_count * area_cont + add_count * area_add
    weighted_cov = (cont_count * area_cont + k_row0_add * area_add) * face_cover_mm
    layer_covs = [face_cover_mm]
    prev_cov = face_cover_mm
    prev_max_d = max(cont_d, add_d) if k_row0_add > 0 else cont_d
    for idx, n_bars in enumerate(extra_rows, start=1):
        layer_cov = prev_cov + (prev_max_d + add_d) / 2.0 + v_clear
        layer_covs.append(layer_cov)
        prev_cov = layer_cov
        prev_max_d = add_d
        layer_x2 = sign_x2 * (h_mm / 2.0 - layer_cov)
        horiz_spacings.append(2.0 * half_add / (n_bars - 1) - add_d)
        for i in range(n_bars // 2):
            y_pos = round((2 * i - (n_bars - 1)) * half_add / (n_bars - 1), 9)
            coords.append((layer_x2, y_pos, area_add, add_d))
            coords.append((layer_x2, -y_pos, area_add, add_d))
        if n_bars % 2 == 1:
            coords.append((layer_x2, 0.0, area_add, add_d))
        weighted_cov += n_bars * area_add * layer_cov

    min_spacing = min(horiz_spacings + ([v_clear] if extra_rows else []))
    eff_centroid = weighted_cov / total_area_face
    row_labels = [f"{cont_count}Φ{cont_d}" + (f"+{k_row0_add}Φ{add_d}" if k_row0_add else "")] + [
        f"{n}Φ{add_d}" for n in extra_rows
    ]
    if min_spacing < s_ref - 1e-6:
        return None, None, "BEAM_SELECTED_REBAR_SPACING_BELOW_REFERENCE", min_spacing
    return coords, row_labels, str(eff_centroid), min_spacing


def build_selected_beam_cage(
    profile: dict,
    *,
    top_continuous_count: int = 2,
    top_continuous_diameter_mm: int = 12,
    top_additional_count: int = 0,
    top_additional_diameter_mm: int = 16,
    bottom_continuous_count: int = 2,
    bottom_continuous_diameter_mm: int = 14,
    bottom_additional_count: int = 0,
    bottom_additional_diameter_mm: int = 16,
    target_top_mm2: float = 0.0,
    target_bottom_mm2: float = 0.0,
    tie_diameter_mm: int = 8,
    max_rows_per_face: int = 3,
    vertical_clear_spacing_mm: float = 25.0,
) -> dict:
    """Build and verify a mixed-diameter symmetric engineer-selected beam section (N=0 signed M3)."""
    for d in (top_continuous_diameter_mm, top_additional_diameter_mm, bottom_continuous_diameter_mm, bottom_additional_diameter_mm):
        if type(d) is not int or d not in SELECTED_LONG_DIAMETERS:
            raise ValueError("BEAM_SELECTED_DIAMETER_INVALID")
    if min(top_continuous_count, bottom_continuous_count) < 2 or min(top_additional_count, bottom_additional_count) < 0:
        raise ValueError("BEAM_SELECTED_BAR_COUNT_INVALID")
    if type(tie_diameter_mm) is not int or tie_diameter_mm < 8:
        raise ValueError("BEAM_SELECTED_TIE_DIAMETER_INVALID")
    t_top = number(target_top_mm2, "target_top_mm2")
    t_bot = number(target_bottom_mm2, "target_bottom_mm2")
    if min(t_top, t_bot) < 0:
        raise ValueError("BEAM_REQUIRED_AREA_NEGATIVE")

    h = number(profile["local2_height_mm"], "local2_height_mm", positive=True)
    b = number(profile["local3_width_mm"], "local3_width_mm", positive=True)
    cov_top = number(profile["cover_top_centroid_mm"], "cover_top_centroid_mm", positive=True)
    cov_bot = number(profile["cover_bottom_centroid_mm"], "cover_bottom_centroid_mm", positive=True)
    side = float(POLICY["side_clear_cover_to_tie_mm"])

    area_top = top_continuous_count * math.pi * top_continuous_diameter_mm ** 2 / 4.0 + top_additional_count * math.pi * top_additional_diameter_mm ** 2 / 4.0
    area_bot = bottom_continuous_count * math.pi * bottom_continuous_diameter_mm ** 2 / 4.0 + bottom_additional_count * math.pi * bottom_additional_diameter_mm ** 2 / 4.0

    def _face_label(cc, cd, ac, ad):
        return f"{cc}Φ{cd}" + (f" + {ac}Φ{ad}" if ac > 0 else "")

    top_label = _face_label(top_continuous_count, top_continuous_diameter_mm, top_additional_count, top_additional_diameter_mm)
    bot_label = _face_label(bottom_continuous_count, bottom_continuous_diameter_mm, bottom_additional_count, bottom_additional_diameter_mm)

    out = {
        "origin": "ENGINEER_SELECTED_BEAM_REBAR",
        "top_label": top_label,
        "bottom_label": bot_label,
        "top_continuous": {"count": top_continuous_count, "diameter_mm": top_continuous_diameter_mm},
        "top_additional": {"count": top_additional_count, "diameter_mm": top_additional_diameter_mm},
        "bottom_continuous": {"count": bottom_continuous_count, "diameter_mm": bottom_continuous_diameter_mm},
        "bottom_additional": {"count": bottom_additional_count, "diameter_mm": bottom_additional_diameter_mm},
        "tie_diameter_mm": tie_diameter_mm,
        "target_top_mm2": t_top,
        "target_bottom_mm2": t_bot,
        "area_top_mm2": area_top,
        "area_bottom_mm2": area_bot,
        "excess_top_mm2": area_top - t_top,
        "excess_bottom_mm2": area_bot - t_bot,
        "strictly_exceeds_targets": area_top > t_top and area_bot > t_bot,
        "covers_targets": area_top >= t_top and area_bot >= t_bot,
        "layout_mode": None,
        "top_row_labels": [],
        "bottom_row_labels": [],
        "effective_top_centroid_mm": None,
        "effective_bottom_centroid_mm": None,
        "minimum_clear_spacing_mm": None,
        "opposite_face_clear_spacing_mm": None,
        "bars": [],
        "capacity": None,
        "status": "BEAM_SELECTED_CAGE_BLOCKED",
        "reason": None,
    }

    top_res = _place_selected_face_bars(
        b_mm=b, h_mm=h, face_cover_mm=cov_top, tie_mm=float(tie_diameter_mm), side_cover_mm=side,
        cont_count=top_continuous_count, cont_d=top_continuous_diameter_mm,
        add_count=top_additional_count, add_d=top_additional_diameter_mm,
        is_top=True, max_rows_per_face=max_rows_per_face, vertical_clear_spacing_mm=vertical_clear_spacing_mm,
    )
    if top_res[0] is None:
        out["reason"] = str(top_res[2])
        return out
    bot_res = _place_selected_face_bars(
        b_mm=b, h_mm=h, face_cover_mm=cov_bot, tie_mm=float(tie_diameter_mm), side_cover_mm=side,
        cont_count=bottom_continuous_count, cont_d=bottom_continuous_diameter_mm,
        add_count=bottom_additional_count, add_d=bottom_additional_diameter_mm,
        is_top=False, max_rows_per_face=max_rows_per_face, vertical_clear_spacing_mm=vertical_clear_spacing_mm,
    )
    if bot_res[0] is None:
        out["reason"] = str(bot_res[2])
        return out

    t_coords, t_rows, t_eff_str, t_min_sp = top_res
    b_coords, b_rows, b_eff_str, b_min_sp = bot_res
    top_inner_edge = min(x2 - d / 2.0 for x2, _, _, d in t_coords)
    bot_inner_edge = max(x2 + d / 2.0 for x2, _, _, d in b_coords)
    opposite_gap = top_inner_edge - bot_inner_edge
    spacing_ref = max(25.0, float(top_continuous_diameter_mm), float(bottom_continuous_diameter_mm),
                      float(top_additional_diameter_mm if top_additional_count > 0 else 0),
                      float(bottom_additional_diameter_mm if bottom_additional_count > 0 else 0))
    if opposite_gap < spacing_ref - 1e-6:
        out["opposite_face_clear_spacing_mm"] = opposite_gap
        out["reason"] = "BEAM_SELECTED_OPPOSITE_FACE_CLEAR_SPACING_BELOW_REFERENCE"
        return out

    all_coords = [*t_coords, *b_coords]
    bars = tuple(Bar(x2, x3, area) for x2, x3, area, _ in all_coords)
    cap = signed_beam_capacity(Section(h, b, bars, Material(**profile["material"])))
    max_layers = max(len(t_rows), len(b_rows))
    out.update({
        "layout_mode": "TWO_ROW" if max_layers == 2 else ("MULTI_ROW" if max_layers > 2 else "SINGLE_ROW"),
        "top_row_labels": t_rows,
        "bottom_row_labels": b_rows,
        "effective_top_centroid_mm": float(t_eff_str),
        "effective_bottom_centroid_mm": float(b_eff_str),
        "opposite_face_clear_spacing_mm": opposite_gap,
        "minimum_clear_spacing_mm": min(float(t_min_sp), float(b_min_sp), opposite_gap),
        "bars": [{"x2_mm": x2, "x3_mm": x3, "area_mm2": area, "diameter_mm": d} for x2, x3, area, d in all_coords],
        "capacity": cap,
        "status": "BEAM_SELECTED_CALCULATED" if cap["status"] == "BEAM_CAPACITY_REFERENCE" else "BEAM_SELECTED_NUMERIC_UNRESOLVED",
    })
    return out
