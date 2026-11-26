"""Scoped, replayable G3 review of design provenance and selected section capacities."""
from hashlib import sha256
import json

from .design_scenario import _digest
from .g2_contract import ACCEPTED_G2, _reference, require
from .g3_capacity import compare_reference, section_inputs
from .g3_demands import demand_census


def g3_contract(source, stages, building):
    g1, g2 = (building[k+"_contract"] for k in ("g1","g2"))
    base = {"schema":"tbdy.next.g3-contract.v1","input_sha256":g1.get("input_sha256"),
            "g1_contract_sha256":g1["contract_sha256"],"g2_contract_sha256":g2["contract_sha256"],
            "decision":"SUPERVISOR_REVIEW","engineering_release":"NOT_READY","excluded_gaps":["GAP-015","GAP-018"],
            "evidence":{},"gaps":{}}
    for gap in ("GAP-008","GAP-010"):
        issues = []
        try:
            require(g1["decision"] == g2["decision"] == "SUPERVISOR_ACCEPTED"
                    and g2["supervisor_acceptance"]["reviewed_contract_sha256"] == ACCEPTED_G2
                    and g2["g1_contract_sha256"] == g1["contract_sha256"]
                    and all(r["contract_sha256"] == _digest({k:v for k,v in r.items() if k!="contract_sha256"})
                            for r in (g1,g2)), "ACCEPTED_PARENT_CONTRACT_REQUIRED")
            if gap == "GAP-008":
                row = demand_census(source,stages,building)
                base["evidence"]["generation"] = row
                if row["shell_solution_role"] == "INPUT_IDENTICAL_PRIVATE_REANALYSIS":
                    issues.append("BASEMENT_SHELL_VECTORS_FROM_SEPARATE_CONTROLLED_SOLVE")
                elif not row["original_generation_independently_verified"] or row["shell_solution_role"] != "ORIGINAL_SOLVER_GENERATION":
                    issues.append("ORIGINAL_SOLVER_GENERATION_LINK_REQUIRED")
                if row["design_combinations_without_same_case_beam_force_arrays"] or not row["design_summary_has_native_element_side_and_step"]:
                    issues.append("NATIVE_BEAM_DESIGN_SUMMARY_LACKS_MATCHING_CUT_STEP_FORCE_VECTORS")
            else:
                ref,digest = _reference("g3_section_reference.json")
                require(digest == "08dfc3af3f0a6dbf8becbc1a2a1d7c72d70679f48420f2f4e51df596c4764e31"
                        and ref["source_sha256"] == base["input_sha256"], "G3_SECTION_REFERENCE_SEAL")
                base["evidence"]["sections"] = compare_reference(section_inputs(source,stages,building),ref)
        except (KeyError,IndexError,ValueError,TypeError,ArithmeticError,OSError) as exc:
            issues.append(str(exc))
        base["gaps"][gap] = {"status":"PARTIAL","closure_ready":not issues,"supervisor_approval":"PENDING","unresolved":issues}
    return {**base,"contract_sha256":_digest(base)}


def g3_verification(directory, building, input_sha):
    hashes = {}
    for group in ("g1","g2","g3"):
        name = group+"-contract.json"
        data = (directory/name).read_bytes()
        value = json.loads(data)
        require(value == building[group+"_contract"] and value["input_sha256"] == input_sha
                and value["contract_sha256"] == _digest({k:v for k,v in value.items() if k!="contract_sha256"}),
                "PERSISTED_"+group.upper()+"_CONTRACT_MISMATCH")
        hashes[name] = sha256(data).hexdigest()
    packet = building["g3_contract"]
    require(all(packet[k+"_contract_sha256"] == building[k+"_contract"]["contract_sha256"] for k in ("g1","g2")),
            "G3_PARENT_CROSS_LINK")
    record = {"schema":"tbdy.next.g3-verification.v1","files_sha256":hashes,"input_sha256":input_sha,
              "contract_sha256":packet["contract_sha256"],"gaps":packet["gaps"],
              "evidence_sha256":{k:_digest(v) for k,v in packet["evidence"].items()}}
    return {**record,"verification_sha256":_digest(record)}
