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
