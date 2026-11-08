"""Read-only VS06-D1 B1 calculation and self-contained engineering HTML report.

Usage:
python -m tools.verify_vs06_b1_sources --geometry B1_GEOMETRY.json
 --wall-loads LC_WDL_OBJECT.json --out B1_RESULT.json --html B1_RESULT.html

Never rewrites or changes original ETABS captures.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

from tbdy_next.b1_source_bridge import evaluate_b1_sources
from tools.etabs_source_gateway_windows import read_json, save_new


def _td(value: object) -> str:
    return "<td>" + escape("—" if value is None else str(value)) + "</td>"


def render_b1_html(report: dict) -> str:
    s=report["story_direction_areas"]
    parts=[]
    for level in s:
        for d in ("X","Y"):
            x=level[d]
            parts.append("<tr>"+ "".join(_td(v) for v in [
                level["story"], d, level["column_count"],x["wall_count"],
                x["loaded_beam_count"],x["loaded_beam_length_m"],
                x["column_Aw_m2"],x["wall_Ag_m2"],x["infill_Ak_assumed_m2"],
                x["infill_shear_stiffness_proxy_kN_m"],
            ])+"</tr>")
    pairs=[]
    for p in report["b1_numerical"]["paired_results"]:
        pairs.append("<tr>"+"".join(_td(p.get(v)) for v in [
            "lower_story","upper_story","direction","Ae_lower_m2",
            "Ae_upper_m2","eta_ci","numeric_condition",
            "infill_omitted_because_lower_more_than_upper",
        ])+"</tr>")
    beam_rows=[]
    for b in report["beam_assumptions"]:
        beam_rows.append("<tr>"+"".join(_td(b.get(v)) for v in [
            "beam_id","story","direction","beam_length_m","clear_wall_height_m",
            "line_load_total_kN_m","thickness_m","assumed_opening_fraction",
            "assumed_Ak_m2","assumed_stiffness_proxy_kN_m",
        ])+"</tr>")
    notes="<ol>"+ "".join("<li>"+escape(t)+"</li>" for t in report["assumptions_notes"])+"</ol>"
    def h(*headers):
        return "<thead><tr>"+"".join("<th>"+escape(x)+"</th>" for x in headers)+"</tr></thead>"
    css="""body{font:14px/1.5 system-ui,sans-serif;max-width:1200px;margin:40px auto;padding:0 24px;color:#263444}table{border-collapse:collapse;width:100%;font-size:12px}td,th{border:1px solid #d0dae4;padding:8px;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#edf4fa}h1,h2{color:#244e70}section{padding:14px 0}p.warning{border-left:4px solid #ae7940;padding:8px;background:#fff9ec}small{color:#687b8c}"""
    numerical=report["b1_numerical"]
    html=("<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
          "<meta name='viewport' content='width=device-width, initial-scale=1'><title>B1 — VS06-D1</title>"
          "<style>"+css+"</style></head><body>"
          "<h1>VS06-D1 · B1 Zayıf Kat — X/Y gerçek kaynak / varsayımsal dolgu</h1>"
          "<p class='warning'><strong>Sayısal hesap yapılmıştır; resmî TBDY uygunluğu NOT_PROVEN.</strong> "
          "ETABS yük deseni fiziksel dolgu duvar yerleşiminin kesin belgesi değildir.</p>"
          "<p>TBDY 2018 Tablo 3.6, §3.6.2.3. ΣAe = ΣAw + ΣAg + 0,15ΣAk; "
          "ηci = Ae,alt/Ae,üst. Kolon ve perde alanları ETABS gerçek kesit/koordinatlarından; "
          "dolgu alanları yük-gözlemli tahmini senaryodan türetilmiştir.</p>"
          "<p>ηci,min = <strong>"+escape(numerical["eta_ci_min"])+"</strong>; "
          "sayısal durum = <strong>"+escape(numerical["numeric_condition"])+"</strong>; "
          "R çarpanı = "+escape(str(numerical["R_multiplier_both_directions"]))+"</p>"
          "<section><h2>Kat ve yön bazında etkili alanlar (m²) ve senaryo rijitlikleri (kN/m)</h2><table>"+
          h("Kat","Yön","Kolon","Perde","Yüklü kiriş","L (m)","Aw (m²)","Ag (m²)","Ak senaryo (m²)","K proxy (kN/m)")+
          "<tbody>"+"".join(parts)+"</tbody></table></section>"
          "<section><h2>B1 katlar arası karşılaştırma</h2><table>"+
          h("Alt kat","Üst kat","Yön","Ae alt (m²)","Ae üst (m²)","ηci","Karar","Ak çıkarıldı")+
          "<tbody>"+"".join(pairs)+"</tbody></table></section>"
          "<section><h2>Kiriş bazlı LC_WDL, yükseklik, tuğla ve açıklık varsayımları</h2><table>"+
          h("ETABS ID","Kat","Yön","L (m)","Net h (m)","q (kN/m)","t (m)","Açıklık %/100","Ak (m²)","K proxy (kN/m)")+
          "<tbody>"+"".join(beam_rows)+"</tbody></table></section>"
          "<section><h2>Model varsayımları ve kapsam sınırı</h2>"+notes+"</section>"
          "<small>Geometri kaynak SHA256: "+escape(report["provenance"]["geometry_capture_sha256"])+
          "; yük kaynak SHA256: "+escape(report["provenance"]["wall_load_capture_sha256"])+
          "; sonuç SHA256: "+escape(report["result_sha256"])+
          ". Analiz/model nesli ve gerçek duvar dizilimi bağımsız onaylı değildir.</small>"
          "</body></html>")
    return html


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--geometry",type=Path,required=True)
    p.add_argument("--wall-loads",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--html",type=Path)
    p.add_argument("--wall-type",choices=("BRITTLE","FLEXIBLE"),default="BRITTLE")
    p.add_argument("--brick-gamma",default="10")
    p.add_argument("--brick-gamma-min",default="6")
    p.add_argument("--brick-gamma-max",default="20")
    p.add_argument("--opening-fraction",default="0.5")
    p.add_argument("--opening-cutoff",default="0.75")
    p.add_argument("--shear-modulus-mpa",default="500")
    p.add_argument("--r",default="7")
    args=p.parse_args()
    result=evaluate_b1_sources(
        read_json(args.geometry),read_json(args.wall_loads),
        wall_type=args.wall_type,
        unit_weight_kN_m3=args.brick_gamma,
        unit_weight_min_kN_m3=args.brick_gamma_min,
        unit_weight_max_kN_m3=args.brick_gamma_max,
        opening_fraction=args.opening_fraction,
        low_load_ratio_cutoff=args.opening_cutoff,
        shear_modulus_mpa=args.shear_modulus_mpa,
        R_base=args.r,
    )
    save_new(args.out,result)
    if args.html:
        html=render_b1_html(result)
        args.html.parent.mkdir(parents=True,exist_ok=True)
        if args.html.exists():
            raise FileExistsError("Refusing to overwrite existing B1 HTML report")
        args.html.write_text(html,encoding="utf-8")
    print(json.dumps({
        "schema":result["schema"],
        "model":result["model"],
        "story_direction_areas":result["story_direction_areas"],
        "b1_eta_min":result["b1_numerical"]["eta_ci_min"],
        "b1_numeric_condition":result["b1_numerical"]["numeric_condition"],
        "expected_b1_pairs":result["b1_numerical"]["expected_story_direction_pairs"],
        "source_wall_load_rows":result["source_wall_load_rows"],
        "source_candidate_wall_beams":result["source_candidate_wall_beams"],
        "assumption_count":len(result["assumptions_notes"]),
        "result_sha256":result["result_sha256"],
        "formal_compliance":result["formal_compliance"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
