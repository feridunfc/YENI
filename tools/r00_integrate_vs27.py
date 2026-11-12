"""Import the verified VS27.3 code candidate into a *clean* Codespaces worktree.

This never runs ETABS or tests, never commits or pushes, and does not merge.
Use --apply only after reviewing the default dry-run report.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from r00_stage_vs27 import StageError, stage

BRANCH = "recovery/r00-r01-vs27-source-20261112"
BASE_SHA = "14ddf197ca8279ea34107eac0344acbabc7327aa"
ALLOWED_TOP = {"src", "tests", "tools", "docs", "examples", "config",
               "README.md", "pyproject.toml", ".gitattributes"}
PROTECTED_PREFIXES = ("docs/supervisor/", "tools/r00_", "tools/r01_", "config/r00_", "config/r01_")
MAX_FILE_BYTES = 24 * 1024 * 1024


class IntegrationError(ValueError):
    pass


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode:
        raise IntegrationError("GIT_" + args[0].upper() + "_FAILED:" + completed.stderr.strip()[:200])
    return completed.stdout.strip()


def check_worktree(root: Path) -> dict:
    if git(root, "rev-parse", "--show-toplevel") != str(root):
        raise IntegrationError("REPO_ROOT_MISMATCH")
    if git(root, "branch", "--show-current") != BRANCH:
        raise IntegrationError("WRONG_RECOVERY_BRANCH")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise IntegrationError("DIRTY_WORKTREE_PREVENTS_IMPORT")
    git(root, "merge-base", "--is-ancestor", BASE_SHA, "HEAD")
    origin = git(root, "remote", "get-url", "origin")
    if not (origin.endswith("/feridunfc/YENI.git") or
            origin.endswith(":feridunfc/YENI.git") or
            origin.endswith("/feridunfc/YENI")):
        raise IntegrationError("UNEXPECTED_GIT_REMOTE")
    return {"branch": BRANCH, "head": git(root, "rev-parse", "HEAD"),
            "origin": "feridunfc/YENI"}


def sha_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def plan_import(root: Path, source: Path) -> dict:
    planned = []
    for candidate in sorted(source.rglob("*")):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        relative = candidate.relative_to(source).as_posix()
        if (relative.split("/")[0] not in ALLOWED_TOP
                or relative.startswith(PROTECTED_PREFIXES)
                or relative in (".gitignore", ".github/workflows/ci.yml")
                or "__pycache__" in relative or relative.endswith(".pyc")):
            continue
        target = root / relative
        if candidate.stat().st_size > MAX_FILE_BYTES or target.is_symlink():
            raise IntegrationError("UNSAFE_OR_OVERSIZE_IMPORT:" + relative)
        if not target.resolve().is_relative_to(root.resolve()):
            raise IntegrationError("IMPORT_ESCAPES_REPO:" + relative)
        old = sha_file(target) if target.exists() else None
        new = sha_file(candidate)
        planned.append({"path": relative, "operation": "UNCHANGED" if old == new else
                        "UPDATE" if old is not None else "ADD",
                        "old_sha256": old, "new_sha256": new,
                        "bytes": candidate.stat().st_size})
    if not planned or not any(p["operation"] != "UNCHANGED" for p in planned):
        raise IntegrationError("NO_VS27_CHANGES_FOUND")
    return {"source": "SHA_PINNED_VS27_3", "branch": BRANCH,
            "candidate_files": len(planned),
            "added": sum(p["operation"] == "ADD" for p in planned),
            "updated": sum(p["operation"] == "UPDATE" for p in planned),
            "unchanged": sum(p["operation"] == "UNCHANGED" for p in planned),
            "paths": planned, "engineering_release": "NOT_READY"}


def apply_import(root: Path, source: Path, report: dict):
    # A clean-tree precondition guarantees that no unknown work is overwritten.
    for item in report["paths"]:
        if item["operation"] == "UNCHANGED":
            continue
        candidate, target = source / item["path"], root / item["path"]
        if (not candidate.is_file() or candidate.is_symlink() or
                sha_file(candidate) != item["new_sha256"]):
            raise IntegrationError("STAGED_SOURCE_CHANGED:" + item["path"])
        if target.is_symlink() or (target.exists() and
               sha_file(target) != item["old_sha256"]):
            raise IntegrationError("WORKTREE_CHANGED:" + item["path"])
    # All preflight checks passed; write atomically. No commit/push or tests.
    for item in report["paths"]:
        if item["operation"] == "UNCHANGED":
            continue
        candidate, target = source / item["path"], root / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".r00-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(candidate.read_bytes())
        try:
            temporary.chmod(candidate.stat().st_mode & 0o777)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True, help="Folder containing all 4 pinned ZIPs")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] /
                        "config/r00_vs27_artifacts.json")
    parser.add_argument("--apply", action="store_true", help="Write changes to the clean working tree")
    parser.add_argument("--report", type=Path, help="Write full path/SHA ledger; never overwrite")
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[1]
        head = check_worktree(root)
        with tempfile.TemporaryDirectory(prefix="tbdy-vs27-stage-") as temp:
            stage_path = Path(temp) / "source"
            receipt = stage(args.inputs, stage_path, args.manifest)
            plan = plan_import(root, stage_path)
            report = {"schema": "tbdy.next.r00-vs27-install-plan.v1", "git": head,
                      "pinned_stage": receipt, "integration": plan,
                      "installed": False, "tests_executed": False, "merge": "HOLD"}
            if args.apply:
                apply_import(root, stage_path, plan)
                report["installed"] = True
            if args.report:
                if args.report.exists() or args.report.is_symlink():
                    raise IntegrationError("OUTPUT_REPORT_EXISTS")
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        print(json.dumps({k: report[k] for k in ("schema", "git", "installed", "tests_executed", "merge")} |
                         {k: plan[k] for k in ("candidate_files", "added", "updated", "unchanged")},
                         indent=2, ensure_ascii=False))
        return 0
    except (IntegrationError, StageError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"integration": "REJECTED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
