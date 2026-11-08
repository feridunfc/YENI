"""VS04-G selected-case restore, source metadata and fail-closed regressions.

All values and ETABS outputs are synthetic; this is NOT live ETABS acceptance.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from tbdy_next.diaphragm_probe import (
    capture_diaphragm_modal_probe,
    review_diaphragm_modal_probe,
    SPECTRUM_MODAL_TABLE,
    DIAPHRAGM_TABLES,
)
from tbdy_next.etabs_modal import ModalCaptureError
from tbdy_next.quick_checks import check_registry


class FakeDb:
    def __init__(self, *, selected=(), restore_fails=False, modal_fails=True,
                 no_static=False, corrupt_metadata=False):
        self.selected=tuple(selected)
        self.original=tuple(selected)
        self.writes=[]
        self.restore_fails=restore_fails
        self.modal_fails=modal_fails
        self.no_static=no_static
        self.corrupt_metadata=corrupt_metadata
        self.available=list(DIAPHRAGM_TABLES)+( [SPECTRUM_MODAL_TABLE] )
        if no_static:
            self.available.remove(DIAPHRAGM_TABLES[1])
        self.records={
           DIAPHRAGM_TABLES[0]:([ "Name", "Type" ], [["D1","Semi Rigid"]]),
           DIAPHRAGM_TABLES[1]:(["Story","UniqueName","Diaphragm"],[
              ["+9.00","A17","D3"],["+4.50","A18","D2"]]),
           DIAPHRAGM_TABLES[2]:(["Story","Label","Diaphragm"],[
              ["+9.00","131","D3"]]),
           SPECTRUM_MODAL_TABLE:(["SpecCase","ModalCase","Mode","Period"],
              [["RSX","Modal","1","0.47"],["RSY","Modal","1","0.47"]]),
        }

    def GetLoadCasesSelectedForDisplay(self):
        return len(self.selected),list(self.selected),0

    def SetLoadCasesSelectedForDisplay(self,values):
        target=tuple(x for x in values if x)
        self.writes.append(target)
        if not (self.restore_fails and target==self.original):
            self.selected=target
        return 0

    def GetAvailableTables(self):
        return len(self.available),self.available,self.available,[0]*len(self.available),0

    def GetAllFieldsInTable(self,key):
        fields=self.records[key][0]
        if self.corrupt_metadata and key==DIAPHRAGM_TABLES[0]:
            return 1,len(fields),fields,fields,[""]*len(fields),[""]*len(fields),[0]*len(fields),1
        return 1,len(fields),fields,fields,[""]*len(fields),[""]*len(fields),[0]*len(fields),0

    def GetTableForDisplayArray(self,key,*args):
        if key==SPECTRUM_MODAL_TABLE and (self.selected != ("RSX","RSY")
                                          or self.modal_fails):
            return None,1,[],0,[],1
        fields,rows=self.records[key]
        flat=[c for row in rows for c in row]
        return None,1,fields,len(rows),flat,0


class FakeSap:
    def __init__(self, *, units_after=None, locked=True, **opts):
        self.DatabaseTables=FakeDb(**opts)
        self.locked=locked
        self.calls=0
        self.units_after=units_after

    def GetModelIsLocked(self):
        return self.locked

    def GetPresentUnits(self):
        self.calls+=1
        return self.units_after if self.calls>1 and self.units_after is not None else 6


class Vs04GTests(unittest.TestCase):
    def test_selected_modal_info_becomes_readable_while_static_tables_unchanged(self):
        sap=FakeSap(modal_fails=False)
        result=capture_diaphragm_modal_probe(sap)
        self.assertEqual(sap.DatabaseTables.selected,())
        self.assertEqual(sap.DatabaseTables.writes,[("RSX","RSY"),()])
        self.assertEqual(result["spectrum_modal_original_selection"]["status"],
                         "CAPTURE_ERROR")
        self.assertEqual(result["spectrum_modal_selected_cases"]["status"],
                         "CAPTURED")
        out=review_diaphragm_modal_probe(result)
        self.assertEqual(out["source_success_count"],4)
        self.assertEqual(out["source_expected_count"],5)
        self.assertFalse(out["accidental_eccentricity_applied_proven"])
        self.assertEqual(out["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(len(check_registry()),12)

    def test_failed_selected_modal_info_is_preserved_not_dropped(self):
        sap=FakeSap(modal_fails=True)
        result=capture_diaphragm_modal_probe(sap)
        self.assertEqual(sap.DatabaseTables.selected,())
        out=review_diaphragm_modal_probe(result)
        self.assertEqual(out["source_success_count"],3)
        self.assertIn("ETABS_TABLE_NOT_CAPTURED",out["tables"][-1]["reason_codes"])
        self.assertEqual(out["engineering_release"],"NOT_READY")

    def test_missing_static_table_is_not_fabricated(self):
        result=capture_diaphragm_modal_probe(FakeSap(no_static=True))
        out=review_diaphragm_modal_probe(result)
        self.assertEqual(out["tables"][1]["source_status"],"NOT_PROVEN")
        self.assertEqual(out["tables"][1]["rows"],0)

    def test_corrupted_metadata_blocks_only_respective_source(self):
        result=capture_diaphragm_modal_probe(FakeSap(corrupt_metadata=True))
        out=review_diaphragm_modal_probe(result)
        self.assertEqual(out["tables"][0]["source_status"],"NOT_PROVEN")
        self.assertEqual(out["source_success_count"],2)

    def test_failed_restoration_rejects_whole_capture(self):
        sap=FakeSap(restore_fails=True)
        with self.assertRaisesRegex(ModalCaptureError,"RESTORE_FAILED"):
            capture_diaphragm_modal_probe(sap)
        self.assertNotEqual(sap.DatabaseTables.selected,())

    def test_unlocked_and_units_changed_rejected(self):
        with self.assertRaisesRegex(ModalCaptureError,"LOCKED"):
            capture_diaphragm_modal_probe(FakeSap(locked=False))
        with self.assertRaisesRegex(ModalCaptureError,"UNITS"):
            capture_diaphragm_modal_probe(FakeSap(units_after=7))

    def test_original_selection_already_contains_both_cases(self):
        sap=FakeSap(selected=("RSX","RSY"),modal_fails=False)
        out=capture_diaphragm_modal_probe(sap)
        self.assertEqual(sap.DatabaseTables.writes,[])
        self.assertEqual(out["spectrum_modal_original_selection"]["status"],
                         "CAPTURED")
        self.assertEqual(review_diaphragm_modal_probe(out)["source_success_count"],5)

    def test_tampered_restore_flag_never_approved(self):
        out=capture_diaphragm_modal_probe(FakeSap(modal_fails=False))
        out["display_selection_restored"]=False
        reviewed=review_diaphragm_modal_probe(out)
        self.assertEqual(reviewed["status"],"SOURCE_REJECTED")

    def test_invalid_case_names_rejected_before_setter(self):
        sap=FakeSap()
        with self.assertRaises(ModalCaptureError):
            capture_diaphragm_modal_probe(sap,spectrum_cases=("RSX","RSX"))
        self.assertEqual(sap.DatabaseTables.writes,[])


if __name__=="__main__":
    unittest.main()
