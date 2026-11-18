#!/usr/bin/env python3
"""Compare three frozen values with the existing, hash-verified YENI owners.

This narrowly scoped harness calls section_axial_limits_kn and
minimum_eccentricity_mm in the inspected published snapshot. It does not import
the independent arithmetic verifier, create a design solver, run a pipeline,
connect to ETABS or claim complete engineering-check acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

REVIEWED_COMMIT = "b255c3030c09c88a17bbec766fc2bb22682ad027"
REVIEWED_OWNER_HASHES = {
    "src/tbdy_next/__init__.py": "14d85518cd6df9aa033853fb7bae5e70da6c95e216fa6031f4ac8e00d94d1951",
    "src/tbdy_next/column_engine/__init__.py": "d092219f153b83146e1757c96639ed591c56f513cbc2af12cf12a803571ae185",
    "src/tbdy_next/column_engine/ts500_column.py": "8411247559fc7605385a69f120b49299415138d20044381e28bb9f648f10e735",
    "src/tbdy_next/column_engine/native_archive.py": "231ccb8ebfa4030f0f310bb967930b73ed1b7e51d6871090231d723457d14c14",
    "src/tbdy_next/column_engine/csi_geometry.py": "1a7b0860dde89b9301c4818d6f42c725795decfe7a131ef97dea0b8cdd0158d6",
}
COMPARISONS = (
    ("GE-CHK-004", "GE-CHK-004-A01", "section_axial_limits_kn", "tbdy_7_3_1_2_max_ndm_kn", "kN"),
    ("GE-CHK-005", "GE-CHK-005-A02", "section_axial_limits_kn", "ts500_eq_7_7_max_nd_kn", "kN"),
    ("GE-CHK-115", "GE-CHK-115-A01", "minimum_eccentricity_mm", None, "mm"),
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_owner_hashes(repo, manifest):
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError("FETCH_MANIFEST files array is required")
    paths = [v.get("path") for v in entries]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate manifest file identity")
    by_path = {v["path"]: v for v in entries}
    evidence = []
    for path, reviewed_hash in REVIEWED_OWNER_HASHES.items():
        entry = by_path.get(path)
        if not entry or entry.get("commit") != REVIEWED_COMMIT:
            raise ValueError("Reviewed commit binding absent for " + path)
        if entry.get("sha256") != reviewed_hash or entry.get("git_blob_verified") is not True:
            raise ValueError("Reviewed file binding differs for " + path)
        file = (repo/path).resolve()
        if not file.is_relative_to(repo) or not file.is_file() or sha256(file) != reviewed_hash:
            raise ValueError("Owner dependency file hash mismatch for " + path)
        evidence.append({"path":path,"sha256":reviewed_hash,"commit":REVIEWED_COMMIT})
    return evidence


def import_verified_owner(repo):
    if any(name == "tbdy_next" or name.startswith("tbdy_next.") for name in sys.modules):
        raise ValueError("YENI was already imported; use a clean process to bind the inspected owner")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo/"src"))
    module = importlib.import_module("tbdy_next.column_engine.ts500_column")
    for name, imported in tuple(sys.modules.items()):
        if name != "tbdy_next" and not name.startswith("tbdy_next."):
            continue
        file_name = getattr(imported, "__file__", None)
        if file_name is None:
            raise ValueError("Unbound package origin for " + name)
        file = Path(file_name).resolve()
        if not file.is_relative_to(repo):
            raise ValueError("Imported owner lies outside the inspected snapshot")
        relative = file.relative_to(repo).as_posix()
        if relative not in REVIEWED_OWNER_HASHES or sha256(file) != REVIEWED_OWNER_HASHES[relative]:
            raise ValueError("An imported YENI dependency is not in the reviewed hash inventory")
    return module


def input_value(case, name, expected_unit):
    matches = [v for v in case["inputs"] if v["name"] == name]
    if len(matches) != 1 or matches[0]["unit"] != expected_unit:
        raise ValueError("Input mapping or unit is uncertain: " + case["case_id"] + "/" + name)
    return matches[0]["value"]


def positive_number(value, label):
    if type(value) not in (int,float) or not math.isfinite(value) or value <= 0:
        raise ValueError("Finite positive numeric input required: " + label)
    return value


def owner_inputs(cases, case_id):
    if case_id == "GE-CHK-115":
        h = positive_number(input_value(cases[case_id], "section_depth", "mm"), "section_depth")
        return {"bending_dimension_mm":h}, {"input_case_ids":[case_id],
            "scope":"Scalar 300 mm bending-depth primitive only; no moment, sign or rotated-axis claim."}
    c5 = cases["GE-CHK-005"]
    fck = positive_number(input_value(c5,"fck","MPa"), "fck")
    gamma = positive_number(input_value(c5,"gamma_c","1"), "gamma_c")
    ac = positive_number(input_value(c5,"Ac","mm²"), "Ac")
    input_cases = ["GE-CHK-005"]
    if case_id == "GE-CHK-004":
        c4 = cases[case_id]
        if input_value(c4,"fck","MPa") != fck:
            raise ValueError("Companion material grades do not agree")
        dims = input_value(c4,"b_h","mm")
        if not isinstance(dims,list) or len(dims) != 2:
            raise ValueError("Rectangular section input is not mapped")
        b,h = [positive_number(v,"section_dimension") for v in dims]
        if b*h != ac:
            raise ValueError("Companion section areas do not agree")
        input_cases.insert(0,case_id)
    return {"fck_mpa":fck,"fcd_mpa":fck/gamma,"ac_mm2":ac}, {
        "input_case_ids":input_cases,
        "input_preparation":"fcd is prepared as the declared fck/gamma_c input; no claim is made to test a separate material owner.",
        "scope":"Concrete-section axial limit only; role applicability, demand coverage and full control acceptance are not tested."}


def run(repo, bank_path, manifest_path):
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_case = {c["case_id"]:c for c in bank["cases"]}
    records=[]
    guard=[]
    owner=None
    guard_error=None
    try:
        guard = require_owner_hashes(repo,manifest)
        owner = import_verified_owner(repo)
    except (ValueError, ImportError, OSError) as exc:
        guard_error = type(exc).__name__ + ": " + str(exc)
    for case_id, assertion_id, function, output_key, expected_unit in COMPARISONS:
        record={"case_id":case_id,"assertion_id":assertion_id,
                "owner_file":"src/tbdy_next/column_engine/ts500_column.py",
                "owner_function":function,"output_key":output_key,"unit":expected_unit,
                "status":"UNMAPPED","engineering_control_closed":False}
        if guard_error:
            record["reason"]=guard_error
            records.append(record)
            continue
        try:
            case=by_case[case_id]
            targets=[a for a in case["assertions"] if a["assertion_id"]==assertion_id]
            if len(targets)!=1 or targets[0]["unit"] != expected_unit:
                raise ValueError("Golden target or unit is uncertain")
            target=targets[0]
            expected=positive_number(target["expected"],"golden_expected")
            args,preparation=owner_inputs(by_case,case_id)
            if function=="section_axial_limits_kn":
                result=owner.section_axial_limits_kn(**args)
                observed=float(result[output_key])
            elif function=="minimum_eccentricity_mm":
                observed=float(owner.minimum_eccentricity_mm(**args))
            else:
                raise ValueError("Owner function outside the inspected subset")
            tolerance=target["tolerance"]
            matched=math.isfinite(observed) and math.isclose(observed,expected,
                abs_tol=tolerance["absolute"],rel_tol=tolerance["relative"])
            record.update(status="MATCH" if matched else "MISMATCH",inputs=args,
                input_preparation=preparation,observed=observed,expected=expected,
                absolute_difference=abs(observed-expected),absolute_tolerance=tolerance["absolute"],
                relative_tolerance=tolerance["relative"],comparison_scope="ONE_EXISTING_OWNER_PRIMITIVE_VALUE")
        except (ValueError,KeyError,TypeError,AttributeError) as exc:
            record["reason"]=type(exc).__name__+": "+str(exc)
        records.append(record)
    matched=sum(r["status"]=="MATCH" for r in records)
    mismatched=sum(r["status"]=="MISMATCH" for r in records)
    return {"schema_version":"yeni.integration.existing-owner-comparison.v1",
        "verification_level":"EXISTING_YENI_OWNER_PRIMITIVE_COMPARISON",
        "status":"MATCH" if matched==3 else "MISMATCH" if mismatched else "INCOMPLETE",
        "executed_at_utc":datetime.now(timezone.utc).isoformat(),
        "command":[Path(sys.executable).name,*sys.argv],
        "environment":{"python":platform.python_version(),"platform":platform.platform()},
        "source_commit":REVIEWED_COMMIT,"owner_dependencies":guard,
        "fetch_manifest_sha256":sha256(manifest_path),"bank_sha256":sha256(bank_path),
        "comparison_tool_sha256":sha256(Path(__file__)),
        "comparison_count":len(records),"matched":matched,"mismatched":mismatched,
        "unmapped":sum(r["status"]=="UNMAPPED" for r in records),
        "full_engineering_checks_closed":0,"existing_44_comparison_records_replaced":0,
        "local_a2e_plus_dirty_status":"NOT_INSPECTED",
        "local_integration_owner_comparison":"NOT_RUN",
        "recorded_source_pipeline_replay":"NOT_RUN","live_etabs_source_validation":"NOT_RUN",
        "engineering_acceptance":"NOT_RUN",
        "limitations":["Only three numeric outputs from two existing owner functions are compared.",
                       "This does not validate complete CHK-004, CHK-005 or CHK-115 applicability and scope.",
                       "The inspected published snapshot is not the inaccessible local integration checkout.",
                       "No independent oracle arithmetic is used as the production implementation.",
                       "The existing 44 production comparisons retain their separate evidence scope."],
        "results":records}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",required=True,type=Path)
    parser.add_argument("--bank",required=True,type=Path)
    parser.add_argument("--manifest",required=True,type=Path,help="Hash-bound FETCH_MANIFEST.json for the inspected snapshot")
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    result=run(args.repo.resolve(),args.bank,args.manifest)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("verification_level","status","comparison_count","matched","mismatched","unmapped")},indent=2))
    return 0 if result["status"]=="MATCH" else 1


if __name__=="__main__":
    raise SystemExit(main())
