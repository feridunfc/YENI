"""Source-side population and scoped force provenance for Supervisor review."""
from hashlib import sha256
import json

from .design_scenario import _digest
from .g1_contract import require
from .g3_contract import ACCEPTED_G3
from .g3_demands import consumed_force_audit
from .g4_accounting import check_accounting
from .g4_population import SOURCE_ERRORS


def g4_contract(source,stages,building,frozen):
    result={"schema":"tbdy.next.g4-contract.v1","input_sha256":frozen["input_sha256"],
            "parents":{k:building[k+"_contract"]["contract_sha256"] for k in ("g1","g2","g3")},
            "decision":"SUPERVISOR_REVIEW","engineering_release":"NOT_READY","evidence":{},"gaps":{}}
    source_digest=_digest(source)
    for gap in ("GAP-008","GAP-005"):
        issues=[]
        try:
            require(result["input_sha256"]==source_digest,"G4_ARCHIVED_SOURCE_BYTES_CHANGED")
            for key in result["parents"]:
                parent=building[key+"_contract"]
                require(parent["input_sha256"]==result["input_sha256"] and
                        parent["contract_sha256"]==_digest({k:v for k,v in parent.items() if k!="contract_sha256"}),
                        "G4_PARENT_CHANGED")
            require(building["g3_contract"].get("supervisor_acceptance",{}).get("reviewed_contract_sha256")==ACCEPTED_G3,
                    "G4_APPROVED_SECTION_CONTRACT_REQUIRED")
            if gap=="GAP-008":
                result["evidence"]["consumed_demands"]=consumed_force_audit(source,stages,building)
            else:
                result["evidence"]["accounting"]=check_accounting(frozen,source,stages,building)
        except SOURCE_ERRORS as exc:
            issues.append(str(exc))
        result["gaps"][gap]={"status":"PARTIAL","closure_ready":not issues,"unresolved":issues,"supervisor_approval":"PENDING"}
    result["expected_population_sha256"]=frozen["population_sha256"]
    return {**result,"contract_sha256":_digest(result)}


def g4_verification(directory,building,input_sha):
    packet=building["g4_contract"]
    files={}
    for name in ("g1-contract","g2-contract","g3-contract","g3-verification","g4-expected","g4-contract"):
        path=directory/(name+".json")
        raw=path.read_bytes()
        data=json.loads(raw)
        require(data["input_sha256"]==input_sha,"G4_PERSISTED_INPUT_CHANGED")
        key="population_sha256" if name=="g4-expected" else "verification_sha256" if name.endswith("verification") else "contract_sha256"
        require(_digest({k:v for k,v in data.items() if k!=key})==data[key],"G4_FILE_SELF_SEAL_CHANGED")
        if name=="g4-expected":
            require(data[key]==packet["expected_population_sha256"],"G4_EXPECTED_FILE_CHANGED")
        elif name.endswith("-contract"):
            require(data==building[name.replace("-","_")],"G4_FILE_CONTRACT_CHANGED")
        files[path.name]=sha256(raw).hexdigest()
    result={"schema":"tbdy.next.g4-verification.v1","input_sha256":input_sha,"files_sha256":files,
            "contract_sha256":packet["contract_sha256"],"gaps":packet["gaps"],
            "evidence_sha256":{k:_digest(v) for k,v in packet["evidence"].items()}}
    return {**result,"verification_sha256":_digest(result)}
