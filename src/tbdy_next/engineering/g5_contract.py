"""Build the two scoped G5 candidates from retained, independently replayable evidence."""
from hashlib import sha256
from .building_stage_graph import BuildingStageGraph, CONTRACTS, FIELDS
from .design_scenario import _digest
from .g1_contract import require
from .g4_contract import ACCEPTED_G4, ACCEPTED_POPULATION
from .pipeline import stage_registry
from ..verification.frame_shear import frame_audit


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


def g5_contract(source, snapshot, records, cli, web, report_building_sha, projection_checks):
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
    return {**packet,"contract_sha256":_digest(packet)}


def verification(directory,packet,snapshot):
    names=["cli-stage-projection.json","g4-contract.json","g4-verification.json","g4-expected.json","g5-contract.json","report.html"]
    result={"schema":"tbdy.next.g5-verification.v1","input_sha256":snapshot["input_sha256"],
            "contract_sha256":packet["contract_sha256"],"gaps":packet["gaps"],
            "snapshot_sha256":_digest(snapshot),"results_sha256":snapshot["results_sha256"],
            "files_sha256":{n:sha256((directory/n).read_bytes()).hexdigest() for n in names},
            "evidence_sha256":{k:_digest(v) for k,v in packet["evidence"].items()}}
    return {**result,"verification_sha256":_digest(result)}
