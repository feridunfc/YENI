"""Centreline geometry for straight and quarter-bent wall bars, in millimetres."""
from math import cos, hypot, pi, sin


def straight_path(face, start, direction, length):
    return {"face":face,"points_mm":[start,[x+length*d for x,d in zip(start,direction)]],
            "chord_error_mm":[0.]}


def bent_path(face, start, direction, turn, run, radius, tail):
    """Sample a true circular centreline and retain each chord's conservative deviation."""
    a = [x+run*d for x,d in zip(start,direction)]
    points = [start,a]
    steps = 8
    for i in range(1,steps+1):
        phi = pi*i/(2*steps)
        points.append([x+radius*(sin(phi)*d+(1-cos(phi))*r) for x,d,r in zip(a,direction,turn)])
    points.append([x+tail*r for x,r in zip(points[-1],turn)])
    return {"face":face,"points_mm":points,"chord_error_mm":[0.,*([radius*(1-cos(pi/(4*steps)))]*steps),0.]}


def point_distance(p,a,b):
    dx,dy = b[0]-a[0],b[1]-a[1]
    den = dx*dx+dy*dy
    f = max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0.
    return hypot(p[0]-a[0]-f*dx,p[1]-a[1]-f*dy)


def segment_distance(a,b,c,d):
    def cross(p,q,r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    if cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0:
        return 0.
    return min(point_distance(a,c,d),point_distance(b,c,d),point_distance(c,a,b),point_distance(d,a,b))
