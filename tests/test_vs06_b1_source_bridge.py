"""VS06-D1 synthetic ETABS source-to-B1 vertical cut, numeric & negative oracles."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest

from tbdy_next.b1_source_bridge import B1BridgeError, evaluate_b1_sources
from tools.verify_vs06_b1_sources import render_b1_html
from test_vs05_story_drift_binding import seal


MODEL=r"C:\tmp\test_b1.EDB"


def table(key,rows,units=None):
    fields=list(rows[0]) if rows else []
    return {"table_key":key,"status":"CAPTURED","row_count":len(rows),
            "fields":fields,"rows":rows,
            "field_metadata":{"status":"OK","field_keys":fields,
                              "units_by_field":units or {k:"" for k in fields}}}


def sources(*, q1="2.07", q2="4.37"):
    points=[]
    def pt(uid,x,y,z):
        points.append({"UniqueName":uid,"X":str(x),"Y":str(y),"Z":str(z)})
    # X-beams and X-walls with exactly two plan endpoints and two elevations.
    for u,x,y,z in [
        ("A1",0,0,0),("A2",2,0,0),("A3",0,0,3),("A4",5,0,3),
        ("A5",2,0,3),("A6",0,0,6),("A7",2,0,6),
        ("B1",0,0,6),("B2",0,4,6)
    ]: pt(u,x,y,z)
    geometry={
        "schema":"tbdy.next.etabs.generic-source-capture.v1",
        "model":MODEL, "model_units_code":6,"status":"CAPTURED",
        "table_reads":{
            "Point Object Connectivity":table("Point Object Connectivity",points,
                                               {"X":"m","Y":"m","Z":"m"}),
            "Story Definitions":table("Story Definitions",[
                {"Story":"+3.00","Height":"3"},
                {"Story":"+6.00","Height":"3"},
                {"Story":"+9.00","Height":"3"}],{"Height":"m"}),
            "Frame Assignments - Section Properties":table(
                "Frame Assignments - Section Properties",[
                {"UniqueName":"C1","Story":"+3.00","SectProp":"COLUMN","Shape":"Concrete Rectangular"},
                {"UniqueName":"C2","Story":"+6.00","SectProp":"COLUMN","Shape":"Concrete Rectangular"},
                {"UniqueName":"B1","Story":"+3.00","SectProp":"BEAM","Shape":"Concrete Rectangular"},
                {"UniqueName":"B2","Story":"+6.00","SectProp":"BEAM","Shape":"Concrete Rectangular"}]),
            "Frame Section Property Definitions - Concrete Rectangular":table(
                "Frame Section Property Definitions - Concrete Rectangular",[
                {"Name":"COLUMN","t2":"0.8","t3":"0.8","DesignType":"Column"},
                {"Name":"BEAM","t2":"0.3","t3":"0.7","DesignType":"Beam"}],
                {"t2":"m","t3":"m"}),
            "Column Object Connectivity":table("Column Object Connectivity",[
                {"UniqueName":"C1","Story":"+3.00","UniquePtI":"A1","UniquePtJ":"A3"},
                {"UniqueName":"C2","Story":"+6.00","UniquePtI":"A3","UniquePtJ":"A6"}]),
            "Area Assignments - Section Properties":table("Area Assignments - Section Properties",[
                {"UniqueName":"W1","Story":"+3.00","SectProp":"WALL","PropType":"Wall"},
                {"UniqueName":"W2","Story":"+6.00","SectProp":"WALL","PropType":"Wall"}]),
            "Wall Property Definitions - Specified":table("Wall Property Definitions - Specified",[
                {"Name":"WALL","Thickness":"0.4"}],{"Thickness":"m"}),
            "Wall Object Connectivity":table("Wall Object Connectivity",[
                {"UniqueName":"W1","Story":"+3.00","UniquePt1":"A1","UniquePt2":"A2","UniquePt3":"A5","UniquePt4":"A3"},
                {"UniqueName":"W2","Story":"+6.00","UniquePt1":"A3","UniquePt2":"A5","UniquePt3":"A7","UniquePt4":"A6"}]),
        },
    }
    load={
        "schema":"tbdy.next.etabs.generic-source-capture.v1",
        "model":MODEL,"model_units_code":6,"status":"SOURCE_PARTIAL",
        "table_reads":{
            "Beam Object Connectivity":table("Beam Object Connectivity",[
                {"UniqueName":"B1","Story":"+3.00","UniquePtI":"A3","UniquePtJ":"A4","Length":"5"},
                {"UniqueName":"B2","Story":"+6.00","UniquePtI":"B1","UniquePtJ":"B2","Length":"4"}],
                {"Length":"m"}),
        },
        "frame_load_object_probe":{
            "schema":"tbdy.next.etabs.frame-object-distributed-load-probe.v1",
            "source_method":"SapModel.FrameObj.GetLoadDistributed",
            "model_units_code":6,"status":"CAPTURED",
            "beam_count":2,"successful_beam_count":2,"unresolved_beam_count":0,
            "load_row_count":2,"unresolved_beams":[],
            "rows":[
                {"UniqueName":"B1","LoadPattern":"LC_WDL","MyType":"1","Dir":"10",
                 "RelDistA":"0","RelDistB":"1","ValA":str(q1),"ValB":str(q1)},
                {"UniqueName":"B2","LoadPattern":"LC_WDL","MyType":"1","Dir":"10",
                 "RelDistA":"0","RelDistB":"1","ValA":str(q2),"ValB":str(q2)},
            ],
        },
    }
    return seal(geometry),seal(load)


class B1ActualSourceBindingTests(unittest.TestCase):
    def test_columns_walls_and_loaded_beams_are_joined_by_story_and_xy(self):
        a,b=sources()
        r=evaluate_b1_sources(a,b)
        self.assertEqual(r["source_beam_count"],2)
        self.assertEqual(r["source_wall_load_rows"],2)
        self.assertEqual(r["source_candidate_wall_beams"],2)
        self.assertEqual(r["b1_numerical"]["expected_story_direction_pairs"],2)
        self.assertEqual(r["b1_numerical"]["inactive_stories"],["+9.00"])
        low=next(x for x in r["story_direction_areas"] if x["story"]=="+3.00")
        high=next(x for x in r["story_direction_areas"] if x["story"]=="+6.00")
        self.assertEqual(Decimal(low["X"]["column_Aw_m2"]),Decimal(".64"))
        self.assertEqual(Decimal(low["X"]["wall_Ag_m2"]),Decimal(".8"))
        self.assertEqual(Decimal(low["X"]["infill_Ak_assumed_m2"]),Decimal(".45"))
        self.assertEqual(Decimal(high["Y"]["infill_Ak_assumed_m2"]),Decimal(".76"))
        self.assertEqual(low["X"]["loaded_beam_count"],1)
        self.assertEqual(high["Y"]["loaded_beam_count"],1)
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(r["b1_numerical"]["formal_compliance"],"NOT_PROVEN")
        self.assertIn("Model varsayımları",render_b1_html(r))
        self.assertIn("Tablo 3.6",render_b1_html(r))

    def test_real_source_clear_height_is_story_height_minus_beam_depth(self):
        r=evaluate_b1_sources(*sources())
        beams={x["beam_id"]:x for x in r["beam_assumptions"]}
        self.assertEqual(beams["B1"]["clear_wall_height_m"],"2.3")
        self.assertEqual(beams["B2"]["clear_wall_height_m"],"2.3")
        self.assertEqual(beams["B1"]["thickness_m"],"0.09")
        self.assertEqual(beams["B2"]["thickness_m"],"0.19")
        self.assertEqual(beams["B1"]["assumed_opening_fraction"],"0")
        self.assertEqual(beams["B2"]["assumed_opening_fraction"],"0")

    def test_low_line_load_uses_explicit_half_opening_heuristic(self):
        r=evaluate_b1_sources(*sources(q1="1.45"))
        x=next(a for a in r["beam_assumptions"] if a["beam_id"]=="B1")
        self.assertEqual(x["thickness_m"],"0.09")
        self.assertEqual(x["assumed_opening_fraction"],"0.5")
        self.assertEqual(x["opening_reason"],"LOW_LINE_LOAD_ASSUMED_HALF_OPENING")
        self.assertEqual(Decimal(x["assumed_Ak_m2"]),Decimal("0.225"))

    def test_flexible_wall_is_numerically_omitted_in_b1_not_physically_erased(self):
        r=evaluate_b1_sources(*sources(),wall_type="FLEXIBLE")
        self.assertTrue(any(Decimal(x["X"]["infill_Ak_assumed_m2"])>0
                            for x in r["story_direction_areas"]))
        self.assertTrue(all(p["flexible_infill_omitted_by_4_9_1_3_b"]
                            for p in r["b1_numerical"]["paired_results"]))

    def test_no_fake_pass_from_trusted_user_flags(self):
        r=evaluate_b1_sources(*sources())
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(r["engineering_release"],"NOT_READY")

    def test_wrong_capture_hash_fails_closed(self):
        g,l=sources()
        l["frame_load_object_probe"]["rows"][0]["LoadPattern"]="HACK"
        with self.assertRaisesRegex(B1BridgeError,"SHA_OR_SCHEMA"):
            evaluate_b1_sources(g,l)

    def test_changed_model_rejected_even_if_sealed(self):
        g,l=sources()
        l["model"]="DIFFERENT"
        with self.assertRaisesRegex(B1BridgeError,"MODEL_OR_UNITS_MISMATCH"):
            evaluate_b1_sources(g,seal(l | {"payload_sha256":None}))

    def test_loss_of_point_coordinate_unit_denied(self):
        g,l=sources()
        g.pop("payload_sha256")
        g["table_reads"]["Point Object Connectivity"]["field_metadata"]["units_by_field"]["X"]="mm"
        with self.assertRaisesRegex(B1BridgeError,"SCHEMA_UNRECONCILED"):
            evaluate_b1_sources(seal(g),l)

    def test_deterministic_no_input_mutation(self):
        g,l=sources()
        old=deepcopy((g,l))
        a=evaluate_b1_sources(g,l)
        b=evaluate_b1_sources(g,l)
        self.assertEqual((g,l),old)
        self.assertEqual(a,b)
        self.assertEqual(len(a["result_sha256"]),64)


if __name__=="__main__":
    unittest.main()
