"""Presentation of VS20 member summaries; no engineering decisions or rounding in selection."""
from html import escape
import json
import math


def number(value, digits=2):
    if value is None:
        return "—"
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("OVERVIEW_DISPLAY_NUMBER_INVALID")
    rounded = round(value, digits)
    return f"{0 if rounded == 0 else rounded:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pmm_text(pm):
    if pm["status"] == "AXIAL_RANGE_EXCEEDED":
        return f"Axial limit exceeded · {pm['axial_outside_count']} records"
    if pm["representative_basis"] == "MAXIMUM_RESOLVED_RADIAL_PMM":
        result = number(pm["maximum_resolved_utilization"], 4) + " · conditional"
    elif pm["representative_basis"] == "MAXIMUM_AXIAL_ONLY_REFERENCE":
        result = "Axial only " + number(pm["maximum_axial_utilization"], 4)
    elif pm["status"] == "NO_STATIC_STATES":
        return "Static calculation record unavailable"
    else:
        result = "Numerical result pending"
    if pm["unresolved_count"] or pm["blocked_count"]:
        result += f" · {pm['unresolved_count']} belirsiz / {pm['blocked_count']} eksik"
    if pm["axial_only_count"] and pm["representative_basis"] == "MAXIMUM_RESOLVED_RADIAL_PMM":
        result += f" · also {pm['axial_only_count']} axial-only"
    if pm["status_counts"].get("EXCEEDS_SCENARIO_SURFACE", 0):
        result += " · surface exceeded"
    return result


SHEAR_TEXT = {"SOURCE_REFERENCE_EXCEEDED": "Source limit exceeded", "PARTIAL_SHEAR_REFERENCES": "Partial source calculation",
    "CONDITIONAL_SHEAR_REFERENCES": "Conditional source calculation", "NO_STATIC_STATES": "Static record unavailable"}


def _table(headers, rows):
    head = "".join("<th>"+escape(h)+"</th>" for h in headers)
    body = "".join("<tr>"+"".join("<td>"+escape(str(v if v is not None else "—"))+"</td>" for v in row)+"</tr>" for row in rows)
    return '<div class="overview-scroll"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def overview_html(overview):
    rows = overview["rows"]
    content = ('<section class="column-overview"><h1>Column engineering summary · VS20</h1>'
        '<p><strong>'+str(overview["member_count"])+' columns · '+str(overview["static_state_count"])+
        ' static source records · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>N, M2 and M3 in each row are concurrent components of the stated governing source record. '
        'Compression is positive and moments use the CSI local axes. Verified Nd, M2d, M3d and '
        'magnified moments are pending. Governing values are selected at full precision.</p>')
    classes = overview["source_combination_classifications"]
    content += ('<p>'+str(classes.get("STATIC_LINEAR_ADD", 0))+' direct static combinations. '+
        str(classes.get("RESPONSE_SPECTRUM_LINEAR_ADD", 0))+' combinations containing spectra are awaiting design vectors. '
        'The first table shows the '+escape(overview["default_display_candidate"])+
        ' display scenario. All three proposals remain available for engineering review.</p>')
    for index, label in enumerate(overview["candidate_labels"]):
        if index:
            content += '<details><summary>'+escape(label)+' display scenario</summary>'
        else:
            content += '<h2>'+escape(label)+' · Governing static record per column</h2>'
        table_rows = []
        for row in rows:
            scenario = next(s for s in row["scenarios"] if s["candidate_label"] == label)
            pm, sh = scenario["pmm"], scenario["shear"]
            source = pm["representative"] or {}; key = source.get("native_key", {}); vector = source.get("source_values", {})
            combo = key.get("LoadCase", "—")
            if pm["critical_state_count"] > 1:
                combo += f" · {pm['critical_state_count']} tied or equally ranked records"
            table_rows.append((row["member_id"], row["story"], combo, number(vector.get("n_compression_kn")),
                number(vector.get("m2_knm")), number(vector.get("m3_knm")), label, pmm_text(pm),
                SHEAR_TEXT[sh["status"]]+" · Ve pending", "Inputs pending"))
        content += _table(("Column", "Story", "Governing static combination", "Source N (kN)", "Source M2 (kN·m)",
            "Source M3 (kN·m)", "Reinforcement scenario", "Conditional PMM", "Shear", "Second order"), table_rows)
        if index:
            content += '</details>'
    cov = overview["station_coverage"]
    content += ('<details><summary>Combination coverage and station matches</summary><p>'+str(cov["design_row_count"])+
        ' design rows / '+str(cov["reference_count"])+' role references. '+str(cov["ambiguous_row_count"])+
        ' unresolved station rows intersect '+str(cov["ambiguous_reference_count"])+
        ' referans; kesin istasyonu bulunmayan '+str(cov["missing_exact_reference_count"])+
        ' references in '+str(cov["overlap_reference_count"])+' across '+str(cov["union_reference_count"])+
        ' combinations. Row and reference counts use separate populations. Matching requires the exact station.</p></details>')
    content += '<h2>Source and calculation details by column</h2>'
    for row in rows:
        content += '<details><summary>'+escape(row["member_id"]+' · '+str(row["story"]))+' · Calculation trace</summary>'
        for scenario in row["scenarios"]:
            pm, sh = scenario["pmm"], scenario["shear"]
            content += '<h3>'+escape(scenario["candidate_label"])+'</h3><p>'+escape(pmm_text(pm))+'</p>'
            content += _table(("Static records", "Radial PMM", "Axial only", "Axial limit exceeded", "Unresolved", "Missing"),
                [(pm[k] for k in ("static_state_count", "radial_pmm_count", "axial_only_count", "axial_outside_count", "unresolved_count", "blocked_count"))])
            content += _table(("Combination", "Station (m)", "Analysis element", "N (kN)", "M2 (kN·m)", "M3 (kN·m)"),
                [(s["native_key"]["LoadCase"], number(s["native_key"]["ObjSta"], 3), s["native_key"]["Elm"],
                    number(s["source_values"]["n_compression_kn"]), number(s["source_values"]["m2_knm"]),
                    number(s["source_values"]["m3_knm"])) for s in pm["critical_states"]])
            content += '<p>Shear maxima use their own governing source records, which can differ from the PMM governing record.</p>'
            content += _table(("Direction", "Concrete contribution scenario", "Resolved / expected", "Maximum |V|/Vr", "Governing combinations"),
                [(b["axis"], "TS500" if b["branch"] == "ts500" else "Vc=0", f"{b['numeric_count']} / {b['state_count']}",
                    number(b["maximum_source_utilization"], 4), ", ".join(sorted({s["native_key"]["LoadCase"] for s in b["critical_source_states"]})))
                    for b in sh["branches"]])
            if sh["other_limit_findings"]:
                content += '<p>Additional shear upper-bound comparisons. Actual Ve and code applicability to columns require verification.</p>'
                content += _table(("Direction", "Reference", "Combination", "Signed V (kN)", "Limit (kN)"),
                    [(f["axis"], "TS500 web limit" if f["reference"] == "ts500_web" else "TBDY brittle shear limit",
                        f["native_key"]["LoadCase"], number(f["source_signed_v_kn"]), number(f["reference_limit_kn"]))
                        for f in sh["other_limit_findings"]])
        second = row["second_order"]
        content += ('<p>Second-order analysis requires verified ln, k, lk, Cm, β and Md. '+str(second["reference_count"])+
            ' sensitivity comparisons include '+str(second["nonpositive_reference_count"])+
            ' with near-zero or negative denominators for the assumed length and stiffness references. '
            'An actual stability decision requires verified column properties.</p>')
        content += '<details><summary>Full precision, source identifiers and all governing ties</summary><pre>'+escape(
            json.dumps(row, ensure_ascii=False, indent=2, allow_nan=False))+'</pre></details></details>'
    return content+'</section>'
