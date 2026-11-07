# VS05 - TBDY 2018 Normative Kernels / Engineering Rule Contract

**BASE:** accepted VS04 main at 895e6b5b55a2e133b34e199577940ec7cee20837.
**BRANCH:** work/vs05-normative-base-shear-drift-20261107.

This is the first genuine normative calculation slice AFTER merging the
bounded VS04 source/product work. This stage does not modify accepted
ETABS COM, eight VS03 controls, source receipts or history.

## Primary rule authority

AFAD official TBDY 2018: https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf

Relevant provisions: 4.7.1.1 Eq (4.19); 4.7.3 Eq (4.26)-(4.27);
4.8.4.1-2 Eq (4.31); 4.9.1.1-4 Eq (4.32)-(4.34).

Metadata rule cards: config/rules/tbdy2018_ch4_vs05.yaml.
Executable pure functions: src/tbdy_next/normative_checks.py.

## Base shear

For each X or Y seismic direction, with independently qualified input:
VtE = max(mt * SaR(Tp), 0.04 * mt * I * SDS * g).
Use kg, m/s2, and convert N to kN.

GammaE=0.90 if at least one A1/B2/B3 is positively classified;
gammaE=0.80 ONLY if all A1, B2, B3 have been explicitly classified absent.
Unknown B2 or B3 must not become gammaE=0.80.

Beta_required=max(1, gammaE * VtE / Vtx_pre_beta).
The numerical condition compares applied beta with beta_required.
Source identity, actual applied scaling, prior beta state, full modal
analysis method applicability, basement boundary, Tp and DD2 are mandatory.

## Effective relative story drift

For each physical story and direction:
Delta_i = max_members abs(u_upper - u_lower)
delta_i,max = (R/I) * Delta_i
lambda = Sae_DD3(Tp) / Sae_DD2(Tp)
lambda * delta_i,max / h_i <= limit

Adjacent brittle infill: limit = 0.008 * kappa.
Documented flexible joints/walls: limit = 0.016 * kappa, but ONLY after
adequate flexible wall displacement capacity and connection verification.
Kappa=1 for RC, 0.5 for steel (no special exception auto-application).

The original reduced displacement basis must NOT have incorporated the
minimum Eq (4.19) force floor or 1.4 TpA period cap for Eq (4.32).
Source ETABS Drift and Drift/ cells alone do not establish this.
Verify complete physical member census and same modal/case/step generation.

## CheckResult dimensions

- applicability: NOT_REVIEWED or APPLICABLE_SOURCE_ASSERTED
- execution: BLOCKED_BY_EVIDENCE or EXECUTED_NUMERIC_FORMULA
- numerical_condition: explicit true or false formula outcome
- status: NOT_PROVEN, MEETS_NUMERICAL_CRITERION or
  DOES_NOT_MEET_NUMERICAL_CRITERION
- coverage, missing_evidence, source_refs, formula_inputs, calculation
- formal_compliance always NOT_PROVEN in VS05 until production-authorized
  engineering evidence is independently verified
- engineering_release always NOT_READY

Even test fixtures with source-assertion booleans True do not constitute
third-party or independent model/analysis certification.

## Verification

Synthetic golden and negative tests cover:
  - Eq (4.19) minimum governing, gamma 0.9/0.8,
    beta required/applied true and false numerical outcome
  - absent/unknown B2/B3, missing generation, wrong RSX/RSY reference,
    NaN, wrong pre-beta Vtx and no source receipt
  - physically signed and zero member-end drift, complete member census,
    flexible-capacity gate, DD3/DD2 matching and height limit
  - no user-asserted data promote a formal code PASS

Next production steps: independently qualify model/analysis generation,
approved Tp and Eq (4.26)/(4.27) cap, mass boundary, spectral DD2/DD3,
irregularities, upper/lower basement scope, pre-beta Vtx, flexible wall
capacity and physical members; then bind real typed facts to the kernel
and JSON/HTML/left Result Tree under one verified run_id.

**VS05 code release:** WORKING BRANCH / FORMULA TESTS ONLY.
**Regulatory acceptance:** NOT_PROVEN.
**Engineering release:** NOT_READY.
**Merge to main:** HOLD until separate supervisor acceptance.
