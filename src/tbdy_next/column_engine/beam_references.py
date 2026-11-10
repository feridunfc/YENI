"""VS23: native-cut beam design-area provenance and conditional cage references.

Only beams incident to the recorded column-joint graph are targeted. Both
object ends are retained. Duplicate/rounded/foreign source rows never become
a maximum-area fallback. The source ZIP and SQLite database stay read-only.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from dataclasses import asdict
import math

from .beam_capacity import DIAMETERS,POLICY,proposed_beam_cage
from .column_joints import GEOMETRY_TOL
from .column_pmm import _native
from .column_prechecks import _number
from .column_stability import OPTIONAL_ERRORS
from .csi_geometry import AXIS_CONVENTION
from .native_archive import BankError,digest,finite,identity
from .section_capacity import Material
from .source_bank import _read_forces,_definitions

SCHEMA='tbdy.next.beam-end-capacity-scenarios.v1'
AREA_FIELDS=('AsMinTop','AsTop','AsMinBot','AsBot','totTopRebar','totBotRebar','TLngRebar')
TABLE_FIELDS=('Story','Label','UniqueName','DesignSect','Station','Status','AsTopCombo','AsBotCombo','TLngCombo','WarnMsg','ErrMsg',*AREA_FIELDS)
REBAR_FIELDS=('MatPropLong','MatPropConfine','CoverTop','CoverBot','TopLeftArea','TopRightArea','BotLeftArea','BotRightArea','pRetVal')
REFERENCES={
    'beam_cover':'https://docs.csiamerica.com/help-files/etabs-api-2016/html/45d94bde-0567-8528-d8cf-daea0b892a8c.htm',
    'beam_summary':'https://docs.csiamerica.com/help-files/etabs-api-2016/html/c3556046-fd3f-4559-7659-966eb731ea4c.htm',
    'spacing':'https://staff.emu.edu.tr/cemalgenes/Documents/courses/INSA471_2019_20_Bahar/TS500.pdf',
    'legacy_compared':'https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/design/core/capacity_design.py'}
OPEN_BASIS=['PROPOSALS_NOT_SELECTED_OR_AS_BUILT','N_ZERO_IS_A_DECLARED_SCENARIO_NOT_SOURCE_N',
    'SIDE_COVER_AND_TIE_DIAMETER_ARE_PROPOSALS','AGGREGATE_AND_FULL_DETAILING_NOT_BOUND',
    'TORSION_SIDE_BARS_ANCHORAGE_AND_CONTINUITY_NOT_DESIGNED','SLAB_AND_PHYSICAL_JOINT_FACES_NOT_BOUND',
    'SEISMIC_COMPATIBLE_ND_AND_SCWB_SIGN_ASSEMBLY_NOT_BOUND','NO_NORMATIVE_SCWB_AUTHORITY']


def station_budget(a,b,length):
    """Machine arithmetic only: 64 ULP, at most 1e-9 m; not display rounding."""
    values=[finite(v,'station') for v in (a,b,length)]
    return min(1e-9,64*math.ulp(max(1.0,*(abs(v) for v in values))))


def _at_cut(value,target,length):
    return abs(value-target)<=station_budget(value,target,length)


def _table_source(archive):
    names=sorted(name for api,kind,name in archive.index if api=='DatabaseTables.GetTableForDisplayArray'
        and kind=='table' and isinstance(name,str) and name.startswith('Concrete Beam Design Summary - '))
    if len(names)!=1:raise BankError('BEAM_DESIGN_TABLE_NOT_UNIQUE_OR_MISSING')
    observed=archive.table(names[0],TABLE_FIELDS,required_units={'Station':'m',**{key:'m2' for key in AREA_FIELDS}})
    if observed is None:raise BankError('BEAM_DESIGN_TABLE_NOT_OBSERVED')
    rows,proof=observed;grouped=defaultdict(list)
    for index,row in enumerate(rows):
        name=identity(row['UniqueName'],'beam_unique_name')
        grouped[name].append({'row_index':index,'values':row,'source_row_id':'BEAM-DESIGN-'+digest(
            {'archive':archive.sha256,'call':proof['call_id'],'index':index,'values':row})[:24]})
    return grouped,proof


def _profile(frame,archive):
    g=frame['geometry']
    if g is None:raise BankError(frame['geometry_reason'] or 'BEAM_GEOMETRY_NOT_BOUND')
    axes=g['axes_global']
    if abs(axes[0][2])>GEOMETRY_TOL or abs(axes[1][2]-1)>GEOMETRY_TOL:
        raise BankError('BEAM_HORIZONTAL_LOCAL2_UP_SCENARIO_NOT_BOUND')
    name=frame['frame_id'];assigned,assignment=_native(archive,'FrameObj.GetSection','frame',name)
    section=identity(assigned['PropName'],'beam_section');rect,rectangle=_native(archive,'PropFrame.GetRectangle','frame_section',section)
    observed=archive.native('PropFrame.GetRebarBeam','beam_section',section,REBAR_FIELDS)
    if observed is None:raise BankError('BEAM_REBAR_SETTING_NOT_OBSERVED')
    rebar,rebar_source=observed
    concrete,concrete_source=_native(archive,'PropMaterial.GetOConcrete','material',identity(rect['MatProp'],'concrete'))
    steel,steel_source=_native(archive,'PropMaterial.GetORebar_1','material',identity(rebar['MatPropLong'],'longitudinal_steel'))
    if concrete['IsLightweight'] is not False:raise BankError('BEAM_NORMALWEIGHT_CONCRETE_NOT_BOUND')
    h,b=(float(_number(rect[k],k)*1000) for k in ('T3','T2'))
    if (section,h,b)!=(g['section']['section_name'],g['section']['local2_extent_mm'],g['section']['local3_extent_mm']):
        raise BankError('BEAM_SECTION_GEOMETRY_BINDING_MISMATCH')
    fc,fy=(float(_number(value,key)/1000) for value,key in ((concrete['Fc'],'Fc'),(steel['FY'],'FY')))
    material=Material(fc,fc/POLICY['gamma_concrete'],fy/POLICY['gamma_steel'])
    result={'section_name':section,'local2_height_mm':h,'local3_width_mm':b,
        'cover_top_centroid_mm':float(_number(rebar['CoverTop'],'CoverTop')*1000),
        'cover_bottom_centroid_mm':float(_number(rebar['CoverBot'],'CoverBot')*1000),
        'cover_basis':POLICY['cover_basis'],'material':asdict(material),'concrete_material':rect['MatProp'],
        'steel_material':rebar['MatPropLong'],'source_calls':{'rectangle':rectangle,'rebar_setting':rebar_source,
            'concrete':concrete_source,'steel':steel_source},'model_overrides_used_as_provided':False}
    result['profile_id']='BEAM-PROFILE-'+digest(result)[:24]
    return result,assignment


def _end_source(frame,end,states,force_source,offsets,design_rows,table_source,controls):
    g=frame['geometry'];length=finite(g['length_m'],'length')
    values,offset_source=offsets;i,j=(finite(values[k],k) for k in ('Length1','Length2'))
    if min(i,j)<0 or i+j>=length:raise BankError('BEAM_END_OFFSETS_INVALID')
    if length-j-i<=2*station_budget(i,length-j,length):raise BankError('BEAM_END_MATCH_WINDOWS_OVERLAP')
    target=i if end=='I' else length-j
    native=[s for s in states if _at_cut(s.values[1],target,length)]
    keys=sorted({s.station_key for s in native})
    matches=[]
    for item in design_rows:
        station=float(_number(item['values']['Station'],'Station'))
        if station<0 or station>length+station_budget(station,length,length):raise BankError('BEAM_DESIGN_STATION_OUTSIDE_MEMBER')
        if _at_cut(station,target,length):matches.append(item)
    result={'target_station_m':target,'native_cut_count':len(keys),'design_match_count':len(matches),
        'native_cut_keys':[dict(zip(('Obj','ObjSta','Elm','ElmSta'),key)) for key in keys],
        'native_force_source':force_source,'offset_source':offset_source,'table_source':table_source,
        'design_matches':deepcopy(matches),'native_source_row_indices':[s.source_row_index for s in native],
        'station_match_policy':'64_ULP_CAPPED_1E_MINUS9_M_NO_DISPLAY_ROUNDING',
        'maximum_station_difference_m':max([abs(k[1]-target) for k in keys]+[abs(float(_number(m['values']['Station'],'Station'))-target) for m in matches],default=None),
        'native_vectors_used_as_design_demand':False,'source_cut_is_physical_joint_face':False,
        'status':'BEAM_END_SOURCE_BLOCKED','reason':None,'targets':None}
    if len(keys)!=1:result['reason']='BEAM_NATIVE_CUT_AMBIGUOUS' if keys else 'BEAM_NATIVE_CUT_NOT_FOUND';return result
    if len(matches)!=1:result['reason']='BEAM_DESIGN_STATION_AMBIGUOUS' if matches else 'BEAM_DESIGN_STATION_NOT_FOUND';return result
    row=matches[0]['values']
    if row['DesignSect']!=g['section']['section_name']:result['reason']='BEAM_DESIGN_SECTION_MISMATCH';return result
    if any(row[k]!='No Message' for k in ('Status','ErrMsg','WarnMsg')):
        result['reason']='BEAM_DESIGN_MESSAGE_NOT_CLEAR';return result
    areas={key:float(_number(row[key],key)*1000000) for key in AREA_FIELDS}
    if min(areas.values())<0:result['reason']='BEAM_REQUIRED_AREA_NEGATIVE';return result
    references={}
    for key in ('AsTopCombo','AsBotCombo','TLngCombo'):
        name=identity(row[key],key);control=controls.get(name)
        if not control or control['status']!='OBSERVED':
            result['reason']='BEAM_CONTROL_REFERENCE_NOT_BOUND';return result
        references[key]={**deepcopy(control),'name':name,'native_output_observed_at_cut':name in {s.output_case for s in native}}
    result.update(status='BEAM_END_SOURCE_BOUND',targets={
        'top_mm2':max(areas[k] for k in ('AsTop','AsMinTop','totTopRebar')),
        'bottom_mm2':max(areas[k] for k in ('AsBot','AsMinBot','totBotRebar')),
        'source_areas_mm2':areas,'top_combination':row['AsTopCombo'],'bottom_combination':row['AsBotCombo'],
        'torsion_combination':row['TLngCombo'],'same_force_vector_claimed':False,
        'control_references':references,
        'total_required_area_is_provided':False,'torsion_cage_layout_designed':False})
    return result


def build_beam_references(chain,joints,archive):
    for item in (chain,joints):
        if (item['source_archive_sha256']!=archive.sha256 or item['source_run_id']!=chain['source_run_id']
                or item['formal_compliance']!='NOT_PROVEN' or item['design_demand_authority']!='DENIED'
                or item['engineering_release']!='NOT_READY'):raise BankError('BEAM_REFERENCE_SOURCE_OR_AUTHORITY_MISMATCH')
    if (joints['axis_convention']!=AXIS_CONVENTION or joints['source_demand_result_sha256']!=chain['result_sha256']
            or joints['selected_design'] is not None or joints['physical_joint_population_proven'] is not False):
        raise BankError('BEAM_REFERENCE_PARENT_SCOPE_MISMATCH')
    graph=joints['graph'];bound=graph['status']=='NATIVE_ENDPOINT_GRAPH_BOUND'
    if graph['status'] not in ('NATIVE_ENDPOINT_GRAPH_BOUND','BLOCKED_INPUTS'):raise BankError('BEAM_UNKNOWN_GRAPH_STATUS')
    frames={f['frame_id']:f for f in graph['frames']};nodes={n['point_id']:n for n in graph['nodes']}
    if len(frames)!=len(graph['frames']) or len(nodes)!=len(graph['nodes']):raise BankError('BEAM_DUPLICATE_GRAPH_IDENTITY')
    selected={r['member_id'] for r in joints['rows']}
    end_keys=[(r['member_id'],r['end']) for r in joints['rows']]
    if (len(selected)!=joints['selected_member_count'] or len(end_keys)!=2*len(selected)
            or set(end_keys)!={(name,end) for name in selected for end in ('I','J')}):
        raise BankError('BEAM_PARENT_COLUMN_POPULATION_MISMATCH')
    if bound:
        if any(name not in frames or frames[name]['design_orientation']!=1 for name in selected):
            raise BankError('BEAM_PARENT_SELECTED_COLUMNS_NOT_BOUND')
        if set(nodes)!={frames[name][key] for name in selected for key in ('point_i','point_j')}:
            raise BankError('BEAM_PARENT_JOINT_POPULATION_MISMATCH')
    elif frames or nodes or graph['points']:raise BankError('BEAM_PARTIAL_GRAPH_NOT_QUALIFIED')
    incident=set();columns={}
    for node in nodes.values():
        actual=[(r['frame_id'],r['end']) for r in node['incident_frames']]
        expected={(f['frame_id'],end) for f in frames.values() for end,key in (('I','point_i'),('J','point_j')) if f[key]==node['point_id']}
        if set(actual)!=expected or len(actual)!=len(expected):raise BankError('BEAM_INCOMPLETE_JOINT_ROSTER')
        columns[node['point_id']]=sorted(f['frame_id'] for f in frames.values() if f['design_orientation']==1 and node['point_id'] in (f['point_i'],f['point_j']))
        incident.update((name,end) for name,end in actual if frames[name]['design_orientation']==2)
    targeted=sorted({name for name,end in incident});all_beams={f['frame_id'] for f in frames.values() if f['design_orientation']==2}
    table_status='BEAM_DESIGN_TABLE_BOUND';table_reason=None;table_source=None;groups={}
    try:groups,table_source=_table_source(archive)
    except OPTIONAL_ERRORS as exc:table_status='BEAM_DESIGN_TABLE_BLOCKED';table_reason=str(exc)
    inventory=defaultdict(list)
    for item in archive.jsonlines('force-inventory.jsonl'):inventory[item.get('frame_name')].append(item)
    cases,combinations=_definitions(archive)
    controls={name:{'kind':kind,'status':item['status'],'definition_source':item.get('source'),'reason':item.get('reason')}
        for kind,items in (('CASE',cases),('COMBINATION',combinations)) for name,item in items.items()}
    rows=[];profiles={}
    for name in targeted:
        frame=frames[name];profile=None;assignment=None;member_reason=None;states=[];force_source=None;offsets=None
        try:
            profile,assignment=_profile(frame,archive);profiles[profile['profile_id']]=profile
            if len(inventory[name])!=1:raise BankError('BEAM_FORCE_INVENTORY_NOT_UNIQUE_OR_MISSING')
            states,force_source=_read_forces(archive,name,inventory[name][0])
            offsets=archive.native('FrameObj.GetEndLengthOffset','frame',name,('AutoOffset','Length1','Length2','RZ','pRetVal'))
            if offsets is None:raise BankError('BEAM_END_OFFSETS_NOT_OBSERVED')
        except OPTIONAL_ERRORS as exc:member_reason=str(exc)
        for end in ('I','J'):
            point=frame['point_'+end.lower()]
            row={'member_id':name,'end':end,'point_id':point,'incident_to_column_joint':(name,end) in incident,
                'adjacent_column_ids':columns.get(point,[]),'profile_id':profile['profile_id'] if profile else None,
                'assignment_source':assignment,'source':None,'status':'BEAM_END_SOURCE_BLOCKED','reason':member_reason or table_reason,
                'candidates':[],'formal_compliance':'NOT_PROVEN','final_design_eligible':False}
            try:
                if row['reason']:raise BankError(row['reason'])
                row['source']=_end_source(frame,end,states,force_source,offsets,groups.get(name,[]),table_source,controls)
                row.update(status=row['source']['status'],reason=row['source']['reason'])
            except OPTIONAL_ERRORS as exc:row['reason']=str(exc)
            for diameter in DIAMETERS:
                proposal={'diameter_mm':diameter,'status':'BEAM_PROPOSAL_BLOCKED','reason':row['reason'],
                    'selected_design':False,'physical_cage_proven':False,'final_design_eligible':False,'capacity':None}
                if row['status']=='BEAM_END_SOURCE_BOUND':
                    targets=row['source']['targets']
                    try:proposal=proposed_beam_cage(profile,targets['top_mm2'],targets['bottom_mm2'],diameter)
                    except OPTIONAL_ERRORS as exc:proposal['reason']=str(exc)
                proposal['candidate_id']='BEAM-CAGE-'+digest({'archive':archive.sha256,'member':name,'end':end,'proposal':proposal})[:24]
                row['candidates'].append(proposal)
            row['end_id']='BEAM-END-'+digest({'archive':archive.sha256,'member':name,'end':end})[:24];rows.append(row)
        ends=rows[-2:]
        if all(row['status']=='BEAM_END_SOURCE_BOUND' for row in ends):
            if ends[0]['source']['native_cut_keys']==ends[1]['source']['native_cut_keys']:
                raise BankError('BEAM_IJ_CUT_IDENTITIES_NOT_DISTINCT')
    result={'schema':SCHEMA,'axis_convention':AXIS_CONVENTION,'policy':deepcopy(POLICY),'source_run_id':chain['source_run_id'],
        'source_archive_sha256':archive.sha256,'source_demand_result_sha256':chain['result_sha256'],
        'source_joints_result_sha256':joints['result_sha256'],'graph_status':graph['status'],'graph_reason':graph['reason'],
        'source_population_status':'NATIVE_JOINT_GRAPH_BOUND' if bound else 'BLOCKED_NATIVE_JOINT_GRAPH',
        'known_column_count':joints['selected_member_count'],'native_beam_count':len(all_beams) if bound else None,
        'target_beam_count':len(targeted) if bound else None,'expected_end_count':len(targeted)*2 if bound else None,
        'expected_incident_end_count':len(incident) if bound else None,'source_end_count':len(rows),
        'source_bound_end_count':sum(r['status']=='BEAM_END_SOURCE_BOUND' for r in rows),
        'incident_bound_end_count':sum(r['status']=='BEAM_END_SOURCE_BOUND' and r['incident_to_column_joint'] for r in rows),
        'expected_candidate_count':len(targeted)*2*len(DIAMETERS) if bound else None,
        'calculated_candidate_count':sum(c['status']=='BEAM_PROPOSAL_CALCULATED' for r in rows for c in r['candidates']),
        'candidate_status_counts':dict(sorted(Counter(c['status'] for r in rows for c in r['candidates']).items())),
        'source_reason_counts':dict(sorted(Counter(r['reason'] for r in rows if r['reason']).items())),
        'outside_joint_scope_beams':[{'member_id':name,'reason':'NO_NATIVE_END_AT_RECORDED_COLUMN_JOINT'} for name in sorted(all_beams-set(targeted))],
        'profiles':list(profiles.values()),'rows':rows,'table_status':table_status,'table_reason':table_reason,'table_source':table_source,
        'source_row_count':table_source['row_count'] if table_source else None,'unknown_source_members':sorted(set(groups)-all_beams) if bound else None,
        'member_id_filter':None,'source_population_reduced':False,'selected_design':None,'actual_or_selected_beam_capacity_bound':False,
        'scwb_ratio':None,'formal_compliance':'NOT_PROVEN','design_demand_authority':'DENIED','engineering_release':'NOT_READY',
        'references':REFERENCES.copy(),'open_basis':OPEN_BASIS.copy()}
    result['result_sha256']=digest(result);return result


def beam_projection(result,member_id=None):
    rows=[r for r in result['rows'] if member_id is None or member_id in r['adjacent_column_ids']]
    profile_ids={r['profile_id'] for r in rows}
    return deepcopy({**result,'rows':rows,'member_id_filter':member_id,'filtered_end_count':len(rows),
        'filtered_bound_end_count':sum(r['status']=='BEAM_END_SOURCE_BOUND' for r in rows),
        'profiles':[p for p in result['profiles'] if p['profile_id'] in profile_ids]})
