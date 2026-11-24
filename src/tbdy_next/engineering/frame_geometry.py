"""Native ETABS frame section dimensions, axes, point identities and adjacency."""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Mapping

from ..column_engine.csi_geometry import NativeSectionDims, to_local_dimensions
from ..column_engine.native_archive import BankError

_GEOMETRY_TOL = 1e-8


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() == "none":
            return None
        value = text
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return numeric if math.isfinite(numeric) else None


def _axis_angle_deg(fa_row: Mapping[str, Any] | None) -> float | None:
    if not fa_row:
        return None
    raw = fa_row.get("AxisAngle")
    if raw is None or (isinstance(raw, str) and raw.strip().lower() in ("", "none")):
        return 0.0
    return _float_or_none(raw)


def _point_coordinates(source: Mapping[str, Any]) -> dict[str, list[float]]:
    for key in ("vs05_delta_source", "vs06_b1_geometry_source"):
        block = source.get(key)
        if not isinstance(block, Mapping):
            continue
        table = (block.get("table_reads") or {}).get("Point Object Connectivity")
        if isinstance(table, Mapping) and isinstance(table.get("rows"), list):
            points: dict[str, list[float]] = {}
            for row in table["rows"]:
                uid = row.get("UniqueName")
                coords = [_float_or_none(row.get(axis)) for axis in ("X", "Y", "Z")]
                if isinstance(uid, str) and uid and all(v is not None for v in coords):
                    points[uid] = [float(coords[0]), float(coords[1]), float(coords[2])]
            if points:
                return points
    return {}


def _dot(a: list[float], b: list[float]) -> float:
    return math.fsum(x * y for x, y in zip(a, b))


def _cross(a: list[float], b: list[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _normalize(v: list[float], label: str) -> list[float]:
    length = math.sqrt(_dot(v, v))
    if not math.isfinite(length) or length <= _GEOMETRY_TOL:
        raise BankError(f"R10_ZERO_LENGTH_VECTOR:{label}")
    return [x / length for x in v]


def _csi_frame_axes(pi_xyz: list[float], pj_xyz: list[float], angle_deg: float) -> list[list[float]]:
    """Reconstruct right-handed CSI [e1, e2, e3] in Global coordinates."""
    e1 = _normalize([b - a for a, b in zip(pi_xyz, pj_xyz)], "e1")
    horiz = math.hypot(e1[0], e1[1])
    if horiz <= _GEOMETRY_TOL:
        e2_0 = [1.0, 0.0, 0.0]
        e3_0 = [0.0, 1.0 if e1[2] > 0 else -1.0, 0.0]
    else:
        e3_0 = _normalize(_cross(e1, [0.0, 0.0, 1.0]), "e3_0")
        e2_0 = _normalize(_cross(e3_0, e1), "e2_0")
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    e2 = _normalize([c * a + s * b for a, b in zip(e2_0, e3_0)], "e2")
    e3 = _normalize([-s * a + c * b for a, b in zip(e2_0, e3_0)], "e3")
    return [e1, e2, e3]


def build_frame_catalog(source: Mapping[str, Any]) -> tuple[dict[str, dict], dict[str, list[float]], dict[str, Any]]:
    tables = (source.get("geometry_capture") or {}).get("tables") or {}
    fa_rows = (tables.get("FRAME_ASSIGNMENTS") or {}).get("rows") or []
    col_rows = (tables.get("COLUMN_CONNECTIVITY") or {}).get("rows") or []
    beam_rows = (tables.get("BEAM_CONNECTIVITY") or {}).get("rows") or []
    rect_rows = (tables.get("RECTANGULAR_SECTIONS") or {}).get("rows") or []

    fa_by_id = {row["UniqueName"]: row for row in fa_rows if row.get("UniqueName")}
    rect_by_name = {row["Name"]: row for row in rect_rows if row.get("Name")}
    points = _point_coordinates(source)
    frames: dict[str, dict[str, Any]] = {}
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def register(rows: list[dict], kind: str) -> None:
        for row in rows:
            uid = row.get("UniqueName")
            pt_i, pt_j = row.get("UniquePtI"), row.get("UniquePtJ")
            if not uid or not pt_i or not pt_j:
                continue
            fa = fa_by_id.get(uid, {})
            sect_name = fa.get("AnalysisSect") or fa.get("DesignSect")
            rect = rect_by_name.get(sect_name or "")
            dims = None
            mat_name = None
            if rect:
                t2_m = _float_or_none(rect.get("t2"))
                t3_m = _float_or_none(rect.get("t3"))
                mat_name = rect.get("Material")
                if t2_m is not None and t3_m is not None and t2_m > 0 and t3_m > 0:
                    dims = to_local_dimensions(NativeSectionDims(t2_m * 1000.0, t3_m * 1000.0))
            angle = _axis_angle_deg(fa)
            axes = None
            if pt_i in points and pt_j in points and angle is not None:
                try:
                    axes = _csi_frame_axes(points[pt_i], points[pt_j], angle)
                except BankError:
                    axes = None
            frames[uid] = {
                "frame_id": uid,
                "label": fa.get("Label") or row.get("ColumnBay") or row.get("BeamBay"),
                "story": row.get("Story") or fa.get("Story"),
                "type": kind,
                "point_i": pt_i,
                "point_j": pt_j,
                "section_name": sect_name,
                "material_name": mat_name,
                "dims": dims,
                "axis_angle_deg": angle,
                "axes_global": axes,
            }
            for pt, end in ((pt_i, "I"), (pt_j, "J")):
                adjacency[pt].append({"frame_id": uid, "end": end, "type": kind})

    register(col_rows, "Column")
    register(beam_rows, "Beam")
    meta = {
        "point_coordinates_available": bool(points),
        "point_count": len(points),
        "column_count": len(col_rows),
        "beam_count": len(beam_rows),
    }
    return frames, points, {"adjacency": adjacency, **meta}
