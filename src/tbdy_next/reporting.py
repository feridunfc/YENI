"""Project finalized pipeline results into JSON and printable reports.

Older captures retain their original source-replay validation. New reports
verify their archived source and receipt chain without evaluating checks.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from hashlib import sha256
from html import escape
import json
import ntpath
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
    """Load an exact run and render only the recorded results for finalized runs."""
    from .engineering.pipeline_snapshot import SCHEMA, read_receipts, read_snapshot

    if not isinstance(run_id, str) or _RUN.fullmatch(run_id) is None:
        raise ReportUnavailable("Invalid run ID")
    directory = Path(root) / run_id
    if directory.is_symlink() or not directory.is_dir():
        raise ReportUnavailable("Run directory unavailable")
    modal = _read_receipt(directory, "modal")
    if modal is None:
        raise ReportUnavailable("Modal receipt unavailable")
    try:
        input_sha = modal["input_sha256"]
        source = _load_source(directory, input_sha)
        receipts = read_receipts(directory, input_sha=input_sha)
        snapshot = read_snapshot(directory, input_sha=input_sha, receipts=receipts)
        if snapshot is not None and snapshot["schema"] == SCHEMA:
            stages = snapshot["results"]
            evidence = stages["report_evidence"]
            return _assemble_complete_report(run_id, source, receipts, stages, evidence, snapshot)
        return _build_legacy_report(directory, source, receipts, snapshot)
    except (OSError, TypeError, ValueError, KeyError) as exc:
        if isinstance(exc, ReportUnavailable):
            raise
        raise ReportUnavailable("Recorded report cannot be verified") from exc


def _build_legacy_report(directory: Path, source: dict[str, Any],
                         receipts: Mapping[str, Mapping[str, Any]],
                         snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    """Keep compatibility with runs predating complete result snapshots."""
    modal = _read_modal_run(directory)
    quick = receipts.get("quick-geometry")
    if modal is None or quick is None:
        raise ReportUnavailable("Complete modal and geometry receipts required")
    if quick.get("input_sha256") != modal["input_sha256"]:
        raise ReportUnavailable("Modal and geometry sources conflict")
    try:
        geometry_source = source.get("geometry_capture")
        geometry = evaluate_geometry_capture(geometry_source)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise ReportUnavailable("Geometry source cannot be verified") from exc
    if geometry != quick["payload"]:
        raise ReportUnavailable("Geometry receipt does not match current evaluator")

    new_checks = None
    if "next_capture" in source:
        from .next_checks import evaluate_next_capture
        receipt = receipts.get("quick-extra")
        if receipt is None or receipt.get("input_sha256") != modal["input_sha256"]:
            raise ReportUnavailable("Missing VS03 receipt for captured VS03 sources")
        new_checks = evaluate_next_capture(source["next_capture"], geometry_source)
        if new_checks != receipt["payload"]:
            raise ReportUnavailable("VS03 source/receipt mismatch")
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
        vs04_receipt = receipts.get("vs04-schema")
        if vs04_receipt is None or vs04_receipt.get("input_sha256") != modal["input_sha256"]:
            raise ReportUnavailable("Missing or invalid VS04 source schema receipt")
        vs04 = review_analysis_sources(source["analysis_sources"])
        if vs04 != vs04_receipt["payload"]:
            raise ReportUnavailable("VS04 source/receipt mismatch")
        vs04_numeric_receipt = receipts.get("vs04-numerics")
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
        vs04_readiness_receipt = receipts.get("vs04-readiness")
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
        vs04_pipeline_receipt = receipts.get("vs04-pipeline")
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
    story_drift_receipt = receipts.get("vs05-story-drift")
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
    r08_receipt = receipts.get("r08-second-order")
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

    from .engineering.analysis_setup import DESIGN_COMBOS, STAGE, bind_analysis_setup, project_analysis_setup_reconciliation
    analysis_setup = None
    setup_receipt = receipts.get(STAGE)
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

    from .engineering.column_axial import STAGE as AXIAL_STAGE, evaluate_column_axial
    axial = None
    axial_receipt = receipts.get(AXIAL_STAGE)
    if "column_axial" in source:
        if axial_receipt is None or axial_receipt["input_sha256"] != modal["input_sha256"]:
            raise ReportUnavailable("Column axial receipt missing or bound to another capture")
        try:
            axial = evaluate_column_axial(source, geometry, new_checks, setup=analysis_setup)
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            raise ReportUnavailable("Column axial source cannot be verified") from exc
        if axial != axial_receipt["payload"]:
            raise ReportUnavailable("Column axial source/receipt mismatch")
    elif axial_receipt is not None:
        raise ReportUnavailable("Orphan column axial receipt")

    pmm = None
    from .engineering.column_pmm import STAGE as PMM_STAGE, evaluate_column_pmm

    pmm_receipt = receipts.get(PMM_STAGE)
    member_request = (source.get("column_axial") or {}).get("request") or {}
    if member_request.get("pmm_member"):
        if pmm_receipt is None or pmm_receipt["input_sha256"] != modal["input_sha256"]:
            raise ReportUnavailable("Column PMM receipt missing or bound to another capture")
        try:
            pmm = evaluate_column_pmm(source, geometry, axial)
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            raise ReportUnavailable("Column PMM source cannot be verified") from exc
        if pmm != pmm_receipt["payload"]:
            raise ReportUnavailable("Column PMM source/receipt mismatch")
    elif pmm_receipt is not None:
        raise ReportUnavailable("Orphan column PMM receipt")

    stages = {
        "result": modal["result"], "geometry": geometry, "extra": new_checks, "vs04": vs04,
        "vs04_numerics": vs04_numerics, "vs04_readiness": vs04_readiness, "vs04_pipeline": vs04_pipeline,
        "story_drift": story_drift, "r08_second_order": r08_second_order, "analysis_setup": analysis_setup,
        "column_axial": axial, "column_pmm": pmm,
    }
    if snapshot is not None:
        old_stages = snapshot["results"]
        for key in ("beam_r10", "r10_live", "column_gates", "analysis_setup_reconciliation",
                    "r08_local_slenderness", "r14_closure"):
            stages[key] = old_stages.get(key)
    else:
        beam_r10 = r10_live = column_gates = None
        if axial is not None:
            from .engineering.beam_r10_live import project_beam_r10_live
            from .engineering.column_live_gates import project_column_gates
            from .engineering.column_r10_live import project_column_r10_live

            beam_r10 = project_beam_r10_live(source, geometry, axial, pmm, new_checks)
            r10_live = project_column_r10_live(source, geometry, axial, pmm, new_checks, beam_live=beam_r10)
            column_gates = project_column_gates(
                source, axial, pmm, local_axis_angle_deg=(r10_live or {}).get("local_axis_angle_deg"),
            )
        stages.update(beam_r10=beam_r10, r10_live=r10_live, column_gates=column_gates,
                      analysis_setup_reconciliation=(
                          project_analysis_setup_reconciliation(analysis_setup, source) if analysis_setup is not None else None
                      ), r08_local_slenderness=None, r14_closure=None)

    from .engineering.pipeline import derive_report_evidence

    evidence = derive_report_evidence(source, stages)
    if pmm is not None and snapshot is None:
        from .engineering.column_r08_local_live import project_column_r08_local_live
        from .engineering.column_r14_closure import project_column_r14_and_r15_closure

        local = project_column_r08_local_live(
            source, geometry, axial, pmm, evidence["r08_second_order"], r10_live=stages["r10_live"],
        )
        stages["r08_local_slenderness"] = local
        stages["r14_closure"] = project_column_r14_and_r15_closure(
            geometry=geometry, axial=axial, pmm=pmm, r08_second_order=evidence["r08_second_order"],
            r08_local=local, beam_r10=stages["beam_r10"], r10_live=stages["r10_live"],
            analysis_setup_reconciliation=stages["analysis_setup_reconciliation"],
        )
    return _assemble_complete_report(directory.name, source, receipts, stages, evidence, snapshot)


def _column_candidate_schedule(stages: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict | None:
    """Display recorded candidates and dependent results; never select or assess a cage."""
    r10 = stages.get("r10_live") or {}
    members = r10.get("per_member")
    if members is None:
        members = {r10["member_id"]: r10} if r10.get("member_id") else {}
    dependencies = evidence.get("design_dependencies") or {}
    ledger = dependencies.get("selected_candidates") or {}
    if not ledger and not any(m.get("engineer_column_selection") for m in members.values()):
        return None
    pmm = stages.get("column_pmm") or {}
    pmm_members = {m["member_id"]: m for m in pmm.get("members", ())}
    if not pmm_members and pmm.get("member_id") not in (None, "ALL"):
        pmm_members = {pmm["member_id"]: pmm}
    bindings = {r["member_id"]: r for r in ledger.get("rows", ())}
    local = stages.get("r08_local_slenderness") or {}
    local_members = local.get("per_member")
    if local_members is None:
        local_members = {local["member_id"]: local} if local.get("member_id") else {}
    # Retain expected-but-blocked members, including a missing PMM projection.
    expected_ids = dict.fromkeys([*pmm_members, *bindings, *members])
    rows = []
    for uid in expected_ids:
        member = pmm_members.get(uid) or {}
        section = member.get("section_evidence") or {}
        selection = (members.get(uid) or {}).get("engineer_column_selection") or {}
        identity_matches = selection.get("member_id") == uid
        candidate = (selection.get("selected") or {}) if identity_matches else {}
        tie = candidate.get("selected_transverse") or {}
        binding = bindings.get(uid) or {}
        binding_status = binding.get("status", "SAME_RUN_BINDING_UNAVAILABLE")
        if selection and not identity_matches:
            binding_status = "CANDIDATE_IDENTITY_MISMATCH"
        elif binding_status == "SAME_RUN_CANDIDATE_BOUND" and not candidate:
            binding_status = "RECORDED_CANDIDATE_UNAVAILABLE"
        dependent = local_members.get(uid) or {}
        magnified = dependent.get("magnified_selected_pmm") or {}
        spectral = dependent.get("spectral_envelope_pmm_scenario") or {}
        rows.append({
            "member_id": uid, "story": member.get("story"), "section": member.get("section"),
            "t2_mm": section.get("t2_mm"), "t3_mm": section.get("t3_mm"),
            "cover_to_tie_mm": section.get("cover_to_tie_mm"),
            "recorded_reinforcement_role": section.get("reinforcement_role"),
            "selection_status": selection.get("status", "CANDIDATE_UNAVAILABLE"),
            "binding_status": binding_status, "candidate_sha256": binding.get("candidate_sha256"),
            **{key: candidate.get(key) for key in (
                "label", "bar_count", "diameter_mm", "area_mm2", "rho_percent",
                "num_bars_2_dir", "num_bars_3_dir", "minimum_clear_spacing_mm",
                "pmm_max_utilization", "pmm_satisfied")},
            "minimum_area_mm2": selection.get("tbdy_minimum_longitudinal_area_mm2") if identity_matches else None,
            **{key: tie.get(key) for key in (
                "tie_diameter_mm", "confinement_spacing_mm", "midspan_spacing_mm",
                "legs_v2", "legs_v3", "crossties_parallel_v2", "crossties_parallel_v3",
                "crosstie_max_spacing_a_mm", "crosstie_limit_25_phi_mm", "all_tbdy_checks_met")},
            "transverse_alerts": tie.get("alerts", []),
            "magnified_pmm_status": magnified.get("status"),
            "magnified_pmm_utilization": magnified.get("max_utilization"),
            "magnified_pmm_resolved_rows": magnified.get("resolved_row_count"),
            "magnified_pmm_expected_rows": magnified.get("expected_row_count"),
            "spectral_bound_status": spectral.get("status"),
            "spectral_bound_utilization": spectral.get("max_bounding_utilization"),
        })
    return {
        "schema": "tbdy.next.column-candidate-schedule.v1",
        "expected_column_count": ledger.get("expected_column_count", pmm.get("expected_column_count", len(rows))),
        "bound_column_count": sum(r["binding_status"] == "SAME_RUN_CANDIDATE_BOUND" for r in rows),
        "selection_role": ledger.get("selection_role", "CANDIDATE_APPROVAL_PENDING"),
        "rows": rows, "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY",
    }


def _assemble_complete_report(run_id: str, source: Mapping[str, Any],
                              receipts: Mapping[str, Mapping[str, Any]], stages: Mapping[str, Any],
                              evidence: Mapping[str, Any], snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    """Format archived evidence and attach provenance. No check evaluation."""
    from .engineering.pipeline_snapshot import SCHEMA

    modal = receipts.get("modal")
    quick = receipts.get("quick-geometry")
    schema = receipts.get("schema")
    geometry = stages["geometry"]
    if modal is None or quick is None or schema is None or geometry is None:
        raise ReportUnavailable("Complete modal and geometry receipts required")
    source_columns = source.get("geometry_capture")
    source_mode = schema["payload"]["source_mode"]
    shown_case = modal["payload"]["case"]
    full_projection = snapshot is not None and snapshot["schema"] == SCHEMA
    modal_definition = next(item for item in check_registry() if item["check_id"] == "modal_mass_95")
    geo_checks = geometry.get("checks", [])
    required_geometry = {"column_rect_min", "beam_width_min", "beam_depth_min", "beam_depth_width"}
    if len(geo_checks) != len(required_geometry) or {c["check_id"] for c in geo_checks} != required_geometry:
        raise ReportUnavailable("Incomplete geometry check population")
    checks = [{**modal_definition, **stages["result"], "check_id": "modal_mass_95",
               "formal_compliance": "NOT_PROVEN"}, *geo_checks]
    new_checks = stages["extra"]
    if new_checks is not None:
        checks.extend(new_checks["checks"])

    vs04, vs04_numerics = stages["vs04"], stages["vs04_numerics"]
    vs04_readiness, vs04_pipeline = stages["vs04_readiness"], stages["vs04_pipeline"]
    axial = stages["column_axial"]
    story_drift, r08_second_order = evidence["story_drift"], evidence["r08_second_order"]
    vs06_b1_result, vs06_b1_source_status = evidence["vs06_b1_result"], evidence["vs06_b1_source_status"]
    b2, wall_geometry = evidence["soft_story_b2"], evidence["wall_geometry"]
    source_controls = evidence["source_controls"]
    earthquake_combinations = evidence["earthquake_combinations"]

    def receipt_hash(stage: str) -> str | None:
        receipt = receipts.get(stage)
        return receipt["receipt_sha256"] if receipt is not None else None

    frame_rows = ((source_columns or {}).get("tables", {}).get("FRAME_ASSIGNMENTS", {})
                  .get("rows", []) or [])
    frame_types = dict(sorted(Counter(str(row.get("Type", "UNKNOWN")) for row in frame_rows).items()))
    table_descriptors: dict[str, Any] = {}
    for role, table in (source_columns or {}).get("tables", {}).items():
        table_descriptors[role] = {
            "table_key": table.get("table_key"), "record_count": table.get("row_count"),
            "capture_status": table.get("status"), "fields": table.get("fields"),
            "field_metadata": table.get("field_metadata"),
        }
    metadata = source.get("capture_metadata") or {}
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
        "design_stage_provenance": {
            "status": "SEALED_PIPELINE_STAGE_RESULTS" if snapshot is not None else "UNSEALED_LEGACY_RECOMPUTATION",
            "snapshot_results_sha256": snapshot.get("results_sha256") if snapshot else None,
            "method": snapshot.get("method") if snapshot else None,
            "full_report_projection_only": full_projection,
            **({"remaining_scope": "This archived run predates complete result snapshots."}
               if not full_projection else {}),
        },
        "title": (f"TBDY Next Engine — {inventory['count']} bounded checks"
                  + (" + VS04 E–J source evidence" if vs04_pipeline else "")
                  + " (not full TBDY design)"),
        "model": ntpath.basename(str(metadata.get("model_filename", ""))) or None,
        "captured_at_utc": modal["captured_at_utc"],
        "source_mode": source_mode,
        "modal_case": shown_case,
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
        **{key: stages[key] for key in (
            "analysis_setup", "analysis_setup_reconciliation", "column_axial", "column_pmm",
            "column_gates", "beam_r10", "r10_live", "r08_local_slenderness", "r14_closure",
        ) if stages[key] is not None},
        **{key: value for key, value in evidence.items() if value is not None},
        "column_candidate_schedule": _column_candidate_schedule(stages, evidence),
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
            "material_types": (source_columns or {}).get("material_types"),
        },
        "evaluation_counts": counts,
        "capture_metadata": metadata,
        "source_provenance": {
            "input_sha256": modal["input_sha256"],
            "modal_receipt_sha256": modal["receipt_sha256"],
            "geometry_receipt_sha256": quick["receipt_sha256"],
            "vs04_schema_receipt_sha256": receipt_hash("vs04-schema"),
            "vs04_numerics_receipt_sha256": receipt_hash("vs04-numerics"),
            "vs04_readiness_receipt_sha256": receipt_hash("vs04-readiness"),
            "vs04_pipeline_receipt_sha256": receipt_hash("vs04-pipeline"),
            "story_drift_receipt_sha256": receipt_hash("vs05-story-drift"),
            "r08_second_order_receipt_sha256": receipt_hash("r08-second-order"),
            **({"analysis_setup_receipt_sha256": receipt_hash("r03-analysis-setup")}
               if stages["analysis_setup"] is not None else {}),
            **({"column_axial_receipt_sha256": receipt_hash("column-axial")} if axial is not None else {}),
            **({"column_pmm_receipt_sha256": receipt_hash("column-pmm")} if stages["column_pmm"] is not None else {}),
            **({"engine_results_receipt_sha256": receipt_hash("engine-results")}
               if snapshot is not None else {}),
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
            analysis_setup, (report.get("source_provenance") or {}).get("analysis_setup_receipt_sha256"),
            reconciliation=report.get("analysis_setup_reconciliation")))
    if report.get("column_axial") is not None:
        vs04_sections.append(_column_axial_html(report["column_axial"],
                                               report["source_provenance"]["column_axial_receipt_sha256"],
                                               report.get("column_axial_expected_instances")))
    if report.get("column_pmm") is not None:
        vs04_sections.append(_column_pmm_html(report["column_pmm"],
                                             report["source_provenance"]["column_pmm_receipt_sha256"],
                                             report.get("column_pmm_reinforcement"),
                                             (report.get("r10_live") or {}).get("engineer_column_selection")))
    if report.get("column_candidate_schedule") is not None:
        vs04_sections.append(_column_candidate_schedule_html(report["column_candidate_schedule"]))
    if report.get("mixed_demand_components") is not None:
        vs04_sections.append(_mixed_components_html(report["mixed_demand_components"]))
    if report.get("native_demand_sources") is not None:
        vs04_sections.append(_native_demand_sources_html(report["native_demand_sources"]))
    pmm_scope = report.get("column_pmm_expected_instances")
    if pmm_scope is not None:
        mesh = pmm_scope.get("analysis_mesh") or {}
        members = mesh.get("members") or {}
        configured = pmm_scope.get("configured_output_cuts") or {}
        mesh_details = (f'<p>Analysis mesh table {_val(mesh["mesh_table_status"])} · '
                        f'Output station assignments {_val(mesh["station_table_status"])} · '
                        f'{sum(member["roster_bound"] for member in members.values())} / {len(members)} '
                        'column element rosters bound.</p>') if mesh else ""
        scope_rows = []
        for item in pmm_scope["instances"]:
            coverage = item.get("analysis_element_coverage") or {}
            required = item.get("configured_cut_coverage") or {}
            cut_gap = configured.get(item["element_id"], {}).get("reason")
            missing_configured = [
                f'{cut["object_station_m"]:.4f} / {cut["analysis_element_id"]} / {cut["element_station_m"]:.4f} ({status})'
                for key, status in (("missing_cuts", "missing"), ("ambiguous_cuts", "ambiguous"))
                for cut in required.get(key, ())
            ]
            scope_rows.append({**item,
                               "expected_elements": ", ".join(coverage.get("expected_analysis_element_ids", ())),
                               "missing_elements": ", ".join(coverage.get("missing_analysis_element_ids", ())),
                               "unmapped_elements": ", ".join(coverage.get("unmapped_analysis_element_ids", ())),
                               "configured_cuts": (f'{required["matched_count"]} / {required["required_count"]}'
                                                   if required else None),
                               "missing_configured_cuts": ", ".join(missing_configured) or cut_gap})
        vs04_sections.append(
            '<section class="percheck"><h2>PMM source coverage</h2>'
            f'<p>{_val(pmm_scope["numerically_complete_signed_pair_count"])} / '
            f'{_val(pmm_scope["expected_member_combination_count"])} expected column–combination pairs '
            'have complete signed results for their observed stations. Independent analysis cut inventory '
            + ('verified.' if pmm_scope["independent_cut_census_proven"] else 'not verified.') + '</p>'
            + mesh_details
            + _table((("element_id", "ETABS Unique ID"), ("combination", "Combination"),
                      ("expected_elements", "Expected analysis elements"), ("missing_elements", "Elements without forces"),
                      ("unmapped_elements", "Unmapped force elements"),
                      ("minimum_object_station_count", "Configured station minimum"),
                      ("observed_object_station_count", "Distinct object stations"),
                      ("configured_cuts", "Matched configured cuts"),
                      ("missing_configured_cuts", "Cut evidence (object station m / element ID / element station m)"),
                      ("section_rows_evaluated", "Evaluated cuts"), ("execution_status", "Status"),
                      ("reason", "Evidence gap")), scope_rows)
            + '</section>'
        )
    if report.get("column_gates") is not None:
        vs04_sections.append(_column_gates_html(report["column_gates"]))
    if report.get("beam_r10") is not None:
        vs04_sections.append(_beam_r10_html(report["beam_r10"]))
    if report.get("r10_live") is not None:
        vs04_sections.append(_column_r10_html(report["r10_live"]))
    if report.get("column_slenderness_evidence") is not None:
        vs04_sections.append(_column_slenderness_html(report["column_slenderness_evidence"],
                                                      report.get("r08_local_slenderness")))
    if report.get("alpha_iteration") is not None:
        vs04_sections.append(_alpha_feedback_html(report["alpha_iteration"]))
    if report.get("r14_closure") is not None:
        vs04_sections.append(_column_r14_r15_html(report["r14_closure"]))
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
<strong>Geometry receipt SHA-256:</strong> {_val(report['source_provenance']['geometry_receipt_sha256'])}<br>
<strong>Pipeline results SHA-256:</strong> {_val((report.get('design_stage_provenance') or {}).get('snapshot_results_sha256'))}</p>
{modal_section}
{''.join(vs04_sections)}
{''.join(check_sections)}
<p class="muted">The JSON export contains the raw source tables, all element rows and material type evidence.
This report replays the archived source with the original evaluators and verifies the stored results.</p>
</body></html>'''
    return html


__all__ = ["ReportUnavailable", "build_complete_report", "build_printable_html"]



def _column_axial_html(result: Mapping[str, Any], receipt_sha: str,
                       ledger: Mapping[str, Any] | None = None) -> str:
    plan = result["combination_plan"]
    columns = [{**item, **(item.get("governing") or {}), "column_status": item["status"]}
               for item in result["columns"]]
    combinations = []
    for item in result["columns"]:
        for check in item.get("combination_checks", []):
            combinations.append({"story": item["story"], "element_id": item["element_id"], **check})
    basis = {"ETABS_STRENGTH": "ETABS Strength selections", "ASSIGNED_DESIGN": "Assigned design combinations",
             "SAVED_DEFAULTS": "Recorded custom combination list"}.get(plan["source"], "Combination source unavailable")
    assignment = plan.get("design_assignment")
    coverage = ""
    if ledger is not None:
        coverage = (f'<p>Expected column–combination coverage: {_val(ledger["evaluated_count"])} / '
                    f'{_val(ledger["expected_count"])} · {_val(ledger["not_proven_count"])} unresolved'
                    + (' · Scope evidence incomplete' if not ledger["scope_complete"] else '')
                    + '</p>')
        if ledger["dependency_blockers"]:
            coverage += '<p>Source issues: ' + _val(', '.join(ledger["dependency_blockers"])) + '</p>'
    return (
        '<section class="percheck"><h2>Column axial compression · TS 500 Eq. (7.7)</h2>'
        + coverage
        + f'<p><strong>{_val(result["status"])}</strong> · {_val(basis)} · '
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


def _column_pmm_html(result: Mapping[str, Any], receipt_sha: str, reinforcement: dict | None = None,
                     selection: Mapping[str, Any] | None = None) -> str:
    if result.get("scope") == "ALL_COLUMNS" or result.get("member_id") == "ALL":
        member_rows = [
            {
                "member_id": m.get("member_id"),
                "story": m.get("story"),
                "section": m.get("section"),
                "status": m.get("status"),
                "stations": f"{m.get('evaluated_station_count', 0)}/{m.get('expected_station_count', 0)}",
                "exceed": m.get("observed_exceedance_count", 0),
                "reason": m.get("reason"),
            }
            for m in result.get("members") or ()
        ]
        return (
            '<section class="percheck"><h2>4.4 · Column PMM (all columns population)</h2>'
            f'<p>{_val(result.get("evaluated_column_count"))}/{_val(result.get("expected_column_count"))} columns · '
            f'{_val(result["status"])} · {_val(result["evaluated_station_count"])}/{_val(result["expected_station_count"])} stations.</p>'
            + _table(
                (("member_id", "Member ID"), ("story", "Story"), ("section", "Section"),
                 ("status", "Status"), ("stations", "Stations"), ("exceed", "Exceedances"), ("reason", "Note")),
                member_rows,
            )
            + f'<p>Calculation receipt SHA-256 {_val(receipt_sha)}</p></section>'
        )
    section = reinforcement or result["section_evidence"]
    minimum = (section or {}).get("tbdy_longitudinal_minimum")
    minimum_summary = ''
    if isinstance(minimum, Mapping):
        minimum_label = {
            "BELOW_MINIMUM": "Does not satisfy As ≥ 0.01 Ac",
            "MEETS_MINIMUM": "Satisfies As ≥ 0.01 Ac",
        }.get(minimum.get("status"), "Minimum reinforcement evidence unavailable")
        minimum_summary = (
            '<p>TBDY 2018 §7.3.2.1 requires As ≥ 0.01 Ac for column longitudinal reinforcement.</p>'
            + _table((("as_mm2", "Recorded As (mm²)"), ("ac_mm2", "Gross Ac (mm²)"),
                      ("rho_percent", "Recorded As / Ac (%)"), ("minimum_percent", "TBDY minimum (%)"),
                      ("minimum_area_mm2", "Required As (mm²)"), ("minimum_check", "TBDY requirement")), [{
                "as_mm2": section.get("longitudinal_steel_area_mm2"),
                "ac_mm2": section.get("gross_section_area_mm2"),
                "rho_percent": section.get("longitudinal_reinforcement_percent"),
                "minimum_percent": minimum.get("minimum_percent"),
                "minimum_area_mm2": minimum.get("minimum_area_mm2"),
                "minimum_check": minimum_label,
            }])
        )
    candidate_summary = ''
    if selection and selection.get("member_id") == result["member_id"] and selection.get("selected"):
        candidate = selection["selected"]
        required = selection.get("tbdy_minimum_longitudinal_area_mm2")
        if required is None and isinstance(minimum, Mapping):
            required = minimum.get("minimum_area_mm2")
        policy_floor = selection.get("minimum_longitudinal_area_mm2")
        candidate_summary = (
            '<h3>Engine-selected column reinforcement candidate</h3>'
            '<p>Approval pending. The PMM station results above use the recorded ETABS reinforcement basis.</p>'
            + _table((("label", "Proposed cage"), ("area_mm2", "Candidate As (mm²)"),
                      ("rho_percent", "Candidate As / Ac (%)"), ("required_as_mm2", "TBDY required As (mm²)")), [{
                **candidate, "required_as_mm2": required,
            }])
            + (f'<p>Selection policy floor As {_val(policy_floor)} mm².</p>'
               if policy_floor is not None and policy_floor != required else '')
        )
    return (
        '<section class="percheck"><h2>4.4 · Column PMM and minimum eccentricity</h2>'
        f'<p>ETABS Unique ID {_val(result["member_id"])} · {_val(result["story"])} · {_val(result["section"])} · '
        f'{_val(result["status"])} · {_val(result["evaluated_station_count"])}/{_val(result["expected_station_count"])} '
        'static combination stations.</p>'
        '<p>Signed ETABS station forces and the TS 500 minimum eccentricity floor define this section comparison. '
        'Analysis order, verification of selected reinforcement and engineering approval remain open.</p>'
        + (f'<p>{_val(result["reason"])}</p>' if result["reason"] else '')
        + _table((("name", "Combination"), ("expected_station_count", "Expected stations"),
                  ("evaluated_station_count", "Evaluated stations"), ("status", "Status"), ("reason", "Evidence gap")),
                 result["combinations"])
        + (_table((("combination", "Combination"), ("analysis_element_id", "Analysis element ID"),
                   ("object_station_m", "Object station (m)"), ("element_station_m", "Element station (m)"),
                   ("nd_kn", "Nd (kN)"), ("m2_knm", "M2 (kN·m)"), ("m3_knm", "M3 (kN·m)"),
                   ("m2_design_knm", "M2 with e_min (kN·m)"), ("m3_design_knm", "M3 with e_min (kN·m)"),
                   ("utilization", "Section utilization"), ("status", "Status"), ("reason", "Evidence gap")),
                  result["rows"]) if result["rows"] else '')
        + ('<h3>Column section and reinforcement</h3>'
           + _table((("reinforcement_role", "ETABS reinforcement basis"), ("t2_mm", "Local 2 extent (mm)"),
                     ("t3_mm", "Local 3 extent (mm)"), ("bar_count", "Longitudinal bars"),
                     ("longitudinal_bar_diameter_mm", "Bar diameter (mm)"),
                     ("cover_to_tie_mm", "Cover to tie (mm)"), ("tie_diameter_mm", "Tie diameter (mm)"),
                     ("tie_spacing_mm", "Tie spacing (mm)"), ("tie_bars_parallel_2", "Tie bars parallel to local 2"),
                     ("tie_bars_parallel_3", "Tie bars parallel to local 3")), [section])
           + minimum_summary
           + '<p>Crosstie placement, anchorage and maximum unsupported leg spacing require verified detailing.</p>'
           if section else '')
        + candidate_summary
        + f'<p>Calculation receipt SHA-256 {_val(receipt_sha)}</p></section>'
    )


def _column_candidate_schedule_html(schedule: Mapping[str, Any]) -> str:
    return (
        '<section class="percheck" id="column-candidate-schedule"><h2>Selected column reinforcement candidates</h2>'
        f'<p>{_val(schedule["bound_column_count"])}/{_val(schedule["expected_column_count"])} columns bound in the same run. '
        'Algorithm-selected candidates; approval pending. As ≥ 0.01 Ac: TBDY 2018 §7.3.2.1. '
        'Ties and crossties: TBDY 2018 §7.3.4.1–7.3.4.2. '
        'The selected-cage results below are distinct from the recorded ETABS template PMM results. '
        'Magnified PMM uses the recorded reference assumptions; spectral corners are independent bounds, not simultaneous force vectors.</p>'
        + _table((("member_id", "ETABS Unique ID"), ("story", "Story"), ("section", "Section"),
                  ("label", "Selected candidate"), ("bar_count", "Bars"), ("diameter_mm", "Bar Ø (mm)"),
                  ("area_mm2", "Selected As (mm²)"), ("rho_percent", "As / Ac (%)"),
                  ("minimum_area_mm2", "Minimum As (mm²)"), ("cover_to_tie_mm", "Cover to tie (mm)"),
                  ("minimum_clear_spacing_mm", "Clear bar spacing (mm)"),
                  ("tie_diameter_mm", "Tie Ø (mm)"), ("confinement_spacing_mm", "Confinement pitch (mm)"),
                  ("midspan_spacing_mm", "Midspan pitch (mm)"),
                  ("legs_v2", "Legs V2"), ("legs_v3", "Legs V3"),
                  ("crossties_parallel_v2", "Crossties V2"), ("crossties_parallel_v3", "Crossties V3"),
                  ("crosstie_max_spacing_a_mm", "Tied-bar spacing a (mm)"),
                  ("all_tbdy_checks_met", "Recorded transverse criteria met"),
                  ("pmm_max_utilization", "Selected static PMM utilization"),
                  ("magnified_pmm_utilization", "Magnified reference PMM utilization"),
                  ("spectral_bound_utilization", "Spectral bound utilization"),
                  ("binding_status", "Same-run cage binding"), ("selection_status", "Selection status")), schedule["rows"])
        + '<p>Hooks, anchorage, splice locations and physical confinement lengths remain subject to detailing verification.</p></section>'
    )


def _column_gates_html(gates: Mapping[str, Any]) -> str:
    axial, reinforcement = gates["axial_gates"], gates.get("reinforcement_gate")
    summary = [{
        "chk005": axial["chk005_exceedance_count"], "chk004": axial["chk004_proven_exceedance_count"],
        "unassigned": axial["chk004_exceeds_reference_but_role_unassigned_count"],
        "basis": axial["seismic_applicability_basis"], "pairs": axial["evaluated_pair_count"],
        "status": gates["status"], "formal": gates["formal_compliance"]}]
    return (
        '<section class="percheck"><h2>Recorded ETABS reinforcement gates · CHK-004 / CHK-005 / CHK-117</h2>'
        '<p>These gates retain the original ETABS reinforcement basis. Engine-selected candidates are listed separately above.</p>'
        '<p>Same axial and PMM results as above, evaluated against TS 500 Eq. (7.7), TBDY 7.3.1.2 and TBDY 7.3.2.1. '
        'A locally proven FAIL is never folded into NOT_PROVEN; no PASS or READY is issued.</p>'
        + _table((("pairs", "Evaluated pairs"), ("chk005", "CHK-005 exceedances"),
                  ("chk004", "CHK-004 proven exceedances"), ("unassigned", "CHK-004 reference exceedances, role unassigned"),
                  ("basis", "Seismic role basis"), ("status", "Gate status"), ("formal", "Formal compliance")), summary)
        + (_table((("role", "Reinforcement role"), ("rho", "ρ = Ast/Ac"), ("rho_min", "ρ min"),
                   ("would_fail_if_selected", "Would fail if selected"), ("status", "Gate status")), [reinforcement])
           if reinforcement else '')
        + _table((("code", "Open gate"), ("status", "Status")), gates["open_gates"])
        + _table((("code", "Local finding"), ("status", "Status"), ("count", "Count")), gates["local_findings"])
        + '</section>')


def _recorded_joint_calculations_html(r10: Mapping[str, Any]) -> str:
    """Display recorded member/end/axis results, including all-column captures."""
    members = r10.get("per_member")
    member_rows = (list(members.items()) if isinstance(members, Mapping) and members
                   else [(r10.get("member_id"), r10)])
    parts = ['<h3>Recorded joint calculation details</h3>'
             '<p>Values below belong to the saved calculation. A dash means the field was not recorded; '
             'missing legacy results and physical-axis mappings are not reconstructed by the report.</p>']
    for uid, member in member_rows:
        if not isinstance(member, Mapping):
            continue
        ends = member.get("member_joint_ends") or ()
        selection = (member.get("engineer_column_selection") or {}).get("selected") or {}
        if not ends:
            parts.append(f'<p>Column {_val(uid)}: joint calculation details were not recorded.</p>')
        for end in ends:
            parts.append(
                '<article class="calculation-trace">'
                f'<h4>Column {_val(end.get("member_id", uid))} · joint {_val(end.get("point_id"))} '
                f'· end {_val(end.get("end"))}</h4>'
                f'<p>Story {_val(end.get("story"))} · Section {_val(end.get("section_name"))} '
                f'· Selected candidate {_val(selection.get("label"))} '
                f'· AxisAngle {_val(member.get("local_axis_angle_deg"))} deg '
                f'· Enclosure {_val(end.get("enclosure_scenario"))} '
                f'· Status {_val(end.get("status"))} · Reason {_val(end.get("reason"))}</p>')
            axes = end.get("axes") or ()
            if not axes:
                parts.append('<p>Joint axis calculations were not recorded.</p></article>')
                continue
            geometry, identities, shears, ties, face_terms, shear_cases = [], [], [], [], [], []
            for axis in axes:
                key = axis.get("axis")
                calculation = axis.get("calculation") or {}
                shear = axis.get("joint_shear_ve") or {}
                tie = axis.get("joint_transverse_7_5_2_3") or {}
                geometry.append({**calculation, "axis": key, "axis_status": axis.get("status")})
                identities.append({
                    "axis": key,
                    "target_axis": tie.get("target_axis", shear.get("target_axis")),
                    "global_direction": tie.get("global_direction", shear.get("global_direction")),
                    "lower_column_id": tie.get("lower_column_id"), "lower_axis": tie.get("lower_axis"),
                    "axis_mapping_status": tie.get("axis_mapping_status"),
                })
                shears.append({**shear, "axis": key,
                               "status": shear.get("status", "NOT_RECORDED")})
                ties.append({**tie, "axis": key,
                             "record_status": tie.get("status", "RECORDED" if tie else "NOT_RECORDED")})
                for face, term in (shear.get("faces") or {}).items():
                    face_terms.append({**term, "axis": key, "face": face})
                for case in shear.get("column_shear_cases") or ():
                    shear_cases.append({**case, "axis": key})
            parts.append(_table((
                ("axis", "Target local axis"), ("target_axis", "Recorded target axis"),
                ("global_direction", "Global direction [X, Y, Z]"),
                ("lower_column_id", "Lower column"), ("lower_axis", "Lower local axis"),
                ("axis_mapping_status", "Physical-axis mapping")), identities))
            parts.append(_table((
                ("axis", "Axis"), ("b_mm", "b (mm)"), ("h_mm", "h (mm)"), ("bj_mm", "bj (mm)"),
                ("fck_mpa", "fck (MPa)"), ("centered_sections_assumed", "Centered sections assumed"),
                ("physical_geometry_proven", "Physical geometry proven"),
                ("axis_status", "Geometry status")), geometry))
            parts.append('<h5>Joint shear · TBDY 7.5.2.1–7.5.2.2</h5>' + _table((
                ("axis", "Axis"), ("sway_a_tension_kn", "Sway A beam tension (kN)"),
                ("sway_b_tension_kn", "Sway B beam tension (kN)"),
                ("v_kol_used_kn", "Column shear deduction (kN)"),
                ("sway_a_ve_kn", "Sway A Ve (kN)"), ("sway_b_ve_kn", "Sway B Ve (kN)")), shears))
            parts.append(_table((
                ("axis", "Axis"), ("v_kol_basis", "Deduction basis"),
                ("v_kol_applicability", "Deduction applicability and unresolved conditions")), shears))
            parts.append(_table((
                ("axis", "Axis"), ("governing_ve_kn", "Governing joint Ve (kN)"),
                ("geometric_limit_kn", "Joint limit (kN)"), ("utilization", "Utilization"),
                ("within_geometric_limit", "Within recorded limit"), ("status", "Shear status"),
                ("reason", "Reason"), ("formal_compliance", "Formal compliance")), shears))
            parts.append(_table((
                ("axis", "Axis"), ("upper_column_ids", "Upper columns"),
                ("lower_column_ids", "Lower columns"),
                ("expected_seismic_combinations", "Expected seismic combinations"),
                ("missing_column_shear_combinations", "Unresolved combinations"),
                ("column_shear_scope_complete", "Deduction scope complete"),
                ("column_topology_issues", "Topology issues")), shears))
            if face_terms:
                parts.append(_table((
                    ("axis", "Axis"), ("face", "Column face"), ("frame_id", "Beam"),
                    ("native_end", "Beam end"), ("present", "Beam present"),
                    ("fyk_mpa", "fyk (MPa)")), face_terms))
                parts.append(_table((
                    ("axis", "Axis"), ("face", "Column face"),
                    ("as_top_mm2", "Selected top As (mm²)"), ("as_bot_mm2", "Selected bottom As (mm²)"),
                    ("t_top_kn", "Top tension (kN)"), ("t_bot_kn", "Bottom tension (kN)")), face_terms))
            if shear_cases:
                parts.append(_table((
                    ("axis", "Axis"), ("combination", "Combination"),
                    ("upper_shear_kn", "Upper shear (kN)"), ("lower_shear_kn", "Lower shear (kN)"),
                    ("deduction_kn", "Deduction (kN)"), ("status", "Case status"),
                    ("missing_column_ids", "Columns without a bound cut")), shear_cases))
            parts.append('<h5>Joint transverse reinforcement · TBDY 7.5.2.3</h5>' + _table((
                ("axis", "Axis"), ("lower_required_ash_mm2", "Lower required Ash (mm²)"),
                ("lower_spacing_mm", "Lower pitch (mm)"),
                ("fraction_of_lower_required_density", "Required fraction of lower Ash/s"),
                ("required_ash_per_s_mm2_per_mm", "Required joint Ash/s (mm²/mm)"),
                ("axial_branch", "Axial branch"), ("record_status", "Record status"),
                ("reason", "Reason")), ties))
            parts.append(_table((
                ("axis", "Axis"), ("required_ash_at_joint_spacing_mm2", "Required joint Ash (mm²)"),
                ("proposed_ash_mm2", "Selected joint Ash (mm²)"),
                ("required_to_proposed_ratio", "Required / selected Ash"),
                ("all_references_met", "All recorded references met")), ties))
            parts.append(_table((
                ("axis", "Axis"), ("tie_diameter_mm", "Tie Ø (mm)"),
                ("joint_spacing_mm", "Selected pitch (mm)"), ("spacing_limit_mm", "Code pitch cap (mm)"),
                ("max_whole_spacing_for_selected_tie_mm", "Maximum whole-mm pitch for selected tie (mm)"),
                ("spacing_reference_met", "Spacing reference met"),
                ("diameter_reference_met", "Diameter reference met")), ties))
            parts.append('</article>')
    return ''.join(parts)


def _column_r10_html(r10: Mapping[str, Any]) -> str:
    enclosure = ", ".join(f"{k}:{v}" for k, v in (r10.get("enclosure_counts") or {}).items()) or None
    summary = [{
        "member_id": r10.get("member_id"),
        "angle": r10.get("local_axis_angle_deg"),
        "joint_ends": r10.get("joint_end_count"),
        "enclosure": enclosure,
        "narrow": r10.get("narrow_beam_joint_count"),
        "scwb_joints": len(r10.get("scwb_joints") or ()),
        "formal": r10.get("formal_compliance"),
    }]
    end_rows = []
    for end in r10.get("member_joint_ends") or ():
        v_lims = ", ".join(
            f"{a['axis']}:{a['calculation']['geometric_limit_kn']:.2f} kN"
            for a in end.get("axes") or ()
            if isinstance(a.get("calculation"), Mapping) and a["calculation"].get("geometric_limit_kn") is not None
        ) or None
        end_rows.append({
            "end": end.get("end"), "point_id": end.get("point_id"),
            "enclosure_scenario": end.get("enclosure_scenario"),
            "missing_faces": ", ".join(end.get("missing_faces") or ()) or None,
            "narrow_faces": ", ".join(end.get("narrow_faces") or ()) or None,
            "limits": v_lims, "status": end.get("status"),
        })
    has_eng_scwb = any(isinstance(j.get("engineer_selected_scwb"), Mapping) for j in r10.get("scwb_joints") or ())
    scwb_rows = []
    axial_ends = {}
    for j in r10.get("scwb_joints") or ():
        eng_s = j.get("engineer_selected_scwb") if isinstance(j.get("engineer_selected_scwb"), Mapping) else {}
        exception = j.get("low_axial_exception") or {}
        for end in exception.get("column_ends", ()):
            axial_ends[j.get("joint_id"), end["member_id"]] = {
                "joint": j.get("joint_id"), "member": end["member_id"], "side": end["physical_side"],
                "end": end["end"], "station": end["configured_cut"][1], "seismic_case": end["governing_seismic_combination"],
                "seismic": end["max_seismic_nd_kn"],
                "case": end["governing_combination"], "nd": end["max_nd_kn"], "limit": end["limit_kn"],
                "decision": exception.get("status"),
            }
        scwb_rows.append({
            "joint_id": j.get("joint_id"), "target_end": j.get("target_end"), "direction": j.get("direction"),
            "column_ids": ", ".join(j.get("column_ids") or ()),
            "beam_ids": ", ".join(j.get("beam_ids") or ()) or None,
            "sampled_min_mrc": j.get("sampled_minimum_column_sum_knm"),
            "sampled_min_mrb": j.get("sampled_minimum_beam_sum_knm"),
            "min_scwb_ratio": j.get("sampled_minimum_normalized_ratio"),
            "eng_min_mrb": eng_s.get("sampled_minimum_beam_sum_knm"),
            "eng_scwb_ratio": eng_s.get("sampled_minimum_normalized_ratio"),
            "low_axial": exception.get("status"),
            "status": j.get("status"),
        })
    eng_col = r10.get("engineer_column_selection")
    eng_col_rows = []
    if isinstance(eng_col, Mapping):
        sel = eng_col.get("selected") or {}
        cands = eng_col.get("candidates_by_diameter") or {}
        for d_key, cand in cands.items():
            if not isinstance(cand, Mapping):
                continue
            tr = cand.get("selected_transverse") or {}
            eng_col_rows.append({
                "role": "SELECTED" if sel.get("diameter_mm") == cand.get("diameter_mm") and cand.get("eligible") else "CANDIDATE",
                "diam": f"Φ{d_key}",
                "cage": cand.get("label") or cand.get("pmm_error"),
                "rho": round(cand["rho_percent"], 2) if cand.get("rho_percent") is not None else None,
                "pmm": f"OK ({cand['pmm_max_utilization']:.3f})" if cand.get("pmm_satisfied") and cand.get("pmm_max_utilization") is not None else (
                    f"FAIL ({cand['pmm_max_utilization']:.3f})" if cand.get("pmm_max_utilization") is not None else cand.get("pmm_error")
                ),
                "stirrups": (f"{tr.get('confinement_label')} / {tr.get('midspan_label')}" if tr else None),
                "legs": (f"{tr.get('legs_v2')}/{tr.get('legs_v3')}" if tr else None),
                "alerts": ", ".join(tr.get("alerts") or ()) or ("OK" if cand.get("eligible") else "BLOCKED"),
            })
    trans = r10.get("column_transverse_and_shear")
    trans_rows = []
    if isinstance(trans, Mapping):
        conf = trans.get("confinement") or {}
        for axis in ("V2", "V3"):
            item = conf.get(axis)
            if isinstance(item, Mapping):
                trans_rows.append({
                    "axis": axis, "asw_mm2": item.get("asw_mm2"),
                    "provided_ash_mm2": item.get("ash_mm2"),
                    "req_ratio": item.get("eq71_a_mm2"),
                    "req_floor": item.get("eq71_b_mm2"),
                    "s_bound": item.get("high_axial_spacing_bound_mm"),
                    "max_util": trans.get("max_v2_ts500_utilization") if axis == "V2" else trans.get("max_v3_ts500_utilization"),
                    "status": trans.get("status"),
                })
    scwb_cols: tuple[tuple[str, str], ...] = (
        ("joint_id", "Joint"), ("target_end", "End"), ("direction", "Dir"),
        ("column_ids", "Columns"), ("beam_ids", "Beams"),
        ("sampled_min_mrc", "Min sum Mrc (kN·m)"), ("sampled_min_mrb", "Min sum Mrb (kN·m)"),
        ("min_scwb_ratio", "Min SCWB ratio"),
    )
    if has_eng_scwb:
        scwb_cols = scwb_cols + (
            ("eng_min_mrb", "Eng. min sum Mrb (kN·m)"),
            ("eng_scwb_ratio", "Eng. SCWB ratio"),
        )
    if any(row["low_axial"] for row in scwb_rows):
        scwb_cols += (("low_axial", "7.3.5.3(a) low-axial exception"),)
    scwb_cols = scwb_cols + (("status", "SCWB status"),)
    return (
        '<section class="percheck"><h2>Column R10 · Joints, SCWB and shear/confinement</h2>'
        '<p>Recorded joint, SCWB and transverse results from the saved pipeline run. '
        'Selected reinforcement and capacity references are shown where recorded; '
        'formal compliance stays NOT_PROVEN.</p>'
        + _table((("member_id", "Target column"), ("angle", "AxisAngle (deg)"), ("joint_ends", "Column ends checked"),
                  ("enclosure", "Enclosure counts"), ("narrow", "Narrow-beam ends"),
                  ("scwb_joints", "SCWB joint checks"), ("formal", "Formal compliance")), summary)
        + (_table((("end", "End"), ("point_id", "Point"), ("enclosure_scenario", "Enclosure"),
                   ("missing_faces", "Missing faces"), ("narrow_faces", "Narrow faces"),
                   ("limits", "Centered 7.5 limits"), ("status", "Status")), end_rows) if end_rows else '')
        + (_table(scwb_cols, scwb_rows) if scwb_rows else '')
        + ('<h3>Axial force at the connected column ends · TBDY 7.3.5.3(a)</h3>' +
           _table((("joint", "Joint"), ("member", "Column"), ("side", "Side"), ("end", "End"),
                   ("station", "Object station (m)"), ("seismic_case", "Governing seismic combination"),
                   ("seismic", "Max seismic Nd (kN)"), ("case", "Governing over all assignments"), ("nd", "Max assigned Nd (kN)"),
                   ("limit", "0.10 Ac fck (kN)"), ("decision", "Joint decision")), list(axial_ends.values()))
           if axial_ends else '')
        + (_table((("role", "Choice"), ("diam", "Φ (mm)"), ("cage", "Bar grid"), ("rho", "Rho (%)"),
                   ("pmm", "PMM (max util)"), ("stirrups", "Stirrups (conf/span)"),
                   ("legs", "Legs V2/V3"), ("alerts", "TBDY/TS500 checks")), eng_col_rows)
           if eng_col_rows else '')
        + (_table((("axis", "Axis"), ("asw_mm2", "Asw (mm²)"), ("provided_ash_mm2", "Provided Ash (mm²)"),
                   ("req_ratio", "7.3.4.1(a) Ash (mm²)"), ("req_floor", "7.3.4.1(b) Ash (mm²)"),
                   ("s_bound", "Max s bound (mm)"), ("max_util", "Max TS500 Vd/Vr"), ("status", "Status")), trans_rows) if trans_rows else '')
        + _recorded_joint_calculations_html(r10)
        + '<h3>Recorded stage open-basis codes</h3><ul>'
        + ''.join(f'<li>{_val(item)}</li>' for item in r10.get("open_basis") or ()) + '</ul>'
        + '</section>'
    )


def _beam_r10_html(beam_r10: Mapping[str, Any]) -> str:
    rows = []
    eng_rows = []
    for beam in beam_r10.get("beams") or ():
        st = beam.get("engineer_stirrups") or {}
        st_conf = (st.get("confinement") or {}).get("label")
        st_span = (st.get("span") or {}).get("label")
        st_label = f"{st_conf} / {st_span}" if st_conf and st_span else None
        st_alerts = ", ".join(st.get("alerts") or ()) or None
        eng_ve_eq = (beam.get("engineer_shear_ve") or {}).get("earthquake_capacity_shear_term_kn")
        for end_key in ("I", "J"):
            end = (beam.get("ends") or {}).get(end_key)
            if not isinstance(end, Mapping):
                continue
            cand = (end.get("candidates") or {}).get(str(end.get("default_diameter_mm", 20))) or {}
            cap = cand.get("capacity") or {}
            rows.append({
                "beam_id": beam.get("member_id"),
                "label": beam.get("label"),
                "section": beam.get("section_name"),
                "end": end_key,
                "top_label": cand.get("top_label"),
                "bottom_label": cand.get("bottom_label"),
                "layout": cand.get("layout_mode"),
                "pos_m3": cap.get("positive_m3_knm"),
                "neg_m3": cap.get("negative_m3_knm"),
                "ve_eq_kn": (beam.get("shear_ve") or {}).get("earthquake_capacity_shear_term_kn"),
                "status": end.get("status"),
            })
            eng = end.get("engineer_selection")
            if isinstance(eng, Mapping):
                e_cap = eng.get("capacity") or {}
                t_req = eng.get("effective_target_top_mm2")
                b_req = eng.get("effective_target_bottom_mm2")
                eng_rows.append({
                    "beam_id": beam.get("member_id"),
                    "label": beam.get("label"),
                    "station": end_key,
                    "top": eng.get("top_label"),
                    "top_area": (f"{eng['area_top_mm2']:.0f} / {t_req:.0f}" if eng.get("area_top_mm2") is not None and t_req is not None else None),
                    "bottom": eng.get("bottom_label"),
                    "bot_area": (f"{eng['area_bottom_mm2']:.0f} / {b_req:.0f}" if eng.get("area_bottom_mm2") is not None and b_req is not None else None),
                    "stirrups": st_label,
                    "mr": (f"{e_cap['positive_m3_knm']:.1f} / {e_cap['negative_m3_knm']:.1f}" if e_cap.get("positive_m3_knm") is not None and e_cap.get("negative_m3_knm") is not None else None),
                    "ve_eq_kn": eng_ve_eq,
                    "alerts": st_alerts or eng.get("selection_status"),
                })
        eng_mid = beam.get("engineer_midspan")
        if isinstance(eng_mid, Mapping):
            m_cap = eng_mid.get("capacity") or {}
            t_req = eng_mid.get("effective_target_top_mm2")
            b_req = eng_mid.get("effective_target_bottom_mm2")
            eng_rows.append({
                "beam_id": beam.get("member_id"),
                "label": beam.get("label"),
                "station": "MID",
                "top": eng_mid.get("top_label"),
                "top_area": (f"{eng_mid['area_top_mm2']:.0f} / {t_req:.0f}" if eng_mid.get("area_top_mm2") is not None and t_req is not None else None),
                "bottom": eng_mid.get("bottom_label"),
                "bot_area": (f"{eng_mid['area_bottom_mm2']:.0f} / {b_req:.0f}" if eng_mid.get("area_bottom_mm2") is not None and b_req is not None else None),
                "stirrups": st_label,
                "mr": (f"{m_cap['positive_m3_knm']:.1f} / {m_cap['negative_m3_knm']:.1f}" if m_cap.get("positive_m3_knm") is not None and m_cap.get("negative_m3_knm") is not None else None),
                "ve_eq_kn": eng_ve_eq,
                "alerts": st_alerts or eng_mid.get("selection_status"),
            })
    return (
        '<section class="percheck"><h2>Beam R10 · Required areas, CHK-132 cages and N=0 signed M3</h2>'
        f'<p>Status: {_val(beam_r10.get("status"))} · Beams evaluated: {_val(beam_r10.get("calculated_beam_count"))}/{_val(beam_r10.get("beam_count"))} '
        '· Candidate scenarios only; formal compliance remains NOT_PROVEN.</p>'
        + (_table((("beam_id", "Beam"), ("label", "Label"), ("station", "Zone"),
                   ("top", "Top (cont + ilave)"), ("top_area", "Top As prov/req (mm²)"),
                   ("bottom", "Bottom (cont + ilave)"), ("bot_area", "Bot As prov/req (mm²)"),
                   ("stirrups", "Stirrups (conf/span)"), ("mr", "+Mr / -Mr (kN·m)"),
                   ("ve_eq_kn", "Eng Eq Ve (kN)"), ("alerts", "Alerts / Status")), eng_rows)
           if eng_rows else '')
        + (_table((("beam_id", "Beam"), ("label", "Label"), ("section", "Section"), ("end", "End"),
                   ("top_label", "Top Φ20"), ("bottom_label", "Bottom Φ20"), ("layout", "CHK-132 layout"),
                   ("pos_m3", "+Mr (kN·m)"), ("neg_m3", "-Mr (kN·m)"), ("ve_eq_kn", "Eq Ve term (kN)"),
                   ("status", "Status")), rows) if rows else '<p>No bound beam design ends in capture.</p>')
        + '</section>'
    )


def _column_slenderness_html(evidence: Mapping[str, Any], local: Mapping[str, Any] | None = None) -> str:
    scenario_rows = []
    if isinstance(local, Mapping):
        stiff = local.get("stiffness_and_euler") or {}
        for row in local.get("combination_scenarios") or ():
            for axis in ("M2", "M3"):
                ax = (row.get("axes") or {}).get(axis) or {}
                slen_ns = ax.get("slenderness_sway_prevented_k1") or {}
                mag_ns = ax.get("magnification_sway_prevented_k1") or {}
                scenario_rows.append({
                    "combination": row.get("combination"),
                    "axis": axis,
                    "nd_kn": row.get("governing_nd_kn"),
                    "nk_kn": (stiff.get(axis) or {}).get("preferred_nk_kn"),
                    "end_ratio": ax.get("signed_end_moment_ratio"),
                    "lk_over_i": slen_ns.get("lk_over_i"),
                    "limit": slen_ns.get("neglect_limit"),
                    "beta_ref": mag_ns.get("beta"),
                    "status": slen_ns.get("status"),
                })
    stations = ", ".join(str(station) for station in evidence["observed_object_stations_m"]) or None
    inputs = "".join(f"<li>{_val(item)}</li>" for item in evidence["unverified_inputs"])
    return (
        '<section class="percheck"><h2>4.5 · Slenderness and moment magnification</h2>'
        f'<p>ETABS Unique ID {_val(evidence["member_id"])} · {_val(evidence["story"])} · '
        f'{_val(evidence["section"])} · {_val(evidence["status"])}</p>'
        '<p>Verify the clear length from physical support faces. Frame length and object stations are ETABS observations.</p>'
        + _table((("frame_length_m", "Frame length I–J (m)"), ("i_joint_id", "Joint I"),
                  ("j_joint_id", "Joint J"), ("stations", "Observed object stations (m)"),
                  ("analysis_order", "Analysis order"), ("global_pdelta_status", "R08 story precheck")),
                 [{**evidence, "stations": stations}])
        + (_table((("combination", "Static combination"), ("axis", "Axis"), ("nd_kn", "Nd (kN)"),
                   ("nk_kn", "Nk ref k=1 (kN)"), ("end_ratio", "M1/M2"),
                   ("lk_over_i", "lk/i"), ("limit", "TS500 limit"),
                   ("beta_ref", "Beta ref (no-sway)"), ("status", "Reference status")),
                  scenario_rows) if scenario_rows else '')
        + '<h3>Inputs requiring verification</h3><ul>' + inputs + '</ul></section>'
    )


def _alpha_feedback_html(record: Mapping[str, Any]) -> str:
    """Display stored iteration evidence. No qualification, solver or arithmetic."""
    qualification = record.get("final_qualification") or {}
    feasibility = record.get("final_feasibility") or {}
    reasons = sorted(set(qualification.get("reason_codes") or ())
                     | set(feasibility.get("reason_codes") or ())
                     | set(feasibility.get("failure_codes") or ()))
    cases = [{**case, "eligible": ", ".join(case.get("eligible_member_ids", ())),
              "amplified": ", ".join(case.get("amplification_member_ids", case.get("eligible_member_ids", ()))),
              "low_n_credit": ", ".join(case.get("low_axial_credit_member_ids", ())),
              "reasons": ", ".join(case.get("reason_codes", ()))}
             for case in qualification.get("cases", ())]
    trace = [{"iteration": step["iteration"], "members": ", ".join(step["changed_member_ids"]),
              "demand_sha": step["demand_revision_sha256"],
              "joint_consumers": ", ".join((step.get("actions") or {}).get("joint_consumer_member_ids", ()))}
             for step in record.get("trace", ())]
    return ('<section class="percheck"><h2>D3 · Recorded alpha demand feedback</h2>'
        '<p>Bounded conditional reference iteration; not engineering acceptance. '
        'Moments and shears are revised from the original signed source, not multiplied cumulatively. '
        'Unsupported spectral or mixed-load shear provenance remains blocked.</p>'
        + _table((("status", "Terminal state"), ("iteration_count", "Iterations"),
                  ("max_iterations", "Limit"), ("feedback_consumed", "Reference feedback consumed"),
                  ("sha256", "Recorded revision")), [record])
        + ('<p>' + escape(", ".join(reasons)) + '</p>' if reasons else '')
        + _table((("story", "Story"), ("direction", "Direction"), ("combination", "Combination"),
                  ("alpha", "Alpha"), ("factor", "Factor"), ("eligible", "Vis columns"),
                  ("amplified", "1/alpha columns"), ("low_n_credit", "Optional low-N credit"),
                  ("status", "Input status"), ("reasons", "Open reasons")), cases)
        + _table((("iteration", "Iteration"), ("members", "Re-selected columns"),
                  ("joint_consumers", "Rechecked joint consumers"), ("demand_sha", "Demand revision")), trace)
        + '</section>')


def _recorded_static_pmm_html(columns: list[Mapping[str, Any]]) -> str:
    """Project the sealed governing cut; never derive a capacity from a ratio."""
    parts = ['<h3>Recorded governing static PMM calculations</h3>'
             '<p>N is compression-positive; M2 and M3 retain the recorded local axes. '
             'Radial capacity and reserve apply at the stated N, moment direction and selected cage. '
             'These reference results do not establish engineering acceptance. '
             'A dash means the field was not recorded.</p>']
    for column in columns:
        pillar = (column.get("pillars") or {}).get("second_order_selected_pmm") or {}
        station = pillar.get("governing_static_station")
        parts.append('<article class="calculation-trace">'
                     f'<h4>Column {_val(column.get("member_id"))} · story {_val(column.get("story"))}</h4>'
                     f'<p>Selected longitudinal cage {_val(pillar.get("longitudinal_label"))} '
                     f'· Selected transverse cage {_val(pillar.get("transverse_label"))} '
                     f'· Selection {_val(pillar.get("selection_status"))} '
                     f'· PMM status {_val(pillar.get("magnified_pmm_status"))}</p>')
        if not isinstance(station, Mapping) or not station:
            parts.append('<p>Governing static station was not recorded. '
                         'No force, capacity or reserve is reconstructed from the summary ratio.</p></article>')
            continue
        parts.append(_table((
            ("combination", "Governing combination"), ("object_station_m", "Object station (m)"),
            ("analysis_element_id", "Analysis element"), ("element_station_m", "Element station (m)"),
            ("step_type", "Step type"), ("step_number", "Step number"),
            ("nd_kn", "N, compression positive (kN)")), [station]))
        parts.append(_table((
            ("first_order_m2_knm", "Source M2 (kN·m)"), ("first_order_m3_knm", "Source M3 (kN·m)"),
            ("first_order_m2_design_knm", "M2 after eccentricity floor (kN·m)"),
            ("first_order_m3_design_knm", "M3 after eccentricity floor (kN·m)")), [station]))
        parts.append(_table((
            ("beta_m2", "Local M2 factor"), ("beta_m3", "Local M3 factor"),
            ("global_beta_ii_applied", "Applied global factor"),
            ("magnified_m2_design_knm", "Design M2 (kN·m)"),
            ("magnified_m3_design_knm", "Design M3 (kN·m)")), [station]))
        parts.append(_table((
            ("moment_demand_knm", "Resultant design moment (kN·m)"),
            ("radial_capacity_knm", "Radial capacity at recorded N (kN·m)"),
            ("moment_reserve_knm", "Moment reserve (kN·m)"), ("utilization", "Utilization"),
            ("status", "Station status")), [station]))
        parts.append('</article>')
    return ''.join(parts)


def _column_r14_r15_html(r14: Mapping[str, Any]) -> str:
    if r14.get("scope") == "ALL_COLUMNS":
        summary = [{
            "expected": r14.get("expected_column_count"),
            "evaluated": r14.get("evaluated_column_count"),
            "closed": r14.get("numerically_closed_count"),
            "failed": r14.get("normative_fail_count"),
            "partial": r14.get("partial_or_unbound_count"),
            "status": r14.get("status"),
            "formal": r14.get("formal_compliance"),
        }]
        cols_tbl = [
            {
                "member_id": c.get("member_id"),
                "story": c.get("story"),
                "section": c.get("section"),
                "status": c.get("status"),
                "pmm_util": (c.get("pillars") or {}).get("second_order_selected_pmm", {}).get("max_magnified_utilization"),
                "ve_util": (c.get("pillars") or {}).get("column_shear_ve", {}).get("max_ve_ts500_utilization"),
                "scwb_ratio": (c.get("pillars") or {}).get("scwb_and_story_alpha", {}).get("min_scwb_ratio"),
                "vj_util": (c.get("pillars") or {}).get("joint_shear_and_transverse", {}).get("max_vj_utilization"),
                "failures": ", ".join(c.get("normative_failures") or ()) or None,
            }
            for c in r14.get("columns") or ()
        ]
        sa = r14.get("story_alpha") or {}
        sa_rows = [
            {
                "story": s.get("story"),
                "direction": s.get("direction"),
                "denom": f"{s.get('evaluated_column_count')}/{s.get('story_column_count')} ({s.get('denominator_status')})",
                "combo": s.get("governing_combination"),
                "alpha_i": s.get("governing_alpha_i"),
                "action": s.get("demand_feedback_action"),
            }
            for s in sa.get("stories") or ()
        ]
        return (
            '<section class="percheck"><h2>R14 / R15 · Building-wide column closure &amp; story αi</h2>'
            '<p>Full population closure ledger across all columns (R15). Formal compliance remains NOT_PROVEN pending source approvals.</p>'
            + _table((("expected", "Expected"), ("evaluated", "Evaluated"), ("closed", "Numerically closed"),
                      ("failed", "Normative fails"), ("partial", "Partial/unbound"),
                      ("status", "Building status"), ("formal", "Compliance")), summary)
            + (_table((("story", "Story"), ("direction", "Dir"), ("denom", "Column denominator"),
                       ("combo", "Governing combo"), ("alpha_i", "αi (Eq. 7.4)"), ("action", "Demand feedback")), sa_rows)
               if sa_rows else '')
            + _table((("member_id", "Column"), ("story", "Story"), ("section", "Section"),
                      ("status", "R14 Status"), ("pmm_util", "2nd-Order PMM"),
                      ("ve_util", "Ve/Vr"), ("scwb_ratio", "SCWB"), ("vj_util", "Vj util"),
                      ("failures", "Normative failures")), cols_tbl)
            + _recorded_static_pmm_html(r14.get("columns") or [])
            + '</section>'
        )
    p = r14.get("pillars") or {}
    row = [{
        "member_id": r14.get("member_id"),
        "story": r14.get("story"),
        "status": r14.get("status"),
        "pmm_util": (p.get("second_order_selected_pmm") or {}).get("max_magnified_utilization"),
        "ve_util": (p.get("column_shear_ve") or {}).get("max_ve_ts500_utilization"),
        "scwb_ratio": (p.get("scwb_and_story_alpha") or {}).get("min_scwb_ratio"),
        "vj_util": (p.get("joint_shear_and_transverse") or {}).get("max_vj_utilization"),
        "failures": ", ".join(r14.get("normative_failures") or ()) or None,
    }]
    return (
        '<section class="percheck"><h2>R14 · Single-column end-to-end closure</h2>'
        + _table((("member_id", "Column"), ("story", "Story"), ("status", "R14 Status"),
                  ("pmm_util", "2nd-Order PMM"), ("ve_util", "Ve/Vr"), ("scwb_ratio", "SCWB"),
                  ("vj_util", "Vj util"), ("failures", "Normative failures")), row)
        + _recorded_static_pmm_html([r14])
        + '</section>'
    )


def _analysis_setup_html(setup: Mapping[str, Any], receipt_sha: str | None = None,
                         *, reconciliation: Mapping[str, Any] | None = None) -> str:
    selected = setup["design_selection_count"]
    summary = (
        f'Case definitions {_val(setup["case_definition_count"])} · '
        f'Combination definitions {_val(len(setup["defined_combination_names"]) if setup["typed_graph_source_sha256"] else None)} · '
        f'Design selection {_val(selected if selected is not None else "Source unavailable")}'
    )
    diagnostics = setup["diagnostics"]
    capture_scope = ("The archived combination selection and static case settings come from separate captures."
                     if setup["source_capture_scope"] == "SEPARATE_CAPTURES" else "")
    reconciled_html = ""
    if isinstance(reconciliation, Mapping):
        assigned = reconciliation.get("assigned_design_families") or {}
        stiff = reconciliation.get("cracked_section_stiffness_audit") or {}
        blockers = reconciliation.get("reconciled_blocker_codes") or setup["blocker_codes"]
        reconciled_html = (
            f'<p><strong>Reconciled design families</strong> '
            f'{_val(assigned.get("bound_families") or "None bound")} · '
            f'Remaining {_val(assigned.get("remaining_unassigned_families") or [])}</p>'
            f'<p><strong>TBDY Table 4.2 section modifiers</strong> '
            f'{_val(stiff.get("status"))} (columns 0.70: {_val(stiff.get("all_columns_match_0_70"))}, '
            f'beams 0.35: {_val(stiff.get("all_beams_match_0_35"))})</p>'
        )
    else:
        blockers = setup["blocker_codes"]
    return (
        '<section class="percheck" data-check-panel="ANALYSIS_BASIS_GATE">'
        '<h2>R03 · ETABS analysis and concrete design setup</h2>'
        f'<p><strong>{_val(setup["status"])}</strong> · {summary}</p>'
        '<p>Strength selection comes from the ETABS design list. Project load roles and analysis generation require separate verification.</p>'
        + (f'<p>{capture_scope}</p>' if capture_scope else '')
        + reconciled_html
        + _table((("design_type", "ETABS design list"), ("combination", "Combination")),
                 setup["design_selection"] or [])
        + _table((("combination", "Defined combination"), ("operator", "ETABS operation"),
                  ("spectral_case_references", "Spectrum case references"),
                  ("observed_design_types", "Design lists captured"),
                  ("nonconcurrent_source_reasons", "Vector restriction")),
                 setup["combination_audit"])
        + _table((("case", "Linear static case"), ("stiffness_setting", "StiffType"),
                  ("nonlinear_case", "NonlinCase")), setup["linear_static_settings"])
        + '<p>Open evidence</p><ul>' + ''.join('<li>' + _val(s) + '</li>' for s in blockers)
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


def _native_demand_sources_html(record):
    modal = record.get("spectral_modal_parameters") or {}
    precision = modal.get("native_numeric_precision") or {}
    torsion = modal.get("native_torsion_definitions") or {}
    spectrum = modal.get("spectrum_response_evidence") or {}
    diaphragm = spectrum.get("diaphragm_force_context") or {}
    cut_scope = record.get("torsion_cut_scope") or {}
    spectrum_html = ('<h4>Signed spectrum amplitude evidence</h4>'
        f'<p>Expected case–mode rows {_val(spectrum.get("expected_case_mode_count"))}. '
        f'Comparison at printed precision {_val(spectrum.get("display_status_counts"))}. '
        f'Unadjusted native-curve references {_val(spectrum.get("curve_reference_count"))}.</p>'
        '<p>The comparison uses the signed participation factor and eigenvalue for the same mode. '
        'Applied amplitudes, effective modal damping and accidental-torsion forces require separate evidence.</p>'
        + _table((("case", "Spectrum case"), ("modal_case", "Modal case"), ("axis", "Excitation axis"),
                  ("curve_status", "Native spectrum curve"), ("damping_status", "Case damping definition"),
                  ("constant_ratio", "Constant damping ratio"), ("overrides", "Mode overrides")),
                 [{**c, "damping_status": c["case_damping"]["status"],
                   "constant_ratio": c["case_damping"].get("constant_ratio"),
                   "overrides": c["case_damping"].get("overrides")} for c in spectrum.get("cases", [])])
        + ''.join('<details><summary>' + _val(c.get("case")) + ' · Modal amplitude comparisons</summary>'
                  + _table((("mode", "Mode"), ("status", "Display comparison"),
                            ("amplitude_from_displayed_acceleration_m", "Amplitude from displayed acceleration (m)"),
                            ("absolute_difference_m", "Absolute difference (m)"),
                            ("printed_interval_budget_m", "Printed interval allowance (m)"),
                            ("unadjusted_curve_amplitude_m", "Unadjusted native-curve amplitude (m)"),
                            ("case_damping_ratio", "Case damping ratio"), ("effective_display_ratio", "Displayed effective ratio"),
                            ("curve_error", "Curve input gap"), ("reason", "Source gap")), c.get("rows", []))
                  + '</details>' for c in spectrum.get("cases", []))
        + f'<p>Modal XML capture {_val(spectrum.get("modal_xml_status"))}. '
        f'Diaphragm forces {_val(diaphragm.get("status"))}. '
        f'Isolated contributions {_val(cut_scope.get("isolated_contribution_count"))} / '
        f'{_val(cut_scope.get("expected_case_cut_count"))} configured case–cuts.</p>') if spectrum else ''
    numeric_html = ('<h4>Native modal numeric precision</h4>'
        f'<p>{_val(precision.get("status"))} · {_val(precision.get("bound_mode_count"))} / '
        f'{_val(precision.get("expected_mode_count"))} modal modes. '
        'Available native period, frequency, eigenvalue and participation results retain API numeric values. '
        'Spectrum amplitudes and active damping still retain display precision; force reconstruction remains unqualified.</p>'
        + _table((("modal_case", "Modal case"), ("bound_mode_count", "Bound native modes"),
                  ("expected_mode_count", "Expected modes")), precision.get("cases", []))
        + f'<p>Source gaps: {_val(precision.get("reason_codes"))}</p>'
        + '<details><summary>Native modal precision evidence</summary>'
        + _table((("modal_case", "Modal case"), ("mode", "Mode"), ("status", "Status"),
                  ("participation_identity_basis", "Participation mode identity basis"),
                  ("period_api_values", "Native period / frequency / eigenvalue"),
                  ("participation_api_values", "Native participation / mass / stiffness"),
                  ("display_absolute_differences", "Differences from displayed source"),
                  ("reason_codes", "Source gaps")), precision.get("rows", [])) + '</details>') if precision else ''
    torsion_html = ('<h4>Accidental-torsion source limits</h4>'
        f'<p>{_val(torsion.get("status"))} · {_val(torsion.get("bound_case_count"))} / '
        f'{_val(torsion.get("expected_case_count"))} case definitions. '
        'Default eccentricity is a ratio; diaphragm overrides are absolute lengths in metres. '
        'An override requires story identity. These settings do not isolate applied torsion forces.</p>'
        + _table((("case", "Spectrum case"), ("default_ratio", "Native default ratio"),
                  ("override_count", "Length overrides"), ("override_lengths_m", "Native overwrite lengths (m)"),
                  ("status", "Definition status"), ("reason_codes", "Source gaps")), torsion.get("cases", []))
        + f'<p>{_val(torsion.get("contribution_status"))}</p>') if torsion else ''
    modal_html = ('<h3>Native response-spectrum modal parameters</h3>'
        f'<p>{_val(modal.get("status"))} · {_val(modal.get("bound_mode_rows"))} / '
        f'{_val(modal.get("expected_mode_rows"))} case–mode rows. '
        'Uses the recorded selected-case table; the failed initial unselected read remains unchanged.</p>'
        '<p>Amplitudes and active damping retain native display precision. They are not yet qualified '
        'for modal force reconstruction. Eccentricity definitions do not prove accidental-torsion '
        'contributions. No concurrent vector or story-alpha authority is granted.</p>'
        + _table((("case", "Spectrum case"), ("modal_case", "Modal case"), ("active_axis", "Local excitation axis"),
                  ("bound_mode_count", "Bound modes"), ("expected_mode_count", "Expected modes"),
                  ("active_damping_min", "Min active damping ratio"), ("active_damping_max", "Max active damping ratio"),
                  ("modal_combination", "Modal combination"), ("directional_combination", "Directional combination"),
                  ("eccentricity_ratio", "Defined eccentricity ratio"), ("accidental_torsion_status", "Torsion evidence"),
                  ("status", "Parameter status"), ("reason_codes", "Source gaps")), modal.get("cases", []))
        + numeric_html + spectrum_html + torsion_html
        + f'<p>Remaining requirements: {_val(modal.get("remaining_requirements"))}</p>') if modal else ''
    return ('<section class="percheck"><h2>Native load-case and modal force coverage</h2>'
            f'<p>{_val(record["status"])} · {_val(record.get("completed_member_case_count"))} / '
            f'{_val(record.get("expected_member_case_count"))} member–case pairs. '
            f'Load patterns captured: {_val(record.get("load_pattern_definitions_captured"))}.</p>'
            '<p>Coverage uses the configured analysis-element-side cuts and the independently captured '
            'modal period inventory. Complete source coverage does not prove spectral force concurrence, '
            'SCWB axial-demand policy, story shear allocation or engineering acceptance.</p>'
            '<p>Primitive response-spectrum cases retain native scalar Max results. No Min row or '
            'simultaneous six-component force vector is synthesized.</p>'
            f'<p>Source gaps: {_val(record.get("reason_codes"))}</p>'
            + _table((("member_id", "ETABS Unique ID"), ("case", "Native case"),
                      ("case_type", "Case type"), ("force_semantics", "Force semantics"),
                      ("expected_mode_count", "Expected modes"),
                      ("observed_mode_count", "Observed modes"),
                      ("expected_cut_slices", "Required cut/step rows"),
                      ("matched_cut_slices", "Matched cut/step rows"),
                      ("status", "Source status"), ("reason_codes", "Evidence gaps")), record.get("rows", []))
            + modal_html + '</section>')


def _mixed_components_html(record):
    """Read-only scalar-envelope evidence; no inference or recomputation."""
    replay = record.get("primitive_replay") or {}
    replay_text = ('<p>Same-capture primitive-case replay: ' + _val(replay.get("status"))
        + ' · matched cuts ' + _val(replay.get("matched_cut_count")) + ' / ' + _val(replay.get("expected_cut_count"))
        + ' · scalar comparisons ' + _val(replay.get("scalar_comparisons"))
        + ' · outside tolerance ' + _val(replay.get("over_tolerance_components"))
        + '. Static centers and spectral radii are reconstructed from the recorded case forces and '
        'combination coefficients, then compared with both native limits.</p>') if replay and replay.get("status") != "NOT_CAPTURED" else (
        '<p>Observed midpoint and radius only. Separate primitive case forces were not captured for this record.</p>')
    rows = [{"member_id": r["member_id"], "combination": r["combination"], "status": r["status"],
             "expected_cut_count": r["expected_cut_count"], "required_cut_count": r["required_cut_count"],
             "observed_interval_count": len(r["cuts"]), "reason_codes": r["reason_codes"],
             "primitive_replay_status": (r.get("primitive_replay") or {}).get("status", "NOT_CAPTURED"),
             "matched_cut_count": (r.get("primitive_replay") or {}).get("matched_cut_count"),
             "mismatched_cut_count": (r.get("primitive_replay") or {}).get("mismatched_cut_count"),
             "unresolved_cut_count": (r.get("primitive_replay") or {}).get("unresolved_cut_count")}
            for r in record.get("rows", ())]
    return ('<section class="percheck"><h2>Recorded mixed/spectral scalar intervals</h2>'
            '<p>Native local P/V2/V3/T/M2/M3 bounds. Compression N reverses the P limits. '
            'No additional 100/30 or spectrum factor is applied. These intervals are NOT concurrent force '
            'vectors, and do NOT authorize story alpha or final design.</p>'
            + replay_text
            + '<p>Expected member-combination pairs: ' + _val(record.get("expected_pair_count"))
            + ' · record SHA-256: ' + _val(record.get("sha256")) + '</p>'
            + _table((("member_id", "Column"), ("combination", "Combination"), ("status", "Evidence status"),
                      ("required_cut_count", "Configured required cuts"), ("expected_cut_count", "All scoped cuts"),
                      ("observed_interval_count", "Observed intervals"),
                      ("primitive_replay_status", "Primitive replay"), ("matched_cut_count", "Matched cuts"),
                      ("mismatched_cut_count", "Mismatched cuts"), ("unresolved_cut_count", "Unresolved cuts"),
                      ("reason_codes", "Gaps")), rows)
            + '</section>')
