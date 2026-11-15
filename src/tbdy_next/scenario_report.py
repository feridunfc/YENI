"""Compact, explicitly conditional joint proposal capacity comparisons."""
from html import escape
import json
from .column_overview_report import number,_table

STATUS={'SCENARIO_REFERENCE_SATISFIED':'Meets scenario reference',
    'SCENARIO_REFERENCE_NOT_SATISFIED':'Below scenario reference',
    'SCENARIO_BOUNDARY_UNRESOLVED':'At numerical boundary · unresolved',
    'SCENARIO_INPUTS_INCOMPLETE':'Missing participant capacity',
    'TOPOLOGY_UNRESOLVED':'Connection geometry unresolved',
    'NO_RECORDED_BEAM_IN_DIRECTION':'No recorded beam in direction',
    'NO_STATIC_SOURCE_CASES':'No static column N record'}


def scenario_html(result):
    content='<section class="scwb-scenarios"><h2>SCWB proposal scenarios · VS24</h2>'
    if result['source_population_status']=='BLOCKED_NATIVE_JOINT_GRAPH':
        return content+'<p>Joint network verification is pending. '+str(result['known_column_count'])+' known columns / '+str(
            result['expected_column_end_count'])+' expected column ends are retained. Joint and scenario totals are unknown. NOT_PROVEN / NOT_READY.</p></section>'
    content+=('<p><strong>'+str(result['joint_node_count'])+' joints · '+str(result['calculated_case_count'])+'/'+str(result['expected_case_count'])+
        ' calculated scenarios · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Ratio = ΣMrc(column source N) / [1.2 ΣMrb(beam N=0)]. The scenario reference is ≥1. '
        'Each summary covers all recorded static cases and both rotations for the same column and beam proposal. '
        'The governing ratio and the column and beam totals refer to the same record. A minimum requires all participants and cases.</p>'
        '<p>Three column proposals and three common beam diameters are evaluated. Beam bar counts vary by end. '
        'Continuity and installed cages require separate evidence. The case selects the column N record, and beam area envelopes use their own governing combinations. '
        'Concurrent seismic beam forces require independent evidence for the N=0 scenario.</p>'
        '<p>Rotation uses the right-hand rule about +Y for X and −X for Y as a geometric reference. '
        'Verification covers native I/J, local axes and the relevant end rotational degree of freedom. Physical column faces, V×r/N×r transfer, slab contribution, '
        'anchorage, continuity, minimum seismic-compatible Nd and exceptions require verification before a final SCWB ratio is available.</p>')
    default=(result['default_column_label'],result['default_beam_diameter_mm'])
    pairs=sorted({(r['column_label'],r['beam_diameter_mm']) for r in result['summaries']},key=lambda pair:(pair!=default,pair))
    for index,(label,diameter) in enumerate(pairs):
        title='Column '+label+' / Beam Φ'+str(diameter)
        content+=('<h3>'+escape(title)+'</h3>') if index==0 else '<details><summary>'+escape(title)+'</summary>'
        summaries=[s for s in result['summaries'] if (s['column_label'],s['beam_diameter_mm'])==(label,diameter)]
        content+=_table(('Joint','Kot (m)','Direction','Case × rotation coverage','Governing column N case / rotation',
            'ΣMrc (kN·m)','ΣMrb (kN·m)','Conditional ratio ≥1','Status'),[
            (s['joint_id'],number(s['elevation_m']),s['direction'],str(s['calculated_case_rotation_count'])+'/'+str(s['expected_case_rotation_count']),
             (s['governing_output_case']+' / '+('+' if s['governing_rotation_sign']==1 else '−')) if s['governing_output_case'] else None,
             number(s['governing_sum_mrc_knm']),number(s['governing_sum_mrb_knm']),number(s['minimum_normalized_scenario_ratio'],3),STATUS[s['status']])
            for s in summaries])
        if index:content+='</details>'
    maps={m['mapping_id']:m for m in result['member_moment_mappings']}
    content+='<details><summary>Beam ends, selected moment branches and source states</summary>'
    content+=_table(('Joint','Direction / rotation','Beam / end','Diameter','Top / bottom proposal','Tension face','Local M3 (kN·m)','End rotation','Open issue'),[
        (r['joint_id'],r['direction']+' / '+('+' if r['rotation_sign']==1 else '−'),r['member_id']+'/'+r['end'],r['diameter_mm'],
         str(r['top_label'])+' / '+str(r['bottom_label']),{'TOP':'Top','BOTTOM':'Bottom'}.get(r['tension_face']),number(r['signed_local_m3_knm']),
         'Degree of freedom unavailable' if maps[r['mapping_id']]['native_release_status']=='UNRELEASED' else 'Serbestlik belirsiz veya serbest',r['reason'])
        for r in result['beam_references']])+'</details>'
    content+='<details><summary>Coverage, numerical states and source identifiers</summary><pre>'+escape(json.dumps(
        {k:result[k] for k in ('schema','result_sha256','source_scwb_result_sha256','source_beam_result_sha256','ratio_definition',
            'rotation_basis','case_basis','case_status_counts','summary_status_counts','mapping_reason_counts','beam_reason_counts','references','open_basis')},
        ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
