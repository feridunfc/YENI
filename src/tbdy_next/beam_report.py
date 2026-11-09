"""Compact beam-end source and proposed N=0 capacity presentation."""
from html import escape
import json
from .column_overview_report import number,_table

STATUS={'BEAM_PROPOSAL_CALCULATED':'Öneri hesabı · koşullu','BEAM_PROPOSAL_BLOCKED':'Girdi veya yerleşim belirsiz',
    'BEAM_PROPOSAL_NUMERIC_UNRESOLVED':'Sayısal çözüm belirsiz'}


def beam_html(result):
    content='<section class="beam-references"><h2>Kiriş uç donatısı ve kapasitesi · VS23</h2>'
    if result['source_population_status']=='BLOCKED_NATIVE_JOINT_GRAPH':
        return content+'<p>Birleşim ağı doğrulanamadı. '+str(result['known_column_count'])+' bilinen kolon korunur; kiriş/uç sayısı bilinmiyor. NOT_PROVEN / NOT_READY.</p></section>'
    content+=('<p><strong>'+str(result['source_bound_end_count'])+'/'+str(result['expected_end_count'])+
        ' kaynak ucu · '+str(result['calculated_candidate_count'])+'/'+str(result['expected_candidate_count'])+
        ' donatı/kapasite senaryosu · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Hedef '+str(result['target_beam_count'])+' kirişin iki ucu korunur. '+str(result['expected_incident_end_count'])+
        ' uç kolon birleşimindedir. Diğer '+str(len(result['outside_joint_scope_beams']))+' kiriş kapsam listesinde tutulur.</p>'
        '<p>Her yüzdeki çubuk sayısı kayıtlı gerekli alanı örten en küçük tamsayıdır; Φ16/Φ20/Φ24 arasından nihai seçim yapılmaz. '
        'Üst/alt gerekli alan ve kontrol birleşimleri ayrı kaynak zarflarıdır. Gerekli As, uygulanmış donatı değildir.</p>'
        '<p>Kapasiteler N=0 saf eğilme senaryosudur; kaynak kiriş N’si kullanılmaz. +M3 alt donatıyı, −M3 üst donatıyı çekmeye çalıştırır. '
        'ETABS üst/alt örtüsü boyuna donatı ağırlık merkezine kadardır; etriye/yarıçap tekrar eklenmez. '
        'Yan net örtü 30 mm ve etriye Φ10 açık öneridir. Agrega, burulma/gövde donatısı, ankraj, süreklilik ve döşeme katkısı doğrulanmadı. SCWB oranı üretilmez.</p>')
    diameters=[result['policy']['default_display_diameter_mm'],*[d for d in result['policy']['diameters_mm'] if d!=result['policy']['default_display_diameter_mm']]]
    for index,diameter in enumerate(diameters):
        if index:content+='<details><summary>Φ'+str(diameter)+' kiriş donatı senaryosu</summary>'
        else:content+='<h3>Φ'+str(diameter)+' · uç başına kaynak ve kapasite</h3>'
        rows=[]
        for row in result['rows']:
            c=next(c for c in row['candidates'] if c['diameter_mm']==diameter);source=row['source'] or {};targets=source.get('targets') or {}
            cap=(c.get('capacity') or {}) if c['status']=='BEAM_PROPOSAL_CALCULATED' else {}
            rows.append((row['member_id'],row['end'],number(source.get('target_station_m'),3),
                number(targets.get('top_mm2')),number(targets.get('bottom_mm2')),c.get('top_label'),c.get('bottom_label'),
                number(cap.get('positive_m3_knm')),number(cap.get('negative_m3_knm')),STATUS[c['status']]))
        content+=_table(('Kiriş','Uç','İstasyon (m)','Üst alan hedefi (mm²)','Alt alan hedefi (mm²)',
            'Üst öneri','Alt öneri','+M3 (kN·m)','−M3 (kN·m)','Durum'),rows)
        if index:content+='</details>'
    content+='<details><summary>Uç kaynakları, belirsiz istasyonlar ve kontrol birleşimleri</summary>'
    content+=_table(('Kiriş','Uç','Native kesit / tasarım satırı','Üst kontrol','Alt kontrol','Burulma kontrol','Açık neden'),
        [(r['member_id'],r['end'],str((r['source'] or {}).get('native_cut_count','—'))+' / '+str((r['source'] or {}).get('design_match_count','—')),
          ((r['source'] or {}).get('targets') or {}).get('top_combination'),((r['source'] or {}).get('targets') or {}).get('bottom_combination'),
          ((r['source'] or {}).get('targets') or {}).get('torsion_combination'),r['reason']) for r in result['rows']])+'</details>'
    content+='<details><summary>Kolon birleşimi kapsamı dışındaki kirişler</summary>'+_table(('Kiriş','Kapsam'),
        [(r['member_id'],'Kayıtlı kolon düğümünde native ucu yok') for r in result['outside_joint_scope_beams']])+'</details>'
    details={k:result[k] for k in ('schema','result_sha256','source_archive_sha256','source_demand_result_sha256',
        'source_joints_result_sha256','policy','profiles','table_source','table_reason','source_reason_counts','references','open_basis')}
    details['ambiguous_or_missing_ends']=[r for r in result['rows'] if r['status']!='BEAM_END_SOURCE_BOUND']
    content+='<details><summary>Kaynak kimlikleri, hesap varsayımları ve belirsiz uç izleri</summary><pre>'+escape(
        json.dumps(details,ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
