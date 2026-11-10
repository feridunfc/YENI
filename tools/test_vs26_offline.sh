#!/usr/bin/env bash
# Codespaces/Linux regression entry point. No ETABS or engineering acceptance.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
vs26_python="${VS26_PYTHON:-python3}"
vs26_logs="$PWD/.receipts/vs26-tests-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p -- "$vs26_logs"
exec > >(tee "$vs26_logs/test.log") 2>&1
trap 'vs26_exit=$?; printf "\nVS26_TEST_EXIT=%s\nLOG_DIR=%s\n" "$vs26_exit" "$vs26_logs"' EXIT

printf 'VS26 offline software and golden regressions\n'
git rev-parse HEAD
git status --short --branch
"$vs26_python" -c 'import sys; print(sys.version); assert sys.version_info >= (3, 11), "Python 3.11+ required"'
node --version

"$vs26_python" -m venv "$vs26_logs/venv"
vs26_python="$vs26_logs/venv/bin/python"
"$vs26_python" -m pip install -e .
"$vs26_python" -m unittest discover -s tests -q
"$vs26_python" -m compileall -q src
node --check src/tbdy_next/static/column.js
for vs26_test in \
  tests/test_vs07_ui_state.cjs \
  tests/test_vs11_column_ui.cjs \
  tests/test_vs20_column_ui.cjs \
  tests/test_vs21_column_ui.cjs \
  tests/test_vs22_column_ui.cjs \
  tests/test_vs23_column_ui.cjs \
  tests/test_vs24_column_ui.cjs \
  tests/test_vs26_column_ui.cjs \
  tests/test_vs26_design_ui.cjs; do
  node "$vs26_test"
done

"$vs26_python" -m tbdy_next.cli inspect-golden-regression --json "$vs26_logs/golden-regression.json"
if "$vs26_python" -m tbdy_next.cli inspect-golden-regression --require-complete --json "$vs26_logs/golden-acceptance-gate.json"; then
  printf 'ERROR: VS26 golden coverage was unexpectedly promoted to complete.\n'
  exit 1
else
  vs26_gate_exit=$?
  if [ "$vs26_gate_exit" -ne 3 ]; then
    printf 'ERROR: golden gate returned %s; expected the documented incomplete-coverage exit 3.\n' "$vs26_gate_exit"
    exit "$vs26_gate_exit"
  fi
fi
git diff --check
printf '\nVS26_SOFTWARE_REGRESSIONS=PASS\nGOLDEN_ENGINEERING_GATE=INCOMPLETE\nNORMATIVE_AUTHORITY=NOT_PROVEN\nENGINEERING_RELEASE=NOT_READY\n'
printf 'The 87-column native archive replay is a separate check; this script does not claim to rerun it.\n'
