"""Independent numerical reference for the existing rectangular PMM model.

No production capacity solver, polygon clipping or disk-cap formula is used.
The SAME declared material model is integrated by strips and Gaussian disk
quadrature, then solved with independent axial and angular bisection. This
checks numerical agreement, not the material model or code applicability.
All quantities are N, mm, MPa; M2 integrates local-3, M3 local-2 coordinates.
"""
from dataclasses import dataclass
from copy import deepcopy
from functools import lru_cache
import math

FORCE_TOL_N = .05
DIRECTION_ABS_TOL_NMM = 100.0
DIRECTION_REL_TOL = 1e-8
INTEGRATION_ABS_TOL_NMM = 100.0
INTEGRATION_REL_TOL = 1e-5
LEVELS = ((8, 12), (16, 24), (32, 48))  # disk panels, quadrant angular intervals
GAUSS = 1 / math.sqrt(3)


def _number(value, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (positive and value <= 0):
        raise ValueError("REFERENCE_NUMBER_INVALID")
    return float(value)


@dataclass(frozen=True)
class ReferenceSection:
    local2_mm: float
    local3_mm: float
    bars: tuple  # (local2 coordinate, local3 coordinate, area)
    block_stress_mpa: float
    block_depth_factor: float
    steel_yield_mpa: float
    steel_modulus_mpa: float = 200000.0
    concrete_ultimate_strain: float = .003

    def __post_init__(self):
        for v in (self.local2_mm, self.local3_mm, self.block_stress_mpa, self.block_depth_factor,
                  self.steel_yield_mpa, self.steel_modulus_mpa, self.concrete_ultimate_strain):
            _number(v, True)
        if not 0 < self.block_depth_factor <= 1 or not isinstance(self.bars, tuple) or not 1 <= len(self.bars) <= 400:
            raise ValueError("REFERENCE_SECTION_INVALID")
        for i, bar in enumerate(self.bars):
            if not isinstance(bar, tuple) or len(bar) != 3:
                raise ValueError("REFERENCE_BAR_INVALID")
            x, y, area = bar; _number(x); _number(y); _number(area, True)
            r = math.sqrt(area / math.pi)
            if abs(x)+r > self.local2_mm/2 or abs(y)+r > self.local3_mm/2:
                raise ValueError("REFERENCE_BAR_DISK_OUTSIDE")
            for bx, by, other in self.bars[:i]:
                if math.hypot(x-bx, y-by) < r+math.sqrt(other/math.pi):
                    raise ValueError("REFERENCE_BAR_DISKS_OVERLAP")
        if sum(b[2] for b in self.bars) >= self.local2_mm*self.local3_mm:
            raise ValueError("REFERENCE_NET_CONCRETE_INVALID")

    @property
    def symmetric(self):
        bars = set(self.bars)
        return all((a*x,b*y,area) in bars for x,y,area in bars for a in (-1,1) for b in (-1,1))


def rectangle_resultants(width, height, nx, ny, level):
    """Integrate split local-2 strips; each piece is at most quadratic."""
    w,h = width/2,height/2
    if ny == 0:
        if nx == 0:
            raise ValueError("REFERENCE_NORMAL_INVALID")
        cut = level/nx
        lo,hi = (max(-w,cut),w) if nx > 0 else (-w,min(w,cut))
        if hi <= lo:
            return 0.0,0.0,0.0
        return height*(hi-lo), height*(hi*hi-lo*lo)/2, 0.0
    cuts = {-w,w}
    if nx != 0:
        for y in (-h,h):
            x = (level-ny*y)/nx
            if -w < x < w:
                cuts.add(x)
    cuts = sorted(cuts); area=[]; first2=[]; first3=[]
    for lo,hi in zip(cuts,cuts[1:]):
        midpoint,half = (lo+hi)/2,(hi-lo)/2
        for sign in (-1,1):
            x = midpoint+sign*GAUSS*half; cut = (level-nx*x)/ny
            bottom,top = (max(-h,cut),h) if ny > 0 else (-h,min(h,cut))
            if top <= bottom:
                continue
            area.append(half*(top-bottom));first2.append(half*x*(top-bottom))
            first3.append(half*(top*top-bottom*bottom)/2)
    return math.fsum(area), math.fsum(first2), math.fsum(first3)


def disk_resultants(area, threshold, panels):
    """Area and first moment of u>=threshold, using u=R sin(t).

    The substitution removes the square-root endpoint singularity. Full/empty
    disks are exact. No acos/spherical-cap expression is borrowed from primary.
    """
    radius = math.sqrt(area/math.pi)
    if threshold <= -radius:
        return area,0.0
    if threshold >= radius:
        return 0.0,0.0
    start = math.asin(threshold/radius); span = (math.pi/2-start)/panels
    a=[];q=[]
    for i in range(panels):
        middle = start+(i+.5)*span; half = span/2
        for sign in (-1,1):
            theta = middle+sign*GAUSS*half
            weight = 2*radius*radius*math.cos(theta)**2*half
            a.append(weight);q.append(weight*radius*math.sin(theta))
    return math.fsum(a),math.fsum(q)


class _StripPlane:
    def __init__(self, section, angle_deg, panels):
        self.section,self.angle,self.panels=section,angle_deg,panels
        theta=math.radians(angle_deg);self.nx,self.ny=math.cos(theta),math.sin(theta)
        if abs(self.nx)<1e-14:self.nx=0.0
        if abs(self.ny)<1e-14:self.ny=0.0
        self.extreme=abs(self.nx)*section.local2_mm/2+abs(self.ny)*section.local3_mm/2
        self.bar_data=tuple((x,y,a,self.extreme-self.nx*x-self.ny*y) for x,y,a in section.bars)

    def evaluate(self,c_mm):
        s=self.section;depth=s.block_depth_factor*c_mm;level=self.extreme-depth
        area,first2,first3=rectangle_resultants(s.local2_mm,s.local3_mm,self.nx,self.ny,level)
        n=[s.block_stress_mpa*area];m2=[s.block_stress_mpa*first3];m3=[s.block_stress_mpa*first2]
        maximum_tension=0.0
        for x,y,bar_area,d in self.bar_data:
            strain=s.concrete_ultimate_strain*(1-d/c_mm)
            maximum_tension=max(maximum_tension,-strain)
            stress=max(-s.steel_yield_mpa,min(s.steel_yield_mpa,s.steel_modulus_mpa*strain))
            steel=stress*bar_area;n.append(steel);m2.append(steel*y);m3.append(steel*x)
            displaced,first=disk_resultants(bar_area,d-depth,self.panels)
            n.append(-s.block_stress_mpa*displaced)
            m2.append(-s.block_stress_mpa*(displaced*y+first*self.ny))
            m3.append(-s.block_stress_mpa*(displaced*x+first*self.nx))
        values=math.fsum(n),math.fsum(m2),math.fsum(m3)
        if any(not math.isfinite(v) for v in values):
            raise ValueError("REFERENCE_RESULT_NONFINITE")
        return {"n_n":values[0],"m2_nmm":values[1],"m3_nmm":values[2],
            "c_mm":c_mm,"theta_deg":self.angle,"maximum_tensile_strain":maximum_tension}


def reference_state(section, angle_deg, c_mm, panels=32):
    if not isinstance(section,ReferenceSection) or type(panels) is not int or not 1<=panels<=128:
        raise ValueError("REFERENCE_REQUEST_INVALID")
    return _StripPlane(section,_number(angle_deg),panels).evaluate(_number(c_mm,True))


def _axial_root(section,angle,n_target,panels):
    plane=_StripPlane(section,angle,panels);diagonal=math.hypot(section.local2_mm,section.local3_mm)
    lo,hi=diagonal*1e-9,diagonal
    lower,upper=plane.evaluate(lo),plane.evaluate(hi)
    for _ in range(30):
        if upper["n_n"]>=n_target:break
        hi*=2;upper=plane.evaluate(hi)
    if not lower["n_n"]<=n_target<=upper["n_n"]:
        raise ValueError("REFERENCE_AXIAL_BRACKET_UNRESOLVED")
    for iteration in range(80):
        mid=(lo+hi)/2;point=plane.evaluate(mid);residual=point["n_n"]-n_target
        if abs(residual)<=FORCE_TOL_N:
            if point["maximum_tensile_strain"]>.1:
                raise ValueError("REFERENCE_STEEL_STRAIN_OUTSIDE_SCOPE")
            return {**point,"axial_residual_n":abs(residual),"axial_iterations":iteration+1}
        if residual<0:lo=mid
        else:hi=mid
    raise ValueError("REFERENCE_AXIAL_BISECTION_UNRESOLVED")


def _direction(point,u2,u3):
    g=point["m2_nmm"]*u3-point["m3_nmm"]*u2
    tolerance=DIRECTION_ABS_TOL_NMM+DIRECTION_REL_TOL*math.hypot(point["m2_nmm"],point["m3_nmm"])
    return g,tolerance


def _radial_level(section,n_target,u2,u3,panels,intervals):
    points={}
    def point(angle):
        if angle not in points:points[angle]=_axial_root(section,angle,n_target,panels)
        return points[angle]
    angles=[90*i/intervals for i in range(intervals+1)]
    sampled=[point(a) for a in angles];roots=[]
    def add(p):
        dot=p["m2_nmm"]*u2+p["m3_nmm"]*u3
        if dot>0:
            roots.append({**p,"capacity_nmm":dot,"direction_residual_nmm":abs(_direction(p,u2,u3)[0])})
    directions=[_direction(p,u2,u3) for p in sampled]
    for p,(g,tolerance) in zip(sampled,directions):
        if abs(g)<=tolerance:add(p)
    for i,((gl,tl),(gh,th)) in enumerate(zip(directions,directions[1:])):
        if abs(gl)<=tl or abs(gh)<=th or gl*gh>=0:continue
        lo,hi=angles[i],angles[i+1]
        for _ in range(60):
            middle=(lo+hi)/2;p=point(middle);g,tolerance=_direction(p,u2,u3)
            if abs(g)<=tolerance:
                add(p);break
            if gl*g<=0:hi=middle
            else:lo=middle;gl=g
        else:raise ValueError("REFERENCE_DIRECTION_BISECTION_UNRESOLVED")
    return {"disk_panels":panels,"quadrant_angular_intervals":intervals,"sampled_angle_range_deg":[0,90],
        "sampled_angle_count":len(sampled),"evaluated_angle_count":len(points),"positive_roots":roots,
        "positive_root_count":len(roots),"max_axial_residual_n":max(p["axial_residual_n"] for p in points.values()),
        "production_bracket_used":False,"global_root_uniqueness_proven":False}


@lru_cache(maxsize=512)
def _cached_radial_capacity(section,n_target_n,m2_nmm,m3_nmm):
    if not isinstance(section,ReferenceSection) or not section.symmetric:
        raise ValueError("REFERENCE_TWO_AXIS_SYMMETRY_REQUIRED")
    n,m2,m3=(_number(v) for v in (n_target_n,m2_nmm,m3_nmm));magnitude=math.hypot(m2,m3)
    if not math.isfinite(magnitude) or magnitude<=0:
        raise ValueError("REFERENCE_NONZERO_MOMENT_REQUIRED")
    steel_area=sum(b[2] for b in section.bars)
    lower=-steel_area*section.steel_yield_mpa
    upper=(section.local2_mm*section.local3_mm-steel_area)*section.block_stress_mpa+steel_area*min(
        section.steel_yield_mpa,section.steel_modulus_mpa*section.concrete_ultimate_strain)
    if not lower+FORCE_TOL_N<n<upper-FORCE_TOL_N:
        raise ValueError("REFERENCE_AXIAL_ENDPOINT_OR_RANGE")
    u2,u3=abs(m2)/magnitude,abs(m3)/magnitude
    history=[_radial_level(section,n,u2,u3,panels,intervals) for panels,intervals in LEVELS]
    result={"status":"REFERENCE_UNRESOLVED","reason":None,"capacity_knm":None,"utilization":None,
        "history":history,"continuous_error_bound_proven":False,"global_root_uniqueness_proven":False,
        "same_material_model_used":True,"independent_material_model_validation":False,
        "moment_signs_from_verified_symmetry":True,"production_capacity_solver_called":False}
    if any(h["positive_root_count"]!=1 for h in history):
        result["reason"]="REFERENCE_POSITIVE_ROOT_COUNT_NOT_ONE";return result
    capacities=[h["positive_roots"][0]["capacity_nmm"] for h in history]
    differences=[abs(a-b) for a,b in zip(capacities,capacities[1:])]
    budgets=[INTEGRATION_ABS_TOL_NMM+INTEGRATION_REL_TOL*max(a,b) for a,b in zip(capacities,capacities[1:])]
    result.update(capacity_knm=capacities[-1]/1e6,utilization=magnitude/capacities[-1],
        differences_knm=[d/1e6 for d in differences],budgets_knm=[b/1e6 for b in budgets],
        max_axial_residual_n=max(h["max_axial_residual_n"] for h in history),
        max_direction_residual_nmm=max(h["positive_roots"][0]["direction_residual_nmm"] for h in history))
    result["status"]="REFERENCE_OBSERVED_STABLE" if all(d<=b for d,b in zip(differences,budgets)) else "REFERENCE_NOT_STABLE"
    return result


def reference_radial_capacity(section,n_target_n,m2_nmm,m3_nmm):
    """Return an isolated result; callers cannot modify the numeric cache."""
    return deepcopy(_cached_radial_capacity(section,n_target_n,m2_nmm,m3_nmm))
