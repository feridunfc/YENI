"""One CLI, two bounded commands; output receipts locally, never to GitHub."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .source import SourceError, artifact_sha256, parse_modal_capture, read_json, review_preflight
from .modal import evaluate_modal_mass
from .receipts import ReceiptRun


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TBDY Next Engine — verified small vertical slices")
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("inspect-preflight", "check-modal"):
        command = actions.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        if name == "check-modal":
            command.add_argument("--case", required=True)
    service = actions.add_parser("serve", help="Local web UI for one implemented vertical slice")
    service.add_argument("--host", default="127.0.0.1")
    service.add_argument("--port", type=int, default=8765)
    service.add_argument("--out", type=Path, default=Path(".receipts"))
    columns = actions.add_parser("import-column-bank", help="Verify an offline native column ZIP; no ETABS call")
    columns.add_argument("--input", type=Path, required=True)
    columns.add_argument("--historical-db", type=Path)
    columns.add_argument("--out", type=Path, default=Path(".receipts"))
    demands = actions.add_parser("inspect-column-demands", help="Derive CE-02 from an existing bank without copying its ZIP/SQLite")
    demands.add_argument("--run-id", required=True)
    demands.add_argument("--out", type=Path, default=Path(".receipts"))
    demands.add_argument("--pmm", action="store_true", help="Evaluate the three proposed cages against all static vectors")
    demands.add_argument("--shear", action="store_true", help="Compare proposed transverse steel with every static V2/V3 source state")
    demands.add_argument("--joints", action="store_true", help="Inspect native joint topology and conditional geometric references offline")
    demands.add_argument("--kinematics", action="store_true", help="Link static force-cut pairs and joint displacement states offline")
    demands.add_argument("--sensitivity", action="store_true", help="Inspect explicit TS500 stiffness and effective-length parameter families offline")
    demands.add_argument("--overview", action="store_true", help="Summarize conditional member results and exact source coverage offline")
    demands.add_argument("--quality", action="store_true", help="Independently compare primary-critical PMM capacities offline")
    demands.add_argument("--scwb", action="store_true", help="Inspect source-bound SCWB rosters and N-dependent column references offline")
    demands.add_argument("--beams", action="store_true", help="Inspect exact beam-end area sources and proposed signed N=0 capacities offline")
    demands.add_argument("--scwb-scenarios", action="store_true", help="Compare explicit column/beam proposal capacities with native joint signs offline")
    demands.add_argument("--spectral", action="store_true", help="Replay scalar spectral envelopes only; no PMM calculation or new source copy")
    demands.add_argument("--column-cage", choices=('16Φ24','16Φ28','16Φ32'), help="Display column proposal for --scwb-scenarios")
    demands.add_argument("--beam-diameter", type=int, choices=(16,20,24), help="Display beam diameter proposal for --scwb-scenarios")
    spectral = actions.add_parser("inspect-spectral-design", help="VS26 conditional sign candidates and existing PMM, entirely offline")
    spectral.add_argument("--run-id", required=True)
    spectral.add_argument("--out", type=Path, default=Path(".receipts"))
    spectral.add_argument("--member")
    spectral.add_argument("--case", dest="output_case")
    spectral.add_argument("--cage", choices=("16Φ24","16Φ28","16Φ32"))
    spectral.add_argument("--candidates", action="store_true", help="Bounded candidate page with source and numeric traces")
    spectral.add_argument("--offset", type=int, default=0)
    spectral.add_argument("--limit", type=int, default=200)
    spectral_files = spectral.add_mutually_exclusive_group()
    spectral_files.add_argument("--json", type=Path, dest="json_path", help="Write this exact bounded page, exclusively to a new file")
    spectral_files.add_argument("--html", type=Path, dest="html_path", help="Write a compact HTML report of this exact page")
    spectral_files.add_argument("--forensic", type=Path, help="Write all VS26 records as a ZIP; filters are forbidden")
    golden = actions.add_parser("inspect-golden-regression", help="Replay the pinned report bank against existing YENI kernels, separately from ETABS")
    golden.add_argument("--source-dir", type=Path, help="Optionally rehash the four original PDFs and two original audit ZIPs")
    golden.add_argument("--require-complete", action="store_true", help="Exit 3 when mandatory engineering report coverage remains incomplete")
    golden_files = golden.add_mutually_exclusive_group()
    golden_files.add_argument("--json", type=Path, dest="json_path")
    golden_files.add_argument("--html", type=Path, dest="html_path")
    live_column = actions.add_parser(
        "reconcile-live-column",
        help="Recompute one live static Grav_Ult PMM and bind R08 geometry (numeric-only)")
    for name in ("live-receipt", "lc-dl-run", "combo-capture", "combo-pmm", "geometry"):
        live_column.add_argument("--" + name, type=Path, required=True)
    live_column.add_argument("--out", type=Path, required=True)
    story_pdelta = actions.add_parser(
        "precheck-story-pdelta",
        help="Screen direction-matched RSX/RSY story shear, G+nQ and drift (numeric-only)")
    story_pdelta.add_argument("--input", type=Path, required=True)
    story_pdelta.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action in ("reconcile-live-column", "precheck-story-pdelta"):
        from .engineering.cli_adapter import run_cli
        return run_cli(args)
    if args.action == "serve":
        from .web import serve
        serve(host=args.host, port=args.port, output_root=args.out)
        return 0
    if args.action == "inspect-golden-regression":
        from .verification.golden_gate import build_golden_gate, build_golden_html
        try:
            result = build_golden_gate(source_dir=args.source_dir)
            if args.json_path is not None:
                with args.json_path.open('x', encoding='utf-8') as target:
                    json.dump(result, target, ensure_ascii=False, indent=2, allow_nan=False)
            elif args.html_path is not None:
                with args.html_path.open('x', encoding='utf-8') as target:
                    target.write(build_golden_html(result))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 3 if args.require_complete and not result['acceptance_eligible'] else 0
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(json.dumps({"status":"REJECTED","reason":str(exc),"engineering_release":"NOT_READY"},ensure_ascii=False))
            return 2
    if args.action == "inspect-spectral-design":
        import sqlite3
        from .column_engine.store import read_column_bank, verified_database
        try:
            if args.forensic is not None:
                if args.member is not None or args.output_case is not None or args.cage is not None or args.candidates or args.offset != 0 or args.limit != 200:
                    parser.error('--forensic exports the full population; do not supply display filters or pagination')
                from .column_engine.demand_view import verified_spectral_design
                from .column_engine.spectral_projection import write_spectral_forensic
                _, result = verified_spectral_design(args.out, args.run_id)
                with args.forensic.open('xb') as target:
                    manifest = write_spectral_forensic(result, target)
                verified_database(args.out, args.run_id)
                print(json.dumps({"output": str(args.forensic), "scope": manifest["scope"],
                    "pmm_result_sha256": manifest["pmm_result_sha256"], "engineering_release": "NOT_READY"}, ensure_ascii=False))
                return 0
            report = read_column_bank(args.out, args.run_id, view="spectral-candidates" if args.candidates else "spectral-design",
                member_id=args.member, output_case=args.output_case, column_label=args.cage, offset=args.offset, limit=args.limit)
            if args.html_path is not None:
                from .spectral_design_report import build_spectral_design_html
                with args.html_path.open('x', encoding='utf-8') as target: target.write(build_spectral_design_html(report))
                print(json.dumps({"output": str(args.html_path), "scope": "SELECTED_FILTERED_PAGE"}))
            elif args.json_path is not None:
                with args.json_path.open('x', encoding='utf-8') as target:
                    json.dump(report, target, ensure_ascii=False, indent=2, allow_nan=False)
                print(json.dumps({"output": str(args.json_path), "scope": "SELECTED_FILTERED_PAGE"}))
            else:
                print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
            return 0
        except (OSError, EOFError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            print(json.dumps({"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}, ensure_ascii=False))
            return 2
    if args.action == "inspect-column-demands":
        if (args.column_cage is not None or args.beam_diameter is not None) and not args.scwb_scenarios:
            parser.error('--column-cage and --beam-diameter require --scwb-scenarios')
        import sqlite3
        from .column_engine.store import read_column_bank
        if args.spectral:
            if any(getattr(args, flag) for flag in ("pmm", "shear", "joints", "kinematics", "sensitivity", "overview", "quality", "scwb", "beams", "scwb_scenarios")):
                parser.error('--spectral is a separate scalar-envelope view')
            try:
                report = read_column_bank(args.out, args.run_id, view="spectral-envelopes", limit=1)
                result = report["column_spectral_envelopes"]
                print(json.dumps({k: v for k, v in result.items() if k not in ("combinations", "spectral_cases")}, indent=2, ensure_ascii=False))
                return 0
            except (OSError, EOFError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                print(json.dumps({"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}, ensure_ascii=False))
                return 2
        try:
            report_view=("pmm-quality" if args.quality or (args.scwb_scenarios and (args.pmm or args.overview or args.shear or args.beams)) or (args.scwb and (args.pmm or args.overview or args.shear))
                or (args.beams and (args.pmm or args.overview or args.shear or args.scwb)) else "beam-cages" if args.beams
                else "scwb" if args.scwb else "overview" if args.overview else "pmm" if args.pmm else "shear" if args.shear else "native")
            if args.scwb_scenarios and report_view!='pmm-quality':report_view='scwb-scenarios'
            report = read_column_bank(args.out, args.run_id, view=report_view,
                column_label=args.column_cage or ('16Φ24' if args.scwb_scenarios else None),
                beam_diameter=args.beam_diameter or (20 if args.scwb_scenarios else None))
            chain = report["demand_chain"]
            result = {k: chain[k] for k in ("source_run_id", "source_archive_sha256", "result_sha256",
                "classification_counts", "static_candidate_count", "formal_compliance", "engineering_release")}
            result["design_summary"] = {k: chain["design_summary"][k] for k in (
                "status", "row_count", "reference_count", "known_combination_references", "unique_static_links", "link_status_counts")}
            prechecks = report["column_prechecks"]
            result["column_prechecks"] = {"critical_state_count": prechecks["critical_selection"]["critical_state_count"],
                "reinforcement_bound_members": prechecks["reinforcement_bounds"]["calculated_member_count"],
                "asmin_source_comparisons": prechecks["reinforcement_bounds"]["source_comparison_counts"],
                "result_sha256": prechecks["result_sha256"]}
            stability = report["column_stability"]
            result["column_stability"] = {k: stability[k] for k in ("calculated_section_count",
                "native_property_match_count", "elastic_member_count", "actual_second_order_applied", "result_sha256")}
            result["column_stability"]["eccentricity_reference_counts"] = stability["eccentricity"]["status_counts"]
            cages = report["column_cages"]
            result["column_cages"] = {k:cages[k] for k in ("bound_member_count","candidate_geometry_count",
                "member_proposal_count","selected_design","result_sha256")}
            if args.pmm:
                pmm = report["column_pmm"]
                result["column_pmm"] = {k:pmm[k] for k in ("static_state_count","assessment_count","status_counts",
                    "reason_counts","selected_design","formal_compliance","result_sha256")}
            transverse = report["column_transverse"]
            result["column_transverse"] = {k:transverse[k] for k in ("bound_member_count","member_proposal_count",
                "selected_design","result_sha256")}
            if args.shear or args.pmm:
                shear = report["column_shear"]
                result["column_shear"] = {k:shear[k] for k in ("static_state_count","assessment_count","status_counts",
                    "reason_counts","ve_status","selected_design","formal_compliance","result_sha256")}
            if args.joints:
                joints = report["column_joints"]
                result["column_joints"] = {k:joints[k] for k in ("joint_node_count","column_end_count","nodes_with_beams",
                    "status_counts","enclosure_counts","geometric_limit_count","tie_reference_count","scenario",
                    "ve_status","scwb_status","formal_compliance","result_sha256")}
                result["column_joints"]["graph_status"] = joints["graph"]["status"]
                result["column_joints"]["graph_reason"] = joints["graph"]["reason"]
            if args.kinematics:
                kinematics = report["column_kinematics"]
                result["column_kinematics"] = {k:kinematics[k] for k in ("expected_member_case_count",
                    "bound_force_pair_count", "calculated_kinematics_count", "linked_member_case_count", "status_counts",
                    "reason_counts", "analysis_order", "actual_second_order_applied", "result_sha256")}
                result["column_kinematics"]["stiffness_setting_counts"] = kinematics["analysis_basis"]["status_counts"]
            if args.sensitivity:
                sensitivity = report["column_sensitivity"]
                result["column_sensitivity"] = {k:sensitivity[k] for k in ("static_state_count", "state_axis_count",
                    "calculated_axis_count", "stiffness_scenario_count", "euler_reference_count", "zero_length_reference_count",
                    "source_denominator_count", "status_counts", "reason_counts", "denominator_status_counts",
                    "axial_profile_status_counts", "actual_second_order_applied", "formal_compliance", "result_sha256")}
            if args.overview:
                result["column_overview"] = report["column_overview"]
            if args.quality:
                result["column_pmm_quality"] = report["column_pmm_quality"]
            if args.scwb:
                result["column_scwb"] = report["column_scwb"]
            if args.beams:
                result["beam_end_references"] = report["beam_end_references"]
            if args.scwb_scenarios:
                result['scwb_scenarios']=report['scwb_scenarios']
        except (OSError, EOFError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            print(json.dumps({"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}, ensure_ascii=False))
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.action == "import-column-bank":
        import sqlite3
        from zipfile import BadZipFile
        from .column_engine.store import save_column_bank
        try:
            result = save_column_bank(args.input, args.out, historical_db=args.historical_db)
        except (OSError, EOFError, ValueError, KeyError, TypeError, BadZipFile, sqlite3.Error) as exc:
            print(json.dumps({"status": "REJECTED", "reason": str(exc),
                              "engineering_release": "NOT_READY"}, ensure_ascii=False))
            return 2
        summary = {k: result[k] for k in ("run_id", "source_kind", "selected_column_count",
            "observed_column_count", "force_row_count", "recorded_output_count", "formal_compliance", "engineering_release")}
        summary["static_replay_scalar_comparisons"] = result["static_replay"]["scalar_comparisons"]
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    source_sha = artifact_sha256(args.input)
    run = ReceiptRun(args.out)
    try:
        run.archive_input(args.input.read_bytes(), expected_sha256=source_sha)
        payload = read_json(args.input)
        if args.action == "inspect-preflight":
            result = review_preflight(payload)
            run.record("discovery", result, input_sha256=source_sha)
        else:
            table = parse_modal_capture(payload, case=args.case)
            run.record("schema", {
                "status": "SCHEMA_VALID",
                "table": "Modal Participating Mass Ratios",
                "target_case": table.target_case,
                "case_row_count": len(table.rows),
                "raw_row_count": table.all_rows_count,
                "source_mode": table.origin,
                "engineering_release": "NOT_READY",
            }, input_sha256=source_sha)
            result = evaluate_modal_mass(table).as_dict()
            run.record("modal", result, input_sha256=source_sha)
    except (SourceError, ValueError, KeyError) as exc:
        result = {"status": "REJECTED", "reason": str(exc), "engineering_release": "NOT_READY"}
        run.record("rejected", result, input_sha256=source_sha)
        print(json.dumps({"run_dir": str(run.root), **result}, ensure_ascii=False))
        return 2
    print(json.dumps({"run_dir": str(run.root), **result}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
