"""VS23 finite beam proposals and signed N=0 rectangular-section references.

Uses the accepted strain-compatible section kernel; no fixed-50-mm cover,
clamped compression block, required-As-as-provided shortcut or SCWB approval.
"""
from copy import deepcopy
from functools import lru_cache
import math

from .section_capacity import Bar,Material,Section,_Curve,number,FORCE_TOL_N,MOMENT_ABS_TOL_NMM,MOMENT_REL_TOL

DIAMETERS=(16,20,24)
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


def proposed_beam_cage(profile,target_top_mm2,target_bottom_mm2,diameter):
    """Three declared diameters; minimum integer counts to cover source targets.

    A target is an area envelope, not a concurrent force vector or provided
    reinforcement. No bar diameter is selected automatically as the design.
    """
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
