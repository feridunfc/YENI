"""CSI native dimensions are not named after their coordinate direction.

Analysis Reference, Frame Element / Section Properties: T3 is the depth in
local direction 2; T2 is the width in local direction 3. Keep native labels
and M2/M3/V2/V3 unchanged, and convert at each physical-geometry boundary.
"""
from .native_archive import BankError, finite

AXIS_CONVENTION = "CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3"
REFERENCE = "https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf"


def local_dimensions(t2_mm, t3_mm):
    """Return (extent along local 2, extent along local 3), in mm."""
    t2, t3 = finite(t2_mm, "native_T2_mm"), finite(t3_mm, "native_T3_mm")
    if min(t2, t3) <= 0:
        raise BankError("POSITIVE_NATIVE_RECTANGLE_DIMENSIONS_REQUIRED")
    return t3, t2
