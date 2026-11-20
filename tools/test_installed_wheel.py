"""Install the wheel in isolation; verify reports, PMM v6 and offline scenarios."""

import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import venv


TESTS = Path(__file__).resolve().parents[1] / "tests"
WHEEL_TESTS = (
    "test_vs06_c2_drift_scenario.Vs06C2HttpIntegration.test_live_once_then_scenario_and_json_html_no_com",
    "test_audit_hardening.PmmAnalysisMeshContracts",
    "test_audit_hardening.SpectrumPopulationContracts",
    "test_r08_local_live.R08LocalUnitTests",
    "test_etabs_source_gateway.GatewayTests.test_pmm_reads_mesh_and_station_assignments_through_one_connected_model",
    "test_etabs_source_gateway.GatewayTests.test_pmm_reads_unrounded_native_coordinates_only_for_meshed_columns",
    "test_offline_design_scenario",
    "test_design_member_dependencies",
    "test_alpha_design_iteration",
    "test_mixed_design_demands",
    "test_native_demand_sources",
    "test_same_source_spectral_replay",
    "test_r13_joint_adapters",
    "test_r10_low_axial",
    "test_rebar_selection",
    "test_recorded_column_calculation_report",
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
                "unittest.main(module=None, argv=['unittest', '-v', *sys.argv[2:]])\n",
                str(TESTS), *WHEEL_TESTS,
            ],
            cwd=isolated, check=True,
        )


if __name__ == "__main__":
    main()
