"""Configured-cut inputs for the synthetic two-column Web selection fixture.

These are test getter/table values, not live ETABS or physical-face approval.
The table census is declared independently of successful force results.
"""
from tbdy_next.engineering.column_r10_live import (
    ANALYSIS_FRAME_ELEMENTS, END_OFFSETS, FRAME_OUTPUT_STATIONS,
)
from test_beam_r10_live import _beam_table


def configure_three_cut_forces(outputs):
    def frame_force(member, item_type, count, *arrays):
        raw = outputs.frame_force(member, item_type, count, *arrays)
        # The original fixture has constant forces. Its synthetic getter returns
        # those values at the three configured cuts of each 3 m object.
        rows = []
        for original in zip(*raw[1:-1]):
            if original[1] != 0.0:
                continue
            for station in (0.0, 1.5, 3.0):
                row = list(original)
                row[1] = row[3] = station
                rows.append(row)
        return [len(rows), *map(list, zip(*rows)), 0]

    outputs.sap.Results.FrameForce.side_effect = frame_force


def attach_configured_selection_scope(data):
    reads = data["column_axial"]["r10_source"]["table_reads"]
    reads[ANALYSIS_FRAME_ELEMENTS] = _beam_table(
        ANALYSIS_FRAME_ELEMENTS, ["Story", "ObjType", "ObjName", "ElmName", "ElmJtI", "ElmJtJ"],
        [("S1", "Frame", "C1", "C1-elm", "P0", "P1"),
         ("S1", "Frame", "C2", "C2-elm", "P10", "P11")])
    reads[FRAME_OUTPUT_STATIONS] = _beam_table(
        FRAME_OUTPUT_STATIONS, ["Story", "UniqueName", "StationOpt", "MaxSpacing", "MinStations"],
        [("S1", uid, "Min Stations", "None", "3") for uid in ("C1", "C2")], {"MaxSpacing": "m"})
    reads[END_OFFSETS] = _beam_table(
        END_OFFSETS, ["Story", "UniqueName", "OffsetI", "OffsetJ"],
        [("S1", "C1", "0", "0"), ("S1", "C2", "0", "0"),
         ("S1", "B1", "0.2", "0.2"), ("S1", "B2", "0.2", "0.2")],
        {"OffsetI": "m", "OffsetJ": "m"})
    for key in (ANALYSIS_FRAME_ELEMENTS, FRAME_OUTPUT_STATIONS, END_OFFSETS):
        reads[key]["field_metadata"]["table_version"] = 1
    return data
