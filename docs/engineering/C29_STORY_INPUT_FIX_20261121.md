# C29 story-input execution fixes

## Scope

Inspected integration base: `896d0add4340b613d85099a61da44e09fe2ff205`.
This patch fixes two executable source-contract defects in the revised gravity
story calculation. It preserves the existing formula owners, pipeline and
paired-force inventory. R08's method identity advances from v13 to v14.

The private Windows read attempt and its exception trace were not available in
this environment. The fixes below are reproduced from committed code. Neither
is asserted to be the undocumented cause of the private read interruption.

## 1. Contradictory paired-member and story-contributor scopes

`normalize_gravity_order_pair` requires the paired force rowsets, mesh and
`frame_object_modifiers` to have exactly the same member IDs. That protects the
paired first-/second-order calculation. However, `produce_story_basis` previously
looked up every story column's object modifiers in this same paired-only map.

For a C29 pair containing only 225 and 142, another story column could not enter
the critical-load sum: adding its modifiers to the paired map failed admission;
omitting them left its stiffness unavailable. More native captures could not
resolve this contradiction.

The producer now accepts a separate optional source under each refined level:

```text
story_basis_source.contributor_modifiers
    schema = tbdy.next.gravity-story-contributor-modifiers.v1
    model_sha256 = the refined level's model hash
    analysis_generation = the refined level's analysis generation
    modifiers[physical_column_unique_id] = the eight native object modifiers
```

The independent geometry census still determines which columns must be present.
The source may include other known physical columns, but cannot substitute
unknown objects. Any paired column appearing in both maps must have identical
modifiers. Missing expected columns, stale generation/model identity, invalid
vectors and conflicting paired values remain unresolved. Legacy inputs without
this field keep their previous behavior. The paired force/mesh/modifier scope
is not widened.

The actual EI and Euler-load owner consumes the new values; the change is not
limited to accepting a new JSON field.

## 2. Frame/Shell namespace collision

`project_native_story_frame_forces` previously joined `ObjName` and `ElmName`
without checking `ObjType`. ETABS can return generated Shell rows in the same
table, with names that overlap the Frame namespace. Such a row could produce a
false duplicate or an incorrect mesh association.

The reader now requires the observed `ObjType` field and filters `Frame` rows
before joining object identities or checking element uniqueness. This matches
the existing PMM mesh-owner convention. A missing namespace field is reported
as an unsupported source schema; it is not guessed.

## Numerical regression and verification

Verification results are recorded in the linked ledger entry
`EV-C29-STORY-CONTRIBUTOR-FIX-20261121`. The example is an offline
`CONTRACT_FIXTURE`, not C29 or an ETABS capture. The model has three expected
columns. Only C1 belongs to the paired/refined calculation; C3 crosses the same
story cut and contributes to that story's compression and critical-load sum.

The normal runner computes actual R08 factors, selected-section PMM, R14 and
sealed results. It retains one paired member, three common physical case-cuts,
four common element sides and 24 finest-mesh paired sides. Those counts must
not be confused with the original C29's 18 physical case-cuts and 24 common sides.

| Quantity | Fresh normal-runner result |
| --- | ---: |
| C3 effective EI (N mm²) | 163,387,643,767,070.34 |
| C3 critical load (kN) | 64,502.856320283914 |
| Complete story critical-load sum (kN) | 193,508.56896085176 |
| Concurrent story compression (kN) | 7,780 |
| Local member factor, both axes | 1.0288216814643838 |
| Governing story/final factor, both axes | 1.0551488523204795 |
| First refined side, revised M2 (kN m) | -158.27232784807194 |
| First refined side, revised M3 (kN m) | 179.3753048944815 |
| First refined side, selected-cage PMM utilization | 0.16967855031804033 |

The tests independently compute C3's EI and Euler load, change its modifier,
and assert that the normal pipeline changes the story factor and final moments.
They retain the paired-only input rejection and do not substitute successful
stage outputs. The two new regression targets fail against an isolated archive
of the exact inspected baseline. That red run is a recorded tool observation;
its raw log was not retained and is not presented as a hashed log artifact.

Fresh verification in Linux, Python 3.12.14 and Node.js v24.22.3:

- Focused command: `PYTHONPATH=src:tests .venv/bin/python -B -m unittest tests.test_gravity_story_basis tests.test_variable_axial_vertical_slice tests.test_adopted_second_order_basis -q` — 44 passed in 31.223 s. Raw log not retained; tool observation recorded separately.
- Full command: `.venv/bin/python -B tools/test_offline.py` — 1,686 Python tests passed in 188.653 s, **zero skipped**, compilation and all 11 JavaScript test files passed. Raw log retained privately.
- Existing 44-record golden CLI: 33 numerical matches, 7 insufficient-source records and 4 interpretation differences. Engineering release remains `NOT_READY`. These records are separate from the new regression tests and fixture.
- Normal CLI fixture run: `RUN-39d1a15ca5114c4f94b235f7bc6b375e`; explicit `--compare-run` replay: `RUN-2671c17a263a49bf90bfa787b8af7a09`, **12/12 stages IDENTICAL**, including sealed results and report evidence.
- A separate normal-runner case, `RUN-83e85ddb54a54281bc391130ed3bfc0b`, removes the story source and retains native-shaped kinematics. It returns `FULL_SPAN_RECOVERED` while the revised story factor remains unavailable. This verifies their execution independence, not original-building deformation.

The public test fixture factory is
`tests/test_variable_axial_vertical_slice.py::completion_with_story_contributor`.
The private CLI exercise command was
`.venv/bin/python -B .receipts/c29-native-input-fix-20261121/run_fixture.py`.
Its source is generated by that factory and passed to the existing `run_cli`;
the script does not introduce another calculation owner. The ledger records
the tested-file manifest, source, sealed result, report and retained log hashes.
No live ETABS run or Windows verification was performed in this patch.

Negative regressions preserve the expected population when a contributor is
missing or comes from a different analysis generation. Additional assertions
reject model mismatch and paired-value conflict. A Shell row with overlapping
object/element names leaves the Frame result unchanged; removing ObjType makes
that source unresolved.

## Original-building continuation

1. Preserve the already solved private 8-part session when available. Record the
   exact exception and failed operation from the stopped read; do not describe
   an unexplained interruption as a completed source acquisition.
2. Capture and consume the native six-DOF kinematics packet through the existing
   R08 path. Full-span recovery is independent of `produce_story_basis`; missing
   story factors need not delay the actual 8-part peak or the subsequent 4/8
   comparison. Preserve the original-joint chord definition and required native
   end-condition/stiffness metadata.
3. For the story calculation, place all required native column modifiers in the
   new contributor source, leaving paired maps restricted to their existing IDs.
   Bind force resultants, equilibrium and actual stiffness/restraint inputs from
   the same revised analysis.
4. Treat `STORY_WALL_CRITICAL_LOAD_METHOD_UNSUPPORTED` as a method limitation,
   not a promise that another getter will supply the missing field. The present
   implementation has no supported wall critical-load input branch. A decision
   to use complete compression with column-only stiffness credit would require
   an explicit method/population contract and supported physical bases for every
   credited column. This patch does not silently make that decision, assign zero
   wall capacity, or accept native offsets as a coupled member's TS 500 free length.

The original C29 result remains the recorded **2/87 conditional numerical
closures**. Its revised-model 12 factors and 24 common-side revised PMM results
are **NOT_RUN in this environment**. No engineering acceptance or whole-building
GAP closure is granted by this patch.
