"""Run the repository's offline regressions on Windows or Linux."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node", help="Path to the Node.js executable")
    args = parser.parse_args()
    node = shutil.which(args.node)
    if node is None:
        parser.error(f"Node.js executable not found: {args.node}")

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PATH"] = os.pathsep.join((str(Path(sys.executable).parent), env.get("PATH", "")))
    env["PYTHONUTF8"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    python = (sys.executable, "-B")

    def run(label, *command, check=True):
        print(label, flush=True)
        return subprocess.run(command, cwd=ROOT, env=env, check=check).returncode

    try:
        run("Git revision", "git", "rev-parse", "HEAD")
        run("Working tree", "git", "status", "--short", "--branch")
        run("Patch whitespace", "git", "-c", "core.safecrlf=false", "diff", "--check", "HEAD")
        run(
            "Installed package and import path",
            *python, "-I", "-c",
            "from pathlib import Path\n"
            "import tbdy_next\n"
            "expected = Path('src/tbdy_next').resolve()\n"
            "actual = Path(tbdy_next.__file__).resolve().parent\n"
            "print(actual)\n"
            "if actual != expected:\n"
            "    raise SystemExit(f'Expected the current editable checkout: {expected}')",
        )
        run("Python tests", *python, "-m", "unittest", "discover", "-s", "tests", "-v")
        run("Python compilation", *python, "-m", "compileall", "-q", "src")
        run("Node.js runtime", node, "--version")
        run("JavaScript syntax", node, "--check", "src/tbdy_next/static/column.js")
        for test in sorted((ROOT / "tests").glob("test_*.cjs")):
            name = str(test.relative_to(ROOT))
            run(name, node, name)

        with TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "golden.json"
            result = run(
                "Golden regression and engineering acceptance",
                *python, "-m", "tbdy_next.cli", "inspect-golden-regression",
                "--require-complete", "--json", report_path, check=False,
            )
            if result not in (0, 3):
                return result
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report["acceptance_eligible"] is not (result == 0):
                raise ValueError("Golden report and command exit status disagree.")
            print(json.dumps({
                "golden_record_count": report["record_count"],
                "classification_counts": report["classification_counts"],
                "acceptance_eligible": report["acceptance_eligible"],
                "engineering_release": report["engineering_release"],
            }, indent=2))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Offline pipeline failed: {exc}", file=sys.stderr)
        return 1

    print("OFFLINE_SOFTWARE_REGRESSIONS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
