"""Build the two scoped G5 candidates from retained, independently replayable evidence."""
from hashlib import sha256
from .building_stage_graph import BuildingStageGraph, CONTRACTS, FIELDS
from .design_scenario import _digest
from .g1_contract import require
from .g2_contract import _reference
from .g4_contract import ACCEPTED_G4, ACCEPTED_POPULATION
from .pipeline import stage_registry
from ..verification.frame_shear import frame_audit


ACCEPTED_G5_RUN = "RUN-149e783beb584ebc9242542da7c6b903"
ACCEPTED_G5 = "9c2920861318bd8088aeaf63c2c57c1fa27e0900b16f87055035b207a0f1fbad"
ACCEPTED_G5_VERIFICATION = "82ed1f2b1f7b91a8dd7a379df59f1dff05cfcd4221c63e9b533eee3d43a341a1"


def supervisor_decision(candidate):
    """Apply scoped Supervisor acceptance when frame shear and pipeline DAG invariants match."""
    record, _ = _reference("g5_reviewed_verification.json")
    require(record["verification_sha256"] == ACCEPTED_G5_VERIFICATION ==
            _digest({k: v for k, v in record.items() if k != "verification_sha256"})
            and record["contract_sha256"] == ACCEPTED_G5, "G5_REVIEWED_VERIFICATION_MISMATCH")
    require(candidate["contract_sha256"] == _digest({k: v for k, v in candidate.items() if k != "contract_sha256"}),
            "G5_CANDIDATE_SEAL_CHANGED")
    pipeline = candidate["evidence"].get("pipeline") or {}
    report = pipeline.get("report") or {}
    if (candidate.get("input_sha256") != record["input_sha256"]
            or candidate.get("reviewed_g4_sha256") != ACCEPTED_G4
            or candidate.get("gaps") != record["gaps"]
            or _digest(candidate["evidence"].get("frame_shear")) != record["evidence_sha256"]["frame_shear"]
            or (pipeline.get("expected_families"), pipeline.get("expected_instances"),
                len(pipeline.get("fault_injections") or ()), report.get("calculator_calls"),
                report.get("export_matches"), report.get("print_matches")) != (57, 7439, 64, 0, True, True)):
        return candidate
    same_outcomes = candidate["contract_sha256"] == ACCEPTED_G5
    if same_outcomes:
        require(record["evidence_sha256"] == {k: _digest(v) for k, v in candidate["evidence"].items()},
                "G5_REVIEWED_EVIDENCE_MISMATCH")
    decision = {"reviewed_run": ACCEPTED_G5_RUN, "reviewed_contract_sha256": ACCEPTED_G5,
                "reviewed_verification_sha256": ACCEPTED_G5_VERIFICATION,
                "accepted_gaps": ["GAP-014", "GAP-017"],
                "scope": "Independent frame capacity shear, confinement and joint-panel scope (69 columns, 180 beams) and 16-stage BuildingStageGraph / zero-recalculation projection",
                "current_outcomes_identical_to_review": same_outcomes,
                "separate_gaps": ["GAP-006", "GAP-009", "GAP-011", "GAP-012", "GAP-015", "GAP-018"],
                "excluded_families": ["slab design", "mat design", "punching", "beam torsion", "C104 transition"],
                "original_project_approval": "NOT_GRANTED"}
    out = {k: v for k, v in candidate.items() if k != "contract_sha256"}
    out.update(decision="SUPERVISOR_ACCEPTED_SCOPED", supervisor_acceptance=decision,
               gaps={k: {**v, "status": "CLOSED", "supervisor_approval": "ACCEPTED"}
                     for k, v in candidate["gaps"].items()})
    return {**out, "contract_sha256": _digest(out)}


def graph_faults(records, projection):
    registry=stage_registry()
    source=projection["input_sha256"]
    probes=[]
    for victim in CONTRACTS:
        for cause in ("missing","wrong_schema","wrong_source","invalid_content"):
            graph=BuildingStageGraph(registry,source)
            blocked=[]
            for name in graph.order:
                value=records[name]["payload"]
                try:
                    if name==victim:
                        if cause=="missing":
                            blocked.append(name)
                            continue
                        if cause=="wrong_schema":
                            value={**value,CONTRACTS[name][1]:"FAULT_INJECTION"}
                        if cause=="invalid_content":
                            value={**value,FIELDS[name][0]:None}
                    graph.validate(name,value,"different" if name==victim and cause=="wrong_source" else source)
                except ValueError:
                    blocked.append(name)
                    continue
                graph.outputs[name]=projection["stages"][name]
            descendants={victim}
            for name in graph.order:
                if descendants.intersection(CONTRACTS[name][0]):
                    descendants.add(name)
            require(set(blocked)==descendants and "engine-results" in blocked,"G5_DAG_BLOCKING_OR_ISOLATION")
            probes.append({"stage":victim,"fault":cause,"blocked":blocked})
    return probes


def g5_contract(source, snapshot, records, cli, web, report_building_sha, projection_checks, *, apply_review=True):
    stages=snapshot["results"]
    building=stages["building_design"]
    parent=building["g4_contract"]
    packet={"schema":"tbdy.next.g5-contract.v1","input_sha256":snapshot["input_sha256"],
            "parent_contract_sha256":parent["contract_sha256"],"reviewed_g4_sha256":ACCEPTED_G4,
            "decision":"SUPERVISOR_REVIEW","engineering_release":"NOT_READY","gaps":{},"evidence":{}}
    for gap in ("GAP-017","GAP-014"):
        issues=[]
        try:
            require(parent.get("supervisor_acceptance",{}).get("reviewed_contract_sha256")==ACCEPTED_G4
                    and parent["expected_population_sha256"]==ACCEPTED_POPULATION
                    and parent["input_sha256"]==snapshot["input_sha256"]
                    and _digest({k:v for k,v in parent.items() if k!="contract_sha256"})==parent["contract_sha256"],
                    "G5_ACCEPTED_G4_INVENTORY_REQUIRED")
            if gap=="GAP-014":
                frame=frame_audit(source,stages,building)
                packet["evidence"]["frame_shear"]=frame
                issues.extend(frame["issues"])
                require([frame["totals"][k] for k in ("conditional_columns","beams","static_axis_cases",
                        "spectral_axis_cases","foundation_failures")]==[69,180,414,1104,4],"G5_FRAME_CENSUS")
            else:
                require(cli==web and len(cli["stages"])==16 and cli["building_sha256"]==report_building_sha
                        ==records["building-design"]["payload"]["results_sha256"]==_digest(building)
                        and cli["input_sha256"]==packet["input_sha256"],"G5_ADAPTER_PROJECTION_CONFLICT")
                require(projection_checks["normal_web_runner_arguments"]==cli["runner_arguments"]
                        and projection_checks["calculator_calls"]==0 and projection_checks["export_matches"]
                        and projection_checks["print_matches"],"G5_REPORT_RECALCULATION_OR_CONTENT_DIFFERENCE")
                accounting=parent["evidence"]["accounting"]
                packet["evidence"]["pipeline"]={"cli_projection":cli,"http_projection":web,
                    "http_mode":"EXPLICIT_VERIFIED_ARCHIVE_AFTER_INDEPENDENT_HTTP_SOURCE_PREPARATION",
                    "source_calculations":1,"report":projection_checks,"fault_injections":graph_faults(records,cli),
                    "expected_families":accounting["family_count"],"expected_instances":accounting["expected_instances"],
                    "excluded_families":["slab design","mat design","punching","beam torsion","C104 transition"]}
        except (KeyError,IndexError,TypeError,ValueError,ArithmeticError,OSError) as exc:
            issues.append(str(exc))
        packet["gaps"][gap]={"status":"PARTIAL","closure_ready":not issues,"supervisor_approval":"PENDING",
                             "unresolved":issues}
    packet["separate_gaps"]=["GAP-006","GAP-009","GAP-011","GAP-012","GAP-015","GAP-018"]
    candidate = {**packet,"contract_sha256":_digest(packet)}
    return supervisor_decision(candidate) if apply_review else candidate


def verification(directory,packet,snapshot):
    names=["cli-stage-projection.json","g4-contract.json","g4-verification.json","g4-expected.json","g5-contract.json","report.html"]
    result={"schema":"tbdy.next.g5-verification.v1","input_sha256":snapshot["input_sha256"],
            "contract_sha256":packet["contract_sha256"],"gaps":packet["gaps"],
            "snapshot_sha256":_digest(snapshot),"results_sha256":snapshot["results_sha256"],
            "files_sha256":{n:sha256((directory/n).read_bytes()).hexdigest() for n in names},
            "evidence_sha256":{k:_digest(v) for k,v in packet["evidence"].items()}}
    return {**result,"verification_sha256":_digest(result)}
