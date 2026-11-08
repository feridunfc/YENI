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


def _vs05_check_inventory(checks: list[dict], story_drift: dict | None) -> dict:
    """Keep the eight historical checks and the STORY_DRIFT source check distinct."""
    entries = [{"check_id": c["check_id"], "evaluation": "BOUNDED_EXISTING"}
               for c in checks]
    if story_drift is not None:
        if story_drift.get("check_id") != "STORY_DRIFT":
            raise ValueError("UNEXPECTED_STORY_DRIFT_CHECK_ID")
        entries.append({"check_id": "STORY_DRIFT", "evaluation": "SOURCE_NUMERICAL",
                        "status": story_drift["status"],
                        "formal_compliance": "NOT_PROVEN"})
    ids = [e["check_id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_REPORTED_CHECK_ID")
    return {"entries": entries, "count": len(entries)}


def _vs05_summary_row(drift: dict) -> dict:
    """Numerical coverage does not imply normative checks met or failed."""
    expected = drift["expected_story_case_direction_count"]
    evaluated = drift["evaluated_story_case_direction_count"]
    if type(expected) is not int or type(evaluated) is not int or not (0 <= evaluated <= expected):
        raise ValueError("STORY_DRIFT_INVALID_COVERAGE")
    return {"check_id": "STORY_DRIFT", "status": drift["status"],
            "expected_count": expected, "evaluated_count": evaluated,
            "met_count": 0, "unmet_count": 0, "not_applicable_count": 0,
            "not_proven_count": expected}


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
    if not isinstance(geo_checks, list) or len(geo_checks) != 4:
        raise ReportUnavailable("Incomplete geometry check population")
    if {check.get("check_id") for check in geo_checks} != {"column_rect_min", "beam_width_min", "beam_depth_min", "beam_depth_width"}:
        raise ReportUnavailable("Check IDs differ from current registry")
    # Never promote a numerical subcondition to an overall regulatory PASS.
    modal_check = {
        **mapping["modal_mass_95"],
        **modal["result"],
        "check_id": "modal_mass_95",
        "formal_compliance": "NOT_PROVEN",
    }
    checks = [modal_check] + geo_checks
    new_checks = None
    if "next_capture" in source:
        from .next_checks import evaluate_next_capture
        receipt = _read_receipt(directory, "quick-extra")
        if receipt is None or receipt.get("input_sha256") != modal["input_sha256"]:
            raise ReportUnavailable("Missing VS03 receipt for captured VS03 sources")
        new_checks = evaluate_next_capture(source["next_capture"], geometry_source)
        if new_checks != receipt["payload"]:
            raise ReportUnavailable("VS03 source/receipt mismatch")
        checks.extend(new_checks["checks"])
    vs04 = None
    vs04_receipt = None
    vs04_numerics = None
    vs04_numeric_receipt = None
    vs04_readiness = None
    vs04_readiness_receipt = None
    vs04_pipeline = None
    vs04_pipeline_receipt = None
    if "analysis_sources" in source:
        from .analysis_sources import review_analysis_sources
        vs04_receipt = _read_receipt(directory, "vs04-schema")
        if vs04_receipt is None or vs04_receipt.get("input_sha256") != modal["input_sha256"]:
            raise ReportUnavailable("Missing or invalid VS04 source schema receipt")
        vs04 = review_analysis_sources(source["analysis_sources"])
        if vs04 != vs04_receipt["payload"]:
            raise ReportUnavailable("VS04 source/receipt mismatch")
        vs04_numeric_receipt = _read_receipt(directory, "vs04-numerics")
        expected = source["analysis_sources"].get("numeric_stage_required") is True
        if expected and (vs04_numeric_receipt is None or
                         vs04_numeric_receipt.get("input_sha256") != modal["input_sha256"]):
            raise ReportUnavailable("VS04 required numerical source receipt unavailable")
        if vs04_numeric_receipt is not None:
            from .analysis_numerics import evaluate_analysis_numerics
            if vs04_numeric_receipt.get("input_sha256") != modal["input_sha256"]:
                raise ReportUnavailable("VS04 numerical source input hash mismatch")
            vs04_numerics = evaluate_analysis_numerics(source["analysis_sources"])
            if vs04_numerics != vs04_numeric_receipt["payload"]:
                raise ReportUnavailable("VS04 numerical source/receipt mismatch")
        vs04_readiness_receipt = _read_receipt(directory, "vs04-readiness")
        readiness_required = source["analysis_sources"].get("readiness_stage_required") is True
        if readiness_required and (vs04_readiness_receipt is None or
                                   vs04_readiness_receipt.get("input_sha256") != modal["input_sha256"]):
            raise ReportUnavailable("VS04-E required readiness receipt unavailable")
        if vs04_readiness_receipt is not None:
            from .normative_basis import review_normative_readiness
            if vs04_readiness_receipt.get("input_sha256") != modal["input_sha256"]:
                raise ReportUnavailable("VS04-E readiness input hash mismatch")
            vs04_readiness = review_normative_readiness(source["analysis_sources"])
            if vs04_readiness != vs04_readiness_receipt["payload"]:
                raise ReportUnavailable("VS04-E readiness source/receipt mismatch")
        vs04_pipeline_receipt = _read_receipt(directory, "vs04-pipeline")
        pipeline_required = source["analysis_sources"].get("pipeline_stage_required") is True
        if pipeline_required and (vs04_pipeline_receipt is None or
                                  vs04_pipeline_receipt.get("input_sha256") != modal["input_sha256"]):
            raise ReportUnavailable("VS04 E-J required source pipeline receipt missing")
        if vs04_pipeline_receipt is not None:
            from .live_source_pipeline import evaluate_single_run_source_pipeline
            if vs04_pipeline_receipt.get("input_sha256") != modal["input_sha256"]:
                raise ReportUnavailable("VS04 E-J pipeline input hash mismatch")
            vs04_pipeline = evaluate_single_run_source_pipeline(source)
            if (vs04_pipeline != vs04_pipeline_receipt["payload"] or
                    vs04_pipeline.get("status") !=
                    "SOURCE_PIPELINE_EVALUATED_PENDING_ENGINEERING_REVIEW"):
                raise ReportUnavailable("VS04 E-J source/receipt content mismatch")

    # VS05 STORY_DRIFT is a candidate source-numeric check in this SAME
    # immutable run; verify the stage receipt by re-evaluating source.
    story_drift = None
    story_drift_receipt = _read_receipt(directory, "vs05-story-drift")
    if ("vs05_delta_source" in source or
            "vs05_delta_capture_error" in source):
        if (story_drift_receipt is None or
                story_drift_receipt.get("input_sha256") != modal["input_sha256"]):
            raise ReportUnavailable("VS05 STORY_DRIFT receipt missing or foreign")
        from .story_drift_binding import bind_story_drift
        story_drift = bind_story_drift(
            source.get("vs05_delta_source"),
            capture_error=source.get("vs05_delta_capture_error"))
        if story_drift != story_drift_receipt["payload"]:
            raise ReportUnavailable("VS05 STORY_DRIFT source/receipt mismatch")
    elif story_drift_receipt is not None:
        raise ReportUnavailable("Orphan VS05 STORY_DRIFT receipt")

    # VS06-A is a read-only projection of the already-verified VS05 record.
    # Never alter the historical receipt payload: exact replay is required.
    vs06_slot_ledger = None
    if (story_drift is not None and
            story_drift.get("execution_status") == "EXECUTED_SOURCE_NUMERICAL"):
        from .story_slot_ledger import build_story_slot_ledger
        try:
            vs06_slot_ledger = build_story_slot_ledger(
                source["vs05_delta_source"], story_drift)
        except (ValueError, TypeError, KeyError) as exc:
            raise ReportUnavailable("VS06 slot ledger cannot be reconciled") from exc

    # VS06-B is another read-only evidence projection. No change to original
    # VS05 receipt, check inventory, or the existing one-button COM workflow.
    vs06_physical_source_review = None
    if vs06_slot_ledger is not None:
        from .story_physical_source import review_story_physical_source
        try:
            vs06_physical_source_review = review_story_physical_source(
                source["vs05_delta_source"], story_drift, vs06_slot_ledger)
        except (ValueError, TypeError, KeyError) as exc:
            raise ReportUnavailable("VS06 physical-source review cannot be reconciled") from exc

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
    source_scope = ("modal 95% + 4 RC geometry screens"
                    + (" + concrete fck + A1 X/Y observed classification" if new_checks else "")
                    + (" + VS04-D analysis schema and five source arithmetic observations"
                       if vs04 else ""))
    if vs04_pipeline and vs04_pipeline.get("pipeline_contract_version") == "v2":
        source_scope += (
            " + VS04 E–J six source-only stages "
            "(initial E/F/G coverage retained; selected-case modal "
            "source reconciled when proven) "
            "+ five NOT_PROVEN regulatory evidence gates"
        )
    elif vs04:
        source_scope += " (E–J historical source evidence if recorded)"
    inventory = _vs05_check_inventory(checks, story_drift)
    if story_drift is not None:
        source_scope += (" + STORY_DRIFT ETABS-derived source numerical "
                         + str(story_drift["evaluated_story_case_direction_count"])
                         + "/" + str(story_drift["expected_story_case_direction_count"])
                         + " records (TBDY NOT_PROVEN)")
    return {
        "schema": "tbdy.next.complete.engineering.report.v1",
        "run_id": run_id,
        "title": (f"TBDY Next Engine — {inventory['count']} bounded checks"
                  + (" + VS04 E–J source evidence" if vs04_pipeline else "")
                  + " (not full TBDY design)"),
        "model": modal["model_name"],
        "captured_at_utc": modal["captured_at_utc"],
        "source_mode": modal["source_mode"],
        "modal_case": modal["case"],
        "engineering_release": "NOT_READY",
        "formal_compliance": "NOT_PROVEN",
        "scope": source_scope,
        "check_inventory": inventory,
        "vs04_source_summary": ({
            "pipeline_contract_version": vs04_pipeline.get("pipeline_contract_version"),
            "source_observed_count": vs04_pipeline.get("source_observed_count", 0),
            "source_diagnostic_resolved_count": vs04_pipeline.get(
                "source_diagnostic_resolved_count", 0),
            "source_unresolved_count": vs04_pipeline.get("source_unresolved_count", 0),
            "conditional_component_count": vs04_pipeline.get(
                "conditional_component_count", 0),
            "source_component_count": vs04_pipeline.get("source_component_count", 0),
            "regulatory_checks_executed": 0,
            "formal_compliance": "NOT_PROVEN",
        } if vs04_pipeline and vs04_pipeline.get("pipeline_contract_version") == "v2"
            else None),
        "vs04": vs04,
        "vs04_numerics": vs04_numerics,
        "vs04_readiness": vs04_readiness,
        "vs04_pipeline": vs04_pipeline,
        **({"story_drift": story_drift} if story_drift is not None else {}),
        **({"vs06_story_slot_ledger": vs06_slot_ledger}
           if vs06_slot_ledger is not None else {}),
        **({"vs06_physical_source_review": vs06_physical_source_review}
           if vs06_physical_source_review is not None else {}),
        "vs03": new_checks,
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
            "vs04_schema_receipt_sha256": vs04_receipt["receipt_sha256"] if vs04_receipt else None,
            "vs04_numerics_receipt_sha256": vs04_numeric_receipt["receipt_sha256"] if vs04_numeric_receipt else None,
            "vs04_readiness_receipt_sha256": vs04_readiness_receipt["receipt_sha256"] if vs04_readiness_receipt else None,
            "vs04_pipeline_receipt_sha256": vs04_pipeline_receipt["receipt_sha256"] if vs04_pipeline_receipt else None,
            "story_drift_receipt_sha256": story_drift_receipt["receipt_sha256"] if story_drift_receipt else None,
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
    modal, geometry, extras = checks[0], checks[1:5], checks[5:]
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
        *geometry, *extras,
    ]
    drift_summary = report.get("story_drift")
    if isinstance(drift_summary, Mapping):
        summary_rows.append(_vs05_summary_row(drift_summary))
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
    extra_cols = (("story", "Kat"), ("direction", "Yön"),
                  ("source_case", "Vaka"), ("material_name", "Malzeme"),
                  ("fck_mpa", "fck MPa"), ("eta_bi", "ηbi"),
                  ("value", "Değer"), ("limit", "Sınır"),
                  ("status", "Durum"), ("reason", "Neden"))
    for check in extras:
        check_sections.append('<section class="percheck"><h2>' + _val(check.get("title")) +
                              '</h2><p>Kaynak bazlı alt kontrol; formal compliance NOT_PROVEN</p>' +
                              _table(extra_cols, check.get("items", [])) + '</section>')
    vs04_sections = []
    if report.get("vs04"):
        v = report["vs04"]
        source_tables = ((report.get("source_snapshot") or {}).get("analysis_sources") or {}).get("tables") or {}
        overview = [dict(t) for t in (v.get("tables") or [])]
        vs04_sections.append('<section class="percheck"><h2>VS04 · Analiz kaynak şeması (henüz onaysız)</h2>'
                            '<p>Kaynak aritmetiği/koşullu hesaplar yönetmelik uygunluğu değildir. Formal uygunluk NOT_PROVEN; '
                            'analiz nesli ve kombinasyon rolleri onaylanmamıştır.</p>'
                            + _table((("table_key","ETABS tablosu"),("status","Kaynak durumu"),
                                      ("row_count","Satır"),("fields","Alanlar"),
                                      ("schema_sha256","Şema SHA-256"),("reason_codes","Engeller")), overview)
                            + "</section>")
        for record in overview:
            key = record.get("table_key")
            raw = source_tables.get(key) if isinstance(source_tables, Mapping) else None
            if not isinstance(raw, Mapping):
                continue
            fields = raw.get("fields") or []
            rows = raw.get("rows") or []
            if isinstance(fields, list) and isinstance(rows, list) and len(fields) == len(set(fields)):
                columns = tuple((name,name) for name in fields if isinstance(name,str))
                vs04_sections.append('<section class="percheck"><h2>VS04 ham ETABS kaynağı · '
                                    + _val(key) + "</h2>"
                                    + _table(columns, rows, "modal-grid") + "</section>")
    readiness = report.get("vs04_readiness")
    if readiness:
        cols = (("check_id", "Beklenen normatif hesap"),("code_ref", "TBDY"),
                ("status", "Kanıt durumu"),("missing_evidence", "Eksik bağımlılıklar"),
                ("source_only_hints", "Gözlenen ancak yetersiz kaynak"))
        vs04_sections.append('<section class="percheck"><h2>VS04-E · TBDY normatif kanıt kapıları</h2>'
                             '<p>Kaynak aritmetiği ile yönetmelik denetimi farklıdır. '
                             'Buradaki 5 beklenen kontrol henüz çalıştırılmamıştır; '
                             'bina uygunluğu NOT_PROVEN ve release NOT_READY.</p>'
                             + _table(cols, readiness.get("checks", [])) + '</section>')
    numeric = report.get("vs04_numerics")
    if numeric:
        numeric_cols = (("component", "Kaynak niceliği"), ("status", "Kaynak durumu"),
                        ("expected_row_count", "Görüntülenen satır"),
                        ("observed_row_count", "Aritmetik gözlem"),
                        ("reason_codes", "Engeller"))
        vs04_sections.append('<section class="percheck"><h2>VS04 · Sayısal kaynak tutarlılığı</h2>'
                             '<p>Yalnız kaynak aritmetiği: normatif kontrol sayısı 0. '
                             'Drift/ fiziksel anlamı ve analiz nesli henüz onaylanmamıştır.</p>'
                             + _table(numeric_cols, numeric.get("results", [])) + '</section>')
        for result in numeric.get("results", []):
            vs04_sections.append('<section class="percheck"><h2>VS04 · '
                                 + _val(result.get("component")) + '</h2>'
                                 + _table(tuple((k, k) for k in (
                                     tuple(result.get("items", [{}])[0].keys())
                                     if result.get("items") else ("reason",))),
                                     result.get("items") or []) + '</section>')
    pipeline = report.get("vs04_pipeline")
    if pipeline:
        source_cols = (("check_id", "Kaynak denetimi"), ("title", "Bileşen"),
                       ("source_status", "İlk kaynak durumu"),
                       ("status", "Bağlanmış kaynak durumu"),
                       ("execution_status", "Çalıştırılma"),
                       ("coverage", "Özgün kapsama / seçilmiş vaka"),
                       ("reason_codes", "Okuma teşhisi / gerekçe"),
                       ("missing_evidence", "Normatif eksik kanıt"),
                       ("formal_compliance", "TBDY uygunluğu"))
        vs04_sections.append('<section class="percheck"><h2>VS04 E–J · Tek çalışma kaynak zinciri</h2>'
                             '<p>Bu altı aşama, mevcut sekiz normatif alt kontrolün yerine geçmez. '
                             'Kütle mutabakatı, spektrum ve taban kesmesi taraması kaynak/koşul '
                             'düzeyindedir. Tam VtE, βtE ve etkin kat ötelenmesi NOT_PROVEN.</p>'
                             + _table(source_cols, pipeline.get("checks", [])) + '</section>')
        diag = pipeline.get("modal_display_selection_reconciliation")
        if diag:
            resolved = (diag.get("status") ==
                        "SOURCE_DISPLAY_SELECTION_DEPENDENCY_RECONCILED")
            diag_summary = (
                'İlk tablo okuması hatalı kalmıştır; özgün E/F/G sayaçları değişmez. '
                'RSX/RSY seçimiyle alınan 200 satır H/I kaynak kontrolleriyle '
                'eşleşmiştir. Yalnız kaynak bağımlılığı açıklanır.'
                if resolved else
                'İlk okuma ve seçilmiş vaka kaynakları henüz uzlaştırılamadı. '
                'Eksik kaynak kanıtı açık kalır.'
            )
            vs04_sections.append(
                '<section class="percheck"><h2>VS04 E/F/G · Seçim bağımlılığı</h2>'
                '<p>' + _val(diag_summary) +
                ' TBDY uygunluğu NOT_PROVEN.</p>'
                + _table((("table_key", "ETABS tablo kimliği"),
                          ("status", "Kaynak teşhis durumu"),
                          ("original_read_still_failed", "İlk okuma hâlâ hatalı"),
                          ("selected_case_row_count", "RSX/RSY satırları"),
                          ("reason_codes", "Gerekçeler"),
                          ("analysis_generation_proven", "Analiz nesli kanıtı")),
                         [diag]) + '</section>'
            )
        conditional = (pipeline.get("stages") or {}).get("vs04_j") or {}
        if conditional.get("conditional_eq_4_19_minimum_term_kn") is not None:
            vs04_sections.append('<section class="percheck"><h2>VS04-J · Koşullu taban kesmesi alt terimi</h2>'
                                 '<p>m, I ve SDS kaynak adaylarına dayalıdır; mühendislik '
                                 'kabulü veya VtE sonucu değildir.</p>'
                                 + _table((("source_mass_candidate_ton", "Aday kütle (ton)"),
                                           ("candidate_importance_factor", "Aday I"),
                                           ("candidate_SDS", "Aday SDS"),
                                           ("conditional_eq_4_19_minimum_term_kn",
                                            "Koşullu alt terim (kN)")),
                                          [conditional]) + '</section>')
    drift_check = report.get("story_drift")
    if isinstance(drift_check, Mapping):
        drift_cols = (("story", "Kat"), ("case", "Analiz vakası"),
                      ("direction", "Yön"), ("height_m", "h (m)"),
                      ("etabs_story_drift_ratio", "ETABS Drift"),
                      ("etabs_derived_delta_mm", "Δ adayı (mm)"),
                      ("etabs_reconciliation_residual_mm", "Fark (mm)"))
        vs04_sections.append(
            '<section class="percheck"><h2>STORY_DRIFT · Kat ötelemesi kaynak hesabı</h2>'
            '<p>Durum: ' + _val(drift_check.get("status")) +
            '; hesaplanan: ' + _val(drift_check.get("evaluated_story_case_direction_count")) +
            ' / ' + _val(drift_check.get("expected_story_case_direction_count")) +
            '. Bu sonuçlar ETABS Drift × kat yüksekliğinden üretilmiştir.'
            ' Eşzamanlı olmayan RSX/RSY düğüm maksimumları çıkarılmamıştır.'
            ' TBDY uygunluğu NOT_PROVEN.</p>' +
            _table(drift_cols, drift_check.get("items", [])) +
            '<h3>Eksik kat/vaka/yön sonuçları</h3>' +
            _table((("story", "Kat"), ("case", "Vaka"), ("direction", "Yön")),
                   drift_check.get("missing_story_case_direction", [])) +
            '</section>')
    ledger = report.get("vs06_story_slot_ledger")
    if isinstance(ledger, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-A · STORY_DRIFT kaynak slot muhasebesi</h2>'
            '<p>Beklenen slot: ' + _val(ledger.get("expected_slot_count")) +
            '; kaynaktan hesaplanan: ' + _val(ledger.get("source_numeric_count")) +
            '; kaynağı eksik: ' + _val(ledger.get("source_missing_count")) +
            '. Tüm satırlar muhasebeleştirilmiştir ancak fiziksel uygulanabilirlik ve '
            'TBDY uygunluğu NOT_PROVEN. Eksik satırlar sıfır veya kapsam dışı sayılmamıştır.</p>' +
            _table((("story", "Kat"), ("case", "Vaka"), ("direction", "Yön"),
                    ("source_status", "Kaynak"), ("source_delta_mm", "Δ adayı (mm)"),
                    ("physical_applicability", "Fiziksel uygulanabilirlik"),
                    ("normative_status", "TBDY durumu"), ("reason_code", "Açık kanıt")),
                   ledger.get("slots", [])) + '</section>')

    physical = report.get("vs06_physical_source_review")
    if isinstance(physical, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-B · Fiziksel kaynak ve spektral eşzamanlılık kanıtı</h2>'
            '<p>Gözlenen kolon bağlantısı: ' + _val(physical.get("endpoint_linked_column_count")) +
            ' / ' + _val(physical.get("observed_column_count")) +
            '; bağımsız RSX/RSY nokta maksimumu: ' +
            _val(physical.get("response_spectrum_independent_max_rows")) +
            '; eşzamanlı tasarım deplasman çifti kanıtlanan: ' +
            _val(physical.get("signed_concurrent_spectrum_design_pairs_proven")) +
            '. Kolonların gözlenmesi tam bina sayımı değildir; yokluk kapsam dışılık '
            'değildir. Fiziksel uygulanabilirlik ve yönetmelik uygunluğu NOT_PROVEN.</p>' +
            '<h3>Kat bazında gözlenen bağlantılar</h3>' +
            _table((("story", "Kat"), ("assigned_columns_observed", "Atanan kolon"),
                    ("endpoint_linked_columns_observed", "Uçları eşlenen"),
                    ("member_presence_evidence", "Kaynak bulgusu"),
                    ("physical_story_applicability", "Uygulanabilirlik")),
                   physical.get("observed_stories", [])) +
            '<h3>Kat / spektral vaka / yön kanıt sınırı</h3>' +
            _table((("story", "Kat"), ("case", "Vaka"), ("direction", "Yön"),
                    ("source_status", "Ötelenme kaynağı"),
                    ("member_presence_evidence", "Fiziksel kaynak"),
                    ("physical_applicability", "Uygulanabilirlik"),
                    ("signed_concurrent_spectrum_delta_available", "Eşzamanlı Δ"),
                    ("regulatory_status", "Yönetmelik")),
                   physical.get("slots", [])) +
            '<h3>Çözümlenemeyen kolon uç bağlantıları</h3>' +
            _table((("column", "Kolon"), ("story", "Kat"), ("reason", "Açık kanıt")),
                   physical.get("unresolved_columns", [])) + '</section>')

    a1_warnings = [
        c for c in extras if c.get("check_id") in ("a1_torsion_x", "a1_torsion_y")
        and any(item.get("status") == "A1_OBSERVED" for item in c.get("items", []))
    ]
    if a1_warnings:
        vs04_sections.append('<section class="percheck"><h2>A1 burulma düzensizliği — KAYNAK UYARISI</h2>'
                             '<p>En az bir kat/yönde ηbi &gt; 1,2 gözlendi. Dışmerkezlik '
                             'uygulaması ve tüm TBDY kapsamı doğrulanmadan nihai '
                             'uygunluk kararı verilemez.</p>'
                             + _table((("check_id", "Yön"), ("status", "Kaynak sınıflaması")),
                                      a1_warnings) + '</section>')
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
<p class="muted">{_val((report.get('check_inventory') or {}).get('count', len(checks)))} kapsamı sınırlı kontrol · STORY_DRIFT kaynak numeriği dahilse TBDY uygunluğu yine NOT_PROVEN · ETABS kaynak verisi</p>
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
{''.join(vs04_sections)}
{''.join(check_sections)}
<p class="muted">Tüm ham kaynak tabloları, bütün eleman satırları ve malzeme tür kanıtları JSON dışa aktarımında bulunur.
Bu rapor, arşivlenen kayıtları aynı algoritmalarla tekrar doğrulayarak üretilmiştir.</p>
</body></html>'''
    return html


__all__ = ["ReportUnavailable", "build_complete_report", "build_printable_html"]
