"""Adapt Column-Engine's sealed native bank reader to YENI's offline boundary.

Source: Column-Engine 4f0afbeb / recipe_v11.bank, r6_source_bank and D7-B13 audit.
No COM. No extraction to user-controlled paths. Full banks and the D7-B13
byte-preserving subset have distinct integrity contracts.
"""
from __future__ import annotations

from collections import defaultdict
import gzip
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_NATIVE_BYTES = 16 * 1024 * 1024


class BankError(ValueError):
    """Missing, malformed or contradictory native evidence."""


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def digest(value) -> str:
    return sha256(canonical(value)).hexdigest()


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise BankError("DUPLICATE_JSON_KEY:" + key)
        out[key] = value
    return out


def decode(raw):
    def invalid(value):
        raise BankError("NONFINITE_JSON:" + value)
    def floating(value):
        number = float(value)
        if not math.isfinite(number):
            raise BankError("NONFINITE_JSON_NUMBER")
        return number
    return json.loads(raw, object_pairs_hook=_unique, parse_constant=invalid, parse_float=floating)


def finite(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise BankError("INVALID_NUMBER:" + label)
    return value


def identity(value, label):
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 200:
        raise BankError("INVALID_ID:" + label)
    return value


def native_observation(z, manifest, item, api, kind, name, expected_fields=None, *, entity_key="name", expected_args=None):
    path = item.get("path")
    if not isinstance(path, str) or path not in manifest["files"] or not path.startswith("shards/"):
        raise BankError("NATIVE_SHARD_UNBOUND:" + api)
    raw = z.read(path)
    actual = sha256(raw).hexdigest()
    if actual != manifest["files"][path]["sha256"] or actual != item.get("sha256"):
        raise BankError("NATIVE_SHARD_HASH_MISMATCH:" + api)
    with gzip.GzipFile(fileobj=BytesIO(raw)) as stream:
        data = stream.read(MAX_NATIVE_BYTES + 1)
    if len(data) > MAX_NATIVE_BYTES:
        raise BankError("NATIVE_SHARD_TOO_LARGE")
    obj = decode(data)
    if (not isinstance(obj, dict) or obj.get("schema") != "tbdy.full-bank.native-observation.v1"
            or obj.get("call_id") != item.get("call_id") or obj.get("api") != api
            or obj.get("entity") != ({"kind": kind, entity_key: name} if entity_key else {"kind": kind})
            or obj.get("status") != "OBSERVED" or type(obj.get("return_code")) is not int
            or obj["return_code"] != 0 or type(obj.get("units_code")) is not int
            or obj["units_code"] != 6):
        raise BankError("NATIVE_IDENTITY_OR_UNITS_MISMATCH:" + api)
    if expected_args is not None and canonical(obj.get("args")) != canonical(expected_args):
        raise BankError("NATIVE_REQUEST_ARGUMENTS_MISMATCH:" + api)
    fields, values = obj.get("output_names"), obj.get("raw_response")
    if (not isinstance(fields, list) or not isinstance(values, list) or not fields
            or any(not isinstance(x, str) for x in fields) or len(set(fields)) != len(fields)
            or len(fields) != len(values) or type(values[-1]) is not int or values[-1] != 0
            or (expected_fields is not None and tuple(fields) != tuple(expected_fields))):
        raise BankError("NATIVE_OUTPUT_SIGNATURE_MISMATCH:" + api)
    return dict(zip(fields, values)), {"api": api, "call_id": item["call_id"],
        "shard_path": path, "shard_sha256": actual, "entity_kind": kind,
        "entity_name": name, "units_code": 6}


class NativeArchive:
    def __init__(self, raw: bytes):
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ARCHIVE_BYTES:
            raise BankError("ARCHIVE_SIZE_INVALID")
        self.raw = raw
        self.sha256 = sha256(raw).hexdigest()
        try:
            self.z = ZipFile(BytesIO(raw))
        except BadZipFile as exc:
            raise BankError("INVALID_ZIP") from exc
        try:
            self._verify()
        except Exception:
            self.z.close()
            raise

    def _verify(self):
        info = self.z.infolist()
        names = {i.filename for i in info}
        if (not info or len(info) > 20000 or len(names) != len(info)
                or sum(i.file_size for i in info) > MAX_EXPANDED_BYTES
                or any(i.file_size > MAX_ARCHIVE_BYTES or i.is_dir() or "\\" in i.filename
                       or PurePosixPath(i.filename).is_absolute() or ".." in PurePosixPath(i.filename).parts
                       for i in info)):
            raise BankError("ARCHIVE_MEMBERS_INVALID")
        self.manifest = self.json("archive-manifest.json")
        files = self.manifest.get("files")
        if (self.manifest.get("schema") != "tbdy.full-bank.archive-manifest.v1"
                or not isinstance(files, dict)):
            raise BankError("ARCHIVE_MANIFEST_INVALID")
        self.subset = self.json("D7B13_SUBSET_PROVENANCE.json") if "D7B13_SUBSET_PROVENANCE.json" in names else None
        if self.subset is not None:
            hashes = self.subset.get("reused_original_member_hashes")
            if (self.subset.get("schema") != "column-engine.d7b13.native-source-subset.v1"
                    or self.subset.get("subset_is_complete_parent") is not False
                    or not isinstance(hashes, dict)
                    or set(hashes) | {"D7B13_SUBSET_PROVENANCE.json"} != names):
                raise BankError("SUBSET_MANIFEST_INVALID")
        else:
            if set(files) | {"archive-manifest.json"} != names:
                raise BankError("MANIFEST_FILES_MISMATCH")
            hashes = {n: f["sha256"] for n, f in files.items()}
        for name, expected in hashes.items():
            value = self.z.read(name)
            if (sha256(value).hexdigest() != expected or
                    (name != "archive-manifest.json" and
                     (files.get(name, {}).get("sha256") != expected or files[name].get("bytes") != len(value)))):
                raise BankError("ARCHIVE_MEMBER_HASH_OR_SIZE_MISMATCH:" + name)
        self.verified_member_count = len(hashes)
        self.selection = self.json("targeted-frame-selection.json")
        selected = self.selection.get("selected_names")
        if (not isinstance(selected, list) or not 0 < len(selected) <= 2000
                or any(not isinstance(n, str) for n in selected) or len(set(selected)) != len(selected)):
            raise BankError("SELECTED_COLUMN_POPULATION_INVALID")
        self.selected = tuple(identity(n, "selected_column") for n in selected)
        if self.subset is not None and (self.subset.get("selected_frame_names") != selected
                or self.subset.get("selected_frame_count") != len(selected)):
            raise BankError("SUBSET_SELECTION_MISMATCH")
        self.index = defaultdict(list)
        if "shard-index.jsonl" in names:
            entries = self.jsonlines("shard-index.jsonl")
        else:
            entries = []
            # D7-B13 has original shard bytes but no complete parent index.
            for name in sorted(n for n in names if n.startswith("shards/") and n.endswith(".json.gz")):
                with gzip.GzipFile(fileobj=BytesIO(self.z.read(name))) as stream:
                    raw = stream.read(MAX_NATIVE_BYTES + 1)
                if len(raw) > MAX_NATIVE_BYTES:
                    raise BankError("NATIVE_SHARD_TOO_LARGE")
                obj = decode(raw)
                entries.append({k: obj.get(k) for k in ("api", "entity", "call_id", "status")} |
                    {"path": name, "sha256": files[name]["sha256"]})
        for item in entries:
            if not isinstance(item, dict) or not isinstance(item.get("entity"), dict):
                continue  # Global calls have no entity and cannot fill member inputs.
            entity = item["entity"]
            self.index[(item.get("api"), entity.get("kind"), entity.get("name", entity.get("key")))].append(item)

    def json(self, name):
        try:
            return decode(self.z.read(name))
        except KeyError as exc:
            raise BankError("ARCHIVE_FILE_MISSING:" + name) from exc

    def jsonlines(self, name):
        return [decode(line) for line in self.z.read(name).splitlines() if line.strip()]

    def native(self, api, kind, name, fields=None, *, entity_key="name", expected_args=None):
        items = self.index.get((api, kind, name), ())
        if len(items) > 1:
            raise BankError("AMBIGUOUS_NATIVE_CALL:" + api + ":" + str(name))
        if not items or items[0].get("status") != "OBSERVED":
            return None
        return native_observation(self.z, self.manifest, items[0], api, kind, name, fields,
            entity_key=entity_key, expected_args=expected_args)

    def table(self, key, required_fields, *, required_units=None, max_records=20000):
        """Read a sealed, complete display table; schema-only evidence is insufficient."""
        # Only the regular point-object displacement table has a larger opt-in
        # budget. The native gzip byte limit and ordinary table limit remain.
        if (type(max_records) is not int or not 0 < max_records <= 50000
                or (max_records > 20000 and key != "Joint Displacements")):
            raise BankError("NATIVE_TABLE_RECORD_BUDGET_INVALID")
        api = "DatabaseTables.GetTableForDisplayArray"
        items = self.index.get((api, "table", key), ())
        if len(items) > 1:
            raise BankError("AMBIGUOUS_NATIVE_TABLE:" + key)
        if not items or items[0].get("status") != "OBSERVED":
            return None
        values, proof = native_observation(self.z, self.manifest, items[0], api,
            "table", key, entity_key="key")
        n, fields, cells = (values.get(k) for k in ("NumberRecords", "FieldsKeysIncluded", "TableData"))
        if (type(n) is not int or not 0 <= n <= max_records or not isinstance(fields, list)
                or not fields or any(not isinstance(f, str) or not f for f in fields)
                or len(set(fields)) != len(fields) or not set(required_fields) <= set(fields)
                or not isinstance(cells, list) or len(cells) != n * len(fields)
                or any(c is not None and not isinstance(c, str) for c in cells)):
            raise BankError("NATIVE_TABLE_SHAPE_OR_FIELDS_INVALID:" + key)
        rows = [dict(zip(fields, cells[i:i + len(fields)])) for i in range(0, len(cells), len(fields))]
        proof = proof | {"table_key": key, "fields": fields, "row_count": n}
        if required_units:
            schema_api = "DatabaseTables.GetAllFieldsInTable"
            schemas = self.index.get((schema_api, "table", key), ())
            if len(schemas) != 1 or schemas[0].get("status") != "OBSERVED":
                raise BankError("TABLE_FIELD_UNITS_NOT_OBSERVED:" + key)
            data, schema_proof = native_observation(self.z, self.manifest, schemas[0],
                schema_api, "table", key, entity_key="key")
            count, keys, units = (data.get(k) for k in ("NumberFields", "FieldKey", "UnitsString"))
            if (type(count) is not int or count <= 0 or not isinstance(keys, list)
                    or not isinstance(units, list) or len(keys) != count or len(units) != count
                    or any(not isinstance(k, str) for k in keys) or len(set(keys)) != count
                    or type(data.get("TableVersion")) is not int or type(values.get("TableVersion")) is not int
                    or data.get("TableVersion") != values.get("TableVersion")
                    or any(dict(zip(keys, units)).get(k) != u for k, u in required_units.items())):
                raise BankError("TABLE_FIELD_UNITS_OR_VERSION_INVALID:" + key)
            proof["field_units"] = dict(zip(keys, units))
            proof["schema_source"] = schema_proof
        return rows, proof

    def close(self):
        self.z.close()
