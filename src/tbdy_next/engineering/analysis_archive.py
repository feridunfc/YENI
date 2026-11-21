"""Reconcile archived ETABS initial stiffness and solved case order in R03."""

from base64 import b64decode
from binascii import Error as Base64Error
from hashlib import sha256
from ntpath import normcase, splitext
import re
from collections.abc import Mapping

from ..vs05_d4_source_authority import SPECTRUM, _case_summary, _source_table

SCHEMA = "tbdy.next.etabs-solver-archive.v1"
ZERO = "USING STIFFNESS AT ZERO (UNSTRESSED) INITIAL CONDITIONS"
STATIC = "L I N E A R   S T A T I C   C A S E S"
MODAL = r"(?:R I T Z|E I G E N)   M O D A L   A N A L Y S I S"
SPECTRAL = "R E S P O N S E - S P E C T R U M   A N A L Y S I S"
COMPLETE = "A N A L Y S I S   C O M P L E T E"
_CASE = r"(?m)^\s*CASE:\s+([^\r\n]+?)\s*$"
_MODAL_KINDS = {"Modal", "Modal - Ritz", "Modal - Eigen"}


def _archive_bytes(value, limit):
    if not isinstance(value, str) or len(value) > (limit + 2) // 3 * 4:
        raise ValueError("SOLVER_ARCHIVE_ARTIFACT_INVALID")
    try:
        raw = b64decode(value, validate=True)
    except Base64Error as exc:
        raise ValueError("SOLVER_ARCHIVE_ARTIFACT_INVALID") from exc
    if not 0 < len(raw) <= limit:
        raise ValueError("SOLVER_ARCHIVE_ARTIFACT_INVALID")
    return raw


def normalize_solver_archive(raw, *, source_data_sha256):
    keys = {"schema", "source_data_sha256", "observed_edb_sha256", "log_base64", "model_export_base64"}
    if (not isinstance(raw, Mapping) or set(raw) != keys or raw["schema"] != SCHEMA
            or raw["source_data_sha256"] != source_data_sha256
            or not isinstance(raw["observed_edb_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", raw["observed_edb_sha256"])):
        raise ValueError("SOLVER_ARCHIVE_SOURCE_BINDING_INVALID")
    _archive_bytes(raw["log_base64"], 1_000_000)
    _archive_bytes(raw["model_export_base64"], 2_000_000)
    return dict(raw)


def reconcile_archived_order(source, analysis_setup):
    """Check actual log blocks, export settings and same-source native inventories."""
    record = source["analysis_archive"]
    log_bytes = _archive_bytes(record["log_base64"], 1_000_000)
    export_bytes = _archive_bytes(record["model_export_base64"], 2_000_000)
    log, export = (raw.decode("latin-1") for raw in (log_bytes, export_bytes))
    tables = source["vs04_basis_probe"]["table_reads"]
    cases = _case_summary(tables, require_key=True)
    filename = splitext(source["capture_metadata"]["model_filename"])[0] + ".LOG"
    log_paths = re.findall(r"(?m)^\s*File:\s*([^\r\n]+?)\s*$", log)
    if (analysis_setup.get("source_capture_scope") != "SAME_CAPTURE"
            or not analysis_setup.get("definition_coverage_known")
            or not log_paths or set(map(normcase, log_paths)) != {normcase(filename)}
            or re.findall(r'(?m)^\s*PDELTA\s+METHOD\s+"([^"]+)"\s*$', export) != ["NONE"]):
        raise ValueError("SOLVER_ARCHIVE_MODEL_OR_PRESET_UNRESOLVED")

    definitions = re.findall(r'(?m)^\s*LOADCASE\s+"([^"]+)"\s+TYPE\s+"([^"]+)"\s+'
                             r'(INITCOND|MODALCASE)\s+"([^"]+)"', export)
    configured = {name: (kind, field, value) for name, kind, field, value in definitions}
    if (len(configured) != len(definitions) or set(configured) != set(cases)
            or any(case["type"] != configured[name][0] for name, case in cases.items())
            or len({name.upper() for name in cases}) != len(cases)):
        raise ValueError("SOLVER_ARCHIVE_CASE_DEFINITIONS_MISMATCH")
    names = {name.upper(): name for name in cases}
    settings = {row["case"]: row for row in analysis_setup["linear_static_settings"]}
    solved = set()
    parents = {}
    mode_counts = {}
    for name, (kind, field, value) in configured.items():
        if kind == "Linear Static":
            row = settings[name]
            expected = {"PRESET": {"P-Delta"}, "NONE": {"Unstressed", "Zero Initial Conditions", "Nonlinear Case"}}
            if (field != "INITCOND" or row["stiffness_setting"] not in expected.get(value, ())
                    or row["nonlinear_case"] not in (None, "", "None")):
                raise ValueError("SOLVER_ARCHIVE_STATIC_STIFFNESS_MISMATCH:" + name)
        elif kind in _MODAL_KINDS and (field != "INITCOND" or value not in {"NONE", "PRESET"}):
            raise ValueError("SOLVER_ARCHIVE_MODAL_STIFFNESS_UNSUPPORTED:" + name)
        elif kind == "Response Spectrum":
            if field != "MODALCASE" or cases.get(value, {}).get("type") not in _MODAL_KINDS:
                raise ValueError("SOLVER_ARCHIVE_SPECTRAL_PARENT_UNRESOLVED:" + name)
            parents[name] = value
    native_parents = _source_table(tables, SPECTRUM, {"Name", "ModalCase"}, require_key=True)
    if {(row["Name"], row["ModalCase"]) for row in native_parents} != set(parents.items()):
        raise ValueError("SOLVER_ARCHIVE_SPECTRAL_PARENT_MISMATCH")

    period_rows = source["analysis_sources"]["tables"]["Modal Periods And Frequencies"]["rows"]
    expected_modes = {name: {int(row["Mode"]) for row in period_rows if row["Case"] == name}
                      for name in set(parents.values())}
    expected_frames = source["column_axial"]["r10_source"]["table_reads"]["Objects and Elements - Frames"]["row_count"]
    runs = log.split("B E G I N   A N A L Y S I S")[1:]
    if len(runs) != len(log_paths):
        raise ValueError("SOLVER_ARCHIVE_RUN_BOUNDARY_MISMATCH")
    for run in runs:
        if (run.count(COMPLETE) != 1
                or re.findall(r"NUMBER OF FRAME/TENDON ELEMENTS\s*=\s*(\d+)", run) != [str(expected_frames)]
                or run.count("FORMING STIFFNESS AT ZERO (UNSTRESSED) INITIAL CONDITIONS") != 1):
            raise ValueError("SOLVER_ARCHIVE_RUN_NOT_COMPLETE_AT_ZERO_STIFFNESS")
        sections = re.split(f"({STATIC}|{MODAL}|{SPECTRAL})", run.split(COMPLETE, 1)[0])
        for offset in range(1, len(sections), 2):
            header, section = sections[offset:offset + 2]
            listed = [names[case.upper()] for case in re.findall(_CASE, section) if not case.startswith("~")]
            if header == SPECTRAL:
                case, = listed
                parent = parents[case]
                counts = re.findall(r"NUMBER OF DYNAMIC MODES TO BE USED\s*=\s*(\d+)", section)
                actual_parent = re.findall(r"(?m)^\s*USING MODES FROM CASE:\s*([^\r\n]+?)\s*$", section)
                if (counts != [str(mode_counts.get(parent))] or actual_parent != [parent.upper()]):
                    raise ValueError("SOLVER_ARCHIVE_SPECTRAL_MODE_USE_MISMATCH:" + case)
            elif ZERO not in section:
                raise ValueError("SOLVER_ARCHIVE_CASE_ZERO_STIFFNESS_UNPROVEN")
            elif header != STATIC:
                case, = listed
                count, = re.findall(r"NUMBER OF (?:RITZ|EIGEN) MODES FOUND\s*=\s*(\d+)", section)
                modes = expected_modes.get(case, set())
                if (cases[case]["type"] not in _MODAL_KINDS or int(count) != len(modes)
                        or not modes or modes != set(range(1, len(modes) + 1))):
                    raise ValueError("SOLVER_ARCHIVE_MODAL_POPULATION_MISMATCH:" + case)
                mode_counts[case] = int(count)
            elif any(case not in settings for case in listed):
                raise ValueError("SOLVER_ARCHIVE_LINEAR_CASE_MISMATCH")
            solved.update(listed)
    if solved != set(cases):
        raise ValueError("SOLVER_ARCHIVE_SOLVED_CASE_POPULATION_MISMATCH")
    return {
        "status": "ARCHIVED_SOLVER_FIRST_ORDER_MATCHED",
        "source_analysis_order": "FIRST_ORDER",
        "source_data_sha256": record["source_data_sha256"],
        "solved_case_guids": {name: cases[name]["guid"] for name in sorted(solved)},
        "configured_static_initial_conditions": {name: configured[name][2] for name in sorted(settings)},
        "spectrum_modal_parents": parents,
        "modal_mode_counts": mode_counts,
        "solver_log_sha256": sha256(log_bytes).hexdigest(),
        "model_export_sha256": sha256(export_bytes).hexdigest(),
        "observed_edb_sha256": record["observed_edb_sha256"],
    }
