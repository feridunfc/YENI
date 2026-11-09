"""Conditional rectangular PMM arithmetic, in N/mm/MPa and CSI local axes.

Adapted from TBDY 1440df1: section_capacity.py and rebar_layout.py. Retains
strain compatibility and polygon clipping. Concrete displaced by a circular
bar is removed using its exact disk/half-plane intersection and first moments;
steel strain remains sampled at the bar centroid, as in the source kernel.
M3 is explicitly converted from the reference kernel to CSI (+2 compression).
This removes the legacy whole-bar-at-center discontinuity, without smoothing
the forces or relaxing their tolerance. Angular refinement follows Column.
This is a numerical scenario kernel, not an engineering approval/selection.
"""
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
import math

K1 = {16: .85, 18: .85, 20: .85, 25: .85, 30: .82, 35: .79, 40: .76, 45: .73, 50: .70}
FORCE_TOL_N = 1.0
MOMENT_ABS_TOL_NMM = 1000.0
MOMENT_REL_TOL = .002
ANGLE_COUNTS = (72, 144, 288)
MAX_ANGLE_COUNT = 1152
DIRECTION_TOL_NMM = 1000.0
DIRECTION_MAX_ITERATIONS = 64
RADIAL_BASIS = "STRAIN_COMPATIBLE_POINT_AT_FIXED_N_AND_MOMENT_DIRECTION"


def number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("PMM_INVALID_NUMBER:" + name)
    if positive and value <= 0:
        raise ValueError("PMM_POSITIVE_NUMBER_REQUIRED:" + name)
    return float(value)


@dataclass(frozen=True)
class Bar:
    x2: float
    x3: float
    area: float

    def __post_init__(self):
        number(self.x2, "x2"); number(self.x3, "x3"); number(self.area, "area", positive=True)


@dataclass(frozen=True)
class Material:
    fck: float
    fcd: float
    fyd: float
    es: float = 200000.0
    ecu: float = .003

    def __post_init__(self):
        for key in ("fck", "fcd", "fyd", "es", "ecu"):
            number(getattr(self, key), key, positive=True)
        if self.fck not in K1 or self.fcd > self.fck or self.fyd / self.es >= .1:
            raise ValueError("PMM_MATERIAL_OUTSIDE_KERNEL_SCOPE")

    @property
    def k1(self):
        return K1[self.fck]


@dataclass(frozen=True)
class Section:
    """Physical extents t2 along local 2 and t3 along local 3, not native T2/T3.

    CSI adapters must pass native T3, T2 in this order.
    """
    t2: float
    t3: float
    bars: tuple
    material: Material

    def __post_init__(self):
        number(self.t2, "t2", positive=True); number(self.t3, "t3", positive=True)
        if not isinstance(self.material, Material) or not isinstance(self.bars, tuple) or not self.bars:
            raise ValueError("PMM_SECTION_INPUTS_REQUIRED")
        if any(not isinstance(b, Bar) or abs(b.x2) >= self.t2/2 or abs(b.x3) >= self.t3/2 for b in self.bars):
            raise ValueError("PMM_BAR_OUTSIDE_SECTION")
        if len({(b.x2, b.x3) for b in self.bars}) != len(self.bars):
            raise ValueError("PMM_DUPLICATE_BAR")
        if sum(b.area for b in self.bars) >= self.t2*self.t3:
            raise ValueError("PMM_STEEL_AREA_INVALID")
        for index, bar in enumerate(self.bars):
            radius = math.sqrt(bar.area/math.pi)
            if abs(bar.x2)+radius > self.t2/2 or abs(bar.x3)+radius > self.t3/2:
                raise ValueError("PMM_BAR_DISK_OUTSIDE_SECTION")
            for other in self.bars[index+1:]:
                if math.hypot(bar.x2-other.x2,bar.x3-other.x3) < radius+math.sqrt(other.area/math.pi):
                    raise ValueError("PMM_BAR_DISKS_OVERLAP")

    @property
    def symmetric(self):
        points = {(b.x2, b.x3, b.area) for b in self.bars}
        return all((s2*b.x2, s3*b.x3, b.area) in points for b in self.bars for s2 in (-1, 1) for s3 in (-1, 1))


def perimeter(t2, t3, cover, tie, diameter, n2=5, n3=5):
    """Physical local-2/local-3 extents; cover is clear to OUTSIDE of the tie.

    These t2/t3 arguments are coordinate extents, not CSI's native T2/T3.
    """
    for key, value in (("t2", t2), ("t3", t3), ("cover", cover), ("tie", tie), ("diameter", diameter)):
        number(value, key, positive=True)
    if any(type(n) is not int or not 2 <= n <= 100 for n in (n2, n3)):
        raise ValueError("PMM_FACE_BAR_COUNT_INVALID")
    center = cover + tie + diameter/2
    a, b = t2/2-center, t3/2-center
    if min(a, b) <= 0:
        raise ValueError("PMM_CAGE_DOES_NOT_FIT")
    x = tuple((2*i-(n2-1))*a/(n2-1) for i in range(n2))
    y = tuple((2*i-(n3-1))*b/(n3-1) for i in range(n3))
    spacing = min(2*a/(n2-1), 2*b/(n3-1))-diameter
    if spacing < 0:
        raise ValueError("PMM_BARS_OVERLAP")
    area = math.pi*diameter**2/4
    bars = tuple(Bar(u, v, area) for u in x for v in (-b, b)) + tuple(Bar(u, v, area) for v in y[1:-1] for u in (-a, a))
    return bars, center, spacing


class _Curve:
    """Continuous N(c) for fixed angle; cached samples only bracket exact roots."""
    def __init__(self, section, angle):
        self.section, self.angle = section, angle
        theta = math.radians(number(angle, "angle"))
        self.nx, self.ny = math.cos(theta), math.sin(theta)
        # Exact cardinal directions prevent artificial duplicate bar-entry cuts.
        if abs(self.nx) < 1e-14: self.nx = 0.0
        if abs(self.ny) < 1e-14: self.ny = 0.0
        w, h = section.t2/2, section.t3/2
        self.polygon = ((-w,-h),(w,-h),(w,h),(-w,h))
        self.q = tuple(x*self.nx+y*self.ny for x,y in self.polygon)
        self.extreme = max(self.q)
        self.depths = tuple(self.extreme-b.x2*self.nx-b.x3*self.ny for b in section.bars)
        self.radii = tuple(math.sqrt(b.area/math.pi) for b in section.bars)
        self.samples = None

    def evaluate(self, c):
        s, mat = self.section, self.section.material
        level = self.extreme-mat.k1*c
        clipped = []
        previous, qp = self.polygon[-1], self.q[-1]-level
        for current, raw_q in zip(self.polygon, self.q):
            qc = raw_q-level
            if (qc >= 0) != (qp >= 0):
                f = qp/(qp-qc)
                clipped.append((previous[0]+f*(current[0]-previous[0]), previous[1]+f*(current[1]-previous[1])))
            if qc >= 0: clipped.append(current)
            previous, qp = current, qc
        area2 = first2 = first3 = 0.0
        if clipped:
            previous = clipped[-1]
            for current in clipped:
                cross = previous[0]*current[1]-current[0]*previous[1]
                area2 += cross
                first2 += (previous[0]+current[0])*cross
                first3 += (previous[1]+current[1])*cross
                previous = current
        stress = .85*mat.fcd
        force = stress*area2/2
        m2, m3 = stress*first3/6, stress*first2/6
        tension_strain = 0.0
        for bar, depth, radius in zip(s.bars, self.depths, self.radii):
            strain = mat.ecu*(1-depth/c)
            tension_strain = max(tension_strain, -strain)
            steel = max(-mat.fyd, min(mat.fyd, mat.es*strain))*bar.area
            force += steel; m2 += steel*bar.x3; m3 += steel*bar.x2
            d = mat.k1*c-depth
            if d <= -radius: continue
            if d >= radius:
                area, first = bar.area, 0.0
            else:
                radicand = max(0.0,radius*radius-d*d)
                root = math.sqrt(radicand)
                area = radius*radius*math.acos(-d/radius)+d*root
                first = 2*radicand*root/3
            force -= stress*area
            m2 -= stress*(area*bar.x3+first*self.ny)
            m3 -= stress*(area*bar.x2+first*self.nx)
        return {"n_n": force, "m2_nmm": m2, "m3_nmm": m3,
            "c_mm": c, "theta_deg": self.angle, "maximum_tensile_strain": tension_strain}

    def _prepare(self):
        s, mat = self.section, self.section.material
        diagonal = math.hypot(s.t2, s.t3)
        low,high = diagonal*1e-9,diagonal*1e6
        cuts = {low*(high/low)**(i/60) for i in range(61)}
        cuts.update((d+sign*r)/mat.k1 for d,r in zip(self.depths,self.radii) for sign in (-1,0,1))
        cuts.update((self.extreme-q)/mat.k1 for q in self.q if q<self.extreme)
        yield_ratio = mat.fyd/(mat.es*mat.ecu)
        cuts.update(d/(1+yield_ratio) for d in self.depths)
        if yield_ratio < 1: cuts.update(d/(1-yield_ratio) for d in self.depths)
        cs = sorted({low,high,*[c for c in cuts if low<c<high]})
        ns = [self.evaluate(c)["n_n"] for c in cs]
        # Nonoverlapping disks entirely in the rectangle ensure a nonnegative
        # remaining concrete strip; steel force is also nondecreasing with c.
        if any(v > w+FORCE_TOL_N for v,w in zip(ns,ns[1:])):
            raise ValueError("PMM_NONMONOTONE_AXIAL_CURVE")
        self.samples = cs,ns

    def solve(self, target, *, seed_c=None):
        if seed_c is None:
            # Preserve the accepted sampled bracket path used by fixed-axis
            # column and asymmetric beam capacity callers.
            if self.samples is None: self._prepare()
            cs,ns = self.samples
            if not ns[0] <= target <= ns[-1]: return None,"AXIAL_ROOT_UNRESOLVED"
            index = max(1,bisect_left(ns,target))
            lo,hi,flo,fhi = cs[index-1],cs[index],ns[index-1]-target,ns[index]-target
        else:
            # A neighbouring solved c is only a bracket hint. Every endpoint
            # is evaluated at this angle, and the interval is expanded until
            # it actually contains N. No interpolated c/resultant is returned.
            seed=number(seed_c,"axial_bracket_seed",positive=True)
            diagonal=math.hypot(self.section.t2,self.section.t3)
            lower,upper=diagonal*1e-9,diagonal*1e6
            lo=max(lower,min(upper,seed/2));hi=max(lower,min(upper,seed*2))
            flo=number(self.evaluate(lo)['n_n'],"axial_bracket_N")-target
            fhi=number(self.evaluate(hi)['n_n'],"axial_bracket_N")-target
            for _ in range(64):
                if flo<=0<=fhi:break
                previous=(lo,hi)
                if flo>0:
                    lo=max(lower,lo/2);flo=number(self.evaluate(lo)['n_n'],"axial_bracket_N")-target
                if fhi<0:
                    hi=min(upper,hi*2);fhi=number(self.evaluate(hi)['n_n'],"axial_bracket_N")-target
                if (lo,hi)==previous:return None,"AXIAL_ROOT_UNRESOLVED"
            else:return None,"AXIAL_ROOT_UNRESOLVED"
        for iteration in range(64):
            if abs(flo)<=FORCE_TOL_N: c = lo
            elif abs(fhi)<=FORCE_TOL_N: c = hi
            else:
                c = (lo*fhi-hi*flo)/(fhi-flo) if fhi!=flo else (lo+hi)/2
                if iteration%5==4 or not lo<c<hi: c = (lo+hi)/2
            point = self.evaluate(c)
            residual = point["n_n"]-target
            if abs(residual)<=FORCE_TOL_N:
                if point["maximum_tensile_strain"]>.1: return None,"STEEL_STRAIN_LIMIT_UNRESOLVED"
                return point,None
            if residual<0: lo,flo = c,residual
            else: hi,fhi = c,residual
        return None,"AXIAL_ROOT_UNRESOLVED"


def evaluate_state(section, angle, c):
    return _Curve(section, angle).evaluate(number(c, "c", positive=True))


def _radial(points, u2, u3):
    hits = []
    for left, right in zip(points, points[1:]):
        x,y = left["m2_nmm"], left["m3_nmm"]
        dx,dy = right["m2_nmm"]-x, right["m3_nmm"]-y
        denominator = u2*dy-u3*dx
        if abs(denominator) < 1e-12: continue
        t = (x*dy-y*dx)/denominator
        f = (x*u3-y*u2)/denominator
        if t > 0 and -1e-10 <= f <= 1+1e-10:
            point2, point3 = x+f*dx, y+f*dy
            hits.append((t, {"left": left, "right": right, "fraction": f,
                "interpolated_angle_deg":left["theta_deg"]+f*(right["theta_deg"]-left["theta_deg"]),
                "direction_residual_nmm": abs(point2*u3-point3*u2)}))
    if not hits: return None
    values = [h[0] for h in hits]
    if max(values)-min(values) > MOMENT_ABS_TOL_NMM: return None
    # Adjacent segments can touch the same sampled vertex. Distinct angular
    # intersections, even at equal radii, are not a single resolved bracket.
    angles = [h[1]["interpolated_angle_deg"] for h in hits]
    if max(angles)-min(angles)>1e-9:return None
    return min(hits, key=lambda hit: hit[0])


def _direction_root(section, target_n, u2, u3, ray):
    """Resolve the actual strain plane; a polygon segment only supplies a bracket.

    Each midpoint uses a fresh axial solve. Neither c nor the section
    resultants are interpolated between angular samples. This local solve
    does not prove global uniqueness of the continuous interaction surface.
    """
    left,right=ray["left"],ray["right"]
    lo,hi=left["theta_deg"],right["theta_deg"]
    result={"status":"MOMENT_DIRECTION_ROOT_UNRESOLVED","reason":None,
        "method":"BRACKETED_BISECTION_EXACT_AXIAL_EQUILIBRIUM","target_n_n":target_n,
        "angle_basis":"COMPRESSION_NORMAL_LOCAL2_TO_LOCAL3_FIRST_QUADRANT_DEG",
        "folded_unit_direction":[u2,u3],"initial_bracket_theta_deg":[lo,hi],
        "final_bracket_theta_deg":[lo,hi],"direction_tolerance_nmm":DIRECTION_TOL_NMM,
        "iterations":0,"evaluated_point_count":0,"max_axial_residual_n":0.0,
        "point":None,"capacity_nmm":None,"axial_residual_n":None,"direction_residual_nmm":None,
        "interpolated_strain_plane_used":False,"global_root_uniqueness_proven":False}
    def inspect(point):
        for k in ("n_n","m2_nmm","m3_nmm","theta_deg","c_mm","maximum_tensile_strain"):
            number(point[k],"root_"+k,positive=k=="c_mm")
        residual=abs(point["n_n"]-target_n)
        if residual>FORCE_TOL_N or point["maximum_tensile_strain"]>.1:
            raise ValueError("DIRECTION_ROOT_AXIAL_STATE_UNRESOLVED")
        result["evaluated_point_count"]+=1
        result["max_axial_residual_n"]=max(result["max_axial_residual_n"],residual)
        g=point["m2_nmm"]*u3-point["m3_nmm"]*u2
        capacity=point["m2_nmm"]*u2+point["m3_nmm"]*u3
        number(g,"root_direction_residual");number(capacity,"root_capacity",positive=True)
        return g,capacity,residual
    def accept(point,g,capacity,residual):
        result.update(status="MOMENT_DIRECTION_ROOT_RESOLVED",point=dict(point),capacity_nmm=capacity,
            axial_residual_n=residual,direction_residual_nmm=abs(g),final_bracket_theta_deg=[lo,hi])
        return result
    try:
        if not 0<=lo<hi<=90:raise ValueError("DIRECTION_ROOT_ANGLE_BRACKET_INVALID")
        gl,cl,rl=inspect(left);gh,ch,rh=inspect(right)
        if abs(gl)<=DIRECTION_TOL_NMM:return accept(left,gl,cl,rl)
        if abs(gh)<=DIRECTION_TOL_NMM:return accept(right,gh,ch,rh)
        if gl*gh>=0:raise ValueError("DIRECTION_ROOT_SIGN_BRACKET_MISSING")
        for iteration in range(DIRECTION_MAX_ITERATIONS):
            result["iterations"]=iteration+1
            angle=(lo+hi)/2
            seed=left['c_mm']+(right['c_mm']-left['c_mm'])/2
            point,reason=_Curve(section,angle).solve(target_n,seed_c=seed)
            if reason:raise ValueError("DIRECTION_ROOT_"+reason)
            g,capacity,residual=inspect(point)
            if abs(g)<=DIRECTION_TOL_NMM:return accept(point,g,capacity,residual)
            if gl*g<=0:hi,right=angle,point
            else:lo,gl,left=angle,g,point
        raise ValueError("DIRECTION_ROOT_ITERATION_LIMIT")
    except (ValueError,OverflowError) as exc:
        result.update(reason=str(exc),final_bracket_theta_deg=[lo,hi])
        return result


class RadialSolver:
    def __init__(self, section):
        if not section.symmetric:
            raise ValueError("PMM_RADIAL_REQUIRES_TWO_AXIS_SYMMETRY")
        self.section = section
        self.curves = {}
        steel_area = sum(b.area for b in section.bars)
        m = section.material
        self.tension = -steel_area*m.fyd
        self.compression = .85*m.fcd*(section.t2*section.t3-steel_area)+steel_area*min(m.fyd,m.es*m.ecu)

    def assess(self, n_n, m2_nmm, m3_nmm):
        n, m2, m3 = (number(v,k) for v,k in ((n_n,"N"),(m2_nmm,"M2"),(m3_nmm,"M3")))
        base = {"status": "NUMERIC_UNRESOLVED", "reason": None, "utilization": None,
            "radial_capacity_kNm": None, "axial_range_kN": [self.tension/1000,self.compression/1000],
            "refinement": None, "final_design_eligible": False}
        if not self.tension <= n <= self.compression:
            return {**base, "status": "OUTSIDE_SCENARIO_AXIAL_RANGE", "reason": "SECTION_MODEL_AXIAL_LIMIT"}
        magnitude = math.hypot(m2,m3)
        if not math.isfinite(magnitude):return {**base,"reason":"MOMENT_MAGNITUDE_NOT_FINITE"}
        if magnitude == 0:
            return {**base, "status": "AXIAL_ONLY_SCENARIO", "axial_utilization": n/self.compression if n>=0 else n/self.tension}
        if min(n-self.tension,self.compression-n) <= FORCE_TOL_N:
            return {**base, "reason": "AXIAL_ENDPOINT_WITH_MOMENT"}
        points_by_angle = {}
        max_residual = 0.0
        u2,u3 = abs(m2)/magnitude,abs(m3)/magnitude
        counts, history = ANGLE_COUNTS, []
        while True:
            points = []
            for i in range(counts[-1]//4+1):
                angle = 360*i/counts[-1]
                if angle not in points_by_angle:
                    if angle not in self.curves: self.curves[angle] = _Curve(self.section,angle)
                    point,reason = self.curves[angle].solve(n)
                    if reason: return {**base,"reason":reason,"unresolved_angle_deg":angle}
                    points_by_angle[angle] = point
                    max_residual = max(max_residual,abs(point["n_n"]-n))
                points.append(points_by_angle[angle])
            # Ordered strain-compatible points; never a convex hull. Each
            # point solves this exact N. Only angles are discretized.
            if any(p["m2_nmm"] < -MOMENT_ABS_TOL_NMM or p["m3_nmm"] < -MOMENT_ABS_TOL_NMM for p in points):
                return {**base,"reason":"QUADRANT_ENVELOPE_UNRESOLVED"}
            rays = [_radial(points[::counts[-1]//count],u2,u3) for count in counts]
            if any(r is None for r in rays): return {**base,"reason":"RADIAL_INTERSECTION_UNRESOLVED"}
            capacities = [r[0] for r in rays]
            differences = [abs(b-a) for a,b in zip(capacities,capacities[1:])]
            budgets = [MOMENT_ABS_TOL_NMM+MOMENT_REL_TOL*max(abs(a),abs(b)) for a,b in zip(capacities,capacities[1:])]
            stable = all(d<=b for d,b in zip(differences,budgets))
            history.append({"angle_counts":list(counts),"capacity_kNm":[c/1e6 for c in capacities],
                "differences_kNm":[d/1e6 for d in differences],"budgets_kNm":[b/1e6 for b in budgets],
                "status":"OBSERVED_STABLE_AT_BOTH_STEPS" if stable else "OBSERVED_NOT_STABLE"})
            evidence = {**history[-1],"history":history,"max_axial_residual_n":max_residual,"finest_ray":rays[-1][1],
                "symmetry_used":"VERIFIED_TWO_AXIS_GEOMETRY","continuous_error_bound_proven":False}
            if stable: break
            if counts[-1]>=MAX_ANGLE_COUNT:
                return {**base,"reason":"ANGULAR_REFINEMENT_NOT_STABLE","refinement":evidence}
            counts = tuple(2*c for c in counts)
        root=_direction_root(self.section,n,u2,u3,rays[-1][1])
        evidence.update(capacity_basis=RADIAL_BASIS,direction_root=root,
            max_axial_residual_n=max(max_residual,root["max_axial_residual_n"]))
        if root["status"]!="MOMENT_DIRECTION_ROOT_RESOLVED":
            return {**base,"reason":root["reason"],"refinement":evidence}
        capacity = root["capacity_nmm"]
        evidence.update(selected_capacity_kNm=capacity/1e6,
            coarse_minimum_capacity_kNm=min(capacities)/1e6,
            root_minus_coarse_minimum_kNm=(capacity-min(capacities))/1e6,
            root_minus_finest_polygon_kNm=(capacity-capacities[-1])/1e6)
        ratio = magnitude/capacity
        # A computed ratio infinitesimally above/below one is not a resolved
        # exceedance/inside finding. Keep a decision guard at the same numeric
        # budget, plus the section-radius lever arm of the force tolerance.
        # This guard does not claim a rigorous continuous-envelope error bound.
        boundary_band = (MOMENT_ABS_TOL_NMM+MOMENT_REL_TOL*max(magnitude,capacity)
            + FORCE_TOL_N*math.hypot(self.section.t2,self.section.t3)/2)
        if abs(magnitude-capacity)<=boundary_band:
            return {**base,"reason":"NEAR_NUMERICAL_SURFACE_BOUNDARY","trial_utilization":ratio,
                "radial_capacity_kNm":capacity/1e6,"boundary_guard_kNm":boundary_band/1e6,"refinement":evidence}
        return {**base,"status":"WITHIN_SCENARIO_SURFACE" if ratio<=1 else "EXCEEDS_SCENARIO_SURFACE",
            "utilization":ratio,"radial_capacity_kNm":capacity/1e6,"refinement":evidence}


@lru_cache(maxsize=12)
def solver(section):
    """Bounded numeric-only cache; key contains full cage/material geometry."""
    return RadialSolver(section)
