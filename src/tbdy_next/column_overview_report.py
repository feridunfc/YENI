"""Presentation of VS20 member summaries; no engineering decisions or rounding in selection."""
from html import escape
import json
import math


def number(value, digits=2):
    if value is None:
        return "—"
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("OVERVIEW_DISPLAY_NUMBER_INVALID")
    rounded = round(value, digits)
    return f"{0 if rounded == 0 else rounded:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pmm_text(pm):
    if pm["status"] == "AXIAL_RANGE_EXCEEDED":
        return f"Eksenel sınır aşılıyor · {pm['axial_outside_count']} kayıt"
    if pm["representative_basis"] == "MAXIMUM_RESOLVED_RADIAL_PMM":
        result = number(pm["maximum_resolved_utilization"], 4) + " · koşullu"
    elif pm["representative_basis"] == "MAXIMUM_AXIAL_ONLY_REFERENCE":
        result = "Yalnız N: " + number(pm["maximum_axial_utilization"], 4)
    elif pm["status"] == "NO_STATIC_STATES":
        return "Statik hesap kaydı yok"
    else:
        result = "Sayısal sonuç bekleniyor"
    if pm["unresolved_count"] or pm["blocked_count"]:
        result += f" · {pm['unresolved_count']} belirsiz / {pm['blocked_count']} eksik"
    if pm["axial_only_count"] and pm["representative_basis"] == "MAXIMUM_RESOLVED_RADIAL_PMM":
        result += f" · ayrıca {pm['axial_only_count']} yalnız N"
    if pm["status_counts"].get("EXCEEDS_SCENARIO_SURFACE", 0):
        result += " · yüzey aşılıyor"
    return result


SHEAR_TEXT = {"SOURCE_REFERENCE_EXCEEDED": "Kaynak sınırı aşılıyor", "PARTIAL_SHEAR_REFERENCES": "Kısmi kaynak hesabı",
    "CONDITIONAL_SHEAR_REFERENCES": "Koşullu kaynak hesabı", "NO_STATIC_STATES": "Statik kayıt yok"}


def _table(headers, rows):
    head = "".join("<th>"+escape(h)+"</th>" for h in headers)
    body = "".join("<tr>"+"".join("<td>"+escape(str(v if v is not None else "—"))+"</td>" for v in row)+"</tr>" for row in rows)
    return '<div class="overview-scroll"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def overview_html(overview):
    rows = overview["rows"]
    content = ('<section class="column-overview"><h1>Kolon mühendislik özeti · VS20</h1>'
        '<p><strong>'+str(overview["member_count"])+' kolon · '+str(overview["static_state_count"])+
        ' statik kaynak kaydı · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>Her satırdaki N, M2 ve M3, belirtilen kritik kaydın birlikte etkiyen kaynak vektörüdür. '
        'N basınç pozitif, momentler CSI yerel eksenlerindedir. Doğrulanmış Nd/M2d/M3d ve '
        'büyütülmüş momentler bekleniyor. Kritik seçim yuvarlanmamış hesapla yapılır.</p>')
    classes = overview["source_combination_classifications"]
    content += ('<p>'+str(classes.get("STATIC_LINEAR_ADD", 0))+' doğrudan statik birleşim; '+
        str(classes.get("RESPONSE_SPECTRUM_LINEAR_ADD", 0))+' spektrum içeren birleşim için tasarım vektörü oluşturulmadı. '
        'İlk tablo '+escape(overview["default_display_candidate"])+
        ' görüntüleme senaryosudur; üç öneri arasında tasarım seçimi yapılmadı.</p>')
    for index, label in enumerate(overview["candidate_labels"]):
        if index:
            content += '<details><summary>'+escape(label)+' görüntüleme senaryosu</summary>'
        else:
            content += '<h2>'+escape(label)+' · kolon başına kritik statik kayıt</h2>'
        table_rows = []
        for row in rows:
            scenario = next(s for s in row["scenarios"] if s["candidate_label"] == label)
            pm, sh = scenario["pmm"], scenario["shear"]
            source = pm["representative"] or {}; key = source.get("native_key", {}); vector = source.get("source_values", {})
            combo = key.get("LoadCase", "—")
            if pm["critical_state_count"] > 1:
                combo += f" · {pm['critical_state_count']} eşit/aynı öncelikli kayıt"
            table_rows.append((row["member_id"], row["story"], combo, number(vector.get("n_compression_kn")),
                number(vector.get("m2_knm")), number(vector.get("m3_knm")), label, pmm_text(pm),
                SHEAR_TEXT[sh["status"]]+" · Ve bekleniyor", "Girdiler bekleniyor"))
        content += _table(("Kolon", "Kat", "Kritik statik birleşim", "N kaynak (kN)", "M2 kaynak (kN·m)",
            "M3 kaynak (kN·m)", "Donatı senaryosu", "Koşullu PMM", "Kesme", "İkinci mertebe"), table_rows)
        if index:
            content += '</details>'
    cov = overview["station_coverage"]
    content += ('<details><summary>Birleşim kapsamı ve istasyon eşleşmeleri</summary><p>'+str(cov["design_row_count"])+
        ' tasarım satırı / '+str(cov["reference_count"])+' rol referansı. '+str(cov["ambiguous_row_count"])+
        ' belirsiz istasyon satırında '+str(cov["ambiguous_reference_count"])+
        ' referans; kesin istasyonu bulunmayan '+str(cov["missing_exact_reference_count"])+
        ' referansla kesişim '+str(cov["overlap_reference_count"])+', birleşim '+str(cov["union_reference_count"])+
        '. Satır ve referans sayıları toplanmaz; yakın istasyon seçilmez.</p></details>')
    content += '<h2>Kolon bazında kaynak ve hesap ayrıntıları</h2>'
    for row in rows:
        content += '<details><summary>'+escape(row["member_id"]+' · '+str(row["story"]))+' · hesap izleri</summary>'
        for scenario in row["scenarios"]:
            pm, sh = scenario["pmm"], scenario["shear"]
            content += '<h3>'+escape(scenario["candidate_label"])+'</h3><p>'+escape(pmm_text(pm))+'</p>'
            content += _table(("Statik kayıt", "Radyal PMM", "Yalnız N", "Eksenel sınır aşımı", "Belirsiz", "Eksik"),
                [(pm[k] for k in ("static_state_count", "radial_pmm_count", "axial_only_count", "axial_outside_count", "unresolved_count", "blocked_count"))])
            content += _table(("Birleşim", "İstasyon (m)", "Analiz elemanı", "N (kN)", "M2 (kN·m)", "M3 (kN·m)"),
                [(s["native_key"]["LoadCase"], number(s["native_key"]["ObjSta"], 3), s["native_key"]["Elm"],
                    number(s["source_values"]["n_compression_kn"]), number(s["source_values"]["m2_knm"]),
                    number(s["source_values"]["m3_knm"])) for s in pm["critical_states"]])
            content += '<p>Kesme maksimumları kendi kaynak durumlarına aittir; PMM kritik kaydıyla aynı olmak zorunda değildir.</p>'
            content += _table(("Yön", "Beton katkısı senaryosu", "Çözülen / beklenen", "En büyük |V|/Vr", "Kritik birleşimler"),
                [(b["axis"], "TS500" if b["branch"] == "ts500" else "Vc=0", f"{b['numeric_count']} / {b['state_count']}",
                    number(b["maximum_source_utilization"], 4), ", ".join(sorted({s["native_key"]["LoadCase"] for s in b["critical_source_states"]})))
                    for b in sh["branches"]])
            if sh["other_limit_findings"]:
                content += '<p>Ek kesme üst sınırı kaynak bulguları; gerçek Ve ve normatif kolon uygulanabilirliği açık kalır.</p>'
                content += _table(("Yön", "Referans", "Birleşim", "İşaretli V (kN)", "Sınır (kN)"),
                    [(f["axis"], "TS500 gövde" if f["reference"] == "ts500_web" else "TBDY gevrek kesme",
                        f["native_key"]["LoadCase"], number(f["source_signed_v_kn"]), number(f["reference_limit_kn"]))
                        for f in sh["other_limit_findings"]])
        second = row["second_order"]
        content += ('<p>İkinci mertebe: doğrulanmış ln, k, lk, Cm, β ve Md bekleniyor. '+str(second["reference_count"])+
            ' duyarlılık karşılaştırmasının '+str(second["nonpositive_reference_count"])+
            ' adedinde sıfıra yakın veya negatif payda; bunlar varsayımsal boy/rijitlik referanslarıdır. '
            'Gerçek kolon stabilite göçmesi veya kabulü göstermez.</p>')
        content += '<details><summary>Tam hassasiyet, kaynak kimlikleri ve eşit kritiklerin tamamı</summary><pre>'+escape(
            json.dumps(row, ensure_ascii=False, indent=2, allow_nan=False))+'</pre></details></details>'
    return content+'</section>'
