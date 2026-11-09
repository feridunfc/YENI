"""Synthetic native ZIP builder. No model data or production arithmetic oracle."""
from collections import Counter
from contextlib import closing
import gzip
from hashlib import sha256
from io import BytesIO
import json
import sqlite3
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def zipped(files):
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as z:
        for name, data in files.items():
            # Rebuilding unchanged synthetic evidence must preserve its identity.
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            z.writestr(info, data, compress_type=ZIP_DEFLATED)
    return output.getvalue()


class SyntheticBank:
    def __init__(self):
        self.members = ["C_SYNTHETIC_1", "C_SYNTHETIC_2"]
        self.cases = {"G": 1, "Q": 1, "RS": 4, "MODAL": 3, "MISSING": 1}
        self.combos = {"SUM": (0, [(0, "G", 1.4), (0, "Q", 1.6)]),
            "RS_SUM": (0, [(0, "G", 1), (0, "RS", 1)]),
            "ENV": (1, [(0, "G", 1), (0, "Q", 1)]),
            "NESTED": (0, [(1, "SUM", 1)])}
        self.calls, self.forces = {}, {}
        self.omitted = set()
        self.context = {"identity_unchanged": True, "restoration_status": "VERIFIED",
            "targeted_capture_attempts_complete": True, "error": None,
            "model_definitions_modified": False, "analysis_rerun_attempted": False}
        self.force_units = 6
        for i, name in enumerate(self.members):
            self.forces[name] = []
            for case, values in (
                ("G", [-100, 2, -3, 4, 5, -6]), ("Q", [-25, -4, 5, -6, -7, 8]),
                # Hand result: 1.4 G + 1.6 Q, all six signed components.
                ("SUM", [-180, -3.6, 3.8, -4, -4.2, 4.4]),
                ("RS", [10, 20, 30, 40, 50, 60]), ("RS_SUM", [10, 20, 30, 40, 50, 60]),
                ("ENV", [10, 20, 30, 40, 50, 60]), ("NESTED", [-180, -3.6, 3.8, -4, -4.2, 4.4]),
                ("MODAL", [1, 2, 3, 4, 5, 6])):
                for j, (station, element, elm_station) in enumerate(((0, "A", 0), (2, "A", 2), (2, "B", 0), (3.3, "B", 1.3))):
                    scale = (i + 1) * (j + 1)
                    self.forces[name].append([name, station, name + element, elm_station, case,
                        "Mode" if case == "MODAL" else "Max" if case in ("RS", "RS_SUM", "ENV") else "Single Value",
                        1 if case == "MODAL" else 0, *[v * scale for v in values]])
            self.call("FrameObj.GetSection", "frame", name, "PropName SAuto pRetVal", ["RECT_SYNTHETIC", "", 0])
            self.call("FrameObj.GetLocalAxes", "frame", name, "Ang Advanced pRetVal", [0, False, 0])
            self.call("FrameObj.GetLabelFromName", "frame", name, "Label Story pRetVal", [name, "SYNTHETIC_STORY", 0])
            self.call("FrameObj.GetPoints", "frame", name, "Point1 Point2 pRetVal", [name + "I", name + "J", 0])
            self.call("FrameObj.GetEndLengthOffset", "frame", name, "AutoOffset Length1 Length2 RZ pRetVal", [True, 0, .7, 0, 0])
            self.call("FrameObj.GetReleases", "frame", name, "II JJ StartValue EndValue pRetVal", [[False]*6, [False]*6, [0]*6, [0]*6, 0])
            self.call("FrameObj.GetTransformationMatrix", "frame", name, "Value pRetVal", [[0,1,0,0,0,1,1,0,0], 0])
            for end, z in (("I", 0), ("J", 4)):
                self.call("PointObj.GetCoordCartesian", "point", name+end, "X Y Z pRetVal", [i*5, 0, z, 0])
                self.call("PointObj.GetRestraint", "point", name+end, "Value pRetVal", [[end == "I"]*6, 0])
        self.call("PropFrame.GetRectangle", "frame_section", "RECT_SYNTHETIC",
            "FileName MatProp T3 T2 Color notes GUID pRetVal", ["", "CONCRETE_SYNTHETIC", .8, .8, 0, "SYNTHETIC", "SYNTHETIC", 0])
        self.call("PropFrame.GetRebarColumn", "column_section", "RECT_SYNTHETIC",
            "MatPropLong MatPropConfine Pattern ConfineType Cover NumberCBars NumberR3Bars NumberR2Bars RebarSize TieSize TieSpacingLongit Number2DirTieBars Number3DirTieBars ToBeDesigned pRetVal",
            ["STEEL_SYNTHETIC", "TIE_STEEL_SYNTHETIC", 1, 1, .04, 4, 5, 5, "20", "10", .15, 4, 4, True, 0])
        self.call("PropMaterial.GetOConcrete", "material", "CONCRETE_SYNTHETIC",
            "Fc IsLightweight FcsFactor SSType SSHysType StrainAtFc StrainUltimate FrictionAngle DilatationalAngle pRetVal",
            [35000, False, 1, 1, 1, .002, .0035, 0, 0, 0])
        for material, fy in (("STEEL_SYNTHETIC", 500000), ("TIE_STEEL_SYNTHETIC", 420000)):
            self.call("PropMaterial.GetORebar_1", "material", material,
                "FY Fu EFy EFu SSType SSHysType StrainAtHardening StrainUltimate FinalSlope UseCaltransSSDefaults pRetVal",
                [fy, 600000, fy, 600000, 1, 1, .01, .1, 0, False, 0])

    def call(self, api, kind, name, fields, values):
        key = (api, kind, name)
        call_id = self.calls.get(key, {}).get("call_id", "SYNTHETIC_" + str(len(self.calls)))
        self.calls[key] = {"schema": "tbdy.full-bank.native-observation.v1", "api": api,
            "entity": {"kind": kind, "name": name}, "call_id": call_id,
            "status": "OBSERVED", "return_code": 0, "units_code": 6,
            "output_names": fields.split(), "raw_response": values}

    def files(self):
        for name, kind in self.cases.items():
            self.call("LoadCases.GetTypeOAPI_1", "case", name,
                "CaseType SubType DesignType DesignTypeOption Auto pRetVal", [kind, 0, 0, 0, 0, 0])
        for name, (operator, terms) in self.combos.items():
            self.call("RespCombo.GetTypeCombo", "combination", name, "ComboType pRetVal", [operator, 0])
            self.call("RespCombo.GetCaseList", "combination", name, "NumberItems CNameType CName SF pRetVal",
                [len(terms), [t[0] for t in terms], [t[1] for t in terms], [t[2] for t in terms], 0])
        fields = "NumberResults Obj ObjSta Elm ElmSta LoadCase StepType StepNum P V2 V3 T M2 M3 pRetVal"
        for name, rows in self.forces.items():
            self.call("Results.FrameForce", "frame", name, fields, [len(rows), *map(list, zip(*rows)), 0])
            self.calls[("Results.FrameForce", "frame", name)]["units_code"] = self.force_units
        files, index, inventory = {}, [], []
        for i, (key, call) in enumerate(self.calls.items()):
            if key in self.omitted:
                continue
            path = "shards/" + str(i) + ".json.gz"
            raw = gzip.compress(encoded(call), mtime=0); files[path] = raw
            index.append({k: call[k] for k in ("api", "entity", "call_id", "status")} |
                         {"path": path, "sha256": sha256(raw).hexdigest()})
            if key[0] == "Results.FrameForce":
                rows = self.forces[key[2]]
                inventory.append({"frame_name": key[2], "call_id": call["call_id"], "shard": path,
                    "status": "OBSERVED", "declared_rows": len(rows), "exact_shape": True,
                    "case_or_combination_rows": dict(Counter(r[4] for r in rows)), "requested_names_without_rows": ["MISSING"]})
        files.update({"targeted-frame-selection.json": encoded({"selected_names": self.members}),
            "shard-index.jsonl": b"\n".join(map(encoded, index)),
            "force-inventory.jsonl": b"\n".join(map(encoded, inventory)),
            "catalogs.json": encoded({"names": {"cases": list(self.cases), "combinations": list(self.combos)},
                "catalog_complete": {"cases": True, "combinations": True}}),
            "collector-summary.json": encoded(self.context)})
        files["archive-manifest.json"] = encoded({"schema": "tbdy.full-bank.archive-manifest.v1",
            "files": {name: {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)} for name, raw in files.items()}})
        return files

    def build(self):
        return zipped(self.files())


def subset(full):
    with ZipFile(BytesIO(full)) as z:
        selected = json.loads(z.read("targeted-frame-selection.json"))["selected_names"]
        files = {name: z.read(name) for name in z.namelist()
                 if name not in ("shard-index.jsonl", "catalogs.json", "collector-summary.json")}
    proof = {"schema": "column-engine.d7b13.native-source-subset.v1", "subset_is_complete_parent": False,
        "parent_archive_sha256": sha256(full).hexdigest(), "selected_frame_names": selected,
        "selected_frame_count": len(selected), "reused_original_member_hashes":
            {name: sha256(raw).hexdigest() for name, raw in files.items()}}
    files["D7B13_SUBSET_PROVENANCE.json"] = encoded(proof)
    return zipped(files)


def historical_db(path):
    with closing(sqlite3.connect(path)) as db:
        db.executescript('CREATE TABLE wall_reactions (id); CREATE TABLE pier_forces (id); '
            'CREATE TABLE d7b3_column_console (story TEXT, output_case TEXT, column_P_kN REAL);')
        db.executemany('INSERT INTO d7b3_column_console VALUES (?,?,?)',
            [("SYNTHETIC_STORY", case, value) for case, value in (("G", -300), ("Q", -75), ("SUM", -540))])
        db.commit()
