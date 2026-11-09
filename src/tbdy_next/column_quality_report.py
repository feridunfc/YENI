"""Readable VS21 numerical comparison; no capacity calculation in rendering."""
from html import escape
import json
from .column_overview_report import number, _table

STATUS={"NUMERICAL_COMPARISON_MATCH":"Tolerans içinde","NUMERICAL_COMPARISON_MISMATCH":"Tolerans dışında",
    "REFERENCE_UNRESOLVED":"Referans çözülemedi","REFERENCE_NOT_STABLE":"Referans kararlı değil"}
PRIMARY={"WITHIN_SCENARIO_SURFACE":"Koşullu yüzey içinde","EXCEEDS_SCENARIO_SURFACE":"Koşullu yüzey aşılıyor",
    "AXIAL_ONLY_SCENARIO":"Yalnız eksenel","OUTSIDE_SCENARIO_AXIAL_RANGE":"Eksenel sınır aşılıyor",
    "NUMERIC_UNRESOLVED":"Sayısal çözüm belirsiz","BLOCKED_INPUTS":"Girdi eksik"}


def quality_html(result):
    content=('<section class="column-quality"><h2>PMM bağımsız sayısal kıyas · VS21</h2><p><strong>'+
        str(result['comparison_count'])+' kritik kayıt / '+str(result['filtered_primary_assessment_count'])+
        ' filtrelenmiş ana PMM değerlendirmesi · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Ana hesabın her kolon/öneri için en büyük çözülen radyal PMM kayıtları ve tüm eşitleri karşılaştırılır. '
        'Kritik seçimin kendisi ve PMM nüfusunun tamamı bağımsız doğrulanmış değildir. '
        'Eksenel, çözülemeyen ve eksik girdili durumlar kapsam tablosunda ayrı kalır.</p>'
        '<p>İki yol aynı malzeme modelini kullanır. Sayısal uyum; malzeme modelini, depremli tasarım talebini, '
        'ikinci mertebeyi veya yönetmelik uygunluğunu kanıtlamaz. Sürekli hata sınırı ve tüm köklerin tekliği kanıtlanmadı.</p>')
    content+='<p>'+escape(' · '.join(STATUS[k]+': '+str(v) for k,v in result['status_counts'].items()) or
        'Seçili filtrede karşılaştırılabilir kritik radyal kayıt yok.')+'</p>'
    content+=_table(('Kolon','Kat','Öneri','Kritik statik birleşim','Ana kapasite (kN·m)','Bağımsız kapasite (kN·m)',
        '|Fark| (kN·m)','Tolerans (kN·m)','Sayısal kıyas'),[(r['member_id'],r['story'],r['candidate_label'],r['native_key']['LoadCase'],
            number(r['primary_capacity_knm']),number(r['reference_capacity_knm']),number(r['absolute_difference_knm'],4),
            number(r['comparison_budget_knm'],4),STATUS[r['status']]) for r in result['rows']])
    content+='<details><summary>Karşılaştırma kapsamı ve kıyaslanmayan durumlar</summary>'
    content+=_table(('Kolon','Öneri','Ana kayıt','Radyal','Radyal dışı','Kritik eşitler','Ana hesap durumları'),
        [(g['member_id'],g['candidate_label'],g['primary_state_count'],g['primary_radial_state_count'],g['primary_nonradial_state_count'],
            g['target_count'],' · '.join(PRIMARY[k]+': '+str(v) for k,v in g['primary_status_counts'].items()) or 'Statik kayıt yok')
            for g in result['members']])+'</details>'
    content+=('<details><summary>Bağımsız hesap yöntemi ve toleranslar</summary><p>Beton: kesit kenarlarında bölünmüş şerit integrasyonu. '
        'Çubuğun yerini alan beton: dairesel alanın 2 noktalı Gauss integrasyonu. Eksenel denge ve moment doğrultusu: bağımsız ikiye bölme çözümü. '
        'Üç çözüm düzeyi: 8/16/32 disk paneli ve çeyrek düzlemde 12/24/48 açısal aralık. Eksenel artık ≤ 0,05 N; '
        'doğrultu artığı ≤ 100 N·mm + 10⁻⁸ |M|. İki ardışık kapasite farkı ≤ 100 N·mm + 10⁻⁵ max(M). '
        'Ana–referans kıyas bütçesi: 1000 N·mm + 0,002 max(M) + (1 + 0,05) N × kesit yarıçapı. '
        'Ana hesabın üç düzeydeki kapasite yayılımı bütçeye eklenmez. Kararlar yuvarlanmamış değerlerle verilir.</p></details>')
    content+='<details><summary>Tam hassasiyet, kaynak kimlikleri ve üç çözüm düzeyi</summary><pre>'+escape(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
