"""Prepare an explicit self-weight axial idealization for the existing runner.

This edits a new scenario request, never the frozen source, an ETABS model or
an existing receipt. It validates the existing scenario contract; source
premises and the structural calculation are evaluated by run-pipeline.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from tbdy_next.column_engine.native_archive import decode
from tbdy_next.engineering.design_scenario import (
    CALCULATION_BASES, POLICIES, SCHEMA, create_design_scenario,
)
from tbdy_next.engineering.pipeline_snapshot import SCHEMA as SNAPSHOT_SCHEMA, read_snapshot


def prepare_request(parent_raw, request, *, members, combinations, decision_reference, scenario_id):
    """Add only the explicitly requested member/case idealization."""
    if not isinstance(request, dict):
        raise ValueError("AXIAL_IDEALIZATION_EXISTING_SCENARIO_OBJECT_REQUIRED")
    if not members or len(set(members)) != len(members):
        raise ValueError("AXIAL_IDEALIZATION_EXPLICIT_UNIQUE_MEMBERS_REQUIRED")
    if not combinations or len(set(combinations)) != len(combinations):
        raise ValueError("AXIAL_IDEALIZATION_EXPLICIT_UNIQUE_COMBINATIONS_REQUIRED")
    result = deepcopy(request)
    basis = result.get("second_order_basis") or {}
    defined = basis.get("members") or {}
    for uid in members:
        if uid not in defined:
            raise ValueError("AXIAL_IDEALIZATION_MEMBER_OUTSIDE_EXISTING_BASIS:" + uid)
        member = defined[uid]
        if not set(combinations) <= set(member.get("combinations") or ()):
            raise ValueError("AXIAL_IDEALIZATION_CASE_OUTSIDE_EXISTING_BASIS:" + uid)
        if any(axis.get("cm_policy") != "UNITY" for axis in (member.get("axes") or {}).values()):
            raise ValueError("AXIAL_IDEALIZATION_REQUIRES_EXISTING_UNITY_CM:" + uid)
        member["applicability"] = "ADOPTED_PRISMATIC_SELF_WEIGHT_NMAX_IDEALIZATION"
        member["axial_idealization"] = {
            "method": "SELF_WEIGHT_NMAX",
            "combinations": sorted(combinations),
            "decision_reference": decision_reference,
        }
    result["scenario_id"] = scenario_id
    # Keep the parent's original hash and all other choices. A wrong or stale
    # parent, undeclared field, unsupported assumption or invalid scope fails
    # through the same validation used by Web and CLI.
    create_design_scenario(parent_raw, result)
    return result


def read_scenario_run(directory):
    """Recover the validated input request and the results that consumed it."""
    raw = (directory / "input.source").read_bytes()
    snapshot = read_snapshot(directory, input_sha=sha256(raw).hexdigest())
    if snapshot is None or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("AXIAL_IDEALIZATION_FINALIZED_SCENARIO_RUN_REQUIRED")
    payload = decode(raw)
    lineage = payload.get("design_scenario") or {}
    if not lineage or "second_order_basis" not in payload:
        raise ValueError("AXIAL_IDEALIZATION_EXISTING_ADOPTED_SCENARIO_REQUIRED")
    source = directory / "parent.source"
    parent = source.read_bytes()
    request = {"schema": SCHEMA, "scenario_id": lineage["scenario_id"],
               "parent_input_sha256": lineage["parent_input_sha256"],
               **{key: payload.get(key) for key in POLICIES},
               **{key: payload[key] for key in CALCULATION_BASES if key in payload}}
    create_design_scenario(parent, request)
    return parent, request, source, snapshot


def request_from_run(directory):
    parent, request, source, _ = read_scenario_run(directory)
    return parent, request, source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--source", type=Path)
    inputs.add_argument("--from-run", type=Path, help="Finalized scenario receipt; uses its frozen parent.source")
    parser.add_argument("--scenario", type=Path,
                        help="Existing source-bound scenario request, not a result file")
    parser.add_argument("--member", action="append", required=True)
    parser.add_argument("--combination", action="append", required=True)
    parser.add_argument("--decision-reference", required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.source) != bool(args.scenario):
        parser.error("--source requires --scenario; --from-run recovers its own request")
    try:
        if args.from_run is not None:
            raw, request, source_path = request_from_run(args.from_run)
        else:
            source_path = args.source
            raw = source_path.read_bytes()
            request = json.loads(args.scenario.read_text(encoding="utf-8-sig"))
        revised = prepare_request(raw, request, members=args.member,
                                  combinations=args.combination,
                                  decision_reference=args.decision_reference,
                                  scenario_id=args.scenario_id)
        content = (json.dumps(revised, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        # Exclusive creation preserves the original request and any earlier
        # prepared experiment, including when --out accidentally reuses a path.
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("xb") as stream:
            stream.write(content)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Scenario preparation rejected: {exc}\n")
    print(json.dumps({
        "status": "SCENARIO_REQUEST_PREPARED_CALCULATION_NOT_RUN",
        "scenario_id": revised["scenario_id"],
        "request_sha256": sha256(content).hexdigest(),
        "members": args.member,
        "combinations": args.combination,
        "engineering_approval": "NOT_GRANTED",
        "conservatism": "NOT_ASSERTED",
        "source_path": str(source_path),
        "next_argv": ["python", "-B", "-m", "tbdy_next.cli", "run-pipeline", "--source", str(source_path),
                      "--design-scenario", str(args.out), "--case", "Modal", "--out", "<new receipt directory>"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
