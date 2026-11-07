"""Complete VS01/VS02 report exports from existing verified local receipts.

Presentation only: uses *the same* modal and geometry evaluators to recheck the
archived payload against receipts. No ETABS, no new engineering authority, no
side effects. Full JSON preserves original source rows for independent audit.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from typing import Any, Mapping

from .history import _MAX_SOURCE_BYTES, _RUN, _read_modal_run, _read_receipt
from .quick_checks import check_registry, evaluate_geometry_capture


class ReportUnavailable(ValueError):
    """No verified five-check result exists for this run."""


def _load_source(directory: Path, expected_sha: str) -> dict[str, Any]:
    source_file = directory / "input.source"
    if source_file.is_symlink() or not source_file.is_file():
        raise ReportUnavailable("Source file unavailable")
    if source_file.stat().st_size > _MAX_SOURCE_BYTES:
        raise ReportUnavailable("Archived source exceeds size limit")
    raw = source_file.read_bytes()
    if sha256(raw).hexdigest() != expected_sha:
        raise ReportUnavailable("Archived source hash mismatch")
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ReportUnavailable("Archived source must be an object")
    return decoded


def build_complete_report(root: Path, run_id: str) -> dict[str, Any]:
    """One complete report for an exact existing five-check run.

    Raises ReportUnavailable on missing/altered source, tampered receipt,
    conflicting evaluated values or incomplete check inventory.
    """
    if not isinstance(run_id, str) or _RUN.fullmatch(run_id) is None:
        raise ReportUnavailable("Invalid run ID")
    directory = Path(root) / run_id
    modal = _read_modal_run(directory)
    quick = _read_receipt(directory, "quick-geometry")
    if modal is None or quick is None:
        raise ReportUnavailable("Complete modal and geometry receipts required")
    if quick.get("input_sha256") != modal["input_sha256"]:
        raise ReportUnavailable("Modal and geometry sources conflict")
    try:
        source = _load_source(directory, modal["input_sha256"])
        geometry_source = source.get("geometry_capture")
        geometry = evaluate_geometry_capture(geometry_source)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise ReportUnavailable("Geometry source cannot be verified") from exc
    if geometry != quick["payload"]:
        raise ReportUnavailable("Geometry receipt does not match current evaluator")

    definitions = check_registry()
    mapping = {item["check_id"]: item for item in definitions}
    geo_checks = geometry.get("checks", [])
    if not isinstance(geo_checks, list) or len(geo_checks) != len(mapping) - 1:
        raise ReportUnavailable("Incomplete geometry check population")
    if {check.get("check_id") for check in geo_checks} != set(mapping) - {"modal_mass_95"}:
        raise ReportUnavailable("Check IDs differ from current registry")
    # Never promote a numerical subcondition to an overall regulatory PASS.
    modal_check = {
        **mapping["modal_mass_95"],
        **modal["result"],
        "check_id": "modal_mass_95",
        "formal_compliance": "NOT_PROVEN",
    }
    checks = [modal_check] + geo_checks
    frame_rows = ((geometry_source or {}).get("tables", {}).get("FRAME_ASSIGNMENTS", {})
                  .get("rows", []) or [])
    frame_types = dict(sorted(Counter(str(row.get("Type", "UNKNOWN")) for row in frame_rows).items()))
    table_descriptors: dict[str, Any] = {}
    for role, table in (geometry_source or {}).get("tables", {}).items():
        table_descriptors[role] = {
            "table_key": table.get("table_key"), "record_count": table.get("row_count"),
            "capture_status": table.get("status"), "fields": table.get("fields"),
            "field_metadata": table.get("field_metadata"),
        }
    metadata = source.get("capture_metadata", {})
    source_table = source.get("table", {})
    counts = {
        "geometry_item_evaluations": sum(int(x.get("expected_count", 0)) for x in geo_checks),
        "geometry_evaluated": sum(int(x.get("evaluated_count", 0)) for x in geo_checks),
        "geometry_meets": sum(int(x.get("met_count", 0)) for x in geo_checks),
        "geometry_does_not_meet": sum(int(x.get("unmet_count", 0)) for x in geo_checks),
        "geometry_not_proven": sum(int(x.get("not_proven_count", 0)) for x in geo_checks),
        "geometry_not_applicable": sum(int(x.get("not_applicable_count", 0)) for x in geo_checks),
    }
    return {
        "schema": "tbdy.next.complete.engineering.report.v1",
        "run_id": run_id,
        "title": "TBDY Next Engine — Complete five-check source-bound screening",
        "model": modal["model_name"],
        "captured_at_utc": modal["captured_at_utc"],
        "source_mode": modal["source_mode"],
        "modal_case": modal["case"],
        "engineering_release": "NOT_READY",
        "formal_compliance": "NOT_PROVEN",
        "scope": "modal 95% numerical subcondition + 4 reinforced-concrete geometry screens",
        "checks": checks,
        "modal_source_table": {
            "table_key": source_table.get("table_key"), "fields": source_table.get("fields"),
            "row_count": source_table.get("row_count"), "rows": source_table.get("rows"),
        },
        "geometry_source_summary": {
            "status": geometry.get("status"),
            "source_units": geometry.get("source_units"),
            "source_row_count": geometry.get("source_row_count"),
            "column_connectivity_count": geometry.get("column_connectivity_count"),
            "beam_connectivity_count": geometry.get("beam_connectivity_count"),
            "frame_types": frame_types,
            "tables": table_descriptors,
            "material_types": (geometry_source or {}).get("material_types"),
        },
        "evaluation_counts": counts,
        "capture_metadata": metadata,
        "source_provenance": {
            "input_sha256": modal["input_sha256"],
            "modal_receipt_sha256": modal["receipt_sha256"],
            "geometry_receipt_sha256": quick["receipt_sha256"],
            "note": "These are local source/receipt fingerprints, not third-party authorization.",
        },
        "source_snapshot": source,  # Full raw 7 tables + exact material facts for independent review.
        "report_note": (
            "All numeric results are recorded as observed numerical subconditions. "
            "The applicable full TBDY/TS500 requirements, model-analysis validity and release "
            "have not been independently established. Export includes project metadata and "
            "source rows; review before sharing."
        ),
    }


def _val(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return escape(str(value), quote=True)


def _table(columns: tuple[tuple[str, str], ...], rows: list[Mapping[str, Any]], cls: str = "") -> str:
    header = "".join(f"<th>{escape(title)}</th>" for _, title in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{_val(item.get(key))}</td>" for key, _ in columns) + "</tr>"
        for item in rows
    )
    return f'<table class="{cls}"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'


def build_printable_html(report: Mapping[str, Any]) -> str:
    """Self-contained print-ready HTML. All five checks and every member row."""
    checks = report["checks"]
    modal, geometry = checks[0], checks[1:]
    summary_cols = (
        ("check_id", "Kontrol"), ("status", "Sayısal durum"),
        ("expected_count", "Eleman-kontrol"), ("evaluated_count", "Hesaplanan"),
        ("met_count", "Sağlayan"), ("unmet_count", "Sağlamayan"),
        ("not_applicable_count", "Kapsam dışı"), ("not_proven_count", "Çözümlenemeyen"),
    )
    summary_rows = [
        {"check_id": modal["check_id"], "status": modal["status"],
         "expected_count": 1, "evaluated_count": 1, "met_count": int(modal["status"] == "MEETS_NUMERICAL_CRITERION"),
         "unmet_count": int(modal["status"] != "MEETS_NUMERICAL_CRITERION"),
         "not_applicable_count": 0, "not_proven_count": 0},
        *geometry,
    ]
    section_cols = (
        ("story", "Kat"), ("element_id", "UniqueName"), ("section", "Atanan kesit"),
        ("material_name", "Malzeme"), ("material_classification", "Malzeme sınıfı"),
        ("width_mm", "t2 mm"), ("depth_mm", "t3 mm"),
        ("value", "Kontrol değeri"), ("limit", "Sınır"), ("ratio", "Oran"),
        ("status", "Durum"), ("reason", "Teşhis"),
    )
    check_sections = []
    for i, check in enumerate(geometry, 1):
        desc = (f"<h2>{i:02d}. {_val(check.get('title'))}</h2>"
                f"<p><strong>{_val(check.get('code_ref'))}</strong> · "
                f"Sayısal durum: {_val(check.get('status'))} · "
                f"Kapsam: {_val(check.get('expected_count'))}, "
                f"Hesaplanan: {_val(check.get('evaluated_count'))}, "
                f"Sağlamayan: {_val(check.get('unmet_count'))}, "
                f"Kapsam dışı: {_val(check.get('not_applicable_count'))}, "
                f"Çözümlenemeyen: {_val(check.get('not_proven_count'))}</p>")
        check_sections.append(f'<section class="percheck">{desc}{_table(section_cols, check.get("items", []))}</section>')
    modal_table = report["modal_source_table"]
    fields = modal_table.get("fields") or []
    modal_cols = tuple((field, field) for field in fields)
    modal_section = (
        f'<section class="percheck"><h2>Modal kaynak tablosu — {_val(modal_table.get("row_count"))} satır</h2>'
        f'<p>İlk hesap: X={_val(modal.get("sum_ux"))}, Y={_val(modal.get("sum_uy"))}, '
        f'Eşik={_val(modal.get("required_ratio"))}, yönetici mod={_val(modal.get("governing_mode_count"))}; '
        f'önemli modlar X={_val(modal.get("significant_modes_x"))}, '
        f'Y={_val(modal.get("significant_modes_y"))}.</p>'
        + _table(modal_cols, modal_table.get("rows") or [], "modal-grid") + "</section>"
    )
    census = report["geometry_source_summary"]
    census_rows = [{"type": k, "count": v} for k,v in census["frame_types"].items()]
    material_facts = (census.get("material_types") or {}).get("facts", {})
    materials = [{"name": name, "code": fact.get("material_type_code"),
                  "status": fact.get("status"), "concrete": fact.get("is_concrete")}
                 for name, fact in sorted(material_facts.items())]
    tables = [{"role": role, "key": tab.get("table_key"), "count": tab.get("record_count"),
               "status": tab.get("capture_status"), "fields": ", ".join(tab.get("fields") or [])}
              for role, tab in census["tables"].items()]
    html = f'''<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>TBDY Next Engine — {_val(report['run_id'])}</title>
<style>
@page {{size: A4 landscape; margin: 10mm}}
* {{box-sizing:border-box}} body {{font:12px/1.48 system-ui,Arial,sans-serif; color:#1c3045; margin:22px auto; max-width:1450px; padding:0 18px}}
h1 {{font-size:24px; margin:0 0 4px}} h2 {{font-size:17px; padding-top:10px; border-top:2px solid #d3dce7; margin:20px 0 8px}}
h3 {{font-size:14px}} .muted {{color:#52687f}} .warning {{padding:9px 13px; border-left:4px solid #986a16; background:#fbf4e9; margin:15px 0}}
.grid {{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:15px 0}} .grid div {{background:#f2f6fa;padding:11px;border:1px solid #d9e2ea}}
table {{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:10px}}
th,td {{border:1px solid #d4deea;padding:4px 5px;text-align:left;overflow-wrap:anywhere}}
th {{background:#e8eff7;font-weight:650}} tr:nth-child(even) td {{background:#f7f9fc}}
.modal-grid {{font-size:9px}} .modal-grid td,.modal-grid th {{padding:3px}}
.percheck {{break-before:page;page-break-before:always}} thead {{display:table-header-group}} tr {{break-inside:avoid;page-break-inside:avoid}}
.toolstrip {{margin-bottom:24px}} .toolstrip button {{background:#245d89;color:white;padding:9px 15px;border:0;border-radius:5px;cursor:pointer}}
@media print {{body {{margin:0;max-width:unset;padding:0;font:10px/1.3 Arial,sans-serif}} .toolstrip {{display:none}} h1 {{font-size:20px}} h2 {{font-size:14px}} table {{font-size:8px}} .modal-grid {{font-size:7px}}}}
</style></head><body>
<div class="toolstrip">Tarayıcıdan <strong>Ctrl+P</strong> → PDF olarak kaydet / yazdır.</div>
<h1>TBDY Next Engine — Mühendislik Kontrol Raporu</h1>
<p class="muted">Beş sayısal alt kontrol · Tam eleman sonuçları · ETABS kaynak verisi</p>
<div class="warning"><strong>FORMAL COMPLIANCE = NOT_PROVEN · ENGINEERING RELEASE = NOT_READY.</strong>
Bu rapor tam TBDY/TS500 uygunluk kararı değildir. Yalnız raporda tanımlanan sayısal alt kontroller çalıştırılmıştır.</div>
<div class="grid">
<div><strong>Model</strong><p>{_val(report.get('model'))}</p></div>
<div><strong>Çalışma / tarih</strong><p>{_val(report['run_id'])}<br>{_val(report['captured_at_utc'])}</p></div>
<div><strong>Kaynak / modal vaka</strong><p>{_val(report['source_mode'])}<br>{_val(report['modal_case'])}</p></div>
</div>
<h2>Kontrol özeti</h2>
{_table(summary_cols, summary_rows)}
<p class="muted">Geometri satırları aynı elemanın farklı kontrollere girdiği eleman-kontrol değerlendirmeleridir; benzersiz eleman sayısı değildir.</p>
<h2>ETABS model envanteri ve malzemeler</h2>
{_table((("type","Eleman türü"),("count","Adet")), census_rows)}
{_table((("name","Malzeme"),("code","ETABS kodu"),("status","Kaynak durumu"),("concrete","Beton")), materials)}
<h2>Kaynak tablo başlıkları ve kayıt sayıları</h2>
{_table((("role","Rol"),("key","Gerçek tablo adı"),("count","Satır"),("status","Durum"),("fields","Gözlenen alanlar")), tables)}
<h2>İzlenebilirlik</h2>
<p><strong>Input SHA-256:</strong> {_val(report['source_provenance']['input_sha256'])}<br>
<strong>Modal receipt SHA-256:</strong> {_val(report['source_provenance']['modal_receipt_sha256'])}<br>
<strong>Geometri receipt SHA-256:</strong> {_val(report['source_provenance']['geometry_receipt_sha256'])}</p>
{modal_section}
{''.join(check_sections)}
<p class="muted">Tüm ham kaynak tabloları, bütün eleman satırları ve malzeme tür kanıtları JSON dışa aktarımında bulunur.
Bu rapor, arşivlenen kayıtları aynı algoritmalarla tekrar doğrulayarak üretilmiştir.</p>
</body></html>'''
    return html


__all__ = ["ReportUnavailable", "build_complete_report", "build_printable_html"]
