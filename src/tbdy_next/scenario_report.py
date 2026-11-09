"""Compact, explicitly conditional joint proposal capacity comparisons."""
from html import escape
import json
from .column_overview_report import number,_table

STATUS={'SCENARIO_REFERENCE_SATISFIED':'Senaryo referansını karşılıyor',
    'SCENARIO_REFERENCE_NOT_SATISFIED':'Senaryo referansının altında',
    'SCENARIO_BOUNDARY_UNRESOLVED':'Sayısal sınırda · belirsiz',
    'SCENARIO_INPUTS_INCOMPLETE':'Katılımcı kapasitesi eksik',
    'TOPOLOGY_UNRESOLVED':'Bağlantı geometrisi belirsiz',
    'NO_RECORDED_BEAM_IN_DIRECTION':'Yönde kayıtlı kiriş yok',
    'NO_STATIC_SOURCE_CASES':'Statik kolon N kaydı yok'}


def scenario_html(result):
    content='<section class="scwb-scenarios"><h2>SCWB öneri senaryoları · VS24</h2>'
    if result['source_population_status']=='BLOCKED_NATIVE_JOINT_GRAPH':
        return content+'<p>Birleşim ağı doğrulanamadı. '+str(result['known_column_count'])+' bilinen kolon / '+str(
            result['expected_column_end_count'])+' beklenen kolon ucu korunur; birleşim ve senaryo paydası bilinmiyor. NOT_PROVEN / NOT_READY.</p></section>'
    content+=('<p><strong>'+str(result['joint_node_count'])+' birleşim · '+str(result['calculated_case_count'])+'/'+str(result['expected_case_count'])+
        ' hesaplanmış senaryo · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Oran = ΣMrc(kolon kaynak N) / [1,2 ΣMrb(kiriş N=0)]; senaryo referansı ≥1. '
        'Her özet aynı kolon/kiriş önerisinde bütün kayıtlı statik vakaları ve iki dönmeyi kapsar. '
        'Kritik oran, kolon ve kiriş toplamlarıyla aynı kayıttan gelir; eksik katılımcı veya vaka varsa minimum verilmez.</p>'
        '<p>Üç kolon önerisi ve üç ortak kiriş çapı arasında nihai seçim yapılmaz. Kirişlerdeki çubuk adetleri uçlara göre değişir; '
        'ortak çap sürekliliği veya uygulanmış kafesi kanıtlamaz. Vaka yalnız kolon N kaydını seçer; kiriş alan zarfları ayrı kontrol birleşimlerinden gelir. '
        'N=0 kiriş senaryosu gerçek eşzamanlı deprem kuvveti değildir.</p>'
        '<p>Dönme, X için +Y, Y için −X eksenine göre sağ el kuralıyla tanımlanan geometrik referanstır. '
        'Native I/J, yerel eksen ve ilgili uç dönme serbestliği doğrulanır. Fiziksel kolon yüzü, V×r/N×r aktarımı, döşeme, '
        'ankraj/süreklilik, depremle uyumlu Nd minimumu ve istisnalar doğrulanmadı; nihai SCWB oranı üretilmez.</p>')
    default=(result['default_column_label'],result['default_beam_diameter_mm'])
    pairs=sorted({(r['column_label'],r['beam_diameter_mm']) for r in result['summaries']},key=lambda pair:(pair!=default,pair))
    for index,(label,diameter) in enumerate(pairs):
        title='Kolon '+label+' / kiriş Φ'+str(diameter)
        content+=('<h3>'+escape(title)+'</h3>') if index==0 else '<details><summary>'+escape(title)+'</summary>'
        summaries=[s for s in result['summaries'] if (s['column_label'],s['beam_diameter_mm'])==(label,diameter)]
        content+=_table(('Birleşim','Kot (m)','Yön','Vaka×dönme kapsamı','Kritik kolon N vakası / dönme',
            'ΣMrc (kN·m)','ΣMrb (kN·m)','Koşullu oran ≥1','Durum'),[
            (s['joint_id'],number(s['elevation_m']),s['direction'],str(s['calculated_case_rotation_count'])+'/'+str(s['expected_case_rotation_count']),
             (s['governing_output_case']+' / '+('+' if s['governing_rotation_sign']==1 else '−')) if s['governing_output_case'] else None,
             number(s['governing_sum_mrc_knm']),number(s['governing_sum_mrb_knm']),number(s['minimum_normalized_scenario_ratio'],3),STATUS[s['status']])
            for s in summaries])
        if index:content+='</details>'
    maps={m['mapping_id']:m for m in result['member_moment_mappings']}
    content+='<details><summary>Kiriş uçları, seçilen moment dalları ve kaynak durumları</summary>'
    content+=_table(('Birleşim','Yön / dönme','Kiriş/uç','Çap','Üst / alt öneri','Çekme yüzü','Yerel M3 (kN·m)','Uç dönmesi','Açık neden'),[
        (r['joint_id'],r['direction']+' / '+('+' if r['rotation_sign']==1 else '−'),r['member_id']+'/'+r['end'],r['diameter_mm'],
         str(r['top_label'])+' / '+str(r['bottom_label']),{'TOP':'Üst','BOTTOM':'Alt'}.get(r['tension_face']),number(r['signed_local_m3_knm']),
         'Serbestlik verilmemiş' if maps[r['mapping_id']]['native_release_status']=='UNRELEASED' else 'Serbestlik belirsiz veya serbest',r['reason'])
        for r in result['beam_references']])+'</details>'
    content+='<details><summary>Kapsam, sayısal durumlar ve kaynak kimlikleri</summary><pre>'+escape(json.dumps(
        {k:result[k] for k in ('schema','result_sha256','source_scwb_result_sha256','source_beam_result_sha256','ratio_definition',
            'rotation_basis','case_basis','case_status_counts','summary_status_counts','mapping_reason_counts','beam_reason_counts','references','open_basis')},
        ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
