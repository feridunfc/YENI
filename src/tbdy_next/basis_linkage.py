"""VS04-F observed ETABS basis binding, NOT normative authorization.

Compiles typed local evidence from the one captured 15-table VS04-E probe.
No COM, no ETABS mutation, no model generation proof, no implicit code PASS.

ETABS database rows are encoded as strings, and continuation records use
the literal string "None". Each contractual binding is exact-name and
exact-unit; table names discovered by keywords are NOT themselves authority.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .basis_probe import review_basis_probe

STORY = "Story Definitions"
BASE_STORY = "Tower and Base Story Definitions"
STORY_MASS = "Mass Summary by Story"
GROUP_MASS = "Mass Summary by Group"
JOINT_MASS = "Assembled Joint Masses"
DIAPH_MASS = "Mass Summary by Diaphragm"
MASS_SOURCE = "Mass Source Definition"
MODAL_RITZ = "Modal Case Definitions - Ritz"
CASE_SUMMARY = "Load Case Definitions - Summary"
SPECTRUM_CASE = "Load Case Definitions - Response Spectrum"
SPECTRUM_FUNCTION = "Functions - Response Spectrum - TSC-2018"
MODAL_DAMPING = "Load Case Definitions - Damping - Modal"
SPECTRUM_MODAL_INFO = "Response Spectrum Modal Info"
COMBO = "Load Combination Definitions"


def _number(value: Any, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or value in ("None", ""):
        raise ValueError("MISSING_NUMERIC_LITERAL")
    try:
        n = Decimal(value)
    except InvalidOperation:
        raise ValueError("UNPARSABLE_NUMERIC_LITERAL") from None
    if not n.is_finite() or (positive and n <= 0):
        raise ValueError("NONFINITE_OR_NONPOSITIVE_VALUE")
    return n


def _rounding_bound(*literals: Any) -> Decimal:
    """Round-to-nearest half-quanta sum for reported decimal masses."""
    bounds = []
    for text in literals:
        value = _number(text)
        bounds.append(Decimal(1).scaleb(value.as_tuple().exponent) / 2)
    return sum(bounds, Decimal(0))


def _close_display(actual: Decimal, expected: Decimal, *raw_values: str) -> bool:
    return abs(actual - expected) <= _rounding_bound(*raw_values)


def _get(probe: Mapping[str, Any], key: str, required: tuple[str, ...],
         units: Mapping[str, str]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    tables = probe.get("table_reads")
    if not isinstance(tables, Mapping):
        raise ValueError("BASIS_TABLE_READS_MISSING")
    record = tables.get(key)
    if not isinstance(record, Mapping) or record.get("table_key") != key:
        raise ValueError("EXACT_TABLE_NOT_CAPTURED:" + key)
    if record.get("status") != "CAPTURED":
        raise ValueError("TABLE_CAPTURE_ERROR:" + key)
    fields = record.get("fields")
    rows = record.get("rows")
    metadata = record.get("field_metadata")
    if (not isinstance(fields, list) or not isinstance(rows, list)
            or not isinstance(metadata, Mapping) or metadata.get("status") != "OK"
            or type(record.get("row_count")) is not int
            or len(rows) != record["row_count"] or not rows):
        raise ValueError("TABLE_STRUCTURE_INVALID:" + key)
    if not set(required).issubset(fields) or len(fields) != len(set(fields)):
        raise ValueError("REQUIRED_DISPLAY_FIELDS_MISSING:" + key)
    keys = metadata.get("field_keys")
    observed_units = metadata.get("units_by_field")
    if (not isinstance(keys, list) or
            len(keys) != metadata.get("field_count") or
            not set(fields).issubset(keys) or
            not isinstance(observed_units, Mapping) or
            any(observed_units.get(k) != v for k, v in units.items())):
        raise ValueError("FIELD_METADATA_OR_UNIT_MISMATCH:" + key)
    if any(not isinstance(r, dict) or set(r) != set(fields) or
           any(not isinstance(v, str) for v in r.values()) for r in rows):
        raise ValueError("SOURCE_ROW_SHAPE_INVALID:" + key)
    return rows, dict(metadata)


def _out(stage: str, *, facts: dict | None = None, reasons: list[str] | None = None,
         cautions: list[str] | None = None) -> dict:
    reasons = reasons or []
    return {
        "component": stage,
        "status": "NOT_PROVEN" if reasons else "SOURCE_CONTRACT_OBSERVED_UNAPPROVED",
        "reason_codes": reasons,
        "caution_codes": cautions or [],
        "source_facts": facts or {},
        "formal_compliance": "NOT_PROVEN",
    }


def _mass(probe: Mapping[str, Any]) -> dict:
    try:
        by_story, _ = _get(probe, STORY_MASS, ("Story","UX","UY","UZ"),
                            {"UX":"ton","UY":"ton","UZ":"ton"})
        groups, _ = _get(probe, GROUP_MASS, ("Group","MassX","MassY","MassZ"),
                          {"MassX":"ton","MassY":"ton","MassZ":"ton"})
        sources, _ = _get(probe, MASS_SOURCE,
                           ("Name","IsDefault","SourceSelf","SourceLoads",
                            "LoadPattern","Multiplier"), {})
        joints, _ = _get(probe, JOINT_MASS,
                          ("PointElm","Story","UX","UY","UZ"),
                          {"UX":"ton","UY":"ton","UZ":"ton"})
        diaph, _ = _get(probe, DIAPH_MASS,
                         ("Story","Diaphragm","MassX","MassY"),
                         {"MassX":"ton","MassY":"ton"})
        names=[r["Story"] for r in by_story]
        if len(set(names)) != len(names):
            raise ValueError("DUPLICATE_STORY_MASS_IDENTITY")
        all_groups=[r for r in groups if r["Group"]=="All"]
        if len(all_groups)!=1:
            raise ValueError("MASS_GROUP_ALL_NOT_UNIQUE")
        default=[r for r in sources if r["IsDefault"]=="Yes"]
        if len(default)!=1 or default[0]["Name"]!="MsSrc1":
            raise ValueError("MASS_SOURCE_DEFAULT_MISSING_OR_AMBIGUOUS")
        if default[0]["SourceSelf"]!="Yes" or default[0]["SourceLoads"]!="Yes":
            raise ValueError("MASS_SOURCE_SELF_OR_LOADS_UNAPPROVED")
        if any(r["Name"]!="MsSrc1" for r in sources):
            raise ValueError("MULTIPLE_SOURCE_ROWS_NOT_RECONCILED")
        if any(r["LoadPattern"] in ("None","") for r in sources):
            raise ValueError("MASS_SOURCE_LOAD_PATTERN_UNBOUND")
        load_factors={r["LoadPattern"]:str(_number(r["Multiplier"])) for r in sources}
        if len(load_factors)!=len(sources):
            raise ValueError("MASS_SOURCE_DUPLICATE_LOAD_PATTERN")
        joint_keys=[r["PointElm"] for r in joints]
        if any(x in ("","None") for x in joint_keys) or len(joint_keys)!=len(set(joint_keys)):
            raise ValueError("ASSEMBLED_JOINT_IDENTITY_NOT_UNIQUE")
        totals={}
        story_sums={}
        group_totals={}
        joint_sums={}
        match={}
        for axis,group_col in (("UX","MassX"),("UY","MassY")):
            story_nums=[_number(r[axis]) for r in by_story]
            joint_nums=[_number(r[axis]) for r in joints]
            if any(x<0 for x in story_nums) or any(x<0 for x in joint_nums):
                raise ValueError("NEGATIVE_DIRECTIONAL_MASS_NEEDS_MANUAL_REVIEW")
            s=sum(story_nums,Decimal(0))
            j=sum(joint_nums,Decimal(0))
            g=_number(all_groups[0][group_col],positive=True)
            story_raw=[r[axis] for r in by_story]
            joint_raw=[r[axis] for r in joints]
            match["story_to_group_"+axis]=_close_display(s,g,*story_raw,all_groups[0][group_col])
            match["joint_to_group_"+axis]=_close_display(j,g,*joint_raw,all_groups[0][group_col])
            story_sums[axis+"_ton"]=str(s)
            group_totals[axis+"_ton"]=str(g)
            joint_sums[axis+"_ton"]=str(j)
        if not all(match.values()):
            return _out("SEISMIC_MASS_RECONCILIATION",
                        facts={"story_sums":story_sums,"group_sums":group_totals,
                               "joint_sums":joint_sums,"comparisons":match,
                               "joint_row_count":len(joints)},
                        reasons=["MASS_JOINT_STORY_GROUP_DISAGREEMENT"])
        diaph_total={axis:sum((_number(r[axis]) for r in diaph),Decimal(0))
                     for axis in ("MassX","MassY")}
        diaph_zero=all(x==0 for x in diaph_total.values())
        return _out("SEISMIC_MASS_RECONCILIATION",
                    facts={"mass_source":"MsSrc1","mass_source_load_multipliers":load_factors,
                           "story_row_count":len(by_story),
                           "joint_row_count":len(joints),
                           "diaphragm_row_count":len(diaph),
                           "story_sums":story_sums,"group_sums":group_totals,
                           "joint_sums":joint_sums,"comparisons":match,
                           "diaphragm_sums_ton":{k:str(v) for k,v in diaph_total.items()}},
                    cautions=["ZERO_DIAPHRAGM_MASS_REQUIRES_ASSIGNMENT_PROOF"] if diaph_zero else
                             ["DIAPHRAGM_MASS_DISTRIBUTION_NOT_CERTIFIED"])
    except (ValueError, KeyError, TypeError) as exc:
        return _out("SEISMIC_MASS_RECONCILIATION",reasons=[str(exc)])


def _cases(probe: Mapping[str, Any]) -> dict:
    try:
        spectrum, meta = _get(probe,SPECTRUM_FUNCTION,
            ("Name","Period","Value","Ss","S1","R","D","I","SDS","SD1","Fs","F1"),
            {"Period":"sec"})
        cases, _ = _get(probe,SPECTRUM_CASE,
            ("Name","MassSource","LoadName","Function","TransAccSF","CoordSys",
             "Angle","ModalCase","ModalCombo","DirCombo","EccenRatio"),
             {"TransAccSF":"m/sec2","Angle":"deg"})
        summary,_ = _get(probe,CASE_SUMMARY,("Name","Type"),{})
        ritz,_ = _get(probe,MODAL_RITZ,
                       ("Name","MassSource","LoadType","LoadName","MaxModes","TargetRatio"),
                       {"TargetRatio":"%"})
        damping,_ = _get(probe,MODAL_DAMPING,("Name","DampType","ConstDamp"),{})
        by_name={r["Name"]:r for r in cases}
        if len(cases)!=2 or set(by_name)!={"RSX","RSY"}:
            raise ValueError("RSX_RSY_CASE_POPULATION_NOT_UNIQUE")
        ids={r["Name"]:r["Type"] for r in summary}
        if len(ids)!=len(summary) or ids.get("Modal")!="Modal - Ritz" or any(ids.get(k)!="Response Spectrum" for k in by_name):
            raise ValueError("CASE_SUMMARY_IDENTITY_MISMATCH")
        modal=[r for r in ritz if r["Name"]=="Modal"]
        if not modal or modal[0]["MassSource"]!="MsSrc1" or modal[0]["LoadType"]!="Accel":
            raise ValueError("MODAL_RITZ_MASS_SOURCE_NOT_QUALIFIED")
        accel={r["LoadName"] for r in modal}
        if not {"Accel UX","Accel UY"}.issubset(accel):
            raise ValueError("MODAL_ACCEL_DIRECTIONS_MISSING")
        damping_names={r["Name"]:r for r in damping}
        if set(damping_names)!={"RSX","RSY"}:
            raise ValueError("MODAL_DAMPING_CASE_BINDINGS_INCOMPLETE")
        fname=cases[0]["Function"]
        if fname in ("","None") or cases[1]["Function"]!=fname:
            raise ValueError("SPECTRUM_FUNCTION_IDENTITY_MISMATCH")
        rows=[r for r in spectrum if r["Name"]==fname]
        if len(rows)!=len(spectrum) or not rows:
            raise ValueError("SPECTRUM_ROW_POPULATION_NOT_QUALIFIED")
        periods=[_number(r["Period"]) for r in rows]
        values=[_number(r["Value"]) for r in rows]
        if any(p<0 for p in periods) or any(v<0 for v in values) or not all(
                periods[i]<periods[i+1] for i in range(len(periods)-1)):
            raise ValueError("SPECTRUM_PERIODS_NOT_STRICTLY_INCREASING")
        first=rows[0]
        R,D,I=(_number(first[k],positive=True) for k in ("R","D","I"))
        Ss,S1,Fs,F1,SDS,SD1=(_number(first[k],positive=True) for k in
                             ("Ss","S1","Fs","F1","SDS","SD1"))
        if not (_close_display(Ss*Fs,SDS,first["SDS"]) and
                _close_display(S1*F1,SD1,first["SD1"])):
            raise ValueError("SDS_SD1_SOURCE_MULTIPLICATION_CONFLICT")
        factors={}
        for name,expected in (("RSX","U1"),("RSY","U2")):
            r=by_name[name]
            if (r["LoadName"]!=expected or r["ModalCase"]!="Modal" or
                    r["CoordSys"]!="Global" or _number(r["Angle"])!=0 or
                    r["MassSource"]!="Previous  (MsSrc1)" or
                    r["ModalCombo"]!="CQC" or r["DirCombo"]!="SRSS" or
                    r["Function"]!=fname):
                raise ValueError("SPECTRUM_CASE_BINDING_MISMATCH:"+name)
            if (damping_names[name]["DampType"]!="Constant" or
                    _number(damping_names[name]["ConstDamp"])!=Decimal("0.05")):
                raise ValueError("SPECTRUM_DAMPING_BINDING_MISMATCH:"+name)
            factors[name]={"direction":expected,"scale_m_s2":str(_number(r["TransAccSF"],positive=True)),
                           "eccentricity_ratio":str(_number(r["EccenRatio"]))}
        return _out("RESPONSE_SPECTRUM_CASE_BINDINGS",
                facts={"function":fname,"modal_case":"Modal","mass_source":"MsSrc1",
                       "spectrum_point_count":len(rows),
                       "period_range_s":[str(periods[0]),str(periods[-1])],
                       "function_parameters":{"R":str(R),"D":str(D),"I":str(I),
                                              "SDS":str(SDS),"SD1":str(SD1),
                                              "Ss":str(Ss),"Fs":str(Fs),
                                              "S1":str(S1),"F1":str(F1)},
                       "modal_combination":"CQC","directional_combination":"SRSS",
                       "case_factors":factors},
                cautions=["I_FIELD_UNITS_METADATA_IS_SEC_BUT_PARAMETER_IS_DIMENSIONLESS"
                          ] if meta.get("units_by_field",{}).get("I")!=" " else [] )
    except (ValueError, KeyError, TypeError) as exc:
        return _out("RESPONSE_SPECTRUM_CASE_BINDINGS",reasons=[str(exc)])


def _geometry(probe: Mapping[str, Any]) -> dict:
    try:
        levels,_=_get(probe,STORY,("Tower","Story","Height"),{"Height":"m"})
        base,_=_get(probe,BASE_STORY,("Tower","BSName","BSElev"),{"BSElev":"m"})
        if len(base)!=1 or len(set(r["Story"] for r in levels))!=len(levels):
            raise ValueError("BASE_OR_STORY_IDENTITY_AMBIGUOUS")
        tower=base[0]["Tower"]
        if any(r["Tower"]!=tower for r in levels):
            raise ValueError("MULTI_TOWER_STORIES_REQUIRE_SEPARATE_SCOPE")
        elevations=[]
        for r in levels:
            try:
                z=Decimal(r["Story"])
            except InvalidOperation:
                raise ValueError("STORY_LABEL_NOT_ELEVATION") from None
            elevations.append((z,r))
        elevations.sort(key=lambda x:x[0])
        bottom=_number(base[0]["BSElev"])
        ascending=[]
        prev=bottom
        for z,r in elevations:
            height=_number(r["Height"],positive=True)
            if not _close_display(z-prev,height,r["Height"],r["Story"],base[0]["BSElev"]):
                # Local geometry contradiction cannot be excused by name matching.
                raise ValueError("STORY_HEIGHT_NOT_MATCHING_ELEVATION")
            ascending.append({"story":r["Story"],"elevation_m":str(z),
                              "height_m":str(height)})
            prev=z
        return _out("PHYSICAL_STORY_GEOMETRY",
                    facts={"tower":tower,"base_story":base[0]["BSName"],
                           "base_elevation_m":str(bottom),"levels_bottom_up":ascending,
                           "story_count":len(levels)})
    except (ValueError,KeyError,TypeError) as exc:
        return _out("PHYSICAL_STORY_GEOMETRY",reasons=[str(exc)])


def _spectrum_modal(probe: Mapping[str, Any]) -> dict:
    raw=(probe.get("table_reads") or {}).get(SPECTRUM_MODAL_INFO)
    if not isinstance(raw,Mapping):
        return _out("SPECTRUM_MODAL_OUTPUT",reasons=["MODAL_INFO_TABLE_MISSING"])
    if raw.get("status")!="CAPTURED":
        return _out("SPECTRUM_MODAL_OUTPUT",
                    facts={"observed_etabs_error":raw.get("error"),
                           "metadata_fields":(raw.get("field_metadata") or {}).get("field_keys")},
                    reasons=["ETABS_RESPONSE_SPECTRUM_MODAL_INFO_RET_CODE_NOT_ZERO"])
    return _out("SPECTRUM_MODAL_OUTPUT",
                facts={"observed_row_count":raw.get("row_count")},
                cautions=["MODAL_AMPLITUDES_NOT_REGULATORY_APPROVAL"])


def review_basis_linkage(raw: Mapping[str, Any] | None) -> dict:
    """Never use this report for actual TBDY compliance or total building mt."""
    base={"stage":"VS04_F_SOURCE_BINDINGS",
          "engineering_release":"NOT_READY", "formal_compliance":"NOT_PROVEN",
          "normative_checks_executed":0,"analysis_generation_proven":False,
          "normative_scalar_promotions":0}
    if not isinstance(raw,Mapping):
        return {**base,"status":"SOURCE_UNAVAILABLE","components":[]}
    source=raw.get("source") if raw.get("schema")=="tbdy.next.vs04e.basis-probe-receipt.v1" else raw
    if not isinstance(source,Mapping) or source.get("schema")!="tbdy.next.vs04e.basis-source-probe.v1":
        return {**base,"status":"SOURCE_REJECTED","reason":"UNKNOWN_SOURCE_SCHEMA","components":[]}
    safety=(source.get("source_mode")=="LIVE_ETABS" and
            source.get("read_only_invariant_proven") is True and
            source.get("units_before")==source.get("units_after")==6 and
            source.get("display_cases_before")==source.get("display_cases_after") and
            source.get("analysis_generation_proven") is False and
            source.get("schema_roles_approved") is False)
    review=review_basis_probe(source)
    if not safety or review.get("status")!="SOURCE_CANDIDATES_OBSERVED_PENDING_REVIEW":
        return {**base,"status":"SOURCE_REJECTED",
                "reason":"PROBE_READONLY_OR_TABLE_INTEGRITY_INVALID","components":[]}
    parts=[_mass(source),_cases(source),_geometry(source),_spectrum_modal(source)]
    observed=sum(x["status"]=="SOURCE_CONTRACT_OBSERVED_UNAPPROVED" for x in parts)
    return {**base,
            "status":"BASIS_SOURCE_PARTIAL_PENDING_ENGINEERING_REVIEW",
            "observed_component_count":observed,
            "expected_component_count":len(parts),
            "source_table_count":source.get("available_table_count"),
            "components":parts,
            "mandatory_holds":[
                "MODEL_ANALYSIS_GENERATION_UNBOUND",
                "SEISMIC_MASS_MT_SCOPE_AND_BASEMENT_NOT_APPROVED",
                "DIAPHRAGM_ASSIGNMENT_AND_ECCENTRICITY_APPLICATION_NOT_PROVEN",
                "SPECTRUM_FUNCTION_DD2_DD3_ROLE_AND_SCALE_NOT_APPROVED",
                "RSX_RSY_UNSCALED_VTX_AND_APPLIED_BETA_NOT_PROVEN",
                "IRREGULARITY_A1_B2_B3_INVENTORY_NOT_COMPLETE",
                "EFFECTIVE_DRIFT_PHYSICAL_STORY_NODE_MAPPING_NOT_PROVEN",
                "DD3_SPECTRUM_AND_LAMBDA_NOT_OBSERVED",
                "NO_SEPARATE_MODEL_FINGERPRINT_TO_LINK_VS04D_VS04E",
            ],
            "source_only_binding_count":observed,
            "seismic_mass_final_kg":None,
            "gamma_E":None,"beta_tE_X":None,"beta_tE_Y":None,
            "effective_drift_X":None,"effective_drift_Y":None,
           }
