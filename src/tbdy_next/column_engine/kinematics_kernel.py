"""Small-rotation joint kinematics; no member stiffness or design decisions.

For an I→J local-1 chord, alpha x e1 = (0, alpha3, -alpha2).
Consequently alpha2=-delta3/L and alpha3=delta2/L. Joint rotations
minus these chord rotations are NOT section rotations at output offsets,
curvature, a TS500 sway class or an independently verified P-delta result.
"""
import math

from .native_archive import BankError, finite
from .ts500_column import positive


def joint_chord_kinematics(axes_global, length_m, u_i, u_j, r_i, r_j):
    def vector(values):
        if not isinstance(values, (list, tuple)) or len(values) != 3:
            raise BankError("KINEMATICS_VECTOR_SHAPE_INVALID")
        return [finite(v, "kinematics") for v in values]
    if not isinstance(axes_global, (list, tuple)) or len(axes_global) != 3:
        raise BankError("KINEMATICS_AXES_SHAPE_INVALID")
    axes = [vector(a) for a in axes_global]
    dot = lambda a, b: sum(x*y for x, y in zip(a, b))
    a, b, c = axes
    cross = [b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0]]
    if (any(abs(dot(axes[i], axes[j])-(1 if i == j else 0)) > 1e-8
            for i in range(3) for j in range(3)) or abs(dot(a, cross)-1) > 1e-8):
        raise BankError("KINEMATICS_AXES_NOT_RIGHT_HANDED_ORTHONORMAL")
    length = positive(length_m, "object_length")
    u_i, u_j, r_i, r_j = map(vector, (u_i, u_j, r_i, r_j))
    local = lambda v: [dot(axis, v) for axis in axes]
    delta_global = [j-i for i, j in zip(u_i, u_j)]
    delta = local(delta_global)
    ri, rj = local(r_i), local(r_j)
    alpha2, alpha3 = -delta[2]/length, delta[1]/length
    result = {"delta_global_m": delta_global, "delta_local_m": delta,
        "joint_i_u_local_m": local(u_i), "joint_j_u_local_m": local(u_j),
        "joint_i_r_local_rad": ri, "joint_j_r_local_rad": rj,
        "chord_alpha2_rad": alpha2, "chord_alpha3_rad": alpha3,
        "joint_i_relative_r2_rad": ri[1]-alpha2, "joint_i_relative_r3_rad": ri[2]-alpha3,
        "joint_j_relative_r2_rad": rj[1]-alpha2, "joint_j_relative_r3_rad": rj[2]-alpha3,
        "object_i_j_length_m": length}
    if any(not math.isfinite(v) for item in result.values()
           for v in (item if isinstance(item, list) else [item])):
        raise BankError("KINEMATICS_ARITHMETIC_OVERFLOW")
    return result
