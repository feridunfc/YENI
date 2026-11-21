# C29 second-order method calculation — 2026-11-21

The existing R08 owner now consumes paired gravity forces, same-generation story
compression and critical-load inputs, and six-component displacement results.
R14 and the printable report consume the sealed result. The original adopted
C29 design path remains the reference for the eight connected beams and joint 40.

## Numerical verification in the normal runner

Source class: `CONTRACT_FIXTURE`. The two-story source and one-column method
comparison are constructed in `tests/test_variable_axial_vertical_slice.py`.
The revised force vectors, support springs and joint motions are test inputs.
The production owners calculate K, Euler loads, magnification, selected-section
PMM, deformation, and the R14 projection.

| Finest-mesh item | Calculated result |
| --- | ---: |
| EI, both axes | 3.26775287534e14 N·mm² |
| K / clear length / effective length | 2.0 / 2.50 m / 5.00 m |
| Member Nk / story Nk | 129,005.713 / 129,005.713 kN |
| Local coefficient Nmax / story Nd | 2,780 / 2,780 kN |
| Eq. 7.29 branch / factor, both axes | MAXIMUM / 1.0288216815 |
| Common physical cuts / retained element sides | 3 / 4 |
| Finest paired sides including additional cuts | 24 / 24 |
| 4- and 8-part recovered peak | 0.8999996 mm at 1.499023 m from the I face |
| Native intervening joints and maximum withheld residual | 4 / 0 mm |
| Full-span uncertainty budget against 0.01 mm | 0.0000025432 mm |
| Sealed explicit replay | 12/12 stages identical |

At the I face, the selected 32Phi16 section uses the original TS 500 result
`[+99.708, +99.708] kN·m`, direct revised second-order result
`[-153.000, +174.000] kN·m`, and revised TS 500 result
`[-154.323, +174.900] kN·m`. The three PMM utilizations are 10.235%, 16.391%
and 16.544%. The revised first-order cut has 2,780 kN compression, versus
2,810 kN in the paired direct second-order cut. Both cut sides at the midpoint
are retained. The fixture changes K by altering the end springs, observes the
change in the real design moments, and retains a failed approximate-method
slenderness check with its denominator.

The deformation check reconstructs a prismatic beam's cubic bending and linear
shear between rigid ends. The benchmark with finite shear stiffness and nonzero
rigid offsets has an independently calculated interior peak of 2.19317249 mm at
2.11149020 m. Recovery gives 2.19317174 mm at 2.1125 m inside a bounded
[2.100, 2.125] m location interval. The full-span comparison uses a common
physical interval, a bounded extremum search and intermediate fine-mesh joints
held out of the coarse fit. Its scope is the numerical displacement
representation. The existing force refinement criterion covers P, M2 and M3.

## Independent source checks

| Example | Production result |
| --- | --- |
| `GE-CHK-117` | K = 0.8975, lk = 2,288.625 mm. Printed K = 0.90. Zero ratios give K = 0.70 and missing restraint remains unresolved. |
| `GE-CHK-119` | Member beta 1.549351615 and story beta 1.192764971. Effective-length reading gives 60.390838 < 83.789339, selects MAXIMUM and gives M2 = −82.317051 kN·m. The report's product reading gives M2 = −98.184895 kN·m. `G02_USED_FACTOR_SZ01_ground` remains an interpretation difference. |

The fresh Windows regressions passed with 1,682 Python passes, one skip
and 11 JavaScript test files. The 44 production comparisons return 33
numerical matches, seven source/method records and four interpretation
differences.

## Original building

Original revised-model replay: **NOT_RUN** for the qualified methods. A new
private 8-part METHOD solve finished 6/6 cases and was still locked after the
read attempt and restoration of run flags. The first read attempt stopped before
sealing the displacement and story inputs. Use the saved session state and
resume the active 8-part clone before reopening it. The historical 2/4/8 meshes
supply signed forces and three translations. The original selected result
remains 2/87 conditional, with eight connected beams and joint 40.

The geometry census at the lower face of column 225 (`+0.00`) contains
32 columns and 21 wall area objects. At the lower face of 142 (`+4.50`) it
contains 32 columns and four wall area objects. Use simultaneous revised
column and wall force resultants and independently allocated loads for the
upper free body. Each wall enters the population once. A wall or coupled
wall–frame critical-load contribution needs a supported method and a bound
physical member definition. Wall area counts establish the geometry population.
Bind directional end restraint and stiffness for each contributing column. Use
only same-revision story totals in the revised method.

See `EV-C29-QUALIFIED-GRAVITY-COMPARISON-20261121` for the exact tested tree,
commands and sealed reports. The owner results are in
`gravity_pair_refinement.py`, `gravity_story_basis.py` and
`gravity_deformation.py`. Continue from the remaining original-model inputs in
[the task](C29_CALCULATION_COMPLETION_TASK_20261121.md).
