# Variable-axial numerical design slice

## Scope and inspected revision

Integration base: `baseline/local_import`, exact inspected commit
`eb6328290a66484c8ddbc8ba37158be270b8fc5d`.

This change adds an explicit self-weight axial idealization to the existing
source-to-design pipeline. The normal runner selects column and beam cages,
calculates second-order PMM, capacity shear and interior-joint checks, seals the
results and projects them into the report. No stage result or resistance is
replaced by a prepared successful result in the public integration example.

The public example is a **CONTRACT_FIXTURE**. It is not the original C29, an
ETABS analysis or an independent whole-building equilibrium solution. The latest
private C29 source, Windows working tree and 18 live matched-EI solutions were
**NOT_INSPECTED** here. Their published checkpoint remains separate.

## The calculation decision

TS 500 7.6.2 states a constant-section and constant-axial-force applicability
condition. The existing gate therefore blocked a member whose recorded force
varied with its self weight, even though the numerical coefficient and section
calculations had been completed.

The new, optional request declares
`ADOPTED_PRISMATIC_SELF_WEIGHT_NMAX_IDEALIZATION`. The request does not assert
that the physical member meets the constant-axial-force condition. For each
explicit signed combination:

1. The source owner reconciles every required cut with the primitive load cases
   and the member's recorded self weight.
2. The maximum recorded compression is supplied to the existing magnification
   coefficient owner on both axes.
3. The actual compression at each cut remains the input to minimum eccentricity
   and section capacity. Original force vectors are preserved.
4. Existing K, EI, Rm, sway, global-factor and Eq. 7.29 decisions remain required.
   Failed coefficients, incomplete populations and downstream failures retain
   their normal outcomes.

This is an **adopted numerical idealization**, not a newly qualified TS 500
method. Its conservatism is not established by self-weight equilibrium or by a
low PMM utilization. `engineering_approval` remains `NOT_GRANTED`, the result
retains `conservative_bound_proven: false`, and engineering release remains
`NOT_READY`. The change does not close the engineering applicability of GAP-009.

The optional declaration is deliberately separate from the legacy
`TS500_7_6_2_CONSTANT_SECTION_AND_AXIAL_FORCE` branch. A request cannot retain
that applicability label while enabling the idealization.

## One existing calculation path

| Step | Existing owner / consumer | Result used downstream |
| --- | --- | --- |
| Explicit scenario | `engineering/second_order_basis.py::normalize_second_order_basis` | Exact members, signed combinations and declared approximation |
| Source premises | `engineering/column_axial_balance.py::project_self_weight_nmax_idealization` | Independent configured-cut scope, actual N range, primitive superposition and self-weight balance |
| Physical scope | Existing clear-length, mesh and configured-cut owners | Prismatic, uncoupled physical member and cut identities |
| Second-order demand | `engineering/column_r08_local_live.py` and `column_engine/ts500_column.py` | Actual Nmax coefficient, local-N eccentricity and final design moments |
| Selected capacity | `column_engine/section_capacity.py` | Actual selected-cage PMM assessment at every cut |
| Beam, column and joint design | Existing R10, SCWB and transverse owners | Selected reinforcement, Ve/Vr, joint shear and directional SCWB |
| Numerical closure | `engineering/column_r14_closure.py::_axial_idealization_context` | Exact application consumption before conditional numerical completion |
| Replay and reporting | Existing pipeline snapshot and report owners | Recorded results, with no report-time recalculation |

Web and CLI continue to enter `EnginePipelineRunner`. The registered local R08
method is `column-r08-local.adopted-basis.v12`. No new CHECK or GAP identity is
introduced. The 73 control/example headings, 44 production comparisons,
historical 333 arithmetic matches, DAG nodes and software tests remain separate
populations.

## Supported source premises

The initial scope is an upright, prismatic, rectangular column with one analysis
element, independently bound physical faces and the existing exact configured
three-cut census. All declared cuts must carry positive compression. Every
actually variable signed design combination must be covered by the request.
Spectral Max/Min component envelopes cannot supply this signed-source proof.

The source calculation checks both the force change between cuts and absolute
primitive-case superposition at each cut. A constant force offset can therefore
not pass merely because its gradient is correct. The numerical superposition
budget is 1e-8 kN. The self-weight residual also has a 0.001 kN absolute cap;
coarse displayed material precision cannot authorize an arbitrary discrepancy.
These are numerical source-control budgets, not design safety margins.

Configured-grid coordinates use the existing PMM machine-tolerance and unique
matching rule. Eligibility evidence and the consumed PMM rows retain identical
native cut identities. A one-ULP representation change is accepted; a material
cut shift, an exact duplicate or an ambiguous nearby duplicate is rejected.

The existing physical scope, current source, selected cage and consumed
coefficient/cut records are bound into R08. R14 validates that exact context
before treating `ADOPTED_AXIAL_IDEALIZATION_ENGINEERING_ACCEPTANCE_PENDING` as
an acceptance condition. That label is not a general allowed-gate exemption.
An unsupported or incomplete request retains a blocking calculation condition.

Wall-coupled members, unexplained transfer forces, missing primitives or cuts,
already-second-order vectors, unsupported section changes and denominator or
story-limit failures are outside the successful branch. The existing C104
physical and reinforcement problem is not represented by this idealization.

## Reproducible public calculation

The fixture uses two 800 x 800 mm columns, four connected beams, an interior
joint, five assigned signed combinations and thirty column case-cuts. The
fixture material has unit weight 25 kN/m3 and weight modifier 1. Its independently
specified self-weight load is:

`25 kN/m3 x 0.64 m2 = 16 kN/m`.

Across a 2.5 m clear span this gives 40 kN of axial variation. The supplied
compression values are `[2540, 2520, 2500]` kN for C1 and
`[1540, 1520, 1500]` kN for C2. The primitive-case source and the five signed
combination vectors carry those same physical cuts.

The paired regression runs the same source with and without the explicit
idealization. The legacy request retains the variable-axial applicability gate.
The explicit request must run all actual owners and complete the conditional
numerical scope. Independent scalar checks cover self weight, EI, Euler load,
coefficient and moment-floor arithmetic; these do not claim an independent
validation of the entire production PMM solver.

Run the published example through the existing command:

```bash
python -B -m tbdy_next.cli run-pipeline --source examples/variable_axial_slice_20261121/synthetic_input.json --design-scenario examples/variable_axial_slice_20261121/design-scenario.json --case Modal --out .receipts/variable-axial-example
```

Numerical outputs, fresh commands, environment and file identities are recorded
in `variable_axial_slice_20261121/VERIFICATION_RESULTS.json`. Do not substitute
the earlier 1,646-test checkpoint or the private 420-cut C29 calculation for this
new verification.

## Continue the actual C29 from its sealed original source

The continuation uses the existing original-source TS 500 calculation. It does
not promote the revised matched-EI comparison into selected demand, combine its
column forces with original-model beam forces, change the chosen K/Rm/story
inputs or resolve the sampled deformation-peak comparison.

The preparation utility recovers the exact existing scenario from its finalized
receipt, verifies its frozen parent and writes a new request. It performs no
calculation, no ETABS acquisition and no model edit. The normal pipeline then
performs all source-premise and design checks. The declaration is opt-in and
must be read as the numerical idealization described above.

From the Windows project root, using the local project interpreter:

```powershell
.\.venv\Scripts\python.exe -B tools/prepare_axial_idealization_scenario.py --from-run .receipts/RUN-464231f1e18f465f88da868f7306a753 --member 225 --member 142 --combination Grav_Ult --combination Grav_TempNeg --combination Grav_TempPos --decision-reference "C29 explicit self-weight Nmax calculation idealization; engineering acceptance pending" --scenario-id c29-self-weight-nmax --out .receipts/c29-self-weight-nmax/request.json

.\.venv\Scripts\python.exe -B -m tbdy_next.cli run-pipeline --source .receipts/RUN-464231f1e18f465f88da868f7306a753/parent.source --design-scenario .receipts/c29-self-weight-nmax/request.json --case Modal --out .receipts/c29-self-weight-nmax
```

The run ID above is the published C29 matched-EI checkpoint. If the local
integration branch contains a newer source, use its actual finalized scenario
receipt instead; never reset local work or substitute an older source to match
this document. The utility refuses to overwrite an existing request. It also
refuses members, combinations or Cm choices outside the existing request.

The actual C29 result must show the original source identities, independently
complete signed cuts, coefficient Nmax versus local N, selected cages, PMM,
shear, connected-beam and joint outcomes in one sealed run. A further source or
design failure must remain visible; no numerical closure count is prescribed
in advance. Report the actual C29 outcome separately from the public fixture.

## Completion boundary

This delivery completes a supported software consumer and an executable
variable-axial numerical design slice. Engineering acceptance of the adopted
idealization remains a real method decision. The private original-building
replay, revised same-model story totals/K, local deformation qualification,
spectral method differences and coupled C104 design are not silently closed by
the public example. The existing GAP IDs retain those scopes.
