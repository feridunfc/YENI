"""Explicit self-weight inputs for the normal two-story design pipeline.

This extends the existing public native-shaped source, not its calculated
results. It is a CONTRACT_FIXTURE, not an ETABS solution or original C29 data.
The axial gradient is independently specified as gamma * area * weight modifier.
Every selected signed combination and primitive uses the same physical cuts.
"""
from copy import deepcopy
from hashlib import sha256
import json

from tbdy_next.engineering.column_axial import column_strength_plan
from tbdy_next.engineering.column_pmm_section import MECHANICAL
from tbdy_next.engineering.demand_sources import SUPPORT_SCHEMA, demand_capture_plan
from tbdy_next.engineering.design_scenario import _digest, _source_data
from test_r10_live import _rowset
from vertical_slice_fixture import (
    COMBINATIONS, CUTS, generic, source_and_request as constant_axial_source_and_request, table,
)


AREA_M2 = .64
WEIGHT_MODIFIER = 1.
TOP_COMPRESSION_KN = {"C1": 2500., "C2": 1500.}
PRIMITIVES = ("LC_DL", "EX", "EY")


def bind_source(source, request):
    """Rebind the ordinary request after a deliberate fixture-input revision."""
    raw = json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    result = deepcopy(request)
    result["parent_input_sha256"] = sha256(raw).hexdigest()
    for key in ("analysis_basis", "second_order_basis"):
        result[key]["source_data_sha256"] = _digest(_source_data(source))
    return raw, result


def source_and_request(*, adopt_axial_idealization=True, k=1., rm=0.,
                       unit_weight_kn_m3=25., gravity_m3_increment_knm=0.):
    """Return raw source and an ordinary design-scenario request.

    Changing the adoption flag changes only the request. Native vectors retain
    their varying N; the declared idealization must be consumed by the owner.
    The moment increment is an explicit input for a downstream capacity test.
    """
    raw, request = constant_axial_source_and_request(two_story=True, k=k, rm=rm)
    source = json.loads(raw)
    source["example_context"].update(
        name="Two-story self-weight axial gradient and interior-joint calculation",
        scope="SIGNED_SELF_WEIGHT_GRADIENT_FIXTURE_NOT_BUILDING_EQUILIBRIUM",
    )
    section = source["geometry_capture"]["tables"]["SECTION_SUMMARY"]
    section["fields"].append("WMod")
    section["field_metadata"]["field_keys"].append("WMod")
    section["field_metadata"]["units_by_field"].update(Area="m2", WMod="")
    for row in section["rows"]:
        row["WMod"] = "1"
    # A concrete source row is supplied in addition to the existing steel row.
    # UnitWeight has explicit printed precision; E1 is an input, not a result.
    properties = source["column_axial"]["pmm_section_source"]["table_reads"]
    properties[MECHANICAL] = table(MECHANICAL, "Material E1 UnitWeight", [
        ("B420C", "200000000", "78.500000"),
        ("C35/45", "33000000", format(unit_weight_kn_m3, ".6f")),
    ], {"E1": "kN/m2", "UnitWeight": "kN/m3"})

    q = unit_weight_kn_m3 * AREA_M2 * WEIGHT_MODIFIER
    main_rows = source["column_axial"]["force_source"]["rowsets"]
    primitive_rows = {}
    for uid, top_compression in TOP_COMPRESSION_KN.items():
        selected, primitive = [], []
        for name in COMBINATIONS:
            sx = 1 if name == "G+EX" else -1 if name == "G-EX" else 0
            sy = 1 if name == "G+EY" else -1 if name == "G-EY" else 0
            for station in CUTS:
                selected.append((uid, station, uid + "-elm", station, name, "Single Value", 0.,
                    -(top_compression + q * (2.5 - station)),
                    25. * sx, 20. * sy, 0., 30. + (2.5 - station) * 20. * sy,
                    30. + gravity_m3_increment_knm + (2.5 - station) * 25. * sx))
        for name in PRIMITIVES:
            for station in CUTS:
                if name == "LC_DL":
                    vector = (-(top_compression + q * (2.5 - station)),
                              0., 0., 0., 30., 30. + gravity_m3_increment_knm)
                elif name == "EX":
                    vector = (0., 25., 0., 0., 0., (2.5 - station) * 25.)
                else:
                    vector = (0., 0., 20., 0., (2.5 - station) * 20., 0.)
                primitive.append((uid, station, uid + "-elm", station, name, "Single Value", 0., *vector))
        main_rows[uid] = _rowset(selected)
        primitive_rows[uid] = _rowset(primitive)

    # Use the normal catalog/selection plan owners; these are source-scope
    # definitions, never prepared engineering outcomes.
    strength_plan = column_strength_plan(source, source["column_axial"]["request"])
    plan = demand_capture_plan(source, strength_plan)
    all_cases = request["analysis_basis"]["case_roles"]
    before = {"cases": dict.fromkeys(all_cases, False), "combos": dict.fromkeys(COMBINATIONS, False)}
    during = deepcopy(before)
    for name in plan["cases"]:
        during["cases"][name] = True
    source["column_axial"]["demand_support"] = {
        "schema": SUPPORT_SCHEMA, "plan": plan,
        "force_source": {"schema": "tbdy.next.etabs-frame-force-source.v1",
            "api": "Results.FrameForce", "item_type": "ObjectElm", "units_code": 6,
            "output_selection_before": before, "output_selection_after": deepcopy(before),
            "output_selection_during": during, "rowsets": primitive_rows, "errors": {}},
    }

    # Retain consistent source cumulative gravity at the two lower story cuts.
    weights = source["r08_second_order_source"]["weight_source"]["table_reads"]
    for row in weights["Story Forces"]["rows"]:
        uid = "C1" if row["Story"] == "S1" else "C2"
        row["P"] = str(TOP_COMPRESSION_KN[uid] + q * 2.5)
    weights["Base Reactions"]["rows"][0]["FZ"] = str(TOP_COMPRESSION_KN["C1"] + q * 2.5)
    source["r08_second_order_source"]["weight_source"] = generic(weights)

    request["scenario_id"] = "public-variable-axial-slice"
    request["analysis_basis"]["basis_id"] = "public-variable-axial-first-order"
    request["second_order_basis"]["basis_id"] = "public-variable-axial-local-basis"
    for uid, member in request["second_order_basis"]["members"].items():
        member["decision_reference"] = "Synthetic prismatic member with native self-weight axial variation"
        if adopt_axial_idealization:
            member["applicability"] = "ADOPTED_PRISMATIC_SELF_WEIGHT_NMAX_IDEALIZATION"
            member["axial_idealization"] = {
                "method": "SELF_WEIGHT_NMAX", "combinations": sorted(COMBINATIONS),
                "decision_reference": "Explicit Nmax surrogate for this signed synthetic source; engineering acceptance not granted",
            }
    return bind_source(source, request)
