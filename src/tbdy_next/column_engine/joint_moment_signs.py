"""CSI section-sign to member-on-joint moment mapping, with explicit sense.

Positive CSI M2 compresses local +3; positive M3 compresses local +2.
Stress integration on a positive-1 face therefore gives -M2*e2 + M3*e3.
The member acts on its I joint with this vector and on its J joint with its
negative. This maps capacity directions; it does not transfer V*r or N*r
from an offset cut to a physical joint face.
"""
import math

from .column_joints import GEOMETRY_TOL
from .native_archive import BankError,finite

REFERENCE='https://docs.csiamerica.com/help-files/sap/Output/Frame_Element_Internal_Forces_Output_Conventions.htm'
ROTATION_AXES={'X':(0,1,0),'Y':(-1,0,0)}  # global Z cross the horizontal direction


def _dot(a,b):return math.fsum(x*y for x,y in zip(a,b))


def moment_sign_mapping(axes,end,direction,rotation_sign,axis):
    """Capacity opposes the declared right-hand joint rotation s*(Z cross d)."""
    if (end not in ('I','J') or direction not in ROTATION_AXES or axis not in ('M2','M3')
            or type(rotation_sign) is not int or rotation_sign not in (-1,1)):
        raise BankError('JOINT_MOMENT_CONTEXT_INVALID')
    if not isinstance(axes,(list,tuple)) or len(axes)!=3 or any(not isinstance(a,(list,tuple)) or len(a)!=3 for a in axes):
        raise BankError('JOINT_MOMENT_AXES_INVALID')
    axes=[[finite(v,'axis_cosine') for v in a] for a in axes]
    if any(abs(_dot(axes[i],axes[j])-(i==j))>GEOMETRY_TOL for i in range(3) for j in range(3)):
        raise BankError('JOINT_MOMENT_AXES_NOT_ORTHONORMAL')
    a,b,c=axes
    cross=[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]]
    if abs(_dot(a,cross)-1)>GEOMETRY_TOL:raise BankError('JOINT_MOMENT_AXES_NOT_RIGHT_HANDED')
    moment_axis=axes[1 if axis=='M2' else 2];rotation_axis=ROTATION_AXES[direction]
    projection=_dot(moment_axis,rotation_axis)
    if abs(abs(projection)-1)>GEOMETRY_TOL:raise BankError('JOINT_MOMENT_NOT_GLOBAL_PRINCIPAL_PLANE')
    eta=1 if end=='I' else -1;stress_sign=-1 if axis=='M2' else 1
    alignment=1 if projection>0 else -1
    sign=-rotation_sign*eta*stress_sign*alignment
    vector=[eta*stress_sign*sign*v for v in moment_axis]
    if any(abs(v+rotation_sign*r)>GEOMETRY_TOL for v,r in zip(vector,rotation_axis)):
        raise BankError('JOINT_MOMENT_RESTORING_DIRECTION_UNRESOLVED')
    return {'end':end,'direction':direction,'rotation_sign':rotation_sign,'axis':axis,
        'rotation_axis_global':list(rotation_axis),'local_axes_global':axes,
        'member_on_joint_end_factor':eta,'csi_stress_moment_factor':stress_sign,
        'moment_axis_projection':projection,'local_internal_moment_sign':sign,
        'member_on_joint_unit_moment_global':vector,'restoring_projection':-rotation_sign,
        'basis':'MEMBER_ON_JOINT_OPPOSES_DECLARED_RIGHT_HAND_ROTATION',
        'physical_joint_moment_transfer_proven':False,'shear_or_axial_offset_moments_applied':False}
