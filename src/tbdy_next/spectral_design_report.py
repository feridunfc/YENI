"""Compact Turkish report from the same bounded VS26 projection as UI/CLI."""
from html import escape
import json

from .column_engine.demand_types import PERMUTATION_POLICY, CSI_RULE
from .column_engine.native_archive import finite
from .column_engine.spectral_design import SCHEMA, VIEW, DETAIL_VIEW
from .column_engine.spectral_pmm import SCHEMA as PMM_SCHEMA, GOVERNING_BASIS
from .spectral_report import _number, _table
from .verification.golden_gate import SCHEMA as GOLDEN_SCHEMA, MANIFEST_SHA256


def validate_spectral_design_report(report):
    s, p, replay, page = (report[k] for k in ("column_spectral_design", "spectral_pmm", "spectral_replay", "demand_page"))
    golden = report.get("golden_regression_gate", {})
    if (s["schema"] != SCHEMA or p["schema"] != PMM_SCHEMA or page["view"] not in (VIEW, DETAIL_VIEW)
            or golden.get("schema") != GOLDEN_SCHEMA or golden.get("source_manifest_sha256") != MANIFEST_SHA256
            or golden.get("normative_qualification") != "NOT_PROVEN"
            or golden.get("acceptance_eligible") is not False or golden.get("engineering_release") != "NOT_READY"
            or golden.get("gate_status") != "REQUIRED_REPORT_GOLDEN_COVERAGE_INCOMPLETE"
            or s["source_run_id"] != report["run_id"] or p["source_run_id"] != report["run_id"]
            or s["source_archive_sha256"] != report["source_archive_sha256"]
            or p["source_archive_sha256"] != report["source_archive_sha256"]
            or s["source_bank_result_sha256"] != report["result_sha256"]
            or s["source_replay_result_sha256"] != replay["result_sha256"]
            or p["source_population_result_sha256"] != s["result_sha256"]
            or p["source_static_demand_result_sha256"] != s["source_static_demand_result_sha256"]
            or s["permutation_policy"] != PERMUTATION_POLICY or s["applicable_design_rule"] != CSI_RULE
            or p["selection_basis"] != GOVERNING_BASIS or p["numerical_policy"]["solver_revision"] != "VS25_DIRECTION_ROOT"
            or any(x["design_demand_authority"] != "DENIED" or x["engineering_release"] != "NOT_READY"
                or x["normative_qualification"] != "NOT_PROVEN"
                or any(x[k] is not False for k in ("final_design_eligible", "physical_concurrency_proven",
                    "analysis_generation_qualified", "continuous_axial_envelope_complete", "second_order_applied")) for x in (s,p))
            or page["member_id"] != s["member_id_filter"] or page["output_case"] != s["output_case_filter"]
            or page["column_label"] != s["reinforcement_filter"] or page["raw_population_included"] is not False
            or not 1 <= page["limit"] <= 500 or len(page["rows"]) > page["limit"]
            or len(page["rows"]) != max(0, min(page["limit"], page["total"]-page["offset"]))):
        raise ValueError("SPECTRAL_DESIGN_REPORT_CONTRACT_INVALID")
    for row in page["rows"]:
        if (row["final_design_eligible"] is not False or row["engineering_status"] != "CONDITIONAL"
                or row["normative_qualification"] != "NOT_PROVEN"
                or row["reinforcement"] != page["column_label"]
                or page["member_id"] is not None and row["member_id"] != page["member_id"]):
            raise ValueError("SPECTRAL_DESIGN_REPORT_ROW_INVALID")
        states = [row] if page["view"] == DETAIL_VIEW else [row["governing_resolved"], row["first_unresolved_or_axial_outside"]]
        for state in (v for v in states if v is not None):
            if (state["member_id"] != row["member_id"] or state["station_key"]["Obj"] != row["member_id"]
                    or page["output_case"] is not None and state["combination"] != page["output_case"]
                    or state["final_design_eligible"] is not False or state["second_order_applied"] is not False):
                raise ValueError("SPECTRAL_DESIGN_REPORT_STATE_INVALID")
            for value in state["forces"].values(): finite(value, "report_force")
            if state["conditional_pmm_ratio"] is not None: finite(state["conditional_pmm_ratio"], "report_ratio")
    return s, p, replay, page


def build_spectral_design_html(report):
    s, p, replay, page = validate_spectral_design_report(report)
    headings = ["Kolon", "Kat", "Birleşim · eleman / istasyon", "İşaret senaryosu", "N (kN)",
        "M2 (kN·m)", "M3 (kN·m)", "Öneri donatı", "Koşullu PMM", "Açık sayısal durum"]
    rows = []
    for row in page["rows"]:
        state = row if page["view"] == DETAIL_VIEW else row["governing_resolved"]
        forces = state["forces"] if state else {}
        cut = state["station_key"] if state else None
        status = (state["numerical_status"] if page["view"] == DETAIL_VIEW else
            f'{row["unresolved_or_axial_outside_count"]} belirsiz / eksenel sınır aşımı; {row["governing_resolved_tie_count"]} eşit kritik kayıt')
        rows.append((row["member_id"], row.get("story"),
            f'{state["combination"]} · {cut["Elm"]} / {_number(cut["ObjSta"],4)}' if state else "Bu filtrede çözülen radyal oran yok",
            state["sign_id"] if state else None, *(_number(forces.get(k)) for k in ("N_kN", "M2_kNm", "M3_kNm")),
            row["reinforcement"], _number(state["conditional_pmm_ratio"],4) if state else "—", status))
    start = page["offset"]+1 if page["rows"] else 0
    end = page["offset"]+len(page["rows"]) if page["rows"] else 0
    body = ["<!doctype html><html lang='tr'><meta charset='utf-8'><title>YENI · Depremli tasarım talebi</title>",
        "<style>body{font:15px system-ui;margin:2rem;color:#183047}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px;border-bottom:1px solid #ccd4dd;text-align:left;font-variant-numeric:tabular-nums}th{background:#edf2f7}details{margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}p{max-width:105ch}</style><main>",
        "<h1>Kolonlar · Depremli tasarım talebi</h1>",
        "<p><strong>Koşullu tasarım zarfı · NOT_PROVEN / NOT_READY.</strong> N basınç pozitiftir. Kuvvetler bir tasarım kontrolü için kurulmuştur; fiziksel olarak eşzamanlı analiz vektörü değildir. İkinci mertebe ve minimum dışmerkezlik uygulanmadı.</p>",
        f'<p>{s["selected_member_count"]} kolon · {replay["eligible_combination_count"]} spektrumlu birleşim · {replay["matched_rows"]}/{replay["expected_native_row_count"]} eşleşen native satır · {replay["scalar_comparisons"]} bileşen karşılaştırması.</p>',
        f'<p>{s["candidate_count"]}/{s["expected_candidate_count"]} işaret adayı · {p["assessment_count"]}/{p["expected_assessment_count"]} PMM değerlendirmesi · {s["blocked_pair_count"]} aday üretilemeyen sınır çifti. Statik referans nüfusu: {s["static_reference_count"]}.</p>',
        f'<p><strong>Seçili sayfa: {start}–{end} / {page["total"]}.</strong> Kolon: {escape(page["member_id"] or "Tümü")} · Birleşim: {escape(page["output_case"] or "Tümü")} · Donatı: {escape(page["column_label"])}.</p>',
        _table(headings, rows),
        "<p>Kritik oran, çözülen sonlu adaylar arasındaki en büyük orandır. Belirsiz çözümler ve eksenel sınır aşımları ayrıca izlenir. Sekiz köşe, ara N değerlerinin tamamı için kapsama kanıtı değildir; donatı önerisi seçilmiş tasarım değildir.</p>",
        "<p><strong>Golden rapor kabul kapısı açık.</strong> Mevcut 23+7 rapor kontrolleri ayrı doğrulama bankasında korunur. PMM, ikinci mertebe, SCWB, kapasite kesmesi ve kat α için tam rapor doğrulaması tamamlanmadı. ETABS kaynak eşleşmesi bu kapıyı kapatmaz.</p>",
        "<details><summary>Golden rapor doğrulama kapsamı</summary><pre>"+
        escape(json.dumps(report["golden_regression_gate"],ensure_ascii=False,indent=2,sort_keys=True))+"</pre></details>",
        "<details><summary>Altı bileşende sayısal kaynak farkları · arşivin tamamı</summary>",
        _table(["Bileşen", "Birim", "Karşılaştırma", "Tolerans dışı", "En büyük mutlak fark"],
            [(d["component"],d["unit"],d["comparisons"],d["mismatches"],format(d["maximum_absolute_difference"],".6g"))
             for d in replay["component_differences"]]), "</details>",
        "<details><summary>Birleşim sınıfları ve kaynak kapsamı</summary>",
        _table(["Birleşim","Sınıf","Eşleşen / beklenen satır","İşaret adayı kapsamı","Açık neden"],
            [(r["combination"],r["classification"],f'{r["matched_rows"]} / {2*r["expected_pairs"]}',r["sign_construction_scope"],r["reason"])
             for r in s["classifications"]]), "</details>",
        "<details><summary>Hesap yöntemi ve mühendislik kabul koşulları</summary>",
        "<p>C işaretli statik katkı, A kayıtlı katsayı mutlak değerleriyle ağırlıklandırılmış spektrum genliğidir. Native P/M2/M3 için bağımsız ± işaretler uygulanır, sonra N=−P dönüşümü yapılır. Kaydedilmiş %100/%30, ölçek ve ortak çarpan ikinci kez uygulanmaz.</p>",
        "<p>CSI'nin çok değerli tasarım çıktıları için kullandığı işaret permütasyonu, TBDY kabulü değildir. TBDY 4.4.2 doğrultu ve 4.10 iç kuvvet kuralları; 4.4.3 düşey deprem uygulanabilirliği; 4.4.4 diğer yüklerle birleşimler; Ek 4B modal kapsam/ölçekleme ve analiz nesli ayrıca doğrulanmalıdır.</p>",
        "<pre>"+escape(json.dumps({"blockers":p["blockers"],"references":s["references"],
            "direction_diagnostics":s["direction_diagnostics"]},ensure_ascii=False,indent=2,sort_keys=True))+"</pre></details>",
        "<details><summary>Seçili sayfanın tam hassasiyeti ve kaynak kimlikleri</summary><pre>",
        escape(json.dumps({"run_id":report["run_id"],"source_sha256":report["source_archive_sha256"],
            "replay_result_sha256":replay["result_sha256"],"population_result_sha256":s["result_sha256"],
            "pmm_result_sha256":p["result_sha256"],"page":page},ensure_ascii=False,indent=2,sort_keys=True)),
        "</pre></details></main></html>"]
    return "".join(body)
