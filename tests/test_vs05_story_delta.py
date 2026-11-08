from __future__ import annotations
import copy
import unittest
from tbdy_next.story_delta import calculate, DeltaSourceError


def table(name, fields, rows, units):
    return {"table_key":name,"status":"CAPTURED","fields":fields,"row_count":len(rows),
            "rows":rows,"field_metadata":{"status":"OK","field_keys":fields,"units_by_field":units}}


def fixture():
    story=table("Story Definitions",["Story","Tower","Height"],
        [{"Story":"+9.00","Tower":"T1","Height":"4.5"},
         {"Story":"+4.50","Tower":"T1","Height":"4.5"}],{"Height":"m"})
    drifts=table("Story Drifts",["Story","OutputCase","CaseType","StepType","Direction","Drift","Label"],
        [{"Story":"+9.00","OutputCase":"RSX","CaseType":"LinRespSpec","StepType":"Max","Direction":"X","Drift":"0.000776","Label":"131"}],{"Drift":""})
    maxes=table("Story Max Over Avg Drifts",["Story","OutputCase","CaseType","StepType","Direction","Max Drift","Avg Drift","Ratio"],
        [{"Story":"+9.00","OutputCase":"RSX","CaseType":"LinRespSpec","StepType":"Max","Direction":"X","Max Drift":"0.003492","Avg Drift":"0.003362","Ratio":"1.039"}],{"Max Drift":"m","Avg Drift":"m"})
    pts=table("Point Object Connectivity",["UniqueName","Story","X","Y","Z"],
        [{"UniqueName":"486","Story":"+4.50","X":"10","Y":"10","Z":"4.5"},
         {"UniqueName":"292","Story":"+9.00","X":"10","Y":"10","Z":"9"}],{"X":"m","Y":"m","Z":"m"})
    cols=table("Column Object Connectivity",["UniqueName","Story","UniquePtI","UniquePtJ","Length"],
        [{"UniqueName":"72","Story":"+9.00","UniquePtI":"486","UniquePtJ":"292","Length":"4.5"}],{"Length":"m"})
    joint=table("Joint Displacements",["UniqueName","Story","OutputCase","CaseType","StepType","StepNumber","Ux","Uy"],
        [{"UniqueName":"486","Story":"+4.50","OutputCase":"Modal","CaseType":"LinModRitz","StepType":"Mode","StepNumber":"1","Ux":"-0.016595","Uy":"0.000768"},
         {"UniqueName":"292","Story":"+9.00","OutputCase":"Modal","CaseType":"LinModRitz","StepType":"Mode","StepNumber":"1","Ux":"-0.025707","Uy":"0.001707"},
         {"UniqueName":"486","Story":"+4.50","OutputCase":"RSX","CaseType":"LinRespSpec","StepType":"Max","StepNumber":"None","Ux":"0.006126","Uy":"0.000817"},
         {"UniqueName":"292","Story":"+9.00","OutputCase":"RSX","CaseType":"LinRespSpec","StepType":"Max","StepNumber":"None","Ux":"0.009545","Uy":"0.001431"}],{"Ux":"m","Uy":"m"})
    return {"schema":"tbdy.next.etabs.generic-source-capture.v1","status":"CAPTURED",
        "model_locked":True,"model_units_code":6,"model_units_unchanged":True,"selection_restored":True,
        "table_reads":{x["table_key"]:x for x in [story,drifts,maxes,pts,cols,joint]}}


class TestDelta(unittest.TestCase):
    def test_etabs_derived_delta_and_real_modal_difference(self):
        result=calculate(fixture())
        self.assertEqual(result["story_deltas"][0]["etabs_derived_delta_m"],"0.0034920")
        self.assertEqual(result["column_modal_shape_differences"][0]["signed_modal_shape_delta_ux_m"],"-0.009112")
        self.assertEqual(result["column_modal_shape_differences"][0]["signed_modal_shape_delta_uy_m"],"0.000939")
        self.assertEqual(result["modal_shape_coverage"]["spectrum_point_max_rows_not_subtracted"],2)
        self.assertEqual(result["tbd_y_eq_4_32_4_34_compliance"],"NOT_PROVEN")

    def test_missing_story_is_not_zero(self):
        result=calculate(fixture())
        self.assertEqual(result["story_delta_coverage"]["uncovered_stories"],["+4.50"])
        self.assertFalse(result["story_delta_coverage"]["all_stories_covered"])

    def test_restore_required(self):
        data=fixture();data["selection_restored"]=False
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_model_locked_required(self):
        data=fixture();data["model_locked"]=False
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_units_required(self):
        data=fixture();data["table_reads"]["Joint Displacements"]["field_metadata"]["units_by_field"]["Ux"]="mm"
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_wrong_story_height_fails(self):
        data=fixture();data["table_reads"]["Story Definitions"]["rows"][0]["Height"]="0"
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_duplicate_drift_fails(self):
        data=fixture();t=data["table_reads"]["Story Drifts"]
        t["rows"].append(copy.deepcopy(t["rows"][0]));t["row_count"]+=1
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_unreconciled_delta_fails(self):
        data=fixture();data["table_reads"]["Story Max Over Avg Drifts"]["rows"][0]["Max Drift"]="0.999"
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_mismatched_story_tabulator_count_fails(self):
        data=fixture();data["table_reads"]["Story Drifts"]["row_count"]=22
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_wrong_spectrum_step_type_fails(self):
        data=fixture();data["table_reads"]["Story Drifts"]["rows"][0]["StepType"]="Mode"
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_multitower_requires_binding(self):
        data=fixture();data["table_reads"]["Story Definitions"]["rows"][1]["Tower"]="T2"
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_duplicate_modal_point_mode_fails(self):
        data=fixture();t=data["table_reads"]["Joint Displacements"]
        t["rows"].append(copy.deepcopy(t["rows"][0]));t["row_count"]+=1
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_nonfinite_rejected(self):
        data=fixture();data["table_reads"]["Story Drifts"]["rows"][0]["Drift"]="NaN"
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_source_status_fails(self):
        data=fixture();data["status"]="PARTIAL"
        with self.assertRaises(DeltaSourceError):calculate(data)

    def test_no_independent_max_fails(self):
        data=fixture();t=data["table_reads"]["Story Max Over Avg Drifts"];t["rows"]=[];t["row_count"]=0
        with self.assertRaises(DeltaSourceError):calculate(data)


if __name__=="__main__":unittest.main()
