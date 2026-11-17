"""Install the wheel in a clean environment and replay the drift report test."""

import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import venv


TESTS = Path(__file__).resolve().parents[1] / "tests"
DRIFT_REPORT_TEST = (
    "test_vs06_c2_drift_scenario.Vs06C2HttpIntegration."
    "test_live_once_then_scenario_and_json_html_no_com"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel_directory", type=Path)
    args = parser.parse_args()
    wheels = sorted(args.wheel_directory.resolve().glob("tbdy_next_engine-*.whl"))
    if len(wheels) != 1:
        parser.error("Expected exactly one YENI wheel.")

    with TemporaryDirectory() as temporary:
        isolated = Path(temporary)
        environment = isolated / "venv"
        venv.create(environment, with_pip=True)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run(
            [
                python, "-I", "-m", "pip", "install", "--disable-pip-version-check",
                "--no-index", "--no-deps", str(wheels[0]),
            ],
            cwd=isolated, check=True,
        )
        subprocess.run(
            [
                python, "-I", "-B", "-c",
                "from pathlib import Path\n"
                "import sys\n"
                "import unittest\n"
                "import tbdy_next\n"
                "package = Path(tbdy_next.__file__).resolve()\n"
                "if not package.is_relative_to(Path(sys.prefix).resolve()):\n"
                "    raise SystemExit(f'Expected the isolated wheel installation, got {package}')\n"
                "sys.path.append(sys.argv[1])\n"
                "unittest.main(module=None, argv=['unittest', '-v', sys.argv[2]])\n",
                str(TESTS), DRIFT_REPORT_TEST,
            ],
            cwd=isolated, check=True,
        )


if __name__ == "__main__":
    main()
