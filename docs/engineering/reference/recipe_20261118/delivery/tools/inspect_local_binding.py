#!/usr/bin/env python3
"""Create private, mechanical local-binding evidence without importing YENI.

This program reads Git metadata and repository bytes. It writes only a new,
explicitly named evidence file outside both the repository and this delivery.
It does not change branches, update files, execute production code, run tests,
or promote a mechanical match to semantic inspection or engineering acceptance.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import tokenize
import io


VERSION = "yeni.local-binding-inspection.v1"
RELEVANT_ROOTS = {"src", "tests", "test", "docs", "tools", "scripts", "config", "configs", ".github"}
ROOT_SUFFIXES = {".py", ".pyi", ".md", ".rst", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini"}
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".receipts"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def guarded_path(repo: Path, relative: str) -> Path:
    """Reject traversal, absolute names, metadata paths and escaping symlinks."""
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative or ":" in relative:
        raise ValueError("Repository path is not a portable relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"..", ".git"} for part in pure.parts):
        raise ValueError("Repository path escapes the permitted source scope")
    candidate = repo.joinpath(*pure.parts)
    resolved = candidate.resolve(strict=False)
    if resolved == repo or not inside(resolved, repo):
        raise ValueError("Repository path or symlink points outside the chosen repository")
    return resolved


def relevant(relative: str) -> bool:
    pure = PurePosixPath(relative)
    if any(part in EXCLUDED_PARTS for part in pure.parts):
        return False
    if pure.name == ".env" or pure.name.startswith(".env."):
        return False
    return bool(pure.parts) and (
        pure.parts[0] in RELEVANT_ROOTS
        or (len(pure.parts) == 1 and (pure.suffix.lower() in ROOT_SUFFIXES or pure.name in {"AGENTS.md", "Makefile"}))
    )


def run_git(git: str, repo: Path, *arguments: str) -> bytes:
    # Optional index refresh writes are disabled. No shell, hooks, aliases or
    # remote access are required for these explicit read-only Git commands.
    env = dict(os.environ)
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    command = [git, "-c", "core.fsmonitor=false", "-c", "maintenance.auto=false", "-C", str(repo), *arguments]
    completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, check=False)
    if completed.returncode:
        raise RuntimeError("Read-only git command failed: " + " ".join(arguments)
                           + "; " + completed.stderr.decode("utf-8", "replace").strip())
    return completed.stdout


def parse_status(raw: bytes) -> list[dict]:
    """Parse porcelain v1 -z, including the second pathname for renames/copies."""
    parts = raw.split(b"\0")
    records = []
    index = 0
    while index < len(parts):
        item = parts[index]
        index += 1
        if not item:
            continue
        if len(item) < 4 or item[2:3] != b" ":
            raise ValueError("Unexpected git status record")
        code = item[:2].decode("ascii")
        record = {"path": os.fsdecode(item[3:]), "git_status": code,
                  "untracked": code == "??"}
        if "R" in code or "C" in code:
            if index >= len(parts) or not parts[index]:
                raise ValueError("Missing original pathname in git rename/copy record")
            record["original_path"] = os.fsdecode(parts[index])
            index += 1
        records.append(record)
    return records


def file_evidence(repo: Path, relative: str, status: str = "  ") -> dict:
    record = {"path": relative, "git_status": status, "sha256": None, "size_bytes": None}
    try:
        path = guarded_path(repo, relative)
        record["resolved_local_path"] = str(path)
        if not path.is_file():
            record["availability"] = "MISSING_OR_NOT_REGULAR_FILE"
            return record
        before = path.stat()
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        after = path.stat()
        record.update(availability="AVAILABLE", sha256=hasher.hexdigest(), size_bytes=after.st_size,
                      stable_during_read=(before.st_size, before.st_mtime_ns, before.st_ino)
                      == (after.st_size, after.st_mtime_ns, after.st_ino))
    except (OSError, ValueError) as error:
        record.update(availability="UNAVAILABLE_OR_PATH_REJECTED", reason=str(error))
    return record


def symbol_evidence(repo: Path, relative: str, symbol: str, cache: dict) -> dict:
    if relative not in cache:
        try:
            path = guarded_path(repo, relative)
            raw = path.read_bytes()
            encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
            tree = ast.parse(raw.decode(encoding), filename=relative)
            cache[relative] = {"tree": tree, "sha256": sha256_bytes(raw), "error": None}
        except (OSError, ValueError, SyntaxError, UnicodeError) as error:
            cache[relative] = {"tree": None, "sha256": None, "error": str(error)}
    source = cache[relative]
    if source["error"] is not None:
        return {"found": False, "reason": source["error"], "parsed_file_sha256": source["sha256"]}
    nodes = source["tree"].body
    node = None
    for component in symbol.split("."):
        matches = [n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                   and n.name == component]
        if len(matches) != 1:
            return {"found": False, "reason": "SYMBOL_MISSING_OR_AMBIGUOUS", "parsed_file_sha256": source["sha256"]}
        node = matches[0]
        nodes = node.body
    function = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    return {"found": True, "parsed_file_sha256": source["sha256"],
            "signature": symbol + "(" + ast.unparse(node.args) + ")" if function else symbol,
            "returns": ast.unparse(node.returns) if function and node.returns else "NOT_ANNOTATED",
            "line_start": node.lineno, "line_end": node.end_lineno}


def compare_owner(owner: dict, repo: Path, files: dict, ast_cache: dict) -> dict:
    relative = owner.get("path")
    symbol = owner.get("symbol")
    expected_hash = owner.get("file_sha256")
    result = {"path": relative, "symbol": symbol, "baseline_commit": owner.get("source_commit"),
              "baseline_file_sha256": expected_hash, "baseline_signature": owner.get("signature"),
              "baseline_returns": owner.get("returns"), "comparison": "UNMAPPED",
              "semantic_review_status": "NOT_INSPECTED", "engineering_acceptance": "NOT_RUN"}
    if not all(isinstance(v, str) and v for v in (relative, symbol, expected_hash, owner.get("signature"))):
        result["reason"] = "INCOMPLETE_BASELINE_BINDING"
        return result
    current = files.get(relative)
    if current is None:
        current = file_evidence(repo, relative)
        files[relative] = current
    result["local_file_sha256"] = current.get("sha256")
    if current.get("availability") != "AVAILABLE":
        result["reason"] = current.get("reason", current["availability"])
        return result
    observed = symbol_evidence(repo, relative, symbol, ast_cache)
    result["observed_symbol"] = observed
    if not observed["found"]:
        result["reason"] = "SYMBOL_UNAVAILABLE_FOR_MECHANICAL_BINDING"
        return result
    same_hash = current["sha256"] == expected_hash
    same_signature = observed["signature"] == owner["signature"] and observed["returns"] == owner.get("returns", "NOT_ANNOTATED")
    stable = bool(current.get("stable_during_read")) and observed["parsed_file_sha256"] == current["sha256"]
    result.update(bytes_match=same_hash, signature_match=same_signature, stable_observation=stable,
                  comparison="MATCHED_BYTES" if same_hash and same_signature and stable else "CHANGED_REVIEW_REQUIRED",
                  reason="Exact file bytes and symbol signature matched; semantic review is still not performed."
                  if same_hash and same_signature and stable else
                  "Source bytes, signature or observation stability differ; review the actual local changes without replacing them.")
    return result


def compare_metadata(source: dict, repo: Path, files: dict, kind: str) -> dict:
    relative = source.get("registry_path") or source.get("path")
    expected = source.get("file_sha256")
    result = {"kind": kind, "path": relative, "baseline_commit": source.get("source_commit"),
              "baseline_file_sha256": expected, "comparison": "UNMAPPED"}
    if not isinstance(relative, str) or not isinstance(expected, str):
        result["reason"] = "INCOMPLETE_BASELINE_METADATA"
        return result
    if relative not in files:
        files[relative] = file_evidence(repo, relative)
    actual = files[relative]
    result["local_file_sha256"] = actual.get("sha256")
    if actual.get("availability") != "AVAILABLE":
        result["reason"] = actual.get("reason", actual["availability"])
    else:
        result["comparison"] = "MATCHED_BYTES" if actual["sha256"] == expected and actual.get("stable_during_read") else "CHANGED_REVIEW_REQUIRED"
    result["note"] = "File identity only; stage/GAP semantics and completeness are not reviewed."
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, type=Path, help="Existing local Git repository root to read; no checkout or update occurs.")
    parser.add_argument("--mapping", required=True, type=Path, help="Explicit CHECK_MAPPING.json to compare with the local bytes.")
    parser.add_argument("--output", required=True, type=Path, help="New PRIVATE JSON evidence path, outside the repo and delivery; parent directory must exist. Existing files are never overwritten.")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required for source AST inspection.")
    try:
        repo = args.repo.resolve(strict=True)
        mapping_path = args.mapping.resolve(strict=True)
        if args.output.is_symlink():
            raise ValueError("--output must not be an existing symbolic link")
        output = args.output.resolve(strict=False)
        delivery = Path(__file__).resolve().parent.parent
        if not repo.is_dir():
            raise ValueError("--repo must be a directory")
        if output.exists() or not output.parent.is_dir():
            raise ValueError("--output must be a new file in an existing private directory")
        if inside(output, repo) or inside(output, delivery) or inside(output, mapping_path.parent):
            raise ValueError("Private output must be outside the repository, delivery directory and mapping directory")
        git = shutil.which("git")
        if git is None:
            raise ValueError("git executable was not found")
        top = Path(os.fsdecode(run_git(git, repo, "rev-parse", "--show-toplevel")).strip()).resolve(strict=True)
        if top != repo:
            raise ValueError("--repo must name the exact Git worktree root")
        head_before = run_git(git, repo, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
        branch = os.fsdecode(run_git(git, repo, "rev-parse", "--abbrev-ref", "HEAD")).strip()
        status_before = run_git(git, repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        status_records = parse_status(status_before)
        statuses = {r["path"]: r["git_status"] for r in status_records}
        tracked = {os.fsdecode(p) for p in run_git(git, repo, "ls-files", "-z", "--cached").split(b"\0") if p}
        mapped_bytes = mapping_path.read_bytes()
        mapping = json.loads(mapped_bytes)
        checks = mapping.get("checks")
        if not isinstance(checks, list) or not checks or len({r["check_id"] for r in checks}) != len(checks):
            raise ValueError("Mapping must contain a nonempty checks array with unique existing check_id values")
        paths = {p for p in tracked | set(statuses) if relevant(p)}
        files = {p: file_evidence(repo, p, statuses.get(p, "  ")) for p in sorted(paths)}
        ast_cache: dict = {}
        comparisons = []
        for check in checks:
            baseline = check.get("reviewed_snapshot_binding", {})
            owners = [compare_owner(o, repo, files, ast_cache) for o in baseline.get("owners", [])]
            related = [compare_owner(o, repo, files, ast_cache) for o in baseline.get("related_source_functions", [])]
            metadata = [compare_metadata(s, repo, files, "REGISTERED_STAGE_FILE") for s in baseline.get("pipeline_stages", [])]
            if baseline.get("gap_source"):
                metadata.append(compare_metadata(baseline["gap_source"], repo, files, "GAP_SOURCE_FILE"))
            comparison = "UNMAPPED" if not owners or any(o["comparison"] == "UNMAPPED" for o in owners) else (
                "MATCHED_BYTES" if all(o["comparison"] == "MATCHED_BYTES" for o in owners) else "CHANGED_REVIEW_REQUIRED")
            comparisons.append({"check_id": check["check_id"], "owner_bytes_comparison": comparison,
                                "owners": owners, "related_source_functions_not_calculation_owners": related,
                                "registry_and_gap_files": metadata, "semantic_review_status": "NOT_INSPECTED",
                                "production_execution": "NOT_RUN", "engineering_acceptance": "NOT_RUN"})
        head_after = run_git(git, repo, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
        status_after = run_git(git, repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        stable = head_before == head_after and status_before == status_after and all(
            f.get("stable_during_read", True) for f in files.values()) and all(
            o.get("stable_observation", True) for c in comparisons for o in c["owners"] + c["related_source_functions_not_calculation_owners"])
        evidence = {
            "schema_version": VERSION, "classification": "PRIVATE_LOCAL_EVIDENCE_DO_NOT_PUBLISH",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "command_argv": [sys.executable, str(Path(__file__).resolve()), *(argv if argv is not None else sys.argv[1:])],
            "environment": {"python_executable": sys.executable, "python_version": sys.version,
                            "platform": platform.platform(), "git_executable": git,
                            "git_version": run_git(git, repo, "--version").decode("utf-8", "replace").strip(),
                            "working_directory": str(Path.cwd()), "git_optional_locks": "0"},
            "tool": {"version": VERSION, "path": str(Path(__file__).resolve()),
                     "sha256": sha256_bytes(Path(__file__).read_bytes())},
            "mapping": {"path": str(mapping_path), "sha256": sha256_bytes(mapped_bytes),
                        "schema_version": mapping.get("schema_version"), "record_count": len(checks)},
            "repository": {"path": str(repo), "head_before": head_before, "head_after": head_after,
                           "branch": branch, "detached_head": branch == "HEAD",
                           "dirty": bool(status_records), "status_records": status_records,
                           "stable_observation": stable,
                           "atomic_snapshot_claimed": False},
            "file_inventory_scope": {
                "included": "Tracked and nonignored untracked source/test/document/tool/config paths, plus explicitly mapped files.",
                "relevant_roots": sorted(RELEVANT_ROOTS), "excluded_path_parts": sorted(EXCLUDED_PARTS),
                "limits": "Ignored files and unrelated paths are not hashed. Git status includes path metadata only. Symlinks escaping the chosen root are not followed. Concurrent edits can require a fresh run."},
            "relevant_files": [files[p] for p in sorted(files)],
            "dirty_relevant_paths": sorted(p for p in statuses if relevant(p) and statuses[p] != "??"),
            "untracked_relevant_paths": sorted(p for p in statuses if relevant(p) and statuses[p] == "??"),
            "check_binding_comparisons": comparisons,
            "counts": {"relevant_files": len(files),
                       "check_owner_bytes_comparisons": dict(Counter(c["owner_bytes_comparison"] for c in comparisons)),
                       "structural_calculations_run": 0, "tests_run": 0},
            "result": "MECHANICAL_REPORT_WRITTEN" if stable else "SOURCE_CHANGED_DURING_INSPECTION_REPEAT_REQUIRED",
            "limits": [
                "MATCHED_BYTES means exact baseline file bytes and a parsed symbol signature; it does not review semantics, applicability, integration or completeness.",
                "CHANGED_REVIEW_REQUIRED preserves local changes for review; it is not a request to reset, checkout, replace or downgrade them.",
                "Raw byte differences include line-ending differences across operating systems; a mismatch alone does not establish a semantic regression.",
                "UNMAPPED means no complete mechanical binding was established. Related utility/source symbols do not become calculation owners.",
                "The current local tree remains semantically NOT_INSPECTED until a separate review is performed.",
                "Production-owner comparison, recorded-source replay, live ETABS and engineering acceptance are NOT_RUN.",
                "This evidence contains local paths and dirty/untracked metadata and must remain separate from publishable delivery files."
            ]
        }
        # Exclusive creation prevents the evidence tool from overwriting any file.
        with output.open("x", encoding="utf-8") as stream:
            json.dump(evidence, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
        print("Private mechanical report written. No semantic or engineering status was promoted.")
        print(str(output))
        return 0 if stable else 3
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print("Inspection could not be completed: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
