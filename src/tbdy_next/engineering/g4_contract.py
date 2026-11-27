"""Source-side population and scoped force provenance for Supervisor review."""
from hashlib import sha256
import json

from .design_scenario import _digest
from .g1_contract import require
from .g2_contract import _reference
from .g3_contract import ACCEPTED_G3
from .g3_demands import consumed_force_audit
from .g4_accounting import check_accounting
from .g4_population import SOURCE_ERRORS


ACCEPTED_RUN = "RUN-1d1f7079ce98462eb1e58b557e9daafa"
ACCEPTED_G4 = "c135f6d62d0d3293386409392d2e42278a894d78328dca25536112832bd41973"
ACCEPTED_VERIFICATION = "4782b5df5266df71d1c4c2f4b89e3b7fd35b946185d79851a6e7b09c09f61bb8"
ACCEPTED_POPULATION = "2242b7244486b5d6e90e8ac2d1715d90cf8116700efd7d37ba8c9b8d76dd3731"
ACCEPTED_PARENTS = {
    "g1": "070ac74e3b57f7f3b77f8327d0e218aa3b5f09af7766a9f23939ec64868468f2",
    "g2": "b742bfb9f35c6d35da3fbc9e7fd2f36347d8394a096251ca2283ba8afe7b7cbb",
    "g3": "f5353e755cd327262e227063c257f1f31d61d3fa9c38564d54c67af51558fc91",
}


def supervisor_decision(candidate):
    """Keep the signed inventory and provenance separate from subsequent design outcomes."""
    record, _ = _reference("g4_reviewed_verification.json")
    require(record["verification_sha256"] == ACCEPTED_VERIFICATION ==
            _digest({k:v for k,v in record.items() if k!="verification_sha256"})
            and record["contract_sha256"] == ACCEPTED_G4, "G4_REVIEWED_VERIFICATION_MISMATCH")
    require(candidate["contract_sha256"] == _digest({k:v for k,v in candidate.items() if k!="contract_sha256"}),
            "G4_CANDIDATE_SEAL_CHANGED")
    accounting = candidate["evidence"].get("accounting") or {}
    if (candidate["input_sha256"] != record["input_sha256"] or candidate.get("parents") != ACCEPTED_PARENTS
            or accounting.get("expected_population_sha256") != ACCEPTED_POPULATION
            or (accounting.get("family_count"), accounting.get("expected_instances")) != (57, 7439)
            or candidate["expected_population_sha256"] != ACCEPTED_POPULATION
            or candidate["gaps"] != record["gaps"]
            or _digest(candidate["evidence"].get("consumed_demands")) != record["evidence_sha256"]["consumed_demands"]):
        return candidate
    same_outcomes = candidate["contract_sha256"] == ACCEPTED_G4
    if same_outcomes:
        require(record["evidence_sha256"] == {k:_digest(v) for k,v in candidate["evidence"].items()},
                "G4_REVIEWED_EVIDENCE_MISMATCH")
    decision = {"reviewed_run":ACCEPTED_RUN, "reviewed_contract_sha256":ACCEPTED_G4,
                "reviewed_verification_sha256":ACCEPTED_VERIFICATION, "accepted_gaps":["GAP-005","GAP-008"],
                "scope":"Frozen check identities and consumed demand provenance for the reviewed original input",
                "expected_population_sha256":ACCEPTED_POPULATION, "current_outcomes_identical_to_review":same_outcomes,
                "separate_gaps":["GAP-011","GAP-012","GAP-015","GAP-018"],
                "open_design_families":["slabs","mats","punching","C104"], "original_project_approval":"NOT_GRANTED"}
    out = {k:v for k,v in candidate.items() if k!="contract_sha256"}
    out.update(decision="SUPERVISOR_ACCEPTED_SCOPED",supervisor_acceptance=decision,
               gaps={k:{**v,"status":"CLOSED","supervisor_approval":"ACCEPTED"} for k,v in candidate["gaps"].items()})
    return {**out,"contract_sha256":_digest(out)}


def g4_contract(source,stages,building,frozen, *, apply_review=True):
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
    candidate = {**result,"contract_sha256":_digest(result)}
    return supervisor_decision(candidate) if apply_review else candidate


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
