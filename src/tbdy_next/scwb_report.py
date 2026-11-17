"""Readable SCWB source references; missing beam steel never becomes capacity."""
from html import escape
import json
from .column_overview_report import number, _table

STATUS={"BEAM_CAPACITY_NOT_BOUND":"Beam end reinforcement pending",
    "COLUMN_AND_BEAM_INPUTS_INCOMPLETE":"Column and beam inputs missing",
    "NO_RECORDED_BEAM_IN_DIRECTION":"No recorded beam in this direction",
    "TOPOLOGY_UNRESOLVED":"Connection geometry unresolved","NO_STATIC_SOURCE_CASES":"Static source case unavailable"}


def scwb_html(result):
    if result['source_population_status']=='BLOCKED_NATIVE_JOINT_GRAPH':
        return ('<section class="column-scwb"><h2>Strong column–weak beam · VS22</h2><p><strong>'
            'Joint network verification pending · NOT_PROVEN / NOT_READY</strong></p><p>'+str(result['selected_column_count'])+
            ' known columns / '+str(result['expected_column_end_count'])+' expected ends / '+str(result['expected_column_reference_count'])+
            ' expected capacity records. Joint count and full coverage remain unresolved.</p>'+
            _table(('Column','End'),[(r['member_id'],r['end']) for r in result['unresolved_member_ends']])+
            '<details><summary>Open connection evidence</summary><p>'+escape(str(result['graph_reason']))+'</p></details></section>')
    content=('<section class="column-scwb"><h2>Strong column–weak beam · VS22</h2><p><strong>'+
        str(result.get('filtered_joint_node_count',result['joint_node_count']))+' joints · '+str(len(result['static_cases']))+
        ' static combinations · three reinforcement scenarios · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Direction-specific column end capacity references depend on N and are summed for the same static case. '
        'The minimum covers the recorded static cases. Minimum Nd consistent with the seismic direction requires separate evidence. '
        'Equality in the two rotation directions follows from verified cage symmetry. Physical joint faces require verification of the source sections.</p>'
        '<p>The beam summary gives required As and the model gives area overrides. Selected end reinforcement requires further evidence. '
        'A zero override has unknown installed reinforcement. Missing members remain in scope with unresolved beam capacities and SCWB ratios. '
        'Roof and low axial force exceptions remain pending.</p>')
    for index,label in enumerate(result['scenario_labels']):
        if index:content+='<details><summary>'+escape(label)+' · SCWB source references</summary>'
        else:content+='<h3>'+escape(label)+' · Source summary per joint</h3>'
        rows=[r for r in result['summaries'] if r['candidate_label']==label]
        content+=_table(('Joint','Kot (m)','Direction / rotation','Column total / case','Minimum source ΣMrc (kN·m)',
            'Governing static combination','SCWB durumu'),[(r['joint_id'],number(r['elevation_m']),
            r['direction']+' / '+('+' if r['rotation_sign']>0 else '−'),
            str(r['calculated_column_sum_count'])+' / '+str(r['expected_case_count']),number(r['sampled_minimum_column_sum_knm']),
            ', '.join(r['sampled_minimum_case_ids']) or '—',STATUS[r['status']]) for r in rows])
        if index:content+='</details>'
    content+='<details><summary>Joint members and missing beam capacity</summary>'
    content+='<p>Adjacent members remain in scope. Beam end capacities, slab contribution, physical faces, seismic Nd and exception applicability require verification.</p>'
    content+=_table(('Joint','Direction','Column ends','Beam ends','Connection'),[(n['point_id'],direction,
        ', '.join(c['member_id']+'/'+c['end'] for c in n['rosters'][direction]['columns']),
        ', '.join(b['member_id']+'/'+b['end'] for b in n['rosters'][direction]['beams']) or 'No record',
        'Geometry unresolved' if n['rosters'][direction]['reasons'] else 'Native ends linked. Physical faces pending.')
        for n in result['nodes'] for direction in ('X','Y')])+'</details>'
    # Full precision is retained in the JSON export. Avoid duplicating thousands
    # of identical source states in HTML; capacity records remain inspectable.
    content+='<details><summary>Column capacity traces · Same case and end section</summary>'
    content+=_table(('Column','End','Local moment','Static combination','Scenario','Source N (kN)','Source Mrc (kN·m)','Source status'),
        [(r['member_id'],r['end'],r['axis'],r['output_case'],r['candidate_label'],number(r['n_source_kn']),
          number(r['capacity_knm']),(r['source_state'] or {}).get('state_id') or r['reason']) for r in result.get('column_references',[])])+'</details>'
    metadata={k:result[k] for k in ('schema','policy','result_sha256','source_archive_sha256','source_demand_result_sha256',
        'source_cages_result_sha256','source_joints_result_sha256','source_kinematics_result_sha256','column_reason_counts',
        'beam_summary_source','open_basis','adapted_sources','code_reference')}
    content+='<details><summary>Source links, method and open inputs</summary><pre>'+escape(
        json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
