"""Source-pinned report regression, separate from ETABS integration replay.

Only existing YENI kernels are called. Missing production paths remain open;
the report's own result never becomes normative authority. Original audit ZIPs
and their independent arithmetic are retained, not relabeled as engine tests.
"""
from collections import Counter
from hashlib import sha256
from html import escape
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

from ..column_engine.native_archive import digest
from ..column_engine import ts500_column, section_capacity, scwb_kernel, joint_kernel
from . import report_oracles

SCHEMA = "tbdy.next.golden-regression-gate.v1"
MANIFEST_SHA256 = "59dedec19a7e6c3d5f496e8d616b8c708af3c99701e271bd872644e39361bec7"
ROOT = Path(__file__).parent
CLASSES = ("NUMERICAL_MATCH", "ENGINEERING_INTERPRETATION_DIFFERENCE", "INSUFFICIENT_SOURCE")
REQUIRED_DOMAINS = ("SECOND_ORDER", "PMM", "SCWB", "CAPACITY_SHEAR", "STORY_ALPHA")


class GoldenRegressionError(ValueError):
    pass


def load_bank(*, root=None, source_dir=None):
    """Revalidate small bundled evidence on every use; never execute ZIP code.

    A supplied source directory rehashes the four complete PDFs and both audit
    ZIPs. Without it, the read-only bank has reviewed, hash-pinned excerpts;
    it does not pretend to have re-read complete PDFs in CI or on Windows.
    """
    root = Path(root) if root is not None else ROOT
    raw = (root / "data/SOURCE_MANIFEST.json").read_bytes()
    if sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise GoldenRegressionError("GOLDEN_SOURCE_MANIFEST_CHANGED")
    manifest = json.loads(raw)
    files = {}
    for name, record in manifest["files"].items():
        raw = (root / name).read_bytes()
        if len(raw) != record["bytes"] or sha256(raw).hexdigest() != record["sha256"]:
            raise GoldenRegressionError("GOLDEN_SOURCE_CHANGED:" + name)
        files[name] = raw
    for archive in manifest["archives"]:
        with ZipFile(io.BytesIO(files[archive["bundled_path"]])) as z:
            actual = {i.filename for i in z.infolist() if not i.is_dir()}
            if actual != set(archive["members"]):
                raise GoldenRegressionError("GOLDEN_ARCHIVE_MEMBERS_CHANGED")
            for name, record in archive["members"].items():
                raw = z.read(name)
                if sha256(raw).hexdigest() != record["sha256"] or len(raw) != record["bytes"]:
                    raise GoldenRegressionError("GOLDEN_ARCHIVE_MEMBER_CHANGED:" + name)
    reports = {r["id"]: r for r in manifest["reports"]}
    evidence = json.loads(files["data/GOLDEN_EVIDENCE.json"])
    if {r["id"]: r["sha256"] for r in evidence["sources"]} != {k: v["sha256"] for k, v in reports.items()}:
        raise GoldenRegressionError("GOLDEN_REPORT_IDENTITY_CONFLICT")
    excerpts = json.loads(files["data/report_excerpts.json"])["pages"]
    for page in excerpts:
        if (page["source_pdf_sha256"] != reports[page["report_id"]]["sha256"]
                or sha256(page["text"].encode()).hexdigest() != page["text_sha256"]):
            raise GoldenRegressionError("GOLDEN_REPORT_EXCERPT_CHANGED")
    if source_dir is not None:
        source_dir = Path(source_dir)
        for row in (*reports.values(), *manifest["archives"]):
            name = row.get("file_name", row.get("original_filename"))
            raw = (source_dir / name).read_bytes()
            if sha256(raw).hexdigest() != row["sha256"] or len(raw) != row["bytes"]:
                raise GoldenRegressionError("GOLDEN_COMPLETE_SOURCE_CHANGED:" + name)
    with ZipFile(io.BytesIO(files["data/golden01.zip"])) as z:
        first = json.loads(z.read("fixtures.json"))
    with ZipFile(io.BytesIO(files["data/golden02.zip"])) as z:
        second = json.loads(z.read("COLUMN_GOLDEN_02/audit_fixture.json"))
    if (len(first["arithmetic_cases"]) != 23
            or first["model"]["source"]["sha256"] != reports["GOLDEN-01"]["sha256"]
            or second["sources_sha256"]["2.pdf"] != reports["GOLDEN-02"]["sha256"]):
        raise GoldenRegressionError("GOLDEN_FIXTURE_IDENTITY_CONFLICT")
    return manifest, first, second, excerpts


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise GoldenRegressionError("GOLDEN_NONFINITE_OR_INVALID_VALUE")
    return value


def compare_values(yeni, independent, report, report_tolerance):
    """Unexplained discrepancies raise; never hide them as interpretation.

    Tolerance to the printed report is separate from the tighter production
    versus independent arithmetic budget. Boolean outcomes require booleans.
    """
    tolerance = _finite(report_tolerance)
    if tolerance < 0:
        raise GoldenRegressionError("GOLDEN_NEGATIVE_TOLERANCE")
    if type(independent) is bool:
        if type(report) is not bool or independent is not report:
            raise GoldenRegressionError("GOLDEN_REFERENCE_REPORT_MISMATCH")
        if yeni is not None and (type(yeni) is not bool or yeni is not independent):
            raise GoldenRegressionError("GOLDEN_YENI_ORACLE_MISMATCH")
        differences = {"oracle_report_difference": 0, "yeni_oracle_difference": 0 if yeni is not None else None}
    else:
        independent, report = _finite(independent), _finite(report)
        if abs(independent-report) > tolerance:
            raise GoldenRegressionError("GOLDEN_REFERENCE_REPORT_MISMATCH")
        budget = 1e-9 + 1e-11*abs(independent)
        if yeni is not None and abs(_finite(yeni)-independent) > budget:
            raise GoldenRegressionError("GOLDEN_YENI_ORACLE_MISMATCH")
        differences = {"oracle_report_difference": abs(independent-report),
            "yeni_oracle_difference": abs(yeni-independent) if yeni is not None else None,
            "yeni_oracle_tolerance": budget}
    return {"classification": "NUMERICAL_MATCH" if yeni is not None else "INSUFFICIENT_SOURCE",
        "yeni": yeni, "independent": independent, "report": report,
        "report_rounding_tolerance": tolerance, **differences}


def _source(manifest, report_id, pages):
    r = next(r for r in manifest["reports"] if r["id"] == report_id)
    return {"report_id": report_id, "source_pdf_sha256": r["sha256"],
        "pdf_pages_1_based": pages, "scope": "SELECTED_REPORT_QUANTITIES_ONLY"}


def _scwb(first, manifest):
    x = next(c["inputs"] for c in first["arithmetic_cases"] if c["id"] == "SCWB_NUMERIC_INEQUALITY")
    context = scwb_kernel.JointCase("GOLDEN-01-P191", manifest["reports"][0]["sha256"],
        "P191-SZ03-S103-KZ13-KZ11", "X", 1, "REPORT_CAPACITIES", "REPORT_SUM_ONLY")
    rows = (("SZ03", "J", "COLUMN", x["Mr_lower"]), ("S103", "I", "COLUMN", x["Mr_upper"]),
        ("KZ13", "I", "BEAM", x["Mr_beam_left"]), ("KZ11", "J", "BEAM", x["Mr_beam_right"]))
    capacities = [scwb_kernel.MemberMomentCapacity(context, name, end, role, value, "GOLDEN-01-P191")
        for name, end, role, value in rows]
    # I/J are fixture role labels, not claimed ETABS native ends. This checks
    # aggregation of printed capacities, not topology or capacity derivation.
    return scwb_kernel.compute_scwb_joint_result(context,
        [("SZ03", "J"), ("S103", "I")], [("KZ13", "I"), ("KZ11", "J")], capacities)


def _first_adapters(first, manifest):
    model = first["model"]["from_pdf"]
    b, h = model["column_width_cm"]*10, model["column_depth_cm"]*10
    # Bar count/area alone is independent of coordinates. Two explicit layout
    # scaffolds exercise the existing perimeter constructor; neither supplies
    # report bar coordinates to a PMM solver.
    area = []
    for cover in (20, 40):
        bars, _, _ = section_capacity.perimeter(b, h, cover, 8, 14, 4, 4)
        if len(bars) != 12:
            raise GoldenRegressionError("GOLDEN_PROVIDED_BAR_COUNT_CHANGED")
        area.append(sum(v.area for v in bars)/100)
    if area[0] != area[1] or abs(area[0]-16) < .01:
        raise GoldenRegressionError("GOLDEN_REQUIRED_PROVIDED_AREA_CONFLATED")
    joint = {name: joint_kernel.centered_joint_limit(column_width_mm=b, column_depth_mm=h,
        beam_widths_mm=[model["beam_width_cm"]*10], fck_mpa=model["concrete_fck_MPa"],
        enclosure=kind)["geometric_limit_kn"] for name, kind in
        (("JOINT_UNCONFINED_LIMIT", "UNENCLOSED"), ("JOINT_CONFINED_LIMIT", "ENCLOSED"))}
    scwb = _scwb(first, manifest)
    return {"PROVIDED_AS": area[0], "AC": ts500_column.rectangle_properties(b,h)["area_mm2"]/100,
        **joint, "SCWB_COLUMN_SUM": scwb["sum_mrc_reference_knm"],
        "SCWB_BEAM_1P2_SUM": scwb["required_mrc_reference_knm"],
        "SCWB_NUMERIC_INEQUALITY": scwb["reference_satisfied"]}


def _beta(case, story):
    return ts500_column.moment_magnification_factors(nd_kn=case["Nd"], nk_kn=case["Nk"],
        sway=ts500_column.SWAY_PERMITTED, story_nd_kn=story["Nd"], story_nk_kn=story["Nk"])


def _second_comparisons(second, manifest):
    data = second["revised"]
    rows = []
    for case in data["member_cases"]:
        story = data["sum_N"][case["story"]]
        result = _beta(case, story)
        independent = report_oracles.member_beta(case["Nd"],case["Nk"])
        rows.append({"id": "G02_BETA_"+case["id"], "domain": "SECOND_ORDER", "legacy_group": "test_beta_member_ts500_denominator",
            **_source(manifest,"GOLDEN-02",[186]), "inputs": case, "yeni_kernel": "ts500_column.moment_magnification_factors",
            **compare_values(result["beta"],independent,case["beta"],.0052),
            "explanation": "Bireysel β karşılaştırması; lk/EI hesabı ve nihai büyütülmüş moment doğrulaması değildir."})
        if result["final_factor"] is not None or result["status"] != "EQ729_DECISION_NOT_PROVEN":
            raise GoldenRegressionError("GOLDEN_UNAPPROVED_EQ729_FACTOR_APPLIED")
        product = independent*report_oracles.member_beta(story["Nd"],story["Nk"])
        compare_values(None,product,case["reported_used"],.012)
        rows.append({"id": "G02_USED_FACTOR_"+case["id"], "domain": "SECOND_ORDER", "legacy_group": "test_report_used_is_product_arithmetically",
            **_source(manifest,"GOLDEN-02",[186]), "inputs": {"member":case,"story":story},
            "classification": "ENGINEERING_INTERPRETATION_DIFFERENCE", "yeni": None,
            "yeni_status": result["status"], "yeni_beta": result["beta"], "yeni_beta_story": result["beta_story"],
            "independent": product, "report": case["reported_used"], "report_quantity": "Alındı Eleman β",
            "oracle_report_difference": abs(product-case["reported_used"]), "report_rounding_tolerance": .012,
            "printed_symbol_probe": report_oracles.printed_eq729(case["lk"],case["Nd"]),
            "explanation": "Raporun Alındı değeri β×βs aritmetiğine uyuyor. YENI nihai çarpanı onaylamıyor; serbest boy, 7.29 politikası ve PMM aktarımı kanıtlı değil. Bireysel β ile Alındı β aynı büyüklük sayılmadı.",
            "normative_disagreement_resolved": False, "engineering_acceptance": False})
        probe = report_oracles.printed_eq729(case["lk"],case["Nd"])
        rows.append({"id":"G02_EQ729_"+case["id"],"domain":"SECOND_ORDER", "legacy_group":"test_ts500_729_requires_separate_branch_proof",
            **_source(manifest,"GOLDEN-02",[186]),"inputs":case,
            **compare_values(None,probe["product_branch_from_printed_symbol"],False,0),
            "independent_details":probe,"explanation":"Eski auditin lk/i duyarlılığı korunur. Kat yüksekliği fiziksel serbest boy olarak atanmaz; tam YENI 7.29 çağrısı için ln/k/mesnet ve politika kaynağı eksik."})
    for name, story in data["sum_N"].items():
        case = next(c for c in data["member_cases"] if c["story"] == name)
        result = _beta(case,story)
        rows.append({"id":"G02_STORY_BETA_"+name,"domain":"SECOND_ORDER", "legacy_group":"test_beta_story",
            **_source(manifest,"GOLDEN-02",[186]),"inputs":story,"yeni_kernel":"ts500_column.moment_magnification_factors",
            **compare_values(result["beta_story"],report_oracles.member_beta(story["Nd"],story["Nk"]),story["beta_s"],.005),
            "explanation":"Basılı kat toplamlarıyla βs aritmetiği; nüfusun tekil ve eksiksiz olduğu ayrıca doğrulanmalıdır."})
    for name, alpha in data["alpha"].items():
        independent = report_oracles.story_alpha(alpha["Vis"],alpha["Vik"])
        rows.append({"id":"G02_ALPHA_"+name,"domain":"STORY_ALPHA", "legacy_group":"test_alpha_ground_fails" if name=="ground" else "test_alpha_top",
            **_source(manifest,"GOLDEN-02",[189]),"inputs":alpha,
            **compare_values(None,independent,alpha["reported"],.00005),
            "below_070_reference":independent<.7,"one_column_repair_proven":False,
            "automatic_inverse_alpha_magnification_authorized":False,
            "explanation":"Bağımsız Vis/Vik hesabı raporla uyumlu. YENI kat α motoru ve eksiksiz tekil kat nüfusu bu sprintte bağlanmadı; tek kolonda donatı artırma veya 1/α ile kabul üretilmez."})
    changed = second["reference"]["ground_phi"] < .05 < data["phi"]["ground"]
    rows.append({"id":"G02_SWAY_BRANCH_CHANGED","domain":"SECOND_ORDER", "legacy_group":"test_sway_branch_changed",
        **_source(manifest,"GOLDEN-02",[185]),"inputs":{"old_phi":second["reference"]["ground_phi"],"new_phi":data["phi"]["ground"]},
        **compare_values(None,changed,True,0),"explanation":"Eski auditin değişen φ dalı doğrulanır; rapor φ değerlerini YENI'nin tam fiziksel kat hesabı üretmiş sayılmaz."})
    return rows


def build_golden_gate(*, source_dir=None):
    manifest, first, second, excerpts = load_bank(source_dir=source_dir)
    adapters = _first_adapters(first,manifest)
    rows = []
    for case in first["arithmetic_cases"]:
        key = case["id"]
        domain = "SCWB" if key.startswith("SCWB") else "REINFORCEMENT_AREA" if key=="PROVIDED_AS" else "REPORT_ARITHMETIC"
        pages = [183,196] if key=="PROVIDED_AS" else [case["source_pdf_page"]]
        explanation = case["comment"]
        if key not in adapters:
            explanation += " Eski bağımsız rapor hesabı korunmuştur; ilgili YENI üretim hesabı bu kayda bağlanmadı."
        elif key=="PROVIDED_AS":
            explanation += " Yalnız 12 çubuğun alanı sınandı; koordinatlar iki açık test yerleşimidir, rapora bağlı PMM geometrisi değildir."
        elif domain=="SCWB":
            explanation += " Basılı uç kapasitelerinin toplamı sınandı; I/J test rolüdür, native uç veya kapasite hesabı kanıtı değildir."
        rows.append({"id":"G01_"+key,"domain":domain,"legacy_case_id":key, **_source(manifest,"GOLDEN-01",pages),
            "inputs":case["inputs"],"formula":case["formula"],
            **compare_values(adapters.get(key),report_oracles.calculate(case),case["expected"],case["absolute_tolerance"]),
            "explanation":explanation.strip()})
    rows.extend(_second_comparisons(second,manifest))
    for name, report, domain, pages, reason in (
        ("PMM_REPORT_GATE","GOLDEN-01","PMM",[183,196,197],"Tam çubuk koordinatları, malzeme/eksen politikası, eşzamanlı talep ve bağımsız sabit-N/sabit-yön PMM referansı eksik; iki ayrı eksen kapasitesi 3B PMM golden sayılmaz."),
        ("CAPACITY_SHEAR_REPORT_GATE","GOLDEN-01","CAPACITY_SHEAR",[188,189],"Ma/Mu yetkisi, fiziksel ln, D dalı ve Vd alt sınırıyla çalışan YENI Ve yolu henüz rapora bağlanmadı; kaynak V veya birleşim Ve hesabı kolon kapasite kesmesi değildir."),
        ("GOLDEN03_REPORT_GATE","GOLDEN-03","SECOND_ORDER",[],"PDF hash'i doğrulandı; tamamlanmış rapor aritmetiği paketi ve YENI karşılaştırması bulunmadı."),
        ("GOLDEN04_REPORT_GATE","GOLDEN-04","SECOND_ORDER",[],"PDF hash'i doğrulandı; tamamlanmış rapor aritmetiği paketi ve YENI karşılaştırması bulunmadı.")):
        rows.append({"id":name,"domain":domain, **_source(manifest,report,pages),"classification":"INSUFFICIENT_SOURCE",
            "yeni":None,"independent":None,"report":None,"explanation":reason})
    classes = dict(Counter(r["classification"] for r in rows))
    domains = []
    for name in REQUIRED_DOMAINS:
        related = [r for r in rows if r["domain"]==name]
        domains.append({"domain":name,"classification_counts":dict(Counter(r["classification"] for r in related)),
            "report_golden_complete":False,"acceptance_eligible":False,
            "reason":"Seçili aritmetik karşılaştırmalar tam algoritma/kapsam kabulü sağlamaz."})
    modules = {"ts500_column":ts500_column,"section_capacity":section_capacity,"scwb_kernel":scwb_kernel,
        "joint_kernel":joint_kernel,"report_oracles":report_oracles}
    code_hashes = {name:sha256(Path(module.__file__).read_bytes()).hexdigest() for name,module in modules.items()}
    code_hashes["golden_gate"] = sha256(Path(__file__).read_bytes()).hexdigest()
    result = {"schema":SCHEMA,"source_manifest_sha256":MANIFEST_SHA256,"source_repositories":manifest["source_repositories"],
        "source_verification":"COMPLETE_PDF_AND_AUDIT_BYTES_REHASHED" if source_dir is not None else "PINNED_REVIEWED_EXCERPTS_AND_AUDIT_BYTES",
        "reports":manifest["reports"],"source_pdf_bytes_bundled":False,"record_count":len(rows),"classification_counts":classes,
        "legacy_reference_bank":{"golden01_comparisons":23,"golden01_reference_arithmetic_matches":23,
            "golden02_original_test_methods":7,"golden02_replayed_test_groups":sorted({r["legacy_group"] for r in rows if "legacy_group" in r}),
            "legacy_success_is_not_yeni_engine_acceptance":True},
        "independent_numerical_bank":{"repository":"feridunfc/Column","commit":manifest["source_repositories"]["Column"],
            "scope":"B7_SYNTHETIC_400x600_N500kN_TWO_CAGES", "is_golden_report_01_02":False,
            "oracle_sha256":manifest["files"]["references/column_oracle.py"]["sha256"],
            "different_point_bar_concrete_replacement_policy":True,
            "not_substituted_for_report_gate":True},
        "real_model_bank":{"source_sha256":manifest["real_model_archive_sha256"],"selected_columns":87,
            "role":"SOURCE_INTEGRATION_REGRESSION","not_substituted_for_report_gate":True},
        "algorithm_sha256":code_hashes,"required_domains":domains,"comparisons":rows,
        "negative_system_reference":{"golden01":"BLOCKED_A15_SYSTEM_MISMATCH","golden02_ground_alpha":report_oracles.story_alpha(34.872,55.6859),
            "single_column_repair_or_inverse_alpha_acceptance":False},
        "gate_status":"REQUIRED_REPORT_GOLDEN_COVERAGE_INCOMPLETE","acceptance_eligible":False,
        "normative_qualification":"NOT_PROVEN","engineering_release":"NOT_READY"}
    result["result_sha256"] = digest(result)
    return result


def golden_gate_summary(result=None):
    result = build_golden_gate() if result is None else result
    if result.get("result_sha256") != digest({k:v for k,v in result.items() if k!="result_sha256"}):
        raise GoldenRegressionError("GOLDEN_DERIVATION_CHANGED")
    return {key:result[key] for key in ("schema","result_sha256","source_manifest_sha256","source_verification",
        "record_count","classification_counts","legacy_reference_bank","required_domains","gate_status",
        "acceptance_eligible","normative_qualification","engineering_release")}


def build_golden_html(result):
    summary = golden_gate_summary(result)
    def cell(value):
        if value is None:return "—"
        if type(value) is float:return format(value,".9g")
        return str(value)
    rows = []
    for r in result["comparisons"]:
        values = (r["id"], ", ".join(map(str,r["pdf_pages_1_based"])), r.get("yeni"), r.get("independent"),
            r.get("report"), r["classification"], r["explanation"])
        rows.append("<tr>"+"".join("<td>"+escape(cell(v))+"</td>" for v in values)+"</tr>")
    return ("<!doctype html><html lang='tr'><meta charset='utf-8'><title>YENI · Golden regresyon kapısı</title>"
        "<style>body{font:15px system-ui;margin:2rem;color:#183047}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:8px;border-bottom:1px solid #ccd4dd;text-align:left}th{background:#edf2f7}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
        "<h1>Golden regresyon kapısı</h1><p><strong>Kabul kapsamı eksik · NOT_READY.</strong> YENI hesabı → bağımsız aritmetik → rapor → farkın açıklaması. Sayısal uyum, raporun veya modelin yönetmelik onayı değildir.</p>"
        "<p>GOLDEN-01'in 23 karşılaştırması ve GOLDEN-02'nin 7 eski test grubu korunur. Üretime bağlanmayan yollar INSUFFICIENT_SOURCE kalır. 87 kolonlu ETABS bankası ayrı kaynak entegrasyonu denetimidir.</p>"
        "<table><tr><th>Kontrol</th><th>PDF sayfası</th><th>YENI</th><th>Bağımsız</th><th>Rapor</th><th>Sınıf</th><th>Açıklama</th></tr>"
        +"".join(rows)+"</table><details><summary>Kaynak ve kabul kimliği</summary><pre>"
        +escape(json.dumps(summary,ensure_ascii=False,indent=2))+"</pre></details></html>")
