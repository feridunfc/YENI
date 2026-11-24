"""Cross-run archive and private ETABS session lifetime regressions."""
import gzip
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from tbdy_next.archive_blobs import archive_bytes, copy_archive, store_archive
from tbdy_next.wall_analysis_replay import _private_session


class ArchiveAndSessionTests(unittest.TestCase):
    def test_two_runs_share_a_large_source_and_verify_its_expanded_contents(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = b"x" * (65 * 1024 * 1024)
            digest = sha256(raw).hexdigest()
            paths = []
            for digit in "12":
                path = root / ("RUN-" + digit * 32) / "input.source"
                path.parent.mkdir()
                store_archive(path, raw, digest=digest)
                paths.append(path)
            blobs = list((root / ".archive-blobs").glob("*.gz"))
            self.assertEqual(len(blobs), 1)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertEqual(copy_archive(paths[1]), digest)
            with self.assertRaisesRegex(ValueError, "EXPANDED_SIZE_LIMIT"):
                copy_archive(paths[0], limit=64 * 1024 * 1024)
            blobs[0].write_bytes(gzip.compress(b"short"))
            with self.assertRaisesRegex(ValueError, "SIZE_MISMATCH"):
                archive_bytes(paths[0])

    def test_legacy_bytes_and_invalid_declared_digest(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "input.source"
            with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
                store_archive(out, b"source", digest="0" * 64)
            self.assertFalse(out.exists())
            store_archive(out, b"source")
            self.assertEqual(archive_bytes(out), b"source")

    def test_restore_after_success_failure_and_user_switch(self):
        for action in ("read", "failure", "user switch"):
            with self.subTest(action=action), TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                original, private, other = (root / (n + ".EDB") for n in ("original","private","other"))
                for path in (original, private, other):
                    path.write_bytes(path.name.encode())
                active = [original]
                opened = []
                def change(name):
                    opened.append(Path(name))
                    active[0] = Path(name)
                    return 0
                sap = SimpleNamespace(GetModelFilename=lambda _: str(active[0]), GetPresentUnits=lambda: 6,
                                      GetModelIsLocked=lambda: True, File=SimpleNamespace(OpenFile=change))
                def read():
                    with _private_session(sap, original, private, sha256(original.read_bytes()).hexdigest(), True):
                        self.assertEqual(active[0], private)
                        if action == "failure":
                            raise ValueError("interrupted")
                        if action == "user switch":
                            change(str(other))
                if action == "failure":
                    with self.assertRaisesRegex(ValueError, "interrupted"):
                        read()
                else:
                    read()
                self.assertEqual(active[0], other if action == "user switch" else original)
                self.assertEqual(opened, [private, active[0]])
