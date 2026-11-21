# Executable variable-axial design example

**CONTRACT_FIXTURE / GENERATED_OFFLINE_NOT_ETABS.** This public source is
synthetic. It is not C29, a native ETABS solution or an engineering approval.

The normal YENI runner selects reinforcement and evaluates the two columns,
four connected beams, column shear and the interior joint. Its numerical
outcomes are calculated by the production owners; no prepared stage result or
resistance is supplied as an input.

## Run

Install the current checkout in the project environment, then run:

```bash
python -B -m tbdy_next.cli run-pipeline --source examples/variable_axial_slice_20261121/synthetic_input.json --design-scenario examples/variable_axial_slice_20261121/design-scenario.json --case Modal --out .receipts/variable-axial-example
```

The output identifies the finalized `RUN-*` directory. Run the same command
with `--compare-run <that directory>` to compare the source, plan, methods,
recorded results and receipts. Open the sealed report using the existing report
interface. Report opening does not recalculate the design.

Use `default-scenario.json` instead to run the same source under the original
constant-axial applicability. It deliberately retains the variable-axial gate.

## Inputs and calculated scope

| Quantity | Value |
| --- | --- |
| Columns and connected beams | 2 and 4 |
| Column dimensions | 800 x 800 mm |
| Clear span | 2.5 m |
| Material unit weight | 25 kN/m3 |
| Section weight modifier | 1 |
| Self-weight load | 16 kN/m |
| C1 compression at 0 / 1.25 / 2.5 m | 2540 / 2520 / 2500 kN |
| C2 compression at 0 / 1.25 / 2.5 m | 1540 / 1520 / 1500 kN |
| Signed combinations | G, G+EX, G-EX, G+EY, G-EY |
| Expected combined-force cuts | 30 across 10 member-combination pairs |
| Primitive-force cuts | 18 across LC_DL, EX and EY |
| Interior-joint SCWB comparisons | 16 unique comparisons in X and Y |

The opt-in request uses the maximum compression from each signed combination
for the existing magnification coefficient. Each cut retains its actual local
compression for eccentricity and section capacity. Source completeness and
self-weight equilibrium are checked before this assumption can be consumed.

Both columns are conditionally numerically complete in the opt-in example;
the unchanged default completes zero. The selected longitudinal cage is
32Phi16, and the transverse scenario is Phi12/70. The complete recorded output
is projected into [calculation-report.html](calculation-report.html) and
[expected-results.json](expected-results.json). Download/open the HTML to read
the standard report; GitHub's code view shows its source.

| Governing result | C1 | C2 |
| --- | ---: | ---: |
| Magnification coefficient | 1.00644015 | 1.00389478 |
| Selected-section PMM utilization | 0.10234089 | 0.09034587 |
| Capacity shear / TS 500 resistance | 0.71968177 | 0.62741371 |
| Capacity shear / zero-concrete resistance | 0.94265694 | 0.80510603 |
| Maximum connected joint shear utilization | 0.14287920 | 0.14287920 |

The interior joint's minimum normalized SCWB lower ratio is 13.77835923.
Its X and Y directions each evaluate eight combination/sway checks. These
are calculated outcomes of the synthetic scenario, not accepted building
design values.

## Limits and verification

The idealization does not satisfy the original constant-axial-force condition
by declaration. Conservatism and engineering acceptance remain unproven, and
the engineering release remains `NOT_READY`. The example does not exercise
wall-coupled columns, spectral component envelopes or alpha below one.

Independent test arithmetic covers self weight, cage inertia, EI, Euler load,
coefficient, local eccentricity and final moments. It is not a second PMM
solver. Source perturbations and an insufficient actual transverse-design
scenario must remain unclosed. The installed-wheel and normal Web/CLI tests
use the existing pipeline.

See the [method and C29 continuation](../../docs/engineering/VARIABLE_AXIAL_SLICE_20261121.md)
and [fresh verification](../../docs/engineering/variable_axial_slice_20261121/VERIFICATION_RESULTS.json).
