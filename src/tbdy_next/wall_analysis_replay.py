"""Opt-in reanalysis of a dedicated input-identical copy for missing wall results."""

from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from shutil import copyfileobj
from stat import FILE_ATTRIBUTE_REPARSE_POINT
from uuid import uuid4

from .etabs_source_gateway_windows import SourceError, capture_assigned_pier_forces, model_file, seal, verify
from .wall_modal_capture import _native
from .wall_transition_capture import capture_transition_shells


def _check(value, reason):
    if not value:
        raise SourceError(reason)


def _digest(path):
    return sha256(path.read_bytes()).hexdigest()


def _safe(path):
    for entry in (path, *path.parents):
        try:
            meta = entry.lstat()
        except FileNotFoundError:
            continue
        if entry.is_symlink() or getattr(meta, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
            return False
    return True


def _write_new(path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def pier_controls(original, observed):
    def index(raw):
        rows = raw["tables"]["table_reads"]["Pier Forces"]["rows"]
        data = {}
        for r in rows:
            if r.get("CaseType") != "Combination":
                continue
            step = r.get("StepType")
            number = r.get("StepNumber", r.get("StepNum"))
            k = (
                r["Pier"],
                r["Story"],
                r["Location"],
                r["OutputCase"],
                "Single Value" if step in (None, "", "None", "Single Value") else step,
                0 if number in (None, "", "None") else float(number),
            )
            _check(k not in data, "DUPLICATE_PIER_CONTROL")
            values = tuple(float(r[n]) for n in ("P", "V2", "V3", "T", "M2", "M3"))
            _check(all(isfinite(v) for v in values), "NONFINITE_PIER_CONTROL")
            data[k] = values
        return data

    a, b = index(original), index(observed)
    _check(
        a and a.keys() == b.keys(),
        f"REPLAY_PIER_CONTROL_SCOPE_DIFFERS: {len(a)} expected, {len(b)} observed; "
        f"missing {list(a.keys() - b.keys())[:2]}, extra {list(b.keys() - a.keys())[:2]}",
    )
    error = [max(abs(v[i] - b[k][i]) for k, v in a.items()) for i in range(6)]
    mismatches = sum(
        abs(x - y) > max(0.00021, 1e-7 * max(abs(x), abs(y))) for k, v in a.items() for x, y in zip(v, b[k])
    )
    for name in ("Pier Section Properties", "Area Assignments - Pier Labels"):

        def records(raw):
            return sorted(
                json.dumps(row, sort_keys=True) for row in raw["tables"]["table_reads"][name]["rows"]
            )

        _check(records(original) == records(observed), "REPLAY_PIER_MEMBERSHIP_OR_PROPERTIES_DIFFER")
    return {
        "rows": len(a),
        "reported_rows": len(observed["tables"]["table_reads"]["Pier Forces"]["rows"]),
        "components": len(a) * 6,
        "outside_tolerance": mismatches,
        "maximum_difference": error,
        "absolute_tolerance": 0.00021,
        "relative_tolerance": 1e-7,
    }


def solve_private_wall_source(sap, pid, parent, parent_sha, previous, output_root):
    verify(previous)
    _check(
        previous["parent_input_sha256"] == parent_sha and previous.get("wall_modes"),
        "ORIGINAL_WALL_CONTROL_READ_REQUIRED",
    )
    base = Path(parent["capture_metadata"]["model_filename"]).with_suffix(".EDB").resolve(strict=True)
    initial_sha = previous["model_sha256"]
    _check(_digest(base) == initial_sha, "ORIGINAL_EDB_HASH_DIFFERS")
    root = Path(output_root).absolute() / "wall-analysis-copies"
    _check(_safe(root), "PRIVATE_WALL_DIRECTORY_MUST_BE_LOCAL_AND_DIRECT")
    root.mkdir(parents=True, exist_ok=True)
    active = Path(model_file(sap)).with_suffix(".EDB").resolve(strict=True)
    if active == base:
        folder = root / uuid4().hex
        folder.mkdir()
        target = folder / base.name
        with base.open("rb") as src, target.open("xb") as dst:
            copyfileobj(src, dst)
        _check(
            _digest(target) == initial_sha and not target.samefile(base),
            "INPUT_IDENTICAL_PRIVATE_COPY_REQUIRED",
        )
        _write_new(
            folder / "source.json",
            {"original": str(base), "parent_sha256": parent_sha, "input_sha256": initial_sha},
        )
        print("Opening private wall analysis copy: " + str(target), flush=True)
        _native(sap.File.OpenFile(str(target)), "Open private wall analysis copy")
    else:
        target, folder = active, active.parent
        _check(
            folder.parent == root and len(folder.name) == 32 and target.name == base.name and _safe(target),
            "Open the original model or this run's private wall copy. Active model: " + str(active),
        )
        manifest = json.loads((folder / "source.json").read_bytes())
        _check(
            manifest == {"original": str(base), "parent_sha256": parent_sha, "input_sha256": initial_sha},
            "PRIVATE_WALL_COPY_PARENT_DIFFERS",
        )

    def guard():
        path = Path(model_file(sap)).resolve(strict=True)
        _check(
            path in (target, target.with_suffix(".$et"))
            and _safe(target)
            and target.stat().st_nlink == 1
            and not target.samefile(base)
            and _digest(base) == initial_sha,
            "PRIVATE_WALL_ANALYSIS_FILE_GUARD_FAILED",
        )

    guard()
    ready_path = folder / "pier-read.json"
    if ready_path.is_file():
        data = json.loads(ready_path.read_bytes())
        verify(data)
        _check(
            data["parent_input_sha256"] == parent_sha
            and data["transition_shells"]["solution"]["solved_sha256"] == _digest(target),
            "PREVIOUS_PRIVATE_WALL_SOLUTION_DIFFERS",
        )
        return data
    cases = sorted(
        {
            r["Name"]
            for r in parent["vs04_basis_probe"]["table_reads"]["Load Case Definitions - Summary"]["rows"]
            if not r["Name"].startswith("~")
        }
    )

    def statuses():
        n, names, flags = _native(sap.Analyze.GetCaseStatus(0, [], []), "Get private case status")
        _check(
            n == len(names) == len(flags) and cases and set(cases) <= set(names),
            "PRIVATE_CASE_CATALOG_DIFFERS",
        )
        return dict(zip(names, flags))

    saved = statuses()
    if not sap.GetModelIsLocked() or any(saved[n] != 4 for n in cases):
        _check(_digest(target) == initial_sha, "PRISTINE_UNSOLVED_PRIVATE_COPY_REQUIRED")
        guard()
        if sap.GetModelIsLocked():
            _native(sap.SetModelIsLocked(False), "Unlock only the private copy")
        _native(sap.Analyze.SetRunCaseFlag("", False, True), "Clear private run flags")
        for name in cases:
            _native(sap.Analyze.SetRunCaseFlag(name, True, False), "Select private case " + name)
        guard()
        print(f"Solving {len(cases)} original cases on the private copy.", flush=True)
        _native(sap.Analyze.RunAnalysis(), "Run analysis on the private wall copy")
        guard()
        saved = statuses()
    _check(sap.GetModelIsLocked() and all(saved[n] == 4 for n in cases), "PRIVATE_WALL_CASES_UNFINISHED")
    solved_sha = _digest(target)
    observed = capture_assigned_pier_forces(sap, pid, parent, parent_sha, private_reference=target)
    _write_new(folder / ("native-controls-" + uuid4().hex + ".json"), observed)
    labels = previous["tables"]["table_reads"]["Area Assignments - Pier Labels"]["rows"]
    shell = capture_transition_shells(sap, parent, labels, initial_sha)
    _check(shell is not None, "PRIVATE_WALL_TRANSITION_POPULATION_EMPTY")
    guard()
    _check(
        sap.GetModelIsLocked() and _digest(target) == solved_sha and sap.GetPresentUnits() == 6,
        "PRIVATE_SOLUTION_CHANGED_DURING_READ",
    )
    acquisition = seal(
        {
            "schema": "tbdy.next.private-wall-read.v1",
            "input_sha256": initial_sha,
            "solved_sha256": solved_sha,
            "original_pier_read_sha256": previous["payload_sha256"],
            "cases": cases,
            "observed": observed,
            "shell": shell,
            "original_preserved": True,
        }
    )
    _write_new(folder / ("wall-read-" + uuid4().hex + ".source"), acquisition)
    result = bind_private_wall_result(previous, acquisition)
    _write_new(ready_path, result)
    print("Read and matched private wall results: " + str(ready_path), flush=True)
    return result


def bind_private_wall_result(previous, acquisition):
    verify(previous)
    verify(acquisition)
    observed, shell = acquisition["observed"], acquisition["shell"]
    verify(observed)
    verify(shell)
    _check(
        acquisition["schema"] == "tbdy.next.private-wall-read.v1"
        and acquisition["original_preserved"] is True
        and acquisition["original_pier_read_sha256"] == previous["payload_sha256"]
        and acquisition["input_sha256"] == previous["model_sha256"] == shell["model_sha256"]
        and acquisition["solved_sha256"] == observed["model_sha256"]
        and observed["schema"] == "tbdy.next.private-pier-comparison.v1"
        and observed["parent_input_sha256"] == previous["parent_input_sha256"]
        and set(observed["combinations"]) == set(previous["combinations"]),
        "PRIVATE_WALL_REPLAY_IDENTITY_DIFFERS",
    )
    compare = pier_controls(previous, observed)
    _check(compare["outside_tolerance"] == 0, "PRIVATE_PIER_CONTROLS_DIFFER:" + str(compare))
    evidence = {
        "method": "INPUT_IDENTICAL_PRIVATE_REANALYSIS",
        "input_sha256": acquisition["input_sha256"],
        "solved_sha256": acquisition["solved_sha256"],
        "original_pier_read_sha256": previous["payload_sha256"],
        "cases": acquisition["cases"],
        "pier_controls": compare,
        "frame_control_member": observed["control_member"],
        "frame_control_matched": True,
        "acquisition_sha256": acquisition["payload_sha256"],
    }
    shell = {k: v for k, v in shell.items() if k != "payload_sha256"}
    shell["solution"] = evidence
    result = {k: v for k, v in previous.items() if k != "payload_sha256"}
    result["transition_shells"] = seal(shell)
    return seal(result)
