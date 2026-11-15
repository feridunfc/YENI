"""Complete VS01/VS02 report exports from existing verified local receipts.

Presentation only: uses *the same* modal and geometry evaluators to recheck the
archived payload against receipts. No ETABS, no new engineering authority, no
side effects. Full JSON preserves original source rows for independent audit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .check_labels import display_check, display_check_group
from .history import _MAX_SOURCE_BYTES, _RUN, _read_modal_run, _read_receipt
from .member_groups import geometry_groups, material_member_groups
from .quick_checks import check_registry, evaluate_geometry_capture


class ReportUnavailable(ValueError):
    """No verified five-check result exists for this run."""


def _column_cage_svg(cage, layout=None):
    """Draw the stored proposed bar coordinates; no structural calculation."""
    w,h = cage["t3_mm"],cage["t2_mm"]  # CSI native T3 is along local 2.
    content = ('<figure><svg xmlns="http://www.w3.org/2000/svg" role="img" width="200" height="200" ' +
        f'viewBox="{-w/2-60} {-h/2-60} {w+120} {h+120}" aria-label="' + escape(cage["label"],quote=True) +
        ' proposed section"><rect ' + f'x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" ' +
        'fill="#edf1f6" stroke="#64748b" stroke-width="3"/>')
    if layout:
        for leg in layout["legs"]:
            a,b = leg["endpoints_mm"]
            content += (f'<line x1="{a[0]}" y1="{-a[1]}" x2="{b[0]}" y2="{-b[1]}" '+
                f'stroke="#34786b" stroke-width="{leg["diameter_mm"]}" '+
                ('stroke-dasharray="12 6" ' if leg["kind"]=="CROSSTIE" else '')+'/>')
    for bar in cage["bars"]:
        content += f'<circle cx="{bar["x2_mm"]}" cy="{-bar["x3_mm"]}" r="{bar["diameter_mm"]/2}" fill="#214e78"/>'
    caption = ' · Diagram of tie and crosstie centerlines. Hook and vertical layouts await verification.' if layout else ''
    return content+'</svg><figcaption>'+escape(cage["label"])+caption+' · Local 2 points right and local 3 points up</figcaption></figure>'


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
    content = '<h1>Column force bank and static combination verification</h1><p>' + _val(report["run_id"]) + '</p>'
    content += ('<p><strong>' + _val(report["observed_column_count"]) + '/' + _val(report["selected_column_count"]) +
        ' selected columns · ' + _val(report["force_row_count"]) + ' force rows · ' +
        _val(report["recorded_output_count"]) + ' recorded cases and combinations</strong></p>')
    content += ('<p>This archive has its own model and analysis identity. Linking it to a separate YENI run requires verification. ' +
        'Native P, V2, V3, T, M2 and M3 signs and analysis element, station and step identifiers are preserved. ' +
        'Components from a response spectrum or envelope row require verification before use as a concurrent design vector. ' +
        'Engineering compliance is <strong>NOT_PROVEN / NOT_READY</strong>.</p>')
    content += '<h2>Columns and source sections</h2>' + _table((
        ("member", "Column"), ("story", "Story"), ("section", "Source section"), ("b2", "b2 (cm)"),
        ("b3", "b3 (cm)"), ("fc", "Fc (MPa)"), ("fy", "Fy (MPa)"), ("rows", "Row"),
        ("elements", "Analysis elements"), ("length", "I–J boyu (m)"), ("j_offset", "J offset (m)"),
        ("face_span", "Output-face spacing (m)"), ("j_is_joint", "Final output at node J"),
        ("status", "Source"), ("reason", "Open issue")), members)
    content += ('<p>TS500 clear and effective lengths require separate verification from output-face spacing. ' +
        'Verification of the actual or selected design cage requires independent evidence beyond the model reinforcement settings.</p>')
    content += '<h2>Case and combination coverage</h2>' + _table((
        ("name", "Source name"), ("kind", "Type"), ("case_type", "Native case type"), ("operator", "Native operation"),
        ("row_count", "Row"), ("members_with_rows", "Columns with data"), ("expected_members", "Expected"),
        ("step_types", "Step types"), ("step_numbers", "Step or mode number"), ("missing_members", "Eksikler")), report["case_coverage"])
    content += ('<h2>Static Linear Add recalculation</h2><p>' + _val(replay["matched_rows"]) +
        ' rows / ' + _val(replay["scalar_comparisons"]) + ' scalar comparisons. Maximum absolute difference ' +
        _number_html(replay["maximum_absolute_difference"], 6) + '. Numerical tolerance ' +
        _number_html(replay["absolute_tolerance_native"], 6) + ' + ' +
        _number_html(replay["relative_tolerance"], 6) +
        ' × max(|calculated|, |source|) in the corresponding native kN or kN·m unit.</p>')
    content += _table((("combination", "Combination"), ("status", "Source expression"),
        ("expected_rows", "Expected rows"), ("matched_rows", "Matched"), ("mismatched_rows", "Different"),
        ("unresolved_rows", "Unresolved"), ("maximum_absolute_difference", "Maximum |Δ|"),
        ("reason", "Coverage or issue")), replay["combinations"])
    chain = report.get("demand_chain")
    if chain:
        design = chain["design_summary"]
        content += ('<h2>CE-02 · Column force trace</h2><p>' + _val(chain["combination_count"]) +
            ' combinations and ' + _val(chain["static_candidate_count"]) + ' verified static source candidates. ' +
            'N = −P with compression positive. Local V2 and V3 signs are preserved. T, M2 and M3 are multiplied by 100 to convert to kN·cm. ' +
            'Tension is retained and the source signs at end J are preserved. The analysis order and design selection are ' +
            'NOT_PROVEN. The moments shown are the source values before magnification.</p>')
        content += _table((("combination", "Combination"), ("classification", "Source class"),
            ("case_names", "Source cases"), ("static_candidate_count", "Static candidate"),
            ("reason", "Open issue")), chain["combinations"])
        content += ('<h3>ETABS governing combination references</h3><p>' + _val(design["row_count"]) +
            ' design summary rows, ' + _val(design["reference_count"]) + ' PMM/VMaj/VMin references, ' +
            _val(design["known_combination_references"]) + ' links to defined combinations and ' +
            _val(design["unique_static_links"]) + ' links to unique static sources. ' +
            _val(design["ambiguous_design_station_rows"]) + ' duplicate station records and ' +
            _val(design["references_without_exact_station"]) + ' references lacking an exact station match ' +
            'are counted separately. These groups may overlap.</p>')
        content += ('<p>Matching uses the exact summary station. The PMMRatio field contains ' +
            _val(design["null_pmm_ratio_rows"]) + ' blank cells, which are treated as unknown. ' +
            'The mapping from VMaj/VMin to V2/V3 awaits verification. The ETABS design summary provides references. Full coverage of the selected design combinations ' +
            'and independent capacity verification require separate evidence.</p>')
        if design.get("reason"):
            content += '<p>Summary source ' + _val(design["reason"]) + '</p>'
        content += _table((("member_id", "Column"), ("static_candidate_count", "Static candidate"),
            ("design_rows", "Design row"), ("unique_static_links", "Unique static link"),
            ("pmm_combinations", "PMM references"), ("major_shear_combinations", "Major-axis shear"),
            ("minor_shear_combinations", "Minor-axis shear")), chain["members"])
        content += ('<p>The full JSON export includes each candidate’s seven-field native key, source row, ' +
            'combination factors, six force components and design summary links. ' +
            'The view is derived on read from the raw SQLite force bank.</p>')
        content += '<p>Demand view SHA-256 ' + _val(chain["result_sha256"]) + '</p>'
    prechecks = report.get("column_prechecks")
    if prechecks:
        critical, bounds = prechecks["critical_selection"], prechecks["reinforcement_bounds"]
        content += ('<h2>VS13 · Governing static records</h2><p>' + _val(critical["candidate_count"]) +
            ' static candidates yielded ' + _val(critical["critical_state_count"]) + ' source records flagged by the governing criteria. ' +
            'The selection retains ties and both signs. PMM requires the full demand population. ' +
            'Each reported vector uses components from a single source row.</p>')
        extrema = [{**m, **{c["criterion"]: c["magnitude"] for c in m["criteria"]}} for m in critical["members"]]
        content += _table((("member_id", "Column"), ("candidate_count", "Static candidate"),
            ("expected_static_states", "Expected source coverage"), ("source_subset_coverage", "Subset coverage"),
            ("N_COMPRESSION_MAX", "Compression (kN)"), ("N_TENSION_MAX", "Tension magnitude (kN)"),
            ("M2_ABS_MAX", "|M2| (kN·cm)"), ("M3_ABS_MAX", "|M3| (kN·cm)"),
            ("V2_ABS_MAX", "|V2| (kN)"), ("V3_ABS_MAX", "|V3| (kN)"), ("T_ABS_MAX", "|T| (kN·cm)")), extrema)
        content += ('<p>Each column is an independent extreme. Use the complete vectors and the criterion-to-state_id links ' +
            'in the JSON export for concurrent force components.</p>')
        content += ('<h2>Longitudinal reinforcement area limits · TBDY 2018 7.3.2.1</h2><p>' +
            _val(bounds["calculated_member_count"]) + '/' + _val(bounds["selected_member_count"]) +
            ' columns evaluated using Ac=b2×b3, As,min=0.01Ac and As,max=0.04Ac. ' +
            'Limits are inclusive. Ductility class, actual cage, bar diameter and count, and lap splice conditions require separate verification. ' +
            'The 6% limit at lap splices applies separately from the general 4% upper limit.</p>')
        content += _table((("member_id", "Column"), ("story", "Story"), ("section_name", "Section"),
            ("gross_area_cm2", "Ac (cm²)"), ("minimum_as_cm2", "As,min (cm²)"), ("maximum_as_cm2", "As,max (cm²)"),
            ("provided_as_cm2", "Verified installed As"), ("status", "Area calculation"), ("reason", "Open issue")), bounds["rows"])
        content += '<p>Numerical comparison with source AsMin ' + _val(bounds["source_comparison_counts"]) + '</p>'
        content += ('<p>Source AsMin is a model output. Differences from the reference bounds are numerical comparisons. ' +
            'Code compliance and engineering acceptance require further evidence. ' +
            'A governing axial demand for the code combination G+Q+E still requires verification.</p>')
        content += '<p>Preliminary calculation SHA-256 ' + _val(prechecks["result_sha256"]) + '</p>'
    stability = report.get("column_stability")
    if stability:
        content += ('<h2>VS14 · Section stiffness and lengths</h2><p>' + _val(stability["calculated_section_count"]) +
            ' columns with ' + _val(stability["distinct_section_count"]) + ' distinct rectangular sections and ' +
            _val(stability["native_property_match_count"]) + ' matching A, I and r source comparisons. ' +
            'E×I is the gross stiffness calculated with the observed modulus of elasticity. Effective and analysis stiffness require separate evidence. ' +
            'The report evaluates r=√(I/A) and the TS500 0.30h approximation separately.</p>')
        stiffness_rows = []
        for row in stability["sections"]:
            section, elastic = row["section"] or {}, row["elastic"] or {}
            stiffness_rows.append({**row, **section, **elastic, **row["lengths"]})
        content += _table((("member_id", "Column"), ("section_name", "Section"), ("i22_mm4", "I22 (mm⁴)"),
            ("i33_mm4", "I33 (mm⁴)"), ("r22_exact_mm", "r22 (mm)"), ("r33_exact_mm", "r33 (mm)"),
            ("observed_E_MPa", "E (MPa)"), ("object_i_j_m", "I–J (m)"), ("output_face_span_m", "Output spacing (m)"),
            ("property_comparison_status", "Source comparison")), stiffness_rows)
        content += ('<p>TS500 moment magnification requires verified clear length, k, sidesway classification, creep, ' +
            'end-moment curvature signs and analysis basis. ' +
            'The decision is NOT_PROVEN because the clear length in the text of 7.29 conflicts with the printed symbol lk.</p>')
        ecc = stability["eccentricity"]
        content += ('<h2>Minimum eccentricity reference · TS500 6.16</h2><p>Native T3 is the local 2 dimension and T2 is the local 3 dimension. e,min=15+0.03h (mm), with h=T2 for M2 and ' +
            'h=T3 for M3. ' + _val(ecc["state_count"]) + ' static source records with ' + _val(ecc["axis_comparison_count"]) +
            ' axis records. ' + _val(ecc["status_counts"]) + '. Rows without compression are listed separately. ' +
            'The rule applies to design end moments. Comparisons at interior stations serve as numerical references. ' +
            'Source vectors and full row traces are available in the JSON export.</p>')
        content += _table((("member_id", "Column"), ("candidate_count", "Static record"),
            ("m2_counts", "M2 source comparison"), ("m3_counts", "M3 source comparison")), ecc["members"])
        content += '<p>Stiffness and eccentricity SHA-256 ' + _val(stability["result_sha256"]) + '</p>'
        content += '<p>Dayanak: <a href="' + escape(stability["reference_url"], quote=True) + '">TS500/2000 copy (EMU)</a>.</p>'
    cages = report.get("column_cages")
    if cages:
        content += ('<h2>VS15 · Proposed reinforcement layouts</h2><p>' + _val(cages["bound_member_count"]) +
            ' columns with three proposed layouts each, 16Φ24, 16Φ28 and 16Φ32. The proposed Φ12 tie uses the TS500 7.4.1 minimum diameter. Installed or selected reinforcement requires separate evidence. ' +
            'CSI cover is measured to the outside face of the tie. Cover to the longitudinal bar center equals model cover plus proposed tie diameter plus φ/2. ' +
            'Model bar names are identifiers. Bar diameters come from the proposal.</p>')
        content += _table((("profile_id","Section profile"),("label","Proposal"),("as_cm2","As (cm²)"),
            ("rho_percent","ρ (%)"),("center_offset_mm","Cover to bar center (mm)"),
            ("minimum_clear_spacing_mm","Clear spacing (mm)"),("area_ratio_status","Area comparison"),
            ("spacing_status","Spacing coverage"),("reason","Open issue")),cages["candidates"])
        for cage in cages["candidates"]:
            layout = next((p["layout"] for p in (report.get("column_transverse") or {}).get("proposals",[])
                if p["candidate_id"]==cage["candidate_id"]),None)
            if cage["geometry_status"] == "PROPOSED_GEOMETRY_CALCULATED": content += _column_cage_svg(cage,layout)
        content += ('<p>The proposals cover longitudinal layouts. Tie and crosstie detailing, aggregate diameter, confinement, splices, ' +
            'bar availability and project material factor acceptance require verification. ' +
            'The three layouts are evaluated as candidates for engineering review.</p>')
        content += '<p>Reinforcement proposals SHA-256 '+_val(cages["result_sha256"])+ '</p>'
    pmm = report.get("column_pmm")
    if pmm:
        content += ('<h2>Conditional PMM · Full static source population</h2><p>' + _val(pmm["static_state_count"]) +
            ' static states × 3 layouts = ' + _val(pmm["assessment_count"]) + ' comparisons using the original source forces. ' +
            'N=−P. M2 and M3 use the CSI local signs. γc=1.5 and γs=1.15 are calculation scenario inputs pending project acceptance. ' +
            'Steel strain is evaluated at each bar center. The circular disk intersection area and first moments account for overlap with the concrete.</p>')
        content += '<p>Numerical states '+_val(pmm["status_counts"])+'. Open issues '+_val(pmm["reason_counts"])+'.</p>'
        summary_rows = []
        for item in pmm["members"]:
            summary_rows.append({**item,"maximum_resolved_utilization":round(item["maximum_resolved_utilization"],6)
                if item["maximum_resolved_utilization"] is not None else None,
                "critical_keys":[s["native_key"] for s in item["critical_resolved_states"]]})
        content += _table((("member_id","Column"),("story","Story"),("candidate_label","Proposal"),("as_cm2","As (cm²)"),
            ("static_state_count","Static record"),("maximum_resolved_utilization","Maximum resolved conditional ratio"),
            ("critical_keys","Governing source key"),("status_counts","Numerical coverage"),
            ("numeric_population_complete","Full numerical population")),summary_rows)
        content += ('<p>Angular sampling starts at 72, 144 and 288 and can refine to 1152. The force residual is ≤1 N. ' +
            'The difference between consecutive radial solutions is ≤0.001 kN·m plus a 0.2% relative allowance. These are observed convergence measures. ' +
            'Unresolved solutions and numerical boundary cases require review. The conditional ratio divides moment demand at fixed N by ' +
            'the strain-compatible capacity at the same N and moment direction. The ETABS design PMM ratio is a separate quantity. ' +
            'The solver finds N(c,θ)=Nsource and M2·u3−M3·u2=0 together within the finest angular bracket, ' +
            'with a direction residual ≤1000 N·mm. Axial equilibrium is solved at each intermediate angle using strain compatibility.</p>')
        content += ('<p>The calculation uses the source moments before minimum eccentricity or second-order adjustments. ' +
            'The complete seismic design population, actual reinforcement, detailing and final selection remain <strong>DENIED / NOT_PROVEN / NOT_READY</strong>. ' +
            'The full JSON includes each source vector, candidate ID, convergence history and resolved θ/c/N/M2/M3 point.</p>')
        content += '<p>Conditional PMM SHA-256 '+_val(pmm["result_sha256"])+ '</p>'
        content += '<p>Calculation references '+', '.join('<a href="'+escape(url,quote=True)+'">'+escape(name)+'</a>'
            for name,url in cages["references"].items())+'</p>'
    transverse = report.get("column_transverse")
    if transverse:
        content += ('<h2>VS16 · Proposed ties and crossties</h2><p>' + _val(transverse["bound_member_count"]) +
            ' columns with transverse reinforcement material linked to its native record. The Φ12/100 proposal uses one closed perimeter tie and ' +
            'three crossties per direction, with five assumed effective legs per direction. Lines show projected centerlines. Hooks, bends and vertical placement require verification. ' +
            'Native tie names and leg counts identify source records.</p>')
        content += _table((("profile_id","Section profile"),("confinement_material","Transverse reinforcement material"),
            ("observed_fywk_mpa","Source fywk (MPa)"),("scenario_fywd_mpa","Scenario fywd (MPa)"),
            ("steel_grade_compliance","Steel grade acceptance")),transverse["profiles"])
        proposal_rows = []
        for p in transverse["proposals"]:
            for name,axis in p["axes"].items():
                proposal_rows.append({**p,**axis,**axis["confinement"],"core_area_mm2":p["layout"]["core_area_mm2"]})
        content += _table((("candidate_label","Longitudinal proposal"),("shear_axis","Shear direction"),("bk_axis","bk ekseni"),
            ("core_area_mm2","Ack (mm²)"),("bk_mm","bk (mm)"),("asw_mm2","Asw (mm²)"),("ash_mm2","Ash (mm²)"),
            ("high_axial_required_ash_mm2","Ash at high N (mm²)"),("low_axial_required_ash_mm2","Ash at low N (mm²)"),
            ("maximum_lateral_leg_spacing_mm","Horizontal leg spacing (mm)"),("confinement_spacing_max_mm","Maximum confinement spacing s (mm)")),proposal_rows)
        content += ('<p>Ack is the outside-to-outside confined area, and bk is the distance between the outermost tie centerlines (TBDY 7.0). Ash uses leg projections perpendicular to bk. ' +
            'Asw uses legs parallel to the shear direction. Their numerical equality here follows from the orthogonal layout. ' +
            'birbirinin yerine konmaz. Denklem 7.1: max[0,30·s·bk·(Ac/Ack−1)·fck/fywk; 0,075·s·bk·fck/fywk]. ' +
            'The Nd≤0.20Acfck branch uses two-thirds of the high-load value. Both branches are shown pending verification of the full seismic axial load population. ' +
            'The separate spacing references are 50≤s≤min(bmin/3,6φlongitudinal,150) and horizontal spacing≤25φtie.</p>')
        content += ('<p>Actual confinement length requires verified clear length between beam faces and cantilever classification. ' +
            'The regular-column reference is max(ln/6,1.5hmax,500). The lower end of a cantilever uses 2hmax. Proposed hooks use ' +
            '135°/135°, inside bend diameter≥5φ and straight tail≥max(6φ,80). Fabrication details, overall compliance ' +
            'and final reinforcement selection remain NOT_PROVEN.</p>')
        content += '<p>Transverse reinforcement proposal SHA-256 '+_val(transverse["result_sha256"])+ '</p>'
    shear = report.get("column_shear")
    if shear:
        content += ('<h2>Conditional shear · Full static source population</h2><p>' + _val(shear["static_state_count"]) +
            ' static vectors × 3 proposals × 2 local directions = ' + _val(shear["assessment_count"]) +
            ' comparisons. For V2, bw=T2 and d=T3−cover to longitudinal bar center. For V3, bw=T3 and d=T2−cover to longitudinal bar center. ' +
            'Reference depth d uses the center of the opposite outer longitudinal layer. Design section acceptance remains open.</p>')
        content += ('<p>TS500 8.1 scenario with fctk=0.35√fck, fctd=fctk/1.5 and Vcr=0.65fctd·bw·d·(1+γ|N|/Ac), ' +
            'γ=0.07 in compression and γ=−0.30 in tension. Vc=0.8Vcr, Vw=(Asw/s)·fywd·d and Vr=Vc+Vw. A separate scenario uses Vc=0. ' +
            'A negative cracking factor leaves the branch with concrete contribution unresolved. The equilibrium Asw/s calculation ' +
            'covers |V|−Vc. Minimum reinforcement and detailing require separate checks.</p>')
        content += ('<p>Actual design Ve is NOT_PROVEN. The calculations use the recorded static-source V. ' +
            'The mandatory Vc=0 branch of TBDY 7.3.7.6 requires verified confinement location, seismic-only shear divided by total seismic-combination shear &gt;0.5 and ' +
            'Nd≤0.05Acfck. The JSON lists 0.85Ac√fck and the TS500 8.7 limit ' +
            '0.22fcd·bw·d as separate source comparisons. Applying the TS500 beam web provision to columns requires verification. ' +
            'Torsion interaction and second-order effects are outside this calculation.</p>')
        summary_rows = []
        for item in shear["members"]:
            ts,zero = item["branches"]["ts500"],item["branches"]["zero_concrete"]
            summary_rows.append({**item,"ts500_ratio":ts["maximum_source_utilization"],
                "zero_ratio":zero["maximum_source_utilization"],
                "critical_ts500":[r["native_key"] for r in ts["critical_source_states"]],
                "critical_zero":[r["native_key"] for r in zero["critical_source_states"]]})
        content += '<p>Numerical coverage '+_val(shear["status_counts"])+'. Open issues '+_val(shear["reason_counts"])+'.</p>'
        content += '<details><summary>Source comparisons by column, proposal and direction</summary>'+_table(
            (("member_id","Column"),("story","Story"),("candidate_label","Longitudinal proposal"),("shear_axis","Direction"),
             ("static_state_count","Static record"),("ts500_ratio","Maximum |V|/Vr · TS500"),("zero_ratio","Maximum |V|/Vr · Vc=0"),
             ("critical_ts500","Governing TS500 source"),("critical_zero","Governing Vc=0 source"),("status_counts","Numerical coverage")),summary_rows)+'</details>'
        content += '<p>Shear calculation SHA-256 '+_val(shear["result_sha256"])+'. <strong>DENIED / NOT_PROVEN / NOT_READY</strong>.</p>'
        content += '<p>Calculation references '+', '.join('<a href="'+escape(url,quote=True)+'">'+escape(name)+'</a>'
            for name,url in shear["references"].items())+'</p>'
    joints = report.get("column_joints")
    if joints:
        from .column_engine.column_joints import joint_summaries, joint_tie_summaries
        content += ('<h2>VS17 · Column–beam joint references</h2><p>' + _val(joints["joint_node_count"]) +
            ' native joints, ' + _val(joints["column_end_count"]) + ' column ends and ' + _val(joints["geometric_limit_count"]) +
            ' directional limits. Each end scenario assumes concentric, orthogonal sections at the joint center. ' +
            'Each row uses geometry from its end column. The stated lower column supplies the confinement reference. ' +
            'Physical joint faces and eccentricities require evidence beyond the native end connectivity.</p>')
        content += ('<p>TBDY 7.5.1 requires beams on all four sides and each beam width ≥75% of the corresponding column width. ' +
            'The confined and unconfined scenarios use 1.7 and 1.0, respectively, multiplied by bj×h×√fck. For a concentric joint, bj is governed by ' +
            'the column width and the narrowest beam width plus h. Dimensions are in mm, strength in MPa and results in kN. ' +
            '<strong>Joint Ve and SCWB are NOT_PROVEN</strong> pending beam reinforcement and seismic-compatible capacity states.</p>')
        content += '<p>Coverage '+_val(joints["status_counts"])+'. End scenarios '+_val(joints["enclosure_counts"])+'.</p>'
        if joints["graph"].get("reason"): content += '<p>Source link '+_val(joints["graph"]["reason"])+'.</p>'
        ends = joint_summaries(joints) if "rows" in joints else joints.get("end_summaries",[])
        content += '<details><summary>Column ends, beam connections and conditional shear limits</summary>'+_table((
            ("member_id","Geometry column"),("end","End"),("point_id","Joint"),("enclosure_scenario","Concentric classification"),
            ("beam_ids","Beams"),("limit_V2_kn","V2 limit (kN)"),("limit_V3_kn","V3 limit (kN)"),
            ("missing_faces","Face without a beam"),("narrow_faces","Narrow-beam face"),("status","Coverage"),("reason","Open issue")),ends)+'</details>'
        content += ('<h3>Joint confinement references · Eq. 7.1 basis</h3><p>The two lower-column axial load branches supply ' +
            'Ash/s references mapped to the physical direction. TBDY 7.5.2.3 applies the 40% and 60% factors to the same Φ12/100 proposal, ' +
            'using spacing limits of 150 and 100 mm and a minimum diameter of 8 mm. Capacity-based shear may require more reinforcement. ' +
            'The full joint requirement and actual reinforcement remain open.</p>')
        ties = joint_tie_summaries(joints) if "rows" in joints else joints.get("tie_summaries",[])
        content += '<details><summary>Confinement references by lower column, direction and proposal</summary>'+_table((
            ("member_id","End column"),("end","End"),("point_id","Joint"),("lower_column_id","Lower column"),
            ("axis","End direction"),("lower_axis","Lower column direction"),("candidate_label","Longitudinal proposal"),
            ("required_high_mm2","Ash at high N (mm²)"),("required_low_mm2","Ash at low N (mm²)"),
            ("proposed_ash_mm2","Proposed Ash (mm²)"),("spacing_mm","Proposed s (mm)"),("tie_reason","Open issue")),ties)+'</details>'
        content += '<p>Joint derivation SHA-256 '+_val(joints["result_sha256"])+'. '+', '.join(
            '<a href="'+escape(url,quote=True)+'">'+escape(name)+'</a>' for name,url in joints["references"].items())+'</p>'
    kinematics = report.get("column_kinematics")
    if kinematics:
        from .column_engine.column_kinematics import kinematic_summaries
        content += ('<h2>VS18 · Column end forces and joint movements</h2><p>' +
            _val(kinematics["linked_member_case_count"])+'/'+_val(kinematics["expected_member_case_count"])+
            ' column–combination source links. I/J forces come from the same single-valued static combination. '+
            'Intermediate stations remain in the demand trace. Output sections and end joints are reported at their respective locations. '+
            '<strong>Analysis order is NOT_PROVEN. Cm, β and magnified design moments are pending.</strong></p>')
        content += ('<p>Global U/R values are converted to verified I→J local axes. '+
            'L is the joint-to-joint length, with α2=−Δu3/L and α3=Δu2/L. R−α is the small joint rotation relative to the column chord. '+
            'Section end rotation, curvature and independent P–δ require separate calculations. The source table reports rounded displacements, '+
            'so a zero cell is limited by source precision.</p>')
        summary = kinematic_summaries(kinematics) if "rows" in kinematics else kinematics.get("summaries", [])
        content += '<details><summary>Source end forces for the same combination</summary>'+_table((
            ("member_id","Column"),("output_case","Combination"),("i_element","I analysis element"),("i_station_m","I station (m)"),
            ("j_element","J analysis element"),("j_station_m","J station (m)"),("i_P","I P (kN)"),("j_P","J P (kN)"),
            ("i_M2","I M2 (kN·m)"),("j_M2","J M2 (kN·m)"),("i_M3","I M3 (kN·m)"),("j_M3","J M3 (kN·m)"),
            ("status","Source link"),("force_reason","Open issue")),summary)+'</details>'
        content += '<details><summary>Joint movements and column chord</summary>'+_table((
            ("member_id","Column"),("output_case","Combination"),("point_i","I joint"),("point_j","J joint"),
            ("object_i_j_length_m","I–J boyu (m)"),("output_cut_span_m","Output-section spacing (m)"),
            ("delta_local_m","Δu1/2/3 (m)"),("chord_alpha2_rad","α2 (rad)"),("chord_alpha3_rad","α3 (rad)"),
            ("joint_i_relative_r2_rad","I R2−α2"),("joint_i_relative_r3_rad","I R3−α3"),
            ("joint_j_relative_r2_rad","J R2−α2"),("joint_j_relative_r3_rad","J R3−α3"),
            ("kinematics_reason","Open issue")),summary)+'</details>'
        content += '<details><summary>Recorded analysis stiffness basis</summary>'+_table((
            ("case_name","Case"),("stiffness_type","Stiffness setting"),("nonlinear_case_raw","Initial case record"),
            ("status","Source status"),("reason","Open issue")),kinematics["analysis_basis"]["cases"])+(
            '<p>Analysis order and full second-order behavior require independent verification of the linear static case and P-Delta settings. '+
            'A Nonlinear Case / None entry leaves the initial condition unverified.</p></details>')
        content += '<p>End derivation SHA-256 '+_val(kinematics["result_sha256"])+'. '+', '.join(
            '<a href="'+escape(url,quote=True)+'">'+escape(name)+'</a>' for name,url in kinematics["references"].items())+'</p>'
    sensitivity = report.get("column_sensitivity")
    if sensitivity:
        from .column_engine.column_sensitivity import sensitivity_summaries
        content += ('<h2>VS19 · Effective length and stiffness sensitivity</h2><p>'+
            _val(sensitivity["static_state_count"])+' static source records, '+_val(sensitivity["state_axis_count"])+
            ' axis records. '+_val(sensitivity["stiffness_scenario_count"])+' EI scenarios, '+
            _val(sensitivity["euler_reference_count"])+' Euler references and '+_val(sensitivity["zero_length_reference_count"])+
            ' lengths at which the equation denominator is zero. All intermediate stations and ties are retained.</p>')
        content += ('<p>TS500 7.19/7.21 gives EI(N·mm²)=0.4EcIc/(1+Rm) and Nk(kN)=π²EI/(1000lk(mm)²). Rm=0, 0.5 and 1 are scenario inputs. '+
            'Actual creep and effective stiffness require verification. The calculation uses i=0.30h and shows √(I/A) separately. '+
            'The 22i value is conditional for sidesway, 40i is an upper bound for sidesway prevented, '+
            'and 100i is the slenderness ceiling of the approximate method. Actual lk requires separate evidence.</p>')
        content += ('<p>lk,0(mm)=π√[EI/(1.3×1000×Nsource(kN))] is the length at which the Eq. 7.24 denominator equals zero. '+
            '<strong>Allowable effective length and the Euler length for Nk=N are separate quantities.</strong> '+
            'The approximate method remains limited to 100i. A positive denominator is a numerical result. '+
            'Engineering stability, Cm, β and design moments remain open.</p>')
        axes = sensitivity.get("axes", [])
        axis_rows, euler_rows = [], []
        for row in axes:
            axis_rows.append({**row, "ei_family": [format(s["effective_ei_nmm2_scenario"], ".6g") for s in row["scenarios"]]})
            for scenario in row["scenarios"]:
                euler_rows.append({"member_id":row["member_id"], "axis":row["axis"], "rm":scenario["creep_ratio_scenario"],
                    "nk_22":scenario["length_references"][0]["nk_kn_scenario"],
                    "nk_40":scenario["length_references"][1]["nk_kn_scenario"],
                    "nk_100":scenario["length_references"][2]["nk_kn_scenario"]})
        content += '<details><summary>Section, radius and EI scenarios</summary>'+_table((
            ("member_id","Column"),("axis","Axis"),("ec_mpa_observed","Ec (MPa)"),("gross_inertia_mm4","Ic (mm⁴)"),
            ("radius_reference_mm","i=0,30h (mm)"),("radius_exact_mm","√(I/A) (mm)"),
            ("length_22i_mm","22i (mm)"),("length_40i_mm","40i (mm)"),("length_100i_mm","100i (mm)"),
            ("ei_family","EI: Rm=0/0,5/1 (N·mm²)"),("status","Source"),("reason","Open issue")),axis_rows)+'</details>'
        content += '<details><summary>Euler loads at reference effective lengths</summary>'+_table((
            ("member_id","Column"),("axis","Axis"),("rm","Rm scenario"),("nk_22","Nk: 22i (kN)"),
            ("nk_40","Nk: 40i (kN)"),("nk_100","Nk: 100i (kN)")),euler_rows)+'</details>'
        summary = sensitivity_summaries(sensitivity) if "rows" in sensitivity else sensitivity.get("summaries", [])
        content += '<details><summary>Minimum denominator-zero lengths by column and axis</summary>'+_table((
            ("member_id","Column"),("axis","Axis"),("recorded_state_count","Static record"),
            ("maximum_source_n_kn","Maximum source N (kN)"),("minimum_zero_lengths_mm","lk,0: Rm 0/0,5/1 (mm)"),
            ("zero_lengths_exceed_100i","Beyond 100i"),("critical_source_states","All governing ties"),
            ("status_counts","Numerical coverage")),summary)+'</details>'
        content += '<p>Numerical coverage of reference denominators '+_val(sensitivity["denominator_status_counts"])+'.</p>'
        content += '<details><summary>Recorded axial force variation</summary>'+_table((
            ("member_id","Column"),("output_case","Combination"),("recorded_static_station_count","Station"),
            ("n_i_kn","I N (kN)"),("n_j_kn","J N (kN)"),("end_n_j_minus_i_kn","NJ−NI (kN)"),
            ("recorded_range_kn","N range across all records (kN)"),("recorded_values_status","Source observation")),
            sensitivity.get("axial_profiles", []))+('<p>TS500 7.6.2 requires a constant section and axial force, linear elastic analysis and a minimum-eccentricity basis. '+
            'Equal recorded N values address only one part of that evidence.</p></details>')
        content += ('<p>Sensitivity derivation SHA-256 '+_val(sensitivity["result_sha256"])+'. '+', '.join(
            '<a href="'+escape(url,quote=True)+'">'+escape(name)+'</a>' for name,url in sensitivity["references"].items())+
            ' · <strong>DENIED / NOT_PROVEN / NOT_READY</strong>.</p>')
    historical = report.get("historical_reconciliation")
    if historical:
        content += '<h2>Historical D7-B6 totals</h2>' + _table((
            ("story", "Story"), ("output_case", "Case"), ("column_count", "Column"),
            ("native_signed_p_sum_kN", "Native ΣP (kN)"), ("historical_signed_p_kN", "Tarihsel ΣP (kN)"),
            ("difference_kN", "Fark (kN)"), ("numeric_match", "Numerical match")), historical["items"])
        content += '<p>The physical cut, analysis generation and story φ authority require separate source verification.</p>'
    content += '<h2>Inputs for the next calculations</h2>' + _table((
        ("topic", "Work package"), ("available", "Source or available path"), ("remaining", "Link to verify")),
        report.get("engineering_evidence_gaps", report["engineering_gaps"]))
    content += ('<h2>Traceability</h2><p>Source ZIP SHA-256 ' + _val(report["source_archive_sha256"]) +
        '<br>Database SHA-256 ' + _val(report.get("database_sha256")) +
        '<br>Calculation SHA-256 ' + _val(report["result_sha256"]) + '</p>')
    if report.get("column_overview"):
        from .column_overview_report import overview_html
        from .column_quality_report import quality_html
        from .scwb_report import scwb_html
        from .beam_report import beam_html
        from .scenario_report import scenario_html
        quality = quality_html(report["column_pmm_quality"]) if report.get("column_pmm_quality") else ""
        scwb = scwb_html(report["column_scwb"]) if report.get("column_scwb") else ""
        beams = beam_html(report["beam_end_references"]) if report.get("beam_end_references") else ""
        scenarios = scenario_html(report['scwb_scenarios']) if report.get('scwb_scenarios') else ''
        content = overview_html(report["column_overview"]) + scenarios + scwb + beams + quality + '<details class="calculation-details"><summary>Source tables, formulas and intermediate calculations</summary>' + content + '</details>'
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>YENI · Column engineering summary</title>' +
        '<style>body{font:14px/1.5 system-ui;margin:32px;color:#243345}h1{font-size:23px}h2{margin-top:30px}' +
        'table{border-collapse:collapse;width:100%;font-size:11px}th,td{border:1px solid #cfd8e3;padding:6px;text-align:left}' +
        'th{background:#eaf0f6}p{overflow-wrap:anywhere}.overview-scroll{overflow-x:auto}.column-overview td{font-variant-numeric:tabular-nums}' +
        'details{margin:12px 0;border:1px solid #cfd8e3;border-radius:6px;padding:10px}summary{cursor:pointer;font-weight:600}' +
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;background:#f4f7fa;padding:12px}' +
        '@media print{thead{display:table-header-group}tr{break-inside:avoid}}</style>' + content + '</html>')


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

    # R08 source/check record: immutable one-run seal, exact re-evaluation
    # on every export; no new analysis and no trust in stored numeric payload.
    r08_second_order = None
    r08_receipt = _read_receipt(directory, "r08-second-order")
    if ("r08_second_order_source" in source or
            "r08_second_order_capture_error" in source):
        if (r08_receipt is None or
                r08_receipt.get("input_sha256") != modal["input_sha256"]):
            raise ReportUnavailable("R08 GLOBAL_SECOND_ORDER receipt missing or foreign")
        from .story_second_order import bind_story_second_order
        r08_second_order = bind_story_second_order(
            source.get("r08_second_order_source"),
            capture_error=source.get("r08_second_order_capture_error"))
        if r08_second_order != r08_receipt["payload"]:
            raise ReportUnavailable("R08 GLOBAL_SECOND_ORDER source/receipt mismatch")
    elif r08_receipt is not None:
        raise ReportUnavailable("Orphan R08 GLOBAL_SECOND_ORDER receipt")

    from .engineering.analysis_setup import DESIGN_COMBOS, STAGE, bind_analysis_setup
    analysis_setup = None
    setup_receipt = _read_receipt(directory, STAGE)
    if "vs04_basis_probe" in source:
        analysis_setup = bind_analysis_setup(source)
        basis = source["vs04_basis_probe"]
        table_reads = basis.get("table_reads") if isinstance(basis, Mapping) else None
        if setup_receipt is None:
            if isinstance(table_reads, Mapping) and DESIGN_COMBOS in table_reads:
                raise ReportUnavailable("R03 analysis setup receipt missing")
        elif (setup_receipt.get("input_sha256") != modal["input_sha256"]
                or setup_receipt["payload"] != analysis_setup):
            raise ReportUnavailable("R03 analysis setup source/receipt mismatch")
    elif setup_receipt is not None:
        raise ReportUnavailable("Orphan R03 analysis setup receipt")

    from .engineering.design_assignments import design_assignments

    from .engineering.column_axial import STAGE as AXIAL_STAGE, evaluate_column_axial
    axial = None
    axial_receipt = _read_receipt(directory, AXIAL_STAGE)
    if "column_axial" in source:
        if axial_receipt is None or axial_receipt["input_sha256"] != modal["input_sha256"]:
            raise ReportUnavailable("Column axial receipt missing or bound to another capture")
        try:
            axial = evaluate_column_axial(source, geometry, new_checks)
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            raise ReportUnavailable("Column axial source cannot be verified") from exc
        if axial != axial_receipt["payload"]:
            raise ReportUnavailable("Column axial source/receipt mismatch")
    elif axial_receipt is not None:
        raise ReportUnavailable("Orphan column axial receipt")

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
        from .compiled_dag import CANDIDATE_CATALOG_PATH, read_candidate_catalog
        from .effective_drift_readiness import review_effective_drift_readiness
        try:
            catalog = read_candidate_catalog(CANDIDATE_CATALOG_PATH)
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
    declared_second_order = r08_second_order
    if physical_scope is not None and story_drift is not None:
        story_drift = scope_story_drift(story_drift, source["vs05_delta_source"], physical_scope)
    if physical_scope is not None and r08_second_order is not None:
        from .story_second_order import scope_story_second_order
        r08_second_order = scope_story_second_order(
            r08_second_order, source.get("r08_second_order_source"),
            source.get("vs05_delta_source"), physical_scope)

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
    if axial is not None:
        inventory["entries"].append({
            "check_id": axial["check_id"], "evaluation": "SELECTED_COMBINATION_NUMERICAL",
            "status": axial["status"], "expected_count": axial["expected_member_combination_count"],
            "evaluated_count": axial["evaluated_member_combination_count"],
            "formal_compliance": axial["formal_compliance"],
        })
        inventory["count"] += 1
    if r08_second_order is not None:
        inventory["entries"].append({
            "check_id": "GLOBAL_SECOND_ORDER",
            "evaluation": ("CONDITIONAL_SOURCE_NUMERICAL" if
                           r08_second_order["evaluated_story_direction_count"] else
                           "BLOCKED_SOURCE"),
            "status": r08_second_order["status"],
            "expected_count": r08_second_order["expected_story_direction_count"],
            "evaluated_count": r08_second_order["evaluated_story_direction_count"],
            "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
        })
        inventory["count"] += 1
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
    if r08_second_order is not None:
        source_scope += (" + GLOBAL_SECOND_ORDER source-numerical " +
                         str(r08_second_order["evaluated_story_direction_count"]) +
                         "/" + str(r08_second_order["expected_story_direction_count"]) +
                         " story-direction records (global P-Delta NOT_PROVEN)")
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
        "vs04_pipeline": display_check_group(vs04_pipeline),
        **({"analysis_setup": analysis_setup} if analysis_setup is not None else {}),
        "design_assignments": design_assignments(analysis_setup or {}),
        **({"column_axial": axial} if axial is not None else {}),
        **({"story_drift": story_drift} if story_drift is not None else {}),
        **({"r08_second_order": r08_second_order}
           if r08_second_order is not None else {}),
        **({"physical_story_scope": physical_scope} if physical_scope is not None else {}),
        **({"declared_story_drift_source_record": declared_story_drift}
           if story_drift != declared_story_drift else {}),
        **({"declared_r08_second_order_source_record": declared_second_order}
           if r08_second_order != declared_second_order else {}),
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
        "vs03": display_check_group(new_checks),
        "checks": [display_check(check) for check in checks],
        "material_member_groups": material_member_groups(checks),
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
            "r08_second_order_receipt_sha256": r08_receipt["receipt_sha256"] if r08_receipt else None,
            **({"analysis_setup_receipt_sha256": setup_receipt["receipt_sha256"] if setup_receipt else None}
               if analysis_setup is not None else {}),
            **({"column_axial_receipt_sha256": axial_receipt["receipt_sha256"]} if axial is not None else {}),
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


_DECIMAL_TEXT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_DIMENSION_FIELDS = re.compile(r"(?:^|_)(?:knm?|nmm\d*|mpa|mm\d*|cm\d*|m[234]|ton)(?:_|$)", re.I)
_ETABS_MASS_FIELDS = frozenset(("UX", "UY", "UZ", "RX", "RY", "RZ",
                                "SumUX", "SumUY", "SumUZ", "SumRX", "SumRY", "SumRZ"))
_ETABS_OTHER_NUMERIC = frozenset(("Period", "Frequency", "CircFreq", "Eigenvalue",
                                  "FX", "FY", "FZ", "MX", "MY", "MZ", "Drift", "K_proxy"))


def _number_html(value: Any, places: int) -> str:
    raw = str(value)
    if type(value) not in (float, int, Decimal, str) or not _DECIMAL_TEXT.fullmatch(raw):
        return _val(value)
    number = Decimal(raw)
    if number.is_zero():
        shown = "0"
    elif number.adjusted() > 14 or number.adjusted() < -places:
        mantissa, power = format(number, ".2E").split("E")
        shown = f"{mantissa.rstrip('0').rstrip('.')}e{power}"
    else:
        shown = format(number, f".{places}f").rstrip("0").rstrip(".")
    if shown == raw:
        return _val(value)
    return f'<span title="{_val(value)}">{escape(shown)}</span>'


def _cell_html(key: str, value: Any) -> str:
    if key == "members_by_story" and isinstance(value, list):
        return "<br>".join(f"{_val(row['story'])} · {_val(row['member_ids_text'])}" for row in value)
    if (key.startswith(("theta_", "normalized_", "adjacent_normalized_", "relative_error_"))
            or key in ("Drift", "drift_raw", "etabs_story_drift_ratio", "average_drift_m",
                       "adjacent_average_drift_m", "etabs_avg_drift_m_candidate",
                       "etabs_reconciliation_residual_mm", "maximum_absolute_difference",
                       "lambda_effective_ratio")):
        return _number_html(value, 6)
    if (_DIMENSION_FIELDS.search(key)
            or key in ("FX", "FY", "FZ", "MX", "MY", "MZ", "K_proxy")):
        return _number_html(value, 2)
    if (type(value) in (float, Decimal) or key in _ETABS_MASS_FIELDS
            or key in _ETABS_OTHER_NUMERIC or key.endswith(("_m", "_s"))
            or key.startswith(("eta_", "beta_", "candidate_", "coefficient_"))
            or "ratio" in key
            or key in ("value", "limit", "factor", "common_factor", "threshold", "b2", "b3",
                       "fc", "fy", "length", "j_offset", "face_span",
                       "circular_frequency_rad_sec", "eigenvalue_rad2_sec2",
                       "expected_circular_frequency_rad_sec", "expected_eigenvalue_rad2_sec2",
                       "expected_frequency_cyc_sec", "observed_reciprocal_product")):
        return _number_html(value, 4)
    return _val(value)


def _table(columns: tuple[tuple[str, str], ...], rows: list[Mapping[str, Any]], cls: str = "") -> str:
    header = "".join(f"<th>{escape(title)}</th>" for _, title in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{_cell_html(key, item.get(key))}</td>" for key, _ in columns) + "</tr>"
        for item in rows
    )
    return f'<table class="{cls}"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'


def _with_material_members(items: list[dict], roster: list[dict]) -> list[dict]:
    by_material = defaultdict(list)
    for group in roster:
        if group["material_name"] is not None:
            by_material[group["material_name"]].append(group)
    return [{**item, **group} for item in items
            for group in by_material.get(item.get("material_name"), [{}])]


def build_printable_html(report: Mapping[str, Any]) -> str:
    """Self-contained print-ready HTML. All five checks and every member row."""
    checks = report["checks"]
    modal, geometry, extras = checks[0], checks[1:5], checks[5:]
    summary_cols = (
        ("check_id", "Check"), ("status", "Numerical status"),
        ("expected_count", "Element-check pairs"), ("evaluated_count", "Calculated"),
        ("met_count", "Pass"), ("unmet_count", "Fail"),
        ("not_applicable_count", "Out of scope"), ("not_proven_count", "Unresolved"),
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
    r08_summary = report.get("r08_second_order")
    if isinstance(r08_summary, Mapping):
        summary_rows.append({
            "check_id": "GLOBAL_SECOND_ORDER",
            "status": r08_summary["status"],
            "expected_count": r08_summary.get("declared_story_direction_count",
                                              r08_summary["expected_story_direction_count"]),
            "evaluated_count": r08_summary["evaluated_story_direction_count"],
            "met_count": 0, "unmet_count": 0,
            "not_applicable_count": r08_summary.get("not_applicable_story_direction_count", 0),
            "not_proven_count": r08_summary["expected_story_direction_count"],
        })
    b1_summary = next((row for row in report.get("check_inventory", {}).get("entries", [])
                       if row["check_id"] == "WEAK_STORY_B1"), None)
    if b1_summary:
        summary_rows.append(dict(b1_summary, met_count=0, unmet_count=0, not_applicable_count=0,
                                 not_proven_count=b1_summary.get("expected_count")))
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
        ("story", "Story"), ("element_id", "ETABS Unique ID"), ("section", "Assigned section"),
        ("material_name", "Material"), ("material_classification", "Material classification"),
        ("width_mm", "t2 mm"), ("depth_mm", "t3 mm"),
        ("value", "Check value"), ("limit", "Limit"), ("ratio", "Ratio"),
        ("status", "Status"), ("reason", "Diagnostic"),
    )
    group_cols = (("member_count", "Members"), ("members_by_story", "ETABS Unique IDs by story")) + section_cols[2:]
    check_sections = []
    for i, check in enumerate(geometry, 1):
        desc = (f"<h2>{i:02d}. {_val(check.get('title'))}</h2>"
                f"<p><strong>{_val(check.get('code_ref'))}</strong> · "
                f"Numerical status {_val(check.get('status'))} · "
                f"Coverage {_val(check.get('expected_count'))}, "
                f"Calculated {_val(check.get('evaluated_count'))}, "
                f"Fail {_val(check.get('unmet_count'))}, "
                f"Out of scope {_val(check.get('not_applicable_count'))}, "
                f"Unresolved {_val(check.get('not_proven_count'))}</p>")
        items = check.get("items", [])
        grouped = _table(group_cols, check.get("member_groups") or geometry_groups(items))
        detail = ('<details><summary>Individual member rows</summary>' + _table(section_cols, items) + '</details>') if items else ''
        check_sections.append(f'<section class="percheck">{desc}{grouped}{detail}</section>')
    roster_cols = (("member_count", "Members"), ("member_type", "Member type"),
                   ("material_classification", "Material classification"), ("members_by_story", "ETABS Unique IDs by story"))
    material_roster = (report.get("material_member_groups")
                       if "material_member_groups" in report else material_member_groups(geometry))
    extra_cols = (("story", "Story"), ("direction", "Direction"),
                  ("source_case", "Case"), ("material_name", "Material"),
                  ("fck_mpa", "fck MPa"), ("eta_bi", "ηbi"),
                  ("value", "Value"), ("limit", "Limit"),
                  ("status", "Status"), ("reason", "Reason"))
    for check in extras:
        columns = extra_cols
        items = check.get("items", [])
        if check.get("check_id") == "concrete_fck_25":
            columns = extra_cols[3:5] + extra_cols[7:] + roster_cols
            items = _with_material_members(items, material_roster)
        check_sections.append('<section class="percheck"><h2>' + _val(check.get("title")) +
                              '</h2><p>Source-based check. Formal compliance is NOT_PROVEN.</p>' +
                              _table(columns, items) + '</section>')
    vs04_sections = []
    analysis_setup = report.get("analysis_setup")
    if isinstance(analysis_setup, Mapping):
        vs04_sections.append(_analysis_setup_html(
            analysis_setup, (report.get("source_provenance") or {}).get("analysis_setup_receipt_sha256")))
    if report.get("column_axial") is not None:
        vs04_sections.append(_column_axial_html(report["column_axial"],
                                               report["source_provenance"]["column_axial_receipt_sha256"]))
    if report.get("vs04"):
        v = report["vs04"]
        source_tables = ((report.get("source_snapshot") or {}).get("analysis_sources") or {}).get("tables") or {}
        overview = [dict(t) for t in (v.get("tables") or [])]
        vs04_sections.append('<section class="percheck"><h2>VS04 · Unverified analysis source schema</h2>'
                            '<p>Formal compliance remains NOT_PROVEN pending separate code checks and verification of the analysis generation '
                            'and combination roles.</p>'
                            + _table((("table_key","ETABS table"),("status","Source status"),
                                      ("row_count","Rows"),("fields","Fields"),
                                      ("schema_sha256","Schema SHA-256"),("reason_codes","Blockers")), overview)
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
                vs04_sections.append('<section class="percheck"><h2>VS04 raw ETABS source · '
                                    + _val(key) + "</h2>"
                                    + _table(columns, rows, "modal-grid") + "</section>")
    readiness = report.get("vs04_readiness")
    if readiness:
        cols = (("check_id", "Required code calculation"),("code_ref", "TBDY"),
                ("status", "Evidence status"),("missing_evidence", "Missing dependencies"),
                ("source_only_hints", "Observed partial evidence"))
        vs04_sections.append('<section class="percheck"><h2>VS04-E · TBDY code evidence gates</h2>'
                             '<p>This section records source arithmetic. '
                             'Five code checks are pending. '
                             'Building compliance is NOT_PROVEN and release is NOT_READY.</p>'
                             + _table(cols, readiness.get("checks", [])) + '</section>')
    numeric = report.get("vs04_numerics")
    if numeric:
        numeric_cols = (("component", "Source quantity"), ("status", "Source status"),
                        ("expected_row_count", "Displayed rows"),
                        ("observed_row_count", "Arithmetic observation"),
                        ("reason_codes", "Engeller"))
        vs04_sections.append('<section class="percheck"><h2>VS04 · Numerical source consistency</h2>'
                             '<p>Source arithmetic completed with zero code checks. '
                             'The physical meaning of the drift results and the analysis generation await verification.</p>'
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
        source_cols = (("check_id", "Source check"), ("title", "Component"),
                       ("source_status", "Initial source status"),
                       ("status", "Resolved source status"),
                       ("execution_status", "Execution"),
                       ("coverage", "Original coverage / selected case"),
                       ("reason_codes", "Capture status / reason"),
                       ("missing_evidence", "Missing code evidence"),
                       ("formal_compliance", "TBDY compliance"))
        vs04_sections.append('<section class="percheck"><h2>VS04 E–J · Single-run source trace</h2>'
                             '<p>The eight code checks require their own evidence. '
                             'Mass reconciliation, spectrum and base shear are source-based or conditional screenings. '
                             'Full VtE, βtE and effective story drift remain NOT_PROVEN.</p>'
                             + _table(source_cols, pipeline.get("checks", [])) + '</section>')
        diag = pipeline.get("modal_display_selection_reconciliation")
        if diag:
            resolved = (diag.get("status") ==
                        "SOURCE_DISPLAY_SELECTION_DEPENDENCY_RECONCILED")
            diag_summary = (
                'The initial table read remains recorded as failed. The original E/F/G counts are preserved. '
                'Reading with RSX/RSY selected returned 200 rows that matched the H/I source checks. '
                'This confirms the table\'s selection dependency.'
                if resolved else
                'Reconciliation of the initial read and selected-case sources is pending. '
                'The missing source evidence remains open.'
            )
            vs04_sections.append(
                '<section class="percheck"><h2>VS04 E/F/G · Case selection dependency</h2>'
                '<p>' + _val(diag_summary) +
                ' TBDY compliance is NOT_PROVEN.</p>'
                + _table((("table_key", "ETABS table ID"),
                          ("status", "Source diagnosis"),
                          ("original_read_still_failed", "Initial read remains failed"),
                          ("selected_case_row_count", "RSX/RSY rows"),
                          ("reason_codes", "Reasons"),
                          ("analysis_generation_proven", "Analysis generation evidence")),
                         [diag]) + '</section>'
            )
        conditional = (pipeline.get("stages") or {}).get("vs04_j") or {}
        if conditional.get("conditional_eq_4_19_minimum_term_kn") is not None:
            vs04_sections.append('<section class="percheck"><h2>VS04-J · Conditional base shear lower-bound term</h2>'
                                 '<p>The calculation uses source candidates for m, I and SDS. '
                                 'Engineering acceptance and the VtE calculation require separate evidence.</p>'
                                 + _table((("source_mass_candidate_ton", "Candidate mass (t)"),
                                           ("candidate_importance_factor", "Aday I"),
                                           ("candidate_SDS", "Aday SDS"),
                                           ("conditional_eq_4_19_minimum_term_kn",
                                            "Conditional lower-bound term (kN)")),
                                          [conditional]) + '</section>')
    physical_scope = report.get("physical_story_scope")
    if isinstance(physical_scope, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>Physical story coverage · B1 / B2 / STORY_DRIFT / R08</h2>'
            '<p>Status ' + _val(physical_scope["status"]) +
            ' · Physical stories ' + _val(physical_scope["physical_story_count"]) +
            ' / Defined stories ' + _val(physical_scope["defined_story_count"]) +
            '. NOT_APPLICABLE applies only when a complete Frame, Area, Wall and Joint inventory confirms an empty story. '
            'Formal TBDY acceptance requires separate evidence.</p>' +
            _table((("story", "Story"), ("applicability", "Coverage"), ("frames", "Frame"),
                    ("areas", "Area"), ("walls", "Wall (subset of Area)"), ("joints", "Joint"),
                    ("reason", "Reason")), physical_scope["stories"]) +
            '<p>Open issue ' + _val(physical_scope["reason_codes"]) +
            ' · Coverage SHA-256 ' + _val(physical_scope["scope_sha256"]) + '</p></section>')
    drift_check = report.get("story_drift")
    if isinstance(drift_check, Mapping):
        drift_cols = (("story", "Story"), ("case", "Analysis case"),
                      ("direction", "Direction"), ("height_m", "h (m)"),
                      ("etabs_story_drift_ratio", "ETABS Drift"),
                      ("etabs_derived_delta_mm", "Candidate Δ (mm)"),
                      ("etabs_reconciliation_residual_mm", "Fark (mm)"))
        vs04_sections.append(
            '<section class="percheck"><h2>STORY_DRIFT · Source-based story drift</h2>'
            '<p>Status ' + _val(drift_check.get("status")) +
            ' · Calculated ' + _val(drift_check.get("evaluated_story_case_direction_count")) +
            ' / ' + _val(drift_check.get("expected_story_case_direction_count")) +
            '. Results use ETABS Drift × story height. '
            'Nonconcurrent RSX/RSY joint maxima were kept as individual values.</p>'
            ' TBDY compliance is NOT_PROVEN.</p>' +
            _table(drift_cols, drift_check.get("items", [])) +
            '<h3>Missing story, case and direction results</h3>' +
            _table((("story", "Story"), ("case", "Case"), ("direction", "Direction")),
                   drift_check.get("missing_story_case_direction", [])) +
            '</section>')
    r08_record = report.get("r08_second_order")
    if isinstance(r08_record, Mapping):
        dr = r08_record.get("direction_results", {})
        direction_rows = [
            {"axis": axis, **(dr.get(axis) or {})} for axis in ("X", "Y")
        ]
        vs04_sections.append(
            '<section class="percheck" data-check-panel="GLOBAL_SECOND_ORDER">'
            '<h2>R08 · Global second-order P–Δ · TBDY 2018 4.9.2</h2>'
            '<p>Source numerical status ' + _val(r08_record.get("status")) +
            ' · Story-direction results ' + _val(r08_record.get("evaluated_story_direction_count")) +
            '/' + _val(r08_record.get("expected_story_direction_count")) +
            '. Stage one calculates a numerical indicator candidate from ETABS source data. '
            'Column and wall mean drift, seismic mass weights, '
            'spectral amplification and analysis generation still require acceptance. '
            '<strong>FORMAL COMPLIANCE: NOT_PROVEN · RELEASE: NOT_READY</strong>.</p>' +
            (_table((("story", "Out-of-scope stories"), ("reason", "Reason")),
                    r08_record["excluded_stories"]) if r08_record.get("excluded_stories") else '') +
            _table((("story", "Story"), ("direction", "Direction"), ("case", "Case"),
                    ("story_height_m", "h (m)"),
                    ("cumulative_seismic_weight_kn_candidate", "Toplam W (kN)"),
                    ("reduced_story_shear_kn_candidate", "Vi (kN)"),
                    ("etabs_avg_drift_m_candidate", "Candidate mean Δ (m)"),
                    ("theta_ii_candidate", "Candidate θII"),
                    ("source_numeric_status", "Source status")),
                   r08_record.get("results", [])) +
            '<h3>Numerical candidates by direction</h3>' +
            _table((("axis", "Direction"), ("theta_max_candidate", "Candidate θmax"),
                    ("theta_limit_reference", "θ limit reference"),
                    ("beta_ii_candidate", "Candidate βII"),
                    ("applied_to_design_forces", "Applied to design forces")),
                   direction_rows) +
            '<p>Source blockers ' + _val(r08_record.get("reason_codes", [])) +
            ' · Kabul eksikleri: ' + _val(r08_record.get("missing_authorities", [])) +
            ' · Source SHA-256 ' + _val(r08_record.get("source_sha256")) +
            '</p></section>')
    ledger = report.get("vs06_story_slot_ledger")
    if isinstance(ledger, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-A · STORY_DRIFT source coverage ledger</h2>'
            '<p>The archive shows all defined stories before the verified empty-story exclusions. '
            'The current applicable coverage is in STORY_DRIFT above.</p>'
            '<p>Expected records: ' + _val(ledger.get("expected_slot_count")) +
            ' · Calculated from source ' + _val(ledger.get("source_numeric_count")) +
            ' · Missing source ' + _val(ledger.get("source_missing_count")) +
            '. The ledger accounts for all rows. Physical applicability and TBDY compliance are NOT_PROVEN. '
            'Missing rows remain unresolved.</p>' +
            _table((("story", "Story"), ("case", "Case"), ("direction", "Direction"),
                    ("source_status", "Source"), ("source_delta_mm", "Candidate Δ (mm)"),
                    ("physical_applicability", "Fiziksel uygulanabilirlik"),
                    ("normative_status", "TBDY durumu"), ("reason_code", "Open evidence")),
                   ledger.get("slots", [])) + '</section>')

    physical = report.get("vs06_physical_source_review")
    if isinstance(physical, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-B · Physical source and spectral concurrence evidence</h2>'
            '<p>The archive reviews evidence at column ends. The physical story coverage table shows the current complete inventory '
            'and verified empty-story exclusions.</p>'
            '<p>Observed column connections ' + _val(physical.get("endpoint_linked_column_count")) +
            ' / ' + _val(physical.get("observed_column_count")) +
            ' · Independent RSX/RSY point maxima ' +
            _val(physical.get("response_spectrum_independent_max_rows")) +
            ' · Verified concurrent design displacement pairs ' +
            _val(physical.get("signed_concurrent_spectrum_design_pairs_proven")) +
            '. Observations cover the inspected columns. Whole-building coverage and exclusions require a complete inventory. '
            'Physical applicability and code compliance remain NOT_PROVEN.</p>' +
            '<h3>Observed connections by story</h3>' +
            _table((("story", "Story"), ("assigned_columns_observed", "Assigned columns"),
                    ("endpoint_linked_columns_observed", "Matched ends"),
                    ("member_presence_evidence", "Source finding"),
                    ("physical_story_applicability", "Uygulanabilirlik")),
                   physical.get("observed_stories", [])) +
            '<h3>Evidence limits by story, spectrum case and direction</h3>' +
            _table((("story", "Story"), ("case", "Case"), ("direction", "Direction"),
                    ("source_status", "Displacement source"),
                    ("member_presence_evidence", "Physical source"),
                    ("physical_applicability", "Uygulanabilirlik"),
                    ("signed_concurrent_spectrum_delta_available", "Concurrent Δ"),
                    ("regulatory_status", "Code")),
                   physical.get("slots", [])) +
            '<h3>Unresolved column end connections</h3>' +
            _table((("column", "Column"), ("story", "Story"), ("reason", "Open evidence")),
                   physical.get("unresolved_columns", [])) + '</section>')

    readiness = report.get("vs06_effective_drift_readiness")
    if isinstance(readiness, Mapping):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-C1 · TBDY 4.9 effective interstory drift readiness</h2>'
            '<p>The archive accounts for all defined stories. The C2 scenario applies verified '
            'empty-story exclusions.</p>'
            '<p>Expected story-direction checks in the 94-node dependency graph ' +
            _val(readiness.get("expected_story_direction_instances")) +
            ' · ETABS numerical source candidates ' +
            _val(readiness.get("source_numeric_primary_instances")) +
            ' · Missing primary sources ' +
            _val(readiness.get("source_missing_primary_instances")) +
            '; aday FCR NOT_PROVEN: ' +
            _val(readiness.get("candidate_fcr_not_proven")) +
            '. The formal calculation for Eq. (4.32)–(4.34) remains pending. '
            'Concurrent design displacements and empty-story exclusions require '
            'separate evidence.</p>' +
            _table((("check_instance_id", "DAG CheckInstance"),
                    ("case", "ETABS case"), ("source_numeric_status", "Source"),
                    ("etabs_derived_delta_mm_candidate", "Source candidate Δ (mm)"),
                    ("member_presence_evidence", "Physical source"),
                    ("physical_applicability", "Uygulanabilirlik"),
                    ("formula_execution", "Equation execution"),
                    ("regulatory_status", "TBDY durumu"),
                    ("required_source_evidence", "Missing code evidence")),
                   readiness.get("check_instances", [])) +
            '</section>')

    scenario = report.get("vs06_drift_scenario")
    if isinstance(scenario, Mapping):
        wall = scenario.get("wall_candidate_inventory") or {}
        options = scenario.get("scenario_input") or {}
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-C2 · TBDY 4.9 effective interstory drift · Numerical scenario</h2>'
            '<p>Brittle infill uses Eq. (4.34a) and 0.008κ. Flexible connections use Eq. (4.34b) and '
            '0.016κ, subject to separate test evidence of connection capacity. '
            'The table uses the observed ETABS Story Drifts × h values. '
            'Physical displacement concurrence and formal compliance require separate evidence. '
            '<strong>FORMAL COMPLIANCE: NOT_PROVEN</strong>.</p>' +
            _table((("r", "Default / scenario R"), ("i", "Scenario I"),
                    ("lambda", "Scenario λ"), ("material", "System"),
                    ("wall_type", "Infill connection"), ("coverage_pct", "Infill share (%)"),
                    ("wall_height_m", "Assumed wall h (m)"),
                    ("opening_pct", "Openings (%)"), ("wall_mode", "Wall source mode"),
                    ("wall_load_pattern", "ETABS wall load pattern")),
                   [options]) +
            '<p>Load pattern ' + _val(wall.get("load_pattern")) + ' observation ' + _val(wall.get("source_status")) +
            ' · Candidate beams ' + _val(wall.get("candidate_beam_count")) +
            ' · Aday toplam uzunluk (m): ' + _val(wall.get("candidate_total_length_m")) +
            ' · Assumed net infill face area (m²) ' +
            _val(wall.get("assumed_net_face_area_m2")) +
            '. Physical infill presence and B1 effective shear area require '
            'additional evidence beyond the load assignment.</p>' +
            _table((("story", "Story"), ("case", "Case"), ("direction", "Direction"),
                    ("source_delta_mm", "Source candidate Δ (mm)"),
                    ("effective_delta_mm", "Scenario effective Δ (mm)"),
                    ("lambda_effective_ratio", "λ δ / h"),
                    ("limit", "Limit"), ("utilization_ratio", "Utilization ratio"),
                    ("conditional_numeric_condition", "Conditional numerical result"),
                    ("formal_compliance", "Formal compliance")),
                   scenario.get("rows", [])) +
            '<p>Scenario SHA-256: ' + _val(scenario.get("scenario_sha256")) +
            ' · Source SHA-256 ' + _val(scenario.get("input_sha256")) +
            '. Test-based capacity evidence for flexible connections ' +
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
            '<section class="percheck"><h2>VS06-D1 · B1 weak story · Numerical source scenario</h2>'
            '<p>TBDY 2018 Table 3.6 and 3.6.2.3 give Ae = Aw+Ag+0.15Ak. '
            'Column and wall geometry comes from the source. Brick thicknesses of 9 and 19 cm and '
            'door and window deductions are assumptions. Formal compliance is NOT_PROVEN.</p>'
            '<p>ηci,min: ' + _number_html(b1_numeric.get("eta_ci_min"), 4) +
            ' · Numerical decision ' + _val(b1_numeric.get("numeric_condition")) +
            ' · Physical story coverage ' + _val(b1.get("physical_source_coverage", "UNKNOWN")) +
            ' · Default brittle infill ' +
            _val((b1.get("parameters") or {}).get("wall_type")) + '</p>' +
            _table((("story", "Story"), ("direction", "Direction"),
                    ("Aw_m2", "Aw (m²)"), ("Ag_m2", "Ag (m²)"),
                    ("Ak_m2", "Assumed Ak (m²)"),
                    ("K_proxy", "K_proxy (kN/m)")), area_rows) +
            _table((("lower_story", "Lower story"), ("upper_story", "Upper story"),
                    ("direction", "Direction"), ("eta_ci", "ηci"),
                    ("numeric_condition", "Numerical status")),
                   b1_numeric.get("paired_results", [])) +
            '<h3>Calculation assumptions</h3><ol>' +
            ''.join('<li>' + escape(str(item)) + '</li>'
                    for item in b1.get("assumptions_notes", [])) +
            '</ol><p>Source SHA-256 ' +
            _val((b1.get("provenance") or {}).get("geometry_capture_sha256")) +
            ' / ' +
            _val((b1.get("provenance") or {}).get("wall_load_capture_sha256")) +
            '. Engineering release is NOT_READY.</p></section>')
    elif report.get("vs06_b1_source_status"):
        vs04_sections.append(
            '<section class="percheck"><h2>VS06-D1 · B1 source mapping</h2>'
            '<p>' + _val(report.get("vs06_b1_source_status")) +
            '.</p></section>')

    if isinstance(b2, Mapping):
        coverage = b2["comparison_coverage"]
        vs04_sections.append(
            '<section class="percheck" data-check-panel="SOFT_STORY_B2">'
            '<h2>B2 soft story · Conditional source calculation</h2>'
            '<p>TBDY 2018 Table 3.6 / §3.6.2.1 gives ηki = '
            '(Avg Driftᵢ / hᵢ) / (Avg Driftⱼ / hⱼ). The story above and the story below are checked separately. '
            'The threshold is ηki &gt; 2.0. Formal B2 classification '
            '<strong>NOT_PROVEN</strong>.</p>'
            '<p>Source status ' + _val(b2["status"]) + ' · Calculation ' +
            _val(b2["numeric_condition"]) + '. Resolved neighbor pairs ' +
            _val(coverage["resolved"]) + '/' + _val(coverage["expected"]) +
            ' · Unresolved ' + _val(coverage["unresolved"]) +
            ' · Coverage ' + _val(b2.get("source_coverage_status", "UNKNOWN")) + '.</p>' +
            _table((("story", "Out-of-scope stories"), ("applicability", "Status"),
                    ("reason", "Reason")), b2.get("excluded_stories", [])) +
            '<details><summary>Story elevations and intermediate point mapping</summary>' +
            '<p>Only top-plane points support the story elevation. Intermediate and lower-boundary points preserve the story height. '
            'The physical story coverage table contains the complete object inventory '
            'by story.</p>' +
            _table((("story", "Story"), ("lower_elevation_m", "Lower elevation (m)"),
                    ("upper_elevation_m", "Upper elevation (m)"), ("at_level_points", "Top-plane point"),
                    ("intermediate_points", "Intermediate elevation points"),
                    ("lower_boundary_points", "Lower-boundary point")),
                   (b2.get("story_order") or {}).get("point_story_span_counts", [])) + '</details>' +
            _table((("story", "Story"), ("direction", "Direction"), ("case", "Case"),
                    ("height_m", "h (m)"), ("average_drift_m", "Avg Drift (m)"),
                    ("status", "Source"), ("reason", "Missing or failed")),
                   b2["source_rows"]) +
            _table((("story", "Story checked"), ("adjacent_story", "Adjacent story"),
                    ("neighbour_role", "Neighbor relation"), ("direction", "Direction"), ("case", "Case"),
                    ("normalized_mean", "Avg Driftᵢ / hᵢ"),
                    ("adjacent_normalized_mean", "Avg Driftⱼ / hⱼ"),
                    ("eta_ki_candidate", "Candidate ηki"), ("status", "Numerical status"),
                    ("reason_codes", "Open issue")),
                   b2["items"]) +
            '<h3>Calculation scope and assumptions</h3><ul>' +
            ''.join('<li>' + _val(s) + '</li>' for s in b2["assumptions_notes"]) +
            '</ul><p>Source / calculation ' + _val(b2["source_payload_sha256"]) +
            ' / ' + _val(b2["result_sha256"]) + '</p><p>Open source evidence ' +
            _val(b2["reason_codes"]) + '. ENGINEERING_RELEASE=NOT_READY.</p></section>')

    if isinstance(wall_geometry, Mapping):
        panel_rows = []
        for row in wall_geometry["items"]:
            panel_rows.append({**row, **{s["rule"]: s["status"] for s in row["subconditions"]}})
        vs04_sections.append(
            '<section class="percheck" data-check-panel="WALL_GEOMETRY_CHECK">'
            '<h2>Shear wall section geometry · Conditional source checks</h2>'
            '<p>TBDY 2018 7.6.1.2 / 7.6.1.2(a). Panels calculated ' +
            _val(wall_geometry["evaluated_count"]) + '/' + _val(wall_geometry["expected_count"]) +
            ' · Numerical criteria ' + _val(wall_geometry["subconditions_evaluated"]) +
            ' · Failed criteria ' + _val(wall_geometry["subconditions_unmet"]) +
            '. Formal compliance NOT_PROVEN.</p>' +
            _table((("story", "Story"), ("element_id", "ETABS Unique ID"), ("section", "Section"),
                    ("story_height_m", "Story h (m)"), ("panel_height_m", "h panel (m)"),
                    ("panel_length_m", "l panel (m)"), ("thickness_mm", "bw (mm)"),
                    ("panel_length_thickness_ratio", "l panel / bw"),
                    ("ordinary_branch_minimum_mm", "Standart dal bw,min (mm)"),
                    ("panel_ratio", "Ratio ≥ 6"), ("thickness_250", "bw ≥ 250 mm"),
                    ("thickness_h16", "bw ≥ h/16"), ("reason", "Open issue")), panel_rows) +
            '<h3>Applicability and calculation limits</h3><ul>' +
            ''.join('<li>' + _val(s) + '</li>' for s in wall_geometry["assumptions_notes"]) + '</ul>' +
            _table((("code_ref", "Clause"), ("status", "Status"), ("reason", "Missing evidence")),
                   wall_geometry["unevaluated_requirements"]) +
            '<p>Source ' + _val(wall_geometry["source_payload_sha256"]) +
            ' · Result ' + _val(wall_geometry["result_sha256"]) +
            ' · Source diagnostic ' + _val(wall_geometry["reason_codes"]) + '</p></section>')

    for bundle in (source_controls, earthquake_combinations):
        if not isinstance(bundle, Mapping):
            continue
        for check in bundle["checks"]:
            if check["check_id"] == "concrete_fck_80":
                columns = (("material_name", "Material"), ("fck_mpa", "Source Fc (MPa)"),
                    ("limit", "Upper limit (MPa)"), ("strength_scope_observation", "Numerical coverage"),
                    ("status", "Criterion"), ("reason", "Open issue"))
                columns += roster_cols
            elif check["check_id"] == "modal_combination_spacing":
                columns = (("direction", "Direction"), ("source_case", "Case"), ("modal_case", "Modal case"),
                    ("modal_combination", "Modal combination"), ("directional_combination", "Directional combination"),
                    ("mode_count", "Mode count"), ("maximum_period_ratio", "Maximum short-to-long period ratio"),
                    ("spacing_status", "SRSS separation criterion"), ("method_condition", "Selected method criterion"),
                    ("reason", "Open issue"))
            elif check["check_id"] == "earthquake_100_30":
                columns = (("combination", "Combination"), ("operator", "Operation"),
                    ("coefficient_x", "X factor"), ("coefficient_y", "Y factor"),
                    ("common_factor", "Common magnitude"), ("minor_major_ratio", "Smaller / larger"),
                    ("dominant_direction", "Dominant direction"), ("status", "Criterion"), ("reason", "Coverage / diagnostic"))
            else:
                columns = (("common_factor", "Common magnitude"), ("other_case_coefficients", "Other case factors"),
                    ("x_combinations", "X-dominant combinations"), ("y_combinations", "Y-dominant combinations"),
                    ("missing_directions", "Unobserved direction"), ("observed_sign_patterns", "Observed signs"),
                    ("unresolved_combination", "Unresolved combinations"), ("status", "Source coverage"),
                    ("reason", "Open issue"))
            pair_tables = []
            alternatives = [{"envelope": item["combination"], **term}
                for item in check["items"] for term in item.get("envelope_alternatives", [])]
            if alternatives:
                pair_tables.append('<details><summary>Envelope alternatives are evaluated individually</summary>' +
                    _table((("envelope", "Envelope"), ("ref", "Alternative"), ("factor", "Factor"),
                            ("ref_type", "Source type")), alternatives) + '</details>')
            for item in check["items"]:
                if item.get("pairs"):
                    pair_tables.append('<details><summary>' + _val(item["source_case"]) +
                        ' · ' + _val(item["tested_adjacent_pair_count"]) + ' adjacent pairs / ' +
                        _val(item["all_distinct_pair_count"]) + ' distinct pairs</summary>' +
                        _table((("short_mode", "Shorter-period mode"), ("long_mode", "Longer-period mode"),
                            ("short_period_s", "Shorter period (s)"), ("long_period_s", "Longer period (s)"),
                            ("period_ratio", "Ratio"), ("limit", "Exclusive upper bound (<)"),
                            ("status", "SRSS separation criterion")), item["pairs"]) + '</details>')
            vs04_sections.append('<section class="percheck" data-check-panel="' +
                escape(check["check_id"], quote=True) + '"><h2>' + _val(check["title"]) + '</h2><p>' +
                _val(check["code_ref"]) + ' · Calculated ' + _val(check["evaluated_count"]) + '/' +
                _val(check["expected_count"]) + ' · Out of scope ' + _val(check["not_applicable_count"]) +
                ' · ' + _val(check["status"]) +
                '. Formal compliance NOT_PROVEN.</p>' + _table(columns,
                    _with_material_members(check["items"], material_roster)
                    if check["check_id"] == "concrete_fck_80" else check["items"]) +
                ''.join(pair_tables) + '<h3>Coverage and open conditions</h3><ul>' +
                ''.join('<li>' + _val(n) + '</li>' for n in check["assumptions_notes"]) + '</ul><p>' +
                _val(check["unevaluated_requirements"]) + '</p><p>Source ' +
                _val(check["source_provenance"]) + ' · Calculation ' + _val(check["result_sha256"]) +
                ' · Diagnostic ' + _val(check["reason_codes"]) + '</p></section>')

    a1_warnings = [
        c for c in extras if c.get("check_id") in ("a1_torsion_x", "a1_torsion_y")
        and any(item.get("status") == "A1_OBSERVED" for item in c.get("items", []))
    ]
    if a1_warnings:
        vs04_sections.append('<section class="percheck"><h2>A1 torsional irregularity · Source warning</h2>'
                             '<p>At least one story and direction has ηbi &gt; 1.2. '
                             'A final compliance decision requires verification of the eccentricity application '
                             'and the complete TBDY scope.</p>'
                             + _table((("check_id", "Direction"), ("status", "Source classification")),
                                      a1_warnings) + '</section>')
    modal_table = report["modal_source_table"]
    fields = modal_table.get("fields") or []
    modal_cols = tuple((field, field) for field in fields)
    modal_section = (
        f'<section class="percheck"><h2>Modal source table · {_val(modal_table.get("row_count"))} rows</h2>'
        f'<p>Initial calculation X={_number_html(modal.get("sum_ux"), 4)}, Y={_number_html(modal.get("sum_uy"), 4)}, '
        f'Threshold={_number_html(modal.get("required_ratio"), 4)}, governing mode={_val(modal.get("governing_mode_count"))}; '
        f'significant modes X={_val(modal.get("significant_modes_x"))}, '
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
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
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
<div class="toolstrip">Press <strong>Ctrl+P</strong> to print or save as PDF.</div>
<h1>TBDY Next Engine — Engineering Check Report</h1>
<p class="muted">{_val((report.get('check_inventory') or {}).get('count', len(checks)))} limited-scope checks from ETABS source data. The STORY_DRIFT numerical result leaves TBDY compliance NOT_PROVEN.</p>
<p class="muted">Hover over a rounded value to see the original. The JSON export also includes full precision.</p>
<div class="warning"><strong>FORMAL COMPLIANCE = NOT_PROVEN · ENGINEERING RELEASE = NOT_READY.</strong>
The report covers the numerical checks documented below. Full TBDY and TS500 compliance requires further evidence.</div>
<div class="grid">
<div><strong>Model</strong><p>{_val(report.get('model'))}</p></div>
<div><strong>Run / date</strong><p>{_val(report['run_id'])}<br>{_val(report['captured_at_utc'])}</p></div>
<div><strong>Source / modal case</strong><p>{_val(report['source_mode'])}<br>{_val(report['modal_case'])}</p></div>
</div>
<h2>Check summary</h2>
{_table(summary_cols, summary_rows)}
<p class="muted">Geometry totals count element-check pairs. Each element may appear in several checks.</p>
<h2>ETABS model inventory and materials</h2>
{_table((("type","Element type"),("count","Count")), census_rows)}
{_table((("name","Material"),("code","ETABS code"),("status","Source status"),("concrete","Concrete")), materials)}
<h3>Members by material</h3>
{_table((("material_name", "Material"),) + roster_cols, material_roster)}
<h2>Source table headers and row counts</h2>
{_table((("role","Role"),("key","Native table name"),("count","Row"),("status","Status"),("fields","Observed fields")), tables)}
<h2>Traceability</h2>
<p><strong>Input SHA-256</strong> {_val(report['source_provenance']['input_sha256'])}<br>
<strong>Modal receipt SHA-256:</strong> {_val(report['source_provenance']['modal_receipt_sha256'])}<br>
<strong>Geometry receipt SHA-256:</strong> {_val(report['source_provenance']['geometry_receipt_sha256'])}</p>
{modal_section}
{''.join(vs04_sections)}
{''.join(check_sections)}
<p class="muted">The JSON export contains the raw source tables, all element rows and material type evidence.
This report replays the archived source with the original evaluators and verifies the stored results.</p>
</body></html>'''
    return html


__all__ = ["ReportUnavailable", "build_complete_report", "build_printable_html"]



def _column_axial_html(result: Mapping[str, Any], receipt_sha: str) -> str:
    plan = result["combination_plan"]
    columns = [{**item, **(item.get("governing") or {}), "column_status": item["status"]}
               for item in result["columns"]]
    combinations = []
    for item in result["columns"]:
        for check in item.get("combination_checks", []):
            combinations.append({"story": item["story"], "element_id": item["element_id"], **check})
    basis = {"ETABS_STRENGTH": "ETABS Strength selections", "ASSIGNED_DESIGN": "Assigned design combinations",
             "SAVED_DEFAULTS": "Recorded custom combination list"}[plan["source"]]
    assignment = plan.get("design_assignment")
    return (
        '<section class="percheck"><h2>Column axial compression · TS 500 Eq. (7.7)</h2>'
        f'<p><strong>{_val(result["status"])}</strong> · {_val(basis)} · '
        f'{_val(result["completed_column_count"])}/{_val(result["expected_column_count"])} columns · '
        f'{_val(result["evaluated_member_combination_count"])}/{_val(result["expected_member_combination_count"])} '
        f'column–combination pairs · {_val(result["native_force_row_count"])} native rows.</p>'
        f'<p>ETABS concrete factor γc {_val(result["gamma_c"])}. The selected combinations and native output '
        'stations define this numerical comparison. TBDY seismic combination applicability '
        'and structural design approval remain open. Full native force arrays are in the JSON export.</p>'
        + (_table((("group", "Design group"), ("names", "Assigned ETABS combinations")),
                  [{"group": group, "names": ", ".join(names)} for group, names in assignment["groups"].items()])
           if assignment else '')
        + ('<ul>' + ''.join('<li>' + _val(code) + '</li>' for code in plan["blockers"]) + '</ul>'
           if plan["blockers"] else '')
        + _table((("name", "Combination"), ("operator", "Operator"), ("force_semantics", "Native force type")),
                 plan["combinations"])
        + _table((("story", "Story"), ("element_id", "ETABS Unique ID"), ("section", "Section"),
                  ("material_name", "Material"), ("combination", "Governing observed combination"),
                  ("object_station_m", "Object station (m)"), ("analysis_element", "Analysis element ID"),
                  ("element_station_m", "Element station (m)"), ("step_type", "Step"),
                  ("nd_kn", "Nd (kN)"), ("ts500_limit_kn", "TS 500 limit (kN)"),
                  ("ratio", "Nd / limit"), ("column_status", "Status"), ("reason", "Evidence gap")), columns)
        + ('<details><summary>Check results by combination</summary>'
           + _table((("element_id", "ETABS Unique ID"), ("combination", "Combination"), ("force_row_count", "Rows"),
                     ("object_station_m", "Object station (m)"), ("step_type", "Step"),
                     ("nd_kn", "Nd (kN)"), ("ratio", "Nd / limit"), ("status", "Status"),
                     ("reason", "Evidence gap")), combinations) + '</details>' if combinations else '')
        + f'<p>Calculation receipt SHA-256 {_val(receipt_sha)}</p></section>'
    )


def _analysis_setup_html(setup: Mapping[str, Any], receipt_sha: str | None = None) -> str:
    selected = setup["design_selection_count"]
    summary = (
        f'Case definitions {_val(setup["case_definition_count"])} · '
        f'Combination definitions {_val(len(setup["defined_combination_names"]) if setup["typed_graph_source_sha256"] else None)} · '
        f'Design selection {_val(selected if selected is not None else "Source unavailable")}'
    )
    diagnostics = setup["diagnostics"]
    capture_scope = ("The archived combination selection and static case settings come from separate captures."
                     if setup["source_capture_scope"] == "SEPARATE_CAPTURES" else "")
    return (
        '<section class="percheck" data-check-panel="ANALYSIS_BASIS_GATE">'
        '<h2>R03 · ETABS analysis and concrete design setup</h2>'
        f'<p><strong>{_val(setup["status"])}</strong> · {summary}</p>'
        '<p>Strength selection comes from the ETABS design list. Project load roles and analysis generation require separate verification.</p>'
        + (f'<p>{capture_scope}</p>' if capture_scope else '')
        + _table((("design_type", "ETABS design list"), ("combination", "Combination")),
                 setup["design_selection"] or [])
        + _table((("combination", "Defined combination"), ("operator", "ETABS operation"),
                  ("spectral_case_references", "Spectrum case references"),
                  ("observed_design_types", "Design lists captured"),
                  ("nonconcurrent_source_reasons", "Vector restriction")),
                 setup["combination_audit"])
        + _table((("case", "Linear static case"), ("stiffness_setting", "StiffType"),
                  ("nonlinear_case", "NonlinCase")), setup["linear_static_settings"])
        + '<p>Open evidence</p><ul>' + ''.join('<li>' + _val(s) + '</li>' for s in setup["blocker_codes"])
        + '</ul>'
        + ('<details><summary>Source diagnostic</summary><pre>' + _val(diagnostics) + '</pre></details>' if diagnostics else '')
        + '<p>Source table SHA-256 ' + _val(setup["source_tables_sha256"])
        + (' · R03 receipt SHA-256 ' + _val(receipt_sha) if receipt_sha else '')
        + '</p></section>'
    )


def build_column_127_gate_html(bundle: Mapping[str, Any]) -> str:
    """Render sealed P0 gate report for column 127/C88 without performing calculations."""
    p0 = bundle["p0_gate_report"]
    verdict = p0["verdict_summary"]
    reinf = p0["p0b_gates"]["f03_reinforcement_states"]
    trans = p0["p0b_gates"]["f07_transverse_topology"]
    setup = p0["p0c_model_analysis_setup_audit"]
    station_rows = [
        {
            "station_m": s["object_station_m"],
            "nd_kn": round(s["nd_compression_kn"], 4),
            "m2_raw": round(s["e_min_gate"]["m2_raw_knm"], 4),
            "m3_raw": round(s["e_min_gate"]["m3_raw_knm"], 4),
            "m2_design": round(s["e_min_gate"]["m2_design_knm"], 4),
            "m3_design": round(s["e_min_gate"]["m3_design_knm"], 4),
            "raw_pmm": round(s["raw_pmm_utilization"], 6),
            "emin_pmm": round(s["pmm_with_e_min_utilization"], 6),
            "axial_status": s["axial_cap_gate"]["status"],
        }
        for s in p0["p0b_gates"]["f02_grav_ult_stations"]
    ]
    reinf_rows = [
        reinf["etabs_template_12phi20"],
        reinf["proposed_scenario_16phi24"],
        reinf["selected_if_template_12phi20_used"],
    ]
    trans_rows = [
        {"case": "Proposed reinforcement", **trans["proposed_16phi24"]},
        {"case": "ETABS template (conditional)", **trans["etabs_template_12phi20_phi10_s150"]},
    ]
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Column 127 / C88 — P0 engineering gates</title>"
        "<style>body{font:13px/1.5 system-ui,sans-serif;max-width:1280px;margin:28px auto;padding:0 20px;color:#1c3045}"
        "table{border-collapse:collapse;width:100%;margin:10px 0 20px;font-size:12px}"
        "th,td{border:1px solid #d4deea;padding:6px 8px;text-align:left}"
        "th{background:#e8eff7}.warn{padding:10px 14px;border-left:4px solid #986a16;background:#fbf4e9;margin:14px 0}</style>"
        "</head><body>"
        f"<h1>Column {_val(p0['member'])} ({_val(p0['label'])}) · Story {_val(p0['story'])} · Section {_val(p0['section_name'])}</h1>"
        "<div class='warn'><strong>FORMAL COMPLIANCE = NOT_PROVEN · ENGINEERING RELEASE = NOT_READY · PRODUCTION_READY = NO</strong></div>"
        "<h2>P0-B · Grav_Ult stations (F01 axial limit, F02 e_min and PMM)</h2>"
        + _table(
            (
                ("station_m", "Station (m)"),
                ("nd_kn", "Nd (kN)"),
                ("m2_raw", "Raw M2 (kN·m)"),
                ("m3_raw", "Raw M3 (kN·m)"),
                ("m2_design", "Design M2 (kN·m)"),
                ("m3_design", "Design M3 (kN·m)"),
                ("raw_pmm", "Raw PMM ratio"),
                ("emin_pmm", "PMM ratio with e_min"),
                ("axial_status", "CHK-005 / CHK-004"),
            ),
            station_rows,
        )
        + "<h2>P0-B · F03 longitudinal reinforcement</h2>"
        + _table(
            (
                ("role", "Role"),
                ("bar_count", "Count"),
                ("bar_diameter_mm", "Diameter (mm)"),
                ("rho", "ρ"),
                ("status", "Status"),
                ("diameter_basis", "Diameter source"),
                ("formal_compliance", "Compliance"),
                ("reason_codes", "Reason"),
            ),
            reinf_rows,
        )
        + "<h2>P0-B · F07 transverse reinforcement leg topology (CHK-123)</h2>"
        + _table(
            (
                ("case", "Cage"),
                ("max_ai_mm", "Maximum ai (mm)"),
                ("ai_limit_25_phi_e_mm", "25φe limit (mm)"),
                ("vertical_spacing_s_mm", "s (mm)"),
                ("s_max_limit_mm", "Maximum s (mm)"),
                ("status", "Status"),
                ("reason_codes", "Reason"),
            ),
            trans_rows,
        )
        + _analysis_setup_html(setup)
        + f"<p><strong>Sealed report SHA-256</strong> {_val(p0['result_sha256'])}</p>"
        + f"<p><strong>Summary decision</strong> {_val(verdict)}</p>"
        + "</body></html>"
    )
