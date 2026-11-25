"""Strict, source-bound calculation assumptions for the existing TS 500 owner.

This module validates and resolves inputs; it owns no structural formulas.
Adoption changes a calculation scenario, never engineering acceptance or the
verification state of an external solver log or project decision.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import re
from typing import Any


SCHEMA = "tbdy.next.second-order-basis.v1"
ROLE = "ADOPTED_CALCULATION_ASSUMPTIONS"
NONSWAY_POLICY = "PIPELINE_TBDY_PLUS_LOCAL_NONSWAY"
SWAY_POLICY = "TS500_SWAY_WITH_TBDY_UNITY"
ACCEPTANCE_GATE = "ADOPTED_SECOND_ORDER_BASIS_ENGINEERING_ACCEPTANCE_PENDING"
AXIAL_IDEALIZATION_METHOD = "SELF_WEIGHT_NMAX"
AXIAL_IDEALIZATION_APPLICABILITY = "ADOPTED_PRISMATIC_SELF_WEIGHT_NMAX_IDEALIZATION"
AXIAL_IDEALIZATION_GATE = "ADOPTED_AXIAL_IDEALIZATION_ENGINEERING_ACCEPTANCE_PENDING"
AXIAL_IDEALIZATION_APPLIED = "ADOPTED_AXIAL_IDEALIZATION_APPLIED_NOT_PROVEN"


def _mapping(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError("SECOND_ORDER_BASIS_FIELDS_INVALID:" + label)
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("SECOND_ORDER_BASIS_TEXT_REQUIRED:" + label)
    return value.strip()


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)
    except (ValueError, OverflowError):
        valid = False
    if not valid:
        raise ValueError("SECOND_ORDER_BASIS_NUMBER_INVALID:" + label)
    return float(value)


def normalize_second_order_basis(raw: Any, *, source_data_sha256: str) -> dict[str, Any]:
    """Return a deterministic supported v1 document; never infer missing inputs.

    ``source_data_sha256`` is the digest of design_scenario._source_data(payload),
    which excludes scenario policies, including this document. Source binding
    prevents reuse after a changed capture. References identify externally
    adopted decisions; their text/hash does not make those decisions verified.
    """
    top = _mapping(raw, {"schema", "basis_id", "basis_role", "engineering_approval", "source_data_sha256",
                         "source_analysis_order", "source_order_reference", "global_factor_policy",
                         "global_factor_reference", "members"}, "document")
    if top["schema"] != SCHEMA or top["basis_role"] != ROLE or top["engineering_approval"] != "NOT_GRANTED":
        raise ValueError("SECOND_ORDER_BASIS_SCHEMA_ROLE_OR_APPROVAL_INVALID")
    if (not isinstance(source_data_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_data_sha256)
            or top["source_data_sha256"] != source_data_sha256):
        raise ValueError("SECOND_ORDER_BASIS_SOURCE_MISMATCH")
    if top["source_analysis_order"] != "FIRST_ORDER":
        raise ValueError("SECOND_ORDER_BASIS_FIRST_ORDER_REQUIRED_NO_DOUBLE_APPLICATION")
    policy = top["global_factor_policy"]
    if not isinstance(policy, str) or policy not in {NONSWAY_POLICY, SWAY_POLICY}:
        raise ValueError("SECOND_ORDER_BASIS_GLOBAL_FACTOR_POLICY_UNSUPPORTED")
    raw_members = top["members"]
    if not isinstance(raw_members, Mapping) or not raw_members:
        raise ValueError("SECOND_ORDER_BASIS_MEMBER_SCOPE_REQUIRED")
    members: dict[str, Any] = {}
    for raw_uid, raw_member in raw_members.items():
        uid = _text(raw_uid, "member_id")
        if uid != raw_uid or uid in members:
            raise ValueError("SECOND_ORDER_BASIS_MEMBER_ID_INVALID")
        member_fields = {"combinations", "applicability", "decision_reference", "axes"}
        if isinstance(raw_member, Mapping) and "axial_idealization" in raw_member:
            member_fields.add("axial_idealization")
        member = _mapping(raw_member, member_fields, uid)
        names = member["combinations"]
        if (not isinstance(names, list) or not names
                or any(not isinstance(n, str) or not n or n.strip() != n for n in names)
                or len(set(names)) != len(names)):
            raise ValueError("SECOND_ORDER_BASIS_COMBINATION_SCOPE_INVALID:" + uid)
        idealization = None
        if "axial_idealization" in member:
            idealization = _mapping(member["axial_idealization"],
                                   {"method", "combinations", "decision_reference"}, uid + ":axial_idealization")
            idealized_names = idealization["combinations"]
            if (member["applicability"] != AXIAL_IDEALIZATION_APPLICABILITY
                    or idealization["method"] != AXIAL_IDEALIZATION_METHOD
                    or not isinstance(idealized_names, list) or not idealized_names
                    or any(not isinstance(name, str) or name not in names for name in idealized_names)
                    or len(set(idealized_names)) != len(idealized_names)):
                raise ValueError("SECOND_ORDER_AXIAL_IDEALIZATION_INVALID:" + uid)
            idealization = {"method": AXIAL_IDEALIZATION_METHOD, "combinations": sorted(idealized_names),
                            "decision_reference": _text(idealization["decision_reference"], "axial_idealization_reference")}
        elif member["applicability"] != "TS500_7_6_2_CONSTANT_SECTION_AND_AXIAL_FORCE":
            raise ValueError("SECOND_ORDER_BASIS_APPLICABILITY_UNSUPPORTED:" + uid)
        raw_axes = _mapping(member["axes"], {"M2", "M3"}, uid + ":axes")
        axes = {}
        for axis in ("M2", "M3"):
            fields = {"k", "creep_ratio_rm", "ei_method", "sway", "cm_policy",
                      "eq729_length_reading", "decision_reference", "story_aggregates"}
            if isinstance(raw_axes[axis], Mapping) and "k_source" in raw_axes[axis]:
                fields.add("k_source")
            a = _mapping(raw_axes[axis], fields, uid + ":" + axis)
            k = _number(a["k"], "k", positive=True)
            rm = _number(a["creep_ratio_rm"], "creep_ratio_rm")
            if not 0 <= rm <= 1:
                raise ValueError("SECOND_ORDER_BASIS_CREEP_RATIO_OUTSIDE_ZERO_ONE")
            if not isinstance(a["ei_method"], str) or a["ei_method"] not in {"TS500_7_20", "TS500_7_21"}:
                raise ValueError("SECOND_ORDER_BASIS_EI_METHOD_UNSUPPORTED")
            sway = a["sway"]
            if not isinstance(sway, str) or sway not in {"SWAY_PREVENTED", "SWAY_PERMITTED"}:
                raise ValueError("SECOND_ORDER_BASIS_SWAY_CLASS_REQUIRED")
            if policy == NONSWAY_POLICY and sway != "SWAY_PREVENTED":
                raise ValueError("SECOND_ORDER_BASIS_GLOBAL_LOCAL_OVERLAP_UNSUPPORTED")
            if (not isinstance(a["cm_policy"], str) or a["cm_policy"] not in {"UNITY", "SIGNED_END_RATIO"}
                    or (sway == "SWAY_PERMITTED" and a["cm_policy"] != "UNITY")):
                raise ValueError("SECOND_ORDER_BASIS_CM_POLICY_UNSUPPORTED")
            if idealization is not None and a["cm_policy"] != "UNITY":
                raise ValueError("SECOND_ORDER_AXIAL_IDEALIZATION_UNITY_CM_REQUIRED:" + uid + ":" + axis)
            reading = a["eq729_length_reading"]
            required_readings = {"FREE_LENGTH", "EFFECTIVE_LENGTH"} if sway == "SWAY_PERMITTED" else {"NOT_APPLICABLE"}
            if not isinstance(reading, str) or reading not in required_readings:
                raise ValueError("SECOND_ORDER_BASIS_EQ729_READING_REQUIRED")
            story = a["story_aggregates"]
            if not isinstance(story, Mapping) or set(story) != (set(names) if sway == "SWAY_PERMITTED" else set()):
                raise ValueError("SECOND_ORDER_BASIS_STORY_COMBINATION_SCOPE_INVALID:" + uid + ":" + axis)
            aggregates = {}
            for name in sorted(story):
                s = _mapping(story[name], {"nd_kn", "nk_kn", "reference"}, "story:" + name)
                aggregates[name] = {"nd_kn": _number(s["nd_kn"], "story_nd_kn", positive=True),
                                    "nk_kn": _number(s["nk_kn"], "story_nk_kn", positive=True),
                                    "reference": _text(s["reference"], "story_reference")}
            axes[axis] = {"k": k, "creep_ratio_rm": rm, "ei_method": a["ei_method"], "sway": sway,
                          "cm_policy": a["cm_policy"], "eq729_length_reading": reading,
                          "decision_reference": _text(a["decision_reference"], "axis_decision_reference"),
                          "story_aggregates": aggregates}
            if "k_source" in a:
                k_source = _mapping(a["k_source"], {"method", "section"}, "k_source")
                if (k_source["method"] not in ("FRAME_END_RATIOS", "LOWER_SUPPORT_SWAY_ENVELOPE") or not isinstance(k_source["section"], str)
                        or k_source["section"] not in {"alpha_web", "alpha_flange_comparison"}):
                    raise ValueError("SECOND_ORDER_BASIS_K_SOURCE_UNSUPPORTED")
                axes[axis]["k_source"] = dict(k_source)
        members[uid] = {"combinations": sorted(names), "applicability": member["applicability"],
                        "decision_reference": _text(member["decision_reference"], "member_decision_reference"), "axes": axes}
        if idealization is not None:
            members[uid]["axial_idealization"] = idealization
    return {"schema": SCHEMA, "basis_id": _text(top["basis_id"], "basis_id"), "basis_role": ROLE,
            "engineering_approval": "NOT_GRANTED", "source_data_sha256": source_data_sha256,
            "source_analysis_order": "FIRST_ORDER", "source_order_reference": _text(top["source_order_reference"], "source_order_reference"),
            "global_factor_policy": policy, "global_factor_reference": _text(top["global_factor_reference"], "global_factor_reference"),
            "members": {uid: members[uid] for uid in sorted(members)}}


def resolve_member_second_order_basis(source: Mapping[str, Any], uid: str,
                                     expected_combinations: Sequence[str] | set[str]) -> dict[str, Any] | None:
    """Resolve an explicitly scoped member; unlisted members remain reference-only."""
    raw = source.get("second_order_basis")
    if raw is None:
        return None
    from .design_scenario import _digest, _source_data

    document = normalize_second_order_basis(raw, source_data_sha256=_digest(_source_data(source)))
    return member_second_order_basis(document, uid, expected_combinations)


def member_second_order_basis(document: Mapping[str, Any], uid: str,
                              expected_combinations: Sequence[str] | set[str]) -> dict[str, Any] | None:
    """Resolve a member from a document already normalized at the pipeline boundary."""
    from .design_scenario import _digest

    member = document["members"].get(uid)
    if member is None:
        return None
    if not expected_combinations or set(member["combinations"]) != set(expected_combinations):
        raise ValueError("SECOND_ORDER_BASIS_REQUIRED_COMBINATION_SCOPE_MISMATCH:" + uid)
    return {**{key: value for key, value in document.items() if key != "members"}, "member_id": uid,
            "member": member, "basis_sha256": _digest(document), "member_basis_sha256": _digest(member)}
