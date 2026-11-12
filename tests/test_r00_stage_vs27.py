"""No private ZIP fixtures required; hash-chain rejection tests."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from r00_stage_vs27 import StageError, _base, _files, _patch, _safe_name, PATCHES


class StageTest(unittest.TestCase):
    def test_unsafe_relative_path_rejected(self):
        for name in ("../x", "/abs", "C:/abs", "x\\y"):
            with self.subTest(name=name), self.assertRaises(StageError):
                _safe_name(name)

    def test_base_manifest_bad_sha_rejected(self):
        prefix = "YENI_VS27_TAM_TEST_SURUMU_20261111/"
        manifest = {"files": [{"path": "source/pyproject.toml", "bytes": 1,
                               "sha256": "0" * 64}]}
        files = {prefix + "FILE_MANIFEST.json": json.dumps(manifest).encode(),
                 prefix + "source/pyproject.toml": b"A"}
        with self.assertRaisesRegex(StageError, "BASE_FILE_SHA_MISMATCH"):
            _base(files)

    def test_patch3_old_hash_mismatch_rejected(self):
        rels = PATCHES[2]
        source = {k: b"ORIGINAL" for k in rels}
        test = "test_vs27_3_phase_isolation.py"
        files = {"patch_files/source/" + k: b"NEW" for k in rels}
        files[test] = b"TEST"
        declared = {k: sha256(v).hexdigest() for k, v in files.items()}
        changes = [{"relative": "source/" + k, "old_hash": "0" * 64,
                    "new_hash": sha256(b"NEW").hexdigest()} for k in rels]
        files["FILE_SHA256.json"] = json.dumps({"required_previous_version": "VS27.2",
                                                   "source_sha256": declared,
                                                   "changes": changes}).encode()
        with self.assertRaisesRegex(StageError, "PATCH_OLD_NEW_HASH_MISMATCH"):
            _patch(source, files, 2)

    def test_zip_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "malicious.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("../evil.py", "evil")
            with self.assertRaisesRegex(StageError, "UNSAFE_ZIP_PATH"):
                _files(path)


if __name__ == "__main__":
    unittest.main()
