"""Continuous principal-plane bounds, signed beam aggregation and recorded results."""
from collections import Counter
import math
import unittest

from tbdy_next.column_engine.native_archive import BankError
from tbdy_next.column_engine.scwb_kernel import JointCase, column_axis_interval_bound
from tbdy_next.column_engine.section_capacity import Material, Section, perimeter
from tbdy_next.engineering.column_r10_live import _selected_scwb_interval
from tbdy_next.reporting import _column_r10_html


def section():
    bars = perimeter(600., 800., 40., 10., 20., n2=5, n3=7)[0]
    return Section(600., 800., bars, Material(35., 35./1.5, 365.))


def independent_moment(sec, axis, axial_kn):
    # Integrate the part of each bar disk inside the concrete block with
    # numerical strips. Locate equilibrium by bisection independently of _Curve.
    width, depth = (sec.t2, sec.t3) if axis == "M2" else (sec.t3, sec.t2)
    bars = Counter(((bar.x3 if axis == "M2" else bar.x2), bar.area) for bar in sec.bars)
    def evaluate(c):
        height = min(sec.material.k1*c, depth)
        edge = depth/2 - height
        stress = .85*sec.material.fcd
        n = width*height*stress
        m = n*(depth/2-height/2)
        for (z, area), mult in bars.items():
            elastic = sec.material.ecu*sec.material.es*(1-(depth/2-z)/c)
            steel = min(sec.material.fyd, max(-sec.material.fyd, elastic))*area
            n += mult*steel
            m += mult*steel*z
            radius = math.sqrt(area/math.pi)
            bottom, top = max(edge, z-radius), z+radius
            if bottom >= top:
                continue
            if bottom <= z-radius:
                n -= mult*stress*area
                m -= mult*stress*area*z
                continue
            step = (top-bottom)/64
            for i in range(64):
                y = bottom+(i+.5)*step
                force = mult*stress*2*math.sqrt(max(0., radius**2-(y-z)**2))*step
                n -= force
                m -= force*y
        return n, m
    lo, hi = .001, 20*depth
    for _ in range(56):
        middle = (lo+hi)/2
        if evaluate(middle)[0] < axial_kn*1000:
            lo = middle
        else:
            hi = middle
    return evaluate((lo+hi)/2)[1]/1e6


class AxialIntervalKernelTests(unittest.TestCase):
    def test_independent_equilibria_cover_both_axes_across_yield_and_disk_entry(self):
        sec = section()
        for axis in ("M2", "M3"):
            interval = column_axis_interval_bound(sec, axis, 400., 3800.)
            self.assertEqual(interval["lever_bound_m"], .4 if axis == "M2" else .3)
            self.assertLessEqual(interval["anchors"][0]["nd_kn"], 400.)
            self.assertGreaterEqual(interval["anchors"][-1]["nd_kn"], 3800.)
            for anchor in interval["anchors"]:
                value = independent_moment(sec, axis, anchor["nd_kn"])
                self.assertAlmostEqual(anchor["mr_knm"], value, delta=.03)
            for i in range(21):
                self.assertLess(interval["mr_lower_bound_knm"], independent_moment(sec, axis, 400.+170*i))

    def test_domain_symmetry_order_and_singleton(self):
        sec = section()
        self.assertGreater(column_axis_interval_bound(sec, "M3", 2100., 2100.)["mr_lower_bound_knm"], 0)
        asymmetric = Section(sec.t2, sec.t3, sec.bars[1:], sec.material)
        for args in ((sec, "M3", 3., 1.), (sec, "M3", -90000., 0.), (asymmetric, "M2", 0., 1.),
                     (sec, "M4", 0., 1.), (sec, "M3", float("nan"), 1.)):
            with self.subTest(args=args[1:]), self.assertRaises((ValueError, BankError)):
                column_axis_interval_bound(*args)
        with self.assertRaises(BankError):
            JointCase("run", "source", "J", "X", 1, "E", "SELECTED_CAGE_AXIAL_INTERVAL")
        with self.assertRaises(BankError):
            JointCase("run", "source", "J", "X", 1, "E", "STATIC", "Axial interval", None)


class SelectedJointIntervalTests(unittest.TestCase):
    def setUp(self):
        x,y,z = [1.,0.,0.], [0.,1.,0.], [0.,0.,1.]
        self.cols = [{"frame_id": i, "axes_global": [z,x,y]} for i in ("U","L")]
        self.beams = [{"frame_id":"B","axes_global":[x,z,[0.,-1.,0.]]}]
        self.ends = {"B":{"end":"I"}}
        self.sec = {"U":section(),"L":section()}
        self.decision = {"input_sha256":"source","seismic_combinations":["E1","E2"], "column_ends":[
            {"member_id":uid,"physical_side":side,"end":end,"configured_cut":[uid,0.,uid+"E",0.],
             "seismic_nd_intervals_kn":{"E1":[400.,1200.],"E2":[800.,2200.]}}
            for uid,side,end in (("U","UPPER","I"),("L","LOWER","J"))]}
        self.plan = {"input_sha256":"source","joints":{"J":{"execution_allowed":True,"column_ids":["L","U"],
                                                            "beam_ends":[{"member_id":"B","end":"I"}]}}}
        self.cap = {"axial_force_scenario_n":0,"status":"BEAM_CAPACITY_REFERENCE",
                    "positive_m3_knm":200.,"negative_m3_knm":-300.,
                    "points":[{"rotation_sign":s,"tolerance_knm":1.} for s in (-1,1)]}
        self.br = {"B":{"ends":{"I":{"released_for_bending":False,"engineer_selection":{"capacity":self.cap}}}}}

    def evaluate(self):
        return _selected_scwb_interval("J","X",self.decision,self.plan,self.cols,self.beams,self.ends,
                                     [(self.beams[0],"I")],self.br,self.sec,"run")

    def test_all_assigned_bounds_both_rotations_and_separate_column_ends(self):
        r = self.evaluate()
        self.assertIs(r["sufficient"],True)
        self.assertEqual(r["expected_checks"],r["evaluated_checks"])
        self.assertEqual(r["evaluated_checks"],4)
        for case in r["cases"]:
            self.assertEqual(set(case["columns"]),{"U","L"})
            self.assertEqual({s["rotation_sign"] for s in case["sways"]},{-1,1})
            self.assertEqual({round(s["required_sum_upper_knm"],5) for s in case["sways"]},{241.2,361.2})
        html = _column_r10_html({"member_id":"U","scwb_joints":[{"joint_id":"J","target_end":"I",
                                    "direction":"X","seismic_axial_interval_check":r}]})
        self.assertIn("Ratio lower bound",html)
        self.assertIn("SCWB_EQ_7_3_INTERVAL_SUFFICIENT",html)

    def test_insufficient_lower_bound_cannot_become_a_proven_failure(self):
        self.cap["positive_m3_knm"] = 20000.
        r = self.evaluate()
        self.assertEqual(r["status"],"SCWB_AXIAL_INTERVAL_BOUND_INCONCLUSIVE")
        self.assertIsNone(r["sufficient"])
        self.assertTrue(any(s["sufficient"] is None for c in r["cases"] for s in c["sways"]))

    def test_missing_cage_cut_case_source_face_or_signed_capacity_blocks(self):
        for problem in ("cage","case","source","face","released","tolerance","range","skew"):
            self.setUp()
            if problem == "cage": self.sec.pop("L")
            if problem == "case": del self.decision["column_ends"][1]["seismic_nd_intervals_kn"]["E2"]
            if problem == "source": self.plan["input_sha256"] = "elsewhere"
            if problem == "face": self.plan["joints"]["J"]["beam_ends"] = []
            if problem == "released": self.br["B"]["ends"]["I"]["released_for_bending"] = True
            if problem == "tolerance": self.cap["points"].pop()
            if problem == "range": self.decision["column_ends"][0]["seismic_nd_intervals_kn"]["E1"] = [5.,-2.]
            if problem == "skew": self.beams[0]["axes_global"][0] = [.7,.7,0.]
            with self.subTest(problem=problem):
                r = self.evaluate()
                self.assertIsNone(r["sufficient"])
                self.assertTrue(r["reasons"])
