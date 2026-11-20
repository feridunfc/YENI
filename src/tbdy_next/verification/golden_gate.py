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

from .. import normative_basis
from ..column_engine.native_archive import digest
from ..column_engine import ts500_column, section_capacity, scwb_kernel, joint_kernel, story_alpha
from ..engineering import story_pdelta
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
    inputs = {case["id"]: case["inputs"] for case in first["arithmetic_cases"]}
    tbdy = inputs["AXIAL_TBDY_LIMIT"]
    ts500 = inputs["AXIAL_TS500_LIMIT"]
    area_mm2 = ts500_column.rectangle_properties(b, h)["area_mm2"]
    if not (tbdy["Ac_cm2"] == ts500["Ac_cm2"] == area_mm2 / 100):
        raise GoldenRegressionError("GOLDEN_AXIAL_SECTION_AREA_CONFLICT")
    axial_limits = ts500_column.section_axial_limits_kn(
        fck_mpa=tbdy["fck_MPa"], fcd_mpa=ts500["fcd_MPa"], ac_mm2=area_mm2,
    )
    drift = inputs["DRIFT_LAMBDA"]
    # The printed pair shares one acceleration scale. A common reference of
    # 1 m/s² per printed unit preserves the dimensionless ratio.
    drift_ratio = normative_basis.eq_4_9_lambda(
        sae_dd3_m_s2=drift["Sae_DD3"], sae_dd2_m_s2=drift["Sae_DD2"],
    )
    # Page 28 supplies cumulative weights, not individual story weights.
    # Compare only theta: no invented ETABS case or mass-source metadata and
    # no conclusion about the report's limit, beta or system applicability.
    theta = {}
    for key in ("THETA_GROUND", "THETA_UPPER"):
        values = inputs[key]
        theta[key] = story_pdelta.theta_ii_reference(
            cumulative_weight_kn=values["sum_W_above_kN"],
            average_reduced_drift_m=values["delta_avg_mm"] / 1000,
            story_shear_kn=values["story_shear_kN"], height_m=values["height_m"],
        )
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
    return {"PROVIDED_AS": area[0], "AC": area_mm2 / 100,
        "AXIAL_TBDY_LIMIT": axial_limits["tbdy_7_3_1_2_max_ndm_kn"],
        "AXIAL_TS500_LIMIT": axial_limits["ts500_eq_7_7_max_nd_kn"],
        "DRIFT_LAMBDA": float(drift_ratio),
        **theta, **joint, "SCWB_COLUMN_SUM": scwb["sum_mrc_reference_knm"],
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
            "explanation": "Individual β comparison. Verification of lk/EI and final magnified moments remains open."})
        if result["final_factor"] is not None or result["status"] != "EQ729_DECISION_NOT_PROVEN":
            raise GoldenRegressionError("GOLDEN_UNAPPROVED_EQ729_FACTOR_APPLIED")
        product = independent*report_oracles.member_beta(story["Nd"],story["Nk"])
        compare_values(None,product,case["reported_used"],.012)
        rows.append({"id": "G02_USED_FACTOR_"+case["id"], "domain": "SECOND_ORDER", "legacy_group": "test_report_used_is_product_arithmetically",
            **_source(manifest,"GOLDEN-02",[186]), "inputs": {"member":case,"story":story},
            "classification": "ENGINEERING_INTERPRETATION_DIFFERENCE", "yeni": None,
            "yeni_status": result["status"], "yeni_beta": result["beta"], "yeni_beta_story": result["beta_story"],
            "independent": product, "report": case["reported_used"], "report_quantity": "Adopted member β",
            "oracle_report_difference": abs(product-case["reported_used"]), "report_rounding_tolerance": .012,
            "printed_symbol_probe": report_oracles.printed_eq729(case["lk"],case["Nd"]),
            "explanation": "The reported adopted value matches β×βs. The final multiplier requires verified clear length, Eq. 7.29 policy and transfer to PMM. Individual and adopted β are distinct quantities.",
            "normative_disagreement_resolved": False, "engineering_acceptance": False})
        probe = report_oracles.printed_eq729(case["lk"],case["Nd"])
        rows.append({"id":"G02_EQ729_"+case["id"],"domain":"SECOND_ORDER", "legacy_group":"test_ts500_729_requires_separate_branch_proof",
            **_source(manifest,"GOLDEN-02",[186]),"inputs":case,
            **compare_values(None,probe["product_branch_from_printed_symbol"],False,0),
            "independent_details":probe,"explanation":"The historical audit preserves the lk/i sensitivity. Applying YENI Eq. 7.29 requires physical clear length, support and k evidence, and an approved policy."})
    for name, story in data["sum_N"].items():
        case = next(c for c in data["member_cases"] if c["story"] == name)
        result = _beta(case,story)
        rows.append({"id":"G02_STORY_BETA_"+name,"domain":"SECOND_ORDER", "legacy_group":"test_beta_story",
            **_source(manifest,"GOLDEN-02",[186]),"inputs":story,"yeni_kernel":"ts500_column.moment_magnification_factors",
            **compare_values(result["beta_story"],report_oracles.member_beta(story["Nd"],story["Nk"]),story["beta_s"],.005),
            "explanation":"βs arithmetic uses printed story totals. The uniqueness and completeness of that population require separate verification."})
    for name, alpha in data["alpha"].items():
        independent = report_oracles.story_alpha(alpha["Vis"],alpha["Vik"])
        result = story_alpha.evaluate_story_alpha_reference(vis_kn=alpha["Vis"], vik_kn=alpha["Vik"])
        rows.append({"id":"G02_ALPHA_"+name,"domain":"STORY_ALPHA", "legacy_group":"test_alpha_ground_fails" if name=="ground" else "test_alpha_top",
            **_source(manifest,"GOLDEN-02",[189]),"inputs":alpha,
            "yeni_kernel":"story_alpha.evaluate_story_alpha_reference",
            **compare_values(float(result["alpha"]),independent,alpha["reported"],.00005),
            "yeni_status":result["numeric_status"],
            "below_070_reference":result["classification_review_required"],"one_column_repair_proven":False,
            "automatic_inverse_alpha_magnification_authorized":False,
            "explanation":"YENI verified story α against the printed Vis and Vik totals. "
                          "The real story column population and SCWB evidence at both ends require separate source links."})
    changed = second["reference"]["ground_phi"] < .05 < data["phi"]["ground"]
    rows.append({"id":"G02_SWAY_BRANCH_CHANGED","domain":"SECOND_ORDER", "legacy_group":"test_sway_branch_changed",
        **_source(manifest,"GOLDEN-02",[185]),"inputs":{"old_phi":second["reference"]["ground_phi"],"new_phi":data["phi"]["ground"]},
        **compare_values(None,changed,True,0),"explanation":"The historical audit verifies the changing φ branch. Reproducing the reported φ values from the full physical story remains open."})
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
        production = {}
        if key not in adapters:
            explanation += " The historical independent report calculation is preserved. A link to the production YENI calculation remains pending."
        elif key in ("AXIAL_TBDY_LIMIT", "AXIAL_TS500_LIMIT"):
            production["yeni_kernel"] = "ts500_column.section_axial_limits_kn"
            explanation += " This compares the section limit in kN. Member demand and combination checks have their own scope."
        elif key == "DRIFT_LAMBDA":
            production["yeni_kernel"] = "normative_basis.eq_4_9_lambda"
            explanation += " This compares the printed DD3/DD2 ordinate ratio. Spectrum-period selection and the storey drift check have their own scope."
        elif key in ("THETA_GROUND", "THETA_UPPER"):
            production.update(
                yeni_kernel="engineering.story_pdelta.theta_ii_reference",
                quantity_unit="dimensionless",
                source_weight_kind="CUMULATIVE_AT_AND_ABOVE_STORY",
                source_directions=["X", "Y"],
            )
            explanation += (" This compares the page-28 theta scalar, printed identically for X and Y. "
                            "The cumulative weight is used once and the printed average drift is converted from mm to m once. "
                            "Story/source qualification, the theta limit, beta and the report's system acceptance are separate.")
        elif key=="PROVIDED_AS":
            explanation += " The check covers the area of 12 bars. Coordinates represent two test layouts. Report-linked PMM geometry requires independent evidence."
        elif domain=="SCWB":
            explanation += " The check sums the printed end capacities. I/J denote test roles. Native end identity and capacity calculation require independent evidence."
        rows.append({"id":"G01_"+key,"domain":domain,"legacy_case_id":key, **_source(manifest,"GOLDEN-01",pages),
            "inputs":case["inputs"],"formula":case["formula"], **production,
            **compare_values(adapters.get(key),report_oracles.calculate(case),case["expected"],case["absolute_tolerance"]),
            "explanation":explanation.strip()})
    rows.extend(_second_comparisons(second,manifest))
    for name, report, domain, pages, reason in (
        ("PMM_REPORT_GATE","GOLDEN-01","PMM",[183,196,197],"The 3D PMM reference requires full bar coordinates, material and axis policies, concurrent demand and independent fixed-N, fixed-direction results. The two axis references cover uniaxial capacity."),
        ("CAPACITY_SHEAR_REPORT_GATE","GOLDEN-01","CAPACITY_SHEAR",[188,189],"Linking YENI column capacity shear Ve to the report requires verified Ma/Mu, physical ln, the D branch and the Vd lower bound. The source V and joint Ve checks cover separate quantities."),
        ("GOLDEN03_REPORT_GATE","GOLDEN-03","SECOND_ORDER",[],"The PDF hash was verified. A completed report arithmetic package and YENI comparison are still pending."),
        ("GOLDEN04_REPORT_GATE","GOLDEN-04","SECOND_ORDER",[],"The PDF hash was verified. A completed report arithmetic package and YENI comparison are still pending.")):
        rows.append({"id":name,"domain":domain, **_source(manifest,report,pages),"classification":"INSUFFICIENT_SOURCE",
            "yeni":None,"independent":None,"report":None,"explanation":reason})
    classes = dict(Counter(r["classification"] for r in rows))
    domains = []
    for name in REQUIRED_DOMAINS:
        related = [r for r in rows if r["domain"]==name]
        domains.append({"domain":name,"classification_counts":dict(Counter(r["classification"] for r in related)),
            "report_golden_complete":False,"acceptance_eligible":False,
            "reason":"The arithmetic checks cover the listed comparisons. Overall algorithm and scope acceptance require further evidence."})
    modules = {"ts500_column":ts500_column,"section_capacity":section_capacity,"scwb_kernel":scwb_kernel,
        "joint_kernel":joint_kernel,"story_alpha":story_alpha,"report_oracles":report_oracles,
        "normative_basis":normative_basis,"story_pdelta":story_pdelta}
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
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><title>YENI · Golden regression gate</title>"
        "<style>body{font:15px system-ui;margin:2rem;color:#183047}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:8px;border-bottom:1px solid #ccd4dd;text-align:left}th{background:#edf2f7}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
        "<h1>Golden regression gate</h1><p><strong>Acceptance incomplete · NOT_READY.</strong> This report compares YENI and independent arithmetic against published values and explains differences. Code approval of the reports and models requires separate evidence.</p>"
        "<p>The gate preserves 23 GOLDEN-01 comparisons and seven historical GOLDEN-02 test groups. Paths awaiting production linkage are INSUFFICIENT_SOURCE. The 87-column ETABS bank verifies source integration separately.</p>"
        "<table><tr><th>Check</th><th>PDF page</th><th>YENI</th><th>Independent</th><th>Reported</th><th>Class</th><th>Explanation</th></tr>"
        +"".join(rows)+"</table><details><summary>Source and acceptance identity</summary><pre>"
        +escape(json.dumps(summary,ensure_ascii=False,indent=2))+"</pre></details></html>")
