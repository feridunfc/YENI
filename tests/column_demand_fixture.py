"""Synthetic ETABS design-summary schema and independent signed force example."""
from column_bank_fixture import SyntheticBank

TABLE = "Concrete Column Design Summary - TS 500-2000(R2018)"
FIELDS = ("Story Label UniqueName DesignSect Station DesignOpt Status PMMRatio PMMCombo "
          "AsMin As BarAs CornerBarAs VMajCombo VMajRebar VMinCombo VMinRebar WarnMsg ErrMsg").split()


class DesignBank(SyntheticBank):
    def __init__(self):
        super().__init__()
        # Independent hand oracle, not calculated by the production evaluator.
        values = {"G": [-100, 10, -20, 3, 40, -50], "Q": [-25, -2, 6, -1, -5, 8],
                  "SUM": [-180, 10.8, -18.4, 2.6, 48, -57.2]}
        for member, rows in self.forces.items():
            for case, force in values.items():
                for scale, row in enumerate((r for r in rows if r[4] == case), 1):
                    row[7:] = [v * scale for v in force]
        self.design_rows = []
        for member in self.members:
            for station in ("0", "2", "2", "3.3"):
                self.design_rows.append(dict(zip(FIELDS, [
                    "SYNTHETIC_STORY", member, member, "RECT_SYNTHETIC", station,
                    "Design", "No Message", None, "SUM", ".0064", ".0064", ".000533", ".000533",
                    "SUM", ".00091", "RS_SUM", ".00091", "No Message", "No Message"])))
        self.units = {f: "m" if f == "Station" else "" for f in FIELDS}
        self.table_fields = list(FIELDS)
        self.truncate = False

    def files(self):
        cells = [row.get(field) for row in self.design_rows for field in self.table_fields]
        if self.truncate:
            cells.pop()
        self.call("DatabaseTables.GetTableForDisplayArray", "table", TABLE,
            "FieldKeyList TableVersion FieldsKeysIncluded NumberRecords TableData pRetVal",
            [[], 1, self.table_fields, len(self.design_rows), cells, 0])
        self.call("DatabaseTables.GetAllFieldsInTable", "table", TABLE,
            "TableVersion NumberFields FieldKey FieldName Description UnitsString IsImportable pRetVal",
            [1, len(FIELDS), list(FIELDS), list(FIELDS), ["SYNTHETIC"] * len(FIELDS),
             [self.units[f] for f in FIELDS], [False] * len(FIELDS), 0])
        for api in ("DatabaseTables.GetTableForDisplayArray", "DatabaseTables.GetAllFieldsInTable"):
            self.calls[(api, "table", TABLE)]["entity"] = {"kind": "table", "key": TABLE}
        return super().files()
