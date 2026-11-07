"""VS05 D2: candidate ModelProfile / ComboBook and frozen limited checks.

Explicitly *research-candidate only*. These declarations cannot be
self-approved or grant actual ETABS/regulatory execution. In particular,
no JSON key, source SHA-256, or "complete=true" attests that a physical
model census is complete or that case/combination generation is current.

The D2 compiler has two ownership boundaries:
  - Profile/Combo sources: untrusted candidate declarations, strictly
    validated by shape, identity, units and exact nested operator DAG;
  - D1 RegulatoryCompiler: immutable plan with execution DENIED, FCR
    accounts for every expected candidate instance without hiding gaps.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Mapping

from .compiled_dag import (
    CompilationRejected, RegulatoryCompiler, canonical_json,
)

PROFILE_SCHEMA="tbdy.next.vs05.typed-model-profile.candidate.v2"
COMBO_SCHEMA="tbdy.next.vs05.typed-combo-book.candidate.v2"
UPPER="UPPER_CANDIDATE"
BASE="BASE_CANDIDATE"
STORY_ROLES=frozenset((UPPER,BASE))
ELEMENT_TYPES=frozenset(("COLUMN","WALL","BEAM","SLAB","NULL"))
COMBO_OPERATORS=frozenset(("SUM","SRSS","ENVELOPE_MAX","ENVELOPE_MIN"))
SAFE_CONCURRENT_OPERATOR="SUM"


def _id(value: Any, name: str)->str:
    if (not isinstance(value,str) or not value or value!=value.strip()
            or len(value)>160 or any(ord(c)<32 for c in value)):
        raise CompilationRejected(name+":INVALID_ID")
    return value


def _hash(value: Any, label: str)->str:
    if (not isinstance(value,str) or len(value)!=64
            or any(c not in "0123456789abcdef" for c in value)):
        raise CompilationRejected(label+":SHA256_REQUIRED")
    return value


def _number(value: Any,label:str, *, positive:bool=False)->Decimal:
    if not isinstance(value,str) or not value or value!=value.strip():
        raise CompilationRejected(label+":DECIMAL_STRING_REQUIRED")
    try:
        x=Decimal(value)
    except InvalidOperation:
        raise CompilationRejected(label+":DECIMAL_INVALID") from None
    if not x.is_finite() or (positive and x<=0):
        raise CompilationRejected(label+":VALUE_INVALID")
    return x


def review_model_profile_candidate(source:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(source,dict) or source.get("schema")!=PROFILE_SCHEMA:
        raise CompilationRejected("CANDIDATE_PROFILE_SCHEMA_REQUIRED")
    for key in ("project_id","model_id","version"):
        _id(source.get(key),key)
    source_sha=_hash(source.get("source_snapshot_sha256"),"source_snapshot_sha256")
    if source.get("analysis_generation_id") is not None:
        raise CompilationRejected("ANALYSIS_GENERATION_CANNOT_SELF_ATTEST")
    if source.get("units")!="kN_m_C":
        raise CompilationRejected("PROFILE_SOURCE_UNITS_NOT_EXPLICIT_KN_M_C")
    stories=source.get("stories")
    elements=source.get("physical_elements")
    if not isinstance(stories,list) or not stories or not isinstance(elements,list):
        raise CompilationRejected("PROFILE_STORY_AND_ELEMENT_LIST_REQUIRED")
    names=set();base_seen=0;upper=0
    bystory={}
    for row in stories:
        if not isinstance(row,dict):
            raise CompilationRejected("INVALID_STORY_RECORD")
        sid=_id(row.get("story_id"),"story_id")
        role=row.get("role")
        if sid in names or role not in STORY_ROLES:
            raise CompilationRejected("DUPLICATE_OR_UNKNOWN_STORY_ROLE")
        names.add(sid)
        elevation=_number(row.get("elevation_m"),"story_elevation")
        if role==BASE:
            base_seen+=1
            if row.get("height_m") is not None:
                raise CompilationRejected("BASE_STORY_HEIGHT_NOT_APPLICABLE")
        else:
            upper+=1
            _number(row.get("height_m"),"height_m",positive=True)
        bystory[sid]={"role":role,"elevation_m":str(elevation)}
    if base_seen!=1 or upper==0:
        raise CompilationRejected("SINGLE_BASE_AND_NONEMPTY_UPPER_STORIES_REQUIRED")
    ids=set();counts={sid:{"COLUMN":0,"WALL":0} for sid in names}
    for row in elements:
        if not isinstance(row,dict):
            raise CompilationRejected("INVALID_PHYSICAL_ELEMENT")
        member=_id(row.get("element_id"),"element_id")
        story=row.get("story_id")
        et=row.get("element_type")
        if member in ids or story not in names or et not in ELEMENT_TYPES:
            raise CompilationRejected("DUPLICATE_ELEMENT_UNKNOWN_STORY_OR_TYPE")
        ids.add(member)
        pointi=_id(row.get("point_i"),"point_i")
        pointj=_id(row.get("point_j"),"point_j")
        if pointi==pointj:
            raise CompilationRejected("ELEMENT_TOPOLOGY_ZERO_ENDPOINT")
        if et in ("COLUMN","WALL"):
            counts[story][et]+=1
    with_role=[sid for sid in names if bystory[sid]["role"]==UPPER]
    # Never hide a story with no captured columns/walls from the denominator.
    missing=[sid for sid in with_role if not (
        counts[sid]["COLUMN"] or counts[sid]["WALL"])]
    return {
        "schema":"tbdy.next.vs05.model-profile-candidate-review.v1",
        "status":"SOURCE_CANDIDATE_ONLY",
        "model_profile_sha256":sha256(canonical_json(source)).hexdigest(),
        "source_snapshot_sha256":source_sha,
        "source_units":"kN_m_C",
        "candidate_story_count":len(stories),
        "candidate_upper_story_ids":sorted(with_role),
        "candidate_element_count":len(elements),
        "candidate_member_counts":counts,
        "upper_story_without_captured_vertical_members":sorted(missing),
        "analysis_generation_proven":False,
        "full_model_census_proven":False,
        "profile_approval_proven":False,
        "formal_compliance":"NOT_PROVEN",
    }


def review_combo_book_candidate(source:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(source,dict) or source.get("schema")!=COMBO_SCHEMA:
        raise CompilationRejected("CANDIDATE_COMBO_SCHEMA_REQUIRED")
    for key in ("book_id","version"):
        _id(source.get(key),key)
    _hash(source.get("source_snapshot_sha256"),"combo_source_sha256")
    cases=source.get("cases")
    combos=source.get("combinations")
    roles=source.get("consumer_roles")
    if not (isinstance(cases,list) and cases and isinstance(combos,list)
            and isinstance(roles,list)):
        raise CompilationRejected("COMBO_CASES_COMBOS_ROLES_LIST_REQUIRED")
    caseset=set()
    for case in cases:
        if not isinstance(case,dict):
            raise CompilationRejected("CASE_RECORD_INVALID")
        k=_id(case.get("case_id"),"case_id")
        _id(case.get("source_case_guid"),"source_case_guid")
        if k in caseset:
            raise CompilationRejected("DUPLICATE_CASE_ID")
        caseset.add(k)
    combomap={}
    for combo in combos:
        if not isinstance(combo,dict):
            raise CompilationRejected("COMBO_RECORD_INVALID")
        cid=_id(combo.get("combo_id"),"combo_id")
        operator=combo.get("operator")
        terms=combo.get("terms")
        if cid in combomap or cid in caseset:
            raise CompilationRejected("DUPLICATE_COMBO_OR_CASE_ID")
        if operator not in COMBO_OPERATORS or not isinstance(terms,list) or not terms:
            raise CompilationRejected("INVALID_COMBO_OPERATOR_OR_TERMS")
        seen=set()
        for term in terms:
            if not isinstance(term,dict):
                raise CompilationRejected("INVALID_COMBO_TERM")
            typ=term.get("ref_type")
            ref=_id(term.get("ref_id"),"term_ref_id")
            if typ not in ("CASE","COMBO") or (typ,ref) in seen:
                raise CompilationRejected("DUPLICATE_OR_UNTYPED_COMBO_TERM")
            _number(term.get("factor"),"term_factor")
            seen.add((typ,ref))
        combomap[cid]={"operator":operator,"terms":terms}
    # Verify referential closure, including typed nested operators, then
    # reject cyclic definitions. No loose names or guessed case roles.
    for cid,c in combomap.items():
        for term in c["terms"]:
            typ,ref=term["ref_type"],term["ref_id"]
            if (typ=="CASE" and ref not in caseset) or (
                    typ=="COMBO" and ref not in combomap):
                raise CompilationRejected("UNKNOWN_CASE_OR_NESTED_COMBO_REFERENCE")
    visiting=set();visited=set()
    def dfs(cid:str):
        if cid in visiting:
            raise CompilationRejected("CYCLIC_NESTED_COMBO_DEFINITION")
        if cid in visited:
            return
        visiting.add(cid)
        for term in combomap[cid]["terms"]:
            if term["ref_type"]=="COMBO":
                dfs(term["ref_id"])
        visiting.remove(cid)
        visited.add(cid)
    for cid in sorted(combomap):
        dfs(cid)
    declared_roles=set()
    for role in roles:
        if not isinstance(role,dict):
            raise CompilationRejected("INVALID_COMBO_CONSUMER_ROLE")
        name=_id(role.get("role_id"),"role_id")
        cref=_id(role.get("source_ref_id"),"source_ref_id")
        typ=role.get("source_ref_type")
        if name in declared_roles:
            raise CompilationRejected("DUPLICATE_COMBO_CONSUMER_ROLE")
        declared_roles.add(name)
        if typ not in ("CASE","COMBO"):
            raise CompilationRejected("UNRECOGNIZED_CONSUMER_SOURCE_TYPE")
        if typ=="CASE" and cref not in caseset:
            raise CompilationRejected("CONSUMER_ROLE_CASE_NOT_IN_BOOK")
        if typ=="COMBO" and cref not in combomap:
            raise CompilationRejected("CONSUMER_ROLE_COMBO_NOT_IN_BOOK")
        if type(role.get("requires_concurrent_vector")) is not bool:
            raise CompilationRejected("CONCURRENCE_INTENT_NOT_EXPLICIT")
        if role["requires_concurrent_vector"] and typ=="COMBO":
            # A nested SUM may contain an envelope; check every nested node.
            to_visit=[cref];seen_combo=set()
            while to_visit:
                current=to_visit.pop()
                if current in seen_combo:
                    continue
                seen_combo.add(current)
                if combomap[current]["operator"] != SAFE_CONCURRENT_OPERATOR:
                    raise CompilationRejected("NONCONCURRENT_OPERATOR_FOR_VECTOR_ROLE")
                to_visit.extend(t["ref_id"] for t in
                                combomap[current]["terms"] if t["ref_type"]=="COMBO")
    return {
        "schema":"tbdy.next.vs05.combo-book-candidate-review.v1",
        "status":"DEFINITION_GRAPH_OBSERVED_UNAPPROVED",
        "combo_book_sha256":sha256(canonical_json(source)).hexdigest(),
        "case_count":len(caseset),
        "combination_count":len(combomap),
        "consumer_role_count":len(roles),
        "nested_definition_acyclic":True,
        "complete_case_combo_population_proven":False,
        "combo_roles_approved":False,
        "same_analysis_generation_proven":False,
        "formal_compliance":"NOT_PROVEN",
    }


def compile_limited_source_candidates(
    compiler:RegulatoryCompiler,
    profile:Mapping[str,Any],
    combo_book:Mapping[str,Any],
)->dict[str,Any]:
    """Compile only directional BASE_SHEAR and per-upper-story STORY_DRIFT.

    A model census self-assertion does not authorize real design execution.
    The explicit candidate upper-story denominator is frozen in the
    downstream D1 plan and accounted by FCR. No other DAG nodes executed.
    """
    a=review_model_profile_candidate(profile)
    b=review_combo_book_candidate(combo_book)
    if a["source_snapshot_sha256"]!=combo_book["source_snapshot_sha256"]:
        raise CompilationRejected("PROFILE_COMBO_DIFFERENT_SOURCE_SNAPSHOTS")
    expected=[]
    for direction in ("X","Y"):
        expected.append({
            "check_instance_id":"BASE_SHEAR:"+direction,
            "node_id":"BASE_SHEAR","subject_id":direction,
            "grain":"GLOBAL_DIRECTION",
        })
        for story in a["candidate_upper_story_ids"]:
            expected.append({
                "check_instance_id":"STORY_DRIFT:"+direction+":"+story,
                "node_id":"STORY_DRIFT","subject_id":direction+":"+story,
                "grain":"STORY_DIRECTION",
            })
    profile_declaration={
        "schema":"tbdy.next.vs05.model_profile.candidate.v1",
        "profile_id":profile["model_id"],
        "version":profile["version"],
        "source_model_sha256":a["source_snapshot_sha256"],
        "profile_v2_sha256":a["model_profile_sha256"],
        "approval_reference":"NOT_APPROVED",
    }
    book_declaration={
        "schema":"tbdy.next.vs05.combo_book.candidate.v1",
        "book_id":combo_book["book_id"],
        "version":combo_book["version"],
        "combo_definition_sha256":b["combo_book_sha256"],
        "approval_reference":"NOT_APPROVED",
    }
    plan=compiler.compile_candidate(
        model_profile=profile_declaration,
        combo_book=book_declaration,
        expected_instances=expected,
    )
    return {
        "schema":"tbdy.next.vs05.limited-source-candidate-scope.v1",
        "status":"UNAPPROVED_CANDIDATE_PHYSICAL_SCOPE",
        "plan":plan,
        "profile_review":a,
        "combo_review":b,
        "expected_instance_count":len(expected),
        "whole_building_expected_check_census_proven":False,
        "engineering_release":"NOT_READY",
        "formal_compliance":"NOT_PROVEN",
        "note":"Only BASE_SHEAR and STORY_DRIFT candidates. No full 94-node runtime.",
    }
