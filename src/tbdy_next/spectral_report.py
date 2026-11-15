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
    labels = {"NUMERICAL_MATCH": "Matches source", "NUMERICAL_MISMATCH": "Source mismatch", "SOURCE_UNRESOLVED": "Source link missing"}
    start = page["offset"] + 1 if page["rows"] else 0
    end = page["offset"] + len(page["rows"]) if page["rows"] else 0
    rows = [(r["member_id"], r["story"], r["output_case"],
             f'{r["station_key"]["Elm"]} · {_number(r["station_key"]["ObjSta"], 4)}',
             *(_interval(r["bounds"], c) for c in ("N", "M2", "M3")), labels[r["status"]]) for r in page["rows"]]
    body = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>YENI · Spectral source envelopes</title>",
        "<style>body{font:15px system-ui;margin:2rem;color:#183047}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px;border-bottom:1px solid #ccd4dd;text-align:left}th{background:#edf2f7}details{margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}p{max-width:95ch}</style><main>",
        "<h1>Spectral source envelopes · VS26</h1>",
        "<p>Lower and upper bounds are calculated separately for each component. Concurrent force vectors and final N<sub>d</sub>/M<sub>d</sub> require further evidence. Design acceptance is <strong>NOT_PROVEN / NOT_READY</strong>.</p>",
        f'<p>Archive coverage {s["selected_member_count"]} columns · {s["eligible_combination_count"]} spectral combinations · {s["matched_rows"]}/{s["expected_native_row_count"]} matched native rows · {s["scalar_comparisons"]} scalar comparisons.</p>',
        f'<p><strong>Current page {start}–{end} / {page["total"]} filtered bound pairs.</strong> Column {escape(page["member_id"] or "All")} · Combination {escape(page["output_case"] or "All")}.</p>',
        f'<p>Source coverage {escape(s["source_coverage_status"])} · Numerical result {escape(s["replay_status"])}. Columns with unknown station coverage {len(s["members_without_station_population"])}.</p>',
        "<p>Compression-positive N is in kN, local M2 and M3 are in kN·m, and stations are in m. Lower N=−upper P and upper N=−lower P. Decisions use full precision.</p>",
        _table(["Column", "Story", "Combination", "Element · station (m)", "Lower / upper N (kN)", "Lower / upper M2 (kN·m)", "Lower / upper M3 (kN·m)", "Numerical source"], rows),
        "<details><summary>V2, V3 and T bounds</summary>",
        _table(["Column", "Combination", "Element", "Object station (m)", "Element station (m)", "Lower / upper V2 (kN)", "Lower / upper V3 (kN)", "Lower / upper T (kN·m)"],
            [(r["member_id"], r["output_case"], r["station_key"]["Elm"], _number(r["station_key"]["ObjSta"], 4),
              _number(r["station_key"]["ElmSta"], 4), *(_interval(r["bounds"], c) for c in ("V2", "V3", "T"))) for r in page["rows"]]),
        "</details><details><summary>Method, source factors and inputs awaiting acceptance</summary>",
        "<p>C is the signed static sum and A is Σ |factor| × spectral Max amplitude. The bounds are C−A and C+A. Recorded combination factors, spectrum scaling, the 100%/30% rule and amplification enter once.</p>",
        "<p>Project combination selection, spectrum scale and modal coverage, analysis generation, second-order effects and code-based PMM demand require evidence beyond the numerical source match.</p>",
        "<pre>" + escape(json.dumps({k: v for k, v in s.items() if k not in ("spectral_cases", "combinations")}, ensure_ascii=False, indent=2)) + "</pre>",
        "</details><details><summary>Sources for combination definitions and spectrum parameters</summary><pre>",
        escape(json.dumps({"combinations": s["combinations"], "spectral_cases": s["spectral_cases"]}, ensure_ascii=False, indent=2)),
        "</pre></details><details><summary>Full-precision calculations and native row links on this page</summary><pre>",
        escape(json.dumps(page, ensure_ascii=False, indent=2)), "</pre></details></main></html>"]
    return "".join(body)
