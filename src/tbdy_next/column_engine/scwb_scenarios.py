"""VS24: explicit column/beam proposal combinations with joint-consistent signs.

The output case identifies the COLUMN source N only. Beam capacities remain
the independent VS23 N=0 proposal scenario; their area controls are not a
concurrent force state. No provided cage, physical-face transfer, earthquake
Nd minimum, code exemption or engineering SCWB approval is inferred.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from dataclasses import asdict
import math

from .beam_capacity import DIAMETERS
from .column_joints import GEOMETRY_TOL,_vertical
from .column_kinematics import _force_pair,SCHEMA as KINEMATICS_SCHEMA
from .column_scwb import LABELS,_joint_roster
from .column_prechecks import _number
from .column_stability import OPTIONAL_ERRORS
from .csi_geometry import AXIS_CONVENTION
from .joint_moment_signs import moment_sign_mapping,REFERENCE as SIGN_REFERENCE
from .native_archive import BankError,digest,finite
from .scwb_kernel import JointCase,MemberMomentCapacity,compute_scwb_joint_result,FACTOR

SCHEMA='tbdy.next.scwb-proposal-scenarios.v1'
POLICY='COMPLETE_JOINT_SAME_COLUMN_CASE_EXPLICIT_BEAM_N0_SIGNED_PROPOSALS_V1'
DEFAULT_COLUMN='16Φ24'
DEFAULT_BEAM=20
RELEASE_FIELDS=('II','JJ','StartValue','EndValue','pRetVal')
OPEN_BASIS=['PROPOSED_COLUMN_AND_BEAM_CAGES_NOT_SELECTED_OR_AS_BUILT',
    'BEAM_N_ZERO_NOT_A_CONCURRENT_COLUMN_LOAD_CASE','EARTHQUAKE_COMPATIBLE_COLUMN_ND_MINIMUM_NOT_BOUND',
    'PHYSICAL_JOINT_FACES_INSERTION_OFFSETS_AND_SLAB_PARTICIPATION_NOT_BOUND',
    'BEAM_TORSION_AGGREGATE_ANCHORAGE_AND_CONTINUITY_NOT_DESIGNED',
    'SECOND_ORDER_FINAL_DEMAND_AND_SCWB_EXCEPTION_APPLICABILITY_NOT_PROVEN']


def _validated(chain,joints,scwb,beams,archive):
    for result in (chain,joints,scwb,beams):
        if result['result_sha256']!=digest({k:v for k,v in result.items() if k!='result_sha256'}):
            raise BankError('SCENARIO_PARENT_CONTENT_HASH_MISMATCH')
        if (result['source_archive_sha256']!=archive.sha256 or result['source_run_id']!=chain['source_run_id']
                or result['formal_compliance']!='NOT_PROVEN' or result['design_demand_authority']!='DENIED'
                or result['engineering_release']!='NOT_READY'):
            raise BankError('SCENARIO_PARENT_SOURCE_OR_AUTHORITY_MISMATCH')
    if (scwb['schema']!='tbdy.next.scwb-source-references.v1' or beams['schema']!='tbdy.next.beam-end-capacity-scenarios.v1'
            or any(r['axis_convention']!=AXIS_CONVENTION or r['source_demand_result_sha256']!=chain['result_sha256']
                or r['selected_design'] is not None for r in (joints,scwb,beams))
            or scwb['source_cages_result_sha256']!=joints['source_cages_result_sha256']
            or any(r['source_joints_result_sha256']!=joints['result_sha256'] for r in (scwb,beams))
            or scwb['member_id_filter'] is not None or scwb['output_case_filter'] is not None or beams['member_id_filter'] is not None
            or scwb['actual_second_order_applied'] is not False or scwb['physical_joint_population_proven'] is not False
            or scwb['normative_exception_applied'] is not False or scwb['earthquake_compatible_minimum_proven'] is not False
            or beams['actual_or_selected_beam_capacity_bound'] is not False or beams['policy']['axial_force_scenario_n']!=0
            or beams['policy']['physical_cage_proven'] is not False or beams['scwb_ratio'] is not None
            or scwb['scenario_labels']!=list(LABELS) or beams['policy']['diameters_mm']!=list(DIAMETERS)):
        raise BankError('SCENARIO_PARENT_SCOPE_MISMATCH')
    graph=joints['graph'];bound=graph['status']=='NATIVE_ENDPOINT_GRAPH_BOUND'
    if graph['status'] not in ('NATIVE_ENDPOINT_GRAPH_BOUND','BLOCKED_INPUTS'):
        raise BankError('SCENARIO_UNKNOWN_GRAPH_STATUS')
    if scwb['graph_status']!=graph['status'] or beams['graph_status']!=graph['status']:
        raise BankError('SCENARIO_GRAPH_STATUS_MISMATCH')
    frames={f['frame_id']:f for f in graph['frames']};points={p['point_id']:p for p in graph['points']}
    nodes={n['point_id']:n for n in graph['nodes']}
    if any(len(index)!=len(graph[key]) for index,key in ((frames,'frames'),(points,'points'),(nodes,'nodes'))):
        raise BankError('SCENARIO_DUPLICATE_GRAPH_IDENTITY')
    if not bound and (frames or points or nodes):raise BankError('SCENARIO_PARTIAL_GRAPH_NOT_QUALIFIED')
    selected={r['member_id'] for r in joints['rows']}
    if (set(scwb['selected_member_ids'])!=selected or len(selected)!=joints['selected_member_count']
            or beams['known_column_count']!=len(selected)):
        raise BankError('SCENARIO_COLUMN_POPULATION_MISMATCH')
    if bound and set(nodes)!={frames[m][end] for m in selected for end in ('point_i','point_j')}:
        raise BankError('SCENARIO_JOINT_POPULATION_MISMATCH')
    old_nodes={n['point_id']:n for n in scwb['nodes']}
    if len(old_nodes)!=len(scwb['nodes']) or set(old_nodes)!=set(nodes):raise BankError('SCENARIO_PARENT_NODES_MISMATCH')
    incident=set()
    for name,node in nodes.items():
        expected={(f['frame_id'],end) for f in frames.values() for end,key in (('I','point_i'),('J','point_j')) if f[key]==name}
        actual=[(r['frame_id'],r['end']) for r in node['incident_frames']]
        if set(actual)!=expected or len(actual)!=len(expected):raise BankError('SCENARIO_INCOMPLETE_NATIVE_ROSTER')
        for direction in ('X','Y'):
            if old_nodes[name]['rosters'][direction]!=_joint_roster(node,direction,frames,points):
                raise BankError('SCENARIO_DIRECTION_ROSTER_MISMATCH')
        incident.update((member,end) for member,end in expected if frames[member]['design_orientation']==2)
    beam_index={(r['member_id'],r['end']):r for r in beams['rows']}
    expected_ends={(name,end) for name in {n for n,e in incident} for end in ('I','J')}
    if len(beam_index)!=len(beams['rows']) or set(beam_index)!=expected_ends:
        raise BankError('SCENARIO_BEAM_END_POPULATION_MISMATCH')
    for key,row in beam_index.items():
        if row['point_id']!=frames[key[0]]['point_'+key[1].lower()]:raise BankError('SCENARIO_BEAM_END_POINT_MISMATCH')
        if row['end_id']!='BEAM-END-'+digest({'archive':archive.sha256,'member':key[0],'end':key[1]})[:24]:
            raise BankError('SCENARIO_BEAM_END_ID_MISMATCH')
        if sorted(c['diameter_mm'] for c in row['candidates'])!=list(DIAMETERS):raise BankError('SCENARIO_BEAM_CANDIDATE_POPULATION_MISMATCH')
        for candidate in row['candidates']:
            expected_id='BEAM-CAGE-'+digest({'archive':archive.sha256,'member':key[0],'end':key[1],
                'proposal':{k:v for k,v in candidate.items() if k!='candidate_id'}})[:24]
            if candidate['candidate_id']!=expected_id:raise BankError('SCENARIO_BEAM_CANDIDATE_SOURCE_BINDING_MISMATCH')
    cases=sorted(c['combination'] for c in chain['combinations'] if c['classification']=='STATIC_LINEAR_ADD')
    if cases!=scwb['static_cases']:raise BankError('SCENARIO_STATIC_CASE_POPULATION_MISMATCH')
    keys=[(r['joint_id'],r['direction'],r['rotation_sign'],r['output_case'],r['candidate_label']) for r in scwb['rows']]
    expected={(node,d,s,case,label) for node in nodes for d in ('X','Y') for s in (-1,1) for case in cases for label in LABELS}
    if len(keys)!=len(expected) or set(keys)!=expected:raise BankError('SCENARIO_PARENT_CASE_POPULATION_MISMATCH')
    force_index=defaultdict(list);pairs={}
    for state in chain['candidates']:
        force_index[(state['native_key']['Obj'],state['native_key']['LoadCase'])].append(state)
    for ref in scwb['column_references']:
        name,end,case=ref['member_id'],ref['end'],ref['output_case'];state=ref['source_state']
        if state is None:
            if ref['capacity_knm'] is not None or ref['n_source_kn'] is not None or not ref['reason']:
                raise BankError('SCENARIO_COLUMN_SOURCE_STATE_MISSING')
            continue
        key=(name,case)
        if key not in pairs:
            observed=archive.native('FrameObj.GetEndLengthOffset','frame',name,('AutoOffset','Length1','Length2','RZ','pRetVal'))
            if observed is None or name not in frames:raise BankError('SCENARIO_COLUMN_NATIVE_END_CUTS_MISSING')
            values,proof=observed
            member={'station_geometry':{'native_facts':{'offsets':{'values':values,'source':proof}}}}
            pairs[key]=_force_pair(member,frames[name],force_index[key])
        expected_state=pairs[key][end.lower()]
        if (state!={k:expected_state[k] for k in ('state_id','source_row_id','native_key','native_values')}
                or state['native_key']['Obj']!=name or state['native_key']['LoadCase']!=case
                or ref['n_source_kn']!=-float(_number(state['native_values']['P'],'P')*1000)/1000
                or ref['source_force_pair_id']!='COLUMN-ENDS-'+digest({'schema':KINEMATICS_SCHEMA,'archive':archive.sha256,'member':name,'case':case})[:24]):
            raise BankError('SCENARIO_COLUMN_NATIVE_END_STATE_MISMATCH')
    return frames,points,old_nodes,beam_index,cases,bound


def _mapping(frame,end,joint_id,direction,sign,axis,archive,release_cache):
    row={'member_id':frame['frame_id'],'end':end,'joint_id':joint_id,'direction':direction,'rotation_sign':sign,
        'axis':axis,'status':'MEMBER_MOMENT_MAPPING_BLOCKED','reason':None,'mapping':None,
        'native_release_status':'NOT_OBSERVED','release_source':None,'release_values':None,
        'native_geometry_source':deepcopy(frame['source_calls']),'physical_moment_transfer_proven':False}
    try:
        if frame['point_'+end.lower()]!=joint_id:raise BankError('SCENARIO_NATIVE_END_POINT_MISMATCH')
        geometry=frame['geometry']
        if geometry is None:raise BankError(frame['geometry_reason'] or 'SCENARIO_GEOMETRY_NOT_BOUND')
        axes=geometry['axes_global']
        if frame['design_orientation']==1:_vertical(frame)
        elif frame['design_orientation']==2:
            if axis!='M3' or abs(axes[0][2])>GEOMETRY_TOL or abs(axes[1][2]-1)>GEOMETRY_TOL:
                raise BankError('SCENARIO_HORIZONTAL_BEAM_LOCAL2_UP_NOT_BOUND')
        else:raise BankError('SCENARIO_MEMBER_ROLE_NOT_BOUND')
        row['mapping']=moment_sign_mapping(axes,end,direction,sign,axis)
        row['transformation_source']=deepcopy(geometry['source_calls']['transformation'])
        name=frame['frame_id']
        if name not in release_cache:release_cache[name]=archive.native('FrameObj.GetReleases','frame',name,RELEASE_FIELDS)
        observed=release_cache[name]
        if observed is None:raise BankError('SCENARIO_NATIVE_RELEASE_NOT_OBSERVED')
        values,proof=observed;row.update(release_source=proof,release_values=deepcopy(values))
        if (any(not isinstance(values[k],list) or len(values[k])!=6 for k in RELEASE_FIELDS[:-1])
                or any(type(v) is not bool for k in ('II','JJ') for v in values[k])):
            raise BankError('SCENARIO_RELEASE_SIGNATURE_INVALID')
        if any(finite(v,'partial_fixity')<0 for k in ('StartValue','EndValue') for v in values[k]):
            raise BankError('SCENARIO_PARTIAL_FIXITY_INVALID')
        released=values['II' if end=='I' else 'JJ'][4 if axis=='M2' else 5]
        row['native_release_status']='RELEASED_OR_PARTIAL' if released else 'UNRELEASED'
        if released:raise BankError('SCENARIO_LOCAL_ROTATION_RELEASED_OR_PARTIAL')
        row['status']='MOMENT_DIRECTION_AND_RELEASE_BOUND'
    except OPTIONAL_ERRORS as exc:row['reason']=str(exc)
    row['mapping_id']='SCENARIO-MAP-'+digest(row)[:24];return row


def _beam_reference(row,diameter,mapping,archive_sha):
    candidate=next(c for c in row['candidates'] if c['diameter_mm']==diameter)
    result={'joint_id':mapping['joint_id'],'member_id':row['member_id'],'end':row['end'],'direction':mapping['direction'],
        'rotation_sign':mapping['rotation_sign'],'diameter_mm':diameter,'mapping_id':mapping['mapping_id'],
        'source_end_id':row['end_id'],'source_candidate_id':candidate['candidate_id'],'source_profile_id':row['profile_id'],
        'local_internal_moment_sign':None,'signed_local_m3_knm':None,'capacity_knm':None,'tolerance_knm':None,
        'tension_face':None,'top_label':candidate.get('top_label'),'bottom_label':candidate.get('bottom_label'),
        'status':'BEAM_SCENARIO_REFERENCE_BLOCKED','reason':mapping['reason'],'axial_scenario_n':0,
        'source_n_used':False,'column_case_is_beam_area_control_case':False,'physical_joint_capacity_proven':False}
    if mapping['reason'] is None:
        try:
            cap=candidate['capacity'];source=row['source']
            if (row['status']!='BEAM_END_SOURCE_BOUND' or candidate['status']!='BEAM_PROPOSAL_CALCULATED'):
                raise BankError(row['reason'] or candidate['reason'] or 'SCENARIO_BEAM_PROPOSAL_NOT_CALCULATED')
            if (row['final_design_eligible'] is not False or candidate['physical_cage_proven'] is not False
                    or candidate['selected_design'] is not False or cap['status']!='BEAM_CAPACITY_REFERENCE'
                    or cap['axial_force_scenario_n']!=0 or cap['source_beam_axial_force_applied'] is not False
                    or cap['final_design_eligible'] is not False or source['native_cut_count']!=1 or source['design_match_count']!=1
                    or source['targets']['same_force_vector_claimed'] is not False
                    or source['targets']['total_required_area_is_provided'] is not False):
                raise BankError('SCENARIO_BEAM_CAPACITY_SCOPE_MISMATCH')
            sign=mapping['mapping']['local_internal_moment_sign'];key='positive_m3_knm' if sign==1 else 'negative_m3_knm'
            value=finite(cap[key],'signed_beam_capacity')
            points=[p for p in cap['points'] if p['rotation_sign']==sign]
            if len(points)!=1 or sign*value<=0 or points[0]['reason'] is not None:raise BankError('SCENARIO_BEAM_SIGNED_CAPACITY_INVALID')
            tolerance=finite(points[0]['tolerance_knm'],'beam_capacity_tolerance')
            if tolerance<0:raise BankError('SCENARIO_BEAM_CAPACITY_TOLERANCE_INVALID')
            result.update(local_internal_moment_sign=sign,signed_local_m3_knm=value,capacity_knm=abs(value),
                tolerance_knm=tolerance,tension_face='BOTTOM' if sign==1 else 'TOP',status='BEAM_SCENARIO_REFERENCE',
                source_design_row_id=source['design_matches'][0]['source_row_id'],
                separate_area_controls={k:source['targets'][k] for k in ('top_combination','bottom_combination','torsion_combination')})
        except OPTIONAL_ERRORS as exc:result['reason']=str(exc)
    result['reference_id']='SCENARIO-BEAM-'+digest({'archive':archive_sha,**result})[:24];return result


def scenario_summaries(nodes,rows,cases,column_labels,beam_diameters):
    grouped=defaultdict(list)
    for row in rows:grouped[(row['joint_id'],row['direction'],row['column_label'],row['beam_diameter_mm'])].append(row)
    summaries=[]
    for node in nodes:
        for direction in ('X','Y'):
            roster=node['rosters'][direction]
            for label in column_labels:
                for diameter in beam_diameters:
                    source=grouped[(node['point_id'],direction,label,diameter)]
                    keys=[(r['output_case'],r['rotation_sign']) for r in source]
                    if len(keys)!=2*len(cases) or set(keys)!={(case,s) for case in cases for s in (-1,1)}:
                        raise BankError('SCENARIO_SUMMARY_CASE_POPULATION_MISMATCH')
                    valid=[r for r in source if r['normalized_scenario_ratio'] is not None]
                    complete=bool(source) and len(valid)==len(source)
                    minimum=min((r['normalized_scenario_ratio'] for r in valid),default=None) if complete else None
                    governing=sorted((r for r in valid if r['normalized_scenario_ratio']==minimum),key=lambda r:r['result_id']) if complete else []
                    first=governing[0] if governing else None
                    counts=dict(sorted(Counter(r['status'] for r in source).items()))
                    satisfied=None
                    if not source:status='NO_STATIC_SOURCE_CASES'
                    elif roster['reasons']:status='TOPOLOGY_UNRESOLVED'
                    elif not roster['beams']:status='NO_RECORDED_BEAM_IN_DIRECTION'
                    elif not complete:status='SCENARIO_INPUTS_INCOMPLETE'
                    elif any(r['scenario_reference_satisfied'] is False for r in source):status='SCENARIO_REFERENCE_NOT_SATISFIED';satisfied=False
                    elif any(r['scenario_reference_satisfied'] is None for r in source):status='SCENARIO_BOUNDARY_UNRESOLVED'
                    else:status='SCENARIO_REFERENCE_SATISFIED';satisfied=True
                    summaries.append({'joint_id':node['point_id'],'elevation_m':node['xyz_m'][2],'direction':direction,
                        'column_label':label,'beam_diameter_mm':diameter,'column_ids':[c['member_id'] for c in roster['columns']],
                        'beam_ids':[b['member_id'] for b in roster['beams']],'expected_case_rotation_count':2*len(cases),
                        'calculated_case_rotation_count':len(valid),'case_status_counts':counts,'status':status,
                        'minimum_normalized_scenario_ratio':minimum,'scenario_reference_satisfied':satisfied,
                        'governing_output_case':first['output_case'] if first else None,'governing_rotation_sign':first['rotation_sign'] if first else None,
                        'governing_sum_mrc_knm':first['sum_mrc_scenario_knm'] if first else None,
                        'governing_sum_mrb_knm':first['sum_mrb_scenario_knm'] if first else None,
                        'governing_required_mrc_knm':first['required_mrc_scenario_knm'] if first else None,
                        'governing_result_ids':[r['result_id'] for r in governing],'case_result_ids':[r['result_id'] for r in source],
                        'topology_reasons':roster['reasons'],'complete_declared_scenario_population':complete,
                        'sampled_static_cases_and_both_rotations_only':True,'normative_nd_minimum_proven':False,
                        'normative_exception_applied':False,'scwb_ratio':None,'formal_compliance':'NOT_PROVEN','final_design_eligible':False})
    return summaries


def build_scwb_scenarios(chain,joints,scwb,beams,archive):
    frames,points,nodes,beam_index,cases,bound=_validated(chain,joints,scwb,beams,archive)
    colrefs={r['reference_id']:r for r in scwb['column_references']}
    if len(colrefs)!=len(scwb['column_references']):raise BankError('SCENARIO_DUPLICATE_COLUMN_REFERENCE')
    mappings={};beamrefs={};releases={};rows=[]
    def mapping(name,end,joint,direction,sign,axis):
        key=(name,end,joint,direction,sign,axis)
        if key not in mappings:mappings[key]=_mapping(frames[name],end,joint,direction,sign,axis,archive,releases)
        return mappings[key]
    for old in scwb['rows']:
        joint,direction,sign,case,label=(old[k] for k in ('joint_id','direction','rotation_sign','output_case','candidate_label'))
        roster=nodes[joint]['rosters'][direction]
        expected_cols={(c['member_id'],c['end']) for c in roster['columns']}
        references=[colrefs[key] for key in old['column_reference_ids']]
        if (len(references)!=len(expected_cols) or {(r['member_id'],r['end']) for r in references}!=expected_cols
                or any(r['output_case']!=case or r['candidate_label']!=label for r in references)
                or old['topology_reasons']!=roster['reasons']):raise BankError('SCENARIO_COLUMN_CASE_BINDING_MISMATCH')
        if any(ref['reference_id']!='SCWB-COL-'+digest({'archive':archive.sha256,'member':ref['member_id'],'end':ref['end'],
                'case':case,'label':label,'direction':direction,'axis':ref['axis']})[:24] for ref in references):
            raise BankError('SCENARIO_COLUMN_REFERENCE_ID_MISMATCH')
        for diameter in DIAMETERS:
            context=JointCase(chain['source_run_id'],archive.sha256,joint,direction,sign,case,label+'/BEAM_PHI'+str(diameter)+'_N0')
            capacities=[];colmaps=[];br=[]
            for ref in references:
                name,end=ref['member_id'],ref['end'];axis=ref['axis']
                # An unresolved original column reference keeps its cause and
                # participant, even if no principal axis was established.
                m=mapping(name,end,joint,direction,sign,axis) if axis else None
                reason=ref['reason'] or (m['reason'] if m else 'SCENARIO_COLUMN_AXIS_NOT_BOUND')
                if ref['capacity_knm'] is not None and not reason:
                    calc=ref['calculation']
                    if (calc['both_signs_equal_from_verified_symmetry'] is not True or calc['source_n_is_design_nd'] is not False
                            or ref['capacity_knm']!=calc['capacity_knm'] or ref['n_source_kn']!=calc['n_source_kn']):
                        raise BankError('SCENARIO_COLUMN_SYMMETRY_OR_N_MISMATCH')
                capacities.append(MemberMomentCapacity(context,name,end,'COLUMN',None if reason else ref['capacity_knm'],
                    ref['reference_id'],ref['tolerance_knm'] or 0,reason))
                colmaps.append(m['mapping_id'] if m else None)
            for beam in roster['beams']:
                name,end=beam['member_id'],beam['end'];key=(joint,direction,sign,name,end,diameter)
                if key not in beamrefs:
                    m=mapping(name,end,joint,direction,sign,'M3')
                    beamrefs[key]=_beam_reference(beam_index[(name,end)],diameter,m,archive.sha256)
                ref=beamrefs[key];br.append(ref)
                capacities.append(MemberMomentCapacity(context,name,end,'BEAM',ref['capacity_knm'],ref['reference_id'],
                    ref['tolerance_knm'] or 0,ref['reason']))
            calc=compute_scwb_joint_result(context,[(c['member_id'],c['end']) for c in roster['columns']],
                [(b['member_id'],b['end']) for b in roster['beams']],capacities)
            row={'joint_id':joint,'direction':direction,'rotation_sign':sign,'output_case':case,'column_label':label,
                'beam_diameter_mm':diameter,'context':asdict(context),'source_scwb_case_id':old['result_id'],
                'column_reference_ids':old['column_reference_ids'],'column_mapping_ids':colmaps,
                'beam_reference_ids':[r['reference_id'] for r in br],'topology_reasons':roster['reasons'],
                'sum_mrc_scenario_knm':calc['sum_mrc_reference_knm'],'sum_mrb_scenario_knm':calc['sum_mrb_reference_knm'],
                'required_mrc_scenario_knm':calc['required_mrc_reference_knm'],'normalized_scenario_ratio':calc['normalized_reference_ratio'],
                'raw_scenario_capacity_ratio':calc['raw_capacity_ratio'],'scenario_reference_satisfied':calc['reference_satisfied'],
                'comparison_tolerance_knm':calc['comparison_tolerance_knm'],'residual_knm':calc['residual_knm'],
                'missing_capacities':calc['missing_capacities'],'expected_column_count':calc['expected_column_count'],
                'expected_beam_count':calc['expected_beam_count'],'factor':FACTOR,'status':calc['status'],
                'beam_axial_force_scenario_n':0,'concurrent_column_and_beam_force_state_proven':False,
                'physical_joint_moment_transfer_proven':False,'scwb_ratio':None,'formal_compliance':'NOT_PROVEN','final_design_eligible':False}
            if roster['reasons']:
                row.update(status='TOPOLOGY_UNRESOLVED',**{k:None for k in ('sum_mrc_scenario_knm','sum_mrb_scenario_knm',
                    'required_mrc_scenario_knm','normalized_scenario_ratio','raw_scenario_capacity_ratio','scenario_reference_satisfied',
                    'comparison_tolerance_knm','residual_knm')})
            row['result_id']='SCENARIO-CASE-'+digest(asdict(context))[:24];rows.append(row)
    node_list=deepcopy(list(nodes.values()));summaries=scenario_summaries(node_list,rows,cases,LABELS,DIAMETERS)
    result={'schema':SCHEMA,'policy':POLICY,'axis_convention':AXIS_CONVENTION,
        'source_run_id':chain['source_run_id'],'source_archive_sha256':archive.sha256,
        'source_demand_result_sha256':chain['result_sha256'],'source_joints_result_sha256':joints['result_sha256'],
        'source_scwb_result_sha256':scwb['result_sha256'],'source_beam_result_sha256':beams['result_sha256'],
        'source_population_status':scwb['source_population_status'],'graph_reason':scwb['graph_reason'],
        'selected_member_ids':scwb['selected_member_ids'],'known_column_count':scwb['selected_column_count'],
        'expected_column_end_count':scwb['expected_column_end_count'],'joint_node_count':len(nodes) if bound else None,
        'expected_case_count':len(nodes)*4*len(cases)*len(LABELS)*len(DIAMETERS) if bound else None,
        'case_count':len(rows),'calculated_case_count':sum(r['normalized_scenario_ratio'] is not None for r in rows),
        'expected_summary_count':len(nodes)*2*len(LABELS)*len(DIAMETERS) if bound else None,
        'summary_count':len(summaries),'static_cases':cases,'column_labels':list(LABELS),'beam_diameters_mm':list(DIAMETERS),
        'default_column_label':DEFAULT_COLUMN,'default_beam_diameter_mm':DEFAULT_BEAM,
        'nodes':node_list,'rows':rows,'summaries':summaries,'member_moment_mappings':list(mappings.values()),
        'beam_references':list(beamrefs.values()),'unresolved_member_ends':deepcopy(scwb['unresolved_member_ends']),
        'case_status_counts':dict(sorted(Counter(r['status'] for r in rows).items())),
        'summary_status_counts':dict(sorted(Counter(r['status'] for r in summaries).items())),
        'mapping_reason_counts':dict(sorted(Counter(r['reason'] for r in mappings.values() if r['reason']).items())),
        'beam_reason_counts':dict(sorted(Counter(r['reason'] for r in beamrefs.values() if r['reason']).items())),
        'factor':FACTOR,'ratio_definition':'SUM_MRC_PROPOSAL_AT_COLUMN_SOURCE_N_OVER_1_2_SUM_MRB_PROPOSAL_AT_N0',
        'rotation_basis':'RIGHT_HAND_ABOUT_GLOBAL_Z_CROSS_DIRECTION',
        'case_basis':'COLUMN_STATIC_SOURCE_N_ONLY_BEAM_N0_PROPOSALS_INDEPENDENT_OF_CASE',
        'source_population_reduced':False,'automatic_scenario_selection':False,'selected_design':None,
        'physical_joint_population_proven':False,'actual_or_selected_cages_bound':False,
        'actual_second_order_applied':False,'normative_exception_applied':False,'earthquake_compatible_minimum_proven':False,
        'physical_joint_moment_transfer_proven':False,'scwb_ratio_count':0,'member_id_filter':None,'output_case_filter':None,
        'display_column_label':None,'display_beam_diameter_mm':None,'open_basis':OPEN_BASIS.copy(),
        'references':{'csi_signs':SIGN_REFERENCE,'tbdy_7_3_5':scwb['code_reference']},
        'formal_compliance':'NOT_PROVEN','design_demand_authority':'DENIED','engineering_release':'NOT_READY'}
    result['result_sha256']=digest(result);return result


def scenario_projection(result,member_id=None,output_case=None,column_label=None,beam_diameter=None):
    if column_label is not None and column_label not in LABELS:raise BankError('SCENARIO_COLUMN_LABEL_INVALID')
    if beam_diameter is not None and (type(beam_diameter) is not int or beam_diameter not in DIAMETERS):
        raise BankError('SCENARIO_BEAM_DIAMETER_INVALID')
    nodes=[n for n in result['nodes'] if member_id is None or any(c['member_id']==member_id for c in n['rosters']['X']['columns'])]
    ids={n['point_id'] for n in nodes};cases=[c for c in result['static_cases'] if output_case is None or c==output_case]
    labels=[column_label] if column_label else result['column_labels'];diameters=[beam_diameter] if beam_diameter else result['beam_diameters_mm']
    rows=[r for r in result['rows'] if r['joint_id'] in ids and r['output_case'] in cases and r['column_label'] in labels and r['beam_diameter_mm'] in diameters]
    mapping_ids={key for r in rows for key in r['column_mapping_ids'] if key};beam_ids={key for r in rows for key in r['beam_reference_ids']}
    beams=[r for r in result['beam_references'] if r['reference_id'] in beam_ids];mapping_ids.update(r['mapping_id'] for r in beams)
    summaries=scenario_summaries(nodes,rows,cases,labels,diameters)
    return deepcopy({**result,'nodes':nodes,'rows':rows,'summaries':summaries,'static_cases':cases,
        'beam_references':beams,'member_moment_mappings':[r for r in result['member_moment_mappings'] if r['mapping_id'] in mapping_ids],
        'member_id_filter':member_id,'output_case_filter':output_case,'display_column_label':column_label,'display_beam_diameter_mm':beam_diameter,
        'filtered_joint_node_count':len(nodes) if result['joint_node_count'] is not None else None,
        'filtered_case_count':len(rows),'filtered_summary_count':len(summaries),
        'filtered_status_counts':dict(sorted(Counter(r['status'] for r in summaries).items())),
        'neighbouring_participants_retained':True,
        'unresolved_member_ends':[r for r in result['unresolved_member_ends'] if member_id is None or r['member_id']==member_id]})
