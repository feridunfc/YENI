# Current local checkpoint — 2026-11-19

**87 column reinforcement candidates are selected and bound to the same pipeline run.**
Final candidate: **32Φ16 + Φ10/90 mm ties, three crossties per local direction**.
Selected As 6,433.98 mm² ≥ 6,400 mm² (1.0053%). The final reference checks pass,
but R14 remains **0 closed / 87 partial**, formal compliance `NOT_PROVEN`,
engineering release `NOT_READY`.

## GAP-018 manual ETABS comparison

ETABS finished Modal, RSX, RSY and both zero-eccentricity cases on the private
copy. The two readbacks reproduced the same native spectral forces and case
definitions. The original model's 3,175 input lines match in order after
excluding the file header, six new case-definition lines and three Save As records.

At 402 element-side cuts on 87 columns, the signed half-difference between
the positive and negative eccentric static cases gives 804 direction-specific
static vectors. Its component magnitude matches the increase in the ETABS
spectrum maximum from zero to 5% eccentricity for 4,824/4,824 scalars.
Eight of ten selected internal cases returned rows. The two dedicated torsion
cases returned zero frame rows. Independent CQC on the private model's own
100 modes, using 5% damping and the unadjusted native spectrum, reproduced
4,824/4,824 zero-eccentricity maxima within the recorded tolerance.

Across the original and private analyses, all 100 modal controls matched the
existing tolerance and 4,686/4,824 original force controls passed.
The 138 exceptions affect 103 of 804 case-cuts on 34 columns. The largest
exception is 1.19003e-6 kN m in RSX M2. The original-model transfer gate
remains open. The signed result applies to the static eccentricity component.
Dynamic simultaneity, story allocation and the original scenario's R14/alpha
gates remain open. Ledger `EV-GAP018-MANUAL-PAIR-20261119` links the native
readbacks, independent audit and per-component exceptions.

## Earlier original controls and R14 closure inventory

A fresh read of the original model reproduced all 4,824 native scalar controls at
402 element-side cuts for two spectrum cases, with zero numerical difference.
The selected scenario `RUN-17fbcff4be754227acb61dd1151b94cf` reproduced
16/16 stage payloads on replay. All 87 members have the same 17 open gates.
Fourteen block numerical closure. The other three still require source evidence
for engineering acceptance. The approved project profile, actual faces and
anchorage, axis-specific restraints, creep and spectral story feedback remain open.

The private Save As export reproduced 3,175 original lines byte-for-byte after
excluding the file header and the additional save-history line. The prepared
input added six definition lines for two zero-eccentricity controls. The
original model's solver log identifies eight internal static cases, including
two torsion solves. The first private API analysis invocation returned 1.
The later manual run and its original-control comparison are recorded above.

Ledger `EV-GAP018-PAIR-CONTROL-20261119` links the frozen roster, selected replay and private proof.
R14 is 0 closed / 87 partial. Engineering release is `NOT_READY`.

## Earlier GAP-018 live ETABS checkpoint on the original model

The user-session gateway on port 8876 captured the locked model twice on
2026-11-19. The v8 source is `RUN-9ad3c981cd9a4875bf383530429a1173`,
SHA-256 `61c5417b8f5f11b7352c9c02f2d518b67666fac09f1c7f6f53546fac207d7db9`.
Both reads observed the same model and units (kN/m/°C). The display, output
and mode selections were restored. The EDB digest matched before and after.
Implementation `9e01f92617a3a37a6e6a79ea913dafe5feb2b8da` is on
`work/gap-018-spectrum-evidence`. The integrated baseline is `24ddc371`.

The native function getter reported 26 points and returned 27 slots per array.
The first live v7 run retained the raw return and blocked the curve. The v8
stage resolved the leading zero pair against all 26 points of the same named
ETABS function table. Its signed, unadjusted curve references agree at printed
resolution for all 200 RSX/RSY case-modes. An exact-fraction calculation checked
1,000 numeric values. XML and array exports contain the same 2,200 text values.

Both cases specify 5% constant damping with zero overrides. All eight material
getters returned zero modal ratios. The one named linear-link property returned
six zero uncoupled damping coefficients. All 5,579 generated link elements map
to two area-spring assignments with user-defined stiffness. The effective modal
ratio is available at display precision. [CSI damping documentation](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Damping.htm)

An independent CQC calculation compared six force components at 402 configured
element-side cuts in each of two cases (4,824 comparisons). It used a uniform
5% effective ratio and the native curve without damping adjustment. All 4,824
ETABS total maxima exceeded that conditional dynamic reference. The model's
15-case catalog contains two spectrum cases, both with 5% eccentricity and
zero eccentricity overrides. Isolated accidental torsion remains **0/804**.
The next required evidence is a source
for the applied unrounded amplitudes and effective ratios, and a separately
identifiable torsional response at the same cuts. Story allocation and spectral
alpha remain open. [CSI accidental eccentricity guidance](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2001549)

Ledger `EV-GAP018-LIVE-SPECTRUM-20261119` records the run identities, frozen
scope, numerical references, replay and test evidence. The selected scenario
`RUN-20e3c9ea485448aeb4c71461e3237f9f` retains the original live input
bytes. All 87 candidate IDs and candidate digests match the earlier selection.
Independent repeats reproduced 16/16 stage payloads for each of the two runs.
The existing gateway served both reports with the same JSON and HTML as the
local projections, where 39 calculation or live entry points were guarded
and received zero calls. The full local suite
ran 1,428 Python tests with one Windows symlink skip and passed 11 JavaScript
test files. The installed wheel passed 252 tests. Engineering release remains
`NOT_READY`. Integration awaits the remaining source acceptance criteria.

## Earlier GAP-018 archive checkpoint

The local and published `baseline/local_import` were verified at
`24ddc371c66ebcba24bf8672fe3038564e26d48c`. The working branch
`work/gap-018-spectrum-evidence` starts there. The existing mixed-demand stage
used `same-source-spectral-components.v7`. At this checkpoint the
user-session gateway at port 8876 was unavailable.

The selected, sealed scenario supplied 100 native modes and 200 signed
amplitudes from the RSX and RSY display table. The amplitude comparison uses
the native signed participation factor and eigenvalue for the same mode. It
propagates the last printed digit of both acceleration and displacement.
All 200 intervals overlap. A separate exact-rational oracle checked the
predicted center, residual and interval allowance for each row. The largest
displayed-center residual was 0.00000641024 m. Trailing zeros can be suppressed
in the table, so this agreement establishes compatibility at printed resolution.
[CSI response-spectrum analysis FAQ](https://wikicsiamerica.atlassian.net/wiki/spaces/kb/pages/2006323)

On a fresh PMM capture, the gateway records the native modal case, load axis,
function, acceleration scale, curve knots, damping type, constant and mode
overrides through the same model connection. A selected-case XML response and
the in-plane diaphragm force table are retained for inspection. A native-curve
amplitude is an unadjusted reference. Effective damping also depends on material
and link/support contributions. The selected archive predates these new reads.
[CSI Analysis Reference Manual, chapter on response-spectrum analysis](https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf)

The configured inventory covers 87 members and 402 element-side cuts across
two spectrum cases. Isolated accidental-torsion contributions are **0/804**.
The case eccentricity and in-plane loads cannot isolate the internally applied
torsional response. The next live read must establish effective per-mode
damping, amplitude precision and the applied response before modal/directional
aggregation, story allocation or SCWB/alpha can consume it.
[CSI accidental eccentricity guidance](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2001549)

The implementation commit is `f5dc030beb7475c975b0d68a2e8ccc664cc1af7e`.
Both v7 CLI runs produced identical payloads for all 16 receipts. The JSON
and HTML report matched the sealed result with 34 entry points disabled and
zero calculation or live calls. The full local suite ran 1,426 Python tests
with one Windows symlink skip and passed 11 JavaScript test files. The
installed wheel passed 251 tests. An earlier full run exposed a stale report
heading assertion on the published baseline. The corrected assertion retains
the ETABS reinforcement gate heading and all three check identities.

The ledger record `EV-GAP018-SPECTRUM-ARCHIVE-20261119` identifies the 319-file
manifest, independent audit, replay and repeat runs, commands, and private log
hashes. The v7 result digest is
`a44cf26136085d5f73b1d8aa7cd1e04467be070b4a1d074a209ad821977dd105`.
All 16 original candidate receipts also passed integrity verification.
At the archive checkpoint the gateway probe returned socket error 10061.
The live checkpoint above supersedes that connection status.

## Integrated candidate checkpoint and source identity

- Logical integration base: `baseline/local_import`.
- Both verified milestones are integrated locally: native modal identity
  `5e1e10c1b9ffd0be777202873f4b428ded19b152`, then candidate reporting
  `46dcb3ccc5c6dfe052a88c81e1d7758838a0f1b5`. The retained work branches are
  historical milestones integrated into `baseline/local_import`.
- The documentation handoff at `24ddc371` followed `46dcb3c...`. Its published
  ref was rechecked directly with `git ls-remote` before the GAP-018 work.
  Original publication evidence remains in `.receipts/handoff/publication.json`.
- Keep baseline current at every completed, verified milestone. Start scoped work
  from that baseline, synchronize it using a normal push and verify the remote SHA.
  Preserve pending work separately; never reset local changes to an older remote.
- Original live source: `RUN-77039b97519e45029e209f0031d72d36`, SHA
  `9e5535ad2fe5749aa897a16023a3f7288062388df65f23013d243bbdb77bf640`.
- Final selection run: `RUN-4c6e8d795ca94411a1cd6d7f7f54c9de`, derived-source SHA
  `3de017a56036769e7436bac7f16363b552224740d75014678c73119fd1cd2171`.
- Final result SHA: `84740c17a28a7b9542ae21e0eee9dabeb51a7e6f8d2b2d7ced20b285f1365b83`.
- Runtime package SHA: `6cf4e08485fdb7b021a91988faca578c6b5cf9045231fa0f7740969cae731e52`.
- [449-file tested manifest](context/TESTED_FILES_COLUMN_CANDIDATES_20261119.json),
  SHA `731de054fa8350f60aa9b15ee2b49034f2a734fe61e8ce7281b1ce2022544bd7`.
  Final documentation and metadata edits are outside its executable test scope.
  Executable files were rechecked unchanged. Raw Windows hashes differ from Git
  text normalization; preserve the exact LF manifest.

Preserve unrelated `.idea/`, `build.zip` and the root handoff-recipe copy.
Keep `.receipts`, model captures, SQLite/PDFs, credentials and environments private.
`YENI_P0` stays read-only. No reset/clean, old-main merge or force-push.

## Completed selection and product work

[Detailed acceptance and commands](engineering/COLUMN_CAGE_SELECTION_ACCEPTANCE_20261119.md).
The plain live-source run had no selection policy. The requested scenario uses
existing `EnginePipelineRunner`, scenario/dependency owners, R10 selection and
same-cage local R08/PMM, then sealed R14/report outputs. No second solver or
attachment route was added. Calculation algorithms are unchanged.

The initial Φ8/90 trial `RUN-0505da6ae4394ceabd4c5a22f8e8ff4c` is retained. Forty
columns per direction exceeded the zero-concrete Ve reference (maximum 1.2388).
It was not adopted as the final transverse choice. The final explicit policy
allows ties 10/12 mm, keeps 90 mm confinement/midspan pitches and 1%–4%
longitudinal bounds, and preserves the exact original bytes in `parent.source`.
No ETABS analysis, model edit or save occurred.

| Final reference evidence | Result |
| --- | --- |
| Expected / selected / same-run bound columns | 87 / 87 / 87 |
| Transverse, both confinement and both shear references | All recorded criteria satisfied |
| Magnified selected PMM | 1,206/1,206 rows; max utilization 0.422829 |
| Spectral bounding corners | 25,728; max bound utilization 0.646794 |
| Ve TS 500 / zero-concrete reference maxima | 0.578317 / 0.793070 |
| Independent Decimal(80) area comparisons | 435; zero outside 1e-8; max difference 5.524e-13 |
| Source/receipt integrity | 16 receipts; original bytes preserved |
| Spectral alpha iteration | 0; BLOCKED_INPUTS |

`reporting.py` adds a projection of the saved candidate schedule, preserving
blocked members and unique-ID binding. `workspace-source.js` shows selected bars,
As, percentage, minimum As, ties and crossties across all IDs in tabs 4.2, 4.4,
4.5 and 4.6. Original ETABS template gates are explicitly labelled separately.
The data remains full precision; only display precision is reduced.

At the candidate-report checkpoint, the user restarted server 8876. Its JSON,
HTML and workspace script matched the final projection. All four tables contained
the same 87 unique IDs. During local
report verification 27 calculation entry points were disabled; zero were called.
No mouse/browser takeover or visual inspection was performed. The existing
server's session probe observed PID 11788, locked model, units 6; rediscover the
session before future reads rather than making that PID permanent.

Tests at the candidate-report milestone: **30 focused Python tests / 11 JavaScript files passed**. Initial
Node Python-path and view-harness failures are retained with successful retries.
Full Python suite, installed wheel and CI are **NOT_RUN for this presentation
increment**. Do not relabel the prior modal milestone's 1,407 Python / 241 wheel
results as newly run. Environment: Windows 11 build 26200, Python 3.12.10,
Node 24.22.1.

Private proof: `.receipts/verification/column-cage-selection-20261118T193312Z/`.
Ledger IDs: `EV-COLUMN-CAGE-TIE10`, `EV-COLUMN-CAGE-REPORT-TESTS`.

## Remaining engineering boundary and next task

The candidates are not engineer-approved or as-built. Hooks, splices, anchorage,
physical confinement lengths and complete physical-cut scope remain open.
Magnified PMM uses recorded reference clear/effective-length, sway and creep
assumptions; low utilization does not approve those inputs. Spectral corners
are independent bounds, not simultaneous force vectors. Both Ve/confinement
reference branches passing does not approve their normative applicability.

The final R14 retains 17 gate codes: R03 approved model/load roles and analysis
generation; physical joint faces/cuts/anchorage; local R08 effective-length,
sway, creep and analysis-order approval; spectral SCWB/story-alpha policy and
alpha feedback. No engineering CHECK or stable GAP is newly CLOSED.

The active bounded task is `SPECTRAL-MODAL-PRECISION-AND-TORSION-QUALIFICATION`,
GAP-018, then GAP-013 / GAP-016. Qualify the remaining applied amplitude,
effective damping and isolated torsional response on the frozen case/mode/cut
scope. Independent modal and directional acceptance and story allocation are
required before qualifying spectral alpha. General scheduler and
complete CheckInstance accounting remain GAP-005 / GAP-017.

## Earlier verified work and recipe

[Native modal acceptance](engineering/LIVE_MODAL_IDENTITY_ACCEPTANCE_20261118.md):
100/100 native numeric modes, 2/2 eccentricity definitions, 500 independent
numeric relationships, 16/16 identical repeat receipts, 1,407 Python / 10 JS /
241 wheel tests. This earlier scope is preserved. Eccentricity definitions do not
prove applied torsion or active damping. The registered method at that checkpoint was
`same-source-spectral-components.v6`.

Historical PMM v6 configured-cut proof remains 2,409 cuts for 73 single-element
columns plus 2,013 for 14 meshed columns, including both sides at 72 internal
joints. Do not convert a configured subset into a complete physical census.

[English recipe entry point](engineering/reference/recipe_20261118/README.md).
Published recipe/v5 source assets remain at a9d053f…; their evidence and the
73-control map are reference coverage, not 73 accepted production checks.
The old exported context ZIP describes b255c303… and is superseded by current
Git documents and ledger. No background GitHub sync is configured.

## Earlier handoff and publication checkpoint

[Worker and new-chat handoff](context/WORKER_HANDOFF_20261119.md) defines the
baseline workflow, reference boundaries and the next bounded acceptance task.
The private local resource index is `.receipts/handoff/LOCAL_RESOURCES_20261119.md`;
it identifies the working directory, Drive connection, reference locations, run
files, SQLite banks and launch command. It is intentionally absent from GitHub.
The baseline handoff at `24ddc371` updated guidance and evidence indexes.
Engineering tests and live ETABS operations were **NOT_RUN for that handoff**.
See `EV-HANDOFF-20261119`; earlier test records retain their original scopes.
