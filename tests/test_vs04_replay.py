"""Offline VS04 RAW replay: source immutability, deterministic output."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.replay_vs04_raw import replay_raw_file
from test_vs04_numerics import numeric_source


class Vs04OfflineReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw_file = self.root / "VS04_RAW_fixture.json"
        self.output_file = self.root / "VS04_REPLAY_fixture.json"
        self.raw_file.write_text(
            json.dumps(numeric_source(), ensure_ascii=False, sort_keys=True),
            encoding="utf-8")
        self.original = self.raw_file.read_bytes()

    def tearDown(self):
        self.tmp.cleanup()

    def test_replay_reports_five_candidates_and_preserves_source(self):
        result = replay_raw_file(self.raw_file, self.output_file)
        self.assertEqual(result["numeric_source_review"]["observed_component_count"], 5)
        self.assertEqual(result["source_schema_review"]["captured_table_count"], 3)
        self.assertEqual(result["engineering_release"], "NOT_READY")
        self.assertEqual(result["formal_compliance"], "NOT_PROVEN")
        self.assertFalse(result["source_raw_included"])
        self.assertEqual(self.original, self.raw_file.read_bytes())
        self.assertEqual(json.loads(self.output_file.read_text(encoding="utf-8")), result)

    def test_replay_is_deterministic(self):
        first = replay_raw_file(self.raw_file, self.output_file)
        text1 = self.output_file.read_bytes()
        second = replay_raw_file(self.raw_file, self.output_file)
        self.assertEqual(first, second)
        self.assertEqual(text1, self.output_file.read_bytes())

    def test_no_overwrite_of_raw_file(self):
        with self.assertRaisesRegex(ValueError, "Cannot overwrite"):
            replay_raw_file(self.raw_file, self.raw_file)
        self.assertEqual(self.original, self.raw_file.read_bytes())

    def test_invalid_source_rejected(self):
        self.raw_file.write_text("not a json", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
            replay_raw_file(self.raw_file, self.output_file)
        self.assertFalse(self.output_file.exists())

    def test_missing_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            replay_raw_file(self.root / "missing.json", self.output_file)


if __name__ == "__main__":
    unittest.main()
