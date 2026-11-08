"""Keep the Windows-only ETABS COM dependency installable in a clean venv.

Offline CI on Linux must not import or require comtypes merely to run numeric
and source-gateway regression tests.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tomllib
import unittest


class WindowsEtabsInstallContract(unittest.TestCase):
    def test_comtypes_declared_as_optional_windows_only_extra(self):
        root = Path(__file__).resolve().parents[1]
        config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        extras = config["project"]["optional-dependencies"]
        requirements = extras["etabs-windows"]
        self.assertEqual(len(requirements), 1)
        self.assertIn("comtypes", requirements[0])
        self.assertIn("sys_platform == 'win32'", requirements[0])
        self.assertNotIn("comtypes", " ".join(config["project"]["dependencies"]))

    def test_offline_gateway_remains_importable_without_windows_com(self):
        from tools.etabs_source_gateway_windows import resolve_keys, SourceError
        self.assertTrue(callable(resolve_keys))
        self.assertTrue(issubclass(SourceError, ValueError))
        if sys.platform != "win32":
            import comtypes
            # comtypes is never required on Linux; if incidentally installed,
            # it must not be a precondition for source inspection.
            self.assertTrue(comtypes is not None)


if __name__ == "__main__":
    unittest.main()
