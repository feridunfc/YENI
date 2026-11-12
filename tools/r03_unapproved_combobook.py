"""R03 candidate-only ETABS case/combination dependency graph from pinned source.

Case labels (e.g. RSX, Cap) are *never* interpreted as regulatory design roles.
The graph detects incomplete references and cycles, but grants no design authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys

from r01_verify_archived_bank import R01Error, read_bank

SCHEMA = "tbdy.next.r03-unapproved-combobook.v1"
OPERATORS = {0: "LINEAR_ADD", 1: "ENVELOPE"}
CASE_TYPES = {1: "LINEAR_STATIC", 3: "MODAL", 4: "RESPONSE_SPECTRUM"}
NEEDED_ROLES = ("G", "Q", "S", "H", "EX", "EY", "EZ")


def _name(value, reason):
    if not isinstance(value, str) or not value:
        raise R01Error("INVALID_SOURCE_NAME:" + reason)
    return value


def _fraction(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise R01Error("NONFINITE_COMBINATION_FACTOR")
    return str(Fraction(str(value)))


def build_book(bank: dict) -> dict:
    cases = bank.get("case_definitions", [])
    combinations = bank.get("combination_definitions", [])
    if not isinstance(cases, list) or not isinstance(combinations, list):
        raise R01Error("NATIVE_CASE_OR_COMBO_CATALOG_MISSING")
    case_index = {}
    combo_index = {}
    for c in cases:
        name = _name(c.get("name"), "case")
        if name in case_index or c.get("status") != "OBSERVED" or type(c.get("case_type")) is not int:
            raise R01Error("DUPLICATE_OR_UNOBSERVED_CASE")
        case_index[name] = c
    for c in combinations:
        name = _name(c.get("name"), "combination")
        if name in combo_index or c.get("status") != "OBSERVED" or type(c.get("operator")) is not int:
            raise R01Error("DUPLICATE_OR_UNOBSERVED_COMBINATION")
        combo_index[name] = c
    if case_index.keys() & combo_index.keys():
        raise R01Error("CASE_COMBINATION_ID_COLLISION")
    if len(case_index) != bank.get("defined_case_count") or len(combo_index) != bank.get("defined_combination_count"):
        raise R01Error("CASE_COMBINATION_DENOMINATOR_CONFLICT")
    edges = {}
    combos = []
    for name, c in combo_index.items():
        op = OPERATORS.get(c["operator"], "UNSUPPORTED_OPERATOR")
        terms = c.get("terms")
        if not isinstance(terms, list) or not terms:
            raise R01Error("COMBINATION_TERMS_EMPTY:" + name)
        normalized = []
        refs = []
        for t in terms:
            k, target = t.get("type"), _name(t.get("name"), "combination term")
            if k == 0:
                if target not in case_index:
                    raise R01Error("UNKNOWN_CASE_REFERENCE:" + name + ":" + target)
                dependency = "CASE"
            elif k == 1:
                if target not in combo_index:
                    raise R01Error("UNKNOWN_COMBINATION_REFERENCE:" + name + ":" + target)
                refs.append(target)
                dependency = "COMBINATION"
            else:
                raise R01Error("UNKNOWN_REFERENCE_TYPE:" + name)
            normalized.append({"reference_kind": dependency, "source_name": target,
                               "exact_factor": _fraction(t.get("factor"))})
        edges[name] = refs
        combos.append({"source_name": name, "native_operator": c["operator"],
                       "operator": op, "terms": normalized,
                       "execution_authority": "DENIED",
                       "formal_compliance": "NOT_PROVEN"})
    marks = {}
    def visit(key):
        current = marks.get(key)
        if current == "ACTIVE":
            raise R01Error("COMBINATION_CYCLE:" + key)
        if current == "CLOSED":
            return
        marks[key] = "ACTIVE"
        for parent in edges[key]:
            visit(parent)
        marks[key] = "CLOSED"
    for key in edges:
        visit(key)
    case_items = [{"source_name": name, "native_case_type": c["case_type"],
                   "observation_type": CASE_TYPES.get(c["case_type"], "OTHER"),
                   "design_role": None, "role_authority": "UNASSIGNED"}
                  for name, c in case_index.items()]
    counts = Counter(c["operator"] for c in combos)
    # Structural labels may look normative. This report intentionally has no guessed roles.
    book = {"schema": SCHEMA,
            "source_run_id": bank["run_id"],
            "source_archive_sha256": bank["source_archive_sha256"],
            "source_bank_result_sha256": bank["result_sha256"],
            "case_count": len(case_items), "combination_count": len(combos),
            "operators": dict(counts),
            "cases": case_items, "combinations": combos,
            "normative_load_roles": {role: {"source_name": None, "status": "NOT_PROVEN"}
                                     for role in NEEDED_ROLES},
            "model_profile": {"SDS": None, "R": None, "D": None, "I": None,
                              "analysis_generation_qualified": False,
                              "response_spectrum_scale_qualified": False,
                              "source_role_authority": "DENIED"},
            "source_dependency_graph": "ACYCLIC_NATIVE_DEFINITIONS",
            "execution_authority": "DENIED",
            "formal_compliance": "NOT_PROVEN",
            "engineering_release": "NOT_READY"}
    raw = json.dumps(book, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    book["candidate_graph_sha256"] = hashlib.sha256(raw).hexdigest()
    return book


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] /
                        "config/r01_archived_sources.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.manifest.read_text(encoding="utf-8"))
        bank = read_bank(args.bank, config["bank_zip_sha256"])
        if bank.get("source_archive_sha256") != config["native_archive_sha256"]:
            raise R01Error("UNTRUSTED_SOURCE_ARCHIVE_ID")
        book = build_book(bank)
        rendered = json.dumps(book, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise R01Error("OUTPUT_EXISTS")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"schema": SCHEMA, "case_count": book["case_count"],
                          "combination_count": book["combination_count"],
                          "candidate_graph_sha256": book["candidate_graph_sha256"],
                          "engineering_release": "NOT_READY"}, indent=2))
        return 0
    except (R01Error, ValueError, KeyError, OSError, RecursionError) as exc:
        print(json.dumps({"r03_status": "REJECTED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
