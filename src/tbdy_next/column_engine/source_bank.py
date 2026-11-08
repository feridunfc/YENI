"""YENI-owned native column states and bounded static combination replay.

Adapts Column-Engine's R6 row/context readers and TBDY's name-blind demand
classification. Keeps every recorded station and six-component vector. The
legacy eight-way spectral sign permutations do not gain design authority here.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import math

from .native_archive import BankError, NativeArchive, digest, finite, identity
from .observed_context import _member_context

FIELDS = ("Obj", "ObjSta", "Elm", "ElmSta", "LoadCase", "StepType", "StepNum",
          "P", "V2", "V3", "T", "M2", "M3")
COMPONENTS = FIELDS[7:]
SCHEMA = "tbdy.next.column-source-bank.v1"
FORCE_SIGNATURE = ("NumberResults", *FIELDS, "pRetVal")
TYPE_SIGNATURE = ("CaseType", "SubType", "DesignType", "DesignTypeOption", "Auto", "pRetVal")
ATOL = Fraction("1e-9")  # kN / kN-m source replay, not a design tolerance
RTOL = Fraction("1e-12")


@dataclass(frozen=True, slots=True)
class NativeForceState:
    """kN-m-C native tuple, with source and analysis-element identity intact."""
    source_row_id: str
    call_id: str
    shard_sha256: str
    source_row_index: int
    values: tuple

    @property
    def station_key(self):
        return self.values[:4]  # Obj, ObjSta, Elm, ElmSta — never ObjSta alone

    @property
    def output_case(self):
        return self.values[4]

    def as_dict(self):
        return dict(zip(FIELDS, self.values)) | {"source_row_id": self.source_row_id,
            "call_id": self.call_id, "shard_sha256": self.shard_sha256,
            "source_row_index": self.source_row_index}


def _read_forces(archive, name, entry):
    if (entry.get("status") != "OBSERVED" or entry.get("exact_shape") is not True
            or entry.get("frame_name") != name):
        raise BankError("COLUMN_FORCE_NOT_OBSERVED")
    observed = archive.native("Results.FrameForce", "frame", name, FORCE_SIGNATURE)
    if observed is None:
        raise BankError("COLUMN_FORCE_CALL_MISSING")
    rowset, proof = observed
    if entry.get("call_id") != proof["call_id"] or entry.get("shard") != proof["shard_path"]:
        raise BankError("FORCE_INVENTORY_CALL_MISMATCH")
    n = rowset["NumberResults"]
    if (type(n) is not int or not 0 < n <= 200000 or n != entry.get("declared_rows")
            or any(not isinstance(rowset[k], list) or len(rowset[k]) != n for k in FIELDS)):
        raise BankError("FORCE_ARRAY_LENGTH_MISMATCH")
    states, seen, counts = [], set(), Counter()
    for i, vals in enumerate(zip(*(rowset[k] for k in FIELDS))):
        if vals[0] != name:
            raise BankError("FORCE_FRAME_ID_MISMATCH")
        for j in (0, 2, 4):
            identity(vals[j], FIELDS[j])
        if not isinstance(vals[5], str):
            raise BankError("FORCE_STEP_TYPE_INVALID")
        for j in (1, 3, 6, *range(7, 13)):
            finite(vals[j], FIELDS[j])
        if vals[1] < 0 or vals[3] < 0 or vals[:7] in seen:
            raise BankError("FORCE_STATION_NEGATIVE_OR_FULL_KEY_DUPLICATE")
        seen.add(vals[:7]); counts[vals[4]] += 1
        row_id = digest({"archive": archive.sha256, "call": proof["call_id"], "index": i, "values": vals})
        states.append(NativeForceState(row_id, proof["call_id"], proof["shard_sha256"], i, vals))
    if dict(counts) != entry.get("case_or_combination_rows"):
        raise BankError("FORCE_CASE_POPULATION_MISMATCH")
    return states, proof


def _definitions(archive):
    cases, combos = {}, {}
    if "catalogs.json" not in archive.z.namelist():
        return cases, combos
    catalogs = archive.json("catalogs.json")
    names = catalogs.get("names", {})
    for group in ("cases", "combinations"):
        if (not isinstance(names.get(group), list) or len(set(names[group])) != len(names[group])
                or catalogs.get("catalog_complete", {}).get(group) is not True):
            raise BankError("CASE_COMBO_CATALOG_INVALID")
    if set(names["cases"]) & set(names["combinations"]):
        raise BankError("CASE_COMBO_ID_COLLISION")
    for name in names["cases"]:
        item = {"name": identity(name, "case"), "status": "NOT_PROVEN", "reason": None}
        try:
            observed = archive.native("LoadCases.GetTypeOAPI_1", "case", name, TYPE_SIGNATURE)
            if observed is None:
                raise BankError("CASE_TYPE_MISSING")
            data, proof = observed
            if any(type(data[k]) is not int for k in TYPE_SIGNATURE[:-1]):
                raise BankError("CASE_TYPE_ENUM_INVALID")
            item.update(status="OBSERVED", case_type=data["CaseType"], subtype=data["SubType"],
                        design_type=data["DesignType"], source=proof)
        except (ValueError, KeyError, TypeError) as exc:
            item["reason"] = str(exc)
        cases[name] = item
    for name in names["combinations"]:
        item = {"name": identity(name, "combination"), "status": "NOT_PROVEN", "reason": None}
        try:
            op = archive.native("RespCombo.GetTypeCombo", "combination", name, ("ComboType", "pRetVal"))
            terms = archive.native("RespCombo.GetCaseList", "combination", name,
                                   ("NumberItems", "CNameType", "CName", "SF", "pRetVal"))
            if op is None or terms is None:
                raise BankError("COMBINATION_DEFINITION_MISSING")
            o, op_proof = op; t, terms_proof = terms
            n = t["NumberItems"]
            if (type(o["ComboType"]) is not int or type(n) is not int or n <= 0
                    or any(not isinstance(t[k], list) or len(t[k]) != n for k in ("CNameType", "CName", "SF"))):
                raise BankError("COMBINATION_DEFINITION_SHAPE_INVALID")
            typed = []
            for kind, ref, sf in zip(t["CNameType"], t["CName"], t["SF"]):
                if type(kind) is not int or kind not in (0, 1):
                    raise BankError("COMBINATION_REFERENCE_TYPE_INVALID")
                typed.append({"type": kind, "name": identity(ref, "constituent"), "factor": finite(sf, "factor")})
            item.update(status="OBSERVED", operator=o["ComboType"], terms=typed,
                        source={"operator": op_proof, "terms": terms_proof})
        except (ValueError, KeyError, TypeError) as exc:
            item["reason"] = str(exc)
        combos[name] = item
    return cases, combos


def _member_geometry(archive, member, states):
    """Recorded object points/offsets. No implicit TS500 free/effective length."""
    name = member["frame_name"]
    facts, missing = {}, []
    requests = {
        "points": ("FrameObj.GetPoints", ("Point1", "Point2", "pRetVal")),
        "offsets": ("FrameObj.GetEndLengthOffset", ("AutoOffset", "Length1", "Length2", "RZ", "pRetVal")),
        "releases": ("FrameObj.GetReleases", ("II", "JJ", "StartValue", "EndValue", "pRetVal")),
        "transformation": ("FrameObj.GetTransformationMatrix", ("Value", "pRetVal")),
    }
    for key, (api, fields) in requests.items():
        result = archive.native(api, "frame", name, fields)
        if result is None:
            missing.append(key)
        else:
            facts[key] = {"values": result[0], "source": result[1]}
    if "releases" in facts:
        r = facts["releases"]["values"]
        if (any(not isinstance(r[k], list) or len(r[k]) != 6 for k in ("II", "JJ", "StartValue", "EndValue"))
                or any(type(v) is not bool for k in ("II", "JJ") for v in r[k])):
            raise BankError("FRAME_RELEASES_INVALID")
        for k in ("StartValue", "EndValue"):
            for value in r[k]:
                finite(value, k)
    if "transformation" in facts:
        values = facts["transformation"]["values"]["Value"]
        if not isinstance(values, list) or len(values) != 9:
            raise BankError("FRAME_TRANSFORMATION_INVALID")
        for value in values:
            finite(value, "transformation")
        matrix = [values[i:i+3] for i in (0, 3, 6)]
        if any(abs(sum(matrix[i][k] * matrix[j][k] for k in range(3)) - (i == j)) > 1e-9
               for i in range(3) for j in range(3)):
            raise BankError("FRAME_TRANSFORMATION_NOT_ORTHONORMAL")
    points = facts.get("points", {}).get("values")
    coordinates = []
    if points:
        for side in ("Point1", "Point2"):
            point = identity(points[side], side)
            coords = archive.native("PointObj.GetCoordCartesian", "point", point, ("X", "Y", "Z", "pRetVal"))
            restraints = archive.native("PointObj.GetRestraint", "point", point, ("Value", "pRetVal"))
            if coords is None:
                missing.append("coordinate:" + point)
            else:
                coordinates.append([finite(coords[0][axis], axis) for axis in ("X", "Y", "Z")])
                facts["coordinate_" + side] = {"values": coords[0], "source": coords[1]}
            if restraints is None:
                missing.append("restraint:" + point)
            else:
                v = restraints[0]["Value"]
                if not isinstance(v, list) or len(v) != 6 or any(type(x) is not bool for x in v):
                    raise BankError("POINT_RESTRAINT_SIGNATURE_INVALID")
                facts["restraint_" + side] = {"values": restraints[0], "source": restraints[1]}
    stations = sorted({s.values[1] for s in states})
    geometry = {"native_facts": facts, "missing_native_facts": missing,
        "observed_object_stations_m": stations, "ts500_free_length_proven": False,
        "effective_length_proven": False, "joint_face_binding_proven": False}
    if len(coordinates) == 2:
        length = math.dist(*coordinates)
        if not math.isfinite(length) or length <= 0:
            raise BankError("COLUMN_OBJECT_LENGTH_INVALID")
        geometry.update(object_i_j_length_m=length, point_i_xyz_m=coordinates[0], point_j_xyz_m=coordinates[1])
        if stations and (stations[0] < -1e-7 or stations[-1] > length + 1e-7):
            raise BankError("FORCE_STATION_OUTSIDE_OBJECT_LENGTH")
        if "offsets" in facts:
            off = facts["offsets"]["values"]
            l1, l2, rz = (finite(off[k], k) for k in ("Length1", "Length2", "RZ"))
            if type(off["AutoOffset"]) is not bool or min(l1, l2) < 0 or l1 + l2 >= length or not 0 <= rz <= 1:
                raise BankError("END_OFFSETS_INVALID")
            geometry.update(offset_i_m=l1, offset_j_m=l2,
                observed_output_face_span_m=length - l1 - l2,
                first_station_matches_i_offset=bool(stations) and abs(stations[0] - l1) <= 1e-7,
                last_station_matches_j_offset=bool(stations) and abs(stations[-1] - (length - l2)) <= 1e-7,
                last_station_is_joint_j=bool(stations) and abs(stations[-1] - length) <= 1e-7)
    return geometry


def replay_static_combinations(states, cases, combos, selected, *, capture_context_observed=True):
    """Six original signed components, at the exact same element/station/step.

    This is a source-arithmetic check. RS/Envelope/permuted component extrema
    never become simultaneous design states. Every observed station remains in
    the expected population, including interfaces between analysis elements.
    """
    locations = defaultdict(set)
    index = defaultdict(list)
    for row in states:
        locations[row.values[0]].add(row.station_key)
        index[(row.station_key, row.output_case)].append(row)
    summaries, comparisons = [], []
    for name, definition in combos.items():
        summary = {"combination": name, "status": "NOT_EVALUATED", "reason": None,
            "expected_rows": 0, "matched_rows": 0, "mismatched_rows": 0, "unresolved_rows": 0,
            "scalar_comparisons": 0, "maximum_absolute_difference": 0.0,
            "maximum_scaled_difference": 0.0, "normative_acceptance": "NOT_PROVEN"}
        terms = definition.get("terms", [])
        if not capture_context_observed:
            summary["reason"] = "CAPTURE_CONTEXT_NOT_STABLE"
        elif definition["status"] != "OBSERVED":
            summary["reason"] = "COMBINATION_DEFINITION_UNRESOLVED"
        elif definition["operator"] != 0:
            summary["reason"] = "NON_LINEAR_ADD_OPERATOR_OUTSIDE_REPLAY_SCOPE"
        elif len({t["name"] for t in terms}) != len(terms):
            summary["reason"] = "REPEATED_REFERENCE_UNSUPPORTED_BY_ADAPTER"
        elif any(t["type"] != 0 for t in terms):
            summary["reason"] = "NESTED_COMBINATION_REQUIRES_SEPARATE_BINDING"
        elif any(cases.get(t["name"], {}).get("status") != "OBSERVED" for t in terms):
            summary["reason"] = "CONSTITUENT_CASE_TYPE_UNRESOLVED"
        elif any(cases[t["name"]]["case_type"] != 1 for t in terms):
            summary["reason"] = "SPECTRAL_OR_OTHER_NONSTATIC_CASE_NOT_CONCURRENT_DESIGN_VECTOR"
        else:
            for member in selected:
                population = sorted(locations.get(member, ())) or [(member, None, None, None)]
                for key in population:
                    summary["expected_rows"] += 1
                    item = {"member_id": member, "combination": name,
                        "object_station_m": key[1], "analysis_element_id": key[2],
                        "element_station_m": key[3], "status": "NOT_PROVEN", "reason": None}
                    try:
                        observed = index.get((key, name), ())
                        sources = [index.get((key, t["name"]), ()) for t in terms]
                        if len(observed) != 1 or any(len(rows) != 1 for rows in sources):
                            raise BankError("EXACT_STATION_CASE_ROW_MISSING_OR_AMBIGUOUS")
                        actual = observed[0]
                        if (actual.values[5] != "Single Value" or
                                any(rows[0].values[5:7] != actual.values[5:7] for rows in sources)):
                            raise BankError("STATIC_STEP_IDENTITY_NOT_SINGLE_AND_EQUAL")
                        calculated, differences, matches, scaled = [], [], [], []
                        for j in range(7, 13):
                            value = sum((Fraction(str(t["factor"])) * Fraction(str(rows[0].values[j]))
                                         for t, rows in zip(terms, sources)), Fraction(0))
                            observed_value = Fraction(str(actual.values[j]))
                            delta = abs(value - observed_value)
                            calculated.append(float(value)); differences.append(float(delta))
                            matches.append(delta <= ATOL + RTOL * max(abs(value), abs(observed_value)))
                            scaled.append(float(delta / max(Fraction(1), abs(value), abs(observed_value))))
                        item.update(status="NUMERICAL_MATCH" if all(matches) else "NUMERICAL_MISMATCH",
                            source_row_id=actual.source_row_id,
                            constituent_row_ids=[r[0].source_row_id for r in sources],
                            calculated=dict(zip(COMPONENTS, calculated)),
                            observed=dict(zip(COMPONENTS, actual.values[7:])),
                            absolute_differences=dict(zip(COMPONENTS, differences)))
                        summary["scalar_comparisons"] += 6
                        summary["matched_rows" if all(matches) else "mismatched_rows"] += 1
                        summary["maximum_absolute_difference"] = max(summary["maximum_absolute_difference"], *differences)
                        summary["maximum_scaled_difference"] = max(summary["maximum_scaled_difference"], *scaled)
                    except (ValueError, KeyError, TypeError, OverflowError) as exc:
                        item["reason"] = str(exc); summary["unresolved_rows"] += 1
                    comparisons.append(item)
            summary["status"] = ("NUMERICAL_MISMATCH" if summary["mismatched_rows"] else
                "PARTIAL" if summary["unresolved_rows"] else "NUMERICAL_MATCH")
        summaries.append(summary)
    return {"schema": "tbdy.next.column-static-replay.v1", "combinations": summaries,
        "items": comparisons, "absolute_tolerance_native": str(float(ATOL)),
        "relative_tolerance": str(float(RTOL)), "components": list(COMPONENTS),
        "matched_rows": sum(s["matched_rows"] for s in summaries),
        "scalar_comparisons": sum(s["scalar_comparisons"] for s in summaries),
        "maximum_absolute_difference": max((s["maximum_absolute_difference"] for s in summaries), default=0.0),
        "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}


def recover_column_bank(raw: bytes) -> dict:
    archive = NativeArchive(raw)
    try:
        inventories = archive.jsonlines("force-inventory.jsonl")
        by_name = defaultdict(list)
        for entry in inventories:
            by_name[entry.get("frame_name")].append(entry)
        cases, combos = _definitions(archive)
        states, members = [], []
        for name in archive.selected:
            member = {"frame_name": name, "force_status": "NOT_PROVEN", "force_rows": 0,
                      "analysis_elements": [], "output_cases": [], "reason_codes": []}
            rows = []
            try:
                entries = by_name[name]
                if len(entries) != 1:
                    raise BankError("FORCE_INVENTORY_MISSING_OR_DUPLICATED")
                rows, proof = _read_forces(archive, name, entries[0])
                if len(states) + len(rows) > 500000:
                    raise BankError("FORCE_BANK_ROW_LIMIT")
                states.extend(rows)
                member.update(force_status="OBSERVED_NATIVE_TUPLES", force_rows=len(rows), force_source=proof,
                    analysis_elements=sorted({r.values[2] for r in rows}),
                    output_cases=sorted({r.output_case for r in rows}),
                    requested_names_without_rows=list(entries[0].get("requested_names_without_rows", [])))
            except (ValueError, KeyError, TypeError) as exc:
                member["reason_codes"].append(str(exc))
            try:
                member["context"] = _member_context(archive.z, archive.manifest, archive.index, name)
                member["station_geometry"] = _member_geometry(archive, member, rows)
            except (ValueError, KeyError, TypeError) as exc:
                member["reason_codes"].append(str(exc))
            members.append(member)
        if len(states) > 500000:
            raise BankError("FORCE_BANK_ROW_LIMIT")
        labels = sorted({r.output_case for r in states})
        coverage = []
        for label in sorted(set(cases) | set(combos) | set(labels)):
            counts = Counter(r.values[0] for r in states if r.output_case == label)
            coverage.append({"name": label, "kind": "COMBINATION" if label in combos else "CASE" if label in cases else "UNCLASSIFIED",
                "case_type": cases.get(label, {}).get("case_type"), "operator": combos.get(label, {}).get("operator"),
                "row_count": sum(counts.values()), "members_with_rows": len(counts),
                "expected_members": len(archive.selected), "missing_members": sorted(set(archive.selected) - set(counts)),
                "step_types": sorted({r.values[5] for r in states if r.output_case == label}),
                "step_numbers": sorted({r.values[6] for r in states if r.output_case == label})})
        full_summary = archive.json("collector-summary.json") if archive.subset is None else None
        capture_context = bool(full_summary and full_summary.get("identity_unchanged") is True
            and full_summary.get("restoration_status") == "VERIFIED"
            and full_summary.get("targeted_capture_attempts_complete") is True
            and full_summary.get("error") is None
            and full_summary.get("model_definitions_modified") is False
            and full_summary.get("analysis_rerun_attempted") is False)
        replay = replay_static_combinations(states, cases, combos, archive.selected,
                                            capture_context_observed=capture_context)
        context_coverage = {
            "section_geometry": sum(bool(m.get("context", {}).get("geometry")) for m in members),
            "concrete_and_steel": sum(all(k in (m.get("context", {}).get("material") or {})
                                          for k in ("fc_MPa", "fy_MPa")) for m in members),
            "model_rebar_settings": sum(bool(m.get("context", {}).get("rebar_configuration")) for m in members),
            "complete_station_geometry": sum("station_geometry" in m and
                not m["station_geometry"]["missing_native_facts"] for m in members),
            "expected_members": len(members),
        }
        gaps = [
            {"topic": "CE-02 Tasarım kuvveti", "available": f"{len(states)} native altı bileşenli satır; tanımlı {len(combos)} birleşim", "remaining": "Tasarım birleşimi seçimi, spektral işaret/eşzamanlılık esası ve analiz nesli"},
            {"topic": "CE-04 İkinci mertebe", "available": f"{context_coverage['complete_station_geometry']}/{len(members)} kolon: geometri, matris, releases, offsets ve mesnetler", "remaining": "TS500 serbest/etkili boy, k/EI, ötelenebilirlik ve P–Δ/P–δ politikası"},
            {"topic": "CE-05 PMM ve boyuna donatı", "available": f"Kesit {context_coverage['section_geometry']}/{len(members)}, beton+çelik {context_coverage['concrete_and_steel']}/{len(members)}, model donatı ayarı {context_coverage['model_rebar_settings']}/{len(members)}", "remaining": "Gerçek veya açıkça tasarlanmış çubuk kafesi; güvenilir tasarım talebi ve yakınsama"},
            {"topic": "CE-06 Kesme ve sargı", "available": "Kuvveti gözlenmiş kolonların V2/V3 bileşenleri; varsa model donatı ayarları", "remaining": "Onaylı uç kapasiteleri, kapasite kesmesi ve fiziksel etriye/çiroz topolojisi"},
            {"topic": "CE-03 / CE-07 Kat ve birleşim", "available": "Komşu eleman ve perde/pier verileri bu bankada tasarım girdisi olarak bağlanmadı", "remaining": "Tam üye/birleşim nüfusu, aynı fiziksel kesit, kat φ ve SCWB kapasite bağlantısı"},
        ]
        result = {"schema": SCHEMA, "source_archive_sha256": archive.sha256,
            "source_kind": "D7B13_SUBSET" if archive.subset else "FULL_NATIVE_ARCHIVE",
            "parent_archive_sha256_claim": archive.subset.get("parent_archive_sha256") if archive.subset else None,
            "parent_archive_bytes_verified": archive.subset is None,
            "verified_archive_members": archive.verified_member_count, "capture_context_observed": capture_context,
            "selected_column_count": len(archive.selected), "observed_column_count": sum(m["force_rows"] > 0 for m in members),
            "analysis_element_count": len({r.values[2] for r in states}), "force_row_count": len(states),
            "recorded_output_count": len(labels), "defined_case_count": len(cases), "defined_combination_count": len(combos),
            "all_building_columns_proven": False, "force_fields": list(FIELDS),
            "force_units": {k: "kN" if k in ("P", "V2", "V3") else "kN-m" for k in COMPONENTS},
            "station_unit": "m", "native_axial_sign_unchanged": True,
            "members": members, "native_context_coverage": context_coverage,
            "case_definitions": list(cases.values()), "combination_definitions": list(combos.values()),
            "case_coverage": coverage, "force_states": [r.as_dict() for r in states], "static_replay": replay,
            "engineering_gaps": gaps, "source_mode": "OFFLINE_RECORDED_ETABS",
            "analysis_generation_proven": False, "design_demand_authority": "DENIED",
            "formal_compliance": "NOT_PROVEN", "engineering_release": "NOT_READY"}
        result["result_sha256"] = digest(result)
        return result
    finally:
        archive.close()
