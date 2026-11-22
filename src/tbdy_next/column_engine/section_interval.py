"""Sufficient PMM check for a symmetric rectangle over continuous N and both moment signs."""
from math import atan2, ceil, cos, degrees, floor, hypot, inf, isfinite, pi, sin

from .section_capacity import FORCE_TOL_N, MOMENT_ABS_TOL_NMM, _Curve, solver


class SectionInterval:
    """Reuse the fixed-angle section kernel. Cache only within one pier calculation."""

    def __init__(self, section):
        self.section = section
        self.radial = solver(section)  # Also verifies two-axis symmetry.
        self.cells = {}

    def _patch(self, nlo, nhi, a, b):
        # From the positive corner, both coordinates of every material point's
        # distance vector are nonnegative. On [a,b] its compression-face depth
        # lies between the two dot products below, for concrete and every bar.
        xmin, ymin = max(0., cos(b)), sin(a)
        xmax, ymax = cos(a), sin(b)
        smaller, larger = hypot(xmin, ymin), hypot(xmax, ymax)
        shallow = _Curve(self.section, degrees(atan2(ymin, xmin)))
        deep = _Curve(self.section, degrees(atan2(ymax, xmax)))
        seed = max(1., .35 * (self.section.t2 * xmax + self.section.t3 * ymax))
        low, reason = shallow.solve(nlo - 2 * FORCE_TOL_N, seed_c=seed)
        if reason:
            raise ValueError(reason)
        high, reason = deep.solve(nhi + 2 * FORCE_TOL_N, seed_c=seed)
        if reason:
            raise ValueError(reason)
        # A shallower depth gives greater stress at fixed c, so its axial root
        # bounds the real c from below. Reverse the depth extremes when
        # evaluating the pointwise lower and upper stress fields.
        lower = deep.evaluate(low["c_mm"] * smaller / larger * (1 - 1e-12))
        upper = shallow.evaluate(high["c_mm"] * larger / smaller * (1 + 1e-12))
        if lower["n_n"] > nlo or upper["n_n"] < nhi or lower["maximum_tensile_strain"] > .1:
            raise ValueError("AXIAL_OR_STRAIN_INTERVAL_UNRESOLVED")
        floors = []
        for field, lever in (("m2_nmm", self.section.t3/2), ("m3_nmm", self.section.t2/2)):
            # Pointwise nonnegative stress increments give |delta M| <= lever * delta N.
            # Both bounds apply at the same N. Their mean eliminates that unknown N.
            lo, hi = lower[field], upper[field]
            lower_limit = max(lo - lever*(nhi-lower["n_n"]), hi - lever*(upper["n_n"]-nlo),
                              (lo + hi - lever*(upper["n_n"]-lower["n_n"]))/2)
            floors.append((lower_limit - MOMENT_ABS_TOL_NMM)/1e6)
        return tuple(floors)

    def assess(self, nd, m2, m3):
        """Upper gauge of the component box in kN, kN·m. An upper bound above one is inconclusive."""
        lo, hi = nd
        if not all(isfinite(v) for v in (lo, hi, m2, m3)) or lo > hi or min(m2, m3) < 0:
            raise ValueError("INVALID_PIER_DEMAND_INTERVAL")
        if lo*1000 <= self.radial.tension or hi*1000 >= self.radial.compression:
            raise ValueError("AXIAL_INTERVAL_TOUCHES_SECTION_LIMIT")
        if m2 == m3 == 0:
            return {"status": "PMM_BOX_SATISFIED", "upper_utilization": max(0., lo*1000/self.radial.tension,
                        hi*1000/self.radial.compression), "basis": "PURE_AXIAL_INTERVAL"}
        # Shared axial cells reuse work between face combinations. Clip end
        # cells near the material limits instead of extrapolating past them.
        best = None
        for divisions, step in ((96, 62.5), (192, 31.25)):
            worst, location = 0., None
            for i in range(floor(lo/step), max(floor(lo/step)+1, ceil(hi/step))):
                bottom, top = i*step, (i+1)*step
                if bottom*1000 <= self.radial.tension+4*FORCE_TOL_N:
                    bottom = max(lo, bottom)
                if top*1000 >= self.radial.compression-4*FORCE_TOL_N:
                    top = min(hi, top)
                key = (bottom, top, divisions)
                if key not in self.cells:
                    half_pi = pi/2
                    try:
                        self.cells[key] = [self._patch(bottom*1000, top*1000, j*half_pi/divisions,
                            (j+1)*half_pi/divisions) for j in range(divisions)]
                    except ValueError as exc:
                        self.cells[key] = str(exc)
                cells = self.cells[key]
                if isinstance(cells, str):
                    worst, location = inf, {"reason": cells, "axial_cell_kn": [bottom, top]}
                    break
                for j, (r2, r3) in enumerate(cells):
                    # Along each possible limit surface point, at least one
                    # component must clear the demand rectangle. The quadrant
                    # sweeps from the strong to the weak principal ray.
                    ratio = min(m2/r2 if r2 > 0 else inf, m3/r3 if r3 > 0 else inf)
                    if ratio > worst:
                        worst, location = ratio, {"axial_cell_kn": [bottom, top],
                            "angle_interval_deg": [j*90/divisions, (j+1)*90/divisions],
                            "moment_component_floors_knm": [r2, r3]}
            if best is None or worst < best[0]:
                best = (worst, divisions, step, location)
            if worst < 1:
                break
        ratio, divisions, step, location = best
        return {"status": "PMM_BOX_SATISFIED" if ratio < 1 else "PMM_BOX_INCONCLUSIVE",
                "upper_utilization": ratio if isfinite(ratio) else None, "governing_cell": location,
                "quadrant_intervals": divisions, "axial_cell_width_kn": step,
                "basis": "POINTWISE_STRESS_BOUNDS_OVER_AXIAL_AND_ANGULAR_INTERVALS"}
