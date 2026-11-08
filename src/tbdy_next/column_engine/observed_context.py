"""Observed member context adapted from Column-Engine 4f0afbeb, r6_member_context.

Retains its native signatures, units and distinction between model settings
and a physical bar cage. Station/length/axis engineering is owned by YENI.
"""
from __future__ import annotations

import math
from .native_archive import BankError, native_observation

CONTEXT_SCHEMA = 'tbdy.column-workflow.r6-d3-member-context.v1'
# exact (API, kind, name) matches are necessary: a section name is not a frame.
REQUIRED = {
    'frame_section': ('FrameObj.GetSection', 'frame'),
    'frame_axes': ('FrameObj.GetLocalAxes', 'frame'),
    'frame_endpoints': ('FrameObj.GetPoints', 'frame'),
    'frame_label': ('FrameObj.GetLabelFromName', 'frame'),
    'section_rectangle': ('PropFrame.GetRectangle', 'frame_section'),
    'section_rebar': ('PropFrame.GetRebarColumn', 'column_section'),
    'concrete': ('PropMaterial.GetOConcrete', 'material'),
    'steel': ('PropMaterial.GetORebar_1', 'material'),
}
EXPECTED_FIELDS = {
    'FrameObj.GetSection': ('PropName', 'SAuto', 'pRetVal'),
    'FrameObj.GetLocalAxes': ('Ang', 'Advanced', 'pRetVal'),
    'FrameObj.GetPoints': ('Point1', 'Point2', 'pRetVal'),
    'FrameObj.GetLabelFromName': ('Label', 'Story', 'pRetVal'),
    'PropFrame.GetRectangle': ('FileName', 'MatProp', 'T3', 'T2', 'Color', 'notes', 'GUID', 'pRetVal'),
    'PropFrame.GetRebarColumn': ('MatPropLong', 'MatPropConfine', 'Pattern', 'ConfineType',
                               'Cover', 'NumberCBars', 'NumberR3Bars', 'NumberR2Bars',
                               'RebarSize', 'TieSize', 'TieSpacingLongit', 'Number2DirTieBars',
                               'Number3DirTieBars', 'ToBeDesigned', 'pRetVal'),
    'PropMaterial.GetOConcrete': ('Fc', 'IsLightweight', 'FcsFactor', 'SSType', 'SSHysType',
                                 'StrainAtFc', 'StrainUltimate', 'FrictionAngle',
                                 'DilatationalAngle', 'pRetVal'),
    'PropMaterial.GetORebar_1': ('FY', 'Fu', 'EFy', 'EFu', 'SSType', 'SSHysType',
                               'StrainAtHardening', 'StrainUltimate', 'FinalSlope',
                               'UseCaltransSSDefaults', 'pRetVal'),
}


def _finite_positive(value, tag):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise BankError('R6_D3_INVALID_POSITIVE:' + tag)
    return value


def _required_string(value, tag):
    if type(value) is not str or not value or len(value) > 200:
        raise BankError('R6_D3_INVALID_NAME:' + tag)
    return value


def _lookup(index, api, kind, name):
    matches = index.get((api, kind, name), [])
    if len(matches) > 1:
        raise BankError('R6_D3_AMBIGUOUS_NATIVE_CALL:' + api + ':' + name)
    return matches[0] if matches else None


def _observation(z, manifest, index, api, kind, name):
    item = _lookup(index, api, kind, name)
    if item is None or item.get("status") != "OBSERVED":
        return None
    return native_observation(z, manifest, item, api, kind, name, EXPECTED_FIELDS[api])

def _member_context(z, manifest, index, frame):
    refs = {}
    missing = []

    def take(tag, name, *, ref_key=None):
        api, kind = REQUIRED[tag]
        observed = _observation(z, manifest, index, api, kind, name)
        if observed is None:
            missing.append(tag)
            return None
        val, ref = observed
        refs[ref_key or tag] = ref
        return val

    sec = take('frame_section', frame)
    axes = take('frame_axes', frame)
    ends = take('frame_endpoints', frame)
    label = take('frame_label', frame)
    section_name = _required_string(sec['PropName'], 'section') if sec else None
    rect = take('section_rectangle', section_name) if section_name else None
    rebar = take('section_rebar', section_name) if section_name else None
    concrete_name = _required_string(rect['MatProp'], 'concrete') if rect else None
    long_name = _required_string(rebar['MatPropLong'], 'longitudinal_material') if rebar else None
    conf_name = _required_string(rebar['MatPropConfine'], 'confinement_material') if rebar else None
    concrete = take('concrete', concrete_name) if concrete_name else None
    steel = take('steel', long_name) if long_name else None
    # Keep the same material for longitudinal and confinement when recorded.
    if conf_name and conf_name != long_name:
        conf = take('steel', conf_name, ref_key='confinement_steel')
        if conf is None:
            missing.append('confinement_steel_material')

    geometry = None
    material = None
    rebar_configuration = None
    if rect:
        b3 = _finite_positive(rect['T3'], 'T3')
        b2 = _finite_positive(rect['T2'], 'T2')
        geometry = {'section_name': section_name,
                    'T3_native_m': b3, 'T2_native_m': b2,
                    'T3_cm': round(100*b3, 9), 'T2_cm': round(100*b2, 9),
                    'source_unit_system': 'kN-m-C',
                    'coordinate_system': 'ETABS_SECTION_LOCAL_2_3',
                    'construction_geometry_qualified': False}
    if concrete:
        fc = _finite_positive(concrete['Fc'], 'concrete_fc')
        material = {'concrete_name': concrete_name, 'fc_native_kN_per_m2': fc,
                    'fc_MPa': round(fc/1000, 9),
                    'longitudinal_grade_name': long_name,
                    'confinement_grade_name': conf_name,
                    'material_grade_verified_in_model_only': True,
                    'constructed_material_properties_qualified': False}
    if steel:
        fy = _finite_positive(steel['FY'], 'rebar_fy')
        if material is None:
            material = {'concrete_name': concrete_name,
                        'constructed_material_properties_qualified': False}
        material.update({'fy_native_kN_per_m2': fy, 'fy_MPa': round(fy/1000,9)})
    if rebar:
        if type(rebar['ToBeDesigned']) is not bool:
            raise BankError('R6_D3_TOBEDESIGNED_INVALID')
        if type(rebar['Pattern']) is not int or type(rebar['ConfineType']) is not int:
            raise BankError('R6_D3_REBAR_ENUM_INVALID')
        cover = _finite_positive(rebar['Cover'], 'cover')
        tiespace = _finite_positive(rebar['TieSpacingLongit'], 'tie_spacing')
        rebar_configuration = {
            'intent': 'DESIGN_SETTING_NOT_AS_BUILT',
            'to_be_designed': rebar['ToBeDesigned'],
            'analysis_workflow_hint': ('TO_BE_DESIGNED' if rebar['ToBeDesigned'] else 'EXISTING_REINFORCEMENT'),
            'hint_is_model_setting_not_as_built': True,
            'pattern_code': rebar['Pattern'], 'confinement_type_code': rebar['ConfineType'],
            'cover_native_m': cover,
            'cover_cm': round(cover*100,9),
            'tie_spacing_native_m': tiespace, 'tie_spacing_cm': round(tiespace*100,9),
            'number_corner_bars_setting': rebar['NumberCBars'],
            'number_R3_bars_setting': rebar['NumberR3Bars'],
            'number_R2_bars_setting': rebar['NumberR2Bars'],
            'longitudinal_bar_size_label': str(rebar['RebarSize']),
            'tie_size_label': str(rebar['TieSize']),
            'number_dir2_tie_bars_setting': rebar['Number2DirTieBars'],
            'number_dir3_tie_bars_setting': rebar['Number3DirTieBars'],
            'actual_bar_coordinates': None, 'actual_bar_areas': None,
            'physical_cage_qualified': False,
        }
    frame_context = {'section_assigned': section_name,
                     'story_label': label['Story'] if label else None,
                     'column_label': label['Label'] if label else None,
                     'point_i_id': ends['Point1'] if ends else None,
                     'point_j_id': ends['Point2'] if ends else None,
                     'local_axis_angle_deg': axes['Ang'] if axes else None,
                     'advanced_axes_setting': axes['Advanced'] if axes else None,
                     'local_axis_matrix_qualified': False}
    if axes:
        if (type(axes['Ang']) not in (float,int) or not math.isfinite(axes['Ang'])
                or type(axes['Advanced']) is not bool):
            raise BankError('R6_D3_FRAME_AXES_INVALID')
    if ends:
        for key in ('Point1','Point2'):
            _required_string(ends[key], key)
        if ends['Point1'] == ends['Point2']:
            raise BankError('R6_D3_FRAME_ENDPOINTS_COLLAPSE')
    if label:
        _required_string(label['Label'],'frame_label')
        _required_string(label['Story'],'story_label')
    return {'schema': CONTEXT_SCHEMA,
            'frame_name': frame, 'state': 'OBSERVED_CONFIGURATION_UNQUALIFIED' if not missing else 'PARTIAL_OBSERVATION',
            'missing_native_calls': sorted(set(missing)), 'frame': frame_context,
            'geometry': geometry, 'material': material,
            'rebar_configuration': rebar_configuration,
            'source_calls': refs,
            'full_eng_qualification': False,
            'as_built_geometry_qualified': False,
            'as_built_bar_cage_qualified': False,
            'source_model_generation_qualified': False,
            'joint_topology_qualified': False,
            'ready_for_pmm_design': False}
