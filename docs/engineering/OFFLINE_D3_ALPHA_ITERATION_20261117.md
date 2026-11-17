# D3 — Bounded alpha demand feedback (offline reference branch)

Base: `efc4f4801546878a6a2fb862163f8bde2322db34`, tree
`594635961dc47960bb67b66e4e1bb55214181da7`.
Branch: `audit/pipeline-pmm-v6-20261117`. No live ETABS/COM, analysis or main merge.
Engineering release remains **NOT_READY**; this is not a full normative design approval.

## Delivered behavior

The existing `EnginePipelineRunner` has one typed `alpha-feedback` substage,
executed for explicit source-bound offline design scenarios after the initial
R10/R08 candidate calculations and before revision evidence and R14. It reuses
the current column selection, section capacity, local second-order, SCWB and
capacity-shear owners. It is not another solver or a catalog-wide scheduler.

1. Qualify the complete physical story population, configured common bottom
   cuts, assigned seismic combinations, selected two-sign SCWB results at both
   ends and original signed shear contributions. No successful-subset denominator.
2. Use the existing `column_engine.story_alpha` owner for Vis/Vik and the
   inclusive 0.70 <= alpha <= 1.00 amplification branch (1/alpha).
3. Apply absolute factors to eligible columns only, by combination and local
   bending/shear axis. Original source rows, N, torsion, signs and all native
   state identifiers remain unchanged. Every revision starts from the original
   captured vectors, never from previously amplified vectors.
4. Re-select only members with changed demands or failed reference local
   PMM/shear checks. Re-evaluate their incident joint consumers; reuse unchanged
   beam candidates and unaffected member results within this run. Reuse is
   checked against source, PMM, candidate and global-order input identities.
5. Feed selected sections to the current R08 owner; selected EI/Nk and magnified
   PMM are recalculated. Failed magnified vectors retain their exact element-side
   identities as additional selection constraints. Capacity shear is recalculated
   from the new capacities; revised Vd is a lower bound, not a multiplier on Mr.
6. Recompute qualified alpha from **original earthquake shear** and the new SCWB
   classification. Stop at a reference fixed point, missing evidence, system
   review, no candidate in the current constrained family, repeated state or
   iteration limit. The maximum is eight rebuilds (internal hard bound 32).
7. Seal trace, factors, eligible IDs, demand/candidate revisions and final
   qualification with the existing v2 snapshot. R14 consumes a valid final
   iteration record only when source, population and final candidate ledger agree.
   JSON and HTML only present the stored iteration; they never run it on export.

## Strictly supported input branch

- Upward vertical, orthogonal frames; configured `Min Stations=3`, zero I offset
  and qualified native element-side bottom cuts. Same physical elevation.
- Complete selected SCWB evidence for both rotation signs at both member ends.
  Missing support/roof exceptions are not invented. Optional low-axial numerator
  credit is not used.
- Same-sign projected story shears in each direction; counteracting contributions
  stay outside this reference branch pending a separately reviewed convention.
- Signed Linear Add seismic states with captured case/combination/load-pattern
  provenance showing **quake-only static case terms and zero self-weight**.
  A user-selected `ductile` group or a combination's name is not sufficient.
  Mixed G/Q/E states require an independently established earthquake-only shear
  decomposition; that expansion is not delivered here. Spectrum component maxima
  are never turned into a concurrent earthquake vector.
- k, free length, creep, analysis order and physical face/anchorage approvals remain
  independent gates. Numerical reference convergence does not resolve them.

## Terminal states

`FIXED_POINT_REFERENCE`: no changed absolute factors, no pending candidate
reselection and complete finite reference local PMM/shear results.
`BLOCKED_INPUTS`: incomplete source, selected SCWB or unsupported demand basis.
`NUMERIC_OR_DEPENDENCY_UNRESOLVED`: calculation evidence cannot establish feasibility.
`REANALYSIS_REQUIRED`: alpha below 0.70; system/ductility classification review is
required; no automatic R/system modification or new ETABS analysis occurs.
`NO_FEASIBLE_CANDIDATE`: the existing selector found none in its current allowed
family/constraints. This is not proof that every structural design is impossible.
`NO_CONVERGENCE_CYCLE` and `NO_CONVERGENCE`: repeated state and iteration cap.

Selection retains additional failed second-order and capacity-shear constraints
within the run, preventing forgotten failures. This monotone reference policy
is not a globally minimal reinforcement optimization. No persistent cache is added.

Joint panel equilibrium retains the original Vkol subtraction reference instead
of blindly subtracting amplified Vkol (which could artificially reduce Vj).
Affected joints explicitly retain `JOINT_EQUILIBRIUM_AFTER_ALPHA_REVIEW_REQUIRED`.
R14 never upgrades this to an approved joint design.

## Verification completed in the development environment

Linux CPython 3.13.5, Node.js 22.16.0:

- Full existing offline command: **1275 Python tests, OK**; 10 JavaScript test
  files and the existing golden acceptance command completed.
- **50 new D3 tests** (included in 1275): threshold, pure-seismic provenance,
  same-cut denominator, both ends/signs, axis mapping, no compounding, immutable
  forces, real owner input consumption, Ve floor, same-run selective R08 reuse,
  stale candidate/input rejection, trace sealing, fixed point, cycle, exhausted
  iterations and no-candidate semantics.
- Isolated wheel: **109 tests, OK**, not additional engineering checks.
- Actual existing selection/section solver on a light synthetic fixture: factor
  1.25 changes PMM utilization 0.07426078154575963 -> 0.09282597693219956,
  with the original capture unchanged. The selected 32Phi16 candidate stays the
  same in this example; changing every cage is not required for convergence.
- Canonical SQLite bank: ten SCWB_ALPHA arithmetic targets match within their
  recorded tolerance. Two alpha ~= 0.6262 cases return no amplification factor
  and require system review. This is a scalar reference check, not a cross-model
  join or full 467-fixture integration. The existing separate 44-record golden
  scope remains 15 matches / 25 insufficient source / 4 interpretation differences.

The iteration-driver positive test uses controlled SCWB/owner-port fixtures;
its convergence is software orchestration evidence, not an independent full
building engineering oracle. Existing calculation owners are tested separately.

## Real archived model: boundary deliberately preserved

The private original capture and explicit policy scenario were replayed with
87 columns, 957 member-combination pairs, 87 selected candidate/R08 results and
180 beam candidate scenarios. Its eight assigned seismic combinations are scalar
response-spectrum envelopes. D3 therefore records **BLOCKED_INPUTS, zero alpha
iterations** and the precise combination names. It does not fall back to gravity.
The pre-existing computations and expected scope remain recorded. R15 stays
87 partial/unbound, zero numerically closed, ENGINEERING_RELEASE=NOT_READY.
This real replay is not a successful alpha redesign or a normative acceptance.

Private sources, SQLite banks and full RUN receipts are not committed. Preserve
all earlier receipts. Use the existing `tools/replay_design_scenario.py` with the
private evidence ZIP and `config/scenarios/offline_tight_ties_v1.json`.

## Normative basis and remaining work

TBDY 2018 7.3.6.1-.3 (printed p.118): full story earthquake-shear ratio, threshold,
eligible two-end columns and 1/alpha. 7.3.7.5 (printed p.120): Ve >= Vd; the other
shear bounds remain separate checks. Original normative PDF page images reviewed
at the mirror https://unaribas.com/wp-content/uploads/2021/04/tbdy2018.pdf .
CSI official load-pattern descriptions distinguish earthquake pattern type and
self-weight; pattern facts do not confer engineering role approval.

Remaining: mixed-load earthquake decomposition / approved spectral demand method,
end exemptions and all geometry branches, complete independent cut census,
source generation and second-order approvals, joint equilibrium/detail closure,
general registry-driven topological execution and full independent structural
iteration golden cases. No execution-authority flag or release status is promoted.
