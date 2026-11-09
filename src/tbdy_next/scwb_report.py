"""Readable SCWB source references; missing beam steel never becomes capacity."""
from html import escape
import json
from .column_overview_report import number, _table

STATUS={"BEAM_CAPACITY_NOT_BOUND":"Kiriş uç donatısı bekleniyor",
    "COLUMN_AND_BEAM_INPUTS_INCOMPLETE":"Kolon ve kiriş girdileri eksik",
    "NO_RECORDED_BEAM_IN_DIRECTION":"Bu yönde kayıtlı kiriş yok",
    "TOPOLOGY_UNRESOLVED":"Bağlantı geometrisi belirsiz","NO_STATIC_SOURCE_CASES":"Statik kaynak vakası yok"}


def scwb_html(result):
    if result['source_population_status']=='BLOCKED_NATIVE_JOINT_GRAPH':
        return ('<section class="column-scwb"><h2>Güçlü kolon–zayıf kiriş · VS22</h2><p><strong>'
            'Birleşim ağı doğrulanamadı · NOT_PROVEN / NOT_READY</strong></p><p>'+str(result['selected_column_count'])+
            ' bilinen kolon / '+str(result['expected_column_end_count'])+' beklenen uç / '+str(result['expected_column_reference_count'])+
            ' beklenen kapasite kaydı. Birleşim sayısı bilinmiyor; kapsam tamamlanmış değildir.</p>'+
            _table(('Kolon','Uç'),[(r['member_id'],r['end']) for r in result['unresolved_member_ends']])+
            '<details><summary>Bağlantı kaynağının açık nedeni</summary><p>'+escape(str(result['graph_reason']))+'</p></details></section>')
    content=('<section class="column-scwb"><h2>Güçlü kolon–zayıf kiriş · VS22</h2><p><strong>'+
        str(result.get('filtered_joint_node_count',result['joint_node_count']))+' birleşim · '+str(len(result['static_cases']))+
        ' statik birleşim · üç donatı senaryosu · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Kolon uçlarının N’ye bağlı, yön bazındaki kapasite referansları aynı statik vakada toplanır. '
        'En küçük toplam yalnız kayıtlı statik vakalar arasındadır; deprem yönüyle uyumlu Nd minimumu değildir. '
        'İki dönme yönündeki kolon eşitliği doğrulanmış kafes simetrisine dayanır. Kaynak kesitleri fiziksel birleşim yüzü olarak doğrulanmadı.</p>'
        '<p>Kiriş tasarım özetindeki gerekli As ve model donatı alanı override değerleri, seçilmiş uç donatısı değildir. '
        'Sıfır override sıfır donatı sayılmaz. Kiriş kapasitesi ve SCWB oranı boş bırakılır; eksik üye hesaptan düşürülmez. '
        'Çatı veya düşük eksenel kuvvet istisnası uygulanmadı.</p>')
    for index,label in enumerate(result['scenario_labels']):
        if index:content+='<details><summary>'+escape(label)+' · SCWB kaynak referansları</summary>'
        else:content+='<h3>'+escape(label)+' · birleşim başına kaynak özeti</h3>'
        rows=[r for r in result['summaries'] if r['candidate_label']==label]
        content+=_table(('Birleşim','Kot (m)','Yön / dönme','Kolon toplamı / vaka','En küçük ΣMrc kaynak (kN·m)',
            'Kritik statik birleşim','SCWB durumu'),[(r['joint_id'],number(r['elevation_m']),
            r['direction']+' / '+('+' if r['rotation_sign']>0 else '−'),
            str(r['calculated_column_sum_count'])+' / '+str(r['expected_case_count']),number(r['sampled_minimum_column_sum_knm']),
            ', '.join(r['sampled_minimum_case_ids']) or '—',STATUS[r['status']]) for r in rows])
        if index:content+='</details>'
    content+='<details><summary>Birleşim üyeleri ve eksik kiriş kapasitesi</summary>'
    content+='<p>Seçili kolonun komşu üyeleri korunur. Kiriş uç kapasiteleri, döşeme katkısı, fiziksel yüzler, depremli Nd ve istisna uygulanabilirliği bekleniyor.</p>'
    content+=_table(('Birleşim','Yön','Kolon uçları','Kiriş uçları','Bağlantı'),[(n['point_id'],direction,
        ', '.join(c['member_id']+'/'+c['end'] for c in n['rosters'][direction]['columns']),
        ', '.join(b['member_id']+'/'+b['end'] for b in n['rosters'][direction]['beams']) or 'Kayıt yok',
        'Geometri belirsiz' if n['rosters'][direction]['reasons'] else 'Native uçlar bağlı; fiziksel yüzler bekleniyor')
        for n in result['nodes'] for direction in ('X','Y')])+'</details>'
    # Full precision is retained in the JSON export. Avoid duplicating thousands
    # of identical source states in HTML; capacity records remain inspectable.
    content+='<details><summary>Kolon kapasite izleri · aynı vaka ve uç kesiti</summary>'
    content+=_table(('Kolon','Uç','Yerel moment','Statik birleşim','Senaryo','N kaynak (kN)','Mrc kaynak (kN·m)','Kaynak durumu'),
        [(r['member_id'],r['end'],r['axis'],r['output_case'],r['candidate_label'],number(r['n_source_kn']),
          number(r['capacity_knm']),(r['source_state'] or {}).get('state_id') or r['reason']) for r in result.get('column_references',[])])+'</details>'
    metadata={k:result[k] for k in ('schema','policy','result_sha256','source_archive_sha256','source_demand_result_sha256',
        'source_cages_result_sha256','source_joints_result_sha256','source_kinematics_result_sha256','column_reason_counts',
        'beam_summary_source','open_basis','adapted_sources','code_reference')}
    content+='<details><summary>Kaynak bağları, yöntem ve açık girdiler</summary><pre>'+escape(
        json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
