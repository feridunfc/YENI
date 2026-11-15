"""Compact beam-end source and proposed N=0 capacity presentation."""
from html import escape
import json
from .column_overview_report import number,_table

STATUS={'BEAM_PROPOSAL_CALCULATED':'Conditional proposal calculation','BEAM_PROPOSAL_BLOCKED':'Input or layout unresolved',
    'BEAM_PROPOSAL_NUMERIC_UNRESOLVED':'Numerical solution unresolved'}


def beam_html(result):
    content='<section class="beam-references"><h2>Beam end reinforcement and capacity · VS23</h2>'
    if result['source_population_status']=='BLOCKED_NATIVE_JOINT_GRAPH':
        return content+'<p>Joint network verification is pending. '+str(result['known_column_count'])+' known columns are retained. Beam and end counts are unknown. NOT_PROVEN / NOT_READY.</p></section>'
    content+=('<p><strong>'+str(result['source_bound_end_count'])+'/'+str(result['expected_end_count'])+
        ' source ends · '+str(result['calculated_candidate_count'])+'/'+str(result['expected_candidate_count'])+
        ' reinforcement and capacity scenarios · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Hedef '+str(result['target_beam_count'])+' beams are listed with both ends. '+str(result['expected_incident_end_count'])+
        ' ends connect to column joints. The other '+str(len(result['outside_joint_scope_beams']))+' remain in the beam coverage list.</p>'
        '<p>Each face uses the smallest whole number of bars that meets the recorded required area. Φ16, Φ20 and Φ24 remain proposals. '
        'Top and bottom required areas and governing combinations are separate source envelopes. Installed reinforcement requires independent evidence.</p>'
        '<p>Capacities assume pure bending at N=0. +M3 puts bottom reinforcement in tension and −M3 puts top reinforcement in tension. '
        'ETABS top and bottom cover is measured to the centroid of the longitudinal reinforcement. '
        'The proposal uses 30 mm side clear cover and Φ10 ties. Aggregate, torsion and web reinforcement, anchorage, continuity and slab contribution require verification before an SCWB decision.</p>')
    diameters=[result['policy']['default_display_diameter_mm'],*[d for d in result['policy']['diameters_mm'] if d!=result['policy']['default_display_diameter_mm']]]
    for index,diameter in enumerate(diameters):
        if index:content+='<details><summary>Φ'+str(diameter)+' beam reinforcement scenario</summary>'
        else:content+='<h3>Φ'+str(diameter)+' · Source and capacity by end</h3>'
        rows=[]
        for row in result['rows']:
            c=next(c for c in row['candidates'] if c['diameter_mm']==diameter);source=row['source'] or {};targets=source.get('targets') or {}
            cap=(c.get('capacity') or {}) if c['status']=='BEAM_PROPOSAL_CALCULATED' else {}
            rows.append((row['member_id'],row['end'],number(source.get('target_station_m'),3),
                number(targets.get('top_mm2')),number(targets.get('bottom_mm2')),c.get('top_label'),c.get('bottom_label'),
                number(cap.get('positive_m3_knm')),number(cap.get('negative_m3_knm')),STATUS[c['status']]))
        content+=_table(('Beam','End','Station (m)','Top area target (mm²)','Bottom area target (mm²)',
            'Top proposal','Bottom proposal','+M3 (kN·m)','−M3 (kN·m)','Status'),rows)
        if index:content+='</details>'
    content+='<details><summary>End sources, unresolved stations and governing combinations</summary>'
    content+=_table(('Beam','End','Native section / design row','Top governing combination','Bottom governing combination','Torsion governing combination','Open issue'),
        [(r['member_id'],r['end'],str((r['source'] or {}).get('native_cut_count','—'))+' / '+str((r['source'] or {}).get('design_match_count','—')),
          ((r['source'] or {}).get('targets') or {}).get('top_combination'),((r['source'] or {}).get('targets') or {}).get('bottom_combination'),
          ((r['source'] or {}).get('targets') or {}).get('torsion_combination'),r['reason']) for r in result['rows']])+'</details>'
    content+='<details><summary>Beams outside column joint coverage</summary>'+_table(('Beam','Coverage'),
        [(r['member_id'],'No native end at a recorded column joint') for r in result['outside_joint_scope_beams']])+'</details>'
    details={k:result[k] for k in ('schema','result_sha256','source_archive_sha256','source_demand_result_sha256',
        'source_joints_result_sha256','policy','profiles','table_source','table_reason','source_reason_counts','references','open_basis')}
    details['ambiguous_or_missing_ends']=[r for r in result['rows'] if r['status']!='BEAM_END_SOURCE_BOUND']
    content+='<details><summary>Source identifiers, assumptions and unresolved end traces</summary><pre>'+escape(
        json.dumps(details,ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
