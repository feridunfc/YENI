"""Bounded, selected-page HTML for native spectral component envelopes."""
from html import escape
import json

from .column_engine.spectral_envelope import SCHEMA, POLICY, VIEW


def _number(value, digits=2):
    if value is None:
        return "—"
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _interval(bounds, component):
    value = (bounds or {}).get(component)
    return "—" if value is None else _number(value["lower"]) + " / " + _number(value["upper"])


def _table(headings, rows):
    return ("<table><thead><tr>" + "".join("<th>" + escape(h) + "</th>" for h in headings)
        + "</tr></thead><tbody>" + "".join("<tr>" + "".join("<td>" + escape(str(v if v is not None else "—"))
        + "</td>" for v in row) + "</tr>" for row in rows) + "</tbody></table>")


def build_spectral_html(report):
    s, page = report["column_spectral_envelopes"], report["demand_page"]
    if (s["schema"] != SCHEMA or s["policy"] != POLICY or page["view"] != VIEW
            or s["source_run_id"] != report["run_id"] or s["source_archive_sha256"] != report["source_archive_sha256"]
            or s["source_bank_result_sha256"] != report["result_sha256"] or s["design_demand_authority"] != "DENIED"
            or s["final_design_eligible"] is not False or s["physical_concurrency_proven"] is not False
            or s["code_rule_qualified"] is not False):
        raise ValueError("SPECTRAL_REPORT_CONTRACT_INVALID")
    labels = {"NUMERICAL_MATCH": "Kaynakla eşleşti", "NUMERICAL_MISMATCH": "Kaynakla uyuşmuyor", "SOURCE_UNRESOLVED": "Kaynak bağı eksik"}
    start = page["offset"] + 1 if page["rows"] else 0
    end = page["offset"] + len(page["rows"]) if page["rows"] else 0
    rows = [(r["member_id"], r["story"], r["output_case"],
             f'{r["station_key"]["Elm"]} · {_number(r["station_key"]["ObjSta"], 4)}',
             *(_interval(r["bounds"], c) for c in ("N", "M2", "M3")), labels[r["status"]]) for r in page["rows"]]
    body = ["<!doctype html><html lang='tr'><meta charset='utf-8'><title>YENI · Spektral kaynak zarfları</title>",
        "<style>body{font:15px system-ui;margin:2rem;color:#183047}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px;border-bottom:1px solid #ccd4dd;text-align:left}th{background:#edf2f7}details{margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}p{max-width:95ch}</style><main>",
        "<h1>Spektral kaynak zarfları · VS26</h1>",
        "<p>Her bileşenin alt/üst sınırı ayrı hesaplanır. Fiziksel eşzamanlı kuvvet vektörü ve nihai N<sub>d</sub>/M<sub>d</sub> değildir. Tasarım kabulü: <strong>NOT_PROVEN / NOT_READY</strong>.</p>",
        f'<p>Arşiv kapsamı: {s["selected_member_count"]} kolon · {s["eligible_combination_count"]} spektral birleşim · {s["matched_rows"]}/{s["expected_native_row_count"]} eşleşen native satır · {s["scalar_comparisons"]} skaler kıyas.</p>',
        f'<p><strong>Bu rapor seçili sayfadır: {start}–{end} / {page["total"]} filtrelenmiş sınır çifti.</strong> Kolon: {escape(page["member_id"] or "Tümü")} · Birleşim: {escape(page["output_case"] or "Tümü")}.</p>',
        f'<p>Kaynak kapsamı: {escape(s["source_coverage_status"])} · sayısal sonuç: {escape(s["replay_status"])}. İstasyon nüfusu bilinmeyen kolon: {len(s["members_without_station_population"])}.</p>',
        "<p>N basınç pozitif, kN; M2/M3 yerel eksenlerde kN·m; istasyon m. N alt=−P üst, N üst=−P alt. Yuvarlama yalnız gösterimdedir.</p>",
        _table(["Kolon", "Kat", "Birleşim", "Eleman · istasyon (m)", "N alt / üst (kN)", "M2 alt / üst (kN·m)", "M3 alt / üst (kN·m)", "Sayısal kaynak"], rows),
        "<details><summary>V2, V3 ve T sınırları</summary>",
        _table(["Kolon", "Birleşim", "Eleman", "Obje istasyonu (m)", "Eleman istasyonu (m)", "V2 alt / üst (kN)", "V3 alt / üst (kN)", "T alt / üst (kN·m)"],
            [(r["member_id"], r["output_case"], r["station_key"]["Elm"], _number(r["station_key"]["ObjSta"], 4),
              _number(r["station_key"]["ElmSta"], 4), *(_interval(r["bounds"], c) for c in ("V2", "V3", "T"))) for r in page["rows"]]),
        "</details><details><summary>Tarif, kaynak katsayıları ve kabul bekleyen girdiler</summary>",
        "<p>C = işaretli statik toplam; A = Σ |katsayı| × spektral Max genliği; sınırlar C−A / C+A. Kayıtlı birleşim katsayıları bir kez kullanılır. Spektrum ölçeği, %100/%30 ve büyütme yeniden uygulanmaz.</p>",
        "<p>Kaynak eşleşmesi; proje birleşimi seçimi, spektrum ölçeği/modal kapsam, analiz nesli, ikinci mertebe ve yönetmeliğe göre PMM talebi oluşturma kabulünü tamamlamaz.</p>",
        "<pre>" + escape(json.dumps({k: v for k, v in s.items() if k not in ("spectral_cases", "combinations")}, ensure_ascii=False, indent=2)) + "</pre>",
        "</details><details><summary>Birleşim tanımları ve spektrum parametrelerinin kaynakları</summary><pre>",
        escape(json.dumps({"combinations": s["combinations"], "spectral_cases": s["spectral_cases"]}, ensure_ascii=False, indent=2)),
        "</pre></details><details><summary>Bu sayfanın tam hassasiyetli hesapları ve native satır bağları</summary><pre>",
        escape(json.dumps(page, ensure_ascii=False, indent=2)), "</pre></details></main></html>"]
    return "".join(body)
