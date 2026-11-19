"""CSI native dimensions are not named after their coordinate direction.

Analysis Reference, Frame Element / Section Properties: T3 is the depth in
local direction 2; T2 is the width in local direction 3. Keep native labels
and M2/M3/V2/V3 unchanged, and convert at each physical-geometry boundary.
"""
from __future__ import annotations

from dataclasses import dataclass

from .native_archive import BankError, finite

AXIS_CONVENTION = "CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3"
REFERENCE = "https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf"


@dataclass(frozen=True)
class NativeSectionDims:
    """ETABS/CSI native rectangular section dimensions (T2 along local 3, T3 along local 2)."""

    native_t2_mm: float
    native_t3_mm: float

    def __post_init__(self) -> None:
        t2, t3 = finite(self.native_t2_mm, "native_T2_mm"), finite(self.native_t3_mm, "native_T3_mm")
        if min(t2, t3) <= 0:
            raise BankError("POSITIVE_NATIVE_RECTANGLE_DIMENSIONS_REQUIRED")
        object.__setattr__(self, "native_t2_mm", float(t2))
        object.__setattr__(self, "native_t3_mm", float(t3))


@dataclass(frozen=True)
class LocalSectionDims:
    """Physical section extents along CSI local axes 2 and 3 after single conversion."""

    local2_extent_mm: float
    local3_extent_mm: float

    def __post_init__(self) -> None:
        d2, d3 = finite(self.local2_extent_mm, "local2_extent_mm"), finite(self.local3_extent_mm, "local3_extent_mm")
        if min(d2, d3) <= 0:
            raise BankError("POSITIVE_LOCAL_RECTANGLE_DIMENSIONS_REQUIRED")
        object.__setattr__(self, "local2_extent_mm", float(d2))
        object.__setattr__(self, "local3_extent_mm", float(d3))

    @property
    def bending_depth_m2_mm(self) -> float:
        """Depth resisting M2 (bending in 1-3 plane, along local axis 3 = native T2)."""
        return self.local3_extent_mm

    @property
    def bending_depth_m3_mm(self) -> float:
        """Depth resisting M3 (bending in 1-2 plane, along local axis 2 = native T3)."""
        return self.local2_extent_mm


def local_dimensions(t2_mm, t3_mm):
    """Return (extent along local 2, extent along local 3), in mm."""
    if isinstance(t2_mm, LocalSectionDims) or isinstance(t3_mm, LocalSectionDims):
        raise TypeError("DOUBLE_AXIS_CONVERSION_DENIED")
    t2, t3 = finite(t2_mm, "native_T2_mm"), finite(t3_mm, "native_T3_mm")
    if min(t2, t3) <= 0:
        raise BankError("POSITIVE_NATIVE_RECTANGLE_DIMENSIONS_REQUIRED")
    return t3, t2


def to_local_dimensions(dims: NativeSectionDims) -> LocalSectionDims:
    """Single-conversion boundary from NativeSectionDims to LocalSectionDims (F08/F09)."""
    if isinstance(dims, LocalSectionDims):
        raise TypeError("DOUBLE_AXIS_CONVERSION_DENIED: already in LocalSectionDims")
    if not isinstance(dims, NativeSectionDims):
        raise TypeError("NATIVE_SECTION_DIMS_REQUIRED")
    d2, d3 = local_dimensions(dims.native_t2_mm, dims.native_t3_mm)
    return LocalSectionDims(local2_extent_mm=d2, local3_extent_mm=d3)


def physical_column_side_at_joint(joint_xyz_m, other_xyz_m, *, tolerance_m=1e-8):
    """Classify the physical other end; native I/J is not an above/below rule."""
    if any(not isinstance(p, (list, tuple)) or len(p) != 3 for p in (joint_xyz_m, other_xyz_m)):
        raise BankError("JOINT_COLUMN_COORDINATES_NOT_BOUND")
    joint = [finite(v, "joint_coordinate_m") for v in joint_xyz_m]
    other = [finite(v, "other_column_end_coordinate_m") for v in other_xyz_m]
    tolerance = finite(tolerance_m, "joint_geometry_tolerance_m")
    if tolerance < 0:
        raise BankError("JOINT_GEOMETRY_TOLERANCE_INVALID")
    delta_z = other[2] - joint[2]
    if delta_z < -tolerance:
        return "LOWER"
    if delta_z > tolerance:
        return "UPPER"
    raise BankError("JOINT_COLUMN_VERTICAL_SIDE_NOT_BOUND")


def physical_shear_axis(direction, axes_global, *, tolerance=1e-8):
    """Map a physical unit direction to one lower-column V2/V3 axis.

    Parallel and antiparallel axes carry the same confinement area. Unsupported
    oblique or ambiguous directions do not inherit the target column's label.
    """
    if (not isinstance(direction, (list, tuple)) or len(direction) != 3
            or not isinstance(axes_global, (list, tuple)) or len(axes_global) != 3
            or any(not isinstance(a, (list, tuple)) or len(a) != 3 for a in axes_global)):
        raise BankError("JOINT_LOWER_AXIS_MAPPING_NOT_BOUND")
    vector = [finite(v, "joint_direction") for v in direction]
    axes = [[finite(v, "column_axis") for v in a] for a in axes_global]
    tol = finite(tolerance, "joint_axis_tolerance")
    if tol < 0 or abs(sum(v * v for v in vector) - 1.0) > tol:
        raise BankError("JOINT_LOWER_AXIS_MAPPING_NOT_BOUND")
    if any(abs(sum(axes[i][k] * axes[j][k] for k in range(3)) - (1.0 if i == j else 0.0)) > tol
           for i in range(3) for j in range(3)):
        raise BankError("JOINT_LOWER_AXIS_MAPPING_NOT_BOUND")
    matches = [i for i in (1, 2) if abs(abs(sum(a * b for a, b in zip(vector, axes[i]))) - 1.0) <= tol]
    if len(matches) != 1:
        raise BankError("JOINT_LOWER_AXIS_MAPPING_NOT_BOUND")
    return "V" + str(matches[0] + 1)
