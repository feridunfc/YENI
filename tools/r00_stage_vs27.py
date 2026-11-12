"""R00: verify 4 pinned VS27 ZIPs and stage sources, without touching the repo.

Codespaces offline input, no ETABS/COM/analysis. Requires all four archives.
The resulting staging directory is only a review candidate, not accepted code.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile

PACKAGES = (
    "YENI_VS27_TAM_TEST_SURUMU_20261111.zip",
    "YENI_VS27_1_SECIM_KORUMA_DUZELTMESI_20261112.zip",
    "YENI_VS27_2_GECICI_CIKTI_SECIMI_DUZELTMESI_20261112.zip",
    "YENI_VS27_3_GORUNTU_CIKTI_EVRE_DUZELTMESI_20261112.zip",
)
PREFIX = "YENI_VS27_TAM_TEST_SURUMU_20261111/"
PATCHES = (
    ("tools/capture_all_columns_windows.py", "tools/windows_column_recipe/Capture-YeniAllColumns.ps1"),
    ("tools/capture_all_columns_windows.py", "tools/windows_column_recipe/Capture-YeniAllColumns.ps1", "tools/audit_column_batch.py"),
    ("tools/capture_all_columns_windows.py", "tools/audit_column_batch.py"),
)
PATCH_TESTS = ("test_vs27_display_selection_guard.py", "test_vs27_2_temporary_selection.py",
               "test_vs27_3_phase_isolation.py")
MAX_BYTES = 24 * 1024 * 1024


class StageError(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe_name(name):
    pure = PurePosixPath(name)
    if (not name or name.startswith(("/", "\\")) or ":" in name or "\\" in name
            or ".." in pure.parts or pure.is_absolute()):
        raise StageError("UNSAFE_ZIP_PATH:" + name)
    return pure


def _files(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 3000:
            raise StageError("DUPLICATE_OR_TOO_MANY_ZIP_MEMBERS")
        data = {}
        size = 0
        for info in z.infolist():
            _safe_name(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise StageError("SYMLINK_IN_PACKAGE")
            if info.is_dir():
                continue
            if info.file_size > MAX_BYTES:
                raise StageError("OVERSIZE_PACKAGE_MEMBER")
            size += info.file_size
            if size > 64 * 1024 * 1024:
                raise StageError("OVERSIZE_PACKAGE")
            data[info.filename] = z.read(info.filename)
        return data


def _json(data, name):
    try:
        return json.loads(data[name])
    except (KeyError, ValueError) as exc:
        raise StageError("MISSING_OR_BAD_MANIFEST:" + name) from exc


def _base(files):
    manifest = _json(files, PREFIX + "FILE_MANIFEST.json")
    declared = manifest.get("files")
    if not isinstance(declared, list) or not declared:
        raise StageError("BASE_MANIFEST_EMPTY")
    source = {}
    for item in declared:
        name = item.get("path")
        if not isinstance(name, str) or not isinstance(item.get("sha256"), str):
            raise StageError("BASE_MANIFEST_ENTRY_BAD")
        actual_name = PREFIX + name
        if actual_name not in files:
            raise StageError("BASE_FILE_MISSING:" + name)
        data = files[actual_name]
        if sha(data) != item["sha256"] or len(data) != item.get("bytes"):
            raise StageError("BASE_FILE_SHA_MISMATCH:" + name)
        if not name.startswith("source/"):
            continue
        rel = name[len("source/"):]
        _safe_name(rel)
        if "__pycache__" in PurePosixPath(rel).parts or rel.endswith(".pyc"):
            continue
        source[rel] = data
    if not source or "pyproject.toml" not in source or "tools/audit_column_batch.py" not in source:
        raise StageError("BASE_SOURCE_INCOMPLETE")
    return source


def _patch(source, files, index):
    manifest = _json(files, "FILE_SHA256.json")
    if index > 0 and manifest.get("required_previous_version") != "VS27." + str(index):
        raise StageError("PATCH_SEQUENCE_INCORRECT:" + str(index + 1))
    hashes = manifest.get("files", manifest.get("source_sha256"))
    if not isinstance(hashes, dict):
        raise StageError("PATCH_MANIFEST_FILE_HASHES_MISSING")
    for name, expected in hashes.items():
        if name not in files or sha(files[name]) != expected:
            raise StageError("PATCH_FILE_SHA_MISMATCH:" + name)
    if index == 0:
        # VS27.1 supplies new hashes but does not include old/new entries.
        if manifest.get("base_vs27_sha256") != "ccf8a4beb25c60a8f113adb50bce8c7a5f0f377d407f77538b16f7977833774f":
            raise StageError("PATCH1_SOURCE_IDENTITY_INVALID")
    changes = manifest.get("changes", [])
    diff_by_rel = {x.get("relative"): x for x in changes if isinstance(x, dict)}
    for rel in PATCHES[index]:
        archive_name = "patch_files/source/" + rel
        if archive_name not in files or rel not in source:
            raise StageError("PATCH_SOURCE_PATH_MISSING:" + rel)
        old = source[rel]
        new = files[archive_name]
        change = diff_by_rel.get("source/" + rel)
        if change:
            if change.get("old_hash") != sha(old) or change.get("new_hash") != sha(new):
                raise StageError("PATCH_OLD_NEW_HASH_MISMATCH:" + rel)
        elif index != 0:
            raise StageError("UNLISTED_PATCH_CHANGE:" + rel)
        source[rel] = new
    test = PATCH_TESTS[index]
    if test not in files:
        raise StageError("PATCH_TEST_MISSING:" + test)
    source["tests/" + test] = files[test]
    if "tests/" + test in source and sha(source["tests/" + test]) != hashes[test]:
        raise StageError("PATCH_TEST_SHA_MISMATCH:" + test)
    return {"patch": index + 1, "changed_source_files": list(PATCHES[index]),
            "test": test, "verified": True}


def stage(inputs, out, manifest_path, *, verify_only=False):
    config = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    hashes = config["source_zips"]
    archives = {}
    for name in PACKAGES:
        path = Path(inputs) / name
        if not path.is_file():
            raise StageError("PINNED_PACKAGE_MISSING:" + name)
        with path.open("rb") as stream:
            h = hashlib.file_digest(stream, "sha256").hexdigest()
        if h != hashes.get(name):
            raise StageError("PACKAGE_SHA_MISMATCH:" + name)
        archives[name] = _files(path)
    source = _base(archives[PACKAGES[0]])
    delta = []
    for i, name in enumerate(PACKAGES[1:]):
        delta.append(_patch(source, archives[name], i))
    if out.exists():
        raise StageError("STAGING_OUTPUT_ALREADY_EXISTS")
    if not verify_only:
        out.mkdir(parents=True, exist_ok=False)
        for rel, data in source.items():
            p = out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    return {"schema": "tbdy.next.r00-stage.v1", "source_files": len(source),
            "source_tree_staged": not verify_only,
            "source_content_sha256": sha(json.dumps({k: sha(v) for k, v in sorted(source.items())},
                                                   sort_keys=True).encode()),
            "patch_sequence": delta, "engineering_release": "NOT_READY"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", type=Path,
                        default=Path(__file__).resolve().parents[1] / "config/r00_vs27_artifacts.json")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(stage(args.inputs, args.out, args.manifest, verify_only=args.verify_only),
                         indent=2, sort_keys=True))
        return 0
    except (StageError, OSError, zipfile.BadZipFile, ValueError) as exc:
        print(json.dumps({"stage_status": "REJECTED", "reason": str(exc)}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
