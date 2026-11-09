"""Small independent rigid-rotation oracle, with rounded ETABS table cells."""
from column_joint_fixture import JointBank

DISPLACEMENTS = "Joint Displacements"
STATIC = "Load Case Definitions - Linear Static"
FIELDS = "Story Label UniqueName OutputCase CaseType StepType StepNumber StepLabel Ux Uy Uz Rx Ry Rz".split()


class KinematicsBank(JointBank):
    def __init__(self):
        super().__init__()
        self.displacement_rows = []
        # Rigid small rotation: alpha2=.0015, alpha3=.002; plus translation.
        for name, ux, uy in (("P0", ".100000", "-.200000"), ("P1", ".108000", "-.206000"),
                            ("P2", ".116000", "-.212000")):
            self.displacement_rows.append(dict(zip(FIELDS, ["SYNTHETIC", "UNRELATED_LABEL", name, "SUM", "Combination",
                None, None, None, ux, uy, ".003000", ".001500", ".002000", "0"])))
        self.displacement_units = {c: "m" if c.startswith("U") else "rad" for c in ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz")}
        self.static_rows = [dict(Name="G", StiffType="Nonlinear Case", NonlinCase="None"),
            dict(Name="Q", StiffType="P-Delta", NonlinCase=None),
            dict(Name="Q", StiffType=None, NonlinCase=None)]

    def table(self, name, fields, rows, units):
        self.call("DatabaseTables.GetTableForDisplayArray", "table", name,
            "FieldKeyList TableVersion FieldsKeysIncluded NumberRecords TableData pRetVal",
            [[], 1, fields, len(rows), [r.get(f) for r in rows for f in fields], 0])
        self.call("DatabaseTables.GetAllFieldsInTable", "table", name,
            "TableVersion NumberFields FieldKey FieldName Description UnitsString IsImportable pRetVal",
            [1, len(fields), fields, fields, ["SYNTHETIC"]*len(fields), [units.get(f, "") for f in fields], [False]*len(fields), 0])
        for api in ("DatabaseTables.GetTableForDisplayArray", "DatabaseTables.GetAllFieldsInTable"):
            self.calls[(api, "table", name)]["entity"] = {"kind": "table", "key": name}

    def files(self):
        self.table(DISPLACEMENTS, FIELDS, self.displacement_rows, self.displacement_units)
        self.table(STATIC, ["Name", "StiffType", "NonlinCase"], self.static_rows, {})
        return super().files()
