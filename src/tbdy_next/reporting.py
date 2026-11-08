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


def build_column_bank_html(report: Mapping[str, Any]) -> str:
    """The existing report layer also presents an explicitly selected column archive."""
    members = []
    for row in report["members"]:
        ctx, geom = row.get("context", {}), row.get("station_geometry", {})
        frame, section, material = ctx.get("frame", {}), ctx.get("geometry") or {}, ctx.get("material") or {}
        members.append({"member": row["frame_name"], "story": frame.get("story_label"),
            "section": frame.get("section_assigned"), "rows": row["force_rows"],
            "elements": row["analysis_elements"], "b2": section.get("T2_cm"), "b3": section.get("T3_cm"),
            "fc": material.get("fc_MPa"), "fy": material.get("fy_MPa"),
            "length": geom.get("object_i_j_length_m"), "j_offset": geom.get("offset_j_m"),
            "face_span": geom.get("observed_output_face_span_m"), "j_is_joint": geom.get("last_station_is_joint_j"),
            "status": row["force_status"], "reason": row["reason_codes"]})
    replay = report["static_replay"]
    content = '<h1>Kolon kuvvet bankası ve statik birleşim doğrulaması</h1><p>' + _val(report["run_id"]) + '</p>'
    content += ('<p><strong>' + _val(report["observed_column_count"]) + '/' + _val(report["selected_column_count"]) +
        ' seçili kolon · ' + _val(report["force_row_count"]) + ' kuvvet satırı · ' +
        _val(report["recorded_output_count"]) + ' kayıtlı vaka/birleşim</strong></p>')
    content += ('<p>Bu arşivin model ve analiz kimliği seçili başka bir YENI kaydına otomatik bağlanmaz. ' +
        'Native P, V2, V3, T, M2, M3 işaretleri ve analiz elemanı/istasyon/adım kimlikleri korunur. ' +
        'RS veya zarfın aynı satırındaki bileşenler eşzamanlı tasarım vektörü olarak onaylanmaz. ' +
        'Mühendislik uygunluğu <strong>NOT_PROVEN / NOT_READY</strong>.</p>')
    content += '<h2>Kolonlar ve kaynak kesitleri</h2>' + _table((
        ("member", "Kolon"), ("story", "Kat"), ("section", "Kaynak kesiti"), ("b2", "b2 (cm)"),
        ("b3", "b3 (cm)"), ("fc", "Fc (MPa)"), ("fy", "Fy (MPa)"), ("rows", "Satır"),
        ("elements", "Analiz elemanları"), ("length", "I–J boyu (m)"), ("j_offset", "J offset (m)"),
        ("face_span", "Çıktı yüzleri arası (m)"), ("j_is_joint", "Son çıktı J düğümünde"),
        ("status", "Kaynak"), ("reason", "Açık neden")), members)
    content += ('<p>Çıktı yüzleri arası mesafe, TS500 serbest veya etkili boy kabulü değildir. ' +
        'Model donatı ayarları gerçek ya da seçilmiş tasarım kafesi yerine kullanılmaz.</p>')
    content += '<h2>Vaka/birleşim kapsamı</h2>' + _table((
        ("name", "Kaynak adı"), ("kind", "Tür"), ("case_type", "Native vaka türü"), ("operator", "Native işlem"),
        ("row_count", "Satır"), ("members_with_rows", "Verili kolon"), ("expected_members", "Beklenen"),
        ("step_types", "Adım türleri"), ("step_numbers", "Adım/mod numarası"), ("missing_members", "Eksikler")), report["case_coverage"])
    content += ('<h2>Statik Linear Add yeniden hesabı</h2><p>' + _val(replay["matched_rows"]) +
        ' satır / ' + _val(replay["scalar_comparisons"]) + ' skaler karşılaştırma. En büyük mutlak fark: ' +
        _val(replay["maximum_absolute_difference"]) + '. Sayısal tolerans: ' +
        _val(replay["absolute_tolerance_native"]) + ' + ' + _val(replay["relative_tolerance"]) +
        ' × max(|hesap|, |kaynak|); ilgili native kN veya kN-m biriminde.</p>')
    content += _table((("combination", "Birleşim"), ("status", "Kaynak aritmetiği"),
        ("expected_rows", "Beklenen satır"), ("matched_rows", "Eşleşen"), ("mismatched_rows", "Farklı"),
        ("unresolved_rows", "Çözümlenemeyen"), ("maximum_absolute_difference", "En büyük |Δ|"),
        ("reason", "Kapsam / neden")), replay["combinations"])
    historical = report.get("historical_reconciliation")
    if historical:
        content += '<h2>Tarihsel D7-B6 toplamları</h2>' + _table((
            ("story", "Kat"), ("output_case", "Vaka"), ("column_count", "Kolon"),
            ("native_signed_p_sum_kN", "Native ΣP (kN)"), ("historical_signed_p_kN", "Tarihsel ΣP (kN)"),
            ("difference_kN", "Fark (kN)"), ("numeric_match", "Sayısal eşleşme")), historical["items"])
        content += '<p>Bu karşılaştırma aynı fiziksel kesiti, analiz neslini veya kat φ yetkisini kanıtlamaz.</p>'
    content += '<h2>Sonraki hesapların girdileri</h2>' + _table((
        ("topic", "İş paketi"), ("available", "Kaynak / kullanılabilir yol"), ("remaining", "Tamamlanacak bağ")), report["engineering_gaps"])
    content += ('<h2>İzlenebilirlik</h2><p>Kaynak ZIP SHA-256: ' + _val(report["source_archive_sha256"]) +
        '<br>Veritabanı SHA-256: ' + _val(report.get("database_sha256")) +
        '<br>Hesap SHA-256: ' + _val(report["result_sha256"]) + '</p>')
    return ('<!doctype html><html lang="tr"><meta charset="utf-8"><title>YENI · Kolon kaynak raporu</title>' +
        '<style>body{font:14px/1.5 system-ui;margin:32px;color:#243345}h1{font-size:23px}h2{margin-top:30px}' +
        'table{border-collapse:collapse;width:100%;font-size:11px}th,td{border:1px solid #cfd8e3;padding:6px;text-align:left}' +
        'th{background:#eaf0f6}p{overflow-wrap:anywhere}@media print{thead{display:table-header-group}tr{break-inside:avoid}}</style>' + content + '</html>')


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


def _vs05_check_inventory(checks: list[dict], story_drift: dict | None,
                          b1: Mapping[str, Any] | None = None,
                          b1_source_status: str | None = None,
                          b2: Mapping[str, Any] | None = None,
                          wall_geometry: Mapping[str, Any] | None = None,
                          source_controls: Mapping[str, Any] | None = None,
                          earthquake_combinations: Mapping[str, Any] | None = None) -> dict:
    """Separate historical checks and source-derived checks; no fake code PASS."""
    entries = [{"check_id": c["check_id"], "evaluation": "BOUNDED_EXISTING"}
               for c in checks]
    if story_drift is not None:
        if story_drift.get("check_id") != "STORY_DRIFT":
            raise ValueError("UNEXPECTED_STORY_DRIFT_CHECK_ID")
        entries.append({"check_id": "STORY_DRIFT", "evaluation": "SOURCE_NUMERICAL",
                        "status": story_drift["status"],
                        "formal_compliance": "NOT_PROVEN"})
    if b1 is not None:
        if (b1.get("check_id") != "WEAK_STORY_B1"
                or b1.get("formal_compliance") != "NOT_PROVEN"
                or not isinstance(b1.get("b1_numerical"), Mapping)
                or b1["b1_numerical"].get("formal_compliance") != "NOT_PROVEN"
                or b1_source_status != "SOURCE_BOUND_NUMERICAL"):
            raise ValueError("B1_INVENTORY_SOURCE_CONTRACT_INVALID")
        numerical = b1["b1_numerical"]
        pairs = numerical.get("computed_story_direction_pairs")
        expected = numerical.get("expected_story_direction_pairs")
        if (type(pairs) is not int or type(expected) is not int
                or pairs < 1 or pairs != expected):
            raise ValueError("B1_INVENTORY_PAIR_COUNT_INVALID")
        entries.append({
            "check_id": "WEAK_STORY_B1",
            "evaluation": "CONDITIONAL_SOURCE_NUMERICAL",
            "status": numerical["numeric_condition"],
            "source_status": b1_source_status,
            "evaluated_count": pairs,
            "expected_count": expected,
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
        })
    elif b1_source_status is not None:
        # An attempted B1 source MUST remain visible even when it failed.
        entries.append({
            "check_id": "WEAK_STORY_B1",
            "evaluation": "BLOCKED_SOURCE",
            "status": "BLOCKED_SOURCE_BINDING",
            "source_status": b1_source_status,
            "evaluated_count": 0,
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY",
        })
    if b2 is not None:
        if (b2.get("check_id") != "SOFT_STORY_B2"
                or b2.get("formal_compliance") != "NOT_PROVEN"
                or b2.get("engineering_release") != "NOT_READY"):
            raise ValueError("B2_INVENTORY_SOURCE_CONTRACT_INVALID")
        entries.append({
            "check_id": "SOFT_STORY_B2",
            "evaluation": ("CONDITIONAL_SOURCE_NUMERICAL"
                           if b2["comparison_coverage"]["resolved"] else "BLOCKED_SOURCE"),
            "status": b2["numeric_condition"], "source_status": b2["status"],
            "expected_count": b2["expected_count"],
            "evaluated_count": b2["evaluated_count"],
            "comparison_coverage": b2["comparison_coverage"],
            "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
        })
    if wall_geometry is not None:
        if (wall_geometry.get("check_id") != "WALL_GEOMETRY_CHECK"
                or wall_geometry.get("formal_compliance") != "NOT_PROVEN"
                or wall_geometry.get("engineering_release") != "NOT_READY"):
            raise ValueError("WALL_GEOMETRY_INVENTORY_CONTRACT_INVALID")
        entries.append({"check_id": "WALL_GEOMETRY_CHECK",
            "evaluation": "CONDITIONAL_SOURCE_NUMERICAL" if wall_geometry["evaluated_count"] else
                          "NOT_APPLICABLE" if wall_geometry["status"] == "NOT_APPLICABLE" else "BLOCKED_SOURCE",
            "status": wall_geometry["numeric_condition"], "source_status": wall_geometry["status"],
            "expected_count": wall_geometry["expected_count"], "evaluated_count": wall_geometry["evaluated_count"],
            "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"})
    if source_controls is not None:
        from .source_control_bundle import CHECKS as SOURCE_CHECKS
        allowed = {c.check_id for c in SOURCE_CHECKS}
        for check in source_controls["checks"]:
            if (check.get("check_id") not in allowed or check.get("formal_compliance") != "NOT_PROVEN"
                    or check.get("engineering_release") != "NOT_READY"):
                raise ValueError("SOURCE_CONTROL_INVENTORY_CONTRACT_INVALID")
            entries.append({"check_id": check["check_id"],
                "evaluation": "CONDITIONAL_SOURCE_NUMERICAL" if check["evaluated_count"] else "BLOCKED_SOURCE",
                "status": check["status"], "expected_count": check["expected_count"],
                "evaluated_count": check["evaluated_count"], "formal_compliance": "NOT_PROVEN",
                "engineering_release": "NOT_READY"})
    if earthquake_combinations is not None:
        from .earthquake_combinations import CHECKS as COMBINATION_CHECKS
        allowed = {c.check_id for c in COMBINATION_CHECKS}
        for check in earthquake_combinations["checks"]:
            if (check.get("check_id") not in allowed or check.get("formal_compliance") != "NOT_PROVEN"
                    or check.get("engineering_release") != "NOT_READY"):
                raise ValueError("EARTHQUAKE_COMBINATION_INVENTORY_CONTRACT_INVALID")
            entries.append({"check_id": check["check_id"],
                "evaluation": "CONDITIONAL_SOURCE_NUMERICAL" if check["evaluated_count"] else
                              "NOT_APPLICABLE" if check["status"] == "NOT_APPLICABLE" else "BLOCKED_SOURCE",
                "status": check["status"], "expected_count": check["expected_count"],
                "evaluated_count": check["evaluated_count"], "not_applicable_count": check["not_applicable_count"],
                "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"})
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

    # VS06-C1: compile the existing 94-node candidate graph into the
    # expected STORY_DIRECTION denominator and blocked normative readiness.
    # The source-verified VS05 receipt remains immutable.
    vs06_effective_drift_readiness = None
    if vs06_physical_source_review is not None:
        from .compiled_dag import read_candidate_catalog
        from .effective_drift_readiness import review_effective_drift_readiness
        try:
            catalog_path = (Path(__file__).resolve().parents[2] / "config" /
                            "dag" / "tbdy_r1c_94_candidate.json")
            catalog = read_candidate_catalog(catalog_path)
            vs06_effective_drift_readiness = review_effective_drift_readiness(
                source["vs05_delta_source"], story_drift, vs06_slot_ledger,
                vs06_physical_source_review, catalog)
        except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            raise ReportUnavailable("VS06-C1 effective drift readiness invalid") from exc

    # VS06-D1: one-click live capture already has the two immutable ETABS
    # source blobs in the same run. Derive B1 X/Y numeric scenario here while
    # rechecking both source hashes; old VS05 archived receipts are unchanged.
    # B1 is optional: missing/unsupported source cannot break VS01-VS06-C2.
    vs06_b1_result = None
    vs06_b1_source_status = None
    from .physical_story_scope import review_physical_story_scope, scope_story_drift
    physical_scope = (review_physical_story_scope(source.get("vs05_delta_source"))
                      if "vs05_delta_source" in source else None)
    if ("vs06_b1_geometry_source" in source or "vs06_wall_load_source" in source
            or "vs06_b1_geometry_capture_error" in source):
        if (isinstance(source.get("vs06_b1_geometry_source"), Mapping) and
                isinstance(source.get("vs06_wall_load_source"), Mapping)):
            from .b1_source_bridge import B1BridgeError, evaluate_b1_sources
            try:
                vs06_b1_result = evaluate_b1_sources(
                    source["vs06_b1_geometry_source"],
                    source["vs06_wall_load_source"], physical_scope=physical_scope,
                    physical_scope_source=source.get("vs05_delta_source"))
                vs06_b1_source_status = "SOURCE_BOUND_NUMERICAL"
            except (B1BridgeError, ValueError, TypeError, KeyError) as exc:
                vs06_b1_source_status = "BLOCKED_SOURCE_BINDING: " + str(exc)
        else:
            vs06_b1_source_status = "BLOCKED_REQUIRED_B1_SOURCES_MISSING"

    # VS07 B2 reuses the SAME sealed source; historical receipts and their
    # evaluators are unchanged. Invalid B2 is local to this optional check.
    b2 = None
    if "vs05_delta_source" in source or "vs05_delta_capture_error" in source:
        from .soft_story_b2 import bind_soft_story_b2
        b2 = bind_soft_story_b2(
            source.get("vs05_delta_source"),
            capture_error=source.get("vs05_delta_capture_error"), physical_scope=physical_scope)

    # Project only AFTER exact legacy receipt/ledger replay. Never overwrite
    # archived source, receipts, or the historical candidate DAG denominator.
    declared_story_drift = story_drift
    if physical_scope is not None and story_drift is not None:
        story_drift = scope_story_drift(story_drift, source["vs05_delta_source"], physical_scope)

    wall_geometry = None
    if "vs06_b1_geometry_source" in source or "vs06_b1_geometry_capture_error" in source:
        from .wall_geometry import bind_wall_geometry
        wall_geometry = bind_wall_geometry(source, physical_scope=physical_scope)

    from .source_control_bundle import bind_source_controls
    source_controls = bind_source_controls(source)
    if not source_controls["checks"]:
        source_controls = None
    earthquake_combinations = None
    if "vs04_basis_probe" in source:
        from .earthquake_combinations import bind_earthquake_combinations
        earthquake_combinations = bind_earthquake_combinations(source)

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
    inventory = _vs05_check_inventory(
        checks, story_drift, vs06_b1_result, vs06_b1_source_status, b2, wall_geometry, source_controls,
        earthquake_combinations)
    if earthquake_combinations is not None:
        source_scope += " + VS10 orthogonal combination coefficients / observed directional coverage (TBDY NOT_PROVEN)"
    if source_controls is not None:
        source_scope += " + VS09 concrete upper strength / modal method source subconditions (TBDY NOT_PROVEN)"
    if wall_geometry is not None:
        source_scope += " + WALL_GEOMETRY_CHECK observed panel subconditions (TBDY NOT_PROVEN)"
    if b2 is not None:
        source_scope += " + SOFT_STORY_B2 assumed Avg Drift/h adjacent-source arithmetic (TBDY NOT_PROVEN)"
    if vs06_b1_result is not None:
        pair_count = vs06_b1_result["b1_numerical"]["computed_story_direction_pairs"]
        source_scope += (" + WEAK_STORY_B1 X/Y source numerical "
                         + str(pair_count) + " physically observed-story pairs"
                         + " (infill assumptions; TBDY NOT_PROVEN)")
    elif vs06_b1_source_status is not None:
        source_scope += " + WEAK_STORY_B1 source BLOCKED (no numeric result)"
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
        **({"physical_story_scope": physical_scope} if physical_scope is not None else {}),
        **({"declared_story_drift_source_record": declared_story_drift}
           if story_drift != declared_story_drift else {}),
        **({"vs06_story_slot_ledger": vs06_slot_ledger}
           if vs06_slot_ledger is not None else {}),
        **({"vs06_physical_source_review": vs06_physical_source_review}
           if vs06_physical_source_review is not None else {}),
        **({"vs06_effective_drift_readiness": vs06_effective_drift_readiness}
           if vs06_effective_drift_readiness is not None else {}),
        **({"vs06_b1_result": vs06_b1_result}
           if vs06_b1_result is not None else {}),
        **({"vs06_b1_source_status": vs06_b1_source_status}
           if vs06_b1_source_status is not None else {}),
        **({"soft_story_b2": b2} if b2 is not None else {}),
        **({"wall_geometry": wall_geometry} if wall_geometry is not None else {}),
        **({"source_controls": source_controls} if source_controls is not None else {}),
        **({"earthquake_combinations": earthquake_combinations} if earthquake_combinations is not None else {}),
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
    b2 = report.get("soft_story_b2")
    wall_geometry = report.get("wall_geometry")
    source_controls = report.get("source_controls")
    if isinstance(source_controls, Mapping):
        summary_rows.extend(source_controls["checks"])
    earthquake_combinations = report.get("earthquake_combinations")
    if isinstance(earthquake_combinations, Mapping):
        summary_rows.extend(earthquake_combinations["checks"])
    if isinstance(wall_geometry, Mapping):
        summary_rows.append({"check_id": "WALL_GEOMETRY_CHECK", "status": wall_geometry["status"],
            "expected_count": wall_geometry["expected_count"], "evaluated_count": wall_geometry["evaluated_count"],
            "met_count": 0, "unmet_count": 0, "not_applicable_count": wall_geometry["not_applicable_count"],
            "not_proven_count": wall_geometry["expected_count"] - wall_geometry["not_applicable_count"]})
    if isinstance(b2, Mapping):
        summary_rows.append({
            "check_id": "SOFT_STORY_B2", "status": b2["status"],
            "expected_count": b2["expected_count"],
            "evaluated_count": b2["evaluated_count"],
            "met_count": 0, "unmet_count": 0, "not_applicable_count": 0,
            "not_proven_count": b2["expected_count"],
        })
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
    physical_scope = report.get("physical_story_scope")
    if isinstance(physical_scope, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>Fiziksel kat kapsamı · B1 / B2 / STORY_DRIFT</h2>'
            '<p>Durum: ' + _val(physical_scope["status"]) +
            '; fiziksel kat: ' + _val(physical_scope["physical_story_count"]) +
            ' / tanımlı kat: ' + _val(physical_scope["defined_story_count"]) +
            '. NOT_APPLICABLE yalnız eksiksiz Frame/Area/Wall/Joint envanteriyle boşluğu '
            'doğrulanan katlara uygulanır. Bu envanter resmî TBDY kabulü değildir.</p>' +
            _table((("story", "Kat"), ("applicability", "Kapsam"), ("frames", "Frame"),
                    ("areas", "Area"), ("walls", "Wall (Area alt kümesi)"), ("joints", "Joint"),
                    ("reason", "Gerekçe")), physical_scope["stories"]) +
            '<p>Açık neden: ' + _val(physical_scope["reason_codes"]) +
            ' · Kapsam SHA: ' + _val(physical_scope["scope_sha256"]) + '</p></section>')
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
            '<p>Arşiv kaydı: fiziksel boş kat istisnasından önceki tanımlı kat kapsamıdır. '
            'Güncel uygulanabilir kapsam yukarıdaki STORY_DRIFT sonucundadır.</p>'
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
            '<p>Arşivdeki kolon ucu kanıt incelemesi; güncel tam nesne envanteri ve '
            'boş kat istisnaları ayrı fiziksel kat kapsamı tablosundadır.</p>'
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

    readiness = report.get("vs06_effective_drift_readiness")
    if isinstance(readiness, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-C1 · TBDY 4.9 etkin göreli kat ötelemesi hesap hazırlığı</h2>'
            '<p>Arşivdeki tanımlı kat muhasebesi korunmuştur; C2 senaryosu doğrulanmış '
            'boş kat istisnalarını uygular.</p>'
            '<p>94 düğümlü mevcut DAG üzerinden beklenen kat/yön kontrolleri: ' +
            _val(readiness.get("expected_story_direction_instances")) +
            '; ETABS kaynak-nümerik aday bulunan: ' +
            _val(readiness.get("source_numeric_primary_instances")) +
            '; temel kaynak eksiği: ' +
            _val(readiness.get("source_missing_primary_instances")) +
            '; aday FCR NOT_PROVEN: ' +
            _val(readiness.get("candidate_fcr_not_proven")) +
            '. Denk. (4.32)–(4.34) formel hesabı henüz yürütülmedi. '
            'Kaynak maksimumları eşzamanlı tasarım deplasmanı değildir. '
            'Boş tanımlı kotlar kanıt olmadan kapsam dışı sayılamaz.</p>' +
            _table((("check_instance_id", "DAG CheckInstance"),
                    ("case", "ETABS vakası"), ("source_numeric_status", "Kaynak"),
                    ("etabs_derived_delta_mm_candidate", "Kaynak Δ adayı (mm)"),
                    ("member_presence_evidence", "Fiziksel kaynak"),
                    ("physical_applicability", "Uygulanabilirlik"),
                    ("formula_execution", "Denklem yürütümü"),
                    ("regulatory_status", "TBDY durumu"),
                    ("required_source_evidence", "Eksik normatif kanıt")),
                   readiness.get("check_instances", [])) +
            '</section>')

    scenario = report.get("vs06_drift_scenario")
    if isinstance(scenario, Mapping):
        wall = scenario.get("wall_candidate_inventory") or {}
        options = scenario.get("scenario_input") or {}
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-C2 · TBDY 4.9 etkin göreli öteleme — SAYISAL SENARYO</h2>'
            '<p>Gevrek dolgu: Denk.(4.34a) / 0.008κ; esnek bağlantı: Denk.(4.34b) / '
            '0.016κ (deneye dayalı bağlantı kapasitesi ayrıca gereklidir). '
            'Bu tablo gerçekte gözlenen ETABS Story Drifts × h kaynak adaylarından '
            'oluşturulmuştur; tam fiziksel eşzamanlı deplasman ve resmî uygunluk '
            'kanıtı değildir. <strong>FORMAL COMPLIANCE: NOT_PROVEN</strong>.</p>' +
            _table((("r", "Varsayılan/senaryo R"), ("i", "Senaryo I"),
                    ("lambda", "Senaryo λ"), ("material", "Sistem"),
                    ("wall_type", "Dolgu bağlantısı"), ("coverage_pct", "Dolgu oranı %"),
                    ("wall_height_m", "Varsayılan duvar h (m)"),
                    ("opening_pct", "Açıklık %"), ("wall_mode", "Duvar kaynak modu"),
                    ("wall_load_pattern", "ETABS duvar yük deseni")),
                   [options]) +
            '<p>Yük deseni ' + _val(wall.get("load_pattern")) + ' gözlemi: ' + _val(wall.get("source_status")) +
            ' · Aday kiriş: ' + _val(wall.get("candidate_beam_count")) +
            ' · Aday toplam uzunluk (m): ' + _val(wall.get("candidate_total_length_m")) +
            ' · Varsayımsal net dolgu yüzey alanı (m²): ' +
            _val(wall.get("assumed_net_face_area_m2")) +
            '. Yük ataması fiziksel dolgu varlığının veya B1 etkin kesme alanının '
            'kanıtı değildir.</p>' +
            _table((("story", "Kat"), ("case", "Vaka"), ("direction", "Yön"),
                    ("source_delta_mm", "Kaynak Δ adayı (mm)"),
                    ("effective_delta_mm", "Etkin Δ senaryo (mm)"),
                    ("lambda_effective_ratio", "λ δ / h"),
                    ("limit", "Sınır"), ("utilization_ratio", "Kullanım oranı"),
                    ("conditional_numeric_condition", "Koşullu sayılsal sonuç"),
                    ("formal_compliance", "Resmî uygunluk")),
                   scenario.get("rows", [])) +
            '<p>Senaryo SHA-256: ' + _val(scenario.get("scenario_sha256")) +
            ' · Kaynak SHA-256: ' + _val(scenario.get("input_sha256")) +
            '. Esnek bağlantı seçimi için deneye dayalı kapasite belgesi: ' +
            _val(scenario.get("flexible_branch_capacity_accepted")) +
            '.</p></section>')

    b1 = report.get("vs06_b1_result")
    if isinstance(b1, Mapping):
        b1_numeric = b1.get("b1_numerical") or {}
        area_rows = []
        for story in b1.get("story_direction_areas", []):
            for d in ("X", "Y"):
                item = story.get(d) or {}
                area_rows.append({"story": story.get("story"), "direction": d,
                    "Aw_m2": item.get("column_Aw_m2"),
                    "Ag_m2": item.get("wall_Ag_m2"),
                    "Ak_m2": item.get("infill_Ak_assumed_m2"),
                    "K_proxy": item.get("infill_shear_stiffness_proxy_kN_m")})
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-D1 · B1 Zayıf Kat — sayısal kaynak senaryosu</h2>'
            '<p>TBDY 2018 Tablo 3.6, 3.6.2.3. Ae = Aw+Ag+0,15Ak. '
            'Kolon/perde gerçek kaynak geometrisidir; tuğla 9/19 cm ve '
            'kapı/pencere azaltması varsayımdır. Formel uygunluk NOT_PROVEN.</p>'
            '<p>ηci,min: ' + _val(b1_numeric.get("eta_ci_min")) +
            ' · Sayısal karar: ' + _val(b1_numeric.get("numeric_condition")) +
            ' · Fiziksel kat kapsamı: ' + _val(b1.get("physical_source_coverage", "UNKNOWN")) +
            ' · Gevrek dolgu varsayılanı: ' +
            _val((b1.get("parameters") or {}).get("wall_type")) + '</p>' +
            _table((("story", "Kat"), ("direction", "Yön"),
                    ("Aw_m2", "Aw (m²)"), ("Ag_m2", "Ag (m²)"),
                    ("Ak_m2", "Ak varsayım (m²)"),
                    ("K_proxy", "K_proxy (kN/m)")), area_rows) +
            _table((("lower_story", "Alt kat"), ("upper_story", "Üst kat"),
                    ("direction", "Yön"), ("eta_ci", "ηci"),
                    ("numeric_condition", "Sayısal durum")),
                   b1_numeric.get("paired_results", [])) +
            '<h3>Hesap varsayımları</h3><ol>' +
            ''.join('<li>' + escape(str(item)) + '</li>'
                    for item in b1.get("assumptions_notes", [])) +
            '</ol><p>Kaynak SHA: ' +
            _val((b1.get("provenance") or {}).get("geometry_capture_sha256")) +
            ' / ' +
            _val((b1.get("provenance") or {}).get("wall_load_capture_sha256")) +
            '. Mühendislik release NOT_READY.</p></section>')
    elif report.get("vs06_b1_source_status"):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-D1 · B1 veri eşleştirmesi</h2>'
            '<p>' + _val(report.get("vs06_b1_source_status")) +
            '. Önceki kabul edilmiş alt kontroller korunmuştur.</p></section>')

    if isinstance(b2, Mapping):
        coverage = b2["comparison_coverage"]
        vs04_sections.append(
            '<section class="percheck" data-check-panel="SOFT_STORY_B2">'
            '<h2>B2 yumuşak kat — koşullu kaynak hesabı</h2>'
            '<p>TBDY 2018 Tablo 3.6 / §3.6.2.1 · ηki = '
            '(Avg Driftᵢ / hᵢ) / (Avg Driftⱼ / hⱼ). Üst ve alt komşu ayrı ayrı '
            'karşılaştırılır; eşik ηki &gt; 2,0. Resmî B2 sınıflandırması: '
            '<strong>NOT_PROVEN</strong>.</p>'
            '<p>Kaynak durumu: ' + _val(b2["status"]) + '; hesap: ' +
            _val(b2["numeric_condition"]) + '. Çözülen komşuluk: ' +
            _val(coverage["resolved"]) + '/' + _val(coverage["expected"]) +
            '; çözülemeyen: ' + _val(coverage["unresolved"]) +
            '; kapsam: ' + _val(b2.get("source_coverage_status", "UNKNOWN")) + '.</p>' +
            _table((("story", "Kapsam dışı kat"), ("applicability", "Durum"),
                    ("reason", "Gerekçe")), b2.get("excluded_stories", [])) +
            '<details><summary>Kat kotu ve ara nokta eşleştirmesi</summary>' +
            '<p>Yalnız üst düzlem noktaları kat kotunu destekler. Ara ve alt sınır '
            'noktaları kat yüksekliğini değiştirmez. Tam nesne sayımı ayrı fiziksel kat '
            'kapsamı tablosunda gösterilir.</p>' +
            _table((("story", "Kat"), ("lower_elevation_m", "Alt kot (m)"),
                    ("upper_elevation_m", "Üst kot (m)"), ("at_level_points", "Üst düzlem noktası"),
                    ("intermediate_points", "Ara kotlu nokta"),
                    ("lower_boundary_points", "Alt sınır noktası")),
                   (b2.get("story_order") or {}).get("point_story_span_counts", [])) + '</details>' +
            _table((("story", "Kat"), ("direction", "Yön"), ("case", "Vaka"),
                    ("height_m", "h (m)"), ("average_drift_m", "Avg Drift (m)"),
                    ("status", "Kaynak"), ("reason", "Eksik / hata")),
                   b2["source_rows"]) +
            _table((("story", "İncelenen kat"), ("adjacent_story", "Komşu kat"),
                    ("neighbour_role", "Komşuluk"), ("direction", "Yön"), ("case", "Vaka"),
                    ("normalized_mean", "Avg Driftᵢ / hᵢ"),
                    ("adjacent_normalized_mean", "Avg Driftⱼ / hⱼ"),
                    ("eta_ki_candidate", "ηki adayı"), ("status", "Sayısal durum"),
                    ("reason_codes", "Açık neden")),
                   b2["items"]) +
            '<h3>Hesap kapsamı ve varsayımları</h3><ul>' +
            ''.join('<li>' + _val(s) + '</li>' for s in b2["assumptions_notes"]) +
            '</ul><p>Kaynak / hesap: ' + _val(b2["source_payload_sha256"]) +
            ' / ' + _val(b2["result_sha256"]) + '</p><p>Açık kaynak: ' +
            _val(b2["reason_codes"]) + '. ENGINEERING_RELEASE=NOT_READY.</p></section>')

    if isinstance(wall_geometry, Mapping):
        panel_rows = []
        for row in wall_geometry["items"]:
            panel_rows.append({**row, **{s["rule"]: s["status"] for s in row["subconditions"]}})
        vs04_sections.append(
            '<section class="percheck" data-check-panel="WALL_GEOMETRY_CHECK">'
            '<h2>Perde kesit geometrisi — koşullu kaynak alt kontrolleri</h2>'
            '<p>TBDY 2018 7.6.1.2 / 7.6.1.2(a). Hesaplanan panel: ' +
            _val(wall_geometry["evaluated_count"]) + '/' + _val(wall_geometry["expected_count"]) +
            '; sayısal alt koşul: ' + _val(wall_geometry["subconditions_evaluated"]) +
            '; karşılanmayan alt koşul: ' + _val(wall_geometry["subconditions_unmet"]) +
            '. Resmî uygunluk NOT_PROVEN.</p>' +
            _table((("story", "Kat"), ("element_id", "ETABS alan ID"), ("section", "Kesit"),
                    ("story_height_m", "h kat (m)"), ("panel_height_m", "h panel (m)"),
                    ("panel_length_m", "l panel (m)"), ("thickness_mm", "bw (mm)"),
                    ("panel_length_thickness_ratio", "l panel / bw"),
                    ("ordinary_branch_minimum_mm", "Standart dal bw,min (mm)"),
                    ("panel_ratio", "Oran ≥ 6"), ("thickness_250", "bw ≥ 250 mm"),
                    ("thickness_h16", "bw ≥ h/16"), ("reason", "Açık neden")), panel_rows) +
            '<h3>Uygulanabilirlik ve hesap sınırı</h3><ul>' +
            ''.join('<li>' + _val(s) + '</li>' for s in wall_geometry["assumptions_notes"]) + '</ul>' +
            _table((("code_ref", "Madde"), ("status", "Durum"), ("reason", "Eksik kanıt")),
                   wall_geometry["unevaluated_requirements"]) +
            '<p>Kaynak: ' + _val(wall_geometry["source_payload_sha256"]) +
            ' · Sonuç: ' + _val(wall_geometry["result_sha256"]) +
            ' · Kaynak teşhisi: ' + _val(wall_geometry["reason_codes"]) + '</p></section>')

    for bundle in (source_controls, earthquake_combinations):
        if not isinstance(bundle, Mapping):
            continue
        for check in bundle["checks"]:
            if check["check_id"] == "concrete_fck_80":
                columns = (("material_name", "Malzeme"), ("fck_mpa", "Fc kaynak (MPa)"),
                    ("limit", "Üst sınır (MPa)"), ("strength_scope_observation", "Sayısal kapsam"),
                    ("status", "Alt koşul"), ("reason", "Açık neden"))
            elif check["check_id"] == "modal_combination_spacing":
                columns = (("direction", "Yön"), ("source_case", "Vaka"), ("modal_case", "Modal vaka"),
                    ("modal_combination", "Mod birleştirme"), ("directional_combination", "Yön birleştirme"),
                    ("mode_count", "Mod sayısı"), ("maximum_period_ratio", "En büyük kısa/uzun oranı"),
                    ("spacing_status", "SRSS ayrıklık koşulu"), ("method_condition", "Seçilen yöntem koşulu"),
                    ("reason", "Açık neden"))
            elif check["check_id"] == "earthquake_100_30":
                columns = (("combination", "Birleşim"), ("operator", "İşlem"),
                    ("coefficient_x", "X katsayısı"), ("coefficient_y", "Y katsayısı"),
                    ("common_factor", "Ortak büyüklük"), ("minor_major_ratio", "Küçük / büyük"),
                    ("dominant_direction", "Baskın yön"), ("status", "Alt koşul"), ("reason", "Kapsam / teşhis"))
            else:
                columns = (("common_factor", "Ortak büyüklük"), ("other_case_coefficients", "Diğer vaka katsayıları"),
                    ("x_combinations", "X baskın birleşimler"), ("y_combinations", "Y baskın birleşimler"),
                    ("missing_directions", "Gözlenmeyen yön"), ("observed_sign_patterns", "Gözlenen işaretler"),
                    ("unresolved_combination", "Çözümlenemeyen birleşim"), ("status", "Kaynak kapsamı"),
                    ("reason", "Açık neden"))
            pair_tables = []
            alternatives = [{"envelope": item["combination"], **term}
                for item in check["items"] for term in item.get("envelope_alternatives", [])]
            if alternatives:
                pair_tables.append('<details><summary>Zarf seçenekleri · toplama yapılmaz</summary>' +
                    _table((("envelope", "Zarf"), ("ref", "Seçenek"), ("factor", "Çarpan"),
                            ("ref_type", "Kaynak türü")), alternatives) + '</details>')
            for item in check["items"]:
                if item.get("pairs"):
                    pair_tables.append('<details><summary>' + _val(item["source_case"]) +
                        ' · ' + _val(item["tested_adjacent_pair_count"]) + ' komşu çift / ' +
                        _val(item["all_distinct_pair_count"]) + ' farklı çift</summary>' +
                        _table((("short_mode", "Kısa T modu"), ("long_mode", "Uzun T modu"),
                            ("short_period_s", "Kısa T (s)"), ("long_period_s", "Uzun T (s)"),
                            ("period_ratio", "Oran"), ("limit", "Kesin üst sınır (<)"),
                            ("status", "SRSS ayrıklık koşulu")), item["pairs"]) + '</details>')
            vs04_sections.append('<section class="percheck" data-check-panel="' +
                escape(check["check_id"], quote=True) + '"><h2>' + _val(check["title"]) + '</h2><p>' +
                _val(check["code_ref"]) + ' · Hesaplanan ' + _val(check["evaluated_count"]) + '/' +
                _val(check["expected_count"]) + ' · Kapsam dışı: ' + _val(check["not_applicable_count"]) +
                ' · ' + _val(check["status"]) +
                '. Resmî uygunluk NOT_PROVEN.</p>' + _table(columns, check["items"]) +
                ''.join(pair_tables) + '<h3>Kapsam ve açık koşullar</h3><ul>' +
                ''.join('<li>' + _val(n) + '</li>' for n in check["assumptions_notes"]) + '</ul><p>' +
                _val(check["unevaluated_requirements"]) + '</p><p>Kaynak: ' +
                _val(check["source_provenance"]) + ' · Hesap: ' + _val(check["result_sha256"]) +
                ' · Teşhis: ' + _val(check["reason_codes"]) + '</p></section>')

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
